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


class IdentifierRequest(BaseModel):
    """Identifier for identity resolution."""
    
    type: str  # email_hash, device_id, ip_hash, phone_hash, cookie
    value: str
    source: str = "direct"


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
    
    # Identity resolution (optional)
    identifiers: List[IdentifierRequest] = Field(
        default_factory=list,
        description="Additional identifiers for cross-device identity resolution",
    )
    
    # Competitive context (optional)
    competitor_ads: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Competitor ads for counter-strategy: [{'name': 'Nike', 'text': '...'}]",
    )
    
    # Options
    include_reasoning: bool = Field(default=False)
    include_explanation: bool = Field(
        default=False,
        description="Include human-readable explanation",
    )
    explanation_audience: str = Field(
        default="advertiser",
        description="Explanation audience: user, advertiser, engineer, regulator",
    )
    timeout_ms: int = Field(default=2000, ge=100, le=10000)


class MechanismApplication(BaseModel):
    """How a mechanism was applied."""
    
    mechanism_id: str
    intensity: float = Field(ge=0.0, le=1.0)
    rationale: str = ""


class ExplanationResponse(BaseModel):
    """Human-readable explanation."""
    
    summary: str
    reasoning: str
    mechanisms: List[Dict[str, Any]] = Field(default_factory=list)
    audience: str = "advertiser"


class IdentityResolution(BaseModel):
    """Identity resolution result."""
    
    unified_identity_id: Optional[str] = None
    match_type: str = "new"  # deterministic, probabilistic, new
    match_confidence: float = 0.0
    cross_device_count: int = 1


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
    
    # Identity resolution (if identifiers provided)
    identity: Optional[IdentityResolution] = None
    
    # Human-readable explanation (if requested)
    explanation: Optional[ExplanationResponse] = None
    
    # Competitive intelligence (if competitor_ads provided)
    competitive_insight: Optional[Dict[str, Any]] = None
    
    # Inferential reasoning chains (the "why, how, when")
    reasoning_chains: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Explicit inferential chains explaining WHY each mechanism "
                    "is recommended, HOW to execute it, and WHEN it applies. "
                    "Only populated when include_reasoning=True.",
    )


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
# HELPERS
# =============================================================================

