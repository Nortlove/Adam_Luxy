# =============================================================================
# ADAM Behavioral Analytics: Classifiers Module
# Location: adam/behavioral_analytics/classifiers/__init__.py
# =============================================================================

"""
BEHAVIORAL CLASSIFIERS

Research-grounded classifiers for inferring psychological states
from behavioral signals.

13 Classifiers (Phase 6: Full Intelligence Utilization):

Core Classifiers:
- PurchaseIntentClassifier: Predicts purchase probability (F1: 0.86-0.89)
- EmotionalStateClassifier: Classifies arousal/valence (70-89% accuracy)
- CognitiveLoadEstimator: Estimates cognitive load (0-1)
- DecisionConfidenceAnalyzer: Analyzes decision confidence (d=1.65-1.80)
- PersonalityInferencer: Infers Big Five from media preferences (r=0.30-0.44)
- AdvertisingEffectivenessPredictor: Predicts ad effectiveness

Advanced Classifiers:
- EvolutionaryMotiveDetector: Detects evolutionary motives (status, mating, etc.)
- MoralFoundationsDetector: Detects moral foundations (care, fairness, etc.)
- MemoryOptimizer: Optimizes for memory retention (spacing, emotional valence)
- ApproachAvoidanceDetector: Detects approach/avoidance motivation
- TemporalTargetingClassifier: Optimal timing based on circadian rhythms
- CognitiveStateEstimator: Estimates cognitive capacity and chronotype
- RegulatoryFocusDetector: Detects promotion vs prevention focus
"""

# Core Classifiers
from adam.behavioral_analytics.classifiers.purchase_intent import (
    PurchaseIntentClassifier,
    get_purchase_intent_classifier,
)
from adam.behavioral_analytics.classifiers.emotional_state import (
    EmotionalStateClassifier,
    get_emotional_state_classifier,
)
from adam.behavioral_analytics.classifiers.cognitive_load import (
    CognitiveLoadEstimator,
    get_cognitive_load_estimator,
)
from adam.behavioral_analytics.classifiers.decision_confidence import (
    DecisionConfidenceAnalyzer,
    get_decision_confidence_analyzer,
)
from adam.behavioral_analytics.classifiers.personality_inferencer import (
    PersonalityInferencer,
    BigFiveProfile,
    get_personality_inferencer,
)
from adam.behavioral_analytics.classifiers.advertising_effectiveness import (
    AdvertisingEffectivenessPredictor,
    get_advertising_effectiveness_predictor,
)

# Advanced Classifiers (Phase 6: Previously unwired)
from adam.behavioral_analytics.classifiers.evolutionary_motive_detector import (
    EvolutionaryMotiveDetector,
    get_evolutionary_motive_detector,
)
from adam.behavioral_analytics.classifiers.moral_foundations_targeting import (
    MoralFoundationsDetector,
    get_moral_foundations_detector,
)
from adam.behavioral_analytics.classifiers.memory_optimizer import (
    MemoryOptimizer,
    get_memory_optimizer,
)
from adam.behavioral_analytics.classifiers.approach_avoidance_detector import (
    ApproachAvoidanceDetector,
    get_approach_avoidance_detector,
)
from adam.behavioral_analytics.classifiers.temporal_targeting import (
    TemporalTargetingClassifier,
    get_temporal_targeting_classifier,
)
from adam.behavioral_analytics.classifiers.cognitive_state_estimator import (
    CognitiveStateEstimator,
    get_cognitive_state_estimator,
)
from adam.behavioral_analytics.classifiers.regulatory_focus_detector import (
    RegulatoryFocusDetector,
    get_regulatory_focus_detector,
)

__all__ = [
    # Core Classifiers
    "PurchaseIntentClassifier",
    "get_purchase_intent_classifier",
    "EmotionalStateClassifier",
    "get_emotional_state_classifier",
    "CognitiveLoadEstimator",
    "get_cognitive_load_estimator",
    "DecisionConfidenceAnalyzer",
    "get_decision_confidence_analyzer",
    "PersonalityInferencer",
    "BigFiveProfile",
    "get_personality_inferencer",
    "AdvertisingEffectivenessPredictor",
    "get_advertising_effectiveness_predictor",
    # Advanced Classifiers (Phase 6)
    "EvolutionaryMotiveDetector",
    "get_evolutionary_motive_detector",
    "MoralFoundationsDetector",
    "get_moral_foundations_detector",
    "MemoryOptimizer",
    "get_memory_optimizer",
    "ApproachAvoidanceDetector",
    "get_approach_avoidance_detector",
    "TemporalTargetingClassifier",
    "get_temporal_targeting_classifier",
    "CognitiveStateEstimator",
    "get_cognitive_state_estimator",
    "RegulatoryFocusDetector",
    "get_regulatory_focus_detector",
]
