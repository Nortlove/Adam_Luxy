"""Pin Slice 8 — RED-criteria snapshot accumulator (producer side).

Discipline anchors (B3-LUXY a/b/c/d) for
``adam/intelligence/red_criteria_snapshot.py``:

    (a) Per audit Tier 1 #10: 6 of 8 RED-criteria producers were
        absent. This in-process accumulator is the producer the
        cascade increments per event so daily Task 42 can compute
        rates per cycle.

    (b) Boundary anchors pinned by these tests:
          - Singleton via get_red_snapshot() — same instance each call
          - reset_for_tests() yields a fresh accumulator
          - record_bid / record_trace_emission / record_floor_violation
            increment the right counters
          - record_latency_ms appends to ring buffer; bounded by
            LATENCY_RING_BUFFER_SIZE
          - snapshot_and_reset returns LaunchGateInputs-shaped dict
          - snapshot_and_reset is atomic (counters reset to zero)
          - p99 returns None on empty buffer
          - p99 returns max for n<100 (conservative-honest)
          - p99 computed correctly for n>=100
          - window_seconds populated and increases monotonically
            between snapshots

    (c) calibration_pending=False — accumulator semantics are mechanical.

    (d) Honest tags — what is NOT tested here:
          - Persistent (Redis) snapshot for multi-pod deploy (sibling)
          - cmo_review / metaphor_coherence input producers (sibling)
          - Identity-stability collapse counter producer (sibling)
"""

from __future__ import annotations

import threading
import time

import pytest

from adam.intelligence.red_criteria_snapshot import (
    LATENCY_RING_BUFFER_SIZE,
    RedCriteriaSnapshot,
    get_red_snapshot,
    reset_for_tests,
)


# -----------------------------------------------------------------------------
# Singleton
# -----------------------------------------------------------------------------


def test_singleton_same_instance():
    reset_for_tests()
    a = get_red_snapshot()
    b = get_red_snapshot()
    assert a is b


def test_reset_for_tests_yields_fresh_instance():
    a = get_red_snapshot()
    a.record_bid()
    reset_for_tests()
    b = get_red_snapshot()
    # New singleton — counters back to zero
    assert b.n_bids == 0
    # Different instance from before
    assert a is not b


# -----------------------------------------------------------------------------
# Increment semantics
# -----------------------------------------------------------------------------


def test_record_bid_increments():
    reset_for_tests()
    snap = get_red_snapshot()
    snap.record_bid()
    snap.record_bid()
    snap.record_bid()
    assert snap.n_bids == 3


def test_record_trace_emission_increments():
    reset_for_tests()
    snap = get_red_snapshot()
    snap.record_trace_emission()
    snap.record_trace_emission()
    assert snap.n_traces_emitted == 2


def test_record_floor_violation_with_count():
    reset_for_tests()
    snap = get_red_snapshot()
    snap.record_floor_violation(3)
    snap.record_floor_violation()  # default n=1
    assert snap.n_floor_violations == 4


def test_record_identity_collapse():
    reset_for_tests()
    snap = get_red_snapshot()
    snap.record_identity_collapse(5)
    assert snap.n_users_with_collapsed_identity_stability == 5


def test_record_latency_appends_to_ring():
    reset_for_tests()
    snap = get_red_snapshot()
    snap.record_latency_ms(10.0)
    snap.record_latency_ms(20.0)
    snap.record_latency_ms(30.0)
    assert len(snap._latency_ring) == 3


def test_record_latency_bounded_by_ring_size():
    reset_for_tests()
    snap = get_red_snapshot()
    for i in range(LATENCY_RING_BUFFER_SIZE + 100):
        snap.record_latency_ms(float(i))
    # Bounded — should not exceed buffer size
    assert len(snap._latency_ring) == LATENCY_RING_BUFFER_SIZE
    # Oldest evicted — buffer holds the most recent N
    assert min(snap._latency_ring) == 100.0


def test_record_latency_none_ignored():
    reset_for_tests()
    snap = get_red_snapshot()
    snap.record_latency_ms(None)  # type: ignore[arg-type]
    assert len(snap._latency_ring) == 0


# -----------------------------------------------------------------------------
# Snapshot + reset atomicity
# -----------------------------------------------------------------------------


def test_snapshot_returns_launch_gate_inputs_shape():
    reset_for_tests()
    snap = get_red_snapshot()
    snap.record_bid()
    snap.record_bid()
    snap.record_trace_emission()
    snap.record_floor_violation(1)
    snap.record_latency_ms(50.0)
    out = snap.snapshot_and_reset()
    assert out["n_bids"] == 2
    assert out["n_traces_emitted"] == 1
    assert out["n_floor_violations"] == 1
    assert out["p99_latency_ms"] == 50.0
    assert "window_seconds" in out
    assert out["window_seconds"] >= 0.0


def test_snapshot_and_reset_clears_counters():
    reset_for_tests()
    snap = get_red_snapshot()
    snap.record_bid()
    snap.record_trace_emission()
    snap.record_floor_violation(2)
    snap.record_latency_ms(10.0)
    snap.snapshot_and_reset()
    # All counters back to zero
    assert snap.n_bids == 0
    assert snap.n_traces_emitted == 0
    assert snap.n_floor_violations == 0
    assert len(snap._latency_ring) == 0


def test_snapshot_window_seconds_increases_between_calls():
    reset_for_tests()
    snap = get_red_snapshot()
    out1 = snap.snapshot_and_reset()
    time.sleep(0.05)  # 50ms
    out2 = snap.snapshot_and_reset()
    assert out2["window_seconds"] >= 0.04  # at least the sleep


# -----------------------------------------------------------------------------
# p99 semantics
# -----------------------------------------------------------------------------


def test_p99_none_on_empty():
    snap = RedCriteriaSnapshot()
    out = snap.snapshot_and_reset()
    assert out["p99_latency_ms"] is None


def test_p99_returns_max_for_small_n():
    snap = RedCriteriaSnapshot()
    for v in [10.0, 20.0, 30.0]:
        snap.record_latency_ms(v)
    out = snap.snapshot_and_reset()
    # n < 100 → conservative-honest: return max
    assert out["p99_latency_ms"] == 30.0


def test_p99_computed_correctly_for_large_n():
    snap = RedCriteriaSnapshot()
    # 0..199 → p99 should be ~ 198 (index 0.99*200 = 198)
    for v in range(200):
        snap.record_latency_ms(float(v))
    out = snap.snapshot_and_reset()
    # p99 index = int(0.99 * 200) = 198 → value 198.0
    assert out["p99_latency_ms"] == 198.0


# -----------------------------------------------------------------------------
# Thread safety
# -----------------------------------------------------------------------------


def test_concurrent_record_bid_thread_safe():
    reset_for_tests()
    snap = get_red_snapshot()

    def _bump():
        for _ in range(1000):
            snap.record_bid()

    threads = [threading.Thread(target=_bump) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert snap.n_bids == 4000
