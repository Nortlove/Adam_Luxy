# =============================================================================
# Daily Task 16: Page Gradient Field Computation
# Location: adam/intelligence/daily/task_16_page_gradients.py
# =============================================================================

"""
Computes ∂P(conversion)/∂(page_dimension) for all (mechanism, barrier)
cells that have accumulated sufficient observations (≥50).

Runs daily. Results feed into PlacementOptimizer to inform which page
psychological dimensions matter most for each mechanism-barrier pairing.
"""

import logging
from typing import Any, Dict

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


class PageGradientTask(DailyStrengtheningTask):
    """Compute page gradient fields from accumulated observations."""

    @property
    def name(self) -> str:
        return "page_gradient_computation"

    @property
    def schedule_hours(self):
        return [4]  # 4 AM UTC daily

    async def execute(self, context: Dict[str, Any]) -> TaskResult:
        """Compute all page gradient fields."""
        from adam.intelligence.page_gradient_fields import get_page_gradient_accumulator

        acc = get_page_gradient_accumulator()
        stats_before = acc.stats

        if stats_before["cells_with_enough_data"] == 0:
            return TaskResult(
                task_name=self.name,
                success=True,
                summary=f"No cells with enough data (need ≥50 observations). "
                        f"Total observations: {stats_before['total_observations']}",
            )

        computed = acc.compute_all_gradients()

        return TaskResult(
            task_name=self.name,
            success=True,
            summary=(
                f"Computed {len(computed)} page gradient fields from "
                f"{stats_before['total_observations']} observations across "
                f"{stats_before['cells_observed']} cells"
            ),
            details={
                "fields_computed": len(computed),
                "total_observations": stats_before["total_observations"],
                "cells_observed": stats_before["cells_observed"],
                "top_fields": {
                    k: [
                        {"dim": d, "gradient": round(g, 4)}
                        for d, g in v.top_dimensions[:3]
                    ]
                    for k, v in list(computed.items())[:5]
                },
            },
        )
