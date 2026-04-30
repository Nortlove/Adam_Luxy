"""Pin Spine #6 Redis hot-cache substrate — directive line 248.

Tests pin:
  * Round-trip via in-memory async fake Redis preserves trace.
  * TTL is set via Redis SET ex= argument.
  * Missing decision_id → load returns None.
  * Soft-fail: no redis_client → store returns False, load returns
    None, list returns [].
  * Bad JSON in Redis → load returns None (not raises).
  * Multiple traces same user retrievable in newest-first order.
  * User index trim cap honored (USER_INDEX_MAX_LENGTH).
  * Index update failure does not roll back primary write.
  * limit on list_traces_for_user enforced.
  * Key prefix discipline pinned (schema lock).
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
from adam.intelligence.decision_trace_store import (
    DEFAULT_TRACE_TTL_SECONDS,
    USER_INDEX_MAX_LENGTH,
    USER_INDEX_TTL_SECONDS,
    list_traces_for_user,
    load_trace,
    primary_key,
    store_trace,
    user_index_key,
)


# -----------------------------------------------------------------------------
# In-memory async fake Redis (just the surface we use)
# -----------------------------------------------------------------------------


class FakeAsyncRedis:
    """Minimal async Redis double covering set/get/lpush/ltrim/lrange/expire.

    Implements only the surface decision_trace_store uses. ``ex`` /
    ``expire`` arguments are recorded for inspection — the fake does
    not actually evict on TTL (tests pin that the call was made, not
    that eviction happened).
    """

    def __init__(self) -> None:
        self.kv: Dict[str, str] = {}
        self.lists: Dict[str, List[str]] = {}
        self.ttls: Dict[str, int] = {}
        # For fault-injection on specific keys
        self.fail_on_set: Optional[str] = None
        self.fail_on_lpush: Optional[str] = None

    async def set(
        self, key: str, value: str, ex: Optional[int] = None,
    ) -> None:
        if self.fail_on_set and key == self.fail_on_set:
            raise RuntimeError("fault-injected set failure")
        self.kv[key] = value
        if ex is not None:
            self.ttls[key] = int(ex)

    async def get(self, key: str) -> Optional[str]:
        return self.kv.get(key)

    async def lpush(self, key: str, *values: Any) -> int:
        if self.fail_on_lpush and key == self.fail_on_lpush:
            raise RuntimeError("fault-injected lpush failure")
        if key not in self.lists:
            self.lists[key] = []
        for v in values:
            self.lists[key].insert(0, str(v))
        return len(self.lists[key])

    async def ltrim(self, key: str, start: int, stop: int) -> None:
        if key not in self.lists:
            return
        # Redis ltrim semantics: keep the slice [start..stop] inclusive
        self.lists[key] = self.lists[key][start: stop + 1]

    async def lrange(self, key: str, start: int, stop: int) -> List[str]:
        items = self.lists.get(key, [])
        # Redis lrange semantics: inclusive stop, negative indexes allowed
        if stop == -1:
            return items[start:]
        return items[start: stop + 1]

    async def expire(self, key: str, seconds: int) -> None:
        self.ttls[key] = int(seconds)


def _example_trace(decision_id: str = "dec-1", user_id: str = "user-7") -> DecisionTrace:
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
        timestamp=datetime(2026, 4, 30, 12, 0, 0, tzinfo=timezone.utc),
    )


# -----------------------------------------------------------------------------
# Key schema discipline
# -----------------------------------------------------------------------------


def test_primary_key_schema_pinned():
    """Key prefix is part of the operational contract — log queries
    and dashboards depend on it. Drift requires deliberate update."""
    assert primary_key("dec-1") == "decision_trace:dec-1"


def test_user_index_key_schema_pinned():
    assert user_index_key("user-7") == "decision_trace_user_idx:user-7"


# -----------------------------------------------------------------------------
# Soft-fail without client
# -----------------------------------------------------------------------------


async def test_store_trace_no_client_returns_false():
    trace = _example_trace()
    assert (await store_trace(trace, redis_client=None)) is False


async def test_load_trace_no_client_returns_none():
    assert (await load_trace("dec-1", redis_client=None)) is None


async def test_list_traces_no_client_returns_empty():
    assert (await list_traces_for_user("user-7", redis_client=None)) == []


# -----------------------------------------------------------------------------
# Round-trip
# -----------------------------------------------------------------------------


async def test_store_then_load_round_trip():
    redis = FakeAsyncRedis()
    trace = _example_trace()
    ok = await store_trace(trace, redis)
    assert ok is True

    loaded = await load_trace(trace.decision_id, redis)
    assert loaded is not None
    assert loaded.decision_id == trace.decision_id
    assert loaded.user_id == trace.user_id
    assert loaded.chosen_score == trace.chosen_score
    assert len(loaded.alternatives) == 1
    assert loaded.alternatives[0].creative_id == "alt-1"


async def test_store_sets_default_ttl():
    redis = FakeAsyncRedis()
    trace = _example_trace()
    await store_trace(trace, redis)
    pkey = primary_key(trace.decision_id)
    assert pkey in redis.ttls
    assert redis.ttls[pkey] == DEFAULT_TRACE_TTL_SECONDS


async def test_store_sets_custom_ttl():
    redis = FakeAsyncRedis()
    trace = _example_trace()
    await store_trace(trace, redis, ttl_seconds=3600)
    pkey = primary_key(trace.decision_id)
    assert redis.ttls[pkey] == 3600


async def test_store_sets_user_index_ttl():
    redis = FakeAsyncRedis()
    trace = _example_trace()
    await store_trace(trace, redis)
    ikey = user_index_key(trace.user_id)
    assert ikey in redis.ttls
    assert redis.ttls[ikey] == USER_INDEX_TTL_SECONDS


# -----------------------------------------------------------------------------
# Missing key / bad payload
# -----------------------------------------------------------------------------


async def test_load_missing_returns_none():
    redis = FakeAsyncRedis()
    assert (await load_trace("missing-id", redis)) is None


async def test_load_bad_json_returns_none():
    redis = FakeAsyncRedis()
    redis.kv[primary_key("dec-bad")] = "not-valid-json-{"
    result = await load_trace("dec-bad", redis)
    assert result is None


async def test_load_partial_json_missing_required_field_returns_none():
    redis = FakeAsyncRedis()
    redis.kv[primary_key("dec-bad-shape")] = '{"decision_id": "x"}'
    result = await load_trace("dec-bad-shape", redis)
    assert result is None  # missing required fields


async def test_load_handles_bytes_payload():
    """Some Redis clients return bytes; the loader must decode."""
    redis = FakeAsyncRedis()
    trace = _example_trace()
    redis.kv[primary_key(trace.decision_id)] = trace.model_dump_json()
    # Inject bytes manually
    redis.kv[primary_key(trace.decision_id)] = (
        trace.model_dump_json().encode("utf-8")
    )
    loaded = await load_trace(trace.decision_id, redis)
    assert loaded is not None
    assert loaded.decision_id == trace.decision_id


# -----------------------------------------------------------------------------
# User index — listing + ordering
# -----------------------------------------------------------------------------


async def test_list_traces_returns_newest_first():
    redis = FakeAsyncRedis()
    t1 = _example_trace(decision_id="dec-1")
    t2 = _example_trace(decision_id="dec-2")
    t3 = _example_trace(decision_id="dec-3")
    await store_trace(t1, redis)
    await store_trace(t2, redis)
    await store_trace(t3, redis)

    traces = await list_traces_for_user(t1.user_id, redis)
    ids = [t.decision_id for t in traces]
    # lpush sequence: t3 newest at head → t3, t2, t1
    assert ids == ["dec-3", "dec-2", "dec-1"]


async def test_list_traces_respects_limit():
    redis = FakeAsyncRedis()
    for i in range(10):
        await store_trace(_example_trace(decision_id=f"dec-{i}"), redis)
    traces = await list_traces_for_user("user-7", redis, limit=3)
    assert len(traces) == 3


async def test_list_traces_caps_limit_at_index_max():
    """limit > USER_INDEX_MAX_LENGTH is silently capped."""
    redis = FakeAsyncRedis()
    await store_trace(_example_trace(decision_id="dec-x"), redis)
    # Caller asks for a million — should not blow up; capped at MAX.
    traces = await list_traces_for_user("user-7", redis, limit=10**6)
    assert len(traces) == 1


async def test_list_traces_zero_limit_returns_empty():
    redis = FakeAsyncRedis()
    await store_trace(_example_trace(decision_id="dec-x"), redis)
    assert (await list_traces_for_user("user-7", redis, limit=0)) == []


async def test_list_traces_empty_user_returns_empty():
    redis = FakeAsyncRedis()
    assert (await list_traces_for_user("no-such-user", redis)) == []


async def test_list_traces_skips_missing_primaries():
    """An index entry whose primary has TTL'd out → silently skipped."""
    redis = FakeAsyncRedis()
    t1 = _example_trace(decision_id="dec-real")
    t2 = _example_trace(decision_id="dec-ghost")
    await store_trace(t1, redis)
    await store_trace(t2, redis)
    # Manually delete the ghost's primary, leave it in the index
    del redis.kv[primary_key("dec-ghost")]
    traces = await list_traces_for_user("user-7", redis)
    assert [t.decision_id for t in traces] == ["dec-real"]


