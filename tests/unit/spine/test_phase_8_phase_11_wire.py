"""Integration test for Phase 8 ↔ Spine #11 wire.

Pins:
    1. register_sapid_for_decision increments the monitor's
       n_sapids_registered counter
    2. build_outcome_event with a known sapid increments
       n_sapids_resolved
    3. build_outcome_event with an unknown sapid increments
       n_sapids_unresolved (the round-trip failure case)
    4. End-to-end: orchestrator-style flow shows monitor counters
       moving through the registration + outcome roundtrip
    5. round_trip_rate computed live from the wired counters
"""

from __future__ import annotations

import pytest

from adam.intelligence.spine.phase_8_stackadapt_integration import (
    get_default_monitor,
    reset_default_monitor,
)
from adam.intelligence.spine.spine_11_negative_outcome_adapter import (
    RawPixelEvent,
    build_outcome_event,
    register_sapid_for_decision,
    reset_sapid_registry,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_default_monitor()
    reset_sapid_registry()
    yield
    reset_default_monitor()
    reset_sapid_registry()


# -----------------------------------------------------------------------------
# Registration counter
# -----------------------------------------------------------------------------


class TestRegistrationWire:

    def test_register_increments_monitor(self):
        monitor = get_default_monitor()
        assert monitor.n_sapids_registered == 0
        register_sapid_for_decision(
            sapid="sa_test_001", decision_id="d:1",
            user_id="u:1", feature_vector=[1.0, 0.0],
        )
        assert monitor.n_sapids_registered == 1

    def test_multiple_registrations_accumulate(self):
        monitor = get_default_monitor()
        for i in range(5):
            register_sapid_for_decision(
                sapid=f"sa_test_{i:03d}", decision_id=f"d:{i}",
                user_id=f"u:{i}", feature_vector=[1.0, 0.0],
            )
        assert monitor.n_sapids_registered == 5


# -----------------------------------------------------------------------------
# Resolution counter (resolved + unresolved)
# -----------------------------------------------------------------------------


class TestResolutionWire:

    def test_known_sapid_increments_resolved(self):
        register_sapid_for_decision(
            sapid="sa_known", decision_id="d:1",
            user_id="u:1", feature_vector=[1.0, 0.0],
        )
        monitor = get_default_monitor()
        # Reset just the resolution counters so the test is isolated
        # from the registration counter (which got bumped above).
        # We only care about resolved/unresolved here.
        before_resolved = monitor.n_sapids_resolved
        before_unresolved = monitor.n_sapids_unresolved

        raw = RawPixelEvent(sapid="sa_known", event_type="view",
                            is_conversion=True)
        outcome = build_outcome_event(raw)
        assert outcome is not None

        assert monitor.n_sapids_resolved == before_resolved + 1
        assert monitor.n_sapids_unresolved == before_unresolved

    def test_unknown_sapid_increments_unresolved(self):
        monitor = get_default_monitor()
        before_resolved = monitor.n_sapids_resolved
        before_unresolved = monitor.n_sapids_unresolved

        raw = RawPixelEvent(sapid="sa_unknown_xyz", event_type="view",
                            is_conversion=True)
        outcome = build_outcome_event(raw)
        assert outcome is None  # round-trip failure path

        assert monitor.n_sapids_resolved == before_resolved
        assert monitor.n_sapids_unresolved == before_unresolved + 1


# -----------------------------------------------------------------------------
# Round-trip rate computed live
# -----------------------------------------------------------------------------


class TestRoundTripRate:

    def test_perfect_flow_yields_full_rate(self):
        # 10 registrations, all 10 events resolve.
        for i in range(10):
            sapid = f"sa_perfect_{i:03d}"
            register_sapid_for_decision(
                sapid=sapid, decision_id=f"d:{i}",
                user_id=f"u:{i}", feature_vector=[1.0, 0.0],
            )
        for i in range(10):
            raw = RawPixelEvent(
                sapid=f"sa_perfect_{i:03d}",
                event_type="view", is_conversion=True,
            )
            build_outcome_event(raw)

        monitor = get_default_monitor()
        assert monitor.round_trip_rate() == 1.0
        assert monitor.meets_phase_8_target() is True

    def test_partial_flow_yields_partial_rate(self):
        # 10 registrations; 9 resolve, 1 unresolved (orphan pixel event)
        for i in range(10):
            register_sapid_for_decision(
                sapid=f"sa_partial_{i:03d}", decision_id=f"d:{i}",
                user_id=f"u:{i}", feature_vector=[1.0, 0.0],
            )
        # 9 known + 1 orphan
        for i in range(9):
            build_outcome_event(RawPixelEvent(
                sapid=f"sa_partial_{i:03d}", event_type="view",
                is_conversion=True,
            ))
        # 1 orphan pixel event with unregistered sapid
        build_outcome_event(RawPixelEvent(
            sapid="sa_orphan_xyz", event_type="view",
            is_conversion=True,
        ))

        monitor = get_default_monitor()
        # 9 resolved + 1 unresolved → 0.9
        assert monitor.round_trip_rate() == pytest.approx(0.9)

    def test_below_target_does_not_meet_phase_8_gate(self):
        # 100 registrations; 90 resolve, 10 unresolved → 0.9 < 0.98 target
        for i in range(100):
            register_sapid_for_decision(
                sapid=f"sa_b_{i:03d}", decision_id=f"d:{i}",
                user_id=f"u:{i}", feature_vector=[1.0, 0.0],
            )
        for i in range(90):
            build_outcome_event(RawPixelEvent(
                sapid=f"sa_b_{i:03d}", event_type="view",
                is_conversion=True,
            ))
        for i in range(10):
            build_outcome_event(RawPixelEvent(
                sapid=f"sa_orphan_b_{i:03d}", event_type="view",
                is_conversion=True,
            ))

        monitor = get_default_monitor()
        assert monitor.round_trip_rate() == pytest.approx(0.9)
        assert monitor.meets_phase_8_target() is False
