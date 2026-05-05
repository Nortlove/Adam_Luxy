"""Tests for the Dayneka-Garg-Jusko four basic IRM variants
(directive §1.F.SI.1)."""
from __future__ import annotations

import math

import numpy as np
import pytest

from adam.pkpd import (
    IndirectResponseModel,
    IndirectResponseParams,
    IndirectResponseTrajectory,
    analytical_steady_state,
    simulate_indirect_response,
)


# ----------------------------------------------------------------------------
# Param invariants
# ----------------------------------------------------------------------------

class TestParamInvariants:
    def test_basic_construction(self) -> None:
        p = IndirectResponseParams(
            model=IndirectResponseModel.INHIBIT_INPUT,
            k_in=10.0, k_out=2.0,
            magnitude=0.5, half_concentration=1.0,
        )
        assert p.k_in == 10.0
        assert p.hill_coefficient == 1.0  # Default

    def test_rejects_non_positive_k_in(self) -> None:
        with pytest.raises(ValueError):
            IndirectResponseParams(
                model=IndirectResponseModel.INHIBIT_INPUT,
                k_in=0.0, k_out=2.0,
                magnitude=0.5, half_concentration=1.0,
            )

    def test_rejects_non_positive_k_out(self) -> None:
        with pytest.raises(ValueError):
            IndirectResponseParams(
                model=IndirectResponseModel.INHIBIT_INPUT,
                k_in=2.0, k_out=-1.0,
                magnitude=0.5, half_concentration=1.0,
            )

    def test_inhibition_magnitude_must_be_in_unit_interval(self) -> None:
        with pytest.raises(ValueError):
            IndirectResponseParams(
                model=IndirectResponseModel.INHIBIT_INPUT,
                k_in=2.0, k_out=1.0,
                magnitude=1.5, half_concentration=1.0,
            )
        with pytest.raises(ValueError):
            IndirectResponseParams(
                model=IndirectResponseModel.INHIBIT_OUTPUT,
                k_in=2.0, k_out=1.0,
                magnitude=-0.1, half_concentration=1.0,
            )

    def test_inhibit_output_full_inhibition_rejected(self) -> None:
        """I_max=1.0 on Model II would yield k_in / 0 = ∞ at saturating c.
        Reject at construction time."""
        with pytest.raises(ValueError):
            IndirectResponseParams(
                model=IndirectResponseModel.INHIBIT_OUTPUT,
                k_in=2.0, k_out=1.0,
                magnitude=1.0, half_concentration=1.0,
            )

    def test_stimulation_magnitude_must_be_non_negative(self) -> None:
        with pytest.raises(ValueError):
            IndirectResponseParams(
                model=IndirectResponseModel.STIMULATE_INPUT,
                k_in=2.0, k_out=1.0,
                magnitude=-0.1, half_concentration=1.0,
            )


# ----------------------------------------------------------------------------
# Analytical steady states
# ----------------------------------------------------------------------------

class TestAnalyticalSteadyState:
    def test_baseline_is_kin_over_kout(self) -> None:
        """Eq. (1) of the module: at c=0, all four models reduce to
        the same dR/dt = k_in - k_out * R, with steady state k_in / k_out."""
        for model in IndirectResponseModel:
            params = IndirectResponseParams(
                model=model, k_in=10.0, k_out=2.5,
                magnitude=0.4, half_concentration=1.0,
            )
            assert analytical_steady_state(params, saturating=False) == \
                pytest.approx(10.0 / 2.5, rel=1e-12)

    def test_inhibit_input_saturating(self) -> None:
        params = IndirectResponseParams(
            model=IndirectResponseModel.INHIBIT_INPUT,
            k_in=10.0, k_out=2.0,
            magnitude=0.7, half_concentration=1.0,
        )
        # k_in * (1 - I_max) / k_out
        assert analytical_steady_state(params) == pytest.approx(
            10.0 * 0.3 / 2.0, rel=1e-12,
        )

    def test_inhibit_output_saturating(self) -> None:
        params = IndirectResponseParams(
            model=IndirectResponseModel.INHIBIT_OUTPUT,
            k_in=10.0, k_out=2.0,
            magnitude=0.5, half_concentration=1.0,
        )
        # k_in / (k_out * (1 - I_max))
        assert analytical_steady_state(params) == pytest.approx(
            10.0 / (2.0 * 0.5), rel=1e-12,
        )

    def test_stimulate_input_saturating(self) -> None:
        params = IndirectResponseParams(
            model=IndirectResponseModel.STIMULATE_INPUT,
            k_in=10.0, k_out=2.0,
            magnitude=2.0, half_concentration=1.0,
        )
        # k_in * (1 + S_max) / k_out
        assert analytical_steady_state(params) == pytest.approx(
            10.0 * 3.0 / 2.0, rel=1e-12,
        )

    def test_stimulate_output_saturating(self) -> None:
        params = IndirectResponseParams(
            model=IndirectResponseModel.STIMULATE_OUTPUT,
            k_in=10.0, k_out=2.0,
            magnitude=2.0, half_concentration=1.0,
        )
        # k_in / (k_out * (1 + S_max))
        assert analytical_steady_state(params) == pytest.approx(
            10.0 / (2.0 * 3.0), rel=1e-12,
        )


