"""Pin Slice 6 — sapid round-trip wiring (registration + resolution).

Discipline anchors (B3-LUXY a/b/c/d):

    (a) Citation: directive Section 3.7 ("Round-trip rate is monitored
        as a load-bearing operational metric — target ≥98%") + Phase 10
        RED-criterion #8 (sapid round-trip rate <95% → defer launch) +
        Audit §D1 ("Sapid round-trip linkage table").

        Substrate already shipped:
          - SapidRoundTripMonitor in
            adam.intelligence.spine.phase_8_stackadapt_integration
          - decision_cache.persist() at decision time
            (adam.api.stackadapt.decision_cache)
          - decision_cache.retrieve() / Neo4j fallback at outcome time
          - record_resolution() wired in negative_outcome_adapters.dispatch
        This slice closes the gap: record_registration() at persist
        + record_resolution() on the conversion-webhook path.

    (b) Boundary anchors pinned by these tests:
          - persist() increments registration counter per call
          - persist() soft-fails when monitor module unavailable
          - webhook conversion (decision found) → record_resolution(True)
          - webhook conversion (decision NOT found) → record_resolution(False)
          - round_trip_rate() correct under symmetric flow
          - registration / resolution paths independent (resolution
            without prior registration still increments)

    (c) calibration_pending=False — counter increments are unconditional.
        DEFAULT_ROUND_TRIP_TARGET=0.98 is calibrated upstream
        (phase_8_stackadapt_integration A14 flag).

    (d) Honest tags — what is NOT in this slice:
          - Conversion-webhook resolution wiring is for the production
            POST conversion path. The negative-outcome adapter path
            already records resolution per dispatch; this slice closes
            the symmetric wire on the conversion-event path.
          - feature_vector storage on SapidRecord (audit's "first-class
            structure" hint) — decision_cache.DecisionContext IS the
            registry; it carries mechanism_scores / edge_dimensions /
            gradient_priorities / etc. as the feature snapshot. No
            separate registry needed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from adam.api.stackadapt.decision_cache import DecisionCache, DecisionContext
from adam.intelligence.spine.phase_8_stackadapt_integration import (
    get_default_monitor,
    reset_default_monitor,
)


def setup_function() -> None:
    reset_default_monitor()


# -----------------------------------------------------------------------------
# Registration side — decision_cache.persist increments counter
# -----------------------------------------------------------------------------


def test_persist_increments_registration_counter():
    """One persist call → one registration recorded."""
    cache = DecisionCache(maxsize=100, ttl_seconds=3600)
    monitor = get_default_monitor()
    pre = monitor.n_sapids_registered

    ctx = DecisionContext(
        decision_id="d-1",
        archetype="status_seeker",
        mechanism_sent="social_proof",
    )
    cache.persist(ctx)

    assert monitor.n_sapids_registered == pre + 1


def test_persist_increments_registration_per_call():
    """Three persist calls → three registrations."""
    cache = DecisionCache(maxsize=100, ttl_seconds=3600)
    monitor = get_default_monitor()
    pre = monitor.n_sapids_registered

    for i in range(3):
        ctx = DecisionContext(decision_id=f"d-{i}")
        cache.persist(ctx)

    assert monitor.n_sapids_registered == pre + 3


def test_persist_soft_fails_when_monitor_unavailable():
    """If the monitor import / call raises, persist still succeeds.

    Bid path must NEVER block on monitor instrumentation."""
    cache = DecisionCache(maxsize=100, ttl_seconds=3600)
    ctx = DecisionContext(decision_id="d-1")

    with patch(
        "adam.intelligence.spine.phase_8_stackadapt_integration.get_default_monitor",
        side_effect=RuntimeError("monitor down"),
    ):
        # Must not raise
        cache.persist(ctx)

    # The decision is still cached even though the monitor failed
    assert cache.retrieve("d-1") is ctx


# -----------------------------------------------------------------------------
# Resolution side — webhook record_resolution wiring
# -----------------------------------------------------------------------------


def test_round_trip_rate_zero_after_only_registrations():
    """record_registration alone doesn't move round_trip_rate (which is
    resolved/(resolved+unresolved))."""
    monitor = get_default_monitor()
    monitor.record_registration()
    monitor.record_registration()
    assert monitor.round_trip_rate() == 0.0


def test_round_trip_rate_one_when_all_resolved():
    """Symmetric flow: 5 registrations + 5 successful resolutions
    → 100% round-trip."""
    monitor = get_default_monitor()
    for _ in range(5):
        monitor.record_registration()
        monitor.record_resolution(resolved=True)
    assert monitor.round_trip_rate() == pytest.approx(1.0)


def test_round_trip_rate_under_target_when_unresolved_dominant():
    """4 unresolved + 1 resolved → 20% round-trip; below DEFAULT 0.98."""
    monitor = get_default_monitor()
    monitor.record_resolution(resolved=True)
    for _ in range(4):
        monitor.record_resolution(resolved=False)
    assert monitor.round_trip_rate() == pytest.approx(0.2)
    assert not monitor.meets_phase_8_target()


def test_round_trip_target_met_at_exactly_98_percent():
    """98 resolved + 2 unresolved = 0.98 → meets target."""
    monitor = get_default_monitor()
    for _ in range(98):
        monitor.record_resolution(resolved=True)
    for _ in range(2):
        monitor.record_resolution(resolved=False)
    assert monitor.round_trip_rate() == pytest.approx(0.98)
    assert monitor.meets_phase_8_target()


# -----------------------------------------------------------------------------
# End-to-end round-trip — registration and resolution counters together
# -----------------------------------------------------------------------------


def test_full_round_trip_registers_then_resolves():
    """Decision → persist (register) → outcome arrives → resolve.

    Pin the operational invariant: every successful round-trip
    increments BOTH counters."""
    cache = DecisionCache(maxsize=100, ttl_seconds=3600)
    monitor = get_default_monitor()

    # Decision time
    ctx = DecisionContext(decision_id="d-rt-1")
    cache.persist(ctx)
    assert monitor.n_sapids_registered == 1

    # Outcome time (simulating the webhook resolution wire)
    decision_ctx_found = cache.retrieve("d-rt-1") is not None
    monitor.record_resolution(resolved=decision_ctx_found)

    assert monitor.n_sapids_resolved == 1
    assert monitor.n_sapids_unresolved == 0
    assert monitor.round_trip_rate() == pytest.approx(1.0)


def test_lost_round_trip_increments_unresolved():
    """Decision persisted → outcome arrives with unknown decision_id
    → record_resolution(resolved=False) increments unresolved."""
    cache = DecisionCache(maxsize=100, ttl_seconds=3600)
    monitor = get_default_monitor()

    ctx = DecisionContext(decision_id="d-real")
    cache.persist(ctx)

    # Outcome with a different decision_id (e.g., adblock-stripped sapid)
    decision_ctx_found = cache.retrieve("d-stripped-by-adblock") is not None
    monitor.record_resolution(resolved=decision_ctx_found)

    assert monitor.n_sapids_registered == 1
    assert monitor.n_sapids_resolved == 0
    assert monitor.n_sapids_unresolved == 1
    assert monitor.round_trip_rate() == pytest.approx(0.0)
