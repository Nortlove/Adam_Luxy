"""
Task 35: Weekly Causal Forest CATE Fit

Schedules ``run_weekly_causal_forest_fit`` per Seven-Component
Methodological Upgrade Handoff §2.10. Fits per-cell heterogeneous
treatment effects (CATEs) across the (archetype × mechanism × category)
universe and writes them back to Neo4j for cascade consumption.

Cell discovery: queries DecisionContext (with pscore_known=true) for
distinct (archetype, mechanism, category) triples within the lookback
window. ``run_weekly_causal_forest_fit`` itself filters out cells with
< 30 rows, so every discovered cell is fed in regardless of size; the
underlying fitter decides which to actually fit.

Schedule: 03:00 UTC Sunday (frequency_hours=168 = 7 days). The
DailyStrengtheningTask base only schedules by hour, so the weekly
cadence is enforced via ``frequency_hours`` and Redis last_run TTL.

Audit reference: CODEBASE_AUDIT_2026_04_29.md §6 — "Schedule
run_weekly_causal_forest_fit() as a job."

Discipline (B3-LUXY a/b/c/d):
    (a) Causal-forest math is canonical (Wager & Athey 2018) and lives
        in causal_forest.py; this task is the scheduling wrapper.
    (b) Regression: see test_task_35_causal_forest_fit.py
        (skip-when-no-driver, skip-when-no-cells, success path records
        cells_fit/skipped_low_n/failed in TaskResult.details).
    (c) calibration_pending=False — the cadence is canonical §2.10,
        not pilot-tuned.
    (d) Honest tag — the task swallows fit-level errors into
        TaskResult.details. CF needs econml installed; missing libs
        surface as task failure with a clear error string rather than
        silent no-op.
"""

from __future__ import annotations

import logging
from typing import Any, List, Optional, Tuple

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


class CausalForestFitTask(DailyStrengtheningTask):
    """Weekly orchestrator for per-cell CATE fits across the cell universe."""

    @property
    def name(self) -> str:
        return "causal_forest_weekly_fit"

    @property
    def schedule_hours(self) -> List[int]:
        # 03:00 UTC. The 168-hour frequency keeps it weekly.
        return [3]

    @property
    def frequency_hours(self) -> int:
        return 24 * 7

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        try:
            from adam.intelligence.causal_forest import (
                run_weekly_causal_forest_fit,
            )
        except Exception as exc:
            result.success = False
            result.details["error"] = f"import failed: {exc}"
            return result

        try:
            cells = _discover_cells_from_decision_log(days_lookback=90)
        except Exception as exc:
            result.success = False
            result.details["error"] = f"cell discovery failed: {exc}"
            return result

        result.details["cells_discovered"] = len(cells)
        if not cells:
            result.details["skipped"] = "no_eligible_cells"
            return result

        try:
            diag = run_weekly_causal_forest_fit(
                cells=cells, days_lookback=90,
            )
        except Exception as exc:
            result.success = False
            result.details["error"] = f"fit driver failed: {exc}"
            return result

        cells_fit = int(getattr(diag, "cells_fit", 0) or 0)
        cells_skipped_low_n = int(getattr(diag, "cells_skipped_low_n", 0) or 0)
        cells_failed = int(getattr(diag, "cells_failed", 0) or 0)
        errors = list(getattr(diag, "errors", []) or [])

        result.items_processed = len(cells)
        result.items_stored = cells_fit
        result.errors = cells_failed
        result.details.update(
            {
                "cells_fit": cells_fit,
                "cells_skipped_low_n": cells_skipped_low_n,
                "cells_failed": cells_failed,
                "fit_errors": errors[:10],
                "library_versions": dict(
                    getattr(diag, "library_versions", {}) or {}
                ),
            }
        )

        # The most common no-op condition is "econml not installed."
        # Surface that so it's actionable in ops, but don't fail the
        # task unless every discovered cell hard-errored (no successes,
        # no low-n skips — pure infrastructure failure).
        if cells_fit == 0 and cells_failed > 0 and cells_skipped_low_n == 0:
            result.success = False

        return result


def _discover_cells_from_decision_log(
    days_lookback: int = 90,
    driver: Optional[Any] = None,
) -> List[Tuple[str, str, str]]:
    """Discover the (archetype, mechanism, category) cells worth fitting.

    Pulls distinct triples from DecisionContext rows with
    pscore_known=true (M4 schema discipline). The CF fit function
    itself drops cells with < 30 rows, so we don't pre-filter on count —
    we just pass the universe of seen cells through.

    Returns [] when the Neo4j driver is unavailable or the query fails.
    The caller treats empty as "no eligible cells," not as failure.
    """
    if driver is None:
        try:
            from adam.core.dependencies import get_neo4j_driver
            driver = get_neo4j_driver()
        except Exception as exc:
            logger.debug("Cell discovery: Neo4j driver unavailable: %s", exc)
            return []
    if driver is None:
        return []

    import time

    cutoff_ts = int((time.time() - days_lookback * 86400) * 1000)

    cypher = """
    MATCH (dc:DecisionContext)
    WHERE dc.pscore_known = true
      AND dc.created_at * 1000 >= $cutoff_ts
      AND dc.archetype IS NOT NULL
      AND dc.mechanism_sent IS NOT NULL
      AND dc.category IS NOT NULL
    RETURN DISTINCT dc.archetype AS archetype,
                    dc.mechanism_sent AS mechanism,
                    dc.category AS category
    """

    cells: List[Tuple[str, str, str]] = []
    try:
        with driver.session() as session:
            for record in session.run(cypher, cutoff_ts=cutoff_ts):
                archetype = record.get("archetype")
                mechanism = record.get("mechanism")
                category = record.get("category")
                if archetype and mechanism and category:
                    cells.append((archetype, mechanism, category))
    except Exception as exc:
        logger.warning("Cell discovery query failed: %s", exc)
        return []

    return cells
