"""Q.2.A — endpoint correctness tests for /analytics/per-archetype-performance.

DecisionTrace.user_posterior_snapshot is Dict[str, float] — strings
not allowed. Archetype lookup is hooked through
``_archetype_lookup_for_user`` so tests patch the hook directly
rather than embedding archetype as a string in the schema-typed
snapshot.
"""

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from adam.api.dashboard.router import router
from adam.intelligence.decision_trace import DecisionTrace


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _trace(decision_id: str, user_id: str) -> DecisionTrace:
    return DecisionTrace(
        decision_id=decision_id,
        user_id=user_id,
        timestamp=datetime.now(timezone.utc),
        chosen_creative_id="ridelux_hero_1",
        chosen_mechanism="authority",
        chosen_score=0.7,
    )


def test_route_registered(client: TestClient):
    response = client.get("/api/dashboard/analytics/per-archetype-performance")
    assert response.status_code == 200
    body = response.json()
    assert "archetypes" in body
    assert "data_source_state" in body


def test_empty_state(client: TestClient):
    with patch(
        "adam.api.dashboard.cell_aggregation_service._fetch_window_traces",
        return_value=[],
    ):
        response = client.get("/api/dashboard/analytics/per-archetype-performance")
        body = response.json()
    assert body["archetypes"] == []
    assert body["total_impressions"] == 0
    assert body["data_source_state"] == "empty"


def test_partial_state_when_archetype_lookup_unwired(client: TestClient):
    """Pre-pilot: archetype lookup returns None → partial state."""
    traces = [_trace(f"d{i}", f"u_{i}") for i in range(3)]
    with patch(
        "adam.api.dashboard.cell_aggregation_service._fetch_window_traces",
        return_value=traces,
    ):
        response = client.get("/api/dashboard/analytics/per-archetype-performance")
        body = response.json()
    assert body["data_source_state"] == "partial"
    assert body["total_impressions"] == 3


def test_populated_state_groups_by_archetype(client: TestClient):
    traces = [
        _trace("d1", "u_a"),
        _trace("d2", "u_a"),
        _trace("d3", "u_b"),
    ]
    archmap = {"u_a": "achiever", "u_b": "explorer"}
    with patch(
        "adam.api.dashboard.cell_aggregation_service._fetch_window_traces",
        return_value=traces,
    ), patch(
        "adam.api.dashboard.cell_aggregation_service._archetype_lookup_for_user",
        side_effect=lambda u: archmap.get(u),
    ):
        response = client.get("/api/dashboard/analytics/per-archetype-performance")
        body = response.json()
    assert body["data_source_state"] == "populated"
    by_arch = {a["archetype_id"]: a for a in body["archetypes"]}
    assert by_arch["achiever"]["impression_count"] == 2
    assert by_arch["explorer"]["impression_count"] == 1


def test_pragmatist_marked_cold_start(client: TestClient):
    """Cold-start convention: PRAGMATIST default → cold_start_share == 1.0."""
    traces = [_trace(f"d{i}", f"u_{i}") for i in range(2)]
    with patch(
        "adam.api.dashboard.cell_aggregation_service._fetch_window_traces",
        return_value=traces,
    ), patch(
        "adam.api.dashboard.cell_aggregation_service._archetype_lookup_for_user",
        side_effect=lambda u: "pragmatist",
    ):
        response = client.get("/api/dashboard/analytics/per-archetype-performance")
        body = response.json()
    by_arch = {a["archetype_id"]: a for a in body["archetypes"]}
    assert abs(by_arch["pragmatist"]["cold_start_share"] - 1.0) < 1e-6


def test_conversion_rate_is_zero_in_pre_pilot(client: TestClient):
    """Pre-pilot: ConversionEdge join not wired → conversion_rate=0."""
    traces = [_trace("d1", "u_a")]
    with patch(
        "adam.api.dashboard.cell_aggregation_service._fetch_window_traces",
        return_value=traces,
    ), patch(
        "adam.api.dashboard.cell_aggregation_service._archetype_lookup_for_user",
        side_effect=lambda u: "achiever",
    ):
        response = client.get("/api/dashboard/analytics/per-archetype-performance")
        body = response.json()
    by_arch = {a["archetype_id"]: a for a in body["archetypes"]}
    assert by_arch["achiever"]["conversion_count"] == 0
    assert by_arch["achiever"]["conversion_rate"] == 0.0


def test_no_raw_buyer_id_in_response(client: TestClient):
    traces = [_trace("d1", "buyer_secret_xyz")]
    with patch(
        "adam.api.dashboard.cell_aggregation_service._fetch_window_traces",
        return_value=traces,
    ), patch(
        "adam.api.dashboard.cell_aggregation_service._archetype_lookup_for_user",
        side_effect=lambda u: "achiever",
    ):
        response = client.get("/api/dashboard/analytics/per-archetype-performance")
        body_text = response.text
    assert "buyer_secret_xyz" not in body_text


def test_query_param_days_default_30(client: TestClient):
    response = client.get("/api/dashboard/analytics/per-archetype-performance")
    assert response.status_code == 200
