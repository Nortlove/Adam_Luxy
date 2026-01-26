# =============================================================================
# ADAM Interaction Bridge
# Location: adam/graph_reasoning/bridge/interaction_bridge.py
# =============================================================================

"""
INTERACTION BRIDGE

The bidirectional interface between Neo4j graph and reasoning components.

PULL (Graph → Reasoning):
- User profile with Big Five and extended traits
- Mechanism effectiveness history
- Recent state trajectory
- Archetype match for cold-start
- Category-level priors

PUSH (Reasoning → Graph):
- Reasoning insights
- Mechanism activations
- State inferences
- Learning signals

Every push emits a learning signal to the Gradient Bridge.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from neo4j import AsyncDriver

from adam.graph_reasoning.models.graph_context import GraphContext
from adam.graph_reasoning.models.reasoning_output import (
    MechanismActivation,
    StateInference,
    ReasoningInsight,
    DecisionAttribution,
    ReasoningTrace,
)
from adam.graph_reasoning.bridge.context_queries import ContextQueryExecutor
from adam.infrastructure.redis import ADAMRedisCache, CacheKeyBuilder, CacheDomain
from adam.infrastructure.kafka import get_kafka_producer, ADAMTopics
from adam.infrastructure.prometheus import get_metrics

logger = logging.getLogger(__name__)


# =============================================================================
# PUSH QUERIES
# =============================================================================

QUERY_PUSH_MECHANISM_ACTIVATION = """
// Create mechanism activation record
MATCH (d:Decision {decision_id: $decision_id})
MATCH (m:CognitiveMechanism {mechanism_id: $mechanism_id})
MERGE (d)-[a:APPLIED_MECHANISM]->(m)
SET a.activation_id = $activation_id,
    a.intensity = $intensity,
    a.intensity_score = $intensity_score,
    a.is_primary = $is_primary,
    a.confidence = $confidence,
    a.activation_reason = $activation_reason,
    a.prior_effectiveness = $prior_effectiveness,
    a.prior_source = $prior_source,
    a.activated_at = datetime($activated_at)
RETURN a
"""

QUERY_PUSH_STATE_INFERENCE = """
// Create state inference and link to user
MATCH (u:User {user_id: $user_id})
CREATE (s:TemporalUserState {
    state_id: $state_id,
    arousal: $arousal,
    valence: $valence,
    current_regulatory_focus: $regulatory_focus,
    current_construal_level: $construal_level,
    confidence: $confidence,
    session_id: $session_id,
    request_id: $request_id,
    timestamp: datetime($inferred_at)
})
CREATE (u)-[:IN_STATE {is_current: true}]->(s)
// Mark previous current state as not current
WITH u, s
MATCH (u)-[r:IN_STATE]->(old:TemporalUserState)
WHERE old.state_id <> $state_id AND r.is_current = true
SET r.is_current = false
RETURN s
"""

QUERY_PUSH_REASONING_INSIGHT = """
// Create reasoning insight node
CREATE (i:ReasoningInsight {
    insight_id: $insight_id,
    insight_type: $insight_type,
    insight_summary: $insight_summary,
    insight_detail: $insight_detail,
    confidence: $confidence,
    confidence_level: $confidence_level,
    evidence_count: $evidence_count,
    is_actionable: $is_actionable,
    request_id: $request_id,
    created_at: datetime($created_at)
})
WITH i
OPTIONAL MATCH (u:User {user_id: $user_id})
WHERE $user_id IS NOT NULL
FOREACH (_ IN CASE WHEN u IS NOT NULL THEN [1] ELSE [] END |
    CREATE (u)-[:HAS_INSIGHT]->(i)
)
RETURN i
"""

QUERY_UPDATE_MECHANISM_EFFECTIVENESS = """
// Update mechanism effectiveness from outcome
MATCH (u:User {user_id: $user_id})
MATCH (m:CognitiveMechanism {mechanism_id: $mechanism_id})
MERGE (u)-[r:RESPONDS_TO]->(m)
ON CREATE SET
    r.success_rate = $outcome_value,
    r.effect_size = $effect_size,
    r.trial_count = 1,
    r.confidence = 0.3,
    r.created_at = datetime()
ON MATCH SET
    r.success_rate = (r.success_rate * r.trial_count + $outcome_value) / (r.trial_count + 1),
    r.trial_count = r.trial_count + 1,
    r.confidence = CASE 
        WHEN r.trial_count > 20 THEN 0.9
        WHEN r.trial_count > 10 THEN 0.7
        WHEN r.trial_count > 5 THEN 0.5
        ELSE 0.3
    END,
    r.last_applied_at = datetime(),
    r.last_success_at = CASE WHEN $outcome_value > 0.5 THEN datetime() ELSE r.last_success_at END
