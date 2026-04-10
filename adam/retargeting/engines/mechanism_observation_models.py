# =============================================================================
# Mechanism Observation Models
# Location: adam/retargeting/engines/mechanism_observation_models.py
# Unified System Evolution Directive, Section B.1
# =============================================================================

"""
For each of the 16 therapeutic mechanisms, defines a 20-dimensional vector
indicating which bilateral alignment dimensions it primarily affects.

These vectors serve three purposes:
1. Active Inference: compute epistemic value of deploying each mechanism
2. Counterfactual Learning: estimate what non-deployed mechanisms would have produced
3. Causal Discovery: weight causal edge evidence by mechanism targeting

Source: inverted from BARRIER_MECHANISM_CANDIDATES × DIMENSION_BARRIER_MAP.
Each mechanism's model reflects which alignment dimensions it operates on,
with weights reflecting primary (0.7-0.9) vs secondary (0.3-0.5) targeting.

The 20 dimensions match the bilateral edge (BRAND_CONVERTED) properties:
    regulatory_fit_score, construal_fit_score, personality_brand_alignment,
    emotional_resonance, value_alignment, evolutionary_motive_match,
    linguistic_style_matching, spending_pain_match, reactance_fit,
    self_monitoring_fit, processing_route_match, mental_simulation_resonance,
    optimal_distinctiveness_fit, involvement_weight_modifier, brand_trust_fit,
    identity_signaling_match, anchor_susceptibility_match, lay_theory_alignment,
    negativity_bias_match, persuasion_confidence_multiplier
"""

import logging
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# The 20 bilateral alignment dimensions in fixed order
DIMENSION_NAMES = [
    "regulatory_fit_score",
    "construal_fit_score",
    "personality_brand_alignment",
    "emotional_resonance",
    "value_alignment",
    "evolutionary_motive_match",
    "linguistic_style_matching",
    "spending_pain_match",
    "reactance_fit",
    "self_monitoring_fit",
    "processing_route_match",
    "mental_simulation_resonance",
    "optimal_distinctiveness_fit",
    "involvement_weight_modifier",
    "brand_trust_fit",
    "identity_signaling_match",
    "anchor_susceptibility_match",
    "lay_theory_alignment",
    "negativity_bias_match",
    "persuasion_confidence_multiplier",
]

_DIM_INDEX = {name: i for i, name in enumerate(DIMENSION_NAMES)}

# Mechanism observation models: which dimensions each mechanism targets.
# Weights: 0.7-0.9 = primary target, 0.3-0.5 = secondary effect
# Dimensions not listed default to 0.0
MECHANISM_OBSERVATION_MODELS: Dict[str, Dict[str, float]] = {
    "evidence_proof": {
        "brand_trust_fit": 0.9,
        "processing_route_match": 0.6,
        "persuasion_confidence_multiplier": 0.5,
        "emotional_resonance": 0.3,
    },
    "claude_argument": {
        # Claude generates novel factual arguments — broad but deep
        "brand_trust_fit": 0.7,
        "emotional_resonance": 0.6,
        "regulatory_fit_score": 0.5,
        "processing_route_match": 0.5,
        "personality_brand_alignment": 0.4,
        "value_alignment": 0.4,
        "persuasion_confidence_multiplier": 0.5,
    },
    "social_proof_matched": {
        "personality_brand_alignment": 0.8,
        "emotional_resonance": 0.6,
        "brand_trust_fit": 0.5,
        "identity_signaling_match": 0.4,
        "self_monitoring_fit": 0.3,
    },
    "narrative_transportation": {
        "emotional_resonance": 0.9,
        "personality_brand_alignment": 0.6,
        "negativity_bias_match": 0.5,
        "value_alignment": 0.4,
        "optimal_distinctiveness_fit": 0.3,
    },
    "autonomy_restoration": {
        "reactance_fit": 0.9,
        "regulatory_fit_score": 0.6,
        "persuasion_confidence_multiplier": 0.4,
    },
    "construal_shift": {
        "construal_fit_score": 0.9,
        "regulatory_fit_score": 0.7,
        "processing_route_match": 0.4,
    },
    "ownership_reactivation": {
        "emotional_resonance": 0.7,
        "spending_pain_match": 0.6,
        "anchor_susceptibility_match": 0.5,
        "value_alignment": 0.4,
    },
    "implementation_intention": {
        "processing_route_match": 0.8,
        "spending_pain_match": 0.5,
        "anchor_susceptibility_match": 0.4,
    },
    "micro_commitment": {
        "processing_route_match": 0.7,
        "reactance_fit": 0.4,
        "persuasion_confidence_multiplier": 0.3,
    },
    "loss_framing": {
        "negativity_bias_match": 0.8,
        "regulatory_fit_score": 0.7,
        "anchor_susceptibility_match": 0.6,
        "spending_pain_match": 0.5,
    },
    "anxiety_resolution": {
        "emotional_resonance": 0.7,
        "brand_trust_fit": 0.7,
        "negativity_bias_match": 0.6,
        "persuasion_confidence_multiplier": 0.4,
    },
    "frustration_control": {
        "processing_route_match": 0.9,
        "emotional_resonance": 0.4,
        "involvement_weight_modifier": 0.3,
    },
    "price_anchor": {
        "anchor_susceptibility_match": 0.9,
        "spending_pain_match": 0.7,
        "processing_route_match": 0.4,
    },
    "dissonance_activation": {
        "personality_brand_alignment": 0.8,
        "emotional_resonance": 0.5,
        "identity_signaling_match": 0.5,
        "self_monitoring_fit": 0.4,
    },
    "novelty_disruption": {
        "evolutionary_motive_match": 0.7,
        "processing_route_match": 0.5,
        "emotional_resonance": 0.3,
    },
    "vivid_scenario": {
        "emotional_resonance": 0.8,
        "mental_simulation_resonance": 0.7,
        "negativity_bias_match": 0.5,
        "value_alignment": 0.4,
    },
}


def build_observation_vectors() -> Dict[str, np.ndarray]:
    """Convert mechanism models to unit-normalized 20-dim numpy vectors.

    Returns: mechanism_id -> np.ndarray shape (20,)
    Dimensions not in a mechanism's model default to 0.0.
    Vectors are L2-normalized so epistemic values are comparable.
    """
    vectors = {}
    for mechanism_id, dim_weights in MECHANISM_OBSERVATION_MODELS.items():
        vec = np.zeros(len(DIMENSION_NAMES))
        for dim_name, weight in dim_weights.items():
            idx = _DIM_INDEX.get(dim_name)
            if idx is not None:
                vec[idx] = weight
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        vectors[mechanism_id] = vec
    return vectors


# Pre-computed at module load time
MECHANISM_VECTORS: Dict[str, np.ndarray] = build_observation_vectors()


def get_mechanism_vector(mechanism_id: str) -> np.ndarray:
    """Get the 20-dim observation vector for a mechanism.

    Returns zero vector for unknown mechanisms.
    """
    return MECHANISM_VECTORS.get(mechanism_id, np.zeros(len(DIMENSION_NAMES)))


def get_all_mechanism_vectors() -> Dict[str, np.ndarray]:
    """Get all mechanism observation vectors."""
    return MECHANISM_VECTORS.copy()
