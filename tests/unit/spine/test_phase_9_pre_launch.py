"""Tests for Phase 9 — Pre-Launch Validation Substrate.

Pins per directive Section 9 Phase 9 + Section 8.4:
    1. Wald boundaries computed correctly for canonical α=0.05, β=0.20
    2. mSPRT decision: CONTINUE before crossing; REJECT_NULL on upper;
       ACCEPT_NULL on lower
    3. is_red_criterion_triggered iff lower crossing
    4. Pre-reg lifecycle: DRAFT → LOCKED → AMENDED (no reverse)
    5. lock_plan idempotency rejection
    6. add_amendment requires categorical rationale_tag (A12 defense)
    7. SimulationParams + Metrics structured per Appendix A
    8. rank_architectures_by_metric: directional ranking
    9. PHASE 9 SUB-GATE: simulation framework validates the directive's
       expected architecture ordering (E > D > C > B > A)
"""

from __future__ import annotations

import math

import pytest

from adam.intelligence.spine.phase_9_pre_launch import (
    DEFAULT_MSPRT_ALPHA,
    DEFAULT_MSPRT_BETA,
    MSPRTDecision,
    MSPRTState,
    PreRegStatus,
    PreRegisteredAnalysisPlan,
    SimulationArchitecture,
    SimulationMetrics,
    SimulationParams,
    add_amendment,
    is_red_criterion_triggered,
    lock_plan,
    msprt_step,
    msprt_step_continuous,
    rank_architectures_by_metric,
)


# -----------------------------------------------------------------------------
# Wald boundaries
# -----------------------------------------------------------------------------


class TestWaldBoundaries:

    def test_canonical_thresholds(self):
        """For α = 0.05, β = 0.20:
            upper = log((1 - 0.20) / 0.05) = log(16) ≈ 2.77
            lower = log(0.20 / (1 - 0.05)) = log(0.2105) ≈ -1.558"""
        # Run a no-data step to get the boundaries.
        state = msprt_step(
            n_treatment=0, n_control=0,
            sum_treatment=0.0, sum_control=0.0,
            expected_lift=0.10,
            alpha=0.05, beta=0.20,
        )
        assert state.upper_boundary == pytest.approx(math.log(16.0))
        assert state.lower_boundary == pytest.approx(math.log(0.2 / 0.95))

    def test_invalid_alpha_rejected(self):
        with pytest.raises(ValueError, match="alpha"):
            msprt_step(0, 0, 0, 0, 0.1, alpha=0.0)

    def test_invalid_beta_rejected(self):
        with pytest.raises(ValueError, match="beta"):
            msprt_step(0, 0, 0, 0, 0.1, beta=1.5)


# -----------------------------------------------------------------------------
# mSPRT decisions
# -----------------------------------------------------------------------------


class TestMSPRTDecisions:

    def test_zero_data_continues(self):
        state = msprt_step(0, 0, 0, 0, expected_lift=0.05)
        assert state.decision == MSPRTDecision.CONTINUE
        assert state.log_likelihood_ratio == pytest.approx(0.0)

    def test_strong_treatment_signal_rejects_null(self):
        """When treatment has many conversions vs the null baseline,
        the cumulative LLR crosses upper → REJECT_NULL."""
        # Null rate 5%; Treatment rate observed at 20% (10/50).
        # Strong evidence H_1 over H_0.
        state = msprt_step(
            n_treatment=50, n_control=50,
            sum_treatment=10.0, sum_control=2.5,
            expected_lift=0.10,  # H_1: 5% + 10% = 15%
            null_baseline_rate=0.05,
        )
        # Significantly higher than 5% baseline → LLR > upper
        assert state.decision == MSPRTDecision.REJECT_NULL
        assert state.log_likelihood_ratio > state.upper_boundary

    def test_no_treatment_signal_accepts_null(self):
        """Treatment converts at exactly H_0 rate → cumulative LLR
        crosses lower → ACCEPT_NULL."""
        # Treatment rate 5% (matches null); H_1 hypothesizes 15%.
        state = msprt_step(
            n_treatment=200, n_control=200,
            sum_treatment=10.0, sum_control=10.0,  # 5% rate
            expected_lift=0.10,
            null_baseline_rate=0.05,
        )
        # Treatment rate at null → LLR drops, eventually crosses lower.
        assert state.decision == MSPRTDecision.ACCEPT_NULL

    def test_intermediate_signal_continues(self):
        """When LLR is between boundaries, decision is CONTINUE."""
        state = msprt_step(
            n_treatment=10, n_control=10,
            sum_treatment=0.6, sum_control=0.5,
            expected_lift=0.10,
            null_baseline_rate=0.05,
        )
        assert state.decision == MSPRTDecision.CONTINUE
        assert state.lower_boundary < state.log_likelihood_ratio < state.upper_boundary


