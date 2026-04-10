"""
Optimized pipeline runner — Batch API + LIWC + best-review filter.

Processes 3 datasets:
  1. All_Beauty (Amazon JSONL + meta)
  2. Beauty_and_Personal_Care (Amazon JSONL + meta)
  3. Sephora (CSV + product_info.csv)

Strategy:
  - Top 20 best reviews per product → Claude Haiku 4.5 via Batch API
  - Remaining reviews → LIWC-lite (fast, local)
  - Product descriptions → Claude Haiku 4.5 via Batch API
  - Edges, ecosystems, priors → pure computation (no API)

Usage:
    nohup python3 adam/corpus/pipeline/optimized_runner.py 2>&1 | tee logs/pipeline.log &
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

# Ensure project root is on path
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
from adam.corpus.pipeline.batch_api import (
    create_batch,
    poll_batch,
    stream_results,
    MAX_BATCH_SIZE,
)
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
LOG_FILE = LOG_DIR / "pipeline.log"

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
for h in root_logger.handlers[:]:
    root_logger.removeHandler(h)

fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
fh = logging.FileHandler(str(LOG_FILE), mode="a")
fh.setFormatter(fmt)
root_logger.addHandler(fh)
sh = logging.StreamHandler(sys.stderr)
sh.setFormatter(fmt)
root_logger.addHandler(sh)

logger = logging.getLogger("adam.corpus.optimized")
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

CHECKPOINT_DIR = "checkpoints"

# =========================================================================
# PROMPTS (same as serial_runner.py)
# =========================================================================

AD_SYSTEM = "You are ADAM's psychological annotation engine. Score product descriptions against an advertising psychology taxonomy. Return ONLY valid JSON."

AD_PROMPT = """Score this product description.

Title: {title}
Category: {category}
Price: {price}
Brand: {brand}
Description: {desc}
Features: {feats}

Return JSON:
{{"annotation_confidence":<0-1>,"framing":{{"gain":<0-1>,"loss":<0-1>,"hedonic":<0-1>,"utilitarian":<0-1>}},"appeals":{{"rational":<0-1>,"emotional":<0-1>,"fear":<0-1>,"narrative":<0-1>,"comparative":<0-1>}},"processing_targets":{{"construal_level":<0-1>,"processing_route":<0-1>}},"persuasion_techniques":{{"social_proof":<0-1>,"scarcity":<0-1>,"authority":<0-1>,"reciprocity":<0-1>,"commitment":<0-1>,"liking":<0-1>,"anchoring":<0-1>,"storytelling":<0-1>}},"value_propositions":{{"performance":<0-1>,"convenience":<0-1>,"reliability":<0-1>,"cost":<0-1>,"pleasure":<0-1>,"peace_of_mind":<0-1>,"self_expression":<0-1>,"transformation":<0-1>,"status":<0-1>,"belonging":<0-1>,"social_responsibility":<0-1>,"novelty":<0-1>,"knowledge":<0-1>}},"brand_personality":{{"sincerity":<0-1>,"excitement":<0-1>,"competence":<0-1>,"sophistication":<0-1>,"ruggedness":<0-1>,"authenticity":<0-1>,"warmth":<0-1>}},"linguistic_style":{{"formality":<0-1>,"complexity":<0-1>,"emotional_tone":<-1 to 1>,"directness":<0-1>}},"evolutionary_targets":{{"self_protection":<0-1>,"affiliation":<0-1>,"status":<0-1>,"mate_acquisition":<0-1>,"kin_care":<0-1>,"disease_avoidance":<0-1>}},"implicit_targets":{{"fluency":<0-1>,"embodied_cognition":<0-1>,"psychological_ownership":<0-1>,"nonconscious_goal":<0-1>}}}}"""

REVIEW_SYSTEM = "You are ADAM's psychological annotation engine. Analyze reviews from TWO perspectives and return structured JSON. Return ONLY valid JSON."

DUAL_PROMPT = """Score this review from TWO perspectives.

