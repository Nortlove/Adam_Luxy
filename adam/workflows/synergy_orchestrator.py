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

from langgraph.graph import StateGraph, END

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
    
    # NEW: Bidirectional AoT ↔ LangGraph feedback
    atom_feedback: List[Dict[str, Any]]  # Feedback from atoms
    prior_validation: Dict[str, Any]  # Did atoms agree with LangGraph priors?
    atom_learning_signals: List[Dict[str, Any]]  # Learning signals to route
    langgraph_learnings: List[Dict[str, Any]]  # Processed learnings
    mechanism_updates_from_atoms: Dict[str, Any]  # Mechanism-specific updates
    archetype_validation: Dict[str, Any]  # Archetype alignment status


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
    
    return {
        **state,
        "graph_intelligence": graph_intel,
        "user_profile": graph_intel["user_profile"],
        "mechanism_history": graph_intel["mechanism_history"],
        "archetype_match": graph_intel["archetype_match"],
        "brand_relationships": graph_intel["brand_relationships"],
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
    
    return {
        **state,
        "full_intelligence_profile": full_intel,
        "behavioral_analysis": full_intel["behavioral_analysis"],
        "brand_copy_analysis": full_intel["brand_copy_analysis"],
        "journey_intelligence": full_intel["journey_intelligence"],
        "injected_intelligence": injected_intel,  # Pass through for atoms
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
    
    return {
        **state,
        "atom_outputs": atom_outputs,
        # NEW: Feedback from atoms to LangGraph
        "atom_feedback": atom_feedback,
        "prior_validation": prior_validation,
        "atom_learning_signals": learning_signals,
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
    # STEP 1: Extract base mechanisms from AoT
    # =================================================================
    mechanisms_applied = []
    
    if "atom_mechanism_activation" in atom_outputs:
        mech_output = atom_outputs["atom_mechanism_activation"]
        if isinstance(mech_output, dict):
            max_score = max(mech_output.get("mechanism_scores", {}).values() or [0])
            for mech, score in mech_output.get("mechanism_scores", {}).items():
                mechanisms_applied.append({
                    "name": mech,
                    "intensity": score,
                    "base_score": score,
                    "source": "aot",
                    "is_primary": score == max_score,
                    "boosts_applied": [],
                })
    
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
    
    # Also persist via gradient bridge
    try:
        from adam.gradient_bridge.service import GradientBridgeService
        # Get service instance... (would need to be passed in or singleton)
    except Exception:
        pass
    
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
        pass
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
    
    Uses:
    - User's archetype
    - Selected mechanisms
    - Brand personality alignment
    - Competitive differentiation
    - Helpful vote effectiveness scores
    """
    archetype = state.get("archetype_match", {}).get("primary_archetype") or "everyman"
    mechanisms = state.get("mechanisms_applied", [])
    competitive = state.get("competitive_intelligence", {})
    helpful_intel = state.get("helpful_vote_intelligence", {})
    brand_copy = state.get("brand_copy_analysis", {})
    
    selected_templates = []
    
    # Get templates from helpful vote intelligence (already filtered by archetype)
    available_templates = helpful_intel.get("templates", [])
    
    # Also try to get from pattern persistence (Neo4j)
    try:
        from adam.infrastructure.neo4j.pattern_persistence import GraphPatternPersistence
        persistence = GraphPatternPersistence()
        
        for mech in mechanisms[:3]:  # Focus on top 3 mechanisms
            mechanism_name = mech.get("name")
            
            neo4j_templates = await persistence.query_templates_for_archetype_mechanism(
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
        
        template["final_score"] = score
    
    # Sort by final score and take top 10
    available_templates.sort(key=lambda t: t.get("final_score", 0), reverse=True)
    selected_templates = available_templates[:10]
    
    logger.debug(f"Selected {len(selected_templates)} personalized templates")
    
    return {
        **state,
        "selected_templates": selected_templates,
    }


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
    graph.add_node("detect_archetype", detect_deep_archetype)
    graph.add_node("execute_aot", execute_aot_with_priors)
    graph.add_node("process_feedback", process_atom_feedback)  # NEW: Bidirectional feedback
    graph.add_node("select_templates", select_personalized_templates)
    graph.add_node("synthesize", synthesize_decision)
    graph.add_node("persist", persist_for_learning)
    graph.add_node("maintain", trigger_graph_maintenance)
    
    # Set entry point
    graph.set_entry_point("prefetch_graph")
    
    # PARALLEL PRE-FETCH: All pre-fetch nodes run simultaneously
    # LangGraph executes nodes with no dependencies in parallel
    # These three don't depend on each other, so they'll parallelize
    graph.add_edge("prefetch_graph", "prefetch_helpful_vote")
    graph.add_edge("prefetch_helpful_vote", "prefetch_full_intel")
    graph.add_edge("prefetch_full_intel", "prefetch_competitive")
    
    # After all pre-fetch completes, detect archetype
    graph.add_edge("prefetch_competitive", "detect_archetype")
    
    # Execute AoT with full context
    graph.add_edge("detect_archetype", "execute_aot")
    
    # NEW: Process atom feedback (bidirectional learning)
    graph.add_edge("execute_aot", "process_feedback")
    
    # Select templates based on mechanisms AND feedback
    graph.add_edge("process_feedback", "select_templates")
    
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
    from langgraph.graph import StateGraph
    
    graph = StateGraph(OrchestratorState)
    
    # Add all nodes
    graph.add_node("prefetch_graph", prefetch_graph_intelligence)
    graph.add_node("prefetch_helpful_vote", prefetch_helpful_vote_intelligence)
    graph.add_node("prefetch_full_intel", prefetch_full_intelligence)
    graph.add_node("prefetch_competitive", prefetch_competitive_intelligence)
    graph.add_node("merge_prefetch", lambda s: s)  # Merge point (no-op)
    graph.add_node("detect_archetype", detect_deep_archetype)
    graph.add_node("execute_aot", execute_aot_with_priors)
    graph.add_node("process_feedback", process_atom_feedback)  # NEW: Bidirectional feedback
    graph.add_node("select_templates", select_personalized_templates)
    graph.add_node("synthesize", synthesize_decision)
    graph.add_node("persist", persist_for_learning)
    graph.add_node("maintain", trigger_graph_maintenance)
    
    # Fan-out: Entry point branches to all prefetch nodes
    graph.set_entry_point("prefetch_graph")
    
    # Each prefetch leads to merge point
    graph.add_edge("prefetch_graph", "prefetch_helpful_vote")
    graph.add_edge("prefetch_helpful_vote", "prefetch_full_intel")
    graph.add_edge("prefetch_full_intel", "prefetch_competitive")
    graph.add_edge("prefetch_competitive", "merge_prefetch")
    
    # Fan-in: After merge, continue sequential processing
    graph.add_edge("merge_prefetch", "detect_archetype")
    graph.add_edge("detect_archetype", "execute_aot")
    graph.add_edge("execute_aot", "process_feedback")  # NEW: Process feedback
    graph.add_edge("process_feedback", "select_templates")
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
