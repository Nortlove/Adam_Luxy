# =============================================================================
# Phase 2 — Posture × Mechanism Modulation of Cascade Scores (Slice 8)
# Location: adam/intelligence/posture_modulation.py
# =============================================================================
"""Promote posture from helper attribute to first-class L3 scoring conditioning.

Closes directive Phase 2 line 971-973:

    "Replace bilateral cascade with trilateral wherever it is consumed."

The posture × mechanism compatibility prior (3db50de
posture_mechanism_prior.py) was previously consumed ONLY by
bid_composer (Slice 2, populating DecisionTrace fluency_score). The
L3 mechanism scoring step itself was posture-blind — every mechanism
got the same cohort × archetype × edge score regardless of whether
the page induced a blend-compatible or vigilance-activating
attentional posture. The directive's Phase 2 deliverable explicitly
says "Promote A4 page_attentional_posture from helper to first-class
conditioning variable" (line 972).

This slice adds the L3 modulation step. After mechanism_scores are
formed by L1/L2/L3, before per-user posterior modulation, the scores
are multiplicatively shifted by a small posture-compatibility factor:

    factor[mech] = 1.0 + POSTURE_WEIGHT · (compatibility - 0.5) · 2.0
    modulated[mech] = base[mech] · factor[mech]

Where ``compatibility`` is the prior from
``posture_mechanism_prior.compatibility_prior`` in {LOW=0.25, MID=0.50,
HIGH=0.75}. With POSTURE_WEIGHT=0.20 (calibration-pending):

    LOW  diagonal (mismatched) → factor 0.90  (−10%)
    MID  (neutral / unknown)   → factor 1.00  (no shift)
    HIGH diagonal (matched)    → factor 1.10  (+10%)

The conservative ±10% band leaves room for bilateral-edge evidence to
override; HIGH does NOT dominate the score, it nudges. The
attention-inversion principle (Foundation rule 11) is operationalized
structurally in two layers:
  - SOFT: this multiplicative score modulation (run on every cascade)
  - HARD: bid_composer's epistemic_bonus gate (Slice 2 — LOW posture
    compatibility zeroes the epistemic bonus)

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Phase 2 line 971-973 (trilateral promotion);
    line 970 (compatibility prior); Foundation rule 11 (fitness
    function IS ethics); attention_inversion_platform_core memory
    (the platform's deepest strategic commitment). The multiplicative
    shrinkage form mirrors per_user_posterior_modulation's pattern
    (Carlin & Louis 2000 §3.4 empirical-Bayes shrinkage).

(b) Tests pin: matched diagonal → score increased by POSTURE_WEIGHT
    band; mismatched diagonal → decreased; MID → unchanged; UNKNOWN
    posture → all unchanged (no signal); empty mechanism_scores →
    pass-through; unknown mechanism in scores → MID by soft-fail;
    score values stay in [0, 1] after modulation; modulation factor
    monotonic in compatibility.

(c) calibration_pending=True. POSTURE_WEIGHT=0.20 is conservative
    pre-pilot. A14 flag: PHASE_2_POSTURE_MODULATION_WEIGHT_PILOT_PENDING.
    LUXY pilot data via the matched_vs_mismatched_diagonals
    accumulator will calibrate.

(d) Honest tags — what is NOT in this slice (named successors):

    * Per-archetype × posture × mechanism prior tensor. The current
      4×9 matrix doesn't condition on archetype; lifting to 4×N×9
      composes with hierarchical_bayes once archetype dimension is
      added. Sibling slice.
    * Continuous-vector posture (Phase 2 line 967-969 5-class head).
      This slice consumes the 4-class categorical surface; when the
      5-class head ships, the prior matrix extends from 4×9 to 5×9.
    * Posture-conditional bilateral edge query. The cascade's L3
      bilateral edge query (level3_bilateral_edges in
      bilateral_cascade.py) does not currently filter edges by page
      posture similarity — that's a separate trilateral-extension
      slice (Phase 2 line 973 "Replace bilateral cascade with
      trilateral wherever it is consumed" includes this; the present
      slice handles the SCORING step only).
    * Empirical recalibration of POSTURE_WEIGHT from
      matched_vs_mismatched_diagonals accumulator (Foundation §2
      test interface; 200+ obs/cell threshold).
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from adam.intelligence.page_attentional_posture_substrate import (
    POSTURE_UNKNOWN,
)
from adam.intelligence.posture_mechanism_prior import (
    COMPATIBILITY_MID,
    compatibility_prior,
)

logger = logging.getLogger(__name__)


# A14 PHASE_2_POSTURE_MODULATION_WEIGHT_PILOT_PENDING
#
# Conservative ±10% modulation band. Wide enough to express the
# attention-inversion structural commitment (matched diagonals favored
# over mismatched) but narrow enough to leave room for bilateral-edge
# evidence to override.
POSTURE_WEIGHT: float = 0.20


# Score floor / ceiling — the same as per_user_posterior_modulation's
# convention. Modulation cannot push scores out of [0, 1].
SCORE_FLOOR: float = 0.0
SCORE_CEILING: float = 1.0


def posture_modulation_factor(posture: str, mechanism: str) -> float:
    """Return the multiplicative factor applied to a mechanism's score.

    Args:
        posture: posture label (POSTURE_BLEND / VIGILANCE / NEUTRAL /
            UNKNOWN). Unknown labels soft-fail to MID compatibility →
            factor 1.0 (no shift).
        mechanism: mechanism name. Unknown names soft-fail to MID
            compatibility → factor 1.0.

    Returns:
        factor in [1 − POSTURE_WEIGHT, 1 + POSTURE_WEIGHT]. With
        POSTURE_WEIGHT=0.20: LOW→0.90, MID→1.00, HIGH→1.10.

    Formula:
        factor = 1.0 + POSTURE_WEIGHT · (prior − 0.5) · 2.0
        where prior ∈ {0.25, 0.50, 0.75}
    """
    prior = compatibility_prior(posture, mechanism)
    # Center on MID=0.5; rescale to [-1, 1] then weight; symmetric.
    centered = (prior - COMPATIBILITY_MID) * 2.0  # in [-0.5, +0.5] → [-1, +1] for HIGH/LOW
    return 1.0 + POSTURE_WEIGHT * centered


def apply_posture_modulation(
    mechanism_scores: Dict[str, float],
    posture: Optional[str],
) -> Dict[str, float]:
    """Modulate mechanism scores by the posture × mechanism compatibility prior.

    Args:
        mechanism_scores: Cohort-prior scores from the cascade's L1–L3
            steps + synergy check.
        posture: posture label or None. None → returns scores unchanged
            (no signal — same contract as the cascade's other modulation
            primitives). POSTURE_UNKNOWN also returns scores unchanged
            since compatibility_prior soft-fails to MID for it →
            factor 1.0 anyway, but the early-out keeps allocations down.

    Returns:
        Modulated scores ∈ [0, 1]. Returns the input dict unchanged on
        the no-signal paths (caller can rely on `is` for identity check
        if needed for downstream "did anything change?" diagnostics).
    """
    if not mechanism_scores or not posture:
        return mechanism_scores
    if posture == POSTURE_UNKNOWN:
        return mechanism_scores

    modulated: Dict[str, float] = {}
    for mech, base_score in mechanism_scores.items():
        try:
            score = float(base_score)
        except (TypeError, ValueError):
            modulated[mech] = base_score
            continue

        factor = posture_modulation_factor(posture, mech)
        new_score = score * factor

        if new_score < SCORE_FLOOR:
            new_score = SCORE_FLOOR
        elif new_score > SCORE_CEILING:
            new_score = SCORE_CEILING

        modulated[mech] = new_score

    return modulated
