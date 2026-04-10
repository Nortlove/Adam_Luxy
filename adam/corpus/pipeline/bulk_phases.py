"""
Bulk computation of Phases 4-8 using batched Cypher + Python.

v2: Expanded edge computation (13 dimensions), peer-buyer matching,
    real outcome tracking, and multi-dimensional Bayesian priors.

Designed for 11M+ reviews at scale. Processes products in batches
instead of one-by-one, uses bulk Cypher where possible.
"""

from __future__ import annotations

import logging
import math
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from neo4j import GraphDatabase

from adam.corpus.edge_builders.match_calculators import (
    compute_brand_buyer_edge,
    compute_peer_buyer_edge,
)
from adam.corpus.neo4j.bulk_writer import BulkWriter
from adam.corpus.pipeline.checkpoint_manager import CheckpointManager

LOG_DIR = Path(__file__).parent.parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
for h in root_logger.handlers[:]:
    root_logger.removeHandler(h)

fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
fh = logging.FileHandler(str(LOG_DIR / "bulk_phases.log"), mode="a")
fh.setFormatter(fmt)
root_logger.addHandler(fh)
sh = logging.StreamHandler(sys.stderr)
sh.setFormatter(fmt)
root_logger.addHandler(sh)

logger = logging.getLogger("adam.corpus.bulk")
logging.getLogger("neo4j.notifications").setLevel(logging.WARNING)

NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "atomofthought"
CHECKPOINT_DIR = "checkpoints"


# =========================================================================
# PHASE 4: Product Ecosystems (batch Cypher) — unchanged
# =========================================================================

