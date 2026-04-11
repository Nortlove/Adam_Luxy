#!/usr/bin/env python3
# =============================================================================
# COMPREHENSIVE AMAZON DEEP LEARNING PIPELINE
# Location: scripts/run_comprehensive_amazon_deep_learning.py
# =============================================================================

"""
COMPREHENSIVE AMAZON DEEP LEARNING PIPELINE
============================================

This pipeline fixes ALL previous issues and implements DEEP learning:

CRITICAL FIXES:
1. ALL reviews MUST be paired with brand/product information via ASIN
2. Metadata is loaded FIRST to build ASIN→Brand/Title/Price index
3. Hierarchical smart matching for runtime queries
4. Co-purchase relationship learning

DEEP LEARNING COMPONENTS:

1. PRODUCT-BRAND PAIRING (MANDATORY)
   - Load all metadata files FIRST
   - Build ASIN → {brand, title, price, category} index
   - EVERY review gets brand info or is marked "unknown_brand"

2. ARCHETYPE CLASSIFICATION (Enhanced)
   - Category-aware classification
   - Price tier influence
   - Brand prestige signals
   - Review quality weighting

3. PSYCHOLINGUISTIC ANALYSIS (Deep)
   - Emotion intensity mapping
   - Decision style detection
   - Persuasion sensitivity scoring
   - Language pattern extraction

4. BRAND INTELLIGENCE
   - Brand → Archetype affinity
   - Brand → Price tier positioning
   - Brand → Category dominance
   - Brand prestige scoring

5. CO-PURCHASE LEARNING
   - Product relationship graphs
   - Category co-occurrence
   - Brand affinity networks
   - Complementary product patterns

6. PERSUASION PATTERNS
   - Cialdini principle effectiveness by archetype
   - Social proof patterns
   - Authority signals
   - Scarcity language effectiveness

7. HIERARCHICAL MATCHING PREPARATION
   - Build search indices for runtime
   - Brand → Products mapping
   - Category → Products mapping
   - Price tier indices

OUTPUT:
- complete_brand_priors.json (ALL brands with archetypes)
- complete_category_priors.json (ALL categories)
- co_purchase_patterns.json (Relationship learning)
- deep_persuasion_priors.json (Persuasion patterns)
- deep_psycholinguistic_priors.json (Language patterns)
- hierarchical_search_index.json (For runtime matching)

Usage:
    # Full processing (8-12 hours for 200GB)
    python scripts/run_comprehensive_amazon_deep_learning.py
    
    # Test mode (sample only)
    python scripts/run_comprehensive_amazon_deep_learning.py --test
    
    # Resume from checkpoint
    python scripts/run_comprehensive_amazon_deep_learning.py --resume
    
    # Skip co-purchase processing
    python scripts/run_comprehensive_amazon_deep_learning.py --skip-copurchase
"""

import argparse
import asyncio
import json
import logging
import re
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Tuple
import hashlib

import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
log_dir = project_root / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_dir / 'comprehensive_amazon_learning.log', mode='a'),
    ]
)
logger = logging.getLogger(__name__)


# =============================================================================
# PATHS
# =============================================================================

AMAZON_DATA_DIR = project_root / "amazon"
COPURCHASE_DIR = AMAZON_DATA_DIR / "Amazon Co-Purchase Models"
LEARNING_DATA_DIR = project_root / "data" / "learning"
LEARNING_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Output paths
CHECKPOINT_PATH = LEARNING_DATA_DIR / "comprehensive_learning_checkpoint.json"
BRAND_PRIORS_PATH = LEARNING_DATA_DIR / "complete_brand_priors.json"
CATEGORY_PRIORS_PATH = LEARNING_DATA_DIR / "complete_category_priors.json"
COPURCHASE_PATH = LEARNING_DATA_DIR / "co_purchase_patterns.json"
PERSUASION_PATH = LEARNING_DATA_DIR / "deep_persuasion_priors.json"
PSYCHOLINGUISTIC_PATH = LEARNING_DATA_DIR / "deep_psycholinguistic_priors.json"
SEARCH_INDEX_PATH = LEARNING_DATA_DIR / "hierarchical_search_index.json"
MERGED_PRIORS_PATH = LEARNING_DATA_DIR / "complete_coldstart_priors.json"


# =============================================================================
# CONSTANTS
# =============================================================================

# Category mapping
CATEGORY_MAP = {
    "Electronics": "Electronics",
    "Cell_Phones_and_Accessories": "Electronics",
    "Home_and_Kitchen": "Home_Kitchen",
    "Tools_and_Home_Improvement": "Home_Improvement",
    "Patio_Lawn_and_Garden": "Home_Garden",
    "Automotive": "Automotive",
    "Sports_and_Outdoors": "Sports_Outdoors",
    "Health_and_Household": "Health_Wellness",
    "Beauty_and_Personal_Care": "Beauty",
    "All_Beauty": "Beauty",
    "Grocery_and_Gourmet_Food": "Food_Grocery",
    "Pet_Supplies": "Pet_Care",
    "Baby_Products": "Baby_Kids",
    "Toys_and_Games": "Toys_Games",
    "Office_Products": "Office",
    "Industrial_and_Scientific": "Industrial",
    "Arts_Crafts_and_Sewing": "Arts_Crafts",
    "Musical_Instruments": "Music_Instruments",
    "Books": "Books",
    "Kindle_Store": "Books_Digital",
    "Movies_and_TV": "Movies_TV",
    "CDs_and_Vinyl": "Music",
    "Digital_Music": "Music_Digital",
    "Video_Games": "Gaming",
    "Software": "Software",
    "Clothing_Shoes_and_Jewelry": "Fashion",
    "Amazon_Fashion": "Fashion",
    "Magazine_Subscriptions": "Subscriptions",
    "Gift_Cards": "Gift_Cards",
    "Appliances": "Appliances",
    "Handmade_Products": "Handmade",
    "Subscription_Boxes": "Subscriptions",
    "Health_and_Personal_Care": "Health_Wellness",
    "Unknown": "Other",
}

# Premium brand indicators
PREMIUM_BRAND_KEYWORDS = {
    "apple", "sony", "samsung", "lg", "bose", "nike", "adidas", "puma",
    "north face", "patagonia", "sorel", "ugg", "canada goose", "coach",
    "kate spade", "michael kors", "ralph lauren", "calvin klein",
    "dyson", "kitchenaid", "le creuset", "vitamix", "breville",
    "levi's", "tommy hilfiger", "guess", "fossil", "ray-ban",
}

# Stop words for keyword extraction
STOP_WORDS = {
    "the", "a", "an", "and", "or", "for", "of", "with", "in", "on", "at",
    "to", "by", "is", "are", "was", "were", "be", "been", "have", "has",
    "this", "that", "it", "its", "my", "your", "their", "our", "i", "you",
    "we", "they", "he", "she", "very", "just", "so", "really", "great",
    "good", "nice", "well", "much", "more", "also", "too", "but", "not",
    "size", "color", "us", "uk", "eu", "m", "b", "d", "w", "medium", "wide",
    "small", "large", "xl", "xxl", "xs", "pack", "set", "piece", "count",
}


# =============================================================================
# DEEP PSYCHOLINGUISTIC ANALYZER
# =============================================================================

