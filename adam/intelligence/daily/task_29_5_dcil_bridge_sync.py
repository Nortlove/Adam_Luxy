"""
Task 29.5: DCIL Bridge — Redis to management.dcil_directives sync
==================================================================

Closes Loop β: validated directives written by task_29 to Redis are
read here and persisted to the management.dcil_directives table, where
the dashboard /recommendations queue picks them up via
adam.api.dashboard.service._load_dcil_directives.

Without this task, the DCIL daily pipeline writes directives the
operator can never review:

  task_28 directive_generation  → Redis "directives:{date}"
  task_29 coherence_validation  → Redis "validated_directives:{date}"
  *task_29.5 (this task)*       → management.dcil_directives table
  dashboard /recommendations    → reads from management.dcil_directives

Pre-task-29.5 state: bridge function existed (adam/api/admin/services/
dcil_bridge.py) but had two bugs (took a campaign_id parameter and
inserted ALL directives under that one id; no idempotency) and zero
schedulers calling it. Loop β was structurally broken.

Schedule: 07:30 UTC daily (after task_29's 07:00 coherence validation).

Failure mode: soft-fail. Sync errors are logged with counts but do not
block the daily pipeline. Re-running the task is idempotent — directives
already in management.dcil_directives are skipped via id-match.
"""

from __future__ import annotations

import logging
import time
from typing import List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


class DCILBridgeSyncTask(DailyStrengtheningTask):

    @property
    def name(self) -> str:
        return "dcil_bridge_sync"

    @property
    def schedule_hours(self) -> List[int]:
        return [7]  # Same hour as task_29; ordering ensured by frequency_hours
                    # and the within-cycle execution sequence in scheduler

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        t0 = time.time()

        try:
            from adam.api.admin.services.dcil_bridge import (
                sync_directives_to_postgres,
            )
        except Exception as exc:
            return TaskResult(
                task_name=self.name, success=False, errors=1,
                details={"error": f"dcil_bridge import failed: {exc}"},
            )

        try:
            counts = await sync_directives_to_postgres()
        except Exception as exc:
            logger.exception("dcil_bridge sync failed")
            return TaskResult(
                task_name=self.name, success=False, errors=1,
                duration_seconds=time.time() - t0,
                details={"error": str(exc)},
            )

        duration = time.time() - t0
        return TaskResult(
            task_name=self.name,
            success=True,
            items_processed=(
                counts.get("synced", 0)
                + counts.get("skipped_existing", 0)
                + counts.get("skipped_no_campaign", 0)
                + counts.get("failed", 0)
            ),
            items_stored=counts.get("synced", 0),
            duration_seconds=duration,
            details=counts,
        )
