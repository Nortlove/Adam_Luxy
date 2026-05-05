"""Tests for the Gross-Vitells LEE trial factor (directive §1.A.SI.2)."""
from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.special import erfc

from adam.blind_analysis import (
    BoxParameter,
    MonteCarloLEEResult,
    empirical_upcrossings_at_threshold,
    gross_vitells_global_p_value,
    gross_vitells_trial_factor,
    monte_carlo_global_p_value,
    p_local_one_sided,
    placeholder_data_generator,
    sealed_box,
)


# ----------------------------------------------------------------------------
# Closed-form local p-value
# ----------------------------------------------------------------------------

class TestLocalPValue:
    def test_p_local_at_zero_is_half(self) -> None:
        assert p_local_one_sided(0.0) == pytest.approx(0.5, abs=1e-12)

    def test_p_local_at_one_point_nine_six(self) -> None:
        # One-sided 2.5% level — z = 1.959964 ≈ 1.96.
        assert p_local_one_sided(1.96) == pytest.approx(0.025, abs=1e-3)

    def test_p_local_decreases_with_z(self) -> None:
        zs = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0]
        ps = [p_local_one_sided(z) for z in zs]
        for prior, current in zip(ps, ps[1:]):
            assert current < prior

    def test_p_local_rejects_non_finite(self) -> None:
        with pytest.raises(ValueError):
            p_local_one_sided(float("nan"))
        with pytest.raises(ValueError):
            p_local_one_sided(float("inf"))


# ----------------------------------------------------------------------------
# Closed-form global p-value (eq. 1)
# ----------------------------------------------------------------------------

class TestGlobalPValue:
    def test_zero_upcrossings_returns_p_local(self) -> None:
        # No LEE correction when N = 0 → trivial scan.
        for z in [0.5, 1.0, 2.0, 3.0, 5.0]:
            p_global = gross_vitells_global_p_value(z, 0.0)
            assert p_global == pytest.approx(p_local_one_sided(z), rel=1e-12)

    def test_global_exceeds_local_when_upcrossings_positive(self) -> None:
        for z in [1.0, 2.0, 3.0, 4.0, 5.0]:
            p_local = p_local_one_sided(z)
            p_global = gross_vitells_global_p_value(z, upcrossings_at_reference=2.0)
            assert p_global > p_local

    def test_p_global_saturates_at_one(self) -> None:
        # Many upcrossings at low local-z drives the LEE term well past 1.
        p_global = gross_vitells_global_p_value(
            local_z=0.5,
            upcrossings_at_reference=100.0,
        )
        assert p_global == 1.0

    def test_negative_upcrossings_rejected(self) -> None:
        with pytest.raises(ValueError):
            gross_vitells_global_p_value(2.0, upcrossings_at_reference=-1.0)

    def test_non_finite_reference_rejected(self) -> None:
        with pytest.raises(ValueError):
            gross_vitells_global_p_value(
                2.0, upcrossings_at_reference=1.0, reference_z=float("nan"),
            )

    def test_reference_z_consistency_via_davies(self) -> None:
        """Equation (2) of the module: ⟨N(z₂)⟩ = ⟨N(z₁)⟩ * exp(-(z₂² - z₁²)/2).

        If we pass two physically-equivalent (upcrossings, reference_z)
        pairs through `gross_vitells_global_p_value`, the resulting
        global p-value at the SAME local_z must match.
        """
        local_z = 4.0
        n_at_zero = 5.0
        z_ref = 1.5
        # Davies-correct N at the new reference threshold.
        n_at_ref = n_at_zero * math.exp(-(z_ref**2) / 2.0)
        p1 = gross_vitells_global_p_value(local_z, n_at_zero, reference_z=0.0)
        p2 = gross_vitells_global_p_value(local_z, n_at_ref, reference_z=z_ref)
        assert p1 == pytest.approx(p2, rel=1e-12)


# ----------------------------------------------------------------------------
# Trial factor
# ----------------------------------------------------------------------------