# ----------------------------------------------------------------------------
# Numerical integration cross-checks
# ----------------------------------------------------------------------------

class TestSimulateNoDrug:
    """At c(t) ≡ 0 the trajectory should equilibrate at k_in / k_out
    regardless of the model variant."""

    @pytest.mark.parametrize("model", list(IndirectResponseModel))
    def test_no_drug_trajectory_holds_baseline(
        self, model: IndirectResponseModel,
    ) -> None:
        # All models behave identically when c=0; magnitude is irrelevant.
        magnitude = 0.5 if model in (
            IndirectResponseModel.INHIBIT_INPUT,
            IndirectResponseModel.INHIBIT_OUTPUT,
        ) else 2.0
        params = IndirectResponseParams(
            model=model, k_in=10.0, k_out=2.5,
            magnitude=magnitude, half_concentration=1.0,
        )
        times = tuple(np.linspace(0.0, 50.0, 21))
        traj = simulate_indirect_response(
            params=params,
            times=times,
            concentration_fn=lambda t: 0.0,
        )
        baseline = params.k_in / params.k_out
        for r in traj.response:
            assert r == pytest.approx(baseline, rel=1e-6)


class TestSimulateConvergence:
    """Under sustained-saturating concentration, the trajectory should
    converge to the analytical steady state computed by
    `analytical_steady_state`."""

    @pytest.mark.parametrize("model", list(IndirectResponseModel))
    def test_saturating_concentration_converges_to_analytical(
        self, model: IndirectResponseModel,
    ) -> None:
        magnitude = 0.6 if model in (
            IndirectResponseModel.INHIBIT_INPUT,
            IndirectResponseModel.INHIBIT_OUTPUT,
        ) else 1.5
        params = IndirectResponseParams(
            model=model, k_in=10.0, k_out=2.0,
            magnitude=magnitude, half_concentration=1.0,
        )
        # Long simulation time → t > 5 / k_out ensures equilibration.
        times = tuple(np.linspace(0.0, 50.0, 101))
        traj = simulate_indirect_response(
            params=params,
            times=times,
            # 1e6 * IC_50 → effectively at saturation.
            concentration_fn=lambda t: 1.0e6,
        )
        analytical = analytical_steady_state(params, saturating=True)
        # Numerical → analytical match within ~1e-4 relative when c
        # is 6 orders of magnitude above IC_50.
        assert traj.response[-1] == pytest.approx(analytical, rel=1e-4)


class TestSimulationEdgeCases:
    def test_initial_response_overrides_default_baseline(self) -> None:
        params = IndirectResponseParams(
            model=IndirectResponseModel.INHIBIT_INPUT,
            k_in=10.0, k_out=2.0,
            magnitude=0.0,  # No drug effect even with c>0.
            half_concentration=1.0,
        )
        # Start at 2x baseline; with no drug effect, decays back to baseline.
        traj = simulate_indirect_response(
            params=params,
            times=tuple(np.linspace(0.0, 30.0, 31)),
            concentration_fn=lambda t: 0.0,
            initial_response=10.0,
        )
        baseline = params.k_in / params.k_out
        assert traj.response[0] == pytest.approx(10.0, rel=1e-12)
        assert traj.response[-1] == pytest.approx(baseline, rel=1e-3)
        # Trajectory monotonically decreasing toward baseline.
        for prior, current in zip(traj.response, traj.response[1:]):
            assert current <= prior + 1e-6

    def test_rejects_too_few_times(self) -> None:
        params = IndirectResponseParams(
            model=IndirectResponseModel.INHIBIT_INPUT,
            k_in=2.0, k_out=1.0,
            magnitude=0.3, half_concentration=1.0,
        )
        with pytest.raises(ValueError):
            simulate_indirect_response(
                params=params,
                times=(0.0,),
                concentration_fn=lambda t: 0.0,
            )

    def test_rejects_non_monotonic_times(self) -> None:
        params = IndirectResponseParams(
            model=IndirectResponseModel.INHIBIT_INPUT,
            k_in=2.0, k_out=1.0,
            magnitude=0.3, half_concentration=1.0,
        )
        with pytest.raises(ValueError):
            simulate_indirect_response(
                params=params,
                times=(0.0, 1.0, 0.5, 2.0),
                concentration_fn=lambda t: 0.0,
            )

    def test_rejects_negative_initial_response(self) -> None:
        params = IndirectResponseParams(
            model=IndirectResponseModel.INHIBIT_INPUT,
            k_in=2.0, k_out=1.0,
            magnitude=0.3, half_concentration=1.0,
        )
        with pytest.raises(ValueError):
            simulate_indirect_response(
                params=params,
                times=(0.0, 1.0),
                concentration_fn=lambda t: 0.0,
                initial_response=-1.0,
            )

    def test_rejects_negative_concentration(self) -> None:
        params = IndirectResponseParams(
            model=IndirectResponseModel.INHIBIT_INPUT,
            k_in=2.0, k_out=1.0,
            magnitude=0.3, half_concentration=1.0,
        )
        with pytest.raises((ValueError, RuntimeError)):
            simulate_indirect_response(
                params=params,
                times=(0.0, 1.0, 2.0),
                concentration_fn=lambda t: -1.0,
            )


