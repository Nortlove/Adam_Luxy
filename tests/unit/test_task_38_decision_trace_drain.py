"""Pin Task 38 — DecisionTrace daily drain (Spine #6 operationalization).

Tests pin:
  * Name + schedule_hours (every UTC hour) + frequency_hours (1).
  * Registration in scheduler registry.
  * execute() drains pending traces successfully when both clients
    available.
  * execute() succeeds with at-least-one client (Redis-only or
    Neo4j-only paths).
  * execute() skipped (success=True with details["skipped"]) when
    neither client available — log NOT drained (preserves traces
    for next attempt).
  * execute() returns failed result when drain_to_storage raises.
  * execute() flags failure when both tiers had clients but neither
    wrote any traces (catastrophic).
  * execute() result counters populated (drained / redis_writes_ok /
    neo4j_writes_ok / log_size_before / log_size_after).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest

from adam.intelligence.daily.task_38_decision_trace_drain import (
    DRAIN_BATCH_MAX_ITEMS,
    DecisionTraceDrainTask,
)
from adam.intelligence.decision_trace import (
    AlternativeCandidate,
    DecisionTrace,
    build_decision_trace,
)
from adam.intelligence.decision_trace_emitter import (
    build_trace_from_cascade,
    emit,
    get_log,
    reset_for_tests,
)


def setup_function() -> None:
    reset_for_tests()


# -----------------------------------------------------------------------------
# Fakes — minimal async Redis + async Neo4j drivers
# -----------------------------------------------------------------------------


class _FakeAsyncRedis:
    def __init__(self) -> None:
        self.kv: Dict[str, str] = {}
        self.lists: Dict[str, List[str]] = {}

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> None:
        self.kv[key] = value

    async def get(self, key: str) -> Optional[str]:
        return self.kv.get(key)

    async def lpush(self, key: str, *values: Any) -> int:
        self.lists.setdefault(key, [])
        for v in values:
            self.lists[key].insert(0, str(v))
        return len(self.lists[key])

    async def ltrim(self, key: str, start: int, stop: int) -> None:
        if key in self.lists:
            self.lists[key] = self.lists[key][start: stop + 1]

    async def lrange(self, key: str, start: int, stop: int) -> List[str]:
        items = self.lists.get(key, [])
        if stop == -1:
            return items[start:]
        return items[start: stop + 1]

    async def expire(self, key: str, seconds: int) -> None:
        return None


class _FakeAsyncSession:
    def __init__(self) -> None:
        self.calls: List = []

    async def __aenter__(self) -> "_FakeAsyncSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def run(self, cypher: str, **params: Any) -> Any:
        self.calls.append((cypher, dict(params)))

        class _R:
            async def single(self_inner) -> None:
                return None

            def __aiter__(self_inner):
                async def _g():
                    return
                    yield  # noqa
                return _g()

        return _R()


class _FakeAsyncNeo4j:
    def __init__(self) -> None:
        self._session = _FakeAsyncSession()

    def session(self) -> _FakeAsyncSession:
        return self._session


class _FakeInfra:
    """Substitutes Infrastructure for the test."""

    def __init__(
        self,
        redis_client: Optional[_FakeAsyncRedis] = None,
        neo4j_driver: Optional[_FakeAsyncNeo4j] = None,
    ) -> None:
        self._redis = redis_client
        self._neo4j = neo4j_driver

    @property
    def redis(self) -> _FakeAsyncRedis:
        if self._redis is None:
            raise RuntimeError("redis not configured")
        return self._redis

    @property
    def neo4j(self) -> _FakeAsyncNeo4j:
        if self._neo4j is None:
            raise RuntimeError("neo4j not configured")
        return self._neo4j


def _example_kwargs() -> dict:
    """Minimal kwargs for build_trace_from_cascade."""
    class _FakeCI:
        mechanism_scores = {"social_proof": 0.9, "authority": 0.5}

    return {
        "decision_id": "dec-1",
        "user_id": "user-7",
        "archetype": "achiever",
        "category": "luxury",
        "cascade_result": _FakeCI(),
        "chosen_mechanism": "social_proof",
        "p_t": 0.985,
    }


# -----------------------------------------------------------------------------
# Schedule + identity pinned
# -----------------------------------------------------------------------------


def test_task_name_pinned():
    task = DecisionTraceDrainTask()
    assert task.name == "decision_trace_drain"


def test_task_schedule_is_every_hour():
    task = DecisionTraceDrainTask()
    assert task.schedule_hours == list(range(24))
    assert task.frequency_hours == 1


def test_drain_batch_max_default_pinned():
    """A14 default — change requires explicit calibration update."""
    assert DRAIN_BATCH_MAX_ITEMS == 10_000


# -----------------------------------------------------------------------------
# Registration in scheduler
# -----------------------------------------------------------------------------


def test_task_38_registers_in_scheduler():
    """Task 38 MUST appear in the scheduler registry under
    'decision_trace_drain'. Without this, the drain consumer never
    runs and Spine #6 storage stays empty."""
    import adam.intelligence.daily.scheduler as scheduler_mod
    scheduler_mod._task_registry.clear()
    registry = scheduler_mod.get_task_registry()
    assert "decision_trace_drain" in registry