def _extract_reasoning_chains(
    atom_outputs: Optional[Dict[str, Any]],
    workflow_result: Optional[Dict[str, Any]] = None,
) -> Optional[List[Dict[str, Any]]]:
    """
    Extract inferential reasoning chains from atom outputs.

    Chains are generated by the MechanismActivationAtom and stored in its
    secondary_assessments under the key "inferential_chains".
    """
    if not atom_outputs:
        if workflow_result:
            atom_outputs = workflow_result.get("atom_outputs", {})
        if not atom_outputs:
            return None

    # Look for chains in mechanism activation atom output
    mech_output = atom_outputs.get("atom_mechanism_activation", {})
    if isinstance(mech_output, dict):
        chains = mech_output.get("secondary_assessments", {}).get("inferential_chains")
        if not chains:
            # Try direct access (some paths serialize differently)
            chains = mech_output.get("inferential_chains")
        if chains:
            return chains

    # Try in synergy orchestrator result
    if workflow_result:
        chains = workflow_result.get("inferential_chains")
        if chains:
            return chains

    return None


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
    
    IMPORTANT: This endpoint now uses the LangGraph workflow executor when available.
    The workflow provides:
    - Proper learning signal propagation
    - Integrated Thompson Sampling for exploration
    - Bidirectional Graph-AoT communication
    - Full susceptibility and persuasion intelligence
    
    Fallback to direct component calls if workflow unavailable.
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
        
        # =====================================================================
        # PRE-DECISION ENRICHMENT: Identity + Competitive Intelligence
        # =====================================================================
        
        enriched_context = None
        identity_result = None
        competitive_insight = None
        
        if request.identifiers or request.competitor_ads:
            try:
                from adam.integration.decision_enrichment import (
                    get_decision_enrichment,
                    IdentifierData,
                )
                
                enrichment = get_decision_enrichment()
                
                # Convert identifiers
                identifiers = [
                    IdentifierData(
                        type=i.type,
                        value=i.value,
                        source=i.source,
                    )
                    for i in request.identifiers
                ] if request.identifiers else None
                
                # Convert competitor ads
                competitor_ads = [
                    (ad["name"], ad["text"])
                    for ad in request.competitor_ads
                ] if request.competitor_ads else None
                
                enriched_context = await enrichment.enrich_context(
                    user_id=request.user_id,
                    identifiers=identifiers,
                    brand_name=request.brand_id,
                    competitor_ads=competitor_ads,
                )
                
                # Prepare identity result for response
                if enriched_context.unified_identity_id:
                    identity_result = IdentityResolution(
                        unified_identity_id=enriched_context.unified_identity_id,
                        match_type=enriched_context.identity_match_type,
                        match_confidence=enriched_context.identity_confidence,
                        cross_device_count=enriched_context.cross_device_count,
                    )
                
                # Prepare competitive insight for response
                if enriched_context.competitor_mechanisms:
                    competitive_insight = {
                        "market_saturation": enriched_context.competitor_mechanisms,
                        "underutilized_mechanisms": enriched_context.underutilized_mechanisms,
                        "recommended_strategy": enriched_context.recommended_counter_strategy,
                    }
                
                logger.debug(
                    f"Pre-decision enrichment complete: identity={enriched_context.identity_match_type}, "
                    f"competitive={len(enriched_context.competitor_mechanisms)} mechanisms"
                )
                
            except ImportError:
                logger.debug("Decision enrichment not available")
            except Exception as e:
                logger.warning(f"Pre-decision enrichment failed: {e}")
        
        # =====================================================================
        # USE WORKFLOW EXECUTOR IF AVAILABLE (PREFERRED PATH)
        # =====================================================================
        
        if container.workflow_executor is not None:
            logger.info(f"Using LangGraph workflow for decision {request.request_id}")
            
            # Execute the complete workflow
            workflow_result = await container.workflow_executor.execute(
                request_id=request.request_id,
                user_id=request.user_id,
                ad_candidates=[ac.model_dump() for ac in ad_candidates],
                category_id=request.category_id,
                brand_id=request.brand_id,
                session_context=request.context.model_dump() if hasattr(request, 'context') and request.context else {},
            )
            
            # Calculate latency
            end_time = datetime.now(timezone.utc)
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            # Extract decision from workflow result
            holistic_decision = workflow_result.get("decision")
            
            if not holistic_decision:
                logger.warning("Workflow returned no decision, falling back to direct path")
                # Fall through to direct component calls
            else:
                # Build response from workflow result
                response = DecisionResponse(
                    decision_id=workflow_result.get("decision_id", str(uuid4())),
                    request_id=request.request_id,
                    selected_ad_id=holistic_decision.get("selected_ad_id") or ad_candidates[0].ad_id,
                    selected_ad_rank=holistic_decision.get("selected_ad_rank", 1),
                    mechanisms=[
                        MechanismApplication(
                            mechanism_id=m.get("mechanism_id"),
                            intensity=m.get("intensity", 0.5),
                            rationale=m.get("rationale", ""),
                        )
                        for m in holistic_decision.get("mechanisms", [])
                    ],
                    primary_mechanism=holistic_decision.get("primary_mechanism"),
                    decision_confidence=holistic_decision.get("confidence", 0.7),
                    execution_path=workflow_result.get("path_taken", "reasoning"),
                    modality_used=holistic_decision.get("modality", "CAUSAL_INFERENCE"),
                    verification_status=holistic_decision.get("verification_status", "passed"),
                    latency_ms=latency_ms,
                )
                
                if request.include_reasoning:
                    response.reasoning = {
                        "workflow_path": workflow_result.get("path_taken"),
                        "node_timings": workflow_result.get("timings"),
                        "errors": workflow_result.get("errors"),
                        "source": "langgraph_workflow",
                    }
                    # Include inferential chains if available
                    response.reasoning_chains = _extract_reasoning_chains(
                        None, workflow_result
                    )
                
                # Background: complete blackboard
                background_tasks.add_task(
                    container.blackboard.complete_blackboard,
                    request.request_id,
                )
                
                # CRITICAL: Persist decision to graph for learning loop
                # This was identified as "never called" in the system audit
                if container.bidirectional_bridge:
                    background_tasks.add_task(
                        container.bidirectional_bridge.persist_decision_to_graph,
                        decision_id=response.decision_id,
                        request_id=request.request_id,
                        user_id=request.user_id,
                        selected_ad_id=response.selected_ad_id,
                        primary_mechanism=response.primary_mechanism,
                        mechanisms=[m.model_dump() for m in response.mechanisms],
                        execution_path=response.execution_path,
                        confidence=response.decision_confidence,
                        latency_ms=latency_ms,
                        atom_outputs=workflow_result.get("atom_outputs"),
                    )
                    logger.debug(f"Scheduled decision persistence for {response.decision_id}")
                
                logger.info(
                    f"Workflow decision complete: {response.decision_id}, "
                    f"path={workflow_result.get('path_taken')}, "
                    f"latency={latency_ms:.0f}ms"
                )
                
                return response
        
        # =====================================================================
        # TRY SYNERGY ORCHESTRATOR (New Intelligence-Aware Path)
        # =====================================================================
        
        try:
            from adam.workflows.synergy_orchestrator import get_synergy_orchestrator
            
            orchestrator = get_synergy_orchestrator()
            
            logger.info(f"Using SynergyOrchestrator for decision {request.request_id}")
            
            synergy_result = await orchestrator.execute(
                user_id=request.user_id,
                brand_name=request.brand_id or "",
                product_name=request.category_id or "",
                product_category=request.category_id or "",
                request_id=request.request_id,
            )
            
            end_time = datetime.now(timezone.utc)
            latency_ms = (end_time - start_time).total_seconds() * 1000
            
            # Extract decision from synergy result
            mechanisms = synergy_result.get("mechanisms_applied", [])
            decision_id = synergy_result.get("decision_id", f"dec_{uuid4().hex[:12]}")
            
            response = DecisionResponse(
                decision_id=decision_id,
                request_id=request.request_id,
                selected_ad_id=ad_candidates[0].ad_id if ad_candidates else "default",
                selected_ad_rank=1,
                mechanisms=[
                    MechanismApplication(
                        mechanism_id=m.get("name", "unknown"),
                        intensity=m.get("intensity", 0.5),
                        rationale=m.get("source", ""),
                    )
                    for m in mechanisms
                ],
                primary_mechanism=mechanisms[0]["name"] if mechanisms else None,
                decision_confidence=synergy_result.get("confidence_scores", {}).get("graph_confidence", 0.6),
                execution_path="synergy_orchestrator",
                modality_used="INTELLIGENCE_FUSION",
                verification_status="passed",
                latency_ms=latency_ms,
                identity=identity_result,
                competitive_insight=competitive_insight,
            )
            
            if request.include_reasoning:
                response.reasoning = {
                    "graph_intelligence": synergy_result.get("graph_intelligence"),
                    "helpful_vote_intelligence": synergy_result.get("helpful_vote_intelligence"),
                    "full_intelligence_profile": synergy_result.get("full_intelligence_profile"),
                    "injected_intelligence": synergy_result.get("injected_intelligence"),
                    "atom_outputs": synergy_result.get("atom_outputs"),
                    "source": "synergy_orchestrator",
                }
            
            # Add explanation if requested
            if request.include_explanation:
                try:
                    from adam.integration.decision_enrichment import get_decision_enrichment
                    enrichment = get_decision_enrichment()
                    
                    if enrichment.explanation_service:
                        from adam.explanation.models import ExplanationAudience
                        
                        audience_map = {
                            "user": ExplanationAudience.USER,
                            "advertiser": ExplanationAudience.ADVERTISER,
                            "engineer": ExplanationAudience.ENGINEER,
                            "regulator": ExplanationAudience.REGULATOR,
                        }
                        
                        explanation = enrichment.explanation_service.explain_decision(
                            decision_id=decision_id,
                            audience=audience_map.get(request.explanation_audience, ExplanationAudience.ADVERTISER),
                            decision_data={
                                "decision_id": decision_id,
                                "mechanisms": [m.get("name") for m in mechanisms],
                                "mechanism_scores": {m.get("name"): m.get("intensity", 0.5) for m in mechanisms},
                                "archetype": synergy_result.get("detected_archetype", "unknown"),
                                "framing": "gain",
                                "confidence": response.decision_confidence,
                            },
                        )
                        
                        response.explanation = ExplanationResponse(
                            summary=explanation.summary,
                            reasoning=explanation.reasoning,
                            mechanisms=[
                                {
                                    "mechanism": m.mechanism,
                                    "description": m.human_description,
                                    "rationale": m.rationale,
                                    "score": m.score,
                                }
                                for m in explanation.mechanisms
                            ],
                            audience=request.explanation_audience,
                        )
                except Exception as e:
                    logger.warning(f"Explanation generation failed: {e}")
            
            # Persist for learning
            if container.bidirectional_bridge:
                background_tasks.add_task(
                    container.bidirectional_bridge.persist_decision_to_graph,
                    decision_id=response.decision_id,
                    request_id=request.request_id,
                    user_id=request.user_id,
                    selected_ad_id=response.selected_ad_id,
                    primary_mechanism=response.primary_mechanism,
                    mechanisms=[m.model_dump() for m in response.mechanisms],
                    execution_path=response.execution_path,
                    confidence=response.decision_confidence,
                    latency_ms=latency_ms,
                    atom_outputs=synergy_result.get("atom_outputs"),
                )
            
            logger.info(
                f"SynergyOrchestrator decision complete: {response.decision_id}, "
                f"mechanisms={len(mechanisms)}, latency={latency_ms:.0f}ms"
            )
            
            return response
            
        except ImportError:
            logger.debug("SynergyOrchestrator not available, falling back to direct calls")
        except Exception as e:
            logger.warning(f"SynergyOrchestrator failed: {e}, falling back to direct calls")
        
        # =====================================================================
        # FALLBACK: DIRECT COMPONENT CALLS (Original Implementation)
        # =====================================================================
        
        logger.info(f"Using direct component calls for decision {request.request_id} (orchestrators unavailable)")
        
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
        
        # CRITICAL: Cache atom_outputs for outcome attribution
        # Without this, the learning loop breaks because outcome processing can't attribute to atoms
        if atom_outputs:
            cache_key = f"adam:atom_outputs:{synthesis_result.decision_id}"
            try:
                await container.redis_cache.set(
                    cache_key,
                    atom_outputs,
                    expire=3600 * 24  # 24 hour TTL for attribution window
                )
                logger.debug(f"Cached {len(atom_outputs)} atom outputs for {synthesis_result.decision_id}")
            except Exception as e:
                logger.warning(f"Failed to cache atom outputs: {e}")
        
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
                "source": "direct_component_calls",  # Indicate fallback path
            }
            # Include inferential chains
            response.reasoning_chains = _extract_reasoning_chains(atom_outputs)
        
        # Background: complete blackboard
        background_tasks.add_task(
            container.blackboard.complete_blackboard,
            request.request_id,
        )
        
        # CRITICAL: Persist decision to graph for learning loop (fallback path)
        if container.bidirectional_bridge:
            background_tasks.add_task(
                container.bidirectional_bridge.persist_decision_to_graph,
                decision_id=response.decision_id,
                request_id=request.request_id,
                user_id=request.user_id,
                selected_ad_id=response.selected_ad_id,
                primary_mechanism=response.primary_mechanism,
                mechanisms=[m.model_dump() for m in response.mechanisms],
                execution_path=response.execution_path,
                confidence=response.decision_confidence,
                latency_ms=response.latency_ms,
                atom_outputs=atom_outputs,
            )
            logger.debug(f"Scheduled decision persistence (fallback) for {response.decision_id}")
        
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
    
    CRITICAL: We now load atom_outputs from cache to enable proper attribution.
    Without this, atom-level learning was completely broken.
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
        
        # CRITICAL FIX: Load atom_outputs from cache for proper attribution
        # Without this, atom-level credit attribution fails completely
        atom_outputs = None
        mechanism_used = None
        execution_path = ""
        
        if attribution:
            # Try to load atom outputs from Redis cache
            cache_key = f"adam:atom_outputs:{request.decision_id}"
            try:
                cached_outputs = await container.redis_cache.get(cache_key)
                if cached_outputs:
                    atom_outputs = cached_outputs
                    logger.debug(f"Loaded {len(atom_outputs)} atom outputs from cache for {request.decision_id}")
            except Exception as e:
                logger.warning(f"Failed to load atom outputs from cache: {e}")
            
            # Extract mechanism and execution path from attribution
            mechanism_used = attribution.primary_mechanism
            execution_path = attribution.execution_path or ""
            
            # If no cached outputs, try to get from atom contribution cache
            if not atom_outputs:
                try:
                    from adam.atoms.core.base import BaseAtom
                    contributions = await BaseAtom.get_all_contributions(request.decision_id)
                    if contributions:
                        atom_outputs = {
                            atom_id: {"contribution": contrib}
                            for atom_id, contrib in contributions.items()
                        }
                        logger.debug(f"Loaded {len(atom_outputs)} contributions for {request.decision_id}")
                except Exception as e:
                    logger.warning(f"Failed to load atom contributions: {e}")
        
        # Process outcome via Gradient Bridge - now with atom_outputs!
        signal_package = await container.gradient_bridge.process_outcome(
            decision_id=request.decision_id,
            request_id=attribution.request_id if attribution else request.decision_id,
            user_id=attribution.user_id if attribution else "unknown",
            outcome_type=outcome_type,
            outcome_value=request.outcome_value,
            atom_outputs=atom_outputs,  # FIXED: Now properly loaded from cache
            mechanism_used=mechanism_used,
            execution_path=execution_path,
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
        
        # CRITICAL: Create learning path in graph for outcome attribution
        # This enables: querying which decisions led to outcomes, mechanism effectiveness over time
        if container.bidirectional_bridge:
            background_tasks.add_task(
                container.bidirectional_bridge.create_learning_path,
                decision_id=request.decision_id,
                outcome_type=request.outcome_type,
                outcome_value=request.outcome_value,
                attribution_computed=signal_package.total_signals > 0,
                signals_emitted=signal_package.total_signals,
            )
            logger.debug(f"Scheduled learning path creation for {request.decision_id}")
        
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


# =============================================================================
# ENRICH ENDPOINT (DSP/SSP Integration Surface)
# =============================================================================

class EnrichRequest(BaseModel):
    """
    Request for psychological enrichment without ad selection.
    
    This is the primary surface for DSP/SSP integration. Given an NDF profile
    (or signals from which to infer one), returns the full inferential
    intelligence: why each mechanism works, how to execute it, and when
    it applies.
    
    No ad candidates needed — this is pure intelligence enrichment.
    """
    request_id: str = Field(
        default_factory=lambda: f"enrich_{uuid4().hex[:12]}"
    )
    
    # NDF profile (the 7 nonconscious decision dimensions, 0-1 scale)
    ndf_profile: Optional[Dict[str, float]] = Field(
        default=None,
        description="Direct NDF profile: {uncertainty_tolerance, cognitive_engagement, "
                    "social_calibration, approach_avoidance, status_sensitivity, "
                    "arousal_seeking, temporal_horizon}. Each 0-1.",
    )
    
    # Alternative: signals to infer NDF from
    user_text: Optional[str] = Field(
        default=None,
        description="User-generated text (review, search query, etc.) "
                    "from which to infer NDF profile.",
    )
    
    # Archetype (optional, for cold-start priors)
    archetype: Optional[str] = None
    
    # Context
    category: Optional[str] = None
    brand: Optional[str] = None
    device: Optional[str] = None
    hour: Optional[int] = None
    price: Optional[float] = None
    involvement: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    time_pressure: bool = False
    novel_category: bool = False
    exposure_count: int = 0
    
    # Output options
    top_k: int = Field(default=5, ge=1, le=15)
    include_narrative: bool = Field(
        default=True,
        description="Include human-readable narrative explanation",
    )
    include_creative_guidance: bool = Field(
        default=True,
        description="Include actionable creative guidance",
    )


class EnrichResponse(BaseModel):
    """
    Psychological enrichment response.
    
    Contains the inferential intelligence that makes ADAM categorically
    different from correlational ad-tech systems:
    - WHY each mechanism is recommended (the inferential chain)
    - HOW to execute it (creative guidance from processing route)
    - WHEN it applies (context conditions and moderators)
    - HOW CONFIDENT we are (chain strength + empirical support)
    """
    request_id: str
    
    # NDF profile used (inferred or provided)
    ndf_profile: Dict[str, float]
    archetype: Optional[str] = None
    
    # Active psychological states
    active_states: List[str] = Field(default_factory=list)
    
    # Inferential chains (the core output)
    chains: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Ranked inferential chains, each containing: "
                    "recommended_mechanism, steps, creative_guidance, "
                    "confidence, transferability_score",
    )
    
    # Narrative explanations (optional)
    narratives: Optional[List[str]] = None
    
    # Summary
    top_mechanism: Optional[str] = None
    top_mechanism_score: Optional[float] = None
    total_chains: int = 0
    processing_route: Optional[str] = None
    context_modifiers: List[str] = Field(default_factory=list)


