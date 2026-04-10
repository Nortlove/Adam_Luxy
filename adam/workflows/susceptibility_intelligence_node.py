#!/usr/bin/env python3
"""
SUSCEPTIBILITY INTELLIGENCE WORKFLOW NODE
=========================================

LangGraph-compatible workflow node for persuasion susceptibility analysis.

This node integrates the research-backed susceptibility constructs into
the holistic decision workflow, providing mechanism effectiveness predictions
based on individual difference variables.

INTEGRATION POINTS:
1. Reads reviews/brand descriptions from workflow state
2. Computes 13 susceptibility construct scores
3. Queries Neo4j for mechanism influence relationships
4. Updates mechanism_predictions in workflow state
5. Emits learning signals for Thompson Sampling updates

RESEARCH FOUNDATION:
All 13 constructs are grounded in peer-reviewed psychological research
with validated measurement scales and meta-analytic effect sizes.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, TypedDict

from adam.intelligence.knowledge_graph.persuasion_susceptibility_graph import (
    SUSCEPTIBILITY_CONSTRUCTS,
    SusceptibilityConstructDefinition,
    get_construct_definitions,
    get_mechanism_susceptibility_influences,
)
from adam.intelligence.persuasion_susceptibility import (
    PersuasionSusceptibilityAnalyzer,
    analyze_customer_susceptibility,
)
from adam.intelligence.brand_trait_extraction import (
    BrandTraitAnalyzer,
    analyze_brand_traits,
)
from adam.intelligence.construct_matching import (
    ConstructMatchingEngine,
    match_constructs,
)

logger = logging.getLogger(__name__)


# =============================================================================
# WORKFLOW STATE EXTENSIONS
# =============================================================================

class SusceptibilityIntelligenceState(TypedDict, total=False):
    """
    Extensions to WorkflowState for susceptibility intelligence.
    
    These fields are added by the susceptibility intelligence node.
    """
    
    # Susceptibility Profile (13 constructs)
    susceptibility_profile: Dict[str, Dict[str, Any]]
    """
    Per-construct scores:
    {
        "suscept_social_proof": {
            "score": 0.72,
            "confidence": 0.85,
            "level": "high",
            "signals_detected": 8,
            "research_basis": "Cialdini (2009)",
            "effect_size": 0.38
        },
        ...
    }
    """
    
    # Brand Trait Profile (10 traits)
    brand_trait_profile: Dict[str, Dict[str, Any]]
    """
    Brand positioning extracted from descriptions.
    """
    
    # Construct Matching Results
    construct_match_results: Dict[str, Any]
    """
    Full results from customer × brand matching.
    """
    
    # Mechanism Effectiveness Modifiers
    mechanism_susceptibility_modifiers: Dict[str, float]
    """
    Per-mechanism effectiveness adjustments based on susceptibility:
    {
        "mimetic_desire": +0.15,  # High social proof susceptibility
        "wanting_liking": +0.10,  # High delay discounting
        ...
    }
    """
    
    # Recommended Mechanisms (from susceptibility analysis)
    susceptibility_recommended_mechanisms: List[str]
    """Top mechanisms based on susceptibility profile."""
    
    # Mechanisms to Avoid (based on reactance, etc.)
    susceptibility_avoid_mechanisms: List[str]
    """Mechanisms that may backfire based on profile."""
    
    # Message Style Recommendations
    susceptibility_message_style: Dict[str, str]
    """
    {
        "complexity": "simple" | "moderate" | "detailed",
        "tone": "professional" | "friendly" | "urgent",
        "evidence_level": "high" | "moderate" | "low",
        "urgency_level": "high" | "moderate" | "avoid"
    }
    """
    
    # Warnings and Cautions
    susceptibility_warnings: List[Dict[str, str]]
    """
    [
        {
            "type": "high_reactance",
            "severity": "high",
            "message": "Avoid pressure tactics...",
            "affected_mechanisms": ["scarcity", "urgency"]
        }
    ]
    """
    
    # Learning Signal Data
    susceptibility_learning_context: Dict[str, Any]
    """Context for learning system integration."""
    
    # Metadata
    susceptibility_reviews_analyzed: int
    susceptibility_brands_analyzed: int
    susceptibility_analysis_time_ms: float


# =============================================================================
# MAIN ANALYSIS FUNCTION
# =============================================================================

async def analyze_susceptibility_intelligence(
    state: Dict[str, Any],
    neo4j_driver=None,
) -> Dict[str, Any]:
    """
    LangGraph node for susceptibility intelligence analysis.
    
    This node enriches the workflow state with:
    1. Susceptibility profile (13 research-backed constructs)
    2. Brand trait profile (10 positioning traits)
    3. Construct matching (customer × brand alignment)
    4. Mechanism effectiveness modifiers
    5. Message style recommendations
    
    Args:
        state: Current workflow state (must contain reviews/descriptions)
        neo4j_driver: Optional Neo4j driver for graph queries
        
    Returns:
        Updated state dict with susceptibility intelligence
    """
    start_time = datetime.now(timezone.utc)
    
    # Extract input data from workflow state
    reviews = _extract_reviews(state)
    brand_descriptions = _extract_brand_descriptions(state)
    
    logger.info(
        f"Susceptibility intelligence: analyzing {len(reviews)} reviews, "
        f"{len(brand_descriptions)} brand descriptions"
    )
    
    updates = {}
    
    try:
        # =====================================================================
        # PHASE 1: Customer Susceptibility Analysis
        # =====================================================================
        if reviews:
            customer_result = analyze_customer_susceptibility(reviews)
            
            # Enrich with research metadata
            susceptibility_profile = {}
            for construct_id, score_data in customer_result.get("susceptibility_profile", {}).items():
                # Add research backing from construct definitions
                if construct_id in SUSCEPTIBILITY_CONSTRUCTS:
                    construct_def = SUSCEPTIBILITY_CONSTRUCTS[construct_id]
                    score_data["research_basis"] = construct_def.research_basis
                    score_data["effect_size"] = construct_def.meta_analysis_effect_size
                    score_data["ad_implications"] = (
                        construct_def.ad_implications_high if score_data.get("score", 0.5) > 0.6
                        else construct_def.ad_implications_low if score_data.get("score", 0.5) < 0.4
                        else "Moderate - balanced approach recommended"
                    )
                susceptibility_profile[construct_id] = score_data
            
            updates["susceptibility_profile"] = susceptibility_profile
            updates["susceptibility_reviews_analyzed"] = len(reviews)
            
            # Extract warnings from customer analysis
            warnings = customer_result.get("mechanism_recommendations", {}).get("_warnings", [])
            updates["susceptibility_warnings"] = warnings
        
        # =====================================================================
        # PHASE 2: Brand Trait Analysis
        # =====================================================================
        if brand_descriptions:
            brand_result = analyze_brand_traits(brand_descriptions)
            updates["brand_trait_profile"] = brand_result.get("brand_traits", {})
            updates["susceptibility_brands_analyzed"] = len(brand_descriptions)
        
        # =====================================================================
        # PHASE 3: Construct Matching (Customer × Brand)
        # =====================================================================
        if reviews and brand_descriptions:
            match_result = match_constructs(reviews, brand_descriptions)
            
            updates["construct_match_results"] = match_result
            updates["susceptibility_recommended_mechanisms"] = match_result.get(
                "recommended_mechanisms", []
            )
            updates["susceptibility_avoid_mechanisms"] = match_result.get(
                "avoid_mechanisms", []
            )
            updates["susceptibility_message_style"] = match_result.get(
                "message_style", {}
            )
            
            # Merge warnings
            match_warnings = match_result.get("warnings", [])
            existing_warnings = updates.get("susceptibility_warnings", [])
            updates["susceptibility_warnings"] = existing_warnings + match_warnings
        
        # =====================================================================
        # PHASE 4: Compute Mechanism Effectiveness Modifiers
        # =====================================================================
        if neo4j_driver and "susceptibility_profile" in updates:
            # Query Neo4j for mechanism influences
            construct_scores = {
                k: v.get("score", 0.5)
                for k, v in updates["susceptibility_profile"].items()
            }
            
            try:
                mechanism_modifiers = await get_mechanism_susceptibility_influences(
                    neo4j_driver, construct_scores
                )
                updates["mechanism_susceptibility_modifiers"] = mechanism_modifiers
            except Exception as e:
                logger.warning(f"Neo4j mechanism query failed: {e}")
                # Fallback: compute from construct definitions
                updates["mechanism_susceptibility_modifiers"] = _compute_mechanism_modifiers_local(
                    construct_scores
                )
        elif "susceptibility_profile" in updates:
            # Compute locally without Neo4j
            construct_scores = {
                k: v.get("score", 0.5)
                for k, v in updates["susceptibility_profile"].items()
            }
            updates["mechanism_susceptibility_modifiers"] = _compute_mechanism_modifiers_local(
                construct_scores
            )
        
        # =====================================================================
        # PHASE 5: Update Existing Mechanism Predictions
        # =====================================================================
        # Merge susceptibility modifiers with existing mechanism_predictions
        if "mechanism_predictions" in state and "mechanism_susceptibility_modifiers" in updates:
            existing_predictions = state.get("mechanism_predictions", {})
            modifiers = updates["mechanism_susceptibility_modifiers"]
            
            # Create merged predictions
            merged_predictions = {}
            for mech, base_score in existing_predictions.items():
                modifier = modifiers.get(mech, 0.0)
                # Apply modifier: score + modifier, bounded [0, 1]
                merged_predictions[mech] = max(0.0, min(1.0, base_score + modifier))
            
            # Add any new mechanisms from modifiers
            for mech, modifier in modifiers.items():
                if mech not in merged_predictions:
                    # New mechanism from susceptibility, start at 0.5 + modifier
                    merged_predictions[mech] = max(0.0, min(1.0, 0.5 + modifier))
            
            updates["mechanism_predictions"] = merged_predictions
        
        # =====================================================================
        # PHASE 6: Prepare Learning Context
        # =====================================================================
        updates["susceptibility_learning_context"] = {
            "profile_hash": _hash_profile(updates.get("susceptibility_profile", {})),
            "recommended_mechanisms": updates.get("susceptibility_recommended_mechanisms", []),
            "avoid_mechanisms": updates.get("susceptibility_avoid_mechanisms", []),
            "construct_scores": {
                k: v.get("score", 0.5)
                for k, v in updates.get("susceptibility_profile", {}).items()
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Susceptibility intelligence analysis failed: {e}")
        updates["susceptibility_error"] = str(e)
    
    # Record timing
    elapsed_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
    updates["susceptibility_analysis_time_ms"] = elapsed_ms
    
    logger.info(
        f"Susceptibility intelligence complete in {elapsed_ms:.1f}ms: "
        f"{len(updates.get('susceptibility_profile', {}))} constructs, "
        f"{len(updates.get('susceptibility_recommended_mechanisms', []))} recommended mechanisms"
    )
    
    return updates


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _extract_reviews(state: Dict[str, Any]) -> List[str]:
    """Extract review texts from workflow state."""
    reviews = []
    
    # Try multiple state locations where reviews might be stored
    
    # From request context
    request_ctx = state.get("request_context", {})
    if isinstance(request_ctx, dict):
        user_intel = request_ctx.get("user_intelligence", {})
        if isinstance(user_intel, dict):
            reviews.extend(user_intel.get("reviews", []))
    
    # From unified intelligence
    unified_reviews = state.get("unified_reviews", [])
    if unified_reviews:
        reviews.extend(unified_reviews)
    
    # From product context
    product_ctx = state.get("product_context", {})
    if isinstance(product_ctx, dict):
        reviews.extend(product_ctx.get("reviews", []))
    
    # From ad context
    ad_ctx = state.get("ad_context", {})
    if isinstance(ad_ctx, dict):
        reviews.extend(ad_ctx.get("product_reviews", []))
    
    # From direct state
    direct_reviews = state.get("reviews", [])
    if direct_reviews:
        reviews.extend(direct_reviews)
    
    return reviews[:100]  # Limit for performance


def _extract_brand_descriptions(state: Dict[str, Any]) -> List[str]:
    """Extract brand/product descriptions from workflow state."""
    descriptions = []
    
    # From ad context
    ad_ctx = state.get("ad_context", {})
    if isinstance(ad_ctx, dict):
        if ad_ctx.get("brand_description"):
            descriptions.append(ad_ctx["brand_description"])
        if ad_ctx.get("product_description"):
            descriptions.append(ad_ctx["product_description"])
        if ad_ctx.get("creative_text"):
            descriptions.append(ad_ctx["creative_text"])
    
    # From brand context
    brand_ctx = state.get("brand_context", {})
    if isinstance(brand_ctx, dict):
        if brand_ctx.get("description"):
            descriptions.append(brand_ctx["description"])
        if brand_ctx.get("about"):
            descriptions.append(brand_ctx["about"])
    
    # From direct state
    if state.get("brand_description"):
        descriptions.append(state["brand_description"])
    if state.get("product_description"):
        descriptions.append(state["product_description"])
    
    return descriptions


def _compute_mechanism_modifiers_local(construct_scores: Dict[str, float]) -> Dict[str, float]:
    """
    Compute mechanism modifiers locally without Neo4j.
    
    Uses the construct definitions' mechanism_influences.
    """
    mechanism_modifiers = {}
    
    for construct_id, score in construct_scores.items():
        # Map from susceptibility ID to graph ID
        graph_id = construct_id
        if not graph_id.startswith("suscept_"):
            graph_id = f"suscept_{construct_id}"
        
        # Try to find in our construct definitions
        # Handle various ID formats
        matching_def = None
        for def_id, construct_def in SUSCEPTIBILITY_CONSTRUCTS.items():
            if def_id == construct_id or def_id == graph_id:
                matching_def = construct_def
                break
            # Also check name-based matching
            normalized_id = construct_id.replace("_susceptibility", "").replace("susceptibility_", "")
            if normalized_id in def_id or def_id.endswith(normalized_id):
                matching_def = construct_def
                break
        
        if matching_def:
            for mechanism, strength in matching_def.mechanism_influences.items():
                # score is 0-1, center at 0.5
                # modifier = (score - 0.5) * strength
                modifier = (score - 0.5) * strength
                
                if mechanism not in mechanism_modifiers:
                    mechanism_modifiers[mechanism] = 0.0
                mechanism_modifiers[mechanism] += modifier
    
    return mechanism_modifiers


def _hash_profile(profile: Dict[str, Dict]) -> str:
    """Create a hash of the susceptibility profile for learning tracking."""
    import hashlib
    
    # Create stable string representation
    items = sorted([
        f"{k}:{v.get('score', 0.5):.2f}"
        for k, v in profile.items()
    ])
    profile_str = "|".join(items)
    
    return hashlib.md5(profile_str.encode()).hexdigest()[:8]


# =============================================================================
# LANGGRAPH NODE FACTORY
# =============================================================================

def create_susceptibility_intelligence_node(
    neo4j_driver=None,
) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    """
    Create a LangGraph-compatible node function for susceptibility intelligence.
    
    Args:
        neo4j_driver: Optional Neo4j driver for graph queries
        
    Returns:
        Async function that can be used as a LangGraph node
    """
    async def node_fn(state: Dict[str, Any]) -> Dict[str, Any]:
        updates = await analyze_susceptibility_intelligence(state, neo4j_driver)
        return {**state, **updates}
    
    return node_fn


# =============================================================================
# LEARNING SIGNAL EMISSION
# =============================================================================

async def emit_susceptibility_learning_signal(
    state: Dict[str, Any],
    outcome: Dict[str, Any],
    kafka_producer=None,
) -> None:
    """
    Emit learning signal for susceptibility-informed mechanism selection.
    
    This enables Thompson Sampling to update based on actual outcomes.
    
    Args:
        state: Workflow state containing susceptibility analysis
        outcome: Outcome data (clicks, conversions, etc.)
        kafka_producer: Optional Kafka producer for event emission
    """
    learning_ctx = state.get("susceptibility_learning_context", {})
    
    if not learning_ctx:
        logger.debug("No susceptibility learning context available")
        return
    
    signal = {
        "type": "susceptibility_mechanism_outcome",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "profile_hash": learning_ctx.get("profile_hash"),
        "recommended_mechanisms": learning_ctx.get("recommended_mechanisms", []),
        "avoid_mechanisms": learning_ctx.get("avoid_mechanisms", []),
        "construct_scores": learning_ctx.get("construct_scores", {}),
        "outcome": {
            "clicked": outcome.get("clicked", False),
            "converted": outcome.get("converted", False),
            "engagement_score": outcome.get("engagement_score", 0.0),
            "mechanism_used": outcome.get("mechanism_used"),
        },
    }
    
    # Determine success/failure for each recommended mechanism
    mechanism_outcomes = []
    mechanism_used = outcome.get("mechanism_used")
    if mechanism_used:
        was_recommended = mechanism_used in learning_ctx.get("recommended_mechanisms", [])
        was_avoided = mechanism_used in learning_ctx.get("avoid_mechanisms", [])
        
        mechanism_outcomes.append({
            "mechanism": mechanism_used,
            "was_recommended": was_recommended,
            "was_avoided": was_avoided,
            "success": outcome.get("converted", False) or outcome.get("clicked", False),
        })
    
    signal["mechanism_outcomes"] = mechanism_outcomes
    
    if kafka_producer:
        try:
            await kafka_producer.send(
                "adam.learning.susceptibility",
                signal,
            )
            logger.debug(f"Emitted susceptibility learning signal: {signal['profile_hash']}")
        except Exception as e:
            logger.warning(f"Failed to emit learning signal: {e}")
    else:
        # Log for offline processing
        logger.info(f"Susceptibility learning signal: {signal}")
