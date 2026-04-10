# =============================================================================
# ADAM Bidirectional Graph-AoT Integration
# Location: adam/graph_reasoning/bridge/bidirectional_integration.py
# =============================================================================

"""
BIDIRECTIONAL GRAPH-AOT INTEGRATION

This module wires together the components needed for full bidirectional
communication between the Neo4j graph and the Atom-of-Thought system:

1. UpdateTierController: Routes updates by priority (immediate/async/batch)
2. ConflictResolutionEngine: Resolves conflicts between graph and LLM
3. InteractionBridge: The core bidirectional interface

CRITICAL: This was identified as broken in the system audit.
The components existed but were never wired together.

Key flows enabled:
- Atom insights → Graph (via UpdateTierController)
- Graph priors → Atoms (via InteractionBridge.pull_context)
- Decisions → Graph (via persist_decision_to_graph)
- Outcomes → Learning (via push_decision_attribution)
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from neo4j import AsyncDriver

from adam.graph_reasoning.update_tiers import (
    UpdateTierController,
    GraphUpdate,
    UpdateCategory,
    UpdateTier,
    UpdatePriority,
)
from adam.graph_reasoning.conflict_resolution import (
    ConflictResolutionEngine,
    Conflict,
    ConflictType,
    ConflictSeverity,
    ResolutionStrategy,
)
from adam.infrastructure.redis import ADAMRedisCache
from adam.infrastructure.kafka import get_kafka_producer, ADAMTopics

logger = logging.getLogger(__name__)


# =============================================================================
# CYPHER QUERIES
# =============================================================================

QUERY_PERSIST_DECISION = """
// Persist a complete decision with all components
MERGE (d:Decision {decision_id: $decision_id})
SET d.request_id = $request_id,
    d.user_id = $user_id,
    d.selected_ad_id = $selected_ad_id,
    d.primary_mechanism = $primary_mechanism,
    d.execution_path = $execution_path,
    d.confidence = $confidence,
    d.latency_ms = $latency_ms,
    d.created_at = datetime($created_at)

// Link to user
WITH d
MATCH (u:User {user_id: $user_id})
MERGE (u)-[:RECEIVED_DECISION]->(d)

// Link to mechanisms applied
WITH d
UNWIND $mechanisms as mech
MATCH (m:CognitiveMechanism {mechanism_id: mech.mechanism_id})
MERGE (d)-[a:APPLIED_MECHANISM]->(m)
SET a.intensity = mech.intensity,
    a.is_primary = mech.is_primary

RETURN d.decision_id
"""

QUERY_CREATE_LEARNING_PATH = """
// Create learning path edge between decision and outcome
MATCH (d:Decision {decision_id: $decision_id})
MERGE (o:Outcome {outcome_id: $outcome_id})
SET o.outcome_type = $outcome_type,
    o.outcome_value = $outcome_value,
    o.recorded_at = datetime($recorded_at)
MERGE (d)-[l:LED_TO_OUTCOME]->(o)
SET l.attribution_computed = $attribution_computed,
    l.signals_emitted = $signals_emitted
RETURN o.outcome_id
"""

QUERY_RECORD_ATOM_INSIGHT = """
// Record an atom's contribution to the graph
MERGE (a:AtomInsight {insight_id: $insight_id})
SET a.atom_name = $atom_name,
    a.decision_id = $decision_id,
    a.insight_type = $insight_type,
    a.content = $content,
    a.confidence = $confidence,
    a.created_at = datetime($created_at)

// Link to decision if exists
WITH a
MATCH (d:Decision {decision_id: $decision_id})
MERGE (d)-[:USED_INSIGHT]->(a)

