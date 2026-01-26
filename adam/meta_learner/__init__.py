# =============================================================================
# ADAM Meta-Learning Orchestration (#03)
# =============================================================================

"""
META-LEARNING ORCHESTRATION

The Meta-Learner is the first substantive routing decision in ADAM's workflow.
It determines which learning modality and execution path to use.

8 Learning Modalities:
- SUPERVISED_CONVERSION: High-data users with conversion history
- SUPERVISED_ENGAGEMENT: High-data users with engagement history
- UNSUPERVISED_CLUSTERING: Users similar to known clusters
- UNSUPERVISED_GRAPH_EMBEDDING: Users with rich graph connections
- REINFORCEMENT_BANDIT: New users, uncertain contexts
- REINFORCEMENT_CONTEXTUAL_BANDIT: Some data, varied contexts
- CAUSAL_INFERENCE: A/B test contexts, attribution needs
- SELF_SUPERVISED_CONTRASTIVE: Cold-start, no labels

3 Execution Paths:
- FAST_PATH: <50ms, cache/graph lookup
- REASONING_PATH: 500ms-2s, full Claude + atoms
- EXPLORATION_PATH: <100ms, bandit exploration

Uses Thompson Sampling for explore/exploit balance.
"""

from adam.meta_learner.models import (
    LearningModality,
    ExecutionPath,
    ModalityPosterior,
    ContextFeatures,
    RoutingDecision,
    ModalityConstraint,
    MODALITY_TO_PATH,
)
from adam.meta_learner.thompson import ThompsonSamplingEngine
from adam.meta_learner.service import MetaLearnerService

__all__ = [
    # Models
    "LearningModality",
    "ExecutionPath",
    "ModalityPosterior",
    "ContextFeatures",
    "RoutingDecision",
    "ModalityConstraint",
    "MODALITY_TO_PATH",
    # Engine
    "ThompsonSamplingEngine",
    # Service
    "MetaLearnerService",
]
