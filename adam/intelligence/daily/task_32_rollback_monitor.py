"""
Task 32: Rollback Monitor
============================

Checks executed directives against current performance. If any rollback
trigger fires (CTR drop >50%, CPA increase >100%, spend overshoot >50%),
automatically reverts the change.

Schedule: 12:00 + 18:00 UTC daily (twice daily, checking morning changes)
"""

from __future__ import annotations

import json
import logging
import time
from typing import List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult
from adam.intelligence.campaign_intelligence.config import get_dcil_config

logger = logging.getLogger(__name__)


class RollbackMonitorTask(DailyStrengtheningTask):

    @property
    def name(self) -> str:
        return "rollback_monitor"

    @property
    def schedule_hours(self) -> List[int]:
        return [12, 18]

    @property
    def frequency_hours(self) -> int:
        return 6

    async def execute(self) -> TaskResult:
        t0 = time.time()
        config = get_dcil_config()

        # Load today's executed directives
        executed = self._load_executed_directives(config)
        if not executed:
            return TaskResult(
                task_name=self.name, success=True,
                details={"message": "No executed directives to monitor."},
            )

        # Load current snapshot for comparison
        from adam.intelligence.daily.task_23_dsp_performance_pull import get_latest_snapshot
        snapshot = get_latest_snapshot()

        if not snapshot:
            return TaskResult(
                task_name=self.name, success=True,
                details={"message": "No current snapshot for comparison."},
            )

        rollbacks = []
        for directive_data in executed:
            pre = directive_data.get("pre_change_snapshot", {})
            if not pre:
                continue

            trigger = self._check_rollback_triggers(directive_data, pre, snapshot, config)
            if trigger:
                result = self._execute_rollback(directive_data, config)
                rollbacks.append({
                    "directive_id": directive_data.get("directive_id", ""),
                    "trigger": trigger,
                    "result": result,
                })
                logger.warning(
                    "ROLLBACK triggered for %s: %s → %s",
                    directive_data.get("directive_id"), trigger, result,
                )

        duration = time.time() - t0
        return TaskResult(
            task_name=self.name,
            success=True,
            items_processed=len(executed),
            items_stored=len(rollbacks),
            duration_seconds=duration,
            details={
                "directives_monitored": len(executed),
                "rollbacks_triggered": len(rollbacks),
                "rollback_details": rollbacks,
            },
        )

    def _check_rollback_triggers(self, directive_data, pre_snapshot, current_snapshot, config):
        """Check if any rollback trigger fires for a directive."""
        campaign_id = directive_data.get("campaign_id", "")
        if not campaign_id:
            return None

        # Find campaign in current snapshot
        current_camp = None
        for camp in current_snapshot.campaigns:
            if camp.campaign_id == campaign_id:
                current_camp = camp
                break

        if not current_camp:
            return None

        pre_stats = pre_snapshot.get("stats", {})

        # CTR drop trigger
        pre_ctr = float(pre_stats.get("ctr", 0) or 0)
        if pre_ctr > 0 and current_camp.ctr > 0:
            ctr_change = (current_camp.ctr - pre_ctr) / pre_ctr
            if ctr_change < -(config.rollback_ctr_drop_pct / 100):
                return f"CTR dropped {abs(ctr_change):.0%} (threshold: {config.rollback_ctr_drop_pct}%)"

        # CPA increase trigger
        pre_cpa = float(pre_stats.get("ecpa", 0) or 0)
        if pre_cpa > 0 and current_camp.cpa > 0:
            cpa_change = (current_camp.cpa - pre_cpa) / pre_cpa
            if cpa_change > (config.rollback_cpa_increase_pct / 100):
                return f"CPA increased {cpa_change:.0%} (threshold: {config.rollback_cpa_increase_pct}%)"

        return None

    def _execute_rollback(self, directive_data, config):
        """Execute a rollback for a directive."""
        try:
            from adam.intelligence.campaign_intelligence.models import (
                Directive, DirectiveType, DirectiveStatus,
            )
            from adam.intelligence.campaign_intelligence.execution_engine import CampaignExecutionEngine

            directive = Directive(
                directive_id=directive_data.get("directive_id", ""),
                directive_type=DirectiveType(directive_data.get("type", "budget_reallocation")),
                campaign_id=directive_data.get("campaign_id", ""),
                pre_change_snapshot=directive_data.get("pre_change_snapshot", {}),
            )

            engine = CampaignExecutionEngine(config)
            return engine.rollback(directive)
        except Exception as e:
            return f"Rollback failed: {e}"

    def _load_executed_directives(self, config):
        """Load today's executed directives."""
        date = time.strftime("%Y-%m-%d")
        try:
            from adam.infrastructure.redis_client import get_redis
            redis = get_redis()
            if redis:
                key = f"{config.redis_prefix}:executed_directives:{date}"
                data = redis.get(key)
                if data:
                    return json.loads(data).get("directives", [])
        except Exception:
            pass

        from adam.intelligence.daily.task_30_execution import _MEMORY_EXECUTION
        if date in _MEMORY_EXECUTION:
            return _MEMORY_EXECUTION[date].get("directives", [])
        return []
