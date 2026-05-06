"""Tests for Funnel-MPC formulation primitives (directive §1.E.SI.1)."""
from __future__ import annotations

import math

import numpy as np
import pytest

from adam.funnel_mpc import (
    FunnelMPCProblem,
    PrescribedPerformanceEnvelope,
)


# ----------------------------------------------------------------------------
# Prescribed-performance envelope (Bechlioulis & Rovithakis 2008)
# ----------------------------------------------------------------------------

class TestEnvelopeAnchors:
    def test_rho_at_zero_equals_rho_initial(self) -> None:
        env = PrescribedPerformanceEnvelope(
            rho_initial=2.0, rho_terminal=0.5, decay_rate=1.0,
            upper_multiplier=1.0, lower_multiplier=1.0,
        )
        assert env.rho(0.0) == pytest.approx(2.0, rel=1e-12)

    def test_rho_at_infinity_approaches_rho_terminal(self) -> None:
        env = PrescribedPerformanceEnvelope(
            rho_initial=2.0, rho_terminal=0.5, decay_rate=1.0,
            upper_multiplier=1.0, lower_multiplier=1.0,
        )
        # 100 / λ time constants → numerically saturated.
        assert env.rho(100.0) == pytest.approx(0.5, abs=1e-12)

    def test_rho_decreases_monotonically(self) -> None:
        env = PrescribedPerformanceEnvelope(
            rho_initial=3.0, rho_terminal=0.1, decay_rate=0.5,
            upper_multiplier=1.0, lower_multiplier=1.0,
        )
        ts = [0.0, 0.5, 1.0, 2.0, 5.0, 10.0]
        rhos = [env.rho(t) for t in ts]
        for prior, current in zip(rhos, rhos[1:]):
            assert current < prior

    def test_decay_rate_controls_speed(self) -> None:
        """Larger decay rate ⇒ envelope reaches rho_terminal faster."""
        slow = PrescribedPerformanceEnvelope(
            rho_initial=2.0, rho_terminal=0.0, decay_rate=0.1,
            upper_multiplier=1.0, lower_multiplier=1.0,
        )
        fast = PrescribedPerformanceEnvelope(
            rho_initial=2.0, rho_terminal=0.0, decay_rate=5.0,
            upper_multiplier=1.0, lower_multiplier=1.0,
        )
        # At t=2, fast envelope is much closer to 0 than slow.
        assert fast.rho(2.0) < slow.rho(2.0)


class TestEnvelopeBounds:
    def test_upper_lower_scale_by_multipliers(self) -> None:
        env = PrescribedPerformanceEnvelope(
            rho_initial=2.0, rho_terminal=0.5, decay_rate=1.0,
            upper_multiplier=1.5, lower_multiplier=0.8,
        )
        rho_t = env.rho(0.5)
        assert env.upper_bound(0.5) == pytest.approx(1.5 * rho_t, rel=1e-12)
        assert env.lower_bound(0.5) == pytest.approx(0.8 * rho_t, rel=1e-12)

    def test_contains_strict_interior(self) -> None:
        env = PrescribedPerformanceEnvelope(
            rho_initial=1.0, rho_terminal=0.0, decay_rate=1.0,
            upper_multiplier=1.0, lower_multiplier=1.0,
        )
        # At t=0, envelope is (-1, 1).
        assert env.contains(0.0, t=0.0)
        assert env.contains(0.5, t=0.0)
        assert env.contains(-0.5, t=0.0)
        # Boundary is strict per Bechlioulis-Rovithakis (open set).
        assert not env.contains(1.0, t=0.0)
        assert not env.contains(-1.0, t=0.0)
        assert not env.contains(2.0, t=0.0)

    def test_asymmetric_multipliers(self) -> None:
        """upper_multiplier ≠ lower_multiplier → asymmetric envelope.
        Useful when over-shooting and under-shooting the target have
        different costs."""
        env = PrescribedPerformanceEnvelope(
            rho_initial=1.0, rho_terminal=1.0, decay_rate=1.0,
            upper_multiplier=2.0, lower_multiplier=0.5,
        )
        # Envelope at any t: (-0.5, 2.0).
        assert env.contains(1.5, t=0.0)
        assert env.contains(-0.4, t=0.0)
        assert not env.contains(2.5, t=0.0)
        assert not env.contains(-0.6, t=0.0)


