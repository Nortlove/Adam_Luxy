"""
StackAdapt Creative Intelligence API — FastAPI Router
=======================================================

Endpoints:
    POST /api/v1/stackadapt/creative-intelligence   — <50ms creative params
    GET  /api/v1/stackadapt/segments                 — available segments
    GET  /api/v1/stackadapt/health                   — service health
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from adam.api.stackadapt.models import (
    ArbitrageIntelligenceResponse,
    ContextIntelligenceResponse,
    CounterfactualAlternative,
    CounterfactualAnalysisResponse,
    CreativeIntelligenceRequest,
    CreativeIntelligenceResponse,
    CreativeParameters,
    CopyGuidance,
    ExpectedLift,
    GradientIntelligenceResponse,
    GradientOptimizationPriority,
    HealthResponse,
    InformationValueResponse,
    MechanismGuidance,
    MechanismPortfolioEntry,
    MechanismPortfolioResponse,
    NDFProfile,
    ProductIntelligence,
    SegmentListItem,
    SegmentListResponse,
    SessionStateResponse,
)
from adam.api.stackadapt.service import get_creative_intelligence_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/stackadapt", tags=["stackadapt"])


_INTELLIGENCE_LEVELS = {
    1: "L1_archetype",
    2: "L2_category",
    3: "L3_bilateral",
    4: "L4_inferential",
    5: "L5_full_reasoning",
}


def _cascade_to_intelligence_level(cascade_level: int) -> str:
    """Map cascade level int to human-readable intelligence tier."""
    return _INTELLIGENCE_LEVELS.get(cascade_level, "static_heuristic")


def _build_counterfactual(data: Optional[dict]) -> Optional[CounterfactualAnalysisResponse]:
    """Build CounterfactualAnalysisResponse from service dict."""
    if not data:
        return None
    return CounterfactualAnalysisResponse(
        chosen_mechanism=data["chosen_mechanism"],
        chosen_effectiveness=data["chosen_effectiveness"],
        alternatives=[
            CounterfactualAlternative(**a) for a in data.get("alternatives", [])
        ],
        chosen_is_optimal=data.get("chosen_is_optimal", True),
        best_alternative=data.get("best_alternative", ""),
        evidence_depth=data.get("evidence_depth", "unknown"),
        reasoning=data.get("reasoning", []),
    )


@router.post(
    "/creative-intelligence",
    response_model=CreativeIntelligenceResponse,
    summary="Real-time creative intelligence for DCO",
    description="Returns psychological creative parameters in <50ms for StackAdapt DCO integration.",
)
async def creative_intelligence(request: CreativeIntelligenceRequest):
    service = get_creative_intelligence_service()
    if not service.is_ready:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        result = service.get_creative_intelligence(
            segment_id=request.segment_id,
            content_category=request.content_category,
            device_type=request.device_type,
            page_url=request.page_url,
            time_of_day=request.time_of_day,
            day_of_week=request.day_of_week,
            product_category=request.product_category,
            brand_name=request.brand_name,
            asin=request.asin,
            buyer_id=request.buyer_id,
        )
    except Exception as e:
        logger.error("Creative intelligence error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    mech_guidance = None
    if result.get("mechanism_guidance"):
        mech_guidance = MechanismGuidance(**result["mechanism_guidance"])

    prod_intel = None
    if result.get("product_intelligence"):
        prod_intel = ProductIntelligence(**result["product_intelligence"])

    grad_intel = None
    if result.get("gradient_intelligence"):
        gi = result["gradient_intelligence"]
        grad_intel = GradientIntelligenceResponse(
            optimization_priorities=[
                GradientOptimizationPriority(**p) for p in gi.get("optimization_priorities", [])
            ],
            total_expected_lift_delta=gi.get("total_expected_lift_delta", 0.0),
            field_metadata=gi.get("field_metadata", {}),
        )

    info_val = None
    if result.get("information_value"):
        info_val = InformationValueResponse(**result["information_value"])

    ctx_intel = None
    if result.get("context_intelligence"):
        ctx_intel = ContextIntelligenceResponse(**result["context_intelligence"])

    mech_portfolio = None
    if result.get("mechanism_portfolio"):
        mp = result["mechanism_portfolio"]
        mech_portfolio = MechanismPortfolioResponse(
            portfolio=[MechanismPortfolioEntry(**p) for p in mp.get("portfolio", [])],
            observation_count=mp.get("observation_count", 0),
        )

    return CreativeIntelligenceResponse(
        decision_id=result.get("decision_id", ""),
        creative_parameters=CreativeParameters(**result["creative_parameters"]),
        ndf_profile=NDFProfile(**result["ndf_profile"]),
        copy_guidance=CopyGuidance(**result["copy_guidance"]),
        expected_lift=ExpectedLift(**result["expected_lift"]),
        mechanism_chain=result.get("mechanism_chain", []),
        mechanism_scores=result.get("mechanism_scores"),
        reasoning_trace=result.get("reasoning_trace", []),
        segment_metadata=result.get("segment_metadata", {}),
        mechanism_guidance=mech_guidance,
        product_intelligence=prod_intel,
        gradient_intelligence=grad_intel,
        information_value=info_val,
        context_intelligence=ctx_intel,
        mechanism_portfolio=mech_portfolio,
        category_deviation=result.get("category_deviation"),
        decision_probability=result.get("decision_probability"),
        counterfactual=_build_counterfactual(result.get("counterfactual")),
        arbitrage=(
            ArbitrageIntelligenceResponse(**result["arbitrage"])
            if result.get("arbitrage") else None
        ),
        session_state=(
            SessionStateResponse(**result["session_state"])
            if result.get("session_state") else None
        ),
        timing_ms=result["timing_ms"],
        cascade_level=result.get("segment_metadata", {}).get("cascade_level", 1),
        intelligence_level=_cascade_to_intelligence_level(
            result.get("segment_metadata", {}).get("cascade_level", 1),
        ),
        evidence_source=result.get("segment_metadata", {}).get("evidence_source", "archetype_prior"),
    )


@router.get(
    "/segments",
    response_model=SegmentListResponse,
    summary="List available INFORMATIV segments",
    description="Returns all psychological audience segments available for StackAdapt campaigns.",
)
async def list_segments():
    service = get_creative_intelligence_service()
    if not service.is_ready:
        raise HTTPException(status_code=503, detail="Service not initialized")

    raw = service.list_segments()
    items = [SegmentListItem(**s) for s in raw]
    return SegmentListResponse(segments=items, total=len(items))


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Creative intelligence service health",
)
async def health():
    service = get_creative_intelligence_service()
    data = service.get_health()
    return HealthResponse(**data)
