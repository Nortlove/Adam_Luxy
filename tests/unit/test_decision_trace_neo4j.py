"""Pin Spine #6 Neo4j archival — directive line 248 (long-term half).

Tests pin:
  * Round-trip via fake async Neo4j driver preserves trace.
  * Archive cypher parameter contract (decision_id / user_id /
    chosen_creative_id / chosen_mechanism / chosen_score / timestamp /
    payload_json / archived_at_ts / schema_version).
  * Idempotent MERGE on decision_id — repeat archive overwrites.
  * Soft-fail: no driver → archive False, load None, list [].
  * Bad JSON in node payload → load returns None.
  * User filter cypher matches via (:User)-[:MADE_DECISION]->(:DecisionTrace).
  * Cypher schema constants pinned (label / relationship names).
  * Per-record parse failures in list silently skipped.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import pytest

from adam.intelligence.decision_trace import (
    AlternativeCandidate,
    DecisionTrace,
    build_decision_trace,
)
from adam.intelligence.decision_trace_neo4j import (
    DECISION_TRACE_NODE_LABEL,
    MADE_DECISION_REL,
    MECHANISM_NODE_LABEL,
    USED_MECHANISM_REL,
    USER_NODE_LABEL,
    archive_trace_to_neo4j,
    list_traces_for_user_from_neo4j,
    load_trace_from_neo4j,
)


# -----------------------------------------------------------------------------
# In-memory fake async Neo4j driver
# -----------------------------------------------------------------------------


class _FakeRecord:
    """A row-like object with .get(key) returning the column value."""

    def __init__(self, data: Dict[str, Any]) -> None:
        self._data = data

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)


class _FakeAsyncResult:
    """Iterates returned rows + supports .single()."""

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
    """Records every cypher call + parameters; routes to driver state."""

    def __init__(self, driver: "FakeAsyncNeo4jDriver") -> None:
        self._driver = driver

    async def __aenter__(self) -> "_FakeAsyncSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def run(self, cypher: str, **params: Any) -> _FakeAsyncResult:
        self._driver.calls.append((cypher, dict(params)))
        if self._driver.fail_next_run:
            self._driver.fail_next_run = False
            raise RuntimeError("fault-injected cypher failure")

        # Route based on cypher type — pattern-match on the start.
        cypher_norm = cypher.strip()

        if cypher_norm.startswith("MERGE (d:"):
            # Archive — write trace into driver state
            decision_id = params["decision_id"]
            self._driver.traces[decision_id] = dict(params)
            user_id = params.get("user_id", "")
            if user_id:
                self._driver.user_index.setdefault(user_id, [])
                if decision_id not in self._driver.user_index[user_id]:
                    self._driver.user_index[user_id].append(decision_id)
            return _FakeAsyncResult([])

        if "RETURN d.payload_json AS payload_json LIMIT 1" in cypher_norm:
            # Load by decision_id
            did = params["decision_id"]
            t = self._driver.traces.get(did)
            if t is None:
                return _FakeAsyncResult([])
            return _FakeAsyncResult(
                [{"payload_json": t["payload_json"]}],
            )

        if "ORDER BY d.timestamp DESC" in cypher_norm:
            # List for user
            uid = params["user_id"]
            limit = params.get("limit", 100)
            ids = self._driver.user_index.get(uid, [])
            # newest-first by timestamp_epoch (we stored it on the trace dict)
            sorted_ids = sorted(
                ids,
                key=lambda d: self._driver.traces[d]["timestamp_epoch"],
                reverse=True,
            )
            rows = []
            for did in sorted_ids[:limit]:
                t = self._driver.traces.get(did)
                if t is None:
                    continue
                rows.append({"payload_json": t["payload_json"]})
            return _FakeAsyncResult(rows)

        return _FakeAsyncResult([])


class FakeAsyncNeo4jDriver:
    def __init__(self) -> None:
        self.traces: Dict[str, Dict[str, Any]] = {}
        self.user_index: Dict[str, List[str]] = {}
        self.calls: List = []
        self.fail_next_run: bool = False

    def session(self) -> _FakeAsyncSession:
        return _FakeAsyncSession(self)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _example_trace(
    decision_id: str = "dec-1",
    user_id: str = "user-7",
    timestamp: Optional[datetime] = None,
) -> DecisionTrace:
    return build_decision_trace(
        decision_id=decision_id,
        user_id=user_id,
        chosen_creative_id="creative-a",
        chosen_mechanism="automatic_evaluation",
        chosen_score=0.71,
        score_components={"pragmatic": 0.5, "fluency": 0.21},
        alternatives=[
            AlternativeCandidate(
                creative_id="alt-1", mechanism="m1",
                posterior_score=0.6, propensity_under_TS=0.2,
            ),
        ],
        timestamp=timestamp or datetime(
            2026, 4, 30, 12, 0, 0, tzinfo=timezone.utc,
        ),
    )


# -----------------------------------------------------------------------------
# Schema constants pinned
# -----------------------------------------------------------------------------


def test_node_label_pinned():
    """Schema is part of the operational contract — drift requires
    deliberate update, not silent rename."""
    assert DECISION_TRACE_NODE_LABEL == "DecisionTrace"
    assert USER_NODE_LABEL == "User"
    assert MECHANISM_NODE_LABEL == "Mechanism"


def test_relationship_names_pinned():
    assert MADE_DECISION_REL == "MADE_DECISION"
    assert USED_MECHANISM_REL == "USED_MECHANISM"


# -----------------------------------------------------------------------------
# Soft-fail without driver
# -----------------------------------------------------------------------------


async def test_archive_no_driver_returns_false():
    trace = _example_trace()
    assert (await archive_trace_to_neo4j(trace, driver=None)) is False


async def test_load_no_driver_returns_none():
    assert (await load_trace_from_neo4j("dec-1", driver=None)) is None


async def test_list_no_driver_returns_empty():
    assert (
        await list_traces_for_user_from_neo4j("user-7", driver=None)
    ) == []


# -----------------------------------------------------------------------------
# Round-trip
# -----------------------------------------------------------------------------


async def test_archive_then_load_round_trip():
    driver = FakeAsyncNeo4jDriver()
    trace = _example_trace()
    ok = await archive_trace_to_neo4j(trace, driver)
    assert ok is True

    loaded = await load_trace_from_neo4j(trace.decision_id, driver)
    assert loaded is not None
    assert loaded.decision_id == trace.decision_id
    assert loaded.user_id == trace.user_id
    assert loaded.chosen_score == trace.chosen_score
    assert len(loaded.alternatives) == 1
    assert loaded.alternatives[0].creative_id == "alt-1"


async def test_archive_writes_all_required_cypher_params():
    """Archive cypher contract — break this test on any param drift."""
    driver = FakeAsyncNeo4jDriver()
    trace = _example_trace()
    await archive_trace_to_neo4j(trace, driver)
    assert len(driver.calls) == 1
    _, params = driver.calls[0]
    expected_keys = {
        "decision_id", "user_id", "chosen_creative_id",
        "chosen_mechanism", "chosen_score", "timestamp_epoch",
        "payload_json", "archived_at_ts", "schema_version",
    }
    assert expected_keys.issubset(params.keys()), (
        f"missing cypher params: {expected_keys - params.keys()}"
    )
    # Scalar field types
    assert isinstance(params["chosen_score"], float)
    assert isinstance(params["timestamp_epoch"], float)
    assert isinstance(params["archived_at_ts"], float)
    assert isinstance(params["payload_json"], str)


async def test_archive_payload_json_round_trips():
    driver = FakeAsyncNeo4jDriver()
    trace = _example_trace()
    await archive_trace_to_neo4j(trace, driver)
    _, params = driver.calls[0]
    rehydrated = DecisionTrace.model_validate_json(params["payload_json"])
    assert rehydrated.decision_id == trace.decision_id
    assert rehydrated.chosen_score == trace.chosen_score


# -----------------------------------------------------------------------------
# Idempotency (MERGE)
# -----------------------------------------------------------------------------


async def test_repeat_archive_overwrites_not_duplicates():
    """Re-archive same decision_id → single trace in driver state
    (last writer wins)."""
    driver = FakeAsyncNeo4jDriver()
    t1 = _example_trace(decision_id="dec-x")
    await archive_trace_to_neo4j(t1, driver)
    assert len(driver.traces) == 1

    # Re-archive with a modified score
    t2 = build_decision_trace(
        decision_id="dec-x",
        user_id=t1.user_id,
        chosen_creative_id=t1.chosen_creative_id,
        chosen_mechanism=t1.chosen_mechanism,
        chosen_score=0.99,  # changed
        timestamp=t1.timestamp,
    )
    await archive_trace_to_neo4j(t2, driver)
    assert len(driver.traces) == 1  # MERGE — no duplicate

    loaded = await load_trace_from_neo4j("dec-x", driver)
    assert loaded.chosen_score == 0.99  # last writer wins


# -----------------------------------------------------------------------------
# Failure paths
# -----------------------------------------------------------------------------


async def test_archive_cypher_failure_returns_false():
    driver = FakeAsyncNeo4jDriver()
    driver.fail_next_run = True
    trace = _example_trace()
    ok = await archive_trace_to_neo4j(trace, driver)
    assert ok is False


async def test_load_cypher_failure_returns_none():
    driver = FakeAsyncNeo4jDriver()
    # Archive normally first
    await archive_trace_to_neo4j(_example_trace(), driver)
    # Now inject a failure for the next run
    driver.fail_next_run = True
    assert (await load_trace_from_neo4j("dec-1", driver)) is None


async def test_load_missing_decision_id_returns_none():
    driver = FakeAsyncNeo4jDriver()
    assert (await load_trace_from_neo4j("never-archived", driver)) is None


async def test_load_bad_payload_json_returns_none():
    driver = FakeAsyncNeo4jDriver()
    # Manually inject corrupt payload
    driver.traces["dec-bad"] = {
        "decision_id": "dec-bad",
        "payload_json": "not-valid-json",
        "user_id": "user-7",
        "timestamp_epoch": 1700000000.0,
    }
    assert (await load_trace_from_neo4j("dec-bad", driver)) is None


async def test_load_handles_bytes_payload():
    driver = FakeAsyncNeo4jDriver()
    trace = _example_trace()
    await archive_trace_to_neo4j(trace, driver)
    # Mutate the stored payload to bytes (simulates some neo4j drivers)
    driver.traces[trace.decision_id]["payload_json"] = (
        trace.model_dump_json().encode("utf-8")
    )
    loaded = await load_trace_from_neo4j(trace.decision_id, driver)
    assert loaded is not None
    assert loaded.decision_id == trace.decision_id


# -----------------------------------------------------------------------------
# List by user
# -----------------------------------------------------------------------------


async def test_list_returns_newest_first():
    driver = FakeAsyncNeo4jDriver()
    base = datetime(2026, 4, 30, 12, 0, 0, tzinfo=timezone.utc)
    from datetime import timedelta
    t1 = _example_trace(decision_id="dec-1", timestamp=base)
    t2 = _example_trace(
        decision_id="dec-2", timestamp=base + timedelta(hours=1),
    )
    t3 = _example_trace(
        decision_id="dec-3", timestamp=base + timedelta(hours=2),
    )
    await archive_trace_to_neo4j(t1, driver)
    await archive_trace_to_neo4j(t2, driver)
    await archive_trace_to_neo4j(t3, driver)

    traces = await list_traces_for_user_from_neo4j("user-7", driver)
    ids = [t.decision_id for t in traces]
    assert ids == ["dec-3", "dec-2", "dec-1"]


async def test_list_respects_limit():
    driver = FakeAsyncNeo4jDriver()
    base = datetime(2026, 4, 30, 12, 0, 0, tzinfo=timezone.utc)
    from datetime import timedelta
    for i in range(8):
        await archive_trace_to_neo4j(
            _example_trace(
                decision_id=f"dec-{i}",
                timestamp=base + timedelta(hours=i),
            ),
            driver,
        )
    traces = await list_traces_for_user_from_neo4j(
        "user-7", driver, limit=3,
    )
    assert len(traces) == 3


async def test_list_zero_limit_returns_empty():
    driver = FakeAsyncNeo4jDriver()
    await archive_trace_to_neo4j(_example_trace(), driver)
    assert (
        await list_traces_for_user_from_neo4j("user-7", driver, limit=0)
    ) == []


async def test_list_empty_user_returns_empty():
    driver = FakeAsyncNeo4jDriver()
    assert (
        await list_traces_for_user_from_neo4j("never-archived-user", driver)
    ) == []


async def test_list_isolates_users():
    driver = FakeAsyncNeo4jDriver()
    base = datetime(2026, 4, 30, 12, 0, 0, tzinfo=timezone.utc)
    await archive_trace_to_neo4j(
        _example_trace(
            decision_id="dec-a", user_id="user-a", timestamp=base,
        ),
        driver,
    )
    await archive_trace_to_neo4j(
        _example_trace(
            decision_id="dec-b", user_id="user-b", timestamp=base,
        ),
        driver,
    )
    a_traces = await list_traces_for_user_from_neo4j("user-a", driver)
    b_traces = await list_traces_for_user_from_neo4j("user-b", driver)
    assert [t.decision_id for t in a_traces] == ["dec-a"]
    assert [t.decision_id for t in b_traces] == ["dec-b"]


async def test_list_skips_unparseable_records():
    """Per-record parse failures don't abort the whole list."""
    driver = FakeAsyncNeo4jDriver()
    await archive_trace_to_neo4j(_example_trace(decision_id="dec-good"), driver)
    # Inject a corrupt record indexed under the same user
    driver.traces["dec-bad"] = {
        "decision_id": "dec-bad",
        "payload_json": "not-valid-json",
        "user_id": "user-7",
        "timestamp_epoch": 1700000001.0,
    }
    driver.user_index["user-7"].append("dec-bad")

    traces = await list_traces_for_user_from_neo4j("user-7", driver)
    ids = [t.decision_id for t in traces]
    assert "dec-good" in ids
    assert "dec-bad" not in ids
