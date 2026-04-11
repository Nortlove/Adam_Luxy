#!/usr/bin/env python3
"""
HIGH-PERFORMANCE PARALLEL AMAZON PROCESSOR
============================================

Multiprocessing pipeline to extract MAXIMUM psychological intelligence
from the full Amazon 2015 dataset at maximum speed.

Uses:
- Multiprocessing for parallel category processing
- Chunked file reading for memory efficiency  
- Optimized regex patterns (pre-compiled)
- Streaming aggregation for statistics

Run:
    python parallel_amazon_processor.py --workers 8 --full
    python parallel_amazon_processor.py --workers 4 --sample 100000
"""

import argparse
import csv
import json
import logging
import os
import re
import sys
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Fix for large CSV fields
csv.field_size_limit(sys.maxsize)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(processName)s] %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# =============================================================================
# PSYCHOLOGICAL PATTERN EXTRACTION (optimized)
# =============================================================================

# Pre-compile all patterns once
MOTIVATION_PATTERNS_COMPILED = {
    "functional_need": re.compile(r'\bneed(?:ed|s)?\b|\brequired?\b|\bnecessary\b|\bfor\s+work\b', re.I),
    "quality_seeking": re.compile(r'\bbest\s+quality\b|\bpremium\b|\bwell[\s-]?made\b|\bdurable\b|\bexcellent\s+(?:quality|build)\b', re.I),
    "value_seeking": re.compile(r'\bgreat\s+(?:deal|value|price)\b|\bbargain\b|\baffordable\b|\bworths?\s+(?:the|every)\b', re.I),
    "status_signaling": re.compile(r'\bimpress\b|\bluxury\b|\bprestige\b|\bcompliments?\b|\bshow\s+off\b', re.I),
    "self_reward": re.compile(r'\btreat\s+(?:my)?self\b|\bdeserve\b|\bindulge\b|\bsplurge\b', re.I),
    "gift_giving": re.compile(r'\bgift\b|\bfor\s+(?:my\s+)?(?:wife|husband|mom|dad|son|daughter)\b|\bbirthday\b|\bchristmas\b', re.I),
    "replacement": re.compile(r'\b(?:old|previous)\s+one\b|\breplacement\b|\bbroke\b|\bwore\s+out\b|\bdied\b', re.I),
    "upgrade": re.compile(r'\bupgrade\b|\bbetter\s+than\s+(?:my\s+)?(?:old|previous)\b|\bimprovement\b', re.I),
    "impulse": re.compile(r'\bimpulse\b|\bcouldn\'t\s+resist\b|\bjust\s+had\s+to\b|\bspur\s+of\b', re.I),
    "research_driven": re.compile(r'\bresearch(?:ed)?\b|\bcompared?\b|\bread\s+(?:all|many)\s+reviews\b|\bstudied\b', re.I),
    "recommendation": re.compile(r'\brecommend(?:ed|ation)?\b|\bwas\s+told\b|\bheard\s+good\b|\bfriend\s+suggested\b', re.I),
    "brand_loyalty": re.compile(r'\balways\s+(?:buy|use)\b|\bloyal\b|\btrust\s+(?:this\s+)?brand\b|\bbrand\s+fan\b', re.I),
    "social_proof": re.compile(r'\beveryone\b|\bpopular\b|\btrending\b|\ball\s+my\s+friends\b|\bfamous\b', re.I),
    "curiosity": re.compile(r'\bwanted\s+to\s+try\b|\bcurious\b|\bsee\s+what\b|\bexperiment\b', re.I),
    "problem_solving": re.compile(r'\bsolve[sd]?\b|\bfix(?:ed|es)?\b|\bhelp(?:ed|s)?\s+with\b|\bissue\b', re.I),
}

DECISION_PATTERNS_COMPILED = {
    "fast": re.compile(r'\bquickly\b|\bimmediately\b|\bon\s+a\s+whim\b|\bspur\s+of\b|\binstant\b', re.I),
    "deliberate": re.compile(r'\bresearch(?:ed)?\b|\bcompared?\b|\bweighed\b|\bstudied\b|\bcareful\b', re.I),
}

EMOTIONAL_PATTERNS_COMPILED = {
    "high_positive": re.compile(r'\b(?:amazing|incredible|perfect|wonderful|fantastic|love|obsessed)\b', re.I),
    "high_negative": re.compile(r'\b(?:terrible|horrible|awful|hate|disgusting|worst)\b', re.I),
    "low": re.compile(r'\b(?:adequate|acceptable|sufficient|okay|fine|decent)\b', re.I),
}