# -----------------------------------------------------------------------------
# Execute — both clients available
# -----------------------------------------------------------------------------


async def test_execute_drains_with_both_clients():
    reset_for_tests()
    for i in range(3):
        kw = _example_kwargs()
        kw["decision_id"] = f"dec-{i}"
        emit(build_trace_from_cascade(**kw))

    redis = _FakeAsyncRedis()
    neo4j = _FakeAsyncNeo4j()
    infra = _FakeInfra(redis_client=redis, neo4j_driver=neo4j)

    async def _fake_get_infra():
        return infra

    with patch(
        "adam.core.dependencies.get_infrastructure",
        side_effect=_fake_get_infra,
    ):
        task = DecisionTraceDrainTask()
        result = await task.execute()

    assert result.success is True
    assert result.items_processed == 3
    assert result.details["drained"] == 3
    assert result.details["redis_writes_ok"] == 3
    assert result.details["neo4j_writes_ok"] == 3
    assert result.details["log_size_before"] == 3
    assert result.details["log_size_after"] == 0
    assert result.details["redis_available"] is True
    assert result.details["neo4j_available"] is True


# -----------------------------------------------------------------------------
# Partial-availability paths
# -----------------------------------------------------------------------------


async def test_execute_succeeds_with_redis_only():
    """Redis-only: still drain (one tier write satisfies)."""
    reset_for_tests()
    kw = _example_kwargs()
    emit(build_trace_from_cascade(**kw))

    redis = _FakeAsyncRedis()
    infra = _FakeInfra(redis_client=redis, neo4j_driver=None)

    async def _fake_get_infra():
        return infra

    with patch(
        "adam.core.dependencies.get_infrastructure",
        side_effect=_fake_get_infra,
    ):
        task = DecisionTraceDrainTask()
        result = await task.execute()

    assert result.success is True
    assert result.details["drained"] == 1
    assert result.details["redis_writes_ok"] == 1
    assert result.details["neo4j_writes_ok"] == 0
    assert result.details["redis_available"] is True
    assert result.details["neo4j_available"] is False


async def test_execute_succeeds_with_neo4j_only():
    """Neo4j-only: still drain (one tier write satisfies)."""
    reset_for_tests()
    kw = _example_kwargs()
    emit(build_trace_from_cascade(**kw))

    neo4j = _FakeAsyncNeo4j()
    infra = _FakeInfra(redis_client=None, neo4j_driver=neo4j)

    async def _fake_get_infra():
        return infra

    with patch(
        "adam.core.dependencies.get_infrastructure",
        side_effect=_fake_get_infra,
    ):
        task = DecisionTraceDrainTask()
        result = await task.execute()

    assert result.success is True
    assert result.details["drained"] == 1
    assert result.details["redis_writes_ok"] == 0
    assert result.details["neo4j_writes_ok"] == 1


# -----------------------------------------------------------------------------
# No-client skip path — preserves traces for next attempt
# -----------------------------------------------------------------------------


