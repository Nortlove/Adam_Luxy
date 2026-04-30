"""Pre-decision processing-depth predictor + mechanism route gate — C2.

The existing adam/retargeting/engines/processing_depth.py classifies
processing depth POST-IMPRESSION (from observed viewability seconds),
weighting outcome-based posterior updates. C2 extends this:
PRE-IMPRESSION, predict the likely processing depth from page features
+ request context, and use the prediction to GATE which mechanisms
are eligible for selection.

Why this matters for ADAM:
    Per the attention-inversion platform commitment (memory:
    project_attention_inversion_platform_core), creatives that read
    as continuous with low-attention browsing context belong to
    BLEND_COMPATIBLE mechanisms (mechanism_taxonomy.py); creatives
    that require active evaluation belong to VIGILANCE_ACTIVATING
    mechanisms. Selecting a vigilance-activating mechanism for an
    impression that will land in a peripheral processing context is
    a structural mismatch — the creative WILL trigger the vigilance
    route, but the user is not in a state to engage that route.

Discipline anchors:
    - The predictor is a TRANSPARENT RULE-BASED function, not an ML
      model. Thresholds and weights are sourced from the existing
      literature already in processing_depth.py (Bornstein 1989,
      Heath 2006, Trappey 1996). The function name reflects this
      honestly: predict_processing_depth_heuristic.
    - The mechanism compatibility map uses the existing
      MECHANISM_TAXONOMY (atom-level names) translated through
      constants.MECHANISM_TO_ATOM (Cialdini → atom). No invented
      route categories per Cialdini name.
    - The route gate FILTERS scores; it does not REWRITE them. A
      mechanism the predictor flags as incompatible with the
      predicted depth is set to score=0, not silently substituted
      for a different mechanism. The mass goes into the ε-floor's
      uniform distribution downstream.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from adam.constants import MECHANISMS, MECHANISM_TO_ATOM
from adam.intelligence.mechanism_taxonomy import (
    MECHANISM_TAXONOMY,
    MechanismRouteCategory,
)
from adam.retargeting.engines.processing_depth import ProcessingDepth

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Prediction — pre-impression depth estimate from page + request context
# -----------------------------------------------------------------------------


PROCESSING_FLUENCY_FLOOR: float = 0.3


def predict_processing_depth_heuristic(
    page_cognitive_load: Optional[float] = None,
    page_remaining_bandwidth: Optional[float] = None,
    page_attention_competition: Optional[float] = None,
    page_processing_mode: Optional[str] = None,
    device_type: Optional[str] = None,
    page_processing_fluency: Optional[float] = None,
) -> ProcessingDepth:
    """Predict the user's likely processing depth on this impression.

    This is a rule-based combiner over the page-intelligence signals
    that already exist on PagePsychologicalProfile, plus device-type
    context. NOT an ML model; the rules are documented inline.

    Inputs are all optional. When all are None, returns PERIPHERAL —
    the modal default for digital ad impressions per Heath (2006).

    Args:
        page_cognitive_load: 0..1, high = complex page content
        page_remaining_bandwidth: 0..1, low = depleted attention
        page_attention_competition: 0+, higher = more competing elements
        page_processing_mode: pre-classified mode if available
                              ("peripheral", "central", etc.)
        device_type: "desktop" / "mobile" / "tablet" / etc.
        page_processing_fluency: 0..1, Reber's processing-fluency
            (hard → easy). Below PROCESSING_FLUENCY_FLOOR (0.3),
            collapses depth to UNPROCESSED — pages that are hard to
            process leave NO cognitive room for ad engagement.
            Acts as the audit-flagged "fluency floor" hard constraint
            via the existing depth-gated route compatibility table:
            UNPROCESSED → blend-compatible only, vigilance-activating
            mechanisms are zeroed downstream by the C2 gate.

    Returns:
        ProcessingDepth — UNPROCESSED, PERIPHERAL, EVALUATED, or REJECTED.
    """
    # Hard fluency floor — cheapest, strictest gate. Per Reber (1989)
    # processing fluency, pages below the floor leave no cognitive
    # bandwidth for any ad engagement; depth collapses regardless of
    # other signals. Routed through UNPROCESSED so the existing C2
    # mechanism-route compatibility table does the actual gating.
    if (
        page_processing_fluency is not None
        and page_processing_fluency < PROCESSING_FLUENCY_FLOOR
    ):
        return ProcessingDepth.UNPROCESSED

    # Pre-classified processing mode wins when present — the page
    # profiler already did the work.
    if page_processing_mode:
        mode = page_processing_mode.lower()
        if "central" in mode or "deep" in mode:
            return ProcessingDepth.EVALUATED
        if "peripheral" in mode or "shallow" in mode:
            return ProcessingDepth.PERIPHERAL
        if "skim" in mode or "scan" in mode:
            return ProcessingDepth.UNPROCESSED

    # Bandwidth-driven: if page leaves no bandwidth, depth is shallow.
    # Bandwidth < 0.3 → UNPROCESSED (Heath 2006 low-attention regime)
    # Bandwidth ∈ [0.3, 0.6) → PERIPHERAL
    # Bandwidth ≥ 0.6 → EVALUATED (provided no other signal contradicts)
    if page_remaining_bandwidth is not None:
        if page_remaining_bandwidth < 0.3:
            return ProcessingDepth.UNPROCESSED
        if page_remaining_bandwidth < 0.6:
            return ProcessingDepth.PERIPHERAL
        # High bandwidth — defer EVALUATED claim until competition check below
        # since high bandwidth + high competition still collapses depth.
        if page_attention_competition is None or page_attention_competition <= 0.7:
            return ProcessingDepth.EVALUATED

    # Attention competition: if many competing page elements, depth
    # collapses regardless of cognitive load.
    if page_attention_competition is not None and page_attention_competition > 0.7:
        return ProcessingDepth.UNPROCESSED

    # Cognitive load — high load on a complex page tends to push
    # peripheral attention to ads (Heath 2006). Low load = bandwidth
    # available for evaluation if the user attends.
    if page_cognitive_load is not None:
        if page_cognitive_load > 0.7:
            return ProcessingDepth.PERIPHERAL  # High-load context
        if page_cognitive_load < 0.3:
            return ProcessingDepth.EVALUATED   # Low-load context

    # Mobile defaults shallower than desktop — smaller viewport,
    # browsing-context norms (Pew/Nielsen, but threshold is heuristic).
    if device_type and device_type.lower() == "mobile":
        return ProcessingDepth.PERIPHERAL

    # Modal default: PERIPHERAL processing for digital advertising.
    return ProcessingDepth.PERIPHERAL


# -----------------------------------------------------------------------------
# Mechanism route compatibility — Cialdini × ProcessingDepth
# -----------------------------------------------------------------------------
# Compatibility rule (handoff cross-component dependency map + attention-
# inversion commitment):
#     UNPROCESSED:  blend-compatible only — vigilance mechanisms have no
#                   surface to activate without conscious attention.
#     PERIPHERAL:   blend-compatible only — peripheral processing is too
#                   shallow for vigilance to land productively.
#     EVALUATED:    both routes eligible — buyer is processing enough to
#                   engage either route.
#     REJECTED:     vigilance-activating only — if the user is processing
#                   deeply enough to deliberate, blend-route mechanisms
#                   can't add new value (the user IS attending), and
#                   vigilance mechanisms can sometimes salvage by giving
#                   the deliberation something concrete to evaluate.


_BLEND_DEPTHS: Set[ProcessingDepth] = {
    ProcessingDepth.UNPROCESSED,
    ProcessingDepth.PERIPHERAL,
    ProcessingDepth.EVALUATED,
}
_VIGILANCE_DEPTHS: Set[ProcessingDepth] = {
    ProcessingDepth.EVALUATED,
    ProcessingDepth.REJECTED,
}


def _category_for_cialdini(cialdini: str) -> Optional[MechanismRouteCategory]:
    """Translate a Cialdini mechanism into its atom-level route category.

    Uses constants.MECHANISM_TO_ATOM as the canonical translation. If
    the atom name isn't in MECHANISM_TAXONOMY, returns None — the
    caller decides how to treat unmapped mechanisms (we default to
    treating them as eligible to avoid silently dropping mechanisms
    just because the taxonomy is incomplete).
    """
    atom = MECHANISM_TO_ATOM.get(cialdini)
    if not atom:
        return None
    classification = MECHANISM_TAXONOMY.get(atom)
    if classification is None:
        return None
    return classification.category


def mechanisms_compatible_with_depth(
    depth: ProcessingDepth,
) -> Set[str]:
    """Return the Cialdini mechanism names compatible with a depth.

    Compatibility table:
        UNPROCESSED → blend-compatible only
        PERIPHERAL  → blend-compatible only
        EVALUATED   → both routes
        REJECTED    → vigilance-activating only

    Mechanisms whose atom counterpart isn't in MECHANISM_TAXONOMY are
    treated as ALWAYS eligible (conservative — don't silently drop
    a mechanism just because the taxonomy is incomplete). This is the
    same discipline B3's constitution applies for unknown mechanisms.
    """
    eligible: Set[str] = set()
    for cialdini in MECHANISMS:
        cat = _category_for_cialdini(cialdini)
        if cat is None:
            # Unmapped — conservative include
            eligible.add(cialdini)
            continue
        if cat == MechanismRouteCategory.BLEND_COMPATIBLE:
            if depth in _BLEND_DEPTHS:
                eligible.add(cialdini)
        elif cat == MechanismRouteCategory.VIGILANCE_ACTIVATING:
            if depth in _VIGILANCE_DEPTHS:
                eligible.add(cialdini)
    return eligible


def gate_mechanism_scores(
    scores: Dict[str, float],
    predicted_depth: ProcessingDepth,
) -> Dict[str, float]:
    """Filter mechanism_scores by route compatibility with predicted depth.

    Incompatible mechanisms have their score set to 0.0 (NOT removed —
    keeping the key preserves auditability of WHY a mechanism wasn't
    chosen). The ε-floor mixer downstream still distributes mass to
    the floor; the gated mechanism gets ε/K probability mass.

    Special case: if NO mechanisms are compatible (e.g., empty taxonomy
    overlap), pass scores through unchanged. Better to ship the wrong
    mechanism than to ship nothing.
    """
    if not scores:
        return scores

    eligible = mechanisms_compatible_with_depth(predicted_depth)
    if not eligible:
        # Degenerate — no mechanism passes the gate. Pass through to
        # avoid serving an empty mechanism set.
        logger.debug(
            "Route gate: no compatible mechanisms for depth %s, passing through",
            predicted_depth.value,
        )
        return scores

    # Filter — score=0 for incompatible, original score for compatible
    return {
        m: (s if m in eligible else 0.0)
        for m, s in scores.items()
    }


# -----------------------------------------------------------------------------
# End-to-end convenience
# -----------------------------------------------------------------------------


def route_mechanism_scores_by_predicted_depth(
    scores: Dict[str, float],
    page_profile: Optional[Any] = None,
    device_type: Optional[str] = None,
) -> Dict[str, float]:
    """Combined predict-and-gate path — what the cascade calls.

    Reads page features off a PagePsychologicalProfile (or any object
    with the same attribute names), predicts depth, gates scores.

    Soft-fail: any extraction error → pass scores through unchanged.
    """
    if not scores:
        return scores

    cog_load = None
    bandwidth = None
    competition = None
    mode = None
    fluency = None
    if page_profile is not None:
        try:
            cog_load = getattr(page_profile, "cognitive_load", None)
            bandwidth = getattr(page_profile, "remaining_bandwidth", None)
            competition = getattr(page_profile, "attention_competition", None)
            mode = getattr(page_profile, "processing_mode", None)
            fluency = getattr(page_profile, "processing_fluency", None)
        except Exception as exc:
            logger.debug("Page profile feature extraction failed: %s", exc)

    depth = predict_processing_depth_heuristic(
        page_cognitive_load=cog_load,
        page_remaining_bandwidth=bandwidth,
        page_attention_competition=competition,
        page_processing_mode=mode,
        device_type=device_type,
        page_processing_fluency=fluency,
    )
    return gate_mechanism_scores(scores, depth)
