"""
Task 8: Gradient Field Recomputation
=====================================

Recomputes ∂P(conversion)/∂alignment_dim for all (archetype, category)
cells that received new evidence from Tasks 5, 6, or 7.

This is the system's core optimization primitive — gradient fields tell
every downstream consumer which psychological dimensions to adjust,
in what direction, by how much.

Produces:
- Updated GradientIntelligence per (archetype, category) cell
- GradientDrift per cell (landscape stability indicator)

Consumed at bid time:
- Determines mechanism selection (highest-gradient mechanisms win)
- Guides copy generation (highest-gradient-gap dimensions guide emphasis)
- Feeds information value (gradient magnitude × buyer uncertainty)

Redis keys:
- informativ:gradient:{archetype}:{category} — cached gradient (24h TTL)
- informativ:gradient:drift:{archetype}:{category} — gradient stability
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


class GradientRecomputeTask(DailyStrengtheningTask):
    """Recompute gradient fields for updated cells."""

    @property
    def name(self) -> str:
        return "gradient_recompute"

    @property
    def schedule_hours(self) -> List[int]:
        return [5]  # 5 AM UTC, after Tasks 5-7

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        # Get the list of cells to recompute
        cells = await self._get_cells_to_recompute()
        result.details["cells_queued"] = len(cells)

        if not cells:
            # Recompute universal gradient at minimum
            cells = [("", "")]

        for archetype, category in cells:
            try:
                gradient = await self._recompute_cell(archetype, category)
                if gradient:
                    # Store in Redis for fast lookup
                    key = f"informativ:gradient:{archetype or 'universal'}:{category or 'universal'}"
                    if self._store_redis_hash(key, {
                        "archetype": archetype or "universal",
                        "category": category or "universal",
                        "gradient_vector": gradient.get("gradient_vector", {}),
                        "optimal_targets": gradient.get("optimal_targets", {}),
                        "optimization_priorities": gradient.get("priorities", []),
                        "sample_size": gradient.get("sample_size", 0),
                        "computed_at": time.time(),
                    }, ttl=86400):
                        result.items_stored += 1
                    result.items_processed += 1
            except Exception as e:
                result.errors += 1
                logger.debug("Gradient recompute failed for (%s, %s): %s",
                             archetype, category, e)

        return result

    async def _get_cells_to_recompute(self) -> List[tuple]:
        """Get (archetype, category) cells that need fresh gradients.

        Checks which cells received new evidence from Tasks 5/7.
        """
        cells = set()
        r = self._get_redis()
        if not r:
            return list(cells)

        try:
            # Check review refresh keys for recently updated categories
            cursor = 0
            while True:
                cursor, keys = r.scan(
                    cursor, match="informativ:review_refresh:*:centroid", count=100,
                )
                for key in keys:
                    parts = key.split(":")
                    if len(parts) >= 4:
                        category = parts[2]
                        # Add cells for all archetypes × this category
                        for arch in _ARCHETYPES:
                            cells.add((arch, category))
                if cursor == 0:
                    break

            # Check social pulse keys
            cursor = 0
            while True:
                cursor, keys = r.scan(
                    cursor, match="informativ:social:*:pulse", count=100,
                )
                for key in keys:
                    parts = key.split(":")
                    if len(parts) >= 4:
                        category = parts[2]
                        for arch in _ARCHETYPES:
                            cells.add((arch, category))
                if cursor == 0:
                    break
        except Exception:
            pass

        return list(cells)[:100]  # Cap recomputation

    async def _recompute_cell(
        self, archetype: str, category: str,
    ) -> Optional[Dict[str, Any]]:
        """Recompute gradient field for a single (archetype, category) cell."""
        try:
            from adam.intelligence.gradient_fields import compute_gradient_from_neo4j
            gradient = await compute_gradient_from_neo4j(archetype, category)
            if gradient:
                return {
                    "gradient_vector": gradient.gradient_vector if hasattr(gradient, 'gradient_vector') else {},
                    "optimal_targets": gradient.optimal_targets if hasattr(gradient, 'optimal_targets') else {},
                    "priorities": gradient.optimization_priorities if hasattr(gradient, 'optimization_priorities') else [],
                    "sample_size": gradient.sample_size if hasattr(gradient, 'sample_size') else 0,
                }
        except Exception as e:
            logger.debug("Gradient computation failed: %s", e)

        # Fallback: compute a simple gradient from cached review data
        return self._compute_fallback_gradient(archetype, category)

    def _compute_fallback_gradient(
        self, archetype: str, category: str,
    ) -> Optional[Dict[str, Any]]:
        """Compute gradient from cached review refresh data when Neo4j unavailable."""
        r = self._get_redis()
        if not r:
            return None

        centroid_key = f"informativ:review_refresh:{category}:centroid"
        data = self._read_redis_hash(centroid_key)
        if not data:
            return None

        import json
        try:
            centroid = json.loads(data.get("ndf_centroid", "{}"))
        except Exception:
            return None

        if not centroid:
            return None

        # Simple gradient: direction from 0.5 (neutral) toward centroid
        # This approximates "what dimensions matter for this category"
        gradient_vector = {}
        for dim, val in centroid.items():
            gradient_vector[dim] = round(val - 0.5, 4)

        return {
            "gradient_vector": gradient_vector,
            "optimal_targets": centroid,
            "priorities": sorted(
                gradient_vector.items(),
                key=lambda x: abs(x[1]),
                reverse=True,
            )[:5],
            "sample_size": int(data.get("sample_size", 0)),
        }


# Known archetypes for cell enumeration
_ARCHETYPES = [
    "explorer", "optimizer", "loyalist", "skeptic",
    "impulse_buyer", "researcher", "bargain_hunter", "premium_seeker",
]
