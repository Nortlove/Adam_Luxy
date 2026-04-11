#!/usr/bin/env python3
"""
COMPREHENSIVE DATA PROCESSOR FOR ALL DATASETS
==============================================

Processes ALL downloaded datasets for maximum impact:
- Criteo Uplift → Persuadability calibration
- Criteo Attribution → Multi-touch sequencing
- Yelp Reviews → Cross-platform patterns
- Amazon Polarity → Sentiment baseline
- IMDB Reviews → Entertainment mindset
- Domain Mapping → Context intelligence

Run:
    python process_all_datasets.py --all
"""

import argparse
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import re

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Paths
HF_DATA_DIR = Path("/Volumes/Sped/new_reviews_and_data/hf_datasets")
OUTPUT_DIR = Path("/Volumes/Sped/new_reviews_and_data/processed_priors")


# =============================================================================
# PSYCHOLOGICAL EXTRACTION PATTERNS
# =============================================================================

MOTIVATION_PATTERNS = {
    "functional_need": re.compile(r'\bneed(?:ed|s)?\b|\brequired?\b|\bnecessary\b', re.I),
    "quality_seeking": re.compile(r'\bbest\s+quality\b|\bpremium\b|\bwell[\s-]?made\b|\bdurable\b', re.I),
    "value_seeking": re.compile(r'\bgreat\s+(?:deal|value|price)\b|\bbargain\b|\baffordable\b', re.I),
    "status_signaling": re.compile(r'\bimpress\b|\bluxury\b|\bprestige\b|\bcompliments?\b', re.I),
    "self_reward": re.compile(r'\btreat\s+(?:my)?self\b|\bdeserve\b|\bindulge\b', re.I),
    "gift_giving": re.compile(r'\bgift\b|\bfor\s+(?:my\s+)?(?:wife|husband|mom|dad)\b|\bbirthday\b', re.I),
    "impulse": re.compile(r'\bimpulse\b|\bcouldn\'t\s+resist\b|\bjust\s+had\s+to\b', re.I),
    "research_driven": re.compile(r'\bresearch(?:ed)?\b|\bcompared?\b|\bread\s+reviews\b', re.I),
    "recommendation": re.compile(r'\brecommend(?:ed)?\b|\bwas\s+told\b|\bfriend\s+suggested\b', re.I),
    "brand_loyalty": re.compile(r'\balways\s+(?:buy|use)\b|\bloyal\b|\btrust\s+(?:this\s+)?brand\b', re.I),
    "social_proof": re.compile(r'\beveryone\b|\bpopular\b|\btrending\b', re.I),
}

DECISION_PATTERNS = {
    "fast": re.compile(r'\bquickly\b|\bimmediately\b|\bimpulse\b', re.I),
    "deliberate": re.compile(r'\bresearch\b|\bcompared?\b|\bweighed\b|\bstudied\b', re.I),
}

EMOTIONAL_PATTERNS = {
    "high_positive": re.compile(r'\b(?:amazing|incredible|perfect|wonderful|love|obsessed)\b', re.I),
    "high_negative": re.compile(r'\b(?:terrible|horrible|awful|hate|worst)\b', re.I),
    "low": re.compile(r'\b(?:adequate|acceptable|okay|fine)\b', re.I),
}


def extract_motivation(text: str) -> str:
    """Extract primary motivation from text."""
    scores = {}
    text_lower = text.lower()
    
    for motivation, pattern in MOTIVATION_PATTERNS.items():
        matches = len(pattern.findall(text_lower))
        if matches > 0:
            scores[motivation] = matches
    
    return max(scores.keys(), key=lambda k: scores[k]) if scores else "functional_need"


def extract_decision_style(text: str) -> str:
    """Extract decision style from text."""
    text_lower = text.lower()
    fast = len(DECISION_PATTERNS["fast"].findall(text_lower))
    deliberate = len(DECISION_PATTERNS["deliberate"].findall(text_lower))
    
    if deliberate > fast:
        return "deliberate"
    elif fast > deliberate:
        return "fast"
    return "moderate"


