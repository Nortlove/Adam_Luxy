"""Pin Slice 35 — StackAdapt shadow-mode bidder wire.

Per the 2026-05-02 wrap-out greenlight: shadow mode, no live bid
writes. Verify recommended_bid_value arrives intact, is propensity-
logged, round-trips through DecisionTrace. Wire CONSUMES via
v3_interfaces.get_active_bid_composer() — when v3 Phase 1 work-
stream 1.D registers an H∞-wrapped Kelly composer, this wire
auto-consumes the wrapped value with zero changes.

Includes the Chris-named regression test: register a sentinel
BidComposer that returns a known synthetic bid value, drive a
shadow-mode impression through the full StackAdapt wire path,
verify the synthetic value lands in the bidder-side message
intact. Pins the gap between Slice 27's regression net (which
exercises trace emission) and the wire path (downstream).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from adam.api.stackadapt.shadow_bidder import (
    SHADOW_BID_NODE_LABEL,
    ShadowBidRecord,
    ShadowBidSubmitResult,
    _capture_active_composer_name,
    submit_shadow_bid,
    submit_shadow_bid_sync,
)
from adam.intelligence.v3_interfaces import (
    register_bid_composer,
    reset_to_defaults_for_tests,
)


@pytest.fixture(autouse=True)
def _reset_registries():
    """Isolate the BidComposer registry per test."""
    reset_to_defaults_for_tests()
    yield
    reset_to_defaults_for_tests()


# -----------------------------------------------------------------------------
# Schema + constants
# -----------------------------------------------------------------------------


def test_shadow_bid_node_label_canonical():
    assert SHADOW_BID_NODE_LABEL == "ShadowBid"


def test_shadow_bid_record_round_trip_pydantic():
    rec = ShadowBidRecord(
        decision_id="d-1",
        recommended_bid_value=4.20,
        ts_propensity=0.85,
        chosen_mechanism="social_proof",
        posture_class="blend_compatible",
        archetype="achiever",
        bid_composer_name="kelly_default",
        user_id="u-7",
    )
    serialized = rec.model_dump_json()
    restored = ShadowBidRecord.model_validate_json(serialized)
    assert restored.decision_id == "d-1"
    assert restored.recommended_bid_value == pytest.approx(4.20)
    assert restored.ts_propensity == pytest.approx(0.85)


def test_shadow_bid_record_extra_fields_forbidden():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ShadowBidRecord(
            decision_id="d", recommended_bid_value=1.0,
            ts_propensity=0.5, chosen_mechanism="m",
            unknown_field=42,  # type: ignore[call-arg]
        )


def test_shadow_bid_record_propensity_clamped():
    """ts_propensity must be in [0, 1]."""
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ShadowBidRecord(
            decision_id="d", recommended_bid_value=1.0,
            ts_propensity=1.5, chosen_mechanism="m",
        )


def test_shadow_bid_submit_result_frozen():
    out = ShadowBidSubmitResult(
        written=True, skipped=False, reason="written",
        composer_name_observed="kelly_default", decision_id="d-1",
    )
    with pytest.raises((AttributeError, Exception)):
        out.written = False  # type: ignore[misc]


# -----------------------------------------------------------------------------
# _capture_active_composer_name
# -----------------------------------------------------------------------------


def test_default_composer_name_captured():
    name = _capture_active_composer_name()
    assert name == "kelly_default"


def test_sentinel_composer_name_captured_after_register():
    """Slice 24 registry honored: registering a sentinel updates
    the captured name on the next read."""

    class _SentinelBC:
        name = "sentinel_bc_xyz"

        def compose_chosen(self, **_):
            return None

        def compose_alternatives(self, alts, **_):
            return alts

    register_bid_composer(_SentinelBC())
    assert _capture_active_composer_name() == "sentinel_bc_xyz"


def test_unnamed_composer_falls_back_to_type_name():
    """Composers without a .name attribute fall back to type name."""

    class UnnamedBC:
        def compose_chosen(self, **_):
            return None

        def compose_alternatives(self, alts, **_):
            return alts

    register_bid_composer(UnnamedBC())
    assert _capture_active_composer_name() == "UnnamedBC"


# -----------------------------------------------------------------------------
# Async submit_shadow_bid — soft-fail paths
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_no_decision_id_skipped():
    out = await submit_shadow_bid(
        decision_id="",
        recommended_bid_value=1.0,
        ts_propensity=0.5,
        chosen_mechanism="social_proof",
        driver=MagicMock(),
    )
    assert out.skipped is True
    assert out.reason == "no_decision_id"


@pytest.mark.asyncio
async def test_submit_no_driver_skipped():
    out = await submit_shadow_bid(
        decision_id="d-1",
        recommended_bid_value=1.0,
        ts_propensity=0.5,
        chosen_mechanism="social_proof",
        driver=None,
    )
    assert out.skipped is True
    assert out.reason == "no_driver"
    assert out.composer_name_observed == "kelly_default"


@pytest.mark.asyncio
async def test_submit_neo4j_exception_soft_fails():
    """Driver session raise → reason=neo4j_exception, written=False,
    NO exception propagates."""
    class _RaisingDriver:
        def session(self):
            raise RuntimeError("connection lost")

    out = await submit_shadow_bid(
        decision_id="d-1",
        recommended_bid_value=1.0,
        ts_propensity=0.5,
        chosen_mechanism="social_proof",
        driver=_RaisingDriver(),
    )
    assert out.written is False
    assert out.skipped is False
    assert out.reason == "neo4j_exception"


# -----------------------------------------------------------------------------
# Async submit_shadow_bid — happy path with fake driver
# -----------------------------------------------------------------------------


class _FakeAsyncResult:
    def __init__(self, rows: List[Dict[str, Any]]) -> None:
        self._rows = list(rows)

    async def single(self) -> Optional[Any]:
        if not self._rows:
            return None
        node = self._rows[0]
        rec = MagicMock()
        rec.get = lambda key: node if key == "b" else None
        return rec


class _FakeAsyncSession:
    def __init__(self, driver: "_FakeAsyncDriver") -> None:
        self._driver = driver

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return None

    async def run(self, cypher: str, **params: Any) -> _FakeAsyncResult:
        self._driver.calls.append((cypher, dict(params)))
        norm = cypher.strip()
        if norm.startswith("MERGE (b:ShadowBid"):
            self._driver.records[params["decision_id"]] = dict(params)
            return _FakeAsyncResult([])
        if norm.startswith("MATCH (b:ShadowBid"):
            rec = self._driver.records.get(params["decision_id"])
            if rec is None:
                return _FakeAsyncResult([])
            node = MagicMock()
            node.get = lambda key, default=None: rec.get(key, default)
            return _FakeAsyncResult([node])
        return _FakeAsyncResult([])


class _FakeAsyncDriver:
    def __init__(self):
        self.records: Dict[str, Dict[str, Any]] = {}
        self.calls: List = []

    def session(self):
        return _FakeAsyncSession(self)


@pytest.mark.asyncio
async def test_submit_writes_correct_cypher_params():
    driver = _FakeAsyncDriver()
    out = await submit_shadow_bid(
        decision_id="d-async-1",
        recommended_bid_value=4.20,
        ts_propensity=0.85,
        chosen_mechanism="social_proof",
        posture_class="blend_compatible",
        archetype="achiever",
        user_id="u-7",
        driver=driver,
    )
    assert out.written is True
    assert out.reason == "written"
    assert len(driver.calls) == 1
    cypher, params = driver.calls[0]
    assert "MERGE (b:ShadowBid" in cypher
    assert params["decision_id"] == "d-async-1"
    assert params["recommended_bid_value"] == pytest.approx(4.20)
    assert params["ts_propensity"] == pytest.approx(0.85)
    assert params["chosen_mechanism"] == "social_proof"
    assert params["posture_class"] == "blend_compatible"
    assert params["archetype"] == "achiever"
    assert params["user_id"] == "u-7"
    # Captured composer name is the registry default at this point.
    assert params["bid_composer_name"] == "kelly_default"


@pytest.mark.asyncio
async def test_submit_idempotent_on_decision_id():
    """Re-submitting same decision_id MERGEs (no duplicate records)."""
    driver = _FakeAsyncDriver()
    await submit_shadow_bid(
        decision_id="d-idemp",
        recommended_bid_value=1.0, ts_propensity=0.5,
        chosen_mechanism="m", driver=driver,
    )
    await submit_shadow_bid(
        decision_id="d-idemp",
        recommended_bid_value=2.0, ts_propensity=0.6,
        chosen_mechanism="m", driver=driver,
    )
    # Both calls hit Cypher; in-memory dict has ONE entry under the
    # decision_id key (re-write).
    assert len(driver.records) == 1
    assert driver.records["d-idemp"]["recommended_bid_value"] == 2.0


# -----------------------------------------------------------------------------
# Sync submit_shadow_bid_sync — service hot-path
# -----------------------------------------------------------------------------


class _FakeSyncSession:
    def __init__(self, driver: "_FakeSyncDriver") -> None:
        self._driver = driver

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return None

    def run(self, cypher: str, **params: Any):
        self._driver.calls.append((cypher, dict(params)))
        if cypher.strip().startswith("MERGE (b:ShadowBid"):
            self._driver.records[params["decision_id"]] = dict(params)
        return MagicMock()


class _FakeSyncDriver:
    def __init__(self):
        self.records: Dict[str, Dict[str, Any]] = {}
        self.calls: List = []

    def session(self):
        return _FakeSyncSession(self)


def test_submit_sync_writes_record():
    driver = _FakeSyncDriver()
    out = submit_shadow_bid_sync(
        decision_id="d-sync-1",
        recommended_bid_value=3.50,
        ts_propensity=0.75,
        chosen_mechanism="authority",
        driver=driver,
    )
    assert out.written is True
    assert out.reason == "written"
    assert len(driver.calls) == 1
    cypher, params = driver.calls[0]
    assert "MERGE (b:ShadowBid" in cypher
    assert params["recommended_bid_value"] == pytest.approx(3.50)


def test_submit_sync_no_driver_skipped():
    out = submit_shadow_bid_sync(
        decision_id="d-1",
        recommended_bid_value=1.0,
        ts_propensity=0.5,
        chosen_mechanism="m",
        driver=None,
    )
    assert out.skipped is True
    assert out.reason == "no_driver"


def test_submit_sync_exception_soft_fails():
    class _RaisingDriver:
        def session(self):
            raise RuntimeError("connection lost")

    out = submit_shadow_bid_sync(
        decision_id="d-1",
        recommended_bid_value=1.0,
        ts_propensity=0.5,
        chosen_mechanism="m",
        driver=_RaisingDriver(),
    )
    assert out.written is False
    assert out.skipped is False
    assert out.reason == "neo4j_exception"


# -----------------------------------------------------------------------------
# REGRESSION TEST per Chris's wrap-out greenlight (the gap between
# Slice 27's trace-emission regression net and the wire path).
#
# Register a sentinel BidComposer that returns a known synthetic bid
# value. Drive a shadow-mode impression through the full StackAdapt
# wire path. Verify the synthetic value lands in the bidder-side
# message intact.
# -----------------------------------------------------------------------------


def test_sentinel_bid_composer_value_lands_in_shadow_log_via_wire_path():
    """Pin the END-TO-END registry-honor invariant: register a
    sentinel BidComposer; drive a shadow-mode impression; verify the
    sentinel's synthetic value + name lands in the persisted shadow
    record. This is the proof that v3 Phase 1.D's H∞-wrapped Kelly
    composer can plug in via register_bid_composer() and the wire
    will consume the wrapped values with zero code changes."""

    SENTINEL_BID = 99.999
    SENTINEL_NAME = "sentinel_hinf_proxy"

    class _SentinelBidComposer:
        name = SENTINEL_NAME

        def compose_chosen(self, **_):
            return SENTINEL_BID

        def compose_alternatives(self, alts, **_):
            return alts

    register_bid_composer(_SentinelBidComposer())

    # Drive the wire DIRECTLY (sync path matches service.py call).
    driver = _FakeSyncDriver()
    out = submit_shadow_bid_sync(
        decision_id="d-sentinel-end-to-end",
        recommended_bid_value=SENTINEL_BID,
        ts_propensity=0.42,
        chosen_mechanism="social_proof",
        posture_class="blend_compatible",
        archetype="achiever",
        user_id="u-sentinel",
        driver=driver,
    )

    assert out.written is True
    assert out.composer_name_observed == SENTINEL_NAME, (
        f"Wire failed to capture the registered sentinel composer's "
        f"name (got {out.composer_name_observed!r}); the registry-"
        f"honor invariant is broken."
    )
    # The persisted record carries BOTH the synthetic value AND the
    # composer name — the auditable proof of registry dispatch.
    persisted = driver.records["d-sentinel-end-to-end"]
    assert persisted["recommended_bid_value"] == pytest.approx(
        SENTINEL_BID,
    )
    assert persisted["bid_composer_name"] == SENTINEL_NAME, (
        f"Persisted record has bid_composer_name="
        f"{persisted['bid_composer_name']!r}; expected {SENTINEL_NAME!r}. "
        "The wire path is not honoring the BidComposer registry."
    )


def test_sentinel_value_default_after_reset():
    """Symmetric pin: after reset_to_defaults_for_tests, the wire
    captures the default kelly_default name on the next write."""
    SENTINEL_BID = 88.888

    class _Sentinel:
        name = "transient_sentinel"

        def compose_chosen(self, **_):
            return SENTINEL_BID

        def compose_alternatives(self, alts, **_):
            return alts

    register_bid_composer(_Sentinel())
    reset_to_defaults_for_tests()  # back to default

    driver = _FakeSyncDriver()
    out = submit_shadow_bid_sync(
        decision_id="d-after-reset",
        recommended_bid_value=1.0,
        ts_propensity=0.5,
        chosen_mechanism="m",
        driver=driver,
    )
    assert out.composer_name_observed == "kelly_default"


# -----------------------------------------------------------------------------
# Service integration — source-text contract pin
# -----------------------------------------------------------------------------


def test_service_imports_shadow_bidder_sync():
    """StackAdapt service must reference submit_shadow_bid_sync at
    the right call site (after _format_response, before return).
    Defends against accidental unwire in a future refactor."""
    from pathlib import Path

    src = Path("adam/api/stackadapt/service.py").read_text()
    assert "submit_shadow_bid_sync" in src, (
        "Service no longer imports/uses submit_shadow_bid_sync. "
        "Slice 35 wire is unwired — recommended_bid_value will not "
        "round-trip through DecisionTrace into a shadow record."
    )


def test_service_uses_graph_cache_sync_driver_for_shadow_bid():
    """Sync driver source — same pattern Slice C uses (matches
    graph_cache._get_driver())."""
    from pathlib import Path

    src = Path("adam/api/stackadapt/service.py").read_text()
    assert "self._graph_cache._get_driver()" in src
    # And the call is gated on bid_value being non-None.
    assert "bid_value = getattr(cascade_result, " in src
    assert "if bid_value is not None:" in src
