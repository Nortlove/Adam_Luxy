"""
ADAM Three Machines Integration
===============================

This module bridges Review Intelligence with ADAM's three core systems:

1. NEO4J GRAPH DATABASE
   - Stores psychological patterns
   - Tracks mechanism effectiveness
   - Enables graph-based recommendations
   
2. LANGGRAPH ORCHESTRATION
   - Pre-fetches relevant priors
   - Coordinates cross-system optimization
   - Manages workflow context
   
3. ATOM-OF-THOUGHT (AoT)
   - Injects psychological intelligence into atoms
   - Provides context for reasoning
   - Enables mechanism activation decisions

THE COOKIE-LESS VALUE CHAIN:
Review Data → Extractors → Unified Intelligence → Three Machines → Ecosystem Outputs
             (Google, Yelp, Twitter, etc.)       (Graph, LangGraph, AoT)   (DSP, SSP, Agency)
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

from . import DataSource, IntelligenceLayer
from .orchestrator import UnifiedIntelligence, ReviewIntelligenceOrchestrator

logger = logging.getLogger(__name__)


# =============================================================================
# NEO4J GRAPH INTEGRATION
# =============================================================================

@dataclass
class GraphSchemaExtension:
    """Schema extensions for review intelligence in Neo4j."""
    
    # New node types
    node_labels = [
        "PsychologicalSegment",
        "LocationProfile",
        "EmotionalState",
        "InfluencerProfile",
        "PersuasiveTemplate",
        "ReviewerArchetype",
        "CategoryProfile",
    ]
    
    # New relationship types
    relationship_types = [
        # Effectiveness relationships
        "MECHANISM_EFFECTIVE_FOR",  # (Mechanism)-[:MECHANISM_EFFECTIVE_FOR {score}]->(Segment)
        "ARCHETYPE_ALIGNED_WITH",   # (Brand)-[:ARCHETYPE_ALIGNED_WITH {score}]->(Archetype)
        
        # Location relationships
        "LOCATED_IN",              # (Business)-[:LOCATED_IN]->(Location)
        "HAS_PROFILE",             # (Location)-[:HAS_PROFILE]->(PsychologicalSegment)
        
        # Social relationships
        "INFLUENCES",              # (User)-[:INFLUENCES {score}]->(User)
        "SIMILAR_TO",              # (Segment)-[:SIMILAR_TO {score}]->(Segment)
        
        # Template relationships
        "EFFECTIVE_TEMPLATE_FOR",  # (Template)-[:EFFECTIVE_TEMPLATE_FOR {score}]->(Mechanism)
    ]


class Neo4jReviewIntelligence:
    """
    Integrates review intelligence with Neo4j graph database.
    
    This class handles:
    - Storing psychological profiles as nodes
    - Creating effectiveness relationships
    - Enabling graph-based queries for targeting
    """
    
    def __init__(self, driver=None):
        """
        Initialize with Neo4j driver.
        
        Args:
            driver: Neo4j driver instance (optional, will be injected)
        """
        self.driver = driver
    
    def create_schema(self):
        """Create schema constraints and indexes."""
        if not self.driver:
            logger.warning("Neo4j driver not available")
            return
        
        with self.driver.session() as session:
            # Create constraints
            constraints = [
                "CREATE CONSTRAINT IF NOT EXISTS FOR (p:PsychologicalSegment) REQUIRE p.segment_id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (l:LocationProfile) REQUIRE l.location_id IS UNIQUE",
                "CREATE CONSTRAINT IF NOT EXISTS FOR (t:PersuasiveTemplate) REQUIRE t.template_id IS UNIQUE",
            ]
            
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    logger.warning(f"Constraint creation: {e}")
            
            # Create indexes
            indexes = [
                "CREATE INDEX IF NOT EXISTS FOR (p:PsychologicalSegment) ON (p.scope_type, p.scope_value)",
                "CREATE INDEX IF NOT EXISTS FOR (l:LocationProfile) ON (l.state, l.city)",
            ]
            
            for index in indexes:
                try:
                    session.run(index)
                except Exception as e:
                    logger.warning(f"Index creation: {e}")
    
    def store_unified_intelligence(
        self,
        unified: UnifiedIntelligence,
    ) -> str:
        """
        Store unified intelligence in the graph.
        
        Creates:
        - PsychologicalSegment node
        - Archetype relationships
        - Mechanism effectiveness edges
        - Template nodes
        """
        if not self.driver:
            logger.warning("Neo4j driver not available - returning mock ID")
            return f"mock_{unified.scope_type}_{unified.scope_value}"
        
        segment_id = f"{unified.scope_type}:{unified.scope_value}"
        
        with self.driver.session() as session:
            # Create segment node
            session.run("""
                MERGE (s:PsychologicalSegment {segment_id: $segment_id})
                SET s.scope_type = $scope_type,
                    s.scope_value = $scope_value,
                    s.psychological_profile = $profile,
                    s.archetype_profile = $archetypes,
                    s.mechanism_effectiveness = $mechanisms,
                    s.sample_size = $sample_size,
                    s.updated_at = datetime()
            """, {
                "segment_id": segment_id,
                "scope_type": unified.scope_type,
                "scope_value": unified.scope_value,
                "profile": str(unified.psychological_profile),
                "archetypes": str(unified.archetype_profile),
                "mechanisms": str(unified.mechanism_effectiveness),
                "sample_size": unified.total_sample_size,
            })
            
            # Create archetype relationships
            for archetype, strength in unified.archetype_profile.items():
                session.run("""
                    MATCH (s:PsychologicalSegment {segment_id: $segment_id})
                    MERGE (a:Archetype {name: $archetype})
                    MERGE (s)-[r:HAS_ARCHETYPE]->(a)
                    SET r.strength = $strength
                """, {
                    "segment_id": segment_id,
                    "archetype": archetype,
                    "strength": strength,
                })
            
            # Create mechanism effectiveness relationships
            for mechanism, effectiveness in unified.mechanism_effectiveness.items():
                session.run("""
                    MATCH (s:PsychologicalSegment {segment_id: $segment_id})
                    MERGE (m:PersuasionMechanism {name: $mechanism})
                    MERGE (m)-[r:EFFECTIVE_FOR]->(s)
                    SET r.effectiveness = $effectiveness,
                        r.sample_size = $sample_size
                """, {
                    "segment_id": segment_id,
                    "mechanism": mechanism,
                    "effectiveness": effectiveness,
                    "sample_size": unified.total_sample_size,
                })
            
            # Store top templates
            for i, template in enumerate(unified.top_templates[:50]):
                template_id = f"{segment_id}:template:{i}"
                session.run("""
                    MATCH (s:PsychologicalSegment {segment_id: $segment_id})
                    MERGE (t:PersuasiveTemplate {template_id: $template_id})
                    SET t.text = $text,
                        t.mechanisms = $mechanisms,
                        t.helpful_score = $helpful_score
                    MERGE (t)-[:TEMPLATE_FOR]->(s)
                """, {
                    "segment_id": segment_id,
                    "template_id": template_id,
                    "text": template.get('text', ''),
                    "mechanisms": str(template.get('mechanisms', [])),
                    "helpful_score": template.get('helpful_score', 0),
                })
        
        logger.info(f"Stored unified intelligence for {segment_id}")
        return segment_id
    
    def query_optimal_mechanisms(
        self,
        scope_type: str,
        scope_value: str,
        top_n: int = 5,
    ) -> List[Dict[str, Any]]:
        """Query optimal mechanisms for a segment."""
        if not self.driver:
            return []
        
        with self.driver.session() as session:
            result = session.run("""
                MATCH (s:PsychologicalSegment {scope_type: $scope_type, scope_value: $scope_value})
                MATCH (m:PersuasionMechanism)-[r:EFFECTIVE_FOR]->(s)
                RETURN m.name AS mechanism, r.effectiveness AS effectiveness
                ORDER BY r.effectiveness DESC
                LIMIT $top_n
            """, {
                "scope_type": scope_type,
                "scope_value": scope_value,
                "top_n": top_n,
            })
            
            return [dict(record) for record in result]
    
    def query_similar_segments(
        self,
        segment_id: str,
        similarity_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Find similar psychological segments."""
        if not self.driver:
            return []
        
        with self.driver.session() as session:
            # Use archetype overlap for similarity
            result = session.run("""
                MATCH (s1:PsychologicalSegment {segment_id: $segment_id})-[r1:HAS_ARCHETYPE]->(a:Archetype)
                MATCH (s2:PsychologicalSegment)-[r2:HAS_ARCHETYPE]->(a)
                WHERE s1 <> s2
                WITH s2, 
                     SUM(r1.strength * r2.strength) AS similarity,
                     COUNT(a) AS overlap_count
                WHERE similarity > $threshold
                RETURN s2.segment_id AS segment_id, 
                       s2.scope_type AS scope_type,
                       s2.scope_value AS scope_value,
                       similarity
                ORDER BY similarity DESC
                LIMIT 10
            """, {
                "segment_id": segment_id,
                "threshold": similarity_threshold,
            })
            
            return [dict(record) for record in result]


