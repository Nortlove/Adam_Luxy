"""Unit tests for blend_fit — creative ↔ page alignment primitive."""

from __future__ import annotations

import math
from typing import Any, Dict

import pytest

from adam.intelligence.blend_fit import (
    BlendFitDecomposition,
    CreativeFeatureBundle,
    compute_blend_fit,
)
from adam.intelligence.pages.claude_feature_scoring import (
    GOAL_ACTIVATION_KEYS,
    PRIMARY_METAPHOR_AXIS_NAMES,
    PageFeatureBundle,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


def _page(**overrides) -> PageFeatureBundle:
    defaults: Dict[str, Any] = dict(
        register_score=0.3,
        register_category="journalistic",
        register_confidence=0.8,
        primary_metaphor_density=0.4,
        primary_metaphor_axes=[0.5] * 8,
        primary_metaphor_confidence=0.7,
        goal_activation_profile={k: 0.2 for k in GOAL_ACTIVATION_KEYS},
        goal_activation_confidence=0.6,
        temporal_horizon_induction=-0.2,
        temporal_horizon_confidence=0.7,
        processing_fluency=0.7,
        processing_fluency_confidence=0.8,
    )
    defaults.update(overrides)
    return PageFeatureBundle(**defaults)


def _creative(**overrides) -> CreativeFeatureBundle:
    defaults: Dict[str, Any] = dict(
        register_score=0.3,
        register_category="journalistic",
        register_confidence=0.8,
        primary_metaphor_density=0.4,
        primary_metaphor_axes=[0.5] * 8,
        primary_metaphor_confidence=0.7,
        goal_fulfillment_profile={k: 0.2 for k in GOAL_ACTIVATION_KEYS},
        goal_fulfillment_confidence=0.6,
        temporal_horizon_induction=-0.2,
        temporal_horizon_confidence=0.7,
        processing_fluency=0.7,
        processing_fluency_confidence=0.8,
        attentional_posture=-0.3,
        attentional_posture_confidence=0.5,
    )
    defaults.update(overrides)
    return CreativeFeatureBundle(**defaults)


# -----------------------------------------------------------------------------
# CreativeFeatureBundle validation
# -----------------------------------------------------------------------------


class TestCreativeBundleValidation:
    def test_valid_bundle_passes(self):
        _creative().validate()

    def test_register_category_must_be_known(self):
        with pytest.raises(ValueError, match="register_category"):
            _creative(register_category="surrealist").validate()

    def test_metaphor_axes_length_enforced(self):
        with pytest.raises(ValueError, match="primary_metaphor_axes length"):
            _creative(primary_metaphor_axes=[0.5] * 6).validate()

    def test_posture_out_of_range_rejected(self):
        with pytest.raises(ValueError, match="attentional_posture"):
            _creative(attentional_posture=1.5).validate()

    def test_goal_key_mismatch_rejected(self):
        bad = {k: 0.1 for k in GOAL_ACTIVATION_KEYS[:-1]}
        with pytest.raises(ValueError, match="goal_fulfillment_profile keys"):
            _creative(goal_fulfillment_profile=bad).validate()


# -----------------------------------------------------------------------------
# compute_blend_fit — identity case
# -----------------------------------------------------------------------------


class TestBlendFitIdentity:
    def test_identical_features_yield_high_blend_fit(self):
        """When creative's feature profile matches the page exactly, blend_fit
        should be near 1.0."""
        page = _page()
        creative = _creative()
        score, decomp = compute_blend_fit(creative, page)
        # Score is weighted alignment; posture axis has weight 0 because
        # PageFeatureBundle doesn't carry attentional_posture. Expect
        # alignment on other axes ≈ 1; aggregate ≈ 1.
        assert score > 0.95

    def test_decomposition_sums_to_score(self):
        page = _page()
        creative = _creative()
        score, decomp = compute_blend_fit(creative, page)
        total_contribution = sum(decomp.per_axis_contribution.values())
        assert math.isclose(total_contribution, score, abs_tol=1e-6)


# -----------------------------------------------------------------------------
# compute_blend_fit — directional tests
# -----------------------------------------------------------------------------


class TestBlendFitDirectionality:
    def test_opposite_register_lowers_blend_fit(self):
        page = _page(register_score=1.0)  # very formal
        creative = _creative(register_score=-1.0)  # very informal
        baseline_score, _ = compute_blend_fit(_creative(), _page())
        score, _ = compute_blend_fit(creative, page)
        assert score < baseline_score

    def test_opposite_temporal_horizon_lowers_blend_fit(self):
        page = _page(temporal_horizon_induction=-1.0)
        creative = _creative(temporal_horizon_induction=1.0)
        baseline_score, _ = compute_blend_fit(_creative(), _page())
        score, _ = compute_blend_fit(creative, page)
        assert score < baseline_score

    def test_goal_fulfillment_matching_activation_yields_high_goal_alignment(self):
        # Page activates affiliation_safety strongly; creative fulfills
        # it strongly. Goal alignment on that axis should be high.
        page = _page(
            goal_activation_profile={
                **{k: 0.0 for k in GOAL_ACTIVATION_KEYS},
                "affiliation_safety": 0.9,
            },
        )
        creative = _creative(
            goal_fulfillment_profile={
                **{k: 0.0 for k in GOAL_ACTIVATION_KEYS},
                "affiliation_safety": 0.9,
            },
        )
        _, decomp = compute_blend_fit(creative, page)
        assert decomp.per_axis_alignment["goal"] >= 0.95

    def test_goal_fulfillment_missing_activated_goal_lowers_alignment(self):
        page = _page(
            goal_activation_profile={
                **{k: 0.0 for k in GOAL_ACTIVATION_KEYS},
                "threat_reduction": 0.9,
            },
        )
        creative = _creative(
            goal_fulfillment_profile={
                **{k: 0.0 for k in GOAL_ACTIVATION_KEYS},
                "status_signaling": 0.9,  # different goal
            },
        )
        _, decomp = compute_blend_fit(creative, page)
        # Creative addresses a goal the page didn't activate → zero overlap.
        assert decomp.per_axis_alignment["goal"] <= 0.05


# -----------------------------------------------------------------------------
# compute_blend_fit — confidence gating
# -----------------------------------------------------------------------------


class TestBlendFitConfidenceGating:
    def test_zero_register_confidence_drops_register_weight(self):
        page = _page(register_confidence=0.0)
        creative = _creative()
        _, decomp = compute_blend_fit(creative, page)
        assert decomp.per_axis_weight["register"] == 0.0

    def test_all_zero_confidences_yields_neutral_fallback(self):
        """When every axis has zero confidence on one side, the primitive
        returns 0.5 (no-information honesty) rather than 0 or 1."""
        page = _page(
            register_confidence=0.0,
            primary_metaphor_confidence=0.0,
            goal_activation_confidence=0.0,
            temporal_horizon_confidence=0.0,
            processing_fluency_confidence=0.0,
        )
        creative = _creative()
        score, decomp = compute_blend_fit(creative, page)
        assert score == 0.5
        assert decomp.total_effective_weight == 0.0


# -----------------------------------------------------------------------------
# BlendFitDecomposition shape
# -----------------------------------------------------------------------------


class TestDecomposition:
    def test_all_six_axes_present_in_decomposition(self):
        _, decomp = compute_blend_fit(_creative(), _page())
        expected_axes = {
            "register", "metaphor", "goal", "horizon", "fluency", "posture",
        }
        assert set(decomp.per_axis_alignment.keys()) == expected_axes
        assert set(decomp.per_axis_weight.keys()) == expected_axes
        assert set(decomp.per_axis_contribution.keys()) == expected_axes

    def test_posture_weight_zero_when_page_has_no_posture(self):
        _, decomp = compute_blend_fit(_creative(), _page())
        # PageFeatureBundle does not carry attentional_posture — posture
        # axis contributes 0 weight.
        assert decomp.per_axis_weight["posture"] == 0.0


# -----------------------------------------------------------------------------
# A14 registry integration
# -----------------------------------------------------------------------------


class TestA14Registration:
    def test_blend_fit_weights_flagged_in_registry(self):
        from adam.intelligence.recommendation_class import (
            ACTIVE_COMPROMISES,
            BLEND_FIT_WEIGHTS_UNVALIDATED,
        )
        assert BLEND_FIT_WEIGHTS_UNVALIDATED in ACTIVE_COMPROMISES

    def test_blend_fit_retirement_trigger_names_calibration(self):
        from adam.intelligence.recommendation_class import (
            BLEND_FIT_WEIGHTS_UNVALIDATED,
        )
        trigger = BLEND_FIT_WEIGHTS_UNVALIDATED.retirement_trigger.lower()
        assert "calibrat" in trigger
        assert "backfire" in trigger  # rule 11 guard
