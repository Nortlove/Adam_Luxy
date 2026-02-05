# =============================================================================
# ADAM Competitive Intelligence Module
# Location: adam/competitive/__init__.py
# =============================================================================

"""
COMPETITIVE INTELLIGENCE MODULE

Analyzes competitor advertising and recommends counter-strategies.

Features:
- Competitor ad analysis pipeline
- Mechanism detection from competitor ads
- Counter-strategy engine
- Game theory module for optimal response
- Psychological vulnerability mapping
"""

from .intelligence import (
    CompetitiveIntelligenceService,
    CompetitorAnalysis,
    CompetitiveIntelligence,
    CounterStrategy,
    Vulnerability,
    get_competitive_intelligence_service,
    analyze_competitor,
    get_counter_strategies,
)

__all__ = [
    "CompetitiveIntelligenceService",
    "CompetitorAnalysis",
    "CompetitiveIntelligence",
    "CounterStrategy",
    "Vulnerability",
    "get_competitive_intelligence_service",
    "analyze_competitor",
    "get_counter_strategies",
]
