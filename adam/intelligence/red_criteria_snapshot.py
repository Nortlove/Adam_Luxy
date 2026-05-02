# =============================================================================
# RED-criteria producer snapshot — feeds the launch-gate runner
# Location: adam/intelligence/red_criteria_snapshot.py
# =============================================================================
"""In-process accumulator for the launch-gate runner's input counters.

Closes audit Tier 1 #10 (producer side): all 8 RED-criteria check
functions + ``run_launch_gate_evaluation`` aggregator exist, but
6 of 8 input counters had no producer wiring. The directive's
"continuous monitoring (the spine's own observability)" line 1128
was unfulfilled — the launch decision could not be evidenced from
inside the system.

WHY THIS EXISTS
---------------

Prometheus counters (Slice 1 added the fluency-floor ones) are
designed for pull-based observability — they're monotonic across
the process lifetime and don't natively support window deltas. The
launch-gate runner needs WINDOW counts (e.g., "in the last 24h, how
many bids and how many trace emissions"). This module is the small
in-process accumulator the cascade increments on each event, and
the daily Task 42 reads + resets per cycle.

ALSO TRACKED
------------

Bid-time latency p99 — the cascade already computes elapsed_ms per
decision (line 3528 area); we keep a bounded ring buffer of the
most recent N samples so p99 can be computed at snapshot time. Ring
buffer is bounded so unbounded growth is impossible regardless of
cycle length / bid rate.

THE PRIMITIVE
-------------

  * ``RedCriteriaSnapshot`` — thread-safe accumulator dataclass.
    Single process-wide singleton via ``get_red_snapshot()``.
  * ``record_bid()`` — increment bid count.
  * ``record_trace_emission()`` — increment trace count.
  * ``record_floor_violation(n=1)`` — fluency-floor drop event(s).
  * ``record_identity_collapse(n=1)`` — user posterior identity-
    stability collapse signal (sibling slice writes when it lands).
  * ``record_latency_ms(ms)`` — append latency sample to ring buffer.
  * ``snapshot_and_reset()`` — return a ``LaunchGateInputs``-shaped
    dict + atomically reset counters.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Section 9 Phase 10 lines 1130-1138 (8 RED
    criteria); phase_10_launch_sequence.LaunchGateInputs (existing
    aggregator); audit 2026-05-01 Tier 1 #10. The thread-safety
    pattern mirrors decision_trace_emitter's InMemoryDecisionTraceLog
    (single lock around accumulator + bounded buffer).

(b) Tests pin: increments thread-safe; snapshot returns LaunchGate
    Inputs-compatible shape; reset clears counters atomically;
    p99 computed from ring buffer (returns None on empty buffer);
    ring buffer bounded (oldest evicted under pressure); singleton
    via get_red_snapshot().

(c) calibration_pending=False — accumulator semantics are mechanical;
    no pilot-data-dependent constants.

(d) Honest tags — what is NOT in this slice (named successors):

    * Persistent (Redis) snapshot for multi-pod deploy. v0.1 in-
      process accumulator is sufficient for single-pod Railway.
    * cmo_review_disposition / n_creatives_failed_spot_check inputs —
      operational/external signals (CMO review form + offline scorer
      run); the runner stays at "skip-when-no-data" until those
      inputs land.
    * Identity-stability collapse counter producer wire. The
      identity-stability decay function exists at phase_8_stackadapt
      _integration:243 but no scheduled sweep updates user posteriors
      yet. Sibling slice on user-posterior maintenance.
    * Histogram-based p99 (vs. ring-buffer percentile). Ring buffer
      with size N=1000 is adequate for daily snapshot; histogram is
      a sibling slice if granularity matters.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, Optional


# Ring-buffer bound — at LUXY's expected ~250 decisions/hour over 24h
# (=6000), 1000 samples covers the freshest ~6.7% of decisions and is
# more than enough for stable p99. Bounded so memory is safe even at
# 100x rate.
LATENCY_RING_BUFFER_SIZE: int = 1000


@dataclass
class RedCriteriaSnapshot:
    """Thread-safe accumulator for launch-gate input counters."""

    n_bids: int = 0
    n_traces_emitted: int = 0
    n_floor_violations: int = 0
    n_users_active: int = 0
    n_users_with_collapsed_identity_stability: int = 0
    _latency_ring: Deque[float] = field(
        default_factory=lambda: deque(maxlen=LATENCY_RING_BUFFER_SIZE)
    )
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _last_reset_ts: float = field(default_factory=time.time)

    def record_bid(self) -> None:
        with self._lock:
            self.n_bids += 1

    def record_trace_emission(self) -> None:
        with self._lock:
            self.n_traces_emitted += 1

    def record_floor_violation(self, n: int = 1) -> None:
        with self._lock:
            self.n_floor_violations += int(n)

    def record_user_active(self, n: int = 1) -> None:
        with self._lock:
            self.n_users_active += int(n)

    def record_identity_collapse(self, n: int = 1) -> None:
        with self._lock:
            self.n_users_with_collapsed_identity_stability += int(n)

    def record_latency_ms(self, ms: float) -> None:
        if ms is None:
            return
        with self._lock:
            self._latency_ring.append(float(ms))

    def _p99_locked(self) -> Optional[float]:
        """p99 over current ring buffer; None when empty."""
        if not self._latency_ring:
            return None
        sorted_samples = sorted(self._latency_ring)
        n = len(sorted_samples)
        # 99th percentile index (inclusive). For n<100, fall back to
        # max — at n=10 the "99th percentile" is ill-defined but max is
        # the conservative-honest answer (we'll be over-estimating
        # rather than under-estimating latency).
        if n < 100:
            return sorted_samples[-1]
        idx = int(0.99 * n)
        return sorted_samples[idx]

    def snapshot_and_reset(self) -> Dict[str, Any]:
        """Return LaunchGateInputs-compatible dict + reset counters.

        Atomic — caller sees a consistent window over the prior cycle.
        Counters that have value 0 may legitimately appear as 0 in
        the snapshot; the runner uses None-skip semantic, so the
        caller must decide whether to forward 0 vs None to the
        gate (Task 42 forwards 0 for n_floor_violations + n_bids
        only when n_bids > 0 — otherwise the rate calc divides by
        zero — see ``compose_inputs_from_snapshot``).
        """
        with self._lock:
            n_bids = self.n_bids
            n_traces_emitted = self.n_traces_emitted
            n_floor_violations = self.n_floor_violations
            n_users_active = self.n_users_active
            n_users_collapsed = self.n_users_with_collapsed_identity_stability
            p99 = self._p99_locked()
            now = time.time()
            window_seconds = max(0.0, now - self._last_reset_ts)

            # Atomic reset
            self.n_bids = 0
            self.n_traces_emitted = 0
            self.n_floor_violations = 0
            self.n_users_active = 0
            self.n_users_with_collapsed_identity_stability = 0
            self._latency_ring.clear()
            self._last_reset_ts = now

        return {
            "n_bids": n_bids,
            "n_traces_emitted": n_traces_emitted,
            "n_floor_violations": n_floor_violations,
            "n_users_active": n_users_active,
            "n_users_with_collapsed_identity_stability": n_users_collapsed,
            "p99_latency_ms": p99,
            "window_seconds": window_seconds,
        }


# =============================================================================
# Singleton
# =============================================================================


_SNAPSHOT_LOCK = threading.Lock()
_SNAPSHOT: Optional[RedCriteriaSnapshot] = None


def get_red_snapshot() -> RedCriteriaSnapshot:
    """Process-singleton snapshot accumulator. Lazy initialized."""
    global _SNAPSHOT
    if _SNAPSHOT is not None:
        return _SNAPSHOT
    with _SNAPSHOT_LOCK:
        if _SNAPSHOT is None:
            _SNAPSHOT = RedCriteriaSnapshot()
    return _SNAPSHOT


def reset_for_tests() -> None:
    """Test-only — replace singleton with a fresh instance."""
    global _SNAPSHOT
    with _SNAPSHOT_LOCK:
        _SNAPSHOT = RedCriteriaSnapshot()
