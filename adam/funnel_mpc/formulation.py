"""Funnel-MPC problem formulation (directive §1.E.SI.1).

Two primitives:

  * `PrescribedPerformanceEnvelope` — Bechlioulis & Rovithakis (2008,
    IEEE Trans. Autom. Control 53:2090–2099, "Robust adaptive control
    of feedback linearizable MIMO nonlinear systems with prescribed
    performance") describe a class of bounded-tracking-error
    controllers that constrain the tracking error e(t) inside an
    exponentially decreasing envelope:

        -δ_low(t)  <  e(t)  <  δ_high(t)                              (1)

    where the envelope is parameterized by a positive decreasing
    function ρ(t) and asymmetric multipliers δ_low, δ_high ≥ 0:

        ρ(t)       = (ρ_0 - ρ_∞) * exp(-λ * t) + ρ_∞                  (2)
        δ_low(t)   = lower_multiplier * ρ(t)
        δ_high(t)  = upper_multiplier * ρ(t)

    The envelope encodes both transient (ρ_0 — initial slack on
    tracking error) and steady-state (ρ_∞ — terminal slack at t→∞)
    performance specs. The decay rate λ controls how fast the
    envelope tightens. In Funnel-MPC: tracking error = (target
    funnel-progression curve) − (actual progression); the envelope
    ensures the actual curve stays bounded around the target.

  * `FunnelMPCProblem` — Camacho & Bordons (2007, *Model Predictive
    Control*, Springer, 2nd ed., Ch. 2) discrete-time MPC
    formulation:

        min   Σ_{k=0}^{N-1} ℓ(x_k, u_k, k) + V_f(x_N)                 (3)
        s.t.  x_{k+1} = f(x_k, u_k, k)                                (4)
              x_0 = current state
              u_lb ≤ u_k ≤ u_ub
              g_i(x_k, k) ≤ 0  (state constraints — including PPC envelope)

    where N is the prediction horizon, ℓ the stage cost, V_f the
    terminal cost, f the dynamics, and {g_i} the state-inequality
    constraints (the PPC envelope is the canonical instance).

The formulation is generic over the state and control dimensions —
ADAM's funnel state is conventionally three-dimensional
(impressions_remaining ∈ ℝ_+, time_remaining ∈ ℝ_+, progression ∈
[0, 1]) but the primitive does not commit to that shape; the SB.1
stage will plug the production funnel state in via the
`dynamics`/`stage_cost`/`terminal_cost` callables.

Stability of the closed-loop receding-horizon system is governed by
Mayne, Rawlings, Rao & Scokaert (2000, *Automatica* 36:789–814,
"Constrained model predictive control: Stability and optimality")
— specifically, the terminal cost V_f and terminal constraint set
must satisfy a Lyapunov-type decrease condition. In the SI stage we
do not enforce that decrease as a runtime invariant; the consumer
chooses (V_f, terminal set) appropriate to the dynamics.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

import numpy as np


__all__ = [
    "FunnelMPCProblem",
    "PrescribedPerformanceEnvelope",
]


# ----------------------------------------------------------------------------
# Prescribed-performance envelope (Bechlioulis & Rovithakis 2008)
# ----------------------------------------------------------------------------

@dataclass(frozen=True)
class PrescribedPerformanceEnvelope:
    """Exponentially decaying envelope around a tracking target.

    Equation (2) of the module: ρ(t) = (ρ_0 - ρ_∞) * exp(-λ t) + ρ_∞.

    Parameters
    ----------
    rho_initial : float
        ρ_0 > 0 — envelope width at t = 0 (initial transient slack).
    rho_terminal : float
        ρ_∞ ≥ 0 — envelope asymptote at t → ∞ (steady-state slack).
        Must satisfy 0 ≤ ρ_∞ ≤ ρ_0.
    decay_rate : float
        λ > 0 — rate at which the envelope tightens from ρ_0 to ρ_∞.
    upper_multiplier : float
        δ_high ≥ 0 — multiplier on ρ for the positive-side bound.
    lower_multiplier : float
        δ_low ≥ 0 — multiplier on ρ for the negative-side bound.
        At least one of (upper, lower) must be > 0.
    """
    rho_initial: float
    rho_terminal: float
    decay_rate: float
    upper_multiplier: float
    lower_multiplier: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.rho_initial) or self.rho_initial <= 0:
            raise ValueError(
                f"rho_initial must be finite and positive, got "
                f"{self.rho_initial!r}"
            )
        if not math.isfinite(self.rho_terminal) or self.rho_terminal < 0:
            raise ValueError(
                f"rho_terminal must be finite and non-negative, got "
                f"{self.rho_terminal!r}"
            )
        if self.rho_terminal > self.rho_initial:
            raise ValueError(
                f"rho_terminal ({self.rho_terminal}) must be ≤ rho_initial "
                f"({self.rho_initial}); the envelope is non-increasing"
            )
        if not math.isfinite(self.decay_rate) or self.decay_rate <= 0:
            raise ValueError(
                f"decay_rate must be finite and positive, got "
                f"{self.decay_rate!r}"
            )
        for name, value in (
            ("upper_multiplier", self.upper_multiplier),
            ("lower_multiplier", self.lower_multiplier),
        ):
            if not math.isfinite(value) or value < 0:
                raise ValueError(
                    f"{name} must be finite and non-negative, got {value!r}"
                )
        if self.upper_multiplier == 0 and self.lower_multiplier == 0:
            raise ValueError(
                "at least one of upper_multiplier / lower_multiplier "
                "must be > 0; an envelope of width zero is degenerate"
            )

    def rho(self, t: float) -> float:
        """ρ(t) per equation (2). Defined for t ≥ 0."""
        if t < 0:
            raise ValueError(f"t must be non-negative, got {t!r}")
        return (
            (self.rho_initial - self.rho_terminal)
            * math.exp(-self.decay_rate * t)
            + self.rho_terminal
        )

    def upper_bound(self, t: float) -> float:
        """δ_high(t) = upper_multiplier * ρ(t) — positive-side
        tracking-error bound."""
        return self.upper_multiplier * self.rho(t)

    def lower_bound(self, t: float) -> float:
        """δ_low(t) = lower_multiplier * ρ(t) — magnitude of the
        negative-side tracking-error bound (returned as a positive
        number; the constraint is e(t) > -lower_bound(t))."""
        return self.lower_multiplier * self.rho(t)

    def contains(self, error: float, t: float) -> bool:
        """True iff -δ_low(t) < error < δ_high(t) — strict inequality
        per Bechlioulis-Rovithakis (the envelope is an open set)."""
        return -self.lower_bound(t) < error < self.upper_bound(t)


# ----------------------------------------------------------------------------
# MPC problem formulation (Camacho & Bordons 2007)
# ----------------------------------------------------------------------------

@dataclass(frozen=True)
class FunnelMPCProblem:
    """Discrete-time MPC problem definition (eqs. 3–4 of the module).

    Generic over state/control dimension. The dynamics, stage-cost,
    and terminal-cost callables are supplied by the consumer; the
    solver in `solver.py` does not assume any particular structure
    beyond differentiability good enough for SLSQP.

    Parameters
    ----------
    horizon : int
        N ≥ 1 — prediction horizon length (number of stages).
    state_dim, control_dim : int
        Dimensions of the state and control vectors.
    dynamics : Callable[(x, u, k), x_next]
        f(x_k, u_k, k) → x_{k+1}. Receives the current step index k
        so non-stationary dynamics work.
    stage_cost : Callable[(x, u, k), float]
        ℓ(x_k, u_k, k). Should return non-negative for sane Lyapunov
        argument (the SI primitive does not enforce this; consumer
        is responsible).
    terminal_cost : Callable[(x_N), float]
        V_f(x_N). Convention from Mayne et al. 2000: V_f is the
        Control-Lyapunov-Function residual at the prediction-horizon
        end-point.
    control_lower_bound, control_upper_bound : ndarray of shape (control_dim,)
        Box constraints on u_k. Must satisfy lb ≤ ub elementwise.
    state_constraints : Sequence[Callable[(x, k), float]] or None
        Inequality constraints g_i(x_k, k) ≤ 0. None means
        unconstrained state.
    """
    horizon: int
    state_dim: int
    control_dim: int
    dynamics: Callable[[np.ndarray, np.ndarray, int], np.ndarray]
    stage_cost: Callable[[np.ndarray, np.ndarray, int], float]
    terminal_cost: Callable[[np.ndarray], float]
    control_lower_bound: np.ndarray
    control_upper_bound: np.ndarray
    state_constraints: Optional[Sequence[
        Callable[[np.ndarray, int], float]
    ]] = None

    def __post_init__(self) -> None:
        if self.horizon < 1:
            raise ValueError(
                f"horizon must be ≥ 1, got {self.horizon!r}"
            )
        if self.state_dim < 1:
            raise ValueError(
                f"state_dim must be ≥ 1, got {self.state_dim!r}"
            )
        if self.control_dim < 1:
            raise ValueError(
                f"control_dim must be ≥ 1, got {self.control_dim!r}"
            )
        lb = np.asarray(self.control_lower_bound, dtype=float)
        ub = np.asarray(self.control_upper_bound, dtype=float)
        if lb.shape != (self.control_dim,):
            raise ValueError(
                f"control_lower_bound must have shape ({self.control_dim},), "
                f"got {lb.shape}"
            )
        if ub.shape != (self.control_dim,):
            raise ValueError(
                f"control_upper_bound must have shape ({self.control_dim},), "
                f"got {ub.shape}"
            )
        if not np.all(np.isfinite(lb)) or not np.all(np.isfinite(ub)):
            raise ValueError("control bounds must be finite")
        if np.any(lb > ub):
            raise ValueError(
                f"control_lower_bound must be ≤ control_upper_bound "
                f"elementwise, got lb={lb}, ub={ub}"
            )

    def rollout(
        self,
        initial_state: np.ndarray,
        control_sequence: np.ndarray,
    ) -> np.ndarray:
        """Open-loop forward simulation under the given control
        sequence. Returns x_0, x_1, ..., x_N (shape (horizon+1,
        state_dim)).

        Used by the solver to (a) evaluate the cost functional and
        (b) check state-constraint feasibility for a candidate u
        sequence.
        """
        x = np.asarray(initial_state, dtype=float)
        if x.shape != (self.state_dim,):
            raise ValueError(
                f"initial_state must have shape ({self.state_dim},), "
                f"got {x.shape}"
            )
        u_seq = np.asarray(control_sequence, dtype=float)
        if u_seq.shape != (self.horizon, self.control_dim):
            raise ValueError(
                f"control_sequence must have shape "
                f"({self.horizon}, {self.control_dim}), got {u_seq.shape}"
            )
        trajectory = np.empty((self.horizon + 1, self.state_dim))
        trajectory[0] = x
        for k in range(self.horizon):
            trajectory[k + 1] = self.dynamics(trajectory[k], u_seq[k], k)
        return trajectory

    def cost(
        self,
        initial_state: np.ndarray,
        control_sequence: np.ndarray,
    ) -> float:
        """Total cost J = Σ ℓ(x_k, u_k, k) + V_f(x_N) (eq. 3)."""
        trajectory = self.rollout(initial_state, control_sequence)
        u_seq = np.asarray(control_sequence, dtype=float)
        total = 0.0
        for k in range(self.horizon):
            total += float(self.stage_cost(trajectory[k], u_seq[k], k))
        total += float(self.terminal_cost(trajectory[-1]))
        return total
