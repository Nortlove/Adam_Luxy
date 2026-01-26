# ADAM Emergent Intelligence: Implementation Companion
## Production Code Patterns and Integration Specifications

**Companion to**: ADAM Emergent Intelligence Architecture  
**Purpose**: Concrete implementation code for the cognitive ecosystem  
**Version**: 1.0  
**Status**: Production Implementation Ready

---

# Part 1: Complete Pydantic Models

## 1.1 Psychological Construct Models

```python
"""
ADAM Core Domain Models
Psychological constructs as first-class entities
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from pydantic import BaseModel, Field, field_validator
import numpy as np


# =============================================================================
# ENUMERATIONS
# =============================================================================

class TraitDomain(str, Enum):
    """Domains of psychological traits."""
    BIG_FIVE = "big_five"
    REGULATORY_FOCUS = "regulatory_focus"
    CONSTRUAL_LEVEL = "construal_level"
    NEED_FOR_COGNITION = "need_for_cognition"
    MORAL_FOUNDATIONS = "moral_foundations"
    EMERGENT = "emergent"


class MechanismType(str, Enum):
    """The 9 cognitive mechanisms plus emergent."""
    AUTOMATIC_EVALUATION = "automatic_evaluation"
    WANTING_LIKING_DISSOCIATION = "wanting_liking_dissociation"
    EVOLUTIONARY_MOTIVE = "evolutionary_motive"
    LINGUISTIC_FRAMING = "linguistic_framing"
    MIMETIC_DESIRE = "mimetic_desire"
    EMBODIED_COGNITION = "embodied_cognition"
    ATTENTION_DYNAMICS = "attention_dynamics"
    IDENTITY_CONSTRUCTION = "identity_construction"
    TEMPORAL_CONSTRUAL = "temporal_construal"
    EMERGENT = "emergent"


class DiscoveryStatus(str, Enum):
    """Status of discovered patterns."""
    DETECTED = "detected"
    HYPOTHESIS_GENERATED = "hypothesis_generated"
    TESTING = "testing"
    VALIDATED = "validated"
    REJECTED = "rejected"
    INTEGRATED = "integrated"


class LearningPriority(str, Enum):
    """Priority levels for learning signal propagation."""
    IMMEDIATE = "immediate"  # <10ms
    FAST = "fast"           # <100ms
    ASYNC = "async"         # <1s
    BATCH = "batch"         # hourly/daily


# =============================================================================
# PSYCHOLOGICAL CONSTRUCTS
# =============================================================================

class BigFiveProfile(BaseModel):
    """Big Five personality trait scores with confidence."""
    
    openness: float = Field(ge=0, le=1, description="Openness to experience")
    openness_confidence: float = Field(ge=0, le=1, default=0.5)
    openness_evidence_count: int = Field(default=0)
    
    conscientiousness: float = Field(ge=0, le=1)
    conscientiousness_confidence: float = Field(ge=0, le=1, default=0.5)
    conscientiousness_evidence_count: int = Field(default=0)
    
    extraversion: float = Field(ge=0, le=1)
    extraversion_confidence: float = Field(ge=0, le=1, default=0.5)
    extraversion_evidence_count: int = Field(default=0)
    
    agreeableness: float = Field(ge=0, le=1)
    agreeableness_confidence: float = Field(ge=0, le=1, default=0.5)
    agreeableness_evidence_count: int = Field(default=0)
    
    neuroticism: float = Field(ge=0, le=1)
    neuroticism_confidence: float = Field(ge=0, le=1, default=0.5)
    neuroticism_evidence_count: int = Field(default=0)
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    def to_vector(self) -> List[float]:
        """Convert to embedding-compatible vector."""
        return [
            self.openness, self.conscientiousness, self.extraversion,
            self.agreeableness, self.neuroticism
        ]
    
    def overall_confidence(self) -> float:
        """Weighted confidence across all traits."""
        return np.mean([
            self.openness_confidence,
            self.conscientiousness_confidence,
            self.extraversion_confidence,
            self.agreeableness_confidence,
            self.neuroticism_confidence
        ])


class RegulatoryFocusState(BaseModel):
    """Current regulatory focus (promotion vs prevention)."""
    
    promotion_score: float = Field(ge=0, le=1)
    prevention_score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1, default=0.5)
    
    # What triggered this state
    trigger_signals: List[str] = Field(default_factory=list)
    
    # Temporal dynamics
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    expected_duration_minutes: Optional[int] = None
    
    @property
    def dominant_focus(self) -> str:
        return "promotion" if self.promotion_score > self.prevention_score else "prevention"
    
    @property
    def focus_strength(self) -> float:
        """How strongly one focus dominates."""
        return abs(self.promotion_score - self.prevention_score)


class ConstrualLevel(BaseModel):
    """Construal level theory state (abstract vs concrete)."""
    
    level: float = Field(
        ge=0, le=1, 
        description="0 = concrete/low-level, 1 = abstract/high-level"
    )
    confidence: float = Field(ge=0, le=1, default=0.5)
    
    # Context
    temporal_distance: Optional[float] = Field(
        None,
        description="Psychological distance of decision (0=immediate, 1=distant)"
    )
    spatial_distance: Optional[float] = None
    social_distance: Optional[float] = None
    
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class ExtendedPsychologicalProfile(BaseModel):
    """Extended psychological constructs beyond Big Five."""
    
    need_for_cognition: float = Field(ge=0, le=1)
    need_for_cognition_confidence: float = Field(ge=0, le=1, default=0.5)
    
    self_monitoring: float = Field(ge=0, le=1)
    self_monitoring_confidence: float = Field(ge=0, le=1, default=0.5)
    
    maximizer_satisficer: float = Field(
        ge=0, le=1,
        description="0 = satisficer, 1 = maximizer"
    )
    maximizer_confidence: float = Field(ge=0, le=1, default=0.5)
    
    risk_tolerance: float = Field(ge=0, le=1)
    risk_tolerance_confidence: float = Field(ge=0, le=1, default=0.5)
    
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# COGNITIVE MECHANISM MODELS
# =============================================================================

class MechanismActivation(BaseModel):
    """A detected mechanism activation."""
    
    mechanism_id: MechanismType
    activation_strength: float = Field(ge=0, le=1)
    detection_confidence: float = Field(ge=0, le=1)
    
    # What signals indicated this activation
    detection_signals: Dict[str, float] = Field(default_factory=dict)
    
    # Context
    context: Dict[str, Any] = Field(default_factory=dict)
    detected_at: datetime = Field(default_factory=datetime.utcnow)


class MechanismEffectiveness(BaseModel):
    """Learned effectiveness of a mechanism for a user."""
    
    mechanism_id: MechanismType
    user_id: str
    
    # Bayesian parameters (Beta distribution)
    alpha: float = Field(default=1.0, description="Success count + prior")
    beta: float = Field(default=1.0, description="Failure count + prior")
    
    # Derived metrics
    @property
    def success_rate(self) -> float:
        return self.alpha / (self.alpha + self.beta)
    
    @property
    def posterior_variance(self) -> float:
        n = self.alpha + self.beta
        return (self.alpha * self.beta) / (n * n * (n + 1))
    
    @property
    def confidence(self) -> float:
        """Confidence based on number of observations."""
        total = self.alpha + self.beta - 2  # Subtract priors
        return 1 - np.exp(-total / 50)  # Saturates ~250 observations
    
    # Context modulation (learned)
    time_of_day_modulation: Dict[str, float] = Field(default_factory=dict)
    category_modulation: Dict[str, float] = Field(default_factory=dict)
    state_modulation: Dict[str, float] = Field(default_factory=dict)
    
    # Tracking
    total_observations: int = Field(default=0)
    last_observation: Optional[datetime] = None
    
    def update(self, success: bool, weight: float = 1.0):
        """Update posterior with new observation."""
        if success:
            self.alpha += weight
        else:
            self.beta += weight
        self.total_observations += 1
        self.last_observation = datetime.utcnow()


class MechanismInteraction(BaseModel):
    """Discovered interaction between two mechanisms."""
    
    mechanism_1: MechanismType
    mechanism_2: MechanismType
    
    interaction_type: str = Field(
        description="synergistic, antagonistic, or conditional"
    )
    interaction_effect: float = Field(
        description="Additional effect when both activated"
    )
    
    # Statistical evidence
    sample_size: int
    p_value: float
    
    # Conditions where this interaction holds
    conditions: List[str] = Field(default_factory=list)
    
    # Discovery metadata
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    discovery_source: str = Field(default="pattern_miner")
    
    # Theoretical status
    is_theoretically_predicted: bool = Field(default=False)
    theoretical_explanation: Optional[str] = None


# =============================================================================
# USER PROFILE
# =============================================================================

class UserProfile(BaseModel):
    """Complete psychological profile for a user."""
    
    user_id: str
    
    # Identity resolution
    platform_ids: List[str] = Field(default_factory=list)
    identity_confidence: float = Field(ge=0, le=1, default=0.5)
    
    # Trait profiles
    big_five: BigFiveProfile
    extended: ExtendedPsychologicalProfile
    
    # Current state
    current_regulatory_focus: Optional[RegulatoryFocusState] = None
    current_construal_level: Optional[ConstrualLevel] = None
    
    # Mechanism effectiveness priors
    mechanism_effectiveness: Dict[str, MechanismEffectiveness] = Field(
        default_factory=dict
    )
    
    # Cluster assignment
    psychological_cluster_id: Optional[int] = None
    cluster_confidence: float = Field(ge=0, le=1, default=0.5)
    
    # Temporal patterns
    peak_receptivity_hours: List[int] = Field(default_factory=list)
    day_of_week_pattern: Optional[str] = None
    
    # Journey state
    journey_stage: Optional[str] = None
    journey_momentum: float = Field(ge=-1, le=1, default=0)
    
    # Meta
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_interaction: Optional[datetime] = None
    total_interactions: int = Field(default=0)
    
    def get_mechanism_prior(self, mechanism_id: MechanismType) -> float:
        """Get effectiveness prior for a mechanism."""
        if mechanism_id.value in self.mechanism_effectiveness:
            return self.mechanism_effectiveness[mechanism_id.value].success_rate
        return 0.5  # Uninformed prior


# =============================================================================
# BEHAVIORAL SIGNATURES
# =============================================================================

class BehavioralSignatureDefinition(BaseModel):
    """Definition of a behavioral signature pattern."""
    
    signature_id: str
    
    # Pattern definition
    pattern_rules: Dict[str, Any] = Field(
        description="Rules that define this signature"
    )
    
    # Statistical profile
    population_prevalence: float = Field(ge=0, le=1)
    outcome_correlation: float = Field(ge=-1, le=1)
    
    # Construct mapping
    is_mapped_to_construct: bool = Field(default=False)
    nearest_constructs: List[Dict[str, float]] = Field(default_factory=list)
    
    # Discovery metadata
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    discovered_by: str = Field(default="pattern_miner")
    sample_size: int = Field(default=0)


class UserSignatureMatch(BaseModel):
    """Whether a user matches a behavioral signature."""
    
    user_id: str
    signature_id: str
    
    matches: bool
    match_strength: float = Field(ge=0, le=1)
    match_confidence: float = Field(ge=0, le=1)
    
    # Evidence
    matching_signals: Dict[str, float] = Field(default_factory=dict)
    
    detected_at: datetime = Field(default_factory=datetime.utcnow)


# =============================================================================
# SUPRALIMINAL SIGNALS
# =============================================================================

class KeystrokeDynamics(BaseModel):
    """Keystroke timing and pattern signals."""
    
    average_dwell_time_ms: float
    average_flight_time_ms: float
    typing_speed_cpm: float
    error_rate: float
    hesitation_count: int
    correction_count: int
    
    # Derived metrics
    deliberation_score: float = Field(
        ge=0, le=1,
        description="Higher = more deliberate typing"
    )
    confidence_score: float = Field(
        ge=0, le=1,
        description="Higher = more confident keystrokes"
    )


class MouseDynamics(BaseModel):
    """Mouse movement pattern signals."""
    
    average_velocity: float
    velocity_variance: float
    directness_ratio: float  # Straight line / actual path
    
    hover_count: int
    hover_duration_ms: float
    
    # Derived metrics
    decisiveness_score: float = Field(ge=0, le=1)
    exploration_score: float = Field(ge=0, le=1)


class ScrollBehavior(BaseModel):
    """Scroll pattern signals."""
    
    scroll_depth: float = Field(ge=0, le=1)
    scroll_velocity: float
    pause_count: int
    pause_duration_total_ms: float
    
    reverse_scroll_count: int
    
    # Derived metrics
    engagement_score: float = Field(ge=0, le=1)
    deliberation_score: float = Field(ge=0, le=1)
    
    @property
    def scroll_pause_ratio(self) -> float:
        """Ratio of time spent paused vs scrolling."""
        if self.pause_duration_total_ms == 0:
            return 0
        # Simplified - would need total scroll time in production
        return min(1.0, self.pause_duration_total_ms / 10000)


class SupraliminalSignals(BaseModel):
    """Combined implicit behavioral signals."""
    
    user_id: str
    session_id: str
    
    keystroke: Optional[KeystrokeDynamics] = None
    mouse: Optional[MouseDynamics] = None
    scroll: Optional[ScrollBehavior] = None
    
    response_latency_ms: Optional[float] = None
    
    captured_at: datetime = Field(default_factory=datetime.utcnow)
    
    def compute_deliberation_score(self) -> float:
        """Overall deliberation score from all signals."""
        scores = []
        if self.keystroke:
            scores.append(self.keystroke.deliberation_score)
        if self.mouse:
            scores.append(1 - self.mouse.decisiveness_score)  # Inverse
        if self.scroll:
            scores.append(self.scroll.deliberation_score)
        if self.response_latency_ms:
            # Longer response = more deliberation
            scores.append(min(1.0, self.response_latency_ms / 3000))
        
        return np.mean(scores) if scores else 0.5


# =============================================================================
# DISCOVERY AND HYPOTHESIS MODELS
# =============================================================================

class TestablePrediction(BaseModel):
    """A testable prediction from a hypothesis."""
    
    prediction: str
    test_method: str  # correlation, a_b_test, segment_analysis
    
    # Test design
    required_sample_size: int = Field(default=100)
    expected_duration_hours: int = Field(default=168)
    
    # Results (filled after testing)
    test_status: str = Field(default="pending")
    result: Optional[Dict[str, Any]] = None
    validated: Optional[bool] = None


class Hypothesis(BaseModel):
    """A system-generated hypothesis about a discovery."""
    
    hypothesis_id: str
    statement: str
    confidence: float = Field(ge=0, le=1)
    
    # Generation context
    generated_from: List[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Testable predictions
    predictions: List[TestablePrediction] = Field(default_factory=list)
    
    # Priority scoring
    priority_score: float = Field(ge=0, le=10, default=5)
    priority_factors: Dict[str, float] = Field(default_factory=dict)
    
    # Status
    status: DiscoveryStatus = Field(default=DiscoveryStatus.HYPOTHESIS_GENERATED)
    
    # Review tracking
    requires_human_review: bool = Field(default=False)
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None
    
    # Outcome
    validated: Optional[bool] = None
    validation_date: Optional[datetime] = None


class Discovery(BaseModel):
    """A pattern discovered by the system."""
    
    discovery_id: str
    discovery_type: str
    description: str
    
    # Evidence
    evidence: Dict[str, Any]
    sample_size: int
    statistical_significance: float
    effect_size: float
    
    # Confidence and routing
    confidence: float = Field(ge=0, le=1)
    requires_human_review: bool = Field(default=False)
    auto_action_approved: bool = Field(default=False)
    
    # Generated hypotheses
    hypotheses: List[Hypothesis] = Field(default_factory=list)
    
    # Timestamps
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    acted_upon_at: Optional[datetime] = None
    
    # Status
    status: DiscoveryStatus = Field(default=DiscoveryStatus.DETECTED)


class EmergentConstruct(BaseModel):
    """A construct discovered by the system, not from theory."""
    
    construct_id: str
    
    # Discovery context
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    discovered_by: str = Field(default="discovery_engine")
    discovery_context: str
    
    # Defining characteristics
    defining_signatures: List[str] = Field(default_factory=list)
    defining_signals: Dict[str, Any] = Field(default_factory=dict)
    
    # Statistical validation
    sample_size: int
    effect_size: float
    statistical_significance: float
    replication_count: int = Field(default=0)
    
    # Theoretical status
    theoretical_interpretation: Optional[str] = None
    nearest_theoretical_construct: Optional[str] = None
    theoretical_distance: Optional[float] = None
    
    # Generated hypotheses about what this construct represents
    hypotheses: List[Hypothesis] = Field(default_factory=list)
    
    # Status
    status: DiscoveryStatus = Field(default=DiscoveryStatus.DETECTED)
    is_active_for_targeting: bool = Field(default=False)


# =============================================================================
# LEARNING SIGNAL MODELS
# =============================================================================

class LearningSignal(BaseModel):
    """A learning signal that propagates through the system."""
    
    signal_id: str
    signal_type: str
    source_component: str
    
    # Payload
    payload: Dict[str, Any]
    
    # Routing
    target_components: List[str] = Field(default_factory=list)
    priority: LearningPriority
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Tracking
    propagation_status: Dict[str, str] = Field(default_factory=dict)


class OutcomeObservedSignal(LearningSignal):
    """Specialized signal for observed outcomes."""
    
    signal_type: str = Field(default="outcome_observed")
    
    # Outcome details
    user_id: str
    session_id: str
    decision_id: str
    mechanism_id: str
    
    outcome: bool
    predicted_confidence: float
    
    # Context
    category: Optional[str] = None
    brand_id: Optional[str] = None
    
    # Timing
    decision_timestamp: datetime
    outcome_timestamp: datetime
    
    @property
    def latency_ms(self) -> int:
        return int((self.outcome_timestamp - self.decision_timestamp).total_seconds() * 1000)


class DiscoveryMadeSignal(LearningSignal):
    """Specialized signal for new discoveries."""
    
    signal_type: str = Field(default="discovery_made")
    
    # Discovery details
    discovery_id: str
    discovery_type: str
    confidence: float
    
    # What was discovered
    evidence: Dict[str, Any]
    hypotheses: List[Dict[str, Any]]
    
    # Action taken
    auto_action_taken: bool
    action_description: Optional[str] = None


# =============================================================================
# DECISION MODELS
# =============================================================================

class DecisionContext(BaseModel):
    """Context for an ad decision."""
    
    user_id: str
    session_id: str
    
    # User state at decision time
    user_profile: UserProfile
    current_signals: SupraliminalSignals
    
    # Content context
    content_id: Optional[str] = None
    content_category: Optional[str] = None
    priming_context: Optional[str] = None
    
    # Brand context
    brand_id: Optional[str] = None
    brand_archetype: Optional[str] = None
    
    # Temporal context
    hour_of_day: int
    day_of_week: int
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MechanismRecommendation(BaseModel):
    """Recommended mechanism activation strategy."""
    
    primary_mechanism: MechanismType
    primary_strength: float = Field(ge=0, le=1)
    
    secondary_mechanisms: List[MechanismType] = Field(default_factory=list)
    
    # Reasoning
    reasoning: str
    confidence: float = Field(ge=0, le=1)
    
    # Expected outcome
    predicted_conversion_rate: float = Field(ge=0, le=1)
    prediction_confidence: float = Field(ge=0, le=1)


class AdDecision(BaseModel):
    """A complete ad decision record."""
    
    decision_id: str
    
    # Context
    context: DecisionContext
    
    # Decision
    mechanism_recommendation: MechanismRecommendation
    selected_creative_id: str
    selected_copy_variant: str
    
    # Confidence
    overall_confidence: float = Field(ge=0, le=1)
    
    # Reasoning trace (for learning)
    reasoning_trace: Dict[str, Any] = Field(default_factory=dict)
    
    # Timing
    decision_timestamp: datetime = Field(default_factory=datetime.utcnow)
    latency_ms: int
    
    # Outcome (filled later)
    outcome: Optional[bool] = None
    outcome_timestamp: Optional[datetime] = None


# =============================================================================
# GRAPH SYNC MODELS
# =============================================================================

class Neo4jSyncRequest(BaseModel):
    """Request to sync data to Neo4j."""
    
    operation: str  # create, update, delete, merge
    node_type: str
    properties: Dict[str, Any]
    
    # For relationships
    relationship_type: Optional[str] = None
    source_id: Optional[str] = None
    target_id: Optional[str] = None
    relationship_properties: Optional[Dict[str, Any]] = None
    
    # Sync metadata
    priority: LearningPriority = Field(default=LearningPriority.ASYNC)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GraphQueryResult(BaseModel):
    """Result from a graph query."""
    
    query_id: str
    query_type: str
    
    # Results
    records: List[Dict[str, Any]]
    record_count: int
    
    # Performance
    execution_time_ms: float
    
    # Metadata
    executed_at: datetime = Field(default_factory=datetime.utcnow)
```

