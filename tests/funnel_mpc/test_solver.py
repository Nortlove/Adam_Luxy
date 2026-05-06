"""Tests for the receding-horizon Funnel-MPC solver
(directive §1.E.SI.1)."""
from __future__ import annotations

import math

import numpy as np
import pytest

from adam.funnel_mpc import (
    FunnelMPCProblem,
    MPCSolveResult,
    PrescribedPerformanceEnvelope,
    simulate_receding_horizon,
    solve_mpc_step,
)


# ----------------------------------------------------------------------------
# Helpers — common problems for repeated use
# ----------------------------------------------------------------------------

def _scalar_regulator_problem(
    horizon: int = 5,
    *,
    decay: float = 0.9,
    control_lb: float = -1.0,
    control_ub: float = 1.0,
) -> FunnelMPCProblem:
    """Linear regulator: y_{k+1} = decay * y_k + u_k. Quadratic cost
    ℓ = y² + 0.1 u²; terminal V_f = y². Standard textbook problem
    with known optimal-feedback structure."""
    def dynamics(x, u, k):
        return decay * x + u

    def stage_cost(x, u, k):
        return float(x[0]**2 + 0.1 * u[0]**2)

    def terminal_cost(x):
        return float(x[0]**2)

    return FunnelMPCProblem(
        horizon=horizon,
        state_dim=1, control_dim=1,
        dynamics=dynamics,
        stage_cost=stage_cost,
        terminal_cost=terminal_cost,
        control_lower_bound=np.array([control_lb]),
        control_upper_bound=np.array([control_ub]),
    )


# ----------------------------------------------------------------------------
# Single-step solver
# ----------------------------------------------------------------------------

class TestSingleStep:
    def test_solver_returns_valid_result(self) -> None:
        prob = _scalar_regulator_problem(horizon=5)
        result = solve_mpc_step(prob, current_state=np.array([1.0]))
        assert isinstance(result, MPCSolveResult)
        assert result.optimal_control_sequence.shape == (5, 1)
        assert result.predicted_state_trajectory.shape == (6, 1)
        assert result.applied_control.shape == (1,)
        assert result.optimal_cost >= 0.0

    def test_solver_respects_control_bounds(self) -> None:
        prob = _scalar_regulator_problem(horizon=5)
        result = solve_mpc_step(prob, current_state=np.array([10.0]))
        u = result.optimal_control_sequence
        assert np.all(u >= -1.0 - 1e-8)
        assert np.all(u <= 1.0 + 1e-8)

    def test_zero_state_zero_control_is_optimal(self) -> None:
        """Starting at the origin, no disturbance, quadratic cost
        with no offsets — the optimal solution is u ≡ 0 with cost 0."""
        prob = _scalar_regulator_problem(horizon=5)
        result = solve_mpc_step(prob, current_state=np.array([0.0]))
        assert result.converged
        assert result.optimal_cost == pytest.approx(0.0, abs=1e-6)
        assert np.allclose(result.optimal_control_sequence, 0.0, atol=1e-4)

    def test_drives_state_toward_origin(self) -> None:
        """For a regulator problem with positive initial state,
        the optimal first control is negative (moves y toward 0
        against the dynamics' decay-toward-zero already in place)."""
        prob = _scalar_regulator_problem(horizon=5)
        result = solve_mpc_step(prob, current_state=np.array([1.0]))
        assert result.applied_control[0] < 0.0
        # Predicted trajectory monotonically decreases.
        traj = result.predicted_state_trajectory.flatten()
        for prior, current in zip(traj, traj[1:]):
            assert current < prior

    def test_warm_start_preserves_optimum(self) -> None:
        """Same problem, two different initial guesses — both should
        converge to the same optimal cost (problem is convex)."""
        prob = _scalar_regulator_problem(horizon=5)
        x0 = np.array([1.0])
        cold = solve_mpc_step(prob, current_state=x0, initial_guess=None)
        warm = solve_mpc_step(
            prob, current_state=x0,
            initial_guess=np.full((5, 1), -0.5),
        )
        assert cold.optimal_cost == pytest.approx(warm.optimal_cost, rel=1e-3)

    def test_rejects_bad_state_shape(self) -> None:
        prob = _scalar_regulator_problem(horizon=5)
        with pytest.raises(ValueError):
            solve_mpc_step(prob, current_state=np.array([1.0, 2.0]))

    def test_rejects_bad_initial_guess_shape(self) -> None:
        prob = _scalar_regulator_problem(horizon=5)
        with pytest.raises(ValueError):
            solve_mpc_step(
                prob, current_state=np.array([1.0]),
                initial_guess=np.zeros((4, 1)),  # horizon=5
            )


