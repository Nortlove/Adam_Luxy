"""Tests for Spine #2 — Within-Subject Scheduler with Washout + Carryover.

Pins per directive Section 2 (Spine #2):
    1. Mechanism vocabulary maps to one of three classes (state_prime,
       construal_shift, trait_aligned)
    2. Washout half-lives match directive ranges (state hours / construal
       medium / trait days)
    3. Eligibility check refuses a mechanism whose washout < 2× half-life
    4. ABAB replication phase explicitly authorizes A→A repeats
    5. Never-delivered mechanisms are eligible without waiting
    6. AR(1) carryover term decays exponentially with time since previous
    7. Same-mechanism repetition has positive ρ (priming)
    8. Conflicting mechanism pairs have negative ρ (interference)
    9. Replication-phase scheduler alternates ABAB on the first 6 touches
   10. After REPLICATION_PHASE_TOUCH_COUNT touches, replication scheduler
       returns None (transitions to adaptive phase)
   11. Combined schedule_next_decision integrates eligibility +
       replication + carryover
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from adam.intelligence.spine.spine_2_within_subject_scheduler import (
    MECHANISM_CLASS_BY_NAME,
    MECHANISM_CLASS_CONSTRUAL_SHIFT,
    MECHANISM_CLASS_STATE_PRIME,
    MECHANISM_CLASS_TRAIT_ALIGNED,
    MECHANISM_WASHOUT_HALF_LIFE_HOURS,
    REPLICATION_PHASE_TOUCH_COUNT,
    WASHOUT_REQUIRED_HALF_LIVES,
    EligibilityResult,
    SchedulingDecision,
    TouchEvent,
    check_mechanism_eligibility,
    compute_carryover_term,
    filter_eligible_mechanisms,
    get_carryover_coefficient,
    get_mechanism_class,
    get_washout_half_life_hours,
    is_in_replication_phase,
    schedule_next_decision,
    select_next_mechanism_replication_phase,
)


# -----------------------------------------------------------------------------
# Mechanism class assignment + washout half-lives
# -----------------------------------------------------------------------------


class TestMechanismClasses:

    def test_state_primes_have_short_half_lives(self):
        """Per directive: 'State primes (regulatory focus, arousal):
        hours (3-8h half-life)'."""
        h = MECHANISM_WASHOUT_HALF_LIFE_HOURS[MECHANISM_CLASS_STATE_PRIME]
        assert 3.0 <= h <= 8.0

    def test_construal_shifts_have_medium_half_lives(self):
        """Per directive: 'Construal-level shifts: medium (12-48h)'."""
        h = MECHANISM_WASHOUT_HALF_LIFE_HOURS[MECHANISM_CLASS_CONSTRUAL_SHIFT]
        assert 12.0 <= h <= 48.0

    def test_trait_aligned_have_long_half_lives(self):
        """Per directive: 'Trait-aligned content (identity construction,
        primary metaphor frames): days (3-7d)'."""
        h = MECHANISM_WASHOUT_HALF_LIFE_HOURS[MECHANISM_CLASS_TRAIT_ALIGNED]
        assert 3.0 * 24 <= h <= 7.0 * 24

    def test_state_primes_decay_faster_than_construal(self):
        assert (
            MECHANISM_WASHOUT_HALF_LIFE_HOURS[MECHANISM_CLASS_STATE_PRIME]
            < MECHANISM_WASHOUT_HALF_LIFE_HOURS[MECHANISM_CLASS_CONSTRUAL_SHIFT]
        )

    def test_construal_decays_faster_than_trait_aligned(self):
        assert (
            MECHANISM_WASHOUT_HALF_LIFE_HOURS[MECHANISM_CLASS_CONSTRUAL_SHIFT]
            < MECHANISM_WASHOUT_HALF_LIFE_HOURS[MECHANISM_CLASS_TRAIT_ALIGNED]
        )

    def test_known_mechanisms_have_class_assignment(self):
        for m in ("scarcity", "authority", "social_proof", "frame_gain"):
            cls = get_mechanism_class(m)
            assert cls in {
                MECHANISM_CLASS_STATE_PRIME,
                MECHANISM_CLASS_CONSTRUAL_SHIFT,
                MECHANISM_CLASS_TRAIT_ALIGNED,
            }

    def test_unknown_mechanism_raises(self):
        with pytest.raises(ValueError, match="Unknown mechanism"):
            get_mechanism_class("arbitrary_fake_mechanism")

    def test_authority_is_trait_aligned(self):
        assert get_mechanism_class("authority") == MECHANISM_CLASS_TRAIT_ALIGNED

    def test_scarcity_is_state_prime(self):
        assert get_mechanism_class("scarcity") == MECHANISM_CLASS_STATE_PRIME


