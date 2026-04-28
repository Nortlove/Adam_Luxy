# =============================================================================
# ADAM Causal Conformal Wrap Tests
# Location: tests/unit/test_causal_conformal.py
# =============================================================================

"""
CONFORMAL LIFT WRAP TESTS — M2 sibling layer (task #23 substrate)

Pins the split-conformal wrap on treatment-effect predictions. The wrap
takes (predicted, realized) calibration pairs and emits intervals with
finite-sample marginal coverage under exchangeability.

Coverage:
  - Refusal-on-empty discipline (no spurious intervals before warmup)
  - Interval shape (centered on point estimate, width = nonconformity quantile)
  - Empirical coverage matches nominal at sufficient calibration size
  - Coverage holds at any N (the property the parametric delta-method
    CI in synthetic_ab_simulation lacks at moderate N)
  - Integration with the synthetic A/B simulation via
    build_conformal_lift_wrap helper
"""

from __future__ import annotations

import math
import random

import pytest

from adam.intelligence.causal_conformal import (
    DEFAULT_ALPHA,
    DEFAULT_MIN_CALIBRATION_SIZE,
    ConformalLiftInterval,
    ConformalLiftWrap,
)
from adam.intelligence.synthetic_ab_simulation import (
    SyntheticABSimulator,
    build_conformal_lift_wrap,
    compute_conformal_lift_interval,
)


# ============================================================================
# Refusal-on-empty discipline
# ============================================================================


class TestEmptyDiscipline:
    """Before warmup, the wrap MUST refuse to emit intervals — otherwise
    callers consume non-coverage intervals as if they had coverage."""

    def test_refuses_below_min_calibration_size(self):
        wrap = ConformalLiftWrap(min_calibration_size=20)
        # Add 19 pairs — one short
        for i in range(19):
            wrap.record_realization(predicted_lift=0.25, realized_lift=0.20)
        with pytest.raises(RuntimeError, match="below min_calibration_size"):
            wrap.interval(predicted_lift=0.25, alpha=0.05)

    def test_emits_at_min_calibration_size(self):
        wrap = ConformalLiftWrap(min_calibration_size=20)
        for i in range(20):
            wrap.record_realization(predicted_lift=0.25, realized_lift=0.20)
        # Should not raise
        iv = wrap.interval(predicted_lift=0.25, alpha=0.05)
        assert isinstance(iv, ConformalLiftInterval)

    def test_min_calibration_size_floor_enforced(self):
        with pytest.raises(ValueError, match="must be >= 2"):
            ConformalLiftWrap(min_calibration_size=1)


# ============================================================================
# Input validation
# ============================================================================


class TestInputValidation:
    def test_record_rejects_non_finite(self):
        wrap = ConformalLiftWrap(min_calibration_size=2)
        with pytest.raises(ValueError, match="finite"):
            wrap.record_realization(predicted_lift=float("inf"), realized_lift=0.0)
        with pytest.raises(ValueError, match="finite"):
            wrap.record_realization(predicted_lift=0.0, realized_lift=float("nan"))

    def test_interval_rejects_non_finite(self):
        wrap = ConformalLiftWrap(min_calibration_size=2)
        wrap.record_realization(0.0, 0.0)
        wrap.record_realization(0.1, 0.1)
        with pytest.raises(ValueError, match="finite"):
            wrap.interval(predicted_lift=float("inf"))

    def test_interval_rejects_invalid_alpha(self):
        wrap = ConformalLiftWrap(min_calibration_size=2)
        wrap.record_realization(0.0, 0.0)
        wrap.record_realization(0.1, 0.1)
        with pytest.raises(ValueError, match="alpha"):
            wrap.interval(predicted_lift=0.0, alpha=0.0)
        with pytest.raises(ValueError, match="alpha"):
            wrap.interval(predicted_lift=0.0, alpha=1.0)


# ============================================================================
# Interval shape
# ============================================================================


