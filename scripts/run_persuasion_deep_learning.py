#!/usr/bin/env python3
# =============================================================================
# ADAM Platform - Persuasion-Focused Deep Learning Pipeline
# Location: scripts/run_persuasion_deep_learning.py
# =============================================================================

"""
PERSUASION-FOCUSED DEEP LEARNING PIPELINE

Extracts PSYCHOLINGUISTIC ADVERTISING SIGNALS from review data for ADAM's
iHeartMedia advertising optimization system.

DATASETS:
1. Yelp (7M reviews) - RICHEST: useful/funny/cool votes reveal social influence
2. Movie Reviews (Rotten Tomatoes) - Critic authority vs. audience patterns
3. Restaurants (380K) - Social dining & local service patterns

PERSUASION SIGNALS EXTRACTED (Cialdini Principles + Psycholinguistic Markers):

1. SOCIAL PROOF SENSITIVITY
   - Language: "everyone", "popular", "recommended", "crowded", "busy"
   - Yelp votes: High useful votes = social proof seeker

2. AUTHORITY DEFERENCE
   - Language: "expert", "professional", "certified", "years of experience"
   - Movie critics: isTopCritic correlation with archetype

3. SCARCITY SENSITIVITY
   - Language: "only", "limited", "last", "hurry", "exclusive", "rare"

4. RECIPROCITY PATTERNS
   - Language: "gave us", "complimentary", "free", "bonus", "extra"

5. COMMITMENT/CONSISTENCY
   - Language: "always", "never", "loyal", "regular", "every time"
   - Yelp: Review count history

6. LIKING/SIMILARITY
   - Language: "friendly", "nice", "welcoming", "like family", "comfortable"

7. EMOTIONAL TRIGGERS
   - Fear/Anxiety: "worried", "concerned", "disappointed", "terrible"
   - Excitement: "amazing", "incredible", "blown away", "exceeded"
   - Trust: "honest", "reliable", "trustworthy", "dependable"
   - Nostalgia: "reminds me", "childhood", "memories", "tradition"

8. DECISION-MAKING STYLE
   - Review length (verbose analyzers vs. quick pragmatists)
   - Detail orientation (specific mentions vs. general impressions)
   - Price sensitivity language

OUTPUT:
- Archetype × Persuasion Technique effectiveness matrix
- Emotional trigger patterns by archetype
- Social influence type correlations
- Decision-making style indicators
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
MOVIE_DIR = project_root / "review_todo" / "movie_reviews"
RESTAURANT_DIR = project_root / "review_todo" / "restaurant_reviews"

PERSUASION_PRIORS_PATH = LEARNING_DATA_DIR / "persuasion_priors.json"
MERGED_PRIORS_PATH = LEARNING_DATA_DIR / "complete_coldstart_priors.json"

# Increase CSV field limit
csv.field_size_limit(10 * 1024 * 1024)


# =============================================================================
# PERSUASION LEXICONS (Cialdini Principles)
# =============================================================================

PERSUASION_LEXICONS = {
    # SOCIAL PROOF - "Others are doing it"
    "social_proof": {
        "keywords": {"everyone", "popular", "crowded", "busy", "packed", "line", 
                     "wait", "reservation", "recommended", "trending", "famous",
                     "well-known", "favorite", "go-to", "must-try", "hot spot"},
        "weight": 1.0,
    },
    
    # AUTHORITY - "Experts say"
    "authority": {
        "keywords": {"expert", "professional", "certified", "licensed", "award",
                     "years", "experience", "trained", "specialized", "chef",
                     "sommelier", "master", "renowned", "acclaimed", "michelin"},
        "weight": 1.0,
    },
    
    # SCARCITY - "Limited availability"
    "scarcity": {
        "keywords": {"only", "limited", "exclusive", "rare", "last", "hurry",
                     "sold out", "reservation", "book ahead", "hard to get",
                     "special", "seasonal", "one-of-a-kind", "unique"},
        "weight": 1.0,
    },
    
    # RECIPROCITY - "They gave, so I give back"
    "reciprocity": {
        "keywords": {"complimentary", "free", "bonus", "extra", "gave us",
                     "on the house", "surprised", "generous", "thoughtful",
                     "gift", "treat", "perk", "included"},
        "weight": 1.0,
    },
    
    # COMMITMENT - "I always do this"
    "commitment": {
        "keywords": {"always", "never", "loyal", "regular", "every time",
                     "years", "come back", "return", "faithful", "dedicated",
                     "tradition", "ritual", "habit", "go-to"},
        "weight": 1.0,
    },
    
    # LIKING - "I like them"
    "liking": {
        "keywords": {"friendly", "nice", "welcoming", "warm", "comfortable",
                     "like family", "personable", "genuine", "sincere",
                     "pleasant", "enjoyable", "fun", "lovely"},
        "weight": 1.0,
    },
}

# =============================================================================
# EMOTIONAL TRIGGER LEXICONS
# =============================================================================

EMOTION_LEXICONS = {
    "fear_anxiety": {
        "keywords": {"worried", "concerned", "afraid", "nervous", "anxious",
                     "disappointed", "terrible", "horrible", "worst", "avoid",
                     "never again", "regret", "mistake", "problem", "issue"},
        "valence": -1,
    },
    
    "excitement": {
        "keywords": {"amazing", "incredible", "awesome", "fantastic", "exceeded",
                     "blown away", "impressed", "outstanding", "phenomenal",
                     "spectacular", "extraordinary", "wow", "mind-blowing"},
        "valence": 1,
    },
    
    "trust": {
        "keywords": {"honest", "reliable", "trustworthy", "dependable", "consistent",
                     "authentic", "genuine", "transparent", "integrity", "safe",
                     "secure", "confident", "assured"},
        "valence": 1,
    },
    
    "nostalgia": {
        "keywords": {"reminds", "childhood", "memories", "tradition", "classic",
                     "old-fashioned", "vintage", "throwback", "used to", "remember",
                     "growing up", "grandmother", "homemade"},
        "valence": 0.5,
    },
    
    "status": {
        "keywords": {"upscale", "elegant", "sophisticated", "classy", "premium",
                     "luxury", "exclusive", "high-end", "refined", "prestigious",
                     "impressive", "fancy", "special occasion"},
        "valence": 0.5,
    },
    
    "value": {
        "keywords": {"affordable", "cheap", "reasonable", "worth", "value",
                     "bang for buck", "deal", "bargain", "budget", "economical",
                     "inexpensive", "fair price", "good deal"},
        "valence": 0,
    },
}

# =============================================================================
# DECISION STYLE MARKERS
# =============================================================================

DECISION_STYLE_MARKERS = {
    "analytical": {
        "keywords": {"compared", "versus", "however", "although", "specifically",
                     "particularly", "exactly", "precisely", "detailed", "thorough",
                     "pros and cons", "on one hand", "on the other"},
        "min_length": 200,
    },
    
    "impulsive": {
        "keywords": {"just", "quickly", "spontaneous", "decided", "grabbed",
                     "popped in", "spur of the moment", "whim"},
        "max_length": 100,
    },
    
    "social": {
        "keywords": {"friends", "family", "group", "party", "celebration",
                     "birthday", "anniversary", "date", "gathering", "together",
                     "we", "our", "us"},
    },
    
    "solo": {
        "keywords": {"alone", "myself", "solo", "by myself", "quiet", "peace",
                     "personal", "individual", "me time"},
    },
}


# =============================================================================
# ARCHETYPE CLASSIFIER WITH PERSUASION SIGNALS
# =============================================================================

class PersuasionArchetypeClassifier:
    """
    Classifies reviews into archetypes while extracting persuasion signals.
    """
    
    PROMOTION_WORDS = {"love", "amazing", "best", "excellent", "perfect", "great", "awesome"}
    PREVENTION_WORDS = {"safe", "reliable", "trust", "quality", "careful", "clean", "consistent"}
    ANALYTICAL_WORDS = {"however", "although", "compared", "specifically", "detailed"}
    SOCIAL_WORDS = {"recommend", "friends", "family", "everyone", "together", "we"}
    EXPLORER_WORDS = {"discovered", "new", "different", "unique", "tried", "first", "hidden gem"}
    
    def classify_with_signals(
        self,
        text: str,
        rating: float,
        category: str = "general",
        useful_votes: int = 0,
        funny_votes: int = 0,
        cool_votes: int = 0,
    ) -> Dict[str, Any]:
        """
        Classify review and extract persuasion signals.
        
        Returns:
            Dict with archetype, confidence, and persuasion_signals
        """
        text_lower = text.lower() if text else ""
        words = set(re.findall(r'\b\w+\b', text_lower))
        word_count = len(text_lower.split())
        
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
        
        # YELP VOTE SIGNALS (unique insight!)
        if useful_votes > 5:
            base_weights["Analyzer"] += 0.1  # Information providers
        if funny_votes > 3:
            base_weights["Connector"] += 0.1  # Entertainment providers
        if cool_votes > 3:
            base_weights["Achiever"] += 0.1  # Trend-setters
        
        # Normalize
        total = sum(base_weights.values())
        normalized = {k: v / total for k, v in base_weights.items()}
        archetype = max(normalized, key=normalized.get)
        confidence = normalized[archetype]
        
        # Extract persuasion signals
        persuasion_scores = self._extract_persuasion_signals(text_lower, words)
        emotion_scores = self._extract_emotion_signals(text_lower, words)
        decision_style = self._extract_decision_style(text_lower, words, word_count)
        
        return {
            "archetype": archetype,
            "confidence": confidence,
            "persuasion_signals": persuasion_scores,
            "emotion_signals": emotion_scores,
            "decision_style": decision_style,
            "word_count": word_count,
        }
    
    def _extract_persuasion_signals(self, text: str, words: Set[str]) -> Dict[str, float]:
        """Extract Cialdini persuasion principle signals."""
        scores = {}
        for principle, data in PERSUASION_LEXICONS.items():
            matches = len(words & data["keywords"])
            # Also check for multi-word phrases
            phrase_matches = sum(1 for kw in data["keywords"] if " " in kw and kw in text)
            total_matches = matches + phrase_matches
            scores[principle] = min(total_matches / 3, 1.0)  # Normalize to 0-1
        return scores
    
    def _extract_emotion_signals(self, text: str, words: Set[str]) -> Dict[str, float]:
        """Extract emotional trigger signals."""
        scores = {}
        for emotion, data in EMOTION_LEXICONS.items():
            matches = len(words & data["keywords"])
            phrase_matches = sum(1 for kw in data["keywords"] if " " in kw and kw in text)
            total_matches = matches + phrase_matches
            scores[emotion] = min(total_matches / 3, 1.0)
        return scores
    
    def _extract_decision_style(self, text: str, words: Set[str], word_count: int) -> str:
        """Determine decision-making style."""
        analytical_score = len(words & DECISION_STYLE_MARKERS["analytical"]["keywords"])
        social_score = len(words & DECISION_STYLE_MARKERS["social"]["keywords"])
        
        if analytical_score >= 2 or word_count > 200:
            return "analytical"
        elif social_score >= 2:
            return "social"
        elif word_count < 50:
            return "impulsive"
        else:
            return "balanced"


# =============================================================================
# PERSUASION AGGREGATOR
# =============================================================================

@dataclass
class PersuasionAggregator:
    """Aggregates persuasion signals by archetype."""
    
    # Archetype × Persuasion Principle sensitivity
    archetype_persuasion: Dict[str, Dict[str, List[float]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(list))
    )
    
    # Archetype × Emotional Trigger sensitivity
    archetype_emotions: Dict[str, Dict[str, List[float]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(list))
    )
    
    # Archetype × Decision Style
    archetype_decision_style: Dict[str, Dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )
    
    # Archetype × Review Length (engagement depth)
    archetype_review_length: Dict[str, List[int]] = field(
        default_factory=lambda: defaultdict(list)
    )
    
    # Archetype × Rating distribution
    archetype_ratings: Dict[str, List[float]] = field(
        default_factory=lambda: defaultdict(list)
    )
    
    # Archetype × Yelp vote patterns (social influence type)
    archetype_useful_votes: Dict[str, List[int]] = field(
        default_factory=lambda: defaultdict(list)
    )
    archetype_funny_votes: Dict[str, List[int]] = field(
        default_factory=lambda: defaultdict(list)
    )
    archetype_cool_votes: Dict[str, List[int]] = field(
        default_factory=lambda: defaultdict(list)
    )
    
    # Category × Archetype (for restaurant/business types)
    category_archetypes: Dict[str, Dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )
    
    # Movie critic patterns
    critic_top_archetypes: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    critic_regular_archetypes: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    movie_sentiment_archetypes: Dict[str, Dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )
    
    # Statistics
    source_stats: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    def add_review(
        self,
        archetype: str,
        persuasion_signals: Dict[str, float],
        emotion_signals: Dict[str, float],
        decision_style: str,
        word_count: int,
        rating: float,
        category: str = None,
        useful_votes: int = 0,
        funny_votes: int = 0,
        cool_votes: int = 0,
        source: str = "yelp",
        is_top_critic: bool = False,
        sentiment: str = None,
    ):
        """Add a review's signals to aggregates."""
        
        # Persuasion signals
        for principle, score in persuasion_signals.items():
            if score > 0:
                self.archetype_persuasion[archetype][principle].append(score)
        
        # Emotion signals
        for emotion, score in emotion_signals.items():
            if score > 0:
                self.archetype_emotions[archetype][emotion].append(score)
        
        # Decision style
        self.archetype_decision_style[archetype][decision_style] += 1
        
        # Review length
        if len(self.archetype_review_length[archetype]) < 50000:
            self.archetype_review_length[archetype].append(word_count)
        
        # Rating
        if len(self.archetype_ratings[archetype]) < 50000:
            self.archetype_ratings[archetype].append(rating)
        
        # Yelp votes
        if source == "yelp":
            if len(self.archetype_useful_votes[archetype]) < 20000:
                self.archetype_useful_votes[archetype].append(useful_votes)
                self.archetype_funny_votes[archetype].append(funny_votes)
                self.archetype_cool_votes[archetype].append(cool_votes)
        
        # Category
        if category:
            self.category_archetypes[category][archetype] += 1
        
        # Movie critic patterns
        if source == "movies":
            if is_top_critic:
                self.critic_top_archetypes[archetype] += 1
            else:
                self.critic_regular_archetypes[archetype] += 1
            if sentiment:
                self.movie_sentiment_archetypes[sentiment][archetype] += 1
        
        self.source_stats[source] += 1