# =============================================================================
# LANGGRAPH INTEGRATION
# =============================================================================

class LangGraphPriorProvider:
    """
    Provides psychological priors to LangGraph workflows.
    
    LangGraph uses these priors to:
    - Pre-fetch relevant intelligence before atom execution
    - Inject context into workflow nodes
    - Make routing decisions based on psychological profiles
    """
    
    def __init__(
        self,
        orchestrator: Optional[ReviewIntelligenceOrchestrator] = None,
    ):
        self.orchestrator = orchestrator
        self._prior_cache: Dict[str, Dict[str, Any]] = {}
    
    def get_priors(
        self,
        scope_type: str,
        scope_value: str,
    ) -> Dict[str, Any]:
        """
        Get psychological priors for a scope.
        
        This is called by LangGraph nodes before atom execution
        to provide relevant context.
        """
        cache_key = f"{scope_type}:{scope_value}"
        
        # Check cache
        if cache_key in self._prior_cache:
            return self._prior_cache[cache_key]
        
        # Build priors from orchestrator
        if self.orchestrator:
            try:
                unified = self.orchestrator.build_unified_intelligence(
                    scope_type=scope_type,
                    scope_value=scope_value,
                )
                priors = unified.langgraph_priors or {}
                self._prior_cache[cache_key] = priors
                return priors
            except Exception as e:
                logger.warning(f"Failed to build priors: {e}")
        
        # Return empty priors if unavailable
        return {
            "prior_key": cache_key,
            "psychological_priors": {},
            "archetype_priors": {},
            "mechanism_priors": {},
        }
    
    def inject_priors_into_state(
        self,
        state: Dict[str, Any],
        scope_type: str,
        scope_value: str,
    ) -> Dict[str, Any]:
        """
        Inject priors into LangGraph state.
        
        Called at workflow start to enrich state with
        relevant psychological context.
        """
        priors = self.get_priors(scope_type, scope_value)
        
        state["review_intelligence"] = {
            "priors": priors,
            "scope": {
                "type": scope_type,
                "value": scope_value,
            },
        }
        
        return state
    
    def get_routing_signal(
        self,
        scope_type: str,
        scope_value: str,
    ) -> str:
        """
        Get routing signal for LangGraph conditional edges.
        
        Based on psychological profile, determines which
        workflow path to take.
        """
        priors = self.get_priors(scope_type, scope_value)
        
        archetypes = priors.get("archetype_priors", {})
        if not archetypes:
            return "standard"
        
        # Find dominant archetype
        dominant = max(archetypes.items(), key=lambda x: x[1])[0]
        
        # Map to workflow routes
        archetype_routes = {
            "ruler": "premium_path",
            "hero": "achievement_path",
            "sage": "educational_path",
            "explorer": "discovery_path",
            "outlaw": "bold_path",
            "everyman": "standard_path",
        }
        
        return archetype_routes.get(dominant.lower(), "standard")


