# =============================================================================
# ADAM Demo - Reviews Router
# Review intelligence and analysis endpoints
# =============================================================================

"""
Review intelligence API endpoints for the ADAM demo platform.

Includes:
- Product review analysis
- Review-based customer intelligence
- Smart review analysis with psychological frameworks
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Review Intelligence"])


# =============================================================================
# MODELS
# =============================================================================

class ReviewIntelligenceRequest(BaseModel):
    """Request for review intelligence analysis."""
    product_name: str = Field(..., description="Name of the product to analyze")
    product_url: Optional[str] = Field(None, description="URL to scrape reviews from")
    brand: Optional[str] = Field(None, description="Brand name for additional context")
    max_reviews: int = Field(default=100, ge=10, le=500, description="Max reviews to analyze")


class ReviewIntelligenceResponse(BaseModel):
    """Response with review-derived intelligence."""
    request_id: str
    timestamp: str
    product_name: str
    brand: Optional[str]
    reviews_analyzed: int
    sources_used: List[str]
    buyer_archetypes: Dict[str, float]
    dominant_archetype: str
    archetype_confidence: float
    personality_traits: Dict[str, float]
    regulatory_focus: Dict[str, float]
    purchase_motivations: List[str]
    primary_motivation: Optional[str]
    language_intelligence: Dict[str, Any]
    mechanism_predictions: Dict[str, float]
    ideal_customer: Dict[str, Any]
    flow_state: Dict[str, Any]
    psychological_needs: Dict[str, Any]
    unified_ad_recommendations: List[Dict[str, Any]]
    unified_archetype: str
    unified_archetype_confidence: float
    avg_rating: float
    overall_confidence: float
    processing_time_ms: float


class SmartReviewRequest(BaseModel):
    """Request for smart review analysis."""
    reviews: List[str] = Field(..., description="List of review texts to analyze")
    brand: Optional[str] = Field(None, description="Brand name for context")
    category: Optional[str] = Field(None, description="Product category")


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/analyze-reviews", response_model=ReviewIntelligenceResponse)
async def analyze_product_reviews(request: ReviewIntelligenceRequest) -> ReviewIntelligenceResponse:
    """
    Analyze product reviews to extract customer intelligence.
    
    This endpoint:
    1. Scrapes reviews from the product URL and other sources
    2. Analyzes each review psychologically
    3. Builds a complete customer intelligence profile
    4. Returns insights for targeting and copy generation
    
    The results integrate with ADAM's entire decision engine:
    - ColdStart uses buyer_archetypes as priors
    - MetaLearner uses personality for Thompson Sampling
    - CopyGeneration uses language_intelligence for ad copy
    """
    start_time = time.time()
    request_id = str(uuid4())[:8]
    
    try:
        from adam.intelligence.review_orchestrator import get_review_orchestrator
        
        orchestrator = get_review_orchestrator()
        profile = await orchestrator.analyze_product(
            product_name=request.product_name,
            product_url=request.product_url,
            brand=request.brand,
            max_reviews=request.max_reviews,
        )
        
        return ReviewIntelligenceResponse(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            product_name=profile.product_name,
            brand=profile.brand,
            reviews_analyzed=profile.reviews_analyzed,
            sources_used=[s.value for s in profile.sources_used],
            buyer_archetypes=profile.buyer_archetypes,
            dominant_archetype=profile.dominant_archetype,
            archetype_confidence=profile.archetype_confidence,
            personality_traits={
                "openness": profile.avg_openness,
                "conscientiousness": profile.avg_conscientiousness,
                "extraversion": profile.avg_extraversion,
                "agreeableness": profile.avg_agreeableness,
                "neuroticism": profile.avg_neuroticism,
            },
            regulatory_focus=profile.regulatory_focus,
            purchase_motivations=[m.value for m in profile.purchase_motivations],
            primary_motivation=profile.primary_motivation.value if profile.primary_motivation else None,
            language_intelligence=profile.get_copy_language(),
            mechanism_predictions=profile.mechanism_predictions,
            ideal_customer={
                "archetype": profile.ideal_customer.archetype,
                "archetype_confidence": profile.ideal_customer.archetype_confidence,
                "primary_motivations": [m.value for m in profile.ideal_customer.primary_motivations],
                "characteristic_phrases": profile.ideal_customer.characteristic_phrases[:5],
            },
            flow_state={
                "arousal": profile.flow_state_arousal,
                "valence": profile.flow_state_valence,
                "optimal_formats": profile.flow_state_optimal_formats[:5],
                "ad_receptivity": profile.flow_state_ad_receptivity,
            },
            psychological_needs={
                "primary_needs": profile.primary_psychological_needs[:5],
                "unmet_needs": profile.unmet_psychological_needs[:5],
                "alignment_score": profile.brand_alignment_score,
                "alignment_gaps": profile.alignment_gaps[:3],
            },
            unified_ad_recommendations=profile.unified_ad_recommendations[:10],
            unified_archetype=profile.unified_archetype,
            unified_archetype_confidence=profile.unified_archetype_confidence,
            avg_rating=profile.avg_rating,
            overall_confidence=profile.overall_confidence,
            processing_time_ms=(time.time() - start_time) * 1000,
        )
        
    except ImportError as e:
        logger.error(f"Review intelligence not available: {e}")
        raise HTTPException(status_code=503, detail=f"Review intelligence not available: {e}")
    except Exception as e:
        logger.error(f"Error analyzing reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/smart-reviews/analyze")
async def analyze_smart_reviews(request: SmartReviewRequest) -> Dict[str, Any]:
    """
    Analyze a batch of reviews with deep psychological extraction.
    
    Uses the 82-framework system to extract:
    - Psychological constructs
    - Persuasion susceptibilities
    - Archetype indicators
    - Language patterns
    """
    start_time = time.time()
    
    try:
        from adam.demo.framework_82_integration import get_framework_intelligence
        
        service = get_framework_intelligence()
        
        results = []
        for review in request.reviews[:50]:  # Limit to 50 reviews
            analysis = service.analyze_text(
                text=review,
                brand=request.brand,
                category=request.category,
            )
            results.append(analysis)
        
        # Aggregate results
        aggregated = _aggregate_review_analyses(results)
        
        return {
            "reviews_analyzed": len(results),
            "brand": request.brand,
            "category": request.category,
            "aggregated": aggregated,
            "individual_results": results[:10],  # Return first 10
            "processing_time_ms": (time.time() - start_time) * 1000,
        }
        
    except ImportError as e:
        logger.warning(f"Framework intelligence not available: {e}")
        return {
            "reviews_analyzed": len(request.reviews),
            "error": "Analysis service not available",
            "processing_time_ms": (time.time() - start_time) * 1000,
        }
    except Exception as e:
        logger.error(f"Error in smart review analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reviews/insights/{product_id}")
async def get_product_review_insights(
    product_id: str,
    limit: int = Query(default=100, ge=10, le=500),
) -> Dict[str, Any]:
    """
    Get pre-computed review insights for a product.
    
    Returns cached psychological intelligence from previous analyses.
    """
    try:
        from adam.intelligence.review_learnings_service import get_review_learnings_service
        
        service = get_review_learnings_service()
        insights = service.get_product_insights(product_id)
        
        if not insights:
            raise HTTPException(
                status_code=404,
                detail=f"No insights found for product: {product_id}"
            )
        
        return insights
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching product insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_mock_review_response(
    request: ReviewIntelligenceRequest,
    request_id: str,
    start_time: float,
) -> ReviewIntelligenceResponse:
    """Generate mock response when service unavailable."""
    return ReviewIntelligenceResponse(
        # ⚠️ FALLBACK RESPONSE - No actual review data was analyzed
        # When real reviews are available, we use the 3,750+ granular type system
        request_id=request_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        product_name=request.product_name,
        brand=request.brand,
        reviews_analyzed=0,
        sources_used=["FALLBACK - No reviews analyzed"],
        # LEGACY archetype distribution (kept for backward compatibility)
        # The granular system (3,750+ types) should be used when reviews are available
        buyer_archetypes={
            "Achiever": 0.35, "Explorer": 0.25,
            "Connector": 0.20, "Guardian": 0.15, "Pragmatist": 0.05,
            "_warning": "LEGACY FALLBACK - Submit reviews for granular type analysis"
        },
        dominant_archetype="Achiever",
        archetype_confidence=0.35,  # Low confidence - fallback
        personality_traits={
            "openness": 0.68, "conscientiousness": 0.72,
            "extraversion": 0.65, "agreeableness": 0.58, "neuroticism": 0.42,
        },
        regulatory_focus={"promotion": 0.62, "prevention": 0.38},
        purchase_motivations=["quality", "convenience", "value"],
        primary_motivation="quality",
        language_intelligence={
            "phrases": ["[no review data - fallback]"],
            "power_words": [],
            "tone": "neutral",
            "note": "Submit actual reviews to extract authentic language patterns",
        },
        mechanism_predictions={"authority": 0.5, "social_proof": 0.5, "scarcity": 0.5},
        ideal_customer={
            # GRANULAR TYPE SYSTEM FIELDS (populated with real review data)
            "granular_type_id": None,  # Would be e.g., "quality_seeking_system2_promotion_high_premium_achiever_tech"
            "granular_type_name": None,  # Would be e.g., "Quality-Seeking Analytical Tech Achiever"
            "purchase_motivation": None,  # Would be one of 15 motivations
            "decision_style": None,  # Would be system1, system2, or mixed
            # LEGACY FIELDS (used as fallback)
            "archetype": "Achiever",
            "archetype_confidence": 0.35,  # Low - fallback
            "primary_motivations": ["quality", "status"],
            "characteristic_phrases": ["[no data - fallback]"],
            "_system": "FALLBACK - Granular type detection requires review text",
        },
        flow_state={
            "arousal": 0.5, "valence": 0.5,
            "optimal_formats": ["adult_contemporary"],
            "ad_receptivity": 0.5,
        },
        psychological_needs={
            "primary_needs": [],
            "unmet_needs": [],
            "alignment_score": 0.0,
            "alignment_gaps": ["No review data analyzed"],
        },
        unified_ad_recommendations=[{
            "priority_score": 0.5,
            "construct_name": "Awaiting Review Data",
            "recommendation": "Submit product reviews to get personalized recommendations using the 3,750+ granular type system",
            "confidence": 0.0,
        }],
        unified_archetype="Achiever",  # Legacy
        unified_archetype_confidence=0.35,
        avg_rating=0.0,
        overall_confidence=0.35,  # Low confidence indicates fallback
        processing_time_ms=(time.time() - start_time) * 1000,
    )


def _aggregate_review_analyses(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate multiple review analyses into summary."""
    if not results:
        return {}
    
    # Calculate archetype distribution
    archetype_counts: Dict[str, int] = {}
    for r in results:
        arch = r.get("archetype", "unknown")
        archetype_counts[arch] = archetype_counts.get(arch, 0) + 1
    
    total = len(results)
    archetype_dist = {k: v / total for k, v in archetype_counts.items()}
    
    # Get dominant archetype
    dominant = max(archetype_counts, key=archetype_counts.get) if archetype_counts else "unknown"
    
    return {
        "archetype_distribution": archetype_dist,
        "dominant_archetype": dominant,
        "sample_size": total,
    }