RETURN a.insight_id
"""


# =============================================================================
# BIDIRECTIONAL BRIDGE INTEGRATION
# =============================================================================

class BidirectionalBridgeIntegration:
    """
    Integrates UpdateTierController and ConflictResolutionEngine with InteractionBridge.
    
    This class is the "glue" that was missing - it ensures:
    1. All graph updates go through proper tier routing
    2. Conflicts are detected and resolved before writes
    3. Decisions are persisted with full context
    4. Learning paths are created for outcome attribution
    """
    
    def __init__(
        self,
        neo4j_driver: AsyncDriver,
        redis_cache: Optional[ADAMRedisCache] = None,
        batch_window_seconds: float = 5.0,
    ):
        self.neo4j = neo4j_driver
        self.redis = redis_cache
        
        # Initialize update tier controller with handlers
        self.update_controller = UpdateTierController(
            immediate_handler=self._handle_immediate_update,
            async_handler=self._handle_async_update,
            batch_handler=self._handle_batch_updates,
            batch_window_seconds=batch_window_seconds,
        )
        
        # Initialize conflict resolution
        self.conflict_engine = ConflictResolutionEngine(
            default_strategy=ResolutionStrategy.CONFIDENCE_WEIGHTED,
            staleness_threshold_hours=24.0,
        )
        
        # Tracking
        self._decisions_persisted = 0
        self._learning_paths_created = 0
        self._conflicts_resolved = 0
        self._updates_processed = 0
        
        # State
        self._processors_started = False
        
        logger.info("BidirectionalBridgeIntegration initialized")
    
    async def start(self) -> None:
        """Start background processors."""
        if self._processors_started:
            return
        
        # Start the async processor
        asyncio.create_task(self.update_controller.start_async_processor())
        asyncio.create_task(self.update_controller.start_batch_processor())
        
        self._processors_started = True
        logger.info("Bidirectional bridge processors started")
    
    async def stop(self) -> None:
        """Stop background processors."""
        self.update_controller.stop_processors()
        self._processors_started = False
        logger.info("Bidirectional bridge processors stopped")
    
    # =========================================================================
    # DECISION PERSISTENCE
    # =========================================================================
    
    async def persist_decision_to_graph(
        self,
        decision_id: str,
        request_id: str,
        user_id: str,
        selected_ad_id: str,
        primary_mechanism: Optional[str],
        mechanisms: List[Dict[str, Any]],
        execution_path: str,
        confidence: float,
        latency_ms: float,
        atom_outputs: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Persist a complete decision to the graph.
        
        This is CRITICAL for the learning loop - without this, we can't:
        1. Track which decisions led to which outcomes
        2. Attribute credit to specific mechanisms
        3. Learn which execution paths are most effective
        
        This method was identified as "never called" in the audit.
        """
        try:
            # Create update
            update = GraphUpdate(
                category=UpdateCategory.DECISION_OUTCOME,
                operation="merge",
                target_node_type="Decision",
                target_node_id=decision_id,
                properties={
                    "decision_id": decision_id,
                    "request_id": request_id,
                    "user_id": user_id,
                    "selected_ad_id": selected_ad_id,
                    "primary_mechanism": primary_mechanism,
                    "mechanisms": mechanisms,
                    "execution_path": execution_path,
                    "confidence": confidence,
                    "latency_ms": latency_ms,
                },
                cypher_query=QUERY_PERSIST_DECISION,
                cypher_params={
                    "decision_id": decision_id,
                    "request_id": request_id,
                    "user_id": user_id,
                    "selected_ad_id": selected_ad_id,
                    "primary_mechanism": primary_mechanism or "",
                    "execution_path": execution_path,
                    "confidence": confidence,
                    "latency_ms": latency_ms,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "mechanisms": [
                        {
                            "mechanism_id": m.get("mechanism_id"),
                            "intensity": m.get("intensity", 0.5),
                            "is_primary": m.get("is_primary", False),
                        }
                        for m in mechanisms
                    ],
                },
                tier=UpdateTier.IMMEDIATE,  # Decisions are critical
                priority=UpdatePriority.HIGH,
                source_component="bidirectional_bridge",
                decision_id=decision_id,
                user_id=user_id,
            )
            
            # Submit through tier controller
            success = await self.update_controller.submit(update)
            
            if success:
                self._decisions_persisted += 1
                logger.info(f"Persisted decision {decision_id} to graph")
                
                # Also persist atom outputs as insights
                if atom_outputs:
                    await self._persist_atom_insights(decision_id, atom_outputs)
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to persist decision {decision_id}: {e}")
            return False
    
    async def _persist_atom_insights(
        self,
        decision_id: str,
        atom_outputs: Dict[str, Any],
    ) -> None:
        """Persist atom outputs as graph insights."""
        for atom_name, output in atom_outputs.items():
            if not output:
                continue
            
            insight_id = f"insight_{decision_id}_{atom_name}"
            
            update = GraphUpdate(
                category=UpdateCategory.PSYCHOLOGICAL_INFERENCE,
                operation="merge",
                target_node_type="AtomInsight",
                target_node_id=insight_id,
                cypher_query=QUERY_RECORD_ATOM_INSIGHT,
                cypher_params={
                    "insight_id": insight_id,
                    "atom_name": atom_name,
                    "decision_id": decision_id,
                    "insight_type": output.get("primary_assessment", "unknown"),
                    "content": str(output)[:1000],  # Truncate for storage
                    "confidence": output.get("overall_confidence", 0.5),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
                tier=UpdateTier.ASYNC,  # Insights can be async
                priority=UpdatePriority.NORMAL,
                source_component=atom_name,
                decision_id=decision_id,
            )
            
            await self.update_controller.submit(update)
    
    # =========================================================================
    # LEARNING PATH CREATION
    # =========================================================================
    
    async def create_learning_path(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        attribution_computed: bool = True,
        signals_emitted: int = 0,
    ) -> bool:
        """
        Create a learning path edge between decision and outcome.
        
        This enables:
        1. Querying which decisions led to positive outcomes
        2. Attribution analysis across decision components
        3. Mechanism effectiveness computation over time
        """
        try:
            outcome_id = f"outcome_{decision_id}_{outcome_type}"
            
            update = GraphUpdate(
                category=UpdateCategory.DECISION_OUTCOME,
                operation="merge",
                target_node_type="Outcome",
                target_node_id=outcome_id,
                properties={
                    "conversion": True if outcome_type == "conversion" else False,
                },
                cypher_query=QUERY_CREATE_LEARNING_PATH,
                cypher_params={
                    "decision_id": decision_id,
                    "outcome_id": outcome_id,
                    "outcome_type": outcome_type,
                    "outcome_value": outcome_value,
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                    "attribution_computed": attribution_computed,
                    "signals_emitted": signals_emitted,
                },
                tier=UpdateTier.IMMEDIATE,  # Learning is critical
                priority=UpdatePriority.HIGH,
                source_component="learning_loop",
                decision_id=decision_id,
            )
            
            success = await self.update_controller.submit(update)
            
            if success:
                self._learning_paths_created += 1
                logger.info(f"Created learning path for decision {decision_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to create learning path: {e}")
            return False
    
    # =========================================================================
    # UPDATE HANDLERS
    # =========================================================================
    
    async def _handle_immediate_update(self, update: GraphUpdate) -> bool:
        """Handle immediate tier updates."""
        try:
            if update.cypher_query:
                async with self.neo4j.session() as session:
                    await session.run(update.cypher_query, **update.cypher_params)
            
            self._updates_processed += 1
            return True
            
        except Exception as e:
            logger.error(f"Immediate update failed: {e}")
            return False
    
    async def _handle_async_update(self, update: GraphUpdate) -> bool:
        """Handle async tier updates."""
        return await self._handle_immediate_update(update)  # Same logic, different queue
    
    async def _handle_batch_updates(self, updates: List[GraphUpdate]) -> int:
        """Handle batch updates."""
        successful = 0
        
        for update in updates:
            if await self._handle_immediate_update(update):
                successful += 1
        
        return successful
    
    # =========================================================================
    # CONFLICT HANDLING
    # =========================================================================
    
    async def check_and_resolve_conflict(
        self,
        property_name: str,
        graph_value: Any,
        llm_value: Any,
        graph_confidence: float = 0.7,
        llm_confidence: float = 0.7,
        node_type: Optional[str] = None,
        node_id: Optional[str] = None,
    ) -> Any:
        """
        Check for conflict between graph and LLM values and resolve.
        
        Returns the resolved value to use.
        """
        # No conflict if values match
        if graph_value == llm_value:
            return graph_value
        
        # Create conflict record
        conflict = Conflict(
            conflict_type=ConflictType.CONTRADICTION,
            severity=ConflictSeverity.MEDIUM,
            property_name=property_name,
            node_type=node_type,
            node_id=node_id,
        )
        conflict.add_value(graph_value, "graph", graph_confidence)
        conflict.add_value(llm_value, "llm", llm_confidence)
        
        # Resolve
        resolved = self.conflict_engine.resolve(conflict)
        
        if resolved.resolved:
            self._conflicts_resolved += 1
            logger.debug(
                f"Resolved conflict on {property_name}: "
                f"graph={graph_value}, llm={llm_value} → {resolved.resolved_value} "
                f"(strategy: {resolved.resolution_strategy})"
            )
            return resolved.resolved_value
        
        # If unresolved, default to graph value (conservative)
        return graph_value
    
    # =========================================================================
    # STATISTICS
    # =========================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get integration statistics."""
        return {
            "decisions_persisted": self._decisions_persisted,
            "learning_paths_created": self._learning_paths_created,
            "conflicts_resolved": self._conflicts_resolved,
            "updates_processed": self._updates_processed,
            "update_controller_stats": self.update_controller.get_statistics(),
        }


# =============================================================================
# SINGLETON
# =============================================================================

_integration: Optional[BidirectionalBridgeIntegration] = None


def get_bidirectional_bridge(
    neo4j_driver: Optional[AsyncDriver] = None,
    redis_cache: Optional[ADAMRedisCache] = None,
) -> Optional[BidirectionalBridgeIntegration]:
    """Get or create the bidirectional bridge integration singleton."""
    global _integration
    
    if _integration is not None:
        return _integration
    
    if neo4j_driver is None:
        logger.warning("Cannot create bidirectional bridge without Neo4j driver")
        return None
    
    _integration = BidirectionalBridgeIntegration(
        neo4j_driver=neo4j_driver,
        redis_cache=redis_cache,
    )
    
    return _integration


async def shutdown_bidirectional_bridge() -> None:
    """Shutdown the bidirectional bridge."""
    global _integration
    if _integration:
        await _integration.stop()
        _integration = None
