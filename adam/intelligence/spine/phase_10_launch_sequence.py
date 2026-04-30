# =============================================================================
# ADAM Phase 10 — Launch Sequence + 8 RED-Criteria
# Location: adam/intelligence/spine/phase_10_launch_sequence.py
# =============================================================================

"""Launch sequence + RED-criterion gates.

PER DIRECTIVE SECTION 9 PHASE 10.

Soft launch (10% of campaign budget against holdout) → ramp to 50%
after first week if no RED-criterion fires → full launch. Continuous
monitoring uses the spine's own observability (NOT the cut measurement
layer per directive Section 8.1).

EIGHT RED-CRITERIA FOR DEFERRING LAUNCH (per directive verbatim)

ANY ONE of the following triggers a launch deferral:
    1. Fluency-floor violation rate >5%
    2. Decision-trace emission rate <99%
    3. Per-user posterior pathologies (divergent posteriors, non-
       update on observed events, identity-stability weight collapse
       for >30% of touches)
    4. mSPRT lower-boundary cross during soft launch
    5. Defensive Reasoning panel produces output that makes the CMO
       uncomfortable in final review
    6. Any creative in rotation fails primary-metaphor coherence in
       spot check despite passing the offline-pipeline scorer
    7. Bid-time latency p99 >120ms above StackAdapt budget
    8. sapid round-trip rate <95%

NON-RED ISSUES (do NOT block launch per directive)
    - Per-archetype lift heterogeneity not reportable yet (deleted
      that path; intentional)
    - Calibration journals not produced (intentional)
    - Some elicited priors not yet fully incorporated (Loop B iterative)
    - Posterior coverage on low-touch users wider than population
      (partial pooling handles by design)

DECISION-TIME CONSUMERS (Rule A check)

Launch sequence operates at every soft-launch monitoring tick (daily)
+ phase-transition decisions (week boundary). The 8 RED checks read
from the spine's running state at those decision moments. Cognitive
primitive at the LAUNCH-DECISION layer (a higher cadence than bid-
time, but still decision-time, not measurement).

REFERENCES

    Per directive: 'Continuous monitoring (the spine's own
    observability — not the cut measurement layer).'
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# Launch phase enum + thresholds
# =============================================================================


class LaunchPhase(str, Enum):
    """Three launch phases per directive Section 9 Phase 10."""

    PRE_LAUNCH = "pre_launch"       # all gates not yet GREEN
    SOFT_10 = "soft_10"             # 10% of budget; daily monitoring
    RAMP_50 = "ramp_50"             # 50% of budget; week 2+
    FULL_100 = "full_100"           # full launch
    DEFERRED = "deferred"           # RED-criterion triggered; launch held


# RED-criterion thresholds per directive Section 9 Phase 10
RED_FLUENCY_FLOOR_VIOLATION_RATE_MAX: float = 0.05         # >5% triggers RED
RED_DECISION_TRACE_EMISSION_RATE_MIN: float = 0.99         # <99% triggers RED
RED_IDENTITY_STABILITY_COLLAPSE_FRACTION_MAX: float = 0.30  # >30% touches → RED
RED_BID_TIME_LATENCY_P99_OVER_BUDGET_MS_MAX: float = 120.0  # p99 over budget
RED_SAPID_ROUND_TRIP_RATE_MIN: float = 0.95                 # <95% triggers RED


# =============================================================================
# Per-criterion check structures
# =============================================================================


class REDCriterion(str, Enum):
    """The 8 RED criteria per directive Section 9 Phase 10."""

    FLUENCY_FLOOR_VIOLATION = "fluency_floor_violation"
    DECISION_TRACE_EMISSION = "decision_trace_emission"
    POSTERIOR_PATHOLOGY = "posterior_pathology"
    MSPRT_LOWER_CROSSED = "msprt_lower_crossed"
    CMO_UNCOMFORTABLE = "cmo_uncomfortable"
    METAPHOR_COHERENCE_FAILED = "metaphor_coherence_failed"
    BID_TIME_LATENCY_P99 = "bid_time_latency_p99"
    SAPID_ROUND_TRIP = "sapid_round_trip"


@dataclass(frozen=True)
class CriterionCheck:
    """Result of one RED-criterion check.

    `triggered` is the gate decision (True = RED). `observed_value`
    is the actual measurement; `threshold` is the directive's
    boundary. `description` is templated narrative for partner audit.
    """

    criterion: REDCriterion
    triggered: bool
    observed_value: float
    threshold: float
    description: str = ""


# =============================================================================
# Eight RED-criterion check functions (each pure, structured input)
# =============================================================================


def check_fluency_floor_violation(
    n_decisions: int,
    n_floor_violations: int,
    *,
    threshold: float = RED_FLUENCY_FLOOR_VIOLATION_RATE_MAX,
) -> CriterionCheck:
    """Per directive: 'Fluency-floor violation rate >5%' triggers RED."""
    rate = (
        n_floor_violations / n_decisions if n_decisions > 0 else 0.0
    )
    return CriterionCheck(
        criterion=REDCriterion.FLUENCY_FLOOR_VIOLATION,
        triggered=rate > threshold,
        observed_value=rate,
        threshold=threshold,
        description=(
            f"Fluency-floor violation rate {rate:.2%} (threshold {threshold:.0%})"
        ),
    )


def check_decision_trace_emission(
    n_bids: int,
    n_traces_emitted: int,
    *,
    threshold: float = RED_DECISION_TRACE_EMISSION_RATE_MIN,
) -> CriterionCheck:
    """Per directive: 'Decision-trace emission rate <99%' triggers RED."""
    rate = (
        n_traces_emitted / n_bids if n_bids > 0 else 1.0
    )
    return CriterionCheck(
        criterion=REDCriterion.DECISION_TRACE_EMISSION,
        triggered=rate < threshold,
        observed_value=rate,
        threshold=threshold,
        description=(
            f"DecisionTrace emission rate {rate:.2%} (threshold {threshold:.0%})"
        ),
    )


def check_posterior_pathology(
    n_users_active: int,
    n_users_with_collapsed_identity_stability: int,
    *,
    threshold: float = RED_IDENTITY_STABILITY_COLLAPSE_FRACTION_MAX,
) -> CriterionCheck:
    """Per directive: 'Per-user posterior pathologies (divergent
    posteriors, non-update on observed events, identity-stability
    weight collapse for >30% of touches)' triggers RED.

    Substrate version uses identity-stability collapse as the
    measurable proxy; the broader 'divergent posteriors' check is
    operational (run by the variational-reconcile pipeline).
    """
    fraction = (
        n_users_with_collapsed_identity_stability / n_users_active
        if n_users_active > 0 else 0.0
    )
    return CriterionCheck(
        criterion=REDCriterion.POSTERIOR_PATHOLOGY,
        triggered=fraction > threshold,
        observed_value=fraction,
        threshold=threshold,
        description=(
            f"Identity-stability collapse fraction {fraction:.2%} "
            f"(threshold {threshold:.0%})"
        ),
    )


def check_msprt_lower_crossed(msprt_decision: str) -> CriterionCheck:
    """Per directive: 'mSPRT lower-boundary cross during soft launch'
    triggers RED. Reads from Phase 9 mSPRT state."""
    crossed = msprt_decision == "accept_null"
    return CriterionCheck(
        criterion=REDCriterion.MSPRT_LOWER_CROSSED,
        triggered=crossed,
        observed_value=1.0 if crossed else 0.0,
        threshold=0.0,
        description=(
            f"mSPRT decision: {msprt_decision} "
            f"({'LOWER CROSSED — RED' if crossed else 'no lower crossing'})"
        ),
    )


def check_cmo_uncomfortable(
    cmo_review_disposition: str,
) -> CriterionCheck:
    """Per directive: 'Defensive Reasoning panel produces output that
    makes the CMO uncomfortable in final review' triggers RED.

    Disposition is a categorical signal from the human reviewer:
    'comfortable' | 'uncomfortable' | 'pending'. (A12: structured.)
    """
    triggered = cmo_review_disposition == "uncomfortable"
    return CriterionCheck(
        criterion=REDCriterion.CMO_UNCOMFORTABLE,
        triggered=triggered,
        observed_value=1.0 if triggered else 0.0,
        threshold=0.0,
        description=f"CMO disposition: {cmo_review_disposition}",
    )


def check_metaphor_coherence_failed(
    n_creatives_in_rotation: int,
    n_creatives_failed_spot_check: int,
) -> CriterionCheck:
    """Per directive: 'Any creative in rotation fails primary-metaphor
    coherence in spot check despite passing the offline-pipeline scorer'
    triggers RED.

    NOTE: ANY failure triggers — not a rate threshold. One bad creative
    is sufficient grounds.
    """
    triggered = n_creatives_failed_spot_check > 0
    return CriterionCheck(
        criterion=REDCriterion.METAPHOR_COHERENCE_FAILED,
        triggered=triggered,
        observed_value=float(n_creatives_failed_spot_check),
        threshold=0.0,
        description=(
            f"{n_creatives_failed_spot_check} of {n_creatives_in_rotation} "
            f"creatives in rotation failed metaphor-coherence spot check"
        ),
    )


def check_bid_time_latency_p99(
    p99_latency_ms: float,
    stackadapt_budget_ms: float = 100.0,
    *,
    over_budget_threshold: float = RED_BID_TIME_LATENCY_P99_OVER_BUDGET_MS_MAX,
) -> CriterionCheck:
    """Per directive: 'Bid-time latency p99 >120ms above StackAdapt
    budget' triggers RED.

    Reads observed p99 latency vs the published StackAdapt bid budget.
    """
    excess = max(0.0, p99_latency_ms - stackadapt_budget_ms)
    return CriterionCheck(
        criterion=REDCriterion.BID_TIME_LATENCY_P99,
        triggered=excess > over_budget_threshold,
        observed_value=p99_latency_ms,
        threshold=stackadapt_budget_ms + over_budget_threshold,
        description=(
            f"Bid-time p99 {p99_latency_ms:.1f}ms (budget "
            f"{stackadapt_budget_ms:.0f}ms + tolerance "
            f"{over_budget_threshold:.0f}ms)"
        ),
    )


def check_sapid_round_trip(
    sapid_round_trip_rate: float,
    *,
    threshold: float = RED_SAPID_ROUND_TRIP_RATE_MIN,
) -> CriterionCheck:
    """Per directive: 'sapid round-trip rate <95%' triggers RED.

    Reads from Phase 8 SapidRoundTripMonitor.round_trip_rate().
    """
    return CriterionCheck(
        criterion=REDCriterion.SAPID_ROUND_TRIP,
        triggered=sapid_round_trip_rate < threshold,
        observed_value=sapid_round_trip_rate,
        threshold=threshold,
        description=(
            f"sapid round-trip rate {sapid_round_trip_rate:.2%} "
            f"(threshold {threshold:.0%})"
        ),
    )


# =============================================================================
# LaunchGateResult — aggregate of all 8 checks
# =============================================================================


class LaunchGateResult(BaseModel):
    """Aggregate evaluation of all 8 RED-criteria.

    Per directive: 'ANY ONE [of the 8 criteria] triggers a launch
    deferral.' This Pydantic model surfaces the structured result
    the partner-facing launch dashboard reads.
    """

    model_config = ConfigDict(extra="forbid")

    checks: List[CriterionCheck] = Field(default_factory=list)
    any_triggered: bool
    triggered_criteria: List[REDCriterion] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=_now_utc)


def evaluate_launch_gate(
    checks: List[CriterionCheck],
) -> LaunchGateResult:
    """Aggregate the 8 individual checks into a launch-gate decision.

    Per directive Section 9 Phase 10: ANY single triggered criterion
    defers launch.
    """
    triggered = [c for c in checks if c.triggered]
    return LaunchGateResult(
        checks=list(checks),
        any_triggered=len(triggered) > 0,
        triggered_criteria=[c.criterion for c in triggered],
    )


@dataclass(frozen=True)
class LaunchGateInputs:
    """Observed values for all 8 RED-criteria checks.

    Field shapes follow each check function's canonical signature
    (counts where the check uses counts; categorical strings where
    the check uses strings). Any field set to None means the caller
    has no data yet — that criterion is skipped (no check appended,
    not falsely set to "not triggered").

    The sole exception is sapid_round_trip_rate: when None, the
    runner pulls from the Phase 8 SapidRoundTripMonitor singleton —
    the canonical in-process source.
    """

    # check_fluency_floor_violation(n_decisions, n_floor_violations)
    n_decisions: Optional[int] = None
    n_floor_violations: Optional[int] = None

    # check_decision_trace_emission(n_bids, n_traces_emitted)
    n_bids: Optional[int] = None
    n_traces_emitted: Optional[int] = None

    # check_posterior_pathology(n_users_active, n_users_with_collapsed_identity_stability)
    n_users_active: Optional[int] = None
    n_users_with_collapsed_identity_stability: Optional[int] = None

    # check_msprt_lower_crossed(msprt_decision: str)
    msprt_decision: Optional[str] = None

    # check_cmo_uncomfortable(cmo_review_disposition: str)
    cmo_review_disposition: Optional[str] = None

    # check_metaphor_coherence_failed(n_creatives_in_rotation, n_creatives_failed_spot_check)
    n_creatives_in_rotation: Optional[int] = None
    n_creatives_failed_spot_check: Optional[int] = None

    # check_bid_time_latency_p99(p99_latency_ms, stackadapt_budget_ms)
    p99_latency_ms: Optional[float] = None
    stackadapt_budget_ms: float = 100.0

    # check_sapid_round_trip(sapid_round_trip_rate)
    # When None, the runner pulls from the Phase 8 monitor singleton.
    sapid_round_trip_rate: Optional[float] = None


def run_launch_gate_evaluation(
    inputs: LaunchGateInputs,
) -> LaunchGateResult:
    """Run all 8 RED-criteria checks against observed inputs.

    Per CODEBASE_AUDIT_2026_04_29.md §6 — Phase D real gap: the 8
    individual check functions existed plus the aggregator
    ``evaluate_launch_gate``, but no runner read each input from the
    spine state and composed the full evaluation. This function is
    the missing integration.

    Decision-time consumer: launch-gate evaluation is read at every
    phase-transition decision (daily soft-launch monitoring tick +
    week-boundary advance/defer decision). Per directive Section 9
    Phase 10: "ANY ONE [of the 8 criteria] triggers a launch
    deferral." A daily task or admin endpoint reads the result and
    feeds it into ``should_advance_phase``.

    Skip-when-no-data discipline: a criterion's check is appended
    ONLY when the caller provided non-None inputs for it. Missing
    data does NOT silently produce a "not triggered" check — that
    would let pre-launch operate as if every gate has been evaluated.
    """
    checks: List[CriterionCheck] = []

    if inputs.n_decisions is not None and inputs.n_floor_violations is not None:
        checks.append(check_fluency_floor_violation(
            inputs.n_decisions, inputs.n_floor_violations,
        ))
    if inputs.n_bids is not None and inputs.n_traces_emitted is not None:
        checks.append(check_decision_trace_emission(
            inputs.n_bids, inputs.n_traces_emitted,
        ))
    if (
        inputs.n_users_active is not None
        and inputs.n_users_with_collapsed_identity_stability is not None
    ):
        checks.append(check_posterior_pathology(
            inputs.n_users_active,
            inputs.n_users_with_collapsed_identity_stability,
        ))
    if inputs.msprt_decision is not None:
        checks.append(check_msprt_lower_crossed(inputs.msprt_decision))
    if inputs.cmo_review_disposition is not None:
        checks.append(check_cmo_uncomfortable(inputs.cmo_review_disposition))
    if (
        inputs.n_creatives_in_rotation is not None
        and inputs.n_creatives_failed_spot_check is not None
    ):
        checks.append(check_metaphor_coherence_failed(
            inputs.n_creatives_in_rotation,
            inputs.n_creatives_failed_spot_check,
        ))
    if inputs.p99_latency_ms is not None:
        checks.append(check_bid_time_latency_p99(
            p99_latency_ms=inputs.p99_latency_ms,
            stackadapt_budget_ms=inputs.stackadapt_budget_ms,
        ))

    # Sapid round-trip — pull from Phase 8 monitor when not provided.
    sapid_rate = inputs.sapid_round_trip_rate
    monitor_total_events = 0
    try:
        from adam.intelligence.spine.phase_8_stackadapt_integration import (
            get_default_monitor,
        )
        monitor = get_default_monitor()
        monitor_total_events = (
            monitor.n_sapids_resolved + monitor.n_sapids_unresolved
        )
        if sapid_rate is None and monitor_total_events > 0:
            sapid_rate = monitor.round_trip_rate()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Sapid monitor read failed in runner: %s", exc)

    # Append the sapid check when we have either an explicit rate OR
    # at least one real event in the monitor. Otherwise skip — not yet
    # evaluable.
    if inputs.sapid_round_trip_rate is not None:
        checks.append(check_sapid_round_trip(inputs.sapid_round_trip_rate))
    elif sapid_rate is not None and monitor_total_events > 0:
        checks.append(check_sapid_round_trip(sapid_rate))

    return evaluate_launch_gate(checks)


# =============================================================================
# Phase progression (SOFT_10 → RAMP_50 → FULL_100)
# =============================================================================


@dataclass(frozen=True)
class PhaseTransitionDecision:
    """Decision on whether to advance from current phase."""

    current_phase: LaunchPhase
    proposed_next_phase: LaunchPhase
    decision_is_advance: bool
    blocking_criteria: List[REDCriterion] = field(default_factory=list)
    rationale: str = ""


def should_advance_phase(
    current_phase: LaunchPhase,
    gate_result: LaunchGateResult,
    *,
    days_in_current_phase: float = 0.0,
) -> PhaseTransitionDecision:
    """Decide whether to advance from the current launch phase.

    Per directive Section 9 Phase 10:
        SOFT_10 → RAMP_50: after first week if no RED-criterion fires
        RAMP_50 → FULL_100: after second week if no RED-criterion fires
        Any RED-criterion → DEFERRED (regardless of phase)

    Returns PhaseTransitionDecision with proposed next phase + rationale.
    """
    # Any RED-criterion → DEFERRED, no matter what phase
    if gate_result.any_triggered:
        return PhaseTransitionDecision(
            current_phase=current_phase,
            proposed_next_phase=LaunchPhase.DEFERRED,
            decision_is_advance=False,
            blocking_criteria=list(gate_result.triggered_criteria),
            rationale=(
                f"{len(gate_result.triggered_criteria)} RED-criteria "
                f"triggered: "
                f"{', '.join(c.value for c in gate_result.triggered_criteria)}"
            ),
        )

    # No RED-criterion: advance per phase progression
    if current_phase == LaunchPhase.PRE_LAUNCH:
        return PhaseTransitionDecision(
            current_phase=current_phase,
            proposed_next_phase=LaunchPhase.SOFT_10,
            decision_is_advance=True,
            rationale="All RED gates GREEN; entering soft launch",
        )

    if current_phase == LaunchPhase.SOFT_10:
        if days_in_current_phase >= 7.0:
            return PhaseTransitionDecision(
                current_phase=current_phase,
                proposed_next_phase=LaunchPhase.RAMP_50,
                decision_is_advance=True,
                rationale="Soft launch week 1 complete; ramping to 50%",
            )
        return PhaseTransitionDecision(
            current_phase=current_phase,
            proposed_next_phase=LaunchPhase.SOFT_10,
            decision_is_advance=False,
            rationale=(
                f"Soft launch in progress (day {days_in_current_phase:.1f} "
                f"of 7); continue monitoring"
            ),
        )

    if current_phase == LaunchPhase.RAMP_50:
        if days_in_current_phase >= 7.0:
            return PhaseTransitionDecision(
                current_phase=current_phase,
                proposed_next_phase=LaunchPhase.FULL_100,
                decision_is_advance=True,
                rationale="50% ramp week complete; advancing to full launch",
            )
        return PhaseTransitionDecision(
            current_phase=current_phase,
            proposed_next_phase=LaunchPhase.RAMP_50,
            decision_is_advance=False,
            rationale=(
                f"50% ramp in progress (day {days_in_current_phase:.1f} "
                f"of 7); continue monitoring"
            ),
        )

    if current_phase == LaunchPhase.FULL_100:
        return PhaseTransitionDecision(
            current_phase=current_phase,
            proposed_next_phase=LaunchPhase.FULL_100,
            decision_is_advance=False,
            rationale="Full launch active; no further phase progression",
        )

    if current_phase == LaunchPhase.DEFERRED:
        return PhaseTransitionDecision(
            current_phase=current_phase,
            proposed_next_phase=LaunchPhase.DEFERRED,
            decision_is_advance=False,
            rationale=(
                "Launch deferred; resolve blocking RED-criteria before "
                "re-evaluating"
            ),
        )

    # Unknown phase
    raise ValueError(f"Unknown launch phase: {current_phase}")


__all__ = [
    "CriterionCheck",
    "LaunchGateResult",
    "LaunchPhase",
    "PhaseTransitionDecision",
    "REDCriterion",
    "RED_BID_TIME_LATENCY_P99_OVER_BUDGET_MS_MAX",
    "RED_DECISION_TRACE_EMISSION_RATE_MIN",
    "RED_FLUENCY_FLOOR_VIOLATION_RATE_MAX",
    "RED_IDENTITY_STABILITY_COLLAPSE_FRACTION_MAX",
    "RED_SAPID_ROUND_TRIP_RATE_MIN",
    "check_bid_time_latency_p99",
    "check_cmo_uncomfortable",
    "check_decision_trace_emission",
    "check_fluency_floor_violation",
    "check_metaphor_coherence_failed",
    "check_msprt_lower_crossed",
    "check_posterior_pathology",
    "check_sapid_round_trip",
    "evaluate_launch_gate",
    "LaunchGateInputs",
    "run_launch_gate_evaluation",
    "should_advance_phase",
]
