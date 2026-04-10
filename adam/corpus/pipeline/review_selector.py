"""
Review selector — identifies best reviews across all 3 datasets.

Best reviews get Claude annotation (rich, dual-perspective).
Remaining reviews get LIWC-lite annotation (fast, user-side only).

Selection criteria for "best" reviews:
  - Product must have 25+ (All_Beauty/Sephora) or 50+ (B&PC) verified reviews
  - Review must be verified purchase with text >= 50 chars
  - Then ranked per product: helpful_votes desc, text_length desc
  - Top N per product go to Claude (default N=20)

Data source formats:
  - Amazon: reviews in .jsonl, product metadata in separate meta_.jsonl
  - Sephora: reviews in CSV files, product metadata in product_info.csv
"""

from __future__ import annotations

import csv
import json
import logging
import os
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

logger = logging.getLogger("adam.corpus.selector")


@dataclass
class ReviewRecord:
    """Unified review record across all dataset formats."""
    review_id: str
    product_id: str
    user_id: str
    text: str
    rating: int
    helpful_votes: int
    verified: bool
    timestamp: int
    source: str  # "all_beauty", "bpc", "sephora"
    # Extra Sephora fields
    skin_tone: str = ""
    skin_type: str = ""
    is_recommended: bool = True


@dataclass
class ProductRecord:
    """Unified product record across all dataset formats."""
    product_id: str
    title: str
    brand: str
    category: str
    price: str
    description: str
    features: str
    source: str
    average_rating: float = 0.0
    rating_count: int = 0
    # Sephora-specific
    ingredients: str = ""
    highlights: str = ""


@dataclass
class DatasetSelection:
    """Result of selecting reviews from a dataset."""
    name: str
    qualifying_products: dict[str, ProductRecord]
    claude_reviews: list[ReviewRecord]
    liwc_reviews: list[ReviewRecord]
    review_counts: dict[str, int]  # product_id -> total review count


# =========================================================================
# AMAZON JSONL READER
# =========================================================================

def _iter_amazon_jsonl(path: str) -> Iterator[dict]:
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