def run_phase_4_bulk(driver, ckpt: CheckpointManager):
    """Build ProductEcosystem nodes using batch Cypher aggregation."""
    logger.info("=" * 60)
    logger.info("PHASE 4: Product Ecosystems (bulk Cypher)")
    logger.info("=" * 60)

    completed = ckpt.load_completed("phase4")
    logger.info(f"Already completed: {len(completed):,} ecosystems")

    with driver.session() as session:
        products = session.run("""
            MATCH (pd:ProductDescription)-[:HAS_REVIEW]->(r:AnnotatedReview)
            WITH pd.asin AS asin, count(r) AS review_count
            WHERE review_count > 0
            RETURN asin, review_count
            ORDER BY review_count DESC
        """).data()

    to_process = [p for p in products if p["asin"] not in completed]
    logger.info(f"Products: {len(products):,} total, {len(to_process):,} to process")

    created = 0
    t0 = time.time()
    BATCH_SIZE = 500

    for i in range(0, len(to_process), BATCH_SIZE):
        batch_asins = [p["asin"] for p in to_process[i:i + BATCH_SIZE]]

        with driver.session() as session:
            session.run("""
                UNWIND $asins AS asin
                MATCH (pd:ProductDescription {asin: asin})-[:HAS_REVIEW]->(r:AnnotatedReview)
                WITH asin,
                     count(r) AS review_count,
                     avg(r.star_rating) AS avg_rating,
                     stdev(r.star_rating) AS std_rating,
                     min(coalesce(r.timestamp, 0)) AS earliest_ts,
                     max(coalesce(r.timestamp, 0)) AS latest_ts,
                     avg(CASE WHEN r.verified_purchase = true THEN 1.0 ELSE 0.0 END) AS verified_ratio,
                     avg(coalesce(r.user_emotion_pleasure, 0.5)) AS avg_pleasure,
                     avg(coalesce(r.user_emotion_arousal, 0.5)) AS avg_arousal,
                     avg(coalesce(r.user_regulatory_focus_promotion, 0.5)) AS avg_promotion,
                     avg(coalesce(r.user_regulatory_focus_prevention, 0.5)) AS avg_prevention,
                     avg(coalesce(r.user_personality_openness, 0.5)) AS avg_openness,
                     avg(coalesce(r.user_personality_conscientiousness, 0.5)) AS avg_conscientiousness,
                     avg(coalesce(r.user_personality_extraversion, 0.5)) AS avg_extraversion,
                     avg(coalesce(r.user_personality_agreeableness, 0.5)) AS avg_agreeableness,
                     avg(coalesce(r.user_personality_neuroticism, 0.5)) AS avg_neuroticism,
                     avg(coalesce(r.peer_ad_testimonial_authenticity, 0.0)) AS avg_authenticity,
                     avg(coalesce(r.peer_ad_social_proof_amplification, 0.0)) AS avg_sp_amp,
                     avg(coalesce(r.peer_ad_recommendation_strength, 0.0)) AS avg_rec_strength,
                     avg(coalesce(r.peer_ad_objection_preemption, 0.0)) AS avg_objection_pre,
                     sum(coalesce(r.helpful_votes, 0)) AS total_helpful

                MERGE (eco:ProductEcosystem {asin: asin})
                SET eco.eco_review_count = review_count,
                    eco.eco_avg_rating = round(avg_rating, 4),
                    eco.eco_std_rating = round(coalesce(std_rating, 0.0), 4),
                    eco.eco_earliest_ts = earliest_ts,
                    eco.eco_latest_ts = latest_ts,
                    eco.eco_verified_ratio = round(verified_ratio, 4),
                    eco.eco_frame_coherence = round(
                        CASE WHEN abs(avg_promotion - avg_prevention) < 1.0
                             THEN 1.0 - abs(avg_promotion - avg_prevention)
                             ELSE 0.0
                        END, 4),
                    eco.eco_sp_density = round(
                        avg_sp_amp * CASE WHEN review_count > 20 THEN 1.0
                                         ELSE toFloat(review_count) / 20.0
                                    END, 4),
                    eco.eco_sp_diversity = round(
                        CASE WHEN (abs(avg_openness - 0.5) + abs(avg_extraversion - 0.5) + abs(avg_agreeableness - 0.5)) / 1.5 > 1.0
                             THEN 1.0
                             ELSE (abs(avg_openness - 0.5) + abs(avg_extraversion - 0.5) + abs(avg_agreeableness - 0.5)) / 1.5
                        END, 4),
                    eco.eco_authority_layers = round(avg_authenticity, 4),
                    eco.eco_cialdini_coverage = round(
                        (CASE WHEN avg_sp_amp > 0.3 THEN 1.0 ELSE 0.0 END +
                         CASE WHEN avg_authenticity > 0.3 THEN 1.0 ELSE 0.0 END +
                         CASE WHEN avg_rec_strength > 0.3 THEN 1.0 ELSE 0.0 END +
                         CASE WHEN avg_objection_pre > 0.3 THEN 1.0 ELSE 0.0 END
                        ) / 4.0, 4),
                    eco.eco_temporal_arc = round(avg_pleasure, 4),
                    eco.eco_risk_coverage = round(avg_objection_pre, 4),
                    eco.eco_neg_review_resolution = round(
                        CASE WHEN avg_rec_strength * avg_rating / 5.0 > 0
                             THEN avg_rec_strength * avg_rating / 5.0
                             ELSE 0.0
                        END, 4)

                WITH eco, asin
                MATCH (pd:ProductDescription {asin: asin})
                MERGE (pd)-[:ANCHORS]->(eco)
            """, asins=batch_asins)

        ckpt.mark_batch_completed("phase4", batch_asins)
        created += len(batch_asins)

        if created % 2000 == 0 or created == len(to_process):
            rate = created / max(time.time() - t0, 1)
            eta = (len(to_process) - created) / max(rate, 1) / 60
            logger.info(f"Phase 4: {created:,}/{len(to_process):,} ({rate:.0f}/s, ETA {eta:.0f}min)")

    logger.info(f"Phase 4 done: {created:,} ecosystems created")


