# =============================================================================
# Mechanism-granularity fluency floor — hard eligibility filter at the cascade
# Location: adam/intelligence/mechanism_fluency_floor.py
# =============================================================================
"""Hard eligibility filter on mechanism × posture compatibility.

Closes Tier 1 audit gap #1 (2026-05-01 deep audit): the existing
``adam/intelligence/fluency_floor.py`` ships
``passes_fluency_floor`` / ``filter_creatives_by_fluency_floor`` over
(CreativeFeatureBundle, PageFeatureBundle), but those primitives need
typed creative-resolution to operate at decision time. Until creative
resolution lands (sibling Slice C), the cascade scores **mechanisms**,
not creatives. The audit found that the only attention-inversion
enforcement at decision time was the ±10% soft posture modulation
(``apply_posture_modulation``) plus a soft penalty in
``bid_composer`` (``epistemic_bonus=0`` when posture × mechanism is
LOW). The directive (line 974) explicitly disallows soft-modifier
treatment:

    "Fluency floor implementation (hard constraint, not optimization
     term): Wire as eligibility filter, not as score modifier."

WHY THIS EXISTS
---------------

This module promotes the existing posture × mechanism compatibility
gate from "soft modifier" to "hard eligibility filter" at the only
granularity the cascade has today (mechanism × posture). When Slice C
ships, ``creative_upload_pipeline.lookup_creative_by_metadata`` will
resolve to a real creative_id and the bundle-level
``fluency_floor.filter_creatives_by_fluency_floor`` will compose
ON TOP of this filter — ineligible mechanisms are dropped first
(coarse pre-filter), then ineligible creatives are dropped (fine
filter). Both are HARD gates per directive line 974.

ATTENTION-INVERSION DISCIPLINE — Foundation §7 rule 11
------------------------------------------------------

Foundation rule 11: "the fitness function IS the ethics." The
attention-inversion principle (project_attention_inversion_platform_core
memory) is the platform's deepest strategic commitment — the system
serves by BLENDING into the attentional pattern the page-context
produced and FULFILLING a goal the context primed, not by GRABBING
attention.

A LOW posture × mechanism compatibility score means a mechanism's
natural processing route MISMATCHES the page's attentional posture.
Examples (illustrative; the actual matrix is in
``posture_mechanism_prior``):
  POSTURE_VIGILANCE × BLEND_COMPATIBLE      → COMPATIBILITY_LOW (0.25)
  POSTURE_BLEND × VIGILANCE_ACTIVATING      → COMPATIBILITY_LOW (0.25)
A LOW combination means serving that mechanism into that page induces
vigilance / interrupts the user's attentional pattern — exactly what
the platform must NOT do. Soft modulation that lets a LOW mechanism
win on bilateral-edge evidence violates Foundation rule 11.

THE PRIMITIVE
-------------

  * ``MECHANISM_FLUENCY_FLOOR`` — threshold (default 0.30, sits between
    COMPATIBILITY_LOW=0.25 and COMPATIBILITY_MID=0.50; matches the
    soft-gate threshold ``bid_composer.FLUENCY_PROXY_FLOOR``).
  * ``MechanismFluencyResult`` — dataclass: filtered_scores,
    n_dropped, dropped_mechanisms, n_eligible, all_dropped, bypassed.
  * ``apply_mechanism_fluency_floor(mechanism_scores, posture, ...)``
    — pure function. Returns the filtered dict + diagnostic counts
    so the cascade can audit + emit Prometheus counters.

ALL-DROP SEMANTIC (v0.1)
------------------------

If every candidate mechanism's posture × mechanism prior is LOW, the
directive (line 122) says the right behavior is the scheduler refusing
ALL bids ("the scheduler is permitted to refuse all mechanisms when no
compatible context exists"). For Slice 1 we soft-fail open and emit a
counter + log warning instead of dropping the bid path entirely; the
hard refuse-all-bid semantic awaits Slice 3 (within-subject scheduler
+ eligible-set construction). The counter is the surface signal that
this case is firing in production.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Phase 2 line 974-976 (hard floor not soft
    modifier); directive Section 5.1 Step 6 line 688 ("Fluency floor
    filter (Spine #4): drop candidates below floor"); directive line
    220 (anti-gaming structural commitment); Foundation rule 11
    (fitness function IS ethics);
    project_attention_inversion_platform_core memory (the platform's
    deepest strategic commitment); audit 2026-05-01 Tier 1 #1.

(b) Tests pin: LOW posture × mechanism dropped; MID kept; HIGH kept;
    UNKNOWN posture pass-through (no signal); empty mechanism_scores
    pass-through; unknown mechanism MID-by-soft-fail (kept); all-drop
    case returns bypassed=True with original scores intact;
    n_dropped + dropped_mechanisms + n_eligible match the diff;
    threshold parameterizable; default threshold matches
    bid_composer.FLUENCY_PROXY_FLOOR for consistency.

(c) calibration_pending=True. ``MECHANISM_FLUENCY_FLOOR=0.30`` matches
    bid_composer's existing FLUENCY_PROXY_FLOOR = 0.30 so the soft
    gate (epistemic_bonus=0) and the hard gate (drop from candidates)
    fire on the same condition. LUXY pilot data + the
    matched_vs_mismatched_diagonals accumulator will calibrate. A14
    flag: PHASE_2_MECHANISM_FLUENCY_FLOOR_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Creative-bundle-level hard fluency floor — that's the existing
      ``fluency_floor.passes_fluency_floor`` over (CreativeFeatureBundle,
      PageFeatureBundle), unblocked when Slice C (creative resolution)
      lands. Will compose ON TOP of this filter, not replace it.
    * Refuse-all-bid semantic when every mechanism is LOW. Per
      directive line 122 this is the within-subject scheduler's
      job — Slice 3 will wire it. Until then we fail-open + counter.
    * Per-archetype × posture × mechanism prior tensor. Current
      4-class posture × N-mechanism matrix lives in
      ``posture_mechanism_prior``; lifting to per-archetype is a
      sibling slice.
    * Five-class posture head (directive Phase 2 line 967-969). This
      filter consumes the 4-class categorical surface; when the
      5-class head ships, the prior matrix extends and this filter
      composes unchanged.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from adam.intelligence.page_attentional_posture_substrate import (
    POSTURE_UNKNOWN,
)
from adam.intelligence.posture_mechanism_prior import compatibility_prior

logger = logging.getLogger(__name__)


# A14 PHASE_2_MECHANISM_FLUENCY_FLOOR_PILOT_PENDING
#
# Sits between COMPATIBILITY_LOW (0.25) and COMPATIBILITY_MID (0.50)
# so that LOW posture × mechanism combinations are dropped while MID
# (neutral / unknown posture) and HIGH (matched diagonal) pass.
# Matches bid_composer.FLUENCY_PROXY_FLOOR (0.30) so the soft-gate
# (epistemic_bonus=0) and this hard-gate (drop from candidates) fire
# on the same condition, removing inconsistency between the two
# attention-inversion enforcement points.
MECHANISM_FLUENCY_FLOOR: float = 0.30


@dataclass(frozen=True)
class MechanismFluencyResult:
    """Outcome of running the floor over a mechanism_scores dict.

    ``filtered_scores``: the eligible scores. When ``bypassed=True``,
        equals the input mechanism_scores (no drops applied).
    ``n_dropped``: count of mechanisms whose compatibility was below
        the floor and which were therefore removed (or would have been
        removed when bypassed=True).
    ``dropped_mechanisms``: ordered list of dropped mechanism names —
        for diagnostics + dashboard surfaces.
    ``n_eligible``: count of mechanisms remaining after the filter
        (input_count - n_dropped when not bypassed; equal to
        len(filtered_scores) always).
    ``all_dropped``: True iff EVERY mechanism in mechanism_scores was
        below the floor. The Slice 3 within-subject scheduler will
        treat this as "refuse all bids"; for Slice 1 we fail-open
        and emit the bypassed flag.
    ``bypassed``: True when the floor logic would have produced
        all_dropped — we then return the input unchanged with a
        warning. Slice 3 will replace this with the directive's
        refuse-all-bid semantic.
    """

    filtered_scores: Dict[str, float]
    n_dropped: int
    dropped_mechanisms: List[str] = field(default_factory=list)
    n_eligible: int = 0
    all_dropped: bool = False
    bypassed: bool = False


def passes_mechanism_fluency(
    posture: Optional[str],
    mechanism: str,
    threshold: float = MECHANISM_FLUENCY_FLOOR,
) -> bool:
    """Return True iff the (posture, mechanism) pair clears the floor.

    Pass-through semantics:
      * posture is None → True (no signal — same contract as the
        cascade's other modulation primitives; without posture we
        cannot certify INeligibility).
      * posture is POSTURE_UNKNOWN → True (compatibility_prior soft-
        fails to MID for it → 0.50 ≥ 0.30 → eligible anyway, but the
        early-out keeps us honest about "no signal" not being
        treated as evidence of incompatibility).
      * unknown mechanism name → soft-fail to MID → True (eligible).
        Same convention as the soft-modulation primitive.

    LOW (0.25) → False. MID (0.50) → True. HIGH (0.75) → True.
    """
    if posture is None or posture == POSTURE_UNKNOWN:
        return True
    prior = compatibility_prior(posture, mechanism)
    return prior >= threshold


def apply_mechanism_fluency_floor(
    mechanism_scores: Dict[str, float],
    posture: Optional[str],
    threshold: float = MECHANISM_FLUENCY_FLOOR,
) -> MechanismFluencyResult:
    """Hard-filter mechanism_scores by posture × mechanism compatibility.

    Args:
        mechanism_scores: cascade-produced scores per mechanism.
        posture: posture label (POSTURE_BLEND / VIGILANCE / NEUTRAL /
            UNKNOWN) or None. None or POSTURE_UNKNOWN → pass-through
            (no signal cannot certify INeligibility).
        threshold: optional override of the default floor.

    Returns:
        ``MechanismFluencyResult``. The cascade reads
        ``filtered_scores`` and uses it as the new mechanism_scores
        going into selection. ``n_dropped`` and ``all_dropped`` feed
        Prometheus counters (RED-criterion #1 input).

    Behavior:
      * Empty input → empty result, no drops, not bypassed.
      * No-signal posture (None / POSTURE_UNKNOWN) → pass-through, no
        drops (the floor applies only when we have positive
        compatibility evidence to act on).
      * One or more LOW mechanisms → drop them; return filtered.
      * ALL mechanisms below floor → bypass (return input unchanged
        with bypassed=True + all_dropped=True). Honest tag (d):
        Slice 3 will replace this with refuse-all-bid per directive
        line 122.
    """
    if not mechanism_scores:
        return MechanismFluencyResult(
            filtered_scores=mechanism_scores,
            n_dropped=0,
            dropped_mechanisms=[],
            n_eligible=0,
            all_dropped=False,
            bypassed=False,
        )

    if posture is None or posture == POSTURE_UNKNOWN:
        return MechanismFluencyResult(
            filtered_scores=mechanism_scores,
            n_dropped=0,
            dropped_mechanisms=[],
            n_eligible=len(mechanism_scores),
            all_dropped=False,
            bypassed=False,
        )

    eligible: Dict[str, float] = {}
    dropped: List[str] = []

    for mech, score in mechanism_scores.items():
        if passes_mechanism_fluency(posture, mech, threshold=threshold):
            eligible[mech] = score
        else:
            dropped.append(mech)

    n_dropped = len(dropped)
    n_input = len(mechanism_scores)
    all_dropped = n_dropped == n_input and n_input > 0

    if all_dropped:
        # v0.1 fail-open: hard refuse-all-bid awaits Slice 3
        # (within-subject scheduler + eligible-set construction). Log
        # at WARNING because production firing of this case means the
        # cascade is being asked to bid into a context where every
        # cohort-prior mechanism would interrupt the user's
        # attentional pattern — operationally the right answer is to
        # not bid, but until Slice 3 lands we preserve current bid
        # behavior and surface the signal via the counter.
        logger.warning(
            "mechanism_fluency_floor: all %d mechanisms below floor "
            "for posture=%s — bypassing filter (Slice 3 awaits)",
            n_input,
            posture,
        )
        return MechanismFluencyResult(
            filtered_scores=mechanism_scores,
            n_dropped=n_dropped,
            dropped_mechanisms=dropped,
            n_eligible=n_input,
            all_dropped=True,
            bypassed=True,
        )

    return MechanismFluencyResult(
        filtered_scores=eligible,
        n_dropped=n_dropped,
        dropped_mechanisms=dropped,
        n_eligible=len(eligible),
        all_dropped=False,
        bypassed=False,
    )
