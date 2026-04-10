# =============================================================================
# Real-Time Creative Adaptation Layer
# Location: adam/retargeting/resonance/creative_adaptation.py
# =============================================================================

"""
Lightweight creative adaptation at impression time (<5ms).

When an ad lands on a page, this layer reads the page's cached
psychological profile and adapts the pre-selected copy variant's
parameters WITHOUT full regeneration. The mechanism stays constant
but the creative execution rotates to align with the page field.

Example:
    Mechanism: evidence_proof
    Page: analytical (high cognitive_load_tolerance)
    → evidence_type: "data" (use statistics, not testimonials)

    Same mechanism, different page: emotional (high emotional_resonance)
    → evidence_type: "testimonial" (use stories, not statistics)

This is the ADAPT layer of the Resonance Engine:
    SENSE → MODEL → MATCH → **ADAPT** → LEARN → EVOLVE

Integration: Called from the bilateral cascade's apply_context_modulation()
after page context is loaded, before the response is assembled.
"""

import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


# Page cluster → evidence type preference
# (which evidence format works best on each page type)
_EVIDENCE_BY_CLUSTER = {
    "analytical": "data",        # Numbers, statistics, comparisons
    "emotional": "testimonial",  # Stories, personal experiences
    "social": "social_proof",    # Reviews, ratings, popularity
    "transactional": "comparison", # Price/feature comparisons
    "aspirational": "narrative",  # Aspirational stories, vision
}

# Page cluster → tone adaptation
_TONE_BY_CLUSTER = {
    "analytical": "authoritative",
    "emotional": "warm",
    "social": "warm",
    "transactional": "direct",
    "aspirational": "aspirational",
}

# Page cluster → CTA style
_CTA_BY_CLUSTER = {
    "analytical": "learn_more",   # "See the data", "View details"
    "emotional": "feel",          # "Experience it", "Discover"
    "social": "join",             # "Join 10,000+", "See what others say"
    "transactional": "act_now",   # "Book now", "Get started"
    "aspirational": "aspire",     # "Elevate your", "Step into"
}


def classify_page_cluster(page_edge_dimensions: Dict[str, float]) -> str:
    """Classify page into psychological cluster from edge dimensions.

    Returns: analytical, emotional, social, transactional, aspirational
    """
    clt = page_edge_dimensions.get("cognitive_load_tolerance", 0.5)
    er = page_edge_dimensions.get("emotional_resonance", 0.5)
    sps = page_edge_dimensions.get("social_proof_sensitivity", 0.5)
    va = page_edge_dimensions.get("value_alignment", 0.5)
    ar = page_edge_dimensions.get("autonomy_reactance", 0.5)

    scores = {
        "analytical": clt * 0.5 + (1 - er) * 0.3 + ar * 0.2,
        "emotional": er * 0.5 + (1 - clt) * 0.3 + va * 0.2,
        "social": sps * 0.5 + er * 0.3 + (1 - ar) * 0.2,
        "transactional": (1 - clt) * 0.3 + (1 - er) * 0.3 + (1 - sps) * 0.2 + (1 - ar) * 0.2,
        "aspirational": va * 0.4 + er * 0.3 + (1 - clt) * 0.15 + sps * 0.15,
    }
    return max(scores, key=scores.get)


def adapt_creative_to_page(
    copy_params: Dict[str, Any],
    page_edge_dimensions: Dict[str, float],
    mechanism: str = "",
    archetype: str = "",
) -> Dict[str, Any]:
    """Adapt creative parameters to the actual page context.

    This is a LIGHTWEIGHT operation (<5ms) that modifies copy parameters
    based on the page's psychological field. The mechanism stays the same —
    only the execution style rotates.

    Args:
        copy_params: Current copy parameters (tone, framing, evidence_type, etc.)
        page_edge_dimensions: 20-dim page psychological profile
        mechanism: The selected mechanism
        archetype: Buyer archetype

    Returns:
        Adapted copy_params dict (modified in place for efficiency)
    """
    if not page_edge_dimensions:
        return copy_params

    cluster = classify_page_cluster(page_edge_dimensions)
    adapted = dict(copy_params)

    # Adapt evidence type to page cluster
    page_evidence = _EVIDENCE_BY_CLUSTER.get(cluster)
    if page_evidence:
        adapted["evidence_type"] = page_evidence

    # Adapt tone — but don't override strong archetype-driven tone
    page_tone = _TONE_BY_CLUSTER.get(cluster)
    if page_tone and adapted.get("tone") not in ("warm", "authoritative"):
        adapted["tone"] = page_tone

    # Adapt CTA style to page engagement mode
    page_cta = _CTA_BY_CLUSTER.get(cluster)
    if page_cta:
        adapted["cta_style"] = page_cta

    # Page-specific dimension adjustments
    er = page_edge_dimensions.get("emotional_resonance", 0.5)
    clt = page_edge_dimensions.get("cognitive_load_tolerance", 0.5)
    ar = page_edge_dimensions.get("autonomy_reactance", 0.5)

    # If page has high emotional resonance, boost emotional appeal
    if er > 0.65:
        adapted["emotional_appeal"] = max(
            adapted.get("emotional_appeal", 0.5), er
        )

    # If page has low cognitive tolerance, simplify
    if clt < 0.35:
        adapted["abstraction_level"] = min(
            adapted.get("abstraction_level", 0.5), 0.3
        )
        adapted["copy_length"] = "short"

    # If page has high autonomy reactance, reduce pressure
    if ar > 0.6:
        adapted["urgency_level"] = min(
            adapted.get("urgency_level", 0.5), 0.2
        )

    adapted["_page_cluster"] = cluster
    adapted["_adapted"] = True

    logger.debug(
        "Creative adapted: cluster=%s, evidence=%s, tone=%s, cta=%s",
        cluster, adapted.get("evidence_type"), adapted.get("tone"),
        adapted.get("cta_style"),
    )

    return adapted


def compute_adaptation_confidence(
    page_edge_dimensions: Dict[str, float],
) -> float:
    """Compute confidence in the page adaptation.

    Higher when page dimensions are extreme (clear cluster membership).
    Lower when near neutral (ambiguous cluster).
    """
    if not page_edge_dimensions:
        return 0.0

    deviations = [abs(v - 0.5) for v in page_edge_dimensions.values()]
    avg_dev = sum(deviations) / len(deviations) if deviations else 0.0

    # Map average deviation to confidence: 0.0→0.3, 0.25→0.8, 0.5→1.0
    return min(1.0, 0.3 + avg_dev * 2.8)
