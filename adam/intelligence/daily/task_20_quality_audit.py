"""
Task 20: Learning Quality Audit

Runs LearningQualityAuditor.run_full_audit() to evaluate whether the
system is actually learning from outcomes — not just updating posteriors.

Answers: "Is ADAM getting smarter, or just going through the motions?"

Schedule: Weekly at 7 AM UTC (Sundays, after task_18 recalibration).
"""

from __future__ import annotations

import logging
from typing import List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


class LearningQualityAuditTask(DailyStrengtheningTask):
    """Weekly learning quality audit."""

    @property
    def name(self) -> str:
        return "learning_quality_audit"

    @property
    def schedule_hours(self) -> List[int]:
        return [7]

    @property
    def frequency_hours(self) -> int:
        return 24 * 7

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        try:
            from adam.core.learning.quality_audit import LearningQualityAuditor
            from adam.core.dependencies import get_infrastructure
            from adam.core.learning.unified_learning_hub import get_unified_learning_hub

            infra = await get_infrastructure()
            neo4j_driver = getattr(infra, "neo4j_driver", None)
            redis_client = getattr(infra, "redis", None)

            if not neo4j_driver:
                result.details["skipped"] = "no_neo4j_driver"
                return result

            hub = get_unified_learning_hub()
            component_registry = {}
            if hub and hasattr(hub, "_components"):
                component_registry = hub._components

            auditor = LearningQualityAuditor(
                neo4j_driver=neo4j_driver,
                redis_client=redis_client,
                component_registry=component_registry,
            )
            audit_result = await auditor.run_full_audit()

            result.details["overall_score"] = audit_result.overall_score
            result.details["dimensions"] = {
                d.dimension.value: d.score
                for d in audit_result.dimension_scores
            }
            result.details["issues"] = [
                {"severity": i.severity, "description": i.description}
                for i in audit_result.issues[:5]
            ]
            result.items_processed = len(audit_result.component_results)

        except Exception as exc:
            logger.debug("Learning quality audit skipped: %s", exc)
            result.details["skipped"] = str(exc)

        return result
