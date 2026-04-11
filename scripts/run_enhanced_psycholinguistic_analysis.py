#!/usr/bin/env python3
# =============================================================================
# ADAM Platform - Enhanced Psycholinguistic Analysis Pipeline
# Location: scripts/run_enhanced_psycholinguistic_analysis.py
# =============================================================================

"""
ENHANCED PSYCHOLINGUISTIC ANALYSIS PIPELINE

Extracts DEEP LINGUISTIC AND BEHAVIORAL PATTERNS for ADAM's advertising system.

ANALYSES:
1. LINGUISTIC STYLE FINGERPRINTING - How each archetype writes
2. YELP USER PROFILE ANALYSIS - Social status, expertise, influence
3. COMPLAINT VS PRAISE PATTERNS - Pain points and delight triggers
4. TEMPORAL BEHAVIOR - When archetypes engage
5. SENTIMENT INTENSITY - Emotional range and extremity
6. TRUST & LOYALTY PATTERNS - What builds/destroys trust

OUTPUT: Enhanced priors for precision ad targeting
"""

import argparse
import asyncio
import json
import logging
import sys
import csv
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
import string

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

ENHANCED_PRIORS_PATH = LEARNING_DATA_DIR / "enhanced_psycholinguistic_priors.json"
MERGED_PRIORS_PATH = LEARNING_DATA_DIR / "complete_coldstart_priors.json"

csv.field_size_limit(10 * 1024 * 1024)


# =============================================================================
# LINGUISTIC ANALYSIS LEXICONS
# =============================================================================

# Certainty markers
CERTAINTY_HIGH = {"definitely", "absolutely", "certainly", "always", "never", 
                  "completely", "totally", "100%", "guaranteed", "without doubt",
                  "undoubtedly", "clearly", "obviously", "no question"}

CERTAINTY_LOW = {"maybe", "might", "could", "perhaps", "possibly", "sometimes",
                 "occasionally", "probably", "likely", "seems", "appears",
                 "sort of", "kind of", "i think", "i guess", "not sure"}

# Hedging language
HEDGING = {"but", "however", "although", "though", "except", "unless",
           "on the other hand", "that said", "to be fair", "admittedly"}

# Superlatives
SUPERLATIVES = {"best", "worst", "greatest", "most", "least", "ultimate",
                "perfect", "horrible", "amazing", "terrible", "incredible",
                "fantastic", "awful", "outstanding", "dreadful"}

# First person markers
FIRST_PERSON = {"i", "me", "my", "mine", "we", "us", "our", "ours", "myself"}

# Third person/objective
THIRD_PERSON = {"it", "they", "the", "this", "that", "one", "people"}

# Complaint triggers by expected archetype
COMPLAINT_TRIGGERS = {
    "service_speed": {"slow", "wait", "waiting", "forever", "took forever", 
                      "long time", "delayed", "late"},
    "cleanliness": {"dirty", "filthy", "unclean", "gross", "disgusting",
                    "messy", "stained", "smell", "smelled"},
    "staff_attitude": {"rude", "unfriendly", "ignored", "dismissive", "attitude",
                       "condescending", "arrogant", "unprofessional"},
    "value_price": {"overpriced", "expensive", "ripoff", "not worth", "waste of money",
                    "too much", "pricey", "highway robbery"},
    "quality": {"poor quality", "mediocre", "subpar", "disappointing", 
                "not as expected", "underwhelming", "bland"},
    "reliability": {"inconsistent", "unreliable", "hit or miss", "varies",
                    "different every time", "not consistent"},
}

# Praise triggers
PRAISE_TRIGGERS = {
    "service_quality": {"excellent service", "great service", "attentive",
                        "helpful", "went above", "exceptional service"},
    "atmosphere": {"cozy", "ambiance", "atmosphere", "vibe", "comfortable",
                   "relaxing", "beautiful decor", "nice environment"},
    "value": {"great value", "worth every", "affordable", "reasonable",
              "good deal", "bang for buck", "fair price"},
    "quality": {"high quality", "fresh", "delicious", "amazing food",
                "best i've had", "top notch", "excellent quality"},
    "reliability": {"consistent", "always good", "never disappoints",
                    "dependable", "reliable", "every time"},
}

# Trust builders
TRUST_BUILDERS = {"honest", "transparent", "trustworthy", "reliable", "consistent",
                  "dependable", "professional", "genuine", "authentic", "integrity",
                  "stood by", "made it right", "fixed it", "resolved", "apologized"}

# Trust destroyers
TRUST_DESTROYERS = {"lied", "dishonest", "scam", "fraud", "fake", "misleading",
                    "deceived", "cheated", "ripped off", "never again", "don't trust",
                    "won't return", "avoid", "warning", "beware"}

# Loyalty indicators
LOYALTY_POSITIVE = {"regular", "always come", "come back", "return", "loyal",
                    "years", "favorite", "go-to", "recommend", "tell everyone"}

LOYALTY_NEGATIVE = {"never again", "won't return", "last time", "done with",
                    "switching", "finding another", "never coming back"}


# =============================================================================
# ARCHETYPE CLASSIFIER (Enhanced)
# =============================================================================

