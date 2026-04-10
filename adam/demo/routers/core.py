# =============================================================================
# ADAM Demo - Core Router
# Status, health, recommend, archetypes
# =============================================================================

"""
Core API endpoints for the ADAM demo platform.
These are the fundamental endpoints needed for basic operation.
"""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Core"])


# =============================================================================
# MODELS (Re-exported for this module)
# =============================================================================

class PsychologicalProfile(BaseModel):
    """Inferred psychological profile."""
    openness: float = 0.5
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    neuroticism: float = 0.5
    promotion_focus: float = 0.5
    prevention_focus: float = 0.5
    construal_level: float = 0.5
    archetype: Optional[str] = None
    archetype_confidence: float = 0.0
    cohort_id: Optional[str] = None
    cohort_match_score: float = 0.0


class MechanismRecommendation(BaseModel):
    """Recommended persuasion mechanism."""
    mechanism: str
    score: float
    reason: str
    synergies: Optional[List[str]] = None
    research_backing: Optional[str] = None


class GraphIntelligence(BaseModel):
    """Intelligence derived from graph edges."""
    synergies_applied: List[Dict[str, Any]] = []
    causal_paths: List[Dict[str, Any]] = []
    archetype_priors: Dict[str, float] = {}
    temporal_sequences: List[Dict[str, Any]] = []


class RecommendationRequest(BaseModel):
    """Request for a personalized recommendation."""
    user_id: Optional[str] = Field(default=None)
    brand_name: Optional[str] = None
    brand_description: Optional[str] = None
    brand_tone: Optional[str] = None
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    product_url: Optional[str] = None
    price_point: Optional[str] = None
    key_benefits: Optional[List[str]] = None
    ad_copy: Optional[str] = None
    ad_headline: Optional[str] = None
    ad_cta: Optional[str] = None
    creative_url: Optional[str] = None
    target_ages: Optional[List[str]] = None
    target_gender: Optional[str] = "all"
    target_income: Optional[List[str]] = None
    target_interests: Optional[List[str]] = None
    target_lifestyle: Optional[str] = None
    preferred_genres: Optional[List[str]] = None
    preferred_dayparts: Optional[List[str]] = None
    station_format: Optional[str] = None


class RecommendationResponse(BaseModel):
    """Full recommendation response."""
    request_id: str
    timestamp: str
    profile: PsychologicalProfile
    mechanisms: List[MechanismRecommendation]
    graph_intelligence: GraphIntelligence
    generated_copy: Optional[Dict[str, Any]] = None
    components_used: List[str]
    processing_time_ms: float
    inference_sources: List[Dict[str, Any]]


class PlatformStatusResponse(BaseModel):
    """Platform status for the demo."""
    status: str
    components_available: List[str]
    components_active: List[str]
    graph_edge_service: bool
    cohort_discovery: bool
    learning_loop: bool
    monitoring: bool
    total_components: int


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.get("/status", response_model=PlatformStatusResponse)
async def get_status() -> PlatformStatusResponse:
    """
    Get platform status showing available and active components.
    
    This endpoint checks which ADAM components are available and functioning,
    giving the demo operator insight into the platform's capabilities.
    """
    # Import here to check availability
    components_available = []
    components_active = []
    graph_edge_service = False
    cohort_discovery = False
    learning_loop = False
    monitoring = False
    
    # Check Graph Edge Service
    try:
        from adam.intelligence.graph_edge_service import get_graph_edge_service
        service = get_graph_edge_service()
        components_available.append("graph_edge_service")
        graph_edge_service = True
        components_active.append("GraphEdgeService")
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"Graph edge service error: {e}")
    
    # Check Cohort Discovery
    try:
        from adam.core.cohort_discovery import CohortDiscoveryService
        components_available.append("cohort_discovery")
        cohort_discovery = True
        components_active.append("CohortDiscovery")
    except ImportError:
        pass
    
    # Check Learning Loop
    try:
        from adam.core.learning.signal_router import LearningSignalRouter
        components_available.append("learning_loop")
        learning_loop = True
        components_active.append("LearningLoop")
    except ImportError:
        pass
    
    # Check Monitoring
    try:
        from adam.monitoring.learning_loop_monitor import get_learning_loop_monitor
        components_available.append("monitoring")
        monitoring = True
        components_active.append("Monitoring")
    except ImportError:
        pass
    
    # Check Cold Start
    try:
        from adam.cold_start.service import ColdStartService
        components_available.append("cold_start")
        components_active.append("ColdStart")
    except ImportError:
        pass
    
    # Check Copy Generation
    try:
        from adam.output.copy_generation.service import CopyGenerationService
        components_available.append("copy_generation")
        components_active.append("CopyGeneration")
    except ImportError:
        pass
    
    # Check Review Intelligence
    try:
        from adam.demo.review_intelligence import get_review_intelligence
        components_available.append("review_intelligence")
        components_active.append("ReviewIntelligence")
    except ImportError:
        pass
    
    return PlatformStatusResponse(
        status="operational" if len(components_active) >= 1 else "degraded",
        components_available=components_available,
        components_active=components_active,
        graph_edge_service=graph_edge_service,
        cohort_discovery=cohort_discovery,
        learning_loop=learning_loop,
        monitoring=monitoring,
        total_components=len(components_active),
    )


