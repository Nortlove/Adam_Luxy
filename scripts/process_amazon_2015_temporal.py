#!/usr/bin/env python3
"""
AMAZON 2015 TEMPORAL DATA PROCESSOR
===================================

Processes the Amazon 2015 review dataset to establish temporal baselines
for psychological pattern analysis.

This script:
1. Loads all 26 TSV files from the Amazon Review 2015 dataset
2. Extracts psychological patterns using the 82-framework analysis
3. Computes category-level baselines for:
   - Motivation distributions
   - Decision style distributions
   - Emotional intensity metrics
   - Authenticity markers (specific details, temporal language, etc.)
   - Rating patterns
4. Exports baselines for integration with temporal_psychology.py

Usage:
    python process_amazon_2015_temporal.py --data-dir /path/to/Amazon\ Review\ 2015/
    python process_amazon_2015_temporal.py --sample 100000  # Process sample only
    python process_amazon_2015_temporal.py --category Tools  # Process single category
"""

import argparse
import json
import logging
import os
import re
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import csv

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ReviewStats:
    """Statistics for a single review."""
    review_length: int
    word_count: int
    unique_words: int
    exclamation_count: int
    question_count: int
    has_specific_details: bool
    has_temporal_language: bool
    has_comparison: bool
    has_personal_context: bool
    rating: float
    verified_purchase: bool
    helpful_votes: int
    total_votes: int


@dataclass
class CategoryBaseline:
    """Computed baseline for a product category."""
    category: str
    review_count: int
    
    # Length metrics
    avg_review_length: float
    std_review_length: float
    avg_word_count: float
    
    # Vocabulary metrics
    vocabulary_diversity: float
    
    # Emotional metrics
    emotional_intensity_mean: float
    emotional_intensity_std: float
    
    # Authenticity markers
    specific_detail_frequency: float
    temporal_language_frequency: float
    comparison_frequency: float
    personal_context_frequency: float
    
    # Rating patterns
    avg_rating: float
    rating_std: float
    rating_distribution: Dict[int, float]
    
    # Verification patterns
    verified_purchase_ratio: float
    helpful_vote_ratio: float
    
    # Motivation distribution (detected from text)
    motivation_distribution: Dict[str, float]
    
    # Decision style distribution
    decision_style_distribution: Dict[str, float]
    
    # Sentiment distribution
    sentiment_distribution: Dict[str, float]


# =============================================================================
# PATTERN DETECTION
# =============================================================================

# Patterns for detecting specific details
SPECIFIC_DETAIL_PATTERNS = [
    r"\b\d+\s*(inches?|feet|cm|mm|lbs?|kg|oz|watts?|volts?|amps?|mah)\b",
    r"\bmodel\s*#?\s*[A-Z0-9-]+\b",
    r"\bv\d+\.\d+\b",
    r"\b\d+\s*(gb|mb|tb)\b",
]

# Patterns for temporal language
TEMPORAL_PATTERNS = [
    r"\bafter\s+\d+\s*(days?|weeks?|months?|years?)\b",
    r"\bbeen\s+(using|have|had)\s+(for|this)\b",
    r"\bfor\s+\d+\s*(days?|weeks?|months?|years?)\b",
    r"\bso\s+far\b",
    r"\bover\s+time\b",
]

# Patterns for comparisons
COMPARISON_PATTERNS = [
    r"\bcompared?\s+to\b",
    r"\bbetter\s+than\b",
    r"\bworse\s+than\b",
    r"\bvs\.?\b",
    r"\bunlike\s+(my|the|other)\b",
    r"\bprevious\s+(one|model|version)\b",
]

# Patterns for personal context
PERSONAL_CONTEXT_PATTERNS = [
    r"\bfor\s+my\s+(wife|husband|son|daughter|kid|mom|dad|dog|cat)\b",
    r"\bin\s+my\s+(kitchen|garage|office|bedroom|bathroom|car)\b",
    r"\bI\s+(use|used|bought|got)\s+this\s+for\b",
    r"\bmy\s+(first|second|third)\b",
]