ARCHETYPE_PATTERNS_COMPILED = {
    "explorer": re.compile(r'\b(?:adventure|discover|explore|new|try|experience)\b', re.I),
    "achiever": re.compile(r'\b(?:success|accomplish|goal|results|performance|win)\b', re.I),
    "connector": re.compile(r'\b(?:family|friends|share|together|community|gathering)\b', re.I),
    "guardian": re.compile(r'\b(?:protect|safe|secure|reliable|trust|depend)\b', re.I),
    "analyst": re.compile(r'\b(?:research|compare|data|specs|technical|detail)\b', re.I),
    "creator": re.compile(r'\b(?:create|design|customize|unique|express|make)\b', re.I),
    "nurturer": re.compile(r'\b(?:care|help|support|kind|gentle|nurture)\b', re.I),
    "pragmatist": re.compile(r'\b(?:practical|functional|works|does\s+the\s+job|utility)\b', re.I),
}

MECHANISM_PATTERNS_COMPILED = {
    "authority": re.compile(r'\b(?:expert|professional|certified|official|endorsed|doctor|specialist)\b', re.I),
    "social_proof": re.compile(r'\b(?:everyone|popular|reviews|recommended|rated|bestseller)\b', re.I),
    "scarcity": re.compile(r'\b(?:limited|exclusive|rare|sold\s+out|hurry|last\s+one)\b', re.I),
    "reciprocity": re.compile(r'\b(?:free|gift|bonus|included|extra|complimentary)\b', re.I),
    "commitment": re.compile(r'\b(?:committed|invested|continued|loyal|repeat)\b', re.I),
    "liking": re.compile(r'\b(?:friendly|nice|pleasant|enjoyable|fun|love)\b', re.I),
    "unity": re.compile(r'\b(?:we|us|our|together|community|family)\b', re.I),
}


def extract_profile_fast(text: str) -> Dict[str, Any]:
    """
    Fast profile extraction using pre-compiled patterns.
    Returns dict instead of dataclass for better multiprocessing.
    """
    if not text or len(text) < 20:
        return None
    
    text_lower = text.lower()
    
    # Motivation detection
    motivation_scores = {}
    for motivation, pattern in MOTIVATION_PATTERNS_COMPILED.items():
        matches = len(pattern.findall(text_lower))
        if matches > 0:
            motivation_scores[motivation] = matches
    
    if motivation_scores:
        best_motivation = max(motivation_scores.keys(), key=lambda k: motivation_scores[k])
    else:
        best_motivation = "functional_need"
    
    # Decision style
    fast_count = len(DECISION_PATTERNS_COMPILED["fast"].findall(text_lower))
    deliberate_count = len(DECISION_PATTERNS_COMPILED["deliberate"].findall(text_lower))
    
    if deliberate_count > fast_count:
        decision_style = "deliberate"
    elif fast_count > deliberate_count:
        decision_style = "fast"
    else:
        decision_style = "moderate"
    
    # Emotional intensity
    high_pos = len(EMOTIONAL_PATTERNS_COMPILED["high_positive"].findall(text_lower))
    high_neg = len(EMOTIONAL_PATTERNS_COMPILED["high_negative"].findall(text_lower))
    low = len(EMOTIONAL_PATTERNS_COMPILED["low"].findall(text_lower))
    exclamations = text.count('!')
    
    if high_pos + high_neg > low or exclamations >= 2:
        emotional_intensity = "high"
    elif low > high_pos + high_neg:
        emotional_intensity = "low"
    else:
        emotional_intensity = "moderate"
    
    # Archetype
    archetype_scores = {}
    for archetype, pattern in ARCHETYPE_PATTERNS_COMPILED.items():
        matches = len(pattern.findall(text_lower))
        if matches > 0:
            archetype_scores[archetype] = matches
    
    if archetype_scores:
        best_archetype = max(archetype_scores.keys(), key=lambda k: archetype_scores[k])
    else:
        best_archetype = "pragmatist"
    
    # Mechanism receptivity
    mechanism_receptivity = {}
    for mechanism, pattern in MECHANISM_PATTERNS_COMPILED.items():
        matches = len(pattern.findall(text_lower))
        mechanism_receptivity[mechanism] = min(matches / 2, 1.0)
    
    # Calculate persuadability
    persuadability_base = {
        "impulse": 0.85, "social_proof": 0.80, "status_signaling": 0.75,
        "self_reward": 0.70, "gift_giving": 0.65, "research_driven": 0.25,
        "brand_loyalty": 0.30, "functional_need": 0.40, "quality_seeking": 0.35,
    }
    persuadability = persuadability_base.get(best_motivation, 0.5)
    
    if decision_style == "fast":
        persuadability += 0.15
    elif decision_style == "deliberate":
        persuadability -= 0.15
    
    persuadability = max(0.1, min(0.95, persuadability))
    
    return {
        "motivation": best_motivation,
        "decision_style": decision_style,
        "emotional_intensity": emotional_intensity,
        "archetype": best_archetype,
        "mechanism_receptivity": mechanism_receptivity,
        "persuadability": persuadability,
        "word_count": len(text.split()),
    }


