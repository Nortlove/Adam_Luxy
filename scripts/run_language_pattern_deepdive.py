#!/usr/bin/env python3
# =============================================================================
# ADAM Platform - Language Pattern Deep Dive
# Location: scripts/run_language_pattern_deepdive.py
# =============================================================================

"""
LANGUAGE PATTERN DEEP DIVE

Extracts ACTUAL PHRASES and LANGUAGE PATTERNS used by each archetype.
This is the most impactful analysis for personalized ad copy generation.

ANALYSES:
1. N-GRAM EXTRACTION - Most common 2-3 word phrases by archetype
2. OPENING PHRASES - How each archetype starts their reviews
3. CLOSING PHRASES - How each archetype concludes
4. TRANSITION LANGUAGE - Phrases used when switching sentiment
5. INTENSIFIER PATTERNS - Words used to amplify/diminish
6. RECOMMENDATION LANGUAGE - How they recommend or warn
7. COMPARISON LANGUAGE - How they compare/contrast

OUTPUT: Actual phrase templates for ad copy personalization
"""

import json
import logging
import sys
import re
from collections import defaultdict, Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

import numpy as np

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# =============================================================================
# PATHS
# =============================================================================

LEARNING_DATA_DIR = project_root / "data" / "learning"
LEARNING_DATA_DIR.mkdir(parents=True, exist_ok=True)

YELP_DIR = project_root / "review_todo" / "yelp_reviews"

LANGUAGE_PATTERNS_PATH = LEARNING_DATA_DIR / "language_patterns.json"
MERGED_PRIORS_PATH = LEARNING_DATA_DIR / "complete_coldstart_priors.json"


# =============================================================================
# STOP WORDS TO FILTER
# =============================================================================

STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
    "be", "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "can", "need", "dare", "ought",
    "used", "it", "its", "this", "that", "these", "those", "i", "you", "he",
    "she", "we", "they", "me", "him", "her", "us", "them", "my", "your",
    "his", "our", "their", "mine", "yours", "hers", "ours", "theirs",
    "what", "which", "who", "whom", "whose", "where", "when", "why", "how",
    "all", "each", "every", "both", "few", "more", "most", "other", "some",
    "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too",
    "very", "just", "also", "now", "here", "there", "then", "once", "if",
}

# =============================================================================
# ARCHETYPE CLASSIFIER
# =============================================================================

class QuickArchetypeClassifier:
    """Quick classifier for high-throughput processing."""
    
    PROMOTION_WORDS = {"love", "amazing", "best", "excellent", "perfect", "great", "awesome"}
    PREVENTION_WORDS = {"safe", "reliable", "trust", "quality", "careful", "clean", "consistent"}
    ANALYTICAL_WORDS = {"however", "although", "compared", "specifically", "detailed"}
    SOCIAL_WORDS = {"recommend", "friends", "family", "everyone", "together", "we"}
    EXPLORER_WORDS = {"discovered", "new", "different", "unique", "tried", "first", "hidden"}
    
    def classify(self, text: str, rating: float) -> str:
        """Quick classification."""
        text_lower = text.lower() if text else ""
        words = set(re.findall(r'\b\w+\b', text_lower))
        word_count = len(text_lower.split())
        
        scores = {
            "Connector": 0.25 + 0.15 * len(words & self.SOCIAL_WORDS),
            "Achiever": 0.20 + 0.1 * len(words & self.PROMOTION_WORDS),
            "Explorer": 0.20 + 0.15 * len(words & self.EXPLORER_WORDS),
            "Guardian": 0.20 + 0.15 * len(words & self.PREVENTION_WORDS),
            "Analyzer": 0.10 + 0.15 * len(words & self.ANALYTICAL_WORDS),
        }
        
        if rating >= 4.5:
            scores["Connector"] += 0.05
        elif rating <= 2:
            scores["Analyzer"] += 0.15
        
        if word_count > 200:
            scores["Analyzer"] += 0.15
        elif word_count < 30:
            scores["Achiever"] += 0.1
        
        return max(scores, key=scores.get)


# =============================================================================
# LANGUAGE PATTERN AGGREGATOR
# =============================================================================

