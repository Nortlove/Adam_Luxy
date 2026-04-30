# =============================================================================
# Cohort Prior Modulation — Cascade Mechanism Boost
# Location: adam/intelligence/cohort_modulation.py
# =============================================================================
"""Apply cohort-level mechanism effectiveness as a bounded boost on
cascade mechanism_scores.

Closes the audit-flagged wiring gap (CODEBASE_AUDIT_2026_04_29.md §6):
``cohort_discovery`` ships a full Louvain-community-detection +
mechanism-effectiveness aggregation service, but no caller reads its
output at decision time. This adapter is the missing wire.

Decision-time consumer: ``result.mechanism_scores`` in run_bilateral_cascade
— that dict becomes the bid mechanism returned to StackAdapt.

The boost formula, mirroring CohortDiscoveryService.get_cohort_boost:

    score' = score + (cohort_effectiveness − 0.5) · membership_score · w

where w = COHORT_BOOST_WEIGHT (default 0.20). Positive shift only when
the cohort's empirical effectiveness for that mechanism exceeds 0.5
(neutral). New / un-clustered buyers (empty priors) bypass.

Discipline rule (B3-LUXY a/b/c/d):
    (a) Boost formula is the canonical CohortDiscoveryService.get_cohort_boost
        rule (cohort_discovery.py:441), kept identical so the cohort
        learning loop and the cascade speak the same language about
        cohort-mechanism strength.
    (b) Regression tests in tests/unit/test_cohort_modulation.py pin:
        empty priors no-op, missing graph_cache no-op, mechanism not in
        priors passthrough, below-0.5 effectiveness no boost,
        above-0.5 effectiveness bounded boost, output ∈ [0, 1].
    (c) calibration_pending=True. COHORT_BOOST_WEIGHT=0.20 matches the
        canonical service; LUXY pilot mSPRT may recalibrate.
    (d) Honest tag — membership_score is currently fixed at 1.0 inside
        graph_cache.get_cohort_priors (the priors dict returns
        effectiveness only). Plumbing membership_score through the
        sync read path is a future refinement; without it the boost
        treats every assigned buyer as a full-strength cohort member,
        which over-shifts users whose Louvain membership_score < 1.0.
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Mirror CohortDiscoveryService.get_cohort_boost weight (cohort_discovery.py:465).
COHORT_BOOST_WEIGHT = 0.20
# Effectiveness floor below which no boost is applied. The service
# only boosts when cohort_effectiveness > 0.5.
NEUTRAL_EFFECTIVENESS = 0.5


def apply_cohort_priors(
    mechanism_scores: Dict[str, float],
    buyer_id: str,
    graph_cache: Any,
    boost_weight: float = COHORT_BOOST_WEIGHT,
) -> Dict[str, float]:
    """Modulate mechanism_scores with cohort-level mechanism effectiveness.

    Real decision-time consumer: cascade mechanism_scores → bid mechanism.

    Args:
        mechanism_scores: Cohort-prior scores from cascade L1–L3 +
            context modulation + per-user posterior modulation.
        buyer_id: StackAdapt postback ID. Empty → no-op.
        graph_cache: GraphIntelligenceCache exposing
            ``get_cohort_priors(buyer_id) -> Dict[str, float]``.
        boost_weight: Strength of the cohort-effectiveness pull.

    Returns:
        Modulated scores ∈ [0, 1]. Returns the input dict unchanged
        when:
            * mechanism_scores is empty or buyer_id is empty
            * graph_cache is None or lacks get_cohort_priors
            * cohort priors lookup returns {} (no cohort data)
            * any internal exception (soft-fail by design)
    """
    if not mechanism_scores or not buyer_id or graph_cache is None:
        return mechanism_scores

    if not hasattr(graph_cache, "get_cohort_priors"):
        return mechanism_scores

    try:
        cohort_priors = graph_cache.get_cohort_priors(buyer_id)
    except Exception as exc:  # noqa: BLE001
        logger.debug("Cohort priors lookup failed for %s: %s", buyer_id, exc)
        return mechanism_scores

    if not cohort_priors:
        return mechanism_scores

    modulated: Dict[str, float] = dict(mechanism_scores)
    for mech_id, base_score in mechanism_scores.items():
        effectiveness = cohort_priors.get(mech_id)
        if effectiveness is None:
            continue
        try:
            eff = float(effectiveness)
        except (TypeError, ValueError):
            continue
        if eff <= NEUTRAL_EFFECTIVENESS:
            # Below-neutral effectiveness contributes no positive boost
            # (matches the canonical service's `> 0.5` gate).
            continue

        boost = (eff - NEUTRAL_EFFECTIVENESS) * boost_weight
        boosted = base_score + boost
        if boosted < 0.0:
            boosted = 0.0
        elif boosted > 1.0:
            boosted = 1.0
        modulated[mech_id] = boosted

    return modulated
