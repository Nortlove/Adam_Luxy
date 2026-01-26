# =============================================================================
# ADAM Kafka Event Models
# Location: adam/infrastructure/kafka/events.py
# =============================================================================

"""
KAFKA EVENT SCHEMAS

Pydantic models for all ADAM Kafka events.
These models define the schema for event serialization.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# =============================================================================
# BASE EVENT
# =============================================================================

class ADAMEvent(BaseModel):
    """Base class for all ADAM events."""
    
    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex[:16]}")
    event_type: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "adam"
    version: str = "1.0"
    
    # Tracing
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    
    def to_kafka_value(self) -> Dict[str, Any]:
        """Serialize for Kafka."""
        return self.model_dump(mode="json")


# =============================================================================
# LEARNING SIGNAL EVENTS
# =============================================================================

class SignalType(str, Enum):
    """Types of learning signals."""
    
    COLD_START = "cold_start"
    MULTIMODAL = "multimodal"
    TEMPORAL = "temporal"
    VERIFICATION = "verification"
    EMERGENCE = "emergence"
    FEATURE_STORE = "feature_store"
    MECHANISM_EFFECTIVENESS = "mechanism_effectiveness"
    PROFILE_UPDATE = "profile_update"


class LearningSignalEvent(ADAMEvent):
    """
    Learning signal event for Gradient Bridge.
    
    All components emit these signals to update priors.
    """
    
    event_type: str = "learning_signal"
    
    # Signal identification
    signal_type: SignalType
    component_id: str
    
    # Context
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    decision_id: Optional[str] = None
    
    # Signal payload
    signal_name: str
    signal_value: float = Field(ge=-1.0, le=1.0)
    signal_confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    
    # Additional context
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Learning targets
    update_targets: List[str] = Field(default_factory=list)
    # Example: ["user_profile", "mechanism_prior", "archetype"]


# =============================================================================
# OUTCOME EVENTS
# =============================================================================

class AdOutcomeType(str, Enum):
    """Types of ad outcomes."""
    
    LISTEN_COMPLETE = "listen_complete"
    LISTEN_PARTIAL = "listen_partial"
    SKIP = "skip"
    CLICK = "click"
    CONVERSION = "conversion"


class AdOutcomeEvent(ADAMEvent):
    """
    Ad decision outcome event.
    
    Records the result of an ad decision for learning.
    """
    
    event_type: str = "ad_outcome"
    
    # Decision reference
    decision_id: str
    user_id: str
    session_id: Optional[str] = None
    
    # Campaign/Creative
    campaign_id: str
    creative_id: str
    
    # Outcome
    outcome_type: AdOutcomeType
    outcome_value: float = Field(ge=0.0, le=1.0)
    
    # Behavioral details
    listen_percentage: float = Field(ge=0.0, le=1.0, default=0.0)
    clicked: bool = False
    converted: bool = False
    
    # Mechanism attribution
    mechanisms_applied: List[str] = Field(default_factory=list)
    mechanism_effectiveness: Dict[str, float] = Field(default_factory=dict)
    
    # Context at outcome
    station_id: Optional[str] = None
    station_format: Optional[str] = None
    content_before_type: Optional[str] = None


class MechanismOutcomeEvent(ADAMEvent):
    """
    Mechanism effectiveness outcome.
    
    Records how well a mechanism worked for a user.
    """
    
    event_type: str = "mechanism_outcome"
    
    mechanism_id: str
    user_id: str
    decision_id: Optional[str] = None
    
    # Effectiveness
    effectiveness: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    
    # Context
    context: Dict[str, Any] = Field(default_factory=dict)
    
    # Should this update the user's mechanism priors?
    update_user_prior: bool = True


# =============================================================================
# SESSION EVENTS
# =============================================================================

class SessionEventType(str, Enum):
    """Types of session events."""
    
    START = "start"
    END = "end"
    PAUSE = "pause"
    RESUME = "resume"


class SessionEvent(ADAMEvent):
    """
    Listening session event.
    
    Records session lifecycle for behavioral analysis.
    """
    
    event_type: str = "session"
    
    session_event_type: SessionEventType
    session_id: str
    user_id: str
    
    # Session context
    platform: str = "iheart"
    device_type: Optional[str] = None
    station_id: Optional[str] = None
    
    # Session metrics (for END events)
    duration_seconds: Optional[int] = None
    tracks_played: Optional[int] = None
    tracks_skipped: Optional[int] = None
    ads_served: Optional[int] = None
    ads_clicked: Optional[int] = None


# =============================================================================
# DECISION EVENTS
# =============================================================================

class DecisionEvent(ADAMEvent):
    """
    ADAM decision event.
    
    Records all ad decisions for analysis and learning.
    """
    
    event_type: str = "decision"
    
    decision_id: str
    user_id: str
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Selection
    campaign_id: str
    creative_id: str
    
    # Psychological reasoning
    mechanisms_applied: List[str] = Field(default_factory=list)
    primary_mechanism: Optional[str] = None
    mechanism_scores: Dict[str, float] = Field(default_factory=dict)
    
    # User profile snapshot
    user_big_five: Dict[str, float] = Field(default_factory=dict)
    user_archetype: Optional[str] = None
    
    # Selection confidence
    selection_confidence: float = Field(ge=0.0, le=1.0)
    
    # Context
    station_id: Optional[str] = None
    station_format: Optional[str] = None
    content_context: Dict[str, Any] = Field(default_factory=dict)


class DecisionReasoningEvent(ADAMEvent):
    """
    Decision reasoning event for explainability.
    
    Records the full reasoning chain for a decision.
    """
    
    event_type: str = "decision_reasoning"
    
    decision_id: str
    
    # Reasoning chain
    reasoning_steps: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Atom of Thought (if used)
    atoms_processed: List[str] = Field(default_factory=list)
    atom_outputs: Dict[str, Any] = Field(default_factory=dict)
    
    # Blackboard state
    blackboard_state: Dict[str, Any] = Field(default_factory=dict)
    
    # Total reasoning time
    reasoning_time_ms: float = 0.0


# =============================================================================
# PROFILE EVENTS
# =============================================================================

class ProfileUpdateEvent(ADAMEvent):
    """
    User profile update event.
    
    Records all profile updates for auditing and CDC.
    """
    
    event_type: str = "profile_update"
    
    user_id: str
    
    # What was updated
    update_type: str  # "big_five", "archetype", "mechanism_prior", etc.
    field_updated: str
    
    # Before/after
    previous_value: Optional[Any] = None
    new_value: Any
    
    # Source of update
    source_signal_id: Optional[str] = None
    source_component: str
    
    # Confidence
    update_confidence: float = Field(ge=0.0, le=1.0)
