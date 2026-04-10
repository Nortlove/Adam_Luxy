# =============================================================================
# ADAM Intelligence API Router
# Location: adam/api/intelligence/router.py
# =============================================================================

"""
INTELLIGENCE API

FastAPI router for querying ADAM's intelligence capabilities.

This exposes all the intelligence we've built:
- Brand copy analysis (Cialdini, Aaker)
- Helpful vote intelligence (templates, effectiveness)
- Journey intelligence (bought_together patterns)
- Archetype-mechanism effectiveness
- Product intelligence (combined brand + reviews)

These endpoints enable:
1. Pre-flight intelligence queries before decisions
2. Debugging and visualization of intelligence
3. Integration with external systems
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/intelligence", tags=["intelligence"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class BrandAnalysisRequest(BaseModel):
    """Request for brand copy analysis."""
    brand: str
    title: str = ""
    features: List[str] = Field(default_factory=list)
    description: str = ""


class BrandAnalysisResponse(BaseModel):
    """Response with brand persuasion analysis."""
    brand: str
    
    # Cialdini principles detected
    cialdini_scores: Dict[str, float]
    primary_cialdini: str
    secondary_cialdini: List[str]
    
    # Aaker brand personality
    aaker_scores: Dict[str, float]
    primary_personality: str
    personality_blend: List[str]
    
    # Tactics detected
    tactics: List[str]
    
    # Archetype alignment (which customer types this appeals to)
    archetype_alignment: Dict[str, float]


class ArchetypeEffectivenessResponse(BaseModel):
    """Response with archetype-mechanism effectiveness."""
    archetype: str
    mechanism_effectiveness: Dict[str, float]
    recommended_mechanisms: List[str]
    sample_sizes: Dict[str, int]


class PersuasiveTemplatesResponse(BaseModel):
    """Response with persuasive language templates."""
    archetype: str
    templates: List[Dict[str, Any]]
    total_templates: int


class JourneyIntelligenceResponse(BaseModel):
    """Response with product journey intelligence."""
    asin: str
    bought_together: List[Dict[str, Any]]
    journey_stage: str
    upgrade_path: List[str]
    accessory_bundle: List[str]
    recommended_next: List[Dict[str, Any]]


class FullIntelligenceRequest(BaseModel):
    """Request for full intelligence profile."""
    user_id: str = ""
    brand_name: str = ""
    product_asin: str = ""
    product_category: str = ""
    detected_archetype: str = ""


class FullIntelligenceResponse(BaseModel):
    """Response with complete intelligence package."""
    request_id: str
    
    # Sources available
    sources_available: List[str]
    confidence_level: str
    
    # Archetype effectiveness
    archetype_effectiveness: Dict[str, Dict[str, float]]
    
    # Best templates for this archetype
    persuasive_templates: List[Dict[str, Any]]
    
    # Brand analysis
    brand_cialdini_scores: Dict[str, float]
    brand_aaker_scores: Dict[str, float]
    brand_personality: str
    brand_tactics: List[str]
    
    # Journey intelligence
    journey_products: List[Dict[str, Any]]
    
    # Review stats
    total_reviews: int
    high_influence_reviews: int


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/brand/analyze", response_model=BrandAnalysisResponse)
async def analyze_brand_copy(request: BrandAnalysisRequest) -> BrandAnalysisResponse:
    """
    Analyze brand copy for persuasion intelligence.
    
    Extracts:
    - Cialdini principles (reciprocity, social proof, authority, etc.)
    - Aaker brand personality (sincerity, excitement, competence, etc.)
    - Persuasion tactics
    - Customer archetype alignment
    """
    try:
        from adam.intelligence.brand_copy_intelligence import (
            get_brand_copy_analyzer,
        )
        
        analyzer = get_brand_copy_analyzer()
        intel = analyzer.analyze(
            brand=request.brand,
            title=request.title,
            features=request.features,
            description=request.description,
        )
        
        return BrandAnalysisResponse(
            brand=request.brand,
            cialdini_scores=intel.cialdini.scores,
            primary_cialdini=intel.cialdini.primary_principle,
            secondary_cialdini=intel.cialdini.secondary_principles,
            aaker_scores=intel.aaker.scores,
            primary_personality=intel.aaker.primary_personality,
            personality_blend=intel.aaker.personality_blend,
            tactics=intel.tactics_detected,
            archetype_alignment=intel.archetype_alignment,
        )
        
    except Exception as e:
        logger.exception(f"Error analyzing brand copy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/archetype/{archetype}/effectiveness", response_model=ArchetypeEffectivenessResponse)
async def get_archetype_effectiveness(
    archetype: str,
    category: Optional[str] = Query(None, description="Product category filter"),
) -> ArchetypeEffectivenessResponse:
    """
    Get mechanism effectiveness rates for an archetype.
    
    Returns which persuasion mechanisms work best for this customer type,
    based on helpful vote analysis from reviews.
    """
    try:
        from adam.infrastructure.neo4j.pattern_persistence import (
            get_pattern_persistence,
        )
        
        persistence = get_pattern_persistence()
        effectiveness = await persistence.get_mechanism_effectiveness(
            archetype=archetype,
            category=category,
        )
        
        # Sort by effectiveness
        sorted_mechanisms = sorted(
            effectiveness.items(),
            key=lambda x: x[1],
            reverse=True,
        )
        
        return ArchetypeEffectivenessResponse(
            archetype=archetype,
            mechanism_effectiveness=effectiveness,
            recommended_mechanisms=[m[0] for m in sorted_mechanisms[:5]],
            sample_sizes={},  # Would need additional query
        )
        
    except Exception as e:
        logger.exception(f"Error getting archetype effectiveness: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/archetype/{archetype}/templates", response_model=PersuasiveTemplatesResponse)
async def get_persuasive_templates(
    archetype: str,
    mechanism: Optional[str] = Query(None, description="Filter by mechanism"),
    limit: int = Query(20, ge=1, le=100),
) -> PersuasiveTemplatesResponse:
    """
    Get persuasive language templates for an archetype.
    
    These are proven language patterns from high-helpful-vote reviews
    that resonate with this customer type.
    """
    try:
        from adam.infrastructure.neo4j.pattern_persistence import (
            get_pattern_persistence,
        )
        
        persistence = get_pattern_persistence()
        templates = await persistence.get_best_templates_for_archetype(
            archetype=archetype,
            mechanism=mechanism,
            limit=limit,
        )
        
        return PersuasiveTemplatesResponse(
            archetype=archetype,
            templates=templates,
            total_templates=len(templates),
        )
        
    except Exception as e:
        logger.exception(f"Error getting templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/journey/{asin}", response_model=JourneyIntelligenceResponse)
async def get_journey_intelligence(asin: str) -> JourneyIntelligenceResponse:
    """
    Get purchase journey intelligence for a product.
    
    Returns:
    - Products frequently bought together
    - Journey stage (entry, core, premium, accessory)
    - Upgrade paths
    - Cross-sell recommendations
    """
    try:
        from adam.intelligence.journey_intelligence import (
            get_journey_intelligence,
        )
        
        intel = await get_journey_intelligence(asin)
        
        return JourneyIntelligenceResponse(
            asin=asin,
            bought_together=intel.bought_together,
            journey_stage=intel.journey_stage,
            upgrade_path=intel.upgrade_path,
            accessory_bundle=intel.accessory_bundle,
            recommended_next=intel.recommended_next,
        )
        
    except Exception as e:
        logger.exception(f"Error getting journey intelligence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/full", response_model=FullIntelligenceResponse)
async def get_full_intelligence(request: FullIntelligenceRequest) -> FullIntelligenceResponse:
    """
    Get complete intelligence package for a decision context.
    
    This is the primary endpoint for gathering all available intelligence
    before making a decision. Returns everything ADAM knows about:
    - The detected/provided archetype
    - The brand (if provided)
    - The product (if ASIN provided)
    - Effective mechanisms and templates
    """
    try:
        from adam.intelligence.atom_intelligence_injector import (
            get_intelligence_injector,
        )
        
        injector = get_intelligence_injector()
        
        request_id = f"intel_{uuid4().hex[:12]}"
        
        intel = await injector.gather_intelligence(
            request_id=request_id,
            user_id=request.user_id or "anonymous",
            brand_name=request.brand_name or None,
            product_asin=request.product_asin or None,
            product_category=request.product_category or None,
            detected_archetype=request.detected_archetype or None,
        )
        
        return FullIntelligenceResponse(
            request_id=request_id,
            sources_available=intel.sources_available,
            confidence_level=intel.confidence_level,
            archetype_effectiveness=intel.archetype_effectiveness,
            persuasive_templates=intel.persuasive_templates,
            brand_cialdini_scores=intel.brand_cialdini_scores,
            brand_aaker_scores=intel.brand_aaker_scores,
            brand_personality=intel.brand_personality,
            brand_tactics=intel.brand_tactics,
            journey_products=intel.journey_products,
            total_reviews=intel.total_reviews,
            high_influence_reviews=intel.high_influence_reviews,
        )
        
    except Exception as e:
        logger.exception(f"Error getting full intelligence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/helpful-votes/stats")
async def get_helpful_vote_stats() -> Dict[str, Any]:
    """
    Get statistics about helpful vote intelligence.
    
    Returns coverage, top archetypes, and effectiveness data.
    """
    try:
        from adam.intelligence.helpful_vote_intelligence import (
            get_helpful_vote_intelligence,
        )
        
        hvi = get_helpful_vote_intelligence()
        routing_data = hvi.get_langgraph_routing_data()
        
        return {
            "coverage": routing_data.get("coverage", {}),
            "archetype_rankings": routing_data.get("archetype_mechanism_rankings", {}),
            "high_confidence_mechanisms": routing_data.get("high_confidence_mechanisms", []),
        }
        
    except Exception as e:
        logger.exception(f"Error getting helpful vote stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# COMPETITIVE INTELLIGENCE ENDPOINTS
# =============================================================================

class CompetitorAdRequest(BaseModel):
    """A competitor ad to analyze."""
    competitor_name: str
    ad_text: str


class CompetitiveAnalysisRequest(BaseModel):
    """Request for competitive intelligence."""
    our_brand: str
    competitor_ads: List[CompetitorAdRequest]
    target_archetypes: List[str] = Field(default_factory=list)


class CompetitiveAnalysisResponse(BaseModel):
    """Response with competitive intelligence."""
    our_brand: str
    competitors_analyzed: int
    
    # Market saturation
    market_mechanism_saturation: Dict[str, float]
    underutilized_mechanisms: List[str]
    
    # Opportunities
    top_vulnerabilities: List[Dict[str, Any]]
    
    # Recommendations
    recommended_strategies: List[Dict[str, Any]]
    
    # Archetypes not being served
    underserved_archetypes: List[str]


@router.post("/competitive/analyze", response_model=CompetitiveAnalysisResponse)
async def analyze_competitive_landscape(
    request: CompetitiveAnalysisRequest,
) -> CompetitiveAnalysisResponse:
    """
    Analyze competitive landscape and get counter-strategies.
    
    Analyzes competitor ads to:
    - Detect their persuasion mechanisms
    - Find psychological vulnerabilities they're not addressing
    - Recommend counter-strategies based on game theory
    """
    try:
        from adam.competitive.intelligence import (
            get_competitive_intelligence_service,
        )
        
        service = get_competitive_intelligence_service()
        
        # Analyze each competitor
        analyses = [
            service.analyze_competitor_ad(
                competitor_name=ad.competitor_name,
                ad_text=ad.ad_text,
            )
            for ad in request.competitor_ads
        ]
        
        # Build competitive intelligence
        intel = service.build_competitive_intelligence(
            our_brand=request.our_brand,
            competitor_analyses=analyses,
            target_archetypes=request.target_archetypes or None,
        )
        
        return CompetitiveAnalysisResponse(
            our_brand=request.our_brand,
            competitors_analyzed=len(analyses),
            market_mechanism_saturation=intel.market_mechanism_saturation,
            underutilized_mechanisms=intel.underutilized_mechanisms,
            top_vulnerabilities=[
                {
                    "mechanism": v.mechanism,
                    "opportunity_score": v.opportunity_score,
                    "rationale": v.rationale,
                    "counter_strategy": v.counter_strategy,
                    "target_archetypes": v.target_archetypes,
                }
                for v in intel.vulnerabilities[:5]
            ],
            recommended_strategies=[
                {
                    "name": s.strategy_name,
                    "description": s.description,
                    "primary_mechanism": s.primary_mechanism,
                    "secondary_mechanisms": s.secondary_mechanisms,
                    "target_archetypes": s.target_archetypes,
                    "expected_effectiveness": s.expected_effectiveness,
                    "implementation_hints": s.implementation_hints,
                }
                for s in intel.counter_strategies
            ],
            underserved_archetypes=intel.underserved_archetypes,
        )
        
    except Exception as e:
        logger.exception(f"Error analyzing competitive landscape: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/competitive/analyze-ad")
async def analyze_single_competitor_ad(
    request: CompetitorAdRequest,
) -> Dict[str, Any]:
    """
    Analyze a single competitor ad.
    
    Returns detected mechanisms and inferred target archetypes.
    """
    try:
        from adam.competitive.intelligence import analyze_competitor
        
        analysis = analyze_competitor(
            competitor_name=request.competitor_name,
            ad_text=request.ad_text,
        )
        
        return {
            "competitor": analysis.competitor_name,
            "mechanisms_detected": [
                {
                    "mechanism": m.mechanism,
                    "confidence": m.confidence,
                    "strength": m.strength.value,
                    "evidence": m.evidence[:5],
                }
                for m in analysis.mechanisms_detected
            ],
            "primary_mechanism": analysis.primary_mechanism,
            "secondary_mechanisms": analysis.secondary_mechanisms,
            "inferred_archetypes": analysis.inferred_target_archetypes,
            "archetype_confidence": analysis.archetype_confidence,
            "sophistication": analysis.persuasion_sophistication,
            "total_mechanisms": analysis.total_mechanisms_used,
        }
        
    except Exception as e:
        logger.exception(f"Error analyzing competitor ad: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# DSP CONSTRUCT ENDPOINTS
# =============================================================================

class ConstructResponse(BaseModel):
    """Response for a single DSP construct."""
    construct_id: str
    name: str = ""
    domain: str = ""
    description: str = ""
    confidence: str = ""
    advertising_relevance: str = ""
    adam_integration: str = ""
    citations: str = ""
    creative_implications: Dict[str, Any] = Field(default_factory=dict)
    effect_sizes: List[Dict[str, Any]] = Field(default_factory=list)
    dsp_signals: List[str] = Field(default_factory=list)


class ConstructListResponse(BaseModel):
    """Response for browsing constructs."""
    domain: str
    constructs: List[Dict[str, Any]]
    total: int


class InferentialChainResponse(BaseModel):
    """Response for inferential chain query."""
    source_id: str
    target_mechanism: str
    chains: List[Dict[str, Any]]
    total_chains: int


@router.get("/constructs/{construct_id}", response_model=ConstructResponse)
async def get_construct(construct_id: str) -> ConstructResponse:
    """
    Get a single DSP construct with all metadata.

    Returns the full construct node including creative_implications,
    effect_sizes, and DSP signal mappings.
    """
    try:
        import json as _json

        from adam.infrastructure.neo4j.pattern_persistence import (
            get_pattern_persistence,
        )

        persistence = get_pattern_persistence()
        construct = await persistence.get_dsp_construct(construct_id)

        if not construct:
            raise HTTPException(
                status_code=404,
                detail=f"Construct '{construct_id}' not found",
            )

        # Parse serialized JSON fields
        ci_raw = construct.get("creative_implications", "{}")
        try:
            creative_implications = _json.loads(ci_raw) if isinstance(ci_raw, str) else (ci_raw or {})
        except (TypeError, _json.JSONDecodeError):
            creative_implications = {}

        es_raw = construct.get("effect_sizes", "[]")
        try:
            effect_sizes = _json.loads(es_raw) if isinstance(es_raw, str) else (es_raw or [])
        except (TypeError, _json.JSONDecodeError):
            effect_sizes = []

        ds_raw = construct.get("dsp_signals", "[]")
        try:
            dsp_signals = _json.loads(ds_raw) if isinstance(ds_raw, str) else (ds_raw or [])
        except (TypeError, _json.JSONDecodeError):
            dsp_signals = []

        return ConstructResponse(
            construct_id=construct.get("construct_id", construct_id),
            name=construct.get("name", ""),
            domain=construct.get("domain", ""),
            description=construct.get("description", ""),
            confidence=construct.get("confidence", ""),
            advertising_relevance=construct.get("advertising_relevance", ""),
            adam_integration=construct.get("adam_integration", ""),
            citations=construct.get("citations", ""),
            creative_implications=creative_implications,
            effect_sizes=effect_sizes,
            dsp_signals=dsp_signals,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting construct: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/constructs", response_model=ConstructListResponse)
async def browse_constructs(
    domain: str = Query(..., description="Psychological domain to browse"),
    limit: int = Query(50, ge=1, le=200),
) -> ConstructListResponse:
    """
    Browse DSP constructs by psychological domain.

    Available domains: personality, motivation, temporal, contextual,
    values, cognitive, decision_making, social, emotional, etc.
    """
    try:
        from adam.infrastructure.neo4j.pattern_persistence import (
            get_pattern_persistence,
        )

        persistence = get_pattern_persistence()
        constructs = await persistence.get_constructs_by_domain(
            domain=domain,
            limit=limit,
        )

        return ConstructListResponse(
            domain=domain,
            constructs=constructs,
            total=len(constructs),
        )

    except Exception as e:
        logger.exception(f"Error browsing constructs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/constructs/{construct_id}/chain", response_model=InferentialChainResponse)
async def get_inferential_chain(
    construct_id: str,
    target_mechanism: str = Query(..., description="Target mechanism to trace to"),
    max_depth: int = Query(3, ge=1, le=5, description="Maximum chain depth"),
) -> InferentialChainResponse:
    """
    Get inferential chains from a construct to a mechanism.

    Returns paths like:
      Signal -> Construct -> Construct -> Mechanism

    Useful for understanding WHY a mechanism was selected — what
    psychological evidence chain connects a signal to the mechanism.
    """
    try:
        from adam.infrastructure.neo4j.pattern_persistence import (
            get_pattern_persistence,
        )

        persistence = get_pattern_persistence()
        chains = await persistence.get_inferential_chain(
            source_id=construct_id,
            target_mechanism=target_mechanism,
            max_depth=max_depth,
        )

        return InferentialChainResponse(
            source_id=construct_id,
            target_mechanism=target_mechanism,
            chains=chains,
            total_chains=len(chains),
        )

    except Exception as e:
        logger.exception(f"Error getting inferential chain: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/constructs/{construct_id}/neighborhood")
async def get_construct_neighborhood(
    construct_id: str,
    max_hops: int = Query(2, ge=1, le=4, description="Maximum hops to traverse"),
    limit: int = Query(20, ge=1, le=100, description="Maximum neighbors to return"),
) -> Dict[str, Any]:
    """
    Get all constructs within N hops of the given construct.

    Returns the construct's neighborhood — all connected constructs,
    their domains, and their distance from the source construct.
    """
    try:
        from adam.infrastructure.neo4j.pattern_persistence import (
            get_pattern_persistence,
        )

        persistence = get_pattern_persistence()
        neighbors = await persistence.get_construct_neighborhood(
            construct_id=construct_id,
            max_hops=max_hops,
            limit=limit,
        )

        return {
            "construct_id": construct_id,
            "max_hops": max_hops,
            "neighbors": neighbors,
            "total_neighbors": len(neighbors),
        }

    except Exception as e:
        logger.exception(f"Error getting construct neighborhood: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/constructs/{construct_id}/creative-implications")
async def get_creative_implications(construct_id: str) -> Dict[str, Any]:
    """
    Get creative implications for a construct.

    Returns style, color, imagery, frame, and CTA guidance derived from
    the construct's own properties and its connected edges.
    """
    try:
        from adam.infrastructure.neo4j.pattern_persistence import (
            get_pattern_persistence,
        )

        persistence = get_pattern_persistence()
        implications = await persistence.get_construct_creative_implications(
            construct_id=construct_id,
        )

        return {
            "construct_id": construct_id,
            "creative_implications": implications,
        }

    except Exception as e:
        logger.exception(f"Error getting creative implications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def intelligence_health() -> Dict[str, Any]:
    """
    Check health of intelligence components.
    """
    health = {
        "status": "healthy",
        "components": {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    # Check each component
    try:
        from adam.intelligence.brand_copy_intelligence import get_brand_copy_analyzer
        get_brand_copy_analyzer()
        health["components"]["brand_copy_analyzer"] = "ok"
    except Exception as e:
        health["components"]["brand_copy_analyzer"] = f"error: {e}"
        health["status"] = "degraded"
    
    try:
        from adam.intelligence.journey_intelligence import get_journey_intelligence_service
        get_journey_intelligence_service()
        health["components"]["journey_intelligence"] = "ok"
    except Exception as e:
        health["components"]["journey_intelligence"] = f"error: {e}"
        health["status"] = "degraded"
    
    try:
        from adam.intelligence.helpful_vote_intelligence import get_helpful_vote_intelligence
        get_helpful_vote_intelligence()
        health["components"]["helpful_vote_intelligence"] = "ok"
    except Exception as e:
        health["components"]["helpful_vote_intelligence"] = f"error: {e}"
        health["status"] = "degraded"
    
    try:
        from adam.intelligence.atom_intelligence_injector import get_intelligence_injector
        get_intelligence_injector()
        health["components"]["atom_intelligence_injector"] = "ok"
    except Exception as e:
        health["components"]["atom_intelligence_injector"] = f"error: {e}"
        health["status"] = "degraded"
    
    try:
        from adam.infrastructure.neo4j.pattern_persistence import get_pattern_persistence
        persistence = get_pattern_persistence()
        health["components"]["pattern_persistence"] = "ok"
    except Exception as e:
        health["components"]["pattern_persistence"] = f"error: {e}"
        health["status"] = "degraded"
    
    return health