class DeepPsycholinguisticAnalyzer:
    """
    Enhanced psycholinguistic analyzer for deep pattern extraction.
    
    Extracts:
    - Archetype signals from language
    - Emotion intensity
    - Decision style
    - Persuasion sensitivity
    - Language patterns
    """
    
    # Archetype keyword signals
    ARCHETYPE_SIGNALS = {
        "Achiever": {
            "positive": ["best", "premium", "excellent", "quality", "superior", "outstanding", "impressive", 
                        "performance", "professional", "luxury", "high-end", "top", "amazing", "perfect"],
            "negative": ["disappointed", "expected more", "not worth", "overpriced"],
        },
        "Explorer": {
            "positive": ["discovered", "tried", "new", "different", "unique", "interesting", "curious",
                        "adventure", "experiment", "innovative", "creative", "exciting", "fresh"],
            "negative": ["boring", "same old", "nothing new"],
        },
        "Connector": {
            "positive": ["recommend", "everyone", "friends", "family", "gift", "share", "community",
                        "love", "wonderful", "perfect for", "bought for", "gave to"],
            "negative": ["wouldn't recommend", "don't share"],
        },
        "Guardian": {
            "positive": ["safe", "reliable", "trust", "durable", "secure", "warranty", "solid",
                        "dependable", "sturdy", "long-lasting", "well-made", "quality"],
            "negative": ["broke", "fell apart", "cheap", "flimsy", "unreliable"],
        },
        "Pragmatist": {
            "positive": ["value", "price", "affordable", "deal", "bargain", "worth", "budget",
                        "economical", "practical", "functional", "useful", "works well"],
            "negative": ["overpriced", "expensive", "not worth the money"],
        },
        "Analyzer": {
            "positive": ["compared", "research", "specs", "features", "performance", "detailed",
                        "tested", "measured", "analysis", "review", "technical", "data"],
            "negative": ["misleading specs", "inaccurate"],
        },
    }
    
    # Emotion intensity markers
    EMOTION_MARKERS = {
        "high_positive": ["absolutely", "love", "amazing", "perfect", "incredible", "fantastic", 
                         "best ever", "couldn't be happier", "exceeded expectations"],
        "moderate_positive": ["good", "nice", "happy", "satisfied", "pleased", "works well"],
        "neutral": ["okay", "fine", "decent", "average", "acceptable", "alright"],
        "moderate_negative": ["disappointed", "not great", "could be better", "issues", "problems"],
        "high_negative": ["terrible", "worst", "awful", "hate", "waste", "garbage", "regret",
                         "complete failure", "stay away", "don't buy"],
    }
    
    # Decision style markers
    DECISION_STYLES = {
        "analytical": ["compared", "researched", "analysis", "specifications", "versus", "however",
                      "although", "considering", "evaluated", "tested multiple"],
        "impulsive": ["impulse", "had to have", "couldn't resist", "saw and bought", "instant"],
        "social": ["everyone", "recommended", "reviews said", "my friend", "trending", "popular"],
        "cautious": ["finally", "took a while", "hesitated", "worried", "concerned", "skeptical"],
    }
    
    # Cialdini's 6 Principles markers
    PERSUASION_MARKERS = {
        "social_proof": ["everyone", "popular", "best seller", "trending", "thousands", "most people",
                        "highly rated", "five stars", "recommended by many"],
        "authority": ["expert", "professional", "doctor", "certified", "official", "authentic",
                     "genuine", "approved", "recommended by"],
        "scarcity": ["limited", "exclusive", "rare", "only", "last one", "selling fast", "don't miss"],
        "reciprocity": ["included", "free", "bonus", "gift", "extra", "complimentary"],
        "commitment": ["consistent", "always", "every time", "loyal", "repeat", "again"],
        "liking": ["love", "beautiful", "gorgeous", "cute", "aesthetic", "pretty", "stylish"],
    }
    
    def analyze(
        self,
        text: str,
        rating: float,
        category: str,
        brand: Optional[str] = None,
        price: Optional[float] = None,
        verified: bool = False,
        helpful_votes: int = 0,
    ) -> Dict[str, Any]:
        """
        Perform deep psycholinguistic analysis on a review.
        
        Returns comprehensive analysis including:
        - archetype_scores
        - emotion_intensity
        - decision_style
        - persuasion_sensitivity
        - extracted_patterns
        """
        text_lower = text.lower() if text else ""
        words = set(re.findall(r'\b\w+\b', text_lower))
        
        # 1. Archetype scoring
        archetype_scores = self._score_archetypes(text_lower, words, rating, category, brand, price)
        
        # 2. Emotion intensity
        emotion = self._analyze_emotion(text_lower, words, rating)
        
        # 3. Decision style
        decision_style = self._detect_decision_style(text_lower, words)
        
        # 4. Persuasion sensitivity
        persuasion = self._analyze_persuasion_sensitivity(text_lower, words)
        
        # 5. Extract patterns
        patterns = self._extract_patterns(text, rating)
        
        # Determine dominant archetype
        dominant_archetype = max(archetype_scores, key=archetype_scores.get)
        confidence = archetype_scores[dominant_archetype]
        
        return {
            "archetype": dominant_archetype,
            "confidence": confidence,
            "archetype_scores": archetype_scores,
            "emotion_intensity": emotion["intensity"],
            "emotion_valence": emotion["valence"],
            "decision_style": decision_style["dominant"],
            "decision_style_scores": decision_style["scores"],
            "persuasion_sensitivity": persuasion,
            "patterns": patterns,
        }
    
    def _score_archetypes(
        self, 
        text_lower: str, 
        words: Set[str],
        rating: float,
        category: str,
        brand: Optional[str],
        price: Optional[float],
    ) -> Dict[str, float]:
        """Score all archetypes based on signals."""
        
        # Base scores from category
        scores = self._get_category_base_scores(category)
        
        # Adjust by keyword signals
        for archetype, signals in self.ARCHETYPE_SIGNALS.items():
            positive_matches = sum(1 for s in signals["positive"] if s in text_lower)
            negative_matches = sum(1 for s in signals["negative"] if s in text_lower)
            
            scores[archetype] = scores.get(archetype, 0.15) + (positive_matches * 0.05) - (negative_matches * 0.03)
        
        # Adjust by rating
        if rating >= 4.5:
            scores["Achiever"] = scores.get("Achiever", 0.2) + 0.05
            scores["Connector"] = scores.get("Connector", 0.2) + 0.05
        elif rating <= 2:
            scores["Analyzer"] = scores.get("Analyzer", 0.1) + 0.1
            scores["Guardian"] = scores.get("Guardian", 0.15) + 0.05
        
        # Adjust by price tier
        if price:
            if price >= 200:
                scores["Achiever"] = scores.get("Achiever", 0.2) + 0.1
                scores["Pragmatist"] = max(0.05, scores.get("Pragmatist", 0.1) - 0.05)
            elif price < 30:
                scores["Pragmatist"] = scores.get("Pragmatist", 0.1) + 0.1
        
        # Adjust by brand prestige
        if brand:
            brand_lower = brand.lower()
            if any(pb in brand_lower for pb in PREMIUM_BRAND_KEYWORDS):
                scores["Achiever"] = scores.get("Achiever", 0.2) + 0.1
                scores["Pragmatist"] = max(0.05, scores.get("Pragmatist", 0.1) - 0.05)
        
        # Normalize
        total = sum(max(0, v) for v in scores.values())
        if total > 0:
            scores = {k: max(0, v) / total for k, v in scores.items()}
        
        return scores
    
    def _get_category_base_scores(self, category: str) -> Dict[str, float]:
        """Get base archetype scores for a category."""
        cat_lower = category.lower()
        
        defaults = {"Achiever": 0.2, "Explorer": 0.2, "Connector": 0.2, "Guardian": 0.15, "Pragmatist": 0.15, "Analyzer": 0.1}
        
        if any(x in cat_lower for x in ["fashion", "clothing", "shoes", "jewelry"]):
            return {"Connector": 0.3, "Achiever": 0.25, "Explorer": 0.2, "Guardian": 0.1, "Pragmatist": 0.1, "Analyzer": 0.05}
        elif any(x in cat_lower for x in ["electronic", "tech", "computer", "phone"]):
            return {"Achiever": 0.3, "Analyzer": 0.25, "Explorer": 0.2, "Guardian": 0.15, "Pragmatist": 0.1, "Connector": 0.0}
        elif any(x in cat_lower for x in ["beauty", "cosmetic", "skincare"]):
            return {"Connector": 0.3, "Achiever": 0.25, "Explorer": 0.2, "Guardian": 0.15, "Pragmatist": 0.05, "Analyzer": 0.05}
        elif any(x in cat_lower for x in ["home", "kitchen", "garden"]):
            return {"Guardian": 0.25, "Pragmatist": 0.25, "Achiever": 0.2, "Connector": 0.15, "Explorer": 0.1, "Analyzer": 0.05}
        elif any(x in cat_lower for x in ["sport", "outdoor", "fitness"]):
            return {"Achiever": 0.3, "Explorer": 0.25, "Connector": 0.2, "Guardian": 0.15, "Pragmatist": 0.1, "Analyzer": 0.0}
        elif any(x in cat_lower for x in ["book", "kindle", "reading"]):
            return {"Analyzer": 0.3, "Explorer": 0.25, "Connector": 0.2, "Achiever": 0.15, "Guardian": 0.1, "Pragmatist": 0.0}
        elif any(x in cat_lower for x in ["baby", "child", "kid"]):
            return {"Guardian": 0.35, "Connector": 0.3, "Achiever": 0.15, "Pragmatist": 0.1, "Explorer": 0.05, "Analyzer": 0.05}
        
        return defaults
    
    def _analyze_emotion(self, text_lower: str, words: Set[str], rating: float) -> Dict[str, Any]:
        """Analyze emotion intensity and valence."""
        
        scores = {
            "high_positive": 0,
            "moderate_positive": 0,
            "neutral": 0,
            "moderate_negative": 0,
            "high_negative": 0,
        }
        
        for level, markers in self.EMOTION_MARKERS.items():
            for marker in markers:
                if marker in text_lower:
                    scores[level] += 1
        
        # Determine dominant
        dominant = max(scores, key=scores.get) if any(scores.values()) else "neutral"
        
        # Calculate intensity (0-1)
        total_markers = sum(scores.values())
        intensity = min(1.0, total_markers / 5) if total_markers else 0.5
        
        # Calculate valence (-1 to 1)
        positive = scores["high_positive"] * 2 + scores["moderate_positive"]
        negative = scores["high_negative"] * 2 + scores["moderate_negative"]
        valence = (positive - negative) / max(positive + negative, 1)
        
        # Adjust by rating
        if rating >= 4:
            valence = max(valence, 0.3)
        elif rating <= 2:
            valence = min(valence, -0.3)
        
        return {
            "intensity": intensity,
            "valence": valence,
            "dominant_level": dominant,
            "marker_counts": scores,
        }
    
    def _detect_decision_style(self, text_lower: str, words: Set[str]) -> Dict[str, Any]:
        """Detect the reviewer's decision-making style."""
        
        scores = {}
        for style, markers in self.DECISION_STYLES.items():
            score = sum(1 for m in markers if m in text_lower)
            scores[style] = score
        
        dominant = max(scores, key=scores.get) if any(scores.values()) else "balanced"
        
        # Normalize scores
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}
        else:
            scores = {k: 0.25 for k in self.DECISION_STYLES}
        
        return {
            "dominant": dominant,
            "scores": scores,
        }
    
    def _analyze_persuasion_sensitivity(self, text_lower: str, words: Set[str]) -> Dict[str, float]:
        """Analyze sensitivity to Cialdini's persuasion principles."""
        
        sensitivity = {}
        for principle, markers in self.PERSUASION_MARKERS.items():
            count = sum(1 for m in markers if m in text_lower)
            sensitivity[principle] = min(1.0, count / 3)  # Normalize to 0-1
        
        return sensitivity
    
    def _extract_patterns(self, text: str, rating: float) -> Dict[str, List[str]]:
        """Extract useful language patterns."""
        
        patterns = {
            "opening_phrases": [],
            "closing_phrases": [],
            "recommendation_phrases": [],
            "comparison_phrases": [],
        }
        
        sentences = re.split(r'[.!?]', text)
        
        for i, sentence in enumerate(sentences):
            sentence = sentence.strip()
            if not sentence or len(sentence) < 10:
                continue
            
            # Opening phrases (first 2 sentences)
            if i < 2 and len(patterns["opening_phrases"]) < 3:
                patterns["opening_phrases"].append(sentence[:100])
            
            # Closing phrases (last 2 sentences)
            if i >= len(sentences) - 3 and len(patterns["closing_phrases"]) < 3:
                patterns["closing_phrases"].append(sentence[:100])
            
            # Recommendation phrases
            if any(w in sentence.lower() for w in ["recommend", "suggest", "try", "buy"]):
                patterns["recommendation_phrases"].append(sentence[:100])
            
            # Comparison phrases
            if any(w in sentence.lower() for w in ["compared", "versus", "better than", "unlike"]):
                patterns["comparison_phrases"].append(sentence[:100])
        
        return patterns


