# =============================================================================
# ADAM Holistic Decision Workflow
# Location: adam/workflows/holistic_decision_workflow.py
# =============================================================================

"""
HOLISTIC DECISION WORKFLOW

This is the complete LangGraph workflow that:
1. Pulls context from all 10 intelligence sources
2. Routes through Meta-Learner
3. Executes Atom of Thought DAG
4. Synthesizes via Holistic Decision Synthesizer
5. Propagates learning through all components

This is the MAIN EXECUTION PATH for ADAM.
"""

from typing import Dict, List, Optional, Any, TypedDict, Annotated, Callable
from datetime import datetime, timezone
from enum import Enum
from functools import partial
from pydantic import BaseModel, Field
import operator
import asyncio
import logging

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)


# =============================================================================
# ASYNC NODE WRAPPERS (FIX: Proper async handling without blocking event loop)
# =============================================================================

def create_async_node(
    async_func: Callable,
    **bound_kwargs
) -> Callable:
    """
    Create a properly async LangGraph node from an async function.
    
    LangGraph natively supports async nodes - this wrapper properly binds
    dependencies without blocking the event loop.
    
    CRITICAL FIX: Replaces the anti-pattern:
        lambda s: asyncio.get_event_loop().run_until_complete(...)
    
    With proper async handling that allows true concurrency.
    """
    async def wrapped_node(state: Dict) -> Dict:
        return await async_func(state, **bound_kwargs)
    return wrapped_node


# =============================================================================
# WORKFLOW STATE
# =============================================================================

class ExecutionPath(str, Enum):
    """Execution paths determined by Meta-Learner."""
    FAST = "fast"           # Cache/archetype-based
    REASONING = "reasoning"  # Full Claude atoms
    EXPLORE = "explore"      # Bandit exploration


class WorkflowState(TypedDict):
    """
    Complete state for the Holistic Decision Workflow.
    
    This state flows through all nodes and accumulates context
    from every intelligence source.
    """
    
    # =========================================================================
    # REQUEST IDENTITY
    # =========================================================================
    request_id: str
    user_id: str
    decision_id: str
    
    # =========================================================================
    # INPUT CONTEXT
    # =========================================================================
    ad_candidates: List[Dict[str, Any]]
    category_id: Optional[str]
    brand_id: Optional[str]
    session_context: Dict[str, Any]
    
    # =========================================================================
    # GRAPH CONTEXT (from #01)
    # =========================================================================
    graph_context: Optional[Dict[str, Any]]
    evidence_package: Optional[Dict[str, Any]]
    
    # =========================================================================
    # BLACKBOARD STATE (from #02)
    # =========================================================================
    blackboard_state: Optional[Dict[str, Any]]
    
    # =========================================================================
    # META-LEARNER ROUTING (from #03)
    # =========================================================================
    selected_modality: Optional[str]
    selected_path: Optional[ExecutionPath]
    routing_confidence: float
    
    # =========================================================================
    # ATOM OUTPUTS (from #04)
    # =========================================================================
    atom_outputs: Dict[str, Dict[str, Any]]
    
    # =========================================================================
    # SIGNAL AGGREGATION (from #08)
    # =========================================================================
    aggregated_signals: Dict[str, Any]
    
    # =========================================================================
    # JOURNEY CONTEXT (from #10)
    # =========================================================================
    journey_state: Optional[str]
    intervention_windows: List[Dict[str, Any]]
    
    # =========================================================================
    # TEMPORAL CONTEXT (from #23)
    # =========================================================================
    temporal_patterns: Optional[Dict[str, Any]]
    life_events: List[Dict[str, Any]]
    
    # =========================================================================
    # ADVERTISING PSYCHOLOGY CONTEXT (from Research Integration)
    # =========================================================================
    advertising_psychology_context: Optional[Dict[str, Any]]
    regulatory_focus_context: Optional[Dict[str, Any]]
    cognitive_state_context: Optional[Dict[str, Any]]
    message_frame_recommendations: Optional[Dict[str, Any]]
    
    # =========================================================================
    # BRAND CONTEXT (from #14)
    # =========================================================================
    brand_constraints: List[str]
    brand_voice: Optional[Dict[str, Any]]
    
    # =========================================================================
    # BRAND PERSONALITY CONTEXT (NEW - Brand-as-Person Integration)
    # =========================================================================
    brand_personality_profile: Optional[Dict[str, Any]]  # Full BrandPersonalityProfile
    brand_archetype: Optional[str]  # Brand's Jung/Mark archetype
    brand_aaker_dimensions: Optional[Dict[str, float]]  # Aaker brand personality
    brand_relationship_role: Optional[str]  # How brand relates to consumer
    brand_voice_characteristics: Optional[Dict[str, float]]  # Voice formality, energy, etc.
    
    # =========================================================================
    # COMPETITIVE CONTEXT (from #22)
    # =========================================================================
    competitive_landscape: Optional[Dict[str, Any]]
    
    # =========================================================================
    # HOLISTIC SYNTHESIS OUTPUT
    # =========================================================================
    holistic_decision: Optional[Dict[str, Any]]
    
    # =========================================================================
    # LEARNING SIGNALS
    # =========================================================================
    learning_signals: Annotated[List[Dict[str, Any]], operator.add]
    
    # =========================================================================
    # EMERGENT INTELLIGENCE CONTEXT
    # =========================================================================
    curiosity_scores: Optional[Dict[str, float]]  # Predictive Processing
    neural_thompson_selection: Optional[Dict[str, Any]]  # Neural Thompson
    emergent_constructs: Optional[List[Dict[str, Any]]]  # Emergence Engine
    causal_insights: Optional[Dict[str, Any]]  # Causal Discovery
    
    # =========================================================================
    # EXECUTION METADATA
    # =========================================================================
    start_time: datetime
    node_timings: Dict[str, float]
    errors: List[str]


# =============================================================================
# WORKFLOW NODE FUNCTIONS
# =============================================================================

async def initialize_state(state: WorkflowState) -> WorkflowState:
    """Initialize workflow state with defaults."""
    
    import uuid
    
    state["decision_id"] = f"dec_{uuid.uuid4().hex[:12]}"
    state["start_time"] = datetime.now(timezone.utc)
    state["atom_outputs"] = {}
    state["learning_signals"] = []
    state["node_timings"] = {}
    state["errors"] = []
    
    return state


