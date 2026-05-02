"""Pin Slice 14 — Creative upload pipeline.

Discipline anchors (B3-LUXY a/b/c/d):

    (a) Citations: directive Phase 8 line 1099 (creative upload with
        metadata); Section 6.4 line 1066 (mechanism + metaphor +
        posture metadata in description blob); Slice 13 (graphql
        mutations 9c369f8); Slice 2 honest tag (creative-resolution
        layer named successor).

    (b) Boundary anchors:
          - upload calls create_creative_by_url with metadata
          - idempotent — re-upload returns existing record
          - manifest persist round-trip preserves all fields
          - lookup by metadata (mechanism, posture, optional metaphor)
          - lookup by name returns existing record
          - soft-fail without client / driver
          - operation-level errors → None
          - missing creative.id → None
          - lookup returns most-recent on multiple matches

    (c) calibration_pending=True (StackAdapt mutation schema validation
        is the calibration tool, carried from Slice 13).

    (d) Honest tags — what is NOT tested here:
          - Decision-time creative resolution from cascade (sibling).
          - Multi-variant generation per cell (sibling).
          - Reactance-risk scorer integration (sibling).
          - Lifecycle management (pause / archive / replace) — sibling.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest

from adam.intelligence.creative_upload_pipeline import (
    CreativeRecord,
    lookup_creative_by_metadata,
    lookup_creative_by_metadata_sync,
    lookup_creative_by_name,
    persist_creative_record,
    upload_creative,
)


# -----------------------------------------------------------------------------
# Fakes — async Neo4j driver + StackAdapt client
# -----------------------------------------------------------------------------


class _FakeRecord:
    def __init__(self, data: Dict[str, Any]) -> None:
        self._data = data

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)


class _FakeAsyncResult:
    def __init__(self, rows: List[Dict[str, Any]]) -> None:
        self._rows = list(rows)

    async def single(self) -> Optional[_FakeRecord]:
        if not self._rows:
            return None
        return _FakeRecord(self._rows[0])

    def __aiter__(self):
        async def _gen():
            for r in self._rows:
                yield _FakeRecord(r)
        return _gen()


class _FakeAsyncSession:
    def __init__(self, driver: "_FakeNeo4jDriver") -> None:
        self._driver = driver

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def run(self, cypher: str, **params: Any) -> _FakeAsyncResult:
        self._driver.calls.append((cypher, dict(params)))
        norm = cypher.strip()

        if norm.startswith("MERGE (c:UploadedCreative"):
            self._driver.records[params["stackadapt_creative_id"]] = dict(params)
            return _FakeAsyncResult([])

        if "MATCH (c:UploadedCreative {name:" in norm:
            for r in self._driver.records.values():
                if r.get("name") == params["name"]:
                    return _FakeAsyncResult([{"c": r}])
            return _FakeAsyncResult([])

        if norm.startswith("MATCH (c:UploadedCreative)"):
            # Filter by mechanism + posture_class + (optional) metaphor
            mech = params.get("mechanism")
            posture = params.get("posture_class")
            metaphor = params.get("primary_metaphor")
            matches = []
            for r in self._driver.records.values():
                if r.get("mechanism") != mech:
                    continue
                if r.get("posture_class") != posture:
                    continue
                if metaphor is not None and r.get("primary_metaphor") != metaphor:
                    continue
                matches.append(r)
            # Sort by uploaded_at_ts descending
            matches.sort(
                key=lambda r: r.get("uploaded_at_ts", 0.0),
                reverse=True,
            )
            return _FakeAsyncResult(
                [{"c": matches[0]}] if matches else []
            )

        return _FakeAsyncResult([])


class _FakeNeo4jDriver:
    def __init__(self) -> None:
        self.records: Dict[str, Dict[str, Any]] = {}
        self.calls: List = []

    def session(self) -> _FakeAsyncSession:
        return _FakeAsyncSession(self)


class _FakeStackAdaptClient:
    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []
        self._next_id = 1
        self.next_response: Optional[Dict[str, Any]] = None

    async def create_creative_by_url(self, **kwargs: Any) -> Dict[str, Any]:
        self.calls.append(kwargs)
        if self.next_response is not None:
            return self.next_response
        cid = f"sa-creative-{self._next_id}"
        self._next_id += 1
        return {
            "creative": {
                "id": cid,
                "name": kwargs.get("name"),
                "landingPageUrl": kwargs.get("landing_page_url"),
            },
            "errors": [],
        }


# -----------------------------------------------------------------------------
# Persist + lookup primitives
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_persist_record_no_driver_returns_false():
    record = CreativeRecord(
        stackadapt_creative_id="c-1", name="x",
        landing_page_url="https://x.com",
    )
    assert await persist_creative_record(record, driver=None) is False


@pytest.mark.asyncio
async def test_persist_then_lookup_by_name_round_trip():
    driver = _FakeNeo4jDriver()
    record = CreativeRecord(
        stackadapt_creative_id="c-rt-1",
        name="luxy commute blend",
        landing_page_url="https://luxy.example/?sapid={SA_POSTBACK_ID}",
        mechanism="social_proof",
        primary_metaphor="reliability_as_weight",
        posture_class="blend_compatible",
        advertiser_id="adv-1",
    )
    assert await persist_creative_record(record, driver=driver) is True

    loaded = await lookup_creative_by_name("luxy commute blend", driver)
    assert loaded is not None
    assert loaded.stackadapt_creative_id == "c-rt-1"
    assert loaded.mechanism == "social_proof"
    assert loaded.primary_metaphor == "reliability_as_weight"
    assert loaded.posture_class == "blend_compatible"
    assert loaded.advertiser_id == "adv-1"


@pytest.mark.asyncio
async def test_lookup_by_metadata_returns_matching():
    driver = _FakeNeo4jDriver()
    rec_a = CreativeRecord(
        stackadapt_creative_id="c-a", name="a",
        landing_page_url="https://a.com",
        mechanism="social_proof", posture_class="blend_compatible",
        primary_metaphor="forward_motion",
    )
    rec_b = CreativeRecord(
        stackadapt_creative_id="c-b", name="b",
        landing_page_url="https://b.com",
        mechanism="scarcity", posture_class="vigilance_activating",
    )
    await persist_creative_record(rec_a, driver)
    await persist_creative_record(rec_b, driver)

    out = await lookup_creative_by_metadata(
        mechanism="social_proof",
        posture_class="blend_compatible",
        driver=driver,
    )
    assert out is not None
    assert out.stackadapt_creative_id == "c-a"


@pytest.mark.asyncio
async def test_lookup_by_metadata_optional_metaphor_filter():
    driver = _FakeNeo4jDriver()
    rec_forward = CreativeRecord(
        stackadapt_creative_id="c-f", name="f",
        landing_page_url="https://f.com",
        mechanism="social_proof", posture_class="blend_compatible",
        primary_metaphor="forward_motion",
    )
    rec_reliable = CreativeRecord(
        stackadapt_creative_id="c-r", name="r",
        landing_page_url="https://r.com",
        mechanism="social_proof", posture_class="blend_compatible",
        primary_metaphor="reliability_as_weight",
    )
    await persist_creative_record(rec_forward, driver)
    await persist_creative_record(rec_reliable, driver)

    out = await lookup_creative_by_metadata(
        mechanism="social_proof",
        posture_class="blend_compatible",
        primary_metaphor="reliability_as_weight",
        driver=driver,
    )
    assert out is not None
    assert out.stackadapt_creative_id == "c-r"


@pytest.mark.asyncio
async def test_lookup_by_metadata_no_match_returns_none():
    driver = _FakeNeo4jDriver()
    rec = CreativeRecord(
        stackadapt_creative_id="c-1", name="x",
        landing_page_url="https://x.com",
        mechanism="social_proof", posture_class="blend_compatible",
    )
    await persist_creative_record(rec, driver)

    out = await lookup_creative_by_metadata(
        mechanism="not_a_real_mechanism",
        posture_class="blend_compatible",
        driver=driver,
    )
    assert out is None


@pytest.mark.asyncio
async def test_lookup_returns_most_recent_on_multiple_matches():
    driver = _FakeNeo4jDriver()
    older = CreativeRecord(
        stackadapt_creative_id="c-old", name="old",
        landing_page_url="https://x.com",
        mechanism="social_proof", posture_class="blend_compatible",
        uploaded_at_ts=100.0,
    )
    newer = CreativeRecord(
        stackadapt_creative_id="c-new", name="new",
        landing_page_url="https://x.com",
        mechanism="social_proof", posture_class="blend_compatible",
        uploaded_at_ts=200.0,
    )
    await persist_creative_record(older, driver)
    await persist_creative_record(newer, driver)

    out = await lookup_creative_by_metadata(
        mechanism="social_proof",
        posture_class="blend_compatible",
        driver=driver,
    )
    assert out is not None
    assert out.stackadapt_creative_id == "c-new"


# -----------------------------------------------------------------------------
# upload_creative
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_creative_calls_api_with_metadata():
    client = _FakeStackAdaptClient()
    driver = _FakeNeo4jDriver()
    record = await upload_creative(
        landing_page_url="https://luxy.example/?sapid={SA_POSTBACK_ID}",
        name="luxy social_proof blend",
        mechanism="social_proof",
        primary_metaphor="forward_motion",
        posture_class="blend_compatible",
        client=client,
        driver=driver,
    )
    assert record is not None
    assert record.mechanism == "social_proof"
    # Client was called with the metadata
    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["mechanism"] == "social_proof"
    assert call["primary_metaphor"] == "forward_motion"
    assert call["posture_class"] == "blend_compatible"


@pytest.mark.asyncio
async def test_upload_creative_idempotent_on_repeat_name():
    """Re-uploading the same name returns the existing record without
    calling the StackAdapt API."""
    client = _FakeStackAdaptClient()
    driver = _FakeNeo4jDriver()

    first = await upload_creative(
        landing_page_url="https://luxy.example/",
        name="repeat",
        mechanism="social_proof",
        client=client, driver=driver,
    )
    assert first is not None
    api_calls_after_first = len(client.calls)

    second = await upload_creative(
        landing_page_url="https://luxy.example/",
        name="repeat",
        mechanism="social_proof",
        client=client, driver=driver,
    )
    assert second is not None
    assert second.stackadapt_creative_id == first.stackadapt_creative_id
    # No new API call
    assert len(client.calls) == api_calls_after_first


@pytest.mark.asyncio
async def test_upload_creative_no_client_returns_none():
    driver = _FakeNeo4jDriver()
    record = await upload_creative(
        landing_page_url="https://x.com",
        name="no-client",
        client=None, driver=driver,
    )
    assert record is None


@pytest.mark.asyncio
async def test_upload_creative_operation_errors_returns_none():
    """GraphQL operation-level errors → upload returns None."""
    client = _FakeStackAdaptClient()
    client.next_response = {
        "creative": None,
        "errors": [{"field": "name", "message": "name in use"}],
    }
    record = await upload_creative(
        landing_page_url="https://x.com",
        name="bad",
        client=client,
    )
    assert record is None


@pytest.mark.asyncio
async def test_upload_creative_missing_id_returns_none():
    """Response missing creative.id → upload returns None."""
    client = _FakeStackAdaptClient()
    client.next_response = {"creative": {}, "errors": []}
    record = await upload_creative(
        landing_page_url="https://x.com",
        name="missing-id",
        client=client,
    )
    assert record is None


@pytest.mark.asyncio
async def test_upload_creative_api_exception_returns_none():
    """API raising → soft-fail, returns None."""
    class _RaisingClient:
        async def create_creative_by_url(self, **kwargs):
            raise RuntimeError("api down")

    record = await upload_creative(
        landing_page_url="https://x.com",
        name="raising",
        client=_RaisingClient(),
    )
    assert record is None


@pytest.mark.asyncio
async def test_upload_creative_persists_to_manifest():
    client = _FakeStackAdaptClient()
    driver = _FakeNeo4jDriver()
    record = await upload_creative(
        landing_page_url="https://x.com",
        name="persisted",
        mechanism="authority",
        primary_metaphor="status_as_verticality",
        posture_class="blend_compatible",
        client=client, driver=driver,
    )
    assert record is not None
    # Manifest contains the record
    persisted = await lookup_creative_by_name("persisted", driver)
    assert persisted is not None
    assert persisted.stackadapt_creative_id == record.stackadapt_creative_id


@pytest.mark.asyncio
async def test_upload_creative_works_without_driver():
    """No driver → upload still calls the API and returns the record;
    just no manifest persist."""
    client = _FakeStackAdaptClient()
    record = await upload_creative(
        landing_page_url="https://x.com",
        name="no-driver",
        client=client, driver=None,
    )
    assert record is not None
    assert len(client.calls) == 1


# -----------------------------------------------------------------------------
# CreativeRecord schema
# -----------------------------------------------------------------------------


def test_creative_record_pydantic_round_trip():
    record = CreativeRecord(
        stackadapt_creative_id="c-x",
        name="round-trip",
        landing_page_url="https://x.com",
        mechanism="social_proof",
        primary_metaphor="forward_motion",
        posture_class="blend_compatible",
        advertiser_id="adv-1",
        creative_type="native",
    )
    serialized = record.model_dump_json()
    restored = CreativeRecord.model_validate_json(serialized)
    assert restored.stackadapt_creative_id == "c-x"
    assert restored.creative_type == "native"


def test_creative_record_extra_fields_forbidden():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        CreativeRecord(
            stackadapt_creative_id="c", name="n",
            landing_page_url="https://x.com",
            unknown_field=42,  # type: ignore[call-arg]
        )


# =============================================================================
# Slice C — sync lookup_creative_by_metadata_sync
# =============================================================================
#
# Mirrors the async lookup but against a sync GraphDatabase driver
# (the one graph_cache._get_driver() returns). Cascade is sync; this
# is the path it actually uses.


class _FakeSyncResult:
    def __init__(self, rows: List[Dict[str, Any]]) -> None:
        self._rows = list(rows)

    def single(self) -> Optional[_FakeRecord]:
        return _FakeRecord(self._rows[0]) if self._rows else None


class _FakeSyncSession:
    def __init__(self, driver: "_FakeSyncDriver") -> None:
        self._driver = driver

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return None

    def run(self, cypher: str, **params: Any) -> _FakeSyncResult:
        self._driver.calls.append((cypher, dict(params)))
        norm = cypher.strip()
        if norm.startswith("MATCH (c:UploadedCreative)"):
            mech = params.get("mechanism")
            posture = params.get("posture_class")
            metaphor = params.get("primary_metaphor")
            matches = []
            for r in self._driver.records.values():
                if r.get("mechanism") != mech:
                    continue
                if r.get("posture_class") != posture:
                    continue
                if metaphor is not None and r.get("primary_metaphor") != metaphor:
                    continue
                matches.append(r)
            matches.sort(
                key=lambda r: r.get("uploaded_at_ts", 0.0), reverse=True,
            )
            return _FakeSyncResult([{"c": matches[0]}] if matches else [])
        return _FakeSyncResult([])


class _FakeSyncDriver:
    def __init__(self) -> None:
        self.records: Dict[str, Dict[str, Any]] = {}
        self.calls: List = []

    def session(self) -> _FakeSyncSession:
        return _FakeSyncSession(self)

    def add(self, record: CreativeRecord) -> None:
        self.records[record.stackadapt_creative_id] = {
            "stackadapt_creative_id": record.stackadapt_creative_id,
            "name": record.name,
            "landing_page_url": record.landing_page_url,
            "mechanism": record.mechanism,
            "primary_metaphor": record.primary_metaphor,
            "posture_class": record.posture_class,
            "advertiser_id": record.advertiser_id,
            "creative_type": record.creative_type,
            "uploaded_at_ts": record.uploaded_at_ts,
        }


def _rec(
    *, cid: str, mech: str, posture: str,
    metaphor: Optional[str] = None, ts: float = 100.0,
) -> CreativeRecord:
    return CreativeRecord(
        stackadapt_creative_id=cid,
        name=f"name-{cid}",
        landing_page_url=f"https://x/{cid}",
        mechanism=mech,
        posture_class=posture,
        primary_metaphor=metaphor,
        uploaded_at_ts=ts,
    )


def test_sync_lookup_no_driver_returns_none():
    out = lookup_creative_by_metadata_sync(
        mechanism="social_proof",
        posture_class="blend_compatible",
        driver=None,
    )
    assert out is None


def test_sync_lookup_empty_mechanism_returns_none():
    driver = _FakeSyncDriver()
    out = lookup_creative_by_metadata_sync(
        mechanism="",
        posture_class="blend_compatible",
        driver=driver,
    )
    assert out is None
    assert len(driver.calls) == 0  # short-circuited


def test_sync_lookup_empty_posture_returns_none():
    driver = _FakeSyncDriver()
    out = lookup_creative_by_metadata_sync(
        mechanism="social_proof",
        posture_class="",
        driver=driver,
    )
    assert out is None
    assert len(driver.calls) == 0


def test_sync_lookup_returns_match():
    driver = _FakeSyncDriver()
    driver.add(_rec(cid="c-1", mech="social_proof", posture="blend_compatible"))

    out = lookup_creative_by_metadata_sync(
        mechanism="social_proof",
        posture_class="blend_compatible",
        driver=driver,
    )
    assert out is not None
    assert out.stackadapt_creative_id == "c-1"
    assert out.mechanism == "social_proof"
    assert out.posture_class == "blend_compatible"


def test_sync_lookup_no_match_returns_none():
    driver = _FakeSyncDriver()
    driver.add(_rec(cid="c-1", mech="social_proof", posture="blend_compatible"))

    out = lookup_creative_by_metadata_sync(
        mechanism="not_a_mech",
        posture_class="blend_compatible",
        driver=driver,
    )
    assert out is None


def test_sync_lookup_optional_metaphor_filter_matches():
    driver = _FakeSyncDriver()
    driver.add(_rec(
        cid="c-fwd", mech="social_proof", posture="blend_compatible",
        metaphor="forward_motion",
    ))
    driver.add(_rec(
        cid="c-rel", mech="social_proof", posture="blend_compatible",
        metaphor="reliability_as_weight",
    ))

    out = lookup_creative_by_metadata_sync(
        mechanism="social_proof",
        posture_class="blend_compatible",
        primary_metaphor="reliability_as_weight",
        driver=driver,
    )
    assert out is not None
    assert out.stackadapt_creative_id == "c-rel"


def test_sync_lookup_metaphor_none_matches_any():
    """primary_metaphor=None should match any metaphor (Cypher OR)."""
    driver = _FakeSyncDriver()
    driver.add(_rec(
        cid="c-1", mech="social_proof", posture="blend_compatible",
        metaphor="forward_motion", ts=100.0,
    ))
    out = lookup_creative_by_metadata_sync(
        mechanism="social_proof",
        posture_class="blend_compatible",
        primary_metaphor=None,
        driver=driver,
    )
    assert out is not None
    assert out.stackadapt_creative_id == "c-1"


def test_sync_lookup_returns_most_recent():
    driver = _FakeSyncDriver()
    driver.add(_rec(
        cid="c-old", mech="social_proof",
        posture="blend_compatible", ts=100.0,
    ))
    driver.add(_rec(
        cid="c-new", mech="social_proof",
        posture="blend_compatible", ts=200.0,
    ))

    out = lookup_creative_by_metadata_sync(
        mechanism="social_proof",
        posture_class="blend_compatible",
        driver=driver,
    )
    assert out is not None
    assert out.stackadapt_creative_id == "c-new"


def test_sync_lookup_session_exception_returns_none():
    """Driver session raising → soft-fail to None (bid path must
    NEVER block on resolution)."""
    class _RaisingDriver:
        def session(self):
            raise RuntimeError("connection lost")

    out = lookup_creative_by_metadata_sync(
        mechanism="social_proof",
        posture_class="blend_compatible",
        driver=_RaisingDriver(),
    )
    assert out is None


def test_sync_lookup_run_exception_returns_none():
    """driver.session().run(...) raising → soft-fail to None."""
    class _BadSession:
        def __enter__(self): return self
        def __exit__(self, *a): return None
        def run(self, *a, **kw):
            raise RuntimeError("cypher syntax error")

    class _BadDriver:
        def session(self):
            return _BadSession()

    out = lookup_creative_by_metadata_sync(
        mechanism="social_proof",
        posture_class="blend_compatible",
        driver=_BadDriver(),
    )
    assert out is None


def test_sync_lookup_passes_correct_cypher_params():
    driver = _FakeSyncDriver()
    driver.add(_rec(cid="c-1", mech="social_proof", posture="blend_compatible"))

    lookup_creative_by_metadata_sync(
        mechanism="social_proof",
        posture_class="blend_compatible",
        primary_metaphor="forward_motion",
        driver=driver,
    )
    assert len(driver.calls) == 1
    _, params = driver.calls[0]
    assert params == {
        "mechanism": "social_proof",
        "posture_class": "blend_compatible",
        "primary_metaphor": "forward_motion",
    }
