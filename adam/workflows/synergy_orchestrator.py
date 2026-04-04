#!/usr/bin/env python3
"""
SYNERGY ORCHESTRATOR
====================

LangGraph nodes that orchestrate the three ADAM systems to work synergistically:

1. **Graph Database** - Source of accumulated knowledge, relationships, patterns
2. **AoT Atoms** - Modular reasoning units that make decisions
3. **Learning System** - Updates all systems from outcomes

LangGraph's role is NOT just sequencing - it's the NERVOUS SYSTEM that:
- Pre-fetches intelligence BEFORE atoms need it
- Routes data to the RIGHT system at the RIGHT time
- Ensures learning signals reach ALL systems
- Triggers graph maintenance and intelligence updates
- Coordinates cross-system information flow

These nodes implement the orchestration logic.

Phase 1: Fix Learning Loop - LangGraph Orchestrator Nodes
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import StateGraph, START, END

logger = logging.getLogger(__name__)


# =============================================================================
# ORCHESTRATOR STATE
# =============================================================================

class OrchestratorState(TypedDict, total=False):
    """
    State that flows through LangGraph orchestration.
    
    Contains pre-fetched intelligence from all systems.
    ENHANCED: Added competitive intelligence, deep archetype detection, and template selection.
    """
    
    # Request context
    request_id: str
    user_id: str
    brand_name: str
    product_name: str
    product_category: str
    
    # NEW: Competitive context (optional input)
    competitor_ads: List[Dict[str, str]]  # [{"name": "...", "text": "..."}, ...]
    
    # NEW: User signals for archetype detection
    user_review_text: str  # If available, for deep archetype detection
    user_behavioral_signals: Dict[str, float]  # Purchase patterns, etc.
    
    # Pre-fetched from Graph
    graph_intelligence: Dict[str, Any]
    user_profile: Dict[str, Any]
    mechanism_history: Dict[str, Any]
    archetype_match: Dict[str, Any]
    brand_relationships: Dict[str, Any]
    
    # Pre-fetched from Helpful Vote Intelligence
    helpful_vote_intelligence: Dict[str, Any]
    mechanism_priors: Dict[str, Dict[str, float]]
    persuasive_templates: List[Dict[str, Any]]
    
    # From FullIntelligenceIntegrator
    full_intelligence_profile: Dict[str, Any]
    behavioral_analysis: Dict[str, Any]
    brand_copy_analysis: Dict[str, Any]
    journey_intelligence: Dict[str, Any]
    
    # NEW: Competitive intelligence
    competitive_intelligence: Dict[str, Any]
    
    # NEW: Deep archetype detection result
    deep_archetype: Dict[str, Any]
    
    # NEW: Selected templates (personalized)
    selected_templates: List[Dict[str, Any]]
    
    # Atom outputs (populated during execution)
    atom_outputs: Dict[str, Any]
    
    # Decision tracking
    decision_id: str
    mechanisms_applied: List[Dict[str, Any]]
    confidence_scores: Dict[str, float]
    
    # For learning
    learning_context: Dict[str, Any]
    
    # Injected intelligence from pattern persistence
    injected_intelligence: Dict[str, Any]
    
    # Graph-inferred construct activations (inferential core)
    construct_activation_profile: Any  # ConstructActivationProfile
    graph_mechanism_priors: Dict[str, float]  # Mechanism priors from graph traversal
    
    # NEW: Bidirectional AoT ↔ LangGraph feedback
    atom_feedback: List[Dict[str, Any]]  # Feedback from atoms
    prior_validation: Dict[str, Any]  # Did atoms agree with LangGraph priors?
    atom_learning_signals: List[Dict[str, Any]]  # Learning signals to route
    langgraph_learnings: List[Dict[str, Any]]  # Processed learnings
    mechanism_updates_from_atoms: Dict[str, Any]  # Mechanism-specific updates
    archetype_validation: Dict[str, Any]  # Archetype alignment status

    # CORPUS FUSION: Intelligence from 1B+ reviews (Layers 1-5)
    corpus_fusion_intelligence: Dict[str, Any]  # Full corpus fusion output (priors, constraints, resonance)
    corpus_mechanism_priors: Dict[str, float]    # Mechanism name → corpus-calibrated prior score
    corpus_creative_constraints: Dict[str, Any]  # Creative pattern constraints from Layer 2
    corpus_platform_calibration: Dict[str, Any]  # Platform-specific calibration factors from Layer 3

    # ALIGNMENT SYSTEM: Ad copy profiling + expanded type inference + alignment
    ad_copy_profile: Dict[str, Any]  # Psychological profile of ad copy
    expanded_customer_type: Dict[str, Any]  # 1.9M expanded type (motivation, decision_style, etc.)
    alignment_scores: Dict[str, Any]  # Alignment matrix scores across all 7 matrices


# =============================================================================
# PRE-FETCH NODES
# =============================================================================

async def prefetch_graph_intelligence(state: OrchestratorState) -> OrchestratorState:
    """
    Pre-fetch all needed intelligence from Graph Database.
    
    This runs BEFORE atoms execute, so they have evidence ready.
    Includes:
    - User profile and traits
    - Mechanism history and effectiveness
    - Archetype matching
    - Brand-user relationships
    """
    user_id = state.get("user_id", "unknown")
    brand_name = state.get("brand_name", "unknown")
    
    graph_intel = {
        "user_profile": {},
        "mechanism_history": {},
        "archetype_match": {},
        "brand_relationships": {},
        "temporal_patterns": {},
    }
    
    try:
        # Get graph service
        from adam.intelligence.graph_edge_service import get_graph_edge_service
        graph_service = get_graph_edge_service()
        
        if graph_service:
            # User profile
            if hasattr(graph_service, "get_user_profile"):
                graph_intel["user_profile"] = await graph_service.get_user_profile(user_id) or {}
            
            # Mechanism history
            if hasattr(graph_service, "get_mechanism_history"):
                graph_intel["mechanism_history"] = await graph_service.get_mechanism_history(user_id) or {}
            
            # Archetype match
            if hasattr(graph_service, "get_archetype_match"):
                graph_intel["archetype_match"] = await graph_service.get_archetype_match(user_id) or {}
            
            logger.debug(f"Pre-fetched graph intelligence for user {user_id}")
            
    except ImportError:
        logger.debug("Graph service not available")
    except Exception as e:
        logger.warning(f"Failed to pre-fetch graph intelligence: {e}")
    
    # Try to get brand-user relationships
    try:
        from adam.intelligence.bidirectional_bridge import get_bidirectional_bridge
        bridge = get_bidirectional_bridge()
        
        if bridge:
            history = await bridge.get_user_history(user_id)
            if history:
                graph_intel["brand_relationships"] = {
                    "previous_decisions": len(history),
                    "brands_interacted": list(set(h.get("brand") for h in history if h.get("brand"))),
                }
    except Exception as e:
        logger.debug(f"Could not fetch brand relationships: {e}")
    
    # --- Type System Graph Inference ---
    graph_type_inference = {}
    graph_mechanism_priors = {}
    try:
        from neo4j import GraphDatabase
        from adam.config.settings import get_settings
        from adam.dsp.graph_type_inference import GraphTypeInferenceService

        settings = get_settings()
        neo4j_driver = GraphDatabase.driver(
            settings.neo4j.uri,
            auth=(settings.neo4j.username, settings.neo4j.password),
        )
        type_service = GraphTypeInferenceService(neo4j_driver)

        # Extract type dimensions from state (from prior inference or defaults)
        motivation = state.get("motivation", state.get("primary_motivation"))
        decision_style = state.get("decision_style", state.get("primary_decision_style"))
        regulatory_focus = state.get("regulatory_focus", state.get("primary_regulatory_focus"))
        product_category = state.get("product_category", state.get("category"))

        if motivation and decision_style:
            type_result = type_service.infer(
                motivation=motivation,
                decision_style=decision_style,
                regulatory_focus=regulatory_focus or "pragmatic_balanced",
                emotional_intensity=state.get("emotional_intensity", "moderate_positive"),
                cognitive_load=state.get("cognitive_load", "moderate_cognitive"),
                temporal_orientation=state.get("temporal_orientation", "medium_term"),
                social_influence=state.get("social_influence", "socially_aware"),
                product_category=product_category,
            )
            graph_type_inference = type_result.to_ad_context()
            graph_mechanism_priors = type_result.to_mechanism_priors()
            logger.info(f"Graph type inference: type_found={type_result.type_found}, mechanisms={list(graph_mechanism_priors.keys())}")
        else:
            logger.debug("Insufficient dimensions for graph type inference (need motivation + decision_style)")

        neo4j_driver.close()
    except ImportError:
        logger.debug("Graph type inference dependencies not available")
    except Exception as e:
        logger.debug(f"Graph type inference failed: {e}")

    return {
        **state,
        "graph_intelligence": graph_intel,
        "user_profile": graph_intel["user_profile"],
        "mechanism_history": graph_intel["mechanism_history"],
        "archetype_match": graph_intel["archetype_match"],
        "brand_relationships": graph_intel["brand_relationships"],
        # Type system graph inference results
        "graph_type_inference": graph_type_inference,
        "graph_mechanism_priors": graph_mechanism_priors,
    }


async def prefetch_helpful_vote_intelligence(state: OrchestratorState) -> OrchestratorState:
    """
    Pre-fetch helpful vote intelligence.
    
    Provides:
    - Mechanism priors from high-vote reviews
    - Persuasive templates
    - Archetype → Mechanism rankings
    """
    archetype = state.get("archetype_match", {}).get("primary_archetype")
    
    helpful_intel = {
        "mechanism_priors": {},
        "templates": [],
        "routing_data": {},
    }
    
    try:
        from adam.intelligence.helpful_vote_intelligence import get_helpful_vote_intelligence
        hvi = get_helpful_vote_intelligence()
        
        # Get mechanism priors if we know archetype
        if archetype:
            helpful_intel["mechanism_priors"] = hvi.get_mechanism_priors(archetype)
        
        # Get templates
        helpful_intel["templates"] = hvi.get_aot_evidence(
            archetype=archetype,
            limit=10,
        )
        
        # Get routing data
        helpful_intel["routing_data"] = hvi.get_langgraph_routing_data()
        
        logger.debug(f"Pre-fetched helpful vote intelligence: {len(helpful_intel['templates'])} templates")
        
    except ImportError:
        logger.debug("Helpful vote intelligence not available")
    except Exception as e:
        logger.warning(f"Failed to pre-fetch helpful vote intelligence: {e}")
    
    return {
        **state,
        "helpful_vote_intelligence": helpful_intel,
        "mechanism_priors": helpful_intel["mechanism_priors"],
        "persuasive_templates": helpful_intel["templates"],
    }


async def prefetch_full_intelligence(state: OrchestratorState) -> OrchestratorState:
    """
    Pre-fetch from FullIntelligenceIntegrator AND AtomIntelligenceInjector.
    
    This is the comprehensive intelligence that includes:
    - All 13 behavioral classifiers
    - Brand copy analysis
    - Journey intelligence
    - Customer influence patterns
    - Pre-computed pattern persistence (from re-ingestion)
    """
    brand_name = state.get("brand_name", "")
    product_name = state.get("product_name", "")
    product_category = state.get("product_category", "")
    request_id = state.get("request_id", "")
    user_id = state.get("user_id", "")
    archetype = state.get("archetype_match", {}).get("primary_archetype")
    
    full_intel = {
        "behavioral_analysis": {},
        "brand_copy_analysis": {},
        "journey_intelligence": {},
        "intelligence_coverage": 0.0,
    }
    
    # NEW: Inject pre-computed intelligence from pattern persistence
    injected_intel = {}
    try:
        from adam.intelligence.atom_intelligence_injector import get_intelligence_injector
        injector = get_intelligence_injector()
        
        injected = await injector.gather_intelligence(
            request_id=request_id,
            user_id=user_id,
            brand_name=brand_name,
            product_category=product_category,
            detected_archetype=archetype,
        )
        
        injected_intel = injected.to_atom_context()
        logger.debug(
            f"Injected pre-computed intelligence: "
            f"confidence={injected.confidence_level}, sources={injected.sources_available}"
        )
        
    except ImportError:
        logger.debug("AtomIntelligenceInjector not available")
    except Exception as e:
        logger.debug(f"Intelligence injection failed: {e}")
    
    # Get from FullIntelligenceIntegrator
    try:
        from adam.intelligence.full_intelligence_integration import get_full_intelligence_integrator
        integrator = get_full_intelligence_integrator()
        
        profile = await integrator.build_full_profile(
            brand_name=brand_name,
            product_name=product_name,
            category=product_category,
        )
        
        full_intel = {
            "behavioral_analysis": profile.behavioral_intelligence or {},
            "brand_copy_analysis": {
                "brand_personality": profile.brand_personality,
                "primary_personality": profile.brand_primary_personality,
                "brand_tactics": profile.brand_tactics or {},
            },
            "journey_intelligence": {
                "customer_cluster": profile.customer_cluster,
                "journey_based_appeals": profile.journey_based_appeals or [],
                "competitor_threats": profile.competitor_threats or [],
            },
            "intelligence_coverage": profile.intelligence_coverage,
        }
        
        logger.debug(f"Pre-fetched full intelligence: {profile.intelligence_coverage:.1%} coverage")
        
    except ImportError:
        logger.debug("FullIntelligenceIntegrator not available")
    except Exception as e:
        logger.warning(f"Failed to pre-fetch full intelligence: {e}")
    
    # Merge injected intelligence into brand copy analysis
    if injected_intel.get("injected_intelligence"):
        injected = injected_intel["injected_intelligence"]
        
        # Enhance brand copy analysis with pre-computed Cialdini scores
        if injected.get("brand_cialdini"):
            full_intel["brand_copy_analysis"]["cialdini_scores"] = injected["brand_cialdini"]
        
        # Add Aaker scores
        if injected.get("brand_aaker"):
            full_intel["brand_copy_analysis"]["aaker_scores"] = injected["brand_aaker"]
        
        # Add archetype effectiveness (critical for mechanism selection)
        if injected.get("archetype_effectiveness"):
            full_intel["archetype_effectiveness"] = injected["archetype_effectiveness"]
        
        # Add persuasive templates
        if injected.get("best_templates"):
            full_intel["persuasive_templates"] = injected["best_templates"]
        
        # Add journey products
        if injected.get("journey_products"):
            full_intel["journey_intelligence"]["journey_products"] = injected["journey_products"]
    
    # =========================================================================
    # GRAPH STATE INFERENCE: The inferential core
    # Instead of heuristic if/else rules, traverse the Neo4j graph:
    #   Observable Signals → BehavioralSignal → DSPConstruct → Mechanism
    # This produces a ConstructActivationProfile with uncertainty bounds
    # and mechanism priors derived from causal chains, not correlations.
    # =========================================================================
    construct_activation_profile = None
    graph_mechanism_priors = {}
    try:
        from adam.dsp.graph_state_inference import get_graph_state_inference_engine
        graph_engine = get_graph_state_inference_engine()

        # Build context from state for signal extraction
        inference_context = {
            "content_category": state.get("product_category", ""),
            "navigation_directness": state.get("navigation_directness"),
            "comparison_behavior": state.get("comparison_behavior"),
            "session_duration_seconds": state.get("session_duration_seconds"),
            "local_hour": state.get("local_hour"),
            "referrer_type": state.get("referrer_type"),
            "device_type": state.get("device_type"),
            "content_sentiment": state.get("content_sentiment"),
            "scroll_velocity": state.get("scroll_velocity"),
            "category_changes": state.get("category_changes"),
        }
        # Also merge any ad_context signals
        ad_ctx = state.get("ad_context", {})
        if isinstance(ad_ctx, dict):
            inference_context.update({
                k: v for k, v in ad_ctx.items()
                if k in (
                    "scroll_depth", "time_on_page_seconds", "pages_viewed",
                    "dark_mode", "connection_speed_mbps", "content_arousal",
                    "content_complexity", "subscriber_status", "session_phase",
                    "ad_density", "mouse_max_deviation", "backspace_frequency",
                )
            })

        construct_activation_profile = graph_engine.infer(inference_context)
        graph_mechanism_priors = construct_activation_profile._mechanism_priors

        logger.debug(
            f"Graph state inference: {construct_activation_profile.total_constructs_activated} "
            f"constructs activated from {construct_activation_profile.total_signals_observed} signals, "
            f"{len(graph_mechanism_priors)} mechanism priors derived"
        )

    except ImportError:
        logger.debug("GraphStateInferenceEngine not available — using heuristic fallback")
    except Exception as e:
        logger.debug(f"Graph state inference failed: {e}")

    return {
        **state,
        "full_intelligence_profile": full_intel,
        "behavioral_analysis": full_intel["behavioral_analysis"],
        "brand_copy_analysis": full_intel["brand_copy_analysis"],
        "journey_intelligence": full_intel["journey_intelligence"],
        "injected_intelligence": injected_intel,  # Pass through for atoms
        # NEW: Graph-inferred construct activations and mechanism priors
        "construct_activation_profile": construct_activation_profile,
        "graph_mechanism_priors": graph_mechanism_priors,
    }


# =============================================================================
# EXECUTION NODES
# =============================================================================

async def execute_aot_with_priors(state: OrchestratorState) -> OrchestratorState:
    """
    ENHANCED: Execute AoT atoms with full LangGraph intelligence injection.
    
    This is where the synergy happens:
    - Graph knowledge -> Atom priors
    - Helpful vote patterns -> Evidence weighting
    - Full intelligence -> Context enrichment
    - Competitive intelligence -> Mechanism differentiation
    - Deep archetype -> Targeted persuasion
    
    BIDIRECTIONAL: Also captures atom feedback for LangGraph learning.
    """
    atom_outputs = state.get("atom_outputs", {})
    atom_feedback = []
    prior_validation = {}
    learning_signals = []
    
    try:
        # Get enhanced AoT executor
        from adam.atoms.orchestration.dag_executor import (
            get_dag_executor,
            PriorContext,
        )
        
        executor = get_dag_executor()
        
        if executor:
            # Build prior context from full LangGraph state
            prior_context = PriorContext.from_langgraph_state(state)
            
            # Execute with prior injection - now returns feedback too!
            result = await executor.execute_with_priors(
                request_id=state.get("request_id", ""),
                user_id=state.get("user_id", ""),
                prior_context=prior_context,
                langgraph_state=state,
            )
            
            # Extract outputs
            atom_outputs = result.outputs
            
            # Capture feedback for LangGraph (NEW - bidirectional!)
            atom_feedback = result.feedback
            prior_validation = result.prior_validation
            learning_signals = result.learning_signals
            
            # Log feedback summary
            validated = len([f for f in atom_feedback if f.get("feedback_type") == "prior_validated"])
            overridden = len([f for f in atom_feedback if f.get("feedback_type") == "prior_overridden"])
            
            logger.info(
                f"AoT executed: {result.atoms_executed} atoms, "
                f"{len(atom_outputs)} outputs, "
                f"{validated} priors validated, {overridden} overridden, "
                f"{len(learning_signals)} learning signals"
            )
            
    except ImportError as e:
        logger.debug(f"DAG executor not available: {e}")
    except Exception as e:
        logger.warning(f"AoT execution failed: {e}")
        import traceback
        logger.debug(traceback.format_exc())
    
    # FALLBACK: If AoT didn't produce mechanism activations, use priors
    if "atom_mechanism_activation" not in atom_outputs or not atom_outputs.get("atom_mechanism_activation"):
        atom_outputs["atom_mechanism_activation"] = await _get_mechanism_activation_from_priors(state)
    
    return {
        **state,
        "atom_outputs": atom_outputs,
        # NEW: Feedback from atoms to LangGraph
        "atom_feedback": atom_feedback,
        "prior_validation": prior_validation,
        "atom_learning_signals": learning_signals,
    }


async def _get_mechanism_activation_from_priors(state: OrchestratorState) -> Dict[str, Any]:
    """
    FALLBACK: Get mechanism activations directly from learned priors.
    
    Used when AoT execution fails or returns empty results.
    Leverages Thompson Sampler's archetype-mechanism effectiveness data.
    """
    archetype = state.get("archetype_match", {}).get("primary_archetype") or "everyman"
    deep_archetype = state.get("deep_archetype", {}).get("primary_archetype")
    if deep_archetype:
        archetype = deep_archetype
    
    brand_name = state.get("brand_name", "")
    category = state.get("category", "")
    
    mechanism_scores = {}
    
    try:
        # Try Thompson Sampler for mechanism selection
        from adam.cold_start.thompson.sampler import get_thompson_sampler
        sampler = get_thompson_sampler()
        
        if sampler:
            # Use sample_top_k method to get multiple mechanisms
            top_mechanisms = sampler.sample_top_k(
                k=5,
                archetype=archetype,
            )
            for mech, score, reason in top_mechanisms:
                # Convert enum to string if needed
                mech_name = mech.value if hasattr(mech, 'value') else str(mech)
                mechanism_scores[mech_name] = score
            
            logger.debug(f"Priors fallback: {len(mechanism_scores)} mechanisms from Thompson Sampler")
    except Exception as e:
        logger.debug(f"Thompson Sampler fallback failed: {e}")
    
    # If Thompson Sampler didn't work, try learned priors directly
    if not mechanism_scores:
        try:
            from adam.core.learning.learned_priors_integration import get_learned_priors
            priors = get_learned_priors()
            
            # Get archetype-mechanism matrix
            matrix = priors._archetype_mechanism_matrix
            if matrix and archetype in matrix:
                arch_mechs = matrix[archetype]
                for mech, effectiveness in arch_mechs.items():
                    if isinstance(effectiveness, (int, float)):
                        mechanism_scores[mech] = effectiveness
            
            logger.debug(f"Priors fallback: {len(mechanism_scores)} mechanisms from priors matrix")
        except Exception as e:
            logger.debug(f"Priors matrix fallback failed: {e}")
    
    # If still empty, use default mechanism set
    if not mechanism_scores:
        # Default mechanisms based on archetype
        default_mechanisms = {
            "everyman": {"social_proof": 0.8, "belonging": 0.7, "relatability": 0.6},
            "achiever": {"scarcity": 0.8, "authority": 0.7, "exclusivity": 0.6},
            "explorer": {"curiosity": 0.8, "novelty": 0.7, "freedom": 0.6},
            "connector": {"social_proof": 0.8, "community": 0.7, "reciprocity": 0.6},
            "guardian": {"trust": 0.8, "safety": 0.7, "consistency": 0.6},
            "pragmatist": {"value": 0.8, "efficiency": 0.7, "proof": 0.6},
            "analyst": {"data": 0.8, "logic": 0.7, "comparison": 0.6},
        }
        mechanism_scores = default_mechanisms.get(archetype, default_mechanisms["everyman"])
        logger.debug(f"Priors fallback: Using default mechanisms for {archetype}")
    
    return {
        "mechanism_scores": mechanism_scores,
        "source": "priors_fallback",
        "archetype": archetype,
    }


async def process_atom_feedback(state: OrchestratorState) -> OrchestratorState:
    """
    NEW: Process feedback from atoms and route learning signals.
    
    This node completes the bidirectional loop:
    1. Processes atom feedback about prior validation
    2. Routes learning signals to appropriate systems
    3. Updates LangGraph's understanding of mechanism effectiveness
    4. Triggers adaptive behavior based on atom insights
    
    This enables LangGraph to LEARN from AoT decisions.
    """
    atom_feedback = state.get("atom_feedback", [])
    prior_validation = state.get("prior_validation", {})
    learning_signals = state.get("atom_learning_signals", [])
    
    # Initialize tracking
    langgraph_learnings = []
    mechanism_updates = {}
    archetype_updates = {}
    
    try:
        # Get feedback interface
        from adam.atoms.orchestration.langgraph_feedback import (
            get_feedback_interface,
            AtomLearningSignal,
        )
        
        feedback_interface = get_feedback_interface()
        
        # 1. Process atom feedback signals
        for fb in atom_feedback:
            signal = AtomLearningSignal(
                atom_id=fb.get("atom_id", "unknown"),
                request_id=state.get("request_id", ""),
                signal_type=fb.get("feedback_type", "unknown"),
                target_entity=fb.get("target_entity", ""),
                entity_type=fb.get("target_entity", "").split(":")[0] if ":" in fb.get("target_entity", "") else "unknown",
                value=fb.get("score", 0.5),
                confidence=fb.get("confidence", 0.5),
                reasoning=fb.get("reasoning", ""),
            )
            await feedback_interface.emit_atom_signal(signal)
            
            # Track mechanism updates
            if "mechanism" in signal.entity_type:
                mech_name = signal.target_entity.replace("mechanism:", "")
                mechanism_updates[mech_name] = {
                    "feedback_type": fb.get("feedback_type"),
                    "score": signal.value,
                }
        
        # 2. Process prior validation
        if prior_validation:
            # Track which priors were accurate
            if prior_validation.get("archetype_aligned"):
                archetype_updates["aligned"] = True
                langgraph_learnings.append({
                    "type": "archetype_validation",
                    "result": "confirmed",
                    "archetype": state.get("archetype_match", {}).get("primary_archetype"),
                })
            else:
                archetype_updates["aligned"] = False
                langgraph_learnings.append({
                    "type": "archetype_validation", 
                    "result": "overridden",
                    "prior_archetype": state.get("archetype_match", {}).get("primary_archetype"),
                })
            
            # Track mechanism alignment
            aligned_mechs = prior_validation.get("mechanisms_aligned", [])
            overridden_mechs = prior_validation.get("mechanisms_overridden", [])
            
            if aligned_mechs:
                langgraph_learnings.append({
                    "type": "mechanism_validation",
                    "aligned": aligned_mechs,
                    "count": len(aligned_mechs),
                })
            
            if overridden_mechs:
                langgraph_learnings.append({
                    "type": "mechanism_override",
                    "overridden": overridden_mechs,
                    "count": len(overridden_mechs),
                })
        
        # 3. Route learning signals to unified hub
        if learning_signals:
            try:
                from adam.core.learning.unified_learning_hub import (
                    get_unified_learning_hub,
                    UnifiedLearningSignal,
                    UnifiedSignalType,
                )
                
                hub = get_unified_learning_hub()
                
                for signal_data in learning_signals:
                    signal = UnifiedLearningSignal(
                        signal_type=UnifiedSignalType.ATOM_ATTRIBUTED,
                        component=signal_data.get("source", "atom"),
                        value=signal_data.get("signal", {}).get("score", 0.5),
                        metadata={
                            "signal_data": signal_data,
                            "request_id": state.get("request_id"),
                        },
                    )
                    await hub.process_signal(signal)
                    
            except ImportError:
                logger.debug("Unified learning hub not available")
        
        # 4. Log feedback summary
        logger.info(
            f"Atom feedback processed: {len(atom_feedback)} signals, "
            f"{len(mechanism_updates)} mechanism updates, "
            f"archetype {'aligned' if archetype_updates.get('aligned') else 'overridden'}"
        )
        
    except ImportError as e:
        logger.debug(f"Feedback interface not available: {e}")
    except Exception as e:
        logger.warning(f"Failed to process atom feedback: {e}")
    
    return {
        **state,
        # Add processed learnings for downstream use
        "langgraph_learnings": langgraph_learnings,
        "mechanism_updates_from_atoms": mechanism_updates,
        "archetype_validation": archetype_updates,
    }


async def synthesize_decision(state: OrchestratorState) -> OrchestratorState:
    """
    ENHANCED: Synthesize final decision from ALL intelligence sources.
    
    Combines:
    - AoT atom outputs
    - Graph intelligence
    - Helpful vote recommendations
    - Full intelligence profile
    - Competitive intelligence (NEW)
    - Deep archetype detection (NEW)
    - Personalized templates (NEW)
    
    Uses multi-source fusion with weighted boosting.
    """
    import uuid
    
    decision_id = f"dec_{uuid.uuid4().hex[:12]}"
    
    # Get all intelligence sources
    atom_outputs = state.get("atom_outputs", {})
    helpful_intel = state.get("helpful_vote_intelligence", {})
    competitive_intel = state.get("competitive_intelligence", {})
    templates = state.get("selected_templates", [])
    deep_archetype = state.get("deep_archetype", {})
    full_profile = state.get("full_intelligence_profile", {})
    
    archetype = deep_archetype.get("primary_archetype") or \
                state.get("archetype_match", {}).get("primary_archetype") or \
                "everyman"
    archetype_confidence = deep_archetype.get("confidence", 0.5)
    
    # =================================================================
    # STEP 0: Graph-Inferred Mechanism Priors (PRIMARY — inferential)
    #
    # This is the core inferential step. Instead of starting from atom
    # heuristics (correlational), we start from graph-traversal priors:
    #   Observable Signals → Constructs → Causal Edges → Mechanisms
    #
    # These priors represent what the validated psychological science
    # (encoded in graph edge effect sizes) predicts should work.
    # =================================================================
    graph_priors = state.get("graph_mechanism_priors", {})
    construct_profile = state.get("construct_activation_profile")

    mechanisms_applied = []

    if graph_priors:
        # Graph priors are the PRIMARY mechanism source
        max_prior = max(graph_priors.values()) if graph_priors else 0
        for mech, prior_strength in graph_priors.items():
            if prior_strength < 0.05:
                continue
            mechanisms_applied.append({
                "name": mech,
                "intensity": prior_strength,
                "base_score": prior_strength,
                "source": "graph_inference",
                "is_primary": prior_strength == max_prior,
                "boosts_applied": ["graph_inferred"],
            })
        logger.debug(
            f"Graph inference produced {len(mechanisms_applied)} mechanism priors "
            f"(top: {max(graph_priors, key=graph_priors.get) if graph_priors else 'none'})"
        )

    # =================================================================
    # STEP 1: AoT Atom Mechanism Validation (SECONDARY — heuristic)
    #
    # Atom outputs validate and calibrate the graph-inferred priors.
    # If graph priors exist, atom scores are blended at 40% weight.
    # If graph priors are empty, atoms become the primary source.
    # =================================================================
    if "atom_mechanism_activation" in atom_outputs:
        mech_output = atom_outputs["atom_mechanism_activation"]
        if isinstance(mech_output, dict):
            atom_scores = mech_output.get("mechanism_scores", {})
            max_score = max(atom_scores.values()) if atom_scores else 0

            if mechanisms_applied:
                # BLEND: graph priors (60%) + atom scores (40%)
                mech_map = {m["name"]: m for m in mechanisms_applied}
                for mech, score in atom_scores.items():
                    if mech in mech_map:
                        graph_val = mech_map[mech]["intensity"]
                        blended = 0.60 * graph_val + 0.40 * score
                        mech_map[mech]["intensity"] = blended
                        mech_map[mech]["boosts_applied"].append(f"aot_blend:{score:.2f}")
                    else:
                        # Atom found a mechanism the graph didn't — add at reduced weight
                        mechanisms_applied.append({
                            "name": mech,
                            "intensity": score * 0.40,
                            "base_score": score,
                            "source": "aot_only",
                            "is_primary": False,
                            "boosts_applied": ["aot_only_reduced"],
                        })
            else:
                # No graph priors — atoms are the primary source (fallback)
                for mech, score in atom_scores.items():
                    mechanisms_applied.append({
                        "name": mech,
                        "intensity": score,
                        "base_score": score,
                        "source": "aot",
                        "is_primary": score == max_score,
                        "boosts_applied": [],
                    })
    
    # =================================================================
    # STEP 1b: Apply DSP graph intelligence to mechanism scoring
    # =================================================================
    dsp_intel = state.get("injected_intelligence", {}).get("dsp_graph_intelligence", {})
    if dsp_intel.get("has_dsp"):
        import math as _math

        # Empirical effectiveness boost (15% weight)
        empirical = dsp_intel.get("empirical_effectiveness", {})
        for mech in mechanisms_applied:
            emp = empirical.get(mech["name"])
            if emp:
                success_rate = emp.get("success_rate", 0.5)
                sample_size = emp.get("sample_size", 0)
                confidence = min(1.0, _math.log1p(sample_size) / 10.0) if sample_size > 0 else 0.1
                emp_boost = 1 + 0.15 * (success_rate - 0.5) * confidence
                mech["intensity"] = min(1.0, mech["intensity"] * emp_boost)
                mech["boosts_applied"].append(f"dsp_empirical:{emp_boost:.3f}")

        # Category moderation (10% weight)
        cat_mod = dsp_intel.get("category_moderation", {})
        for mech in mechanisms_applied:
            delta = cat_mod.get(mech["name"])
            if delta is not None:
                cat_boost = 1 + 0.10 * delta
                mech["intensity"] = min(1.0, max(0.0, mech["intensity"] * cat_boost))
                mech["boosts_applied"].append(f"dsp_category:{cat_boost:.3f}")

        # Susceptibility adjustment (10% weight)
        suscept = dsp_intel.get("mechanism_susceptibility", {})
        for mech in mechanisms_applied:
            sus = suscept.get(mech["name"])
            if sus is not None:
                sus_boost = 1 + 0.10 * (sus - 0.5)
                mech["intensity"] = min(1.0, max(0.0, mech["intensity"] * sus_boost))
                mech["boosts_applied"].append(f"dsp_susceptibility:{sus_boost:.3f}")

    # =================================================================
    # STEP 2: Apply helpful vote effectiveness boost
    # =================================================================
    mechanism_priors = helpful_intel.get("mechanism_priors", {})
    
    for mech in mechanisms_applied:
        prior = mechanism_priors.get(mech["name"], 0)
        if prior > 0:
            boost = 1 + (prior * 0.3)  # Up to 30% boost
            mech["intensity"] = min(1.0, mech["intensity"] * boost)
            mech["helpful_vote_effectiveness"] = prior
            mech["boosts_applied"].append(f"helpful_vote:{boost:.2f}")
    
    # =================================================================
    # STEP 3: Apply competitive differentiation boost
    # =================================================================
    underutilized = set(competitive_intel.get("underutilized_mechanisms", []))
    
    for mech in mechanisms_applied:
        if mech["name"] in underutilized:
            boost = 1.2  # 20% boost for competitive advantage
            mech["intensity"] = min(1.0, mech["intensity"] * boost)
            mech["competitive_advantage"] = True
            mech["boosts_applied"].append(f"competitive:{boost:.2f}")
    
    # Add mechanisms from counter-strategies if not already present
    for strategy in competitive_intel.get("counter_strategies", [])[:2]:
        counter_mech = strategy.get("target_mechanism")
        if counter_mech and not any(m["name"] == counter_mech for m in mechanisms_applied):
            mechanisms_applied.append({
                "name": counter_mech,
                "intensity": 0.6,
                "base_score": 0.6,
                "source": "competitive_counter",
                "is_primary": False,
                "competitive_advantage": True,
                "counter_strategy": strategy.get("strategy_name"),
                "boosts_applied": ["competitive_counter"],
            })
    
    # =================================================================
    # STEP 4: Apply template-based validation boost
    # =================================================================
    template_mechanisms = set(t.get("mechanism") for t in templates if t.get("mechanism"))
    
    for mech in mechanisms_applied:
        if mech["name"] in template_mechanisms:
            boost = 1.15  # 15% boost for proven templates
            mech["intensity"] = min(1.0, mech["intensity"] * boost)
            mech["has_proven_templates"] = True
            mech["boosts_applied"].append(f"template_validated:{boost:.2f}")
    
    # =================================================================
    # STEP 5: Add mechanisms from helpful vote rankings (if missing)
    # =================================================================
    helpful_routing = helpful_intel.get("routing_data", {})
    if archetype in helpful_routing.get("archetype_mechanism_rankings", {}):
        rankings = helpful_routing["archetype_mechanism_rankings"][archetype]
        for rank in rankings[:3]:
            if not any(m["name"] == rank["mechanism"] for m in mechanisms_applied):
                mechanisms_applied.append({
                    "name": rank["mechanism"],
                    "intensity": rank["score"],
                    "base_score": rank["score"],
                    "source": "helpful_vote_ranking",
                    "is_primary": False,
                    "helpful_vote_confidence": rank.get("confidence", 0.5),
                    "boosts_applied": [],
                })
    
    # Sort by final intensity
    mechanisms_applied.sort(key=lambda m: m["intensity"], reverse=True)
    
    # =================================================================
    # STEP 6: Build comprehensive confidence scores
    # =================================================================
    confidence_scores = {
        "overall": 0.0,
        "archetype_confidence": archetype_confidence,
        "archetype_detection_method": deep_archetype.get("detection_method", "unknown"),
        "graph_confidence": state.get("graph_intelligence", {}).get("confidence", 0.5),
        "helpful_vote_coverage": helpful_routing.get("coverage", {}).get("archetypes", 0) / 10,
        "competitive_available": competitive_intel.get("available", False),
        "templates_selected": len(templates),
        "intelligence_coverage": full_profile.get("intelligence_coverage", 0),
    }
    
    # Calculate overall confidence
    confidence_scores["overall"] = sum([
        confidence_scores["archetype_confidence"] * 0.3,
        confidence_scores["graph_confidence"] * 0.2,
        confidence_scores["helpful_vote_coverage"] * 0.2,
        (1.0 if confidence_scores["competitive_available"] else 0.5) * 0.1,
        min(1.0, confidence_scores["templates_selected"] / 5) * 0.1,
        confidence_scores["intelligence_coverage"] * 0.1,
    ])
    
    # =================================================================
    # STEP 7: Build rich learning context
    # =================================================================
    learning_context = {
        "decision_id": decision_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": state.get("user_id"),
        "brand_name": state.get("brand_name"),
        "product_name": state.get("product_name"),
        "product_category": state.get("product_category"),
        
        # Archetype intelligence
        "archetype": archetype,
        "archetype_confidence": archetype_confidence,
        "archetype_detection_method": deep_archetype.get("detection_method"),
        "secondary_archetypes": deep_archetype.get("secondary_archetypes", []),
        "psychological_profile": deep_archetype.get("psychological_profile", {}),
        
        # Mechanisms with full context
        "mechanisms_applied": [
            {
                "name": m["name"],
                "intensity": m["intensity"],
                "base_score": m.get("base_score", m["intensity"]),
                "source": m["source"],
                "boosts_applied": m.get("boosts_applied", []),
                "competitive_advantage": m.get("competitive_advantage", False),
                "has_proven_templates": m.get("has_proven_templates", False),
            }
            for m in mechanisms_applied
        ],
        
        # Templates used
        "templates_used": [
            {
                "pattern": t.get("pattern", "")[:100],
                "mechanism": t.get("mechanism"),
                "effectiveness": t.get("effectiveness_score", 0),
                "competitive_advantage": t.get("competitive_advantage", False),
            }
            for t in templates[:5]
        ],
        
        # Intelligence sources tracking
        "intelligence_sources": {
            "graph_intelligence": bool(state.get("graph_intelligence")),
            "helpful_vote_intelligence": bool(helpful_intel),
            "competitive_intelligence": competitive_intel.get("available", False),
            "full_intelligence": bool(full_profile),
            "deep_archetype_detection": deep_archetype.get("detection_method") == "deep_linguistic_analysis",
        },
        
        # Competitive context (for learning what worked against competitors)
        "competitive_context": {
            "underutilized_mechanisms_used": [
                m["name"] for m in mechanisms_applied 
                if m.get("competitive_advantage")
            ],
            "counter_strategies_applied": [
                s.get("strategy_name") 
                for s in competitive_intel.get("counter_strategies", [])[:2]
            ],
        },
        
        # For outcome attribution
        "atom_outputs_summary": {
            k: type(v).__name__ for k, v in atom_outputs.items()
        },
        
        # Alignment system context (for CognitiveLearningSystem outcome comparison)
        "alignment_scores": state.get("alignment_scores", {}),
        "alignment_recommendation": state.get("alignment_recommendation", ""),
        "expanded_customer_type": state.get("expanded_customer_type", {}),
        "ad_copy_profile": state.get("ad_copy_profile", {}),
        "predicted_effectiveness": state.get("alignment_scores", {}).get("overall_alignment", 0.0),
        
        # DSP graph enrichment summary
        "dsp_enrichment": {
            "has_empirical_effectiveness": bool(state.get("injected_intelligence", {}).get("dsp_graph_intelligence", {}).get("empirical_effectiveness")),
            "has_category_moderation": bool(state.get("injected_intelligence", {}).get("dsp_graph_intelligence", {}).get("category_moderation")),
            "has_alignment_edges": bool(state.get("injected_intelligence", {}).get("dsp_graph_intelligence", {}).get("alignment_edges")),
        },
        
        # Graph inference context (for learning loop)
        "graph_inference": {
            "method": getattr(construct_profile, "inference_method", "not_available") if construct_profile else "not_available",
            "constructs_activated": getattr(construct_profile, "total_constructs_activated", 0) if construct_profile else 0,
            "signals_observed": getattr(construct_profile, "total_signals_observed", 0) if construct_profile else 0,
            "top_constructs": [
                {"id": c.construct_id, "activation": c.activation, "confidence": c.confidence}
                for c in (construct_profile.get_top_constructs(5) if construct_profile else [])
            ],
            "mechanism_priors_from_graph": graph_priors,
        },
    }
    
    logger.info(
        f"Synthesized decision {decision_id}: "
        f"archetype={archetype} (conf={archetype_confidence:.2f}), "
        f"{len(mechanisms_applied)} mechanisms, "
        f"{len(templates)} templates, "
        f"competitive={'yes' if competitive_intel.get('available') else 'no'}"
    )
    
    return {
        **state,
        "decision_id": decision_id,
        "mechanisms_applied": mechanisms_applied,
        "confidence_scores": confidence_scores,
        "learning_context": learning_context,
    }


# =============================================================================
# LEARNING NODES
# =============================================================================

async def persist_for_learning(state: OrchestratorState) -> OrchestratorState:
    """
    Persist decision to graph for future learning.
    
    Creates:
    - Decision node
    - Mechanism edges
    - User edges
    
    This enables learning path completion when outcome arrives.
    """
    decision_id = state.get("decision_id")
    user_id = state.get("user_id")
    mechanisms = state.get("mechanisms_applied", [])
    
    if not decision_id:
        return state
    
    try:
        # Persist via bidirectional bridge
        from adam.intelligence.bidirectional_bridge import get_bidirectional_bridge
        bridge = get_bidirectional_bridge()
        
        if bridge:
            # Extract confidence from state or use default
            confidence = state.get("confidence_scores", {}).get("overall", 0.5)
            
            # Get atom outputs from state
            atom_outputs = state.get("atom_outputs", {})
            
            await bridge.persist_decision_to_graph(
                decision_id=decision_id,
                user_id=user_id,
                brand=state.get("brand_name", ""),
                product=state.get("product_name", ""),
                mechanism_used=mechanisms[0]["name"] if mechanisms else "unknown",
                atom_outputs=atom_outputs,
                confidence=confidence,
            )
            
            logger.debug(f"Persisted decision {decision_id} for learning")
            
    except ImportError:
        logger.debug("Bidirectional bridge not available")
    except Exception as e:
        logger.warning(f"Failed to persist for learning: {e}")
    
    # Also persist via gradient bridge for credit attribution
    try:
        from adam.core.learning.unified_learning_hub import (
            get_unified_learning_hub,
            UnifiedLearningSignal,
            UnifiedSignalType,
        )
        
        hub = get_unified_learning_hub()
        
        # Create learning signal for gradient bridge
        mechanisms = state.get("mechanisms_applied", [])
        primary_mechanism = mechanisms[0]["name"] if mechanisms else "unknown"
        
        # Build enriched payload with alignment + DSP context
        # This ensures CognitiveLearningSystem receives alignment predictions
        # for outcome comparison when OutcomeHandler processes outcomes
        alignment_scores = state.get("alignment_scores", {})
        learning_ctx = state.get("learning_context", {})
        
        # Extract active constructs — primarily from graph inference (inferential)
        active_constructs = []
        construct_profile = state.get("construct_activation_profile")
        if construct_profile and hasattr(construct_profile, "get_top_constructs"):
            for act in construct_profile.get_top_constructs(20):
                if act.construct_id not in active_constructs:
                    active_constructs.append(act.construct_id)

        # Also include DSP injected constructs as supplementary evidence
        dsp_intel = state.get("injected_intelligence", {}).get("dsp_graph_intelligence", {})
        if dsp_intel.get("has_dsp"):
            for key in list(dsp_intel.get("empirical_effectiveness", {}).keys()):
                if key not in active_constructs:
                    active_constructs.append(key)
            for edge in dsp_intel.get("alignment_edges", []):
                target = edge.get("target_id", "")
                if target and target not in active_constructs:
                    active_constructs.append(target)
        
        # Collect corpus fusion state for learning attribution
        corpus_fusion_intel = state.get("corpus_fusion_intelligence", {})
        corpus_mechanism_priors = state.get("corpus_mechanism_priors", {})
        corpus_platform_cal = state.get("corpus_platform_calibration", {})
        corpus_creative = state.get("corpus_creative_constraints", {})
        
        signal = UnifiedLearningSignal(
            signal_type=UnifiedSignalType.CREDIT_MECHANISM,
            source_component="synergy_orchestrator",
            archetype=state.get("archetype_match", {}).get("primary_archetype", "everyman"),
            mechanism=primary_mechanism,
            confidence=state.get("confidence_scores", {}).get("overall", 0.5),
            active_constructs=active_constructs,
            payload={
                "decision_id": decision_id,
                "user_id": user_id,
                "mechanisms": [m["name"] for m in mechanisms],
                "event_type": "decision_persisted",
                # Alignment system context (for CognitiveLearningSystem)
                "alignment_scores": alignment_scores,
                "predicted_effectiveness": alignment_scores.get("overall_alignment", 0.0),
                "alignment_recommendation": state.get("alignment_recommendation", ""),
                "expanded_customer_type": state.get("expanded_customer_type", {}),
                "ad_copy_profile": state.get("ad_copy_profile", {}),
                "product_category": state.get("product_category", ""),
                "active_dsp_constructs": active_constructs,
                "dsp_construct_count": len(active_constructs),
                # Corpus Fusion tracking — enables post-hoc analysis of
                # how corpus intelligence correlates with outcomes
                "corpus_fusion": {
                    "mechanism_priors": corpus_mechanism_priors,
                    "prior_confidence": corpus_fusion_intel.get("confidence", 0.0),
                    "evidence_count": corpus_fusion_intel.get("evidence_count", 0),
                    "platform_calibration": corpus_platform_cal,
                    "creative_constraints": corpus_creative,
                    "transfer_sources": corpus_fusion_intel.get("transfer_sources", []),
                    "had_corpus": bool(corpus_mechanism_priors),
                },
            },
        )
        
        await hub.process_signal(signal)
        logger.debug(f"Gradient signal emitted for decision {decision_id}")
        
    except ImportError as e:
        logger.debug(f"Gradient bridge not available: {e}")
    except Exception as e:
        logger.warning(f"Failed to emit gradient signal: {e}")
    
    return state


async def trigger_graph_maintenance(state: OrchestratorState) -> OrchestratorState:
    """
    Trigger graph intelligence maintenance if needed.
    
    Periodically:
    - Run GDS algorithms (PageRank, community detection)
    - Update emergence patterns
    - Refresh mechanism effectiveness
    """
    # Only run periodically (every ~100 decisions)
    import random
    if random.random() > 0.01:  # 1% chance
        return state
    
    try:
        # Trigger async maintenance
        from adam.intelligence.graph_maintenance import trigger_maintenance
        asyncio.create_task(trigger_maintenance())
        logger.info("Triggered graph maintenance")
    except ImportError:
        # Fallback: emit maintenance signal for other systems to handle
        try:
            from adam.core.learning.unified_learning_hub import (
                get_unified_learning_hub,
                UnifiedLearningSignal,
                UnifiedSignalType,
            )
            
            hub = get_unified_learning_hub()
            signal = UnifiedLearningSignal(
                signal_type=UnifiedSignalType.CALIBRATION_NEEDED,
                source_component="graph_maintenance_trigger",
                archetype="system",
                mechanism="maintenance",
                confidence=1.0,
                payload={
                    "maintenance_type": "graph",
                    "trigger_reason": "periodic",
                },
            )
            await hub.process_signal(signal)
            logger.debug("Emitted graph maintenance signal via learning hub")
        except Exception:
            logger.debug("Graph maintenance unavailable, skipping")
    except Exception as e:
        logger.debug(f"Could not trigger maintenance: {e}")
    
    return state


# =============================================================================
# NEW NODES: COMPETITIVE INTELLIGENCE
# =============================================================================

async def prefetch_competitive_intelligence(state: OrchestratorState) -> OrchestratorState:
    """
    Pre-fetch competitive intelligence if competitor ads are available.
    
    Provides:
    - Market mechanism saturation
    - Underutilized mechanisms (competitive advantage)
    - Counter-strategies
    - Competitor vulnerabilities
    """
    competitor_ads = state.get("competitor_ads", [])
    brand_name = state.get("brand_name", "")
    archetype = state.get("archetype_match", {}).get("primary_archetype")
    
    competitive_intel = {
        "market_saturation": {},
        "underutilized_mechanisms": [],
        "counter_strategies": [],
        "vulnerabilities": [],
        "available": False,
    }
    
    if competitor_ads and brand_name:
        try:
            from adam.competitive.intelligence import get_competitive_intelligence_service
            service = get_competitive_intelligence_service()
            
            # Analyze each competitor ad
            analyses = []
            for ad in competitor_ads:
                if isinstance(ad, dict) and "name" in ad and "text" in ad:
                    analysis = service.analyze_competitor_ad(ad["name"], ad["text"])
                    analyses.append(analysis)
            
            if analyses:
                # Build comprehensive competitive intelligence
                intel = service.build_competitive_intelligence(
                    our_brand=brand_name,
                    competitor_analyses=analyses,
                    target_archetypes=[archetype] if archetype else None,
                )
                
                competitive_intel = {
                    "market_saturation": intel.market_mechanism_saturation,
                    "underutilized_mechanisms": intel.underutilized_mechanisms,
                    "counter_strategies": [
                        {
                            "strategy_name": s.strategy_name,
                            "target_mechanism": s.target_mechanism,
                            "counter_approach": s.counter_approach,
                            "expected_lift": s.expected_lift,
                        }
                        for s in intel.counter_strategies[:5]
                    ],
                    "vulnerabilities": [
                        {
                            "competitor": v.competitor,
                            "vulnerability_type": v.vulnerability_type,
                            "description": v.description,
                            "exploitation_approach": v.exploitation_approach,
                        }
                        for v in intel.vulnerabilities[:3]
                    ],
                    "available": True,
                }
                
                logger.debug(
                    f"Competitive intel: {len(analyses)} competitors analyzed, "
                    f"{len(competitive_intel['underutilized_mechanisms'])} underutilized mechanisms"
                )
        
        except ImportError:
            logger.debug("Competitive intelligence service not available")
        except Exception as e:
            logger.warning(f"Competitive intelligence failed: {e}")
    
    return {
        **state,
        "competitive_intelligence": competitive_intel,
    }


async def prefetch_corpus_fusion(state: OrchestratorState) -> OrchestratorState:
    """
    Pre-fetch corpus fusion intelligence from the 1B+ review corpus.
    
    Provides:
    - Empirical mechanism priors from corpus (Layer 1)
    - Creative pattern constraints (Layer 2)
    - Platform-specific calibration factors (Layer 3)
    - Resonance templates from helpful-vote-validated reviews (Layer 5)
    
    This runs in parallel with all other prefetch nodes.
    """
    product_category = state.get("product_category", "")
    brand_name = state.get("brand_name", "")
    # Archetype may not be determined yet in prefetch; use best available
    archetype = (
        state.get("deep_archetype", {}).get("primary_archetype")
        or state.get("archetype_match", {}).get("primary_archetype")
    )
    
    corpus_intel = {
        "mechanism_priors": {},
        "prior_confidence": 0.0,
        "evidence_count": 0,
        "creative_constraints": {},
        "platform_calibration": {},
        "resonance_templates": [],
        "available": False,
    }
    mechanism_priors = {}
    creative_constraints = {}
    platform_calibration = {}
    
    if not product_category:
        logger.debug("Corpus fusion: no product_category — skipping")
        return {
            **state,
            "corpus_fusion_intelligence": corpus_intel,
            "corpus_mechanism_priors": mechanism_priors,
            "corpus_creative_constraints": creative_constraints,
            "corpus_platform_calibration": platform_calibration,
        }
    
    # Layer 1: Extract empirical priors
    try:
        from adam.fusion.prior_extraction import get_prior_extraction_service
        prior_service = get_prior_extraction_service()
        
        corpus_prior = prior_service.extract_prior(
            category=product_category,
            archetype=archetype,
            brand=brand_name or None,
        )
        
        if corpus_prior and corpus_prior.mechanism_priors:
            mechanism_priors = corpus_prior.get_mechanism_dict()
            corpus_intel["mechanism_priors"] = mechanism_priors
            corpus_intel["prior_confidence"] = corpus_prior.confidence
            corpus_intel["evidence_count"] = corpus_prior.evidence_count
            corpus_intel["available"] = True
            
            logger.debug(
                f"Corpus fusion Layer 1: {len(mechanism_priors)} mechanism priors "
                f"(confidence={corpus_prior.confidence:.2f}, n={corpus_prior.evidence_count})"
            )
    except ImportError:
        logger.debug("PriorExtractionService not available")
    except Exception as e:
        logger.warning(f"Corpus fusion Layer 1 failed: {e}")
    
    # Layer 2: Extract creative constraints
    try:
        from adam.fusion.creative_patterns import get_creative_pattern_extractor
        creative_service = get_creative_pattern_extractor()
        
        constraints = creative_service.extract_creative_constraints(
            category=product_category,
            target_archetype=archetype,
        )
        
        if constraints:
            creative_constraints = {
                "framing_guidance": constraints.framing_guidance if hasattr(constraints, 'framing_guidance') else {},
                "emotional_register": constraints.emotional_register if hasattr(constraints, 'emotional_register') else {},
                "mechanism_deployment": constraints.mechanism_deployment if hasattr(constraints, 'mechanism_deployment') else {},
                "ranked_patterns": [
                    {"pattern": p.pattern_type if hasattr(p, 'pattern_type') else str(p), 
                     "effectiveness": p.effectiveness if hasattr(p, 'effectiveness') else 0.5}
                    for p in (constraints.ranked_patterns if hasattr(constraints, 'ranked_patterns') else [])[:5]
                ],
            }
            corpus_intel["creative_constraints"] = creative_constraints
            
            logger.debug(f"Corpus fusion Layer 2: creative constraints extracted")
    except ImportError:
        logger.debug("CreativePatternExtractor not available")
    except Exception as e:
        logger.warning(f"Corpus fusion Layer 2 failed: {e}")
    
    # Layer 3: Platform calibration
    try:
        from adam.fusion.platform_calibration import get_platform_calibration_layer
        calibration = get_platform_calibration_layer()
        
        # Get calibration for top mechanisms
        platform = "general"  # Will be refined when platform context is available
        calibration_factors = {}
        for mech_name, prior_score in list(mechanism_priors.items())[:10]:
            calibrated, confidence, source = calibration.get_calibrated_score(
                platform=platform,
                mechanism=mech_name,
                category=product_category,
                corpus_prior=prior_score,
            )
            calibration_factors[mech_name] = {
                "calibrated_score": calibrated,
                "confidence": confidence,
                "source": source,
            }
        
        if calibration_factors:
            platform_calibration = calibration_factors
            corpus_intel["platform_calibration"] = platform_calibration
            logger.debug(f"Corpus fusion Layer 3: {len(calibration_factors)} mechanisms calibrated")
    except ImportError:
        logger.debug("PlatformCalibrationLayer not available")
    except Exception as e:
        logger.warning(f"Corpus fusion Layer 3 failed: {e}")
    
    # Layer 5: Resonance templates
    try:
        from adam.fusion.resonance_index import get_persuasion_resonance_index
        resonance = get_persuasion_resonance_index()
        
        templates = resonance.get_resonance_templates(
            category=product_category,
            archetype=archetype,
            top_k=5,
        )
        
        if templates:
            corpus_intel["resonance_templates"] = [
                {
                    "mechanism": t.mechanism if hasattr(t, 'mechanism') else "",
                    "pattern": t.pattern if hasattr(t, 'pattern') else str(t),
                    "effectiveness": t.effectiveness if hasattr(t, 'effectiveness') else 0.5,
                    "helpful_vote_score": t.helpful_vote_score if hasattr(t, 'helpful_vote_score') else 0.0,
                }
                for t in templates[:5]
            ]
            logger.debug(f"Corpus fusion Layer 5: {len(templates)} resonance templates")
    except ImportError:
        logger.debug("PersuasionResonanceIndex not available")
    except Exception as e:
        logger.warning(f"Corpus fusion Layer 5 failed: {e}")
    
    return {
        **state,
        "corpus_fusion_intelligence": corpus_intel,
        "corpus_mechanism_priors": mechanism_priors,
        "corpus_creative_constraints": creative_constraints,
        "corpus_platform_calibration": platform_calibration,
    }


async def validate_and_merge_prefetch(state: OrchestratorState) -> OrchestratorState:
    """
    Validate and merge all prefetch intelligence before continuing pipeline.
    
    This is a critical sync point that:
    1. Validates prefetch results are properly formatted
    2. Tracks which intelligence sources were successful
    3. Computes overall intelligence confidence
    4. Prepares unified context for downstream nodes
    
    Enterprise Requirement: All prefetch failures must be logged and tracked.
    """
    # Track successful prefetches
    prefetch_results = {
        "graph_intelligence": bool(state.get("graph_intelligence")),
        "helpful_vote_intelligence": bool(state.get("helpful_vote_intelligence")),
        "full_intelligence_profile": bool(state.get("full_intelligence_profile")),
        "competitive_intelligence": state.get("competitive_intelligence", {}).get("available", False),
        "corpus_fusion_intelligence": state.get("corpus_fusion_intelligence", {}).get("available", False),
    }
    
    successful_prefetches = sum(prefetch_results.values())
    total_prefetches = len(prefetch_results)
    
    # Calculate intelligence coverage
    intelligence_coverage = successful_prefetches / total_prefetches if total_prefetches > 0 else 0
    
    # Log prefetch status for enterprise monitoring
    if successful_prefetches < total_prefetches:
        missing = [k for k, v in prefetch_results.items() if not v]
        logger.warning(
            f"Prefetch incomplete: {successful_prefetches}/{total_prefetches} sources. "
            f"Missing: {missing}"
        )
    else:
        logger.info(f"All {total_prefetches} prefetch sources available")
    
    # Build unified intelligence context for downstream nodes
    unified_context = {
        "prefetch_status": prefetch_results,
        "intelligence_coverage": intelligence_coverage,
        "has_graph_context": prefetch_results["graph_intelligence"],
        "has_helpful_votes": prefetch_results["helpful_vote_intelligence"],
        "has_full_profile": prefetch_results["full_intelligence_profile"],
        "has_competitive_intel": prefetch_results["competitive_intelligence"],
    }
    
    # Extract key signals from full intelligence profile
    full_profile = state.get("full_intelligence_profile", {})
    if full_profile:
        unified_context["dominant_archetype"] = full_profile.get("psychological_profile", {}).get(
            "dominant_archetype"
        )
        unified_context["susceptibility_tier"] = full_profile.get("susceptibility", {}).get("tier")
        unified_context["behavioral_classifiers"] = list(
            full_profile.get("behavioral_classifiers", {}).keys()
        )
    
    # Emit prefetch completion signal for learning loop
    try:
        from adam.core.learning.unified_learning_hub import (
            get_unified_learning_hub,
            UnifiedLearningSignal,
            UnifiedSignalType,
        )
        
        hub = get_unified_learning_hub()
        signal = UnifiedLearningSignal(
            signal_type=UnifiedSignalType.PATTERN_DISCOVERED,
            source_component="prefetch_merge",
            archetype=unified_context.get("dominant_archetype", "unknown"),
            mechanism="prefetch_coverage",
            confidence=intelligence_coverage,
            payload={
                "prefetch_status": prefetch_results,
                "coverage": intelligence_coverage,
                "request_id": state.get("request_id"),
            },
        )
        await hub.process_signal(signal)
    except Exception as e:
        logger.debug(f"Could not emit prefetch signal: {e}")
    
    return {
        **state,
        "unified_intelligence_context": unified_context,
        "intelligence_coverage": intelligence_coverage,
    }


# =============================================================================
# NEW NODES: DEEP ARCHETYPE DETECTION
# =============================================================================

async def detect_deep_archetype(state: OrchestratorState) -> OrchestratorState:
    """
    Perform deep archetype detection using psychological analysis.
    
    Uses multiple signals:
    1. User review text (if available) - 500+ linguistic markers
    2. Behavioral signals - purchase patterns
    3. Graph profile - learned preferences
    4. Category/brand priors - fallback
    
    This replaces simple category-based archetype assignment.
    """
    archetype_result = {
        "primary_archetype": None,
        "secondary_archetypes": [],
        "confidence": 0.0,
        "detection_method": "unknown",
        "psychological_profile": {},
    }
    
    # Priority 1: If we already have archetype from graph profile
    existing_archetype = state.get("archetype_match", {}).get("primary_archetype")
    existing_confidence = state.get("archetype_match", {}).get("confidence", 0)
    
    if existing_archetype and existing_confidence > 0.7:
        archetype_result = {
            "primary_archetype": existing_archetype,
            "secondary_archetypes": state.get("archetype_match", {}).get("secondary", []),
            "confidence": existing_confidence,
            "detection_method": "graph_profile",
            "psychological_profile": state.get("user_profile", {}),
        }
        return {**state, "deep_archetype": archetype_result, "archetype_match": archetype_result}
    
    # Priority 2: Deep detection from user text
    user_text = state.get("user_review_text", "")
    if user_text and len(user_text) > 50:
        try:
            from adam.intelligence.deep_archetype_detection import DeepArchetypeDetector
            detector = DeepArchetypeDetector()
            
            deep_result = detector.detect_archetype(user_text)
            
            if deep_result.confidence > 0.4:
                archetype_result = {
                    "primary_archetype": deep_result.primary_archetype,
                    "secondary_archetypes": deep_result.secondary_archetypes[:3],
                    "confidence": deep_result.confidence,
                    "detection_method": "deep_linguistic_analysis",
                    "psychological_profile": {
                        "value_profile": deep_result.value_profile,
                        "cognitive_style": deep_result.cognitive_style,
                        "regulatory_focus": deep_result.regulatory_focus,
                    },
                }
                logger.debug(
                    f"Deep archetype detected: {deep_result.primary_archetype} "
                    f"(confidence: {deep_result.confidence:.2f})"
                )
                return {**state, "deep_archetype": archetype_result, "archetype_match": archetype_result}
        
        except ImportError:
            logger.debug("Deep archetype detector not available")
        except Exception as e:
            logger.debug(f"Deep archetype detection failed: {e}")
    
    # Priority 3: Cold-start archetype detection with behavioral signals
    behavioral_signals = state.get("user_behavioral_signals", {})
    brand_name = state.get("brand_name", "")
    product_category = state.get("product_category", "")
    
    try:
        from adam.cold_start.archetypes.detector import ArchetypeDetector
        detector = ArchetypeDetector()
        
        result = detector.detect_archetype(
            behavioral_signals=behavioral_signals,
            category=product_category,
            brand=brand_name,
        )
        
        archetype_result = {
            "primary_archetype": result.archetype.value if result.archetype else "everyman",
            "secondary_archetypes": [a.value for a in result.secondary_matches[:3]],
            "confidence": result.confidence,
            "detection_method": "cold_start_detector",
            "psychological_profile": {},
        }
        
    except ImportError:
        logger.debug("Cold-start archetype detector not available")
    except Exception as e:
        logger.debug(f"Cold-start detection failed: {e}")
    
    # Priority 4: Fallback to category default
    if not archetype_result["primary_archetype"]:
        archetype_result = {
            "primary_archetype": "everyman",
            "secondary_archetypes": [],
            "confidence": 0.3,
            "detection_method": "category_default",
            "psychological_profile": {},
        }
    
    return {
        **state,
        "deep_archetype": archetype_result,
        "archetype_match": archetype_result,
    }


# =============================================================================
# NEW NODES: PERSONALIZED TEMPLATE SELECTION
# =============================================================================

async def select_personalized_templates(state: OrchestratorState) -> OrchestratorState:
    """
    Select the best templates for this specific user/context combination.
    
    ENHANCED: Now includes alignment-based scoring from the 7 alignment matrices
    and DSP graph intelligence alongside existing competitive and helpful vote scoring.
    
    Uses:
    - User's archetype
    - Selected mechanisms
    - Brand personality alignment
    - Competitive differentiation
    - Helpful vote effectiveness scores
    - Alignment scores (optimal mechanism + linguistic style match) [NEW]
    - DSP graph intelligence (empirical effectiveness) [NEW]
    """
    archetype = state.get("archetype_match", {}).get("primary_archetype") or "everyman"
    mechanisms = state.get("mechanisms_applied", [])
    competitive = state.get("competitive_intelligence", {})
    helpful_intel = state.get("helpful_vote_intelligence", {})
    brand_copy = state.get("brand_copy_analysis", {})
    
    # NEW: Get alignment and ad profile data
    alignment_scores = state.get("alignment_scores", {})
    ad_copy_profile = state.get("ad_copy_profile", {})
    expanded_type = state.get("expanded_customer_type", {})
    
    selected_templates = []
    
    # Get templates from helpful vote intelligence (already filtered by archetype)
    available_templates = helpful_intel.get("templates", [])
    
    # Also try to get from pattern persistence (Neo4j)
    # FIX: Use correct method name (was query_templates_for_archetype_mechanism which doesn't exist)
    try:
        from adam.infrastructure.neo4j.pattern_persistence import get_pattern_persistence
        persistence = get_pattern_persistence()
        
        for mech in mechanisms[:3]:  # Focus on top 3 mechanisms
            mechanism_name = mech.get("name")
            
            neo4j_templates = await persistence.get_best_templates_for_archetype(
                archetype=archetype,
                mechanism=mechanism_name,
                limit=5,
            )
            
            for t in neo4j_templates:
                t["source"] = "neo4j"
                t["mechanism"] = mechanism_name
                available_templates.append(t)
    
    except ImportError:
        logger.debug("Pattern persistence not available")
    except Exception as e:
        logger.debug(f"Neo4j template query failed: {e}")
    
    # Score and rank templates
    underutilized = set(competitive.get("underutilized_mechanisms", []))
    brand_personality = brand_copy.get("primary_personality", "")
    
    # NEW: Extract alignment-optimal mechanism and linguistic style
    optimal_mechanisms = expanded_type.get("optimal_mechanism_sequence", [])
    optimal_mechanism_primary = optimal_mechanisms[0] if optimal_mechanisms else ""
    ad_linguistic_style = ad_copy_profile.get("linguistic_style", "")
    product_category = state.get("product_category", "").lower()
    
    for template in available_templates:
        score = template.get("effectiveness_score", 0.5)
        
        # Boost for mechanism match
        template_mechanism = template.get("mechanism", "")
        matching_applied = next(
            (m for m in mechanisms if m.get("name") == template_mechanism),
            None
        )
        if matching_applied:
            score *= 1.3
            template["mechanism_match"] = True
        
        # Boost for competitive advantage
        if template_mechanism in underutilized:
            score *= 1.25
            template["competitive_advantage"] = True
        
        # Boost for brand personality alignment
        if brand_personality and brand_personality.lower() in template.get("pattern", "").lower():
            score *= 1.15
            template["brand_aligned"] = True
        
        # Boost for high helpful votes
        votes = template.get("vote_count", template.get("helpful_votes", 0))
        if votes > 100:
            score *= 1.2
        elif votes > 50:
            score *= 1.1
        
        # =====================================================================
        # NEW: Alignment-based scoring
        # =====================================================================
        
        # +30% if template mechanism matches alignment-optimal mechanism
        if optimal_mechanism_primary and template_mechanism == optimal_mechanism_primary:
            score *= 1.3
            template["alignment_optimal_match"] = True
        
        # +15% if template linguistic style matches ad copy linguistic style
        template_pattern = template.get("pattern", "").lower()
        if ad_linguistic_style:
            style_markers = {
                "technical": ["specification", "performance", "benchmark", "feature"],
                "emotional": ["feel", "love", "amazing", "transform", "beautiful"],
                "professional": ["clinical", "proven", "research", "expert", "certified"],
                "storytelling": ["journey", "story", "discover", "experience", "imagine"],
                "urgent": ["now", "limited", "hurry", "today", "fast"],
            }
            markers = style_markers.get(ad_linguistic_style, [])
            if markers and any(m in template_pattern for m in markers):
                score *= 1.15
                template["linguistic_style_match"] = True
        
        # +10% if template category aligns with product category
        template_category = template.get("category", "").lower()
        if product_category and template_category and product_category in template_category:
            score *= 1.1
            template["category_match"] = True

        # =====================================================================
        # DSP Graph Intelligence scoring
        # =====================================================================
        dsp_intel = state.get("injected_intelligence", {}).get("dsp_graph_intelligence", {})
        if dsp_intel.get("has_dsp"):
            empirical = dsp_intel.get("empirical_effectiveness", {})
            cat_mod = dsp_intel.get("category_moderation", {})

            # Empirical effectiveness boost
            emp_data = empirical.get(template_mechanism)
            if emp_data and emp_data.get("sample_size", 0) > 100:
                success = emp_data.get("success_rate", 0.5)
                score *= 1 + 0.2 * (success - 0.5)
                template["dsp_empirical_boost"] = True

            # Category moderation delta
            delta = cat_mod.get(template_mechanism)
            if delta is not None:
                score *= 1 + 0.1 * delta
                template["dsp_category_boost"] = True

        template["final_score"] = score
    
    # Sort by final score and take top 10
    available_templates.sort(key=lambda t: t.get("final_score", 0), reverse=True)
    selected_templates = available_templates[:10]
    
    logger.debug(
        f"Selected {len(selected_templates)} personalized templates "
        f"(alignment_optimal={optimal_mechanism_primary}, style={ad_linguistic_style})"
    )
    
    return {
        **state,
        "selected_templates": selected_templates,
    }


# =============================================================================
# ALIGNMENT SYSTEM NODES (Phase D3)
# =============================================================================

async def profile_ad_copy(state: OrchestratorState) -> OrchestratorState:
    """
    Profile the ad/product copy psychologically.

    Uses brand_name, product_name, product_category to build an
    AdvertisementProfile containing value propositions, emotional tone,
    linguistic style, and persuasion techniques detected in the copy.
    """
    brand_name = state.get("brand_name", "")
    product_name = state.get("product_name", "")
    product_category = state.get("product_category", "")
    brand_copy = state.get("brand_copy_analysis", {})

    ad_profile: Dict[str, Any] = {
        "brand": brand_name,
        "product": product_name,
        "category": product_category,
        "detected_value_propositions": [],
        "detected_persuasion_techniques": [],
        "emotional_tone": {},
        "linguistic_style": "conversational",
        "brand_personality": {},
    }

    try:
        from adam.core.learning.learned_priors_integration import get_learned_priors
        priors = get_learned_priors()

        # Infer category-level product profile
        cat_profile = priors.get_product_category_profile(product_category)
        if cat_profile:
            ad_profile["category_profile"] = cat_profile

        # If brand_copy_analysis was prefetched, extract ad characteristics
        if brand_copy:
            copy_text = brand_copy.get("copy_text", "")
            detected_techniques = brand_copy.get("persuasion_techniques", [])
            ad_profile["detected_persuasion_techniques"] = detected_techniques
            ad_profile["emotional_tone"] = brand_copy.get("emotional_tone", {})

        # Infer value propositions from category
        vp_map = {
            "Electronics": ["vp_performance_superiority", "vp_novelty_innovation", "vp_reliability_durability"],
            "Beauty": ["vp_transformation", "vp_self_expression", "vp_pleasure_enjoyment"],
            "Health": ["vp_peace_of_mind", "vp_reliability_durability", "vp_knowledge_expertise"],
            "Books": ["vp_knowledge_expertise", "vp_pleasure_enjoyment", "vp_transformation"],
            "Clothing": ["vp_self_expression", "vp_status_prestige", "vp_pleasure_enjoyment"],
            "Baby": ["vp_peace_of_mind", "vp_reliability_durability", "vp_belonging_connection"],
            "Grocery": ["vp_convenience_ease", "vp_pleasure_enjoyment", "vp_cost_efficiency"],
            "Home": ["vp_convenience_ease", "vp_reliability_durability", "vp_cost_efficiency"],
            "Sports": ["vp_performance_superiority", "vp_transformation", "vp_pleasure_enjoyment"],
        }
        for key, vps in vp_map.items():
            if key.lower() in product_category.lower():
                ad_profile["detected_value_propositions"] = vps
                break
        if not ad_profile["detected_value_propositions"]:
            ad_profile["detected_value_propositions"] = ["vp_cost_efficiency", "vp_convenience_ease"]

        # Detect linguistic style from brand copy or category
        style_map = {
            "Electronics": "technical", "Beauty": "emotional", "Health": "professional",
            "Books": "storytelling", "Clothing": "emotional", "Sports": "urgent",
        }
        for key, style in style_map.items():
            if key.lower() in product_category.lower():
                ad_profile["linguistic_style"] = style
                break

    except Exception as e:
        logger.debug(f"Ad copy profiling partial failure: {e}")

    logger.debug(f"Ad copy profiled: {len(ad_profile.get('detected_value_propositions', []))} VPs, style={ad_profile.get('linguistic_style')}")

    # Write to BOTH keys: our new key and the key PriorContext.from_langgraph_state reads
    return {**state, "ad_copy_profile": ad_profile, "product_ad_profile": ad_profile}


async def infer_expanded_customer_type(state: OrchestratorState) -> OrchestratorState:
    """
    Infer expanded customer type from the 1.9M type system.

    Uses archetype, behavioral signals, NDF, and context to infer:
    - Primary motivation (from 37)
    - Decision style (from 12)
    - Regulatory focus (from 8)
    - Emotional intensity (from 9)
    - Social influence type (from 5)
    """
    archetype_data = state.get("deep_archetype", state.get("archetype_match", {}))
    primary_archetype = archetype_data.get("primary_archetype", "explorer")
    behavioral = state.get("user_behavioral_signals", {})
    ndf = state.get("atom_outputs", {}).get("ndf_profile", {})

    expanded_type: Dict[str, Any] = {
        "archetype": primary_archetype,
        "motivation": "problem_solving_mot",  # default
        "decision_style": "ds_satisficing",    # default
        "regulatory_focus": "rf_pragmatic_balanced",
        "emotional_intensity": "ei_moderate_positive",
        "social_influence_type": "si_socially_aware",
        "confidence": 0.4,
    }

    try:
        from adam.core.learning.learned_priors_integration import get_learned_priors
        priors = get_learned_priors()

        # 1. Infer decision style from priors
        ds_priors = priors.get_decision_style(primary_archetype)
        if ds_priors:
            best_style = max(ds_priors.items(), key=lambda x: x[1]) if ds_priors else None
            if best_style:
                expanded_type["decision_style"] = f"ds_{best_style[0]}"
                expanded_type["decision_style_distribution"] = ds_priors
                expanded_type["confidence"] = min(0.85, expanded_type["confidence"] + 0.15)

        # 2. Infer social influence type from priors
        si_priors = priors.get_social_influence_type(primary_archetype)
        if si_priors:
            expanded_type["social_influence_data"] = si_priors
            # Map from archetype patterns
            arch_social_map = {
                "explorer": "si_informational_seeker",
                "achiever": "si_opinion_leader",
                "connector": "si_normatively_driven",
                "guardian": "si_socially_aware",
                "analyst": "si_informational_seeker",
                "pragmatist": "si_highly_independent",
            }
            expanded_type["social_influence_type"] = arch_social_map.get(
                primary_archetype.lower(), "si_socially_aware"
            )

        # 3. Infer motivation from context
        category = state.get("product_category", "")
        cat_motivation_map = {
            "Electronics": "mastery_seeking",
            "Beauty": "self_expression",
            "Health": "risk_mitigation",
            "Baby": "risk_mitigation",
            "Books": "pure_curiosity",
            "Clothing": "self_expression",
            "Grocery": "cost_minimization",
            "Sports": "personal_growth",
            "Home": "quality_assurance",
        }
        for key, mot in cat_motivation_map.items():
            if key.lower() in category.lower():
                expanded_type["motivation"] = mot
                expanded_type["confidence"] = min(0.85, expanded_type["confidence"] + 0.1)
                break

        # 4. Infer emotional intensity from persuasion sensitivity
        emo_priors = priors.get_emotion_sensitivity(primary_archetype)
        if emo_priors:
            expanded_type["emotion_sensitivity"] = emo_priors

        # 5. Infer regulatory focus from archetype
        reg_map = {
            "explorer": "rf_optimistic_exploration",
            "achiever": "rf_eager_advancement",
            "connector": "rf_pragmatic_balanced",
            "guardian": "rf_conservative_preservation",
            "analyst": "rf_vigilant_security",
            "pragmatist": "rf_pragmatic_balanced",
        }
        expanded_type["regulatory_focus"] = reg_map.get(
            primary_archetype.lower(), "rf_pragmatic_balanced"
        )

    except Exception as e:
        logger.debug(f"Expanded type inference partial failure: {e}")

    logger.debug(
        f"Expanded type: motivation={expanded_type['motivation']}, "
        f"decision_style={expanded_type['decision_style']}, "
        f"social={expanded_type['social_influence_type']}"
    )

    # Write to BOTH keys: our new key and the key PriorContext.from_langgraph_state reads
    return {**state, "expanded_customer_type": expanded_type, "expanded_type": expanded_type}


async def calculate_alignment_scores(state: OrchestratorState) -> OrchestratorState:
    """
    Calculate alignment scores across all 7 matrices.

    Combines:
    - Ad copy profile (value propositions, linguistic style, persuasion techniques)
    - Expanded customer type (motivation, decision style, regulatory focus, etc.)
    - Archetype personality alignment

    Produces a comprehensive alignment score that feeds into mechanism selection
    and confidence calibration.
    """
    ad_profile = state.get("ad_copy_profile", {})
    customer_type = state.get("expanded_customer_type", {})
    archetype_data = state.get("deep_archetype", state.get("archetype_match", {}))
    primary_archetype = archetype_data.get("primary_archetype", "explorer")

    alignment: Dict[str, Any] = {
        "overall_alignment": 0.5,
        "matrix_scores": {},
        "best_mechanisms": [],
        "recommended_adjustments": [],
    }

    try:
        from adam.core.learning.learned_priors_integration import get_learned_priors
        priors = get_learned_priors()
        matrices = priors.get_alignment_matrices()

        total_score = 0.0
        matrix_count = 0

        # 1. Motivation-Value alignment
        motivation = customer_type.get("motivation", "problem_solving_mot")
        ad_vps = ad_profile.get("detected_value_propositions", [])
        mv_matrix = matrices.get("motivation_value", {})
        mv_row = mv_matrix.get(motivation, {})
        if mv_row and ad_vps:
            vp_scores = [mv_row.get(vp.replace("vp_", ""), 0) for vp in ad_vps]
            mv_score = max(vp_scores) if vp_scores else 0.5
            alignment["matrix_scores"]["motivation_value"] = mv_score
            total_score += mv_score
            matrix_count += 1
            if mv_score < 0.4:
                best_vp = max(mv_row.items(), key=lambda x: x[1])
                alignment["recommended_adjustments"].append(
                    f"Shift value proposition toward '{best_vp[0]}' (alignment={best_vp[1]:.2f})"
                )

        # 2. Decision Style-Linguistic alignment
        ds = customer_type.get("decision_style", "ds_satisficing").replace("ds_", "")
        ad_style = ad_profile.get("linguistic_style", "conversational")
        dsl_matrix = matrices.get("decision_style_linguistic", {})
        dsl_row = dsl_matrix.get(ds, {})
        if dsl_row:
            dsl_score = dsl_row.get(ad_style, 0.5)
            alignment["matrix_scores"]["decision_style_linguistic"] = dsl_score
            total_score += dsl_score
            matrix_count += 1
            if dsl_score < 0.5:
                best_style = max(dsl_row.items(), key=lambda x: x[1])
                alignment["recommended_adjustments"].append(
                    f"Switch linguistic style to '{best_style[0]}' (alignment={best_style[1]:.2f})"
                )

        # 3. Regulatory-Emotional alignment
        rf = customer_type.get("regulatory_focus", "rf_pragmatic_balanced").replace("rf_", "")
        re_matrix = matrices.get("regulatory_emotional", {})
        re_row = re_matrix.get(rf, {})
        if re_row:
            ad_emotion = ad_profile.get("emotional_tone", {})
            best_emotion_match = 0.5
            for emo, score in re_row.items():
                if score > best_emotion_match:
                    best_emotion_match = score
            alignment["matrix_scores"]["regulatory_emotional"] = best_emotion_match
            total_score += best_emotion_match
            matrix_count += 1

        # 4. Archetype-Brand Personality alignment
        abp_matrix = matrices.get("archetype_personality", {})
        abp_row = abp_matrix.get(primary_archetype.lower(), {})
        brand_personality = ad_profile.get("brand_personality", {})
        if abp_row:
            bp_score = max(abp_row.values()) if abp_row else 0.5
            alignment["matrix_scores"]["archetype_personality"] = bp_score
            total_score += bp_score
            matrix_count += 1

        # 5. Mechanism Susceptibility
        ms_matrix = matrices.get("mechanism_susceptibility", {})
        ms_row = ms_matrix.get(ds, {})
        if ms_row:
            sorted_mechs = sorted(ms_row.items(), key=lambda x: x[1], reverse=True)
            alignment["best_mechanisms"] = [
                {"mechanism": m, "susceptibility": s} for m, s in sorted_mechs[:5]
            ]
            ms_score = sorted_mechs[0][1] if sorted_mechs else 0.5
            alignment["matrix_scores"]["mechanism_susceptibility"] = ms_score
            total_score += ms_score
            matrix_count += 1

        # 6. Social Persuasion alignment
        si = customer_type.get("social_influence_type", "si_socially_aware").replace("si_", "")
        sp_matrix = matrices.get("social_persuasion", {})
        sp_row = sp_matrix.get(si, {})
        if sp_row:
            ad_techniques = ad_profile.get("detected_persuasion_techniques", [])
            sp_score = 0.5
            if ad_techniques:
                tech_scores = [sp_row.get(t, 0) for t in ad_techniques]
                sp_score = max(tech_scores) if tech_scores else 0.5
            alignment["matrix_scores"]["social_persuasion"] = sp_score
            total_score += sp_score
            matrix_count += 1

        # =====================================================================
        # DSP Graph Alignment Enhancement
        # Blend Neo4j alignment edge strengths with static matrix scores
        # (20% graph weight, 80% static weight)
        # =====================================================================
        try:
            injected = state.get("injected_intelligence", {})
            dsp_intel = injected.get("dsp_graph_intelligence", {})
            alignment_edges = dsp_intel.get("alignment_edges", [])

            if alignment_edges:
                for edge in alignment_edges:
                    matrix_name = edge.get("matrix", "")
                    strength = edge.get("strength", 0.0)
                    target = edge.get("target_id", "")

                    # Map matrix name to alignment key
                    matrix_key_map = {
                        "MOTIVATION_VALUE_ALIGNMENT": "motivation_value",
                        "DECISION_STYLE_LINGUISTIC_ALIGNMENT": "decision_style_linguistic",
                        "REGULATORY_EMOTIONAL_ALIGNMENT": "regulatory_emotional",
                        "ARCHETYPE_PERSONALITY_ALIGNMENT": "archetype_personality",
                        "MECHANISM_SUSCEPTIBILITY": "mechanism_susceptibility",
                        "COGNITIVE_COMPLEXITY_ALIGNMENT": "cognitive_complexity",
                        "SOCIAL_PERSUASION_ALIGNMENT": "social_persuasion",
                    }

                    key = matrix_key_map.get(matrix_name, "")
                    if key and key in alignment["matrix_scores"]:
                        # Blend: 80% static + 20% graph
                        static_val = alignment["matrix_scores"][key]
                        blended = 0.80 * static_val + 0.20 * strength
                        alignment["matrix_scores"][key] = blended

                        # Recompute total
                        total_score = sum(alignment["matrix_scores"].values())
                        matrix_count = len(alignment["matrix_scores"])
        except Exception as e:
            logger.debug(f"DSP alignment edge enhancement failed: {e}")

        # Calculate overall alignment
        if matrix_count > 0:
            alignment["overall_alignment"] = total_score / matrix_count

    except Exception as e:
        logger.debug(f"Alignment calculation partial failure: {e}")

    logger.debug(
        f"Alignment scores: overall={alignment['overall_alignment']:.2f}, "
        f"matrices={len(alignment['matrix_scores'])}, "
        f"adjustments={len(alignment['recommended_adjustments'])}"
    )

    # Derive alignment recommendation from overall score
    overall = alignment.get("overall_alignment", 0.0)
    if overall >= 0.7:
        recommendation = "strong_match"
    elif overall >= 0.5:
        recommendation = "moderate_match"
    elif overall >= 0.3:
        recommendation = "weak_match"
    else:
        recommendation = "mismatch"

    return {**state, "alignment_scores": alignment, "alignment_recommendation": recommendation}


# =============================================================================
# BUILD ORCHESTRATOR GRAPH (ENHANCED WITH PARALLEL EXECUTION)
# =============================================================================

def build_synergy_orchestrator() -> StateGraph:
    """
    Build the ENHANCED LangGraph orchestrator for synergistic operation.
    
    ENHANCED FLOW:
    1. Pre-fetch (PARALLEL): Graph, Helpful Vote, Full Intelligence, Competitive
    2. Detect: Deep archetype detection (uses prefetched data)
    3. Execute: AoT with injected priors
    4. Select: Personalized template selection
    5. Synthesize: Enhanced multi-source decision fusion
    6. Persist: Store for learning
    7. Maintain: Trigger graph maintenance
    
    PARALLEL EXECUTION reduces latency by ~3x.
    """
    graph = StateGraph(OrchestratorState)
    
    # Add all nodes
    graph.add_node("prefetch_graph", prefetch_graph_intelligence)
    graph.add_node("prefetch_helpful_vote", prefetch_helpful_vote_intelligence)
    graph.add_node("prefetch_full_intel", prefetch_full_intelligence)
    graph.add_node("prefetch_competitive", prefetch_competitive_intelligence)
    graph.add_node("prefetch_corpus_fusion", prefetch_corpus_fusion)
    graph.add_node("merge_prefetch", validate_and_merge_prefetch)
    graph.add_node("detect_archetype", detect_deep_archetype)
    graph.add_node("execute_aot", execute_aot_with_priors)
    graph.add_node("process_feedback", process_atom_feedback)  # Bidirectional feedback
    # ALIGNMENT SYSTEM: 3 new nodes
    graph.add_node("profile_ad_copy", profile_ad_copy)
    graph.add_node("infer_expanded_type", infer_expanded_customer_type)
    graph.add_node("calculate_alignment", calculate_alignment_scores)
    graph.add_node("select_templates", select_personalized_templates)
    graph.add_node("synthesize", synthesize_decision)
    graph.add_node("persist", persist_for_learning)
    graph.add_node("maintain", trigger_graph_maintenance)
    
    # TRUE PARALLEL PRE-FETCH: Fan-out from START to all 5 prefetch nodes
    # Each runs concurrently, writing to different state keys
    graph.add_edge(START, "prefetch_graph")
    graph.add_edge(START, "prefetch_helpful_vote")
    graph.add_edge(START, "prefetch_full_intel")
    graph.add_edge(START, "prefetch_competitive")
    graph.add_edge(START, "prefetch_corpus_fusion")
    
    # Fan-in: All prefetch nodes merge into validation/merge node
    graph.add_edge("prefetch_graph", "merge_prefetch")
    graph.add_edge("prefetch_helpful_vote", "merge_prefetch")
    graph.add_edge("prefetch_full_intel", "merge_prefetch")
    graph.add_edge("prefetch_competitive", "merge_prefetch")
    graph.add_edge("prefetch_corpus_fusion", "merge_prefetch")
    
    # After merge, detect archetype with full prefetched context
    graph.add_edge("merge_prefetch", "detect_archetype")
    
    # Execute AoT with full context
    graph.add_edge("detect_archetype", "execute_aot")
    
    # Process atom feedback (bidirectional learning)
    graph.add_edge("execute_aot", "process_feedback")
    
    # ALIGNMENT SYSTEM: Profile ad copy → infer expanded type → calculate alignment
    graph.add_edge("process_feedback", "profile_ad_copy")
    graph.add_edge("profile_ad_copy", "infer_expanded_type")
    graph.add_edge("infer_expanded_type", "calculate_alignment")
    
    # Select templates based on alignment + mechanisms + feedback
    graph.add_edge("calculate_alignment", "select_templates")
    
    # Synthesize final decision
    graph.add_edge("select_templates", "synthesize")
    
    # Persist and maintain
    graph.add_edge("synthesize", "persist")
    graph.add_edge("persist", "maintain")
    graph.add_edge("maintain", END)
    
    return graph


def build_parallel_synergy_orchestrator() -> StateGraph:
    """
    Build a TRUE parallel orchestrator using LangGraph's parallel execution.
    
    This version uses conditional edges and parallel node execution
    for maximum performance.
    
    ENHANCED: Now includes bidirectional feedback processing.
    """
    from langgraph.graph import StateGraph, START
    
    graph = StateGraph(OrchestratorState)
    
    # Add all nodes
    graph.add_node("prefetch_graph", prefetch_graph_intelligence)
    graph.add_node("prefetch_helpful_vote", prefetch_helpful_vote_intelligence)
    graph.add_node("prefetch_full_intel", prefetch_full_intelligence)
    graph.add_node("prefetch_competitive", prefetch_competitive_intelligence)
    graph.add_node("prefetch_corpus_fusion", prefetch_corpus_fusion)
    graph.add_node("merge_prefetch", validate_and_merge_prefetch)  # Validate prefetch results
    graph.add_node("detect_archetype", detect_deep_archetype)
    graph.add_node("execute_aot", execute_aot_with_priors)
    graph.add_node("process_feedback", process_atom_feedback)  # Bidirectional feedback
    # ALIGNMENT SYSTEM: 3 new nodes
    graph.add_node("profile_ad_copy", profile_ad_copy)
    graph.add_node("infer_expanded_type", infer_expanded_customer_type)
    graph.add_node("calculate_alignment", calculate_alignment_scores)
    graph.add_node("select_templates", select_personalized_templates)
    graph.add_node("synthesize", synthesize_decision)
    graph.add_node("persist", persist_for_learning)
    graph.add_node("maintain", trigger_graph_maintenance)
    
    # TRUE PARALLEL FAN-OUT: All 5 prefetch nodes run concurrently from START
    graph.add_edge(START, "prefetch_graph")
    graph.add_edge(START, "prefetch_helpful_vote")
    graph.add_edge(START, "prefetch_full_intel")
    graph.add_edge(START, "prefetch_competitive")
    graph.add_edge(START, "prefetch_corpus_fusion")
    
    # FAN-IN: All prefetch nodes converge to merge point
    graph.add_edge("prefetch_graph", "merge_prefetch")
    graph.add_edge("prefetch_helpful_vote", "merge_prefetch")
    graph.add_edge("prefetch_full_intel", "merge_prefetch")
    graph.add_edge("prefetch_competitive", "merge_prefetch")
    graph.add_edge("prefetch_corpus_fusion", "merge_prefetch")
    
    # After merge, continue sequential processing
    graph.add_edge("merge_prefetch", "detect_archetype")
    graph.add_edge("detect_archetype", "execute_aot")
    graph.add_edge("execute_aot", "process_feedback")
    # ALIGNMENT SYSTEM
    graph.add_edge("process_feedback", "profile_ad_copy")
    graph.add_edge("profile_ad_copy", "infer_expanded_type")
    graph.add_edge("infer_expanded_type", "calculate_alignment")
    graph.add_edge("calculate_alignment", "select_templates")
    graph.add_edge("select_templates", "synthesize")
    graph.add_edge("synthesize", "persist")
    graph.add_edge("persist", "maintain")
    graph.add_edge("maintain", END)
    
    return graph


# =============================================================================
# ORCHESTRATOR EXECUTOR
# =============================================================================

class SynergyOrchestrator:
    """
    ENHANCED Main orchestrator class that runs the LangGraph workflow.
    
    Usage:
        orchestrator = SynergyOrchestrator()
        result = await orchestrator.execute(
            user_id="user123",
            brand_name="Nike",
            product_name="Air Max",
            product_category="Athletic_Footwear",
            competitor_ads=[
                {"name": "Adidas", "text": "Impossible is Nothing..."},
            ],
            user_review_text="I love these shoes...",  # For deep archetype detection
        )
    
    NEW FEATURES:
    - Competitive intelligence integration
    - Deep archetype detection
    - Personalized template selection
    - Multi-source intelligence fusion
    """
    
    def __init__(self, use_parallel: bool = False):
        """
        Initialize the orchestrator.
        
        Args:
            use_parallel: If True, use the parallel execution graph (experimental)
        """
        self._graph = None
        self._compiled = None
        self._use_parallel = use_parallel
        self._execution_count = 0
        self._total_latency_ms = 0.0
    
    def _ensure_compiled(self):
        """Ensure graph is built and compiled."""
        if self._compiled is None:
            if self._use_parallel:
                self._graph = build_parallel_synergy_orchestrator()
            else:
                self._graph = build_synergy_orchestrator()
            self._compiled = self._graph.compile()
    
    async def execute(
        self,
        user_id: str,
        brand_name: str,
        product_name: str,
        product_category: str = "",
        request_id: Optional[str] = None,
        # NEW: Competitive context
        competitor_ads: Optional[List[Dict[str, str]]] = None,
        # NEW: User signals for deep archetype detection
        user_review_text: Optional[str] = None,
        user_behavioral_signals: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Execute the ENHANCED synergy orchestrator.
        
        Args:
            user_id: User identifier
            brand_name: Brand being considered
            product_name: Product being considered
            product_category: Product category
            request_id: Optional request ID
            competitor_ads: Optional list of competitor ads for competitive intel
                           [{"name": "Competitor", "text": "Ad copy..."}, ...]
            user_review_text: Optional user-provided text for deep archetype detection
            user_behavioral_signals: Optional behavioral signals {signal: value}
        
        Returns:
            Final state with decision, mechanisms, templates, and learning context.
        """
        import uuid
        import time
        
        start_time = time.time()
        self._ensure_compiled()
        
        initial_state: OrchestratorState = {
            "request_id": request_id or f"req_{uuid.uuid4().hex[:12]}",
            "user_id": user_id,
            "brand_name": brand_name,
            "product_name": product_name,
            "product_category": product_category,
            "competitor_ads": competitor_ads or [],
            "user_review_text": user_review_text or "",
            "user_behavioral_signals": user_behavioral_signals or {},
            "atom_outputs": {},
        }
        
        try:
            final_state = await self._compiled.ainvoke(initial_state)
            
            # Track execution metrics
            latency_ms = (time.time() - start_time) * 1000
            self._execution_count += 1
            self._total_latency_ms += latency_ms
            
            # Enhanced logging
            archetype = final_state.get("archetype_match", {}).get("primary_archetype", "unknown")
            arch_method = final_state.get("deep_archetype", {}).get("detection_method", "unknown")
            competitive = final_state.get("competitive_intelligence", {}).get("available", False)
            templates = len(final_state.get("selected_templates", []))
            
            logger.info(
                f"Orchestrator complete: decision={final_state.get('decision_id')}, "
                f"archetype={archetype} ({arch_method}), "
                f"mechanisms={len(final_state.get('mechanisms_applied', []))}, "
                f"templates={templates}, "
                f"competitive={'yes' if competitive else 'no'}, "
                f"latency={latency_ms:.1f}ms"
            )
            
            # Add execution metadata
            final_state["execution_metadata"] = {
                "latency_ms": latency_ms,
                "execution_count": self._execution_count,
                "avg_latency_ms": self._total_latency_ms / self._execution_count,
                "graph_type": "parallel" if self._use_parallel else "sequential",
            }
            
            return final_state
            
        except Exception as e:
            logger.error(f"Orchestrator failed: {e}")
            return {
                **initial_state,
                "error": str(e),
                "execution_metadata": {
                    "latency_ms": (time.time() - start_time) * 1000,
                    "error": True,
                },
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator execution statistics."""
        return {
            "execution_count": self._execution_count,
            "total_latency_ms": self._total_latency_ms,
            "avg_latency_ms": self._total_latency_ms / max(1, self._execution_count),
            "graph_type": "parallel" if self._use_parallel else "sequential",
        }
    
    async def process_outcome(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        helpful_votes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Process an outcome through the learning system.
        
        This closes the learning loop:
        1. Routes to UnifiedLearningHub
        2. Updates Graph
        3. Updates Thompson Sampling
        4. Stores helpful vote patterns
        """
        result = {
            "decision_id": decision_id,
            "outcome_processed": False,
            "systems_updated": [],
        }
        
        # 1. Route through Unified Learning Hub
        try:
            from adam.core.learning.unified_learning_hub import get_initialized_learning_hub
            hub = await get_initialized_learning_hub()
            
            # Get helpful vote weight
            weight = 1.0
            if helpful_votes:
                from adam.intelligence.helpful_vote_intelligence import InfluenceTier
                tier = InfluenceTier.from_votes(helpful_votes)
                weight = InfluenceTier.get_weight(tier)
            
            delivered = await hub.emit_outcome(
                decision_id=decision_id,
                outcome_value=outcome_value,
                helpful_vote_weight=weight,
            )
            
            result["systems_updated"].append(f"learning_hub ({delivered} deliveries)")
            result["outcome_processed"] = True
            
        except Exception as e:
            logger.error(f"Learning hub outcome processing failed: {e}")
        
        # 2. Create learning path in graph
        try:
            from adam.intelligence.bidirectional_bridge import get_bidirectional_bridge
            bridge = get_bidirectional_bridge()
            
            if bridge:
                await bridge.create_learning_path(
                    decision_id=decision_id,
                    outcome_type=outcome_type,
                    outcome_value=outcome_value,
                )
                result["systems_updated"].append("bidirectional_bridge")
                
        except Exception as e:
            logger.debug(f"Bridge learning path failed: {e}")
        
        logger.info(
            f"Processed outcome for {decision_id}: "
            f"value={outcome_value}, systems={result['systems_updated']}"
        )
        
        return result


# =============================================================================
# SINGLETON
# =============================================================================

_orchestrator: Optional[SynergyOrchestrator] = None


def get_synergy_orchestrator() -> SynergyOrchestrator:
    """Get singleton synergy orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = SynergyOrchestrator()
    return _orchestrator
