# =============================================================================
# Phase 2 — Posture × Mechanism Compatibility Prior Matrix
# Location: adam/intelligence/posture_mechanism_prior.py
# =============================================================================
"""Posture × mechanism compatibility prior matrix.

Closes directive Phase 2 line 970:

    "Posture × mechanism compatibility prior matrix."

This is the SOFT prior that biases the cascade toward matched (posture,
mechanism) cells when bilateral edge data is sparse. It is NOT a hard
filter — that's the fluency floor (``adam/intelligence/fluency_floor.py``,
shipped d5107a5). The prior composes with edge-data evidence the way
any informative Bayesian prior composes with likelihood: when edge
data is dense, evidence dominates; when sparse, the prior carries.

ARCHITECTURE
------------

Inputs already in-tree:

  * ``adam/intelligence/mechanism_taxonomy.MECHANISM_TAXONOMY`` — 9
    mechanisms classified BLEND_COMPATIBLE (7) or VIGILANCE_ACTIVATING
    (2) per the attention-inversion principle (Foundation rule 11).
  * ``adam/intelligence/page_attentional_posture_substrate`` —
    POSTURE_BLEND / POSTURE_VIGILANCE / POSTURE_NEUTRAL /
    POSTURE_UNKNOWN labels with confidence-floor semantics.

Output:

  * ``compatibility_prior(posture, mechanism) → float`` in [0, 1] —
    single-cell prior.
  * ``mechanism_compatibility_for_posture(posture, mechanisms=None)
    → Dict[str, float]`` — per-mechanism prior for the posture, ready
    to compose with TS samples or Beta priors in the cascade.

DEFAULT PRIOR LEVELS (calibration-pending)
------------------------------------------

  POSTURE_BLEND × BLEND_COMPATIBLE          → COMPATIBILITY_HIGH (0.75)
  POSTURE_VIGILANCE × VIGILANCE_ACTIVATING  → COMPATIBILITY_HIGH (0.75)
  POSTURE_BLEND × VIGILANCE_ACTIVATING      → COMPATIBILITY_LOW  (0.25)
  POSTURE_VIGILANCE × BLEND_COMPATIBLE      → COMPATIBILITY_LOW  (0.25)
  POSTURE_NEUTRAL × *                       → COMPATIBILITY_MID  (0.50)
  POSTURE_UNKNOWN × *                       → COMPATIBILITY_MID  (0.50)

The HIGH/LOW band is intentionally NOT extreme — 0.75 vs 0.25 leaves
room for empirical evidence to override when bilateral edge data
disagrees with the prior. A 0.95/0.05 band would force evidence to
fight a near-degenerate prior. A 0.55/0.45 band would carry no signal.
0.75/0.25 is the conservative-informative compromise; LUXY pilot data
will calibrate.

Per directive Foundation rule 11 (fitness function IS ethics): the
matched/mismatched asymmetry is the attention-inversion principle
operationalized as a numeric prior. Selection pressure naturally
biases toward matched cells (blend-compatible mechanisms on blend-
compatible pages); the prior makes that bias explicit and auditable
rather than implicit and opaque.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citation: Foundation rule 11 + project_attention_inversion_
    platform_core.md (the platform's deepest strategic commitment).
    The matched/mismatched diagonal pattern itself is operationalized
    in ``mechanism_taxonomy_runtime.matched_vs_mismatched_diagonals()``
    as the diagnostic accumulator (Foundation §2 test interface). The
    prior matrix here is the runtime decision-time companion to that
    diagnostic.

(b) Tests pin: matched diagonals → HIGH; mismatched diagonals → LOW;
    neutral / unknown postures → MID; bulk accessor returns the
    full per-mechanism dict; unknown posture or mechanism strings →
    MID (soft-fail); matrix coverage check (every taxonomy mechanism
    × every posture label has a defined prior; no missing cells).

(c) calibration_pending=True. The {HIGH=0.75, LOW=0.25, MID=0.50}
    triple is conservative-informative; LUXY pilot data will
    calibrate against the matched_vs_mismatched_diagonals accumulator
    once it has 200+ observations per cell. A14 flag:
    PHASE_2_POSTURE_MECHANISM_PRIOR_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Empirical recalibration of the matrix from
      ``matched_vs_mismatched_diagonals()`` accumulator data —
      composes with this primitive once the accumulator has enough
      observations per cell. The recalibration would replace the
      conservative-informative defaults with pilot-derived posteriors.
    * Per-archetype × posture × mechanism prior tensor — would lift
      this 4×9 matrix into 4×N×9 when archetype effects on posture
      compatibility are observed. Composes with hierarchical_bayes.py.
    * Wiring into bilateral_cascade.py — requires mapping the cascade's
      page-conditioning step to a posture label and threading the
      prior into the TS sample / Beta posterior compute. Its own slice.
    * Five-class posture head per directive line 967-969 — the prior
      matrix here uses the 4-label categorical surface
      (page_attentional_posture_substrate); when the 5-class head
      ships, the matrix extends from 4×9 to 5×9 with new posture
      classes.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from adam.intelligence.mechanism_taxonomy import (
    MECHANISM_TAXONOMY,
    MechanismRouteCategory,
)
from adam.intelligence.page_attentional_posture_substrate import (
    POSTURE_BLEND,
    POSTURE_NEUTRAL,
    POSTURE_UNKNOWN,
    POSTURE_VIGILANCE,
)

logger = logging.getLogger(__name__)


# =============================================================================
# A14 calibration-pending compatibility levels
# =============================================================================

# A14 PHASE_2_POSTURE_MECHANISM_PRIOR_PILOT_PENDING
#
# Conservative-informative band: 0.75 vs 0.25 leaves room for evidence
# to override. LUXY pilot data will calibrate via the matched/
# mismatched accumulator once cells have sufficient observations.

COMPATIBILITY_HIGH: float = 0.75
"""Posture matches mechanism's natural route. Prior favors selection
without dominating evidence."""

COMPATIBILITY_LOW: float = 0.25
"""Posture mismatches mechanism's natural route. Prior penalizes
selection without forbidding it (forbidding is the fluency floor's
job, not the soft prior's)."""

COMPATIBILITY_MID: float = 0.50
"""Neutral / unknown posture, or unknown labels. No prior signal in
either direction; pure cascade evidence drives the decision."""


# =============================================================================
# Recognized labels (defensive — soft-fail unknowns to MID)
# =============================================================================


_RECOGNIZED_POSTURES = frozenset({
    POSTURE_BLEND,
    POSTURE_VIGILANCE,
    POSTURE_NEUTRAL,
    POSTURE_UNKNOWN,
})


# =============================================================================
# Single-cell prior
# =============================================================================


def compatibility_prior(posture: str, mechanism: str) -> float:
    """Return the compatibility prior for one (posture, mechanism) cell.

    Args:
        posture: one of ``POSTURE_BLEND``, ``POSTURE_VIGILANCE``,
            ``POSTURE_NEUTRAL``, ``POSTURE_UNKNOWN``. Unknown strings
            are soft-failed to MID with a debug log.
        mechanism: a canonical taxonomy mechanism (in
            ``MECHANISM_TAXONOMY``) OR a cohort-side mechanism (in
            ``MECHANISM_DIMENSION_MAP`` — Cialdini-style: social_proof,
            scarcity, etc.). Cohort-side names are translated to their
            canonical equivalent via ``mechanism_vocab.to_canonical``
            before the taxonomy lookup. Genuinely unknown strings
            soft-fail to MID with a debug log.

    Returns:
        prior in {COMPATIBILITY_HIGH, COMPATIBILITY_LOW,
        COMPATIBILITY_MID}. The prior is a discrete-banded value, not
        a continuous score — the calibration-pending discipline says
        we have not earned continuous distinctions yet.
    """
    if posture not in _RECOGNIZED_POSTURES:
        logger.debug(
            "compatibility_prior: unknown posture %r → MID", posture,
        )
        return COMPATIBILITY_MID

    # Slice 11: translate cohort-side names (social_proof, scarcity,
    # authority, etc.) to canonical taxonomy names before lookup.
    # Canonical names pass through unchanged. Genuinely unknown names
    # also pass through and fall through to the MID soft-fail below.
    from adam.intelligence.mechanism_vocab import to_canonical
    mechanism = to_canonical(mechanism)

    if mechanism not in MECHANISM_TAXONOMY:
        logger.debug(
            "compatibility_prior: unknown mechanism %r → MID", mechanism,
        )
        return COMPATIBILITY_MID

    # Neutral / unknown postures: no signal either way.
    if posture in (POSTURE_NEUTRAL, POSTURE_UNKNOWN):
        return COMPATIBILITY_MID

    mech_category = MECHANISM_TAXONOMY[mechanism].category

    # Matched diagonals
    if (
        posture == POSTURE_BLEND
        and mech_category == MechanismRouteCategory.BLEND_COMPATIBLE
    ):
        return COMPATIBILITY_HIGH
    if (
        posture == POSTURE_VIGILANCE
        and mech_category == MechanismRouteCategory.VIGILANCE_ACTIVATING
    ):
        return COMPATIBILITY_HIGH

    # Mismatched diagonals
    if (
        posture == POSTURE_BLEND
        and mech_category == MechanismRouteCategory.VIGILANCE_ACTIVATING
    ):
        return COMPATIBILITY_LOW
    if (
        posture == POSTURE_VIGILANCE
        and mech_category == MechanismRouteCategory.BLEND_COMPATIBLE
    ):
        return COMPATIBILITY_LOW

    # Defensive — should be unreachable; if a new MechanismRouteCategory
    # is added without updating this function, return MID and log so the
    # gap is surfaced rather than silently miscategorized.
    logger.warning(
        "compatibility_prior: unhandled (posture=%r, mech_category=%r) "
        "— returning MID. Update posture_mechanism_prior to handle new "
        "category.",
        posture, mech_category,
    )
    return COMPATIBILITY_MID


# =============================================================================
# Bulk accessor — per-mechanism prior for a single posture
# =============================================================================


def mechanism_compatibility_for_posture(
    posture: str,
    mechanisms: Optional[List[str]] = None,
) -> Dict[str, float]:
    """Return the per-mechanism compatibility prior for the given posture.

    Args:
        posture: page posture label.
        mechanisms: optional list of mechanism names to score. When
            None, returns priors for every mechanism in
            ``MECHANISM_TAXONOMY``. Unknown mechanism names in the
            list are included with MID (soft-fail).

    Returns:
        ``{mechanism_name: prior}`` covering the requested mechanisms.
    """
    if mechanisms is None:
        mechanisms = sorted(MECHANISM_TAXONOMY.keys())
    return {
        m: compatibility_prior(posture, m)
        for m in mechanisms
    }


# =============================================================================
# Coverage helper — used by tests + diagnostics
# =============================================================================


def all_recognized_postures() -> List[str]:
    """Return the canonical posture labels in stable sorted order."""
    return sorted(_RECOGNIZED_POSTURES)
