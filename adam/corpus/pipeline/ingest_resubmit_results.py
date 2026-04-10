"""
Ingest completed resubmission batch results into Neo4j.

Overlays Claude annotations on existing product/review nodes,
then recomputes BRAND_CONVERTED edges and priors.
"""

from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import anthropic
from neo4j import GraphDatabase

from adam.corpus.pipeline.batch_api import stream_results
from adam.corpus.models.ad_side_annotation import AdSideAnnotation
from adam.corpus.models.user_side_annotation import UserSideAnnotation
from adam.corpus.models.peer_ad_annotation import PeerAdSideAnnotation
from adam.corpus.neo4j.bulk_writer import BulkWriter
from adam.corpus.edge_builders.match_calculators import compute_brand_buyer_edge

LOG_DIR = Path(__file__).parent.parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
for h in root_logger.handlers[:]:
    root_logger.removeHandler(h)

fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
fh = logging.FileHandler(str(LOG_DIR / "ingest_resub.log"), mode="a")
fh.setFormatter(fmt)
root_logger.addHandler(fh)
sh = logging.StreamHandler(sys.stderr)
sh.setFormatter(fmt)
root_logger.addHandler(sh)

logger = logging.getLogger("adam.corpus.ingest_resub")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)
logging.getLogger("neo4j.notifications").setLevel(logging.WARNING)

NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "atomofthought"


def ingest_product_results(client: anthropic.Anthropic, batch_ids: list[str], driver):
    """Overlay Claude product annotations on existing ProductDescription nodes."""
    logger.info("=" * 60)
    logger.info("STEP 1: Ingest product batch results")
    logger.info("=" * 60)

    annotated = 0
    errors = 0

    for bid in batch_ids:
        logger.info(f"Reading product batch {bid}...")
        batch: list[dict] = []

        for custom_id, result in stream_results(client, bid):
            pid = custom_id.replace("prod_", "", 1)

            if not result:
                errors += 1
                continue

            try:
                ann = AdSideAnnotation(asin=pid, **result)
                flat = ann.to_flat_dict()
                flat["annotation_tier"] = "claude"
                flat["annotation_confidence"] = flat.get("annotation_confidence", 0.8)
                annotated += 1
            except Exception as e:
                errors += 1
                continue

            batch.append({"asin": pid, "flat": flat})

            if len(batch) >= 500:
                _write_product_overlays(driver, batch)
                batch.clear()
                if annotated % 5000 == 0:
                    logger.info(f"  Products: {annotated:,} annotated, {errors:,} errors")

        if batch:
            _write_product_overlays(driver, batch)

    logger.info(f"Product ingestion done: {annotated:,} annotated, {errors:,} errors")
    return annotated


def _write_product_overlays(driver, batch: list[dict]):
    """Overlay Claude annotations onto existing ProductDescription nodes."""
    with driver.session() as session:
        for item in batch:
            asin = item["asin"]
            flat = item["flat"]
            # Build SET clause dynamically
            set_parts = []
            params = {"asin": asin}
            for k, v in flat.items():
                if v is not None and not isinstance(v, (list, dict)):
                    param_name = f"p_{k}"
                    set_parts.append(f"pd.{k} = ${param_name}")
                    params[param_name] = v

            if set_parts:
                query = f"MATCH (pd:ProductDescription {{asin: $asin}}) SET {', '.join(set_parts)}"
                session.run(query, **params)


def ingest_review_results(client: anthropic.Anthropic, batch_ids: list[str], driver):
    """Overlay Claude review annotations on existing AnnotatedReview nodes."""
    logger.info("=" * 60)
    logger.info("STEP 2: Ingest review batch results")
    logger.info("=" * 60)

    annotated = 0
    errors = 0
    skipped = 0

    for bid in batch_ids:
        logger.info(f"Reading review batch {bid}...")

        for custom_id, result in stream_results(client, bid):
            if not result:
                errors += 1
                continue

            review_id = custom_id.replace("rev_", "", 1)

            try:
                user_data = result.get("user_side", {})
                peer_data = result.get("peer_ad_side", {})
                conversion = result.get("conversion_outcome", "satisfied")

                user_ann = UserSideAnnotation(
                    review_id=review_id,
                    conversion_outcome=conversion,
                    **user_data,
                )
                user_flat = user_ann.to_flat_dict()
                user_flat["annotation_tier"] = "claude"

                peer_flat = {}
                if peer_data:
                    peer_ann = PeerAdSideAnnotation(review_id=review_id, **peer_data)
                    peer_flat = peer_ann.to_flat_dict()

                annotated += 1
            except Exception as e:
                errors += 1
                continue

            # Overlay on existing node
            all_props = {**user_flat, **peer_flat}
            _write_review_overlay(driver, review_id, all_props)

            if annotated % 2000 == 0:
                logger.info(f"  Reviews: {annotated:,} annotated, {errors:,} errors")

    logger.info(f"Review ingestion done: {annotated:,} annotated, {errors:,} errors")
    return annotated


