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
        
        # Behavioral Analytics (Nonconscious Signal Intelligence)
        self._behavioral_analytics_engine = None
        self._behavioral_learning_bridge = None
        self._behavioral_hypothesis_engine = None
        self._behavioral_knowledge_promoter = None
        self._behavioral_knowledge_graph = None
    
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
        
        # Simple event bus implementation
        class SimpleEventBus:
            """Simple in-memory event bus for development."""
            
            def __init__(self):
                self._subscribers = {}
                self._events = []
            
            async def publish(self, topic: str, event: dict):
                self._events.append((topic, event))
                if topic in self._subscribers:
                    for callback in self._subscribers[topic]:
                        try:
                            await callback(event)
                        except Exception as e:
                            logger.error(f"Event callback error: {e}")
            
            def subscribe(self, topic: str, callback):
                if topic not in self._subscribers:
                    self._subscribers[topic] = []
                self._subscribers[topic].append(callback)
        
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
        
        event_bus = SimpleEventBus()
        
        # Signal router
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
        
        # Cold Start Learning
        self._cold_start_learning = UnifiedColdStartLearning(
            cold_start_engine=cold_start_service,
            archetype_library=ARCHETYPE_DEFINITIONS,
            thompson_sampler=thompson_sampler,
            neo4j_driver=self._infra.neo4j,
            redis_client=self._infra.redis,
            event_bus=event_bus,
        )
        
        # Multimodal Fusion (using v3 temporal dynamics)
        self._multimodal_learning = MultimodalFusionLearningBridge(
            fusion_engine=self._v3_temporal,  # Use temporal dynamics for multimodal fusion
            neo4j_driver=self._infra.neo4j,
            redis_client=self._infra.redis,
            event_bus=event_bus,
        )
        
        # Feature Store (using v3 causal discovery for feature importance)
        self._feature_store_learning = FeatureStoreLearningBridge(
            feature_store=self._v3_causal,  # Use causal discovery for feature relationships
            neo4j_driver=self._infra.neo4j,
            redis_client=self._infra.redis,
            event_bus=event_bus,
        )
        
        # Temporal Patterns (using v3 temporal dynamics)
        self._temporal_learning = TemporalLearningBridge(
            temporal_engine=self._v3_temporal,
            neo4j_driver=self._infra.neo4j,
            redis_client=self._infra.redis,
            event_bus=event_bus,
        )
        
        # Verification (with real prompt manager and verification layer)
        prompt_manager = RedisPromptManager(self._infra.redis)
        verification_layer = VerificationLayerWrapper()
        
        self._verification_learning = VerificationLearningBridge(
            verification_layer=verification_layer,
            atom_prompt_manager=prompt_manager,
            neo4j_driver=self._infra.neo4j,
            redis_client=self._infra.redis,
            event_bus=event_bus,
        )
        
        # Emergence Detector (using v3 emergence engine)
        claude_client = SimplifiedClaudeClient()
        
        self._emergence_detector = EmergenceDetector(
            neo4j_driver=self._infra.neo4j,
            redis_client=self._infra.redis,
            event_bus=event_bus,
            claude_client=claude_client,
        )
        
        # Metrics exporter
        self._metrics_exporter = LearningMetricsExporter()
        
        logger.info("V3 cognitive layers integrated")
        
        # =====================================================================
        # BEHAVIORAL ANALYTICS (Nonconscious Signal Intelligence)
        # =====================================================================
        
        from adam.behavioral_analytics import (
            BehavioralAnalyticsEngine,
            get_behavioral_analytics_engine,
            BehavioralLearningBridge,
            get_behavioral_learning_bridge,
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
        
        # Knowledge graph for Neo4j storage
        self._behavioral_knowledge_graph = get_behavioral_knowledge_graph(
            neo4j_driver=self._infra.neo4j,
        )
        
        # Hypothesis engine for testing signal-outcome relationships
        self._behavioral_hypothesis_engine = get_hypothesis_engine()
        
        # Knowledge promoter for validated pattern promotion
        self._behavioral_knowledge_promoter = get_knowledge_promoter(
            hypothesis_engine=self._behavioral_hypothesis_engine,
            graph=self._behavioral_knowledge_graph,
        )
        
        # Main analytics engine
        self._behavioral_analytics_engine = get_behavioral_analytics_engine()
        
        # Learning bridge for Gradient Bridge integration
        self._behavioral_learning_bridge = get_behavioral_learning_bridge()
        
        # Seed research-validated knowledge
        seeder = get_research_knowledge_seeder()
        knowledge_items = seeder.seed_all_knowledge()
        logger.info(
            f"Behavioral analytics: seeded {len(knowledge_items)} "
            "research-validated knowledge items"
        )
        
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
        
        self._initialized = True
        logger.info("ADAM learning components initialized (including behavioral analytics)")
    
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
