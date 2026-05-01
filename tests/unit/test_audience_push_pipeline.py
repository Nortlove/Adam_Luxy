"""Pin Slice 15 — Audience push pipeline (cohort_id → StackAdapt audience).

Discipline anchors (B3-LUXY a/b/c/d):

    (a) Citations: directive line 542-543 (audience-segment pushes
        via GraphQL); Slice 13 substrate (9c369f8); cohort_id as
        canonical key (Spine #7).

    (b) Boundary anchors:
          - ensure creates new audience when cohort unknown
          - ensure returns existing record without API call when
            cohort already mapped (idempotent)
          - persist + lookup round-trip preserves all fields
          - sync_users adds users + updates user_count + last_synced_ts
          - sync_users no-op (just timestamp bump) on empty user_ids
          - sync_users returns None when cohort not in manifest
          - soft-fail without client / driver / cohort_id
          - operation errors → None
          - missing audience.id → None

    (c) calibration_pending=True (carried from Slice 13).

    (d) Honest tags — what is NOT tested here:
          - Real cohort discovery (Spine #7 BLOCKED on Loop B)
          - User-removal primitive (sibling)
          - Hourly / daily scheduler hookup (sibling)
          - Cohort-prior writeback (separate concern)
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import pytest

from adam.intelligence.audience_push_pipeline import (
    AudienceRecord,
    ensure_audience_for_cohort,
    list_all_audiences,
    lookup_audience_by_cohort,
    persist_audience_record,
    sync_users_to_cohort_audience,
)


# -----------------------------------------------------------------------------
# Fakes
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

        if norm.startswith("MERGE (a:CohortAudience"):
            self._driver.records[params["cohort_id"]] = dict(params)
            return _FakeAsyncResult([])

        if "MATCH (a:CohortAudience {cohort_id:" in norm:
            cid = params["cohort_id"]
            row = self._driver.records.get(cid)
            return _FakeAsyncResult([{"a": row}] if row else [])

        if norm.startswith("MATCH (a:CohortAudience)"):
            return _FakeAsyncResult(
                [{"a": r} for r in self._driver.records.values()]
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
        self.create_calls: List[Dict[str, Any]] = []
        self.add_calls: List[Dict[str, Any]] = []
        self._next_id = 1
        self.next_create_response: Optional[Dict[str, Any]] = None
        self.next_add_response: Optional[Dict[str, Any]] = None

    async def create_audience(self, **kwargs: Any) -> Dict[str, Any]:
        self.create_calls.append(kwargs)
        if self.next_create_response is not None:
            return self.next_create_response
        aid = f"sa-aud-{self._next_id}"
        self._next_id += 1
        return {
            "audience": {"id": aid, "name": kwargs.get("name")},
            "errors": [],
        }

    async def add_users_to_audience(
        self, *, audience_id: str, user_ids: List[str],
    ) -> Dict[str, Any]:
        self.add_calls.append(
            {"audience_id": audience_id, "user_ids": list(user_ids)}
        )
        if self.next_add_response is not None:
            return self.next_add_response
        return {"audience": {"id": audience_id}, "errors": []}


# -----------------------------------------------------------------------------
# Persist + lookup primitives
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_persist_no_driver_returns_false():
    record = AudienceRecord(
        cohort_id="c-1", stackadapt_audience_id="sa-1", name="x",
    )
    assert await persist_audience_record(record, driver=None) is False


@pytest.mark.asyncio
async def test_persist_then_lookup_round_trip():
    driver = _FakeNeo4jDriver()
    record = AudienceRecord(
        cohort_id="cohort-airport-transfer",
        stackadapt_audience_id="sa-aud-rt",
        name="adam_cohort_cohort-airport-transfer",
        advertiser_id="adv-1",
        description="LUXY airport transfer cohort",
        user_count=42,
    )
    assert await persist_audience_record(record, driver=driver) is True

    loaded = await lookup_audience_by_cohort(
        "cohort-airport-transfer", driver,
    )
    assert loaded is not None
    assert loaded.stackadapt_audience_id == "sa-aud-rt"
    assert loaded.name == "adam_cohort_cohort-airport-transfer"
    assert loaded.user_count == 42
    assert loaded.description == "LUXY airport transfer cohort"


@pytest.mark.asyncio
async def test_lookup_missing_cohort_returns_none():
    driver = _FakeNeo4jDriver()
    out = await lookup_audience_by_cohort("not-mapped", driver)
    assert out is None


@pytest.mark.asyncio
async def test_lookup_no_driver_returns_none():
    out = await lookup_audience_by_cohort("c-1", driver=None)
    assert out is None


@pytest.mark.asyncio
async def test_lookup_empty_cohort_returns_none():
    driver = _FakeNeo4jDriver()
    out = await lookup_audience_by_cohort("", driver)
    assert out is None


@pytest.mark.asyncio
async def test_list_all_audiences_returns_full_manifest():
    driver = _FakeNeo4jDriver()
    for i in range(3):
        rec = AudienceRecord(
            cohort_id=f"c-{i}",
            stackadapt_audience_id=f"sa-{i}",
            name=f"cohort-{i}",
        )
        await persist_audience_record(rec, driver)
    out = await list_all_audiences(driver)
    assert len(out) == 3
    assert {r.cohort_id for r in out} == {"c-0", "c-1", "c-2"}


@pytest.mark.asyncio
async def test_list_all_no_driver_returns_empty():
    assert await list_all_audiences(driver=None) == []


# -----------------------------------------------------------------------------
# ensure_audience_for_cohort
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ensure_creates_audience_via_api():
    client = _FakeStackAdaptClient()
    driver = _FakeNeo4jDriver()
    record = await ensure_audience_for_cohort(
        cohort_id="cohort-luxy-1",
        client=client, driver=driver,
    )
    assert record is not None
    assert record.cohort_id == "cohort-luxy-1"
    assert record.name == "adam_cohort_cohort-luxy-1"
    assert len(client.create_calls) == 1


@pytest.mark.asyncio
async def test_ensure_idempotent_on_repeat_cohort():
    client = _FakeStackAdaptClient()
    driver = _FakeNeo4jDriver()

    first = await ensure_audience_for_cohort(
        cohort_id="repeat-cohort", client=client, driver=driver,
    )
    api_calls_after_first = len(client.create_calls)

    second = await ensure_audience_for_cohort(
        cohort_id="repeat-cohort", client=client, driver=driver,
    )

    assert second is not None
    assert second.stackadapt_audience_id == first.stackadapt_audience_id
    # No new API call on idempotent re-ensure
    assert len(client.create_calls) == api_calls_after_first


@pytest.mark.asyncio
async def test_ensure_no_cohort_id_returns_none():
    client = _FakeStackAdaptClient()
    record = await ensure_audience_for_cohort(
        cohort_id="", client=client,
    )
    assert record is None


@pytest.mark.asyncio
async def test_ensure_no_client_returns_none():
    driver = _FakeNeo4jDriver()
    record = await ensure_audience_for_cohort(
        cohort_id="c", client=None, driver=driver,
    )
    assert record is None


@pytest.mark.asyncio
async def test_ensure_with_custom_name_and_description():
    client = _FakeStackAdaptClient()
    record = await ensure_audience_for_cohort(
        cohort_id="c-custom",
        name="LUXY VIP commuters",
        description="High-value frequent travelers",
        advertiser_id="adv-luxy",
        client=client,
    )
    assert record is not None
    assert record.name == "LUXY VIP commuters"
    assert record.description == "High-value frequent travelers"
    assert record.advertiser_id == "adv-luxy"


@pytest.mark.asyncio
async def test_ensure_operation_errors_returns_none():
    client = _FakeStackAdaptClient()
    client.next_create_response = {
        "audience": None,
        "errors": [{"field": "name", "message": "in use"}],
    }
    record = await ensure_audience_for_cohort(
        cohort_id="c-err", client=client,
    )
    assert record is None


@pytest.mark.asyncio
async def test_ensure_missing_audience_id_returns_none():
    client = _FakeStackAdaptClient()
    client.next_create_response = {"audience": {}, "errors": []}
    record = await ensure_audience_for_cohort(
        cohort_id="c-no-id", client=client,
    )
    assert record is None


@pytest.mark.asyncio
async def test_ensure_api_exception_returns_none():
    class _Raising:
        async def create_audience(self, **kwargs):
            raise RuntimeError("api down")

    record = await ensure_audience_for_cohort(
        cohort_id="c-x", client=_Raising(),
    )
    assert record is None


# -----------------------------------------------------------------------------
# sync_users_to_cohort_audience
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sync_users_calls_api_and_updates_user_count():
    client = _FakeStackAdaptClient()
    driver = _FakeNeo4jDriver()
    await ensure_audience_for_cohort(
        cohort_id="c-sync", client=client, driver=driver,
    )

    updated = await sync_users_to_cohort_audience(
        cohort_id="c-sync",
        user_ids=["u-1", "u-2", "u-3"],
        client=client, driver=driver,
    )
    assert updated is not None
    assert updated.user_count == 3
    assert len(client.add_calls) == 1
    assert client.add_calls[0]["user_ids"] == ["u-1", "u-2", "u-3"]


@pytest.mark.asyncio
async def test_sync_empty_user_ids_no_api_call_but_timestamp_bumps():
    client = _FakeStackAdaptClient()
    driver = _FakeNeo4jDriver()
    record = await ensure_audience_for_cohort(
        cohort_id="c-empty", client=client, driver=driver,
    )
    assert record is not None
    initial_synced_ts = record.last_synced_ts

    # Sleep micro-second so timestamps differ
    time.sleep(0.001)

    updated = await sync_users_to_cohort_audience(
        cohort_id="c-empty", user_ids=[],
        client=client, driver=driver,
    )
    assert updated is not None
    assert updated.user_count == 0
    assert updated.last_synced_ts > initial_synced_ts
    # No API call for empty user_ids
    assert len(client.add_calls) == 0


@pytest.mark.asyncio
async def test_sync_returns_none_when_cohort_not_in_manifest():
    """Caller must call ensure_audience_for_cohort first."""
    client = _FakeStackAdaptClient()
    driver = _FakeNeo4jDriver()
    out = await sync_users_to_cohort_audience(
        cohort_id="never-ensured",
        user_ids=["u-1"],
        client=client, driver=driver,
    )
    assert out is None


@pytest.mark.asyncio
async def test_sync_no_client_returns_none():
    client = _FakeStackAdaptClient()
    driver = _FakeNeo4jDriver()
    await ensure_audience_for_cohort(
        cohort_id="c-no-client", client=client, driver=driver,
    )
    out = await sync_users_to_cohort_audience(
        cohort_id="c-no-client",
        user_ids=["u-1"],
        client=None, driver=driver,
    )
    assert out is None


@pytest.mark.asyncio
async def test_sync_operation_errors_returns_none():
    client = _FakeStackAdaptClient()
    driver = _FakeNeo4jDriver()
    await ensure_audience_for_cohort(
        cohort_id="c-err", client=client, driver=driver,
    )
    client.next_add_response = {
        "audience": None,
        "errors": [{"field": "userIds", "message": "exceeds limit"}],
    }
    out = await sync_users_to_cohort_audience(
        cohort_id="c-err",
        user_ids=["u-1", "u-2"],
        client=client, driver=driver,
    )
    assert out is None


@pytest.mark.asyncio
async def test_sync_accumulates_user_count_across_calls():
    """Multiple sync calls accumulate user_count (each adds users)."""
    client = _FakeStackAdaptClient()
    driver = _FakeNeo4jDriver()
    await ensure_audience_for_cohort(
        cohort_id="c-accum", client=client, driver=driver,
    )

    await sync_users_to_cohort_audience(
        cohort_id="c-accum",
        user_ids=["u-1", "u-2"],
        client=client, driver=driver,
    )
    await sync_users_to_cohort_audience(
        cohort_id="c-accum",
        user_ids=["u-3"],
        client=client, driver=driver,
    )
    record = await lookup_audience_by_cohort("c-accum", driver)
    assert record is not None
    assert record.user_count == 3


# -----------------------------------------------------------------------------
# AudienceRecord schema
# -----------------------------------------------------------------------------


def test_audience_record_pydantic_round_trip():
    record = AudienceRecord(
        cohort_id="c-rt", stackadapt_audience_id="sa-rt",
        name="rt-test", advertiser_id="adv-1",
        description="d", user_count=5,
    )
    serialized = record.model_dump_json()
    restored = AudienceRecord.model_validate_json(serialized)
    assert restored.cohort_id == "c-rt"
    assert restored.user_count == 5


def test_audience_record_extra_fields_forbidden():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        AudienceRecord(
            cohort_id="c", stackadapt_audience_id="s", name="n",
            unknown_field=42,  # type: ignore[call-arg]
        )


def test_audience_record_negative_user_count_rejected():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        AudienceRecord(
            cohort_id="c", stackadapt_audience_id="s", name="n",
            user_count=-1,
        )
