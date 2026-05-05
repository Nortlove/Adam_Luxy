"""PK/PD modeling of ad exposure as a "drug" (directive §1.F).

Per directive §1.F.SI.1 — Hill / Mager-Jusko / Dayneka-Garg-Jusko
indirect-response models for treating ad-impression dose-response and
delayed creative effects. Pharmacokinetic input concentration c(t) is
supplied by the consumer; the PD primitives here translate c(t) into
response trajectories R(t).

Per-user PK/PD calibration is the substrate-blocked §1.F.SB.1 stage,
which awaits S9 (per-user AR(1) carryover infrastructure). The SI
stage ships the canonical model implementations and analytical /
numerical cross-checks.
"""
from adam.pkpd.hill import (
    hill_response,
    inhibition_factor,
    stimulation_factor,
)
from adam.pkpd.indirect_response import (
    IndirectResponseModel,
    IndirectResponseParams,
    IndirectResponseTrajectory,
    analytical_steady_state,
    simulate_indirect_response,
)

__all__ = [
    "hill_response",
    "inhibition_factor",
    "stimulation_factor",
    "IndirectResponseModel",
    "IndirectResponseParams",
    "IndirectResponseTrajectory",
    "analytical_steady_state",
    "simulate_indirect_response",
]
