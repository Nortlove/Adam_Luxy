"""F5 — Blend-compatible vs vigilance-activating strategic weighting.

Closes the F5 task: MECHANISM_TAXONOMY blend-vs-vigilance consumed in
mechanism selection. Today the taxonomy is consumed only by C2's
processing_depth_router (which ZEROS scores for incompatible mechanisms
under the predicted processing depth). F5 is the parallel, smaller
adjustment: a STRATEGIC PREFERENCE weight that runs across all depths,
favoring blend-compatible mechanisms over vigilance-activating ones
even when both are eligible.

Why both: C2's route gate is binary (eligible / not eligible based on
processing depth). F5 is continuous (preference within the eligible
set). Both ground in the attention-inversion platform commitment but
operate at different scales:

    C2: "vigilance mechanisms can't land at peripheral depth" — hard gate
    F5: "all else equal, blend mechanisms are platform-preferred" —
        soft preference

The weighting is composable with C2: F5 weights apply to whatever C2
left non-zero. If C2 zeros all vigilance mechanisms (e.g., predicted
PERIPHERAL depth), F5 has nothing to dampen.

Discipline anchor — the weight is hand-set, not empirical:
    Default blend boost = 1.05, vigilance dampen = 0.95 (5% each way).
    These are STRATEGIC PREFERENCE PARAMETERS encoding the attention-
    inversion platform commitment. They are NOT empirically derived;
    they are not pretending to be derived. If A/B testing later shows
    a different value works better, the constants tune via a single
    config value. The tests pin both the canonical default AND the
    fact that the value is hand-set (so a future refactor can't
    silently relabel it as "empirically tuned").

Reuses C2's _category_for_cialdini helper so taxonomy translation lives
in one place. F5 is the WEIGHTING; C2 is the GATE; both share the
classification surface.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Optional

from adam.intelligence.mechanism_taxonomy import MechanismRouteCategory
from adam.intelligence.processing_depth_router import _category_for_cialdini

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BlendVigilanceWeights:
    """Strategic-preference multipliers per route category.

    blend_boost > 1.0:    blend-compatible mechanisms scale up
    vigilance_dampen < 1.0: vigilance-activating mechanisms scale down
    unmapped_passthrough = 1.0: mechanisms with no taxonomy entry are
        unchanged (conservative — same discipline as the constitution
        and the route gate)

    Default values: hand-set per attention-inversion platform commitment.
    Strategic preference, NOT empirical. A future tuning task may revise
    these based on outcome data, but that's a deliberate change, not a
    silent calibration.
    """
    blend_boost: float = 1.05
    vigilance_dampen: float = 0.95
    unmapped_passthrough: float = 1.0

    def __post_init__(self) -> None:
        # Sanity bounds: never invert direction (blend ≥ 1, vigilance ≤ 1)
        # and never push so far that the gate disappears (blend ≤ 1.25).
        if not (1.0 <= self.blend_boost <= 1.25):
            raise ValueError(
                f"blend_boost {self.blend_boost} outside [1.0, 1.25] — "
                "F5 is a strategic preference, not a hard override"
            )
        if not (0.75 <= self.vigilance_dampen <= 1.0):
            raise ValueError(
                f"vigilance_dampen {self.vigilance_dampen} outside [0.75, 1.0]"
            )


_DEFAULT_WEIGHTS = BlendVigilanceWeights()


def apply_blend_vigilance_weighting(
    scores: Dict[str, float],
    weights: Optional[BlendVigilanceWeights] = None,
) -> Dict[str, float]:
    """Apply the strategic-preference multiplier to mechanism scores.

    For each Cialdini mechanism in scores:
        if blend-compatible:    score *= blend_boost (default 1.05)
        if vigilance-activating: score *= vigilance_dampen (default 0.95)
        if unmapped (no taxonomy entry): score *= unmapped_passthrough (1.0)

    Returns a NEW dict — does not mutate input. Scores are clipped to
    [0, 1] after the multiplication so a boost can't push above the
    cascade's score range.

    Soft-fail: empty scores → empty dict. No exception path.
    """
    if not scores:
        return {}

    w = weights or _DEFAULT_WEIGHTS
    out: Dict[str, float] = {}
    for mech, score in scores.items():
        cat = _category_for_cialdini(mech)
        if cat == MechanismRouteCategory.BLEND_COMPATIBLE:
            multiplier = w.blend_boost
        elif cat == MechanismRouteCategory.VIGILANCE_ACTIVATING:
            multiplier = w.vigilance_dampen
        else:
            multiplier = w.unmapped_passthrough
        out[mech] = max(0.0, min(1.0, score * multiplier))
    return out


def explain_blend_vigilance_classification(
    scores: Dict[str, float],
) -> Dict[str, str]:
    """Diagnostic: per-mechanism classification label.

    Useful for cascade reasoning traces and debugging. Returns
    {mech_name: 'blend' | 'vigilance' | 'unmapped'} for each mechanism
    in scores.
    """
    labels: Dict[str, str] = {}
    for mech in scores.keys():
        cat = _category_for_cialdini(mech)
        if cat == MechanismRouteCategory.BLEND_COMPATIBLE:
            labels[mech] = "blend"
        elif cat == MechanismRouteCategory.VIGILANCE_ACTIVATING:
            labels[mech] = "vigilance"
        else:
            labels[mech] = "unmapped"
    return labels
