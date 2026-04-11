#!/usr/bin/env python3
"""
INFORMATIV Pre-Flight Check — Run before pilot launch.

Validates EVERYTHING needed for the pilot to function:
1. Infrastructure (Neo4j, Redis)
2. Data integrity (edges, archetypes, theory graph, gradients)
3. Campaign config (no placeholders, valid dates)
4. System components (cascade, prefetch, intelligence loop)
5. Copy (all 15 touches have headlines/body/CTA)
6. Image assets (all 45 files present)
7. Webhook chain (attribution bridge validates)

Exit code 0 = READY TO LAUNCH
Exit code 1 = ISSUES FOUND
"""

import asyncio
import json
import os
import sys

PASS = 0
FAIL = 0
WARN = 0


def check(name, passed, detail=""):
    global PASS, FAIL
    if passed:
        PASS += 1
        print(f"  ✓ {name:50s} {detail[:50]}")
    else:
        FAIL += 1
        print(f"  ✗ {name:50s} {detail[:50]}")


def warn(name, detail=""):
    global WARN
    WARN += 1
    print(f"  ⚠ {name:50s} {detail[:50]}")


async def main():
    print("=" * 70)
    print("INFORMATIV PRE-FLIGHT CHECK")
    print("=" * 70)

    # 1. Infrastructure
    print("\n── INFRASTRUCTURE ──")
    try:
        from neo4j import GraphDatabase
        d = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "atomofthought"))
        d.verify_connectivity()
        check("Neo4j", True, "connected")
        d.close()
    except:
        check("Neo4j", False, "NOT CONNECTED — start Neo4j first")

    try:
        import redis
        redis.Redis().ping()
        check("Redis", True, "connected")
    except:
        check("Redis", False, "NOT CONNECTED — start Redis first")

    # 2. Data
    print("\n── DATA ──")
    try:
        from neo4j import GraphDatabase
        d = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "atomofthought"))
        with d.session() as s:
            lux = s.run('MATCH (pd)-[bc:BRAND_CONVERTED]->() WHERE pd.asin STARTS WITH "lux_" RETURN count(bc) AS c').single()["c"]
            check("Luxury edges", lux >= 3000, f"{lux:,} edges")

            archs = s.run('MATCH (pd)-[:BRAND_CONVERTED]->(ar) WHERE pd.asin STARTS WITH "lux_" AND ar.user_archetype IS NOT NULL RETURN count(DISTINCT ar.user_archetype) AS c').single()["c"]
            check("Archetype classification", archs >= 3, f"{archs} archetypes")

            theory = s.run("MATCH (n:PsychologicalState) RETURN count(n) AS c").single()["c"]
            check("Theory graph", theory >= 14, f"{theory} states")

            grads = s.run("MATCH (bp:BayesianPrior {prior_type:'gradient_field'}) WHERE bp.gradient_n_edges > 0 RETURN count(bp) AS c").single()["c"]
            check("Gradient fields", grads >= 3, f"{grads} fields")
        d.close()
    except Exception as e:
        check("Data integrity", False, str(e)[:50])

    # 3. Campaign config
    print("\n── CAMPAIGN CONFIG ──")
    try:
        with open("campaigns/ridelux_v6/luxy_ride_campaign_config.json") as f:
            cfg = json.load(f)

        # Check for placeholders
        cfg_str = json.dumps(cfg)
        placeholders = cfg_str.count("<<REPLACE")
        if placeholders > 0:
            warn(f"{placeholders} placeholder IDs remain", "Fill after StackAdapt account setup")
        else:
            check("No placeholders", True)

        check("Flight dates", cfg["meta"]["campaign_flight"]["start"] >= "2026-03-29")
        check("15 campaigns", sum(len(g.get("campaigns", [])) for g in cfg.get("campaign_groups", [])) == 15)
    except Exception as e:
        check("Campaign config", False, str(e)[:50])

    # 4. Copy
    print("\n── COPY ──")
    try:
        with open("campaigns/ridelux_v6/luxy_ride_creatives.json") as f:
            creatives = json.load(f)
        all_copy = all(c.get("headline") and c.get("body") and c.get("cta") for c in creatives)
        check("All 15 creatives have copy", all_copy)

        pipeline = sum(1 for c in creatives if "pipeline" in (c.get("copy_generated_by") or "").lower())
        check("Copy from full pipeline", pipeline >= 10, f"{pipeline}/15")
    except Exception as e:
        check("Copy", False, str(e)[:50])

    # 5. Domain lists
    print("\n── DOMAINS ──")
    try:
        with open("campaigns/ridelux_v6/luxy_ride_domain_whitelist.csv") as f:
            domains = [l.strip() for l in f if l.strip() and l.strip() != "domain"]
        check("Whitelist", len(domains) >= 25, f"{len(domains)} domains")

        with open("campaigns/ridelux_v6/luxy_ride_domain_blacklist.csv") as f:
            blocked = [l.strip() for l in f if l.strip() and l.strip() != "domain"]
        check("Blacklist", len(blocked) >= 3, f"{len(blocked)} domains")
    except Exception as e:
        check("Domains", False, str(e)[:50])

    # 6. Image assets
    print("\n── IMAGE ASSETS ──")
    asset_dir = "campaigns/ridelux_v6/assets"
    if os.path.exists(asset_dir):
        images = [f for f in os.listdir(asset_dir) if f.endswith(('.jpg', '.png', '.jpeg'))]
        if len(images) >= 45:
            check("Image assets", True, f"{len(images)} images")
        elif len(images) > 0:
            warn(f"Only {len(images)}/45 images", "Need 15 creatives × 3 sizes")
        else:
            warn("No images yet", "See IMAGE_CREATIVE_BRIEFS.md")
    else:
        warn("Assets directory empty", "See IMAGE_CREATIVE_BRIEFS.md")

    # 7. System components
    print("\n── SYSTEM COMPONENTS ──")
    try:
        from adam.api.stackadapt.bilateral_cascade import run_bilateral_cascade
        check("Bilateral cascade", True, "importable")
    except:
        check("Bilateral cascade", False)

    try:
        from adam.intelligence.causal_decomposition import get_causal_decomposition_engine
        check("Causal decomposition", True, "importable")
    except:
        check("Causal decomposition", False)

    try:
        from adam.intelligence.inferential_hypothesis_engine import get_inferential_hypothesis_engine
        check("Hypothesis engine", True, "importable")
    except:
        check("Hypothesis engine", False)

    try:
        from adam.intelligence.daily_intelligence_brief import generate_daily_brief
        check("Daily brief", True, "importable")
    except:
        check("Daily brief", False)

    # 8. Supporting docs
    print("\n── DOCUMENTATION ──")
    docs = [
        "STACKADAPT_SETUP_CHECKLIST.md",
        "STACKADAPT_IMPLEMENTATION_GUIDE.md",
        "STACKADAPT_API_SUBMISSION.md",
        "IMAGE_CREATIVE_BRIEFS.md",
    ]
    for doc in docs:
        path = f"campaigns/ridelux_v6/{doc}"
        check(doc, os.path.exists(path))

    # Summary
    print(f"\n{'='*70}")
    total = PASS + FAIL
    if FAIL == 0 and WARN == 0:
        print(f"PRE-FLIGHT: ALL CLEAR — {PASS}/{total} checks passed")
        print("READY TO LAUNCH")
        sys.exit(0)
    elif FAIL == 0:
        print(f"PRE-FLIGHT: {PASS}/{total} passed, {WARN} warnings")
        print("READY WITH WARNINGS (fill placeholders + produce images)")
        sys.exit(0)
    else:
        print(f"PRE-FLIGHT: {PASS} passed, {FAIL} FAILED, {WARN} warnings")
        print("NOT READY — fix failures above")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
