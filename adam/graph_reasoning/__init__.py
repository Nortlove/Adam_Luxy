# =============================================================================
# ADAM Graph Reasoning - Bidirectional Fusion (#01)
# =============================================================================

"""
BIDIRECTIONAL GRAPH-REASONING FUSION

The cognitive substrate for ADAM's multi-source intelligence.

This module implements:
1. 10 Intelligence Sources - Different forms of knowledge
2. Interaction Bridge - Bidirectional graph ↔ reasoning flow
3. Multi-Source Orchestrator - Coordinates all sources
4. Conflict Resolution Engine - Handles contradictions between sources
5. Update Tier Controller - Manages graph update latency tiers
6. Learning Bridge - Propagates outcomes to update all relationships

Key Insight:
Intelligence emerges from the INTERPLAY between sources, not from any
single source alone. The graph enables sources to discover relationships
that none of them were looking for.
"""

from adam.graph_reasoning.models.intelligence_sources import (
    IntelligenceSourceType,
    IntelligenceSourceBase,
    ClaudeReasoningEvidence,
    EmpiricalPatternEvidence,
    NonconsciousSignalEvidence,
    GraphEmergenceEvidence,
    BanditPosteriorEvidence,
)
from adam.graph_reasoning.models.graph_context import (
    UserProfileSnapshot,
    MechanismHistory,
    GraphContext,
)
from adam.graph_reasoning.models.reasoning_output import (
    MechanismActivation,
    StateInference,
    ReasoningInsight,
)
from adam.graph_reasoning.bridge.interaction_bridge import (
    InteractionBridge,
)
from adam.graph_reasoning.update_tiers import (
    UpdateTier,
    UpdatePriority,
    UpdateCategory,
    GraphUpdate,
    UpdateTierController,
    get_update_tier_controller,
)
from adam.graph_reasoning.conflict_resolution import (
    ConflictType,
    ResolutionStrategy,
    ConflictSeverity,
    Conflict,
    ConflictResolutionEngine,
    get_conflict_resolution_engine,
)

__all__ = [
    # Intelligence Sources
    "IntelligenceSourceType",
    "IntelligenceSourceBase",
    "ClaudeReasoningEvidence",
    "EmpiricalPatternEvidence",
    "NonconsciousSignalEvidence",
    "GraphEmergenceEvidence",
    "BanditPosteriorEvidence",
    # Graph Context
    "UserProfileSnapshot",
    "MechanismHistory",
    "GraphContext",
    # Reasoning Output
    "MechanismActivation",
    "StateInference",
    "ReasoningInsight",
    # Bridge
    "InteractionBridge",
    # Update Tier Controller
    "UpdateTier",
    "UpdatePriority",
    "UpdateCategory",
    "GraphUpdate",
    "UpdateTierController",
    "get_update_tier_controller",
    # Conflict Resolution Engine
    "ConflictType",
    "ResolutionStrategy",
    "ConflictSeverity",
    "Conflict",
    "ConflictResolutionEngine",
    "get_conflict_resolution_engine",
]
