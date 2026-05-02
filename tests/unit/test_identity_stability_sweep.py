"""Pin Slice 16 — identity-stability collapse sweep primitive.

Closes the named sibling tag from
task_42_launch_gate_runner.py:43-46 — RED criterion #4 producer.

Discipline anchors (B3-LUXY a/b/c/d):

    (a) Citations: directive Section 9 Phase 10 lines 1131-1138 (RED
        criterion #4 — identity-stability collapse > 30%);
        task_42_launch_gate_runner.py:43-46 (named sibling); decay
        primitive from phase_8_stackadapt_integration.

    (b) Boundary anchors:
          - empty cache → n_active=0 + n_collapsed=0
          - fresh-touch buyer (Δ=0d) → not collapsed
          - old buyer (Δ=200d at 2%/day) → collapsed
          - lookback filter excludes Δ > LOOKBACK_DAYS
          - anonymous buyers (empty buyer_id) excluded
          - snapshot record_user_active + record_identity_collapse
            incremented when n_active > 0
          - soft-fail when no decision_cache
          - IdentityStabilitySweepResult frozen
          - per_buyer populated only when include_per_buyer=True

    (c) calibration_pending=True. Default threshold (0.05),
        initial stability (1.0), lookback (30d) — all conservative
        pre-pilot.

    (d) Honest tags — what is NOT tested here:
          - Persistent per-user identity_stability storage
          - Multi-pod sweep (Redis-backed)
          - Per-cohort attrition_per_day calibration
"""

from __future__ import annotations

import math
import time
from typing import Any, List
from unittest.mock import MagicMock

import pytest

from adam.intelligence.identity_stability_sweep import (
    IDENTITY_STABILITY_COLLAPSE_THRESHOLD,
    IDENTITY_STABILITY_DEFAULT_INITIAL,
    IDENTITY_STABILITY_LOOKBACK_DAYS,
    IdentityStabilitySweepResult,
    compute_decayed_stability,
    is_identity_collapsed,
    sweep_active_buyers,
)


# -----------------------------------------------------------------------------
# Fakes
# -----------------------------------------------------------------------------


class _FakeContext:
    def __init__(self, buyer_id: str, created_at: float) -> None:
        self.buyer_id = buyer_id
        self.created_at = created_at


class _FakeCache:
    """Minimal duck-type matching DecisionCache._store iteration."""

    def __init__(self, contexts: List[_FakeContext]) -> None:
        # OrderedDict-like; values() iteration is what the sweep uses.
        self._store = {f"d{i}": c for i, c in enumerate(contexts)}


class _FakeSnapshot:
    def __init__(self) -> None:
        self.user_active_calls: List[int] = []
        self.collapse_calls: List[int] = []

    def record_user_active(self, n: int = 1) -> None:
        self.user_active_calls.append(int(n))

    def record_identity_collapse(self, n: int = 1) -> None:
        self.collapse_calls.append(int(n))


# -----------------------------------------------------------------------------
# compute_decayed_stability
# -----------------------------------------------------------------------------


def test_decayed_stability_at_zero_days_unchanged():
    out = compute_decayed_stability(days_since_last_seen=0.0)
    assert out == 1.0


def test_decayed_stability_decays_per_day():
    """At 2%/day default, 50 days → 0.98^50 ≈ 0.364."""
    out = compute_decayed_stability(days_since_last_seen=50.0)
    expected = 0.98 ** 50
    assert out == pytest.approx(expected, rel=1e-9)


def test_decayed_stability_negative_days_treated_as_zero():
    """Defensive — clock skew → no decay applied."""
    out = compute_decayed_stability(days_since_last_seen=-5.0)
    assert out == 1.0


def test_decayed_stability_custom_initial():
    out = compute_decayed_stability(
        days_since_last_seen=10.0,
        initial_stability=0.5,
    )
    assert out == pytest.approx(0.5 * (0.98 ** 10), rel=1e-9)


def test_decayed_stability_custom_attrition():
    out = compute_decayed_stability(
        days_since_last_seen=10.0,
        attrition_per_day=0.05,
    )
    assert out == pytest.approx(0.95 ** 10, rel=1e-9)


# -----------------------------------------------------------------------------
# is_identity_collapsed
# -----------------------------------------------------------------------------


def test_is_collapsed_above_threshold_false():
    assert is_identity_collapsed(0.5) is False


def test_is_collapsed_below_threshold_true():
    assert is_identity_collapsed(0.01) is True


def test_is_collapsed_at_threshold_false():
    """Exactly at the threshold → NOT collapsed (strict <)."""
    assert is_identity_collapsed(IDENTITY_STABILITY_COLLAPSE_THRESHOLD) is False


def test_is_collapsed_custom_threshold():
    assert is_identity_collapsed(0.4, threshold=0.5) is True
    assert is_identity_collapsed(0.6, threshold=0.5) is False


# -----------------------------------------------------------------------------
# sweep_active_buyers — wire-point primitive
# -----------------------------------------------------------------------------


def test_sweep_no_cache_returns_empty():
    out = sweep_active_buyers(decision_cache=None)
    assert out.n_active == 0
    assert out.n_collapsed == 0
    assert out.collapse_fraction == 0.0


