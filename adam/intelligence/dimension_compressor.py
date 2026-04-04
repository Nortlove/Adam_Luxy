# =============================================================================
# Dimension Compressor — PCA-based alignment dimension reduction
# Location: adam/intelligence/dimension_compressor.py
# Session 34-2 CCA follow-up: 25 raw dims → 7 principal components
# =============================================================================

"""
Reduces 25 bilateral alignment dimensions to 7 principal components
for hot-path computation (barrier diagnosis, mechanism selection,
Neural-LinUCB context).

Derived from PCA on 1,492 LUXY Ride bilateral edges.

Key finding: PC1 (r=-0.849 with conversion) is the "conversion axis":
  - reactance_fit (+0.35): high reactance → non-conversion
  - emotional_resonance (-0.35): high emotion → conversion
  - brand_trust_fit (-0.34): high trust → conversion
  - negativity_bias_match (+0.32): high negativity → non-conversion

The full 25 dimensions are preserved for:
  - Learning pipeline (posterior updates need per-dimension granularity)
  - Audit/analysis (interpretability requires named dimensions)
  - Frustration scoring (dimension-pair correlations need raw dims)

The 7 PCs are used for:
  - Fast composite scoring (7 dot products vs 25)
  - Neural-LinUCB compressed context (reduces arm matrix from 50×50 to 32×32)
  - Real-time barrier classification
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Default path to pre-computed PCA loadings
_DEFAULT_LOADINGS_PATH = Path(__file__).parent.parent / "data" / "pca_loadings_25d.json"


class DimensionCompressor:
    """PCA-based compression of bilateral alignment dimensions.

    Fitted on LUXY Ride data. Loadings are stored in a JSON file
    and loaded at startup. No online learning — refit when the
    corpus changes significantly.
    """

    def __init__(self, loadings_path: Optional[str] = None):
        path = Path(loadings_path) if loadings_path else _DEFAULT_LOADINGS_PATH
        self._loadings_path = path
        self._fitted = False

        # PCA parameters
        self.dimensions: List[str] = []
        self.mean: np.ndarray = np.array([])
        self.std: np.ndarray = np.array([])
        self.loadings: np.ndarray = np.array([])  # (n_components, n_dims)
        self.n_components: int = 0
        self.explained_variance: List[float] = []

        self._load()

    def _load(self) -> None:
        """Load pre-computed PCA loadings from JSON."""
        if not self._loadings_path.exists():
            logger.warning("PCA loadings not found at %s", self._loadings_path)
            return

        with open(self._loadings_path) as f:
            data = json.load(f)

        self.dimensions = data["dimensions"]
        self.mean = np.array(data["mean"])
        self.std = np.array(data["std"])
        self.loadings = np.array(data["loadings_7pc"])
        self.n_components = data["n_components"]
        self.explained_variance = data["explained_variance"]
        self._fitted = True

        logger.info(
            "DimensionCompressor loaded: %d dims → %d PCs (%.1f%% variance)",
            len(self.dimensions),
            self.n_components,
            sum(self.explained_variance) * 100,
        )

    @property
    def is_fitted(self) -> bool:
        return self._fitted

    def compress(self, edge_dimensions: Dict[str, float]) -> np.ndarray:
        """Compress a bilateral edge dict into 7 principal components.

        Args:
            edge_dimensions: Dict of dimension_name → value.

        Returns:
            np.ndarray of shape (n_components,) — the PC scores.
            Returns zeros if not fitted.
        """
        if not self._fitted:
            return np.zeros(self.n_components or 7)

        # Build raw vector in the correct dimension order
        raw = np.array([
            edge_dimensions.get(dim, 0.0) for dim in self.dimensions
        ])

        # Standardize using fitted mean/std
        standardized = (raw - self.mean) / self.std

        # Project onto principal components
        return self.loadings @ standardized

    def compress_to_dict(self, edge_dimensions: Dict[str, float]) -> Dict[str, float]:
        """Compress and return as a named dict.

        Returns dict like {"pc1": -1.23, "pc2": 0.45, ...}.
        """
        scores = self.compress(edge_dimensions)
        return {f"pc{i+1}": round(float(scores[i]), 4) for i in range(len(scores))}

    def get_conversion_score(self, edge_dimensions: Dict[str, float]) -> float:
        """Fast conversion likelihood estimate using PC1 alone.

        PC1 correlates r=-0.849 with conversion. Higher PC1 = less likely
        to convert (high reactance, low trust, low emotion).

        Returns a 0-1 score where 1.0 = high conversion likelihood.
        """
        if not self._fitted:
            return 0.5

        scores = self.compress(edge_dimensions)
        # PC1 is anti-correlated: negate and sigmoid-normalize
        raw = -scores[0]
        return float(1.0 / (1.0 + np.exp(-raw)))

    def get_pc_interpretation(self) -> List[Dict]:
        """Get human-readable interpretation of each PC."""
        if not self._fitted:
            return []

        interpretations = []
        for i in range(self.n_components):
            loadings_i = self.loadings[i]
            top_idx = np.argsort(np.abs(loadings_i))[-3:][::-1]
            top_dims = [
                {"dimension": self.dimensions[j], "loading": round(float(loadings_i[j]), 3)}
                for j in top_idx
            ]
            interpretations.append({
                "pc": i + 1,
                "explained_variance": round(self.explained_variance[i] * 100, 1),
                "top_dimensions": top_dims,
            })
        return interpretations


# Singleton
_compressor: Optional[DimensionCompressor] = None


def get_dimension_compressor() -> DimensionCompressor:
    """Get the singleton DimensionCompressor."""
    global _compressor
    if _compressor is None:
        _compressor = DimensionCompressor()
    return _compressor