def extract_emotional_intensity(text: str) -> str:
    """Extract emotional intensity from text."""
    text_lower = text.lower()
    high_pos = len(EMOTIONAL_PATTERNS["high_positive"].findall(text_lower))
    high_neg = len(EMOTIONAL_PATTERNS["high_negative"].findall(text_lower))
    low = len(EMOTIONAL_PATTERNS["low"].findall(text_lower))
    
    if high_pos + high_neg > low or text.count('!') >= 2:
        return "high"
    elif low > high_pos + high_neg:
        return "low"
    return "moderate"


# =============================================================================
# DATASET PROCESSORS
# =============================================================================

def process_criteo_uplift(output_dir: Path) -> Dict[str, Any]:
    """Process Criteo uplift data for persuadability calibration."""
    logger.info("Processing Criteo Uplift data...")
    
    uplift_path = HF_DATA_DIR / "criteo_uplift"
    if not uplift_path.exists():
        logger.warning("Criteo uplift data not found")
        return {}
    
    try:
        from datasets import load_from_disk
        ds = load_from_disk(str(uplift_path))
        
        train_data = ds['train'] if 'train' in ds else ds
        sample_size = min(500000, len(train_data))
        
        treatment_conversions = 0
        control_conversions = 0
        treatment_count = 0
        control_count = 0
        
        for i, row in enumerate(train_data):
            if i >= sample_size:
                break
            
            treatment = row.get('treatment', 0)
            conversion = row.get('conversion', row.get('visit', 0))
            
            if treatment:
                treatment_count += 1
                treatment_conversions += conversion
            else:
                control_count += 1
                control_conversions += conversion
        
        treatment_rate = treatment_conversions / treatment_count if treatment_count > 0 else 0
        control_rate = control_conversions / control_count if control_count > 0 else 0
        uplift = treatment_rate - control_rate
        
        result = {
            "source": "criteo_uplift",
            "sample_size": sample_size,
            "treatment_count": treatment_count,
            "control_count": control_count,
            "treatment_conversion_rate": round(treatment_rate, 5),
            "control_conversion_rate": round(control_rate, 5),
            "average_uplift": round(uplift, 5),
            "relative_uplift": round(uplift / control_rate if control_rate > 0 else 0, 4),
            "persuadability_calibrations": {
                "highly_persuadable": {"uplift_multiplier": 2.0, "base_conversion": treatment_rate * 1.5},
                "moderately_persuadable": {"uplift_multiplier": 1.0, "base_conversion": treatment_rate},
                "low_persuadability": {"uplift_multiplier": 0.5, "base_conversion": treatment_rate * 0.7},
                "resistant": {"uplift_multiplier": 0.1, "base_conversion": control_rate * 0.5},
            }
        }
        
        logger.info(f"  Uplift: {uplift:.2%} (treatment: {treatment_rate:.2%}, control: {control_rate:.2%})")
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing Criteo uplift: {e}")
        return {}


