# =============================================================================
# ADAM Spine #8 — Active-Inference Epistemic-Value Bid Bonus (Dual Control)
# Location: adam/intelligence/spine/spine_8_epistemic_bonus.py
# =============================================================================

"""Active-inference epistemic-value bid bonus — dual-control completion.

PER DIRECTIVE SECTION 2 (Spine #8).

The bid value for an impression is the sum of:
    (a) expected pragmatic utility (Kelly-edge × posterior on conversion
        under chosen mechanism)
    (b) expected epistemic value (information gain about the user's
        posterior under chosen mechanism, weighted by posterior precision)

On low-information users, the epistemic term dominates — the system
pays a small premium for impressions that *teach it about the user*,
even at zero pragmatic edge.

WHY THIS IS SPINE — pair to Spine #5 (free-energy)

Per directive: "Industry programmatic bids on expected reward only.
ADAM is running an N-of-1 trial on every recurring user; learning is
part of the objective. Without explicit dual-control formulation, the
policy gets stuck exploit-only on users with noisy posteriors and
never transitions to confident exploitation. Dual control is a 50-year-
old result from optimal control (Feldbaum 1960); active inference
operationalizes it cleanly."

Spine #5 (free-energy) is the EXPLOITATION direction (blend with goal,
fulfill it). Spine #8 (epistemic) is the EXPLORATION direction (learn
about the user). Together they form the complete dual-control policy.

THE MATH (per directive Section 2 Spine #8 + Section 3.2)

    bid_value(a | i, c) = pragmatic(a | i, c) + epistemic(a | i, c)
    pragmatic(a | i, c) = E[reward | a, i, c] · pacing_modifier
    epistemic(a | i, c) = w_epistemic · E[information_gain(posterior_i | a, c)]

w_epistemic decays with the user's posterior precision. High-information
users (tight posterior) get LOW epistemic bonus (no need to learn more).
Low-information users (wide posterior) get HIGH epistemic bonus (high
expected information gain per observation).

Under BONG natural-gradient updates, expected information gain per
observation is computable in closed form from the candidate Fisher
matrix update — no heavy MC integration needed at decision time.

CONSTRAINED BY FLUENCY FLOOR (Spine #4)

Per directive Section 5: "the epistemic bonus is multiplied by an
indicator that the candidate has already passed the Spine #4 fluency
floor. Reactance prevention is structural, not voluntary."

The system cannot rationalize incompatible contexts as "exploration."
Foundation §7 rule 11 protected.

CAPPED BY PACING

Per directive: "the epistemic bonus is bounded as a fraction of total
bid budget per cohort per day, to prevent the system from spending the
campaign on exploration during a regime change."

DECISION-TIME CONSUMERS (Rule A check)

  - Spine #9 (Kelly-fraction bid sizing) reads epistemic + pragmatic
    to compute the final bid value
  - Spine #6 DecisionTrace records the epistemic_bonus per candidate
  - The orchestrator's bid layer composes pragmatic + epistemic

Cognitive primitive at the serving path. NOT measurement.

THIS COMMIT SHIPS

    - compute_information_gain_under_bong: closed-form info gain
      under BONG natural-gradient update for a candidate feature vector
    - epistemic_weight_from_precision: decay-with-precision weighting
    - compute_epistemic_bonus: full epistemic value per candidate,
      conditioned on fluency-floor pass (Rule A enforcement)
    - cap_epistemic_by_pacing: bound epistemic bonus to a fraction of
      cohort daily budget
    - compose_dual_control_bid: pragmatic + epistemic combination

REFERENCES

    Feldbaum 1960 — Dual control theory.
    Friston et al. — Expected Free Energy as policy objective.
    Da Costa et al. 2020 — Active inference on discrete state-spaces.
    Jones, Chang & Murphy 2024 — BONG (closed-form Fisher under natural
        gradient).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration constants
# =============================================================================


# Epistemic bonus base weight. Pilot-pending; calibrated to LUXY's
# expected pragmatic/epistemic ratio at small N.
DEFAULT_EPISTEMIC_BASE_WEIGHT: float = 1.0


# Precision threshold below which the epistemic bonus is at full weight,
# above which it decays. This implements "high-information users get
# low epistemic bonus" per directive Section 2 Spine #8.
DEFAULT_PRECISION_DECAY_THRESHOLD: float = 5.0


# Default cap on epistemic bonus as a fraction of cohort daily budget.
# Per directive: "to prevent the system from spending the campaign on
# exploration during a regime change."
DEFAULT_EPISTEMIC_BUDGET_FRACTION: float = 0.2


# =============================================================================
# Information gain under BONG (closed-form)
# =============================================================================


def compute_information_gain_under_bong(
    feature_vector: List[float],
    current_posterior_precision_diag: List[float],
    *,
    likelihood_weight: float = 1.0,
) -> float:
    """Compute expected information gain under a BONG single-step update.

    Per Jones, Chang & Murphy 2024: the BONG natural-gradient update
    adds w · x xᵀ to the precision matrix Λ, where x is the feature
    vector and w is the likelihood weight.

    Expected information gain per observation in closed form
    (Lindley 1956 reformulation under natural-parameter updates):
        IG(x) ≈ 0.5 · log( det(Λ_new) / det(Λ_old) )
              ≈ 0.5 · sum_i log( 1 + w · x_i² / Λ_ii )

    Approximation: uses diagonal precision (sufficient for the
    decision-time substrate; full-covariance update is in the Spine #1
    BONG step but for IG we approximate via the diagonal — the
    conservative estimate).

    Returns expected log-bits gain for one observation. Higher = more
    informative for the user posterior.

    For zero-feature vectors, returns 0 (no update → no info gain).
    """
    if len(feature_vector) != len(current_posterior_precision_diag):
        raise ValueError(
            f"feature_vector and precision_diag must have same length; "
            f"got {len(feature_vector)} vs "
            f"{len(current_posterior_precision_diag)}"
        )
    if likelihood_weight < 0.0:
        raise ValueError(
            f"likelihood_weight must be non-negative; got {likelihood_weight}"
        )

    info_gain = 0.0
    for i, (x_i, lambda_i) in enumerate(
        zip(feature_vector, current_posterior_precision_diag)
    ):
        if x_i == 0.0:
            continue
        if lambda_i <= 0.0:
            # Degenerate diagonal precision — skip this dim.
            continue
        # log(1 + w · x² / λ)
        info_gain += 0.5 * math.log1p(
            likelihood_weight * (x_i * x_i) / lambda_i
        )
    return info_gain


# =============================================================================
# Epistemic weight from posterior precision
# =============================================================================


def epistemic_weight_from_precision(
    posterior_precision_summary: float,
    *,
    base_weight: float = DEFAULT_EPISTEMIC_BASE_WEIGHT,
    decay_threshold: float = DEFAULT_PRECISION_DECAY_THRESHOLD,
) -> float:
    """Compute epistemic-bonus weight from posterior precision summary.

    Per directive: "w_epistemic decays with the user's posterior
    precision: high-information users get low epistemic bonus."

    Decay rule (interim heuristic; calibration-pending):
        w = base_weight · max(0, 1 - precision / decay_threshold)

    For precision = 0 (uniformative prior): w = base_weight (full bonus).
    For precision >= decay_threshold: w = 0 (no bonus; user is well-known).

    The posterior_precision_summary is a scalar — typically the trace
    of the posterior precision matrix or a similar summary; the
    orchestrator computes it from Spine #1 UserPosterior.
    """
    if posterior_precision_summary < 0.0:
        raise ValueError(
            f"posterior_precision_summary must be non-negative; "
            f"got {posterior_precision_summary}"
        )
    if base_weight < 0.0:
        raise ValueError(f"base_weight must be non-negative; got {base_weight}")
    if decay_threshold <= 0.0:
        raise ValueError(
            f"decay_threshold must be positive; got {decay_threshold}"
        )

    weight = base_weight * max(
        0.0, 1.0 - posterior_precision_summary / decay_threshold,
    )
    return weight


# =============================================================================
# Compute epistemic bonus per candidate
# =============================================================================


@dataclass(frozen=True)
class EpistemicBonusResult:
    """Result of an epistemic-bonus computation.

    Decomposed for the DecisionTrace + partner-facing render.
    """

    candidate_mechanism: str
    info_gain: float
    epistemic_weight: float
    raw_bonus: float          # info_gain · epistemic_weight (pre-floor)
    fluency_floor_passed: bool
    bonus: float              # 0.0 when floor failed; else raw_bonus


def compute_epistemic_bonus(
    candidate_mechanism: str,
    feature_vector: List[float],
    current_posterior_precision_diag: List[float],
    posterior_precision_summary: float,
    *,
    fluency_floor_passed: bool,
    likelihood_weight: float = 1.0,
    base_weight: float = DEFAULT_EPISTEMIC_BASE_WEIGHT,
    decay_threshold: float = DEFAULT_PRECISION_DECAY_THRESHOLD,
) -> EpistemicBonusResult:
    """Compute the epistemic bonus for one candidate.

    Per directive Section 5 + Spine #8:
        epistemic(a) = w_epistemic · E[information_gain(posterior_i | a, c)]

    CONDITIONED ON FLUENCY FLOOR PASS. When fluency_floor_passed is
    False, the bonus is forced to 0.0 — the system cannot rationalize
    incompatible contexts as "exploration." Foundation §7 rule 11
    protected structurally.

    Returns EpistemicBonusResult with structured decomposition for
    the DecisionTrace + partner render.
    """
    info_gain = compute_information_gain_under_bong(
        feature_vector=feature_vector,
        current_posterior_precision_diag=current_posterior_precision_diag,
        likelihood_weight=likelihood_weight,
    )
    weight = epistemic_weight_from_precision(
        posterior_precision_summary,
        base_weight=base_weight,
        decay_threshold=decay_threshold,
    )
    raw = info_gain * weight

    bonus = raw if fluency_floor_passed else 0.0

    return EpistemicBonusResult(
        candidate_mechanism=candidate_mechanism,
        info_gain=info_gain,
        epistemic_weight=weight,
        raw_bonus=raw,
        fluency_floor_passed=fluency_floor_passed,
        bonus=bonus,
    )


# =============================================================================
# Pacing cap on epistemic spend
# =============================================================================


def cap_epistemic_by_pacing(
    epistemic_bonuses: List[EpistemicBonusResult],
    cohort_daily_budget: float,
    *,
    epistemic_budget_fraction: float = DEFAULT_EPISTEMIC_BUDGET_FRACTION,
) -> List[EpistemicBonusResult]:
    """Cap the epistemic bonuses so the cohort's daily epistemic spend
    does not exceed `epistemic_budget_fraction` of the cohort daily budget.

    Per directive: "the epistemic bonus is bounded as a fraction of
    total bid budget per cohort per day, to prevent the system from
    spending the campaign on exploration during a regime change."

    Implementation: if the sum of bonuses exceeds the cap, scale all
    bonuses proportionally so the sum equals the cap. Preserves the
    relative ranking of candidates.

    Returns a new list of EpistemicBonusResult with possibly-scaled
    bonuses.
    """
    if cohort_daily_budget <= 0.0:
        # No budget → no epistemic spend allowed.
        return [
            EpistemicBonusResult(
                candidate_mechanism=b.candidate_mechanism,
                info_gain=b.info_gain,
                epistemic_weight=b.epistemic_weight,
                raw_bonus=b.raw_bonus,
                fluency_floor_passed=b.fluency_floor_passed,
                bonus=0.0,
            )
            for b in epistemic_bonuses
        ]
    if not 0.0 <= epistemic_budget_fraction <= 1.0:
        raise ValueError(
            f"epistemic_budget_fraction must be in [0, 1]; got "
            f"{epistemic_budget_fraction}"
        )

    cap = cohort_daily_budget * epistemic_budget_fraction
    total = sum(b.bonus for b in epistemic_bonuses)
    if total <= cap:
        return list(epistemic_bonuses)

    scale = cap / total if total > 0 else 0.0
    return [
        EpistemicBonusResult(
            candidate_mechanism=b.candidate_mechanism,
            info_gain=b.info_gain,
            epistemic_weight=b.epistemic_weight,
            raw_bonus=b.raw_bonus,
            fluency_floor_passed=b.fluency_floor_passed,
            bonus=b.bonus * scale,
        )
        for b in epistemic_bonuses
    ]


# =============================================================================
# Dual-control bid composition
# =============================================================================


@dataclass(frozen=True)
class DualControlBid:
    """Pragmatic + epistemic decomposition of a candidate's bid value.

    Read by Spine #9 Kelly-fraction sizing for the final bid value;
    recorded in Spine #6 DecisionTrace as the bid_value structured
    component.
    """

    candidate_mechanism: str
    pragmatic_value: float
    epistemic_bonus: float
    total_bid_value: float


def compose_dual_control_bid(
    candidate_mechanism: str,
    pragmatic_value: float,
    epistemic_bonus_result: EpistemicBonusResult,
) -> DualControlBid:
    """Compose pragmatic + epistemic into a structured DualControlBid.

    The orchestrator typically computes pragmatic_value as
    E[reward | candidate, user, context] · pacing_modifier from Spine
    #1 posterior + cohort policy from Spine #7. Spine #9 Kelly-fraction
    sizing reads the resulting DualControlBid's total_bid_value to
    compute the actual bid amount.
    """
    if epistemic_bonus_result.candidate_mechanism != candidate_mechanism:
        raise ValueError(
            f"epistemic_bonus_result.candidate_mechanism "
            f"({epistemic_bonus_result.candidate_mechanism}) does not "
            f"match candidate_mechanism ({candidate_mechanism})"
        )

    return DualControlBid(
        candidate_mechanism=candidate_mechanism,
        pragmatic_value=pragmatic_value,
        epistemic_bonus=epistemic_bonus_result.bonus,
        total_bid_value=pragmatic_value + epistemic_bonus_result.bonus,
    )


__all__ = [
    "DEFAULT_EPISTEMIC_BASE_WEIGHT",
    "DEFAULT_EPISTEMIC_BUDGET_FRACTION",
    "DEFAULT_PRECISION_DECAY_THRESHOLD",
    "DualControlBid",
    "EpistemicBonusResult",
    "cap_epistemic_by_pacing",
    "compose_dual_control_bid",
    "compute_epistemic_bonus",
    "compute_information_gain_under_bong",
    "epistemic_weight_from_precision",
]
