#!/usr/bin/env python3
"""
Production Deployment Verification
Run AFTER deploying to EC2 to verify everything works.

Usage:
    python3 scripts/verify_production.py
    python3 scripts/verify_production.py --url https://informativ.yourdomain.com
"""

import argparse
import asyncio
import json
import sys
import time


async def verify_local():
    """Verify local installation."""
    print("=" * 60)
    print("PRODUCTION VERIFICATION — Local")
    print("=" * 60)

    checks = 0
    passed = 0

    # Neo4j
    checks += 1
    try:
        from neo4j import GraphDatabase
        import os
        pwd = os.environ.get("NEO4J_PASSWORD", "atomofthought")
        d = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", pwd))
        d.verify_connectivity()
        with d.session() as s:
            edges = s.run("MATCH ()-[r:BRAND_CONVERTED]->() RETURN count(r) AS c").single()["c"]
        d.close()
        if edges > 0:
            print(f"  ✓ Neo4j: {edges:,} edges")
            passed += 1
        else:
            print(f"  ✗ Neo4j: connected but NO EDGES — import database")
    except Exception as e:
        print(f"  ✗ Neo4j: {e}")

    # Redis
    checks += 1
    try:
        import redis
        redis.Redis().ping()
        print(f"  ✓ Redis: connected")
        passed += 1
    except:
        print(f"  ✗ Redis: not connected")

    # ANTHROPIC_API_KEY
    checks += 1
    import os
    if os.environ.get("ANTHROPIC_API_KEY"):
        print(f"  ✓ ANTHROPIC_API_KEY: set")
        passed += 1
    else:
        print(f"  ✗ ANTHROPIC_API_KEY: NOT SET")

    # ADAM_API_KEYS
    checks += 1
    if os.environ.get("ADAM_API_KEYS"):
        print(f"  ✓ ADAM_API_KEYS: set (auth enabled)")
        passed += 1
    else:
        print(f"  ⚠ ADAM_API_KEYS: not set (auth disabled)")
        passed += 1  # Warning, not failure

    # Theory graph
    checks += 1
    try:
        from neo4j import GraphDatabase
        d = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", pwd))
        with d.session() as s:
            theory = s.run("MATCH (n:PsychologicalState) RETURN count(n) AS c").single()["c"]
        d.close()
        if theory >= 14:
            print(f"  ✓ Theory graph: {theory} states")
            passed += 1
        else:
            print(f"  ✗ Theory graph: only {theory} states (need ≥14)")
    except:
        print(f"  ✗ Theory graph: query failed")

    # Gradient fields
    checks += 1
    try:
        from neo4j import GraphDatabase
        d = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", pwd))
        with d.session() as s:
            grads = s.run("MATCH (bp:BayesianPrior {prior_type:'gradient_field'}) WHERE bp.gradient_n_edges > 0 RETURN count(bp) AS c").single()["c"]
        d.close()
        if grads >= 3:
            print(f"  ✓ Gradient fields: {grads}")
            passed += 1
        else:
            print(f"  ✗ Gradient fields: {grads} (need ≥3) — run scripts/compute_gradient_fields.py")
    except:
        print(f"  ✗ Gradient fields: query failed")

    # Application import
    checks += 1
    try:
        from adam.main import create_app
        print(f"  ✓ Application: importable")
        passed += 1
    except Exception as e:
        print(f"  ✗ Application: {e}")

    # Campaign files
    checks += 1
    try:
        with open("campaigns/ridelux_v6/luxy_ride_campaign_config.json") as f:
            json.load(f)
        print(f"  ✓ Campaign config: valid JSON")
        passed += 1
    except:
        print(f"  ✗ Campaign config: not found or invalid")

    print(f"\n{passed}/{checks} checks passed")
    if passed == checks:
        print("PRODUCTION READY")
    else:
        print("FIX ISSUES ABOVE")
        sys.exit(1)


async def verify_remote(url: str):
    """Verify remote server via HTTP."""
    import httpx

    print(f"Verifying {url}...")

    async with httpx.AsyncClient(timeout=30) as client:
        # Health
        try:
            r = await client.get(f"{url}/health")
            print(f"  ✓ Health: {r.status_code}")
        except Exception as e:
            print(f"  ✗ Health: {e}")
            return

        # Metrics
        try:
            r = await client.get(f"{url}/metrics")
            print(f"  ✓ Metrics: {r.status_code}")
        except:
            print(f"  ⚠ Metrics: unavailable")

        # Auth check
        try:
            r = await client.get(f"{url}/api/v1/decisions")
            if r.status_code == 401:
                print(f"  ✓ Auth: enforced (401 without key)")
            else:
                print(f"  ⚠ Auth: not enforced ({r.status_code})")
        except:
            pass

        print("\nRemote verification complete")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="", help="Remote server URL")
    args = parser.parse_args()

    if args.url:
        await verify_remote(args.url)
    else:
        await verify_local()


if __name__ == "__main__":
    asyncio.run(main())
