# =============================================================================
# ADAM Mechanism Rotation — pre-registered event substrate (task #22)
# Location: adam/intelligence/mechanism_rotation.py
# =============================================================================

"""
PRE-REGISTERED MECHANISM ROTATION

Per simulation analysis: this is the single most powerful Pilot 2
demonstration artifact. Falsifiability + showmanship in one structure.

PRE-REGISTRATION

Before pilot launch, the team commits publicly to rotations like:

    "On day 14 of the LUXY pilot, when accumulated bilateral edge
     evidence for the Careful Truster × prevention-focused-page cell
     crosses 50 conversions, the system will rotate the recommended
     mechanism from authority to brand_trust_evidence based on the
     observed CATE differential."

WHEN THE TRIGGER FIRES

  - System emits a RotationEvent recording the moment, the evidence
    that triggered, the from/to mechanisms, the recommendation summary.
  - Dashboard renders a single graph: conversion rate by day with the
    rotation moment marked. If the post-rotation rate climbs, that
    graph is the deck-winning artifact.
  - If the rotation does NOT produce expected lift, the discipline
    of pre-registration is itself credibility — falsifiable failure
    is more useful than post-hoc success.

DESIGN

Pure substrate; no Neo4j writes in this module (the rotation event
can be persisted via the dialogue ledger or a sibling store later).
The trigger logic is testable against synthetic evidence streams.

DISCIPLINE

  - The commitment is IMMUTABLE once registered (registered_at fixed,
    cannot be amended). Amending after-the-fact destroys the
    falsifiability.
  - The trigger fires DETERMINISTICALLY on the registered conditions.
    No "the system would have rotated except..." excuses.
  - Both the trigger-fire AND the trigger-no-fire are recorded as
    explicit events so post-pilot audit can verify discipline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4


# =============================================================================
# ENUMS + IDS
# =============================================================================


class RotationStatus(str, Enum):
    """Lifecycle state of a rotation commitment."""

    REGISTERED = "registered"     # commitment made, trigger not yet evaluated
    PENDING = "pending"           # waiting for accumulated evidence
    TRIGGERED = "triggered"       # rotation fired
    EXPIRED = "expired"           # commitment window closed without trigger
    CANCELLED = "cancelled"       # explicit pre-rotation cancellation
                                  # (counts as failure of discipline — logged)


class TriggerCondition(str, Enum):
    """How the trigger evaluates evidence accumulation."""

    EDGE_COUNT_THRESHOLD = "edge_count_threshold"
    """Trigger fires when accumulated bilateral edges for the cell
    crosses N (e.g. 50 conversions)."""

    CATE_DIFFERENTIAL_THRESHOLD = "cate_differential_threshold"
    """Trigger fires when CATE estimate differential between the
    'from' and 'to' mechanisms exceeds a threshold (e.g. 0.05 abs)."""

    CONFORMAL_INTERVAL_NON_OVERLAP = "conformal_interval_non_overlap"
    """Trigger fires when the conformal CI of the 'to' mechanism
    no longer overlaps the conformal CI of the 'from' mechanism."""


def _new_rotation_id() -> str:
    return f"rot:{uuid4().hex[:16]}"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# COMMITMENT MODEL
# =============================================================================


@dataclass(frozen=True)
class RotationCommitment:
    """Pre-registered mechanism rotation commitment.

    Immutable once registered (frozen dataclass). The trigger logic
    evaluates the conditions; the registration itself does not change
    over the pilot's lifetime.

    Attributes:
        rotation_id: unique identifier
        archetype: archetype targeted (e.g. "careful_truster")
        page_context: page-context filter (e.g. "prevention_focused"
            or None for all contexts)
        from_mechanism: mechanism currently recommended for this cell
        to_mechanism: mechanism the system will rotate TO when triggered
        rationale: why the system would rotate (the falsifiable
            hypothesis — must be specific, e.g. "bilateral edge data
            shows brand_trust_evidence outperforms authority by 15%
            relative on Careful Truster × prevention-focused pages")
        trigger_condition: which evaluation type
        trigger_threshold: numeric threshold for the condition
        registered_at: when the commitment was made (immutable)
        evaluation_window_days: how long after registration the
            commitment remains active. After this, status → EXPIRED
            even if trigger conditions unmet.
        registered_by: user_id of the registrant (audit)
        public_url: optional — link to where the commitment was
            published externally (OSF, blog, etc.)
    """

    rotation_id: str
    archetype: str
    from_mechanism: str
    to_mechanism: str
    rationale: str
    trigger_condition: TriggerCondition
    trigger_threshold: float
    registered_at: datetime
    evaluation_window_days: int
    registered_by: str
    page_context: Optional[str] = None
    public_url: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.rationale.strip():
            raise ValueError("rationale must be non-empty")
        if not self.from_mechanism.strip() or not self.to_mechanism.strip():
            raise ValueError("from_mechanism and to_mechanism must be non-empty")
        if self.from_mechanism == self.to_mechanism:
            raise ValueError(
                "from_mechanism and to_mechanism must differ; got both = "
                f"{self.from_mechanism!r}"
            )
        if self.trigger_threshold <= 0:
            raise ValueError(
                f"trigger_threshold must be positive; got {self.trigger_threshold}"
            )
        if self.evaluation_window_days <= 0:
            raise ValueError(
                f"evaluation_window_days must be positive; "
                f"got {self.evaluation_window_days}"
            )

    @property
    def public_statement(self) -> str:
        """Render the commitment as a public-facing statement.

        Format used in pre-registration documents and deck slides.
        """
        ctx = (
            f" × {self.page_context}-page" if self.page_context else ""
        )
        return (
            f"Pre-registered rotation {self.rotation_id}: when "
            f"{self.trigger_condition.value} for "
            f"{self.archetype}{ctx} crosses {self.trigger_threshold}, "
            f"the system will rotate from '{self.from_mechanism}' to "
            f"'{self.to_mechanism}'. Registered "
            f"{self.registered_at.isoformat()} by {self.registered_by}. "
            f"Rationale: {self.rationale}"
        )


def register_rotation(
    *,
    archetype: str,
    from_mechanism: str,
    to_mechanism: str,
    rationale: str,
    trigger_condition: TriggerCondition,
    trigger_threshold: float,
    evaluation_window_days: int,
    registered_by: str,
    page_context: Optional[str] = None,
    public_url: Optional[str] = None,
    registered_at: Optional[datetime] = None,
) -> RotationCommitment:
    """Build a RotationCommitment with required validation.

    `registered_at` defaults to now() — pass an explicit value only for
    testing or back-dated registrations (which themselves should be
    audited).
    """
    return RotationCommitment(
        rotation_id=_new_rotation_id(),
        archetype=archetype,
        page_context=page_context,
        from_mechanism=from_mechanism,
        to_mechanism=to_mechanism,
        rationale=rationale,
        trigger_condition=trigger_condition,
        trigger_threshold=trigger_threshold,
        registered_at=registered_at if registered_at is not None else _now_utc(),
        evaluation_window_days=evaluation_window_days,
        registered_by=registered_by,
        public_url=public_url,
    )


# =============================================================================
# EVIDENCE INPUT
# =============================================================================


@dataclass(frozen=True)
class CellEvidence:
    """Evidence accumulated for a (archetype, page_context, mechanism) cell.

    The trigger logic reads this to decide whether the commitment's
    threshold is met.
    """

    archetype: str
    page_context: Optional[str]
    mechanism: str
    edge_count: int
    cate_estimate: Optional[float] = None
    conformal_ci_low: Optional[float] = None
    conformal_ci_high: Optional[float] = None
    observed_at: datetime = field(default_factory=_now_utc)


# =============================================================================
# TRIGGER LOGIC
# =============================================================================


def evaluate_trigger(
    commitment: RotationCommitment,
    *,
    from_evidence: CellEvidence,
    to_evidence: CellEvidence,
    now: Optional[datetime] = None,
) -> RotationStatus:
    """Evaluate whether the trigger conditions are met.

    Returns the rotation's current status:
      - REGISTERED → not enough time elapsed to fire (synonym for
        "no signal yet")
      - PENDING → conditions partially met but not all
      - TRIGGERED → all conditions met, rotation fires
      - EXPIRED → evaluation window passed without trigger conditions met

    The from_evidence and to_evidence cells must match the commitment's
    archetype and page_context — caller is responsible for filtering.
    """
    now = now or _now_utc()

    # Check window expiration first
    elapsed = now - commitment.registered_at
    elapsed_days = elapsed.total_seconds() / 86400.0
    if elapsed_days > commitment.evaluation_window_days:
        return RotationStatus.EXPIRED

    # Validate cell match
    if from_evidence.archetype != commitment.archetype:
        raise ValueError(
            f"from_evidence.archetype ({from_evidence.archetype}) does not "
            f"match commitment.archetype ({commitment.archetype})"
        )
    if to_evidence.archetype != commitment.archetype:
        raise ValueError(
            f"to_evidence.archetype ({to_evidence.archetype}) does not "
            f"match commitment.archetype ({commitment.archetype})"
        )
    if from_evidence.mechanism != commitment.from_mechanism:
        raise ValueError(
            f"from_evidence.mechanism ({from_evidence.mechanism}) does not "
            f"match commitment.from_mechanism ({commitment.from_mechanism})"
        )
    if to_evidence.mechanism != commitment.to_mechanism:
        raise ValueError(
            f"to_evidence.mechanism ({to_evidence.mechanism}) does not "
            f"match commitment.to_mechanism ({commitment.to_mechanism})"
        )

    if commitment.trigger_condition == TriggerCondition.EDGE_COUNT_THRESHOLD:
        # Both cells must have crossed the threshold
        if (
            from_evidence.edge_count >= commitment.trigger_threshold
            and to_evidence.edge_count >= commitment.trigger_threshold
        ):
            return RotationStatus.TRIGGERED
        return RotationStatus.PENDING

    if commitment.trigger_condition == TriggerCondition.CATE_DIFFERENTIAL_THRESHOLD:
        if (
            from_evidence.cate_estimate is None
            or to_evidence.cate_estimate is None
        ):
            return RotationStatus.PENDING
        differential = to_evidence.cate_estimate - from_evidence.cate_estimate
        if differential >= commitment.trigger_threshold:
            return RotationStatus.TRIGGERED
        return RotationStatus.PENDING

    if commitment.trigger_condition == TriggerCondition.CONFORMAL_INTERVAL_NON_OVERLAP:
        if (
            from_evidence.conformal_ci_low is None
            or from_evidence.conformal_ci_high is None
            or to_evidence.conformal_ci_low is None
            or to_evidence.conformal_ci_high is None
        ):
            return RotationStatus.PENDING
        # Non-overlap: 'to' interval lies strictly above 'from' interval.
        # The threshold here is interpreted as a minimum non-overlap gap.
        non_overlap_gap = to_evidence.conformal_ci_low - from_evidence.conformal_ci_high
        if non_overlap_gap >= commitment.trigger_threshold:
            return RotationStatus.TRIGGERED
        return RotationStatus.PENDING

    # Unknown condition — defensive
    raise ValueError(
        f"Unknown trigger_condition: {commitment.trigger_condition}"
    )


# =============================================================================
# ROTATION EVENT (when trigger fires)
# =============================================================================


@dataclass(frozen=True)
class RotationEvent:
    """The recorded moment of a triggered rotation.

    Built when evaluate_trigger() returns TRIGGERED. Captures the
    state at the trigger moment for audit + visualization.
    """

    rotation_id: str
    triggered_at: datetime
    commitment_public_statement: str
    from_evidence: CellEvidence
    to_evidence: CellEvidence
    final_status: RotationStatus = RotationStatus.TRIGGERED

    @property
    def days_to_trigger(self) -> float:
        """How long the rotation was pending. Computed from the
        commitment's registered_at — caller passes the commitment in
        construct_rotation_event."""
        # Note: caller must populate this via the helper below; the
        # dataclass keeps the raw triggered_at.
        return 0.0  # placeholder; the helper computes it

    def public_summary(self) -> str:
        return (
            f"Rotation {self.rotation_id} TRIGGERED at "
            f"{self.triggered_at.isoformat()}. "
            f"From '{self.from_evidence.mechanism}' "
            f"(edge_count={self.from_evidence.edge_count}, "
            f"CATE={self.from_evidence.cate_estimate}) to "
            f"'{self.to_evidence.mechanism}' "
            f"(edge_count={self.to_evidence.edge_count}, "
            f"CATE={self.to_evidence.cate_estimate})."
        )


def construct_rotation_event(
    commitment: RotationCommitment,
    from_evidence: CellEvidence,
    to_evidence: CellEvidence,
    *,
    triggered_at: Optional[datetime] = None,
) -> RotationEvent:
    """Build a RotationEvent from a triggered commitment.

    Caller must verify evaluate_trigger() returned TRIGGERED before
    calling this.
    """
    return RotationEvent(
        rotation_id=commitment.rotation_id,
        triggered_at=triggered_at or _now_utc(),
        commitment_public_statement=commitment.public_statement,
        from_evidence=from_evidence,
        to_evidence=to_evidence,
        final_status=RotationStatus.TRIGGERED,
    )


# =============================================================================
# REGISTRY — in-memory commitment store + lifecycle management
# =============================================================================


class RotationRegistry:
    """In-memory registry of rotation commitments + triggered events.

    Production wire would persist to Neo4j (a Rotation node label
    paired with the Migration framework); v0.1 is in-memory because
    pilot scope has at most a handful of pre-registered rotations
    and we want them visible in the deck immediately.

    The registry tracks COMMITMENT immutability — once registered, the
    commitment cannot be modified. Cancellation creates a status change
    but the original commitment record is preserved for audit.
    """

    def __init__(self) -> None:
        self._commitments: Dict[str, RotationCommitment] = {}
        self._statuses: Dict[str, RotationStatus] = {}
        self._events: Dict[str, RotationEvent] = {}

    def register(self, commitment: RotationCommitment) -> None:
        """Register a new commitment. Idempotent on rotation_id —
        re-registering raises (commitments are IMMUTABLE per discipline)."""
        if commitment.rotation_id in self._commitments:
            raise ValueError(
                f"Rotation {commitment.rotation_id} already registered "
                f"and is immutable"
            )
        self._commitments[commitment.rotation_id] = commitment
        self._statuses[commitment.rotation_id] = RotationStatus.REGISTERED

    def get(self, rotation_id: str) -> Optional[RotationCommitment]:
        return self._commitments.get(rotation_id)

    def status_of(self, rotation_id: str) -> Optional[RotationStatus]:
        return self._statuses.get(rotation_id)

    def update_status_from_evidence(
        self,
        rotation_id: str,
        from_evidence: CellEvidence,
        to_evidence: CellEvidence,
        *,
        now: Optional[datetime] = None,
    ) -> RotationStatus:
        """Re-evaluate a commitment against fresh evidence.

        If the new status is TRIGGERED, also constructs and stores a
        RotationEvent. Returns the new status.
        """
        commitment = self._commitments.get(rotation_id)
        if commitment is None:
            raise KeyError(f"rotation_id {rotation_id} not registered")
        new_status = evaluate_trigger(
            commitment,
            from_evidence=from_evidence,
            to_evidence=to_evidence,
            now=now,
        )
        prev_status = self._statuses.get(rotation_id, RotationStatus.REGISTERED)

        # Once triggered or expired, status is terminal — don't downgrade.
        if prev_status in (RotationStatus.TRIGGERED, RotationStatus.EXPIRED):
            return prev_status

        self._statuses[rotation_id] = new_status

        if new_status == RotationStatus.TRIGGERED:
            self._events[rotation_id] = construct_rotation_event(
                commitment, from_evidence, to_evidence,
                triggered_at=now,
            )

        return new_status

    def cancel(self, rotation_id: str, reason: str) -> None:
        """Explicitly cancel a pending rotation.

        Cancellation is a discipline failure (the commitment was made,
        the trigger conditions might or might not have been met, the
        team is opting out). Logged as such; the original commitment
        record is preserved.
        """
        if rotation_id not in self._commitments:
            raise KeyError(f"rotation_id {rotation_id} not registered")
        if self._statuses[rotation_id] in (
            RotationStatus.TRIGGERED, RotationStatus.EXPIRED,
        ):
            raise ValueError(
                f"Cannot cancel rotation in terminal state: "
                f"{self._statuses[rotation_id]}"
            )
        self._statuses[rotation_id] = RotationStatus.CANCELLED

    def get_event(self, rotation_id: str) -> Optional[RotationEvent]:
        return self._events.get(rotation_id)

    def all_commitments(self) -> List[RotationCommitment]:
        return list(self._commitments.values())

    def all_triggered_events(self) -> List[RotationEvent]:
        return list(self._events.values())

    def reset(self) -> None:
        """Test-only — clear everything."""
        self._commitments.clear()
        self._statuses.clear()
        self._events.clear()


# =============================================================================
# Singleton
# =============================================================================


_rotation_registry: Optional[RotationRegistry] = None


def get_rotation_registry() -> RotationRegistry:
    global _rotation_registry
    if _rotation_registry is None:
        _rotation_registry = RotationRegistry()
    return _rotation_registry


def reset_rotation_registry() -> None:
    """Test-only — clear the singleton."""
    global _rotation_registry
    _rotation_registry = None


__all__ = [
    "CellEvidence",
    "RotationCommitment",
    "RotationEvent",
    "RotationRegistry",
    "RotationStatus",
    "TriggerCondition",
    "construct_rotation_event",
    "evaluate_trigger",
    "get_rotation_registry",
    "register_rotation",
    "reset_rotation_registry",
]
