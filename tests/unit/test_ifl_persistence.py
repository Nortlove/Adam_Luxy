"""Pin InferentialLearningAgent persistence — proposition graph survives restart.

Discipline anchors:
    - The proposition graph (hypotheses + statuses + evidence ratios +
      parent/child relationships + complexity-ceiling unlock progress)
      is the agent's accumulated theory. Without persistence, every
      restart wiped it; the platform's "system understands more over
      time" claim required persistence to be meaningful.
    - Schema mismatch returns fresh-init state (no propositions /
      experiments) — honest empty rather than corrupted overlay.
"""

from __future__ import annotations

import json
import time
from unittest.mock import patch, MagicMock

from adam.intelligence.inferential_learning_agent import (
    ComplexityLevel,
    InferentialLearningAgent,
    Proposition,
    PropositionStatus,
    Experiment,
    _ifl_to_state_dict,
    _ifl_load_state_dict,
    _save_ifl_to_redis,
    _load_ifl_from_redis,
    maybe_persist_ifl,
)


def _populated_agent() -> InferentialLearningAgent:
    """Agent with non-trivial proposition graph + experiments."""
    agent = InferentialLearningAgent()
    p = Proposition(
        prop_id="prop_test_1",
        statement="Authority works for connectors in luxury transportation",
        complexity=ComplexityLevel.CONDITIONAL,
        archetype="connector",
        mechanism="authority",
        domain_category="luxury_transportation",
        supporting_observations=12,
        contradicting_observations=3,
        total_observations=15,
        confidence=0.78,
        status=PropositionStatus.HYPOTHESIS,
        last_tested_at=1700000000.0,
        test_count=15,
    )
    agent.propositions[p.prop_id] = p
    e = Experiment(
        experiment_id="exp_test_1",
        proposition_id="prop_test_1",
        description="Test authority vs scarcity for connectors",
        test_mechanism="authority",
        test_archetype="connector",
        observations=42,
        successes=18,
        actual_rate=0.43,
        baseline_rate=0.30,
    )
    agent.experiments[e.experiment_id] = e
    agent._observation_buffer = [
        {"archetype": "connector", "mechanism": "authority", "outcome_value": 1.0},
    ]
    agent._total_observations = 15
    agent._theory_revisions = 2
    agent._current_complexity_ceiling = ComplexityLevel.CAUSAL_CHAIN
    return agent


def test_state_dict_round_trip_preserves_propositions():
    src = _populated_agent()
    state = _ifl_to_state_dict(src)

    dst = InferentialLearningAgent()
    _ifl_load_state_dict(dst, state)

    assert "prop_test_1" in dst.propositions
    p = dst.propositions["prop_test_1"]
    assert p.statement.startswith("Authority works")
    assert p.archetype == "connector"
    assert p.mechanism == "authority"
    assert p.confidence == 0.78
    assert p.supporting_observations == 12
    assert p.total_observations == 15
    assert p.complexity == ComplexityLevel.CONDITIONAL
    assert p.status == PropositionStatus.HYPOTHESIS


def test_state_dict_round_trip_preserves_experiments():
    src = _populated_agent()
    state = _ifl_to_state_dict(src)

    dst = InferentialLearningAgent()
    _ifl_load_state_dict(dst, state)

    assert "exp_test_1" in dst.experiments
    e = dst.experiments["exp_test_1"]
    assert e.proposition_id == "prop_test_1"
    assert e.observations == 42
    assert e.actual_rate == 0.43


def test_state_dict_round_trip_preserves_complexity_ceiling():
    """Complexity ceiling unlocks progressively as observation count
    grows. After restart, the unlock progress must be preserved —
    otherwise the agent loses authorization to form higher-complexity
    propositions."""
    src = _populated_agent()
    state = _ifl_to_state_dict(src)

    dst = InferentialLearningAgent()
    _ifl_load_state_dict(dst, state)

    assert dst._current_complexity_ceiling == ComplexityLevel.CAUSAL_CHAIN
    assert dst._total_observations == 15
    assert dst._theory_revisions == 2


