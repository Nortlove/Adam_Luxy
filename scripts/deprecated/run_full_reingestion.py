#!/usr/bin/env python3
"""
FULL RE-INGESTION WITH HELPFUL VOTE INTELLIGENCE
=================================================

Processes all ~1B Amazon reviews with:
1. ASIN linking (reviews → meta via parent_asin)
2. Helpful vote weighting (meta-validation signal)
3. Persuasion pattern extraction (from high-vote reviews)
4. Brand copy analysis (the "ad" from meta)
5. Archetype → Mechanism effectiveness mapping

Optimized for MacBook Pro Max 2:
- 32GB RAM
- 12 CPUs (8 performance, 4 efficiency)
- 32 GPUs

Processing Strategy:
- Multiprocessing Pool for CPU-bound analysis
- Streaming file processing (no full load into memory)
- Checkpoint every 100K reviews
- Resume capability

Output:
- Per-category JSON checkpoints
- Aggregated effectiveness matrix
- Persuasive template library
- Learning artifacts for Graph/AoT/LangGraph
"""

import argparse
import gc
import gzip
import json
import logging
import multiprocessing as mp
import os
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import math

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from adam.intelligence.amazon_data_registry import (
    AmazonCategory,
    CATEGORY_INFO,
    get_category_files,
    get_available_categories,
    AMAZON_DATA_DIR,
)
from adam.intelligence.helpful_vote_intelligence import (
    HelpfulVoteIntelligence,
    InfluenceTier,
    PersuasiveTemplate,
    MechanismEffectiveness,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

# Hardware optimization
NUM_WORKERS = 8  # Use 8 of 12 CPUs, leave 4 for system
BATCH_SIZE = 10000  # Reviews per batch
CHECKPOINT_INTERVAL = 100000  # Save every 100K reviews

# Output directory
OUTPUT_DIR = Path("/Users/chrisnocera/Sites/adam-platform/data/reingestion_output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# DATA CLASSES FOR OUTPUT
# =============================================================================

@dataclass
class CategoryProcessingResult:
    """Result of processing one category."""
    
    category: str
    reviews_processed: int = 0
    products_linked: int = 0
    high_influence_reviews: int = 0
    templates_extracted: int = 0
    total_helpful_votes: int = 0
    
    # Archetype → Mechanism effectiveness
    effectiveness_matrix: Dict[str, Dict[str, Dict]] = field(default_factory=dict)
    
    # Persuasive templates
    templates: List[Dict] = field(default_factory=list)
    
    # Processing time
    duration_seconds: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            "category": self.category,
            "reviews_processed": self.reviews_processed,
            "products_linked": self.products_linked,
            "high_influence_reviews": self.high_influence_reviews,
            "templates_extracted": self.templates_extracted,
            "total_helpful_votes": self.total_helpful_votes,
            "effectiveness_matrix": self.effectiveness_matrix,
            "templates": self.templates[:1000],  # Limit to top 1000
            "duration_seconds": self.duration_seconds,
        }


# =============================================================================
# WORKER FUNCTION
# =============================================================================

def process_review_batch(args: Tuple[List[Dict], Dict[str, Dict], str]) -> Dict:
    """
    Process a batch of reviews.
    
    Args:
        args: (reviews, metadata_index, category)
    
    Returns:
        Dict with batch results
    """
    reviews, meta_index, category = args
    
    hvi = HelpfulVoteIntelligence()
    
    results = {
        "reviews_processed": 0,
        "products_linked": 0,
        "high_influence": 0,
        "helpful_votes": 0,
        "templates": [],
    }
    
    linked_asins = set()
    
    for review in reviews:
        try:
            parent_asin = review.get("parent_asin", "")
            
            # Link to meta if available
            product_info = meta_index.get(parent_asin, {})
            brand = product_info.get("store") or product_info.get("details", {}).get("brand", "")
            
            if parent_asin not in linked_asins and parent_asin in meta_index:
                linked_asins.add(parent_asin)
                results["products_linked"] += 1
            
            # Get helpful votes
            helpful_votes = review.get("helpful_vote", 0)
            results["helpful_votes"] += helpful_votes
            
            # Determine archetype from category info
            cat_info = CATEGORY_INFO.get(AmazonCategory(category), {})
            archetypes = cat_info.get("typical_archetypes", ["everyman"])
            archetype = archetypes[0] if archetypes else "everyman"
            
            # Process through HelpfulVoteIntelligence
            process_result = hvi.process_review(
                review_text=review.get("text", ""),
                helpful_votes=helpful_votes,
                verified_purchase=review.get("verified_purchase", False),
                archetype=archetype,
                product_category=category,
                rating=review.get("rating", 0.0),
            )
            
            results["reviews_processed"] += 1
            
            if process_result["tier"] in ("viral", "very_high", "high"):
                results["high_influence"] += 1
                
                # Collect templates
                for pattern in process_result.get("templates_extracted", []):
                    results["templates"].append({
                        "pattern": pattern,
                        "helpful_votes": helpful_votes,
                        "mechanisms": process_result["mechanisms_detected"],
                        "archetype": archetype,
                        "category": category,
                    })
        
        except Exception as e:
            logger.debug(f"Error processing review: {e}")
            continue
    
    # Get effectiveness data
    results["effectiveness"] = hvi.get_graph_effectiveness_matrix()
    
    return results


# =============================================================================
# CATEGORY PROCESSOR
# =============================================================================

def process_category(
    category: AmazonCategory,
    resume_from: int = 0,
) -> CategoryProcessingResult:
    """
    Process all reviews in a category.
    
    Uses streaming to handle large files without loading entirely into memory.
    """
    start_time = time.time()
    result = CategoryProcessingResult(category=category.value)
    
    files = get_category_files(category)
    
    if not files.both_exist:
        logger.warning(f"Missing files for {category.value}")
        return result
    
    logger.info(f"{'='*60}")
    logger.info(f"PROCESSING: {category.value}")
    logger.info(f"{'='*60}")
    
    # Load metadata index (for linking)
    logger.info(f"Loading metadata index...")
    meta_index = {}
    meta_path = files.meta_path
    
    opener = gzip.open if str(meta_path).endswith('.gz') else open
    with opener(meta_path, 'rt', encoding='utf-8') as f:
        for line in f:
            try:
                item = json.loads(line)
                asin = item.get("parent_asin") or item.get("asin")
                if asin:
                    # Store minimal info to save memory
                    meta_index[asin] = {
                        "store": item.get("store", ""),
                        "title": item.get("title", "")[:100],
                        "details": {"brand": item.get("details", {}).get("brand", "")},
                    }
            except json.JSONDecodeError:
                continue
    
    logger.info(f"Loaded {len(meta_index):,} products into index")
    
    # Process reviews in batches
    review_path = files.review_path
    opener = gzip.open if str(review_path).endswith('.gz') else open
    
    batch = []
    reviews_seen = 0
    checkpoint_count = 0
    
    # Aggregated results
    all_templates = []
    effectiveness_aggregator = defaultdict(lambda: defaultdict(lambda: {
        "success_count": 0,
        "total_count": 0,
        "weighted_success": 0.0,
        "weighted_total": 0.0,
    }))
    
    logger.info(f"Streaming reviews from {review_path.name}...")
    
    with opener(review_path, 'rt', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            # Skip if resuming
            if line_num <= resume_from:
                continue
            
            try:
                review = json.loads(line)
                batch.append(review)
                reviews_seen += 1
                
                # Process batch
                if len(batch) >= BATCH_SIZE:
                    batch_result = process_review_batch((batch, meta_index, category.value))
                    
                    # Aggregate
                    result.reviews_processed += batch_result["reviews_processed"]
                    result.products_linked += batch_result["products_linked"]
                    result.high_influence_reviews += batch_result["high_influence"]
                    result.total_helpful_votes += batch_result["helpful_votes"]
                    
                    all_templates.extend(batch_result.get("templates", []))
                    
                    # Aggregate effectiveness
                    for eff in batch_result.get("effectiveness", []):
                        arch = eff["archetype"]
                        mech = eff["mechanism"]
                        agg = effectiveness_aggregator[arch][mech]
                        agg["total_count"] += eff.get("sample_size", 1)
                        agg["weighted_total"] += eff.get("weighted_success_rate", 0.5) * eff.get("sample_size", 1)
                    
                    batch = []
                    
                    # Progress
                    elapsed = time.time() - start_time
                    rate = result.reviews_processed / max(elapsed, 0.001)
                    logger.info(
                        f"  {result.reviews_processed:,} reviews | "
                        f"{result.high_influence_reviews:,} high-influence | "
                        f"{rate:,.0f}/sec"
                    )
                    
                    # Checkpoint
                    if result.reviews_processed >= (checkpoint_count + 1) * CHECKPOINT_INTERVAL:
                        checkpoint_count += 1
                        save_checkpoint(category.value, result, checkpoint_count)
            
            except json.JSONDecodeError:
                continue
    
    # Process final batch
    if batch:
        batch_result = process_review_batch((batch, meta_index, category.value))
        result.reviews_processed += batch_result["reviews_processed"]
        result.products_linked += batch_result["products_linked"]
        result.high_influence_reviews += batch_result["high_influence"]
        result.total_helpful_votes += batch_result["helpful_votes"]
        all_templates.extend(batch_result.get("templates", []))
    
    # Finalize
    result.templates_extracted = len(all_templates)
    result.templates = sorted(
        all_templates,
        key=lambda t: t.get("helpful_votes", 0),
        reverse=True
    )[:1000]  # Keep top 1000
    
    # Convert effectiveness aggregator
    for arch, mechs in effectiveness_aggregator.items():
        result.effectiveness_matrix[arch] = {}
        for mech, data in mechs.items():
            if data["total_count"] > 0:
                result.effectiveness_matrix[arch][mech] = {
                    "success_rate": data["weighted_total"] / data["total_count"],
                    "sample_size": data["total_count"],
                }
    
    result.duration_seconds = time.time() - start_time
    
    logger.info(f"\n✅ COMPLETE: {category.value}")
    logger.info(f"   Reviews: {result.reviews_processed:,}")
    logger.info(f"   Products Linked: {result.products_linked:,}")
    logger.info(f"   High-Influence: {result.high_influence_reviews:,}")
    logger.info(f"   Templates: {result.templates_extracted:,}")
    logger.info(f"   Duration: {result.duration_seconds:.1f}s")
    
    # Save final result
    save_category_result(category.value, result)
    
    return result


def save_checkpoint(category: str, result: CategoryProcessingResult, checkpoint_num: int):
    """Save processing checkpoint."""
    checkpoint_file = OUTPUT_DIR / f"{category}_checkpoint_{checkpoint_num}.json"
    with open(checkpoint_file, 'w') as f:
        json.dump({
            "checkpoint": checkpoint_num,
            "reviews_processed": result.reviews_processed,
            "high_influence": result.high_influence_reviews,
            "templates_count": len(result.templates),
        }, f)
    logger.info(f"  💾 Checkpoint {checkpoint_num} saved")


def save_category_result(category: str, result: CategoryProcessingResult):
    """Save final category result."""
    result_file = OUTPUT_DIR / f"{category}_result.json"
    with open(result_file, 'w') as f:
        json.dump(result.to_dict(), f, indent=2)
    logger.info(f"  💾 Result saved to {result_file.name}")


def _load_result_from_file(result_file: Path) -> Optional[CategoryProcessingResult]:
    """Load a CategoryProcessingResult from a _result.json file."""
    try:
        with open(result_file) as f:
            data = json.load(f)
        return CategoryProcessingResult(
            category=data.get("category", result_file.stem.replace("_result", "")),
            reviews_processed=data.get("reviews_processed", 0),
            products_linked=data.get("products_linked", 0),
            high_influence_reviews=data.get("high_influence_reviews", 0),
            templates_extracted=data.get("templates_extracted", 0),
            total_helpful_votes=data.get("total_helpful_votes", 0),
            effectiveness_matrix=data.get("effectiveness_matrix", {}),
            templates=data.get("templates", []),
            duration_seconds=data.get("duration_seconds", 0.0),
        )
    except Exception as e:
        logger.warning(f"Could not load {result_file}: {e}")
        return None


def get_remaining_categories() -> List[AmazonCategory]:
    """Return categories that do not yet have a _result.json in OUTPUT_DIR."""
    available = get_available_categories()
    remaining = []
    for cat in available:
        result_file = OUTPUT_DIR / f"{cat.value}_result.json"
        if not result_file.exists():
            remaining.append(cat)
    return remaining


def aggregate_existing_results() -> CategoryProcessingResult:
    """Sum all existing category _result.json files (excluding TOTAL) into one TOTAL result."""
    total = CategoryProcessingResult(category="TOTAL")
    for p in OUTPUT_DIR.glob("*_result.json"):
        if p.stem == "TOTAL":
            continue
        r = _load_result_from_file(p)
        if r is None:
            continue
        total.reviews_processed += r.reviews_processed
        total.products_linked += r.products_linked
        total.high_influence_reviews += r.high_influence_reviews
        total.templates_extracted += r.templates_extracted
        total.total_helpful_votes += r.total_helpful_votes
    return total


# =============================================================================
# MAIN
# =============================================================================

def main(remaining_only: bool = False):
    """Run full re-ingestion. If remaining_only=True, process only categories without _result.json."""
    
    print("=" * 70)
    print("AMAZON REVIEW RE-INGESTION WITH HELPFUL VOTE INTELLIGENCE")
    print("=" * 70)
    print(f"\nHardware: 12 CPUs, 32GB RAM, 32 GPUs")
    print(f"Workers: {NUM_WORKERS}")
    print(f"Batch Size: {BATCH_SIZE:,}")
    print(f"Output: {OUTPUT_DIR}")
    
    if remaining_only:
        categories = get_remaining_categories()
        if not categories:
            print("\nNo remaining categories to process. All 33 categories already have results.")
            return
        print(f"\nRESUME MODE: Processing {len(categories)} remaining categories:")
        for c in categories:
            print(f"  - {c.value}")
    else:
        categories = get_available_categories()
        print(f"\nCategories to process: {len(categories)}")
    
    total_result = CategoryProcessingResult(category="TOTAL")
    start_time = time.time()
    
    for i, category in enumerate(categories, 1):
        print(f"\n[{i}/{len(categories)}] Processing {category.value}...")
        
        try:
            result = process_category(category)
            
            total_result.reviews_processed += result.reviews_processed
            total_result.products_linked += result.products_linked
            total_result.high_influence_reviews += result.high_influence_reviews
            total_result.templates_extracted += result.templates_extracted
            total_result.total_helpful_votes += result.total_helpful_votes
            
        except Exception as e:
            logger.error(f"Failed to process {category.value}: {e}")
            continue
        
        # Free memory between categories to reduce RAM pressure (helps avoid Cursor/system crashes)
        gc.collect()
    
    total_result.duration_seconds = time.time() - start_time
    
    if remaining_only and categories:
        existing = aggregate_existing_results()
        total_result.reviews_processed += existing.reviews_processed
        total_result.products_linked += existing.products_linked
        total_result.high_influence_reviews += existing.high_influence_reviews
        total_result.templates_extracted += existing.templates_extracted
        total_result.total_helpful_votes += existing.total_helpful_votes
    
    save_category_result("TOTAL", total_result)
    
    print("\n" + "=" * 70)
    print("COMPLETE")
    print("=" * 70)
    print(f"\nTotal Reviews: {total_result.reviews_processed:,}")
    print(f"Products Linked: {total_result.products_linked:,}")
    print(f"High-Influence Reviews: {total_result.high_influence_reviews:,}")
    print(f"Templates Extracted: {total_result.templates_extracted:,}")
    print(f"Total Helpful Votes: {total_result.total_helpful_votes:,}")
    print(f"Duration: {total_result.duration_seconds/3600:.2f} hours")
    print(f"\nOutput: {OUTPUT_DIR}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Amazon review re-ingestion with helpful vote intelligence"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Process only All_Beauty (small category) for testing",
    )
    parser.add_argument(
        "--remaining",
        action="store_true",
        help="Process only categories that do not yet have a _result.json (resume after crash)",
    )
    args = parser.parse_args()

    if args.test:
        print("TEST MODE: Processing All_Beauty only")
        result = process_category(AmazonCategory.ALL_BEAUTY)
        print(f"\nTest complete: {result.reviews_processed:,} reviews")
    else:
        main(remaining_only=args.remaining)