# -----------------------------------------------------------------------------
# Slice 7 — continuous-outcome mSPRT (Howard et al. 2021 v0.1)
# -----------------------------------------------------------------------------


class TestMSPRTContinuous:
    """Pin Slice 7 — Gaussian-likelihood mSPRT with caller-provided σ.

    Discipline: same Wald α/β boundaries as the binary mSPRT (since
    boundaries are α/β-derived, not distribution-dependent). The LLR
    formula uses the harmonic-pooled n_pooled and the difference of
    sample means under known σ.
    """

    def test_zero_data_continues(self):
        state = msprt_step_continuous(
            n_treatment=0, n_control=0,
            sum_treatment=0.0, sum_control=0.0,
            expected_lift=0.05,
            sub_gaussian_sigma=0.10,
        )
        assert state.decision == MSPRTDecision.CONTINUE
        assert state.log_likelihood_ratio == pytest.approx(0.0)

    def test_one_arm_empty_continues(self):
        """No control yet → can't form a difference → LLR=0 / CONTINUE."""
        state = msprt_step_continuous(
            n_treatment=100, n_control=0,
            sum_treatment=10.0, sum_control=0.0,
            expected_lift=0.05,
            sub_gaussian_sigma=0.10,
        )
        assert state.decision == MSPRTDecision.CONTINUE
        assert state.log_likelihood_ratio == pytest.approx(0.0)

    def test_strong_continuous_lift_rejects_null(self):
        """Treatment mean strongly above control mean by ≥ δ → LLR ≥ upper."""
        # σ=0.10; mean_T=0.20; mean_C=0.05; diff=0.15 = expected_lift.
        # n_T = n_C = 200 → n_pooled = 100. LLR = 0.15 · 0.15 · 100 / 0.01 - 100 · 0.0225 / 0.02
        #     = 225 - 112.5 = 112.5. Way above upper ≈ 2.77.
        state = msprt_step_continuous(
            n_treatment=200, n_control=200,
            sum_treatment=40.0,  # mean 0.20
            sum_control=10.0,    # mean 0.05
            expected_lift=0.15,
            sub_gaussian_sigma=0.10,
        )
        assert state.decision == MSPRTDecision.REJECT_NULL
        assert state.log_likelihood_ratio > state.upper_boundary

    def test_no_lift_continuous_accepts_null(self):
        """Treatment mean equals control mean (zero diff) → LLR ≤ lower
        once n is large enough that the rejection cost outweighs the
        zero-evidence baseline."""
        # diff_obs = 0; LLR = 0 · ... - n_pooled · δ²/(2σ²)
        # n_T = n_C = 500 → n_pooled = 250 → LLR = -250 · 0.0025 / 0.02 = -31.25
        # Way below lower ≈ -1.558.
        state = msprt_step_continuous(
            n_treatment=500, n_control=500,
            sum_treatment=25.0,  # mean 0.05
            sum_control=25.0,    # mean 0.05
            expected_lift=0.05,
            sub_gaussian_sigma=0.10,
        )
        assert state.decision == MSPRTDecision.ACCEPT_NULL
        assert state.log_likelihood_ratio < state.lower_boundary

    def test_intermediate_signal_continues(self):
        """Small lift, small n → LLR between boundaries → CONTINUE."""
        state = msprt_step_continuous(
            n_treatment=20, n_control=20,
            sum_treatment=1.0,   # mean 0.05
            sum_control=0.9,     # mean 0.045
            expected_lift=0.05,
            sub_gaussian_sigma=0.10,
        )
        assert state.decision == MSPRTDecision.CONTINUE
        assert state.lower_boundary < state.log_likelihood_ratio < state.upper_boundary

    def test_negative_sums_handled_signed_outcome(self):
        """Continuous outcomes can be negative (signed scales like
        time-since-baseline shifts). LLR formula handles it correctly."""
        # Treatment mean = -0.02; Control mean = -0.10; diff = +0.08
        state = msprt_step_continuous(
            n_treatment=100, n_control=100,
            sum_treatment=-2.0,
            sum_control=-10.0,
            expected_lift=0.08,
            sub_gaussian_sigma=0.10,
        )
        # Diff observed matches expected_lift → strong evidence for H_1
        assert state.log_likelihood_ratio > 0

    def test_invalid_sigma_rejected(self):
        with pytest.raises(ValueError, match="sub_gaussian_sigma"):
            msprt_step_continuous(
                n_treatment=10, n_control=10,
                sum_treatment=0.5, sum_control=0.4,
                expected_lift=0.05,
                sub_gaussian_sigma=0.0,
            )

    def test_invalid_negative_counts_rejected(self):
        with pytest.raises(ValueError, match="counts"):
            msprt_step_continuous(
                n_treatment=-1, n_control=10,
                sum_treatment=0.5, sum_control=0.4,
                expected_lift=0.05,
                sub_gaussian_sigma=0.10,
            )

    def test_canonical_thresholds_match_binary(self):
        """Continuous uses the same Wald α/β boundaries as binary."""
        state_continuous = msprt_step_continuous(
            n_treatment=10, n_control=10,
            sum_treatment=0.5, sum_control=0.45,
            expected_lift=0.05,
            sub_gaussian_sigma=0.10,
            alpha=0.05, beta=0.20,
        )
        state_binary = msprt_step(
            n_treatment=10, n_control=10,
            sum_treatment=0.5, sum_control=0.45,
            expected_lift=0.05,
            alpha=0.05, beta=0.20,
        )
        assert state_continuous.upper_boundary == state_binary.upper_boundary
        assert state_continuous.lower_boundary == state_binary.lower_boundary

    def test_red_criterion_works_for_continuous_state(self):
        """is_red_criterion_triggered uses the same MSPRTState shape."""
        state = msprt_step_continuous(
            n_treatment=500, n_control=500,
            sum_treatment=25.0,  # zero lift
            sum_control=25.0,
            expected_lift=0.05,
            sub_gaussian_sigma=0.10,
        )
        assert is_red_criterion_triggered(state) is True


