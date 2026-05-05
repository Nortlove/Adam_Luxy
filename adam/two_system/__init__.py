"""Daw two-system arbitration (directive §1.G).

Per directive §1.G.SI.1 — closed-form Bayesian uncertainty-weighted
arbitration between a model-free (heuristic, habit-driven, cached
value) system and a model-based (deliberative, planned, simulated
value) system.

The substrate-blocked stage §1.G.SB.1 (deferred until S6 + S7 close)
will compose this primitive with a processing-mode prior derived
from the cell classifier + journey-state machine. The SI stage
ships the abstract arbitration model and the action-selection
seam without committing to that prior's source.
"""
from adam.two_system.arbitration import (
    ArbitrationResult,
    QValueWithUncertainty,
    TwoSystemEstimate,
    arbitrate_with_processing_mode_prior,
    softmax_action_selection,
    uncertainty_weighted_arbitration,
)

__all__ = [
    "ArbitrationResult",
    "QValueWithUncertainty",
    "TwoSystemEstimate",
    "arbitrate_with_processing_mode_prior",
    "softmax_action_selection",
    "uncertainty_weighted_arbitration",
]
