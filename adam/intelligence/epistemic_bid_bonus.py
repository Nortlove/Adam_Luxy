# =============================================================================
# Spine #8 — Active-Inference Epistemic-Value Bid Bonus (Dual Control)
# Location: adam/intelligence/epistemic_bid_bonus.py
# =============================================================================
"""Closed-form epistemic-value bid bonus for the dual-control bidder.

Closes directive Spine #8 (lines 273-293) + Phase 4 deliverable line
1016-1020:

    "Active-inference epistemic-value bid bonus (Spine #8):
       - Closed-form information gain under BONG.
       - Decay-with-precision weighting.
       - Cap as fraction of cohort daily budget.
       - Conditioned on fluency-floor pass."

WHY THIS EXISTS
---------------

The directive's diagnosis (line 277): "Industry programmatic bids on
expected reward only. ADAM is running an N-of-1 trial on every
recurring user; learning is part of the objective. Without explicit
dual-control formulation, the policy gets stuck exploit-only on users
with noisy posteriors and never transitions to confident exploitation."

Dual-control bidding splits the bid value into pragmatic + epistemic:

    bid_value(a | i, c) = pragmatic(a | i, c) + epistemic(a | i, c)
    epistemic(a | i, c) = w_epistemic · E[information_gain]

Where w_epistemic decays with the user's posterior precision — a
high-information user gets near-zero epistemic bonus (we already know
them), a low-information user gets a meaningful bonus (we pay a
small premium for impressions that *teach* us about them).

CLOSED-FORM INFORMATION GAIN UNDER BONG
---------------------------------------

Per directive line 287: "Under BONG natural-gradient updates, the
expected information gain per observation is computable in closed
form from the candidate Fisher matrix update. No heavy MC integration
needed at decision time."

For BONG's natural-parameter representation with diagonal precision D
and additive update D' = D + τ (where τ is observation precision):

    posterior_var_per_dim_pre  = 1 / D[i]
    posterior_var_per_dim_post = 1 / (D[i] + τ[i])
    EIG_per_dim = 0.5 * log((D[i] + τ[i]) / D[i])
                = 0.5 * log(1 + τ[i] / D[i])
    EIG_total   = sum over i of EIG_per_dim

Derivation: KL(N(μ', Σ') || N(μ, Σ)) for matched means and diagonal
covariances reduces to 0.5 * sum_i [log(σ²_pre / σ²_post) + σ²_post/σ²_pre - 1].
For our update where the mean is conditionally unchanged on the prior
and only precision grows, the closed form simplifies to the
log-determinant ratio above.

This is O(d), not O(d³) — matches the BONG update's complexity.
The low-rank U component of BONG's precision (D + UU^T) is ignored
in this closed form per the directive's "diagonal-only first" pattern;
full Woodbury-corrected EIG is a sibling slice.

COMPOSITION CHAIN
-----------------

    fluency_floor.passes_fluency_floor(creative, page) -> verdict
            ↓ (only if verdict.passed)
    epistemic_bid_bonus.compute_epistemic_bonus(
        individual=BONGPosterior, observation_precision,
        fluency_passed=True, cohort_daily_budget=...)
            ↓
    EpistemicBonusResult(bonus, info_gain, weight, capped, rationale)
            ↓
    [bidder] bid_value = pragmatic + bonus.bonus

Per directive line 220 (safeguard against epistemic-value gaming):
"the epistemic bonus is multiplied by an indicator that the candidate
has already passed the Spine #4 fluency floor. Reactance prevention
is structural, not voluntary." The fluency_passed gate is hard, not
a multiplier — when False, bonus is exactly 0.0.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations:
    - Closed-form EIG for diagonal-precision MVN under additive
      precision update: standard result from Bayesian sequential
      design (DeGroot 1962, Lindley 1956). The natural-parameter
      formulation matches BONG's update exactly (Jones, Chang,
      Murphy NeurIPS 2024).
    - Dual-control framing: Feldbaum 1960 (canonical optimal-
      control result; directive's named precedent line 277).
      Active inference operationalization: Friston et al. (Expected
      Free Energy as policy objective); Da Costa et al. 2020.
    - Fluency-floor safeguard: directive Spine #5 line 220
      (anti-gaming structural constraint).

(b) Tests pin: EIG monotonic in observation precision; EIG monotonic
    decreasing in posterior precision (more info → less new info);
    zero observation precision → zero EIG; bonus=0 when
    fluency_passed=False (hard gate); bonus capped at
    cohort_daily_budget * cap_fraction; epistemic_weight decays
    with posterior precision; numerical guards on extreme values;
    EpistemicBonusResult shape.

(c) calibration_pending=True. Decay constants are conservative
    pre-pilot defaults; LUXY pilot data will calibrate
    DEFAULT_W_MAX, DEFAULT_PRECISION_DECAY_SCALE,
    DEFAULT_COHORT_BUDGET_CAP_FRACTION against actual epistemic-
    pragmatic balance observed in N-of-1 trials. A14 flag:
    SPINE_8_EPISTEMIC_BONUS_DEFAULTS_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Full Woodbury-corrected EIG including BONG's low-rank U
      component (D + UU^T precision rather than D-only). The closed
      form here uses the diagonal approximation; full Woodbury is
      a sibling slice. The diagonal approximation is conservative:
      it underestimates EIG when U is significant, which biases the
      bonus DOWN — safer default than overestimating.
    * Cohort-specific daily budget. Spine #7 (cohort discovery) is
      BLOCKED on Loop B per the session handoff. We accept a
      cohort_daily_budget parameter; when None, no cap is applied.
      Calibration will land once cohorts ship.
    * Pragmatic-component computation (Kelly-edge × posterior on
      conversion under chosen mechanism). That's Spine #9 territory
      — the dual-control sum bid_value = pragmatic + epistemic
      composes once Spine #9 ships.
    * Wiring into the cascade producer. The DecisionTrace
      AlternativeCandidate.epistemic_bonus field (schema slot from
      ca03336) is the consumer slot; the producer wiring that
      populates it is its own slice — composes with the cascade
      producer (ab10f26) once we have a typed bid composer.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Optional, Union

import numpy as np

from adam.intelligence.bong import BONGPosterior, MIN_PRECISION

logger = logging.getLogger(__name__)


# =============================================================================
# A14 calibration-pending defaults
# =============================================================================

# A14 SPINE_8_EPISTEMIC_BONUS_DEFAULTS_PILOT_PENDING
#
# Conservative pre-pilot bands. LUXY pilot will calibrate the
# epistemic-vs-pragmatic balance observed in N-of-1 trials.

DEFAULT_W_MAX: float = 1.0
"""Maximum epistemic weight at zero posterior precision (cold-start
user). When the user's posterior is fully diffuse, the bonus is
weighted by w_max * EIG. Pilot calibration may scale this against
typical pragmatic values to balance the dual-control objective."""

DEFAULT_PRECISION_DECAY_SCALE: float = 10.0
"""Decay scale for w_epistemic. With sigmoid-style decay
``w = w_max / (1 + posterior_precision_total / scale)``, a
posterior_precision_total = 10 cuts w_epistemic in half."""

DEFAULT_COHORT_BUDGET_CAP_FRACTION: float = 0.10
"""Per directive line 291: 'bounded as a fraction of total bid
budget per cohort per day'. Default 10% — caller may override."""