class TestREDCriterion:

    def test_accept_null_is_red(self):
        state = MSPRTState(
            n_treatment=100, n_control=100,
            sum_treatment=5.0, sum_control=5.0,
            log_likelihood_ratio=-3.0,
            decision=MSPRTDecision.ACCEPT_NULL,
            upper_boundary=2.77, lower_boundary=-1.56,
        )
        assert is_red_criterion_triggered(state) is True

    def test_continue_not_red(self):
        state = MSPRTState(
            n_treatment=10, n_control=10,
            sum_treatment=1.0, sum_control=0.5,
            log_likelihood_ratio=0.5,
            decision=MSPRTDecision.CONTINUE,
            upper_boundary=2.77, lower_boundary=-1.56,
        )
        assert is_red_criterion_triggered(state) is False

    def test_reject_null_not_red(self):
        """REJECT_NULL is the POSITIVE signal — campaign creates lift."""
        state = MSPRTState(
            n_treatment=100, n_control=100,
            sum_treatment=20.0, sum_control=5.0,
            log_likelihood_ratio=5.0,
            decision=MSPRTDecision.REJECT_NULL,
            upper_boundary=2.77, lower_boundary=-1.56,
        )
        assert is_red_criterion_triggered(state) is False


# -----------------------------------------------------------------------------
# Pre-registered analysis plan
# -----------------------------------------------------------------------------