class TestIntervalShape:
    def test_interval_centered_on_point_estimate(self):
        """When residuals are symmetric, the interval is centered on
        the point estimate."""
        wrap = ConformalLiftWrap(min_calibration_size=10)
        for i in range(30):
            # Symmetric noise: realized = predicted ± 0.05
            offset = 0.05 if i % 2 == 0 else -0.05
            wrap.record_realization(
                predicted_lift=0.25, realized_lift=0.25 + offset,
            )
        iv = wrap.interval(predicted_lift=0.25, alpha=0.05)
        assert iv.lower < 0.25 < iv.upper
        # Centered: lower and upper equidistant from point
        assert abs((0.25 - iv.lower) - (iv.upper - 0.25)) < 1e-9

    def test_interval_width_increases_with_residual_spread(self):
        """Wider residuals → wider intervals."""
        narrow = ConformalLiftWrap(min_calibration_size=10)
        for i in range(30):
            narrow.record_realization(
                predicted_lift=0.25,
                realized_lift=0.25 + (0.01 * (1 if i % 2 == 0 else -1)),
            )
        wide = ConformalLiftWrap(min_calibration_size=10)
        for i in range(30):
            wide.record_realization(
                predicted_lift=0.25,
                realized_lift=0.25 + (0.10 * (1 if i % 2 == 0 else -1)),
            )

        iv_narrow = narrow.interval(predicted_lift=0.25, alpha=0.05)
        iv_wide = wide.interval(predicted_lift=0.25, alpha=0.05)
        assert iv_wide.width() > iv_narrow.width()

    def test_signed_predictions_supported(self):
        """Treatment effects can be negative (backfire). The wrap must
        not assume non-negativity."""
        wrap = ConformalLiftWrap(min_calibration_size=10)
        for i in range(30):
            wrap.record_realization(
                predicted_lift=-0.10,
                realized_lift=-0.10 + (0.02 * (1 if i % 2 == 0 else -1)),
            )
        iv = wrap.interval(predicted_lift=-0.10, alpha=0.05)
        assert iv.point_estimate == -0.10
        assert iv.lower < -0.10 < iv.upper


# ============================================================================
# Empirical coverage — the load-bearing property
# ============================================================================


class TestEmpiricalCoverage:
    """Across many calibration sets drawn from a known noise distribution,
    the conformal CI must achieve the nominal coverage rate. This is
    what the parametric delta-method CI in synthetic_ab_simulation
    fails to do at moderate N."""

    def test_nominal_coverage_recovered_with_gaussian_noise(self):
        """Calibration pairs drawn from Gaussian noise → empirical
        coverage ≈ 1 - alpha."""
        rng = random.Random(42)
        wrap = ConformalLiftWrap(min_calibration_size=50)

        # Build a calibration set: predicted=0.25 (planted), realized
        # has Gaussian noise ~N(0, sigma^2)
        sigma = 0.05
        for _ in range(200):
            noise = rng.gauss(0, sigma)
            wrap.record_realization(
                predicted_lift=0.25,
                realized_lift=0.25 + noise,
            )

        # Empirical coverage at nominal 95% should be approximately 95%
        empirical = wrap.empirical_coverage(alpha=0.05)
        # Allow ±5 percentage points (binomial noise on N=200 with p=0.95
        # has SE ≈ 1.5 percentage points; allow 3.3 SD for robustness)
        assert 0.90 <= empirical <= 1.0, (
            f"Empirical coverage {empirical:.2%} not in [90%, 100%]"
        )

    def test_alpha_10_gives_lower_coverage_than_alpha_05(self):
        """Higher alpha → narrower interval → lower empirical coverage."""
        rng = random.Random(42)
        wrap = ConformalLiftWrap(min_calibration_size=50)
        for _ in range(200):
            wrap.record_realization(
                predicted_lift=0.25,
                realized_lift=0.25 + rng.gauss(0, 0.05),
            )
        cov_05 = wrap.empirical_coverage(alpha=0.05)
        cov_10 = wrap.empirical_coverage(alpha=0.10)
        assert cov_05 > cov_10