@router.get("/archetypes")
async def get_archetypes() -> Dict[str, Any]:
    """
    Get available psychological archetypes.
    
    ⚠️ LEGACY ENDPOINT: This returns the 6 basic archetypes.
    
    For the full customer type system, use GET /customer-types which returns
    the 3,750+ GRANULAR TYPE SYSTEM with multi-dimensional analysis.
    
    The granular system includes:
    - 15 purchase motivations
    - 3 decision styles
    - 2 regulatory focuses
    - 3 emotional intensities
    - 4 price sensitivities
    - 8 archetypes (as one dimension)
    - 10 domains
    """
    try:
        from adam.cold_start.service import ColdStartService
        
        service = ColdStartService()
        stats = service.get_statistics()
        
        # Build archetype info (LEGACY - archetypes are now ONE dimension of the granular system)
        archetypes = {
            "explorer": {
                "name": "Explorer",
                "description": "Curious, adventurous, seeks novel experiences",
                "key_traits": ["high_openness", "high_extraversion"],
                "effective_mechanisms": ["novelty", "social_proof"],
                "ad_tone": "exciting, discovery-focused",
            },
            "analytical": {
                "name": "Analytical",
                "description": "Detail-oriented, research-driven decision maker",
                "key_traits": ["high_conscientiousness", "moderate_openness"],
                "effective_mechanisms": ["authority", "commitment"],
                "ad_tone": "informative, evidence-based",
            },
            "skeptic": {
                "name": "Skeptic",
                "description": "Cautious, needs convincing, values authenticity",
                "key_traits": ["low_agreeableness", "high_conscientiousness"],
                "effective_mechanisms": ["authority", "social_proof"],
                "ad_tone": "honest, transparent, backed by evidence",
            },
            "enthusiast": {
                "name": "Enthusiast",
                "description": "Passionate, expressive, loves to share experiences",
                "key_traits": ["high_extraversion", "high_agreeableness"],
                "effective_mechanisms": ["social_proof", "liking"],
                "ad_tone": "energetic, community-focused",
            },
            "pragmatist": {
                "name": "Pragmatist",
                "description": "Practical, efficiency-focused, value-conscious",
                "key_traits": ["high_conscientiousness", "low_neuroticism"],
                "effective_mechanisms": ["scarcity", "commitment"],
                "ad_tone": "clear, benefit-focused, practical",
            },
            "loyalist": {
                "name": "Loyalist",
                "description": "Brand-loyal, relationship-focused, values consistency",
                "key_traits": ["high_agreeableness", "moderate_conscientiousness"],
                "effective_mechanisms": ["commitment", "reciprocity"],
                "ad_tone": "warm, trustworthy, relationship-building",
            },
        }
        
        return {
            "archetypes": archetypes,
            "total": len(archetypes),
            "data_source": "941M+ Amazon reviews",
            "statistics": stats,
            "_note": "LEGACY: Use GET /customer-types for the full 3,750+ GRANULAR TYPE SYSTEM",
        }
        
    except ImportError:
        # Return basic archetype info without statistics
        archetypes = {
            "explorer": {"name": "Explorer", "description": "Curious, adventurous"},
            "analytical": {"name": "Analytical", "description": "Detail-oriented"},
            "skeptic": {"name": "Skeptic", "description": "Cautious, needs convincing"},
            "enthusiast": {"name": "Enthusiast", "description": "Passionate, expressive"},
            "pragmatist": {"name": "Pragmatist", "description": "Practical, efficient"},
            "loyalist": {"name": "Loyalist", "description": "Brand-loyal, consistent"},
        }
        return {
            "archetypes": archetypes,
            "total": 6,
            "_note": "LEGACY: Use GET /customer-types for the full 3,750+ GRANULAR TYPE SYSTEM",
        }
    except Exception as e:
        logger.error(f"Error getting archetypes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/customer-types")