# =========================================================================
# PHASE 5: BRAND_CONVERTED edges (v2: 13-dimension alignment)
# =========================================================================

def run_phase_5_bulk(driver, writer: BulkWriter, ckpt: CheckpointManager):
    """Compute BRAND_CONVERTED edges using all ~108 annotated constructs."""
    logger.info("=" * 60)
    logger.info("PHASE 5: BRAND_CONVERTED Edges (v2 — 13 alignment dimensions)")
    logger.info("=" * 60)

    completed = ckpt.load_completed("phase5")
    logger.info(f"Already completed: {len(completed):,} edges")

    with driver.session() as session:
        claude_products = session.run("""
            MATCH (pd:ProductDescription)
            WHERE pd.annotation_tier IN ['claude', 'tier_1_batch_api', 'tier_1_claude_max']
              AND pd.ad_framing_gain IS NOT NULL
            RETURN pd.asin AS asin
        """).data()

    logger.info(f"Found {len(claude_products):,} Claude-annotated products for edge computation")

    total_edges = 0
    t0 = time.time()

    for idx, prod in enumerate(claude_products):
        asin = prod["asin"]

        with driver.session() as session:
            data = session.run("""
                MATCH (pd:ProductDescription {asin: $asin})-[:HAS_REVIEW]->(r:AnnotatedReview)
                WHERE r.annotation_confidence > 0
                RETURN properties(pd) AS ad_props,
                       r.review_id AS review_id,
                       properties(r) AS user_props
                LIMIT 500
            """, asin=asin).data()

        if not data:
            continue

        ad_props = data[0]["ad_props"]

        with driver.session() as session:
            stats_row = session.run("""
                MATCH (eco:ProductEcosystem {asin: $asin})
                RETURN eco.eco_avg_rating AS avg_rating,
                       eco.eco_std_rating AS std_rating,
                       eco.eco_earliest_ts AS earliest_ts,
                       eco.eco_latest_ts AS latest_ts
            """, asin=asin).single()
        product_stats = dict(stats_row) if stats_row else {}

        batch: list[dict[str, Any]] = []

        for row in data:
            review_id = row["review_id"]
            edge_id = f"{asin}_{review_id}"
            if edge_id in completed:
                continue

            user_props = row["user_props"]
            review_meta = {
                "rating": user_props.get("star_rating", 0),
                "helpful_vote": user_props.get("helpful_votes", 0),
                "text": "x" * (user_props.get("text_length", 100) or 100),
                "category": ad_props.get("main_category", "Beauty"),
                "timestamp": user_props.get("timestamp", 0),
                "verified_purchase": user_props.get("verified_purchase", True),
            }

            edge_props = compute_brand_buyer_edge(ad_props, user_props, review_meta, product_stats)
            batch.append({
                "product_asin": asin,
                "review_id": review_id,
                "properties": edge_props,
            })

        if batch:
            writer.write_brand_converted_edges(batch)
            ckpt.mark_batch_completed("phase5", [f"{asin}_{r['review_id']}" for r in batch])
            total_edges += len(batch)

        if (idx + 1) % 100 == 0:
            rate = total_edges / max(time.time() - t0, 1)
            logger.info(f"Phase 5: {idx+1}/{len(claude_products)} products, {total_edges:,} edges ({rate:.0f}/s)")

    logger.info(f"Phase 5 done: {total_edges:,} BRAND_CONVERTED edges created")


# =========================================================================
# PHASE 6: PEER_INFLUENCED edges (v2: buyer-side construct matching)
# =========================================================================

