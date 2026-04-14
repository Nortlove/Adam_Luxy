# =============================================================================
# Every-Other-Day Intelligence Report Generator
# Location: adam/ops/intelligence_report.py
# =============================================================================
"""
Generates actionable StackAdapt optimization instructions every 48 hours.

This is NOT a summary report. Every item is a specific action:
  "Change X in StackAdapt campaign Y because Z"

The report draws from:
  1. Telemetry signal profiles (section engagement, click patterns)
  2. Goal activation learning (which domains/goals produce outcomes)
  3. Archetype performance (conversion rates by archetype × domain)
  4. Mechanism effectiveness (which creative approaches are working)
  5. Suppression signals (users showing reactance/economist/skeptic patterns)
  6. Budget efficiency (spend vs outcome by campaign)

Output: JSON + human-readable markdown, designed to be handed directly
to the agency for execution in StackAdapt.
"""

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ReportAction:
    """A single actionable instruction for the agency."""
    priority: str          # "critical", "high", "medium", "low"
    category: str          # "budget", "domain", "creative", "frequency", "suppress", "new_test"
    campaign: str          # which StackAdapt campaign this affects (e.g., "TL-T1")
    action: str            # what to do, in plain language
    rationale: str         # why, with data
    expected_impact: str   # what we think will happen
    confidence: float      # 0-1, how sure we are
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IntelligenceReport:
    """Complete every-other-day intelligence report."""
    report_id: str
    generated_at: float
    period_start: float
    period_end: float
    period_label: str         # e.g., "Days 1-2", "Days 3-4"
    total_impressions: int = 0
    total_clicks: int = 0
    total_conversions: int = 0
    total_spend: float = 0.0
    actions: List[ReportAction] = field(default_factory=list)
    domain_performance: Dict[str, Dict] = field(default_factory=dict)
    archetype_performance: Dict[str, Dict] = field(default_factory=dict)
    suppression_candidates: List[Dict] = field(default_factory=list)
    learning_summary: Dict[str, Any] = field(default_factory=dict)


async def generate_intelligence_report(
    redis,
    period_hours: int = 48,
) -> IntelligenceReport:
    """Generate the every-other-day intelligence report.

    Pulls all available data from Redis, computes performance metrics,
    and generates specific StackAdapt actions.

    Args:
        redis: Redis connection
        period_hours: How many hours to look back (default 48)

    Returns:
        IntelligenceReport with prioritized actions
    """
    now = time.time()
    period_start = now - (period_hours * 3600)
    report_id = f"ir_{int(now)}"
    day_num = 1  # This should come from campaign start date tracking

    report = IntelligenceReport(
        report_id=report_id,
        generated_at=now,
        period_start=period_start,
        period_end=now,
        period_label=f"Period ending {time.strftime('%Y-%m-%d %H:%M', time.localtime(now))}",
    )

    # ── 1. Gather signal profiles ──
    try:
        profiles = await _gather_signal_profiles(redis, period_start)
        report.total_impressions = len(profiles)
    except Exception as e:
        logger.warning("Failed to gather signal profiles: %s", e)
        profiles = []

    # ── 2. Gather conversion data ──
    try:
        conversions = await _gather_conversions(redis, period_start)
        report.total_conversions = len(conversions)
    except Exception as e:
        logger.warning("Failed to gather conversions: %s", e)
        conversions = []

    # ── 3. Compute domain performance ──
    domain_perf = _compute_domain_performance(profiles, conversions)
    report.domain_performance = domain_perf

    # ── 4. Compute archetype performance ──
    archetype_perf = _compute_archetype_performance(profiles, conversions)
    report.archetype_performance = archetype_perf

    # ── 5. Identify suppression candidates ──
    suppress = _identify_suppression_candidates(profiles)
    report.suppression_candidates = suppress

    # ── 6. Get goal activation learning summary ──
    try:
        from adam.intelligence.goal_activation import get_goal_learner
        learner = get_goal_learner()
        report.learning_summary = learner.get_learning_summary()
    except Exception:
        report.learning_summary = {}

    # ── 7. Generate actions ──
    actions = []

    # Domain actions
    actions.extend(_generate_domain_actions(domain_perf, profiles))

    # Budget reallocation actions
    actions.extend(_generate_budget_actions(archetype_perf))

    # Creative actions
    actions.extend(_generate_creative_actions(archetype_perf, profiles))

    # Suppression actions
    actions.extend(_generate_suppression_actions(suppress))

    # Frequency actions
    actions.extend(_generate_frequency_actions(profiles))

    # New test recommendations
    actions.extend(_generate_test_actions(report.learning_summary, domain_perf))

    # Sort by priority
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    actions.sort(key=lambda a: priority_order.get(a.priority, 9))

    report.actions = actions
    return report