# Patterns for motivation detection
MOTIVATION_PATTERNS = {
    "functional_need": [
        r"\bneed(?:ed|s)?\s+(?:it|this|one)\b",
        r"\brequired\b",
        r"\bnecessary\b",
        r"\bfor\s+(work|job|school)\b",
    ],
    "quality_seeking": [
        r"\b(best|top)\s+quality\b",
        r"\bpremium\b",
        r"\bwell[\s-]?(made|built|constructed)\b",
        r"\bdurable\b",
    ],
    "value_seeking": [
        r"\bgreat\s+(deal|value|price)\b",
        r"\bbargain\b",
        r"\baffordable\b",
        r"\bbudget\b",
    ],
    "impulse": [
        r"\bimpulse\b",
        r"\bcouldn't\s+resist\b",
        r"\bjust\s+had\s+to\b",
    ],
    "replacement": [
        r"\b(old|previous)\s+one\s+(broke|died|stopped)\b",
        r"\breplacement\b",
        r"\bneed(?:ed)?\s+(?:a\s+)?new\s+one\b",
    ],
    "gift_giving": [
        r"\b(?:bought|got)\s+(?:this\s+)?(?:for|as)\s+(?:a\s+)?gift\b",
        r"\bfor\s+(?:my\s+)?(?:wife|husband|mom|dad|friend)\b",
        r"\bbirthday\b",
        r"\bchristmas\b",
    ],
    "research_driven": [
        r"\b(?:after|did)\s+(?:much|extensive)\s+research\b",
        r"\bread\s+(?:many|all)\s+(?:the\s+)?reviews\b",
        r"\bcompared\s+(?:to|with|many)\b",
    ],
    "brand_loyalty": [
        r"\balways\s+(?:buy|use|get)\s+(?:this\s+)?brand\b",
        r"\bloyal\b",
        r"\btrust\s+(?:this\s+)?brand\b",
    ],
}

# Decision style patterns
DECISION_STYLE_PATTERNS = {
    "fast": [
        r"\bquickly\b",
        r"\bimmediately\b",
        r"\bright\s+away\b",
        r"\bon\s+a\s+whim\b",
    ],
    "deliberate": [
        r"\bresearched\b",
        r"\bcompared\s+(?:many|several)\b",
        r"\bread\s+(?:many|all)\s+reviews\b",
        r"\bweighed\s+(?:my\s+)?options\b",
    ],
}


def compile_patterns(patterns: List[str]) -> List[re.Pattern]:
    """Compile regex patterns for efficiency."""
    return [re.compile(p, re.IGNORECASE) for p in patterns]


# Pre-compile all patterns
COMPILED_SPECIFIC_DETAIL = compile_patterns(SPECIFIC_DETAIL_PATTERNS)
COMPILED_TEMPORAL = compile_patterns(TEMPORAL_PATTERNS)
COMPILED_COMPARISON = compile_patterns(COMPARISON_PATTERNS)
COMPILED_PERSONAL = compile_patterns(PERSONAL_CONTEXT_PATTERNS)

COMPILED_MOTIVATION = {
    key: compile_patterns(patterns) 
    for key, patterns in MOTIVATION_PATTERNS.items()
}

COMPILED_DECISION_STYLE = {
    key: compile_patterns(patterns)
    for key, patterns in DECISION_STYLE_PATTERNS.items()
}


def analyze_review(text: str, rating: float, verified: bool, 
                   helpful_votes: int, total_votes: int) -> ReviewStats:
    """Analyze a single review and extract statistics."""
    
    # Basic metrics
    review_length = len(text)
    words = text.lower().split()
    word_count = len(words)
    unique_words = len(set(words))
    
    # Punctuation counts
    exclamation_count = text.count('!')
    question_count = text.count('?')
    
    # Pattern matching
    has_specific_details = any(p.search(text) for p in COMPILED_SPECIFIC_DETAIL)
    has_temporal_language = any(p.search(text) for p in COMPILED_TEMPORAL)
    has_comparison = any(p.search(text) for p in COMPILED_COMPARISON)
    has_personal_context = any(p.search(text) for p in COMPILED_PERSONAL)
    
    return ReviewStats(
        review_length=review_length,
        word_count=word_count,
        unique_words=unique_words,
        exclamation_count=exclamation_count,
        question_count=question_count,
        has_specific_details=has_specific_details,
        has_temporal_language=has_temporal_language,
        has_comparison=has_comparison,
        has_personal_context=has_personal_context,
        rating=rating,
        verified_purchase=verified,
        helpful_votes=helpful_votes,
        total_votes=total_votes,
    )


