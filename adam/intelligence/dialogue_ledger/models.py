# =============================================================================
# ADAM Dialogue Ledger — Pydantic models matching the Neo4j schema
# Location: adam/intelligence/dialogue_ledger/models.py
# =============================================================================

"""
Pydantic models for the Dialogue Ledger schema. Mirror migration 019.

CRITICAL DISCIPLINE RULE (HMT Rule 12): every Claim enters with
status=ClaimStatus.HYPOTHESIS. Promotion requires explicit transition
through the LearningStatus lifecycle. Direct construction with another
status is forbidden — the constructor enforces this.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


# =============================================================================
# ENUMS
# =============================================================================


class ClaimStatus(str, Enum):
    """Where a Claim sits in the learning lifecycle.

    HYPOTHESIS is the only legal entry state. Other states are reached
    only via explicit transition through LearningStatus.transition().
    """

    HYPOTHESIS = "hypothesis"
    INSTRUMENTED = "instrumented"  # attached to a measurable outcome
    TESTING = "testing"             # within horizon, awaiting causal signal
    VALIDATED_USER_RIGHT = "validated_user_right"
    VALIDATED_SYSTEM_RIGHT = "validated_system_right"
    INDETERMINATE = "indeterminate"
    RETIRED = "retired"


class LearningStatusState(str, Enum):
    """Same lifecycle states viewed from the LearningStatus node side.

    Identical values to ClaimStatus — kept as a separate Enum so
    consumers reading LearningStatus.current can distinguish "the
    status of a learning" from "the current state of a Claim's
    status field" semantically.
    """

    CAPTURED = "captured"           # claim observed but not instrumented
    INSTRUMENTED = "instrumented"
    TESTING = "testing"
    VALIDATED_USER_RIGHT = "validated_user_right"
    VALIDATED_SYSTEM_RIGHT = "validated_system_right"
    INDETERMINATE = "indeterminate"
    RETIRED = "retired"


class ElicitationMode(str, Enum):
    """Which elicitation format produced this Claim.

    HMT foundation §8 specifies 10 modes. v0.1 ships 4: ForcedPair,
    TimedPair, StoryPrompt, RecallabilityProbe. The remaining 6 are
    valid enum values for forward compatibility but do not yet have
    generators.
    """

    FORCED_PAIR = "forced_pair"
    TIMED_PAIR = "timed_pair"
    STORY = "story"
    RECALLABILITY = "recallability"
    K_AFC = "k_afc"
    RANK_ORDER = "rank_order"
    COUNTER_EXAMPLE = "counter_example"
    SCENARIO = "scenario"
    SPIES = "spies"
    FOUR_POINT = "four_point"


class HorizonClass(str, Enum):
    """Expected time-to-causal-signal for a domain.

    Adjudication cannot occur before the horizon. HMT §9.2.
    """

    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"


class FrameLabel(str, Enum):
    """Gain/loss/neutral frame the Claim was elicited under."""

    GAIN = "gain"
    LOSS = "loss"
    NEUTRAL = "neutral"


class RecallabilityLabel(str, Enum):
    """Tacit-vs-confabulation discrimination signal.

    Populated when a RecallabilityProbe follows the Claim:
      FLUENT — user produced a specific instance with detail and speed
      HESITANT — user produced an instance after pause/uncertainty
      ABSENT — user could not produce a specific instance
    """

    FLUENT = "fluent"
    HESITANT = "hesitant"
    ABSENT = "absent"


class DeviationAdjudicationOutcome(str, Enum):
    """Result of comparing the user's override against the system's
    original recommendation after the adjudication horizon.

    HMT §11.5: every override is a HYPOTHESIS at write time about
    "the system was wrong here." The lifecycle tracks the hypothesis
    through to causal evidence.

    States:
      CONFIRMED_OVERRIDE       — observed outcome supported user's choice;
                                 system's recommendation would have been
                                 worse. The user's override is validated.
      SYSTEM_VINDICATED        — observed outcome supported system's
                                 recommendation; user's override produced
                                 a worse result.
      FALSE_CORRECTION         — observed outcome was indistinguishable
                                 between system rec and user override
                                 (no causal signal); the override was
                                 not load-bearing for the outcome.
      PENDING_INSUFFICIENT_DATA — adjudication horizon elapsed but data
                                 quality / quantity below the threshold
                                 needed for a verdict.
    """

    CONFIRMED_OVERRIDE = "confirmed_override"
    SYSTEM_VINDICATED = "system_vindicated"
    FALSE_CORRECTION = "false_correction"
    PENDING_INSUFFICIENT_DATA = "pending_insufficient_data"


class DeviationLifecycleState(str, Enum):
    """Where a HumanDeviation sits in its lifecycle.

    Valid transitions:
        RECORDED → AWAITING_OUTCOME (auto on schedule_adjudication)
        AWAITING_OUTCOME → ADJUDICATED (on adjudicate_deviation call
                                        with sufficient data)
        AWAITING_OUTCOME → PENDING (on adjudication call when data
                                    insufficient; can re-attempt later)
        PENDING → ADJUDICATED (on later successful adjudication)

    No transitions return to RECORDED; lifecycle is monotonic forward.
    """

    RECORDED = "recorded"
    AWAITING_OUTCOME = "awaiting_outcome"
    ADJUDICATED = "adjudicated"
    PENDING = "pending"


# =============================================================================
# NODE MODELS
# =============================================================================


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _new_id(prefix: str) -> str:
    return f"{prefix}:{uuid4().hex[:16]}"


class DialogueUser(BaseModel):
    """The partner driving the platform.

    Single-tenant pilot uses the well-known id "user:chris" stamped by
    the dashboard auth stub. Multi-tenant adds id-per-real-user.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    email: Optional[str] = None
    display_name: Optional[str] = None
    role: str = "planner"
    created_at: datetime = Field(default_factory=_now_utc)
    rational_experiential_preference: Optional[float] = None
    trust_mode_default: str = "explain"


