"""
Task 24: Performance Normalizer
=================================

Maps raw DSP campaign data to INFORMATIV's psychological framework:
- Campaigns → archetypes
- Groups → mechanism assignments
- Computes per-archetype and per-mechanism matrices
- Computes rolling averages for trend detection
- Feeds new outcome data into the OutcomeHandler (triggers 22 learning systems)

Schedule: 04:15 UTC daily (after Task 23)
"""

from __future__ import annotations

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

# Campaign group → archetype mapping
# This maps the DSP's campaign group names to INFORMATIV archetypes.
# Extended as new campaigns are created.
GROUP_ARCHETYPE_MAP = {
    # LUXY-specific (from deployment package)
    "Corporate Executives": "careful_truster",
    "Travel Arrangers": "reliable_cooperator",
    "Travel Managers": "dependable_loyalist",
    "Home Market": "dependable_loyalist",
    "Event Planners": "prevention_planner",
    "Legal Vertical": "careful_truster",
    "Life Sciences": "careful_truster",
    "Financial Dealmakers": "status_seeker",
    "Private Aviation": "status_seeker",
    "CFO/T&E": "careful_truster",
    "Hotel B2B": "dependable_loyalist",
    "Supply Partners": "",
    # ZGM legacy campaigns
    "Professionals": "careful_truster",
    "Professionals-Kinective": "careful_truster",
    "Leisure Travel": "special_occasion",
    "Leisure Travel-Kinective": "special_occasion",
    "General Website RT": "repeat_loyal",
}

# Campaign group → primary mechanism mapping
GROUP_MECHANISM_MAP = {
    "Corporate Executives": "regulatory_focus",
    "Travel Arrangers": "construal_level",
    "Travel Managers": "regulatory_focus",
    "Home Market": "automatic_evaluation",
    "Event Planners": "construal_level",
    "Legal Vertical": "regulatory_focus",
    "Life Sciences": "regulatory_focus",
    "Financial Dealmakers": "identity_construction",
    "Private Aviation": "identity_construction",
    "CFO/T&E": "construal_level",
    "Professionals": "unknown",
    "Leisure Travel": "unknown",
    "General Website RT": "unknown",
}


