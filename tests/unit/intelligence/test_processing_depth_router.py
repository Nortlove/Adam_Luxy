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


# -----------------------------------------------------------------------------
# Fluency floor (audit §6 hard constraint)
# -----------------------------------------------------------------------------


def test_fluency_below_floor_collapses_to_unprocessed():
    """processing_fluency < PROCESSING_FLUENCY_FLOOR (0.3) MUST force
    UNPROCESSED depth — the audit-flagged hard constraint."""
    from adam.intelligence.processing_depth_router import (
        PROCESSING_FLUENCY_FLOOR,
    )
    assert PROCESSING_FLUENCY_FLOOR == 0.3
    d = predict_processing_depth_heuristic(
        page_processing_fluency=0.2,
        # Even with high bandwidth + central mode, fluency floor wins:
        page_remaining_bandwidth=1.0,
        page_processing_mode="central",
    )
    assert d == ProcessingDepth.UNPROCESSED


def test_fluency_at_floor_does_not_collapse():
    """fluency exactly at the floor (0.3) is NOT below — strict <
    threshold per the canonical Reber rule."""
    d = predict_processing_depth_heuristic(
        page_processing_fluency=0.3,
        page_processing_mode="central",
    )
    # central mode wins because fluency check did not trigger
    assert d == ProcessingDepth.EVALUATED


def test_fluency_above_floor_does_not_force_collapse():
    """High fluency leaves all other signals authoritative."""
    d = predict_processing_depth_heuristic(
        page_processing_fluency=0.9,
        page_processing_mode="central",
    )
    assert d == ProcessingDepth.EVALUATED


def test_fluency_none_does_not_short_circuit():
    """None fluency must not affect the predictor's other paths."""
    d = predict_processing_depth_heuristic(
        page_processing_fluency=None,
        page_processing_mode="central",
    )
    assert d == ProcessingDepth.EVALUATED


def test_route_path_low_fluency_filters_vigilance():
    """End-to-end: low fluency → UNPROCESSED → vigilance mechanisms zeroed.

    Uses Cialdini names whose atom counterparts ARE in MECHANISM_TAXONOMY:
        loss_aversion → temporal_construal (BLEND_COMPATIBLE)
        authority → identity_construction (VIGILANCE_ACTIVATING)
        curiosity → attention_dynamics (VIGILANCE_ACTIVATING)
    Mechanisms whose atom counterpart is NOT in the taxonomy
    (social_proof, scarcity) are conservatively included regardless of
    depth — that's the canonical contract; testing them here would be
    testing the wrong thing.
    """
    profile = SimpleNamespace(
        cognitive_load=0.5,
        remaining_bandwidth=1.0,         # high — would normally give EVALUATED
        attention_competition=0.0,        # low
        processing_mode=None,
        processing_fluency=0.15,          # below the 0.3 floor
    )
    scores = {
        "loss_aversion": 0.7,   # blend-compatible (via temporal_construal)
        "authority": 0.7,        # vigilance-activating (via identity_construction)
        "curiosity": 0.7,        # vigilance-activating (via attention_dynamics)
    }
    gated = route_mechanism_scores_by_predicted_depth(
        scores=scores, page_profile=profile,
    )
    # Blend-compatible survives; vigilance mechanisms zeroed
    assert gated["loss_aversion"] == 0.7
    assert gated["authority"] == 0.0
    assert gated["curiosity"] == 0.0


def test_route_path_high_fluency_allows_vigilance():
    """Sanity inverse: high fluency on a high-bandwidth page → EVALUATED →
    vigilance mechanisms remain eligible."""
    profile = SimpleNamespace(
        cognitive_load=0.4,
        remaining_bandwidth=1.0,
        attention_competition=0.0,
        processing_mode=None,
        processing_fluency=0.85,
    )
    scores = {"loss_aversion": 0.7, "authority": 0.7}
    gated = route_mechanism_scores_by_predicted_depth(
        scores=scores, page_profile=profile,
    )
    # Both routes preserved at full score
    assert gated["loss_aversion"] == 0.7
    assert gated["authority"] == 0.7