def detect_motivation(text: str) -> Optional[str]:
    """Detect the primary purchase motivation from review text."""
    scores = {}
    
    for motivation, patterns in COMPILED_MOTIVATION.items():
        score = sum(1 for p in patterns if p.search(text))
        if score > 0:
            scores[motivation] = score
    
    if scores:
        return max(scores.keys(), key=lambda k: scores[k])
    return None


def detect_decision_style(text: str) -> str:
    """Detect the decision style from review text."""
    fast_score = sum(1 for p in COMPILED_DECISION_STYLE["fast"] if p.search(text))
    deliberate_score = sum(1 for p in COMPILED_DECISION_STYLE["deliberate"] if p.search(text))
    
    if deliberate_score > fast_score:
        return "deliberate"
    elif fast_score > deliberate_score:
        return "fast"
    return "moderate"


def detect_sentiment(text: str, rating: float) -> str:
    """Simple sentiment detection based on rating and text."""
    if rating >= 4.0:
        return "positive"
    elif rating <= 2.0:
        return "negative"
    return "neutral"


# =============================================================================
# TSV PROCESSING
# =============================================================================

def process_tsv_file(filepath: Path, sample_size: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Process a single TSV file from the Amazon 2015 dataset.
    
    Expected columns:
    marketplace, customer_id, review_id, product_id, product_parent, 
    product_title, product_category, star_rating, helpful_votes, 
    total_votes, vine, verified_purchase, review_headline, review_body, review_date
    """
    reviews = []
    
    logger.info(f"Processing {filepath.name}...")
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f, delimiter='\t')
            
            for i, row in enumerate(reader):
                if sample_size and i >= sample_size:
                    break
                
                try:
                    # Extract fields
                    review_text = row.get('review_body', '') or ''
                    if not review_text or len(review_text) < 10:
                        continue
                    
                    rating = float(row.get('star_rating', 0) or 0)
                    verified = row.get('verified_purchase', 'N') == 'Y'
                    helpful = int(row.get('helpful_votes', 0) or 0)
                    total = int(row.get('total_votes', 0) or 0)
                    
                    # Analyze review
                    stats = analyze_review(review_text, rating, verified, helpful, total)
                    
                    # Detect psychological patterns
                    motivation = detect_motivation(review_text)
                    decision_style = detect_decision_style(review_text)
                    sentiment = detect_sentiment(review_text, rating)
                    
                    reviews.append({
                        'stats': stats,
                        'motivation': motivation,
                        'decision_style': decision_style,
                        'sentiment': sentiment,
                    })
                    
                except Exception as e:
                    logger.debug(f"Error processing row {i}: {e}")
                    continue
                
                if (i + 1) % 100000 == 0:
                    logger.info(f"  Processed {i + 1} reviews...")
    
    except Exception as e:
        logger.error(f"Error reading {filepath}: {e}")
    
    logger.info(f"  Extracted {len(reviews)} valid reviews from {filepath.name}")
    return reviews


def compute_baseline(category: str, reviews: List[Dict[str, Any]]) -> CategoryBaseline:
    """Compute baseline statistics for a category."""
    
    if not reviews:
        return None
    
    n = len(reviews)
    
    # Extract stats
    lengths = [r['stats'].review_length for r in reviews]
    word_counts = [r['stats'].word_count for r in reviews]
    unique_counts = [r['stats'].unique_words for r in reviews]
    ratings = [r['stats'].rating for r in reviews]
    exclamations = [r['stats'].exclamation_count for r in reviews]
    
    # Calculate averages
    import statistics
    
    avg_length = statistics.mean(lengths)
    std_length = statistics.stdev(lengths) if n > 1 else 0
    avg_words = statistics.mean(word_counts)
    
    # Vocabulary diversity
    vocab_diversities = [r['stats'].unique_words / max(r['stats'].word_count, 1) for r in reviews]
    vocab_diversity = statistics.mean(vocab_diversities)
    
    # Emotional intensity (based on exclamations and review length)
    emotional_intensities = [
        r['stats'].exclamation_count / max(r['stats'].word_count, 1) * 10
        for r in reviews
    ]
    emotional_mean = statistics.mean(emotional_intensities)
    emotional_std = statistics.stdev(emotional_intensities) if n > 1 else 0
    
    # Authenticity markers
    specific_freq = sum(1 for r in reviews if r['stats'].has_specific_details) / n
    temporal_freq = sum(1 for r in reviews if r['stats'].has_temporal_language) / n
    comparison_freq = sum(1 for r in reviews if r['stats'].has_comparison) / n
    personal_freq = sum(1 for r in reviews if r['stats'].has_personal_context) / n
    
    # Rating statistics
    avg_rating = statistics.mean(ratings)
    rating_std = statistics.stdev(ratings) if n > 1 else 0
    
    # Rating distribution
    rating_dist = defaultdict(int)
    for r in reviews:
        rating_dist[int(r['stats'].rating)] += 1
    rating_distribution = {k: v / n for k, v in rating_dist.items()}
    
    # Verification ratio
    verified_ratio = sum(1 for r in reviews if r['stats'].verified_purchase) / n
    
    # Helpful vote ratio
    helpful_reviews = [r for r in reviews if r['stats'].total_votes > 0]
    if helpful_reviews:
        helpful_ratio = statistics.mean([
            r['stats'].helpful_votes / r['stats'].total_votes
            for r in helpful_reviews
        ])
    else:
        helpful_ratio = 0.0
    
    # Motivation distribution
    motivation_counts = defaultdict(int)
    for r in reviews:
        if r['motivation']:
            motivation_counts[r['motivation']] += 1
    
    motivation_total = sum(motivation_counts.values())
    motivation_distribution = {
        k: v / motivation_total if motivation_total > 0 else 0
        for k, v in motivation_counts.items()
    }
    
    # Decision style distribution
    decision_counts = defaultdict(int)
    for r in reviews:
        decision_counts[r['decision_style']] += 1
    
    decision_style_distribution = {
        k: v / n for k, v in decision_counts.items()
    }
    
    # Sentiment distribution
    sentiment_counts = defaultdict(int)
    for r in reviews:
        sentiment_counts[r['sentiment']] += 1
    
    sentiment_distribution = {
        k: v / n for k, v in sentiment_counts.items()
    }
    
    return CategoryBaseline(
        category=category,
        review_count=n,
        avg_review_length=round(avg_length, 1),
        std_review_length=round(std_length, 1),
        avg_word_count=round(avg_words, 1),
        vocabulary_diversity=round(vocab_diversity, 3),
        emotional_intensity_mean=round(emotional_mean, 3),
        emotional_intensity_std=round(emotional_std, 3),
        specific_detail_frequency=round(specific_freq, 3),
        temporal_language_frequency=round(temporal_freq, 3),
        comparison_frequency=round(comparison_freq, 3),
        personal_context_frequency=round(personal_freq, 3),
        avg_rating=round(avg_rating, 2),
        rating_std=round(rating_std, 2),
        rating_distribution=rating_distribution,
        verified_purchase_ratio=round(verified_ratio, 3),
        helpful_vote_ratio=round(helpful_ratio, 3),
        motivation_distribution=motivation_distribution,
        decision_style_distribution=decision_style_distribution,
        sentiment_distribution=sentiment_distribution,
    )


# =============================================================================
# MAIN PROCESSING
# =============================================================================

def process_all_categories(
    data_dir: Path,
    output_path: Path,
    sample_size: Optional[int] = None,
    single_category: Optional[str] = None,
) -> Dict[str, CategoryBaseline]:
    """
    Process all TSV files and compute baselines.
    
    Args:
        data_dir: Directory containing TSV files
        output_path: Path to save output JSON
        sample_size: Optional sample size per file
        single_category: Optional single category to process
        
    Returns:
        Dict of category → baseline
    """
    baselines = {}
    
    # Find all TSV files
    tsv_files = list(data_dir.glob("amazon_reviews_us_*.tsv"))
    
    if not tsv_files:
        logger.error(f"No TSV files found in {data_dir}")
        return baselines
    
    logger.info(f"Found {len(tsv_files)} TSV files to process")
    
    for tsv_file in sorted(tsv_files):
        # Extract category from filename
        # Format: amazon_reviews_us_CategoryName_v1_00.tsv
        parts = tsv_file.stem.split('_')
        if len(parts) >= 4:
            category = parts[3]  # e.g., "Apparel", "Electronics"
        else:
            category = tsv_file.stem
        
        # Skip if we're only processing a single category
        if single_category and category.lower() != single_category.lower():
            continue
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Processing category: {category}")
        logger.info(f"{'='*60}")
        
        # Process file
        reviews = process_tsv_file(tsv_file, sample_size)
        
        if reviews:
            baseline = compute_baseline(category, reviews)
            if baseline:
                baselines[category] = baseline
                
                logger.info(f"\n{category} Baseline Summary:")
                logger.info(f"  Reviews: {baseline.review_count:,}")
                logger.info(f"  Avg Length: {baseline.avg_review_length:.0f} chars")
                logger.info(f"  Avg Rating: {baseline.avg_rating:.2f}")
                logger.info(f"  Verified Purchase Ratio: {baseline.verified_purchase_ratio:.0%}")
                logger.info(f"  Top Motivation: {max(baseline.motivation_distribution.items(), key=lambda x: x[1], default=('unknown', 0))[0]}")
    
    # Save results
    if baselines:
        output_data = {
            "version": "1.0",
            "source": "Amazon Review 2015 Dataset",
            "year": 2015,
            "total_categories": len(baselines),
            "baselines": {
                cat: asdict(baseline) 
                for cat, baseline in baselines.items()
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        logger.info(f"\nSaved baselines to {output_path}")
    
    return baselines


def main():
    parser = argparse.ArgumentParser(
        description="Process Amazon 2015 data for temporal baselines"
    )
    parser.add_argument(
        "--data-dir",
        default="/Volumes/Sped/new_reviews_and_data/Amazon Review 2015",
        help="Directory containing TSV files"
    )
    parser.add_argument(
        "--output",
        default="/Volumes/Sped/new_reviews_and_data/Amazon Review 2015/processed_baselines.json",
        help="Output JSON path"
    )
    parser.add_argument(
        "--sample",
        type=int,
        help="Sample size per category (for testing)"
    )
    parser.add_argument(
        "--category",
        help="Process single category only"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    
    data_dir = Path(args.data_dir)
    output_path = Path(args.output)
    
    if not data_dir.exists():
        logger.error(f"Data directory does not exist: {data_dir}")
        return 1
    
    # Process
    baselines = process_all_categories(
        data_dir=data_dir,
        output_path=output_path,
        sample_size=args.sample,
        single_category=args.category,
    )
    
    if not baselines:
        logger.error("No baselines computed")
        return 1
    
    # Summary
    print("\n" + "="*60)
    print("AMAZON 2015 TEMPORAL BASELINE SUMMARY")
    print("="*60)
    print(f"\nCategories processed: {len(baselines)}")
    print(f"Total reviews: {sum(b.review_count for b in baselines.values()):,}")
    print(f"\nOutput saved to: {output_path}")
    
    print("\nCategory Overview:")
    for cat, baseline in sorted(baselines.items(), key=lambda x: x[1].review_count, reverse=True):
        print(f"  {cat}: {baseline.review_count:,} reviews, {baseline.avg_rating:.1f}★")
    
    return 0


if __name__ == "__main__":
    exit(main())
