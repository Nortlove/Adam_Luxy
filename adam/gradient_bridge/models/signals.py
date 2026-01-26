# =============================================================================
# ADAM Gradient Bridge Signal Models
# Location: adam/gradient_bridge/models/signals.py
# =============================================================================

"""
LEARNING SIGNAL MODELS

Models for learning signals that flow through the Gradient Bridge.

Signal Flow:
Outcome → Gradient Bridge → [Bandit, Graph, Meta-Learner, Atoms, Verification]
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from adam.gradient_bridge.models.credit import ComponentType, OutcomeType


# =============================================================================
# SIGNAL TYPES
# =============================================================================

class SignalType(str, Enum):
    """Types of learning signals."""
    
    # Outcome signals
    REWARD = "reward"
    ENGAGEMENT = "engagement"
    REVENUE = "revenue"
    
    # Attribution signals
    CREDIT = "credit"
    COUNTERFACTUAL = "counterfactual"
    
    # Update signals
    CONFIDENCE_UPDATE = "confidence"
    PRIOR_UPDATE = "prior"
    EMBEDDING_UPDATE = "embedding"
    PROFILE_UPDATE = "profile"
    
    # Mechanism signals
    MECHANISM_EFFECTIVENESS = "mechanism_effectiveness"
    PERSONALITY_VALIDATION = "personality_validation"
    STATE_TRANSITION = "state_transition"
    
    # Advertising Psychology signals (200+ empirical findings integration)
    REGULATORY_FOCUS_MATCH = "regulatory_focus_match"
    COGNITIVE_LOAD_OPTIMIZATION = "cognitive_load_optimization"
    MESSAGE_FRAME_EFFECTIVENESS = "message_frame_effectiveness"
    CONSTRUAL_LEVEL_MATCH = "construal_level_match"
    TEMPORAL_PATTERN_VALIDATION = "temporal_pattern_validation"
    MORAL_FOUNDATION_RESPONSE = "moral_foundation_response"
    MEMORY_OPTIMIZATION = "memory_optimization"
    IMPLICIT_SIGNAL_VALIDATION = "implicit_signal_validation"


class SignalPriority(str, Enum):
    """Priority for processing signals."""
    
    LOW = "low"           # Batch processing OK
    MEDIUM = "medium"     # Process within minutes
    HIGH = "high"         # Process within seconds
    CRITICAL = "critical" # Immediate processing


# =============================================================================
# LEARNING SIGNAL
# =============================================================================

class LearningSignal(BaseModel):
    """
    A single learning signal to be propagated.
    
    Signals are the currency of the Gradient Bridge - they carry
    outcome information to every component that can learn from it.
    """
    
    signal_id: str = Field(
        default_factory=lambda: f"sig_{uuid4().hex[:12]}"
    )
    
    # Signal type
    signal_type: SignalType
    priority: SignalPriority = Field(default=SignalPriority.MEDIUM)
    
    # Source
    source_component: ComponentType = Field(default=ComponentType.GRAPH)
    source_id: str = ""
    
    # Target
    target_component: ComponentType
    target_id: str = ""
    
    # Signal content
    signal_value: float = Field(ge=-1.0, le=1.0)
    signal_weight: float = Field(ge=0.0, le=1.0, default=1.0)
    
    # Context
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    decision_id: Optional[str] = None
    
    # Payload (component-specific data)
    payload: Dict[str, Any] = Field(default_factory=dict)
    
    # Timing
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    expires_at: Optional[datetime] = None
    
    # Processing state
    processed: bool = Field(default=False)
    processed_at: Optional[datetime] = None
    processing_result: Optional[str] = None


# =============================================================================
# COMPONENT UPDATE
# =============================================================================

class ComponentUpdate(BaseModel):
    """
    Update to be applied to a component.
    
    The result of processing learning signals.
    """
    
    update_id: str = Field(
        default_factory=lambda: f"upd_{uuid4().hex[:12]}"
    )
    
    # Target
    component_type: ComponentType
    component_id: str = ""
    
    # Update type
    update_type: str  # "posterior", "prior", "embedding", "confidence"
    
    # Values
    old_value: Optional[Dict[str, Any]] = None
    new_value: Dict[str, Any] = Field(default_factory=dict)
    delta: Optional[float] = None
    
    # Weight
    update_weight: float = Field(ge=0.0, le=1.0, default=1.0)
    
    # Learning rate adjustment
    learning_rate: float = Field(ge=0.0, le=1.0, default=0.1)
    
    # Source signals
    source_signal_ids: List[str] = Field(default_factory=list)
    
    # Status
    applied: bool = Field(default=False)
    applied_at: Optional[datetime] = None


# =============================================================================
# SIGNAL PACKAGE
# =============================================================================

class SignalPackage(BaseModel):
    """
    Package of signals from a single outcome.
    
    An outcome generates multiple signals for different components.
    """
    
    package_id: str = Field(
        default_factory=lambda: f"pkg_{uuid4().hex[:12]}"
    )
    
    # Source outcome
    decision_id: str
    request_id: str
    user_id: str
    outcome_type: OutcomeType
    outcome_value: float = Field(ge=0.0, le=1.0)
    
    # All signals in this package
    signals: List[LearningSignal] = Field(default_factory=list)
    
    # Summary
    total_signals: int = Field(default=0, ge=0)
    signals_by_target: Dict[str, int] = Field(default_factory=dict)
    
    # Timing
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    # Processing state
    fully_processed: bool = Field(default=False)
    signals_processed: int = Field(default=0, ge=0)
    
    def add_signal(self, signal: LearningSignal) -> None:
        """Add a signal to the package."""
        self.signals.append(signal)
        self.total_signals += 1
        
        target = signal.target_component.value
        self.signals_by_target[target] = self.signals_by_target.get(target, 0) + 1
    
    def get_signals_for_component(
        self,
        component: ComponentType,
    ) -> List[LearningSignal]:
        """Get signals targeting a specific component."""
        return [s for s in self.signals if s.target_component == component]


# =============================================================================
# BANDIT UPDATE SIGNAL
# =============================================================================

class BanditUpdateSignal(BaseModel):
    """
    Specialized signal for updating the contextual bandit.
    
    Contains enriched feature vector from atoms.
    """
    
    signal_id: str = Field(
        default_factory=lambda: f"ban_{uuid4().hex[:12]}"
    )
    
    # Arm that was pulled
    arm_id: str
    arm_mechanism: str
    
    # Reward
    reward: float = Field(ge=0.0, le=1.0)
    
    # Enriched context (40+ features)
    context_features: Dict[str, float] = Field(default_factory=dict)
    
    # Atom-derived features
    regulatory_focus: str = ""  # "promotion", "prevention", "balanced"
    regulatory_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    construal_level: str = ""  # "abstract", "concrete", "moderate"
    construal_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Personality features
    big_five: Dict[str, float] = Field(default_factory=dict)
    
    # Session features
    session_depth: int = Field(default=0, ge=0)
    time_of_day: int = Field(ge=0, le=23, default=12)
    
    # User segment
    user_segment: str = ""
    cold_start: bool = Field(default=False)


# =============================================================================
# GRAPH UPDATE SIGNAL
# =============================================================================

class GraphUpdateSignal(BaseModel):
    """
    Specialized signal for updating the Neo4j graph.
    """
    
    signal_id: str = Field(
        default_factory=lambda: f"gph_{uuid4().hex[:12]}"
    )
    
    # What to update
    node_type: str  # "User", "Mechanism", "Pattern"
    node_id: str
    
    # Update operation
    operation: str  # "update_property", "create_relationship", "update_weight"
    
    # Property updates
    properties: Dict[str, Any] = Field(default_factory=dict)
    
    # Relationship updates
    relationship_type: Optional[str] = None
    related_node_type: Optional[str] = None
    related_node_id: Optional[str] = None
    relationship_properties: Dict[str, Any] = Field(default_factory=dict)
    
    # Weight update
    weight_delta: float = Field(default=0.0)
    confidence_delta: float = Field(default=0.0)


# =============================================================================
# ADVERTISING PSYCHOLOGY SIGNAL
# =============================================================================

class AdvertisingPsychologySignal(BaseModel):
    """
    Specialized signal for advertising psychology learning.
    
    Enables the system to learn from outcomes whether the psychological
    research-based predictions were effective, refining the 200+ empirical
    findings integration over time.
    
    Key research domains tracked:
    - Regulatory focus matching (OR = 2-6x CTR)
    - Cognitive load optimization (d = 0.5-0.8)
    - Construal level matching (g = 0.475)
    - Temporal targeting
    - Moral foundations
    - Memory optimization (spacing, peak-end)
    """
    
    signal_id: str = Field(
        default_factory=lambda: f"adv_{uuid4().hex[:12]}"
    )
    
    # Decision context
    decision_id: str
    user_id: str
    
    # Regulatory Focus (highest-impact: OR = 2-6x)
    predicted_focus: str = ""  # "promotion", "prevention", "neutral"
    focus_detection_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    used_frame: str = ""  # "gain", "loss_avoidance", "neutral"
    frame_match_score: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Cognitive State (d = 0.5-0.8)
    predicted_cognitive_load: float = Field(ge=0.0, le=1.0, default=0.5)
    used_processing_route: str = ""  # "central", "peripheral", "mixed"
    message_complexity: str = ""  # "high", "moderate", "low"
    complexity_match_effective: bool = Field(default=False)
    
    # Construal Level (g = 0.475)
    funnel_stage: str = ""  # "awareness", "consideration", "decision", "purchase"
    predicted_construal: str = ""  # "high_abstract", "low_concrete", "mixed"
    used_construal: str = ""
    construal_match_effective: bool = Field(default=False)
    
    # Temporal Patterns
    hour_of_day: int = Field(ge=0, le=23, default=12)
    day_of_week: int = Field(ge=0, le=6, default=0)
    is_weekend: bool = Field(default=False)
    chronotype: str = ""  # "morning", "evening", "neutral"
    at_cognitive_peak: bool = Field(default=False)
    
    # Moral Foundations (d = 0.3-0.5)
    dominant_foundations: List[str] = Field(default_factory=list)
    used_foundation_appeals: List[str] = Field(default_factory=list)
    foundation_match_effective: bool = Field(default=False)
    
    # Memory Optimization
    exposure_count: int = Field(default=0, ge=0)
    days_since_last_exposure: float = Field(default=0.0, ge=0.0)
    spacing_optimal: bool = Field(default=False)
    ad_fatigue_level: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Implicit Signals (nonconscious processing)
    implicit_signals_used: List[str] = Field(default_factory=list)
    implicit_signal_accuracy: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Outcome
    outcome_type: str = ""  # "click", "conversion", "engagement", "brand_recall"
    outcome_value: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Attribution (contribution of psychology-based targeting)
    psychology_contribution: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Research validation
    research_domain_contributions: Dict[str, float] = Field(default_factory=dict)
    tier1_findings_validated: List[str] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class AdvertisingPsychologyUpdate(BaseModel):
    """
    Update to advertising psychology knowledge based on observed outcomes.
    
    When outcomes validate or invalidate research-based predictions,
    this update is applied to refine the system's knowledge.
    """
    
    update_id: str = Field(
        default_factory=lambda: f"adv_upd_{uuid4().hex[:12]}"
    )
    
    # What to update
    knowledge_type: str  # "signal_mapping", "knowledge_item", "user_profile"
    knowledge_id: str
    
    # Update operation
    operation: str  # "validate", "invalidate", "refine_confidence"
    
    # Validation metrics
    validation_count_delta: int = Field(default=1)
    validation_success: bool = Field(default=False)
    
    # Confidence adjustment
    confidence_before: float = Field(ge=0.0, le=1.0, default=0.5)
    confidence_after: float = Field(ge=0.0, le=1.0, default=0.5)
    confidence_delta: float = Field(default=0.0)
    
    # Effect size refinement
    observed_effect_size: Optional[float] = None
    expected_effect_size: Optional[float] = None
    effect_size_delta: Optional[float] = None
    
    # Context
    user_segment: str = ""
    category: str = ""
    temporal_context: str = ""
    
    # Source signal
    source_signal_id: str = ""
    
    # Applied status
    applied: bool = Field(default=False)
    applied_at: Optional[datetime] = None
