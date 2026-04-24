"""Unit tests for sequential-analysis schedule + O'Brien-Fleming boundaries."""

from __future__ import annotations

import math

import pytest

from adam.intelligence.recommendation_class import (
    InterimDecision,
    LookSchedule,
    SequentialAdjudicator,
)
from adam.intelligence.recommendation_class.sequential_schedule import (
    _normal_cdf, _normal_ppf,
)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


class TestNormalHelpers:
    def test_normal_cdf_standard_points(self):
        assert math.isclose(_normal_cdf(0.0), 0.5, abs_tol=1e-9)
        assert math.isclose(_normal_cdf(1.96), 0.975, abs_tol=1e-3)
        assert math.isclose(_normal_cdf(-1.96), 0.025, abs_tol=1e-3)

    def test_normal_ppf_round_trip(self):
        for p in (0.025, 0.05, 0.5, 0.95, 0.975, 0.99):
            z = _normal_ppf(p)
            recovered = _normal_cdf(z)
            assert math.isclose(recovered, p, abs_tol=1e-6)

    def test_ppf_known_values(self):
        # Standard critical values
        assert math.isclose(_normal_ppf(0.975), 1.959964, abs_tol=1e-4)
        assert math.isclose(_normal_ppf(0.995), 2.575829, abs_tol=1e-4)

    def test_ppf_out_of_range_rejected(self):
        with pytest.raises(ValueError, match="ppf"):
            _normal_ppf(-0.1)
        with pytest.raises(ValueError, match="ppf"):
            _normal_ppf(1.1)


# -----------------------------------------------------------------------------
# LookSchedule
# -----------------------------------------------------------------------------


class TestLookSchedule:
    def test_equal_spacing_constructs(self):
        sched = LookSchedule.equal_spacing(n_looks=4, alpha=0.05)
        assert sched.n_looks() == 4
        assert sched.information_fractions == (0.25, 0.5, 0.75, 1.0)

    def test_empty_fractions_rejected(self):
        with pytest.raises(ValueError, match="non-empty"):
            LookSchedule(information_fractions=())

    def test_non_monotone_fractions_rejected(self):
        with pytest.raises(ValueError, match="strictly increasing"):
            LookSchedule(information_fractions=(0.3, 0.2, 1.0))

    def test_out_of_range_fraction_rejected(self):
        with pytest.raises(ValueError, match="in \\(0, 1\\]"):
            LookSchedule(information_fractions=(0.0, 1.0))
        with pytest.raises(ValueError, match="in \\(0, 1\\]"):
            LookSchedule(information_fractions=(0.5, 1.5))

    def test_missing_terminal_one_rejected(self):
        with pytest.raises(ValueError, match="end at 1.0"):
            LookSchedule(information_fractions=(0.25, 0.75))

    def test_invalid_alpha_rejected(self):
        with pytest.raises(ValueError, match="alpha"):
            LookSchedule(information_fractions=(1.0,), alpha=0.0)
        with pytest.raises(ValueError, match="alpha"):
            LookSchedule(information_fractions=(1.0,), alpha=1.0)

    def test_obrien_fleming_monotonically_decreasing(self):
        """O'Brien-Fleming critical z-values shrink across looks."""
        sched = LookSchedule.equal_spacing(n_looks=5, alpha=0.05)
        bounds = sched.obrien_fleming_boundaries()
        for a, b in zip(bounds, bounds[1:]):
            assert a > b

    def test_obrien_fleming_final_equals_unadjusted_critical(self):
        """At t=1.0 the OBF boundary equals the unadjusted two-sided
        critical z — the formula z_overall * sqrt(1/1)."""
        sched = LookSchedule.equal_spacing(n_looks=3, alpha=0.05)
        bounds = sched.obrien_fleming_boundaries()
        assert math.isclose(bounds[-1], 1.959964, abs_tol=1e-4)

    def test_obrien_fleming_early_look_conservative(self):
        """Early-look boundaries are much higher than the final one,
        matching the canonical OBF shape that concentrates rejection
        mass at late looks."""
        sched = LookSchedule.equal_spacing(n_looks=4, alpha=0.05)
        bounds = sched.obrien_fleming_boundaries()
        assert bounds[0] > 3.0  # First look: > 3 sigma
        assert bounds[-1] < 2.0  # Final look: ~ 1.96


# -----------------------------------------------------------------------------
# SequentialAdjudicator — interim-look decisions
# -----------------------------------------------------------------------------


