"""
DSP Enrichment Engine — NDF Bridge Layer
==========================================

Bidirectionally maps between the DSP engine's PsychologicalStateVector
(50+ dimensions) and ADAM's NDF profile (7+1 dimensions).

This is the critical connective tissue that enables:
    - DSP behavioral signals to flow into ADAM's atom DAG
    - ADAM's review-derived intelligence to enrich DSP state vectors
    - Inferential chains to span both real-time signals and empirical priors

Mapping:
    approach_avoidance  <-- promotion_focus - prevention_focus
    temporal_horizon    <-- construal_level
    social_calibration  <-- social_proof_susceptibility
    uncertainty_tolerance <-- inverse(choice_overload + low_confidence)
    status_sensitivity  <-- status_motivation
    cognitive_engagement <-- processing_mode (System1 vs System2)
    arousal_seeking     <-- arousal
    cognitive_velocity  <-- processing_fluency * attention
"""

import logging
from typing import Any, Dict, Optional

from adam.dsp.models import (
    ImpressionContext,
    PsychologicalStateVector,
    FunnelStage,
)

logger = logging.getLogger(__name__)


def state_vector_to_ndf(state: PsychologicalStateVector) -> Dict[str, float]:
    """
    Convert a DSP PsychologicalStateVector to ADAM's 7+1 NDF profile.

    This is the primary bridge: DSP impression-level inference -> ADAM
    atom system input. The NDF profile feeds into ADAM's 30-atom DAG,
    enabling the full inferential chain + Thompson Sampling machinery.
    """
    return state.to_ndf_profile()


def ndf_to_state_vector(
    ndf: Dict[str, float],
    ctx: Optional[ImpressionContext] = None,
) -> PsychologicalStateVector:
    """
    Expand an ADAM NDF profile back to a PsychologicalStateVector,
    enriched with impression-level signals if available.

    This enables ADAM's review-derived NDF profiles to be used with
    the DSP strategy generation and scoring engines.
    """
    state = PsychologicalStateVector()

    # Map NDF dimensions to state vector
    aa = ndf.get("approach_avoidance", 0.0)
    if aa > 0:
        state.promotion_focus = 0.5 + aa * 0.5
        state.prevention_focus = 0.5 - aa * 0.3
    else:
        state.promotion_focus = 0.5 + aa * 0.3
        state.prevention_focus = 0.5 - aa * 0.5

    state.construal_level = ndf.get("temporal_horizon", 0.5)
    state.social_proof_susceptibility = ndf.get("social_calibration", 0.5)

    ut = ndf.get("uncertainty_tolerance", 0.5)
    state.decision_confidence = 0.3 + ut * 0.4
    state.choice_overload_risk = max(0.0, 0.5 - ut * 0.5)

    state.status_motivation = ndf.get("status_sensitivity", 0.3)
    state.processing_mode = ndf.get("cognitive_engagement", 0.5)
    state.arousal = ndf.get("arousal_seeking", 0.5)

    cv = ndf.get("cognitive_velocity", 0.5)
    state.processing_fluency = cv
    state.attention_level = 0.4 + cv * 0.3

    # Enrich with impression context if available
    if ctx:
        state = _enrich_from_context(state, ctx)

    return state


