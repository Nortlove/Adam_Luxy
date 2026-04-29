"""Tests for Phase 10 — Launch Sequence + 8 RED-criteria.

Pins per directive Section 9 Phase 10 verbatim:
    1-8: each of the 8 RED-criteria triggers correctly per directive
       thresholds
    9. ANY single triggered RED → launch DEFERRED
    10. Phase progression: PRE_LAUNCH → SOFT_10 → RAMP_50 → FULL_100
        with 7-day dwell at SOFT_10 + RAMP_50 per directive
    11. RED-criterion at any phase → DEFERRED
    12. Non-RED issues do NOT block (sanity)
"""

from __future__ import annotations

import pytest

from adam.intelligence.spine.phase_10_launch_sequence import (
    CriterionCheck,
    LaunchGateResult,
    LaunchPhase,
    PhaseTransitionDecision,
    RED_BID_TIME_LATENCY_P99_OVER_BUDGET_MS_MAX,
    RED_DECISION_TRACE_EMISSION_RATE_MIN,
    RED_FLUENCY_FLOOR_VIOLATION_RATE_MAX,
    RED_IDENTITY_STABILITY_COLLAPSE_FRACTION_MAX,
    RED_SAPID_ROUND_TRIP_RATE_MIN,
    REDCriterion,
    check_bid_time_latency_p99,
    check_cmo_uncomfortable,
    check_decision_trace_emission,
    check_fluency_floor_violation,
    check_metaphor_coherence_failed,
    check_msprt_lower_crossed,
    check_posterior_pathology,
    check_sapid_round_trip,
    evaluate_launch_gate,
    should_advance_phase,
)


# -----------------------------------------------------------------------------
# 8 RED-criterion checks (one per directive criterion)
# -----------------------------------------------------------------------------


class TestFluencyFloorViolationCheck:

    def test_in_band_does_not_trigger(self):
        # 1% violation < 5% threshold
        c = check_fluency_floor_violation(
            n_decisions=1000, n_floor_violations=10,
        )
        assert c.triggered is False
        assert c.observed_value == pytest.approx(0.01)

    def test_at_threshold_does_not_trigger(self):
        # 5% exactly = threshold; per directive '>5%' triggers
        c = check_fluency_floor_violation(
            n_decisions=1000, n_floor_violations=50,
        )
        assert c.triggered is False

    def test_above_threshold_triggers(self):
        # 6% > 5%
        c = check_fluency_floor_violation(
            n_decisions=1000, n_floor_violations=60,
        )
        assert c.triggered is True
        assert c.criterion == REDCriterion.FLUENCY_FLOOR_VIOLATION

    def test_zero_decisions_handled(self):
        c = check_fluency_floor_violation(0, 0)
        assert c.triggered is False
        assert c.observed_value == 0.0


class TestDecisionTraceEmissionCheck:

    def test_high_emission_does_not_trigger(self):
        c = check_decision_trace_emission(
            n_bids=1000, n_traces_emitted=999,
        )
        # 99.9% > 99% threshold
        assert c.triggered is False

    def test_at_threshold_does_not_trigger(self):
        c = check_decision_trace_emission(
            n_bids=100, n_traces_emitted=99,
        )
        # 99% exactly; '<99%' triggers, so 99% is borderline OK
        assert c.triggered is False

    def test_below_threshold_triggers(self):
        c = check_decision_trace_emission(
            n_bids=1000, n_traces_emitted=980,
        )
        # 98% < 99%
        assert c.triggered is True
        assert c.criterion == REDCriterion.DECISION_TRACE_EMISSION

    def test_zero_bids_does_not_trigger(self):
        c = check_decision_trace_emission(0, 0)
        # No bids → rate defaults to 1.0 (no events to fail emission)
        assert c.triggered is False


class TestPosteriorPathologyCheck:

    def test_low_collapse_does_not_trigger(self):
        # 10% collapse < 30% threshold
        c = check_posterior_pathology(
            n_users_active=1000, n_users_with_collapsed_identity_stability=100,
        )
        assert c.triggered is False

    def test_above_threshold_triggers(self):
        # 35% collapse > 30%
        c = check_posterior_pathology(
            n_users_active=1000, n_users_with_collapsed_identity_stability=350,
        )
        assert c.triggered is True
        assert c.criterion == REDCriterion.POSTERIOR_PATHOLOGY

    def test_zero_users_handled(self):
        c = check_posterior_pathology(0, 0)
        assert c.triggered is False


class TestMSPRTLowerCrossedCheck:

    def test_continue_does_not_trigger(self):
        c = check_msprt_lower_crossed("continue")
        assert c.triggered is False

    def test_reject_null_does_not_trigger(self):
        """REJECT_NULL is the POSITIVE signal; not a RED criterion."""
        c = check_msprt_lower_crossed("reject_null")
        assert c.triggered is False

    def test_accept_null_triggers(self):
        c = check_msprt_lower_crossed("accept_null")
        assert c.triggered is True
        assert c.criterion == REDCriterion.MSPRT_LOWER_CROSSED


