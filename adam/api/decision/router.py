# =============================================================================
# ADAM Decision API Router
# Location: adam/api/decision/router.py
# =============================================================================

"""
DECISION API

FastAPI router for the main decision endpoint.
This is the primary interface for requesting ad decisions from ADAM.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from adam.core.container import get_container, ADAMContainer
from adam.blackboard.models.zone1_context import RequestContext, AdCandidate
from adam.meta_learner.models import RoutingDecision
from adam.verification.models.results import VerificationStatus

# V3 Cognitive Layer imports
from src.v3.narrative.session import get_narrative_session_engine
from src.v3.metacognitive.reasoning import get_metacognitive_engine, ReasoningStrategy
from src.v3.interactions.mechanism import get_mechanism_interaction_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/decisions", tags=["decisions"])


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class AdCandidateRequest(BaseModel):
    """Ad candidate in request."""
    
    ad_id: str
    campaign_id: str
    creative_id: str = ""
    brand_id: str = ""
    category_id: str = ""
    mechanism_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionContextRequest(BaseModel):
    """Session context in request."""
    
    session_id: str = ""
    session_depth: int = Field(default=0, ge=0)
    device_type: str = "unknown"
    platform: str = "unknown"
    hour_of_day: int = Field(default=12, ge=0, le=23)
    day_of_week: int = Field(default=0, ge=0, le=6)


class DecisionRequest(BaseModel):
    """Request for an ad decision."""
    
    request_id: str = Field(
        default_factory=lambda: f"req_{uuid4().hex[:12]}"
    )
    user_id: str
    
    # Ad candidates to choose from
    ad_candidates: List[AdCandidateRequest]
    
    # Context
    category_id: Optional[str] = None
    brand_id: Optional[str] = None
    session_context: SessionContextRequest = Field(
        default_factory=SessionContextRequest
    )
    
    # Options
    include_reasoning: bool = Field(default=False)
    timeout_ms: int = Field(default=2000, ge=100, le=10000)


class MechanismApplication(BaseModel):
    """How a mechanism was applied."""
    
    mechanism_id: str
    intensity: float = Field(ge=0.0, le=1.0)
    rationale: str = ""


class DecisionResponse(BaseModel):
    """Response containing the decision."""
    
    decision_id: str
    request_id: str
    
    # Selected ad
    selected_ad_id: str
    selected_ad_rank: int = Field(default=1, ge=1)
    
    # Mechanisms applied
    mechanisms: List[MechanismApplication] = Field(default_factory=list)
    primary_mechanism: Optional[str] = None
    
    # Confidence
    decision_confidence: float = Field(ge=0.0, le=1.0)
    
    # Execution path taken
    execution_path: str = ""  # "fast", "reasoning", "exploration"
    modality_used: str = ""
    
    # Verification status
    verification_status: str = ""
    
    # Timing
    latency_ms: float = Field(ge=0.0)
    
    # Optional reasoning explanation
    reasoning: Optional[Dict[str, Any]] = None


class OutcomeRequest(BaseModel):
    """Request to record an outcome."""
    
    decision_id: str
    outcome_type: str  # "conversion", "click", "skip", "engagement"
    outcome_value: float = Field(ge=0.0, le=1.0)
    
    # Optional context
    revenue: Optional[float] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OutcomeResponse(BaseModel):
    """Response after recording an outcome."""
    
    decision_id: str
    outcome_recorded: bool
    signals_generated: int = Field(default=0, ge=0)


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/", response_model=DecisionResponse)
async def make_decision(
    request: DecisionRequest,
    background_tasks: BackgroundTasks,
    container: ADAMContainer = Depends(get_container),
) -> DecisionResponse:
    """
    Make an ad decision using the ADAM platform.
    
    This is the main entry point for ad serving requests.
    
    Flow:
    1. Pull context from graph
    2. Route via Meta-Learner
    3. Execute appropriate path (fast/reasoning/explore)
    4. Verify decision
    5. Return selected ad with mechanisms
    """
    start_time = datetime.now(timezone.utc)
    
    try:
        # Convert request to internal models
        ad_candidates = [
            AdCandidate(
                ad_id=ac.ad_id,
                campaign_id=ac.campaign_id,
                creative_id=ac.creative_id,
                brand_id=ac.brand_id,
                category_id=ac.category_id,
                mechanism_id=ac.mechanism_id,
            )
            for ac in request.ad_candidates
        ]
        
        # Step 0: Initialize v3 cognitive layers
        narrative_engine = get_narrative_session_engine()
        metacognitive_engine = get_metacognitive_engine()
        mechanism_engine = get_mechanism_interaction_engine()
        
        # Record session event for narrative tracking
        await narrative_engine.record_event(
            user_id=request.user_id,
            event_type="decision_request",
            content_id=request.category_id,
            engagement_score=0.5,  # Neutral at request time
            context={
                "ad_count": len(request.ad_candidates),
                "brand_id": request.brand_id,
            }
        )
        
        # Step 1: Create blackboard state
        await container.blackboard.create_blackboard(
            request_id=request.request_id,
            user_id=request.user_id,
        )
        
        # Step 2: Pull graph context
        graph_context = await container.interaction_bridge.pull_context(
            request_id=request.request_id,
            user_id=request.user_id,
        )
        
        # Build request context for blackboard
        request_context = RequestContext(
            request_id=request.request_id,
            user_id=request.user_id,
            category_id=request.category_id or "",
            brand_id=request.brand_id or "",
        )
        
        # Step 3: Route via Meta-Learner
        routing_decision = await container.meta_learner.route_request(
            request_id=request.request_id,
            request_context=request_context,
        )
        
        # Step 4: Execute appropriate path
        if routing_decision.execution_path.value == "fast":
            # Fast path - use cached/archetype decision
            atom_outputs = await _execute_fast_path(
                container, request.user_id, request.category_id
            )
        elif routing_decision.execution_path.value == "exploration":
            # Exploration path - bandit-driven
            atom_outputs = await _execute_exploration_path(
                container, request.user_id, ad_candidates
            )
        else:
            # Reasoning path - full atom DAG
            dag_result = await container.atom_dag.execute(
                request_id=request.request_id,
                request_context=request_context,
            )
            atom_outputs = {
                r.atom_id: r.output.model_dump() if r.output else {}
                for r in dag_result.atom_results
            }
        
        # Step 4.5: Use v3 Mechanism Interaction Engine to optimize mechanism combination
        available_mechanisms = list(atom_outputs.get("atom_mechanism_activation", {}).get("mechanism_weights", {}).keys())
        if available_mechanisms:
            optimal_combo = await mechanism_engine.evaluate_combination(
                mechanisms=available_mechanisms[:5],  # Top 5 mechanisms
                context={"category": request.category_id, "brand": request.brand_id}
            )
            # Inject optimal combo info into atom outputs
            atom_outputs["v3_mechanism_optimization"] = {
                "optimal_mechanisms": optimal_combo.mechanisms,
                "combined_effectiveness": optimal_combo.combined_effectiveness,
                "synergies": optimal_combo.synergies,
                "conflicts": optimal_combo.conflicts,
            }
        
        # Step 5: Synthesize decision
        synthesis_result = await container.holistic_synthesizer.synthesize(
            request_id=request.request_id,
            user_id=request.user_id,
            atom_outputs=atom_outputs,
            ad_candidates=[ac.model_dump() for ac in ad_candidates],
            category_id=request.category_id,
            brand_id=request.brand_id,
        )
        
        # Step 6: Verify decision
        verification_result = await container.verification.verify(
            request_id=request.request_id,
            atom_outputs=atom_outputs,
            user_id=request.user_id,
            decision_id=synthesis_result.decision_id,
            auto_correct=True,
        )
        
        # Calculate latency
        end_time = datetime.now(timezone.utc)
        latency_ms = (end_time - start_time).total_seconds() * 1000
        
        # Step 7: Trace reasoning with v3 Meta-Cognitive Engine
        reasoning_trace = await metacognitive_engine.trace_reasoning(
            decision_id=synthesis_result.decision_id,
            strategy=ReasoningStrategy.DELIBERATE if routing_decision.execution_path.value == "reasoning" else ReasoningStrategy.FAST_HEURISTIC,
            input_sources=["graph_context", "blackboard", "meta_learner", "atom_dag", "holistic_synthesizer"],
            conclusion=f"Selected ad {synthesis_result.selected_ad_id or 'default'}",
            raw_confidence=synthesis_result.decision_confidence if hasattr(synthesis_result, 'decision_confidence') else 0.7,
            steps=[
                f"Pulled graph context for user {request.user_id}",
                f"Meta-learner routed to {routing_decision.execution_path.value} path",
                f"Executed atom DAG with {len(atom_outputs)} outputs",
                f"Synthesized decision from all sources",
                f"Verified decision: {verification_result.status.value}",
            ],
            uncertainties=[
                "User profile completeness unknown",
                "Mechanism effectiveness estimates based on historical data",
            ],
            reasoning_time_ms=latency_ms,
            user_id=request.user_id,
        )
        
        # Build response
        response = DecisionResponse(
            decision_id=synthesis_result.decision_id,
            request_id=request.request_id,
            selected_ad_id=synthesis_result.selected_ad_id or ad_candidates[0].ad_id,
            selected_ad_rank=1,
            mechanisms=[
                MechanismApplication(
                    mechanism_id=m.mechanism_id,
                    intensity=m.intensity,
                    rationale=m.rationale,
                )
                for m in synthesis_result.applied_mechanisms
            ] if hasattr(synthesis_result, 'applied_mechanisms') else [],
            primary_mechanism=synthesis_result.primary_mechanism if hasattr(synthesis_result, 'primary_mechanism') else None,
            decision_confidence=synthesis_result.decision_confidence if hasattr(synthesis_result, 'decision_confidence') else 0.7,
            execution_path=routing_decision.execution_path.value,
            modality_used=routing_decision.selected_modality.value,
            verification_status=verification_result.status.value,
            latency_ms=latency_ms,
        )
        
        if request.include_reasoning:
            response.reasoning = {
                "atom_outputs": atom_outputs,
                "routing_decision": routing_decision.model_dump(),
                "verification": {
                    "status": verification_result.status.value,
                    "constraints_passed": verification_result.total_constraints_passed,
                    "constraints_checked": verification_result.total_constraints_checked,
                },
                "v3_metacognitive": {
                    "trace_id": reasoning_trace.trace_id,
                    "strategy": reasoning_trace.strategy.value,
                    "calibrated_confidence": reasoning_trace.calibrated_confidence,
                    "confidence_level": reasoning_trace.confidence_level.value,
                    "steps": reasoning_trace.steps,
                    "uncertainties": reasoning_trace.uncertainties,
                },
                "v3_mechanism_optimization": atom_outputs.get("v3_mechanism_optimization"),
            }
        
        # Background: complete blackboard
        background_tasks.add_task(
            container.blackboard.complete_blackboard,
            request.request_id,
        )
        
        return response
    
    except Exception as e:
        logger.exception(f"Error making decision: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _execute_fast_path(
    container: ADAMContainer,
    user_id: str,
    category_id: Optional[str],
) -> Dict[str, Any]:
    """Execute fast path using cached/archetype outputs."""
    # Check cache first
    cache_key = f"adam:decision_cache:{user_id}:{category_id or 'default'}"
    cached = await container.redis_cache.get(cache_key)
    if cached:
        return cached
    
    # Use default outputs
    return {
        "atom_regulatory_focus": {"primary_assessment": "balanced", "overall_confidence": 0.5},
        "atom_construal_level": {"primary_assessment": "moderate", "overall_confidence": 0.5},
    }


async def _execute_exploration_path(
    container: ADAMContainer,
    user_id: str,
    ad_candidates: List[AdCandidate],
) -> Dict[str, Any]:
    """Execute exploration path using bandit."""
    # Simplified: random selection for exploration
    import random
    selected = random.choice(ad_candidates)
    return {
        "exploration_selection": {
            "selected_ad_id": selected.ad_id,
            "selection_method": "thompson_exploration",
            "overall_confidence": 0.4,
        }
    }


@router.post("/outcome", response_model=OutcomeResponse)
async def record_outcome(
    request: OutcomeRequest,
    background_tasks: BackgroundTasks,
    container: ADAMContainer = Depends(get_container),
) -> OutcomeResponse:
    """
    Record an outcome for a decision.
    
    This triggers learning across all components via the Gradient Bridge
    and updates v3 cognitive layer models.
    """
    try:
        # Map outcome type
        from adam.gradient_bridge.models.credit import OutcomeType
        outcome_type_map = {
            "conversion": OutcomeType.CONVERSION,
            "click": OutcomeType.CLICK,
            "skip": OutcomeType.SKIP,
            "engagement": OutcomeType.ENGAGEMENT,
        }
        outcome_type = outcome_type_map.get(
            request.outcome_type, OutcomeType.ENGAGEMENT
        )
        
        # Get cached attribution if available
        attribution = await container.gradient_bridge.get_attribution(
            request.decision_id
        )
        
        # Process outcome via Gradient Bridge
        signal_package = await container.gradient_bridge.process_outcome(
            decision_id=request.decision_id,
            request_id=attribution.request_id if attribution else request.decision_id,
            user_id=attribution.user_id if attribution else "unknown",
            outcome_type=outcome_type,
            outcome_value=request.outcome_value,
            atom_outputs=None,  # Would be loaded from cache
            mechanism_used=None,
            execution_path="",
        )
        
        # V3: Record outcome in meta-cognitive engine for confidence calibration
        metacognitive_engine = get_metacognitive_engine()
        correct = request.outcome_value >= 0.5  # Simple threshold
        
        # Find any reasoning traces for this decision and update them
        # This helps calibrate future confidence estimates
        for trace_id, trace in list(metacognitive_engine._traces.items()):
            if trace.decision_id == request.decision_id:
                await metacognitive_engine.record_outcome(trace_id, correct)
                break
        
        # V3: Record outcome in narrative engine
        narrative_engine = get_narrative_session_engine()
        if attribution:
            await narrative_engine.record_event(
                user_id=attribution.user_id,
                event_type=f"outcome_{request.outcome_type}",
                content_id=request.decision_id,
                engagement_score=request.outcome_value,
                context={"outcome_type": request.outcome_type}
            )
            
            # Check for milestone achievements
            milestone = await narrative_engine.check_for_milestone(attribution.user_id)
            if milestone:
                logger.info(f"User {attribution.user_id} achieved milestone: {milestone}")
        
        return OutcomeResponse(
            decision_id=request.decision_id,
            outcome_recorded=True,
            signals_generated=signal_package.total_signals,
        )
    
    except Exception as e:
        logger.exception(f"Error recording outcome: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{decision_id}")
async def get_decision(
    decision_id: str,
    container: ADAMContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Get details of a past decision."""
    
    # Try to get from attribution cache
    attribution = await container.gradient_bridge.get_attribution(decision_id)
    
    if not attribution:
        raise HTTPException(status_code=404, detail="Decision not found")
    
    return {
        "decision_id": decision_id,
        "request_id": attribution.request_id,
        "user_id": attribution.user_id,
        "outcome": {
            "type": attribution.outcome_type.value if attribution.outcome_type else None,
            "value": attribution.outcome_value,
        },
        "attribution": {
            "atom_credits": [
                {"atom_id": ac.atom_id, "credit": ac.credit_score}
                for ac in attribution.atom_credits
            ],
            "primary_mechanism": attribution.primary_mechanism,
            "execution_path": attribution.execution_path,
        },
    }
