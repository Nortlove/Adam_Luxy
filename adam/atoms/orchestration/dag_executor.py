# =============================================================================
# ADAM Enhanced DAG Executor with LangGraph Integration
# Location: adam/atoms/orchestration/dag_executor.py
# =============================================================================

"""
ENHANCED DAG EXECUTOR WITH LANGGRAPH INTELLIGENCE

This module bridges the gap between LangGraph's orchestration and AoT's reasoning.

KEY CAPABILITIES:
1. Prior Injection - LangGraph pre-fetches intelligence, we inject it into atoms
2. Bidirectional Feedback - Atoms emit signals that LangGraph can consume
3. Context Enrichment - LangGraph state flows to atoms, atom outputs flow back
4. Learning Loop Completion - Ensures outcomes reach all systems

ARCHITECTURE:

    ┌─────────────────────────────────────────────────────────────────────┐
    │                       LangGraph Orchestrator                        │
    │     (pre-fetches graph intelligence, helpful vote data, etc.)       │
    └──────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                     DAGExecutorWithPriors                           │
    │                                                                     │
    │  1. Receives prior_context from LangGraph                           │
    │  2. Injects into AtomInput.ad_context                               │
    │  3. Executes atoms with enriched context                            │
    │  4. Collects feedback from atoms                                    │
    │  5. Returns outputs + feedback to LangGraph                         │
    │                                                                     │
    └──────────────────────────────┬──────────────────────────────────────┘
                                   │
                                   ▼
    ┌─────────────────────────────────────────────────────────────────────┐
    │                         AtomDAG                                     │
    │                (Existing atom execution engine)                     │
    └─────────────────────────────────────────────────────────────────────┘
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# PRIOR CONTEXT MODEL
# =============================================================================

@dataclass
class PriorContext:
    """
    Intelligence context from LangGraph to inject into atoms.
    
    This is what LangGraph pre-fetches and passes to atoms.
    """
    
    # Graph-based priors
    user_profile: Dict[str, Any] = field(default_factory=dict)
    mechanism_history: Dict[str, Any] = field(default_factory=dict)
    archetype: Optional[str] = None
    archetype_confidence: float = 0.5
    brand_relationships: Dict[str, Any] = field(default_factory=dict)
    
    # Helpful vote intelligence
    mechanism_effectiveness: Dict[str, float] = field(default_factory=dict)
    persuasive_templates: List[Dict[str, Any]] = field(default_factory=list)
    
    # Full intelligence from integrator
    behavioral_analysis: Dict[str, Any] = field(default_factory=dict)
    brand_personality: Optional[str] = None
    brand_cialdini: Dict[str, float] = field(default_factory=dict)
    brand_aaker: Dict[str, float] = field(default_factory=dict)
    customer_cluster: Optional[str] = None
    
    # Journey intelligence
    journey_products: List[Dict[str, Any]] = field(default_factory=list)
    
    # Competitive intelligence (NEW)
    competitor_mechanisms: List[str] = field(default_factory=list)
    underutilized_mechanisms: List[str] = field(default_factory=list)
    counter_strategies: List[Dict[str, Any]] = field(default_factory=list)
    
    # Deep archetype detection (NEW)
    deep_archetype_scores: Dict[str, float] = field(default_factory=dict)
    linguistic_markers: List[str] = field(default_factory=list)
    
    # =========================================================================
    # POST-INGESTION EXTENSIONS (Phase 2-3 of POST_INGESTION_MASTER_PLAN)
    # =========================================================================
    
    # Product advertisement psychology profile (from create_advertisement_profile)
    # Populated by profile_ad_copy LangGraph node
    product_ad_profile: Dict[str, Any] = field(default_factory=dict)
    # Format: {primary_persuasion, primary_emotion, primary_value, linguistic_style,
    #          all_techniques: [...], emotional_appeals: [...], value_propositions: [...]}
    
    # Expanded granular type (from ExpandedTypeIntegrationService.infer_type_from_text)
    # 1.9M+ possible type combinations from empirical psychology framework
    expanded_type: Dict[str, Any] = field(default_factory=dict)
    # Format: {motivation, decision_style, emotional_intensity, regulatory_focus,
    #          cognitive_load, temporal_orientation, social_influence,
    #          optimal_mechanism_sequence: [...], message_framing, urgency_appropriateness}
    
    # Customer-Ad alignment scores (from calculate_alignment, 7 matrices)
    alignment_scores: Dict[str, float] = field(default_factory=dict)
    # Format: {motivation_value: 0.85, decision_linguistic: 0.7, regulatory_emotional: 0.6,
    #          emotional: 0.75, mechanism_susceptibility: 0.8, cognitive_complexity: 0.9,
    #          archetype_personality: 0.7, overall: 0.78}
    alignment_recommendation: str = ""  # "strong_match", "moderate_match", "weak_match", "mismatch"
    
    # Dimensional priors from ingestion (430+ dimensions aggregated)
    # Loaded from ingestion_merged_priors.json via LearnedPriorsService
    dimensional_priors: Dict[str, Any] = field(default_factory=dict)
    # Format: {motivation_distribution: {...}, decision_style_distribution: {...},
    #          mechanism_receptivity: {...}, persuasion_techniques: {...}}
    
    # Category-level archetype distribution (population base rates)
    category_archetype_distribution: Dict[str, float] = field(default_factory=dict)
    # Format: {achiever: 0.22, explorer: 0.18, connector: 0.25, ...}
    
    # =========================================================================
    # NDF (Nonconscious Decision Fingerprint) Intelligence
    # =========================================================================
    
    # Real-time NDF extracted from user text (8 dims)
    ndf_profile: Dict[str, float] = field(default_factory=dict)
    # Format: {approach_avoidance, temporal_horizon, social_calibration,
    #          uncertainty_tolerance, status_sensitivity, cognitive_engagement,
    #          arousal_seeking, cognitive_velocity}
    
    # NDF-derived mechanism susceptibility (7 Cialdini mechanisms)
    ndf_mechanism_susceptibility: Dict[str, float] = field(default_factory=dict)
    # Format: {reciprocity: 0.7, commitment: 0.6, social_proof: 0.8, ...}
    
    # Population NDF priors (from 1B+ review ingestion)
    ndf_population_priors: Dict[str, Any] = field(default_factory=dict)
    
    # Archetype-conditioned NDF profile
    ndf_archetype_profile: Dict[str, float] = field(default_factory=dict)
    
    # =========================================================================
    # DSP GRAPH INTELLIGENCE (from Neo4j DSPConstruct nodes + edges)
    # =========================================================================
    
    # Empirical effectiveness from EMPIRICALLY_EFFECTIVE edges (1,148 edges)
    dsp_empirical_effectiveness: Dict[str, Dict] = field(default_factory=dict)
    # Format: {mechanism_id: {success_rate, sample_size, categories_seen}}
    
    # Alignment matrix edges (209 edges across 7 matrices)
    dsp_alignment_edges: List[Dict[str, Any]] = field(default_factory=list)
    # Format: [{edge_type, target_id, strength, matrix}]
    
    # Category moderation deltas from CONTEXTUALLY_MODERATES (26 edges)
    dsp_category_moderation: Dict[str, float] = field(default_factory=dict)
    # Format: {mechanism_id: delta}
    
    # Relationship amplification boosts from MODERATES (107 edges)
    dsp_relationship_boosts: Dict[str, float] = field(default_factory=dict)
    # Format: {mechanism_id: boost_factor}
    
    # Decision style → mechanism susceptibility from SUSCEPTIBLE_TO
    dsp_mechanism_susceptibility: Dict[str, float] = field(default_factory=dict)
    # Format: {mechanism_id: susceptibility_strength}
    
    # =========================================================================
    # TYPE SYSTEM GRAPH INFERENCE (from 1.9M GranularType nodes in Neo4j)
    # =========================================================================
    
    # Graph-inferred mechanism priors from type system traversal
    graph_mechanism_priors: Dict[str, float] = field(default_factory=dict)
    # Format: {authority: 0.9, commitment: 0.85, reciprocity: 0.6}
    
    # Full graph type inference context (type dimensions, all recommendations)
    graph_type_inference: Dict[str, Any] = field(default_factory=dict)
    # Format: {type_id, type_found, dimensions, graph_mechanism_priors,
    #          graph_value_propositions, graph_style_recommendations, ...}
    
    # Metadata
    sources_used: List[str] = field(default_factory=list)
    confidence_level: str = "low"  # low, medium, high
    
    @classmethod
    def from_langgraph_state(cls, state: Dict[str, Any]) -> "PriorContext":
        """
        Create PriorContext from LangGraph OrchestratorState.
        
        This is the primary way to convert LangGraph state to prior context.
        """
        return cls(
            user_profile=state.get("user_profile", {}),
            mechanism_history=state.get("mechanism_history", {}),
            archetype=state.get("archetype_match", {}).get("primary_archetype"),
            archetype_confidence=state.get("archetype_match", {}).get("confidence", 0.5),
            brand_relationships=state.get("brand_relationships", {}),
            
            mechanism_effectiveness=state.get("mechanism_priors", {}),
            persuasive_templates=state.get("persuasive_templates", [])
                                 or state.get("selected_templates", []),
            
            behavioral_analysis=state.get("behavioral_analysis", {}),
            brand_personality=state.get("brand_copy_analysis", {}).get("primary_personality"),
            brand_cialdini=state.get("brand_copy_analysis", {}).get("cialdini_scores", {}),
            brand_aaker=state.get("brand_copy_analysis", {}).get("aaker_scores", {}),
            customer_cluster=state.get("journey_intelligence", {}).get("customer_cluster"),
            
            journey_products=state.get("journey_intelligence", {}).get("products", []),
            
            # Competitive (NEW)
            competitor_mechanisms=state.get("competitive_intelligence", {})
                                  .get("competitor_mechanisms", []),
            underutilized_mechanisms=state.get("competitive_intelligence", {})
                                     .get("underutilized_mechanisms", []),
            counter_strategies=state.get("competitive_intelligence", {})
                              .get("counter_strategies", []),
            
            # Deep archetype (NEW)
            deep_archetype_scores=state.get("deep_archetype", {})
                                  .get("archetype_scores", {}),
            linguistic_markers=state.get("deep_archetype", {})
                              .get("markers_detected", []),
            
            # Post-ingestion extensions (Phase 2-3)
            product_ad_profile=state.get("product_ad_profile", {}),
            expanded_type=state.get("expanded_type", {}),
            alignment_scores=state.get("alignment_scores", {}),
            alignment_recommendation=state.get("alignment_recommendation", ""),
            dimensional_priors=state.get("dimensional_priors", {}),
            category_archetype_distribution=state.get("category_archetype_distribution", {}),
            
            # NDF Intelligence
            ndf_profile=state.get("ndf_profile", {}),
            ndf_mechanism_susceptibility=state.get("ndf_mechanism_susceptibility", {}),
            ndf_population_priors=state.get("ndf_population_priors", {}),
            ndf_archetype_profile=state.get("ndf_archetype_profile", {}),
            
            # DSP Graph Intelligence (from injected intelligence or state)
            dsp_empirical_effectiveness=state.get("dsp_graph_intelligence", {})
                                        .get("empirical_effectiveness", {}),
            dsp_alignment_edges=state.get("dsp_graph_intelligence", {})
                               .get("alignment_edges", []),
            dsp_category_moderation=state.get("dsp_graph_intelligence", {})
                                   .get("category_moderation", {}),
            dsp_relationship_boosts=state.get("dsp_graph_intelligence", {})
                                   .get("relationship_amplification", {}),
            dsp_mechanism_susceptibility=state.get("dsp_graph_intelligence", {})
                                        .get("mechanism_susceptibility", {}),
            
            # Type System Graph Inference (from 1.9M GranularType traversal)
            graph_mechanism_priors=state.get("graph_mechanism_priors", {}),
            graph_type_inference=state.get("graph_type_inference", {}),
            
            sources_used=state.get("full_intelligence_profile", {})
                        .get("sources", []),
            confidence_level=_calculate_confidence(state),
        )
    
    def to_atom_context(self) -> Dict[str, Any]:
        """
        Convert to format injectable into AtomInput.ad_context.
        """
        return {
            # Graph priors
            "graph_priors": {
                "user_profile": self.user_profile,
                "mechanism_history": self.mechanism_history,
                "archetype": self.archetype,
                "archetype_confidence": self.archetype_confidence,
            },
            
            # Helpful vote priors
            "helpful_vote_priors": {
                "mechanism_effectiveness": self.mechanism_effectiveness,
                "templates": self.persuasive_templates[:10],
            },
            
            # Full intelligence
            "full_intelligence": {
                "behavioral": self.behavioral_analysis,
                "brand_personality": self.brand_personality,
                "brand_cialdini": self.brand_cialdini,
                "brand_aaker": self.brand_aaker,
                "customer_cluster": self.customer_cluster,
            },
            
            # Journey
            "journey_intelligence": {
                "products": self.journey_products[:5],
            },
            
            # Competitive (NEW)
            "competitive_intelligence": {
                "competitor_mechanisms": self.competitor_mechanisms,
                "underutilized": self.underutilized_mechanisms,
                "counter_strategies": self.counter_strategies[:3],
            },
            
            # Deep archetype (NEW)
            "deep_archetype": {
                "scores": self.deep_archetype_scores,
                "markers": self.linguistic_markers[:10],
            },
            
            # Post-ingestion: Product Ad Psychology (Phase 2-3)
            "product_ad_psychology": {
                "profile": self.product_ad_profile,
                "has_profile": bool(self.product_ad_profile),
            },
            
            # Post-ingestion: Expanded Granular Type (1.9M types)
            "expanded_customer_type": {
                "type": self.expanded_type,
                "optimal_mechanism_sequence": self.expanded_type.get("optimal_mechanism_sequence", []),
                "message_framing": self.expanded_type.get("message_framing", ""),
                "urgency_appropriateness": self.expanded_type.get("urgency_appropriateness", 0.5),
            },
            
            # Post-ingestion: Customer-Ad Alignment (7 matrices)
            "alignment": {
                "scores": self.alignment_scores,
                "recommendation": self.alignment_recommendation,
                "overall": self.alignment_scores.get("overall", 0.0),
            },
            
            # Post-ingestion: Dimensional Priors (430+ dims from corpus)
            "dimensional_priors": self.dimensional_priors,
            
            # Post-ingestion: Category population base rates
            "category_archetype_distribution": self.category_archetype_distribution,
            
            # NDF (Nonconscious Decision Fingerprint) Intelligence
            "ndf_intelligence": {
                "profile": self.ndf_profile,
                "mechanism_susceptibility": self.ndf_mechanism_susceptibility,
                "population_priors": self.ndf_population_priors,
                "archetype_profile": self.ndf_archetype_profile,
                "has_ndf": bool(self.ndf_profile),
                "has_population_priors": bool(self.ndf_population_priors),
            },
            
            # DSP Graph Intelligence (from Neo4j 2,400+ DSPConstruct edges)
            "dsp_graph_intelligence": {
                "empirical_effectiveness": self.dsp_empirical_effectiveness,
                "alignment_edges": self.dsp_alignment_edges,
                "category_moderation": self.dsp_category_moderation,
                "relationship_amplification": self.dsp_relationship_boosts,
                "mechanism_susceptibility": self.dsp_mechanism_susceptibility,
                "has_dsp": bool(self.dsp_empirical_effectiveness) or bool(self.dsp_alignment_edges),
            },
            
            # Type System Graph Inference (1.9M GranularType nodes)
            "graph_mechanism_priors": self.graph_mechanism_priors,
            "graph_type_inference": self.graph_type_inference,
            
            # Flags
            "has_langgraph_priors": True,
            "has_ingestion_priors": bool(self.dimensional_priors) or bool(self.alignment_scores),
            "has_ndf_intelligence": bool(self.ndf_profile) or bool(self.ndf_population_priors),
            "has_dsp_intelligence": bool(self.dsp_empirical_effectiveness) or bool(self.dsp_alignment_edges),
            "has_graph_type_system": bool(self.graph_mechanism_priors),
            "prior_confidence": self.confidence_level,
            "prior_sources": self.sources_used,
        }


def _calculate_confidence(state: Dict[str, Any]) -> str:
    """Calculate confidence level from LangGraph state."""
    sources = []
    
    if state.get("user_profile"):
        sources.append("user")
    if state.get("mechanism_priors"):
        sources.append("helpful_vote")
    if state.get("brand_copy_analysis"):
        sources.append("brand")
    if state.get("competitive_intelligence"):
        sources.append("competitive")
    if state.get("deep_archetype"):
        sources.append("archetype")
    if state.get("alignment_scores"):
        sources.append("alignment")
    if state.get("dsp_graph_intelligence"):
        sources.append("dsp_graph")
    
    if len(sources) >= 5:
        return "high"
    elif len(sources) >= 3:
        return "high"
    elif len(sources) >= 2:
        return "medium"
    return "low"


# =============================================================================
# ATOM FEEDBACK MODEL
# =============================================================================

class FeedbackType(str, Enum):
    """Types of feedback atoms can emit."""
    MECHANISM_SELECTED = "mechanism_selected"
    MECHANISM_REJECTED = "mechanism_rejected"
    CONFIDENCE_SIGNAL = "confidence_signal"
    EVIDENCE_CONFLICT = "evidence_conflict"
    PRIOR_VALIDATED = "prior_validated"
    PRIOR_OVERRIDDEN = "prior_overridden"
    LEARNING_SIGNAL = "learning_signal"


@dataclass
class AtomFeedback:
    """
    Feedback from an atom back to LangGraph.
    
    This completes the bidirectional loop - atoms can signal back
    to LangGraph about what worked, what didn't, and what should be learned.
    """
    
    atom_id: str
    feedback_type: FeedbackType
    
    # What the feedback is about
    target_entity: str = ""  # e.g., mechanism name, archetype, brand
    
    # Scores/values
    score: float = 0.5
    confidence: float = 0.5
    
    # Context
    reasoning: str = ""
    evidence_used: List[str] = field(default_factory=list)
    
    # For learning
    should_propagate: bool = True
    learning_weight: float = 1.0
    
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# EXECUTION RESULT MODEL
# =============================================================================

class ExecutionResultWithFeedback(BaseModel):
    """
    Result of executing DAG with priors - includes feedback for LangGraph.
    """
    
    # Standard outputs
    request_id: str
    success: bool = True
    
    # Atom outputs (keyed by atom_id)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    
    # Final decisions
    final_mechanisms: List[str] = Field(default_factory=list)
    mechanism_weights: Dict[str, float] = Field(default_factory=dict)
    overall_confidence: float = 0.5
    
    # Feedback for LangGraph (NEW)
    feedback: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Prior validation (NEW) - did atoms agree with LangGraph priors?
    prior_validation: Dict[str, Any] = Field(default_factory=dict)
    
    # Learning signals to route back (NEW)
    learning_signals: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Timing
    duration_ms: float = 0.0
    atoms_executed: int = 0


# =============================================================================
# LIGHTWEIGHT BRIDGE (Fallback when Neo4j unavailable)
# =============================================================================

class LightweightBridge:
    """
    Lightweight bridge for DAG execution when Neo4j is unavailable.
    
    Provides minimal interface compatibility with InteractionBridge,
    using in-memory data and learned priors instead of graph queries.
    """
    
    def __init__(self):
        self._context_cache: Dict[str, Any] = {}
        self._decision_cache: Dict[str, Any] = {}
        self._priors = None
        logger.info("LightweightBridge initialized (no Neo4j)")
    
    async def get_user_context(
        self,
        user_id: str,
        request_id: str,
    ) -> Dict[str, Any]:
        """Get user context from priors instead of graph."""
        try:
            if self._priors is None:
                from adam.core.learning.learned_priors_integration import get_learned_priors
                self._priors = get_learned_priors()
            
            # Build context from priors
            context = {
                "user_id": user_id,
                "request_id": request_id,
                "global_archetype_distribution": self._priors._global_archetype_distribution,
                "temporal_patterns": self._priors._temporal_patterns,
                "source": "lightweight_bridge",
            }
            
            self._context_cache[user_id] = context
            return context
            
        except Exception as e:
            logger.debug(f"LightweightBridge.get_user_context error: {e}")
            return {"user_id": user_id, "request_id": request_id}
    
    async def get_brand_context(
        self,
        brand_name: str,
    ) -> Dict[str, Any]:
        """Get brand context from priors."""
        try:
            if self._priors is None:
                from adam.core.learning.learned_priors_integration import get_learned_priors
                self._priors = get_learned_priors()
            
            brand_priors = self._priors._brand_archetype_priors.get(brand_name, {})
            return {
                "brand": brand_name,
                "archetype_priors": brand_priors,
                "source": "lightweight_bridge",
            }
            
        except Exception as e:
            logger.debug(f"LightweightBridge.get_brand_context error: {e}")
            return {"brand": brand_name}
    
    async def get_category_context(
        self,
        category: str,
    ) -> Dict[str, Any]:
        """Get category context from priors."""
        try:
            if self._priors is None:
                from adam.core.learning.learned_priors_integration import get_learned_priors
                self._priors = get_learned_priors()
            
            category_priors = self._priors._category_priors.get(category, {})
            return {
                "category": category,
                "archetype_priors": category_priors,
                "source": "lightweight_bridge",
            }
            
        except Exception as e:
            logger.debug(f"LightweightBridge.get_category_context error: {e}")
            return {"category": category}
    
    async def persist_decision(
        self,
        decision_id: str,
        decision_data: Dict[str, Any],
    ) -> bool:
        """Cache decision for later persistence."""
        self._decision_cache[decision_id] = {
            **decision_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pending_persistence": True,
        }
        logger.debug(f"LightweightBridge cached decision {decision_id}")
        return True
    
    async def emit_learning_signal(
        self,
        signal_type: str,
        signal_data: Dict[str, Any],
    ) -> bool:
        """Emit learning signal to in-memory hub."""
        try:
            from adam.core.learning.unified_learning_hub import get_unified_learning_hub
            hub = get_unified_learning_hub()
            
            # Convert to unified signal format
            from adam.core.learning.unified_learning_hub import (
                UnifiedLearningSignal,
                UnifiedSignalType,
            )
            
            signal = UnifiedLearningSignal(
                signal_type=UnifiedSignalType.MECHANISM_FEEDBACK,
                source_component="lightweight_bridge",
                archetype=signal_data.get("archetype", "unknown"),
                mechanism=signal_data.get("mechanism", "unknown"),
                confidence=signal_data.get("confidence", 0.5),
                payload=signal_data,
            )
            
            await hub.process_signal(signal)
            return True
            
        except Exception as e:
            logger.debug(f"LightweightBridge.emit_learning_signal error: {e}")
            return False


# =============================================================================
# ENHANCED DAG EXECUTOR
# =============================================================================

class DAGExecutorWithPriors:
    """
    Enhanced DAG executor that bridges LangGraph and AoT.
    
    This is the primary interface for LangGraph to invoke AoT with
    pre-fetched intelligence and receive feedback.
    
    Usage:
        executor = get_dag_executor()
        
        # Build prior context from LangGraph state
        priors = PriorContext.from_langgraph_state(state)
        
        # Execute with priors
        result = await executor.execute_with_priors(
            request_id="req_123",
            user_id="user_456",
            prior_context=priors,
        )
        
        # Process feedback
        for fb in result.feedback:
            if fb["feedback_type"] == "prior_overridden":
                # LangGraph should learn this
                pass
    """
    
    def __init__(self):
        """Initialize the executor."""
        self._dag = None
        self._blackboard = None
        self._bridge = None
        self._feedback_buffer: List[AtomFeedback] = []
        self._initialized = False
    
    async def _ensure_initialized(self):
        """Lazy initialization of dependencies with fallback support."""
        if self._initialized:
            return
        
        try:
            from adam.blackboard.service import get_blackboard_service
            from adam.graph_reasoning.bridge import get_interaction_bridge
            from adam.atoms.dag import AtomDAG
            
            # Get blackboard (now has in-memory fallback)
            self._blackboard = get_blackboard_service()
            
            # Try to get interaction bridge
            try:
                self._bridge = get_interaction_bridge()
            except Exception as bridge_error:
                logger.warning(f"InteractionBridge unavailable: {bridge_error}, using lightweight mode")
                self._bridge = LightweightBridge()
            
            self._dag = AtomDAG(
                blackboard=self._blackboard,
                bridge=self._bridge,
            )
            self._initialized = True
            logger.info("DAGExecutorWithPriors initialized successfully")
            
        except Exception as e:
            logger.warning(f"Failed to initialize DAG executor: {e}")
            # Create lightweight fallback DAG
            self._create_lightweight_fallback()
    
    def _create_lightweight_fallback(self):
        """Create a lightweight DAG executor without full dependencies."""
        try:
            from adam.blackboard.service import InMemoryBlackboardCache
            
            # Create minimal dependencies
            self._blackboard = type('MockBlackboard', (), {
                'cache': InMemoryBlackboardCache(),
                'read_zone1': lambda *args, **kwargs: None,
                'write_zone1': lambda *args, **kwargs: True,
                'read_zone2': lambda *args, **kwargs: None,
                'write_zone2': lambda *args, **kwargs: True,
            })()
            
            self._bridge = LightweightBridge()
            
            # Create lightweight DAG with minimal atoms
            from adam.atoms.dag import AtomDAG, AtomNode
            
            lightweight_nodes = [
                AtomNode(
                    atom_id="user_state",
                    atom_class="UserStateAtom",
                    dependencies=[],
                    execution_order=1,
                ),
                AtomNode(
                    atom_id="mechanism_activation",
                    atom_class="MechanismActivationAtom",
                    dependencies=["user_state"],
                    execution_order=2,
                ),
            ]
            
            self._dag = AtomDAG(
                blackboard=self._blackboard,
                bridge=self._bridge,
                nodes=lightweight_nodes,
            )
            self._initialized = True
            logger.info("DAGExecutorWithPriors initialized in lightweight mode")
            
        except Exception as e:
            logger.error(f"Failed to create lightweight fallback: {e}")
            self._initialized = False
    
    async def execute(
        self,
        request_id: str,
        user_id: str,
    ) -> ExecutionResultWithFeedback:
        """
        Execute DAG without priors (fallback/compatibility).
        """
        return await self.execute_with_priors(
            request_id=request_id,
            user_id=user_id,
            prior_context=None,
        )
    
    async def execute_with_priors(
        self,
        request_id: str,
        user_id: str,
        prior_context: Optional[PriorContext] = None,
        ad_context: Optional[Dict[str, Any]] = None,
        langgraph_state: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResultWithFeedback:
        """
        Execute the atom DAG with LangGraph intelligence injected.
        
        This is the main entry point for LangGraph → AoT communication.
        
        Args:
            request_id: Unique request identifier
            user_id: User making the request
            prior_context: Pre-built PriorContext (if available)
            ad_context: Additional ad context to merge
            langgraph_state: Raw LangGraph state (alternative to prior_context)
            
        Returns:
            ExecutionResultWithFeedback with outputs and feedback
        """
        await self._ensure_initialized()
        
        start_time = datetime.now(timezone.utc)
        self._feedback_buffer = []  # Clear previous feedback
        
        result = ExecutionResultWithFeedback(request_id=request_id)
        
        # Build prior context if not provided
        if prior_context is None and langgraph_state:
            prior_context = PriorContext.from_langgraph_state(langgraph_state)
        
        try:
            if not self._dag:
                raise RuntimeError("DAG not initialized")
            
            # Build request context with injected priors
            request_context = await self._build_enriched_request_context(
                request_id=request_id,
                user_id=user_id,
                prior_context=prior_context,
                ad_context=ad_context,
            )
            
            # Execute the DAG
            dag_result = await self._dag.execute(
                request_id=request_id,
                request_context=request_context,
            )
            
            # Extract outputs
            result.success = dag_result.success
            result.outputs = {
                atom_id: self._serialize_output(output)
                for atom_id, output in dag_result.atom_outputs.items()
            }
            result.final_mechanisms = dag_result.final_mechanisms
            result.mechanism_weights = dag_result.mechanism_weights
            result.overall_confidence = dag_result.overall_confidence
            result.atoms_executed = dag_result.atoms_executed
            
            # Collect feedback from atoms
            result.feedback = [
                self._serialize_feedback(fb) 
                for fb in self._feedback_buffer
            ]
            
            # Validate priors against atom decisions
            if prior_context:
                result.prior_validation = self._validate_priors(
                    prior_context, dag_result
                )
            
            # Collect learning signals
            result.learning_signals = self._extract_learning_signals(dag_result)
            
        except Exception as e:
            logger.error(f"DAG execution with priors failed: {e}")
            result.success = False
        
        end_time = datetime.now(timezone.utc)
        result.duration_ms = (end_time - start_time).total_seconds() * 1000
        
        return result
    
    async def _build_enriched_request_context(
        self,
        request_id: str,
        user_id: str,
        prior_context: Optional[PriorContext],
        ad_context: Optional[Dict[str, Any]],
    ):
        """
        Build RequestContext with LangGraph priors injected.
        
        CRITICAL: request_id is required by RequestContext model.
        """
        from adam.blackboard.models.zone1_context import (
            RequestContext,
            UserIntelligencePackage,
        )
        
        # Start with basic user intelligence
        user_intel = UserIntelligencePackage(user_id=user_id)
        
        # Inject prior context if available
        if prior_context:
            # Enrich user intelligence with graph priors
            user_intel = await self._enrich_user_intelligence(
                user_intel, prior_context
            )
        
        # Build ad context with priors
        enriched_ad_context = ad_context.copy() if ad_context else {}
        if prior_context:
            enriched_ad_context.update(prior_context.to_atom_context())
        
        # Build request context with required request_id
        return RequestContext(
            request_id=request_id,
            user_intelligence=user_intel,
            ad_context=enriched_ad_context,
        )
    
    async def _enrich_user_intelligence(
        self,
        user_intel,
        prior_context: PriorContext,
    ):
        """
        Enrich UserIntelligencePackage with LangGraph priors.
        """
        from adam.graph_reasoning.models.graph_context import (
            MechanismHistory,
            MechanismEffectiveness,
        )
        
        # Add mechanism history from priors
        if prior_context.mechanism_effectiveness:
            mechanism_list = []
            for mech_id, effectiveness in prior_context.mechanism_effectiveness.items():
                mechanism_list.append(MechanismEffectiveness(
                    mechanism_id=mech_id,
                    mechanism_name=mech_id,
                    success_rate=effectiveness,
                    effect_size=effectiveness,
                    trial_count=10,  # Assume some baseline
                    confidence=0.7,
                ))
            
            # Get top mechanisms
            top_mechs = sorted(
                mechanism_list,
                key=lambda m: m.success_rate,
                reverse=True,
            )[:5]
            
            user_intel.mechanism_history = MechanismHistory(
                user_id=user_intel.user_id,
                mechanism_effectiveness=mechanism_list,
                top_mechanisms=[m.mechanism_id for m in top_mechs],
            )
        
        # Add archetype if detected
        if prior_context.archetype:
            if not hasattr(user_intel, '_prior_archetype'):
                user_intel._prior_archetype = prior_context.archetype
                user_intel._prior_archetype_confidence = prior_context.archetype_confidence
        
        return user_intel
    
    def _validate_priors(
        self,
        prior_context: PriorContext,
        dag_result,
    ) -> Dict[str, Any]:
        """
        Compare LangGraph priors against atom decisions.
        
        This feedback helps LangGraph learn when its priors are accurate.
        """
        validation = {
            "archetype_aligned": False,
            "mechanisms_aligned": [],
            "mechanisms_overridden": [],
            "effectiveness_validated": {},
        }
        
        # Check archetype alignment
        if prior_context.archetype:
            # Get archetype from atom outputs
            user_state = dag_result.atom_outputs.get("atom_user_state")
            if user_state and hasattr(user_state, "secondary_assessments"):
                atom_archetype = user_state.secondary_assessments.get("archetype")
                validation["archetype_aligned"] = (
                    atom_archetype == prior_context.archetype
                )
                
                if not validation["archetype_aligned"]:
                    # Emit feedback
                    self._feedback_buffer.append(AtomFeedback(
                        atom_id="atom_user_state",
                        feedback_type=FeedbackType.PRIOR_OVERRIDDEN,
                        target_entity="archetype",
                        score=0.0,
                        reasoning=f"Prior archetype '{prior_context.archetype}' "
                                  f"overridden by '{atom_archetype}'",
                    ))
        
        # Check mechanism alignment
        if prior_context.mechanism_effectiveness:
            final_mechs = set(dag_result.final_mechanisms)
            prior_mechs = set(prior_context.mechanism_effectiveness.keys())
            
            validation["mechanisms_aligned"] = list(final_mechs & prior_mechs)
            validation["mechanisms_overridden"] = list(final_mechs - prior_mechs)
            
            # Check if top prior mechanism was selected
            if prior_context.mechanism_effectiveness:
                top_prior = max(
                    prior_context.mechanism_effectiveness.items(),
                    key=lambda x: x[1]
                )[0]
                
                validation["effectiveness_validated"] = {
                    "top_prior_mechanism": top_prior,
                    "top_prior_selected": top_prior in final_mechs,
                }
                
                # Emit feedback
                if top_prior in final_mechs:
                    self._feedback_buffer.append(AtomFeedback(
                        atom_id="atom_mechanism_activation",
                        feedback_type=FeedbackType.PRIOR_VALIDATED,
                        target_entity=top_prior,
                        score=1.0,
                        reasoning=f"Top prior mechanism '{top_prior}' was selected",
                    ))
        
        return validation
    
    def _extract_learning_signals(
        self,
        dag_result,
    ) -> List[Dict[str, Any]]:
        """
        Extract learning signals from atom execution for routing back to LangGraph.
        """
        signals = []
        
        for atom_id, output in dag_result.atom_outputs.items():
            if output and hasattr(output, "learning_signals"):
                for signal in (output.learning_signals or []):
                    signals.append({
                        "source": atom_id,
                        "signal": signal,
                    })
        
        # Add feedback signals
        for fb in self._feedback_buffer:
            if fb.should_propagate:
                signals.append({
                    "source": fb.atom_id,
                    "signal": {
                        "type": fb.feedback_type.value,
                        "entity": fb.target_entity,
                        "score": fb.score,
                        "reasoning": fb.reasoning,
                    },
                })
        
        return signals
    
    def _serialize_output(self, output) -> Dict[str, Any]:
        """Serialize atom output for LangGraph."""
        if output is None:
            return {}
        
        if hasattr(output, "model_dump"):
            return output.model_dump()
        elif hasattr(output, "__dict__"):
            return {
                k: v for k, v in output.__dict__.items()
                if not k.startswith("_")
            }
        return {}
    
    def _serialize_feedback(self, feedback: AtomFeedback) -> Dict[str, Any]:
        """Serialize feedback for return to LangGraph."""
        return {
            "atom_id": feedback.atom_id,
            "feedback_type": feedback.feedback_type.value,
            "target_entity": feedback.target_entity,
            "score": feedback.score,
            "confidence": feedback.confidence,
            "reasoning": feedback.reasoning,
            "evidence_used": feedback.evidence_used,
            "should_propagate": feedback.should_propagate,
            "learning_weight": feedback.learning_weight,
        }
    
    def add_feedback(self, feedback: AtomFeedback):
        """
        Allow atoms to add feedback during execution.
        
        Atoms can call this to signal back to LangGraph.
        """
        self._feedback_buffer.append(feedback)
    
    def get_execution_plan(self) -> Dict[str, Any]:
        """Get execution plan for debugging."""
        if self._dag:
            return self._dag.get_execution_plan()
        return {}


# =============================================================================
# SINGLETON
# =============================================================================

_executor: Optional[DAGExecutorWithPriors] = None


def get_dag_executor() -> DAGExecutorWithPriors:
    """
    Get singleton DAG executor.
    
    This is the entry point for LangGraph to access the AoT system.
    """
    global _executor
    if _executor is None:
        _executor = DAGExecutorWithPriors()
    return _executor
