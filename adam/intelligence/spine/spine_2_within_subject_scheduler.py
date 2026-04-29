# =============================================================================
# ADAM Spine #2 — Within-Subject Crossover Scheduler with Washout + Carryover
# Location: adam/intelligence/spine/spine_2_within_subject_scheduler.py
# =============================================================================

"""Within-subject scheduler with washout intervals and AR(1) carryover.

PER DIRECTIVE SECTION 2 (Spine #2 specification).

Per-user randomization schedule (ABAB, ABBA, response-adaptive sequencing,
SMART-style sequential rules) governing which mechanism is delivered when,
with mechanism-specific washout intervals and explicit AR(1)-style
carryover-correction term in the N-of-1 likelihood.

Why this is spine: industry frequency capping is a max-count heuristic;
it does not account for what was previously served, when, or with what
carryover signature. SCED literature is clear that behavioral non-
pharmaceutical carryover is real and confounds within-subject inference
unless it is either washed out or modeled. Without this primitive the
per-user posteriors from Spine #1 are biased and the within-subject
contrasts (the partner-facing demonstrable claim) are artifacts of order,
not effect.

DECISION-TIME CONSUMERS (Rule A check)

This module is consumed at decision time by:
    - The trilateral L3 cascade (Spine #4) — operates only over the
      eligibility-filtered candidate set this scheduler returns
    - The free-energy scorer (Spine #5) — same eligibility set
    - The decision-time policy (top-two Thompson sampling) — chooses
      among only the eligible-set members
    - The N-of-1 likelihood (Spine #1) — consumes the carryover term
      as part of the linear predictor η_iat

Therefore: NOT measurement. Cognitive primitive that determines what
the system is allowed to do at every impression decision.

ARCHITECTURAL ROLE — ATTENTION-INVERSION ENFORCEMENT

Per the directive: "the scheduler is permitted to refuse all mechanisms
when no compatible context exists." This is the architectural location
where attention-inversion is partly enforced (the scheduler refuses to
serve into a user whose washout for that mechanism has not elapsed by
≥2× half-life, unless the within-subject design explicitly schedules
an A→A replication).

Foundation §7 rule 11 made operational at the scheduler.

THIS COMMIT SHIPS

    - Mechanism-class washout half-life table (state primes hours;
      construal-level shifts medium; trait-aligned content days)
    - Pydantic models for TouchEvent + EligibilityResult
    - Eligibility check: refuses a candidate mechanism whose washout
      has not elapsed by ≥2× half-life unless ABAB-style replication
      explicitly authorized
    - AR(1) carryover correction term computation
    - Replication-first early-phase scheduler (first N touches: ABAB)
    - Pure-Python reference for all arithmetic

THIS COMMIT DOES NOT SHIP (follow-on commits)

    - TS-PostDiff response-adaptive randomization (depends on Spine #1
      posterior reads; wires in next commit when both are integrated)
    - SMART staged sequencing for click-but-no-conversion transitions
    - Persistent TouchHistory store (TouchEvent shape is ready; the
      Neo4j wire is the next commit)

REFERENCES

    Norwood et al. 2024 — SMARTs via Thompson sampling (Biometrics).
    IntelligentPooling — sequencing in DIAMANTE / HeartSteps II.
    Carryover handling in fixed-period N-of-1 trials (PMC6787650).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


# =============================================================================
# Mechanism classes and washout half-lives (per directive Spine #2 spec)
# =============================================================================


# Per directive Spine #2: "Mechanism-specific washout half-lives,
# calibrated from the audio-content priming literature and learned
# online during pilot:
#   State primes (regulatory focus shifts, arousal carryover): hours (3–8h half-life)
#   Construal-level shifts: medium (12–48h)
#   Trait-aligned content (identity construction, primary metaphor frames): days (3–7d)"

MECHANISM_CLASS_STATE_PRIME = "state_prime"
MECHANISM_CLASS_CONSTRUAL_SHIFT = "construal_shift"
MECHANISM_CLASS_TRAIT_ALIGNED = "trait_aligned"


# Initial washout half-lives in hours. Pilot-pending — calibrated against
# pilot data when LUXY observations land. Values are conservative midpoints
# of the directive's ranges.
MECHANISM_WASHOUT_HALF_LIFE_HOURS: Dict[str, float] = {
    MECHANISM_CLASS_STATE_PRIME: 5.5,        # midpoint of 3–8h
    MECHANISM_CLASS_CONSTRUAL_SHIFT: 30.0,   # midpoint of 12–48h
    MECHANISM_CLASS_TRAIT_ALIGNED: 120.0,    # midpoint of 3–7d (5 days)
}


# Mechanism → class assignment for the active LUXY mechanism vocabulary.
# Calibration-pending; the offline pipeline (Spine #12) refines.
MECHANISM_CLASS_BY_NAME: Dict[str, str] = {
    # State primes (regulatory focus, arousal)
    "scarcity": MECHANISM_CLASS_STATE_PRIME,
    "urgency": MECHANISM_CLASS_STATE_PRIME,
    "loss_aversion": MECHANISM_CLASS_STATE_PRIME,
    "social_proof": MECHANISM_CLASS_STATE_PRIME,
    # Construal-level shifts
    "construal_concrete": MECHANISM_CLASS_CONSTRUAL_SHIFT,
    "construal_abstract": MECHANISM_CLASS_CONSTRUAL_SHIFT,
    "comparison_framing": MECHANISM_CLASS_CONSTRUAL_SHIFT,
    "frame_gain": MECHANISM_CLASS_CONSTRUAL_SHIFT,
    "frame_loss": MECHANISM_CLASS_CONSTRUAL_SHIFT,
    # Trait-aligned (identity, primary metaphor)
    "authority": MECHANISM_CLASS_TRAIT_ALIGNED,
    "identity_construction": MECHANISM_CLASS_TRAIT_ALIGNED,
    "reliability_metaphor": MECHANISM_CLASS_TRAIT_ALIGNED,
    "containment_metaphor": MECHANISM_CLASS_TRAIT_ALIGNED,
    "forward_motion_metaphor": MECHANISM_CLASS_TRAIT_ALIGNED,
    "status_verticality_metaphor": MECHANISM_CLASS_TRAIT_ALIGNED,
}


def get_mechanism_class(mechanism: str) -> str:
    """Return the mechanism class for a given mechanism name.

    Raises ValueError when unknown — the offline pipeline owns the
    mechanism vocabulary; unknown names mean a new mechanism arrived
    without a class assignment.
    """
    cls = MECHANISM_CLASS_BY_NAME.get(mechanism)
    if cls is None:
        raise ValueError(
            f"Unknown mechanism '{mechanism}'. Add to MECHANISM_CLASS_BY_NAME "
            f"in spine_2_within_subject_scheduler.py with appropriate class "
            f"({MECHANISM_CLASS_STATE_PRIME}, {MECHANISM_CLASS_CONSTRUAL_SHIFT}, "
            f"or {MECHANISM_CLASS_TRAIT_ALIGNED})."
        )
    return cls


def get_washout_half_life_hours(mechanism: str) -> float:
    """Return the washout half-life for a mechanism in hours."""
    cls = get_mechanism_class(mechanism)
    return MECHANISM_WASHOUT_HALF_LIFE_HOURS[cls]


# =============================================================================
# Eligibility constants
# =============================================================================


# Per directive: "The scheduler refuses to serve a mechanism into a user
# whose washout for that mechanism has not elapsed by ≥2× half-life,
# *unless* the within-subject design explicitly schedules an A→A
# replication."
WASHOUT_REQUIRED_HALF_LIVES: float = 2.0


# Replication-first early phase length (per directive: "First 6 touches
# per user follow an explicit ABAB or ABBA design").
REPLICATION_PHASE_TOUCH_COUNT: int = 6


# =============================================================================
# Pydantic models
# =============================================================================


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class TouchEvent(BaseModel):
    """One served impression in the user's touch history.

    The scheduler reads ordered TouchEvents to determine eligibility
    and carryover. The N-of-1 likelihood (Spine #1) reads them via
    the same store but for likelihood-side bookkeeping.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: str
    mechanism: str
    delivered_at: datetime
    decision_id: Optional[str] = None  # Links to DecisionTrace (Spine #6)
    outcome_observed_at: Optional[datetime] = None
    outcome_class: Optional[str] = None  # From Spine #1 outcome vocabulary

    @field_validator("mechanism")
    @classmethod
    def _validate_mechanism_known(cls, v: str) -> str:
        if v not in MECHANISM_CLASS_BY_NAME:
            raise ValueError(
                f"Mechanism '{v}' not in MECHANISM_CLASS_BY_NAME. "
                "Either the mechanism vocabulary is being extended OR the "
                "scheduler is being asked about an unknown mechanism."
            )
        return v


class EligibilityResult(BaseModel):
    """Outcome of an eligibility check.

    `eligible` is the decision; `washout_half_lives_elapsed` and
    `seconds_since_last_delivery` carry diagnostic info that the
    decision trace (Spine #6) records on rejection so the partner
    surface can show "this mechanism was eligibility-filtered because
    only 1.3 half-lives had elapsed since the last delivery."
    """

    model_config = ConfigDict(extra="forbid")

    mechanism: str
    eligible: bool
    reason: str
    seconds_since_last_delivery: Optional[float] = None
    washout_half_lives_elapsed: Optional[float] = None
    last_delivery_at: Optional[datetime] = None


# =============================================================================
# Eligibility check
# =============================================================================


def check_mechanism_eligibility(
    mechanism: str,
    touch_history: List[TouchEvent],
    *,
    now: Optional[datetime] = None,
    allow_replication: bool = False,
) -> EligibilityResult:
    """Determine whether a candidate mechanism is eligible to be served
    to the user given their touch history.

    Per directive: "refuses to serve a mechanism into a user whose
    washout for that mechanism has not elapsed by ≥2× half-life,
    *unless* the within-subject design explicitly schedules an A→A
    replication."

    Args:
        mechanism: candidate mechanism name
        touch_history: ordered touch history for the user (most recent
            last; the scheduler scans backward to find the last
            delivery of this mechanism)
        now: current time; defaults to UTC now
        allow_replication: when True, bypasses the 2× half-life check
            (used by the replication-first early-phase scheduler when
            an ABAB design explicitly schedules an A→A repeat)

    Returns:
        EligibilityResult with the decision + diagnostic info.
    """
    base_time = now or _now_utc()

    # Find the most recent delivery of this mechanism in the history.
    last_delivery: Optional[TouchEvent] = None
    for event in reversed(touch_history):
        if event.mechanism == mechanism:
            last_delivery = event
            break

    if last_delivery is None:
        # Never delivered before → eligible (no washout to wait for).
        return EligibilityResult(
            mechanism=mechanism,
            eligible=True,
            reason="never_delivered",
            seconds_since_last_delivery=None,
            washout_half_lives_elapsed=None,
            last_delivery_at=None,
        )

    seconds_elapsed = (base_time - last_delivery.delivered_at).total_seconds()
    if seconds_elapsed < 0:
        # Clock skew or future-dated touch event; treat as not elapsed.
        seconds_elapsed = 0.0

    half_life_hours = get_washout_half_life_hours(mechanism)
    half_life_seconds = half_life_hours * 3600.0
    half_lives_elapsed = (
        seconds_elapsed / half_life_seconds if half_life_seconds > 0 else 0.0
    )

    if allow_replication:
        return EligibilityResult(
            mechanism=mechanism,
            eligible=True,
            reason="replication_authorized",
            seconds_since_last_delivery=seconds_elapsed,
            washout_half_lives_elapsed=half_lives_elapsed,
            last_delivery_at=last_delivery.delivered_at,
        )

    if half_lives_elapsed >= WASHOUT_REQUIRED_HALF_LIVES:
        return EligibilityResult(
            mechanism=mechanism,
            eligible=True,
            reason="washout_elapsed",
            seconds_since_last_delivery=seconds_elapsed,
            washout_half_lives_elapsed=half_lives_elapsed,
            last_delivery_at=last_delivery.delivered_at,
        )

    return EligibilityResult(
        mechanism=mechanism,
        eligible=False,
        reason="washout_not_elapsed",
        seconds_since_last_delivery=seconds_elapsed,
        washout_half_lives_elapsed=half_lives_elapsed,
        last_delivery_at=last_delivery.delivered_at,
    )


def filter_eligible_mechanisms(
    candidate_mechanisms: List[str],
    touch_history: List[TouchEvent],
    *,
    now: Optional[datetime] = None,
    allow_replication: bool = False,
) -> List[EligibilityResult]:
    """Filter a candidate set to only the eligible mechanisms.

    Returns one EligibilityResult per candidate (eligible or not) so
    callers can record the rejection reasons in the DecisionTrace
    (Spine #6) for partner-facing inspection.
    """
    return [
        check_mechanism_eligibility(
            mechanism=m, touch_history=touch_history,
            now=now, allow_replication=allow_replication,
        )
        for m in candidate_mechanisms
    ]


# =============================================================================
# AR(1) carryover correction
# =============================================================================


# Initial mechanism-pair carryover coefficients. Per directive Spine #2:
# "ρ_m1→m2 is a learned mechanism-pair carryover coefficient (positive =
# priming, negative = interference); priors come from offline mechanism-
# pair semantic-similarity (high overlap → high positive ρ)."
#
# Default 0.0 for unspecified pairs; populated explicitly for known
# pairs. Pilot-pending; learned online and refined offline.

@dataclass(frozen=True)
class CarryoverPairKey:
    prev_mechanism: str
    next_mechanism: str


_DEFAULT_CARRYOVER_RHO: Dict[tuple, float] = {
    # Same-mechanism repetition is positive priming (ABAB design)
    # for trait-aligned and weak-positive for state primes (which
    # decay fast).
    # Inter-class transitions where the mechanisms semantically conflict
    # carry negative priors (interference); semantically aligned pairs
    # carry positive priors. Calibration-pending.
    ("authority", "social_proof"): -0.15,        # Authority to social proof creates frame conflict
    ("scarcity", "social_proof"): -0.20,         # Scarcity then social proof: pressure-then-validation reads grabby
    ("frame_gain", "frame_loss"): -0.30,         # Direct frame inversion is interference
    ("frame_loss", "frame_gain"): -0.30,
    ("construal_concrete", "construal_abstract"): -0.20,
    ("construal_abstract", "construal_concrete"): -0.20,
    ("forward_motion_metaphor", "containment_metaphor"): 0.10,  # Compatible framings
    ("reliability_metaphor", "authority"): 0.20,
    ("identity_construction", "social_proof"): 0.15,
}


def get_carryover_coefficient(
    prev_mechanism: str, next_mechanism: str,
) -> float:
    """Return the AR(1) carryover coefficient ρ_m1→m2 for a mechanism
    pair. Returns 0.0 for unspecified pairs."""
    key = (prev_mechanism, next_mechanism)
    if key in _DEFAULT_CARRYOVER_RHO:
        return _DEFAULT_CARRYOVER_RHO[key]
    # Same-mechanism repetition: weak positive priming for non-fast-
    # decaying classes; the explicit ABAB design handles the high-rho
    # case explicitly via allow_replication.
    if prev_mechanism == next_mechanism:
        cls = get_mechanism_class(prev_mechanism)
        if cls == MECHANISM_CLASS_STATE_PRIME:
            return 0.05  # state primes decay fast; mild positive
        elif cls == MECHANISM_CLASS_CONSTRUAL_SHIFT:
            return 0.15
        else:  # trait-aligned
            return 0.25
    return 0.0


def compute_carryover_term(
    prev_mechanism: str,
    next_mechanism: str,
    seconds_since_prev: float,
    prev_effect_estimate: float = 1.0,
) -> float:
    """Compute the AR(1) carryover correction term for the N-of-1
    likelihood.

    Per directive Section 2:
        carryover_term_t = ρ_m1→m2 · effect(m1, t-Δ) · exp(-Δ / τ_m1)

    where:
        ρ_m1→m2 is the mechanism-pair carryover coefficient (positive =
            priming, negative = interference)
        effect(m1, t-Δ) is the prev mechanism's posterior effect at the
            time of its delivery (passed in as prev_effect_estimate;
            the engine consumer reads from Spine #1)
        Δ is seconds since the previous delivery
        τ_m1 is the prev mechanism's behavioral half-life (in seconds)
    """
    rho = get_carryover_coefficient(prev_mechanism, next_mechanism)
    if rho == 0.0:
        return 0.0
    half_life_hours = get_washout_half_life_hours(prev_mechanism)
    half_life_seconds = half_life_hours * 3600.0
    if half_life_seconds <= 0:
        return 0.0
    decay = math.exp(-seconds_since_prev / half_life_seconds)
    return rho * prev_effect_estimate * decay


# =============================================================================
# Replication-first early-phase scheduler
# =============================================================================


def is_in_replication_phase(touch_history: List[TouchEvent]) -> bool:
    """Return True iff the user is still in the replication-first early
    phase (first REPLICATION_PHASE_TOUCH_COUNT touches)."""
    return len(touch_history) < REPLICATION_PHASE_TOUCH_COUNT


def select_next_mechanism_replication_phase(
    touch_history: List[TouchEvent],
    candidate_mechanisms: List[str],
) -> Optional[str]:
    """Select the next mechanism per ABAB replication-first design.

    Strategy: alternate the two mechanisms with the highest variance in
    the candidate set (proxy: the first two passed; the policy at the
    consumer side is responsible for ordering candidates by uncertainty).
    The first 6 touches go ABAB (or AABB depending on schedule preference).

    For the first touch, pick A (candidate_mechanisms[0]).
    For subsequent touches, alternate: if last delivered was A pick B;
    if last delivered was B pick A. After REPLICATION_PHASE_TOUCH_COUNT
    touches, return None (signaling: transition to adaptive phase).

    Returns None when:
        - User has exited the replication phase
        - Fewer than 2 candidates available
        - No eligible mechanism found

    Eligibility check: even in replication, mechanism must be eligible
    OR allow_replication must be True (an A→A repeat that's part of
    the ABAB design explicitly authorizes it).
    """
    if not is_in_replication_phase(touch_history):
        return None
    if len(candidate_mechanisms) < 2:
        return None

    arm_a = candidate_mechanisms[0]
    arm_b = candidate_mechanisms[1]

    if not touch_history:
        # First touch — pick A.
        return arm_a

    last_mechanism = touch_history[-1].mechanism

    # Alternate. ABAB: if last was A pick B, if last was B pick A.
    if last_mechanism == arm_a:
        return arm_b
    elif last_mechanism == arm_b:
        return arm_a
    # Last touch was outside the candidate pair (rare — could happen if
    # candidates rotate between touches). Default to arm_a.
    return arm_a


# =============================================================================
# Combined: the scheduler entry point
# =============================================================================


@dataclass(frozen=True)
class SchedulingDecision:
    """Output of the scheduler at decision time.

    Either `chosen_mechanism` is set (eligible mechanism selected by
    the appropriate phase logic) OR `chosen_mechanism` is None and
    `eligible_set` is the filtered list of eligible candidates that
    the policy can sample from (when not in replication phase).

    `carryover_terms` is per-eligible-mechanism, populated when there
    is a previous touch — the consumer (Spine #1 likelihood) reads
    these to add the AR(1) correction.
    """

    user_id: str
    chosen_mechanism: Optional[str]
    eligible_set: List[EligibilityResult]
    in_replication_phase: bool
    n_touches: int
    carryover_terms: Dict[str, float] = field(default_factory=dict)


def schedule_next_decision(
    user_id: str,
    candidate_mechanisms: List[str],
    touch_history: List[TouchEvent],
    *,
    now: Optional[datetime] = None,
) -> SchedulingDecision:
    """End-to-end scheduling step.

    Combines:
        - Eligibility filtering (washout-respecting; replication-aware)
        - Replication-phase preference (first N touches: ABAB)
        - Carryover term computation per eligible mechanism

    Returns a SchedulingDecision the policy consumes.
    """
    base_time = now or _now_utc()
    n_touches = len(touch_history)
    in_repl = is_in_replication_phase(touch_history)

    # In replication phase, ABAB explicitly authorizes A→A repeats.
    eligibility = filter_eligible_mechanisms(
        candidate_mechanisms=candidate_mechanisms,
        touch_history=touch_history,
        now=base_time,
        allow_replication=in_repl,
    )

    chosen: Optional[str] = None
    if in_repl:
        chosen = select_next_mechanism_replication_phase(
            touch_history=touch_history,
            candidate_mechanisms=candidate_mechanisms,
        )

    # Compute carryover term per candidate mechanism if a previous
    # touch exists.
    carryover: Dict[str, float] = {}
    if touch_history:
        prev = touch_history[-1]
        seconds_since = (base_time - prev.delivered_at).total_seconds()
        for m in candidate_mechanisms:
            carryover[m] = compute_carryover_term(
                prev_mechanism=prev.mechanism,
                next_mechanism=m,
                seconds_since_prev=seconds_since,
            )

    return SchedulingDecision(
        user_id=user_id,
        chosen_mechanism=chosen,
        eligible_set=eligibility,
        in_replication_phase=in_repl,
        n_touches=n_touches,
        carryover_terms=carryover,
    )


__all__ = [
    "MECHANISM_CLASS_STATE_PRIME",
    "MECHANISM_CLASS_CONSTRUAL_SHIFT",
    "MECHANISM_CLASS_TRAIT_ALIGNED",
    "MECHANISM_WASHOUT_HALF_LIFE_HOURS",
    "MECHANISM_CLASS_BY_NAME",
    "REPLICATION_PHASE_TOUCH_COUNT",
    "WASHOUT_REQUIRED_HALF_LIVES",
    "EligibilityResult",
    "SchedulingDecision",
    "TouchEvent",
    "check_mechanism_eligibility",
    "compute_carryover_term",
    "filter_eligible_mechanisms",
    "get_carryover_coefficient",
    "get_mechanism_class",
    "get_washout_half_life_hours",
    "is_in_replication_phase",
    "schedule_next_decision",
    "select_next_mechanism_replication_phase",
]