async def pull_graph_context(
    state: WorkflowState,
    interaction_bridge
) -> WorkflowState:
    """
    Pull complete context from Neo4j via Interaction Bridge (#01).
    
    This gathers:
    - User profile snapshot
    - Mechanism effectiveness history
    - Personality priors
    - Category patterns
    - Multi-source evidence package
    """
    
    start = datetime.now(timezone.utc)
    
    try:
        context = await interaction_bridge.pull_context(
            request_id=state["request_id"],
            user_id=state["user_id"],
            include_evidence=True
        )
        
        state["graph_context"] = context.model_dump() if hasattr(context, "model_dump") else context
        state["evidence_package"] = context.evidence_package if hasattr(context, "evidence_package") else None
        
    except Exception as e:
        logger.error(f"Error pulling graph context: {e}")
        state["errors"].append(f"graph_context: {str(e)}")
    
    state["node_timings"]["pull_graph_context"] = (
        datetime.now(timezone.utc) - start
    ).total_seconds() * 1000
    
    return state


async def get_blackboard_state(
    state: WorkflowState,
    blackboard_service
) -> WorkflowState:
    """
    Get current Blackboard state (#02).
    
    This provides shared working memory across components.
    """
    
    start = datetime.now(timezone.utc)
    
    try:
        bb_state = await blackboard_service.get_complete_state(
            request_id=state["request_id"],
            user_id=state["user_id"]
        )
        state["blackboard_state"] = bb_state
        
    except Exception as e:
        logger.error(f"Error getting blackboard state: {e}")
        state["errors"].append(f"blackboard: {str(e)}")
    
    state["node_timings"]["get_blackboard"] = (
        datetime.now(timezone.utc) - start
    ).total_seconds() * 1000
    
    return state


async def meta_learner_routing(
    state: WorkflowState,
    meta_learner,
    meta_learner_integration
) -> WorkflowState:
    """
    Route request via Meta-Learner (#03).
    
    Determines optimal execution path using Thompson Sampling.
    """
    
    start = datetime.now(timezone.utc)
    
    try:
        # Build context features for routing
        context_features = {
            "user_data_richness": _compute_data_richness(state.get("graph_context")),
            "has_conversion_history": bool(state.get("graph_context", {}).get("conversion_history")),
            "category_novelty": _compute_category_novelty(state.get("category_id"), state.get("graph_context")),
            "session_depth": len(state.get("session_context", {}).get("events", [])),
        }
        
        routing_decision = await meta_learner.select_modality(
            user_id=state["user_id"],
            context_features=context_features
        )
        
        state["selected_modality"] = routing_decision.modality
        state["selected_path"] = ExecutionPath(routing_decision.path.lower())
        state["routing_confidence"] = routing_decision.confidence
        
        # Register for learning
        await meta_learner_integration.register_routing_decision(
            decision_id=state["decision_id"],
            user_id=state["user_id"],
            context=context_features,
            selected_modality=routing_decision.modality,
            selected_path=routing_decision.path,
            selection_confidence=routing_decision.confidence
        )
        
    except Exception as e:
        logger.error(f"Error in meta-learner routing: {e}")
        state["selected_path"] = ExecutionPath.REASONING  # Default to full reasoning
        state["errors"].append(f"meta_learner: {str(e)}")
    
    state["node_timings"]["meta_learner_routing"] = (
        datetime.now(timezone.utc) - start
    ).total_seconds() * 1000
    
    return state


def _compute_data_richness(graph_context: Optional[Dict]) -> float:
    """Compute user data richness score."""
    if not graph_context:
        return 0.0
    
    scores = []
    if graph_context.get("personality_snapshot"):
        scores.append(0.3)
    if graph_context.get("mechanism_effectiveness"):
        scores.append(0.3)
    if graph_context.get("conversion_history"):
        scores.append(0.4)
    
    return sum(scores)


def _compute_category_novelty(category_id: Optional[str], graph_context: Optional[Dict]) -> float:
    """Compute how novel this category is for the user."""
    if not category_id or not graph_context:
        return 1.0  # High novelty if unknown
    
    seen_categories = graph_context.get("seen_categories", [])
    if category_id in seen_categories:
        return 0.2  # Low novelty
    return 0.8  # High novelty


async def execute_fast_path(
    state: WorkflowState,
    cache_service,
    archetype_service
) -> WorkflowState:
    """
    Fast path execution - use cached/archetype-based decisions.
    """
    
    start = datetime.now(timezone.utc)
    
    try:
        # Try cache first
        cached = await cache_service.get_cached_decision(
            user_id=state["user_id"],
            category_id=state.get("category_id")
        )
        
        if cached:
            state["atom_outputs"] = cached.get("atom_outputs", {})
        else:
            # Fall back to archetype
            archetype_outputs = await archetype_service.get_archetype_outputs(
                user_id=state["user_id"],
                category_id=state.get("category_id")
            )
            state["atom_outputs"] = archetype_outputs
            
    except Exception as e:
        logger.error(f"Error in fast path: {e}")
        state["errors"].append(f"fast_path: {str(e)}")
    
    state["node_timings"]["fast_path"] = (
        datetime.now(timezone.utc) - start
    ).total_seconds() * 1000
    
    return state


async def execute_reasoning_path(
    state: WorkflowState,
    atom_executor,
    atom_integration
) -> WorkflowState:
    """
    Reasoning path execution - full Atom of Thought DAG.
    
    Executes the complete psychological reasoning pipeline:
    - User State Atom
    - Regulatory Focus Atom
    - Construal Level Atom
    - Cognitive Load Atom
    - Personality Expression Atom
    - Mechanism Activation Atom
    - Message Framing Atom
    """
    
    start = datetime.now(timezone.utc)
    
    try:
        # Build atom context
        atom_context = {
            "user_id": state["user_id"],
            "graph_context": state.get("graph_context"),
            "evidence_package": state.get("evidence_package"),
            "session_context": state.get("session_context"),
            "blackboard_state": state.get("blackboard_state"),
        }
        
        # Execute atom DAG
        atom_outputs = await atom_executor.execute_dag(
            context=atom_context,
            ad_candidates=state.get("ad_candidates", [])
        )
        
        state["atom_outputs"] = atom_outputs
        
        # Register for learning
        await atom_integration.register_atom_execution(
            decision_id=state["decision_id"],
            atom_outputs=atom_outputs
        )
        
    except Exception as e:
        logger.error(f"Error in reasoning path: {e}")
        state["errors"].append(f"reasoning_path: {str(e)}")
    
    state["node_timings"]["reasoning_path"] = (
        datetime.now(timezone.utc) - start
    ).total_seconds() * 1000
    
    return state


