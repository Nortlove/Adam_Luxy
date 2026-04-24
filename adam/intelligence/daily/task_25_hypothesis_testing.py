"""
Task 25: Hypothesis Testing
==============================

Runs 5 standing hypotheses + trend/anomaly detection against the
current performance snapshot. Stores results for downstream scope
determination and directive generation.

Schedule: 05:00 UTC daily (after normalization)
"""

from __future__ import annotations

import json
import logging
import time
from typing import List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult
from adam.intelligence.campaign_intelligence.config import get_dcil_config

logger = logging.getLogger(__name__)


class HypothesisTestingTask(DailyStrengtheningTask):

    @property
    def name(self) -> str:
        return "hypothesis_testing"

    @property
    def schedule_hours(self) -> List[int]:
        return [5]

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        t0 = time.time()
        config = get_dcil_config()

        from adam.intelligence.daily.task_23_dsp_performance_pull import get_latest_snapshot
        snapshot = get_latest_snapshot()

        if snapshot is None:
            return TaskResult(
                task_name=self.name, success=False, errors=1,
                details={"error": "No snapshot available."},
            )

        from adam.intelligence.campaign_intelligence.hypothesis_battery import HypothesisBattery
        battery = HypothesisBattery(config)

        results, anomalies = battery.run_all(snapshot)

        # Store results for downstream tasks
        _store_hypothesis_results(results, anomalies, config)

        confirmed = sum(1 for r in results if r.status.value == "confirmed")
        rejected = sum(1 for r in results if r.status.value == "rejected")
        inconclusive = sum(1 for r in results if r.status.value == "inconclusive")

        duration = time.time() - t0
        return TaskResult(
            task_name=self.name,
            success=True,
            items_processed=len(results),
            items_stored=len(results) + len(anomalies),
            duration_seconds=duration,
            details={
                "confirmed": confirmed,
                "rejected": rejected,
                "inconclusive": inconclusive,
                "anomalies": len(anomalies),
                "findings": [r.finding for r in results],
                "anomaly_descriptions": [a.description for a in anomalies],
            },
        )


def _store_hypothesis_results(results, anomalies, config):
    """Store to Redis or memory for downstream consumption."""
    data = {
        "timestamp": time.time(),
        "date": time.strftime("%Y-%m-%d"),
        "hypotheses": [
            {
                "id": r.hypothesis_id,
                "name": r.hypothesis_name,
                "status": r.status.value,
                "p_value": r.p_value,
                "effect_size": r.effect_size,
                "sample_size": r.sample_size,
                "finding": r.finding,
                "recommendation": r.recommendation,
                "action": r.action_if_rejected,
            }
            for r in results
        ],
        "anomalies": [
            {
                "type": a.anomaly_type,
                "severity": a.severity.value,
                "metric": a.metric,
                "archetype": a.archetype,
                "description": a.description,
            }
            for a in anomalies
        ],
    }

    try:
        from adam.infrastructure.redis_client import get_redis
        redis = get_redis()
        if redis:
            key = f"{config.redis_prefix}:hypothesis_results:{data['date']}"
            redis.setex(key, config.snapshot_ttl_days * 86400, json.dumps(data))
            return
    except Exception:
        pass

    _MEMORY_HYPOTHESIS_RESULTS[data["date"]] = data


_MEMORY_HYPOTHESIS_RESULTS = {}


def get_latest_hypothesis_results():
    """Retrieve latest hypothesis results."""
    try:
        from adam.infrastructure.redis_client import get_redis
        redis = get_redis()
        if redis:
            date = time.strftime("%Y-%m-%d")
            key = f"{get_dcil_config().redis_prefix}:hypothesis_results:{date}"
            data = redis.get(key)
            if data:
                return json.loads(data)
    except Exception:
        pass

    if _MEMORY_HYPOTHESIS_RESULTS:
        return _MEMORY_HYPOTHESIS_RESULTS[max(_MEMORY_HYPOTHESIS_RESULTS.keys())]
    return None
