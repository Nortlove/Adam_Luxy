# =============================================================================
# ADAM Mechanism Rotation Tests
# Location: tests/unit/test_mechanism_rotation.py
# =============================================================================

"""Tests for task #22 — pre-registered mechanism rotation event.

Coverage:
  - Commitment construction validation
  - Public statement rendering
  - Trigger evaluation across all three TriggerCondition types
  - Window expiration
  - Cell-mismatch validation
  - Registry: register/get/update/cancel lifecycle
  - Idempotency / immutability discipline
  - Singleton
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from adam.intelligence.mechanism_rotation import (
    CellEvidence,
    RotationCommitment,
    RotationEvent,
    RotationRegistry,
    RotationStatus,
    TriggerCondition,
    construct_rotation_event,
    evaluate_trigger,
    get_rotation_registry,
    register_rotation,
    reset_rotation_registry,
)


# ============================================================================
# Commitment construction + validation
# ============================================================================


class TestCommitmentConstruction:

    def test_register_basic(self):
        c = register_rotation(
            archetype="careful_truster",
            page_context="prevention_focused",
            from_mechanism="authority",
            to_mechanism="brand_trust_evidence",
            rationale="Bilateral edge data shows brand_trust_evidence outperforms authority",
            trigger_condition=TriggerCondition.EDGE_COUNT_THRESHOLD,
            trigger_threshold=50.0,
            evaluation_window_days=14,
            registered_by="user:chris",
        )
        assert c.archetype == "careful_truster"
        assert c.from_mechanism == "authority"
        assert c.to_mechanism == "brand_trust_evidence"
        assert c.rotation_id.startswith("rot:")

    def test_register_rejects_empty_rationale(self):
        with pytest.raises(ValueError, match="rationale"):
            register_rotation(
                archetype="x", from_mechanism="a", to_mechanism="b",
                rationale="", trigger_condition=TriggerCondition.EDGE_COUNT_THRESHOLD,
                trigger_threshold=50.0, evaluation_window_days=14,
                registered_by="u",
            )

    def test_register_rejects_same_from_to(self):
        with pytest.raises(ValueError, match="must differ"):
            register_rotation(
                archetype="x", from_mechanism="authority",
                to_mechanism="authority",
                rationale="r", trigger_condition=TriggerCondition.EDGE_COUNT_THRESHOLD,
                trigger_threshold=50.0, evaluation_window_days=14,
                registered_by="u",
            )

    def test_register_rejects_non_positive_threshold(self):
        with pytest.raises(ValueError, match="trigger_threshold"):
            register_rotation(
                archetype="x", from_mechanism="a", to_mechanism="b",
                rationale="r", trigger_condition=TriggerCondition.EDGE_COUNT_THRESHOLD,
                trigger_threshold=0.0, evaluation_window_days=14,
                registered_by="u",
            )

    def test_register_rejects_non_positive_window(self):
        with pytest.raises(ValueError, match="evaluation_window_days"):
            register_rotation(
                archetype="x", from_mechanism="a", to_mechanism="b",
                rationale="r", trigger_condition=TriggerCondition.EDGE_COUNT_THRESHOLD,
                trigger_threshold=50.0, evaluation_window_days=0,
                registered_by="u",
            )

    def test_public_statement_includes_all_fields(self):
        c = register_rotation(
            archetype="careful_truster",
            page_context="prevention_focused",
            from_mechanism="authority",
            to_mechanism="brand_trust_evidence",
            rationale="Bilateral evidence shows X",
            trigger_condition=TriggerCondition.EDGE_COUNT_THRESHOLD,
            trigger_threshold=50.0,
            evaluation_window_days=14,
            registered_by="user:chris",
        )
        statement = c.public_statement
        assert "careful_truster" in statement
        assert "prevention_focused" in statement
        assert "authority" in statement
        assert "brand_trust_evidence" in statement
        assert "Bilateral evidence shows X" in statement
        assert "user:chris" in statement
        assert "50" in statement


# ============================================================================
# Trigger evaluation — EDGE_COUNT_THRESHOLD
# ============================================================================


def _make_commitment(
    *,
    threshold: float = 50.0,
    condition: TriggerCondition = TriggerCondition.EDGE_COUNT_THRESHOLD,
    window_days: int = 14,
    from_mech: str = "authority",
    to_mech: str = "brand_trust_evidence",
    archetype: str = "careful_truster",
    page_context: str = "prevention_focused",
    registered_at: datetime = None,
) -> RotationCommitment:
    return register_rotation(
        archetype=archetype,
        page_context=page_context,
        from_mechanism=from_mech,
        to_mechanism=to_mech,
        rationale="test",
        trigger_condition=condition,
        trigger_threshold=threshold,
        evaluation_window_days=window_days,
        registered_by="test",
        registered_at=registered_at,
    )


class TestEdgeCountThreshold:

    def test_below_threshold_pending(self):
        c = _make_commitment(threshold=50.0)
        from_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.from_mechanism, edge_count=30,
        )
        to_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.to_mechanism, edge_count=30,
        )
        assert evaluate_trigger(c, from_evidence=from_ev, to_evidence=to_ev) == RotationStatus.PENDING

    def test_only_one_above_threshold_pending(self):
        c = _make_commitment(threshold=50.0)
        from_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.from_mechanism, edge_count=100,
        )
        to_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.to_mechanism, edge_count=30,
        )
        assert evaluate_trigger(c, from_evidence=from_ev, to_evidence=to_ev) == RotationStatus.PENDING

    def test_both_above_threshold_triggered(self):
        c = _make_commitment(threshold=50.0)
        from_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.from_mechanism, edge_count=80,
        )
        to_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.to_mechanism, edge_count=70,
        )
        assert evaluate_trigger(c, from_evidence=from_ev, to_evidence=to_ev) == RotationStatus.TRIGGERED


# ============================================================================
# Trigger evaluation — CATE_DIFFERENTIAL_THRESHOLD
# ============================================================================


class TestCATEDifferential:

    def test_missing_cate_pending(self):
        c = _make_commitment(condition=TriggerCondition.CATE_DIFFERENTIAL_THRESHOLD, threshold=0.05)
        from_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.from_mechanism, edge_count=100,
            cate_estimate=None,
        )
        to_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.to_mechanism, edge_count=100,
            cate_estimate=None,
        )
        assert evaluate_trigger(c, from_evidence=from_ev, to_evidence=to_ev) == RotationStatus.PENDING

    def test_below_differential_pending(self):
        c = _make_commitment(condition=TriggerCondition.CATE_DIFFERENTIAL_THRESHOLD, threshold=0.05)
        from_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.from_mechanism, edge_count=100,
            cate_estimate=0.10,
        )
        to_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.to_mechanism, edge_count=100,
            cate_estimate=0.13,  # diff = 0.03 < 0.05
        )
        assert evaluate_trigger(c, from_evidence=from_ev, to_evidence=to_ev) == RotationStatus.PENDING

    def test_at_or_above_differential_triggered(self):
        c = _make_commitment(condition=TriggerCondition.CATE_DIFFERENTIAL_THRESHOLD, threshold=0.05)
        from_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.from_mechanism, edge_count=100,
            cate_estimate=0.10,
        )
        to_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.to_mechanism, edge_count=100,
            cate_estimate=0.20,  # diff = 0.10 ≥ 0.05
        )
        assert evaluate_trigger(c, from_evidence=from_ev, to_evidence=to_ev) == RotationStatus.TRIGGERED


# ============================================================================
# Trigger evaluation — CONFORMAL_INTERVAL_NON_OVERLAP
# ============================================================================


class TestConformalNonOverlap:

    def test_overlapping_intervals_pending(self):
        c = _make_commitment(condition=TriggerCondition.CONFORMAL_INTERVAL_NON_OVERLAP, threshold=0.01)
        from_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.from_mechanism, edge_count=100,
            conformal_ci_low=0.10, conformal_ci_high=0.20,
        )
        to_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.to_mechanism, edge_count=100,
            conformal_ci_low=0.18, conformal_ci_high=0.28,  # overlaps
        )
        assert evaluate_trigger(c, from_evidence=from_ev, to_evidence=to_ev) == RotationStatus.PENDING

    def test_separated_intervals_triggered(self):
        c = _make_commitment(condition=TriggerCondition.CONFORMAL_INTERVAL_NON_OVERLAP, threshold=0.01)
        from_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.from_mechanism, edge_count=100,
            conformal_ci_low=0.10, conformal_ci_high=0.15,
        )
        to_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.to_mechanism, edge_count=100,
            conformal_ci_low=0.20, conformal_ci_high=0.30,  # to_low > from_high + threshold
        )
        assert evaluate_trigger(c, from_evidence=from_ev, to_evidence=to_ev) == RotationStatus.TRIGGERED


# ============================================================================
# Window expiration
# ============================================================================


class TestWindowExpiration:

    def test_after_window_expired(self):
        old_registered = datetime.now(timezone.utc) - timedelta(days=20)
        c = _make_commitment(window_days=14, registered_at=old_registered)
        from_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.from_mechanism, edge_count=100,
        )
        to_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.to_mechanism, edge_count=100,
        )
        # Even though both above threshold, window is past — EXPIRED
        assert evaluate_trigger(c, from_evidence=from_ev, to_evidence=to_ev) == RotationStatus.EXPIRED

    def test_within_window_normal_evaluation(self):
        recent_registered = datetime.now(timezone.utc) - timedelta(days=3)
        c = _make_commitment(
            window_days=14, threshold=50.0, registered_at=recent_registered,
        )
        from_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.from_mechanism, edge_count=100,
        )
        to_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.to_mechanism, edge_count=100,
        )
        assert evaluate_trigger(c, from_evidence=from_ev, to_evidence=to_ev) == RotationStatus.TRIGGERED


# ============================================================================
# Cell mismatch validation
# ============================================================================


class TestCellMismatchValidation:

    def test_archetype_mismatch_raises(self):
        c = _make_commitment()
        from_ev = CellEvidence(
            archetype="status_seeker",  # doesn't match c.archetype
            page_context=c.page_context,
            mechanism=c.from_mechanism, edge_count=100,
        )
        to_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.to_mechanism, edge_count=100,
        )
        with pytest.raises(ValueError, match="archetype"):
            evaluate_trigger(c, from_evidence=from_ev, to_evidence=to_ev)

    def test_mechanism_mismatch_raises(self):
        c = _make_commitment()
        from_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism="WRONG", edge_count=100,
        )
        to_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.to_mechanism, edge_count=100,
        )
        with pytest.raises(ValueError, match="from_mechanism"):
            evaluate_trigger(c, from_evidence=from_ev, to_evidence=to_ev)


# ============================================================================
# Registry — lifecycle + immutability
# ============================================================================


class TestRegistry:

    def test_register_and_get(self):
        reg = RotationRegistry()
        c = _make_commitment()
        reg.register(c)
        assert reg.get(c.rotation_id) is c
        assert reg.status_of(c.rotation_id) == RotationStatus.REGISTERED

    def test_double_registration_fails(self):
        reg = RotationRegistry()
        c = _make_commitment()
        reg.register(c)
        with pytest.raises(ValueError, match="immutable"):
            reg.register(c)

    def test_update_status_from_evidence_to_triggered(self):
        reg = RotationRegistry()
        c = _make_commitment(threshold=50.0)
        reg.register(c)

        from_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.from_mechanism, edge_count=80,
        )
        to_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.to_mechanism, edge_count=70,
        )
        new_status = reg.update_status_from_evidence(
            c.rotation_id, from_ev, to_ev,
        )
        assert new_status == RotationStatus.TRIGGERED
        assert reg.status_of(c.rotation_id) == RotationStatus.TRIGGERED
        # RotationEvent created
        ev = reg.get_event(c.rotation_id)
        assert ev is not None
        assert ev.rotation_id == c.rotation_id

    def test_triggered_state_terminal(self):
        """Once triggered, subsequent evaluations don't downgrade."""
        reg = RotationRegistry()
        c = _make_commitment(threshold=50.0)
        reg.register(c)

        # First update — triggers
        from_ev_1 = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.from_mechanism, edge_count=80,
        )
        to_ev_1 = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.to_mechanism, edge_count=70,
        )
        reg.update_status_from_evidence(c.rotation_id, from_ev_1, to_ev_1)

        # Second update with low evidence — should still be TRIGGERED
        from_ev_2 = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.from_mechanism, edge_count=10,
        )
        to_ev_2 = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.to_mechanism, edge_count=10,
        )
        new_status = reg.update_status_from_evidence(
            c.rotation_id, from_ev_2, to_ev_2,
        )
        assert new_status == RotationStatus.TRIGGERED

    def test_cancel_changes_status(self):
        reg = RotationRegistry()
        c = _make_commitment()
        reg.register(c)
        reg.cancel(c.rotation_id, reason="test cancellation")
        assert reg.status_of(c.rotation_id) == RotationStatus.CANCELLED

    def test_cannot_cancel_triggered(self):
        reg = RotationRegistry()
        c = _make_commitment(threshold=50.0)
        reg.register(c)
        from_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.from_mechanism, edge_count=80,
        )
        to_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.to_mechanism, edge_count=70,
        )
        reg.update_status_from_evidence(c.rotation_id, from_ev, to_ev)
        with pytest.raises(ValueError, match="terminal state"):
            reg.cancel(c.rotation_id, reason="too late")


