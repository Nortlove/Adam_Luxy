#!/usr/bin/env python3
"""
Gap 5: Automated Campaign Creation + Weekly Evolution via GraphQL
=================================================================

Creates and evolves StackAdapt campaigns programmatically:
- Creates 8 archetype campaigns with multiple creative variants
- Configures conversion trackers and domain targeting
- Weekly: pauses losers, boosts winners, creates new variants from learning

Prerequisites:
    export STACKADAPT_GRAPHQL_KEY="your-key-here"
    export STACKADAPT_ADVERTISER_ID="your-advertiser-id"

Usage:
    # Initial campaign creation
    python3 scripts/stackadapt_campaign_manager.py create

    # Weekly evolution (run after learning systems update)
    python3 scripts/stackadapt_campaign_manager.py evolve

    # Status check
    python3 scripts/stackadapt_campaign_manager.py status
"""

import argparse
import json
import logging
import os
import sys
import time
from typing import Any, Dict, List, Optional

import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GRAPHQL_ENDPOINT = "https://api.stackadapt.com/graphql"

# Campaign specifications from INFORMATIV intelligence
CAMPAIGN_SPECS = {
    "careful_truster": {
        "name": "LUXY — Careful Truster",
        "segment_id": "informativ_careful_truster_authority_luxury_transportation_t1",
        "daily_budget": 33.0,
        "variants": [
            {
                "name": "CT-Authority",
                "mechanism": "authority",
                "headline": "The executive standard in ground transportation",
                "body": "Trusted by Fortune 500 travel managers. On-time guarantee backed by real-time tracking.",
                "cta": "See why professionals choose LUXY",
            },
            {
                "name": "CT-SocialProof",
                "mechanism": "social_proof",
                "headline": "10,000+ executive travelers trust LUXY",
                "body": "Join the professionals who demand reliability and discretion in every ride.",
                "cta": "Join the professionals",
            },
            {
                "name": "CT-CogEase",
                "mechanism": "cognitive_ease",
                "headline": "Premium transport. One tap.",
                "body": "No surge pricing. No uncertainty. Just seamless professional transportation.",
                "cta": "Book now",
            },
        ],
        "domains": ["bloomberg.com", "forbes.com", "wsj.com", "hbr.org", "ft.com",
                    "cnbc.com", "businessinsider.com", "fortune.com"],
    },
    "status_seeker": {
        "name": "LUXY — Status Seeker",
        "segment_id": "informativ_status_seeker_scarcity_luxury_transportation_t1",
        "daily_budget": 34.0,
        "variants": [
            {
                "name": "SS-SocialProof",
                "mechanism": "social_proof",
                "headline": "The ride that says you've arrived",
                "body": "When your car matters as much as your destination. Premium fleet, professional chauffeurs.",
                "cta": "Elevate your arrival",
            },
            {
                "name": "SS-Scarcity",
                "mechanism": "scarcity",
                "headline": "Limited fleet. Unlimited impression.",
                "body": "Our curated fleet of luxury vehicles is reserved for those who expect excellence.",
                "cta": "Reserve your car",
            },
            {
                "name": "SS-Authority",
                "mechanism": "authority",
                "headline": "The standard bearer in luxury ground transport",
                "body": "Recognized by Condé Nast Traveler. Chosen by discerning executives worldwide.",
                "cta": "Experience the standard",
            },
        ],
        "domains": ["robbreport.com", "departures.com", "luxurytravelmagazine.com",
                    "elledecor.com", "architecturaldigest.com", "townandcountrymag.com"],
    },
    "easy_decider": {
        "name": "LUXY — Easy Decider",
        "segment_id": "informativ_easy_decider_cognitive_ease_luxury_transportation_t1",
        "daily_budget": 35.0,
        "variants": [
            {
                "name": "ED-CogEase",
                "mechanism": "cognitive_ease",
                "headline": "Book in 30 seconds. Ride in style.",
                "body": "No accounts. No surge. No hassle. Premium transportation made effortless.",
                "cta": "One tap. Done.",
            },
            {
                "name": "ED-SocialProof",
                "mechanism": "social_proof",
                "headline": "Why thousands switch to LUXY every month",
                "body": "Simple booking. Reliable service. Premium vehicles. The easy choice.",
                "cta": "Try LUXY",
            },
        ],
        "domains": ["tripadvisor.com", "kayak.com", "google.com/travel",
                    "expedia.com", "hotels.com"],
    },
    "corporate_executive": {
        "name": "LUXY — Corporate Executive",
        "segment_id": "informativ_corporate_executive_social_proof_luxury_transportation_t1",
        "daily_budget": 30.0,
        "variants": [
            {
                "name": "CE-Authority",
                "mechanism": "authority",
                "headline": "Corporate ground transport. Redefined.",
                "body": "GSA-rate compliant. Receipt-ready. Travel policy approved. The professional choice.",
                "cta": "Set up your corporate account",
            },
            {
                "name": "CE-Commitment",
                "mechanism": "commitment",
                "headline": "Your company deserves better than rideshare",
                "body": "Dedicated account management. Volume pricing. Duty of care compliance.",
                "cta": "Request a corporate proposal",
            },
        ],
        "domains": ["businesstravelnews.com", "skift.com", "travelweekly.com",
                    "gbta.org", "phocuswire.com"],
    },
    "airport_anxiety": {
        "name": "LUXY — Airport Anxiety",
        "segment_id": "informativ_airport_anxiety_authority_luxury_transportation_t1",
        "daily_budget": 26.0,
        "variants": [
            {
                "name": "AA-Authority",
                "mechanism": "authority",
                "headline": "Never miss a flight. Guaranteed.",
                "body": "Real-time flight tracking. Automatic schedule adjustment. Free waiting time.",
                "cta": "Book your guaranteed transfer",
            },
            {
                "name": "AA-CogEase",
                "mechanism": "cognitive_ease",
                "headline": "Airport stress, solved.",
                "body": "Your driver tracks your flight. Arrives early. Handles luggage. You just relax.",
                "cta": "Relax. We've got this.",
            },
        ],
        "domains": ["flightaware.com", "airportguide.com", "tsa.gov",
                    "seatguru.com", "sleepinginairports.net"],
    },
    "special_occasion": {
        "name": "LUXY — Special Occasion",
        "segment_id": "informativ_special_occasion_liking_luxury_transportation_t1",
        "daily_budget": 30.0,
        "variants": [
            {
                "name": "SO-Liking",
                "mechanism": "liking",
                "headline": "Make your special day unforgettable — from the first ride",
                "body": "Weddings. Anniversaries. Milestones. Arrive in a way that matches the moment.",
                "cta": "Plan your event transportation",
            },
            {
                "name": "SO-SocialProof",
                "mechanism": "social_proof",
                "headline": "How 2,000+ couples arrived at their wedding",
                "body": "Reviewed 4.9/5 for event transportation. Decorated vehicles. Red carpet service.",
                "cta": "See wedding packages",
            },
        ],
        "domains": ["theknot.com", "weddingwire.com", "brides.com",
                    "marthastewartweddings.com", "zola.com"],
    },
    "first_timer": {
        "name": "LUXY — First Timer",
        "segment_id": "informativ_first_timer_curiosity_luxury_transportation_t1",
        "daily_budget": 20.0,
        "variants": [
            {
                "name": "FT-Curiosity",
                "mechanism": "curiosity",
                "headline": "Curious what a private car service is actually like?",
                "body": "It's not what you think. No stiffness. No pretension. Just a better ride.",
                "cta": "Try your first ride",
            },
            {
                "name": "FT-CogEase",
                "mechanism": "cognitive_ease",
                "headline": "Your first luxury ride. No commitment.",
                "body": "Download. Book. Ride. Cancel anytime. See what you've been missing.",
                "cta": "Get started free",
            },
        ],
        "domains": ["cntraveler.com", "travelandleisure.com", "afar.com",
                    "lonelyplanet.com", "thepointsguy.com"],
    },
    "repeat_loyal": {
        "name": "LUXY — Repeat Loyal",
        "segment_id": "informativ_repeat_loyal_commitment_luxury_transportation_t1",
        "daily_budget": 44.0,
        "variants": [
            {
                "name": "RL-Commitment",
                "mechanism": "commitment",
                "headline": "Welcome back. Your ride is ready.",
                "body": "Your preferences remembered. Your routes saved. Your loyalty rewarded.",
                "cta": "Book your usual",
            },
            {
                "name": "RL-Liking",
                "mechanism": "liking",
                "headline": "Thank you for choosing LUXY — again",
                "body": "Loyal riders get priority booking, preferred vehicles, and dedicated support.",
                "cta": "See your loyalty benefits",
            },
        ],
        "domains": ["bloomberg.com", "wsj.com", "ft.com", "cnbc.com",
                    "economist.com", "hbr.org"],
    },
}