def select_amazon_dataset(
    reviews_path: str,
    meta_path: str,
    source_name: str,
    min_reviews: int = 25,
    top_n_per_product: int = 20,
) -> DatasetSelection:
    """
    Select best reviews from an Amazon JSONL dataset.
    Two-pass for memory efficiency on large files:
      Pass 1: count reviews per ASIN (only counters in memory)
      Pass 2: re-read file, only hold reviews for qualifying ASINs
    """
    logger.info(f"[{source_name}] Pass 1: counting reviews per product...")

    # Pass 1: count only (memory-efficient)
    review_counts: Counter = Counter()
    total = 0
    qualified_text = 0

    for r in _iter_amazon_jsonl(reviews_path):
        total += 1
        if not r.get("verified_purchase"):
            continue
        text = r.get("text", "")
        if len(text) < 50:
            continue
        asin = r.get("parent_asin", r.get("asin", ""))
        if not asin:
            continue
        qualified_text += 1
        review_counts[asin] += 1

        if total % 5_000_000 == 0:
            logger.info(f"  [{source_name}] ...counted {total:,} reviews")

    qualifying_asins = {a for a, c in review_counts.items() if c >= min_reviews}
    total_qualifying_reviews = sum(review_counts[a] for a in qualifying_asins)
    logger.info(
        f"[{source_name}] Pass 1 done: {total:,} total, {qualified_text:,} qualified. "
        f"{len(qualifying_asins):,} products with {min_reviews}+ reviews "
        f"({total_qualifying_reviews:,} reviews)"
    )

    # Load product metadata for qualifying ASINs
    logger.info(f"[{source_name}] Loading product metadata...")
    products: dict[str, ProductRecord] = {}
    for r in _iter_amazon_jsonl(meta_path):
        asin = r.get("parent_asin", r.get("asin", ""))
        if asin not in qualifying_asins:
            continue
        products[asin] = ProductRecord(
            product_id=asin,
            title=r.get("title", "")[:500],
            brand=r.get("store", "") or r.get("brand", ""),
            category=r.get("main_category", ""),
            price=str(r.get("price", "")),
            description=" ".join(r.get("description", []))[:2000],
            features=" ".join(r.get("features", []))[:1000],
            source=source_name,
            average_rating=r.get("average_rating", 0.0),
            rating_count=r.get("rating_number", 0),
        )
    logger.info(f"[{source_name}] Loaded metadata for {len(products):,} products")

    # Pass 2: collect reviews for qualifying ASINs only
    # Use a per-product heap to keep only top-N for Claude + all others for LIWC
    logger.info(f"[{source_name}] Pass 2: selecting best reviews...")
    import heapq

    # Per-product: keep top_n by (helpful, text_len) for Claude
    # Use (score, counter, record) to avoid comparing dicts on tie
    product_heaps: dict[str, list] = defaultdict(list)  # min-heaps of size top_n
    liwc_records: list[tuple] = []  # (asin, raw_record) for non-top reviews
    counter = 0  # unique tiebreaker for heap

    pass2_total = 0
    for r in _iter_amazon_jsonl(reviews_path):
        pass2_total += 1
        if not r.get("verified_purchase"):
            continue
        text = r.get("text", "")
        if len(text) < 50:
            continue
        asin = r.get("parent_asin", r.get("asin", ""))
        if asin not in qualifying_asins:
            continue

        helpful = r.get("helpful_vote", 0) or 0
        score = (helpful, len(text))  # sort key
        counter += 1

        heap = product_heaps[asin]
        if len(heap) < top_n_per_product:
            heapq.heappush(heap, (score, counter, r))
        else:
            # If better than worst in heap, replace and push old to LIWC
            if score > heap[0][0]:
                _, _, evicted = heapq.heapreplace(heap, (score, counter, r))
                liwc_records.append((asin, evicted))
            else:
                liwc_records.append((asin, r))

        if pass2_total % 5_000_000 == 0:
            logger.info(f"  [{source_name}] ...pass2 {pass2_total:,}")

    # Convert heaps to review records
    claude_reviews: list[ReviewRecord] = []
    for asin, heap in product_heaps.items():
        for _, _, r in heap:
            uid = r.get("user_id", "unknown")
            ts = r.get("timestamp", 0)
            rid = f"{uid}_{asin}_{ts}"
            claude_reviews.append(ReviewRecord(
                review_id=rid, product_id=asin, user_id=uid,
                text=r.get("text", ""), rating=r.get("rating", 3),
                helpful_votes=r.get("helpful_vote", 0) or 0,
                verified=True, timestamp=ts, source=source_name,
            ))

    liwc_reviews: list[ReviewRecord] = []
    for asin, r in liwc_records:
        uid = r.get("user_id", "unknown")
        ts = r.get("timestamp", 0)
        rid = f"{uid}_{asin}_{ts}"
        liwc_reviews.append(ReviewRecord(
            review_id=rid, product_id=asin, user_id=uid,
            text=r.get("text", ""), rating=r.get("rating", 3),
            helpful_votes=r.get("helpful_vote", 0) or 0,
            verified=True, timestamp=ts, source=source_name,
        ))

    logger.info(
        f"[{source_name}] Selected {len(claude_reviews):,} for Claude, "
        f"{len(liwc_reviews):,} for LIWC"
    )

    return DatasetSelection(
        name=source_name,
        qualifying_products=products,
        claude_reviews=claude_reviews,
        liwc_reviews=liwc_reviews,
        review_counts=dict(review_counts),
    )


# =========================================================================
# SEPHORA CSV READER
# =========================================================================

