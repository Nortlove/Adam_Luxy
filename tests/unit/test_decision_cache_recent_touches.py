"""Pin Slice 3 — DecisionCache.recent_touches_for_buyer adapter.

The within-subject eligibility filter (Slice 3) needs per-buyer
touch history at decision time. This test pins the cascade-side
adapter that surfaces it from the in-process decision_cache.

Anchors:
    * Method returns (Dict[mechanism, hours_since], last_touched_mechanism)
    * Cold buyer (no decisions in cache) → ({}, None)
    * Empty buyer_id → ({}, None)
    * Newest-only-per-mechanism semantics (multiple decisions on same
      mechanism return only the newest)
    * Stale decisions (> max_age_hours) excluded
    * Cross-buyer isolation (buyer A's history not visible to buyer B)
    * Honest tag: in-process LRU; multi-pod Redis backing is sibling
      slice (named in within_subject_eligibility (d)).
"""

from __future__ import annotations

import time

from adam.api.stackadapt.decision_cache import (
    DecisionCache,
    DecisionContext,
)


def _make_ctx(
    decision_id: str,
    buyer_id: str,
    mechanism: str,
    hours_ago: float,
) -> DecisionContext:
    return DecisionContext(
        decision_id=decision_id,
        buyer_id=buyer_id,
        mechanism_sent=mechanism,
        created_at=time.time() - hours_ago * 3600.0,
    )


def test_cold_buyer_returns_empty():
    """No decisions → empty history + None last-touched."""
    cache = DecisionCache(maxsize=100, ttl_seconds=86400)
    history, last = cache.recent_touches_for_buyer("ramp_id_42")
    assert history == {}
    assert last is None


def test_empty_buyer_id_returns_empty():
    """Empty buyer_id → empty result (no bucketing)."""
    cache = DecisionCache(maxsize=100, ttl_seconds=86400)
    cache.persist(_make_ctx("d1", "ramp_id_42", "social_proof", 1.0))
    history, last = cache.recent_touches_for_buyer("")
    assert history == {}
    assert last is None


def test_single_touch_recovered():
    """One decision → that mechanism in history with correct age."""
    cache = DecisionCache(maxsize=100, ttl_seconds=86400)
    cache.persist(_make_ctx("d1", "ramp_id_42", "social_proof", 5.0))
    history, last = cache.recent_touches_for_buyer("ramp_id_42")
    assert "social_proof" in history
    assert 4.9 <= history["social_proof"] <= 5.1  # tolerance for elapsed
    assert last == "social_proof"


def test_newest_per_mechanism():
    """Multiple decisions same mechanism → newest age returned."""
    cache = DecisionCache(maxsize=100, ttl_seconds=86400)
    cache.persist(_make_ctx("d1", "ramp_id_42", "social_proof", 10.0))
    cache.persist(_make_ctx("d2", "ramp_id_42", "social_proof", 2.0))
    cache.persist(_make_ctx("d3", "ramp_id_42", "social_proof", 7.0))
    history, last = cache.recent_touches_for_buyer("ramp_id_42")
    # newest = 2.0h ago
    assert 1.9 <= history["social_proof"] <= 2.1
    assert last == "social_proof"


def test_multiple_mechanisms_per_buyer():
    """Each mechanism gets its own newest-touch age."""
    cache = DecisionCache(maxsize=100, ttl_seconds=86400)
    cache.persist(_make_ctx("d1", "ramp_id_42", "social_proof", 10.0))
    cache.persist(_make_ctx("d2", "ramp_id_42", "scarcity", 3.0))
    cache.persist(_make_ctx("d3", "ramp_id_42", "loss_aversion", 7.0))
    history, last = cache.recent_touches_for_buyer("ramp_id_42")
    assert set(history.keys()) == {"social_proof", "scarcity", "loss_aversion"}
    # last_touched is the most recent across all mechanisms
    assert last == "scarcity"


def test_stale_decisions_excluded():
    """Decisions older than max_age_hours filtered out."""
    cache = DecisionCache(maxsize=100, ttl_seconds=86400 * 30)  # large TTL
    cache.persist(_make_ctx("d1", "ramp_id_42", "social_proof", 200.0))  # >168h
    cache.persist(_make_ctx("d2", "ramp_id_42", "scarcity", 5.0))
    history, last = cache.recent_touches_for_buyer(
        "ramp_id_42", max_age_hours=168.0,
    )
    assert "social_proof" not in history  # stale
    assert "scarcity" in history
    assert last == "scarcity"


def test_cross_buyer_isolation():
    """Buyer A's touches not visible to buyer B."""
    cache = DecisionCache(maxsize=100, ttl_seconds=86400)
    cache.persist(_make_ctx("d1", "ramp_id_A", "social_proof", 1.0))
    cache.persist(_make_ctx("d2", "ramp_id_B", "scarcity", 2.0))

    history_a, last_a = cache.recent_touches_for_buyer("ramp_id_A")
    history_b, last_b = cache.recent_touches_for_buyer("ramp_id_B")

    assert "social_proof" in history_a
    assert "scarcity" not in history_a
    assert last_a == "social_proof"

    assert "scarcity" in history_b
    assert "social_proof" not in history_b
    assert last_b == "scarcity"


def test_no_mechanism_sent_skipped():
    """Decisions without mechanism_sent (e.g., no-bid) are skipped."""
    cache = DecisionCache(maxsize=100, ttl_seconds=86400)
    cache.persist(_make_ctx("d1", "ramp_id_42", "social_proof", 1.0))
    cache.persist(_make_ctx("d2", "ramp_id_42", "", 2.0))  # no mechanism
    history, last = cache.recent_touches_for_buyer("ramp_id_42")
    assert "social_proof" in history
    assert "" not in history
    assert last == "social_proof"