@dataclass
class CategoryStats:
    """Aggregated statistics for a category."""
    category: str
    review_count: int = 0
    total_word_count: int = 0
    total_rating: float = 0.0
    verified_count: int = 0
    
    motivation_counts: Dict[str, int] = field(default_factory=Counter)
    decision_counts: Dict[str, int] = field(default_factory=Counter)
    emotional_counts: Dict[str, int] = field(default_factory=Counter)
    archetype_counts: Dict[str, int] = field(default_factory=Counter)
    mechanism_totals: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    persuadability_total: float = 0.0
    
    def add_profile(self, profile: Dict, rating: float, verified: bool):
        """Add a profile to aggregated stats."""
        self.review_count += 1
        self.total_word_count += profile["word_count"]
        self.total_rating += rating
        if verified:
            self.verified_count += 1
        
        self.motivation_counts[profile["motivation"]] += 1
        self.decision_counts[profile["decision_style"]] += 1
        self.emotional_counts[profile["emotional_intensity"]] += 1
        self.archetype_counts[profile["archetype"]] += 1
        
        for mech, score in profile["mechanism_receptivity"].items():
            self.mechanism_totals[mech] += score
        
        self.persuadability_total += profile["persuadability"]
    
    def to_dict(self) -> Dict:
        """Convert to exportable dictionary."""
        n = max(self.review_count, 1)
        
        return {
            "category": self.category,
            "year": 2015,
            "review_count": self.review_count,
            "avg_word_count": round(self.total_word_count / n, 1),
            "avg_rating": round(self.total_rating / n, 2),
            "verified_ratio": round(self.verified_count / n, 3),
            
            "top_motivation": max(self.motivation_counts.keys(), key=lambda k: self.motivation_counts[k]) if self.motivation_counts else "unknown",
            "motivation_distribution": {k: round(v / n, 4) for k, v in self.motivation_counts.items()},
            
            "decision_style_distribution": {k: round(v / n, 4) for k, v in self.decision_counts.items()},
            "emotional_intensity_distribution": {k: round(v / n, 4) for k, v in self.emotional_counts.items()},
            "archetype_distribution": {k: round(v / n, 4) for k, v in self.archetype_counts.items()},
            
            "mechanism_receptivity": {k: round(v / n, 4) for k, v in self.mechanism_totals.items()},
            "avg_persuadability": round(self.persuadability_total / n, 4),
        }


def process_category_file(args: Tuple[Path, Optional[int]]) -> Dict:
    """
    Process a single category TSV file.
    Designed for multiprocessing - takes tuple of (filepath, sample_size).
    """
    filepath, sample_size = args
    
    # Extract category from filename
    parts = filepath.stem.split('_')
    category = parts[3] if len(parts) >= 4 else filepath.stem
    
    logger.info(f"Processing {category} ({filepath.name})...")
    
    stats = CategoryStats(category=category)
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f, delimiter='\t')
            
            processed = 0
            for row in reader:
                if sample_size and processed >= sample_size:
                    break
                
                review_text = row.get('review_body', '')
                if not review_text or len(review_text) < 20:
                    continue
                
                profile = extract_profile_fast(review_text)
                if profile is None:
                    continue
                
                try:
                    rating = float(row.get('star_rating', 0) or 0)
                except:
                    rating = 0.0
                
                verified = row.get('verified_purchase', '').upper() == 'Y'
                
                stats.add_profile(profile, rating, verified)
                processed += 1
                
                if processed % 100000 == 0:
                    logger.info(f"  {category}: {processed:,} reviews processed")
        
        result = stats.to_dict()
        logger.info(f"  {category}: DONE - {stats.review_count:,} reviews, "
                   f"top motivation: {result['top_motivation']}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing {filepath}: {e}")
        return {"category": category, "error": str(e)}