def _write_review_overlay(driver, review_id: str, flat: dict):
    """Overlay Claude annotations onto existing AnnotatedReview node."""
    with driver.session() as session:
        set_parts = []
        params = {"review_id": review_id}
        for k, v in flat.items():
            if v is not None and not isinstance(v, (list, dict)):
                param_name = f"p_{k}"
                set_parts.append(f"r.{k} = ${param_name}")
                params[param_name] = v

        if set_parts:
            query = f"MATCH (r:AnnotatedReview {{review_id: $review_id}}) SET {', '.join(set_parts)}"
            session.run(query, **params)


def recompute_brand_edges(driver, writer: BulkWriter):
    """Recompute BRAND_CONVERTED edges for ALL Claude-annotated products."""
    logger.info("=" * 60)
    logger.info("STEP 3: Recompute BRAND_CONVERTED edges (all Claude products)")
    logger.info("=" * 60)

    # First delete old edges to recompute cleanly
    with driver.session() as session:
        old_count = session.run("MATCH ()-[e:BRAND_CONVERTED]->() RETURN count(e) AS c").single()["c"]
        logger.info(f"Deleting {old_count:,} existing BRAND_CONVERTED edges...")
        # Delete in batches to avoid OOM
        while True:
            result = session.run("""
                MATCH ()-[e:BRAND_CONVERTED]->()
                WITH e LIMIT 50000
                DELETE e
                RETURN count(*) AS deleted
            """).single()["deleted"]
            if result == 0:
                break
            logger.info(f"  Deleted batch of {result:,}")

    # Get all Claude-annotated products
    with driver.session() as session:
        claude_products = session.run("""
            MATCH (pd:ProductDescription)
            WHERE pd.annotation_tier IN ['claude', 'tier_1_batch_api', 'tier_1_claude_max']
              AND pd.ad_framing_gain IS NOT NULL
            RETURN pd.asin AS asin
        """).data()

    logger.info(f"Found {len(claude_products):,} Claude-annotated products")

    total_edges = 0
    t0 = time.time()

    for idx, prod in enumerate(claude_products):
        asin = prod["asin"]

        # Get product + reviews (limit to 200 per product for speed)
        with driver.session() as session:
            data = session.run("""
                MATCH (pd:ProductDescription {asin: $asin})-[:HAS_REVIEW]->(r:AnnotatedReview)
                WHERE r.annotation_confidence > 0
                RETURN properties(pd) AS ad_props,
                       r.review_id AS review_id,
                       properties(r) AS user_props
                LIMIT 200
            """, asin=asin).data()

        if not data:
            continue

        ad_props = data[0]["ad_props"]
        batch: list[dict[str, Any]] = []

        for row in data:
            user_props = row["user_props"]
            review_meta = {
                "rating": user_props.get("star_rating", 0),
                "helpful_vote": user_props.get("helpful_votes", 0),
                "text": "x" * (user_props.get("text_length", 100) or 100),
                "category": ad_props.get("main_category", "Beauty"),
            }

            edge_props = compute_brand_buyer_edge(ad_props, user_props, review_meta)
            batch.append({
                "product_asin": asin,
                "review_id": row["review_id"],
                "properties": edge_props,
            })

        if batch:
            writer.write_brand_converted_edges(batch)
            total_edges += len(batch)

        if (idx + 1) % 1000 == 0:
            rate = total_edges / max(time.time() - t0, 1)
            eta = (len(claude_products) - idx - 1) * (time.time() - t0) / max(idx + 1, 1) / 60
            logger.info(f"  {idx+1:,}/{len(claude_products):,} products, {total_edges:,} edges ({rate:.0f}/s, ETA {eta:.0f}min)")

    elapsed = time.time() - t0
    logger.info(f"BRAND_CONVERTED edges done: {total_edges:,} in {elapsed:.0f}s")
    return total_edges


