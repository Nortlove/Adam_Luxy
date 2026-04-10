# =============================================================================
# ADAM Online Reinforcement Learning
# Location: adam/ml/online_learner.py
# =============================================================================

"""
ONLINE REINFORCEMENT LEARNING FROM AD OUTCOMES

The model doesn't stop learning after training. Every ad impression,
click, and conversion becomes a learning signal that updates the model
in real-time. This creates a system that IMPROVES FROM ITS OWN DECISIONS.

Three online learning mechanisms:

1. CONTEXTUAL BANDITS — Mechanism Selection
   Each ad decision is an arm in a contextual bandit. The context is the
   (NDF profile, archetype, category) tuple. The reward is the conversion
   outcome. Uses LinUCB for efficient exploration.

   Innovation: The context includes the NEURAL EMBEDDING from our foundation
   model, not just hand-crafted features. This means the bandit automatically
   captures complex interactions.

2. GRADIENT-FREE MODEL UPDATE — NDF Refinement
   Uses exponential moving average (EMA) updates to shift NDF predictions
   toward outcomes. No backpropagation needed, so it's fast enough for
   real-time use.

   For each outcome:
     ndf_bias[dim] = ema_alpha * ndf_bias[dim] + (1 - ema_alpha) * gradient_signal

3. REWARD-WEIGHTED REGRESSION — Archetype Model Fine-tuning
   Periodically collects a batch of (text, archetype, reward) tuples and
   fine-tunes the archetype head with reward-weighted loss. High-reward
   examples get higher weight in the loss function.

   This is a form of policy gradient: the model shifts its predictions
   toward archetypes that led to successful outcomes.

Academic grounding:
- Li et al. (2010) — Contextual Bandits for Personalized News (LinUCB)
- Abbasi-Yadkori et al. (2011) — Improved Algorithms for Linear Stochastic Bandits
- Polyak & Juditsky (1992) — Averaging for Stochastic Approximation (EMA updates)
- Peters & Schaal (2008) — Reward-Weighted Regression (policy gradient)
"""

import logging
import time
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# CONTEXTUAL BANDIT — LinUCB for Mechanism Selection
# =============================================================================

@dataclass
class BanditArm:
    """A mechanism arm in the contextual bandit."""
    mechanism: str
    A: np.ndarray = field(default_factory=lambda: np.eye(32))  # Context precision
    b: np.ndarray = field(default_factory=lambda: np.zeros(32))  # Reward vector
    pulls: int = 0
    total_reward: float = 0.0