class TestCMOUncomfortableCheck:

    def test_comfortable_does_not_trigger(self):
        c = check_cmo_uncomfortable("comfortable")
        assert c.triggered is False

    def test_uncomfortable_triggers(self):
        c = check_cmo_uncomfortable("uncomfortable")
        assert c.triggered is True
        assert c.criterion == REDCriterion.CMO_UNCOMFORTABLE

    def test_pending_does_not_trigger(self):
        # Pending review is not a RED — it's a hold, not a fail
        c = check_cmo_uncomfortable("pending")
        assert c.triggered is False


class TestMetaphorCoherenceFailedCheck:

    def test_zero_failures_does_not_trigger(self):
        c = check_metaphor_coherence_failed(
            n_creatives_in_rotation=10, n_creatives_failed_spot_check=0,
        )
        assert c.triggered is False

    def test_any_failure_triggers(self):
        """Per directive: 'ANY creative in rotation fails' triggers RED.
        Not a rate threshold — one bad creative is sufficient."""
        c = check_metaphor_coherence_failed(
            n_creatives_in_rotation=20, n_creatives_failed_spot_check=1,
        )
        assert c.triggered is True
        assert c.criterion == REDCriterion.METAPHOR_COHERENCE_FAILED


class TestBidTimeLatencyP99Check:

    def test_within_budget_does_not_trigger(self):
        # p99 100ms; budget 100ms; over_budget = 0; threshold 120ms.
        # 0 < 120 → not triggered.
        c = check_bid_time_latency_p99(
            p99_latency_ms=100.0, stackadapt_budget_ms=100.0,
        )
        assert c.triggered is False

    def test_within_tolerance_does_not_trigger(self):
        # p99 200ms; budget 100ms; over = 100. 100 < 120 → not triggered.
        c = check_bid_time_latency_p99(
            p99_latency_ms=200.0, stackadapt_budget_ms=100.0,
        )
        assert c.triggered is False

    def test_above_tolerance_triggers(self):
        # p99 230ms; budget 100ms; over = 130. 130 > 120 → triggered.
        c = check_bid_time_latency_p99(
            p99_latency_ms=230.0, stackadapt_budget_ms=100.0,
        )
        assert c.triggered is True
        assert c.criterion == REDCriterion.BID_TIME_LATENCY_P99


class TestSapidRoundTripCheck:

    def test_above_threshold_does_not_trigger(self):
        c = check_sapid_round_trip(0.97)  # 97% > 95%
        assert c.triggered is False

    def test_at_threshold_does_not_trigger(self):
        c = check_sapid_round_trip(0.95)
        # '<95%' triggers; 95% exactly does not
        assert c.triggered is False

    def test_below_threshold_triggers(self):
        c = check_sapid_round_trip(0.93)
        assert c.triggered is True
        assert c.criterion == REDCriterion.SAPID_ROUND_TRIP


# -----------------------------------------------------------------------------
# Aggregate launch gate
# -----------------------------------------------------------------------------


class TestEvaluateLaunchGate:

    def test_all_green_no_trigger(self):
        checks = [
            check_fluency_floor_violation(1000, 10),
            check_decision_trace_emission(1000, 999),
            check_posterior_pathology(1000, 100),
            check_msprt_lower_crossed("continue"),
            check_cmo_uncomfortable("comfortable"),
            check_metaphor_coherence_failed(20, 0),
            check_bid_time_latency_p99(120.0, 100.0),
            check_sapid_round_trip(0.99),
        ]
        result = evaluate_launch_gate(checks)
        assert result.any_triggered is False
        assert result.triggered_criteria == []

    def test_any_one_red_triggers_aggregate(self):
        """Per directive: ANY ONE triggered criterion defers launch."""
        checks = [
            check_fluency_floor_violation(1000, 10),  # OK
            check_decision_trace_emission(1000, 999),  # OK
            check_sapid_round_trip(0.93),  # RED
        ]
        result = evaluate_launch_gate(checks)
        assert result.any_triggered is True
        assert REDCriterion.SAPID_ROUND_TRIP in result.triggered_criteria

    def test_multiple_red_all_recorded(self):
        checks = [
            check_fluency_floor_violation(1000, 100),  # 10% > 5% RED
            check_sapid_round_trip(0.85),  # RED
            check_msprt_lower_crossed("accept_null"),  # RED
        ]
        result = evaluate_launch_gate(checks)
        assert len(result.triggered_criteria) == 3


# -----------------------------------------------------------------------------
# Phase progression
# -----------------------------------------------------------------------------