class EnhancedArchetypeClassifier:
    """Enhanced classifier with linguistic style extraction."""
    
    PROMOTION_WORDS = {"love", "amazing", "best", "excellent", "perfect", "great", "awesome"}
    PREVENTION_WORDS = {"safe", "reliable", "trust", "quality", "careful", "clean", "consistent"}
    ANALYTICAL_WORDS = {"however", "although", "compared", "specifically", "detailed"}
    SOCIAL_WORDS = {"recommend", "friends", "family", "everyone", "together", "we"}
    EXPLORER_WORDS = {"discovered", "new", "different", "unique", "tried", "first", "hidden gem"}
    
    def classify_enhanced(
        self,
        text: str,
        rating: float,
        useful_votes: int = 0,
        funny_votes: int = 0,
        cool_votes: int = 0,
    ) -> Dict[str, Any]:
        """Classify with full linguistic analysis."""
        text_lower = text.lower() if text else ""
        words = set(re.findall(r'\b\w+\b', text_lower))
        word_list = text_lower.split()
        word_count = len(word_list)
        
        # Base archetype weights
        base_weights = {
            "Connector": 0.25, "Achiever": 0.20, "Explorer": 0.20,
            "Guardian": 0.20, "Analyzer": 0.10, "Pragmatist": 0.05
        }
        
        # Keyword adjustments
        if len(words & self.PROMOTION_WORDS) > 0:
            base_weights["Achiever"] += 0.1
        if len(words & self.PREVENTION_WORDS) > 0:
            base_weights["Guardian"] += 0.15
        if len(words & self.ANALYTICAL_WORDS) > 0:
            base_weights["Analyzer"] += 0.15
        if len(words & self.SOCIAL_WORDS) > 0:
            base_weights["Connector"] += 0.15
        if len(words & self.EXPLORER_WORDS) > 0:
            base_weights["Explorer"] += 0.15
        
        # Rating adjustments
        if rating >= 4.5:
            base_weights["Connector"] += 0.05
        elif rating <= 2:
            base_weights["Analyzer"] += 0.1
        
        # Length adjustments
        if word_count > 200:
            base_weights["Analyzer"] += 0.1
        elif word_count < 30:
            base_weights["Pragmatist"] += 0.1
        
        # Vote adjustments
        if useful_votes > 5:
            base_weights["Analyzer"] += 0.1
        if funny_votes > 3:
            base_weights["Connector"] += 0.1
        if cool_votes > 3:
            base_weights["Achiever"] += 0.1
        
        # Normalize
        total = sum(base_weights.values())
        normalized = {k: v / total for k, v in base_weights.items()}
        archetype = max(normalized, key=normalized.get)
        confidence = normalized[archetype]
        
        # Extract linguistic style
        linguistic_style = self._extract_linguistic_style(text, text_lower, words, word_count)
        
        # Extract complaint/praise patterns
        complaint_praise = self._extract_complaint_praise(text_lower, words, rating)
        
        # Extract trust/loyalty
        trust_loyalty = self._extract_trust_loyalty(text_lower, words)
        
        return {
            "archetype": archetype,
            "confidence": confidence,
            "rating": rating,
            "linguistic_style": linguistic_style,
            "complaint_praise": complaint_praise,
            "trust_loyalty": trust_loyalty,
        }
    
    def _extract_linguistic_style(self, text: str, text_lower: str, 
                                   words: Set[str], word_count: int) -> Dict[str, Any]:
        """Extract linguistic style fingerprint."""
        
        # Certainty level
        high_certainty = len(words & CERTAINTY_HIGH)
        low_certainty = len(words & CERTAINTY_LOW)
        certainty_score = (high_certainty - low_certainty) / max(word_count / 50, 1)
        
        # Hedging frequency
        hedging_count = len(words & HEDGING)
        hedging_rate = hedging_count / max(word_count / 100, 1)
        
        # Superlative usage
        superlative_count = len(words & SUPERLATIVES)
        superlative_rate = superlative_count / max(word_count / 50, 1)
        
        # Perspective (first vs third person)
        first_person_count = len(words & FIRST_PERSON)
        third_person_count = len(words & THIRD_PERSON)
        perspective_ratio = first_person_count / max(first_person_count + third_person_count, 1)
        
        # Exclamation intensity
        exclamation_count = text.count("!")
        exclamation_rate = exclamation_count / max(word_count / 50, 1)
        
        # Question asking
        question_count = text.count("?")
        question_rate = question_count / max(word_count / 100, 1)
        
        # Caps usage (emotional intensity)
        caps_words = len([w for w in text.split() if w.isupper() and len(w) > 1])
        caps_rate = caps_words / max(word_count, 1)
        
        # Sentence complexity (avg words per sentence)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]
        avg_sentence_length = word_count / max(len(sentences), 1)
        
        # Vocabulary diversity
        unique_words = len(set(text_lower.split()))
        vocab_diversity = unique_words / max(word_count, 1)
        
        return {
            "certainty_score": round(certainty_score, 3),
            "hedging_rate": round(hedging_rate, 3),
            "superlative_rate": round(superlative_rate, 3),
            "first_person_ratio": round(perspective_ratio, 3),
            "exclamation_rate": round(exclamation_rate, 3),
            "question_rate": round(question_rate, 3),
            "caps_rate": round(caps_rate, 4),
            "avg_sentence_length": round(avg_sentence_length, 1),
            "vocab_diversity": round(vocab_diversity, 3),
            "word_count": word_count,
        }
    
    def _extract_complaint_praise(self, text_lower: str, words: Set[str], 
                                   rating: float) -> Dict[str, Any]:
        """Extract complaint and praise patterns."""
        
        complaints = {}
        for category, triggers in COMPLAINT_TRIGGERS.items():
            matches = len(words & triggers)
            phrase_matches = sum(1 for t in triggers if " " in t and t in text_lower)
            if matches + phrase_matches > 0:
                complaints[category] = matches + phrase_matches
        
        praises = {}
        for category, triggers in PRAISE_TRIGGERS.items():
            matches = len(words & triggers)
            phrase_matches = sum(1 for t in triggers if " " in t and t in text_lower)
            if matches + phrase_matches > 0:
                praises[category] = matches + phrase_matches
        
        # Determine if review is complaint-focused or praise-focused
        is_complaint = rating <= 2 or sum(complaints.values()) > sum(praises.values())
        is_praise = rating >= 4 or sum(praises.values()) > sum(complaints.values())
        
        return {
            "complaints": complaints,
            "praises": praises,
            "is_complaint_focused": is_complaint,
            "is_praise_focused": is_praise,
            "rating": rating,
        }
    
    def _extract_trust_loyalty(self, text_lower: str, words: Set[str]) -> Dict[str, Any]:
        """Extract trust and loyalty signals."""
        
        trust_build = len(words & TRUST_BUILDERS)
        trust_build += sum(1 for t in TRUST_BUILDERS if " " in t and t in text_lower)
        
        trust_destroy = len(words & TRUST_DESTROYERS)
        trust_destroy += sum(1 for t in TRUST_DESTROYERS if " " in t and t in text_lower)
        
        loyalty_pos = len(words & LOYALTY_POSITIVE)
        loyalty_pos += sum(1 for t in LOYALTY_POSITIVE if " " in t and t in text_lower)
        
        loyalty_neg = len(words & LOYALTY_NEGATIVE)
        loyalty_neg += sum(1 for t in LOYALTY_NEGATIVE if " " in t and t in text_lower)
        
        return {
            "trust_builders": trust_build,
            "trust_destroyers": trust_destroy,
            "loyalty_positive": loyalty_pos,
            "loyalty_negative": loyalty_neg,
            "trust_net": trust_build - trust_destroy,
            "loyalty_net": loyalty_pos - loyalty_neg,
        }


