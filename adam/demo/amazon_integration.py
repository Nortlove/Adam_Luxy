# =============================================================================
# ADAM Demo - Amazon Data Integration
# Location: adam/demo/amazon_integration.py
# =============================================================================

"""
AMAZON DATA INTEGRATION FOR DEMO

Connects Amazon review psychological profiles to the demo via the
MEDIA-PSYCHOLOGY-PRODUCT TRIANGLE:

    ┌─────────────────────────────────────────────────────────────────┐
    │                                                                 │
    │                      PSYCHOLOGICAL PROFILE                      │
    │                     (Big Five, Regulatory Focus)                │
    │                              ▲                                  │
    │                             /│\                                 │
    │                            / │ \                                │
    │                           /  │  \                               │
    │                          ▼   │   ▼                              │
    │              ┌───────────┐   │   ┌───────────┐                  │
    │              │   MEDIA   │◀──┼──▶│  PRODUCT  │                  │
    │              │           │   │   │           │                  │
    │              │ Books     │   │   │ Beauty    │                  │
    │              │ Music     │   │   │ Fashion   │                  │
    │              │ Movies/TV │   │   │ Food      │                  │
    │              └───────────┘   │   └───────────┘                  │
    │                              │                                  │
    │                              ▼                                  │
    │                          REVIEWER                               │
    │                    (Cross-domain link)                          │
    │                                                                 │
    └─────────────────────────────────────────────────────────────────┘

Key capabilities:
1. Media consumption → Psychological inference → Product affinity
2. Cross-domain reviewer linkage (same person buys media AND products)
3. Persuasion mechanism recommendations based on media profile
4. "Seamless advertising" that mimics the user's state
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# AMAZON PSYCHOLOGICAL PRIORS
# =============================================================================

# Pre-computed category psychological profiles
# Based on Amazon review corpus linguistic analysis
CATEGORY_PSYCHOLOGY = {
    "All_Beauty": {
        "big_five": {
            "openness": 0.58,
            "conscientiousness": 0.52,
            "extraversion": 0.62,
            "agreeableness": 0.58,
            "neuroticism": 0.55,
        },
        "regulatory_focus": {"promotion": 0.55, "prevention": 0.45},
        "effective_mechanisms": ["identity_expression", "social_proof", "authenticity"],
        "description": "Beauty buyers value self-expression and social validation",
    },
    "Amazon_Fashion": {
        "big_five": {
            "openness": 0.65,
            "conscientiousness": 0.48,
            "extraversion": 0.68,
            "agreeableness": 0.55,
            "neuroticism": 0.52,
        },
        "regulatory_focus": {"promotion": 0.62, "prevention": 0.38},
        "effective_mechanisms": ["social_proof", "identity_expression", "novelty", "scarcity"],
        "description": "Fashion buyers are trend-conscious, social, and identity-driven",
    },
    "Beauty_and_Personal_Care": {
        "big_five": {
            "openness": 0.55,
            "conscientiousness": 0.54,
            "extraversion": 0.60,
            "agreeableness": 0.58,
            "neuroticism": 0.54,
        },
        "regulatory_focus": {"promotion": 0.52, "prevention": 0.48},
        "effective_mechanisms": ["authority", "social_proof", "identity_expression"],
        "description": "Personal care buyers balance self-expression with trust in experts",
    },
    "Books": {
        "big_five": {
            "openness": 0.72,
            "conscientiousness": 0.58,
            "extraversion": 0.42,
            "agreeableness": 0.55,
            "neuroticism": 0.52,
        },
        "regulatory_focus": {"promotion": 0.48, "prevention": 0.52},
        "effective_mechanisms": ["authority", "intellectual_stimulation", "self_improvement"],
        "description": "Book buyers are highly open, introspective, and value learning",
    },
    "Clothing_Shoes_and_Jewelry": {
        "big_five": {
            "openness": 0.62,
            "conscientiousness": 0.50,
            "extraversion": 0.65,
            "agreeableness": 0.55,
            "neuroticism": 0.53,
        },
        "regulatory_focus": {"promotion": 0.58, "prevention": 0.42},
        "effective_mechanisms": ["social_proof", "identity_expression", "scarcity"],
        "description": "Clothing buyers prioritize social image and self-expression",
    },
    "Digital_Music": {
        "big_five": {
            "openness": 0.68,
            "conscientiousness": 0.45,
            "extraversion": 0.55,
            "agreeableness": 0.52,
            "neuroticism": 0.50,
        },
        "regulatory_focus": {"promotion": 0.60, "prevention": 0.40},
        "effective_mechanisms": ["nostalgia", "identity_expression", "novelty"],
        "description": "Music buyers value emotional connection and self-expression through music",
    },
    "Grocery_and_Gourmet_Food": {
        "big_five": {
            "openness": 0.55,
            "conscientiousness": 0.60,
            "extraversion": 0.52,
            "agreeableness": 0.58,
            "neuroticism": 0.48,
        },
        "regulatory_focus": {"promotion": 0.45, "prevention": 0.55},
        "effective_mechanisms": ["authority", "health_wellness", "authenticity", "quality"],
        "description": "Food buyers are quality-conscious and health-oriented",
    },
    "Kindle_Store": {
        "big_five": {
            "openness": 0.70,
            "conscientiousness": 0.55,
            "extraversion": 0.45,
            "agreeableness": 0.52,
            "neuroticism": 0.50,
        },
        "regulatory_focus": {"promotion": 0.52, "prevention": 0.48},
        "effective_mechanisms": ["convenience", "intellectual_stimulation", "value"],
        "description": "Digital readers value convenience and intellectual growth",
    },
    "Magazine_Subscriptions": {
        "big_five": {
            "openness": 0.65,
            "conscientiousness": 0.58,
            "extraversion": 0.50,
            "agreeableness": 0.55,
            "neuroticism": 0.48,
        },
        "regulatory_focus": {"promotion": 0.48, "prevention": 0.52},
        "effective_mechanisms": ["authority", "social_identity", "habit", "commitment"],
        "description": "Magazine subscribers value ongoing learning and curated content",
    },
    "Movies_and_TV": {
        "big_five": {
            "openness": 0.62,
            "conscientiousness": 0.48,
            "extraversion": 0.55,
            "agreeableness": 0.52,
            "neuroticism": 0.52,
        },
        "regulatory_focus": {"promotion": 0.55, "prevention": 0.45},
        "effective_mechanisms": ["nostalgia", "social_proof", "escapism", "entertainment"],
        "description": "Media buyers value entertainment, escapism, and shared experiences",
    },
}


# =============================================================================
# AMAZON ARCHETYPES
# =============================================================================

# Pre-defined reviewer archetypes for cold-start matching
AMAZON_ARCHETYPES = {
    "explorer": {
        "name": "Explorer",
        "description": "Curious, adventurous buyers who seek novelty and new experiences",
        "big_five": {
            "openness": 0.78,
            "conscientiousness": 0.48,
            "extraversion": 0.58,
            "agreeableness": 0.52,
            "neuroticism": 0.45,
        },
        "regulatory_focus": {"promotion": 0.72, "prevention": 0.28},
        "effective_mechanisms": ["novelty", "curiosity", "adventure", "discovery"],
        "category_affinities": ["Books", "Digital_Music", "Movies_and_TV"],
        "behavioral_markers": {
            "avg_rating": 4.2,
            "review_length": "long",
            "category_diversity": "high",
        },
    },
    "achiever": {
        "name": "Achiever",
        "description": "Goal-oriented buyers focused on quality and success",
        "big_five": {
            "openness": 0.55,
            "conscientiousness": 0.75,
            "extraversion": 0.60,
            "agreeableness": 0.50,
            "neuroticism": 0.42,
        },
        "regulatory_focus": {"promotion": 0.65, "prevention": 0.35},
        "effective_mechanisms": ["authority", "competence", "achievement", "quality"],
        "category_affinities": ["Books", "Kindle_Store", "Magazine_Subscriptions"],
        "behavioral_markers": {
            "avg_rating": 3.8,
            "review_length": "detailed",
            "category_diversity": "moderate",
        },
    },
    "connector": {
        "name": "Connector",
        "description": "Social buyers who value relationships and community",
        "big_five": {
            "openness": 0.55,
            "conscientiousness": 0.50,
            "extraversion": 0.72,
            "agreeableness": 0.70,
            "neuroticism": 0.48,
        },
        "regulatory_focus": {"promotion": 0.58, "prevention": 0.42},
        "effective_mechanisms": ["social_proof", "community", "belonging", "reciprocity"],
        "category_affinities": ["Amazon_Fashion", "Beauty_and_Personal_Care", "Clothing_Shoes_and_Jewelry"],
        "behavioral_markers": {
            "avg_rating": 4.3,
            "review_length": "moderate",
            "category_diversity": "moderate",
        },
    },
    "guardian": {
        "name": "Guardian",
        "description": "Security-focused buyers who prioritize safety and reliability",
        "big_five": {
            "openness": 0.45,
            "conscientiousness": 0.70,
            "extraversion": 0.45,
            "agreeableness": 0.60,
            "neuroticism": 0.58,
        },
        "regulatory_focus": {"promotion": 0.32, "prevention": 0.68},
        "effective_mechanisms": ["security", "trust", "reliability", "authority"],
        "category_affinities": ["Grocery_and_Gourmet_Food", "Beauty_and_Personal_Care"],
        "behavioral_markers": {
            "avg_rating": 3.5,
            "review_length": "detailed",
            "category_diversity": "low",
        },
    },
    "pragmatist": {
        "name": "Pragmatist",
        "description": "Value-focused buyers who seek the best bang for buck",
        "big_five": {
            "openness": 0.50,
            "conscientiousness": 0.65,
            "extraversion": 0.50,
            "agreeableness": 0.52,
            "neuroticism": 0.50,
        },
        "regulatory_focus": {"promotion": 0.45, "prevention": 0.55},
        "effective_mechanisms": ["value", "comparison", "practicality", "efficiency"],
        "category_affinities": ["Grocery_and_Gourmet_Food", "Kindle_Store"],
        "behavioral_markers": {
            "avg_rating": 3.7,
            "review_length": "short",
            "category_diversity": "moderate",
        },
    },
    "connoisseur": {
        "name": "Connoisseur",
        "description": "Quality-obsessed buyers who appreciate the finer things",
        "big_five": {
            "openness": 0.72,
            "conscientiousness": 0.60,
            "extraversion": 0.48,
            "agreeableness": 0.48,
            "neuroticism": 0.45,
        },
        "regulatory_focus": {"promotion": 0.52, "prevention": 0.48},
        "effective_mechanisms": ["quality", "exclusivity", "expertise", "authenticity"],
        "category_affinities": ["Grocery_and_Gourmet_Food", "Digital_Music", "Books"],
        "behavioral_markers": {
            "avg_rating": 3.5,
            "review_length": "very_long",
            "category_diversity": "focused",
        },
    },
}


# =============================================================================
# AMAZON INTEGRATION SERVICE
# =============================================================================

class AmazonIntegrationService:
    """
    Service for integrating Amazon psychological priors with the demo.
    """
    
    def __init__(self, profiles_dir: Optional[str] = None):
        """
        Initialize with optional custom profiles directory.
        
        Args:
            profiles_dir: Path to directory containing exported profiles
        """
        self.profiles_dir = Path(profiles_dir) if profiles_dir else None
        self._user_profiles: Dict[str, Dict] = {}
        self._category_profiles: Dict[str, Dict] = CATEGORY_PSYCHOLOGY.copy()
        self._archetypes: Dict[str, Dict] = AMAZON_ARCHETYPES.copy()
        
        # Load custom profiles if available
        if self.profiles_dir:
            self._load_custom_profiles()
    
    def _load_custom_profiles(self):
        """Load custom profiles from files."""
        if not self.profiles_dir or not self.profiles_dir.exists():
            return
        
        # Load user profiles
        user_profiles_path = self.profiles_dir / "user_profiles.json"
        if user_profiles_path.exists():
            try:
                with open(user_profiles_path) as f:
                    profiles = json.load(f)
                    for p in profiles:
                        self._user_profiles[p["amazon_user_id"]] = p
                logger.info(f"Loaded {len(self._user_profiles)} user profiles")
            except Exception as e:
                logger.warning(f"Failed to load user profiles: {e}")
        
        # Load category profiles
        category_profiles_path = self.profiles_dir / "category_profiles.json"
        if category_profiles_path.exists():
            try:
                with open(category_profiles_path) as f:
                    profiles = json.load(f)
                    for p in profiles:
                        self._category_profiles[p["category_name"]] = {
                            "big_five": {
                                "openness": p.get("openness_mean", 0.5),
                                "conscientiousness": p.get("conscientiousness_mean", 0.5),
                                "extraversion": p.get("extraversion_mean", 0.5),
                                "agreeableness": p.get("agreeableness_mean", 0.5),
                                "neuroticism": p.get("neuroticism_mean", 0.5),
                            },
                            "sample_size": p.get("sample_size", 0),
                        }
                logger.info(f"Loaded {len(profiles)} category profiles")
            except Exception as e:
                logger.warning(f"Failed to load category profiles: {e}")
    
    def get_category_priors(self, category: str) -> Dict[str, Any]:
        """
        Get psychological priors for a category.
        
        Args:
            category: Amazon category name
        
        Returns:
            Category psychological profile
        """
        # Try exact match
        if category in self._category_profiles:
            return self._category_profiles[category]
        
        # Try normalized match
        normalized = category.replace(" ", "_").replace("&", "and")
        for key, profile in self._category_profiles.items():
            if key.lower() == normalized.lower():
                return profile
        
        # Return default
        return {
            "big_five": {
                "openness": 0.55,
                "conscientiousness": 0.55,
                "extraversion": 0.55,
                "agreeableness": 0.55,
                "neuroticism": 0.50,
            },
            "regulatory_focus": {"promotion": 0.50, "prevention": 0.50},
            "effective_mechanisms": ["social_proof", "authority"],
            "description": "Default profile",
        }
    
    def get_all_categories(self) -> List[str]:
        """Get list of all available categories."""
        return list(self._category_profiles.keys())
    
    def match_archetype(
        self,
        big_five: Dict[str, float],
        categories: Optional[List[str]] = None,
    ) -> Tuple[str, Dict[str, Any], float]:
        """
        Match a user's Big Five profile to the best archetype.
        
        Args:
            big_five: User's Big Five scores
            categories: Categories the user has shown interest in
        
        Returns:
            Tuple of (archetype_id, archetype_data, match_score)
        """
        best_match = None
        best_score = -1
        
        for arch_id, arch in self._archetypes.items():
            arch_big5 = arch["big_five"]
            
            # Compute Big Five similarity (Euclidean distance)
            distance = sum(
                (big_five.get(trait, 0.5) - arch_big5.get(trait, 0.5)) ** 2
                for trait in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
            ) ** 0.5
            
            # Convert to similarity (0-1, higher is better)
            similarity = 1 - (distance / 2.24)  # Max possible distance is sqrt(5) ≈ 2.24
            
            # Category affinity bonus
            if categories:
                category_overlap = len(
                    set(categories) & set(arch.get("category_affinities", []))
                )
                similarity += category_overlap * 0.05
            
            if similarity > best_score:
                best_score = similarity
                best_match = arch_id
        
        return best_match, self._archetypes.get(best_match, {}), min(1.0, max(0.0, best_score))
    
    def get_archetype(self, archetype_id: str) -> Optional[Dict[str, Any]]:
        """Get archetype by ID."""
        return self._archetypes.get(archetype_id)
    
    def get_all_archetypes(self) -> Dict[str, Dict[str, Any]]:
        """Get all archetypes."""
        return self._archetypes
    
    def infer_from_interests(
        self,
        interests: List[str],
    ) -> Dict[str, Any]:
        """
        Infer psychological profile from user interests.
        
        Maps interests to Amazon categories and aggregates priors.
        
        Args:
            interests: List of user interests
        
        Returns:
            Inferred psychological profile
        """
        # Map interests to categories
        interest_to_category = {
            "fashion": "Amazon_Fashion",
            "clothing": "Clothing_Shoes_and_Jewelry",
            "beauty": "Beauty_and_Personal_Care",
            "books": "Books",
            "reading": "Books",
            "music": "Digital_Music",
            "movies": "Movies_and_TV",
            "tv": "Movies_and_TV",
            "food": "Grocery_and_Gourmet_Food",
            "cooking": "Grocery_and_Gourmet_Food",
            "health": "Beauty_and_Personal_Care",
            "fitness": "Beauty_and_Personal_Care",
            "technology": "Kindle_Store",  # Approximation
        }
        
        matched_categories = []
        for interest in interests:
            interest_lower = interest.lower()
            for key, category in interest_to_category.items():
                if key in interest_lower:
                    matched_categories.append(category)
        
        if not matched_categories:
            # Return neutral profile
            return {
                "big_five": {
                    "openness": 0.55,
                    "conscientiousness": 0.55,
                    "extraversion": 0.55,
                    "agreeableness": 0.55,
                    "neuroticism": 0.50,
                },
                "confidence": 0.3,
                "source": "default",
            }
        
        # Aggregate Big Five from matched categories
        big_five_sums = {t: 0.0 for t in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]}
        
        for category in matched_categories:
            priors = self.get_category_priors(category)
            for trait, value in priors.get("big_five", {}).items():
                big_five_sums[trait] += value
        
        count = len(matched_categories)
        big_five = {t: v / count for t, v in big_five_sums.items()}
        
        # Match to archetype
        arch_id, arch_data, arch_score = self.match_archetype(big_five, matched_categories)
        
        return {
            "big_five": big_five,
            "matched_categories": matched_categories,
            "archetype": arch_id,
            "archetype_name": arch_data.get("name", "Unknown"),
            "archetype_match_score": arch_score,
            "effective_mechanisms": arch_data.get("effective_mechanisms", []),
            "confidence": min(0.8, 0.4 + len(matched_categories) * 0.1),
            "source": "amazon_priors",
        }


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_amazon_integration(profiles_dir: Optional[str] = None) -> AmazonIntegrationService:
    """Create Amazon integration service."""
    return AmazonIntegrationService(profiles_dir)


# =============================================================================
# DEMO HELPER FUNCTIONS
# =============================================================================

def get_category_insight(category: str) -> str:
    """Get a human-readable insight about a category's psychology."""
    priors = CATEGORY_PSYCHOLOGY.get(category, {})
    
    if not priors:
        return f"Limited psychological data for {category}"
    
    big5 = priors.get("big_five", {})
    mechanisms = priors.get("effective_mechanisms", [])
    
    # Find dominant trait
    dominant = max(big5.items(), key=lambda x: x[1]) if big5 else ("openness", 0.5)
    
    return (
        f"{category} buyers tend to be high in {dominant[0]} ({dominant[1]:.0%}). "
        f"Effective mechanisms: {', '.join(mechanisms[:3])}. "
        f"{priors.get('description', '')}"
    )