class ContextualMechanismBandit:
    """
    LinUCB contextual bandit for mechanism selection.

    Given a context (NDF embedding + archetype + category), selects
    the mechanism most likely to produce a positive outcome.

    Uses the ADAM Foundation Model's embedding as context features,
    creating a tight feedback loop: model predicts → bandit selects
    → outcome updates bandit → outcome also updates model.
    """

    def __init__(
        self,
        mechanisms: Optional[List[str]] = None,
        context_dim: int = 32,
        alpha: float = 1.0,
        min_exploration: float = 0.05,
    ):
        self.mechanisms = mechanisms or [
            "social_proof", "scarcity", "authority", "commitment",
            "reciprocity", "identity_construction", "mimetic_desire",
            "attention_dynamics", "embodied_cognition",
        ]
        self.context_dim = context_dim
        self.alpha = alpha
        self.min_exploration = min_exploration

        # Initialize arms
        self._arms: Dict[str, BanditArm] = {
            mech: BanditArm(
                mechanism=mech,
                A=np.eye(context_dim),
                b=np.zeros(context_dim),
            )
            for mech in self.mechanisms
        }

        self._total_pulls = 0
        self._history: List[Dict] = []

    def select(
        self,
        context: np.ndarray,
        eligible_mechanisms: Optional[List[str]] = None,
        top_k: int = 3,
    ) -> List[Tuple[str, float]]:
        """
        Select top-K mechanisms for this context using LinUCB.

        Args:
            context: Context feature vector (from foundation model embedding)
            eligible_mechanisms: Subset of mechanisms to consider
            top_k: How many mechanisms to recommend

        Returns: [(mechanism, ucb_score), ...]
        """
        # Ensure context is the right dimension
        if len(context) != self.context_dim:
            context = self._project_context(context)

        eligible = eligible_mechanisms or self.mechanisms
        scores = []

        for mech in eligible:
            arm = self._arms.get(mech)
            if arm is None:
                continue

            try:
                # LinUCB formula: θ = A^(-1) * b
                A_inv = np.linalg.inv(arm.A)
                theta = A_inv @ arm.b

                # Expected reward
                expected = float(context @ theta)

                # Exploration bonus: α * sqrt(x^T A^(-1) x)
                exploration = self.alpha * float(
                    np.sqrt(context @ A_inv @ context)
                )

                ucb = expected + exploration
                scores.append((mech, ucb))

            except np.linalg.LinAlgError:
                # Singular matrix — use uniform
                scores.append((mech, np.random.random()))

        # Sort by UCB score
        scores.sort(key=lambda x: x[1], reverse=True)

        # Epsilon-greedy exploration floor
        if np.random.random() < self.min_exploration:
            np.random.shuffle(scores)

        return scores[:top_k]

    def update(
        self,
        mechanism: str,
        context: np.ndarray,
        reward: float,
    ) -> None:
        """
        Update the bandit after observing a reward.

        Args:
            mechanism: Which mechanism was selected
            context: The context features used for selection
            reward: Observed reward (0.0 for no conversion, 1.0 for conversion)
        """
        if mechanism not in self._arms:
            return

        if len(context) != self.context_dim:
            context = self._project_context(context)

        arm = self._arms[mechanism]

        # LinUCB update: A = A + x * x^T, b = b + reward * x
        arm.A += np.outer(context, context)
        arm.b += reward * context
        arm.pulls += 1
        arm.total_reward += reward
        self._total_pulls += 1

        self._history.append({
            "mechanism": mechanism,
            "reward": reward,
            "timestamp": time.time(),
        })

        # Trim history
        if len(self._history) > 10000:
            self._history = self._history[-10000:]

    def get_statistics(self) -> Dict[str, Any]:
        """Get bandit statistics."""
        stats = {}
        for mech, arm in self._arms.items():
            avg_reward = arm.total_reward / max(1, arm.pulls)
            stats[mech] = {
                "pulls": arm.pulls,
                "total_reward": arm.total_reward,
                "avg_reward": avg_reward,
            }

        return {
            "total_pulls": self._total_pulls,
            "arms": stats,
            "history_size": len(self._history),
        }

    def _project_context(self, context: np.ndarray) -> np.ndarray:
        """Project context to the right dimension."""
        if len(context) > self.context_dim:
            # Truncate
            return context[:self.context_dim]
        elif len(context) < self.context_dim:
            # Pad
            padded = np.zeros(self.context_dim)
            padded[:len(context)] = context
            return padded
        return context

    def export_state(self) -> Dict[str, Any]:
        """Export bandit state."""
        return {
            "arms": {
                mech: {
                    "A": arm.A.tolist(),
                    "b": arm.b.tolist(),
                    "pulls": arm.pulls,
                    "total_reward": arm.total_reward,
                }
                for mech, arm in self._arms.items()
            },
            "total_pulls": self._total_pulls,
        }

    def import_state(self, state: Dict[str, Any]) -> None:
        """Import bandit state."""
        for mech, arm_data in state.get("arms", {}).items():
            if mech in self._arms:
                self._arms[mech].A = np.array(arm_data["A"])
                self._arms[mech].b = np.array(arm_data["b"])
                self._arms[mech].pulls = arm_data["pulls"]
                self._arms[mech].total_reward = arm_data["total_reward"]
        self._total_pulls = state.get("total_pulls", 0)


