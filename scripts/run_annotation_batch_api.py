#!/usr/bin/env python3
"""
Fully automated annotation pipeline via Anthropic Message Batches API.

Reads raw Amazon/Sephora data, selects best reviews, submits to Claude
via the batch API (50% cheaper than real-time), polls for completion,
saves results, and imports into Neo4j.

Cost estimate for all_beauty (~1,500 products + ~30,000 reviews):
  Products: ~$3-5  |  Reviews: ~$50-75  |  Total: ~$55-80

Usage:
    # Full pipeline (products + reviews → annotate → import):
    python scripts/run_annotation_batch_api.py --dataset all_beauty

    # Products only:
    python scripts/run_annotation_batch_api.py --dataset all_beauty --products-only

    # Reviews only:
    python scripts/run_annotation_batch_api.py --dataset all_beauty --reviews-only

    # Dry run (count items, estimate cost, don't call API):
    python scripts/run_annotation_batch_api.py --dataset all_beauty --dry-run

    # Skip import (just annotate, don't write to Neo4j):
    python scripts/run_annotation_batch_api.py --dataset all_beauty --skip-import

    # Resume from checkpoint (after a crash):
    python scripts/run_annotation_batch_api.py --dataset all_beauty --resume

Environment:
    ANTHROPIC_API_KEY  — required
    ADAM_BATCH_MODEL   — override model (default: claude-sonnet-4-20250514)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import anthropic

from adam.corpus.annotators.prompt_templates import (
    AD_SIDE_SYSTEM_PROMPT,
    AD_SIDE_USER_PROMPT_TEMPLATE,
    DUAL_SYSTEM_PROMPT,
    DUAL_PROMPT_TEMPLATE,
)
from adam.corpus.pipeline.batch_api import submit_and_wait
from adam.corpus.pipeline.checkpoint_manager import CheckpointManager
from adam.corpus.pipeline.review_selector import (
    DatasetSelection,
    select_amazon_dataset,
    select_sephora_dataset,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("data/annotation_api.log", mode="a"),
    ],
)
logger = logging.getLogger("annotation_api")

DATASET_CONFIGS = {
    "all_beauty": {
        "type": "amazon",
        "reviews": "/Volumes/Sped/Review Data/Amazon/All_Beauty.jsonl",
        "meta": "/Volumes/Sped/Review Data/Amazon/meta_All_Beauty.jsonl",
        "min_reviews": 25,
        "top_n": 20,
    },
    "bpc": {
        "type": "amazon",
        "reviews": "/Volumes/Sped/Review Data/Amazon/Beauty_and_Personal_Care.jsonl",
        "meta": "/Volumes/Sped/Review Data/Amazon/meta_Beauty_and_Personal_Care.jsonl",
        "min_reviews": 50,
        "top_n": 20,
    },
    "sephora": {
        "type": "sephora",
        "dir": "/Volumes/Sped/Review Data/sephora_reviews",
        "min_reviews": 25,
        "top_n": 20,
    },
}

RESULTS_DIR = Path("data/annotation_results")
CHECKPOINT_DIR = "checkpoints/annotation_api"

HAIKU_INPUT_COST = 0.80 / 1_000_000    # $0.80/MTok input
HAIKU_OUTPUT_COST = 4.00 / 1_000_000   # $4.00/MTok output
BATCH_DISCOUNT = 0.50                    # 50% off with batch API


def estimate_cost(n_products: int, n_reviews: int) -> dict:
    avg_product_input_tokens = 800
    avg_product_output_tokens = 600
    avg_review_input_tokens = 1200
    avg_review_output_tokens = 900

    prod_input_cost = n_products * avg_product_input_tokens * HAIKU_INPUT_COST * BATCH_DISCOUNT
    prod_output_cost = n_products * avg_product_output_tokens * HAIKU_OUTPUT_COST * BATCH_DISCOUNT
    rev_input_cost = n_reviews * avg_review_input_tokens * HAIKU_INPUT_COST * BATCH_DISCOUNT
    rev_output_cost = n_reviews * avg_review_output_tokens * HAIKU_OUTPUT_COST * BATCH_DISCOUNT

    return {
        "products": round(prod_input_cost + prod_output_cost, 2),
        "reviews": round(rev_input_cost + rev_output_cost, 2),
        "total": round(prod_input_cost + prod_output_cost + rev_input_cost + rev_output_cost, 2),
    }


def build_product_requests(
    selection: DatasetSelection,
    completed_ids: set[str],
) -> list[dict]:
    requests = []
    for pid, product in selection.qualifying_products.items():
        if pid in completed_ids:
            continue
        user_prompt = AD_SIDE_USER_PROMPT_TEMPLATE.format(
            title=product.title[:500],
            category=product.category,
            price=product.price,
            brand=product.brand,
            description_text=(product.description or "")[:800],
            features_text=(product.features or "")[:500],
        )
        requests.append({
            "custom_id": f"product_{pid}",
            "system": AD_SIDE_SYSTEM_PROMPT,
            "user_prompt": user_prompt,
        })
    return requests


def build_review_requests(
    selection: DatasetSelection,
    completed_ids: set[str],
    dataset: str,
) -> tuple[list[dict], dict[str, str]]:
    """Build review API requests. Returns (requests, id_mapping).
    
    Uses sequential numeric custom_ids (max 64 chars) and saves
    a mapping file to recover the original review_id from each.
    """
    product_titles = {
        pid: p.title for pid, p in selection.qualifying_products.items()
    }
    requests = []
    id_map: dict[str, str] = {}  # custom_id -> original review_id
    seen_rids: set[str] = set()
    seq = 0

    for review in selection.claude_reviews:
        rid = review.review_id
        if rid in completed_ids or rid in seen_rids:
            continue
        seen_rids.add(rid)
        seq += 1
        custom_id = f"r{seq}"
        id_map[custom_id] = rid

        title = product_titles.get(review.product_id, "Unknown Product")
        user_prompt = DUAL_PROMPT_TEMPLATE.format(
            product_title=title,
            category=review.source,
            star_rating=review.rating,
            helpful_votes=review.helpful_votes,
            review_text=(review.text or "")[:2000],
        )
        requests.append({
            "custom_id": custom_id,
            "system": DUAL_SYSTEM_PROMPT,
            "user_prompt": user_prompt,
        })

    skipped = len(selection.claude_reviews) - len(seen_rids) - len(completed_ids)
    if skipped > 0:
        logger.info(f"Skipped {skipped} duplicate review IDs")

    map_path = RESULTS_DIR / dataset / "review_id_mapping.json"
    map_path.parent.mkdir(parents=True, exist_ok=True)
    map_path.write_text(json.dumps(id_map), encoding="utf-8")
    logger.info(f"Saved review ID mapping ({len(id_map)} entries) to {map_path}")

    return requests, id_map


def save_results(
    results: list[tuple[str, dict | None]],
    result_type: str,
    dataset: str,
    chunk_idx: int,
) -> Path:
    out_dir = RESULTS_DIR / dataset / result_type
    out_dir.mkdir(parents=True, exist_ok=True)

    fname = f"batch_{chunk_idx:04d}_results.json"
    path = out_dir / fname

    valid_results = []
    for custom_id, data in results:
        if data is None:
            continue
        raw_id = custom_id.replace(f"{result_type}_", "", 1)
        if result_type == "products":
            data["asin"] = raw_id
        elif result_type == "reviews":
            data["review_id"] = raw_id
        valid_results.append(data)

    path.write_text(json.dumps(valid_results, indent=2), encoding="utf-8")
    logger.info(f"Saved {len(valid_results)} {result_type} results to {path}")
    return path


def run_product_annotation(
    client: anthropic.Anthropic,
    selection: DatasetSelection,
    dataset: str,
    ckpt: CheckpointManager,
    dry_run: bool = False,
) -> int:
    completed = ckpt.load_completed("products")
    requests = build_product_requests(selection, completed)

    logger.info(
        f"Products: {len(selection.qualifying_products)} total, "
        f"{len(completed)} already done, {len(requests)} remaining"
    )

    if dry_run or not requests:
        return len(requests)

    chunk_size = 10_000
    total_saved = 0
    for i in range(0, len(requests), chunk_size):
        chunk = requests[i:i + chunk_size]
        chunk_idx = i // chunk_size + 1
        logger.info(f"Submitting product batch chunk {chunk_idx} ({len(chunk)} items)...")

        results = list(submit_and_wait(
            client, chunk, description=f"{dataset} products chunk {chunk_idx}"
        ))

        path = save_results(results, "products", dataset, chunk_idx)

        successful_ids = [
            cid.replace("product_", "", 1)
            for cid, data in results if data is not None
        ]
        ckpt.mark_batch_completed("products", successful_ids)
        total_saved += len(successful_ids)
        logger.info(f"Chunk {chunk_idx}: {len(successful_ids)} succeeded")

    return total_saved


def run_review_annotation(
    client: anthropic.Anthropic,
    selection: DatasetSelection,
    dataset: str,
    ckpt: CheckpointManager,
    dry_run: bool = False,
) -> int:
    completed = ckpt.load_completed("reviews")
    requests, id_map = build_review_requests(selection, completed, dataset)

    logger.info(
        f"Reviews: {len(selection.claude_reviews)} total, "
        f"{len(completed)} already done, {len(requests)} remaining"
    )

    if dry_run or not requests:
        return len(requests)

    chunk_size = 10_000
    total_saved = 0
    for i in range(0, len(requests), chunk_size):
        chunk = requests[i:i + chunk_size]
        chunk_idx = i // chunk_size + 1
        logger.info(f"Submitting review batch chunk {chunk_idx} ({len(chunk)} items)...")

        results = list(submit_and_wait(
            client, chunk, description=f"{dataset} reviews chunk {chunk_idx}"
        ))

        # Translate custom_ids back to original review_ids before saving
        translated = []
        for cid, data in results:
            original_rid = id_map.get(cid, cid)
            translated.append((f"review_{original_rid}", data))

        path = save_results(translated, "reviews", dataset, chunk_idx)

        successful_ids = [
            id_map.get(cid, cid)
            for cid, data in results if data is not None
        ]
        ckpt.mark_batch_completed("reviews", successful_ids)
        total_saved += len(successful_ids)
        logger.info(f"Chunk {chunk_idx}: {len(successful_ids)} succeeded")

    return total_saved


def run_neo4j_import(dataset: str):
    logger.info("Starting Neo4j import...")
    from neo4j import GraphDatabase
    from adam.corpus.models.ad_side_annotation import AdSideAnnotation
    from adam.corpus.models.user_side_annotation import UserSideAnnotation
    from adam.corpus.neo4j.bulk_writer import BulkWriter
    from adam.corpus.neo4j.schema_extension import apply_schema

    NEO4J_URI = "neo4j://127.0.0.1:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "atomofthought"

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    try:
        driver.verify_connectivity()
    except Exception as e:
        logger.error(f"Cannot connect to Neo4j: {e}")
        logger.warning("Import skipped. Run manually: python scripts/import_annotations_to_neo4j.py --dataset " + dataset)
        return

    logger.info("Applying schema...")
    apply_schema(driver)

    writer = BulkWriter(driver, batch_size=500)

    product_dir = RESULTS_DIR / dataset / "products"
    if product_dir.exists():
        all_products = []
        for f in sorted(product_dir.glob("batch_*_results.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            all_products.extend(data if isinstance(data, list) else [data])

        records = []
        for raw in all_products:
            asin = raw.get("asin", "")
            if not asin:
                continue
            try:
                anno = AdSideAnnotation(asin=asin, **{k: v for k, v in raw.items() if k != "asin"})
                flat = anno.to_flat_dict()
            except Exception:
                flat = raw.copy()
            flat["main_category"] = dataset
            flat["annotation_tier"] = "tier_1_batch_api"
            records.append({"asin": asin, "properties": flat})

        if records:
            written = writer.write_product_descriptions(records)
            logger.info(f"Imported {written} ProductDescription nodes")

    review_dir = RESULTS_DIR / dataset / "reviews"
    if review_dir.exists():
        all_reviews = []
        for f in sorted(review_dir.glob("batch_*_results.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            all_reviews.extend(data if isinstance(data, list) else [data])

        records = []
        for raw in all_reviews:
            review_id = raw.get("review_id", "")
            if not review_id:
                continue
            user_side_raw = raw.get("user_side", {})
            peer_ad_raw = raw.get("peer_ad_side", {})
            conversion = raw.get("conversion_outcome", "satisfied")

            try:
                anno = UserSideAnnotation(
                    review_id=review_id,
                    conversion_outcome=conversion,
                    annotation_confidence=user_side_raw.get("annotation_confidence", 0.5),
                    **{k: v for k, v in user_side_raw.items() if k != "annotation_confidence"},
                )
                flat = anno.to_flat_dict()
            except Exception:
                flat = {"annotation_confidence": 0.3, "user_conversion_outcome": conversion}

            for key, val in peer_ad_raw.items():
                if isinstance(val, dict):
                    for subkey, subval in val.items():
                        flat[f"peer_ad_{key}_{subkey}"] = subval
                else:
                    flat[f"peer_ad_{key}"] = val

            flat["annotation_tier"] = "tier_1_batch_api"
            records.append({"review_id": review_id, "properties": flat})

        if records:
            written = writer.write_annotated_reviews(records)
            logger.info(f"Imported {written} AnnotatedReview nodes")

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

    driver.close()
    logger.info("Neo4j import complete")


def main():
    parser = argparse.ArgumentParser(
        description="Automated annotation via Anthropic Batch API"
    )
    parser.add_argument("--dataset", required=True, choices=list(DATASET_CONFIGS.keys()))
    parser.add_argument("--products-only", action="store_true")
    parser.add_argument("--reviews-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Estimate cost, don't call API")
    parser.add_argument("--skip-import", action="store_true", help="Skip Neo4j import after annotation")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    args = parser.parse_args()

    Path("data").mkdir(exist_ok=True)

    logger.info("=" * 70)
    logger.info(f"ANNOTATION PIPELINE: {args.dataset}")
    logger.info("=" * 70)

    cfg = DATASET_CONFIGS[args.dataset]

    if cfg["type"] == "amazon":
        if not os.path.exists(cfg["reviews"]):
            logger.error(f"Reviews file not found: {cfg['reviews']}")
            logger.error("Is the external drive mounted at /Volumes/Sped/?")
            sys.exit(1)
        logger.info("Loading Amazon dataset (this may take a few minutes for large files)...")
        selection = select_amazon_dataset(
            reviews_path=cfg["reviews"],
            meta_path=cfg["meta"],
            source_name=args.dataset,
            min_reviews=cfg["min_reviews"],
            top_n_per_product=cfg["top_n"],
        )
    elif cfg["type"] == "sephora":
        if not os.path.exists(cfg["dir"]):
            logger.error(f"Sephora dir not found: {cfg['dir']}")
            sys.exit(1)
        selection = select_sephora_dataset(
            reviews_dir=cfg["dir"],
            min_reviews=cfg["min_reviews"],
            top_n_per_product=cfg["top_n"],
        )
    else:
        logger.error(f"Unknown dataset type: {cfg['type']}")
        sys.exit(1)

    n_products = len(selection.qualifying_products)
    n_reviews = len(selection.claude_reviews)
    costs = estimate_cost(
        n_products if not args.reviews_only else 0,
        n_reviews if not args.products_only else 0,
    )

    logger.info(f"Dataset loaded:")
    logger.info(f"  Products: {n_products:,}")
    logger.info(f"  Claude reviews: {n_reviews:,}")
    logger.info(f"  LIWC reviews: {len(selection.liwc_reviews):,}")
    logger.info(f"  Estimated cost: ${costs['total']:.2f} "
                f"(products=${costs['products']:.2f}, reviews=${costs['reviews']:.2f})")

    if args.dry_run:
        logger.info("[DRY RUN] No API calls will be made.")
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not set. Export it first:")
        logger.error("  export ANTHROPIC_API_KEY='sk-ant-...'")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    ckpt_dir = f"{CHECKPOINT_DIR}/{args.dataset}"
    ckpt = CheckpointManager(ckpt_dir)

    if not args.resume:
        ckpt.reset_phase("products")
        ckpt.reset_phase("reviews")

    products_done = 0
    reviews_done = 0

    if not args.reviews_only:
        logger.info("-" * 50)
        logger.info("PHASE 1: PRODUCT ANNOTATION")
        logger.info("-" * 50)
        products_done = run_product_annotation(
            client, selection, args.dataset, ckpt
        )

    if not args.products_only:
        logger.info("-" * 50)
        logger.info("PHASE 2: REVIEW ANNOTATION")
        logger.info("-" * 50)
        reviews_done = run_review_annotation(
            client, selection, args.dataset, ckpt
        )

    logger.info("=" * 70)
    logger.info("ANNOTATION COMPLETE")
    logger.info(f"  Products annotated: {products_done}")
    logger.info(f"  Reviews annotated:  {reviews_done}")
    logger.info(f"  Results saved to:   {RESULTS_DIR / args.dataset}")
    logger.info("=" * 70)

    if not args.skip_import:
        logger.info("-" * 50)
        logger.info("PHASE 3: NEO4J IMPORT")
        logger.info("-" * 50)
        run_neo4j_import(args.dataset)

    logger.info("=" * 70)
    logger.info("ALL DONE")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
