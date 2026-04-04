# =============================================================================
# Frustration Scorer — Dimension Conflict Analysis
# Location: adam/retargeting/engines/frustration.py
# Session 34-2: Empirically validated from 754 converted LUXY Ride edges
# =============================================================================

"""
Computes per-edge frustration score from bilateral alignment dimensions.

Frustration arises when satisfying one alignment dimension makes another
worse. Among 754 converted LUXY Ride edges, 27 dimension pairs show
strong negative correlation (r < -0.3). Aggregate frustration score
predicts non-conversion with r = -0.582 (p < 0.0001).

The dominant frustrator is anchor_susceptibility_match — price anchoring
competes with 9 other dimensions (emotional resonance, value alignment,
mental simulation, personality, uniqueness, identity, lay theory, etc.).
This means price-focused messaging suppresses emotional/trust appeal
and vice versa. The retargeting planner must ADDRESS THEM SEQUENTIALLY.

Uses:
1. Score individual edges to predict conversion difficulty
2. Identify which dimension pairs are in tension for a specific buyer
3. Plan sequential mechanism deployment (resolve one side first)
4. Inform the DiagnosticReasoner: high frustration → H2/H3 modifiers
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from adam.constants import FRUSTRATED_DIMENSION_PAIRS

logger = logging.getLogger(__name__)


# =============================================================================
# PRE-COMPUTED INDEX
# =============================================================================

# Build bidirectional lookup: dimension → [(partner_dim, correlation)]
_FRUSTRATED_INDEX: Dict[str, List[Tuple[str, float]]] = {}
for _dim_a, _dim_b, _corr in FRUSTRATED_DIMENSION_PAIRS:
    _FRUSTRATED_INDEX.setdefault(_dim_a, []).append((_dim_b, _corr))
    _FRUSTRATED_INDEX.setdefault(_dim_b, []).append((_dim_a, _corr))

# Set of all frustrated dimension names for quick membership test
FRUSTRATED_DIMENSIONS = set(_FRUSTRATED_INDEX.keys())


# =============================================================================
# FRUSTRATION SCORER
# =============================================================================

class FrustrationScorer:
    """Computes frustration scores and identifies tension points.

    Frustration score = sum of |dim_a - dim_b| for all frustrated pairs
    where both dimensions are present. Higher = more internal conflict
    in the alignment profile, harder to convert.
    """

    def __init__(self):
        self._index = _FRUSTRATED_INDEX
        self._pairs = FRUSTRATED_DIMENSION_PAIRS

    def score(self, edge_dimensions: Dict[str, float]) -> float:
        """Compute aggregate frustration score for an edge.

        Args:
            edge_dimensions: Dict of dimension_name → value (0-1).

        Returns:
            Frustration score (0 = no frustration, higher = more conflict).
            Normalized to [0, 1] range based on number of scoreable pairs.
        """
        total = 0.0
        max_possible = 0.0

        for dim_a, dim_b, corr in self._pairs:
            val_a = edge_dimensions.get(dim_a)
            val_b = edge_dimensions.get(dim_b)
            if val_a is not None and val_b is not None:
                # Frustration = product of both values * |correlation|
                # When BOTH dimensions are high, the conflict is real.
                # When one is low, there's no actual tension.
                tension = val_a * val_b * abs(corr)
                total += tension
                max_possible += abs(corr)  # max when both vals = 1.0

        if max_possible == 0.0:
            return 0.0

        return total / max_possible

    def identify_tensions(
        self,
        edge_dimensions: Dict[str, float],
        threshold: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """Identify the specific dimension tensions in an edge.

        Returns pairs where both dimensions are high (both sides of the
        conflict are activated), sorted by tension severity.

        Args:
            edge_dimensions: Dict of dimension_name → value (0-1).
            threshold: Minimum dimension value to consider "activated".

        Returns:
            List of tension dicts with dim_a, dim_b, val_a, val_b,
            correlation, tension_score.
        """
        tensions = []

        for dim_a, dim_b, corr in self._pairs:
            val_a = edge_dimensions.get(dim_a)
            val_b = edge_dimensions.get(dim_b)
            if val_a is None or val_b is None:
                continue

            # Both dimensions must be above threshold to be "in tension"
            # (if one is near zero, there's no real conflict)
            if val_a >= threshold and val_b >= threshold:
                tension = val_a * val_b * abs(corr)
                tensions.append({
                    "dim_a": dim_a,
                    "dim_b": dim_b,
                    "val_a": round(val_a, 3),
                    "val_b": round(val_b, 3),
                    "correlation": corr,
                    "tension_score": round(tension, 4),
                })

        tensions.sort(key=lambda t: -t["tension_score"])
        return tensions

    def recommend_sequence(
        self,
        edge_dimensions: Dict[str, float],
        target_dimension: str,
    ) -> Dict[str, Any]:
        """Recommend whether to address target_dimension now or defer.

        If the target dimension is frustrated with dimensions that are
        currently strong (high value), addressing it first could suppress
        them. Better to address the frustrated partner first.

        Args:
            edge_dimensions: Current alignment profile.
            target_dimension: Dimension the mechanism would target.

        Returns:
            Dict with should_defer, reason, defer_to_dimensions.
        """
        frustrated_with = self._index.get(target_dimension, [])
        if not frustrated_with:
            return {
                "should_defer": False,
                "reason": f"{target_dimension} has no frustrated partners",
                "defer_to_dimensions": [],
            }

        # Check if any frustrated partner has a stronger value
        target_val = edge_dimensions.get(target_dimension, 0.5)
        stronger_partners = []

        for partner_dim, corr in frustrated_with:
            partner_val = edge_dimensions.get(partner_dim, 0.5)
            if partner_val >= target_val + 0.05:  # Partner is meaningfully stronger
                stronger_partners.append({
                    "dimension": partner_dim,
                    "value": round(partner_val, 3),
                    "correlation": corr,
                })

        if stronger_partners:
            stronger_partners.sort(key=lambda p: -p["value"])
            return {
                "should_defer": True,
                "reason": (
                    f"{target_dimension} (val={target_val:.2f}) is frustrated with "
                    f"{len(stronger_partners)} stronger dimensions — address them first"
                ),
                "defer_to_dimensions": stronger_partners,
                "target_value": round(target_val, 3),
            }

        return {
            "should_defer": False,
            "reason": f"{target_dimension} is not dominated by frustrated partners",
            "defer_to_dimensions": [],
            "target_value": round(target_val, 3),
        }

    def get_frustration_h_modifiers(
        self,
        frustration_score: float,
    ) -> Dict[str, float]:
        """Get H1-H5 modifiers based on frustration level.

        High frustration means the buyer's alignment profile has internal
        contradictions — no single mechanism can resolve everything.
        This increases H2 (wrong mechanism) and H3 (wrong stage) because
        the "right" mechanism depends on sequencing.
        """
        if frustration_score > 0.6:
            return {"H1": 0.0, "H2": 0.15, "H3": 0.10, "H4": 0.0, "H5": 0.0}
        elif frustration_score > 0.3:
            return {"H1": 0.0, "H2": 0.08, "H3": 0.05, "H4": 0.0, "H5": 0.0}
        return {"H1": 0.0, "H2": 0.0, "H3": 0.0, "H4": 0.0, "H5": 0.0}


def get_frustration_scorer() -> FrustrationScorer:
    """Get a FrustrationScorer instance (stateless)."""
    return FrustrationScorer()
