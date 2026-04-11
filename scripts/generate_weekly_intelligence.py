#!/usr/bin/env python3
# =============================================================================
# Weekly Intelligence Report Generator — LUXY Ride Pilot
# =============================================================================
#
# Produces the weekly intelligence report for the agency.
# Combines:
#   1. StackAdapt campaign reporting (from GraphQL API or CSV import)
#   2. INFORMATIV behavioral signal data (from Redis)
#   3. Bilateral learning analysis
#
# Outputs a formatted markdown report with actionable recommendations.
#
# Usage:
#   PYTHONPATH=. python scripts/generate_weekly_intelligence.py \
#     --stackadapt-csv reports/weekly_stackadapt_export.csv \
#     --output reports/weekly_intelligence_report.md
#
#   OR with GraphQL API:
#   PYTHONPATH=. python scripts/generate_weekly_intelligence.py \
#     --stackadapt-api-key YOUR_KEY \
#     --output reports/weekly_intelligence_report.md
#
# =============================================================================

import argparse
import csv
import json
import logging
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def load_stackadapt_csv(csv_path: str) -> List[Dict]:
    """Load campaign data from StackAdapt CSV export."""
    rows = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    logger.info("Loaded %d rows from StackAdapt CSV", len(rows))
    return rows


def load_signal_profiles(redis_url: str = "redis://localhost:6379") -> Dict:
    """Load behavioral signal profiles from Redis."""
    profiles = {}
    try:
        import redis
        r = redis.from_url(redis_url, decode_responses=True)
        # Scan for all nonconscious profiles
        cursor = 0
        while True:
            cursor, keys = r.scan(cursor, match="adam:*nonconscious*profile*", count=100)
            for key in keys:
                data = r.get(key)
                if data:
                    try:
                        profile = json.loads(data)
                        profiles[profile.get("user_id", key)] = profile
                    except json.JSONDecodeError:
                        pass
            if cursor == 0:
                break
        logger.info("Loaded %d signal profiles from Redis", len(profiles))
    except Exception as e:
        logger.warning("Could not load Redis profiles: %s", e)
    return profiles


def load_conversions(redis_url: str = "redis://localhost:6379") -> List[Dict]:
    """Load conversion events from Redis."""
    conversions = []
    try:
        import redis
        r = redis.from_url(redis_url, decode_responses=True)
        cursor = 0
        while True:
            cursor, keys = r.scan(cursor, match="adam:conversion:*", count=100)
            for key in keys:
                data = r.get(key)
                if data:
                    try:
                        conversions.append(json.loads(data))
                    except json.JSONDecodeError:
                        pass
            if cursor == 0:
                break
        logger.info("Loaded %d conversions from Redis", len(conversions))
    except Exception as e:
        logger.warning("Could not load conversions: %s", e)
    return conversions


