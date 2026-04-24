"""Unit tests for ArticleObservation's Claude-scored feature fields.

The existing ArticleObservation validator covers url / title /
construct_vector / exposure_context_confidence / attentional_posture.
This file covers only the five new feature fields added for the
#7 MV slice (register, primary_metaphor, goal_activation,
temporal_horizon, processing_fluency).
"""

from __future__ import annotations

import pytest

from adam.intelligence.pages.entity_graph import (
    ArticleObservation,
    PublicationUpsert,
)


def _base_observation(**overrides) -> ArticleObservation:
    defaults = dict(
        url="https://example.com/article-1",
        title="Example article",
        publication=PublicationUpsert(
            name="Example Daily",
            canonical_domain="example.com",
        ),
    )
    defaults.update(overrides)
    return ArticleObservation(**defaults)


class TestRegisterFields:
    def test_none_register_fields_pass(self):
        _base_observation().validate()

    def test_valid_register_score_passes(self):
        _base_observation(register_score=0.5).validate()

    def test_register_score_out_of_upper_bound_rejected(self):
        with pytest.raises(ValueError, match="register_score"):
            _base_observation(register_score=1.2).validate()

    def test_register_score_out_of_lower_bound_rejected(self):
        with pytest.raises(ValueError, match="register_score"):
            _base_observation(register_score=-1.2).validate()

    def test_register_confidence_out_of_range_rejected(self):
        with pytest.raises(ValueError, match="register_confidence"):
            _base_observation(register_confidence=1.5).validate()


class TestPrimaryMetaphorFields:
    def test_none_metaphor_fields_pass(self):
        _base_observation().validate()

    def test_valid_metaphor_axes_passes(self):
        _base_observation(
            primary_metaphor_density=0.4,
            primary_metaphor_axes_scored=[0.1] * 8,
            primary_metaphor_confidence=0.7,
        ).validate()

    def test_metaphor_axes_wrong_length_rejected(self):
        with pytest.raises(ValueError, match="primary_metaphor_axes_scored length"):
            _base_observation(
                primary_metaphor_axes_scored=[0.1] * 6,
            ).validate()

    def test_metaphor_axes_out_of_range_rejected(self):
        axes = [0.1] * 8
        axes[3] = 1.5
        with pytest.raises(ValueError, match=r"primary_metaphor_axes_scored\[3\]"):
            _base_observation(primary_metaphor_axes_scored=axes).validate()

    def test_metaphor_density_out_of_range_rejected(self):
        with pytest.raises(ValueError, match="primary_metaphor_density"):
            _base_observation(primary_metaphor_density=1.2).validate()


class TestGoalActivationFields:
    def test_none_goal_fields_pass(self):
        _base_observation().validate()

    def test_valid_goal_profile_passes(self):
        _base_observation(
            goal_activation_profile={
                "affiliation_safety": 0.3,
                "threat_reduction": 0.7,
            },
            goal_activation_confidence=0.6,
        ).validate()

    def test_goal_value_out_of_range_rejected(self):
        with pytest.raises(ValueError, match=r"goal_activation_profile\[affiliation_safety\]"):
            _base_observation(
                goal_activation_profile={"affiliation_safety": 1.2},
            ).validate()

    def test_goal_confidence_out_of_range_rejected(self):
        with pytest.raises(ValueError, match="goal_activation_confidence"):
            _base_observation(goal_activation_confidence=-0.1).validate()


class TestTemporalHorizonFields:
    def test_valid_horizon_passes(self):
        _base_observation(
            temporal_horizon_induction=-0.4,
            temporal_horizon_confidence=0.8,
        ).validate()

    def test_horizon_below_minus_one_rejected(self):
        with pytest.raises(ValueError, match="temporal_horizon_induction"):
            _base_observation(temporal_horizon_induction=-1.1).validate()

    def test_horizon_confidence_out_of_range_rejected(self):
        with pytest.raises(ValueError, match="temporal_horizon_confidence"):
            _base_observation(temporal_horizon_confidence=2.0).validate()


class TestProcessingFluencyFields:
    def test_valid_fluency_passes(self):
        _base_observation(
            processing_fluency=0.7,
            processing_fluency_confidence=0.5,
        ).validate()

    def test_fluency_out_of_range_rejected(self):
        with pytest.raises(ValueError, match="processing_fluency "):
            _base_observation(processing_fluency=1.2).validate()

    def test_fluency_confidence_out_of_range_rejected(self):
        with pytest.raises(ValueError, match="processing_fluency_confidence"):
            _base_observation(processing_fluency_confidence=-0.5).validate()


class TestAllFeaturesTogether:
    def test_fully_populated_observation_passes(self):
        _base_observation(
            register_score=0.3,
            register_category="editorial",
            register_confidence=0.7,
            primary_metaphor_density=0.4,
            primary_metaphor_axes_scored=[0.2] * 8,
            primary_metaphor_confidence=0.6,
            goal_activation_profile={
                "affiliation_safety": 0.3,
                "social_alignment": 0.4,
                "threat_reduction": 0.2,
                "competence_verification": 0.1,
                "status_signaling": 0.3,
                "novelty_exploration": 0.5,
                "planning_completion": 0.4,
                "indulgence_permission": 0.2,
            },
            goal_activation_confidence=0.8,
            temporal_horizon_induction=0.4,
            temporal_horizon_confidence=0.7,
            processing_fluency=0.8,
            processing_fluency_confidence=0.9,
        ).validate()