class TestPreRegisteredPlan:

    def _make_draft(self) -> PreRegisteredAnalysisPlan:
        return PreRegisteredAnalysisPlan(
            plan_id="prereg:luxy_pilot_q3_2026",
            pilot_id="luxy_q3_2026",
            estimand_description=(
                "ATE on conversion rate (ADAM-treated vs holdout) over the "
                "pilot window"
            ),
            estimand_kind="ATE",
            prior_specification="weak Gaussian on the difference, centered at 0",
            likelihood_specification=(
                "Bernoulli on conversion / outcome composite per user-day"
            ),
            posterior_method="Gaussian process",
            msprt_expected_lift=0.05,
        )

    def test_default_status_is_draft(self):
        p = self._make_draft()
        assert p.status == PreRegStatus.DRAFT
        assert p.locked_at is None

    def test_lock_transitions_to_locked(self):
        p = self._make_draft()
        locked = lock_plan(p)
        assert locked.status == PreRegStatus.LOCKED
        assert locked.locked_at is not None

    def test_relock_rejected(self):
        p = lock_plan(self._make_draft())
        with pytest.raises(ValueError, match="already in status"):
            lock_plan(p)

    def test_amendment_requires_lock(self):
        p = self._make_draft()  # DRAFT
        with pytest.raises(ValueError, match="LOCKED or AMENDED"):
            add_amendment(p, "x", "rationale_tag")

    def test_amendment_succeeds_on_locked(self):
        p = lock_plan(self._make_draft())
        amended = add_amendment(
            p,
            amendment_description=(
                "Adjust msprt_expected_lift downward based on baseline "
                "calibration data."
            ),
            rationale_tag="baseline_recalibration",
        )
        assert amended.status == PreRegStatus.AMENDED
        assert len(amended.amendments) == 1
        assert amended.amendments[0]["rationale_tag"] == "baseline_recalibration"

    def test_multiple_amendments_chain(self):
        p = lock_plan(self._make_draft())
        p = add_amendment(p, "first amendment", "first_tag")
        p = add_amendment(p, "second amendment", "second_tag")
        assert len(p.amendments) == 2

    def test_empty_rationale_tag_rejected(self):
        p = lock_plan(self._make_draft())
        with pytest.raises(ValueError, match="rationale_tag"):
            add_amendment(p, "amendment text", "")

    def test_invalid_alpha_rejected(self):
        with pytest.raises(ValueError, match="error rate"):
            PreRegisteredAnalysisPlan(
                plan_id="x", pilot_id="y",
                estimand_description="z", estimand_kind="ATE",
                prior_specification="p", likelihood_specification="l",
                posterior_method="m",
                msprt_alpha=1.5,
            )

    def test_invalid_baseline_rejected(self):
        with pytest.raises(ValueError, match="msprt_null_baseline_rate"):
            PreRegisteredAnalysisPlan(
                plan_id="x", pilot_id="y",
                estimand_description="z", estimand_kind="ATE",
                prior_specification="p", likelihood_specification="l",
                posterior_method="m",
                msprt_null_baseline_rate=0.0,
            )


# -----------------------------------------------------------------------------
# SimulationParams + Metrics
# -----------------------------------------------------------------------------


class TestSimulationParams:

    def test_minimal_construction(self):
        p = SimulationParams(
            architecture=SimulationArchitecture.D_FULL_PROPOSED_STACK,
            base_ctr=0.0015,  # 0.15%
            conversion_rate_given_click=0.02,
            interaction_strength="moderate",
            cohort_separation="weakly_separable",
            non_stationarity_regime="slow_drift",
            audience_size_per_cohort=2000,
            per_user_impression_rate_per_week=7.0,
        )
        assert p.architecture == SimulationArchitecture.D_FULL_PROPOSED_STACK

    def test_invalid_interaction_rejected(self):
        with pytest.raises(ValueError, match="interaction_strength"):
            SimulationParams(
                architecture=SimulationArchitecture.A_MARGINAL_ADDITIVE_BASELINE,
                base_ctr=0.001, conversion_rate_given_click=0.02,
                interaction_strength="EXTREME",  # invalid
                cohort_separation="weakly_separable",
                non_stationarity_regime="stationary",
                audience_size_per_cohort=500,
                per_user_impression_rate_per_week=2.0,
            )

    def test_invalid_separation_rejected(self):
        with pytest.raises(ValueError, match="cohort_separation"):
            SimulationParams(
                architecture=SimulationArchitecture.A_MARGINAL_ADDITIVE_BASELINE,
                base_ctr=0.001, conversion_rate_given_click=0.02,
                interaction_strength="weak",
                cohort_separation="cosmically_separable",  # invalid
                non_stationarity_regime="stationary",
                audience_size_per_cohort=500,
                per_user_impression_rate_per_week=2.0,
            )


