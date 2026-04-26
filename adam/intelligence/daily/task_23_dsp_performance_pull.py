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
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult
from adam.intelligence.campaign_intelligence.config import get_dcil_config
from adam.intelligence.campaign_intelligence.models import (
    CampaignSnapshot,
    PerformanceSnapshot,
)


# 30-day rolling window for per-campaign delivery metrics. Mirrors the
# dashboard service.py window — same window in both surfaces means the
# threshold-fallback path and the DCIL path see the same per-campaign
# CPA / spend / CTR figures, which keeps the Pinker override coherent.
# (DCIL gets priority over threshold per campaign; if the windows
# diverged, the override would compare apples to oranges.)
_DELIVERY_WINDOW_DAYS = 30


def _campaign_window() -> tuple[str, str]:
    """30-day rolling window ending today (UTC). Returns (from, to) ISO dates."""
    today = datetime.now(timezone.utc).date()
    return (
        (today - timedelta(days=_DELIVERY_WINDOW_DAYS)).isoformat(),
        today.isoformat(),
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

        # 2. Pull campaign list (metadata only) + per-campaign delivery metrics.
        #
        # StackAdapt removed Campaign.stats from the schema — per-campaign
        # metrics now live on the top-level campaignDelivery resolver. We
        # join in two queries:
        #   - campaigns(first:100) → id, name, channel, group, status, ads
        #   - campaignDelivery(dataType:TABLE, granularity:TOTAL, date:{from,to})
        #     → metrics per campaign WITH activity in the window
        # Campaigns without delivery records get zero metrics — DCIL upstream
        # tasks (hypothesis testing, scope determination) correctly produce
        # no findings on zero metrics, which is the right behavior for
        # campaigns that haven't been live in the window.
        #
        # Same window/shape as adam/api/dashboard/service.py so the DCIL
        # path and the threshold-fallback path see identical per-campaign
        # figures (Pinker override coherence).
        from_date, to_date = _campaign_window()

        camp_data = monitor._query(
            """
            query CampaignsList {
              campaigns(first: 100) {
                nodes {
                  id name channelType
                  campaignGroup { name }
                  campaignStatus { status }
                  ads(first: 10) { nodes { id name } totalCount }
                }
              }
            }
            """,
        )

        delivery_data = monitor._query(
            """
            query CampaignDelivery($from: ISO8601Date!, $to: ISO8601Date!) {
              campaignDelivery(
                dataType: TABLE,
                granularity: TOTAL,
                date: { from: $from, to: $to }
              ) {
                __typename
                ... on CampaignDeliveryOutcome {
                  records {
                    nodes {
                      campaign { id }
                      metrics {
                        impressionsBigint clicksBigint conversionsBigint
                        cost ctr ecpa roas conversionRevenue
                      }
                    }
                  }
                }
                ... on Progress { _ }
              }
            }
            """,
            variables={"from": from_date, "to": to_date},
        )

        # Build campaign_id → metrics map from delivery records. Empty map
        # if Progress (async pending), errors, or missing — campaigns get
        # zero metrics, which downstream tasks treat as "no signal."
        delivery_metrics_by_id: Dict[str, Dict[str, Any]] = {}
        delivery = (delivery_data.get("data") or {}).get("campaignDelivery") or {}
        if delivery.get("__typename") == "CampaignDeliveryOutcome":
            for rec in (delivery.get("records") or {}).get("nodes") or []:
                cid = (rec.get("campaign") or {}).get("id")
                if cid:
                    delivery_metrics_by_id[str(cid)] = rec.get("metrics") or {}
        elif delivery.get("__typename") == "Progress":
            logger.info(
                "task_23: campaignDelivery returned Progress (async pending); "
                "per-campaign metrics will be zero for this snapshot"
            )

        for camp in camp_data.get("data", {}).get("campaigns", {}).get("nodes", []):
            cid = str(camp.get("id", ""))
            metrics = delivery_metrics_by_id.get(cid) or {}

            snap = CampaignSnapshot(
                campaign_id=cid,
                name=camp.get("name", ""),
                channel_type=camp.get("channelType", ""),
                group_name=(camp.get("campaignGroup") or {}).get("name", ""),
                status=(camp.get("campaignStatus") or {}).get("status", ""),
                impressions=int(metrics.get("impressionsBigint", 0) or 0),
                clicks=int(metrics.get("clicksBigint", 0) or 0),
                conversions=int(metrics.get("conversionsBigint", 0) or 0),
                spend=float(metrics.get("cost", 0) or 0),
                revenue=float(metrics.get("conversionRevenue", 0) or 0),
            )
            snap.compute_derived()

            # Store creative info from the campaigns query (ads still
            # resolves on Campaign in the current schema).
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
