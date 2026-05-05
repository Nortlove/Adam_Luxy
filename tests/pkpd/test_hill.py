"""Tests for the Hill / Emax dose-response (directive §1.F.SI.1)."""
from __future__ import annotations

import math

import pytest

from adam.pkpd import (
    hill_response,
    inhibition_factor,
    stimulation_factor,
)


# ----------------------------------------------------------------------------
# Hill / Emax response
# ----------------------------------------------------------------------------

class TestHillResponseAnchors:
    def test_at_zero_concentration_returns_baseline(self) -> None:
        assert hill_response(
            0.0,
            baseline_effect=1.5,
            max_effect=8.0,
            ec50=2.0,
            hill_coefficient=1.0,
        ) == 1.5

    def test_at_ec50_returns_midpoint(self) -> None:
        e_0 = 1.5
        e_max = 8.0
        e_at_ec50 = hill_response(
            2.0,
            baseline_effect=e_0,
            max_effect=e_max,
            ec50=2.0,
            hill_coefficient=1.0,
        )
        assert e_at_ec50 == pytest.approx((e_0 + e_max) / 2.0, rel=1e-12)

    def test_asymptotes_to_max_effect(self) -> None:
        # 1000 * EC_50 → very near saturation regardless of n.
        e = hill_response(
            2000.0,
            baseline_effect=1.0,
            max_effect=10.0,
            ec50=2.0,
            hill_coefficient=1.0,
        )
        assert e == pytest.approx(10.0, rel=1e-3)


class TestHillResponseShape:
    def test_monotonic_in_concentration(self) -> None:
        cs = [0.0, 0.5, 1.0, 2.0, 5.0, 20.0, 100.0]
        es = [
            hill_response(
                c,
                baseline_effect=0.0,
                max_effect=10.0,
                ec50=2.0,
                hill_coefficient=1.0,
            )
            for c in cs
        ]
        for prior, current in zip(es, es[1:]):
            assert current >= prior

    def test_higher_hill_coefficient_steeper_curve(self) -> None:
        """At c < EC_50 a higher Hill coefficient produces a SMALLER
        response (the curve is suppressed); at c > EC_50 a higher
        coefficient produces a LARGER response (sharper saturation)."""
        c_low, c_high = 1.0, 4.0  # EC_50 = 2.0 → c_low < EC_50 < c_high
        ec50 = 2.0
        e_at_low_n_high = hill_response(
            c_low, baseline_effect=0.0, max_effect=1.0,
            ec50=ec50, hill_coefficient=1.0,
        )
        e_at_high_n_high = hill_response(
            c_low, baseline_effect=0.0, max_effect=1.0,
            ec50=ec50, hill_coefficient=4.0,
        )
        e_at_low_n_high_c = hill_response(
            c_high, baseline_effect=0.0, max_effect=1.0,
            ec50=ec50, hill_coefficient=1.0,
        )
        e_at_high_n_high_c = hill_response(
            c_high, baseline_effect=0.0, max_effect=1.0,
            ec50=ec50, hill_coefficient=4.0,
        )
        # Below EC_50: higher n suppresses.
        assert e_at_high_n_high < e_at_low_n_high
        # Above EC_50: higher n saturates harder.
        assert e_at_high_n_high_c > e_at_low_n_high_c

    def test_negative_baseline_to_positive_max_works(self) -> None:
        """E_0 and E_max can have arbitrary sign; the curve interpolates."""
        e_0 = -2.0
        e_max = 5.0
        e_zero = hill_response(
            0.0, baseline_effect=e_0, max_effect=e_max,
            ec50=2.0, hill_coefficient=1.0,
        )
        e_inf = hill_response(
            100000.0, baseline_effect=e_0, max_effect=e_max,
            ec50=2.0, hill_coefficient=1.0,
        )
        assert e_zero == e_0
        assert e_inf == pytest.approx(e_max, abs=0.001)


class TestHillResponseValidation:
    def test_rejects_negative_concentration(self) -> None:
        with pytest.raises(ValueError):
            hill_response(
                -1.0, baseline_effect=0.0, max_effect=1.0,
                ec50=2.0, hill_coefficient=1.0,
            )

    def test_rejects_non_finite_concentration(self) -> None:
        with pytest.raises(ValueError):
            hill_response(
                float("inf"), baseline_effect=0.0, max_effect=1.0,
                ec50=2.0, hill_coefficient=1.0,
            )

    def test_rejects_non_positive_ec50(self) -> None:
        with pytest.raises(ValueError):
            hill_response(
                1.0, baseline_effect=0.0, max_effect=1.0,
                ec50=0.0, hill_coefficient=1.0,
            )

    def test_rejects_non_positive_hill_coefficient(self) -> None:
        with pytest.raises(ValueError):
            hill_response(
                1.0, baseline_effect=0.0, max_effect=1.0,
                ec50=1.0, hill_coefficient=0.0,
            )


# ----------------------------------------------------------------------------
# Inhibition / Stimulation factors
# ----------------------------------------------------------------------------

class TestInhibitionFactor:
    def test_no_drug_no_inhibition(self) -> None:
        assert inhibition_factor(
            0.0, max_inhibition=0.8, ic50=2.0,
        ) == pytest.approx(1.0, rel=1e-12)

    def test_high_drug_approaches_one_minus_imax(self) -> None:
        f = inhibition_factor(
            10000.0, max_inhibition=0.8, ic50=2.0,
        )
        assert f == pytest.approx(1.0 - 0.8, abs=1e-3)

    def test_at_ic50_returns_one_minus_half_imax(self) -> None:
        f = inhibition_factor(
            2.0, max_inhibition=0.8, ic50=2.0,
        )
        assert f == pytest.approx(1.0 - 0.4, rel=1e-12)

    def test_factor_in_unit_minus_imax_to_unit(self) -> None:
        for c in [0.1, 0.5, 1.0, 5.0, 100.0]:
            f = inhibition_factor(c, max_inhibition=0.6, ic50=2.0)
            assert (1.0 - 0.6) <= f <= 1.0

    def test_rejects_imax_outside_unit_interval(self) -> None:
        with pytest.raises(ValueError):
            inhibition_factor(1.0, max_inhibition=1.5, ic50=1.0)
        with pytest.raises(ValueError):
            inhibition_factor(1.0, max_inhibition=-0.1, ic50=1.0)


class TestStimulationFactor:
    def test_no_drug_no_stimulation(self) -> None:
        assert stimulation_factor(
            0.0, max_stimulation=2.0, sc50=2.0,
        ) == pytest.approx(1.0, rel=1e-12)

    def test_high_drug_approaches_one_plus_smax(self) -> None:
        f = stimulation_factor(
            10000.0, max_stimulation=2.0, sc50=2.0,
        )
        assert f == pytest.approx(1.0 + 2.0, abs=1e-3)

    def test_at_sc50_returns_one_plus_half_smax(self) -> None:
        f = stimulation_factor(
            2.0, max_stimulation=2.0, sc50=2.0,
        )
        assert f == pytest.approx(1.0 + 1.0, rel=1e-12)

    def test_factor_in_one_to_one_plus_smax(self) -> None:
        for c in [0.1, 0.5, 1.0, 5.0, 100.0]:
            f = stimulation_factor(c, max_stimulation=3.0, sc50=2.0)
            assert 1.0 <= f <= 1.0 + 3.0

    def test_rejects_negative_smax(self) -> None:
        with pytest.raises(ValueError):
            stimulation_factor(1.0, max_stimulation=-0.1, sc50=1.0)
