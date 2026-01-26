# =============================================================================
# ADAM Temporal Module
# =============================================================================

"""
ADAM Temporal Intelligence

Components for temporal pattern learning and state trajectory modeling.

This implements Intelligence Source #8:
- Temporal and Contextual Pattern Intelligence
- State trajectory modeling
- Timing prediction and validation
"""

from adam.temporal.learning_integration import (
    TemporalLearningBridge,
    LifeEventType,
    DecisionStage,
    TimingPrediction,
    TimingEffectiveness,
)

from adam.temporal.state_trajectory import (
    StateTrajectoryModeler,
    StateVector,
    StateMomentum,
    StateTrajectory,
    TrajectoryType,
    TrajectoryPrediction,
)

__all__ = [
    # Learning Integration
    "TemporalLearningBridge",
    "LifeEventType",
    "DecisionStage",
    "TimingPrediction",
    "TimingEffectiveness",
    # State Trajectory
    "StateTrajectoryModeler",
    "StateVector",
    "StateMomentum",
    "StateTrajectory",
    "TrajectoryType",
    "TrajectoryPrediction",
]
