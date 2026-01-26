# =============================================================================
# ADAM Behavioral Analytics: Classifiers Module
# Location: adam/behavioral_analytics/classifiers/__init__.py
# =============================================================================

"""
BEHAVIORAL CLASSIFIERS

Research-grounded classifiers for inferring psychological states
from behavioral signals.

Classifiers:
- PurchaseIntentClassifier: Predicts purchase probability (F1: 0.86-0.89)
- EmotionalStateClassifier: Classifies arousal/valence (70-89% accuracy)
- CognitiveLoadEstimator: Estimates cognitive load (0-1)
- DecisionConfidenceAnalyzer: Analyzes decision confidence (d=1.65-1.80)
- PersonalityInferencer: Infers Big Five from media preferences (r=0.30-0.44)
"""

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

__all__ = [
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
    # Advertising effectiveness
    "AdvertisingEffectivenessPredictor",
    "get_advertising_effectiveness_predictor",
]
