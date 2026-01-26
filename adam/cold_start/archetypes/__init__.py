# =============================================================================
# ADAM Enhancement #13: Archetypes Package
# Location: adam/cold_start/archetypes/__init__.py
# =============================================================================

"""
Psychological Archetype System

8 research-grounded archetypes for cold start profiling:
- Explorer: High Openness, Promotion-focused
- Achiever: High Conscientiousness, Goal-oriented
- Connector: High Extraversion + Agreeableness
- Guardian: High Neuroticism, Prevention-focused
- Analyst: High C + O, Low Extraversion
- Creator: High Openness, Low Conscientiousness
- Nurturer: High Agreeableness, Community-oriented
- Pragmatist: Balanced traits, Practical focus

Each archetype has:
- Big Five trait profile
- Mechanism effectiveness priors
- Message frame preferences
"""

from .definitions import (
    ARCHETYPE_TRAIT_PROFILES,
    ARCHETYPE_MECHANISM_PRIORS,
    ARCHETYPE_MESSAGE_PREFERENCES,
    ARCHETYPE_DEFINITIONS,
    build_archetype_definitions,
    get_archetype,
    get_all_archetypes,
)

from .detector import (
    ArchetypeDetector,
    get_archetype_detector,
)

__all__ = [
    # Definitions
    "ARCHETYPE_TRAIT_PROFILES",
    "ARCHETYPE_MECHANISM_PRIORS",
    "ARCHETYPE_MESSAGE_PREFERENCES",
    "ARCHETYPE_DEFINITIONS",
    "build_archetype_definitions",
    "get_archetype",
    "get_all_archetypes",
    
    # Detector
    "ArchetypeDetector",
    "get_archetype_detector",
]
