# =============================================================================
# ADAM Demo - Learned Priors Router
# Learned intelligence and priors endpoints
# =============================================================================

"""
Learned priors API endpoints for the ADAM demo platform.

Includes:
- Learned priors summary
- Ad strategy generation
- Persuasion insights
- Linguistic fingerprints
- Location-based priors
- Brand/category priors
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Learned Priors"])


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/learned-priors/summary")
async def get_learned_priors_summary() -> Dict[str, Any]:
    """
    Get comprehensive summary of all learned priors from review corpus.
    
    This endpoint exposes the full depth of psychological intelligence
    learned from 941M+ customer reviews across 10 sources:
    - Amazon, Google, Yelp, Sephora, Steam, Netflix
    - Rotten Tomatoes, MovieLens, Podcasts, BH Photo, Edmunds
    
    Returns corpus statistics, capabilities, and loading status.
    """
    try:
        from adam.core.learning.learned_priors_integration import get_learned_priors
        
        priors = get_learned_priors()
        summary = priors.get_summary()
        corpus = priors.get_corpus_statistics()
        
        return {
            "status": "operational" if summary["loaded"] else "partial",
            "corpus_statistics": {
                "total_reviews": corpus.get("total_reviews", 0),
                "total_reviewers": corpus.get("total_unique_reviewers", 0),
                "sources": list(corpus.get("sources", {}).keys()),
                "source_breakdown": corpus.get("sources", {}),
            },
            "learned_dimensions": {
                "categories": summary["counts"]["categories"],
                "brands": summary["counts"]["brands"],
                "states": summary["counts"]["states"],
                "regions": summary["counts"]["regions"],
            },
            "capabilities": summary["capabilities"],
            "loading_status": summary["loading_status"],
            "global_archetype_distribution": corpus.get("global_archetype_distribution", {}),
        }
    except Exception as e:
        logger.error(f"Error getting learned priors summary: {e}")
        return {"status": "error", "error": str(e)}


@router.get("/learned-priors/ad-strategy/{archetype}")
async def get_ad_copy_strategy(
    archetype: str,
    category: Optional[str] = Query(None, description="Product/service category"),
    brand: Optional[str] = Query(None, description="Brand name"),
) -> Dict[str, Any]:
    """
    Generate comprehensive ad copy strategy based on learned priors.
    
    This is the MAIN endpoint for ad optimization, providing:
    - Linguistic style recommendations
    - Best persuasion techniques (Cialdini principles)
    - Emotional triggers to emphasize
    - Decision-making style insights
    - Pain points to address
    - Trust/loyalty messaging
    - Timing recommendations
    
    All recommendations are backed by analysis of 941M+ real customer reviews.
    """
    try:
        from adam.core.learning.learned_priors_integration import get_learned_priors
        
        priors = get_learned_priors()
        strategy = priors.generate_ad_copy_strategy(
            archetype=archetype,
            category=category,
            brand=brand,
        )
        
        return {
            "status": "success",
            "archetype": archetype,
            "category": category,
            "brand": brand,
            "strategy": strategy,
            "data_source": "941M+ customer reviews across 10 platforms",
        }
    except Exception as e:
        logger.error(f"Error generating ad strategy: {e}")
        return {"status": "error", "error": str(e)}


@router.get("/learned-priors/persuasion/{archetype}")
async def get_persuasion_insights(archetype: str) -> Dict[str, Any]:
    """
    Get Cialdini persuasion technique sensitivity for an archetype.
    
    Returns effectiveness scores for:
    - Social Proof
    - Authority
    - Scarcity
    - Reciprocity
    - Commitment/Consistency
    - Liking
    
    Based on analysis of 941M+ reviews showing what language patterns
    correlate with positive outcomes for each archetype.
    """
    try:
        from adam.core.learning.learned_priors_integration import get_learned_priors
        
        priors = get_learned_priors()
        
        best_techniques = priors.get_best_persuasion_techniques(archetype, top_n=6)
        best_emotions = priors.get_best_emotional_triggers(archetype, top_n=6)
        decision_style, confidence = priors.get_dominant_decision_style(archetype)
        
        return {
            "archetype": archetype,
            "persuasion_techniques": [
                {"technique": t, "effectiveness": round(e, 3)} 
                for t, e in best_techniques
            ],
            "emotional_triggers": [
                {"emotion": e, "sensitivity": round(s, 3)} 
                for e, s in best_emotions
            ],
            "decision_style": {
                "dominant": decision_style,
                "confidence": round(confidence, 3),
            },
            "trust_focused": priors.is_trust_focused(archetype),
            "loyalty_focused": priors.is_loyalty_focused(archetype),
        }
    except Exception as e:
        logger.error(f"Error getting persuasion insights: {e}")
        return {"status": "error", "error": str(e)}


@router.get("/learned-priors/linguistic/{archetype}")
async def get_linguistic_fingerprint(archetype: str) -> Dict[str, Any]:
    """
    Get linguistic style fingerprint for an archetype.
    
    Used for matching ad copy style to archetype's natural language patterns.
    
    Returns:
    - Certainty level
    - Hedging patterns
    - Superlative usage
    - First-person ratio
    - Emotional intensity
    - Sentence complexity
    """
    try:
        from adam.core.learning.learned_priors_integration import get_learned_priors
        
        priors = get_learned_priors()
        
        fingerprint = priors.get_linguistic_fingerprint(archetype)
        style_recommendations = priors.get_optimal_ad_copy_style(archetype)
        
        return {
            "archetype": archetype,
            "linguistic_fingerprint": fingerprint,
            "ad_copy_recommendations": style_recommendations,
        }
    except Exception as e:
        logger.error(f"Error getting linguistic fingerprint: {e}")
        return {"status": "error", "error": str(e)}


@router.get("/learned-priors/location/{state}")
async def get_location_priors(
    state: str,
    category: Optional[str] = Query(None, description="Local service category"),
) -> Dict[str, Any]:
    """
    Get location-aware archetype priors for a US state.
    
    Based on analysis of Google Reviews with geographic data.
    """
    try:
        from adam.core.learning.learned_priors_integration import get_learned_priors
        
        priors = get_learned_priors()
        
        state_prior = priors.get_state_archetype_prior(state)
        best_archetype, confidence = priors.get_archetype_for_state(state)
        top_categories = priors.get_top_categories_for_state(state, top_n=10)
        
        return {
            "state": state,
            "archetype_distribution": state_prior,
            "dominant_archetype": {
                "archetype": best_archetype,
                "confidence": confidence,
            },
            "top_categories": top_categories,
            "category_filter": category,
        }
    except Exception as e:
        logger.error(f"Error getting location priors for {state}: {e}")
        return {"status": "error", "error": str(e)}


@router.get("/learned-priors/brand/{brand_name}")
async def get_brand_priors(brand_name: str) -> Dict[str, Any]:
    """
    Get learned priors for a specific brand.
    
    Returns brand-specific psychological intelligence from review analysis.
    """
    try:
        from adam.core.learning.learned_priors_integration import get_learned_priors
        
        priors = get_learned_priors()
        brand_data = priors.get_brand_priors(brand_name)
        
        if not brand_data:
            raise HTTPException(
                status_code=404,
                detail=f"No learned priors found for brand: {brand_name}"
            )
        
        return {
            "brand": brand_name,
            "archetypes": brand_data.get("archetypes", {}),
            "mechanisms": brand_data.get("mechanisms", {}),
            "personality": brand_data.get("personality", {}),
            "review_count": brand_data.get("review_count", 0),
            "confidence": brand_data.get("confidence", 0.0),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting brand priors for {brand_name}: {e}")
        return {"status": "error", "error": str(e)}


@router.get("/learned-priors/category/{category}")
async def get_category_priors(category: str) -> Dict[str, Any]:
    """
    Get learned priors for a product category.
    
    Returns category-specific psychological patterns.
    """
    try:
        from adam.core.learning.learned_priors_integration import get_learned_priors
        
        priors = get_learned_priors()
        category_data = priors.get_category_priors(category)
        
        if not category_data:
            return {
                "category": category,
                "found": False,
                "message": f"No learned priors for category: {category}",
            }
        
        return {
            "category": category,
            "found": True,
            "archetypes": category_data.get("archetypes", {}),
            "mechanisms": category_data.get("mechanisms", {}),
            "review_count": category_data.get("review_count", 0),
        }
    except Exception as e:
        logger.error(f"Error getting category priors for {category}: {e}")
        return {"status": "error", "error": str(e)}


@router.post("/learned-priors/predict-archetype")
async def predict_archetype(
    text: str = Query(..., min_length=10, description="Review or text to analyze"),
    context: Optional[str] = Query(None, description="Additional context"),
) -> Dict[str, Any]:
    """
    Predict archetype from text using learned patterns.
    
    Analyzes linguistic patterns to predict psychological archetype.
    """
    try:
        from adam.demo.framework_82_integration import get_framework_intelligence
        
        service = get_framework_intelligence()
        prediction = service.predict_archetype(text)
        
        return {
            "text_length": len(text),
            "predicted_archetype": prediction.get("archetype", "unknown"),
            "confidence": prediction.get("confidence", 0.0),
            "archetype_scores": prediction.get("scores", {}),
            "linguistic_markers": prediction.get("markers", []),
        }
    except Exception as e:
        logger.error(f"Error predicting archetype: {e}")
        return {"status": "error", "error": str(e)}


@router.get("/learned-priors/categories")
async def list_learned_categories() -> Dict[str, Any]:
    """
    List all categories with learned priors.
    """
    try:
        from adam.core.learning.learned_priors_integration import get_learned_priors
        
        priors = get_learned_priors()
        categories = priors.get_all_categories()
        
        return {
            "categories": categories,
            "count": len(categories),
        }
    except Exception as e:
        logger.error(f"Error listing categories: {e}")
        return {"categories": [], "count": 0, "error": str(e)}


@router.get("/learned-priors/comprehensive-strategy/{archetype}")
async def get_comprehensive_strategy(
    archetype: str,
    category: Optional[str] = Query(None),
    brand: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """
    Get comprehensive targeting strategy combining all intelligence sources.
    
    Merges:
    - Archetype priors
    - Category priors  
    - Brand priors
    - Location priors
    
    Into a unified, actionable strategy.
    """
    try:
        from adam.core.learning.learned_priors_integration import get_learned_priors
        
        priors = get_learned_priors()
        
        # Get individual components
        strategy = {
            "archetype": archetype,
            "inputs": {"category": category, "brand": brand, "state": state},
        }
        
        # Archetype base
        strategy["archetype_profile"] = {
            "persuasion": priors.get_best_persuasion_techniques(archetype, top_n=3),
            "emotions": priors.get_best_emotional_triggers(archetype, top_n=3),
            "decision_style": priors.get_dominant_decision_style(archetype),
        }
        
        # Category overlay
        if category:
            cat_priors = priors.get_category_priors(category)
            if cat_priors:
                strategy["category_overlay"] = cat_priors
        
        # Brand overlay
        if brand:
            brand_priors = priors.get_brand_priors(brand)
            if brand_priors:
                strategy["brand_overlay"] = brand_priors
        
        # Location overlay
        if state:
            state_prior = priors.get_state_archetype_prior(state)
            strategy["location_overlay"] = {
                "state": state,
                "archetypes": state_prior,
            }
        
        # Generate unified recommendations
        strategy["unified_recommendation"] = {
            "primary_mechanism": strategy["archetype_profile"]["persuasion"][0][0] if strategy["archetype_profile"]["persuasion"] else "social_proof",
            "tone": "confident" if priors.is_trust_focused(archetype) else "warm",
            "emotional_trigger": strategy["archetype_profile"]["emotions"][0][0] if strategy["archetype_profile"]["emotions"] else "satisfaction",
        }
        
        return strategy
        
    except Exception as e:
        logger.error(f"Error getting comprehensive strategy: {e}")
        return {"status": "error", "error": str(e)}