# =============================================================================
# ATOM-OF-THOUGHT INTEGRATION
# =============================================================================

class AtomIntelligenceInjector:
    """
    Injects review intelligence into AoT atoms.
    
    Each atom receives relevant psychological intelligence
    to inform its reasoning and decisions.
    """
    
    def __init__(
        self,
        orchestrator: Optional[ReviewIntelligenceOrchestrator] = None,
    ):
        self.orchestrator = orchestrator
        self._injection_cache: Dict[str, Dict[str, Any]] = {}
    
    def get_atom_injections(
        self,
        unified: UnifiedIntelligence,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get injections for all atoms from unified intelligence.
        """
        return unified.atom_injections or {}
    
    def inject_into_user_state_atom(
        self,
        atom_context: Dict[str, Any],
        unified: UnifiedIntelligence,
    ) -> Dict[str, Any]:
        """
        Inject into UserStateAtom.
        
        Provides:
        - Psychological baseline for user state inference
        - Archetype affinities to consider
        - Emotional state patterns
        """
        injections = self.get_atom_injections(unified)
        user_state_injection = injections.get("UserStateAtom", {})
        
        atom_context["review_intelligence"] = {
            "psychological_baseline": user_state_injection.get(
                "psychological_baseline", {}
            ),
            "archetype_affinities": user_state_injection.get(
                "archetype_affinities", {}
            ),
            "source": "review_intelligence_layer",
        }
        
        return atom_context
    
    def inject_into_review_intelligence_atom(
        self,
        atom_context: Dict[str, Any],
        unified: UnifiedIntelligence,
    ) -> Dict[str, Any]:
        """
        Inject into ReviewIntelligenceAtom.
        
        Provides:
        - Persuasive templates to use/adapt
        - Mechanism effectiveness data
        - Helpful vote patterns
        """
        injections = self.get_atom_injections(unified)
        review_injection = injections.get("ReviewIntelligenceAtom", {})
        
        atom_context["templates"] = review_injection.get(
            "persuasive_templates", []
        )
        atom_context["mechanism_effectiveness"] = review_injection.get(
            "mechanism_effectiveness", {}
        )
        
        return atom_context
    
    def inject_into_mechanism_activation_atom(
        self,
        atom_context: Dict[str, Any],
        unified: UnifiedIntelligence,
    ) -> Dict[str, Any]:
        """
        Inject into MechanismActivationAtom.
        
        This is the CRITICAL injection - it tells the atom
        which mechanisms to activate based on review evidence.
        """
        injections = self.get_atom_injections(unified)
        mechanism_injection = injections.get("MechanismActivationAtom", {})
        
        atom_context["mechanism_priors"] = mechanism_injection.get(
            "mechanism_effectiveness", {}
        )
        atom_context["context_modifiers"] = mechanism_injection.get(
            "context_modifiers", {}
        )
        
        # Add safeguards if emotional state data is present
        if DataSource.TWITTER_MENTAL_HEALTH in unified.sources_used:
            atom_context["emotional_safeguards"] = {
                "enabled": True,
                "avoid_for_vulnerable": [
                    "fear_appeal", "scarcity", "urgency"
                ],
            }
        
        return atom_context
    
    def inject_into_channel_selection_atom(
        self,
        atom_context: Dict[str, Any],
        unified: UnifiedIntelligence,
    ) -> Dict[str, Any]:
        """
        Inject into ChannelSelectionAtom.
        
        Provides:
        - Format affinities from review analysis
        - Timing recommendations
        - iHeart alignment data
        """
        injections = self.get_atom_injections(unified)
        channel_injection = injections.get("ChannelSelectionAtom", {})
        
        atom_context["format_affinities"] = channel_injection.get(
            "format_affinities", {}
        )
        atom_context["timing_recommendations"] = channel_injection.get(
            "timing_recommendations", {}
        )
        
        return atom_context


# =============================================================================
# UNIFIED MACHINE BRIDGE
# =============================================================================

class ReviewIntelligenceMachineBridge:
    """
    The unified bridge connecting review intelligence to all three machines.
    
    This is the main integration point that:
    1. Receives unified intelligence from the orchestrator
    2. Distributes to Neo4j, LangGraph, and AoT
    3. Ensures consistency across all systems
    4. Emits learning signals to UnifiedLearningHub (Synergistic Brain Architecture)
    5. Receives outcome feedback to improve predictions
    """
    
    def __init__(
        self,
        orchestrator: ReviewIntelligenceOrchestrator,
        neo4j_driver=None,
    ):
        self.orchestrator = orchestrator
        
        # Initialize machine integrations
        self.neo4j = Neo4jReviewIntelligence(driver=neo4j_driver)
        self.langgraph = LangGraphPriorProvider(orchestrator=orchestrator)
        self.aot = AtomIntelligenceInjector(orchestrator=orchestrator)
        
        # Learning loop integration (Synergistic Brain Architecture)
        self._learning_hub = None
        self._outcome_history: List[Dict[str, Any]] = []
    
    async def connect_to_learning_hub(self) -> bool:
        """
        Connect to the UnifiedLearningHub for bidirectional learning.
        
        This enables:
        - Review intelligence -> Learning signals
        - Outcome feedback -> Intelligence updates
        """
        try:
            from adam.core.learning.unified_learning_hub import (
                get_unified_learning_hub, UnifiedSignalType,
            )
            
            self._learning_hub = get_unified_learning_hub()
            
            # Register as a learning component
            async def review_intelligence_handler(signal):
                await self._handle_learning_signal(signal)
            
            self._learning_hub.register_component(
                name="review_intelligence_bridge",
                handler=review_intelligence_handler,
                signal_types={
                    UnifiedSignalType.OUTCOME_OBSERVED,
                    UnifiedSignalType.CREDIT_MECHANISM,
                },
                priority=3,  # Medium priority - receives outcome feedback
            )
            
            logger.info("ReviewIntelligenceMachineBridge connected to UnifiedLearningHub")
            return True
            
        except ImportError:
            logger.warning("UnifiedLearningHub not available")
            return False
        except Exception as e:
            logger.warning(f"Could not connect to learning hub: {e}")
            return False
    
    async def _handle_learning_signal(self, signal) -> None:
        """
        Handle incoming learning signals from the hub.
        
        Processes outcome signals to:
        - Track mechanism effectiveness by segment
        - Update intelligence recommendations
        """
        from adam.core.learning.unified_learning_hub import UnifiedSignalType
        
        if signal.signal_type == UnifiedSignalType.OUTCOME_OBSERVED:
            # Store outcome for future intelligence updates
            self._outcome_history.append({
                "request_id": signal.request_id,
                "outcome_value": signal.value,
                "mechanisms_used": signal.payload.get("mechanisms_used", []),
                "segment": signal.payload.get("segment"),
                "timestamp": signal.timestamp,
            })
            
            # Aggregate and update when we have enough data
            if len(self._outcome_history) >= 100:
                await self._update_mechanism_effectiveness()
    
    async def _update_mechanism_effectiveness(self) -> None:
        """
        Update mechanism effectiveness based on accumulated outcomes.
        
        This is the critical learning loop that improves review intelligence
        predictions over time.
        """
        from collections import defaultdict
        
        # Group outcomes by mechanism
        mechanism_outcomes: Dict[str, List[float]] = defaultdict(list)
        
        for outcome in self._outcome_history:
            for mechanism in outcome.get("mechanisms_used", []):
                mechanism_outcomes[mechanism].append(outcome["outcome_value"])
        
        # Calculate updated effectiveness
        effectiveness_updates = {}
        for mechanism, outcomes in mechanism_outcomes.items():
            if len(outcomes) >= 10:  # Require minimum sample
                effectiveness_updates[mechanism] = sum(outcomes) / len(outcomes)
        
        # Update the orchestrator's effectiveness priors
        if effectiveness_updates and self.orchestrator:
            self.orchestrator.update_mechanism_priors(effectiveness_updates)
            logger.info(
                f"Updated mechanism effectiveness from {len(self._outcome_history)} outcomes: "
                f"{len(effectiveness_updates)} mechanisms"
            )
        
        # Clear processed history (keep last 10 for continuity)
        self._outcome_history = self._outcome_history[-10:]
    
    async def emit_intelligence_signal(
        self,
        unified: UnifiedIntelligence,
        request_id: str,
    ) -> None:
        """
        Emit a learning signal when intelligence is provided to atoms.
        
        This enables the learning loop to track which intelligence was used
        for credit attribution.
        """
        if not self._learning_hub:
            return
        
        try:
            from adam.core.learning.unified_learning_hub import (
                UnifiedLearningSignal, UnifiedSignalType,
            )
            
            # Emit signal with intelligence details
            await self._learning_hub.process_signal(UnifiedLearningSignal(
                signal_type=UnifiedSignalType.PATTERN_DISCOVERED,
                request_id=request_id,
                value=unified.total_sample_size / 1000.0,  # Normalize
                component="review_intelligence_bridge",
                payload={
                    "scope_type": unified.scope_type,
                    "scope_value": unified.scope_value,
                    "sources_used": [s.value for s in unified.sources_used],
                    "mechanism_effectiveness": unified.mechanism_effectiveness,
                    "archetype_profile": unified.archetype_profile,
                    "template_count": len(unified.top_templates),
                },
            ))
            
        except Exception as e:
            logger.debug(f"Could not emit intelligence signal: {e}")
    
    async def sync_intelligence(
        self,
        scope_type: str,
        scope_value: str,
        sources: Optional[List[DataSource]] = None,
        request_id: Optional[str] = None,
    ) -> UnifiedIntelligence:
        """
        Sync review intelligence across all three machines.
        
        This is the main method to call after extraction.
        Enhanced with learning signal emission for Synergistic Brain Architecture.
        """
        # Build unified intelligence
        logger.info(f"Building unified intelligence for {scope_type}={scope_value}")
        unified = self.orchestrator.build_unified_intelligence(
            scope_type=scope_type,
            scope_value=scope_value,
            sources=sources,
        )
        
        # 1. Store in Neo4j
        logger.info("Syncing to Neo4j graph...")
        segment_id = self.neo4j.store_unified_intelligence(unified)
        
        # 2. Cache in LangGraph provider
        logger.info("Caching in LangGraph prior provider...")
        self.langgraph.get_priors(scope_type, scope_value)
        
        # 3. Prepare AoT injections (cached in unified object)
        logger.info("Preparing AoT injections...")
        # Already in unified.atom_injections
        
        # 4. Emit learning signal (Synergistic Brain Architecture)
        if request_id:
            await self.emit_intelligence_signal(unified, request_id)
        
        logger.info(f"Synced intelligence: {segment_id}")
        return unified
    
    def sync_intelligence_sync(
        self,
        scope_type: str,
        scope_value: str,
        sources: Optional[List[DataSource]] = None,
    ) -> UnifiedIntelligence:
        """
        Synchronous version of sync_intelligence for non-async contexts.
        
        Note: Does not emit learning signals (async-only feature).
        """
        # Build unified intelligence
        logger.info(f"Building unified intelligence for {scope_type}={scope_value}")
        unified = self.orchestrator.build_unified_intelligence(
            scope_type=scope_type,
            scope_value=scope_value,
            sources=sources,
        )
        
        # 1. Store in Neo4j
        logger.info("Syncing to Neo4j graph...")
        segment_id = self.neo4j.store_unified_intelligence(unified)
        
        # 2. Cache in LangGraph provider
        logger.info("Caching in LangGraph prior provider...")
        self.langgraph.get_priors(scope_type, scope_value)
        
        logger.info(f"Synced intelligence: {segment_id}")
        return unified
    
    def get_ecosystem_outputs(
        self,
        unified: UnifiedIntelligence,
    ) -> Dict[str, Any]:
        """
        Get formatted outputs for all ecosystem partners.
        """
        return {
            "dsp": unified.dsp_output,
            "ssp": unified.ssp_output,
            "agency": unified.agency_output,
        }
    
    def get_atom_context(
        self,
        atom_name: str,
        unified: UnifiedIntelligence,
    ) -> Dict[str, Any]:
        """
        Get enriched context for a specific atom.
        """
        base_context = {}
        
        if atom_name == "UserStateAtom":
            return self.aot.inject_into_user_state_atom(base_context, unified)
        elif atom_name == "ReviewIntelligenceAtom":
            return self.aot.inject_into_review_intelligence_atom(base_context, unified)
        elif atom_name == "MechanismActivationAtom":
            return self.aot.inject_into_mechanism_activation_atom(base_context, unified)
        elif atom_name == "ChannelSelectionAtom":
            return self.aot.inject_into_channel_selection_atom(base_context, unified)
        else:
            return base_context