## 1.2 Event Contracts

```python
"""
ADAM Event Contracts
Kafka event schemas for cross-component communication
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


# =============================================================================
# BASE EVENT
# =============================================================================

class ADAMEvent(BaseModel):
    """Base class for all ADAM events."""
    
    event_id: str
    event_type: str
    source_component: str
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Tracing
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# =============================================================================
# OUTCOME EVENTS
# =============================================================================

class OutcomeObservedEvent(ADAMEvent):
    """Published when an interaction outcome is observed."""
    
    event_type: str = Field(default="outcome.observed")
    
    # Core identifiers
    user_id: str
    session_id: str
    decision_id: str
    
    # Outcome details
    outcome_type: str  # conversion, click, engagement, bounce
    outcome_value: bool
    outcome_magnitude: Optional[float] = None  # For non-binary outcomes
    
    # Decision context
    mechanism_id: str
    mechanism_activation_strength: float
    predicted_confidence: float
    
    # Attribution context
    category: Optional[str] = None
    brand_id: Optional[str] = None
    creative_id: Optional[str] = None
    
    # Timing
    decision_timestamp: datetime
    outcome_timestamp: datetime


class ConversionEvent(ADAMEvent):
    """Published when a conversion occurs."""
    
    event_type: str = Field(default="outcome.conversion")
    
    user_id: str
    session_id: str
    
    # Conversion details
    conversion_type: str  # purchase, signup, download, etc.
    conversion_value: float  # Monetary or score value
    
    # Attribution
    attributed_decisions: List[str]  # Decision IDs that led here
    attribution_weights: Dict[str, float]  # Decision ID → weight


# =============================================================================
# LEARNING EVENTS
# =============================================================================

class LearningSignalEvent(ADAMEvent):
    """Published when a learning signal should propagate."""
    
    event_type: str = Field(default="learning.signal")
    
    signal_type: str
    payload: Dict[str, Any]
    
    # Routing
    target_components: List[str] = Field(default_factory=list)
    priority: str  # immediate, fast, async, batch
    
    # What triggered this signal
    trigger_event_id: Optional[str] = None


class PosteriorUpdateEvent(ADAMEvent):
    """Published when a posterior is updated."""
    
    event_type: str = Field(default="learning.posterior_update")
    
    user_id: str
    mechanism_id: str
    
    # Old values
    old_alpha: float
    old_beta: float
    old_success_rate: float
    
    # New values
    new_alpha: float
    new_beta: float
    new_success_rate: float
    
    # What caused this update
    triggering_outcome_id: str
    credit_weight: float


class CalibrationUpdateEvent(ADAMEvent):
    """Published when calibration data is updated."""
    
    event_type: str = Field(default="learning.calibration_update")
    
    # Calibration bucket
    confidence_bucket: int  # 0-10 representing 0.0-1.0
    
    # Update
    total_predictions: int
    positive_outcomes: int
    calibration_error: float
    
    # Trigger
    triggering_outcome_id: str


# =============================================================================
# DISCOVERY EVENTS
# =============================================================================

class DiscoveryMadeEvent(ADAMEvent):
    """Published when the discovery engine finds something."""
    
    event_type: str = Field(default="discovery.made")
    
    discovery_id: str
    discovery_type: str  # mechanism_interaction, behavioral_signature, etc.
    
    # What was found
    description: str
    evidence: Dict[str, Any]
    
    # Statistical support
    sample_size: int
    effect_size: float
    statistical_significance: float
    
    # Confidence and routing
    confidence: float
    auto_action_taken: bool
    requires_human_review: bool


class HypothesisGeneratedEvent(ADAMEvent):
    """Published when a hypothesis is generated."""
    
    event_type: str = Field(default="discovery.hypothesis_generated")
    
    hypothesis_id: str
    discovery_id: str  # What discovery triggered this
    
    statement: str
    confidence: float
    
    # Testing plan
    predictions: List[Dict[str, Any]]
    test_method: str
    estimated_test_duration_hours: int


class HypothesisValidatedEvent(ADAMEvent):
    """Published when a hypothesis is validated or rejected."""
    
    event_type: str = Field(default="discovery.hypothesis_validated")
    
    hypothesis_id: str
    
    validated: bool  # True = validated, False = rejected
    
    # Evidence
    test_results: Dict[str, Any]
    final_p_value: float
    final_effect_size: float
    
    # Impact
    knowledge_integrated: bool
    affected_components: List[str]


# =============================================================================
# STATE EVENTS
# =============================================================================

class StateTransitionEvent(ADAMEvent):
    """Published when a user's psychological state changes."""
    
    event_type: str = Field(default="state.transition")
    
    user_id: str
    session_id: str
    
    state_type: str  # regulatory_focus, construal_level, etc.
    
    # Transition
    old_state: Dict[str, Any]
    new_state: Dict[str, Any]
    transition_confidence: float
    
    # Trigger
    trigger_signals: List[str]


class JourneyProgressEvent(ADAMEvent):
    """Published when a user progresses in their journey."""
    
    event_type: str = Field(default="state.journey_progress")
    
    user_id: str
    
    old_stage: str
    new_stage: str
    
    momentum_change: float
    confidence: float


# =============================================================================
# MECHANISM EVENTS
# =============================================================================

class MechanismActivatedEvent(ADAMEvent):
    """Published when a mechanism activation is detected."""
    
    event_type: str = Field(default="mechanism.activated")
    
    user_id: str
    session_id: str
    
    mechanism_id: str
    activation_strength: float
    detection_confidence: float
    
    # What signals indicated this
    detection_signals: Dict[str, float]
    
    # Context
    content_id: Optional[str] = None
    priming_context: Optional[str] = None


class MechanismInteractionDiscoveredEvent(ADAMEvent):
    """Published when a mechanism interaction is discovered."""
    
    event_type: str = Field(default="mechanism.interaction_discovered")
    
    mechanism_1: str
    mechanism_2: str
    
    interaction_type: str  # synergistic, antagonistic, conditional
    interaction_effect: float
    
    sample_size: int
    p_value: float
    
    conditions: List[str]


# =============================================================================
# CACHE EVENTS
# =============================================================================

class CacheInvalidationEvent(ADAMEvent):
    """Published when caches need invalidation."""
    
    event_type: str = Field(default="cache.invalidation")
    
    invalidation_type: str  # user, mechanism, segment, global
    
    # What to invalidate
    cache_keys: List[str] = Field(default_factory=list)
    cache_patterns: List[str] = Field(default_factory=list)
    
    # Scope
    user_id: Optional[str] = None
    mechanism_id: Optional[str] = None
    segment_id: Optional[str] = None
    
    # Reason
    trigger_event_id: str
    reason: str
```

