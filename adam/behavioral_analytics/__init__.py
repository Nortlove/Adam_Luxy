# =============================================================================
# ADAM Behavioral Analytics Module
# Location: adam/behavioral_analytics/__init__.py
# =============================================================================

"""
BEHAVIORAL ANALYTICS & KNOWLEDGE DISCOVERY SYSTEM

A comprehensive analytics and knowledge discovery system that:
1. Captures both explicit (clicks, conversions) and implicit (touch, swipe, latency) signals
2. Tests hypotheses about signal-outcome relationships for statistical significance
3. Promotes validated patterns into system-wide knowledge when significant
4. Embeds research findings (150+ studies) as foundational knowledge
5. Continuously refines knowledge through outcome-based learning

Key Components:
- BehavioralAnalyticsEngine: Main orchestrator for session processing and inference
- HypothesisEngine: Tests and validates signal-outcome relationships
- ResearchKnowledgeSeeder: Seeds 150+ research-validated knowledge items
- AtomKnowledgeInterface: Interface for Atom of Thought integration
- BehavioralDriftDetector: Monitors behavioral signal distributions

Extensions to Existing Infrastructure:
- Multimodal Fusion (#16): Adds behavioral sub-modalities
- Drift Detection (#20): Adds behavioral drift types
- Caching (#31): Uses BEHAVIORAL cache domain
- Gradient Bridge (#06): Forwards outcomes for learning
- Meta-Learner (#03): Routes behavioral requests
- Verification (#11): Validates behavioral hypotheses
"""

# Core models
from adam.behavioral_analytics.models.events import (
    BehavioralSession,
    BehavioralOutcome,
    OutcomeType,
    TouchEvent,
    SwipeEvent,
    ScrollEvent,
    SensorSample,
    PageViewEvent,
    ClickEvent,
    CartEvent,
    PurchaseEvent,
    AdEvent,
    HesitationEvent,
    RageClickEvent,
    EventType,
    SwipeDirection,
    DeviceType,
    SessionPhase,
)

from adam.behavioral_analytics.models.knowledge import (
    BehavioralKnowledge,
    BehavioralHypothesis,
    KnowledgeValidationEvent,
    KnowledgeType,
    KnowledgeStatus,
    HypothesisStatus,
    EffectType,
    SignalCategory,
    KnowledgeTier,
    ResearchSource,
)

# Knowledge components
from adam.behavioral_analytics.knowledge.research_seeder import (
    ResearchKnowledgeSeeder,
    get_research_knowledge_seeder,
    create_tier1_knowledge,
    create_tier2_knowledge,
    create_personality_knowledge,
)

from adam.behavioral_analytics.knowledge.graph_integration import (
    BehavioralKnowledgeGraph,
    get_behavioral_knowledge_graph,
    seed_research_knowledge,
)

from adam.behavioral_analytics.knowledge.hypothesis_engine import (
    HypothesisEngine,
    get_hypothesis_engine,
    StatisticalTest,
)

# Main engine
from adam.behavioral_analytics.engine import (
    BehavioralAnalyticsEngine,
    PsychologicalInference,
    get_behavioral_analytics_engine,
)

# Atom integration
from adam.behavioral_analytics.atom_interface import (
    AtomKnowledgeInterface,
    AtomBehavioralContext,
    get_atom_knowledge_interface,
    enhance_regulatory_focus_atom,
    enhance_construal_level_atom,
)

# Extensions
from adam.behavioral_analytics.extensions.multimodal_extension import (
    BehavioralModality,
    BehavioralSignalSource,
    BehavioralModalitySignal,
    BehavioralModalityWeights,
    BehavioralProfileContribution,
    extract_behavioral_signals,
)

from adam.behavioral_analytics.extensions.drift_extension import (
    BehavioralDriftType,
    BehavioralDriftDetector,
    get_behavioral_drift_detector,
)

from adam.behavioral_analytics.extensions.cache_extension import (
    BehavioralCache,
    BehavioralCacheKeyBuilder,
    BehavioralCacheDomain,
    get_behavioral_cache,
)

# Gradient Bridge Integration (properly integrates with existing architecture)
from adam.behavioral_analytics.integration import (
    BehavioralGradientBridgeIntegration,
    get_behavioral_gradient_bridge_integration,
)

