# =============================================================================
# Weekly Task 17: Active Copy Evolution
# Location: adam/intelligence/daily/task_17_copy_evolution.py
# =============================================================================

"""
Identifies bottom-performing copy variants and regenerates them using
the CopyEffectivenessLearner's empirically-learned parameters.

Runs weekly (Sunday 5 AM UTC). This is DIRECTED evolution:
the system doesn't randomly mutate copy — it regenerates using
parameters that the learner discovered work better.

Cycle:
1. Query learner for bottom 20% variants by conversion rate
2. For each, get learned params for that (archetype, barrier, page_cluster) cell
3. Generate new copy via generate_evolved() with learned params
4. Replace the old variant in the cache
5. Log what changed and why
"""

import logging
from datetime import datetime
from typing import Any, Dict

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


class CopyEvolutionTask(DailyStrengtheningTask):
    """Weekly copy evolution — regenerate bottom performers with learned params."""

    @property
    def name(self) -> str:
        return "copy_evolution"

    @property
    def schedule_hours(self):
        return [5]  # 5 AM UTC

    async def execute(self, context: Dict[str, Any]) -> TaskResult:
        """Run the evolution cycle."""
        # Only run on Sundays
        if datetime.utcnow().weekday() != 6:
            return TaskResult(
                task_name=self.name,
                success=True,
                summary="Skipped (runs Sundays only)",
            )

        from adam.output.copy_generation.copy_learner import get_copy_learner

        learner = get_copy_learner()
        stats = learner.stats

        if stats["total_outcomes"] < 50:
            return TaskResult(
                task_name=self.name,
                success=True,
                summary=f"Not enough data yet ({stats['total_outcomes']} outcomes, need ≥50)",
            )

        # Find bottom performers
        bottom = learner.get_bottom_performers(min_served=10, bottom_pct=0.2)

        if not bottom:
            return TaskResult(
                task_name=self.name,
                success=True,
                summary="No underperforming variants found (all above threshold or insufficient serving data)",
            )

        # Get learned parameter summary
        learned_summary = learner.get_learned_params_summary()

        evolved = 0
        evolution_log = []

        for context_key, variant in bottom:
            parts = context_key.split(":")
            archetype = parts[0] if len(parts) > 0 else ""
            barrier = parts[1] if len(parts) > 1 else ""
            page_cluster = parts[2] if len(parts) > 2 else ""

            # Get recommended params for this cell
            recommended = learner.recommend_params(archetype, barrier, page_cluster)

            evolution_log.append({
                "variant_id": variant.variant_id,
                "context": context_key,
                "old_rate": round(variant.conversion_rate, 4),
                "served": variant.served_count,
                "old_params": {
                    "tone": variant.tone,
                    "framing": variant.framing,
                    "evidence_type": variant.evidence_type,
                    "cta_style": variant.cta_style,
                },
                "new_params": recommended,
            })

            # NOTE: Actual regeneration requires Claude API.
            # In production, this would call:
            #   from adam.output.copy_generation.service import CopyGenerationService
            #   svc = CopyGenerationService()
            #   new_copy = await svc.generate_evolved(request, archetype, barrier, page_cluster)
            # For now, we log the recommendation for manual execution.
            evolved += 1

        return TaskResult(
            task_name=self.name,
            success=True,
            summary=(
                f"Identified {len(bottom)} underperforming variants for evolution. "
                f"Learned params: {learned_summary}"
            ),
            details={
                "variants_flagged": evolved,
                "learned_params": learned_summary,
                "evolution_log": evolution_log,
                "total_outcomes": stats["total_outcomes"],
            },
        )
