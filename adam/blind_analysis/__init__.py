"""Blind-analysis discipline (particle-physics lineage).

Per directive §1.A — blind-analysis box construction (§1.A.SI.1) is
the pre-registration mechanism that prevents post-hoc box-redrawing
once data is unblinded. The Gross-Vitells LEE trial-factor
(§1.A.SI.2) corrects the false-discovery rate at the box's threshold
for the look-elsewhere effect introduced by scanning over many
parameter points.
"""
from adam.blind_analysis.box import (
    BlindAnalysisBox,
    BoxParameter,
    BoxValidationError,
    UnblindingState,
    sealed_box,
    placeholder_data_generator,
)
from adam.blind_analysis.lee import (
    MonteCarloLEEResult,
    empirical_upcrossings_at_threshold,
    gross_vitells_global_p_value,
    gross_vitells_trial_factor,
    monte_carlo_global_p_value,
    p_local_one_sided,
)

__all__ = [
    "BlindAnalysisBox",
    "BoxParameter",
    "BoxValidationError",
    "UnblindingState",
    "sealed_box",
    "placeholder_data_generator",
    "MonteCarloLEEResult",
    "empirical_upcrossings_at_threshold",
    "gross_vitells_global_p_value",
    "gross_vitells_trial_factor",
    "monte_carlo_global_p_value",
    "p_local_one_sided",
]
