# =============================================================================
# ADAM Enhancement #13: Core Enums & Types
# Location: adam/cold_start/models/enums.py
# =============================================================================

"""
Core enumerations and type definitions for Cold Start Strategy.

These define the fundamental classification system for:
- User data tiers (how much data we have)
- Prior sources (where priors come from)
- Psychological archetypes (behavioral clusters)
- Cognitive mechanisms (persuasion strategies)
- Cold start strategies (which approach to use)
"""

from __future__ import annotations
from enum import Enum


class UserDataTier(str, Enum):
    """
    Classification of users by available data richness.
    
    Each tier determines which cold start strategy to apply and
    what prior sources are available.
    
    75% of traffic is in Tiers 0-4 (cold start territory).
    Only 25% reach Tier 5 (full psychological profile).
    """
    # Tier 0: First pageview - no data at all
    TIER_0_ANONYMOUS_NEW = "tier_0_anonymous_new"
    
    # Tier 1: Has session behavior (clicks, scrolls, time on page)
    TIER_1_ANONYMOUS_SESSION = "tier_1_anonymous_session"
    
    # Tier 2: Registered with demographics only
    TIER_2_REGISTERED_MINIMAL = "tier_2_registered_minimal"
    
    # Tier 3: Some behavioral history (5-20 interactions)
    TIER_3_REGISTERED_SPARSE = "tier_3_registered_sparse"
    
    # Tier 4: Moderate history (20-50 interactions)
    TIER_4_REGISTERED_MODERATE = "tier_4_registered_moderate"
    
    # Tier 5: Full psychological profile available
    TIER_5_PROFILED_FULL = "tier_5_profiled_full"
    
    @property
    def is_cold_start(self) -> bool:
        """Whether this tier requires cold start strategies."""
        return self != UserDataTier.TIER_5_PROFILED_FULL
    
    @property
    def tier_number(self) -> int:
        """Numeric tier for comparison."""
        tier_map = {
            UserDataTier.TIER_0_ANONYMOUS_NEW: 0,
            UserDataTier.TIER_1_ANONYMOUS_SESSION: 1,
            UserDataTier.TIER_2_REGISTERED_MINIMAL: 2,
            UserDataTier.TIER_3_REGISTERED_SPARSE: 3,
            UserDataTier.TIER_4_REGISTERED_MODERATE: 4,
            UserDataTier.TIER_5_PROFILED_FULL: 5,
        }
        return tier_map[self]


class PriorSource(str, Enum):
    """
    Source of prior distribution in the hierarchical system.
    
    Order of specificity (least to most):
    1. POPULATION - Global population from Amazon corpus
    2. CLUSTER - Psychological cluster priors
    3. DEMOGRAPHIC - Age/gender/location priors
    4. CONTEXTUAL - Content/time/device priors
    5. ARCHETYPE - Matched archetype priors
    6. HISTORICAL_USER - User's own history (most specific)
    """
    POPULATION = "population"           # Global population from Amazon corpus
    CLUSTER = "cluster"                 # Psychological cluster priors
    DEMOGRAPHIC = "demographic"         # Age/gender/location priors
    CONTEXTUAL = "contextual"           # Content/time/device priors
    ARCHETYPE = "archetype"             # Matched archetype priors
    CATEGORY = "category"               # Product category priors
    BRAND = "brand"                     # Brand-specific priors
    HISTORICAL_USER = "historical_user" # User's own history


class ArchetypeID(str, Enum):
    """
    Research-grounded psychological archetypes.
    
    Based on Jung's psychological types, validated through
    Big Five research and advertising response studies.
    
    Each archetype has:
    - Big Five profile (mean + variance)
    - Regulatory focus distribution
    - Mechanism effectiveness Beta priors
    - Construal level tendency
    - Value hierarchy
    """
    EXPLORER = "explorer"           # High Openness, Promotion-focused
    ACHIEVER = "achiever"           # High Conscientiousness, Goal-oriented
    CONNECTOR = "connector"         # High Extraversion + Agreeableness
    GUARDIAN = "guardian"           # High Neuroticism, Prevention-focused
    ANALYST = "analyst"             # High Conscientiousness + Openness, Low E
    CREATOR = "creator"             # High Openness, Low Conscientiousness
    NURTURER = "nurturer"           # High Agreeableness, Community-oriented
    PRAGMATIST = "pragmatist"       # Balanced traits, Practical focus


class CognitiveMechanism(str, Enum):
    """
    The 9 cognitive mechanisms for persuasion.
    
    Each mechanism has effectiveness priors that vary by user.
    Thompson Sampling selects mechanisms based on these priors.
    """
    CONSTRUAL_LEVEL = "construal_level"
    REGULATORY_FOCUS = "regulatory_focus"
    AUTOMATIC_EVALUATION = "automatic_evaluation"
    WANTING_LIKING = "wanting_liking"
    MIMETIC_DESIRE = "mimetic_desire"
    ATTENTION_DYNAMICS = "attention_dynamics"
    TEMPORAL_CONSTRUAL = "temporal_construal"
    IDENTITY_CONSTRUCTION = "identity_construction"
    EVOLUTIONARY_MOTIVE = "evolutionary_motive"


class PersonalityTrait(str, Enum):
    """Big Five personality traits."""
    OPENNESS = "openness"
    CONSCIENTIOUSNESS = "conscientiousness"
    EXTRAVERSION = "extraversion"
    AGREEABLENESS = "agreeableness"
    NEUROTICISM = "neuroticism"


class ExtendedConstruct(str, Enum):
    """Extended psychological constructs beyond Big Five."""
    REGULATORY_FOCUS_PROMOTION = "regulatory_focus_promotion"
    REGULATORY_FOCUS_PREVENTION = "regulatory_focus_prevention"
    NEED_FOR_COGNITION = "need_for_cognition"
    SELF_MONITORING = "self_monitoring"
    MAXIMIZING_TENDENCY = "maximizing_tendency"
    RISK_TOLERANCE = "risk_tolerance"


class ColdStartStrategy(str, Enum):
    """
    Strategy applied for cold start inference.
    
    Selected based on user's data tier and available signals.
    """
    POPULATION_PRIOR_ONLY = "population_prior_only"     # Tier 0
    CONTEXTUAL_INFERENCE = "contextual_inference"       # Tier 1
    DEMOGRAPHIC_PRIOR = "demographic_prior"             # Tier 2
    ARCHETYPE_MATCH = "archetype_match"                 # Tier 3
    PROGRESSIVE_BAYESIAN = "progressive_bayesian"       # Tier 4
    FULL_PROFILE = "full_profile"                       # Tier 5