def graphql_request(api_key: str, query: str, variables: Dict = None) -> Dict:
    """Execute a GraphQL request against StackAdapt."""
    headers = {
        "Content-Type": "application/json",
        "X-AUTHORIZATION": api_key,
    }
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    r = requests.post(GRAPHQL_ENDPOINT, json=payload, headers=headers, timeout=60)
    return r.json()


def create_campaigns(api_key: str, advertiser_id: str):
    """Create all 8 archetype campaigns with creative variants."""
    print("=" * 60)
    print("CREATING LUXY RIDE CAMPAIGNS")
    print("=" * 60)

    for arch, spec in CAMPAIGN_SPECS.items():
        print(f"\n── {spec['name']} ──")
        print(f"  Segment: {spec['segment_id']}")
        print(f"  Budget: ${spec['daily_budget']}/day")
        print(f"  Variants: {len(spec['variants'])}")
        for v in spec["variants"]:
            print(f"    [{v['mechanism']}] {v['headline']}")
        print(f"  Domains: {', '.join(spec['domains'][:3])}...")

        # In production, this would execute GraphQL mutations:
        # createCampaign, createCreative (per variant), setDomainTargeting
        # For now, output the spec as ready-to-execute

    print("\n" + "=" * 60)
    print("CAMPAIGN SPECS READY")
    print(f"Total campaigns: {len(CAMPAIGN_SPECS)}")
    print(f"Total variants: {sum(len(s['variants']) for s in CAMPAIGN_SPECS.values())}")
    print(f"Total daily budget: ${sum(s['daily_budget'] for s in CAMPAIGN_SPECS.values()):.0f}")
    print("=" * 60)


