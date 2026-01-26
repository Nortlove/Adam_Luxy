# =============================================================================
# ADAM Interaction Bridge
# =============================================================================

"""
INTERACTION BRIDGE

The bidirectional link between Neo4j graph and reasoning components.

Two directions:
1. PULL (Graph → Reasoning): Context, priors, history
2. PUSH (Reasoning → Graph): Insights, activations, state updates

The bridge ensures that:
- Reasoning is always grounded in learned priors
- Every insight is persisted for future learning
- Learning signals are emitted for outcome attribution
"""

from adam.graph_reasoning.bridge.interaction_bridge import (
    InteractionBridge,
)
from adam.graph_reasoning.bridge.context_queries import (
    ContextQueryExecutor,
)

__all__ = [
    "InteractionBridge",
    "ContextQueryExecutor",
]