---

# Part 2: LangGraph Workflow Definitions

## 2.1 Core Decision Workflow

```python
"""
ADAM Core Decision Workflow
LangGraph implementation for ad decisions
"""

from typing import TypedDict, Annotated, Sequence, Dict, Any, List
from datetime import datetime
import operator
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage

from adam.models.core import (
    UserProfile, DecisionContext, AdDecision, 
    MechanismRecommendation, SupraliminalSignals
)
from adam.services.graph_service import GraphService
from adam.services.cache_service import CacheService
from adam.services.learning_propagator import LearningPropagator


# =============================================================================
# STATE DEFINITION
# =============================================================================

class DecisionState(TypedDict):
    """State passed through the decision workflow."""
    
    # Input
    user_id: str
    session_id: str
    request_timestamp: datetime
    
    # Retrieved context
    user_profile: UserProfile | None
    current_signals: SupraliminalSignals | None
    mechanism_priors: Dict[str, float]
    
    # Graph context
    graph_context: Dict[str, Any]
    
    # Reasoning
    mechanism_reasoning: str
    selected_mechanism: str
    mechanism_confidence: float
    
    # Decision
    recommendation: MechanismRecommendation | None
    decision: AdDecision | None
    
    # Messages for Claude reasoning
    messages: Annotated[Sequence[BaseMessage], operator.add]
    
    # Workflow tracking
    workflow_stage: str
    latency_breakdown: Dict[str, float]
    errors: List[str]


# =============================================================================
# WORKFLOW NODES
# =============================================================================

async def retrieve_user_profile(state: DecisionState) -> DecisionState:
    """Retrieve user profile from graph and cache."""
    
    start_time = datetime.utcnow()
    
    # Try cache first
    cache = CacheService()
    cached_profile = await cache.get_user_profile(state['user_id'])
    
    if cached_profile:
        state['user_profile'] = cached_profile
    else:
        # Fetch from Neo4j
        graph = GraphService()
        profile = await graph.get_user_profile(state['user_id'])
        state['user_profile'] = profile
        
        # Cache for next time
        await cache.set_user_profile(state['user_id'], profile)
    
    state['latency_breakdown']['profile_retrieval'] = (
        datetime.utcnow() - start_time
    ).total_seconds() * 1000
    state['workflow_stage'] = 'profile_retrieved'
    
    return state


async def retrieve_mechanism_priors(state: DecisionState) -> DecisionState:
    """Retrieve mechanism effectiveness priors from graph."""
    
    start_time = datetime.utcnow()
    
    graph = GraphService()
    
    # Get user's mechanism effectiveness history
    priors = await graph.get_mechanism_priors(state['user_id'])
    
    # Enrich with cluster-level priors if user data is sparse
    if state['user_profile'] and state['user_profile'].total_interactions < 20:
        cluster_id = state['user_profile'].psychological_cluster_id
        if cluster_id:
            cluster_priors = await graph.get_cluster_mechanism_priors(cluster_id)
            # Blend user and cluster priors
            for mech, prior in cluster_priors.items():
                if mech not in priors or priors[mech]['confidence'] < 0.5:
                    priors[mech] = prior
    
    state['mechanism_priors'] = priors
    state['latency_breakdown']['prior_retrieval'] = (
        datetime.utcnow() - start_time
    ).total_seconds() * 1000
    state['workflow_stage'] = 'priors_retrieved'
    
    return state


async def retrieve_graph_context(state: DecisionState) -> DecisionState:
    """Retrieve relevant graph context for reasoning."""
    
    start_time = datetime.utcnow()
    
    graph = GraphService()
    
    # Get contextual information from graph
    context = await graph.get_decision_context(
        user_id=state['user_id'],
        traits=state['user_profile'].big_five if state['user_profile'] else None,
        current_hour=datetime.utcnow().hour
    )
    
    # Include any relevant discoveries
    context['recent_discoveries'] = await graph.get_relevant_discoveries(
        user_cluster=state['user_profile'].psychological_cluster_id
        if state['user_profile'] else None
    )
    
    state['graph_context'] = context
    state['latency_breakdown']['graph_context'] = (
        datetime.utcnow() - start_time
    ).total_seconds() * 1000
    state['workflow_stage'] = 'graph_context_retrieved'
    
    return state


async def reason_about_mechanisms(state: DecisionState) -> DecisionState:
    """Use Claude to reason about which mechanisms to activate."""
    
    start_time = datetime.utcnow()
    
    # Build prompt with all context
    prompt = build_mechanism_reasoning_prompt(
        user_profile=state['user_profile'],
        mechanism_priors=state['mechanism_priors'],
        graph_context=state['graph_context'],
        current_signals=state['current_signals']
    )
    
    # Call Claude
    llm = ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0)
    
    messages = state['messages'] + [HumanMessage(content=prompt)]
    
    response = await llm.ainvoke(messages)
    
    # Parse response
    reasoning, selected, confidence = parse_mechanism_response(response.content)
    
    state['mechanism_reasoning'] = reasoning
    state['selected_mechanism'] = selected
    state['mechanism_confidence'] = confidence
    state['messages'] = messages + [response]
    
    state['latency_breakdown']['mechanism_reasoning'] = (
        datetime.utcnow() - start_time
    ).total_seconds() * 1000
    state['workflow_stage'] = 'mechanism_selected'
    
    return state


async def verify_with_graph(state: DecisionState) -> DecisionState:
    """Verify Claude's reasoning against graph knowledge."""
    
    start_time = datetime.utcnow()
    
    graph = GraphService()
    
    # Check if selected mechanism has empirical support for this user
    verification = await graph.verify_mechanism_selection(
        user_id=state['user_id'],
        mechanism_id=state['selected_mechanism'],
        user_profile=state['user_profile']
    )
    
    if not verification['supported']:
        # Add verification feedback and re-reason if needed
        if state['mechanism_confidence'] < 0.7:
            # Low confidence + no support = try different mechanism
            state['graph_context']['verification_feedback'] = verification
            state['workflow_stage'] = 'needs_re_reasoning'
        else:
            # High confidence from Claude, log for learning
            state['graph_context']['verification_override'] = True
    
    state['latency_breakdown']['verification'] = (
        datetime.utcnow() - start_time
    ).total_seconds() * 1000
    
    if state['workflow_stage'] != 'needs_re_reasoning':
        state['workflow_stage'] = 'verified'
    
    return state


async def generate_recommendation(state: DecisionState) -> DecisionState:
    """Generate final mechanism recommendation."""
    
    start_time = datetime.utcnow()
    
    recommendation = MechanismRecommendation(
        primary_mechanism=state['selected_mechanism'],
        primary_strength=state['mechanism_confidence'],
        secondary_mechanisms=extract_secondary_mechanisms(state['mechanism_reasoning']),
        reasoning=state['mechanism_reasoning'],
        confidence=state['mechanism_confidence'],
        predicted_conversion_rate=estimate_conversion_rate(
            state['mechanism_priors'],
            state['selected_mechanism'],
            state['user_profile']
        ),
        prediction_confidence=calculate_prediction_confidence(
            state['mechanism_priors'],
            state['selected_mechanism']
        )
    )
    
    state['recommendation'] = recommendation
    state['latency_breakdown']['recommendation'] = (
        datetime.utcnow() - start_time
    ).total_seconds() * 1000
    state['workflow_stage'] = 'recommendation_generated'
    
    return state


async def finalize_decision(state: DecisionState) -> DecisionState:
    """Create final decision record."""
    
    start_time = datetime.utcnow()
    
    total_latency = sum(state['latency_breakdown'].values())
    
    decision = AdDecision(
        decision_id=f"dec_{state['user_id']}_{state['session_id']}_{int(datetime.utcnow().timestamp())}",
        context=DecisionContext(
            user_id=state['user_id'],
            session_id=state['session_id'],
            user_profile=state['user_profile'],
            current_signals=state['current_signals'],
            timestamp=state['request_timestamp']
        ),
        mechanism_recommendation=state['recommendation'],
        selected_creative_id="",  # Filled by downstream
        selected_copy_variant="",  # Filled by downstream
        overall_confidence=state['recommendation'].confidence,
        reasoning_trace={
            'mechanism_reasoning': state['mechanism_reasoning'],
            'graph_context': state['graph_context'],
            'latency_breakdown': state['latency_breakdown']
        },
        decision_timestamp=datetime.utcnow(),
        latency_ms=int(total_latency)
    )
    
    state['decision'] = decision
    state['workflow_stage'] = 'complete'
    
    # Emit decision for learning
    await emit_decision_event(decision)
    
    return state


# =============================================================================
# WORKFLOW DEFINITION
# =============================================================================

def should_re_reason(state: DecisionState) -> str:
    """Determine if we need to re-reason after verification."""
    if state['workflow_stage'] == 'needs_re_reasoning':
        return "re_reason"
    return "generate"


def create_decision_workflow() -> StateGraph:
    """Create the LangGraph workflow for ad decisions."""
    
    workflow = StateGraph(DecisionState)
    
    # Add nodes
    workflow.add_node("retrieve_profile", retrieve_user_profile)
    workflow.add_node("retrieve_priors", retrieve_mechanism_priors)
    workflow.add_node("retrieve_graph_context", retrieve_graph_context)
    workflow.add_node("reason", reason_about_mechanisms)
    workflow.add_node("verify", verify_with_graph)
    workflow.add_node("generate", generate_recommendation)
    workflow.add_node("finalize", finalize_decision)
    
    # Define edges
    workflow.set_entry_point("retrieve_profile")
    workflow.add_edge("retrieve_profile", "retrieve_priors")
    workflow.add_edge("retrieve_priors", "retrieve_graph_context")
    workflow.add_edge("retrieve_graph_context", "reason")
    workflow.add_edge("reason", "verify")
    
    # Conditional edge after verification
    workflow.add_conditional_edges(
        "verify",
        should_re_reason,
        {
            "re_reason": "reason",  # Loop back to reasoning
            "generate": "generate"   # Continue to generation
        }
    )
    
    workflow.add_edge("generate", "finalize")
    workflow.add_edge("finalize", END)
    
    return workflow.compile()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def build_mechanism_reasoning_prompt(
    user_profile: UserProfile,
    mechanism_priors: Dict[str, float],
    graph_context: Dict[str, Any],
    current_signals: SupraliminalSignals
) -> str:
    """Build the prompt for mechanism reasoning."""
    
    prompt = f"""You are an expert in psychological advertising science. Based on the following user profile and context, recommend which cognitive mechanism(s) to activate for maximum effectiveness.

## User Psychological Profile

Big Five Traits:
- Openness: {user_profile.big_five.openness:.2f} (confidence: {user_profile.big_five.openness_confidence:.2f})
- Conscientiousness: {user_profile.big_five.conscientiousness:.2f} (confidence: {user_profile.big_five.conscientiousness_confidence:.2f})
- Extraversion: {user_profile.big_five.extraversion:.2f} (confidence: {user_profile.big_five.extraversion_confidence:.2f})
- Agreeableness: {user_profile.big_five.agreeableness:.2f} (confidence: {user_profile.big_five.agreeableness_confidence:.2f})
- Neuroticism: {user_profile.big_five.neuroticism:.2f} (confidence: {user_profile.big_five.neuroticism_confidence:.2f})

Current State:
- Regulatory Focus: {user_profile.current_regulatory_focus.dominant_focus if user_profile.current_regulatory_focus else 'unknown'}
- Construal Level: {user_profile.current_construal_level.level if user_profile.current_construal_level else 'unknown'}

## Mechanism Effectiveness History (User's Priors)
"""
    
    for mech, prior_data in mechanism_priors.items():
        prompt += f"- {mech}: {prior_data['success_rate']:.2f} (n={prior_data['observations']})\n"
    
    prompt += f"""

## Current Behavioral Signals
- Deliberation Score: {current_signals.compute_deliberation_score():.2f}
- Response Latency: {current_signals.response_latency_ms}ms

## Graph Context
{graph_context}

## Task
1. Analyze which cognitive mechanism(s) would be most effective for this user
2. Explain your reasoning based on psychological theory AND the empirical priors
3. Provide a confidence score (0-1) for your recommendation

Format your response as:
MECHANISM: [mechanism_name]
CONFIDENCE: [0-1]
REASONING: [your explanation]
"""
    
    return prompt


def parse_mechanism_response(response: str) -> tuple:
    """Parse Claude's mechanism response."""
    
    lines = response.strip().split('\n')
    
    mechanism = None
    confidence = 0.5
    reasoning = ""
    
    for line in lines:
        if line.startswith('MECHANISM:'):
            mechanism = line.replace('MECHANISM:', '').strip()
        elif line.startswith('CONFIDENCE:'):
            try:
                confidence = float(line.replace('CONFIDENCE:', '').strip())
            except ValueError:
                confidence = 0.5
        elif line.startswith('REASONING:'):
            reasoning = line.replace('REASONING:', '').strip()
    
    # Get rest of response as reasoning if not captured
    if not reasoning:
        reasoning = response
    
    return reasoning, mechanism, confidence
```

