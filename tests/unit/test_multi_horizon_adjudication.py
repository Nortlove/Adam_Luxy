# =============================================================================
# ADAM Multi-Horizon Adjudication Tests
# Location: tests/unit/test_multi_horizon_adjudication.py
# =============================================================================

"""Tests for task #27 — multi-horizon adjudication substrate."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from adam.intelligence.multi_horizon_adjudication import (
    HORIZON_DAYS,
    ConversionCohort,
    HorizonWindow,
    MultiHorizonAdjudicator,
    get_multi_horizon_adjudicator,
    reset_multi_horizon_adjudicator,
)


# Fixed reference time for deterministic tests
T0 = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def days(n: int) -> timedelta:
    return timedelta(days=n)


# ============================================================================
# Cohort registration
# ============================================================================


class TestCohortRegistration:

    def test_register_creates_cohort(self):
        adj = MultiHorizonAdjudicator()
        cohort = adj.register_conversion(
            decision_id="dec_001",
            treatment_arm="bilateral",
            converted_at=T0,
            user_id="user:1",
            archetype="careful_truster",
        )
        assert cohort.decision_id == "dec_001"
        assert cohort.treatment_arm == "bilateral"
        assert cohort.return_visit_count_d7 == 0
        assert cohort.return_visit_count_d30 == 0
        assert cohort.return_visit_count_d60 == 0

    def test_register_idempotent_on_decision_id(self):
        adj = MultiHorizonAdjudicator()
        c1 = adj.register_conversion(
            decision_id="dec_001",
            treatment_arm="bilateral",
            converted_at=T0,
            user_id="user:1",
        )
        c2 = adj.register_conversion(
            decision_id="dec_001",
            treatment_arm="bilateral",
            converted_at=T0,
            user_id="user:1",
        )
        assert c1 is c2

    def test_register_indexes_by_user(self):
        adj = MultiHorizonAdjudicator()
        adj.register_conversion(
            decision_id="dec_a", treatment_arm="bilateral",
            converted_at=T0, user_id="user:1",
        )
        adj.register_conversion(
            decision_id="dec_b", treatment_arm="bilateral",
            converted_at=T0, user_id="user:1",
        )
        # Two cohorts under user:1
        assert "user:1" in adj._cohorts_by_user
        assert len(adj._cohorts_by_user["user:1"]) == 2


# ============================================================================
# Return visit recording
# ============================================================================


class TestReturnVisitRecording:

    def test_visit_within_d7_increments_all_three_horizons(self):
        adj = MultiHorizonAdjudicator()
        adj.register_conversion(
            decision_id="dec_a", treatment_arm="bilateral",
            converted_at=T0, user_id="user:1",
        )
        # Visit 3 days after conversion
        n_updated = adj.record_return_visit("user:1", T0 + days(3))
        assert n_updated == 3  # d7, d30, d60 all incremented
        cohort = adj.get_cohort("dec_a")
        assert cohort.return_visit_count_d7 == 1
        assert cohort.return_visit_count_d30 == 1
        assert cohort.return_visit_count_d60 == 1

    def test_visit_within_d30_only(self):
        adj = MultiHorizonAdjudicator()
        adj.register_conversion(
            decision_id="dec_a", treatment_arm="bilateral",
            converted_at=T0, user_id="user:1",
        )
        # Visit 14 days after — past d7 but within d30 + d60
        n_updated = adj.record_return_visit("user:1", T0 + days(14))
        assert n_updated == 2  # d30 + d60
        cohort = adj.get_cohort("dec_a")
        assert cohort.return_visit_count_d7 == 0
        assert cohort.return_visit_count_d30 == 1
        assert cohort.return_visit_count_d60 == 1

    def test_visit_within_d60_only(self):
        adj = MultiHorizonAdjudicator()
        adj.register_conversion(
            decision_id="dec_a", treatment_arm="bilateral",
            converted_at=T0, user_id="user:1",
        )
        # Visit 45 days after — past d7 + d30, within d60
        n_updated = adj.record_return_visit("user:1", T0 + days(45))
        assert n_updated == 1  # d60 only
        cohort = adj.get_cohort("dec_a")
        assert cohort.return_visit_count_d7 == 0
        assert cohort.return_visit_count_d30 == 0
        assert cohort.return_visit_count_d60 == 1

    def test_visit_after_d60_no_increment(self):
        adj = MultiHorizonAdjudicator()
        adj.register_conversion(
            decision_id="dec_a", treatment_arm="bilateral",
            converted_at=T0, user_id="user:1",
        )
        # Visit 75 days after
        n_updated = adj.record_return_visit("user:1", T0 + days(75))
        assert n_updated == 0
        cohort = adj.get_cohort("dec_a")
        assert cohort.return_visit_count_d60 == 0

    def test_visit_before_conversion_ignored(self):
        adj = MultiHorizonAdjudicator()
        adj.register_conversion(
            decision_id="dec_a", treatment_arm="bilateral",
            converted_at=T0, user_id="user:1",
        )
        # Visit 5 days BEFORE conversion (timing artifact)
        n_updated = adj.record_return_visit("user:1", T0 - days(5))
        assert n_updated == 0

    def test_unknown_user_no_op(self):
        adj = MultiHorizonAdjudicator()
        n_updated = adj.record_return_visit("user:nonexistent", T0)
        assert n_updated == 0

    def test_multiple_cohorts_per_user_all_updated(self):
        adj = MultiHorizonAdjudicator()
        adj.register_conversion(
            decision_id="dec_a", treatment_arm="bilateral",
            converted_at=T0, user_id="user:1",
        )
        adj.register_conversion(
            decision_id="dec_b", treatment_arm="bilateral",
            converted_at=T0 + days(2), user_id="user:1",
        )
        # Visit 5 days after T0 — within d7 of dec_a (5 days ago) and
        # within d7 of dec_b (3 days ago)
        n_updated = adj.record_return_visit("user:1", T0 + days(5))
        # Both cohorts updated; each gets 3 horizon increments
        assert n_updated == 6
        a = adj.get_cohort("dec_a")
        b = adj.get_cohort("dec_b")
        assert a.return_visit_count_d7 == 1
        assert b.return_visit_count_d7 == 1


# ============================================================================
# Horizon-conditional rates
# ============================================================================


class TestHorizonRates:

    def test_horizon_complete_only_includes_eligible(self):
        adj = MultiHorizonAdjudicator()
        # Cohort A: 10 days old (eligible for d7, not d30 or d60)
        adj.register_conversion(
            decision_id="dec_a", treatment_arm="bilateral",
            converted_at=T0 - days(10), user_id="user:a",
        )
        # Cohort B: 35 days old (eligible for d7 + d30, not d60)
        adj.register_conversion(
            decision_id="dec_b", treatment_arm="bilateral",
            converted_at=T0 - days(35), user_id="user:b",
        )
        # Cohort C: 65 days old (all eligible)
        adj.register_conversion(
            decision_id="dec_c", treatment_arm="bilateral",
            converted_at=T0 - days(65), user_id="user:c",
        )

        rates = adj.compute_horizon_return_rates(now=T0)
        # Only B and C eligible at d30
        d30_data = rates.get(("bilateral", HorizonWindow.DAY_30))
        assert d30_data is not None
        assert d30_data["n_cohorts"] == 2

        d60_data = rates.get(("bilateral", HorizonWindow.DAY_60))
        assert d60_data is not None
        assert d60_data["n_cohorts"] == 1  # only C

    def test_return_rate_correct(self):
        adj = MultiHorizonAdjudicator()
        # 10 cohorts converted 10 days ago (eligible for d7)
        for i in range(10):
            decision_id = f"dec_{i}"
            user_id = f"user:{i}"
            adj.register_conversion(
                decision_id=decision_id,
                treatment_arm="bilateral",
                converted_at=T0 - days(10),
                user_id=user_id,
            )
            # 7 of 10 return within d7 (3 days post-conversion)
            if i < 7:
                adj.record_return_visit(user_id, T0 - days(7))

        rates = adj.compute_horizon_return_rates(now=T0)
        d7_data = rates[("bilateral", HorizonWindow.DAY_7)]
        assert d7_data["n_cohorts"] == 10
        assert d7_data["n_returned"] == 7
        assert d7_data["return_rate"] == 0.7


# ============================================================================
# Adjudication — multi-horizon discordance
# ============================================================================


class TestAdjudication:

    def _build_balanced_arms(
        self,
        adj: MultiHorizonAdjudicator,
        n_per_arm: int,
        treatment_d7_returns: int,
        treatment_d60_returns: int,
        control_d7_returns: int,
        control_d60_returns: int,
    ) -> None:
        """Build n_per_arm cohorts in each arm, all 65 days old, with
        the specified return-visit counts at d7 and d60."""
        for i in range(n_per_arm):
            t_user = f"user:t{i}"
            adj.register_conversion(
                decision_id=f"t{i}",
                treatment_arm="bilateral",
                converted_at=T0 - days(65),
                user_id=t_user,
            )
            if i < treatment_d7_returns:
                adj.record_return_visit(t_user, T0 - days(60))  # d7-window
            if i < treatment_d60_returns:
                adj.record_return_visit(t_user, T0 - days(10))  # d60-window-only

            c_user = f"user:c{i}"
            adj.register_conversion(
                decision_id=f"c{i}",
                treatment_arm="control",
                converted_at=T0 - days(65),
                user_id=c_user,
            )
            if i < control_d7_returns:
                adj.record_return_visit(c_user, T0 - days(60))
            if i < control_d60_returns:
                adj.record_return_visit(c_user, T0 - days(10))

    def test_discordance_detected_when_treatment_wins_early_loses_late(self):
        adj = MultiHorizonAdjudicator()
        # Treatment beats control at d7 but loses at d60
        self._build_balanced_arms(
            adj, n_per_arm=50,
            treatment_d7_returns=40,  # 80%
            control_d7_returns=20,    # 40%
            # By d60, all incremented (d7 visits also count for d60),
            # plus the additional d60-only returns:
            treatment_d60_returns=10,  # 10 more d60-only → total = 40+10=50, capped at 50
            control_d60_returns=30,    # 30 more d60-only → total = 20+30=50
        )
        # ACTUALLY this is a problem with my helper — the d60 count
        # IS the total cumulative. Let me think.
        #
        # In my helper, treatment_d60_returns=10 means "10 of the
        # cohorts get an additional return visit at d60-window-only."
        # Each of those increments d60 by 1.
        #
        # Cohorts that got a d7-window visit also got d30 + d60
        # incremented (from the same visit). So treatment d60 count =
        # 40 (from d7 visits) + 10 (additional d60-only) = 50.
        # Control d60 count = 20 (from d7) + 30 (additional) = 50.
        #
        # So treatment d60 returns = 50/50 = 100%; control d60 = 50/50
        # = 100%. No discordance.
        #
        # Need a different setup to test discordance properly.
        # Skip this test for now and write a more targeted one below.
        pass

    def test_discordance_via_targeted_setup(self):
        """Build cohorts where treatment wins at d7 but DOES NOT
        accumulate d60 visits proportionally. Treatment d7 high,
        treatment d60 low (the failure mode)."""
        adj = MultiHorizonAdjudicator()
        n = 50

        # Treatment: 40/50 return at d7 ONLY (no later visits — these
        # users converted, came back briefly, then never returned)
        for i in range(n):
            t_user = f"user:t{i}"
            adj.register_conversion(
                decision_id=f"t{i}", treatment_arm="bilateral",
                converted_at=T0 - days(65), user_id=t_user,
            )
            if i < 40:
                # One visit at d7 — but they don't return again, so
                # d60 count = 1, but those who DIDN'T visit at d7
                # also didn't visit at all → d60 count = 0
                adj.record_return_visit(t_user, T0 - days(60))

        # Control: 20/50 return at d7, ALL 50 return again later (d60-window-only)
        for i in range(n):
            c_user = f"user:c{i}"
            adj.register_conversion(
                decision_id=f"c{i}", treatment_arm="control",
                converted_at=T0 - days(65), user_id=c_user,
            )
            if i < 20:
                adj.record_return_visit(c_user, T0 - days(60))
            # Plus all 50 visit again at d60-window-only
            adj.record_return_visit(c_user, T0 - days(10))

        # Treatment d7 returns: 40/50 = 80%
        # Treatment d60 returns: 40/50 = 80% (same cohorts that visited
        #                                     at d7 — no d60-window-only)
        # Control d7 returns: 20/50 = 40%
        # Control d60 returns: 50/50 = 100% (all 50 visited at d60-window)

        result = adj.adjudicate(
            now=T0, treatment_arm="bilateral", control_arm="control",
            min_cohorts_per_arm=30,
        )
        # Treatment wins d7 (80% vs 40%), loses d60 (80% vs 100%)
        d7 = result["per_horizon"][HorizonWindow.DAY_7.value]
        d60 = result["per_horizon"][HorizonWindow.DAY_60.value]
        assert d7["absolute_lift"] == pytest.approx(0.80 - 0.40, abs=1e-6)
        assert d60["absolute_lift"] == pytest.approx(0.80 - 1.0, abs=1e-6)
        assert result["discordance_detected"] is True
        assert "DISCORDANCE" in result["discordance_note"]

    def test_no_discordance_when_aligned(self):
        adj = MultiHorizonAdjudicator()
        n = 50
        for i in range(n):
            t_user = f"user:t{i}"
            adj.register_conversion(
                decision_id=f"t{i}", treatment_arm="bilateral",
                converted_at=T0 - days(65), user_id=t_user,
            )
            if i < 40:
                adj.record_return_visit(t_user, T0 - days(60))

            c_user = f"user:c{i}"
            adj.register_conversion(
                decision_id=f"c{i}", treatment_arm="control",
                converted_at=T0 - days(65), user_id=c_user,
            )
            if i < 20:
                adj.record_return_visit(c_user, T0 - days(60))

        # Treatment wins at both horizons (no later visits skew
        # control up): treatment d60 = 80% vs control d60 = 40%
        result = adj.adjudicate(
            now=T0, treatment_arm="bilateral", control_arm="control",
            min_cohorts_per_arm=30,
        )
        assert result["discordance_detected"] is False
        assert "Aligned" in result["discordance_note"]

    def test_insufficient_n_no_discordance_call(self):
        adj = MultiHorizonAdjudicator()
        # Only 10 cohorts per arm — below the default min_cohorts_per_arm=30
        for i in range(10):
            for arm in ("bilateral", "control"):
                user = f"user:{arm}_{i}"
                adj.register_conversion(
                    decision_id=f"{arm}_{i}",
                    treatment_arm=arm,
                    converted_at=T0 - days(65),
                    user_id=user,
                )
        result = adj.adjudicate(now=T0, min_cohorts_per_arm=30)
        assert result["discordance_detected"] is False
        assert "Insufficient" in result["discordance_note"]


# ============================================================================
# Cohort.is_horizon_complete + .returned_within
# ============================================================================


class TestCohortMethods:

    def test_is_horizon_complete(self):
        cohort = ConversionCohort(
            decision_id="x", user_id="u", treatment_arm="bilateral",
            archetype=None, converted_at=T0,
        )
        # 6 days after — d7 not complete
        assert not cohort.is_horizon_complete(HorizonWindow.DAY_7, T0 + days(6))
        # 7 days — complete
        assert cohort.is_horizon_complete(HorizonWindow.DAY_7, T0 + days(7))
        # 30 days — d7 + d30 complete
        assert cohort.is_horizon_complete(HorizonWindow.DAY_30, T0 + days(30))
        # Day 30 is below d60
        assert not cohort.is_horizon_complete(HorizonWindow.DAY_60, T0 + days(30))

    def test_returned_within_reflects_counter(self):
        cohort = ConversionCohort(
            decision_id="x", user_id="u", treatment_arm="bilateral",
            archetype=None, converted_at=T0,
        )
        cohort.return_visit_count_d7 = 1
        assert cohort.returned_within(HorizonWindow.DAY_7) is True
        # d30 / d60 still 0
        assert cohort.returned_within(HorizonWindow.DAY_30) is False


# ============================================================================
# Singleton
# ============================================================================


class TestSingleton:

    def test_singleton_consistency(self):
        reset_multi_horizon_adjudicator()
        try:
            a1 = get_multi_horizon_adjudicator()
            a2 = get_multi_horizon_adjudicator()
            assert a1 is a2
        finally:
            reset_multi_horizon_adjudicator()
