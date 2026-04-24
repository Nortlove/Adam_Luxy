"""Unit tests for split-conformal coverage."""

from __future__ import annotations

import random

import pytest

from adam.intelligence.recommendation_class import (
    ConformalCoverage,
    ConformalInterval,
    DEFAULT_MIN_CALIBRATION_SIZE,
)


# -----------------------------------------------------------------------------
# Construction
# -----------------------------------------------------------------------------


class TestConstruction:
    def test_defaults_accepted(self):
        c = ConformalCoverage()
        assert c.calibration_size() == 0

    def test_invalid_min_cal_size_rejected(self):
        with pytest.raises(ValueError, match="min_calibration_size"):
            ConformalCoverage(min_calibration_size=1)
        with pytest.raises(ValueError, match="min_calibration_size"):
            ConformalCoverage(min_calibration_size=0)


# -----------------------------------------------------------------------------
# Calibration set
# -----------------------------------------------------------------------------


class TestCalibration:
    def test_record_appends(self):
        c = ConformalCoverage()
        c.record_realization(0.02, 0.025)
        c.record_realization(0.03, 0.028)
        assert c.calibration_size() == 2
        pairs = c.snapshot_pairs()
        assert pairs == [(0.02, 0.025), (0.03, 0.028)]

    def test_projected_rate_out_of_range_rejected(self):
        c = ConformalCoverage()
        with pytest.raises(ValueError, match="projected_rate"):
            c.record_realization(-0.01, 0.02)
        with pytest.raises(ValueError, match="projected_rate"):
            c.record_realization(1.01, 0.02)

    def test_realized_rate_out_of_range_rejected(self):
        c = ConformalCoverage()
        with pytest.raises(ValueError, match="realized_rate"):
            c.record_realization(0.02, -0.01)
        with pytest.raises(ValueError, match="realized_rate"):
            c.record_realization(0.02, 1.01)


# -----------------------------------------------------------------------------
# Interval emission
# -----------------------------------------------------------------------------


class TestIntervalEmission:
    def test_below_min_cal_refuses(self):
        c = ConformalCoverage(min_calibration_size=5)
        for _ in range(4):
            c.record_realization(0.02, 0.03)
        with pytest.raises(RuntimeError, match="below"):
            c.interval(projected_rate=0.02)

    def test_at_min_cal_emits(self):
        c = ConformalCoverage(min_calibration_size=5)
        for _ in range(5):
            c.record_realization(0.02, 0.03)
        iv = c.interval(projected_rate=0.02)
        assert isinstance(iv, ConformalInterval)

    def test_interval_clipped_to_zero_one(self):
        c = ConformalCoverage(min_calibration_size=5)
        # Large residuals push the raw interval below 0 or above 1
        for i in range(5):
            c.record_realization(0.5, 0.9)
        iv = c.interval(projected_rate=0.02, alpha=0.1)
        assert iv.lower >= 0.0
        assert iv.upper <= 1.0

    def test_interval_contains_check(self):
        c = ConformalCoverage(min_calibration_size=5)
        for _ in range(5):
            c.record_realization(0.02, 0.03)
        iv = c.interval(projected_rate=0.02, alpha=0.1)
        assert iv.contains(0.025)
        # Extreme value unlikely to be in a narrow interval
        assert not iv.contains(0.99)

    def test_width_is_upper_minus_lower(self):
        c = ConformalCoverage(min_calibration_size=5)
        for i in range(10):
            c.record_realization(0.03, 0.03 + (i - 5) * 0.002)
        iv = c.interval(projected_rate=0.03, alpha=0.1)
        assert iv.width() == pytest.approx(iv.upper - iv.lower, abs=1e-9)

    def test_coverage_probability_reflects_alpha(self):
        c = ConformalCoverage(min_calibration_size=5)
        for _ in range(5):
            c.record_realization(0.02, 0.03)
        iv = c.interval(projected_rate=0.02, alpha=0.1)
        assert iv.coverage_probability == pytest.approx(0.9, abs=1e-9)

    def test_calibration_size_stamped_on_interval(self):
        c = ConformalCoverage(min_calibration_size=3)
        for _ in range(7):
            c.record_realization(0.02, 0.03)
        iv = c.interval(projected_rate=0.02)
        assert iv.calibration_size == 7

    def test_interval_alpha_out_of_range_rejected(self):
        c = ConformalCoverage(min_calibration_size=3)
        for _ in range(3):
            c.record_realization(0.02, 0.03)
        with pytest.raises(ValueError, match="alpha"):
            c.interval(projected_rate=0.02, alpha=0.0)
        with pytest.raises(ValueError, match="alpha"):
            c.interval(projected_rate=0.02, alpha=1.0)


# -----------------------------------------------------------------------------
# Marginal coverage — the theoretical guarantee
# -----------------------------------------------------------------------------


class TestMarginalCoverage:
    def test_empirical_coverage_refuses_below_min_cal(self):
        c = ConformalCoverage(min_calibration_size=20)
        for _ in range(5):
            c.record_realization(0.02, 0.03)
        with pytest.raises(RuntimeError, match="below"):
            c.empirical_coverage(alpha=0.1)

    def test_empirical_coverage_approximately_matches_nominal(self):
        """With IID symmetric residuals, empirical coverage should be
        close to 1 - alpha (split-conformal exchangeability guarantee).
        """
        rng = random.Random(42)
        c = ConformalCoverage(min_calibration_size=20)
        # Simulate 100 IID (projected, realized) pairs with fixed
        # Gaussian residual around 0
        for _ in range(100):
            proj = rng.uniform(0.01, 0.10)
            # Realized = proj + noise
            real = max(0.0, min(1.0, proj + rng.gauss(0.0, 0.02)))
            c.record_realization(proj, real)
        cov = c.empirical_coverage(alpha=0.1)
        # Tolerance: binomial noise at n=100 gives ~4-5pp spread.
        assert 0.8 < cov <= 1.0
