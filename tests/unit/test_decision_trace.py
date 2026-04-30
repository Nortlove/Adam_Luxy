"""Pin Spine #6 schema slice — directive lines 224-250.

Tests pin:
  * DecisionTrace round-trips through Pydantic model_dump_json /
    model_validate_json without information loss.
  * AlternativeCandidate validates propensity ∈ [0, 1].
  * ChainOfReasoning percentages must sum to 100 ± 0.5; raw construction
    with bad sums raises ValidationError.
  * decompose_score_components builds valid chains:
      - empty mapping → empty chain
      - all-zero contributions → empty chain (no division by zero)
      - NaN / Inf contributions → skipped
      - magnitude-normalized percentages preserve sign on entries
      - single-component decomposition → 100% to that component
  * Builder produces a valid trace from minimal inputs.
  * Builder accepts score_components and routes through decompose.
  * Trace alternatives count > 50 raises ValidationError.
  * Schema is opt-in: extra fields rejected (extra="forbid").
"""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from adam.intelligence.decision_trace import (
    AlternativeCandidate,
    ChainOfReasoning,
    ChainOfReasoningEntry,
    DecisionTrace,
    build_decision_trace,
    decompose_score_components,
)


# -----------------------------------------------------------------------------
# decompose_score_components
# -----------------------------------------------------------------------------


def test_decompose_empty_mapping_returns_empty_chain():
    chain = decompose_score_components({})
    assert chain.entries == []
    assert chain.total == 0.0


def test_decompose_all_zero_returns_empty_chain():
    chain = decompose_score_components({"a": 0.0, "b": 0.0, "c": 0.0})
    assert chain.entries == []
    assert chain.total == 0.0


def test_decompose_single_component_is_100_pct():
    chain = decompose_score_components({"pragmatic": 0.5})
    assert len(chain.entries) == 1
    assert chain.entries[0].name == "pragmatic"
    assert chain.entries[0].contribution == 0.5
    assert chain.entries[0].pct_of_total == pytest.approx(100.0, abs=1e-9)
    assert chain.total == 0.5


def test_decompose_two_equal_components_split_50_50():
    chain = decompose_score_components({"a": 0.3, "b": 0.3})
    assert len(chain.entries) == 2
    pct_a = next(e.pct_of_total for e in chain.entries if e.name == "a")
    pct_b = next(e.pct_of_total for e in chain.entries if e.name == "b")
    assert pct_a == pytest.approx(50.0, abs=1e-6)
    assert pct_b == pytest.approx(50.0, abs=1e-6)


def test_decompose_negative_components_use_magnitude_normalization():
    """Sign of contribution preserved on entry; pct uses magnitude."""
    chain = decompose_score_components({"pragmatic": 0.4, "epistemic": -0.1})
    pragmatic = next(e for e in chain.entries if e.name == "pragmatic")
    epistemic = next(e for e in chain.entries if e.name == "epistemic")
    assert pragmatic.contribution == 0.4
    assert epistemic.contribution == -0.1
    # Magnitude total = 0.5; pct_pragmatic = 80; pct_epistemic = 20
    assert pragmatic.pct_of_total == pytest.approx(80.0, abs=1e-6)
    assert epistemic.pct_of_total == pytest.approx(20.0, abs=1e-6)
    # Signed total = 0.3
    assert chain.total == pytest.approx(0.3, abs=1e-9)


def test_decompose_canceling_components_still_produce_nonzero_pcts():
    """A and B perfectly cancel: a=+0.5, b=-0.5. Magnitude normalization
    still gives each 50%. Without magnitude normalization, the signed
    total would be 0 and percentages would be undefined."""
    chain = decompose_score_components({"a": 0.5, "b": -0.5})
    pcts = sorted(e.pct_of_total for e in chain.entries)
    assert pcts[0] == pytest.approx(50.0, abs=1e-6)
    assert pcts[1] == pytest.approx(50.0, abs=1e-6)
    assert chain.total == pytest.approx(0.0, abs=1e-9)


def test_decompose_skips_nan_and_inf():
    """NaN / Inf contributions silently dropped — defensive against
    upstream NaN propagation rather than infecting the chain."""
    chain = decompose_score_components({
        "a": 0.5,
        "b": float("nan"),
        "c": float("inf"),
        "d": -float("inf"),
        "e": 0.5,
    })
    names = {e.name for e in chain.entries}
    assert names == {"a", "e"}
    assert all(e.pct_of_total == pytest.approx(50.0, abs=1e-6) for e in chain.entries)


