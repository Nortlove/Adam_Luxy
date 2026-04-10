"""
Serial pipeline runner — 25+ review filter, rate-limit-safe.

Filters to products with 25+ reviews (2,748 products, 184,945 reviews).
This keeps 41% of all review data while cutting Claude calls by 60%,
focusing on the most statistically valuable products.

At 5 RPM: ~26 days for full completion.

Usage:
    nohup python3 adam/corpus/pipeline/serial_runner.py &
    tail -f logs/pipeline.log
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any, Iterator

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import anthropic
from neo4j import GraphDatabase

from adam.corpus.models.ad_side_annotation import AdSideAnnotation
from adam.corpus.models.user_side_annotation import UserSideAnnotation
from adam.corpus.models.peer_ad_annotation import PeerAdSideAnnotation
from adam.corpus.edge_builders.match_calculators import compute_brand_buyer_edge
from adam.corpus.neo4j.bulk_writer import BulkWriter
from adam.corpus.neo4j.schema_extension import apply_schema
from adam.corpus.pipeline.checkpoint_manager import CheckpointManager
from adam.corpus.quality.validation import run_full_validation, get_graph_stats

# =========================================================================
# LOGGING — writes to file + stderr
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

logger = logging.getLogger("adam.corpus.serial")

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)
logging.getLogger("anthropic._base_client").setLevel(logging.WARNING)
logging.getLogger("neo4j.notifications").setLevel(logging.WARNING)

# =========================================================================
# CONFIG
# =========================================================================

NEO4J_URI = "neo4j://127.0.0.1:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "atomofthought"
REVIEWS_PATH = "/Volumes/Sped/Review Data/Amazon/All_Beauty.jsonl"
PRODUCTS_PATH = "/Volumes/Sped/Review Data/Amazon/meta_All_Beauty.jsonl"
CHECKPOINT_DIR = "checkpoints"

CALL_DELAY = 13.0       # seconds between Claude calls (5 RPM limit)
NEO4J_BATCH = 10        # flush to Neo4j every N records
MIN_REVIEWS = 25        # minimum reviews per product to include

# =========================================================================
# CLAUDE CLIENT
# =========================================================================

class ClaudeAnnotator:
    """Serial Claude caller with SDK-managed retry."""

    MODEL = "claude-sonnet-4-20250514"
    MAX_TOKENS = 4096

    def __init__(self):
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self.client = anthropic.Anthropic(api_key=api_key, max_retries=5)
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0
        self.errors = 0

    def annotate(self, system: str, user_prompt: str) -> dict:
        """Call Claude, return parsed JSON."""
        try:
            response = self.client.messages.create(
                model=self.MODEL,
                max_tokens=self.MAX_TOKENS,
                system=system,
                messages=[{"role": "user", "content": user_prompt}],
            )
            self.calls += 1
            self.input_tokens += response.usage.input_tokens
            self.output_tokens += response.usage.output_tokens

            text = response.content[0].text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(l for l in lines if not l.strip().startswith("```"))
            return json.loads(text)
        except json.JSONDecodeError as e:
            self.errors += 1
            logger.error(f"JSON parse error: {e}")
            return {}
        except Exception as e:
            self.errors += 1
            logger.error(f"Claude error: {e}")
            return {}

    @property
    def stats(self) -> str:
        cost = (self.input_tokens * 3 / 1_000_000) + (self.output_tokens * 15 / 1_000_000)
        return (
            f"calls={self.calls} in={self.input_tokens:,} out={self.output_tokens:,} "
            f"err={self.errors} cost=${cost:.2f}"
        )


# =========================================================================
# DATA
# =========================================================================

def iter_jsonl(path: str) -> Iterator[dict]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def build_qualifying_asins() -> set[str]:
    """Pre-scan reviews to find ASINs with 25+ verified reviews with text."""
    logger.info(f"Pre-scanning reviews to find products with {MIN_REVIEWS}+ reviews...")
    t0 = time.time()
    review_counts: Counter = Counter()
    for r in iter_jsonl(REVIEWS_PATH):
        if r.get("verified_purchase") and len(r.get("text", "")) >= 50:
            asin = r.get("parent_asin", r.get("asin", ""))
            if asin:
                review_counts[asin] += 1

    qualifying = {asin for asin, cnt in review_counts.items() if cnt >= MIN_REVIEWS}
    total_reviews = sum(review_counts[a] for a in qualifying)

    logger.info(
        f"Pre-scan done in {time.time()-t0:.1f}s: "
        f"{len(qualifying):,} products with {MIN_REVIEWS}+ reviews, "
        f"{total_reviews:,} total reviews in scope"
    )
    return qualifying


def load_product_index(path: str, qualifying: set[str]) -> dict[str, dict]:
    """Load product metadata only for qualifying ASINs."""
    logger.info("Loading product index (filtered)...")
    idx: dict[str, dict] = {}
    for r in iter_jsonl(path):
        key = r.get("parent_asin", r.get("asin", ""))
        if key and key in qualifying:
            idx[key] = r
    logger.info(f"Loaded {len(idx)} qualifying products")
    return idx


# =========================================================================
# PROMPTS — imported from canonical prompt_templates (single source of truth)
# =========================================================================

from adam.corpus.annotators.prompt_templates import (
    AD_SIDE_SYSTEM_PROMPT as AD_SYSTEM,
    AD_SIDE_COMPACT_TEMPLATE as AD_PROMPT,
    DUAL_SYSTEM_PROMPT as REVIEW_SYSTEM,
    DUAL_COMPACT_TEMPLATE as DUAL_PROMPT,
    USER_ONLY_COMPACT_TEMPLATE as USER_ONLY_PROMPT,
)


# =========================================================================
# PHASE 1: PRODUCT DESCRIPTIONS (only qualifying products)
# =========================================================================

def run_phase_1(
    claude: ClaudeAnnotator,
    writer: BulkWriter,
    ckpt: CheckpointManager,
    product_index: dict[str, dict],
):
    logger.info("=== PHASE 1: Product Description Annotation (25+ review products) ===")
    completed = ckpt.load_completed("phase1")
    logger.info(f"Resuming from {len(completed)} checkpointed products")

    stats = {"annotated": 0, "minimal": 0, "errors": 0, "skipped": 0}
    batch: list[dict] = []
    t0 = time.time()

    for asin, record in product_index.items():
        if asin in completed:
            stats["skipped"] += 1
            continue

        desc = " ".join(record.get("description", []))
        features = " ".join(record.get("features", []))
        has_text = len(desc) > 20 or len(features) > 20

        if has_text:
            prompt = AD_PROMPT.format(
                title=record.get("title", "")[:200],
                category=record.get("main_category", ""),
                price=record.get("price", "unknown"),
                brand=record.get("store", "") or record.get("brand", ""),
                desc=(desc or features or record.get("title", ""))[:2000],
                feats=(features if desc else "")[:1000],
            )
            result = claude.annotate(AD_SYSTEM, prompt)
            time.sleep(CALL_DELAY)

            if result:
                try:
                    ann = AdSideAnnotation(asin=asin, **result)
                    flat = ann.to_flat_dict()
                    stats["annotated"] += 1
                except Exception:
                    flat = {"annotation_confidence": 0.1, "annotation_tier": "failed"}
                    stats["errors"] += 1
            else:
                flat = {"annotation_confidence": 0.1, "annotation_tier": "failed"}
                stats["errors"] += 1
        else:
            flat = {"annotation_confidence": 0.1, "annotation_tier": "minimal"}
            stats["minimal"] += 1

        props = {
            "asin": asin,
            "title": record.get("title", "")[:500],
            "main_category": record.get("main_category", ""),
            "store": record.get("store", ""),
            "price": str(record.get("price", "")),
            "average_rating": record.get("average_rating", 0.0),
            "rating_number": record.get("rating_number", 0),
            **flat,
        }
        batch.append({"asin": asin, "properties": props})

        if len(batch) >= NEO4J_BATCH:
            writer.write_product_descriptions(batch)
            ckpt.mark_batch_completed("phase1", [r["asin"] for r in batch])
            batch.clear()

        total = stats["annotated"] + stats["minimal"] + stats["errors"]
        if total % 50 == 0 and total > 0:
            elapsed = time.time() - t0
            ann_rate = stats["annotated"] / elapsed if elapsed > 0 else 0
            remaining_ann = sum(
                1 for a, r in product_index.items()
                if a not in completed
                and (len(" ".join(r.get("description", []))) > 20
                     or len(" ".join(r.get("features", []))) > 20)
            ) - stats["annotated"]
            eta_h = remaining_ann * CALL_DELAY / 3600 if remaining_ann > 0 else 0
            logger.info(
                f"P1: {total}/{len(product_index)} | annotated={stats['annotated']} "
                f"minimal={stats['minimal']} err={stats['errors']} "
                f"(ETA ~{eta_h:.1f}h) | {claude.stats}"
            )

    if batch:
        writer.write_product_descriptions(batch)
        ckpt.mark_batch_completed("phase1", [r["asin"] for r in batch])

    logger.info(f"Phase 1 done: {stats} | {claude.stats}")
    return stats


# =========================================================================
# PHASE 2+3: REVIEWS (only for qualifying products)
# =========================================================================

def _should_dual(review: dict) -> bool:
    helpful = review.get("helpful_vote", 0) or 0
    rating = review.get("rating", 3)
    text_len = len(review.get("text", ""))
    return helpful >= 1 or (rating in (1, 5) and text_len > 200)


def run_phase_2_3(
    claude: ClaudeAnnotator,
    product_index: dict[str, dict],
    qualifying_asins: set[str],
    writer: BulkWriter,
    ckpt: CheckpointManager,
):
    logger.info("=== PHASE 2+3: Review Annotation (25+ review products only) ===")
    completed = ckpt.load_completed("phase2_3")
    logger.info(f"Resuming from {len(completed)} checkpointed reviews")

    stats = {
        "user": 0, "dual": 0, "short": 0, "unverified": 0,
        "errors": 0, "skipped": 0, "filtered_out": 0,
    }
    review_batch: list[dict] = []
    reviewer_batch: list[dict] = []
    has_review_batch: list[dict] = []
    t0 = time.time()

    for record in iter_jsonl(REVIEWS_PATH):
        if not record.get("verified_purchase", False):
            stats["unverified"] += 1
            continue
        text = record.get("text", "")
        if not text or len(text) < 50:
            stats["short"] += 1
            continue

        asin = record.get("parent_asin", record.get("asin", "unknown"))

        # --- 25+ review filter ---
        if asin not in qualifying_asins:
            stats["filtered_out"] += 1
            continue

        uid = record.get("user_id", "unknown")
        ts = record.get("timestamp", 0)
        rid = f"{uid}_{asin}_{ts}"

        if rid in completed:
            stats["skipped"] += 1
            continue

        product = product_index.get(asin, {})
        title = product.get("title", "Beauty Product")
        cat = product.get("main_category", "All Beauty")

        dual = _should_dual(record)
        if dual:
            prompt = DUAL_PROMPT.format(
                title=title[:200], cat=cat,
                rating=record.get("rating", 0),
                helpful=record.get("helpful_vote", 0),
                text=text[:3000],
            )
        else:
            prompt = USER_ONLY_PROMPT.format(
                title=title[:200], cat=cat,
                rating=record.get("rating", 0),
                helpful=record.get("helpful_vote", 0),
                text=text[:3000],
            )

        result = claude.annotate(REVIEW_SYSTEM, prompt)
        time.sleep(CALL_DELAY)

        if not result:
            stats["errors"] += 1
            continue

        try:
            if dual:
                user_data = result.get("user_side", {})
                peer_data = result.get("peer_ad_side", {})
                conversion = result.get("conversion_outcome", "satisfied")
                user_ann = UserSideAnnotation(review_id=rid, conversion_outcome=conversion, **user_data)
                peer_ann = PeerAdSideAnnotation(review_id=rid, **peer_data)
                user_flat = user_ann.to_flat_dict()
                peer_flat = peer_ann.to_flat_dict()
                stats["dual"] += 1
            else:
                conversion = result.pop("conversion_outcome", "satisfied")
                user_ann = UserSideAnnotation(review_id=rid, conversion_outcome=conversion, **result)
                user_flat = user_ann.to_flat_dict()
                peer_flat = None
                stats["user"] += 1
        except Exception as e:
            stats["errors"] += 1
            logger.error(f"Parse error for {rid}: {e}")
            continue

        node_props: dict[str, Any] = {
            "review_id": rid,
            "asin": asin,
            "parent_asin": record.get("parent_asin", asin),
            "user_id": uid,
            "star_rating": record.get("rating", 0),
            "helpful_votes": record.get("helpful_vote", 0),
            "verified_purchase": True,
            "timestamp": ts,
            "text_length": len(text),
            **user_flat,
        }
        if peer_flat:
            node_props.update(peer_flat)

        review_batch.append({"review_id": rid, "properties": node_props})
        reviewer_batch.append({"reviewer_id": uid, "review_id": rid})
        has_review_batch.append({"product_asin": asin, "review_id": rid})

        if len(review_batch) >= NEO4J_BATCH:
            writer.write_annotated_reviews(review_batch)
            writer.write_reviewers([{"reviewer_id": r["reviewer_id"]} for r in reviewer_batch])
            writer.write_authored_edges(reviewer_batch)
            writer.write_has_review_edges(has_review_batch)
            ckpt.mark_batch_completed("phase2_3", [r["review_id"] for r in review_batch])
            review_batch.clear()
            reviewer_batch.clear()
            has_review_batch.clear()

        total = stats["user"] + stats["dual"]
        if total % 50 == 0 and total > 0:
            elapsed = time.time() - t0
            rate = total / elapsed if elapsed > 0 else 0
            remaining = 184945 - total - stats["skipped"]
            eta_h = remaining / rate / 3600 if rate > 0 else 0
            logger.info(
                f"P2+3: {total}/184,945 | user={stats['user']} dual={stats['dual']} "
                f"err={stats['errors']} filtered={stats['filtered_out']:,} "
                f"({rate:.2f}/s, ETA {eta_h:.1f}h) | {claude.stats}"
            )

    # Flush
    if review_batch:
        writer.write_annotated_reviews(review_batch)
        writer.write_reviewers([{"reviewer_id": r["reviewer_id"]} for r in reviewer_batch])
        writer.write_authored_edges(reviewer_batch)
        writer.write_has_review_edges(has_review_batch)
        ckpt.mark_batch_completed("phase2_3", [r["review_id"] for r in review_batch])

    logger.info(f"Phase 2+3 done: {stats} | {claude.stats}")
    return stats


# =========================================================================
# PHASES 4-8 (imported — no Claude, all computation)
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
    logger.info("ADAM Corpus Pipeline — 25+ Review Filter")
    logger.info("=" * 60)

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    logger.info(f"Connected to Neo4j at {NEO4J_URI}")

    writer = BulkWriter(driver, batch_size=500)
    ckpt = CheckpointManager(CHECKPOINT_DIR)
    claude = ClaudeAnnotator()

    # Phase 0: Schema
    logger.info("=== PHASE 0: Schema ===")
    apply_schema(driver)

    # Pre-scan: find qualifying ASINs (25+ reviews)
    qualifying_asins = build_qualifying_asins()

    # Load product metadata for qualifying ASINs only
    product_index = load_product_index(PRODUCTS_PATH, qualifying_asins)

    # Phase 1: Product descriptions
    run_phase_1(claude, writer, ckpt, product_index)

    # Phase 2+3: Reviews
    run_phase_2_3(claude, product_index, qualifying_asins, writer, ckpt)

    # Phase 4: Ecosystems
    run_phase_4(driver, writer, ckpt)

    # Phase 5: BRAND_CONVERTED edges
    run_phase_5(driver, writer, ckpt)

    # Phase 6: PEER_INFLUENCED edges
    run_phase_6(driver, writer, ckpt)

    # Phase 7: ECOSYSTEM_CONVERTED edges
    run_phase_7(driver, writer, ckpt)

    # Phase 8: Bayesian priors
    run_phase_8(driver)

    # Validation
    logger.info("=== VALIDATION ===")
    run_full_validation(driver)

    graph_stats = get_graph_stats(driver)
    driver.close()

    elapsed = time.time() - t0
    logger.info("=" * 60)
    logger.info(f"PIPELINE COMPLETE in {elapsed:.0f}s ({elapsed/3600:.1f}h)")
    for k, v in graph_stats.items():
        logger.info(f"  {k}: {v}")
    logger.info(f"  Claude: {claude.stats}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
