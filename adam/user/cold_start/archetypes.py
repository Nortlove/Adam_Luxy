# =============================================================================
# ADAM User Archetypes
# Location: adam/user/cold_start/archetypes.py
# =============================================================================

"""
USER ARCHETYPES

Psychological archetypes derived from Amazon review corpus.
These provide cold-start priors for new users.

Based on clustering of 100M+ Amazon reviewers across:
- Linguistic patterns → Big Five
- Category preferences → Lifestyle
- Rating patterns → Decision style
- Review timing → Engagement level
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field


# =============================================================================
# ARCHETYPE MODELS
# =============================================================================

class ArchetypeCategory(str, Enum):
    """Primary archetype categories."""
    
    EXPLORER = "explorer"         # High openness, novelty-seeking
    ACHIEVER = "achiever"         # High conscientiousness, goal-oriented
    CONNECTOR = "connector"       # High extraversion, social-focused
    GUARDIAN = "guardian"         # High agreeableness, value-driven
    ANALYZER = "analyzer"         # High need for cognition, detail-oriented
    PRAGMATIST = "pragmatist"     # Balanced, practical
    ENTHUSIAST = "enthusiast"     # High emotional engagement
    MINIMALIST = "minimalist"     # Low complexity preference


class BigFivePrior(BaseModel):
    """Big Five personality prior with uncertainty."""
    
    openness: float = Field(ge=0.0, le=1.0, default=0.5)
    openness_std: float = Field(ge=0.0, le=0.5, default=0.15)
    
    conscientiousness: float = Field(ge=0.0, le=1.0, default=0.5)
    conscientiousness_std: float = Field(ge=0.0, le=0.5, default=0.15)
    
    extraversion: float = Field(ge=0.0, le=1.0, default=0.5)
    extraversion_std: float = Field(ge=0.0, le=0.5, default=0.15)
    
    agreeableness: float = Field(ge=0.0, le=1.0, default=0.5)
    agreeableness_std: float = Field(ge=0.0, le=0.5, default=0.15)
    
    neuroticism: float = Field(ge=0.0, le=1.0, default=0.5)
    neuroticism_std: float = Field(ge=0.0, le=0.5, default=0.15)


class MechanismPrior(BaseModel):
    """Mechanism effectiveness prior."""
    
    mechanism_name: str
    effectiveness: float = Field(ge=0.0, le=1.0, default=0.5)
    confidence: float = Field(ge=0.0, le=1.0, default=0.3)


class UserArchetype(BaseModel):
    """A user archetype with psychological priors."""
    
    archetype_id: str
    category: ArchetypeCategory
    name: str
    description: str
    
    # Population statistics
    population_percentage: float = Field(
        ge=0.0, le=1.0,
        description="Percentage of population in this archetype"
    )
    
    # Psychological priors
    big_five: BigFivePrior
    
    # Regulatory focus tendency
    promotion_tendency: float = Field(ge=0.0, le=1.0, default=0.5)
    prevention_tendency: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Construal level tendency
    abstract_tendency: float = Field(
        ge=0.0, le=1.0, default=0.5,
        description="0=concrete, 1=abstract"
    )
    
    # Mechanism effectiveness priors
    mechanism_priors: List[MechanismPrior] = Field(default_factory=list)
    
    # Category affinities
    category_affinities: Dict[str, float] = Field(default_factory=dict)
    
    # Matching signals (what indicates this archetype)
    matching_signals: Dict[str, Any] = Field(default_factory=dict)


class ArchetypeMatch(BaseModel):
    """Result of matching a user to archetypes."""
    
    user_id: str
    
    # Primary match
    primary_archetype: UserArchetype
    primary_confidence: float = Field(ge=0.0, le=1.0)
    
    # Secondary matches
    secondary_archetypes: List[tuple] = Field(
        default_factory=list,
        description="List of (archetype_id, confidence) tuples"
    )
    
    # Blended profile
    blended_big_five: BigFivePrior
    blended_mechanism_priors: Dict[str, float] = Field(default_factory=dict)
    
    # Matching evidence
    matching_signals_used: List[str] = Field(default_factory=list)
    
    # Metadata
    matched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    data_tier: str = Field(default="cold_start")


# =============================================================================
# DEFAULT AMAZON ARCHETYPES
# =============================================================================

AMAZON_ARCHETYPES = {
    "explorer": UserArchetype(
        archetype_id="arch_explorer",
        category=ArchetypeCategory.EXPLORER,
        name="The Explorer",
        description="Novelty-seeking, high openness, tries new products and categories",
        population_percentage=0.15,
        big_five=BigFivePrior(
            openness=0.78, openness_std=0.12,
            conscientiousness=0.45, conscientiousness_std=0.18,
            extraversion=0.62, extraversion_std=0.15,
            agreeableness=0.55, agreeableness_std=0.15,
            neuroticism=0.42, neuroticism_std=0.18,
        ),
        promotion_tendency=0.72,
        prevention_tendency=0.28,
        abstract_tendency=0.65,
        mechanism_priors=[
            MechanismPrior(mechanism_name="curiosity", effectiveness=0.75, confidence=0.6),
            MechanismPrior(mechanism_name="novelty", effectiveness=0.72, confidence=0.6),
            MechanismPrior(mechanism_name="social_proof", effectiveness=0.45, confidence=0.5),
        ],
        category_affinities={
            "electronics": 0.75,
            "books": 0.70,
            "outdoor": 0.65,
            "travel": 0.68,
        },
        matching_signals={
            "category_diversity": "> 8 categories",
            "new_brand_rate": "> 40%",
            "review_detail": "medium-high",
        },
    ),
    
    "achiever": UserArchetype(
        archetype_id="arch_achiever",
        category=ArchetypeCategory.ACHIEVER,
        name="The Achiever",
        description="Goal-oriented, high conscientiousness, values quality and efficiency",
        population_percentage=0.18,
        big_five=BigFivePrior(
            openness=0.55, openness_std=0.15,
            conscientiousness=0.82, conscientiousness_std=0.10,
            extraversion=0.58, extraversion_std=0.15,
            agreeableness=0.48, agreeableness_std=0.15,
            neuroticism=0.35, neuroticism_std=0.15,
        ),
        promotion_tendency=0.68,
        prevention_tendency=0.32,
        abstract_tendency=0.45,
        mechanism_priors=[
            MechanismPrior(mechanism_name="achievement", effectiveness=0.78, confidence=0.65),
            MechanismPrior(mechanism_name="efficiency", effectiveness=0.72, confidence=0.6),
            MechanismPrior(mechanism_name="quality", effectiveness=0.70, confidence=0.6),
        ],
        category_affinities={
            "productivity": 0.80,
            "fitness": 0.72,
            "business": 0.75,
            "home_office": 0.70,
        },
        matching_signals={
            "rating_consistency": "high",
            "review_structure": "organized",
            "purchase_timing": "planned",
        },
    ),
    
    "connector": UserArchetype(
        archetype_id="arch_connector",
        category=ArchetypeCategory.CONNECTOR,
        name="The Connector",
        description="Social-focused, high extraversion, influenced by others",
        population_percentage=0.14,
        big_five=BigFivePrior(
            openness=0.60, openness_std=0.15,
            conscientiousness=0.50, conscientiousness_std=0.18,
            extraversion=0.82, extraversion_std=0.10,
            agreeableness=0.68, agreeableness_std=0.12,
            neuroticism=0.48, neuroticism_std=0.18,
        ),
        promotion_tendency=0.65,
        prevention_tendency=0.35,
        abstract_tendency=0.40,
        mechanism_priors=[
            MechanismPrior(mechanism_name="social_proof", effectiveness=0.82, confidence=0.7),
            MechanismPrior(mechanism_name="mimetic_desire", effectiveness=0.75, confidence=0.65),
            MechanismPrior(mechanism_name="belonging", effectiveness=0.70, confidence=0.6),
        ],
        category_affinities={
            "fashion": 0.72,
            "beauty": 0.68,
            "entertainment": 0.75,
            "gifts": 0.70,
        },
        matching_signals={
            "helpful_vote_ratio": "high",
            "social_references": "frequent",
            "gift_purchases": "> 20%",
        },
    ),
    
    "guardian": UserArchetype(
        archetype_id="arch_guardian",
        category=ArchetypeCategory.GUARDIAN,
        name="The Guardian",
        description="Value-driven, high agreeableness, protective and caring",
        population_percentage=0.16,
        big_five=BigFivePrior(
            openness=0.45, openness_std=0.18,
            conscientiousness=0.65, conscientiousness_std=0.15,
            extraversion=0.48, extraversion_std=0.18,
            agreeableness=0.78, agreeableness_std=0.10,
            neuroticism=0.52, neuroticism_std=0.15,
        ),
        promotion_tendency=0.38,
        prevention_tendency=0.62,
        abstract_tendency=0.35,
        mechanism_priors=[
            MechanismPrior(mechanism_name="safety", effectiveness=0.78, confidence=0.65),
            MechanismPrior(mechanism_name="trust", effectiveness=0.75, confidence=0.65),
            MechanismPrior(mechanism_name="loss_aversion", effectiveness=0.72, confidence=0.6),
        ],
        category_affinities={
            "baby": 0.75,
            "health": 0.72,
            "home_safety": 0.70,
            "family": 0.78,
        },
        matching_signals={
            "safety_mentions": "frequent",
            "brand_loyalty": "high",
            "negative_review_focus": "protection",
        },
    ),
    
    "analyzer": UserArchetype(
        archetype_id="arch_analyzer",
        category=ArchetypeCategory.ANALYZER,
        name="The Analyzer",
        description="Detail-oriented, high need for cognition, research-driven",
        population_percentage=0.12,
        big_five=BigFivePrior(
            openness=0.68, openness_std=0.12,
            conscientiousness=0.72, conscientiousness_std=0.12,
            extraversion=0.38, extraversion_std=0.18,
            agreeableness=0.52, agreeableness_std=0.15,
            neuroticism=0.45, neuroticism_std=0.18,
        ),
        promotion_tendency=0.48,
        prevention_tendency=0.52,
        abstract_tendency=0.55,
        mechanism_priors=[
            MechanismPrior(mechanism_name="information", effectiveness=0.82, confidence=0.7),
            MechanismPrior(mechanism_name="comparison", effectiveness=0.78, confidence=0.65),
            MechanismPrior(mechanism_name="authority", effectiveness=0.65, confidence=0.55),
        ],
        category_affinities={
            "electronics": 0.78,
            "books": 0.75,
            "tools": 0.70,
            "software": 0.72,
        },
        matching_signals={
            "review_length": "long",
            "technical_detail": "high",
            "comparison_mentions": "frequent",
        },
    ),
    
    "pragmatist": UserArchetype(
        archetype_id="arch_pragmatist",
        category=ArchetypeCategory.PRAGMATIST,
        name="The Pragmatist",
        description="Balanced, practical, value-for-money focused",
        population_percentage=0.20,
        big_five=BigFivePrior(
            openness=0.50, openness_std=0.15,
            conscientiousness=0.58, conscientiousness_std=0.15,
            extraversion=0.52, extraversion_std=0.15,
            agreeableness=0.55, agreeableness_std=0.15,
            neuroticism=0.48, neuroticism_std=0.15,
        ),
        promotion_tendency=0.50,
        prevention_tendency=0.50,
        abstract_tendency=0.45,
        mechanism_priors=[
            MechanismPrior(mechanism_name="value", effectiveness=0.75, confidence=0.65),
            MechanismPrior(mechanism_name="utility", effectiveness=0.72, confidence=0.6),
            MechanismPrior(mechanism_name="convenience", effectiveness=0.68, confidence=0.55),
        ],
        category_affinities={
            "household": 0.72,
            "grocery": 0.70,
            "automotive": 0.68,
            "office": 0.65,
        },
        matching_signals={
            "price_mentions": "frequent",
            "value_focus": "high",
            "rating_distribution": "balanced",
        },
    ),
}