# -----------------------------------------------------------------------------
# Index trim cap
# -----------------------------------------------------------------------------


async def test_index_trims_to_max_length():
    """Pushing more than USER_INDEX_MAX_LENGTH ids triggers ltrim."""
    redis = FakeAsyncRedis()
    # Push USER_INDEX_MAX_LENGTH + 5 ids — index list must end at MAX.
    n = USER_INDEX_MAX_LENGTH + 5
    for i in range(n):
        await store_trace(_example_trace(decision_id=f"dec-{i}"), redis)
    ikey = user_index_key("user-7")
    assert len(redis.lists[ikey]) == USER_INDEX_MAX_LENGTH


# -----------------------------------------------------------------------------
# Failure isolation between primary and index
# -----------------------------------------------------------------------------


async def test_index_failure_does_not_rollback_primary():
    """Primary already wrote; an index lpush exception still returns
    True. The trace is reachable via direct decision_id load."""
    redis = FakeAsyncRedis()
    trace = _example_trace()
    redis.fail_on_lpush = user_index_key(trace.user_id)
    ok = await store_trace(trace, redis)
    assert ok is True
    loaded = await load_trace(trace.decision_id, redis)
    assert loaded is not None
    assert loaded.decision_id == trace.decision_id


async def test_primary_failure_returns_false():
    redis = FakeAsyncRedis()
    trace = _example_trace()
    redis.fail_on_set = primary_key(trace.decision_id)
    ok = await store_trace(trace, redis)
    assert ok is False
    # No primary written; load returns None
    loaded = await load_trace(trace.decision_id, redis)
    assert loaded is None


# -----------------------------------------------------------------------------
# Module constant regression — pin the directive's calibration window
# -----------------------------------------------------------------------------


def test_default_trace_ttl_inside_directive_window():
    """Directive line 248: TTL within 7-30 days. Default must respect."""
    assert 7 * 86400 <= DEFAULT_TRACE_TTL_SECONDS <= 30 * 86400


def test_user_index_ttl_at_least_as_long_as_primary():
    """Index TTL must outlast primary TTL so traces aren't unreachable
    via the index after their direct keys expire."""
    assert USER_INDEX_TTL_SECONDS >= DEFAULT_TRACE_TTL_SECONDS
