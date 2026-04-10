"""
Pipeline orchestrator for the All_Beauty corpus ingestion.

Executes all 8 phases sequentially with checkpoint/resume support.
This is the main entry point for the pipeline.

Usage:
    python -m adam.corpus.pipeline.orchestrator \\
        --reviews "/Volumes/Sped/Review Data/Amazon/All_Beauty.jsonl" \\
        --products "/Volumes/Sped/Review Data/Amazon/meta_All_Beauty.jsonl" \\
        --neo4j-uri neo4j://127.0.0.1:7687 \
        --neo4j-password atomofthought
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Iterator

from neo4j import GraphDatabase

# Project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from adam.corpus.annotators.ad_side_annotator import AdSideAnnotator
from adam.corpus.annotators.dual_annotator import DualAnnotator, _should_dual_annotate
from adam.corpus.edge_builders.match_calculators import compute_brand_buyer_edge
from adam.corpus.neo4j.bulk_writer import BulkWriter
from adam.corpus.neo4j.schema_extension import apply_schema
from adam.corpus.pipeline.checkpoint_manager import CheckpointManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("adam.corpus.pipeline")


# =============================================================================
# DATA LOADING
# =============================================================================

def iter_jsonl(path: str | Path) -> Iterator[dict[str, Any]]:
    """Stream JSONL records without loading entire file into memory."""
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                if line_num % 100_000 == 0:
                    logger.warning(f"JSON parse error at line {line_num}: {e}")


def load_product_index(products_path: str) -> dict[str, dict]:
    """Load product metadata indexed by parent_asin."""
    logger.info(f"Loading product index from {products_path}...")
    index: dict[str, dict] = {}
    for record in iter_jsonl(products_path):
        key = record.get("parent_asin", record.get("asin", ""))
        if key:
            index[key] = record
    logger.info(f"Loaded {len(index)} products")
    return index


# =============================================================================
# PHASE RUNNERS
# =============================================================================

def run_phase_0(driver, checkpoint_dir: str) -> None:
    """Phase 0: Apply Neo4j schema extensions."""
    logger.info("=== PHASE 0: Schema Extension ===")
    n = apply_schema(driver)
    logger.info(f"Applied {n} schema statements")


def run_phase_1(
    products_path: str,
    annotator: AdSideAnnotator,
    writer: BulkWriter,
    checkpoint: CheckpointManager,
    limit: int | None = None,
) -> dict[str, int]:
    """Phase 1: Annotate product descriptions (ad-side, Domains 29-33)."""
    logger.info("=== PHASE 1: Product Description Annotation ===")
    completed = checkpoint.load_completed("phase1")
    logger.info(f"Resuming from {len(completed)} previously completed products")

    stats = {"annotated": 0, "skipped_short": 0, "skipped_completed": 0, "errors": 0}
    batch: list[dict[str, Any]] = []
    batch_size = 50

    for record in iter_jsonl(products_path):
        asin = record.get("parent_asin", record.get("asin", ""))
        if not asin:
            continue
        if asin in completed:
            stats["skipped_completed"] += 1
            continue

        if limit and stats["annotated"] + stats["skipped_short"] >= limit:
            break

        try:
            # Check if product has enough text to annotate with Claude
            desc = " ".join(record.get("description", []))
            features = " ".join(record.get("features", []))
            has_text = len(desc) > 20 or len(features) > 20

            if has_text:
                annotation = annotator.annotate(record)
                props = annotation.to_flat_dict()
                stats["annotated"] += 1
            else:
                # Minimal annotation from title/category/price
                props = {
                    "annotation_confidence": 0.1,
                    "annotation_tier": "minimal",
                }
                stats["skipped_short"] += 1

            # Build node record
            node_props = {
                "asin": asin,
                "title": record.get("title", "")[:500],
                "main_category": record.get("main_category", ""),
                "store": record.get("store", ""),
                "price": str(record.get("price", "")),
                "average_rating": record.get("average_rating", 0.0),
                "rating_number": record.get("rating_number", 0),
                **props,
            }

            batch.append({"asin": asin, "properties": node_props})

            if len(batch) >= batch_size:
                writer.write_product_descriptions(batch)
                checkpoint.mark_batch_completed("phase1", [r["asin"] for r in batch])
                batch.clear()

                total = stats["annotated"] + stats["skipped_short"]
                if total % 500 == 0:
                    logger.info(
                        f"Phase 1: {stats['annotated']} annotated, "
                        f"{stats['skipped_short']} minimal, "
                        f"{stats['errors']} errors"
                    )

        except Exception as e:
            stats["errors"] += 1
            logger.error(f"Phase 1 error for {asin}: {e}")
            continue

    # Flush remaining
    if batch:
        writer.write_product_descriptions(batch)
        checkpoint.mark_batch_completed("phase1", [r["asin"] for r in batch])

    logger.info(f"Phase 1 complete: {stats}")
    return stats


def run_phase_2_3(
    reviews_path: str,
    product_index: dict[str, dict],
    annotator: DualAnnotator,
    writer: BulkWriter,
    checkpoint: CheckpointManager,
    limit: int | None = None,
) -> dict[str, int]:
    """Phase 2+3: Review annotation (user-side + peer-ad-side dual annotation)."""
    logger.info("=== PHASE 2+3: Review Annotation ===")
    completed = checkpoint.load_completed("phase2_3")
    logger.info(f"Resuming from {len(completed)} previously completed reviews")

    stats = {
        "user_annotated": 0, "dual_annotated": 0,
        "skipped_short": 0, "skipped_completed": 0,
        "skipped_unverified": 0, "errors": 0,
    }
    review_batch: list[dict[str, Any]] = []
    reviewer_batch: list[dict[str, Any]] = []
    has_review_batch: list[dict[str, Any]] = []
    batch_size = 50

    for record in iter_jsonl(reviews_path):
        # Filter: verified purchase + text > 50 chars
        if not record.get("verified_purchase", False):
            stats["skipped_unverified"] += 1
            continue
        text = record.get("text", "")
        if not text or len(text) < 50:
            stats["skipped_short"] += 1
            continue

        user_id = record.get("user_id", "unknown")
        asin = record.get("asin", record.get("parent_asin", "unknown"))
        ts = record.get("timestamp", 0)
        review_id = f"{user_id}_{asin}_{ts}"

        if review_id in completed:
            stats["skipped_completed"] += 1
            continue

        if limit and (stats["user_annotated"] + stats["dual_annotated"]) >= limit:
            break

        try:
            # Get product context for prompt
            product = product_index.get(asin, product_index.get(record.get("parent_asin", ""), {}))
            product_title = product.get("title", "Beauty Product")
            category = product.get("main_category", "All Beauty")

            user_ann, peer_ann = annotator.annotate(record, product_title, category)

            # Build AnnotatedReview node
            node_props: dict[str, Any] = {
                "review_id": review_id,
                "asin": asin,
                "parent_asin": record.get("parent_asin", asin),
                "user_id": user_id,
                "star_rating": record.get("rating", 0),
                "helpful_votes": record.get("helpful_vote", 0),
                "verified_purchase": True,
                "timestamp": ts,
                "text_length": len(text),
                **user_ann.to_flat_dict(),
            }

            if peer_ann is not None:
                node_props.update(peer_ann.to_flat_dict())
                stats["dual_annotated"] += 1
            else:
                stats["user_annotated"] += 1

            review_batch.append({"review_id": review_id, "properties": node_props})
            reviewer_batch.append({"reviewer_id": user_id, "review_id": review_id})
            has_review_batch.append({"product_asin": asin, "review_id": review_id})

            if len(review_batch) >= batch_size:
                writer.write_annotated_reviews(review_batch)
                writer.write_reviewers(
                    [{"reviewer_id": r["reviewer_id"]} for r in reviewer_batch]
                )
                # Write supporting edges
                writer.write_authored_edges(reviewer_batch)
                writer.write_has_review_edges(has_review_batch)

                checkpoint.mark_batch_completed(
                    "phase2_3", [r["review_id"] for r in review_batch]
                )
                review_batch.clear()
                reviewer_batch.clear()
                has_review_batch.clear()

                total = stats["user_annotated"] + stats["dual_annotated"]
                if total % 200 == 0:
                    logger.info(
                        f"Phase 2+3: {stats['user_annotated']} user-only, "
                        f"{stats['dual_annotated']} dual, "
                        f"{stats['errors']} errors | "
                        f"Claude stats: {annotator.stats}"
                    )

        except Exception as e:
            stats["errors"] += 1
            logger.error(f"Phase 2+3 error for review {review_id}: {e}")
            continue

    # Flush remaining
    if review_batch:
        writer.write_annotated_reviews(review_batch)
        writer.write_reviewers(
            [{"reviewer_id": r["reviewer_id"]} for r in reviewer_batch]
        )
        writer.write_authored_edges(reviewer_batch)
        writer.write_has_review_edges(has_review_batch)
        checkpoint.mark_batch_completed(
            "phase2_3", [r["review_id"] for r in review_batch]
        )

    logger.info(f"Phase 2+3 complete: {stats}")
    return stats


def run_phase_4(
    driver,
    writer: BulkWriter,
    checkpoint: CheckpointManager,
) -> dict[str, int]:
    """Phase 4: Build product ecosystems (Domain 35 aggregation).

    Aggregate review annotations per product to compute ecosystem-level constructs.
    This is mostly computation — runs directly against Neo4j.
    """
    logger.info("=== PHASE 4: Product Ecosystem Construction ===")
    completed = checkpoint.load_completed("phase4")

    stats = {"ecosystems_created": 0, "skipped_completed": 0}

    # Get all products that have reviews
    with driver.session() as session:
        products = session.run("""
            MATCH (pd:ProductDescription)-[:HAS_REVIEW]->(r:AnnotatedReview)
            WITH pd.asin AS asin, count(r) AS review_count
            WHERE review_count > 0
            RETURN asin, review_count
            ORDER BY review_count DESC
        """).data()

    logger.info(f"Found {len(products)} products with reviews")

    batch: list[dict[str, Any]] = []
    anchors_batch: list[dict[str, Any]] = []

    for p in products:
        asin = p["asin"]
        if asin in completed:
            stats["skipped_completed"] += 1
            continue

        # Aggregate review annotations for this product
        with driver.session() as session:
            agg = session.run("""
                MATCH (pd:ProductDescription {asin: $asin})-[:HAS_REVIEW]->(r:AnnotatedReview)
                RETURN
                    count(r) AS review_count,
                    avg(r.star_rating) AS avg_rating,
                    avg(toFloat(r.verified_purchase = true)) AS verified_ratio,
                    avg(r.user_emotion_pleasure) AS avg_pleasure,
                    avg(r.user_emotion_arousal) AS avg_arousal,
                    avg(r.user_regulatory_focus_promotion) AS avg_promotion,
                    avg(r.user_regulatory_focus_prevention) AS avg_prevention,
                    avg(r.user_personality_openness) AS avg_openness,
                    avg(r.user_personality_conscientiousness) AS avg_conscientiousness,
                    avg(r.user_personality_extraversion) AS avg_extraversion,
                    avg(r.user_personality_agreeableness) AS avg_agreeableness,
                    avg(r.user_personality_neuroticism) AS avg_neuroticism,
                    avg(r.peer_ad_testimonial_authenticity) AS avg_authenticity,
                    avg(r.peer_ad_social_proof_amplification) AS avg_sp_amp,
                    avg(r.peer_ad_recommendation_strength) AS avg_rec_strength,
                    avg(r.peer_ad_objection_preemption) AS avg_objection_pre,
                    sum(r.helpful_votes) AS total_helpful,
                    collect(r.helpful_votes) AS helpful_list
            """, asin=asin).single()

        if not agg or agg["review_count"] == 0:
            continue

        review_count = agg["review_count"]
        helpful_list = [h for h in (agg["helpful_list"] or []) if h and h > 0]
        helpful_concentration = 0.0
        if helpful_list and sum(helpful_list) > 0:
            total_h = sum(helpful_list)
            top_10_pct = sorted(helpful_list, reverse=True)[:max(1, len(helpful_list) // 10)]
            helpful_concentration = sum(top_10_pct) / total_h if total_h > 0 else 0.0

        # Compute ecosystem constructs
        eco_props = {
            "asin": asin,
            "eco_review_count": review_count,
            "eco_avg_rating": round(agg["avg_rating"] or 0, 4),
            "eco_verified_ratio": round(agg["verified_ratio"] or 0, 4),
            "eco_helpful_concentration": round(helpful_concentration, 4),

            # Frame coherence: how consistent is the emotional framing across reviews?
            # High coherence = reviews agree on what the product IS
            "eco_frame_coherence": round(
                max(0, 1.0 - abs((agg["avg_promotion"] or 0.5) - (agg["avg_prevention"] or 0.5))), 4
            ),

            # Social proof density: what fraction of reviews contribute meaningful social proof?
            "eco_sp_density": round(
                (agg["avg_sp_amp"] or 0) * min(1.0, review_count / 20.0), 4
            ),

            # Social proof diversity: personality diversity of reviewers
            "eco_sp_diversity": round(
                min(1.0, (
                    abs((agg["avg_openness"] or 0.5) - 0.5) +
                    abs((agg["avg_extraversion"] or 0.5) - 0.5) +
                    abs((agg["avg_agreeableness"] or 0.5) - 0.5)
                ) / 1.5), 4
            ),

            # Authority layering: domain expertise signals
            "eco_authority_layers": round(agg["avg_authenticity"] or 0, 4),

            # Cialdini coverage: breadth of persuasion techniques present
            "eco_cialdini_coverage": round(
                min(1.0, (
                    (1.0 if (agg["avg_sp_amp"] or 0) > 0.3 else 0.0) +
                    (1.0 if (agg["avg_authenticity"] or 0) > 0.3 else 0.0) +
                    (1.0 if (agg["avg_rec_strength"] or 0) > 0.3 else 0.0) +
                    (1.0 if (agg["avg_objection_pre"] or 0) > 0.3 else 0.0)
                ) / 4.0), 4
            ),

            # Temporal arc: how does sentiment evolve?
            "eco_temporal_arc": round(agg["avg_pleasure"] or 0, 4),

            # Risk coverage: how well do reviews address purchase risks?
            "eco_risk_coverage": round(agg["avg_objection_pre"] or 0, 4),

            # Negative review resolution quality
            "eco_neg_review_resolution": round(
                max(0, (agg["avg_rec_strength"] or 0) * (agg["avg_rating"] or 0) / 5.0), 4
            ),
        }

        batch.append({"asin": asin, "properties": eco_props})
        anchors_batch.append({"asin": asin})

        if len(batch) >= 100:
            writer.write_ecosystems(batch)
            writer.write_anchors_edges(anchors_batch)
            checkpoint.mark_batch_completed("phase4", [r["asin"] for r in batch])
            stats["ecosystems_created"] += len(batch)
            batch.clear()
            anchors_batch.clear()

            if stats["ecosystems_created"] % 500 == 0:
                logger.info(f"Phase 4: {stats['ecosystems_created']} ecosystems created")

    if batch:
        writer.write_ecosystems(batch)
        writer.write_anchors_edges(anchors_batch)
        checkpoint.mark_batch_completed("phase4", [r["asin"] for r in batch])
        stats["ecosystems_created"] += len(batch)

    logger.info(f"Phase 4 complete: {stats}")
    return stats


def run_phase_5(
    driver,
    writer: BulkWriter,
    checkpoint: CheckpointManager,
) -> dict[str, int]:
    """Phase 5: Compute BRAND_CONVERTED edges (pure math, no Claude)."""
    logger.info("=== PHASE 5: BRAND_CONVERTED Edge Construction ===")
    completed = checkpoint.load_completed("phase5")
    stats = {"edges_created": 0, "skipped_completed": 0}

    # Get all (product, review) pairs
    with driver.session() as session:
        pairs = session.run("""
            MATCH (pd:ProductDescription)-[:HAS_REVIEW]->(r:AnnotatedReview)
            WHERE r.annotation_confidence > 0
            RETURN pd.asin AS product_asin, r.review_id AS review_id
        """).data()

    logger.info(f"Found {len(pairs)} product-review pairs for edge construction")

    batch: list[dict[str, Any]] = []

    for pair in pairs:
        edge_id = f"{pair['product_asin']}_{pair['review_id']}"
        if edge_id in completed:
            stats["skipped_completed"] += 1
            continue

        # Fetch annotations
        with driver.session() as session:
            data = session.run("""
                MATCH (pd:ProductDescription {asin: $asin})
                MATCH (r:AnnotatedReview {review_id: $review_id})
                RETURN properties(pd) AS ad_props, properties(r) AS user_props
            """, asin=pair["product_asin"], review_id=pair["review_id"]).single()

        if not data:
            continue

        ad_props = data["ad_props"]
        user_props = data["user_props"]

        review_meta = {
            "rating": user_props.get("star_rating", 0),
            "helpful_vote": user_props.get("helpful_votes", 0),
            "text": "x" * user_props.get("text_length", 100),
            "category": ad_props.get("main_category", "All Beauty"),
        }

        edge_props = compute_brand_buyer_edge(ad_props, user_props, review_meta)

        batch.append({
            "product_asin": pair["product_asin"],
            "review_id": pair["review_id"],
            "properties": edge_props,
        })

        if len(batch) >= 200:
            writer.write_brand_converted_edges(batch)
            checkpoint.mark_batch_completed(
                "phase5", [f"{r['product_asin']}_{r['review_id']}" for r in batch]
            )
            stats["edges_created"] += len(batch)
            batch.clear()

            if stats["edges_created"] % 2000 == 0:
                logger.info(f"Phase 5: {stats['edges_created']} BRAND_CONVERTED edges")

    if batch:
        writer.write_brand_converted_edges(batch)
        checkpoint.mark_batch_completed(
            "phase5", [f"{r['product_asin']}_{r['review_id']}" for r in batch]
        )
        stats["edges_created"] += len(batch)

    logger.info(f"Phase 5 complete: {stats}")
    return stats


def run_phase_6(
    driver,
    writer: BulkWriter,
    checkpoint: CheckpointManager,
) -> dict[str, int]:
    """Phase 6: Compute PEER_INFLUENCED edges.

    For each product, link top-N helpful reviews (peer-ad-side) to
    subsequent buyer reviews (user-side) that came after them.
    """
    logger.info("=== PHASE 6: PEER_INFLUENCED Edge Construction ===")
    completed = checkpoint.load_completed("phase6")
    stats = {"edges_created": 0, "skipped_completed": 0}

    # Get products with peer-annotated reviews
    with driver.session() as session:
        products = session.run("""
            MATCH (pd:ProductDescription)-[:HAS_REVIEW]->(r:AnnotatedReview)
            WHERE r.peer_ad_annotation_confidence IS NOT NULL
              AND r.peer_ad_annotation_confidence > 0
            WITH pd.asin AS asin, collect({
                review_id: r.review_id,
                timestamp: r.timestamp,
                helpful_votes: r.helpful_votes,
                peer_ad_testimonial_authenticity: r.peer_ad_testimonial_authenticity,
                peer_ad_use_case_matching: r.peer_ad_use_case_matching,
                peer_ad_narrative_arc_completeness: r.peer_ad_narrative_arc_completeness,
                peer_ad_resolved_anxiety_narrative: r.peer_ad_resolved_anxiety_narrative,
                peer_ad_recommendation_strength: r.peer_ad_recommendation_strength
            }) AS peer_reviews
            WHERE size(peer_reviews) > 0
            RETURN asin, peer_reviews
        """).data()

    logger.info(f"Found {len(products)} products with peer-annotated reviews")

    batch: list[dict[str, Any]] = []

    for p in products:
        asin = p["asin"]
        peer_reviews = sorted(
            p["peer_reviews"],
            key=lambda x: x.get("helpful_votes", 0) or 0,
            reverse=True,
        )[:10]  # Top 10 peer reviews

        if not peer_reviews:
            continue

        # Get subsequent buyer reviews for this product
        earliest_peer_ts = min(
            pr.get("timestamp", 0) or 0 for pr in peer_reviews
        )

        with driver.session() as session:
            buyer_reviews = session.run("""
                MATCH (pd:ProductDescription {asin: $asin})-[:HAS_REVIEW]->(r:AnnotatedReview)
                WHERE r.timestamp > $earliest_ts
                  AND r.annotation_confidence > 0
                  AND NOT r.review_id IN $peer_ids
                RETURN r.review_id AS review_id, r.timestamp AS timestamp
            """,
                asin=asin,
                earliest_ts=earliest_peer_ts,
                peer_ids=[pr["review_id"] for pr in peer_reviews],
            ).data()

        for peer in peer_reviews:
            for buyer in buyer_reviews:
                # Only link if buyer came AFTER peer
                peer_ts = peer.get("timestamp", 0) or 0
                buyer_ts = buyer.get("timestamp", 0) or 0
                if buyer_ts <= peer_ts:
                    continue

                edge_id = f"{peer['review_id']}_{buyer['review_id']}"
                if edge_id in completed:
                    stats["skipped_completed"] += 1
                    continue

                # Compute influence weight based on helpful votes and recency
                helpful = peer.get("helpful_votes", 0) or 0
                influence = min(1.0, helpful / 100.0) * 0.7 + \
                    (peer.get("peer_ad_recommendation_strength", 0) or 0) * 0.3

                batch.append({
                    "peer_review_id": peer["review_id"],
                    "buyer_review_id": buyer["review_id"],
                    "properties": {
                        "influence_weight": round(influence, 4),
                        "peer_authenticity_resonance": round(
                            peer.get("peer_ad_testimonial_authenticity", 0) or 0, 4
                        ),
                        "risk_resolution_match": round(
                            peer.get("peer_ad_resolved_anxiety_narrative", 0) or 0, 4
                        ),
                        "narrative_resonance": round(
                            peer.get("peer_ad_narrative_arc_completeness", 0) or 0, 4
                        ),
                        "use_case_alignment": round(
                            peer.get("peer_ad_use_case_matching", 0) or 0, 4
                        ),
                        "star_rating": buyer.get("star_rating", 0),
                        "outcome": "satisfied",
                    },
                })

                if len(batch) >= 500:
                    writer.write_peer_influenced_edges(batch)
                    checkpoint.mark_batch_completed(
                        "phase6",
                        [f"{r['peer_review_id']}_{r['buyer_review_id']}" for r in batch],
                    )
                    stats["edges_created"] += len(batch)
                    batch.clear()

    if batch:
        writer.write_peer_influenced_edges(batch)
        checkpoint.mark_batch_completed(
            "phase6",
            [f"{r['peer_review_id']}_{r['buyer_review_id']}" for r in batch],
        )
        stats["edges_created"] += len(batch)

    logger.info(f"Phase 6 complete: {stats}")
    return stats


def run_phase_7(
    driver,
    writer: BulkWriter,
    checkpoint: CheckpointManager,
) -> dict[str, int]:
    """Phase 7: Compute ECOSYSTEM_CONVERTED edges."""
    logger.info("=== PHASE 7: ECOSYSTEM_CONVERTED Edge Construction ===")
    completed = checkpoint.load_completed("phase7")
    stats = {"edges_created": 0, "skipped_completed": 0}

    # Get ecosystem-review pairs
    with driver.session() as session:
        pairs = session.run("""
            MATCH (eco:ProductEcosystem)
            MATCH (pd:ProductDescription {asin: eco.asin})-[:HAS_REVIEW]->(r:AnnotatedReview)
            WHERE r.annotation_confidence > 0
            RETURN eco.asin AS product_asin, r.review_id AS review_id,
                   eco.eco_frame_coherence AS fc,
                   eco.eco_risk_coverage AS rc,
                   eco.eco_sp_density AS spd,
                   eco.eco_cialdini_coverage AS cc,
                   eco.eco_sp_diversity AS spdi,
                   eco.eco_authority_layers AS al,
                   r.star_rating AS star_rating
        """).data()

    logger.info(f"Found {len(pairs)} ecosystem-review pairs")

    batch: list[dict[str, Any]] = []
    for pair in pairs:
        edge_id = f"eco_{pair['product_asin']}_{pair['review_id']}"
        if edge_id in completed:
            stats["skipped_completed"] += 1
            continue

        batch.append({
            "product_asin": pair["product_asin"],
            "review_id": pair["review_id"],
            "properties": {
                "frame_coherence_at_time": pair.get("fc", 0) or 0,
                "risk_coverage_at_time": pair.get("rc", 0) or 0,
                "sp_density_at_time": pair.get("spd", 0) or 0,
                "cialdini_coverage_at_time": pair.get("cc", 0) or 0,
                "sp_diversity_at_time": pair.get("spdi", 0) or 0,
                "authority_layers_at_time": pair.get("al", 0) or 0,
                "star_rating": pair.get("star_rating", 0),
                "outcome": "satisfied",
            },
        })

        if len(batch) >= 500:
            writer.write_ecosystem_converted_edges(batch)
            checkpoint.mark_batch_completed(
                "phase7",
                [f"eco_{r['product_asin']}_{r['review_id']}" for r in batch],
            )
            stats["edges_created"] += len(batch)
            batch.clear()

            if stats["edges_created"] % 5000 == 0:
                logger.info(f"Phase 7: {stats['edges_created']} ECOSYSTEM_CONVERTED edges")

    if batch:
        writer.write_ecosystem_converted_edges(batch)
        checkpoint.mark_batch_completed(
            "phase7",
            [f"eco_{r['product_asin']}_{r['review_id']}" for r in batch],
        )
        stats["edges_created"] += len(batch)

    logger.info(f"Phase 7 complete: {stats}")
    return stats


def run_phase_8(
    driver,
) -> dict[str, int]:
    """Phase 8: Generate Bayesian priors from edges.

    Aggregate all three edge types into queryable prior distributions.
    """
    logger.info("=== PHASE 8: Bayesian Prior Generation ===")
    stats = {}

    with driver.session() as session:
        # 1. Category-level construct distributions
        logger.info("Computing category construct distributions...")
        session.run("""
            MATCH (pd:ProductDescription)-[e:BRAND_CONVERTED]->(r:AnnotatedReview)
            WITH pd.main_category AS category,
                 avg(e.regulatory_fit_score) AS avg_reg_fit,
                 avg(e.construal_fit_score) AS avg_constr_fit,
                 avg(e.personality_brand_alignment) AS avg_pers_align,
                 avg(e.emotional_resonance) AS avg_emo_res,
                 avg(e.value_alignment) AS avg_val_align,
                 avg(e.evolutionary_motive_match) AS avg_evo_match,
                 stDev(e.regulatory_fit_score) AS std_reg_fit,
                 stDev(e.construal_fit_score) AS std_constr_fit,
                 count(e) AS n_observations
            WHERE n_observations >= 5
            MERGE (prior:BayesianPrior {id: 'cat_' + coalesce(category, 'unknown')})
            SET prior.category = category,
                prior.prior_type = 'category_construct_distribution',
                prior.avg_regulatory_fit = avg_reg_fit,
                prior.avg_construal_fit = avg_constr_fit,
                prior.avg_personality_alignment = avg_pers_align,
                prior.avg_emotional_resonance = avg_emo_res,
                prior.avg_value_alignment = avg_val_align,
                prior.avg_evolutionary_motive_match = avg_evo_match,
                prior.std_regulatory_fit = std_reg_fit,
                prior.std_construal_fit = std_constr_fit,
                prior.n_observations = n_observations
        """)

        # 2. Mechanism effectiveness by profile type
        logger.info("Computing mechanism effectiveness priors...")
        session.run("""
            MATCH (pd:ProductDescription)-[e:BRAND_CONVERTED]->(r:AnnotatedReview)
            WHERE e.mech_social_proof IS NOT NULL
            WITH CASE
                   WHEN r.user_personality_extraversion > 0.6 THEN 'high_e'
                   WHEN r.user_personality_extraversion < 0.4 THEN 'low_e'
                   ELSE 'mid_e'
                 END AS profile_type,
                 avg(e.mech_social_proof) AS sp_eff,
                 avg(e.mech_authority) AS auth_eff,
                 avg(e.mech_scarcity) AS scar_eff,
                 count(e) AS n
            WHERE n >= 3
            MERGE (prior:BayesianPrior {id: 'mech_' + profile_type})
            SET prior.prior_type = 'mechanism_effectiveness',
                prior.profile_type = profile_type,
                prior.social_proof_effectiveness = sp_eff,
                prior.authority_effectiveness = auth_eff,
                prior.scarcity_effectiveness = scar_eff,
                prior.n_observations = n
        """)

        # 3. Brand vs peer effectiveness
        logger.info("Computing brand vs peer effectiveness priors...")
        session.run("""
            MATCH ()-[b:BRAND_CONVERTED]->()
            WITH avg(b.regulatory_fit_score) AS brand_avg_fit,
                 avg(b.personality_brand_alignment) AS brand_avg_align,
                 count(b) AS brand_n
            MATCH ()-[p:PEER_INFLUENCED]->()
            WITH brand_avg_fit, brand_avg_align, brand_n,
                 avg(p.influence_weight) AS peer_avg_influence,
                 avg(p.peer_authenticity_resonance) AS peer_avg_auth,
                 count(p) AS peer_n
            MERGE (prior:BayesianPrior {id: 'brand_vs_peer'})
            SET prior.prior_type = 'brand_vs_peer_effectiveness',
                prior.brand_avg_fit = brand_avg_fit,
                prior.brand_avg_alignment = brand_avg_align,
                prior.brand_n = brand_n,
                prior.peer_avg_influence = peer_avg_influence,
                prior.peer_avg_authenticity = peer_avg_auth,
                prior.peer_n = peer_n
        """)

        # Count priors created
        prior_count = session.run(
            "MATCH (p:BayesianPrior) RETURN count(p) AS cnt"
        ).single()["cnt"]
        stats["priors_created"] = prior_count

    logger.info(f"Phase 8 complete: {stats}")
    return stats


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================

def run_pipeline(
    reviews_path: str,
    products_path: str,
    neo4j_uri: str = "neo4j://127.0.0.1:7687",
    neo4j_user: str = "neo4j",
    neo4j_password: str = "atomofthought",
    checkpoint_dir: str = "checkpoints",
    phase1_limit: int | None = None,
    phase2_limit: int | None = None,
    skip_phases: set[int] | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Run the full 8-phase pipeline.

    Args:
        reviews_path: Path to All_Beauty.jsonl
        products_path: Path to meta_All_Beauty.jsonl
        neo4j_uri: Neo4j connection URI
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password
        checkpoint_dir: Directory for checkpoint files
        phase1_limit: Limit products to annotate (for testing)
        phase2_limit: Limit reviews to annotate (for testing)
        skip_phases: Set of phase numbers to skip
        api_key: Anthropic API key (or from env)
    """
    skip = skip_phases or set()
    all_stats: dict[str, Any] = {"start_time": time.time()}

    # Connect to Neo4j
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    logger.info(f"Connected to Neo4j at {neo4j_uri}")

    writer = BulkWriter(driver, batch_size=500)
    checkpoint = CheckpointManager(checkpoint_dir)

    # Phase 0
    if 0 not in skip:
        run_phase_0(driver, checkpoint_dir)

    # Phase 1
    if 1 not in skip:
        ad_annotator = AdSideAnnotator(api_key=api_key)
        all_stats["phase1"] = run_phase_1(
            products_path, ad_annotator, writer, checkpoint, limit=phase1_limit
        )
        all_stats["phase1_claude_stats"] = ad_annotator.stats
        logger.info(f"Phase 1 Claude stats: {ad_annotator.stats}")

    # Phase 2+3
    if 2 not in skip:
        product_index = load_product_index(products_path)
        dual_annotator = DualAnnotator(api_key=api_key)
        all_stats["phase2_3"] = run_phase_2_3(
            reviews_path, product_index, dual_annotator, writer, checkpoint,
            limit=phase2_limit,
        )
        all_stats["phase2_3_claude_stats"] = dual_annotator.stats
        logger.info(f"Phase 2+3 Claude stats: {dual_annotator.stats}")

    # Phase 4
    if 4 not in skip:
        all_stats["phase4"] = run_phase_4(driver, writer, checkpoint)

    # Phase 5
    if 5 not in skip:
        all_stats["phase5"] = run_phase_5(driver, writer, checkpoint)

    # Phase 6
    if 6 not in skip:
        all_stats["phase6"] = run_phase_6(driver, writer, checkpoint)

    # Phase 7
    if 7 not in skip:
        all_stats["phase7"] = run_phase_7(driver, writer, checkpoint)

    # Phase 8
    if 8 not in skip:
        all_stats["phase8"] = run_phase_8(driver)

    # Final stats
    all_stats["elapsed_s"] = time.time() - all_stats["start_time"]
    all_stats["neo4j_writer_stats"] = writer.stats

    driver.close()

    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info(f"Total time: {all_stats['elapsed_s']:.0f}s")
    logger.info(f"Writer stats: {writer.stats}")
    logger.info("=" * 60)

    return all_stats


