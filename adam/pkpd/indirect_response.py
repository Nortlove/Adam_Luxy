"""Dayneka-Garg-Jusko four basic indirect-response (IRM) models
(directive §1.F.SI.1).

Dayneka, Garg & Jusko (1993, *J. Pharmacokinet. Biopharm.* 21:457–478,
"Comparison of four basic models of indirect pharmacodynamic
responses") describe the canonical taxonomy of indirect-response
models. Each takes the form

    dR/dt = k_in_term - k_out_term

where k_in is the zero-order production rate of the response variable
R and k_out is the first-order elimination rate. Drug effect modulates
either k_in or k_out, and either inhibits or stimulates that rate,
yielding four models:

  Model I   (inhibition of input):
    dR/dt = k_in * (1 - I_max * c^n / (IC_50^n + c^n)) - k_out * R
    Drug REDUCES production. R(∞ | c=∞) = k_in * (1 - I_max) / k_out.

  Model II  (inhibition of output):
    dR/dt = k_in - k_out * (1 - I_max * c^n / (IC_50^n + c^n)) * R
    Drug REDUCES elimination. R(∞ | c=∞) = k_in / (k_out * (1 - I_max)).

  Model III (stimulation of input):
    dR/dt = k_in * (1 + S_max * c^n / (SC_50^n + c^n)) - k_out * R
    Drug INCREASES production. R(∞ | c=∞) = k_in * (1 + S_max) / k_out.

  Model IV  (stimulation of output):
    dR/dt = k_in - k_out * (1 + S_max * c^n / (SC_50^n + c^n)) * R
    Drug INCREASES elimination. R(∞ | c=∞) = k_in / (k_out * (1 + S_max)).

The baseline (no-drug) steady-state for all four models is

    R_baseline = k_in / k_out                                      (1)

which is the canonical analytical anchor we test against — at c=0
all four models reduce to dR/dt = k_in - k_out * R, whose
steady-state solution is k_in / k_out.

Mager-Jusko (2001, *J. Pharmacokinet. Pharmacodyn.* 28:507–532) then
extends the basic IRM family with target-mediated drug disposition,
transit-compartment chains, and cell-life models. The basic four-
variant taxonomy here is the substrate that those extensions
compose against; the SB stage (§1.F.SB.1) will calibrate per-user
parameters once S9 closes.

ADAM application context:
  * R = some user-state variable (e.g., conversion-rate inflation
    factor, brand-attitude score, decision-time response readiness).
  * c(t) = "concentration" of ad exposure built from impression
    history, typically by convolving impressions with a one-
    compartment exponential-decay PK kernel.
  * (k_in, k_out, I_max / S_max, IC_50 / SC_50, n) calibrated
    per-user at §1.F.SB.1.

Numerical integration uses scipy.integrate.solve_ivp with the LSODA
solver (default fallback to RK45) so stiffness in the
high-concentration regime resolves correctly without the consumer
having to choose a solver.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Tuple

import numpy as np
from scipy.integrate import solve_ivp

from adam.pkpd.hill import inhibition_factor, stimulation_factor


__all__ = [
    "IndirectResponseModel",
    "IndirectResponseParams",
    "IndirectResponseTrajectory",
    "analytical_steady_state",
    "simulate_indirect_response",
]


class IndirectResponseModel(str, Enum):
    """The four Dayneka-Garg-Jusko basic IRM variants."""

    INHIBIT_INPUT = "inhibit_input"        # Model I
    INHIBIT_OUTPUT = "inhibit_output"      # Model II
    STIMULATE_INPUT = "stimulate_input"    # Model III
    STIMULATE_OUTPUT = "stimulate_output"  # Model IV


@dataclass(frozen=True)
class IndirectResponseParams:
    """Parameters for one of the four IRM variants.

    `magnitude` is interpreted as I_max (for INHIBIT_*) or S_max (for
    STIMULATE_*); `half_concentration` is interpreted as IC_50 or
    SC_50 correspondingly. We use a single name pair to keep the
    dataclass uniform across variants — the model variant is the
    discriminator."""

    model: IndirectResponseModel
    k_in: float
    k_out: float
    magnitude: float       # I_max or S_max
    half_concentration: float  # IC_50 or SC_50
    hill_coefficient: float = 1.0

    def __post_init__(self) -> None:
        if self.k_in <= 0:
            raise ValueError(f"k_in must be positive, got {self.k_in!r}")
        if self.k_out <= 0:
            raise ValueError(f"k_out must be positive, got {self.k_out!r}")
        if self.half_concentration <= 0:
            raise ValueError(
                f"half_concentration must be positive, got "
                f"{self.half_concentration!r}"
            )
        if self.hill_coefficient <= 0:
            raise ValueError(
                f"hill_coefficient must be positive, got "
                f"{self.hill_coefficient!r}"
            )
        # Model-conditional magnitude bounds.
        if self.model in (
            IndirectResponseModel.INHIBIT_INPUT,
            IndirectResponseModel.INHIBIT_OUTPUT,
        ):
            if not 0.0 <= self.magnitude <= 1.0:
                raise ValueError(
                    f"magnitude (I_max) must be in [0, 1] for inhibition "
                    f"models, got {self.magnitude!r}"
                )
            # Model II divergence guard: total inhibition of output
            # would imply infinite steady state.
            if (
                self.model == IndirectResponseModel.INHIBIT_OUTPUT
                and self.magnitude == 1.0
            ):
                raise ValueError(
                    "INHIBIT_OUTPUT with I_max = 1.0 has unbounded "
                    "steady state at saturating concentration"
                )
        else:
            if self.magnitude < 0:
                raise ValueError(
                    f"magnitude (S_max) must be non-negative for "
                    f"stimulation models, got {self.magnitude!r}"
                )


@dataclass(frozen=True)
class IndirectResponseTrajectory:
    """Time-series of a simulated IRM run."""

    times: Tuple[float, ...]
    response: Tuple[float, ...]
    concentrations: Tuple[float, ...]
    model: IndirectResponseModel

    def baseline(self) -> float:
        """The no-drug steady-state response k_in / k_out — read off
        the first time point (which we always start at the no-drug
        equilibrium by convention)."""
        return self.response[0] if self.response else 0.0


def analytical_steady_state(
    params: IndirectResponseParams,
    *,
    saturating: bool = True,
) -> float:
    """Closed-form steady-state response under sustained-concentration
    assumption.

    `saturating=True`: c → ∞ → Hill factor saturates to its limit:
      Model I  : R_ss = k_in * (1 - I_max) / k_out
      Model II : R_ss = k_in / (k_out * (1 - I_max))
      Model III: R_ss = k_in * (1 + S_max) / k_out
      Model IV : R_ss = k_in / (k_out * (1 + S_max))

    `saturating=False`: c = 0 → no drug effect. All four models
    reduce to dR/dt = k_in - k_out * R, steady state = k_in / k_out
    (eq. (1) of the module docstring).
    """
    if not saturating:
        return params.k_in / params.k_out

    if params.model == IndirectResponseModel.INHIBIT_INPUT:
        return params.k_in * (1.0 - params.magnitude) / params.k_out
    if params.model == IndirectResponseModel.INHIBIT_OUTPUT:
        return params.k_in / (params.k_out * (1.0 - params.magnitude))
    if params.model == IndirectResponseModel.STIMULATE_INPUT:
        return params.k_in * (1.0 + params.magnitude) / params.k_out
    if params.model == IndirectResponseModel.STIMULATE_OUTPUT:
        return params.k_in / (params.k_out * (1.0 + params.magnitude))
    raise ValueError(f"unknown model: {params.model!r}")


def _drift(
    t: float,
    response: float,
    *,
    params: IndirectResponseParams,
    concentration_fn: Callable[[float], float],
) -> float:
    """The right-hand side of dR/dt for the chosen model variant."""
    c = concentration_fn(t)
    if c < 0:
        raise ValueError(
            f"concentration_fn returned negative concentration {c!r} at t={t!r}"
        )

    if params.model == IndirectResponseModel.INHIBIT_INPUT:
        factor = inhibition_factor(
            c,
            max_inhibition=params.magnitude,
            ic50=params.half_concentration,
            hill_coefficient=params.hill_coefficient,
        )
        return params.k_in * factor - params.k_out * response
    if params.model == IndirectResponseModel.INHIBIT_OUTPUT:
        factor = inhibition_factor(
            c,
            max_inhibition=params.magnitude,
            ic50=params.half_concentration,
            hill_coefficient=params.hill_coefficient,
        )
        return params.k_in - params.k_out * factor * response
    if params.model == IndirectResponseModel.STIMULATE_INPUT:
        factor = stimulation_factor(
            c,
            max_stimulation=params.magnitude,
            sc50=params.half_concentration,
            hill_coefficient=params.hill_coefficient,
        )
        return params.k_in * factor - params.k_out * response
    if params.model == IndirectResponseModel.STIMULATE_OUTPUT:
        factor = stimulation_factor(
            c,
            max_stimulation=params.magnitude,
            sc50=params.half_concentration,
            hill_coefficient=params.hill_coefficient,
        )
        return params.k_in - params.k_out * factor * response
    raise ValueError(f"unknown model: {params.model!r}")


def simulate_indirect_response(
    params: IndirectResponseParams,
    *,
    times: Tuple[float, ...],
    concentration_fn: Callable[[float], float],
    initial_response: float | None = None,
    rtol: float = 1e-8,
    atol: float = 1e-10,
) -> IndirectResponseTrajectory:
    """Numerically integrate dR/dt over the supplied time grid.

    Parameters
    ----------
    params
        Model variant + parameters.
    times
        Sorted, monotonically increasing tuple of evaluation times
        (t_0 first; t_0 ≤ t_1 ≤ ... ≤ t_n). Must contain at least
        2 distinct points.
    concentration_fn
        Callable t → c(t). Must return non-negative values.
    initial_response
        R(t_0). If `None`, defaults to the no-drug steady state
        k_in / k_out.
    rtol, atol
        Solver tolerances. Defaults are tight enough to recover the
        analytical steady state to ~6 significant figures.

    Returns
    -------
    IndirectResponseTrajectory with `times`, `response`, and the
    sampled concentrations at the same times for plotting /
    diagnostics.
    """
    if len(times) < 2:
        raise ValueError("times must contain at least 2 points")
    times_sorted = tuple(times)
    for prior, current in zip(times_sorted, times_sorted[1:]):
        if current < prior:
            raise ValueError("times must be monotonically non-decreasing")

    r0 = initial_response if initial_response is not None else (
        params.k_in / params.k_out
    )
    if r0 < 0:
        raise ValueError(
            f"initial_response must be non-negative, got {r0!r}"
        )

    t_span = (times_sorted[0], times_sorted[-1])
    sol = solve_ivp(
        fun=lambda t, y: _drift(
            t, y[0], params=params, concentration_fn=concentration_fn,
        ),
        t_span=t_span,
        y0=[r0],
        t_eval=np.array(times_sorted, dtype=float),
        method="LSODA",
        rtol=rtol,
        atol=atol,
    )
    if not sol.success:
        raise RuntimeError(f"solve_ivp failed: {sol.message}")

    response_arr = sol.y[0].tolist()
    concentrations = tuple(
        float(concentration_fn(t)) for t in times_sorted
    )

    return IndirectResponseTrajectory(
        times=times_sorted,
        response=tuple(response_arr),
        concentrations=concentrations,
        model=params.model,
    )
