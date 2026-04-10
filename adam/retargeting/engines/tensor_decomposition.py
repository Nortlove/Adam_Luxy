# =============================================================================
# Tensor CP Decomposition of Bilateral Edges
# Location: adam/retargeting/engines/tensor_decomposition.py
# Enhancement #34, Session 34-7
# =============================================================================

"""
Tensor CP decomposition discovers bilateral alignment archetypes from data.

Constructs a 3-way tensor T ∈ ℝ^{d_buyer × d_seller × K} where each slice
represents the average alignment profile for a (buyer_dim_bin, seller_dim_bin)
combination, stratified by conversion outcome.

CP decomposition factorizes T into rank-one components, each representing
a bilateral alignment archetype — a pattern of buyer×seller dimension
co-occurrence that predicts conversion.

Why this matters: Enhancement #33's k-means archetypes (careful_truster,
status_seeker, etc.) were computed on buyer dimensions only. Tensor
decomposition discovers archetypes in the BILATERAL space — patterns
that include both buyer AND seller characteristics simultaneously.

Validation: Compare tensor-discovered archetypes against k-means clusters.
If they diverge, the bilateral patterns contain structure not captured by
buyer-only clustering.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Try tensorly; fall back to SVD-based approximation
try:
    import tensorly as tl
    from tensorly.decomposition import parafac
    _TENSORLY_AVAILABLE = True
except ImportError:
    _TENSORLY_AVAILABLE = False
    logger.info("TensorLy not available. Using SVD-based tensor approximation.")


@dataclass
class TensorArchetype:
    """A bilateral alignment archetype discovered via CP decomposition."""

    rank: int  # Component index (0-based)
    weight: float  # Component weight (eigenvalue analog)

    # Factor vectors: what buyer/seller/outcome patterns define this archetype
    buyer_factor: Dict[str, float]  # dim_name → loading
    seller_factor: Dict[str, float]  # dim_name → loading (mechanism scores)
    outcome_factor: Dict[str, float]  # outcome → loading

    # Interpretation
    dominant_buyer_dims: List[Tuple[str, float]]  # Top 5 buyer dims by |loading|
    dominant_seller_dims: List[Tuple[str, float]]  # Top 5 seller dims
    conversion_tendency: float  # Positive = converts, negative = doesn't

    # Comparison to k-means
    closest_kmeans_archetype: str = ""
    kmeans_similarity: float = 0.0


@dataclass
class TensorDecompositionResult:
    """Complete result of tensor CP decomposition."""

    archetypes: List[TensorArchetype]
    optimal_rank: int
    reconstruction_error: float
    explained_variance: float
    tensor_shape: Tuple[int, ...]
    n_edges: int

    # Elbow analysis
    rank_errors: Dict[int, float] = field(default_factory=dict)


# Buyer-side dimensions (from bilateral edges)
BUYER_DIMS = [
    "emotional_resonance", "brand_trust_fit", "regulatory_fit_score",
    "personality_brand_alignment", "appeal_resonance", "reactance_fit",
    "negativity_bias_match", "spending_pain_match", "processing_route_match",
    "optimal_distinctiveness_fit", "value_alignment", "evolutionary_motive_match",
]

# Seller-side dimensions (mechanism effectiveness scores on edges)
SELLER_DIMS = [
    "mech_social_proof", "mech_authority", "mech_reciprocity",
    "mech_commitment", "mech_liking",
]

# Outcome bins
OUTCOME_MAP = {
    "evangelized": 2,   # Strong positive
    "satisfied": 1,     # Positive
    "neutral": 0,       # Neutral
    "warned": -1,       # Negative
    "regret": -2,       # Strong negative
}

N_OUTCOME_BINS = 3  # Positive (evangelized+satisfied), Neutral, Negative (warned+regret)


class BilateralTensorDecomposer:
    """Discovers bilateral alignment archetypes via CP decomposition.

    Usage:
        decomposer = BilateralTensorDecomposer()
        result = decomposer.decompose(edges, max_rank=8)
        for archetype in result.archetypes:
            print(archetype.dominant_buyer_dims)
    """

    def __init__(self, n_bins: int = 3):
        """
        Args:
            n_bins: Number of bins per dimension for discretization.
                    3 = terciles (low/medium/high). More bins = finer
                    resolution but sparser tensor.
        """
        self.n_bins = n_bins

    def decompose(
        self,
        edges: List[Dict],
        max_rank: int = 8,
        min_rank: int = 2,
    ) -> TensorDecompositionResult:
        """Run CP decomposition on bilateral edges.

        Args:
            edges: List of edge dicts with buyer/seller/outcome dims
            max_rank: Maximum CP rank to test
            min_rank: Minimum CP rank

        Returns:
            TensorDecompositionResult with discovered archetypes
        """
        # 1. Build tensor
        tensor, buyer_vals, seller_vals = self._build_tensor(edges)
        logger.info(
            "Tensor shape: %s (buyer=%d × seller=%d × outcome=%d)",
            tensor.shape, tensor.shape[0], tensor.shape[1], tensor.shape[2],
        )

        # 2. Find optimal rank via elbow method
        rank_errors = {}
        for rank in range(min_rank, max_rank + 1):
            error = self._decompose_at_rank(tensor, rank)
            rank_errors[rank] = error

        optimal_rank = self._find_elbow(rank_errors)
        logger.info("Optimal rank: %d (from elbow analysis)", optimal_rank)

        # 3. Decompose at optimal rank
        factors, weights = self._full_decomposition(tensor, optimal_rank)

        # 4. Build archetype descriptions
        archetypes = self._build_archetypes(
            factors, weights, buyer_vals, seller_vals, edges
        )

        # 5. Compute explained variance
        reconstruction = self._reconstruct(factors, weights, tensor.shape)
        total_var = np.sum(tensor ** 2)
        residual_var = np.sum((tensor - reconstruction) ** 2)
        explained = 1.0 - residual_var / max(total_var, 1e-10)

        return TensorDecompositionResult(
            archetypes=archetypes,
            optimal_rank=optimal_rank,
            reconstruction_error=rank_errors.get(optimal_rank, 0),
            explained_variance=round(float(explained), 4),
            tensor_shape=tensor.shape,
            n_edges=len(edges),
            rank_errors=rank_errors,
        )

    def _build_tensor(
        self, edges: List[Dict]
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Build 3-way tensor from edges.

        Discretizes buyer and seller dims into bins, counts conversion
        outcomes per (buyer_bin, seller_bin) cell.
        """
        n_buyer = len(BUYER_DIMS)
        n_seller = len(SELLER_DIMS)

        # Extract raw values
        buyer_matrix = np.array([
            [e.get(d, 0.5) for d in BUYER_DIMS] for e in edges
        ])
        seller_matrix = np.array([
            [e.get(d, 0.0) for d in SELLER_DIMS] for e in edges
        ])

        # Map outcomes to bins: 0=negative, 1=neutral, 2=positive
        outcomes = []
        for e in edges:
            out = e.get("outcome", "neutral")
            if out in ("evangelized", "satisfied"):
                outcomes.append(2)
            elif out in ("warned", "regret"):
                outcomes.append(0)
            else:
                outcomes.append(1)
        outcomes = np.array(outcomes)

        # Build tensor using average alignment per cell
        # For simplicity: use the raw (n_edges × n_buyer) and (n_edges × n_seller)
        # matrices directly, with outcome as the third mode
        tensor = np.zeros((n_buyer, n_seller, N_OUTCOME_BINS))

        for outcome_bin in range(N_OUTCOME_BINS):
            mask = outcomes == outcome_bin
            if mask.sum() > 0:
                b_sub = buyer_matrix[mask]
                s_sub = seller_matrix[mask]
                # Outer product averaged: captures buyer×seller co-occurrence
                for i in range(mask.sum()):
                    tensor[:, :, outcome_bin] += np.outer(b_sub[i], s_sub[i])
                tensor[:, :, outcome_bin] /= mask.sum()

        return tensor, buyer_matrix, seller_matrix

    def _decompose_at_rank(self, tensor: np.ndarray, rank: int) -> float:
        """Decompose and return reconstruction error."""
        try:
            factors, weights = self._full_decomposition(tensor, rank)
            reconstruction = self._reconstruct(factors, weights, tensor.shape)
            error = float(np.sqrt(np.sum((tensor - reconstruction) ** 2)))
            return error
        except Exception:
            return float("inf")

    def _full_decomposition(
        self, tensor: np.ndarray, rank: int
    ) -> Tuple[List[np.ndarray], np.ndarray]:
        """Run CP decomposition at given rank."""
        if _TENSORLY_AVAILABLE:
            result = parafac(tl.tensor(tensor), rank=rank, init="random", random_state=42)
            weights = result.weights if hasattr(result, 'weights') else np.ones(rank)
            factors = [f for f in result.factors]
            return factors, np.array(weights)

        # SVD-based approximation (mode-1 unfolding → truncated SVD)
        # Less accurate than true CP but works without tensorly
        unfolded = tensor.reshape(tensor.shape[0], -1)
        U, S, Vt = np.linalg.svd(unfolded, full_matrices=False)

        actual_rank = min(rank, len(S))
        weights = S[:actual_rank]
        factor_buyer = U[:, :actual_rank]
        factor_rest = Vt[:actual_rank, :].reshape(actual_rank, tensor.shape[1], tensor.shape[2])

        # Approximate seller and outcome factors
        factor_seller = factor_rest[:, :, 0].T if tensor.shape[2] > 0 else np.zeros((tensor.shape[1], actual_rank))
        factor_outcome = factor_rest[:, 0, :].T if tensor.shape[1] > 0 else np.zeros((tensor.shape[2], actual_rank))

        return [factor_buyer, factor_seller, factor_outcome], weights

    def _reconstruct(
        self,
        factors: List[np.ndarray],
        weights: np.ndarray,
        shape: Tuple[int, ...],
    ) -> np.ndarray:
        """Reconstruct tensor from factors."""
        rank = len(weights)
        result = np.zeros(shape)
        for r in range(min(rank, factors[0].shape[1] if len(factors[0].shape) > 1 else 1)):
            w = weights[r] if r < len(weights) else 1.0
            if len(factors) >= 3 and all(f.shape[1] > r if len(f.shape) > 1 else f.shape[0] > r for f in factors):
                a = factors[0][:, r] if len(factors[0].shape) > 1 else factors[0]
                b = factors[1][:, r] if len(factors[1].shape) > 1 else factors[1]
                c = factors[2][:, r] if len(factors[2].shape) > 1 else factors[2]
                result += w * np.einsum('i,j,k', a, b, c)
        return result

    def _find_elbow(self, rank_errors: Dict[int, float]) -> int:
        """Find elbow point in rank vs reconstruction error curve."""
        ranks = sorted(rank_errors.keys())
        errors = [rank_errors[r] for r in ranks]

        if len(errors) < 3:
            return ranks[0]

        # Simple elbow: largest second derivative
        best_rank = ranks[0]
        best_curvature = 0.0
        for i in range(1, len(errors) - 1):
            curvature = errors[i - 1] - 2 * errors[i] + errors[i + 1]
            if curvature > best_curvature:
                best_curvature = curvature
                best_rank = ranks[i]

        return best_rank

    def _build_archetypes(
        self,
        factors: List[np.ndarray],
        weights: np.ndarray,
        buyer_vals: np.ndarray,
        seller_vals: np.ndarray,
        edges: List[Dict],
    ) -> List[TensorArchetype]:
        """Build human-readable archetype descriptions from factors."""
        archetypes = []
        rank = min(len(weights), factors[0].shape[1] if len(factors[0].shape) > 1 else 1)

        for r in range(rank):
            # Extract factor vectors for this component
            buyer_f = factors[0][:, r] if len(factors[0].shape) > 1 else factors[0]
            seller_f = factors[1][:, r] if len(factors[1].shape) > 1 else factors[1]
            outcome_f = factors[2][:, r] if len(factors[2].shape) > 1 else factors[2]

            # Map to dimension names
            buyer_dict = {BUYER_DIMS[i]: round(float(buyer_f[i]), 4)
                         for i in range(min(len(BUYER_DIMS), len(buyer_f)))}
            seller_dict = {SELLER_DIMS[i]: round(float(seller_f[i]), 4)
                          for i in range(min(len(SELLER_DIMS), len(seller_f)))}
            outcome_dict = {
                "positive": round(float(outcome_f[2]), 4) if len(outcome_f) > 2 else 0,
                "neutral": round(float(outcome_f[1]), 4) if len(outcome_f) > 1 else 0,
                "negative": round(float(outcome_f[0]), 4) if len(outcome_f) > 0 else 0,
            }

            # Sort by absolute loading
            dominant_buyer = sorted(
                buyer_dict.items(), key=lambda x: abs(x[1]), reverse=True
            )[:5]
            dominant_seller = sorted(
                seller_dict.items(), key=lambda x: abs(x[1]), reverse=True
            )[:5]

            # Conversion tendency: positive outcome loading minus negative
            conv_tendency = outcome_dict.get("positive", 0) - outcome_dict.get("negative", 0)

            archetypes.append(TensorArchetype(
                rank=r,
                weight=round(float(weights[r]), 4),
                buyer_factor=buyer_dict,
                seller_factor=seller_dict,
                outcome_factor=outcome_dict,
                dominant_buyer_dims=dominant_buyer,
                dominant_seller_dims=dominant_seller,
                conversion_tendency=round(float(conv_tendency), 4),
            ))

        # Sort by weight (importance)
        archetypes.sort(key=lambda a: abs(a.weight), reverse=True)
        return archetypes
