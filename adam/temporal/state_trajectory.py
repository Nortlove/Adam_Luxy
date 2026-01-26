# =============================================================================
# ADAM State Trajectory Modeling
# Location: adam/temporal/state_trajectory.py
# =============================================================================

"""
STATE TRAJECTORY MODELING

Models the evolution of user psychological states over time.

This implements Intelligence Source #8: Temporal and Contextual Pattern Intelligence
- Patterns that only emerge when you consider time
- "This user converts on Thursdays but not Mondays"
- "The effectiveness of social proof decays over repeated exposures"

Key capabilities:
1. State Vector Tracking - Track arousal, valence, regulatory focus over time
2. Trajectory Classification - Identify trajectory patterns (engaging, disengaging, cycling)
3. State Prediction - Predict future state based on trajectory
4. Momentum Calculation - Model state change velocity and acceleration
5. Session-to-Session Patterns - Track how states evolve across sessions

Reference: ADAM_EMERGENT_INTELLIGENCE_ARCHITECTURE.md - Source 8
"""

import logging
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from collections import deque
import math

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# MODELS
# =============================================================================

class TrajectoryType(str, Enum):
    """Classification of state trajectory patterns."""
    
    ENGAGING = "engaging"  # Arousal ↑, Valence ↑
    DISENGAGING = "disengaging"  # Arousal ↓, Valence ↓
    FRUSTRATED = "frustrated"  # Arousal ↑, Valence ↓
    CALMING = "calming"  # Arousal ↓, Valence ↑
    STABLE = "stable"  # Minimal change
    CYCLING = "cycling"  # Oscillating patterns
    ACCELERATING = "accelerating"  # Increasing rate of change
    DECELERATING = "decelerating"  # Decreasing rate of change


class StateVector(BaseModel):
    """A point in psychological state space."""
    
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Core state dimensions (0-1)
    arousal: float = Field(ge=0.0, le=1.0, default=0.5)
    valence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Regulatory dimensions (0-1)
    promotion_focus: float = Field(ge=0.0, le=1.0, default=0.5)
    prevention_focus: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Cognitive dimensions (0-1)
    construal_level: float = Field(ge=0.0, le=1.0, default=0.5)  # 0=concrete, 1=abstract
    cognitive_load: float = Field(ge=0.0, le=1.0, default=0.3)
    
    # Context
    session_id: Optional[str] = None
    trigger_event: Optional[str] = None
    
    def distance_to(self, other: "StateVector") -> float:
        """Euclidean distance to another state vector."""
        return math.sqrt(
            (self.arousal - other.arousal) ** 2 +
            (self.valence - other.valence) ** 2 +
            (self.promotion_focus - other.promotion_focus) ** 2 +
            (self.prevention_focus - other.prevention_focus) ** 2 +
            (self.construal_level - other.construal_level) ** 2 +
            (self.cognitive_load - other.cognitive_load) ** 2
        )
    
    def to_vector(self) -> List[float]:
        """Convert to numeric vector."""
        return [
            self.arousal,
            self.valence,
            self.promotion_focus,
            self.prevention_focus,
            self.construal_level,
            self.cognitive_load,
        ]


class StateMomentum(BaseModel):
    """First and second derivatives of state."""
    
    # Velocity (first derivative)
    arousal_velocity: float = 0.0
    valence_velocity: float = 0.0
    promotion_velocity: float = 0.0
    prevention_velocity: float = 0.0
    construal_velocity: float = 0.0
    load_velocity: float = 0.0
    
    # Acceleration (second derivative)
    arousal_acceleration: float = 0.0
    valence_acceleration: float = 0.0
    
    @property
    def overall_momentum(self) -> float:
        """Magnitude of overall momentum."""
        return math.sqrt(
            self.arousal_velocity ** 2 +
            self.valence_velocity ** 2
        )
    
    @property
    def momentum_direction(self) -> str:
        """Direction of momentum in arousal-valence space."""
        if abs(self.arousal_velocity) < 0.05 and abs(self.valence_velocity) < 0.05:
            return "stable"
        elif self.arousal_velocity > 0 and self.valence_velocity > 0:
            return "engaging"
        elif self.arousal_velocity < 0 and self.valence_velocity < 0:
            return "disengaging"
        elif self.arousal_velocity > 0 and self.valence_velocity < 0:
            return "frustrated"
        else:
            return "calming"


