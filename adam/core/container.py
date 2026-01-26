# =============================================================================
# ADAM Dependency Container
# Location: adam/core/container.py
# =============================================================================

"""
DEPENDENCY CONTAINER

Unified dependency injection for all ADAM components.
Wires together the complete system from infrastructure to workflow.

Usage:
    container = ADAMContainer()
    await container.initialize()
    
    # Use components
    decision = await container.workflow_executor.execute(...)
"""

import logging
from typing import Optional
from dataclasses import dataclass

from neo4j import AsyncDriver

from adam.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ContainerConfig:
    """Configuration for the dependency container."""
    
    # Enable/disable components
    enable_kafka: bool = True
    enable_redis: bool = True
    enable_neo4j: bool = True
    
    # Test mode (uses mocks)
    test_mode: bool = False


class ADAMContainer:
    """
    Unified dependency container for ADAM platform.
    
    Provides lazy initialization and proper cleanup of all components.
    """
    
    def __init__(self, config: Optional[ContainerConfig] = None):
        self.config = config or ContainerConfig()
        self.settings = get_settings()
        self._initialized = False
        
        # Infrastructure
        self._neo4j_driver: Optional[AsyncDriver] = None
        self._redis_cache = None
        self._kafka_producer = None
        
        # Core Services
        self._blackboard_service = None
        self._meta_learner_service = None
        self._gradient_bridge_service = None
        self._verification_service = None
        
        # Graph Reasoning
        self._interaction_bridge = None
        
        # Atoms
        self._atom_dag = None
        
        # Workflow
        self._workflow_executor = None
        self._holistic_synthesizer = None
        
        # V3 Cognitive Layers
        self._v3_emergence = None
        self._v3_causal = None
        self._v3_temporal = None
        self._v3_metacognitive = None
        self._v3_narrative = None
        self._v3_mechanism = None
        
        # Behavioral Analytics (Nonconscious Signal Intelligence)
        self._behavioral_analytics_engine = None
        self._behavioral_learning_bridge = None
        self._behavioral_knowledge_graph = None
        self._behavioral_hypothesis_engine = None
        self._behavioral_knowledge_promoter = None
        
        # Cold Start Strategy
        self._cold_start_service = None
    
    async def initialize(self) -> None:
        """Initialize all components in dependency order."""
        if self._initialized:
            return
        
        logger.info("Initializing ADAM Container...")
        
        # Phase 1: Infrastructure
        await self._init_infrastructure()
        
        # Phase 2: Core Services
        await self._init_core_services()
        
        # Phase 3: Reasoning Components
        await self._init_reasoning_components()
        
        # Phase 4: V3 Cognitive Layers
        await self._init_v3_cognitive_layers()
        
        # Phase 5: Behavioral Analytics (Nonconscious Signal Intelligence)
        await self._init_behavioral_analytics()
        
        # Phase 6: Workflow
        await self._init_workflow()
        
        self._initialized = True
        logger.info("ADAM Container initialized successfully")
    
    async def _init_infrastructure(self) -> None:
        """Initialize infrastructure components."""
        
        # Neo4j
        if self.config.enable_neo4j and not self.config.test_mode:
            from neo4j import AsyncGraphDatabase
            self._neo4j_driver = AsyncGraphDatabase.driver(
                self.settings.NEO4J_URI,
                auth=(self.settings.NEO4J_USER, self.settings.NEO4J_PASSWORD),
            )
            logger.info("Neo4j driver initialized")
        
        # Redis
        if self.config.enable_redis and not self.config.test_mode:
            from adam.infrastructure.redis import ADAMRedisCache
            self._redis_cache = ADAMRedisCache(
                host=self.settings.REDIS_HOST,
                port=self.settings.REDIS_PORT,
            )
            await self._redis_cache.connect()
            logger.info("Redis cache initialized")
        else:
            # Mock cache for testing
            from adam.infrastructure.redis import ADAMRedisCache
            self._redis_cache = ADAMRedisCache()
        
        # Kafka
        if self.config.enable_kafka and not self.config.test_mode:
            from adam.infrastructure.kafka import get_kafka_producer
            self._kafka_producer = await get_kafka_producer()
            logger.info("Kafka producer initialized")
    
    async def _init_core_services(self) -> None:
        """Initialize core services."""
        
        # Blackboard Service
        from adam.blackboard.service import BlackboardService
        self._blackboard_service = BlackboardService(
            redis_cache=self._redis_cache,
        )
        logger.info("Blackboard service initialized")
        
        # Interaction Bridge (Graph Reasoning)
        from adam.graph_reasoning.bridge import InteractionBridge
        self._interaction_bridge = InteractionBridge(
            neo4j_driver=self._neo4j_driver,
            redis_cache=self._redis_cache,
        )
        logger.info("Interaction bridge initialized")
        
        # Meta-Learner Service
        from adam.meta_learner.service import MetaLearnerService
        self._meta_learner_service = MetaLearnerService(
            blackboard=self._blackboard_service,
            cache=self._redis_cache,
        )
        logger.info("Meta-learner service initialized")
        
        # Gradient Bridge Service
        from adam.gradient_bridge.service import GradientBridgeService
        self._gradient_bridge_service = GradientBridgeService(
            blackboard=self._blackboard_service,
            bridge=self._interaction_bridge,
            cache=self._redis_cache,
        )
        logger.info("Gradient bridge service initialized")
        
        # Verification Service
        from adam.verification.service import VerificationService
        self._verification_service = VerificationService(
            blackboard=self._blackboard_service,
            bridge=self._interaction_bridge,
            cache=self._redis_cache,
        )
        logger.info("Verification service initialized")
        
        # Cold Start Service
        from adam.cold_start.service import get_cold_start_service
        self._cold_start_service = get_cold_start_service()
        logger.info("Cold start service initialized")
    
    async def _init_reasoning_components(self) -> None:
        """Initialize reasoning components."""
        
        # Atom DAG
        from adam.atoms.dag import AtomDAG
        self._atom_dag = AtomDAG(
            blackboard=self._blackboard_service,
            bridge=self._interaction_bridge,
        )
        logger.info("Atom DAG initialized")
        
        # Holistic Synthesizer
        from adam.core.synthesis.holistic_decision_synthesizer import HolisticDecisionSynthesizer
        self._holistic_synthesizer = HolisticDecisionSynthesizer(
            blackboard=self._blackboard_service,
            verification=self._verification_service,
            bridge=self._interaction_bridge,
        )
        logger.info("Holistic synthesizer initialized")
    
    async def _init_v3_cognitive_layers(self) -> None:
        """Initialize v3 cognitive intelligence layers."""
        
        from src.v3.emergence.engine import get_emergence_engine
        from src.v3.causal.discovery import get_causal_discovery_engine
        from src.v3.temporal.dynamics import get_temporal_dynamics_engine
        from src.v3.metacognitive.reasoning import get_metacognitive_engine
        from src.v3.narrative.session import get_narrative_session_engine
        from src.v3.interactions.mechanism import get_mechanism_interaction_engine
        
        self._v3_emergence = get_emergence_engine()
        self._v3_causal = get_causal_discovery_engine()
        self._v3_temporal = get_temporal_dynamics_engine()
        self._v3_metacognitive = get_metacognitive_engine()
        self._v3_narrative = get_narrative_session_engine()
        self._v3_mechanism = get_mechanism_interaction_engine()
        
        logger.info("V3 cognitive layers initialized (6 engines)")
    
    async def _init_behavioral_analytics(self) -> None:
        """
        Initialize behavioral analytics components.
        
        Behavioral Analytics provides nonconscious signal intelligence:
        - Implicit behavioral signal collection (touch, swipe, scroll, hesitation)
        - Psychological state inference (arousal, confidence, intent)
        - Hypothesis testing for signal-outcome relationships
        - Knowledge promotion for validated patterns
        - Learning signal emission to Gradient Bridge
        """
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
        
        # Initialize knowledge graph for Neo4j storage
        self._behavioral_knowledge_graph = get_behavioral_knowledge_graph(
            neo4j_driver=self._neo4j_driver,
        )
        if self._neo4j_driver:
            await self._behavioral_knowledge_graph.create_schema()
        logger.info("Behavioral knowledge graph initialized")
        
        # Initialize hypothesis engine for testing signal-outcome relationships
        self._behavioral_hypothesis_engine = get_hypothesis_engine()
        logger.info("Behavioral hypothesis engine initialized")
        
        # Initialize knowledge promoter for validating patterns
        self._behavioral_knowledge_promoter = get_knowledge_promoter(
            hypothesis_engine=self._behavioral_hypothesis_engine,
            graph=self._behavioral_knowledge_graph,
        )
        logger.info("Behavioral knowledge promoter initialized")
        
        # Initialize main analytics engine
        self._behavioral_analytics_engine = get_behavioral_analytics_engine()
        logger.info("Behavioral analytics engine initialized")
        
        # Initialize learning bridge for Gradient Bridge integration
        self._behavioral_learning_bridge = get_behavioral_learning_bridge()
        logger.info("Behavioral learning bridge initialized")
        
        # Seed research-validated knowledge
        from adam.behavioral_analytics.knowledge.research_seeder import (
            get_research_knowledge_seeder,
        )
        seeder = get_research_knowledge_seeder()
        knowledge_items = seeder.seed_all_knowledge()
        logger.info(
            f"Behavioral analytics: seeded {len(knowledge_items)} "
            "research-validated knowledge items"
        )
        
        # Store seeded knowledge in graph
        if self._neo4j_driver:
            for knowledge in knowledge_items:
                await self._behavioral_knowledge_graph.store_knowledge(knowledge)
            logger.info("Research knowledge stored in Neo4j graph")
    
    async def _init_workflow(self) -> None:
        """Initialize workflow executor."""
        # Workflow executor is built on-demand
        logger.info("Workflow components ready")
    
    async def shutdown(self) -> None:
        """Clean shutdown of all components."""
        logger.info("Shutting down ADAM Container...")
        
        if self._neo4j_driver:
            await self._neo4j_driver.close()
        
        if self._redis_cache:
            await self._redis_cache.close()
        
        if self._kafka_producer:
            await self._kafka_producer.stop()
        
        self._initialized = False
        logger.info("ADAM Container shutdown complete")
    
    # =========================================================================
    # COMPONENT ACCESSORS
    # =========================================================================
    
    @property
    def neo4j_driver(self) -> AsyncDriver:
        """Get Neo4j driver."""
        return self._neo4j_driver
    
    @property
    def redis_cache(self):
        """Get Redis cache."""
        return self._redis_cache
    
    @property
    def blackboard(self):
        """Get Blackboard service."""
        return self._blackboard_service
    
    @property
    def meta_learner(self):
        """Get Meta-Learner service."""
        return self._meta_learner_service
    
    @property
    def gradient_bridge(self):
        """Get Gradient Bridge service."""
        return self._gradient_bridge_service
    
    @property
    def verification(self):
        """Get Verification service."""
        return self._verification_service
    
    @property
    def interaction_bridge(self):
        """Get Interaction Bridge."""
        return self._interaction_bridge
    
    @property
    def atom_dag(self):
        """Get Atom DAG."""
        return self._atom_dag
    
    @property
    def holistic_synthesizer(self):
        """Get Holistic Synthesizer."""
        return self._holistic_synthesizer
    
    @property
    def cold_start_service(self):
        """Get Cold Start Service."""
        return self._cold_start_service
    
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
    # BEHAVIORAL ANALYTICS ACCESSORS
    # =========================================================================
    
    @property
    def behavioral_analytics_engine(self):
        """
        Get Behavioral Analytics Engine.
        
        The engine provides:
        - Session processing with implicit signal extraction
        - Psychological state inference from behavioral signals
        - Integration with hypothesis testing pipeline
        - Real-time and batch analytics modes
        """
        return self._behavioral_analytics_engine
    
    @property
    def behavioral_learning_bridge(self):
        """
        Get Behavioral Learning Bridge.
        
        The bridge connects behavioral outcomes to:
        - Gradient Bridge for credit attribution
        - Hypothesis engine for observation recording
        - Knowledge graph for pattern validation
        """
        return self._behavioral_learning_bridge
    
    @property
    def behavioral_knowledge_graph(self):
        """
        Get Behavioral Knowledge Graph.
        
        Provides Neo4j storage for:
        - Research-validated behavioral knowledge
        - System-discovered patterns
        - Hypothesis lifecycle tracking
        """
        return self._behavioral_knowledge_graph
    
    @property
    def behavioral_hypothesis_engine(self):
        """
        Get Behavioral Hypothesis Engine.
        
        Manages statistical testing of signal-outcome relationships:
        - Hypothesis generation from observed patterns
        - Statistical validation (p-value, effect size)
        - Cross-validation for generalization
        - Promotion criteria checking
        """
        return self._behavioral_hypothesis_engine
    
    @property
    def behavioral_knowledge_promoter(self):
        """
        Get Behavioral Knowledge Promoter.
        
        Promotes validated hypotheses to system knowledge:
        - Criteria checking (observations, p-value, effect size)
        - Knowledge creation from hypothesis
        - Propagation to all components
        - Event emission for learning
        """
        return self._behavioral_knowledge_promoter


# =============================================================================
# GLOBAL CONTAINER
# =============================================================================

_container: Optional[ADAMContainer] = None


async def get_container() -> ADAMContainer:
    """Get the global container instance."""
    global _container
    if _container is None:
        _container = ADAMContainer()
        await _container.initialize()
    return _container


async def shutdown_container() -> None:
    """Shutdown the global container."""
    global _container
    if _container:
        await _container.shutdown()
        _container = None