class TestEnvelopeValidation:
    def test_rejects_non_positive_rho_initial(self) -> None:
        with pytest.raises(ValueError):
            PrescribedPerformanceEnvelope(
                rho_initial=0.0, rho_terminal=0.0, decay_rate=1.0,
                upper_multiplier=1.0, lower_multiplier=1.0,
            )

    def test_rejects_negative_rho_terminal(self) -> None:
        with pytest.raises(ValueError):
            PrescribedPerformanceEnvelope(
                rho_initial=1.0, rho_terminal=-0.1, decay_rate=1.0,
                upper_multiplier=1.0, lower_multiplier=1.0,
            )

    def test_rejects_terminal_above_initial(self) -> None:
        """The envelope is non-increasing — rho_terminal can't exceed
        rho_initial."""
        with pytest.raises(ValueError):
            PrescribedPerformanceEnvelope(
                rho_initial=0.5, rho_terminal=1.0, decay_rate=1.0,
                upper_multiplier=1.0, lower_multiplier=1.0,
            )

    def test_rejects_non_positive_decay_rate(self) -> None:
        with pytest.raises(ValueError):
            PrescribedPerformanceEnvelope(
                rho_initial=1.0, rho_terminal=0.0, decay_rate=0.0,
                upper_multiplier=1.0, lower_multiplier=1.0,
            )

    def test_rejects_negative_multipliers(self) -> None:
        with pytest.raises(ValueError):
            PrescribedPerformanceEnvelope(
                rho_initial=1.0, rho_terminal=0.0, decay_rate=1.0,
                upper_multiplier=-0.1, lower_multiplier=1.0,
            )

    def test_rejects_both_multipliers_zero(self) -> None:
        """Degenerate envelope (width zero) is rejected."""
        with pytest.raises(ValueError):
            PrescribedPerformanceEnvelope(
                rho_initial=1.0, rho_terminal=0.0, decay_rate=1.0,
                upper_multiplier=0.0, lower_multiplier=0.0,
            )

    def test_rejects_negative_t(self) -> None:
        env = PrescribedPerformanceEnvelope(
            rho_initial=1.0, rho_terminal=0.0, decay_rate=1.0,
            upper_multiplier=1.0, lower_multiplier=1.0,
        )
        with pytest.raises(ValueError):
            env.rho(-1.0)


# ----------------------------------------------------------------------------
# Funnel-MPC problem formulation (Camacho & Bordons 2007)
# ----------------------------------------------------------------------------

def _make_simple_linear_problem(
    horizon: int = 5,
) -> FunnelMPCProblem:
    """A simple linear-quadratic MPC problem for testing.

    State: scalar y; control: scalar u.
    Dynamics: y_{k+1} = 0.9 * y_k + u_k.
    Stage cost: y_k² + 0.1 * u_k².
    Terminal cost: y_N².
    Control bounded in [-1, 1].
    """
    def dynamics(x, u, k):
        return 0.9 * x + u

    def stage_cost(x, u, k):
        return float(x[0]**2 + 0.1 * u[0]**2)

    def terminal_cost(x):
        return float(x[0]**2)

    return FunnelMPCProblem(
        horizon=horizon,
        state_dim=1,
        control_dim=1,
        dynamics=dynamics,
        stage_cost=stage_cost,
        terminal_cost=terminal_cost,
        control_lower_bound=np.array([-1.0]),
        control_upper_bound=np.array([1.0]),
    )


