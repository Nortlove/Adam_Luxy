# =============================================================================
# Prospect Theory Value Function for Bilateral Edge Computation
# Location: adam/retargeting/engines/prospect_theory.py
# Enhancement #34, Session 34-10
# =============================================================================

"""
Prospect Theory value function integration.

Current state: The bilateral edge computation uses LINEAR scaling of
alignment dimensions (0-1 range). But Kahneman & Tversky established
that psychological value follows an ASYMMETRIC S-shaped function:
- Gains are concave (diminishing returns)
- Losses are convex (accelerating pain)
- Losses weighted λ≈2.25× vs equivalent gains

This matters for INFORMATIV because:
1. A buyer who perceives the brand as SLIGHTLY below their trust threshold
   experiences disproportionate loss (loss aversion on trust_deficit)
2. A buyer who already trusts the brand gets diminishing returns from
   more trust signals (concave gains)
3. The reactance dimension (r=-0.79 with conversion) is a LOSS domain —
   perceived freedom threats are psychologically amplified

Integration: Applied to bilateral edge dimensions before composite
computation. Dimensions are classified as gain-domain or loss-domain
based on their reference point (archetype baseline). Values above
reference = gain (concave), below = loss (convex, λ-weighted).
"""

import logging
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Prospect Theory parameters (Tversky & Kahneman, 1992)
LOSS_AVERSION_LAMBDA = 2.25  # Losses hurt 2.25× vs equivalent gains
GAIN_CURVATURE_ALPHA = 0.88  # Gain sensitivity (concave: x^0.88)
LOSS_CURVATURE_BETA = 0.88   # Loss sensitivity (convex: x^0.88)

# Dimensions classified by domain type
# GAIN dimensions: higher is better for conversion (should be concave)
GAIN_DIMENSIONS = {
    "emotional_resonance",       # r=+0.80
    "brand_trust_fit",           # r=+0.78
    "regulatory_fit_score",      # r=+0.74
    "appeal_resonance",          # r=+0.62
    "personality_brand_alignment",  # r=+0.55
    "optimal_distinctiveness_fit",  # r=+0.34
    "value_alignment",           # r=+0.06
    "evolutionary_motive_match", # r=+0.07
    "anchor_susceptibility_match",  # r=+0.11
    "mental_ownership_match",    # r=+0.14
}

# LOSS dimensions: higher is WORSE for conversion (should be convex + λ-weighted)
LOSS_DIMENSIONS = {
    "reactance_fit",             # r=-0.79
    "negativity_bias_match",     # r=-0.78
    "spending_pain_match",       # r=-0.54
    "processing_route_match",    # r=-0.30 (overload = loss)
    "full_cosine_alignment",     # r=-0.40
    "involvement_weight_modifier",  # r=-0.58
}

# Reference points per archetype (baseline where gain/loss = 0)
# These are the population MEANS for each archetype, computed from
# bilateral edge data. Values above = gain domain, below = loss domain.
# For loss dimensions, the reference is the population mean as well,
# but exceeding it = LOSS (worse).
ARCHETYPE_REFERENCE_POINTS = {
    "careful_truster": {
        "emotional_resonance": 0.45, "brand_trust_fit": 0.40,
        "regulatory_fit_score": 0.35, "reactance_fit": 0.20,
        "negativity_bias_match": 0.25, "spending_pain_match": 0.35,
    },
    "status_seeker": {
        "emotional_resonance": 0.50, "brand_trust_fit": 0.45,
        "regulatory_fit_score": 0.10, "reactance_fit": 0.10,
        "negativity_bias_match": 0.15, "spending_pain_match": 0.25,
    },
    "easy_decider": {
        "emotional_resonance": 0.50, "brand_trust_fit": 0.45,
        "processing_route_match": 0.50, "reactance_fit": 0.15,
        "negativity_bias_match": 0.20, "spending_pain_match": 0.30,
    },
    "_default": {
        "emotional_resonance": 0.45, "brand_trust_fit": 0.42,
        "regulatory_fit_score": 0.30, "reactance_fit": 0.18,
        "negativity_bias_match": 0.22, "spending_pain_match": 0.32,
        "processing_route_match": 0.48, "personality_brand_alignment": 0.48,
    },
}


@dataclass
class ProspectTransformedValue:
    """Result of prospect theory transformation for a single dimension."""

    dimension: str
    raw_value: float
    reference_point: float
    domain: str  # "gain" or "loss"
    deviation: float  # raw - reference (positive = gain, negative = loss)
    prospect_value: float  # Transformed value
    amplification: float  # How much the transform changed the value