# Numerical guards
_MIN_OBS_PRECISION_FOR_EIG: float = 1e-12


# =============================================================================
# Result type
# =============================================================================


@dataclass(frozen=True)
class EpistemicBonusResult:
    """Outcome of one epistemic-bonus computation.

    ``bonus``: the final value to add to pragmatic in the bid.
    ``info_gain``: the closed-form EIG (in nats) under BONG.
    ``weight``: the precision-decayed w_epistemic applied.
    ``capped``: True iff the bonus was clipped to the cohort budget
        cap. ``rationale`` then documents the pre-cap value.
    ``rationale``: short label for diagnostic / dashboard surfaces.
        Examples: "computed", "blocked_by_fluency_floor",
        "capped_to_cohort_budget", "zero_observation_precision".
    """

    bonus: float
    info_gain: float
    weight: float
    capped: bool
    rationale: str


# =============================================================================
# Closed-form information gain
# =============================================================================


def expected_information_gain(
    individual: BONGPosterior,
    observation_precision: Union[float, np.ndarray],
) -> float:
    """Closed-form EIG (in nats) under BONG's additive update.

    EIG_per_dim = 0.5 * log(1 + obs_precision[i] / D[i])
    EIG_total = sum across dims

    Args:
        individual: BONGPosterior with diagonal precision ``D``.
        observation_precision: scalar τ (broadcast to all dims) OR
            shape-(d,) per-dim observation precisions. Negative or
            non-finite values are floored to 0 with a debug log.

    Returns:
        EIG in nats (always ≥ 0). Use Math.log2 conversion downstream
        if bits are preferred.

    Soft-fail: when individual.D contains pathologically small values
    (below MIN_PRECISION), they are floored to MIN_PRECISION before
    the log to avoid log(very-large-number) instability.
    """
    D = np.asarray(individual.D, dtype=np.float64)
    D_safe = np.maximum(D, MIN_PRECISION)

    if isinstance(observation_precision, np.ndarray):
        tau = np.asarray(observation_precision, dtype=np.float64)
        if tau.shape != D.shape:
            logger.debug(
                "expected_information_gain: tau shape %s != D shape %s; "
                "broadcasting if possible.", tau.shape, D.shape,
            )
        tau = np.where(np.isfinite(tau), tau, 0.0)
        tau = np.maximum(tau, 0.0)
    else:
        tau_scalar = float(observation_precision)
        if not math.isfinite(tau_scalar) or tau_scalar < 0.0:
            tau_scalar = 0.0
        tau = np.full_like(D_safe, tau_scalar)

    # Per-dim EIG = 0.5 * log((D + τ) / D) = 0.5 * log1p(τ/D)
    ratio = tau / D_safe
    # log1p is numerically stable for small τ/D.
    eig_per_dim = 0.5 * np.log1p(ratio)
    eig_total = float(eig_per_dim.sum())

    # EIG must be non-negative; small numerical noise → floor at 0.
    if eig_total < 0.0:
        eig_total = 0.0
    return eig_total


