#!/usr/bin/env python3
"""
BIDIRECTIONAL BRIDGE
====================

Connects the AoT (Atom-of-Thought) system with the Graph Database
for bidirectional learning.

AoT → Graph: Persist decisions, mechanisms, and outcomes
Graph → AoT: Inform future decisions with historical patterns

Phase 5: Learning Loop Completion
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class LearningPathEntry:
    """Entry in a learning path."""
    
    decision_id: str
    outcome_type: str
    outcome_value: float
    mechanism_used: Optional[str] = None
    timestamp: str = ""
    attribution_computed: bool = False
    signals_emitted: int = 0


class BidirectionalBridge:
    """
    Bridge between AoT and Graph Database.
    
    Responsibilities:
    1. Persist decisions to graph for historical querying
    2. Persist outcomes for learning path completion
    3. Query graph for historical mechanism effectiveness
    4. Enable cross-session learning
    """
    
    def __init__(self, neo4j_client=None):
        self._neo4j = neo4j_client
        self._decision_cache: Dict[str, Dict[str, Any]] = {}
        self._learning_paths: List[LearningPathEntry] = []
        self._decisions_persisted = 0
        self._outcomes_recorded = 0
    
    async def persist_decision_to_graph(
        self,
        decision_id: str,
        user_id: str,
        brand: str,
        product: str,
        mechanism_used: str,
        atom_outputs: Dict[str, Any],
        confidence: float,
    ) -> bool:
        """
        Persist a decision to the graph database.
        
        Creates nodes and edges:
        - Decision node
        - User -> Decision edge
        - Decision -> Mechanism edge
        - Decision -> Brand edge
        """
        # Cache for local tracking
        self._decision_cache[decision_id] = {
            "user_id": user_id,
            "brand": brand,
            "product": product,
            "mechanism_used": mechanism_used,
            "confidence": confidence,
            "created_at": datetime.now().isoformat(),
        }
        
        self._decisions_persisted += 1
        
        # Persist to Neo4j if available
        if self._neo4j:
            try:
                query = """
                MERGE (d:Decision {decision_id: $decision_id})
                SET d.user_id = $user_id,
                    d.brand = $brand,
                    d.product = $product,
                    d.mechanism = $mechanism_used,
                    d.confidence = $confidence,
                    d.created_at = datetime()
                
                MERGE (u:User {user_id: $user_id})
                MERGE (u)-[:MADE_DECISION]->(d)
                
                MERGE (m:Mechanism {name: $mechanism_used})
                MERGE (d)-[:USED_MECHANISM]->(m)
                
                MERGE (b:Brand {name: $brand})
                MERGE (d)-[:FOR_BRAND]->(b)
                
                RETURN d.decision_id
                """
                
                await self._neo4j.run_query(
                    query,
                    decision_id=decision_id,
                    user_id=user_id,
                    brand=brand,
                    product=product,
                    mechanism_used=mechanism_used,
                    confidence=confidence,
                )
                
                logger.debug(f"Persisted decision {decision_id} to graph")
                return True
                
            except Exception as e:
                logger.warning(f"Failed to persist decision to graph: {e}")
                return False
        
        logger.debug(f"Decision {decision_id} cached locally (no Neo4j)")
        return True
    
    async def create_learning_path(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        attribution_computed: bool = False,
        signals_emitted: int = 0,
    ) -> None:
        """
        Create a learning path entry linking decision to outcome.
        
        This enables:
        - Querying which decisions led to outcomes
        - Mechanism effectiveness over time
        - User journey analysis
        """
        entry = LearningPathEntry(
            decision_id=decision_id,
            outcome_type=outcome_type,
            outcome_value=outcome_value,
            mechanism_used=self._decision_cache.get(decision_id, {}).get("mechanism_used"),
            timestamp=datetime.now().isoformat(),
            attribution_computed=attribution_computed,
            signals_emitted=signals_emitted,
        )
        
        self._learning_paths.append(entry)
        self._outcomes_recorded += 1
        
        # Persist to Neo4j if available
        if self._neo4j:
            try:
                query = """
                MATCH (d:Decision {decision_id: $decision_id})
                MERGE (o:Outcome {decision_id: $decision_id, outcome_type: $outcome_type})
                SET o.value = $outcome_value,
                    o.recorded_at = datetime(),
                    o.attribution_computed = $attribution_computed,
                    o.signals_emitted = $signals_emitted
                
                MERGE (d)-[:HAD_OUTCOME]->(o)
                
                WITH d, o
                MATCH (d)-[:USED_MECHANISM]->(m:Mechanism)
                MERGE (m)-[r:EFFECTIVENESS {outcome_type: $outcome_type}]->(o)
                SET r.value = $outcome_value,
                    r.updated_at = datetime()
                
                RETURN o.decision_id
                """
                
                await self._neo4j.run_query(
                    query,
                    decision_id=decision_id,
                    outcome_type=outcome_type,
                    outcome_value=outcome_value,
                    attribution_computed=attribution_computed,
                    signals_emitted=signals_emitted,
                )
                
                logger.debug(f"Created learning path for {decision_id}")
                
            except Exception as e:
                logger.warning(f"Failed to create learning path in graph: {e}")
        
        logger.debug(f"Learning path created: {decision_id} -> {outcome_type}={outcome_value}")
    
    async def get_mechanism_effectiveness(
        self,
        mechanism: str,
        brand: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Get historical effectiveness for a mechanism.
        
        Returns aggregated stats from learning paths.
        """
        # Local calculation from cache
        relevant = [
            lp for lp in self._learning_paths
            if lp.mechanism_used == mechanism
        ]
        
        if not relevant:
            return {
                "mechanism": mechanism,
                "total_decisions": 0,
                "avg_outcome": 0.5,
                "conversion_rate": 0.0,
            }
        
        total = len(relevant)
        avg_outcome = sum(lp.outcome_value for lp in relevant) / total
        conversions = sum(1 for lp in relevant if lp.outcome_type == "conversion")
        
        return {
            "mechanism": mechanism,
            "total_decisions": total,
            "avg_outcome": avg_outcome,
            "conversion_rate": conversions / total if total > 0 else 0.0,
        }
    
    async def get_user_history(
        self,
        user_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get a user's decision history."""
        # From local cache
        user_decisions = [
            {"decision_id": did, **data}
            for did, data in self._decision_cache.items()
            if data.get("user_id") == user_id
        ][:limit]
        
        return user_decisions
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bridge statistics."""
        return {
            "decisions_persisted": self._decisions_persisted,
            "outcomes_recorded": self._outcomes_recorded,
            "cached_decisions": len(self._decision_cache),
            "learning_paths": len(self._learning_paths),
            "neo4j_connected": self._neo4j is not None,
        }
    
    # =========================================================================
    # LANGGRAPH INTEGRATION
    # =========================================================================
    
    async def emit_learning_signal(
        self,
        signal_type: str,
        archetype: str,
        mechanism: str,
        payload: Dict[str, Any],
    ) -> bool:
        """
        Emit a learning signal to the unified learning hub.
        
        This is the entry point for LangGraph workflows to route
        learning signals into the ADAM learning ecosystem.
        
        Args:
            signal_type: Type of signal (e.g., "outcome_success", "credit_mechanism")
            archetype: User archetype associated with this signal
            mechanism: Mechanism associated with this signal
            payload: Additional signal data
            
        Returns:
            True if signal was successfully emitted
        """
        try:
            from adam.core.learning.unified_learning_hub import (
                get_unified_learning_hub,
                UnifiedLearningSignal,
                UnifiedSignalType,
                SIGNAL_TYPE_MAPPING,
            )
            
            # Map string to enum
            signal_enum = SIGNAL_TYPE_MAPPING.get(
                signal_type,
                UnifiedSignalType.OUTCOME_SUCCESS,
            )
            
            hub = get_unified_learning_hub()
            
            signal = UnifiedLearningSignal(
                signal_type=signal_enum,
                source_component="bidirectional_bridge",
                archetype=archetype,
                mechanism=mechanism,
                confidence=payload.get("confidence", 0.5),
                payload=payload,
            )
            
            await hub.process_signal(signal)
            logger.debug(f"Emitted learning signal: {signal_type} for {archetype}/{mechanism}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to emit learning signal: {e}")
            return False
    
    async def route_atom_feedback(
        self,
        atom_id: str,
        feedback_type: str,
        feedback_data: Dict[str, Any],
    ) -> bool:
        """
        Route feedback from an AoT atom to appropriate learning systems.
        
        This enables AoT → LangGraph bidirectional communication.
        
        Args:
            atom_id: ID of the atom emitting feedback
            feedback_type: Type of feedback (prior_validated, prior_overridden, etc.)
            feedback_data: Feedback payload
            
        Returns:
            True if feedback was successfully routed
        """
        try:
            from adam.core.learning.unified_learning_hub import (
                get_unified_learning_hub,
                UnifiedLearningSignal,
                UnifiedSignalType,
            )
            
            hub = get_unified_learning_hub()
            
            # Determine signal type based on feedback
            if feedback_type == "prior_validated":
                signal_type = UnifiedSignalType.UPDATE_ATOM_PRIOR
                confidence = feedback_data.get("validation_strength", 0.8)
            elif feedback_type == "prior_overridden":
                signal_type = UnifiedSignalType.UPDATE_ATOM_PRIOR
                confidence = feedback_data.get("override_confidence", 0.6)
            elif feedback_type == "mechanism_effective":
                signal_type = UnifiedSignalType.CREDIT_MECHANISM
                confidence = feedback_data.get("effectiveness", 0.7)
            else:
                signal_type = UnifiedSignalType.PATTERN_DISCOVERED
                confidence = 0.5
            
            signal = UnifiedLearningSignal(
                signal_type=signal_type,
                source_component=f"atom:{atom_id}",
                archetype=feedback_data.get("archetype", "unknown"),
                mechanism=feedback_data.get("mechanism", "unknown"),
                confidence=confidence,
                payload={
                    "feedback_type": feedback_type,
                    "atom_id": atom_id,
                    **feedback_data,
                },
            )
            
            await hub.process_signal(signal)
            logger.debug(f"Routed atom feedback from {atom_id}: {feedback_type}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to route atom feedback: {e}")
            return False
    
    async def get_langgraph_context(
        self,
        user_id: str,
        brand: str,
        category: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get enriched context for LangGraph workflows.
        
        Aggregates historical data from:
        - Decision cache
        - Learning paths
        - Neo4j (if available)
        
        Returns context optimized for LangGraph state initialization.
        """
        context = {
            "user_history_available": False,
            "mechanism_effectiveness": {},
            "brand_affinity": 0.5,
            "historical_outcomes": [],
            "recommended_mechanisms": [],
        }
        
        # Get user history
        user_history = await self.get_user_history(user_id)
        if user_history:
            context["user_history_available"] = True
            context["user_decision_count"] = len(user_history)
            
            # Analyze preferred mechanisms
            mechanism_counts: Dict[str, int] = {}
            for decision in user_history:
                mech = decision.get("mechanism_used")
                if mech:
                    mechanism_counts[mech] = mechanism_counts.get(mech, 0) + 1
            
            if mechanism_counts:
                total = sum(mechanism_counts.values())
                context["mechanism_preference"] = {
                    mech: count / total for mech, count in mechanism_counts.items()
                }
        
        # Get mechanism effectiveness for common mechanisms
        common_mechanisms = ["social_proof", "scarcity", "authority", "reciprocity"]
        for mech in common_mechanisms:
            effectiveness = await self.get_mechanism_effectiveness(mech, brand)
            if effectiveness["total_decisions"] > 0:
                context["mechanism_effectiveness"][mech] = effectiveness
        
        # Get historical outcomes for this user
        user_paths = [
            lp for lp in self._learning_paths
            if self._decision_cache.get(lp.decision_id, {}).get("user_id") == user_id
        ]
        if user_paths:
            context["historical_outcomes"] = [
                {
                    "outcome_type": lp.outcome_type,
                    "value": lp.outcome_value,
                    "mechanism": lp.mechanism_used,
                }
                for lp in user_paths[-10:]  # Last 10 outcomes
            ]
            
            # Calculate average outcome
            context["avg_historical_outcome"] = sum(
                lp.outcome_value for lp in user_paths
            ) / len(user_paths)
        
        # Recommend mechanisms based on effectiveness
        if context["mechanism_effectiveness"]:
            sorted_mechs = sorted(
                context["mechanism_effectiveness"].items(),
                key=lambda x: x[1]["avg_outcome"],
                reverse=True,
            )
            context["recommended_mechanisms"] = [
                {"mechanism": mech, "expected_outcome": data["avg_outcome"]}
                for mech, data in sorted_mechs[:3]
            ]
        
        return context
    
    async def sync_with_langgraph_state(
        self,
        state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Sync bidirectional bridge with LangGraph workflow state.
        
        This is called at the start of workflow execution to:
        1. Inject historical context
        2. Set up tracking for this decision
        3. Prepare learning path
        
        Returns enriched state.
        """
        user_id = state.get("user_id", "")
        brand = state.get("brand_name", "")
        category = state.get("category", "")
        
        # Get context for this user/brand
        bridge_context = await self.get_langgraph_context(user_id, brand, category)
        
        # Inject into state
        return {
            **state,
            "bridge_context": bridge_context,
            "bidirectional_bridge_active": True,
        }


# =============================================================================
# SINGLETON
# =============================================================================

_bridge: Optional[BidirectionalBridge] = None


def get_bidirectional_bridge() -> BidirectionalBridge:
    """Get singleton bidirectional bridge."""
    global _bridge
    if _bridge is None:
        _bridge = BidirectionalBridge()
    return _bridge
