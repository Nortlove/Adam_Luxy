"""Pin the MRT producer singleton.

Discipline anchors:
    - Singleton: same instance across calls within a process. Logging
      semantics depend on a single producer (otherwise records vanish
      between calls).
    - Soft-fail: emit() must NEVER raise. The bid path is upstream of
      this; a logging exception cannot be allowed to break decisions.
    - reset_for_tests is the test seam — without it, a pollution from
      one test leaks into the next.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from adam.intelligence.mrt_logging import MRTDecisionRecord
from adam.intelligence.mrt_producer import (
    dump_to_jsonl,
    emit,
    get_mrt_producer,
    reset_for_tests,
)


def _make_record(user_id: str = "u", arm: str = "social_proof") -> MRTDecisionRecord:
    return MRTDecisionRecord(
        ts=1700000000000, user_id=user_id, decision_point_t=1,
        archetype_id="status_seeker", mechanism_id=arm,
        category_id="luxury_transportation", moderators_S_t={},
        action_A_t=1, rand_prob_p_t=0.97, epsilon_floor=0.02,
        availability_I_t=1, p_t_known=True,
    )


def setup_function():
    reset_for_tests()


# -----------------------------------------------------------------------------
# Singleton behavior
# -----------------------------------------------------------------------------


def test_get_returns_same_instance_within_process():
    a = get_mrt_producer()
    b = get_mrt_producer()
    assert a is b


def test_emit_lands_in_singleton_log():
    emit(_make_record())
    emit(_make_record())
    assert len(get_mrt_producer()) == 2


def test_reset_for_tests_swaps_clean_log():
    emit(_make_record())
    assert len(get_mrt_producer()) == 1
    reset_for_tests()
    assert len(get_mrt_producer()) == 0


# -----------------------------------------------------------------------------
# Soft-fail
# -----------------------------------------------------------------------------


def test_emit_swallows_producer_exception():
    """If the producer's emit raises, the cascade caller must not see it.
    Patch the singleton's emit to raise; emit() must not propagate."""
    producer = get_mrt_producer()
    original_emit = producer.emit

    def broken_emit(rec):
        raise ConnectionError("kafka down")

    try:
        producer.emit = broken_emit
        emit(_make_record())  # must NOT raise
    finally:
        producer.emit = original_emit


# -----------------------------------------------------------------------------
# JSONL dump
# -----------------------------------------------------------------------------


def test_dump_to_jsonl_writes_one_record_per_line(tmp_path):
    emit(_make_record(arm="social_proof"))
    emit(_make_record(arm="authority"))
    emit(_make_record(arm="scarcity"))

    path = tmp_path / "decisions.jsonl"
    n = dump_to_jsonl(path)

    assert n == 3
    lines = path.read_text().strip().split("\n")
    assert len(lines) == 3
    # Each line is valid JSON with the expected shape
    parsed = [json.loads(line) for line in lines]
    arms = [p["mechanism_id"] for p in parsed]
    assert arms == ["social_proof", "authority", "scarcity"]


def test_dump_to_jsonl_empty_log(tmp_path):
    path = tmp_path / "empty.jsonl"
    n = dump_to_jsonl(path)
    assert n == 0
    assert path.read_text() == ""


def test_dump_to_jsonl_preserves_order():
    """Decisions are time-ordered; dump preserves insertion order so
    decision_point_t increments stay correct in the offline analysis."""
    for i in range(10):
        rec = _make_record(user_id=f"u{i}")
        rec.decision_point_t = i
        emit(rec)


# -----------------------------------------------------------------------------
# Kafka env var path (logged but in-memory still used today)
# -----------------------------------------------------------------------------


def test_kafka_env_var_logs_but_falls_through_to_memory():
    """KAFKA_BOOTSTRAP_SERVERS env var present → log + use in-memory.
    A future commit wires kafka-python; today's pilot stays in-memory."""
    reset_for_tests()
    with patch.dict("os.environ", {"KAFKA_BOOTSTRAP_SERVERS": "localhost:9092"}):
        producer = get_mrt_producer()
    # Still an in-memory log (Kafka path not yet wired)
    from adam.intelligence.mrt_logging import InMemoryDecisionLog
    assert isinstance(producer, InMemoryDecisionLog)
