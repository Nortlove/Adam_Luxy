"""Phase 1 RED-criterion gate test — integrated synthetic trajectory.

Per CLAUDE_CODE_DIRECTIVE_FULL_BUILD.md Section 9 Phase 1:

    Gate: End-to-end synthetic trajectory test. A simulated user
    receives 8 touches across 2 mechanisms with washout, and the system
    produces:
      (a) coherent posterior trajectory
      (b) within-subject crossover with carryover correction visible
      (c) explicit non-response handling
      (d) all storage paths exercised

    RED if any of (a)–(d) fails.

This test exercises Spines #1, #2, and #11 together. It is the
substantive proof that the Phase 1 substrate is correctly composed.

The trajectory:
    Touch 1: ABAB → authority delivered. Outcome: VIEWED_ENGAGED.
    Touch 2: ABAB → social_proof delivered. Outcome: VIEWED_DISENGAGED.
    Touch 3: ABAB → authority. Outcome: CLICK_QUALIFIED.
    Touch 4: ABAB → social_proof. Outcome: IMPRESSION_NON_VIEWABLE (a).
    Touch 5: ABAB → authority. Outcome: CONVERSION.
    Touch 6: ABAB → social_proof. Outcome: CLICK_BOUNCED.
    [exits replication phase]
    Touch 7: post-replication → authority eligible (washout passed),
             social_proof within washout. Outcome: VIEWED_ENGAGED.
    Touch 8: depends on schedule — must respect washout for SP.

Asserted invariants:
    - posterior shifts coherently across touches
    - replication phase produces ABAB on first 6 touches
    - non-viewable touch (a) leaves natural params unchanged but
      bumps observation count
    - carryover term computed across each transition
    - sapid registry round-trip works for every touch
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from adam.intelligence.spine.spine_1_n_of_1_engine import (
    USER_POSTERIOR_DIM,
    init_user_posterior,
)
from adam.intelligence.spine.spine_2_within_subject_scheduler import (
    REPLICATION_PHASE_TOUCH_COUNT,
    TouchEvent,
    is_in_replication_phase,
    schedule_next_decision,
)
from adam.intelligence.spine.spine_11_negative_outcome_adapter import (
    OutcomeEvent,
    register_sapid_for_decision,
    reset_sapid_registry,
    route_outcome_to_posterior,
)


def _feature_vector_for_mechanism(mechanism: str) -> list:
    """Hand-crafted design vector per mechanism — distinct dims active
    so the trajectory's cumulative posterior shift on each dim is
    inspectable."""
    x = [0.0] * USER_POSTERIOR_DIM
    if mechanism == "authority":
        x[0] = 1.0  # dim 0 active for authority
    elif mechanism == "social_proof":
        x[1] = 1.0  # dim 1 active for social proof
    return x


@pytest.fixture(autouse=True)
def _reset_state():
    reset_sapid_registry()
    yield
    reset_sapid_registry()


def _simulate_touch(
    user_id: str,
    candidate_mechanisms: list,
    touch_history: list,
    outcome_class: str,
    base_time: datetime,
    touch_index: int,
    posterior,
):
    """Execute one touch: schedule → register sapid → simulate outcome
    → route to posterior. Returns (updated_posterior, new_TouchEvent,
    SchedulingDecision)."""
    now = base_time + timedelta(hours=touch_index * 24)  # 1 touch/day

    # 1. Schedule (Spine #2)
    decision = schedule_next_decision(
        user_id=user_id,
        candidate_mechanisms=candidate_mechanisms,
        touch_history=touch_history,
        now=now,
    )

    # 2. Pick a mechanism — replication phase chooses; otherwise pick
    # first eligible.
    if decision.chosen_mechanism is not None:
        mechanism = decision.chosen_mechanism
    else:
        eligible = [r.mechanism for r in decision.eligible_set if r.eligible]
        if not eligible:
            pytest.fail(
                f"Touch {touch_index}: no eligible mechanism. "
                f"eligible_set: {decision.eligible_set}"
            )
        mechanism = eligible[0]

    # 3. Register sapid for this decision (Spine #11 round-trip anchor)
    sapid = f"sa_{user_id}_{touch_index}"
    decision_id = f"d_{user_id}_{touch_index}"
    feature_vector = _feature_vector_for_mechanism(mechanism)
    register_sapid_for_decision(sapid, decision_id, user_id, feature_vector)

    # 4. Build the outcome (simulating pixel event arrival)
    outcome = OutcomeEvent(
        sapid=sapid,
        outcome_class=outcome_class,
        user_id=user_id,
        decision_id=decision_id,
        occurred_at=now + timedelta(minutes=30),
    )

    # 5. Route to posterior (Spine #1 BONG update via Spine #11 adapter)
    new_posterior = route_outcome_to_posterior(outcome, posterior)

    # 6. Append to touch history.
    new_event = TouchEvent(
        user_id=user_id, mechanism=mechanism,
        delivered_at=now, decision_id=decision_id,
        outcome_observed_at=now + timedelta(minutes=30),
        outcome_class=outcome_class,
    )
    return new_posterior, new_event, decision


def test_phase_1_red_gate_8_touch_synthetic_trajectory():
    """Phase 1 RED-criterion gate per directive Section 9 Phase 1.

    Asserts (a)–(d) per the directive specification.
    """
    user_id = "u:phase1_gate"
    candidates = ["authority", "social_proof"]
    base_time = datetime(2026, 5, 1, tzinfo=timezone.utc)

    posterior = init_user_posterior(user_id=user_id)
    touch_history: list = []

    # Trajectory specification
    trajectory = [
        # (touch_idx, expected_mechanism, outcome_class)
        (0, "authority", "VIEWED_ENGAGED"),
        (1, "social_proof", "VIEWED_DISENGAGED"),
        (2, "authority", "CLICK_QUALIFIED"),
        (3, "social_proof", "IMPRESSION_NON_VIEWABLE"),
        (4, "authority", "CONVERSION"),
        (5, "social_proof", "CLICK_BOUNCED"),
        (6, None, "VIEWED_ENGAGED"),  # post-replication; mechanism follows eligibility
        (7, None, "VIEWED_ENGAGED"),  # post-replication
    ]

    posterior_history = [posterior]
    decisions = []

    for (idx, expected_m, outcome_class) in trajectory:
        posterior, event, decision = _simulate_touch(
            user_id=user_id,
            candidate_mechanisms=candidates,
            touch_history=touch_history,
            outcome_class=outcome_class,
            base_time=base_time,
            touch_index=idx,
            posterior=posterior,
        )
        # If trajectory specified an expected mechanism, assert it
        # matches.
        if expected_m is not None:
            assert event.mechanism == expected_m, (
                f"Touch {idx}: expected {expected_m}, got {event.mechanism}. "
                f"in_replication={decision.in_replication_phase}"
            )
        touch_history.append(event)
        posterior_history.append(posterior)
        decisions.append(decision)

    # ============================================================
    # GATE (a): coherent posterior trajectory
    # ============================================================

    # Authority delivered on touches 0, 2, 4 with outcomes VIEWED_ENGAGED
    # (weight 0.3, +1), CLICK_QUALIFIED (weight 0.4, +1), CONVERSION
    # (weight 1.0, +1). Touches 6 and 7 are post-replication; authority
    # is within 2× washout (5d half-life, last delivered at day 4) so
    # NOT eligible at days 6 and 7. Hence η[0] = 0.3 + 0.4 + 1.0 = 1.7
    expected_eta_0 = 0.3 + 0.4 + 1.0
    assert posterior.precision_weighted_mean[0] == pytest.approx(expected_eta_0)

    # Social_proof delivered on touches 1, 3, 5 with outcomes
    # VIEWED_DISENGAGED (weight 0.5, -1), IMPRESSION_NON_VIEWABLE
    # (weight 0, no update), CLICK_BOUNCED (weight 0.7, -1). Touches 6
    # and 7 are post-replication; social_proof IS eligible (5.5h half-
    # life, last delivered at day 5; days 6 and 7 are >2× half-lives
    # past). Both touches outcome VIEWED_ENGAGED (weight 0.3, +1).
    # η[1] = -0.5 + 0 + -0.7 + 0.3 + 0.3 = -0.6
    expected_eta_1 = -0.5 + 0.0 + (-0.7) + 0.3 + 0.3
    assert posterior.precision_weighted_mean[1] == pytest.approx(expected_eta_1)

    # Direction sanity: positive evidence on authority (η[0] > 0),
    # negative evidence on social_proof (η[1] < 0)
    assert posterior.precision_weighted_mean[0] > 0
    assert posterior.precision_weighted_mean[1] < 0

    # ============================================================
    # GATE (b): within-subject crossover with carryover correction visible
    # ============================================================

    # The first 6 touches must be ABAB: A, B, A, B, A, B
    expected_first_six = [
        "authority", "social_proof", "authority", "social_proof",
        "authority", "social_proof",
    ]
    actual_first_six = [touch_history[i].mechanism for i in range(6)]
    assert actual_first_six == expected_first_six

    # Carryover terms were computed for every touch except the first.
    for idx in range(1, len(decisions)):
        d = decisions[idx]
        # Carryover dict should be non-empty for every transition.
        assert d.carryover_terms, (
            f"Touch {idx}: carryover_terms empty; carryover correction not visible"
        )
        # Both candidate mechanisms appear in the dict.
        assert "authority" in d.carryover_terms
        assert "social_proof" in d.carryover_terms

    # Specifically verify that frame interference / repetition priming
    # produces the right SIGN. authority → authority is same-mechanism
    # repetition: positive ρ. So at any transition where the previous
    # touch was authority and the candidate is authority, the carryover
    # term should be non-zero positive.
    # Touch 1: prev=authority. Candidate authority's carryover should
    # be positive (same-mechanism repetition is priming).
    touch_1_decision = decisions[1]
    if "authority" in touch_1_decision.carryover_terms:
        assert touch_1_decision.carryover_terms["authority"] > 0

    # ============================================================
    # GATE (c): explicit non-response handling
    # ============================================================

    # Touch 3 (idx 3) had IMPRESSION_NON_VIEWABLE. Posterior natural
    # parameters at that step should be unchanged from posterior at
    # step 2, but observation count should bump.
    p_before_nonresponse = posterior_history[3]   # state after touch 2 (idx 2)
    p_after_nonresponse = posterior_history[4]    # state after touch 3 (idx 3)

    assert p_after_nonresponse.precision_weighted_mean == \
        p_before_nonresponse.precision_weighted_mean
    assert p_after_nonresponse.precision_matrix_flat == \
        p_before_nonresponse.precision_matrix_flat
    # But observation count incremented + last_outcome_class updated.
    assert p_after_nonresponse.total_observations == \
        p_before_nonresponse.total_observations + 1
    assert p_after_nonresponse.last_outcome_class == "IMPRESSION_NON_VIEWABLE"

    # ============================================================
    # GATE (d): all storage paths exercised
    # ============================================================

    # Posterior to-Neo4j-props serialization works on the final state.
    props = posterior.to_neo4j_props()
    assert "precision_matrix_flat_json" in props
    assert "precision_weighted_mean_json" in props
    assert props["total_observations"] == len(trajectory)

    # Sapid registry was populated for every touch.
    from adam.intelligence.spine.spine_11_negative_outcome_adapter import (
        sapid_registry_size,
    )
    assert sapid_registry_size() == len(trajectory)

    # Replication phase exited correctly after 6 touches.
    # Touches 0-5 (6 total) are in replication; from touch 6 onwards
    # we should be out.
    for idx in range(6):
        assert decisions[idx].in_replication_phase is True
    for idx in range(6, len(decisions)):
        assert decisions[idx].in_replication_phase is False


def test_phase_1_red_gate_within_washout_filtering():
    """Sub-gate: when a mechanism is within washout post-replication,
    it must be filtered from the eligible set.

    Trajectory: replication phase ABAB delivers authority and
    social_proof alternately on a 1-touch-per-day cadence. Authority's
    washout half-life is 5 days (trait_aligned); 2× = 10 days. So at
    touch 6 (day 6), authority delivered last on day 4, only 2 days
    elapsed = 0.4 half-lives. Authority must be ineligible.

    Social_proof's washout half-life is 5.5 hours (state_prime); 2× =
    11 hours. Last delivered day 5 (24 hours ago). 24 / 5.5 = 4.36
    half-lives. Social_proof IS eligible.
    """
    user_id = "u:washout_gate"
    candidates = ["authority", "social_proof"]
    base_time = datetime(2026, 5, 1, tzinfo=timezone.utc)
    posterior = init_user_posterior(user_id=user_id)
    touch_history: list = []

    # ABAB on days 0, 1, 2, 3, 4, 5 (6 touches; replication phase).
    for idx in range(REPLICATION_PHASE_TOUCH_COUNT):
        outcome_class = "VIEWED_ENGAGED"  # neutral throughout
        posterior, event, _ = _simulate_touch(
            user_id=user_id,
            candidate_mechanisms=candidates,
            touch_history=touch_history,
            outcome_class=outcome_class,
            base_time=base_time,
            touch_index=idx,
            posterior=posterior,
        )
        touch_history.append(event)

    # Touch 6 (day 6, 24 hours after touch 5) — out of replication.
    now_t6 = base_time + timedelta(hours=6 * 24)
    decision = schedule_next_decision(
        user_id=user_id,
        candidate_mechanisms=candidates,
        touch_history=touch_history,
        now=now_t6,
    )
    eligibility = {r.mechanism: r.eligible for r in decision.eligible_set}

    # Authority delivered last at touch 4 (day 4). Day 6 - day 4 = 2
    # days = 48h. Half-life 120h. 2× = 240h. Not yet eligible.
    assert eligibility["authority"] is False, (
        "Authority should be within 2× half-life washout"
    )

    # Social_proof delivered last at touch 5 (day 5). Day 6 - day 5 =
    # 1 day = 24h. Half-life 5.5h. 24 / 5.5 = 4.36 half-lives. ELIGIBLE.
    assert eligibility["social_proof"] is True, (
        "Social_proof should be past 2× half-life washout (state_prime fast decay)"
    )


def test_phase_1_red_gate_unknown_sapid_drops_outcome():
    """Sub-gate: outcomes whose sapid does not resolve via the registry
    are dropped (round-trip failure handling)."""
    from adam.intelligence.spine.spine_11_negative_outcome_adapter import (
        RawPixelEvent,
        build_outcome_event,
    )

    raw = RawPixelEvent(
        sapid="never_registered",
        event_type="view",
        is_conversion=True,
    )
    outcome = build_outcome_event(raw)
    assert outcome is None, (
        "Round-trip failure: unknown sapid must yield None, NOT a "
        "fabricated outcome with a guessed user."
    )
