# =============================================================================
# Resonance Engineering — Cold Start Theory Priors
# Location: adam/retargeting/resonance/cold_start.py
# =============================================================================

"""
Theory-driven mechanism ideal vectors for Resonance Engineering cold start.

Before the system has conversion data conditioned on page mindstate, it
uses THEORY PRIORS to estimate which page environments amplify each mechanism.
These are derived from the psychological research in Enhancement #33's
16 research domains.

Each mechanism has a 32-dimensional "ideal page mindstate vector" — the
page psychological field that maximally amplifies that mechanism's effectiveness.

Stage A resonance: resonance_multiplier = sigmoid(dot(page_mindstate, ideal_vector) / temperature)

As data accumulates, Stage B (empirical logistic regression) and Stage C
(neural network) override these theory priors. But the theory priors
ensure the system makes REASONABLE placement decisions from day one.
"""

import numpy as np
from typing import Dict

from adam.retargeting.resonance.models import (
    PageMindstateVector,
    EDGE_DIM_NAMES,
    NDF_DIM_NAMES,
    ENV_DIM_NAMES,
    MINDSTATE_DIM_COUNT,
)


def _build_ideal_vector(**kwargs) -> np.ndarray:
    """Build a 32-dim ideal vector from named dimension values.

    Unspecified dimensions default to 0.0 (neutral — no preference).
    Positive values = page should have HIGH value on this dimension.
    Negative values = page should have LOW value on this dimension.
    """
    vec = np.zeros(MINDSTATE_DIM_COUNT)
    all_dims = EDGE_DIM_NAMES + NDF_DIM_NAMES + ENV_DIM_NAMES

    for dim_name, value in kwargs.items():
        if dim_name in all_dims:
            idx = all_dims.index(dim_name)
            vec[idx] = value

    return vec


# ─────────────────────────────────────────────────────────────────────
# MECHANISM IDEAL VECTORS
# Each mechanism's ideal page mindstate for maximum resonance.
# Values range from -0.5 (page should be LOW on this dim) to
# +0.5 (page should be HIGH on this dim). 0.0 = no preference.
# ─────────────────────────────────────────────────────────────────────