def _compute_domain_performance(profiles, conversions):
    """Compute per-domain metrics from signal profiles."""
    domain_data = defaultdict(lambda: {
        "impressions": 0, "clicks": 0, "conversions": 0,
        "total_dwell": 0, "booking_page_visits": 0,
        "archetypes": defaultdict(int),
        "goals_activated": defaultdict(float),
    })

    for p in profiles:
        domains = p.get("impression_domains", [])
        archetype = p.get("attributed_archetype", "")
        sections = p.get("section_dwell_totals", {})
        total_dwell = sum(sections.values())

        for domain in domains:
            d = domain_data[domain]
            d["impressions"] += 1
            if p.get("ad_attributed_sessions", 0) > 0:
                d["clicks"] += 1
            d["total_dwell"] += total_dwell
            if archetype:
                d["archetypes"][archetype] += 1
            if sections.get("section-booking", 0) > 0:
                d["booking_page_visits"] += 1

        # Goal activations
        for ga in p.get("impression_goal_activations", []):
            for domain in domains:
                for goal, score in ga.items():
                    domain_data[domain]["goals_activated"][goal] += score

    # Compute conversion rates per domain
    converted_users = {c.get("visitor_id") for c in conversions}
    for p in profiles:
        if p.get("user_id") in converted_users:
            for domain in p.get("impression_domains", []):
                domain_data[domain]["conversions"] += 1

    # Convert to regular dict
    result = {}
    for domain, data in domain_data.items():
        imps = data["impressions"]
        result[domain] = {
            "impressions": imps,
            "clicks": data["clicks"],
            "conversions": data["conversions"],
            "ctr": data["clicks"] / imps if imps > 0 else 0,
            "conversion_rate": data["conversions"] / imps if imps > 0 else 0,
            "avg_dwell": data["total_dwell"] / imps if imps > 0 else 0,
            "booking_page_rate": data["booking_page_visits"] / imps if imps > 0 else 0,
            "top_archetype": max(data["archetypes"], key=data["archetypes"].get) if data["archetypes"] else "",
            "top_goal": max(data["goals_activated"], key=data["goals_activated"].get) if data["goals_activated"] else "",
        }

    return result


def _compute_archetype_performance(profiles, conversions):
    """Compute per-archetype metrics."""
    arch_data = defaultdict(lambda: {"impressions": 0, "clicks": 0, "conversions": 0, "total_dwell": 0})

    converted_users = {c.get("visitor_id") for c in conversions}

    for p in profiles:
        archetype = p.get("attributed_archetype", "unclassified")
        sections = p.get("section_dwell_totals", {})
        total_dwell = sum(sections.values())

        arch_data[archetype]["impressions"] += 1
        if p.get("ad_attributed_sessions", 0) > 0:
            arch_data[archetype]["clicks"] += 1
        arch_data[archetype]["total_dwell"] += total_dwell
        if p.get("user_id") in converted_users:
            arch_data[archetype]["conversions"] += 1

    result = {}
    for arch, data in arch_data.items():
        imps = data["impressions"]
        result[arch] = {
            "impressions": imps,
            "clicks": data["clicks"],
            "conversions": data["conversions"],
            "ctr": data["clicks"] / imps if imps > 0 else 0,
            "conversion_rate": data["conversions"] / imps if imps > 0 else 0,
            "avg_dwell": data["total_dwell"] / imps if imps > 0 else 0,
        }

    return result


