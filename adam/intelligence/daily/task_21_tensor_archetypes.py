"""
Task 21: Tensor Archetype Discovery

Runs BilateralTensorDecomposer on accumulated BRAND_CONVERTED edge data
to discover bilateral alignment archetypes — patterns of buyer×seller
dimension co-occurrence that predict conversion.

Unlike k-means archetypes (buyer-only), tensor-discovered archetypes
operate in the BILATERAL space, capturing what combinations of buyer
psychology and seller strategy actually drive conversion.

Schedule: Weekly at 4 AM UTC (before recalibration at 5 AM).
"""

from __future__ import annotations

import logging
from typing import List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


class TensorArchetypeTask(DailyStrengtheningTask):
    """Weekly tensor archetype discovery."""

    @property
    def name(self) -> str:
        return "tensor_archetype_discovery"

    @property
    def schedule_hours(self) -> List[int]:
        return [4]

    @property
    def frequency_hours(self) -> int:
        return 24 * 7

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        try:
            from adam.retargeting.engines.tensor_decomposition import (
                BilateralTensorDecomposer,
            )
            from adam.core.dependencies import get_infrastructure

            infra = await get_infrastructure()
            driver = getattr(infra, "neo4j_driver", None)
            if not driver:
                result.details["skipped"] = "no_neo4j_driver"
                return result

            # Fetch edge data for decomposition
            async with driver.session() as session:
                cursor = await session.run(
                    "MATCH ()-[e:BRAND_CONVERTED]->() "
                    "WHERE e.outcome IS NOT NULL "
                    "RETURN properties(e) AS props "
                    "LIMIT 10000"
                )
                records = await cursor.data()

            if len(records) < 200:
                result.details["skipped"] = f"insufficient_edges ({len(records)})"
                return result

            edges = [r["props"] for r in records if isinstance(r.get("props"), dict)]

            decomposer = BilateralTensorDecomposer()
            decomposition = decomposer.decompose(edges)

            if decomposition:
                result.items_processed = len(edges)
                result.details["archetypes_discovered"] = len(
                    decomposition.archetypes
                )
                result.details["explained_variance"] = decomposition.explained_variance
                result.details["top_archetypes"] = [
                    {
                        "rank": a.rank,
                        "weight": round(a.weight, 4),
                        "buyer_dims": a.dominant_buyer_dims[:3],
                        "seller_dims": a.dominant_seller_dims[:3],
                    }
                    for a in decomposition.archetypes[:5]
                ]

        except Exception as exc:
            logger.debug("Tensor archetype discovery skipped: %s", exc)
            result.details["skipped"] = str(exc)

        return result
