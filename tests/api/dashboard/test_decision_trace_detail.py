"""Q.2.A — endpoint correctness tests for /ledger/decision-trace/{impression_id}."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from adam.api.dashboard.router import router
from adam.intelligence.decision_trace import (
    AlternativeCandidate,
    ChainOfReasoning,
    ChainOfReasoningEntry,
    DecisionTrace,
)


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _trace(
    decision_id: str = "imp_123",
    user_id: str = "buyer_secret_alpha",
) -> DecisionTrace:
    return DecisionTrace(
        decision_id=decision_id,
        user_id=user_id,
        timestamp=datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc),
        chosen_creative_id="ridelux_hero_3",
        chosen_mechanism="authority",
        chosen_score=0.84,
        alternatives=[
            AlternativeCandidate(
                creative_id="ridelux_value_1",
                mechanism="social_proof",
                posterior_score=0.65,
                propensity_under_TS=0.20,
            ),
        ],
        # user_posterior_snapshot is Dict[str, float] — archetype is
        # NOT carried as a string field on the trace. Schema-gap:
        # archetype lookup goes through the
        # _archetype_lookup_for_user hook which tests patch directly.
        user_posterior_snapshot={},
        posture_class="task_oriented",
        chain_of_reasoning=ChainOfReasoning(
            entries=[
                ChainOfReasoningEntry(
                    name="fomo_active", contribution=0.4, pct_of_total=60.0,
                ),
                ChainOfReasoningEntry(
                    name="psych_ownership", contribution=0.2, pct_of_total=40.0,
                ),
            ],
            total=0.6,
        ),
    )


def test_route_registered(client: TestClient):
    """Endpoint reachable; returns shape even on not_found."""
    with patch(
        "adam.api.dashboard.cell_aggregation_service._get_async_redis_client",
        new=AsyncMock(return_value=None),
    ), patch(
        "adam.api.dashboard.cell_aggregation_service._get_async_neo4j_driver",
        new=AsyncMock(return_value=None),
    ):
        response = client.get("/api/dashboard/ledger/decision-trace/missing_id")
    assert response.status_code == 200
    body = response.json()
    assert body["data_source_state"] == "not_found"
    assert body["impression_id"] == "missing_id"


def test_redis_hit_returns_found_state(client: TestClient):
    trace = _trace(decision_id="imp_123")
    with patch(
        "adam.api.dashboard.cell_aggregation_service._get_async_redis_client",
        new=AsyncMock(return_value="dummy_client"),
    ), patch(
        "adam.api.dashboard.cell_aggregation_service.load_trace",
        new=AsyncMock(return_value=trace),
    ):
        response = client.get("/api/dashboard/ledger/decision-trace/imp_123")
        body = response.json()
    assert body["data_source_state"] == "found"
    assert body["impression_id"] == "imp_123"


def test_neo4j_fallback_returns_partial_state(client: TestClient):
    """Redis miss + Neo4j hit → partial."""
    trace = _trace(decision_id="imp_456")
    with patch(
        "adam.api.dashboard.cell_aggregation_service._get_async_redis_client",
        new=AsyncMock(return_value="dummy_client"),
    ), patch(
        "adam.api.dashboard.cell_aggregation_service.load_trace",
        new=AsyncMock(return_value=None),
    ), patch(
        "adam.api.dashboard.cell_aggregation_service._get_async_neo4j_driver",
        new=AsyncMock(return_value="dummy_driver"),
    ), patch(
        "adam.api.dashboard.cell_aggregation_service.load_trace_from_neo4j",
        new=AsyncMock(return_value=trace),
    ):
        response = client.get("/api/dashboard/ledger/decision-trace/imp_456")
        body = response.json()
    assert body["data_source_state"] == "partial"


def test_buyer_id_anonymized(client: TestClient):
    """Privacy guard: raw user_id must NOT appear in response body."""
    trace = _trace(decision_id="imp_priv", user_id="buyer_secret_alpha")
    with patch(
        "adam.api.dashboard.cell_aggregation_service._get_async_redis_client",
        new=AsyncMock(return_value="dummy"),
    ), patch(
        "adam.api.dashboard.cell_aggregation_service.load_trace",
        new=AsyncMock(return_value=trace),
    ):
        response = client.get("/api/dashboard/ledger/decision-trace/imp_priv")
        body_text = response.text
        body = response.json()
    assert "buyer_secret_alpha" not in body_text
    assert body["buyer_id_anonymized"].startswith("buyer_")
    # Anonymized ID is not the raw input
    assert body["buyer_id_anonymized"] != "buyer_secret_alpha"


def test_predicates_fired_projected_from_chain(client: TestClient):
    trace = _trace(decision_id="imp_pred")
    with patch(
        "adam.api.dashboard.cell_aggregation_service._get_async_redis_client",
        new=AsyncMock(return_value="dummy"),
    ), patch(
        "adam.api.dashboard.cell_aggregation_service.load_trace",
        new=AsyncMock(return_value=trace),
    ):
        response = client.get("/api/dashboard/ledger/decision-trace/imp_pred")
        body = response.json()
    by_name = {p["predicate_name"]: p for p in body["predicates_fired"]}
    assert by_name["fomo_active"]["fired"] is True
    assert by_name["psych_ownership"]["fired"] is True
    assert by_name["maximizer_high"]["fired"] is False


def test_modulations_projected_from_alternatives(client: TestClient):
    trace = _trace(decision_id="imp_mod")
    with patch(
        "adam.api.dashboard.cell_aggregation_service._get_async_redis_client",
        new=AsyncMock(return_value="dummy"),
    ), patch(
        "adam.api.dashboard.cell_aggregation_service.load_trace",
        new=AsyncMock(return_value=trace),
    ):
        response = client.get("/api/dashboard/ledger/decision-trace/imp_mod")
        body = response.json()
    assert len(body["modulations_applied"]) == 1
    mod = body["modulations_applied"][0]
    assert mod["mechanism"] == "social_proof"
    assert abs(mod["score_before"] - 0.65) < 1e-6
    assert abs(mod["score_after"] - 0.84) < 1e-6


def test_archetype_lookup_hook_propagates(client: TestClient):
    """Archetype is fetched via _archetype_lookup_for_user hook; tests
    patch the hook to simulate Aura-cohort-population state."""
    trace = _trace(decision_id="imp_arch")
    with patch(
        "adam.api.dashboard.cell_aggregation_service._get_async_redis_client",
        new=AsyncMock(return_value="dummy"),
    ), patch(
        "adam.api.dashboard.cell_aggregation_service.load_trace",
        new=AsyncMock(return_value=trace),
    ), patch(
        "adam.api.dashboard.cell_aggregation_service._archetype_lookup_for_user",
        side_effect=lambda u: "achiever",
    ):
        response = client.get("/api/dashboard/ledger/decision-trace/imp_arch")
        body = response.json()
    assert body["archetype"] == "achiever"


def test_cluster_id_derived_from_creative(client: TestClient):
    trace = _trace(decision_id="imp_clus")
    with patch(
        "adam.api.dashboard.cell_aggregation_service._get_async_redis_client",
        new=AsyncMock(return_value="dummy"),
    ), patch(
        "adam.api.dashboard.cell_aggregation_service.load_trace",
        new=AsyncMock(return_value=trace),
    ):
        response = client.get("/api/dashboard/ledger/decision-trace/imp_clus")
        body = response.json()
    assert body["cluster_id"] == "ridelux_hero"
    assert body["chosen_creative_cluster"] == "ridelux_hero"


def test_posture_class_passed_through(client: TestClient):
    trace = _trace(decision_id="imp_post")
    with patch(
        "adam.api.dashboard.cell_aggregation_service._get_async_redis_client",
        new=AsyncMock(return_value="dummy"),
    ), patch(
        "adam.api.dashboard.cell_aggregation_service.load_trace",
        new=AsyncMock(return_value=trace),
    ):
        response = client.get("/api/dashboard/ledger/decision-trace/imp_post")
        body = response.json()
    assert body["posture_class"] == "task_oriented"


def test_unavailable_fields_marked_none(client: TestClient):
    """Schema-gap fields (cell_id, cohort_id, journey_stage, regulatory_focus,
    why_explanation) are None — Q.2.A documented limitation."""
    trace = _trace(decision_id="imp_gap")
    with patch(
        "adam.api.dashboard.cell_aggregation_service._get_async_redis_client",
        new=AsyncMock(return_value="dummy"),
    ), patch(
        "adam.api.dashboard.cell_aggregation_service.load_trace",
        new=AsyncMock(return_value=trace),
    ):
        response = client.get("/api/dashboard/ledger/decision-trace/imp_gap")
        body = response.json()
    assert body["cell_id"] is None
    assert body["cohort_id"] is None
    assert body["journey_stage"] is None
    assert body["regulatory_focus"] is None
    assert body["why_explanation"] is None
