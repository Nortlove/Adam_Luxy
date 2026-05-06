"""Receding-horizon Funnel-MPC solver (directive §1.E.SI.1).

Implements the canonical receding-horizon principle (Camacho &
Bordons 2007, *Model Predictive Control*, Springer 2nd ed., Ch. 2):

  1. At each closed-loop step t, given the current state x_t, solve
     the finite-horizon optimal control problem of length N over a
     candidate control sequence (u_0, u_1, ..., u_{N-1}).
  2. Apply only the first control u_0 to the system.
  3. Advance the system state by one step.
  4. Repeat from (1) at t+1 with the new state.

The "receding" aspect is what gives MPC its closed-loop robustness
to disturbances: re-optimizing at every step lets the controller
correct for any unmodeled deviations as they accumulate.

The single-step optimizer is `scipy.optimize.minimize` with the
SLSQP method (Sequential Least-SQuares Programming) — the
default-good choice for nonlinear-objective + nonlinear-inequality-
constraint problems with bound constraints. State-inequality
constraints from `FunnelMPCProblem.state_constraints` are passed
through as `inequality` constraints; the prescribed-performance
envelope (`PrescribedPerformanceEnvelope.contains`) is the
canonical instance and composes here as a state-constraint factory
the consumer constructs.

Numerical-method note: SLSQP uses a finite-difference Jacobian by
default, which is reliable but slow for high-dimensional control
horizons. For Funnel-MPC's typical horizon size (N ~ 5–20) the
finite-difference cost is acceptable. Faster differentiation (e.g.,
JAX-based) is a future-stage concern not in scope for SI.1.

Stability of the closed-loop receding-horizon system follows
Mayne, Rawlings, Rao & Scokaert 2000, *Automatica* 36:789–814 — the
terminal cost V_f and terminal constraint set must be a control-
Lyapunov function and a corresponding positively-invariant set under
the local terminal controller. The SI primitive does not enforce
that pair as a runtime invariant; the consumer's choice of (V_f,
terminal set) is what determines closed-loop stability.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
from scipy.optimize import Bounds, minimize

from adam.funnel_mpc.formulation import FunnelMPCProblem


__all__ = [
    "MPCSolveResult",
    "simulate_receding_horizon",
    "solve_mpc_step",
]


@dataclass(frozen=True)
class MPCSolveResult:
    """Outcome of one finite-horizon optimization.

    `optimal_control_sequence` has shape (horizon, control_dim);
    `predicted_state_trajectory` has shape (horizon + 1, state_dim).
    `applied_control` is the first control u_0 of the optimal
    sequence — the receding-horizon principle says this is what the
    closed-loop applies.
    """
    optimal_control_sequence: np.ndarray
    predicted_state_trajectory: np.ndarray
    applied_control: np.ndarray
    optimal_cost: float
    converged: bool
    n_iterations: int
    solver_message: str


def solve_mpc_step(
    problem: FunnelMPCProblem,
    current_state: np.ndarray,
    *,
    initial_guess: Optional[np.ndarray] = None,
    max_iter: int = 200,
    tolerance: float = 1e-6,
) -> MPCSolveResult:
    """Solve one finite-horizon optimization step (eqs. 3–4 of
    `formulation.py`).

    Parameters
    ----------
    problem
        Funnel-MPC problem definition.
    current_state
        x_t — initial state for this step.
    initial_guess
        Initial guess for the control sequence. Shape
        (horizon, control_dim). Defaults to the elementwise mean of
        the bounds (a stable, feasible warm-start).
    max_iter
        SLSQP iteration cap.
    tolerance
        SLSQP convergence tolerance.

    Returns
    -------
    MPCSolveResult with the optimal control sequence, predicted
    trajectory, the receding-horizon control u_0, and convergence
    diagnostics.
    """
    x0 = np.asarray(current_state, dtype=float)
    if x0.shape != (problem.state_dim,):
        raise ValueError(
            f"current_state must have shape ({problem.state_dim},), "
            f"got {x0.shape}"
        )

    n = problem.horizon
    m = problem.control_dim
    lb = np.asarray(problem.control_lower_bound, dtype=float)
    ub = np.asarray(problem.control_upper_bound, dtype=float)

    if initial_guess is None:
        u0_per_step = 0.5 * (lb + ub)
        u_init = np.tile(u0_per_step, (n, 1))
    else:
        u_init = np.asarray(initial_guess, dtype=float)
        if u_init.shape != (n, m):
            raise ValueError(
                f"initial_guess must have shape ({n}, {m}), "
                f"got {u_init.shape}"
            )

    # Objective: total cost as a function of the flattened control.
    def objective(u_flat: np.ndarray) -> float:
        u_seq = u_flat.reshape((n, m))
        return problem.cost(x0, u_seq)

    # Bounds on the flattened control.
    flat_lb = np.tile(lb, n)
    flat_ub = np.tile(ub, n)
    bounds = Bounds(flat_lb, flat_ub)

    # State-inequality constraints — SLSQP wants ≥ 0 for inequality
    # type, but our convention is g_i(x, k) ≤ 0; convert by negation.
    constraints = []
    if problem.state_constraints:
        # One scalar constraint function per (constraint, stage) pair.
        for state_constraint in problem.state_constraints:
            for k in range(n + 1):  # x_0, x_1, ..., x_N
                def _make(sc, k):
                    def fn(u_flat):
                        traj = problem.rollout(x0, u_flat.reshape((n, m)))
                        return -float(sc(traj[k], k))
                    return fn
                constraints.append({
                    "type": "ineq",
                    "fun": _make(state_constraint, k),
                })

    sol = minimize(
        fun=objective,
        x0=u_init.ravel(),
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": max_iter, "ftol": tolerance, "disp": False},
    )

    optimal_control_sequence = sol.x.reshape((n, m))
    predicted_trajectory = problem.rollout(x0, optimal_control_sequence)
    applied_control = optimal_control_sequence[0].copy()

    return MPCSolveResult(
        optimal_control_sequence=optimal_control_sequence,
        predicted_state_trajectory=predicted_trajectory,
        applied_control=applied_control,
        optimal_cost=float(sol.fun),
        converged=bool(sol.success),
        n_iterations=int(getattr(sol, "nit", -1)),
        solver_message=str(sol.message),
    )


def simulate_receding_horizon(
    problem: FunnelMPCProblem,
    initial_state: np.ndarray,
    n_closed_loop_steps: int,
    *,
    max_iter: int = 200,
    tolerance: float = 1e-6,
    warm_start: bool = True,
) -> Tuple[np.ndarray, np.ndarray, list]:
    """Closed-loop simulation: at each of `n_closed_loop_steps`
    steps, solve the MPC step, apply u_0, advance the state.

    Parameters
    ----------
    problem
        Funnel-MPC problem definition.
    initial_state
        x_0 — closed-loop initial condition.
    n_closed_loop_steps
        Number of receding-horizon iterations to run.
    max_iter, tolerance
        Forwarded to `solve_mpc_step`.
    warm_start
        If True, use the previous step's optimal sequence (shifted
        by one stage) as the warm-start guess for the next step —
        the canonical MPC warm-start that accelerates convergence
        on slowly-varying problems. If False, defaults to the
        bound-midpoint initial guess at each step.

    Returns
    -------
    state_trajectory : ndarray of shape (n_closed_loop_steps + 1, state_dim)
        Closed-loop state evolution x_0, x_1, ..., x_T.
    control_trajectory : ndarray of shape (n_closed_loop_steps, control_dim)
        Sequence of applied controls u_0, u_1, ..., u_{T-1}.
    solve_results : list[MPCSolveResult]
        One per closed-loop step, for diagnostics.
    """
    if n_closed_loop_steps < 1:
        raise ValueError(
            f"n_closed_loop_steps must be ≥ 1, got {n_closed_loop_steps!r}"
        )
    state = np.asarray(initial_state, dtype=float).copy()
    state_trajectory = [state.copy()]
    control_trajectory = []
    results = []

    last_solution: Optional[np.ndarray] = None
    n = problem.horizon
    m = problem.control_dim

    for t in range(n_closed_loop_steps):
        if warm_start and last_solution is not None:
            shifted = np.vstack([
                last_solution[1:],
                last_solution[-1:],
            ])
            initial_guess = shifted
        else:
            initial_guess = None

        result = solve_mpc_step(
            problem=problem,
            current_state=state,
            initial_guess=initial_guess,
            max_iter=max_iter,
            tolerance=tolerance,
        )
        results.append(result)
        applied = result.applied_control
        control_trajectory.append(applied.copy())
        # Advance the closed-loop system by one step.
        state = np.asarray(
            problem.dynamics(state, applied, t), dtype=float,
        )
        state_trajectory.append(state.copy())
        last_solution = result.optimal_control_sequence

    return (
        np.array(state_trajectory),
        np.array(control_trajectory),
        results,
    )