@dataclass
class LanguagePatternAggregator:
    """Aggregates language patterns by archetype."""
    
    # Bigrams (2-word phrases)
    archetype_bigrams: Dict[str, Counter] = field(
        default_factory=lambda: defaultdict(Counter))
    
    # Trigrams (3-word phrases)
    archetype_trigrams: Dict[str, Counter] = field(
        default_factory=lambda: defaultdict(Counter))
    
    # Opening phrases (first 5 words)
    archetype_openings: Dict[str, Counter] = field(
        default_factory=lambda: defaultdict(Counter))
    
    # Closing phrases (last 5 words)
    archetype_closings: Dict[str, Counter] = field(
        default_factory=lambda: defaultdict(Counter))
    
    # Recommendation phrases
    archetype_recommendations: Dict[str, Counter] = field(
        default_factory=lambda: defaultdict(Counter))
    
    # Warning phrases
    archetype_warnings: Dict[str, Counter] = field(
        default_factory=lambda: defaultdict(Counter))
    
    # Intensifiers
    archetype_intensifiers: Dict[str, Counter] = field(
        default_factory=lambda: defaultdict(Counter))
    
    # Diminishers
    archetype_diminishers: Dict[str, Counter] = field(
        default_factory=lambda: defaultdict(Counter))
    
    # Transition phrases
    archetype_transitions: Dict[str, Counter] = field(
        default_factory=lambda: defaultdict(Counter))
    
    # Comparison phrases
    archetype_comparisons: Dict[str, Counter] = field(
        default_factory=lambda: defaultdict(Counter))
    
    # Emotional expressions
    archetype_emotions: Dict[str, Counter] = field(
        default_factory=lambda: defaultdict(Counter))
    
    total_reviews: int = 0
    
    def add_review(self, archetype: str, text: str, rating: float):
        """Extract and add language patterns from a review."""
        
        self.total_reviews += 1
        
        if not text or len(text) < 20:
            return
        
        text_lower = text.lower()
        words = re.findall(r'\b[a-z]+\b', text_lower)
        sentences = re.split(r'[.!?]+', text)
        
        # Filter stop words for n-grams
        content_words = [w for w in words if w not in STOP_WORDS and len(w) > 2]
        
        # Extract bigrams
        for i in range(len(content_words) - 1):
            bigram = f"{content_words[i]} {content_words[i+1]}"
            self.archetype_bigrams[archetype][bigram] += 1
        
        # Extract trigrams
        for i in range(len(content_words) - 2):
            trigram = f"{content_words[i]} {content_words[i+1]} {content_words[i+2]}"
            self.archetype_trigrams[archetype][trigram] += 1
        
        # Opening phrases (first sentence, up to 6 words)
        if sentences:
            first_sentence = sentences[0].strip()
            first_words = first_sentence.split()[:6]
            if len(first_words) >= 3:
                opening = " ".join(first_words).lower()
                self.archetype_openings[archetype][opening] += 1
        
        # Closing phrases (last sentence, up to 6 words)
        non_empty_sentences = [s.strip() for s in sentences if s.strip()]
        if non_empty_sentences:
            last_sentence = non_empty_sentences[-1]
            last_words = last_sentence.split()[-6:]
            if len(last_words) >= 3:
                closing = " ".join(last_words).lower()
                self.archetype_closings[archetype][closing] += 1
        
        # Recommendation phrases
        rec_patterns = [
            r"(i recommend\b[^.!?]{0,30})",
            r"(highly recommend\b[^.!?]{0,30})",
            r"(definitely try\b[^.!?]{0,30})",
            r"(must try\b[^.!?]{0,30})",
            r"(you should\b[^.!?]{0,30})",
            r"(you have to\b[^.!?]{0,30})",
            r"(i\'d suggest\b[^.!?]{0,30})",
        ]
        for pattern in rec_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                self.archetype_recommendations[archetype][match.strip()] += 1
        
        # Warning phrases
        warn_patterns = [
            r"(don\'t go\b[^.!?]{0,30})",
            r"(avoid\b[^.!?]{0,30})",
            r"(never again\b[^.!?]{0,30})",
            r"(stay away\b[^.!?]{0,30})",
            r"(would not recommend\b[^.!?]{0,30})",
            r"(beware\b[^.!?]{0,30})",
            r"(be warned\b[^.!?]{0,30})",
        ]
        for pattern in warn_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                self.archetype_warnings[archetype][match.strip()] += 1
        
        # Intensifiers
        intensifier_patterns = [
            r"(absolutely\s+\w+)",
            r"(definitely\s+\w+)",
            r"(extremely\s+\w+)",
            r"(incredibly\s+\w+)",
            r"(totally\s+\w+)",
            r"(completely\s+\w+)",
            r"(truly\s+\w+)",
            r"(really\s+\w+)",
            r"(so\s+\w+)",
            r"(very\s+\w+)",
        ]
        for pattern in intensifier_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                self.archetype_intensifiers[archetype][match] += 1
        
        # Diminishers
        diminisher_patterns = [
            r"(a bit\s+\w+)",
            r"(a little\s+\w+)",
            r"(somewhat\s+\w+)",
            r"(slightly\s+\w+)",
            r"(kind of\s+\w+)",
            r"(sort of\s+\w+)",
            r"(fairly\s+\w+)",
            r"(rather\s+\w+)",
        ]
        for pattern in diminisher_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                self.archetype_diminishers[archetype][match] += 1
        
        # Transition phrases
        transition_patterns = [
            r"(but\s+[^.!?]{0,25})",
            r"(however\s+[^.!?]{0,25})",
            r"(although\s+[^.!?]{0,25})",
            r"(on the other hand\s+[^.!?]{0,25})",
            r"(that said\s+[^.!?]{0,25})",
            r"(nevertheless\s+[^.!?]{0,25})",
        ]
        for pattern in transition_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                self.archetype_transitions[archetype][match.strip()] += 1
        
        # Comparison phrases
        comparison_patterns = [
            r"(better than\s+[^.!?]{0,20})",
            r"(worse than\s+[^.!?]{0,20})",
            r"(compared to\s+[^.!?]{0,20})",
            r"(unlike\s+[^.!?]{0,20})",
            r"(similar to\s+[^.!?]{0,20})",
            r"(as good as\s+[^.!?]{0,20})",
            r"(not as\s+[^.!?]{0,20})",
        ]
        for pattern in comparison_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                self.archetype_comparisons[archetype][match.strip()] += 1
        
        # Emotional expressions
        emotion_patterns = [
            r"(i love\b[^.!?]{0,20})",
            r"(i hate\b[^.!?]{0,20})",
            r"(so happy\b[^.!?]{0,20})",
            r"(disappointed\b[^.!?]{0,20})",
            r"(excited\b[^.!?]{0,20})",
            r"(frustrated\b[^.!?]{0,20})",
            r"(impressed\b[^.!?]{0,20})",
            r"(surprised\b[^.!?]{0,20})",
            r"(delighted\b[^.!?]{0,20})",
        ]
        for pattern in emotion_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                self.archetype_emotions[archetype][match.strip()] += 1


