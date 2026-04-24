"""
Task 26: Bilateral Analysis
==============================

Runs the InferentialLearningAgent cycle with current performance data,
updates gradient fields, and collects confirmed propositions for
downstream scope determination.

Schedule: 05:00 UTC daily (parallel with Task 25)
"""

from __future__ import annotations

import json
import logging
import time
from typing import List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult
from adam.intelligence.campaign_intelligence.config import get_dcil_config

logger = logging.getLogger(__name__)


class BilateralAnalysisTask(DailyStrengtheningTask):

    @property
    def name(self) -> str:
        return "bilateral_analysis"

    @property
    def schedule_hours(self) -> List[int]:
        return [5]

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        t0 = time.time()

        from adam.intelligence.daily.task_23_dsp_performance_pull import get_latest_snapshot
        snapshot = get_latest_snapshot()

        if snapshot is None:
            return TaskResult(
                task_name=self.name, success=False, errors=1,
                details={"error": "No snapshot available."},
            )

        # 1. Run inferential learning cycle
        propositions = []
        actions = {}
        try:
            from adam.intelligence.inferential_learning_agent import get_inferential_agent
            agent = get_inferential_agent()

            performance_data = {
                "archetypes": snapshot.archetype_stats,
                "mechanisms": snapshot.mechanism_stats,
                "total_conversions": snapshot.total_conversions,
                "total_spend": snapshot.total_spend,
                "overall_cpa": snapshot.overall_cpa,
                "source": "dcil_daily",
            }

            cycle_result = agent.run_learning_cycle(performance_data)
            propositions = cycle_result.get("new_propositions", [])
            actions = cycle_result.get("actions", {})
        except Exception as e:
            logger.warning("Inferential agent cycle failed: %s", e)

        # 2. Propagate through knowledge propagation network
        propagated = 0
        try:
            from adam.intelligence.knowledge_propagation import get_propagation_network
            kpn = get_propagation_network()

            for arch, stats in snapshot.archetype_stats.items():
                if stats.get("conversions", 0) > 0:
                    kpn.process_outcome({
                        "archetype": arch,
                        "mechanism": "mixed",
                        "outcome_value": 1.0,
                        "cpa": stats.get("cpa", 0),
                        "source": "dcil_daily",
                    })
                    propagated += 1

            kpn.flush_batched()
        except Exception as e:
            logger.debug("KPN propagation failed: %s", e)

        # 3. Store results
        analysis_data = {
            "timestamp": time.time(),
            "date": time.strftime("%Y-%m-%d"),
            "propositions_count": len(propositions),
            "actions": actions,
            "propagated_signals": propagated,
        }

        _store_analysis_results(analysis_data)

        duration = time.time() - t0
        return TaskResult(
            task_name=self.name,
            success=True,
            items_processed=len(snapshot.archetype_stats),
            items_stored=len(propositions),
            duration_seconds=duration,
            details={
                "propositions": len(propositions),
                "actions": len(actions),
                "kpn_signals": propagated,
            },
        )


_MEMORY_ANALYSIS_RESULTS = {}


def _store_analysis_results(data):
    config = get_dcil_config()
    try:
        from adam.infrastructure.redis_client import get_redis
        redis = get_redis()
        if redis:
            key = f"{config.redis_prefix}:analysis_results:{data['date']}"
            redis.setex(key, config.snapshot_ttl_days * 86400, json.dumps(data))
            return
    except Exception:
        pass
    _MEMORY_ANALYSIS_RESULTS[data["date"]] = data


def get_latest_analysis_results():
    try:
        from adam.infrastructure.redis_client import get_redis
        redis = get_redis()
        if redis:
            date = time.strftime("%Y-%m-%d")
            key = f"{get_dcil_config().redis_prefix}:analysis_results:{date}"
            data = redis.get(key)
            if data:
                return json.loads(data)
    except Exception:
        pass
    if _MEMORY_ANALYSIS_RESULTS:
        return _MEMORY_ANALYSIS_RESULTS[max(_MEMORY_ANALYSIS_RESULTS.keys())]
    return None
