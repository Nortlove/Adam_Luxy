"""Pin the MRT bid-time logging substrate.

Discipline anchors:
    - ε-floor mixer: p_t = (1-ε)·π_TS + ε·(1/K). With ε=0.02 the
      positivity bounds are [ε/K, 1-ε(1-1/K)]. Drift in this formula
      silently breaks the WCLS analytical guarantee (Boruvka 2018 §2).
    - p_t_known is the discipline anchor. Positivity violations MUST
      flag p_t_known=false so downstream WCLS excludes the row. A
      logger that silently records p_t_known=true on degenerate
      distributions corrupts the entire analysis (Bibaut 2024 / Shi-
      Dempsey 2025: small p_t recording errors dominate bias).
    - I_t=0 → DO NOT randomize, DO NOT log (handoff §1.9). Logging
      a non-randomized decision contaminates the trial.
    - The Avro schema is the contract between producers and consumers.
      Field-name drift across a sequence of refactors silently breaks
      the analysis pipeline.
"""

from __future__ import annotations

import pytest

from adam.intelligence.mrt_logging import (
    EPSILON_FLOOR,
    InMemoryDecisionLog,
    MRT_DECISIONS_V1_AVRO_SCHEMA,
    MRTDecisionRecord,
    assert_positivity,
    epsilon_floor_mix,
    estimate_optimality_probabilities,
    pi_from_argmax_scores,
    select_action_from_pi,
    select_action_from_scores,
    select_action_with_logged_propensity,
)


# -----------------------------------------------------------------------------
# ε-floor mixer math
# -----------------------------------------------------------------------------


def test_epsilon_floor_default_is_canonical_002():
    """Handoff §1.1: ε=0.02 minimizes revenue impact in the 1-10% Liao
    standard band. Drifting this value would silently change the
    sample-size calculation."""
    assert EPSILON_FLOOR == 0.02


def test_epsilon_floor_mix_two_arms_at_canonical():
    """K=2, ε=0.02: bounds should be [0.01, 0.99]."""
    pi_ts = {"a": 1.0, "b": 0.0}
    p_t = epsilon_floor_mix(pi_ts, epsilon=0.02)
    assert pytest.approx(p_t["a"]) == 0.99
    assert pytest.approx(p_t["b"]) == 0.01


def test_epsilon_floor_mix_preserves_probability_mass():
    """Output must sum to 1.0 exactly (within float tolerance)."""
    pi_ts = {"a": 0.7, "b": 0.2, "c": 0.1}
    p_t = epsilon_floor_mix(pi_ts)
    assert pytest.approx(sum(p_t.values()), abs=1e-9) == 1.0


def test_epsilon_floor_mix_ten_arms():
    """K=10, ε=0.02: floor = 0.002, ceiling = 0.982."""
    pi_ts = {f"m{i}": 1.0 if i == 0 else 0.0 for i in range(10)}
    p_t = epsilon_floor_mix(pi_ts, epsilon=0.02)
    assert min(p_t.values()) == pytest.approx(0.002)
    # Argmax arm: (1-0.02)·1 + 0.02·0.1 = 0.982
    assert max(p_t.values()) == pytest.approx(0.982)


def test_epsilon_floor_mix_never_zero_when_epsilon_positive():
    """Even degenerate π_TS (one arm = 1) must produce positive p_t for
    every other arm. This is the whole point of the ε-floor."""
    pi_ts = {"a": 1.0, "b": 0.0, "c": 0.0}
    p_t = epsilon_floor_mix(pi_ts, epsilon=0.02)
    for arm, p in p_t.items():
        assert p > 0, f"{arm} has p_t={p}, violates positivity"


def test_epsilon_floor_mix_uniform_input_unchanged():
    """Uniform input → uniform output regardless of ε. ε-mixing changes
    ratios, not uniform distributions."""
    pi_ts = {"a": 0.25, "b": 0.25, "c": 0.25, "d": 0.25}
    p_t = epsilon_floor_mix(pi_ts, epsilon=0.02)
    for p in p_t.values():
        assert pytest.approx(p) == 0.25