# ============================================================================
# Singleton
# ============================================================================


class TestSingleton:

    def test_singleton_consistency(self):
        reset_rotation_registry()
        try:
            r1 = get_rotation_registry()
            r2 = get_rotation_registry()
            assert r1 is r2
        finally:
            reset_rotation_registry()


# ============================================================================
# RotationEvent
# ============================================================================


class TestRotationEvent:

    def test_construct_from_triggered(self):
        c = _make_commitment(threshold=50.0)
        from_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.from_mechanism, edge_count=80,
            cate_estimate=0.12,
        )
        to_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.to_mechanism, edge_count=70,
            cate_estimate=0.18,
        )
        ev = construct_rotation_event(c, from_ev, to_ev)
        assert ev.rotation_id == c.rotation_id
        assert ev.from_evidence.cate_estimate == 0.12
        assert ev.to_evidence.cate_estimate == 0.18

    def test_public_summary_includes_evidence(self):
        c = _make_commitment(threshold=50.0)
        from_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.from_mechanism, edge_count=80,
            cate_estimate=0.12,
        )
        to_ev = CellEvidence(
            archetype=c.archetype, page_context=c.page_context,
            mechanism=c.to_mechanism, edge_count=70,
            cate_estimate=0.18,
        )
        ev = construct_rotation_event(c, from_ev, to_ev)
        summary = ev.public_summary()
        assert c.rotation_id in summary
        assert "TRIGGERED" in summary
        assert c.from_mechanism in summary
        assert c.to_mechanism in summary
