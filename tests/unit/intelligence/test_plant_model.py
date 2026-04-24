"""Unit tests for PlantModel."""

from __future__ import annotations

import math

import pytest

from adam.core.learning.effect_size_correction import (
    CLT_MATCHING_EFFECT,
    CorrectionMethod,
    PublicationBiasCorrectedEffect,
)
from adam.intelligence.recommendation_class import (
    AudienceScope,
    AudienceSummary,
    DEFAULT_CONVERSION_RATE_BIN_EDGES,
    DEFAULT_INDUSTRY_PRIOR_RATE,
    PlantModel,
    PlantModelInputs,
    PrimingCondition,
    RecommendationClassIdentity,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


def _identity() -> RecommendationClassIdentity:
    return RecommendationClassIdentity(
        advertiser_id="luxy_ride",
        archetype_id="status_seeker",
        mechanism="regulatory_fit",
        context_posture_band="autopilot_high",
        horizon_band="short",
    )


def _scope() -> AudienceScope:
    return AudienceScope(
        advertiser_id="luxy_ride",
        archetype_id="status_seeker",
        vertical="luxury_transportation",
        context_posture_band="autopilot_high",
        horizon_band="short",
    )


def _priming() -> PrimingCondition:
    return PrimingCondition(
        page_activation_vector=[0.5] * 20,
        ad_mechanism="regulatory_fit",
        attentional_posture=-0.3,
        attentional_posture_confidence=0.6,
        register_match=0.7,
    )


def _summary(obs: int = 40) -> AudienceSummary:
    return AudienceSummary(
        observation_count=obs,
        coverage_estimate=0.8,
        expected_signal_strength=0.6,
    )


def _inputs(
    construct_effect: object = None,
    posture_band: str = "autopilot_high",
    obs: int = 40,
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
    return PlantModelInputs(
        identity=identity,
        audience_scope=scope,
        priming_condition=_priming(),
        audience_summary=_summary(obs),
        construct_effect=construct_effect,
    )


# -----------------------------------------------------------------------------
# Construction / configuration validation
# -----------------------------------------------------------------------------


class TestConstruction:
    def test_defaults_accepted(self):
        PlantModel()

    def test_invalid_industry_rate_rejected(self):
        with pytest.raises(ValueError, match="industry_prior_rate"):
            PlantModel(industry_prior_rate=0.0)
        with pytest.raises(ValueError, match="industry_prior_rate"):
            PlantModel(industry_prior_rate=1.0)

    def test_nonpositive_concentration_rejected(self):
        with pytest.raises(ValueError, match="industry_prior_concentration"):
            PlantModel(industry_prior_concentration=0.0)

    def test_bad_bin_edges_rejected(self):
        with pytest.raises(ValueError, match="bin_edges"):
            PlantModel(bin_edges=(0.5,))
        with pytest.raises(ValueError, match="strictly increasing"):
            PlantModel(bin_edges=(0.0, 0.2, 0.2, 1.0))
        with pytest.raises(ValueError, match="strictly increasing"):
            PlantModel(bin_edges=(0.0, 0.5, 0.3, 1.0))


# -----------------------------------------------------------------------------
# project() core behavior
# -----------------------------------------------------------------------------


class TestProject:
    def test_project_returns_validated_impact(self):
        model = PlantModel()
        projected = model.project(_inputs())
        projected.validate()
        assert projected.content_hash is not None

    def test_spies_weights_sum_to_one(self):
        model = PlantModel()
        projected = model.project(_inputs())
        total = sum(projected.goal_fulfillment_outcome.projected_distribution.bin_weights)
        assert math.isclose(total, 1.0, abs_tol=1e-6)

    def test_spies_bin_edges_match_plant_configuration(self):
        model = PlantModel()
        projected = model.project(_inputs())
        assert (
            projected.goal_fulfillment_outcome.projected_distribution.bin_edges
            == list(DEFAULT_CONVERSION_RATE_BIN_EDGES)
        )

    def test_implied_rate_matches_industry_when_no_effect(self):
        model = PlantModel()
        rate = model.implied_rate(_inputs(construct_effect=None, obs=0))
        assert math.isclose(rate, DEFAULT_INDUSTRY_PRIOR_RATE, abs_tol=1e-9)

    def test_implied_rate_shifts_up_with_positive_effect(self):
        model = PlantModel()
        base_rate = model.implied_rate(_inputs(construct_effect=None, obs=40))
        with_effect = model.implied_rate(_inputs(CLT_MATCHING_EFFECT, obs=40))
        assert with_effect > base_rate

    def test_implied_rate_stays_in_valid_range(self):
        """Very large positive AND very large negative d should land
        the implied rate in [0, 1], not over/underflow."""
        model = PlantModel()
        big_positive = PublicationBiasCorrectedEffect(
            construct_name="test_large_pos",
            published_g=10.0,
            corrected_d=5.0,
            correction_method=CorrectionMethod.SCHIMMACK_RATIO,
        )
        big_negative = PublicationBiasCorrectedEffect(
            construct_name="test_large_neg",
            published_g=-10.0,
            corrected_d=-5.0,
            correction_method=CorrectionMethod.SCHIMMACK_RATIO,
        )
        for effect in (big_positive, big_negative):
            rate = model.implied_rate(_inputs(effect, obs=40))
            assert 0.0 <= rate <= 1.0

    def test_implied_rate_is_reasonable_for_conversion_scale(self):
        """CLT effect (d=0.276) on 2% baseline should land in the
        advertising-conversion-rate range, not the signal-detection
        50%-ish range. This is the regression test for the log-odds
        shift fix applied on 2026-04-25.
        """
        model = PlantModel()
        rate = model.implied_rate(_inputs(CLT_MATCHING_EFFECT, obs=40))
        assert 0.005 < rate < 0.10, (
            f"implied rate {rate:.4f} outside realistic conversion range "
            "for a 2% baseline × d=0.276 construct shift; check log-odds "
            "interpretation in _posterior_parameters"
        )


# -----------------------------------------------------------------------------
# Determinism
# -----------------------------------------------------------------------------


class TestDeterminism:
    def test_same_inputs_same_content_hash(self):
        model = PlantModel()
        a = model.project(_inputs(CLT_MATCHING_EFFECT))
        b = model.project(_inputs(CLT_MATCHING_EFFECT))
        assert a.content_hash == b.content_hash
        assert a.claim_id == b.claim_id

    def test_different_observation_count_changes_hash(self):
        model = PlantModel()
        a = model.project(_inputs(CLT_MATCHING_EFFECT, obs=20))
        b = model.project(_inputs(CLT_MATCHING_EFFECT, obs=100))
        assert a.content_hash != b.content_hash

    def test_different_industry_rate_changes_hash(self):
        a = PlantModel(industry_prior_rate=0.02).project(_inputs(CLT_MATCHING_EFFECT))
        b = PlantModel(industry_prior_rate=0.05).project(_inputs(CLT_MATCHING_EFFECT))
        assert a.content_hash != b.content_hash


# -----------------------------------------------------------------------------
# Posture → route split
# -----------------------------------------------------------------------------


class TestRouteSplit:
    @pytest.mark.parametrize("band,expected_higher", [
        ("autopilot_high", "autopilot"),
        ("autopilot_low",  "autopilot"),
        ("vigilance_low",  "attention"),
        ("vigilance_high", "attention"),
    ])
    def test_posture_band_sets_dominant_route(self, band, expected_higher):
        model = PlantModel()
        projected = model.project(_inputs(posture_band=band))
        gfo = projected.goal_fulfillment_outcome
        if expected_higher == "autopilot":
            assert gfo.autopilot_route_fraction > gfo.attention_route_fraction
        else:
            assert gfo.attention_route_fraction > gfo.autopilot_route_fraction

    def test_unknown_band_rejected(self):
        model = PlantModel()
        bad = _inputs()
        # Force an invalid band on the identity only
        with pytest.raises(ValueError):
            model.project(
                PlantModelInputs(
                    identity=RecommendationClassIdentity(
                        advertiser_id="x", archetype_id="y", mechanism="z",
                        context_posture_band="nonsense", horizon_band="short",
                    ),
                    audience_scope=bad.audience_scope,
                    priming_condition=bad.priming_condition,
                    audience_summary=bad.audience_summary,
                    construct_effect=None,
                )
            )

    def test_route_fractions_sum_within_budget(self):
        model = PlantModel()
        for band in (
            "autopilot_high", "autopilot_low", "neutral",
            "vigilance_low", "vigilance_high",
        ):
            projected = model.project(_inputs(posture_band=band))
            gfo = projected.goal_fulfillment_outcome
            assert gfo.autopilot_route_fraction + gfo.attention_route_fraction <= 1.0 + 1e-9


# -----------------------------------------------------------------------------
# Bias-flag population
# -----------------------------------------------------------------------------


class TestBiasFlags:
    def test_winners_curse_always_true_pilot(self):
        """Single-level shrinkage is the A14 compromise — flag is True
        for every projection until the #8 hierarchy ships."""
        model = PlantModel()
        for effect in (None, CLT_MATCHING_EFFECT):
            projected = model.project(_inputs(effect))
            assert projected.competing_activations.winners_curse_portion is True

    def test_attention_residual_always_true_pilot(self):
        model = PlantModel()
        projected = model.project(_inputs())
        assert projected.competing_activations.attention_route_residual is True

    def test_counter_regulation_always_true_pilot(self):
        model = PlantModel()
        projected = model.project(_inputs())
        assert projected.competing_activations.counter_regulation_untracked is True

    def test_pub_bias_false_when_pre_registered(self):
        model = PlantModel()
        projected = model.project(_inputs(CLT_MATCHING_EFFECT))
        assert projected.competing_activations.publication_bias_residual is False

    def test_pub_bias_true_when_no_construct_effect(self):
        model = PlantModel()
        projected = model.project(_inputs(None))
        assert projected.competing_activations.publication_bias_residual is True

    def test_pub_bias_true_when_non_pre_registered_correction(self):
        robma_effect = PublicationBiasCorrectedEffect(
            construct_name="example_construct",
            published_g=0.5,
            corrected_d=0.25,
            correction_method=CorrectionMethod.ROBMA_MEDIAN,
        )
        model = PlantModel()
        projected = model.project(_inputs(robma_effect))
        assert projected.competing_activations.publication_bias_residual is True


# -----------------------------------------------------------------------------
# Input validation
# -----------------------------------------------------------------------------


class TestInputValidation:
    def test_archetype_mismatch_rejected(self):
        model = PlantModel()
        inputs = _inputs()
        bad = PlantModelInputs(
            identity=inputs.identity,
            audience_scope=AudienceScope(
                advertiser_id="luxy_ride",
                archetype_id="different_archetype",
                vertical="luxury_transportation",
                context_posture_band="autopilot_high",
                horizon_band="short",
            ),
            priming_condition=inputs.priming_condition,
            audience_summary=inputs.audience_summary,
            construct_effect=None,
        )
        with pytest.raises(ValueError, match="archetype_id"):
            model.project(bad)

    def test_nonpositive_horizon_rejected(self):
        model = PlantModel()
        inputs = _inputs()
        bad = PlantModelInputs(
            identity=inputs.identity,
            audience_scope=inputs.audience_scope,
            priming_condition=inputs.priming_condition,
            audience_summary=inputs.audience_summary,
            construct_effect=None,
            horizon_days=0,
        )
        with pytest.raises(ValueError, match="horizon_days"):
            model.project(bad)


# -----------------------------------------------------------------------------
# SPIES binning
# -----------------------------------------------------------------------------


class TestSpiesBinning:
    def test_bin_weights_nonnegative(self):
        model = PlantModel()
        projected = model.project(_inputs(CLT_MATCHING_EFFECT))
        for w in projected.goal_fulfillment_outcome.projected_distribution.bin_weights:
            assert w >= 0.0

    def test_bin_weights_concentrate_around_posterior_mean(self):
        """The bin containing the posterior mean, together with its
        neighbors, should carry the majority of the weight. Strict
        "mean bin is max" is not guaranteed for right-skewed Beta
        posteriors crossing narrow left-tail bins, so we check that
        the mean bin + immediate neighbors dominate."""
        model = PlantModel()
        inputs = _inputs(CLT_MATCHING_EFFECT, obs=200)
        projected = model.project(inputs)
        rate = model.implied_rate(inputs)
        dist = projected.goal_fulfillment_outcome.projected_distribution
        mean_bin = None
        for i in range(len(dist.bin_edges) - 1):
            if dist.bin_edges[i] <= rate < dist.bin_edges[i + 1]:
                mean_bin = i
                break
        assert mean_bin is not None
        neighbor_start = max(0, mean_bin - 1)
        neighbor_end = min(len(dist.bin_weights), mean_bin + 2)
        neighbor_mass = sum(dist.bin_weights[neighbor_start:neighbor_end])
        assert neighbor_mass > 0.5, (
            f"mean bin + neighbors carry only {neighbor_mass:.2f}; "
            "expected > 0.5"
        )
