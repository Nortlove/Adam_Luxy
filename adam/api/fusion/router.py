# =============================================================================
# Corpus Fusion Intelligence API Router
# Location: adam/api/fusion/router.py
# =============================================================================

"""
FUSION API

FastAPI router exposing the 5-layer Corpus Fusion Intelligence system.
Provides access to:
  - Empirical priors from 1B+ verified purchase reviews (Layer 1)
  - Proven creative pattern constraints (Layer 2)
  - Platform-specific calibration factors (Layer 3)
  - Bidirectional learning loop statistics (Layer 4)
  - Helpful-vote-validated resonance templates (Layer 5)
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/fusion", tags=["corpus-fusion"])


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class PriorResponse(BaseModel):
    """Corpus-derived mechanism priors for a given context."""
    category: str = ""
    archetype: Optional[str] = None
    mechanism_priors: Dict[str, float] = Field(default_factory=dict)
    confidence: float = 0.0
    evidence_count: int = 0
    transfer_sources: List[str] = Field(default_factory=list)
    source: str = "corpus_fusion"
    # Product-level enrichment (when ASIN is provided)
    product_asin: Optional[str] = None
    product_mechanism_priors: Optional[Dict[str, float]] = None
    product_ad_profile: Optional[Dict[str, str]] = None
    product_archetype_affinities: Optional[Dict[str, float]] = None
    product_intelligence_source: Optional[str] = None


class ProductIntelligenceResponse(BaseModel):
    """Full product-level intelligence for a specific ASIN."""
    asin: str
    category: str = ""
    ad_profile: Optional[Dict[str, str]] = None
    archetype_profile: Optional[Dict[str, float]] = None
    dominant_archetype: Optional[str] = None
    product_mechanism_priors: Dict[str, float] = Field(default_factory=dict)
    product_confidence: float = 0.0
    similar_products: List[Dict[str, Any]] = Field(default_factory=list)
    source: str = "product_intelligence"


class CreativeConstraintResponse(BaseModel):
    """Proven creative pattern constraints from corpus analysis."""
    category: str = ""
    archetype: Optional[str] = None
    patterns: List[Dict[str, Any]] = Field(default_factory=list)
    top_tactics: List[str] = Field(default_factory=list)
    recommended_frame: Optional[str] = None
    source: str = "corpus_fusion"


class CalibrationResponse(BaseModel):
    """Platform-specific calibration factors."""
    platform: str
    factors: Dict[str, float] = Field(default_factory=dict)
    convergence: float = 0.0
    update_count: int = 0
    all_platforms: List[str] = Field(default_factory=list)


class ResonanceTemplateResponse(BaseModel):
    """Helpful-vote-validated persuasion template."""
    template_id: str
    technique: str
    pattern: str
    helpfulness_score: float = 0.0
    vote_count: int = 0
    source_category: str = ""


class FusionStatisticsResponse(BaseModel):
    """Aggregate statistics about the corpus fusion system."""
    prior_categories_loaded: int = 0
    total_evidence_count: int = 0
    platform_calibrations: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    resonance_templates_loaded: int = 0
    creative_patterns_loaded: int = 0
    product_profiles_loaded: int = 0
    bidirectional_outcomes_processed: int = 0
    system_status: str = "operational"


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/priors", response_model=PriorResponse)
async def get_priors(
    category: str = Query("", description="Product category (empty for cross-category)"),
    archetype: Optional[str] = Query(None, description="Consumer archetype"),
    asin: Optional[str] = Query(None, description="Specific ASIN for product-level resolution"),
):
    """
    Get corpus-derived mechanism priors for a category/archetype/product combination.
    
    Returns empirical Bayesian priors extracted from 1B+ verified purchase reviews.
    When an ASIN is provided, the response includes product-specific mechanism priors
    weighted by the product's actual archetype affinity distribution.
    """
    try:
        from adam.fusion.prior_extraction import get_prior_extraction_service
        service = get_prior_extraction_service()
        prior = service.extract_prior(
            category=category,
            archetype=archetype,
            asin=asin,
        )
        
        if not prior:
            return PriorResponse(category=category, archetype=archetype)
        
        return PriorResponse(
            category=prior.category,
            archetype=prior.archetype,
            mechanism_priors=prior.get_mechanism_dict(),
            confidence=prior.confidence,
            evidence_count=prior.total_evidence,
            transfer_sources=prior.transfer_sources,
            # Product-level enrichment
            product_asin=prior.product_asin,
            product_mechanism_priors=prior.product_mechanism_priors or None,
            product_ad_profile=prior.product_ad_profile,
            product_archetype_affinities=prior.product_archetype_affinities,
            product_intelligence_source=prior.product_intelligence_source,
        )
    except ImportError:
        raise HTTPException(status_code=503, detail="Prior extraction service unavailable")
    except Exception as e:
        logger.error(f"Failed to get priors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/creative-constraints", response_model=CreativeConstraintResponse)
async def get_creative_constraints(
    category: str = Query("", description="Product category"),
    archetype: Optional[str] = Query(None, description="Consumer archetype"),
):
    """
    Get proven creative pattern constraints from corpus analysis.
    
    Returns creative patterns that have been validated through
    helpful-vote analysis and review text mining.
    """
    try:
        from adam.fusion.creative_patterns import get_creative_pattern_extractor
        extractor = get_creative_pattern_extractor()
        constraints = extractor.extract_creative_constraints(
            category=category,
            target_archetype=archetype,
        )
        
        patterns = []
        if constraints and constraints.patterns:
            patterns = [
                {
                    "pattern_type": p.pattern_type if hasattr(p, "pattern_type") else "unknown",
                    "mechanism": p.mechanism if hasattr(p, "mechanism") else "",
                    "effectiveness": p.weighted_effectiveness if hasattr(p, "weighted_effectiveness") else 0.0,
                    "evidence_count": p.evidence_count if hasattr(p, "evidence_count") else 0,
                }
                for p in constraints.patterns
            ]
        
        top_tactics = constraints.recommended_mechanisms if constraints else []
        frame = None
        if constraints and constraints.recommended_framing:
            frame = constraints.recommended_framing.value if hasattr(constraints.recommended_framing, "value") else str(constraints.recommended_framing)
        
        return CreativeConstraintResponse(
            category=category,
            archetype=archetype,
            patterns=patterns,
            top_tactics=top_tactics,
            recommended_frame=frame,
        )
    except ImportError:
        raise HTTPException(status_code=503, detail="Creative pattern extractor unavailable")
    except Exception as e:
        logger.error(f"Failed to get creative constraints: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/calibration", response_model=CalibrationResponse)
async def get_calibration(
    platform: str = Query("default", description="Platform name (e.g., stackadapt, audioboom)"),
):
    """
    Get platform-specific calibration factors.
    
    These factors adjust mechanism effectiveness based on observed
    platform-specific performance differences.
    """
    try:
        from adam.fusion.platform_calibration import get_platform_calibration_layer
        layer = get_platform_calibration_layer()
        
        all_platforms = list(layer._calibrations.keys()) if hasattr(layer, "_calibrations") else []
        
        # Get all mechanism calibrations for this platform across categories
        factors = layer.get_all_calibrations(platform=platform, category="")
        
        convergence_info = layer.get_convergence_status()
        platform_convergence = convergence_info.get("platforms", {}).get(platform, {})
        
        return CalibrationResponse(
            platform=platform,
            factors={mech: factor for mech, (factor, _conf) in factors.items()} if factors else {},
            convergence=platform_convergence.get("convergence", 0.0),
            update_count=platform_convergence.get("update_count", 0),
            all_platforms=all_platforms,
        )
    except ImportError:
        raise HTTPException(status_code=503, detail="Platform calibration layer unavailable")
    except Exception as e:
        logger.error(f"Failed to get calibration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resonance-templates", response_model=List[ResonanceTemplateResponse])
async def get_resonance_templates(
    technique: Optional[str] = Query(None, description="Filter by persuasion technique"),
    limit: int = Query(20, ge=1, le=100, description="Max templates to return"),
):
    """
    Get helpful-vote-validated persuasion resonance templates.
    
    These templates represent persuasive patterns that real customers
    found genuinely helpful, validated through Amazon helpful-vote data.
    """
    try:
        from adam.fusion.resonance_index import get_persuasion_resonance_index
        index = get_persuasion_resonance_index()
        
        templates = index.get_resonance_templates(
            category="",  # All categories
            mechanism=technique,
            top_k=limit,
        )
        
        return [
            ResonanceTemplateResponse(
                template_id=t.template_id,
                technique=t.mechanism,
                pattern=t.pattern,
                helpfulness_score=t.resonance_score if hasattr(t, "resonance_score") else t.normalized_vote_score,
                vote_count=t.helpful_votes,
                source_category=t.category,
            )
            for t in templates
        ]
    except ImportError:
        raise HTTPException(status_code=503, detail="Resonance index unavailable")
    except Exception as e:
        logger.error(f"Failed to get resonance templates: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=FusionStatisticsResponse)
async def get_statistics():
    """
    Get aggregate statistics about the corpus fusion intelligence system.
    
    Provides a dashboard-level overview of all 5 fusion layers:
    how many categories, calibrations, templates, and outcomes are loaded.
    """
    stats = FusionStatisticsResponse()
    
    try:
        from adam.fusion.prior_extraction import get_prior_extraction_service
        service = get_prior_extraction_service()
        if hasattr(service, "_priors_data") and service._priors_data:
            stats.prior_categories_loaded = len(service._priors_data)
            stats.total_evidence_count = sum(
                cat_data.get("total_reviews", 0)
                for cat_data in service._priors_data.values()
                if isinstance(cat_data, dict)
            )
    except (ImportError, Exception):
        pass
    
    try:
        from adam.fusion.creative_patterns import get_creative_pattern_extractor
        extractor = get_creative_pattern_extractor()
        if hasattr(extractor, "_patterns"):
            stats.creative_patterns_loaded = len(extractor._patterns)
    except (ImportError, Exception):
        pass
    
    try:
        from adam.fusion.platform_calibration import get_platform_calibration_layer
        layer = get_platform_calibration_layer()
        if hasattr(layer, "_calibrations"):
            for platform, cal in layer._calibrations.items():
                stats.platform_calibrations[platform] = {
                    "convergence": cal.convergence if hasattr(cal, "convergence") else 0.0,
                    "update_count": cal.update_count if hasattr(cal, "update_count") else 0,
                }
    except (ImportError, Exception):
        pass
    
    try:
        from adam.fusion.resonance_index import get_persuasion_resonance_index
        index = get_persuasion_resonance_index()
        if hasattr(index, "_templates"):
            stats.resonance_templates_loaded = len(index._templates)
    except (ImportError, Exception):
        pass
    
    try:
        from adam.fusion.bidirectional_learning import get_bidirectional_learning_loop
        loop = get_bidirectional_learning_loop()
        if hasattr(loop, "_outcomes_processed"):
            stats.bidirectional_outcomes_processed = loop._outcomes_processed
    except (ImportError, Exception):
        pass
    
    # Product intelligence stats
    try:
        from adam.fusion.product_intelligence import get_product_intelligence_service
        prod_svc = get_product_intelligence_service()
        prod_stats = prod_svc.get_stats()
        stats.product_profiles_loaded = prod_stats.get("total_ad_profiles", 0)
    except (ImportError, Exception):
        pass
    
    stats.system_status = "operational"
    return stats


@router.get("/product-intelligence/{asin}", response_model=ProductIntelligenceResponse)
async def get_product_intelligence(asin: str):
    """
    Get full product-level intelligence for a specific ASIN.
    
    Returns the product's psychological advertising profile, archetype
    affinities, product-weighted mechanism priors, and similar products.
    This is the most granular level of intelligence in the system.
    """
    try:
        from adam.fusion.product_intelligence import get_product_intelligence_service
        service = get_product_intelligence_service()
        intel = service.get_product_intelligence(asin)
        
        if not intel:
            raise HTTPException(
                status_code=404,
                detail=f"No product intelligence found for ASIN {asin}"
            )
        
        # Get similar products for context
        similar = service.find_similar_products(asin=asin, top_k=5)
        
        return ProductIntelligenceResponse(
            asin=asin,
            category=intel.category,
            ad_profile=intel.ad_profile.model_dump() if intel.ad_profile else None,
            archetype_profile=intel.archetype_profile.archetype_scores if intel.archetype_profile else None,
            dominant_archetype=intel.archetype_profile.dominant_archetype if intel.archetype_profile else None,
            product_mechanism_priors=intel.product_mechanism_priors,
            product_confidence=intel.product_confidence,
            similar_products=similar,
        )
    except HTTPException:
        raise
    except ImportError:
        raise HTTPException(status_code=503, detail="Product intelligence service unavailable")
    except Exception as e:
        logger.error(f"Failed to get product intelligence for {asin}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/product-intelligence/{asin}/similar", response_model=List[Dict[str, Any]])
async def get_similar_products(
    asin: str,
    category: Optional[str] = Query(None, description="Filter by category"),
    top_k: int = Query(5, ge=1, le=20, description="Max results"),
):
    """
    Find products with similar psychological profiles (zero-shot transfer).
    
    When a new product has no data, this endpoint finds similar products
    whose priors can be transferred.
    """
    try:
        from adam.fusion.product_intelligence import get_product_intelligence_service
        service = get_product_intelligence_service()
        similar = service.find_similar_products(
            asin=asin,
            category=category,
            top_k=top_k,
        )
        return similar
    except ImportError:
        raise HTTPException(status_code=503, detail="Product intelligence service unavailable")
    except Exception as e:
        logger.error(f"Failed to find similar products for {asin}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
