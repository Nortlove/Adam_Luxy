"""
Task 29.6: Horizon Adjudicator — auto-adjudicate horizon-expired Deviations
============================================================================

Closes Loop γ auto-path. Operator deviations from system recommendations
are recorded as :Deviation nodes (created by the dashboard decide flow,
adam/api/dashboard/router.py:1316). Each Deviation carries a
horizon_class (hours/days/weeks/months); when the horizon window has
closed, the deviation is "ready" for adjudication — the system needs
to compare what happened to what was predicted and verdict
system_right / user_right / indeterminate.

Two paths exist for adjudication:
  - Operator-led (Slice D2, commit ced281d): operator opens the horizon
    card in the dashboard /recommendations queue, picks a verdict,
    causal_adjudicator.adjudicate_deviation_with_operator_verdict()
    persists the Outcome + (on system_right) WhyLibraryEntry
  - Auto path (this task): nightly sweep over users-with-pending-
    deviations, calls causal_adjudicator.adjudicate_ready_deviations()
    for each, runs the evaluators (pause_campaign / zero_conversions /
    low_ctr / client_recommendation), persists Outcome with
    verdict_source='auto'

Without this task, the auto path NEVER fires — the
adjudicate_ready_deviations function is exposed only at
adam/api/dashboard/router.py:734 (operator-triggered). Operators who
don't open the dashboard daily leave horizon-expired deviations
forever pending, and Loop γ doesn't accumulate WhyLibraryEntries that
feed defensive priors for future cascade decisions.

A5 antipattern note: the auto-evaluators in causal_adjudicator.py
(_evaluate_pause_campaign, _evaluate_zero_conversions, _evaluate_low_ctr,
_evaluate_client_recommendation) compute before/after metric deltas →
verdict. Honest labeling is in the module docstring (lines 10-14):
"v1 makes a directional adjudication — real causal-inference would
require holdouts." This task closes Loop γ STRUCTURALLY; the upgrade
to holdout-aware adjudication is Doc 3 §I.5 territory.

Schedule: 08:00 UTC daily (after the daily DCIL chain finishes).
"""

from __future__ import annotations

import logging
import time
from typing import List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


class HorizonAdjudicatorTask(DailyStrengtheningTask):

    @property
    def name(self) -> str:
        return "horizon_adjudicator"

    @property
    def schedule_hours(self) -> List[int]:
        return [8]

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        t0 = time.time()
        try:
            users_with_pending = await _users_with_pending_deviations()
        except Exception as exc:
            logger.exception("horizon_adjudicator: user enumeration failed")
            return TaskResult(
                task_name=self.name, success=False, errors=1,
                duration_seconds=time.time() - t0,
                details={"error": f"user enumeration: {exc}"},
            )

        total_adjudicated = 0
        total_skipped_too_early = 0
        total_skipped_no_data = 0
        total_skipped_already_done = 0
        users_processed = 0
        users_failed = 0

        try:
            from adam.intelligence.causal_adjudicator import (
                adjudicate_ready_deviations,
            )
        except Exception as exc:
            return TaskResult(
                task_name=self.name, success=False, errors=1,
                duration_seconds=time.time() - t0,
                details={"error": f"causal_adjudicator import: {exc}"},
            )

        for user_id in users_with_pending:
            try:
                batch = await adjudicate_ready_deviations(user_id)
                total_adjudicated += len(batch.adjudicated)
                total_skipped_too_early += batch.skipped_too_early
                total_skipped_no_data += batch.skipped_no_data
                total_skipped_already_done += batch.skipped_already_done
                users_processed += 1
            except Exception as exc:
                logger.warning(
                    "horizon_adjudicator: user %s failed: %s", user_id, exc,
                )
                users_failed += 1

        details = {
            "users_processed": users_processed,
            "users_failed": users_failed,
            "users_total": len(users_with_pending),
            "adjudicated": total_adjudicated,
            "skipped_too_early": total_skipped_too_early,
            "skipped_no_data": total_skipped_no_data,
            "skipped_already_done": total_skipped_already_done,
        }
        logger.info(
            "horizon_adjudicator: %d users processed, %d adjudicated, "
            "%d too_early, %d no_data, %d already_done, %d users_failed",
            users_processed, total_adjudicated, total_skipped_too_early,
            total_skipped_no_data, total_skipped_already_done, users_failed,
        )
        return TaskResult(
            task_name=self.name,
            success=users_failed == 0,
            items_processed=len(users_with_pending),
            items_stored=total_adjudicated,
            duration_seconds=time.time() - t0,
            errors=users_failed,
            details=details,
        )


async def _users_with_pending_deviations() -> List[str]:
    """Return user_ids that have at least one pending Deviation node.

    Returns an empty list when Neo4j is unavailable — the daily task
    treats this as "nothing to do," soft-fail.
    """
    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client
        client = get_neo4j_client()
        if not client.is_connected:
            return []
        async with await client.session() as session:
            result = await session.run(
                """
                MATCH (u:DialogueUser)-[:DEVIATED]->(d:Deviation)
                WHERE coalesce(d.adjudication_status, 'pending') = 'pending'
                RETURN DISTINCT u.id AS user_id
                """
            )
            return [r["user_id"] async for r in result]
    except Exception as exc:
        logger.debug("horizon_adjudicator: Neo4j query failed: %s", exc)
        return []