class StateTrajectory(BaseModel):
    """A sequence of states forming a trajectory."""
    
    user_id: str
    states: List[StateVector] = Field(default_factory=list)
    
    # Classification
    trajectory_type: TrajectoryType = TrajectoryType.STABLE
    
    # Current momentum
    momentum: StateMomentum = Field(default_factory=StateMomentum)
    
    # Statistics
    avg_arousal: float = 0.5
    avg_valence: float = 0.5
    arousal_std: float = 0.0
    valence_std: float = 0.0
    
    # Periodicity detection
    cycle_period_hours: Optional[float] = None
    cycle_amplitude: Optional[float] = None
    
    # Prediction
    predicted_next_state: Optional[StateVector] = None
    prediction_confidence: float = 0.0


class TrajectoryPrediction(BaseModel):
    """Prediction of future state based on trajectory."""
    
    user_id: str
    prediction_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Predicted state
    predicted_arousal: float = Field(ge=0.0, le=1.0)
    predicted_valence: float = Field(ge=0.0, le=1.0)
    predicted_promotion: float = Field(ge=0.0, le=1.0)
    predicted_prevention: float = Field(ge=0.0, le=1.0)
    
    # Prediction horizon
    horizon_minutes: int = 30
    
    # Confidence
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Model used
    model_type: str = "momentum"  # "momentum", "arima", "pattern_match"
    
    # Validation
    validated: bool = False
    actual_arousal: Optional[float] = None
    actual_valence: Optional[float] = None
    prediction_error: Optional[float] = None


# =============================================================================
# STATE TRAJECTORY MODELER
# =============================================================================

