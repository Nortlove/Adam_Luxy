# =============================================================================
# ADAM Behavioral Analytics: Knowledge Models
# Location: adam/behavioral_analytics/models/knowledge.py
# =============================================================================

"""
BEHAVIORAL KNOWLEDGE MODELS

Models for representing research-validated and system-discovered knowledge
about behavioral signals and their psychological construct mappings.

Knowledge Lifecycle:
1. RESEARCH_VALIDATED - From peer-reviewed studies (150+ sources)
2. HYPOTHESIS_GENERATED - System-discovered pattern, under testing
3. HYPOTHESIS_TESTING - Collecting validation data
4. SYSTEM_VALIDATED - Passed statistical validation
5. PROMOTED - Active system knowledge
6. DEPRECATED - No longer validates, under review
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import uuid


class KnowledgeType(str, Enum):
    """Types of behavioral knowledge."""
    RESEARCH_VALIDATED = "research_validated"  # From peer-reviewed studies
    SYSTEM_DISCOVERED = "system_discovered"    # Discovered by ADAM
    UNDER_TESTING = "under_testing"            # Hypothesis being tested


class KnowledgeStatus(str, Enum):
    """Lifecycle status of knowledge."""
    ACTIVE = "active"              # In use for predictions
    UNDER_REVIEW = "under_review"  # Validation rate dropped
    DEPRECATED = "deprecated"      # No longer reliable
    TESTING = "testing"            # Collecting validation data


class EffectType(str, Enum):
    """Type of effect size metric."""
    ACCURACY = "accuracy"           # Classification accuracy (0-1)
    CORRELATION = "correlation"     # Pearson r (-1 to 1)
    COHENS_D = "cohens_d"          # Cohen's d effect size
    AUC = "auc"                     # Area under curve (0-1)
    SHAP_IMPORTANCE = "shap"        # SHAP feature importance
    ODDS_RATIO = "odds_ratio"       # Odds ratio
    CONVERSION_LIFT = "lift"        # Conversion lift percentage
    BEHAVIORAL = "behavioral"       # Qualitative behavioral observation


class SignalCategory(str, Enum):
    """Category of behavioral signal."""
    IMPLICIT = "implicit"           # Nonconscious signals
    EXPLICIT = "explicit"           # Conscious actions
    TEMPORAL = "temporal"           # Time-based patterns
    SENSOR = "sensor"               # Device sensor data
    NAVIGATION = "navigation"       # Click/page patterns


class KnowledgeTier(int, Enum):
    """Predictive value tier."""
    TIER_1 = 1  # Highest predictive value
    TIER_2 = 2  # Strong value with context
    TIER_3 = 3  # Supporting signals


class ResearchSource(BaseModel):
    """A research study source."""
    
    source_id: str
    authors: str
    year: int
    title: str
    journal: Optional[str] = None
    sample_size: Optional[int] = None
    key_finding: str


class BehavioralKnowledge(BaseModel):
    """
    A piece of validated behavioral knowledge.
    
    Represents a mapping from an observable behavioral signal
    to a psychological construct, with effect size and validation data.
    """
    
    knowledge_id: str = Field(default_factory=lambda: f"bk_{uuid.uuid4().hex[:12]}")
    knowledge_type: KnowledgeType
    status: KnowledgeStatus = KnowledgeStatus.ACTIVE
    
    # Signal definition
    signal_name: str
    signal_category: SignalCategory
    signal_description: str
    
    # Feature engineering
    feature_name: str  # e.g., "pressure_mean", "response_latency_p50"
    feature_computation: str  # How to compute from raw data
    
    # Construct mapping
    maps_to_construct: str  # e.g., "emotional_arousal", "decision_confidence"
    mapping_direction: str  # "positive", "negative", "nonlinear"
    mapping_description: str
    
    # Effect metrics
    effect_size: float
    effect_type: EffectType
    confidence_interval_lower: Optional[float] = None
    confidence_interval_upper: Optional[float] = None
    p_value: Optional[float] = None
    
    # Evidence
    study_count: int = 0
    total_sample_size: int = 0
    sources: List[ResearchSource] = Field(default_factory=list)
    
    # Thresholds for application
    signal_threshold_high: Optional[float] = None
    signal_threshold_low: Optional[float] = None
    
    # Validation tracking
    tier: KnowledgeTier = KnowledgeTier.TIER_2
    validation_count: int = 0
    validation_successes: int = 0
    last_validated: Optional[datetime] = None
    
    # Implementation guidance
    implementation_notes: str = ""
    requires_baseline: bool = False  # Needs per-user baseline?
    min_observations: int = 1
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def validation_rate(self) -> float:
        """Proportion of validations that confirmed the mapping."""
        if self.validation_count == 0:
            return 0.0
        return self.validation_successes / self.validation_count
    
    @property
    def is_reliable(self) -> bool:
        """Whether knowledge is currently reliable."""
        if self.knowledge_type == KnowledgeType.RESEARCH_VALIDATED:
            return self.status == KnowledgeStatus.ACTIVE
        # For system-discovered, require validation
        return (
            self.status == KnowledgeStatus.ACTIVE and
            self.validation_count >= 50 and
            self.validation_rate >= 0.65
        )


class HypothesisStatus(str, Enum):
    """Status of a behavioral hypothesis."""
    GENERATED = "generated"     # Just created
    TESTING = "testing"         # Collecting data
    VALIDATED = "validated"     # Passed statistical tests
    REJECTED = "rejected"       # Failed statistical tests
    PROMOTED = "promoted"       # Became system knowledge


class BehavioralHypothesis(BaseModel):
    """
    A hypothesis about a behavioral signal-outcome relationship.
    
    Generated by the system when patterns are observed,
    tested for statistical significance, and promoted to
    knowledge when validated.
    """
    
    hypothesis_id: str = Field(default_factory=lambda: f"bh_{uuid.uuid4().hex[:12]}")
    status: HypothesisStatus = HypothesisStatus.GENERATED
    
    # Hypothesis definition
    signal_pattern: str  # e.g., "high_pressure_variance_during_checkout"
    signal_features: List[str]  # Features involved
    predicted_outcome: str  # e.g., "cart_abandonment", "conversion"
    predicted_direction: str  # "positive", "negative"
    hypothesis_description: str
    
    # Testing state
    observations: int = 0
    positive_outcomes: int = 0
    negative_outcomes: int = 0
    
    # Statistical metrics
    observed_effect_size: Optional[float] = None
    observed_effect_type: EffectType = EffectType.CORRELATION
    p_value: Optional[float] = None
    confidence_interval_lower: Optional[float] = None
    confidence_interval_upper: Optional[float] = None
    
    # Cross-validation
    cv_folds_passed: int = 0
    cv_folds_total: int = 5
    
    # Promotion criteria
    min_observations_required: int = 50
    significance_threshold: float = 0.05
    min_effect_size: float = 0.1
    
    # Timestamps
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    last_observation: Optional[datetime] = None
    validated_at: Optional[datetime] = None
    promoted_at: Optional[datetime] = None
    
    # Link to promoted knowledge
    promoted_knowledge_id: Optional[str] = None
    
    @property
    def is_promotable(self) -> bool:
        """Check if hypothesis meets promotion criteria."""
        return (
            self.observations >= self.min_observations_required and
            self.p_value is not None and
            self.p_value < self.significance_threshold and
            self.observed_effect_size is not None and
            abs(self.observed_effect_size) >= self.min_effect_size and
            self.cv_folds_passed >= 3  # Majority of CV folds
        )
    
    @property
    def observation_rate(self) -> float:
        """Rate of positive outcomes."""
        if self.observations == 0:
            return 0.0
        return self.positive_outcomes / self.observations


class KnowledgeValidationEvent(BaseModel):
    """An event validating or invalidating a piece of knowledge."""
    
    event_id: str = Field(default_factory=lambda: f"kv_{uuid.uuid4().hex[:12]}")
    knowledge_id: str
    
    # Validation context
    user_id: str
    session_id: str
    decision_id: Optional[str] = None
    
    # Signal observed
    signal_value: float
    signal_features: Dict[str, float] = Field(default_factory=dict)
    
    # Outcome observed
    outcome_type: str
    outcome_value: float
    
    # Validation result
    prediction_matched: bool
    prediction_confidence: float
    
    # Timestamps
    observed_at: datetime = Field(default_factory=datetime.utcnow)