MECHANISM_IDEAL_VECTORS: Dict[str, np.ndarray] = {
    # --- EVIDENCE_PROOF (Domain 3: Scaffolding) ---
    # Works best on analytical, high-authority pages with central processing
    "evidence_proof": _build_ideal_vector(
        information_seeking=0.4,
        cognitive_engagement=0.4,
        publisher_authority=0.5,
        cognitive_load=0.3,             # Medium load (engaged but not overwhelmed)
        emotional_arousal=-0.2,         # Low arousal (calm, analytical)
        remaining_bandwidth=0.3,
        social_proof_sensitivity=0.2,
    ),

    # --- NARRATIVE_TRANSPORTATION (Domain 5: Green & Brock) ---
    # Works best on warm, story-driven pages with peripheral processing
    "narrative_transportation": _build_ideal_vector(
        emotional_resonance=0.5,
        narrative_transport=0.5,
        emotional_valence=0.3,          # Positive valence
        emotional_arousal=0.3,          # Moderate arousal
        cognitive_load=-0.3,            # Low cognitive load (immersive)
        remaining_bandwidth=0.4,        # High bandwidth (attention available)
        cooperative_framing_fit=0.2,
    ),

    # --- SOCIAL_PROOF_MATCHED (Domain 12: Bandura) ---
    # Works best on community pages with visible social signals
    "social_proof_matched": _build_ideal_vector(
        social_proof_sensitivity=0.5,
        social_calibration=0.4,
        mimetic_desire=0.3,
        emotional_valence=0.2,
        publisher_authority=0.2,
        cooperative_framing_fit=0.3,
    ),

    # --- AUTONOMY_RESTORATION (Domain 8: SDT) ---
    # Works best on low-pressure, choice-rich pages
    "autonomy_restoration": _build_ideal_vector(
        autonomy_reactance=-0.4,        # Low reactance on the page
        remaining_bandwidth=0.3,
        emotional_valence=0.2,
        cognitive_load=-0.2,
        persuasion_susceptibility=-0.3, # Page doesn't feel "salesy"
    ),

    # --- CONSTRUAL_SHIFT (Domain 9: CLT) ---
    # Works best when page construal CONTRASTS with the mechanism's target
    "construal_shift": _build_ideal_vector(
        cognitive_engagement=0.3,
        temporal_horizon=0.2,
        information_seeking=0.3,
        emotional_arousal=-0.1,
        remaining_bandwidth=0.3,
    ),

    # --- OWNERSHIP_REACTIVATION (Domain 10: Endowment) ---
    # Works best on pages that prime possession/investment thinking
    "ownership_reactivation": _build_ideal_vector(
        emotional_resonance=0.3,
        temporal_discounting=-0.2,      # Long-term thinking
        loss_aversion_intensity=0.3,
        brand_relationship_depth=0.3,
        emotional_valence=0.2,
    ),

    # --- IMPLEMENTATION_INTENTION (Domain 14: Gollwitzer) ---
    # Works best on action-oriented, concrete, low-complexity pages
    "implementation_intention": _build_ideal_vector(
        cognitive_load=-0.3,            # Simple pages
        remaining_bandwidth=0.4,        # High bandwidth for action
        temporal_horizon=-0.2,          # Near-term focus
        approach_avoidance=0.3,         # Approach motivation
        emotional_arousal=0.2,          # Enough arousal to act
    ),

    # --- MICRO_COMMITMENT (Domain 6: FITD) ---
    # Works best on interactive, low-stakes pages
    "micro_commitment": _build_ideal_vector(
        cognitive_load=-0.3,
        remaining_bandwidth=0.3,
        persuasion_susceptibility=0.2,
        approach_avoidance=0.2,
        social_calibration=0.2,
    ),

    # --- DISSONANCE_ACTIVATION (Domain 11: Festinger) ---
    # Works best on pages that prime self-concept / identity
    "dissonance_activation": _build_ideal_vector(
        personality_alignment=0.3,
        emotional_resonance=0.2,
        cognitive_engagement=0.3,
        status_sensitivity=0.2,
    ),

    # --- LOSS_FRAMING (Domain 10: Loss aversion) ---
    # Works best on prevention-oriented pages with negative valence
    "loss_framing": _build_ideal_vector(
        emotional_valence=-0.3,         # Negative valence primes loss
        loss_aversion_intensity=0.4,
        approach_avoidance=-0.3,        # Prevention/avoidance frame
        emotional_arousal=0.3,          # High arousal amplifies urgency
        temporal_horizon=-0.3,          # Near-term urgency
    ),

    # --- ANXIETY_RESOLUTION (Domain 2: Rupture repair) ---
    # COUNTERINTUITIVE: may work on POSITIVE-valence pages via contrast
    # (Hypothesis to test in evolutionary engine)
    "anxiety_resolution": _build_ideal_vector(
        emotional_valence=-0.2,         # Slight negative (primes anxiety)
        publisher_authority=0.4,        # High authority resolves anxiety
        social_proof_sensitivity=0.3,
        brand_relationship_depth=0.2,
        emotional_arousal=0.2,
    ),

    # --- FRUSTRATION_CONTROL (Domain 3: Scaffolding) ---
    # Works best on simple, clear, low-cognitive-load pages
    "frustration_control": _build_ideal_vector(
        cognitive_load=-0.4,            # Very low load
        remaining_bandwidth=0.4,
        emotional_valence=0.2,          # Positive = less frustration
        approach_avoidance=0.2,
    ),

    # --- NOVELTY_DISRUPTION (Domain 13: Dual process) ---
    # Works best on predictable pages (disruption stands out via CONTRAST)
    "novelty_disruption": _build_ideal_vector(
        cognitive_load=0.2,             # Medium load (pattern exists to disrupt)
        arousal_seeking=0.3,
        emotional_arousal=-0.2,         # Calm page = disruption is jarring
        decision_entropy=0.2,
    ),

    # --- VIVID_SCENARIO (Domain 5: Transportation) ---
    # Works best on warm, visual, experiential pages
    "vivid_scenario": _build_ideal_vector(
        emotional_resonance=0.4,
        narrative_transport=0.4,
        emotional_valence=0.3,
        emotional_arousal=0.3,
        interoceptive_awareness=0.3,    # Sensory awareness
        remaining_bandwidth=0.3,
    ),

    # --- PRICE_ANCHOR (Domain 9: CLT concrete) ---
    # Works best on comparison/deal pages with analytical processing
    "price_anchor": _build_ideal_vector(
        information_seeking=0.4,
        cognitive_engagement=0.3,
        loss_aversion_intensity=0.3,
        temporal_discounting=-0.2,      # Near-term value focus
        cognitive_load=0.2,             # Some load OK (comparison)
    ),

    # --- CLAUDE_ARGUMENT (Domain 16: LLM factual argument) ---
    # Works best on high-authority, high-trust, analytical pages
    # where readers are in central-processing mode and OPEN to arguments
    "claude_argument": _build_ideal_vector(
        publisher_authority=0.5,
        information_seeking=0.4,
        cognitive_engagement=0.4,
        remaining_bandwidth=0.4,        # Need bandwidth for novel argument
        emotional_arousal=-0.1,         # Calm enough to process
        persuasion_susceptibility=-0.2, # NOT "salesy" pages
    ),
}

