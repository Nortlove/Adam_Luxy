# =============================================================================
# ADAM Campaign Orchestrator
# Location: adam/orchestrator/__init__.py
# =============================================================================

"""
ADAM Campaign Orchestrator

The unified entry point for campaign analysis that coordinates ALL ADAM services:
- Review Intelligence (scraping + psychological analysis)
- Neo4j Graph Queries (mechanisms, archetypes, synergies)
- AtomDAG Execution (atom of thought reasoning)
- MetaLearner (Thompson Sampling mechanism selection)
- ColdStart (archetype priors)
- Blackboard (shared state)
- Learning Systems (feedback and improvement)

This replaces the mock demo logic with REAL system intelligence.
"""

from adam.orchestrator.campaign_orchestrator import (
    CampaignOrchestrator,
    get_campaign_orchestrator,
)
from adam.orchestrator.models import (
    CampaignAnalysisResult,
    ReasoningTrace,
    DataSourceInfo,
    GraphQueryResult,
    AtomExecutionResult,
    MechanismSelectionResult,
    SegmentRecommendation,
)

__all__ = [
    "CampaignOrchestrator",
    "get_campaign_orchestrator",
    "CampaignAnalysisResult",
    "ReasoningTrace",
    "DataSourceInfo",
    "GraphQueryResult",
    "AtomExecutionResult",
    "MechanismSelectionResult",
    "SegmentRecommendation",
]
