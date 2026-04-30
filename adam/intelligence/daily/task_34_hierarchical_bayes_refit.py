"""
Task 34: Nightly Hierarchical Bayes Refit

Schedules ``run_nightly_hierarchical_refit`` per Seven-Component
Methodological Upgrade Handoff §3.5. Without this, the
(archetype × mechanism × category) posteriors that the cascade reads
stay frozen at last-fit values; per-cell learning never closes.

Schedule: 02:00 UTC nightly. Sits between the data-pull tasks
(00:00–04:00) and the gradient-recompute task (05:00) so refit
posteriors are available downstream the same cycle.

Audit reference: CODEBASE_AUDIT_2026_04_29.md §6 — "Schedule
run_nightly_hierarchical_refit() as a job."

Discipline (B3-LUXY a/b/c/d):
    (a) The fit math lives in hierarchical_bayes.py; this task is the
        scheduling wrapper, not a re-implementation.
    (b) Regression: see test_task_34_hierarchical_bayes_refit.py
        (skip-when-no-driver, skip-when-no-observations, success path
        records r̂_max + cells_written into TaskResult.details).
    (c) calibration_pending=False — the cadence is the canonical §3.5
        cadence, not pilot-tuned.
    (d) Honest tag — the task swallows fit-level errors into
        TaskResult.details rather than raising, matching every other
        daily task's contract. A failure here does NOT take the
        scheduler down.
"""

from __future__ import annotations

import logging
from typing import List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


class HierarchicalBayesRefitTask(DailyStrengtheningTask):
    """Nightly orchestrator for the per-cell hierarchical posterior refit."""

    @property
    def name(self) -> str:
        return "hierarchical_bayes_refit"

    @property
    def schedule_hours(self) -> List[int]:
        return [2]

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        try:
            from adam.intelligence.hierarchical_bayes import (
                run_nightly_hierarchical_refit,
            )
        except Exception as exc:
            result.success = False
            result.details["error"] = f"import failed: {exc}"
            return result

        try:
            diag = run_nightly_hierarchical_refit(days_lookback=90)
        except Exception as exc:
            result.success = False
            result.details["error"] = f"refit failed: {exc}"
            return result

        cells_recovered = int(getattr(diag, "cells_recovered", 0) or 0)
        r_hat_max = float(getattr(diag, "r_hat_max", 0.0) or 0.0)
        divergences = int(getattr(diag, "divergences", 0) or 0)
        ess_bulk_min = float(getattr(diag, "ess_bulk_min", 0.0) or 0.0)
        errors = list(getattr(diag, "errors", []) or [])

        result.items_processed = cells_recovered
        result.items_stored = cells_recovered
        result.errors = len(errors)
        result.details = {
            "cells_recovered": cells_recovered,
            "r_hat_max": r_hat_max,
            "divergences": divergences,
            "ess_bulk_min": ess_bulk_min,
            "fit_errors": errors[:10],  # cap details payload
        }

        # Diagnostic flags — surface but don't fail the task
        if r_hat_max > 1.01:
            result.details["warning_r_hat"] = (
                f"r_hat_max={r_hat_max:.3f} > 1.01 (chains may not have converged)"
            )
        if divergences:
            result.details["warning_divergences"] = divergences

        if errors and cells_recovered == 0:
            # Total failure — no posteriors recovered
            result.success = False

        return result
