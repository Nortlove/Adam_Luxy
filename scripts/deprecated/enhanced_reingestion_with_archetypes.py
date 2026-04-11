#!/usr/bin/env python3
"""
ENHANCED RE-INGESTION WITH DEEP ARCHETYPE DETECTION
====================================================

This is the UPGRADED version of run_full_reingestion.py that:

1. Uses DeepArchetypeDetector for per-review archetype detection
2. Builds customer profiles from review patterns
3. Extracts richer psychological intelligence
4. Creates archetype distribution per product

WHY THIS MATTERS:
-----------------
Previous ingestion assigned ONE archetype per category (e.g., ALL Beauty = "lover").
This loses 90%+ of archetype intelligence.

This version detects archetypes from the ACTUAL REVIEW TEXT using 500+ linguistic
markers across 10 psychological dimensions.

EXPECTED OUTPUT:
----------------
- Effectiveness matrix with 8+ archetypes per category (not 1)
- Per-product archetype distribution
- Customer psychological profiles
- Richer persuasive templates with archetype context

USAGE:
------
# Test on one category first
python scripts/enhanced_reingestion_with_archetypes.py --category All_Beauty --test

# Full run (after verifying test)
python scripts/enhanced_reingestion_with_archetypes.py --full
"""

import argparse
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