def test_decompose_pcts_sum_to_100_under_floats():
    """Many small components — float accumulation must not break the
    validator's 100 ± 0.5 invariant."""
    contributions = {f"comp_{i}": 0.01 * (i + 1) for i in range(50)}
    chain = decompose_score_components(contributions)
    pct_sum = sum(e.pct_of_total for e in chain.entries)
    assert 99.5 <= pct_sum <= 100.5


# -----------------------------------------------------------------------------
# ChainOfReasoning validator
# -----------------------------------------------------------------------------


def test_chain_validator_rejects_bad_pct_sum():
    """Hand-constructed chain with percentages NOT summing to ~100 →
    ValidationError. Forces callers to go through decompose_score_components."""
    with pytest.raises(ValidationError):
        ChainOfReasoning(
            entries=[
                ChainOfReasoningEntry(
                    name="a", contribution=1.0, pct_of_total=70.0,
                ),
                ChainOfReasoningEntry(
                    name="b", contribution=1.0, pct_of_total=10.0,
                ),
            ],
            total=2.0,
        )


def test_chain_validator_accepts_empty_entries():
    chain = ChainOfReasoning(entries=[], total=0.0)
    assert chain.entries == []


def test_chain_entry_pct_must_be_in_zero_hundred():
    with pytest.raises(ValidationError):
        ChainOfReasoningEntry(
            name="a", contribution=1.0, pct_of_total=150.0,
        )
    with pytest.raises(ValidationError):
        ChainOfReasoningEntry(
            name="a", contribution=1.0, pct_of_total=-1.0,
        )


# -----------------------------------------------------------------------------
# AlternativeCandidate
# -----------------------------------------------------------------------------


def test_alternative_minimal_construction():
    alt = AlternativeCandidate(
        creative_id="creative-7",
        mechanism="automatic_evaluation",
        posterior_score=0.65,
        propensity_under_TS=0.18,
    )
    assert alt.free_energy_F is None
    assert alt.fluency_score is None
    assert alt.bid_value is None


def test_alternative_propensity_bounds():
    with pytest.raises(ValidationError):
        AlternativeCandidate(
            creative_id="c", mechanism="m",
            posterior_score=0.5, propensity_under_TS=1.5,
        )
    with pytest.raises(ValidationError):
        AlternativeCandidate(
            creative_id="c", mechanism="m",
            posterior_score=0.5, propensity_under_TS=-0.1,
        )


def test_alternative_extra_fields_forbidden():
    """extra='forbid' — typos / unexpected fields raise rather than
    silently being accepted (would cause schema drift)."""
    with pytest.raises(ValidationError):
        AlternativeCandidate(
            creative_id="c", mechanism="m",
            posterior_score=0.5, propensity_under_TS=0.2,
            unknown_field=42,  # type: ignore[call-arg]
        )


# -----------------------------------------------------------------------------
# DecisionTrace
# -----------------------------------------------------------------------------


def test_trace_minimal_construction_via_builder():
    trace = build_decision_trace(
        decision_id="dec-1",
        user_id="user-7",
        chosen_creative_id="creative-3",
        chosen_mechanism="automatic_evaluation",
        chosen_score=0.72,
    )
    assert trace.decision_id == "dec-1"
    assert trace.alternatives == []
    assert trace.chain_of_reasoning.entries == []
    assert trace.timestamp.tzinfo is not None  # default is UTC
    assert trace.schema_version == "1.0"


def test_trace_builder_routes_score_components_through_decompose():
    trace = build_decision_trace(
        decision_id="dec-2",
        user_id="user-7",
        chosen_creative_id="c",
        chosen_mechanism="m",
        chosen_score=0.5,
        score_components={"pragmatic": 0.3, "fluency": 0.2},
    )
    assert len(trace.chain_of_reasoning.entries) == 2
    pct_sum = sum(e.pct_of_total for e in trace.chain_of_reasoning.entries)
    assert pct_sum == pytest.approx(100.0, abs=0.5)


