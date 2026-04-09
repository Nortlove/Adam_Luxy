#!/usr/bin/env python3
# =============================================================================
# Neo4j Seed Script — LUXY Ride Pilot
# =============================================================================
#
# Bootstraps Neo4j with all data needed for the LUXY Ride campaign:
#   1. Core schema constraints and indexes
#   2. Mechanism and personality seed data
#   3. LUXY Ride bilateral edges (1,492 edges → BRAND_CONVERTED relationships)
#   4. Archetype priors from bilateral edge analysis
#   5. Gradient field computation
#
# Usage:
#   PYTHONPATH=. python scripts/seed_neo4j_pilot.py
#
# Prerequisites:
#   - Neo4j running and accessible (check NEO4J_URI in .env)
#   - reviews/luxury_bilateral_edges.json present
#
# =============================================================================

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
EDGES_FILE = PROJECT_ROOT / "reviews" / "luxury_bilateral_edges.json"
MIGRATIONS_DIR = PROJECT_ROOT / "adam" / "infrastructure" / "neo4j" / "migrations"


async def check_neo4j_connection():
    """Verify Neo4j is reachable."""
    from neo4j import AsyncGraphDatabase

    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "atomofthought")

    logger.info("Connecting to Neo4j at %s ...", uri)
    driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
    try:
        await driver.verify_connectivity()
        logger.info("Neo4j connection: OK")
        return driver
    except Exception as e:
        logger.error("Neo4j connection FAILED: %s", e)
        sys.exit(1)


async def run_migrations(driver):
    """Run schema migration Cypher files."""
    if not MIGRATIONS_DIR.exists():
        logger.warning("No migrations directory found at %s", MIGRATIONS_DIR)
        return

    migration_files = sorted(MIGRATIONS_DIR.glob("*.cypher"))
    logger.info("Found %d migration files", len(migration_files))

    async with driver.session() as session:
        for mf in migration_files:
            logger.info("Running migration: %s", mf.name)
            cypher = mf.read_text()
            # Split on semicolons for multi-statement files
            statements = [s.strip() for s in cypher.split(";") if s.strip()]
            for stmt in statements:
                try:
                    await session.run(stmt)
                except Exception as e:
                    # Constraints/indexes may already exist — that's fine
                    if "already exists" in str(e).lower() or "equivalent" in str(e).lower():
                        pass
                    else:
                        logger.warning("  Migration statement warning: %s", e)


async def load_bilateral_edges(driver):
    """Load LUXY Ride bilateral edges into Neo4j."""
    if not EDGES_FILE.exists():
        logger.error("Bilateral edges file not found: %s", EDGES_FILE)
        logger.error("Download or generate it first.")
        sys.exit(1)

    with open(EDGES_FILE) as f:
        data = json.load(f)
    edges = data["edges"]
    logger.info("Loading %d bilateral edges into Neo4j...", len(edges))

    # Check if edges already loaded
    async with driver.session() as session:
        result = await session.run(
            "MATCH ()-[r:BRAND_CONVERTED]->() RETURN count(r) AS n"
        )
        record = await result.single()
        existing = record["n"] if record else 0
        if existing >= len(edges):
            logger.info("Edges already loaded (%d existing >= %d target). Skipping.", existing, len(edges))
            return existing

    # Batch load edges
    batch_size = 200
    loaded = 0
    t0 = time.time()

    async with driver.session() as session:
        for i in range(0, len(edges), batch_size):
            batch = edges[i:i + batch_size]

            # Create ProductDescription + AnnotatedReview + BRAND_CONVERTED
            await session.run("""
                UNWIND $batch AS edge
                MERGE (p:ProductDescription {asin: coalesce(edge._ad_brand, 'luxy_ride')})
                ON CREATE SET p.name = coalesce(edge._company, 'LUXY Ride'),
                              p.product_category = 'Luxury Transportation'
                MERGE (r:AnnotatedReview {review_id: toString(edge._review_id)})
                ON CREATE SET r.star_rating = edge.star_rating,
                              r.outcome = edge.outcome,
                              r.annotation_tier = coalesce(edge.annotation_tier, 'claude')
                MERGE (p)-[e:BRAND_CONVERTED]->(r)
                SET e.regulatory_fit_score = edge.regulatory_fit_score,
                    e.construal_fit_score = edge.construal_fit_score,
                    e.personality_brand_alignment = edge.personality_brand_alignment,
                    e.emotional_resonance = edge.emotional_resonance,
                    e.value_alignment = edge.value_alignment,
                    e.evolutionary_motive_match = edge.evolutionary_motive_match,
                    e.appeal_resonance = edge.appeal_resonance,
                    e.processing_route_match = edge.processing_route_match,
                    e.implicit_driver_match = edge.implicit_driver_match,
                    e.lay_theory_alignment = edge.lay_theory_alignment,
                    e.linguistic_style_match = edge.linguistic_style_match,
                    e.identity_signaling_match = edge.identity_signaling_match,
                    e.full_cosine_alignment = edge.full_cosine_alignment,
                    e.linguistic_style_matching = edge.linguistic_style_matching,
                    e.uniqueness_popularity_fit = edge.uniqueness_popularity_fit,
                    e.mental_simulation_resonance = edge.mental_simulation_resonance,
                    e.involvement_weight_modifier = edge.involvement_weight_modifier,
                    e.composite_alignment = edge.composite_alignment,
                    e.negativity_bias_match = edge.negativity_bias_match,
                    e.reactance_fit = edge.reactance_fit,
                    e.optimal_distinctiveness_fit = edge.optimal_distinctiveness_fit,
                    e.brand_trust_fit = edge.brand_trust_fit,
                    e.self_monitoring_fit = edge.self_monitoring_fit,
                    e.spending_pain_match = edge.spending_pain_match,
                    e.disgust_contamination_fit = edge.disgust_contamination_fit,
                    e.anchor_susceptibility_match = edge.anchor_susceptibility_match,
                    e.mental_ownership_match = edge.mental_ownership_match,
                    e.persuasion_confidence_multiplier = edge.persuasion_confidence_multiplier,
                    e.star_rating = edge.star_rating,
                    e.outcome = edge.outcome,
                    e.helpful_votes = edge.helpful_votes
            """, batch=batch)

            loaded += len(batch)
            if loaded % 500 == 0 or loaded == len(edges):
                logger.info("  Loaded %d / %d edges (%.1fs)", loaded, len(edges), time.time() - t0)

    logger.info("Edge loading complete: %d edges in %.1fs", loaded, time.time() - t0)
    return loaded


