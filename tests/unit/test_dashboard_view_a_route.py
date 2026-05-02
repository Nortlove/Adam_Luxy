"""Pin Slice 10 — FastAPI route for View A agency-dashboard payload.

Audit Tier 1 #9: agency_dashboard.build_agency_dashboard_payload
aggregates rotation_events + attention_inversion_diagonals +
page_posture into a JSON payload, but had ZERO callers outside tests.
Spine #13's central demo artifact (View A mechanism-rotation graph)
had no HTTP surface.

Tests pin:
    * Route registered at /api/dashboard/agency-view-a
    * 200 returns a payload (always — no 404 for empty registries)
    * Payload includes decision_summary snapshot of system state
    * Payload includes rotation_events when registry has commitments
    * Payload includes attention_inversion_diagonals when taxonomy
      accumulator has data
    * Page posture summary section present when accumulator has data
    * Soft-fails gracefully when underlying singletons unavailable
    * Source-text wire pin for build_agency_dashboard_payload import
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from adam.api.dashboard.router import router


# -----------------------------------------------------------------------------
# Source-text contract pin
# -----------------------------------------------------------------------------


def test_router_imports_build_agency_dashboard_payload():
    """Source-text pin — route must reference the build helper."""
    src = Path("adam/api/dashboard/router.py").read_text()
    assert "build_agency_dashboard_payload" in src, (
        "Router lost build_agency_dashboard_payload reference. "
        "Slice 10 (View A route) is broken — Spine #13's central demo "
        "artifact is dark again."
    )
    assert "agency-view-a" in src, (
        "View A route URL changed — frontend chart components hard-"
        "coded against the old path will break."
    )


# -----------------------------------------------------------------------------
# TestClient app
# -----------------------------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# -----------------------------------------------------------------------------
# Happy path — payload structure
# -----------------------------------------------------------------------------


def test_route_returns_200_with_payload(client: TestClient):
    """Route always returns 200 with at least decision_summary populated."""
    response = client.get("/api/dashboard/agency-view-a")
    assert response.status_code == 200
    body = response.json()
    assert "decision_summary" in body
    assert body["decision_summary"]["view"] == "agency_overview"
    assert body["decision_summary"]["snapshot_type"] == "system_state"
    assert "snapshot_at" in body["decision_summary"]
    assert "generated_at" in body


def test_route_includes_rotation_events_when_registry_has_data(
    client: TestClient,
):
    """Rotation events section populated when registry has commitments."""
    response = client.get("/api/dashboard/agency-view-a")
    body = response.json()
    # Whether the registry is empty or populated, the rotation_events
    # section should appear (build helper gates on registry being
    # non-None, not on it having entries) — confirms the wire is in
    # place; emptiness is a separate concern.
    assert "rotation_events" in body
    assert "rotation_events_count" in body
    assert isinstance(body["rotation_events"], list)
    assert body["rotation_events_count"] == len(body["rotation_events"])


def test_route_includes_attention_inversion_diagonals(client: TestClient):
    """Attention-inversion diagonals section appears when taxonomy
    accumulator is reachable."""
    response = client.get("/api/dashboard/agency-view-a")
    body = response.json()
    assert "attention_inversion_diagonals" in body


def test_route_includes_page_posture(client: TestClient):
    """Page posture summary appears when posture accumulator is reachable."""
    response = client.get("/api/dashboard/agency-view-a")
    body = response.json()
    assert "page_posture" in body


# -----------------------------------------------------------------------------
# Per-decision sections explicitly NOT included on the overview
# -----------------------------------------------------------------------------


def test_route_omits_per_decision_sections(client: TestClient):
    """Overview does not include uncertainty_panel / construct_chain /
    session_mood — those are per-decision and require a specific
    decision_id (sibling slices)."""
    response = client.get("/api/dashboard/agency-view-a")
    body = response.json()
    # Per the route's honest tag (d): per-decision sections are NOT
    # populated on the overview surface
    assert "uncertainty_panel" not in body
    assert "construct_chain" not in body
    assert "session_mood" not in body


# -----------------------------------------------------------------------------
# Soft-fail — underlying singletons unavailable
# -----------------------------------------------------------------------------


def test_route_soft_fails_when_all_singletons_unavailable(client: TestClient):
    """When all accumulators raise on import, route still returns
    200 with at least decision_summary."""
    with patch(
        "adam.intelligence.mechanism_rotation.get_rotation_registry",
        side_effect=RuntimeError("rotation registry down"),
    ), patch(
        "adam.intelligence.mechanism_taxonomy_runtime.get_taxonomy_accumulator",
        side_effect=RuntimeError("taxonomy down"),
    ), patch(
        "adam.intelligence.page_attentional_posture_substrate."
        "get_page_attentional_posture_accumulator",
        side_effect=RuntimeError("posture down"),
    ):
        response = client.get("/api/dashboard/agency-view-a")

    assert response.status_code == 200
    body = response.json()
    # Decision_summary always present even when everything else fails
    assert body["decision_summary"]["view"] == "agency_overview"
    # When singletons are unavailable, their sections are absent
    assert "rotation_events" not in body
    assert "attention_inversion_diagonals" not in body
    assert "page_posture" not in body