class TestShouldAdvancePhase:

    def _all_green_gate(self) -> LaunchGateResult:
        return evaluate_launch_gate([
            check_fluency_floor_violation(1000, 10),
            check_decision_trace_emission(1000, 999),
            check_posterior_pathology(1000, 100),
            check_msprt_lower_crossed("continue"),
            check_cmo_uncomfortable("comfortable"),
            check_metaphor_coherence_failed(20, 0),
            check_bid_time_latency_p99(120.0, 100.0),
            check_sapid_round_trip(0.99),
        ])

    def test_pre_launch_to_soft_10_when_green(self):
        decision = should_advance_phase(
            LaunchPhase.PRE_LAUNCH, self._all_green_gate(),
        )
        assert decision.proposed_next_phase == LaunchPhase.SOFT_10
        assert decision.decision_is_advance is True

    def test_soft_10_to_ramp_50_after_week(self):
        decision = should_advance_phase(
            LaunchPhase.SOFT_10, self._all_green_gate(),
            days_in_current_phase=7.0,
        )
        assert decision.proposed_next_phase == LaunchPhase.RAMP_50
        assert decision.decision_is_advance is True

    def test_soft_10_holds_within_first_week(self):
        decision = should_advance_phase(
            LaunchPhase.SOFT_10, self._all_green_gate(),
            days_in_current_phase=3.0,
        )
        assert decision.proposed_next_phase == LaunchPhase.SOFT_10
        assert decision.decision_is_advance is False

    def test_ramp_50_to_full_after_second_week(self):
        decision = should_advance_phase(
            LaunchPhase.RAMP_50, self._all_green_gate(),
            days_in_current_phase=8.0,
        )
        assert decision.proposed_next_phase == LaunchPhase.FULL_100
        assert decision.decision_is_advance is True

    def test_full_100_stays_full(self):
        decision = should_advance_phase(
            LaunchPhase.FULL_100, self._all_green_gate(),
            days_in_current_phase=30.0,
        )
        assert decision.proposed_next_phase == LaunchPhase.FULL_100
        assert decision.decision_is_advance is False

    def test_red_in_soft_10_defers(self):
        gate = evaluate_launch_gate([
            check_sapid_round_trip(0.85),  # RED
        ])
        decision = should_advance_phase(
            LaunchPhase.SOFT_10, gate, days_in_current_phase=3.0,
        )
        assert decision.proposed_next_phase == LaunchPhase.DEFERRED
        assert decision.decision_is_advance is False
        assert REDCriterion.SAPID_ROUND_TRIP in decision.blocking_criteria

    def test_red_in_pre_launch_defers(self):
        gate = evaluate_launch_gate([
            check_fluency_floor_violation(1000, 100),  # RED
        ])
        decision = should_advance_phase(LaunchPhase.PRE_LAUNCH, gate)
        assert decision.proposed_next_phase == LaunchPhase.DEFERRED

    def test_red_in_ramp_50_defers(self):
        gate = evaluate_launch_gate([
            check_msprt_lower_crossed("accept_null"),  # RED
        ])
        decision = should_advance_phase(
            LaunchPhase.RAMP_50, gate, days_in_current_phase=8.0,
        )
        assert decision.proposed_next_phase == LaunchPhase.DEFERRED

    def test_deferred_stays_deferred(self):
        decision = should_advance_phase(
            LaunchPhase.DEFERRED, self._all_green_gate(),
        )
        assert decision.proposed_next_phase == LaunchPhase.DEFERRED
        assert "deferred" in decision.rationale.lower()


# -----------------------------------------------------------------------------
# Phase 10 sub-gate sanity
# -----------------------------------------------------------------------------


class TestPhase10Sanity:
    """Sub-gate spot checks: the full set of 8 criteria covers exactly
    the directive's enumerated set."""

    def test_eight_criteria_per_directive(self):
        all_kinds = {c.value for c in REDCriterion}
        expected = {
            "fluency_floor_violation",
            "decision_trace_emission",
            "posterior_pathology",
            "msprt_lower_crossed",
            "cmo_uncomfortable",
            "metaphor_coherence_failed",
            "bid_time_latency_p99",
            "sapid_round_trip",
        }
        assert all_kinds == expected

    def test_thresholds_match_directive_verbatim(self):
        """Pin the directive's exact thresholds."""
        # >5% fluency violation triggers
        assert RED_FLUENCY_FLOOR_VIOLATION_RATE_MAX == 0.05
        # <99% trace emission triggers
        assert RED_DECISION_TRACE_EMISSION_RATE_MIN == 0.99
        # >30% identity-stability collapse triggers
        assert RED_IDENTITY_STABILITY_COLLAPSE_FRACTION_MAX == 0.30
        # >120ms p99 above budget triggers
        assert RED_BID_TIME_LATENCY_P99_OVER_BUDGET_MS_MAX == 120.0
        # <95% sapid round-trip triggers
        assert RED_SAPID_ROUND_TRIP_RATE_MIN == 0.95