Product: {title}  Category: {cat}  Rating: {rating}/5  Helpful: {helpful}  Verified: Yes

REVIEW: {text}

Perspective 1 (AUTHOR): What does this reveal about the reviewer's psychology?
Perspective 2 (PERSUASION): How does this function as persuasion for future readers?

{{"user_side":{{"annotation_confidence":<0-1>,"personality":{{"openness":<0-1>,"conscientiousness":<0-1>,"extraversion":<0-1>,"agreeableness":<0-1>,"neuroticism":<0-1>,"confidence_openness":<0-1>,"confidence_conscientiousness":<0-1>,"confidence_extraversion":<0-1>,"confidence_agreeableness":<0-1>,"confidence_neuroticism":<0-1>}},"regulatory_focus":{{"promotion":<0-1>,"prevention":<0-1>}},"decision_style":{{"maximizer":<0-1>,"impulse":<0-1>,"information_search_depth":<0-1>}},"construal_level":<0-1>,"need_for_cognition":<0-1>,"evolutionary_motives":{{"self_protection":<0-1>,"affiliation":<0-1>,"status":<0-1>,"mate_acquisition":<0-1>,"kin_care":<0-1>,"disease_avoidance":<0-1>}},"mechanisms_cited":{{"social_proof":<0-1>,"authority":<0-1>,"scarcity":<0-1>,"reciprocity":<0-1>,"commitment":<0-1>,"liking":<0-1>}},"emotion":{{"pleasure":<-1 to 1>,"arousal":<0-1>,"dominance":<0-1>,"primary_emotions":["up to 3"]}},"stated_purchase_reason":"<string>","implicit_drivers":{{"compensatory":<0-1>,"identity_signaling":<0-1>,"wanting_over_liking":<0-1>}},"lay_theories":{{"price_quality":<0-1>,"natural_goodness":<0-1>,"effort_quality":<0-1>,"scarcity_value":<0-1>}}}},"peer_ad_side":{{"annotation_confidence":<0-1>,"testimonial_authenticity":<0-1>,"relatable_vulnerability":<0-1>,"outcome_specificity":<0-1>,"outcome_timeline":<0-1>,"before_after_narrative":<0-1>,"risk_resolution":{{"financial":<0-1>,"performance":<0-1>,"social":<0-1>,"durability":<0-1>}},"use_case_matching":<0-1>,"social_proof_amplification":<0-1>,"objection_preemption":<0-1>,"domain_expertise_signals":<0-1>,"comparative_depth":<0-1>,"emotional_contagion_potency":<0-1>,"narrative_arc_completeness":<0-1>,"resolved_anxiety_narrative":<0-1>,"recommendation_strength":<0-1>}},"conversion_outcome":"<satisfied|neutral|regret|evangelized|warned>"}}"""


# =========================================================================
# HELPERS
# =========================================================================

def _product_to_ad_prompt(p: ProductRecord) -> str | None:
    """Build ad annotation prompt for a product. Returns None if no text."""
    desc = p.description
    feats = p.features
    if p.source == "sephora":
        # Sephora: use ingredients + highlights as description/features
        desc = p.description or ""
        feats = p.highlights or p.ingredients or ""

    if len(desc) < 20 and len(feats) < 20:
        return None

    return AD_PROMPT.format(
        title=p.title[:200],
        category=p.category,
        price=p.price or "unknown",
        brand=p.brand,
        desc=desc[:2000],
        feats=feats[:1000],
    )


def _review_to_dual_prompt(rev: ReviewRecord, products: dict[str, ProductRecord]) -> str:
    """Build dual-annotation prompt for a review."""
    prod = products.get(rev.product_id)
    title = prod.title if prod else "Beauty Product"
    cat = prod.category if prod else "Beauty"

    return DUAL_PROMPT.format(
        title=title[:200],
        cat=cat,
        rating=rev.rating,
        helpful=rev.helpful_votes,
        text=rev.text[:3000],
    )


# =========================================================================
# SUBMIT BATCHES (non-blocking — returns batch IDs)
# =========================================================================

def write_minimal_products(
    selections: list[DatasetSelection],
    writer: BulkWriter,
    ckpt: CheckpointManager,
):
    """Write products with no description text immediately (no Claude needed)."""
    logger.info("Writing minimal products (no description)...")
    completed = ckpt.load_completed("phase1")
    batch = []
    written = 0
    for sel in selections:
        for pid, prod in sel.qualifying_products.items():
            if pid in completed:
                continue
            prompt = _product_to_ad_prompt(prod)
            if prompt is None:
                props = {
                    "asin": prod.product_id,
                    "title": prod.title,
                    "main_category": prod.category,
                    "store": prod.brand,
                    "price": prod.price,
                    "average_rating": prod.average_rating,
                    "rating_number": prod.rating_count,
                    "source_dataset": prod.source,
                    "annotation_confidence": 0.1,
                    "annotation_tier": "minimal",
                }
                batch.append({"asin": prod.product_id, "properties": props})
                if len(batch) >= 500:
                    writer.write_product_descriptions(batch)
                    ckpt.mark_batch_completed("phase1", [r["asin"] for r in batch])
                    written += len(batch)
                    batch.clear()
    if batch:
        writer.write_product_descriptions(batch)
        ckpt.mark_batch_completed("phase1", [r["asin"] for r in batch])
        written += len(batch)
    logger.info(f"Wrote {written:,} minimal products")


def submit_phase_1_batches(
    client: anthropic.Anthropic,
    selections: list[DatasetSelection],
    ckpt: CheckpointManager,
) -> list[str]:
    """Submit product description annotation batches. Returns batch IDs."""
    logger.info("=" * 60)
    logger.info("SUBMITTING Phase 1 batches: Product Descriptions")
    logger.info("=" * 60)

    completed = ckpt.load_completed("phase1")
    batch_requests = []

    for sel in selections:
        for pid, prod in sel.qualifying_products.items():
            if pid in completed:
                continue
            prompt = _product_to_ad_prompt(prod)
            if prompt:
                batch_requests.append({
                    "custom_id": f"prod_{pid}",
                    "system": AD_SYSTEM,
                    "user_prompt": prompt,
                })

    logger.info(f"Phase 1: {len(batch_requests):,} products for Claude Batch API")
    if not batch_requests:
        return []

    # Submit in chunks
    batch_ids = []
    for i in range(0, len(batch_requests), MAX_BATCH_SIZE):
        chunk = batch_requests[i:i + MAX_BATCH_SIZE]
        bid = create_batch(client, chunk, f"P1 products [{i}..{i+len(chunk)}]")
        batch_ids.append(bid)
        logger.info(f"Submitted product batch: {bid} ({len(chunk):,} requests)")

    return batch_ids


def submit_phase_3_batches(
    client: anthropic.Anthropic,
    selections: list[DatasetSelection],
    ckpt: CheckpointManager,
) -> list[str]:
    """Submit review annotation batches. Returns batch IDs."""
    logger.info("=" * 60)
    logger.info("SUBMITTING Phase 3 batches: Review Annotations")
    logger.info("=" * 60)

    completed = ckpt.load_completed("phase3_claude")
    all_products: dict[str, ProductRecord] = {}
    for sel in selections:
        all_products.update(sel.qualifying_products)

    batch_requests = []
    for sel in selections:
        for rev in sel.claude_reviews:
            if rev.review_id in completed:
                continue
            prompt = _review_to_dual_prompt(rev, all_products)
            batch_requests.append({
                "custom_id": f"rev_{rev.review_id}",
                "system": REVIEW_SYSTEM,
                "user_prompt": prompt,
            })

    logger.info(f"Phase 3: {len(batch_requests):,} reviews for Claude Batch API")
    if not batch_requests:
        return []

    batch_ids = []
    for i in range(0, len(batch_requests), MAX_BATCH_SIZE):
        chunk = batch_requests[i:i + MAX_BATCH_SIZE]
        bid = create_batch(client, chunk, f"P3 reviews [{i}..{i+len(chunk)}]")
        batch_ids.append(bid)
        logger.info(f"Submitted review batch: {bid} ({len(chunk):,} requests)")
        if i + MAX_BATCH_SIZE < len(batch_requests):
            logger.info("Waiting 30s between batch submissions (rate limit)...")
            time.sleep(30)

    return batch_ids


# =========================================================================
# INGEST BATCH RESULTS (blocking — polls until done)
# =========================================================================

def ingest_product_batch_results(
    client: anthropic.Anthropic,
    batch_ids: list[str],
    selections: list[DatasetSelection],
    writer: BulkWriter,
    ckpt: CheckpointManager,
):
    """Poll product batches and write results to Neo4j."""
    if not batch_ids:
        logger.info("No product batches to ingest")
        return

    logger.info("=" * 60)
    logger.info(f"INGESTING Phase 1 results: {len(batch_ids)} batch(es)")
    logger.info("=" * 60)

    # Build product lookup
    all_products: dict[str, ProductRecord] = {}
    for sel in selections:
        all_products.update(sel.qualifying_products)

    annotated = 0
    errors = 0

    for bid in batch_ids:
        status = poll_batch(client, bid, poll_interval=30)
        if "error" in status:
            logger.error(f"Product batch {bid} failed: {status}")
            continue

        batch = []
        for custom_id, result in stream_results(client, bid):
            pid = custom_id.replace("prod_", "", 1)
            prod = all_products.get(pid)
            if not prod:
                continue

            if result:
                try:
                    ann = AdSideAnnotation(asin=pid, **result)
                    flat = ann.to_flat_dict()
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
                ckpt.mark_batch_completed("phase1", [r["asin"] for r in batch])
                batch.clear()

        if batch:
            writer.write_product_descriptions(batch)
            ckpt.mark_batch_completed("phase1", [r["asin"] for r in batch])

    logger.info(f"Phase 1 ingestion done: annotated={annotated}, errors={errors}")


def ingest_review_batch_results(
    client: anthropic.Anthropic,
    batch_ids: list[str],
    selections: list[DatasetSelection],
    writer: BulkWriter,
    ckpt: CheckpointManager,
):
    """Poll review batches and write results to Neo4j."""
    if not batch_ids:
        logger.info("No review batches to ingest")
        return

    logger.info("=" * 60)
    logger.info(f"INGESTING Phase 3 results: {len(batch_ids)} batch(es)")
    logger.info("=" * 60)

    # Build review lookup
    review_lookup: dict[str, ReviewRecord] = {}
    for sel in selections:
        for rev in sel.claude_reviews:
            review_lookup[f"rev_{rev.review_id}"] = rev

    annotated = 0
    errors = 0

    for bid in batch_ids:
        status = poll_batch(client, bid, poll_interval=30)
        if "error" in status:
            logger.error(f"Review batch {bid} failed: {status}")
            continue

        review_batch: list[dict] = []
        reviewer_batch: list[dict] = []
        has_review_batch: list[dict] = []

        for custom_id, result in stream_results(client, bid):
            rev = review_lookup.get(custom_id)
            if not rev:
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

                peer_flat = {}
                if peer_data:
                    peer_ann = PeerAdSideAnnotation(review_id=rev.review_id, **peer_data)
                    peer_flat = peer_ann.to_flat_dict()

                annotated += 1
            except Exception as e:
                errors += 1
                logger.debug(f"Parse error for {rev.review_id}: {e}")
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

        # Flush
        if review_batch:
            writer.write_annotated_reviews(review_batch)
            writer.write_reviewers([{"reviewer_id": r["reviewer_id"]} for r in reviewer_batch])
            writer.write_authored_edges(reviewer_batch)
            writer.write_has_review_edges(has_review_batch)
            ckpt.mark_batch_completed("phase3_claude", [r["review_id"] for r in review_batch])

    logger.info(f"Phase 3 ingestion done: annotated={annotated}, errors={errors}")


# =========================================================================
# PHASE 2: LIWC ANNOTATION (fast, local)
# =========================================================================

def run_phase_2_liwc(
    selections: list[DatasetSelection],
    writer: BulkWriter,
    ckpt: CheckpointManager,
):
    """Annotate remaining reviews with LIWC-lite (fast, local, no API)."""
    logger.info("=" * 60)
    logger.info("PHASE 2: LIWC Annotation (local, fast)")
    logger.info("=" * 60)

    completed = ckpt.load_completed("phase2_liwc")
    logger.info(f"Resuming from {len(completed)} checkpointed LIWC reviews")

    total_liwc = sum(len(s.liwc_reviews) for s in selections)
    logger.info(f"Total LIWC reviews to process: {total_liwc:,}")

    processed = 0
    review_batch: list[dict] = []
    reviewer_batch: list[dict] = []
    has_review_batch: list[dict] = []
    t0 = time.time()

    for sel in selections:
        for rev in sel.liwc_reviews:
            if rev.review_id in completed:
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

                if processed % 10_000 == 0:
                    rate = processed / (time.time() - t0)
                    eta = (total_liwc - processed) / rate / 60 if rate > 0 else 0
                    logger.info(
                        f"LIWC: {processed:,}/{total_liwc:,} ({rate:.0f}/s, ETA {eta:.0f}min)"
                    )

    # Flush
    if review_batch:
        writer.write_annotated_reviews(review_batch)
        writer.write_reviewers([{"reviewer_id": r["reviewer_id"]} for r in reviewer_batch])
        writer.write_authored_edges(reviewer_batch)
        writer.write_has_review_edges(has_review_batch)
        ckpt.mark_batch_completed("phase2_liwc", [r["review_id"] for r in review_batch])

    elapsed = time.time() - t0
    logger.info(f"LIWC done: {processed:,} reviews in {elapsed:.0f}s ({processed/max(elapsed,1):.0f}/s)")




# =========================================================================
# PHASES 4-8 (imported from orchestrator — no Claude, all computation)
# =========================================================================

from adam.corpus.pipeline.orchestrator import (
    run_phase_4, run_phase_5, run_phase_6, run_phase_7, run_phase_8,
)


# =========================================================================
# MAIN
# =========================================================================

def main():
    t0 = time.time()

    logger.info("=" * 60)
    logger.info("ADAM Corpus Pipeline — OPTIMIZED (Batch + LIWC + Best Reviews)")
    logger.info("=" * 60)

    # Connect
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    logger.info(f"Connected to Neo4j at {NEO4J_URI}")

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    client = anthropic.Anthropic(api_key=api_key)

    writer = BulkWriter(driver, batch_size=500)
    ckpt = CheckpointManager(CHECKPOINT_DIR)

    # Phase 0: Schema
    logger.info("=== PHASE 0: Schema ===")
    apply_schema(driver)

    # Select reviews from all datasets
    logger.info("=" * 60)
    logger.info("SELECTING REVIEWS FROM ALL DATASETS")
    logger.info("=" * 60)

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

    # Deduplicate across datasets (All_Beauty is subset of B&PC)
    logger.info("Deduplicating across datasets...")
    seen_products: set[str] = set()
    seen_reviews: set[str] = set()

    for sel in selections:
        # Deduplicate products
        deduped_products = {}
        for pid, prod in sel.qualifying_products.items():
            if pid not in seen_products:
                deduped_products[pid] = prod
                seen_products.add(pid)
        orig_p = len(sel.qualifying_products)
        sel.qualifying_products = deduped_products

        # Deduplicate Claude reviews
        deduped_claude = []
        for rev in sel.claude_reviews:
            if rev.review_id not in seen_reviews:
                deduped_claude.append(rev)
                seen_reviews.add(rev.review_id)
        orig_c = len(sel.claude_reviews)
        sel.claude_reviews = deduped_claude

        # Deduplicate LIWC reviews
        deduped_liwc = []
        for rev in sel.liwc_reviews:
            if rev.review_id not in seen_reviews:
                deduped_liwc.append(rev)
                seen_reviews.add(rev.review_id)
        orig_l = len(sel.liwc_reviews)
        sel.liwc_reviews = deduped_liwc

        if orig_p != len(sel.qualifying_products) or orig_c != len(sel.claude_reviews) or orig_l != len(sel.liwc_reviews):
            logger.info(
                f"  {sel.name}: removed {orig_p - len(sel.qualifying_products)} dup products, "
                f"{orig_c - len(sel.claude_reviews)} dup Claude, "
                f"{orig_l - len(sel.liwc_reviews)} dup LIWC"
            )

    # Summary
    total_products = sum(len(s.qualifying_products) for s in selections)
    total_claude = sum(len(s.claude_reviews) for s in selections)
    total_liwc = sum(len(s.liwc_reviews) for s in selections)
    logger.info("=" * 60)
    logger.info(f"SELECTION SUMMARY (after dedup):")
    for sel in selections:
        logger.info(
            f"  {sel.name}: {len(sel.qualifying_products):,} products, "
            f"{len(sel.claude_reviews):,} Claude, {len(sel.liwc_reviews):,} LIWC"
        )
    logger.info(f"  TOTAL: {total_products:,} products, {total_claude:,} Claude, {total_liwc:,} LIWC")
    logger.info("=" * 60)

    # === STEP 1: Submit Batch API jobs for products + best reviews ===
    # Load previously submitted batch IDs (resume support)
    batch_id_dir = Path(CHECKPOINT_DIR)
    prod_batch_file = batch_id_dir / "product_batch_ids.txt"
    rev_batch_file = batch_id_dir / "review_batch_ids.txt"

    if prod_batch_file.exists():
        product_batch_ids = [l.strip() for l in prod_batch_file.read_text().splitlines() if l.strip()]
        logger.info(f"Resuming {len(product_batch_ids)} previously submitted product batch(es)")
    else:
        product_batch_ids = submit_phase_1_batches(client, selections, ckpt)
        prod_batch_file.write_text("\n".join(product_batch_ids) + "\n")
        if product_batch_ids:
            logger.info("Waiting 30s before submitting review batches (rate limit)...")
            time.sleep(30)

    if rev_batch_file.exists():
        review_batch_ids = [l.strip() for l in rev_batch_file.read_text().splitlines() if l.strip()]
        logger.info(f"Resuming {len(review_batch_ids)} previously submitted review batch(es)")
    else:
        review_batch_ids = submit_phase_3_batches(client, selections, ckpt)
        rev_batch_file.write_text("\n".join(review_batch_ids) + "\n")

    # === STEP 2: While batches process, run LIWC locally (fast) ===
    # Also write minimal products immediately
    write_minimal_products(selections, writer, ckpt)
    run_phase_2_liwc(selections, writer, ckpt)

    # === STEP 3: Poll and ingest batch results ===
    ingest_product_batch_results(client, product_batch_ids, selections, writer, ckpt)
    ingest_review_batch_results(client, review_batch_ids, selections, writer, ckpt)

    # === STEP 4: Compute edges (pure math, no API) ===
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

    # Final stats
    from adam.corpus.quality.validation import run_full_validation, get_graph_stats
    logger.info("=== VALIDATION ===")
    run_full_validation(driver)
    stats = get_graph_stats(driver)
    driver.close()

    elapsed = time.time() - t0
    logger.info("=" * 60)
    logger.info(f"PIPELINE COMPLETE in {elapsed:.0f}s ({elapsed/3600:.1f}h)")
    for k, v in stats.items():
        logger.info(f"  {k}: {v}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
