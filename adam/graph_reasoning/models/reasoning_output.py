# =============================================================================
# ADAM Reasoning Output Models
# Location: adam/graph_reasoning/models/reasoning_output.py
# =============================================================================

"""
REASONING OUTPUT MODELS

Models for insights and activations pushed back to the graph.

The Interaction Bridge pushes these outputs after reasoning completes.
These become nodes and relationships in Neo4j for future learning.

Output Types:
- MechanismActivation: Which mechanisms were activated and why
- StateInference: Inferred psychological state
- ReasoningInsight: General insight from reasoning
- DecisionAttribution: Attribution of decision outcomes
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# =============================================================================
# MECHANISM ACTIVATION
# =============================================================================

class ActivationIntensity(str, Enum):
    """Intensity levels for mechanism activation."""
    
    LOW = "low"           # Subtle, background activation
    MEDIUM = "medium"     # Standard activation
    HIGH = "high"         # Strong, primary activation
    MAXIMUM = "maximum"   # Dominant, saturating


class MechanismActivation(BaseModel):
    """
    Record of a mechanism being activated in a decision.
    
    This creates a (:Decision)-[:APPLIED_MECHANISM]->(:CognitiveMechanism)
    relationship in Neo4j for learning.
    """
    
    activation_id: str = Field(default_factory=lambda: f"act_{uuid4().hex[:12]}")
    
    # Mechanism reference
    mechanism_id: str
    mechanism_name: str
    
    # Activation details
    intensity: ActivationIntensity = Field(default=ActivationIntensity.MEDIUM)
    intensity_score: float = Field(ge=0.0, le=1.0)
    
    # Was this the primary mechanism?
    is_primary: bool = Field(default=False)
    
    # Confidence in this activation
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Justification
    activation_reason: str
    supporting_evidence: List[str] = Field(default_factory=list)
    
    # Context
    decision_id: str
    user_id: str
    request_id: Optional[str] = None
    
    # Priors used
    prior_effectiveness: float = Field(ge=0.0, le=1.0, default=0.5)
    prior_source: str = Field(default="default")  # "user", "archetype", "category", "default"
    
    # Timestamp
    activated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# =============================================================================
# STATE INFERENCE
# =============================================================================

class StateTransitionType(str, Enum):
    """Type of state transition."""
    
    NATURAL = "natural"       # Natural drift
    TRIGGERED = "triggered"   # Event-triggered change
    INFERRED = "inferred"     # Inferred from behavior


class StateInference(BaseModel):
    """
    Inferred psychological state from reasoning.
    
    This creates a (:User)-[:IN_STATE]->(:TemporalUserState) relationship.
    """
    
    inference_id: str = Field(default_factory=lambda: f"inf_{uuid4().hex[:12]}")
    
    # User reference
    user_id: str
    
    # State dimensions
    arousal: float = Field(ge=0.0, le=1.0)
    valence: float = Field(ge=0.0, le=1.0)
    
    # Regulatory state
    regulatory_focus: str = Field(default="balanced")
    construal_level: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Confidence
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Evidence
    inference_basis: List[str] = Field(default_factory=list)
    behavioral_signals: List[str] = Field(default_factory=list)
    
    # Transition from previous
    transition_type: StateTransitionType = Field(default=StateTransitionType.INFERRED)
    previous_state_id: Optional[str] = None
    
    # Context
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # Timestamp
    inferred_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# =============================================================================
# REASONING INSIGHT
# =============================================================================

class InsightType(str, Enum):
    """Types of reasoning insights."""
    
    PERSONALITY_INFERENCE = "personality_inference"
    MECHANISM_RECOMMENDATION = "mechanism_recommendation"
    STATE_PREDICTION = "state_prediction"
    PATTERN_DISCOVERY = "pattern_discovery"
    CONFLICT_DETECTION = "conflict_detection"
    CAUSAL_ATTRIBUTION = "causal_attribution"


class InsightConfidenceLevel(str, Enum):
    """Confidence levels for insights."""
    
    SPECULATIVE = "speculative"   # < 0.4
    MODERATE = "moderate"         # 0.4 - 0.7
    HIGH = "high"                 # 0.7 - 0.9
    VERY_HIGH = "very_high"       # > 0.9


class ReasoningInsight(BaseModel):
    """
    General insight produced by reasoning.
    
    This creates a (:ReasoningInsight) node in Neo4j with relationships
    to relevant entities (users, mechanisms, decisions).
    """
    
    insight_id: str = Field(default_factory=lambda: f"ins_{uuid4().hex[:12]}")
    
    # Insight content
    insight_type: InsightType
    insight_summary: str
    insight_detail: str
    
    # Confidence
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_level: InsightConfidenceLevel = Field(
        default=InsightConfidenceLevel.MODERATE
    )
    
    # Evidence basis
    evidence_sources: List[str] = Field(default_factory=list)
    evidence_count: int = Field(default=0, ge=0)
    
    # Related entities
    related_user_id: Optional[str] = None
    related_mechanism_ids: List[str] = Field(default_factory=list)
    related_decision_ids: List[str] = Field(default_factory=list)
    
    # Actionability
    is_actionable: bool = Field(default=False)
    recommended_action: Optional[str] = None
    
    # Context
    request_id: Optional[str] = None
    reasoning_chain_id: Optional[str] = None
    
    # Timestamp
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    # Validity
    valid_until: Optional[datetime] = None
    
    def set_confidence_level(self) -> None:
        """Set confidence level from confidence score."""
        if self.confidence < 0.4:
            self.confidence_level = InsightConfidenceLevel.SPECULATIVE
        elif self.confidence < 0.7:
            self.confidence_level = InsightConfidenceLevel.MODERATE
        elif self.confidence < 0.9:
            self.confidence_level = InsightConfidenceLevel.HIGH
        else:
            self.confidence_level = InsightConfidenceLevel.VERY_HIGH


# =============================================================================
# DECISION ATTRIBUTION
# =============================================================================

class DecisionOutcome(str, Enum):
    """Possible decision outcomes."""
    
    CONVERSION = "conversion"
    CLICK = "click"
    ENGAGEMENT = "engagement"
    NO_ACTION = "no_action"
    BOUNCE = "bounce"
    NEGATIVE = "negative"


class DecisionAttribution(BaseModel):
    """
    Attribution of a decision outcome to contributing factors.
    
    Used to update mechanism effectiveness through the Gradient Bridge.
    """
    
    attribution_id: str = Field(default_factory=lambda: f"attr_{uuid4().hex[:12]}")
    
    # Decision reference
    decision_id: str
    user_id: str
    
    # Outcome
    outcome: DecisionOutcome
    outcome_value: float = Field(ge=0.0, le=1.0)
    
    # Mechanism attribution (which mechanisms contributed)
    mechanism_attributions: Dict[str, float] = Field(default_factory=dict)
    # e.g., {"mimetic_desire": 0.4, "scarcity": 0.35, "identity": 0.25}
    
    # Primary mechanism
    primary_mechanism_id: str
    primary_mechanism_contribution: float = Field(ge=0.0, le=1.0)
    
    # Attribution confidence
    attribution_confidence: float = Field(ge=0.0, le=1.0)
    attribution_method: str = Field(default="gradient_based")
    
    # Context factors
    context_factors: Dict[str, float] = Field(default_factory=dict)
    
    # Timing
    decision_at: datetime
    outcome_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    attribution_delay_seconds: int = Field(default=0, ge=0)


# =============================================================================
# REASONING TRACE
# =============================================================================

class ReasoningStep(BaseModel):
    """A single step in the reasoning chain."""
    
    step_id: str = Field(default_factory=lambda: f"step_{uuid4().hex[:8]}")
    step_number: int = Field(ge=0)
    
    # Step content
    step_type: str  # e.g., "context_pull", "mechanism_selection", "synthesis"
    step_description: str
    
    # Inputs and outputs
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    
    # Timing
    started_at: datetime
    completed_at: datetime
    duration_ms: float = Field(ge=0.0)
    
    # Success
    success: bool = Field(default=True)
    error_message: Optional[str] = None


class ReasoningTrace(BaseModel):
    """
    Complete trace of a reasoning process.
    
    Used for debugging, explainability, and learning.
    """
    
    trace_id: str = Field(default_factory=lambda: f"trace_{uuid4().hex[:12]}")
    
    # Request context
    request_id: str
    user_id: str
    decision_id: Optional[str] = None
    
    # Reasoning steps
    steps: List[ReasoningStep] = Field(default_factory=list)
    
    # Produced outputs
    mechanism_activations: List[MechanismActivation] = Field(default_factory=list)
    state_inferences: List[StateInference] = Field(default_factory=list)
    insights: List[ReasoningInsight] = Field(default_factory=list)
    
    # Timing
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: Optional[datetime] = None
    total_duration_ms: float = Field(default=0.0, ge=0.0)
    
    # Success
    success: bool = Field(default=True)
    error_message: Optional[str] = None
    
    def add_step(
        self,
        step_type: str,
        description: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        started_at: datetime,
        completed_at: datetime,
    ) -> ReasoningStep:
        """Add a step to the trace."""
        step = ReasoningStep(
            step_number=len(self.steps),
            step_type=step_type,
            step_description=description,
            inputs=inputs,
            outputs=outputs,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=(completed_at - started_at).total_seconds() * 1000,
        )
        self.steps.append(step)
        return step
    
    def complete(self) -> None:
        """Mark the trace as complete."""
        self.completed_at = datetime.now(timezone.utc)
        self.total_duration_ms = (
            self.completed_at - self.started_at
        ).total_seconds() * 1000