# =============================================================================
# Precision-decayed weight
# =============================================================================


def epistemic_weight_from_precision(
    individual: BONGPosterior,
    *,
    w_max: float = DEFAULT_W_MAX,
    decay_scale: float = DEFAULT_PRECISION_DECAY_SCALE,
) -> float:
    """w_epistemic decays as the user's posterior precision grows.

    Per directive line 285: "high-information users get low epistemic
    bonus." Sigmoid-style decay:

        posterior_precision_total = sum(D)
        w_epistemic = w_max / (1 + posterior_precision_total / decay_scale)

    Properties:
      - At posterior_precision_total = 0:        w_epistemic = w_max
      - At posterior_precision_total = decay:    w_epistemic = w_max / 2
      - As posterior_precision_total → ∞:        w_epistemic → 0
      - Always in [0, w_max]; never negative; smooth.

    Numerical guards: D values below MIN_PRECISION floored before sum;
    decay_scale ≤ 0 falls back to DEFAULT_PRECISION_DECAY_SCALE.
    """
    if decay_scale <= 0.0:
        logger.debug(
            "epistemic_weight_from_precision: invalid decay_scale=%s, "
            "using default %s", decay_scale, DEFAULT_PRECISION_DECAY_SCALE,
        )
        decay_scale = DEFAULT_PRECISION_DECAY_SCALE

    D = np.asarray(individual.D, dtype=np.float64)
    D_safe = np.maximum(D, MIN_PRECISION)
    posterior_precision_total = float(D_safe.sum())

    weight = w_max / (1.0 + posterior_precision_total / decay_scale)
    # Clip just in case w_max is negative — defensive.
    if weight < 0.0:
        weight = 0.0
    return weight


# =============================================================================
# Composed bonus
# =============================================================================


def compute_epistemic_bonus(
    individual: BONGPosterior,
    observation_precision: Union[float, np.ndarray],
    *,
    fluency_passed: bool = True,
    w_max: float = DEFAULT_W_MAX,
    decay_scale: float = DEFAULT_PRECISION_DECAY_SCALE,
    cohort_daily_budget: Optional[float] = None,
    cohort_budget_cap_fraction: float = DEFAULT_COHORT_BUDGET_CAP_FRACTION,
) -> EpistemicBonusResult:
    """Compose the dual-control epistemic bonus for one candidate.

    Pipeline:
      1. fluency_passed=False → bonus 0.0 with rationale
         "blocked_by_fluency_floor". Hard gate (directive line 220
         + 289). The system cannot rationalize incompatible contexts
         as exploration.
      2. info_gain = expected_information_gain(individual, obs_prec)
      3. weight   = epistemic_weight_from_precision(individual,
                       w_max=w_max, decay_scale=decay_scale)
      4. raw_bonus = weight * info_gain
      5. If cohort_daily_budget is not None:
           cap = cohort_daily_budget * cohort_budget_cap_fraction
           bonus = min(raw_bonus, cap)
           capped = (raw_bonus > cap)
         else: bonus = raw_bonus, capped = False
    """
    # Stage 1: fluency-floor hard gate
    if not fluency_passed:
        return EpistemicBonusResult(
            bonus=0.0,
            info_gain=0.0,
            weight=0.0,
            capped=False,
            rationale="blocked_by_fluency_floor",
        )

    # Stage 2-3: info gain + weight
    info_gain = expected_information_gain(individual, observation_precision)
    weight = epistemic_weight_from_precision(
        individual, w_max=w_max, decay_scale=decay_scale,
    )

    # Edge: zero info gain → zero bonus (cannot teach us anything).
    if info_gain <= _MIN_OBS_PRECISION_FOR_EIG:
        return EpistemicBonusResult(
            bonus=0.0,
            info_gain=info_gain,
            weight=weight,
            capped=False,
            rationale="zero_information_gain",
        )

    # Stage 4: raw bonus
    raw_bonus = weight * info_gain

    # Stage 5: cohort cap
    if cohort_daily_budget is not None and cohort_daily_budget > 0.0:
        cap = float(cohort_daily_budget) * float(cohort_budget_cap_fraction)
        if raw_bonus > cap:
            return EpistemicBonusResult(
                bonus=cap,
                info_gain=info_gain,
                weight=weight,
                capped=True,
                rationale="capped_to_cohort_budget",
            )

    return EpistemicBonusResult(
        bonus=raw_bonus,
        info_gain=info_gain,
        weight=weight,
        capped=False,
        rationale="computed",
    )