# =============================================================================
# GENERATE LANGUAGE PRIORS
# =============================================================================

def generate_language_priors(aggregator: LanguagePatternAggregator) -> Dict[str, Any]:
    """Generate language pattern priors."""
    
    priors = {}
    
    # =========================================================================
    # 1. TOP BIGRAMS BY ARCHETYPE
    # =========================================================================
    
    bigram_priors = {}
    for archetype, counter in aggregator.archetype_bigrams.items():
        top_bigrams = counter.most_common(50)
        bigram_priors[archetype] = [
            {"phrase": phrase, "count": count}
            for phrase, count in top_bigrams
        ]
    priors["top_bigrams_by_archetype"] = bigram_priors
    
    # =========================================================================
    # 2. TOP TRIGRAMS BY ARCHETYPE
    # =========================================================================
    
    trigram_priors = {}
    for archetype, counter in aggregator.archetype_trigrams.items():
        top_trigrams = counter.most_common(30)
        trigram_priors[archetype] = [
            {"phrase": phrase, "count": count}
            for phrase, count in top_trigrams
        ]
    priors["top_trigrams_by_archetype"] = trigram_priors
    
    # =========================================================================
    # 3. OPENING PHRASES
    # =========================================================================
    
    opening_priors = {}
    for archetype, counter in aggregator.archetype_openings.items():
        top_openings = counter.most_common(20)
        opening_priors[archetype] = [
            {"phrase": phrase, "count": count}
            for phrase, count in top_openings
        ]
    priors["opening_phrases_by_archetype"] = opening_priors
    
    # =========================================================================
    # 4. CLOSING PHRASES
    # =========================================================================
    
    closing_priors = {}
    for archetype, counter in aggregator.archetype_closings.items():
        top_closings = counter.most_common(20)
        closing_priors[archetype] = [
            {"phrase": phrase, "count": count}
            for phrase, count in top_closings
        ]
    priors["closing_phrases_by_archetype"] = closing_priors
    
    # =========================================================================
    # 5. RECOMMENDATION PHRASES
    # =========================================================================
    
    rec_priors = {}
    for archetype, counter in aggregator.archetype_recommendations.items():
        top_recs = counter.most_common(15)
        rec_priors[archetype] = [
            {"phrase": phrase, "count": count}
            for phrase, count in top_recs
        ]
    priors["recommendation_phrases_by_archetype"] = rec_priors
    
    # =========================================================================
    # 6. WARNING PHRASES
    # =========================================================================
    
    warn_priors = {}
    for archetype, counter in aggregator.archetype_warnings.items():
        top_warns = counter.most_common(15)
        warn_priors[archetype] = [
            {"phrase": phrase, "count": count}
            for phrase, count in top_warns
        ]
    priors["warning_phrases_by_archetype"] = warn_priors
    
    # =========================================================================
    # 7. INTENSIFIER PATTERNS
    # =========================================================================
    
    int_priors = {}
    for archetype, counter in aggregator.archetype_intensifiers.items():
        top_ints = counter.most_common(20)
        int_priors[archetype] = [
            {"phrase": phrase, "count": count}
            for phrase, count in top_ints
        ]
    priors["intensifier_patterns_by_archetype"] = int_priors
    
    # =========================================================================
    # 8. DIMINISHER PATTERNS
    # =========================================================================
    
    dim_priors = {}
    for archetype, counter in aggregator.archetype_diminishers.items():
        top_dims = counter.most_common(15)
        dim_priors[archetype] = [
            {"phrase": phrase, "count": count}
            for phrase, count in top_dims
        ]
    priors["diminisher_patterns_by_archetype"] = dim_priors
    
    # =========================================================================
    # 9. TRANSITION PHRASES
    # =========================================================================
    
    trans_priors = {}
    for archetype, counter in aggregator.archetype_transitions.items():
        top_trans = counter.most_common(15)
        trans_priors[archetype] = [
            {"phrase": phrase, "count": count}
            for phrase, count in top_trans
        ]
    priors["transition_phrases_by_archetype"] = trans_priors
    
    # =========================================================================
    # 10. COMPARISON PHRASES
    # =========================================================================
    
    comp_priors = {}
    for archetype, counter in aggregator.archetype_comparisons.items():
        top_comps = counter.most_common(15)
        comp_priors[archetype] = [
            {"phrase": phrase, "count": count}
            for phrase, count in top_comps
        ]
    priors["comparison_phrases_by_archetype"] = comp_priors
    
    # =========================================================================
    # 11. EMOTIONAL EXPRESSIONS
    # =========================================================================
    
    emotion_priors = {}
    for archetype, counter in aggregator.archetype_emotions.items():
        top_emotions = counter.most_common(15)
        emotion_priors[archetype] = [
            {"phrase": phrase, "count": count}
            for phrase, count in top_emotions
        ]
    priors["emotional_expressions_by_archetype"] = emotion_priors
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    priors["language_pattern_stats"] = {
        "total_reviews_analyzed": aggregator.total_reviews,
        "timestamp": datetime.now().isoformat(),
    }
    
    return priors


