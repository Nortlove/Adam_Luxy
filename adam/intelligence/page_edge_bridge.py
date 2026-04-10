"""
Page → Edge Bridge: Trilateral Resonance at the Edge Level
============================================================

THE GAP THIS SOLVES:

Currently, the bilateral cascade computes mechanism scores from edge
dimensions (the 20-dim alignment between buyer and product), then
AFTERWARDS applies page modulation as a multiplier. This is wrong.

The page doesn't just modify mechanisms — it shifts the BUYER'S POSITION
in the 20-dimensional psychological space BEFORE they encounter the ad.
A financial anxiety article doesn't just "open loss_aversion channel" —
it repositions the reader along multiple edge dimensions:

    regulatory_fit:         shifts toward prevention (reader primed for safety)
    persuasion_susceptibility: increases (anxiety makes people more persuadable)
    autonomy_reactance:     decreases (anxious people seek guidance)
    loss_aversion_intensity: increases (threat-primed reader weighs losses 3x)
    social_proof_sensitivity: increases (uncertain reader looks to peers)
    cognitive_load_tolerance: decreases (anxiety consumes bandwidth)
    temporal_discounting:    shifts to immediate (threat feels urgent)
    decision_entropy:        increases (anxiety creates decision paralysis)

These are the SAME 20 dimensions on the bilateral edges. By predicting
the page's effect on each dimension, we produce a PAGE-SHIFTED ALIGNMENT
VECTOR. The cascade then computes mechanisms from THIS shifted vector
instead of raw edge averages — meaning the same product gets different
mechanism priorities on different pages, not just different multipliers.

This is true trilateral resonance: buyer(edge) × product(edge) × page(shift).

ARCHITECTURE:

    PagePsychologicalProfile
           ↓
    compute_page_edge_shift()
           ↓
    page_shifted_alignment = raw_edge_alignment + shift_vector
           ↓
    mechanism_scoring(page_shifted_alignment)
           ↓
    CreativeIntelligence (now page-aware from the ground up)

The shift vector also feeds back into:
- Gradient field priorities (dimensions with high gradient AND page amplification)
- Information value (dimensions where page creates learnable signal)
- Decision probability (page-conditioned conversion prediction)
- Copy generation (creative direction from page-shifted gaps)
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# The 20 edge dimensions and how page NDF maps to each
_EDGE_DIMS = [
    "regulatory_fit", "construal_fit", "personality_alignment",
    "emotional_resonance", "value_alignment", "evolutionary_motive",
    "linguistic_style", "composite_alignment",
    "persuasion_susceptibility", "cognitive_load_tolerance",
    "narrative_transport", "social_proof_sensitivity",
    "loss_aversion_intensity", "temporal_discounting",
    "brand_relationship_depth", "autonomy_reactance",
    "information_seeking", "mimetic_desire",
    "interoceptive_awareness", "cooperative_framing_fit",
    "decision_entropy",
]


# ============================================================================
# PAGE → EDGE SHIFT MATRIX
# ============================================================================
# How each page psychological state shifts each edge dimension.
# Derived from psychological theory:
#
# - Regulatory Focus Theory (Higgins): page frame → regulatory_fit shift
# - Construal Level Theory (Trope & Liberman): page temporal → construal shift
# - Elaboration Likelihood Model (Petty & Cacioppo): page bandwidth → processing route
# - Prospect Theory (Kahneman & Tversky): page loss frame → loss aversion amplification
# - Social Impact Theory (Latané): page social context → social proof sensitivity
# - Reactance Theory (Brehm): page authority → autonomy reactance modulation
# - Terror Management Theory (Greenberg): page threat → evolutionary motive activation
#
# Each entry: (page_ndf_dimension, edge_dimension, weight, direction)
# direction: +1 = page high → edge increases, -1 = page high → edge decreases

_SHIFT_MATRIX = [
    # ── Page approach_avoidance → multiple edge dimensions ──
    # Prevention-framed page activates loss aversion, suppresses approach-oriented edges
    ("approach_avoidance", "regulatory_fit", 0.40, +1),
    # Neg avoidance page → buyer more loss-averse
    ("approach_avoidance", "loss_aversion_intensity", 0.35, -1),
    # Prevention page → more susceptible to authority (seeking safety)
    ("approach_avoidance", "persuasion_susceptibility", 0.15, -1),
    # Threat context → activates evolutionary survival motives
    ("approach_avoidance", "evolutionary_motive", 0.20, -1),
    # Approach page → more autonomy/independence
    ("approach_avoidance", "autonomy_reactance", 0.10, +1),

    # ── Page temporal_horizon → construal + temporal discounting ──
    # Future-oriented page → abstract construal, long-term thinking
    ("temporal_horizon", "construal_fit", 0.45, +1),
    # Future page → lower temporal discounting (values long-term)
    ("temporal_horizon", "temporal_discounting", 0.40, -1),
    # Future page → less urgency-driven, more deliberate
    ("temporal_horizon", "decision_entropy", 0.15, -1),

    # ── Page social_calibration → social edge dimensions ──
    # Highly social page → social proof sensitivity increases
    ("social_calibration", "social_proof_sensitivity", 0.45, +1),
    # Social page → mimetic desire activated (want what others want)
    ("social_calibration", "mimetic_desire", 0.30, +1),
    # Social page → personality alignment matters more (social identity)
    ("social_calibration", "personality_alignment", 0.15, +1),
    # Social page → cooperative framing more effective
    ("social_calibration", "cooperative_framing_fit", 0.20, +1),

    # ── Page uncertainty_tolerance → cognitive/decision edges ──
    # High uncertainty page → decision entropy increases (paralysis)
    ("uncertainty_tolerance", "decision_entropy", 0.35, +1),
    # Uncertain page → more susceptible to persuasion (seeking answers)
    ("uncertainty_tolerance", "persuasion_susceptibility", 0.25, +1),
    # Uncertain page → information seeking increases
    ("uncertainty_tolerance", "information_seeking", 0.20, +1),
    # Uncertain page → autonomy reactance decreases (willing to be guided)
    ("uncertainty_tolerance", "autonomy_reactance", 0.15, -1),

    # ── Page cognitive_engagement → processing edge dimensions ──
    # Analytical page → cognitive load tolerance tested (some depleted)
    ("cognitive_engagement", "cognitive_load_tolerance", 0.30, -1),
    # Analytical page → narrative transport decreased (analytical ≠ narrative)
    ("cognitive_engagement", "narrative_transport", 0.20, -1),
    # Analytical page → information seeking activated
    ("cognitive_engagement", "information_seeking", 0.25, +1),
    # Analytical page → construal becomes more concrete
    ("cognitive_engagement", "construal_fit", 0.15, -1),

    # ── Page arousal_seeking → emotional/motivational edges ──
    # High arousal page → emotional resonance primed
    ("arousal_seeking", "emotional_resonance", 0.40, +1),
    # High arousal → interoceptive (body-signal) awareness heightened
    ("arousal_seeking", "interoceptive_awareness", 0.25, +1),
    # High arousal → narrative transport enhanced (immersed)
    ("arousal_seeking", "narrative_transport", 0.20, +1),
    # High arousal → cognitive load tolerance reduced (bandwidth consumed)
    ("arousal_seeking", "cognitive_load_tolerance", 0.15, -1),

    # ── Page status_sensitivity → identity/brand edges ──
    # Status page → brand relationship depth matters more
    ("status_sensitivity", "brand_relationship_depth", 0.30, +1),
    # Status page → mimetic desire (wanting what high-status others have)
    ("status_sensitivity", "mimetic_desire", 0.25, +1),
    # Status page → value alignment matters (brand values = identity)
    ("status_sensitivity", "value_alignment", 0.20, +1),
    # Status page → linguistic style matching matters (register sensitivity)
    ("status_sensitivity", "linguistic_style", 0.15, +1),
]

# ── Additional shifts from non-NDF page signals ──
# These use specific PagePsychologicalProfile fields beyond the 7 NDF dims

_EXTENDED_SHIFT_RULES = {
    # prospect_frame from deep scoring
    "prospect_frame": [
        ("loss_aversion_intensity", 0.30, -1),  # Loss frame → loss aversion amplified
        ("regulatory_fit", 0.20, -1),            # Loss frame → prevention regulatory fit
        ("temporal_discounting", 0.15, +1),      # Loss frame → present urgency
    ],
    # endowment_effect from deep scoring
    "endowment_effect": [
        ("loss_aversion_intensity", 0.25, +1),   # Ownership language → loss aversion
        ("brand_relationship_depth", 0.15, +1),  # "Your X" → personal attachment
    ],
    # publisher_authority from page profile
    "publisher_authority": [
        ("persuasion_susceptibility", 0.15, +1),  # Authoritative page → more persuadable
        ("autonomy_reactance", 0.10, -1),          # Trust in source → less resistant
    ],
    # remaining_bandwidth from page profile
    "remaining_bandwidth_low": [
        ("cognitive_load_tolerance", 0.30, -1),   # Depleted bandwidth → can't process complex
        ("decision_entropy", 0.20, +1),            # Low bandwidth → harder to decide
        ("narrative_transport", 0.15, +1),          # Low bandwidth → susceptible to stories
    ],
    # content_freshness: breaking news
    "breaking_news": [
        ("temporal_discounting", 0.25, +1),       # Breaking → present-focused
        ("emotional_resonance", 0.20, +1),         # Breaking → emotionally activated
        ("social_proof_sensitivity", 0.15, +1),    # Breaking → seeking peer validation
    ],
    # immersion (CTV content)
    "ctv_immersion": [
        ("narrative_transport", 0.40, +1),         # Deep immersion → story susceptible
        ("emotional_resonance", 0.35, +1),          # Immersion → emotional priming
        ("cognitive_load_tolerance", 0.30, -1),     # Immersion → bandwidth depleted
        ("interoceptive_awareness", 0.20, +1),      # Immersion → body-state heightened
        ("autonomy_reactance", 0.15, -1),           # Immersion → guard lowered
    ],
}


# ============================================================================
# COMPUTE PAGE → EDGE SHIFT VECTOR
# ============================================================================

def compute_page_edge_shift(
    page_ndf: Dict[str, float],
    page_profile_fields: Optional[Dict[str, Any]] = None,
) -> Dict[str, float]:
    """Compute how the page shifts the buyer's position in edge-dimension space.

    Takes the page's NDF vector (7 dims) and optional extended fields,
    returns a shift vector over the 20 edge dimensions.

    The shift represents: "a buyer on THIS page is psychologically
    repositioned by this much along each edge dimension, relative to
    their baseline edge position."

    Args:
        page_ndf: 7-dimension NDF vector from page profile
        page_profile_fields: Optional extended fields (prospect_frame,
            publisher_authority, remaining_bandwidth, content_freshness,
            immersion_depth for CTV)

    Returns:
        Dict mapping edge dimension → shift value (typically -0.3 to +0.3)
    """
    shift = {dim: 0.0 for dim in _EDGE_DIMS}
    profile = page_profile_fields or {}

    # ── Apply NDF-based shifts ──
    for ndf_dim, edge_dim, weight, direction in _SHIFT_MATRIX:
        ndf_val = page_ndf.get(ndf_dim, 0.5)
        # Center at 0.5 neutral, compute deviation
        deviation = ndf_val - 0.5
        # For approach_avoidance, center is 0.0 and range is -1 to +1
        if ndf_dim == "approach_avoidance":
            deviation = ndf_val  # Already centered at 0
        contribution = deviation * weight * direction
        shift[edge_dim] += contribution

    # ── Apply extended signal shifts ──
    # Prospect Theory frame
    prospect_frame = profile.get("prospect_frame", 0.0)
    if abs(prospect_frame) > 0.2:
        for edge_dim, weight, direction in _EXTENDED_SHIFT_RULES.get("prospect_frame", []):
            shift[edge_dim] += prospect_frame * weight * direction

    # Endowment effect
    endowment = profile.get("endowment_effect", 0.0)
    if endowment > 0.1:
        for edge_dim, weight, direction in _EXTENDED_SHIFT_RULES.get("endowment_effect", []):
            shift[edge_dim] += endowment * weight * direction

    # Publisher authority
    pub_auth = profile.get("publisher_authority", 0.5)
    if pub_auth > 0.6:
        for edge_dim, weight, direction in _EXTENDED_SHIFT_RULES.get("publisher_authority", []):
            shift[edge_dim] += (pub_auth - 0.5) * weight * direction

    # Low remaining bandwidth
    bandwidth = profile.get("remaining_bandwidth", 0.5)
    if bandwidth < 0.3:
        for edge_dim, weight, direction in _EXTENDED_SHIFT_RULES.get("remaining_bandwidth_low", []):
            shift[edge_dim] += (0.5 - bandwidth) * weight * direction

    # Breaking news context
    if profile.get("content_freshness") == "breaking":
        for edge_dim, weight, direction in _EXTENDED_SHIFT_RULES.get("breaking_news", []):
            shift[edge_dim] += 0.5 * weight * direction  # Strong signal

    # CTV immersion
    immersion = profile.get("immersion_depth", 0.0)
    if immersion > 0.3:
        for edge_dim, weight, direction in _EXTENDED_SHIFT_RULES.get("ctv_immersion", []):
            shift[edge_dim] += immersion * weight * direction

    # Round all values
    return {k: round(v, 4) for k, v in shift.items()}


def apply_page_shift_to_edges(
    raw_edge_dimensions: Dict[str, float],
    page_shift: Dict[str, float],
    page_confidence: float = 0.5,
) -> Dict[str, float]:
    """Apply page shift vector to raw edge alignment dimensions.

    The shift is weighted by page confidence — a deeply scored page
    (confidence 0.8+) has more authority to shift edges than a
    domain-heuristic page (confidence 0.3).

    Returns page-shifted alignment vector. This replaces raw_edge_dimensions
    in mechanism scoring formulas.
    """
    shifted = {}
    # Scale shift by confidence (weak page intelligence = weak shift)
    shift_weight = min(1.0, page_confidence * 1.2)

    for dim in _EDGE_DIMS:
        raw = raw_edge_dimensions.get(dim, 0.5)
        page_delta = page_shift.get(dim, 0.0) * shift_weight
        shifted[dim] = round(max(0.0, min(1.0, raw + page_delta)), 4)

    return shifted


# ============================================================================
# PAGE-CONDITIONED GRADIENT PRIORITIES
# ============================================================================

def compute_page_conditioned_gradient(
    gradient_field: Dict[str, float],
    page_shift: Dict[str, float],
    raw_edge_dimensions: Dict[str, float],
    optimal_targets: Dict[str, float],
) -> List[Dict[str, Any]]:
    """Recompute gradient priorities accounting for page shift.

    A dimension where the page ALREADY shifts the buyer toward optimal
    is less valuable (the page did the work). A dimension where the page
    shifts AWAY from optimal is MORE valuable (the ad must compensate).

    This produces page-conditioned creative directions:
    "On THIS page, emphasize X because the page works against you on X,
     but don't worry about Y because the page already primes it."
    """
    priorities = []

    for dim, gradient_val in gradient_field.items():
        if dim not in raw_edge_dimensions:
            continue

        raw = raw_edge_dimensions.get(dim, 0.5)
        optimal = optimal_targets.get(dim, raw)
        page_delta = page_shift.get(dim, 0.0)

        # Raw gap (without page): how far from optimal
        raw_gap = optimal - raw

        # Page-shifted gap: the page already moved the buyer
        shifted_position = raw + page_delta
        shifted_gap = optimal - shifted_position

        # If page reduces the gap, this dimension is LESS valuable to emphasize
        # If page increases the gap, this dimension is MORE valuable
        page_effect = abs(shifted_gap) - abs(raw_gap)

        # Adjusted expected lift
        raw_lift = abs(gradient_val * raw_gap) * 100
        shifted_lift = abs(gradient_val * shifted_gap) * 100

        # Direction for creative
        if shifted_gap > 0.05:
            direction = "increase"
        elif shifted_gap < -0.05:
            direction = "decrease"
        else:
            direction = "maintain"  # Page already optimized this

        priorities.append({
            "dimension": dim,
            "gradient": round(gradient_val, 4),
            "raw_gap": round(raw_gap, 4),
            "page_shift": round(page_delta, 4),
            "shifted_gap": round(shifted_gap, 4),
            "raw_lift_pct": round(raw_lift, 2),
            "page_adjusted_lift_pct": round(shifted_lift, 2),
            "page_effect": "helps" if page_effect < -0.01 else ("hurts" if page_effect > 0.01 else "neutral"),
            "direction": direction,
            "creative_implication": _get_creative_implication(dim, shifted_gap, page_delta),
        })

    # Sort by page-adjusted lift (highest = most important to address in ad)
    priorities.sort(key=lambda x: x["page_adjusted_lift_pct"], reverse=True)
    return priorities


def _get_creative_implication(dim: str, gap: float, page_shift: float) -> str:
    """Generate human-readable creative direction for a dimension."""
    _IMPLICATIONS = {
        "regulatory_fit": {
            "increase": "Strengthen gain/promotion framing — page has NOT primed approach orientation",
            "decrease": "Use prevention/protection framing — page already primed approach, ad should protect gains",
            "maintain": "Page has aligned regulatory fit — maintain current framing direction",
        },
        "loss_aversion_intensity": {
            "increase": "Emphasize what buyer stands to LOSE — page context hasn't activated loss aversion yet",
            "decrease": "Reduce loss messaging — page has already activated strong loss aversion, ad should offer SOLUTION",
            "maintain": "Loss aversion is well-calibrated by page context",
        },
        "social_proof_sensitivity": {
            "increase": "Add social proof — page hasn't primed social validation",
            "decrease": "Social proof is saturated — use authority or evidence instead",
            "maintain": "Social proof at optimal level from page context",
        },
        "cognitive_load_tolerance": {
            "increase": "Buyer has bandwidth — use detailed evidence, comparisons, specifications",
            "decrease": "Buyer bandwidth depleted by page — simplify radically, emotional appeal only",
            "maintain": "Moderate complexity is fine",
        },
        "emotional_resonance": {
            "increase": "Increase emotional intensity — page is analytical, ad needs emotional hook",
            "decrease": "Reduce emotion — page already primed strong feelings, ad should be grounding",
            "maintain": "Emotional level well-matched to page context",
        },
        "autonomy_reactance": {
            "increase": "Use softer persuasion — buyer has high resistance, offer choice not direction",
            "decrease": "Direct recommendation works — page has lowered guard, buyer is receptive to guidance",
            "maintain": "Moderate directness appropriate",
        },
        "decision_entropy": {
            "increase": "Buyer is paralyzed — simplify choice, provide clear recommendation, reduce options",
            "decrease": "Buyer is decisive — present options, let them choose",
            "maintain": "Normal decision complexity",
        },
        "narrative_transport": {
            "increase": "Use storytelling — buyer is primed for narrative processing",
            "decrease": "Use data/evidence — buyer is in analytical mode, stories feel manipulative",
            "maintain": "Balanced approach works",
        },
        "construal_fit": {
            "increase": "Go abstract — talk about values, identity, big picture",
            "decrease": "Go concrete — specific features, prices, immediate benefits",
            "maintain": "Moderate abstraction level",
        },
        "temporal_discounting": {
            "increase": "Add urgency — buyer is future-oriented, needs pull to present action",
            "decrease": "Remove urgency — buyer is already present-focused, urgency feels pressuring",
            "maintain": "Temporal framing well-matched",
        },
        "persuasion_susceptibility": {
            "increase": "Subtle persuasion — buyer has high resistance to obvious tactics",
            "decrease": "Direct persuasion works — buyer is open to influence on this page",
            "maintain": "Moderate persuasion intensity",
        },
        "mimetic_desire": {
            "increase": "Show aspirational ownership — buyer primed to want what others have",
            "decrease": "Focus on individual value — buyer is in independent mode",
            "maintain": "Balanced social/individual framing",
        },
    }

    dim_map = _IMPLICATIONS.get(dim, {})
    if abs(gap) < 0.05:
        return dim_map.get("maintain", f"{dim}: maintain current approach")
    elif gap > 0:
        return dim_map.get("increase", f"{dim}: strengthen this dimension in ad")
    else:
        return dim_map.get("decrease", f"{dim}: reduce emphasis on this dimension")


# ============================================================================
# PAGE-CONDITIONED DECISION PROBABILITY
# ============================================================================

def compute_page_conditioned_probability(
    raw_probability: float,
    page_shift: Dict[str, float],
    page_confidence: float,
) -> Dict[str, Any]:
    """Adjust conversion probability estimate based on page context.

    Some pages amplify conversion probability (e.g., high-authority page
    for authority-based ad). Others suppress it (e.g., scarcity-skeptical
    page for scarcity-based ad).

    The adjustment is based on whether the page shift moves key dimensions
    TOWARD or AWAY from the profile that historically converts.
    """
    # Compute net shift quality: positive = page helps, negative = page hurts
    conversion_relevant_dims = [
        "persuasion_susceptibility", "loss_aversion_intensity",
        "social_proof_sensitivity", "emotional_resonance",
        "autonomy_reactance",  # Negative: high reactance hurts
    ]

    net_quality = 0.0
    for dim in conversion_relevant_dims:
        shift_val = page_shift.get(dim, 0.0)
        if dim == "autonomy_reactance":
            net_quality -= shift_val  # Less reactance = better
        else:
            net_quality += shift_val  # More of others = better (generally)

    # Scale by confidence
    adjustment = net_quality * page_confidence * 0.5  # Cap at ±25% adjustment

    adjusted_prob = max(0.01, min(0.99, raw_probability * (1 + adjustment)))

    return {
        "raw_probability": round(raw_probability, 4),
        "page_adjustment": round(adjustment, 4),
        "adjusted_probability": round(adjusted_prob, 4),
        "page_helps": adjustment > 0.02,
        "page_hurts": adjustment < -0.02,
        "net_shift_quality": round(net_quality, 4),
    }


# ============================================================================
# MASTER FUNCTION: Full Page-Edge Integration
# ============================================================================

def compute_full_page_edge_intelligence(
    page_profile,  # PagePsychologicalProfile
    raw_edge_dimensions: Dict[str, float],
    gradient_field: Optional[Dict[str, float]] = None,
    optimal_targets: Optional[Dict[str, float]] = None,
    raw_probability: float = 0.0,
) -> Dict[str, Any]:
    """Compute complete page-edge integration for the bilateral cascade.

    This is the single function the cascade should call to get
    page-conditioned intelligence. It replaces the current post-hoc
    modulation with deep integration at the edge level.

    PRIORITY: Uses full-width edge_dimensions (20-dim) when available.
    Falls back to NDF-based shift computation only when edge_dimensions
    is empty (NDF is the FALLBACK, not the primary pathway).

    Returns:
        {
            "page_edge_dims": {...},       # Page's own 20-dim profile (when available)
            "page_shift": {...},           # How page shifts each edge dim
            "shifted_alignment": {...},    # Page-adjusted 20-dim alignment
            "gradient_priorities": [...],  # Page-conditioned creative direction
            "probability": {...},          # Page-adjusted conversion probability
            "creative_implications": [...], # Top 5 creative directions for this page
            "scoring_method": str,         # "full_width" or "ndf_mapped"
        }
    """
    # ── PRIMARY: Use full-width edge dimensions if available ──
    page_edge_dims = {}
    scoring_method = "ndf_mapped"
    if hasattr(page_profile, 'edge_dimensions') and page_profile.edge_dimensions:
        page_edge_dims = page_profile.edge_dimensions
        scoring_method = "full_width"

        # When we have full-width page edges, the "shift" is computed directly:
        # shift = page_edge_value - 0.5 (deviation from neutral)
        # This is MORE ACCURATE than mapping through the NDF shift matrix
        page_shift = {}
        for dim in _EDGE_DIMS:
            page_val = page_edge_dims.get(dim, 0.5)
            page_shift[dim] = round(page_val - 0.5, 4)

        page_confidence = getattr(page_profile, 'confidence', 0.5)
        shifted_alignment = apply_page_shift_to_edges(
            raw_edge_dimensions, page_shift, page_confidence,
        )

        # Page-conditioned gradient priorities
        gradient_priorities = []
        if gradient_field and optimal_targets:
            gradient_priorities = compute_page_conditioned_gradient(
                gradient_field, page_shift, raw_edge_dimensions, optimal_targets,
            )

        # Page-conditioned probability
        probability = {}
        if raw_probability > 0:
            probability = compute_page_conditioned_probability(
                raw_probability, page_shift, page_confidence,
            )

        creative_implications = []
        for pri in gradient_priorities[:5]:
            if pri["page_adjusted_lift_pct"] > 1.0:
                creative_implications.append({
                    "dimension": pri["dimension"],
                    "direction": pri["direction"],
                    "lift_pct": pri["page_adjusted_lift_pct"],
                    "page_effect": pri["page_effect"],
                    "action": pri["creative_implication"],
                })

        return {
            "page_edge_dims": page_edge_dims,
            "page_shift": page_shift,
            "shifted_alignment": shifted_alignment,
            "gradient_priorities": gradient_priorities,
            "probability": probability,
            "creative_implications": creative_implications,
            "page_confidence": page_confidence,
            "shift_magnitude": round(
                sum(abs(v) for v in page_shift.values()) / len(page_shift), 4
            ),
            "scoring_method": "full_width",
            "edge_scoring_tier": getattr(page_profile, 'edge_scoring_tier', ''),
        }

    # ── FALLBACK: Legacy profile without edge_dimensions ──
    # This path handles old cached profiles that only have NDF.
    # It will be phased out as all profiles are re-scored with edge dims.
    logger.debug("Page-edge bridge using NDF fallback (legacy profile)")
    page_ndf = page_profile.construct_activations if hasattr(page_profile, 'construct_activations') else {}
    extended_fields = {}

    if hasattr(page_profile, 'primed_decision_style'):
        ds = page_profile.primed_decision_style
        extended_fields["prospect_frame"] = ds.get("prospect_frame", 0.0)
        extended_fields["endowment_effect"] = ds.get("endowment_effect", 0.0)

    if hasattr(page_profile, 'publisher_authority'):
        extended_fields["publisher_authority"] = page_profile.publisher_authority
    if hasattr(page_profile, 'remaining_bandwidth'):
        extended_fields["remaining_bandwidth"] = page_profile.remaining_bandwidth
    if hasattr(page_profile, 'content_freshness'):
        extended_fields["content_freshness"] = page_profile.content_freshness
    if hasattr(page_profile, 'content_type') and page_profile.content_type == "ctv_content":
        # CTV: use immersion depth from bandwidth (inverted)
        extended_fields["immersion_depth"] = max(0, 1.0 - page_profile.remaining_bandwidth * 2.5)

    page_confidence = getattr(page_profile, 'confidence', 0.5)

    # 1. Compute page → edge shift vector
    page_shift = compute_page_edge_shift(page_ndf, extended_fields)

    # 2. Apply shift to raw edge dimensions
    shifted_alignment = apply_page_shift_to_edges(
        raw_edge_dimensions, page_shift, page_confidence,
    )

    # 3. Page-conditioned gradient priorities (if gradient available)
    gradient_priorities = []
    if gradient_field and optimal_targets:
        gradient_priorities = compute_page_conditioned_gradient(
            gradient_field, page_shift, raw_edge_dimensions, optimal_targets,
        )

    # 4. Page-conditioned probability
    probability = {}
    if raw_probability > 0:
        probability = compute_page_conditioned_probability(
            raw_probability, page_shift, page_confidence,
        )

    # 5. Top creative implications
    creative_implications = []
    for pri in gradient_priorities[:5]:
        if pri["page_adjusted_lift_pct"] > 1.0:
            creative_implications.append({
                "dimension": pri["dimension"],
                "direction": pri["direction"],
                "lift_pct": pri["page_adjusted_lift_pct"],
                "page_effect": pri["page_effect"],
                "action": pri["creative_implication"],
            })

    return {
        "page_shift": page_shift,
        "shifted_alignment": shifted_alignment,
        "gradient_priorities": gradient_priorities,
        "probability": probability,
        "creative_implications": creative_implications,
        "page_confidence": page_confidence,
        "shift_magnitude": round(
            sum(abs(v) for v in page_shift.values()) / len(page_shift), 4
        ),
        "scoring_method": "ndf_mapped",
        "edge_scoring_tier": "ndf_fallback",
        "page_edge_dims": {},
    }
