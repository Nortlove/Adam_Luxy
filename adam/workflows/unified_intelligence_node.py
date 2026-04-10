# =============================================================================
# Unified Psychological Intelligence Workflow Node
# Location: adam/workflows/unified_intelligence_node.py
# =============================================================================

"""
LangGraph Workflow Node for Unified Psychological Intelligence

This module provides a LangGraph-compatible workflow node that integrates
the Unified Psychological Intelligence service into the holistic decision
workflow.

The node:
1. Pulls review/brand data from the workflow state
2. Runs all 3 psychological analysis modules
3. Enriches the workflow state with psychological insights
4. Emits learning signals for continuous improvement

Usage in workflow:
    from adam.workflows.unified_intelligence_node import (
        analyze_psychological_intelligence,
        create_unified_intelligence_node,
    )
    
    # Add to workflow
    workflow.add_node(
        "unified_intelligence",
        create_unified_intelligence_node(unified_intelligence_service)
    )
"""

import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, TypedDict

logger = logging.getLogger(__name__)


# =============================================================================
# WORKFLOW STATE EXTENSIONS
# =============================================================================

class UnifiedIntelligenceState(TypedDict, total=False):
    """
    Extensions to WorkflowState for unified psychological intelligence.
    
    These fields are added to the workflow state by the unified intelligence node.
    """
    
    # Profile identification
    psychological_profile_id: str
    
    # Archetype determination
    primary_archetype: str
    archetype_confidence: float
    
    # Flow state from analysis
    flow_arousal: float
    flow_valence: float
    flow_energy: float
    flow_cognitive_load: float
    ad_receptivity: float
    optimal_ad_formats: List[str]
    recommended_tone: str
    
    # Psychological needs
    promotion_focus: float
    prevention_focus: float
    alignment_score: float
    unmet_needs: List[str]
    
    # Mechanism predictions (informed by all 3 modules)
    mechanism_predictions: Dict[str, float]
    
    # Unified constructs (32 psycholinguistic constructs)
    unified_constructs: Dict[str, float]
    
    # Ad recommendations
    unified_ad_recommendations: List[Dict[str, Any]]
    
    # Metadata
    reviews_analyzed: int
    modules_used: List[str]
    analysis_time_ms: float


# =============================================================================
# WORKFLOW NODE FUNCTION
# =============================================================================

