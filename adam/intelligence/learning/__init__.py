# =============================================================================
# Intelligence Learning Module
# Location: adam/intelligence/learning/__init__.py
# =============================================================================

"""
Deep Learning Integrations for Psychological Intelligence

This module provides deep learning capabilities for all psychological
intelligence components, ensuring they fully participate in the
universal learning architecture.

Components:
- UnifiedPsychologicalIntelligenceLearning
- ReviewAnalyzerLearning
- FlowStateLearning
- NeedDetectionLearning

Usage:
    from adam.intelligence.learning import (
        create_unified_intelligence_learning,
        create_flow_state_learning,
        create_need_detection_learning,
    )
"""

from adam.intelligence.learning.psychological_learning_integration import (
    # Learning integrations
    UnifiedPsychologicalIntelligenceLearning,
    ReviewAnalyzerLearning,
    FlowStateLearning,
    NeedDetectionLearning,
    # Signal types
    PsychologicalLearningSignalType,
    # Factories
    create_unified_intelligence_learning,
    create_flow_state_learning,
    create_need_detection_learning,
)

__all__ = [
    # Learning integrations
    "UnifiedPsychologicalIntelligenceLearning",
    "ReviewAnalyzerLearning",
    "FlowStateLearning",
    "NeedDetectionLearning",
    # Signal types
    "PsychologicalLearningSignalType",
    # Factories
    "create_unified_intelligence_learning",
    "create_flow_state_learning",
    "create_need_detection_learning",
]
