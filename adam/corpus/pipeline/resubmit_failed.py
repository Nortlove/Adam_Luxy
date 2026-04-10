"""
Resubmit failed batch items from the original pipeline run.

Collects the custom_ids that errored in each batch,
rebuilds their prompts from the original data,
and submits new batches.
"""

from __future__ import annotations

import json
import logging
import os
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

from adam.corpus.pipeline.review_selector import (
    select_amazon_dataset,
    select_sephora_dataset,
    DatasetSelection,
    ReviewRecord,
    ProductRecord,
)
from adam.corpus.pipeline.batch_api import create_batch, MAX_BATCH_SIZE

LOG_DIR = Path(__file__).parent.parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(str(LOG_DIR / "resubmit.log"), mode="a"),
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger("adam.corpus.resubmit")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)

# Prompts — imported from canonical prompt_templates (single source of truth)
from adam.corpus.annotators.prompt_templates import (
    AD_SIDE_SYSTEM_PROMPT as AD_SYSTEM,
    AD_SIDE_COMPACT_TEMPLATE as AD_PROMPT,
    DUAL_SYSTEM_PROMPT as REVIEW_SYSTEM,
    DUAL_COMPACT_TEMPLATE as DUAL_PROMPT,
)


DATASETS = {
    "all_beauty": {
        "reviews": "/Volumes/Sped/Review Data/Amazon/All_Beauty.jsonl",
        "meta": "/Volumes/Sped/Review Data/Amazon/meta_All_Beauty.jsonl",
        "type": "amazon",
        "min_reviews": 25,
        "top_n": 20,
    },
    "bpc": {
        "reviews": "/Volumes/Sped/Review Data/Amazon/Beauty_and_Personal_Care.jsonl",
        "meta": "/Volumes/Sped/Review Data/Amazon/meta_Beauty_and_Personal_Care.jsonl",
        "type": "amazon",
        "min_reviews": 50,
        "top_n": 20,
    },
    "sephora": {
        "dir": "/Volumes/Sped/Review Data/sephora_reviews",
        "type": "sephora",
        "min_reviews": 25,
        "top_n": 20,
    },
}

# Completed batch IDs from original run
PRODUCT_BATCHES = ["msgbatch_01KEBLT5fzf1MuTXCe1AhckH"]
REVIEW_BATCHES = [
    "msgbatch_011QjJgYX6b2qDkm3ihFSdtE",
    "msgbatch_01P61ohsb7Ed56CLRqPha3iL",
    "msgbatch_01KN1HdZAtXqvvB1SKkYjsm2",
    "msgbatch_013EFHjukuxRYKTo8BEGFkBD",
]


def collect_failed_ids(client: anthropic.Anthropic, batch_ids: list[str]) -> set[str]:
    """Collect all custom_ids that errored in the given batches."""
    failed: set[str] = set()
    for bid in batch_ids:
        logger.info(f"Scanning batch {bid} for failed items...")
        count = 0
        for result in client.messages.batches.results(bid):
            if result.result.type != "succeeded":
                failed.add(result.custom_id)
                count += 1
        logger.info(f"  {count:,} failed in {bid}")
    return failed