def _identify_suppression_candidates(profiles):
    """Identify users who should be suppressed (added to exclusion audience)."""
    candidates = []
    for p in profiles:
        reasons = []
        # Reactance detected
        if p.get("reactance_detected"):
            reasons.append(f"reactance detected at touch {p.get('reactance_onset_touch', '?')}")
        # High neuroticism + spending pain (anxious economist)
        # These would come from the puzzle solver's archetype classification
        # For now, check behavioral signals
        if p.get("total_sessions", 0) >= 4 and p.get("ad_attributed_sessions", 0) >= 3:
            sections = p.get("section_dwell_totals", {})
            if sum(sections.values()) < 5:
                reasons.append("4+ sessions with <5s total engagement — ad averse")

        if reasons:
            candidates.append({
                "user_id": p.get("user_id", ""),
                "reasons": reasons,
                "sessions": p.get("total_sessions", 0),
                "archetype": p.get("attributed_archetype", ""),
            })

    return candidates


def _generate_domain_actions(domain_perf, profiles):
    """Generate domain-level StackAdapt actions."""
    actions = []

    for domain, perf in domain_perf.items():
        # High-performing domain: recommend increasing bid
        if perf["conversion_rate"] > 0.05 and perf["impressions"] >= 10:
            actions.append(ReportAction(
                priority="high",
                category="domain",
                campaign=f"All {perf['top_archetype']} campaigns",
                action=f"Increase bid multiplier on {domain} by 20-30%",
                rationale=f"{domain} converting at {perf['conversion_rate']:.1%} "
                          f"({perf['conversions']} conversions from {perf['impressions']} impressions). "
                          f"Dominant goal: {perf['top_goal']}.",
                expected_impact=f"~{int(perf['conversions'] * 0.25)} additional conversions",
                confidence=min(0.8, perf["impressions"] / 50),
                data=perf,
            ))

        # Underperforming domain: recommend reducing or removing
        if perf["impressions"] >= 20 and perf["ctr"] < 0.001 and perf["avg_dwell"] < 3:
            actions.append(ReportAction(
                priority="medium",
                category="domain",
                campaign=f"All {perf['top_archetype']} campaigns",
                action=f"Remove {domain} from whitelist or reduce bid by 50%",
                rationale=f"{domain}: {perf['impressions']} impressions, "
                          f"{perf['ctr']:.3%} CTR, {perf['avg_dwell']:.1f}s avg dwell. "
                          f"Goal activation not translating to engagement.",
                expected_impact="Redirect spend to higher-performing domains",
                confidence=0.6,
                data=perf,
            ))

        # High engagement but no conversion: investigate
        if perf["avg_dwell"] > 30 and perf["booking_page_rate"] > 0.1 and perf["conversions"] == 0:
            actions.append(ReportAction(
                priority="high",
                category="creative",
                campaign=f"{perf['top_archetype']} campaigns",
                action=f"Investigate {domain} — high engagement ({perf['avg_dwell']:.0f}s dwell, "
                       f"{perf['booking_page_rate']:.0%} reached booking page) but zero conversions",
                rationale="Users from this domain are engaged and reaching booking but not converting. "
                          "This suggests a landing page issue or price friction, not a targeting problem.",
                expected_impact="Could unlock a high-value domain if booking friction is resolved",
                confidence=0.5,
                data=perf,
            ))

    return actions


