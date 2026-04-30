"""Pin Spine #11 — LUXY negative-outcome adapter end-to-end.

Directive Phase 1 deliverable. Three layers pinned:
  1. LuxyRideAdapter normalizes the LUXY booking-system payload.
  2. The default registry routes a LUXY-shaped payload to LuxyRideAdapter
     (not GenericJSONAdapter or any other catch-all).
  3. The webhook router POSTs the payload through the registry into
     OutcomeHandler.process_outcome with the right outcome_type +
     decision_id.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from adam.api.negative_outcomes.router import router as negative_outcomes_router
from adam.intelligence.negative_outcome_adapters import (
    GenericJSONAdapter,
    LuxyRideAdapter,
    NegativeOutcomeAdapterRegistry,
    NormalizedNegativeOutcome,
    StripeRefundAdapter,
    get_default_registry,
    reset_default_registry,
)


# -----------------------------------------------------------------------------
# Layer 1 — LuxyRideAdapter unit tests
# -----------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_registry():
    """Each test gets a fresh default registry — adapter ordering
    decisions in earlier tests must not bleed into later tests."""
    reset_default_registry()
    yield
    reset_default_registry()


def _luxy_payload(event_type: str = "ride_cancelled", decision_id: str = "dec_abc") -> dict:
    return {
        "event_type": event_type,
        "occurred_at": "2026-04-30T18:00:00Z",
        "booking": {
            "id": "bk_123",
            "decision_id": decision_id,
            "rider_id": "rider_456",
            "fare_cents": 5000,
        },
    }


def test_luxy_adapter_normalizes_ride_cancelled():
    """ride_cancelled → regret_signal (post-booking pre-pickup regret)."""
    adapter = LuxyRideAdapter()
    result = adapter.normalize(_luxy_payload("ride_cancelled"))
    assert result is not None
    assert result.decision_id == "dec_abc"
    assert result.outcome_type == "regret_signal"
    assert result.outcome_value == 0.0
    assert result.metadata["source_adapter"] == "luxy_ride"
    assert result.metadata["luxy_event_type"] == "ride_cancelled"
    assert result.metadata["luxy_booking_id"] == "bk_123"
    assert result.metadata["luxy_rider_id"] == "rider_456"
    assert result.metadata["luxy_fare_cents"] == 5000


def test_luxy_adapter_normalizes_ride_no_show():
    """ride_no_show → regret_signal (decided not to show)."""
    result = LuxyRideAdapter().normalize(_luxy_payload("ride_no_show"))
    assert result is not None
    assert result.outcome_type == "regret_signal"


def test_luxy_adapter_normalizes_ride_refunded():
    """ride_refunded → canonical refund."""
    result = LuxyRideAdapter().normalize(_luxy_payload("ride_refunded"))
    assert result is not None
    assert result.outcome_type == "refund"


def test_luxy_adapter_normalizes_ride_complaint():
    """ride_complaint → canonical complaint."""
    result = LuxyRideAdapter().normalize(_luxy_payload("ride_complaint"))
    assert result is not None
    assert result.outcome_type == "complaint"


def test_luxy_adapter_normalizes_chargeback():
    """chargeback → refund (forced reversal)."""
    result = LuxyRideAdapter().normalize(_luxy_payload("chargeback"))
    assert result is not None
    assert result.outcome_type == "refund"


def test_luxy_adapter_returns_none_for_unknown_event_type():
    """Unknown event_type → None (registry dispatches to next adapter)."""
    payload = _luxy_payload()
    payload["event_type"] = "ride_completed_successfully"
    assert LuxyRideAdapter().normalize(payload) is None


def test_luxy_adapter_returns_none_when_decision_id_missing():
    """No decision_id → can't bind outcome to a decision → return None.

    The Phase 8 sapid round-trip monitor counts this as an unresolved
    event (registry.dispatch's side-effect)."""
    payload = _luxy_payload()
    del payload["booking"]["decision_id"]
    assert LuxyRideAdapter().normalize(payload) is None


def test_luxy_adapter_returns_none_when_booking_missing():
    """No booking object → invalid LUXY shape → None."""
    payload = {"event_type": "ride_cancelled"}
    assert LuxyRideAdapter().normalize(payload) is None


def test_luxy_adapter_returns_none_for_non_dict():
    """Defensive — list / string / None payloads return None."""
    assert LuxyRideAdapter().normalize([]) is None
    assert LuxyRideAdapter().normalize("not a dict") is None
    assert LuxyRideAdapter().normalize(None) is None


# -----------------------------------------------------------------------------
# Layer 2 — Default registry routes LUXY shape to LuxyRideAdapter
# -----------------------------------------------------------------------------


def test_default_registry_includes_luxy_first():
    """LuxyRideAdapter must be registered AND in front of GenericJSON
    so LUXY shapes don't fall through to a less-specific adapter."""
    registry = get_default_registry()
    types = [a.__class__.__name__ for a in registry._adapters]
    assert "LuxyRideAdapter" in types
    assert types.index("LuxyRideAdapter") < types.index("GenericJSONAdapter")


def test_default_registry_dispatch_routes_luxy_payload():
    """A LUXY payload through the production registry yields a
    LuxyRideAdapter normalized result (verified via source_adapter)."""
    registry = get_default_registry()
    result = registry.dispatch(_luxy_payload("ride_complaint"))
    assert result is not None
    assert result.metadata["source_adapter"] == "luxy_ride"
    assert result.outcome_type == "complaint"


def test_default_registry_dispatch_unknown_payload_returns_none():
    """A payload that no adapter recognizes returns None — the Phase 8
    monitor records this as a failed resolution."""
    registry = get_default_registry()
    result = registry.dispatch({"random": "shape", "no_known_keys": True})
    assert result is None


# -----------------------------------------------------------------------------
# Layer 3 — Webhook router end-to-end
# -----------------------------------------------------------------------------


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(negative_outcomes_router)
    return app


def test_webhook_dispatches_luxy_payload_to_outcome_handler():
    """End-to-end: POST → registry.dispatch → OutcomeHandler.process_outcome
    with normalized fields."""
    app = _build_test_app()

    mock_handler = MagicMock()
    mock_handler.process_outcome = AsyncMock(return_value={"updates": {}})

    with patch(
        "adam.api.negative_outcomes.router._get_outcome_handler",
        return_value=mock_handler,
    ):
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/negative-outcomes/event",
                json=_luxy_payload("ride_cancelled", decision_id="dec_xyz"),
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "processed"
    assert body["decision_id"] == "dec_xyz"
    assert body["outcome_type"] == "regret_signal"
    assert body["source_adapter"] == "luxy_ride"

    # And the OutcomeHandler was actually called with the normalized fields
    mock_handler.process_outcome.assert_called_once()
    call_kwargs = mock_handler.process_outcome.call_args.kwargs
    assert call_kwargs["decision_id"] == "dec_xyz"
    assert call_kwargs["outcome_type"] == "regret_signal"
    assert call_kwargs["outcome_value"] == 0.0
    # Metadata carries LUXY-source attribution all the way through
    assert call_kwargs["metadata"]["source_adapter"] == "luxy_ride"
    assert call_kwargs["metadata"]["luxy_event_type"] == "ride_cancelled"


def test_webhook_returns_422_for_unrecognized_payload():
    """Unrecognized shape (no adapter matches) → 422 with diagnostics."""
    app = _build_test_app()
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/negative-outcomes/event",
            json={"random_key": "no_adapter_recognizes_this"},
        )
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["status"] == "unrecognized"
    assert "payload_keys" in detail