def main():
    t0 = time.time()
    logger.info("=" * 60)
    logger.info("RESUBMIT FAILED BATCH ITEMS")
    logger.info("=" * 60)

    client = anthropic.Anthropic()

    # Step 1: Collect failed IDs from all batches
    logger.info("Collecting failed IDs from product batches...")
    failed_products = collect_failed_ids(client, PRODUCT_BATCHES)
    logger.info(f"Total failed products: {len(failed_products):,}")

    logger.info("Collecting failed IDs from review batches...")
    failed_reviews = collect_failed_ids(client, REVIEW_BATCHES)
    logger.info(f"Total failed reviews: {len(failed_reviews):,}")

    # Step 2: Re-select data (need prompts)
    logger.info("Re-selecting data to rebuild prompts...")
    selections: list[DatasetSelection] = []
    for name, cfg in DATASETS.items():
        if cfg["type"] == "amazon":
            sel = select_amazon_dataset(
                reviews_path=cfg["reviews"],
                meta_path=cfg["meta"],
                source_name=name,
                min_reviews=cfg["min_reviews"],
                top_n_per_product=cfg["top_n"],
            )
        elif cfg["type"] == "sephora":
            sel = select_sephora_dataset(
                reviews_dir=cfg["dir"],
                min_reviews=cfg["min_reviews"],
                top_n_per_product=cfg["top_n"],
            )
        else:
            continue
        selections.append(sel)

    # Deduplicate across datasets
    seen_products: set[str] = set()
    seen_reviews: set[str] = set()
    for sel in selections:
        sel.qualifying_products = {
            pid: p for pid, p in sel.qualifying_products.items()
            if pid not in seen_products and not seen_products.add(pid)
        }
        sel.claude_reviews = [
            r for r in sel.claude_reviews
            if r.review_id not in seen_reviews and not seen_reviews.add(r.review_id)
        ]

    # Build lookups
    all_products: dict[str, ProductRecord] = {}
    all_reviews: dict[str, ReviewRecord] = {}
    for sel in selections:
        all_products.update(sel.qualifying_products)
        for rev in sel.claude_reviews:
            all_reviews[f"rev_{rev.review_id}"] = rev

    # Step 3: Build product resubmission requests
    product_requests: list[dict] = []
    for custom_id in failed_products:
        pid = custom_id.replace("prod_", "", 1)
        prod = all_products.get(pid)
        if not prod:
            continue

        desc = prod.description or ""
        feats = prod.features or ""
        if prod.source == "sephora":
            desc = prod.description or ""
            feats = prod.highlights or prod.ingredients or ""
        if len(desc) < 20 and len(feats) < 20:
            continue

        prompt = AD_PROMPT.format(
            title=prod.title[:200],
            category=prod.category,
            price=prod.price or "unknown",
            brand=prod.brand,
            desc=desc[:2000],
            feats=feats[:1000],
        )
        product_requests.append({
            "custom_id": custom_id,
            "system": AD_SYSTEM,
            "user_prompt": prompt,
        })

    logger.info(f"Product requests rebuilt: {len(product_requests):,}")

    # Step 4: Build review resubmission requests
    review_requests: list[dict] = []
    for custom_id in failed_reviews:
        rev = all_reviews.get(custom_id)
        if not rev:
            continue

        prod = all_products.get(rev.product_id)
        title = prod.title if prod else "Beauty Product"
        cat = prod.category if prod else "Beauty"

        prompt = DUAL_PROMPT.format(
            title=title[:200],
            cat=cat,
            rating=rev.rating,
            helpful=rev.helpful_votes,
            text=rev.text[:3000],
        )
        review_requests.append({
            "custom_id": custom_id,
            "system": REVIEW_SYSTEM,
            "user_prompt": prompt,
        })

    logger.info(f"Review requests rebuilt: {len(review_requests):,}")

    # Step 5: Submit product batches
    checkpoint_dir = Path("checkpoints")
    checkpoint_dir.mkdir(exist_ok=True)
    new_batch_ids_file = checkpoint_dir / "resubmit_batch_ids.txt"

    all_new_ids: list[str] = []

    if product_requests:
        logger.info(f"Submitting {len(product_requests):,} product requests...")
        for i in range(0, len(product_requests), MAX_BATCH_SIZE):
            chunk = product_requests[i:i + MAX_BATCH_SIZE]
            bid = create_batch(client, chunk, description=f"resub_products_{i}")
            all_new_ids.append(f"prod:{bid}")
            logger.info(f"Product batch submitted: {bid} ({len(chunk):,} requests)")
            time.sleep(30)  # Rate limit

    # Step 6: Submit review batches
    if review_requests:
        logger.info(f"Submitting {len(review_requests):,} review requests...")
        for i in range(0, len(review_requests), MAX_BATCH_SIZE):
            chunk = review_requests[i:i + MAX_BATCH_SIZE]
            bid = create_batch(client, chunk, description=f"resub_reviews_{i}")
            all_new_ids.append(f"rev:{bid}")
            logger.info(f"Review batch submitted: {bid} ({len(chunk):,} requests)")
            time.sleep(30)  # Rate limit

    # Save batch IDs
    new_batch_ids_file.write_text("\n".join(all_new_ids) + "\n")
    logger.info(f"All batch IDs saved to {new_batch_ids_file}")

    elapsed = time.time() - t0
    logger.info(f"Resubmission complete in {elapsed:.0f}s")
    logger.info(f"Submitted {len(all_new_ids)} batches. Monitor with:")
    logger.info(f"  python3 -c \"import anthropic; c=anthropic.Anthropic(); print(c.messages.batches.retrieve('BATCH_ID').processing_status)\"")


if __name__ == "__main__":
    main()
