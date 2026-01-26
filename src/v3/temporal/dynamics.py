# =============================================================================
# ADAM v3: Temporal Dynamics Engine
# Location: src/v3/temporal/dynamics.py
# =============================================================================

"""
TEMPORAL DYNAMICS ENGINE

Models how psychological states evolve over time.

Key capabilities:
- State trajectory modeling
- Phase transition detection
- Momentum analysis
- Future state prediction
- Optimal intervention timing
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field
import logging
import uuid
import numpy as np
from collections import deque

logger = logging.getLogger(__name__)


class TemporalPhase(str, Enum):
    """Phases of psychological state evolution."""
    STABLE = "stable"               # Minimal change
    TRANSITIONING = "transitioning" # Moving between states
    OSCILLATING = "oscillating"     # Fluctuating
    TRENDING_UP = "trending_up"     # Consistent increase
    TRENDING_DOWN = "trending_down" # Consistent decrease
    CHAOTIC = "chaotic"             # Unpredictable changes


class StateTrajectory(BaseModel):
    """Trajectory of a psychological state over time."""
    
    trajectory_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    state_name: str
    user_id: str
    
    # Time series data
    timestamps: List[datetime] = Field(default_factory=list)
    values: List[float] = Field(default_factory=list)
    
    # Derived metrics
    current_value: float = 0.0
    velocity: float = 0.0          # Rate of change
    acceleration: float = 0.0       # Change in velocity
    momentum: float = 0.0           # Persistence of direction
    
    # Phase
    current_phase: TemporalPhase = TemporalPhase.STABLE
    phase_duration_minutes: float = 0.0
    
    # Predictions
    predicted_next: Optional[float] = None
    prediction_confidence: float = 0.0
    
    def add_observation(self, timestamp: datetime, value: float) -> None:
        """Add a new observation to the trajectory."""
        self.timestamps.append(timestamp)
        self.values.append(value)
        self.current_value = value
        
        if len(self.values) >= 2:
            self._update_dynamics()
    
    def _update_dynamics(self) -> None:
        """Update derived dynamics metrics."""
        if len(self.values) < 2:
            return
        
        # Velocity (recent change rate)
        recent = self.values[-5:] if len(self.values) >= 5 else self.values
        if len(recent) >= 2:
            self.velocity = (recent[-1] - recent[0]) / len(recent)
        
        # Acceleration (change in velocity)
        if len(self.values) >= 3:
            v1 = self.values[-2] - self.values[-3]
            v2 = self.values[-1] - self.values[-2]
            self.acceleration = v2 - v1
        
        # Momentum (consistency of direction)
        if len(self.values) >= 5:
            changes = [self.values[i] - self.values[i-1] for i in range(1, len(self.values))]
            positive_changes = sum(1 for c in changes[-5:] if c > 0)
            self.momentum = (positive_changes / 5) * 2 - 1  # -1 to 1


class PhaseTransition(BaseModel):
    """A detected phase transition."""
    
    transition_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    trajectory_id: str
    
    from_phase: TemporalPhase
    to_phase: TemporalPhase
    transition_time: datetime = Field(default_factory=datetime.utcnow)
    
    # Metrics
    velocity_at_transition: float = 0.0
    acceleration_at_transition: float = 0.0
    
    # Context
    trigger_signals: List[str] = Field(default_factory=list)
    confidence: float = 0.5


class InterventionWindow(BaseModel):
    """Optimal timing window for intervention."""
    
    window_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    trajectory_id: str
    
    # Timing
    start_time: datetime
    end_time: datetime
    optimal_time: datetime
    
    # Why this window
    reason: str
    
    # Expected impact
    expected_lift: float = 0.0
    confidence: float = 0.5


class TemporalDynamicsEngine:
    """
    Models temporal evolution of psychological states.
    
    Tracks:
    - State trajectories for users
    - Phase transitions
    - Intervention opportunities
    - Future predictions
    """
    
    # Phase detection thresholds
    STABLE_THRESHOLD = 0.02
    TRENDING_THRESHOLD = 0.05
    OSCILLATION_THRESHOLD = 3  # sign changes
    
    # Prediction horizon
    PREDICTION_HORIZON_MINUTES = 30
    
    def __init__(self):
        # Active trajectories by user
        self._trajectories: Dict[str, Dict[str, StateTrajectory]] = {}
        
        # Transition history
        self._transitions: List[PhaseTransition] = []
        
        # Statistics
        self._observations = 0
        self._transitions_detected = 0
    
    async def record_observation(
        self,
        user_id: str,
        state_name: str,
        value: float,
        timestamp: Optional[datetime] = None
    ) -> StateTrajectory:
        """
        Record a state observation for a user.
        
        Args:
            user_id: User identifier
            state_name: Name of psychological state
            value: Observed value (0-1)
            timestamp: Observation time (defaults to now)
            
        Returns:
            Updated trajectory
        """
        timestamp = timestamp or datetime.utcnow()
        self._observations += 1
        
        # Get or create trajectory
        if user_id not in self._trajectories:
            self._trajectories[user_id] = {}
        
        if state_name not in self._trajectories[user_id]:
            self._trajectories[user_id][state_name] = StateTrajectory(
                state_name=state_name,
                user_id=user_id,
            )
        
        trajectory = self._trajectories[user_id][state_name]
        old_phase = trajectory.current_phase
        
        # Add observation
        trajectory.add_observation(timestamp, value)
        
        # Detect phase
        new_phase = self._detect_phase(trajectory)
        
        # Check for transition
        if new_phase != old_phase:
            transition = PhaseTransition(
                trajectory_id=trajectory.trajectory_id,
                from_phase=old_phase,
                to_phase=new_phase,
                transition_time=timestamp,
                velocity_at_transition=trajectory.velocity,
                acceleration_at_transition=trajectory.acceleration,
            )
            self._transitions.append(transition)
            self._transitions_detected += 1
            
            trajectory.current_phase = new_phase
            trajectory.phase_duration_minutes = 0.0
        else:
            # Update phase duration
            if len(trajectory.timestamps) >= 2:
                duration = (trajectory.timestamps[-1] - trajectory.timestamps[-2]).total_seconds() / 60
                trajectory.phase_duration_minutes += duration
        
        # Update prediction
        trajectory.predicted_next, trajectory.prediction_confidence = self._predict_next(trajectory)
        
        return trajectory
    
    def _detect_phase(self, trajectory: StateTrajectory) -> TemporalPhase:
        """Detect the current phase of a trajectory."""
        if len(trajectory.values) < 3:
            return TemporalPhase.STABLE
        
        recent = trajectory.values[-10:] if len(trajectory.values) >= 10 else trajectory.values
        
        # Check for stability
        std = np.std(recent)
        if std < self.STABLE_THRESHOLD:
            return TemporalPhase.STABLE
        
        # Check for trending
        velocity = trajectory.velocity
        if velocity > self.TRENDING_THRESHOLD:
            return TemporalPhase.TRENDING_UP
        elif velocity < -self.TRENDING_THRESHOLD:
            return TemporalPhase.TRENDING_DOWN
        
        # Check for oscillation
        changes = [recent[i] - recent[i-1] for i in range(1, len(recent))]
        sign_changes = sum(
            1 for i in range(1, len(changes))
            if changes[i] * changes[i-1] < 0
        )
        
        if sign_changes >= self.OSCILLATION_THRESHOLD:
            return TemporalPhase.OSCILLATING
        
        # Check for chaos (high variance, no pattern)
        if std > 0.2 and abs(velocity) < self.TRENDING_THRESHOLD:
            return TemporalPhase.CHAOTIC
        
        return TemporalPhase.TRANSITIONING
    
    def _predict_next(
        self,
        trajectory: StateTrajectory
    ) -> Tuple[Optional[float], float]:
        """Predict next value using simple momentum model."""
        if len(trajectory.values) < 3:
            return None, 0.0
        
        # Simple linear extrapolation with momentum adjustment
        current = trajectory.current_value
        velocity = trajectory.velocity
        momentum = trajectory.momentum
        
        # Predict based on velocity, dampened by momentum consistency
        momentum_factor = 0.5 + 0.5 * abs(momentum)
        predicted = current + velocity * momentum_factor
        
        # Clip to valid range
        predicted = max(0.0, min(1.0, predicted))
        
        # Confidence based on momentum and phase
        confidence = 0.3
        if trajectory.current_phase == TemporalPhase.STABLE:
            confidence = 0.8
        elif trajectory.current_phase in (TemporalPhase.TRENDING_UP, TemporalPhase.TRENDING_DOWN):
            confidence = 0.6
        
        confidence *= abs(momentum) + 0.5
        confidence = min(0.95, confidence)
        
        return predicted, confidence
    
    async def find_intervention_windows(
        self,
        user_id: str,
        target_state: str,
        lookahead_minutes: int = 60
    ) -> List[InterventionWindow]:
        """
        Find optimal intervention windows for a user.
        
        Args:
            user_id: User to analyze
            target_state: State to optimize
            lookahead_minutes: How far ahead to look
            
        Returns:
            List of intervention windows
        """
        if user_id not in self._trajectories:
            return []
        
        if target_state not in self._trajectories[user_id]:
            return []
        
        trajectory = self._trajectories[user_id][target_state]
        windows = []
        
        now = datetime.utcnow()
        
        # Optimal windows based on phase
        if trajectory.current_phase == TemporalPhase.TRANSITIONING:
            # Good time to intervene - state is in flux
            window = InterventionWindow(
                trajectory_id=trajectory.trajectory_id,
                start_time=now,
                end_time=now + timedelta(minutes=15),
                optimal_time=now + timedelta(minutes=5),
                reason="User is in transition - receptive to influence",
                expected_lift=0.15,
                confidence=0.7,
            )
            windows.append(window)
        
        elif trajectory.current_phase in (TemporalPhase.TRENDING_UP, TemporalPhase.TRENDING_DOWN):
            # Ride the momentum
            direction = "positive" if trajectory.current_phase == TemporalPhase.TRENDING_UP else "negative"
            window = InterventionWindow(
                trajectory_id=trajectory.trajectory_id,
                start_time=now,
                end_time=now + timedelta(minutes=30),
                optimal_time=now + timedelta(minutes=10),
                reason=f"User has {direction} momentum - amplify or redirect",
                expected_lift=0.12,
                confidence=0.6,
            )
            windows.append(window)
        
        elif trajectory.current_phase == TemporalPhase.STABLE:
            # Wait for change or trigger one
            window = InterventionWindow(
                trajectory_id=trajectory.trajectory_id,
                start_time=now + timedelta(minutes=30),
                end_time=now + timedelta(minutes=60),
                optimal_time=now + timedelta(minutes=45),
                reason="User is stable - requires disruption to change",
                expected_lift=0.08,
                confidence=0.5,
            )
            windows.append(window)
        
        return windows
    
    def get_user_dynamics(self, user_id: str) -> Dict[str, StateTrajectory]:
        """Get all trajectories for a user."""
        return self._trajectories.get(user_id, {})
    
    def get_recent_transitions(
        self,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[PhaseTransition]:
        """Get recent phase transitions."""
        transitions = self._transitions
        
        if user_id:
            user_trajectories = set(
                t.trajectory_id for t in self._trajectories.get(user_id, {}).values()
            )
            transitions = [t for t in transitions if t.trajectory_id in user_trajectories]
        
        return transitions[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "observations_recorded": self._observations,
            "users_tracked": len(self._trajectories),
            "active_trajectories": sum(
                len(states) for states in self._trajectories.values()
            ),
            "transitions_detected": self._transitions_detected,
        }


# Singleton instance
_engine: Optional[TemporalDynamicsEngine] = None


def get_temporal_dynamics_engine() -> TemporalDynamicsEngine:
    """Get singleton Temporal Dynamics Engine."""
    global _engine
    if _engine is None:
        _engine = TemporalDynamicsEngine()
    return _engine
