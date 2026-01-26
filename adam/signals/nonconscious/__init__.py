# =============================================================================
# ADAM Nonconscious Analytics Module
# =============================================================================

"""
NONCONSCIOUS ANALYTICS

Research-backed implicit signal processing for persuasion optimization.

This module captures and analyzes signals that operate below conscious awareness,
providing insights into pre-conscious processing, automatic evaluations, and
implicit preferences.

Key Research Foundations:
- Unconscious Thought Theory (Dijksterhuis & Nordgren, 2006)
- Dual Process Theory / System 1 (Kahneman, 2011)
- Elaboration Likelihood Model (Petty & Cacioppo, 1986)
- Mere Exposure Effect (Zajonc, 1980)
- Somatic Marker Hypothesis (Damasio, 1994)

Signal Categories:
1. Kinematic Signals - Mouse, scroll, touch dynamics
2. Temporal Signals - Response latency, dwell time
3. Rhythmic Signals - Session patterns, engagement cadence
4. Physiological Proxies - Hesitation, correction, acceleration
"""

from adam.signals.nonconscious.models import (
    # Core signal types
    NonconsciousSignal,
    KinematicSignal,
    TemporalSignal,
    RhythmicSignal,
    HesitationSignal,
    
    # Aggregated constructs
    ApproachAvoidanceTendency,
    CognitiveLoadIndicator,
    EmotionalValenceProxy,
    ProcessingFluencyScore,
    EngagementIntensity,
    
    # Inference results
    NonconsciousProfile,
    ImplicitPreference,
    AutomaticEvaluation,
)

from adam.signals.nonconscious.capture import (
    NonconsciousSignalCapture,
    MouseDynamicsCapture,
    ScrollBehaviorCapture,
    KeystrokeDynamicsCapture,
    ResponseLatencyCapture,
)

from adam.signals.nonconscious.analysis import (
    NonconsciousAnalyzer,
    ApproachAvoidanceAnalyzer,
    CognitiveLoadEstimator,
    ProcessingFluencyAnalyzer,
    ImplicitPreferenceInference,
)

from adam.signals.nonconscious.service import NonconsciousAnalyticsService

__all__ = [
    # Service
    "NonconsciousAnalyticsService",
    
    # Capture
    "NonconsciousSignalCapture",
    "MouseDynamicsCapture",
    "ScrollBehaviorCapture",
    "KeystrokeDynamicsCapture",
    "ResponseLatencyCapture",
    
    # Analysis
    "NonconsciousAnalyzer",
    "ApproachAvoidanceAnalyzer",
    "CognitiveLoadEstimator",
    "ProcessingFluencyAnalyzer",
    "ImplicitPreferenceInference",
    
    # Models
    "NonconsciousSignal",
    "KinematicSignal",
    "TemporalSignal",
    "RhythmicSignal",
    "HesitationSignal",
    "ApproachAvoidanceTendency",
    "CognitiveLoadIndicator",
    "EmotionalValenceProxy",
    "ProcessingFluencyScore",
    "EngagementIntensity",
    "NonconsciousProfile",
    "ImplicitPreference",
    "AutomaticEvaluation",
]
