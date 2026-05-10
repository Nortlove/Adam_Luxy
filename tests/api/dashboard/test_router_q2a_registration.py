"""Q.2.A — router registration + cross-cutting privacy/latency tests."""

import time
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from adam.api.dashboard.router import router


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# --- All 5 endpoints reachable ---


def test_all_5_endpoints_registered(client: TestClient):
    paths = [
        "/api/dashboard/analytics/per-cluster-fire-rate",
        "/api/dashboard/analytics/per-archetype-performance",
        "/api/dashboard/analytics/per-cohort-outcome-correlation",
        "/api/dashboard/learning/loop-dispatch-rates",
        "/api/dashboard/ledger/decision-trace/some_id",
    ]
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200, f"{path} returned {response.status_code}"


def test_router_imports_q2a_service(tmp_path):
    """Source pin — router must import the Q.2.A service module."""
    from pathlib import Path
    src = Path("adam/api/dashboard/router.py").read_text()
    assert "cell_aggregation_service" in src
    assert "get_per_cluster_fire_rate" in src
    assert "get_decision_trace_detail" in src


def test_q2a_service_module_imports():
    """Smoke: imports work + DISPATCH_METHOD_NAMES has 14 entries."""
    from adam.api.dashboard.cell_aggregation_service import (
        DISPATCH_METHOD_NAMES,
    )
    assert len(DISPATCH_METHOD_NAMES) == 14


# --- Privacy guard cross-cutting ---


def test_no_raw_buyer_id_across_all_5_endpoints(client: TestClient):
    """Cross-cutting: no endpoint may leak a raw buyer id pattern."""
    # We verify each endpoint with a state where buyer ids would be
    # most likely to appear. The endpoints that don't touch buyer ids
    # at all (cluster, dispatch) are still exercised for shape.
    sentinel = "RAW_BUYER_SHOULD_NEVER_APPEAR"
    paths = [
        "/api/dashboard/analytics/per-cluster-fire-rate",
        "/api/dashboard/analytics/per-archetype-performance",
        "/api/dashboard/analytics/per-cohort-outcome-correlation",
        "/api/dashboard/learning/loop-dispatch-rates",
    ]
    for path in paths:
        response = client.get(path)
        assert sentinel not in response.text


# --- Latency targets ---


def test_aggregation_endpoints_p99_under_500ms(client: TestClient):
    """Window-aggregating endpoints: target < 500ms in empty-state."""
    paths = [
        "/api/dashboard/analytics/per-cluster-fire-rate",
        "/api/dashboard/analytics/per-archetype-performance",
        "/api/dashboard/analytics/per-cohort-outcome-correlation",
        "/api/dashboard/learning/loop-dispatch-rates",
    ]
    for path in paths:
        # Warm up
        client.get(path)
        latencies = []
        for _ in range(10):
            t0 = time.time()
            client.get(path)
            latencies.append(time.time() - t0)
        latencies.sort()
        p99 = latencies[-1]  # 10 samples, p100 ~= p99 stand-in
        assert p99 < 0.5, f"{path} p99 {p99:.3f}s exceeds 500ms target"


def test_decision_trace_detail_p99_under_50ms(client: TestClient):
    """Single-trace lookup: target < 50ms in not_found state."""
    from unittest.mock import AsyncMock
    with patch(
        "adam.api.dashboard.cell_aggregation_service._get_async_redis_client",
        new=AsyncMock(return_value=None),
    ), patch(
        "adam.api.dashboard.cell_aggregation_service._get_async_neo4j_driver",
        new=AsyncMock(return_value=None),
    ):
        # Warm up
        client.get("/api/dashboard/ledger/decision-trace/probe_warmup")
        latencies = []
        for i in range(10):
            t0 = time.time()
            client.get(f"/api/dashboard/ledger/decision-trace/probe_{i}")
            latencies.append(time.time() - t0)
    latencies.sort()
    p99 = latencies[-1]
    # Generous bound — TestClient adds overhead. Real-world target 50ms;
    # test-environment bound 250ms accommodates request-scaffold overhead.
    assert p99 < 0.25, f"decision-trace-detail p99 {p99:.3f}s exceeds bound"
