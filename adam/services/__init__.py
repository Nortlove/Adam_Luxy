# =============================================================================
# ADAM Services Package
# Location: adam/services/__init__.py
# =============================================================================

"""
ADAM Services Package

This package provides core business services for the ADAM system.

Services:
- BrandLibraryService: Brand intelligence and positioning
- CompetitiveIntelService: Competitive landscape analysis
- TemporalPatternsService: Temporal pattern analysis
- ArchetypeService: Archetype-based fast path decisions
- BanditService: Thompson Sampling for exploration/exploitation
"""

from adam.services.brand_library import (
    BrandLibraryService,
    BrandProfile,
    BrandVoice,
    get_brand_library_service,
)
from adam.services.competitive_intel import (
    CompetitiveIntelService,
    CompetitiveLandscape,
    CompetitorProfile,
    get_competitive_intel_service,
)
from adam.services.temporal_patterns import (
    TemporalPatternsService,
    TemporalPatternProfile,
    DayPeriod,
    Chronotype,
    get_temporal_patterns_service,
)
from adam.services.archetype_service import (
    ArchetypeService,
    CustomerArchetype,
    ArchetypeOutputs,
    get_archetype_service,
)
from adam.services.bandit_service import (
    BanditService,
    BanditDecision,
    BetaDistribution,
    get_bandit_service,
)

__all__ = [
    # Brand Library
    "BrandLibraryService",
    "BrandProfile",
    "BrandVoice",
    "get_brand_library_service",
    # Competitive Intel
    "CompetitiveIntelService",
    "CompetitiveLandscape",
    "CompetitorProfile",
    "get_competitive_intel_service",
    # Temporal Patterns
    "TemporalPatternsService",
    "TemporalPatternProfile",
    "DayPeriod",
    "Chronotype",
    "get_temporal_patterns_service",
    # Archetype
    "ArchetypeService",
    "CustomerArchetype",
    "ArchetypeOutputs",
    "get_archetype_service",
    # Bandit
    "BanditService",
    "BanditDecision",
    "BetaDistribution",
    "get_bandit_service",
]
