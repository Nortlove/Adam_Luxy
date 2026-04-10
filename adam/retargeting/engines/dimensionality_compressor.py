# =============================================================================
# Information Bottleneck Dimensionality Compression
# Location: adam/retargeting/engines/dimensionality_compressor.py
# Enhancement #34, Session 34-11
# =============================================================================

"""
Profile compression based on Information Bottleneck / PCA analysis.

Session 34-2 diagnostic found: 7 PCA components capture 90% of variance
in the 24 bilateral alignment dimensions. The system is over-parameterized.

This compressor:
1. Fits PCA on bilateral edge data to learn the 7 principal directions
2. Projects new edges to the compressed 7-dim space for faster inference
3. Reconstructs back to full 24-dim space for interpretability
4. Tracks which original dimensions load on which components

Benefits:
- Faster Neural-LinUCB: 7-dim input instead of 43-dim (6× smaller embedding)
- Better generalization: removes noise dimensions
- Interpretable: each component has named dimension loadings
- Fallback: can always use full dimensions if compression loses signal

Integration: Sits between bilateral edge extraction and mechanism selection.
Compressed representation used by Neural-LinUCB; full representation used
by barrier diagnostic (which needs individual dimension values for gap analysis).
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CompressedProfile:
    """A bilateral edge profile in the compressed space."""

    components: np.ndarray  # (n_components,) compressed representation
    n_components: int
    explained_variance: float  # How much of original variance is captured
    reconstruction_error: float  # MSE of reconstruction vs original

    # Interpretability: which original dims load on which components
    top_loadings_per_component: List[List[Tuple[str, float]]] = field(
        default_factory=list
    )


@dataclass
class CompressionFitResult:
    """Result of fitting the compressor to data."""

    n_components: int
    n_samples: int
    explained_variance_ratio: List[float]  # Per-component
    cumulative_variance: List[float]
    total_explained: float

    # Per-component interpretation
    component_names: List[str]  # Human-readable names for each component
    component_loadings: List[Dict[str, float]]  # dim_name → loading per component


class BilateralProfileCompressor:
    """PCA-based bilateral profile compression.

    Learns principal directions from bilateral edge data, then projects
    new edges to compressed space. Designed for the Information Bottleneck
    principle: compress psychological profile while preserving conversion-
    relevant information.

    Usage:
        compressor = BilateralProfileCompressor(n_components=7)
        fit_result = compressor.fit(edges)
        compressed = compressor.compress(new_edge)
        reconstructed = compressor.reconstruct(compressed)
    """

    def __init__(
        self,
        n_components: int = 7,
        dimension_names: Optional[List[str]] = None,
    ):
        self.n_components = n_components
        self.dim_names = dimension_names or self._default_dims()

        # PCA parameters (set by fit())
        self._mean: Optional[np.ndarray] = None
        self._std: Optional[np.ndarray] = None
        self._components: Optional[np.ndarray] = None  # (n_components, n_dims)
        self._explained_variance_ratio: Optional[np.ndarray] = None
        self._fitted = False

    def fit(self, edges: List[Dict]) -> CompressionFitResult:
        """Fit PCA on bilateral edge data.

        Args:
            edges: List of edge dicts with alignment dimensions

        Returns:
            CompressionFitResult with variance analysis and loadings
        """
        # Build matrix
        X = self._edges_to_matrix(edges)
        n_samples, n_dims = X.shape
        logger.info("Fitting compressor: %d samples × %d dims → %d components",
                     n_samples, n_dims, self.n_components)

        # Standardize
        self._mean = X.mean(axis=0)
        self._std = X.std(axis=0)
        self._std[self._std < 1e-8] = 1.0
        X_norm = (X - self._mean) / self._std

        # SVD
        U, S, Vt = np.linalg.svd(X_norm, full_matrices=False)

        # Select components
        actual_n = min(self.n_components, len(S))
        self._components = Vt[:actual_n]  # (n_components, n_dims)
        total_var = (S ** 2).sum()
        var_ratio = (S[:actual_n] ** 2) / total_var
        self._explained_variance_ratio = var_ratio
        self._fitted = True

        # Build loadings (which original dims load on which components)
        component_loadings = []
        component_names = []
        for i in range(actual_n):
            loadings = {
                self.dim_names[j]: round(float(self._components[i, j]), 4)
                for j in range(min(len(self.dim_names), n_dims))
            }
            component_loadings.append(loadings)

            # Name component by top 2 loading dimensions
            top2 = sorted(loadings.items(), key=lambda x: abs(x[1]), reverse=True)[:2]
            name = f"PC{i+1}_{top2[0][0][:15]}_{top2[1][0][:15]}"
            component_names.append(name)

        cumulative = np.cumsum(var_ratio).tolist()

        return CompressionFitResult(
            n_components=actual_n,
            n_samples=n_samples,
            explained_variance_ratio=[round(float(v), 4) for v in var_ratio],
            cumulative_variance=[round(float(c), 4) for c in cumulative],
            total_explained=round(float(cumulative[-1]), 4),
            component_names=component_names,
            component_loadings=component_loadings,
        )

    def compress(self, edge: Dict[str, float]) -> CompressedProfile:
        """Project a single bilateral edge to compressed space.

        Args:
            edge: Dict of dim_name → value

        Returns:
            CompressedProfile with n_components values
        """
        if not self._fitted:
            raise RuntimeError("Compressor not fitted. Call fit() first.")

        x = np.array([edge.get(d, 0.5) for d in self.dim_names])
        x_norm = (x - self._mean) / self._std

        # Project
        z = x_norm @ self._components.T  # (n_components,)

        # Reconstruction error
        x_recon = z @ self._components
        x_recon_raw = x_recon * self._std + self._mean
        recon_error = float(np.mean((x - x_recon_raw) ** 2))

        # Top loadings per component for interpretability
        top_loadings = []
        for i in range(self._components.shape[0]):
            sorted_loadings = sorted(
                [(self.dim_names[j], float(self._components[i, j]))
                 for j in range(len(self.dim_names))],
                key=lambda x: abs(x[1]), reverse=True,
            )
            top_loadings.append(sorted_loadings[:3])

        return CompressedProfile(
            components=z,
            n_components=len(z),
            explained_variance=float(self._explained_variance_ratio.sum()),
            reconstruction_error=round(recon_error, 6),
            top_loadings_per_component=top_loadings,
        )

    def reconstruct(self, compressed: CompressedProfile) -> Dict[str, float]:
        """Reconstruct full-dimensional profile from compressed.

        Useful for interpretability: see what the compressed representation
        "thinks" the full profile looks like.
        """
        if not self._fitted:
            raise RuntimeError("Compressor not fitted.")

        z = compressed.components
        x_norm = z @ self._components
        x_raw = x_norm * self._std + self._mean

        return {
            self.dim_names[i]: round(float(x_raw[i]), 4)
            for i in range(len(self.dim_names))
        }

    def compress_batch(self, edges: List[Dict[str, float]]) -> np.ndarray:
        """Compress a batch of edges. Returns (n_edges, n_components) array."""
        if not self._fitted:
            raise RuntimeError("Compressor not fitted.")

        X = self._edges_to_matrix(edges)
        X_norm = (X - self._mean) / self._std
        return X_norm @ self._components.T

    def _edges_to_matrix(self, edges: List[Dict]) -> np.ndarray:
        """Convert edge dicts to numpy matrix."""
        return np.array([
            [e.get(d, 0.5) for d in self.dim_names]
            for e in edges
        ])

    @staticmethod
    def _default_dims() -> List[str]:
        """Default bilateral alignment dimension names."""
        return [
            "regulatory_fit_score", "construal_fit_score",
            "personality_brand_alignment", "emotional_resonance",
            "value_alignment", "evolutionary_motive_match",
            "appeal_resonance", "processing_route_match",
            "implicit_driver_match", "lay_theory_alignment",
            "linguistic_style_match", "identity_signaling_match",
            "full_cosine_alignment", "uniqueness_popularity_fit",
            "mental_simulation_resonance", "involvement_weight_modifier",
            "negativity_bias_match", "reactance_fit",
            "optimal_distinctiveness_fit", "brand_trust_fit",
            "self_monitoring_fit", "spending_pain_match",
            "anchor_susceptibility_match", "mental_ownership_match",
        ]

    @property
    def is_fitted(self) -> bool:
        return self._fitted
