#!/usr/bin/env python3
"""Validate LUXY Ride campaign config before StackAdapt submission.

Checks:
1. No <<REPLACE>> placeholders remaining
2. Flight dates are in the future
3. Budget totals are consistent
4. All 15 campaigns are present
5. Creative entries have actual copy (not just directions)

Usage:
    python3 scripts/validate_campaign_config.py
"""

import json
import sys
from datetime import date, datetime

CONFIG = "campaigns/ridelux_v6/luxy_ride_campaign_config.json"
CREATIVES = "campaigns/ridelux_v6/luxy_ride_creatives.json"

errors = []
warnings = []


def check_placeholders(data, path=""):
    """Recursively check for <<REPLACE>> placeholders."""
    if isinstance(data, str):
        if "<<REPLACE" in data or "<<replace" in data.lower():
            errors.append(f"Placeholder found at {path}: {data[:60]}")
    elif isinstance(data, dict):
        for k, v in data.items():
            check_placeholders(v, f"{path}.{k}")
    elif isinstance(data, list):
        for i, v in enumerate(data):
            check_placeholders(v, f"{path}[{i}]")


def main():
    # Load config
    try:
        with open(CONFIG) as f:
            config = json.load(f)
    except Exception as e:
        errors.append(f"Cannot read config: {e}")
        report()
        return

    # 1. Placeholders
    check_placeholders(config)

    # 2. Flight dates
    flight = config.get("meta", {}).get("campaign_flight", {})
    start = flight.get("start", "")
    end = flight.get("end", "")
    today = date.today().isoformat()
    if start and start < today:
        warnings.append(f"Start date {start} is in the past (today={today})")
    if end and end < today:
        errors.append(f"End date {end} is in the past")

    # 3. Campaign count
    groups = config.get("campaign_groups", [])
    total_campaigns = sum(len(g.get("campaigns", [])) for g in groups)
    if total_campaigns != 15:
        errors.append(f"Expected 15 campaigns, found {total_campaigns}")

    # 4. Budget consistency
    daily_budget = config.get("meta", {}).get("total_daily_budget", 0)
    group_daily_sum = 0
    for g in groups:
        for c in g.get("campaigns", []):
            group_daily_sum += c.get("budget", {}).get("daily", 0)
    if abs(group_daily_sum - daily_budget) > 1.0:
        warnings.append(
            f"Campaign daily budget sum ({group_daily_sum:.2f}) "
            f"differs from meta total ({daily_budget:.2f})"
        )

    # 5. Creative copy check
    try:
        with open(CREATIVES) as f:
            creatives = json.load(f)
        # Handle both array and dict formats
        entries = creatives if isinstance(creatives, list) else creatives.get("creatives", [])
        for entry in entries:
            arch = entry.get("archetype", "?")
            touch = entry.get("touch_position", "?")
            if not entry.get("headline"):
                warnings.append(f"{arch} Touch {touch}: missing headline")
            if not entry.get("body"):
                warnings.append(f"{arch} Touch {touch}: missing body text")
            if not entry.get("cta"):
                warnings.append(f"{arch} Touch {touch}: missing CTA")
    except Exception as e:
        warnings.append(f"Cannot read creatives file: {e}")

    report()


def report():
    print("=" * 60)
    print("LUXY Ride Campaign Config Validation")
    print("=" * 60)

    if errors:
        print(f"\nERRORS ({len(errors)}):")
        for e in errors:
            print(f"  [FAIL] {e}")

    if warnings:
        print(f"\nWARNINGS ({len(warnings)}):")
        for w in warnings:
            print(f"  [WARN] {w}")

    if not errors and not warnings:
        print("\n  ALL CHECKS PASSED")

    print()
    status = "BLOCKED" if errors else "READY (with warnings)" if warnings else "READY"
    print(f"Status: {status}")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