def analyze_behavioral_conversion_patterns(
    profiles: Dict,
    conversions: List[Dict],
) -> Dict:
    """Join behavioral profiles with conversion outcomes.

    This is the core attribution intelligence — connecting what users
    DID on the site (behavioral signals) with what they BOUGHT (conversions).
    """
    if not profiles or not conversions:
        return {"status": "insufficient_data"}

    # Index conversions by visitor_id
    conv_by_visitor = {}
    for c in conversions:
        vid = c.get("visitor_id", "")
        if vid:
            conv_by_visitor[vid] = c

    converters = []
    non_converters = []

    for vid, profile in profiles.items():
        if vid in conv_by_visitor:
            converters.append(profile)
        elif profile.get("total_sessions", 0) >= 2:
            non_converters.append(profile)

    if not converters:
        return {"status": "no_conversions_yet", "profiles_tracked": len(profiles)}

    # Analyze what's different about converters vs non-converters
    insights = {
        "total_profiles": len(profiles),
        "converters": len(converters),
        "non_converters": len(non_converters),
        "conversion_rate": len(converters) / max(1, len(converters) + len(non_converters)),
    }

    # Section engagement comparison
    def avg_section(users, section):
        vals = [u.get("section_dwell_totals", {}).get(section, 0) for u in users]
        return sum(vals) / max(1, len(vals))

    sections = ["section-pricing", "section-safety", "section-reviews",
                "section-testimonials", "section-fleet", "section-booking", "section-faq"]

    section_comparison = {}
    for sec in sections:
        conv_avg = avg_section(converters, sec)
        non_avg = avg_section(non_converters, sec)
        if conv_avg > 0 or non_avg > 0:
            ratio = conv_avg / max(0.1, non_avg)
            section_comparison[sec] = {
                "converter_avg_dwell": round(conv_avg, 1),
                "non_converter_avg_dwell": round(non_avg, 1),
                "ratio": round(ratio, 2),
                "insight": f"Converters spend {ratio:.1f}x on {sec}" if ratio > 1.5 else "",
            }
    insights["section_comparison"] = section_comparison

    # Archetype distribution
    def archetype_dist(users):
        dist = defaultdict(int)
        for u in users:
            arch = u.get("attributed_archetype", "unclassified")
            dist[arch] += 1
        return dict(dist)

    insights["converter_archetypes"] = archetype_dist(converters)
    insights["non_converter_archetypes"] = archetype_dist(non_converters)

    # Organic return rate comparison
    def avg_organic_ratio(users):
        ratios = []
        for u in users:
            total = u.get("ad_attributed_sessions", 0) + u.get("organic_sessions", 0)
            if total > 0:
                ratios.append(u.get("organic_sessions", 0) / total)
        return sum(ratios) / max(1, len(ratios))

    insights["converter_organic_ratio"] = round(avg_organic_ratio(converters), 3)
    insights["non_converter_organic_ratio"] = round(avg_organic_ratio(non_converters), 3)

    # Average sessions to conversion
    conv_sessions = [c.get("total_sessions_at_conversion", 0) for c in conversions if c.get("total_sessions_at_conversion")]
    if conv_sessions:
        insights["avg_sessions_to_convert"] = round(sum(conv_sessions) / len(conv_sessions), 1)

    # Top barrier at conversion
    barriers = defaultdict(int)
    for c in conversions:
        b = c.get("self_reported_barrier", "")
        if b:
            barriers[b] += 1
    insights["barriers_at_conversion"] = dict(sorted(barriers.items(), key=lambda x: -x[1]))

    return insights


def analyze_archetype_performance(campaign_data: List[Dict]) -> Dict:
    """Analyze per-archetype campaign performance."""
    archetypes = defaultdict(lambda: {
        "impressions": 0, "clicks": 0, "conversions": 0,
        "spend": 0.0, "campaigns": [],
    })

    for row in campaign_data:
        name = row.get("Campaign Name", row.get("campaign_name", ""))

        # Detect archetype from campaign name
        archetype = "unknown"
        if "CT-" in name or "Careful Truster" in name or "careful_truster" in name:
            archetype = "careful_truster"
        elif "SS-" in name or "Status Seeker" in name or "status_seeker" in name:
            archetype = "status_seeker"
        elif "ED-" in name or "Easy Decider" in name or "easy_decider" in name:
            archetype = "easy_decider"

        a = archetypes[archetype]
        a["impressions"] += int(row.get("Impressions", row.get("impressions", 0)))
        a["clicks"] += int(row.get("Clicks", row.get("clicks", 0)))
        a["conversions"] += int(row.get("Conversions", row.get("conversions", 0)))
        a["spend"] += float(row.get("Spend", row.get("spend", 0)))
        a["campaigns"].append(name)

    # Compute derived metrics
    for arch, data in archetypes.items():
        data["ctr"] = data["clicks"] / max(1, data["impressions"])
        data["cvr"] = data["conversions"] / max(1, data["clicks"])
        data["cpb"] = data["spend"] / max(1, data["conversions"])

    return dict(archetypes)


def analyze_touch_progression(campaign_data: List[Dict]) -> Dict:
    """Analyze per-touch conversion funnel."""
    touches = defaultdict(lambda: {
        "impressions": 0, "clicks": 0, "conversions": 0, "spend": 0.0,
    })

    for row in campaign_data:
        name = row.get("Campaign Name", row.get("campaign_name", ""))

        # Detect touch position
        for t in range(1, 6):
            if f"T{t}" in name or f"Touch {t}" in name:
                touches[t]["impressions"] += int(row.get("Impressions", row.get("impressions", 0)))
                touches[t]["clicks"] += int(row.get("Clicks", row.get("clicks", 0)))
                touches[t]["conversions"] += int(row.get("Conversions", row.get("conversions", 0)))
                touches[t]["spend"] += float(row.get("Spend", row.get("spend", 0)))
                break

    for t, data in touches.items():
        data["ctr"] = data["clicks"] / max(1, data["impressions"])
        data["cvr"] = data["conversions"] / max(1, data["clicks"])

    return dict(touches)


