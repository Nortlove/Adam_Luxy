"""
Task 45: Daily creative spot-check sweep — RED criterion #6 producer.

Closes the named sibling at task_42_launch_gate_runner.py:40-42:
"Offline-pipeline metaphor coherence scorer is Section 6 (Spine #12)
work; not in cascade today. Skip-when-no-data until that scorer
runs and aggregates."

Per directive Phase 10 line 1135 (RED criterion #6 — "any creative
in rotation fails primary-metaphor coherence in spot check"). Slices
18/19/20 shipped the scorers; Slice 23 ships the sweep that runs
them against persisted CreativeRecord copy_text and increments the
launch-gate snapshot counters.

Schedule: 04:00 UTC alongside Task 41 / 44 — all populate state
Task 42 (05:00) reads.

NOT IN SCOPE (named successors)
  * Visual / non-text scoring (sibling).
  * Per-cohort threshold tuning (sibling).
  * Multi-language scorer markers (sibling).
  * StackAdapt-side dynamic copy fetch — v0.1 reads CreativeRecord.
    copy_text only (Slice 23 added this field; populated at upload
    or via reconciliation from userMetadata.adam_metadata.copy_text).
"""

from __future__ import annotations

import logging
from typing import List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


class CreativeSpotCheckTask(DailyStrengtheningTask):
    """Daily spot-check over :UploadedCreative entries — populates
    Phase 10 RED criterion #6 producer counters."""

    @property
    def name(self) -> str:
        return "creative_spot_check"

    @property
    def schedule_hours(self) -> List[int]:
        # 04:00 UTC slot — alongside Task 41 (OPE) + Task 44
        # (identity-stability sweep). All populate state Task 42
        # (05:00) reads.
        return [4]

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        try:
            from adam.intelligence.creative_spot_check_sweep import (
                sweep_creative_spot_check,
            )
            from adam.intelligence.red_criteria_snapshot import (
                get_red_snapshot,
            )
        except Exception as exc:
            result.success = False
            result.details["error"] = f"import failed: {exc}"
            return result

        # Resolve infrastructure
        neo4j_driver = None
        try:
            from adam.core.dependencies import get_infrastructure
            infra = await get_infrastructure()
            neo4j_driver = getattr(infra, "neo4j_driver", None) or getattr(
                infra, "neo4j", None,
            )
        except Exception as exc:
            logger.debug("Task 45 infrastructure unavailable: %s", exc)

        if neo4j_driver is None:
            result.details["skipped"] = "no_neo4j_driver"
            return result

        snapshot = None
        try:
            snapshot = get_red_snapshot()
        except Exception as exc:
            logger.debug("Task 45 snapshot unavailable: %s", exc)

        try:
            sweep_result = await sweep_creative_spot_check(
                driver=neo4j_driver,
                snapshot=snapshot,
            )
        except Exception as exc:
            result.success = False
            result.details["error"] = f"sweep failed: {exc}"
            return result

        result.details["n_in_rotation"] = sweep_result.n_in_rotation
        result.details["n_failed"] = sweep_result.n_failed
        result.details["n_skipped_no_copy"] = sweep_result.n_skipped_no_copy
        result.details["n_skipped_no_metadata"] = (
            sweep_result.n_skipped_no_metadata
        )
        result.details["snapshot_recorded"] = (
            snapshot is not None
            and sweep_result.n_in_rotation > 0
        )
        result.items_processed = sweep_result.n_in_rotation

        logger.info(
            "Task 45 creative spot-check: in_rotation=%d failed=%d "
            "skipped_no_copy=%d skipped_no_metadata=%d",
            sweep_result.n_in_rotation,
            sweep_result.n_failed,
            sweep_result.n_skipped_no_copy,
            sweep_result.n_skipped_no_metadata,
        )
        return result