class TestTrialFactor:
    def test_trial_factor_one_when_no_upcrossings(self) -> None:
        for z in [1.0, 2.0, 3.0, 4.0]:
            assert gross_vitells_trial_factor(z, 0.0) == pytest.approx(1.0, rel=1e-12)

    @pytest.mark.parametrize("local_z", [3.0, 4.0, 5.0, 6.0, 7.0])
    @pytest.mark.parametrize("upcrossings", [0.5, 1.0, 5.0, 20.0])
    def test_asymptotic_linearity_in_z(
        self, local_z: float, upcrossings: float,
    ) -> None:
        """Directive §1.A.SI.2 parametrization: TF − 1 is asymptotically
        linear in fixed-mass z.

        Equation (3) of the module:
          TF(z) − 1 ≈ ⟨N(z_ref=0)⟩ * √(2π) * z   (z → ∞)

        At each (z, N) we check that the ratio (TF − 1) / z is within
        tolerance of the asymptotic slope ⟨N⟩ * √(2π). Tolerance
        loosens at smaller z (still in the asymptotic regime z ≥ 3
        but the leading-order correction matters).
        """
        tf_minus_one = gross_vitells_trial_factor(local_z, upcrossings) - 1.0
        empirical_slope = tf_minus_one / local_z
        asymptotic_slope = upcrossings * math.sqrt(2.0 * math.pi)
        # Looser tolerance at z=3 (still some sub-leading correction);
        # tighter at z=7 (deep in the asymptotic regime).
        tolerance = 0.5 / local_z  # ~17% at z=3; ~7% at z=7.
        assert empirical_slope == pytest.approx(asymptotic_slope, rel=tolerance)

    def test_trial_factor_scales_linearly_with_upcrossings(self) -> None:
        """At fixed z, doubling N approximately doubles (TF − 1)."""
        z = 5.0
        tf1 = gross_vitells_trial_factor(z, upcrossings_at_reference=1.0) - 1.0
        tf2 = gross_vitells_trial_factor(z, upcrossings_at_reference=2.0) - 1.0
        assert tf2 == pytest.approx(2.0 * tf1, rel=1e-3)

    def test_trial_factor_grows_with_z(self) -> None:
        """TF strictly increases in local_z when ⟨N⟩ > 0."""
        upcrossings = 3.0
        zs = [3.0, 4.0, 5.0, 6.0, 7.0]
        tfs = [gross_vitells_trial_factor(z, upcrossings) for z in zs]
        for prior, current in zip(tfs, tfs[1:]):
            assert current > prior


# ----------------------------------------------------------------------------
# Empirical upcrossings counter
# ----------------------------------------------------------------------------

class TestUpcrossings:
    def test_zero_upcrossings_for_constant(self) -> None:
        field = [0.5] * 10
        assert empirical_upcrossings_at_threshold(field, threshold=0.0) == 0

    def test_one_upcrossing_for_step(self) -> None:
        field = [-1.0, -0.5, 0.5, 1.0]
        assert empirical_upcrossings_at_threshold(field, threshold=0.0) == 1

    def test_multiple_oscillations(self) -> None:
        # Three upward crossings of zero.
        field = [-1.0, 1.0, -1.0, 1.0, -1.0, 1.0]
        assert empirical_upcrossings_at_threshold(field, threshold=0.0) == 3

    def test_threshold_other_than_zero(self) -> None:
        field = [0.0, 1.0, 0.0, 2.0]
        # Crossings of threshold=0.5: from 0.0 → 1.0 (yes), then 0.0 → 2.0 (yes).
        assert empirical_upcrossings_at_threshold(field, threshold=0.5) == 2

    def test_rejects_non_1d(self) -> None:
        with pytest.raises(ValueError):
            empirical_upcrossings_at_threshold([[1.0, 2.0], [3.0, 4.0]], threshold=0.0)


# ----------------------------------------------------------------------------
# Monte-Carlo Gaussian-process ensemble
# ----------------------------------------------------------------------------

class TestMonteCarlo:
    def test_result_shape(self) -> None:
        result = monte_carlo_global_p_value(
            n_trials=50, n_grid_points=64, correlation_length=0.05, seed=0,
        )
        assert isinstance(result, MonteCarloLEEResult)
        assert result.n_trials == 50
        assert result.n_grid_points == 64
        assert len(result.max_z_per_trial) == 50
        assert result.upcrossings_at_zero >= 0.0

    def test_seed_determinism(self) -> None:
        a = monte_carlo_global_p_value(
            n_trials=20, n_grid_points=64, correlation_length=0.1, seed=42,
        )
        b = monte_carlo_global_p_value(
            n_trials=20, n_grid_points=64, correlation_length=0.1, seed=42,
        )
        assert a.max_z_per_trial == b.max_z_per_trial
        assert a.upcrossings_at_zero == b.upcrossings_at_zero

    def test_different_seeds_different_samples(self) -> None:
        a = monte_carlo_global_p_value(
            n_trials=20, n_grid_points=64, correlation_length=0.1, seed=1,
        )
        b = monte_carlo_global_p_value(
            n_trials=20, n_grid_points=64, correlation_length=0.1, seed=2,
        )
        assert a.max_z_per_trial != b.max_z_per_trial

    def test_upcrossings_scale_inversely_with_correlation_length(self) -> None:
        """Shorter correlation length ⇒ more independent regions ⇒ more
        zero-crossings per trial."""
        short = monte_carlo_global_p_value(
            n_trials=200, n_grid_points=256, correlation_length=0.01, seed=7,
        )
        long = monte_carlo_global_p_value(
            n_trials=200, n_grid_points=256, correlation_length=0.20, seed=7,
        )
        assert short.upcrossings_at_zero > long.upcrossings_at_zero

    def test_empirical_p_global_decreases_with_threshold(self) -> None:
        result = monte_carlo_global_p_value(
            n_trials=500, n_grid_points=128, correlation_length=0.05, seed=11,
        )
        thresholds = [0.0, 1.0, 2.0, 3.0]
        ps = [result.empirical_p_global(t) for t in thresholds]
        for prior, current in zip(ps, ps[1:]):
            assert current <= prior

    def test_empirical_matches_closed_form_at_moderate_z(self) -> None:
        """Cross-check: at moderate threshold (z ≈ 2.5) the empirical
        p_global from a 10k-trial ensemble agrees with the closed-form
        prediction within a few standard errors of the binomial
        proportion estimator. ⟨N(0)⟩ is calibrated from the SAME
        ensemble.
        """
        result = monte_carlo_global_p_value(
            n_trials=10_000,
            n_grid_points=128,
            correlation_length=0.05,
            seed=2026,
        )
        threshold_z = 2.5
        empirical = result.empirical_p_global(threshold_z)
        predicted = gross_vitells_global_p_value(
            threshold_z,
            upcrossings_at_reference=result.upcrossings_at_zero,
        )
        # Standard error of the empirical proportion.
        se = math.sqrt(empirical * (1 - empirical) / result.n_trials)
        # Allow ~3 standard errors plus a small floor for the
        # asymptotic-correction sub-leading terms at z=2.5.
        tolerance = 3.0 * se + 0.01
        assert abs(empirical - predicted) <= tolerance

    def test_rejects_non_positive_n_trials(self) -> None:
        with pytest.raises(ValueError):
            monte_carlo_global_p_value(
                n_trials=0, n_grid_points=64, correlation_length=0.1,
            )

    def test_rejects_non_positive_correlation_length(self) -> None:
        with pytest.raises(ValueError):
            monte_carlo_global_p_value(
                n_trials=10, n_grid_points=64, correlation_length=-0.1,
            )

    def test_rejects_too_few_grid_points(self) -> None:
        with pytest.raises(ValueError):
            monte_carlo_global_p_value(
                n_trials=10, n_grid_points=1, correlation_length=0.1,
            )