def _generate_budget_actions(archetype_perf):
    """Generate budget reallocation recommendations."""
    actions = []

    if not archetype_perf:
        return actions

    # Find best and worst performing archetypes
    with_data = {k: v for k, v in archetype_perf.items()
                 if v["impressions"] >= 10 and k != "unclassified"}
    if len(with_data) < 2:
        return actions

    best = max(with_data, key=lambda k: with_data[k]["conversion_rate"])
    worst = min(with_data, key=lambda k: with_data[k]["conversion_rate"])

    best_rate = with_data[best]["conversion_rate"]
    worst_rate = with_data[worst]["conversion_rate"]

    if best_rate > worst_rate * 2 and worst_rate < 0.02:
        # Best is 2x+ better than worst
        from adam.constants import CAMPAIGN_ARCHETYPE_MAP
        inv_map = {v: k for k, v in CAMPAIGN_ARCHETYPE_MAP.items()}
        best_prefix = inv_map.get(best, best[:2].upper())
        worst_prefix = inv_map.get(worst, worst[:2].upper())

        actions.append(ReportAction(
            priority="high",
            category="budget",
            campaign=f"{worst_prefix}-* → {best_prefix}-*",
            action=f"Shift 15-20% of {worst} daily budget to {best}",
            rationale=f"{best} converting at {best_rate:.1%} vs {worst} at {worst_rate:.1%} "
                      f"({best_rate/max(0.001, worst_rate):.1f}x difference). "
                      f"Based on {with_data[best]['impressions']} and {with_data[worst]['impressions']} impressions.",
            expected_impact=f"Estimated {int(with_data[best]['conversions'] * 0.2)} additional conversions "
                          f"from redirected spend",
            confidence=min(0.7, min(with_data[best]["impressions"], with_data[worst]["impressions"]) / 50),
        ))

    return actions


def _generate_creative_actions(archetype_perf, profiles):
    """Generate creative change recommendations."""
    actions = []

    # Check if any archetype has high impressions but very low CTR
    for arch, perf in archetype_perf.items():
        if arch == "unclassified":
            continue
        if perf["impressions"] >= 30 and perf["ctr"] < 0.002:
            actions.append(ReportAction(
                priority="medium",
                category="creative",
                campaign=f"All {arch} campaigns",
                action=f"Consider refreshing creative for {arch} — CTR is {perf['ctr']:.3%} "
                       f"across {perf['impressions']} impressions",
                rationale="Low CTR suggests the ad creative is not resonating with the audience "
                         "on these domains. The targeting may be correct but the message isn't landing.",
                expected_impact="Creative refresh typically produces 20-40% CTR improvement",
                confidence=0.5,
            ))

    return actions


def _generate_suppression_actions(suppress_candidates):
    """Generate user suppression actions."""
    actions = []

    if len(suppress_candidates) >= 3:
        actions.append(ReportAction(
            priority="medium",
            category="suppress",
            campaign="All campaigns",
            action=f"Add {len(suppress_candidates)} users to exclusion audience "
                   f"(reactance/ad-averse detected)",
            rationale=f"These users show behavioral patterns indicating continued ad exposure "
                     f"will produce negative ROI: {', '.join(c['reasons'][0] for c in suppress_candidates[:3])}...",
            expected_impact=f"Save ~${len(suppress_candidates) * 0.5:.0f}/day in wasted impressions",
            confidence=0.7,
            data={"user_ids": [c["user_id"] for c in suppress_candidates]},
        ))

    return actions


def _generate_frequency_actions(profiles):
    """Generate frequency cap adjustment recommendations."""
    actions = []

    # Check for users hitting frequency caps with declining engagement
    declining_users = 0
    for p in profiles:
        outcomes = p.get("touch_outcomes", [])
        if len(outcomes) >= 4:
            early = sum(outcomes[:2]) / 2 if outcomes[:2] else 0
            recent = sum(outcomes[-2:]) / 2 if outcomes[-2:] else 0
            if early > 0.5 and recent < 0.2:
                declining_users += 1

    if declining_users >= 5:
        actions.append(ReportAction(
            priority="medium",
            category="frequency",
            campaign="All campaigns",
            action=f"Reduce frequency caps by 1/day — {declining_users} users showing "
                   f"engagement decline after touch 3+",
            rationale="Users who engaged early are now declining. This is frequency decay, "
                     "not targeting failure. Reducing frequency preserves the relationship.",
            expected_impact="Slower but more sustainable conversion path for these users",
            confidence=0.6,
        ))

    return actions