class PerformanceNormalizerTask(DailyStrengtheningTask):

    @property
    def name(self) -> str:
        return "performance_normalizer"

    @property
    def schedule_hours(self) -> List[int]:
        return [4]

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        t0 = time.time()

        # Load latest snapshot
        from adam.intelligence.daily.task_23_dsp_performance_pull import get_latest_snapshot
        snapshot = get_latest_snapshot()

        if snapshot is None:
            return TaskResult(
                task_name=self.name,
                success=False,
                errors=1,
                details={"error": "No snapshot available. Task 23 may have failed."},
            )

        # 0. Provenance gate (Rule 7): refuse simulated data
        if snapshot.data_source == "simulated":
            return TaskResult(
                task_name=self.name,
                success=False,
                errors=1,
                details={"error": "PROVENANCE GATE: Snapshot is from simulated source. "
                         "Learning loop refuses simulated data (Rule 7). "
                         "A system that learns from theater becomes confidently wrong."},
            )
        snapshot.provenance_verified = True

        # 1. Map campaigns to archetypes and mechanisms
        mapped = 0
        for camp in snapshot.campaigns:
            archetype = GROUP_ARCHETYPE_MAP.get(camp.group_name, "")
            mechanism = GROUP_MECHANISM_MAP.get(camp.group_name, "")

            if not archetype:
                archetype = _infer_archetype_from_name(camp.name, camp.group_name)
            if not mechanism:
                mechanism = _infer_mechanism_from_name(camp.name)

            camp.archetype = archetype
            camp.mechanism = mechanism
            if archetype:
                mapped += 1

        # 2. Compute per-archetype aggregates
        archetype_agg: Dict[str, Dict[str, Any]] = {}
        for camp in snapshot.campaigns:
            if not camp.archetype or camp.status != "ACTIVE":
                continue
            if camp.archetype not in archetype_agg:
                archetype_agg[camp.archetype] = {
                    "impressions": 0, "clicks": 0, "conversions": 0,
                    "spend": 0.0, "revenue": 0.0, "campaigns": 0,
                }
            agg = archetype_agg[camp.archetype]
            agg["impressions"] += camp.impressions
            agg["clicks"] += camp.clicks
            agg["conversions"] += camp.conversions
            agg["spend"] += camp.spend
            agg["revenue"] += camp.revenue
            agg["campaigns"] += 1

        for arch, agg in archetype_agg.items():
            if agg["impressions"] > 0:
                agg["ctr"] = agg["clicks"] / agg["impressions"]
            if agg["conversions"] > 0:
                agg["cpa"] = agg["spend"] / agg["conversions"]
            if agg["clicks"] > 0:
                agg["cvr"] = agg["conversions"] / agg["clicks"]
            if agg["spend"] > 0 and agg["revenue"] > 0:
                agg["roas"] = agg["revenue"] / agg["spend"]

        snapshot.archetype_stats = archetype_agg

        # 3. Compute per-mechanism aggregates
        mechanism_agg: Dict[str, Dict[str, Any]] = {}
        for camp in snapshot.campaigns:
            if not camp.mechanism or camp.mechanism == "unknown" or camp.status != "ACTIVE":
                continue
            if camp.mechanism not in mechanism_agg:
                mechanism_agg[camp.mechanism] = {
                    "impressions": 0, "clicks": 0, "conversions": 0,
                    "spend": 0.0, "campaigns": 0,
                }
            agg = mechanism_agg[camp.mechanism]
            agg["impressions"] += camp.impressions
            agg["clicks"] += camp.clicks
            agg["conversions"] += camp.conversions
            agg["spend"] += camp.spend
            agg["campaigns"] += 1

        for mech, agg in mechanism_agg.items():
            if agg["impressions"] > 0:
                agg["ctr"] = agg["clicks"] / agg["impressions"]
            if agg["conversions"] > 0:
                agg["cpa"] = agg["spend"] / agg["conversions"]

        snapshot.mechanism_stats = mechanism_agg

        # 4. Compute rolling averages from historical snapshots
        snapshot.rolling_3d = _compute_rolling_average(snapshot.date, 3)
        snapshot.rolling_7d = _compute_rolling_average(snapshot.date, 7)

        # 5. Update the stored snapshot with normalized data
        _update_stored_snapshot(snapshot)

        # 6. Feed into learning systems via OutcomeHandler
        learning_fed = await _feed_outcome_handler(snapshot)

        duration = time.time() - t0
        return TaskResult(
            task_name=self.name,
            success=True,
            items_processed=len(snapshot.campaigns),
            items_stored=mapped,
            duration_seconds=duration,
            details={
                "campaigns_mapped": mapped,
                "archetypes_found": list(archetype_agg.keys()),
                "mechanisms_found": list(mechanism_agg.keys()),
                "learning_fed": learning_fed,
            },
        )


def _infer_archetype_from_name(campaign_name: str, group_name: str) -> str:
    """Infer archetype from campaign/group name when no mapping exists."""
    name_lower = (campaign_name + " " + group_name).lower()

    if any(kw in name_lower for kw in ["informativ", "careful_truster", "ct-"]):
        return "careful_truster"
    if any(kw in name_lower for kw in ["status_seeker", "ss-"]):
        return "status_seeker"
    if any(kw in name_lower for kw in ["easy_decider", "ed-"]):
        return "easy_decider"
    if any(kw in name_lower for kw in ["executive", "corporate"]):
        return "careful_truster"
    if any(kw in name_lower for kw in ["leisure", "vacation"]):
        return "special_occasion"
    if any(kw in name_lower for kw in ["retarget", "rt", "remarketing"]):
        return "repeat_loyal"

    return ""