async def execute_explore_path(
    state: WorkflowState,
    bandit_service
) -> WorkflowState:
    """
    Exploration path - bandit-driven discovery.
    """
    
    start = datetime.now(timezone.utc)
    
    try:
        explore_outputs = await bandit_service.explore(
            user_id=state["user_id"],
            context=state.get("graph_context", {}),
            ad_candidates=state.get("ad_candidates", [])
        )
        
        state["atom_outputs"] = explore_outputs
        
    except Exception as e:
        logger.error(f"Error in explore path: {e}")
        state["errors"].append(f"explore_path: {str(e)}")
    
    state["node_timings"]["explore_path"] = (
        datetime.now(timezone.utc) - start
    ).total_seconds() * 1000
    
    return state


async def aggregate_signals(
    state: WorkflowState,
    signal_aggregation,
    signal_integration
) -> WorkflowState:
    """
    Aggregate real-time signals (#08).
    """
    
    start = datetime.now(timezone.utc)
    
    try:
        signals = await signal_aggregation.get_aggregated_signals(
            user_id=state["user_id"],
            session_id=state["session_context"].get("session_id")
        )
        
        state["aggregated_signals"] = signals
        
        # Register for learning
        await signal_integration.register_signal_contribution(
            decision_id=state["decision_id"],
            signals=signals.get("signals", []),
            derived_features=signals.get("features", {})
        )
        
    except Exception as e:
        logger.error(f"Error aggregating signals: {e}")
        state["errors"].append(f"signal_aggregation: {str(e)}")
    
    state["node_timings"]["aggregate_signals"] = (
        datetime.now(timezone.utc) - start
    ).total_seconds() * 1000
    
    return state


async def get_journey_context(
    state: WorkflowState,
    journey_tracker
) -> WorkflowState:
    """
    Get journey context (#10).
    """
    
    start = datetime.now(timezone.utc)
    
    try:
        position = await journey_tracker.get_position(state["user_id"])
        windows = await journey_tracker.get_intervention_windows(state["user_id"])
        
        state["journey_state"] = position.state if position else None
        state["intervention_windows"] = windows or []
        
    except Exception as e:
        logger.error(f"Error getting journey context: {e}")
        state["errors"].append(f"journey: {str(e)}")
    
    state["node_timings"]["get_journey"] = (
        datetime.now(timezone.utc) - start
    ).total_seconds() * 1000
    
    return state


async def get_temporal_context(
    state: WorkflowState,
    temporal_patterns
) -> WorkflowState:
    """
    Get temporal context (#23).
    """
    
    start = datetime.now(timezone.utc)
    
    try:
        patterns = await temporal_patterns.get_user_patterns(state["user_id"])
        life_events = await temporal_patterns.detect_life_events(state["user_id"])
        
        state["temporal_patterns"] = patterns
        state["life_events"] = life_events or []
        
    except Exception as e:
        logger.error(f"Error getting temporal context: {e}")
        state["errors"].append(f"temporal: {str(e)}")
    
    state["node_timings"]["get_temporal"] = (
        datetime.now(timezone.utc) - start
    ).total_seconds() * 1000
    
    return state


async def get_advertising_psychology_context(
    state: WorkflowState,
    atom_knowledge_interface
) -> WorkflowState:
    """
    Get advertising psychology context from 200+ empirical findings.
    
    This node pulls:
    - Regulatory focus detection (OR = 2-6x CTR when matched)
    - Cognitive state estimation (d = 0.5-0.8 for load-reducing interventions)
    - Message frame recommendations (g = 0.475 for construal matching)
    
    The advertising psychology research integration enables:
    - Signal collection (linguistic, desktop, mobile)
    - Psychological construct inference
    - Message framing and timing optimization
    - Memory optimization (spacing, peak-end)
    - Social and values-based targeting
    """
    
    start = datetime.now(timezone.utc)
    
    try:
        # Get user texts from session context for linguistic analysis
        user_texts = state.get("session_context", {}).get("user_texts", [])
        
        # Get behavioral signals from aggregated signals
        behavioral_signals = state.get("aggregated_signals", {}).get("features", {})
        
        # Get current hour for circadian matching
        current_hour = datetime.now().hour
        
        # Session duration for fatigue estimation
        session_start = state.get("session_context", {}).get("start_time")
        session_duration = 0.0
        if session_start:
            session_duration = (datetime.now(timezone.utc) - session_start).total_seconds() / 60.0
        
        # Get comprehensive advertising psychology profile
        adv_psych_profile = await atom_knowledge_interface.get_advertising_psychology_context(
            user_id=state["user_id"],
            session_id=state.get("session_context", {}).get("session_id", state["request_id"]),
            user_texts=user_texts if user_texts else None,
            behavioral_signals=behavioral_signals if behavioral_signals else None,
            hour=current_hour,
            session_duration_minutes=session_duration,
            chronotype=state.get("graph_context", {}).get("chronotype", "neutral"),
        )
        
        state["advertising_psychology_context"] = adv_psych_profile.model_dump() if hasattr(adv_psych_profile, "model_dump") else {}
        
        # Get specific regulatory focus context
        reg_focus = await atom_knowledge_interface.get_regulatory_focus_context(
            user_id=state["user_id"],
            session_id=state.get("session_context", {}).get("session_id", state["request_id"]),
            user_texts=user_texts if user_texts else None,
            behavioral_signals=behavioral_signals if behavioral_signals else None,
        )
        state["regulatory_focus_context"] = reg_focus.to_dict() if hasattr(reg_focus, "to_dict") else {}
        
        # Get cognitive state context
        cog_state = await atom_knowledge_interface.get_cognitive_state_context(
            user_id=state["user_id"],
            session_id=state.get("session_context", {}).get("session_id", state["request_id"]),
            hour=current_hour,
            session_duration_minutes=session_duration,
            chronotype=state.get("graph_context", {}).get("chronotype", "neutral"),
            behavioral_signals=behavioral_signals if behavioral_signals else None,
        )
        state["cognitive_state_context"] = cog_state.to_dict() if hasattr(cog_state, "to_dict") else {}
        
        # Get message frame recommendations with funnel stage
        funnel_stage = state.get("session_context", {}).get("funnel_stage", "consideration")
        message_recs = await atom_knowledge_interface.get_message_frame_recommendations(
            user_id=state["user_id"],
            session_id=state.get("session_context", {}).get("session_id", state["request_id"]),
            regulatory_focus=reg_focus.focus_type if hasattr(reg_focus, 'focus_type') else None,
            funnel_stage=funnel_stage,
        )
        state["message_frame_recommendations"] = message_recs
        
        logger.info(
            f"Advertising psychology context for user {state['user_id']}: "
            f"regulatory_focus={reg_focus.focus_type if hasattr(reg_focus, 'focus_type') else 'unknown'}, "
            f"cognitive_load={cog_state.cognitive_load if hasattr(cog_state, 'cognitive_load') else 0.5:.2f}, "
            f"recommended_frame={message_recs.get('recommended_frame', 'unknown')}"
        )
        
    except Exception as e:
        logger.error(f"Error getting advertising psychology context: {e}")
        state["errors"].append(f"adv_psychology: {str(e)}")
        state["advertising_psychology_context"] = None
        state["regulatory_focus_context"] = None
        state["cognitive_state_context"] = None
        state["message_frame_recommendations"] = None
    
    state["node_timings"]["get_adv_psychology"] = (
        datetime.now(timezone.utc) - start
    ).total_seconds() * 1000
    
    return state


