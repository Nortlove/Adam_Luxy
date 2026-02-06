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
        
        # Review Intelligence (Cookie-less Targeting)
        self._review_intelligence_bridge = None
    
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
        
        # Phase 7: Learning Component Registration (CRITICAL FIX)
        # This was missing - components were emitting signals but not registered to receive them
        await self._init_learning_signal_routing()
        
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
        """
        Initialize the Holistic Decision Workflow Executor.
        
        This is CRITICAL - the workflow executor orchestrates all decision-making
        via LangGraph, integrating all psychological reasoning, learning, and synthesis.
        
        Previously this was a STUB that just logged a message. Now it properly
        initializes the complete workflow with all dependencies.
        """
        logger.info("Initializing workflow executor...")
        
        try:
            # Import workflow components
            from adam.workflows.holistic_decision_workflow import HolisticDecisionWorkflowExecutor
            from adam.core.learning.component_integrations import (
                MetaLearnerLearningIntegration,
                AtomOfThoughtLearningIntegration,
                get_learning_registry,
            )
            from adam.signals.learning_integration import SignalLearningBridge
            
            # Import services (using our newly created services)
            from adam.services import (
                get_brand_library_service,
                get_competitive_intel_service,
                get_temporal_patterns_service,
                get_archetype_service,
                get_bandit_service,
            )
            from adam.user.signal_aggregation.service import get_signal_aggregation_service
            from adam.user.journey.service import get_journey_tracking_service
            
            # Get or create learning signal router
            if hasattr(self, '_signal_router') and self._signal_router:
                learning_signal_router = self._signal_router
            else:
                from adam.core.learning.universal_learning_interface import LearningSignalRouter
                from adam.core.learning.event_bus import InMemoryEventBus
                event_bus = InMemoryEventBus()
                learning_signal_router = LearningSignalRouter(event_bus)
            
            # Start the learning signal router to subscribe to event bus
            # This enables: Kafka → EventBus → Router → Components flow
            await learning_signal_router.start()
            
            # Create integration instances
            meta_learner_integration = MetaLearnerLearningIntegration(
                meta_learner=self._meta_learner_service,
                redis_client=self._redis_cache,
                neo4j_driver=self._neo4j_driver,
            )
            
            atom_integration = AtomOfThoughtLearningIntegration(
                atom_executor=self._atom_dag,
                redis_client=self._redis_cache,
                neo4j_driver=self._neo4j_driver,
            )
            
            signal_integration = SignalLearningBridge(
                neo4j_driver=self._neo4j_driver,
                redis_client=self._redis_cache,
                event_bus=learning_signal_router._event_bus if hasattr(learning_signal_router, '_event_bus') else InMemoryEventBus(),
            )
            
            # Get services
            signal_aggregation = get_signal_aggregation_service()
            journey_tracker = get_journey_tracking_service()
            temporal_patterns = get_temporal_patterns_service(neo4j_driver=self._neo4j_driver)
            brand_library = get_brand_library_service(neo4j_driver=self._neo4j_driver)
            competitive_intel = get_competitive_intel_service(neo4j_driver=self._neo4j_driver)
            archetype_service = get_archetype_service(neo4j_driver=self._neo4j_driver)
            bandit_service = get_bandit_service(neo4j_driver=self._neo4j_driver)
            
            # Import advanced engines (Phase 5: V3 Cognitive Engines)
            from adam.meta_learner.neural_thompson import get_neural_thompson_engine
            from adam.intelligence.predictive_processing import get_predictive_processing_engine
            
            neural_thompson = get_neural_thompson_engine()
            predictive_engine = get_predictive_processing_engine()
            
            # Phase 1 (Full Intelligence): Import and create FullIntelligenceIntegrator
            # This ensures 100% of our intelligence capabilities are used in every decision
            from adam.intelligence.full_intelligence_integration import (
                FullIntelligenceIntegrator,
                get_full_intelligence_integrator,
            )
            full_intelligence_integrator = get_full_intelligence_integrator()
            logger.info("Full Intelligence Integrator initialized - 100% capability utilization enabled")
            
            # Create the workflow executor
            self._workflow_executor = HolisticDecisionWorkflowExecutor(
                interaction_bridge=self._interaction_bridge,
                blackboard_service=self._blackboard_service,
                meta_learner=self._meta_learner_service,
                meta_learner_integration=meta_learner_integration,
                atom_executor=self._atom_dag,
                atom_integration=atom_integration,
                signal_aggregation=signal_aggregation,
                signal_integration=signal_integration,
                journey_tracker=journey_tracker,
                temporal_patterns=temporal_patterns,
                brand_library=brand_library,
                competitive_intel=competitive_intel,
                holistic_synthesizer=self._holistic_synthesizer,
                learning_signal_router=learning_signal_router,
                cache_service=self._redis_cache,
                archetype_service=archetype_service,
                bandit_service=bandit_service,
                # Phase 5: V3 Cognitive Engines - Now wired!
                neural_thompson_engine=neural_thompson,
                predictive_engine=predictive_engine,
                emergence_engine=self._v3_emergence,  # V3 emergence engine
                use_enhanced_routing=True,  # Enable enhanced routing with neural thompson
                # Phase 1 (Full Intelligence): FullIntelligenceIntegrator - Now wired!
                full_intelligence_integrator=full_intelligence_integrator,
                # CRITICAL FIX (Feb 2026): Pass Neo4j driver for graph intelligence queries
                neo4j_driver=self._neo4j_driver,
            )
            
            # Store integration references for learning loop
            self._meta_learner_integration = meta_learner_integration
            self._atom_integration = atom_integration
            self._signal_integration = signal_integration
            self._learning_signal_router = learning_signal_router
            
            # Initialize bidirectional bridge for Graph-AoT communication
            # This enables: decision persistence, learning paths, conflict resolution
            from adam.graph_reasoning.bridge import (
                get_bidirectional_bridge,
                BidirectionalBridgeIntegration,
            )
            self._bidirectional_bridge = get_bidirectional_bridge(
                neo4j_driver=self._neo4j_driver,
                redis_cache=self._redis_cache,
            )
            if self._bidirectional_bridge:
                await self._bidirectional_bridge.start()
                logger.info("Bidirectional bridge initialized and started")
            
            logger.info("Workflow executor initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize workflow executor: {e}")
            # Non-fatal - system can still function without workflow
            # Individual components can be called directly
            self._workflow_executor = None
    
    async def _init_learning_signal_routing(self) -> None:
        """
        Initialize learning signal routing using UnifiedLearningHub.
        
        SYNERGISTIC BRAIN ARCHITECTURE:
        UnifiedLearningHub is THE SINGLE source of truth for all learning signals.
        It consolidates signal_router.py and universal_learning_interface.py,
        providing both signal routing AND direct updates (belt & suspenders).
        
        Signal Flow:
        1. Outcomes → Gradient Bridge → UnifiedLearningHub
        2. UnifiedLearningHub → Direct updates (Thompson, Graph, Meta-learner)
        3. UnifiedLearningHub → Registered component handlers
        4. Zone 5 (Blackboard) → UnifiedLearningHub for attribution context
        """
        try:
            from adam.core.learning.unified_learning_hub import (
                UnifiedLearningHub,
                UnifiedSignalType,
                get_unified_learning_hub,
            )
            
            # Get or create the singleton UnifiedLearningHub
            self._unified_learning_hub = get_unified_learning_hub()
            await self._unified_learning_hub.initialize()
            
            # Register all learning-capable components with the hub
            registered_count = 0
            
            # Meta-learner - receives credit and outcome signals
            if self._meta_learner_service:
                try:
                    async def meta_learner_handler(signal):
                        if hasattr(self._meta_learner_service, 'on_learning_signal'):
                            await self._meta_learner_service.on_learning_signal(signal)
                    
                    self._unified_learning_hub.register_component(
                        name="meta_learner",
                        handler=meta_learner_handler,
                        signal_types={
                            UnifiedSignalType.OUTCOME_SUCCESS,
                            UnifiedSignalType.OUTCOME_FAILURE,
                            UnifiedSignalType.UPDATE_META_LEARNER,
                            UnifiedSignalType.CREDIT_COMPONENT,
                        },
                        priority=10,  # High priority
                    )
                    registered_count += 1
                except Exception as e:
                    logger.debug(f"Could not register meta_learner: {e}")
            
            # Gradient Bridge - processes all outcomes for credit attribution
            if self._gradient_bridge_service:
                try:
                    async def gradient_bridge_handler(signal):
                        if hasattr(self._gradient_bridge_service, 'on_learning_signal'):
                            await self._gradient_bridge_service.on_learning_signal(signal)
                    
                    self._unified_learning_hub.register_component(
                        name="gradient_bridge",
                        handler=gradient_bridge_handler,
                        signal_types={
                            UnifiedSignalType.OUTCOME_SUCCESS,
                            UnifiedSignalType.OUTCOME_FAILURE,
                            UnifiedSignalType.OUTCOME_ENGAGEMENT,
                            UnifiedSignalType.CREDIT_MECHANISM,
                            UnifiedSignalType.CREDIT_ATOM,
                        },
                        priority=15,  # Highest priority - does attribution
                    )
                    registered_count += 1
                except Exception as e:
                    logger.debug(f"Could not register gradient_bridge: {e}")
            
            # Blackboard Zone 5 - learning zone aggregation
            if self._blackboard_service:
                try:
                    # Capture reference for closure
                    blackboard_svc = self._blackboard_service
                    
                    async def blackboard_learning_handler(signal):
                        # Store signal in Zone 5 for attribution context
                        if hasattr(blackboard_svc, 'write_zone5_from_unified'):
                            await blackboard_svc.write_zone5_from_unified(signal)
                    
                    self._unified_learning_hub.register_component(
                        name="blackboard_zone5",
                        handler=blackboard_learning_handler,
                        signal_types={
                            UnifiedSignalType.CREDIT_MECHANISM,
                            UnifiedSignalType.CREDIT_ATOM,
                            UnifiedSignalType.PATTERN_DISCOVERED,
                            UnifiedSignalType.CONSTRUCT_EMERGED,
                        },
                        priority=5,  # Lower priority - for logging/tracking
                    )
                    registered_count += 1
                except Exception as e:
                    logger.debug(f"Could not register blackboard_zone5: {e}")
            
            # V3 Emergence Engine - receives pattern discovery signals
            if self._v3_emergence:
                try:
                    async def emergence_handler(signal):
                        if hasattr(self._v3_emergence, 'on_learning_signal'):
                            await self._v3_emergence.on_learning_signal(signal)
                    
                    self._unified_learning_hub.register_component(
                        name="v3_emergence",
                        handler=emergence_handler,
                        signal_types={
                            UnifiedSignalType.PATTERN_DISCOVERED,
                            UnifiedSignalType.CONSTRUCT_EMERGED,
                            UnifiedSignalType.CALIBRATION_NEEDED,
                        },
                        priority=5,
                    )
                    registered_count += 1
                except Exception as e:
                    logger.debug(f"Could not register v3_emergence: {e}")
            
            # Behavioral Analytics - receives behavioral outcome signals
            if self._behavioral_analytics_engine:
                try:
                    async def behavioral_handler(signal):
                        if hasattr(self._behavioral_analytics_engine, 'on_learning_signal'):
                            await self._behavioral_analytics_engine.on_learning_signal(signal)
                    
                    self._unified_learning_hub.register_component(
                        name="behavioral_analytics",
                        handler=behavioral_handler,
                        signal_types={
                            UnifiedSignalType.OUTCOME_SUCCESS,
                            UnifiedSignalType.OUTCOME_ENGAGEMENT,
                            UnifiedSignalType.PATTERN_DISCOVERED,
                        },
                        priority=3,
                    )
                    registered_count += 1
                except Exception as e:
                    logger.debug(f"Could not register behavioral_analytics: {e}")
            
            # Store reference to learning hub for other components
            self._learning_signal_router = self._unified_learning_hub  # Alias for compatibility
            
            logger.info(f"UnifiedLearningHub initialized with {registered_count} components registered")
            
            # Connect Review Intelligence Bridge to learning hub
            await self._init_review_intelligence_bridge()
            
        except Exception as e:
            logger.warning(f"Learning signal routing initialization failed: {e}")
            import traceback
            traceback.print_exc()
            # Non-fatal - system can still function without learning routing
    
    async def _init_review_intelligence_bridge(self) -> None:
        """
        Initialize Review Intelligence Bridge and connect to learning loop.
        
        This enables:
        - Cookie-less psychological targeting from review data
        - Bidirectional learning with UnifiedLearningHub
        - Integration with Neo4j, LangGraph, and AoT
        """
        try:
            from adam.intelligence.review_intelligence.orchestrator import (
                ReviewIntelligenceOrchestrator,
            )
            from adam.intelligence.review_intelligence.machine_integration import (
                ReviewIntelligenceMachineBridge,
            )
            from pathlib import Path
            
            # Get review data root from settings or use default
            review_data_root = getattr(
                self.settings, 'REVIEW_DATA_ROOT',
                Path("/Volumes/Sped/Nocera Models/Review Data")
            )
            
            if review_data_root.exists():
                # Initialize orchestrator
                orchestrator = ReviewIntelligenceOrchestrator(
                    data_root=review_data_root,
                )
                
                # Create bridge with Neo4j driver
                self._review_intelligence_bridge = ReviewIntelligenceMachineBridge(
                    orchestrator=orchestrator,
                    neo4j_driver=self._neo4j_driver,
                )
                
                # Connect to learning hub for bidirectional learning
                await self._review_intelligence_bridge.connect_to_learning_hub()
                
                logger.info("Review Intelligence Bridge initialized and connected to learning loop")
            else:
                logger.debug(f"Review data root not found: {review_data_root}")
                
        except Exception as e:
            logger.debug(f"Review Intelligence Bridge not initialized: {e}")
            # Non-fatal - system can function without review intelligence
    
    async def shutdown(self) -> None:
        """Clean shutdown of all components."""
        logger.info("Shutting down ADAM Container...")
        
        # Stop learning signal router
        if hasattr(self, '_learning_signal_router') and self._learning_signal_router:
            try:
                await self._learning_signal_router.stop()
                logger.info("Learning signal router stopped")
            except Exception as e:
                logger.warning(f"Error stopping learning signal router: {e}")
        
        # Stop bidirectional bridge
        if hasattr(self, '_bidirectional_bridge') and self._bidirectional_bridge:
            try:
                await self._bidirectional_bridge.stop()
                logger.info("Bidirectional bridge stopped")
            except Exception as e:
                logger.warning(f"Error stopping bidirectional bridge: {e}")
        
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
    
    @property
    def neural_thompson_engine(self):
        """
        Get Neural Thompson Sampling Engine.
        
        Advanced context-aware exploration-exploitation using:
        - Neural networks for context encoding
        - Bootstrap heads for epistemic uncertainty
        - Learned exploration bonuses
        """
        try:
            from adam.meta_learner.neural_thompson import get_neural_thompson_engine
            return get_neural_thompson_engine()
        except Exception:
            return None
    
    @property
    def predictive_processing_engine(self):
        """
        Get Predictive Processing Engine.
        
        Free energy-based optimization for:
        - Active inference (curiosity-driven exploration)
        - Prediction error minimization
        - Epistemic/pragmatic value balancing
        """
        try:
            from adam.intelligence.predictive_processing import get_predictive_processing_engine
            return get_predictive_processing_engine()
        except Exception:
            return None
    
    # =========================================================================
    # BEHAVIORAL ANALYTICS ACCESSORS
    # =========================================================================
    
    @property
    def workflow_executor(self):
        """
        Get the Holistic Decision Workflow Executor.
        
        This is the main entry point for making ad decisions via LangGraph.
        Returns None if workflow initialization failed.
        """
        return self._workflow_executor
    
    @property
    def learning_signal_router(self):
        """Get the Learning Signal Router for propagating learning signals."""
        return getattr(self, '_learning_signal_router', None)
    
    @property
    def bidirectional_bridge(self):
        """
        Get the Bidirectional Bridge for Graph-AoT communication.
        
        This enables:
        - Decision persistence to the graph
        - Learning path creation for outcome attribution
        - Conflict resolution between graph and LLM
        - Tiered update routing (immediate/async/batch)
        """
        return getattr(self, '_bidirectional_bridge', None)
    
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
