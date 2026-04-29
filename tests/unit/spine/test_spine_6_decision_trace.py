"""Tests for Spine #6 — Decision-Time Counterfactual Trace + Propensity.

Pins per directive Section 2 (Spine #6) + Section 5.4:
    1. DecisionTrace required fields + propensity in [0, 1]
    2. AlternativeDecomposition stores all per-candidate components
    3. chain_of_reasoning produces structured decomposition
    4. to_neo4j_props serializes nested objects as JSON strings
    5. compute_ttts_propensity closed-form (Jeunen 2025)
    6. IPS estimator: matches the played-arm reward when propensity = 1
    7. SNIPS estimator: reduces variance vs IPS
    8. Doubly Robust: degrades to IPS when reward_model = 0
    9. Store: record / query by decision_id / by sapid
   10. close_trace_with_outcome links outcome to trace
"""

from __future__ import annotations

import json

import pytest

from adam.intelligence.spine.spine_6_decision_trace import (
    AlternativeDecomposition,
    DecisionTrace,
    close_trace_with_outcome,
    compute_ttts_propensity,
    doubly_robust_estimate,
    ips_estimate,
    query_trace_by_id,
    query_trace_by_sapid,
    record_trace,
    reset_default_store,
    snips_estimate,
    store_size,
)


@pytest.fixture(autouse=True)
def _reset_store():
    reset_default_store()
    yield
    reset_default_store()


# -----------------------------------------------------------------------------
# DecisionTrace + AlternativeDecomposition validation
# -----------------------------------------------------------------------------


class TestDecisionTraceConstruction:

    def test_minimal_valid_construction(self):
        t = DecisionTrace(
            decision_id="d:1", user_id="u:1",
            chosen_mechanism="authority", chosen_score=0.5,
            propensity_chosen=0.4,
        )
        assert t.decision_id == "d:1"
        assert t.alternatives == []

    def test_propensity_must_be_in_unit_interval(self):
        with pytest.raises(ValueError, match="propensity_chosen"):
            DecisionTrace(
                decision_id="d", user_id="u",
                chosen_mechanism="authority", chosen_score=0.5,
                propensity_chosen=1.5,
            )

    def test_posture_confidence_validated(self):
        with pytest.raises(ValueError, match="page_posture_confidence"):
            DecisionTrace(
                decision_id="d", user_id="u",
                chosen_mechanism="authority", chosen_score=0.5,
                propensity_chosen=0.5,
                page_posture_confidence=1.5,
            )


class TestAlternativeDecomposition:

    def test_default_zeros(self):
        alt = AlternativeDecomposition(mechanism="scarcity", posterior_score=0.3)
        assert alt.free_energy_F == 0.0
        assert alt.fluency_score == 0.0
        assert alt.fluency_floor_passed is True

    def test_full_decomposition(self):
        alt = AlternativeDecomposition(
            mechanism="scarcity",
            posterior_score=0.3,
            free_energy_F=0.5,
            fluency_score=-0.5,
            fluency_floor_passed=False,
            posture_compatibility_score=-0.5,
            carryover_correction_term=0.1,
            epistemic_bonus=0.05,
            propensity_under_TS=0.2,
            final_score=0.45,
        )
        assert alt.posterior_score == 0.3
        assert alt.fluency_floor_passed is False


# -----------------------------------------------------------------------------
# chain_of_reasoning rendering
# -----------------------------------------------------------------------------


class TestChainOfReasoning:

    def test_renders_when_chosen_in_alternatives(self):
        chosen_alt = AlternativeDecomposition(
            mechanism="authority",
            posterior_score=0.7,
            free_energy_F=0.2,
            fluency_score=0.5,
            posture_compatibility_score=0.5,
            carryover_correction_term=0.1,
            epistemic_bonus=0.05,
        )
        other_alt = AlternativeDecomposition(
            mechanism="scarcity", posterior_score=0.3,
        )
        t = DecisionTrace(
            decision_id="d", user_id="u",
            chosen_mechanism="authority", chosen_score=1.5,
            propensity_chosen=0.6,
            alternatives=[chosen_alt, other_alt],
            page_posture="task_completion",
        )
        cor = t.chain_of_reasoning()
        assert cor["chosen_mechanism"] == "authority"
        assert cor["chosen_score"] == 1.5
        assert cor["components"]["posterior"] == 0.7
        assert cor["components"]["fluency"] == 0.5
        assert cor["components"]["carryover"] == 0.1
        assert cor["posture"] == "task_completion"

    def test_renders_when_chosen_not_in_alternatives(self):
        t = DecisionTrace(
            decision_id="d", user_id="u",
            chosen_mechanism="authority", chosen_score=0.5,
            propensity_chosen=0.5,
            alternatives=[],
        )
        cor = t.chain_of_reasoning()
        assert cor["chosen_mechanism"] == "authority"
        assert cor["chosen_score"] == 0.5
        assert cor["components"] == {}


# -----------------------------------------------------------------------------
# Neo4j serialization
# -----------------------------------------------------------------------------