def run_phase_6_bulk(driver, writer: BulkWriter, ckpt: CheckpointManager):
    """Compute PEER_INFLUENCED edges with buyer-side psychological matching."""
    logger.info("=" * 60)
    logger.info("PHASE 6: PEER_INFLUENCED Edges (v2 — buyer matching)")
    logger.info("=" * 60)

    completed = ckpt.load_completed("phase6")

    with driver.session() as session:
        products = session.run("""
            MATCH (pd:ProductDescription)-[:HAS_REVIEW]->(r:AnnotatedReview)
            WHERE r.peer_ad_annotation_confidence IS NOT NULL
              AND r.peer_ad_annotation_confidence > 0
            WITH pd.asin AS asin, count(r) AS peer_count
            WHERE peer_count > 0
            RETURN asin, peer_count
            ORDER BY peer_count DESC
        """).data()

    logger.info(f"Found {len(products)} products with peer-annotated reviews")

    total_edges = 0
    t0 = time.time()

    for pidx, p in enumerate(products):
        asin = p["asin"]

        with driver.session() as session:
            peer_data = session.run("""
                MATCH (pd:ProductDescription {asin: $asin})-[:HAS_REVIEW]->(r:AnnotatedReview)
                WHERE r.peer_ad_annotation_confidence IS NOT NULL
                  AND r.peer_ad_annotation_confidence > 0
                RETURN r.review_id AS review_id,
                       r.timestamp AS timestamp,
                       properties(r) AS props
                ORDER BY coalesce(r.helpful_votes, 0) DESC
                LIMIT 10
            """, asin=asin).data()

        if not peer_data:
            continue

        with driver.session() as session:
            stats_row = session.run("""
                MATCH (eco:ProductEcosystem {asin: $asin})
                RETURN eco.eco_avg_rating AS avg_rating,
                       eco.eco_std_rating AS std_rating,
                       eco.eco_earliest_ts AS earliest_ts,
                       eco.eco_latest_ts AS latest_ts
            """, asin=asin).single()
        product_stats = dict(stats_row) if stats_row else {}

        peer_ids = [pr["review_id"] for pr in peer_data]
        earliest_ts = min((pr.get("timestamp") or 0) for pr in peer_data)

        with driver.session() as session:
            buyer_data = session.run("""
                MATCH (pd:ProductDescription {asin: $asin})-[:HAS_REVIEW]->(r:AnnotatedReview)
                WHERE r.timestamp > $earliest_ts
                  AND r.annotation_confidence > 0
                  AND NOT r.review_id IN $peer_ids
                RETURN r.review_id AS review_id,
                       r.timestamp AS timestamp,
                       properties(r) AS props
                LIMIT 50
            """, asin=asin, earliest_ts=earliest_ts, peer_ids=peer_ids).data()

        batch: list[dict[str, Any]] = []
        for peer_row in peer_data:
            peer_props = peer_row["props"]
            peer_ts = peer_row.get("timestamp") or 0

            for buyer_row in buyer_data:
                buyer_ts = buyer_row.get("timestamp") or 0
                if buyer_ts <= peer_ts:
                    continue

                edge_id = f"{peer_row['review_id']}_{buyer_row['review_id']}"
                if edge_id in completed:
                    continue

                buyer_props = buyer_row["props"]
                peer_meta = {
                    "helpful_votes": peer_props.get("helpful_votes", 0) or 0,
                    "timestamp": peer_props.get("timestamp", 0) or 0,
                    "verified_purchase": peer_props.get("verified_purchase", True),
                }

                edge_props = compute_peer_buyer_edge(peer_props, buyer_props, peer_meta, product_stats)
                batch.append({
                    "peer_review_id": peer_row["review_id"],
                    "buyer_review_id": buyer_row["review_id"],
                    "properties": edge_props,
                })

        if batch:
            writer.write_peer_influenced_edges(batch)
            ckpt.mark_batch_completed(
                "phase6",
                [f"{r['peer_review_id']}_{r['buyer_review_id']}" for r in batch],
            )
            total_edges += len(batch)

        if (pidx + 1) % 50 == 0:
            logger.info(f"Phase 6: {pidx+1}/{len(products)} products, {total_edges:,} edges")

    logger.info(f"Phase 6 done: {total_edges:,} PEER_INFLUENCED edges")


