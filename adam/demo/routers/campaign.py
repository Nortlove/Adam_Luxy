# =============================================================================
# ADAM Demo - Campaign Router
# Campaign analysis and scenario endpoints
# =============================================================================

"""
Campaign analysis API endpoints for the ADAM demo platform.

Includes:
- Full campaign analysis with ADAM orchestrator
- Buyer-friendly campaign analysis
- Pre-defined demo scenarios
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Campaign Analysis"])


# =============================================================================
# MODELS
# =============================================================================

class CampaignRequest(BaseModel):
    """Request for campaign analysis."""
    brand_name: str = Field(..., description="Brand name")
    product_name: Optional[str] = Field(None, description="Product name")
    description: Optional[str] = Field(None, description="Product/campaign description")
    call_to_action: Optional[str] = Field(None, description="Desired call to action")
    product_url: Optional[str] = Field(None, description="Product URL for review scraping")
    target_audience: Optional[str] = Field(None, description="Target audience description")
    category: Optional[str] = Field(None, description="Product category")
    subcategory: Optional[str] = Field(None, description="Product subcategory")


class CampaignAnalysisResponse(BaseModel):
    """Response from campaign analysis."""
    request_id: str
    timestamp: str
    brand_name: str
    product_name: Optional[str]
    customer_segments: List[Dict[str, Any]]
    station_recommendations: List[Dict[str, Any]]
    review_intelligence: Optional[Dict[str, Any]]
    relationship_intelligence: Optional[Dict[str, Any]]
    psychological_constructs: Optional[Dict[str, Any]]
    components_used: List[str]
    overall_confidence: float
    reasoning_trace: Optional[Dict[str, Any]]
    processing_time_ms: float


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/analyze-campaign", response_model=CampaignAnalysisResponse)
async def analyze_campaign(request: CampaignRequest) -> CampaignAnalysisResponse:
    """
    Analyze a campaign using the FULL ADAM system.
    
    This is the primary endpoint for the iHeart demo that uses
    the REAL ADAM orchestrator to coordinate:
    1. Review Intelligence (scraping + psychological analysis)
    2. Graph Intelligence (Neo4j mechanism/archetype queries)
    3. AtomDAG Execution (atom of thought reasoning)
    4. MetaLearner (Thompson Sampling mechanism selection)
    5. Full reasoning trace for demo visibility
    """
    start_time = time.time()
    request_id = str(uuid4())[:8]
    
    try:
        from adam.orchestrator import get_campaign_orchestrator
        
        orchestrator = get_campaign_orchestrator()
        
        result = await orchestrator.analyze_campaign(
            brand=request.brand_name,
            product=request.product_name,
            description=request.description,
            call_to_action=request.call_to_action,
            product_url=request.product_url,
            target_audience=request.target_audience,
            category=request.category,
            subcategory=request.subcategory,
            return_reasoning=True,
        )
        
        logger.info(
            f"ADAM Analysis complete: {len(result.customer_segments)} segments, "
            f"{len(result.components_used)} components, "
            f"{result.overall_confidence:.0%} confidence"
        )
        
        # Convert to response format
        segments = []
        for seg in result.customer_segments:
            segments.append({
                "segment_id": seg.segment_id,
                "segment_name": seg.segment_name,
                "archetype": seg.archetype,
                "match_score": seg.match_score,
                "primary_mechanism": seg.primary_mechanism,
                "secondary_mechanisms": seg.secondary_mechanisms,
                "recommended_tone": seg.recommended_tone,
                "example_hook": seg.example_hook,
            })
        
        stations = []
        for st in result.station_recommendations:
            stations.append({
                "station_format": st.station_format,
                "station_description": st.station_description,
                "recommendation_reason": st.recommendation_reason,
                "peak_receptivity_score": st.peak_receptivity_score,
                "best_dayparts": st.best_dayparts,
            })
        
        return CampaignAnalysisResponse(
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            brand_name=request.brand_name,
            product_name=request.product_name,
            customer_segments=segments,
            station_recommendations=stations,
            review_intelligence=result.reasoning_trace.review_intelligence_summary if result.reasoning_trace else None,
            relationship_intelligence=None,
            psychological_constructs=None,
            components_used=result.components_used,
            overall_confidence=result.overall_confidence,
            reasoning_trace=result.reasoning_trace.__dict__ if result.reasoning_trace else None,
            processing_time_ms=(time.time() - start_time) * 1000,
        )
        
    except ImportError as e:
        logger.error(f"Campaign orchestrator not available: {e}")
        raise HTTPException(status_code=503, detail=f"Campaign orchestrator not available: {e}")
    except Exception as e:
        logger.error(f"Error analyzing campaign: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-campaign/buyer-friendly")
async def analyze_campaign_buyer_friendly(request: CampaignRequest) -> Dict[str, Any]:
    """
    Simplified campaign analysis for media buyers.
    
    Returns actionable insights in a format optimized for media buying decisions:
    - Clear archetype targeting
    - Station/format recommendations
    - Daypart optimization
    - Copy direction
    """
    start_time = time.time()
    
    try:
        from adam.orchestrator import get_campaign_orchestrator
        
        orchestrator = get_campaign_orchestrator()
        result = await orchestrator.analyze_campaign(
            brand=request.brand_name,
            product=request.product_name,
            description=request.description,
            category=request.category,
            return_reasoning=False,
        )
        
        # Simplify for buyers
        primary_segment = result.customer_segments[0] if result.customer_segments else None
        primary_station = result.station_recommendations[0] if result.station_recommendations else None
        
        return {
            "brand": request.brand_name,
            "recommendation": {
                "target_customer": {
                    "archetype": primary_segment.archetype if primary_segment else "General",
                    "description": primary_segment.segment_name if primary_segment else "Broad audience",
                    "confidence": primary_segment.match_score if primary_segment else 0.5,
                },
                "messaging": {
                    "primary_mechanism": primary_segment.primary_mechanism if primary_segment else "social_proof",
                    "tone": primary_segment.recommended_tone if primary_segment else "authentic",
                    "hook_example": primary_segment.example_hook if primary_segment else "Discover what works for you",
                },
                "placement": {
                    "format": primary_station.station_format if primary_station else "Adult Contemporary",
                    "best_dayparts": primary_station.best_dayparts if primary_station else ["Morning Drive"],
                    "receptivity": primary_station.peak_receptivity_score if primary_station else 0.7,
                },
            },
            "confidence": result.overall_confidence,
            "processing_time_ms": (time.time() - start_time) * 1000,
        }
        
    except ImportError as e:
        logger.error(f"Campaign orchestrator not available: {e}")
        raise HTTPException(status_code=503, detail=f"Campaign orchestrator not available: {e}")
    except Exception as e:
        logger.error(f"Error in buyer-friendly analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scenarios")
async def get_demo_scenarios() -> Dict[str, Any]:
    """
    Get pre-defined demo scenarios for showcasing ADAM capabilities.
    
    Returns curated scenarios covering different industries and use cases.
    """
    scenarios = [
        {
            "id": "anti_aging_serum",
            "name": "Anti-Aging Serum",
            "brand": "Premium Skincare",
            "category": "All_Beauty",
            "asin": "B001LY7FRK",
            "description": "Clinical anti-aging serum with prevention-focused psychology",
            "target_audience": "Women 35-55 seeking evidence-based skincare",
        },
        {
            "id": "trend_cosmetics",
            "name": "Trend Color Palette",
            "brand": "Innovation Beauty",
            "category": "All_Beauty",
            "asin": "B01NB1ZBA1",
            "description": "Bold color cosmetics driven by novelty-seeking psychology",
            "target_audience": "Trend-forward beauty consumers 20-35",
        },
        {
            "id": "organic_skincare",
            "name": "Organic Face Oil",
            "brand": "Natural Beauty",
            "category": "All_Beauty",
            "asin": "B06XRZ6Q4Z",
            "description": "Clean beauty product for trust-oriented health-conscious consumers",
            "target_audience": "Clean beauty seekers 25-45",
        },
        {
            "id": "expert_treatment",
            "name": "Professional Treatment",
            "brand": "Expert Beauty",
            "category": "All_Beauty",
            "asin": "B00KCTER3U",
            "description": "Dermatologist-grade treatment driven by authority signals",
            "target_audience": "Results-driven skincare enthusiasts 28-50",
        },
        {
            "id": "community_skincare",
            "name": "Viral Skincare",
            "brand": "Community Beauty",
            "category": "All_Beauty",
            "asin": "B01IDOV7TC",
            "description": "Community-validated products where peer influence drives conversion",
            "target_audience": "Social beauty enthusiasts 22-40",
        },
    ]
    
    return {
        "scenarios": scenarios,
        "count": len(scenarios),
        "note": "Use scenario ID with /scenarios/{id} for full analysis",
    }


@router.get("/scenarios/{scenario_id}")
async def run_scenario(scenario_id: str) -> Dict[str, Any]:
    """
    Run a pre-defined demo scenario.
    
    Returns full ADAM analysis for the selected scenario.
    """
    # Scenario definitions
    scenarios = {
        "anti_aging_serum": CampaignRequest(
            brand_name="Premium Skincare",
            product_name="Anti-Aging Serum",
            description="Clinical anti-aging serum backed by 12 peer-reviewed studies",
            category="All_Beauty",
            subcategory="Anti-Aging Skincare",
            target_audience="Women 35-55 seeking evidence-based skincare",
        ),
        "trend_cosmetics": CampaignRequest(
            brand_name="Innovation Beauty",
            product_name="Trend Color Palette",
            description="Bold color cosmetics with never-before-seen pigmentation technology",
            category="All_Beauty",
            subcategory="Color Cosmetics",
            target_audience="Trend-forward beauty consumers 20-35",
        ),
        "organic_skincare": CampaignRequest(
            brand_name="Natural Beauty",
            product_name="Organic Face Oil",
            description="100% organic face oil with full ingredient traceability",
            category="All_Beauty",
            subcategory="Clean Beauty",
            target_audience="Clean beauty seekers 25-45",
        ),
    }
    
    if scenario_id not in scenarios:
        raise HTTPException(
            status_code=404,
            detail=f"Scenario not found: {scenario_id}"
        )
    
    # Run the full analysis
    return await analyze_campaign(scenarios[scenario_id])


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _get_mock_campaign_response(
    request: CampaignRequest,
    request_id: str,
    start_time: float,
) -> CampaignAnalysisResponse:
    """Generate mock response when orchestrator unavailable."""
    return CampaignAnalysisResponse(
        request_id=request_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        brand_name=request.brand_name,
        product_name=request.product_name,
        customer_segments=[{
            "segment_id": "seg_001",
            "segment_name": "Achievement-Driven Professionals",
            "archetype": "achiever",
            "match_score": 0.85,
            "primary_mechanism": "authority",
            "secondary_mechanisms": ["social_proof", "scarcity"],
            "recommended_tone": "confident and aspirational",
            "example_hook": "Trusted by industry leaders",
        }],
        station_recommendations=[{
            "station_format": "Adult Contemporary",
            "station_description": "Professional listeners during commute",
            "recommendation_reason": "High concentration of target archetype",
            "peak_receptivity_score": 0.78,
            "best_dayparts": ["Morning Drive", "Evening Drive"],
        }],
        review_intelligence=None,
        relationship_intelligence=None,
        psychological_constructs=None,
        components_used=["mock_data"],
        overall_confidence=0.65,
        reasoning_trace=None,
        processing_time_ms=(time.time() - start_time) * 1000,
    )


def _get_mock_buyer_friendly_response(
    request: CampaignRequest,
    start_time: float,
) -> Dict[str, Any]:
    """
    Generate mock buyer-friendly response.
    
    ⚠️ NOTE: This is a MOCK/FALLBACK response when the orchestrator is unavailable.
    Real responses use the 3,750+ GRANULAR TYPE SYSTEM.
    """
    return {
        "brand": request.brand_name,
        "recommendation": {
            "target_customer": {
                # LEGACY archetype (kept for backward compatibility)
                "archetype": "Achiever",
                "description": "Achievement-driven professionals",
                "confidence": 0.35,  # Low confidence - mock data
                # GRANULAR TYPE SYSTEM fields (would be populated with real analysis)
                "granular_type_id": None,  # e.g., "quality_seeking_system2_promotion_high_premium_achiever_tech"
                "granular_type_name": None,  # e.g., "Quality-Seeking Analytical Achiever"
                "purchase_motivation": None,  # e.g., "quality_seeking"
                "decision_style": None,  # e.g., "system2"
                "_system": "MOCK DATA - Real analysis uses 3,750+ granular customer types",
            },
            "messaging": {
                "primary_mechanism": "authority",
                "tone": "confident",
                "hook_example": "The professional's choice",
            },
            "placement": {
                "format": "Adult Contemporary",
                "best_dayparts": ["Morning Drive"],
                "receptivity": 0.72,
            },
        },
        "confidence": 0.35,  # Low confidence - mock data
        "processing_time_ms": (time.time() - start_time) * 1000,
        "note": "MOCK DATA - orchestrator not available. Real analysis uses 3,750+ granular customer types.",
    }
