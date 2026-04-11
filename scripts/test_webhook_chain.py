#!/usr/bin/env python3
"""
Test the complete webhook → outcome handler → learning cascade chain.

Run this AFTER the INFORMATIV server is running to verify
the full attribution path works before going live.

Usage:
    # Against local server:
    python3 scripts/test_webhook_chain.py

    # Against production:
    python3 scripts/test_webhook_chain.py --url https://your-server.com
"""

import argparse
import asyncio
import json
import sys
import time


async def test_internal():
    """Test the internal chain without HTTP (direct function call)."""
    print("Testing INTERNAL chain (no HTTP)...")
    print("=" * 60)

    from adam.api.stackadapt.attribution_bridge import (
        validate_attribution_chain, simulate_conversion_flow,
    )

    # 1. Simulate full conversion
    result = simulate_conversion_flow(
        archetype="careful_truster",
        mechanism="authority",
        page_url="https://businesstraveller.com/features/test",
        barrier="negativity_block",
    )

    print(f"\n1. Attribution validation: {'PASS' if result['validation']['valid'] else 'FAIL'}")
    for check in result['validation']['checks']:
        print(f"   {check}")
    print(f"   Paths that would fire: {result['coverage']}")

    # 2. Run through outcome handler
    print(f"\n2. Outcome handler...")
    from adam.core.learning.outcome_handler import OutcomeHandler
    handler = OutcomeHandler()

    t0 = time.time()
    outcome = await handler.process_outcome(
        decision_id="webhook_test_001",
        outcome_type="conversion",
        outcome_value=1.0,
        metadata=result['event'],
    )
    elapsed = (time.time() - t0) * 1000

    updates = outcome.get("updates", {})
    fired = sum(1 for v in updates.values() if v and "error" not in str(v).lower())

    print(f"   Processed in {elapsed:.0f}ms")
    print(f"   Paths fired: {fired}")

    for name in ['thompson', 'resonance_learning', 'causal_intelligence',
                  'priority_crawl', 'counterfactual', 'copy_learning']:
        v = updates.get(name)
        if v:
            print(f"   ✓ {name}: {str(v)[:60]}")

    # 3. Check learning state
    print(f"\n3. Learning state after test conversion:")
    try:
        from adam.intelligence.inferential_hypothesis_engine import get_inferential_hypothesis_engine
        he = get_inferential_hypothesis_engine()
        print(f"   Hypotheses: {he.stats}")
    except: pass

    try:
        from adam.intelligence.prediction_engine import get_prediction_engine
        pe = get_prediction_engine()
        print(f"   Predictions: {pe.stats}")
    except: pass

    print(f"\n{'='*60}")
    print(f"RESULT: {'PASS' if fired >= 10 else 'DEGRADED' if fired >= 5 else 'FAIL'} ({fired} paths)")


async def test_http(base_url: str):
    """Test via HTTP against running server."""
    import httpx

    print(f"Testing HTTP chain against {base_url}...")
    print("=" * 60)

    webhook_payload = {
        "events": [{
            "event_id": "test_evt_001",
            "uid": "sa-TEST",
            "url": "https://luxyride.com/booking-complete",
            "event_args": {
                "action": "booking_complete",
                "revenue": 189.00,
                "order_id": "TEST-001",
                "informativ_segment_id": "informativ_corporate_executive_luxury_transportation_t1",
            }
        }]
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Health check
        try:
            r = await client.get(f"{base_url}/health")
            print(f"1. Health: {r.status_code} {'✓' if r.status_code == 200 else '✗'}")
        except Exception as e:
            print(f"1. Health: FAILED — {e}")
            print(f"   Is the server running? Start with: ./scripts/start_pilot.sh")
            return

        # Webhook test
        try:
            r = await client.post(
                f"{base_url}/api/v1/stackadapt/webhook",
                json=webhook_payload,
            )
            print(f"2. Webhook: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                print(f"   Response: {json.dumps(data, indent=2)[:200]}")
            else:
                print(f"   Error: {r.text[:200]}")
        except Exception as e:
            print(f"2. Webhook: FAILED — {e}")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="", help="Server URL for HTTP test")
    args = parser.parse_args()

    if args.url:
        await test_http(args.url)
    else:
        await test_internal()


if __name__ == "__main__":
    asyncio.run(main())