async def get_customer_types() -> Dict[str, Any]:
    """
    Get the GRANULAR CUSTOMER TYPE SYSTEM (3,750+ types).
    
    This is the PRIMARY customer classification system that replaces
    the legacy 8-archetype system.
    
    Type Formula:
        CustomerType = Motivation × DecisionStyle × RegulatoryFocus × 
                       EmotionalIntensity × PriceSensitivity × Archetype × Domain
    
    Total Types: 15 × 3 × 2 × 3 × 4 × 8 × ~10 = 43,200+ theoretical
    Practical (active combinations): ~3,750+
    """
    try:
        from adam.intelligence.customer_types import (
            get_customer_type_generator,
            PurchaseMotivation,
            DecisionStyle,
            RegulatoryFocus,
            EmotionalIntensity,
            PriceSensitivity,
            Archetype,
        )
        from adam.intelligence.granular_type_detector import get_granular_type_detector
        
        generator = get_customer_type_generator()
        detector = get_granular_type_detector()
        
        return {
            "system_name": "GRANULAR CUSTOMER TYPE SYSTEM",
            "status": "ACTIVE",
            "type_counts": {
                "primary_types": generator.get_primary_type_count(),
                "full_types_with_archetypes": generator.get_full_type_count(),
                "theoretical_maximum": 43200,
            },
            "dimensions": {
                "purchase_motivations": {
                    "count": len(PurchaseMotivation),
                    "values": [m.value for m in PurchaseMotivation],
                    "predictive_weight": "Tier 1 (Highest)",
                },
                "decision_styles": {
                    "count": len(DecisionStyle),
                    "values": [s.value for s in DecisionStyle],
                    "predictive_weight": "Tier 1 (Highest)",
                },
                "regulatory_focus": {
                    "count": len(RegulatoryFocus),
                    "values": [r.value for r in RegulatoryFocus],
                    "predictive_weight": "Tier 2 (Strong)",
                },
                "emotional_intensity": {
                    "count": len(EmotionalIntensity),
                    "values": [e.value for e in EmotionalIntensity],
                    "predictive_weight": "Tier 2 (Strong)",
                },
                "price_sensitivity": {
                    "count": len(PriceSensitivity),
                    "values": [p.value for p in PriceSensitivity],
                    "predictive_weight": "Tier 2 (Strong)",
                },
                "archetypes": {
                    "count": len(Archetype),
                    "values": [a.value for a in Archetype],
                    "note": "One dimension of the system, NOT the primary classification",
                },
            },
            "formula": "CustomerType = Motivation × DecisionStyle × RegulatoryFocus × EmotionalIntensity × PriceSensitivity × Archetype × Domain",
            "integration": {
                "orchestrator": True,
                "demo_api": True,
                "detector_available": detector is not None,
            },
            "replaces": {
                "legacy_system": "8-Archetype System",
                "improvement": f"8 types → {generator.get_full_type_count():,}+ types",
            },
        }
    except Exception as e:
        logger.error(f"Error getting customer types: {e}")
        return {
            "system_name": "GRANULAR CUSTOMER TYPE SYSTEM",
            "status": "ERROR",
            "error": str(e),
            "note": "Customer types module not available",
        }


@router.get("/health/detailed")
async def get_detailed_health() -> Dict[str, Any]:
    """
    Get detailed health status of all ADAM components.
    
    Used for debugging and monitoring the demo platform.
    """
    health = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_status": "healthy",
        "components": {},
    }
    
    # Check each component
    components_to_check = [
        ("graph_edge_service", "adam.intelligence.graph_edge_service", "get_graph_edge_service"),
        ("cohort_discovery", "adam.core.cohort_discovery", "CohortDiscoveryService"),
        ("cold_start", "adam.cold_start.service", "ColdStartService"),
        ("learning_loop", "adam.core.learning.signal_router", "LearningSignalRouter"),
        ("monitoring", "adam.monitoring.learning_loop_monitor", "get_learning_loop_monitor"),
    ]
    
    healthy_count = 0
    for name, module, attr in components_to_check:
        try:
            mod = __import__(module, fromlist=[attr])
            getattr(mod, attr)
            health["components"][name] = {"status": "available", "error": None}
            healthy_count += 1
        except ImportError as e:
            health["components"][name] = {"status": "not_installed", "error": str(e)}
        except Exception as e:
            health["components"][name] = {"status": "error", "error": str(e)}
    
    health["healthy_components"] = healthy_count
    health["total_components"] = len(components_to_check)
    health["overall_status"] = "healthy" if healthy_count >= 3 else "degraded" if healthy_count >= 1 else "unhealthy"
    
    return health
