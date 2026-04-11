#!/usr/bin/env python3
"""
StackAdapt Intelligence Refresh — Tier 3 Batch Pre-Computation
===============================================================

Nightly batch job that exports the full power of the Neo4j graph into
pre-computed artifacts consumed by the Creative Intelligence API at
request time (Tier 1 warm cache).

What it does:
    1. Full 27-dimension BRAND_CONVERTED edge analysis per category x archetype
    2. Thompson posterior snapshot from the cold-start sampler
    3. Segment taxonomy refresh with graph-backed confidence
    4. BayesianPrior aggregation export
    5. Product ad profile export for high-traffic ASINs

Outputs:
    data/stackadapt/graph_intelligence_export.json
    data/stackadapt/thompson_posteriors.json
    data/stackadapt/informativ_taxonomy.json
    data/stackadapt/bayesian_prior_summary.json

Usage:
    python scripts/refresh_stackadapt_intelligence.py [--dry-run] [--skip-taxonomy]

    Run nightly via cron or before major campaign launches:
    nohup python scripts/refresh_stackadapt_intelligence.py >> logs/stackadapt_refresh.log 2>&1 &
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("stackadapt_refresh")

NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "atomofthought")

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "stackadapt"

ARCHETYPES = ["achiever", "guardian", "connector", "explorer", "analyst", "pragmatist"]

EDGE_DIMENSIONS = [
    "personality_brand_alignment", "emotional_resonance",
    "regulatory_fit_score", "construal_fit_score", "value_alignment",
    "evolutionary_motive_match", "composite_alignment",
    "linguistic_style_matching", "persuasion_confidence_multiplier",
    "social_proof_score", "authority_score", "scarcity_score",
    "reciprocity_score", "commitment_score", "liking_score",
    "anchoring_score", "fomo_score", "unity_score",
    "cognitive_load_index", "argument_quality_score",
    "temporal_framing_match", "identity_relevance_score",
    "risk_perception_alignment", "need_for_cognition_match",
    "construal_level_match", "affect_transfer_score",
    "narrative_transportation_score",
]


def get_neo4j_driver():
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
        driver.verify_connectivity()
        logger.info("Connected to Neo4j at %s", NEO4J_URI)
        return driver
    except Exception as e:
        logger.error("Failed to connect to Neo4j: %s", e)
        return None


# ─── Step 1: Full Edge Analysis ─────────────────────────────────────────────

def export_edge_analysis(driver) -> Dict[str, Any]:
    """
    Export full 27-dimension BRAND_CONVERTED edge analysis
    aggregated by category x archetype.
    """
    logger.info("Step 1: Exporting BRAND_CONVERTED edge analysis...")
    start = time.time()

    avg_clauses = ", ".join(
        f"avg(bc.{dim}) AS avg_{dim}" for dim in EDGE_DIMENSIONS
    )
    std_clauses = ", ".join(
        f"stDev(bc.{dim}) AS std_{dim}" for dim in EDGE_DIMENSIONS[:7]
    )

    query = f"""
    MATCH (pd:ProductDescription)-[bc:BRAND_CONVERTED]->(ar:AnnotatedReview)
    RETURN pd.main_category AS category,
           ar.user_archetype AS archetype,
           count(bc) AS edge_count,
           {avg_clauses},
           {std_clauses}
    """

    results = {}
    try:
        with driver.session() as session:
            records = session.run(query).data()

        for row in records:
            cat = row.get("category") or "unknown"
            arch = row.get("archetype") or "unknown"
            key = f"{cat}:{arch}"

            entry = {
                "category": cat,
                "archetype": arch,
                "edge_count": row.get("edge_count", 0),
                "averages": {},
                "std_devs": {},
            }

            for dim in EDGE_DIMENSIONS:
                avg_val = row.get(f"avg_{dim}")
                if avg_val is not None:
                    entry["averages"][dim] = round(float(avg_val), 4)

            for dim in EDGE_DIMENSIONS[:7]:
                std_val = row.get(f"std_{dim}")
                if std_val is not None:
                    entry["std_devs"][dim] = round(float(std_val), 4)

            results[key] = entry

        elapsed = time.time() - start
        logger.info(
            "Edge analysis complete: %d category x archetype combinations in %.1fs",
            len(results), elapsed,
        )
    except Exception as e:
        logger.error("Edge analysis failed: %s", e)

    return results


# ─── Step 2: Thompson Posterior Snapshot ──────────────────────────────────────

def export_thompson_posteriors() -> Dict[str, Any]:
    """
    Snapshot the current Thompson sampling posteriors from the cold-start
    system into a portable JSON format.
    """
    logger.info("Step 2: Exporting Thompson posteriors...")
    start = time.time()

    posteriors: Dict[str, Any] = {
        "snapshot_at": datetime.now(timezone.utc).isoformat(),
        "archetypes": {},
        "population": {},
    }

    try:
        from adam.cold_start.thompson.sampler import ThompsonSampler
        from adam.cold_start.models.enums import CognitiveMechanism, ArchetypeID

        sampler = ThompsonSampler()

        for mech in CognitiveMechanism:
            post = sampler.population_posteriors.get(mech)
            if post:
                posteriors["population"][mech.value] = {
                    "alpha": post.alpha,
                    "beta": post.beta,
                    "mean": round(post.alpha / (post.alpha + post.beta), 4),
                }

        for arch_id in ArchetypeID:
            arch_data = {}
            if arch_id in sampler.posteriors:
                for mech, post in sampler.posteriors[arch_id].items():
                    arch_data[mech.value] = {
                        "alpha": post.alpha,
                        "beta": post.beta,
                        "mean": round(post.alpha / (post.alpha + post.beta), 4),
                    }
            posteriors["archetypes"][arch_id.value] = arch_data

        elapsed = time.time() - start
        logger.info("Thompson posteriors exported in %.2fs", elapsed)
    except Exception as e:
        logger.warning("Thompson posterior export skipped: %s", e)
        posteriors["error"] = str(e)

    return posteriors


# ─── Step 3: Taxonomy Refresh ──────────────────────────────────────────────

def refresh_taxonomy(graph_intel: Dict[str, Any]) -> Optional[str]:
    """
    Re-generate the full segment taxonomy with graph intelligence.
    Returns the output file path.
    """
    logger.info("Step 3: Refreshing segment taxonomy...")
    start = time.time()

    try:
        from adam.integrations.stackadapt.taxonomy_generator import TaxonomyGenerator

        gen = TaxonomyGenerator()
        gen.load_data()

        if hasattr(gen, "load_graph_intelligence"):
            gen.load_graph_intelligence(graph_intel)

        segments = gen.generate()
        output_path = OUTPUT_DIR / "informativ_taxonomy.json"
        gen.export_json(segments, output_path)

        elapsed = time.time() - start
        logger.info(
            "Taxonomy refreshed: %d segments in %.2fs -> %s",
            len(segments), elapsed, output_path,
        )
        return str(output_path)
    except Exception as e:
        logger.error("Taxonomy refresh failed: %s", e)
        return None


# ─── Step 4: BayesianPrior Summary ──────────────────────────────────────────

def export_bayesian_priors(driver) -> Dict[str, Any]:
    """Export all BayesianPrior nodes as a structured summary."""
    logger.info("Step 4: Exporting BayesianPrior summary...")
    start = time.time()

    summary: Dict[str, Any] = {"categories": {}, "total_priors": 0}

    try:
        with driver.session() as session:
            results = session.run(
                "MATCH (bp:BayesianPrior) RETURN properties(bp) AS props"
            ).data()

        for r in results:
            props = r["props"]
            cat = props.get("category", "unknown")
            prior_type = props.get("prior_type", "general")

            if cat not in summary["categories"]:
                summary["categories"][cat] = {
                    "priors": [],
                    "total_observations": 0,
                }

            clean_props = {
                k: round(float(v), 4) if isinstance(v, (int, float)) else v
                for k, v in props.items()
                if v is not None
            }
            summary["categories"][cat]["priors"].append(clean_props)
            summary["categories"][cat]["total_observations"] += int(
                props.get("n_observations", 0)
            )

        summary["total_priors"] = len(results)
        elapsed = time.time() - start
        logger.info(
            "BayesianPrior summary: %d priors across %d categories in %.2fs",
            summary["total_priors"], len(summary["categories"]), elapsed,
        )
    except Exception as e:
        logger.error("BayesianPrior export failed: %s", e)

    return summary


# ─── Step 5: High-Traffic Product Profiles ───────────────────────────────────

def export_top_product_profiles(driver, limit: int = 500) -> List[Dict[str, Any]]:
    """
    Export product ad profiles for the most-connected ASINs
    (highest BRAND_CONVERTED edge count).
    """
    logger.info("Step 5: Exporting top %d product profiles...", limit)
    start = time.time()

    profiles = []
    try:
        with driver.session() as session:
            results = session.run(
                "MATCH (pd:ProductDescription)-[bc:BRAND_CONVERTED]->() "
                "WITH pd, count(bc) AS edge_count "
                "ORDER BY edge_count DESC LIMIT $limit "
                "RETURN properties(pd) AS props, edge_count",
                limit=limit,
            ).data()

        for r in results:
            props = r["props"]
            profile = {
                "asin": props.get("asin", ""),
                "category": props.get("main_category", ""),
                "edge_count": r["edge_count"],
                "framing": {},
                "brand_personality": {},
                "persuasion_techniques": {},
            }

            for key, val in props.items():
                if val is None:
                    continue
                if key.startswith("ad_framing_"):
                    profile["framing"][key.replace("ad_framing_", "")] = val
                elif key.startswith("ad_brand_personality_"):
                    profile["brand_personality"][key.replace("ad_brand_personality_", "")] = val
                elif key.startswith("ad_persuasion_techniques_"):
                    profile["persuasion_techniques"][key.replace("ad_persuasion_techniques_", "")] = val

            profiles.append(profile)

        elapsed = time.time() - start
        logger.info("Exported %d product profiles in %.2fs", len(profiles), elapsed)
    except Exception as e:
        logger.error("Product profile export failed: %s", e)

    return profiles


# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="StackAdapt Tier 3 intelligence refresh",
    )
    parser.add_argument("--dry-run", action="store_true", help="Log what would be done without writing files")
    parser.add_argument("--skip-taxonomy", action="store_true", help="Skip taxonomy regeneration")
    parser.add_argument("--output-dir", type=str, default=str(OUTPUT_DIR), help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    total_start = time.time()
    logger.info("=" * 60)
    logger.info("StackAdapt Intelligence Refresh — Tier 3 Batch")
    logger.info("=" * 60)
    logger.info("Output directory: %s", out_dir)

    driver = get_neo4j_driver()

    # Step 1: Edge analysis
    if driver:
        edge_analysis = export_edge_analysis(driver)
    else:
        logger.warning("Skipping edge analysis (no Neo4j)")
        edge_analysis = {}

    # Step 2: Thompson posteriors
    thompson = export_thompson_posteriors()

    # Step 3: BayesianPrior summary
    if driver:
        bp_summary = export_bayesian_priors(driver)
    else:
        logger.warning("Skipping BayesianPrior export (no Neo4j)")
        bp_summary = {}

    # Step 4: Product profiles
    if driver:
        products = export_top_product_profiles(driver)
    else:
        logger.warning("Skipping product profiles (no Neo4j)")
        products = []

    if not args.dry_run:
        manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "neo4j_available": driver is not None,
        }

        # Write edge analysis
        edge_path = out_dir / "graph_intelligence_export.json"
        with open(edge_path, "w") as f:
            json.dump({
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "edge_dimensions": EDGE_DIMENSIONS,
                "category_archetype_edges": edge_analysis,
                "total_combinations": len(edge_analysis),
            }, f, indent=2)
        logger.info("Wrote %s", edge_path)
        manifest["edge_analysis"] = str(edge_path)

        # Write Thompson posteriors
        thompson_path = out_dir / "thompson_posteriors.json"
        with open(thompson_path, "w") as f:
            json.dump(thompson, f, indent=2)
        logger.info("Wrote %s", thompson_path)
        manifest["thompson_posteriors"] = str(thompson_path)

        # Write BayesianPrior summary
        bp_path = out_dir / "bayesian_prior_summary.json"
        with open(bp_path, "w") as f:
            json.dump(bp_summary, f, indent=2)
        logger.info("Wrote %s", bp_path)
        manifest["bayesian_priors"] = str(bp_path)

        # Write product profiles
        prod_path = out_dir / "top_product_profiles.json"
        with open(prod_path, "w") as f:
            json.dump({
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "products": products,
                "total": len(products),
            }, f, indent=2)
        logger.info("Wrote %s", prod_path)
        manifest["product_profiles"] = str(prod_path)

        # Step 5: Taxonomy refresh
        if not args.skip_taxonomy:
            taxonomy_path = refresh_taxonomy(edge_analysis)
            manifest["taxonomy"] = taxonomy_path
        else:
            logger.info("Skipping taxonomy refresh (--skip-taxonomy)")

        # Write manifest
        manifest_path = out_dir / "refresh_manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        logger.info("Wrote manifest: %s", manifest_path)

    if driver:
        driver.close()

    total_elapsed = time.time() - total_start
    logger.info("=" * 60)
    logger.info("Refresh complete in %.1fs", total_elapsed)
    logger.info("  Edge analysis: %d category x archetype combinations", len(edge_analysis))
    logger.info("  Thompson posteriors: %d population + %d archetype-specific",
                len(thompson.get("population", {})),
                len(thompson.get("archetypes", {})))
    logger.info("  BayesianPriors: %d total", bp_summary.get("total_priors", 0))
    logger.info("  Product profiles: %d", len(products))
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