@router.post("/enrich", response_model=EnrichResponse)
async def enrich(request: EnrichRequest) -> EnrichResponse:
    """
    Psychological enrichment endpoint for DSP/SSP integration.
    
    Given an NDF profile (or user text to infer one), returns the full
    inferential intelligence: explicit reasoning chains with creative guidance.
    
    This is the endpoint that makes ADAM's intelligence accessible to
    external platforms without requiring the full ad-decision pipeline.
    
    Example:
        POST /api/v1/decisions/enrich
        {
            "ndf_profile": {
                "uncertainty_tolerance": 0.3,
                "cognitive_engagement": 0.8,
                "social_calibration": 0.6,
                "approach_avoidance": 0.7,
                "status_sensitivity": 0.4,
                "arousal_seeking": 0.5,
                "temporal_horizon": 0.6
            },
            "category": "electronics",
            "time_pressure": true,
            "include_narrative": true
        }
    
    Returns inferential chains explaining WHY authority + social_proof
    work for this user (low uncertainty tolerance → need for closure →
    authority, high cognitive engagement → central route → substantive
    evidence required), with creative guidance on HOW to execute.
    """
    try:
        from adam.intelligence.graph.reasoning_chain_generator import (
            generate_chains_local,
            _determine_active_states,
        )
        
        # Get or infer NDF profile
        ndf_profile = request.ndf_profile
        
        if not ndf_profile and request.user_text:
            # Attempt to infer NDF from text via the foundation model
            try:
                from adam.ml.foundation_model import get_foundation_model
                fm = get_foundation_model()
                prediction = fm.predict(request.user_text)
                if prediction and prediction.get("ndf"):
                    ndf_profile = prediction["ndf"]
            except Exception as e:
                logger.debug(f"Foundation model NDF inference failed: {e}")
        
        if not ndf_profile:
            # Use archetype-based defaults if available
            if request.archetype:
                try:
                    from adam.core.learning.learned_priors_integration import (
                        get_learned_priors_service,
                    )
                    priors = get_learned_priors_service()
                    ndf_profile = priors.get_ndf_for_archetype(request.archetype)
                except Exception:
                    pass
        
        if not ndf_profile:
            raise HTTPException(
                status_code=400,
                detail="Either ndf_profile or user_text must be provided. "
                       "ndf_profile is a dict of 7 NDF dimensions (0-1 scale): "
                       "uncertainty_tolerance, cognitive_engagement, social_calibration, "
                       "approach_avoidance, status_sensitivity, arousal_seeking, temporal_horizon",
            )
        
        # Build context
        context = {}
        if request.device:
            context["device"] = request.device
        if request.hour is not None:
            context["hour"] = request.hour
        if request.price is not None:
            context["price"] = request.price
        if request.involvement is not None:
            context["involvement"] = request.involvement
        if request.time_pressure:
            context["time_pressure"] = True
        if request.novel_category:
            context["novel_category"] = True
        if request.exposure_count > 0:
            context["exposure_count"] = request.exposure_count
        
        # Generate inferential chains
        chains = generate_chains_local(
            ndf_profile=ndf_profile,
            context=context,
            archetype=request.archetype or "",
            category=request.category or "",
            request_id=request.request_id,
            top_k=request.top_k,
        )
        
        active_states = _determine_active_states(ndf_profile)
        
        # Build response
        chain_dicts = [c.to_dict() for c in chains]
        
        # Remove creative guidance if not requested
        if not request.include_creative_guidance:
            for cd in chain_dicts:
                cd.pop("creative_guidance", None)
        
        # Build narratives if requested
        narratives = None
        if request.include_narrative and chains:
            narratives = [c.to_narrative() for c in chains]
        
        return EnrichResponse(
            request_id=request.request_id,
            ndf_profile=ndf_profile,
            archetype=request.archetype,
            active_states=active_states,
            chains=chain_dicts,
            narratives=narratives,
            top_mechanism=chains[0].recommended_mechanism if chains else None,
            top_mechanism_score=round(chains[0].mechanism_score, 4) if chains else None,
            total_chains=len(chains),
            processing_route=chains[0].processing_route if chains else None,
            context_modifiers=chains[0].context_modifiers if chains else [],
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in enrichment: {e}")
        raise HTTPException(status_code=500, detail=str(e))
