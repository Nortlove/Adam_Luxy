# =============================================================================
# ADAM Enhancement #13: Cold Start Models Package
# Location: adam/cold_start/models/__init__.py
# =============================================================================

"""
Cold Start Strategy Data Models

This package contains all Pydantic models for the Cold Start Strategy:

Enums:
- UserDataTier: Classification of users by data richness (6 tiers)
- PriorSource: Where priors come from in the hierarchy
- ArchetypeID: 8 research-grounded psychological archetypes
- CognitiveMechanism: 9 cognitive mechanisms for persuasion
- ColdStartStrategy: Which approach to use based on tier

User Models:
- UserDataInventory: What data we have about a user
- UserInteractionStats: Behavioral density metrics
- UserDataProfile: Complete profile for tier classification
- UserTierClassifier: Configurable tier classifier

Prior Models:
- BetaDistribution: For mechanism effectiveness (conjugate to Bernoulli)
- GaussianDistribution: For personality traits
- TraitPrior: Prior for a single trait
- MechanismPrior: Prior for mechanism effectiveness
- PsychologicalPrior: Complete psychological prior
- HierarchicalPrior: Multi-level prior combination

Archetype Models:
- ArchetypeTraitProfile: Big Five profile for an archetype
- ArchetypeMechanismProfile: Mechanism effectiveness for archetype
- ArchetypeDefinition: Complete archetype definition
- ArchetypeMatchResult: Result of archetype matching

Decision Models:
- ColdStartDecision: Output of cold start strategy selection
- TierTransitionEvent: User tier transition event
- ProfileVelocityMetrics: Profile development tracking
- ColdStartOutcome: Decision outcome for learning
"""

# Enums
from .enums import (
    UserDataTier,
    PriorSource,
    ArchetypeID,
    CognitiveMechanism,
    PersonalityTrait,
    ExtendedConstruct,
    ColdStartStrategy,
)

# User models
from .user import (
    UserDataInventory,
    UserInteractionStats,
    UserDataProfile,
    UserTierClassifier,
)

# Prior models
from .priors import (
    BetaDistribution,
    GaussianDistribution,
    TraitPrior,
    MechanismPrior,
    PsychologicalPrior,
    HierarchicalPrior,
)

# Archetype models
from .archetypes import (
    ArchetypeTraitProfile,
    ArchetypeMechanismProfile,
    ArchetypeDefinition,
    ArchetypeMatchResult,
)

# Decision models
from .decisions import (
    ColdStartDecision,
    TierTransitionEvent,
    ProfileVelocityMetrics,
    ColdStartOutcome,
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
]
