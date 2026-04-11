#!/usr/bin/env python3
# =============================================================================
# Build Amazon Local Review Database Index
# Location: scripts/build_amazon_index.py
# =============================================================================

"""
Builds the SQLite index for fast Amazon product/brand search.

This is a ONE-TIME operation that creates an index from the metadata JSONL files.
The index enables fast lookups by brand and product name without loading the
massive JSONL files into memory.

Usage:
    # Build full index (all categories)
    python scripts/build_amazon_index.py
    
    # Build with specific categories
    python scripts/build_amazon_index.py --categories Books,Digital_Music
    
    # Quick test (1000 products per category)
    python scripts/build_amazon_index.py --quick
    
    # Force rebuild
    python scripts/build_amazon_index.py --force
    
    # Show index stats
    python scripts/build_amazon_index.py --stats
"""

import argparse
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def main():
    parser = argparse.ArgumentParser(
        description="Build Amazon product metadata index for fast search"
    )
    
    parser.add_argument(
        "--data-dir",
        type=str,
        default="/Users/chrisnocera/Sites/adam-platform/amazon",
        help="Path to Amazon data directory"
    )
    
    parser.add_argument(
        "--categories",
        type=str,
        default=None,
        help="Comma-separated list of categories to index"
    )
    
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit products per category (for testing)"
    )
    
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Quick mode (1000 products per category)"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force rebuild even if index exists"
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show index statistics and exit"
    )
    
    args = parser.parse_args()
    
    from adam.data.amazon import MetadataIndexer, build_metadata_index
    
    # Show stats only
    if args.stats:
        indexer = MetadataIndexer(args.data_dir)
        stats = indexer.get_stats()
        
        print("\n" + "=" * 60)
        print("AMAZON INDEX STATISTICS")
        print("=" * 60)
        
        if stats.get("status") == "not_built":
            print("Index has not been built yet.")
            print("Run: python scripts/build_amazon_index.py")
        else:
            print(f"Total products: {stats.get('total_products', 0):,}")
            print(f"With brand: {stats.get('with_brand', 0):,}")
            print("\nBy category:")
            for cat, count in stats.get("by_category", {}).items():
                print(f"  {cat}: {count:,}")
        
        print("=" * 60)
        indexer.close()
        return
    
    # Parse categories
    categories = None
    if args.categories:
        categories = [c.strip() for c in args.categories.split(",")]
    
    # Set limit for quick mode
    limit = args.limit
    if args.quick and not limit:
        limit = 1000
    
    print("\n" + "=" * 60)
    print("AMAZON INDEX BUILDER")
    print("=" * 60)
    print(f"Data directory: {args.data_dir}")
    if categories:
        print(f"Categories: {', '.join(categories)}")
    else:
        print("Categories: ALL")
    if limit:
        print(f"Limit per category: {limit:,}")
    print(f"Force rebuild: {args.force}")
    print("=" * 60)
    print()
    
    # Build index
    stats = build_metadata_index(
        data_dir=args.data_dir,
        categories=categories,
        limit_per_category=limit,
        force_rebuild=args.force,
    )
    
    # Show results
    print("\n" + "=" * 60)
    print("INDEX BUILD COMPLETE")
    print("=" * 60)
    
    if stats.get("status") == "skipped":
        print("Index already exists. Use --force to rebuild.")
    else:
        print(f"Total products indexed: {stats.get('total_products', 0):,}")
        print(f"With brand: {stats.get('total_with_brand', 0):,}")
        print("\nCategories:")
        for cat_stat in stats.get("categories", []):
            print(f"  {cat_stat['category']}: {cat_stat['products']:,} products")
    
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
