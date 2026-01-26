# =============================================================================
# ADAM Behavioral Analytics: API Router
# Location: adam/behavioral_analytics/api/router.py
# =============================================================================

"""
BEHAVIORAL ANALYTICS API

FastAPI router providing endpoints for:
1. Event collection - Record individual analytics events
2. Session analysis - Process complete behavioral sessions
3. Knowledge queries - Get behavioral knowledge for constructs
4. Hypothesis status - View and manage hypothesis testing
5. Profile retrieval - Get behavioral profiles for users
6. Outcome recording - Record outcomes for learning
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
import logging

from adam.behavioral_analytics.models.events import (
    BehavioralSession,
    BehavioralOutcome,
    OutcomeType,
    TouchEvent,
    SwipeEvent,
    ScrollEvent,
    PageViewEvent,
    ClickEvent,
    DeviceType,
)
from adam.behavioral_analytics.models.knowledge import (
    BehavioralKnowledge,
    BehavioralHypothesis,
    HypothesisStatus,
    KnowledgeTier,
)
from adam.behavioral_analytics.engine import (
    get_behavioral_analytics_engine,
    PsychologicalInference,
)
from adam.behavioral_analytics.knowledge.research_seeder import (
    get_research_knowledge_seeder,
)
from adam.behavioral_analytics.knowledge.hypothesis_engine import (
    get_hypothesis_engine,
)
from adam.behavioral_analytics.extensions.drift_extension import (
    get_behavioral_drift_detector,
)
from adam.behavioral_analytics.atom_interface import (
    get_atom_knowledge_interface,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/behavioral", tags=["behavioral_analytics"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class EventRequest(BaseModel):
    """Request to record a single analytics event."""
    
    session_id: str
    user_id: Optional[str] = None
    device_id: str
    event_type: str
    timestamp: Optional[datetime] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class SessionRequest(BaseModel):
    """Request to analyze a complete session."""
    
    session_id: str
    user_id: Optional[str] = None
    device_id: str
    device_type: str = "mobile"
    
    # Events
    page_views: List[Dict[str, Any]] = Field(default_factory=list)
    clicks: List[Dict[str, Any]] = Field(default_factory=list)
    touches: List[Dict[str, Any]] = Field(default_factory=list)
    swipes: List[Dict[str, Any]] = Field(default_factory=list)
    scrolls: List[Dict[str, Any]] = Field(default_factory=list)
    sensor_samples: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Session metadata
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_ms: int = 0


class OutcomeRequest(BaseModel):
    """Request to record an outcome for learning."""
    
    session_id: str
    user_id: Optional[str] = None
    decision_id: Optional[str] = None
    outcome_type: str
    outcome_value: float
    outcome_label: str = ""
    context: Dict[str, Any] = Field(default_factory=dict)


class SessionAnalysisResponse(BaseModel):
    """Response from session analysis."""
    
    session_id: str
    user_id: Optional[str]
    is_known_user: bool
    processing_timestamp: str
    
    # Features
    feature_count: int
    features: Dict[str, float]
    
    # Signals
    signal_count: int
    signals: List[Dict[str, Any]]
    
    # Inference
    inference: Dict[str, Any]
    
    # Hypotheses
    hypotheses_generated: List[str] = Field(default_factory=list)


class KnowledgeResponse(BaseModel):
    """Response with behavioral knowledge."""
    
    target_construct: str
    knowledge_items: List[Dict[str, Any]]
    total_count: int
    tier_filter: Optional[int] = None


class InferenceResponse(BaseModel):
    """Response with psychological inference."""
    
    session_id: str
    user_id: Optional[str]
    
    # Core inferences
    emotional_arousal: float
    emotional_valence: float
    decision_confidence: float
    cognitive_load: float
    purchase_intent: float
    frustration_level: float
    
    # Processing mode
    processing_mode: str
    
    # Regulatory focus
    promotion_focus_score: float
    prevention_focus_score: float
    
    # Confidence
    inference_confidence: float
    signals_used: int
    knowledge_applied: List[str]


class HealthResponse(BaseModel):
    """Health status response."""
    
    status: str
    research_knowledge_count: int
    drift_health: Dict[str, Any]
    hypothesis_count: int


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/event", summary="Record a single analytics event")
async def record_event(request: EventRequest) -> Dict[str, Any]:
    """
    Record a single analytics event.
    
    Events are accumulated into sessions for analysis.
    Real-time alerts may be triggered for frustration signals.
    """
    # For now, just acknowledge - session batching would be in production
    return {
        "status": "recorded",
        "session_id": request.session_id,
        "event_type": request.event_type,
        "timestamp": (request.timestamp or datetime.now(timezone.utc)).isoformat(),
    }


@router.post("/session", response_model=SessionAnalysisResponse, summary="Analyze complete session")
async def analyze_session(request: SessionRequest) -> SessionAnalysisResponse:
    """
    Analyze a complete behavioral session.
    
    Extracts features, infers psychological states, and
    generates hypotheses for testing.
    """
    engine = get_behavioral_analytics_engine()
    
    # Build session from request
    session = BehavioralSession(
        session_id=request.session_id,
        user_id=request.user_id,
        device_id=request.device_id,
        device_type=DeviceType(request.device_type),
        start_time=request.start_time or datetime.now(timezone.utc),
        end_time=request.end_time,
        duration_ms=request.duration_ms,
    )
    
    # Convert event dicts to models (simplified)
    for pv in request.page_views:
        session.page_views.append(PageViewEvent(**pv))
    
    for click in request.clicks:
        session.clicks.append(ClickEvent(**click))
    
    for touch in request.touches:
        session.touches.append(TouchEvent(**touch))
    
    for swipe in request.swipes:
        session.swipes.append(SwipeEvent(**swipe))
    
    for scroll in request.scrolls:
        session.scrolls.append(ScrollEvent(**scroll))
    
    # Process session
    result = await engine.process_session(session)
    
    return SessionAnalysisResponse(**result)


@router.post("/outcome", summary="Record outcome for learning")
async def record_outcome(request: OutcomeRequest) -> Dict[str, Any]:
    """
    Record an outcome for learning.
    
    Updates hypotheses and validates knowledge based on
    observed outcomes.
    """
    engine = get_behavioral_analytics_engine()
    
    outcome = BehavioralOutcome(
        session_id=request.session_id,
        user_id=request.user_id,
        decision_id=request.decision_id,
        outcome_type=OutcomeType(request.outcome_type),
        outcome_value=request.outcome_value,
        outcome_label=request.outcome_label,
        context=request.context,
    )
    
    result = await engine.record_outcome(outcome)
    
    return result


@router.get("/knowledge/{construct}", response_model=KnowledgeResponse, summary="Get knowledge for construct")
async def get_knowledge_for_construct(
    construct: str,
    tier: Optional[int] = Query(None, ge=1, le=3, description="Filter by tier (1-3)"),
) -> KnowledgeResponse:
    """
    Get all behavioral knowledge for a psychological construct.
    
    Constructs include:
    - emotional_arousal
    - decision_confidence
    - purchase_intent
    - cognitive_load
    - frustration
    - promotion_focus
    - prevention_focus
    """
    interface = get_atom_knowledge_interface()
    
    tier_enum = KnowledgeTier(tier) if tier else None
    knowledge = await interface.get_knowledge_for_construct(construct, tier_enum)
    
    return KnowledgeResponse(
        target_construct=construct,
        knowledge_items=knowledge,
        total_count=len(knowledge),
        tier_filter=tier,
    )


@router.get("/knowledge", summary="Get all research knowledge")
async def get_all_knowledge(
    tier: Optional[int] = Query(None, ge=1, le=3, description="Filter by tier"),
) -> Dict[str, Any]:
    """
    Get all research-validated behavioral knowledge.
    """
    seeder = get_research_knowledge_seeder()
    all_knowledge = seeder.seed_all_knowledge()
    
    if tier:
        tier_enum = KnowledgeTier(tier)
        all_knowledge = [k for k in all_knowledge if k.tier == tier_enum]
    
    # Group by construct
    by_construct: Dict[str, List] = {}
    for k in all_knowledge:
        construct = k.maps_to_construct
        if construct not in by_construct:
            by_construct[construct] = []
        by_construct[construct].append({
            "knowledge_id": k.knowledge_id,
            "signal_name": k.signal_name,
            "effect_size": k.effect_size,
            "effect_type": k.effect_type.value,
            "tier": k.tier.value,
        })
    
    return {
        "total_count": len(all_knowledge),
        "tier_filter": tier,
        "by_construct": by_construct,
    }


@router.get("/hypotheses", summary="Get active hypotheses")
async def get_hypotheses(
    status: Optional[str] = Query(None, description="Filter by status"),
) -> Dict[str, Any]:
    """
    Get behavioral hypotheses and their testing status.
    """
    hypothesis_engine = get_hypothesis_engine()
    
    if status:
        status_enum = HypothesisStatus(status)
        hypotheses = hypothesis_engine.get_hypotheses_by_status(status_enum)
    else:
        hypotheses = list(hypothesis_engine._hypotheses.values())
    
    return {
        "total_count": len(hypotheses),
        "status_filter": status,
        "hypotheses": [
            {
                "hypothesis_id": h.hypothesis_id,
                "status": h.status.value,
                "signal_pattern": h.signal_pattern,
                "predicted_outcome": h.predicted_outcome,
                "predicted_direction": h.predicted_direction,
                "observations": h.observations,
                "observed_effect_size": h.observed_effect_size,
                "p_value": h.p_value,
                "is_promotable": h.is_promotable,
            }
            for h in hypotheses
        ],
    }


@router.get("/hypotheses/promotable", summary="Get promotable hypotheses")
async def get_promotable_hypotheses() -> Dict[str, Any]:
    """
    Get hypotheses ready for promotion to knowledge.
    """
    hypothesis_engine = get_hypothesis_engine()
    promotable = hypothesis_engine.get_promotable_hypotheses()
    
    return {
        "count": len(promotable),
        "hypotheses": [
            {
                "hypothesis_id": h.hypothesis_id,
                "signal_pattern": h.signal_pattern,
                "predicted_outcome": h.predicted_outcome,
                "observations": h.observations,
                "observed_effect_size": h.observed_effect_size,
                "p_value": h.p_value,
            }
            for h in promotable
        ],
    }


@router.post("/hypotheses/{hypothesis_id}/promote", summary="Promote hypothesis to knowledge")
async def promote_hypothesis(hypothesis_id: str) -> Dict[str, Any]:
    """
    Promote a validated hypothesis to system knowledge.
    """
    hypothesis_engine = get_hypothesis_engine()
    
    hypothesis = hypothesis_engine.get_hypothesis(hypothesis_id)
    if not hypothesis:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    
    if hypothesis.status != HypothesisStatus.VALIDATED:
        raise HTTPException(
            status_code=400,
            detail=f"Hypothesis status is {hypothesis.status.value}, must be validated"
        )
    
    knowledge = await hypothesis_engine.promote_hypothesis(hypothesis_id)
    
    if not knowledge:
        raise HTTPException(status_code=500, detail="Failed to promote hypothesis")
    
    return {
        "status": "promoted",
        "hypothesis_id": hypothesis_id,
        "knowledge_id": knowledge.knowledge_id,
        "signal_name": knowledge.signal_name,
        "maps_to_construct": knowledge.maps_to_construct,
        "effect_size": knowledge.effect_size,
    }


@router.get("/profiles/{user_id}", summary="Get behavioral profile")
async def get_behavioral_profile(
    user_id: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get behavioral profile for a user.
    
    Combines historical knowledge with current session inference.
    """
    interface = get_atom_knowledge_interface()
    
    if session_id:
        context = await interface.get_behavioral_context(
            session_id=session_id,
            user_id=user_id,
        )
        
        return {
            "user_id": user_id,
            "session_id": session_id,
            "has_implicit_signals": context.has_implicit_signals,
            "current_state": {
                "emotional_arousal": context.emotional_arousal,
                "decision_confidence": context.decision_confidence,
                "cognitive_load": context.cognitive_load,
                "purchase_intent": context.purchase_intent,
                "processing_mode": context.processing_mode,
            },
            "regulatory_focus_hints": context.get_regulatory_focus_hints(),
            "construal_level_hints": context.get_construal_level_hints(),
            "arousal_alignment": context.get_arousal_alignment_hints(),
        }
    else:
        # No session - return placeholder
        return {
            "user_id": user_id,
            "session_id": None,
            "has_implicit_signals": False,
            "message": "Provide session_id for real-time behavioral context",
        }


@router.get("/drift", summary="Get behavioral drift status")
async def get_drift_status() -> Dict[str, Any]:
    """
    Get current behavioral signal drift status.
    """
    detector = get_behavioral_drift_detector()
    return detector.get_behavioral_health()


@router.get("/health", response_model=HealthResponse, summary="Get service health")
async def get_health() -> HealthResponse:
    """
    Get behavioral analytics service health.
    """
    engine = get_behavioral_analytics_engine()
    health = engine.get_health()
    
    return HealthResponse(**health)


# =============================================================================
# WEBSOCKET FOR REAL-TIME SIGNALS
# =============================================================================

# WebSocket endpoint would be added here for real-time streaming
# from fastapi import WebSocket, WebSocketDisconnect
# 
# @router.websocket("/realtime/{session_id}")
# async def realtime_signals(websocket: WebSocket, session_id: str):
#     """Real-time behavioral signal streaming."""
#     await websocket.accept()
#     try:
#         while True:
#             data = await websocket.receive_json()
#             # Process and respond with real-time inferences
#     except WebSocketDisconnect:
#         pass