class TestSequentialAdjudicator:
    def test_implied_rate_out_of_range_rejected(self):
        sched = LookSchedule.equal_spacing(n_looks=3)
        with pytest.raises(ValueError, match="implied_rate"):
            SequentialAdjudicator(schedule=sched, implied_rate=0.0)
        with pytest.raises(ValueError, match="implied_rate"):
            SequentialAdjudicator(schedule=sched, implied_rate=1.0)

    def test_look_index_out_of_range_rejected(self):
        sched = LookSchedule.equal_spacing(n_looks=3)
        adj = SequentialAdjudicator(schedule=sched, implied_rate=0.05)
        with pytest.raises(ValueError, match="look_index"):
            adj.evaluate_look(look_index=3, observed_count=0, observed_sample_size=100)
        with pytest.raises(ValueError, match="look_index"):
            adj.evaluate_look(look_index=-1, observed_count=0, observed_sample_size=100)

    def test_bad_sample_size_rejected(self):
        sched = LookSchedule.equal_spacing(n_looks=3)
        adj = SequentialAdjudicator(schedule=sched, implied_rate=0.05)
        with pytest.raises(ValueError, match="observed_sample_size"):
            adj.evaluate_look(0, 0, 0)

    def test_count_over_sample_rejected(self):
        sched = LookSchedule.equal_spacing(n_looks=3)
        adj = SequentialAdjudicator(schedule=sched, implied_rate=0.05)
        with pytest.raises(ValueError, match="observed_count"):
            adj.evaluate_look(0, 20, 10)

    def test_on_implied_rate_continues(self):
        """Observed rate exactly at the implied rate → z=0 → CONTINUE."""
        sched = LookSchedule.equal_spacing(n_looks=3)
        adj = SequentialAdjudicator(schedule=sched, implied_rate=0.05)
        result = adj.evaluate_look(
            look_index=1, observed_count=50, observed_sample_size=1000,
        )
        assert result.decision == InterimDecision.CONTINUE
        assert math.isclose(result.z_statistic, 0.0, abs_tol=1e-9)

    def test_strong_overperformance_stops_for_efficacy_at_final(self):
        """At the final look (t=1), boundary ~ 1.96. Observed rate well
        above implied should cross the upper boundary."""
        sched = LookSchedule.equal_spacing(n_looks=3)
        adj = SequentialAdjudicator(schedule=sched, implied_rate=0.05)
        # 200/1000 = 20% vs implied 5% — huge z
        result = adj.evaluate_look(
            look_index=2, observed_count=200, observed_sample_size=1000,
        )
        assert result.decision == InterimDecision.STOP_FOR_EFFICACY

    def test_strong_underperformance_stops_for_futility_at_final(self):
        sched = LookSchedule.equal_spacing(n_looks=3)
        adj = SequentialAdjudicator(schedule=sched, implied_rate=0.10)
        # 5/1000 = 0.5% vs implied 10%
        result = adj.evaluate_look(
            look_index=2, observed_count=5, observed_sample_size=1000,
        )
        assert result.decision == InterimDecision.STOP_FOR_FUTILITY

    def test_early_look_requires_stronger_evidence(self):
        """At look 0 of 3 (t=1/3), OBF boundary is ~3.4. A moderate
        z-statistic that would cross the final boundary (1.96) should
        NOT cross the early boundary."""
        sched = LookSchedule.equal_spacing(n_looks=3)
        adj = SequentialAdjudicator(schedule=sched, implied_rate=0.05)
        # Rate 10% on 100 samples → z ~= 2.3 (exceeds 1.96 but not 3.4)
        result = adj.evaluate_look(
            look_index=0, observed_count=10, observed_sample_size=100,
        )
        assert result.decision == InterimDecision.CONTINUE
        assert 2.0 < result.z_statistic < 3.0

    def test_result_contains_all_evidence_fields(self):
        sched = LookSchedule.equal_spacing(n_looks=3)
        adj = SequentialAdjudicator(schedule=sched, implied_rate=0.05)
        result = adj.evaluate_look(
            look_index=1, observed_count=55, observed_sample_size=1000,
        )
        assert result.look_index == 1
        assert result.observed_count == 55
        assert result.observed_sample_size == 1000
        assert math.isclose(result.observed_rate, 0.055, abs_tol=1e-9)
        assert result.implied_rate == 0.05
        assert result.upper_boundary > 0
        assert result.lower_boundary == -result.upper_boundary
        assert result.information_fraction == pytest.approx(2 / 3, abs=1e-9)