# =============================================================================
# CHECKPOINT MANAGEMENT
# =============================================================================

@dataclass
class ComprehensiveCheckpoint:
    """Checkpoint for resumable comprehensive learning."""
    started_at: str = ""
    last_updated: str = ""
    phase: str = "metadata"  # metadata, reviews, copurchase, finalize
    
    # Metadata loading progress
    metadata_categories_loaded: List[str] = field(default_factory=list)
    total_products_indexed: int = 0
    total_brands_indexed: int = 0
    
    # Review processing progress
    completed_categories: List[str] = field(default_factory=list)
    current_category: str = ""
    current_position: int = 0
    
    # Statistics
    total_reviews_processed: int = 0
    reviews_with_brand: int = 0
    reviews_without_brand: int = 0
    total_unique_brands: int = 0
    
    # Archetype distribution
    archetype_counts: Dict[str, int] = field(default_factory=dict)
    category_review_counts: Dict[str, int] = field(default_factory=dict)
    
    def save(self):
        """Save checkpoint."""
        self.last_updated = datetime.now().isoformat()
        with open(CHECKPOINT_PATH, 'w') as f:
            json.dump(asdict(self), f, indent=2)
    
    @classmethod
    def load(cls) -> 'ComprehensiveCheckpoint':
        """Load checkpoint."""
        if CHECKPOINT_PATH.exists():
            with open(CHECKPOINT_PATH) as f:
                data = json.load(f)
                return cls(**data)
        return cls(started_at=datetime.now().isoformat())


# =============================================================================
# COMPREHENSIVE AGGREGATOR
# =============================================================================

