# =============================================================================
# ADAM A/B Testing Infrastructure (#12)
# Location: adam/experimentation/__init__.py
# =============================================================================

"""
A/B TESTING INFRASTRUCTURE

Enhancement #12: Production-ready experimentation platform for psychological advertising.

Key Capabilities:
- Experiment design with psychological stratification
- Traffic assignment with consistent hashing
- Statistical analysis (frequentist + Bayesian)
- Multi-armed bandit integration
- Mechanism isolation testing
"""

from adam.experimentation.service import ExperimentService
from adam.experimentation.models import (
    Experiment,
    ExperimentType,
    ExperimentStatus,
    Variant,
    Assignment,
    ExperimentResult,
)

__all__ = [
    "ExperimentService",
    "Experiment",
    "ExperimentType",
    "ExperimentStatus",
    "Variant",
    "Assignment",
    "ExperimentResult",
]