NUM_WORKERS = 6  # Use 6 of 12 CPUs (archetype detection is heavier)
BATCH_SIZE = 5000  # Smaller batches (archetype detection takes more memory)
CHECKPOINT_INTERVAL = 50000  # More frequent checkpoints
OUTPUT_DIR = Path("/Users/chrisnocera/Sites/adam-platform/data/enhanced_reingestion_output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# DEEP ARCHETYPE DETECTOR (CACHED)
# =============================================================================

# Global detector instance (initialized once per worker)
_detector = None

def get_deep_detector():
    """Get or create the deep archetype detector."""
    global _detector
    if _detector is None:
        try:
            from adam.intelligence.deep_archetype_detection import DeepArchetypeDetector
            _detector = DeepArchetypeDetector()
            logger.debug("Initialized DeepArchetypeDetector")
        except ImportError:
            logger.warning("DeepArchetypeDetector not available, falling back to category defaults")
    return _detector


# =============================================================================
# ENHANCED DATA STRUCTURES
# =============================================================================

@dataclass
class EnhancedProcessingResult:
    """Enhanced result with deep archetype detection."""
    
    category: str
    reviews_processed: int = 0
    products_linked: int = 0
    high_influence_reviews: int = 0
    templates_extracted: int = 0
    total_helpful_votes: int = 0
    
    # ENHANCED: Archetype distribution per category
    archetype_distribution: Dict[str, int] = field(default_factory=dict)
    
    # ENHANCED: Archetype detection methods used
    detection_methods: Dict[str, int] = field(default_factory=dict)
    
    # ENHANCED: Multi-archetype effectiveness matrix
    effectiveness_matrix: Dict[str, Dict[str, Dict]] = field(default_factory=dict)
    
    # ENHANCED: Product-level archetype profiles
    product_archetype_profiles: Dict[str, Dict[str, float]] = field(default_factory=dict)
    
    # Persuasive templates (now with diverse archetypes)
    templates: List[Dict] = field(default_factory=list)
    
    # Processing time
    duration_seconds: float = 0.0
    
    def to_dict(self) -> Dict:
        # Limit product profiles to top 1000 most interesting
        sorted_products = sorted(
            self.product_archetype_profiles.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:1000]
        
        return {
            "category": self.category,
            "reviews_processed": self.reviews_processed,
            "products_linked": self.products_linked,
            "high_influence_reviews": self.high_influence_reviews,
            "templates_extracted": self.templates_extracted,
            "total_helpful_votes": self.total_helpful_votes,
            "archetype_distribution": self.archetype_distribution,
            "detection_methods": self.detection_methods,
            "effectiveness_matrix": self.effectiveness_matrix,
            "product_archetype_profiles": dict(sorted_products),
            "templates": self.templates[:1000],
            "duration_seconds": self.duration_seconds,
        }


# =============================================================================
# ENHANCED WORKER FUNCTION
# =============================================================================

def process_review_batch_enhanced(args: Tuple[List[Dict], Dict[str, Dict], str]) -> Dict:
    """
    Process a batch of reviews with DEEP ARCHETYPE DETECTION.
    
    Args:
        args: (reviews, metadata_index, category)
    
    Returns:
        Dict with batch results including archetype distribution
    """
    reviews, meta_index, category = args
    
    hvi = HelpfulVoteIntelligence()
    detector = get_deep_detector()
    
    # Category default archetype (fallback)
    cat_info = CATEGORY_INFO.get(AmazonCategory(category), {})
    default_archetypes = cat_info.get("typical_archetypes", ["everyman"])
    default_archetype = default_archetypes[0] if default_archetypes else "everyman"
    
    results = {
        "reviews_processed": 0,
        "products_linked": 0,
        "high_influence": 0,
        "helpful_votes": 0,
        "templates": [],
        "archetype_distribution": defaultdict(int),
        "detection_methods": defaultdict(int),
        "product_profiles": defaultdict(lambda: defaultdict(float)),
    }
    
    linked_asins = set()
    
    for review in reviews:
        try:
            review_text = review.get("text", "")
            parent_asin = review.get("parent_asin", "")
            helpful_votes = review.get("helpful_vote", 0)
            rating = review.get("rating", 0.0)
            verified = review.get("verified_purchase", False)
            
            results["helpful_votes"] += helpful_votes
            
            # Link to meta if available
            if parent_asin and parent_asin in meta_index:
                if parent_asin not in linked_asins:
                    linked_asins.add(parent_asin)
                    results["products_linked"] += 1
            
            # ============================================
            # DEEP ARCHETYPE DETECTION
            # ============================================
            archetype = default_archetype
            archetype_confidence = 0.3
            detection_method = "category_default"
            
            # Only run deep detection on substantial reviews
            if detector and len(review_text) > 50:
                try:
                    deep_result = detector.detect_archetype(review_text)
                    
                    if deep_result.confidence > 0.35:
                        archetype = deep_result.primary_archetype
                        archetype_confidence = deep_result.confidence
                        detection_method = "deep_linguistic"
                    elif deep_result.confidence > 0.25 and deep_result.primary_archetype:
                        # Use detected but with lower confidence
                        archetype = deep_result.primary_archetype
                        archetype_confidence = deep_result.confidence
                        detection_method = "deep_linguistic_low_conf"
                        
                except Exception as e:
                    # Fall back to category default silently
                    pass
            
            # Track distribution
            results["archetype_distribution"][archetype] += 1
            results["detection_methods"][detection_method] += 1
            
            # Build product archetype profile
            if parent_asin:
                results["product_profiles"][parent_asin][archetype] += archetype_confidence
            
            # ============================================
            # PROCESS THROUGH HELPFUL VOTE INTELLIGENCE
            # ============================================
            process_result = hvi.process_review(
                review_text=review_text,
                helpful_votes=helpful_votes,
                verified_purchase=verified,
                archetype=archetype,  # Now using detected archetype!
                product_category=category,
                rating=rating,
            )
            
            results["reviews_processed"] += 1
            
            if process_result["tier"] in ("viral", "very_high", "high"):
                results["high_influence"] += 1
                
                # Collect templates with detected archetype
                for pattern in process_result.get("templates_extracted", []):
                    results["templates"].append({
                        "pattern": pattern,
                        "helpful_votes": helpful_votes,
                        "mechanisms": process_result["mechanisms_detected"],
                        "archetype": archetype,
                        "archetype_confidence": archetype_confidence,
                        "detection_method": detection_method,
                        "category": category,
                    })
        
        except Exception as e:
            continue
    
    # Get effectiveness data
    results["effectiveness"] = hvi.get_graph_effectiveness_matrix()
    
    # Convert defaultdicts to regular dicts
    results["archetype_distribution"] = dict(results["archetype_distribution"])
    results["detection_methods"] = dict(results["detection_methods"])
    results["product_profiles"] = {k: dict(v) for k, v in results["product_profiles"].items()}
    
    return results


# =============================================================================
# CATEGORY PROCESSOR
# =============================================================================

def process_category_enhanced(
    category: AmazonCategory,
    test_mode: bool = False,
    resume_from: int = 0,
) -> EnhancedProcessingResult:
    """
    Process all reviews in a category with enhanced archetype detection.
    """
    start_time = time.time()
    result = EnhancedProcessingResult(category=category.value)
    
    files = get_category_files(category)
    
    if not files.both_exist:
        logger.warning(f"Missing files for {category.value}")
        return result
    
    logger.info(f"{'='*60}")
    logger.info(f"ENHANCED PROCESSING: {category.value}")
    logger.info(f"{'='*60}")
    
    # Load metadata index
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
                    meta_index[asin] = {
                        "store": item.get("store", ""),
                        "title": item.get("title", "")[:100],
                        "details": {"brand": item.get("details", {}).get("brand", "")},
                    }
            except:
                continue
    
    logger.info(f"Loaded {len(meta_index):,} products")
    
    # Process reviews
    review_path = files.review_path
    opener = gzip.open if str(review_path).endswith('.gz') else open
    
    batch = []
    reviews_seen = 0
    checkpoint_num = 0
    
    # Aggregation for results
    archetype_dist = defaultdict(int)
    detection_methods = defaultdict(int)
    product_profiles = defaultdict(lambda: defaultdict(float))
    all_templates = []
    all_effectiveness = {}
    
    # Limit for test mode
    max_reviews = 100000 if test_mode else float('inf')
    
    with opener(review_path, 'rt', encoding='utf-8') as f:
        for line in f:
            if reviews_seen >= max_reviews:
                break
                
            reviews_seen += 1
            
            if reviews_seen < resume_from:
                continue
            
            try:
                review = json.loads(line)
                batch.append(review)
            except:
                continue
            
            # Process batch
            if len(batch) >= BATCH_SIZE:
                batch_result = process_review_batch_enhanced((batch, meta_index, category.value))
                
                # Aggregate results
                result.reviews_processed += batch_result["reviews_processed"]
                result.products_linked += batch_result["products_linked"]
                result.high_influence_reviews += batch_result["high_influence"]
                result.total_helpful_votes += batch_result["helpful_votes"]
                
                # Aggregate archetype distribution
                for arch, count in batch_result["archetype_distribution"].items():
                    archetype_dist[arch] += count
                
                for method, count in batch_result["detection_methods"].items():
                    detection_methods[method] += count
                
                # Aggregate product profiles
                for asin, profile in batch_result["product_profiles"].items():
                    for arch, score in profile.items():
                        product_profiles[asin][arch] += score
                
                # Collect templates
                all_templates.extend(batch_result["templates"])
                
                # Merge effectiveness (get_graph_effectiveness_matrix returns a list of edge dicts)
                for eff in batch_result.get("effectiveness", []):
                    key = (eff.get("archetype"), eff.get("mechanism"))
                    if not key[0] or not key[1]:
                        continue
                    sample = eff.get("sample_size", 0)
                    rate = eff.get("weighted_success_rate", eff.get("success_rate", 0))
                    if key not in all_effectiveness:
                        all_effectiveness[key] = {"total_count": sample, "weighted_success": rate * sample}
                    else:
                        all_effectiveness[key]["total_count"] += sample
                        all_effectiveness[key]["weighted_success"] += rate * sample
                
                batch = []
                
                # Log progress
                if reviews_seen % 50000 == 0:
                    unique_archetypes = len(archetype_dist)
                    deep_pct = detection_methods.get("deep_linguistic", 0) / max(1, sum(detection_methods.values())) * 100
                    logger.info(
                        f"  Progress: {reviews_seen:,} reviews, "
                        f"{unique_archetypes} archetypes detected, "
                        f"{deep_pct:.1f}% deep detection"
                    )
                
                # Checkpoint
                if reviews_seen % CHECKPOINT_INTERVAL == 0:
                    checkpoint_num += 1
                    save_checkpoint_enhanced(
                        category.value,
                        checkpoint_num,
                        result.reviews_processed,
                        archetype_dist,
                        detection_methods,
                    )
    
    # Process remaining batch
    if batch:
        batch_result = process_review_batch_enhanced((batch, meta_index, category.value))
        result.reviews_processed += batch_result["reviews_processed"]
        result.products_linked += batch_result["products_linked"]
        result.high_influence_reviews += batch_result["high_influence"]
        result.total_helpful_votes += batch_result["helpful_votes"]
        
        for arch, count in batch_result["archetype_distribution"].items():
            archetype_dist[arch] += count
        for method, count in batch_result["detection_methods"].items():
            detection_methods[method] += count
        for asin, profile in batch_result["product_profiles"].items():
            for arch, score in profile.items():
                product_profiles[asin][arch] += score
        all_templates.extend(batch_result["templates"])
        # Merge effectiveness from remaining batch
        for eff in batch_result.get("effectiveness", []):
            key = (eff.get("archetype"), eff.get("mechanism"))
            if not key[0] or not key[1]:
                continue
            sample = eff.get("sample_size", 0)
            rate = eff.get("weighted_success_rate", eff.get("success_rate", 0))
            if key not in all_effectiveness:
                all_effectiveness[key] = {"total_count": sample, "weighted_success": rate * sample}
            else:
                all_effectiveness[key]["total_count"] += sample
                all_effectiveness[key]["weighted_success"] += rate * sample
    
    # Finalize result
    result.archetype_distribution = dict(archetype_dist)
    result.detection_methods = dict(detection_methods)
    result.product_archetype_profiles = {k: dict(v) for k, v in product_profiles.items()}
    
    # Sort templates by helpful votes
    all_templates.sort(key=lambda t: t.get("helpful_votes", 0), reverse=True)
    result.templates = all_templates[:2000]  # Keep top 2000
    result.templates_extracted = len(all_templates)
    
    # Build effectiveness matrix (nested arch -> mech -> {success_rate, sample_size})
    result.effectiveness_matrix = {}
    for (arch, mech), data in all_effectiveness.items():
        total = data.get("total_count", 0)
        if total <= 0:
            continue
        w_success = data.get("weighted_success", 0)
        if arch not in result.effectiveness_matrix:
            result.effectiveness_matrix[arch] = {}
        result.effectiveness_matrix[arch][mech] = {
            "success_rate": w_success / total,
            "sample_size": total,
        }
    
    result.duration_seconds = time.time() - start_time
    
    # Log summary
    logger.info(f"\n{'='*60}")
    logger.info(f"CATEGORY COMPLETE: {category.value}")
    logger.info(f"{'='*60}")
    logger.info(f"Reviews processed: {result.reviews_processed:,}")
    logger.info(f"Products linked: {result.products_linked:,}")
    logger.info(f"High-influence reviews: {result.high_influence_reviews:,}")
    logger.info(f"Templates extracted: {result.templates_extracted:,}")
    logger.info(f"Archetypes detected: {len(result.archetype_distribution)}")
    logger.info(f"Detection methods: {result.detection_methods}")
    logger.info(f"Duration: {result.duration_seconds:.1f}s")
    
    # Show archetype distribution
    logger.info(f"\nArchetype Distribution:")
    sorted_archetypes = sorted(
        result.archetype_distribution.items(),
        key=lambda x: x[1],
        reverse=True
    )
    for arch, count in sorted_archetypes[:10]:
        pct = count / max(1, result.reviews_processed) * 100
        logger.info(f"  {arch}: {count:,} ({pct:.1f}%)")
    
    # Save result
    save_result_enhanced(result)
    
    return result


def save_checkpoint_enhanced(category: str, num: int, reviews: int, archetypes: Dict, methods: Dict):
    """Save an enhanced checkpoint."""
    checkpoint_path = OUTPUT_DIR / f"{category}_checkpoint_{num}.json"
    with open(checkpoint_path, 'w') as f:
        json.dump({
            "checkpoint": num,
            "reviews_processed": reviews,
            "archetypes_detected": len(archetypes),
            "detection_methods": methods,
        }, f)


def save_result_enhanced(result: EnhancedProcessingResult):
    """Save enhanced processing result."""
    result_path = OUTPUT_DIR / f"{result.category}_enhanced_result.json"
    with open(result_path, 'w') as f:
        json.dump(result.to_dict(), f, indent=2)
    logger.info(f"Saved: {result_path}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Enhanced Re-ingestion with Deep Archetype Detection")
    parser.add_argument("--category", type=str, help="Single category to process")
    parser.add_argument("--test", action="store_true", help="Test mode (100K reviews limit)")
    parser.add_argument("--full", action="store_true", help="Process all categories")
    
    args = parser.parse_args()
    
    if args.category:
        try:
            category = AmazonCategory(args.category)
            process_category_enhanced(category, test_mode=args.test)
        except ValueError:
            logger.error(f"Unknown category: {args.category}")
            logger.info(f"Available: {[c.value for c in AmazonCategory]}")
    
    elif args.full:
        categories = get_available_categories()
        logger.info(f"Processing {len(categories)} categories with enhanced archetype detection")
        
        for category in categories:
            try:
                process_category_enhanced(category, test_mode=False)
            except Exception as e:
                logger.error(f"Failed to process {category.value}: {e}")
                continue
    
    else:
        parser.print_help()
        print("\nExample:")
        print("  python scripts/enhanced_reingestion_with_archetypes.py --category All_Beauty --test")


if __name__ == "__main__":
    main()