@dataclass
class ComprehensiveAggregator:
    """
    Aggregates ALL learning data with proper brand pairing.
    
    CRITICAL: Every review MUST have brand info or be explicitly marked.
    """
    
    # ASIN → Product Info (built from metadata)
    product_index: Dict[str, Dict] = field(default_factory=dict)
    
    # Brand → Archetype counts
    brand_archetypes: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
    # Brand → Category counts
    brand_categories: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
    # Brand → Price tier counts
    brand_price_tiers: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
    # Brand → Review quality metrics
    brand_quality: Dict[str, Dict[str, float]] = field(default_factory=lambda: defaultdict(lambda: {"ratings": [], "helpful": []}))
    
    # Category → Archetype counts
    category_archetypes: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
    # Category → Brand counts
    category_brands: Dict[str, Dict[str, int]] = field(default_factory=lambda: defaultdict(lambda: defaultdict(int)))
    
    # Persuasion principle effectiveness
    principle_archetype: Dict[str, Dict[str, List[float]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(list))
    )
    
    # Decision style by archetype
    decision_style_archetype: Dict[str, Dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )
    
    # Emotion patterns
    emotion_by_archetype: Dict[str, Dict[str, List[float]]] = field(
        default_factory=lambda: defaultdict(lambda: {"intensity": [], "valence": []})
    )
    
    # Language patterns by archetype
    language_patterns: Dict[str, Dict[str, List[str]]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(list))
    )
    
    # Price tier → Archetype
    price_tier_archetypes: Dict[str, Dict[str, int]] = field(
        default_factory=lambda: defaultdict(lambda: defaultdict(int))
    )
    
    # Cross-category reviewer tracking
    reviewer_categories: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    reviewer_brands: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    
    # Co-purchase data
    copurchase_pairs: Dict[Tuple[str, str], int] = field(default_factory=lambda: defaultdict(int))
    product_copurchases: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    
    # Statistics
    stats: Dict[str, int] = field(default_factory=lambda: {
        "total_reviews": 0,
        "with_brand": 0,
        "without_brand": 0,
        "with_price": 0,
    })
    
    def add_product(self, asin: str, brand: str, title: str, price: Optional[float], category: str):
        """Add a product to the index."""
        self.product_index[asin] = {
            "brand": brand,
            "title": title,
            "price": price,
            "category": category,
        }
    
    def get_product_info(self, asin: str) -> Optional[Dict]:
        """Get product info for an ASIN."""
        return self.product_index.get(asin)
    
    def add_review(
        self,
        reviewer_id: str,
        asin: str,
        category: str,
        brand: str,
        price: Optional[float],
        analysis: Dict[str, Any],
        rating: float,
        verified: bool,
        helpful_votes: int,
    ):
        """Add a review with its analysis to aggregates."""
        
        archetype = analysis["archetype"]
        
        # Stats
        self.stats["total_reviews"] += 1
        if brand and brand != "unknown_brand":
            self.stats["with_brand"] += 1
        else:
            self.stats["without_brand"] += 1
        if price:
            self.stats["with_price"] += 1
        
        # Category → Archetype
        self.category_archetypes[category][archetype] += 1
        
        # Brand tracking (CRITICAL)
        if brand and brand != "unknown_brand":
            self.brand_archetypes[brand][archetype] += 1
            self.brand_categories[brand][category] += 1
            self.category_brands[category][brand] += 1
            
            # Brand quality tracking
            if len(self.brand_quality[brand]["ratings"]) < 1000:
                self.brand_quality[brand]["ratings"].append(rating)
            if helpful_votes > 0 and len(self.brand_quality[brand]["helpful"]) < 100:
                self.brand_quality[brand]["helpful"].append(helpful_votes)
            
            # Price tier by brand
            if price:
                tier = self._get_price_tier(price)
                self.brand_price_tiers[brand][tier] += 1
        
        # Price tier → Archetype
        if price:
            tier = self._get_price_tier(price)
            self.price_tier_archetypes[tier][archetype] += 1
        
        # Persuasion sensitivity by archetype
        for principle, score in analysis.get("persuasion_sensitivity", {}).items():
            if score > 0:
                self.principle_archetype[archetype][principle].append(score)
        
        # Decision style by archetype
        decision_style = analysis.get("decision_style", "balanced")
        self.decision_style_archetype[archetype][decision_style] += 1
        
        # Emotion by archetype
        if "emotion_intensity" in analysis:
            self.emotion_by_archetype[archetype]["intensity"].append(analysis["emotion_intensity"])
            self.emotion_by_archetype[archetype]["valence"].append(analysis.get("emotion_valence", 0))
        
        # Language patterns (limited collection)
        patterns = analysis.get("patterns", {})
        for pattern_type, phrases in patterns.items():
            if len(self.language_patterns[archetype][pattern_type]) < 100:
                self.language_patterns[archetype][pattern_type].extend(phrases[:2])
        
        # Reviewer tracking (limited for memory)
        if len(self.reviewer_categories) < 500000:
            self.reviewer_categories[reviewer_id].add(category)
            if brand and brand != "unknown_brand":
                self.reviewer_brands[reviewer_id].add(brand)
    
    def add_copurchase(self, product1: str, product2: str):
        """Add a co-purchase relationship."""
        pair = tuple(sorted([product1, product2]))
        self.copurchase_pairs[pair] += 1
        self.product_copurchases[product1].add(product2)
        self.product_copurchases[product2].add(product1)
    
    def _get_price_tier(self, price: float) -> str:
        """Determine price tier."""
        if price < 25:
            return "budget"
        elif price < 75:
            return "mid_range"
        elif price < 200:
            return "premium"
        else:
            return "luxury"


# =============================================================================
# METADATA LOADER
# =============================================================================