async def get_brand_context(
    state: WorkflowState,
    brand_library
) -> WorkflowState:
    """
    Get brand context (#14).
    
    Enhanced with Brand-as-Person integration - pulls full brand personality
    profile from Neo4j including:
    - Brand archetype (Jung/Mark)
    - Aaker brand personality dimensions
    - Brand-consumer relationship role
    - Brand voice characteristics
    """
    
    start = datetime.now(timezone.utc)
    
    try:
        brand_id = state.get("brand_id")
        
        if brand_id:
            # Get legacy brand constraints/voice
            brand = await brand_library.get_brand(brand_id)
            state["brand_constraints"] = brand.constraints if brand else []
            state["brand_voice"] = brand.voice if brand else None
            
            # =====================================================================
            # BRAND PERSONALITY PROFILE (NEW - Brand-as-Person Integration)
            # =====================================================================
            try:
                from adam.intelligence.knowledge_graph.brand_graph_builder import (
                    get_brand_graph_builder,
                )
                # Get Neo4j driver from brand_library or create new connection
                driver = getattr(brand_library, 'driver', None)
                if driver:
                    builder = await get_brand_graph_builder(driver)
                    profile_data = await builder.get_brand_profile(brand_id)
                    
                    if profile_data:
                        state["brand_personality_profile"] = profile_data
                        state["brand_archetype"] = profile_data.get("brand_archetype")
                        state["brand_aaker_dimensions"] = {
                            "sincerity": profile_data.get("aaker_sincerity", 0.5),
                            "excitement": profile_data.get("aaker_excitement", 0.5),
                            "competence": profile_data.get("aaker_competence", 0.5),
                            "sophistication": profile_data.get("aaker_sophistication", 0.5),
                            "ruggedness": profile_data.get("aaker_ruggedness", 0.5),
                        }
                        state["brand_relationship_role"] = profile_data.get("relationship_role")
                        state["brand_voice_characteristics"] = {
                            "formality": profile_data.get("voice_formality", 0.5),
                            "energy": profile_data.get("voice_energy", 0.5),
                            "humor": profile_data.get("voice_humor", 0.3),
                            "directness": profile_data.get("voice_directness", 0.5),
                        }
                        logger.debug(
                            f"Loaded brand personality for {brand_id}: "
                            f"archetype={state['brand_archetype']}"
                        )
                    else:
                        state["brand_personality_profile"] = None
                        state["brand_archetype"] = None
                        state["brand_aaker_dimensions"] = None
                        state["brand_relationship_role"] = None
                        state["brand_voice_characteristics"] = None
                else:
                    logger.debug("No Neo4j driver available for brand personality")
                    state["brand_personality_profile"] = None
                    state["brand_archetype"] = None
                    state["brand_aaker_dimensions"] = None
                    state["brand_relationship_role"] = None
                    state["brand_voice_characteristics"] = None
                    
            except ImportError:
                logger.debug("Brand graph builder not available")
                state["brand_personality_profile"] = None
                state["brand_archetype"] = None
                state["brand_aaker_dimensions"] = None
                state["brand_relationship_role"] = None
                state["brand_voice_characteristics"] = None
            except Exception as e:
                logger.warning(f"Could not load brand personality: {e}")
                state["brand_personality_profile"] = None
                state["brand_archetype"] = None
                state["brand_aaker_dimensions"] = None
                state["brand_relationship_role"] = None
                state["brand_voice_characteristics"] = None
        else:
            state["brand_constraints"] = []
            state["brand_voice"] = None
            state["brand_personality_profile"] = None
            state["brand_archetype"] = None
            state["brand_aaker_dimensions"] = None
            state["brand_relationship_role"] = None
            state["brand_voice_characteristics"] = None
            
    except Exception as e:
        logger.error(f"Error getting brand context: {e}")
        state["errors"].append(f"brand: {str(e)}")
    
    state["node_timings"]["get_brand"] = (
        datetime.now(timezone.utc) - start
    ).total_seconds() * 1000
    
    return state


async def get_competitive_context(
    state: WorkflowState,
    competitive_intel
) -> WorkflowState:
    """
    Get competitive context (#22).
    """
    
    start = datetime.now(timezone.utc)
    
    try:
        landscape = await competitive_intel.get_landscape(state.get("category_id"))
        state["competitive_landscape"] = landscape
        
    except Exception as e:
        logger.error(f"Error getting competitive context: {e}")
        state["errors"].append(f"competitive: {str(e)}")
    
    state["node_timings"]["get_competitive"] = (
        datetime.now(timezone.utc) - start
    ).total_seconds() * 1000
    
    return state