def merge_language_priors(language: Dict, existing_path: Path) -> Dict:
    """Merge language priors with existing."""
    if not existing_path.exists():
        return language
    
    with open(existing_path) as f:
        existing = json.load(f)
    
    merged = existing.copy()
    
    # Add all language priors
    for key, value in language.items():
        merged[key] = value
    
    return merged


# =============================================================================
# PARSE YELP
# =============================================================================

def parse_yelp_reviews(filepath: Path, sample_rate: float = 0.15, max_reviews: int = 1000000):
    """Parse Yelp reviews."""
    count = 0
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if max_reviews and count >= max_reviews:
                    break
                if sample_rate < 1.0 and np.random.random() > sample_rate:
                    continue
                try:
                    row = json.loads(line.strip())
                    yield {
                        "text": row.get("text", ""),
                        "rating": float(row.get("stars", 3)),
                    }
                    count += 1
                except:
                    continue
    except Exception as e:
        logger.warning(f"Error parsing Yelp: {e}")
    logger.info(f"  Parsed {count:,} reviews")


# =============================================================================
# MAIN
# =============================================================================

def main():
    start_time = datetime.now()
    
    print("\n" + "=" * 70)
    print("LANGUAGE PATTERN DEEP DIVE")
    print("=" * 70)
    print(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nExtracting ACTUAL PHRASES by archetype:")
    print("  • N-grams (2-3 word phrases)")
    print("  • Opening/Closing phrases")
    print("  • Recommendation/Warning language")
    print("  • Intensifiers/Diminishers")
    print("  • Transition phrases")
    print("  • Comparison language")
    print("  • Emotional expressions")
    print()
    
    aggregator = LanguagePatternAggregator()
    classifier = QuickArchetypeClassifier()
    
    # Process Yelp reviews
    logger.info("Processing Yelp reviews for language patterns...")
    review_file = YELP_DIR / "yelp_academic_dataset_review.json"
    
    if review_file.exists():
        for review in parse_yelp_reviews(review_file, sample_rate=0.15, max_reviews=1000000):
            if not review["text"]:
                continue
            
            archetype = classifier.classify(review["text"], review["rating"])
            aggregator.add_review(archetype, review["text"], review["rating"])
    
    logger.info(f"Total reviews processed: {aggregator.total_reviews:,}")
    
    # Generate priors
    logger.info("Generating language pattern priors...")
    language_priors = generate_language_priors(aggregator)
    
    # Save language priors
    with open(LANGUAGE_PATTERNS_PATH, 'w') as f:
        json.dump(language_priors, f, indent=2)
    logger.info(f"✓ Language patterns saved: {LANGUAGE_PATTERNS_PATH}")
    
    # Merge with existing
    logger.info("Merging with complete priors...")
    merged = merge_language_priors(language_priors, MERGED_PRIORS_PATH)
    
    with open(MERGED_PRIORS_PATH, 'w') as f:
        json.dump(merged, f, indent=2)
    logger.info(f"✓ Merged priors saved: {MERGED_PRIORS_PATH}")
    
    # Summary
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 70)
    print("LANGUAGE PATTERN DEEP DIVE COMPLETE")
    print("=" * 70)
    print(f"\nProcessing time: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    print(f"Reviews analyzed: {aggregator.total_reviews:,}")
    
    # Show sample insights
    print("\n" + "-" * 50)
    print("SAMPLE INSIGHTS:")
    print("-" * 50)
    
    print("\n[TOP BIGRAMS BY ARCHETYPE]")
    for archetype in ["Achiever", "Connector", "Analyzer", "Guardian", "Explorer"]:
        bigrams = language_priors.get("top_bigrams_by_archetype", {}).get(archetype, [])
        if bigrams:
            top3 = [b["phrase"] for b in bigrams[:3]]
            print(f"  {archetype}: {', '.join(top3)}")
    
    print("\n[TOP RECOMMENDATION PHRASES]")
    for archetype in ["Achiever", "Connector", "Analyzer"]:
        recs = language_priors.get("recommendation_phrases_by_archetype", {}).get(archetype, [])
        if recs:
            top2 = [r["phrase"][:40] for r in recs[:2]]
            print(f"  {archetype}: {' | '.join(top2)}")
    
    print("\n[TOP INTENSIFIERS]")
    for archetype in ["Achiever", "Connector", "Analyzer"]:
        ints = language_priors.get("intensifier_patterns_by_archetype", {}).get(archetype, [])
        if ints:
            top3 = [i["phrase"] for i in ints[:3]]
            print(f"  {archetype}: {', '.join(top3)}")
    
    print("\n[TOP EMOTIONAL EXPRESSIONS]")
    for archetype in ["Achiever", "Connector", "Analyzer"]:
        emotions = language_priors.get("emotional_expressions_by_archetype", {}).get(archetype, [])
        if emotions:
            top3 = [e["phrase"][:25] for e in emotions[:3]]
            print(f"  {archetype}: {', '.join(top3)}")
    
    print("\n✓ Language pattern deep dive complete!")
    print("\nThese patterns enable:")
    print("  • Matching ad copy phrases to archetype vocabulary")
    print("  • Using archetype-specific intensifiers")
    print("  • Crafting recommendations in archetype voice")
    print("  • Emotional resonance through familiar expressions")


if __name__ == "__main__":
    main()