class TestNeo4jSerialization:

    def test_props_include_required_fields(self):
        t = DecisionTrace(
            decision_id="d:1", user_id="u:1", sapid="sa_abc",
            chosen_mechanism="authority", chosen_score=0.5,
            propensity_chosen=0.4,
            alternatives=[
                AlternativeDecomposition(
                    mechanism="scarcity", posterior_score=0.3,
                ),
            ],
        )
        props = t.to_neo4j_props()
        assert props["decision_id"] == "d:1"
        assert props["sapid"] == "sa_abc"
        assert "alternatives_json" in props
        # Round-trip the alternatives JSON.
        alts = json.loads(props["alternatives_json"])
        assert alts[0]["mechanism"] == "scarcity"


# -----------------------------------------------------------------------------
# Closed-form TTTS propensity
# -----------------------------------------------------------------------------


class TestTTTSPropensity:

    def test_clearly_dominant_arm_high_propensity(self):
        # Authority dominant (always best); scarcity always loses.
        samples = {
            "authority": [0.9, 0.85, 0.92, 0.88, 0.95],
            "scarcity": [0.1, 0.15, 0.05, 0.12, 0.08],
        }
        p_auth = compute_ttts_propensity(samples, "authority")
        p_scar = compute_ttts_propensity(samples, "scarcity")
        # Authority is best 100% of the time → at β=0.5, propensity is
        # 0.5 · 1.0 + 0.5 · 0 = 0.5
        assert p_auth == pytest.approx(0.5)
        # Scarcity is best 0% of the time but is second 100% of the
        # time when not best → 0.5 · 0 + 0.5 · 1.0 = 0.5
        assert p_scar == pytest.approx(0.5)

    def test_unknown_arm_returns_zero(self):
        samples = {"authority": [0.5, 0.6]}
        p = compute_ttts_propensity(samples, "never_seen")
        assert p == 0.0

    def test_empty_samples_returns_zero(self):
        samples = {"authority": []}
        p = compute_ttts_propensity(samples, "authority")
        assert p == 0.0

    def test_mismatched_sample_counts_raises(self):
        samples = {"a": [0.5, 0.6], "b": [0.4]}
        with pytest.raises(ValueError, match="same number of"):
            compute_ttts_propensity(samples, "a")

    def test_propensity_in_unit_interval(self):
        samples = {
            "a": [0.5, 0.6, 0.7, 0.8],
            "b": [0.4, 0.5, 0.6, 0.7],
            "c": [0.3, 0.4, 0.5, 0.6],
        }
        for arm in ("a", "b", "c"):
            p = compute_ttts_propensity(samples, arm)
            assert 0.0 <= p <= 1.0

    def test_beta_zero_only_uses_second_best(self):
        """β = 0 → propensity is P(second-best | not best); never picks
        first-place arms."""
        samples = {
            "a": [0.9, 0.9, 0.9],  # always best
            "b": [0.5, 0.5, 0.5],  # always second
            "c": [0.1, 0.1, 0.1],  # always last
        }
        p_a = compute_ttts_propensity(samples, "a", beta=0.0)
        p_b = compute_ttts_propensity(samples, "b", beta=0.0)
        # a is always best → never selected under β=0 (TTTS picks
        # second-best when not exploring; β=0 means always exploring
        # second-best path).
        assert p_a == 0.0
        assert p_b == 1.0


# -----------------------------------------------------------------------------
# IPS / SNIPS / Doubly Robust off-policy estimators
# -----------------------------------------------------------------------------


class TestIPSEstimator:

    def _make_trace(self, mechanism, propensity, outcome_value=1.0):
        return DecisionTrace(
            decision_id=f"d:{mechanism}_{propensity}",
            user_id="u",
            chosen_mechanism=mechanism,
            chosen_score=0.5,
            propensity_chosen=propensity,
            outcome_value=outcome_value,
        )

    def test_no_traces_returns_zero(self):
        assert ips_estimate([], "authority") == 0.0

    def test_full_propensity_recovers_played_reward(self):
        """When all arms have propensity 1.0 and reward 1.0 for the
        target, IPS recovers 1.0."""
        traces = [
            self._make_trace("authority", 1.0, 1.0),
            self._make_trace("authority", 1.0, 1.0),
        ]
        # Each contributes 1/1.0 · 1.0 = 1.0; mean = 2.0 / 2 = 1.0
        assert ips_estimate(traces, "authority") == pytest.approx(1.0)

    def test_only_target_arm_traces_count(self):
        """Traces of OTHER arms contribute 0 (the indicator 1{a=target} = 0)."""
        traces = [
            self._make_trace("authority", 0.5, 1.0),
            self._make_trace("scarcity", 0.5, 1.0),  # different arm
        ]
        # IPS = (1.0/0.5 + 0) / 2 = 1.0
        assert ips_estimate(traces, "authority") == pytest.approx(1.0)

    def test_low_propensity_amplifies_reward(self):
        """A trace with low propensity contributes high IPS weight."""
        # propensity 0.1 → weight 10. Reward 1. Single trace mean = 10 / 1 = 10
        traces = [self._make_trace("authority", 0.1, 1.0)]
        assert ips_estimate(traces, "authority") == pytest.approx(10.0)