# =========================================================================
# PHASE 7: ECOSYSTEM_CONVERTED edges (v2: real outcome derivation)
# =========================================================================

def run_phase_7_bulk(driver, ckpt: CheckpointManager):
    """Compute ECOSYSTEM_CONVERTED edges with real outcome tracking."""
    logger.info("=" * 60)
    logger.info("PHASE 7: ECOSYSTEM_CONVERTED Edges (v2 — real outcomes)")
    logger.info("=" * 60)

    with driver.session() as session:
        eco_count = session.run("MATCH (e:ProductEcosystem) RETURN count(e) AS c").single()["c"]
    logger.info(f"Found {eco_count:,} ecosystems")

    if eco_count == 0:
        logger.warning("No ecosystems — skipping Phase 7")
        return

    with driver.session() as session:
        eco_asins = [r["asin"] for r in session.run(
            "MATCH (e:ProductEcosystem) RETURN e.asin AS asin"
        ).data()]

    completed = ckpt.load_completed("phase7")
    to_process = [a for a in eco_asins if a not in completed]
    logger.info(f"To process: {len(to_process):,} ecosystems")

    total = 0
    t0 = time.time()
    batch_asins: list[str] = []

    for idx, asin in enumerate(to_process):
        with driver.session() as session:
            result = session.run("""
                MATCH (eco:ProductEcosystem {asin: $asin})
                MATCH (pd:ProductDescription {asin: $asin})-[:HAS_REVIEW]->(r:AnnotatedReview)
                WHERE r.annotation_confidence > 0
                WITH eco, r,
                     eco.eco_frame_coherence AS fc,
                     eco.eco_risk_coverage AS rc,
                     eco.eco_sp_density AS spd,
                     eco.eco_cialdini_coverage AS cc,
                     eco.eco_sp_diversity AS spdi,
                     eco.eco_authority_layers AS al,
                     CASE
                         WHEN r.user_conversion_outcome IS NOT NULL THEN r.user_conversion_outcome
                         WHEN coalesce(r.star_rating, 3) >= 4 THEN 'satisfied'
                         WHEN coalesce(r.star_rating, 3) <= 2 THEN 'regret'
                         ELSE 'neutral'
                     END AS derived_outcome
                CREATE (eco)-[:ECOSYSTEM_CONVERTED {
                    frame_coherence_at_time: coalesce(fc, 0),
                    risk_coverage_at_time: coalesce(rc, 0),
                    sp_density_at_time: coalesce(spd, 0),
                    cialdini_coverage_at_time: coalesce(cc, 0),
                    sp_diversity_at_time: coalesce(spdi, 0),
                    authority_layers_at_time: coalesce(al, 0),
                    star_rating: coalesce(r.star_rating, 0),
                    outcome: derived_outcome
                }]->(r)
                RETURN count(*) AS edges
            """, asin=asin).single()

        edge_count = result["edges"] if result else 0
        total += edge_count
        batch_asins.append(asin)

        if len(batch_asins) >= 100:
            ckpt.mark_batch_completed("phase7", batch_asins)
            batch_asins.clear()

        if (idx + 1) % 2000 == 0 or idx + 1 == len(to_process):
            rate = total / max(time.time() - t0, 1)
            logger.info(f"Phase 7: {idx+1:,}/{len(to_process):,} ecosystems, {total:,} edges")

    if batch_asins:
        ckpt.mark_batch_completed("phase7", batch_asins)

    logger.info(f"Phase 7 done: {total:,} ECOSYSTEM_CONVERTED edges")


# =========================================================================
# PHASE 8: Bayesian Priors (v2: multi-dimensional segmentation)
# =========================================================================