def analyze_behavioral_signals(profiles: Dict) -> Dict:
    """Aggregate behavioral signal insights across all profiles."""
    if not profiles:
        return {"status": "no_data", "note": "No behavioral profiles available yet"}

    total = len(profiles)
    organic_count = sum(1 for p in profiles.values() if p.get("organic_sessions", 0) > 0)
    reactance_count = sum(1 for p in profiles.values() if p.get("reactance_detected", False))
    barrier_overrides = sum(1 for p in profiles.values()
                          if p.get("barrier_self_report_confidence", 0) > 0.5)

    # Top barriers from self-report
    barriers = defaultdict(int)
    for p in profiles.values():
        b = p.get("self_reported_barrier", "")
        if b:
            barriers[b] += 1

    # Section engagement
    sections = defaultdict(float)
    for p in profiles.values():
        for sec, dwell in p.get("section_dwell_totals", {}).items():
            sections[sec] += dwell

    return {
        "total_profiles": total,
        "organic_return_rate": organic_count / max(1, total),
        "reactance_detected_rate": reactance_count / max(1, total),
        "barrier_override_rate": barrier_overrides / max(1, total),
        "top_barriers": dict(sorted(barriers.items(), key=lambda x: -x[1])[:5]),
        "section_engagement": dict(sorted(sections.items(), key=lambda x: -x[1])[:8]),
    }


def generate_recommendations(
    archetype_perf: Dict,
    touch_perf: Dict,
    behavioral: Dict,
) -> List[str]:
    """Generate actionable recommendations."""
    recs = []

    # Touch progression check
    if touch_perf:
        sorted_touches = sorted(touch_perf.items())
        for i in range(1, len(sorted_touches)):
            prev_t, prev_data = sorted_touches[i-1]
            curr_t, curr_data = sorted_touches[i]
            if curr_data["cvr"] < prev_data["cvr"] and prev_data["cvr"] > 0:
                recs.append(
                    f"**Touch {curr_t} converts LOWER than Touch {prev_t}** "
                    f"({curr_data['cvr']:.1%} vs {prev_data['cvr']:.1%}). "
                    f"The mechanism at Touch {curr_t} may need changing. "
                    f"Consider testing an alternative creative."
                )

    # Archetype performance
    for arch, data in archetype_perf.items():
        if arch == "unknown":
            continue
        if data["ctr"] < 0.003:
            recs.append(
                f"**{arch}** CTR is below 0.3% ({data['ctr']:.2%}). "
                f"Consider refreshing Touch 1 creative or adjusting domain targeting."
            )
        if data["cpb"] > 100 and data["conversions"] > 0:
            recs.append(
                f"**{arch}** cost per booking is ${data['cpb']:.2f}. "
                f"Consider reducing budget or tightening targeting."
            )

    # Behavioral insights
    if isinstance(behavioral, dict) and behavioral.get("total_profiles", 0) > 0:
        if behavioral.get("reactance_detected_rate", 0) > 0.15:
            recs.append(
                f"**Reactance alert**: {behavioral['reactance_detected_rate']:.0%} of tracked users "
                f"show engagement decline. Consider reducing frequency caps across all archetypes."
            )
        if behavioral.get("barrier_override_rate", 0) > 0.3:
            recs.append(
                f"**Barrier mismatch**: {behavioral['barrier_override_rate']:.0%} of users show "
                f"behavioral barriers that differ from our predicted barriers. "
                f"Review creative-to-audience matching."
            )
        top_section = next(iter(behavioral.get("section_engagement", {})), None)
        if top_section:
            recs.append(
                f"**Most engaged section**: '{top_section}' — consider creating a creative "
                f"variant that directly addresses the concerns raised by this section."
            )

    if not recs:
        recs.append("No specific adjustments recommended this week. Continue current strategy.")

    return recs