def get_archetype_description(archetype_id: str) -> str:
    """Get human-readable archetype description."""
    arch = AMAZON_ARCHETYPES.get(archetype_id, {})
    
    if not arch:
        return f"Unknown archetype: {archetype_id}"
    
    return (
        f"**{arch['name']}**: {arch['description']}. "
        f"Best mechanisms: {', '.join(arch['effective_mechanisms'][:3])}."
    )


# =============================================================================
# MEDIA-PSYCHOLOGY-PRODUCT TRIANGLE
# =============================================================================

# Import the persuasion engine if available
try:
    from adam.data.amazon.media_product_graph import (
        PersuasionEngine,
        MediaProductGraphBuilder,
        MEDIA_PSYCHOLOGY,
        PRODUCT_PSYCHOLOGY,
        CategoryType,
        CATEGORY_TYPES,
    )
    PERSUASION_ENGINE_AVAILABLE = True
except ImportError:
    PERSUASION_ENGINE_AVAILABLE = False
    MEDIA_PSYCHOLOGY = {}
    PRODUCT_PSYCHOLOGY = {}


class MediaProductPersuasionService:
    """
    Service for cross-domain persuasion based on the Media-Psychology-Product triangle.
    
    Core insight: People's MEDIA consumption reveals their psychology,
    which predicts what PRODUCTS they'll respond to and HOW to persuade them.
    """
    
    def __init__(self):
        if PERSUASION_ENGINE_AVAILABLE:
            self.engine = PersuasionEngine()
        else:
            self.engine = None
    
    def infer_from_radio_format(
        self,
        radio_format: str,
        daypart: str = "morning",
    ) -> Dict[str, Any]:
        """
        Infer psychological profile from radio station format.
        
        Maps radio formats to media consumption patterns:
        - Top 40/Pop → Movies_and_TV, Digital_Music
        - Talk Radio → Books, Kindle_Store, Magazine_Subscriptions
        - Classical → Books, Movies_and_TV (documentary)
        - Country → Movies_and_TV, Magazine_Subscriptions
        - Rock → Digital_Music, Movies_and_TV
        """
        # Map radio format to Amazon media categories
        format_to_media = {
            "pop": ["Digital_Music", "Movies_and_TV"],
            "top_40": ["Digital_Music", "Movies_and_TV"],
            "rock": ["Digital_Music", "Movies_and_TV"],
            "alternative": ["Digital_Music", "Books"],
            "hip_hop": ["Digital_Music", "Movies_and_TV"],
            "r_and_b": ["Digital_Music", "Movies_and_TV"],
            "country": ["Digital_Music", "Magazine_Subscriptions"],
            "classical": ["Books", "Digital_Music"],
            "jazz": ["Books", "Digital_Music"],
            "news_talk": ["Books", "Kindle_Store", "Magazine_Subscriptions"],
            "sports": ["Magazine_Subscriptions", "Movies_and_TV"],
            "podcast": ["Books", "Kindle_Store"],
            "oldies": ["Digital_Music", "Movies_and_TV"],
            "adult_contemporary": ["Digital_Music", "Magazine_Subscriptions"],
        }
        
        # Normalize format
        format_lower = radio_format.lower().replace(" ", "_").replace("-", "_")
        
        # Find matching media categories
        media_categories = []
        for key, categories in format_to_media.items():
            if key in format_lower:
                media_categories.extend(categories)
                break
        
        if not media_categories:
            media_categories = ["Digital_Music", "Movies_and_TV"]
        
        # Dedupe
        media_categories = list(dict.fromkeys(media_categories))
        
        # Use persuasion engine if available
        if self.engine:
            inference = self.engine.infer_from_media(media_categories)
        else:
            # Fallback to manual inference
            inference = self._manual_media_inference(media_categories)
        
        inference["radio_format"] = radio_format
        inference["daypart"] = daypart
        
        return inference
    
    def _manual_media_inference(self, media_categories: List[str]) -> Dict[str, Any]:
        """Fallback inference without the full engine."""
        
        # Aggregate from category priors
        psych_profile = {}
        all_mechanisms = []
        
        for category in media_categories:
            if category in CATEGORY_PSYCHOLOGY:
                cat_profile = CATEGORY_PSYCHOLOGY[category]
                big5 = cat_profile.get("big_five", {})
                for trait, value in big5.items():
                    if trait not in psych_profile:
                        psych_profile[trait] = []
                    psych_profile[trait].append(value)
                
                all_mechanisms.extend(cat_profile.get("effective_mechanisms", []))
        
        # Average traits
        avg_profile = {
            trait: sum(values) / len(values)
            for trait, values in psych_profile.items()
        }
        
        # Dedupe mechanisms
        unique_mechanisms = list(dict.fromkeys(all_mechanisms))
        
        return {
            "media_consumed": media_categories,
            "psychological_profile": avg_profile,
            "media_optimal_mechanisms": unique_mechanisms[:5],
            "confidence": 0.6,
        }
    
    def recommend_product_approach(
        self,
        radio_format: str,
        product_category: str,
    ) -> Dict[str, Any]:
        """
        Given radio format, recommend how to advertise a product.
        
        This is the CORE cross-domain function:
        "User listens to X radio, how do we advertise Y product?"
        """
        # Get media inference from radio format
        media_inference = self.infer_from_radio_format(radio_format)
        media_categories = media_inference.get("media_consumed", [])
        
        if self.engine:
            return self.engine.recommend_product_approach(
                media_categories=media_categories,
                product_category=product_category,
            )
        
        # Fallback recommendation
        product_psych = PRODUCT_PSYCHOLOGY.get(product_category, {})
        
        return {
            "media_profile": media_categories,
            "target_product": product_category,
            "psychological_match": media_inference.get("psychological_profile", {}),
            "recommended_mechanisms": (
                product_psych.get("optimal_mechanisms", [])[:3]
                or media_inference.get("media_optimal_mechanisms", [])[:3]
            ),
            "approach_confidence": media_inference.get("confidence", 0.5),
        }
    
    def get_cross_domain_insight(
        self,
        radio_format: str,
        product_category: str,
    ) -> str:
        """
        Get human-readable cross-domain insight.
        
        For demo display purposes.
        """
        recommendation = self.recommend_product_approach(radio_format, product_category)
        
        mechanisms = recommendation.get("recommended_mechanisms", [])
        confidence = recommendation.get("approach_confidence", 0.5)
        
        return (
            f"Listeners of {radio_format} stations have psychological profiles "
            f"that align with {product_category} through: {', '.join(mechanisms[:3])}. "
            f"(Confidence: {confidence:.0%})"
        )