def _generate_test_actions(learning_summary, domain_perf):
    """Generate new test recommendations based on epistemic value."""
    actions = []

    # If we have high-uncertainty domain-goal pairs, recommend testing
    if learning_summary and learning_summary.get("goal_page_pairs_tracked", 0) > 0:
        top_errors = learning_summary.get("top_calibration_errors", [])
        for key, error, obs in top_errors[:2]:
            actions.append(ReportAction(
                priority="low",
                category="new_test",
                campaign="Test budget",
                action=f"Allocate small test budget to {key} — "
                       f"model predictions are {error:.0%} off from observed outcomes",
                rationale=f"After {obs} observations, the goal activation model's predictions "
                         f"for this domain-goal pair are miscalibrated. More data will improve "
                         f"targeting accuracy for future periods.",
                expected_impact="Better model accuracy → better domain targeting in weeks 3+",
                confidence=0.4,
            ))

    return actions


async def _gather_signal_profiles(redis, since_ts):
    """Gather all signal profiles updated since timestamp."""
    profiles = []
    try:
        keys = await redis.keys("adam:NONCONSCIOUS:profile:*")
        for key in keys[:500]:  # Cap at 500 for performance
            raw = await redis.get(key)
            if raw:
                profile = json.loads(raw)
                if profile.get("last_updated", 0) >= since_ts:
                    profiles.append(profile)
    except Exception as e:
        logger.warning("Signal profile scan failed: %s", e)
    return profiles


async def _gather_conversions(redis, since_ts):
    """Gather conversion events since timestamp."""
    conversions = []
    try:
        raw_list = await redis.lrange("adam:conversions", 0, 500)
        for raw in raw_list:
            conv = json.loads(raw)
            if conv.get("timestamp", 0) >= since_ts:
                conversions.append(conv)
    except Exception as e:
        logger.warning("Conversion scan failed: %s", e)
    return conversions


def format_report_markdown(report: IntelligenceReport) -> str:
    """Format the report as human-readable markdown for the agency."""
    lines = []
    lines.append(f"# INFORMATIV Intelligence Report")
    lines.append(f"**{report.period_label}**")
    lines.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M', time.localtime(report.generated_at))}")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append(f"- Impressions: {report.total_impressions}")
    lines.append(f"- Clicks: {report.total_clicks}")
    lines.append(f"- Conversions: {report.total_conversions}")
    lines.append(f"- Actions recommended: {len(report.actions)}")
    lines.append("")

    # Actions by priority
    for priority in ["critical", "high", "medium", "low"]:
        priority_actions = [a for a in report.actions if a.priority == priority]
        if not priority_actions:
            continue

        lines.append(f"## {priority.upper()} Priority Actions")
        lines.append("")
        for i, action in enumerate(priority_actions, 1):
            lines.append(f"### {i}. {action.action}")
            lines.append(f"**Campaign:** {action.campaign}")
            lines.append(f"**Category:** {action.category}")
            lines.append(f"**Why:** {action.rationale}")
            lines.append(f"**Expected impact:** {action.expected_impact}")
            lines.append(f"**Confidence:** {action.confidence:.0%}")
            lines.append("")

    # Domain performance table
    if report.domain_performance:
        lines.append("## Domain Performance")
        lines.append("")
        lines.append("| Domain | Impressions | CTR | Conv Rate | Avg Dwell | Top Goal |")
        lines.append("|---|---|---|---|---|---|")
        for domain in sorted(report.domain_performance,
                           key=lambda d: -report.domain_performance[d]["conversion_rate"]):
            p = report.domain_performance[domain]
            lines.append(
                f"| {domain} | {p['impressions']} | {p['ctr']:.2%} | "
                f"{p['conversion_rate']:.2%} | {p['avg_dwell']:.1f}s | {p['top_goal']} |"
            )
        lines.append("")

    # Suppression
    if report.suppression_candidates:
        lines.append(f"## Suppression Candidates ({len(report.suppression_candidates)} users)")
        lines.append("These users should be added to the exclusion audience:")
        for c in report.suppression_candidates[:10]:
            lines.append(f"- `{c['user_id']}`: {', '.join(c['reasons'])}")
        lines.append("")

    return "\n".join(lines)
