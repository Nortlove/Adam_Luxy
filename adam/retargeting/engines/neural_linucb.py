# =============================================================================
# Neural-LinUCB for Mechanism Selection
# Location: adam/retargeting/engines/neural_linucb.py
# Reference: Xu et al. (ICLR 2022) — Achieves Õ(√T) regret
# =============================================================================

"""
Neural-LinUCB Mechanism Selection Engine.

Architecture:
1. Representation network: maps 43-dim bilateral edge context to a learned
   d-dim embedding that captures non-linear buyer×seller×alignment interactions
2. LinUCB layer: operates on the embedding with closed-form UCB confidence
   intervals for each mechanism arm

Why this matters: The current Thompson Sampling ignores the 43 bilateral
edge dimensions available at L3+ of the cascade. These dimensions have
correlations with conversion of |r| up to 0.80 (emotional_resonance).
Neural-LinUCB captures non-linear interactions between them (e.g.,
"high reactance × low trust × scarcity = very negative") that the
barrier-categorical conditioning in Enhancement #33 cannot represent.

Integration: Composes with the existing BayesianMechanismSelector.
When bilateral edge dims are available (L3+), Neural-LinUCB provides
reward estimates. When not (L1-L2), falls back to Thompson Sampling.

Latency target: <30ms forward pass (within 100ms total budget).
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Try PyTorch — fall back to numpy-only implementation if unavailable
try:
    import torch
    import torch.nn as nn
    _TORCH_AVAILABLE = True
except ImportError:
    _TORCH_AVAILABLE = False
    logger.info("PyTorch not available. Neural-LinUCB will use numpy-only mode.")


# ---------------------------------------------------------------------------
# The 43 bilateral edge dimensions available at L3+ of the cascade.
# These are the context features that Neural-LinUCB operates on.
# ---------------------------------------------------------------------------
BILATERAL_CONTEXT_DIMS = [
    # Core alignment (8)
    "regulatory_fit_score", "construal_fit_score", "personality_brand_alignment",
    "emotional_resonance", "value_alignment", "evolutionary_motive_match",
    "composite_alignment", "persuasion_confidence_multiplier",
    # Extended psychological (13)
    "appeal_resonance", "processing_route_match", "implicit_driver_match",
    "lay_theory_alignment", "linguistic_style_match", "identity_signaling_match",
    "full_cosine_alignment", "uniqueness_popularity_fit",
    "mental_simulation_resonance", "involvement_weight_modifier",
    "negativity_bias_match", "reactance_fit", "optimal_distinctiveness_fit",
    # Match dimensions (10)
    "brand_trust_fit", "self_monitoring_fit", "spending_pain_match",
    "disgust_contamination_fit", "anchor_susceptibility_match",
    "mental_ownership_match", "linguistic_style_matching",
    # Mechanism scores (5)
    "mech_social_proof", "mech_authority", "mech_reciprocity",
    "mech_commitment", "mech_liking",
    # Metadata signals (2)
    "star_rating", "helpful_votes",
    # Enhancement #36: Within-subject repeated measures features (10)
    # These capture per-user longitudinal state that standard bilateral
    # edge dims cannot represent. Enables Neural-LinUCB to learn
    # "evidence_proof works better for users who are warming up" etc.
    "user_random_intercept",        # User baseline deviation from population
    "user_trajectory_trend",        # Linear engagement slope across touches
    "user_ar1_correlation",         # Within-user outcome autocorrelation
    "user_total_touches",           # How many touches this user has received
    "user_best_mechanism_mean",     # Posterior mean of user's best mechanism
    "user_variance_ratio",          # Within/between variance ratio (personalization signal)
    "touch_position_in_sequence",   # Current position (1-7)
    "is_exploration_slot",          # 1.0 if exploration, 0.0 if exploitation
    "time_since_last_touch_hours",  # Temporal spacing (recency effect)
    "cumulative_mechanism_diversity",  # How many distinct mechanisms tried (0-1 scaled)
    # Enhancement #34: Nonconscious signal intelligence features (5)
    # These capture behavioral processing state that bilateral edge dims
    # cannot represent. Enables Neural-LinUCB to learn context-dependent
    # mechanism effectiveness (e.g., "loss_framing works poorly when
    # processing depth is low because the argument isn't evaluated").
    "processing_depth_weight",         # 0.05 (unprocessed) → 1.0 (deliberate rejection)
    "frustration_score",               # 0-1, dimension conflict level (r=-0.58 with conversion)
    "click_latency_slope",             # Negative = resolving, positive = building reactance
    "organic_surge_multiplier",        # Individual organic ratio / population baseline
    "reactance_h4_modifier",           # -0.10 to +0.30 from frequency decay
    # PCA-compressed dimensions (Session 34-2 CCA follow-up)
    # PC1 alone correlates r=-0.849 with conversion. Including PCs gives
    # LinUCB the conversion axis directly as a feature, plus orthogonal
    # variance components that raw dims don't cleanly separate.
    "pca_pc1",  # Conversion axis: reactance(+), emotion(-), trust(-)
    "pca_pc2",  # Processing depth axis
    "pca_pc3",  # Value-anchor tension axis
    "pca_pc4",  # Identity-signaling axis
    "pca_pc5",  # Ownership-uniqueness axis
    "pca_pc6",  # Disgust sensitivity axis
    "pca_pc7",  # Ownership-distinctiveness axis
]

# Number of mechanism arms
N_MECHANISMS = 16  # From TherapeuticMechanism enum


@dataclass
class LinUCBArm:
    """Per-arm state for LinUCB with d-dimensional context."""

    arm_id: str
    d: int  # Embedding dimension

    # A = d×d matrix (regularized design matrix)
    A: np.ndarray = field(default=None)
    # b = d×1 vector (reward-weighted context sum)
    b: np.ndarray = field(default=None)
    # Observation count
    n_obs: int = 0

    def __post_init__(self):
        if self.A is None:
            self.A = np.eye(self.d)  # Regularization: λI where λ=1
        if self.b is None:
            self.b = np.zeros(self.d)

    def get_ucb(self, context: np.ndarray, alpha: float = 1.0) -> Tuple[float, float]:
        """Compute UCB score for this arm given context embedding.

        Returns (ucb_score, estimated_reward) where:
        - estimated_reward = θ̂ᵀz (ridge regression estimate)
        - ucb_score = estimated_reward + α√(zᵀA⁻¹z) (exploration bonus)
        """
        A_inv = np.linalg.solve(self.A, np.eye(self.d))
        theta = A_inv @ self.b

        estimated_reward = float(theta @ context)
        uncertainty = float(np.sqrt(context @ A_inv @ context))
        ucb_score = estimated_reward + alpha * uncertainty

        return ucb_score, estimated_reward

    def update(self, context: np.ndarray, reward: float) -> None:
        """Update arm statistics with observed (context, reward) pair."""
        self.A += np.outer(context, context)
        self.b += reward * context
        self.n_obs += 1


class RepresentationNetwork:
    """Neural network that maps raw bilateral context to learned embedding.

    Architecture (Xu et al. 2022):
    - Input: 50-dim context (27 alignment + 5 mech + 2 metadata + 10 user + 5 signals + 1 frustration)
    - Hidden: 2 layers with ReLU, BatchNorm, dropout
    - Output: d-dim embedding (default d=16)

    The key insight: LinUCB operates on the LAST LAYER only, giving
    closed-form confidence intervals. The network handles non-linearity,
    LinUCB handles exploration.
    """

    def __init__(self, input_dim: int = len(BILATERAL_CONTEXT_DIMS), embed_dim: int = 16, hidden_dim: int = 64):
        self.input_dim = input_dim
        self.embed_dim = embed_dim
        self.hidden_dim = hidden_dim

        if _TORCH_AVAILABLE:
            self._build_torch_network()
        else:
            self._build_numpy_network()

    def _build_torch_network(self):
        """Build PyTorch representation network."""
        self.net = nn.Sequential(
            nn.Linear(self.input_dim, self.hidden_dim),
            nn.ReLU(),
            nn.BatchNorm1d(self.hidden_dim),
            nn.Dropout(0.1),
            nn.Linear(self.hidden_dim, self.hidden_dim // 2),
            nn.ReLU(),
            nn.BatchNorm1d(self.hidden_dim // 2),
            nn.Linear(self.hidden_dim // 2, self.embed_dim),
        )
        self.net.eval()  # Start in eval mode (no training yet)
        self._mode = "torch"

    def _build_numpy_network(self):
        """Build numpy-only network (random projection fallback).

        When PyTorch isn't available or the network hasn't been trained,
        use a random projection matrix. This is equivalent to Random
        Kitchen Sinks / FastRP — still captures some non-linear structure
        via random features.
        """
        rng = np.random.RandomState(42)
        self.W1 = rng.randn(self.input_dim, self.hidden_dim) * np.sqrt(2.0 / self.input_dim)
        self.b1 = np.zeros(self.hidden_dim)
        self.W2 = rng.randn(self.hidden_dim, self.embed_dim) * np.sqrt(2.0 / self.hidden_dim)
        self.b2 = np.zeros(self.embed_dim)
        self._mode = "numpy"

    def embed(self, context: np.ndarray) -> np.ndarray:
        """Map raw 43-dim context to d-dim embedding.

        Args:
            context: (43,) or (batch, 43) array of bilateral edge features

        Returns:
            (d,) or (batch, d) embedding
        """
        if self._mode == "torch" and _TORCH_AVAILABLE:
            return self._embed_torch(context)
        return self._embed_numpy(context)

    def _embed_torch(self, context: np.ndarray) -> np.ndarray:
        """PyTorch forward pass."""
        with torch.no_grad():
            x = torch.tensor(context, dtype=torch.float32)
            if x.dim() == 1:
                x = x.unsqueeze(0)
            self.net.eval()
            z = self.net(x).numpy()
            if z.shape[0] == 1:
                return z[0]
            return z

    def _embed_numpy(self, context: np.ndarray) -> np.ndarray:
        """Numpy forward pass (random projection + ReLU)."""
        h = np.maximum(0, context @ self.W1 + self.b1)  # ReLU
        z = h @ self.W2 + self.b2
        # L2 normalize for stability
        norm = np.linalg.norm(z)
        if norm > 0:
            z = z / norm
        return z


@dataclass
class NeuralLinUCBResult:
    """Result of Neural-LinUCB mechanism selection."""

    selected_mechanism: str
    ucb_score: float
    estimated_reward: float
    uncertainty: float
    all_scores: Dict[str, float]
    embedding_dim: int
    latency_ms: float
    mode: str  # "torch" or "numpy"


class NeuralLinUCBSelector:
    """Neural-LinUCB mechanism selection engine.

    Composes with the existing BayesianMechanismSelector:
    - When bilateral edge dims are available (L3+): Neural-LinUCB selects
    - When not available (L1-L2): falls back to Thompson Sampling
    - The hierarchical prior provides the BASE reward estimate;
      Neural-LinUCB ADJUSTS it based on the full bilateral context

    Usage:
        selector = NeuralLinUCBSelector()
        result = selector.select(
            bilateral_edge={"emotional_resonance": 0.8, "reactance_fit": 0.1, ...},
            candidate_mechanisms=["evidence_proof", "social_proof_matched", ...],
        )
    """

    def __init__(
        self,
        embed_dim: int = 16,
        alpha: float = 1.0,
        mechanism_list: Optional[List[str]] = None,
    ):
        self.embed_dim = embed_dim
        self.alpha = alpha  # UCB exploration parameter

        # Default mechanism list from constants
        if mechanism_list is None:
            from adam.constants import THERAPEUTIC_MECHANISMS
            mechanism_list = THERAPEUTIC_MECHANISMS

        # Representation network
        input_dim = len(BILATERAL_CONTEXT_DIMS)
        self.rep_net = RepresentationNetwork(
            input_dim=input_dim, embed_dim=embed_dim
        )

        # Per-mechanism LinUCB arms
        self.arms: Dict[str, LinUCBArm] = {
            mech: LinUCBArm(arm_id=mech, d=embed_dim)
            for mech in mechanism_list
        }

        # Feature mean/std for normalization (updated online)
        self._feature_sum = np.zeros(input_dim)
        self._feature_sq_sum = np.zeros(input_dim)
        self._n_contexts = 0

        # Lock to protect arm A/b matrices from concurrent select + update
        self._lock = threading.Lock()

    def select(
        self,
        bilateral_edge: Dict[str, float],
        candidate_mechanisms: Optional[List[str]] = None,
        alpha_override: Optional[float] = None,
    ) -> NeuralLinUCBResult:
        """Select mechanism using Neural-LinUCB.

        Args:
            bilateral_edge: Dict of dimension_name → value (up to 43 dims)
            candidate_mechanisms: Subset of mechanisms to consider
                (from BARRIER_MECHANISM_CANDIDATES). If None, considers all.
            alpha_override: Override the UCB exploration parameter

        Returns:
            NeuralLinUCBResult with selected mechanism and scores
        """
        start = time.time()
        alpha = alpha_override if alpha_override is not None else self.alpha

        # 1. Build raw context vector from bilateral edge
        raw_context = self._build_context_vector(bilateral_edge)

        # 2. Normalize
        context_norm = self._normalize(raw_context)

        # 3. Embed via representation network
        embedding = self.rep_net.embed(context_norm)

        # 4. Compute UCB for each candidate arm (under lock to prevent
        #    concurrent update() from modifying A/b mid-solve)
        with self._lock:
            candidates = candidate_mechanisms or list(self.arms.keys())
            scores: Dict[str, float] = {}
            rewards: Dict[str, float] = {}
            best_mech = candidates[0]
            best_ucb = float("-inf")

            for mech in candidates:
                arm = self.arms.get(mech)
                if arm is None:
                    # Unknown mechanism — create arm on the fly
                    arm = LinUCBArm(arm_id=mech, d=self.embed_dim)
                    self.arms[mech] = arm

                ucb, reward = arm.get_ucb(embedding, alpha=alpha)
                scores[mech] = round(ucb, 4)
                rewards[mech] = round(reward, 4)

                if ucb > best_ucb:
                    best_ucb = ucb
                    best_mech = mech

            best_arm = self.arms[best_mech]
            _, best_reward = best_arm.get_ucb(embedding, alpha=0)
            uncertainty = best_ucb - best_reward

        elapsed_ms = (time.time() - start) * 1000

        return NeuralLinUCBResult(
            selected_mechanism=best_mech,
            ucb_score=round(best_ucb, 4),
            estimated_reward=round(best_reward, 4),
            uncertainty=round(uncertainty, 4),
            all_scores=scores,
            embedding_dim=self.embed_dim,
            latency_ms=round(elapsed_ms, 2),
            mode=self.rep_net._mode,
        )

    def update(
        self,
        bilateral_edge: Dict[str, float],
        mechanism: str,
        reward: float,
    ) -> None:
        """Update arm with observed (context, mechanism, reward) tuple.

        Called after each retargeting outcome. Updates:
        1. The LinUCB arm's A matrix and b vector
        2. The running feature statistics for normalization

        Thread-safe: acquires lock to prevent concurrent select() from
        reading A/b matrices mid-update.
        """
        raw_context = self._build_context_vector(bilateral_edge)
        self._update_stats(raw_context)
        context_norm = self._normalize(raw_context)
        embedding = self.rep_net.embed(context_norm)

        with self._lock:
            arm = self.arms.get(mechanism)
            if arm is None:
                arm = LinUCBArm(arm_id=mechanism, d=self.embed_dim)
                self.arms[mechanism] = arm

            arm.update(embedding, reward)

    def _build_context_vector(self, bilateral_edge: Dict[str, float]) -> np.ndarray:
        """Build ordered context vector from bilateral edge dict.

        Automatically computes PCA features if the DimensionCompressor
        is available and the edge has sufficient raw dimensions.
        """
        enriched = self._enrich_with_pca(bilateral_edge)
        return np.array([
            enriched.get(dim, 0.0) for dim in BILATERAL_CONTEXT_DIMS
        ], dtype=np.float64)

    @staticmethod
    def _enrich_with_pca(edge: Dict[str, float]) -> Dict[str, float]:
        """Add PCA-compressed features to the edge dict if not already present."""
        if "pca_pc1" in edge:
            return edge  # Already enriched

        try:
            from adam.intelligence.dimension_compressor import get_dimension_compressor
            comp = get_dimension_compressor()
            if comp.is_fitted:
                pcs = comp.compress(edge)
                enriched = dict(edge)
                for i, val in enumerate(pcs):
                    enriched[f"pca_pc{i+1}"] = float(val)
                return enriched
        except Exception:
            pass

        return edge

    def _normalize(self, raw: np.ndarray) -> np.ndarray:
        """Online normalization using running mean/std."""
        if self._n_contexts < 2:
            return raw  # Not enough data for normalization
        mean = self._feature_sum / self._n_contexts
        var = self._feature_sq_sum / self._n_contexts - mean ** 2
        std = np.sqrt(np.maximum(var, 1e-8))
        return (raw - mean) / std

    def _update_stats(self, raw: np.ndarray) -> None:
        """Update running feature statistics for normalization."""
        self._feature_sum += raw
        self._feature_sq_sum += raw ** 2
        self._n_contexts += 1

    @property
    def stats(self) -> Dict[str, Any]:
        """Summary statistics for monitoring."""
        arm_stats = {}
        for mech, arm in self.arms.items():
            if arm.n_obs > 0:
                A_inv = np.linalg.solve(arm.A, np.eye(arm.d))
                theta = A_inv @ arm.b
                arm_stats[mech] = {
                    "n_obs": arm.n_obs,
                    "theta_norm": float(np.linalg.norm(theta)),
                }
        return {
            "total_contexts": self._n_contexts,
            "embed_dim": self.embed_dim,
            "mode": self.rep_net._mode,
            "active_arms": len(arm_stats),
            "arms": arm_stats,
        }
