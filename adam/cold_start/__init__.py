# =============================================================================
# ADAM Enhancement #13: Cold Start Strategy
# Location: adam/cold_start/__init__.py
# =============================================================================

"""
COLD START STRATEGY

Enterprise-Grade Bayesian Profiling with Hierarchical Priors & Thompson Sampling

Serves 75% of traffic (new/sparse users) with:

1. HIERARCHICAL PRIORS
   - Population: Global from Amazon corpus (least specific)
   - Cluster: Psychological cluster priors
   - Demographic: Age/gender/location adjusted
   - Contextual: Content/time/device priors
   - Archetype: Matched archetype priors (most specific)

2. PSYCHOLOGICAL ARCHETYPES (8 research-grounded)
   - Explorer: High Openness, Promotion-focused
   - Achiever: High Conscientiousness, Goal-oriented
   - Connector: High Extraversion + Agreeableness
   - Guardian: High Neuroticism, Prevention-focused
   - Analyst: High C + O, Low Extraversion
   - Creator: High Openness, Low Conscientiousness
   - Nurturer: High Agreeableness, Community-oriented
   - Pragmatist: Balanced traits, Practical focus

3. THOMPSON SAMPLING
   - Beta posteriors for mechanism effectiveness
   - Exploration bonus for uncertain mechanisms
   - Outcome-based posterior updates

4. PROGRESSIVE PROFILING
   - Bayesian updates with conjugate priors
   - 6 user data tiers (0-5)
   - Tier transition tracking

Expected Performance:
- Cold user CTR: 1.3x vs random baseline
- Time to full profile: <14 days median
- Inference latency: <50ms p99
"""

# Models
from adam.cold_start.models import (
    # Enums
    UserDataTier,
    PriorSource,
    ArchetypeID,
    CognitiveMechanism,
    PersonalityTrait,
    ExtendedConstruct,
    ColdStartStrategy,
    
    # User models
    UserDataInventory,
    UserInteractionStats,
    UserDataProfile,
    UserTierClassifier,
    
    # Prior models
    BetaDistribution,
    GaussianDistribution,
    TraitPrior,
    MechanismPrior,
    PsychologicalPrior,
    HierarchicalPrior,
    
    # Archetype models
    ArchetypeTraitProfile,
    ArchetypeMechanismProfile,
    ArchetypeDefinition,
    ArchetypeMatchResult,
    
    # Decision models
    ColdStartDecision,
    TierTransitionEvent,
    ProfileVelocityMetrics,
    ColdStartOutcome,
)

# Archetypes
from adam.cold_start.archetypes import (
    ARCHETYPE_DEFINITIONS,
    get_archetype,
    get_all_archetypes,
    ArchetypeDetector,
    get_archetype_detector,
)

# Priors
from adam.cold_start.priors import (
    PopulationPriorEngine,
    get_population_prior_engine,
    DemographicPriorEngine,
    get_demographic_prior_engine,
)

# Thompson Sampling
from adam.cold_start.thompson import (
    ThompsonSampler,
    get_thompson_sampler,
)

# Main Service
from adam.cold_start.service import (
    ColdStartService,
    get_cold_start_service,
)

# Cache
from adam.cold_start.cache import (
    PriorCache,
    PriorCacheConfig,
    get_prior_cache,
)

# Events
from adam.cold_start.events import (
    ColdStartEventType,
    ColdStartEvent,
    DecisionMadeEvent,
    TierTransitionEvent,
    OutcomeReceivedEvent,
    ColdStartEventPublisher,
    get_event_publisher,
)

# Learning
from adam.cold_start.learning import (
    ColdStartLearningSignal,
    ColdStartGradientBridge,
    get_cold_start_gradient_bridge,
)

__all__ = [
    # Enums
    "UserDataTier",
    "PriorSource",
    "ArchetypeID",
    "CognitiveMechanism",
    "PersonalityTrait",
    "ExtendedConstruct",
    "ColdStartStrategy",
    
    # User models
    "UserDataInventory",
    "UserInteractionStats",
    "UserDataProfile",
    "UserTierClassifier",
    
    # Prior models
    "BetaDistribution",
    "GaussianDistribution",
    "TraitPrior",
    "MechanismPrior",
    "PsychologicalPrior",
    "HierarchicalPrior",
    
    # Archetype models
    "ArchetypeTraitProfile",
    "ArchetypeMechanismProfile",
    "ArchetypeDefinition",
    "ArchetypeMatchResult",
    
    # Decision models
    "ColdStartDecision",
    "TierTransitionEvent",
    "ProfileVelocityMetrics",
    "ColdStartOutcome",
    
    # Archetypes
    "ARCHETYPE_DEFINITIONS",
    "get_archetype",
    "get_all_archetypes",
    "ArchetypeDetector",
    "get_archetype_detector",
    
    # Priors
    "PopulationPriorEngine",
    "get_population_prior_engine",
    "DemographicPriorEngine",
    "get_demographic_prior_engine",
    
    # Thompson Sampling
    "ThompsonSampler",
    "get_thompson_sampler",
    
    # Main Service
    "ColdStartService",
    "get_cold_start_service",
    
    # Cache
    "PriorCache",
    "PriorCacheConfig",
    "get_prior_cache",
    
    # Events
    "ColdStartEventType",
    "ColdStartEvent",
    "DecisionMadeEvent",
    "TierTransitionEvent",
    "OutcomeReceivedEvent",
    "ColdStartEventPublisher",
    "get_event_publisher",
    
    # Learning
    "ColdStartLearningSignal",
    "ColdStartGradientBridge",
    "get_cold_start_gradient_bridge",
]