BIG_FIVE_DIMS = [
    ("openness", "user_personality_openness"),
    ("conscientiousness", "user_personality_conscientiousness"),
    ("extraversion", "user_personality_extraversion"),
    ("agreeableness", "user_personality_agreeableness"),
    ("neuroticism", "user_personality_neuroticism"),
]


def run_phase_8_bulk(driver):
    """Generate expanded Bayesian priors: category, Big Five x mechanism, outcome-stratified."""
    logger.info("=" * 60)
    logger.info("PHASE 8: Bayesian Priors (v2 — multi-dimensional)")
    logger.info("=" * 60)

    with driver.session() as session:

        # ── 1. Category-level construct distributions (expanded with new dimensions) ──
        logger.info("Computing category construct distributions (13 dimensions)...")
        session.run("""
            MATCH (pd:ProductDescription)-[e:BRAND_CONVERTED]->(r:AnnotatedReview)
            WITH pd.main_category AS category,
                 avg(e.regulatory_fit_score) AS avg_reg_fit,
                 avg(e.construal_fit_score) AS avg_constr_fit,
                 avg(e.personality_brand_alignment) AS avg_pers_align,
                 avg(e.emotional_resonance) AS avg_emo_res,
                 avg(e.value_alignment) AS avg_val_align,
                 avg(e.evolutionary_motive_match) AS avg_evo_match,
                 avg(e.appeal_resonance) AS avg_appeal_res,
                 avg(e.processing_route_match) AS avg_proc_match,
                 avg(e.implicit_driver_match) AS avg_impl_match,
                 avg(e.lay_theory_alignment) AS avg_lay_align,
                 avg(e.linguistic_style_match) AS avg_ling_match,
                 avg(e.identity_signaling_match) AS avg_id_match,
                 avg(e.full_cosine_alignment) AS avg_cosine,
                 avg(e.composite_alignment) AS avg_composite,
                 stDev(e.composite_alignment) AS std_composite,
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
                prior.avg_appeal_resonance = avg_appeal_res,
                prior.avg_processing_route_match = avg_proc_match,
                prior.avg_implicit_driver_match = avg_impl_match,
                prior.avg_lay_theory_alignment = avg_lay_align,
                prior.avg_linguistic_style_match = avg_ling_match,
                prior.avg_identity_signaling_match = avg_id_match,
                prior.avg_full_cosine_alignment = avg_cosine,
                prior.avg_composite_alignment = avg_composite,
                prior.std_composite_alignment = std_composite,
                prior.n_observations = n_observations
        """)

        # ── 2. Mechanism effectiveness by ALL Big Five dimensions ──
        logger.info("Computing mechanism effectiveness by all Big Five dimensions...")
        for dim_name, dim_prop in BIG_FIVE_DIMS:
            session.run(f"""
                MATCH (pd:ProductDescription)-[e:BRAND_CONVERTED]->(r:AnnotatedReview)
                WHERE e.mech_social_proof IS NOT NULL
                WITH CASE
                       WHEN r.{dim_prop} > 0.6 THEN 'high'
                       WHEN r.{dim_prop} < 0.4 THEN 'low'
                       ELSE 'mid'
                     END AS level,
                     avg(e.mech_social_proof) AS avg_sp,
                     avg(e.mech_authority) AS avg_auth,
                     avg(e.mech_scarcity) AS avg_scar,
                     avg(e.mech_reciprocity) AS avg_recip,
                     avg(e.mech_commitment) AS avg_commit,
                     avg(e.mech_liking) AS avg_liking,
                     avg(e.composite_alignment) AS avg_composite,
                     count(*) AS n
                WHERE n >= 3
                MERGE (prior:BayesianPrior {{id: 'mech_{dim_name}_' + level}})
                SET prior.prior_type = 'mechanism_effectiveness',
                    prior.personality_dimension = '{dim_name}',
                    prior.personality_level = level,
                    prior.personality_profile = '{dim_name}_' + level,
                    prior.avg_social_proof = avg_sp,
                    prior.avg_authority = avg_auth,
                    prior.avg_scarcity = avg_scar,
                    prior.avg_reciprocity = avg_recip,
                    prior.avg_commitment = avg_commit,
                    prior.avg_liking = avg_liking,
                    prior.avg_composite_alignment = avg_composite,
                    prior.n_observations = n
            """)
            logger.info(f"  Mechanism priors for {dim_name}: done")

        # ── 3. Outcome-stratified priors ──
        logger.info("Computing outcome-stratified priors...")
        session.run("""
            MATCH (pd:ProductDescription)-[e:BRAND_CONVERTED]->(r:AnnotatedReview)
            WHERE e.outcome IS NOT NULL
            WITH e.outcome AS outcome,
                 avg(e.composite_alignment) AS avg_composite,
                 avg(e.personality_brand_alignment) AS avg_pers_align,
                 avg(e.emotional_resonance) AS avg_emo_res,
                 avg(e.appeal_resonance) AS avg_appeal,
                 avg(e.regulatory_fit_score) AS avg_reg_fit,
                 avg(e.processing_route_match) AS avg_proc,
                 stDev(e.composite_alignment) AS std_composite,
                 count(e) AS n
            WHERE n >= 3
            MERGE (prior:BayesianPrior {id: 'outcome_' + outcome})
            SET prior.prior_type = 'outcome_stratified',
                prior.outcome = outcome,
                prior.avg_composite_alignment = avg_composite,
                prior.avg_personality_alignment = avg_pers_align,
                prior.avg_emotional_resonance = avg_emo_res,
                prior.avg_appeal_resonance = avg_appeal,
                prior.avg_regulatory_fit = avg_reg_fit,
                prior.avg_processing_route_match = avg_proc,
                prior.std_composite_alignment = std_composite,
                prior.n_observations = n
        """)

        # ── 4. Category x Big Five composite priors ──
        logger.info("Computing category x Big Five composite priors...")
        for dim_name, dim_prop in BIG_FIVE_DIMS:
            session.run(f"""
                MATCH (pd:ProductDescription)-[e:BRAND_CONVERTED]->(r:AnnotatedReview)
                WHERE e.composite_alignment IS NOT NULL
                WITH pd.main_category AS category,
                     CASE
                       WHEN r.{dim_prop} > 0.6 THEN 'high'
                       WHEN r.{dim_prop} < 0.4 THEN 'low'
                       ELSE 'mid'
                     END AS level,
                     avg(e.composite_alignment) AS avg_composite,
                     avg(e.personality_brand_alignment) AS avg_pers,
                     count(e) AS n
                WHERE n >= 3
                MERGE (prior:BayesianPrior {{id: 'cat_bf_' + coalesce(category, 'unknown') + '_{dim_name}_' + level}})
                SET prior.prior_type = 'category_personality_composite',
                    prior.category = category,
                    prior.personality_dimension = '{dim_name}',
                    prior.personality_level = level,
                    prior.avg_composite_alignment = avg_composite,
                    prior.avg_personality_alignment = avg_pers,
                    prior.n_observations = n
            """)

        # ── 5. Peer influence effectiveness (expanded) ──
        logger.info("Computing peer influence priors...")
        session.run("""
            MATCH ()-[p:PEER_INFLUENCED]->()
            WITH avg(p.influence_weight) AS avg_influence,
                 avg(p.peer_authenticity_resonance) AS avg_auth,
                 avg(p.narrative_resonance) AS avg_narr,
                 avg(p.use_case_match) AS avg_ucm,
                 avg(p.anxiety_resolution_match) AS avg_anxiety,
                 avg(p.sp_resonance) AS avg_sp,
                 avg(p.expertise_resonance) AS avg_expert,
                 avg(p.emotional_contagion) AS avg_emo,
                 avg(p.composite_peer_alignment) AS avg_composite,
                 count(*) AS n
            WHERE n >= 1
            MERGE (prior:BayesianPrior {id: 'peer_global'})
            SET prior.prior_type = 'peer_influence_global',
                prior.avg_influence_weight = avg_influence,
                prior.avg_authenticity_resonance = avg_auth,
                prior.avg_narrative_resonance = avg_narr,
                prior.avg_use_case_match = avg_ucm,
                prior.avg_anxiety_resolution = avg_anxiety,
                prior.avg_sp_resonance = avg_sp,
                prior.avg_expertise_resonance = avg_expert,
                prior.avg_emotional_contagion = avg_emo,
                prior.avg_composite_peer_alignment = avg_composite,
                prior.n_observations = n
        """)

        # ── 6. Ecosystem-level priors ──
        logger.info("Computing ecosystem priors...")
        session.run("""
            MATCH (eco:ProductEcosystem)
            WITH avg(eco.eco_frame_coherence) AS avg_fc,
                 avg(eco.eco_sp_density) AS avg_spd,
                 avg(eco.eco_cialdini_coverage) AS avg_cc,
                 avg(eco.eco_authority_layers) AS avg_al,
                 avg(eco.eco_risk_coverage) AS avg_rc,
                 stDev(eco.eco_frame_coherence) AS std_fc,
                 count(*) AS n
            WHERE n >= 1
            MERGE (prior:BayesianPrior {id: 'ecosystem_global'})
            SET prior.prior_type = 'ecosystem_distribution',
                prior.avg_frame_coherence = avg_fc,
                prior.avg_sp_density = avg_spd,
                prior.avg_cialdini_coverage = avg_cc,
                prior.avg_authority_layers = avg_al,
                prior.avg_risk_coverage = avg_rc,
                prior.std_frame_coherence = std_fc,
                prior.n_observations = n
        """)

        count = session.run("MATCH (p:BayesianPrior) RETURN count(p) AS c").single()["c"]
        logger.info(f"Phase 8 done: {count} Bayesian priors created")