def process_criteo_attribution(output_dir: Path) -> Dict[str, Any]:
    """Process Criteo attribution data for multi-touch sequencing."""
    logger.info("Processing Criteo Attribution data...")
    
    attribution_path = HF_DATA_DIR / "criteo_attribution"
    if not attribution_path.exists():
        logger.warning("Criteo attribution data not found")
        return {}
    
    try:
        from datasets import load_from_disk
        ds = load_from_disk(str(attribution_path))
        
        train_data = ds['train'] if 'train' in ds else ds
        sample_size = min(500000, len(train_data))
        
        conversions = 0
        path_lengths = []
        
        for i, row in enumerate(train_data):
            if i >= sample_size:
                break
            
            conversion = row.get('conversion', row.get('Sale', 0))
            conversions += conversion
            
            # Count touchpoints
            touchpoints = sum(1 for k, v in row.items() 
                            if ('timestamp' in k.lower() or 'click' in k.lower()) and v and v > 0)
            if touchpoints > 0:
                path_lengths.append(min(touchpoints, 20))
        
        avg_path_length = sum(path_lengths) / len(path_lengths) if path_lengths else 0
        conversion_rate = conversions / sample_size if sample_size > 0 else 0
        
        # Compute path distribution
        path_dist = defaultdict(int)
        for length in path_lengths:
            bucket = f"{length}" if length < 10 else "10+"
            path_dist[bucket] += 1
        
        total_paths = len(path_lengths)
        path_distribution = {k: round(v / total_paths, 4) for k, v in sorted(path_dist.items())}
        
        result = {
            "source": "criteo_attribution",
            "sample_size": sample_size,
            "total_conversions": conversions,
            "conversion_rate": round(conversion_rate, 5),
            "avg_path_length": round(avg_path_length, 2),
            "path_distribution": path_distribution,
            "attribution_insights": {
                "first_touch_weight": 0.30,
                "last_touch_weight": 0.40,
                "middle_touches_weight": 0.30,
                "optimal_touchpoints_by_decision_style": {
                    "fast": 2,
                    "moderate": 4,
                    "deliberate": 6,
                }
            }
        }
        
        logger.info(f"  Avg path: {avg_path_length:.1f} touchpoints, conversion: {conversion_rate:.2%}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing Criteo attribution: {e}")
        return {}


def process_yelp_reviews(output_dir: Path) -> Dict[str, Any]:
    """Process Yelp reviews for cross-platform patterns."""
    logger.info("Processing Yelp reviews...")
    
    yelp_path = HF_DATA_DIR / "yelp_reviews"
    if not yelp_path.exists():
        yelp_path = HF_DATA_DIR / "yelp_polarity"
    
    if not yelp_path.exists():
        logger.warning("Yelp data not found")
        return {}
    
    try:
        from datasets import load_from_disk
        ds = load_from_disk(str(yelp_path))
        
        train_data = ds['train'] if 'train' in ds else ds
        sample_size = min(200000, len(train_data))
        
        motivation_counts = defaultdict(int)
        decision_counts = defaultdict(int)
        emotional_counts = defaultdict(int)
        
        for i, row in enumerate(train_data):
            if i >= sample_size:
                break
            
            text = row.get('text', '')
            if not text or len(text) < 20:
                continue
            
            motivation_counts[extract_motivation(text)] += 1
            decision_counts[extract_decision_style(text)] += 1
            emotional_counts[extract_emotional_intensity(text)] += 1
        
        total = sum(motivation_counts.values())
        
        result = {
            "source": "yelp_reviews",
            "sample_size": total,
            "platform": "yelp",
            "motivation_distribution": {k: round(v / total, 4) for k, v in motivation_counts.items()},
            "decision_style_distribution": {k: round(v / total, 4) for k, v in decision_counts.items()},
            "emotional_intensity_distribution": {k: round(v / total, 4) for k, v in emotional_counts.items()},
            "platform_characteristics": {
                "expression_style": "detailed_review",
                "authenticity_baseline": 0.75,
                "typical_length": "medium_to_long",
            }
        }
        
        top_motivation = max(motivation_counts.keys(), key=lambda k: motivation_counts[k])
        logger.info(f"  {total:,} reviews, top motivation: {top_motivation}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing Yelp: {e}")
        return {}


