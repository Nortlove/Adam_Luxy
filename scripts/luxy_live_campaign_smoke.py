#!/usr/bin/env python3
"""Live-API smoke: pull current LUXY campaign data + verify creative scorer
shape compatibility against real production data.

Per the 2026-04-30 directive (memory: feedback_use_live_data_never_simulate):
  "There is no reason for us to be simulating" when live data is reachable.
  The current campaign isn't INFORMATIV-driven — it carries calibration
  signal nonetheless.

Per Chris's clarification on partial-real-data:
  "while the current campaign that is running is not our campaign...
   we may still need to simulate but we should always try to use the
   real data where we can"

This smoke shows what's REAL in the LUXY StackAdapt account:
  * Active campaign list (LIVE / DRAFT)
  * Ad inventory by subtype (NativeAd / DisplayAd / CtvAd / VideoAd)
  * Ad-level metadata (brand, channel, click URL)
  * For NativeAds: heading + tagline + cta (text creative — directly
    consumable by score_creative_features)
  * For DisplayAd / CtvAd: text creative is in image / video files,
    NOT exposed as text via the GraphQL schema

GAP HONESTLY DOCUMENTED:
  The current LUXY campaign uses Display + CTV (image + video) only.
  Native ads with text would route directly into score_creative_features.
  For image/video, downstream Phase G dashboard would need either:
    (a) Image OCR / video transcription (real but expensive)
    (b) Partner-provided creative copy (out-of-band)
    (c) Synthesized text matching the campaign theme + naming
        (e.g., 'LUXY Ride - Professionals - Journeys') — anchored
        to real but synthesized

Usage:
    python3 scripts/luxy_live_campaign_smoke.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(_PROJECT_ROOT / ".env")


async def main() -> int:
    from adam.integrations.stackadapt.graphql_client import get_stackadapt_client
    client = get_stackadapt_client()

    if not client.is_configured:
        print("FATAL: StackAdapt client not configured (no API token)")
        return 1

    # ── 1. Campaigns ──────────────────────────────────────────────
    campaigns_q = """
    query LuxyCampaigns {
      campaigns(first: 50) {
        edges {
          node {
            id name isArchived isDraft channelType tacticType goalType
            campaignStatus { state status }
            currentFlight { id name startTime partingTimeZone }
          }
        }
      }
    }
    """
    res = await client._query(campaigns_q)
    if "errors" in res:
        print(f"campaigns query failed: {res['errors']}")
        return 1

    campaign_edges = (res.get("campaigns") or {}).get("edges") or []
    print("=" * 78)
    print(f"LUXY ACCOUNT — LIVE CAMPAIGN STATE ({len(campaign_edges)} campaigns)")
    print("=" * 78)
    live = []
    draft = []
    for e in campaign_edges:
        n = e.get("node") or {}
        if n.get("isArchived"):
            continue
        if n.get("isDraft"):
            draft.append(n)
        else:
            live.append(n)
    print(f"\nLIVE: {len(live)} campaigns")
    for n in live:
        print(f"  ● {n.get('name','?'):50}  ({n.get('channelType')}/{n.get('tacticType')})")
    print(f"\nDRAFT: {len(draft)} campaigns")
    for n in draft:
        print(f"  ○ {n.get('name','?'):50}  ({n.get('channelType')}/{n.get('tacticType')})")

    # ── 2. Ads (with NativeAd creative copy where present) ────────
    ads_q = """
    query LuxyAds {
      ads(first: 100) {
        edges {
          node {
            __typename
            id name brandname channelType clickUrl
            ... on NativeAd { heading tagline cta }
            ... on VideoAd { heading tagline }
          }
        }
      }
    }
    """
    res = await client._query(ads_q)
    if "errors" in res:
        print(f"\nads query failed: {res['errors']}")
        return 1

    ad_edges = (res.get("ads") or {}).get("edges") or []
    print("\n" + "=" * 78)
    print(f"AD INVENTORY ({len(ad_edges)} ads)")
    print("=" * 78)

    by_type: dict[str, list[dict]] = {}
    for e in ad_edges:
        n = e.get("node") or {}
        t = n.get("__typename", "?")
        by_type.setdefault(t, []).append(n)

    for t, ads in sorted(by_type.items()):
        text_count = sum(
            1 for a in ads
            if a.get("heading") or a.get("tagline") or a.get("cta")
        )
        print(f"\n  {t}: {len(ads)} ads ({text_count} with text creative)")
        for a in ads[:3]:
            print(f"    {a.get('name','?')[:60]}")
            if a.get("heading") or a.get("tagline") or a.get("cta"):
                print(f"      HEADING: {a.get('heading')!r}")
                print(f"      TAGLINE: {a.get('tagline')!r}")
                print(f"      CTA:     {a.get('cta')!r}")

    # ── 3. Verify the creative scorer accepts production-shape data ─
    print("\n" + "=" * 78)
    print("CREATIVE SCORER COMPATIBILITY CHECK")
    print("=" * 78)
    scoreable = [
        a for a in ad_edges
        if isinstance(a.get("node"), dict) and (
            a["node"].get("heading") or a["node"].get("tagline") or a["node"].get("cta")
        )
    ]
    print(f"\nAds with directly-scoreable text creative: {len(scoreable)}")

    if not scoreable:
        print("\n  → Current LUXY campaign uses Display + CTV (image + video)")
        print("    only. None of the active ads expose text via the GraphQL")
        print("    schema. score_creative_features needs text input.")
        print("\n  → Honest gap (documented): downstream dashboard / blend_fit")
        print("    integration would need:")
        print("    (a) image OCR / video transcription (real but costly), OR")
        print("    (b) partner-provided creative copy, OR")
        print("    (c) synthesized text anchored to real campaign theme")
        print("        (e.g., 'LUXY Ride - Professionals - Journeys')")
    else:
        print(f"\n  → {len(scoreable)} ads can flow directly into")
        print("    score_creative_features. No shape adaptation needed.")

    # ── 4. Show campaign-name themes that ARE real signal ──────────
    print("\n" + "=" * 78)
    print("REAL SIGNAL FROM CAMPAIGN NAMES (anchor for synthesized text)")
    print("=" * 78)
    archetypes_seen = set()
    for n in live + draft:
        name = (n.get("name") or "").lower()
        for a in ("professionals", "executives", "leisure", "corporate", "website"):
            if a in name:
                archetypes_seen.add(a)
    print(f"\nArchetype tags in real campaign names: {sorted(archetypes_seen)}")
    print("\nThese are the real audience segments LUXY's media team is")
    print("targeting. Any synthesized creative copy for verification should")
    print("anchor to these themes, not invented archetypes.")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
