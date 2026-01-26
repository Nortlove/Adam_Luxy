# =============================================================================
# ADAM Enhancement #13: Learning Package
# Location: adam/cold_start/learning/__init__.py
# =============================================================================

"""
Cold Start Learning Integration

Connects cold start with ADAM's learning infrastructure:
- Gradient Bridge: Propagates outcomes to update components
- Learning Signals: Typed signals for component updates
"""

from .gradient_bridge import (
    ColdStartLearningSignal,
    ColdStartGradientBridge,
    get_cold_start_gradient_bridge,
)

__all__ = [
    "ColdStartLearningSignal",
    "ColdStartGradientBridge",
    "get_cold_start_gradient_bridge",
]