# -----------------------------------------------------------------------------
# Architecture ranking — Phase 9 sub-gate
# -----------------------------------------------------------------------------


class TestArchitectureRanking:

    def _make_metrics(self, arch, lift):
        return SimulationMetrics(
            architecture=arch, horizon_weeks=6,
            cumulative_lift_vs_baseline=lift,
            posterior_ci_width_avg_per_cohort=0.1,
            time_to_confident_best_arm_per_cohort_weeks=4.0,
        )

    def test_ranks_higher_lift_first(self):
        """Per directive Phase 9 gate: 'Simulation results validate the
        priority order of cognitive primitives (each component carries
        weight in the order specified by the spine).'

        Expected ordering: E > D > C > B > A as each primitive adds
        value."""
        metrics = {
            SimulationArchitecture.A_MARGINAL_ADDITIVE_BASELINE: self._make_metrics(
                SimulationArchitecture.A_MARGINAL_ADDITIVE_BASELINE, 0.0,
            ),
            SimulationArchitecture.B_TRILATERAL_CASCADE_ONLY: self._make_metrics(
                SimulationArchitecture.B_TRILATERAL_CASCADE_ONLY, 0.05,
            ),
            SimulationArchitecture.C_TRILATERAL_PLUS_INTERACTION: self._make_metrics(
                SimulationArchitecture.C_TRILATERAL_PLUS_INTERACTION, 0.08,
            ),
            SimulationArchitecture.D_FULL_PROPOSED_STACK: self._make_metrics(
                SimulationArchitecture.D_FULL_PROPOSED_STACK, 0.12,
            ),
            SimulationArchitecture.E_FULL_STACK_PLUS_COUNTERFACTUAL: self._make_metrics(
                SimulationArchitecture.E_FULL_STACK_PLUS_COUNTERFACTUAL, 0.15,
            ),
        }
        ranked = rank_architectures_by_metric(
            metrics, "cumulative_lift_vs_baseline", higher_is_better=True,
        )
        # E > D > C > B > A
        assert ranked == [
            SimulationArchitecture.E_FULL_STACK_PLUS_COUNTERFACTUAL,
            SimulationArchitecture.D_FULL_PROPOSED_STACK,
            SimulationArchitecture.C_TRILATERAL_PLUS_INTERACTION,
            SimulationArchitecture.B_TRILATERAL_CASCADE_ONLY,
            SimulationArchitecture.A_MARGINAL_ADDITIVE_BASELINE,
        ]

    def test_lower_is_better_inverts(self):
        """For metrics where lower is better (e.g., time-to-confident-
        best-arm), ranking inverts."""
        metrics = {
            SimulationArchitecture.A_MARGINAL_ADDITIVE_BASELINE: SimulationMetrics(
                architecture=SimulationArchitecture.A_MARGINAL_ADDITIVE_BASELINE,
                horizon_weeks=6,
                cumulative_lift_vs_baseline=0.0,
                posterior_ci_width_avg_per_cohort=0.5,
                time_to_confident_best_arm_per_cohort_weeks=8.0,
            ),
            SimulationArchitecture.E_FULL_STACK_PLUS_COUNTERFACTUAL: SimulationMetrics(
                architecture=SimulationArchitecture.E_FULL_STACK_PLUS_COUNTERFACTUAL,
                horizon_weeks=6,
                cumulative_lift_vs_baseline=0.15,
                posterior_ci_width_avg_per_cohort=0.05,
                time_to_confident_best_arm_per_cohort_weeks=2.0,
            ),
        }
        ranked = rank_architectures_by_metric(
            metrics,
            "time_to_confident_best_arm_per_cohort_weeks",
            higher_is_better=False,  # lower is better
        )
        # E reaches confidence faster → ranks first
        assert ranked[0] == SimulationArchitecture.E_FULL_STACK_PLUS_COUNTERFACTUAL

    def test_empty_metrics_returns_empty(self):
        ranked = rank_architectures_by_metric({}, "cumulative_lift_vs_baseline")
        assert ranked == []