# ----------------------------------------------------------------------------
# Receding-horizon closed-loop simulation
# ----------------------------------------------------------------------------

class TestRecedingHorizon:
    def test_closed_loop_drives_to_origin(self) -> None:
        """Receding-horizon closed-loop should drive the state to
        the origin from any initial condition (linear-quadratic
        problem with stable open-loop dynamics; standard MPC
        textbook result)."""
        prob = _scalar_regulator_problem(horizon=10)
        traj, ctrls, results = simulate_receding_horizon(
            problem=prob,
            initial_state=np.array([2.0]),
            n_closed_loop_steps=20,
        )
        # Final state close to origin.
        assert abs(traj[-1, 0]) < 0.1
        # Trajectory shape correct.
        assert traj.shape == (21, 1)
        assert ctrls.shape == (20, 1)
        assert len(results) == 20
        # All steps converged.
        assert all(r.converged for r in results)

    def test_closed_loop_cost_decreases(self) -> None:
        """Lyapunov-style closed-loop monotonicity: stage cost
        evaluated on the closed-loop trajectory is non-increasing
        on average over the run (it can wobble step-to-step but
        the long-run trend is strictly decreasing for a stable
        regulator problem)."""
        prob = _scalar_regulator_problem(horizon=10)
        traj, ctrls, _ = simulate_receding_horizon(
            problem=prob,
            initial_state=np.array([2.0]),
            n_closed_loop_steps=30,
        )
        # Average over first 10 vs last 10 — decreasing.
        early_cost = np.mean(traj[:10, 0]**2)
        late_cost = np.mean(traj[-10:, 0]**2)
        assert late_cost < early_cost

    def test_warm_start_reaches_same_endpoint(self) -> None:
        """Warm-start vs cold-start should converge to similar
        closed-loop trajectories (problem is convex; warm-starting
        is an efficiency optimization, not a correctness change)."""
        prob = _scalar_regulator_problem(horizon=5)
        traj_warm, _, _ = simulate_receding_horizon(
            problem=prob, initial_state=np.array([1.0]),
            n_closed_loop_steps=15, warm_start=True,
        )
        traj_cold, _, _ = simulate_receding_horizon(
            problem=prob, initial_state=np.array([1.0]),
            n_closed_loop_steps=15, warm_start=False,
        )
        # Endpoints close.
        assert abs(traj_warm[-1, 0] - traj_cold[-1, 0]) < 0.01

    def test_disturbed_dynamics_recovered_by_closed_loop(self) -> None:
        """Open-loop trajectory under the optimal sequence diverges
        if the dynamics deviate; closed-loop receding-horizon
        absorbs the deviation. We simulate by injecting a one-time
        unmodeled state perturbation midway and verify the closed-
        loop state still reaches near-origin."""
        steps_until_kick = 5
        kick_magnitude = 0.5

        # We build a "true" dynamics that injects a kick at step 5;
        # the MPC's internal model is the unkicked dynamics.
        class _Dyn:
            def __init__(self):
                self.true_step = 0
            def __call__(self, x, u, k):
                # Internal model (used by MPC.rollout): no kick.
                return 0.9 * x + u

        dyn_obj = _Dyn()

        def true_dyn(x, u, k):
            x_next = 0.9 * x + u
            if k == steps_until_kick:
                x_next = x_next + kick_magnitude
            return x_next

        # Build the MPC problem with the model dynamics, but advance
        # the closed loop with the true dynamics by overriding the
        # `dynamics` attribute on a copy. Easiest way: build two
        # problems and simulate manually.
        model_prob = _scalar_regulator_problem(horizon=8)

        # Closed-loop simulation under true dynamics, MPC steps under
        # model dynamics.
        state = np.array([2.0])
        traj = [state.copy()]
        for t in range(20):
            r = solve_mpc_step(model_prob, current_state=state)
            applied = r.applied_control
            state = np.asarray(true_dyn(state, applied, t), dtype=float)
            traj.append(state.copy())
        # Despite the kick, closed-loop reaches near-origin.
        assert abs(traj[-1][0]) < 0.2

    def test_rejects_zero_steps(self) -> None:
        prob = _scalar_regulator_problem(horizon=3)
        with pytest.raises(ValueError):
            simulate_receding_horizon(
                problem=prob, initial_state=np.array([1.0]),
                n_closed_loop_steps=0,
            )


