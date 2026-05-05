"""Blind-analysis discipline (particle-physics lineage).

Per directive §1.A — blind-analysis box construction is the
pre-registration mechanism that prevents post-hoc box-redrawing
once data is unblinded. Gross-Vitells LEE trial-factor correction
(§1.A.SI.2) lands as a follow-on slice.
"""
from adam.blind_analysis.box import (
    BlindAnalysisBox,
    BoxParameter,
    BoxValidationError,
    UnblindingState,
    sealed_box,
    placeholder_data_generator,
)

__all__ = [
    "BlindAnalysisBox",
    "BoxParameter",
    "BoxValidationError",
    "UnblindingState",
    "sealed_box",
    "placeholder_data_generator",
]
