"""Pin Slice 9 — FastAPI route for Defensive Reasoning renderer.

Audit Tier 1 #8: defensive_reasoning_renderer.py (392 lines, fully
tested) had ZERO callers outside tests; Spine #13's whole partner-
facing artifact was dark. This route is the FastAPI surface that
loads a DecisionTrace from Redis → Neo4j and renders the 5-layer view.

Tests pin:
    * Route registered at /api/dashboard/decision-trace/{decision_id}/render
    * 200 + structured 5-layer DefensiveReasoningRender on happy path
    * 404 when the trace is not found in either storage backend
    * 503 when BOTH Redis and Neo4j are unavailable
    * load_and_render is the canonical loader (source-text wire pin)
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from adam.api.dashboard.router import router
from adam.intelligence.decision_trace import DecisionTrace
from adam.intelligence.defensive_reasoning_renderer import (
    DefensiveReasoningRender,
)


# -----------------------------------------------------------------------------
# Source-text contract pins
# -----------------------------------------------------------------------------


def test_router_module_imports_load_and_render_in_route_scope():
    """Route function must import load_and_render at call time.

    Source-text pin — guards against silent removal of the wire (e.g.,
    a refactor that drops the import without realizing the route
    depends on it).
    """
    src = Path("adam/api/dashboard/router.py").read_text()
    assert "load_and_render" in src, (
        "Router lost reference to load_and_render. Slice 9 (DR route) "
        "is broken — Spine #13's partner-facing artifact is dark again."
    )
    assert "decision-trace/{decision_id}/render" in src, (
        "DR route URL changed — clients hard-coded against the old "
        "path will 404."
    )


# -----------------------------------------------------------------------------
# TestClient app
# -----------------------------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _fake_render() -> DefensiveReasoningRender:
    """Construct a minimal valid DefensiveReasoningRender for response tests.

    Schema (defensive_reasoning_renderer.py:156): one_liner is plain
    str, counterfactual is Optional[str], decomposition is a List of
    ChainOfReasoningEntry, confidence + provenance are nested objects.
    """
    from adam.intelligence.decision_trace import ChainOfReasoningEntry
    from adam.intelligence.defensive_reasoning_renderer import (
        ConfidenceLayer,
        ProvenanceLayer,
    )
    return DefensiveReasoningRender(
        decision_id="dec_test_42",
        one_liner=(
            "Served the curiosity creative because user is in "
            "POSTURE_BLEND posture."
        ),
        counterfactual=(
            "Would have served scarcity at gap 0.05 below the chosen "
            "mechanism."
        ),
        decomposition=[
            ChainOfReasoningEntry(
                name="trilateral_score",
                contribution=0.60,
                pct_of_total=60.0,
            ),
            ChainOfReasoningEntry(
                name="free_energy",
                contribution=-0.40,
                pct_of_total=40.0,
            ),
        ],
        confidence=ConfidenceLayer(status="not_available"),
        provenance=ProvenanceLayer(),
        one_liner_uses_metaphor_inventory=False,
    )


# -----------------------------------------------------------------------------
# Happy path
# -----------------------------------------------------------------------------


def test_route_returns_200_with_render(client: TestClient):
    """Trace found + renders cleanly → 200 with all 5 layers."""
    fake_render = _fake_render()
    fake_redis = MagicMock()
    fake_neo4j = MagicMock()

    with patch(
        "adam.core.dependencies.get_redis",
        new=AsyncMock(return_value=fake_redis),
    ), patch(
        "adam.core.dependencies.get_neo4j_driver",
        new=AsyncMock(return_value=fake_neo4j),
    ), patch(
        "adam.intelligence.defensive_reasoning_renderer.load_and_render",
        new=AsyncMock(return_value=fake_render),
    ):
        response = client.get("/api/dashboard/decision-trace/dec_test_42/render")

    assert response.status_code == 200
    body = response.json()
    assert body["decision_id"] == "dec_test_42"
    # 5 layers per directive lines 849-859
    assert "one_liner" in body
    assert "counterfactual" in body
    assert "decomposition" in body
    assert "confidence" in body
    assert "provenance" in body


def test_route_one_liner_carries_posture_and_mechanism(client: TestClient):
    """The plain-string one_liner surfaces posture + mechanism for the
    partner-facing 'why this impression' read."""
    fake_render = _fake_render()
    fake_redis = MagicMock()

    with patch(
        "adam.core.dependencies.get_redis",
        new=AsyncMock(return_value=fake_redis),
    ), patch(
        "adam.core.dependencies.get_neo4j_driver",
        new=AsyncMock(return_value=None),
    ), patch(
        "adam.intelligence.defensive_reasoning_renderer.load_and_render",
        new=AsyncMock(return_value=fake_render),
    ):
        response = client.get("/api/dashboard/decision-trace/dec_test_42/render")

    body = response.json()
    # one_liner is a plain string in the schema
    assert isinstance(body["one_liner"], str)
    assert "POSTURE_BLEND" in body["one_liner"]
    assert "curiosity" in body["one_liner"]


# -----------------------------------------------------------------------------
# 404 — trace not found
# -----------------------------------------------------------------------------


def test_route_returns_404_when_trace_not_found(client: TestClient):
    """load_and_render returns None → route returns 404."""
    fake_redis = MagicMock()

    with patch(
        "adam.core.dependencies.get_redis",
        new=AsyncMock(return_value=fake_redis),
    ), patch(
        "adam.core.dependencies.get_neo4j_driver",
        new=AsyncMock(return_value=None),
    ), patch(
        "adam.intelligence.defensive_reasoning_renderer.load_and_render",
        new=AsyncMock(return_value=None),
    ):
        response = client.get(
            "/api/dashboard/decision-trace/dec_does_not_exist/render"
        )

    assert response.status_code == 404
    body = response.json()
    assert "dec_does_not_exist" in body["detail"]
    assert "not found" in body["detail"].lower()


# -----------------------------------------------------------------------------
# 503 — both backends unavailable
# -----------------------------------------------------------------------------


def test_route_returns_503_when_both_backends_unavailable(client: TestClient):
    """Both Redis and Neo4j unreachable → 503 with structured detail."""
    with patch(
        "adam.core.dependencies.get_redis",
        new=AsyncMock(side_effect=RuntimeError("redis down")),
    ), patch(
        "adam.core.dependencies.get_neo4j_driver",
        new=AsyncMock(side_effect=RuntimeError("neo4j down")),
    ):
        response = client.get(
            "/api/dashboard/decision-trace/dec_anything/render"
        )

    assert response.status_code == 503
    body = response.json()
    assert "unavailable" in body["detail"].lower()


# -----------------------------------------------------------------------------
# Storage fallback semantics
# -----------------------------------------------------------------------------


def test_route_succeeds_with_redis_only(client: TestClient):
    """Neo4j unavailable but Redis works → still serves render."""
    fake_render = _fake_render()
    fake_redis = MagicMock()

    with patch(
        "adam.core.dependencies.get_redis",
        new=AsyncMock(return_value=fake_redis),
    ), patch(
        "adam.core.dependencies.get_neo4j_driver",
        new=AsyncMock(side_effect=RuntimeError("neo4j down")),
    ), patch(
        "adam.intelligence.defensive_reasoning_renderer.load_and_render",
        new=AsyncMock(return_value=fake_render),
    ):
        response = client.get("/api/dashboard/decision-trace/dec_x/render")

    assert response.status_code == 200


def test_route_succeeds_with_neo4j_only(client: TestClient):
    """Redis unavailable but Neo4j works → still serves render (warm path)."""
    fake_render = _fake_render()
    fake_neo4j = MagicMock()

    with patch(
        "adam.core.dependencies.get_redis",
        new=AsyncMock(side_effect=RuntimeError("redis down")),
    ), patch(
        "adam.core.dependencies.get_neo4j_driver",
        new=AsyncMock(return_value=fake_neo4j),
    ), patch(
        "adam.intelligence.defensive_reasoning_renderer.load_and_render",
        new=AsyncMock(return_value=fake_render),
    ):
        response = client.get("/api/dashboard/decision-trace/dec_y/render")

    assert response.status_code == 200