# ----------------------------------------------------------------------------
# Integration with §1.A.SI.1 (sealed-box pre-registration)
# ----------------------------------------------------------------------------

class TestIntegrationWithSealedBox:
    """The two §1.A SI slices compose: the box (SI.1) pre-registers a
    parameter grid + decision threshold; the LEE trial factor (SI.2)
    predicts the false-discovery rate at that threshold given the
    grid's effective number of independent points."""

    def test_box_grid_size_drives_trial_factor_magnitude(self) -> None:
        """A larger parameter grid ⇒ more candidate combinations ⇒
        larger LEE correction. We don't claim a quantitative match
        between grid size and ⟨N(0)⟩ here (that requires the
        autocorrelation structure of the test statistic). We do
        claim that the closed-form trial factor at a given z scales
        monotonically with the assumed ⟨N(0)⟩, and that ⟨N(0)⟩ is
        upper-bounded by the number of grid points."""
        small_box = sealed_box(
            name="small",
            parameters=[
                BoxParameter("axis_a", values=tuple(range(3))),
                BoxParameter("axis_b", values=tuple(range(3))),
            ],
            signal_region=[(i, j) for i in range(3) for j in range(3)],
            control_region=[],
            decision_statistic="z",
            decision_threshold=3.0,
        )
        large_box = sealed_box(
            name="large",
            parameters=[
                BoxParameter("axis_a", values=tuple(range(8))),
                BoxParameter("axis_b", values=tuple(range(8))),
            ],
            signal_region=[(i, j) for i in range(8) for j in range(8)],
            control_region=[],
            decision_statistic="z",
            decision_threshold=3.0,
        )
        # Use grid-size as an upper bound on ⟨N(0)⟩ (loose proxy).
        small_n = float(len(small_box.signal_region))
        large_n = float(len(large_box.signal_region))
        z = small_box.decision_threshold
        small_tf = gross_vitells_trial_factor(z, small_n)
        large_tf = gross_vitells_trial_factor(z, large_n)
        assert large_tf > small_tf

    def test_placeholder_null_data_yields_calibrable_upcrossings(self) -> None:
        """Run the SI.1 placeholder generator over many seeds and
        confirm that the empirical Type-I rate at the box threshold
        is consistent with `p_local_one_sided(threshold)` (since the
        placeholder draws are independent). This test does NOT
        compose the full LEE correction — independent draws have
        ⟨N(c)⟩ = (n_grid_points − 1) * p_local(c) by design — but it
        verifies the placeholder generator's null distribution is
        what `p_local_one_sided` predicts."""
        box = sealed_box(
            name="independent_null",
            parameters=[BoxParameter("axis", values=tuple(range(20)))],
            signal_region=[(i,) for i in range(20)],
            control_region=[],
            decision_statistic="z",
            decision_threshold=2.0,
        )
        n_seeds = 2000
        threshold = box.decision_threshold
        false_positives = 0
        for seed in range(n_seeds):
            data = placeholder_data_generator(box, seed=seed)
            if any(v > threshold for v in data.values()):
                false_positives += 1
        # Expected: 1 - (1 - p_local(2))^20 — i.e., union bound on 20
        # independent N(0,1) draws each above z=2.
        p_local = p_local_one_sided(threshold)
        expected = 1.0 - (1.0 - p_local) ** len(box.signal_region)
        empirical = false_positives / n_seeds
        # Binomial std-error of empirical at this rate.
        se = math.sqrt(expected * (1 - expected) / n_seeds)
        assert abs(empirical - expected) <= 4.0 * se
