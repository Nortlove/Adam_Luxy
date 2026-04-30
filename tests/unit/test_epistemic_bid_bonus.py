"""Pin Spine #8 — closed-form epistemic-value bid bonus.

Tests pin:
  * EIG monotonic in observation precision.
  * EIG monotonic decreasing in posterior precision (more information
    on the user → less new information available per observation).
  * Zero observation precision → zero EIG.
  * EIG matches the closed-form 0.5 * log(1 + τ/D) per dim.
  * Symmetric across dimensions (sum invariant under permutation).
  * Negative / NaN observation_precision floored to 0.
  * epistemic_weight_from_precision: decays as posterior precision
    grows; w(0) = w_max; w(decay_scale) = w_max/2; → 0 at infinity.
  * Bonus = 0 when fluency_passed=False (hard gate; directive line 220).
  * Bonus = 0 when info_gain ≈ 0 (rationale "zero_information_gain").
  * Bonus capped at cohort_daily_budget * cap_fraction; capped flag set.
  * EpistemicBonusResult shape: bonus, info_gain, weight, capped,
    rationale fields.
  * Constants pinned at A14 defaults.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from adam.intelligence.bong import BONGPosterior
from adam.intelligence.epistemic_bid_bonus import (
    DEFAULT_COHORT_BUDGET_CAP_FRACTION,
    DEFAULT_PRECISION_DECAY_SCALE,
    DEFAULT_W_MAX,
    EpistemicBonusResult,
    compute_epistemic_bonus,
    epistemic_weight_from_precision,
    expected_information_gain,
)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _individual(d: int = 5, precision: float = 4.0):
    """BONGPosterior with d dims, all D[i] = precision."""
    D = np.full(d, precision, dtype=np.float64)
    eta = D * 0.5  # μ = 0.5
    return BONGPosterior(eta=eta, D=D, observation_count=0, last_updated=0.0)


# -----------------------------------------------------------------------------
# Constants pinned (A14 defaults — change requires explicit calibration update)
# -----------------------------------------------------------------------------


def test_constants_pinned():
    assert DEFAULT_W_MAX == 1.0
    assert DEFAULT_PRECISION_DECAY_SCALE == 10.0
    assert DEFAULT_COHORT_BUDGET_CAP_FRACTION == 0.10


# -----------------------------------------------------------------------------
# expected_information_gain
# -----------------------------------------------------------------------------


def test_eig_zero_observation_precision_returns_zero():
    indiv = _individual(d=4, precision=10.0)
    assert expected_information_gain(indiv, 0.0) == 0.0


def test_eig_zero_observation_precision_array_returns_zero():
    indiv = _individual(d=4, precision=10.0)
    eig = expected_information_gain(indiv, np.zeros(4))
    assert eig == 0.0


def test_eig_monotonic_in_observation_precision():
    """Higher τ → higher EIG."""
    indiv = _individual(d=4, precision=10.0)
    eig_low = expected_information_gain(indiv, 0.5)
    eig_mid = expected_information_gain(indiv, 2.0)
    eig_high = expected_information_gain(indiv, 10.0)
    assert eig_low < eig_mid < eig_high


def test_eig_monotonic_decreasing_in_posterior_precision():
    """Higher posterior precision (well-known user) → less EIG per
    observation. Holds the observation precision fixed, varies D."""
    indiv_diffuse = _individual(d=4, precision=1.0)    # cold-start
    indiv_known = _individual(d=4, precision=100.0)    # well-known
    eig_diffuse = expected_information_gain(indiv_diffuse, 1.0)
    eig_known = expected_information_gain(indiv_known, 1.0)
    assert eig_known < eig_diffuse, (
        f"well-known user should have lower EIG; "
        f"got diffuse={eig_diffuse} known={eig_known}"
    )


def test_eig_matches_closed_form():
    """EIG_per_dim = 0.5 * log(1 + τ/D); sum across dims."""
    indiv = _individual(d=3, precision=4.0)
    tau = 1.0
    expected = 3 * 0.5 * math.log1p(tau / 4.0)
    actual = expected_information_gain(indiv, tau)
    assert actual == pytest.approx(expected, abs=1e-9)


def test_eig_per_dim_array_matches_sum():
    """Per-dim observation precision array sums per-dim EIG."""
    indiv = _individual(d=3, precision=4.0)
    tau = np.array([0.5, 1.0, 2.0])
    expected = sum(0.5 * math.log1p(t / 4.0) for t in tau)
    actual = expected_information_gain(indiv, tau)
    assert actual == pytest.approx(expected, abs=1e-9)


def test_eig_symmetric_across_dim_permutation():
    """EIG is a sum across dims; reordering D doesn't change the result."""
    D1 = np.array([1.0, 4.0, 9.0])
    D2 = np.array([9.0, 1.0, 4.0])
    indiv1 = BONGPosterior(eta=D1 * 0.5, D=D1, observation_count=0, last_updated=0.0)
    indiv2 = BONGPosterior(eta=D2 * 0.5, D=D2, observation_count=0, last_updated=0.0)
    assert expected_information_gain(indiv1, 1.0) == pytest.approx(
        expected_information_gain(indiv2, 1.0), abs=1e-9,
    )


