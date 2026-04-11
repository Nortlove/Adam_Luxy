#!/usr/bin/env python3
"""
ADAM MASTER DATASET INTEGRATOR

Orchestrates the integration of multiple datasets into ADAM's intelligence system.
Each dataset contributes a UNIQUE psychological layer.

Datasets and Their Unique Layers:
1. Amazon 2015 (23GB)      → TEMPORAL PSYCHOLOGY LAYER
2. Trustpilot UK (123K)    → UK MARKET PSYCHOLOGY LAYER  
3. TripAdvisor (201K)      → MULTI-ASPECT SATISFACTION LAYER
4. Drug Reviews (185K)     → HIGH-STAKES TRUST LAYER
5. Twitter Support (794K)  → SERVICE RECOVERY LAYER
6. Bank Reviews (19K)      → FINANCIAL TRUST LAYER (already integrated)

Usage:
    python scripts/master_dataset_integrator.py --status          # Check integration status
    python scripts/master_dataset_integrator.py --integrate all   # Integrate all datasets
    python scripts/master_dataset_integrator.py --update-priors   # Update coldstart priors
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

# Paths
PROJECT_ROOT = Path(__file__).parent.parent
DOWNLOAD_DIR = PROJECT_ROOT / "data" / "downloads" / "huggingface"
LEARNING_DIR = PROJECT_ROOT / "data" / "learning"
PRIORS_FILE = PROJECT_ROOT / "data" / "learning" / "multi_domain" / "complete_coldstart_priors.json"

# Dataset configurations
DATASETS = {
    "amazon_2015": {
        "name": "Amazon 2015 Temporal",
        "unique_layer": "TEMPORAL_PSYCHOLOGY",
        "source_type": "local_tsv",
        "source_path": "/Volumes/Sped/new_reviews_and_data/Amazon Review 2015",
        "processor": "scripts/process_amazon_2015_temporal.py",
        "checkpoint": "data/learning/temporal/checkpoint_amazon_2015_temporal.json",
        "estimated_reviews": 100_000_000,
        "psychological_value": [
            "Temporal drift analysis (language evolution over 10 years)",
            "Authenticity baseline (pre-social-media patterns)",
            "Persuasion validation (explicit helpful_votes)",
            "Archetype evolution tracking",
            "Vine/influencer patterns (proto-influencer analysis)",
        ],
        "integration_points": {
            "coldstart_priors": ["temporal_baselines", "mechanism_effectiveness_2015"],
            "atoms": ["UserStateAtom: archetype evolution", "MechanismActivationAtom: temporal decay"],
            "neo4j": ["TemporalPattern nodes", "EVOLVED_TO relationships"],
        },
    },
    "trustpilot_uk": {
        "name": "Trustpilot UK Market",
        "unique_layer": "UK_MARKET_PSYCHOLOGY",
        "source_type": "huggingface",
        "huggingface_id": "Kerassy/trustpilot-reviews-123k",
        "processor": "scripts/process_trustpilot_uk.py",
        "checkpoint": "data/downloads/huggingface/trustpilot_uk/checkpoint.json",
        "estimated_reviews": 123_181,
        "psychological_value": [
            "UK English expression calibration",
            "Service industry psychology (vs product reviews)",
            "Very recent data (Dec 2024 - Jan 2025)",
            "Cross-Atlantic psychological comparison",
            "B2C interaction patterns",
        ],
        "integration_points": {
            "coldstart_priors": ["uk_market_psychology", "british_expression_calibration"],
            "atoms": ["UserStateAtom: UK context detection", "MessageFramingAtom: British style"],
            "neo4j": ["Region nodes", "RegionalEffectiveness relationships"],
        },
    },
    "tripadvisor_hotels": {
        "name": "TripAdvisor Multi-Aspect",
        "unique_layer": "MULTI_ASPECT_SATISFACTION",
        "source_type": "huggingface",
        "huggingface_id": "jniimi/tripadvisor-review-rating",
        "processor": "scripts/process_tripadvisor_multiaspect.py",
        "checkpoint": "data/downloads/huggingface/tripadvisor_hotels/checkpoint.json",
        "estimated_reviews": 201_000,
        "psychological_value": [
            "Multi-dimensional satisfaction (6+ dimensions)",
            "Satisfaction composition analysis",
            "Hygiene vs delight factor detection",
            "Compensation effect modeling",
            "Travel mindset psychology",
        ],
        "integration_points": {
            "coldstart_priors": ["satisfaction_composition", "dimension_weights"],
            "atoms": ["UserStateAtom: archetype-dimension mapping", "MessageFramingAtom: dimension emphasis"],
            "neo4j": ["SatisfactionDimension nodes", "PRIORITIZES relationships"],
        },
    },
    "drug_reviews": {
        "name": "Drug Reviews High-Stakes",
        "unique_layer": "HIGH_STAKES_TRUST",
        "source_type": "huggingface",
        "huggingface_id": "forwins/Drug-Review-Dataset",
        "processor": "scripts/process_drug_reviews.py",
        "checkpoint": "data/downloads/huggingface/drug_reviews/checkpoint.json",
        "estimated_reviews": 185_000,
        "psychological_value": [
            "High-stakes decision psychology (parallels banking)",
            "Condition-specific psychological states",
            "Usefulness-validated persuasion patterns",
            "Health anxiety detection",
            "Treatment journey stages (like credit journeys)",
        ],
        "integration_points": {
            "coldstart_priors": ["health_psychology", "condition_patterns"],
            "atoms": ["UserStateAtom: health context detection", "Extend FinancialPsychologyService"],
            "neo4j": ["ConditionType nodes", "HealthJourneyStage nodes"],
        },
    },
    "twitter_support": {
        "name": "Twitter Customer Support",
        "unique_layer": "SERVICE_RECOVERY_PATTERNS",
        "source_type": "huggingface",
        "huggingface_id": "TNE-AI/customer-support-on-twitter-conversation",
        "processor": "scripts/process_twitter_support.py",
        "checkpoint": "data/downloads/huggingface/twitter_support/checkpoint.json",
        "estimated_reviews": 794_000,
        "psychological_value": [
            "Service recovery patterns",
            "Brand-customer interaction dynamics",
            "Complaint resolution psychology",
            "Public complaint behavior",
            "Real-time sentiment evolution",
        ],
        "integration_points": {
            "coldstart_priors": ["service_recovery_patterns", "complaint_resolution"],
            "atoms": ["UserStateAtom: complaint detection", "BrandPersonalityAtom: response style"],
            "neo4j": ["ServiceRecoveryPattern nodes", "RECOVERS_WITH relationships"],
        },
    },
    "bank_reviews": {
        "name": "Bank Reviews Financial Trust",
        "unique_layer": "FINANCIAL_TRUST",
        "source_type": "huggingface",
        "huggingface_id": "UniqueData/customers-reviews-on-banks",
        "processor": "scripts/process_bank_reviews.py",
        "checkpoint": "data/learning/multi_domain/checkpoint_bank_reviews.json",
        "estimated_reviews": 19_271,
        "psychological_value": [
            "Financial trust psychology",
            "Credit rebuilding journeys",
            "Banking relationship dynamics",
            "Financial anxiety detection",
            "Service interaction patterns",
        ],
        "integration_points": {
            "coldstart_priors": ["financial_psychology", "bank_profiles"],
            "atoms": ["UserStateAtom: FinancialPsychologyState", "MechanismActivationAtom: credit journey"],
            "neo4j": ["Bank nodes", "FinancialAnxietyState nodes", "CreditJourneyStage nodes"],
        },
        "status": "INTEGRATED",  # Already integrated
    },
}


def check_integration_status() -> Dict[str, Any]:
    """
    Check the integration status of all datasets.
    
    Returns:
        Status dictionary for all datasets
    """
    status = {
        "timestamp": datetime.now().isoformat(),
        "datasets": {},
        "summary": {
            "integrated": 0,
            "downloaded": 0,
            "pending": 0,
            "total_estimated_reviews": 0,
        },
    }
    
    for key, config in DATASETS.items():
        checkpoint_path = PROJECT_ROOT / config["checkpoint"]
        
        dataset_status = {
            "name": config["name"],
            "unique_layer": config["unique_layer"],
            "estimated_reviews": config["estimated_reviews"],
            "checkpoint_exists": checkpoint_path.exists(),
            "status": "UNKNOWN",
        }
        
        # Check if already integrated (special flag)
        if config.get("status") == "INTEGRATED":
            dataset_status["status"] = "INTEGRATED"
            status["summary"]["integrated"] += 1
        elif checkpoint_path.exists():
            # Check if it's a download checkpoint or full processing checkpoint
            try:
                with open(checkpoint_path) as f:
                    checkpoint_data = json.load(f)
                
                if "total_rows" in checkpoint_data:
                    dataset_status["status"] = "DOWNLOADED"
                    dataset_status["downloaded_rows"] = checkpoint_data.get("total_rows", 0)
                    status["summary"]["downloaded"] += 1
                elif "total_reviews" in checkpoint_data:
                    dataset_status["status"] = "PROCESSED"
                    status["summary"]["integrated"] += 1
                else:
                    dataset_status["status"] = "PARTIAL"
                    status["summary"]["downloaded"] += 1
            except:
                dataset_status["status"] = "ERROR"
                status["summary"]["pending"] += 1
        else:
            # Check if source exists for local datasets
            if config["source_type"] == "local_tsv":
                source_path = Path(config["source_path"])
                if source_path.exists():
                    dataset_status["status"] = "SOURCE_AVAILABLE"
                    status["summary"]["pending"] += 1
                else:
                    dataset_status["status"] = "SOURCE_MISSING"
                    status["summary"]["pending"] += 1
            else:
                dataset_status["status"] = "NOT_DOWNLOADED"
                status["summary"]["pending"] += 1
        
        status["summary"]["total_estimated_reviews"] += config["estimated_reviews"]
        status["datasets"][key] = dataset_status
    
    return status


def print_status():
    """Print integration status in a formatted way."""
    status = check_integration_status()
    
    print("\n" + "=" * 70)
    print("ADAM DATASET INTEGRATION STATUS")
    print("=" * 70)
    
    print(f"\n{'Dataset':<30} {'Unique Layer':<30} {'Status':<15}")
    print("-" * 75)
    
    for key, ds in status["datasets"].items():
        status_emoji = {
            "INTEGRATED": "✓",
            "PROCESSED": "✓",
            "DOWNLOADED": "○",
            "SOURCE_AVAILABLE": "○",
            "NOT_DOWNLOADED": "✗",
            "SOURCE_MISSING": "✗",
            "PARTIAL": "◐",
            "ERROR": "⚠",
        }.get(ds["status"], "?")
        
        print(f"{status_emoji} {ds['name']:<28} {ds['unique_layer']:<30} {ds['status']:<15}")
    
    print("-" * 75)
    print(f"\nSummary:")
    print(f"  Integrated: {status['summary']['integrated']}")
    print(f"  Downloaded: {status['summary']['downloaded']}")
    print(f"  Pending:    {status['summary']['pending']}")
    print(f"  Total Estimated Reviews: {status['summary']['total_estimated_reviews']:,}")
    print("=" * 70 + "\n")


def update_coldstart_priors(dataset_key: str) -> bool:
    """
    Update coldstart priors with intelligence from a specific dataset.
    
    Args:
        dataset_key: Key from DATASETS dictionary
        
    Returns:
        True if successful
    """
    if dataset_key not in DATASETS:
        logger.error(f"Unknown dataset: {dataset_key}")
        return False
    
    config = DATASETS[dataset_key]
    checkpoint_path = PROJECT_ROOT / config["checkpoint"]
    
    if not checkpoint_path.exists():
        logger.error(f"Checkpoint not found: {checkpoint_path}")
        return False
    
    # Load checkpoint
    with open(checkpoint_path) as f:
        checkpoint_data = json.load(f)
    
    # Load existing priors
    if PRIORS_FILE.exists():
        with open(PRIORS_FILE) as f:
            priors = json.load(f)
    else:
        priors = {}
    
    # Add dataset-specific priors
    layer_key = config["unique_layer"].lower()
    
    if dataset_key == "amazon_2015":
        # Add temporal baselines
        priors["temporal_psychology"] = {
            "source": "Amazon 2015",
            "extraction_date": checkpoint_data.get("extraction_timestamp", ""),
            "mechanism_effectiveness_2015": checkpoint_data.get("aggregate", {}).get("mechanism_effectiveness", {}),
            "archetype_distribution_2015": checkpoint_data.get("aggregate", {}).get("archetype_distribution", {}),
        }
    
    elif dataset_key == "trustpilot_uk":
        priors["uk_market_psychology"] = {
            "source": "Trustpilot UK 2024-2025",
            "total_reviews": checkpoint_data.get("total_rows", 0),
            "download_date": checkpoint_data.get("download_timestamp", ""),
        }
    
    elif dataset_key == "tripadvisor_hotels":
        priors["multi_aspect_satisfaction"] = {
            "source": "TripAdvisor Hotels",
            "total_reviews": checkpoint_data.get("total_rows", 0),
            "download_date": checkpoint_data.get("download_timestamp", ""),
        }
    
    # Save updated priors
    PRIORS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PRIORS_FILE, "w") as f:
        json.dump(priors, f, indent=2)
    
    logger.info(f"✓ Updated coldstart priors with {config['name']}")
    return True


def generate_integration_report() -> str:
    """Generate a comprehensive integration report."""
    status = check_integration_status()
    
    report = []
    report.append("# ADAM Dataset Integration Report")
    report.append(f"\nGenerated: {datetime.now().isoformat()}")
    report.append("\n## Summary")
    report.append(f"- **Total Datasets**: {len(DATASETS)}")
    report.append(f"- **Integrated**: {status['summary']['integrated']}")
    report.append(f"- **Downloaded**: {status['summary']['downloaded']}")
    report.append(f"- **Pending**: {status['summary']['pending']}")
    report.append(f"- **Total Reviews**: {status['summary']['total_estimated_reviews']:,}")
    
    report.append("\n## Dataset Details")
    
    for key, ds in status["datasets"].items():
        config = DATASETS[key]
        report.append(f"\n### {config['name']}")
        report.append(f"- **Unique Layer**: {config['unique_layer']}")
        report.append(f"- **Estimated Reviews**: {config['estimated_reviews']:,}")
        report.append(f"- **Status**: {ds['status']}")
        report.append(f"- **Psychological Value**:")
        for val in config["psychological_value"]:
            report.append(f"  - {val}")
        report.append(f"- **Integration Points**:")
        for comp, points in config["integration_points"].items():
            report.append(f"  - {comp}: {', '.join(points) if isinstance(points, list) else points}")
    
    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(
        description="ADAM Master Dataset Integrator"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Check integration status of all datasets"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate comprehensive integration report"
    )
    parser.add_argument(
        "--update-priors",
        type=str,
        help="Update coldstart priors from a specific dataset (or 'all')"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all datasets and their unique layers"
    )
    
    args = parser.parse_args()
    
    if args.status:
        print_status()
        return 0
    
    if args.list:
        print("\n" + "=" * 60)
        print("ADAM DATASET INVENTORY")
        print("=" * 60)
        for key, config in DATASETS.items():
            print(f"\n{key}:")
            print(f"  Name: {config['name']}")
            print(f"  Unique Layer: {config['unique_layer']}")
            print(f"  Reviews: {config['estimated_reviews']:,}")
        print("=" * 60 + "\n")
        return 0
    
    if args.report:
        report = generate_integration_report()
        report_file = PROJECT_ROOT / "docs" / "DATASET_INTEGRATION_REPORT.md"
        with open(report_file, "w") as f:
            f.write(report)
        print(f"Report saved to: {report_file}")
        print(report)
        return 0
    
    if args.update_priors:
        if args.update_priors == "all":
            for key in DATASETS.keys():
                update_coldstart_priors(key)
        else:
            update_coldstart_priors(args.update_priors)
        return 0
    
    # Default: show status
    print_status()
    return 0


if __name__ == "__main__":
    sys.exit(main())
