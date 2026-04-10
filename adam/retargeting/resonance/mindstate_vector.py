# =============================================================================
# Resonance Engineering — Layer 1: SENSE
# Location: adam/retargeting/resonance/mindstate_vector.py
# =============================================================================

"""
PageMindstateVector extraction from PagePsychologicalProfile.

The existing page intelligence system (page_intelligence.py) produces a rich
15-layer PagePsychologicalProfile for each page. This module extracts the
compact 32-dimensional PageMindstateVector suitable for resonance computation.

The 32 dimensions are:
- 20 edge_dimensions (same space as bilateral BRAND_CONVERTED edges)
- 7 NDF construct activations
- 5 environmental scalars (valence, arousal, cognitive_load, authority, bandwidth)

Integration: Called from PageIntelligenceCache.lookup() alongside the full
profile. The mindstate vector is the MODEL's input; the full profile is for
human interpretation.
"""

import logging
from typing import Any, Dict, Optional

from adam.retargeting.resonance.models import (
    PageMindstateVector,
    EDGE_DIM_NAMES,
    NDF_DIM_NAMES,
)

logger = logging.getLogger(__name__)

# Mapping from PagePsychologicalProfile edge_dimensions keys to our canonical names
# The profile uses slightly different key names in some cases
_EDGE_DIM_ALIASES = {
    "regulatory_fit": "regulatory_fit",
    "construal_fit": "construal_fit",
    "personality_alignment": "personality_alignment",
    "emotional_resonance": "emotional_resonance",
    "value_alignment": "value_alignment",
    "evolutionary_motive": "evolutionary_motive",
    "linguistic_style": "linguistic_style",
    "persuasion_susceptibility": "persuasion_susceptibility",
    "cognitive_load_tolerance": "cognitive_load_tolerance",
    "narrative_transport": "narrative_transport",
    "social_proof_sensitivity": "social_proof_sensitivity",
    "loss_aversion_intensity": "loss_aversion_intensity",
    "temporal_discounting": "temporal_discounting",
    "brand_relationship_depth": "brand_relationship_depth",
    "autonomy_reactance": "autonomy_reactance",
    "information_seeking": "information_seeking",
    "mimetic_desire": "mimetic_desire",
    "interoceptive_awareness": "interoceptive_awareness",
    "cooperative_framing_fit": "cooperative_framing_fit",
    "decision_entropy": "decision_entropy",
}

# NDF dimension mapping
_NDF_DIM_ALIASES = {
    "approach_avoidance": "approach_avoidance",
    "temporal_horizon": "temporal_horizon",
    "social_calibration": "social_calibration",
    "uncertainty_tolerance": "uncertainty_tolerance",
    "status_sensitivity": "status_sensitivity",
    "cognitive_engagement": "cognitive_engagement",
    "arousal_seeking": "arousal_seeking",
}


def extract_mindstate_vector(
    page_profile: Any,
    url: str = "",
    domain: str = "",
) -> PageMindstateVector:
    """Extract PageMindstateVector from a PagePsychologicalProfile.

    Handles both the full dataclass profile and dict representations
    (from Redis deserialization).

    Args:
        page_profile: PagePsychologicalProfile instance or dict
        url: URL pattern for metadata
        domain: Domain for metadata

    Returns:
        PageMindstateVector with 32 dimensions populated
    """
    # Handle both dataclass and dict
    if isinstance(page_profile, dict):
        return _extract_from_dict(page_profile, url, domain)

    return _extract_from_profile(page_profile, url, domain)


def _extract_from_profile(profile: Any, url: str, domain: str) -> PageMindstateVector:
    """Extract from PagePsychologicalProfile dataclass."""

    # Edge dimensions (Layer 15 of PagePsychologicalProfile)
    edge_dims = {}
    raw_edge = getattr(profile, "edge_dimensions", {}) or {}
    for canonical, alias in _EDGE_DIM_ALIASES.items():
        edge_dims[canonical] = raw_edge.get(alias, raw_edge.get(canonical, 0.5))

    # NDF construct activations
    ndf = {}
    raw_ndf = getattr(profile, "construct_activations", {}) or {}
    for canonical, alias in _NDF_DIM_ALIASES.items():
        ndf[canonical] = raw_ndf.get(alias, raw_ndf.get(canonical, 0.5))

    # Mechanism susceptibility
    mech_susc = getattr(profile, "mechanism_adjustments", {}) or {}

    # Environmental scalars
    valence = getattr(profile, "emotional_valence", 0.0)
    arousal = getattr(profile, "emotional_arousal", 0.5)
    cog_load = getattr(profile, "cognitive_load", 0.5)
    authority = getattr(profile, "publisher_authority", 0.5)
    bandwidth = getattr(profile, "remaining_bandwidth", 0.5)

    # Confidence from profile
    confidence = getattr(profile, "confidence", 0.3)
    scoring_tier = getattr(profile, "profile_source",
                          getattr(profile, "edge_scoring_tier", "unknown"))

    return PageMindstateVector(
        edge_dimensions=edge_dims,
        ndf_activations=ndf,
        mechanism_susceptibility=mech_susc,
        emotional_valence=valence,
        emotional_arousal=arousal,
        cognitive_load=cog_load,
        publisher_authority=authority,
        remaining_bandwidth=bandwidth,
        url_pattern=url or getattr(profile, "url_pattern", ""),
        domain=domain or getattr(profile, "domain", ""),
        confidence=confidence,
        scoring_tier=scoring_tier,
    )


def _extract_from_dict(d: Dict[str, Any], url: str, domain: str) -> PageMindstateVector:
    """Extract from dict representation (Redis deserialized)."""

    edge_dims = {}
    raw_edge = d.get("edge_dimensions", {})
    if isinstance(raw_edge, str):
        import json
        try:
            raw_edge = json.loads(raw_edge)
        except (json.JSONDecodeError, TypeError):
            raw_edge = {}

    for canonical in EDGE_DIM_NAMES:
        edge_dims[canonical] = float(raw_edge.get(canonical, 0.5))

    ndf = {}
    raw_ndf = d.get("construct_activations", {})
    if isinstance(raw_ndf, str):
        import json
        try:
            raw_ndf = json.loads(raw_ndf)
        except (json.JSONDecodeError, TypeError):
            raw_ndf = {}

    for canonical in NDF_DIM_NAMES:
        ndf[canonical] = float(raw_ndf.get(canonical, 0.5))

    mech_susc = d.get("mechanism_adjustments", {})
    if isinstance(mech_susc, str):
        import json
        try:
            mech_susc = json.loads(mech_susc)
        except (json.JSONDecodeError, TypeError):
            mech_susc = {}

    return PageMindstateVector(
        edge_dimensions=edge_dims,
        ndf_activations=ndf,
        mechanism_susceptibility=mech_susc,
        emotional_valence=float(d.get("emotional_valence", 0.0)),
        emotional_arousal=float(d.get("emotional_arousal", 0.5)),
        cognitive_load=float(d.get("cognitive_load", 0.5)),
        publisher_authority=float(d.get("publisher_authority", 0.5)),
        remaining_bandwidth=float(d.get("remaining_bandwidth", 0.5)),
        url_pattern=url or d.get("url_pattern", ""),
        domain=domain or d.get("domain", ""),
        confidence=float(d.get("confidence", 0.3)),
        scoring_tier=d.get("profile_source", d.get("edge_scoring_tier", "unknown")),
    )