def load_all_metadata(
    data_dir: Path,
    aggregator: ComprehensiveAggregator,
    checkpoint: ComprehensiveCheckpoint,
    test_mode: bool = False,
) -> int:
    """
    Load ALL metadata files to build the product index.
    
    CRITICAL: This must run BEFORE processing reviews.
    """
    
    logger.info("=" * 70)
    logger.info("PHASE 1: LOADING ALL METADATA (REQUIRED FOR BRAND PAIRING)")
    logger.info("=" * 70)
    
    meta_files = sorted(data_dir.glob("meta_*.jsonl"))
    logger.info(f"Found {len(meta_files)} metadata files")
    
    total_products = 0
    total_brands = set()
    
    for meta_file in meta_files:
        category_name = meta_file.stem.replace("meta_", "")
        
        if category_name in checkpoint.metadata_categories_loaded:
            logger.info(f"  Skipping {category_name} (already loaded)")
            continue
        
        logger.info(f"\n  Loading: {meta_file.name} ({meta_file.stat().st_size / 1024 / 1024:.1f} MB)")
        
        category_count = 0
        category_brands = set()
        
        limit = 50000 if test_mode else None
        
        try:
            with open(meta_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if limit and category_count >= limit:
                        break
                    
                    try:
                        item = json.loads(line)
                        
                        asin = item.get("parent_asin") or item.get("asin")
                        if not asin:
                            continue
                        
                        brand = item.get("brand") or item.get("manufacturer") or item.get("store") or ""
                        title = item.get("title", "")
                        
                        # Parse price
                        price_raw = item.get("price")
                        price = None
                        if price_raw:
                            try:
                                if isinstance(price_raw, str):
                                    price = float(price_raw.replace("$", "").replace(",", "").split("-")[0].strip())
                                else:
                                    price = float(price_raw)
                            except (ValueError, TypeError):
                                pass
                        
                        # Add to index
                        mapped_category = CATEGORY_MAP.get(category_name, category_name)
                        aggregator.add_product(asin, brand, title, price, mapped_category)
                        
                        category_count += 1
                        if brand:
                            category_brands.add(brand)
                            total_brands.add(brand)
                        
                        if category_count % 100000 == 0:
                            logger.info(f"    Progress: {category_count:,} products, {len(category_brands):,} brands")
                    
                    except json.JSONDecodeError:
                        continue
            
            logger.info(f"    Loaded: {category_count:,} products, {len(category_brands):,} unique brands")
            total_products += category_count
            
            checkpoint.metadata_categories_loaded.append(category_name)
            checkpoint.total_products_indexed = total_products
            checkpoint.total_brands_indexed = len(total_brands)
            checkpoint.save()
            
        except Exception as e:
            logger.error(f"    Error loading {meta_file.name}: {e}")
    
    logger.info(f"\n  METADATA LOADING COMPLETE")
    logger.info(f"  Total products indexed: {total_products:,}")
    logger.info(f"  Total unique brands: {len(total_brands):,}")
    
    return total_products


# =============================================================================
# REVIEW PROCESSOR
# =============================================================================

def process_reviews(
    data_dir: Path,
    aggregator: ComprehensiveAggregator,
    checkpoint: ComprehensiveCheckpoint,
    analyzer: DeepPsycholinguisticAnalyzer,
    test_mode: bool = False,
    sample_rate: float = 1.0,
) -> int:
    """
    Process all review files with proper brand pairing.
    
    CRITICAL: Uses product_index to pair EVERY review with brand info.
    """
    
    logger.info("\n" + "=" * 70)
    logger.info("PHASE 2: PROCESSING REVIEWS WITH BRAND PAIRING")
    logger.info("=" * 70)
    
    review_files = sorted([
        f for f in data_dir.glob("*.jsonl")
        if not f.name.startswith("meta_")
    ], key=lambda x: x.stat().st_size)  # Smallest first
    
    logger.info(f"Found {len(review_files)} review files")
    logger.info(f"Product index size: {len(aggregator.product_index):,}")
    
    if test_mode:
        sample_rate = 0.01  # 1% for test
        max_per_category = 50000
    else:
        sample_rate = 0.05  # 5% sampling for full run (still gives millions of reviews)
        max_per_category = 500000
    
    total_processed = checkpoint.total_reviews_processed
    
    for file_idx, review_file in enumerate(review_files):
        category_name = review_file.stem
        mapped_category = CATEGORY_MAP.get(category_name, category_name)
        
        if category_name in checkpoint.completed_categories:
            logger.info(f"  [{file_idx+1}/{len(review_files)}] Skipping {category_name} (completed)")
            continue
        
        logger.info(f"\n  [{file_idx+1}/{len(review_files)}] Processing {category_name}")
        logger.info(f"    File size: {review_file.stat().st_size / 1024 / 1024 / 1024:.2f} GB")
        
        checkpoint.current_category = category_name
        category_count = 0
        category_with_brand = 0
        category_without_brand = 0
        
        try:
            with open(review_file, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if category_count >= max_per_category:
                        break
                    
                    # Sampling
                    if sample_rate < 1.0 and np.random.random() > sample_rate:
                        continue
                    
                    try:
                        review = json.loads(line)
                        
                        # Get review text
                        text = review.get('text', '') or review.get('reviewText', '') or ''
                        if len(text) < 30:
                            continue
                        
                        # Get ASIN and look up product info
                        asin = review.get('parent_asin') or review.get('asin', '')
                        product_info = aggregator.get_product_info(asin)
                        
                        # Extract brand (CRITICAL)
                        if product_info:
                            brand = product_info.get("brand", "")
                            price = product_info.get("price")
                            product_title = product_info.get("title", "")
                        else:
                            brand = ""
                            price = None
                            product_title = ""
                        
                        if brand:
                            category_with_brand += 1
                        else:
                            brand = "unknown_brand"
                            category_without_brand += 1
                        
                        # Get other fields
                        rating = float(review.get('rating', review.get('overall', 3)) or 3)
                        reviewer_id = review.get('user_id', review.get('reviewerID', ''))
                        verified = review.get('verified_purchase', review.get('verified', False))
                        helpful_votes = review.get('helpful_vote', 0) or 0
                        
                        # Deep analysis
                        analysis = analyzer.analyze(
                            text=text,
                            rating=rating,
                            category=mapped_category,
                            brand=brand if brand != "unknown_brand" else None,
                            price=price,
                            verified=verified,
                            helpful_votes=helpful_votes,
                        )
                        
                        # Add to aggregator
                        aggregator.add_review(
                            reviewer_id=f"amz_{reviewer_id}" if reviewer_id else f"amz_{category_count}",
                            asin=asin,
                            category=mapped_category,
                            brand=brand,
                            price=price,
                            analysis=analysis,
                            rating=rating,
                            verified=verified,
                            helpful_votes=helpful_votes,
                        )
                        
                        category_count += 1
                        total_processed += 1
                        
                        if category_count % 50000 == 0:
                            logger.info(f"    Progress: {category_count:,} reviews ({category_with_brand:,} with brand)")
                            checkpoint.total_reviews_processed = total_processed
                            checkpoint.reviews_with_brand = aggregator.stats["with_brand"]
                            checkpoint.reviews_without_brand = aggregator.stats["without_brand"]
                            checkpoint.save()
                    
                    except json.JSONDecodeError:
                        continue
            
            brand_rate = (category_with_brand / category_count * 100) if category_count else 0
            logger.info(f"    Completed: {category_count:,} reviews, {brand_rate:.1f}% with brand")
            
            checkpoint.completed_categories.append(category_name)
            checkpoint.category_review_counts[category_name] = category_count
            checkpoint.save()
            
        except Exception as e:
            logger.error(f"    Error processing {review_file.name}: {e}")
            import traceback
            traceback.print_exc()
    
    logger.info(f"\n  REVIEW PROCESSING COMPLETE")
    logger.info(f"  Total reviews: {total_processed:,}")
    logger.info(f"  With brand: {aggregator.stats['with_brand']:,}")
    logger.info(f"  Without brand: {aggregator.stats['without_brand']:,}")
    
    return total_processed


# =============================================================================
# CO-PURCHASE PROCESSOR
# =============================================================================

def process_copurchase_data(
    copurchase_dir: Path,
    aggregator: ComprehensiveAggregator,
    test_mode: bool = False,
) -> int:
    """
    Process Amazon co-purchase data for relationship learning.
    """
    
    logger.info("\n" + "=" * 70)
    logger.info("PHASE 3: PROCESSING CO-PURCHASE DATA")
    logger.info("=" * 70)
    
    meta_file = copurchase_dir / "amazon-meta.txt"
    if not meta_file.exists():
        logger.warning(f"Co-purchase metadata not found: {meta_file}")
        return 0
    
    logger.info(f"Loading co-purchase data from {meta_file.name}")
    logger.info(f"File size: {meta_file.stat().st_size / 1024 / 1024:.1f} MB")
    
    total_products = 0
    total_copurchases = 0
    
    limit = 50000 if test_mode else 500000
    
    try:
        with open(meta_file, 'r', encoding='utf-8', errors='ignore') as f:
            current_product = {}
            
            for line in f:
                if total_products >= limit:
                    break
                
                line = line.strip()
                
                if line.startswith("Id:"):
                    # Save previous product
                    if current_product.get("asin") and current_product.get("similar"):
                        for similar_asin in current_product["similar"]:
                            aggregator.add_copurchase(current_product["asin"], similar_asin)
                            total_copurchases += 1
                        total_products += 1
                    
                    current_product = {}
                
                elif line.startswith("ASIN:"):
                    current_product["asin"] = line.split(":")[1].strip()
                
                elif line.startswith("  similar:"):
                    # Format: "  similar: 5  ASIN1  ASIN2  ASIN3  ASIN4  ASIN5"
                    parts = line.split()
                    if len(parts) > 2:
                        try:
                            similar_asins = parts[2:]  # Skip "similar:" and count
                            current_product["similar"] = similar_asins
                        except:
                            pass
                
                if total_products % 50000 == 0 and total_products > 0:
                    logger.info(f"  Progress: {total_products:,} products, {total_copurchases:,} relationships")
        
        logger.info(f"\n  CO-PURCHASE COMPLETE")
        logger.info(f"  Products: {total_products:,}")
        logger.info(f"  Relationships: {total_copurchases:,}")
        
    except Exception as e:
        logger.error(f"Error processing co-purchase data: {e}")
    
    return total_copurchases


# =============================================================================
# PRIORS GENERATION
# =============================================================================

def generate_brand_priors(aggregator: ComprehensiveAggregator) -> Dict:
    """Generate comprehensive brand priors."""
    
    priors = {
        "brand_archetype_priors": {},
        "brand_category_focus": {},
        "brand_price_positioning": {},
        "brand_quality_metrics": {},
        "total_brands": len(aggregator.brand_archetypes),
    }
    
    # Brand → Archetype priors
    for brand, archetypes in aggregator.brand_archetypes.items():
        total = sum(archetypes.values())
        if total >= 10:  # Minimum threshold
            priors["brand_archetype_priors"][brand] = {
                arch: round(count / total, 4)
                for arch, count in archetypes.items()
            }
    
    # Brand → Category focus
    for brand, categories in aggregator.brand_categories.items():
        total = sum(categories.values())
        if total >= 10:
            priors["brand_category_focus"][brand] = {
                cat: round(count / total, 4)
                for cat, count in categories.items()
            }
    
    # Brand → Price positioning
    for brand, tiers in aggregator.brand_price_tiers.items():
        total = sum(tiers.values())
        if total >= 10:
            priors["brand_price_positioning"][brand] = {
                tier: round(count / total, 4)
                for tier, count in tiers.items()
            }
    
    # Brand quality metrics
    for brand, quality in aggregator.brand_quality.items():
        ratings = quality["ratings"]
        helpful = quality["helpful"]
        if ratings:
            priors["brand_quality_metrics"][brand] = {
                "avg_rating": round(np.mean(ratings), 2),
                "rating_std": round(np.std(ratings), 2) if len(ratings) > 1 else 0,
                "review_count": len(ratings),
                "avg_helpful_votes": round(np.mean(helpful), 1) if helpful else 0,
            }
    
    return priors


def generate_category_priors(aggregator: ComprehensiveAggregator) -> Dict:
    """Generate comprehensive category priors."""
    
    priors = {
        "category_archetype_priors": {},
        "category_top_brands": {},
        "category_price_distribution": {},
        "cross_category_lift": {},
    }
    
    # Category → Archetype
    for category, archetypes in aggregator.category_archetypes.items():
        total = sum(archetypes.values())
        if total > 0:
            priors["category_archetype_priors"][category] = {
                arch: round(count / total, 4)
                for arch, count in archetypes.items()
            }
    
    # Category → Top brands
    for category, brands in aggregator.category_brands.items():
        sorted_brands = sorted(brands.items(), key=lambda x: x[1], reverse=True)[:20]
        priors["category_top_brands"][category] = {
            brand: count for brand, count in sorted_brands
        }
    
    # Cross-category lift
    category_counts = {cat: sum(archs.values()) for cat, archs in aggregator.category_archetypes.items()}
    total_reviewers = len(aggregator.reviewer_categories)
    
    multi_cat = [(rid, cats) for rid, cats in aggregator.reviewer_categories.items() if len(cats) > 1]
    if len(multi_cat) > 100000:
        import random
        multi_cat = random.sample(multi_cat, 100000)
    
    cat_pairs = defaultdict(int)
    for _, cats in multi_cat:
        cats_list = list(cats)
        for i in range(len(cats_list)):
            for j in range(i + 1, len(cats_list)):
                pair = tuple(sorted([cats_list[i], cats_list[j]]))
                cat_pairs[pair] += 1
    
    for (cat1, cat2), cooccur in cat_pairs.items():
        if cooccur < 50:
            continue
        expected = (category_counts.get(cat1, 1) / max(total_reviewers, 1)) * \
                   (category_counts.get(cat2, 1) / max(total_reviewers, 1)) * total_reviewers
        if expected > 0:
            lift = cooccur / expected
            if cat1 not in priors["cross_category_lift"]:
                priors["cross_category_lift"][cat1] = {}
            priors["cross_category_lift"][cat1][cat2] = round(lift, 4)
    
    return priors


def generate_persuasion_priors(aggregator: ComprehensiveAggregator) -> Dict:
    """Generate deep persuasion priors."""
    
    priors = {
        "principle_effectiveness_by_archetype": {},
        "decision_style_by_archetype": {},
        "emotion_patterns_by_archetype": {},
        "price_tier_archetype_affinity": {},
    }
    
    # Persuasion principle effectiveness by archetype
    for archetype, principles in aggregator.principle_archetype.items():
        priors["principle_effectiveness_by_archetype"][archetype] = {
            principle: round(np.mean(scores), 3) if scores else 0
            for principle, scores in principles.items()
        }
    
    # Decision style by archetype
    for archetype, styles in aggregator.decision_style_archetype.items():
        total = sum(styles.values())
        if total > 0:
            priors["decision_style_by_archetype"][archetype] = {
                style: round(count / total, 4)
                for style, count in styles.items()
            }
    
    # Emotion patterns by archetype
    for archetype, emotions in aggregator.emotion_by_archetype.items():
        if emotions["intensity"]:
            priors["emotion_patterns_by_archetype"][archetype] = {
                "avg_intensity": round(np.mean(emotions["intensity"]), 3),
                "avg_valence": round(np.mean(emotions["valence"]), 3),
            }
    
    # Price tier archetype affinity
    for tier, archetypes in aggregator.price_tier_archetypes.items():
        total = sum(archetypes.values())
        if total > 0:
            priors["price_tier_archetype_affinity"][tier] = {
                arch: round(count / total, 4)
                for arch, count in archetypes.items()
            }
    
    return priors


def generate_psycholinguistic_priors(aggregator: ComprehensiveAggregator) -> Dict:
    """Generate deep psycholinguistic priors."""
    
    priors = {
        "language_patterns_by_archetype": {},
    }
    
    # Language patterns by archetype
    for archetype, patterns in aggregator.language_patterns.items():
        priors["language_patterns_by_archetype"][archetype] = {
            pattern_type: phrases[:50]  # Limit to 50 examples
            for pattern_type, phrases in patterns.items()
            if phrases
        }
    
    return priors


def generate_copurchase_priors(aggregator: ComprehensiveAggregator) -> Dict:
    """Generate co-purchase priors."""
    
    priors = {
        "total_relationships": len(aggregator.copurchase_pairs),
        "products_with_copurchases": len(aggregator.product_copurchases),
        "top_copurchase_pairs": [],
    }
    
    # Top co-purchase pairs
    sorted_pairs = sorted(
        aggregator.copurchase_pairs.items(),
        key=lambda x: x[1],
        reverse=True
    )[:1000]
    
    priors["top_copurchase_pairs"] = [
        {"pair": list(pair), "count": count}
        for pair, count in sorted_pairs
    ]
    
    return priors


def generate_search_index(aggregator: ComprehensiveAggregator) -> Dict:
    """
    Generate hierarchical search index for runtime queries.
    
    This enables the SMART MATCHING that the user requested:
    - Brand → Products
    - Category → Products
    - Keywords → Products
    """
    
    index = {
        "brand_to_products": {},
        "category_to_brands": {},
        "brand_metadata": {},
    }
    
    # Brand → Sample products (for search)
    brand_products = defaultdict(list)
    for asin, info in aggregator.product_index.items():
        brand = info.get("brand", "")
        if brand and len(brand_products[brand]) < 100:
            brand_products[brand].append({
                "asin": asin,
                "title": info.get("title", "")[:100],
                "price": info.get("price"),
            })
    
    index["brand_to_products"] = dict(brand_products)
    
    # Category → Top brands
    for category, brands in aggregator.category_brands.items():
        sorted_brands = sorted(brands.items(), key=lambda x: x[1], reverse=True)[:50]
        index["category_to_brands"][category] = [b[0] for b in sorted_brands]
    
    # Brand metadata (for smart matching)
    for brand, archetypes in aggregator.brand_archetypes.items():
        total = sum(archetypes.values())
        if total >= 10:
            dominant = max(archetypes, key=archetypes.get)
            index["brand_metadata"][brand] = {
                "dominant_archetype": dominant,
                "review_count": total,
                "categories": list(aggregator.brand_categories.get(brand, {}).keys())[:5],
            }
    
    return index


# =============================================================================
# MAIN PIPELINE
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(description="Comprehensive Amazon Deep Learning")
    parser.add_argument("--test", action="store_true", help="Test mode (sample only)")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--skip-copurchase", action="store_true", help="Skip co-purchase processing")
    args = parser.parse_args()
    
    start_time = datetime.now()
    
    print("\n" + "=" * 70)
    print("COMPREHENSIVE AMAZON DEEP LEARNING PIPELINE")
    print("=" * 70)
    print(f"\nStarted at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {'TEST' if args.test else 'FULL PROCESSING'}")
    print()
    
    # Load or create checkpoint
    if args.resume:
        checkpoint = ComprehensiveCheckpoint.load()
        logger.info(f"Resuming from checkpoint: {checkpoint.total_reviews_processed} reviews")
    else:
        checkpoint = ComprehensiveCheckpoint(started_at=datetime.now().isoformat())
    
    # Initialize
    aggregator = ComprehensiveAggregator()
    analyzer = DeepPsycholinguisticAnalyzer()
    
    # =========================================================================
    # PHASE 1: LOAD METADATA (REQUIRED FOR BRAND PAIRING)
    # =========================================================================
    
    if checkpoint.phase in ["metadata", ""]:
        load_all_metadata(AMAZON_DATA_DIR, aggregator, checkpoint, args.test)
        checkpoint.phase = "reviews"
        checkpoint.save()
    else:
        logger.info("Skipping metadata loading (already completed)")
        # Need to reload product index
        logger.info("Reloading product index from metadata...")
        load_all_metadata(AMAZON_DATA_DIR, aggregator, checkpoint, args.test)
    
    # =========================================================================
    # PHASE 2: PROCESS REVIEWS
    # =========================================================================
    
    if checkpoint.phase in ["reviews"]:
        process_reviews(AMAZON_DATA_DIR, aggregator, checkpoint, analyzer, args.test)
        checkpoint.phase = "copurchase"
        checkpoint.save()
    
    # =========================================================================
    # PHASE 3: CO-PURCHASE DATA
    # =========================================================================
    
    if not args.skip_copurchase and checkpoint.phase in ["copurchase"]:
        process_copurchase_data(COPURCHASE_DIR, aggregator, args.test)
        checkpoint.phase = "finalize"
        checkpoint.save()
    
    # =========================================================================
    # PHASE 4: GENERATE PRIORS
    # =========================================================================
    
    logger.info("\n" + "=" * 70)
    logger.info("PHASE 4: GENERATING COMPREHENSIVE PRIORS")
    logger.info("=" * 70)
    
    # Brand priors
    logger.info("\n  Generating brand priors...")
    brand_priors = generate_brand_priors(aggregator)
    with open(BRAND_PRIORS_PATH, 'w') as f:
        json.dump(brand_priors, f, indent=2)
    logger.info(f"  ✓ Brand priors: {len(brand_priors['brand_archetype_priors'])} brands")
    
    # Category priors
    logger.info("\n  Generating category priors...")
    category_priors = generate_category_priors(aggregator)
    with open(CATEGORY_PRIORS_PATH, 'w') as f:
        json.dump(category_priors, f, indent=2)
    logger.info(f"  ✓ Category priors: {len(category_priors['category_archetype_priors'])} categories")
    
    # Persuasion priors
    logger.info("\n  Generating persuasion priors...")
    persuasion_priors = generate_persuasion_priors(aggregator)
    with open(PERSUASION_PATH, 'w') as f:
        json.dump(persuasion_priors, f, indent=2)
    logger.info(f"  ✓ Persuasion priors saved")
    
    # Psycholinguistic priors
    logger.info("\n  Generating psycholinguistic priors...")
    psycho_priors = generate_psycholinguistic_priors(aggregator)
    with open(PSYCHOLINGUISTIC_PATH, 'w') as f:
        json.dump(psycho_priors, f, indent=2)
    logger.info(f"  ✓ Psycholinguistic priors saved")
    
    # Co-purchase priors
    copurchase_priors = {}
    if not args.skip_copurchase:
        logger.info("\n  Generating co-purchase priors...")
        copurchase_priors = generate_copurchase_priors(aggregator)
        with open(COPURCHASE_PATH, 'w') as f:
            json.dump(copurchase_priors, f, indent=2)
        logger.info(f"  ✓ Co-purchase priors: {copurchase_priors['total_relationships']} relationships")
    
    # Search index
    logger.info("\n  Generating hierarchical search index...")
    search_index = generate_search_index(aggregator)
    with open(SEARCH_INDEX_PATH, 'w') as f:
        json.dump(search_index, f, indent=2)
    logger.info(f"  ✓ Search index: {len(search_index['brand_to_products'])} brands indexed")
    
    # =========================================================================
    # MERGE INTO COMPLETE PRIORS (PRESERVING ALL EXISTING LEARNING)
    # =========================================================================
    
    logger.info("\n  Merging into complete coldstart priors...")
    logger.info("  IMPORTANT: Preserving ALL existing priors and adding new Amazon learning")
    
    # Load existing complete priors to preserve all previous learning
    existing_priors = {}
    if MERGED_PRIORS_PATH.exists():
        with open(MERGED_PRIORS_PATH) as f:
            existing_priors = json.load(f)
        logger.info(f"  Loaded existing priors with {len(existing_priors)} keys")
    
    # Start with existing priors (preserves Google, Specialty, Language, etc.)
    merged = existing_priors.copy()
    
    # =========================================================================
    # UPDATE/ADD AMAZON-SPECIFIC PRIORS (FIXES THE BROKEN ONES)
    # =========================================================================
    
    # 1. BRAND PRIORS - This was broken (had 0 brands from Amazon)
    # Merge existing brands with new Amazon brands (Amazon takes precedence for conflicts)
    existing_brands = merged.get("brand_archetype_priors", {})
    new_brands = brand_priors.get("brand_archetype_priors", {})
    merged["brand_archetype_priors"] = {**existing_brands, **new_brands}
    logger.info(f"  Updated brand_archetype_priors: {len(existing_brands)} existing + {len(new_brands)} new = {len(merged['brand_archetype_priors'])} total")
    
    # 2. CATEGORY PRIORS - Merge (Amazon categories are more granular)
    existing_cats = merged.get("category_archetype_priors", {})
    new_cats = category_priors.get("category_archetype_priors", {})
    merged["category_archetype_priors"] = {**existing_cats, **new_cats}
    logger.info(f"  Updated category_archetype_priors: {len(merged['category_archetype_priors'])} total")
    
    # 3. CROSS-CATEGORY LIFT - Merge
    existing_lift = merged.get("cross_category_lift", {})
    new_lift = category_priors.get("cross_category_lift", {})
    for cat, targets in new_lift.items():
        if cat not in existing_lift:
            existing_lift[cat] = {}
        existing_lift[cat].update(targets)
    merged["cross_category_lift"] = existing_lift
    
    # =========================================================================
    # ADD NEW AMAZON-SPECIFIC PRIORS (DIDN'T EXIST BEFORE)
    # =========================================================================
    
    # 4. Brand Category Focus (NEW)
    merged["brand_category_focus"] = brand_priors.get("brand_category_focus", {})
    
    # 5. Brand Price Positioning (NEW)
    merged["brand_price_positioning"] = brand_priors.get("brand_price_positioning", {})
    
    # 6. Brand Quality Metrics (NEW)
    merged["brand_quality_metrics"] = brand_priors.get("brand_quality_metrics", {})
    
    # 7. Category Top Brands (NEW)
    merged["category_top_brands"] = category_priors.get("category_top_brands", {})
    
    # 8. Price Tier Archetype Affinity (ENHANCED)
    merged["price_tier_archetype_affinity"] = persuasion_priors.get("price_tier_archetype_affinity", {})
    
    # 9. Persuasion Principle Effectiveness by Archetype (ENHANCED)
    existing_persuasion = merged.get("archetype_persuasion_sensitivity", {})
    new_persuasion = persuasion_priors.get("principle_effectiveness_by_archetype", {})
    # Merge by averaging if both exist
    for arch, principles in new_persuasion.items():
        if arch in existing_persuasion:
            for principle, score in principles.items():
                old_score = existing_persuasion[arch].get(principle, score)
                existing_persuasion[arch][principle] = (old_score + score) / 2
        else:
            existing_persuasion[arch] = principles
    merged["archetype_persuasion_sensitivity"] = existing_persuasion
    merged["principle_effectiveness_by_archetype"] = new_persuasion
    
    # 10. Decision Style by Archetype (ENHANCED)
    merged["decision_style_by_archetype"] = persuasion_priors.get("decision_style_by_archetype", {})
    
    # 11. Emotion Patterns by Archetype (NEW)
    merged["emotion_patterns_by_archetype"] = persuasion_priors.get("emotion_patterns_by_archetype", {})
    
    # 12. Language Patterns by Archetype (ENHANCED)
    existing_lang = merged.get("language_patterns_by_archetype", {})
    new_lang = psycho_priors.get("language_patterns_by_archetype", {})
    for arch, patterns in new_lang.items():
        if arch not in existing_lang:
            existing_lang[arch] = {}
        for pattern_type, phrases in patterns.items():
            if pattern_type not in existing_lang[arch]:
                existing_lang[arch][pattern_type] = []
            existing_lang[arch][pattern_type].extend(phrases)
            # Limit to 100 per type
            existing_lang[arch][pattern_type] = existing_lang[arch][pattern_type][:100]
    merged["language_patterns_by_archetype"] = existing_lang
    
    # =========================================================================
    # ADD CO-PURCHASE PATTERNS (COMPLETELY NEW)
    # =========================================================================
    
    if not args.skip_copurchase:
        merged["co_purchase_patterns"] = {
            "total_relationships": copurchase_priors.get("total_relationships", 0),
            "products_with_copurchases": copurchase_priors.get("products_with_copurchases", 0),
            "top_copurchase_pairs": copurchase_priors.get("top_copurchase_pairs", [])[:100],
        }
    
    # =========================================================================
    # UPDATE METADATA
    # =========================================================================
    
    existing_meta = merged.get("metadata", {})
    merged["metadata"] = {
        **existing_meta,
        "amazon_deep_learning": {
            "total_reviews_processed": aggregator.stats["total_reviews"],
            "reviews_with_brand": aggregator.stats["with_brand"],
            "reviews_without_brand": aggregator.stats["without_brand"],
            "total_brands_from_amazon": len(new_brands),
            "total_categories_from_amazon": len(new_cats),
            "generated_at": datetime.now().isoformat(),
        },
        "last_updated": datetime.now().isoformat(),
        "total_brands": len(merged["brand_archetype_priors"]),
        "total_categories": len(merged["category_archetype_priors"]),
    }
    
    # Save merged priors
    with open(MERGED_PRIORS_PATH, 'w') as f:
        json.dump(merged, f, indent=2)
    
    merged_size = MERGED_PRIORS_PATH.stat().st_size / 1024 / 1024
    logger.info(f"  ✓ Complete merged priors saved: {merged_size:.1f} MB")
    logger.info(f"    Total keys: {len(merged)}")
    logger.info(f"    Total brands: {len(merged.get('brand_archetype_priors', {}))}")
    logger.info(f"    Total categories: {len(merged.get('category_archetype_priors', {}))}")
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print("\n" + "=" * 70)
    print("COMPREHENSIVE AMAZON DEEP LEARNING COMPLETE")
    print("=" * 70)
    
    print(f"\nProcessing time: {duration:.1f} seconds ({duration/60:.1f} minutes)")
    
    print(f"\n📊 STATISTICS:")
    print(f"  Total reviews processed: {aggregator.stats['total_reviews']:,}")
    print(f"  Reviews WITH brand: {aggregator.stats['with_brand']:,} ({aggregator.stats['with_brand']/max(aggregator.stats['total_reviews'],1)*100:.1f}%)")
    print(f"  Reviews WITHOUT brand: {aggregator.stats['without_brand']:,}")
    
    print(f"\n📦 BRAND PRIORS:")
    print(f"  Total brands learned: {len(brand_priors['brand_archetype_priors']):,}")
    print(f"  Brands with price positioning: {len(brand_priors['brand_price_positioning']):,}")
    print(f"  Brands with quality metrics: {len(brand_priors['brand_quality_metrics']):,}")
    
    print(f"\n📁 OUTPUT FILES:")
    print(f"  {BRAND_PRIORS_PATH}")
    print(f"  {CATEGORY_PRIORS_PATH}")
    print(f"  {PERSUASION_PATH}")
    print(f"  {PSYCHOLINGUISTIC_PATH}")
    if not args.skip_copurchase:
        print(f"  {COPURCHASE_PATH}")
    print(f"  {SEARCH_INDEX_PATH}")
    print(f"  {MERGED_PRIORS_PATH}")
    
    print("\n✓ Pipeline complete!")
    

if __name__ == "__main__":
    asyncio.run(main())
