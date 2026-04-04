# =============================================================================
# ADAM Journey Models
# Location: adam/user/journey/models.py
# =============================================================================

"""
JOURNEY MODELS

Models for tracking user journey states.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field


class JourneyStage(str, Enum):
    """User journey stages."""
    
    # Awareness
    UNAWARE = "unaware"
    AWARE = "aware"
    
    # Consideration
    CONSIDERING = "considering"
    RESEARCHING = "researching"
    COMPARING = "comparing"
    
    # Decision
    READY_TO_BUY = "ready_to_buy"
    DECIDING = "deciding"
    
    # Action
    PURCHASING = "purchasing"
    PURCHASED = "purchased"
    
    # Post-purchase
    USING = "using"
    EVALUATING = "evaluating"
    ADVOCATING = "advocating"
    CHURNING = "churning"


# ---------------------------------------------------------------------------
# TTM-derived Conversion Stage mapping (Enhancement #33)
# Maps the 13 granular JourneyStage values to 6 retargeting conversion stages.
# ---------------------------------------------------------------------------
_JOURNEY_TO_CONVERSION_STAGE = {
    "unaware":      "unaware",
    "aware":        "curious",
    "considering":  "evaluating",
    "researching":  "evaluating",
    "comparing":    "evaluating",
    "ready_to_buy": "intending",
    "deciding":     "intending",
    "purchasing":   "intending",
    "purchased":    "converted",
    "using":        "converted",
    "evaluating":   "converted",
    "advocating":   "converted",
    "churning":     "stalled",
}


def to_conversion_stage(journey_stage: "JourneyStage") -> str:
    """Map a JourneyStage to a retargeting ConversionStage string.

    Returns one of: unaware, curious, evaluating, intending, stalled, converted.
    Used by the Therapeutic Retargeting Engine (Enhancement #33) to determine
    which intervention class is appropriate.
    """
    return _JOURNEY_TO_CONVERSION_STAGE.get(journey_stage.value, "unaware")


class DecisionUrgency(str, Enum):
    """Urgency of decision."""
    
    IMMEDIATE = "immediate"      # Minutes
    TODAY = "today"              # Hours
    THIS_WEEK = "this_week"      # Days
    PLANNING = "planning"        # Weeks/months
    PASSIVE = "passive"          # No timeline


class JourneyState(BaseModel):
    """Current state in user journey."""
    
    user_id: str
    category: str  # Product/service category
    
    # Current stage
    stage: JourneyStage
    stage_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Stage timing
    entered_stage_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    expected_stage_duration: Optional[timedelta] = None
    
    # Urgency
    urgency: DecisionUrgency = Field(default=DecisionUrgency.PASSIVE)
    urgency_signals: List[str] = Field(default_factory=list)
    
    # Engagement
    engagement_level: float = Field(ge=0.0, le=1.0, default=0.5)
    touchpoint_count: int = Field(default=0, ge=0)
    
    # Context
    last_interaction: Optional[datetime] = None
    last_interaction_type: Optional[str] = None


class JourneyTransition(BaseModel):
    """A transition between journey stages."""
    
    transition_id: str
    user_id: str
    category: str
    
    # Transition
    from_stage: JourneyStage
    to_stage: JourneyStage
    
    # Trigger
    trigger_signal: str
    trigger_confidence: float = Field(ge=0.0, le=1.0)
    
    # Context
    context: Dict[str, Any] = Field(default_factory=dict)
    
    # Timing
    transitioned_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    time_in_previous_stage: Optional[timedelta] = None


class UserJourney(BaseModel):
    """Complete user journey for a category."""
    
    user_id: str
    category: str
    
    # Current state
    current_state: JourneyState
    
    # History
    transitions: List[JourneyTransition] = Field(default_factory=list)
    
    # Summary
    total_touchpoints: int = Field(default=0, ge=0)
    journey_started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    # Predictions
    predicted_next_stage: Optional[JourneyStage] = None
    predicted_conversion_probability: Optional[float] = None
    
    # Updated
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
