"""
DCIL Bridge Service
=====================

Syncs DCIL pipeline results from Redis to PostgreSQL for the management
platform. Bridges the gap between the automated DCIL tasks (which write
to Redis) and the management API (which reads from PostgreSQL).

Runs after DCIL Task 29 (coherence validation) to persist directives
for human review workflow.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

from adam.api.admin.db import get_db
from adam.intelligence.campaign_intelligence.config import get_dcil_config

logger = logging.getLogger(__name__)


async def sync_directives_to_postgres(campaign_id: str) -> int:
    """Sync DCIL directives from Redis to PostgreSQL for a specific campaign."""
    config = get_dcil_config()
    db = get_db()
    synced = 0

    directive_data = _load_from_redis_or_memory("validated_directives")
    if not directive_data:
        return 0

    for dd in directive_data.get("directives", []):
        directive_id = str(uuid.uuid4())
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        await db.execute(
            "INSERT INTO dcil_directives (id, campaign_id, directive_type, status, parameter, "
            "proposed_value, source_finding_id, rationale, bilateral_evidence, scope, "
            "confidence, expected_impact, created_at, updated_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)",
            directive_id, campaign_id, dd.get("type", ""),
            dd.get("status", "proposed"), dd.get("parameter", ""),
            json.dumps(dd.get("proposed_value", "")),
            dd.get("source_finding_id", ""), dd.get("rationale", ""),
            dd.get("bilateral_evidence", ""), dd.get("scope", ""),
            dd.get("confidence", 0), dd.get("expected_impact", ""),
            now, now,
        )
        synced += 1

    logger.info("Synced %d directives to PostgreSQL for campaign %s", synced, campaign_id)
    return synced


async def sync_performance_snapshot(campaign_id: str) -> bool:
    """Sync latest performance snapshot from Redis to PostgreSQL."""
    db = get_db()

    snapshot_data = _load_from_redis_or_memory("snapshot")
    if not snapshot_data:
        return False

    date = snapshot_data.get("date", time.strftime("%Y-%m-%d"))
    snap_id = str(uuid.uuid4())

    # Aggregate campaign-specific data from snapshot
    total_impressions = 0
    total_clicks = 0
    total_conversions = 0
    total_spend = 0.0
    total_revenue = 0.0

    for camp in snapshot_data.get("campaigns", []):
        total_impressions += camp.get("impressions", 0)
        total_clicks += camp.get("clicks", 0)
        total_conversions += camp.get("conversions", 0)
        total_spend += camp.get("spend", 0)
        total_revenue += camp.get("revenue", 0)

    ctr = total_clicks / total_impressions if total_impressions > 0 else 0
    cvr = total_conversions / total_clicks if total_clicks > 0 else 0
    cpa = total_spend / total_conversions if total_conversions > 0 else 0
    roas = total_revenue / total_spend if total_spend > 0 else 0

    try:
        await db.execute(
            "INSERT INTO campaign_performance_snapshots "
            "(id, campaign_id, snapshot_date, impressions, clicks, conversions, spend, revenue, ctr, cvr, cpa, roas, "
            "archetype_breakdown, domain_breakdown) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)",
            snap_id, campaign_id, date, total_impressions, total_clicks,
            total_conversions, total_spend, total_revenue, ctr, cvr, cpa, roas,
            json.dumps(snapshot_data.get("archetype_stats", {})),
            json.dumps(snapshot_data.get("domain_stats", {})),
        )
        return True
    except Exception as e:
        logger.warning("Performance snapshot sync failed: %s", e)
        return False


async def sync_report_to_postgres(
    campaign_id: str,
    organization_id: str,
    tier: str,
    report_data: Dict[str, Any],
    period_start: str,
    period_end: str,
) -> str:
    """Store a generated report in PostgreSQL."""
    db = get_db()
    report_id = str(uuid.uuid4())
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    await db.execute(
        "INSERT INTO reports (id, campaign_id, organization_id, tier, period_start, period_end, "
        "report_data, generated_at) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
        report_id, campaign_id, organization_id, tier, period_start, period_end,
        json.dumps(report_data), now,
    )

    return report_id


def _load_from_redis_or_memory(key_suffix: str) -> Optional[Dict]:
    """Load data from Redis or in-memory fallback."""
    config = get_dcil_config()
    date = time.strftime("%Y-%m-%d")

    try:
        from adam.infrastructure.redis_client import get_redis
        redis = get_redis()
        if redis:
            key = f"{config.redis_prefix}:{key_suffix}:{date}"
            data = redis.get(key)
            if data:
                return json.loads(data)
    except Exception:
        pass

    # Try memory fallbacks from DCIL tasks
    try:
        if key_suffix == "validated_directives":
            from adam.intelligence.daily.task_29_coherence_validation import _MEMORY_VALIDATED
            if date in _MEMORY_VALIDATED:
                return _MEMORY_VALIDATED[date]
        elif key_suffix == "snapshot":
            from adam.intelligence.daily.task_23_dsp_performance_pull import _MEMORY_SNAPSHOTS
            if date in _MEMORY_SNAPSHOTS:
                from adam.intelligence.daily.task_23_dsp_performance_pull import _snapshot_to_dict
                return _snapshot_to_dict(_MEMORY_SNAPSHOTS[date])
    except Exception:
        pass

    return None