class TestSNIPSEstimator:

    def _make_trace(self, mechanism, propensity, outcome_value=1.0):
        return DecisionTrace(
            decision_id=f"d:{mechanism}_{propensity}",
            user_id="u",
            chosen_mechanism=mechanism,
            chosen_score=0.5,
            propensity_chosen=propensity,
            outcome_value=outcome_value,
        )

    def test_full_propensity_returns_played_reward(self):
        traces = [
            self._make_trace("authority", 1.0, 0.8),
            self._make_trace("authority", 1.0, 1.0),
        ]
        # SNIPS = (1·0.8 + 1·1.0) / (1 + 1) = 0.9
        assert snips_estimate(traces, "authority") == pytest.approx(0.9)

    def test_normalizes_by_total_weight(self):
        """SNIPS divides by sum of weights, so it's a weighted average
        of rewards weighted by inverse-propensity. Different from IPS
        which divides by N regardless of how many target-arm traces."""
        traces = [
            self._make_trace("authority", 0.1, 1.0),  # weight 10
            self._make_trace("scarcity", 0.5, 0.5),   # different arm
        ]
        # SNIPS for authority = (10·1.0) / 10 = 1.0 (only authority counted)
        assert snips_estimate(traces, "authority") == pytest.approx(1.0)


class TestDoublyRobustEstimator:

    def _make_trace(self, mechanism, propensity, outcome_value=1.0,
                    user_id="u"):
        return DecisionTrace(
            decision_id=f"d:{mechanism}_{propensity}_{user_id}",
            user_id=user_id,
            chosen_mechanism=mechanism,
            chosen_score=0.5,
            propensity_chosen=propensity,
            outcome_value=outcome_value,
        )

    def test_dr_matches_played_arm_when_model_is_zero(self):
        """When reward_model = 0 (q̂=0), DR reduces to IPS."""
        traces = [self._make_trace("authority", 1.0, 1.0)]
        dr = doubly_robust_estimate(traces, "authority", reward_model={})
        ips = ips_estimate(traces, "authority")
        assert dr == pytest.approx(ips)

    def test_dr_correct_when_model_is_perfect(self):
        """When reward_model perfectly predicts, the IPS correction
        term is zero and DR returns the model's prediction."""
        traces = [self._make_trace("authority", 1.0, 0.7)]
        # Model predicts 0.7 perfectly.
        rm = {("u", "authority"): 0.7, ("u", "scarcity"): 0.4}
        dr_auth = doubly_robust_estimate(traces, "authority", reward_model=rm)
        # q̂(target=authority) = 0.7; correction = (0.7 - 0.7)/1.0 = 0
        # DR = 0.7
        assert dr_auth == pytest.approx(0.7)


# -----------------------------------------------------------------------------
# In-memory store
# -----------------------------------------------------------------------------


class TestStore:

    def test_record_and_query_by_id(self):
        t = DecisionTrace(
            decision_id="d:abc", user_id="u",
            chosen_mechanism="authority", chosen_score=0.5,
            propensity_chosen=0.4,
        )
        record_trace(t)
        result = query_trace_by_id("d:abc")
        assert result is not None
        assert result.decision_id == "d:abc"

    def test_query_unknown_id_returns_none(self):
        assert query_trace_by_id("never_recorded") is None

    def test_query_by_sapid(self):
        t = DecisionTrace(
            decision_id="d:abc", user_id="u", sapid="sa_xyz",
            chosen_mechanism="authority", chosen_score=0.5,
            propensity_chosen=0.4,
        )
        record_trace(t)
        result = query_trace_by_sapid("sa_xyz")
        assert result is not None
        assert result.decision_id == "d:abc"

    def test_query_unknown_sapid_returns_none(self):
        assert query_trace_by_sapid("never_recorded") is None

    def test_store_size(self):
        assert store_size() == 0
        for i in range(5):
            record_trace(DecisionTrace(
                decision_id=f"d:{i}", user_id="u",
                chosen_mechanism="authority", chosen_score=0.5,
                propensity_chosen=0.4,
            ))
        assert store_size() == 5


# -----------------------------------------------------------------------------
# close_trace_with_outcome
# -----------------------------------------------------------------------------


class TestCloseTraceWithOutcome:

    def test_close_attaches_outcome(self):
        t = DecisionTrace(
            decision_id="d:1", user_id="u",
            chosen_mechanism="authority", chosen_score=0.5,
            propensity_chosen=0.4,
        )
        record_trace(t)
        updated = close_trace_with_outcome(
            "d:1", outcome_class="CONVERSION", outcome_value=1.0,
        )
        assert updated is not None
        assert updated.outcome_class == "CONVERSION"
        assert updated.outcome_value == 1.0
        assert updated.outcome_observed_at is not None
        # Re-query confirms persistence.
        re_queried = query_trace_by_id("d:1")
        assert re_queried.outcome_class == "CONVERSION"

    def test_close_unknown_id_returns_none(self):
        result = close_trace_with_outcome(
            "never_recorded", outcome_class="CONVERSION", outcome_value=1.0,
        )
        assert result is None
