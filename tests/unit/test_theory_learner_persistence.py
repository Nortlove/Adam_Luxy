"""Pin TheoryLearner Redis persistence — state survives restart.

Discipline anchors:
    - Without persistence, every backend restart wiped accumulated
      theoretical link posteriors. The "system gets stronger with
      every outcome" claim was true within a process lifetime;
      meaningless across restart boundaries. These tests pin that
      state survives the round-trip.
    - Schema version mismatch is honest: a future incompatible state
      schema returns the learner in fresh-init state rather than
      corrupting in-memory data.
    - Soft-fail: Redis-unavailable / serialization-error paths return
      False / no-op rather than raising. Backend startup never blocks
      on persistence.
"""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

from adam.core.learning.theory_learner import (
    LinkPosterior,
    TheoryLearner,
    ChainOutcomeRecord,
    _theory_learner_to_state_dict,
    _theory_learner_load_state_dict,
    _save_theory_learner_to_redis,
    _load_theory_learner_from_redis,
    maybe_persist_theory_learner,
)


def _populated_learner() -> TheoryLearner:
    """Build a learner with non-trivial state for round-trip tests."""
    learner = TheoryLearner(max_history=100)
    # Posteriors
    learner._link_posteriors["link_A"] = LinkPosterior(
        alpha=15.0, beta=5.0, observation_count=18, last_updated=1700000000.0,
    )
    learner._link_posteriors["link_B"] = LinkPosterior(
        alpha=3.0, beta=12.0, observation_count=13, last_updated=1700000100.0,
    )
    # Chain history
    learner._chain_history.append(ChainOutcomeRecord(
        chain_id="chain_1", decision_id="dec_X", mechanism="authority",
        theoretical_link_keys=["link_A", "link_B"],
        success=True, outcome_value=1.0, timestamp=1700000000.0,
    ))
    # Pattern stats
    learner._chain_pattern_stats["pattern_X"] = {
        "successes": 5, "failures": 2, "total_value": 5.0,
    }
    learner._total_outcomes = 18
    return learner


# -----------------------------------------------------------------------------
# State serialization round-trip
# -----------------------------------------------------------------------------


def test_state_dict_round_trip_preserves_posteriors():
    """Producer → state_dict → consumer must preserve every field of
    every LinkPosterior. Without this, posteriors load with stale
    Beta values after restart and learning starts from a wrong prior."""
    src = _populated_learner()
    state = _theory_learner_to_state_dict(src)

    dst = TheoryLearner()
    _theory_learner_load_state_dict(dst, state)

    assert "link_A" in dst._link_posteriors
    assert dst._link_posteriors["link_A"].alpha == 15.0
    assert dst._link_posteriors["link_A"].beta == 5.0
    assert dst._link_posteriors["link_A"].observation_count == 18
    assert dst._link_posteriors["link_A"].last_updated == 1700000000.0


def test_state_dict_round_trip_preserves_chain_history():
    src = _populated_learner()
    state = _theory_learner_to_state_dict(src)

    dst = TheoryLearner()
    _theory_learner_load_state_dict(dst, state)

    assert len(dst._chain_history) == 1
    rec = dst._chain_history[0]
    assert rec.chain_id == "chain_1"
    assert rec.theoretical_link_keys == ["link_A", "link_B"]
    assert rec.success is True


def test_state_dict_round_trip_preserves_pattern_stats():
    src = _populated_learner()
    state = _theory_learner_to_state_dict(src)

    dst = TheoryLearner()
    _theory_learner_load_state_dict(dst, state)

    assert dst._chain_pattern_stats["pattern_X"]["successes"] == 5
    assert dst._chain_pattern_stats["pattern_X"]["failures"] == 2
    assert dst._chain_pattern_stats["pattern_X"]["total_value"] == 5.0


def test_state_dict_round_trip_preserves_total_outcomes():
    src = _populated_learner()
    state = _theory_learner_to_state_dict(src)

    dst = TheoryLearner()
    _theory_learner_load_state_dict(dst, state)

    assert dst._total_outcomes == 18


def test_state_is_json_serializable():
    """The state dict MUST be json.dumps-able — Redis storage shape."""
    src = _populated_learner()
    state = _theory_learner_to_state_dict(src)

    # Must round-trip through JSON without losing fidelity
    json_str = json.dumps(state, default=str)
    parsed = json.loads(json_str)

    dst = TheoryLearner()
    _theory_learner_load_state_dict(dst, parsed)

    assert dst._link_posteriors["link_A"].alpha == 15.0
    assert dst._total_outcomes == 18