def main():
    parser = argparse.ArgumentParser(description="ADAM Corpus Annotation Pipeline")
    parser.add_argument(
        "--reviews", required=True,
        help="Path to All_Beauty.jsonl",
    )
    parser.add_argument(
        "--products", required=True,
        help="Path to meta_All_Beauty.jsonl",
    )
    parser.add_argument("--neo4j-uri", default="neo4j://127.0.0.1:7687")
    parser.add_argument("--neo4j-user", default="neo4j")
    parser.add_argument("--neo4j-password", default="atomofthought")
    parser.add_argument("--checkpoint-dir", default="checkpoints")
    parser.add_argument(
        "--phase1-limit", type=int, default=None,
        help="Limit products to annotate (for testing)",
    )
    parser.add_argument(
        "--phase2-limit", type=int, default=None,
        help="Limit reviews to annotate (for testing)",
    )
    parser.add_argument(
        "--skip-phases", type=str, default="",
        help="Comma-separated phase numbers to skip (e.g., '1,2')",
    )
    parser.add_argument("--api-key", default=None, help="Anthropic API key")
    args = parser.parse_args()

    skip = set()
    if args.skip_phases:
        skip = {int(x.strip()) for x in args.skip_phases.split(",") if x.strip()}

    results = run_pipeline(
        reviews_path=args.reviews,
        products_path=args.products,
        neo4j_uri=args.neo4j_uri,
        neo4j_user=args.neo4j_user,
        neo4j_password=args.neo4j_password,
        checkpoint_dir=args.checkpoint_dir,
        phase1_limit=args.phase1_limit,
        phase2_limit=args.phase2_limit,
        skip_phases=skip,
        api_key=args.api_key,
    )

    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
