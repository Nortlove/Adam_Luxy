#!/usr/bin/env python3
"""
Run Twitter Mental Health and Google Local ingestion.

This script runs:
1. Twitter Mental Health - using music profiles with lyrics and emotion scores
2. Google Local - all 50 states (~201GB)

Usage:
    python scripts/run_twitter_google_ingestion.py
    python scripts/run_twitter_google_ingestion.py --twitter-only
    python scripts/run_twitter_google_ingestion.py --google-only
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from scripts.run_multi_dataset_ingestion import (
    process_twitter,
    process_google_local,
    logger,
    REVIEW_DATA_ROOT,
    OUTPUT_DIR,
)


def save_result(result):
    """Save a dataset result to JSON."""
    result_file = OUTPUT_DIR / f"{result.name}_result.json"
    with open(result_file, 'w') as f:
        json.dump(result.to_dict(), f, indent=2)
    logger.info(f"  Saved: {result_file}")


def main():
    parser = argparse.ArgumentParser(description="Run Twitter and Google Local ingestion")
    parser.add_argument("--twitter-only", action="store_true", help="Only run Twitter")
    parser.add_argument("--google-only", action="store_true", help="Only run Google Local")
    args = parser.parse_args()
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    # Twitter Mental Health
    if not args.google_only:
        print("\n" + "=" * 70)
        print("TWITTER MENTAL HEALTH INGESTION")
        print("Using: musics_profiles_anonymized.csv (lyrics + pre-computed emotions)")
        print("=" * 70 + "\n")
        
        twitter_config = {
            "name": "twitter",
            "display_name": "Twitter Mental Health",
            "path": REVIEW_DATA_ROOT / "Twitter",
            "file_type": "twitter",
            "unique_value": "Emotional state intelligence and mental health signals",
            "size_mb": 19000,
        }
        
        twitter_result = process_twitter(twitter_config)
        save_result(twitter_result)
        results.append(twitter_result)
        
        print(f"\nTwitter Results:")
        print(f"  Lyrics processed: {twitter_result.reviews_processed:,}")
        print(f"  Templates extracted: {twitter_result.templates_extracted:,}")
        print(f"  Duration: {twitter_result.duration_seconds:.1f}s")
        print(f"  Emotion profiles: {twitter_result.specific_intelligence.get('avg_emotion_profile', {})}")
    
    # Google Local
    if not args.twitter_only:
        print("\n" + "=" * 70)
        print("GOOGLE LOCAL INGESTION")
        print("Processing all 52 state files (~201GB) - THIS WILL TAKE SEVERAL HOURS")
        print("=" * 70 + "\n")
        
        google_config = {
            "name": "google_local",
            "display_name": "Google Local (50 States)",
            "path": REVIEW_DATA_ROOT / "Google",
            "file_type": "google",
            "unique_value": "Hyperlocal targeting by state/city with business responses",
            "size_mb": 201000,
        }
        
        google_result = process_google_local(google_config)
        save_result(google_result)
        results.append(google_result)
        
        print(f"\nGoogle Local Results:")
        print(f"  Reviews processed: {google_result.reviews_processed:,}")
        print(f"  Templates extracted: {google_result.templates_extracted:,}")
        print(f"  Duration: {google_result.duration_seconds / 3600:.2f} hours")
    
    # Summary
    if results:
        print("\n" + "=" * 70)
        print("INGESTION COMPLETE")
        print("=" * 70)
        total_reviews = sum(r.reviews_processed for r in results)
        total_templates = sum(r.templates_extracted for r in results)
        total_duration = sum(r.duration_seconds for r in results)
        print(f"  Total reviews: {total_reviews:,}")
        print(f"  Total templates: {total_templates:,}")
        print(f"  Total duration: {total_duration / 3600:.2f} hours")


if __name__ == "__main__":
    main()