def process_amazon_polarity(output_dir: Path) -> Dict[str, Any]:
    """Process Amazon polarity data for sentiment baseline."""
    logger.info("Processing Amazon polarity...")
    
    amazon_path = HF_DATA_DIR / "amazon_polarity"
    if not amazon_path.exists():
        logger.warning("Amazon polarity data not found")
        return {}
    
    try:
        from datasets import load_from_disk
        ds = load_from_disk(str(amazon_path))
        
        train_data = ds['train'] if 'train' in ds else ds
        sample_size = min(500000, len(train_data))
        
        motivation_counts = defaultdict(int)
        decision_counts = defaultdict(int)
        positive_count = 0
        
        for i, row in enumerate(train_data):
            if i >= sample_size:
                break
            
            text = row.get('content', row.get('text', ''))
            label = row.get('label', 0)
            
            if not text or len(text) < 20:
                continue
            
            motivation_counts[extract_motivation(text)] += 1
            decision_counts[extract_decision_style(text)] += 1
            if label == 1:
                positive_count += 1
        
        total = sum(motivation_counts.values())
        
        result = {
            "source": "amazon_polarity",
            "sample_size": total,
            "positive_ratio": round(positive_count / total, 4) if total > 0 else 0,
            "motivation_distribution": {k: round(v / total, 4) for k, v in motivation_counts.items()},
            "decision_style_distribution": {k: round(v / total, 4) for k, v in decision_counts.items()},
            "sentiment_baseline": {
                "positive": round(positive_count / total, 4) if total > 0 else 0.5,
                "negative": round((total - positive_count) / total, 4) if total > 0 else 0.5,
            }
        }
        
        logger.info(f"  {total:,} reviews, positive ratio: {result['positive_ratio']:.1%}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing Amazon polarity: {e}")
        return {}


def process_imdb_reviews(output_dir: Path) -> Dict[str, Any]:
    """Process IMDB reviews for entertainment mindset."""
    logger.info("Processing IMDB reviews...")
    
    imdb_path = HF_DATA_DIR / "imdb_reviews"
    if not imdb_path.exists():
        logger.warning("IMDB data not found")
        return {}
    
    try:
        from datasets import load_from_disk
        ds = load_from_disk(str(imdb_path))
        
        train_data = ds['train'] if 'train' in ds else ds
        sample_size = min(25000, len(train_data))
        
        emotional_counts = defaultdict(int)
        positive_count = 0
        
        for i, row in enumerate(train_data):
            if i >= sample_size:
                break
            
            text = row.get('text', '')
            label = row.get('label', 0)
            
            if not text:
                continue
            
            emotional_counts[extract_emotional_intensity(text)] += 1
            if label == 1:
                positive_count += 1
        
        total = sum(emotional_counts.values())
        
        result = {
            "source": "imdb_reviews",
            "sample_size": total,
            "domain": "entertainment",
            "positive_ratio": round(positive_count / total, 4) if total > 0 else 0,
            "emotional_intensity_distribution": {k: round(v / total, 4) for k, v in emotional_counts.items()},
            "mindset_profile": {
                "mindset": "entertainment",
                "openness": 0.85,
                "engagement": 0.80,
                "persuasion_receptivity": 0.65,
            }
        }
        
        logger.info(f"  {total:,} reviews, emotional intensity distribution computed")
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing IMDB: {e}")
        return {}


