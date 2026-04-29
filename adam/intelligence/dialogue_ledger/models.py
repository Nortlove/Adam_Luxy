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