def test_eig_negative_observation_precision_floored_to_zero():
    indiv = _individual(d=3, precision=4.0)
    assert expected_information_gain(indiv, -1.0) == 0.0


def test_eig_nan_observation_precision_floored_to_zero():
    indiv = _individual(d=3, precision=4.0)
    assert expected_information_gain(indiv, float("nan")) == 0.0


def test_eig_array_with_negative_and_nan_floored_to_zero():
    """Per-dim array: negative / NaN entries silently floored, valid
    entries contribute normally."""
    indiv = _individual(d=4, precision=4.0)
    tau = np.array([-0.5, 1.0, float("nan"), 2.0])
    # Expected: only dims 1 and 3 contribute
    expected = 0.5 * math.log1p(1.0 / 4.0) + 0.5 * math.log1p(2.0 / 4.0)
    assert expected_information_gain(indiv, tau) == pytest.approx(
        expected, abs=1e-9,
    )


def test_eig_always_non_negative():
    """Monotonic-non-negative property (Bayesian update can never
    produce negative information)."""
    indiv = _individual(d=5, precision=4.0)
    for tau in [0.0, 0.001, 1.0, 10.0, 1000.0]:
        assert expected_information_gain(indiv, tau) >= 0.0


# -----------------------------------------------------------------------------
# epistemic_weight_from_precision
# -----------------------------------------------------------------------------


def test_weight_at_zero_precision_equals_w_max():
    """A pathological zero-precision user gets w_max. (We floor D at
    MIN_PRECISION so this is asymptotic, not exact.)"""
    D = np.full(3, 1e-300)  # essentially zero
    indiv = BONGPosterior(eta=np.zeros(3), D=D, observation_count=0, last_updated=0.0)
    w = epistemic_weight_from_precision(indiv, w_max=2.0, decay_scale=10.0)
    # With D floored at MIN_PRECISION ≈ 1e-6, sum_D ≈ 3e-6, weight ≈ w_max.
    assert w == pytest.approx(2.0, rel=1e-3)


def test_weight_at_decay_scale_is_half_w_max():
    """Posterior precision sum exactly equal to decay_scale → w/2."""
    # 5 dims at precision 2.0 each → sum = 10.0 = decay_scale
    indiv = _individual(d=5, precision=2.0)
    w = epistemic_weight_from_precision(
        indiv, w_max=1.0, decay_scale=10.0,
    )
    assert w == pytest.approx(0.5, abs=1e-9)


def test_weight_decreases_monotonically_with_precision():
    """Increasing posterior precision → strictly decreasing w."""
    indiv_low = _individual(d=4, precision=1.0)    # sum=4
    indiv_mid = _individual(d=4, precision=10.0)   # sum=40
    indiv_high = _individual(d=4, precision=100.0) # sum=400
    w_low = epistemic_weight_from_precision(indiv_low)
    w_mid = epistemic_weight_from_precision(indiv_mid)
    w_high = epistemic_weight_from_precision(indiv_high)
    assert w_high < w_mid < w_low


def test_weight_clamps_negative_decay_scale_to_default():
    """Bad decay_scale → fallback to default; no exception."""
    indiv = _individual(d=3, precision=4.0)
    w_bad = epistemic_weight_from_precision(
        indiv, w_max=1.0, decay_scale=-5.0,
    )
    w_default = epistemic_weight_from_precision(
        indiv, w_max=1.0, decay_scale=DEFAULT_PRECISION_DECAY_SCALE,
    )
    assert w_bad == pytest.approx(w_default, abs=1e-9)


def test_weight_never_negative():
    """w_max < 0 should still produce w >= 0."""
    indiv = _individual(d=3, precision=4.0)
    assert epistemic_weight_from_precision(indiv, w_max=-1.0) == 0.0


# -----------------------------------------------------------------------------
# compute_epistemic_bonus
# -----------------------------------------------------------------------------


def test_bonus_blocked_by_fluency_floor():
    """fluency_passed=False → bonus 0.0 with rationale
    'blocked_by_fluency_floor'. Hard gate per directive line 220."""
    indiv = _individual(d=3, precision=4.0)
    result = compute_epistemic_bonus(
        indiv, observation_precision=2.0, fluency_passed=False,
    )
    assert result.bonus == 0.0
    assert result.info_gain == 0.0
    assert result.weight == 0.0
    assert result.rationale == "blocked_by_fluency_floor"
    assert result.capped is False


