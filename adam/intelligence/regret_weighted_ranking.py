# =============================================================================
# Regret-Weighted Mechanism Ranking — Cascade Modulator
# Location: adam/intelligence/regret_weighted_ranking.py
# =============================================================================
"""Apply regret-correlation-prior penalty to cascade mechanism_scores.

Closes the "regret-weighted rank" half of Audit Item 11 (Weakness #6
in the Structural Weakness Registry). The convergence-thresholds half
is NOT in scope here — it requires cell-variance signal that does not
yet flow at cascade decision time.

PROBLEM
-------
The cascade ranks mechanisms by `mechanism_scores` ∈ [0, 1]. F5
(blend/vigilance weighting) applies a binary CATEGORY-level shift
(blend +5%, vigilance −5%); C2 (depth gate) zeroes out incompatible
mechanisms. Neither distinguishes WITHIN a category.

`MECHANISM_TAXONOMY[atom].regret_correlation_prior` is a graded prior
in [0, 1]:
  * BLEND_COMPATIBLE atoms: 0.15–0.25 (low regret)
  * VIGILANCE_ACTIVATING atoms: 0.50–0.70 (high regret)

The graded prior carries differential signal that F5/C2 throw away.
Within BLEND, `embodied_cognition` (0.15) is preferable to
`linguistic_framing` (0.25). Within VIGILANCE,
`identity_construction` (0.50) is preferable to `attention_dynamics`
(0.70). This module surfaces that signal as a multiplicative penalty:

    score' = score * (1 − regret_correlation_prior * REGRET_PENALTY_WEIGHT)

Decision-time consumer: `result.mechanism_scores` after this call
feeds the M1 ε-floor sampler (`_select_primary_with_logged_propensity`)
which selects the bid mechanism. Real consumer.

Discipline rule (B3-LUXY a/b/c/d):
    (a) Multiplicative regret discount; canonical formula above.
        Foundation §7 rule 11 ("the fitness function IS the ethics") —
        regret penalty enforces that high-regret mechanisms cost more
        in the ranking even when they would otherwise win on score.
    (b) Regression tests pin: known-regret atom penalized; unmapped
        Cialdini name (no atom translation) passes through; mechanism
        in MECHANISM_TO_ATOM but atom not in MECHANISM_TAXONOMY passes
        through; ±15% bound; output ∈ [0, 1]; identity preservation
        on no-op; copy-on-modulate.
    (c) calibration_pending=True. REGRET_PENALTY_WEIGHT=0.20 is a
        conservative default (max ~14% penalty on the highest-regret
        mechanism, attention_dynamics with 0.70 prior). Retirement
        trigger: REGRET_PENALTY_WEIGHT_PILOT_PENDING — calibrate when
        LUXY pilot data validates regret_correlation_prior values
        empirically (the same A14 flag MECHANISM_TAXONOMY_UNVALIDATED
        retires).
    (d) Honest tag — the OTHER half of Audit Item 11 (distribution-
        calibrated convergence thresholds) is NOT in this module. It
        requires cell-variance signal that doesn't yet flow at decision
        time. That work is deferred to a separate slice when the
        per-cell variance producer ships.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Penalty weight: a mechanism with regret_correlation_prior=p loses
# (p * REGRET_PENALTY_WEIGHT) fraction of its score. Conservative
# default — the highest-regret atom (attention_dynamics, 0.70) gets
# 14% off; the lowest in VIGILANCE (identity_construction, 0.50) gets
# 10% off; BLEND atoms get 3-5% off. Calibration-pending under LUXY.
REGRET_PENALTY_WEIGHT_DEFAULT: float = 0.20


def apply_regret_weighted_ranking(
    mechanism_scores: Dict[str, float],
    penalty_weight: float = REGRET_PENALTY_WEIGHT_DEFAULT,
) -> Dict[str, float]:
    """Penalize mechanism_scores by their atom-level regret prior.

    For each Cialdini-named mechanism in mechanism_scores:
        1. Translate to atom name via constants.MECHANISM_TO_ATOM
        2. Look up regret_correlation_prior in MECHANISM_TAXONOMY
        3. score' = score * (1 - regret_correlation_prior * penalty_weight)

    Mechanisms whose atom counterpart is NOT in MECHANISM_TAXONOMY pass
    through unchanged (conservative — same discipline as the C2 route
    gate's unknown-mechanism handling).

    Returns:
        Dict[str, float] in [0, 1]. Returns the input dict UNCHANGED
        (identity preserved) when:
            * mechanism_scores is empty
            * no mechanism has a known regret prior (full passthrough)
            * any internal exception (soft-fail by design)
    """
    if not mechanism_scores:
        return mechanism_scores
    if penalty_weight <= 0.0:
        return mechanism_scores

    try:
        from adam.constants import MECHANISM_TO_ATOM
        from adam.intelligence.mechanism_taxonomy import MECHANISM_TAXONOMY
    except Exception as exc:  # noqa: BLE001 — soft-fail
        logger.debug("Regret-weighted rank: import failed: %s", exc)
        return mechanism_scores

    modulated: Dict[str, float] = dict(mechanism_scores)
    any_shift = False

    for cialdini_name, base_score in mechanism_scores.items():
        atom_name = MECHANISM_TO_ATOM.get(cialdini_name)
        if atom_name is None:
            # Cialdini name not in the canonical translation map.
            continue
        classification = MECHANISM_TAXONOMY.get(atom_name)
        if classification is None:
            # Atom not in taxonomy — taxonomy is the 9-entry canonical
            # set; some atoms (e.g., scarcity, social_proof) are not
            # yet classified and pass through.
            continue
        prior = classification.regret_correlation_prior
        if prior is None or prior <= 0.0:
            continue

        # Multiplicative discount; bounded to [0, 1] (input score is
        # bounded; multiplication by [0, 1] keeps it bounded).
        discount = prior * penalty_weight
        if discount >= 1.0:
            discount = 1.0  # max-discount guard (shouldn't fire with
                             # default weight; defensive)
        new_score = base_score * (1.0 - discount)
        if new_score < 0.0:
            new_score = 0.0
        elif new_score > 1.0:
            new_score = 1.0

        if new_score != base_score:
            modulated[cialdini_name] = new_score
            any_shift = True

    if not any_shift:
        # No mechanism had a discountable regret prior — return the
        # input dict (identity preserved) so the cascade's reasoning
        # diff-detection logs nothing for this stage.
        return mechanism_scores

    return modulated
