# =============================================================================
# ADAM Atom Orchestration
# =============================================================================

"""
Atom Orchestration - LangGraph ↔ AoT Interface

This module provides the bridge between LangGraph workflows and
the Atom of Thought (AoT) reasoning system.

Key Components:
- DAGExecutorWithPriors: Enhanced executor with LangGraph intelligence injection
- LangGraphAtomFeedback: Bidirectional feedback for learning
- get_dag_executor(): Singleton access to the executor
"""

from adam.atoms.orchestration.dag_executor import (
    DAGExecutorWithPriors,
    get_dag_executor,
    PriorContext,
    AtomFeedback,
    FeedbackType,
)
from adam.atoms.orchestration.langgraph_feedback import (
    LangGraphAtomFeedback,
    get_feedback_interface,
    AtomLearningSignal,
    LangGraphLearningSignal,
)

__all__ = [
    # Executor
    "DAGExecutorWithPriors",
    "get_dag_executor",
    "PriorContext",
    "AtomFeedback",
    "FeedbackType",
    # Feedback
    "LangGraphAtomFeedback",
    "get_feedback_interface",
    "AtomLearningSignal",
    "LangGraphLearningSignal",
]
