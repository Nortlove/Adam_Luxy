# =============================================================================
# ADAM Dependency Injection
# Location: adam/core/dependencies.py
# =============================================================================

"""
DEPENDENCY INJECTION

Provides FastAPI dependency injection for all ADAM components.
Uses singleton pattern for infrastructure components.
"""

from typing import Optional, AsyncGenerator
from functools import lru_cache
import logging

from neo4j import AsyncGraphDatabase, AsyncDriver
import redis.asyncio as redis

from adam.config.settings import settings

logger = logging.getLogger(__name__)


# =============================================================================
# INFRASTRUCTURE SINGLETONS
# =============================================================================

class Infrastructure:
    """Singleton infrastructure manager."""
    
    _instance: Optional["Infrastructure"] = None
    
    def __init__(self):
        self._neo4j_driver: Optional[AsyncDriver] = None
        self._redis_client: Optional[redis.Redis] = None
        self._circuit_breakers = None
        self._initialized: bool = False
    
    @classmethod
    def get_instance(cls) -> "Infrastructure":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def initialize(self) -> None:
        """Initialize all infrastructure connections."""
        
        if self._initialized:
            return
        
        logger.info("Initializing ADAM infrastructure...")
        
        # Neo4j
        self._neo4j_driver = AsyncGraphDatabase.driver(
            settings.neo4j.uri,
            auth=(settings.neo4j.username, settings.neo4j.password),
            max_connection_pool_size=settings.neo4j.max_connection_pool_size,
        )
        
        # Verify Neo4j connection
        try:
            await self._neo4j_driver.verify_connectivity()
            logger.info("Neo4j connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
        
        # Redis
        self._redis_client = redis.Redis(
            host=settings.redis.host,
            port=settings.redis.port,
            password=settings.redis.password,
            db=settings.redis.db,
            decode_responses=True,
            socket_timeout=settings.redis.socket_timeout,
            socket_connect_timeout=settings.redis.socket_connect_timeout,
            max_connections=settings.redis.max_connections,
        )
        
        # Verify Redis connection
        try:
            await self._redis_client.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
        
        # Circuit breakers — initialize with tuned configs for hot path
        from adam.infrastructure.resilience.circuit_breaker import (
            CircuitBreakerConfig,
            CircuitBreakerRegistry,
        )
        self._circuit_breakers = CircuitBreakerRegistry()
        self._circuit_breakers.register("neo4j", CircuitBreakerConfig(
            name="neo4j",
            failure_threshold=5,
            recovery_timeout=30.0,
            call_timeout=0.050,  # 50ms — hot path Neo4j queries must be fast
        ))
        self._circuit_breakers.register("redis", CircuitBreakerConfig(
            name="redis",
            failure_threshold=5,
            recovery_timeout=10.0,
            call_timeout=0.020,  # 20ms
        ))
        self._circuit_breakers.register("prefetch", CircuitBreakerConfig(
            name="prefetch",
            failure_threshold=5,
            recovery_timeout=30.0,
            call_timeout=0.040,  # 40ms — prefetch budget
        ))
        logger.info("Circuit breakers initialized: neo4j(50ms), redis(20ms), prefetch(40ms)")

        self._initialized = True
        logger.info("ADAM infrastructure initialized successfully")
    
    async def shutdown(self) -> None:
        """Shutdown all infrastructure connections."""
        
        logger.info("Shutting down ADAM infrastructure...")
        
        if self._neo4j_driver:
            await self._neo4j_driver.close()
            logger.info("Neo4j connection closed")
        
        if self._redis_client:
            await self._redis_client.close()
            logger.info("Redis connection closed")
        
        self._initialized = False
        logger.info("ADAM infrastructure shutdown complete")
    
    @property
    def neo4j(self) -> AsyncDriver:
        if not self._neo4j_driver:
            raise RuntimeError("Infrastructure not initialized")
        return self._neo4j_driver
    
    @property
    def redis(self) -> redis.Redis:
        if not self._redis_client:
            raise RuntimeError("Infrastructure not initialized")
        return self._redis_client

    @property
    def circuit_breakers(self):
        """Get the circuit breaker registry."""
        if self._circuit_breakers is None:
            # Lazy init if infrastructure hasn't been fully initialized
            from adam.infrastructure.resilience.circuit_breaker import (
                get_circuit_breaker_registry,
            )
            self._circuit_breakers = get_circuit_breaker_registry()
        return self._circuit_breakers

    @property
    def neo4j_driver(self):
        """Alias for neo4j property — used by persistence code."""
        return self._neo4j_driver


# =============================================================================
# LEARNING COMPONENTS
# =============================================================================

class LearningComponents:
    """Manages learning component instances."""
    
    _instance: Optional["LearningComponents"] = None
    
    def __init__(self, infrastructure: Infrastructure):
        self._infra = infrastructure
        self._initialized = False
        
        # Component instances
        self._cold_start_learning = None
        self._multimodal_learning = None
        self._feature_store_learning = None
        self._temporal_learning = None
        self._verification_learning = None
        self._emergence_detector = None
        self._signal_router = None
        self._holistic_synthesizer = None
        self._metrics_exporter = None
        
        # Event bus and consumers (Phase 1.3)
        self._event_bus = None
        self._kafka_consumers = []
        
        # Behavioral Analytics (Nonconscious Signal Intelligence)
        self._behavioral_analytics_engine = None
        self._behavioral_learning_bridge = None
        self._behavioral_hypothesis_engine = None
        self._behavioral_knowledge_promoter = None
        self._behavioral_knowledge_graph = None

        # Nonconscious Signal Intelligence (Enhancement #34)
        self._signal_collector = None

        # Therapeutic Retargeting (Enhancement #33 + #36)
        self._hierarchical_prior_manager = None
        self._user_posterior_manager = None
        self._mixed_effects_estimator = None
        self._therapeutic_orchestrator = None
        self._barrier_diagnostic_engine = None
    
    @classmethod
    def get_instance(cls, infrastructure: Infrastructure) -> "LearningComponents":
        if cls._instance is None:
            cls._instance = cls(infrastructure)
        return cls._instance
    
    async def initialize(self) -> None:
        """Initialize all learning components."""
        
        if self._initialized:
            return
        
        logger.info("Initializing ADAM learning components...")
        
        # Import here to avoid circular imports
        from adam.core.learning.universal_learning_interface import LearningSignalRouter
        from adam.coldstart.unified_learning import (
            UnifiedColdStartLearning, 
        )
        from adam.multimodal.learning_integration import MultimodalFusionLearningBridge
        from adam.features.learning_integration import FeatureStoreLearningBridge
        from adam.temporal.learning_integration import TemporalLearningBridge
        from adam.verification.learning_integration import VerificationLearningBridge
        from adam.atoms.emergence_detector import EmergenceDetector
        from adam.monitoring.learning_metrics import LearningMetricsExporter
        
        # Import real cold_start components
        from adam.cold_start.service import ColdStartService, get_cold_start_service
        from adam.cold_start.thompson.sampler import ThompsonSampler, get_thompson_sampler
        from adam.cold_start.archetypes.definitions import ARCHETYPE_DEFINITIONS
        
        # Import v3 cognitive layers
        from src.v3.emergence.engine import get_emergence_engine
        from src.v3.causal.discovery import get_causal_discovery_engine
        from src.v3.temporal.dynamics import get_temporal_dynamics_engine
        from src.v3.metacognitive.reasoning import get_metacognitive_engine
        from src.v3.narrative.session import get_narrative_session_engine
        from src.v3.interactions.mechanism import get_mechanism_interaction_engine
        
        # Import proper event bus from Phase 1.1
        from adam.core.learning.event_bus import (
            InMemoryEventBus,
            KafkaEventBus,
            Event,
        )
        
        # Use InMemoryEventBus unless Kafka is explicitly available
        # Kafka requires a running broker — skip if not configured or unreachable
        use_kafka = False
        if settings.is_production and hasattr(settings, 'kafka'):
            kafka_servers = settings.kafka.bootstrap_servers
            if kafka_servers and kafka_servers != 'localhost:9092':
                use_kafka = True

        if use_kafka:
            try:
                logger.info("Using KafkaEventBus for production")
                event_bus_impl = KafkaEventBus({
                    'bootstrap.servers': settings.kafka.bootstrap_servers,
                    'client.id': 'adam-learning-bus'
                })
                if hasattr(event_bus_impl, 'start'):
                    await event_bus_impl.start()
            except Exception as e:
                logger.warning("Kafka unavailable (%s), falling back to InMemoryEventBus", e)
                event_bus_impl = InMemoryEventBus()
        else:
            logger.info("Using InMemoryEventBus (no Kafka configured)")
            event_bus_impl = InMemoryEventBus()

        if hasattr(event_bus_impl, 'start') and not use_kafka:
            try:
                await event_bus_impl.start()
            except Exception:
                pass
        self._event_bus = event_bus_impl
        
        # Legacy-compatible wrapper for components expecting old interface
        class EventBusWrapper:
            """Wraps the new EventBus to provide backward-compatible interface."""
            
            def __init__(self, event_bus):
                self._bus = event_bus
                self._events = []
            
            async def publish(self, topic: str, event_data: dict):
                """Legacy publish method."""
                from adam.core.learning.event_bus import Event
                event = Event(
                    event_type=topic,
                    source_component="legacy_wrapper",
                    payload=event_data,
                )
                self._events.append((topic, event_data))
                await self._bus.publish(event)
            
            def subscribe(self, topic: str, callback):
                """Legacy subscribe method (sync wrapper)."""
                import asyncio
                asyncio.create_task(self._bus.subscribe(topic, callback))
        
        event_bus = EventBusWrapper(event_bus_impl)
        
        # Prompt manager using Redis
        class RedisPromptManager:
            """Prompt manager backed by Redis."""
            
            def __init__(self, redis_client):
                self.redis = redis_client
                self.prompts = {}
            
            async def get_prompt(self, name: str) -> str:
                if self.redis:
                    try:
                        cached = await self.redis.get(f"prompt:{name}")
                        if cached:
                            return cached
                    except Exception:
                        pass
                return self.prompts.get(name, f"Default prompt for {name}")
            
            async def update_prompt(self, name: str, prompt: str, reason: str):
                self.prompts[name] = prompt
                if self.redis:
                    try:
                        await self.redis.set(f"prompt:{name}", prompt)
                    except Exception:
                        pass
        
        # Verification layer wrapper
        class VerificationLayerWrapper:
            """Wrapper around verification service."""
            
            def __init__(self):
                self.strictness = {}
            
            async def increase_strictness(self, name: str):
                current = self.strictness.get(name, 0.5)
                self.strictness[name] = min(1.0, current + 0.1)
        
        # Claude client wrapper (simplified for now)
        class SimplifiedClaudeClient:
            """Simplified Claude client for development."""
            
            async def complete(self, prompt: str, **kwargs) -> str:
                # In production, this would call the real Claude API
                return "{\"status\": \"ok\"}"
        
        # NOTE: event_bus was correctly set to EventBusWrapper(event_bus_impl) above.
        # A previous bug here overwrote it with SimpleEventBus() which doesn't exist.
        
        # Signal router
        try:
            self._signal_router = LearningSignalRouter(event_bus=event_bus)
        except TypeError:
            self._signal_router = LearningSignalRouter()
        
        # Real cold start service
        cold_start_service = get_cold_start_service()
        thompson_sampler = get_thompson_sampler()
        
        # V3 cognitive layers
        self._v3_emergence = get_emergence_engine()
        self._v3_causal = get_causal_discovery_engine()
        self._v3_temporal = get_temporal_dynamics_engine()
        self._v3_metacognitive = get_metacognitive_engine()
        self._v3_narrative = get_narrative_session_engine()
        self._v3_mechanism = get_mechanism_interaction_engine()
        
        # Initialize each learning bridge in isolation — one failure
        # should not prevent others from initializing.

        try:
            self._cold_start_learning = UnifiedColdStartLearning(
                cold_start_engine=cold_start_service,
                archetype_library=ARCHETYPE_DEFINITIONS,
                thompson_sampler=thompson_sampler,
                neo4j_driver=self._infra.neo4j,
                redis_client=self._infra.redis,
                event_bus=event_bus,
            )
        except Exception as e:
            logger.warning("Cold start learning bridge failed: %s", e)

        try:
            self._multimodal_learning = MultimodalFusionLearningBridge(
                fusion_engine=self._v3_temporal,
                neo4j_driver=self._infra.neo4j,
                redis_client=self._infra.redis,
                event_bus=event_bus,
            )
        except Exception as e:
            logger.warning("Multimodal learning bridge failed: %s", e)

        try:
            self._feature_store_learning = FeatureStoreLearningBridge(
                feature_store=self._v3_causal,
                redis_client=self._infra.redis,
                event_bus=event_bus,
            )
        except Exception as e:
            logger.warning("Feature store learning bridge failed: %s", e)

        try:
            self._temporal_learning = TemporalLearningBridge(
                temporal_engine=self._v3_temporal,
                neo4j_driver=self._infra.neo4j,
                redis_client=self._infra.redis,
                event_bus=event_bus,
            )
        except Exception as e:
            logger.warning("Temporal learning bridge failed: %s", e)

        try:
            prompt_manager = RedisPromptManager(self._infra.redis)
            verification_layer = VerificationLayerWrapper()
            self._verification_learning = VerificationLearningBridge(
                verification_layer=verification_layer,
                atom_prompt_manager=prompt_manager,
                neo4j_driver=self._infra.neo4j,
                redis_client=self._infra.redis,
                event_bus=event_bus,
            )
        except Exception as e:
            logger.warning("Verification learning bridge failed: %s", e)
        
        # Emergence Detector (using v3 emergence engine)
        claude_client = SimplifiedClaudeClient()
        
        try:
            # Emergence Detector
            claude_client = SimplifiedClaudeClient()
            self._emergence_detector = EmergenceDetector(
                neo4j_driver=self._infra.neo4j,
                redis_client=self._infra.redis,
                event_bus=event_bus,
                claude_client=claude_client,
            )
        except Exception as e:
            logger.warning("Emergence detector failed: %s", e)

        # Metrics exporter
        try:
            self._metrics_exporter = LearningMetricsExporter()
        except Exception as e:
            logger.warning("Metrics exporter failed: %s", e)

        logger.info("V3 cognitive layers integrated")
        
        # =====================================================================
        # BEHAVIORAL ANALYTICS (Nonconscious Signal Intelligence)
        # =====================================================================

        try:
            from adam.behavioral_analytics import (
                BehavioralAnalyticsEngine,
                get_behavioral_analytics_engine,
                HypothesisEngine,
                get_hypothesis_engine,
                KnowledgePromoter,
                get_knowledge_promoter,
            )
            from adam.behavioral_analytics.knowledge.graph_integration import (
                BehavioralKnowledgeGraph,
                get_behavioral_knowledge_graph,
            )
            from adam.behavioral_analytics.knowledge.research_seeder import (
                get_research_knowledge_seeder,
            )

            self._behavioral_knowledge_graph = get_behavioral_knowledge_graph(
                neo4j_driver=self._infra.neo4j,
            )
            self._behavioral_hypothesis_engine = get_hypothesis_engine()
            self._behavioral_knowledge_promoter = get_knowledge_promoter(
                hypothesis_engine=self._behavioral_hypothesis_engine,
                graph=self._behavioral_knowledge_graph,
            )
            self._behavioral_analytics_engine = get_behavioral_analytics_engine()

            # Learning bridge (may not exist yet)
            try:
                from adam.behavioral_analytics import (
                    BehavioralLearningBridge,
                    get_behavioral_learning_bridge,
                )
                self._behavioral_learning_bridge = get_behavioral_learning_bridge()
            except ImportError:
                logger.debug("BehavioralLearningBridge not available")

            # Seed research knowledge
            seeder = get_research_knowledge_seeder()
            knowledge_items = seeder.seed_all_knowledge()
            logger.info(
                "Behavioral analytics: seeded %d research-validated knowledge items",
                len(knowledge_items),
            )
        except Exception as e:
            logger.warning("Behavioral analytics partially initialized: %s", e)
        
        # Register all consumers with signal router
        for component in [
            self._cold_start_learning,
            self._multimodal_learning,
            self._feature_store_learning,
            self._temporal_learning,
            self._verification_learning,
            self._emergence_detector,
        ]:
            self._signal_router.register_consumer(component)

        # =================================================================
        # THERAPEUTIC RETARGETING (Enhancement #33 + #36)
        # =================================================================

        try:
            from adam.retargeting.engines.prior_manager import (
                HierarchicalPriorManager,
                get_prior_manager,
            )
            from adam.retargeting.engines.repeated_measures import (
                UserPosteriorManager,
                MixedEffectsEstimator,
            )
            from adam.retargeting.engines.barrier_diagnostic import (
                ConversionBarrierDiagnosticEngine,
            )
            from adam.retargeting.engines.sequence_orchestrator import (
                TherapeuticSequenceOrchestrator,
            )

            # Hierarchical prior manager (singleton with Neo4j persistence)
            self._hierarchical_prior_manager = get_prior_manager(
                neo4j_driver=self._infra.neo4j_driver,
            )

            # Enhancement #36: Within-subject repeated measures
            self._mixed_effects_estimator = MixedEffectsEstimator()
            self._user_posterior_manager = UserPosteriorManager(
                prior_manager=self._hierarchical_prior_manager,
                redis_client=self._infra.redis,
            )
            self._user_posterior_manager.set_mixed_effects(
                self._mixed_effects_estimator,
            )

            # Barrier diagnostic engine (shared singleton)
            self._barrier_diagnostic_engine = ConversionBarrierDiagnosticEngine()

            # Sequence orchestrator with full wiring
            self._therapeutic_orchestrator = TherapeuticSequenceOrchestrator(
                prior_manager=self._hierarchical_prior_manager,
                neo4j_driver=self._infra.neo4j_driver,
                redis_client=self._infra.redis,
                user_posterior_manager=self._user_posterior_manager,
            )

            logger.info(
                "Therapeutic retargeting initialized "
                "(prior manager + user posteriors + barrier diagnostics + orchestrator)"
            )
        except Exception as e:
            logger.debug("Therapeutic retargeting not available: %s", e)

        # Enhancement #34: Nonconscious Signal Intelligence
        try:
            from adam.retargeting.engines.signal_collector import (
                NonconsciousSignalCollector,
            )
            self._signal_collector = NonconsciousSignalCollector(
                redis_client=self._infra.redis,
            )
            logger.info("Nonconscious signal collector initialized")
        except Exception as e:
            logger.debug("Signal collector not available: %s", e)

        # DiagnosticReasoner — core platform deductive engine
        self._diagnostic_reasoner = None
        try:
            from adam.retargeting.engines.diagnostic_reasoner import DiagnosticReasoner
            self._diagnostic_reasoner = DiagnosticReasoner(
                barrier_diagnostic_engine=self._barrier_diagnostic_engine,
            )
            logger.info("DiagnosticReasoner initialized (core platform primitive)")
        except Exception as e:
            logger.debug("DiagnosticReasoner not available: %s", e)

        # =================================================================
        # KAFKA CONSUMERS (Phase 1.3)
        # =================================================================
        
        # Start Kafka consumers in production mode
        if settings.is_production:
            try:
                from adam.infrastructure.kafka.consumer import (
                    create_learning_signal_consumer,
                    create_outcome_consumer,
                )
                
                # Handler that routes signals through the LearningSignalRouter
                async def learning_signal_handler(message: dict):
                    """Route Kafka learning signals to components."""
                    try:
                        from adam.core.learning.event_bus import Event
                        event = Event(
                            event_type=message.get("type", "learning_signal"),
                            source_component=message.get("source", "kafka"),
                            payload=message,
                        )
                        await event_bus_impl.publish(event)
                        logger.debug(f"Routed learning signal: {event.event_type}")
                    except Exception as e:
                        logger.error(f"Failed to route learning signal: {e}")
                
                async def outcome_handler(message: dict):
                    """Route Kafka outcome events to learning components."""
                    try:
                        from adam.core.learning.event_bus import Event
                        event = Event(
                            event_type="outcome_recorded",
                            source_component="kafka",
                            payload=message,
                            # Extract helpful_vote weighting if available
                            confidence=message.get("confidence", 1.0),
                            weight=message.get("weight", 1.0),
                        )
                        await event_bus_impl.publish(event)
                        logger.debug(f"Routed outcome event")
                    except Exception as e:
                        logger.error(f"Failed to route outcome: {e}")
                
                # Start consumers
                learning_consumer = await create_learning_signal_consumer(learning_signal_handler)
                outcome_consumer = await create_outcome_consumer(outcome_handler)
                
                self._kafka_consumers = [learning_consumer, outcome_consumer]
                logger.info(f"Started {len(self._kafka_consumers)} Kafka consumers")
                
            except ImportError as e:
                logger.warning(f"Kafka consumers disabled (aiokafka not installed): {e}")
            except Exception as e:
                logger.error(f"Failed to start Kafka consumers: {e}")
                # Continue without Kafka in non-production
                if settings.is_production:
                    raise
        else:
            logger.info("Kafka consumers disabled in development mode (using InMemoryEventBus)")
        
        self._initialized = True
        logger.info("ADAM learning components initialized (including behavioral analytics)")
    
    async def shutdown(self) -> None:
        """Shutdown learning components and event bus."""
        
        logger.info("Shutting down ADAM learning components...")
        
        # Stop Kafka consumers
        for consumer in self._kafka_consumers:
            try:
                await consumer.stop()
            except Exception as e:
                logger.error(f"Error stopping Kafka consumer: {e}")
        
        # Stop event bus
        if self._event_bus:
            try:
                await self._event_bus.stop()
            except Exception as e:
                logger.error(f"Error stopping event bus: {e}")
        
        self._initialized = False
        logger.info("ADAM learning components shutdown complete")
    
    @property
    def event_bus(self):
        """Get the event bus instance."""
        return self._event_bus
    
    @property
    def cold_start(self):
        return self._cold_start_learning
    
    @property
    def multimodal(self):
        return self._multimodal_learning
    
    @property
    def feature_store(self):
        return self._feature_store_learning
    
    @property
    def temporal(self):
        return self._temporal_learning
    
    @property
    def verification(self):
        return self._verification_learning
    
    @property
    def emergence(self):
        return self._emergence_detector
    
    @property
    def signal_router(self):
        return self._signal_router
    
    @property
    def metrics(self):
        return self._metrics_exporter
    
    # V3 Cognitive Layer Accessors
    @property
    def v3_emergence(self):
        """Get v3 Emergence Engine."""
        return self._v3_emergence
    
    @property
    def v3_causal(self):
        """Get v3 Causal Discovery Engine."""
        return self._v3_causal
    
    @property
    def v3_temporal(self):
        """Get v3 Temporal Dynamics Engine."""
        return self._v3_temporal
    
    @property
    def v3_metacognitive(self):
        """Get v3 Meta-Cognitive Reasoning Engine."""
        return self._v3_metacognitive
    
    @property
    def v3_narrative(self):
        """Get v3 Narrative Session Engine."""
        return self._v3_narrative
    
    @property
    def v3_mechanism(self):
        """Get v3 Mechanism Interaction Engine."""
        return self._v3_mechanism
    
    # =========================================================================
    # BEHAVIORAL ANALYTICS PROPERTIES
    # =========================================================================
    
    @property
    def behavioral_analytics_engine(self):
        """
        Get Behavioral Analytics Engine.
        
        Provides nonconscious signal processing:
        - Touch dynamics, swipe patterns, scroll behavior
        - Hesitation detection, rage click detection
        - Sensor data integration
        - Psychological state inference
        """
        return self._behavioral_analytics_engine
    
    @property
    def behavioral_learning_bridge(self):
        """
        Get Behavioral Learning Bridge.
        
        Connects behavioral outcomes to learning systems:
        - Credit attribution to behavioral signals
        - Hypothesis observation recording
        - Knowledge validation updates
        """
        return self._behavioral_learning_bridge
    
    @property
    def behavioral_hypothesis_engine(self):
        """
        Get Behavioral Hypothesis Engine.
        
        Statistical testing of signal-outcome relationships:
        - Pearson correlation for continuous outcomes
        - Effect size calculation (Cohen's d)
        - Cross-validation for generalization
        """
        return self._behavioral_hypothesis_engine
    
    @property
    def behavioral_knowledge_promoter(self):
        """
        Get Behavioral Knowledge Promoter.
        
        Promotes validated hypotheses to system knowledge:
        - Statistical significance checking
        - Effect size thresholds
        - Observation count requirements
        """
        return self._behavioral_knowledge_promoter
    
    @property
    def behavioral_knowledge_graph(self):
        """
        Get Behavioral Knowledge Graph.
        
        Neo4j storage for behavioral intelligence:
        - Research-validated knowledge nodes
        - System-discovered patterns
        - Hypothesis lifecycle tracking
        - Signal-construct relationships
        """
        return self._behavioral_knowledge_graph

    # =========================================================================
    # THERAPEUTIC RETARGETING PROPERTIES (Enhancement #33 + #36)
    # =========================================================================

    @property
    def hierarchical_prior_manager(self):
        """Get HierarchicalPriorManager — 6-level Bayesian prior hierarchy."""
        return self._hierarchical_prior_manager

    @property
    def user_posterior_manager(self):
        """Get UserPosteriorManager — per-user mechanism posteriors (Enhancement #36)."""
        return self._user_posterior_manager

    @property
    def mixed_effects_estimator(self):
        """Get MixedEffectsEstimator — ICC and design-effect computation."""
        return self._mixed_effects_estimator

    @property
    def therapeutic_orchestrator(self):
        """Get TherapeuticSequenceOrchestrator — full retargeting lifecycle."""
        return self._therapeutic_orchestrator

    @property
    def barrier_diagnostic_engine(self):
        """Get ConversionBarrierDiagnosticEngine — shared singleton."""
        return self._barrier_diagnostic_engine

    @property
    def signal_collector(self):
        """Get NonconsciousSignalCollector — telemetry ingestion (Enhancement #34)."""
        return self._signal_collector

    @property
    def diagnostic_reasoner(self):
        """Get DiagnosticReasoner — core platform deductive engine."""
        return self._diagnostic_reasoner


# =============================================================================
# FASTAPI DEPENDENCIES
# =============================================================================

async def get_infrastructure() -> Infrastructure:
    """Get infrastructure instance."""
    return Infrastructure.get_instance()


async def get_neo4j() -> AsyncDriver:
    """Get Neo4j driver."""
    infra = Infrastructure.get_instance()
    return infra.neo4j


async def get_redis() -> redis.Redis:
    """Get Redis client."""
    infra = Infrastructure.get_instance()
    return infra.redis


async def get_learning_components() -> LearningComponents:
    """Get learning components instance."""
    infra = Infrastructure.get_instance()
    return LearningComponents.get_instance(infra)


async def get_cold_start_learning():
    """Get cold start learning component."""
    components = await get_learning_components()
    return components.cold_start


async def get_multimodal_learning():
    """Get multimodal learning component."""
    components = await get_learning_components()
    return components.multimodal


async def get_feature_store_learning():
    """Get feature store learning component."""
    components = await get_learning_components()
    return components.feature_store


async def get_temporal_learning():
    """Get temporal learning component."""
    components = await get_learning_components()
    return components.temporal


async def get_verification_learning():
    """Get verification learning component."""
    components = await get_learning_components()
    return components.verification


async def get_emergence_detector():
    """Get emergence detector."""
    components = await get_learning_components()
    return components.emergence


async def get_signal_router():
    """Get signal router."""
    components = await get_learning_components()
    return components.signal_router


async def get_metrics_exporter():
    """Get metrics exporter."""
    components = await get_learning_components()
    return components.metrics


async def get_event_bus():
    """
    Get the event bus for publishing learning signals.
    
    The event bus enables asynchronous communication between components:
    - InMemoryEventBus for local development
    - KafkaEventBus for production
    
    Example:
        @router.post("/decisions/{id}/outcome")
        async def record_outcome(
            id: str,
            outcome: OutcomeData,
            event_bus = Depends(get_event_bus),
        ):
            from adam.core.learning.event_bus import Event
            event = Event(
                event_type="outcome_recorded",
                source_component="decision_api",
                payload={"decision_id": id, **outcome.dict()},
            )
            await event_bus.publish(event)
    """
    components = await get_learning_components()
    return components.event_bus


# =============================================================================
# V3 COGNITIVE LAYER DEPENDENCIES
# =============================================================================

async def get_v3_emergence():
    """Get v3 Emergence Engine."""
    components = await get_learning_components()
    return components.v3_emergence


async def get_v3_causal():
    """Get v3 Causal Discovery Engine."""
    components = await get_learning_components()
    return components.v3_causal


async def get_v3_temporal():
    """Get v3 Temporal Dynamics Engine."""
    components = await get_learning_components()
    return components.v3_temporal


async def get_v3_metacognitive():
    """Get v3 Meta-Cognitive Reasoning Engine."""
    components = await get_learning_components()
    return components.v3_metacognitive


async def get_v3_narrative():
    """Get v3 Narrative Session Engine."""
    components = await get_learning_components()
    return components.v3_narrative


async def get_v3_mechanism():
    """Get v3 Mechanism Interaction Engine."""
    components = await get_learning_components()
    return components.v3_mechanism


# =============================================================================
# BEHAVIORAL ANALYTICS DEPENDENCIES
# =============================================================================

async def get_behavioral_analytics_engine():
    """
    Get Behavioral Analytics Engine.
    
    The engine provides nonconscious signal intelligence:
    - Session processing with implicit signal extraction
    - Psychological state inference from behavioral signals
    - Integration with hypothesis testing pipeline
    
    Example:
        @router.post("/behavioral/session")
        async def process_session(
            session: BehavioralSession,
            engine = Depends(get_behavioral_analytics_engine),
        ):
            result = await engine.process_session(session)
            return result
    """
    components = await get_learning_components()
    return components.behavioral_analytics_engine


async def get_behavioral_learning_bridge():
    """
    Get Behavioral Learning Bridge.
    
    The bridge connects behavioral outcomes to:
    - Gradient Bridge for credit attribution
    - Hypothesis engine for observation recording
    - Knowledge graph for pattern validation
    
    Example:
        @router.post("/behavioral/outcome")
        async def record_outcome(
            outcome: BehavioralOutcome,
            bridge = Depends(get_behavioral_learning_bridge),
        ):
            event = await bridge.process_outcome(outcome)
            return event.to_dict()
    """
    components = await get_learning_components()
    return components.behavioral_learning_bridge


async def get_behavioral_hypothesis_engine():
    """
    Get Behavioral Hypothesis Engine.
    
    Manages statistical testing of signal-outcome relationships:
    - Hypothesis generation from observed patterns
    - Statistical validation (p-value, effect size)
    - Cross-validation for generalization
    
    Example:
        @router.get("/behavioral/hypotheses")
        async def get_hypotheses(
            engine = Depends(get_behavioral_hypothesis_engine),
        ):
            return engine.get_all_hypotheses()
    """
    components = await get_learning_components()
    return components.behavioral_hypothesis_engine


async def get_behavioral_knowledge_promoter():
    """
    Get Behavioral Knowledge Promoter.
    
    Promotes validated hypotheses to system knowledge:
    - Criteria checking (observations, p-value, effect size)
    - Knowledge creation from hypothesis
    - Propagation to all components
    
    Example:
        @router.post("/behavioral/hypotheses/{id}/promote")
        async def promote_hypothesis(
            id: str,
            promoter = Depends(get_behavioral_knowledge_promoter),
        ):
            event = await promoter.promote_hypothesis(id)
            return event.to_dict()
    """
    components = await get_learning_components()
    return components.behavioral_knowledge_promoter


async def get_behavioral_knowledge_graph():
    """
    Get Behavioral Knowledge Graph.
    
    Provides Neo4j storage for:
    - Research-validated behavioral knowledge
    - System-discovered patterns
    - Hypothesis lifecycle tracking
    
    Example:
        @router.get("/behavioral/knowledge/{construct}")
        async def get_knowledge(
            construct: str,
            graph = Depends(get_behavioral_knowledge_graph),
        ):
            return await graph.get_knowledge_for_construct(construct)
    """
    components = await get_learning_components()
    return components.behavioral_knowledge_graph


# =============================================================================
# THERAPEUTIC RETARGETING DEPENDENCIES (Enhancement #33 + #36)
# =============================================================================

async def get_hierarchical_prior_manager():
    """Get HierarchicalPriorManager — 6-level Bayesian prior hierarchy.

    Platform primitive used by retargeting, bilateral cascade, outcome handler,
    and campaign orchestrator for barrier-conditioned mechanism selection.
    """
    components = await get_learning_components()
    return components.hierarchical_prior_manager


async def get_user_posterior_manager():
    """Get UserPosteriorManager — per-user mechanism posteriors (Enhancement #36).

    Provides within-subject repeated measures analysis:
    - Per-user Beta posteriors (L1 memory + L2 Redis)
    - Design-effect weighting for population updates
    - Cold-start from population posteriors
    """
    components = await get_learning_components()
    return components.user_posterior_manager


async def get_mixed_effects_estimator():
    """Get MixedEffectsEstimator — ICC and design-effect computation.

    Online method-of-moments variance decomposition for
    between/within-user variance, intraclass correlation,
    and design-effect weighting.
    """
    components = await get_learning_components()
    return components.mixed_effects_estimator


async def get_therapeutic_orchestrator():
    """Get TherapeuticSequenceOrchestrator — full retargeting lifecycle.

    The orchestrator manages: diagnosis → mechanism selection → sequence
    creation → touch generation → outcome processing → learning.
    """
    components = await get_learning_components()
    return components.therapeutic_orchestrator


async def get_barrier_diagnostic_engine():
    """Get ConversionBarrierDiagnosticEngine — shared singleton.

    Diagnoses conversion barriers from bilateral edge gaps and
    behavioral signals. Used by retargeting AND first-touch flows.
    """
    components = await get_learning_components()
    return components.barrier_diagnostic_engine


async def get_signal_collector():
    """Get NonconsciousSignalCollector — telemetry ingestion (Enhancement #34).

    Receives site telemetry payloads and accumulates per-user signal
    profiles in Redis. Feeds all 6 nonconscious signals.
    """
    components = await get_learning_components()
    return components.signal_collector


async def get_diagnostic_reasoner():
    """Get DiagnosticReasoner — core platform deductive engine.

    Interprets each outcome as evidence about a psychological puzzle,
    then selects the constrained next move that maximizes diagnostic
    information. Used by retargeting orchestrator, campaign orchestrator,
    and any system that reasons about Person x PageMindstate x Mechanism.
    """
    components = await get_learning_components()
    return components.diagnostic_reasoner
