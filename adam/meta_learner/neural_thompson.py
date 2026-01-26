# =============================================================================
# ADAM Meta-Learner: Neural Thompson Sampling
# Location: adam/meta_learner/neural_thompson.py
# =============================================================================

"""
NEURAL THOMPSON SAMPLING

Cutting-edge enhancement to the Meta-Learner that learns context-dependent
exploration-exploitation tradeoffs using neural networks.

Key Advantages over Standard Thompson Sampling:
1. Context-Aware: Uses user/session features to estimate posteriors
2. Learned Exploration: Exploration bonus learned from data, not fixed
3. Epistemic Uncertainty: Neural network uncertainty drives exploration
4. Transfer Learning: Shares knowledge across similar contexts

Reference:
- Riquelme et al. (2018) "Deep Bayesian Bandits Showdown"
- Blundell et al. (2015) "Weight Uncertainty in Neural Networks"
- Osband et al. (2016) "Deep Exploration via Bootstrapped DQN"
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import logging
import math
import random
import numpy as np
from collections import defaultdict

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

@dataclass
class NeuralThompsonConfig:
    """Configuration for Neural Thompson Sampling."""
    
    # Network architecture
    context_dim: int = 32  # Input context dimension
    hidden_dim: int = 64   # Hidden layer dimension
    num_heads: int = 5     # Number of bootstrap heads for uncertainty
    
    # Learning parameters
    learning_rate: float = 0.01
    prior_variance: float = 1.0
    posterior_variance: float = 0.01
    
    # Exploration parameters
    exploration_bonus_base: float = 0.1
    exploration_decay: float = 0.995
    min_exploration: float = 0.01
    
    # Uncertainty calibration
    epistemic_weight: float = 0.5  # Weight for epistemic vs aleatoric uncertainty
    calibration_window: int = 100  # Rolling window for calibration
    
    # Memory
    max_history: int = 10000
    batch_size: int = 32


class ModalityType(str, Enum):
    """Learning modalities for routing."""
    SUPERVISED_CONVERSION = "supervised_conversion"
    SUPERVISED_ENGAGEMENT = "supervised_engagement"
    UNSUPERVISED_CLUSTERING = "unsupervised_clustering"
    UNSUPERVISED_GRAPH = "unsupervised_graph"
    REINFORCEMENT_BANDIT = "reinforcement_bandit"
    REINFORCEMENT_CONTEXTUAL = "reinforcement_contextual"
    CAUSAL_INFERENCE = "causal_inference"
    SELF_SUPERVISED = "self_supervised"


# =============================================================================
# NEURAL NETWORK COMPONENTS (Numpy-based for simplicity)
# =============================================================================

class BootstrapHead:
    """
    Single bootstrap head for uncertainty estimation.
    
    Each head is trained on a different bootstrap sample,
    enabling ensemble-based uncertainty estimation.
    """
    
    def __init__(self, input_dim: int, hidden_dim: int, output_dim: int, seed: int):
        self.rng = np.random.default_rng(seed)
        
        # Xavier initialization
        self.W1 = self.rng.normal(0, np.sqrt(2.0 / input_dim), (input_dim, hidden_dim))
        self.b1 = np.zeros(hidden_dim)
        self.W2 = self.rng.normal(0, np.sqrt(2.0 / hidden_dim), (hidden_dim, output_dim))
        self.b2 = np.zeros(output_dim)
        
        # Eligibility traces for learning
        self.trace_W1 = np.zeros_like(self.W1)
        self.trace_b1 = np.zeros_like(self.b1)
        self.trace_W2 = np.zeros_like(self.W2)
        self.trace_b2 = np.zeros_like(self.b2)
    
    def forward(self, x: np.ndarray) -> np.ndarray:
        """Forward pass through the network."""
        h = np.tanh(x @ self.W1 + self.b1)
        y = h @ self.W2 + self.b2
        return y
    
    def predict_with_hidden(self, x: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Forward pass returning hidden activations for learning."""
        h = np.tanh(x @ self.W1 + self.b1)
        y = h @ self.W2 + self.b2
        return y, h
    
    def update(self, x: np.ndarray, target: float, lr: float = 0.01) -> float:
        """
        Update weights using gradient descent.
        
        Returns the squared error.
        """
        # Forward
        y, h = self.predict_with_hidden(x)
        
        # Error
        error = target - y[0]
        
        # Backward
        dW2 = np.outer(h, np.array([error]))
        db2 = np.array([error])
        
        dh = self.W2[:, 0] * error
        dtanh = (1 - h ** 2) * dh
        dW1 = np.outer(x, dtanh)
        db1 = dtanh
        
        # Update
        self.W1 += lr * dW1
        self.b1 += lr * db1
        self.W2 += lr * dW2
        self.b2 += lr * db2
        
        return error ** 2


