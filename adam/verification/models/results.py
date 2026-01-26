# =============================================================================
# ADAM Verification Result Models
# Location: adam/verification/models/results.py
# =============================================================================

"""
VERIFICATION RESULT MODELS

Models for verification pipeline results.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from adam.verification.models.constraints import ConstraintResult, ConstraintSeverity


# =============================================================================
# ENUMS
# =============================================================================

class VerificationStatus(str, Enum):
    """Overall verification status."""
    
    PASSED = "passed"           # All checks passed
    PASSED_WITH_WARNINGS = "passed_with_warnings"
    FAILED = "failed"           # Failed, but correctable
    BLOCKED = "blocked"         # Critical failure, cannot proceed
    CORRECTED = "corrected"     # Failed but self-corrected


class VerificationLayer(str, Enum):
    """The four verification layers."""
    
    CONSISTENCY = "consistency"
    CALIBRATION = "calibration"
    SAFETY = "safety"
    GROUNDING = "grounding"


# =============================================================================
# LAYER RESULT
# =============================================================================

class LayerResult(BaseModel):
    """Result from a single verification layer."""
    
    layer: VerificationLayer
    
    # Status
    passed: bool
    
    # Constraint results
    constraints_checked: int = Field(default=0, ge=0)
    constraints_satisfied: int = Field(default=0, ge=0)
    constraints_violated: int = Field(default=0, ge=0)
    
    # Detailed results
    constraint_results: List[ConstraintResult] = Field(default_factory=list)
    
    # Highest severity violation
    max_severity: ConstraintSeverity = Field(default=ConstraintSeverity.INFO)
    
    # Timing
    duration_ms: float = Field(ge=0.0, default=0.0)
    
    # Messages
    summary: str = ""
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    
    def add_result(self, result: ConstraintResult) -> None:
        """Add a constraint result."""
        self.constraint_results.append(result)
        self.constraints_checked += 1
        
        if result.satisfied:
            self.constraints_satisfied += 1
        else:
            self.constraints_violated += 1
            
            if result.severity.value > self.max_severity.value:
                self.max_severity = result.severity
            
            if result.severity in [ConstraintSeverity.ERROR, ConstraintSeverity.CRITICAL]:
                self.errors.append(result.violation_message or result.constraint_name)
            else:
                self.warnings.append(result.violation_message or result.constraint_name)


# =============================================================================
# CALIBRATION RESULT
# =============================================================================

class CalibrationResult(BaseModel):
    """Result from confidence calibration."""
    
    # Original vs calibrated
    original_confidence: float = Field(ge=0.0, le=1.0)
    calibrated_confidence: float = Field(ge=0.0, le=1.0)
    
    # Calibration method used
    method: str = ""  # "historical", "platt", "isotonic"
    
    # Calibration curve data
    curve_data: Dict[str, float] = Field(default_factory=dict)
    
    # Expected Calibration Error
    ece: float = Field(ge=0.0, default=0.0)
    
    # Was recalibration needed?
    recalibrated: bool = Field(default=False)
    recalibration_factor: float = Field(default=1.0)


# =============================================================================
# GROUNDING RESULT
# =============================================================================

class GroundingResult(BaseModel):
    """Result from graph grounding verification."""
    
    # Claims checked
    claims_checked: int = Field(default=0, ge=0)
    claims_grounded: int = Field(default=0, ge=0)
    claims_ungrounded: int = Field(default=0, ge=0)
    
    # Hallucination detection
    hallucinations_detected: int = Field(default=0, ge=0)
    hallucination_details: List[str] = Field(default_factory=list)
    
    # Graph queries run
    queries_run: int = Field(default=0, ge=0)
    query_latency_ms: float = Field(ge=0.0, default=0.0)


# =============================================================================
# SELF-CORRECTION
# =============================================================================

class CorrectionAttempt(BaseModel):
    """Record of a self-correction attempt."""
    
    attempt_number: int = Field(ge=1)
    
    # What failed
    failed_constraint: str
    failure_reason: str
    
    # Correction applied
    correction_type: str  # "retry", "fallback", "adjustment"
    correction_details: str
    
    # Result
    successful: bool
    new_output: Dict[str, Any] = Field(default_factory=dict)


# =============================================================================
# COMPLETE VERIFICATION RESULT
# =============================================================================

class VerificationResult(BaseModel):
    """
    Complete verification result for a decision.
    
    Contains results from all four layers plus any self-corrections.
    """
    
    verification_id: str = Field(
        default_factory=lambda: f"ver_{uuid4().hex[:12]}"
    )
    
    # What was verified
    request_id: str
    decision_id: Optional[str] = None
    
    # Overall status
    status: VerificationStatus
    
    # Layer results
    layer_results: Dict[VerificationLayer, LayerResult] = Field(
        default_factory=dict
    )
    
    # Calibration
    calibration: Optional[CalibrationResult] = None
    
    # Grounding
    grounding: Optional[GroundingResult] = None
    
    # Self-correction attempts
    correction_attempts: List[CorrectionAttempt] = Field(default_factory=list)
    corrections_applied: int = Field(default=0, ge=0)
    
    # Final output (may be corrected)
    original_output: Dict[str, Any] = Field(default_factory=dict)
    verified_output: Dict[str, Any] = Field(default_factory=dict)
    output_modified: bool = Field(default=False)
    
    # Summary
    total_constraints_checked: int = Field(default=0, ge=0)
    total_constraints_passed: int = Field(default=0, ge=0)
    
    # Timing
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: Optional[datetime] = None
    total_duration_ms: float = Field(ge=0.0, default=0.0)
    
    def add_layer_result(self, result: LayerResult) -> None:
        """Add a layer result."""
        self.layer_results[result.layer] = result
        self.total_constraints_checked += result.constraints_checked
        self.total_constraints_passed += result.constraints_satisfied
    
    def complete(self) -> None:
        """Mark verification as complete."""
        self.completed_at = datetime.now(timezone.utc)
        if self.started_at:
            self.total_duration_ms = (
                self.completed_at - self.started_at
            ).total_seconds() * 1000
        
        # Determine final status
        has_critical = any(
            lr.max_severity == ConstraintSeverity.CRITICAL
            for lr in self.layer_results.values()
        )
        has_error = any(
            lr.max_severity == ConstraintSeverity.ERROR
            for lr in self.layer_results.values()
        )
        has_warning = any(
            lr.max_severity == ConstraintSeverity.WARNING
            for lr in self.layer_results.values()
        )
        
        if has_critical:
            self.status = VerificationStatus.BLOCKED
        elif has_error:
            if self.corrections_applied > 0:
                self.status = VerificationStatus.CORRECTED
            else:
                self.status = VerificationStatus.FAILED
        elif has_warning:
            self.status = VerificationStatus.PASSED_WITH_WARNINGS
        else:
            self.status = VerificationStatus.PASSED