async def test_execute_skipped_when_no_clients_available():
    """When neither Redis nor Neo4j is reachable, the task does NOT
    drain — pulling traces out of the in-memory log without anywhere
    to write them would lose data. Wait for next cycle."""
    reset_for_tests()
    kw = _example_kwargs()
    emit(build_trace_from_cascade(**kw))

    infra = _FakeInfra(redis_client=None, neo4j_driver=None)

    async def _fake_get_infra():
        return infra

    with patch(
        "adam.core.dependencies.get_infrastructure",
        side_effect=_fake_get_infra,
    ):
        task = DecisionTraceDrainTask()
        result = await task.execute()

    assert result.success is True  # not a failure — just skipped
    assert result.details["skipped"] == "no_storage_clients"
    assert result.details["log_size_at_skip"] == 1
    # Log preserved — trace still queued for next attempt
    assert len(get_log()) == 1


async def test_execute_skipped_when_infrastructure_unavailable():
    """Infrastructure import / instance failure → skipped, not failed."""
    reset_for_tests()
    kw = _example_kwargs()
    emit(build_trace_from_cascade(**kw))

    async def _boom():
        raise RuntimeError("infra unavailable")

    with patch(
        "adam.core.dependencies.get_infrastructure",
        side_effect=_boom,
    ):
        task = DecisionTraceDrainTask()
        result = await task.execute()

    # Infra unavailable → no clients → skipped
    assert result.success is True
    assert result.details["skipped"] == "no_storage_clients"
    assert len(get_log()) == 1


# -----------------------------------------------------------------------------
# Failure paths
# -----------------------------------------------------------------------------


async def test_execute_returns_failed_when_drain_raises():
    """drain_to_storage exception → result.success=False with error."""
    reset_for_tests()
    kw = _example_kwargs()
    emit(build_trace_from_cascade(**kw))

    redis = _FakeAsyncRedis()
    infra = _FakeInfra(redis_client=redis, neo4j_driver=None)

    async def _fake_get_infra():
        return infra

    async def _raising_drain(**kwargs):
        raise RuntimeError("simulated drain failure")

    with patch(
        "adam.core.dependencies.get_infrastructure",
        side_effect=_fake_get_infra,
    ), patch(
        "adam.intelligence.decision_trace_emitter.drain_to_storage",
        side_effect=_raising_drain,
    ):
        task = DecisionTraceDrainTask()
        result = await task.execute()

    assert result.success is False
    assert "drain_to_storage failed" in result.details["error"]


async def test_execute_flags_catastrophic_when_both_tiers_fail_all_writes():
    """Both clients available but BOTH wrote zero out of N drained →
    failed. This catches pathological storage failures (e.g., schema
    mismatch, auth expired) that the per-trace soft-fail can't surface."""
    reset_for_tests()
    for i in range(3):
        kw = _example_kwargs()
        kw["decision_id"] = f"dec-{i}"
        emit(build_trace_from_cascade(**kw))

    redis = _FakeAsyncRedis()
    neo4j = _FakeAsyncNeo4j()
    infra = _FakeInfra(redis_client=redis, neo4j_driver=neo4j)

    async def _fake_get_infra():
        return infra

    async def _zero_drain(**kwargs):
        # Drain pops 3 traces from log but writes 0 to each tier
        from adam.intelligence.decision_trace_emitter import get_log
        items = get_log().drain(max_items=10)
        return (len(items), 0, 0)

    with patch(
        "adam.core.dependencies.get_infrastructure",
        side_effect=_fake_get_infra,
    ), patch(
        "adam.intelligence.decision_trace_emitter.drain_to_storage",
        side_effect=_zero_drain,
    ):
        task = DecisionTraceDrainTask()
        result = await task.execute()

    assert result.success is False
    assert "both storage tiers wrote zero" in result.details["error"]


# -----------------------------------------------------------------------------
# Empty-log path
# -----------------------------------------------------------------------------


async def test_execute_empty_log_returns_zero_counters():
    """No traces queued → drain returns 0/0/0; success=True."""
    reset_for_tests()

    redis = _FakeAsyncRedis()
    neo4j = _FakeAsyncNeo4j()
    infra = _FakeInfra(redis_client=redis, neo4j_driver=neo4j)

    async def _fake_get_infra():
        return infra

    with patch(
        "adam.core.dependencies.get_infrastructure",
        side_effect=_fake_get_infra,
    ):
        task = DecisionTraceDrainTask()
        result = await task.execute()

    assert result.success is True
    assert result.items_processed == 0
    assert result.details["drained"] == 0
    assert result.details["redis_writes_ok"] == 0
    assert result.details["neo4j_writes_ok"] == 0