def test_state_dict_is_json_serializable():
    src = _populated_agent()
    state = _ifl_to_state_dict(src)

    json_str = json.dumps(state, default=str)
    parsed = json.loads(json_str)

    dst = InferentialLearningAgent()
    _ifl_load_state_dict(dst, parsed)

    assert "prop_test_1" in dst.propositions


def test_schema_version_mismatch_skips_load():
    state = {
        "schema_version": 999,
        "propositions": {"prop_X": {"statement": "should not load"}},
        "total_observations": 99999,
    }
    agent = InferentialLearningAgent()
    _ifl_load_state_dict(agent, state)

    assert "prop_X" not in agent.propositions
    assert agent._total_observations == 0


def test_save_to_redis_writes_state():
    redis_mock = MagicMock()
    redis_mock.set = MagicMock()
    agent = _populated_agent()

    with patch(
        "adam.infrastructure.redis_client.get_redis", return_value=redis_mock,
    ):
        ok = _save_ifl_to_redis(agent)

    assert ok is True
    redis_mock.set.assert_called_once()
    key, payload = redis_mock.set.call_args.args
    assert key == "adam:inferential_agent:state:v1"
    parsed = json.loads(payload)
    assert "prop_test_1" in parsed["propositions"]


def test_save_to_redis_soft_fails_when_unavailable():
    with patch(
        "adam.infrastructure.redis_client.get_redis", return_value=None,
    ):
        agent = _populated_agent()
        ok = _save_ifl_to_redis(agent)
    assert ok is False


def test_load_from_redis_restores_state():
    src = _populated_agent()
    state_json = json.dumps(_ifl_to_state_dict(src), default=str)

    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value=state_json)

    with patch(
        "adam.infrastructure.redis_client.get_redis", return_value=redis_mock,
    ):
        dst = InferentialLearningAgent()
        ok = _load_ifl_from_redis(dst)

    assert ok is True
    assert "prop_test_1" in dst.propositions


def test_load_from_redis_returns_false_when_key_empty():
    redis_mock = MagicMock()
    redis_mock.get = MagicMock(return_value=None)

    with patch(
        "adam.infrastructure.redis_client.get_redis", return_value=redis_mock,
    ):
        dst = InferentialLearningAgent()
        ok = _load_ifl_from_redis(dst)

    assert ok is False
    assert len(dst.propositions) == 0


def test_maybe_persist_at_cadence_boundary():
    save_calls = []

    def fake_save(agent):
        save_calls.append(agent._total_observations)
        return True

    with patch(
        "adam.intelligence.inferential_learning_agent._save_ifl_to_redis",
        side_effect=fake_save,
    ):
        agent = InferentialLearningAgent()
        agent._total_observations = 1
        maybe_persist_ifl(agent)
        assert save_calls == []

        agent._total_observations = 10
        maybe_persist_ifl(agent)
        assert save_calls == [10]

        agent._total_observations = 20
        maybe_persist_ifl(agent)
        assert save_calls == [10, 20]


def test_maybe_persist_zero_total_is_noop():
    save_called = []

    with patch(
        "adam.intelligence.inferential_learning_agent._save_ifl_to_redis",
        side_effect=lambda a: save_called.append(True),
    ):
        agent = InferentialLearningAgent()
        maybe_persist_ifl(agent)

    assert save_called == []


def test_observe_increments_and_persists_at_cadence():
    """observe() increments _total_observations and triggers
    rate-limited save. End-to-end: ten observe() calls trigger one
    save."""
    save_calls = []

    with patch(
        "adam.intelligence.inferential_learning_agent._save_ifl_to_redis",
        side_effect=lambda a: save_calls.append(a._total_observations),
    ):
        agent = InferentialLearningAgent()
        for i in range(10):
            agent.observe({"archetype": "test", "mechanism": "test", "outcome_value": 0.5})

    # Cadence 10 → save fires when _total_observations hits 10
    assert save_calls == [10]