async def analyze_psychological_intelligence(
    state: Dict[str, Any],
    unified_intelligence,
    brand_name: Optional[str] = None,
    product_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    LangGraph node for unified psychological intelligence analysis.
    
    This node enriches the workflow state with deep psychological insights
    from all 3 analysis modules.
    
    Args:
        state: Current workflow state
        unified_intelligence: UnifiedPsychologicalIntelligence service instance
        brand_name: Optional override for brand name
        product_name: Optional override for product name
    
    Returns:
        Updated workflow state with psychological intelligence
    """
    start = datetime.now(timezone.utc)
    
    try:
        # Extract reviews from state
        reviews = _extract_reviews_from_state(state)
        
        if not reviews:
            logger.warning("No reviews found in workflow state for psychological analysis")
            state["psychological_profile_id"] = None
            state["node_timings"] = state.get("node_timings", {})
            state["node_timings"]["unified_intelligence"] = 0.0
            return state
        
        # Extract brand content from state
        brand_content = _extract_brand_content_from_state(state)
        
        # Determine brand/product names
        resolved_brand = brand_name or state.get("brand_name") or state.get("brand_id") or "Brand"
        resolved_product = product_name or state.get("product_name") or state.get("category_id") or "Product"
        
        # Run unified psychological analysis
        profile = await unified_intelligence.analyze_reviews(
            reviews=reviews,
            brand_content=brand_content,
            brand_name=resolved_brand,
            product_name=resolved_product,
        )
        
        # Emit learning signal
        await unified_intelligence.emit_learning_signal(profile)
        
        # Enrich workflow state with psychological intelligence
        state["psychological_profile_id"] = profile.profile_id
        state["primary_archetype"] = profile.primary_archetype
        state["archetype_confidence"] = profile.archetype_confidence
        
        # Flow state
        state["flow_arousal"] = profile.flow_state.arousal
        state["flow_valence"] = profile.flow_state.valence
        state["flow_energy"] = profile.flow_state.energy
        state["flow_cognitive_load"] = profile.flow_state.cognitive_load
        state["ad_receptivity"] = profile.flow_state.ad_receptivity_score
        state["optimal_ad_formats"] = profile.flow_state.optimal_formats
        state["recommended_tone"] = profile.flow_state.recommended_tone
        
        # Psychological needs
        state["promotion_focus"] = profile.psychological_needs.promotion_focus
        state["prevention_focus"] = profile.psychological_needs.prevention_focus
        state["alignment_score"] = profile.psychological_needs.overall_alignment_score
        state["unmet_needs"] = profile.psychological_needs.unmet_needs
        
        # Mechanism predictions
        state["mechanism_predictions"] = profile.mechanism_predictions
        
        # Unified constructs (top 10 for efficiency)
        top_constructs = dict(
            sorted(
                profile.unified_constructs.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10]
        )
        state["unified_constructs"] = top_constructs
        
        # Ad recommendations
        state["unified_ad_recommendations"] = [
            rec.to_dict() if hasattr(rec, "to_dict") else {
                "construct_name": rec.construct_name,
                "recommendation": rec.recommendation,
                "confidence": rec.confidence,
            }
            for rec in profile.unified_ad_recommendations[:5]
        ]
        
        # Metadata
        state["reviews_analyzed"] = profile.reviews_analyzed
        state["modules_used"] = profile.modules_used
        state["analysis_time_ms"] = profile.analysis_time_ms
        
        logger.info(
            f"Unified Intelligence: Analyzed {profile.reviews_analyzed} reviews, "
            f"archetype={profile.primary_archetype} ({profile.archetype_confidence:.2f})"
        )
        
    except Exception as e:
        logger.error(f"Error in unified intelligence node: {e}")
        state["errors"] = state.get("errors", [])
        state["errors"].append(f"unified_intelligence: {str(e)}")
    
    # Record timing
    state["node_timings"] = state.get("node_timings", {})
    state["node_timings"]["unified_intelligence"] = (
        datetime.now(timezone.utc) - start
    ).total_seconds() * 1000
    
    return state


def create_unified_intelligence_node(
    unified_intelligence,
    brand_name: Optional[str] = None,
    product_name: Optional[str] = None,
) -> Callable:
    """
    Create a LangGraph-compatible node for unified psychological intelligence.
    
    Args:
        unified_intelligence: UnifiedPsychologicalIntelligence service instance
        brand_name: Optional default brand name
        product_name: Optional default product name
    
    Returns:
        Async function suitable for LangGraph workflow
    """
    async def node(state: Dict) -> Dict:
        return await analyze_psychological_intelligence(
            state=state,
            unified_intelligence=unified_intelligence,
            brand_name=brand_name,
            product_name=product_name,
        )
    return node


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _extract_reviews_from_state(state: Dict[str, Any]) -> List[str]:
    """
    Extract review texts from workflow state.
    
    Looks in multiple locations for review data.
    """
    reviews = []
    
    # Direct reviews field
    if state.get("reviews"):
        reviews.extend(state["reviews"])
    
    # Customer intelligence profile
    if state.get("customer_intelligence"):
        ci = state["customer_intelligence"]
        if isinstance(ci, dict) and ci.get("review_texts"):
            reviews.extend(ci["review_texts"])
    
    # Review analysis results
    if state.get("review_analysis"):
        ra = state["review_analysis"]
        if isinstance(ra, dict) and ra.get("reviews"):
            reviews.extend([r.get("text", "") for r in ra["reviews"]])
    
    # Blackboard state (Zone 1 or Zone 6)
    if state.get("blackboard_state"):
        bb = state["blackboard_state"]
        if isinstance(bb, dict):
            if bb.get("zone1_reviews"):
                reviews.extend(bb["zone1_reviews"])
            if bb.get("zone6_intelligence", {}).get("reviews"):
                reviews.extend(bb["zone6_intelligence"]["reviews"])
    
    # Graph context
    if state.get("graph_context"):
        gc = state["graph_context"]
        if isinstance(gc, dict) and gc.get("customer_reviews"):
            reviews.extend(gc["customer_reviews"])
    
    # Deduplicate while preserving order
    seen = set()
    unique_reviews = []
    for review in reviews:
        if review and review not in seen:
            seen.add(review)
            unique_reviews.append(review)
    
    return unique_reviews


def _extract_brand_content_from_state(state: Dict[str, Any]) -> Optional[Dict[str, List[str]]]:
    """
    Extract brand content from workflow state.
    
    Looks in multiple locations for brand/product content.
    """
    brand_content = {}
    
    # Direct brand content field
    if state.get("brand_content"):
        bc = state["brand_content"]
        if isinstance(bc, dict):
            brand_content = bc
    
    # Brand intelligence
    if state.get("brand_intelligence"):
        bi = state["brand_intelligence"]
        if isinstance(bi, dict):
            if bi.get("descriptions"):
                brand_content["descriptions"] = bi["descriptions"]
            if bi.get("website_copy"):
                brand_content["website"] = bi["website_copy"]
            if bi.get("ad_copy"):
                brand_content["ads"] = bi["ad_copy"]
    
    # Graph context brand data
    if state.get("graph_context"):
        gc = state["graph_context"]
        if isinstance(gc, dict) and gc.get("brand_profile"):
            bp = gc["brand_profile"]
            if bp.get("taglines"):
                brand_content["taglines"] = bp["taglines"]
            if bp.get("value_propositions"):
                brand_content["values"] = bp["value_propositions"]
    
    # Ad candidates for brand voice
    if state.get("ad_candidates"):
        ad_texts = [
            ad.get("copy", "") or ad.get("headline", "")
            for ad in state["ad_candidates"]
            if ad.get("copy") or ad.get("headline")
        ]
        if ad_texts:
            brand_content["ads"] = brand_content.get("ads", []) + ad_texts
    
    return brand_content if brand_content else None


# =============================================================================
# INTEGRATION WITH EXISTING WORKFLOW
# =============================================================================

def add_unified_intelligence_to_workflow(
    workflow,
    unified_intelligence,
    after_node: str = "pull_graph_context",
    before_node: str = "meta_learner_routing",
):
    """
    Add unified intelligence node to an existing LangGraph workflow.
    
    Args:
        workflow: StateGraph instance
        unified_intelligence: UnifiedPsychologicalIntelligence service
        after_node: Node to execute after
        before_node: Node to execute before
    
    Example:
        from adam.workflows.holistic_decision_workflow import create_workflow
        from adam.intelligence.unified_psychological_intelligence import get_unified_intelligence
        
        workflow = create_workflow(...)
        add_unified_intelligence_to_workflow(
            workflow,
            get_unified_intelligence()
        )
    """
    # Create the node
    node = create_unified_intelligence_node(unified_intelligence)
    
    # Add to workflow
    workflow.add_node("unified_intelligence", node)
    
    # Update edges
    # Note: This requires workflow modification support
    # In practice, you'd rebuild the workflow with the new node
    logger.info(
        f"Added unified_intelligence node to workflow "
        f"(after={after_node}, before={before_node})"
    )
