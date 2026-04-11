#!/usr/bin/env python3
# =============================================================================
# ADAM Platform - Pre-Learning Script
# Location: scripts/run_prelearning.py
# =============================================================================

"""
Run Pre-Learning on Amazon Review Corpus

This script processes millions of Amazon reviews to:
1. Build category psychological profiles
2. Train the unified psychological intelligence
3. Populate the storage with baseline profiles
4. Establish mechanism effectiveness patterns
5. Create learning signals for continuous improvement

Usage:
    # Full pre-learning (all categories)
    python scripts/run_prelearning.py
    
    # Specific categories only
    python scripts/run_prelearning.py --categories Tools_and_Home_Improvement Electronics
    
    # Quick test (limited reviews)
    python scripts/run_prelearning.py --test
    
    # Resume from previous run
    python scripts/run_prelearning.py --resume

Progress is saved automatically and can be resumed if interrupted.
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from adam.data.amazon import (
    get_prelearning_orchestrator,
    PreLearningConfig,
    AMAZON_CATEGORIES,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/prelearning.log', mode='a'),
    ]
)
logger = logging.getLogger(__name__)


async def run_prelearning(
    categories: list = None,
    test_mode: bool = False,
    resume: bool = False,
    batch_size: int = 100,
    max_reviews: int = 10000,
):
    """Run the pre-learning process."""
    
    print("=" * 70)
    print("ADAM PLATFORM - PRE-LEARNING FROM AMAZON REVIEW CORPUS")
    print("=" * 70)
    
    # Configure
    config = PreLearningConfig(
        batch_size=batch_size,
        max_reviews_per_category=50 if test_mode else max_reviews,
        verified_only=True,
        min_text_length=50,
        enable_unified_intelligence=True,
        enable_relationship_detection=True,
        enable_graph_storage=True,
        enable_mechanism_learning=True,
        save_progress=True,
        categories=categories,
    )
    
    if test_mode:
        print("\n[TEST MODE] Processing limited reviews per category")
        config.categories = categories or ["Tools_and_Home_Improvement"]
    
    # Get orchestrator
    orchestrator = get_prelearning_orchestrator(config)
    
    # Resume if requested
    if resume:
        if orchestrator.load_progress():
            print(f"\nResuming from previous run:")
            progress = orchestrator.get_progress()
            print(f"  Categories completed: {len(progress.categories_completed)}")
            print(f"  Categories remaining: {len(progress.categories_remaining)}")
            print(f"  Reviews processed: {progress.reviews_processed:,}")
        else:
            print("\nNo previous progress found, starting fresh")
    
    # Show configuration
    categories_to_process = config.categories or AMAZON_CATEGORIES
    print(f"\nConfiguration:")
    print(f"  Categories to process: {len(categories_to_process)}")
    print(f"  Max reviews per category: {config.max_reviews_per_category:,}")
    print(f"  Batch size: {config.batch_size}")
    print(f"  Test mode: {test_mode}")
    
    print("\nCategories:")
    for i, cat in enumerate(categories_to_process, 1):
        print(f"  {i}. {cat}")
    
    print("\n" + "-" * 70)
    print("Starting pre-learning...")
    print("-" * 70 + "\n")
    
    # Run pre-learning
    try:
        progress = await orchestrator.run_full_prelearning()
        
        # Print summary
        print("\n" + "=" * 70)
        print("PRE-LEARNING COMPLETE")
        print("=" * 70)
        print(f"\nSummary:")
        print(f"  Categories processed: {len(progress.categories_completed)}")
        print(f"  Reviews analyzed: {progress.reviews_processed:,}")
        print(f"  Profiles created: {progress.profiles_created:,}")
        print(f"  Learning signals emitted: {progress.learning_signals_emitted:,}")
        
        if progress.errors:
            print(f"\nErrors ({len(progress.errors)}):")
            for err in progress.errors[-5:]:
                print(f"  - {err}")
        
        return progress
        
    except KeyboardInterrupt:
        print("\n\nPre-learning interrupted. Progress saved.")
        print("Run with --resume to continue.")
        return None


async def show_category_stats():
    """Show statistics about available categories."""
    from adam.data.amazon import get_amazon_client
    
    client = get_amazon_client()
    await client.initialize()
    stats = await client.get_stats()
    
    print("\nAmazon Review Corpus Statistics")
    print("=" * 50)
    print(f"Data directory: {stats['data_dir']}")
    print(f"Index available: {stats['index_available']}")
    print(f"\nCategories ({len(stats['categories'])}):")
    
    for cat in stats['categories']:
        print(f"  - {cat['name']}")


def main():
    parser = argparse.ArgumentParser(
        description="Run pre-learning on Amazon review corpus"
    )
    parser.add_argument(
        "--categories", "-c",
        nargs="+",
        help="Specific categories to process"
    )
    parser.add_argument(
        "--test", "-t",
        action="store_true",
        help="Test mode (limited reviews)"
    )
    parser.add_argument(
        "--resume", "-r",
        action="store_true",
        help="Resume from previous run"
    )
    parser.add_argument(
        "--batch-size", "-b",
        type=int,
        default=100,
        help="Batch size for processing"
    )
    parser.add_argument(
        "--max-reviews", "-m",
        type=int,
        default=10000,
        help="Max reviews per category"
    )
    parser.add_argument(
        "--stats", "-s",
        action="store_true",
        help="Show category statistics only"
    )
    
    args = parser.parse_args()
    
    # Create logs directory
    Path("logs").mkdir(exist_ok=True)
    
    if args.stats:
        asyncio.run(show_category_stats())
        return
    
    # Run pre-learning
    asyncio.run(run_prelearning(
        categories=args.categories,
        test_mode=args.test,
        resume=args.resume,
        batch_size=args.batch_size,
        max_reviews=args.max_reviews,
    ))


if __name__ == "__main__":
    main()