def _infer_mechanism_from_name(campaign_name: str) -> str:
    """Infer mechanism from campaign name patterns."""
    name_lower = campaign_name.lower()
    if "authority" in name_lower:
        return "regulatory_focus"
    if "social" in name_lower or "proof" in name_lower:
        return "mimetic_desire"
    if "ease" in name_lower or "simple" in name_lower:
        return "automatic_evaluation"
    if "identity" in name_lower or "status" in name_lower:
        return "identity_construction"
    return ""


def _compute_rolling_average(current_date: str, window_days: int) -> Optional[Dict[str, float]]:
    """Compute rolling average from historical snapshots."""
    try:
        from adam.intelligence.daily.task_23_dsp_performance_pull import (
            get_latest_snapshot,
            _MEMORY_SNAPSHOTS,
        )
        import json
        from adam.infrastructure.redis_client import get_redis
        from adam.intelligence.campaign_intelligence.config import get_dcil_config

        config = get_dcil_config()
        redis = get_redis()

        snapshots = []
        if redis:
            from datetime import datetime, timedelta
            base_date = datetime.strptime(current_date, "%Y-%m-%d")
            for i in range(1, window_days + 1):
                d = (base_date - timedelta(days=i)).strftime("%Y-%m-%d")
                key = f"{config.redis_prefix}:snapshot:{d}"
                data = redis.get(key)
                if data:
                    snapshots.append(json.loads(data))
        else:
            for date_key, snap in sorted(_MEMORY_SNAPSHOTS.items(), reverse=True):
                if date_key < current_date and len(snapshots) < window_days:
                    snapshots.append({"total_spend": snap.total_spend, "total_conversions": snap.total_conversions, "overall_cpa": snap.overall_cpa, "overall_ctr": snap.overall_ctr})

        if not snapshots:
            return None

        n = len(snapshots)
        return {
            "avg_spend": sum(s.get("total_spend", 0) for s in snapshots) / n,
            "avg_conversions": sum(s.get("total_conversions", 0) for s in snapshots) / n,
            "avg_cpa": sum(s.get("overall_cpa", 0) for s in snapshots) / n,
            "avg_ctr": sum(s.get("overall_ctr", 0) for s in snapshots) / n,
            "window_days": n,
        }
    except Exception as e:
        logger.debug("Rolling average computation failed: %s", e)
        return None


def _update_stored_snapshot(snapshot: PerformanceSnapshot) -> None:
    """Update the stored snapshot with normalized archetype/mechanism data."""
    try:
        import json
        from adam.infrastructure.redis_client import get_redis
        from adam.intelligence.campaign_intelligence.config import get_dcil_config
        from adam.intelligence.daily.task_23_dsp_performance_pull import _snapshot_to_dict

        config = get_dcil_config()
        redis = get_redis()
        if redis:
            key = f"{config.redis_prefix}:snapshot:{snapshot.date}"
            redis.setex(key, config.snapshot_ttl_days * 86400, json.dumps(_snapshot_to_dict(snapshot)))
    except Exception as e:
        logger.debug("Snapshot update failed: %s", e)

    from adam.intelligence.daily.task_23_dsp_performance_pull import _MEMORY_SNAPSHOTS
    _MEMORY_SNAPSHOTS[snapshot.date] = snapshot


async def _feed_outcome_handler(snapshot) -> bool:
    """Feed campaign performance data into the learning systems."""
    try:
        from adam.intelligence.inferential_learning_agent import get_inferential_agent
        agent = get_inferential_agent()

        for camp in snapshot.campaigns:
            if not camp.archetype or camp.status != "ACTIVE":
                continue

            agent.observe({
                "archetype": camp.archetype,
                "mechanism": camp.mechanism,
                "domain_category": "mixed",
                "impressions": camp.impressions,
                "clicks": camp.clicks,
                "conversions": camp.conversions,
                "spend": camp.spend,
                "ctr": camp.ctr,
                "cpa": camp.cpa,
                "source": "dcil_daily_pull",
                "campaign_id": camp.campaign_id,
                "campaign_name": camp.name,
            })

        return True
    except Exception as e:
        logger.debug("Learning feed failed: %s", e)
        return False