# =============================================================================
# NDF ONLINE UPDATER — Gradient-Free Real-Time Updates
# =============================================================================

class NDFOnlineUpdater:
    """
    Real-time NDF prediction refinement using outcome signals.

    Maintains per-context NDF biases that shift the foundation model's
    NDF predictions based on observed outcomes. No backpropagation needed.

    For each (archetype, category) context:
        adjusted_ndf[dim] = model_ndf[dim] + bias[context][dim]

    Biases are updated via EMA:
        gradient = reward * (target_ndf[dim] - predicted_ndf[dim])
        bias[context][dim] += ema_alpha * gradient
    """

    def __init__(
        self,
        ndf_dimensions: int = 7,
        ema_alpha: float = 0.01,
        max_bias: float = 0.15,
    ):
        self.ndf_dimensions = ndf_dimensions
        self.ema_alpha = ema_alpha
        self.max_bias = max_bias

        # Per-context NDF biases
        self._biases: Dict[str, np.ndarray] = defaultdict(
            lambda: np.zeros(ndf_dimensions)
        )
        self._update_counts: Dict[str, int] = defaultdict(int)

        # Reward history for analysis
        self._reward_by_context: Dict[str, List[float]] = defaultdict(list)

    def adjust_ndf(
        self,
        ndf_profile: Dict[str, float],
        archetype: str,
        category: str = "",
    ) -> Dict[str, float]:
        """
        Adjust NDF prediction with learned biases.

        Returns adjusted NDF profile.
        """
        context_key = f"{archetype}_{category}"
        bias = self._biases[context_key]

        ndf_dims = [
            "approach_avoidance", "temporal_horizon", "social_calibration",
            "uncertainty_tolerance", "status_sensitivity",
            "cognitive_engagement", "arousal_seeking",
        ]

        adjusted = {}
        for i, dim in enumerate(ndf_dims):
            original = ndf_profile.get(dim, 0.5)
            adjusted_val = np.clip(original + bias[i], 0.0, 1.0)
            adjusted[dim] = float(adjusted_val)

        return adjusted

    def update(
        self,
        predicted_ndf: Dict[str, float],
        archetype: str,
        category: str,
        reward: float,
        mechanism_used: str = "",
    ) -> None:
        """
        Update NDF biases based on outcome.

        The gradient signal is:
        - If reward is high: shift NDF toward the prediction (reinforce)
        - If reward is low: shift NDF away from prediction (explore)

        For mechanism-specific learning:
        - If authority mechanism succeeded: increase cognitive_engagement bias
        - If social_proof succeeded: increase social_calibration bias
        """
        context_key = f"{archetype}_{category}"
        bias = self._biases[context_key]

        ndf_dims = [
            "approach_avoidance", "temporal_horizon", "social_calibration",
            "uncertainty_tolerance", "status_sensitivity",
            "cognitive_engagement", "arousal_seeking",
        ]

        # Mechanism-specific gradient signals
        mech_gradient = self._get_mechanism_gradient(mechanism_used, reward)

        for i, dim in enumerate(ndf_dims):
            predicted = predicted_ndf.get(dim, 0.5)

            # Base gradient: push toward extremes if successful
            if reward > 0.5:
                # Reinforce: push away from 0.5 (uncertain) toward prediction
                gradient = (predicted - 0.5) * reward * 0.5
            else:
                # Explore: push toward 0.5 (reset toward uncertainty)
                gradient = (0.5 - predicted) * (1 - reward) * 0.2

            # Add mechanism-specific signal
            gradient += mech_gradient.get(dim, 0.0) * reward

            # EMA update
            bias[i] += self.ema_alpha * gradient

            # Clip to max bias
            bias[i] = np.clip(bias[i], -self.max_bias, self.max_bias)

        self._biases[context_key] = bias
        self._update_counts[context_key] += 1
        self._reward_by_context[context_key].append(reward)

        # Trim reward history
        if len(self._reward_by_context[context_key]) > 500:
            self._reward_by_context[context_key] = (
                self._reward_by_context[context_key][-500:]
            )

    def _get_mechanism_gradient(
        self,
        mechanism: str,
        reward: float,
    ) -> Dict[str, float]:
        """Get NDF gradient signal specific to mechanism outcome."""
        # Domain knowledge: which NDF dimensions each mechanism relates to
        mechanism_ndf_map = {
            "social_proof": {"social_calibration": 0.1},
            "authority": {"cognitive_engagement": 0.08},
            "scarcity": {"arousal_seeking": 0.08, "uncertainty_tolerance": -0.05},
            "commitment": {"temporal_horizon": 0.06},
            "reciprocity": {"social_calibration": 0.06, "approach_avoidance": 0.04},
            "identity_construction": {"status_sensitivity": 0.08},
            "mimetic_desire": {"social_calibration": 0.1, "status_sensitivity": 0.06},
            "attention_dynamics": {"arousal_seeking": 0.08, "cognitive_engagement": 0.04},
            "embodied_cognition": {"approach_avoidance": 0.06},
        }

        return mechanism_ndf_map.get(mechanism, {})

    def get_context_performance(self) -> Dict[str, Dict[str, float]]:
        """Get performance by context."""
        return {
            context: {
                "avg_reward": float(np.mean(rewards)),
                "updates": self._update_counts[context],
                "bias_magnitude": float(np.linalg.norm(self._biases[context])),
            }
            for context, rewards in self._reward_by_context.items()
            if rewards
        }

    def export_state(self) -> Dict[str, Any]:
        """Export state for persistence."""
        return {
            "biases": {k: v.tolist() for k, v in self._biases.items()},
            "update_counts": dict(self._update_counts),
        }

    def import_state(self, state: Dict[str, Any]) -> None:
        """Import state."""
        for k, v in state.get("biases", {}).items():
            self._biases[k] = np.array(v)
        self._update_counts.update(state.get("update_counts", {}))