async def get_predictive_processing_context(
    state: WorkflowState,
    predictive_engine
) -> WorkflowState:
    """
    Get curiosity scores and precision-weighted recommendations from Predictive Processing.
    
    Uses the Free Energy Principle to balance:
    - Pragmatic value (expected reward)
    - Epistemic value (information gain from showing ad)
    """
    
    start = datetime.now(timezone.utc)
    
    try:
        # Get or create belief state for user
        belief_state = predictive_engine.get_or_create_belief_state(state["user_id"])
        
        # Calculate curiosity scores for each ad candidate
        curiosity_scores = {}
        for i, candidate in enumerate(state.get("ad_candidates", [])):
            ad_features = candidate.get("features", {})
            curiosity = predictive_engine.get_curiosity_score(
                state["user_id"],
                ad_features
            )
            curiosity_scores[f"ad_{i}"] = curiosity
        
        state["curiosity_scores"] = curiosity_scores
        
        logger.debug(
            f"Predictive processing for user {state['user_id']}: "
            f"belief_uncertainty={belief_state.total_uncertainty:.2f}, "
            f"avg_curiosity={sum(curiosity_scores.values())/max(1, len(curiosity_scores)):.3f}"
        )
        
    except Exception as e:
        logger.error(f"Error in predictive processing: {e}")
        state["errors"].append(f"predictive_processing: {str(e)}")
        state["curiosity_scores"] = None
    
    state["node_timings"]["get_predictive_processing"] = (
        datetime.now(timezone.utc) - start
    ).total_seconds() * 1000
    
    return state


async def enhanced_meta_learner_routing(
    state: WorkflowState,
    neural_thompson_engine,
    meta_learner_integration
) -> WorkflowState:
    """
    Enhanced Meta-Learner routing using Neural Thompson Sampling.
    
    Uses context-aware neural network uncertainty for smarter exploration.
    Replaces standard Thompson Sampling with learned exploration.
    """
    
    start = datetime.now(timezone.utc)
    
    try:
        # Build context features
        context_features = {
            "user_data_richness": _compute_data_richness(state.get("graph_context")),
            "has_conversion_history": float(bool(state.get("graph_context", {}).get("conversion_history"))),
            "category_novelty": _compute_category_novelty(state.get("category_id"), state.get("graph_context")),
            "session_depth": float(len(state.get("session_context", {}).get("events", []))),
            "hour_of_day": float(datetime.now().hour) / 24.0,
            "cognitive_load": state.get("cognitive_state_context", {}).get("cognitive_load", 0.5),
        }
        
        # Add curiosity scores if available
        if state.get("curiosity_scores"):
            avg_curiosity = sum(state["curiosity_scores"].values()) / max(1, len(state["curiosity_scores"]))
            context_features["avg_curiosity"] = avg_curiosity
        
        # Neural Thompson selection
        selected_modality, prediction = await neural_thompson_engine.select_modality(
            context_features
        )
        
        state["neural_thompson_selection"] = {
            "modality": selected_modality.value,
            "expected_reward": prediction.expected_reward,
            "uncertainty": prediction.uncertainty,
            "exploration_bonus": prediction.exploration_bonus,
        }
        
        # Map to execution path
        if "fast" in selected_modality.value.lower() or prediction.expected_reward > 0.8:
            state["selected_path"] = ExecutionPath.FAST
        elif "explore" in selected_modality.value.lower() or prediction.uncertainty > 0.3:
            state["selected_path"] = ExecutionPath.EXPLORE
        else:
            state["selected_path"] = ExecutionPath.REASONING
        
        state["selected_modality"] = selected_modality.value
        state["routing_confidence"] = 1.0 - prediction.uncertainty
        
        # Register for learning
        if meta_learner_integration:
            await meta_learner_integration.register_routing_decision(
                decision_id=state["decision_id"],
                user_id=state["user_id"],
                context=context_features,
                selected_modality=selected_modality.value,
                selected_path=state["selected_path"].value,
                selection_confidence=state["routing_confidence"]
            )
        
        logger.info(
            f"Neural Thompson routing for {state['user_id']}: "
            f"{selected_modality.value} → {state['selected_path'].value} "
            f"(uncertainty={prediction.uncertainty:.3f})"
        )
        
    except Exception as e:
        logger.error(f"Error in Neural Thompson routing: {e}")
        state["selected_path"] = ExecutionPath.REASONING  # Default fallback
        state["errors"].append(f"neural_thompson: {str(e)}")
    
    state["node_timings"]["neural_thompson_routing"] = (
        datetime.now(timezone.utc) - start
    ).total_seconds() * 1000
    
    return state


async def record_for_emergence(
    state: WorkflowState,
    emergence_engine
) -> WorkflowState:
    """
    Record prediction for the Emergence Engine.
    
    Feeds predictions and outcomes to the engine so it can
    detect unexplained variance and discover novel constructs.
    """
    
    start = datetime.now(timezone.utc)
    
    try:
        # Build feature vector from state
        features = {}
        
        # Include regulatory focus if available
        if state.get("regulatory_focus_context"):
            rf = state["regulatory_focus_context"]
            features["regulatory_focus_strength"] = rf.get("focus_strength", 0.5)
            features["is_promotion_focus"] = 1.0 if rf.get("focus_type") == "promotion" else 0.0
        
        # Include cognitive state
        if state.get("cognitive_state_context"):
            cs = state["cognitive_state_context"]
            features["cognitive_load"] = cs.get("cognitive_load", 0.5)
        
        # Include curiosity if available
        if state.get("curiosity_scores"):
            features["avg_curiosity"] = sum(state["curiosity_scores"].values()) / max(1, len(state["curiosity_scores"]))
        
        # Get predicted outcome from synthesis
        predicted = state.get("holistic_decision", {}).get("decision_confidence", 0.5)
        
        # Record for emergence engine (observed will be updated on outcome)
        emergence_engine.record_prediction(
            features=features,
            predicted=predicted,
            observed=predicted,  # Will be updated when actual outcome arrives
            decision_id=state["decision_id"],
            user_id=state["user_id"],
        )
        
        # Check if any emergent constructs apply
        promoted_constructs = emergence_engine.get_promoted_constructs()
        if promoted_constructs:
            construct_matches = []
            for construct in promoted_constructs[:5]:  # Limit to top 5
                enhanced = emergence_engine.apply_construct_to_features(features, construct)
                membership_key = f"emergent_{construct.construct_id}"
                if membership_key in enhanced and enhanced[membership_key] > 0.5:
                    construct_matches.append({
                        "construct_id": construct.construct_id,
                        "name": construct.name,
                        "membership": enhanced[membership_key],
                    })
            state["emergent_constructs"] = construct_matches
        else:
            state["emergent_constructs"] = []
        
    except Exception as e:
        logger.error(f"Error recording for emergence: {e}")
        state["errors"].append(f"emergence: {str(e)}")
        state["emergent_constructs"] = []
    
    state["node_timings"]["record_emergence"] = (
        datetime.now(timezone.utc) - start
    ).total_seconds() * 1000
    
    return state