def test_epsilon_floor_mix_rejects_empty():
    with pytest.raises(ValueError):
        epsilon_floor_mix({})


def test_epsilon_floor_mix_rejects_invalid_epsilon():
    with pytest.raises(ValueError):
        epsilon_floor_mix({"a": 1.0}, epsilon=1.5)
    with pytest.raises(ValueError):
        epsilon_floor_mix({"a": 1.0}, epsilon=-0.1)


def test_epsilon_floor_mix_rejects_non_normalized_input():
    """π_TS that doesn't sum to 1 is malformed — silent normalization
    would mask upstream bugs."""
    with pytest.raises(ValueError):
        epsilon_floor_mix({"a": 0.5, "b": 0.2})  # sums to 0.7


# -----------------------------------------------------------------------------
# Positivity assertion
# -----------------------------------------------------------------------------


def test_assert_positivity_passes_on_mixed():
    p_t = epsilon_floor_mix({"a": 0.9, "b": 0.1}, epsilon=0.02)
    assert_positivity(p_t, epsilon=0.02)  # should not raise


def test_assert_positivity_raises_on_zero_arm():
    """Manually-crafted p_t with a zero — mixer was bypassed."""
    bad = {"a": 1.0, "b": 0.0}
    with pytest.raises(AssertionError):
        assert_positivity(bad, epsilon=0.02)


def test_assert_positivity_raises_on_too_high():
    bad = {"a": 1.5, "b": -0.5}
    with pytest.raises(AssertionError):
        assert_positivity(bad, epsilon=0.02)


# -----------------------------------------------------------------------------
# Monte Carlo optimality estimation
# -----------------------------------------------------------------------------


def test_optimality_dominant_arm_wins():
    """Arm with much stronger Beta posterior (high α, low β) should
    dominate the optimality probability."""
    posteriors = {
        "winner": (50.0, 5.0),     # mean ≈ 0.91
        "loser": (5.0, 50.0),      # mean ≈ 0.09
    }
    pi = estimate_optimality_probabilities(posteriors, n_samples=2000, rng_seed=42)
    assert pi["winner"] > 0.95
    assert pi["loser"] < 0.05
    assert pytest.approx(sum(pi.values())) == 1.0


def test_optimality_uniform_priors_split_evenly():
    """Beta(1,1) for all arms → uniform optimality probability."""
    posteriors = {f"m{i}": (1.0, 1.0) for i in range(4)}
    pi = estimate_optimality_probabilities(posteriors, n_samples=4000, rng_seed=42)
    for p in pi.values():
        # ~0.25 each, MC noise tolerated
        assert 0.20 < p < 0.30


def test_optimality_handles_extreme_posteriors():
    """Beta(α, β) where α or β is near zero must not crash. The
    sampler clamps to 1e-6 internally."""
    posteriors = {"a": (0.0, 1.0), "b": (1.0, 0.0)}
    pi = estimate_optimality_probabilities(posteriors, n_samples=100, rng_seed=42)
    assert pytest.approx(sum(pi.values()), abs=0.01) == 1.0


def test_optimality_empty_returns_empty():
    assert estimate_optimality_probabilities({}) == {}


# -----------------------------------------------------------------------------
# Decision-and-log integration
# -----------------------------------------------------------------------------


def test_select_action_logs_p_t_in_valid_range():
    """End-to-end: pick an arm, log p_t. p_t must respect the
    [ε/K, 1-ε(1-1/K)] bounds."""
    posteriors = {"social_proof": (10.0, 5.0), "authority": (3.0, 12.0)}
    log = InMemoryDecisionLog()

    arm, p_t, record = select_action_with_logged_propensity(
        user_id="u1", decision_point_t=1, archetype_id="status_seeker",
        category_id="luxury_transportation", posteriors=posteriors,
        moderators_S_t={"prior_touches": 2.0},
        rng_seed=42, producer=log.emit,
    )

    assert arm in posteriors
    assert 0.01 <= p_t <= 0.99   # K=2, ε=0.02
    assert record is not None
    assert record.p_t_known is True
    assert record.rand_prob_p_t == p_t
    assert len(log) == 1


