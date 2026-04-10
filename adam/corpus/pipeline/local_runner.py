"""
Local runner — ingest completed batch results + LIWC, no new API calls.

Reads results from already-completed Anthropic batches,
runs LIWC locally, computes edges and priors.
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
from neo4j import GraphDatabase

from adam.corpus.pipeline.review_selector import (
    select_amazon_dataset,
    select_sephora_dataset,
    DatasetSelection,
    ReviewRecord,
    ProductRecord,
)
from adam.corpus.pipeline.batch_api import stream_results
from adam.corpus.pipeline.liwc_scorer import score_review_liwc
from adam.corpus.neo4j.bulk_writer import BulkWriter
from adam.corpus.neo4j.schema_extension import apply_schema
from adam.corpus.pipeline.checkpoint_manager import CheckpointManager
from adam.corpus.models.ad_side_annotation import AdSideAnnotation
from adam.corpus.models.user_side_annotation import UserSideAnnotation
from adam.corpus.models.peer_ad_annotation import PeerAdSideAnnotation

# =========================================================================
# LOGGING
# =========================================================================

LOG_DIR = Path(__file__).parent.parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
for h in root_logger.handlers[:]:
    root_logger.removeHandler(h)

fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
fh = logging.FileHandler(str(LOG_DIR / "local_runner.log"), mode="a")
fh.setFormatter(fmt)
root_logger.addHandler(fh)
sh = logging.StreamHandler(sys.stderr)
sh.setFormatter(fmt)
root_logger.addHandler(sh)

logger = logging.getLogger("adam.corpus.local")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)
logging.getLogger("neo4j.notifications").setLevel(logging.WARNING)

# =========================================================================
# CONFIG
# =========================================================================

NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "atomofthought"

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

# Completed batch IDs
PRODUCT_BATCHES = ["msgbatch_01KEBLT5fzf1MuTXCe1AhckH"]
REVIEW_BATCHES = [
    "msgbatch_011QjJgYX6b2qDkm3ihFSdtE",
    "msgbatch_01P61ohsb7Ed56CLRqPha3iL",
    "msgbatch_01KN1HdZAtXqvvB1SKkYjsm2",
    "msgbatch_013EFHjukuxRYKTo8BEGFkBD",
]

CHECKPOINT_DIR = "checkpoints"


# =========================================================================
# STEP 1: Write ALL product metadata to Neo4j (no Claude needed)
# =========================================================================

def write_all_products(
    selections: list[DatasetSelection],
    writer: BulkWriter,
    ckpt: CheckpointManager,
):
    """Write all product metadata to Neo4j with basic properties."""
    logger.info("=" * 60)
    logger.info("STEP 1: Writing all product metadata to Neo4j")
    logger.info("=" * 60)

    completed = ckpt.load_completed("phase1_meta")
    total = sum(len(s.qualifying_products) for s in selections)
    logger.info(f"Total products: {total:,}, already done: {len(completed):,}")

    batch = []
    written = 0
    for sel in selections:
        for pid, prod in sel.qualifying_products.items():
            if pid in completed:
                continue
            props = {
                "asin": prod.product_id,
                "title": prod.title,
                "main_category": prod.category,
                "store": prod.brand,
                "price": prod.price,
                "average_rating": prod.average_rating,
                "rating_number": prod.rating_count,
                "source_dataset": prod.source,
                "annotation_tier": "metadata",
                "annotation_confidence": 0.1,
            }
            # Add Sephora-specific fields
            if prod.ingredients:
                props["ingredients"] = prod.ingredients[:2000]
            if prod.highlights:
                props["highlights"] = prod.highlights[:1000]
            if prod.description:
                props["description_text"] = prod.description[:2000]
            if prod.features:
                props["features_text"] = prod.features[:1000]

            batch.append({"asin": pid, "properties": props})
            if len(batch) >= 500:
                writer.write_product_descriptions(batch)
                ckpt.mark_batch_completed("phase1_meta", [r["asin"] for r in batch])
                written += len(batch)
                batch.clear()
                if written % 5000 == 0:
                    logger.info(f"  Products written: {written:,}/{total:,}")

    if batch:
        writer.write_product_descriptions(batch)
        ckpt.mark_batch_completed("phase1_meta", [r["asin"] for r in batch])
        written += len(batch)

    logger.info(f"Step 1 done: wrote {written:,} products")


# =========================================================================
# STEP 2: Ingest completed batch results (products + reviews)
# =========================================================================

def ingest_product_batches(
    client: anthropic.Anthropic,
    selections: list[DatasetSelection],
    writer: BulkWriter,
    ckpt: CheckpointManager,
):
    """Ingest completed product annotation batches."""
    logger.info("=" * 60)
    logger.info("STEP 2a: Ingesting product batch results")
    logger.info("=" * 60)

    completed = ckpt.load_completed("phase1_claude")
    all_products: dict[str, ProductRecord] = {}
    for sel in selections:
        all_products.update(sel.qualifying_products)

    annotated = 0
    errors = 0

    for bid in PRODUCT_BATCHES:
        logger.info(f"Reading results from batch {bid}...")
        batch = []
        for custom_id, result in stream_results(client, bid):
            pid = custom_id.replace("prod_", "", 1)
            if pid in completed:
                continue
            prod = all_products.get(pid)
            if not prod:
                continue

            if result:
                try:
                    ann = AdSideAnnotation(asin=pid, **result)
                    flat = ann.to_flat_dict()
                    flat["annotation_tier"] = "claude"
                    annotated += 1
                except Exception:
                    flat = {"annotation_confidence": 0.1, "annotation_tier": "failed"}
                    errors += 1
            else:
                flat = {"annotation_confidence": 0.1, "annotation_tier": "failed"}
                errors += 1

            props = {
                "asin": pid,
                "title": prod.title,
                "main_category": prod.category,
                "store": prod.brand,
                "price": prod.price,
                "average_rating": prod.average_rating,
                "rating_number": prod.rating_count,
                "source_dataset": prod.source,
                **flat,
            }
            batch.append({"asin": pid, "properties": props})

            if len(batch) >= 500:
                writer.write_product_descriptions(batch)
                ckpt.mark_batch_completed("phase1_claude", [r["asin"] for r in batch])
                batch.clear()

        if batch:
            writer.write_product_descriptions(batch)
            ckpt.mark_batch_completed("phase1_claude", [r["asin"] for r in batch])

    logger.info(f"Product batches: {annotated:,} annotated, {errors:,} errors")


def ingest_review_batches(
    client: anthropic.Anthropic,
    selections: list[DatasetSelection],
    writer: BulkWriter,
    ckpt: CheckpointManager,
):
    """Ingest completed review annotation batches."""
    logger.info("=" * 60)
    logger.info("STEP 2b: Ingesting review batch results")
    logger.info("=" * 60)

    completed = ckpt.load_completed("phase3_claude")

    # Build review lookup from all selections
    review_lookup: dict[str, ReviewRecord] = {}
    for sel in selections:
        for rev in sel.claude_reviews:
            review_lookup[f"rev_{rev.review_id}"] = rev

    logger.info(f"Review lookup: {len(review_lookup):,} reviews, {len(completed):,} already done")

    annotated = 0
    errors = 0
    skipped = 0

    for bid in REVIEW_BATCHES:
        logger.info(f"Reading results from batch {bid}...")
        review_batch: list[dict] = []
        reviewer_batch: list[dict] = []
        has_review_batch: list[dict] = []

        for custom_id, result in stream_results(client, bid):
            rev = review_lookup.get(custom_id)
            if not rev:
                skipped += 1
                continue
            if rev.review_id in completed:
                continue

            if not result:
                errors += 1
                continue

            try:
                user_data = result.get("user_side", {})
                peer_data = result.get("peer_ad_side", {})
                conversion = result.get("conversion_outcome", "satisfied")

                user_ann = UserSideAnnotation(
                    review_id=rev.review_id,
                    conversion_outcome=conversion,
                    **user_data,
                )
                user_flat = user_ann.to_flat_dict()
                user_flat["annotation_tier"] = "claude"

                peer_flat = {}
                if peer_data:
                    peer_ann = PeerAdSideAnnotation(review_id=rev.review_id, **peer_data)
                    peer_flat = peer_ann.to_flat_dict()

                annotated += 1
            except Exception as e:
                errors += 1
                continue

            node_props: dict[str, Any] = {
                "review_id": rev.review_id,
                "asin": rev.product_id,
                "parent_asin": rev.product_id,
                "user_id": rev.user_id,
                "star_rating": rev.rating,
                "helpful_votes": rev.helpful_votes,
                "verified_purchase": True,
                "timestamp": rev.timestamp,
                "text_length": len(rev.text),
                "source_dataset": rev.source,
                **user_flat,
            }
            if peer_flat:
                node_props.update(peer_flat)

            review_batch.append({"review_id": rev.review_id, "properties": node_props})
            reviewer_batch.append({"reviewer_id": rev.user_id, "review_id": rev.review_id})
            has_review_batch.append({"product_asin": rev.product_id, "review_id": rev.review_id})

            if len(review_batch) >= 500:
                writer.write_annotated_reviews(review_batch)
                writer.write_reviewers([{"reviewer_id": r["reviewer_id"]} for r in reviewer_batch])
                writer.write_authored_edges(reviewer_batch)
                writer.write_has_review_edges(has_review_batch)
                ckpt.mark_batch_completed("phase3_claude", [r["review_id"] for r in review_batch])
                review_batch.clear()
                reviewer_batch.clear()
                has_review_batch.clear()
                logger.info(f"  Claude reviews: {annotated:,} ingested, {errors:,} errors")

        if review_batch:
            writer.write_annotated_reviews(review_batch)
            writer.write_reviewers([{"reviewer_id": r["reviewer_id"]} for r in reviewer_batch])
            writer.write_authored_edges(reviewer_batch)
            writer.write_has_review_edges(has_review_batch)
            ckpt.mark_batch_completed("phase3_claude", [r["review_id"] for r in review_batch])

    logger.info(f"Review batches: {annotated:,} annotated, {errors:,} errors, {skipped:,} skipped (no match)")


# =========================================================================
# STEP 3: LIWC annotation (fast, local, no API)
# =========================================================================

def run_liwc(
    selections: list[DatasetSelection],
    writer: BulkWriter,
    ckpt: CheckpointManager,
):
    """Annotate remaining reviews with LIWC-lite."""
    logger.info("=" * 60)
    logger.info("STEP 3: LIWC Annotation (local)")
    logger.info("=" * 60)

    completed = ckpt.load_completed("phase2_liwc")
    claude_done = ckpt.load_completed("phase3_claude")
    total_liwc = sum(len(s.liwc_reviews) for s in selections)
    logger.info(f"LIWC reviews: {total_liwc:,}, already done: {len(completed):,}")

    processed = 0
    review_batch: list[dict] = []
    reviewer_batch: list[dict] = []
    has_review_batch: list[dict] = []
    t0 = time.time()

    for sel in selections:
        for rev in sel.liwc_reviews:
            if rev.review_id in completed or rev.review_id in claude_done:
                continue

            scores = score_review_liwc(rev.text, rev.rating, rev.helpful_votes)

            node_props: dict[str, Any] = {
                "review_id": rev.review_id,
                "asin": rev.product_id,
                "parent_asin": rev.product_id,
                "user_id": rev.user_id,
                "star_rating": rev.rating,
                "helpful_votes": rev.helpful_votes,
                "verified_purchase": True,
                "timestamp": rev.timestamp,
                "text_length": len(rev.text),
                "source_dataset": rev.source,
                **scores,
            }

            review_batch.append({"review_id": rev.review_id, "properties": node_props})
            reviewer_batch.append({"reviewer_id": rev.user_id, "review_id": rev.review_id})
            has_review_batch.append({"product_asin": rev.product_id, "review_id": rev.review_id})
            processed += 1

            if len(review_batch) >= 500:
                writer.write_annotated_reviews(review_batch)
                writer.write_reviewers([{"reviewer_id": r["reviewer_id"]} for r in reviewer_batch])
                writer.write_authored_edges(reviewer_batch)
                writer.write_has_review_edges(has_review_batch)
                ckpt.mark_batch_completed("phase2_liwc", [r["review_id"] for r in review_batch])
                review_batch.clear()
                reviewer_batch.clear()
                has_review_batch.clear()

                if processed % 50_000 == 0:
                    rate = processed / (time.time() - t0)
                    eta = (total_liwc - processed) / rate / 60 if rate > 0 else 0
                    logger.info(
                        f"  LIWC: {processed:,}/{total_liwc:,} ({rate:.0f}/s, ETA {eta:.0f}min)"
                    )

    if review_batch:
        writer.write_annotated_reviews(review_batch)
        writer.write_reviewers([{"reviewer_id": r["reviewer_id"]} for r in reviewer_batch])
        writer.write_authored_edges(reviewer_batch)
        writer.write_has_review_edges(has_review_batch)
        ckpt.mark_batch_completed("phase2_liwc", [r["review_id"] for r in review_batch])

    elapsed = time.time() - t0
    logger.info(f"LIWC done: {processed:,} in {elapsed:.0f}s ({processed/max(elapsed,1):.0f}/s)")


# =========================================================================
# MAIN
# =========================================================================

def main():
    t0 = time.time()

    logger.info("=" * 60)
    logger.info("ADAM Local Runner — Ingest Batches + LIWC (no new API calls)")
    logger.info("=" * 60)

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    client = anthropic.Anthropic()  # only for reading batch results
    writer = BulkWriter(driver, batch_size=500)
    ckpt = CheckpointManager(CHECKPOINT_DIR)

    # Schema
    apply_schema(driver)

    # Select reviews (same logic as optimized_runner)
    logger.info("Selecting reviews from all datasets...")
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

    # Dedup
    seen_products: set[str] = set()
    seen_reviews: set[str] = set()
    for sel in selections:
        deduped_p = {pid: p for pid, p in sel.qualifying_products.items() if pid not in seen_products and not seen_products.add(pid)}
        sel.qualifying_products = deduped_p
        deduped_c = [r for r in sel.claude_reviews if r.review_id not in seen_reviews and not seen_reviews.add(r.review_id)]
        sel.claude_reviews = deduped_c
        deduped_l = [r for r in sel.liwc_reviews if r.review_id not in seen_reviews and not seen_reviews.add(r.review_id)]
        sel.liwc_reviews = deduped_l

    total_p = sum(len(s.qualifying_products) for s in selections)
    total_c = sum(len(s.claude_reviews) for s in selections)
    total_l = sum(len(s.liwc_reviews) for s in selections)
    logger.info(f"After dedup: {total_p:,} products, {total_c:,} Claude, {total_l:,} LIWC")

    # Step 1: Write all products (metadata only)
    write_all_products(selections, writer, ckpt)

    # Step 2a: Ingest product Claude annotations (overlay on top)
    ingest_product_batches(client, selections, writer, ckpt)

    # Step 2b: Ingest review Claude annotations
    ingest_review_batches(client, selections, writer, ckpt)

    # Step 3: LIWC for remaining reviews
    run_liwc(selections, writer, ckpt)

    # Step 4-8: Computation phases
    from adam.corpus.pipeline.orchestrator import (
        run_phase_4, run_phase_5, run_phase_6, run_phase_7, run_phase_8,
    )
    logger.info("=== PHASE 4: Product Ecosystems ===")
    run_phase_4(driver, writer, ckpt)
    logger.info("=== PHASE 5: BRAND_CONVERTED edges ===")
    run_phase_5(driver, writer, ckpt)
    logger.info("=== PHASE 6: PEER_INFLUENCED edges ===")
    run_phase_6(driver, writer, ckpt)
    logger.info("=== PHASE 7: ECOSYSTEM_CONVERTED edges ===")
    run_phase_7(driver, writer, ckpt)
    logger.info("=== PHASE 8: Bayesian Priors ===")
    run_phase_8(driver)

    # Stats
    with driver.session() as session:
        stats = {}
        for label in ["ProductDescription", "AnnotatedReview", "Reviewer", "ProductEcosystem"]:
            count = session.run(f"MATCH (n:{label}) RETURN count(n) AS c").single()["c"]
            stats[label] = count
        for rel in ["HAS_REVIEW", "AUTHORED", "BRAND_CONVERTED", "PEER_INFLUENCED", "ECOSYSTEM_CONVERTED"]:
            count = session.run(f"MATCH ()-[r:{rel}]->() RETURN count(r) AS c").single()["c"]
            stats[f"rel_{rel}"] = count

    driver.close()

    elapsed = time.time() - t0
    logger.info("=" * 60)
    logger.info(f"LOCAL RUNNER COMPLETE in {elapsed:.0f}s ({elapsed/3600:.1f}h)")
    for k, v in stats.items():
        logger.info(f"  {k}: {v:,}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