def select_sephora_dataset(
    reviews_dir: str,
    min_reviews: int = 25,
    top_n_per_product: int = 20,
) -> DatasetSelection:
    """
    Select best reviews from Sephora CSV dataset.
    """
    review_files = sorted(Path(reviews_dir).glob("reviews_*.csv"))
    product_info_path = Path(reviews_dir) / "product_info.csv"

    logger.info(f"[sephora] Reading {len(review_files)} review files...")

    # Pass 1: read all reviews, count per product
    all_reviews: dict[str, list] = defaultdict(list)
    total = 0

    for rf in review_files:
        with open(rf, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                total += 1
                text = row.get("review_text", "") or ""
                if len(text) < 50:
                    continue
                pid = row.get("product_id", "")
                if not pid:
                    continue
                all_reviews[pid].append(row)

    qualifying_pids = {p for p, revs in all_reviews.items() if len(revs) >= min_reviews}
    total_qualifying = sum(len(all_reviews[p]) for p in qualifying_pids)
    logger.info(
        f"[sephora] Scanned {total:,} reviews. "
        f"Products with {min_reviews}+ reviews: {len(qualifying_pids):,}, "
        f"total reviews: {total_qualifying:,}"
    )

    # Load product metadata
    logger.info("[sephora] Loading product metadata...")
    products: dict[str, ProductRecord] = {}
    if product_info_path.exists():
        with open(product_info_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                pid = row.get("product_id", "")
                if pid not in qualifying_pids:
                    continue
                highlights = row.get("highlights", "")
                products[pid] = ProductRecord(
                    product_id=pid,
                    title=row.get("product_name", "")[:500],
                    brand=row.get("brand_name", ""),
                    category=row.get("primary_category", ""),
                    price=row.get("price_usd", ""),
                    description=f"{row.get('primary_category', '')} > {row.get('secondary_category', '')} > {row.get('tertiary_category', '')}",
                    features=highlights[:1000] if highlights else "",
                    source="sephora",
                    average_rating=float(row.get("rating", 0) or 0),
                    rating_count=int(row.get("reviews", 0) or 0),
                    ingredients=row.get("ingredients", "")[:2000],
                    highlights=highlights[:1000],
                )

    logger.info(f"[sephora] Loaded metadata for {len(products):,} products")

    # Select top-N per product
    claude_reviews: list[ReviewRecord] = []
    liwc_reviews: list[ReviewRecord] = []

    for pid in qualifying_pids:
        revs = all_reviews.get(pid, [])
        # Sort by helpfulness/positive feedback desc, then text length desc
        revs.sort(
            key=lambda r: (
                int(float(r.get("total_pos_feedback_count", 0) or 0)),
                len(r.get("review_text", "") or ""),
            ),
            reverse=True,
        )

        for i, row in enumerate(revs):
            text = row.get("review_text", "") or ""
            author_id = row.get("author_id", "unknown")
            rid = f"sephora_{author_id}_{pid}_{i}"

            rec = ReviewRecord(
                review_id=rid,
                product_id=pid,
                user_id=author_id,
                text=text,
                rating=int(float(row.get("rating", 3) or 3)),
                helpful_votes=int(float(row.get("total_pos_feedback_count", 0) or 0)),
                verified=True,  # Sephora reviews are all verified purchases
                timestamp=0,  # Will parse submission_time if needed
                source="sephora",
                skin_tone=row.get("skin_tone", "") or "",
                skin_type=row.get("skin_type", "") or "",
                is_recommended=row.get("is_recommended", "1") == "1.0" or row.get("is_recommended", "1") == "1",
            )

            if i < top_n_per_product:
                claude_reviews.append(rec)
            else:
                liwc_reviews.append(rec)

    logger.info(
        f"[sephora] Selected {len(claude_reviews):,} for Claude, "
        f"{len(liwc_reviews):,} for LIWC"
    )

    review_counts = {pid: len(revs) for pid, revs in all_reviews.items()}

    return DatasetSelection(
        name="sephora",
        qualifying_products=products,
        claude_reviews=claude_reviews,
        liwc_reviews=liwc_reviews,
        review_counts=review_counts,
    )