def generate_report(
    archetype_perf: Dict,
    touch_perf: Dict,
    behavioral: Dict,
    recommendations: List[str],
    report_date: str,
) -> str:
    """Generate the formatted markdown report."""
    lines = [
        f"# INFORMATIV Weekly Intelligence Report",
        f"## LUXY Ride Pilot Campaign",
        f"## Week of {report_date}",
        "",
        "---",
        "",
        "## Archetype Performance",
        "",
        "| Archetype | Impressions | Clicks | CTR | Conversions | CVR | Spend | CPB |",
        "|-----------|------------|--------|-----|------------|-----|-------|-----|",
    ]

    for arch in ["careful_truster", "status_seeker", "easy_decider"]:
        d = archetype_perf.get(arch, {})
        if d:
            lines.append(
                f"| {arch} | {d.get('impressions',0):,} | {d.get('clicks',0):,} | "
                f"{d.get('ctr',0):.2%} | {d.get('conversions',0)} | "
                f"{d.get('cvr',0):.2%} | ${d.get('spend',0):,.2f} | "
                f"${d.get('cpb',0):,.2f} |"
            )

    lines.extend(["", "## Touch Progression (Should Increase T1→T5)", ""])
    lines.append("| Touch | Impressions | Clicks | CTR | Conversions | CVR |")
    lines.append("|-------|------------|--------|-----|------------|-----|")
    for t in sorted(touch_perf.keys()):
        d = touch_perf[t]
        lines.append(
            f"| T{t} | {d['impressions']:,} | {d['clicks']:,} | "
            f"{d['ctr']:.2%} | {d['conversions']} | {d['cvr']:.2%} |"
        )

    lines.extend(["", "## Behavioral Intelligence (From INFORMATIV Telemetry)", ""])
    if isinstance(behavioral, dict) and behavioral.get("total_profiles", 0) > 0:
        lines.append(f"- **Profiles tracked**: {behavioral['total_profiles']}")
        lines.append(f"- **Organic return rate**: {behavioral.get('organic_return_rate', 0):.1%}")
        lines.append(f"- **Reactance detection rate**: {behavioral.get('reactance_detected_rate', 0):.1%}")
        lines.append(f"- **Barrier override rate**: {behavioral.get('barrier_override_rate', 0):.1%}")
        if behavioral.get("top_barriers"):
            lines.append(f"- **Top self-reported barriers**: {', '.join(behavioral['top_barriers'].keys())}")
        if behavioral.get("section_engagement"):
            top_sections = list(behavioral["section_engagement"].items())[:3]
            sec_str = ", ".join(f"{s} ({d:.0f}s)" for s, d in top_sections)
            lines.append(f"- **Most-engaged sections**: {sec_str}")
    else:
        lines.append("*Behavioral data not yet available — telemetry will begin collecting after GTM tags are live.*")

    lines.extend(["", "## Recommendations", ""])
    for i, rec in enumerate(recommendations, 1):
        lines.append(f"{i}. {rec}")

    lines.extend([
        "",
        "---",
        "",
        "*Generated by INFORMATIV bilateral psycholinguistic intelligence system.*",
        f"*Report date: {report_date}*",
    ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Weekly Intelligence Report")
    parser.add_argument("--stackadapt-csv", help="Path to StackAdapt CSV export")
    parser.add_argument("--redis-url", default="redis://localhost:6379")
    parser.add_argument("--output", default="reports/weekly_intelligence_report.md")
    args = parser.parse_args()

    report_date = datetime.now().strftime("%B %d, %Y")

    # Load StackAdapt data
    if args.stackadapt_csv and Path(args.stackadapt_csv).exists():
        campaign_data = load_stackadapt_csv(args.stackadapt_csv)
    else:
        logger.info("No StackAdapt CSV provided — using empty data (report will show structure only)")
        campaign_data = []

    # Load behavioral signals
    profiles = load_signal_profiles(args.redis_url)

    # Load conversions for attribution analysis
    conversions = load_conversions(args.redis_url)

    # Analyze
    archetype_perf = analyze_archetype_performance(campaign_data)
    touch_perf = analyze_touch_progression(campaign_data)
    behavioral = analyze_behavioral_signals(profiles)
    attribution = analyze_behavioral_conversion_patterns(profiles, conversions)
    recommendations = generate_recommendations(archetype_perf, touch_perf, behavioral)

    # Add attribution-based recommendations
    if isinstance(attribution, dict) and attribution.get("converters", 0) > 0:
        sc = attribution.get("section_comparison", {})
        for sec, data in sc.items():
            if data.get("ratio", 1.0) > 2.0:
                recommendations.append(
                    f"**{sec}**: Converters spend {data['ratio']:.1f}x more time here "
                    f"({data['converter_avg_dwell']}s vs {data['non_converter_avg_dwell']}s). "
                    f"Consider creating ad creative that directly references this content."
                )
        if attribution.get("converter_organic_ratio", 0) > attribution.get("non_converter_organic_ratio", 0) * 1.5:
            recommendations.append(
                f"**Organic returns predict conversion**: Converters have "
                f"{attribution['converter_organic_ratio']:.0%} organic ratio vs "
                f"{attribution['non_converter_organic_ratio']:.0%} for non-converters. "
                f"Users returning organically should get priority retargeting."
            )

    # Generate report
    report = generate_report(archetype_perf, touch_perf, behavioral, recommendations, report_date)

    # Write
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report)
    logger.info("Report written to %s", output_path)
    print()
    print(report)


if __name__ == "__main__":
    main()
