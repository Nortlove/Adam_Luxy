#!/usr/bin/env python3
"""
INTELLIGENCE PREFETCH NODES
===========================

LangGraph nodes for pre-fetching intelligence from new data sources:
- Context Intelligence (Domain Mapping)
- Persuadability Intelligence (Criteo Uplift)
- Attribution Intelligence (Criteo Attribution)
- Temporal Psychology (Amazon 2015)
- Cross-Platform Validation (Amazon-Reddit)

These nodes integrate with the existing synergy orchestrator to provide
comprehensive multi-source intelligence BEFORE atoms execute.

Integration Flow:
    Request → [Pre-fetch ALL intelligence in parallel] → Atoms → Learning
    
New Pre-fetch Nodes:
1. prefetch_context_intelligence - Domain/mindset context
2. prefetch_persuadability - Persuadability segments
3. prefetch_attribution - Optimal sequences
4. prefetch_temporal_baselines - Historical patterns
5. prefetch_cross_platform - Validation confidence
6. prefetch_combined_enrichment - Unified enrichment
"""

import asyncio
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# CONTEXT INTELLIGENCE PRE-FETCH
# =============================================================================

async def prefetch_context_intelligence(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pre-fetch context intelligence based on ad placement domain.
    
    This node:
    - Detects the domain/placement context
    - Determines user mindset (informed, entertained, purchasing, etc.)
    - Provides mechanism adjustment factors
    - Recommends complexity and tone
    
    State Input:
        placement_domain: Domain where ad will be shown
        
    State Output:
        context_intelligence: {
            domain, category, mindset, attention_level,
            mechanism_adjustments, recommended_complexity, optimal_tone
        }
    """
    placement_domain = state.get("placement_domain", "")
    
    if not placement_domain:
        # No domain provided - return neutral context
        state["context_intelligence"] = {
            "domain": "unknown",
            "category": "unknown",
            "mindset": "unknown",
            "attention_level": "medium",
            "mechanism_adjustments": {},
            "confidence": 0.0,
        }
        return state
    
    try:
        from adam.intelligence.context_intelligence import (
            get_context_intelligence_service
        )
        
        service = get_context_intelligence_service()
        recommendation = service.get_context_recommendation(placement_domain)
        
        state["context_intelligence"] = {
            "domain": recommendation["domain"],
            "category": recommendation["category"],
            "mindset": recommendation["mindset"],
            "mindset_description": recommendation["mindset_description"],
            "attention_level": recommendation["attention_level"],
            "cognitive_load": recommendation["cognitive_load"],
            "purchase_intent": recommendation["purchase_intent"],
            "mechanism_adjustments": recommendation["mechanism_adjustments"],
            "recommended_mechanisms": recommendation["recommended_mechanisms"],
            "avoid_mechanisms": recommendation["avoid_mechanisms"],
            "recommended_complexity": recommendation["recommended_complexity"],
            "optimal_tone": recommendation["optimal_tone"],
            "confidence": recommendation["confidence"],
        }
        
        logger.info(
            f"Context intelligence pre-fetched: mindset={recommendation['mindset']}, "
            f"attention={recommendation['attention_level']}"
        )
        
    except Exception as e:
        logger.error(f"Error prefetching context intelligence: {e}")
        state["context_intelligence"] = {
            "domain": placement_domain,
            "category": "unknown",
            "mindset": "unknown",
            "attention_level": "medium",
            "mechanism_adjustments": {},
            "confidence": 0.0,
            "error": str(e),
        }
    
    return state


# =============================================================================
# PERSUADABILITY INTELLIGENCE PRE-FETCH
# =============================================================================

async def prefetch_persuadability_intelligence(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pre-fetch persuadability intelligence for the detected customer type.
    
    This node:
    - Calculates persuadability score for the granular type
    - Determines persuadability segment (highly_persuadable, resistant, etc.)
    - Provides targeting recommendations (bid multiplier, frequency cap)
    - Predicts uplift from advertising
    
    State Input:
        granular_type: {motivation, decision_style, emotional_intensity, ...}
        
    State Output:
        persuadability_intelligence: {
            score, segment, predicted_uplift, recommendation,
            bid_multiplier, frequency_cap, should_target
        }
    """
    granular_type = state.get("granular_type", {})
    
    motivation = granular_type.get("motivation", "functional_need")
    decision_style = granular_type.get("decision_style", "moderate")
    emotional_intensity = granular_type.get("emotional_intensity", "moderate")
    
    try:
        from adam.intelligence.persuadability_intelligence import (
            get_persuadability_service
        )
        
        service = get_persuadability_service()
        
        # Get prediction
        prediction = service.predict_for_segment(
            motivation=motivation,
            decision_style=decision_style,
            emotional_intensity=emotional_intensity,
        )
        
        # Get recommendation
        recommendation = service.get_segment_recommendation(
            prediction.persuadability_score
        )
        
        state["persuadability_intelligence"] = {
            "score": prediction.persuadability_score,
            "segment": recommendation["segment"],
            "predicted_uplift": prediction.predicted_uplift,
            "control_conversion": prediction.control_conversion,
            "treatment_conversion": prediction.treatment_conversion,
            "confidence_interval": {
                "lower": prediction.confidence_lower,
                "upper": prediction.confidence_upper,
            },
            "is_persuadable": prediction.is_persuadable,
            "recommendation": prediction.recommendation,
            "targeting": recommendation["targeting"],
            "expected_roi_multiplier": recommendation["expected_roi_multiplier"],
        }
        
        logger.info(
            f"Persuadability pre-fetched: score={prediction.persuadability_score:.0%}, "
            f"segment={recommendation['segment']}"
        )
        
    except Exception as e:
        logger.error(f"Error prefetching persuadability intelligence: {e}")
        state["persuadability_intelligence"] = {
            "score": 0.5,
            "segment": "unknown",
            "predicted_uplift": 0.0,
            "recommendation": "test",
            "error": str(e),
        }
    
    return state


# =============================================================================
# ATTRIBUTION INTELLIGENCE PRE-FETCH
# =============================================================================

async def prefetch_attribution_intelligence(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pre-fetch attribution intelligence for mechanism sequencing.
    
    This node:
    - Determines optimal mechanism sequence for the customer type
    - Calculates expected touchpoints needed
    - Provides position-specific mechanism recommendations
    - Compares sequence alternatives
    
    State Input:
        granular_type: {motivation, decision_style, emotional_intensity, ...}
        persuadability_intelligence: {score, ...}
        current_touchpoint: Current position in journey (optional)
        
    State Output:
        attribution_intelligence: {
            optimal_sequence, touchpoints_needed, first_touch_best,
            last_touch_best, current_recommendation, expected_lift
        }
    """
    granular_type = state.get("granular_type", {})
    persuadability = state.get("persuadability_intelligence", {})
    current_touchpoint = state.get("current_touchpoint", 0)
    
    motivation = granular_type.get("motivation", "functional_need")
    decision_style = granular_type.get("decision_style", "moderate")
    emotional_intensity = granular_type.get("emotional_intensity", "moderate")
    persuadability_score = persuadability.get("score", 0.5)
    
    try:
        from adam.intelligence.attribution_intelligence import (
            get_attribution_service, TouchpointPosition
        )
        
        service = get_attribution_service()
        
        # Get optimal sequence
        sequence = service.get_optimal_sequence(
            motivation=motivation,
            decision_style=decision_style,
            emotional_intensity=emotional_intensity,
            persuadability=persuadability_score,
        )
        
        # Get current position recommendation
        if current_touchpoint < len(sequence.sequence):
            current_mechanism, position_type = service.get_mechanism_at_position(
                position=current_touchpoint,
                total_touchpoints=sequence.touchpoints_needed,
                sequence=sequence.sequence,
            )
        else:
            current_mechanism = sequence.last_touch_best
            position_type = TouchpointPosition.LAST
        
        # Calculate sequence effectiveness
        effectiveness = service.calculate_sequence_effectiveness(sequence.sequence)
        
        state["attribution_intelligence"] = {
            "optimal_sequence": sequence.sequence,
            "touchpoints_needed": sequence.touchpoints_needed,
            "first_touch_best": sequence.first_touch_best,
            "last_touch_best": sequence.last_touch_best,
            "expected_lift": sequence.expected_lift,
            "confidence": sequence.confidence,
            "alternatives": sequence.alternatives,
            "current_touchpoint": current_touchpoint,
            "current_recommendation": {
                "mechanism": current_mechanism,
                "position_type": position_type.value,
            },
            "sequence_effectiveness": effectiveness,
        }
        
        logger.info(
            f"Attribution pre-fetched: sequence={' → '.join(sequence.sequence)}, "
            f"touchpoints={sequence.touchpoints_needed}"
        )
        
    except Exception as e:
        logger.error(f"Error prefetching attribution intelligence: {e}")
        state["attribution_intelligence"] = {
            "optimal_sequence": ["authority", "social_proof", "scarcity"],
            "touchpoints_needed": 3,
            "first_touch_best": "authority",
            "last_touch_best": "scarcity",
            "error": str(e),
        }
    
    return state


# =============================================================================
# TEMPORAL PSYCHOLOGY PRE-FETCH
# =============================================================================

async def prefetch_temporal_intelligence(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pre-fetch temporal baselines and authenticity intelligence.
    
    This node:
    - Gets historical baseline for the product category
    - Provides authenticity detection thresholds
    - Returns temporal pattern evolution data
    
    State Input:
        product_category: Product category
        review_sample: Optional sample review for authenticity check
        
    State Output:
        temporal_intelligence: {
            baseline, authenticity_threshold, evolution_data
        }
    """
    product_category = state.get("product_category", "")
    review_sample = state.get("review_sample", "")
    
    try:
        from adam.intelligence.temporal_psychology import (
            get_temporal_psychology_service
        )
        
        service = get_temporal_psychology_service()
        
        # Get baseline for category
        baseline = service.get_baseline(product_category)
        
        # Get authenticity threshold
        threshold = service.get_authenticity_threshold(product_category)
        
        state["temporal_intelligence"] = {
            "category": baseline.category,
            "year": baseline.year,
            "baseline_metrics": {
                "avg_review_length": baseline.avg_review_length,
                "emotional_intensity_mean": baseline.emotional_intensity_mean,
                "emotional_intensity_std": baseline.emotional_intensity_std,
                "avg_rating": baseline.avg_rating,
                "verified_purchase_ratio": baseline.verified_purchase_ratio,
            },
            "motivation_distribution": baseline.motivation_distribution,
            "decision_style_distribution": baseline.decision_style_distribution,
            "authenticity_markers": {
                "specific_detail_frequency": baseline.specific_detail_frequency,
                "temporal_language_frequency": baseline.temporal_language_frequency,
                "comparison_frequency": baseline.comparison_frequency,
                "personal_context_frequency": baseline.personal_context_frequency,
            },
            "authenticity_threshold": threshold,
        }
        
        # If we have a review sample, analyze authenticity
        if review_sample:
            authenticity = service.analyze_authenticity(
                review_text=review_sample,
                category=product_category,
                rating=state.get("review_rating", 4.0),
                verified_purchase=state.get("verified_purchase", True),
            )
            
            state["temporal_intelligence"]["authenticity_analysis"] = {
                "is_likely_authentic": authenticity.is_likely_authentic,
                "authenticity_score": authenticity.authenticity_score,
                "signals": authenticity.signals,
                "concerns": authenticity.concerns,
                "temporal_consistency": authenticity.temporal_consistency,
            }
        
        logger.info(
            f"Temporal intelligence pre-fetched: category={baseline.category}, "
            f"threshold={threshold:.0%}"
        )
        
    except Exception as e:
        logger.error(f"Error prefetching temporal intelligence: {e}")
        state["temporal_intelligence"] = {
            "category": product_category or "unknown",
            "authenticity_threshold": 0.5,
            "error": str(e),
        }
    
    return state


# =============================================================================
# CROSS-PLATFORM VALIDATION PRE-FETCH
# =============================================================================

async def prefetch_cross_platform_validation(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pre-fetch cross-platform confidence boosts.
    
    This node:
    - Gets confidence boost for the granular type based on cross-platform validation
    - Provides pattern consistency information
    
    State Input:
        granular_type: {motivation, decision_style, emotional_intensity, ...}
        
    State Output:
        cross_platform_validation: {
            confidence_boost, validated_patterns
        }
    """
    granular_type = state.get("granular_type", {})
    
    motivation = granular_type.get("motivation", "functional_need")
    decision_style = granular_type.get("decision_style", "moderate")
    emotional_intensity = granular_type.get("emotional_intensity", "moderate")
    
    try:
        from adam.intelligence.cross_platform_validation import (
            get_cross_platform_service
        )
        
        service = get_cross_platform_service()
        
        # Get confidence boost
        confidence_boost = service.get_confidence_boost(
            motivation=motivation,
            decision_style=decision_style,
            emotional_intensity=emotional_intensity,
        )
        
        state["cross_platform_validation"] = {
            "confidence_boost": confidence_boost,
            "motivation": motivation,
            "decision_style": decision_style,
            "emotional_intensity": emotional_intensity,
            "validated": confidence_boost > 0.1,
        }
        
        logger.info(
            f"Cross-platform validation pre-fetched: boost=+{confidence_boost:.0%}"
        )
        
    except Exception as e:
        logger.error(f"Error prefetching cross-platform validation: {e}")
        state["cross_platform_validation"] = {
            "confidence_boost": 0.0,
            "validated": False,
            "error": str(e),
        }
    
    return state


# =============================================================================
# COMBINED ENRICHMENT PRE-FETCH
# =============================================================================

async def prefetch_combined_intelligence_enrichment(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Combine all intelligence sources into unified enrichment.
    
    This node runs AFTER individual prefetch nodes and:
    - Applies context adjustments to mechanism effectiveness
    - Applies persuadability filtering to targeting
    - Applies attribution sequencing to mechanism selection
    - Applies temporal baselines to authenticity
    - Applies cross-platform boosts to confidence
    
    State Input:
        context_intelligence: From prefetch_context_intelligence
        persuadability_intelligence: From prefetch_persuadability_intelligence
        attribution_intelligence: From prefetch_attribution_intelligence
        temporal_intelligence: From prefetch_temporal_intelligence
        cross_platform_validation: From prefetch_cross_platform_validation
        mechanism_priors: Base mechanism effectiveness
        
    State Output:
        enriched_mechanism_scores: Fully adjusted mechanism scores
        enriched_confidence: Boosted confidence scores
        enriched_targeting: Combined targeting recommendations
    """
    # Get all intelligence
    context = state.get("context_intelligence", {})
    persuadability = state.get("persuadability_intelligence", {})
    attribution = state.get("attribution_intelligence", {})
    temporal = state.get("temporal_intelligence", {})
    cross_platform = state.get("cross_platform_validation", {})
    base_priors = state.get("mechanism_priors", {})
    
    # Start with base mechanism effectiveness
    enriched_scores = {}
    
    for mechanism, base_score in base_priors.items():
        score = base_score
        
        # Apply context adjustments
        context_adjustments = context.get("mechanism_adjustments", {})
        if mechanism in context_adjustments:
            score = score * context_adjustments[mechanism]
        
        enriched_scores[mechanism] = {
            "base_score": base_score,
            "context_adjusted": score,
            "context_adjustment": context_adjustments.get(mechanism, 1.0),
        }
    
    # Apply attribution sequencing
    current_position = attribution.get("current_touchpoint", 0)
    current_recommendation = attribution.get("current_recommendation", {})
    recommended_mechanism = current_recommendation.get("mechanism", "")
    
    if recommended_mechanism and recommended_mechanism in enriched_scores:
        # Boost recommended mechanism
        enriched_scores[recommended_mechanism]["sequence_boost"] = 1.2
        enriched_scores[recommended_mechanism]["final_score"] = (
            enriched_scores[recommended_mechanism]["context_adjusted"] * 1.2
        )
    
    # Calculate final scores for all
    for mechanism in enriched_scores:
        if "final_score" not in enriched_scores[mechanism]:
            enriched_scores[mechanism]["final_score"] = (
                enriched_scores[mechanism]["context_adjusted"]
            )
    
    # Calculate enriched confidence
    base_confidence = state.get("confidence", 0.7)
    cross_platform_boost = cross_platform.get("confidence_boost", 0.0)
    enriched_confidence = min(base_confidence + cross_platform_boost, 0.99)
    
    # Combined targeting
    persuadability_score = persuadability.get("score", 0.5)
    targeting = persuadability.get("targeting", {})
    
    enriched_targeting = {
        "should_target": persuadability_score >= 0.35,
        "priority": targeting.get("priority", "medium"),
        "bid_multiplier": targeting.get("bid_multiplier", 1.0),
        "frequency_cap": targeting.get("frequency_cap", 10),
        "recommended_complexity": context.get("recommended_complexity", "moderate"),
        "optimal_tone": context.get("optimal_tone", "balanced"),
        "authenticity_threshold": temporal.get("authenticity_threshold", 0.5),
    }
    
    state["enriched_mechanism_scores"] = enriched_scores
    state["enriched_confidence"] = enriched_confidence
    state["enriched_targeting"] = enriched_targeting
    state["enrichment_applied"] = True
    
    logger.info(
        f"Combined enrichment applied: confidence={enriched_confidence:.0%}, "
        f"should_target={enriched_targeting['should_target']}"
    )
    
    return state


# =============================================================================
# PARALLEL PRE-FETCH ORCHESTRATION
# =============================================================================

async def prefetch_all_intelligence_parallel(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run all intelligence pre-fetch nodes in parallel.
    
    This is the main entry point that orchestrates parallel fetching
    of all intelligence sources before atoms execute.
    
    State Input:
        All inputs needed by individual prefetch nodes
        
    State Output:
        All outputs from individual prefetch nodes plus enrichment
    """
    logger.info("Starting parallel intelligence pre-fetch")
    
    # Run all prefetch nodes in parallel
    results = await asyncio.gather(
        prefetch_context_intelligence(dict(state)),
        prefetch_persuadability_intelligence(dict(state)),
        prefetch_attribution_intelligence(dict(state)),
        prefetch_temporal_intelligence(dict(state)),
        prefetch_cross_platform_validation(dict(state)),
        return_exceptions=True,
    )
    
    # Merge results
    for result in results:
        if isinstance(result, dict):
            state.update(result)
        elif isinstance(result, Exception):
            logger.error(f"Prefetch error: {result}")
    
    # Apply combined enrichment
    state = await prefetch_combined_intelligence_enrichment(state)
    
    logger.info("Parallel intelligence pre-fetch complete")
    
    return state


# =============================================================================
# EXPORT FOR LANGGRAPH INTEGRATION
# =============================================================================

INTELLIGENCE_PREFETCH_NODES = {
    "prefetch_context_intelligence": prefetch_context_intelligence,
    "prefetch_persuadability_intelligence": prefetch_persuadability_intelligence,
    "prefetch_attribution_intelligence": prefetch_attribution_intelligence,
    "prefetch_temporal_intelligence": prefetch_temporal_intelligence,
    "prefetch_cross_platform_validation": prefetch_cross_platform_validation,
    "prefetch_combined_enrichment": prefetch_combined_intelligence_enrichment,
    "prefetch_all_intelligence_parallel": prefetch_all_intelligence_parallel,
}


def register_intelligence_prefetch_nodes(graph: "StateGraph") -> None:
    """
    Register all intelligence prefetch nodes with a LangGraph.
    
    Args:
        graph: LangGraph StateGraph to register nodes with
    """
    for name, func in INTELLIGENCE_PREFETCH_NODES.items():
        graph.add_node(name, func)
    
    logger.info(f"Registered {len(INTELLIGENCE_PREFETCH_NODES)} intelligence prefetch nodes")


if __name__ == "__main__":
    import asyncio
    
    logging.basicConfig(level=logging.INFO)
    
    # Test parallel prefetch
    test_state = {
        "placement_domain": "nytimes.com",
        "product_category": "Electronics",
        "granular_type": {
            "motivation": "quality_seeking",
            "decision_style": "deliberate",
            "emotional_intensity": "low",
        },
        "mechanism_priors": {
            "authority": 0.75,
            "social_proof": 0.70,
            "scarcity": 0.65,
            "reciprocity": 0.60,
            "commitment": 0.55,
            "liking": 0.50,
        },
    }
    
    result = asyncio.run(prefetch_all_intelligence_parallel(test_state))
    
    print("\n" + "="*60)
    print("PARALLEL INTELLIGENCE PRE-FETCH TEST")
    print("="*60)
    
    for key in ["context_intelligence", "persuadability_intelligence", 
                "attribution_intelligence", "temporal_intelligence",
                "cross_platform_validation", "enriched_targeting"]:
        if key in result:
            print(f"\n{key}:")
            import json
            print(json.dumps(result[key], indent=2, default=str)[:500])
