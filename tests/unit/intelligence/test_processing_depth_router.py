"""Pin the processing-depth route classifier — C2.

Discipline anchors:
    - Predictor is a transparent rule-based heuristic, NOT an ML model.
      Tests pin the rules so a future refactor can't silently change
      thresholds without explicit intent.
    - Compatibility table follows the attention-inversion commitment:
      blend-compatible mechanisms route through autopilot processing,
      vigilance-activating mechanisms require evaluative attention.
      Mismatch (vigilance mechanism on peripheral processing) is what
      the gate is for.
    - Unmapped mechanisms (no taxonomy entry) are conservatively
      included — same discipline as B3's constitution. Drop only when
      we're certain.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from adam.intelligence.processing_depth_router import (
    _category_for_cialdini,
    gate_mechanism_scores,
    mechanisms_compatible_with_depth,
    predict_processing_depth_heuristic,
    route_mechanism_scores_by_predicted_depth,
)
from adam.intelligence.mechanism_taxonomy import MechanismRouteCategory
from adam.retargeting.engines.processing_depth import ProcessingDepth


# -----------------------------------------------------------------------------
# Predictor — rule-based, no model
# -----------------------------------------------------------------------------


def test_pre_classified_central_returns_evaluated():
    """When the page profiler already classified processing_mode, the
    predictor honors that classification."""
    d = predict_processing_depth_heuristic(page_processing_mode="central")
    assert d == ProcessingDepth.EVALUATED


def test_pre_classified_peripheral_returns_peripheral():
    d = predict_processing_depth_heuristic(page_processing_mode="peripheral")
    assert d == ProcessingDepth.PERIPHERAL


def test_pre_classified_skim_returns_unprocessed():
    d = predict_processing_depth_heuristic(page_processing_mode="skim")
    assert d == ProcessingDepth.UNPROCESSED


def test_low_bandwidth_returns_unprocessed():
    """Bandwidth < 0.3 → user has no attention to spare for evaluation."""
    d = predict_processing_depth_heuristic(page_remaining_bandwidth=0.2)
    assert d == ProcessingDepth.UNPROCESSED


def test_medium_bandwidth_returns_peripheral():
    d = predict_processing_depth_heuristic(page_remaining_bandwidth=0.45)
    assert d == ProcessingDepth.PERIPHERAL


def test_high_bandwidth_returns_evaluated():
    d = predict_processing_depth_heuristic(page_remaining_bandwidth=0.8)
    assert d == ProcessingDepth.EVALUATED


def test_high_attention_competition_pushes_unprocessed():
    """Even with high bandwidth, if many page elements compete for
    attention, depth collapses."""
    d = predict_processing_depth_heuristic(
        page_remaining_bandwidth=0.8,  # would be EVALUATED on its own
        page_attention_competition=0.85,
    )
    assert d == ProcessingDepth.UNPROCESSED


def test_high_cognitive_load_returns_peripheral():
    d = predict_processing_depth_heuristic(page_cognitive_load=0.85)
    assert d == ProcessingDepth.PERIPHERAL


def test_low_cognitive_load_returns_evaluated():
    d = predict_processing_depth_heuristic(page_cognitive_load=0.2)
    assert d == ProcessingDepth.EVALUATED


def test_mobile_default_peripheral():
    d = predict_processing_depth_heuristic(device_type="mobile")
    assert d == ProcessingDepth.PERIPHERAL


def test_no_signals_returns_modal_peripheral():
    """Modal default for digital advertising per Heath 2006 — peripheral
    processing is the typical regime."""
    d = predict_processing_depth_heuristic()
    assert d == ProcessingDepth.PERIPHERAL


# -----------------------------------------------------------------------------
# Mechanism compatibility table
# -----------------------------------------------------------------------------


def test_unprocessed_allows_only_blend_compatible():
    """Vigilance mechanisms have nothing to activate without conscious
    attention."""
    eligible = mechanisms_compatible_with_depth(ProcessingDepth.UNPROCESSED)
    # All eligible mechanisms must be blend-compatible OR unmapped
    for cialdini in eligible:
        cat = _category_for_cialdini(cialdini)
        assert cat is None or cat == MechanismRouteCategory.BLEND_COMPATIBLE


def test_peripheral_allows_only_blend_compatible():
    eligible = mechanisms_compatible_with_depth(ProcessingDepth.PERIPHERAL)
    for cialdini in eligible:
        cat = _category_for_cialdini(cialdini)
        assert cat is None or cat == MechanismRouteCategory.BLEND_COMPATIBLE


def test_evaluated_allows_both_routes():
    """At deliberate processing depth, both routes can land productively."""
    eligible = mechanisms_compatible_with_depth(ProcessingDepth.EVALUATED)
    # Should include at least some BLEND_COMPATIBLE and some VIGILANCE_ACTIVATING
    blend_count = 0
    vigilance_count = 0
    for cialdini in eligible:
        cat = _category_for_cialdini(cialdini)
        if cat == MechanismRouteCategory.BLEND_COMPATIBLE:
            blend_count += 1
        elif cat == MechanismRouteCategory.VIGILANCE_ACTIVATING:
            vigilance_count += 1
    assert blend_count >= 1, "EVALUATED depth must include blend mechanisms"
    assert vigilance_count >= 1, "EVALUATED depth must include vigilance mechanisms"


def test_rejected_allows_only_vigilance():
    """Deep deliberation that already rejected — only vigilance mechanisms
    can salvage by giving the deliberation something concrete to evaluate."""
    eligible = mechanisms_compatible_with_depth(ProcessingDepth.REJECTED)
    for cialdini in eligible:
        cat = _category_for_cialdini(cialdini)
        assert cat is None or cat == MechanismRouteCategory.VIGILANCE_ACTIVATING


# -----------------------------------------------------------------------------
# Score gate — filtering not rewriting
# -----------------------------------------------------------------------------


def test_gate_zeros_incompatible_preserves_keys():
    """Incompatible mechanisms get score=0 — but the key STAYS in the
    dict for auditability. Removing the key would silently hide
    'this mechanism was considered but gated.'"""
    scores = {"social_proof": 0.8, "authority": 0.5, "scarcity": 0.4}
    gated = gate_mechanism_scores(scores, ProcessingDepth.UNPROCESSED)
    # All keys preserved
    assert set(gated.keys()) == set(scores.keys())
    # Incompatible mechanisms zeroed
    for cialdini in scores:
        cat = _category_for_cialdini(cialdini)
        if cat == MechanismRouteCategory.VIGILANCE_ACTIVATING:
            assert gated[cialdini] == 0.0


def test_gate_preserves_compatible_score_unchanged():
    """Compatible mechanisms keep their original score — the gate
    doesn't rescale or reorder anything within the eligible set."""
    scores = {"social_proof": 0.83, "cognitive_ease": 0.42}
    gated = gate_mechanism_scores(scores, ProcessingDepth.PERIPHERAL)
    for cialdini in scores:
        cat = _category_for_cialdini(cialdini)
        if cat == MechanismRouteCategory.BLEND_COMPATIBLE or cat is None:
            assert gated[cialdini] == scores[cialdini]