# =============================================================================
# PARSERS
# =============================================================================

def parse_yelp_reviews(filepath: Path, business_categories: Dict[str, str], 
                       sample_rate: float = 0.1, max_reviews: int = 1000000):
    """Parse Yelp review JSON (one per line)."""
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
                    business_id = row.get("business_id", "")
                    yield {
                        "text": row.get("text", ""),
                        "rating": float(row.get("stars", 3)),
                        "useful": int(row.get("useful", 0)),
                        "funny": int(row.get("funny", 0)),
                        "cool": int(row.get("cool", 0)),
                        "category": business_categories.get(business_id, "general"),
                        "user_id": row.get("user_id", ""),
                    }
                    count += 1
                except:
                    continue
    except Exception as e:
        logger.warning(f"Error parsing Yelp: {e}")
    logger.info(f"  Parsed {count:,} Yelp reviews")


def load_yelp_businesses(filepath: Path) -> Dict[str, str]:
    """Load Yelp business categories."""
    categories = {}
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                try:
                    row = json.loads(line.strip())
                    business_id = row.get("business_id", "")
                    cats = row.get("categories", "")
                    if business_id and cats:
                        # Get primary category
                        primary = cats.split(",")[0].strip().lower()
                        categories[business_id] = primary
                except:
                    continue
    except Exception as e:
        logger.warning(f"Error loading Yelp businesses: {e}")
    return categories