def recompute_priors(driver):
    """Recompute Bayesian priors from the new edges."""
    logger.info("=" * 60)
    logger.info("STEP 4: Recompute Bayesian Priors")
    logger.info("=" * 60)

    with driver.session() as session:
        # Clear old priors
        session.run("MATCH (p:BayesianPrior) DETACH DELETE p")

        # Category-level construct distributions
        logger.info("Computing category priors...")
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
                 stDev(e.personality_brand_alignment) AS std_pers,
                 stDev(e.emotional_resonance) AS std_emo,
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
                prior.std_personality_alignment = std_pers,
                prior.std_emotional_resonance = std_emo,
                prior.n_observations = n_observations
        """)

        # Mechanism effectiveness by personality
        logger.info("Computing mechanism priors...")
        session.run("""
            MATCH (pd:ProductDescription)-[e:BRAND_CONVERTED]->(r:AnnotatedReview)
            WHERE e.mech_social_proof IS NOT NULL OR e.mech_authority IS NOT NULL
            WITH CASE
                   WHEN r.user_personality_extraversion > 0.6 THEN 'high_extraversion'
                   WHEN r.user_personality_extraversion < 0.4 THEN 'low_extraversion'
                   ELSE 'mid_extraversion'
                 END AS profile,
                 avg(e.mech_social_proof) AS avg_sp,
                 avg(e.mech_authority) AS avg_auth,
                 avg(e.mech_scarcity) AS avg_scar,
                 avg(e.mech_reciprocity) AS avg_recip,
                 count(*) AS n
            WHERE n >= 3
            MERGE (prior:BayesianPrior {id: 'mech_' + profile})
            SET prior.prior_type = 'mechanism_effectiveness',
                prior.personality_profile = profile,
                prior.avg_social_proof = avg_sp,
                prior.avg_authority = avg_auth,
                prior.avg_scarcity = avg_scar,
                prior.avg_reciprocity = avg_recip,
                prior.n_observations = n
        """)

        # Outcome prediction priors
        logger.info("Computing outcome priors...")
        session.run("""
            MATCH (pd:ProductDescription)-[e:BRAND_CONVERTED]->(r:AnnotatedReview)
            WHERE e.outcome IS NOT NULL
            WITH e.outcome AS outcome,
                 avg(e.regulatory_fit_score) AS avg_reg,
                 avg(e.personality_brand_alignment) AS avg_pers,
                 avg(e.emotional_resonance) AS avg_emo,
                 avg(e.value_alignment) AS avg_val,
                 count(*) AS n
            WHERE n >= 10
            MERGE (prior:BayesianPrior {id: 'outcome_' + outcome})
            SET prior.prior_type = 'outcome_prediction',
                prior.outcome = outcome,
                prior.avg_regulatory_fit = avg_reg,
                prior.avg_personality_alignment = avg_pers,
                prior.avg_emotional_resonance = avg_emo,
                prior.avg_value_alignment = avg_val,
                prior.n_observations = n
        """)

        # Peer influence global
        logger.info("Computing peer influence priors...")
        session.run("""
            MATCH ()-[p:PEER_INFLUENCED]->()
            WITH avg(p.influence_weight) AS avg_influence,
                 avg(p.peer_authenticity_resonance) AS avg_auth,
                 avg(p.narrative_resonance) AS avg_narr,
                 avg(p.use_case_match) AS avg_uca,
                 count(*) AS n
            WHERE n >= 1
            MERGE (prior:BayesianPrior {id: 'peer_global'})
            SET prior.prior_type = 'peer_influence_global',
                prior.avg_influence_weight = avg_influence,
                prior.avg_authenticity_resonance = avg_auth,
                prior.avg_narrative_resonance = avg_narr,
                prior.avg_use_case_alignment = avg_uca,
                prior.n_observations = n
        """)

        # Ecosystem priors
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
        logger.info(f"Priors done: {count} created")


def main():
    t0 = time.time()
    logger.info("=" * 60)
    logger.info("INGEST RESUBMISSION RESULTS + RECOMPUTE EDGES")
    logger.info("=" * 60)

    client = anthropic.Anthropic()
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    writer = BulkWriter(driver, batch_size=500)

    # Load batch IDs
    batch_file = Path("checkpoints/resubmit_batch_ids.txt").read_text().strip().split("\n")
    prod_batches = [line.split(":")[1] for line in batch_file if line.startswith("prod:")]
    rev_batches = [line.split(":")[1] for line in batch_file if line.startswith("rev:")]

    # Step 1: Ingest product annotations
    n_products = ingest_product_results(client, prod_batches, driver)

    # Step 2: Ingest review annotations
    n_reviews = ingest_review_results(client, rev_batches, driver)

    # Step 3: Recompute BRAND_CONVERTED edges
    n_edges = recompute_brand_edges(driver, writer)

    # Step 4: Recompute priors
    recompute_priors(driver)

    # Final stats
    logger.info("=" * 60)
    logger.info("FINAL GRAPH STATS")
    logger.info("=" * 60)
    with driver.session() as session:
        for label in ["ProductDescription", "AnnotatedReview", "Reviewer",
                       "ProductEcosystem", "BayesianPrior"]:
            c = session.run(f"MATCH (n:{label}) RETURN count(n) AS c").single()["c"]
            logger.info(f"  {label}: {c:,}")

        # Count Claude-annotated specifically
        claude_p = session.run("""
            MATCH (pd:ProductDescription)
            WHERE pd.annotation_tier IN ['claude', 'tier_1_batch_api', 'tier_1_claude_max'] AND pd.ad_framing_gain IS NOT NULL
            RETURN count(pd) AS c
        """).single()["c"]
        logger.info(f"  Claude-annotated products: {claude_p:,}")

        for rel in ["BRAND_CONVERTED", "PEER_INFLUENCED", "ECOSYSTEM_CONVERTED"]:
            c = session.run(f"MATCH ()-[r:{rel}]->() RETURN count(r) AS c").single()["c"]
            logger.info(f"  {rel}: {c:,}")

    driver.close()
    elapsed = time.time() - t0
    logger.info(f"Complete in {elapsed:.0f}s ({elapsed/60:.1f}min)")


if __name__ == "__main__":
    main()
