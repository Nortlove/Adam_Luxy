# =============================================================================
# Per-User Posterior Modulation — N-of-1 Cascade Mechanism Shrinkage
# Location: adam/intelligence/per_user_posterior_modulation.py
# =============================================================================
"""Per-user N-of-1 posterior modulation for cascade mechanism scores.

Closes the audit-flagged wiring gap (CODEBASE_AUDIT_2026_04_29.md §0a):
the cascade currently reads cached archive priors at decision time, while
per-user BONG posteriors only feed the bid-time information-value premium.
This module converts mechanism_scores from cohort-prior to per-user
posterior using empirical-Bayes shrinkage:

    final_score = base_score + (stability · w) · (personal_affinity - base_score)

where:
    personal_affinity = mean(user_alignment[d] for d in mech.primary_dims)
    stability         = aggregate_confidence ∈ [0, 1]
    w                 = MIXING_WEIGHT_DEFAULT (calibration-pending)

For new buyers (low total_interactions) the modulation is bypassed:
the cohort prior IS the right answer when we have no per-user evidence.

Discipline rule (B3-LUXY a/b/c/d):
    (a) Canonical formula — empirical-Bayes posterior mean as a convex
        combination of cohort prior and per-user posterior, with the
        mixing weight scaled by posterior confidence (stability). See
        Carlin & Louis (2000), "Bayes and Empirical Bayes Methods for
        Data Analysis," 2nd ed., §3.4.
    (b) Regression test — see tests/test_per_user_posterior_modulation.py
        pinning: (i) zero-observation buyer → no modulation,
        (ii) high-stability buyer with biased posterior → bounded shift
        proportional to stability · mixing_weight,
        (iii) bounded output ∈ [0, 1].
    (c) calibration_pending = True. MIXING_WEIGHT_DEFAULT = 0.30 is a
        conservative default; LUXY pilot mSPRT outcomes recalibrate.
        MIN_OBSERVATIONS_FOR_MODULATION = 2 keeps cold-start users on
        the cohort prior; tunable as more LUXY data accrues.
    (d) Honest tag — the mechanism→dimension map is the canonical
        Doc 3 §III mapping reused from MechanismActivation; it is
        substrate, not learned. Replacing it with edge-derived weights
        is a future refinement.
"""

import logging
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)

# ── Mechanism → primary alignment dimensions ────────────────────────────────
# Canonical map from MechanismActivation atom (mechanism_activation.py:1585).
# Dimension names are the COHORT-side scoring vocabulary (the same names
# the cascade's L3 raw_dims use), NOT the BONG DEFAULT_DIMENSIONS.
MECHANISM_DIMENSION_MAP: Dict[str, List[str]] = {
    "regulatory_focus": ["regulatory_fit"],
    "temporal_construal": ["construal_fit", "temporal_discounting"],
    "social_proof": ["social_proof_sensitivity", "mimetic_desire"],
    "scarcity": ["loss_aversion_intensity", "decision_entropy"],
    "identity_construction": ["personality_alignment", "brand_relationship_depth"],
    "mimetic_desire": ["mimetic_desire", "social_proof_sensitivity"],
    "anchoring": ["cognitive_load_tolerance", "decision_entropy"],
    "attention_dynamics": ["interoceptive_awareness", "cognitive_load_tolerance"],
    "embodied_cognition": ["interoceptive_awareness"],
    "authority": ["persuasion_susceptibility", "information_seeking"],
    "liking": ["cooperative_framing_fit", "brand_relationship_depth"],
    "reciprocity": ["cooperative_framing_fit"],
    "commitment": ["autonomy_reactance", "brand_relationship_depth"],
    "cognitive_ease": ["cognitive_load_tolerance", "decision_entropy"],
    "curiosity": ["information_seeking", "narrative_transport"],
    "loss_aversion": ["loss_aversion_intensity", "temporal_discounting"],
    "storytelling": ["narrative_transport"],
    "unity": ["cooperative_framing_fit", "mimetic_desire"],
}

# BONG dimension name → cohort-side dimension name. Identity by default;
# only listed exceptions translate. Keeps the dimension vocabularies
# reconcilable without forcing either side to rename.
BONG_TO_COHORT_DIM: Dict[str, str] = {
    "regulatory_fit_score": "regulatory_fit",
    "construal_fit_score": "construal_fit",
    "personality_brand_alignment": "personality_alignment",
    "evolutionary_motive_match": "evolutionary_motive",
    "anchor_susceptibility_match": "anchor_susceptibility",
    "identity_signaling_match": "identity_signaling",
    "negativity_bias_match": "negativity_bias",
}

MIXING_WEIGHT_DEFAULT = 0.30
MIN_OBSERVATIONS_FOR_MODULATION = 2
SCORE_FLOOR = 0.0
SCORE_CEILING = 1.0


