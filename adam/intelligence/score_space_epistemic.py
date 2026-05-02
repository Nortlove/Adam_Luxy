# =============================================================================
# Score-space epistemic bonus modulation — Spine #8 wired BEFORE TTTS
# Location: adam/intelligence/score_space_epistemic.py
# =============================================================================
"""Apply the active-inference epistemic-value bonus in score-space, per
mechanism, BEFORE selection.

Closes audit Tier 1 #4: ``compute_epistemic_bonus`` runs in
``bid_composer`` AFTER the chosen mechanism is selected. It populates
``AlternativeCandidate.epistemic_bonus`` in the trace, but it does
NOT influence which mechanism gets chosen. Per directive Section 5.1
Step 9 (line 691):

    "Epistemic-value bonus (Spine #8): score → score + λ_E · epistemic,
     conditioned on fluency-floor pass."

The bonus is supposed to MODULATE the choice — give exploration weight
to candidates that would teach the engine the most about the user.
Without this wire, exploration vs. exploitation is purely the
posterior reward signal.

WHY THIS EXISTS
---------------

This module is the per-candidate, per-mechanism EIG-weighted score
modulator. For each candidate:
  observation_precision = unit vector over candidate's primary dims
                          (per MECHANISM_DIMENSION_MAP)
  bonus = compute_epistemic_bonus(bong_posterior, observation_precision)
  modulated_score = score + λ_E · bonus

Per directive Step 9, the bonus is conditioned on fluency-floor pass —
since Slice 1's hard floor already drops LOW posture × mechanism
candidates from mechanism_scores, every candidate REACHING this
modulation has already passed the floor. ``fluency_passed=True`` at
this layer. Slice 1 makes the directive's anti-gaming safeguard
(line 220) structural at the cascade: "the system cannot rationalize
incompatible contexts as exploration."

THE PRIMITIVE
-------------

  * ``DEFAULT_LAMBDA_E`` — score-space mixing weight. Default 0.05
    (calibration-pending) — keeps the bonus comparable in magnitude to
    the ±10% posture modulation while leaving headroom for the dual-
    control formulation's pragmatic + epistemic split per directive
    line 282.
  * ``EpistemicScoreModResult`` — frozen dataclass: modulated_scores,
    n_modulated, per_mechanism_bonus, total_bonus_mass.
  * ``observation_precision_for_mechanism(mechanism, bong_dims, ...)``
    — translates mechanism's primary dims (cohort vocabulary) into
    BONG-dim observation precision vector.
  * ``apply_score_space_epistemic_bonus(mechanism_scores, bong_posterior,
    lambda_e=DEFAULT_LAMBDA_E)`` — the wire-point primitive.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Section 5.1 Step 9 line 691; Spine #8 lines
    273-294 (closed-form EIG under BONG); directive line 220 (anti-
    gaming safeguard); Foundation rule 11 (fitness function IS ethics);
    audit 2026-05-01 Tier 1 #4. The per-mechanism observation-precision
    construction follows the MECHANISM_DIMENSION_MAP pattern from
    ``per_user_posterior_modulation`` and the BONG cohort-side
    translation from ``mechanism_vocab``.

(b) Tests pin: bonus added to score-space; mechanism without primary
    dims (unknown) → no bonus (preserves score); empty mechanism_scores
    → pass-through; missing bong_posterior → pass-through;
    high-precision user → low bonus per directive line 285;
    fluency_passed=True at this layer (already enforced by Slice 1);
    score floor / ceiling preserved [0, 1]; lambda_e=0 → no-op;
    EpistemicScoreModResult frozen.

(c) calibration_pending=True. ``DEFAULT_LAMBDA_E=0.05`` is conservative
    pre-pilot. A14 flag: PHASE_4_LAMBDA_E_PILOT_PENDING. LUXY pilot
    via the matched_vs_mismatched_diagonals accumulator + per-mechanism
    EIG telemetry will calibrate.

(d) Honest tags — what is NOT in this slice (named successors):

    * Cohort-budget cap on epistemic bonus (directive line 291).
      Spine #7 cohort discovery is BLOCKED on Loop B per session
      handoffs; the cohort_daily_budget parameter on
      compute_epistemic_bonus is wired but kept None at this layer.
      When cohorts ship, the cap composes here.
    * Differential observation_precision based on edge-derived weights
      (per_user_posterior_modulation honest tag). v0.1 uses unit
      precision on primary dims; pilot calibration will replace.
    * Cross-dimension correlations in EIG. The EIG closed-form here
      treats the BONG diagonal D values; the full-covariance EIG that
      uses cross-dim correlation structure is a sibling slice.
    * The bid_composer's separate post-choice epistemic logging stays
      as-is — it populates AlternativeCandidate.epistemic_bonus in the
      trace for the DR renderer's decomposition layer 3. The two
      consumers serve different purposes: this slice modulates the
      CHOICE; bid_composer's call surfaces the bonus on the trace.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from adam.intelligence.bong import DEFAULT_DIMENSIONS
from adam.intelligence.epistemic_bid_bonus import (
    DEFAULT_PRECISION_DECAY_SCALE,
    DEFAULT_W_MAX,
    compute_epistemic_bonus,
)
from adam.intelligence.per_user_posterior_modulation import (
    BONG_TO_COHORT_DIM,
    MECHANISM_DIMENSION_MAP,
)

logger = logging.getLogger(__name__)


# A14 PHASE_4_LAMBDA_E_PILOT_PENDING
#
# Score-space mixing weight for the epistemic-value bonus per directive
# line 691 (score → score + λ_E · epistemic). Conservative default
# 0.05 — same order of magnitude as the ±10% posture modulation
# (POSTURE_WEIGHT=0.20 · centered=±0.50 = ±10%); leaves headroom for
# pilot calibration to scale up if exploration value warrants.
DEFAULT_LAMBDA_E: float = 0.05

# Floor / ceiling for modulated scores — same convention as
# posture_modulation and per_user_posterior_modulation.
SCORE_FLOOR: float = 0.0
SCORE_CEILING: float = 1.0

# Per-primary-dim observation precision used to build the candidate-
# specific EIG. v0.1 unit (1.0) on primary dims, 0.0 elsewhere — yields
# a clean per-mechanism EIG difference. Pilot calibration will replace
# with edge-derived weights per (a) above.
DEFAULT_PRIMARY_DIM_PRECISION: float = 1.0


# v0.1 best-effort alias map from cohort-side mechanism dim names
# (used in MECHANISM_DIMENSION_MAP) to BONG dim names (DEFAULT_DIMENSIONS).
# The cohort vocabulary and the BONG vocabulary were designed for
# different purposes; only ~7 cohort dims have direct mappings via
# BONG_TO_COHORT_DIM. This alias table provides best-effort semantic
# bridging so every mechanism's primary dims have at least one BONG
# dim to compute EIG over. Honest tag (d): full vocabulary unification
# across the cohort side and BONG side is a sibling slice.
COHORT_DIM_BONG_ALIAS: Dict[str, str] = {
    # Direct via BONG_TO_COHORT_DIM (reverse): regulatory_fit,
    # construal_fit, personality_alignment, evolutionary_motive,
    # anchor_susceptibility, identity_signaling, negativity_bias.
    # Best-effort additions for cohort-vocab-only dims:
    "social_proof_sensitivity": "personality_brand_alignment",
    "mimetic_desire": "identity_signaling_match",
    "loss_aversion_intensity": "negativity_bias_match",
    "decision_entropy": "anchor_susceptibility_match",
    "cognitive_load_tolerance": "processing_route_match",
    "interoceptive_awareness": "mental_simulation_resonance",
    "persuasion_susceptibility": "persuasion_confidence_multiplier",
    "information_seeking": "lay_theory_alignment",
    "cooperative_framing_fit": "linguistic_style_matching",
    "brand_relationship_depth": "brand_trust_fit",
    "autonomy_reactance": "reactance_fit",
    "narrative_transport": "mental_simulation_resonance",
    "temporal_discounting": "spending_pain_match",
}


@dataclass(frozen=True)
class EpistemicScoreModResult:
    """Outcome of running the score-space epistemic modulation.

    ``modulated_scores``: per-mechanism scores after epistemic bonus.
        When the bonus is identically zero across all mechanisms (e.g.,
        no bong_posterior, λ_E=0), equals input mechanism_scores.
    ``n_modulated``: count of mechanisms whose score was shifted by
        more than numerical noise (1e-9 tolerance).
    ``per_mechanism_bonus``: per-candidate raw bonus value (BEFORE
        λ_E scaling) — useful for diagnostics + dashboard surfaces.
        Empty when modulation was a no-op.
    ``total_bonus_mass``: sum of |bonus| across candidates × λ_E —
        captures how much the modulation shifted the score landscape.
    """

    modulated_scores: Dict[str, float]
    n_modulated: int
    per_mechanism_bonus: Dict[str, float] = field(default_factory=dict)
    total_bonus_mass: float = 0.0


def observation_precision_for_mechanism(
    mechanism: str,
    bong_dim_names: List[str],
    primary_precision: float = DEFAULT_PRIMARY_DIM_PRECISION,
) -> Optional[np.ndarray]:
    """Build the per-BONG-dim observation precision vector for a mechanism.

    Mechanisms have primary cohort-side dimension names in
    MECHANISM_DIMENSION_MAP; we translate to BONG-dim names via
    BONG_TO_COHORT_DIM (reverse) plus identity match for non-listed
    dims, then build a vector with ``primary_precision`` on those
    dims and 0.0 elsewhere.

    Returns:
        Shape-(d,) numpy array, or None when the mechanism has no
        primary dims (unknown mechanism). The cascade caller treats
        None as "skip the bonus for this candidate" — no information
        gain claim made for unknown mechanisms.
    """
    primary_cohort_dims = MECHANISM_DIMENSION_MAP.get(mechanism)
    if not primary_cohort_dims:
        return None

    # Build target BONG-dim set for this mechanism using two paths:
    #   1. Reverse BONG_TO_COHORT_DIM (the canonical 7-dim translation)
    #   2. COHORT_DIM_BONG_ALIAS (best-effort bridging for the
    #      cohort-vocab-only dims)
    cohort_to_bong = {v: k for k, v in BONG_TO_COHORT_DIM.items()}
    target_bong_dims: set = set()
    for cohort_dim in primary_cohort_dims:
        # Path 1: canonical translation
        if cohort_dim in cohort_to_bong:
            target_bong_dims.add(cohort_to_bong[cohort_dim])
        # Path 2: best-effort alias
        if cohort_dim in COHORT_DIM_BONG_ALIAS:
            target_bong_dims.add(COHORT_DIM_BONG_ALIAS[cohort_dim])
        # Path 3: identity match (cohort_dim happens to match a BONG
        # dim name as-is)
        if cohort_dim in bong_dim_names:
            target_bong_dims.add(cohort_dim)

    if not target_bong_dims:
        # No primary dims bridged to any BONG dim — vocabulary
        # mismatch beyond what aliases cover. Honest signal that we
        # couldn't compute EIG for this mechanism.
        return None

    # Build BONG-dim mask
    precision = np.zeros(len(bong_dim_names), dtype=np.float64)
    for i, bong_dim in enumerate(bong_dim_names):
        if bong_dim in target_bong_dims:
            precision[i] = primary_precision

    if not (precision > 0).any():
        return None

    return precision


def apply_score_space_epistemic_bonus(
    mechanism_scores: Dict[str, float],
    bong_posterior: Optional[Any],
    *,
    lambda_e: float = DEFAULT_LAMBDA_E,
    w_max: float = DEFAULT_W_MAX,
    decay_scale: float = DEFAULT_PRECISION_DECAY_SCALE,
    bong_dim_names: Optional[List[str]] = None,
) -> EpistemicScoreModResult:
    """Apply per-candidate EIG-weighted score modulation per directive Step 9.

    Args:
        mechanism_scores: candidate scores from cascade through Step 8
            (post free-energy modulation per directive line 690).
        bong_posterior: the user's BONGPosterior (from BuyerProfile or
            equivalent). None → pass-through (no information gain
            without a posterior to learn).
        lambda_e: score-space mixing weight. Default 0.05.
        w_max / decay_scale: forwarded to compute_epistemic_bonus.

    Returns:
        ``EpistemicScoreModResult``. The cascade reads
        ``modulated_scores`` and uses it as the new mechanism_scores
        going into selection.

    Behavior:
      * Empty mechanism_scores → empty result, no modulation.
      * No bong_posterior → pass-through (cannot compute EIG without
        a posterior; caller has no signal to act on).
      * lambda_e == 0 → pass-through (modulation explicitly disabled).
      * Per-candidate observation precision built from primary dims;
        unknown mechanism → no bonus for that candidate (score
        unchanged).
      * Score floor/ceiling preserved [0, 1].
    """
    if not mechanism_scores or bong_posterior is None or lambda_e == 0.0:
        return EpistemicScoreModResult(
            modulated_scores=mechanism_scores,
            n_modulated=0,
            per_mechanism_bonus={},
            total_bonus_mass=0.0,
        )

    # BONGPosterior carries (eta, D) only; dimension_names live on the
    # BONGUpdater singleton. Caller passes bong_dim_names explicitly,
    # else default to DEFAULT_DIMENSIONS (the canonical 20-dim BONG
    # space the cohort-side dims map onto via BONG_TO_COHORT_DIM).
    if bong_dim_names is None:
        bong_dim_names = list(DEFAULT_DIMENSIONS)
    if not bong_dim_names:
        return EpistemicScoreModResult(
            modulated_scores=mechanism_scores,
            n_modulated=0,
            per_mechanism_bonus={},
            total_bonus_mass=0.0,
        )

    modulated: Dict[str, float] = {}
    per_mech_bonus: Dict[str, float] = {}
    total_mass = 0.0
    n_shifted = 0

    for mech, score in mechanism_scores.items():
        try:
            base_score = float(score)
        except (TypeError, ValueError):
            modulated[mech] = score
            continue

        # Build per-mechanism observation precision vector
        obs_prec = observation_precision_for_mechanism(mech, bong_dim_names)
        if obs_prec is None:
            # Unknown mechanism — no bonus claim
            modulated[mech] = base_score
            continue

        try:
            bonus_result = compute_epistemic_bonus(
                individual=bong_posterior,
                observation_precision=obs_prec,
                fluency_passed=True,  # Slice 1 already enforced
                w_max=w_max,
                decay_scale=decay_scale,
                cohort_daily_budget=None,  # Spine #7 BLOCKED on Loop B
            )
            bonus = float(bonus_result.bonus)
        except Exception as exc:
            logger.debug(
                "score_space_epistemic: compute_epistemic_bonus failed "
                "for mechanism=%s: %s", mech, exc,
            )
            modulated[mech] = base_score
            continue

        per_mech_bonus[mech] = bonus
        new_score = base_score + lambda_e * bonus

        if new_score < SCORE_FLOOR:
            new_score = SCORE_FLOOR
        elif new_score > SCORE_CEILING:
            new_score = SCORE_CEILING

        modulated[mech] = new_score
        total_mass += lambda_e * abs(bonus)
        if abs(new_score - base_score) > 1e-9:
            n_shifted += 1

    return EpistemicScoreModResult(
        modulated_scores=modulated,
        n_modulated=n_shifted,
        per_mechanism_bonus=per_mech_bonus,
        total_bonus_mass=total_mass,
    )
