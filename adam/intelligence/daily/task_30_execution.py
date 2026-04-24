"""
Task 30: Campaign Execution
==============================

Executes approved directives via StackAdapt GraphQL (when auto_execute=True)
or generates human-readable instructions (when auto_execute=False).

Schedule: 07:30 UTC daily
"""

from __future__ import annotations

import json
import logging
import time
from typing import List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult
from adam.intelligence.campaign_intelligence.config import get_dcil_config

logger = logging.getLogger(__name__)


class CampaignExecutionTask(DailyStrengtheningTask):

    @property
    def name(self) -> str:
        return "campaign_execution"

    @property
    def schedule_hours(self) -> List[int]:
        return [7]

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        t0 = time.time()
        config = get_dcil_config()

        from adam.intelligence.daily.task_29_coherence_validation import get_latest_validated_directives

        validated_data = get_latest_validated_directives()
        if not validated_data or not validated_data.get("directives"):
            return TaskResult(
                task_name=self.name, success=True,
                details={"message": "No validated directives to execute."},
            )

        from adam.intelligence.campaign_intelligence.models import (
            Directive, DirectiveType, DirectiveStatus, LearningScope,
        )
        from adam.intelligence.campaign_intelligence.execution_engine import (
            CampaignExecutionEngine, format_execution_summary,
        )

        directives = []
        for dd in validated_data.get("directives", []):
            status = DirectiveStatus(dd.get("status", "proposed"))
            if status not in (DirectiveStatus.APPROVED, DirectiveStatus.CAPPED):
                continue

            d = Directive(
                directive_id=dd.get("directive_id", ""),
                directive_type=DirectiveType(dd.get("type", "budget_reallocation")),
                status=status,
                campaign_id=dd.get("campaign_id", ""),
                archetype=dd.get("archetype", ""),
                parameter=dd.get("parameter", ""),
                proposed_value=dd.get("proposed_value", ""),
                rationale=dd.get("rationale", ""),
                confidence=dd.get("confidence", 0),
            )
            directives.append(d)

        if not directives:
            return TaskResult(
                task_name=self.name, success=True,
                details={"message": "No approved/capped directives to execute."},
            )

        engine = CampaignExecutionEngine(config)
        executed = engine.execute_all(directives)

        # Store execution results
        _store_execution_results(executed, config)

        # Generate summary
        summary = format_execution_summary(executed)
        logger.info("DCIL Execution Summary:\n%s", summary)

        succeeded = sum(1 for d in executed if d.status == DirectiveStatus.EXECUTED)
        failed = sum(1 for d in executed if d.status == DirectiveStatus.FAILED)

        duration = time.time() - t0
        return TaskResult(
            task_name=self.name,
            success=True,
            items_processed=len(executed),
            items_stored=succeeded,
            errors=failed,
            duration_seconds=duration,
            details={
                "executed": succeeded,
                "failed": failed,
                "auto_execute": config.auto_execute,
                "summary": summary[:500],
            },
        )


_MEMORY_EXECUTION = {}


def _store_execution_results(directives, config):
    date = time.strftime("%Y-%m-%d")
    data = {
        "timestamp": time.time(),
        "date": date,
        "directives": [
            {
                "directive_id": d.directive_id,
                "type": d.directive_type.value,
                "status": d.status.value,
                "campaign_id": d.campaign_id,
                "archetype": d.archetype,
                "parameter": d.parameter,
                "proposed_value": str(d.proposed_value),
                "execution_result": d.execution_result,
                "executed_at": d.executed_at,
                "pre_change_snapshot": d.pre_change_snapshot,
            }
            for d in directives
        ],
    }
    try:
        from adam.infrastructure.redis_client import get_redis
        redis = get_redis()
        if redis:
            key = f"{config.redis_prefix}:executed_directives:{date}"
            redis.setex(key, config.snapshot_ttl_days * 86400, json.dumps(data))
            return
    except Exception:
        pass
    _MEMORY_EXECUTION[date] = data