---

# Part 3: Service Implementations

## 3.1 Graph Service

```python
"""
ADAM Graph Service
Neo4j integration for the cognitive medium
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from neo4j import AsyncGraphDatabase
from adam.models.core import UserProfile, BigFiveProfile, ExtendedPsychologicalProfile


class GraphService:
    """Service for interacting with Neo4j cognitive medium."""
    
    def __init__(self, uri: str = None, user: str = None, password: str = None):
        self.uri = uri or "bolt://localhost:7687"
        self.user = user or "neo4j"
        self.password = password or "password"
        self._driver = None
    
    async def connect(self):
        """Initialize driver connection."""
        if not self._driver:
            self._driver = AsyncGraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
    
    async def close(self):
        """Close driver connection."""
        if self._driver:
            await self._driver.close()
    
    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Retrieve complete user profile from graph."""
        
        await self.connect()
        
        query = """
        MATCH (u:User {user_id: $user_id})
        
        // Get mechanism effectiveness
        OPTIONAL MATCH (u)-[r:RESPONDS_TO]->(m:CognitiveMechanism)
        
        // Get current state
        OPTIONAL MATCH (u)-[:CURRENT_STATE]->(s:PsychologicalState)
        
        RETURN u, 
               collect({
                   mechanism: m.mechanism_id, 
                   alpha: r.alpha, 
                   beta: r.beta,
                   observations: r.total_observations
               }) as mechanisms,
               s
        """
        
        async with self._driver.session() as session:
            result = await session.run(query, user_id=user_id)
            record = await result.single()
        
        if not record:
            return None
        
        user_data = dict(record['u'])
        mechanisms = record['mechanisms']
        state_data = dict(record['s']) if record['s'] else {}
        
        # Build profile
        profile = UserProfile(
            user_id=user_id,
            big_five=BigFiveProfile(
                openness=user_data.get('openness', 0.5),
                openness_confidence=user_data.get('openness_confidence', 0.5),
                conscientiousness=user_data.get('conscientiousness', 0.5),
                conscientiousness_confidence=user_data.get('conscientiousness_confidence', 0.5),
                extraversion=user_data.get('extraversion', 0.5),
                extraversion_confidence=user_data.get('extraversion_confidence', 0.5),
                agreeableness=user_data.get('agreeableness', 0.5),
                agreeableness_confidence=user_data.get('agreeableness_confidence', 0.5),
                neuroticism=user_data.get('neuroticism', 0.5),
                neuroticism_confidence=user_data.get('neuroticism_confidence', 0.5)
            ),
            extended=ExtendedPsychologicalProfile(
                need_for_cognition=user_data.get('need_for_cognition', 0.5),
                self_monitoring=user_data.get('self_monitoring', 0.5),
                maximizer_satisficer=user_data.get('maximizer_satisficer', 0.5),
                risk_tolerance=user_data.get('risk_tolerance', 0.5)
            ),
            psychological_cluster_id=user_data.get('psychological_cluster_id'),
            total_interactions=user_data.get('total_interactions', 0)
        )
        
        # Add mechanism effectiveness
        for mech in mechanisms:
            if mech['mechanism']:
                from adam.models.core import MechanismEffectiveness
                profile.mechanism_effectiveness[mech['mechanism']] = MechanismEffectiveness(
                    mechanism_id=mech['mechanism'],
                    user_id=user_id,
                    alpha=mech['alpha'] or 1.0,
                    beta=mech['beta'] or 1.0,
                    total_observations=mech['observations'] or 0
                )
        
        return profile
    
    async def get_mechanism_priors(self, user_id: str) -> Dict[str, Dict[str, float]]:
        """Get mechanism effectiveness priors for a user."""
        
        await self.connect()
        
        query = """
        MATCH (u:User {user_id: $user_id})-[r:RESPONDS_TO]->(m:CognitiveMechanism)
        RETURN m.mechanism_id as mechanism,
               r.alpha as alpha,
               r.beta as beta,
               r.total_observations as observations,
               r.alpha / (r.alpha + r.beta) as success_rate
        """
        
        async with self._driver.session() as session:
            result = await session.run(query, user_id=user_id)
            records = await result.data()
        
        priors = {}
        for record in records:
            priors[record['mechanism']] = {
                'success_rate': record['success_rate'],
                'alpha': record['alpha'],
                'beta': record['beta'],
                'observations': record['observations'],
                'confidence': 1 - np.exp(-record['observations'] / 50)
            }
        
        return priors
    
    async def get_cluster_mechanism_priors(
        self, 
        cluster_id: int
    ) -> Dict[str, Dict[str, float]]:
        """Get mechanism priors aggregated at cluster level."""
        
        await self.connect()
        
        query = """
        MATCH (u:User {psychological_cluster_id: $cluster_id})-[r:RESPONDS_TO]->(m:CognitiveMechanism)
        WITH m.mechanism_id as mechanism,
             sum(r.alpha) as total_alpha,
             sum(r.beta) as total_beta,
             count(u) as user_count
        RETURN mechanism,
               total_alpha,
               total_beta,
               total_alpha / (total_alpha + total_beta) as success_rate,
               user_count
        """
        
        async with self._driver.session() as session:
            result = await session.run(query, cluster_id=cluster_id)
            records = await result.data()
        
        priors = {}
        for record in records:
            priors[record['mechanism']] = {
                'success_rate': record['success_rate'],
                'alpha': record['total_alpha'],
                'beta': record['total_beta'],
                'observations': int(record['total_alpha'] + record['total_beta'] - 2 * record['user_count']),
                'confidence': 0.7  # Cluster-level gets moderate confidence
            }
        
        return priors
    
    async def update_mechanism_posterior(
        self,
        user_id: str,
        mechanism_id: str,
        success: bool,
        weight: float = 1.0
    ):
        """Update user's mechanism posterior after an outcome."""
        
        await self.connect()
        
        query = """
        MATCH (u:User {user_id: $user_id})
        MATCH (m:CognitiveMechanism {mechanism_id: $mechanism_id})
        
        MERGE (u)-[r:RESPONDS_TO]->(m)
        ON CREATE SET r.alpha = 1.0, r.beta = 1.0, r.total_observations = 0
        
        SET r.alpha = CASE WHEN $success THEN r.alpha + $weight ELSE r.alpha END,
            r.beta = CASE WHEN NOT $success THEN r.beta + $weight ELSE r.beta END,
            r.total_observations = r.total_observations + 1,
            r.last_observation = datetime()
        
        RETURN r.alpha as alpha, r.beta as beta
        """
        
        async with self._driver.session() as session:
            await session.run(
                query,
                user_id=user_id,
                mechanism_id=mechanism_id,
                success=success,
                weight=weight
            )
    
    async def create_discovery(self, discovery: 'Discovery'):
        """Store a discovery in the graph."""
        
        await self.connect()
        
        query = """
        CREATE (d:Discovery {
            discovery_id: $discovery_id,
            discovery_type: $discovery_type,
            description: $description,
            evidence: $evidence,
            sample_size: $sample_size,
            effect_size: $effect_size,
            statistical_significance: $statistical_significance,
            confidence: $confidence,
            status: $status,
            discovered_at: datetime()
        })
        
        // Create hypotheses
        WITH d
        UNWIND $hypotheses as hyp
        CREATE (h:Hypothesis {
            hypothesis_id: hyp.hypothesis_id,
            statement: hyp.statement,
            confidence: hyp.confidence,
            status: 'pending'
        })
        CREATE (d)-[:GENERATED]->(h)
        
        RETURN d
        """
        
        async with self._driver.session() as session:
            await session.run(
                query,
                discovery_id=discovery.discovery_id,
                discovery_type=discovery.discovery_type,
                description=discovery.description,
                evidence=str(discovery.evidence),
                sample_size=discovery.sample_size,
                effect_size=discovery.effect_size,
                statistical_significance=discovery.statistical_significance,
                confidence=discovery.confidence,
                status=discovery.status.value,
                hypotheses=[
                    {
                        'hypothesis_id': h.hypothesis_id,
                        'statement': h.statement,
                        'confidence': h.confidence
                    }
                    for h in discovery.hypotheses
                ]
            )
    
    async def create_mechanism_interaction(
        self,
        mechanism_1: str,
        mechanism_2: str,
        interaction_type: str,
        interaction_effect: float,
        sample_size: int,
        p_value: float,
        conditions: List[str]
    ):
        """Create a discovered mechanism interaction in the graph."""
        
        await self.connect()
        
        query = """
        MATCH (m1:CognitiveMechanism {mechanism_id: $mechanism_1})
        MATCH (m2:CognitiveMechanism {mechanism_id: $mechanism_2})
        
        MERGE (m1)-[i:INTERACTS_WITH]-(m2)
        SET i.interaction_type = $interaction_type,
            i.interaction_effect = $interaction_effect,
            i.sample_size = $sample_size,
            i.p_value = $p_value,
            i.conditions = $conditions,
            i.discovered_at = datetime(),
            i.is_validated = false
        
        RETURN i
        """
        
        async with self._driver.session() as session:
            await session.run(
                query,
                mechanism_1=mechanism_1,
                mechanism_2=mechanism_2,
                interaction_type=interaction_type,
                interaction_effect=interaction_effect,
                sample_size=sample_size,
                p_value=p_value,
                conditions=conditions
            )
    
    async def run_discovery_query(self, query_type: str) -> List[Dict[str, Any]]:
        """Run a predefined discovery query."""
        
        await self.connect()
        
        queries = {
            'mechanism_interactions': """
                MATCH (u:User)-[r1:RESPONDS_TO]->(m1:CognitiveMechanism)
                MATCH (u)-[r2:RESPONDS_TO]->(m2:CognitiveMechanism)
                WHERE m1.mechanism_id < m2.mechanism_id
                AND r1.success_rate > 0.7 AND r2.success_rate > 0.7
                WITH m1, m2, count(DISTINCT u) as co_responders,
                     avg(r1.success_rate + r2.success_rate) / 2 as combined_rate
                WHERE co_responders > 100
                AND NOT EXISTS((m1)-[:INTERACTS_WITH]-(m2))
                MATCH (m1)<-[r1all:RESPONDS_TO]-(:User)
                MATCH (m2)<-[r2all:RESPONDS_TO]-(:User)
                WITH m1, m2, co_responders, combined_rate,
                     avg(r1all.success_rate) as m1_base,
                     avg(r2all.success_rate) as m2_base
                WHERE combined_rate > (m1_base + m2_base) / 2 * 1.1
                RETURN m1.mechanism_id as mech1, m2.mechanism_id as mech2,
                       co_responders, combined_rate,
                       (m1_base + m2_base) / 2 as baseline,
                       combined_rate / ((m1_base + m2_base) / 2) as synergy
                ORDER BY synergy DESC
                LIMIT 10
            """,
            
            'unmapped_signatures': """
                MATCH (bs:BehavioralSignature)
                WHERE bs.outcome_correlation > 0.25
                AND bs.population_prevalence > 0.03
                AND bs.is_mapped_to_construct = false
                RETURN bs
                ORDER BY bs.outcome_correlation DESC
                LIMIT 20
            """,
            
            'segment_anomalies': """
                MATCH (u:User)-[r:RESPONDS_TO]->(m:CognitiveMechanism)
                WITH u.psychological_cluster_id as cluster,
                     m.mechanism_id as mechanism,
                     avg(r.success_rate) as cluster_avg,
                     count(u) as cluster_size
                WHERE cluster_size > 100
                MATCH (:User)-[rall:RESPONDS_TO]->(mall:CognitiveMechanism {mechanism_id: mechanism})
                WITH cluster, mechanism, cluster_avg, cluster_size,
                     avg(rall.success_rate) as pop_avg,
                     stdev(rall.success_rate) as pop_stdev
                WHERE abs(cluster_avg - pop_avg) > 2 * pop_stdev
                RETURN cluster, mechanism, cluster_avg, pop_avg,
                       (cluster_avg - pop_avg) / pop_stdev as z_score
                ORDER BY abs(z_score) DESC
                LIMIT 10
            """
        }
        
        query = queries.get(query_type)
        if not query:
            raise ValueError(f"Unknown query type: {query_type}")
        
        async with self._driver.session() as session:
            result = await session.run(query)
            return await result.data()
```