# -----------------------------------------------------------------------------
# Eligibility check
# -----------------------------------------------------------------------------


class TestEligibilityCheck:

    def test_never_delivered_is_eligible(self):
        result = check_mechanism_eligibility(
            mechanism="authority", touch_history=[],
        )
        assert result.eligible is True
        assert result.reason == "never_delivered"

    def test_well_after_washout_is_eligible(self):
        now = datetime(2026, 5, 1, tzinfo=timezone.utc)
        # Authority is trait-aligned (5d half-life). 30 days ago is far
        # past 2× half-life.
        history = [TouchEvent(
            user_id="u", mechanism="authority",
            delivered_at=now - timedelta(days=30),
        )]
        result = check_mechanism_eligibility(
            mechanism="authority", touch_history=history, now=now,
        )
        assert result.eligible is True
        assert result.reason == "washout_elapsed"
        assert result.washout_half_lives_elapsed > WASHOUT_REQUIRED_HALF_LIVES

    def test_within_washout_is_ineligible(self):
        now = datetime(2026, 5, 1, tzinfo=timezone.utc)
        # Scarcity is state_prime (5.5h half-life). 1 hour ago is well
        # within 2× half-life.
        history = [TouchEvent(
            user_id="u", mechanism="scarcity",
            delivered_at=now - timedelta(hours=1),
        )]
        result = check_mechanism_eligibility(
            mechanism="scarcity", touch_history=history, now=now,
        )
        assert result.eligible is False
        assert result.reason == "washout_not_elapsed"

    def test_replication_authorized_overrides_washout(self):
        """ABAB design explicitly authorizes A→A repeat even within washout."""
        now = datetime(2026, 5, 1, tzinfo=timezone.utc)
        history = [TouchEvent(
            user_id="u", mechanism="authority",
            delivered_at=now - timedelta(hours=1),  # well within 5d half-life
        )]
        result = check_mechanism_eligibility(
            mechanism="authority", touch_history=history, now=now,
            allow_replication=True,
        )
        assert result.eligible is True
        assert result.reason == "replication_authorized"

    def test_only_last_delivery_of_target_mechanism_used(self):
        """The check looks back to the LAST delivery of the candidate
        mechanism, not just the last touch event."""
        now = datetime(2026, 5, 1, tzinfo=timezone.utc)
        history = [
            TouchEvent(user_id="u", mechanism="authority",
                       delivered_at=now - timedelta(days=30)),
            TouchEvent(user_id="u", mechanism="scarcity",
                       delivered_at=now - timedelta(hours=1)),
        ]
        # Authority was last delivered 30 days ago — past washout.
        result = check_mechanism_eligibility(
            mechanism="authority", touch_history=history, now=now,
        )
        assert result.eligible is True
        # Scarcity was just delivered an hour ago — within washout.
        result_s = check_mechanism_eligibility(
            mechanism="scarcity", touch_history=history, now=now,
        )
        assert result_s.eligible is False


class TestFilterEligibleMechanisms:

    def test_filter_returns_one_result_per_candidate(self):
        now = datetime(2026, 5, 1, tzinfo=timezone.utc)
        history = [TouchEvent(
            user_id="u", mechanism="scarcity",
            delivered_at=now - timedelta(hours=1),
        )]
        results = filter_eligible_mechanisms(
            candidate_mechanisms=["authority", "scarcity", "social_proof"],
            touch_history=history, now=now,
        )
        assert len(results) == 3
        # Authority + social_proof never delivered → eligible
        # Scarcity within washout → ineligible
        eligible_names = {r.mechanism for r in results if r.eligible}
        assert "authority" in eligible_names
        assert "social_proof" in eligible_names
        assert "scarcity" not in eligible_names


# -----------------------------------------------------------------------------
# AR(1) carryover correction
# -----------------------------------------------------------------------------


