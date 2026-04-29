# =============================================================================
# ADAM C4 — HumanDeviation Lifecycle Tests
# Location: tests/unit/test_deviation_lifecycle.py
# =============================================================================

"""Tests for HumanDeviation models + deviation_lifecycle service.

Pins the load-bearing structural claims:
    1. HumanDeviation enforces RECORDED at construction (HMT rule 12)
    2. reason_tag is required (A12 defense — categorical not free-form)
    3. State machine transitions are monotonic forward; back-transitions raise
    4. schedule_adjudication populates horizon and advances state
    5. is_adjudication_due requires both horizon elapsed AND non-terminal state
    6. adjudicate_deviation outcomes match the threshold matrix:
       - insufficient samples → PENDING_INSUFFICIENT_DATA
       - missing outcome → PENDING_INSUFFICIENT_DATA
       - |delta| < threshold → FALSE_CORRECTION
       - substitute outperformed → CONFIRMED_OVERRIDE
       - recommendation outperformed → SYSTEM_VINDICATED
    7. A14 flag emitted only for non-terminal deviations
    8. A14 flag identifier + retirement trigger documented
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from adam.intelligence.deviation_lifecycle import (
    AdjudicationThresholds,
    DEVIATION_PENDING_ADJUDICATION_FLAG,
    DEVIATION_PENDING_RETIREMENT_TRIGGER,
    InvalidTransitionError,
    adjudicate_deviation,
    horizon_for_domain,
    is_adjudication_due,
    is_pending_adjudication,
    record_deviation_a14_flag,
    schedule_adjudication,
    transition_state,
)
from adam.intelligence.dialogue_ledger.models import (
    DeviationAdjudicationOutcome,
    DeviationLifecycleState,
    HumanDeviation,
    make_deviation,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


def _make_test_deviation() -> HumanDeviation:
    return make_deviation(
        user_id="user:test",
        decision_id="decision:test_1",
        domain="ad_conversion",
        system_recommendation={"mechanism": "authority", "tone": "warm"},
        user_substitute={"mechanism": "scarcity", "tone": "urgent"},
        reason_tag="archetype_mismatch",
        reason_text="The system suggested authority but I think this user "
                    "responds better to scarcity for this product category.",
        expected_outcome_tag="higher_conversion",
    )


# -----------------------------------------------------------------------------
# Construction-time invariants
# -----------------------------------------------------------------------------


class TestHumanDeviationConstruction:

    def test_construction_succeeds_with_recorded_state(self):
        d = _make_test_deviation()
        assert d.lifecycle_state == DeviationLifecycleState.RECORDED
        assert d.user_id == "user:test"
        assert d.reason_tag == "archetype_mismatch"

    def test_explicit_non_recorded_state_rejected(self):
        # HMT rule 12: deviations must enter as RECORDED, not pre-advanced.
        with pytest.raises(ValueError, match="RECORDED"):
            HumanDeviation(
                user_id="u",
                decision_id="d",
                domain="ad_conversion",
                system_recommendation={"mechanism": "authority"},
                user_substitute={"mechanism": "scarcity"},
                reason_tag="x",
                lifecycle_state=DeviationLifecycleState.AWAITING_OUTCOME,
            )

    def test_empty_reason_tag_rejected(self):
        # A12 defense: free-form reason_text alone insufficient.
        with pytest.raises(ValueError, match="reason_tag"):
            make_deviation(
                user_id="u",
                decision_id="d",
                domain="ad_conversion",
                system_recommendation={},
                user_substitute={},
                reason_tag="",
            )

    def test_whitespace_only_reason_tag_rejected(self):
        with pytest.raises(ValueError, match="reason_tag"):
            make_deviation(
                user_id="u",
                decision_id="d",
                domain="ad_conversion",
                system_recommendation={},
                user_substitute={},
                reason_tag="   ",
            )

    def test_id_auto_generated_with_deviation_prefix(self):
        d = _make_test_deviation()
        assert d.id.startswith("deviation:")
        assert len(d.id) > len("deviation:")

    def test_to_neo4j_props_serializes_dicts_as_json(self):
        d = _make_test_deviation()
        props = d.to_neo4j_props()
        # Dict fields persist as JSON strings (Neo4j scalar discipline).
        assert "system_recommendation_json" in props
        assert "user_substitute_json" in props
        assert isinstance(props["system_recommendation_json"], str)
        # Round-trippable.
        import json
        round_tripped = json.loads(props["system_recommendation_json"])
        assert round_tripped["mechanism"] == "authority"


# -----------------------------------------------------------------------------
# State-machine transitions
# -----------------------------------------------------------------------------


class TestStateMachineTransitions:

    def test_recorded_to_awaiting_outcome(self):
        d = _make_test_deviation()
        d2 = transition_state(d, DeviationLifecycleState.AWAITING_OUTCOME)
        assert d2.lifecycle_state == DeviationLifecycleState.AWAITING_OUTCOME
        # Original is unchanged (Pydantic model_copy semantics).
        assert d.lifecycle_state == DeviationLifecycleState.RECORDED

    def test_awaiting_to_adjudicated(self):
        d = _make_test_deviation()
        d = transition_state(d, DeviationLifecycleState.AWAITING_OUTCOME)
        d = transition_state(d, DeviationLifecycleState.ADJUDICATED)
        assert d.lifecycle_state == DeviationLifecycleState.ADJUDICATED

    def test_awaiting_to_pending_then_adjudicated(self):
        d = _make_test_deviation()
        d = transition_state(d, DeviationLifecycleState.AWAITING_OUTCOME)
        d = transition_state(d, DeviationLifecycleState.PENDING)
        d = transition_state(d, DeviationLifecycleState.ADJUDICATED)
        assert d.lifecycle_state == DeviationLifecycleState.ADJUDICATED

    def test_recorded_directly_to_adjudicated_rejected(self):
        # Must pass through AWAITING_OUTCOME first.
        d = _make_test_deviation()
        with pytest.raises(InvalidTransitionError):
            transition_state(d, DeviationLifecycleState.ADJUDICATED)

    def test_adjudicated_is_terminal(self):
        d = _make_test_deviation()
        d = transition_state(d, DeviationLifecycleState.AWAITING_OUTCOME)
        d = transition_state(d, DeviationLifecycleState.ADJUDICATED)
        # No transitions allowed from ADJUDICATED.
        with pytest.raises(InvalidTransitionError):
            transition_state(d, DeviationLifecycleState.AWAITING_OUTCOME)
        with pytest.raises(InvalidTransitionError):
            transition_state(d, DeviationLifecycleState.RECORDED)

    def test_back_transitions_rejected(self):
        d = _make_test_deviation()
        d = transition_state(d, DeviationLifecycleState.AWAITING_OUTCOME)
        # Cannot go back to RECORDED.
        with pytest.raises(InvalidTransitionError):
            transition_state(d, DeviationLifecycleState.RECORDED)


# -----------------------------------------------------------------------------
# schedule_adjudication
# -----------------------------------------------------------------------------


class TestScheduleAdjudication:

    def test_default_horizon_for_domain(self):
        # ad_conversion default = 30 days
        assert horizon_for_domain("ad_conversion") == 30
        assert horizon_for_domain("brand_equity") == 90
        # Unknown domain → default 30
        assert horizon_for_domain("unknown_domain") == 30

    def test_schedule_advances_state_and_sets_horizon(self):
        d = _make_test_deviation()
        now = datetime(2026, 5, 1, tzinfo=timezone.utc)
        d2 = schedule_adjudication(d, horizon_days=30, now=now)
        assert d2.lifecycle_state == DeviationLifecycleState.AWAITING_OUTCOME
        expected = now + timedelta(days=30)
        assert d2.horizon_ends_at == expected

    def test_schedule_uses_domain_default_when_horizon_omitted(self):
        d = _make_test_deviation()  # domain="ad_conversion" → 30
        now = datetime(2026, 5, 1, tzinfo=timezone.utc)
        d2 = schedule_adjudication(d, now=now)
        expected = now + timedelta(days=30)
        assert d2.horizon_ends_at == expected

    def test_negative_or_zero_horizon_rejected(self):
        d = _make_test_deviation()
        with pytest.raises(ValueError):
            schedule_adjudication(d, horizon_days=0)
        with pytest.raises(ValueError):
            schedule_adjudication(d, horizon_days=-1)


# -----------------------------------------------------------------------------
# is_adjudication_due
# -----------------------------------------------------------------------------


class TestIsAdjudicationDue:

    def test_horizon_in_future_not_due(self):
        d = _make_test_deviation()
        now = datetime(2026, 5, 1, tzinfo=timezone.utc)
        d = schedule_adjudication(d, horizon_days=30, now=now)
        # Check 10 days later — still 20 days from horizon.
        future = now + timedelta(days=10)
        assert is_adjudication_due(d, now=future) is False

    def test_horizon_elapsed_is_due(self):
        d = _make_test_deviation()
        now = datetime(2026, 5, 1, tzinfo=timezone.utc)
        d = schedule_adjudication(d, horizon_days=30, now=now)
        future = now + timedelta(days=31)
        assert is_adjudication_due(d, now=future) is True

    def test_no_horizon_set_not_due(self):
        d = _make_test_deviation()
        # Still in RECORDED with horizon_ends_at=None.
        assert is_adjudication_due(d) is False

    def test_adjudicated_state_not_due(self):
        d = _make_test_deviation()
        now = datetime(2026, 5, 1, tzinfo=timezone.utc)
        d = schedule_adjudication(d, horizon_days=30, now=now)
        d = transition_state(d, DeviationLifecycleState.ADJUDICATED)
        future = now + timedelta(days=60)
        # Even though horizon elapsed, terminal state means not due.
        assert is_adjudication_due(d, now=future) is False

    def test_pending_state_can_be_due(self):
        d = _make_test_deviation()
        now = datetime(2026, 5, 1, tzinfo=timezone.utc)
        d = schedule_adjudication(d, horizon_days=30, now=now)
        d = transition_state(d, DeviationLifecycleState.PENDING)
        future = now + timedelta(days=31)
        assert is_adjudication_due(d, now=future) is True


# -----------------------------------------------------------------------------
# adjudicate_deviation — outcome verdicts
# -----------------------------------------------------------------------------


class TestAdjudicateDeviation:

    def _adjudicate(self, rec_outcome, sub_outcome, n=10):
        d = _make_test_deviation()
        return adjudicate_deviation(
            d,
            observed_outcome_for_recommendation=rec_outcome,
            observed_outcome_for_substitute=sub_outcome,
            n_samples=n,
        )

    def test_insufficient_samples_pending(self):
        verdict = self._adjudicate(rec_outcome=0.1, sub_outcome=0.2, n=2)
        assert verdict.outcome == DeviationAdjudicationOutcome.PENDING_INSUFFICIENT_DATA
        assert verdict.confidence == 0.0
        assert verdict.rationale_tag == "insufficient_data"

    def test_missing_recommendation_outcome_pending(self):
        verdict = self._adjudicate(rec_outcome=None, sub_outcome=0.2, n=10)
        assert verdict.outcome == DeviationAdjudicationOutcome.PENDING_INSUFFICIENT_DATA

    def test_missing_substitute_outcome_pending(self):
        verdict = self._adjudicate(rec_outcome=0.1, sub_outcome=None, n=10)
        assert verdict.outcome == DeviationAdjudicationOutcome.PENDING_INSUFFICIENT_DATA

    def test_substitute_clearly_outperformed_confirmed(self):
        # Substitute 0.20 vs Recommendation 0.10 → 100% relative advantage
        verdict = self._adjudicate(rec_outcome=0.10, sub_outcome=0.20, n=10)
        assert verdict.outcome == DeviationAdjudicationOutcome.CONFIRMED_OVERRIDE
        assert verdict.rationale_tag == "substitute_outperformed"
        assert verdict.confidence > 0.0

    def test_recommendation_clearly_outperformed_vindicated(self):
        verdict = self._adjudicate(rec_outcome=0.20, sub_outcome=0.10, n=10)
        assert verdict.outcome == DeviationAdjudicationOutcome.SYSTEM_VINDICATED
        assert verdict.rationale_tag == "recommendation_outperformed"

    def test_no_signal_false_correction(self):
        # 0.100 vs 0.101 → ~1% relative advantage, below 5% threshold
        verdict = self._adjudicate(rec_outcome=0.100, sub_outcome=0.101, n=10)
        assert verdict.outcome == DeviationAdjudicationOutcome.FALSE_CORRECTION
        assert verdict.rationale_tag == "no_signal"

    def test_confidence_scales_with_n_samples(self):
        v_low = self._adjudicate(rec_outcome=0.1, sub_outcome=0.2, n=5)
        v_high = self._adjudicate(rec_outcome=0.1, sub_outcome=0.2, n=100)
        assert v_high.confidence > v_low.confidence

    def test_custom_thresholds_change_outcome(self):
        d = _make_test_deviation()
        # With strict 50% threshold, 20% advantage no longer counts.
        verdict = adjudicate_deviation(
            d,
            observed_outcome_for_recommendation=0.10,
            observed_outcome_for_substitute=0.12,  # 20% advantage
            n_samples=10,
            thresholds=AdjudicationThresholds(
                min_outcome_samples=5,
                confidence_for_verdict=0.6,
                min_relative_advantage=0.50,  # require 50%
            ),
        )
        assert verdict.outcome == DeviationAdjudicationOutcome.FALSE_CORRECTION

    def test_iteration_recorded(self):
        d = _make_test_deviation()
        verdict = adjudicate_deviation(
            d,
            observed_outcome_for_recommendation=0.1,
            observed_outcome_for_substitute=0.2,
            n_samples=10,
            iteration=2,
        )
        assert verdict.iteration == 2

    def test_verdict_is_pydantic_model(self):
        from adam.intelligence.dialogue_ledger.models import (
            DeviationAdjudication,
        )
        v = self._adjudicate(rec_outcome=0.1, sub_outcome=0.2, n=10)
        assert isinstance(v, DeviationAdjudication)
        # to_neo4j_props yields scalar-friendly dict.
        props = v.to_neo4j_props()
        assert "outcome" in props
        assert "confidence" in props


# -----------------------------------------------------------------------------
# A14 flag emission
# -----------------------------------------------------------------------------


class TestA14FlagEmission:

    def test_recorded_deviation_emits_flag(self):
        d = _make_test_deviation()
        flags = record_deviation_a14_flag(d)
        assert DEVIATION_PENDING_ADJUDICATION_FLAG in flags

    def test_awaiting_deviation_emits_flag(self):
        d = _make_test_deviation()
        d = transition_state(d, DeviationLifecycleState.AWAITING_OUTCOME)
        flags = record_deviation_a14_flag(d)
        assert DEVIATION_PENDING_ADJUDICATION_FLAG in flags

    def test_pending_deviation_emits_flag(self):
        d = _make_test_deviation()
        d = transition_state(d, DeviationLifecycleState.AWAITING_OUTCOME)
        d = transition_state(d, DeviationLifecycleState.PENDING)
        flags = record_deviation_a14_flag(d)
        assert DEVIATION_PENDING_ADJUDICATION_FLAG in flags

    def test_adjudicated_deviation_emits_no_flag(self):
        d = _make_test_deviation()
        d = transition_state(d, DeviationLifecycleState.AWAITING_OUTCOME)
        d = transition_state(d, DeviationLifecycleState.ADJUDICATED)
        flags = record_deviation_a14_flag(d)
        assert flags == []

    def test_is_pending_adjudication(self):
        d = _make_test_deviation()
        assert is_pending_adjudication(d) is True
        d = transition_state(d, DeviationLifecycleState.AWAITING_OUTCOME)
        assert is_pending_adjudication(d) is True
        d = transition_state(d, DeviationLifecycleState.ADJUDICATED)
        assert is_pending_adjudication(d) is False


# -----------------------------------------------------------------------------
# A14 flag identifier + retirement trigger documented
# -----------------------------------------------------------------------------


class TestA14FlagDocumented:

    def test_flag_identifier_stable(self):
        assert DEVIATION_PENDING_ADJUDICATION_FLAG == "DEVIATION_PENDING_ADJUDICATION"

    def test_retirement_trigger_documented(self):
        # Conditions pinned by string assertion: refactors that change
        # the trigger surface immediately in this test.
        assert "CONFIRMED_OVERRIDE" in DEVIATION_PENDING_RETIREMENT_TRIGGER
        assert "SYSTEM_VINDICATED" in DEVIATION_PENDING_RETIREMENT_TRIGGER
        assert "FALSE_CORRECTION" in DEVIATION_PENDING_RETIREMENT_TRIGGER
        assert "propagated to the analytics loop" in (
            DEVIATION_PENDING_RETIREMENT_TRIGGER
        )