def process_domain_mapping(output_dir: Path) -> Dict[str, Any]:
    """Process domain mapping data for context intelligence."""
    logger.info("Processing domain mapping...")
    
    domain_path = HF_DATA_DIR / "domain_mapping"
    if not domain_path.exists():
        logger.warning("Domain mapping data not found")
        return {}
    
    try:
        from datasets import load_from_disk
        ds = load_from_disk(str(domain_path))
        
        train_data = ds['train'] if 'train' in ds else ds
        
        category_counts = defaultdict(int)
        total_domains = 0
        
        for row in train_data:
            domain = row.get('domain', '')
            classes = row.get('classes', '')
            
            if domain:
                total_domains += 1
                try:
                    if isinstance(classes, str):
                        import ast
                        class_list = ast.literal_eval(classes) if classes else []
                    else:
                        class_list = classes or []
                    
                    for cls in class_list[:3]:
                        category_counts[str(cls)] += 1
                except:
                    pass
        
        # Map to mindsets
        category_to_mindset = {
            "Shopping": "transactional",
            "News": "informed",
            "Arts": "creative",
            "Business": "professional",
            "Health": "wellness",
            "Sports": "entertainment",
            "Science": "learning",
            "Computers": "tech",
            "Recreation": "entertainment",
            "Reference": "learning",
        }
        
        result = {
            "source": "domain_mapping",
            "total_domains": total_domains,
            "unique_categories": len(category_counts),
            "top_categories": dict(sorted(category_counts.items(), key=lambda x: x[1], reverse=True)[:20]),
            "category_to_mindset_mapping": category_to_mindset,
            "context_effectiveness_multipliers": {
                "ecommerce": {"scarcity": 1.2, "social_proof": 1.15, "reciprocity": 1.1},
                "finance": {"authority": 1.3, "commitment": 1.2, "social_proof": 0.9},
                "health": {"authority": 1.25, "social_proof": 1.1, "unity": 1.05},
                "technology": {"authority": 1.2, "scarcity": 1.15, "social_proof": 1.1},
                "entertainment": {"liking": 1.3, "social_proof": 1.2, "reciprocity": 1.1},
            }
        }
        
        logger.info(f"  {total_domains:,} domains, {len(category_counts)} categories")
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing domain mapping: {e}")
        return {}


# =============================================================================
# MAIN
# =============================================================================

def process_all(output_dir: Path) -> Dict[str, Any]:
    """Process all datasets and merge results."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = {}
    
    # Process each dataset
    results["criteo_uplift"] = process_criteo_uplift(output_dir)
    results["criteo_attribution"] = process_criteo_attribution(output_dir)
    results["yelp_reviews"] = process_yelp_reviews(output_dir)
    results["amazon_polarity"] = process_amazon_polarity(output_dir)
    results["imdb_reviews"] = process_imdb_reviews(output_dir)
    results["domain_mapping"] = process_domain_mapping(output_dir)
    
    # Compute global statistics
    total_records = sum(
        r.get("sample_size", 0) for r in results.values() if isinstance(r, dict)
    )
    
    # Merge motivation distributions
    global_motivation = defaultdict(float)
    motivation_sources = 0
    
    for source, data in results.items():
        if isinstance(data, dict) and "motivation_distribution" in data:
            sample_size = data.get("sample_size", 1)
            for mot, ratio in data["motivation_distribution"].items():
                global_motivation[mot] += ratio * sample_size
            motivation_sources += sample_size
    
    if motivation_sources > 0:
        global_motivation = {k: round(v / motivation_sources, 4) for k, v in global_motivation.items()}
    
    # Create merged output
    merged = {
        "version": "3.0",
        "total_records_processed": total_records,
        "sources": list(results.keys()),
        "global_motivation_distribution": dict(global_motivation),
        "data": results,
        "persuadability_priors": results.get("criteo_uplift", {}).get("persuadability_calibrations", {}),
        "attribution_priors": results.get("criteo_attribution", {}).get("attribution_insights", {}),
        "context_priors": results.get("domain_mapping", {}).get("context_effectiveness_multipliers", {}),
    }
    
    # Save individual results
    for source, data in results.items():
        if data:
            filepath = output_dir / f"{source}_priors.json"
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
    
    # Save merged result
    merged_path = output_dir / "all_datasets_priors.json"
    with open(merged_path, 'w') as f:
        json.dump(merged, f, indent=2)
    
    logger.info(f"\n{'='*60}")
    logger.info("PROCESSING COMPLETE")
    logger.info(f"{'='*60}")
    logger.info(f"Total records: {total_records:,}")
    logger.info(f"Sources: {len(results)}")
    logger.info(f"Output: {output_dir}")
    
    return merged


def main():
    parser = argparse.ArgumentParser(description="Process all datasets")
    parser.add_argument("--all", action="store_true", help="Process all datasets")
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    
    if args.all:
        process_all(output_dir)
    else:
        print("Use --all to process all datasets")


if __name__ == "__main__":
    main()
