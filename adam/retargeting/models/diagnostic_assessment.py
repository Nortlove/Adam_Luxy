# =============================================================================
# DiagnosticReasoner — Data Models
# Location: adam/retargeting/models/diagnostic_assessment.py
# =============================================================================

"""
Data models for the DiagnosticReasoner — a core platform deductive engine
that interprets each outcome as evidence about an underlying psychological
puzzle, then selects the constrained next move that maximizes diagnostic
information.

These models are used across the platform:
- TherapeuticSequenceOrchestrator (retargeting)
- CampaignOrchestrator (first-touch decisions)
- Any system that reasons about Person x PageMindstate x Mechanism -> Outcome
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from adam.retargeting.models.enums import (
    BarrierCategory,
    ConversionStage,
    ScaffoldLevel,
    TherapeuticMechanism,
)


# =============================================================================
# ENUMS
# =============================================================================


class EngagementOutcome(str, Enum):
    """Canonical engagement outcome types for diagnostic classification.

    Each type triggers a different diagnostic reasoning path in the
    DiagnosticReasoner. The classification determines which hypotheses
    are evaluated and how the constraint graph is traversed.
    """

    CONVERSION = "conversion"
    CLICK_NO_CONVERT = "click_no_convert"
    IGNORE = "ignore"
    ACTIVE_REJECTION = "active_rejection"
    PARTIAL_ENGAGEMENT = "partial_engagement"


class NonConversionHypothesis(str, Enum):
    """The five competing hypotheses for why a non-conversion occurred.

    When a touch doesn't convert, exactly one (or a weighted combination)
    of these hypotheses explains what went wrong. The reasoner scores
    each against available evidence and uses the primary hypothesis to
    guide the next move.
    """

    WRONG_PAGE_MINDSTATE = "wrong_page_mindstate"
    WRONG_MECHANISM = "wrong_mechanism"
    WRONG_STAGE_MATCH = "wrong_stage_match"
    PKM_REACTANCE_SUPPRESSION = "pkm_reactance"
    AD_FATIGUE = "ad_fatigue"


# =============================================================================
# REASONING TRACE MODELS
# =============================================================================


class ReasoningStep(BaseModel):
    """A single step in the diagnostic reasoning trace.

    The trace is a first-class output — it explains WHY each decision
    was made, which hypotheses were evaluated, and which constraints
    eliminated candidate moves. This is critical for:
    - Debugging poor sequence performance
    - Learning signal attribution
    - Regulatory explainability
    - Human review of automated decisions
    """

    step_number: int
    step_type: str = Field(
        description=(
            "Phase of reasoning: outcome_classification, hypothesis_evaluation, "
            "candidate_generation, constraint_check, diagnostic_scoring, "
            "move_selection, signal_generation"
        ),
    )
    description: str
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: float = 0.0


class HypothesisEvaluation(BaseModel):
    """Evidence assessment for a single non-conversion hypothesis."""

    hypothesis: NonConversionHypothesis
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_for: List[str] = Field(default_factory=list)
    evidence_against: List[str] = Field(default_factory=list)
    is_primary: bool = False


class ConstraintViolation(BaseModel):
    """A candidate move that was eliminated by the constraint graph."""

    mechanism: str
    page_cluster: str
    constraint_type: str = Field(
        description=(
            "frustrated_pair, reactance_limit, pkm_penalty, "
            "stage_mismatch, coherence_failure, blacklisted, repetition"
        ),
    )
    reason: str
    severity: float = Field(ge=0.0, le=1.0, default=1.0)


class FrustratedPairPlan(BaseModel):
    """Multi-touch plan for sequential barrier resolution.

    When two barriers involve anti-correlated dimensions (e.g.,
    trust_deficit and price_friction, r=-0.457), they CANNOT be
    addressed simultaneously. This plan sequences them.
    """

    current_phase: int
    total_phases: int
    current_target_dimension: str
    deferred_dimensions: List[str] = Field(default_factory=list)
    deferred_barriers: List[str] = Field(default_factory=list)
    correlation: float = Field(
        description="Negative correlation between frustrated dimensions",
    )
    rationale: str


# =============================================================================
# INPUT MODEL
# =============================================================================


class DiagnosticInput(BaseModel):
    """Complete input bundle for the DiagnosticReasoner.

    Bundles all context needed for one diagnostic reasoning cycle.
    Designed to be constructable from any calling context — retargeting
    orchestrator, campaign orchestrator, API endpoints, etc.
    """

    user_id: str
    brand_id: str
    archetype_id: str

    # The observed outcome
    engagement_type: Optional[str] = None
    converted: bool = False
    stage_advanced: bool = False
    barrier_resolved: Optional[bool] = None

    # The deployed intervention (what was tried)
    deployed_mechanism: str = ""
    deployed_page_cluster: str = ""
    deployed_scaffold_level: str = ""

    # Context at decision time
    bilateral_edge: Dict[str, float] = Field(default_factory=dict)
    page_mindstate: Optional[Dict[str, float]] = None
    behavioral_signals: Dict[str, float] = Field(default_factory=dict)

    # User state
    current_barrier: Optional[str] = None
    current_stage: str = "evaluating"
    reactance_level: float = 0.0
    pkm_phase: int = 1
    ownership_level: float = 0.0

    # User profile (for per-user posterior lookup)
    user_profile: Optional[Any] = None

    # Sequence context
    sequence_id: str = ""
    touch_position: int = 0
    touch_history: List[Dict] = Field(default_factory=list)
    mechanisms_already_tried: List[str] = Field(default_factory=list)
    mechanisms_blacklisted: List[str] = Field(default_factory=list)

    # Enhancement #34: External hypothesis modifiers
    # Applied additively to H1-H5 base confidences BEFORE evaluation.
    # Sources: processing depth, click latency trajectory, device mismatch, etc.
    external_h_modifiers: Dict[str, float] = Field(
        default_factory=dict,
        description="Additive modifiers to H1-H5 from nonconscious signals",
    )


# =============================================================================
# OUTPUT MODEL
# =============================================================================


class DiagnosticAssessment(BaseModel):
    """Complete output of the DiagnosticReasoner.

    Contains the outcome interpretation, next move recommendation,
    full reasoning trace, and upstream signals for other platform
    components to consume.
    """

    assessment_id: str = Field(default_factory=lambda: str(uuid4())[:12])
    user_id: str
    brand_id: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )

    # A. Outcome interpretation
    observed_outcome: EngagementOutcome
    outcome_interpretation: str = Field(
        description="Human-readable explanation of why this outcome occurred",
    )
    hypothesis_evaluations: List[HypothesisEvaluation] = Field(
        default_factory=list,
    )
    primary_hypothesis: Optional[NonConversionHypothesis] = None
    hypothesis_confidences: Dict[str, float] = Field(default_factory=dict)

    # B. Next move selection
    next_mechanism: str = ""
    next_page_cluster: str = ""
    next_scaffold_level: str = ""
    move_confidence: float = Field(ge=0.0, le=1.0, default=0.5)

    # C. Reasoning trace
    reasoning_trace: List[ReasoningStep] = Field(default_factory=list)
    total_reasoning_ms: float = 0.0

    # D. Diagnostic metadata
    expected_diagnostic_value: float = Field(
        default=0.0,
        description="Expected information gain from the recommended move (bits)",
    )
    diagnostic_explanation: str = Field(
        default="",
        description="What we expect to learn from this move",
    )
    constraint_violations: List[ConstraintViolation] = Field(
        default_factory=list,
    )
    frustrated_pair_plan: Optional[FrustratedPairPlan] = None
    alternatives_if_fails: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Backup (mechanism, page_cluster, rationale) tuples",
    )

    # E. Upstream signals for other platform components
    signals_for_upstream: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Keys: stage_progression, mechanism_blacklist, cooldown_required, "
            "cooldown_hours, reactance_alert, exploration_recommended, "
            "frustrated_pair_alert, crawl_expansion_signal"
        ),
    )
