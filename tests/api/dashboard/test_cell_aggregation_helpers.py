"""Q.2.A — unit tests for cell_aggregation pure helpers.

These helpers are I/O-free; tests construct DecisionTrace + UserCohort
fixtures directly and assert aggregation correctness. Coverage:
cluster_id derivation, cluster aggregation, predicate aggregation
with dormant flagging, archetype aggregation with cold-start /
conversion lookups, mechanism orientation classification, cohort
confidence labels, cohort aggregation, anonymization guard, empty
window bounds.
"""

from datetime import datetime, timedelta, timezone

from adam.api.dashboard.cell_aggregation import (
    KNOWN_ARCHETYPES,
    KNOWN_PREDICATES,
    aggregate_by_archetype,
    aggregate_by_cluster,
    aggregate_by_cohort,
    aggregate_by_predicate,
    anonymize_buyer_id,
    classify_mechanism_orientation,
    cluster_id_for_creative,
    cohort_confidence_label,
    empty_window_bounds_now,
)
from adam.intelligence.cohort_discovery import UserCohort
from adam.intelligence.decision_trace import (
    AlternativeCandidate,
    ChainOfReasoning,
    ChainOfReasoningEntry,
    DecisionTrace,
)


def _make_trace(
    decision_id: str = "dec_1",
    user_id: str = "u_1",
    creative: str = "ridelux_hero_3",
    chain_names: tuple = (),
) -> DecisionTrace:
    entries = []
    if chain_names:
        n = len(chain_names)
        pct = 100.0 / n
        for name in chain_names:
            entries.append(
                ChainOfReasoningEntry(
                    name=name, contribution=0.5, pct_of_total=pct,
                )
            )
    return DecisionTrace(
        decision_id=decision_id,
        user_id=user_id,
        timestamp=datetime.now(timezone.utc),
        chosen_creative_id=creative,
        chosen_mechanism="authority",
        chosen_score=0.7,
        chain_of_reasoning=ChainOfReasoning(entries=entries, total=0.5),
    )


# --- cluster_id derivation ---


def test_cluster_id_strips_variant_suffix():
    assert cluster_id_for_creative("ridelux_hero_3") == "ridelux_hero"
    assert cluster_id_for_creative("ridelux_hero_12") == "ridelux_hero"


def test_cluster_id_passes_through_no_suffix():
    assert cluster_id_for_creative("ridelux_hero") == "ridelux_hero"


def test_cluster_id_none_returns_none():
    assert cluster_id_for_creative(None) is None
    assert cluster_id_for_creative("") is None


# --- aggregate_by_cluster ---


def test_aggregate_by_cluster_groups_variants():
    traces = [
        _make_trace("d1", creative="ridelux_hero_1"),
        _make_trace("d2", creative="ridelux_hero_2"),
        _make_trace("d3", creative="ridelux_value_1"),
    ]
    result = aggregate_by_cluster(traces)
    assert len(result) == 2
    by_id = {c.cluster_id: c for c in result}
    assert by_id["ridelux_hero"].impression_count == 2
    assert by_id["ridelux_value"].impression_count == 1
    assert abs(by_id["ridelux_hero"].share_of_total - 2/3) < 1e-6


def test_aggregate_by_cluster_empty():
    assert aggregate_by_cluster([]) == []


# --- aggregate_by_predicate ---


def test_aggregate_by_predicate_counts_fires_and_dormant():
    traces = [
        _make_trace("d1", chain_names=("fomo_active",)),
        _make_trace("d2", chain_names=("fomo_active", "psych_ownership")),
        _make_trace("d3", chain_names=()),
    ]
    result = aggregate_by_predicate(traces)
    by_name = {p.predicate_name: p for p in result}
    assert by_name["fomo_active"].fire_count == 2
    assert abs(by_name["fomo_active"].fire_rate - 2/3) < 1e-6
    assert not by_name["fomo_active"].dormant
    assert by_name["psych_ownership"].fire_count == 1
    # Predicate never fired in window → dormant
    assert by_name["maximizer_high"].fire_count == 0
    assert by_name["maximizer_high"].dormant


def test_aggregate_by_predicate_empty_traces_returns_empty_list():
    assert aggregate_by_predicate([]) == []


def test_aggregate_by_predicate_returns_full_known_catalog():
    traces = [_make_trace("d1", chain_names=())]
    result = aggregate_by_predicate(traces)
    assert len(result) == len(KNOWN_PREDICATES)
    assert all(p.dormant for p in result)


# --- aggregate_by_archetype ---


def test_aggregate_by_archetype_with_lookups():
    traces = [
        _make_trace("d1", user_id="u_a"),
        _make_trace("d2", user_id="u_a"),
        _make_trace("d3", user_id="u_b"),
    ]
    archmap = {"u_a": "achiever", "u_b": "explorer"}
    coldset = {"u_b"}  # u_b is cold-start
    convset = {"d1"}   # d1 converted

    result = aggregate_by_archetype(
        traces,
        archetype_lookup=lambda u: archmap.get(u),
        cold_start_lookup=lambda u: u in coldset,
        conversion_lookup=lambda d: d in convset,
    )
    by_arch = {a.archetype_id: a for a in result}
    assert by_arch["achiever"].impression_count == 2
    assert by_arch["achiever"].conversion_count == 1
    assert abs(by_arch["achiever"].conversion_rate - 0.5) < 1e-6
    assert abs(by_arch["achiever"].cold_start_share - 0.0) < 1e-6
    assert by_arch["explorer"].impression_count == 1
    assert abs(by_arch["explorer"].cold_start_share - 1.0) < 1e-6


