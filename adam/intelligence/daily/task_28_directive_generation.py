"""
Task 28: Directive Generation
================================

Converts findings from hypothesis testing, scoped learnings, and
inferential agent into executable optimization directives.

Schedule: 06:30 UTC daily
"""

from __future__ import annotations

import json
import logging
import time
from typing import List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult
from adam.intelligence.campaign_intelligence.config import get_dcil_config

logger = logging.getLogger(__name__)


class DirectiveGenerationTask(DailyStrengtheningTask):

    @property
    def name(self) -> str:
        return "directive_generation"

    @property
    def schedule_hours(self) -> List[int]:
        return [6]

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        t0 = time.time()
        config = get_dcil_config()

        from adam.intelligence.daily.task_23_dsp_performance_pull import get_latest_snapshot
        from adam.intelligence.daily.task_25_hypothesis_testing import get_latest_hypothesis_results
        from adam.intelligence.daily.task_27_scope_determination import get_latest_scoped_learnings
        from adam.intelligence.daily.task_26_bilateral_analysis import get_latest_analysis_results

        snapshot = get_latest_snapshot()
        hypothesis_data = get_latest_hypothesis_results() or {"hypotheses": [], "anomalies": []}
        scoped_data = get_latest_scoped_learnings() or {"learnings": []}
        analysis_data = get_latest_analysis_results() or {}

        if snapshot is None:
            return TaskResult(task_name=self.name, success=False, errors=1,
                              details={"error": "No snapshot available."})

        from adam.intelligence.campaign_intelligence.directive_generator import OptimizationDirectiveGenerator
        from adam.intelligence.campaign_intelligence.models import ScopedLearning, LearningScope

        generator = OptimizationDirectiveGenerator(config)

        scoped_learnings = []
        for sl_data in scoped_data.get("learnings", []):
            scoped_learnings.append(ScopedLearning(
                finding_id=sl_data.get("finding_id", ""),
                finding_type=sl_data.get("finding_type", ""),
                statement=sl_data.get("statement", ""),
                scope=LearningScope(sl_data.get("scope", "campaign_specific")),
                i_squared=sl_data.get("i_squared", 100),
                tau_squared=sl_data.get("tau_squared", 0),
                effect_size=sl_data.get("effect_size", 0),
                n_studies=sl_data.get("n_studies", 0),
                affected_archetypes=sl_data.get("affected_archetypes", []),
                affected_campaigns=sl_data.get("affected_campaigns", []),
            ))

        directives = generator.generate(
            snapshot=snapshot,
            hypothesis_data=hypothesis_data,
            scoped_learnings=scoped_learnings,
            inferential_actions=analysis_data.get("actions"),
        )

        _store_directives(directives, config)

        duration = time.time() - t0
        return TaskResult(
            task_name=self.name,
            success=True,
            items_processed=len(hypothesis_data.get("hypotheses", [])) + len(scoped_learnings),
            items_stored=len(directives),
            duration_seconds=duration,
            details={
                "directives_generated": len(directives),
                "by_type": _count_by_type(directives),
            },
        )


def _count_by_type(directives):
    counts = {}
    for d in directives:
        t = d.directive_type.value
        counts[t] = counts.get(t, 0) + 1
    return counts


_MEMORY_DIRECTIVES = {}


def _store_directives(directives, config):
    from adam.intelligence.campaign_intelligence.models import DirectiveStatus
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
                "rationale": d.rationale,
                "bilateral_evidence": d.bilateral_evidence,
                "confidence": d.confidence,
                "scope": d.scope.value if hasattr(d.scope, 'value') else str(d.scope),
                "source_finding_id": d.source_finding_id,
                "expected_impact": d.expected_impact,
            }
            for d in directives
        ],
    }
    try:
        from adam.infrastructure.redis_client import get_redis
        redis = get_redis()
        if redis:
            key = f"{config.redis_prefix}:directives:{date}"
            redis.setex(key, config.snapshot_ttl_days * 86400, json.dumps(data))
            return
    except Exception:
        pass
    _MEMORY_DIRECTIVES[date] = data


def get_latest_directives():
    try:
        from adam.infrastructure.redis_client import get_redis
        redis = get_redis()
        if redis:
            date = time.strftime("%Y-%m-%d")
            key = f"{get_dcil_config().redis_prefix}:directives:{date}"
            data = redis.get(key)
            if data:
                return json.loads(data)
    except Exception:
        pass
    if _MEMORY_DIRECTIVES:
        return _MEMORY_DIRECTIVES[max(_MEMORY_DIRECTIVES.keys())]
    return None
