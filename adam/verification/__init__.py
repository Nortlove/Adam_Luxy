# =============================================================================
# ADAM Verification Layer (#05)
# =============================================================================

"""
VERIFICATION LAYER

Enterprise-grade verification pipeline for psychological reasoning.

Four-Layer Architecture:
1. Atom Consistency - Cross-atom logical coherence
2. Confidence Calibration - Historical calibration adjustment
3. Safety Validation - Vulnerable population protection
4. Graph Grounding - Verify claims against Neo4j

Plus: Self-correction mechanism for failed verifications.
"""

from adam.verification.models.constraints import (
    Constraint,
    ConstraintType,
    ConstraintResult,
    PsychologicalConstraint,
)
from adam.verification.models.results import (
    VerificationResult,
    LayerResult,
    VerificationStatus,
)
from adam.verification.layers.consistency import ConsistencyVerifier
from adam.verification.layers.calibration import CalibrationLayer
from adam.verification.layers.safety import SafetyValidator
from adam.verification.layers.grounding import GraphGroundingLayer
from adam.verification.service import VerificationService

__all__ = [
    # Models
    "Constraint",
    "ConstraintType",
    "ConstraintResult",
    "PsychologicalConstraint",
    "VerificationResult",
    "LayerResult",
    "VerificationStatus",
    # Layers
    "ConsistencyVerifier",
    "CalibrationLayer",
    "SafetyValidator",
    "GraphGroundingLayer",
    # Service
    "VerificationService",
]
