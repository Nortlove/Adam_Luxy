# =============================================================================
# ADAM Signals Module
# =============================================================================

"""
ADAM SIGNALS

Multi-channel signal processing for behavioral understanding.

This module provides:
1. Nonconscious Analytics - Implicit behavioral signal capture and analysis
2. Supraliminal Signals - Explicit behavioral signals
3. Signal Fusion - Combining conscious and nonconscious signals

Key Components:
- NonconsciousAnalyticsService: Captures mouse, scroll, keystroke, timing
- SignalProcessor: Transforms raw events into typed signals
- SignalAggregator: Combines signals into profiles
"""

from adam.signals.nonconscious import (
    # Service
    NonconsciousAnalyticsService,
    
    # Capture
    NonconsciousSignalCapture,
    MouseDynamicsCapture,
    ScrollBehaviorCapture,
    KeystrokeDynamicsCapture,
    ResponseLatencyCapture,
    
    # Analysis
    NonconsciousAnalyzer,
    ApproachAvoidanceAnalyzer,
    CognitiveLoadEstimator,
    ProcessingFluencyAnalyzer,
    ImplicitPreferenceInference,
    
    # Models
    NonconsciousSignal,
    KinematicSignal,
    TemporalSignal,
    RhythmicSignal,
    HesitationSignal,
    ApproachAvoidanceTendency,
    CognitiveLoadIndicator,
    EmotionalValenceProxy,
    ProcessingFluencyScore,
    EngagementIntensity,
    NonconsciousProfile,
    ImplicitPreference,
    AutomaticEvaluation,
)

__all__ = [
    # Nonconscious Service
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