async def holistic_synthesis(
    state: WorkflowState,
    holistic_synthesizer
) -> WorkflowState:
    """
    Holistic Decision Synthesis - the executive function.
    
    This is where ALL intelligence sources are fused into a
    coherent, optimal decision.
    """
    
    start = datetime.now(timezone.utc)
    
    try:
        decision = await holistic_synthesizer.synthesize(
            request_id=state["request_id"],
            user_id=state["user_id"],
            atom_outputs=state.get("atom_outputs", {}),
            ad_candidates=state.get("ad_candidates", []),
            category_id=state.get("category_id"),
            brand_id=state.get("brand_id"),
        )
        
        state["holistic_decision"] = decision.model_dump() if hasattr(decision, "model_dump") else decision
        
    except Exception as e:
        logger.error(f"Error in holistic synthesis: {e}")
        state["errors"].append(f"synthesis: {str(e)}")
    
    state["node_timings"]["holistic_synthesis"] = (
        datetime.now(timezone.utc) - start
    ).total_seconds() * 1000
    
    return state


async def propagate_learning(
    state: WorkflowState,
    learning_signal_router
) -> WorkflowState:
    """
    Propagate learning signals to all components.
    
    This ensures that when an outcome is observed, every component learns.
    """
    
    start = datetime.now(timezone.utc)
    
    try:
        # Learning happens asynchronously when outcome is observed
        # Here we just prepare the decision context for later learning
        
        from adam.core.learning.universal_learning_interface import LearningSignal, LearningSignalType
        
        # Emit decision-made signal
        decision_signal = LearningSignal(
            signal_type=LearningSignalType.CREDIT_ASSIGNED,
            source_component="workflow",
            decision_id=state["decision_id"],
            user_id=state["user_id"],
            payload={
                "path_taken": state.get("selected_path", "unknown"),
                "atoms_executed": list(state.get("atom_outputs", {}).keys()),
                "synthesis_confidence": state.get("holistic_decision", {}).get("decision_confidence", 0.5),
            },
            confidence=1.0
        )
        
        state["learning_signals"].append(decision_signal.model_dump())
        
    except Exception as e:
        logger.error(f"Error preparing learning: {e}")
        state["errors"].append(f"learning: {str(e)}")
    
    state["node_timings"]["propagate_learning"] = (
        datetime.now(timezone.utc) - start
    ).total_seconds() * 1000
    
    return state


def determine_path(state: WorkflowState) -> str:
    """
    Conditional routing based on Meta-Learner decision.
    """
    
    path = state.get("selected_path", ExecutionPath.REASONING)
    
    if path == ExecutionPath.FAST:
        return "fast_path"
    elif path == ExecutionPath.EXPLORE:
        return "explore_path"
    else:
        return "reasoning_path"


# =============================================================================
# WORKFLOW BUILDER
# =============================================================================