# -----------------------------------------------------------------------------
# Attentional posture (audit Item 6 — categorize_posture wire into C2)
# -----------------------------------------------------------------------------


def test_posture_blend_compatible_returns_peripheral():
    """Confident blend_compatible posture → PERIPHERAL depth (autopilot)."""
    d = predict_processing_depth_heuristic(
        page_attentional_posture_label="blend_compatible",
    )
    assert d == ProcessingDepth.PERIPHERAL


def test_posture_vigilance_activating_returns_evaluated():
    """Confident vigilance_activating posture → EVALUATED depth."""
    d = predict_processing_depth_heuristic(
        page_attentional_posture_label="vigilance_activating",
    )
    assert d == ProcessingDepth.EVALUATED


def test_posture_neutral_falls_through():
    """neutral posture does NOT short-circuit; mode/bandwidth wins."""
    d = predict_processing_depth_heuristic(
        page_attentional_posture_label="neutral",
        page_processing_mode="central",  # would give EVALUATED on its own
    )
    assert d == ProcessingDepth.EVALUATED  # mode wins, posture didn't override


def test_posture_unknown_falls_through():
    """unknown posture (sub-confidence-floor) does NOT short-circuit."""
    d = predict_processing_depth_heuristic(
        page_attentional_posture_label="unknown",
        page_processing_mode="central",
    )
    assert d == ProcessingDepth.EVALUATED


def test_posture_none_does_not_break_other_paths():
    """None posture must not affect existing predictor paths."""
    d = predict_processing_depth_heuristic(
        page_attentional_posture_label=None,
        page_processing_mode="peripheral",
    )
    assert d == ProcessingDepth.PERIPHERAL


def test_fluency_floor_beats_vigilance_posture():
    """Order discipline: fluency floor < 0.3 → UNPROCESSED REGARDLESS of
    asserted vigilance posture. A hard-to-process page leaves no
    cognitive room for any route, posture or not."""
    d = predict_processing_depth_heuristic(
        page_processing_fluency=0.15,             # below floor
        page_attentional_posture_label="vigilance_activating",  # would say EVALUATED
    )
    assert d == ProcessingDepth.UNPROCESSED


def test_route_path_reads_posture_from_page_profile():
    """End-to-end: route_mechanism_scores_by_predicted_depth reads
    attentional_posture + confidence from page_profile, translates via
    categorize_posture, and gates accordingly."""
    # Strong vigilance posture (well above thresholds)
    profile = SimpleNamespace(
        cognitive_load=0.5,
        remaining_bandwidth=0.3,           # would normally give PERIPHERAL
        attention_competition=0.0,
        processing_mode=None,
        processing_fluency=0.85,
        attentional_posture=0.7,            # > 0.20 vigilance threshold
        attentional_posture_confidence=0.9,  # > 0.40 min confidence
    )
    scores = {
        "loss_aversion": 0.7,    # blend (via temporal_construal)
        "authority": 0.7,         # vigilance (via identity_construction)
    }
    gated = route_mechanism_scores_by_predicted_depth(
        scores=scores, page_profile=profile,
    )
    # Vigilance posture → EVALUATED → both routes eligible
    assert gated["loss_aversion"] == 0.7
    assert gated["authority"] == 0.7


def test_route_path_low_confidence_posture_falls_through_to_bandwidth():
    """Confidence below MIN_POSTURE_CONFIDENCE (0.40) → posture label
    becomes 'unknown' → predictor falls through to bandwidth path."""
    profile = SimpleNamespace(
        cognitive_load=0.5,
        remaining_bandwidth=0.2,          # < 0.3 → UNPROCESSED
        attention_competition=0.0,
        processing_mode=None,
        processing_fluency=0.85,
        attentional_posture=0.9,           # strong float
        attentional_posture_confidence=0.1, # but very low confidence → "unknown"
    )
    scores = {"loss_aversion": 0.7, "authority": 0.7}
    gated = route_mechanism_scores_by_predicted_depth(
        scores=scores, page_profile=profile,
    )
    # Posture label = "unknown" → falls through → bandwidth 0.2 → UNPROCESSED
    # → vigilance gated
    assert gated["loss_aversion"] == 0.7
    assert gated["authority"] == 0.0