# =============================================================================
# ENHANCED AGGREGATOR
# =============================================================================

@dataclass
class EnhancedPsycholinguisticAggregator:
    """Aggregates enhanced psycholinguistic patterns."""
    
    # Linguistic style by archetype
    archetype_certainty: Dict[str, List[float]] = field(
        default_factory=lambda: defaultdict(list))
    archetype_hedging: Dict[str, List[float]] = field(
        default_factory=lambda: defaultdict(list))
    archetype_superlatives: Dict[str, List[float]] = field(
        default_factory=lambda: defaultdict(list))
    archetype_first_person: Dict[str, List[float]] = field(
        default_factory=lambda: defaultdict(list))
    archetype_exclamation: Dict[str, List[float]] = field(
        default_factory=lambda: defaultdict(list))
    archetype_question: Dict[str, List[float]] = field(
        default_factory=lambda: defaultdict(list))
    archetype_caps: Dict[str, List[float]] = field(
        default_factory=lambda: defaultdict(list))
    archetype_sentence_length: Dict[str, List[float]] = field(
        default_factory=lambda: defaultdict(list))
    archetype_vocab_diversity: Dict[str, List[float]] = field(
        default_factory=lambda: defaultdict(list))
    
    # Complaint patterns by archetype
    archetype_complaints: Dict[str, Dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    archetype_praises: Dict[str, Dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
    # Trust/loyalty by archetype
    archetype_trust_build: Dict[str, List[int]] = field(
        default_factory=lambda: defaultdict(list))
    archetype_trust_destroy: Dict[str, List[int]] = field(
        default_factory=lambda: defaultdict(list))
    archetype_loyalty_pos: Dict[str, List[int]] = field(
        default_factory=lambda: defaultdict(list))
    archetype_loyalty_neg: Dict[str, List[int]] = field(
        default_factory=lambda: defaultdict(list))
    
    # Rating distribution (sentiment intensity)
    archetype_ratings: Dict[str, List[float]] = field(
        default_factory=lambda: defaultdict(list))
    
    # Temporal patterns
    archetype_hour: Dict[str, Dict[int, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    archetype_day: Dict[str, Dict[int, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
    # User profile patterns (Yelp)
    archetype_review_count: Dict[str, List[int]] = field(
        default_factory=lambda: defaultdict(list))
    archetype_friend_count: Dict[str, List[int]] = field(
        default_factory=lambda: defaultdict(list))
    archetype_elite_years: Dict[str, List[int]] = field(
        default_factory=lambda: defaultdict(list))
    archetype_avg_stars: Dict[str, List[float]] = field(
        default_factory=lambda: defaultdict(list))
    archetype_compliments: Dict[str, Dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
    # Stats
    total_reviews: int = 0
    total_users: int = 0
    
    def add_review(self, archetype: str, linguistic: Dict, complaint_praise: Dict,
                   trust_loyalty: Dict, timestamp: datetime = None):
        """Add review data to aggregates."""
        
        self.total_reviews += 1
        max_samples = 100000
        
        # Linguistic style
        if len(self.archetype_certainty[archetype]) < max_samples:
            self.archetype_certainty[archetype].append(linguistic["certainty_score"])
            self.archetype_hedging[archetype].append(linguistic["hedging_rate"])
            self.archetype_superlatives[archetype].append(linguistic["superlative_rate"])
            self.archetype_first_person[archetype].append(linguistic["first_person_ratio"])
            self.archetype_exclamation[archetype].append(linguistic["exclamation_rate"])
            self.archetype_question[archetype].append(linguistic["question_rate"])
            self.archetype_caps[archetype].append(linguistic["caps_rate"])
            self.archetype_sentence_length[archetype].append(linguistic["avg_sentence_length"])
            self.archetype_vocab_diversity[archetype].append(linguistic["vocab_diversity"])
        
        # Complaints/praises
        for category, count in complaint_praise.get("complaints", {}).items():
            self.archetype_complaints[archetype][category] += count
        for category, count in complaint_praise.get("praises", {}).items():
            self.archetype_praises[archetype][category] += count
        
        # Trust/loyalty
        if len(self.archetype_trust_build[archetype]) < max_samples:
            self.archetype_trust_build[archetype].append(trust_loyalty["trust_builders"])
            self.archetype_trust_destroy[archetype].append(trust_loyalty["trust_destroyers"])
            self.archetype_loyalty_pos[archetype].append(trust_loyalty["loyalty_positive"])
            self.archetype_loyalty_neg[archetype].append(trust_loyalty["loyalty_negative"])
        
        # Rating
        if len(self.archetype_ratings[archetype]) < max_samples:
            self.archetype_ratings[archetype].append(complaint_praise["rating"])
        
        # Temporal
        if timestamp:
            self.archetype_hour[archetype][timestamp.hour] += 1
            self.archetype_day[archetype][timestamp.weekday()] += 1
    
    def add_user_profile(self, archetype: str, profile: Dict):
        """Add Yelp user profile data."""
        
        self.total_users += 1
        max_samples = 50000
        
        if len(self.archetype_review_count[archetype]) < max_samples:
            self.archetype_review_count[archetype].append(profile.get("review_count", 0))
            self.archetype_friend_count[archetype].append(profile.get("friends_count", 0))
            self.archetype_elite_years[archetype].append(profile.get("elite_years", 0))
            self.archetype_avg_stars[archetype].append(profile.get("average_stars", 3.0))
        
        # Compliments
        for comp_type in ["hot", "more", "funny", "cool", "cute", "photos", "writer"]:
            if profile.get(f"compliment_{comp_type}", 0) > 0:
                self.archetype_compliments[archetype][comp_type] += profile.get(f"compliment_{comp_type}", 0)


# =============================================================================
# PARSERS
# =============================================================================

def parse_yelp_reviews_enhanced(filepath: Path, sample_rate: float = 0.15, 
                                 max_reviews: int = 1000000):
    """Parse Yelp reviews with timestamp."""
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
                    timestamp = None
                    date_str = row.get("date", "")
                    if date_str:
                        try:
                            timestamp = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                        except:
                            pass
                    
                    yield {
                        "text": row.get("text", ""),
                        "rating": float(row.get("stars", 3)),
                        "useful": int(row.get("useful", 0)),
                        "funny": int(row.get("funny", 0)),
                        "cool": int(row.get("cool", 0)),
                        "user_id": row.get("user_id", ""),
                        "timestamp": timestamp,
                    }
                    count += 1
                except:
                    continue
    except Exception as e:
        logger.warning(f"Error parsing Yelp: {e}")
    logger.info(f"  Parsed {count:,} Yelp reviews")


def parse_yelp_users(filepath: Path, sample_rate: float = 0.2, max_users: int = 500000):
    """Parse Yelp user profiles."""
    count = 0
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if max_users and count >= max_users:
                    break
                if sample_rate < 1.0 and np.random.random() > sample_rate:
                    continue
                try:
                    row = json.loads(line.strip())
                    
                    # Count elite years
                    elite = row.get("elite", "")
                    elite_years = len(elite.split(",")) if elite and elite != "None" else 0
                    
                    # Count friends
                    friends = row.get("friends", "")
                    friends_count = len(friends.split(",")) if friends and friends != "None" else 0
                    
                    yield {
                        "user_id": row.get("user_id", ""),
                        "review_count": int(row.get("review_count", 0)),
                        "friends_count": friends_count,
                        "elite_years": elite_years,
                        "average_stars": float(row.get("average_stars", 3.0)),
                        "compliment_hot": int(row.get("compliment_hot", 0)),
                        "compliment_more": int(row.get("compliment_more", 0)),
                        "compliment_funny": int(row.get("compliment_funny", 0)),
                        "compliment_cool": int(row.get("compliment_cool", 0)),
                        "compliment_cute": int(row.get("compliment_cute", 0)),
                        "compliment_photos": int(row.get("compliment_photos", 0)),
                        "compliment_writer": int(row.get("compliment_writer", 0)),
                    }
                    count += 1
                except:
                    continue
    except Exception as e:
        logger.warning(f"Error parsing Yelp users: {e}")
    logger.info(f"  Parsed {count:,} Yelp user profiles")


# =============================================================================
# GENERATE ENHANCED PRIORS
# =============================================================================

def generate_enhanced_priors(aggregator: EnhancedPsycholinguisticAggregator) -> Dict[str, Any]:
    """Generate enhanced psycholinguistic priors."""
    
    priors = {}
    
    # =========================================================================
    # 1. LINGUISTIC STYLE FINGERPRINTS
    # =========================================================================
    
    linguistic_fingerprints = {}
    for archetype in aggregator.archetype_certainty.keys():
        certainty = aggregator.archetype_certainty[archetype]
        hedging = aggregator.archetype_hedging[archetype]
        superlatives = aggregator.archetype_superlatives[archetype]
        first_person = aggregator.archetype_first_person[archetype]
        exclamation = aggregator.archetype_exclamation[archetype]
        question = aggregator.archetype_question[archetype]
        caps = aggregator.archetype_caps[archetype]
        sentence_len = aggregator.archetype_sentence_length[archetype]
        vocab_div = aggregator.archetype_vocab_diversity[archetype]
        
        if certainty:
            linguistic_fingerprints[archetype] = {
                "certainty": {
                    "mean": round(np.mean(certainty), 4),
                    "std": round(np.std(certainty), 4),
                },
                "hedging": {
                    "mean": round(np.mean(hedging), 4),
                    "high_hedging_rate": round(len([h for h in hedging if h > 0.5]) / len(hedging), 4),
                },
                "superlatives": {
                    "mean": round(np.mean(superlatives), 4),
                    "heavy_user_rate": round(len([s for s in superlatives if s > 1]) / len(superlatives), 4),
                },
                "first_person_ratio": {
                    "mean": round(np.mean(first_person), 4),
                    "high_personal_rate": round(len([f for f in first_person if f > 0.5]) / len(first_person), 4),
                },
                "emotional_intensity": {
                    "exclamation_mean": round(np.mean(exclamation), 4),
                    "question_mean": round(np.mean(question), 4),
                    "caps_mean": round(np.mean(caps), 5),
                },
                "complexity": {
                    "avg_sentence_length": round(np.mean(sentence_len), 1),
                    "vocab_diversity_mean": round(np.mean(vocab_div), 4),
                },
                "observations": len(certainty),
            }
    
    priors["linguistic_style_fingerprints"] = linguistic_fingerprints
    
    # =========================================================================
    # 2. COMPLAINT PATTERNS BY ARCHETYPE
    # =========================================================================
    
    complaint_patterns = {}
    for archetype, complaints in aggregator.archetype_complaints.items():
        total = sum(complaints.values())
        if total > 0:
            complaint_patterns[archetype] = {
                category: {
                    "count": count,
                    "rate": round(count / total, 4),
                }
                for category, count in sorted(complaints.items(), 
                                               key=lambda x: x[1], reverse=True)
            }
    
    priors["complaint_patterns_by_archetype"] = complaint_patterns
    
    # =========================================================================
    # 3. PRAISE PATTERNS BY ARCHETYPE
    # =========================================================================
    
    praise_patterns = {}
    for archetype, praises in aggregator.archetype_praises.items():
        total = sum(praises.values())
        if total > 0:
            praise_patterns[archetype] = {
                category: {
                    "count": count,
                    "rate": round(count / total, 4),
                }
                for category, count in sorted(praises.items(), 
                                               key=lambda x: x[1], reverse=True)
            }
    
    priors["praise_patterns_by_archetype"] = praise_patterns
    
    # =========================================================================
    # 4. TRUST & LOYALTY PATTERNS
    # =========================================================================
    
    trust_loyalty_patterns = {}
    for archetype in aggregator.archetype_trust_build.keys():
        trust_build = aggregator.archetype_trust_build[archetype]
        trust_destroy = aggregator.archetype_trust_destroy[archetype]
        loyalty_pos = aggregator.archetype_loyalty_pos[archetype]
        loyalty_neg = aggregator.archetype_loyalty_neg[archetype]
        
        if trust_build:
            # Calculate rates
            total = len(trust_build)
            trust_builder_reviews = len([t for t in trust_build if t > 0])
            trust_destroyer_reviews = len([t for t in trust_destroy if t > 0])
            loyalty_pos_reviews = len([l for l in loyalty_pos if l > 0])
            loyalty_neg_reviews = len([l for l in loyalty_neg if l > 0])
            
            trust_loyalty_patterns[archetype] = {
                "trust": {
                    "mentions_trust_builders": round(trust_builder_reviews / total, 4),
                    "mentions_trust_destroyers": round(trust_destroyer_reviews / total, 4),
                    "net_trust_orientation": round((trust_builder_reviews - trust_destroyer_reviews) / total, 4),
                },
                "loyalty": {
                    "mentions_loyalty_positive": round(loyalty_pos_reviews / total, 4),
                    "mentions_loyalty_negative": round(loyalty_neg_reviews / total, 4),
                    "net_loyalty_orientation": round((loyalty_pos_reviews - loyalty_neg_reviews) / total, 4),
                },
                "observations": total,
            }
    
    priors["trust_loyalty_patterns"] = trust_loyalty_patterns
    
    # =========================================================================
    # 5. SENTIMENT INTENSITY (Rating Distribution)
    # =========================================================================
    
    sentiment_intensity = {}
    for archetype, ratings in aggregator.archetype_ratings.items():
        if ratings:
            ratings_arr = np.array(ratings)
            sentiment_intensity[archetype] = {
                "mean_rating": round(np.mean(ratings_arr), 3),
                "std_rating": round(np.std(ratings_arr), 3),
                "extreme_positive_rate": round(len([r for r in ratings if r >= 5]) / len(ratings), 4),
                "extreme_negative_rate": round(len([r for r in ratings if r <= 1]) / len(ratings), 4),
                "moderate_rate": round(len([r for r in ratings if 2 < r < 4]) / len(ratings), 4),
                "positivity_bias": round(len([r for r in ratings if r >= 4]) / len(ratings), 4),
                "rating_distribution": {
                    "1_star": round(len([r for r in ratings if r == 1]) / len(ratings), 4),
                    "2_star": round(len([r for r in ratings if r == 2]) / len(ratings), 4),
                    "3_star": round(len([r for r in ratings if r == 3]) / len(ratings), 4),
                    "4_star": round(len([r for r in ratings if r == 4]) / len(ratings), 4),
                    "5_star": round(len([r for r in ratings if r == 5]) / len(ratings), 4),
                },
            }
    
    priors["sentiment_intensity_by_archetype"] = sentiment_intensity
    
    # =========================================================================
    # 6. TEMPORAL BEHAVIOR PATTERNS
    # =========================================================================
    
    temporal_patterns = {}
    
    # Hour of day
    hour_patterns = {}
    for archetype, hours in aggregator.archetype_hour.items():
        total = sum(hours.values())
        if total > 0:
            hour_patterns[archetype] = {
                "morning_6_12": round(sum(hours.get(h, 0) for h in range(6, 12)) / total, 4),
                "afternoon_12_18": round(sum(hours.get(h, 0) for h in range(12, 18)) / total, 4),
                "evening_18_24": round(sum(hours.get(h, 0) for h in range(18, 24)) / total, 4),
                "night_0_6": round(sum(hours.get(h, 0) for h in range(0, 6)) / total, 4),
                "peak_hour": max(hours.items(), key=lambda x: x[1])[0] if hours else 12,
            }
    
    # Day of week
    day_patterns = {}
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    for archetype, days in aggregator.archetype_day.items():
        total = sum(days.values())
        if total > 0:
            day_patterns[archetype] = {
                "weekday_rate": round(sum(days.get(d, 0) for d in range(5)) / total, 4),
                "weekend_rate": round(sum(days.get(d, 0) for d in range(5, 7)) / total, 4),
                "peak_day": day_names[max(days.items(), key=lambda x: x[1])[0]] if days else "Saturday",
            }
    
    temporal_patterns["hour_of_day"] = hour_patterns
    temporal_patterns["day_of_week"] = day_patterns
    priors["temporal_behavior_patterns"] = temporal_patterns
    
    # =========================================================================
    # 7. USER PROFILE PATTERNS (Yelp-specific)
    # =========================================================================
    
    user_profile_patterns = {}
    for archetype in aggregator.archetype_review_count.keys():
        review_counts = aggregator.archetype_review_count[archetype]
        friend_counts = aggregator.archetype_friend_count[archetype]
        elite_years = aggregator.archetype_elite_years[archetype]
        avg_stars = aggregator.archetype_avg_stars[archetype]
        
        if review_counts:
            user_profile_patterns[archetype] = {
                "expertise": {
                    "avg_review_count": round(np.mean(review_counts), 1),
                    "median_review_count": round(np.median(review_counts), 1),
                    "prolific_rate": round(len([r for r in review_counts if r > 50]) / len(review_counts), 4),
                },
                "social_connectivity": {
                    "avg_friends": round(np.mean(friend_counts), 1),
                    "median_friends": round(np.median(friend_counts), 1),
                    "highly_connected_rate": round(len([f for f in friend_counts if f > 100]) / len(friend_counts), 4),
                },
                "status": {
                    "elite_rate": round(len([e for e in elite_years if e > 0]) / len(elite_years), 4),
                    "avg_elite_years": round(np.mean([e for e in elite_years if e > 0]) if any(e > 0 for e in elite_years) else 0, 2),
                },
                "positivity": {
                    "avg_stars_given": round(np.mean(avg_stars), 3),
                    "generous_rate": round(len([s for s in avg_stars if s >= 4]) / len(avg_stars), 4),
                    "critical_rate": round(len([s for s in avg_stars if s <= 2.5]) / len(avg_stars), 4),
                },
                "observations": len(review_counts),
            }
    
    # Compliment patterns
    compliment_patterns = {}
    for archetype, compliments in aggregator.archetype_compliments.items():
        total = sum(compliments.values())
        if total > 0:
            compliment_patterns[archetype] = {
                comp_type: round(count / total, 4)
                for comp_type, count in sorted(compliments.items(), 
                                                key=lambda x: x[1], reverse=True)
            }
    
    user_profile_patterns["compliment_types_received"] = compliment_patterns
    priors["yelp_user_profile_patterns"] = user_profile_patterns
    
    # =========================================================================
    # 8. STATISTICS
    # =========================================================================
    
    priors["enhanced_analysis_stats"] = {
        "total_reviews_analyzed": aggregator.total_reviews,
        "total_users_analyzed": aggregator.total_users,
        "timestamp": datetime.now().isoformat(),
    }
    
    return priors


def merge_enhanced_priors(enhanced: Dict, existing_path: Path) -> Dict:
    """Merge enhanced priors with existing."""
    if not existing_path.exists():
        return enhanced
    
    with open(existing_path) as f:
        existing = json.load(f)
    
    merged = existing.copy()
    
    # Add all enhanced priors
    for key, value in enhanced.items():
        merged[key] = value
    
    return merged


# =============================================================================
# MAIN
# =============================================================================

async def main():
    start_time = datetime.now()
    
    print("\n" + "=" * 70)
    print("ENHANCED PSYCHOLINGUISTIC ANALYSIS PIPELINE")
    print("=" * 70)
    print(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nAnalyses:")
    print("  1. Linguistic Style Fingerprinting")
    print("  2. Yelp User Profile Deep Dive")
    print("  3. Complaint vs Praise Patterns")
    print("  4. Temporal Behavior Patterns")
    print("  5. Sentiment Intensity Analysis")
    print("  6. Trust & Loyalty Patterns")
    print()
    
    aggregator = EnhancedPsycholinguisticAggregator()
    classifier = EnhancedArchetypeClassifier()
    
    # Track user -> archetype mapping for profile analysis
    user_archetypes = {}
    
    # =========================================================================
    # PHASE 1: PROCESS YELP REVIEWS
    # =========================================================================
    
    logger.info("=" * 50)
    logger.info("PHASE 1: Processing Yelp Reviews (Enhanced)")
    logger.info("=" * 50)
    
    review_file = YELP_DIR / "yelp_academic_dataset_review.json"
    if review_file.exists():
        logger.info("Processing Yelp reviews with full linguistic analysis...")
        for review in parse_yelp_reviews_enhanced(review_file, sample_rate=0.15, 
                                                   max_reviews=1000000):
            if not review["text"]:
                continue
            
            result = classifier.classify_enhanced(
                review["text"],
                review["rating"],
                review.get("useful", 0),
                review.get("funny", 0),
                review.get("cool", 0),
            )
            
            aggregator.add_review(
                archetype=result["archetype"],
                linguistic=result["linguistic_style"],
                complaint_praise=result["complaint_praise"],
                trust_loyalty=result["trust_loyalty"],
                timestamp=review.get("timestamp"),
            )
            
            # Track user archetype for profile phase
            user_id = review.get("user_id")
            if user_id:
                if user_id not in user_archetypes:
                    user_archetypes[user_id] = []
                user_archetypes[user_id].append(result["archetype"])
    
    logger.info(f"Reviews processed: {aggregator.total_reviews:,}")
    
    # =========================================================================
    # PHASE 2: PROCESS YELP USER PROFILES
    # =========================================================================
    
    logger.info("\n" + "=" * 50)
    logger.info("PHASE 2: Processing Yelp User Profiles")
    logger.info("=" * 50)
    
    user_file = YELP_DIR / "yelp_academic_dataset_user.json"
    if user_file.exists():
        logger.info("Processing Yelp user profiles...")
        
        # Determine dominant archetype for each user
        user_dominant_archetype = {}
        for user_id, archetypes in user_archetypes.items():
            from collections import Counter
            counts = Counter(archetypes)
            user_dominant_archetype[user_id] = counts.most_common(1)[0][0]
        
        for profile in parse_yelp_users(user_file, sample_rate=0.3, max_users=500000):
            user_id = profile.get("user_id")
            
            # Use known archetype or classify based on profile
            if user_id in user_dominant_archetype:
                archetype = user_dominant_archetype[user_id]
            else:
                # Heuristic classification based on profile
                if profile.get("elite_years", 0) > 0:
                    archetype = "Achiever"
                elif profile.get("review_count", 0) > 100:
                    archetype = "Analyzer"
                elif profile.get("friends_count", 0) > 200:
                    archetype = "Connector"
                elif profile.get("average_stars", 3) >= 4.2:
                    archetype = "Connector"
                else:
                    archetype = "Explorer"
            
            aggregator.add_user_profile(archetype, profile)
    
    logger.info(f"User profiles processed: {aggregator.total_users:,}")
    
    # =========================================================================
    # GENERATE AND SAVE PRIORS
    # =========================================================================
    
    logger.info("\n" + "=" * 50)
    logger.info("GENERATING ENHANCED PRIORS")
    logger.info("=" * 50)
    
    enhanced_priors = generate_enhanced_priors(aggregator)
    
    # Save enhanced priors
    with open(ENHANCED_PRIORS_PATH, 'w') as f:
        json.dump(enhanced_priors, f, indent=2)
    logger.info(f"✓ Enhanced priors saved: {ENHANCED_PRIORS_PATH}")
    
    # Merge with existing
    logger.info("Merging with complete priors...")
    merged = merge_enhanced_priors(enhanced_priors, MERGED_PRIORS_PATH)
    
    with open(MERGED_PRIORS_PATH, 'w') as f:
        json.dump(merged, f, indent=2)
    logger.info(f"✓ Merged priors saved: {MERGED_PRIORS_PATH}")
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 70)
    print("ENHANCED PSYCHOLINGUISTIC ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"\nProcessing time: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    print(f"\nData processed:")
    print(f"  • Reviews: {aggregator.total_reviews:,}")
    print(f"  • User profiles: {aggregator.total_users:,}")
    
    # Show key insights
    print("\n" + "-" * 50)
    print("KEY ENHANCED INSIGHTS:")
    print("-" * 50)
    
    # Linguistic fingerprints
    print("\n[1. LINGUISTIC STYLE FINGERPRINTS]")
    fingerprints = enhanced_priors.get("linguistic_style_fingerprints", {})
    for arch in ["Analyzer", "Connector", "Achiever", "Guardian", "Explorer"]:
        if arch in fingerprints:
            fp = fingerprints[arch]
            cert = fp.get("certainty", {}).get("mean", 0)
            excl = fp.get("emotional_intensity", {}).get("exclamation_mean", 0)
            sent_len = fp.get("complexity", {}).get("avg_sentence_length", 0)
            print(f"  {arch}: certainty={cert:.3f}, exclamation={excl:.3f}, avg_sentence={sent_len:.1f}w")
    
    # Complaint patterns
    print("\n[2. TOP COMPLAINT TRIGGERS BY ARCHETYPE]")
    complaints = enhanced_priors.get("complaint_patterns_by_archetype", {})
    for arch, patterns in complaints.items():
        if patterns:
            top = list(patterns.items())[0]
            print(f"  {arch}: {top[0]} ({top[1]['rate']:.1%})")
    
    # Praise patterns
    print("\n[3. TOP PRAISE TRIGGERS BY ARCHETYPE]")
    praises = enhanced_priors.get("praise_patterns_by_archetype", {})
    for arch, patterns in praises.items():
        if patterns:
            top = list(patterns.items())[0]
            print(f"  {arch}: {top[0]} ({top[1]['rate']:.1%})")
    
    # Trust patterns
    print("\n[4. TRUST ORIENTATION BY ARCHETYPE]")
    trust = enhanced_priors.get("trust_loyalty_patterns", {})
    for arch, patterns in trust.items():
        net = patterns.get("trust", {}).get("net_trust_orientation", 0)
        loyalty = patterns.get("loyalty", {}).get("net_loyalty_orientation", 0)
        print(f"  {arch}: trust_net={net:+.3f}, loyalty_net={loyalty:+.3f}")
    
    # Sentiment intensity
    print("\n[5. SENTIMENT INTENSITY]")
    sentiment = enhanced_priors.get("sentiment_intensity_by_archetype", {})
    for arch, patterns in sentiment.items():
        extreme_pos = patterns.get("extreme_positive_rate", 0)
        extreme_neg = patterns.get("extreme_negative_rate", 0)
        print(f"  {arch}: 5-star={extreme_pos:.1%}, 1-star={extreme_neg:.1%}")
    
    # Temporal patterns
    print("\n[6. TEMPORAL BEHAVIOR]")
    temporal = enhanced_priors.get("temporal_behavior_patterns", {})
    hour_p = temporal.get("hour_of_day", {})
    day_p = temporal.get("day_of_week", {})
    for arch in ["Analyzer", "Connector", "Achiever"]:
        if arch in hour_p and arch in day_p:
            peak_hour = hour_p[arch].get("peak_hour", 12)
            peak_day = day_p[arch].get("peak_day", "Saturday")
            print(f"  {arch}: peak_hour={peak_hour}:00, peak_day={peak_day}")
    
    # User profiles
    print("\n[7. USER PROFILE PATTERNS]")
    profiles = enhanced_priors.get("yelp_user_profile_patterns", {})
    for arch in ["Analyzer", "Connector", "Achiever", "Guardian", "Explorer"]:
        if arch in profiles:
            p = profiles[arch]
            reviews = p.get("expertise", {}).get("avg_review_count", 0)
            friends = p.get("social_connectivity", {}).get("avg_friends", 0)
            elite = p.get("status", {}).get("elite_rate", 0)
            print(f"  {arch}: avg_reviews={reviews:.0f}, avg_friends={friends:.0f}, elite={elite:.1%}")
    
    print("\n✓ Enhanced psycholinguistic analysis complete!")
    print("\nThese insights enable:")
    print("  • Ad copy style matching to archetype natural language")
    print("  • Pain point messaging by archetype")
    print("  • Trust building strategies by archetype")
    print("  • Optimal ad timing by archetype")
    print("  • Influencer targeting based on profile patterns")


if __name__ == "__main__":
    asyncio.run(main())