# Classifiers
from adam.behavioral_analytics.classifiers import (
    PurchaseIntentClassifier,
    get_purchase_intent_classifier,
    EmotionalStateClassifier,
    get_emotional_state_classifier,
    CognitiveLoadEstimator,
    get_cognitive_load_estimator,
    DecisionConfidenceAnalyzer,
    get_decision_confidence_analyzer,
)

# Knowledge Promoter
from adam.behavioral_analytics.knowledge.promoter import (
    KnowledgePromoter,
    PromotionCriteria,
    get_knowledge_promoter,
)

# Workflow Nodes
from adam.behavioral_analytics.workflow_nodes import (
    collect_implicit_signals,
    infer_psychological_state,
    query_behavioral_knowledge,
    record_for_hypothesis_testing,
    apply_behavioral_context,
    build_behavioral_workflow_nodes,
    enhance_workflow_state,
)

# Learning is now handled through proper Gradient Bridge integration
# See adam.behavioral_analytics.integration.gradient_bridge_integration


__all__ = [
    # Core session/event models
    "BehavioralSession",
    "BehavioralOutcome",
    "OutcomeType",
    "TouchEvent",
    "SwipeEvent",
    "ScrollEvent",
    "SensorSample",
    "PageViewEvent",
    "ClickEvent",
    "CartEvent",
    "PurchaseEvent",
    "AdEvent",
    "HesitationEvent",
    "RageClickEvent",
    "EventType",
    "SwipeDirection",
    "DeviceType",
    "SessionPhase",
    
    # Knowledge models
    "BehavioralKnowledge",
    "BehavioralHypothesis",
    "KnowledgeValidationEvent",
    "KnowledgeType",
    "KnowledgeStatus",
    "HypothesisStatus",
    "EffectType",
    "SignalCategory",
    "KnowledgeTier",
    "ResearchSource",
    
    # Knowledge seeder
    "ResearchKnowledgeSeeder",
    "get_research_knowledge_seeder",
    "create_tier1_knowledge",
    "create_tier2_knowledge",
    "create_personality_knowledge",
    
    # Graph integration
    "BehavioralKnowledgeGraph",
    "get_behavioral_knowledge_graph",
    "seed_research_knowledge",
    
    # Hypothesis engine
    "HypothesisEngine",
    "get_hypothesis_engine",
    "StatisticalTest",
    
    # Main engine
    "BehavioralAnalyticsEngine",
    "PsychologicalInference",
    "get_behavioral_analytics_engine",
    
    # Atom integration
    "AtomKnowledgeInterface",
    "AtomBehavioralContext",
    "get_atom_knowledge_interface",
    "enhance_regulatory_focus_atom",
    "enhance_construal_level_atom",
    
    # Multimodal extension
    "BehavioralModality",
    "BehavioralSignalSource",
    "BehavioralModalitySignal",
    "BehavioralModalityWeights",
    "BehavioralProfileContribution",
    "extract_behavioral_signals",
    
    # Drift extension
    "BehavioralDriftType",
    "BehavioralDriftDetector",
    "get_behavioral_drift_detector",
    
    # Cache extension
    "BehavioralCache",
    "BehavioralCacheKeyBuilder",
    "BehavioralCacheDomain",
    "get_behavioral_cache",
    
    # Gradient Bridge Integration (proper architecture integration)
    "BehavioralGradientBridgeIntegration",
    "get_behavioral_gradient_bridge_integration",
    
    # Classifiers
    "PurchaseIntentClassifier",
    "get_purchase_intent_classifier",
    "EmotionalStateClassifier",
    "get_emotional_state_classifier",
    "CognitiveLoadEstimator",
    "get_cognitive_load_estimator",
    "DecisionConfidenceAnalyzer",
    "get_decision_confidence_analyzer",
    
    # Knowledge promoter
    "KnowledgePromoter",
    "PromotionCriteria",
    "get_knowledge_promoter",
    
    # Workflow nodes
    "collect_implicit_signals",
    "infer_psychological_state",
    "query_behavioral_knowledge",
    "record_for_hypothesis_testing",
    "apply_behavioral_context",
    "build_behavioral_workflow_nodes",
    "enhance_workflow_state",
    
]