RETURN r
"""


# =============================================================================
# INTERACTION BRIDGE
# =============================================================================

class InteractionBridge:
    """
    Bidirectional bridge between Neo4j graph and reasoning components.
    
    PULL: Assembles complete context for reasoning
    PUSH: Persists reasoning outputs and emits learning signals
    
    Every operation is:
    - Cached for performance
    - Measured with Prometheus metrics
    - Emits Kafka events for downstream processing
    """
    
    def __init__(
        self,
        neo4j_driver: AsyncDriver,
        redis_cache: Optional[ADAMRedisCache] = None,
    ):
        self.neo4j = neo4j_driver
        self.cache = redis_cache
        self.query_executor = ContextQueryExecutor(neo4j_driver, redis_cache)
        self.metrics = get_metrics()
    
    # -------------------------------------------------------------------------
    # PULL: Graph → Reasoning
    # -------------------------------------------------------------------------
    
    async def pull_context(
        self,
        request_id: str,
        user_id: str,
        category_name: Optional[str] = None,
    ) -> GraphContext:
        """
        Pull complete context from graph for reasoning.
        
        Executes queries in parallel for performance.
        Returns GraphContext with all available priors.
        """
        start_time = datetime.now(timezone.utc)
        cache_hit = False
        
        try:
            # Check cache first
            if self.cache:
                cache_key = CacheKeyBuilder.profile(user_id)
                cached = await self.cache.get(cache_key)
                if cached:
                    cache_hit = True
                    # Still need to pull fresh state history
                    state_history = await self.query_executor.pull_state_history(user_id)
                    # Return cached context with fresh state
                    # (In production, would deserialize cached GraphContext)
            
            # Pull all context in parallel
            profile_task = self.query_executor.pull_user_profile(user_id)
            mechanism_task = self.query_executor.pull_mechanism_history(user_id)
            state_task = self.query_executor.pull_state_history(user_id)
            archetype_task = self.query_executor.pull_archetype_match(user_id)
            
            tasks = [profile_task, mechanism_task, state_task, archetype_task]
            
            if category_name:
                category_task = self.query_executor.pull_category_priors(category_name)
                tasks.append(category_task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Unpack results
            user_profile = results[0] if not isinstance(results[0], Exception) else None
            mechanism_history = results[1] if not isinstance(results[1], Exception) else None
            state_history = results[2] if not isinstance(results[2], Exception) else None
            archetype_match = results[3] if not isinstance(results[3], Exception) else None
            category_priors = results[4] if len(results) > 4 and not isinstance(results[4], Exception) else None
            
            # Handle failures gracefully
            if user_profile is None:
                from adam.graph_reasoning.models.graph_context import UserProfileSnapshot
                user_profile = UserProfileSnapshot(user_id=user_id, is_cold_start=True)
            
            if mechanism_history is None:
                from adam.graph_reasoning.models.graph_context import MechanismHistory
                mechanism_history = MechanismHistory(user_id=user_id)
            
            if state_history is None:
                from adam.graph_reasoning.models.graph_context import StateHistory
                state_history = StateHistory(user_id=user_id)
            
            # Calculate latency
            latency_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            # Build context
            context = GraphContext(
                request_id=request_id,
                user_id=user_id,
                user_profile=user_profile,
                mechanism_history=mechanism_history,
                state_history=state_history,
                archetype_match=archetype_match,
                category_priors=category_priors,
                query_latency_ms=latency_ms,
                cache_hit=cache_hit,
                is_cold_start=user_profile.is_cold_start,
            )
            
            # Record metrics
            self.metrics.record_inference(
                component="interaction_bridge",
                operation="pull_context",
                latency_seconds=latency_ms / 1000,
            )
            self.metrics.record_profile_lookup(cache_hit=cache_hit, source="neo4j")
            
            # Emit event
            await self._emit_context_pulled_event(context)
            
            logger.debug(
                f"Pulled context for user {user_id} in {latency_ms:.1f}ms "
                f"(cold_start={context.is_cold_start}, cache_hit={cache_hit})"
            )
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to pull context: {e}")
            # Return minimal context on failure
            from adam.graph_reasoning.models.graph_context import (
                UserProfileSnapshot, MechanismHistory, StateHistory
            )
            return GraphContext(
                request_id=request_id,
                user_id=user_id,
                user_profile=UserProfileSnapshot(user_id=user_id, is_cold_start=True),
                mechanism_history=MechanismHistory(user_id=user_id),
                state_history=StateHistory(user_id=user_id),
                is_cold_start=True,
            )
    
    # -------------------------------------------------------------------------
    # PUSH: Reasoning → Graph
    # -------------------------------------------------------------------------
    
    async def push_mechanism_activation(
        self,
        activation: MechanismActivation,
    ) -> bool:
        """
        Push mechanism activation to graph.
        
        Creates APPLIED_MECHANISM relationship for learning.
        """
        try:
            async with self.neo4j.session() as session:
                await session.run(
                    QUERY_PUSH_MECHANISM_ACTIVATION,
                    decision_id=activation.decision_id,
                    mechanism_id=activation.mechanism_id,
                    activation_id=activation.activation_id,
                    intensity=activation.intensity.value,
                    intensity_score=activation.intensity_score,
                    is_primary=activation.is_primary,
                    confidence=activation.confidence,
                    activation_reason=activation.activation_reason,
                    prior_effectiveness=activation.prior_effectiveness,
                    prior_source=activation.prior_source,
                    activated_at=activation.activated_at.isoformat(),
                )
            
            # Emit learning signal
            await self._emit_mechanism_activation_signal(activation)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to push mechanism activation: {e}")
            return False
    
    async def push_state_inference(
        self,
        inference: StateInference,
    ) -> bool:
        """
        Push state inference to graph.
        
        Creates TemporalUserState node and IN_STATE relationship.
        """
        try:
            async with self.neo4j.session() as session:
                await session.run(
                    QUERY_PUSH_STATE_INFERENCE,
                    user_id=inference.user_id,
                    state_id=inference.inference_id,
                    arousal=inference.arousal,
                    valence=inference.valence,
                    regulatory_focus=inference.regulatory_focus,
                    construal_level=inference.construal_level,
                    confidence=inference.confidence,
                    session_id=inference.session_id,
                    request_id=inference.request_id,
                    inferred_at=inference.inferred_at.isoformat(),
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to push state inference: {e}")
            return False
    
    async def push_reasoning_insight(
        self,
        insight: ReasoningInsight,
    ) -> bool:
        """
        Push reasoning insight to graph.
        
        Creates ReasoningInsight node with relationships.
        """
        try:
            async with self.neo4j.session() as session:
                await session.run(
                    QUERY_PUSH_REASONING_INSIGHT,
                    insight_id=insight.insight_id,
                    insight_type=insight.insight_type.value,
                    insight_summary=insight.insight_summary,
                    insight_detail=insight.insight_detail,
                    confidence=insight.confidence,
                    confidence_level=insight.confidence_level.value,
                    evidence_count=insight.evidence_count,
                    is_actionable=insight.is_actionable,
                    request_id=insight.request_id,
                    user_id=insight.related_user_id,
                    created_at=insight.created_at.isoformat(),
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to push reasoning insight: {e}")
            return False
    
    async def push_decision_attribution(
        self,
        attribution: DecisionAttribution,
    ) -> bool:
        """
        Push decision attribution to update mechanism effectiveness.
        
        This is the critical learning loop - outcomes update priors.
        """
        try:
            # Update each mechanism's effectiveness
            for mechanism_id, contribution in attribution.mechanism_attributions.items():
                # Weighted outcome based on contribution
                weighted_outcome = attribution.outcome_value * contribution
                
                async with self.neo4j.session() as session:
                    await session.run(
                        QUERY_UPDATE_MECHANISM_EFFECTIVENESS,
                        user_id=attribution.user_id,
                        mechanism_id=mechanism_id,
                        outcome_value=weighted_outcome,
                        effect_size=contribution,
                    )
            
            # Emit learning signal
            await self._emit_attribution_signal(attribution)
            
            # Record metrics
            self.metrics.record_ad_outcome(
                outcome_type=attribution.outcome.value,
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to push decision attribution: {e}")
            return False
    
    async def push_reasoning_trace(
        self,
        trace: ReasoningTrace,
    ) -> bool:
        """
        Push complete reasoning trace.
        
        Persists all outputs from a reasoning cycle.
        """
        try:
            # Push mechanism activations
            for activation in trace.mechanism_activations:
                await self.push_mechanism_activation(activation)
            
            # Push state inferences
            for inference in trace.state_inferences:
                await self.push_state_inference(inference)
            
            # Push insights
            for insight in trace.insights:
                await self.push_reasoning_insight(insight)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to push reasoning trace: {e}")
            return False
    
    # -------------------------------------------------------------------------
    # EVENT EMISSION
    # -------------------------------------------------------------------------
    
    async def _emit_context_pulled_event(self, context: GraphContext) -> None:
        """Emit event when context is pulled."""
        try:
            producer = await get_kafka_producer()
            if producer:
                await producer.send(
                    ADAMTopics.EVENTS_DECISION,
                    value={
                        "event_type": "context_pulled",
                        "request_id": context.request_id,
                        "user_id": context.user_id,
                        "is_cold_start": context.is_cold_start,
                        "query_latency_ms": context.query_latency_ms,
                        "cache_hit": context.cache_hit,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    key=context.user_id,
                )
        except Exception as e:
            logger.warning(f"Failed to emit context_pulled event: {e}")
    
    async def _emit_mechanism_activation_signal(
        self,
        activation: MechanismActivation,
    ) -> None:
        """Emit learning signal for mechanism activation."""
        try:
            producer = await get_kafka_producer()
            if producer:
                await producer.emit_learning_signal(
                    signal_type="mechanism_effectiveness",
                    signal_name=f"activation_{activation.mechanism_id}",
                    signal_value=activation.intensity_score,
                    user_id=activation.user_id,
                    decision_id=activation.decision_id,
                    component_id="interaction_bridge",
                    confidence=activation.confidence,
                    metadata={
                        "mechanism_id": activation.mechanism_id,
                        "is_primary": activation.is_primary,
                        "prior_source": activation.prior_source,
                    },
                )
        except Exception as e:
            logger.warning(f"Failed to emit mechanism activation signal: {e}")
    
    async def _emit_attribution_signal(
        self,
        attribution: DecisionAttribution,
    ) -> None:
        """Emit learning signal for decision attribution."""
        try:
            producer = await get_kafka_producer()
            if producer:
                await producer.emit_ad_outcome(
                    decision_id=attribution.decision_id,
                    user_id=attribution.user_id,
                    campaign_id="",  # Would come from decision context
                    creative_id="",
                    outcome_type=attribution.outcome.value,
                    outcome_value=attribution.outcome_value,
                    mechanisms_applied=list(attribution.mechanism_attributions.keys()),
                )
        except Exception as e:
            logger.warning(f"Failed to emit attribution signal: {e}")
    
    # -------------------------------------------------------------------------
    # PATTERN DISCOVERY
    # -------------------------------------------------------------------------
    
    async def discover_mechanism_interactions(
        self,
        min_trials: int = 5,
        min_co_occurrences: int = 10,
        min_interaction_strength: float = 0.1,
    ) -> List[Dict[str, Any]]:
        """
        Discover mechanism synergies and suppressions from the graph.
        
        Returns discovered interactions for the Emergence Engine.
        """
        return await self.query_executor.discover_mechanism_interactions(
            min_trials=min_trials,
            min_co_occurrences=min_co_occurrences,
            min_interaction_strength=min_interaction_strength,
        )
    
    async def discover_behavioral_patterns(
        self,
        lookback_days: int = 30,
        min_occurrences: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Discover behavioral patterns that correlate with outcomes.
        
        These are candidates for hypothesis generation.
        """
        return await self.query_executor.discover_behavioral_patterns(
            lookback_days=lookback_days,
            min_pattern_occurrences=min_occurrences,
        )
    
    async def discover_cohorts(self, min_trials: int = 5) -> List[Dict[str, Any]]:
        """Discover natural user cohorts based on mechanism response."""
        return await self.query_executor.discover_cohorts(min_trials=min_trials)
    
    async def discover_temporal_patterns(self, lookback_days: int = 7) -> List[Dict[str, Any]]:
        """Discover temporal patterns in user state trajectories."""
        return await self.query_executor.discover_temporal_patterns(lookback_days=lookback_days)
    
    async def discover_cross_domain_patterns(
        self,
        min_trials: int = 5,
        min_users: int = 10,
    ) -> List[Dict[str, Any]]:
        """Find mechanism patterns that transfer across categories."""
        return await self.query_executor.discover_cross_domain_patterns(
            min_trials=min_trials,
            min_users=min_users,
        )
    
    # -------------------------------------------------------------------------
    # HYPOTHESIS MANAGEMENT
    # -------------------------------------------------------------------------
    
    async def create_hypothesis(
        self,
        hypothesis_id: str,
        hypothesis_type: str,
        statement: str,
        expected_effect_size: float,
        source: str = "pattern_discovery",
        related_pattern_id: Optional[str] = None,
    ) -> bool:
        """Create a new hypothesis for testing."""
        return await self.query_executor.create_hypothesis(
            hypothesis_id=hypothesis_id,
            hypothesis_type=hypothesis_type,
            statement=statement,
            expected_effect_size=expected_effect_size,
            source=source,
            related_pattern_id=related_pattern_id,
        )
    
    async def update_hypothesis(
        self,
        hypothesis_id: str,
        success: bool,
    ) -> bool:
        """Update hypothesis after a test."""
        return await self.query_executor.update_hypothesis(
            hypothesis_id=hypothesis_id,
            success=success,
        )
    
    async def get_testable_hypotheses(
        self,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get hypotheses ready for testing."""
        return await self.query_executor.get_testable_hypotheses(limit=limit)
    
    # -------------------------------------------------------------------------
    # PATTERN MANAGEMENT
    # -------------------------------------------------------------------------
    
    async def create_behavioral_pattern(
        self,
        pattern_id: str,
        pattern_name: str,
        description: str,
        signal_pattern: List[str],
        predicted_outcome: str,
        sample_size: int,
        effect_size: float,
        p_value: float,
        lift: float,
        mechanism_ids: Optional[List[str]] = None,
    ) -> bool:
        """Store a discovered behavioral pattern."""
        return await self.query_executor.create_behavioral_pattern(
            pattern_id=pattern_id,
            pattern_name=pattern_name,
            description=description,
            signal_pattern=signal_pattern,
            predicted_outcome=predicted_outcome,
            sample_size=sample_size,
            effect_size=effect_size,
            p_value=p_value,
            lift=lift,
            mechanism_ids=mechanism_ids,
        )
    
    async def link_user_to_pattern(
        self,
        user_id: str,
        pattern_id: str,
        confidence: float = 0.5,
    ) -> bool:
        """Create EXHIBITS relationship between user and pattern."""
        return await self.query_executor.link_user_to_pattern(
            user_id=user_id,
            pattern_id=pattern_id,
            confidence=confidence,
        )
    
    # -------------------------------------------------------------------------
    # ADVERTISING KNOWLEDGE MANAGEMENT
    # -------------------------------------------------------------------------
    
    async def store_advertising_knowledge(
        self,
        knowledge_id: str,
        predictor_category: str,
        predictor_name: str,
        predictor_value: str,
        ad_element: str,
        element_specification: str,
        outcome_metric: str,
        outcome_direction: str,
        effect_size: float,
        effect_type: str,
        robustness_tier: int,
        study_count: int = 1,
        related_mechanisms: Optional[List[str]] = None,
    ) -> bool:
        """Store advertising knowledge from consumer psychology research."""
        return await self.query_executor.store_advertising_knowledge(
            knowledge_id=knowledge_id,
            predictor_category=predictor_category,
            predictor_name=predictor_name,
            predictor_value=predictor_value,
            ad_element=ad_element,
            element_specification=element_specification,
            outcome_metric=outcome_metric,
            outcome_direction=outcome_direction,
            effect_size=effect_size,
            effect_type=effect_type,
            robustness_tier=robustness_tier,
            study_count=study_count,
            related_mechanisms=related_mechanisms,
        )
    
    async def get_advertising_knowledge_for_user(
        self,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """Get relevant advertising knowledge for a user based on their profile."""
        return await self.query_executor.get_advertising_knowledge_for_user(
            user_id=user_id,
        )
    
    async def get_advertising_knowledge_for_predictor(
        self,
        predictor_name: str,
        robustness_tier: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Get all advertising knowledge for a predictor variable."""
        return await self.query_executor.get_advertising_knowledge_for_predictor(
            predictor_name=predictor_name,
            robustness_tier=robustness_tier,
        )
    
    async def get_meta_analyzed_knowledge(self) -> List[Dict[str, Any]]:
        """Get all Tier 1 (meta-analyzed) advertising knowledge."""
        return await self.query_executor.get_meta_analyzed_knowledge()
    
    async def store_advertising_interaction(
        self,
        interaction_id: str,
        primary_variable: str,
        moderating_variable: str,
        interaction_type: str,
        effect_when_present: float,
        effect_when_absent: float,
    ) -> bool:
        """Store advertising interaction effect."""
        return await self.query_executor.store_advertising_interaction(
            interaction_id=interaction_id,
            primary_variable=primary_variable,
            moderating_variable=moderating_variable,
            interaction_type=interaction_type,
            effect_when_present=effect_when_present,
            effect_when_absent=effect_when_absent,
        )
    
    async def get_interactions_for_variable(
        self,
        variable: str,
    ) -> List[Dict[str, Any]]:
        """Get all interactions involving a variable."""
        return await self.query_executor.get_interactions_for_variable(
            variable=variable,
        )