class TestCarryoverCoefficient:

    def test_same_mechanism_repetition_has_positive_priming(self):
        # Same-mechanism: trait_aligned (authority) > construal > state_prime
        rho_trait = get_carryover_coefficient("authority", "authority")
        rho_construal = get_carryover_coefficient("frame_gain", "frame_gain")
        rho_state = get_carryover_coefficient("scarcity", "scarcity")
        assert rho_trait > 0
        assert rho_construal > 0
        assert rho_state > 0
        # Trait-aligned has stronger priming than fast-decaying state.
        assert rho_trait > rho_state

    def test_frame_inversion_is_interference(self):
        rho = get_carryover_coefficient("frame_gain", "frame_loss")
        assert rho < 0
        # Symmetric.
        rho_rev = get_carryover_coefficient("frame_loss", "frame_gain")
        assert rho_rev < 0

    def test_construal_inversion_is_interference(self):
        rho = get_carryover_coefficient(
            "construal_concrete", "construal_abstract",
        )
        assert rho < 0

    def test_unspecified_pair_returns_zero(self):
        # A pair not in _DEFAULT_CARRYOVER_RHO and not same-mechanism
        # returns 0.0. Pick two unrelated trait_aligned mechanisms.
        rho = get_carryover_coefficient(
            "containment_metaphor", "status_verticality_metaphor",
        )
        assert rho == 0.0

    def test_known_compatible_pair_has_positive_priming(self):
        rho = get_carryover_coefficient("reliability_metaphor", "authority")
        assert rho > 0


class TestCarryoverTermComputation:

    def test_carryover_decays_exponentially(self):
        """At zero seconds, carryover = ρ · effect · 1 = ρ · effect.
        At one half-life, carryover = ρ · effect · 0.5."""
        # authority is trait_aligned with 5d (120h) half-life
        seconds_at_zero = 0.0
        seconds_at_half_life = 120.0 * 3600.0  # 5 days in seconds

        c_zero = compute_carryover_term(
            prev_mechanism="authority", next_mechanism="authority",
            seconds_since_prev=seconds_at_zero, prev_effect_estimate=1.0,
        )
        c_half = compute_carryover_term(
            prev_mechanism="authority", next_mechanism="authority",
            seconds_since_prev=seconds_at_half_life, prev_effect_estimate=1.0,
        )
        # At zero, carryover = ρ_authority→authority · 1 · exp(0) = ρ
        # At half-life, carryover = ρ · 1 · exp(-1) ≈ ρ · 0.368
        assert c_zero > c_half
        # Specifically, ratio should be exp(-1) ≈ 0.368.
        assert c_half / c_zero == pytest.approx(0.36787944117, rel=1e-3)

    def test_zero_rho_pair_returns_zero(self):
        c = compute_carryover_term(
            prev_mechanism="containment_metaphor",
            next_mechanism="status_verticality_metaphor",
            seconds_since_prev=3600.0,
        )
        assert c == 0.0

    def test_carryover_scales_with_prev_effect(self):
        c_low = compute_carryover_term(
            "authority", "authority", 0.0, prev_effect_estimate=0.5,
        )
        c_high = compute_carryover_term(
            "authority", "authority", 0.0, prev_effect_estimate=2.0,
        )
        assert c_high == pytest.approx(c_low * 4.0)


# -----------------------------------------------------------------------------
# Replication-phase scheduler
# -----------------------------------------------------------------------------


class TestReplicationPhase:

    def test_empty_history_is_in_replication_phase(self):
        assert is_in_replication_phase([]) is True

    def test_first_n_minus_one_touches_in_replication_phase(self):
        history = [
            TouchEvent(user_id="u", mechanism="authority",
                       delivered_at=datetime.now(timezone.utc))
            for _ in range(REPLICATION_PHASE_TOUCH_COUNT - 1)
        ]
        assert is_in_replication_phase(history) is True

    def test_after_n_touches_exits_replication_phase(self):
        history = [
            TouchEvent(user_id="u", mechanism="authority",
                       delivered_at=datetime.now(timezone.utc))
            for _ in range(REPLICATION_PHASE_TOUCH_COUNT)
        ]
        assert is_in_replication_phase(history) is False