def parse_movie_reviews(filepath: Path, sample_rate: float = 0.5, max_reviews: int = 500000):
    """Parse Rotten Tomatoes movie reviews."""
    count = 0
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if max_reviews and count >= max_reviews:
                    break
                if sample_rate < 1.0 and np.random.random() > sample_rate:
                    continue
                try:
                    yield {
                        "text": row.get("reviewText", ""),
                        "sentiment": row.get("scoreSentiment", "NEUTRAL"),
                        "is_top_critic": row.get("isTopCritic", "False").lower() == "true",
                        "movie_id": row.get("id", ""),
                    }
                    count += 1
                except:
                    continue
    except Exception as e:
        logger.warning(f"Error parsing movies: {e}")
    logger.info(f"  Parsed {count:,} movie reviews")


# =============================================================================
# GENERATE PERSUASION PRIORS
# =============================================================================

def generate_persuasion_priors(aggregator: PersuasionAggregator) -> Dict[str, Any]:
    """Generate persuasion-focused priors."""
    
    priors = {}
    
    # =========================================================================
    # 1. ARCHETYPE × PERSUASION TECHNIQUE EFFECTIVENESS
    # =========================================================================
    persuasion_matrix = {}
    for archetype, principles in aggregator.archetype_persuasion.items():
        persuasion_matrix[archetype] = {}
        for principle, scores in principles.items():
            if scores:
                persuasion_matrix[archetype][principle] = {
                    "avg_sensitivity": round(np.mean(scores), 4),
                    "presence_rate": round(len([s for s in scores if s > 0]) / max(len(scores), 1), 4),
                    "observations": len(scores),
                }
    priors["archetype_persuasion_sensitivity"] = persuasion_matrix
    
    # =========================================================================
    # 2. ARCHETYPE × EMOTIONAL TRIGGER SENSITIVITY
    # =========================================================================
    emotion_matrix = {}
    for archetype, emotions in aggregator.archetype_emotions.items():
        emotion_matrix[archetype] = {}
        for emotion, scores in emotions.items():
            if scores:
                emotion_matrix[archetype][emotion] = {
                    "avg_sensitivity": round(np.mean(scores), 4),
                    "presence_rate": round(len([s for s in scores if s > 0]) / max(len(scores), 1), 4),
                    "observations": len(scores),
                }
    priors["archetype_emotion_sensitivity"] = emotion_matrix
    
    # =========================================================================
    # 3. ARCHETYPE × DECISION STYLE
    # =========================================================================
    decision_priors = {}
    for archetype, styles in aggregator.archetype_decision_style.items():
        total = sum(styles.values())
        if total > 0:
            decision_priors[archetype] = {
                style: round(count / total, 4)
                for style, count in styles.items()
            }
    priors["archetype_decision_styles"] = decision_priors
    
    # =========================================================================
    # 4. ARCHETYPE × REVIEW ENGAGEMENT DEPTH
    # =========================================================================
    engagement_priors = {}
    for archetype, lengths in aggregator.archetype_review_length.items():
        if lengths:
            engagement_priors[archetype] = {
                "avg_word_count": round(np.mean(lengths), 1),
                "median_word_count": round(np.median(lengths), 1),
                "p90_word_count": round(np.percentile(lengths, 90), 1),
                "observations": len(lengths),
            }
    priors["archetype_engagement_depth"] = engagement_priors
    
    # =========================================================================
    # 5. ARCHETYPE × RATING PATTERNS
    # =========================================================================
    rating_priors = {}
    for archetype, ratings in aggregator.archetype_ratings.items():
        if ratings:
            rating_priors[archetype] = {
                "avg_rating": round(np.mean(ratings), 2),
                "median_rating": round(np.median(ratings), 2),
                "std_rating": round(np.std(ratings), 2),
                "positive_rate": round(len([r for r in ratings if r >= 4]) / len(ratings), 4),
            }
    priors["archetype_rating_patterns"] = rating_priors
    
    # =========================================================================
    # 6. SOCIAL INFLUENCE TYPE (Yelp votes) - UNIQUE!
    # =========================================================================
    social_influence = {}
    for archetype in aggregator.archetype_useful_votes.keys():
        useful = aggregator.archetype_useful_votes[archetype]
        funny = aggregator.archetype_funny_votes[archetype]
        cool = aggregator.archetype_cool_votes[archetype]
        
        if useful:
            total_votes = sum(useful) + sum(funny) + sum(cool)
            social_influence[archetype] = {
                "avg_useful_votes": round(np.mean(useful), 2),
                "avg_funny_votes": round(np.mean(funny), 2),
                "avg_cool_votes": round(np.mean(cool), 2),
                "useful_share": round(sum(useful) / max(total_votes, 1), 4),
                "funny_share": round(sum(funny) / max(total_votes, 1), 4),
                "cool_share": round(sum(cool) / max(total_votes, 1), 4),
                "influence_type": (
                    "information_seeker" if sum(useful) > sum(funny) + sum(cool)
                    else "entertainment_seeker" if sum(funny) > sum(useful) + sum(cool)
                    else "trend_follower" if sum(cool) > sum(useful) + sum(funny)
                    else "balanced"
                ),
            }
    priors["archetype_social_influence_type"] = social_influence
    
    # =========================================================================
    # 7. MOVIE CRITIC AUTHORITY PATTERNS
    # =========================================================================
    total_top = sum(aggregator.critic_top_archetypes.values())
    total_regular = sum(aggregator.critic_regular_archetypes.values())
    
    if total_top > 0 or total_regular > 0:
        priors["movie_critic_patterns"] = {
            "top_critic_archetypes": {
                arch: round(count / max(total_top, 1), 4)
                for arch, count in aggregator.critic_top_archetypes.items()
            },
            "regular_critic_archetypes": {
                arch: round(count / max(total_regular, 1), 4)
                for arch, count in aggregator.critic_regular_archetypes.items()
            },
        }
    
    # Sentiment patterns
    sentiment_priors = {}
    for sentiment, archetypes in aggregator.movie_sentiment_archetypes.items():
        total = sum(archetypes.values())
        if total > 0:
            sentiment_priors[sentiment] = {
                arch: round(count / total, 4)
                for arch, count in archetypes.items()
            }
    if sentiment_priors:
        priors["movie_sentiment_archetypes"] = sentiment_priors
    
    # =========================================================================
    # 8. CATEGORY PRIORS (from Yelp)
    # =========================================================================
    category_priors = {}
    for category, archetypes in aggregator.category_archetypes.items():
        total = sum(archetypes.values())
        if total >= 50:
            category_priors[category] = {
                arch: round(count / total, 4)
                for arch, count in archetypes.items()
            }
    priors["yelp_category_archetype_priors"] = category_priors
    
    # =========================================================================
    # 9. SOURCE STATISTICS
    # =========================================================================
    priors["persuasion_learning_stats"] = dict(aggregator.source_stats)
    
    return priors


