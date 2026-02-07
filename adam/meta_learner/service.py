# =============================================================================
# ADAM Meta-Learner Service
# Location: adam/meta_learner/service.py
# =============================================================================

"""
META-LEARNER SERVICE

Main service for meta-learning orchestration.

Coordinates:
- Context feature extraction
- Thompson Sampling modality selection
- Blackboard integration
- Learning signal emission
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Optional

from adam.meta_learner.models import (
    LearningModality,
    ExecutionPath,
    ContextFeatures,
    RoutingDecision,
    PosteriorState,
    DataRichness,
    ContextNovelty,
)
from adam.meta_learner.thompson import ThompsonSamplingEngine
from adam.blackboard.models.zone1_context import RequestContext
from adam.blackboard.models.zone5_learning import (
    ComponentSignal,
    SignalSource,
    SignalPriority,
)
from adam.blackboard.service import BlackboardService
from adam.blackboard.models.core import ComponentRole
from adam.infrastructure.redis import ADAMRedisCache, CacheKeyBuilder, CacheDomain
from adam.infrastructure.kafka import get_kafka_producer, ADAMTopics
from adam.infrastructure.prometheus import get_metrics
from adam.core.learning.universal_learning_interface import (
    LearningSignal,
    LearningSignalType,
    LearningSignalPriority,
    LearningContribution,
    LearningQualityMetrics,
)
from typing import Any, List, Set, Tuple

logger = logging.getLogger(__name__)

# Cache for tracking routing decisions
_routing_decisions_cache: Dict[str, Dict[str, Any]] = {}


class MetaLearnerService:
    """
    Meta-Learner service for routing decisions.
    
    The Meta-Learner is the first substantive routing decision.
    It determines which modality and execution path to use.
    """
    
    def __init__(
        self,
        blackboard: BlackboardService,
        cache: ADAMRedisCache,
    ):
        self.blackboard = blackboard
        self.cache = cache
        self.metrics = get_metrics()
        
        # Thompson Sampling engine (initialized lazily with state)
        self._engine: Optional[ThompsonSamplingEngine] = None
    
    async def route_request(
        self,
        request_id: str,
        request_context: RequestContext,
    ) -> RoutingDecision:
        """
        Route a request to the appropriate execution path.
        
        Args:
            request_id: Unique request identifier
            request_context: Zone 1 request context
        
        Returns:
            RoutingDecision with selected modality and path
        """
        start_time = datetime.now(timezone.utc)
        user_id = request_context.user_intelligence.user_id
        
        try:
            # Step 1: Extract context features
            context = self._extract_context_features(request_context)
            
            # Step 2: Get or initialize Thompson engine with cached state
            engine = await self._get_engine()
            
            # Step 3: Select modality via Thompson Sampling
            decision = engine.select_modality(
                request_id=request_id,
                user_id=user_id,
                context=context,
            )
            
            # Step 4: Record metrics
            self._record_metrics(decision)
            
            # Step 5: Emit learning signal
            await self._emit_routing_signal(decision)
            
            # Step 6: Cache posterior state
            await self._cache_posterior_state(engine.posterior_state)
            
            # Step 7: Cache routing decision for learning attribution
            self._cache_routing_decision(decision)
            
            logger.info(
                f"Routed request {request_id} to {decision.execution_path.value} "
                f"via {decision.selected_modality.value}"
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"Error routing request {request_id}: {e}")
            
            # Fall back to safe exploration path
            return RoutingDecision(
                request_id=request_id,
                user_id=user_id,
                selected_modality=LearningModality.REINFORCEMENT_BANDIT,
                execution_path=ExecutionPath.EXPLORATION_PATH,
                selection_reason=f"Fallback due to error: {str(e)}",
            )
    
    async def update_from_outcome(
        self,
        decision_id: str,
        modality: LearningModality,
        reward: float,
    ) -> None:
        """
        Update posteriors from an observed outcome.
        
        Args:
            decision_id: Original decision ID
            modality: The modality that was used
            reward: Observed reward (0-1)
        """
        engine = await self._get_engine()
        engine.update(modality, reward)
        
        # Cache updated state
        await self._cache_posterior_state(engine.posterior_state)
        
        # Record metric
        self.metrics.meta_learner_updates.labels(
            modality=modality.value,
            reward_bin=self._reward_bin(reward),
        ).inc()
        
        logger.debug(f"Updated modality {modality.value} with reward {reward:.2f}")
    
    def _extract_context_features(
        self,
        context: RequestContext,
    ) -> ContextFeatures:
        """Extract context features from request context."""
        user_intel = context.user_intelligence
        
        # Determine interaction count
        interaction_count = 0
        if user_intel.mechanism_history:
            interaction_count = user_intel.mechanism_history.total_mechanism_trials
        
        # Determine conversion count (approximate from success rates)
        conversion_count = 0
        if user_intel.mechanism_history and user_intel.mechanism_history.mechanism_effectiveness:
            for m in user_intel.mechanism_history.mechanism_effectiveness:
                conversion_count += int(m.trial_count * m.success_rate)
        
        # Determine profile completeness
        profile_completeness = 0.0
        if user_intel.profile:
            # Simple heuristic: count non-null fields
            profile_dict = user_intel.profile.model_dump()
            total_fields = len(profile_dict)
            filled_fields = sum(1 for v in profile_dict.values() if v is not None)
            profile_completeness = filled_fields / total_fields if total_fields > 0 else 0.0
        
        # Determine data richness
        if interaction_count == 0:
            data_richness = DataRichness.COLD_START
        elif interaction_count < 10:
            data_richness = DataRichness.SPARSE
        elif interaction_count < 50:
            data_richness = DataRichness.MODERATE
        else:
            data_richness = DataRichness.RICH
        
        # Determine context novelty
        if context.session_context and context.session_context.decisions_in_session == 0:
            context_novelty = ContextNovelty.SOMEWHAT_NOVEL
        else:
            context_novelty = ContextNovelty.FAMILIAR
        
        return ContextFeatures(
            user_id=user_intel.user_id,
            interaction_count=interaction_count,
            conversion_count=conversion_count,
            profile_completeness=profile_completeness,
            data_richness=data_richness,
            content_type=context.content_context.content_type,
            station_format=context.content_context.station_format,
            context_novelty=context_novelty,
            ad_pool_size=context.ad_candidates.total_count,
            latency_budget_ms=context.latency_budget_ms,
            exploration_allowed=True,  # Could be configured per campaign
            campaign_mode="standard",
        )
    
    async def _get_engine(self) -> ThompsonSamplingEngine:
        """Get or initialize the Thompson Sampling engine."""
        if self._engine is not None:
            return self._engine
        
        # Try to load cached posterior state
        posterior_state = await self._load_posterior_state()
        
        self._engine = ThompsonSamplingEngine(
            posterior_state=posterior_state,
        )
        
        return self._engine
    
    async def _load_posterior_state(self) -> PosteriorState:
        """Load posterior state from cache."""
        key = CacheKeyBuilder.meta_learner_posteriors()
        
        state = await self.cache.get(key, PosteriorState)
        if state:
            logger.debug("Loaded posterior state from cache")
            return state
        
        # Initialize fresh state
        logger.info("Initializing fresh posterior state")
        return PosteriorState()
    
    async def _cache_posterior_state(self, state: PosteriorState) -> None:
        """Cache posterior state."""
        key = CacheKeyBuilder.meta_learner_posteriors()
        await self.cache.set(
            key,
            state,
            domain=CacheDomain.FEATURE,  # Long TTL
        )
    
    async def _emit_routing_signal(self, decision: RoutingDecision) -> None:
        """Emit a learning signal for the routing decision."""
        signal = ComponentSignal(
            source=SignalSource.META_LEARNER,
            source_component_id="meta_learner",
            source_component_type="meta_learner",
            target_construct="modality_selection",
            target_entity_id=decision.selected_modality.value,
            signal_type="routing_decision",
            signal_value=1.0,  # Will be updated with outcome
            signal_direction="neutral",
            user_id=decision.user_id,
            request_id=decision.request_id,
            confidence=decision.selection_confidence,
            priority=SignalPriority.MEDIUM,
        )
        
        # Write to Zone 5
        await self.blackboard.write_zone5_signal(
            decision.request_id,
            signal,
            role=ComponentRole.META_LEARNER,
        )
        
        # Emit to Kafka for async processing
        try:
            producer = await get_kafka_producer()
            if producer:
                await producer.emit_learning_signal(
                    signal_type="modality_selection",
                    user_id=decision.user_id,
                    component_id="meta_learner",
                    signal_value=decision.selection_confidence,
                    context={
                        "modality": decision.selected_modality.value,
                        "path": decision.execution_path.value,
                        "decision_id": decision.decision_id,
                    },
                )
        except Exception as e:
            logger.warning(f"Failed to emit routing signal to Kafka: {e}")
    
    def _record_metrics(self, decision: RoutingDecision) -> None:
        """Record Prometheus metrics."""
        # Modality selection
        self.metrics.meta_learner_selections.labels(
            modality=decision.selected_modality.value,
            path=decision.execution_path.value,
        ).inc()
        
        # Selection latency
        self.metrics.meta_learner_latency.observe(
            decision.decision_latency_ms / 1000
        )
        
        # Exploration rate
        if decision.exploration_probability > 0.5:
            self.metrics.meta_learner_explorations.inc()
    
    def _reward_bin(self, reward: float) -> str:
        """Bin reward for metrics."""
        if reward >= 0.8:
            return "high"
        elif reward >= 0.4:
            return "medium"
        else:
            return "low"
    
    async def get_posterior_summary(self) -> Dict:
        """Get summary of all posteriors for API/debugging."""
        engine = await self._get_engine()
        return engine.get_posterior_summary()
    
    async def apply_decay(self) -> None:
        """Apply decay to posteriors (call periodically)."""
        engine = await self._get_engine()
        engine.apply_decay()
        await self._cache_posterior_state(engine.posterior_state)
        logger.info("Applied decay to all posteriors")
    
    # =========================================================================
    # LEARNING CAPABLE COMPONENT INTERFACE
    # =========================================================================
    
    @property
    def component_name(self) -> str:
        """Component name for learning signal routing."""
        return "meta_learner"
    
    @property
    def component_version(self) -> str:
        """Component version."""
        return "1.0"
    
    def _cache_routing_decision(self, decision: RoutingDecision) -> None:
        """Cache routing decision for credit attribution."""
        _routing_decisions_cache[decision.request_id] = {
            "decision_id": decision.decision_id,
            "request_id": decision.request_id,
            "user_id": decision.user_id,
            "modality": decision.selected_modality.value,
            "execution_path": decision.execution_path.value,
            "confidence": decision.selection_confidence,
            "exploration_probability": decision.exploration_probability,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    
    async def on_outcome_received(
        self,
        decision_id: str,
        outcome_type: str,
        outcome_value: float,
        context: Dict[str, Any],
    ) -> List[LearningSignal]:
        """
        Process an outcome and generate learning signals.
        
        For Meta-Learner, this updates Thompson Sampling posteriors
        and emits signals about routing effectiveness.
        """
        signals = []
        
        # Get cached routing decision
        routing_data = _routing_decisions_cache.get(decision_id)
        if not routing_data:
            return signals
        
        modality_str = routing_data.get("modality")
        if modality_str:
            try:
                modality = LearningModality(modality_str)
                
                # Update posteriors
                await self.update_from_outcome(
                    decision_id=decision_id,
                    modality=modality,
                    reward=outcome_value,
                )
                
                # Emit learning signal
                signal = LearningSignal(
                    signal_type=LearningSignalType.PRIOR_UPDATED,
                    source_component=self.component_name,
                    source_version=self.component_version,
                    decision_id=decision_id,
                    payload={
                        "modality": modality_str,
                        "execution_path": routing_data.get("execution_path"),
                        "outcome_value": outcome_value,
                        "was_exploration": routing_data.get("exploration_probability", 0) > 0.5,
                    },
                    confidence=outcome_value,
                    priority=LearningSignalPriority.NORMAL,
                )
                signals.append(signal)
                
            except ValueError:
                pass
        
        return signals
    
    async def on_learning_signal_received(
        self,
        signal: LearningSignal,
    ) -> Optional[List[LearningSignal]]:
        """Process incoming learning signals."""
        # Meta-learner primarily emits signals, doesn't consume many
        # But it can respond to calibration updates
        if signal.signal_type == LearningSignalType.CALIBRATION_UPDATED:
            # Could adjust exploration rate based on calibration
            pass
        return None
    
    def get_consumed_signal_types(self) -> Set[LearningSignalType]:
        """Return signal types this component consumes."""
        return {
            LearningSignalType.CALIBRATION_UPDATED,
            LearningSignalType.DRIFT_DETECTED,
        }
    
    async def get_learning_contribution(
        self,
        decision_id: str,
    ) -> Optional[LearningContribution]:
        """Get this component's contribution to a decision."""
        routing_data = _routing_decisions_cache.get(decision_id)
        if not routing_data:
            return None
        
        return LearningContribution(
            component_name=self.component_name,
            decision_id=decision_id,
            contribution_type="routing_decision",
            contribution_value={
                "modality": routing_data.get("modality"),
                "execution_path": routing_data.get("execution_path"),
            },
            confidence=routing_data.get("confidence", 0.5),
            reasoning_summary=f"Selected {routing_data.get('execution_path')} path via {routing_data.get('modality')}",
            evidence_sources=["thompson_sampling", "context_features"],
            weight=0.2,  # Routing contributes ~20% to decision
        )
    
    async def get_learning_quality_metrics(self) -> LearningQualityMetrics:
        """Get metrics about learning quality."""
        engine = await self._get_engine()
        summary = engine.get_posterior_summary()
        
        # Calculate metrics from posterior state
        total_updates = sum(
            p.get("alpha", 1) + p.get("beta", 1) - 2
            for p in summary.get("posteriors", {}).values()
        )
        
        return LearningQualityMetrics(
            component_name=self.component_name,
            measurement_period_hours=24,
            signals_emitted=total_updates,
            signals_consumed=0,
            outcomes_processed=total_updates,
            prediction_accuracy=summary.get("best_modality_mean", 0.5),
            prediction_accuracy_trend="stable",
            attribution_coverage=1.0,
        )
    
    async def inject_priors(
        self,
        user_id: str,
        priors: Dict[str, Any],
    ) -> None:
        """
        Inject priors for meta-learning routing decisions.
        
        The meta-learner uses these priors to:
        1. Route reasoning to appropriate modality (fast vs full)
        2. Initialize user-specific routing preferences
        3. Bias modality selection for cold-start users
        """
        if not priors:
            return
        
        # Store user-specific routing hints
        if not hasattr(self, '_user_routing_priors'):
            self._user_routing_priors = {}
        
        self._user_routing_priors[user_id] = {
            "preferred_modality": priors.get("preferred_modality", "balanced"),
            "complexity_tolerance": priors.get("complexity_tolerance", 0.5),
            "latency_sensitivity": priors.get("latency_sensitivity", 0.5),
            "archetype": priors.get("archetype"),
        }
        
        # If archetype-based routing priors provided, update global posteriors
        if "modality_effectiveness" in priors:
            for modality, effectiveness in priors["modality_effectiveness"].items():
                if hasattr(self, '_modality_posteriors'):
                    # Bayesian update with prior
                    if modality in self._modality_posteriors:
                        prior = self._modality_posteriors[modality]
                        # Simple weighted update
                        self._modality_posteriors[modality] = (
                            prior * 0.7 + effectiveness * 0.3
                        )
        
        logger.debug(f"Injected meta-learner priors for user {user_id}")
    
    async def validate_learning_health(self) -> Tuple[bool, List[str]]:
        """Validate learning health."""
        issues = []
        
        try:
            engine = await self._get_engine()
            summary = engine.get_posterior_summary()
            
            # Check for converged posteriors
            for modality, posterior in summary.get("posteriors", {}).items():
                variance = posterior.get("variance", 0)
                if variance < 0.001:
                    issues.append(f"Modality {modality} has converged (variance={variance:.6f})")
            
            # Check for stale posteriors
            if not summary.get("posteriors"):
                issues.append("No posterior data available")
                
        except Exception as e:
            issues.append(f"Failed to get engine state: {e}")
        
        return len(issues) == 0, issues
    
    @classmethod
    def clear_routing_cache(cls, request_id: str) -> None:
        """Clear cached routing decision."""
        if request_id in _routing_decisions_cache:
            del _routing_decisions_cache[request_id]


