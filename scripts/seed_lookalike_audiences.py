#!/usr/bin/env python3
"""
Gap 4: Lookalike Audience Seeding from Psychological Profiles
==============================================================

Takes LUXY Ride first-party data (email list, booking history),
scores each customer against our archetype model, and uploads the
highest-value archetype clusters as StackAdapt CRM segments via
GraphQL. StackAdapt builds lookalike audiences from these seeds —
targeting people who PSYCHOLOGICALLY RESEMBLE our best converters.

Prerequisites:
- LUXY first-party data (CSV with email, name, booking history)
- StackAdapt GraphQL API key (from Becca's account manager)
- pip install requests

Usage:
    export STACKADAPT_GRAPHQL_KEY="your-key-here"
    python3 scripts/seed_lookalike_audiences.py --input luxy_customers.csv
"""

import argparse
import csv
import hashlib
import json
import logging
import os
import sys
from typing import Any, Dict, List, Optional

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GRAPHQL_ENDPOINT = "https://api.stackadapt.com/graphql"


def classify_archetype(customer: Dict[str, Any]) -> str:
    """Score a customer against INFORMATIV archetype model.

    Uses booking history patterns to infer psychological archetype.
    This is a simplified classifier — the full system uses 27
    bilateral dimensions. For seeding purposes, behavioral proxies
    are sufficient because StackAdapt's lookalike model will
    generalize from the seed.
    """
    bookings = int(customer.get("total_bookings", 0))
    avg_fare = float(customer.get("avg_fare", 0))
    airport_pct = float(customer.get("airport_booking_pct", 0))
    corporate = customer.get("corporate_account", "").lower() == "true"
    event_bookings = int(customer.get("event_bookings", 0))

    if corporate and bookings >= 5:
        return "corporate_executive"
    if airport_pct > 0.6:
        return "airport_anxiety"
    if event_bookings > 0:
        return "special_occasion"
    if bookings >= 10:
        return "repeat_loyal"
    if bookings >= 3 and avg_fare > 200:
        return "status_seeker"
    if bookings == 1:
        return "first_timer"
    if avg_fare < 100:
        return "easy_decider"
    return "careful_truster"


def hash_pii(value: str) -> str:
    """SHA-1 hash for StackAdapt CRM upload (their required format)."""
    return hashlib.sha1(value.strip().lower().encode()).hexdigest()


def upload_crm_segment(
    api_key: str,
    segment_name: str,
    hashed_emails: List[str],
    advertiser_id: str,
) -> Optional[str]:
    """Upload a CRM segment to StackAdapt via GraphQL."""
    mutation = """
    mutation createCRMSegment($input: CRMSegmentInput!) {
        createCRMSegment(input: $input) {
            segment { id name matchRate }
            userErrors { message path }
        }
    }
    """
    variables = {
        "input": {
            "name": segment_name,
            "advertiserId": advertiser_id,
            "emails": hashed_emails,
        }
    }

    headers = {
        "Content-Type": "application/json",
        "X-AUTHORIZATION": api_key,
    }

    try:
        r = requests.post(
            GRAPHQL_ENDPOINT,
            json={"query": mutation, "variables": variables},
            headers=headers,
            timeout=60,
        )
        data = r.json()
        if "errors" in data:
            logger.error("GraphQL errors: %s", data["errors"])
            return None
        segment = data.get("data", {}).get("createCRMSegment", {}).get("segment", {})
        return segment.get("id")
    except Exception as e:
        logger.error("CRM segment upload failed: %s", e)
        return None


def main():
    parser = argparse.ArgumentParser(description="Seed lookalike audiences from LUXY data")
    parser.add_argument("--input", required=True, help="Path to LUXY customer CSV")
    parser.add_argument("--advertiser-id", default="", help="StackAdapt advertiser ID")
    parser.add_argument("--dry-run", action="store_true", help="Classify only, don't upload")
    args = parser.parse_args()

    api_key = os.environ.get("STACKADAPT_GRAPHQL_KEY", "")
    if not api_key and not args.dry_run:
        logger.error("Set STACKADAPT_GRAPHQL_KEY environment variable")
        sys.exit(1)

    # Read customer data
    customers = []
    with open(args.input) as f:
        reader = csv.DictReader(f)
        for row in reader:
            customers.append(row)

    logger.info("Loaded %d customers from %s", len(customers), args.input)

    # Classify into archetypes
    archetype_buckets: Dict[str, List[Dict]] = {}
    for customer in customers:
        arch = classify_archetype(customer)
        if arch not in archetype_buckets:
            archetype_buckets[arch] = []
        archetype_buckets[arch].append(customer)

    # Report
    print("\n=== ARCHETYPE CLASSIFICATION ===")
    for arch, members in sorted(archetype_buckets.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  {arch}: {len(members)} customers")

    if args.dry_run:
        print("\n[DRY RUN] No upload performed.")
        return

    # Upload each archetype as a CRM segment
    print("\n=== UPLOADING CRM SEGMENTS ===")
    for arch, members in archetype_buckets.items():
        if len(members) < 100:
            print(f"  {arch}: skipping ({len(members)} < 100 minimum for useful lookalike)")
            continue

        hashed = [hash_pii(m.get("email", "")) for m in members if m.get("email")]
        if len(hashed) < 100:
            continue

        segment_name = f"INFORMATIV_{arch}_seed"
        segment_id = upload_crm_segment(
            api_key, segment_name, hashed, args.advertiser_id
        )
        if segment_id:
            print(f"  {arch}: uploaded {len(hashed)} emails → segment {segment_id}")
            print(f"    → Enable Lookalike Expansion in StackAdapt for 5-10x reach")
        else:
            print(f"  {arch}: upload failed")

    print("\nDone. Enable Lookalike Expansion on each segment in StackAdapt dashboard.")


if __name__ == "__main__":
    main()