# -----------------------------------------------------------------------------
# Schema version handling
# -----------------------------------------------------------------------------


def test_schema_version_mismatch_skips_load():
    """A future incompatible state must skip load rather than corrupting
    the in-memory learner. Fresh-init state is honest."""
    state = {
        "schema_version": 999,  # future version
        "link_posteriors": {"link_A": {"alpha": 99.0, "beta": 99.0}},
        "total_outcomes": 99999,
    }

    learner = TheoryLearner()
    _theory_learner_load_state_dict(learner, state)

    # Nothing loaded — state remained fresh
    assert "link_A" not in learner._link_posteriors
    assert learner._total_outcomes == 0


# -----------------------------------------------------------------------------
# Redis save/load — mocked Redis client
# -----------------------------------------------------------------------------


def test_save_to_redis_writes_state_under_known_key():
    redis_mock = MagicMock()
    redis_mock.set = MagicMock()
    learner = _populated_learner()

    with patch(
        "adam.infrastructure.redis_client.get_redis", return_value=redis_mock,
    ):
        ok = _save_theory_learner_to_redis(learner)

    assert ok is True
    redis_mock.set.assert_called_once()
    key, payload = redis_mock.set.call_args.args
    assert key == "adam:theory_learner:state:v1"
    parsed = json.loads(payload)
    assert parsed["total_outcomes"] == 18
    assert "link_A" in parsed["link_posteriors"]


def test_save_to_redis_soft_fails_when_redis_unavailable():
    """Redis None → save returns False, no exception. Backend startup
    must never block on persistence."""
    with patch(
        "adam.infrastructure.redis_client.get_redis", return_value=None,
    ):
        learner = _populated_learner()
        ok = _save_theory_learner_to_redis(learner)
    assert ok is False


def test_load_from_redis_restores_state():
    """Round-trip through Redis: save → restart → load → state matches."""
    src = _populated_learner()
    state_json = json.dumps(_theory_learner_to_state_dict(src), default=str)

    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value=state_json)

    with patch(
        "adam.infrastructure.redis_client.get_redis", return_value=redis_mock,
    ):
        dst = TheoryLearner()
        ok = _load_theory_learner_from_redis(dst)

    assert ok is True
    assert dst._total_outcomes == 18
    assert "link_A" in dst._link_posteriors
    assert dst._link_posteriors["link_A"].alpha == 15.0


def test_load_from_redis_returns_false_when_key_empty():
    """No prior state in Redis → load returns False, learner starts fresh."""
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value=None)

    with patch(
        "adam.infrastructure.redis_client.get_redis", return_value=redis_mock,
    ):
        dst = TheoryLearner()
        ok = _load_theory_learner_from_redis(dst)

    assert ok is False
    assert dst._total_outcomes == 0


# -----------------------------------------------------------------------------
# Rate-limited persistence — every N updates
# -----------------------------------------------------------------------------


def test_maybe_persist_at_cadence_boundary():
    """Cadence default 10 — _total_outcomes==10 triggers save;
    _total_outcomes==1 does not. Without rate-limiting, every
    impression would write Redis; with it, batched into N-update
    flushes."""
    save_calls = []

    def fake_save(learner):
        save_calls.append(learner._total_outcomes)
        return True

    with patch(
        "adam.core.learning.theory_learner._save_theory_learner_to_redis",
        side_effect=fake_save,
    ):
        learner = TheoryLearner()
        learner._total_outcomes = 1
        maybe_persist_theory_learner(learner)
        assert save_calls == []

        learner._total_outcomes = 10  # cadence boundary
        maybe_persist_theory_learner(learner)
        assert save_calls == [10]

        learner._total_outcomes = 11  # not boundary
        maybe_persist_theory_learner(learner)
        assert save_calls == [10]

        learner._total_outcomes = 20  # next boundary
        maybe_persist_theory_learner(learner)
        assert save_calls == [10, 20]


def test_maybe_persist_zero_total_is_noop():
    """Fresh learner (total_outcomes=0) must not trigger save —
    avoids spurious empty-state writes."""
    save_called = []

    with patch(
        "adam.core.learning.theory_learner._save_theory_learner_to_redis",
        side_effect=lambda l: save_called.append(True),
    ):
        learner = TheoryLearner()
        # _total_outcomes = 0 by default
        maybe_persist_theory_learner(learner)

    assert save_called == []
