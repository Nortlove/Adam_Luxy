# =============================================================================
# ADAM Explanation Service (#18)
# Location: adam/explanation/__init__.py
# =============================================================================

"""
EXPLANATION GENERATION

Enhancement #18: Making the black box transparent.

Key Capabilities:
- Multi-audience explanations (user, advertiser, engineer, regulator)
- Decision trace generation
- Compliance reporting (GDPR, CCPA)
- Campaign-level analysis
"""

from adam.explanation.service import ExplanationService
from adam.explanation.models import (
    Explanation,
    ExplanationAudience,
    DecisionTrace,
    MechanismExplanation,
)

__all__ = [
    "ExplanationService",
    "Explanation",
    "ExplanationAudience",
    "DecisionTrace",
    "MechanismExplanation",
]
