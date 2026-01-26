#!/usr/bin/env python3
# =============================================================================
# ADAM Amazon Data Processing Script
# Location: scripts/process_amazon_data.py
# =============================================================================

"""
PROCESS AMAZON DATA FOR ADAM COLD START

This script processes the Amazon review corpus to generate:
1. Archetype priors (updates adam/user/cold_start/archetypes.py)
2. Category psychology profiles (for cold start)
3. Media-product correlations (for cross-domain inference)
4. Neo4j graph data (reviewer profiles, products, relationships)

The data feeds into the existing ADAM cold start system:
- adam/user/cold_start/service.py (ColdStartService)
- adam/coldstart/unified_learning.py (UnifiedColdStartLearning)
- adam/meta_learner/thompson.py (Thompson Sampling)

Usage:
    # Process all categories (full)
    python scripts/process_amazon_data.py --data-dir /path/to/amazon
    
    # Quick test (limited data)
    python scripts/process_amazon_data.py --data-dir /path/to/amazon --quick
    
    # Specific categories
    python scripts/process_amazon_data.py --data-dir /path/to/amazon --categories Books,Digital_Music
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
)
logger = logging.getLogger("ADAM-Amazon")


def process_amazon_data(
    data_dir: str,
    output_dir: str = "./amazon_processed",
    categories: Optional[List[str]] = None,
    limit_per_category: Optional[int] = None,
    quick_mode: bool = False,
) -> Dict[str, Any]:
    """
    Process Amazon data to generate cold start priors.
    
    This uses the existing ADAM data processing modules:
    - adam/data/amazon/loader.py - Load JSONL files
    - adam/data/amazon/profiler.py - Extract linguistic features
    - adam/data/amazon/media_product_graph.py - Build relationships
    """
    
    from adam.data.amazon.loader import AmazonDataLoader, ReviewerAggregator
    from adam.data.amazon.media_product_graph import (
        MediaProductGraphBuilder,
        CATEGORY_TYPES,
        CategoryType,
    )
    
    # Settings for quick mode
    if quick_mode:
        limit_per_category = limit_per_category or 5000
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    stats = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "data_dir": data_dir,
        "categories_processed": [],
        "totals": {
            "reviews": 0,
            "users": 0,
            "media_reviews": 0,
            "product_reviews": 0,
        },
    }
    
    print("\n")
    print("=" * 70)
    print("ADAM AMAZON DATA PROCESSING")
    print("=" * 70)
    print(f"Data directory: {data_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Mode: {'QUICK' if quick_mode else 'FULL'}")
    if limit_per_category:
        print(f"Limit per category: {limit_per_category:,}")
    print("=" * 70)
    print()
    
    # Initialize
    try:
        loader = AmazonDataLoader(data_dir)
    except FileNotFoundError as e:
        logger.error(f"Data directory not found: {data_dir}")
        return {"error": str(e)}
    
    graph_builder = MediaProductGraphBuilder()
    aggregator = ReviewerAggregator()
    
    # Get categories to process
    if categories:
        categories_to_process = [c for c in categories if c in loader.available_categories]
    else:
        categories_to_process = loader.available_categories
    
    logger.info(f"Processing {len(categories_to_process)} categories")
    
    # =========================================================================
    # PHASE 1: Load and aggregate reviews
    # =========================================================================
    
    print("\n--- PHASE 1: Loading Reviews ---\n")
    
    for category in categories_to_process:
        category_type = CATEGORY_TYPES.get(category, CategoryType.PRODUCT)
        type_label = "📚 MEDIA" if category_type == CategoryType.MEDIA else "🛍️ PRODUCT"
        
        logger.info(f"{type_label} | {category}")
        
        try:
            count = 0
            for review in loader.stream_reviews(category, limit=limit_per_category):
                # Add to graph builder
                graph_builder.add_review(
                    reviewer_id=review.user_id,
                    category=category,
                    text=review.text,
                    rating=review.rating,
                    asin=review.asin,
                )
                
                # Add to aggregator
                aggregator.add_review(review, category)
                
                count += 1
                if count % 10000 == 0:
                    logger.info(f"  → {count:,} reviews...")
            
            stats["totals"]["reviews"] += count
            if category_type == CategoryType.MEDIA:
                stats["totals"]["media_reviews"] += count
            else:
                stats["totals"]["product_reviews"] += count
            
            stats["categories_processed"].append({
                "category": category,
                "type": category_type.value,
                "reviews": count,
            })
            
            logger.info(f"  ✓ {count:,} reviews loaded")
            
        except FileNotFoundError:
            logger.warning(f"  ✗ Category file not found")
        except Exception as e:
            logger.error(f"  ✗ Error: {e}")
    
    stats["totals"]["users"] = len(aggregator.users)
    
    # =========================================================================
    # PHASE 2: Compute cross-domain statistics
    # =========================================================================
    
    print("\n--- PHASE 2: Cross-Domain Analysis ---\n")
    
    cross_domain_profiles = graph_builder.get_cross_domain_profiles(
        min_media_reviews=1,
        min_product_reviews=1,
    )
    
    logger.info(f"Cross-domain reviewers: {len(cross_domain_profiles):,}")
    logger.info(f"  (Users who reviewed BOTH media AND products)")
    
    correlations = graph_builder.get_media_product_correlations()
    
    logger.info("\nMedia → Product Correlations:")
    for media_cat, products in correlations.items():
        top = sorted(products.items(), key=lambda x: x[1], reverse=True)[:3]
        if top:
            logger.info(f"  {media_cat}: {', '.join(f'{p[0]}({p[1]:.0%})' for p in top)}")
    
    stats["cross_domain"] = {
        "cross_domain_users": len(cross_domain_profiles),
        "correlations": correlations,
    }
    
    # =========================================================================
    # PHASE 3: Export for cold start system
    # =========================================================================
    
    print("\n--- PHASE 3: Exporting for Cold Start ---\n")
    
    # Export cross-domain profiles
    profiles_export = []
    for profile in cross_domain_profiles[:10000]:  # Limit for file size
        profiles_export.append({
            "reviewer_id": profile.reviewer_id,
            "media_categories": list(profile.media_categories),
            "product_categories": list(profile.product_categories),
            "is_cross_domain": True,
            "cross_domain_confidence": profile.cross_domain_confidence,
        })
    
    profiles_path = output_path / "cross_domain_profiles.json"
    with open(profiles_path, "w") as f:
        json.dump(profiles_export, f, indent=2)
    logger.info(f"Exported {len(profiles_export)} cross-domain profiles")
    
    # Export correlations
    correlations_path = output_path / "media_product_correlations.json"
    with open(correlations_path, "w") as f:
        json.dump(correlations, f, indent=2)
    logger.info(f"Exported correlations")
    
    # Export aggregator stats
    agg_stats = aggregator.get_stats()
    stats_path = output_path / "aggregator_stats.json"
    with open(stats_path, "w") as f:
        json.dump(agg_stats, f, indent=2)
    logger.info(f"Exported aggregator stats")
    
    # Export processing stats
    stats["completed_at"] = datetime.now(timezone.utc).isoformat()
    final_stats_path = output_path / "processing_stats.json"
    with open(final_stats_path, "w") as f:
        json.dump(stats, f, indent=2, default=str)
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    
    print("\n" + "=" * 70)
    print("PROCESSING COMPLETE")
    print("=" * 70)
    print(f"📊 Reviews processed: {stats['totals']['reviews']:,}")
    print(f"👥 Unique users: {stats['totals']['users']:,}")
    print(f"📚 Media reviews: {stats['totals']['media_reviews']:,}")
    print(f"🛍️ Product reviews: {stats['totals']['product_reviews']:,}")
    print(f"🔗 Cross-domain users: {len(cross_domain_profiles):,}")
    print(f"💾 Output: {output_dir}")
    print("=" * 70)
    print()
    
    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Process Amazon data for ADAM cold start system"
    )
    
    parser.add_argument(
        "--data-dir",
        type=str,
        default="/Users/chrisnocera/Sites/adam-platform/amazon",
        help="Path to Amazon data directory"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./amazon_processed",
        help="Output directory"
    )
    
    parser.add_argument(
        "--categories",
        type=str,
        default=None,
        help="Comma-separated list of categories"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit reviews per category"
    )
    
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode (5000 reviews per category)"
    )
    
    args = parser.parse_args()
    
    categories = None
    if args.categories:
        categories = [c.strip() for c in args.categories.split(",")]
    
    process_amazon_data(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        categories=categories,
        limit_per_category=args.limit,
        quick_mode=args.quick,
    )


if __name__ == "__main__":
    main()
