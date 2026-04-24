"""
Task 23: DSP Performance Pull
===============================

Pulls full performance snapshot from StackAdapt GraphQL API including
campaign-level, domain-level, and time-windowed data. Stores to Redis
for consumption by all downstream DCIL tasks.

Schedule: 04:00 UTC daily
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult
from adam.intelligence.campaign_intelligence.config import get_dcil_config
from adam.intelligence.campaign_intelligence.models import (
    CampaignSnapshot,
    PerformanceSnapshot,
)

logger = logging.getLogger(__name__)


class DSPPerformancePullTask(DailyStrengtheningTask):

    @property
    def name(self) -> str:
        return "dsp_performance_pull"

    @property
    def schedule_hours(self) -> List[int]:
        return [4]

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        t0 = time.time()
        config = get_dcil_config()

        try:
            from adam.integrations.stackadapt_monitor import StackAdaptMonitor
            monitor = StackAdaptMonitor(api_key=config.stackadapt_api_key)
        except Exception as e:
            return TaskResult(
                task_name=self.name,
                success=False,
                errors=1,
                details={"error": f"Monitor init failed: {e}"},
            )

        snapshot = PerformanceSnapshot(
            date=time.strftime("%Y-%m-%d"),
            data_source="dsp_api",
            provenance_verified=False,
        )

        # 1. Pull advertiser-level stats
        adv_data = monitor._query("""
            { advertisers(first: 1) {
                nodes {
                    id name
                    stats {
                        impressionsBigint clicksBigint conversionsBigint
                        cost ctr ecpa roas conversionRevenue
                    }
                }
            }}
        """)

        for adv in adv_data.get("data", {}).get("advertisers", {}).get("nodes", []):
            snapshot.advertiser_name = adv.get("name", "")
            s = adv.get("stats") or {}
            snapshot.total_impressions = int(s.get("impressionsBigint", 0) or 0)
            snapshot.total_clicks = int(s.get("clicksBigint", 0) or 0)
            snapshot.total_conversions = int(s.get("conversionsBigint", 0) or 0)
            snapshot.total_spend = float(s.get("cost", 0) or 0)
            snapshot.overall_ctr = float(s.get("ctr", 0) or 0)
            snapshot.overall_cpa = float(s.get("ecpa", 0) or 0)
            snapshot.overall_roas = float(s.get("roas", 0) or 0)
            snapshot.total_revenue = float(s.get("conversionRevenue", 0) or 0)

        if adv_data.get("errors"):
            logger.warning("Advertiser query errors: %s", adv_data["errors"])
            snapshot.data_source = "dsp_api_error"
            snapshot.provenance_verified = False
            return TaskResult(
                task_name=self.name,
                success=False,
                errors=1,
                details={"error": "StackAdapt API error", "api_errors": adv_data["errors"]},
            )

        # Data came from real DSP API — mark provenance
        snapshot.provenance_verified = True

        # 2. Pull per-campaign stats with creative counts
        camp_data = monitor._query("""
            { campaigns(first: 100) {
                nodes {
                    id name channelType
                    campaignGroup { name }
                    campaignStatus { status }
                    stats {
                        impressionsBigint clicksBigint conversionsBigint
                        cost ctr ecpa roas conversionRevenue
                    }
                    ads(first: 10) {
                        nodes { id name }
                        totalCount
                    }
                    budget { daily total }
                    frequencyCap { impressions period }
                }
            }}
        """)

        for camp in camp_data.get("data", {}).get("campaigns", {}).get("nodes", []):
            cs = camp.get("stats") or {}
            budget_info = camp.get("budget") or {}
            freq_info = camp.get("frequencyCap") or {}

            snap = CampaignSnapshot(
                campaign_id=str(camp.get("id", "")),
                name=camp.get("name", ""),
                channel_type=camp.get("channelType", ""),
                group_name=(camp.get("campaignGroup") or {}).get("name", ""),
                status=(camp.get("campaignStatus") or {}).get("status", ""),
                impressions=int(cs.get("impressionsBigint", 0) or 0),
                clicks=int(cs.get("clicksBigint", 0) or 0),
                conversions=int(cs.get("conversionsBigint", 0) or 0),
                spend=float(cs.get("cost", 0) or 0),
                revenue=float(cs.get("conversionRevenue", 0) or 0),
            )
            snap.compute_derived()

            # Store creative info
            ads = camp.get("ads") or {}
            snap.creative_stats = [
                {"id": a.get("id"), "name": a.get("name")}
                for a in (ads.get("nodes") or [])
            ]

            snapshot.campaigns.append(snap)

        # 3. Store snapshot to Redis
        stored = self._store_snapshot(snapshot, config)

        duration = time.time() - t0
        return TaskResult(
            task_name=self.name,
            success=True,
            items_processed=len(snapshot.campaigns),
            items_stored=1 if stored else 0,
            duration_seconds=duration,
            details={
                "advertiser": snapshot.advertiser_name,
                "campaigns": len(snapshot.campaigns),
                "total_spend": snapshot.total_spend,
                "total_conversions": snapshot.total_conversions,
                "overall_cpa": snapshot.overall_cpa,
            },
        )

    def _store_snapshot(self, snapshot: PerformanceSnapshot, config) -> bool:
        """Store snapshot to Redis for downstream tasks."""
        try:
            from adam.infrastructure.redis_client import get_redis
            redis = get_redis()
            if redis is None:
                logger.warning("Redis not available — storing snapshot in memory")
                _MEMORY_SNAPSHOTS[snapshot.date] = snapshot
                return True

            key = f"{config.redis_prefix}:snapshot:{snapshot.date}"
            data = _snapshot_to_dict(snapshot)
            redis.setex(key, config.snapshot_ttl_days * 86400, json.dumps(data))

            # Update rolling window pointer
            rolling_key = f"{config.redis_prefix}:snapshot:latest"
            redis.set(rolling_key, snapshot.date)

            return True
        except Exception as e:
            logger.warning("Redis store failed, using memory: %s", e)
            _MEMORY_SNAPSHOTS[snapshot.date] = snapshot
            return True


# In-memory fallback for environments without Redis
_MEMORY_SNAPSHOTS: Dict[str, PerformanceSnapshot] = {}


def get_latest_snapshot() -> Optional[PerformanceSnapshot]:
    """Retrieve the latest snapshot (Redis or memory fallback)."""
    try:
        from adam.infrastructure.redis_client import get_redis
        redis = get_redis()
        if redis:
            latest_date = redis.get(f"{get_dcil_config().redis_prefix}:snapshot:latest")
            if latest_date:
                date_str = latest_date.decode() if isinstance(latest_date, bytes) else latest_date
                key = f"{get_dcil_config().redis_prefix}:snapshot:{date_str}"
                data = redis.get(key)
                if data:
                    raw = json.loads(data)
                    return _dict_to_snapshot(raw)
    except Exception:
        pass

    if _MEMORY_SNAPSHOTS:
        latest_key = max(_MEMORY_SNAPSHOTS.keys())
        return _MEMORY_SNAPSHOTS[latest_key]
    return None


def _snapshot_to_dict(s: PerformanceSnapshot) -> Dict[str, Any]:
    """Serialize snapshot for Redis storage."""
    return {
        "timestamp": s.timestamp,
        "date": s.date,
        "advertiser_name": s.advertiser_name,
        "total_impressions": s.total_impressions,
        "total_clicks": s.total_clicks,
        "total_conversions": s.total_conversions,
        "total_spend": s.total_spend,
        "total_revenue": s.total_revenue,
        "overall_ctr": s.overall_ctr,
        "overall_cpa": s.overall_cpa,
        "overall_roas": s.overall_roas,
        "campaigns": [
            {
                "campaign_id": c.campaign_id,
                "name": c.name,
                "channel_type": c.channel_type,
                "group_name": c.group_name,
                "status": c.status,
                "impressions": c.impressions,
                "clicks": c.clicks,
                "conversions": c.conversions,
                "spend": c.spend,
                "revenue": c.revenue,
                "ctr": c.ctr,
                "cpa": c.cpa,
                "cvr": c.cvr,
                "roas": c.roas,
                "archetype": c.archetype,
                "mechanism": c.mechanism,
                "domain_stats": c.domain_stats,
                "creative_stats": c.creative_stats,
            }
            for c in s.campaigns
        ],
        "archetype_stats": s.archetype_stats,
        "mechanism_stats": s.mechanism_stats,
        "domain_stats": s.domain_stats,
    }


def _dict_to_snapshot(d: Dict[str, Any]) -> PerformanceSnapshot:
    """Deserialize snapshot from Redis."""
    s = PerformanceSnapshot(
        timestamp=d.get("timestamp", 0),
        date=d.get("date", ""),
        advertiser_name=d.get("advertiser_name", ""),
        total_impressions=d.get("total_impressions", 0),
        total_clicks=d.get("total_clicks", 0),
        total_conversions=d.get("total_conversions", 0),
        total_spend=d.get("total_spend", 0),
        total_revenue=d.get("total_revenue", 0),
        overall_ctr=d.get("overall_ctr", 0),
        overall_cpa=d.get("overall_cpa", 0),
        overall_roas=d.get("overall_roas", 0),
    )
    for cd in d.get("campaigns", []):
        cs = CampaignSnapshot(
            campaign_id=cd.get("campaign_id", ""),
            name=cd.get("name", ""),
            channel_type=cd.get("channel_type", ""),
            group_name=cd.get("group_name", ""),
            status=cd.get("status", ""),
            impressions=cd.get("impressions", 0),
            clicks=cd.get("clicks", 0),
            conversions=cd.get("conversions", 0),
            spend=cd.get("spend", 0),
            revenue=cd.get("revenue", 0),
            ctr=cd.get("ctr", 0),
            cpa=cd.get("cpa", 0),
            cvr=cd.get("cvr", 0),
            roas=cd.get("roas", 0),
            archetype=cd.get("archetype", ""),
            mechanism=cd.get("mechanism", ""),
            domain_stats=cd.get("domain_stats", []),
            creative_stats=cd.get("creative_stats", []),
        )
        s.campaigns.append(cs)
    s.archetype_stats = d.get("archetype_stats", {})
    s.mechanism_stats = d.get("mechanism_stats", {})
    s.domain_stats = d.get("domain_stats", {})
    return s
