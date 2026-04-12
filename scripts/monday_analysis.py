#!/usr/bin/env python3
# =============================================================================
# Monday Analysis Framework
# Run when Becca shares her StackAdapt campaign data
# =============================================================================

"""
Takes Becca's StackAdapt export and cross-references with:
1. Our LUXY Ride bilateral edge archetypes
2. Airline review archetypes (cross-category validation)
3. Our psychological domain profiles
4. Our dayparting predictions

Usage:
    PYTHONPATH=. python scripts/monday_analysis.py \
        --stackadapt-csv data/becca_export.csv \
        --output reports/monday_analysis.md
"""

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path


def load_becca_data(csv_path: str):
    """Load Becca's StackAdapt export."""
    rows = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def analyze_domains(rows, domain_profiles_path="campaigns/ridelux_v6/luxy_ride_site_profiles.json"):
    """Cross-reference converting domains with our psychological profiles."""
    # Load our domain profiles
    try:
        with open(domain_profiles_path) as f:
            profiles = json.load(f)
    except:
        profiles = {}

    domain_perf = defaultdict(lambda: {"impressions": 0, "clicks": 0, "conversions": 0, "spend": 0.0})

    for row in rows:
        domain = row.get("Domain", row.get("domain", row.get("Site", "")))
        if not domain:
            continue
        d = domain_perf[domain]
        d["impressions"] += int(row.get("Impressions", row.get("impressions", 0)) or 0)
        d["clicks"] += int(row.get("Clicks", row.get("clicks", 0)) or 0)
        d["conversions"] += int(row.get("Conversions", row.get("conversions", 0)) or 0)
        d["spend"] += float(row.get("Spend", row.get("spend", 0)) or 0)

    # Sort by conversions
    sorted_domains = sorted(domain_perf.items(), key=lambda x: -x[1]["conversions"])

    results = []
    for domain, perf in sorted_domains[:30]:
        profile = profiles.get(domain, {})
        results.append({
            "domain": domain,
            **perf,
            "ctr": perf["clicks"] / max(1, perf["impressions"]),
            "cvr": perf["conversions"] / max(1, perf["clicks"]),
            "psychological_profile": profile.get("archetype_alignment", {}),
            "in_our_whitelist": domain in [p for p in profiles],
        })

    return results


def analyze_time_of_day(rows):
    """Compare Becca's time-of-day performance to our predictions."""
    hour_perf = defaultdict(lambda: {"impressions": 0, "clicks": 0, "conversions": 0})

    for row in rows:
        hour = row.get("Hour", row.get("hour", ""))
        if not hour:
            continue
        try:
            h = int(hour)
        except:
            continue
        hour_perf[h]["impressions"] += int(row.get("Impressions", 0) or 0)
        hour_perf[h]["clicks"] += int(row.get("Clicks", 0) or 0)
        hour_perf[h]["conversions"] += int(row.get("Conversions", 0) or 0)

    return dict(sorted(hour_perf.items()))


def analyze_devices(rows):
    """Compare device performance to our ELM predictions."""
    device_perf = defaultdict(lambda: {"impressions": 0, "clicks": 0, "conversions": 0})

    for row in rows:
        device = row.get("Device", row.get("device", row.get("Device Type", "")))
        if not device:
            continue
        device_perf[device.lower()]["impressions"] += int(row.get("Impressions", 0) or 0)
        device_perf[device.lower()]["clicks"] += int(row.get("Clicks", 0) or 0)
        device_perf[device.lower()]["conversions"] += int(row.get("Conversions", 0) or 0)

    return dict(device_perf)


def generate_report(domains, hours, devices, output_path):
    """Generate the Monday analysis report."""
    lines = [
        "# Monday Analysis — Becca's Data × INFORMATIV Intelligence",
        f"## Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "---",
        "",
        "## Domain Performance × Psychological Profiles",
        "",
        "| Domain | Impressions | Clicks | Conversions | CTR | CVR | In Whitelist |",
        "|--------|------------|--------|-------------|-----|-----|-------------|",
    ]

    for d in domains[:15]:
        lines.append(
            f"| {d['domain'][:30]} | {d['impressions']:,} | {d['clicks']:,} | "
            f"{d['conversions']} | {d['ctr']:.2%} | {d['cvr']:.2%} | "
            f"{'YES' if d['in_our_whitelist'] else 'NO'} |"
        )

    new_domains = [d for d in domains if not d["in_our_whitelist"] and d["conversions"] > 0]
    if new_domains:
        lines.extend([
            "",
            "### Domains Converting That We DIDN'T Have",
            "These should be added to the whitelist and psychologically profiled:",
            "",
        ])
        for d in new_domains[:10]:
            lines.append(f"- **{d['domain']}**: {d['conversions']} conversions, {d['cvr']:.2%} CVR")

    lines.extend([
        "",
        "## Time of Day Performance",
        "",
        "| Hour | Impressions | Clicks | Conversions |",
        "|------|------------|--------|-------------|",
    ])
    for hour in sorted(hours.keys()):
        h = hours[hour]
        lines.append(f"| {hour}:00 | {h['impressions']:,} | {h['clicks']:,} | {h['conversions']} |")

    lines.extend([
        "",
        "## Device Performance",
        "",
        "| Device | Impressions | Clicks | Conversions | CVR |",
        "|--------|------------|--------|-------------|-----|",
    ])
    for device, perf in devices.items():
        cvr = perf["conversions"] / max(1, perf["clicks"])
        lines.append(f"| {device} | {perf['impressions']:,} | {perf['clicks']:,} | {perf['conversions']} | {cvr:.2%} |")

    report = "\n".join(lines)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(report)
    print(report)
    print(f"\nReport saved to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Monday Analysis")
    parser.add_argument("--stackadapt-csv", required=True, help="Becca's export CSV")
    parser.add_argument("--output", default="reports/monday_analysis.md")
    args = parser.parse_args()

    print("Loading Becca's data...")
    rows = load_becca_data(args.stackadapt_csv)
    print(f"Loaded {len(rows)} rows")

    print("Analyzing domains...")
    domains = analyze_domains(rows)

    print("Analyzing time of day...")
    hours = analyze_time_of_day(rows)

    print("Analyzing devices...")
    devices = analyze_devices(rows)

    print("Generating report...")
    generate_report(domains, hours, devices, args.output)


if __name__ == "__main__":
    main()
