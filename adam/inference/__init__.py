# =============================================================================
# ADAM Inference Engine (#09)
# Location: adam/inference/__init__.py
# =============================================================================

"""
LATENCY-OPTIMIZED INFERENCE ENGINE

Enhancement #09: Real-time psychological decision serving at sub-100ms scale.

Key Capabilities:
- Tiered inference (5 tiers from full reasoning to global defaults)
- Circuit breakers for graceful degradation
- Parallel feature fetching
- Decision caching
"""

from adam.inference.engine import (
    InferenceEngine,
    InferenceTier,
    InferenceResult,
)
from adam.inference.models import (
    InferenceRequest,
    InferenceResponse,
    DecisionContext,
    MechanismSelection,
)

__all__ = [
    "InferenceEngine",
    "InferenceTier",
    "InferenceResult",
    "InferenceRequest",
    "InferenceResponse",
    "DecisionContext",
    "MechanismSelection",
]
