# =============================================================================
# ADAM WPP API Router
# Location: adam/platform/wpp/router.py
# =============================================================================

"""
WPP AD DESK API ROUTER

FastAPI endpoints for WPP advertising platform integration.

Endpoints:
- POST /api/v1/wpp/optimize - Optimize campaign creative selection
- POST /api/v1/wpp/outcome - Record campaign outcome
- GET /api/v1/wpp/insights/{campaign_id} - Get campaign insights
- GET /api/v1/wpp/priors/{category} - Get Amazon priors
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from adam.core.container import get_container, ADAMContainer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/wpp", tags=["wpp"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class BrandConstraintsRequest(BaseModel):
    """Brand constraints in request."""
    
    mechanism_constraints: Dict[str, str] = Field(default_factory=dict)
    max_mechanism_intensity: float = Field(ge=0.0, le=1.0, default=0.8)


class BrandRequest(BaseModel):
    """Brand info in request."""
    
    brand_id: str
    name: str
    category: str
    constraints: BrandConstraintsRequest = Field(
        default_factory=BrandConstraintsRequest
    )


class CampaignRequest(BaseModel):
    """Campaign in request."""
    
    campaign_id: str
    name: str
    objective: str = Field(default="awareness")
    target_categories: List[str] = Field(default_factory=list)
    preferred_mechanisms: List[str] = Field(default_factory=list)


class CreativeRequest(BaseModel):
    """Creative in request."""
    
    creative_id: str
    name: str
    mechanisms: List[str] = Field(default_factory=list)
    personality_target: Dict[str, float] = Field(default_factory=dict)


class OptimizeRequest(BaseModel):
    """Request for campaign optimization."""
    
    user_id: str
    platform: str = Field(default="iheart")
    
    campaign: CampaignRequest
    brand: BrandRequest
    creatives: List[CreativeRequest]


class OptimizeResponse(BaseModel):
    """Response with optimization result."""
    
    request_id: str
    campaign_id: str
    brand_id: str
    
    # Selected creative
    selected_creative_id: str
    selected_creative_name: str
    
    # Mechanisms
    mechanisms_applied: List[str]
    
    # Amazon priors
    amazon_priors_used: bool
    archetype_match: Optional[Dict[str, Any]] = None
    
    # Verification
    verification_status: str
    
    # Latency
    latency_ms: float = Field(ge=0.0)


class OutcomeRequest(BaseModel):
    """Request to record outcome."""
    
    campaign_id: str
    request_id: str
    user_id: str
    outcome_type: str  # "impression", "click", "conversion"
    outcome_value: float = Field(ge=0.0, le=1.0)
    revenue: Optional[float] = Field(None, ge=0.0)


class OutcomeResponse(BaseModel):
    """Response after recording outcome."""
    
    request_id: str
    campaign_id: str
    processed: bool
    signals_generated: int = Field(default=0, ge=0)


class CategoryPriorResponse(BaseModel):
    """Response with category priors."""
    
    category_id: str
    category_name: str
    typical_personality: Dict[str, float]
    mechanism_priors: Dict[str, float]
    regulatory_tendency: str
    sample_size: int


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/optimize", response_model=OptimizeResponse)
async def optimize_campaign(
    request: OptimizeRequest,
    container: ADAMContainer = Depends(get_container),
) -> OptimizeResponse:
    """
    Optimize campaign creative selection using ADAM intelligence.
    
    Uses psychological reasoning + Amazon priors + brand constraints.
    """
    start_time = datetime.now(timezone.utc)
    
    try:
        from adam.platform.wpp.service import WPPAdDeskService
        from adam.platform.wpp.models.brand import (
            BrandProfile,
            WPPCampaign,
            BrandConstraints,
            MechanismConstraint,
            CampaignObjective,
        )
        
        service = WPPAdDeskService(container)
        
        # Build brand profile
        brand = BrandProfile(
            brand_id=request.brand.brand_id,
            name=request.brand.name,
            advertiser_id=request.brand.brand_id,
            category=request.brand.category,
            constraints=BrandConstraints(
                mechanism_constraints={
                    k: MechanismConstraint(v)
                    for k, v in request.brand.constraints.mechanism_constraints.items()
                    if v in [e.value for e in MechanismConstraint]
                },
                max_mechanism_intensity=request.brand.constraints.max_mechanism_intensity,
            ),
        )
        
        # Build campaign
        campaign = WPPCampaign(
            campaign_id=request.campaign.campaign_id,
            brand_id=request.brand.brand_id,
            advertiser_id=request.brand.brand_id,
            name=request.campaign.name,
            objective=CampaignObjective(request.campaign.objective) if request.campaign.objective in [e.value for e in CampaignObjective] else CampaignObjective.AWARENESS,
            target_categories=request.campaign.target_categories,
            preferred_mechanisms=request.campaign.preferred_mechanisms,
            budget_total=0.0,
            budget_daily=0.0,
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc),
        )
        
        # Build creatives
        creatives = [
            {
                "creative_id": c.creative_id,
                "name": c.name,
                "mechanisms": c.mechanisms,
                "personality_target": c.personality_target,
            }
            for c in request.creatives
        ]
        
        # Optimize
        result = await service.optimize_campaign(
            campaign=campaign,
            brand=brand,
            target_user_id=request.user_id,
            available_creatives=creatives,
            platform=request.platform,
        )
        
        # Calculate latency
        end_time = datetime.now(timezone.utc)
        latency_ms = (end_time - start_time).total_seconds() * 1000
        
        selected = result.get("selected_creative", {})
        
        return OptimizeResponse(
            request_id=result["request_id"],
            campaign_id=result["campaign_id"],
            brand_id=result["brand_id"],
            selected_creative_id=selected.get("creative_id", ""),
            selected_creative_name=selected.get("name", ""),
            mechanisms_applied=result["mechanisms_applied"],
            amazon_priors_used=result["amazon_priors_used"],
            archetype_match=result.get("archetype_match"),
            verification_status=result["verification_status"],
            latency_ms=latency_ms,
        )
    
    except Exception as e:
        logger.exception(f"Error in WPP optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outcome", response_model=OutcomeResponse)
async def record_outcome(
    request: OutcomeRequest,
    container: ADAMContainer = Depends(get_container),
) -> OutcomeResponse:
    """
    Record campaign outcome for cross-platform learning.
    """
    try:
        from adam.platform.wpp.service import WPPAdDeskService
        
        service = WPPAdDeskService(container)
        
        result = await service.record_campaign_outcome(
            campaign_id=request.campaign_id,
            request_id=request.request_id,
            user_id=request.user_id,
            outcome_type=request.outcome_type,
            outcome_value=request.outcome_value,
            revenue=request.revenue,
        )
        
        return OutcomeResponse(
            request_id=request.request_id,
            campaign_id=request.campaign_id,
            processed=result["processed"],
            signals_generated=result["signals_generated"],
        )
    
    except Exception as e:
        logger.exception(f"Error recording WPP outcome: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/insights/{campaign_id}")
async def get_campaign_insights(
    campaign_id: str,
    container: ADAMContainer = Depends(get_container),
) -> Dict[str, Any]:
    """
    Get ADAM-derived psychological insights for a campaign.
    """
    try:
        from adam.platform.wpp.service import WPPAdDeskService
        
        service = WPPAdDeskService(container)
        return await service.get_campaign_insights(campaign_id)
    
    except Exception as e:
        logger.exception(f"Error getting insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/priors/{category}", response_model=CategoryPriorResponse)
async def get_category_priors(
    category: str,
    container: ADAMContainer = Depends(get_container),
) -> CategoryPriorResponse:
    """
    Get Amazon-derived psychological priors for a category.
    """
    try:
        from adam.platform.wpp.amazon_priors import AmazonPriorService
        
        prior_service = AmazonPriorService(container.redis_cache)
        prior = await prior_service.get_category_prior(category)
        
        if not prior:
            raise HTTPException(status_code=404, detail=f"No priors for category: {category}")
        
        return CategoryPriorResponse(
            category_id=prior.category_id,
            category_name=prior.category_name,
            typical_personality={
                "openness": prior.typical_personality.openness,
                "conscientiousness": prior.typical_personality.conscientiousness,
                "extraversion": prior.typical_personality.extraversion,
                "agreeableness": prior.typical_personality.agreeableness,
                "neuroticism": prior.typical_personality.neuroticism,
            },
            mechanism_priors={
                m_id: m.responsiveness
                for m_id, m in prior.mechanism_priors.items()
            },
            regulatory_tendency=prior.regulatory_focus_tendency,
            sample_size=prior.total_reviews_analyzed,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting priors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def wpp_health() -> Dict[str, Any]:
    """Health check for WPP integration."""
    return {
        "status": "healthy",
        "platform": "wpp",
        "version": "1.0.0",
    }
