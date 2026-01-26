# =============================================================================
# ADAM Psychological Validity Models
# Location: adam/validity/models.py
# =============================================================================

"""
PSYCHOLOGICAL VALIDITY MODELS

Models for validity testing framework.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field


class ValidityType(str, Enum):
    """Types of psychological validity."""
    
    CONSTRUCT = "construct"       # Measuring what we claim
    PREDICTIVE = "predictive"     # Predictions match outcomes
    CONVERGENT = "convergent"     # Related constructs correlate
    DISCRIMINANT = "discriminant" # Unrelated constructs differ
    FACE = "face"                 # Intuitive psychological sense


class ValidityStatus(str, Enum):
    """Status of validity check."""
    
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    INSUFFICIENT_DATA = "insufficient_data"


class ConstructType(str, Enum):
    """Psychological constructs we validate."""
    
    BIG_FIVE = "big_five"
    REGULATORY_FOCUS = "regulatory_focus"
    CONSTRUAL_LEVEL = "construal_level"
    MECHANISM_EFFECTIVENESS = "mechanism_effectiveness"
    JOURNEY_STATE = "journey_state"


# =============================================================================
# VALIDITY CHECK
# =============================================================================

class ValidityCheck(BaseModel):
    """A single validity check."""
    
    check_id: str
    validity_type: ValidityType
    construct: ConstructType
    
    # Check details
    description: str
    metric_name: str
    
    # Thresholds
    pass_threshold: float
    warning_threshold: float
    
    # Weight for overall score
    weight: float = Field(ge=0.0, le=1.0, default=1.0)


class ValidityResult(BaseModel):
    """Result of a validity check."""
    
    check: ValidityCheck
    
    # Results
    status: ValidityStatus
    score: float
    
    # Evidence
    sample_size: int = Field(default=0, ge=0)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    
    # Interpretation
    interpretation: str
    recommendations: List[str] = Field(default_factory=list)
    
    # Timing
    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# =============================================================================
# SPECIFIC VALIDITY TYPES
# =============================================================================

class ConstructValidity(BaseModel):
    """Construct validity assessment."""
    
    construct: ConstructType
    
    # Factor analysis results
    factor_loadings: Dict[str, float] = Field(default_factory=dict)
    explained_variance: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Internal consistency
    cronbachs_alpha: Optional[float] = None
    
    # Status
    status: ValidityStatus
    interpretation: str


class PredictiveValidity(BaseModel):
    """Predictive validity assessment."""
    
    prediction_type: str  # e.g., "mechanism_effectiveness", "conversion"
    
    # Correlation with outcomes
    correlation: float = Field(ge=-1.0, le=1.0)
    p_value: float = Field(ge=0.0, le=1.0)
    
    # Sample
    sample_size: int = Field(ge=0)
    time_period_days: int = Field(ge=0)
    
    # AUC for classification predictions
    auc_roc: Optional[float] = None
    
    # Status
    status: ValidityStatus
    interpretation: str


class ConvergentValidity(BaseModel):
    """Convergent validity assessment."""
    
    construct_a: ConstructType
    construct_b: ConstructType
    expected_relationship: str  # "positive", "negative", "none"
    
    # Observed correlation
    correlation: float = Field(ge=-1.0, le=1.0)
    p_value: float = Field(ge=0.0, le=1.0)
    
    # Did it match expectations?
    matches_theory: bool
    
    # Status
    status: ValidityStatus
    interpretation: str


class DiscriminantValidity(BaseModel):
    """Discriminant validity assessment."""
    
    construct_a: ConstructType
    construct_b: ConstructType
    
    # Should be distinct (low correlation)
    correlation: float = Field(ge=-1.0, le=1.0)
    
    # Is the correlation low enough?
    sufficiently_distinct: bool
    
    # Status
    status: ValidityStatus
    interpretation: str


# =============================================================================
# VALIDITY REPORT
# =============================================================================

class ValidityReport(BaseModel):
    """Complete validity report."""
    
    report_id: str
    
    # Scope
    scope: str  # "system", "construct", "component"
    target: Optional[str] = None  # Specific construct or component
    
    # Time period
    start_date: datetime
    end_date: datetime
    
    # Results
    construct_validity: List[ConstructValidity] = Field(default_factory=list)
    predictive_validity: List[PredictiveValidity] = Field(default_factory=list)
    convergent_validity: List[ConvergentValidity] = Field(default_factory=list)
    discriminant_validity: List[DiscriminantValidity] = Field(default_factory=list)
    
    # Individual check results
    check_results: List[ValidityResult] = Field(default_factory=list)
    
    # Summary
    overall_status: ValidityStatus
    overall_score: float = Field(ge=0.0, le=1.0)
    
    # Counts
    checks_passed: int = Field(default=0, ge=0)
    checks_warning: int = Field(default=0, ge=0)
    checks_failed: int = Field(default=0, ge=0)
    
    # Recommendations
    critical_issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    
    # Timing
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