def test_webhook_returns_400_for_non_dict_body():
    """Body must be a JSON object."""
    app = _build_test_app()
    with TestClient(app) as client:
        resp = client.post(
            "/api/v1/negative-outcomes/event",
            json=["not", "a", "dict"],
        )
    assert resp.status_code == 400


def test_webhook_soft_fails_when_outcome_handler_raises():
    """OutcomeHandler raising must NOT 500 the upstream caller —
    return 200 with status='degraded' so LUXY's webhook delivery
    succeeds while we degrade gracefully internally."""
    app = _build_test_app()

    mock_handler = MagicMock()
    mock_handler.process_outcome = AsyncMock(
        side_effect=RuntimeError("internal pipeline broken"),
    )

    with patch(
        "adam.api.negative_outcomes.router._get_outcome_handler",
        return_value=mock_handler,
    ):
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/negative-outcomes/event",
                json=_luxy_payload("ride_refunded", decision_id="dec_qwe"),
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["decision_id"] == "dec_qwe"
    assert "internal pipeline broken" in body["reason"]


def test_webhook_returns_degraded_when_handler_unavailable():
    """If OutcomeHandler can't be imported, normalized event still
    reported but flagged as degraded — payload was VALID, the
    learning pipeline is what's down."""
    app = _build_test_app()

    with patch(
        "adam.api.negative_outcomes.router._get_outcome_handler",
        return_value=None,
    ):
        with TestClient(app) as client:
            resp = client.post(
                "/api/v1/negative-outcomes/event",
                json=_luxy_payload("ride_complaint"),
            )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["outcome_type"] == "complaint"


def test_webhook_lists_adapters_in_dispatch_order():
    """GET /adapters surfaces the dispatch ordering — ops needs
    visibility that LuxyRideAdapter is in front of GenericJSON."""
    app = _build_test_app()
    with TestClient(app) as client:
        resp = client.get("/api/v1/negative-outcomes/adapters")
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] >= 4
    assert "luxy_ride" in body["dispatch_order"]
    assert (
        body["dispatch_order"].index("luxy_ride")
        < body["dispatch_order"].index("generic_json")
    )
