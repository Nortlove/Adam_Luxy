# =============================================================================
# ADAM Learning System
# =============================================================================

"""
ADAM Learning System (CONVENIENCE AGGREGATOR — see role below)

ROLE PER G1 LANDSCAPE DOC: this package is a thin convenience
aggregator. It re-exports from cold-start, user-cold-start, and
archetype modules so callers can reach multiple surfaces with one
import. Do NOT add new logic here.

For new learning code:
  - Production runtime: adam.core.learning (CANONICAL)
  - Cold-start gradient bridge: adam.cold_start.learning
  - Offline corpus learning scripts: adam.intelligence.learning

See adam/core/learning/__init__.py for the full four-package
landscape documentation.

Convenience imports below (kept for backwards compat):
    from adam.coldstart.unified_learning import UnifiedColdStartLearning
    from adam.user.cold_start.service import ColdStartService
    from adam.user.cold_start.archetypes import AMAZON_ARCHETYPES
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
