# =============================================================================
# ADAM Experimentation Models (#12)
# Location: adam/experimentation/models.py
# =============================================================================

"""
A/B TESTING DATA MODELS

Pydantic models for experiment management and analysis.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ExperimentType(str, Enum):
    """Types of experiments ADAM can run."""
    AB_STANDARD = "ab_standard"
    AB_MULTIVARIATE = "ab_multivariate"
    MECHANISM_ISOLATION = "mechanism_isolation"
    PERSONALITY_MATCH = "personality_match"
    FRAME_TEST = "frame_test"
    CONSTRUAL_TEST = "construal_test"
    MULTI_ARMED_BANDIT = "mab"


class ExperimentStatus(str, Enum):
    """Experiment lifecycle states."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    STOPPED = "stopped"


class MetricType(str, Enum):
    """Types of metrics to track."""
    CONVERSION = "conversion"
    CTR = "ctr"
    ENGAGEMENT = "engagement"
    REVENUE = "revenue"
    RETENTION = "retention"


class Variant(BaseModel):
    """Experiment variant definition."""
    
    variant_id: str = Field(default_factory=lambda: f"var_{uuid4().hex[:8]}")
    name: str
    description: Optional[str] = None
    
    # Traffic allocation
    traffic_percentage: float = Field(ge=0.0, le=100.0)
    
    # Psychological parameters
    mechanism: Optional[str] = None
    framing: Optional[str] = None  # gain, loss
    construal: Optional[str] = None  # abstract, concrete
    
    # Custom parameters
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
    # Control flag
    is_control: bool = False


class Experiment(BaseModel):
    """Experiment definition."""
    
    experiment_id: str = Field(default_factory=lambda: f"exp_{uuid4().hex[:12]}")
    name: str
    description: Optional[str] = None
    hypothesis: Optional[str] = None
    
    # Type and status
    experiment_type: ExperimentType = ExperimentType.AB_STANDARD
    status: ExperimentStatus = ExperimentStatus.DRAFT
    
    # Variants
    variants: List[Variant] = Field(default_factory=list)
    
    # Targeting
    target_audience: Optional[Dict[str, Any]] = None
    min_sample_size: int = 1000
    
    # Metrics
    primary_metric: MetricType = MetricType.CONVERSION
    secondary_metrics: List[MetricType] = Field(default_factory=list)
    
    # Timeline
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[str] = None
    
    def get_control(self) -> Optional[Variant]:
        """Get control variant."""
        for v in self.variants:
            if v.is_control:
                return v
        return self.variants[0] if self.variants else None


class Assignment(BaseModel):
    """User assignment to experiment variant."""
    
    assignment_id: str = Field(default_factory=lambda: f"asn_{uuid4().hex[:12]}")
    experiment_id: str
    variant_id: str
    user_id: str
    
    # Assignment context
    assigned_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    assignment_reason: str = "random"
    
    # User context at assignment
    archetype: Optional[str] = None
    segment: Optional[str] = None


class VariantMetrics(BaseModel):
    """Metrics for a single variant."""
    
    variant_id: str
    sample_size: int = 0
    
    # Core metrics
    conversions: int = 0
    conversion_rate: float = 0.0
    revenue: float = 0.0
    
    # Statistical
    mean: float = 0.0
    variance: float = 0.0
    std_error: float = 0.0
    
    # Confidence interval
    ci_lower: float = 0.0
    ci_upper: float = 0.0
    confidence_level: float = 0.95


class ExperimentResult(BaseModel):
    """Results of experiment analysis."""
    
    experiment_id: str
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Variant metrics
    variant_metrics: Dict[str, VariantMetrics] = Field(default_factory=dict)
    
    # Statistical significance
    is_significant: bool = False
    p_value: Optional[float] = None
    confidence_level: float = 0.95
    
    # Effect size
    relative_lift: Optional[float] = None
    absolute_lift: Optional[float] = None
    
    # Winner
    winning_variant_id: Optional[str] = None
    recommendation: Optional[str] = None
    
    # Quality checks
    srm_detected: bool = False  # Sample ratio mismatch
    sufficient_power: bool = False
