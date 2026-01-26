# =============================================================================
# ADAM Prometheus Metrics Infrastructure
# Location: adam/infrastructure/prometheus/__init__.py
# =============================================================================

"""
PROMETHEUS METRICS

ADAM-specific metrics for observability.

Metric Categories:
- adam_decision_* - Ad decision metrics
- adam_mechanism_* - Mechanism effectiveness metrics
- adam_profile_* - Profile update metrics
- adam_inference_* - Inference latency metrics
- adam_learning_* - Learning signal metrics
"""

from adam.infrastructure.prometheus.metrics import (
    ADAMMetrics,
    get_metrics,
)

__all__ = [
    "ADAMMetrics",
    "get_metrics",
]
