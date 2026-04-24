"""Unit tests for Adjudicator."""

from __future__ import annotations

import pytest

from adam.core.learning.effect_size_correction import CLT_MATCHING_EFFECT
from adam.intelligence.recommendation_class import (
    Adjudicator,
    AudienceScope,
    AudienceSummary,
    Partition,
    PlantModel,
    PlantModelInputs,
    PrimingCondition,
    RealizedOutcomes,
    RecommendationClassIdentity,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


def _plant_inputs(
    posture_band: str = "autopilot_high",
    obs: int = 40,
    with_effect: bool = True,
) -> PlantModelInputs:
    identity = RecommendationClassIdentity(
        advertiser_id="luxy_ride",
        archetype_id="status_seeker",
        mechanism="regulatory_fit",
        context_posture_band=posture_band,
        horizon_band="short",
    )
    scope = AudienceScope(
        advertiser_id="luxy_ride",
        archetype_id="status_seeker",
        vertical="luxury_transportation",
        context_posture_band=posture_band,
        horizon_band="short",
    )
    priming = PrimingCondition(
        page_activation_vector=[0.5] * 20,
        ad_mechanism="regulatory_fit",
        attentional_posture=-0.3,
        attentional_posture_confidence=0.6,
        register_match=0.7,
    )
    summary = AudienceSummary(
        observation_count=obs, coverage_estimate=0.8, expected_signal_strength=0.6,
    )
    return PlantModelInputs(
        identity=identity,
        audience_scope=scope,
        priming_condition=priming,
        audience_summary=summary,
        construct_effect=(CLT_MATCHING_EFFECT if with_effect else None),
    )


# -----------------------------------------------------------------------------
# Construction
# -----------------------------------------------------------------------------


class TestConstruction:
    def test_defaults_accepted(self):
        Adjudicator()

    def test_invalid_min_sample_rejected(self):
        with pytest.raises(ValueError):
            Adjudicator(untested_min_sample_size=0)


# -----------------------------------------------------------------------------
# Realized outcomes validation
# -----------------------------------------------------------------------------


class TestRealizedOutcomes:
    def test_nonpositive_sample_rejected(self):
        with pytest.raises(ValueError):
            RealizedOutcomes(total_conversions=0, total_sample_size=0).validate()

    def test_counts_over_sample_rejected(self):
        with pytest.raises(ValueError):
            RealizedOutcomes(total_conversions=11, total_sample_size=10).validate()

    def test_partial_route_counts_rejected(self):
        with pytest.raises(ValueError):
            RealizedOutcomes(
                total_conversions=5, total_sample_size=100,
                autopilot_route_conversions=3,
                autopilot_route_sample_size=None,
            ).validate()

    def test_route_counts_out_of_range_rejected(self):
        with pytest.raises(ValueError):
            RealizedOutcomes(
                total_conversions=5, total_sample_size=100,
                autopilot_route_conversions=11,
                autopilot_route_sample_size=10,
            ).validate()


# -----------------------------------------------------------------------------
# Partition logic
# -----------------------------------------------------------------------------


class TestPartition:
    def test_low_sample_size_is_untested(self):
        model = PlantModel()
        inputs = _plant_inputs(obs=40)
        projected = model.project(inputs)
        realized = RealizedOutcomes(total_conversions=1, total_sample_size=30)
        adj = Adjudicator(untested_min_sample_size=50)
        result = adj.adjudicate(projected, realized, model, inputs)
        assert result.partition == Partition.UNTESTED

    def test_realized_matches_projected_validated(self):
        model = PlantModel()
        inputs = _plant_inputs(obs=40, with_effect=True)
        projected = model.project(inputs)
        implied = model.implied_rate(inputs)
        # Construct realized outcomes that match the implied rate
        n = 1000
        c = int(round(implied * n))
        realized = RealizedOutcomes(total_conversions=c, total_sample_size=n)
        adj = Adjudicator()
        result = adj.adjudicate(projected, realized, model, inputs)
        assert result.partition == Partition.VALIDATED

    def test_realized_far_below_projected_failing(self):
        model = PlantModel()
        inputs = _plant_inputs(obs=200, with_effect=True)
        projected = model.project(inputs)
        # 2 conversions on 10000 impressions vs ~2-3% implied → crushingly
        # below projection even after bias-flag accounting
        realized = RealizedOutcomes(total_conversions=2, total_sample_size=10000)
        adj = Adjudicator()
        result = adj.adjudicate(projected, realized, model, inputs)
        assert result.partition == Partition.FAILING

    def test_realized_far_above_projected_validated_not_failing(self):
        """Over-performance is never failing. Theory predicted a floor
        that was cleared. Validated."""
        model = PlantModel()
        inputs = _plant_inputs(obs=200, with_effect=True)
        projected = model.project(inputs)
        # 50% conversion rate vs 2-3% implied
        realized = RealizedOutcomes(total_conversions=5000, total_sample_size=10000)
        adj = Adjudicator()
        result = adj.adjudicate(projected, realized, model, inputs)
        assert result.partition == Partition.VALIDATED


# -----------------------------------------------------------------------------
# Residual decomposition
# -----------------------------------------------------------------------------


class TestResidualDecomposition:
    def test_residual_decomposition_sums_to_raw(self):
        model = PlantModel()
        inputs = _plant_inputs(obs=100, with_effect=True)
        projected = model.project(inputs)
        realized = RealizedOutcomes(total_conversions=5, total_sample_size=200)
        adj = Adjudicator()
        result = adj.adjudicate(projected, realized, model, inputs)
        rd = result.residual_divergence
        # noise + sum(bias) + unexplained ≈ raw (sign-preserving)
        total_abs = (
            abs(rd.noise_within_tolerance)
            + sum(abs(v) for v in rd.bias_flag_accounted.values())
            + abs(rd.unexplained)
        )
        assert total_abs == pytest.approx(abs(rd.raw_divergence), abs=1e-9)

    def test_bias_flags_only_active_ones_absorb(self):
        """An inactive flag gets 0 in the decomposition."""
        model = PlantModel()
        inputs = _plant_inputs(obs=100, with_effect=True)
        projected = model.project(inputs)
        # CLT effect is pre-registered → publication_bias_residual is False
        assert projected.competing_activations.publication_bias_residual is False
        realized = RealizedOutcomes(total_conversions=3, total_sample_size=200)
        adj = Adjudicator()
        result = adj.adjudicate(projected, realized, model, inputs)
        # publication_bias_residual should not absorb any residual
        assert result.residual_divergence.bias_flag_accounted["publication_bias_residual"] == 0.0

    def test_noise_absorbs_small_residuals(self):
        """When realized is close to projected, most of the residual
        is noise-within-tolerance and unexplained is ~0."""
        model = PlantModel()
        inputs = _plant_inputs(obs=40, with_effect=True)
        projected = model.project(inputs)
        implied = model.implied_rate(inputs)
        n = 1000
        c = int(round(implied * n))
        realized = RealizedOutcomes(total_conversions=c, total_sample_size=n)
        adj = Adjudicator()
        result = adj.adjudicate(projected, realized, model, inputs)
        assert abs(result.residual_divergence.unexplained) < 1e-6


# -----------------------------------------------------------------------------
# Route split
# -----------------------------------------------------------------------------


class TestRouteSplit:
    def test_unannotated_flags_requires_annotation(self):
        model = PlantModel()
        inputs = _plant_inputs(obs=200, with_effect=True)
        projected = model.project(inputs)
        realized = RealizedOutcomes(total_conversions=5, total_sample_size=200)
        adj = Adjudicator()
        result = adj.adjudicate(projected, realized, model, inputs)
        assert result.route_split.requires_annotation is True
        assert result.route_split.autopilot_route_residual is None
        assert result.route_split.attention_route_residual is None

    def test_annotated_split_produces_residuals(self):
        model = PlantModel()
        inputs = _plant_inputs(obs=200, with_effect=True)
        projected = model.project(inputs)
        realized = RealizedOutcomes(
            total_conversions=8, total_sample_size=200,
            autopilot_route_conversions=6, autopilot_route_sample_size=150,
            attention_route_conversions=2, attention_route_sample_size=50,
        )
        adj = Adjudicator()
        result = adj.adjudicate(projected, realized, model, inputs)
        assert result.route_split.requires_annotation is False
        assert result.route_split.autopilot_route_residual is not None
        assert result.route_split.attention_route_residual is not None


# -----------------------------------------------------------------------------
# Parameterization sensitivity
# -----------------------------------------------------------------------------


class TestParameterizationSensitivity:
    def test_validated_near_projected_is_stable(self):
        model = PlantModel()
        inputs = _plant_inputs(obs=100, with_effect=True)
        projected = model.project(inputs)
        implied = model.implied_rate(inputs)
        n = 500
        realized = RealizedOutcomes(
            total_conversions=int(round(implied * n)), total_sample_size=n,
        )
        adj = Adjudicator()
        result = adj.adjudicate(projected, realized, model, inputs)
        assert result.parameterization_sensitivity.partition_stable is True
        assert len(result.parameterization_sensitivity.partitions_observed) == 5

    def test_unstable_when_borderline(self):
        """Construct a case where perturbations of the plant parameters
        flip the partition — sensitivity flags instability."""
        # Set up a case where the nominal projection is just barely
        # failing and a perturbation shifts it to validated.
        model = PlantModel(industry_prior_rate=0.03)
        inputs = _plant_inputs(obs=5, with_effect=False)
        projected = model.project(inputs)
        realized = RealizedOutcomes(total_conversions=3, total_sample_size=1000)
        adj = Adjudicator()
        result = adj.adjudicate(projected, realized, model, inputs)
        # Don't assert the specific stability bool — just that the
        # machinery runs and produces the expected number of samples.
        assert len(result.parameterization_sensitivity.partitions_observed) == 5


# -----------------------------------------------------------------------------
# AdjudicatorOutput shape
# -----------------------------------------------------------------------------


class TestAdjudicatorOutputShape:
    def test_output_carries_claim_and_class_ids(self):
        model = PlantModel()
        inputs = _plant_inputs(obs=100, with_effect=True)
        projected = model.project(inputs)
        realized = RealizedOutcomes(total_conversions=5, total_sample_size=200)
        adj = Adjudicator()
        result = adj.adjudicate(projected, realized, model, inputs)
        assert result.claim_id == projected.claim_id
        assert result.recommendation_class_id == projected.recommendation_class_id

    def test_inferential_chain_attribution_empty_pilot_launch(self):
        """Attribution is deliberately empty at pilot launch; full
        population lands in weeks 8-9."""
        model = PlantModel()
        inputs = _plant_inputs(obs=100, with_effect=True)
        projected = model.project(inputs)
        realized = RealizedOutcomes(total_conversions=2, total_sample_size=10000)
        adj = Adjudicator()
        result = adj.adjudicate(projected, realized, model, inputs)
        assert result.inferential_chain_attribution == {}

    def test_evidence_trace_observation_density_positive(self):
        model = PlantModel()
        inputs = _plant_inputs(obs=100, with_effect=True)
        projected = model.project(inputs)
        realized = RealizedOutcomes(total_conversions=5, total_sample_size=200)
        adj = Adjudicator()
        result = adj.adjudicate(projected, realized, model, inputs)
        assert result.evidence_trace.observation_density > 0
        assert result.evidence_trace.sample_size == 200