def test_select_action_when_unavailable_logs_nothing():
    """Handoff §1.9: I_t=0 → DO NOT randomize, DO NOT log. A row
    written here would contaminate the trial."""
    posteriors = {"a": (5.0, 5.0), "b": (5.0, 5.0)}
    log = InMemoryDecisionLog()

    arm, p_t, record = select_action_with_logged_propensity(
        user_id="u1", decision_point_t=1, archetype_id="x",
        category_id="x", posteriors=posteriors,
        moderators_S_t={}, availability_I_t=0,
        producer=log.emit, rng_seed=42,
    )

    assert arm is None
    assert p_t == 0.0
    assert record is None
    assert len(log) == 0


def test_select_action_records_posterior_alpha_beta_for_audit():
    """The Beta (α, β) at decision time is part of the audit trail.
    A future analysis can verify the decision was consistent with the
    posterior state at that moment."""
    posteriors = {"a": (50.0, 5.0), "b": (5.0, 50.0)}
    log = InMemoryDecisionLog()

    select_action_with_logged_propensity(
        user_id="u1", decision_point_t=1, archetype_id="x",
        category_id="x", posteriors=posteriors,
        moderators_S_t={}, producer=log.emit, rng_seed=42,
    )

    rec = log.records[0]
    chosen_alpha, chosen_beta = posteriors[rec.mechanism_id]
    assert rec.ts_posterior_alpha == chosen_alpha
    assert rec.ts_posterior_beta == chosen_beta


def test_select_action_dominant_arm_chosen_more_often():
    """Sanity: with seed=N, the strongly-dominant arm should be picked
    most of the time. ε-floor still leaves 0.01 for the other arm."""
    posteriors = {"winner": (100.0, 5.0), "loser": (5.0, 100.0)}

    chosen = []
    for trial in range(100):
        log = InMemoryDecisionLog()
        arm, _, _ = select_action_with_logged_propensity(
            user_id="u", decision_point_t=trial, archetype_id="x",
            category_id="x", posteriors=posteriors,
            moderators_S_t={}, producer=log.emit, rng_seed=trial,
        )
        chosen.append(arm)

    # Winner should be picked at least 90% (random seeds, ε=0.02)
    winner_count = sum(1 for c in chosen if c == "winner")
    assert winner_count >= 90, f"winner picked only {winner_count}/100"


def test_select_action_producer_failure_does_not_break_decision():
    """Handoff §1.10 implicit: bid path must not break on logging
    failure. Producer raises → decision still returns; log row may be
    lost but the bid lands."""
    posteriors = {"a": (10.0, 5.0), "b": (3.0, 12.0)}

    def bad_producer(record):
        raise ConnectionError("kafka down")

    arm, p_t, record = select_action_with_logged_propensity(
        user_id="u1", decision_point_t=1, archetype_id="x",
        category_id="x", posteriors=posteriors,
        moderators_S_t={}, producer=bad_producer, rng_seed=42,
    )

    # Decision still happened
    assert arm is not None
    assert 0.01 <= p_t <= 0.99


def test_select_action_no_producer_still_returns_record():
    """When producer=None, no emit happens but the record is still
    returned to the caller (who decides whether to track)."""
    posteriors = {"a": (10.0, 5.0), "b": (5.0, 10.0)}
    arm, p_t, record = select_action_with_logged_propensity(
        user_id="u1", decision_point_t=1, archetype_id="x",
        category_id="x", posteriors=posteriors,
        moderators_S_t={}, producer=None, rng_seed=42,
    )
    assert record is not None
    assert record.user_id == "u1"


def test_select_action_empty_posteriors_raises():
    """Empty arm set is a contract violation — surface clearly."""
    with pytest.raises(ValueError):
        select_action_with_logged_propensity(
            user_id="u", decision_point_t=1, archetype_id="x",
            category_id="x", posteriors={},
            moderators_S_t={}, rng_seed=42,
        )


# -----------------------------------------------------------------------------
# Avro schema contract
# -----------------------------------------------------------------------------


