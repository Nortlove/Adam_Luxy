# =============================================================================
# Intelligence Learning Module
# Location: adam/intelligence/learning/__init__.py
# =============================================================================

"""
Deep Learning Integrations for Psychological Intelligence
(OFFLINE-SCRIPT-ONLY ROLE — see below)

ROLE PER G1 LANDSCAPE DOC: scoped to offline corpus-learning scripts.
Audit 2026-04-27 confirmed ZERO production runtime consumers — used
exclusively by batch scripts (run_deep_prelearning, run_full_corpus_
learning, run_comprehensive_deep_learning, run_multi_source_learning,
ingest_multi_source_reviews). NOT a runtime path.

For new learning code:
  - Production runtime: adam.core.learning (CANONICAL)
  - Convenience aggregator: adam.learning
  - Cold-start gradient bridge: adam.cold_start.learning

If you find yourself wanting to add code here for a runtime use case,
move it to adam.core.learning instead. This package's lifecycle is
batch / offline only.

See adam/core/learning/__init__.py for the full four-package
landscape documentation.

This module provides deep learning capabilities for psychological
intelligence components participating in the universal learning
architecture from the offline / corpus-learning side.

Components:
- UnifiedPsychologicalIntelligenceLearning
- ReviewAnalyzerLearning
- FlowStateLearning
- NeedDetectionLearning

Usage (offline scripts only):
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
