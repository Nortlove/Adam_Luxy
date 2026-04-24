"""
Task 31: Tier Reporting
=========================

Generates all three report tiers:
  Tier A: Customer-facing (performance + archetype insights)
  Tier B: Optimization engine summary (what changed + why)
  Tier C: Internal audit (posterior state + generalizability + creative genealogy)

Report frequency decreases over time per the deployment package:
  Week 1: daily | Week 2-3: every 3 days | Week 4-6: weekly | Week 7+: biweekly

Schedule: 08:00 UTC daily (checks frequency before generating)
"""

from __future__ import annotations

import json
import logging
import time
from typing import List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult
from adam.intelligence.campaign_intelligence.config import get_dcil_config

logger = logging.getLogger(__name__)


class TierReportingTask(DailyStrengtheningTask):

    @property
    def name(self) -> str:
        return "tier_reporting"

    @property
    def schedule_hours(self) -> List[int]:
        return [8]

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        t0 = time.time()
        config = get_dcil_config()

        from adam.intelligence.daily.task_23_dsp_performance_pull import get_latest_snapshot
        from adam.intelligence.daily.task_25_hypothesis_testing import get_latest_hypothesis_results
        from adam.intelligence.daily.task_27_scope_determination import get_latest_scoped_learnings

        snapshot = get_latest_snapshot()
        hypothesis_data = get_latest_hypothesis_results()
        scoped_data = get_latest_scoped_learnings()

        reports_generated = []

        # Tier A: Customer-facing (check frequency)
        if self._should_generate_tier_a(config):
            tier_a = self._generate_tier_a(snapshot)
            _store_report("tier_a", tier_a, config)
            reports_generated.append("tier_a")

        # Tier B: Optimization engine (always generate)
        tier_b = self._generate_tier_b(snapshot, hypothesis_data, scoped_data)
        _store_report("tier_b", tier_b, config)
        reports_generated.append("tier_b")

        # Tier C: Internal audit (always generate)
        tier_c = self._generate_tier_c(snapshot, hypothesis_data, scoped_data)
        _store_report("tier_c", tier_c, config)
        reports_generated.append("tier_c")

        duration = time.time() - t0
        return TaskResult(
            task_name=self.name,
            success=True,
            items_processed=3,
            items_stored=len(reports_generated),
            duration_seconds=duration,
            details={"reports": reports_generated},
        )

    def _should_generate_tier_a(self, config) -> bool:
        """Check if Tier A report is due based on campaign age."""
        # For now, always generate. In production, check campaign start date
        # and apply the decreasing frequency schedule.
        return True

    def _generate_tier_a(self, snapshot) -> dict:
        """Customer-facing report: performance + archetype insights."""
        if not snapshot:
            return {"error": "No snapshot available."}

        archetype_dist = {}
        total_conv = max(snapshot.total_conversions, 1)
        for arch, stats in snapshot.archetype_stats.items():
            conv = stats.get("conversions", 0)
            archetype_dist[arch] = round(conv / total_conv * 100, 1)

        # Top domains by conversions
        top_domains = []
        domain_agg = {}
        for camp in snapshot.campaigns:
            for ds in camp.domain_stats:
                d = ds.get("domain", "")
                if d:
                    if d not in domain_agg:
                        domain_agg[d] = {"impressions": 0, "clicks": 0, "conversions": 0}
                    domain_agg[d]["impressions"] += ds.get("impressions", 0)
                    domain_agg[d]["conversions"] += ds.get("conversions", 0)

        for domain, stats in sorted(domain_agg.items(), key=lambda x: x[1]["conversions"], reverse=True)[:10]:
            top_domains.append({"domain": domain, **stats})

        # Customer psychology summary
        dominant = max(archetype_dist, key=archetype_dist.get) if archetype_dist else "unknown"
        profile_summaries = {
            "careful_truster": "Your converting customers value reliability and evidence over aspiration. They respond to prevention-framed messaging and concrete proof.",
            "status_seeker": "Your converting customers are motivated by identity and status signaling. They respond to gain-framed messaging and social proof.",
            "easy_decider": "Your converting customers prefer frictionless experiences. They respond to simplicity and automatic evaluation — remove barriers.",
            "dependable_loyalist": "Your converting customers seek consistent, dependable partnerships. They respond to evidence of reliability.",
            "reliable_cooperator": "Your converting customers are collaborative decision-makers. They respond to tools that make their job easier.",
        }

        return {
            "date": snapshot.date,
            "impressions": snapshot.total_impressions,
            "clicks": snapshot.total_clicks,
            "conversions": snapshot.total_conversions,
            "spend": snapshot.total_spend,
            "cpa": snapshot.overall_cpa,
            "roas": snapshot.overall_roas,
            "archetype_distribution": archetype_dist,
            "top_domains": top_domains,
            "customer_profile_summary": profile_summaries.get(dominant, "Analyzing customer psychology..."),
        }

    def _generate_tier_b(self, snapshot, hypothesis_data, scoped_data) -> dict:
        """Optimization engine summary: what changed and why."""
        return {
            "date": time.strftime("%Y-%m-%d"),
            "snapshot_available": snapshot is not None,
            "hypotheses_tested": len((hypothesis_data or {}).get("hypotheses", [])),
            "hypotheses": (hypothesis_data or {}).get("hypotheses", []),
            "anomalies": (hypothesis_data or {}).get("anomalies", []),
            "scoped_learnings": len((scoped_data or {}).get("learnings", [])),
            "scope_distribution": _count_scopes((scoped_data or {}).get("learnings", [])),
        }

    def _generate_tier_c(self, snapshot, hypothesis_data, scoped_data) -> dict:
        """Internal audit: posterior state + generalizability + system learning."""
        # Posterior state from Thompson sampler
        posteriors = {}
        try:
            from adam.meta_learner.thompson import get_thompson_sampler
            sampler = get_thompson_sampler()
            if hasattr(sampler, "posteriors"):
                posteriors = {k: {"alpha": v[0], "beta": v[1]} for k, v in sampler.posteriors.items()}
        except Exception:
            pass

        # Generalizability summary
        learnings = (scoped_data or {}).get("learnings", [])
        gen_summary = _count_scopes(learnings)

        return {
            "date": time.strftime("%Y-%m-%d"),
            "posterior_state": posteriors,
            "generalizability_summary": gen_summary,
            "scoped_learnings": learnings,
            "system_health": {
                "total_spend": snapshot.total_spend if snapshot else 0,
                "total_conversions": snapshot.total_conversions if snapshot else 0,
                "archetypes_active": len(snapshot.archetype_stats) if snapshot else 0,
            },
        }


def _count_scopes(learnings):
    counts = {}
    for sl in learnings:
        scope = sl.get("scope", "unknown")
        counts[scope] = counts.get(scope, 0) + 1
    return counts


def _store_report(tier, data, config):
    date = time.strftime("%Y-%m-%d")
    try:
        from adam.infrastructure.redis_client import get_redis
        redis = get_redis()
        if redis:
            key = f"{config.redis_prefix}:report:{tier}:{date}"
            redis.setex(key, config.snapshot_ttl_days * 86400, json.dumps(data))
    except Exception:
        pass