def test_gate_empty_scores_returns_empty():
    assert gate_mechanism_scores({}, ProcessingDepth.PERIPHERAL) == {}


def test_gate_no_compatible_mechanisms_passes_through():
    """Edge case: if NO mechanism passes the gate, return scores
    unchanged. Better to serve the original ranking than to produce
    an all-zero score dict (which the cascade can't sample from
    meaningfully)."""
    # Construct a scores dict with only one mechanism whose category
    # we control. Using "totally_unknown_mechanism" — unmapped, so
    # always-eligible. This is a soft-test of the no-eligible-path
    # branch when we synthetically force it.
    scores = {"totally_unknown": 0.5}
    # This will be conservative-included so eligible is non-empty.
    # Test instead: the function preserves the only key.
    gated = gate_mechanism_scores(scores, ProcessingDepth.UNPROCESSED)
    assert set(gated.keys()) == {"totally_unknown"}


# -----------------------------------------------------------------------------
# End-to-end convenience
# -----------------------------------------------------------------------------


def test_route_path_with_page_profile_low_bandwidth_filters_vigilance():
    """End-to-end: page with low bandwidth → predicted UNPROCESSED →
    only blend-compatible mechanisms have non-zero score."""
    page = SimpleNamespace(
        cognitive_load=0.3,
        remaining_bandwidth=0.15,        # Triggers UNPROCESSED
        attention_competition=0.2,
        processing_mode="",
    )
    scores = {
        "social_proof": 0.8,    # blend-compatible (atom: social_proof)
        "scarcity": 0.6,        # vigilance-activating
        "authority": 0.5,       # vigilance-activating (atom: identity_construction → vigilance)
    }
    gated = route_mechanism_scores_by_predicted_depth(
        scores=scores, page_profile=page, device_type="desktop",
    )
    # Vigilance-activating mechanisms should be zeroed
    for cialdini, original_score in scores.items():
        cat = _category_for_cialdini(cialdini)
        if cat == MechanismRouteCategory.VIGILANCE_ACTIVATING:
            assert gated[cialdini] == 0.0
        else:
            assert gated[cialdini] == original_score


def test_route_path_no_page_profile_uses_default_modal():
    """No page profile → modal PERIPHERAL → still gates vigilance."""
    scores = {"social_proof": 0.8, "scarcity": 0.6}
    gated = route_mechanism_scores_by_predicted_depth(
        scores=scores, page_profile=None,
    )
    for cialdini, original_score in scores.items():
        cat = _category_for_cialdini(cialdini)
        if cat == MechanismRouteCategory.VIGILANCE_ACTIVATING:
            assert gated[cialdini] == 0.0
        else:
            assert gated[cialdini] == original_score


def test_route_path_high_bandwidth_allows_vigilance():
    """High bandwidth → EVALUATED → vigilance mechanisms compete on
    their original scores."""
    page = SimpleNamespace(
        cognitive_load=0.3,
        remaining_bandwidth=0.85,
        attention_competition=0.2,
        processing_mode="",
    )
    scores = {"social_proof": 0.8, "scarcity": 0.6, "authority": 0.5}
    gated = route_mechanism_scores_by_predicted_depth(
        scores=scores, page_profile=page,
    )
    # All scores preserved (no zeroing)
    assert gated == scores


def test_route_path_extraction_failure_passes_through():
    """If page_profile lacks the expected attributes, extraction soft-
    fails to None and the predictor falls through to modal PERIPHERAL.
    Test pins that the cascade doesn't crash on a malformed profile."""
    bad_profile = object()  # has no attributes
    scores = {"social_proof": 0.7}
    gated = route_mechanism_scores_by_predicted_depth(
        scores=scores, page_profile=bad_profile,
    )
    # Cascade still gets a usable scores dict
    assert "social_proof" in gated
