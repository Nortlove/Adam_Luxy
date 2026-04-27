# =============================================================================
# ADAM Enhancement #13: Learning Package
# Location: adam/cold_start/learning/__init__.py
# =============================================================================

"""
Cold Start Learning Integration (COLD-START-ONLY ROLE — see below)

ROLE PER G1 LANDSCAPE DOC: scoped to the cold-start path. Production
cold-start depends on this for outcome propagation back into archetype
priors when a buyer has insufficient observation history for the main
learning loop.

For new learning code OUTSIDE cold-start:
  - Production runtime: adam.core.learning (CANONICAL)
  - Convenience aggregator: adam.learning
  - Offline corpus learning scripts: adam.intelligence.learning

See adam/core/learning/__init__.py for the full four-package
landscape documentation.

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
