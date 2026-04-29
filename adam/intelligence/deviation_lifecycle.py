# =============================================================================
# ADAM C4 — HumanDeviation Lifecycle Service
# Location: adam/intelligence/deviation_lifecycle.py
# =============================================================================

"""Deviation lifecycle service — HMT §11.5 substrate.

PURPOSE

Every partner override of a system recommendation is a HYPOTHESIS at
write time about "the system was wrong here." Without a lifecycle that
adjudicates each override against post-horizon outcomes, overrides
remain anecdotal noise — Foundation §7 rule 11 (fitness function IS
the ethics) requires that the learning loop ingest override evidence
as causal signal, not just user testimony.

This module is the lifecycle:
    1. record_deviation         — capture the override + reason
    2. schedule_adjudication    — assign the horizon-end adjudication date
    3. is_adjudication_due      — check whether the horizon has elapsed
    4. adjudicate_deviation     — produce the verdict from observed outcome
    5. transition_state         — controlled state-machine transitions

The verdict (DeviationAdjudicationOutcome) flows back to the analytics
loop as a learning signal: CONFIRMED_OVERRIDE updates the system
posterior toward respecting the user's substitute; SYSTEM_VINDICATED
updates toward the original recommendation; FALSE_CORRECTION marks the
deviation as non-load-bearing (don't update on it). This loop closure
is the C2/C3/Defensive Reasoning prerequisite per the build roadmap
dependency graph.

A14 FLAG

Identifier:
    DEVIATION_PENDING_ADJUDICATION

Retirement trigger:
    Retire when (a) the deviation has been adjudicated with a verdict
    in {CONFIRMED_OVERRIDE, SYSTEM_VINDICATED, FALSE_CORRECTION}, AND
    (b) the verdict has been propagated to the analytics loop's
    learning state.

Until both conditions hold, every deviation carries the flag so the
agency dashboard can surface "5 deviations awaiting adjudication" as
a discipline-visible counter rather than buried operational state.

WIRING

`record_deviation` is the entry point at the partner-facing API where
overrides arrive. `adjudicate_deviation` is the entry point for the
nightly cron that walks deviations whose horizon has elapsed. The
service is library-free (depends only on dialogue_ledger.models +
prometheus metrics for A14 emission) so it ships shippable today
even before the partner-facing override UI is built.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from adam.intelligence.dialogue_ledger.models import (
    DeviationAdjudication,
    DeviationAdjudicationOutcome,
    DeviationLifecycleState,
    HumanDeviation,
)

logger = logging.getLogger(__name__)


# =============================================================================
# A14 flag constants
# =============================================================================


DEVIATION_PENDING_ADJUDICATION_FLAG: str = "DEVIATION_PENDING_ADJUDICATION"

DEVIATION_PENDING_RETIREMENT_TRIGGER: str = (
    "Retire DEVIATION_PENDING_ADJUDICATION on a per-deviation basis when "
    "(a) the deviation has been adjudicated with a verdict in "
    "{CONFIRMED_OVERRIDE, SYSTEM_VINDICATED, FALSE_CORRECTION}, AND "
    "(b) the verdict has been propagated to the analytics loop's "
    "learning state."
)


# =============================================================================
# Default horizons per domain class (HMT §9.2)
# =============================================================================


_DEFAULT_HORIZON_DAYS: Dict[str, int] = {
    # Ad-tech outcomes typically need ~30 days to surface conversion
    # signal; brand-equity proxy horizons are longer.
    "default": 30,
    "ad_conversion": 30,
    "brand_equity": 90,
    "creative_fit": 14,
    "channel_capacity": 21,
}


def horizon_for_domain(domain: str) -> int:
    """Return horizon in days for a domain. Falls back to default 30."""
    return _DEFAULT_HORIZON_DAYS.get(domain, _DEFAULT_HORIZON_DAYS["default"])


# =============================================================================
# Adjudication thresholds
# =============================================================================


@dataclass(frozen=True)
class AdjudicationThresholds:
    """Thresholds that gate adjudication outcome decisions.

    These are pilot-pending values — the A14 flag's retirement trigger
    references the moment these are pinned by ≥30 calibrated
    adjudications on real LUXY data. Until then, the defaults below
    are honest interim values, not claims of empirical calibration.
    """

    min_outcome_samples: int = 5
    confidence_for_verdict: float = 0.6
    min_relative_advantage: float = 0.05  # 5pp lift to break tie

    @classmethod
    def default(cls) -> "AdjudicationThresholds":
        return cls()


# =============================================================================
# Lifecycle state-machine transitions
# =============================================================================


# Valid forward transitions. Lifecycle is monotonic — no return arrows.
_VALID_TRANSITIONS: Dict[DeviationLifecycleState, set] = {
    DeviationLifecycleState.RECORDED: {
        DeviationLifecycleState.AWAITING_OUTCOME,
    },
    DeviationLifecycleState.AWAITING_OUTCOME: {
        DeviationLifecycleState.ADJUDICATED,
        DeviationLifecycleState.PENDING,
    },
    DeviationLifecycleState.PENDING: {
        DeviationLifecycleState.ADJUDICATED,
    },
    DeviationLifecycleState.ADJUDICATED: set(),  # terminal
}


class InvalidTransitionError(ValueError):
    """Raised when an attempted transition is not in _VALID_TRANSITIONS."""
    pass


def transition_state(
    deviation: HumanDeviation,
    new_state: DeviationLifecycleState,
) -> HumanDeviation:
    """Transition a HumanDeviation to a new lifecycle state.

    Returns a new HumanDeviation with updated state (Pydantic models
    are immutable by frozen-equivalent semantics here — we use
    model_copy to preserve the rest of the fields).

    Raises InvalidTransitionError when the transition is not in
    _VALID_TRANSITIONS.
    """
    current = deviation.lifecycle_state
    allowed = _VALID_TRANSITIONS.get(current, set())
    if new_state not in allowed:
        raise InvalidTransitionError(
            f"Invalid transition: {current.value} → {new_state.value} "
            f"(allowed from {current.value}: "
            f"{sorted(s.value for s in allowed)})"
        )
    return deviation.model_copy(update={"lifecycle_state": new_state})


# =============================================================================
# Lifecycle entry points
# =============================================================================


def schedule_adjudication(
    deviation: HumanDeviation,
    horizon_days: Optional[int] = None,
    now: Optional[datetime] = None,
) -> HumanDeviation:
    """Set the horizon_ends_at timestamp + transition to AWAITING_OUTCOME.

    Returns a new HumanDeviation with horizon_ends_at populated and
    lifecycle_state advanced. The horizon defaults to the per-domain
    value from `horizon_for_domain` when not specified.
    """
    if horizon_days is None:
        horizon_days = horizon_for_domain(deviation.domain)
    if horizon_days <= 0:
        raise ValueError(f"horizon_days must be positive; got {horizon_days}")

    base = now or datetime.now(timezone.utc)
    horizon_end = base + timedelta(days=horizon_days)

    advanced = transition_state(
        deviation, DeviationLifecycleState.AWAITING_OUTCOME,
    )
    return advanced.model_copy(update={"horizon_ends_at": horizon_end})


def is_adjudication_due(
    deviation: HumanDeviation,
    now: Optional[datetime] = None,
) -> bool:
    """Return True iff the deviation's horizon has elapsed.

    A deviation is "due" when its horizon_ends_at is in the past AND
    its lifecycle is in {AWAITING_OUTCOME, PENDING}.
    """
    if deviation.horizon_ends_at is None:
        return False
    if deviation.lifecycle_state not in {
        DeviationLifecycleState.AWAITING_OUTCOME,
        DeviationLifecycleState.PENDING,
    }:
        return False
    base = now or datetime.now(timezone.utc)
    return deviation.horizon_ends_at <= base


def is_pending_adjudication(deviation: HumanDeviation) -> bool:
    """Return True iff the deviation is in any non-terminal state."""
    return deviation.lifecycle_state != DeviationLifecycleState.ADJUDICATED


# =============================================================================
# Adjudication
# =============================================================================


def adjudicate_deviation(
    deviation: HumanDeviation,
    observed_outcome_for_recommendation: Optional[float],
    observed_outcome_for_substitute: Optional[float],
    n_samples: int,
    *,
    iteration: int = 0,
    adjudicator: str = "auto",
    thresholds: Optional[AdjudicationThresholds] = None,
    rationale_tag: Optional[str] = None,
    observed_outcome_summary: Optional[Dict[str, Any]] = None,
) -> DeviationAdjudication:
    """Produce a DeviationAdjudication verdict from observed outcomes.

    The adjudicator compares the observed outcome under the system's
    original recommendation against the observed outcome under the
    user's substitute. The thresholds gate the verdict:

        - If n_samples < min_outcome_samples: PENDING_INSUFFICIENT_DATA
        - If either outcome is None: PENDING_INSUFFICIENT_DATA
        - If |delta| / max(|sub|, |rec|, 1e-9) < min_relative_advantage:
              FALSE_CORRECTION (no causal signal between substitute and rec)
        - If substitute outperformed recommendation by ≥ relative threshold:
              CONFIRMED_OVERRIDE
        - If recommendation outperformed substitute:
              SYSTEM_VINDICATED

    Confidence is currently 1 - 1/n_samples for verdicts above the
    threshold; this is honest interim arithmetic, not empirically
    calibrated. The A14 flag's retirement trigger references the
    moment confidence is replaced with an empirical calibration.

    Args:
        deviation: the HumanDeviation to adjudicate
        observed_outcome_for_recommendation: realized outcome metric if
            the system's recommendation had been followed (counterfactual
            via M2 estimate or matched-cohort baseline). None when not
            estimable.
        observed_outcome_for_substitute: realized outcome metric for
            the user's actual substitute (factual). None when not
            measured.
        n_samples: count of outcomes underlying the comparison
        iteration: which adjudication attempt this is (0 for first)
        adjudicator: "auto" or a user_id of human reviewer
        thresholds: AdjudicationThresholds; defaults to .default()
        rationale_tag: optional templated reason; defaults to a derived tag
        observed_outcome_summary: optional structured summary for the record

    Returns DeviationAdjudication with the verdict.
    """
    th = thresholds or AdjudicationThresholds.default()
    summary = observed_outcome_summary or {}

    # Insufficient data check
    if (
        n_samples < th.min_outcome_samples
        or observed_outcome_for_recommendation is None
        or observed_outcome_for_substitute is None
    ):
        return DeviationAdjudication(
            deviation_id=deviation.id,
            outcome=DeviationAdjudicationOutcome.PENDING_INSUFFICIENT_DATA,
            iteration=iteration,
            observed_outcome_summary=summary,
            adjudicator=adjudicator,
            confidence=0.0,
            rationale_tag=rationale_tag or "insufficient_data",
        )

    delta = observed_outcome_for_substitute - observed_outcome_for_recommendation
    denom = max(
        abs(observed_outcome_for_substitute),
        abs(observed_outcome_for_recommendation),
        1e-9,
    )
    relative_advantage = abs(delta) / denom

    if relative_advantage < th.min_relative_advantage:
        outcome = DeviationAdjudicationOutcome.FALSE_CORRECTION
        rationale = rationale_tag or "no_signal"
    elif delta > 0:
        outcome = DeviationAdjudicationOutcome.CONFIRMED_OVERRIDE
        rationale = rationale_tag or "substitute_outperformed"
    else:
        outcome = DeviationAdjudicationOutcome.SYSTEM_VINDICATED
        rationale = rationale_tag or "recommendation_outperformed"

    confidence = max(0.0, min(1.0, 1.0 - 1.0 / max(n_samples, 1)))

    return DeviationAdjudication(
        deviation_id=deviation.id,
        outcome=outcome,
        iteration=iteration,
        observed_outcome_summary=summary,
        adjudicator=adjudicator,
        confidence=confidence,
        rationale_tag=rationale,
    )


# =============================================================================
# A14 flag emission
# =============================================================================


def record_deviation_a14_flag(
    deviation: HumanDeviation,
    atom_id: str = "deviation_lifecycle",
) -> List[str]:
    """Emit DEVIATION_PENDING_ADJUDICATION for non-terminal deviations.

    Increments the Prometheus a14_flag_active counter. Returns the
    list of flags applied. Empty list when the deviation is already
    in a terminal state.
    """
    flags: List[str] = []
    if is_pending_adjudication(deviation):
        flags.append(DEVIATION_PENDING_ADJUDICATION_FLAG)
        _increment_a14_counter(atom_id, DEVIATION_PENDING_ADJUDICATION_FLAG)
    return flags


def _increment_a14_counter(atom_id: str, flag: str) -> None:
    """Non-fatal Prometheus counter increment."""
    try:
        from adam.infrastructure.prometheus.metrics import get_metrics
        pm = get_metrics()
        pm.a14_flag_active.labels(atom_id=atom_id, a14_flag=flag).inc()
    except Exception as exc:
        logger.debug("Deviation A14 metric emission failed: %s", exc)


__all__ = [
    "AdjudicationThresholds",
    "DEVIATION_PENDING_ADJUDICATION_FLAG",
    "DEVIATION_PENDING_RETIREMENT_TRIGGER",
    "InvalidTransitionError",
    "adjudicate_deviation",
    "horizon_for_domain",
    "is_adjudication_due",
    "is_pending_adjudication",
    "record_deviation_a14_flag",
    "schedule_adjudication",
    "transition_state",
]
