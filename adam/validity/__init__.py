# =============================================================================
# ADAM Psychological Validity Framework (#11)
# =============================================================================

"""
PSYCHOLOGICAL VALIDITY TESTING

Framework for ensuring psychological validity of ADAM's inferences.

Validity Types:
1. Construct Validity - Are we measuring what we claim to measure?
2. Predictive Validity - Do our predictions correlate with outcomes?
3. Convergent Validity - Do related constructs correlate appropriately?
4. Discriminant Validity - Do unrelated constructs differ appropriately?
5. Face Validity - Do outputs make intuitive psychological sense?

This framework is critical for scientific credibility of ADAM's
psychological intelligence claims.
"""

from adam.validity.models import (
    ValidityType,
    ValidityCheck,
    ValidityResult,
    ConstructValidity,
    PredictiveValidity,
    ValidityReport,
)
from adam.validity.checks import (
    ConstructValidityChecker,
    PredictiveValidityChecker,
    ConvergentValidityChecker,
    DiscriminantValidityChecker,
)
from adam.validity.service import PsychologicalValidityService

__all__ = [
    # Models
    "ValidityType",
    "ValidityCheck",
    "ValidityResult",
    "ConstructValidity",
    "PredictiveValidity",
    "ValidityReport",
    # Checkers
    "ConstructValidityChecker",
    "PredictiveValidityChecker",
    "ConvergentValidityChecker",
    "DiscriminantValidityChecker",
    # Service
    "PsychologicalValidityService",
]