# ----------------------------------------------------------------------------
# Prescribed-performance envelope wired as a state constraint
# ----------------------------------------------------------------------------

class TestPrescribedPerformanceConstraint:
    """Compose the PPC envelope with FunnelMPCProblem.state_constraints
    — the canonical Funnel-MPC use case."""

    def _problem_with_envelope(
        self,
        envelope: PrescribedPerformanceEnvelope,
    ) -> FunnelMPCProblem:
        # State y, target trajectory y_target(k) = 0 ∀ k.
        # Tracking error e_k = y_target - y_k = -y_k.
        # PPC constraint: e_k ∈ (-δ_low(k), δ_high(k))
        # ⇔ -δ_low < -y_k < δ_high
        # ⇔ -δ_high < y_k < δ_low.
        # State constraint as g(x, k) ≤ 0:
        #   g_upper(x, k) = y - δ_low(k)  ≤ 0   (y < δ_low(k))
        #   g_lower(x, k) = -y - δ_high(k) ≤ 0  (-y < δ_high(k))
        def upper(x, k):
            return float(x[0]) - envelope.lower_bound(float(k))

        def lower(x, k):
            return -float(x[0]) - envelope.upper_bound(float(k))

        def dynamics(x, u, k):
            return 0.9 * x + u

        def stage_cost(x, u, k):
            return float(x[0]**2 + 0.1 * u[0]**2)

        def terminal_cost(x):
            return float(x[0]**2)

        return FunnelMPCProblem(
            horizon=8,
            state_dim=1, control_dim=1,
            dynamics=dynamics,
            stage_cost=stage_cost,
            terminal_cost=terminal_cost,
            control_lower_bound=np.array([-2.0]),
            control_upper_bound=np.array([2.0]),
            state_constraints=[upper, lower],
        )

    def test_loose_envelope_does_not_bind(self) -> None:
        """Wide envelope ⇒ MPC behaves as if unconstrained."""
        envelope = PrescribedPerformanceEnvelope(
            rho_initial=10.0, rho_terminal=10.0, decay_rate=0.1,
            upper_multiplier=1.0, lower_multiplier=1.0,
        )
        prob = self._problem_with_envelope(envelope)
        unconstrained = _scalar_regulator_problem(
            horizon=8, control_lb=-2.0, control_ub=2.0,
        )
        result_constrained = solve_mpc_step(
            prob, current_state=np.array([1.0]),
        )
        result_unconstrained = solve_mpc_step(
            unconstrained, current_state=np.array([1.0]),
        )
        # Cost similar (within solver tolerance); envelope inactive.
        assert result_constrained.optimal_cost == pytest.approx(
            result_unconstrained.optimal_cost, rel=1e-2,
        )

    def test_envelope_is_satisfied_in_predicted_trajectory(self) -> None:
        """A loose-but-non-trivial envelope should be satisfied by
        the predicted trajectory."""
        envelope = PrescribedPerformanceEnvelope(
            rho_initial=2.0, rho_terminal=0.5, decay_rate=0.5,
            upper_multiplier=1.0, lower_multiplier=1.0,
        )
        prob = self._problem_with_envelope(envelope)
        result = solve_mpc_step(prob, current_state=np.array([1.0]))
        # Verify the predicted trajectory satisfies envelope at each k.
        for k in range(prob.horizon + 1):
            y_k = float(result.predicted_state_trajectory[k, 0])
            e_k = -y_k  # target = 0
            assert envelope.contains(e_k, t=float(k)) or \
                math.isclose(e_k, envelope.upper_bound(float(k)), abs_tol=1e-6) or \
                math.isclose(e_k, -envelope.lower_bound(float(k)), abs_tol=1e-6)
