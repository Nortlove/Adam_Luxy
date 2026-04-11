#!/usr/bin/env python3
"""
Compute Psychological Gradient Fields
=======================================

Pre-computes gradient fields for all (archetype, category) cells and
stores them on BayesianPrior nodes in Neo4j.

Usage:
    python3 scripts/compute_gradient_fields.py
    python3 scripts/compute_gradient_fields.py --category Beauty
    python3 scripts/compute_gradient_fields.py --dry-run

This should be run:
- After initial data ingestion
- Periodically (weekly) to update gradients as new conversion data arrives
- Before StackAdapt deployment to ensure all Phase 1 cells have gradients
"""

import argparse
import json
import logging
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adam.constants import EXTERNAL_ARCHETYPES
from adam.intelligence.gradient_fields import (
    compute_gradient_from_neo4j,
    gradient_to_neo4j_properties,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

NEO4J_URI = os.getenv("NEO4J_URI", "neo4j://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASS", "atomofthought")

# Phase 1 categories with full BRAND_CONVERTED edge coverage
PHASE1_CATEGORIES = ["Beauty", "Personal Care", "Beauty & Personal Care"]


def main():
    parser = argparse.ArgumentParser(description="Compute Psychological Gradient Fields")
    parser.add_argument("--category", help="Compute for specific category only")
    parser.add_argument("--archetype", help="Compute for specific archetype only")
    parser.add_argument("--dry-run", action="store_true", help="Compute but don't store in Neo4j")
    parser.add_argument("--all-categories", action="store_true", help="Include all categories, not just Phase 1")
    args = parser.parse_args()

    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    driver.verify_connectivity()
    logger.info("Connected to Neo4j at %s", NEO4J_URI)

    # Determine categories
    if args.category:
        categories = [args.category]
    elif args.all_categories:
        with driver.session() as session:
            results = session.run(
                "MATCH (pd:ProductDescription)-[:BRAND_CONVERTED]->() "
                "RETURN DISTINCT pd.main_category AS cat, count(*) AS n "
                "ORDER BY n DESC LIMIT 50"
            ).data()
            categories = [r["cat"] for r in results if r["cat"]]
    else:
        categories = PHASE1_CATEGORIES

    archetypes = [args.archetype] if args.archetype else EXTERNAL_ARCHETYPES

    logger.info(
        "Computing gradients for %d archetypes x %d categories = %d cells",
        len(archetypes), len(categories), len(archetypes) * len(categories),
    )

    results_summary = []
    start = time.time()

    for category in categories:
        for archetype in archetypes:
            t0 = time.time()
            gv = compute_gradient_from_neo4j(driver, archetype, category)
            elapsed = time.time() - t0

            if gv.is_valid:
                # Sort gradients by absolute magnitude
                sorted_grads = sorted(
                    gv.gradients.items(), key=lambda x: abs(x[1]), reverse=True,
                )
                top3 = ", ".join(f"{k}={v:+.3f}" for k, v in sorted_grads[:3])

                logger.info(
                    "  %s x %s: n=%d, R2=%.3f, top: %s (%.0fms)",
                    archetype, category, gv.n_edges, gv.r_squared, top3, elapsed * 1000,
                )

                results_summary.append({
                    "archetype": archetype,
                    "category": category,
                    "n_edges": gv.n_edges,
                    "r_squared": gv.r_squared,
                    "gradients": gv.gradients,
                    "optima": gv.optima,
                })

                if not args.dry_run:
                    # Store on BayesianPrior node
                    props = gradient_to_neo4j_properties(gv)
                    try:
                        with driver.session() as session:
                            session.run(
                                "MERGE (bp:BayesianPrior {category: $cat, archetype: $arch}) "
                                "SET bp += $props",
                                cat=category, arch=archetype, props=props,
                            )
                    except Exception as e:
                        logger.warning("Failed to store gradient for %s x %s: %s", archetype, category, e)
            else:
                logger.info(
                    "  %s x %s: insufficient data (n=%d) (%.0fms)",
                    archetype, category, gv.n_edges, elapsed * 1000,
                )

    total_elapsed = time.time() - start
    valid_count = len(results_summary)
    total_cells = len(archetypes) * len(categories)

    logger.info(
        "\nComplete: %d/%d cells computed in %.1fs",
        valid_count, total_cells, total_elapsed,
    )

    if valid_count > 0:
        avg_r2 = sum(r["r_squared"] for r in results_summary) / valid_count
        avg_edges = sum(r["n_edges"] for r in results_summary) / valid_count
        logger.info("  Average R2: %.3f, Average edges per cell: %.0f", avg_r2, avg_edges)

    # Save summary to JSON
    summary_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", "learning", "gradient_field_summary.json",
    )
    os.makedirs(os.path.dirname(summary_path), exist_ok=True)
    with open(summary_path, "w") as f:
        json.dump({
            "computed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_cells": total_cells,
            "valid_cells": valid_count,
            "categories": categories,
            "archetypes": archetypes,
            "results": results_summary,
        }, f, indent=2)
    logger.info("Summary saved to %s", summary_path)

    driver.close()


if __name__ == "__main__":
    main()
