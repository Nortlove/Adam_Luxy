"""
Task 29: Coherence Validation
================================

Validates all generated directives against full platform state.
Enforces "no silo decisions" — every change is checked for cross-campaign
consistency, safety rails, cooldown periods, and temporal coherence.

Schedule: 07:00 UTC daily
"""

from __future__ import annotations

import json
import logging
import time
from typing import List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult
from adam.intelligence.campaign_intelligence.config import get_dcil_config

logger = logging.getLogger(__name__)


class CoherenceValidationTask(DailyStrengtheningTask):

    @property
    def name(self) -> str:
        return "coherence_validation"

    @property
    def schedule_hours(self) -> List[int]:
        return [7]

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        t0 = time.time()
        config = get_dcil_config()

        from adam.intelligence.daily.task_28_directive_generation import get_latest_directives
        from adam.intelligence.daily.task_23_dsp_performance_pull import get_latest_snapshot

        directive_data = get_latest_directives()
        snapshot = get_latest_snapshot()

        if not directive_data or not directive_data.get("directives"):
            return TaskResult(
                task_name=self.name, success=True,
                items_processed=0, items_stored=0,
                details={"message": "No directives to validate."},
            )

        from adam.intelligence.campaign_intelligence.models import (
            Directive, DirectiveType, DirectiveStatus, LearningScope,
        )
        from adam.intelligence.campaign_intelligence.coherence_validator import (
            PlatformCoherenceValidator, assemble_platform_state,
        )

        # Reconstruct directive objects
        directives = []
        for dd in directive_data.get("directives", []):
            d = Directive(
                directive_id=dd.get("directive_id", ""),
                directive_type=DirectiveType(dd.get("type", "budget_reallocation")),
                campaign_id=dd.get("campaign_id", ""),
                archetype=dd.get("archetype", ""),
                parameter=dd.get("parameter", ""),
                proposed_value=dd.get("proposed_value", ""),
                rationale=dd.get("rationale", ""),
                confidence=dd.get("confidence", 0),
                scope=LearningScope(dd.get("scope", "campaign_specific")),
                source_finding_id=dd.get("source_finding_id", ""),
            )
            directives.append(d)

        # Assemble platform state
        platform_state = assemble_platform_state(
            snapshot=snapshot,
            recent_directives=_load_recent_executed_directives(config),
        )

        # Validate
        validator = PlatformCoherenceValidator(config)
        validated = validator.validate(directives, platform_state)

        # Store validated directives
        _store_validated_directives(validated, config)

        approved = sum(1 for d in validated if d.status == DirectiveStatus.APPROVED)
        blocked = sum(1 for d in validated if d.status == DirectiveStatus.BLOCKED)
        capped = sum(1 for d in validated if d.status == DirectiveStatus.CAPPED)

        duration = time.time() - t0
        return TaskResult(
            task_name=self.name,
            success=True,
            items_processed=len(validated),
            items_stored=approved + capped,
            duration_seconds=duration,
            details={
                "approved": approved,
                "blocked": blocked,
                "capped": capped,
                "blocked_reasons": [d.blocked_reason for d in validated if d.blocked_reason],
            },
        )


def _load_recent_executed_directives(config):
    """Load directives executed in the last 7 days."""
    from adam.intelligence.campaign_intelligence.models import (
        Directive, DirectiveType, DirectiveStatus,
    )
    recent = []
    try:
        from adam.infrastructure.redis_client import get_redis
        from datetime import datetime, timedelta
        redis = get_redis()
        if redis:
            for i in range(7):
                d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
                key = f"{config.redis_prefix}:executed_directives:{d}"
                data = redis.get(key)
                if data:
                    for dd in json.loads(data).get("directives", []):
                        recent.append(Directive(
                            directive_id=dd.get("directive_id", ""),
                            directive_type=DirectiveType(dd.get("type", "budget_reallocation")),
                            status=DirectiveStatus(dd.get("status", "executed")),
                            campaign_id=dd.get("campaign_id", ""),
                            archetype=dd.get("archetype", ""),
                            parameter=dd.get("parameter", ""),
                            proposed_value=dd.get("proposed_value", ""),
                            executed_at=dd.get("executed_at", 0),
                        ))
    except Exception:
        pass
    return recent


_MEMORY_VALIDATED = {}


def _store_validated_directives(directives, config):
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
                "blocked_reason": d.blocked_reason,
                "confidence": d.confidence,
            }
            for d in directives
        ],
    }
    try:
        from adam.infrastructure.redis_client import get_redis
        redis = get_redis()
        if redis:
            key = f"{config.redis_prefix}:validated_directives:{date}"
            redis.setex(key, config.snapshot_ttl_days * 86400, json.dumps(data))
            return
    except Exception:
        pass
    _MEMORY_VALIDATED[date] = data


def get_latest_validated_directives():
    try:
        from adam.infrastructure.redis_client import get_redis
        redis = get_redis()
        if redis:
            date = time.strftime("%Y-%m-%d")
            key = f"{get_dcil_config().redis_prefix}:validated_directives:{date}"
            data = redis.get(key)
            if data:
                return json.loads(data)
    except Exception:
        pass
    if _MEMORY_VALIDATED:
        return _MEMORY_VALIDATED[max(_MEMORY_VALIDATED.keys())]
    return None