def create_media_product_service() -> MediaProductPersuasionService:
    """Create the media-product persuasion service."""
    return MediaProductPersuasionService()


# =============================================================================
# DEMO DATA: CROSS-DOMAIN EXAMPLES
# =============================================================================

# Pre-computed examples for demo
CROSS_DOMAIN_EXAMPLES = {
    "pop_beauty": {
        "radio_format": "Top 40/Pop",
        "product_category": "All_Beauty",
        "psychological_link": "High extraversion + identity expression",
        "mechanisms": ["social_proof", "identity_expression", "scarcity"],
        "confidence": 0.78,
        "insight": "Pop listeners value social validation and self-expression - beauty products that emphasize 'trending' and 'be your best self' resonate strongly.",
    },
    "news_talk_books": {
        "radio_format": "News/Talk",
        "product_category": "Kindle_Store",
        "psychological_link": "High need for cognition + openness",
        "mechanisms": ["authority", "intellectual_stimulation", "self_improvement"],
        "confidence": 0.85,
        "insight": "News/talk listeners are information seekers who value expertise - Kindle books marketed through 'expert-recommended' and 'deepen your understanding' messaging are highly effective.",
    },
    "country_grocery": {
        "radio_format": "Country",
        "product_category": "Grocery_and_Gourmet_Food",
        "psychological_link": "Traditionalism + agreeableness + authenticity",
        "mechanisms": ["authenticity", "tradition", "quality", "family"],
        "confidence": 0.72,
        "insight": "Country listeners value authenticity and tradition - food products marketed as 'homemade quality' and 'family recipe' create deep resonance.",
    },
    "rock_fashion": {
        "radio_format": "Rock",
        "product_category": "Clothing_Shoes_and_Jewelry",
        "psychological_link": "High openness + identity expression + rebelliousness",
        "mechanisms": ["identity_expression", "uniqueness", "authenticity"],
        "confidence": 0.68,
        "insight": "Rock listeners value self-expression and standing out - fashion that emphasizes 'express yourself' and 'limited edition' connects strongly.",
    },
    "classical_food": {
        "radio_format": "Classical",
        "product_category": "Grocery_and_Gourmet_Food",
        "psychological_link": "High openness + quality sensitivity + sophistication",
        "mechanisms": ["quality", "expertise", "exclusivity", "authenticity"],
        "confidence": 0.75,
        "insight": "Classical listeners appreciate refinement and quality - gourmet products marketed as 'artisanal' and 'curated selection' align perfectly.",
    },
}
