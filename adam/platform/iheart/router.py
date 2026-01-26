# =============================================================================
# ADAM iHeart API Router
# Location: adam/platform/iheart/router.py
# =============================================================================

"""
iHEART API ROUTER

FastAPI endpoints for iHeart ad serving integration.

Endpoints:
- POST /api/v1/iheart/ad-request - Request an ad decision
- POST /api/v1/iheart/outcome - Record ad outcome
- GET /api/v1/iheart/session/{session_id} - Get session info
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from adam.core.container import get_container, ADAMContainer
from adam.platform.iheart.models.advertising import (
    AdOutcomeType,
    Campaign,
    AdCreative,
    CreativeType,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/iheart", tags=["iheart"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class CampaignRequest(BaseModel):
    """Campaign in ad request."""
    
    campaign_id: str
    brand_id: str
    brand_name: str
    target_genres: List[str] = Field(default_factory=list)
    target_mechanisms: List[str] = Field(default_factory=list)
    is_active: bool = Field(default=True)


class CreativeRequest(BaseModel):
    """Creative in ad request."""
    
    creative_id: str
    campaign_id: str
    name: str
    duration_seconds: int = Field(default=30, ge=0)
    creative_type: str = Field(default="midroll")
    target_mechanisms: List[str] = Field(default_factory=list)
    is_active: bool = Field(default=True)


class AdRequestBody(BaseModel):
    """Request body for ad decision."""
    
    user_id: str
    session_id: str
    station_id: str
    slot_position: str = Field(default="midroll")
    
    # Available ads
    campaigns: List[CampaignRequest]
    creatives: List[CreativeRequest]
    
    # Content context
    content_before_id: Optional[str] = None
    content_energy: Optional[float] = Field(None, ge=0.0, le=1.0)
    content_valence: Optional[float] = Field(None, ge=0.0, le=1.0)


class AdDecisionResponse(BaseModel):
    """Response with ad decision."""
    
    decision_id: str
    
    # Selected ad
    campaign_id: str
    creative_id: str
    
    # Psychological reasoning
    mechanisms_applied: List[str]
    primary_mechanism: Optional[str] = None
    
    # Confidence
    selection_confidence: float = Field(ge=0.0, le=1.0)
    selection_reason: str
    
    # Latency
    latency_ms: float = Field(ge=0.0)


class OutcomeRequest(BaseModel):
    """Request to record outcome."""
    
    decision_id: str
    outcome_type: str  # AdOutcomeType value
    
    # Listening behavior
    listen_duration_seconds: int = Field(default=0, ge=0)
    listen_percentage: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Actions
    clicked: bool = Field(default=False)
    converted: bool = Field(default=False)
    conversion_value: Optional[float] = Field(None, ge=0.0)


class OutcomeResponse(BaseModel):
    """Response after recording outcome."""
    
    outcome_id: str
    decision_id: str
    processed: bool
    signals_generated: int = Field(default=0, ge=0)


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/ad-request", response_model=AdDecisionResponse)
async def request_ad(
    request: AdRequestBody,
    background_tasks: BackgroundTasks,
    container: ADAMContainer = Depends(get_container),
) -> AdDecisionResponse:
    """
    Request an ad decision for an iHeart ad slot.
    
    This calls into ADAM's full psychological reasoning pipeline.
    """
    start_time = datetime.now(timezone.utc)
    
    try:
        from adam.platform.iheart.service import iHeartAdService
        
        service = iHeartAdService(container)
        
        # Convert request models
        campaigns = [
            Campaign(
                campaign_id=c.campaign_id,
                brand_id=c.brand_id,
                brand_name=c.brand_name,
                name=c.brand_name,
                target_genres=c.target_genres,
                target_mechanisms=c.target_mechanisms,
                is_active=c.is_active,
            )
            for c in request.campaigns
        ]
        
        creatives_by_campaign: Dict[str, List[AdCreative]] = {}
        for c in request.creatives:
            creative = AdCreative(
                creative_id=c.creative_id,
                campaign_id=c.campaign_id,
                name=c.name,
                duration_seconds=c.duration_seconds,
                creative_type=CreativeType(c.creative_type) if c.creative_type in [e.value for e in CreativeType] else CreativeType.MIDROLL,
                target_mechanisms=c.target_mechanisms,
                is_active=c.is_active,
            )
            if c.campaign_id not in creatives_by_campaign:
                creatives_by_campaign[c.campaign_id] = []
            creatives_by_campaign[c.campaign_id].append(creative)
        
        # Get decision
        decision = await service.request_ad(
            user_id=request.user_id,
            session_id=request.session_id,
            station_id=request.station_id,
            available_campaigns=campaigns,
            creatives_by_campaign=creatives_by_campaign,
            slot_position=request.slot_position,
            content_context={
                "content_before_id": request.content_before_id,
                "content_energy": request.content_energy,
                "content_valence": request.content_valence,
            },
        )
        
        # Calculate latency
        end_time = datetime.now(timezone.utc)
        latency_ms = (end_time - start_time).total_seconds() * 1000
        
        return AdDecisionResponse(
            decision_id=decision.decision_id,
            campaign_id=decision.campaign_id,
            creative_id=decision.creative_id,
            mechanisms_applied=decision.mechanisms_applied,
            primary_mechanism=decision.primary_mechanism,
            selection_confidence=decision.selection_confidence,
            selection_reason=decision.selection_reason,
            latency_ms=latency_ms,
        )
    
    except Exception as e:
        logger.exception(f"Error in iHeart ad request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outcome", response_model=OutcomeResponse)
async def record_outcome(
    request: OutcomeRequest,
    container: ADAMContainer = Depends(get_container),
) -> OutcomeResponse:
    """
    Record the outcome of an ad play.
    
    This triggers learning updates across ADAM.
    """
    try:
        from adam.platform.iheart.service import iHeartAdService
        
        # Map outcome type
        try:
            outcome_type = AdOutcomeType(request.outcome_type)
        except ValueError:
            outcome_type = AdOutcomeType.LISTEN_PARTIAL
        
        service = iHeartAdService(container)
        
        outcome = await service.record_outcome(
            decision_id=request.decision_id,
            outcome_type=outcome_type,
            listen_duration_seconds=request.listen_duration_seconds,
            listen_percentage=request.listen_percentage,
            clicked=request.clicked,
            converted=request.converted,
            conversion_value=request.conversion_value,
        )
        
        return OutcomeResponse(
            outcome_id=outcome.outcome_id,
            decision_id=request.decision_id,
            processed=outcome.processed_by_gradient_bridge,
            signals_generated=1,  # Would get from gradient bridge
        )
    
    except Exception as e:
        logger.exception(f"Error recording iHeart outcome: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def iheart_health() -> Dict[str, Any]:
    """Health check for iHeart integration."""
    return {
        "status": "healthy",
        "platform": "iheart",
        "version": "1.0.0",
    }
