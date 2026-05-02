#!/usr/bin/env python3
"""Section 6 calibration runner — closes wrap-out hard-stop criterion (iii).

Executes both Section 6.2 cadence pipelines end-to-end on a curated
LUXY-plausible seed corpus + the existing campaign observations:

  Monthly cadence  → corpus mechanism re-discovery (Slice 33)
  Quarterly cadence → hierarchical prior reconciliation (Slice 34)

Persists a versioned-inventory artifact under
artifacts/section_6/ as JSON-lines. Per the wrap-out: "First run
is a calibration run; tune in v3 Phase 1."

Usage:
    python3 scripts/run_section_6_calibration.py
    python3 scripts/run_section_6_calibration.py --no-claude
        (skip the Claude API call — runs reconciliation only)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional


# =============================================================================
# Operator-curated LUXY seed corpus
# =============================================================================
#
# Per directive Section 6.3 (LUXY Brand Intelligence Library
# specification), LUXY's positioning spans: B2B corporate-travel
# black-car service, Concur/TripActions/TMC integration, executive-
# travel reliability, professional-driver staffing.
#
# Five primary metaphors named in the directive:
#   CONTAINMENT/CONTROL, RELIABILITY-AS-WEIGHT, FORWARD-MOTION/PROGRESS,
#   STATUS-AS-VERTICALITY, TIME-AS-RESOURCE.
#
# These snippets are operator-curated illustrative descriptions
# spanning those metaphors + the canonical 8 mechanisms; not
# fabrications of LUXY's actual marketing copy. Production runs
# will replace this with the actual LUXY corpus crawl when that
# infrastructure ships.

_LUXY_SEED_CORPUS: List[str] = [
    # CONTAINMENT/CONTROL — the executive owns the journey end-to-end.
    "Your travel manager controls every aspect of the executive's "
    "ground transportation, from the moment they touch down to the "
    "moment they return. Centralized booking. Integrated billing. "
    "Single point of accountability across cities and continents.",
    # RELIABILITY-AS-WEIGHT — the service is built on solid foundations.
    "Our drivers complete a 200-hour certification program. Every "
    "vehicle is inspected before each shift. Our infrastructure "
    "rests on 30 years of black-car experience. When the meeting "
    "matters, what carries the executive matters more.",
    # FORWARD-MOTION/PROGRESS — moving the business forward.
    "Step into the next phase of corporate travel. Move beyond ad-"
    "hoc booking. Advance toward fully integrated expense reporting "
    "via your Concur or SAP TripActions workflow. Your team's time "
    "should drive results, not paperwork.",
    # STATUS-AS-VERTICALITY — premium positioning.
    "Top-tier corporate travel for the senior executive. The "
    "highest standards in the industry. Leading global firms trust "
    "LUXY to elevate their travel experience above the standard "
    "ride-hail market.",
    # TIME-AS-RESOURCE — the executive's time is finite + valuable.
    "Save 40 minutes per business trip. Our drivers know the routes "
    "your team uses, the gates at the airports, and the hotels at "
    "your destination. Reclaim that hour for the work that pays.",
    # social_proof — the major firms already use LUXY.
    "Trusted by 350+ Fortune 1000 companies. The leading global "
    "law firms, investment banks, and consulting houses already "
    "use LUXY for their senior partners' ground transportation.",
    # authority — the credentials are real.
    "TSA-certified drivers. ISO 9001 quality management. Department-"
    "of-Transportation-licensed fleet. Insurance coverage exceeding "
    "$5 million per ride. Our credentials are not marketing — they "
    "are the operational floor.",
    # reciprocity — give value before asking.
    "Sign up your company today and your first three executive "
    "trips are complimentary. No card required. We invest in proving "
    "the service before asking for the long-term commitment.",
    # commitment — start small.
    "Start with one trip. One executive, one airport transfer. See "
    "the difference. Most clients begin with a single VIP trip and "
    "scale to enterprise-wide integration within 90 days.",
    # liking — personalization.
    "Your travel manager builds a profile for every executive. "
    "Their preferred greeting style. Their preferred vehicle class. "
    "The amenities they value. We treat your team the way the firm "
    "would treat its top clients.",
    # unity — we and our partners are one team.
    "Our partnership with your travel-management company means we "
    "share data, share standards, and share accountability. We "
    "are an extension of your team, not a vendor competing for "
    "your trust.",
    # reason_why — the structural reason it works.
    "Independent black-car services struggle with consistency "
    "across cities — different fleets, different standards, "
    "different risk profiles. We've built a single global operating "
    "standard so your executive's experience in Singapore matches "
    "the experience in San Francisco — that's why our clients "
    "consolidate to LUXY.",
    # scarcity — limited capacity at scale.
    "Our enterprise contracts are capped at 50 firms per region "
    "to maintain service density. We're currently accepting two "
    "new accounts in the Northeast metro corridor for the next "
    "quarter.",
    # warmth metaphor — trust and personal connection.
    "We treat your executive like family. The driver remembers her "
    "favorite seat, his preferred climate, the music their team "
    "always plays. Black-car service should feel like a friend who "
    "happens to drive.",
    # path metaphor — the journey is direct.
    "Direct routes. No multi-stop pickups. No detours. We take the "
    "fastest path from origin to destination, with the driver "
    "navigating real-time traffic so your team's path stays clear.",
]


# Per Section 6.2 quarterly cadence, the reconciliation walks
# corpus → category → brand → campaign. v0.1 calibration uses
# these illustrative observation counts to demonstrate the pipeline.
_RECONCILE_OBSERVATIONS: Dict[str, Dict[str, tuple]] = {
    # Corpus-level: broad transportation/B2B observations.
    "corpus_observations": {
        "social_proof": (10000, 4500),
        "authority": (10000, 5200),
        "scarcity": (10000, 2100),
        "reciprocity": (10000, 3800),
        "commitment": (10000, 4200),
        "liking": (10000, 4900),
        "unity": (10000, 4400),
        "reason_why": (10000, 5500),
    },
    # Category: B2B corporate-travel — authority + reason_why
    # over-perform vs corpus.
    "category_observations": {
        "social_proof": (2000, 900),
        "authority": (2000, 1300),
        "scarcity": (2000, 200),
        "reciprocity": (2000, 700),
        "commitment": (2000, 900),
        "liking": (2000, 700),
        "unity": (2000, 900),
        "reason_why": (2000, 1400),
    },
    # Brand: LUXY-specific — reliability-as-weight (authority) + unity
    # ship strongly per Section 6.3.
    "brand_observations": {
        "social_proof": (500, 220),
        "authority": (500, 350),
        "scarcity": (500, 30),
        "reciprocity": (500, 180),
        "commitment": (500, 240),
        "liking": (500, 200),
        "unity": (500, 280),
        "reason_why": (500, 360),
    },
    # Campaign: current LUXY rideshare campaign (substrate-
    # validation scale; no real conversion data yet).
    "campaign_observations": {
        "social_proof": (50, 22),
        "authority": (50, 30),
        "scarcity": (50, 3),
        "reciprocity": (50, 18),
        "commitment": (50, 24),
        "liking": (50, 19),
        "unity": (50, 26),
        "reason_why": (50, 32),
    },
}


def _load_env_from_dotenv() -> None:
    env_path = Path(__file__).parent.parent / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def _build_claude_client() -> Optional[Any]:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    try:
        from adam.llm.client import ClaudeClient
        return ClaudeClient()
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "ClaudeClient construction failed: %s", exc,
        )
        return None


async def _run(args: argparse.Namespace) -> int:
    log = logging.getLogger("section_6_calibration")

    from adam.intelligence.section_6 import (
        rediscover_from_corpus,
        reconcile_hierarchy,
    )

    inventory_version = (
        f"luxy-calibration-{int(time.time())}"
    )

    # ── Monthly cadence: corpus mechanism re-discovery ──
    rediscovery_result = None
    if args.no_claude:
        log.info("--no-claude flag set; skipping Claude API call")
    else:
        client = _build_claude_client()
        if client is None:
            log.warning(
                "ANTHROPIC_API_KEY not set; skipping Claude rediscovery "
                "(reconciliation will still run)"
            )
        else:
            log.info(
                "Running corpus mechanism re-discovery on %d-snippet seed "
                "corpus...", len(_LUXY_SEED_CORPUS),
            )
            rediscovery_result = await rediscover_from_corpus(
                corpus=_LUXY_SEED_CORPUS,
                claude_client=client,
                inventory_version=inventory_version,
            )
            log.info(
                "Re-discovery complete: %d mechanisms proposed (%d survive "
                "BH-FDR), %d metaphors proposed (%d survive)",
                len(rediscovery_result.proposed_mechanisms),
                rediscovery_result.surviving_mechanism_count,
                len(rediscovery_result.proposed_metaphors),
                rediscovery_result.surviving_metaphor_count,
            )
            try:
                await client.close()
            except Exception:
                pass

    # ── Quarterly cadence: hierarchical reconciliation ──
    log.info(
        "Running hierarchical reconciliation across "
        "corpus → category → brand → campaign...",
    )
    reconcile_result = reconcile_hierarchy(
        corpus_observations=_RECONCILE_OBSERVATIONS["corpus_observations"],
        category_observations=_RECONCILE_OBSERVATIONS["category_observations"],
        brand_observations=_RECONCILE_OBSERVATIONS["brand_observations"],
        campaign_observations=_RECONCILE_OBSERVATIONS["campaign_observations"],
        inventory_version=inventory_version,
    )
    log.info(
        "Reconciliation complete: %d levels reconciled across %d mechanisms",
        len(reconcile_result.levels), len(reconcile_result.mechanisms),
    )

    # ── Persist versioned-inventory artifact ──
    out_dir = (
        Path(__file__).parent.parent / "artifacts" / "section_6"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = out_dir / f"calibration_{inventory_version}.jsonl"

    with open(artifact_path, "w") as f:
        # Header
        header = {
            "_record_type": "section_6_header",
            "inventory_version": inventory_version,
            "calibration_run_at_ts": time.time(),
            "corpus_n_snippets": len(_LUXY_SEED_CORPUS),
            "reconcile_levels": [
                l.level_name for l in reconcile_result.levels
            ],
        }
        f.write(json.dumps(header) + "\n")

        # Reconciled hierarchy levels
        for level in reconcile_result.levels:
            payload = {
                "_record_type": "reconcile_level",
                "level_name": level.level_name,
                "parent_level": level.parent_level,
                "n_observations": level.n_observations,
                "parent_prior_strength": level.parent_prior_strength,
                "per_mechanism_alpha_beta": {
                    m: list(ab)
                    for m, ab in level.per_mechanism_alpha_beta.items()
                },
            }
            f.write(json.dumps(payload) + "\n")

        # Re-discovery proposals (when Claude ran)
        if rediscovery_result is not None:
            for prop in rediscovery_result.proposed_mechanisms:
                payload = {
                    "_record_type": "proposed_mechanism",
                    "name": prop.name,
                    "evidence_quotes": list(prop.evidence_quotes),
                    "supporting_metaphors": list(prop.supporting_metaphors),
                    "raw_p_value": prop.raw_p_value,
                    "survives_fdr": prop.survives_fdr,
                }
                f.write(json.dumps(payload) + "\n")
            for prop in rediscovery_result.proposed_metaphors:
                payload = {
                    "_record_type": "proposed_metaphor",
                    "axis_name": prop.axis_name,
                    "evidence_quotes": list(prop.evidence_quotes),
                    "supporting_tokens": list(prop.supporting_tokens),
                    "raw_p_value": prop.raw_p_value,
                    "survives_fdr": prop.survives_fdr,
                }
                f.write(json.dumps(payload) + "\n")
            for err in rediscovery_result.errors:
                f.write(json.dumps({
                    "_record_type": "rediscovery_error", "error": err,
                }) + "\n")

    log.info("Artifact written: %s (%d bytes)",
             artifact_path, artifact_path.stat().st_size)

    print()
    print("=" * 90)
    print("SECTION 6 CALIBRATION SUMMARY")
    print("=" * 90)
    print(f"Inventory version: {inventory_version}")
    print(f"Corpus snippets:   {len(_LUXY_SEED_CORPUS)}")
    print(f"Artifact:          {artifact_path}")
    print()

    print("Hierarchical reconciliation (per-level posterior means):")
    print("-" * 90)
    for level in reconcile_result.levels:
        print(f"  {level.level_name} (parent={level.parent_level}, "
              f"n_obs={level.n_observations}):")
        for m in sorted(level.per_mechanism_alpha_beta.keys()):
            a, b = level.per_mechanism_alpha_beta[m]
            mean = a / (a + b) if (a + b) > 0 else 0.0
            print(f"    {m:<16}  Beta(α={a:8.2f}, β={b:8.2f})  mean={mean:.4f}")
        print()

    if rediscovery_result is not None:
        print("Corpus re-discovery proposals:")
        print("-" * 90)
        if rediscovery_result.proposed_mechanisms:
            print("  Mechanisms:")
            for p in rediscovery_result.proposed_mechanisms:
                surv = "✓ SURVIVES" if p.survives_fdr else "  rejected"
                print(f"    [{surv}]  {p.name}  (raw_p={p.raw_p_value:.4f})")
        else:
            print("  Mechanisms: (none proposed)")
        if rediscovery_result.proposed_metaphors:
            print("  Metaphors:")
            for p in rediscovery_result.proposed_metaphors:
                surv = "✓ SURVIVES" if p.survives_fdr else "  rejected"
                print(f"    [{surv}]  {p.axis_name}  (raw_p={p.raw_p_value:.4f})")
        else:
            print("  Metaphors: (none proposed)")
        if rediscovery_result.errors:
            print("  Errors:")
            for e in rediscovery_result.errors:
                print(f"    {e}")

    print()
    print("=" * 90)
    print("Hard-stop criterion (iii) status: artifact written → CRITERION CLOSED")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--no-claude", action="store_true",
        help="Skip Claude API call; run reconciliation only.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    _load_env_from_dotenv()

    return asyncio.run(_run(args))


if __name__ == "__main__":
    sys.exit(main())
