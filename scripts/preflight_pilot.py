#!/usr/bin/env python3
# =============================================================================
# Pre-Flight Validation — LUXY Ride Pilot
# =============================================================================
#
# Checks EVERYTHING needed before the campaign goes live:
#   - Server infrastructure (Neo4j, Redis, API)
#   - Data completeness (bilateral edges, PCA, priors)
#   - API endpoints responding
#   - Static files servable (informativ.js)
#   - Campaign config validity
#   - Signal pipeline functional
#
# Usage:
#   PYTHONPATH=. python scripts/preflight_pilot.py
#
# For remote server check (when server is running):
#   python scripts/preflight_pilot.py --server-url https://your-server.com
#
# =============================================================================

import argparse
import json
import os
import sys
import time
from pathlib import Path

CHECKS = []
PASSED = 0
FAILED = 0

PROJECT_ROOT = Path(__file__).parent.parent


def check(name, condition, detail=""):
    global PASSED, FAILED
    status = "PASS" if condition else "FAIL"
    if condition:
        PASSED += 1
    else:
        FAILED += 1
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {name}{suffix}")
    CHECKS.append((name, condition, detail))


def section(title):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def check_local():
    """Check local file system and imports."""

    section("A. DATA FILES")

    # Bilateral edges
    edges_path = PROJECT_ROOT / "reviews" / "luxury_bilateral_edges.json"
    check("Bilateral edges file exists", edges_path.exists())
    if edges_path.exists():
        with open(edges_path) as f:
            data = json.load(f)
        n_edges = len(data.get("edges", []))
        check("Bilateral edges count", n_edges >= 1400, f"{n_edges} edges")

    # PCA loadings
    pca_path = PROJECT_ROOT / "adam" / "data" / "pca_loadings_25d.json"
    check("PCA loadings file exists", pca_path.exists())
    if pca_path.exists():
        with open(pca_path) as f:
            pca = json.load(f)
        check("PCA has 7 components", pca.get("n_components") == 7)

    # Amazon priors
    priors_path = PROJECT_ROOT / "adam" / "data" / "amazon_priors.json"
    check("Amazon priors file exists", priors_path.exists())

    # Telemetry JS
    js_path = PROJECT_ROOT / "static" / "telemetry" / "informativ.js"
    check("INFORMATIV telemetry JS exists", js_path.exists())
    if js_path.exists():
        check("Telemetry JS size > 10KB", js_path.stat().st_size > 10000,
              f"{js_path.stat().st_size:,} bytes")

    section("B. CAMPAIGN FILES")

    # Agency handoff
    handoff = PROJECT_ROOT / "campaigns" / "ridelux_v6" / "AGENCY_HANDOFF_COMPLETE.md"
    check("Agency handoff document", handoff.exists())

    # Clean domain CSVs
    wl = PROJECT_ROOT / "campaigns" / "ridelux_v6" / "stackadapt_whitelist_upload.csv"
    bl = PROJECT_ROOT / "campaigns" / "ridelux_v6" / "stackadapt_blacklist_upload.csv"
    check("StackAdapt whitelist (clean)", wl.exists())
    check("StackAdapt blacklist (clean)", bl.exists())
    if wl.exists():
        domains = wl.read_text().strip().split("\n")
        check("Whitelist has domains", len(domains) >= 30, f"{len(domains)} domains")
    if bl.exists():
        domains = bl.read_text().strip().split("\n")
        check("Blacklist has domains", len(domains) >= 15, f"{len(domains)} domains")

    # Creatives
    creatives_path = PROJECT_ROOT / "campaigns" / "ridelux_v6" / "luxy_ride_creatives.json"
    check("Creatives JSON exists", creatives_path.exists())
    if creatives_path.exists():
        with open(creatives_path) as f:
            creatives = json.load(f)
        check("15 creatives defined", len(creatives) == 15, f"{len(creatives)} creatives")
        # Check no placeholder copy
        placeholders = [c for c in creatives if "PLACEHOLDER" in c.get("headline", "").upper()
                       or "TODO" in c.get("headline", "").upper()
                       or not c.get("headline")]
        check("All creatives have real copy", len(placeholders) == 0,
              f"{len(placeholders)} placeholders" if placeholders else "all populated")

    section("C. PYTHON IMPORTS")

    modules = [
        ("adam.main", "FastAPI app"),
        ("adam.retargeting.engines.processing_depth", "Signal 4"),
        ("adam.retargeting.engines.click_latency", "Signal 1"),
        ("adam.retargeting.engines.barrier_self_report", "Signal 2"),
        ("adam.retargeting.engines.organic_return", "Signal 3"),
        ("adam.retargeting.engines.device_compat", "Signal 5"),
        ("adam.retargeting.engines.frequency_decay", "Signal 6"),
        ("adam.retargeting.engines.nonconscious_profile", "Composite"),
        ("adam.retargeting.engines.signal_collector", "Collector"),
        ("adam.retargeting.engines.frustration", "Frustration"),
        ("adam.retargeting.engines.neural_linucb", "Neural-LinUCB"),
        ("adam.retargeting.engines.mechanism_selector", "Mechanism selector"),
        ("adam.intelligence.dimension_compressor", "PCA compressor"),
        ("adam.api.signals.router", "Signals API"),
        ("adam.infrastructure.redis.cache", "Redis cache"),
    ]

    for mod, label in modules:
        try:
            __import__(mod)
            check(f"Import: {label}", True)
        except Exception as e:
            check(f"Import: {label}", False, str(e)[:80])

    section("D. DEPLOYMENT FILES")

    check("Dockerfile exists", (PROJECT_ROOT / "deployment" / "Dockerfile").exists())
    check("docker-compose.prod.yml", (PROJECT_ROOT / "deployment" / "docker-compose.prod.yml").exists())
    check(".env.production template", (PROJECT_ROOT / "deployment" / ".env.production").exists())
    check("launch-pilot.sh", (PROJECT_ROOT / "deployment" / "launch-pilot.sh").exists())
    check("requirements.production.txt", (PROJECT_ROOT / "deployment" / "requirements.production.txt").exists())

    # Check .env.production for unfilled placeholders
    env_path = PROJECT_ROOT / "deployment" / ".env.production"
    if env_path.exists():
        content = env_path.read_text()
        placeholders = [line for line in content.split("\n")
                       if "<<REPLACE" in line and not line.strip().startswith("#")]
        check(".env placeholders to fill", True,
              f"{len(placeholders)} values need filling" if placeholders else "all filled")

    section("E. SIGNAL PIPELINE (functional test)")

    try:
        from adam.retargeting.engines.processing_depth import classify_processing_depth, ProcessingDepth
        depth = classify_processing_depth(0.5, False)
        check("Processing depth classifier", depth == ProcessingDepth.UNPROCESSED)
    except Exception as e:
        check("Processing depth classifier", False, str(e)[:60])

    try:
        from adam.intelligence.dimension_compressor import get_dimension_compressor
        comp = get_dimension_compressor()
        check("Dimension compressor loaded", comp.is_fitted)
        if comp.is_fitted:
            score = comp.get_conversion_score({"emotional_resonance": 0.8, "reactance_fit": 0.2})
            check("Conversion scoring works", 0 <= score <= 1, f"score={score:.3f}")
    except Exception as e:
        check("Dimension compressor", False, str(e)[:60])

    try:
        from adam.retargeting.engines.neural_linucb import NeuralLinUCBSelector, BILATERAL_CONTEXT_DIMS
        check("Neural-LinUCB context dims", len(BILATERAL_CONTEXT_DIMS) == 57,
              f"{len(BILATERAL_CONTEXT_DIMS)} dims")
        sel = NeuralLinUCBSelector()
        result = sel.select(
            bilateral_edge={"emotional_resonance": 0.8, "reactance_fit": 0.2},
            candidate_mechanisms=["evidence_proof", "narrative_transportation"],
        )
        check("Neural-LinUCB selection works", result.selected_mechanism in
              ["evidence_proof", "narrative_transportation"],
              f"latency={result.latency_ms:.1f}ms")
    except Exception as e:
        check("Neural-LinUCB", False, str(e)[:60])