def test_avro_schema_required_fields_present():
    """Field names must match handoff §1.2 schema. Producers and
    consumers depend on this contract."""
    field_names = {f["name"] for f in MRT_DECISIONS_V1_AVRO_SCHEMA["fields"]}
    required = {
        "ts", "user_id", "decision_point_t", "archetype_id", "mechanism_id",
        "category_id", "moderators_S_t", "action_A_t", "rand_prob_p_t",
        "epsilon_floor", "availability_I_t", "p_t_known",
        "ts_posterior_alpha", "ts_posterior_beta",
    }
    missing = required - field_names
    assert not missing, f"Avro schema missing fields: {missing}"


def test_avro_schema_namespace_is_versioned():
    """Schema-registry compatibility relies on a stable namespace.
    Drift here would require schema-evolution coordination."""
    assert MRT_DECISIONS_V1_AVRO_SCHEMA["namespace"] == "informativ.mrt.v1"
    assert MRT_DECISIONS_V1_AVRO_SCHEMA["name"] == "MRTDecision"


def test_avro_schema_p_t_known_is_required_boolean():
    """p_t_known is the discipline-anchor field — its presence and
    type must be guaranteed."""
    fields = {f["name"]: f for f in MRT_DECISIONS_V1_AVRO_SCHEMA["fields"]}
    assert fields["p_t_known"]["type"] == "boolean"


# -----------------------------------------------------------------------------
# In-memory producer
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# Score-based path — pi_from_argmax_scores + select_action_from_scores
# -----------------------------------------------------------------------------


def test_pi_from_argmax_scores_delta_on_unique_winner():
    """Single argmax → π = 1.0 on argmax, 0.0 elsewhere."""
    scores = {"a": 0.8, "b": 0.5, "c": 0.3}
    pi = pi_from_argmax_scores(scores)
    assert pi["a"] == 1.0
    assert pi["b"] == 0.0
    assert pi["c"] == 0.0
    assert pytest.approx(sum(pi.values())) == 1.0


def test_pi_from_argmax_scores_splits_ties_equally():
    """Tied argmax → mass split equally. Important: in a 3-way tie, each
    gets 1/3 — never 1.0 to one and 0.0 to others (that would silently
    bias toward dict-iteration order)."""
    scores = {"a": 0.7, "b": 0.7, "c": 0.7}
    pi = pi_from_argmax_scores(scores)
    for arm, p in pi.items():
        assert pytest.approx(p) == 1.0 / 3.0


def test_pi_from_argmax_scores_handles_negative_scores():
    scores = {"a": -0.5, "b": -0.3, "c": -0.8}
    pi = pi_from_argmax_scores(scores)
    # b is the max (-0.3 > -0.5 > -0.8)
    assert pi["b"] == 1.0
    assert pi["a"] == 0.0
    assert pi["c"] == 0.0


def test_pi_from_argmax_scores_empty_returns_empty():
    assert pi_from_argmax_scores({}) == {}


def test_select_action_from_scores_argmax_wins_most_of_time():
    """With ε=0.02 and one strong argmax, the argmax should be picked
    ~98% of the time (1 - ε(1-1/K)). For K=3 → ε(2/3) = 0.0133 floor
    on each non-argmax → 1 - 2*0.0133 = 0.9733 on argmax."""
    scores = {"social_proof": 0.9, "authority": 0.4, "scarcity": 0.2}

    chosen_counts = {"social_proof": 0, "authority": 0, "scarcity": 0}
    log = InMemoryDecisionLog()

    for trial in range(2000):
        arm, _, _ = select_action_from_scores(
            scores=scores,
            user_id=f"u{trial}", decision_point_t=trial,
            archetype_id="x", category_id="x",
            moderators_S_t={}, producer=log.emit, rng_seed=trial,
        )
        chosen_counts[arm] += 1

    # Argmax should be picked ~97-98% of the time (some MC noise)
    argmax_rate = chosen_counts["social_proof"] / 2000
    assert 0.95 <= argmax_rate <= 0.99, f"argmax picked {argmax_rate}, expected ~0.97"
    # Non-argmax arms should each be picked ~0.7-1.5% of the time
    assert chosen_counts["authority"] > 0
    assert chosen_counts["scarcity"] > 0


