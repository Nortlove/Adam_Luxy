# =============================================================================
# LEGACY RE-EXPORT SHIM
# Location: adam/coldstart/unified_learning.py
#
# The authoritative module is adam/cold_start/unified_learning.py.
# This file exists because 5 importers reference the legacy path
# (adam.coldstart.unified_learning). Redirect so both paths resolve
# to the same module objects — prevents singleton state divergence
# and ensures edits to one file are visible everywhere.
# =============================================================================

from adam.cold_start.unified_learning import (  # noqa: F401
    Archetype,
    ArchetypeEffectiveness,
    ColdStartPrediction,
    PersonalityInferenceAccuracy,
    TierTransition,
    UnifiedColdStartLearning,
    UserTier,
)

__all__ = [
    "Archetype",
    "ArchetypeEffectiveness",
    "ColdStartPrediction",
    "PersonalityInferenceAccuracy",
    "TierTransition",
    "UnifiedColdStartLearning",
    "UserTier",
]