async def seed_archetype_priors(driver):
    """Seed archetype-mechanism priors from hardcoded research values."""
    logger.info("Seeding archetype mechanism priors...")

    # These are the 8 archetypes with differentiated Beta priors
    archetypes = {
        "achiever": {"social_proof": (5, 3), "authority": (6, 2), "scarcity": (4, 4), "narrative": (3, 5)},
        "guardian": {"social_proof": (6, 2), "authority": (7, 1), "scarcity": (2, 6), "narrative": (4, 4)},
        "explorer": {"social_proof": (3, 5), "authority": (3, 5), "scarcity": (5, 3), "narrative": (6, 2)},
        "connector": {"social_proof": (7, 1), "authority": (4, 4), "scarcity": (3, 5), "narrative": (5, 3)},
        "analyst": {"social_proof": (2, 6), "authority": (5, 3), "scarcity": (3, 5), "narrative": (2, 6)},
        "creator": {"social_proof": (3, 5), "authority": (3, 5), "scarcity": (4, 4), "narrative": (7, 1)},
        "nurturer": {"social_proof": (6, 2), "authority": (4, 4), "scarcity": (2, 6), "narrative": (5, 3)},
        "pragmatist": {"social_proof": (4, 4), "authority": (5, 3), "scarcity": (5, 3), "narrative": (3, 5)},
    }

    async with driver.session() as session:
        for arch_id, mechanisms in archetypes.items():
            await session.run("""
                MERGE (a:CustomerArchetype {archetype_id: $arch_id})
                SET a.name = $arch_id
            """, arch_id=arch_id)

            for mech, (alpha, beta) in mechanisms.items():
                await session.run("""
                    MATCH (a:CustomerArchetype {archetype_id: $arch_id})
                    MERGE (m:Mechanism {name: $mech})
                    MERGE (a)-[r:RESPONDS_TO]->(m)
                    SET r.alpha = $alpha, r.beta = $beta,
                        r.effectiveness = toFloat($alpha) / ($alpha + $beta)
                """, arch_id=arch_id, mech=mech, alpha=alpha, beta=beta)

    logger.info("Archetype priors seeded: %d archetypes", len(archetypes))


async def verify_data(driver):
    """Verify all expected data is present."""
    logger.info("Verifying data...")

    checks = []
    async with driver.session() as session:
        # Edges
        result = await session.run("MATCH ()-[r:BRAND_CONVERTED]->() RETURN count(r) AS n")
        record = await result.single()
        n_edges = record["n"]
        checks.append(("BRAND_CONVERTED edges", n_edges, n_edges >= 1400))

        # Products
        result = await session.run("MATCH (p:ProductDescription) RETURN count(p) AS n")
        record = await result.single()
        n_products = record["n"]
        checks.append(("ProductDescription nodes", n_products, n_products >= 1))

        # Reviews
        result = await session.run("MATCH (r:AnnotatedReview) RETURN count(r) AS n")
        record = await result.single()
        n_reviews = record["n"]
        checks.append(("AnnotatedReview nodes", n_reviews, n_reviews >= 1000))

        # Archetypes
        result = await session.run("MATCH (a:CustomerArchetype) RETURN count(a) AS n")
        record = await result.single()
        n_archs = record["n"]
        checks.append(("CustomerArchetype nodes", n_archs, n_archs >= 6))

        # Mechanism priors
        result = await session.run("MATCH ()-[r:RESPONDS_TO]->() RETURN count(r) AS n")
        record = await result.single()
        n_priors = record["n"]
        checks.append(("RESPONDS_TO priors", n_priors, n_priors >= 20))

    logger.info("")
    logger.info("DATA VERIFICATION:")
    all_pass = True
    for name, count, ok in checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        logger.info("  [%s] %s: %d", status, name, count)

    return all_pass


async def main():
    print("=" * 60)
    print("INFORMATIV Neo4j Seed — LUXY Ride Pilot")
    print("=" * 60)
    print()

    driver = await check_neo4j_connection()

    try:
        await run_migrations(driver)
        await load_bilateral_edges(driver)
        await seed_archetype_priors(driver)
        ok = await verify_data(driver)

        print()
        if ok:
            print("=" * 60)
            print("NEO4J SEED COMPLETE — All data verified")
            print("=" * 60)
        else:
            print("=" * 60)
            print("NEO4J SEED COMPLETE — SOME CHECKS FAILED (see above)")
            print("=" * 60)
            sys.exit(1)
    finally:
        await driver.close()


if __name__ == "__main__":
    asyncio.run(main())