def prospect_value_function(
    x: float,
    reference: float = 0.5,
    is_loss_dimension: bool = False,
    lambda_: float = LOSS_AVERSION_LAMBDA,
    alpha: float = GAIN_CURVATURE_ALPHA,
    beta: float = LOSS_CURVATURE_BETA,
) -> float:
    """Kahneman-Tversky prospect theory value function.

    v(x) = (x - ref)^α           if x ≥ ref (gain)
    v(x) = -λ(ref - x)^β         if x < ref (loss)

    For loss dimensions (higher = worse), the roles are inverted:
    v(x) = -λ(x - ref)^β         if x > ref (exceeding threshold = loss)
    v(x) = (ref - x)^α           if x ≤ ref (below threshold = gain)
    """
    deviation = x - reference

    if is_loss_dimension:
        # For loss dims: EXCEEDING reference is a LOSS
        if deviation > 0:
            # Above reference = LOSS (amplified by λ)
            return -lambda_ * math.pow(abs(deviation), beta)
        else:
            # Below reference = GAIN (concave)
            return math.pow(abs(deviation), alpha)
    else:
        # For gain dims: normal prospect theory
        if deviation >= 0:
            # Above reference = GAIN (concave)
            return math.pow(deviation, alpha)
        else:
            # Below reference = LOSS (convex, λ-weighted)
            return -lambda_ * math.pow(abs(deviation), beta)


def apply_prospect_transform(
    bilateral_edge: Dict[str, float],
    archetype_id: str = "_default",
) -> Dict[str, ProspectTransformedValue]:
    """Apply prospect theory transformation to all bilateral edge dimensions.

    Returns transformed values that can be used in place of raw values
    for composite alignment computation.
    """
    refs = ARCHETYPE_REFERENCE_POINTS.get(
        archetype_id,
        ARCHETYPE_REFERENCE_POINTS["_default"],
    )

    transformed = {}
    for dim, raw_value in bilateral_edge.items():
        if dim in GAIN_DIMENSIONS or dim in LOSS_DIMENSIONS:
            is_loss = dim in LOSS_DIMENSIONS
            ref = refs.get(dim, 0.5)
            pv = prospect_value_function(raw_value, ref, is_loss)

            transformed[dim] = ProspectTransformedValue(
                dimension=dim,
                raw_value=raw_value,
                reference_point=ref,
                domain="loss" if is_loss else "gain",
                deviation=round(raw_value - ref, 4),
                prospect_value=round(pv, 4),
                amplification=round(abs(pv) - abs(raw_value - ref), 4),
            )

    return transformed


def prospect_weighted_composite(
    bilateral_edge: Dict[str, float],
    archetype_id: str = "_default",
    dim_weights: Optional[Dict[str, float]] = None,
) -> Tuple[float, Dict[str, ProspectTransformedValue]]:
    """Compute prospect-theory-weighted composite alignment.

    Like the standard composite but with S-shaped value function
    applied to each dimension before weighting. Losses (below
    reference) are amplified 2.25×.

    Returns:
        (composite_score, transform_details)
    """
    transformed = apply_prospect_transform(bilateral_edge, archetype_id)

    # Default weights from data-calibrated v6 (match_calculators.py)
    if dim_weights is None:
        dim_weights = {
            "emotional_resonance": 0.138, "brand_trust_fit": 0.125,
            "regulatory_fit_score": 0.087, "appeal_resonance": 0.083,
            "evolutionary_motive_match": 0.075, "reactance_fit": 0.059,
            "spending_pain_match": 0.054, "processing_route_match": 0.037,
            "personality_brand_alignment": 0.008,
            "negativity_bias_match": 0.019, "optimal_distinctiveness_fit": 0.025,
            "value_alignment": 0.030, "anchor_susceptibility_match": 0.033,
            "mental_ownership_match": 0.028,
        }

    composite = 0.0
    for dim, tv in transformed.items():
        w = abs(dim_weights.get(dim, 0.01))
        # Prospect value can be negative (losses) — weight preserves sign
        composite += tv.prospect_value * w

    # Normalize to 0-1 via sigmoid (prospect values can be negative)
    composite_norm = 1.0 / (1.0 + math.exp(-5.0 * composite))

    return round(composite_norm, 4), transformed