def create_holistic_decision_workflow(
    interaction_bridge,
    blackboard_service,
    meta_learner,
    meta_learner_integration,
    atom_executor,
    atom_integration,
    signal_aggregation,
    signal_integration,
    journey_tracker,
    temporal_patterns,
    brand_library,
    competitive_intel,
    holistic_synthesizer,
    learning_signal_router,
    cache_service,
    archetype_service,
    bandit_service,
    atom_knowledge_interface=None,  # Advertising psychology
    # New: Emergent Intelligence Engines
    neural_thompson_engine=None,     # Context-aware exploration
    predictive_engine=None,          # Predictive processing / curiosity
    emergence_engine=None,           # Novel construct discovery
    use_enhanced_routing: bool = True,  # Feature flag
) -> StateGraph:
    """
    Create the complete Holistic Decision Workflow.
    
    This is the main entry point for building the LangGraph workflow.
    
    New in v2.0:
    - Neural Thompson Sampling for context-aware exploration
    - Predictive Processing for curiosity-driven selection
    - Emergence Engine for novel construct discovery
    """
    
    # Create state graph
    workflow = StateGraph(WorkflowState)
    
    # =========================================================================
    # ADD NODES (Using proper async handling - no event loop blocking)
    # =========================================================================
    
    # Phase 1: Context Gathering (parallel where possible)
    # NOTE: LangGraph natively supports async nodes - we use create_async_node
    # to properly bind dependencies without blocking the event loop
    
    workflow.add_node("initialize", initialize_state)
    
    workflow.add_node("pull_graph_context", 
        create_async_node(pull_graph_context, interaction_bridge=interaction_bridge)
    )
    
    workflow.add_node("get_blackboard",
        create_async_node(get_blackboard_state, blackboard_service=blackboard_service)
    )
    
    workflow.add_node("aggregate_signals",
        create_async_node(aggregate_signals, 
            signal_aggregation=signal_aggregation,
            signal_integration=signal_integration)
    )
    
    workflow.add_node("get_journey",
        create_async_node(get_journey_context, journey_tracker=journey_tracker)
    )
    
    workflow.add_node("get_temporal",
        create_async_node(get_temporal_context, temporal_patterns=temporal_patterns)
    )
    
    workflow.add_node("get_brand",
        create_async_node(get_brand_context, brand_library=brand_library)
    )
    
    workflow.add_node("get_competitive",
        create_async_node(get_competitive_context, competitive_intel=competitive_intel)
    )
    
    # Advertising Psychology Context (Research Integration)
    if atom_knowledge_interface:
        workflow.add_node("get_adv_psychology",
            create_async_node(get_advertising_psychology_context, 
                atom_knowledge_interface=atom_knowledge_interface)
        )
    
    # Susceptibility Intelligence Context (Persuasion Susceptibility Analysis)
    # This adds 13 research-backed susceptibility constructs for mechanism prediction
    from adam.workflows.susceptibility_intelligence_node import (
        analyze_susceptibility_intelligence,
        create_susceptibility_intelligence_node,
    )
    workflow.add_node("get_susceptibility_intelligence",
        create_async_node(analyze_susceptibility_intelligence, neo4j_driver=None)
    )
    
    # Phase 2: Routing
    workflow.add_node("meta_learner_routing",
        create_async_node(meta_learner_routing, 
            meta_learner=meta_learner,
            meta_learner_integration=meta_learner_integration)
    )
    
    # Phase 3: Path Execution (conditional)
    workflow.add_node("fast_path",
        create_async_node(execute_fast_path, 
            cache_service=cache_service,
            archetype_service=archetype_service)
    )
    
    workflow.add_node("reasoning_path",
        create_async_node(execute_reasoning_path, 
            atom_executor=atom_executor,
            atom_integration=atom_integration)
    )
    
    workflow.add_node("explore_path",
        create_async_node(execute_explore_path, bandit_service=bandit_service)
    )
    
    # Phase 3.5: Predictive Processing (curiosity scoring)
    if predictive_engine:
        workflow.add_node("get_predictive_processing",
            create_async_node(get_predictive_processing_context,
                predictive_engine=predictive_engine)
        )
    
    # Phase 2.5: Enhanced Routing with Neural Thompson
    if neural_thompson_engine and use_enhanced_routing:
        workflow.add_node("neural_thompson_routing",
            create_async_node(enhanced_meta_learner_routing,
                neural_thompson_engine=neural_thompson_engine,
                meta_learner_integration=meta_learner_integration)
        )
    
    # Phase 4: Synthesis
    workflow.add_node("holistic_synthesis",
        create_async_node(holistic_synthesis, holistic_synthesizer=holistic_synthesizer)
    )
    
    # Phase 4.5: Emergence Recording
    if emergence_engine:
        workflow.add_node("record_emergence",
            create_async_node(record_for_emergence,
                emergence_engine=emergence_engine)
        )
    
    # Phase 5: Learning
    workflow.add_node("propagate_learning",
        create_async_node(propagate_learning, learning_signal_router=learning_signal_router)
    )
    
    # =========================================================================
    # ADD EDGES
    # =========================================================================
    
    # Entry
    workflow.set_entry_point("initialize")
    
    # Initialize → Context gathering (parallel fanout)
    workflow.add_edge("initialize", "pull_graph_context")
    workflow.add_edge("initialize", "get_blackboard")
    workflow.add_edge("initialize", "aggregate_signals")
    workflow.add_edge("initialize", "get_journey")
    workflow.add_edge("initialize", "get_temporal")
    workflow.add_edge("initialize", "get_brand")
    workflow.add_edge("initialize", "get_competitive")
    
    # Advertising Psychology Context - runs after signals are aggregated
    if atom_knowledge_interface:
        workflow.add_edge("aggregate_signals", "get_adv_psychology")
    
    # Susceptibility Intelligence - runs after signals, enriches mechanism predictions
    workflow.add_edge("aggregate_signals", "get_susceptibility_intelligence")
    
    # Determine routing node based on feature flags
    routing_node = "neural_thompson_routing" if (neural_thompson_engine and use_enhanced_routing) else "meta_learner_routing"
    
    # Context gathering → Predictive Processing (if enabled) → Routing
    if predictive_engine:
        # Signals flow to predictive processing
        workflow.add_edge("aggregate_signals", "get_predictive_processing")
        workflow.add_edge("get_predictive_processing", routing_node)
        
        # Other contexts go directly to routing
        workflow.add_edge("pull_graph_context", routing_node)
        workflow.add_edge("get_blackboard", routing_node)
        workflow.add_edge("get_journey", routing_node)
        workflow.add_edge("get_temporal", routing_node)
        workflow.add_edge("get_brand", routing_node)
        workflow.add_edge("get_competitive", routing_node)
    else:
        # Standard context → routing flow
        workflow.add_edge("pull_graph_context", routing_node)
        workflow.add_edge("get_blackboard", routing_node)
        workflow.add_edge("aggregate_signals", routing_node)
        workflow.add_edge("get_journey", routing_node)
        workflow.add_edge("get_temporal", routing_node)
        workflow.add_edge("get_brand", routing_node)
        workflow.add_edge("get_competitive", routing_node)
    
    # Advertising psychology feeds into routing
    if atom_knowledge_interface:
        workflow.add_edge("get_adv_psychology", routing_node)
    
    # Susceptibility intelligence feeds into routing
    workflow.add_edge("get_susceptibility_intelligence", routing_node)
    
    # Neural Thompson or standard Meta-Learner → Conditional path selection
    workflow.add_conditional_edges(
        routing_node,
        determine_path,
        {
            "fast_path": "fast_path",
            "reasoning_path": "reasoning_path",
            "explore_path": "explore_path",
        }
    )
    
    # All paths → Synthesis
    workflow.add_edge("fast_path", "holistic_synthesis")
    workflow.add_edge("reasoning_path", "holistic_synthesis")
    workflow.add_edge("explore_path", "holistic_synthesis")
    
    # Synthesis → Emergence Recording (if enabled) → Learning → End
    if emergence_engine:
        workflow.add_edge("holistic_synthesis", "record_emergence")
        workflow.add_edge("record_emergence", "propagate_learning")
    else:
        workflow.add_edge("holistic_synthesis", "propagate_learning")
    
    workflow.add_edge("propagate_learning", END)
    
    return workflow


# =============================================================================
# WORKFLOW EXECUTOR
# =============================================================================

