"""
StackAdapt Campaign Monitor
=============================

Pulls live performance data from StackAdapt's GraphQL API and feeds
it into INFORMATIV's learning systems. Produces weekly intelligence
briefs and identifies optimization opportunities.

This is the READ side of the integration — works with the current
API key permissions (no write access needed).

Usage:
    from adam.integrations.stackadapt_monitor import StackAdaptMonitor
    monitor = StackAdaptMonitor()
    report = monitor.pull_and_analyze()
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

GRAPHQL_ENDPOINT = "https://api.stackadapt.com/graphql"


@dataclass
class CampaignStats:
    """Stats for one campaign from StackAdapt."""
    campaign_id: str
    name: str
    channel_type: str
    group_name: str
    status: str
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0.0
    ctr: float = 0.0
    cpa: float = 0.0
    roas: float = 0.0


@dataclass
class MonitorReport:
    """Complete monitoring report."""
    timestamp: float = field(default_factory=time.time)
    advertiser_name: str = ""

    # Aggregate stats
    total_impressions: int = 0
    total_clicks: int = 0
    total_conversions: int = 0
    total_spend: float = 0.0
    overall_ctr: float = 0.0
    overall_cpa: float = 0.0

    # Per-campaign
    campaigns: List[CampaignStats] = field(default_factory=list)

    # Per-group (maps to archetypes)
    group_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # INFORMATIV analysis
    opportunities: List[Dict[str, str]] = field(default_factory=list)
    learning_fed: bool = False


class StackAdaptMonitor:
    """Monitors StackAdapt campaigns and feeds data to INFORMATIV."""

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get(
            "STACKADAPT_GRAPHQL_KEY",
            "eff852132f1db1ece9317c5b7c55e5b94f13df3cf9a8076488c90d5d408feb88"
        )

    def _query(self, query: str) -> Dict:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        try:
            r = requests.post(
                GRAPHQL_ENDPOINT,
                json={"query": query},
                headers=headers,
                timeout=30,
            )
            return r.json()
        except Exception as e:
            logger.error("StackAdapt query failed: %s", e)
            return {"errors": [{"message": str(e)}]}

    def pull_and_analyze(self) -> MonitorReport:
        """Pull current stats and produce analysis."""
        report = MonitorReport()

        # 1. Get advertiser-level stats
        adv_data = self._query("""
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
            report.advertiser_name = adv["name"]
            s = adv.get("stats", {}) or {}
            report.total_impressions = int(s.get("impressionsBigint", 0) or 0)
            report.total_clicks = int(s.get("clicksBigint", 0) or 0)
            report.total_conversions = int(s.get("conversionsBigint", 0) or 0)
            report.total_spend = float(s.get("cost", 0) or 0)
            report.overall_ctr = float(s.get("ctr", 0) or 0)
            report.overall_cpa = float(s.get("ecpa", 0) or 0)

        # 2. Get per-campaign stats
        camp_data = self._query("""
            { campaigns(first: 50) {
                nodes {
                    id name channelType
                    campaignGroup { name }
                    campaignStatus { status }
                    ads(first: 5) { nodes { id name } totalCount }
                }
            }}
        """)

        for camp in camp_data.get("data", {}).get("campaigns", {}).get("nodes", []):
            cs = CampaignStats(
                campaign_id=camp["id"],
                name=camp["name"],
                channel_type=camp["channelType"],
                group_name=camp.get("campaignGroup", {}).get("name", ""),
                status=camp.get("campaignStatus", {}).get("status", ""),
            )
            report.campaigns.append(cs)

            # Track by group
            group = cs.group_name
            if group not in report.group_stats:
                report.group_stats[group] = {
                    "campaigns": 0, "active": 0,
                    "channels": set(),
                    "ad_count": 0,
                }
            report.group_stats[group]["campaigns"] += 1
            if cs.status == "ACTIVE":
                report.group_stats[group]["active"] += 1
            report.group_stats[group]["channels"].add(cs.channel_type)
            report.group_stats[group]["ad_count"] += (
                camp.get("ads", {}).get("totalCount", 0)
            )

        # 3. Analyze and identify opportunities
        report.opportunities = self._analyze_opportunities(report)

        # 4. Feed into INFORMATIV learning
        report.learning_fed = self._feed_learning_systems(report)

        return report

    def _analyze_opportunities(self, report: MonitorReport) -> List[Dict[str, str]]:
        """Identify optimization opportunities from current performance."""
        opportunities = []

        # High CPA
        if report.overall_cpa > 500:
            opportunities.append({
                "type": "HIGH_CPA",
                "severity": "critical",
                "finding": (
                    f"CPA is ${report.overall_cpa:,.0f} — INFORMATIV's bilateral "
                    f"evidence predicts $63-137 CPA with psychologically-optimized "
                    f"creative and domain targeting."
                ),
                "recommendation": (
                    "Deploy INFORMATIV creative variants per archetype with "
                    "mechanism-matched copy and domain-category targeting."
                ),
            })

        # Low CTR
        if report.overall_ctr < 0.001:
            opportunities.append({
                "type": "LOW_CTR",
                "severity": "high",
                "finding": (
                    f"CTR is {report.overall_ctr:.3%} — well below the 0.08-0.15% "
                    f"range for psychologically-targeted native/display."
                ),
                "recommendation": (
                    "Creative messaging may not match audience psychology. "
                    "INFORMATIV analysis shows authority mechanism should be "
                    "primary for Corporate Executives, social proof for "
                    "Leisure Travel."
                ),
            })

        # No revenue tracking
        if report.total_conversions > 0 and report.overall_cpa > 0:
            roas_check = self._query("""
                { advertisers(first: 1) {
                    nodes { stats { roas conversionRevenue } }
                }}
            """)
            adv = roas_check.get("data", {}).get("advertisers", {}).get("nodes", [{}])[0]
            rev = float((adv.get("stats", {}) or {}).get("conversionRevenue", 0) or 0)
            if rev == 0:
                opportunities.append({
                    "type": "NO_REVENUE_TRACKING",
                    "severity": "high",
                    "finding": (
                        f"{report.total_conversions} conversions recorded but "
                        f"$0 revenue attributed. Conversion pixel may not be "
                        f"passing revenue values."
                    ),
                    "recommendation": (
                        "Configure the conversion pixel to include revenue: "
                        "saq('conv', 'event_name', {'revenue': ORDER_TOTAL})"
                    ),
                })

        # Missing INFORMATIV integration
        informativ_campaigns = [
            c for c in report.campaigns
            if "informativ" in c.name.lower()
        ]
        if not any(c.status == "ACTIVE" for c in informativ_campaigns):
            opportunities.append({
                "type": "INFORMATIV_NOT_ACTIVE",
                "severity": "medium",
                "finding": (
                    "INFORMATIV-optimized campaign exists in draft but is not "
                    "active. Current campaigns use standard targeting without "
                    "psychological intelligence."
                ),
                "recommendation": (
                    "Activate the INFORMATIV campaign with psychologically-"
                    "optimized creative variants and domain targeting."
                ),
            })

        return opportunities

    def _feed_learning_systems(self, report: MonitorReport) -> bool:
        """Feed StackAdapt performance data into INFORMATIV learning."""
        try:
            import sys
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

            # Feed into inferential learning agent
            from adam.intelligence.inferential_learning_agent import get_inferential_agent
            agent = get_inferential_agent()

            # Map campaign groups to archetypes
            group_archetype_map = {
                "Corporate Executives": "corporate_executive",
                "Professionals": "careful_truster",
                "Leisure Travel": "special_occasion",
                "General Website RT": "repeat_loyal",
            }

            for group_name, stats in report.group_stats.items():
                archetype = group_archetype_map.get(group_name, "")
                if archetype:
                    agent.observe({
                        "archetype": archetype,
                        "mechanism": "unknown",
                        "domain_category": "mixed",
                        "outcome_value": 1.0 if report.total_conversions > 0 else 0.0,
                        "source": "stackadapt_monitor",
                    })

            return True
        except Exception as e:
            logger.debug("Learning feed failed: %s", e)
            return False

    def format_report(self, report: MonitorReport) -> str:
        """Format monitoring report for human consumption."""
        lines = []
        lines.append("=" * 65)
        lines.append("INFORMATIV × STACKADAPT CAMPAIGN MONITOR")
        lines.append("=" * 65)
        lines.append(f"Advertiser: {report.advertiser_name}")
        lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M')}")

        lines.append(f"\n── AGGREGATE PERFORMANCE ──")
        lines.append(f"  Impressions: {report.total_impressions:,}")
        lines.append(f"  Clicks: {report.total_clicks:,}")
        lines.append(f"  Conversions: {report.total_conversions}")
        lines.append(f"  Spend: ${report.total_spend:,.2f}")
        lines.append(f"  CTR: {report.overall_ctr:.3%}")
        lines.append(f"  CPA: ${report.overall_cpa:,.0f}")

        lines.append(f"\n── CAMPAIGNS ({len(report.campaigns)}) ──")
        for camp in report.campaigns:
            status_icon = "🟢" if camp.status == "ACTIVE" else "⚪"
            lines.append(f"  {status_icon} [{camp.channel_type}] {camp.name}")

        lines.append(f"\n── CAMPAIGN GROUPS ──")
        for group, stats in report.group_stats.items():
            channels = ", ".join(stats.get("channels", set()))
            lines.append(
                f"  {group}: {stats['active']}/{stats['campaigns']} active "
                f"({channels}), {stats['ad_count']} ads"
            )

        if report.opportunities:
            lines.append(f"\n── OPPORTUNITIES ({len(report.opportunities)}) ──")
            for opp in report.opportunities:
                icon = "🔴" if opp["severity"] == "critical" else "🟡" if opp["severity"] == "high" else "🔵"
                lines.append(f"\n  {icon} [{opp['type']}]")
                lines.append(f"  Finding: {opp['finding']}")
                lines.append(f"  → {opp['recommendation']}")

        lines.append(f"\n  Learning systems fed: {'Yes' if report.learning_fed else 'No'}")
        lines.append("")
        return "\n".join(lines)


def get_monitor() -> StackAdaptMonitor:
    return StackAdaptMonitor()
