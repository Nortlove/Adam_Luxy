# =============================================================================
# ADAM Behavioral Analytics Integration
# Location: adam/behavioral_analytics/integration/__init__.py
# =============================================================================

"""
Behavioral Analytics Integration Layer

Properly integrates behavioral analytics with ADAM's core architecture:
- GradientBridgeService for learning signals
- Kafka Event Bus for signal propagation
- Blackboard for shared state
- Neo4j InteractionBridge for graph updates
"""

from adam.behavioral_analytics.integration.gradient_bridge_integration import (
    BehavioralGradientBridgeIntegration,
    get_behavioral_gradient_bridge_integration,
)

__all__ = [
    "BehavioralGradientBridgeIntegration",
    "get_behavioral_gradient_bridge_integration",
]