def process_all_categories_parallel(
    data_dir: Path,
    output_dir: Path,
    workers: int = 4,
    sample_size: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Process all Amazon 2015 categories in parallel.
    """
    tsv_files = sorted(data_dir.glob("amazon_reviews_us_*.tsv"))
    
    logger.info(f"Found {len(tsv_files)} TSV files to process")
    logger.info(f"Using {workers} parallel workers")
    
    if sample_size:
        logger.info(f"Sample size: {sample_size:,} per category")
    else:
        logger.info("Processing FULL dataset (no sampling)")
    
    # Prepare arguments for multiprocessing
    task_args = [(f, sample_size) for f in tsv_files]
    
    results = {}
    
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process_category_file, args): args[0] for args in task_args}
        
        for future in as_completed(futures):
            filepath = futures[future]
            try:
                result = future.result()
                category = result.get("category", filepath.stem)
                results[category] = result
            except Exception as e:
                logger.error(f"Failed to process {filepath}: {e}")
    
    # Compute global aggregates
    total_reviews = sum(r.get("review_count", 0) for r in results.values() if "error" not in r)
    
    global_motivation = defaultdict(float)
    global_decision = defaultdict(float)
    global_mechanism = defaultdict(float)
    
    for cat_stats in results.values():
        if "error" in cat_stats:
            continue
        
        n = cat_stats.get("review_count", 0)
        
        for mot, ratio in cat_stats.get("motivation_distribution", {}).items():
            global_motivation[mot] += ratio * n
        
        for dec, ratio in cat_stats.get("decision_style_distribution", {}).items():
            global_decision[dec] += ratio * n
        
        for mech, score in cat_stats.get("mechanism_receptivity", {}).items():
            global_mechanism[mech] += score * n
    
    output = {
        "source": "Amazon Review 2015",
        "year": 2015,
        "processed_with": f"{workers} parallel workers",
        "sample_size_per_category": sample_size or "full",
        "total_categories": len([r for r in results.values() if "error" not in r]),
        "total_reviews": total_reviews,
        "category_baselines": results,
        "global_motivation_distribution": {k: round(v / total_reviews, 4) for k, v in global_motivation.items()},
        "global_decision_style_distribution": {k: round(v / total_reviews, 4) for k, v in global_decision.items()},
        "global_mechanism_receptivity": {k: round(v / total_reviews, 4) for k, v in global_mechanism.items()},
    }
    
    # Save output
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "amazon2015_full_priors.json"
    
    with open(output_file, 'w') as f:
        json.dump(output, f, indent=2)
    
    logger.info(f"\nSaved results to {output_file}")
    
    return output


def main():
    parser = argparse.ArgumentParser(description="Parallel Amazon 2015 Processor")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers")
    parser.add_argument("--sample", type=int, help="Sample size per category (omit for full)")
    parser.add_argument("--full", action="store_true", help="Process full dataset (no sampling)")
    parser.add_argument("--data-dir", default="/Volumes/Sped/new_reviews_and_data/Amazon Review 2015")
    parser.add_argument("--output-dir", default="/Volumes/Sped/new_reviews_and_data/processed_priors")
    
    args = parser.parse_args()
    
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    
    if not data_dir.exists():
        logger.error(f"Data directory not found: {data_dir}")
        sys.exit(1)
    
    sample_size = None if args.full else args.sample
    
    print("\n" + "=" * 60)
    print("PARALLEL AMAZON 2015 PROCESSOR")
    print("=" * 60)
    print(f"Workers: {args.workers}")
    print(f"Sample: {'FULL' if sample_size is None else f'{sample_size:,} per category'}")
    print("=" * 60 + "\n")
    
    results = process_all_categories_parallel(
        data_dir=data_dir,
        output_dir=output_dir,
        workers=args.workers,
        sample_size=sample_size,
    )
    
    # Print summary
    print("\n" + "=" * 60)
    print("PROCESSING COMPLETE")
    print("=" * 60)
    print(f"Total categories: {results['total_categories']}")
    print(f"Total reviews: {results['total_reviews']:,}")
    print("\nTop 5 global motivations:")
    for mot, ratio in sorted(
        results['global_motivation_distribution'].items(),
        key=lambda x: x[1],
        reverse=True
    )[:5]:
        print(f"  {mot}: {ratio:.1%}")
    print("=" * 60)


if __name__ == "__main__":
    main()