def evolve_campaigns(api_key: str, advertiser_id: str):
    """Weekly evolution: update campaigns based on learning."""
    print("=" * 60)
    print("WEEKLY CAMPAIGN EVOLUTION")
    print("=" * 60)

    # Load learning state
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    try:
        from adam.intelligence.campaign_report import generate_weekly_report, format_report_for_becca
        report = generate_weekly_report(week_number=1)
        print(format_report_for_becca(report))
    except Exception as e:
        logger.warning("Report generation failed: %s", e)

    # Load simulation for updated predictions
    try:
        from adam.intelligence.campaign_simulator import generate_campaign_forecast
        forecast = generate_campaign_forecast()

        print("\nUPDATED PREDICTIONS:")
        for pred in forecast.top_cells[:5]:
            print(f"  {pred.archetype} × {pred.mechanism} × {pred.domain_category}")
            print(f"    P(conv)={pred.p_conversion:.4f} | CPA=${pred.expected_cpa:.0f}")
    except Exception as e:
        logger.warning("Simulation failed: %s", e)

    print("\nEVOLUTION ACTIONS:")
    print("  (Actions would be pushed via GraphQL mutations)")
    print("  - Pause underperforming creative variants")
    print("  - Boost budget for winning archetypes")
    print("  - Create new variants from learning insights")
    print("  - Adjust domain bid modifiers from goal activation data")


def show_status(api_key: str, advertiser_id: str):
    """Show current campaign and learning status."""
    print("=" * 60)
    print("CAMPAIGN STATUS")
    print("=" * 60)

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    try:
        from adam.intelligence.bong_promotion import get_promotion_tracker
        tracker = get_promotion_tracker()
        print(f"\nBONG Promotion: {json.dumps(tracker.stats, indent=2)}")
    except Exception:
        pass

    try:
        from adam.intelligence.counterfactual_learner import get_counterfactual_learner
        cf = get_counterfactual_learner()
        print(f"Counterfactual: {json.dumps(cf.stats, indent=2)}")
    except Exception:
        pass

    try:
        from adam.retargeting.engines.intervention_emitter import get_intervention_emitter
        ie = get_intervention_emitter()
        print(f"Interventions: {json.dumps(ie.stats, indent=2)}")
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="StackAdapt campaign management")
    parser.add_argument("command", choices=["create", "evolve", "status"])
    args = parser.parse_args()

    api_key = os.environ.get("STACKADAPT_GRAPHQL_KEY", "")
    advertiser_id = os.environ.get("STACKADAPT_ADVERTISER_ID", "")

    if args.command == "create":
        create_campaigns(api_key, advertiser_id)
    elif args.command == "evolve":
        evolve_campaigns(api_key, advertiser_id)
    elif args.command == "status":
        show_status(api_key, advertiser_id)


if __name__ == "__main__":
    main()
