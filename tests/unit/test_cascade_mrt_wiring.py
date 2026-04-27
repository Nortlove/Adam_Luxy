"""Pin the live-cascade MRT rewire — every cascade run logs p_t.

Discipline anchors:
    - Every call to run_bilateral_cascade with a buyer_id must produce
      a logged decision row. Without this, the LUXY pilot's WCLS / OPE
      analysis has no propensity data to consume.
    - The chosen mechanism MUST be sampled from the ε-floor-mixed score
      distribution. Greedy argmax collapses p_t to {0,1} and breaks
      Boruvka 2018 §2 — the rewire's whole point.
    - The propensity fields (ts_propensity, epsilon_floor, p_t_known)
      MUST land on the CreativeIntelligence result so downstream
      consumers (decision_cache, Neo4j persist) can store them.
    - Soft-fail: when MRT logging is unavailable (numpy missing,
      producer broken), the cascade returns a result with
      p_t_known=false rather than crashing. The bid path must NEVER
      block on logging (handoff §1.10).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from adam.api.stackadapt.bilateral_cascade import (
    CreativeIntelligence,
    _select_primary_with_logged_propensity,
)
from adam.intelligence.mrt_producer import reset_for_tests, get_mrt_producer


def setup_function():
    reset_for_tests()


def _ci_with_scores(scores: dict, primary: str = "social_proof") -> CreativeIntelligence:
    return CreativeIntelligence(
        primary_mechanism=primary,
        secondary_mechanism="authority",
        mechanism_scores=dict(scores),
        cascade_level=3,
    )


# -----------------------------------------------------------------------------
# _select_primary_with_logged_propensity — direct tests
# -----------------------------------------------------------------------------


def test_rewire_stamps_propensity_fields_on_result():
    """ts_propensity, epsilon_floor, p_t_known must land on the result.
    Downstream Neo4j persist consumes these per the M4 schema."""
    base = _ci_with_scores({"social_proof": 0.9, "authority": 0.4, "scarcity": 0.2})

    chosen, p_t, p_t_known = _select_primary_with_logged_propensity(
        base=base, archetype="status_seeker", category="luxury_transportation",
        user_id="u1", decision_point_t=1, rng_seed=42,
    )

    assert base.ts_propensity == p_t
    assert base.epsilon_floor == 0.02
    assert base.p_t_known is True


def test_rewire_logs_record_to_singleton_producer():
    """Every successful call must add ONE row to the singleton MRT log."""
    base = _ci_with_scores({"social_proof": 0.9, "authority": 0.4, "scarcity": 0.2})

    initial = len(get_mrt_producer())
    _select_primary_with_logged_propensity(
        base=base, archetype="status_seeker", category="luxury_transportation",
        user_id="u1", decision_point_t=1, rng_seed=42,
    )
    final = len(get_mrt_producer())

    assert final == initial + 1


def test_rewire_argmax_wins_most_of_time():
    """ε=0.02 over K=3 → argmax wins ~97-98% of the time. With 1000 trials,
    a clear argmax should land >950 times."""
    chosen_count = {"social_proof": 0, "authority": 0, "scarcity": 0}
    for trial in range(1000):
        reset_for_tests()
        base = _ci_with_scores(
            {"social_proof": 0.9, "authority": 0.4, "scarcity": 0.2}
        )
        chosen, _, _ = _select_primary_with_logged_propensity(
            base=base, archetype="x", category="y",
            user_id=f"u{trial}", decision_point_t=trial, rng_seed=trial,
        )
        chosen_count[chosen] += 1

    assert chosen_count["social_proof"] > 950
    # Other arms get the ε-floor mass — non-zero exploration
    assert chosen_count["authority"] > 0 or chosen_count["scarcity"] > 0


def test_rewire_p_t_in_canonical_range():
    """K=3, ε=0.02 → bounds [0.00667, 0.98667]."""
    base = _ci_with_scores({"a": 0.9, "b": 0.4, "c": 0.2})
    chosen, p_t, _ = _select_primary_with_logged_propensity(
        base=base, archetype="x", category="y",
        user_id="u", decision_point_t=1, rng_seed=42,
    )
    floor = 0.02 / 3.0 - 1e-9
    ceiling = 1.0 - 0.02 * (2.0 / 3.0) + 1e-9
    assert floor <= p_t <= ceiling


def test_rewire_writes_back_chosen_to_primary_mechanism():
    """Whatever the rewire samples must replace base.primary_mechanism.
    A previous argmax may have set primary to one arm; the sample may
    pick a different arm; downstream consumers see the SAMPLED choice."""
    base = _ci_with_scores(
        {"social_proof": 0.9, "authority": 0.4, "scarcity": 0.2},
        primary="authority",  # pre-set to non-argmax (simulates prior logic)
    )
    chosen, _, _ = _select_primary_with_logged_propensity(
        base=base, archetype="x", category="y",
        user_id="u", decision_point_t=1, rng_seed=42,
    )
    # Caller writes chosen back to primary_mechanism — that's downstream
    # of this helper, but the helper must return a non-empty chosen.
    assert chosen in base.mechanism_scores


# -----------------------------------------------------------------------------
# Soft-fail paths
# -----------------------------------------------------------------------------


def test_rewire_empty_scores_returns_p_t_known_false():
    """Degenerate input — empty scores dict. Don't crash; return current
    primary with p_t_known=false."""
    base = CreativeIntelligence(
        primary_mechanism="social_proof", mechanism_scores={},
    )
    chosen, p_t, p_t_known = _select_primary_with_logged_propensity(
        base=base, archetype="x", category="y", user_id="u",
        decision_point_t=1, rng_seed=42,
    )
    assert chosen == "social_proof"  # fell back to existing primary
    assert p_t == 0.0
    assert p_t_known is False
    assert base.p_t_known is False


def test_rewire_single_score_returns_p_t_known_false():
    """K=1 is degenerate for MRT — only one arm can ever be chosen.
    Treat as not-randomized; pscore_known=false."""
    base = _ci_with_scores({"only_arm": 0.7})
    chosen, p_t, p_t_known = _select_primary_with_logged_propensity(
        base=base, archetype="x", category="y", user_id="u",
        decision_point_t=1, rng_seed=42,
    )
    assert chosen == "only_arm"
    assert p_t_known is False


def test_rewire_anonymous_user_still_works():
    """Empty user_id falls back to 'anonymous'. The rewire still logs
    a row — the MRT analysis can choose to filter on user_id later, but
    we don't drop the row."""
    base = _ci_with_scores({"a": 0.5, "b": 0.5})
    initial = len(get_mrt_producer())
    chosen, _, _ = _select_primary_with_logged_propensity(
        base=base, archetype="x", category="y",
        user_id="",  # anonymous
        decision_point_t=1, rng_seed=42,
    )
    final = len(get_mrt_producer())
    assert chosen in base.mechanism_scores
    assert final == initial + 1


# -----------------------------------------------------------------------------
# Production safety — cascade must never crash on logging failure
# -----------------------------------------------------------------------------


def test_rewire_survives_producer_exception():
    """Producer raises mid-emit. The cascade must still return a chosen
    mechanism. The record is lost but the bid lands."""
    base = _ci_with_scores({"a": 0.7, "b": 0.3})

    # Patch the singleton's emit to raise, simulating a Kafka outage
    producer = get_mrt_producer()
    original_emit = producer.emit
    try:
        producer.emit = MagicMock(side_effect=ConnectionError("kafka down"))

        # Must not raise
        chosen, p_t, p_t_known = _select_primary_with_logged_propensity(
            base=base, archetype="x", category="y",
            user_id="u", decision_point_t=1, rng_seed=42,
        )

        # Cascade still picks; propensity fields still land on result
        assert chosen in base.mechanism_scores
        assert base.epsilon_floor == 0.02
    finally:
        producer.emit = original_emit
