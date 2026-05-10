"""Q.2.A — endpoint correctness tests for /analytics/per-cluster-fire-rate."""

from datetime import datetime, timezone
from typing import List
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from adam.api.dashboard.router import router
from adam.intelligence.decision_trace import (
    ChainOfReasoning,
    ChainOfReasoningEntry,
    DecisionTrace,
)


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _trace(decision_id: str, creative: str, chain_names=()) -> DecisionTrace:
    entries = []
    if chain_names:
        n = len(chain_names)
        pct = 100.0 / n
        entries = [
            ChainOfReasoningEntry(name=name, contribution=0.5, pct_of_total=pct)
            for name in chain_names
        ]
    return DecisionTrace(
        decision_id=decision_id,
        user_id=f"u_{decision_id}",
        timestamp=datetime.now(timezone.utc),
        chosen_creative_id=creative,
        chosen_mechanism="authority",
        chosen_score=0.7,
        chain_of_reasoning=ChainOfReasoning(entries=entries, total=0.5),
    )


def test_route_registered(client: TestClient):
    """Route reachable; empty-state response shape correct (Aura paused)."""
    response = client.get("/api/dashboard/analytics/per-cluster-fire-rate")
    assert response.status_code == 200
    body = response.json()
    assert "clusters" in body
    assert "predicates" in body
    assert "total_impressions" in body
    assert "data_source_state" in body


def test_empty_state_when_no_traces(client: TestClient):
    """No infrastructure → empty response with data_source_state='empty'."""
    with patch(
        "adam.api.dashboard.cell_aggregation_service._fetch_window_traces",
        return_value=[],
    ):
        response = client.get("/api/dashboard/analytics/per-cluster-fire-rate")
        body = response.json()
    assert body["clusters"] == []
    assert body["predicates"] == []
    assert body["total_impressions"] == 0
    assert body["data_source_state"] == "empty"


def test_populated_state_aggregates_clusters(client: TestClient):
    traces: List[DecisionTrace] = [
        _trace("d1", "ridelux_hero_1", chain_names=("fomo_active",)),
        _trace("d2", "ridelux_hero_2", chain_names=("fomo_active",)),
        _trace("d3", "ridelux_value_1", chain_names=("psych_ownership",)),
    ]
    with patch(
        "adam.api.dashboard.cell_aggregation_service._fetch_window_traces",
        return_value=traces,
    ):
        response = client.get("/api/dashboard/analytics/per-cluster-fire-rate")
        body = response.json()
    assert body["data_source_state"] == "populated"
    assert body["total_impressions"] == 3
    cluster_ids = {c["cluster_id"] for c in body["clusters"]}
    assert "ridelux_hero" in cluster_ids
    assert "ridelux_value" in cluster_ids


def test_partial_state_when_traces_but_no_predicate_fires(client: TestClient):
    """Traces present but chain_of_reasoning empty → partial."""
    traces = [_trace(f"d{i}", "ridelux_hero_1", chain_names=()) for i in range(3)]
    with patch(
        "adam.api.dashboard.cell_aggregation_service._fetch_window_traces",
        return_value=traces,
    ):
        response = client.get("/api/dashboard/analytics/per-cluster-fire-rate")
        body = response.json()
    assert body["data_source_state"] == "partial"
    assert body["total_impressions"] == 3
    # All known predicates should be dormant
    for p in body["predicates"]:
        assert p["dormant"] is True
        assert p["fire_count"] == 0


def test_dormant_predicate_flagged(client: TestClient):
    traces = [_trace("d1", "ridelux_hero_1", chain_names=("fomo_active",))]
    with patch(
        "adam.api.dashboard.cell_aggregation_service._fetch_window_traces",
        return_value=traces,
    ):
        response = client.get("/api/dashboard/analytics/per-cluster-fire-rate")
        body = response.json()
    by_name = {p["predicate_name"]: p for p in body["predicates"]}
    assert by_name["fomo_active"]["dormant"] is False
    assert by_name["maximizer_high"]["dormant"] is True


def test_query_param_days_validation(client: TestClient):
    """days must be in [1, 365]."""
    r1 = client.get("/api/dashboard/analytics/per-cluster-fire-rate?days=0")
    assert r1.status_code == 422
    r2 = client.get("/api/dashboard/analytics/per-cluster-fire-rate?days=999")
    assert r2.status_code == 422


def test_query_param_campaign_id_accepted(client: TestClient):
    response = client.get(
        "/api/dashboard/analytics/per-cluster-fire-rate?days=14&campaign_id=cmp_1"
    )
    assert response.status_code == 200


def test_window_bounds_present(client: TestClient):
    response = client.get("/api/dashboard/analytics/per-cluster-fire-rate?days=7")
    body = response.json()
    assert "window_start" in body
    assert "window_end" in body


def test_share_of_total_sums_to_one(client: TestClient):
    traces = [
        _trace(f"d{i}", "ridelux_hero_1", chain_names=())
        for i in range(5)
    ]
    with patch(
        "adam.api.dashboard.cell_aggregation_service._fetch_window_traces",
        return_value=traces,
    ):
        response = client.get("/api/dashboard/analytics/per-cluster-fire-rate")
        body = response.json()
    total_share = sum(c["share_of_total"] for c in body["clusters"])
    assert abs(total_share - 1.0) < 1e-6


def test_no_raw_buyer_id_in_response(client: TestClient):
    """Privacy guard: response must NOT contain raw user_id."""
    traces = [_trace("d1", "ridelux_hero_1", chain_names=("fomo_active",))]
    with patch(
        "adam.api.dashboard.cell_aggregation_service._fetch_window_traces",
        return_value=traces,
    ):
        response = client.get("/api/dashboard/analytics/per-cluster-fire-rate")
        body_text = response.text
    assert "u_d1" not in body_text  # raw user_id pattern
