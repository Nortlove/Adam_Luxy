#!/usr/bin/env python3
"""
Import Claude Max annotation results into Neo4j.

Reads JSON result files produced during the Claude Max annotation workflow,
validates against Pydantic models, and writes to Neo4j using BulkWriter.

Usage:
    python scripts/import_annotations_to_neo4j.py --dataset all_beauty
    python scripts/import_annotations_to_neo4j.py --dataset all_beauty --products-only
    python scripts/import_annotations_to_neo4j.py --dataset all_beauty --reviews-only
    python scripts/import_annotations_to_neo4j.py --dataset all_beauty --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from neo4j import GraphDatabase

from adam.corpus.models.ad_side_annotation import AdSideAnnotation
from adam.corpus.models.user_side_annotation import UserSideAnnotation
from adam.corpus.neo4j.bulk_writer import BulkWriter
from adam.corpus.neo4j.schema_extension import apply_schema

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("import_annotations")

NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "atomofthought"

RESULTS_DIR = Path("data/annotation_results")
BATCHES_DIR = Path("data/annotation_batches")


def load_product_results(dataset: str) -> list[dict]:
    """Load all product annotation result files for a dataset."""
    results_path = RESULTS_DIR / dataset / "products"
    if not results_path.exists():
        logger.warning(f"No product results dir: {results_path}")
        return []

    all_products = []
    for f in sorted(results_path.glob("batch_*_results.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, list):
                all_products.extend(data)
            elif isinstance(data, dict):
                all_products.append(data)
            logger.info(f"  Loaded {f.name}: {len(data) if isinstance(data, list) else 1} products")
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"  FAILED to parse {f.name}: {e}")
    return all_products


def load_review_results(dataset: str) -> list[dict]:
    """Load all review annotation result files for a dataset."""
    results_path = RESULTS_DIR / dataset / "reviews"
    if not results_path.exists():
        logger.warning(f"No review results dir: {results_path}")
        return []

    all_reviews = []
    for f in sorted(results_path.glob("batch_*_results.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, list):
                all_reviews.extend(data)
            elif isinstance(data, dict):
                all_reviews.append(data)
            logger.info(f"  Loaded {f.name}: {len(data) if isinstance(data, list) else 1} reviews")
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"  FAILED to parse {f.name}: {e}")
    return all_reviews


def load_manifest(dataset: str) -> dict | None:
    """Load the batch manifest for product metadata."""
    path = BATCHES_DIR / dataset / "manifest.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


def validate_product(raw: dict) -> AdSideAnnotation | None:
    """Validate a raw product annotation against the Pydantic model."""
    asin = raw.get("asin", "")
    if not asin:
        logger.warning("Product missing 'asin' field, skipping")
        return None
    try:
        return AdSideAnnotation(asin=asin, **{
            k: v for k, v in raw.items() if k != "asin"
        })
    except Exception as e:
        logger.warning(f"Validation failed for product {asin}: {e}")
        return AdSideAnnotation(asin=asin)


def validate_review(raw: dict) -> tuple[str, dict] | None:
    """Validate a raw review annotation and return (review_id, flat_props)."""
    review_id = raw.get("review_id", "")
    if not review_id:
        logger.warning("Review missing 'review_id' field, skipping")
        return None

    user_side_raw = raw.get("user_side", {})
    peer_ad_raw = raw.get("peer_ad_side", {})
    conversion = raw.get("conversion_outcome", "satisfied")

    try:
        user_anno = UserSideAnnotation(
            review_id=review_id,
            conversion_outcome=conversion,
            **{k: v for k, v in user_side_raw.items()
               if k not in ("annotation_confidence",)},
            annotation_confidence=user_side_raw.get("annotation_confidence", 0.5),
        )
        flat = user_anno.to_flat_dict()
    except Exception as e:
        logger.warning(f"User-side validation failed for {review_id}: {e}")
        flat = {"annotation_confidence": 0.3, "user_conversion_outcome": conversion}

    # Recursively flatten peer-ad-side with prefix
    def _flatten(d: dict, prefix: str):
        for key, val in d.items():
            full_key = f"{prefix}_{key}" if prefix else key
            if isinstance(val, dict):
                _flatten(val, full_key)
            elif isinstance(val, list):
                flat[full_key] = [v for v in val if isinstance(v, (str, int, float, bool))]
            elif isinstance(val, (str, int, float, bool)) or val is None:
                flat[full_key] = val

    _flatten(peer_ad_raw, "peer_ad")

    return review_id, flat


def import_products(
    writer: BulkWriter,
    products: list[dict],
    dataset: str,
    dry_run: bool = False,
):
    """Import validated product annotations as ProductDescription nodes."""
    records = []
    for raw in products:
        anno = validate_product(raw)
        if anno is None:
            continue
        flat = anno.to_flat_dict()
        flat["main_category"] = dataset
        flat["annotation_tier"] = "tier_1_claude_max"
        records.append({
            "asin": anno.asin,
            "properties": flat,
        })

    logger.info(f"Validated {len(records)}/{len(products)} products")

    if dry_run:
        logger.info("[DRY RUN] Would write %d ProductDescription nodes", len(records))
        if records:
            sample = records[0]
            logger.info(f"  Sample ASIN: {sample['asin']}")
            logger.info(f"  Sample props: {len(sample['properties'])} fields")
        return

    written = writer.write_product_descriptions(records)
    logger.info(f"Wrote {written} ProductDescription nodes to Neo4j")


def import_reviews(
    writer: BulkWriter,
    reviews: list[dict],
    dry_run: bool = False,
):
    """Import validated review annotations as AnnotatedReview nodes."""
    records = []
    for raw in reviews:
        result = validate_review(raw)
        if result is None:
            continue
        review_id, flat = result
        flat["annotation_tier"] = "tier_1_claude_max"
        records.append({
            "review_id": review_id,
            "properties": flat,
        })

    logger.info(f"Validated {len(records)}/{len(reviews)} reviews")

    if dry_run:
        logger.info("[DRY RUN] Would write %d AnnotatedReview nodes", len(records))
        if records:
            sample = records[0]
            logger.info(f"  Sample review_id: {sample['review_id']}")
            logger.info(f"  Sample props: {len(sample['properties'])} fields")
        return

    written = writer.write_annotated_reviews(records)
    logger.info(f"Wrote {written} AnnotatedReview nodes to Neo4j")


def link_reviews_to_products(driver, dry_run: bool = False):
    """Create HAS_REVIEW edges between ProductDescription and AnnotatedReview nodes."""
    if dry_run:
        logger.info("[DRY RUN] Would link reviews to products via HAS_REVIEW edges")
        return

    with driver.session() as session:
        result = session.run("""
            MATCH (r:AnnotatedReview)
            WHERE r.parent_asin IS NOT NULL OR r.asin IS NOT NULL
            WITH r, coalesce(r.parent_asin, r.asin) AS product_asin
            MATCH (pd:ProductDescription {asin: product_asin})
            MERGE (pd)-[:HAS_REVIEW]->(r)
            RETURN count(*) AS linked
        """)
        linked = result.single()["linked"]
        logger.info(f"Linked {linked} reviews to products via HAS_REVIEW")


def main():
    parser = argparse.ArgumentParser(description="Import annotations to Neo4j")
    parser.add_argument("--dataset", required=True, choices=["all_beauty", "bpc", "sephora"])
    parser.add_argument("--products-only", action="store_true")
    parser.add_argument("--reviews-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing to Neo4j")
    parser.add_argument("--skip-schema", action="store_true", help="Skip schema creation")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info(f"IMPORTING ANNOTATIONS: {args.dataset}")
    logger.info("=" * 60)

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    try:
        driver.verify_connectivity()
        logger.info("Neo4j connection verified")
    except Exception as e:
        logger.error(f"Cannot connect to Neo4j at {NEO4J_URI}: {e}")
        sys.exit(1)

    if not args.skip_schema and not args.dry_run:
        logger.info("Applying schema...")
        count = apply_schema(driver)
        logger.info(f"Schema: {count} statements applied")

    writer = BulkWriter(driver, batch_size=500)

    if not args.reviews_only:
        logger.info("Loading product results...")
        products = load_product_results(args.dataset)
        if products:
            import_products(writer, products, args.dataset, dry_run=args.dry_run)
        else:
            logger.warning("No product results found")

    if not args.products_only:
        logger.info("Loading review results...")
        reviews = load_review_results(args.dataset)
        if reviews:
            import_reviews(writer, reviews, dry_run=args.dry_run)
        else:
            logger.warning("No review results found")

    if not args.dry_run and not args.products_only and not args.reviews_only:
        logger.info("Linking reviews to products...")
        link_reviews_to_products(driver, dry_run=args.dry_run)

    logger.info("=" * 60)
    logger.info("IMPORT COMPLETE")
    logger.info(f"  Stats: {writer.stats}")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Next step: Run edge computation (Phases 4-8)")
    logger.info("  nohup python -m adam.corpus.pipeline.bulk_phases >> logs/bulk_phases.log 2>&1 &")

    driver.close()


if __name__ == "__main__":
    main()