class TestProblemConstruction:
    def test_basic_construction(self) -> None:
        prob = _make_simple_linear_problem(horizon=5)
        assert prob.horizon == 5
        assert prob.state_dim == 1
        assert prob.control_dim == 1

    def test_rejects_non_positive_horizon(self) -> None:
        with pytest.raises(ValueError):
            FunnelMPCProblem(
                horizon=0, state_dim=1, control_dim=1,
                dynamics=lambda x, u, k: x,
                stage_cost=lambda x, u, k: 0.0,
                terminal_cost=lambda x: 0.0,
                control_lower_bound=np.array([0.0]),
                control_upper_bound=np.array([1.0]),
            )

    def test_rejects_lb_above_ub(self) -> None:
        with pytest.raises(ValueError):
            FunnelMPCProblem(
                horizon=3, state_dim=1, control_dim=1,
                dynamics=lambda x, u, k: x,
                stage_cost=lambda x, u, k: 0.0,
                terminal_cost=lambda x: 0.0,
                control_lower_bound=np.array([1.0]),
                control_upper_bound=np.array([0.0]),
            )

    def test_rejects_bound_shape_mismatch(self) -> None:
        with pytest.raises(ValueError):
            FunnelMPCProblem(
                horizon=3, state_dim=1, control_dim=2,
                dynamics=lambda x, u, k: x,
                stage_cost=lambda x, u, k: 0.0,
                terminal_cost=lambda x: 0.0,
                control_lower_bound=np.array([0.0]),  # only 1 element
                control_upper_bound=np.array([1.0, 1.0]),
            )


class TestRolloutAndCost:
    def test_rollout_shape(self) -> None:
        prob = _make_simple_linear_problem(horizon=5)
        u_seq = np.zeros((5, 1))
        traj = prob.rollout(np.array([1.0]), u_seq)
        assert traj.shape == (6, 1)
        assert traj[0, 0] == 1.0

    def test_rollout_zero_control_decays_at_dynamics_rate(self) -> None:
        """Dynamics y_{k+1} = 0.9 y_k with u=0 → y_k = 0.9^k * y_0."""
        prob = _make_simple_linear_problem(horizon=5)
        u_seq = np.zeros((5, 1))
        traj = prob.rollout(np.array([1.0]), u_seq)
        for k in range(6):
            assert traj[k, 0] == pytest.approx(0.9**k, rel=1e-12)

    def test_rollout_constant_control(self) -> None:
        """y_{k+1} = 0.9 y_k + u with u=0.5, y_0=0 yields the
        geometric series 0.5 * (1 - 0.9^k) / (1 - 0.9)."""
        prob = _make_simple_linear_problem(horizon=4)
        u_seq = np.full((4, 1), 0.5)
        traj = prob.rollout(np.array([0.0]), u_seq)
        for k in range(5):
            expected = 0.5 * (1.0 - 0.9**k) / (1.0 - 0.9)
            assert traj[k, 0] == pytest.approx(expected, rel=1e-12)

    def test_cost_zero_state_zero_control(self) -> None:
        prob = _make_simple_linear_problem(horizon=5)
        u_seq = np.zeros((5, 1))
        # Zero state, zero control → zero cost (quadratic, no offsets).
        cost = prob.cost(np.array([0.0]), u_seq)
        assert cost == pytest.approx(0.0, abs=1e-12)

    def test_cost_includes_terminal(self) -> None:
        """Build a problem where ℓ ≡ 0 — only V_f contributes."""
        def dynamics(x, u, k):
            return x + u
        def zero(x, u, k):
            return 0.0
        def terminal(x):
            return float(x[0]**2)
        prob = FunnelMPCProblem(
            horizon=3, state_dim=1, control_dim=1,
            dynamics=dynamics,
            stage_cost=zero,
            terminal_cost=terminal,
            control_lower_bound=np.array([-10.0]),
            control_upper_bound=np.array([10.0]),
        )
        u_seq = np.array([[1.0], [1.0], [1.0]])
        # Trajectory: 0 → 1 → 2 → 3. Terminal cost: 9. Stage cost: 0.
        cost = prob.cost(np.array([0.0]), u_seq)
        assert cost == pytest.approx(9.0, rel=1e-12)

    def test_rollout_rejects_bad_initial_shape(self) -> None:
        prob = _make_simple_linear_problem(horizon=3)
        with pytest.raises(ValueError):
            prob.rollout(np.array([1.0, 2.0]), np.zeros((3, 1)))

    def test_rollout_rejects_bad_control_shape(self) -> None:
        prob = _make_simple_linear_problem(horizon=3)
        with pytest.raises(ValueError):
            prob.rollout(np.array([0.0]), np.zeros((4, 1)))