# Temperature for sigmoid in Stage A resonance computation
# Higher temperature = smoother (more tolerant of mismatch)
# Lower temperature = sharper (more discriminating)
RESONANCE_TEMPERATURE = 3.0


def get_ideal_vector(mechanism: str) -> np.ndarray:
    """Get the theory-derived ideal page mindstate vector for a mechanism.

    Returns a 32-dim vector where positive values indicate the mechanism
    prefers HIGH values on that page dimension, and negative values
    indicate it prefers LOW values.
    """
    return MECHANISM_IDEAL_VECTORS.get(mechanism, np.zeros(MINDSTATE_DIM_COUNT))


def compute_theory_resonance(
    page_mindstate: PageMindstateVector,
    mechanism: str,
    temperature: float = RESONANCE_TEMPERATURE,
) -> float:
    """Compute Stage A (theory prior) resonance multiplier.

    resonance = sigmoid(dot(page_vector, ideal_vector) / temperature)

    Returns a multiplier in [0.3, 3.0]:
    - < 1.0: page dampens the mechanism
    - = 1.0: page is neutral
    - > 1.0: page amplifies the mechanism
    """
    page_vec = page_mindstate.to_numpy()
    ideal = get_ideal_vector(mechanism)

    # Dot product captures alignment between page field and ideal field
    alignment = float(np.dot(page_vec - 0.5, ideal))  # Center around 0.5

    # Sigmoid maps to (0, 1), then scale to (0.3, 3.0)
    import math
    sigmoid = 1.0 / (1.0 + math.exp(-alignment / temperature))
    multiplier = 0.3 + sigmoid * 2.7  # Range: [0.3, 3.0]

    return round(multiplier, 4)


def compute_all_mechanism_resonances(
    page_mindstate: PageMindstateVector,
) -> Dict[str, float]:
    """Compute theory resonance for all 16 mechanisms on this page.

    Returns {mechanism: resonance_multiplier} sorted by resonance.
    """
    resonances = {}
    for mechanism in MECHANISM_IDEAL_VECTORS:
        resonances[mechanism] = compute_theory_resonance(page_mindstate, mechanism)

    return dict(sorted(resonances.items(), key=lambda x: x[1], reverse=True))
