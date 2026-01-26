# =============================================================================
# ADAM Blackboard Architecture (#02)
# =============================================================================

"""
SHARED STATE BLACKBOARD

Working memory for real-time psychological intelligence during request processing.

The Blackboard is divided into 5 zones:
- Zone 1: Request Context (read-only after initialization)
- Zone 2: Atom Reasoning Spaces (each atom writes to its namespace)
- Zone 3: Synthesis Workspace (aggregated reasoning)
- Zone 4: Decision State (final decisions)
- Zone 5: Learning Signals (outcome attribution)

Key Benefits:
- Atoms can coordinate reasoning in real-time
- Synthesis sees reasoning evolution, not just final outputs
- Learning signals are aggregated for complete attribution
- Sub-100ms state access via Redis
"""

from adam.blackboard.models.core import (
    BlackboardState,
    BlackboardZone,
    ZoneAccessMode,
)
from adam.blackboard.models.zone1_context import (
    RequestContext,
    UserIntelligencePackage,
)
from adam.blackboard.models.zone2_reasoning import (
    AtomReasoningSpace,
    PreliminarySignal,
    ConfidenceEvolution,
)
from adam.blackboard.models.zone3_synthesis import (
    SynthesisWorkspace,
    AtomAggregation,
    ConflictResolution,
)
from adam.blackboard.models.zone4_decision import (
    DecisionState,
    DecisionCandidate,
)
from adam.blackboard.models.zone5_learning import (
    LearningSignalAggregator,
    ComponentSignal,
)
from adam.blackboard.service import BlackboardService

__all__ = [
    # Core
    "BlackboardState",
    "BlackboardZone",
    "ZoneAccessMode",
    # Zone 1
    "RequestContext",
    "UserIntelligencePackage",
    # Zone 2
    "AtomReasoningSpace",
    "PreliminarySignal",
    "ConfidenceEvolution",
    # Zone 3
    "SynthesisWorkspace",
    "AtomAggregation",
    "ConflictResolution",
    # Zone 4
    "DecisionState",
    "DecisionCandidate",
    # Zone 5
    "LearningSignalAggregator",
    "ComponentSignal",
    # Service
    "BlackboardService",
]
