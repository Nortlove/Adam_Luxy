"""
High-throughput concurrent pipeline runner.

Uses asyncio with controlled concurrency for Claude API calls.
Processes all 8 phases with much higher throughput than serial execution.

Usage:
    python3 adam/corpus/pipeline/concurrent_runner.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Iterator

# Project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from neo4j import GraphDatabase

from adam.corpus.annotators.ad_side_annotator import AdSideAnnotator, SYSTEM_PROMPT as AD_SYSTEM, USER_PROMPT_TEMPLATE as AD_USER_TMPL
from adam.corpus.annotators.dual_annotator import (
    DualAnnotator,
    SYSTEM_PROMPT as DUAL_SYSTEM,
    DUAL_PROMPT_TEMPLATE,
    USER_ONLY_PROMPT_TEMPLATE,
    _should_dual_annotate,
)
from adam.corpus.annotators.base_annotator import BaseAnnotator, RateLimiter
from adam.corpus.models.ad_side_annotation import AdSideAnnotation
from adam.corpus.models.user_side_annotation import UserSideAnnotation
from adam.corpus.models.peer_ad_annotation import PeerAdSideAnnotation
from adam.corpus.edge_builders.match_calculators import compute_brand_buyer_edge
from adam.corpus.neo4j.bulk_writer import BulkWriter
from adam.corpus.neo4j.schema_extension import apply_schema
from adam.corpus.pipeline.checkpoint_manager import CheckpointManager
from adam.corpus.quality.validation import run_full_validation, get_graph_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("adam.corpus.concurrent")

# =========================================================================
# CONFIG
# =========================================================================

NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "atomofthought"
REVIEWS_PATH = "/Volumes/Sped/Review Data/Amazon/All_Beauty.jsonl"
PRODUCTS_PATH = "/Volumes/Sped/Review Data/Amazon/meta_All_Beauty.jsonl"
CHECKPOINT_DIR = "checkpoints"

# Concurrency control — stay within API rate limits
# Conservative to avoid 429s — Anthropic SDK retries internally too
MAX_CONCURRENT_CALLS = 2  # Claude parallel calls
BATCH_SIZE = 100  # Neo4j write batch size


# =========================================================================
# DATA LOADING
# =========================================================================

def iter_jsonl(path: str) -> Iterator[dict[str, Any]]:
    """Stream JSONL."""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def load_product_index(path: str) -> dict[str, dict]:
    """Load product metadata indexed by parent_asin."""
    logger.info(f"Loading product index...")
    index: dict[str, dict] = {}
    for record in iter_jsonl(path):
        key = record.get("parent_asin", record.get("asin", ""))
        if key:
            index[key] = record
    logger.info(f"Loaded {len(index)} products")
    return index


# =========================================================================
# PHASE 1: CONCURRENT PRODUCT ANNOTATION
# =========================================================================

async def annotate_product_async(
    annotator: BaseAnnotator,
    product: dict[str, Any],
    semaphore: asyncio.Semaphore,
) -> tuple[str, dict[str, Any]]:
    """Annotate a single product with semaphore-controlled concurrency."""
    asin = product.get("parent_asin", product.get("asin", ""))

    desc = " ".join(product.get("description", []))
    features = " ".join(product.get("features", []))
    title = product.get("title", "")
    has_text = len(desc) > 20 or len(features) > 20

    if not has_text:
        props = {
            "asin": asin,
            "title": title[:500],
            "main_category": product.get("main_category", ""),
            "store": product.get("store", ""),
            "price": str(product.get("price", "")),
            "average_rating": product.get("average_rating", 0.0),
            "rating_number": product.get("rating_number", 0),
            "annotation_confidence": 0.1,
            "annotation_tier": "minimal",
        }
        return asin, props

    prompt = AD_USER_TMPL.format(
        title=title[:200],
        category=product.get("main_category", ""),
        price=product.get("price", "unknown"),
        brand=product.get("store", "") or product.get("brand", ""),
        description_text=(desc or features or title)[:2000],
        features_text=(features if desc else "")[:1000],
    )

    async with semaphore:
        result = await annotator.call_claude(AD_SYSTEM, prompt)

    try:
        ann = AdSideAnnotation(asin=asin, **result)
        flat = ann.to_flat_dict()
    except Exception:
        flat = {"annotation_confidence": 0.1, "annotation_tier": "failed"}

    props = {
        "asin": asin,
        "title": title[:500],
        "main_category": product.get("main_category", ""),
        "store": product.get("store", ""),
        "price": str(product.get("price", "")),
        "average_rating": product.get("average_rating", 0.0),
        "rating_number": product.get("rating_number", 0),
        **flat,
    }
    return asin, props


async def run_phase_1_concurrent(
    writer: BulkWriter,
    checkpoint: CheckpointManager,
    api_key: str | None = None,
) -> dict[str, int]:
    """Phase 1: Annotate products concurrently."""
    logger.info("=== PHASE 1: Concurrent Product Annotation ===")

    rate_limiter = RateLimiter(calls_per_second=1.0, burst=2)
    annotator = BaseAnnotator(api_key=api_key, rate_limiter=rate_limiter)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_CALLS)

    completed = checkpoint.load_completed("phase1")
    logger.info(f"Resuming from {len(completed)} previously completed products")

    stats = {"annotated": 0, "minimal": 0, "errors": 0, "skipped": 0}

    # Collect products needing annotation
    products_to_annotate: list[dict] = []
    products_minimal: list[tuple[str, dict]] = []

    for record in iter_jsonl(PRODUCTS_PATH):
        asin = record.get("parent_asin", record.get("asin", ""))
        if not asin or asin in completed:
            stats["skipped"] += 1
            continue

        desc = " ".join(record.get("description", []))
        features = " ".join(record.get("features", []))

        if len(desc) > 20 or len(features) > 20:
            products_to_annotate.append(record)
        else:
            # Minimal annotation — no Claude needed
            props = {
                "asin": asin,
                "title": record.get("title", "")[:500],
                "main_category": record.get("main_category", ""),
                "store": record.get("store", ""),
                "price": str(record.get("price", "")),
                "average_rating": record.get("average_rating", 0.0),
                "rating_number": record.get("rating_number", 0),
                "annotation_confidence": 0.1,
                "annotation_tier": "minimal",
            }
            products_minimal.append((asin, props))

    logger.info(
        f"Products: {len(products_to_annotate)} need Claude, "
        f"{len(products_minimal)} minimal"
    )

    # Write minimal products first (no Claude needed)
    if products_minimal:
        batch = [{"asin": asin, "properties": props} for asin, props in products_minimal]
        for i in range(0, len(batch), 500):
            chunk = batch[i:i + 500]
            writer.write_product_descriptions(chunk)
            checkpoint.mark_batch_completed("phase1", [r["asin"] for r in chunk])
        stats["minimal"] = len(products_minimal)
        logger.info(f"Wrote {stats['minimal']} minimal products to Neo4j")

    # Annotate products with Claude in concurrent batches
    t0 = time.time()
    for batch_start in range(0, len(products_to_annotate), MAX_CONCURRENT_CALLS * 4):
        batch_products = products_to_annotate[batch_start:batch_start + MAX_CONCURRENT_CALLS * 4]

        tasks = [
            annotate_product_async(annotator, p, semaphore)
            for p in batch_products
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        neo4j_batch: list[dict] = []
        completed_ids: list[str] = []

        for res in results:
            if isinstance(res, Exception):
                stats["errors"] += 1
                logger.error(f"Annotation error: {res}")
                continue

            asin, props = res
            neo4j_batch.append({"asin": asin, "properties": props})
            completed_ids.append(asin)
            stats["annotated"] += 1

        if neo4j_batch:
            writer.write_product_descriptions(neo4j_batch)
            checkpoint.mark_batch_completed("phase1", completed_ids)

        elapsed = time.time() - t0
        total_done = stats["annotated"] + stats["errors"]
        rate = total_done / elapsed if elapsed > 0 else 0
        remaining = len(products_to_annotate) - total_done
        eta_min = remaining / rate / 60 if rate > 0 else 0

        if total_done % 100 == 0 or total_done == len(products_to_annotate):
            logger.info(
                f"Phase 1: {total_done}/{len(products_to_annotate)} annotated "
                f"({rate:.1f}/s, ETA {eta_min:.0f}m) | "
                f"errors={stats['errors']} | "
                f"tokens: {annotator.stats}"
            )

    logger.info(f"Phase 1 complete: {stats}")
    return stats


# =========================================================================
# PHASE 2+3: CONCURRENT REVIEW ANNOTATION
# =========================================================================

async def annotate_review_async(
    annotator: BaseAnnotator,
    review: dict[str, Any],
    product_title: str,
    category: str,
    semaphore: asyncio.Semaphore,
) -> tuple[str, dict[str, Any], dict[str, Any] | None]:
    """Annotate a single review (user-side + optional peer-ad-side)."""
    user_id = review.get("user_id", "unknown")
    asin = review.get("asin", review.get("parent_asin", "unknown"))
    ts = review.get("timestamp", 0)
    review_id = f"{user_id}_{asin}_{ts}"
    text = review.get("text", "")

    if not text or len(text) < 50:
        return review_id, {}, None

    dual = _should_dual_annotate(review)

    if dual:
        prompt = DUAL_PROMPT_TEMPLATE.format(
            product_title=product_title[:200],
            category=category,
            star_rating=review.get("rating", 0),
            helpful_votes=review.get("helpful_vote", 0),
            review_text=text[:3000],
        )
    else:
        prompt = USER_ONLY_PROMPT_TEMPLATE.format(
            product_title=product_title[:200],
            category=category,
            star_rating=review.get("rating", 0),
            helpful_votes=review.get("helpful_vote", 0),
            review_text=text[:3000],
        )

    async with semaphore:
        result = await annotator.call_claude(DUAL_SYSTEM, prompt)

    if dual:
        user_data = result.get("user_side", {})
        peer_data = result.get("peer_ad_side", {})
        conversion = result.get("conversion_outcome", "satisfied")
    else:
        user_data = result
        peer_data = None
        conversion = result.pop("conversion_outcome", "satisfied")

    # Build user annotation
    try:
        user_ann = UserSideAnnotation(
            review_id=review_id,
            conversion_outcome=conversion,
            **user_data,
        )
        user_flat = user_ann.to_flat_dict()
    except Exception:
        user_flat = {"annotation_confidence": 0.0}

    # Build peer annotation if dual
    peer_flat = None
    if peer_data:
        try:
            peer_ann = PeerAdSideAnnotation(review_id=review_id, **peer_data)
            peer_flat = peer_ann.to_flat_dict()
        except Exception:
            peer_flat = None

    # Build full node props
    node_props: dict[str, Any] = {
        "review_id": review_id,
        "asin": asin,
        "parent_asin": review.get("parent_asin", asin),
        "user_id": user_id,
        "star_rating": review.get("rating", 0),
        "helpful_votes": review.get("helpful_vote", 0),
        "verified_purchase": True,
        "timestamp": ts,
        "text_length": len(text),
        **user_flat,
    }
    if peer_flat:
        node_props.update(peer_flat)

    return review_id, node_props, peer_flat


async def run_phase_2_3_concurrent(
    product_index: dict[str, dict],
    writer: BulkWriter,
    checkpoint: CheckpointManager,
    api_key: str | None = None,
) -> dict[str, int]:
    """Phase 2+3: Concurrent review annotation."""
    logger.info("=== PHASE 2+3: Concurrent Review Annotation ===")

    rate_limiter = RateLimiter(calls_per_second=1.0, burst=2)
    annotator = BaseAnnotator(api_key=api_key, rate_limiter=rate_limiter)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_CALLS)

    completed = checkpoint.load_completed("phase2_3")
    logger.info(f"Resuming from {len(completed)} previously completed reviews")

    stats = {
        "user_annotated": 0, "dual_annotated": 0,
        "skipped_short": 0, "skipped_completed": 0,
        "skipped_unverified": 0, "errors": 0,
    }

    # Stream and batch reviews
    batch_reviews: list[tuple[dict, str, str]] = []  # (review, title, category)
    t0 = time.time()

    for record in iter_jsonl(REVIEWS_PATH):
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

        product = product_index.get(asin, product_index.get(record.get("parent_asin", ""), {}))
        product_title = product.get("title", "Beauty Product")
        category = product.get("main_category", "All Beauty")

        batch_reviews.append((record, product_title, category))

        # Process in concurrent batches
        if len(batch_reviews) >= MAX_CONCURRENT_CALLS * 4:
            batch_stats = await _process_review_batch(
                batch_reviews, annotator, semaphore, writer, checkpoint, stats
            )
            batch_reviews.clear()

            total_done = stats["user_annotated"] + stats["dual_annotated"]
            elapsed = time.time() - t0
            rate = total_done / elapsed if elapsed > 0 else 0

            if total_done % 200 == 0 and total_done > 0:
                logger.info(
                    f"Phase 2+3: {total_done} annotated ({rate:.1f}/s) | "
                    f"user={stats['user_annotated']} dual={stats['dual_annotated']} "
                    f"errors={stats['errors']} | tokens={annotator.stats}"
                )

    # Flush remaining
    if batch_reviews:
        await _process_review_batch(
            batch_reviews, annotator, semaphore, writer, checkpoint, stats
        )

    logger.info(f"Phase 2+3 complete: {stats}")
    return stats


async def _process_review_batch(
    batch_reviews: list[tuple[dict, str, str]],
    annotator: BaseAnnotator,
    semaphore: asyncio.Semaphore,
    writer: BulkWriter,
    checkpoint: CheckpointManager,
    stats: dict,
) -> None:
    """Process a batch of reviews concurrently."""
    tasks = [
        annotate_review_async(annotator, review, title, category, semaphore)
        for review, title, category in batch_reviews
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    review_batch: list[dict] = []
    reviewer_batch: list[dict] = []
    has_review_batch: list[dict] = []
    completed_ids: list[str] = []

    for i, res in enumerate(results):
        if isinstance(res, Exception):
            stats["errors"] += 1
            logger.error(f"Review annotation error: {res}")
            continue

        review_id, node_props, peer_flat = res
        if not node_props:
            stats["skipped_short"] += 1
            continue

        review_batch.append({"review_id": review_id, "properties": node_props})

        user_id = node_props.get("user_id", "unknown")
        asin = node_props.get("asin", "unknown")
        reviewer_batch.append({"reviewer_id": user_id, "review_id": review_id})
        has_review_batch.append({"product_asin": asin, "review_id": review_id})
        completed_ids.append(review_id)

        if peer_flat:
            stats["dual_annotated"] += 1
        else:
            stats["user_annotated"] += 1

    if review_batch:
        writer.write_annotated_reviews(review_batch)
        writer.write_reviewers(
            [{"reviewer_id": r["reviewer_id"]} for r in reviewer_batch]
        )
        writer.write_authored_edges(reviewer_batch)
        writer.write_has_review_edges(has_review_batch)
        checkpoint.mark_batch_completed("phase2_3", completed_ids)


# =========================================================================
# PHASES 4-8: Import from orchestrator (these are already efficient)
# =========================================================================

from adam.corpus.pipeline.orchestrator import (
    run_phase_4,
    run_phase_5,
    run_phase_6,
    run_phase_7,
    run_phase_8,
)


# =========================================================================
# MAIN
# =========================================================================

async def run_all_phases() -> dict[str, Any]:
    """Execute all 8 phases with concurrent Claude annotation."""
    all_stats: dict[str, Any] = {"start_time": time.time()}

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    logger.info(f"Connected to Neo4j at {NEO4J_URI}")

    writer = BulkWriter(driver, batch_size=500)
    checkpoint = CheckpointManager(CHECKPOINT_DIR)

    api_key = os.environ.get("ANTHROPIC_API_KEY")

    # Phase 0: Schema
    logger.info("=== PHASE 0: Schema Extension ===")
    apply_schema(driver)

    # Phase 1: Products (concurrent Claude)
    all_stats["phase1"] = await run_phase_1_concurrent(writer, checkpoint, api_key)

    # Phase 2+3: Reviews (concurrent Claude)
    product_index = load_product_index(PRODUCTS_PATH)
    all_stats["phase2_3"] = await run_phase_2_3_concurrent(
        product_index, writer, checkpoint, api_key
    )

    # Phase 4: Ecosystems (DB aggregation)
    all_stats["phase4"] = run_phase_4(driver, writer, checkpoint)

    # Phase 5: BRAND_CONVERTED edges (pure math)
    all_stats["phase5"] = run_phase_5(driver, writer, checkpoint)

    # Phase 6: PEER_INFLUENCED edges (pure math)
    all_stats["phase6"] = run_phase_6(driver, writer, checkpoint)

    # Phase 7: ECOSYSTEM_CONVERTED edges (pure math)
    all_stats["phase7"] = run_phase_7(driver, writer, checkpoint)

    # Phase 8: Bayesian priors
    all_stats["phase8"] = run_phase_8(driver)

    # Validation
    logger.info("=== VALIDATION ===")
    results = run_full_validation(driver)

    # Final stats
    graph_stats = get_graph_stats(driver)
    all_stats["graph_stats"] = graph_stats
    all_stats["neo4j_writer_stats"] = writer.stats
    all_stats["elapsed_s"] = time.time() - all_stats["start_time"]

    driver.close()

    logger.info("=" * 60)
    logger.info("PIPELINE COMPLETE")
    logger.info(f"Total time: {all_stats['elapsed_s']:.0f}s")
    for k, v in graph_stats.items():
        logger.info(f"  {k}: {v}")
    logger.info("=" * 60)

    return all_stats


def main():
    results = asyncio.run(run_all_phases())
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