def test_trace_builder_accepts_alternatives():
    alts = [
        AlternativeCandidate(
            creative_id="c1", mechanism="m1",
            posterior_score=0.6, propensity_under_TS=0.3,
        ),
        AlternativeCandidate(
            creative_id="c2", mechanism="m2",
            posterior_score=0.55, propensity_under_TS=0.25,
            fluency_score=0.4,
        ),
    ]
    trace = build_decision_trace(
        decision_id="dec-3",
        user_id="user-7",
        chosen_creative_id="c0",
        chosen_mechanism="m0",
        chosen_score=0.7,
        alternatives=alts,
    )
    assert len(trace.alternatives) == 2
    assert trace.alternatives[0].creative_id == "c1"
    assert trace.alternatives[1].fluency_score == 0.4


def test_trace_round_trips_through_json():
    """model_dump_json → model_validate_json preserves the trace."""
    trace = build_decision_trace(
        decision_id="dec-4",
        user_id="user-99",
        chosen_creative_id="creative-7",
        chosen_mechanism="automatic_evaluation",
        chosen_score=0.8,
        score_components={
            "pragmatic": 0.5, "fluency": 0.2, "epistemic": 0.1,
        },
        alternatives=[
            AlternativeCandidate(
                creative_id="alt1", mechanism="m_alt",
                posterior_score=0.6, propensity_under_TS=0.2,
            ),
        ],
        user_posterior_snapshot={"alignment_x": 0.4, "alignment_y": 0.6},
        page_posture_vector=[0.1, 0.2, -0.3],
        posture_class="blend_compatible",
        posture_confidence=0.78,
        bid_value=2.45,
    )
    blob = trace.model_dump_json()
    rehydrated = DecisionTrace.model_validate_json(blob)
    assert rehydrated.decision_id == trace.decision_id
    assert rehydrated.chosen_score == trace.chosen_score
    assert (
        rehydrated.alternatives[0].creative_id
        == trace.alternatives[0].creative_id
    )
    assert rehydrated.user_posterior_snapshot == trace.user_posterior_snapshot
    assert rehydrated.page_posture_vector == trace.page_posture_vector
    assert rehydrated.posture_confidence == trace.posture_confidence
    # Chain percentages preserved within tolerance
    orig_pcts = sorted(e.pct_of_total for e in trace.chain_of_reasoning.entries)
    new_pcts = sorted(e.pct_of_total for e in rehydrated.chain_of_reasoning.entries)
    assert orig_pcts == pytest.approx(new_pcts, abs=1e-6)


def test_trace_posture_confidence_bounds():
    with pytest.raises(ValidationError):
        DecisionTrace(
            decision_id="d", user_id="u",
            timestamp=datetime.now(timezone.utc),
            chosen_creative_id="c", chosen_mechanism="m",
            chosen_score=0.5,
            posture_confidence=1.5,
        )


def test_trace_alternatives_explosion_rejected():
    """50+ alternatives → ValidationError (likely accidental)."""
    too_many = [
        AlternativeCandidate(
            creative_id=f"c{i}", mechanism="m",
            posterior_score=0.5, propensity_under_TS=0.05,
        )
        for i in range(60)
    ]
    with pytest.raises(ValidationError):
        DecisionTrace(
            decision_id="d", user_id="u",
            timestamp=datetime.now(timezone.utc),
            chosen_creative_id="c", chosen_mechanism="m",
            chosen_score=0.5,
            alternatives=too_many,
        )


def test_trace_extra_fields_rejected():
    with pytest.raises(ValidationError):
        DecisionTrace(
            decision_id="d", user_id="u",
            timestamp=datetime.now(timezone.utc),
            chosen_creative_id="c", chosen_mechanism="m",
            chosen_score=0.5,
            new_unexpected_field=1.23,  # type: ignore[call-arg]
        )


def test_trace_default_chain_is_empty():
    trace = build_decision_trace(
        decision_id="d", user_id="u",
        chosen_creative_id="c", chosen_mechanism="m",
        chosen_score=0.5,
    )
    assert isinstance(trace.chain_of_reasoning, ChainOfReasoning)
    assert trace.chain_of_reasoning.entries == []
    assert trace.chain_of_reasoning.total == 0.0


def test_trace_json_is_valid_json():
    """The serialized trace must be parseable as JSON."""
    trace = build_decision_trace(
        decision_id="d", user_id="u",
        chosen_creative_id="c", chosen_mechanism="m",
        chosen_score=0.5,
    )
    blob = trace.model_dump_json()
    parsed = json.loads(blob)
    assert parsed["decision_id"] == "d"
    assert parsed["chosen_mechanism"] == "m"
    assert "schema_version" in parsed
