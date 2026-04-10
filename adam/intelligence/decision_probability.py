"""
Decision Probability Engine — The Core Equation
=================================================

Implements the Nonconscious Decision Probability Equation:

    P(purchase | message, NDF, context) = σ(Σ wᵢ · match_i(ndfᵢ, mᵢ) + bias)

Where:
    σ = sigmoid (maps to probability 0-1)
    wᵢ = learned weights per dimension (from effectiveness matrix)
    match_i = congruence function (NDF dimension × message feature alignment)
    ndfᵢ = buyer's NDF dimensions (7 core)
    mᵢ = message features (ad's persuasion profile per dimension)
    bias = category base conversion rate

The key insight from Matz et al. 2017: CONGRUENCE drives conversion.
Not absolute values, but alignment between buyer psychology and message
psychology. When both are promotion-focused, the match amplifies.
When one is promotion and the other is prevention, the match dampens
(potential backfire).

This replaces:
    - Categorical archetype → mechanism lookup (loses continuous signal)
    - Binary framing thresholds (bins 0.59 same as 0.01)
    - Fixed Matz constants for lift estimation (ignores cell-specific gradients)

With:
    - Continuous NDF × message congruence computation
    - Sigmoid-mapped purchase probability
    - Per-dimension match functions grounded in psychological theory
    - Learned weights from empirical effectiveness data
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _sigmoid(x: float) -> float:
    """Numerically stable sigmoid."""
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    ez = math.exp(x)
    return ez / (1.0 + ez)


def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


# ---------------------------------------------------------------------------
# NDF Dimension Match Functions (from NONCONSCIOUS_DECISION_MODELS.md Model 4)
# ---------------------------------------------------------------------------
# Each function computes congruence between a buyer's NDF dimension
# and the corresponding ad message feature. Congruence (same direction)
# amplifies; incongruence (opposite direction) dampens or backfires.

def match_approach_avoidance(buyer_alpha: float, ad_framing: float) -> float:
    """Match buyer's regulatory focus with ad framing.

    buyer_alpha: [-1, +1] — promotion (+) vs prevention (-)
    ad_framing: [-1, +1] — gain-framed (+) vs loss-framed (-)

    Congruence (both positive or both negative) = positive match.
    Incongruence (opposite signs) = potential backfire.
    """
    congruence = buyer_alpha * ad_framing
    intensity = abs(buyer_alpha) * abs(ad_framing)
    return congruence * (1.0 + intensity)


def match_temporal_horizon(buyer_tau: float, ad_urgency: float) -> float:
    """Match buyer's time orientation with ad urgency.

    buyer_tau: [0, 1] — present-focused (0) vs future-focused (1)
    ad_urgency: [0, 1] — low urgency (0) vs high urgency (1)

    Present-focused buyers respond to urgency. Future-focused resist it.
    """
    # Invert: present-focused (low tau) + high urgency = congruent
    buyer_present = 1.0 - buyer_tau
    return buyer_present * ad_urgency + buyer_tau * (1.0 - ad_urgency)


def match_social_calibration(buyer_sigma: float, ad_social_proof: float) -> float:
    """Match buyer's social orientation with ad social proof density.

    buyer_sigma: [0, 1] — independent (0) vs socially-referenced (1)
    ad_social_proof: [0, 1] — individual focus (0) vs social proof heavy (1)
    """
    return buyer_sigma * ad_social_proof + (1.0 - buyer_sigma) * (1.0 - ad_social_proof)


def match_uncertainty_tolerance(buyer_upsilon: float, ad_certainty: float) -> float:
    """Match buyer's uncertainty tolerance with ad message certainty.

    buyer_upsilon: [0, 1] — needs closure (0) vs open to ambiguity (1)
    ad_certainty: [0, 1] — suggestive (0) vs definitive (1)

    Low-tolerance buyers need definitive messaging.
    """
    buyer_needs_closure = 1.0 - buyer_upsilon
    return buyer_needs_closure * ad_certainty + buyer_upsilon * (1.0 - ad_certainty)


def match_status_sensitivity(buyer_rho: float, ad_prestige: float) -> float:
    """Match buyer's status motivation with ad premium positioning.

    buyer_rho: [0, 1] — practical (0) vs status-driven (1)
    ad_prestige: [0, 1] — functional (0) vs premium (1)
    """
    return buyer_rho * ad_prestige + (1.0 - buyer_rho) * (1.0 - ad_prestige)


def match_cognitive_engagement(buyer_kappa: float, ad_depth: float) -> float:
    """Match buyer's processing style with ad message depth.

    buyer_kappa: [0, 1] — peripheral processing (0) vs central processing (1)
    ad_depth: [0, 1] — heuristic/simple (0) vs data-driven/complex (1)

    Elaboration Likelihood Model: central processors need strong arguments.
    """
    return buyer_kappa * ad_depth + (1.0 - buyer_kappa) * (1.0 - ad_depth)


def match_arousal_seeking(buyer_lambda: float, ad_intensity: float) -> float:
    """Match buyer's arousal needs with ad emotional intensity.

    buyer_lambda: [0, 1] — calm preference (0) vs excitement seeking (1)
    ad_intensity: [0, 1] — subdued (0) vs high-energy (1)
    """
    return buyer_lambda * ad_intensity + (1.0 - buyer_lambda) * (1.0 - ad_intensity)


# Match function registry
_MATCH_FUNCTIONS = {
    "approach_avoidance": match_approach_avoidance,
    "temporal_horizon": match_temporal_horizon,
    "social_calibration": match_social_calibration,
    "uncertainty_tolerance": match_uncertainty_tolerance,
    "status_sensitivity": match_status_sensitivity,
    "cognitive_engagement": match_cognitive_engagement,
    "arousal_seeking": match_arousal_seeking,
}


# ---------------------------------------------------------------------------
# Default learned weights (from effectiveness matrix empirical data)
# ---------------------------------------------------------------------------
# These are the wᵢ in the decision equation. They represent how much
# each dimension's congruence contributes to purchase probability.
# Initial values from Matz et al. (2017) + research synthesis.
#
# At startup, these should be overridden by gradient field magnitudes
# from Neo4j BayesianPrior nodes. The hardcoded values are fallback
# priors for cold-start or when gradient fields are unavailable.

_DEFAULT_DIMENSION_WEIGHTS: Dict[str, float] = {
    "approach_avoidance": 1.8,    # Regulatory focus is the strongest predictor
    "temporal_horizon": 1.2,      # Temporal construal moderates urgency effects
    "social_calibration": 1.5,    # Social proof susceptibility varies widely
    "uncertainty_tolerance": 1.3,  # Need for closure drives mechanism receptivity
    "status_sensitivity": 1.0,    # Status signaling moderates positioning
    "cognitive_engagement": 1.4,  # ELM route is a strong moderator
    "arousal_seeking": 0.9,       # Arousal match matters but less predictive
}

# Mutable: overridden by load_weights_from_gradient_field() at startup
_active_weights: Dict[str, float] = dict(_DEFAULT_DIMENSION_WEIGHTS)

# Category-level bias (base conversion rate in sigmoid space)
# Fallback values — in production these are computed from BayesianPrior
# nodes' empirical conversion rates per (category, archetype) cell.
_CATEGORY_BIAS: Dict[str, float] = {
    "beauty": -2.5,        # ~7.5% base CVR
    "electronics": -3.0,   # ~4.7% base CVR
    "health": -2.7,        # ~6.3% base CVR
    "fashion": -2.6,       # ~6.9% base CVR
    "food": -2.3,          # ~9.1% base CVR
    "automotive": -3.5,    # ~2.9% base CVR
    "finance": -3.8,       # ~2.2% base CVR
    "default": -2.8,       # ~5.7% base CVR
}

# Mutable: overridden by load_category_bias_from_graph() at startup
_active_category_bias: Dict[str, float] = dict(_CATEGORY_BIAS)


def load_weights_from_gradient_field(gradient_field: Any) -> bool:
    """Replace hardcoded dimension weights with gradient-field magnitudes.

    Called at startup when gradient fields are available. The gradient
    magnitude for each dimension tells us how much that dimension
    contributes to conversion — a data-learned replacement for the
    theory-based defaults.

    Maps from gradient dimension names to NDF match function names.
    """
    global _active_weights

    if not gradient_field or not hasattr(gradient_field, "gradients"):
        return False

    # Gradient dim → NDF dimension mapping
    _GRAD_TO_NDF = {
        "regulatory_fit": "approach_avoidance",
        "construal_fit": "temporal_horizon",
        "personality_alignment": "social_calibration",
        "emotional_resonance": "arousal_seeking",
        "value_alignment": "status_sensitivity",
        "persuasion_confidence": "uncertainty_tolerance",
    }

    updated = 0
    for grad_dim, ndf_dim in _GRAD_TO_NDF.items():
        grad = gradient_field.gradients.get(grad_dim)
        if grad is not None and abs(grad) > 0.01:
            # Raw gradient magnitude → weight. No magic scaling factor.
            # Preserve relative ordering from data, but ensure minimum
            # contribution so no dimension is fully zeroed out.
            _active_weights[ndf_dim] = max(0.3, abs(grad))
            updated += 1

    if updated > 0:
        logger.info(
            "Decision weights updated from gradient field: %d/%d dims",
            updated, len(_GRAD_TO_NDF),
        )
    return updated > 0


def load_category_bias_from_graph(category_rates: Dict[str, float]) -> bool:
    """Replace static category bias with empirical conversion rates.

    Args:
        category_rates: {category: empirical_conversion_rate} from
            BayesianPrior nodes or outcome tracking.
    """
    global _active_category_bias

    if not category_rates:
        return False

    import math
    updated = 0
    for cat, rate in category_rates.items():
        if 0.001 < rate < 0.999:
            # Convert conversion rate → sigmoid bias: log(p / (1-p))
            _active_category_bias[cat.lower()] = round(math.log(rate / (1.0 - rate)), 2)
            updated += 1

    if updated > 0:
        logger.info("Category bias updated from empirical rates: %d categories", updated)
    return updated > 0


# ---------------------------------------------------------------------------
# Message Feature Extraction
# ---------------------------------------------------------------------------

def extract_message_features(
    edge_dimensions: Optional[Dict[str, float]] = None,
    ad_profile: Optional[Dict[str, Any]] = None,
    mechanism_scores: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """Extract ad message features aligned to the 7 NDF dimensions.

    Maps from edge dimensions and ad profile to the message feature
    vector that the congruence functions consume.

    Returns: {dimension_name: message_feature_value} all in [0, 1] or [-1, 1]
    """
    features: Dict[str, float] = {
        "approach_avoidance": 0.0,
        "temporal_horizon": 0.5,
        "social_calibration": 0.5,
        "uncertainty_tolerance": 0.5,
        "status_sensitivity": 0.5,
        "cognitive_engagement": 0.5,
        "arousal_seeking": 0.5,
    }

    if edge_dimensions:
        # Map bilateral edge dimensions → NDF message features
        reg_fit = edge_dimensions.get("regulatory_fit", 0.5)
        features["approach_avoidance"] = _clamp(2.0 * reg_fit - 1.0)  # [0,1] → [-1,1]
        features["temporal_horizon"] = edge_dimensions.get("construal_fit", 0.5)
        features["social_calibration"] = edge_dimensions.get("personality_alignment", 0.5)
        features["uncertainty_tolerance"] = 1.0 - edge_dimensions.get("emotional_resonance", 0.5)
        features["status_sensitivity"] = edge_dimensions.get("value_alignment", 0.5)
        features["cognitive_engagement"] = edge_dimensions.get("construal_fit", 0.5)
        features["arousal_seeking"] = edge_dimensions.get("emotional_resonance", 0.5)

    if ad_profile:
        # Enrich from ad-side profile (ProductDescription constructs)
        gain = float(ad_profile.get("ad_frame_gain", 0) or 0)
        loss = float(ad_profile.get("ad_frame_loss", 0) or 0)
        if gain + loss > 0:
            features["approach_avoidance"] = _clamp(gain - loss)

        abstract = float(ad_profile.get("ad_construal_abstract", 0) or 0)
        concrete = float(ad_profile.get("ad_construal_concrete", 0) or 0)
        if abstract + concrete > 0:
            features["cognitive_engagement"] = abstract / (abstract + concrete)

        bp = ad_profile.get("brand_personality", {})
        if isinstance(bp, dict):
            sophistication = float(bp.get("sophistication", 0) or 0)
            features["status_sensitivity"] = min(1.0, sophistication)

    if mechanism_scores:
        # Social proof score → social calibration of the message
        features["social_calibration"] = max(
            features["social_calibration"],
            mechanism_scores.get("social_proof", 0),
        )
        features["arousal_seeking"] = max(
            features["arousal_seeking"],
            mechanism_scores.get("scarcity", 0) * 0.7 + mechanism_scores.get("curiosity", 0) * 0.3,
        )

    return features


# ---------------------------------------------------------------------------
# The Decision Probability Equation
# ---------------------------------------------------------------------------

@dataclass
class DecisionProbabilityResult:
    """Output of the decision probability computation."""

    # The probability
    purchase_probability: float = 0.0

    # Per-dimension breakdown
    dimension_matches: Dict[str, float] = field(default_factory=dict)
    dimension_contributions: Dict[str, float] = field(default_factory=dict)

    # Components
    weighted_sum: float = 0.0
    category_bias: float = 0.0

    # Congruence analysis
    congruent_dimensions: List[str] = field(default_factory=list)
    incongruent_dimensions: List[str] = field(default_factory=list)
    backfire_risk: float = 0.0

    # Continuous creative parameters (replaces categorical bins)
    framing_weight: float = 0.0       # [-1, +1]: -1=pure loss, +1=pure gain
    construal_weight: float = 0.5     # [0, 1]: 0=concrete, 1=abstract
    urgency_weight: float = 0.3       # [0, 1]: 0=none, 1=maximum
    social_proof_weight: float = 0.5  # [0, 1]: 0=individual, 1=collective
    depth_weight: float = 0.5         # [0, 1]: 0=peripheral, 1=central
    arousal_weight: float = 0.5       # [0, 1]: 0=calm, 1=intense
    status_weight: float = 0.5        # [0, 1]: 0=practical, 1=premium

    reasoning: List[str] = field(default_factory=list)


def compute_decision_probability(
    buyer_ndf: Dict[str, float],
    message_features: Dict[str, float],
    category: str = "",
    dimension_weights: Optional[Dict[str, float]] = None,
    page_ndf: Optional[Dict[str, float]] = None,
    gradient_field: Optional[Any] = None,
    buyer_edge_dimensions: Optional[Dict[str, float]] = None,
) -> DecisionProbabilityResult:
    """Compute P(purchase | buyer psychology, message features, context).

    Core equation:
        P = σ(Σ wᵢ · match_i(buyerᵢ, messageᵢ) + Σ wⱼ · edge_congruenceⱼ + bias)

    The first sum runs over the 7 NDF match functions (Matz et al. 2017).
    The second sum runs over any additional bilateral edge dimensions
    provided in buyer_edge_dimensions. This extends the equation from
    7 to 20+ dimensions without losing backward compatibility.

    When buyer_edge_dimensions is provided, the equation captures
    13 additional psychological alignment signals (narrative_transport,
    loss_aversion_intensity, autonomy_reactance, etc.) that NDF
    compression discards.

    Args:
        buyer_ndf: 7 NDF dimensions for this buyer (backward compatibility)
        message_features: 7 corresponding features of the ad message
        category: Product category for bias term
        dimension_weights: Override learned weights (from gradient field)
        page_ndf: Page psychological profile for trilateral congruence
        gradient_field: If available, use gradient magnitudes as weights
        buyer_edge_dimensions: Full 20+ bilateral edge dimensions (preferred)

    Returns:
        DecisionProbabilityResult with probability + per-dimension breakdown
    """
    result = DecisionProbabilityResult()

    # Use active weights (populated from gradient field at startup, or defaults)
    weights = dict(_active_weights)
    if dimension_weights:
        weights.update(dimension_weights)
    elif gradient_field and hasattr(gradient_field, "gradients"):
        # Per-query gradient field override (e.g., category-specific gradient)
        for dim, grad in gradient_field.gradients.items():
            if dim in weights and abs(grad) > 0.01:
                weights[dim] = max(0.3, abs(grad))

    # Category bias (from empirical rates when available, else static defaults)
    cat_key = category.lower().replace("_", "").replace(" ", "") if category else "default"
    for k in _active_category_bias:
        if k in cat_key:
            cat_key = k
            break
    else:
        cat_key = "default"
    bias = _active_category_bias.get(cat_key, _active_category_bias.get("default", -2.8))
    result.category_bias = bias

    # Compute per-dimension congruence matches
    weighted_sum = bias
    for dim, match_fn in _MATCH_FUNCTIONS.items():
        buyer_val = buyer_ndf.get(dim, 0.5)
        message_val = message_features.get(dim, 0.5)
        w = weights.get(dim, 1.0)

        # Compute bilateral match (buyer × message)
        raw_match = match_fn(buyer_val, message_val)

        # Trilateral modulation: page psychological state amplifies/dampens
        if page_ndf:
            page_val = page_ndf.get(dim, 0.5)
            # Page alignment: how much the page primes this dimension
            # High page value on this dimension = the page has activated
            # this psychological channel, making the buyer more receptive
            page_alignment = 0.5 + (page_val - 0.5) * 0.5  # [0.25, 0.75]
            raw_match *= (0.5 + page_alignment)  # [0.75x, 1.25x]

        contribution = w * raw_match
        weighted_sum += contribution

        result.dimension_matches[dim] = round(raw_match, 4)
        result.dimension_contributions[dim] = round(contribution, 4)

        if raw_match > 0.1:
            result.congruent_dimensions.append(dim)
        elif raw_match < -0.1:
            result.incongruent_dimensions.append(dim)

    # Extended bilateral edge dimensions (13 additional signals)
    # Each dimension contributes a simple congruence term: how far from 0.5
    # (neutral) the buyer is on this construct, weighted by gradient magnitude.
    # This captures psychological signals that NDF compression discards.
    extended_dims_used = 0
    if buyer_edge_dimensions:
        _EXTENDED_DIMS = [
            "persuasion_susceptibility", "cognitive_load_tolerance",
            "narrative_transport", "social_proof_sensitivity",
            "loss_aversion_intensity", "temporal_discounting",
            "brand_relationship_depth", "autonomy_reactance",
            "information_seeking", "mimetic_desire",
            "interoceptive_awareness", "cooperative_framing_fit",
            "decision_entropy",
        ]
        for dim in _EXTENDED_DIMS:
            val = buyer_edge_dimensions.get(dim)
            if val is None:
                continue

            # Congruence = deviation from neutral (0.5)
            # Strong signal in either direction = more informative
            deviation = val - 0.5
            # Weight by gradient magnitude (data-learned, no arbitrary scaling)
            w = 0.8  # fallback when no gradient available
            if gradient_field and hasattr(gradient_field, "gradients"):
                grad = gradient_field.gradients.get(dim)
                if grad is not None:
                    w = abs(grad) if abs(grad) > 0.01 else 0.0
            elif dimension_weights and dim in dimension_weights:
                w = dimension_weights[dim]

            contribution = w * deviation
            weighted_sum += contribution
            extended_dims_used += 1

            result.dimension_matches[dim] = round(deviation, 4)
            result.dimension_contributions[dim] = round(contribution, 4)

            if deviation > 0.1:
                result.congruent_dimensions.append(dim)
            elif deviation < -0.1:
                result.incongruent_dimensions.append(dim)

    result.weighted_sum = round(weighted_sum, 4)
    result.purchase_probability = round(_sigmoid(weighted_sum), 4)

    # Backfire risk: fraction of dimensions that are incongruent
    total_dims = len(_MATCH_FUNCTIONS) + extended_dims_used
    result.backfire_risk = round(
        len(result.incongruent_dimensions) / max(total_dims, 1), 3
    )

    # Derive continuous creative parameters from match scores
    # These replace the categorical bins (gain/loss/mixed, etc.)
    aa_match = result.dimension_matches.get("approach_avoidance", 0)
    result.framing_weight = _clamp(aa_match)  # [-1, +1] continuous

    result.construal_weight = max(0, min(1,
        0.5 + result.dimension_matches.get("cognitive_engagement", 0) * 0.5
    ))
    result.urgency_weight = max(0, min(1,
        0.5 - result.dimension_matches.get("temporal_horizon", 0) * 0.5
    ))
    result.social_proof_weight = max(0, min(1,
        0.5 + result.dimension_matches.get("social_calibration", 0) * 0.5
    ))
    result.depth_weight = max(0, min(1,
        0.5 + result.dimension_matches.get("cognitive_engagement", 0) * 0.5
    ))
    result.arousal_weight = max(0, min(1,
        0.5 + result.dimension_matches.get("arousal_seeking", 0) * 0.5
    ))
    result.status_weight = max(0, min(1,
        0.5 + result.dimension_matches.get("status_sensitivity", 0) * 0.5
    ))

    # Reasoning
    top_congruent = sorted(
        result.dimension_contributions.items(), key=lambda x: x[1], reverse=True
    )[:3]
    for dim, contrib in top_congruent:
        match = result.dimension_matches[dim]
        result.reasoning.append(
            f"{dim}: match={match:+.3f}, contribution={contrib:+.3f} "
            f"(buyer={buyer_ndf.get(dim, 0):.2f}, message={message_features.get(dim, 0):.2f})"
        )

    if result.backfire_risk > 0.3:
        result.reasoning.append(
            f"WARNING: {len(result.incongruent_dimensions)} incongruent dimensions "
            f"({', '.join(result.incongruent_dimensions)}). "
            f"Backfire risk: {result.backfire_risk:.0%}"
        )

    if page_ndf:
        result.reasoning.append(
            f"Trilateral: page modulated {total_dims} dimensions "
            f"(page α={page_ndf.get('approach_avoidance', 0):+.2f}, "
            f"σ={page_ndf.get('social_calibration', 0):.2f})"
        )

    return result
