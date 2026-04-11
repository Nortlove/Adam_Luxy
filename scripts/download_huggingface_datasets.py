#!/usr/bin/env python3
"""
ADAM DATASET DOWNLOADER - HuggingFace Priority Datasets

Downloads and prepares high-priority datasets for ADAM integration.
Each dataset provides a UNIQUE psychological layer.

Usage:
    python scripts/download_huggingface_datasets.py --dataset trustpilot
    python scripts/download_huggingface_datasets.py --dataset all
    python scripts/download_huggingface_datasets.py --list
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DOWNLOAD_DIR = PROJECT_ROOT / "data" / "downloads" / "huggingface"
CHECKPOINT_DIR = PROJECT_ROOT / "data" / "learning" / "multi_domain"

# Dataset configurations
DATASETS = {
    "trustpilot_uk": {
        "name": "Trustpilot UK Reviews 123K",
        "huggingface_id": "Kerassy/trustpilot-reviews-123k",
        "unique_layer": "UK_MARKET_PSYCHOLOGY",
        "priority": 1,
        "estimated_size": "123,181 reviews",
        "description": "Recent UK company reviews (Dec 2024 - Jan 2025)",
        "psychological_value": [
            "UK English-speaking market patterns",
            "Service industry psychology", 
            "B2C interaction patterns",
            "VERY RECENT data (2024-2025)",
        ],
        "fields": ["text", "title", "rating", "company", "category"],
    },
    "tripadvisor_hotels": {
        "name": "TripAdvisor Hotel Reviews 201K",
        "huggingface_id": "jniimi/tripadvisor-review-rating",
        "unique_layer": "MULTI_ASPECT_SATISFACTION",
        "priority": 2,
        "estimated_size": "201,000 reviews",
        "description": "Multi-dimensional hotel satisfaction ratings",
        "psychological_value": [
            "Multi-aspect ratings (cleanliness, value, location, rooms, sleep)",
            "Service experience psychology",
            "Travel mindset patterns",
            "Expectation vs reality dynamics",
        ],
        "fields": ["text", "overall", "cleanliness", "value", "location", "rooms", "sleep_quality"],
    },
    "drug_reviews": {
        "name": "Drug Reviews 185K",
        "huggingface_id": "forwins/Drug-Review-Dataset",
        "unique_layer": "HIGH_STAKES_TRUST",
        "priority": 2,
        "estimated_size": "185,000 reviews",
        "description": "Patient drug reviews with conditions and ratings",
        "psychological_value": [
            "High-stakes decision psychology (like banking!)",
            "Health anxiety patterns",
            "Trust in institutional recommendations",
            "Long-term relationship dynamics",
        ],
        "fields": ["drugName", "condition", "review", "rating", "usefulCount"],
    },
    "twitter_support": {
        "name": "Twitter Customer Support 794K",
        "huggingface_id": "TNE-AI/customer-support-on-twitter-conversation",
        "unique_layer": "SERVICE_RECOVERY_PATTERNS",
        "priority": 2,
        "estimated_size": "794,000 conversations",
        "description": "Customer-company support interactions on Twitter",
        "psychological_value": [
            "Service recovery patterns",
            "Brand-customer interaction dynamics",
            "Complaint resolution psychology",
            "Public vs private complaint behavior",
        ],
        "fields": ["conversation_id", "company", "conversation", "summary"],
    },
    "airline_satisfaction": {
        "name": "Airline Satisfaction 130K",
        "huggingface_id": "drukeroni/airline-satisfaction-analysis",
        "unique_layer": "JOURNEY_TOUCHPOINT_ANALYSIS",
        "priority": 3,
        "estimated_size": "130,000 reviews",
        "description": "21-dimension airline satisfaction metrics",
        "psychological_value": [
            "Journey touchpoint psychology (21 dimensions!)",
            "Service quality expectations",
            "Premium vs economy psychology",
            "Delay tolerance and recovery",
        ],
        "fields": ["satisfaction", "inflight_wifi", "seat_comfort", "food_drink", "entertainment"],
    },
    "bestbuy_electronics": {
        "name": "Best Buy Electronics 45K",
        "huggingface_id": "ValerianFourel/bestbuy-reviews",
        "unique_layer": "OWNERSHIP_JOURNEY_PSYCHOLOGY",
        "priority": 3,
        "estimated_size": "45,000 reviews",
        "description": "Consumer electronics with ownership duration",
        "psychological_value": [
            "Tech purchase psychology",
            "Ownership duration patterns",
            "Post-purchase rationalization",
            "Brand response effectiveness",
        ],
        "fields": ["product", "rating", "verified", "ownership_duration", "text"],
    },
    "yelp_full": {
        "name": "Yelp Reviews Full 700K",
        "huggingface_id": "Yelp/yelp_review_full",
        "unique_layer": "LOCAL_BUSINESS_PSYCHOLOGY",
        "priority": 3,
        "estimated_size": "700,000 reviews",
        "description": "Local business reviews with star ratings",
        "psychological_value": [
            "Local business trust patterns",
            "Community-based recommendations",
            "Service industry psychology",
            "Word-of-mouth dynamics",
        ],
        "fields": ["text", "label"],
    },
    "steam_games": {
        "name": "Steam Games Dataset 124K",
        "huggingface_id": "FronkonGames/steam-games-dataset",
        "unique_layer": "ENGAGEMENT_DEPTH_PSYCHOLOGY",
        "priority": 3,
        "estimated_size": "124,000 games",
        "description": "Gaming metadata with player engagement metrics",
        "psychological_value": [
            "Engagement depth patterns (playtime = commitment)",
            "Entertainment value psychology",
            "Community-driven recommendations",
            "Price sensitivity in entertainment",
        ],
        "fields": ["name", "positive", "negative", "user_score", "peak_ccu", "price"],
    },
}


def download_dataset(dataset_key: str, force: bool = False) -> Optional[Dict[str, Any]]:
    """
    Download a specific dataset from HuggingFace.
    
    Args:
        dataset_key: Key from DATASETS dictionary
        force: Force re-download even if exists
        
    Returns:
        Dataset info dict or None if failed
    """
    if dataset_key not in DATASETS:
        logger.error(f"Unknown dataset: {dataset_key}")
        logger.info(f"Available datasets: {list(DATASETS.keys())}")
        return None
    
    config = DATASETS[dataset_key]
    output_dir = DOWNLOAD_DIR / dataset_key
    checkpoint_file = output_dir / "checkpoint.json"
    
    # Check if already downloaded
    if checkpoint_file.exists() and not force:
        logger.info(f"Dataset {dataset_key} already downloaded. Use --force to re-download.")
        with open(checkpoint_file) as f:
            return json.load(f)
    
    logger.info("=" * 60)
    logger.info(f"DOWNLOADING: {config['name']}")
    logger.info(f"Unique Layer: {config['unique_layer']}")
    logger.info(f"Estimated Size: {config['estimated_size']}")
    logger.info("=" * 60)
    
    try:
        from datasets import load_dataset
        
        # Create output directory
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Download dataset
        logger.info(f"Loading from HuggingFace: {config['huggingface_id']}")
        
        # Handle different dataset structures
        if dataset_key == "tripadvisor_hotels":
            dataset = load_dataset(config["huggingface_id"])
        elif dataset_key == "twitter_support":
            dataset = load_dataset(config["huggingface_id"])
        else:
            dataset = load_dataset(config["huggingface_id"])
        
        # Get dataset statistics
        stats = {
            "dataset_key": dataset_key,
            "name": config["name"],
            "huggingface_id": config["huggingface_id"],
            "unique_layer": config["unique_layer"],
            "download_timestamp": datetime.now().isoformat(),
            "splits": {},
            "total_rows": 0,
        }
        
        # Process each split
        for split_name in dataset.keys():
            split_data = dataset[split_name]
            split_rows = len(split_data)
            stats["splits"][split_name] = split_rows
            stats["total_rows"] += split_rows
            
            # Save split to parquet
            output_file = output_dir / f"{split_name}.parquet"
            split_data.to_parquet(str(output_file))
            logger.info(f"  Saved {split_name}: {split_rows:,} rows → {output_file.name}")
        
        # Sample first few rows for verification
        first_split = list(dataset.keys())[0]
        sample = dataset[first_split][:3]
        stats["sample_fields"] = list(sample.keys()) if hasattr(sample, 'keys') else list(dataset[first_split].features.keys())
        
        # Save checkpoint
        with open(checkpoint_file, "w") as f:
            json.dump(stats, f, indent=2)
        
        logger.info(f"✓ Download complete: {stats['total_rows']:,} total rows")
        logger.info(f"✓ Checkpoint saved: {checkpoint_file}")
        
        return stats
        
    except ImportError:
        logger.error("HuggingFace datasets library not installed!")
        logger.error("Install with: pip install datasets")
        return None
    except Exception as e:
        logger.error(f"Failed to download {dataset_key}: {e}")
        import traceback
        traceback.print_exc()
        return None


def download_all_priority(max_priority: int = 2, force: bool = False) -> Dict[str, Any]:
    """
    Download all datasets up to specified priority level.
    
    Args:
        max_priority: Maximum priority level to download (1=highest)
        force: Force re-download
        
    Returns:
        Summary of downloaded datasets
    """
    results = {
        "timestamp": datetime.now().isoformat(),
        "datasets": {},
        "success_count": 0,
        "failed_count": 0,
    }
    
    # Sort by priority
    sorted_datasets = sorted(
        DATASETS.items(),
        key=lambda x: x[1]["priority"]
    )
    
    for dataset_key, config in sorted_datasets:
        if config["priority"] > max_priority:
            logger.info(f"Skipping {dataset_key} (priority {config['priority']} > {max_priority})")
            continue
        
        result = download_dataset(dataset_key, force=force)
        
        if result:
            results["datasets"][dataset_key] = result
            results["success_count"] += 1
        else:
            results["datasets"][dataset_key] = {"error": "Download failed"}
            results["failed_count"] += 1
    
    # Save summary
    summary_file = DOWNLOAD_DIR / "download_summary.json"
    with open(summary_file, "w") as f:
        json.dump(results, f, indent=2)
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("DOWNLOAD SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Successful: {results['success_count']}")
    logger.info(f"Failed: {results['failed_count']}")
    logger.info(f"Summary saved: {summary_file}")
    
    return results


def list_datasets():
    """Print available datasets with their unique layers."""
    print("\n" + "=" * 70)
    print("AVAILABLE DATASETS FOR ADAM INTEGRATION")
    print("=" * 70)
    
    # Sort by priority
    sorted_datasets = sorted(
        DATASETS.items(),
        key=lambda x: x[1]["priority"]
    )
    
    for dataset_key, config in sorted_datasets:
        status = "✓ Downloaded" if (DOWNLOAD_DIR / dataset_key / "checkpoint.json").exists() else "○ Not downloaded"
        
        print(f"\n[P{config['priority']}] {dataset_key}")
        print(f"    Name: {config['name']}")
        print(f"    Unique Layer: {config['unique_layer']}")
        print(f"    Size: {config['estimated_size']}")
        print(f"    Status: {status}")
        print(f"    Value: {', '.join(config['psychological_value'][:2])}")
    
    print("\n" + "=" * 70)
    print("Usage:")
    print("  python scripts/download_huggingface_datasets.py --dataset trustpilot_uk")
    print("  python scripts/download_huggingface_datasets.py --priority 2  # Download P1 and P2")
    print("  python scripts/download_huggingface_datasets.py --all")
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Download HuggingFace datasets for ADAM integration"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        help="Specific dataset to download (e.g., trustpilot_uk, tripadvisor_hotels)"
    )
    parser.add_argument(
        "--priority",
        type=int,
        default=2,
        help="Download all datasets up to this priority level (default: 2)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Download all datasets regardless of priority"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if already exists"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available datasets"
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_datasets()
        return 0
    
    if args.dataset:
        result = download_dataset(args.dataset, force=args.force)
        return 0 if result else 1
    
    if args.all:
        results = download_all_priority(max_priority=99, force=args.force)
        return 0 if results["failed_count"] == 0 else 1
    
    # Default: download priority 1 and 2
    results = download_all_priority(max_priority=args.priority, force=args.force)
    return 0 if results["failed_count"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