def apply_per_user_posterior_modulation(
    mechanism_scores: Dict[str, float],
    buyer_id: str,
    graph_cache: Any,
    mixing_weight: float = MIXING_WEIGHT_DEFAULT,
) -> Dict[str, float]:
    """Modulate mechanism_scores by the buyer's per-user posterior.

    The directive's central N-of-1 differentiator. Without this wire,
    cascade decisions read cached archive priors; with it, each request
    applies the buyer's accumulated BRAND_CONVERTED-edge evidence as an
    empirical-Bayes shrinkage on top of the cohort prior.

    Args:
        mechanism_scores: Cohort-prior scores from cascade L1–L3 +
            context modulation + synergy check.
        buyer_id: StackAdapt postback ID or sapid round-trip ID. If
            empty / unknown, returns scores unchanged.
        graph_cache: GraphIntelligenceCache (or compatible) exposing
            ``get_buyer_profile(buyer_id) -> BuyerUncertaintyProfile``.
        mixing_weight: Strength of the per-user posterior pull versus
            the cohort prior. Default 0.30 (calibration-pending).

    Returns:
        Modulated mechanism scores ∈ [0, 1]. Returns the input dict
        unchanged when:
            * mechanism_scores is empty or buyer_id is empty
            * graph_cache is None or lacks get_buyer_profile
            * profile is None or has < MIN_OBSERVATIONS_FOR_MODULATION
            * neither BONG posterior nor legacy constructs yield a usable
              per-user alignment vector
    """
    if not mechanism_scores or not buyer_id or graph_cache is None:
        return mechanism_scores

    if not hasattr(graph_cache, "get_buyer_profile"):
        return mechanism_scores

    try:
        profile = graph_cache.get_buyer_profile(buyer_id=buyer_id)
    except Exception as exc:  # noqa: BLE001 — soft-fail by design
        logger.debug("Per-user modulation: get_buyer_profile failed: %s", exc)
        return mechanism_scores

    if profile is None:
        return mechanism_scores

    if getattr(profile, "total_interactions", 0) < MIN_OBSERVATIONS_FOR_MODULATION:
        return mechanism_scores

    user_alignment = _user_alignment_from_bong(profile)
    if not user_alignment:
        user_alignment = _user_alignment_from_constructs(profile)

    if not user_alignment:
        return mechanism_scores

    stability = _stability_from_profile(profile)
    return _shrink_scores(
        mechanism_scores=mechanism_scores,
        user_alignment=user_alignment,
        stability=stability,
        mixing_weight=mixing_weight,
    )


def _user_alignment_from_bong(profile: Any) -> Dict[str, float]:
    """Read per-user alignment from the BONG multivariate posterior.

    Returns {} when BONG isn't initialized for this buyer or the BONG
    updater itself isn't ready.
    """
    bong_post = getattr(profile, "bong_posterior", None)
    if bong_post is None:
        return {}

    try:
        from adam.intelligence.bong import get_bong_updater
        updater = get_bong_updater()
        if updater.prior_eta is None:
            # Updater not initialized; per-user mean would just echo
            # the default prior — bypass.
            return {}
        mean_vec = updater.get_mean(bong_post)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Per-user modulation: BONG.get_mean failed: %s", exc)
        return {}

    alignment: Dict[str, float] = {}
    for i, bong_dim in enumerate(updater.dimension_names):
        if i >= len(mean_vec):
            break
        cohort_dim = BONG_TO_COHORT_DIM.get(bong_dim, bong_dim)
        alignment[cohort_dim] = float(mean_vec[i])
    return alignment


def _user_alignment_from_constructs(profile: Any) -> Dict[str, float]:
    """Fallback: read per-user alignment from legacy per-construct Betas."""
    alignment: Dict[str, float] = {}
    constructs = getattr(profile, "constructs", {}) or {}
    for dim_name, posterior in constructs.items():
        mean_val = getattr(posterior, "mean", None)
        if mean_val is None:
            continue
        try:
            alignment[dim_name] = float(mean_val)
        except (TypeError, ValueError):
            continue
    return alignment


def _stability_from_profile(profile: Any) -> float:
    """Return aggregate_confidence ∈ [0, 1] (well-characterized = high)."""
    val = getattr(profile, "aggregate_confidence", 0.0)
    try:
        stability = float(val)
    except (TypeError, ValueError):
        return 0.0
    if stability < 0.0:
        return 0.0
    if stability > 1.0:
        return 1.0
    return stability


def _shrink_scores(
    mechanism_scores: Dict[str, float],
    user_alignment: Dict[str, float],
    stability: float,
    mixing_weight: float,
) -> Dict[str, float]:
    """Empirical-Bayes shrinkage from cohort prior toward per-user posterior."""
    if stability <= 0.0 or mixing_weight <= 0.0:
        return mechanism_scores

    effective_weight = stability * mixing_weight
    if effective_weight < 1e-6:
        return mechanism_scores
    if effective_weight > 1.0:
        effective_weight = 1.0

    modulated: Dict[str, float] = {}
    for mech_id, base_score in mechanism_scores.items():
        primary_dims = MECHANISM_DIMENSION_MAP.get(mech_id)
        if not primary_dims:
            modulated[mech_id] = base_score
            continue

        affinity = _personal_affinity(user_alignment, primary_dims)
        if affinity is None:
            modulated[mech_id] = base_score
            continue

        shrunk = base_score + effective_weight * (affinity - base_score)
        if shrunk < SCORE_FLOOR:
            shrunk = SCORE_FLOOR
        elif shrunk > SCORE_CEILING:
            shrunk = SCORE_CEILING
        modulated[mech_id] = shrunk

    return modulated


def _personal_affinity(
    user_alignment: Dict[str, float],
    primary_dims: Iterable[str],
) -> Optional[float]:
    """Mean of user's posterior over a mechanism's primary dimensions.

    Returns None when none of the mechanism's primary dimensions are
    represented in the user's alignment vector (caller leaves the
    score untouched in that case).
    """
    values = [user_alignment[d] for d in primary_dims if d in user_alignment]
    if not values:
        return None
    return sum(values) / len(values)