---

# Part 4: Prometheus Metrics

```python
"""
ADAM Prometheus Metrics
Comprehensive observability for the cognitive ecosystem
"""

from prometheus_client import Counter, Histogram, Gauge, Summary
from functools import wraps
import time


# =============================================================================
# DECISION METRICS
# =============================================================================

DECISION_COUNTER = Counter(
    'adam_decisions_total',
    'Total number of ad decisions made',
    ['mechanism', 'outcome', 'confidence_bucket']
)

DECISION_LATENCY = Histogram(
    'adam_decision_latency_seconds',
    'Latency of ad decisions',
    ['stage'],
    buckets=[0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 1.0]
)

DECISION_CONFIDENCE = Histogram(
    'adam_decision_confidence',
    'Confidence distribution of decisions',
    ['mechanism'],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

# =============================================================================
# LEARNING METRICS
# =============================================================================

LEARNING_SIGNAL_COUNTER = Counter(
    'adam_learning_signals_total',
    'Total learning signals processed',
    ['signal_type', 'priority']
)

POSTERIOR_UPDATE_COUNTER = Counter(
    'adam_posterior_updates_total',
    'Total posterior updates',
    ['mechanism', 'outcome']
)

LEARNING_LATENCY = Histogram(
    'adam_learning_latency_seconds',
    'Latency of learning signal propagation',
    ['priority'],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0]
)

CALIBRATION_ERROR = Gauge(
    'adam_calibration_error',
    'Expected calibration error',
    ['confidence_bucket']
)

# =============================================================================
# DISCOVERY METRICS
# =============================================================================

DISCOVERY_COUNTER = Counter(
    'adam_discoveries_total',
    'Total discoveries made',
    ['discovery_type', 'action_taken']
)

HYPOTHESIS_COUNTER = Counter(
    'adam_hypotheses_total',
    'Total hypotheses generated',
    ['status']  # pending, testing, validated, rejected
)

HYPOTHESIS_VALIDATION_RATE = Gauge(
    'adam_hypothesis_validation_rate',
    'Rate of hypothesis validation',
    ['discovery_type']
)

EMERGENT_CONSTRUCTS = Gauge(
    'adam_emergent_constructs_total',
    'Total emergent constructs discovered'
)

# =============================================================================
# GRAPH METRICS
# =============================================================================

GRAPH_QUERY_LATENCY = Histogram(
    'adam_graph_query_latency_seconds',
    'Latency of Neo4j queries',
    ['query_type'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5]
)

GRAPH_RELATIONSHIPS = Gauge(
    'adam_graph_relationships_total',
    'Total relationships in the graph',
    ['relationship_type']
)

GRAPH_NODES = Gauge(
    'adam_graph_nodes_total',
    'Total nodes in the graph',
    ['node_type']
)

# =============================================================================
# MECHANISM METRICS
# =============================================================================

MECHANISM_ACTIVATION_COUNTER = Counter(
    'adam_mechanism_activations_total',
    'Total mechanism activations detected',
    ['mechanism', 'strength_bucket']
)

MECHANISM_EFFECTIVENESS = Gauge(
    'adam_mechanism_effectiveness',
    'Average mechanism effectiveness',
    ['mechanism', 'segment']
)

MECHANISM_INTERACTION_COUNTER = Counter(
    'adam_mechanism_interactions_total',
    'Total mechanism interactions discovered',
    ['interaction_type']
)

# =============================================================================
# MOAT METRICS
# =============================================================================

FLYWHEEL_VELOCITY = Gauge(
    'adam_flywheel_velocity',
    'Rate of flywheel progression',
    ['stage']  # users, interactions, relationships, predictions
)

KNOWLEDGE_ACCUMULATION_RATE = Gauge(
    'adam_knowledge_accumulation_rate',
    'Rate of new knowledge accumulation per day',
    ['knowledge_type']  # relationships, discoveries, validations
)

PROPRIETARY_CONSTRUCTS = Gauge(
    'adam_proprietary_constructs_total',
    'Total proprietary psychological constructs'
)

TIME_TO_REPLICATE_ESTIMATE = Gauge(
    'adam_time_to_replicate_months',
    'Estimated time for competitor to replicate current state'
)

# =============================================================================
# HELPER DECORATORS
# =============================================================================

def track_latency(metric: Histogram, labels: dict = None):
    """Decorator to track function latency."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
        return wrapper
    return decorator


def track_counter(metric: Counter, labels: dict = None):
    """Decorator to increment counter on function call."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            if labels:
                metric.labels(**labels).inc()
            else:
                metric.inc()
            return result
        return wrapper
    return decorator
```

---

# Conclusion

This implementation companion provides:

1. **Complete Pydantic Models** - Type-safe domain models for all ADAM concepts
2. **Event Contracts** - Kafka event schemas for cross-component communication
3. **LangGraph Workflows** - Decision workflow implementation
4. **Graph Service** - Neo4j integration for the cognitive medium
5. **Prometheus Metrics** - Comprehensive observability including moat metrics

Together with the main architecture document, this provides a complete foundation for implementing ADAM as a cognitive ecosystem.

---

*ADAM Implementation Companion v1.0*
*~40KB of production-ready code patterns*