class TestReplicationScheduler:

    def test_first_touch_picks_arm_a(self):
        chosen = select_next_mechanism_replication_phase(
            touch_history=[],
            candidate_mechanisms=["authority", "social_proof"],
        )
        assert chosen == "authority"

    def test_alternates_abab(self):
        """ABAB: pick A first, then B, then A, then B."""
        candidates = ["authority", "social_proof"]
        history = []
        chosen_sequence = []
        now = datetime(2026, 5, 1, tzinfo=timezone.utc)

        for i in range(4):
            chosen = select_next_mechanism_replication_phase(
                touch_history=history,
                candidate_mechanisms=candidates,
            )
            chosen_sequence.append(chosen)
            # Simulate the touch happening.
            history.append(TouchEvent(
                user_id="u", mechanism=chosen,
                delivered_at=now + timedelta(hours=i * 6),
            ))

        assert chosen_sequence == ["authority", "social_proof",
                                    "authority", "social_proof"]

    def test_exits_after_n_touches(self):
        candidates = ["authority", "social_proof"]
        history = [
            TouchEvent(user_id="u", mechanism="authority",
                       delivered_at=datetime.now(timezone.utc))
            for _ in range(REPLICATION_PHASE_TOUCH_COUNT)
        ]
        chosen = select_next_mechanism_replication_phase(
            touch_history=history, candidate_mechanisms=candidates,
        )
        assert chosen is None

    def test_fewer_than_two_candidates_returns_none(self):
        chosen = select_next_mechanism_replication_phase(
            touch_history=[], candidate_mechanisms=["authority"],
        )
        assert chosen is None


# -----------------------------------------------------------------------------
# Combined schedule_next_decision
# -----------------------------------------------------------------------------


class TestScheduleNextDecision:

    def test_first_decision_for_new_user(self):
        decision = schedule_next_decision(
            user_id="u",
            candidate_mechanisms=["authority", "social_proof", "scarcity"],
            touch_history=[],
        )
        assert decision.in_replication_phase is True
        assert decision.n_touches == 0
        # All three candidates eligible (never delivered).
        assert all(r.eligible for r in decision.eligible_set)
        # Replication phase picks arm A.
        assert decision.chosen_mechanism == "authority"

    def test_within_washout_not_in_replication_filters_correctly(self):
        now = datetime(2026, 5, 1, tzinfo=timezone.utc)
        history = [
            TouchEvent(user_id="u", mechanism="authority",
                       delivered_at=now - timedelta(days=1))  # within 5d half-life
            for _ in range(REPLICATION_PHASE_TOUCH_COUNT)
        ]
        decision = schedule_next_decision(
            user_id="u",
            candidate_mechanisms=["authority", "social_proof"],
            touch_history=history,
            now=now,
        )
        # Out of replication phase; not allowed to repeat A.
        assert decision.in_replication_phase is False
        # Authority is within washout (1d on 5d half-life = 0.2 half-lives,
        # well below 2). Social proof was never delivered.
        eligible_names = {r.mechanism for r in decision.eligible_set if r.eligible}
        assert "authority" not in eligible_names
        assert "social_proof" in eligible_names

    def test_carryover_terms_populated_when_history_exists(self):
        now = datetime(2026, 5, 1, tzinfo=timezone.utc)
        history = [TouchEvent(
            user_id="u", mechanism="frame_gain",
            delivered_at=now - timedelta(hours=12),
        )]
        decision = schedule_next_decision(
            user_id="u",
            candidate_mechanisms=["frame_loss", "social_proof"],
            touch_history=history, now=now,
        )
        # frame_gain → frame_loss is interference (negative ρ)
        assert decision.carryover_terms["frame_loss"] < 0
        # frame_gain → social_proof is unspecified (0)
        assert decision.carryover_terms["social_proof"] == 0.0

    def test_no_history_no_carryover_terms(self):
        decision = schedule_next_decision(
            user_id="u",
            candidate_mechanisms=["authority"],
            touch_history=[],
        )
        assert decision.carryover_terms == {}


class TestTouchEventValidation:

    def test_unknown_mechanism_rejected(self):
        with pytest.raises(ValueError, match="not in MECHANISM_CLASS_BY_NAME"):
            TouchEvent(
                user_id="u", mechanism="arbitrary_fake",
                delivered_at=datetime.now(timezone.utc),
            )

    def test_known_mechanism_accepted(self):
        e = TouchEvent(
            user_id="u", mechanism="authority",
            delivered_at=datetime.now(timezone.utc),
        )
        assert e.mechanism == "authority"
