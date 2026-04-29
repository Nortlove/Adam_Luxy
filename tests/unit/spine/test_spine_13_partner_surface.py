"""Tests for Spine #13 — Partner Surface (Defensive Reasoning + Mechanism
Rotation + CMO Walkthrough).

Pins per directive Section 7 + Spine #13:
    1. DefensiveReasoningView reads from DecisionTrace (NOT old Why
       Library); reframed per directive Section 8.2
    2. Five layers populated correctly (one-line, counterfactual,
       decomposition, confidence, provenance)
    3. Pure-function determinism: identical traces → identical output
    4. Counterfactual surfaces the carryover-penalty narrative when
       carryover differs materially
    5. CohortDriftIndicator + FluencyFloorComplianceMetric structured
    6. compute_floor_compliance: in-band detection per directive's
       0.1-2% target
    7. MSPRTBoundaryStatus tracks crossing
    8. WalkthroughScript: 10 canonical steps per directive Section 7.3
    9. All elements structured / templated (A12 defense)
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from adam.intelligence.spine.spine_6_decision_trace import (
    AlternativeDecomposition,
    DecisionTrace,
)
from adam.intelligence.spine.spine_13_partner_surface import (
    CohortDriftIndicator,
    CohortMechanismTimepoint,
    DefensiveReasoningView,
    FluencyFloorComplianceMetric,
    MSPRTBoundaryStatus,
    MechanismRotationGraph,
    WalkthroughScript,
    WalkthroughStep,
    WalkthroughStepKind,
    compute_floor_compliance,
    make_canonical_cmo_walkthrough,
    render_from_decision_trace,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


def _make_trace_with_alts() -> DecisionTrace:
    """A DecisionTrace with chosen + 1 runner-up + 1 also-ran."""
    chosen_alt = AlternativeDecomposition(
        mechanism="authority",
        posterior_score=0.7,
        free_energy_F=0.2,
        fluency_score=0.5,
        fluency_floor_passed=True,
        posture_compatibility_score=0.5,
        carryover_correction_term=0.1,
        epistemic_bonus=0.05,
        propensity_under_TS=0.6,
        final_score=1.55,
    )
    runner_up = AlternativeDecomposition(
        mechanism="social_proof",
        posterior_score=0.5,
        free_energy_F=0.4,
        fluency_score=0.3,
        fluency_floor_passed=True,
        posture_compatibility_score=0.3,
        carryover_correction_term=0.0,
        epistemic_bonus=0.05,
        propensity_under_TS=0.3,
        final_score=1.20,
    )
    also_ran = AlternativeDecomposition(
        mechanism="scarcity",
        posterior_score=0.2,
        free_energy_F=0.6,
        fluency_score=-0.6,  # below fluency floor
        fluency_floor_passed=False,
        final_score=0.6,
    )
    return DecisionTrace(
        decision_id="d:abc",
        user_id="u:1",
        chosen_mechanism="authority",
        chosen_score=1.55,
        propensity_chosen=0.6,
        sapid="sa_d_abc",
        alternatives=[chosen_alt, runner_up, also_ran],
        page_posture="task_completion",
        page_posture_confidence=0.85,
        bid_value=1.20,
    )


# -----------------------------------------------------------------------------
# DefensiveReasoningView render
# -----------------------------------------------------------------------------


class TestDefensiveReasoningRender:

    def test_renders_one_liner_with_chosen_and_posture(self):
        trace = _make_trace_with_alts()
        view = render_from_decision_trace(trace)
        assert "authority" in view.one_line_summary
        assert "task_completion" in view.one_line_summary

    def test_renders_counterfactual_with_runner_up(self):
        trace = _make_trace_with_alts()
        view = render_from_decision_trace(trace)
        assert view.runner_up_mechanism == "social_proof"
        assert view.runner_up_score == 1.20
        assert "social_proof" in view.counterfactual_summary

    def test_no_runner_up_when_only_chosen_in_alternatives(self):
        chosen = AlternativeDecomposition(
            mechanism="authority", posterior_score=0.7,
            final_score=1.5,
        )
        trace = DecisionTrace(
            decision_id="d", user_id="u",
            chosen_mechanism="authority",
            chosen_score=1.5,
            propensity_chosen=0.5,
            alternatives=[chosen],
        )
        view = render_from_decision_trace(trace)
        assert view.runner_up_mechanism is None
        assert "single-candidate" in view.counterfactual_summary.lower()

    def test_decomposition_components_populated(self):
        trace = _make_trace_with_alts()
        view = render_from_decision_trace(trace)
        # All 5 components present.
        for key in ("posterior", "fluency", "free_energy",
                    "carryover", "epistemic"):
            assert key in view.score_components
        # Decomposition summary references components.
        assert "posterior" in view.decomposition_summary
        assert "fluency" in view.decomposition_summary

    def test_provenance_includes_decision_id_and_sapid(self):
        trace = _make_trace_with_alts()
        view = render_from_decision_trace(trace)
        assert view.provenance_links["decision_id"] == "d:abc"
        assert view.provenance_links["sapid"] == "sa_d_abc"
        assert view.provenance_links["user_id"] == "u:1"

    def test_aggregate_a14_flags_propagate(self):
        trace = _make_trace_with_alts()
        view = render_from_decision_trace(
            trace, aggregate_a14_flags=["FLAG_A", "FLAG_B"],
        )
        assert "FLAG_A" in view.discipline_flags
        assert "FLAG_B" in view.discipline_flags

    def test_carryover_penalty_narrative_when_carryover_differs(self):
        """When carryover penalty between chosen and runner-up differs
        materially, the counterfactual narrative cites carryover."""
        chosen_alt = AlternativeDecomposition(
            mechanism="authority", posterior_score=0.5,
            free_energy_F=0.2,
            fluency_score=0.5,
            fluency_floor_passed=True,
            posture_compatibility_score=0.5,
            carryover_correction_term=0.4,  # high positive priming
            epistemic_bonus=0.05,
            final_score=1.65,
        )
        runner_up = AlternativeDecomposition(
            mechanism="social_proof", posterior_score=0.7,
            free_energy_F=0.2,
            fluency_score=0.5,
            fluency_floor_passed=True,
            posture_compatibility_score=0.5,
            carryover_correction_term=-0.3,  # interference
            epistemic_bonus=0.05,
            final_score=1.40,
        )
        trace = DecisionTrace(
            decision_id="d", user_id="u",
            chosen_mechanism="authority", chosen_score=1.65,
            propensity_chosen=0.6,
            alternatives=[chosen_alt, runner_up],
        )
        view = render_from_decision_trace(trace)
        assert "carryover" in view.counterfactual_summary.lower()


class TestRenderDeterminism:

    def test_identical_inputs_produce_identical_output(self):
        trace = _make_trace_with_alts()
        v1 = render_from_decision_trace(trace)
        v2 = render_from_decision_trace(trace)
        assert v1.one_line_summary == v2.one_line_summary
        assert v1.counterfactual_summary == v2.counterfactual_summary
        assert v1.score_components == v2.score_components


# -----------------------------------------------------------------------------
# Mechanism rotation graph
# -----------------------------------------------------------------------------


class TestCohortMechanismTimepoint:

    def test_construction(self):
        tp = CohortMechanismTimepoint(
            cohort_id="status_seeker",
            mechanism="authority",
            timestamp=datetime(2026, 5, 1, tzinfo=timezone.utc),
            budget_share=0.4,
            posterior_ci_width=0.15,
            n_observations_in_window=50,
        )
        assert tp.budget_share == 0.4


class TestCohortDriftIndicator:

    def test_construction(self):
        d = CohortDriftIndicator(
            cohort_id="status_seeker",
            drift_magnitude=0.3,
            indicator_status="drifting",
        )
        assert d.indicator_status == "drifting"


class TestFluencyFloorComplianceMetric:

    def test_violation_rate_validated(self):
        with pytest.raises(ValueError, match="violation_rate"):
            FluencyFloorComplianceMetric(
                n_decisions=100, n_floor_violations=200,
                violation_rate=2.0,  # > 1
                in_target_band=False,
            )


class TestComputeFloorCompliance:

    def test_in_target_band(self):
        # Per directive: 0.1-2% target band → 0.001 to 0.02
        m = compute_floor_compliance(
            n_decisions=1000, n_floor_violations=15,  # 1.5%
        )
        assert m.in_target_band is True
        assert m.violation_rate == pytest.approx(0.015)

    def test_too_low_out_of_band(self):
        # 0% → too lax
        m = compute_floor_compliance(
            n_decisions=1000, n_floor_violations=0,
        )
        assert m.in_target_band is False

    def test_too_high_out_of_band(self):
        # 10% → too strict
        m = compute_floor_compliance(
            n_decisions=1000, n_floor_violations=100,
        )
        assert m.in_target_band is False

    def test_zero_decisions(self):
        m = compute_floor_compliance(n_decisions=0, n_floor_violations=0)
        assert m.in_target_band is False
        assert m.violation_rate == 0.0


class TestMSPRTBoundaryStatus:

    def test_no_crossing(self):
        s = MSPRTBoundaryStatus(
            upper_boundary=2.0, lower_boundary=-2.0,
            current_test_statistic=0.5,
        )
        assert s.boundary_crossed is None
        assert s.is_red_criterion_triggered is False

    def test_lower_crossing_is_red(self):
        s = MSPRTBoundaryStatus(
            upper_boundary=2.0, lower_boundary=-2.0,
            current_test_statistic=-2.5,
            boundary_crossed="lower",
            is_red_criterion_triggered=True,
        )
        assert s.is_red_criterion_triggered is True


class TestMechanismRotationGraph:

    def test_default_rolling_window_30_days(self):
        g = MechanismRotationGraph()
        assert g.rolling_window_days == 30

    def test_with_timepoints_and_drift(self):
        g = MechanismRotationGraph(
            timepoints=[CohortMechanismTimepoint(
                cohort_id="status_seeker", mechanism="authority",
                timestamp=datetime(2026, 5, 1, tzinfo=timezone.utc),
                budget_share=0.5, posterior_ci_width=0.1,
                n_observations_in_window=50,
            )],
            cohort_drift_indicators=[CohortDriftIndicator(
                cohort_id="status_seeker",
                drift_magnitude=0.05,
                indicator_status="stable",
            )],
            fluency_floor_compliance=FluencyFloorComplianceMetric(
                n_decisions=1000, n_floor_violations=10,
                violation_rate=0.01, in_target_band=True,
            ),
        )
        assert len(g.timepoints) == 1
        assert g.fluency_floor_compliance.in_target_band is True


# -----------------------------------------------------------------------------
# CMO Walkthrough script per directive Section 7.3
# -----------------------------------------------------------------------------


class TestCMOWalkthrough:

    def test_canonical_script_has_ten_steps(self):
        script = make_canonical_cmo_walkthrough()
        assert len(script.steps) == 10

    def test_step_indices_sequential(self):
        script = make_canonical_cmo_walkthrough()
        for i, step in enumerate(script.steps, start=1):
            assert step.step_index == i

    def test_canonical_script_targets_luxy(self):
        script = make_canonical_cmo_walkthrough()
        assert script.target_pilot == "luxy"

    def test_each_step_has_narrative(self):
        script = make_canonical_cmo_walkthrough()
        for step in script.steps:
            assert step.narrative
            # Narrative is human-authored prose; non-empty + reasonable length
            assert 20 < len(step.narrative) < 500

    def test_step_kinds_match_directive_section_7_3(self):
        """Per directive Section 7.3: 10 canonical step kinds."""
        script = make_canonical_cmo_walkthrough()
        kinds = [step.kind for step in script.steps]
        # The first should be SHOW_ROTATION_GRAPH
        assert kinds[0] == WalkthroughStepKind.SHOW_ROTATION_GRAPH
        # Click-into-impression appears
        assert WalkthroughStepKind.CLICK_INTO_IMPRESSION in kinds
        # Walk-do-calculus-chain
        assert WalkthroughStepKind.WALK_DO_CALCULUS_CHAIN in kinds
        # Show-counterfactual
        assert WalkthroughStepKind.SHOW_COUNTERFACTUAL in kinds
        # Show-credible-interval
        assert WalkthroughStepKind.SHOW_CREDIBLE_INTERVAL in kinds
        # Show-floor-compliance
        assert WalkthroughStepKind.SHOW_FLOOR_COMPLIANCE in kinds

    def test_step_by_index_lookup(self):
        script = make_canonical_cmo_walkthrough()
        step_5 = script.step_by_index(5)
        assert step_5 is not None
        assert step_5.step_index == 5
        # Out-of-range
        assert script.step_by_index(99) is None

    def test_walkthrough_step_narrative_is_human_authored_not_llm(self):
        """Spot-check: the canonical narratives reference structured
        cognitive vocabulary (within-subject, posterior, fluency floor,
        do-calculus, etc.) per Foundation §7 rule 11."""
        script = make_canonical_cmo_walkthrough()
        all_text = " ".join(s.narrative for s in script.steps).lower()
        for token in ("within-subject", "posterior", "do-calculus",
                      "credible interval", "carryover"):
            assert token in all_text, (
                f"Walkthrough narrative missing structural token '{token}'"
            )