def state_vector_to_request_context(
    state: PsychologicalStateVector,
    ctx: ImpressionContext,
) -> Dict[str, Any]:
    """
    Create an ADAM-compatible request context dict from DSP signals.

    This maps DSP impression data into the format expected by ADAM's
    atom system (RequestContext-compatible dict).
    """
    ndf = state.to_ndf_profile()

    return {
        "ndf_profile": ndf,
        "user_id": f"dsp_impression_{int(ctx.timestamp or 0)}",
        "request_id": f"dsp_{int(ctx.timestamp or 0)}",
        "product_category": ctx.product_category or ctx.content_category.value,
        "brand_name": ctx.brand_name,
        "device_type": ctx.device_type.value,
        "session_context": {
            "session_phase": ctx.session_phase,
            "session_duration_seconds": ctx.session_duration_seconds,
            "pages_viewed": ctx.pages_viewed,
            "referrer_type": ctx.referrer_type,
        },
        "behavioral_signals": {
            "scroll_velocity": ctx.scroll_velocity,
            "scroll_depth": ctx.scroll_depth,
            "mouse_velocity": ctx.mouse_velocity,
            "navigation_directness": ctx.navigation_directness,
            "comparison_behavior": ctx.comparison_behavior,
            "time_on_page": ctx.time_on_page_seconds,
        },
        "temporal_context": {
            "local_hour": ctx.local_hour,
            "day_of_week": ctx.day_of_week,
            "circadian_capacity": state.circadian_cognitive_capacity,
        },
        "content_context": {
            "content_category": ctx.content_category.value,
            "content_sentiment": ctx.content_sentiment,
            "content_arousal": ctx.content_arousal,
            "content_complexity": ctx.content_complexity,
        },
        "psychological_state": {
            "regulatory_frame": state.get_dominant_motivational_frame(),
            "processing_route": state.get_optimal_processing_route(),
            "cognitive_load": state.cognitive_load,
            "attention_level": state.attention_level,
            "vulnerability_flags": [v.value for v in state.vulnerability_flags],
        },
        "involvement_level": ctx.involvement_level,
        "price_point": ctx.price_point,
        "archetype_hint": ctx.archetype_hint,
    }


def merge_ndf_profiles(
    dsp_ndf: Dict[str, float],
    adam_ndf: Optional[Dict[str, float]] = None,
    dsp_weight: float = 0.6,
) -> Dict[str, float]:
    """
    Merge a DSP-inferred NDF profile with an ADAM-derived NDF profile.

    When ADAM has prior NDF data (from review intelligence, prior interactions,
    or archetype matching), blend it with the DSP's real-time inference.

    Args:
        dsp_ndf: NDF profile inferred from impression behavioral signals
        adam_ndf: NDF profile from ADAM's historical intelligence
        dsp_weight: Weight for DSP signal (0-1); complement goes to ADAM

    Returns:
        Merged NDF profile
    """
    if not adam_ndf:
        return dsp_ndf

    merged = {}
    adam_weight = 1.0 - dsp_weight

    for dim in [
        "approach_avoidance", "temporal_horizon", "social_calibration",
        "uncertainty_tolerance", "status_sensitivity", "cognitive_engagement",
        "arousal_seeking", "cognitive_velocity",
    ]:
        dsp_val = dsp_ndf.get(dim, 0.5)
        adam_val = adam_ndf.get(dim, 0.5)
        merged[dim] = dsp_weight * dsp_val + adam_weight * adam_val

    return merged


# =============================================================================
# Private helpers
# =============================================================================

def _enrich_from_context(
    state: PsychologicalStateVector,
    ctx: ImpressionContext,
) -> PsychologicalStateVector:
    """Enrich a state vector with impression context signals."""

    # Temporal
    state.chronotype_state = ctx.estimated_chronotype_state

    # Circadian
    if 9 <= ctx.local_hour <= 11:
        state.circadian_cognitive_capacity = 0.95
    elif 22 <= ctx.local_hour or ctx.local_hour <= 5:
        state.circadian_cognitive_capacity = 0.35
    else:
        state.circadian_cognitive_capacity = 0.65

    # Cognitive load from content
    state.cognitive_load = max(state.cognitive_load, ctx.estimated_cognitive_load)

    # Valence and arousal from content
    state.valence = ctx.content_sentiment
    state.arousal = max(state.arousal, ctx.content_arousal)

    # Fatigue from session
    fatigue = min(0.4, ctx.session_duration_seconds / 3600)
    fatigue += min(0.3, ctx.pages_viewed / 30)
    state.decision_fatigue_level = max(state.decision_fatigue_level, fatigue)

    # Funnel stage from navigation
    if ctx.navigation_directness > 0.8 and ctx.comparison_behavior > 0.5:
        state.funnel_stage = FunnelStage.PURCHASE
    elif ctx.comparison_behavior > 0.3:
        state.funnel_stage = FunnelStage.CONSIDERATION
    elif ctx.navigation_directness < 0.4 and ctx.category_changes > 2:
        state.funnel_stage = FunnelStage.AWARENESS

    return state
