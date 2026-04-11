#!/usr/bin/env python3
"""
Prepare paste-ready annotation batch files for Claude Max.

Reads raw Amazon/Sephora data, selects best reviews per product via
review_selector.py, and writes batch files that can be pasted directly
into a Claude Max chat session.

Usage:
    python scripts/prepare_annotation_batches.py --dataset all_beauty
    python scripts/prepare_annotation_batches.py --dataset bpc
    python scripts/prepare_annotation_batches.py --dataset sephora
    python scripts/prepare_annotation_batches.py --dataset all_beauty --products-only
    python scripts/prepare_annotation_batches.py --dataset all_beauty --reviews-only
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from adam.corpus.pipeline.review_selector import (
    DatasetSelection,
    ProductRecord,
    ReviewRecord,
    select_amazon_dataset,
    select_sephora_dataset,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger("prepare_batches")

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

PRODUCTS_PER_BATCH = 25
REVIEWS_PER_BATCH = 25

OUTPUT_DIR = Path("data/annotation_batches")


def format_product_for_paste(idx: int, p: ProductRecord) -> str:
    desc = (p.description or "")[:800]
    feats = (p.features or "")[:500]
    return (
        f"--- PRODUCT {idx} ---\n"
        f"ASIN: {p.product_id}\n"
        f"Title: {p.title}\n"
        f"Category: {p.category}\n"
        f"Price: {p.price}\n"
        f"Brand: {p.brand}\n"
        f"Description: {desc}\n"
        f"Features: {feats}\n"
    )


def format_review_for_paste(idx: int, r: ReviewRecord, product_title: str) -> str:
    text = (r.text or "")[:2000]
    return (
        f"--- REVIEW {idx} ---\n"
        f"Review ID: {r.review_id}\n"
        f"Product: {product_title}\n"
        f"Product ASIN: {r.product_id}\n"
        f"Category: {r.source}\n"
        f"Star Rating: {r.rating}/5\n"
        f"Helpful Votes: {r.helpful_votes}\n"
        f"Verified Purchase: Yes\n"
        f"\n{text}\n"
    )


PRODUCT_BATCH_HEADER = """PRODUCT ANNOTATION BATCH — Score these products using the ad-side schema from your instructions. Return JSON array with "asin" in each object.

"""

REVIEW_DUAL_BATCH_HEADER = """REVIEW DUAL ANNOTATION BATCH — Score each review using the dual schema (user_side + peer_ad_side) from your instructions. Return JSON array with "review_id" in each object.

"""


def write_product_batches(
    selection: DatasetSelection,
    dataset_name: str,
) -> int:
    out_dir = OUTPUT_DIR / dataset_name / "products"
    out_dir.mkdir(parents=True, exist_ok=True)

    products = list(selection.qualifying_products.values())
    logger.info(f"Writing {len(products)} products in batches of {PRODUCTS_PER_BATCH}")

    batch_num = 0
    for i in range(0, len(products), PRODUCTS_PER_BATCH):
        batch = products[i : i + PRODUCTS_PER_BATCH]
        batch_num += 1
        fname = f"batch_{batch_num:04d}.txt"

        lines = [PRODUCT_BATCH_HEADER]
        for j, p in enumerate(batch, 1):
            lines.append(format_product_for_paste(j, p))
        lines.append(
            f"\nReturn JSON array of {len(batch)} objects. "
            "Include the 'asin' field in each."
        )

        (out_dir / fname).write_text("\n".join(lines), encoding="utf-8")

    logger.info(f"Wrote {batch_num} product batch files to {out_dir}")
    return batch_num


def write_review_batches(
    selection: DatasetSelection,
    dataset_name: str,
) -> int:
    out_dir = OUTPUT_DIR / dataset_name / "reviews"
    out_dir.mkdir(parents=True, exist_ok=True)

    product_titles = {
        pid: p.title for pid, p in selection.qualifying_products.items()
    }

    reviews = selection.claude_reviews
    logger.info(f"Writing {len(reviews)} reviews in batches of {REVIEWS_PER_BATCH}")

    batch_num = 0
    for i in range(0, len(reviews), REVIEWS_PER_BATCH):
        batch = reviews[i : i + REVIEWS_PER_BATCH]
        batch_num += 1
        fname = f"batch_{batch_num:04d}.txt"

        lines = [REVIEW_DUAL_BATCH_HEADER]
        for j, r in enumerate(batch, 1):
            title = product_titles.get(r.product_id, "Unknown Product")
            lines.append(format_review_for_paste(j, r, title))
        lines.append(
            f"\nReturn JSON array of {len(batch)} objects. "
            "Include the 'review_id' field in each."
        )

        (out_dir / fname).write_text("\n".join(lines), encoding="utf-8")

    logger.info(f"Wrote {batch_num} review batch files to {out_dir}")
    return batch_num


def write_manifest(
    selection: DatasetSelection,
    dataset_name: str,
    product_batches: int,
    review_batches: int,
):
    manifest = {
        "dataset": dataset_name,
        "qualifying_products": len(selection.qualifying_products),
        "claude_reviews": len(selection.claude_reviews),
        "liwc_reviews": len(selection.liwc_reviews),
        "product_batches": product_batches,
        "review_batches": review_batches,
        "products_per_batch": PRODUCTS_PER_BATCH,
        "reviews_per_batch": REVIEWS_PER_BATCH,
        "product_asins": list(selection.qualifying_products.keys()),
        "status": {
            "products_completed": 0,
            "reviews_completed": 0,
        },
    }
    path = OUTPUT_DIR / dataset_name / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info(f"Manifest written to {path}")


def main():
    parser = argparse.ArgumentParser(description="Prepare annotation batches for Claude Max")
    parser.add_argument("--dataset", required=True, choices=list(DATASET_CONFIGS.keys()))
    parser.add_argument("--products-only", action="store_true")
    parser.add_argument("--reviews-only", action="store_true")
    args = parser.parse_args()

    cfg = DATASET_CONFIGS[args.dataset]

    logger.info(f"Loading dataset: {args.dataset}")

    if cfg["type"] == "amazon":
        if not os.path.exists(cfg["reviews"]):
            logger.error(f"Reviews file not found: {cfg['reviews']}")
            logger.error("Is the external drive mounted at /Volumes/Sped/?")
            sys.exit(1)
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

    logger.info(
        f"Selection: {len(selection.qualifying_products)} products, "
        f"{len(selection.claude_reviews)} claude reviews, "
        f"{len(selection.liwc_reviews)} liwc reviews"
    )

    product_batches = 0
    review_batches = 0

    if not args.reviews_only:
        product_batches = write_product_batches(selection, args.dataset)
    if not args.products_only:
        review_batches = write_review_batches(selection, args.dataset)

    write_manifest(selection, args.dataset, product_batches, review_batches)

    logger.info("=" * 60)
    logger.info("BATCH PREPARATION COMPLETE")
    logger.info(f"  Product batches: {product_batches}")
    logger.info(f"  Review batches:  {review_batches}")
    logger.info(f"  Output dir:      {OUTPUT_DIR / args.dataset}")
    logger.info("")
    logger.info("Next steps:")
    logger.info("  1. Open Claude Max at claude.ai")
    logger.info("  2. See docs/CLAUDE_MAX_ANNOTATION_INSTRUCTIONS.md for workflow")
    logger.info("  3. Paste each batch file, save JSON result")
    logger.info("  4. Run scripts/import_annotations_to_neo4j.py when done")


if __name__ == "__main__":
    main()