def test_select_action_from_scores_logs_p_t_in_canonical_range():
    """K=3, ε=0.02 → bounds [ε/3, 1-ε(2/3)] = [0.00667, 0.98667]."""
    scores = {"a": 0.9, "b": 0.4, "c": 0.2}
    log = InMemoryDecisionLog()

    arm, p_t, record = select_action_from_scores(
        scores=scores,
        user_id="u1", decision_point_t=1,
        archetype_id="x", category_id="x",
        moderators_S_t={}, producer=log.emit, rng_seed=42,
    )

    assert arm in scores
    floor = 0.02 / 3.0 - 1e-9
    ceiling = 1.0 - 0.02 * (2.0 / 3.0) + 1e-9
    assert floor <= p_t <= ceiling
    assert record.p_t_known is True
    assert record.mechanism_id == arm


def test_select_action_from_scores_unavailability_silent():
    """I_t=0 → no decision, no log row."""
    scores = {"a": 0.5, "b": 0.5}
    log = InMemoryDecisionLog()

    arm, p_t, record = select_action_from_scores(
        scores=scores,
        user_id="u1", decision_point_t=1,
        archetype_id="x", category_id="x",
        moderators_S_t={}, availability_I_t=0,
        producer=log.emit, rng_seed=42,
    )

    assert arm is None
    assert p_t == 0.0
    assert record is None
    assert len(log) == 0


def test_select_action_from_scores_empty_raises():
    with pytest.raises(ValueError):
        select_action_from_scores(
            scores={}, user_id="u", decision_point_t=1,
            archetype_id="x", category_id="x", moderators_S_t={},
        )


def test_select_action_from_scores_handles_tied_argmax():
    """When the top score is tied, the ε-floor mixer + sample distribute
    fairly across the tied arms. No silent bias from argmax order."""
    scores = {"a": 0.5, "b": 0.5, "c": 0.0}

    chosen_counts = {"a": 0, "b": 0, "c": 0}
    for trial in range(500):
        arm, _, _ = select_action_from_scores(
            scores=scores,
            user_id=f"u{trial}", decision_point_t=trial,
            archetype_id="x", category_id="x",
            moderators_S_t={}, rng_seed=trial,
        )
        chosen_counts[arm] += 1

    # a and b should each be picked ~half (within MC noise — 500 trials),
    # c should rarely be picked (only via ε-floor leak)
    assert chosen_counts["a"] > 200
    assert chosen_counts["b"] > 200
    assert chosen_counts["c"] < 50


# -----------------------------------------------------------------------------
# select_action_from_pi — the shared core
# -----------------------------------------------------------------------------


def test_select_action_from_pi_flows_through():
    """Pre-computed π flows through ε-floor + sample correctly."""
    pi = {"a": 0.7, "b": 0.3}
    log = InMemoryDecisionLog()

    arm, p_t, record = select_action_from_pi(
        pi_ts=pi,
        user_id="u", decision_point_t=1,
        archetype_id="x", category_id="x",
        moderators_S_t={}, producer=log.emit, rng_seed=42,
    )

    assert arm in pi
    assert 0.01 <= p_t <= 0.99
    assert record.p_t_known is True


def test_select_action_from_pi_rejects_empty():
    with pytest.raises(ValueError):
        select_action_from_pi(
            pi_ts={}, user_id="u", decision_point_t=1,
            archetype_id="x", category_id="x", moderators_S_t={},
        )


# -----------------------------------------------------------------------------
# In-memory producer (existing test below)
# -----------------------------------------------------------------------------


def test_in_memory_log_collects_records():
    log = InMemoryDecisionLog()
    rec = MRTDecisionRecord(
        ts=0, user_id="u", decision_point_t=0, archetype_id="x",
        mechanism_id="m", category_id="c", moderators_S_t={},
        action_A_t=1, rand_prob_p_t=0.5, epsilon_floor=0.02,
        availability_I_t=1, p_t_known=True,
    )
    log.emit(rec)
    log.emit(rec)
    assert len(log) == 2
    log.reset()
    assert len(log) == 0
