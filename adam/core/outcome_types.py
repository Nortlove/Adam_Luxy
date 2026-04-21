"""
Canonical OutcomeType enum and reward semantics for the ADAM learning loop.

WHY THIS FILE EXISTS
====================

Before this module, five parallel `OutcomeType` enums existed across the
codebase (behavioral_analytics, bayesian_fusion, gradient_bridge, blackboard,
theory_based_simulator) and the main `OutcomeHandler.process_outcome()` took
an untyped `outcome_type: str` with no canonical vocabulary. This
fragmentation meant negative outcomes — refunds, complaints, regret signals,
long-horizon churn — could not be consistently represented, and no path in
the learning loop treated them as first-class.

The fitness function IS the ethics (Foundation §7 rule 11). Selection is
amoral. If the reward signal does not penalize backfire, regret, complaint,
refund, and churn, selection pressure will drive the system toward whatever
maximizes immediate conversion regardless of long-horizon damage. This
module defines the outcome vocabulary that makes the reward signal able to
receive those penalties.

DESIGN PRINCIPLES
=================

1. **Positive and negative outcomes are not mirror opposites.**
   A REFUND is a *reversal* of a binding event, not its absence.
   It carries stronger evidence against the decision than a plain SKIP.
   Magnitudes (below) reflect this.

2. **Delayed outcomes are first-class.**
   CHURN_30D is observed at horizon expiry (scheduled), not at impression
   time. The schema supports both immediate and horizon-resolved outcomes
   because the platform operates at three time-scales simultaneously
   (Foundation §2.5 — Bargh/Pinker/Dawkins).

3. **Structural gates are respected.**
   Negative outcomes do not bypass the decision-mode gate. A REFUND on an
   INCOMPLETE-chain decision is recorded as a causal observation but does
   not force posterior updates — the same structural filter applies as for
   positive outcomes. See `adam.core.decision_mode`.

4. **Processing depth weighting still applies.**
   An unprocessed impression that "refunds" carries less evidentiary weight
   than a deliberately engaged one. Processing depth weights stack on top
   of outcome magnitude.

5. **The existing five OutcomeType enums are not deleted yet.**
   Per the orientation document's "consolidation not construction" rule,
   the canonical enum here is the reference; the others should be migrated
   to import from here over time. This file is the source of truth.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Canonical enum
# =============================================================================


class OutcomeType(str, Enum):
    """Canonical outcome types for the ADAM learning loop.

    Three categories:

    - **Positive** — evidence that the decision's causal chain held.
      Increment alpha on the posterior.

    - **Neutral / non-engagement** — single observation against.
      Standard beta increment. The user did not engage, but there is
      no active evidence the decision was wrong; it may have been
      a poor-time delivery or low-processing-depth exposure.

    - **Negative (ethics-gate signals)** — evidence that the decision
      was actively wrong, produced backfire, or caused long-horizon
      damage. Magnitude-weighted beta increment. THIS IS THE GAP
      THAT PHASE 1 CLOSES.

    New outcome types should be added here first, with a
    corresponding entry in `_OUTCOME_SEMANTICS` below. No outcome
    type without semantics is accepted by the learning loop.
    """

    # Positive — evidence for
    CONVERSION = "conversion"
    CLICK = "click"
    ENGAGEMENT = "engagement"
    LISTEN_COMPLETE = "listen_complete"
    LISTEN_PARTIAL = "listen_partial"
    RETURN_VISIT = "return_visit"

    # Neutral / non-engagement — evidence against at weak magnitude
    SKIP = "skip"
    BOUNCE = "bounce"
    ABANDONMENT = "abandonment"
    NO_CONVERSION = "no_conversion"

    # Negative — the ethics-gate signals. These are what Phase 1 adds.
    REFUND = "refund"                  # Conversion reversed — strong negative
    COMPLAINT = "complaint"            # Explicit complaint — moderate-strong negative
    NEGATIVE_REVIEW = "negative_review"  # Post-purchase negative review — moderate
    REGRET_SIGNAL = "regret_signal"    # barrier_self_report indicates regret
    CHURN_30D = "churn_30d"            # No return within 30 days of conversion — delayed
    AD_FATIGUE = "ad_fatigue"          # Frequency-decay reactance threshold crossed


# =============================================================================
# Reward semantics per outcome type
# =============================================================================


@dataclass(frozen=True)
class OutcomeSemantics:
    """How an outcome type translates into a signed reward.

    Fields:
      reward_sign: +1.0 for positive outcomes, -1.0 for negative.
      magnitude: Evidentiary weight for the posterior update. Higher
        magnitudes mean this outcome should move posteriors more
        strongly than a baseline observation. The baseline is
        CONVERSION = 1.0; a REFUND at 3.0 says a refund is three
        times the evidence against that a conversion was for.
      label: Human-readable description used in logs and metrics.
      delayed: True for outcomes that require horizon-scheduled
        evaluation (CHURN_30D), False for synchronous outcomes.
    """

    reward_sign: float
    magnitude: float
    label: str
    delayed: bool = False


# Magnitudes are calibrated to the following reference points:
#   1.0 — a conversion (baseline positive evidence)
#   1.0 — a skip (baseline against — a non-engagement)
#   2.0–3.0 — a moderate-to-strong backfire signal
#
# These are initial values. They should be updated as empirical data
# accumulates on how strongly each signal predicts inversion of the
# original decision's correctness. See phase-1 verification plan.
_OUTCOME_SEMANTICS: dict[OutcomeType, OutcomeSemantics] = {
    # --- Positive ---
    OutcomeType.CONVERSION: OutcomeSemantics(+1.0, 1.0, "conversion"),
    OutcomeType.CLICK: OutcomeSemantics(+1.0, 0.3, "click (weaker evidence than conversion)"),
    OutcomeType.ENGAGEMENT: OutcomeSemantics(+1.0, 0.5, "deep engagement short of conversion"),
    OutcomeType.LISTEN_COMPLETE: OutcomeSemantics(+1.0, 0.7, "listened to completion"),
    OutcomeType.LISTEN_PARTIAL: OutcomeSemantics(+1.0, 0.3, "partial listen"),
    OutcomeType.RETURN_VISIT: OutcomeSemantics(+1.0, 0.5, "user returned (re-engagement)"),

    # --- Neutral / non-engagement ---
    OutcomeType.SKIP: OutcomeSemantics(-1.0, 1.0, "non-engagement / skip"),
    OutcomeType.BOUNCE: OutcomeSemantics(-1.0, 1.0, "bounce / short exposure"),
    OutcomeType.ABANDONMENT: OutcomeSemantics(-1.0, 1.0, "funnel abandonment before convert"),
    OutcomeType.NO_CONVERSION: OutcomeSemantics(-1.0, 1.0, "no conversion observed"),

    # --- Negative ethics-gate signals ---
    OutcomeType.REFUND: OutcomeSemantics(
        reward_sign=-1.0, magnitude=3.0,
        label="conversion reversed — strong evidence against",
    ),
    OutcomeType.COMPLAINT: OutcomeSemantics(
        reward_sign=-1.0, magnitude=2.0,
        label="explicit complaint — moderate-strong negative",
    ),
    OutcomeType.NEGATIVE_REVIEW: OutcomeSemantics(
        reward_sign=-1.0, magnitude=1.5,
        label="post-purchase negative review — moderate negative",
    ),
    OutcomeType.REGRET_SIGNAL: OutcomeSemantics(
        reward_sign=-1.0, magnitude=2.0,
        label="user-reported regret (barrier self-report)",
    ),
    OutcomeType.CHURN_30D: OutcomeSemantics(
        reward_sign=-1.0, magnitude=1.5,
        label="no return within 30 days — delayed backfire",
        delayed=True,
    ),
    OutcomeType.AD_FATIGUE: OutcomeSemantics(
        reward_sign=-1.0, magnitude=1.5,
        label="frequency-decay reactance threshold crossed",
    ),
}


# =============================================================================
# Public API
# =============================================================================


def resolve_outcome_type(raw: str) -> Optional[OutcomeType]:
    """Return the canonical OutcomeType for a raw string, or None if unknown.

    Unknown outcome types should be surfaced (metric + log) rather than
    silently coerced — a decision made here propagates into the learning
    loop's signed reward, and silent coercion of unknowns to SKIP would
    hide upstream telemetry bugs.
    """
    try:
        return OutcomeType(raw)
    except (ValueError, TypeError):
        return None


def get_semantics(outcome_type: OutcomeType) -> OutcomeSemantics:
    """Return the OutcomeSemantics for a canonical outcome type.

    Raises KeyError if the outcome type lacks semantics (indicates
    an enum was added without updating _OUTCOME_SEMANTICS). Callers
    should not catch this — a missing semantics entry is a
    programmer error that must be fixed in this module.
    """
    return _OUTCOME_SEMANTICS[outcome_type]


def compute_signed_reward(
    outcome_type: str,
    outcome_value: float = 1.0,
    processing_depth_weight: float = 1.0,
) -> float:
    """Compute the signed, magnitude-weighted reward for a learning update.

    Args:
        outcome_type: Raw outcome type string (e.g. "conversion", "refund").
        outcome_value: Intensity of the outcome, [0.0, 1.0]. For
            conversions this is typically 1.0; for engagement-like
            outcomes it may be fractional (e.g. scroll-depth ratio).
        processing_depth_weight: Enhancement #34 processing-depth
            observation weight [0.05, 1.0]. Unprocessed impressions
            (viewport < 1s) get 0.05 so their outcomes do not drive
            learning as strongly as deliberate engagements.

    Returns:
        A signed float:
          signed_reward > 0  →  evidence FOR the decision's chain.
                                Increment alpha by the magnitude.
          signed_reward < 0  →  evidence AGAINST the decision's chain.
                                Increment beta by |magnitude|.
          signed_reward == 0 →  unknown outcome type, no update.

    Examples:
        >>> compute_signed_reward("conversion", 1.0, 1.0)
        1.0
        >>> compute_signed_reward("refund", 1.0, 1.0)
        -3.0
        >>> compute_signed_reward("conversion", 1.0, 0.05)  # unprocessed
        0.05
        >>> compute_signed_reward("unknown_type", 1.0, 1.0)
        0.0
    """
    canonical = resolve_outcome_type(outcome_type)
    if canonical is None:
        logger.warning(
            "Unknown outcome_type=%r — no signed reward computed. "
            "Add to adam.core.outcome_types.OutcomeType if this is a new "
            "outcome class the learning loop should handle.",
            outcome_type,
        )
        return 0.0

    sem = _OUTCOME_SEMANTICS[canonical]
    return sem.reward_sign * sem.magnitude * outcome_value * processing_depth_weight


def is_positive_outcome(outcome_type: str) -> bool:
    """True if this outcome is evidence FOR the decision's chain.

    Provided for backward compatibility with the legacy boolean
    `success` variable in `OutcomeHandler.process_outcome`. Callers
    that compute `signed_reward` directly should use its sign
    instead.
    """
    canonical = resolve_outcome_type(outcome_type)
    if canonical is None:
        return False
    return _OUTCOME_SEMANTICS[canonical].reward_sign > 0


def is_negative_ethics_signal(outcome_type: str) -> bool:
    """True if this outcome is an ethics-gate negative signal —
    backfire, regret, complaint, refund, churn, ad-fatigue — as
    distinct from neutral non-engagement (skip, bounce).

    Used by metric emitters and logging to distinguish the two
    classes of "failure": a user who didn't click versus a user
    who actively signaled the decision was wrong.
    """
    return outcome_type in {
        OutcomeType.REFUND.value,
        OutcomeType.COMPLAINT.value,
        OutcomeType.NEGATIVE_REVIEW.value,
        OutcomeType.REGRET_SIGNAL.value,
        OutcomeType.CHURN_30D.value,
        OutcomeType.AD_FATIGUE.value,
    }


def is_delayed_outcome(outcome_type: str) -> bool:
    """True if this outcome requires horizon-scheduled evaluation
    rather than synchronous processing at impression time.

    CHURN_30D is the canonical example — it can only be observed
    after the horizon window closes with no return visit.
    """
    canonical = resolve_outcome_type(outcome_type)
    if canonical is None:
        return False
    return _OUTCOME_SEMANTICS[canonical].delayed


def all_outcome_labels() -> dict[str, str]:
    """Return a dict of every canonical outcome type and its human-
    readable label. Used by the settings panel and metric-label
    enumeration."""
    return {ot.value: sem.label for ot, sem in _OUTCOME_SEMANTICS.items()}
