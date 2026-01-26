# =============================================================================
# ADAM Learning System
# =============================================================================

"""
ADAM Learning System

The learning system builds understanding from data through the unified
learning interface defined in Enhancement #13.

For Amazon data processing, use:
    from adam.data.amazon import AmazonPipeline, PipelineConfig
    
For Cold Start learning, use:
    from adam.coldstart.unified_learning import UnifiedColdStartLearning
    
For Thompson Sampling, use:
    from adam.meta_learner.thompson import ThompsonSamplingEngine
"""

# Re-export from proper locations
from adam.coldstart.unified_learning import UnifiedColdStartLearning
from adam.user.cold_start.service import ColdStartService
from adam.user.cold_start.archetypes import AMAZON_ARCHETYPES

# Emergence Engine - autonomous intelligence discovery
from adam.learning.emergence_engine import (
    EmergenceEngine,
    HypothesisGenerator,
    HypothesisType,
    HypothesisStatus,
    DiscoveredPattern,
    GeneratedHypothesis,
    EmergenceResult,
    get_emergence_engine,
)

# Mechanism Interaction Learning
from adam.learning.mechanism_interactions import (
    MechanismInteractionLearner,
    LearnedInteraction,
    InteractionType,
    MechanismPair,
    InteractionObservation,
    InteractionMatrix,
)

__all__ = [
    "UnifiedColdStartLearning",
    "ColdStartService",
    "AMAZON_ARCHETYPES",
    # Emergence Engine
    "EmergenceEngine",
    "HypothesisGenerator",
    "HypothesisType",
    "HypothesisStatus",
    "DiscoveredPattern",
    "GeneratedHypothesis",
    "EmergenceResult",
    "get_emergence_engine",
    # Mechanism Interactions
    "MechanismInteractionLearner",
    "LearnedInteraction",
    "InteractionType",
    "MechanismPair",
    "InteractionObservation",
    "InteractionMatrix",
]