def merge_persuasion_priors(persuasion: Dict, existing_path: Path) -> Dict:
    """Merge persuasion priors with existing."""
    if not existing_path.exists():
        return persuasion
    
    with open(existing_path) as f:
        existing = json.load(f)
    
    merged = existing.copy()
    
    # Add all persuasion priors
    for key, value in persuasion.items():
        merged[key] = value
    
    # Merge category priors
    existing_cats = existing.get("category_archetype_priors", {})
    yelp_cats = persuasion.get("yelp_category_archetype_priors", {})
    for cat, priors in yelp_cats.items():
        if cat not in existing_cats:
            existing_cats[cat] = priors
    merged["category_archetype_priors"] = existing_cats
    
    return merged


# =============================================================================
# MAIN
# =============================================================================

async def main():
    start_time = datetime.now()
    
    print("\n" + "=" * 70)
    print("PERSUASION-FOCUSED DEEP LEARNING PIPELINE")
    print("=" * 70)
    print(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nExtracting PSYCHOLINGUISTIC ADVERTISING SIGNALS:")
    print("  • Cialdini Persuasion Principles (social proof, authority, scarcity...)")
    print("  • Emotional Triggers (fear, excitement, trust, nostalgia...)")
    print("  • Decision-Making Styles (analytical, impulsive, social...)")
    print("  • Social Influence Types (from Yelp votes)")
    print()
    
    aggregator = PersuasionAggregator()
    classifier = PersuasionArchetypeClassifier()
    
    # =========================================================================
    # PROCESS YELP (Richest dataset - 7M reviews)
    # =========================================================================
    
    logger.info("=" * 50)
    logger.info("PROCESSING YELP (7M reviews)")
    logger.info("=" * 50)
    
    # Load business categories
    business_file = YELP_DIR / "yelp_academic_dataset_business.json"
    business_categories = {}
    if business_file.exists():
        logger.info("Loading Yelp business categories...")
        business_categories = load_yelp_businesses(business_file)
        logger.info(f"  Loaded {len(business_categories):,} business categories")
    
    # Process reviews
    review_file = YELP_DIR / "yelp_academic_dataset_review.json"
    if review_file.exists():
        logger.info("Processing Yelp reviews...")
        for review in parse_yelp_reviews(review_file, business_categories, 
                                         sample_rate=0.15, max_reviews=1000000):
            if not review["text"]:
                continue
            
            result = classifier.classify_with_signals(
                review["text"],
                review["rating"],
                review.get("category", "general"),
                review.get("useful", 0),
                review.get("funny", 0),
                review.get("cool", 0),
            )
            
            aggregator.add_review(
                archetype=result["archetype"],
                persuasion_signals=result["persuasion_signals"],
                emotion_signals=result["emotion_signals"],
                decision_style=result["decision_style"],
                word_count=result["word_count"],
                rating=review["rating"],
                category=review.get("category"),
                useful_votes=review.get("useful", 0),
                funny_votes=review.get("funny", 0),
                cool_votes=review.get("cool", 0),
                source="yelp",
            )
    
    logger.info(f"Yelp reviews processed: {aggregator.source_stats['yelp']:,}")
    
    # =========================================================================
    # PROCESS MOVIE REVIEWS (Critic patterns)
    # =========================================================================
    
    logger.info("\n" + "=" * 50)
    logger.info("PROCESSING MOVIE REVIEWS (Rotten Tomatoes)")
    logger.info("=" * 50)
    
    movie_file = MOVIE_DIR / "rotten_tomatoes_movie_reviews.csv"
    if movie_file.exists():
        logger.info("Processing movie reviews...")
        for review in parse_movie_reviews(movie_file, sample_rate=0.5, max_reviews=500000):
            if not review["text"]:
                continue
            
            # Movie critics don't have ratings, use sentiment
            rating = 5 if review["sentiment"] == "POSITIVE" else 2
            
            result = classifier.classify_with_signals(
                review["text"],
                rating,
                "movies",
            )
            
            aggregator.add_review(
                archetype=result["archetype"],
                persuasion_signals=result["persuasion_signals"],
                emotion_signals=result["emotion_signals"],
                decision_style=result["decision_style"],
                word_count=result["word_count"],
                rating=rating,
                source="movies",
                is_top_critic=review.get("is_top_critic", False),
                sentiment=review.get("sentiment"),
            )
    
    logger.info(f"Movie reviews processed: {aggregator.source_stats['movies']:,}")
    
    # =========================================================================
    # GENERATE AND SAVE PRIORS
    # =========================================================================
    
    logger.info("\n" + "=" * 50)
    logger.info("GENERATING PERSUASION PRIORS")
    logger.info("=" * 50)
    
    persuasion_priors = generate_persuasion_priors(aggregator)
    
    # Save persuasion priors
    with open(PERSUASION_PRIORS_PATH, 'w') as f:
        json.dump(persuasion_priors, f, indent=2)
    logger.info(f"✓ Persuasion priors saved: {PERSUASION_PRIORS_PATH}")
    
    # Merge with existing
    logger.info("Merging with existing priors...")
    merged = merge_persuasion_priors(persuasion_priors, MERGED_PRIORS_PATH)
    
    with open(MERGED_PRIORS_PATH, 'w') as f:
        json.dump(merged, f, indent=2)
    logger.info(f"✓ Merged priors saved: {MERGED_PRIORS_PATH}")
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 70)
    print("PERSUASION DEEP LEARNING COMPLETE")
    print("=" * 70)
    print(f"\nProcessing time: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    
    total = sum(aggregator.source_stats.values())
    print(f"\nReviews processed: {total:,}")
    for source, count in aggregator.source_stats.items():
        print(f"  • {source}: {count:,}")
    
    # Show key insights
    print("\n" + "-" * 50)
    print("KEY PERSUASION INSIGHTS:")
    print("-" * 50)
    
    # Persuasion sensitivity
    print("\n[ARCHETYPE × PERSUASION TECHNIQUE]")
    persuasion_matrix = persuasion_priors.get("archetype_persuasion_sensitivity", {})
    for archetype in ["Achiever", "Connector", "Explorer", "Guardian", "Analyzer"]:
        if archetype in persuasion_matrix:
            principles = persuasion_matrix[archetype]
            top_principle = max(principles.items(), key=lambda x: x[1].get("avg_sensitivity", 0))
            print(f"  {archetype}: Most sensitive to {top_principle[0]} ({top_principle[1].get('avg_sensitivity', 0):.2f})")
    
    # Social influence
    print("\n[SOCIAL INFLUENCE TYPE (from Yelp votes)]")
    social = persuasion_priors.get("archetype_social_influence_type", {})
    for archetype, data in social.items():
        print(f"  {archetype}: {data.get('influence_type', 'unknown')} (useful:{data.get('avg_useful_votes', 0):.1f}, funny:{data.get('avg_funny_votes', 0):.1f}, cool:{data.get('avg_cool_votes', 0):.1f})")
    
    # Decision styles
    print("\n[DECISION STYLE DISTRIBUTION]")
    decision = persuasion_priors.get("archetype_decision_styles", {})
    for archetype, styles in decision.items():
        dominant = max(styles.items(), key=lambda x: x[1])
        print(f"  {archetype}: {dominant[0]} ({dominant[1]:.1%})")
    
    print("\n✓ Persuasion deep learning complete!")
    print("\nThese insights can now be used for:")
    print("  • Matching ads to archetypes based on persuasion technique")
    print("  • Optimizing emotional triggers in ad copy")
    print("  • Timing decisions based on decision style")
    print("  • Targeting social influence channels by archetype")


if __name__ == "__main__":
    asyncio.run(main())
