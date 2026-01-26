# =============================================================================
# ADAM Cold Start Strategy (#13)
# =============================================================================

"""
COLD START STRATEGY

Bootstrap new users from Amazon archetypes and platform priors.

This module provides:
- Archetype matching from minimal signals
- Progressive profile enrichment
- Prior injection for cold-start reasoning
"""

from adam.user.cold_start.archetypes import (
    UserArchetype,
    ArchetypeMatch,
    AMAZON_ARCHETYPES,
)
from adam.user.cold_start.service import ColdStartService

__all__ = [
    "UserArchetype",
    "ArchetypeMatch",
    "AMAZON_ARCHETYPES",
    "ColdStartService",
]