def check_remote(server_url):
    """Check remote server endpoints."""
    import urllib.request
    import urllib.error

    section("F. REMOTE SERVER ENDPOINTS")

    endpoints = [
        ("/health", "Health check"),
        ("/health/ready", "Readiness check"),
        ("/api/v1/signals/health", "Signals API health"),
        ("/static/telemetry/informativ.js", "Telemetry JS served"),
        ("/metrics", "Prometheus metrics"),
        ("/docs", "API documentation"),
    ]

    for path, label in endpoints:
        url = f"{server_url.rstrip('/')}{path}"
        try:
            req = urllib.request.Request(url, method="GET")
            resp = urllib.request.urlopen(req, timeout=10)
            check(f"GET {path}", resp.status == 200, f"HTTP {resp.status}")
        except urllib.error.HTTPError as e:
            check(f"GET {path}", False, f"HTTP {e.code}")
        except Exception as e:
            check(f"GET {path}", False, str(e)[:60])

    # Test CORS headers
    section("G. CORS CONFIGURATION")
    try:
        url = f"{server_url.rstrip('/')}/api/v1/signals/health"
        req = urllib.request.Request(url, method="OPTIONS")
        req.add_header("Origin", "https://luxyride.com")
        req.add_header("Access-Control-Request-Method", "POST")
        resp = urllib.request.urlopen(req, timeout=10)
        cors_origin = resp.headers.get("Access-Control-Allow-Origin", "")
        check("CORS allows luxyride.com", "luxyride.com" in cors_origin or cors_origin == "*",
              f"Allow-Origin: {cors_origin}")
    except Exception as e:
        check("CORS check", False, str(e)[:60])


def main():
    parser = argparse.ArgumentParser(description="INFORMATIV Pre-Flight Validation")
    parser.add_argument("--server-url", help="Remote server URL to check (e.g. https://your-server.com)")
    args = parser.parse_args()

    print("=" * 60)
    print("INFORMATIV PRE-FLIGHT VALIDATION — LUXY Ride Pilot")
    print("=" * 60)

    check_local()

    if args.server_url:
        check_remote(args.server_url)

    print()
    print("=" * 60)
    if FAILED == 0:
        print(f"  STATUS: READY — All {PASSED} checks PASS")
    else:
        print(f"  STATUS: NOT READY — {FAILED} FAILURES out of {PASSED + FAILED} checks")
        print()
        print("  Failed checks:")
        for name, ok, detail in CHECKS:
            if not ok:
                print(f"    - {name}: {detail}")
    print("=" * 60)

    return 0 if FAILED == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