class StateTrajectoryModeler:
    """
    Models and predicts user psychological state trajectories.
    
    This is the core temporal intelligence component that:
    1. Tracks state evolution over time
    2. Classifies trajectory patterns
    3. Predicts future states
    4. Learns from prediction outcomes
    """
    
    def __init__(
        self,
        max_history_per_user: int = 100,
        prediction_horizon_minutes: int = 30,
    ):
        self.max_history = max_history_per_user
        self.prediction_horizon = prediction_horizon_minutes
        
        # User state histories
        self._user_states: Dict[str, deque] = {}
        
        # Trajectory patterns
        self._user_trajectories: Dict[str, StateTrajectory] = {}
        
        # Pending predictions for validation
        self._pending_predictions: Dict[str, TrajectoryPrediction] = {}
        
        # Learned patterns
        self._trajectory_outcomes: Dict[TrajectoryType, Dict[str, float]] = {
            t: {"conversions": 0, "impressions": 0, "rate": 0.0}
            for t in TrajectoryType
        }
    
    def record_state(
        self,
        user_id: str,
        state: StateVector,
    ) -> StateTrajectory:
        """
        Record a new state observation and update trajectory.
        
        Returns:
            Updated trajectory for the user
        """
        # Initialize if needed
        if user_id not in self._user_states:
            self._user_states[user_id] = deque(maxlen=self.max_history)
        
        # Add state
        self._user_states[user_id].append(state)
        
        # Update trajectory
        trajectory = self._compute_trajectory(user_id)
        self._user_trajectories[user_id] = trajectory
        
        return trajectory
    
    def _compute_trajectory(self, user_id: str) -> StateTrajectory:
        """Compute trajectory from state history."""
        states = list(self._user_states.get(user_id, []))
        
        if len(states) < 2:
            return StateTrajectory(
                user_id=user_id,
                states=states,
                trajectory_type=TrajectoryType.STABLE,
            )
        
        # Compute momentum (velocity and acceleration)
        momentum = self._compute_momentum(states)
        
        # Classify trajectory
        trajectory_type = self._classify_trajectory(states, momentum)
        
        # Compute statistics
        avg_arousal = sum(s.arousal for s in states) / len(states)
        avg_valence = sum(s.valence for s in states) / len(states)
        
        arousal_std = math.sqrt(
            sum((s.arousal - avg_arousal) ** 2 for s in states) / len(states)
        )
        valence_std = math.sqrt(
            sum((s.valence - avg_valence) ** 2 for s in states) / len(states)
        )
        
        # Detect periodicity
        cycle_period, cycle_amplitude = self._detect_periodicity(states)
        
        # Predict next state
        predicted, confidence = self._predict_next_state(states, momentum)
        
        return StateTrajectory(
            user_id=user_id,
            states=states,
            trajectory_type=trajectory_type,
            momentum=momentum,
            avg_arousal=avg_arousal,
            avg_valence=avg_valence,
            arousal_std=arousal_std,
            valence_std=valence_std,
            cycle_period_hours=cycle_period,
            cycle_amplitude=cycle_amplitude,
            predicted_next_state=predicted,
            prediction_confidence=confidence,
        )
    
    def _compute_momentum(self, states: List[StateVector]) -> StateMomentum:
        """Compute first and second derivatives of state."""
        if len(states) < 2:
            return StateMomentum()
        
        # Use last 5 states for velocity
        recent = states[-5:] if len(states) >= 5 else states
        
        # Time-weighted velocity
        total_time_hours = 0.0
        arousal_change = 0.0
        valence_change = 0.0
        
        for i in range(1, len(recent)):
            dt = (recent[i].timestamp - recent[i-1].timestamp).total_seconds() / 3600
            if dt > 0:
                total_time_hours += dt
                arousal_change += recent[i].arousal - recent[i-1].arousal
                valence_change += recent[i].valence - recent[i-1].valence
        
        if total_time_hours > 0:
            arousal_velocity = arousal_change / total_time_hours
            valence_velocity = valence_change / total_time_hours
        else:
            arousal_velocity = 0.0
            valence_velocity = 0.0
        
        # Acceleration (change in velocity)
        if len(states) >= 4:
            old_states = states[-4:-2]
            new_states = states[-2:]
            
            old_arousal_vel = (old_states[-1].arousal - old_states[0].arousal)
            new_arousal_vel = (new_states[-1].arousal - new_states[0].arousal)
            arousal_acceleration = new_arousal_vel - old_arousal_vel
            
            old_valence_vel = (old_states[-1].valence - old_states[0].valence)
            new_valence_vel = (new_states[-1].valence - new_states[0].valence)
            valence_acceleration = new_valence_vel - old_valence_vel
        else:
            arousal_acceleration = 0.0
            valence_acceleration = 0.0
        
        return StateMomentum(
            arousal_velocity=arousal_velocity,
            valence_velocity=valence_velocity,
            arousal_acceleration=arousal_acceleration,
            valence_acceleration=valence_acceleration,
        )
    
    def _classify_trajectory(
        self,
        states: List[StateVector],
        momentum: StateMomentum,
    ) -> TrajectoryType:
        """Classify the trajectory type."""
        
        # Check for cycling (oscillation)
        if len(states) >= 6:
            sign_changes = 0
            for i in range(2, len(states)):
                prev_delta = states[i-1].arousal - states[i-2].arousal
                curr_delta = states[i].arousal - states[i-1].arousal
                if prev_delta * curr_delta < 0:
                    sign_changes += 1
            
            if sign_changes >= len(states) // 2:
                return TrajectoryType.CYCLING
        
        # Check acceleration
        if abs(momentum.arousal_acceleration) > 0.1:
            if momentum.arousal_acceleration > 0:
                return TrajectoryType.ACCELERATING
            else:
                return TrajectoryType.DECELERATING
        
        # Check momentum direction
        av = momentum.arousal_velocity
        vv = momentum.valence_velocity
        threshold = 0.05
        
        if abs(av) < threshold and abs(vv) < threshold:
            return TrajectoryType.STABLE
        elif av > threshold and vv > threshold:
            return TrajectoryType.ENGAGING
        elif av < -threshold and vv < -threshold:
            return TrajectoryType.DISENGAGING
        elif av > threshold and vv < -threshold:
            return TrajectoryType.FRUSTRATED
        else:
            return TrajectoryType.CALMING
    
    def _detect_periodicity(
        self,
        states: List[StateVector],
    ) -> Tuple[Optional[float], Optional[float]]:
        """Detect periodic patterns in state trajectory."""
        if len(states) < 10:
            return None, None
        
        # Simple autocorrelation-based period detection
        arousal_values = [s.arousal for s in states]
        mean_arousal = sum(arousal_values) / len(arousal_values)
        
        # Try different periods (in number of states)
        best_period = None
        best_correlation = 0.0
        
        for period in range(3, min(len(states) // 2, 20)):
            correlation = 0.0
            count = 0
            
            for i in range(len(states) - period):
                correlation += (
                    (arousal_values[i] - mean_arousal) *
                    (arousal_values[i + period] - mean_arousal)
                )
                count += 1
            
            if count > 0:
                correlation /= count
                if correlation > best_correlation:
                    best_correlation = correlation
                    best_period = period
        
        if best_period is not None and best_correlation > 0.3:
            # Estimate period in hours
            avg_interval = sum(
                (states[i].timestamp - states[i-1].timestamp).total_seconds()
                for i in range(1, len(states))
            ) / (len(states) - 1) / 3600
            
            period_hours = best_period * avg_interval
            
            # Estimate amplitude
            amplitude = max(arousal_values) - min(arousal_values)
            
            return period_hours, amplitude
        
        return None, None
    
    def _predict_next_state(
        self,
        states: List[StateVector],
        momentum: StateMomentum,
    ) -> Tuple[Optional[StateVector], float]:
        """Predict the next state based on trajectory."""
        if len(states) < 2:
            return None, 0.0
        
        last_state = states[-1]
        
        # Simple momentum-based prediction
        predicted_arousal = last_state.arousal + momentum.arousal_velocity * 0.1
        predicted_arousal = max(0.0, min(1.0, predicted_arousal))
        
        predicted_valence = last_state.valence + momentum.valence_velocity * 0.1
        predicted_valence = max(0.0, min(1.0, predicted_valence))
        
        # Confidence based on trajectory stability
        if len(states) >= 5:
            # Lower confidence for high-variance trajectories
            variance = sum(s.distance_to(last_state) for s in states[-5:]) / 5
            confidence = max(0.2, min(0.9, 1.0 - variance))
        else:
            confidence = 0.4
        
        predicted = StateVector(
            arousal=predicted_arousal,
            valence=predicted_valence,
            promotion_focus=last_state.promotion_focus,
            prevention_focus=last_state.prevention_focus,
            construal_level=last_state.construal_level,
            cognitive_load=last_state.cognitive_load,
        )
        
        return predicted, confidence
    
    def get_trajectory(self, user_id: str) -> Optional[StateTrajectory]:
        """Get the current trajectory for a user."""
        return self._user_trajectories.get(user_id)
    
    def predict_state(
        self,
        user_id: str,
        horizon_minutes: int = 30,
    ) -> Optional[TrajectoryPrediction]:
        """Create a prediction for future state."""
        trajectory = self._user_trajectories.get(user_id)
        if not trajectory or not trajectory.predicted_next_state:
            return None
        
        predicted = trajectory.predicted_next_state
        
        prediction = TrajectoryPrediction(
            user_id=user_id,
            predicted_arousal=predicted.arousal,
            predicted_valence=predicted.valence,
            predicted_promotion=predicted.promotion_focus,
            predicted_prevention=predicted.prevention_focus,
            horizon_minutes=horizon_minutes,
            confidence=trajectory.prediction_confidence,
        )
        
        # Store for validation
        self._pending_predictions[user_id] = prediction
        
        return prediction
    
    def validate_prediction(
        self,
        user_id: str,
        actual_state: StateVector,
    ) -> Optional[float]:
        """
        Validate a previous prediction against actual state.
        
        Returns:
            Prediction error (if prediction existed)
        """
        prediction = self._pending_predictions.pop(user_id, None)
        if not prediction:
            return None
        
        # Compute error
        error = math.sqrt(
            (prediction.predicted_arousal - actual_state.arousal) ** 2 +
            (prediction.predicted_valence - actual_state.valence) ** 2
        )
        
        prediction.validated = True
        prediction.actual_arousal = actual_state.arousal
        prediction.actual_valence = actual_state.valence
        prediction.prediction_error = error
        
        return error
    
    def record_outcome(
        self,
        user_id: str,
        outcome_value: float,
    ) -> None:
        """
        Record an outcome for trajectory learning.
        
        This updates the trajectory-outcome correlation model.
        """
        trajectory = self._user_trajectories.get(user_id)
        if not trajectory:
            return
        
        # Update trajectory type statistics
        ttype = trajectory.trajectory_type
        stats = self._trajectory_outcomes[ttype]
        stats["impressions"] += 1
        if outcome_value > 0.5:
            stats["conversions"] += 1
        if stats["impressions"] > 0:
            stats["rate"] = stats["conversions"] / stats["impressions"]
    
    def get_trajectory_effectiveness(self) -> Dict[str, Dict[str, float]]:
        """Get conversion rates by trajectory type."""
        return {
            t.value: stats
            for t, stats in self._trajectory_outcomes.items()
        }
    
    def get_optimal_trajectory_for_conversion(self) -> TrajectoryType:
        """Get the trajectory type most associated with conversion."""
        best_type = TrajectoryType.ENGAGING  # Default
        best_rate = 0.0
        
        for ttype, stats in self._trajectory_outcomes.items():
            if stats["impressions"] >= 20 and stats["rate"] > best_rate:
                best_rate = stats["rate"]
                best_type = ttype
        
        return best_type