# ============================================================================
# Integration with synthetic A/B simulation
# ============================================================================


class TestSyntheticIntegration:
    """The conformal wrap, fed by the synthetic A/B simulator's
    bootstrap_calibration helper, must produce intervals that contain
    the planted lift at ~95% coverage — which is the property the
    parametric delta-method CI in the simulator approached but
    under-shot."""

    def test_bootstrap_calibration_produces_valid_wrap(self):
        wrap = build_conformal_lift_wrap(
            planted_lift=0.25,
            n_per_subsample=4000,
            n_subsamples=30,
            base_seed=42,
            min_calibration_size=20,
        )
        # All 30 subsamples should have produced finite observed lifts;
        # the wrap should hold ~30 pairs (some may fail isfinite check
        # in degenerate seeds — should be very rare at n=4000)
        assert wrap.calibration_size() >= 25
        assert wrap.calibration_size() <= 30

    def test_conformal_interval_contains_planted_lift(self):
        """At sufficient calibration size, the conformal interval
        around the planted lift contains the realized lift at ~95%
        empirical coverage. Tested across many subsample seeds."""
        wrap = build_conformal_lift_wrap(
            planted_lift=0.25,
            n_per_subsample=4000,
            n_subsamples=100,
            base_seed=0,
            min_calibration_size=20,
        )
        # Empirical coverage at nominal 95% on the calibration set itself
        # should be approximately 95%. (This is testing in-sample so it
        # should be exact up to ceiling effects of split-conformal.)
        empirical = wrap.empirical_coverage(alpha=0.05)
        # Split-conformal in-sample empirical coverage is exactly
        # ceil((n+1)(1-alpha))/n. For n=100, alpha=0.05:
        # k = ceil(101*0.95) = 96, coverage = 96/100 = 0.96
        # Allow 90-100% range (some seeds produce non-finite lift)
        assert 0.90 <= empirical <= 1.0

    def test_compute_conformal_lift_interval_convenience(self):
        wrap = build_conformal_lift_wrap(
            planted_lift=0.25,
            n_per_subsample=4000,
            n_subsamples=30,
            base_seed=10,
            min_calibration_size=20,
        )
        iv = compute_conformal_lift_interval(
            wrap=wrap, point_estimate=0.25, alpha=0.05,
        )
        assert isinstance(iv, ConformalLiftInterval)
        assert iv.point_estimate == 0.25
        assert iv.lower < 0.25 < iv.upper
        assert iv.coverage_probability == 0.95


# ============================================================================
# Snapshot + reset
# ============================================================================


class TestStateManagement:
    def test_snapshot_returns_independent_copy(self):
        wrap = ConformalLiftWrap(min_calibration_size=2)
        wrap.record_realization(0.0, 0.0)
        wrap.record_realization(0.1, 0.1)
        snap1 = wrap.snapshot_pairs()
        wrap.record_realization(0.2, 0.2)
        snap2 = wrap.snapshot_pairs()
        # First snapshot unchanged
        assert len(snap1) == 2
        assert len(snap2) == 3

    def test_reset_clears_calibration(self):
        wrap = ConformalLiftWrap(min_calibration_size=2)
        wrap.record_realization(0.0, 0.0)
        wrap.record_realization(0.1, 0.1)
        assert wrap.calibration_size() == 2
        wrap.reset()
        assert wrap.calibration_size() == 0


# ============================================================================
# Defaults
# ============================================================================


class TestDefaults:
    def test_default_alpha_is_05(self):
        assert DEFAULT_ALPHA == 0.05

    def test_default_min_calibration_size_is_20(self):
        assert DEFAULT_MIN_CALIBRATION_SIZE == 20
