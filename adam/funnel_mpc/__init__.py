"""Funnel-MPC receding-horizon scheduler with prescribed-performance bounds
(directive §1.E).

Per directive §1.E.SI.1 — Model-Predictive Control over the
conversion-funnel state (impressions remaining in budget × time
remaining × cohort progression toward conversion). The receding-
horizon solver enforces prescribed-performance bounds (Bechlioulis
& Rovithakis 2008 IEEE TAC 53:2090–2099) so the funnel-rate
trajectory stays inside an exponentially decaying envelope around a
target trajectory.

Calibration of the envelope parameters (initial slack ρ_0, terminal
slack ρ_∞, decay rate λ, asymmetric multipliers δ_low / δ_high) is
the substrate-blocked §1.E.SB.1 stage, which awaits S6 (cell
classifier v0) per directive §1.E.SB.1. The SI stage ships the
mathematical primitives and the solver — closed-form envelope,
generic dynamics interface, scipy-based receding-horizon solver —
with regression tests pinning the canonical references.
"""
from adam.funnel_mpc.formulation import (
    FunnelMPCProblem,
    PrescribedPerformanceEnvelope,
)
from adam.funnel_mpc.solver import (
    MPCSolveResult,
    simulate_receding_horizon,
    solve_mpc_step,
)

__all__ = [
    "FunnelMPCProblem",
    "MPCSolveResult",
    "PrescribedPerformanceEnvelope",
    "simulate_receding_horizon",
    "solve_mpc_step",
]
