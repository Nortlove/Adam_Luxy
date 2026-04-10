# =============================================================================
# Page Gradient Fields — ∂P(conversion)/∂(page_dimension)
# Location: adam/intelligence/page_gradient_fields.py
# =============================================================================

"""
Computes how each page psychological dimension affects conversion
probability for a given (mechanism, barrier) cell.

This is the page-side equivalent of gradient_fields.py (buyer-side).
While buyer gradients tell you "which buyer dimensions matter for conversion,"
page gradients tell you "which PAGE dimensions matter for THIS mechanism
to work against THIS barrier."

Example output:
    For (evidence_proof, trust_deficit):
        cognitive_load_tolerance: +0.35  (analytical pages amplify evidence)
        emotional_resonance: -0.12      (emotional pages dampen evidence)
        autonomy_respect: +0.22         (low-pressure pages help trust)

This tells PlacementOptimizer: bid higher on pages with high
cognitive_load_tolerance when deploying evidence_proof against trust_deficit.

Computation: Logistic regression on accumulated observations.
Minimum 50 observations per cell before gradients are computed.
Updated daily via the strengthening scheduler.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Same 20 dimensions as bilateral cascade and page similarity index
PAGE_DIMENSIONS = [
    "regulatory_fit", "construal_fit", "personality_alignment",
    "emotional_resonance", "value_alignment", "evolutionary_motive",
    "persuasion_confidence", "persuasion_susceptibility",
    "cognitive_load_tolerance", "narrative_transport",
    "social_proof_sensitivity", "loss_aversion_intensity",
    "temporal_discounting", "brand_relationship_depth",
    "autonomy_reactance", "information_seeking", "mimetic_desire",
    "interoceptive_awareness", "cooperative_framing_fit",
    "decision_entropy",
]

MIN_OBSERVATIONS = 50  # Minimum before computing gradients


@dataclass
class PageGradientField:
    """Gradient field for a (mechanism, barrier) cell."""

    mechanism: str
    barrier: str
    gradients: Dict[str, float]  # dimension → ∂P/∂dim
    n_observations: int = 0
    computed_at: float = field(default_factory=time.time)

    @property
    def top_dimensions(self) -> List[Tuple[str, float]]:
        """Top 5 dimensions by absolute gradient magnitude."""
        return sorted(
            self.gradients.items(),
            key=lambda x: abs(x[1]),
            reverse=True,
        )[:5]

    @property
    def is_valid(self) -> bool:
        return self.n_observations >= MIN_OBSERVATIONS


class PageGradientAccumulator:
    """Accumulates page × mechanism × barrier observations for gradient computation.

    Each observation is a (page_vector_20d, mechanism, barrier, converted) tuple.
    Stored in-memory with periodic Redis persistence.
    """

    def __init__(self):
        # Key: (mechanism, barrier) → list of (page_vector, outcome)
        self._observations: Dict[Tuple[str, str], List[Tuple[np.ndarray, float]]] = {}
        self._computed_gradients: Dict[Tuple[str, str], PageGradientField] = {}

    def record_observation(
        self,
        page_dimensions: Dict[str, float],
        mechanism: str,
        barrier: str,
        converted: bool,
    ) -> None:
        """Record a single page × mechanism × barrier outcome."""
        vec = np.array([page_dimensions.get(d, 0.5) for d in PAGE_DIMENSIONS])
        outcome = 1.0 if converted else 0.0
        key = (mechanism, barrier)

        if key not in self._observations:
            self._observations[key] = []
        self._observations[key].append((vec, outcome))

        # Cap at 10K observations per cell (rolling window)
        if len(self._observations[key]) > 10_000:
            self._observations[key] = self._observations[key][-10_000:]

    def compute_gradients(
        self,
        mechanism: str,
        barrier: str,
    ) -> Optional[PageGradientField]:
        """Compute gradient field for a (mechanism, barrier) cell.

        Uses logistic regression: P(conversion) = sigmoid(w · page_vector + b)
        The weights w are the gradients: ∂P/∂(page_dim_i).

        Returns None if insufficient observations.
        """
        key = (mechanism, barrier)
        obs = self._observations.get(key, [])

        if len(obs) < MIN_OBSERVATIONS:
            return None

        X = np.stack([v for v, _ in obs])
        y = np.array([o for _, o in obs])

        # Check for degenerate cases (all same outcome)
        if y.std() < 0.01:
            return None

        # Simple logistic regression via gradient descent
        # (avoids sklearn dependency)
        n_dims = X.shape[1]
        w = np.zeros(n_dims)
        b = 0.0
        lr = 0.01
        n_iter = 200

        for _ in range(n_iter):
            z = X @ w + b
            pred = 1.0 / (1.0 + np.exp(-np.clip(z, -10, 10)))
            error = pred - y
            w -= lr * (X.T @ error) / len(y)
            b -= lr * error.mean()

        # Map weights to dimension names
        gradients = {
            PAGE_DIMENSIONS[i]: float(w[i])
            for i in range(n_dims)
        }

        field = PageGradientField(
            mechanism=mechanism,
            barrier=barrier,
            gradients=gradients,
            n_observations=len(obs),
        )
        self._computed_gradients[key] = field

        logger.info(
            "Page gradient computed: %s × %s (n=%d). Top dims: %s",
            mechanism, barrier, len(obs),
            [(d, f"{g:.3f}") for d, g in field.top_dimensions[:3]],
        )
        return field

    def compute_all_gradients(self) -> Dict[str, PageGradientField]:
        """Compute gradients for all cells with sufficient data.

        Called daily by the strengthening scheduler.
        """
        computed = {}
        for (mechanism, barrier), obs in self._observations.items():
            if len(obs) >= MIN_OBSERVATIONS:
                field = self.compute_gradients(mechanism, barrier)
                if field:
                    computed[f"{mechanism}:{barrier}"] = field
        return computed

    def get_gradient(
        self, mechanism: str, barrier: str
    ) -> Optional[PageGradientField]:
        """Get pre-computed gradient field for a cell."""
        return self._computed_gradients.get((mechanism, barrier))

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "cells_observed": len(self._observations),
            "total_observations": sum(
                len(v) for v in self._observations.values()
            ),
            "cells_computed": len(self._computed_gradients),
            "cells_with_enough_data": sum(
                1 for obs in self._observations.values()
                if len(obs) >= MIN_OBSERVATIONS
            ),
        }


# =============================================================================
# SINGLETON
# =============================================================================

_accumulator: Optional[PageGradientAccumulator] = None


def get_page_gradient_accumulator() -> PageGradientAccumulator:
    global _accumulator
    if _accumulator is None:
        _accumulator = PageGradientAccumulator()
    return _accumulator