# =========================================================================
# MAIN
# =========================================================================

def main():
    t0 = time.time()
    logger.info("=" * 60)
    logger.info("BULK PHASES 4-8 v2 — Ecosystems, Edges, Priors")
    logger.info("=" * 60)

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    writer = BulkWriter(driver, batch_size=500)
    ckpt = CheckpointManager(CHECKPOINT_DIR)

    with driver.session() as session:
        for label in ["ProductDescription", "AnnotatedReview", "Reviewer"]:
            c = session.run(f"MATCH (n:{label}) RETURN count(n) AS c").single()["c"]
            logger.info(f"  {label}: {c:,}")

    run_phase_4_bulk(driver, ckpt)
    run_phase_5_bulk(driver, writer, ckpt)
    run_phase_6_bulk(driver, writer, ckpt)
    run_phase_7_bulk(driver, ckpt)
    run_phase_8_bulk(driver)

    logger.info("=" * 60)
    logger.info("FINAL GRAPH STATS")
    logger.info("=" * 60)
    with driver.session() as session:
        for label in ["ProductDescription", "AnnotatedReview", "Reviewer",
                       "ProductEcosystem", "BayesianPrior", "Domain", "Construct"]:
            c = session.run(f"MATCH (n:{label}) RETURN count(n) AS c").single()["c"]
            logger.info(f"  {label}: {c:,}")
        for rel in ["HAS_REVIEW", "AUTHORED", "BRAND_CONVERTED",
                     "PEER_INFLUENCED", "ECOSYSTEM_CONVERTED", "ANCHORS"]:
            c = session.run(f"MATCH ()-[r:{rel}]->() RETURN count(r) AS c").single()["c"]
            logger.info(f"  {rel}: {c:,}")

    driver.close()
    elapsed = time.time() - t0
    logger.info(f"All phases complete in {elapsed:.0f}s ({elapsed/60:.1f}min)")


if __name__ == "__main__":
    main()