# =============================================================================
# REWARD-WEIGHTED REGRESSION — Periodic Archetype Fine-tuning
# =============================================================================

class RewardWeightedTrainer:
    """
    Periodically fine-tunes the foundation model's archetype and
    mechanism heads using reward-weighted regression.

    Collects batches of (text, prediction, reward) tuples and
    fine-tunes with reward as the loss weight. High-reward
    predictions get reinforced, low-reward predictions get suppressed.

    This is a form of REINFORCE policy gradient adapted for
    classification/regression heads.
    """

    def __init__(
        self,
        buffer_size: int = 5000,
        min_batch_for_update: int = 100,
        update_interval_requests: int = 500,
        learning_rate: float = 1e-5,
        reward_temperature: float = 2.0,
    ):
        self.buffer_size = buffer_size
        self.min_batch_for_update = min_batch_for_update
        self.update_interval = update_interval_requests
        self.learning_rate = learning_rate
        self.reward_temperature = reward_temperature

        # Experience buffer
        self._buffer: List[Dict[str, Any]] = []
        self._requests_since_update = 0
        self._total_updates = 0

    def add_experience(
        self,
        text: str,
        category: str,
        predicted_ndf: Dict[str, float],
        predicted_archetype: str,
        predicted_mechanisms: Dict[str, float],
        reward: float,
    ) -> None:
        """Add an experience to the replay buffer."""
        self._buffer.append({
            "text": text,
            "category": category,
            "ndf": predicted_ndf,
            "archetype": predicted_archetype,
            "mechanisms": predicted_mechanisms,
            "reward": reward,
            "timestamp": time.time(),
        })

        # Trim buffer
        if len(self._buffer) > self.buffer_size:
            self._buffer = self._buffer[-self.buffer_size:]

        self._requests_since_update += 1

    def should_update(self) -> bool:
        """Check if it's time for a model update."""
        return (
            self._requests_since_update >= self.update_interval
            and len(self._buffer) >= self.min_batch_for_update
        )

    def compute_update(
        self,
    ) -> Optional[Dict[str, Any]]:
        """
        Compute the reward-weighted update for the model.

        Returns a dict with update signals that can be applied to
        the foundation model's heads.
        """
        if len(self._buffer) < self.min_batch_for_update:
            return None

        # Sample batch (prioritize recent + high-reward)
        batch = self._sample_batch()

        rewards = np.array([ex["reward"] for ex in batch])

        # Reward-weight: exp(reward * temperature) / sum
        weights = np.exp(rewards * self.reward_temperature)
        weights = weights / weights.sum()

        # Compute NDF target shift
        ndf_dims = [
            "approach_avoidance", "temporal_horizon", "social_calibration",
            "uncertainty_tolerance", "status_sensitivity",
            "cognitive_engagement", "arousal_seeking",
        ]

        # Weighted mean of NDF predictions (high-reward predictions dominate)
        ndf_target = {}
        for dim in ndf_dims:
            dim_values = np.array([ex["ndf"].get(dim, 0.5) for ex in batch])
            ndf_target[dim] = float(np.sum(dim_values * weights))

        # Mechanism target
        mechanism_names = [
            "social_proof", "scarcity", "authority", "commitment",
            "reciprocity", "identity_construction", "mimetic_desire",
            "attention_dynamics", "embodied_cognition",
        ]
        mech_target = {}
        for mech in mechanism_names:
            mech_values = np.array([
                ex["mechanisms"].get(mech, 0.5) for ex in batch
            ])
            mech_target[mech] = float(np.sum(mech_values * weights))

        self._requests_since_update = 0
        self._total_updates += 1

        return {
            "ndf_target": ndf_target,
            "mechanism_target": mech_target,
            "batch_size": len(batch),
            "avg_reward": float(np.mean(rewards)),
            "reward_std": float(np.std(rewards)),
            "update_number": self._total_updates,
            "texts": [ex["text"] for ex in batch],
            "weights": weights.tolist(),
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get trainer statistics."""
        if not self._buffer:
            return {"buffer_size": 0}

        rewards = [ex["reward"] for ex in self._buffer]
        return {
            "buffer_size": len(self._buffer),
            "avg_reward": float(np.mean(rewards)),
            "total_updates": self._total_updates,
            "requests_since_update": self._requests_since_update,
        }

    def _sample_batch(self, batch_size: int = 256) -> List[Dict]:
        """Sample a batch with recency + reward priority."""
        if len(self._buffer) <= batch_size:
            return list(self._buffer)

        # Priority sampling: recent + high-reward
        n = len(self._buffer)
        recency_weight = np.linspace(0.5, 1.0, n)
        reward_weight = np.array([
            0.5 + ex["reward"] for ex in self._buffer
        ])
        probs = recency_weight * reward_weight
        probs = probs / probs.sum()

        indices = np.random.choice(n, size=batch_size, replace=False, p=probs)
        return [self._buffer[i] for i in indices]


# =============================================================================
# UNIFIED ONLINE LEARNING SYSTEM
# =============================================================================

class OnlineLearningSystem:
    """
    Unified online learning system that combines all three
    online learning mechanisms into a single interface.

    Usage:
        system = OnlineLearningSystem()

        # At prediction time:
        mechanisms = system.select_mechanisms(context_embedding, archetype, category)
        adjusted_ndf = system.adjust_ndf(ndf_profile, archetype, category)

        # After outcome:
        system.record_outcome(text, category, predicted_ndf, archetype, mechanisms, reward)
    """

    def __init__(
        self,
        persistence_dir: Optional[str] = None,
    ):
        self.persistence_dir = persistence_dir

        self.bandit = ContextualMechanismBandit()
        self.ndf_updater = NDFOnlineUpdater()
        self.reward_trainer = RewardWeightedTrainer()

        self._total_outcomes = 0

        if persistence_dir:
            self._load_state()

    def select_mechanisms(
        self,
        context_embedding: np.ndarray,
        archetype: str = "",
        category: str = "",
        eligible: Optional[List[str]] = None,
        top_k: int = 3,
    ) -> List[Tuple[str, float]]:
        """Select best mechanisms using contextual bandit."""
        return self.bandit.select(context_embedding, eligible, top_k)

    def adjust_ndf(
        self,
        ndf_profile: Dict[str, float],
        archetype: str,
        category: str = "",
    ) -> Dict[str, float]:
        """Adjust NDF prediction with learned biases."""
        return self.ndf_updater.adjust_ndf(ndf_profile, archetype, category)

    def record_outcome(
        self,
        text: str,
        category: str,
        predicted_ndf: Dict[str, float],
        archetype: str,
        mechanisms_used: List[str],
        mechanism_scores: Dict[str, float],
        reward: float,
        context_embedding: Optional[np.ndarray] = None,
    ) -> Dict[str, Any]:
        """
        Record an outcome and update all learning systems.

        Returns update info.
        """
        self._total_outcomes += 1
        updates = {}

        # 1. Update bandit for each mechanism used
        if context_embedding is not None:
            for mech in mechanisms_used:
                self.bandit.update(mech, context_embedding, reward)
            updates["bandit_updated"] = len(mechanisms_used)

        # 2. Update NDF biases
        for mech in mechanisms_used:
            self.ndf_updater.update(
                predicted_ndf, archetype, category, reward, mech
            )
        updates["ndf_biases_updated"] = True

        # 3. Add to reward-weighted trainer buffer
        self.reward_trainer.add_experience(
            text, category, predicted_ndf, archetype,
            mechanism_scores, reward,
        )
        updates["experience_buffered"] = True

        # 4. Check if model update is due
        if self.reward_trainer.should_update():
            update_signals = self.reward_trainer.compute_update()
            if update_signals:
                updates["model_update_computed"] = True
                updates["model_update_details"] = {
                    "batch_size": update_signals["batch_size"],
                    "avg_reward": update_signals["avg_reward"],
                }

        # Periodic persistence
        if self._total_outcomes % 100 == 0 and self.persistence_dir:
            self._save_state()

        return updates

    def get_statistics(self) -> Dict[str, Any]:
        """Get unified statistics."""
        return {
            "total_outcomes": self._total_outcomes,
            "bandit": self.bandit.get_statistics(),
            "ndf_updater": self.ndf_updater.get_context_performance(),
            "reward_trainer": self.reward_trainer.get_statistics(),
        }

    def _save_state(self) -> None:
        """Persist state."""
        if not self.persistence_dir:
            return
        path = Path(self.persistence_dir)
        path.mkdir(parents=True, exist_ok=True)

        state = {
            "bandit": self.bandit.export_state(),
            "ndf_updater": self.ndf_updater.export_state(),
            "total_outcomes": self._total_outcomes,
        }

        with open(path / "online_learning_state.json", "w") as f:
            json.dump(state, f)

    def _load_state(self) -> None:
        """Load state from disk."""
        if not self.persistence_dir:
            return
        path = Path(self.persistence_dir) / "online_learning_state.json"
        if not path.exists():
            return
        try:
            with open(path) as f:
                state = json.load(f)
            self.bandit.import_state(state.get("bandit", {}))
            self.ndf_updater.import_state(state.get("ndf_updater", {}))
            self._total_outcomes = state.get("total_outcomes", 0)
            logger.info(f"Loaded online learning state ({self._total_outcomes} outcomes)")
        except Exception as e:
            logger.warning(f"Failed to load online learning state: {e}")