class BayesianNeuralNetwork:
    """
    Ensemble of bootstrap heads for Bayesian uncertainty estimation.
    
    Disagreement between heads = epistemic uncertainty (model uncertainty)
    Variance within heads = aleatoric uncertainty (data noise)
    """
    
    def __init__(self, config: NeuralThompsonConfig, output_dim: int):
        self.config = config
        self.output_dim = output_dim
        
        # Create bootstrap heads
        self.heads = [
            BootstrapHead(
                config.context_dim, 
                config.hidden_dim, 
                output_dim,
                seed=i * 42
            )
            for i in range(config.num_heads)
        ]
        
        # Training history
        self.training_count = 0
    
    def predict(self, context: np.ndarray) -> np.ndarray:
        """Predict mean output across all heads."""
        predictions = np.array([head.forward(context) for head in self.heads])
        return predictions.mean(axis=0)
    
    def predict_with_uncertainty(
        self, 
        context: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict with epistemic uncertainty estimation.
        
        Returns:
            mean: Mean prediction across heads
            std: Standard deviation (epistemic uncertainty)
        """
        predictions = np.array([head.forward(context) for head in self.heads])
        mean = predictions.mean(axis=0)
        std = predictions.std(axis=0)
        return mean, std
    
    def sample_posterior(self, context: np.ndarray) -> np.ndarray:
        """
        Thompson Sampling: Sample from the posterior.
        
        Uses a random head's prediction + noise for exploration.
        """
        # Select random head (Thompson sampling)
        head = random.choice(self.heads)
        prediction = head.forward(context)
        
        # Add posterior noise proportional to uncertainty
        _, std = self.predict_with_uncertainty(context)
        noise = np.random.normal(0, std * self.config.posterior_variance)
        
        return prediction + noise
    
    def update(
        self, 
        context: np.ndarray, 
        action: int, 
        reward: float,
        bootstrap_mask: Optional[np.ndarray] = None
    ) -> float:
        """
        Update network with observed reward.
        
        Uses bootstrapping: each head sees different samples.
        """
        if bootstrap_mask is None:
            # Poisson bootstrap
            bootstrap_mask = np.random.poisson(1, len(self.heads))
        
        total_error = 0.0
        for i, (head, count) in enumerate(zip(self.heads, bootstrap_mask)):
            for _ in range(count):
                # Update the head
                error = head.update(
                    context, 
                    reward,  # Learning signal
                    lr=self.config.learning_rate
                )
                total_error += error
        
        self.training_count += 1
        return total_error


# =============================================================================
# NEURAL THOMPSON SAMPLING ENGINE
# =============================================================================

@dataclass
class ModalityPrediction:
    """Prediction for a single modality."""
    modality: ModalityType
    expected_reward: float
    uncertainty: float
    sampled_value: float
    exploration_bonus: float
    final_score: float


class NeuralThompsonEngine:
    """
    Neural Thompson Sampling for context-aware modality selection.
    
    This replaces the standard Beta-posterior Thompson Sampling with
    a neural network that conditions on context features.
    
    Key Features:
    1. Context conditioning: Uses user/session features
    2. Ensemble uncertainty: Bootstrap heads for exploration
    3. Learned exploration: Exploration adapts to context
    4. Credit assignment: Proper attribution of outcomes
    
    Usage:
        engine = NeuralThompsonEngine()
        
        # Select modality
        selection = await engine.select_modality(context_features)
        
        # Update on outcome
        await engine.update(selection.modality, context_features, reward)
    """
    
    def __init__(self, config: Optional[NeuralThompsonConfig] = None):
        self.config = config or NeuralThompsonConfig()
        
        # One network per modality
        self.networks: Dict[ModalityType, BayesianNeuralNetwork] = {
            modality: BayesianNeuralNetwork(self.config, 1)
            for modality in ModalityType
        }
        
        # Exploration decay
        self.exploration_bonus = self.config.exploration_bonus_base
        
        # History for learning
        self.history: List[Dict] = []
        
        # Calibration tracking
        self.calibration_errors: List[float] = []
        
        # Statistics
        self.selection_counts: Dict[ModalityType, int] = defaultdict(int)
        self.total_selections = 0
    
    async def select_modality(
        self,
        context_features: Dict[str, float],
        eligible_modalities: Optional[List[ModalityType]] = None,
    ) -> Tuple[ModalityType, ModalityPrediction]:
        """
        Select modality using Neural Thompson Sampling.
        
        Args:
            context_features: Context dictionary (will be featurized)
            eligible_modalities: Subset of modalities to consider
            
        Returns:
            Tuple of selected modality and prediction details
        """
        # Default to all modalities
        if eligible_modalities is None:
            eligible_modalities = list(ModalityType)
        
        # Featurize context
        context_vector = self._featurize_context(context_features)
        
        # Get predictions for each modality
        predictions: Dict[ModalityType, ModalityPrediction] = {}
        
        for modality in eligible_modalities:
            network = self.networks[modality]
            
            # Get expected value and uncertainty
            expected, uncertainty = network.predict_with_uncertainty(context_vector)
            expected_value = expected[0]
            uncertainty_value = uncertainty[0]
            
            # Thompson sample
            sampled = network.sample_posterior(context_vector)[0]
            
            # Exploration bonus (decays over time, increases with uncertainty)
            exploration = self.exploration_bonus * uncertainty_value
            
            # Final score
            final_score = sampled + exploration
            
            predictions[modality] = ModalityPrediction(
                modality=modality,
                expected_reward=expected_value,
                uncertainty=uncertainty_value,
                sampled_value=sampled,
                exploration_bonus=exploration,
                final_score=final_score,
            )
        
        # Select best modality by final score
        best_modality = max(
            eligible_modalities,
            key=lambda m: predictions[m].final_score
        )
        
        # Update statistics
        self.selection_counts[best_modality] += 1
        self.total_selections += 1
        
        # Decay exploration
        self.exploration_bonus = max(
            self.config.min_exploration,
            self.exploration_bonus * self.config.exploration_decay
        )
        
        logger.debug(
            f"Neural Thompson selected {best_modality.value}: "
            f"expected={predictions[best_modality].expected_reward:.3f}, "
            f"uncertainty={predictions[best_modality].uncertainty:.3f}"
        )
        
        return best_modality, predictions[best_modality]
    
    async def update(
        self,
        modality: ModalityType,
        context_features: Dict[str, float],
        reward: float,
        decision_id: Optional[str] = None,
    ) -> float:
        """
        Update the network with observed reward.
        
        Args:
            modality: Modality that was selected
            context_features: Context at decision time
            reward: Observed reward (0-1)
            decision_id: Optional decision ID for tracking
            
        Returns:
            Training error
        """
        context_vector = self._featurize_context(context_features)
        
        # Update the selected modality's network
        network = self.networks[modality]
        error = network.update(context_vector, 0, reward)  # action=0 since single output
        
        # Store in history
        self.history.append({
            "decision_id": decision_id,
            "modality": modality,
            "context": context_features,
            "reward": reward,
            "timestamp": datetime.now(),
        })
        
        # Trim history
        if len(self.history) > self.config.max_history:
            self.history = self.history[-self.config.max_history:]
        
        # Update calibration
        self._update_calibration(modality, context_features, reward)
        
        logger.debug(f"Updated {modality.value} network: reward={reward:.3f}, error={error:.4f}")
        
        return error
    
    def _featurize_context(self, context: Dict[str, float]) -> np.ndarray:
        """
        Convert context dictionary to feature vector.
        
        Handles missing features and normalizes.
        """
        # Define feature order (must be consistent)
        feature_names = [
            "user_data_richness",
            "has_conversion_history",
            "category_novelty",
            "session_depth",
            "hour_of_day",
            "day_of_week",
            "is_mobile",
            "is_returning_user",
            "time_since_last_visit",
            "cart_value",
            "page_views",
            "scroll_depth",
            "click_count",
            "cognitive_load",
            "regulatory_focus",
            "construal_level",
            "emotional_valence",
            "engagement_score",
            "purchase_intent_score",
            "brand_familiarity",
        ]
        
        # Build vector with defaults
        vector = np.zeros(self.config.context_dim)
        
        for i, name in enumerate(feature_names[:self.config.context_dim]):
            if name in context:
                vector[i] = float(context[name])
        
        # Normalize
        vector = np.clip(vector, -3, 3)  # Prevent extreme values
        
        return vector
    
    def _update_calibration(
        self,
        modality: ModalityType,
        context_features: Dict[str, float],
        observed_reward: float,
    ) -> None:
        """Track calibration of uncertainty estimates."""
        context_vector = self._featurize_context(context_features)
        network = self.networks[modality]
        
        expected, uncertainty = network.predict_with_uncertainty(context_vector)
        
        # Check if observed was within predicted uncertainty
        prediction_error = abs(expected[0] - observed_reward)
        expected_error = uncertainty[0]  # 1 std
        
        # Calibration: prediction_error should be ~= expected_error
        calibration_ratio = prediction_error / max(0.01, expected_error)
        self.calibration_errors.append(calibration_ratio)
        
        # Trim calibration window
        if len(self.calibration_errors) > self.config.calibration_window:
            self.calibration_errors = self.calibration_errors[-self.config.calibration_window:]
    
    def get_calibration_score(self) -> float:
        """
        Get calibration score (1.0 = perfectly calibrated).
        
        Values > 1 indicate under-confident (too much uncertainty).
        Values < 1 indicate over-confident (too little uncertainty).
        """
        if not self.calibration_errors:
            return 1.0
        return np.mean(self.calibration_errors)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "total_selections": self.total_selections,
            "selection_counts": {m.value: c for m, c in self.selection_counts.items()},
            "exploration_bonus": self.exploration_bonus,
            "calibration_score": self.get_calibration_score(),
            "history_size": len(self.history),
            "training_counts": {
                m.value: self.networks[m].training_count 
                for m in ModalityType
            },
        }
    
    def get_modality_summary(
        self,
        context_features: Dict[str, float],
    ) -> Dict[str, Dict[str, float]]:
        """
        Get summary of expected rewards for all modalities.
        
        Useful for debugging and understanding routing decisions.
        """
        context_vector = self._featurize_context(context_features)
        
        summary = {}
        for modality in ModalityType:
            network = self.networks[modality]
            expected, uncertainty = network.predict_with_uncertainty(context_vector)
            
            summary[modality.value] = {
                "expected_reward": float(expected[0]),
                "uncertainty": float(uncertainty[0]),
                "selection_count": self.selection_counts[modality],
            }
        
        return summary


# =============================================================================
# SINGLETON
# =============================================================================

_engine: Optional[NeuralThompsonEngine] = None


def get_neural_thompson_engine() -> NeuralThompsonEngine:
    """Get singleton Neural Thompson engine."""
    global _engine
    if _engine is None:
        _engine = NeuralThompsonEngine()
    return _engine