class DialogueDomain(BaseModel):
    """A bounded knowledge domain within which calibration is tracked."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str = ""
    typical_horizon_class: HorizonClass = HorizonClass.WEEKS


class Claim(BaseModel):
    """An assertion the user made.

    HMT discipline rule 12 enforced at construction: status MUST be
    HYPOTHESIS at creation. Other statuses are reached only via
    LearningStatus transitions.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: _new_id("claim"))
    user_id: str
    text: str
    elicitation_mode: ElicitationMode
    stated_confidence: Optional[float] = None
    latency_ms: Optional[int] = None
    frame: FrameLabel = FrameLabel.NEUTRAL
    domain: str
    status: ClaimStatus = ClaimStatus.HYPOTHESIS
    created_at: datetime = Field(default_factory=_now_utc)
    session_id: Optional[str] = None
    mood_index: Optional[float] = None
    recallability: Optional[RecallabilityLabel] = None

    @field_validator("status")
    @classmethod
    def _enforce_hypothesis_at_creation(cls, v: ClaimStatus) -> ClaimStatus:
        if v != ClaimStatus.HYPOTHESIS:
            raise ValueError(
                f"Claim must be created with status=HYPOTHESIS, got {v}. "
                "HMT discipline rule 12: user assertions enter as "
                "hypotheses, not learnings. Promotion happens via "
                "LearningStatus transitions."
            )
        return v

    @field_validator("stated_confidence")
    @classmethod
    def _validate_confidence_range(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        if not 0.0 <= v <= 1.0:
            raise ValueError(
                f"stated_confidence must be in [0, 1]; got {v}"
            )
        return v

    @field_validator("mood_index")
    @classmethod
    def _validate_mood_range(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return v
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"mood_index must be in [0, 1]; got {v}")
        return v

    def to_neo4j_props(self) -> Dict[str, Any]:
        """Serialize to a Neo4j-property-friendly dict.

        Datetimes → ISO strings; enums → their .value; None → omitted.
        """
        props: Dict[str, Any] = {
            "id": self.id,
            "user_id": self.user_id,
            "text": self.text,
            "elicitation_mode": self.elicitation_mode.value,
            "frame": self.frame.value,
            "domain": self.domain,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
        }
        if self.stated_confidence is not None:
            props["stated_confidence"] = float(self.stated_confidence)
        if self.latency_ms is not None:
            props["latency_ms"] = int(self.latency_ms)
        if self.session_id:
            props["session_id"] = self.session_id
        if self.mood_index is not None:
            props["mood_index"] = float(self.mood_index)
        if self.recallability is not None:
            props["recallability"] = self.recallability.value
        return props


class LearningStatus(BaseModel):
    """Lifecycle state for a Claim (linked 1:1 via :HAS_STATUS)."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str
    current: LearningStatusState = LearningStatusState.CAPTURED
    transitioned_at: datetime = Field(default_factory=_now_utc)
    reason: str = "claim captured"
    horizon_ends_at: Optional[datetime] = None
    evidence_strength: float = 0.0

    def to_neo4j_props(self) -> Dict[str, Any]:
        props: Dict[str, Any] = {
            "claim_id": self.claim_id,
            "current": self.current.value,
            "transitioned_at": self.transitioned_at.isoformat(),
            "reason": self.reason,
            "evidence_strength": float(self.evidence_strength),
        }
        if self.horizon_ends_at is not None:
            props["horizon_ends_at"] = self.horizon_ends_at.isoformat()
        return props


# =============================================================================
# Convenience constructors
# =============================================================================


def make_claim(
    user_id: str,
    text: str,
    elicitation_mode: ElicitationMode,
    domain: str,
    *,
    stated_confidence: Optional[float] = None,
    latency_ms: Optional[int] = None,
    frame: FrameLabel = FrameLabel.NEUTRAL,
    session_id: Optional[str] = None,
    mood_index: Optional[float] = None,
) -> Claim:
    """Make a Claim with HMT-compliant defaults.

    Discipline rule 12 enforced: status is forced to HYPOTHESIS.
    """
    return Claim(
        user_id=user_id,
        text=text,
        elicitation_mode=elicitation_mode,
        domain=domain,
        stated_confidence=stated_confidence,
        latency_ms=latency_ms,
        frame=frame,
        session_id=session_id,
        mood_index=mood_index,
    )


# =============================================================================
# HumanDeviation — partner override of a system recommendation
# =============================================================================


class HumanDeviation(BaseModel):
    """A partner override of a system recommendation (HMT §11.5).

    HMT discipline rule 12 applied to overrides: every deviation is a
    HYPOTHESIS at write time about "the system was wrong here." The
    lifecycle tracks the hypothesis through to causal evidence via
    the adjudication horizon.

    Construction-time invariants:
        - lifecycle_state is RECORDED at creation; transitions occur
          only via the deviation_lifecycle service module.
        - reason is required and templated (categorical reason tag +
          optional free-text annotation). Free-form reason WITHOUT a
          tag is rejected — the analytics loop needs a categorical
          signal to aggregate, not free-form prose.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: _new_id("deviation"))
    user_id: str
    claim_id: Optional[str] = None  # links back to a Claim if applicable
    decision_id: str                # The system decision that was overridden
    domain: str
    system_recommendation: Dict[str, Any]   # Templated structured rec
    user_substitute: Dict[str, Any]         # Templated structured override
    reason_tag: str                          # Categorical reason (required)
    reason_text: Optional[str] = None        # Optional free-text annotation
    expected_outcome_tag: Optional[str] = None  # Categorical expected outcome
    lifecycle_state: DeviationLifecycleState = DeviationLifecycleState.RECORDED
    horizon_ends_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_now_utc)

    @field_validator("lifecycle_state")
    @classmethod
    def _enforce_recorded_at_creation(
        cls, v: DeviationLifecycleState,
    ) -> DeviationLifecycleState:
        if v != DeviationLifecycleState.RECORDED:
            raise ValueError(
                f"HumanDeviation must be created with "
                f"lifecycle_state=RECORDED, got {v}. Use "
                f"deviation_lifecycle.transition_state to advance."
            )
        return v

    @field_validator("reason_tag")
    @classmethod
    def _validate_reason_tag_non_empty(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError(
                "reason_tag is required (categorical signal for the "
                "analytics loop). Free-form reason_text alone is "
                "insufficient — A12 defense."
            )
        return v

    def to_neo4j_props(self) -> Dict[str, Any]:
        props: Dict[str, Any] = {
            "id": self.id,
            "user_id": self.user_id,
            "decision_id": self.decision_id,
            "domain": self.domain,
            "reason_tag": self.reason_tag,
            "lifecycle_state": self.lifecycle_state.value,
            "created_at": self.created_at.isoformat(),
            # Dicts persist as JSON strings on Neo4j properties.
            "system_recommendation_json": _json_dumps_safe(
                self.system_recommendation,
            ),
            "user_substitute_json": _json_dumps_safe(self.user_substitute),
        }
        if self.claim_id:
            props["claim_id"] = self.claim_id
        if self.reason_text:
            props["reason_text"] = self.reason_text
        if self.expected_outcome_tag:
            props["expected_outcome_tag"] = self.expected_outcome_tag
        if self.horizon_ends_at is not None:
            props["horizon_ends_at"] = self.horizon_ends_at.isoformat()
        return props


class DeviationAdjudication(BaseModel):
    """The adjudicated verdict on a HumanDeviation after horizon elapses.

    Linked 1:1 to a HumanDeviation via deviation_id. Multiple
    adjudication attempts may exist for the same deviation if the first
    attempt produced PENDING_INSUFFICIENT_DATA — each later attempt is
    a separate DeviationAdjudication record with iteration > 0.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: _new_id("adjudication"))
    deviation_id: str
    outcome: DeviationAdjudicationOutcome
    iteration: int = 0
    observed_outcome_summary: Dict[str, Any] = Field(default_factory=dict)
    adjudicator: str = "auto"  # "auto" | user_id of human reviewer
    confidence: float = 0.0
    rationale_tag: str = ""    # Templated reason for the verdict
    adjudicated_at: datetime = Field(default_factory=_now_utc)

    @field_validator("confidence")
    @classmethod
    def _validate_confidence_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be in [0, 1]; got {v}")
        return v

    def to_neo4j_props(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "deviation_id": self.deviation_id,
            "outcome": self.outcome.value,
            "iteration": int(self.iteration),
            "observed_outcome_summary_json": _json_dumps_safe(
                self.observed_outcome_summary,
            ),
            "adjudicator": self.adjudicator,
            "confidence": float(self.confidence),
            "rationale_tag": self.rationale_tag,
            "adjudicated_at": self.adjudicated_at.isoformat(),
        }


def _json_dumps_safe(payload: Dict[str, Any]) -> str:
    """JSON-serialize a dict for Neo4j property storage.

    Falls back to repr-rendered string when the payload contains
    non-JSON-serializable objects (datetimes, etc.). The fallback is
    audit-traceable, not silent — a non-empty payload that cannot be
    JSON-rendered is still persisted, just as a string representation.
    """
    import json as _json
    try:
        return _json.dumps(payload, default=str, sort_keys=True)
    except Exception:
        return repr(payload)


def make_deviation(
    user_id: str,
    decision_id: str,
    domain: str,
    system_recommendation: Dict[str, Any],
    user_substitute: Dict[str, Any],
    reason_tag: str,
    *,
    claim_id: Optional[str] = None,
    reason_text: Optional[str] = None,
    expected_outcome_tag: Optional[str] = None,
) -> HumanDeviation:
    """Convenience constructor for a HumanDeviation.

    HMT discipline rule 12 enforced: lifecycle_state forced to RECORDED.
    A12 defense enforced via reason_tag requirement.
    """
    return HumanDeviation(
        user_id=user_id,
        decision_id=decision_id,
        domain=domain,
        system_recommendation=system_recommendation,
        user_substitute=user_substitute,
        reason_tag=reason_tag,
        claim_id=claim_id,
        reason_text=reason_text,
        expected_outcome_tag=expected_outcome_tag,
    )