def test_bonus_zero_information_gain_returns_zero():
    """Zero observation precision → zero info gain → zero bonus,
    rationale 'zero_information_gain'."""
    indiv = _individual(d=3, precision=4.0)
    result = compute_epistemic_bonus(
        indiv, observation_precision=0.0, fluency_passed=True,
    )
    assert result.bonus == 0.0
    assert result.rationale == "zero_information_gain"


def test_bonus_computed_when_fluency_passes_and_obs_informative():
    indiv = _individual(d=3, precision=4.0)
    result = compute_epistemic_bonus(
        indiv, observation_precision=2.0, fluency_passed=True,
    )
    assert result.bonus > 0.0
    assert result.info_gain > 0.0
    assert result.weight > 0.0
    assert result.rationale == "computed"
    assert result.capped is False


def test_bonus_equals_weight_times_info_gain_when_uncapped():
    indiv = _individual(d=3, precision=4.0)
    result = compute_epistemic_bonus(
        indiv, observation_precision=1.5,
        w_max=1.0, decay_scale=10.0,
    )
    assert result.bonus == pytest.approx(
        result.weight * result.info_gain, abs=1e-9,
    )


def test_bonus_capped_to_cohort_budget():
    """Raw bonus exceeding cohort_daily_budget * cap_fraction is
    clipped; capped flag set; rationale documents."""
    # Diffuse user → high w_epistemic; high observation precision →
    # high EIG. Together produce a raw bonus that overshoots a small
    # budget.
    indiv = _individual(d=10, precision=0.5)
    result = compute_epistemic_bonus(
        indiv,
        observation_precision=20.0,
        cohort_daily_budget=1.0,
        cohort_budget_cap_fraction=0.1,  # cap = 0.1
    )
    assert result.bonus == pytest.approx(0.1, abs=1e-9)
    assert result.capped is True
    assert result.rationale == "capped_to_cohort_budget"


def test_bonus_uncapped_when_under_cohort_budget():
    """Raw bonus below the cap → bonus unchanged, capped=False."""
    # Well-known user → tiny bonus
    indiv = _individual(d=3, precision=100.0)
    result = compute_epistemic_bonus(
        indiv,
        observation_precision=0.1,
        cohort_daily_budget=1000.0,
        cohort_budget_cap_fraction=0.5,
    )
    assert result.capped is False
    assert result.rationale == "computed"


def test_bonus_cohort_budget_none_means_no_cap():
    """Without cohort budget arg, bonus is never capped."""
    indiv = _individual(d=10, precision=0.5)
    result = compute_epistemic_bonus(
        indiv, observation_precision=20.0, cohort_daily_budget=None,
    )
    assert result.capped is False


def test_bonus_zero_or_negative_cohort_budget_skips_cap():
    """Defensive: cohort_daily_budget <= 0 → no cap applied."""
    indiv = _individual(d=10, precision=0.5)
    result_zero = compute_epistemic_bonus(
        indiv, observation_precision=20.0, cohort_daily_budget=0.0,
    )
    assert result_zero.capped is False
    result_neg = compute_epistemic_bonus(
        indiv, observation_precision=20.0, cohort_daily_budget=-1.0,
    )
    assert result_neg.capped is False


def test_bonus_result_is_immutable():
    """Frozen dataclass — caller cannot mutate the verdict."""
    indiv = _individual(d=3, precision=4.0)
    result = compute_epistemic_bonus(indiv, observation_precision=1.0)
    with pytest.raises((AttributeError, Exception)):
        result.bonus = 999.0  # type: ignore[misc]


# -----------------------------------------------------------------------------
# Decision-time consumer pattern: bonus composes with pragmatic
# -----------------------------------------------------------------------------


def test_bonus_decreases_as_user_becomes_known():
    """Same observation across two users — diffuse user gets a larger
    bonus than well-known user. Pin the dual-control intent: pay
    premium for impressions that teach us about new users; less
    premium when we already know them."""
    diffuse = _individual(d=5, precision=1.0)
    known = _individual(d=5, precision=50.0)
    bonus_diffuse = compute_epistemic_bonus(diffuse, observation_precision=2.0)
    bonus_known = compute_epistemic_bonus(known, observation_precision=2.0)
    assert bonus_diffuse.bonus > bonus_known.bonus


def test_bonus_increases_with_observation_informativeness():
    """For the same user, a more-informative impression (higher τ)
    produces a larger bonus."""
    indiv = _individual(d=5, precision=1.0)
    bonus_weak = compute_epistemic_bonus(indiv, observation_precision=0.5)
    bonus_strong = compute_epistemic_bonus(indiv, observation_precision=10.0)
    assert bonus_strong.bonus > bonus_weak.bonus