class HolisticDecisionWorkflowExecutor:
    """
    Executor for the Holistic Decision Workflow.
    
    This wraps the LangGraph workflow with initialization and execution helpers.
    
    New in v2.0:
    - Neural Thompson Sampling for smarter exploration
    - Predictive Processing for curiosity-driven selection
    - Emergence Engine for novel construct discovery
    
    New in v3.0 (Full Intelligence Utilization):
    - FullIntelligenceIntegrator for 100% capability usage
    - All intelligence sources contribute to every decision
    """
    
    def __init__(
        self,
        interaction_bridge,
        blackboard_service,
        meta_learner,
        meta_learner_integration,
        atom_executor,
        atom_integration,
        signal_aggregation,
        signal_integration,
        journey_tracker,
        temporal_patterns,
        brand_library,
        competitive_intel,
        holistic_synthesizer,
        learning_signal_router,
        cache_service,
        archetype_service,
        bandit_service,
        atom_knowledge_interface=None,  # Advertising psychology
        # New: Emergent Intelligence Engines
        neural_thompson_engine=None,
        predictive_engine=None,
        emergence_engine=None,
        use_enhanced_routing: bool = True,
        # v3.0: Full Intelligence Integration
        full_intelligence_integrator=None,
    ):
        self.workflow = create_holistic_decision_workflow(
            interaction_bridge=interaction_bridge,
            blackboard_service=blackboard_service,
            meta_learner=meta_learner,
            meta_learner_integration=meta_learner_integration,
            atom_executor=atom_executor,
            atom_integration=atom_integration,
            signal_aggregation=signal_aggregation,
            signal_integration=signal_integration,
            journey_tracker=journey_tracker,
            temporal_patterns=temporal_patterns,
            brand_library=brand_library,
            competitive_intel=competitive_intel,
            holistic_synthesizer=holistic_synthesizer,
            learning_signal_router=learning_signal_router,
            cache_service=cache_service,
            archetype_service=archetype_service,
            bandit_service=bandit_service,
            atom_knowledge_interface=atom_knowledge_interface,
            # New: Emergent Intelligence Engines
            neural_thompson_engine=neural_thompson_engine,
            predictive_engine=predictive_engine,
            emergence_engine=emergence_engine,
            use_enhanced_routing=use_enhanced_routing,
        )
        
        self.compiled = self.workflow.compile(checkpointer=MemorySaver())
        
        # v3.0: Store full intelligence integrator for pre-decision intelligence gathering
        self.full_intelligence_integrator = full_intelligence_integrator
    
    async def execute(
        self,
        request_id: str,
        user_id: str,
        ad_candidates: List[Dict[str, Any]],
        category_id: Optional[str] = None,
        brand_id: Optional[str] = None,
        session_context: Optional[Dict[str, Any]] = None,
        # v3.0: Additional context for full intelligence
        brand_name: Optional[str] = None,
        product_name: Optional[str] = None,
        brand_description: Optional[str] = None,
        reviews: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the workflow for a single request.
        
        v3.0: Now builds FullIntelligenceProfile before workflow execution.
        This ensures all intelligence sources contribute to the decision.
        
        Returns the holistic decision.
        """
        
        # v3.0: Build full intelligence profile if integrator is available
        full_intelligence_profile = None
        if self.full_intelligence_integrator and (brand_name or product_name):
            try:
                full_intelligence_profile = await self.full_intelligence_integrator.build_full_profile(
                    brand_name=brand_name or "",
                    product_name=product_name or "",
                    category=category_id or "",
                    brand_description=brand_description,
                    reviews=reviews,
                    customer_signals=session_context,
                )
                logger.info(
                    f"Built full intelligence profile: "
                    f"coverage={full_intelligence_profile.intelligence_coverage:.1%}, "
                    f"confidence={full_intelligence_profile.overall_confidence:.2f}"
                )
            except Exception as e:
                logger.warning(f"Failed to build full intelligence profile: {e}")
        
        initial_state = {
            "request_id": request_id,
            "user_id": user_id,
            "ad_candidates": ad_candidates,
            "category_id": category_id,
            "brand_id": brand_id,
            "session_context": session_context or {},
            # v3.0: Include full intelligence in state
            "full_intelligence_profile": (
                full_intelligence_profile.to_dict() 
                if full_intelligence_profile else None
            ),
        }
        
        config = {"configurable": {"thread_id": request_id}}
        
        result = await self.compiled.ainvoke(initial_state, config)
        
        return {
            "decision": result.get("holistic_decision"),
            "decision_id": result.get("decision_id"),
            "path_taken": result.get("selected_path"),
            "timings": result.get("node_timings"),
            "errors": result.get("errors"),
            # v3.0: Include intelligence utilization metrics
            "intelligence_coverage": (
                full_intelligence_profile.intelligence_coverage 
                if full_intelligence_profile else 0.0
            ),
            "intelligence_confidence": (
                full_intelligence_profile.overall_confidence
                if full_intelligence_profile else 0.0
            ),
        }


# =============================================================================
# OUTCOME HANDLER
# =============================================================================

class OutcomeHandler:
    """
    Handles outcomes and triggers learning across all components.
    """
    
    def __init__(
        self,
        learning_registry,
        gradient_bridge_integration,
        learning_signal_router
    ):
        self.learning_registry = learning_registry
        self.gradient_bridge_integration = gradient_bridge_integration
        self.learning_signal_router = learning_signal_router
    
    async def handle_outcome(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any]
    ) -> int:
        """
        Handle an observed outcome.
        
        This triggers learning across ALL registered components.
        
        Returns:
            Number of learning signals propagated
        """
        
        all_signals = []
        
        # 1. Gradient Bridge processes first (computes attribution)
        gb_signals = await self.gradient_bridge_integration.on_outcome_received(
            decision_id=decision_id,
            outcome_type=outcome_type,
            outcome_value=outcome_value,
            context=context
        )
        all_signals.extend(gb_signals)
        
        # 2. All other components process
        for component in self.learning_registry.all_components():
            if component.component_name == "gradient_bridge":
                continue  # Already processed
            
            try:
                signals = await component.on_outcome_received(
                    decision_id=decision_id,
                    outcome_type=outcome_type,
                    outcome_value=outcome_value,
                    context=context
                )
                all_signals.extend(signals)
            except Exception as e:
                logger.error(f"Error in {component.component_name} outcome processing: {e}")
        
        # 3. Route all signals
        routed_count = 0
        for signal in all_signals:
            from adam.core.learning.universal_learning_interface import LearningSignal
            if isinstance(signal, dict):
                signal = LearningSignal(**signal)
            count = await self.learning_signal_router.route_signal(signal)
            routed_count += count
        
        return routed_count
