# =============================================================================
# ADAM Media-Psychology-Product Graph
# Location: adam/data/amazon/media_product_graph.py
# =============================================================================

"""
MEDIA-PSYCHOLOGY-PRODUCT TRIANGLE

The core insight: Amazon data lets us build a powerful triangular relationship:

    ┌─────────────────────────────────────────────────────────────────┐
    │                                                                 │
    │                      PSYCHOLOGICAL PROFILE                      │
    │                     (Big Five, Regulatory Focus,                │
    │                      Need for Cognition, etc.)                  │
    │                              ▲                                  │
    │                             /│\                                 │
    │                            / │ \                                │
    │                           /  │  \                               │
    │              Linguistic  /   │   \  Linguistic                  │
    │              Analysis   /    │    \ Analysis                    │
    │                        /     │     \                            │
    │                       /      │      \                           │
    │                      ▼       │       ▼                          │
    │              ┌───────────┐   │   ┌───────────┐                  │
    │              │   MEDIA   │◀──┼──▶│  PRODUCT  │                  │
    │              │           │   │   │           │                  │
    │              │ Books     │   │   │ Beauty    │                  │
    │              │ Music     │   │   │ Fashion   │                  │
    │              │ Movies/TV │   │   │ Food      │                  │
    │              │ Kindle    │   │   │ Clothing  │                  │
    │              │ Magazines │   │   │           │                  │
    │              └───────────┘   │   └───────────┘                  │
    │                      ▲       │       ▲                          │
    │                       \      │      /                           │
    │                        \     │     /                            │
    │                         \  Same   /                             │
    │                          \Person /                              │
    │                           \ ID  /                               │
    │                            \   /                                │
    │                             \ /                                 │
    │                              ▼                                  │
    │                         REVIEWER                                │
    │                    (Cross-domain link)                          │
    │                                                                 │
    └─────────────────────────────────────────────────────────────────┘

CONNECTION METHODS:
1. EXPLICIT: Same reviewerID across media and product categories
2. IMPLICIT: Psychographic similarity from linguistic analysis

This enables:
- "People who like X music tend to buy Y products"
- "This psychological profile responds to Z mechanisms for products"
- "Match ad products to media consumption for seamless persuasion"
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# CATEGORY CLASSIFICATION
# =============================================================================

class CategoryType(str, Enum):
    """Classification of Amazon categories."""
    
    MEDIA = "media"      # Content consumption (books, music, movies)
    PRODUCT = "product"  # Physical/consumable products


# Category to type mapping
CATEGORY_TYPES = {
    # MEDIA - Content consumption, reveals psychological preferences
    "Books": CategoryType.MEDIA,
    "Digital_Music": CategoryType.MEDIA,
    "Kindle_Store": CategoryType.MEDIA,
    "Movies_and_TV": CategoryType.MEDIA,
    "Magazine_Subscriptions": CategoryType.MEDIA,
    
    # PRODUCT - Purchase behavior, reveals lifestyle and needs
    "All_Beauty": CategoryType.PRODUCT,
    "Amazon_Fashion": CategoryType.PRODUCT,
    "Beauty_and_Personal_Care": CategoryType.PRODUCT,
    "Clothing_Shoes_and_Jewelry": CategoryType.PRODUCT,
    "Grocery_and_Gourmet_Food": CategoryType.PRODUCT,
}


# Media category psychological implications
MEDIA_PSYCHOLOGY = {
    "Books": {
        "psychological_dimensions": {
            "openness": 0.72,
            "need_for_cognition": 0.75,
            "introspection": 0.70,
            "delayed_gratification": 0.65,
        },
        "genre_insights": {
            "fiction": {"openness": 0.75, "empathy": 0.70},
            "non-fiction": {"need_for_cognition": 0.80, "conscientiousness": 0.65},
            "self-help": {"growth_mindset": 0.75, "conscientiousness": 0.60},
            "mystery": {"need_for_cognition": 0.70, "curiosity": 0.75},
            "romance": {"agreeableness": 0.65, "extraversion": 0.55},
        },
        "persuasion_style": "intellectual_appeal",
        "optimal_mechanisms": ["authority", "self_improvement", "intellectual_stimulation"],
    },
    "Digital_Music": {
        "psychological_dimensions": {
            "openness": 0.68,
            "emotional_sensitivity": 0.72,
            "identity_expression": 0.70,
            "mood_regulation": 0.75,
        },
        "genre_insights": {
            "pop": {"extraversion": 0.70, "agreeableness": 0.60},
            "rock": {"openness": 0.65, "rebelliousness": 0.60},
            "classical": {"openness": 0.80, "need_for_cognition": 0.70},
            "hip_hop": {"extraversion": 0.68, "status_seeking": 0.60},
            "country": {"agreeableness": 0.65, "traditionalism": 0.60},
            "electronic": {"openness": 0.72, "novelty_seeking": 0.70},
        },
        "persuasion_style": "emotional_resonance",
        "optimal_mechanisms": ["identity_expression", "nostalgia", "mood_matching"],
    },
    "Movies_and_TV": {
        "psychological_dimensions": {
            "openness": 0.62,
            "need_for_escapism": 0.68,
            "social_bonding": 0.60,
            "emotional_processing": 0.65,
        },
        "genre_insights": {
            "action": {"sensation_seeking": 0.70, "extraversion": 0.60},
            "comedy": {"extraversion": 0.65, "agreeableness": 0.60},
            "drama": {"openness": 0.68, "emotional_depth": 0.70},
            "documentary": {"need_for_cognition": 0.75, "openness": 0.72},
            "horror": {"sensation_seeking": 0.65, "openness": 0.55},
            "sci_fi": {"openness": 0.75, "need_for_cognition": 0.68},
        },
        "persuasion_style": "narrative_transport",
        "optimal_mechanisms": ["storytelling", "social_proof", "escapism"],
    },
    "Kindle_Store": {
        "psychological_dimensions": {
            "openness": 0.70,
            "need_for_cognition": 0.72,
            "convenience_orientation": 0.68,
            "tech_savvy": 0.65,
        },
        "persuasion_style": "convenience_intellectual",
        "optimal_mechanisms": ["convenience", "intellectual_stimulation", "value"],
    },
    "Magazine_Subscriptions": {
        "psychological_dimensions": {
            "openness": 0.65,
            "need_for_information": 0.70,
            "habit_formation": 0.72,
            "identity_expression": 0.60,
        },
        "persuasion_style": "identity_commitment",
        "optimal_mechanisms": ["commitment", "social_identity", "authority"],
    },
}

# Product category psychological implications
PRODUCT_PSYCHOLOGY = {
    "All_Beauty": {
        "psychological_dimensions": {
            "self_image_investment": 0.75,
            "social_presentation": 0.70,
            "identity_expression": 0.68,
            "experimentation": 0.60,
        },
        "purchase_drivers": ["self_enhancement", "social_approval", "ritual"],
        "persuasion_style": "aspirational_identity",
        "optimal_mechanisms": ["social_proof", "identity_expression", "authority"],
    },
    "Amazon_Fashion": {
        "psychological_dimensions": {
            "status_consciousness": 0.72,
            "identity_expression": 0.75,
            "trend_awareness": 0.70,
            "social_signaling": 0.68,
        },
        "purchase_drivers": ["social_signaling", "identity", "trend_following"],
        "persuasion_style": "social_aspiration",
        "optimal_mechanisms": ["social_proof", "scarcity", "identity_expression"],
    },
    "Beauty_and_Personal_Care": {
        "psychological_dimensions": {
            "self_care": 0.72,
            "health_consciousness": 0.65,
            "quality_sensitivity": 0.68,
            "routine_orientation": 0.70,
        },
        "purchase_drivers": ["self_care", "health", "routine"],
        "persuasion_style": "wellness_authority",
        "optimal_mechanisms": ["authority", "health_wellness", "consistency"],
    },
    "Clothing_Shoes_and_Jewelry": {
        "psychological_dimensions": {
            "identity_expression": 0.75,
            "social_awareness": 0.70,
            "quality_consciousness": 0.65,
            "style_consistency": 0.68,
        },
        "purchase_drivers": ["identity", "occasion", "quality"],
        "persuasion_style": "identity_quality",
        "optimal_mechanisms": ["social_proof", "identity_expression", "quality"],
    },
    "Grocery_and_Gourmet_Food": {
        "psychological_dimensions": {
            "health_consciousness": 0.68,
            "quality_over_price": 0.65,
            "culinary_exploration": 0.60,
            "routine_efficiency": 0.70,
        },
        "purchase_drivers": ["health", "convenience", "quality", "exploration"],
        "persuasion_style": "quality_health",
        "optimal_mechanisms": ["authority", "health_wellness", "authenticity"],
    },
}


# =============================================================================
# CROSS-DOMAIN REVIEWER PROFILE
# =============================================================================

@dataclass
class CrossDomainProfile:
    """
    A reviewer's profile across both media and product categories.
    
    This is the KEY data structure for the persuasion engine:
    It captures what someone CONSUMES (media) and what they BUY (products).
    """
    
    reviewer_id: str
    
    # Media consumption patterns
    media_categories: Set[str] = field(default_factory=set)
    media_review_count: int = 0
    media_total_words: int = 0
    
    # Product purchase patterns
    product_categories: Set[str] = field(default_factory=set)
    product_review_count: int = 0
    product_total_words: int = 0
    
    # Inferred psychology (from linguistic analysis)
    big_five: Dict[str, float] = field(default_factory=dict)
    psychological_dimensions: Dict[str, float] = field(default_factory=dict)
    
    # Review texts for deeper analysis
    media_reviews: List[Dict[str, Any]] = field(default_factory=list)
    product_reviews: List[Dict[str, Any]] = field(default_factory=list)
    
    # Computed insights
    is_cross_domain: bool = False  # Has both media AND product reviews
    cross_domain_confidence: float = 0.0
    
    def add_media_review(self, category: str, text: str, rating: float, asin: str):
        """Add a media review."""
        self.media_categories.add(category)
        self.media_review_count += 1
        self.media_total_words += len(text.split())
        self.media_reviews.append({
            "category": category,
            "text": text,
            "rating": rating,
            "asin": asin,
        })
        self._update_cross_domain_status()
    
    def add_product_review(self, category: str, text: str, rating: float, asin: str):
        """Add a product review."""
        self.product_categories.add(category)
        self.product_review_count += 1
        self.product_total_words += len(text.split())
        self.product_reviews.append({
            "category": category,
            "text": text,
            "rating": rating,
            "asin": asin,
        })
        self._update_cross_domain_status()
    
    def _update_cross_domain_status(self):
        """Update cross-domain status."""
        self.is_cross_domain = bool(self.media_categories and self.product_categories)
        if self.is_cross_domain:
            # Confidence based on review count in both domains
            media_confidence = min(1.0, self.media_review_count / 5)
            product_confidence = min(1.0, self.product_review_count / 5)
            self.cross_domain_confidence = (media_confidence + product_confidence) / 2
    
    def get_all_text(self) -> str:
        """Get all review text for linguistic analysis."""
        texts = []
        for r in self.media_reviews:
            texts.append(r.get("text", ""))
        for r in self.product_reviews:
            texts.append(r.get("text", ""))
        return " ".join(texts)
    
    def get_media_text(self) -> str:
        """Get media review text only."""
        return " ".join(r.get("text", "") for r in self.media_reviews)
    
    def get_product_text(self) -> str:
        """Get product review text only."""
        return " ".join(r.get("text", "") for r in self.product_reviews)


# =============================================================================
# MEDIA-PRODUCT GRAPH BUILDER
# =============================================================================

class MediaProductGraphBuilder:
    """
    Builds the Media-Psychology-Product graph from Amazon data.
    
    Key operations:
    1. Process reviews and classify by category type
    2. Build cross-domain profiles for reviewers
    3. Identify explicit links (same reviewerID)
    4. Identify implicit links (psychographic similarity)
    5. Generate persuasion insights
    """
    
    def __init__(self):
        self.profiles: Dict[str, CrossDomainProfile] = {}
        self.media_asins: Dict[str, Dict[str, Any]] = {}  # ASIN → metadata
        self.product_asins: Dict[str, Dict[str, Any]] = {}
        
        # Statistics
        self.stats = {
            "total_reviews": 0,
            "media_reviews": 0,
            "product_reviews": 0,
            "unique_reviewers": 0,
            "cross_domain_reviewers": 0,
        }
    
    def add_review(
        self,
        reviewer_id: str,
        category: str,
        text: str,
        rating: float,
        asin: str,
    ):
        """
        Add a review to the graph.
        
        Automatically classifies by category type and updates the profile.
        """
        if not text or len(text) < 10:
            return
        
        # Get or create profile
        if reviewer_id not in self.profiles:
            self.profiles[reviewer_id] = CrossDomainProfile(reviewer_id=reviewer_id)
        
        profile = self.profiles[reviewer_id]
        
        # Classify category
        category_type = CATEGORY_TYPES.get(category, CategoryType.PRODUCT)
        
        if category_type == CategoryType.MEDIA:
            profile.add_media_review(category, text, rating, asin)
            self.stats["media_reviews"] += 1
        else:
            profile.add_product_review(category, text, rating, asin)
            self.stats["product_reviews"] += 1
        
        self.stats["total_reviews"] += 1
    
    def add_product_metadata(self, asin: str, category: str, metadata: Dict[str, Any]):
        """Add product/media metadata."""
        category_type = CATEGORY_TYPES.get(category, CategoryType.PRODUCT)
        
        if category_type == CategoryType.MEDIA:
            self.media_asins[asin] = {"category": category, **metadata}
        else:
            self.product_asins[asin] = {"category": category, **metadata}
    
    def compute_statistics(self) -> Dict[str, Any]:
        """Compute graph statistics."""
        self.stats["unique_reviewers"] = len(self.profiles)
        self.stats["cross_domain_reviewers"] = sum(
            1 for p in self.profiles.values() if p.is_cross_domain
        )
        
        # Category distribution
        media_category_counts = defaultdict(int)
        product_category_counts = defaultdict(int)
        
        for profile in self.profiles.values():
            for cat in profile.media_categories:
                media_category_counts[cat] += 1
            for cat in profile.product_categories:
                product_category_counts[cat] += 1
        
        self.stats["media_category_distribution"] = dict(media_category_counts)
        self.stats["product_category_distribution"] = dict(product_category_counts)
        
        return self.stats
    
    def get_cross_domain_profiles(
        self,
        min_media_reviews: int = 2,
        min_product_reviews: int = 2,
    ) -> List[CrossDomainProfile]:
        """
        Get profiles with both media and product reviews.
        
        These are GOLDEN profiles - we have explicit cross-domain data.
        """
        return [
            p for p in self.profiles.values()
            if p.is_cross_domain
            and p.media_review_count >= min_media_reviews
            and p.product_review_count >= min_product_reviews
        ]
    
    def get_media_product_correlations(self) -> Dict[str, Dict[str, float]]:
        """
        Compute correlations between media and product categories.
        
        Returns: {media_category: {product_category: correlation_strength}}
        
        This answers: "People who consume X media tend to buy Y products"
        """
        correlations = defaultdict(lambda: defaultdict(float))
        co_occurrence = defaultdict(lambda: defaultdict(int))
        media_totals = defaultdict(int)
        
        for profile in self.profiles.values():
            if not profile.is_cross_domain:
                continue
            
            # Count co-occurrences
            for media_cat in profile.media_categories:
                media_totals[media_cat] += 1
                for product_cat in profile.product_categories:
                    co_occurrence[media_cat][product_cat] += 1
        
        # Normalize to get correlation strength
        for media_cat, products in co_occurrence.items():
            total = media_totals[media_cat]
            if total > 0:
                for product_cat, count in products.items():
                    correlations[media_cat][product_cat] = count / total
        
        return dict(correlations)
    
    def get_persuasion_insights(
        self,
        media_category: str,
    ) -> Dict[str, Any]:
        """
        Get persuasion insights for targeting media consumers.
        
        Given a media category, returns:
        - Likely product categories
        - Psychological profile
        - Recommended persuasion mechanisms
        """
        media_psych = MEDIA_PSYCHOLOGY.get(media_category, {})
        correlations = self.get_media_product_correlations()
        media_correlations = correlations.get(media_category, {})
        
        # Get top correlated product categories
        sorted_products = sorted(
            media_correlations.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        # Aggregate product psychology for correlated categories
        aggregated_mechanisms = []
        for product_cat, strength in sorted_products:
            product_psych = PRODUCT_PSYCHOLOGY.get(product_cat, {})
            mechanisms = product_psych.get("optimal_mechanisms", [])
            for m in mechanisms:
                if m not in aggregated_mechanisms:
                    aggregated_mechanisms.append(m)
        
        return {
            "media_category": media_category,
            "psychological_profile": media_psych.get("psychological_dimensions", {}),
            "media_persuasion_style": media_psych.get("persuasion_style", ""),
            "media_optimal_mechanisms": media_psych.get("optimal_mechanisms", []),
            "correlated_products": [
                {
                    "category": cat,
                    "correlation_strength": strength,
                    "psychology": PRODUCT_PSYCHOLOGY.get(cat, {}),
                }
                for cat, strength in sorted_products
            ],
            "cross_domain_mechanisms": aggregated_mechanisms[:6],
            "cross_domain_count": sum(
                1 for p in self.profiles.values()
                if p.is_cross_domain and media_category in p.media_categories
            ),
        }


# =============================================================================
# PSYCHOGRAPHIC CLUSTER ANALYZER
# =============================================================================

class PsychographicClusterAnalyzer:
    """
    Analyzes psychographic clusters across media and products.
    
    This identifies IMPLICIT connections:
    - People with similar linguistic patterns
    - Similar psychological profiles
    - Even if they don't have same reviewerID
    """
    
    # Linguistic markers mapped to psychological dimensions
    LINGUISTIC_MARKERS = {
        "intellectual_curiosity": [
            "fascinating", "interesting", "thought-provoking", "insightful",
            "perspective", "understand", "analyze", "concept",
        ],
        "emotional_sensitivity": [
            "feel", "heart", "moving", "touched", "emotional", "beautiful",
            "love", "amazing", "wonderful",
        ],
        "social_orientation": [
            "share", "recommend", "friends", "family", "everyone", "together",
            "community", "people",
        ],
        "quality_focus": [
            "quality", "excellent", "premium", "worth", "value", "superior",
            "best", "top",
        ],
        "practical_orientation": [
            "works", "useful", "practical", "functional", "purpose", "need",
            "effective", "efficient",
        ],
        "identity_expression": [
            "style", "unique", "personal", "express", "represent", "who I am",
            "identity", "self",
        ],
    }
    
    def analyze_text(self, text: str) -> Dict[str, float]:
        """
        Analyze text for psychographic markers.
        
        Returns scores for each psychological dimension.
        """
        text_lower = text.lower()
        words = text_lower.split()
        word_count = len(words) or 1
        
        scores = {}
        for dimension, markers in self.LINGUISTIC_MARKERS.items():
            count = sum(1 for marker in markers if marker in text_lower)
            # Normalize by text length
            scores[dimension] = min(1.0, count / (word_count / 100))
        
        return scores
    
    def compute_similarity(
        self,
        profile1: Dict[str, float],
        profile2: Dict[str, float],
    ) -> float:
        """Compute similarity between two psychographic profiles."""
        dimensions = set(profile1.keys()) | set(profile2.keys())
        
        if not dimensions:
            return 0.0
        
        # Euclidean distance
        sum_sq = sum(
            (profile1.get(d, 0.5) - profile2.get(d, 0.5)) ** 2
            for d in dimensions
        )
        
        distance = sum_sq ** 0.5
        max_distance = len(dimensions) ** 0.5  # Max possible distance
        
        return 1 - (distance / max_distance) if max_distance > 0 else 1.0
    
    def find_similar_profiles(
        self,
        target_profile: Dict[str, float],
        profiles: List[Tuple[str, Dict[str, float]]],
        top_k: int = 10,
    ) -> List[Tuple[str, float]]:
        """
        Find profiles most similar to the target.
        
        Args:
            target_profile: Target psychographic profile
            profiles: List of (profile_id, profile_dict) tuples
            top_k: Number of similar profiles to return
        
        Returns:
            List of (profile_id, similarity_score) tuples
        """
        similarities = []
        
        for profile_id, profile_dict in profiles:
            sim = self.compute_similarity(target_profile, profile_dict)
            similarities.append((profile_id, sim))
        
        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]


# =============================================================================
# PERSUASION ENGINE CORE
# =============================================================================

class PersuasionEngine:
    """
    The core persuasion engine that connects media, psychology, and products.
    
    Given information about what media someone consumes, infers:
    1. Their psychological profile
    2. What products they're likely interested in
    3. What persuasion mechanisms will be most effective
    """
    
    def __init__(self, graph_builder: Optional[MediaProductGraphBuilder] = None):
        self.graph = graph_builder or MediaProductGraphBuilder()
        self.cluster_analyzer = PsychographicClusterAnalyzer()
    
    def infer_from_media(
        self,
        media_categories: List[str],
        media_genres: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Infer psychological profile and product affinities from media consumption.
        
        Args:
            media_categories: Categories consumed (Books, Digital_Music, etc.)
            media_genres: Optional genre specifics (fiction, rock, etc.)
        
        Returns:
            Comprehensive inference including products and mechanisms
        """
        # Aggregate psychological dimensions
        psych_dimensions = defaultdict(list)
        all_mechanisms = []
        persuasion_styles = []
        
        for category in media_categories:
            media_psych = MEDIA_PSYCHOLOGY.get(category, {})
            
            for dim, value in media_psych.get("psychological_dimensions", {}).items():
                psych_dimensions[dim].append(value)
            
            all_mechanisms.extend(media_psych.get("optimal_mechanisms", []))
            if media_psych.get("persuasion_style"):
                persuasion_styles.append(media_psych["persuasion_style"])
            
            # Add genre-specific insights
            if media_genres:
                genre_insights = media_psych.get("genre_insights", {})
                for genre in media_genres:
                    genre_lower = genre.lower()
                    for genre_key, genre_psych in genre_insights.items():
                        if genre_key in genre_lower:
                            for dim, value in genre_psych.items():
                                psych_dimensions[dim].append(value)
        
        # Average psychological dimensions
        avg_dimensions = {
            dim: sum(values) / len(values)
            for dim, values in psych_dimensions.items()
        }
        
        # Dedupe mechanisms while preserving order
        unique_mechanisms = []
        for m in all_mechanisms:
            if m not in unique_mechanisms:
                unique_mechanisms.append(m)
        
        # Get product correlations from graph
        product_affinities = {}
        for category in media_categories:
            insights = self.graph.get_persuasion_insights(category)
            for product_info in insights.get("correlated_products", []):
                cat = product_info["category"]
                strength = product_info["correlation_strength"]
                if cat in product_affinities:
                    product_affinities[cat] = max(product_affinities[cat], strength)
                else:
                    product_affinities[cat] = strength
        
        # Sort products by affinity
        sorted_products = sorted(
            product_affinities.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Get product-specific mechanisms
        product_mechanisms = []
        for product_cat, _ in sorted_products[:3]:
            product_psych = PRODUCT_PSYCHOLOGY.get(product_cat, {})
            for m in product_psych.get("optimal_mechanisms", []):
                if m not in product_mechanisms:
                    product_mechanisms.append(m)
        
        return {
            "media_consumed": media_categories,
            "psychological_profile": avg_dimensions,
            "primary_persuasion_style": persuasion_styles[0] if persuasion_styles else "balanced",
            "media_optimal_mechanisms": unique_mechanisms[:5],
            "product_affinities": [
                {
                    "category": cat,
                    "affinity_strength": strength,
                    "psychology": PRODUCT_PSYCHOLOGY.get(cat, {}),
                }
                for cat, strength in sorted_products[:5]
            ],
            "product_optimal_mechanisms": product_mechanisms[:5],
            "cross_domain_mechanisms": list(set(unique_mechanisms[:3]) | set(product_mechanisms[:3])),
            "confidence": min(0.9, 0.5 + len(media_categories) * 0.1),
        }
    
    def recommend_product_approach(
        self,
        media_categories: List[str],
        product_category: str,
    ) -> Dict[str, Any]:
        """
        Given media consumption, recommend how to advertise a product category.
        
        This is the CORE persuasion function:
        "If someone listens to X and Y, how do we advertise Z to them?"
        """
        # Get media-based inference
        media_inference = self.infer_from_media(media_categories)
        
        # Get product psychology
        product_psych = PRODUCT_PSYCHOLOGY.get(product_category, {})
        
        # Find mechanism overlap
        media_mechanisms = set(media_inference.get("media_optimal_mechanisms", []))
        product_mechanisms = set(product_psych.get("optimal_mechanisms", []))
        
        # Mechanisms that work for BOTH media profile AND product
        shared_mechanisms = media_mechanisms & product_mechanisms
        
        # Primary strategy
        if shared_mechanisms:
            primary_mechanisms = list(shared_mechanisms)
        else:
            # Use media mechanisms (match the person)
            primary_mechanisms = media_inference.get("media_optimal_mechanisms", [])[:2]
        
        # Get affinity strength for this product
        product_affinities = {
            p["category"]: p["affinity_strength"]
            for p in media_inference.get("product_affinities", [])
        }
        affinity_strength = product_affinities.get(product_category, 0.3)
        
        return {
            "media_profile": media_categories,
            "target_product": product_category,
            "psychological_match": media_inference.get("psychological_profile", {}),
            "affinity_strength": affinity_strength,
            "primary_persuasion_style": media_inference.get("primary_persuasion_style", ""),
            "recommended_mechanisms": primary_mechanisms,
            "mechanism_reasoning": self._explain_mechanism_choice(
                primary_mechanisms,
                media_categories,
                product_category,
            ),
            "approach_confidence": affinity_strength * media_inference.get("confidence", 0.5),
        }
    
    def _explain_mechanism_choice(
        self,
        mechanisms: List[str],
        media_categories: List[str],
        product_category: str,
    ) -> str:
        """Generate human-readable explanation for mechanism choice."""
        media_str = ", ".join(media_categories)
        mechanisms_str = ", ".join(mechanisms[:3])
        
        return (
            f"For consumers of {media_str}, we recommend {mechanisms_str} mechanisms "
            f"when advertising {product_category}. This aligns their media consumption "
            f"psychology with the product's optimal persuasion approach, ensuring the "
            f"ad feels natural and non-disruptive."
        )


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_persuasion_engine() -> PersuasionEngine:
    """Create a new persuasion engine instance."""
    return PersuasionEngine()


def create_graph_builder() -> MediaProductGraphBuilder:
    """Create a new graph builder instance."""
    return MediaProductGraphBuilder()
