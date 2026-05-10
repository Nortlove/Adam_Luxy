"""Q.2.A — endpoint correctness tests for /learning/loop-dispatch-rates."""

from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from adam.api.dashboard.cell_aggregation_service import DISPATCH_METHOD_NAMES
from adam.api.dashboard.router import router
from adam.core.learning.outcome_handler import OutcomeHandler


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_route_registered(client: TestClient):
    response = client.get("/api/dashboard/learning/loop-dispatch-rates")
    assert response.status_code == 200
    body = response.json()
    assert "dispatch_methods" in body
    assert "data_source_state" in body


def test_14_methods_enumerated(client: TestClient):
    response = client.get("/api/dashboard/learning/loop-dispatch-rates")
    body = response.json()
    method_names = {m["method_name"] for m in body["dispatch_methods"]}
    assert len(DISPATCH_METHOD_NAMES) == 14
    for name in DISPATCH_METHOD_NAMES:
        assert name in method_names


def test_dormant_state_when_no_dispatches(client: TestClient):
    """Fresh OutcomeHandler with no dispatches → all dormant."""
    # Reset singleton to a fresh handler
    import adam.core.learning.outcome_handler as oh
    oh._outcome_handler = OutcomeHandler()
    response = client.get("/api/dashboard/learning/loop-dispatch-rates")
    body = response.json()
    for method in body["dispatch_methods"]:
        assert method["dormant"] is True
        assert method["dispatch_count"] == 0
        assert method["last_dispatch_at"] is None


def test_counter_increment_via_record_dispatch(client: TestClient):
    """Calling _record_dispatch directly increments the counter."""
    import adam.core.learning.outcome_handler as oh
    fresh = OutcomeHandler()
    fresh._record_dispatch("_update_thompson")
    fresh._record_dispatch("_update_thompson")
    fresh._record_dispatch("_update_meta_orchestrator")
    oh._outcome_handler = fresh

    response = client.get("/api/dashboard/learning/loop-dispatch-rates")
    body = response.json()
    by_name = {m["method_name"]: m for m in body["dispatch_methods"]}
    assert by_name["_update_thompson"]["dispatch_count"] == 2
    assert by_name["_update_thompson"]["dormant"] is False
    assert by_name["_update_thompson"]["last_dispatch_at"] is not None
    assert by_name["_update_meta_orchestrator"]["dispatch_count"] == 1
    # All other methods remain dormant
    for name in DISPATCH_METHOD_NAMES:
        if name not in ("_update_thompson", "_update_meta_orchestrator"):
            assert by_name[name]["dispatch_count"] == 0


def test_data_source_state_partial_when_dispatches_but_no_outcomes(
    client: TestClient,
):
    """Counter incremented but outcomes_processed still 0 → partial."""
    import adam.core.learning.outcome_handler as oh
    fresh = OutcomeHandler()
    fresh._record_dispatch("_update_thompson")
    oh._outcome_handler = fresh
    response = client.get("/api/dashboard/learning/loop-dispatch-rates")
    body = response.json()
    assert body["data_source_state"] == "partial"


def test_outcome_handler_stats_extension():
    """Direct unit test of OutcomeHandler.stats — Q.2.A extension."""
    handler = OutcomeHandler()
    handler._record_dispatch("_update_neo4j_attribution")
    stats = handler.stats
    assert "dispatch_counts" in stats
    assert "dispatch_last_at" in stats
    assert stats["dispatch_counts"]["_update_neo4j_attribution"] == 1
    assert "_update_neo4j_attribution" in stats["dispatch_last_at"]
