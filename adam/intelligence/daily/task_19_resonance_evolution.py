"""
Task 19: Resonance Evolution Cycle

Runs the ResonanceEvolutionaryEngine's daily evolution cycle:
1. Generates new hypotheses from accumulated resonance observations
2. Creates experiments for promising hypotheses (UCB1 allocation)
3. Evaluates active experiments (promote/prune/continue)
4. Detects mechanism synergies from observation patterns
5. Self-evaluates prediction accuracy and detects concept drift

This is the system's active self-improvement loop — it discovers
resonance strategies beyond what theory predicts, tests them with
controlled exploration, and evolves the resonance model over time.

Schedule: Daily at 6 AM UTC (same window as self-teaching task 15).
"""

from __future__ import annotations

import logging
from typing import List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


class ResonanceEvolutionTask(DailyStrengtheningTask):
    """Daily resonance evolution cycle."""

    @property
    def name(self) -> str:
        return "resonance_evolution"

    @property
    def schedule_hours(self) -> List[int]:
        return [6]

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        try:
            from adam.retargeting.resonance.evolutionary_engine import (
                ResonanceEvolutionaryEngine,
            )
            from adam.retargeting.resonance.resonance_learner import get_resonance_learner

            learner = get_resonance_learner()
            engine = ResonanceEvolutionaryEngine(learner=learner)
            report = engine.run_evolution_cycle()

            result.items_processed = report.get("total_observations", 0)
            result.details = report

        except Exception as exc:
            logger.debug("Resonance evolution skipped: %s", exc)
            result.details["skipped"] = str(exc)

        return result