def test_sweep_empty_store_returns_empty():
    cache = _FakeCache([])
    out = sweep_active_buyers(decision_cache=cache)
    assert out.n_active == 0
    assert out.n_collapsed == 0


def test_sweep_fresh_buyer_not_collapsed():
    """Buyer touched today → not collapsed → n_active=1, n_collapsed=0."""
    now = time.time()
    cache = _FakeCache([
        _FakeContext("buyer-1", now),
    ])
    snapshot = _FakeSnapshot()
    out = sweep_active_buyers(decision_cache=cache, snapshot=snapshot)
    assert out.n_active == 1
    assert out.n_collapsed == 0
    assert snapshot.user_active_calls == [1]
    assert snapshot.collapse_calls == []  # not incremented when 0


def test_sweep_old_buyer_collapsed():
    """Buyer with Δ=200 days at default 2%/day decay → stability ≈
    0.98^200 ≈ 0.0176 < 0.05 threshold → collapsed."""
    now = time.time()
    days_ago = 200.0
    cache = _FakeCache([
        _FakeContext("buyer-old", now - days_ago * 86400.0),
    ])
    snapshot = _FakeSnapshot()
    # Lookback wide enough to include 200d
    out = sweep_active_buyers(
        decision_cache=cache, snapshot=snapshot,
        lookback_days=365.0,
    )
    assert out.n_active == 1
    assert out.n_collapsed == 1
    assert snapshot.user_active_calls == [1]
    assert snapshot.collapse_calls == [1]


def test_sweep_lookback_excludes_old_buyers():
    """Buyer Δ=100d but lookback=30d → excluded → n_active=0."""
    now = time.time()
    cache = _FakeCache([
        _FakeContext("buyer-old", now - 100 * 86400.0),
    ])
    out = sweep_active_buyers(
        decision_cache=cache, lookback_days=30.0,
    )
    assert out.n_active == 0


def test_sweep_anonymous_buyers_excluded():
    """Empty buyer_id → not addressable per-user → excluded."""
    now = time.time()
    cache = _FakeCache([
        _FakeContext("buyer-1", now),
        _FakeContext("", now),       # anonymous
        _FakeContext("buyer-2", now),
    ])
    out = sweep_active_buyers(decision_cache=cache)
    assert out.n_active == 2  # only the two with real ids


def test_sweep_multiple_touches_uses_most_recent():
    """Same buyer with two touches → days_since computed from the
    most recent timestamp."""
    now = time.time()
    cache = _FakeCache([
        _FakeContext("buyer-x", now - 100 * 86400.0),  # old touch
        _FakeContext("buyer-x", now - 1 * 86400.0),    # recent touch
    ])
    snapshot = _FakeSnapshot()
    out = sweep_active_buyers(
        decision_cache=cache, snapshot=snapshot,
        include_per_buyer=True,
    )
    assert out.n_active == 1
    # Most recent touch is 1 day ago → not collapsed
    assert out.n_collapsed == 0
    bid, days_since, _stab, _coll = out.per_buyer[0]
    assert bid == "buyer-x"
    assert days_since == pytest.approx(1.0, abs=0.01)


def test_sweep_collapse_fraction_calculated():
    """Mix of fresh + old → fraction = collapsed / active."""
    now = time.time()
    cache = _FakeCache([
        _FakeContext("buyer-fresh-1", now),
        _FakeContext("buyer-fresh-2", now - 1 * 86400.0),
        _FakeContext("buyer-old-1", now - 200 * 86400.0),  # collapsed
        _FakeContext("buyer-old-2", now - 250 * 86400.0),  # collapsed
    ])
    out = sweep_active_buyers(
        decision_cache=cache, lookback_days=365.0,
    )
    assert out.n_active == 4
    assert out.n_collapsed == 2
    assert out.collapse_fraction == pytest.approx(0.5)


def test_sweep_no_snapshot_does_not_raise():
    """Passing snapshot=None → counters not incremented + no error."""
    now = time.time()
    cache = _FakeCache([_FakeContext("buyer-1", now)])
    out = sweep_active_buyers(decision_cache=cache, snapshot=None)
    assert out.n_active == 1


def test_sweep_snapshot_failure_does_not_break_result():
    """If snapshot.record_* raises, the sweep still returns a clean
    result (logged WARNING but not propagated)."""
    now = time.time()
    cache = _FakeCache([_FakeContext("buyer-1", now)])

    class _BadSnapshot:
        def record_user_active(self, n=1):
            raise RuntimeError("boom")
        def record_identity_collapse(self, n=1):
            raise RuntimeError("boom")

    out = sweep_active_buyers(
        decision_cache=cache, snapshot=_BadSnapshot(),
    )
    assert out.n_active == 1


def test_sweep_per_buyer_populated_only_when_requested():
    now = time.time()
    cache = _FakeCache([_FakeContext("buyer-1", now)])
    out_no = sweep_active_buyers(decision_cache=cache)
    out_yes = sweep_active_buyers(
        decision_cache=cache, include_per_buyer=True,
    )
    assert out_no.per_buyer == []
    assert len(out_yes.per_buyer) == 1


def test_sweep_result_frozen():
    out = IdentityStabilitySweepResult(n_active=5, n_collapsed=2)
    with pytest.raises((AttributeError, Exception)):
        out.n_active = 99  # type: ignore[misc]
