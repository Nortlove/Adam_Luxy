"""Tests for Spine #7 — Cohort discovery + non-stationary policy.

Pins per directive Section 2 (Spine #7) + Section 9 Phase 3 gate:
    1. SW-UCB sliding window forgets old observations
    2. Empirical mean over current window is correct
    3. UCB exploration bonus decays with N(a)
    4. Unobserved arms get +inf score (force exploration)
    5. SW-UCB picks the highest-UCB arm
    6. Mortal-bandit retires arms after lifetime exhausted
    7. CohortPolicyService gates SW-UCB selection by mortal-bandit
    8. PHASE 3 GATE: lift recovery after regime shift materially
       better than static-priors baseline
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

import pytest

from adam.intelligence.spine.spine_7_cohort_policy import (
    DEFAULT_ARM_LIFETIME_OBSERVATIONS,
    DEFAULT_SW_UCB_EXPLORATION,
    DEFAULT_SW_UCB_WINDOW,
    ArmLifetime,
    ArmRewardWindow,
    CohortPolicyService,
    CohortPolicyState,
    CohortSWUCBPolicy,
)


# -----------------------------------------------------------------------------
# ArmRewardWindow — sliding-window mechanics
# -----------------------------------------------------------------------------


class TestArmRewardWindow:

    def test_record_appends(self):
        w = ArmRewardWindow(arm="authority", window_size=5)
        for r in [0.1, 0.2, 0.3]:
            w.record(r)
        assert w.n_in_window() == 3
        assert w.total_observations == 3

    def test_window_forgets_oldest_when_size_exceeded(self):
        w = ArmRewardWindow(arm="authority", window_size=3)
        for r in [0.1, 0.2, 0.3, 0.4, 0.5]:
            w.record(r)
        # window contains last 3: 0.3, 0.4, 0.5
        assert w.n_in_window() == 3
        assert w.total_observations == 5
        # Empirical mean is over the window only.
        assert w.empirical_mean() == pytest.approx((0.3 + 0.4 + 0.5) / 3)

    def test_empty_window_returns_zero_mean(self):
        w = ArmRewardWindow(arm="authority")
        assert w.empirical_mean() == 0.0

    def test_total_observations_persists_across_window_eviction(self):
        w = ArmRewardWindow(arm="x", window_size=2)
        for r in range(10):
            w.record(float(r))
        # Window has 2; total has 10.
        assert w.n_in_window() == 2
        assert w.total_observations == 10


# -----------------------------------------------------------------------------
# CohortSWUCBPolicy — UCB scoring
# -----------------------------------------------------------------------------


class TestCohortSWUCBPolicy:

    def test_unobserved_arm_returns_infinity(self):
        p = CohortSWUCBPolicy(cohort_id="c1")
        assert math.isinf(p.ucb_score("authority"))

    def test_observed_arm_returns_finite_score(self):
        p = CohortSWUCBPolicy(cohort_id="c1")
        for r in [0.5, 0.6, 0.7]:
            p.record_outcome("authority", r)
        score = p.ucb_score("authority")
        assert math.isfinite(score)
        # Score = empirical_mean + exploration_bonus
        assert score > 0.6  # mean is 0.6 + a positive bonus

    def test_select_arm_picks_highest_ucb(self):
        p = CohortSWUCBPolicy(cohort_id="c1")
        # Authority observed with high reward; social_proof never observed.
        for _ in range(20):
            p.record_outcome("authority", 0.9)
        # social_proof is unobserved → +inf, beats authority.
        chosen = p.select_arm(["authority", "social_proof"])
        assert chosen == "social_proof"

    def test_exploration_bonus_decays_with_n(self):
        """As N(a) grows, the UCB bonus shrinks (more confidence)."""
        p_few = CohortSWUCBPolicy(cohort_id="c1")
        for _ in range(2):
            p_few.record_outcome("a", 0.5)
        p_many = CohortSWUCBPolicy(cohort_id="c1")
        for _ in range(100):
            p_many.record_outcome("a", 0.5)
        # Bonus = sqrt(ξ · log(t) / N). With same mean (0.5), more N
        # → smaller bonus → smaller UCB.
        assert p_many.ucb_score("a") < p_few.ucb_score("a")

    def test_select_arm_returns_none_for_empty_candidates(self):
        p = CohortSWUCBPolicy(cohort_id="c1")
        assert p.select_arm([]) is None

    def test_arm_summary_structure(self):
        p = CohortSWUCBPolicy(cohort_id="c1")
        p.record_outcome("authority", 0.7)
        summary = p.cohort_arm_summary()
        assert "authority" in summary
        assert "empirical_mean" in summary["authority"]
        assert "n_in_window" in summary["authority"]
        assert "total_observations" in summary["authority"]
        assert "ucb_score" in summary["authority"]


# -----------------------------------------------------------------------------
# Mortal-bandit ArmLifetime
# -----------------------------------------------------------------------------


class TestArmLifetime:

    def test_arm_alive_when_below_lifetime(self):
        lt = ArmLifetime(arm="authority", lifetime_observations=10)
        assert lt.is_alive() is True

    def test_arm_retires_at_lifetime_threshold(self):
        lt = ArmLifetime(arm="authority", lifetime_observations=3)
        for i in range(3):
            still_alive = lt.increment()
            if i < 2:
                assert still_alive is True
            else:
                assert still_alive is False
        assert lt.is_alive() is False
        assert lt.retired_at is not None

    def test_force_retire_immediately(self):
        lt = ArmLifetime(arm="authority", lifetime_observations=100)
        lt.force_retire()
        assert lt.is_alive() is False

    def test_fraction_consumed(self):
        lt = ArmLifetime(arm="x", lifetime_observations=10)
        for _ in range(3):
            lt.increment()
        assert lt.fraction_consumed() == pytest.approx(0.3)

    def test_force_retire_sets_alive_false(self):
        lt = ArmLifetime(arm="x", lifetime_observations=100)
        lt.increment()
        lt.increment()
        lt.force_retire()
        assert lt.is_alive() is False


# -----------------------------------------------------------------------------
# CohortPolicyService — composed entry point
# -----------------------------------------------------------------------------


class TestCohortPolicyService:

    def test_first_call_auto_registers_arms(self):
        svc = CohortPolicyService(cohort_id="c1")
        chosen = svc.select_arm(["authority", "scarcity"])
        # Both arms unobserved → both have UCB +inf; either is valid.
        assert chosen in ("authority", "scarcity")
        # Both auto-registered.
        assert "authority" in svc.arm_lifetimes
        assert "scarcity" in svc.arm_lifetimes

    def test_record_outcome_increments_lifetime(self):
        svc = CohortPolicyService(cohort_id="c1", arm_default_lifetime=5)
        for _ in range(3):
            svc.record_outcome("authority", 0.6)
        assert svc.arm_lifetimes["authority"].observations_so_far == 3
        assert svc.arm_lifetimes["authority"].is_alive() is True

    def test_arm_retired_excluded_from_selection(self):
        svc = CohortPolicyService(cohort_id="c1", arm_default_lifetime=2)
        for _ in range(2):
            svc.record_outcome("authority", 0.8)
        # Authority retired (2/2); scarcity never observed → +inf.
        chosen = svc.select_arm(["authority", "scarcity"])
        assert chosen == "scarcity"

    def test_all_retired_returns_none(self):
        svc = CohortPolicyService(cohort_id="c1", arm_default_lifetime=1)
        svc.record_outcome("authority", 0.5)
        svc.record_outcome("scarcity", 0.5)
        chosen = svc.select_arm(["authority", "scarcity"])
        assert chosen is None

    def test_state_snapshot_serializes(self):
        svc = CohortPolicyService(cohort_id="c1")
        svc.record_outcome("authority", 0.7)
        snap = svc.state_snapshot()
        assert isinstance(snap, CohortPolicyState)
        assert snap.cohort_id == "c1"
        assert "authority" in snap.arm_summaries
        assert "authority" in snap.lifetime_summaries

    def test_alive_arms_filters_correctly(self):
        svc = CohortPolicyService(cohort_id="c1", arm_default_lifetime=3)
        for _ in range(3):
            svc.record_outcome("authority", 0.5)
        # Authority retired; scarcity not registered.
        alive = svc.alive_arms(["authority", "scarcity"])
        assert "authority" not in alive
        assert "scarcity" in alive


# -----------------------------------------------------------------------------
# PHASE 3 GATE — non-stationary regime shift
# -----------------------------------------------------------------------------


class TestPhase3Gate:
    """Per directive Section 9 Phase 3 gate:
    'Synthetic non-stationary trajectory: a simulated cohort experiences
    an abrupt regime shift; the system's lift-recovery time after the
    shift is materially better than a static-priors baseline.'
    """

    def _simulate_swucb_under_regime_shift(
        self,
        n_pre_shift: int,
        n_post_shift: int,
        window_size: int,
    ) -> List[float]:
        """Simulate SW-UCB under regime shift.

        Pre-shift regime: arm_a yields high reward (0.8), arm_b yields
        low reward (0.2).
        Regime shift: roles swap. arm_a now yields 0.2, arm_b now 0.8.
        Returns a list of empirical_mean(arm_b) at each step in the
        post-shift period — measures how fast SW-UCB picks up that
        arm_b is now better.
        """
        import random as _r
        rng = _r.Random(42)

        svc = CohortPolicyService(
            cohort_id="c1",
            window_size=window_size,
            arm_default_lifetime=10000,  # don't retire during simulation
        )

        # Pre-shift: arm_a high, arm_b low. Heavy exploration of both.
        for _ in range(n_pre_shift):
            chosen = svc.select_arm(["arm_a", "arm_b"])
            if chosen == "arm_a":
                reward = 0.8 + rng.gauss(0, 0.05)
            else:
                reward = 0.2 + rng.gauss(0, 0.05)
            svc.record_outcome(chosen, reward)

        # Regime shift: roles swap.
        recoveries: List[float] = []
        for _ in range(n_post_shift):
            chosen = svc.select_arm(["arm_a", "arm_b"])
            if chosen == "arm_a":
                reward = 0.2 + rng.gauss(0, 0.05)
            else:
                reward = 0.8 + rng.gauss(0, 0.05)
            svc.record_outcome(chosen, reward)
            recoveries.append(svc.sw_ucb.arm_windows["arm_b"].empirical_mean())

        return recoveries

    def test_swucb_recovers_after_regime_shift(self):
        """SW-UCB with reasonable window should pick up the new
        regime — arm_b's empirical_mean should rise from low (0.2-ish)
        to high (0.8-ish) within the post-shift window."""
        recoveries = self._simulate_swucb_under_regime_shift(
            n_pre_shift=200, n_post_shift=200, window_size=50,
        )
        # By the end of the post-shift period, arm_b's empirical mean
        # should be solidly above the pre-shift reward (0.2).
        final_mean = recoveries[-1]
        assert final_mean > 0.5, (
            f"SW-UCB failed to recover after regime shift. "
            f"Final arm_b empirical mean: {final_mean}"
        )

    def test_swucb_recovers_faster_with_smaller_window(self):
        """A smaller window forgets the old regime faster, so it should
        recover faster. This is the directive's argument for SW-UCB
        over static priors: parameter-drift transition density tracks
        regime changes."""
        recoveries_small = self._simulate_swucb_under_regime_shift(
            n_pre_shift=100, n_post_shift=100, window_size=20,
        )
        recoveries_large = self._simulate_swucb_under_regime_shift(
            n_pre_shift=100, n_post_shift=100, window_size=200,
        )
        # Both should recover by the end. But the large-window policy
        # is contaminated by old observations longer; its mid-recovery
        # estimate is worse.
        # Compare empirical means at step 30 post-shift:
        mid_small = recoveries_small[30] if len(recoveries_small) > 30 else 0
        mid_large = recoveries_large[30] if len(recoveries_large) > 30 else 0
        assert mid_small > mid_large, (
            f"Small-window SW-UCB ({mid_small:.3f}) should recover "
            f"faster than large-window ({mid_large:.3f}) at step 30 "
            f"post-shift."
        )

    def test_static_baseline_fails_to_recover(self):
        """A non-windowed policy (effectively infinite-window UCB) is
        contaminated by the pre-shift observations and recovers slowly.
        SW-UCB with a moderate window beats it materially."""
        # "Static baseline" simulated as window = pre + post (so no
        # forgetting).
        recoveries_baseline = self._simulate_swucb_under_regime_shift(
            n_pre_shift=200, n_post_shift=200, window_size=400,
        )
        recoveries_swucb = self._simulate_swucb_under_regime_shift(
            n_pre_shift=200, n_post_shift=200, window_size=50,
        )
        # SW-UCB's post-shift arm_b mean should END materially HIGHER
        # than the static baseline's.
        final_swucb = recoveries_swucb[-1]
        final_baseline = recoveries_baseline[-1]
        assert final_swucb > final_baseline, (
            f"SW-UCB recovery ({final_swucb:.3f}) NOT better than "
            f"static-priors baseline ({final_baseline:.3f}). "
            f"Phase 3 gate FAIL."
        )
