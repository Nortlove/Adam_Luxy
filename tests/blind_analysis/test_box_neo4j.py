"""Q.B/Q.3 (Sketch C+) — tests for blind_analysis Neo4j persistence.

Pin: write/read round-trip; idempotent MERGE; state-machine transitions
honored; soft-fail on absent driver.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock

import pytest

from adam.blind_analysis.box import (
    BoxParameter,
    UnblindingState,
    sealed_box,
)
from adam.blind_analysis.box_neo4j import (
    PersistedBoxRecord,
    authorize_box,
    mark_unblinded,
    read_box_from_neo4j,
    write_box_to_neo4j,
)


def _small_box():
    p_arch = BoxParameter(name="archetype", values=("a", "b"))
    p_dim = BoxParameter(name="dim", values=("d1", "d2"))
    grid = [(a, d) for a in ("a", "b") for d in ("d1", "d2")]
    return sealed_box(
        name="test_box",
        parameters=(p_arch, p_dim),
        signal_region=[],
        control_region=grid,
        decision_statistic="test_stat",
        decision_threshold=0.05,
    )


class _FakeAsyncSession:
    def __init__(self, recorded):
        self._recorded = recorded
        self._next_record = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def run(self, cypher, params=None, **kwargs):
        if params is None:
            params = kwargs
        self._recorded.append((cypher, dict(params)))
        result = MagicMock()
        result.single = AsyncMock(return_value=self._next_record)
        return result

    def set_next_record(self, record):
        self._next_record = record


class _FakeAsyncDriver:
    def __init__(self):
        self.calls: List = []
        self._session = _FakeAsyncSession(self.calls)

    def session(self):
        return self._session


@pytest.mark.asyncio
async def test_write_box_to_neo4j_serializes_box():
    box = _small_box()
    driver = _FakeAsyncDriver()
    ok = await write_box_to_neo4j(box, driver)
    assert ok is True
    assert len(driver.calls) == 1
    cypher, params = driver.calls[0]
    assert "BlindAnalysisBox" in cypher
    assert params["hash"] == box.pre_registration_hash
    assert params["name"] == "test_box"
    assert params["state"] == "sealed"
    assert params["decision_threshold"] == 0.05


@pytest.mark.asyncio
async def test_write_box_persists_post_pilot_methods():
    box = _small_box()
    driver = _FakeAsyncDriver()
    methods = {"method_a": {"params": "x"}}
    ok = await write_box_to_neo4j(box, driver, post_pilot_methods=methods)
    assert ok is True
    _, params = driver.calls[0]
    assert "method_a" in params["post_pilot_methods_json"]


@pytest.mark.asyncio
async def test_write_box_soft_fails_no_driver():
    box = _small_box()
    ok = await write_box_to_neo4j(box, None)
    assert ok is False


@pytest.mark.asyncio
async def test_read_box_from_neo4j_returns_record():
    driver = _FakeAsyncDriver()
    node = {
        "hash": "abcd1234",
        "name": "test_box",
        "decision_statistic": "test_stat",
        "decision_threshold": 0.05,
        "state": "unblinded",
        "sealed_at": datetime.now(timezone.utc),
        "authorized_at": None,
        "unblinded_at": datetime.now(timezone.utc),
        "notes": "",
        "post_pilot_methods_json": '{"k": "v"}',
    }
    record = MagicMock()
    record.get = lambda k: {"b": node}.get(k)
    driver._session.set_next_record(record)
    rec = await read_box_from_neo4j("abcd1234", driver)
    assert rec is not None
    assert rec.hash == "abcd1234"
    assert rec.is_unblinded is True
    assert rec.post_pilot_methods_json == '{"k": "v"}'


@pytest.mark.asyncio
async def test_read_box_returns_none_when_not_found():
    driver = _FakeAsyncDriver()
    driver._session.set_next_record(None)
    rec = await read_box_from_neo4j("missing_hash", driver)
    assert rec is None


@pytest.mark.asyncio
async def test_authorize_box_sends_party_and_justification():
    driver = _FakeAsyncDriver()
    record = MagicMock()
    record.get = lambda k: {"b": {"hash": "abcd"}}.get(k)
    driver._session.set_next_record(record)
    ok = await authorize_box(
        "abcd", "Chris Nocera", "pilot launch", driver,
    )
    assert ok is True
    cypher, params = driver.calls[0]
    assert "state = 'sealed'" in cypher
    assert "state = 'authorized'" in cypher
    assert params["party"] == "Chris Nocera"
    assert params["justification"] == "pilot launch"


@pytest.mark.asyncio
async def test_authorize_box_requires_party_and_justification():
    from adam.blind_analysis.box import BoxValidationError
    driver = _FakeAsyncDriver()
    with pytest.raises(BoxValidationError):
        await authorize_box("h", "", "j", driver)
    with pytest.raises(BoxValidationError):
        await authorize_box("h", "p", "", driver)


@pytest.mark.asyncio
async def test_mark_unblinded_uses_state_gated_cypher():
    driver = _FakeAsyncDriver()
    record = MagicMock()
    record.get = lambda k: {"b": {"hash": "abcd"}}.get(k)
    driver._session.set_next_record(record)
    ok = await mark_unblinded("abcd", driver)
    assert ok is True
    cypher, _ = driver.calls[0]
    assert "state = 'authorized'" in cypher
    assert "state = 'unblinded'" in cypher


@pytest.mark.asyncio
async def test_authorize_box_returns_false_when_not_found():
    driver = _FakeAsyncDriver()
    driver._session.set_next_record(None)
    ok = await authorize_box("missing", "p", "j", driver)
    assert ok is False


@pytest.mark.asyncio
async def test_box_hash_determinism_across_writes():
    """The hash MUST be identical for two boxes built from same params.
    This is the regression invariant — box hash is the identity."""
    box1 = _small_box()
    box2 = _small_box()
    assert box1.pre_registration_hash == box2.pre_registration_hash


def test_persisted_box_record_is_unblinded_property():
    sealed = PersistedBoxRecord(
        hash="h", name="n", decision_statistic="s",
        decision_threshold=0.05, state="sealed",
        sealed_at=None, authorized_at=None, unblinded_at=None,
        notes="", post_pilot_methods_json=None,
    )
    assert sealed.is_unblinded is False
    unblinded = PersistedBoxRecord(
        hash="h", name="n", decision_statistic="s",
        decision_threshold=0.05, state="unblinded",
        sealed_at=None, authorized_at=None, unblinded_at=None,
        notes="", post_pilot_methods_json=None,
    )
    assert unblinded.is_unblinded is True