def test_aggregate_by_archetype_skips_unknown_lookup():
    traces = [_make_trace("d1", user_id="u_x")]
    result = aggregate_by_archetype(
        traces,
        archetype_lookup=lambda u: None,
        cold_start_lookup=lambda u: False,
        conversion_lookup=lambda d: False,
    )
    assert result == []


def test_aggregate_by_archetype_orders_known_archetypes():
    # Sanity: KNOWN_ARCHETYPES has 8 entries
    assert len(KNOWN_ARCHETYPES) == 8


# --- mechanism orientation classification ---


def test_orientation_affiliative_dominance():
    orient, lead = classify_mechanism_orientation(
        ["social_proof", "liking", "unity", "authority"]
    )
    assert orient == "affiliative"
    assert lead == "social_proof"


def test_orientation_transactional_dominance():
    orient, lead = classify_mechanism_orientation(
        ["anchoring", "scarcity", "loss_aversion", "authority"]
    )
    assert orient == "transactional"
    assert lead == "anchoring"


def test_orientation_mixed_below_threshold():
    orient, lead = classify_mechanism_orientation(
        ["social_proof", "anchoring", "authority", "reciprocity"]
    )
    assert orient == "mixed"
    assert lead == "social_proof"


def test_orientation_empty_returns_mixed_unknown():
    orient, lead = classify_mechanism_orientation([])
    assert orient == "mixed"
    assert lead == "unknown"


# --- cohort confidence label ---


def test_confidence_label_high():
    assert cohort_confidence_label(0.85) == "high_confidence"
    assert cohort_confidence_label(0.95) == "high_confidence"


def test_confidence_label_partial():
    assert cohort_confidence_label(0.65) == "partial_evidence"
    assert cohort_confidence_label(0.55) == "partial_evidence"


def test_confidence_label_uninformative():
    assert cohort_confidence_label(0.30) == "uninformative"
    assert cohort_confidence_label(0.0) == "uninformative"


# --- aggregate_by_cohort ---


def test_aggregate_by_cohort_classifies_and_clamps():
    cohorts = [
        UserCohort(
            cohort_id="c_aff",
            size=300,
            sample_members=[],
            dominant_mechanisms=["social_proof", "liking", "unity"],
            compensatory_consumption_pattern=True,
            compensatory_detection_confidence=0.85,
        ),
        UserCohort(
            cohort_id="c_tr",
            size=100,
            sample_members=[],
            dominant_mechanisms=["anchoring", "scarcity"],
            compensatory_consumption_pattern=False,
            compensatory_detection_confidence=0.55,
        ),
    ]
    rates = {"c_aff": 0.42, "c_tr": 1.5}  # second is out-of-range; should clamp
    result = aggregate_by_cohort(
        cohorts, lambda cid: rates.get(cid, 0.0),
    )
    by_id = {m.cohort_id: m for m in result}
    assert by_id["c_aff"].mechanism_orientation == "affiliative"
    assert by_id["c_aff"].compensatory_flag is True
    assert by_id["c_aff"].confidence_label == "high_confidence"
    assert abs(by_id["c_aff"].conversion_rate - 0.42) < 1e-6
    assert by_id["c_tr"].mechanism_orientation == "transactional"
    assert by_id["c_tr"].compensatory_flag is False
    assert by_id["c_tr"].conversion_rate == 1.0  # clamped


def test_aggregate_by_cohort_empty():
    assert aggregate_by_cohort([], lambda cid: 0.0) == []


# --- privacy guard ---


def test_anonymize_buyer_id_deterministic():
    a = anonymize_buyer_id("buyer_abc_123")
    b = anonymize_buyer_id("buyer_abc_123")
    assert a == b
    assert a.startswith("buyer_")
    # Anonymized must NOT contain the raw input as a substring
    assert "abc_123" not in a


def test_anonymize_buyer_id_different_inputs_different_outputs():
    a = anonymize_buyer_id("buyer_one")
    b = anonymize_buyer_id("buyer_two")
    assert a != b


def test_anonymize_buyer_id_empty_returns_unknown():
    assert anonymize_buyer_id("") == "buyer_unknown"
    assert anonymize_buyer_id(None) == "buyer_unknown"


# --- empty window bounds ---


def test_empty_window_bounds_returns_pair():
    start, end = empty_window_bounds_now(7)
    assert isinstance(start, datetime)
    assert isinstance(end, datetime)
    assert end > start
    delta = end - start
    assert abs(delta.total_seconds() - 7 * 86400) < 60  # tolerance 1m


def test_empty_window_bounds_zero_days_yields_collapsed_window():
    start, end = empty_window_bounds_now(0)
    assert end >= start
    delta = end - start
    assert delta.total_seconds() < 5  # essentially same instant