# =============================================================================
# SINGLETON
# =============================================================================

_meta_learner_instance: Optional[MetaLearnerService] = None


def get_meta_learner() -> Optional[MetaLearnerService]:
    """
    Get singleton MetaLearnerService instance.
    
    Returns None if dependencies aren't available (e.g., Redis not running).
    The CampaignOrchestrator will use Thompson Sampling simulation as fallback.
    """
    global _meta_learner_instance
    
    if _meta_learner_instance is not None:
        return _meta_learner_instance
    
    try:
        import redis.asyncio as redis_lib
        from adam.blackboard.service import BlackboardService
        from adam.infrastructure.redis import ADAMRedisCache
        
        # Try to connect to Redis
        redis_url = "redis://localhost:6379"
        redis_client = redis_lib.from_url(redis_url, decode_responses=False)
        
        # Create Redis cache
        cache = ADAMRedisCache(redis_client=redis_client)
        
        # Create blackboard with cache dependency
        blackboard = BlackboardService(redis_cache=cache)
        
        _meta_learner_instance = MetaLearnerService(
            blackboard=blackboard,
            cache=cache,
        )
        logger.info("MetaLearnerService initialized with Redis")
        return _meta_learner_instance
        
    except Exception as e:
        logger.info(f"MetaLearner using simulation mode (Redis not available): {e}")
        return None