class TestModelDifferentiation:
    """The four models predict qualitatively different responses under
    the same drug input. These tests pin the qualitative ordering."""

    def test_inhibit_input_drives_response_below_baseline(self) -> None:
        params = IndirectResponseParams(
            model=IndirectResponseModel.INHIBIT_INPUT,
            k_in=10.0, k_out=2.0,
            magnitude=0.5, half_concentration=1.0,
        )
        baseline = params.k_in / params.k_out
        traj = simulate_indirect_response(
            params=params,
            times=tuple(np.linspace(0.0, 30.0, 31)),
            concentration_fn=lambda t: 100.0,  # Saturating.
        )
        assert traj.response[-1] < baseline

    def test_stimulate_input_drives_response_above_baseline(self) -> None:
        params = IndirectResponseParams(
            model=IndirectResponseModel.STIMULATE_INPUT,
            k_in=10.0, k_out=2.0,
            magnitude=2.0, half_concentration=1.0,
        )
        baseline = params.k_in / params.k_out
        traj = simulate_indirect_response(
            params=params,
            times=tuple(np.linspace(0.0, 30.0, 31)),
            concentration_fn=lambda t: 100.0,
        )
        assert traj.response[-1] > baseline

    def test_inhibit_output_drives_response_above_baseline(self) -> None:
        """Inhibiting elimination raises steady state."""
        params = IndirectResponseParams(
            model=IndirectResponseModel.INHIBIT_OUTPUT,
            k_in=10.0, k_out=2.0,
            magnitude=0.5, half_concentration=1.0,
        )
        baseline = params.k_in / params.k_out
        traj = simulate_indirect_response(
            params=params,
            times=tuple(np.linspace(0.0, 30.0, 31)),
            concentration_fn=lambda t: 100.0,
        )
        assert traj.response[-1] > baseline

    def test_stimulate_output_drives_response_below_baseline(self) -> None:
        """Stimulating elimination lowers steady state."""
        params = IndirectResponseParams(
            model=IndirectResponseModel.STIMULATE_OUTPUT,
            k_in=10.0, k_out=2.0,
            magnitude=2.0, half_concentration=1.0,
        )
        baseline = params.k_in / params.k_out
        traj = simulate_indirect_response(
            params=params,
            times=tuple(np.linspace(0.0, 30.0, 31)),
            concentration_fn=lambda t: 100.0,
        )
        assert traj.response[-1] < baseline


class TestTimeVaryingConcentration:
    """The IRM family's distinguishing feature is the DELAY between
    drug-concentration changes and response changes. Test that an
    instantaneous drop in c(t) does not produce an instantaneous drop
    in R(t)."""

    def test_response_lags_concentration_step_off(self) -> None:
        """Equilibrate at saturating c, then drop c → 0 at t=15. R(t)
        should NOT instantaneously return to baseline; it decays at
        rate ~k_out."""
        params = IndirectResponseParams(
            model=IndirectResponseModel.STIMULATE_INPUT,
            k_in=10.0, k_out=0.5,  # slow elimination → strong delay
            magnitude=2.0, half_concentration=1.0,
        )

        def concentration(t: float) -> float:
            return 1.0e6 if t < 15.0 else 0.0

        baseline = params.k_in / params.k_out
        elevated = analytical_steady_state(params, saturating=True)
        # Equilibrate at elevated for t < 15; sample shortly after the
        # step-off; the response should still be well above baseline.
        traj = simulate_indirect_response(
            params=params,
            times=(0.0, 14.0, 15.5, 30.0),
            concentration_fn=concentration,
        )
        # By t=14 we should be at the elevated steady state. With
        # k_out=0.5 → time constant 2; t=14 is 7 time constants
        # → e^-7 ≈ 0.001 residual error from fully-equilibrated.
        assert traj.response[1] == pytest.approx(elevated, rel=1e-2)
        # By t=15.5 (0.5 time units after step-off, k_out=0.5 → time
        # constant 2 units) — response should still be much closer to
        # elevated than to baseline.
        decayed = traj.response[2]
        assert decayed > baseline
        assert decayed > 0.5 * elevated
        # By t=30 (15 time units after step-off → ~7.5 time constants)
        # response should be nearly back to baseline.
        assert traj.response[3] == pytest.approx(baseline, rel=1e-2)
