# =============================================================================
# ADAM Intelligence: Predictive Processing Framework
# Location: adam/intelligence/predictive_processing.py
# =============================================================================

"""
PREDICTIVE PROCESSING FRAMEWORK

Implements a cognitive science-grounded approach to ad selection based on
the brain's predictive processing paradigm.

Core Concepts:
1. Prediction Error: Unexpected outcomes drive learning and attention
2. Precision Weighting: Reliable signals weighted more in belief updates
3. Active Inference: Balance information gain (curiosity) with reward
4. Free Energy Minimization: Unified objective for perception and action

This framework enables ADAM to:
- Select ads that maximize expected information gain (exploration)
- Weight learning signals by their reliability (precision)
- Optimize for curiosity as well as conversion (active inference)
- Unify different objectives under one principled framework

Reference:
- Friston (2010) "The free-energy principle"
- Rao & Ballard (1999) "Predictive coding in the visual cortex"
- Schwartenbeck et al. (2019) "Computational mechanisms of curiosity"
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import logging
import math
import numpy as np
from collections import defaultdict

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class PredictiveProcessingConfig:
    """Configuration for the Predictive Processing framework."""
    
    # Prediction error
    prediction_error_threshold: float = 0.2  # Threshold for "surprising"
    learning_rate: float = 0.1  # Base learning rate
    
    # Precision weighting
    default_precision: float = 1.0
    min_precision: float = 0.1
    max_precision: float = 10.0
    precision_decay: float = 0.99  # Decay per update
    
    # Curiosity / Active inference
    curiosity_weight: float = 0.3  # Weight for epistemic value
    pragmatic_weight: float = 0.7  # Weight for expected reward
    curiosity_decay: float = 0.95  # Decay as certainty increases
    
    # Free energy
    complexity_penalty: float = 0.1  # Penalty for model complexity
    
    # Tracking
    history_window: int = 100


class ValueType(str, Enum):
    """Types of value in active inference."""
    PRAGMATIC = "pragmatic"    # Expected reward
    EPISTEMIC = "epistemic"    # Information gain
    COMBINED = "combined"      # Weighted combination


# =============================================================================
# BELIEF STATE
# =============================================================================

class BeliefState(BaseModel):
    """
    Represents current beliefs about a user/context.
    
    Beliefs are distributions, not point estimates.
    Uncertainty drives exploration.
    """
    
    # User identity
    user_id: str
    
    # Belief distributions (mean, precision for each dimension)
    personality_beliefs: Dict[str, Tuple[float, float]] = Field(default_factory=dict)
    preference_beliefs: Dict[str, Tuple[float, float]] = Field(default_factory=dict)
    context_beliefs: Dict[str, Tuple[float, float]] = Field(default_factory=dict)
    
    # Overall uncertainty
    total_uncertainty: float = Field(default=1.0)
    
    # Update history
    update_count: int = Field(default=0)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    def get_uncertainty(self, dimension: str) -> float:
        """Get uncertainty (inverse precision) for a dimension."""
        for beliefs in [self.personality_beliefs, self.preference_beliefs, self.context_beliefs]:
            if dimension in beliefs:
                _, precision = beliefs[dimension]
                return 1.0 / max(0.1, precision)
        return 1.0  # Default high uncertainty
    
    def get_mean(self, dimension: str) -> float:
        """Get belief mean for a dimension."""
        for beliefs in [self.personality_beliefs, self.preference_beliefs, self.context_beliefs]:
            if dimension in beliefs:
                mean, _ = beliefs[dimension]
                return mean
        return 0.5  # Default neutral
    
    def update_belief(
        self,
        dimension: str,
        observed: float,
        observation_precision: float,
    ) -> float:
        """
        Update belief using precision-weighted Bayesian update.
        
        Returns the prediction error.
        """
        # Find the belief
        for beliefs in [self.personality_beliefs, self.preference_beliefs, self.context_beliefs]:
            if dimension in beliefs:
                prior_mean, prior_precision = beliefs[dimension]
                break
        else:
            prior_mean, prior_precision = 0.5, 1.0
            self.context_beliefs[dimension] = (prior_mean, prior_precision)
        
        # Precision-weighted update (Kalman-like)
        total_precision = prior_precision + observation_precision
        posterior_mean = (
            prior_precision * prior_mean + observation_precision * observed
        ) / total_precision
        posterior_precision = total_precision
        
        # Prediction error
        prediction_error = observed - prior_mean
        
        # Update
        self.context_beliefs[dimension] = (posterior_mean, posterior_precision)
        self.update_count += 1
        self.last_updated = datetime.utcnow()
        
        # Recalculate total uncertainty
        all_precisions = []
        for beliefs in [self.personality_beliefs, self.preference_beliefs, self.context_beliefs]:
            for _, precision in beliefs.values():
                all_precisions.append(precision)
        
        if all_precisions:
            self.total_uncertainty = 1.0 / np.mean(all_precisions)
        
        return prediction_error


# =============================================================================
# PREDICTION ERROR TRACKER
# =============================================================================

class PredictionErrorTracker:
    """
    Tracks prediction errors for learning and surprise detection.
    
    Surprising events (large prediction errors) capture attention
    and drive learning. This is the core of predictive processing.
    """
    
    def __init__(self, config: PredictiveProcessingConfig):
        self.config = config
        self.errors: List[Dict] = []
        self.dimension_errors: Dict[str, List[float]] = defaultdict(list)
    
    def record_error(
        self,
        dimension: str,
        predicted: float,
        observed: float,
        precision: float,
        decision_id: str,
    ) -> Dict[str, Any]:
        """
        Record a prediction error.
        
        Returns surprise analysis.
        """
        error = observed - predicted
        abs_error = abs(error)
        
        # Precision-weighted error (surprisal)
        surprisal = precision * abs_error
        
        # Is this surprising?
        is_surprising = abs_error > self.config.prediction_error_threshold
        
        # Record
        record = {
            "decision_id": decision_id,
            "dimension": dimension,
            "predicted": predicted,
            "observed": observed,
            "error": error,
            "abs_error": abs_error,
            "precision": precision,
            "surprisal": surprisal,
            "is_surprising": is_surprising,
            "timestamp": datetime.utcnow(),
        }
        
        self.errors.append(record)
        self.dimension_errors[dimension].append(abs_error)
        
        # Trim
        if len(self.errors) > self.config.history_window:
            self.errors = self.errors[-self.config.history_window:]
        if len(self.dimension_errors[dimension]) > self.config.history_window:
            self.dimension_errors[dimension] = self.dimension_errors[dimension][-self.config.history_window:]
        
        return record
    
    def get_surprise_rate(self) -> float:
        """Get rate of surprising predictions."""
        if not self.errors:
            return 0.0
        surprising = sum(1 for e in self.errors if e["is_surprising"])
        return surprising / len(self.errors)
    
    def get_dimension_reliability(self, dimension: str) -> float:
        """
        Get reliability (inverse of error variance) for a dimension.
        
        High reliability = precise predictions = high precision
        """
        errors = self.dimension_errors.get(dimension, [])
        if len(errors) < 2:
            return 1.0  # Default
        
        variance = np.var(errors)
        reliability = 1.0 / max(0.1, variance)
        
        return min(self.config.max_precision, reliability)


# =============================================================================
# CURIOSITY ENGINE
# =============================================================================

class CuriosityEngine:
    """
    Computes epistemic value (information gain) for active inference.
    
    Curiosity = Expected reduction in uncertainty from taking an action.
    
    Key insight: Sometimes showing an ad that might not convert is
    valuable because it reduces uncertainty about the user.
    """
    
    def __init__(self, config: PredictiveProcessingConfig):
        self.config = config
    
    def compute_epistemic_value(
        self,
        belief_state: BeliefState,
        ad_features: Dict[str, float],
    ) -> float:
        """
        Compute epistemic value of showing an ad.
        
        Epistemic value = Expected information gain about the user.
        
        Higher value when:
        - User beliefs have high uncertainty
        - Ad tests specific uncertain dimensions
        """
        # Get dimensions tested by this ad
        tested_dimensions = list(ad_features.keys())
        
        # Calculate expected information gain
        info_gain = 0.0
        
        for dim in tested_dimensions:
            uncertainty = belief_state.get_uncertainty(dim)
            
            # Ad feature strength determines how informative the observation will be
            feature_strength = abs(ad_features.get(dim, 0) - 0.5) * 2  # 0-1
            
            # Expected info gain = uncertainty * feature_strength
            # (observing response to strongly-featured ad is more informative)
            dim_info_gain = uncertainty * feature_strength
            info_gain += dim_info_gain
        
        # Normalize by number of dimensions
        if tested_dimensions:
            info_gain /= len(tested_dimensions)
        
        return info_gain
    
    def compute_curiosity_bonus(
        self,
        belief_state: BeliefState,
        ad_features: Dict[str, float],
    ) -> float:
        """
        Compute curiosity bonus for ad selection.
        
        Bonus is higher when:
        - We're uncertain about dimensions relevant to this ad
        - Showing this ad would reduce that uncertainty
        """
        epistemic_value = self.compute_epistemic_value(belief_state, ad_features)
        
        # Apply curiosity weight and decay
        uncertainty_factor = belief_state.total_uncertainty
        decayed_weight = self.config.curiosity_weight * (
            self.config.curiosity_decay ** belief_state.update_count
        )
        
        bonus = epistemic_value * decayed_weight * uncertainty_factor
        
        return bonus


# =============================================================================
# FREE ENERGY CALCULATOR
# =============================================================================

class FreeEnergyCalculator:
    """
    Computes expected free energy for action selection.
    
    Free Energy = Expected Surprise + Complexity
    
    Minimizing free energy unifies:
    - Maximizing expected reward (minimizing negative surprise)
    - Reducing uncertainty (minimizing complexity)
    - Seeking information (epistemic value)
    """
    
    def __init__(self, config: PredictiveProcessingConfig):
        self.config = config
    
    def compute_expected_free_energy(
        self,
        belief_state: BeliefState,
        expected_reward: float,
        reward_precision: float,
        epistemic_value: float,
    ) -> float:
        """
        Compute expected free energy (lower is better).
        
        Expected Free Energy =
            - Pragmatic Value (expected reward)
            - Epistemic Value (information gain)
            + Complexity (model uncertainty)
        
        Actions that minimize this are preferred.
        """
        # Pragmatic value (weighted by precision - more certain rewards valued more)
        pragmatic = expected_reward * reward_precision * self.config.pragmatic_weight
        
        # Epistemic value (weighted by curiosity)
        epistemic = epistemic_value * self.config.curiosity_weight
        
        # Complexity penalty (uncertainty in current beliefs)
        complexity = belief_state.total_uncertainty * self.config.complexity_penalty
        
        # Free energy (negative because we want to MINIMIZE)
        free_energy = -pragmatic - epistemic + complexity
        
        return free_energy
    
    def select_action_by_free_energy(
        self,
        belief_state: BeliefState,
        candidates: List[Dict[str, Any]],
    ) -> Tuple[int, Dict[str, float]]:
        """
        Select action (ad) that minimizes expected free energy.
        
        Args:
            belief_state: Current user beliefs
            candidates: List of ad candidates with features
            
        Returns:
            Tuple of (selected_index, free_energy_breakdown)
        """
        curiosity_engine = CuriosityEngine(self.config)
        
        free_energies = []
        breakdowns = []
        
        for candidate in candidates:
            # Expected reward (from model)
            expected_reward = candidate.get("expected_reward", 0.5)
            reward_precision = candidate.get("reward_precision", 1.0)
            
            # Epistemic value
            ad_features = candidate.get("features", {})
            epistemic = curiosity_engine.compute_epistemic_value(belief_state, ad_features)
            
            # Free energy
            fe = self.compute_expected_free_energy(
                belief_state,
                expected_reward,
                reward_precision,
                epistemic,
            )
            
            free_energies.append(fe)
            breakdowns.append({
                "free_energy": fe,
                "expected_reward": expected_reward,
                "epistemic_value": epistemic,
                "complexity": belief_state.total_uncertainty * self.config.complexity_penalty,
            })
        
        # Select minimum free energy
        selected_idx = np.argmin(free_energies)
        
        return selected_idx, breakdowns[selected_idx]


# =============================================================================
# PREDICTIVE PROCESSING ENGINE
# =============================================================================

class PredictiveProcessingEngine:
    """
    Main engine for predictive processing-based ad selection.
    
    This unifies multiple optimization objectives under the
    free energy principle from cognitive science.
    
    Advantages:
    1. Principled balance of exploration/exploitation
    2. Precision-weighted learning (reliable signals matter more)
    3. Curiosity-driven exploration (reduces uncertainty)
    4. Unified objective (no arbitrary weighting)
    
    Usage:
        engine = PredictiveProcessingEngine()
        
        # Get belief state for user
        belief_state = engine.get_or_create_belief_state(user_id)
        
        # Select ad minimizing free energy
        selected_idx, breakdown = engine.select_ad(belief_state, ad_candidates)
        
        # Update beliefs on observation
        engine.update_on_observation(belief_state, ad_features, outcome)
    """
    
    def __init__(self, config: Optional[PredictiveProcessingConfig] = None):
        self.config = config or PredictiveProcessingConfig()
        
        # Components
        self.error_tracker = PredictionErrorTracker(self.config)
        self.curiosity_engine = CuriosityEngine(self.config)
        self.free_energy = FreeEnergyCalculator(self.config)
        
        # User belief states
        self.belief_states: Dict[str, BeliefState] = {}
        
        # Dimension precisions (learned from data)
        self.dimension_precisions: Dict[str, float] = defaultdict(lambda: 1.0)
        
        # Statistics
        self.selections = 0
        self.updates = 0
    
    def get_or_create_belief_state(self, user_id: str) -> BeliefState:
        """Get or create belief state for a user."""
        if user_id not in self.belief_states:
            self.belief_states[user_id] = BeliefState(user_id=user_id)
        return self.belief_states[user_id]
    
    def select_ad(
        self,
        belief_state: BeliefState,
        candidates: List[Dict[str, Any]],
    ) -> Tuple[int, Dict[str, float]]:
        """
        Select ad minimizing expected free energy.
        
        Args:
            belief_state: User's current belief state
            candidates: List of ad candidates
            
        Returns:
            Tuple of (selected_index, free_energy_breakdown)
        """
        if not candidates:
            return 0, {}
        
        selected_idx, breakdown = self.free_energy.select_action_by_free_energy(
            belief_state, candidates
        )
        
        self.selections += 1
        
        logger.debug(
            f"Selected ad {selected_idx} via free energy minimization: "
            f"FE={breakdown['free_energy']:.3f}, "
            f"reward={breakdown['expected_reward']:.3f}, "
            f"epistemic={breakdown['epistemic_value']:.3f}"
        )
        
        return selected_idx, breakdown
    
    def update_on_observation(
        self,
        belief_state: BeliefState,
        observed_features: Dict[str, float],
        decision_id: str,
    ) -> Dict[str, float]:
        """
        Update beliefs based on observed user response.
        
        Args:
            belief_state: User's belief state
            observed_features: Observed feature values
            decision_id: Decision ID for tracking
            
        Returns:
            Dict of prediction errors per dimension
        """
        prediction_errors = {}
        
        for dimension, observed in observed_features.items():
            # Get prediction
            predicted = belief_state.get_mean(dimension)
            
            # Get precision from tracker
            precision = self.dimension_precisions[dimension]
            
            # Record error
            error_record = self.error_tracker.record_error(
                dimension, predicted, observed, precision, decision_id
            )
            
            # Update belief
            prediction_error = belief_state.update_belief(
                dimension, observed, precision * self.config.learning_rate
            )
            
            prediction_errors[dimension] = prediction_error
            
            # Update dimension precision based on reliability
            new_precision = self.error_tracker.get_dimension_reliability(dimension)
            self.dimension_precisions[dimension] = (
                self.config.precision_decay * self.dimension_precisions[dimension] +
                (1 - self.config.precision_decay) * new_precision
            )
        
        self.updates += 1
        
        return prediction_errors
    
    def get_curiosity_score(
        self,
        user_id: str,
        ad_features: Dict[str, float],
    ) -> float:
        """
        Get curiosity score for showing a specific ad to a user.
        
        High curiosity score = high information gain potential.
        """
        belief_state = self.get_or_create_belief_state(user_id)
        return self.curiosity_engine.compute_curiosity_bonus(belief_state, ad_features)
    
    def get_surprise_analysis(self) -> Dict[str, Any]:
        """Get analysis of recent prediction surprises."""
        return {
            "surprise_rate": self.error_tracker.get_surprise_rate(),
            "total_errors_tracked": len(self.error_tracker.errors),
            "dimension_reliabilities": {
                dim: self.error_tracker.get_dimension_reliability(dim)
                for dim in self.error_tracker.dimension_errors.keys()
            },
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "total_selections": self.selections,
            "total_updates": self.updates,
            "active_users": len(self.belief_states),
            "dimension_precisions": dict(self.dimension_precisions),
            "surprise_rate": self.error_tracker.get_surprise_rate(),
        }


# =============================================================================
# SINGLETON
# =============================================================================

_engine: Optional[PredictiveProcessingEngine] = None


def get_predictive_processing_engine() -> PredictiveProcessingEngine:
    """Get singleton Predictive Processing engine."""
    global _engine
    if _engine is None:
        _engine = PredictiveProcessingEngine()
    return _engine
