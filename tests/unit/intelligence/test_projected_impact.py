"""Unit tests for ProjectedImpact structured predicate data model.

Tests the invariants that make the predicate viable as a pre-registered claim:
- All sub-types reject invalid inputs with explicit ValueErrors
- SPIES distribution validates mass-sum, non-negativity, strict monotonic edges
- ProjectedImpact composes validation over all sub-types
- content_hash is deterministic and stable across metadata-only changes
- content_hash changes on any substantive mutation
- Frozen semantics prevent post-registration mutation
"""

from __future__ import annotations

import dataclasses
import pytest

from adam.intelligence.recommendation_class import (
    AudienceScope,
    AudienceSummary,
    CompetingActivations,
    GoalFulfillmentOutcome,
    PrimingCondition,
    ProjectedImpact,
    SpiesDistribution,
    canonical_hash,
)


# -----------------------------------------------------------------------------
# Fixtures — valid minimal instances of each sub-type
# -----------------------------------------------------------------------------

def _valid_spies() -> SpiesDistribution:
    return SpiesDistribution(
        metric_name="durable_conversion_rate",
        bin_edges=[0.0, 0.02, 0.05, 0.10, 1.0],
        bin_weights=[0.40, 0.35, 0.20, 0.05],
    )


def _valid_audience_scope() -> AudienceScope:
    return AudienceScope(
        advertiser_id="luxy_ride",
        archetype_id="status_seeker",
        vertical="luxury_transportation",
        context_posture_band="autopilot_low",
        horizon_band="short",
    )


def _valid_priming() -> PrimingCondition:
    return PrimingCondition(
        page_activation_vector=[0.5] * 20,
        ad_mechanism="regulatory_fit",
        attentional_posture=-0.3,
        attentional_posture_confidence=0.7,
        register_match=0.6,
    )


def _valid_outcome() -> GoalFulfillmentOutcome:
    return GoalFulfillmentOutcome(
        outcome_metric="durable_conversion_rate",
        projected_distribution=_valid_spies(),
        autopilot_route_fraction=0.7,
        attention_route_fraction=0.2,
    )


def _valid_competing() -> CompetingActivations:
    return CompetingActivations(
        counter_regulation_untracked=True,
        attention_route_residual=True,
        winners_curse_portion=True,
        publication_bias_residual=True,
        baseline_rate=0.01,
        notes="Pilot-phase flags; retirement triggers documented in pilot plan.",
    )


def _valid_summary() -> AudienceSummary:
    return AudienceSummary(
        observation_count=150,
        coverage_estimate=0.8,
        expected_signal_strength=0.6,
    )


def _valid_projected_impact() -> ProjectedImpact:
    return ProjectedImpact(
        claim_id="luxy_status_seeker_regfit_autopilot_low_short",
        recommendation_class_id="rc_luxy_status_seeker_regfit_autopilot_low_short",
        priming_condition=_valid_priming(),
        audience_scope=_valid_audience_scope(),
        goal_fulfillment_outcome=_valid_outcome(),
        competing_activations=_valid_competing(),
        audience_summary=_valid_summary(),
        horizon_days=14,
    )


# -----------------------------------------------------------------------------
# SpiesDistribution
# -----------------------------------------------------------------------------

class TestSpiesDistribution:
    def test_valid(self):
        _valid_spies().validate()

    def test_missing_metric_name(self):
        s = SpiesDistribution(metric_name="", bin_edges=[0.0, 1.0], bin_weights=[1.0])
        with pytest.raises(ValueError, match="metric_name"):
            s.validate()

    def test_too_few_edges(self):
        s = SpiesDistribution(metric_name="m", bin_edges=[0.0], bin_weights=[])
        with pytest.raises(ValueError, match="at least 2 bin_edges"):
            s.validate()

    def test_weights_length_mismatch(self):
        s = SpiesDistribution(
            metric_name="m", bin_edges=[0.0, 0.5, 1.0], bin_weights=[1.0],
        )
        with pytest.raises(ValueError, match="bin_weights length"):
            s.validate()

    def test_non_monotonic_edges(self):
        s = SpiesDistribution(
            metric_name="m", bin_edges=[0.0, 0.5, 0.3, 1.0],
            bin_weights=[0.25, 0.25, 0.50],
        )
        with pytest.raises(ValueError, match="strictly increasing"):
            s.validate()

    def test_negative_weights(self):
        s = SpiesDistribution(
            metric_name="m", bin_edges=[0.0, 0.5, 1.0], bin_weights=[-0.1, 1.1],
        )
        with pytest.raises(ValueError, match="non-negative"):
            s.validate()

    def test_weights_do_not_sum_to_one(self):
        s = SpiesDistribution(
            metric_name="m", bin_edges=[0.0, 0.5, 1.0], bin_weights=[0.3, 0.5],
        )
        with pytest.raises(ValueError, match="sum to 1.0"):
            s.validate()


# -----------------------------------------------------------------------------
# AudienceScope
# -----------------------------------------------------------------------------

class TestAudienceScope:
    def test_valid(self):
        _valid_audience_scope().validate()

    def test_empty_field_rejected(self):
        s = AudienceScope(
            advertiser_id="",
            archetype_id="a",
            vertical="v",
            context_posture_band="p",
            horizon_band="h",
        )
        with pytest.raises(ValueError, match="advertiser_id"):
            s.validate()


# -----------------------------------------------------------------------------
# PrimingCondition
# -----------------------------------------------------------------------------

class TestPrimingCondition:
    def test_valid(self):
        _valid_priming().validate()

    def test_wrong_vector_dims(self):
        p = PrimingCondition(
            page_activation_vector=[0.5] * 10,
            ad_mechanism="m",
            attentional_posture=0.0,
            attentional_posture_confidence=0.5,
        )
        with pytest.raises(ValueError, match="20 dims"):
            p.validate()

    def test_empty_mechanism(self):
        p = PrimingCondition(
            page_activation_vector=[0.5] * 20,
            ad_mechanism="",
            attentional_posture=0.0,
            attentional_posture_confidence=0.5,
        )
        with pytest.raises(ValueError, match="ad_mechanism"):
            p.validate()

    def test_posture_out_of_range(self):
        p = PrimingCondition(
            page_activation_vector=[0.5] * 20,
            ad_mechanism="m",
            attentional_posture=1.5,
            attentional_posture_confidence=0.5,
        )
        with pytest.raises(ValueError, match="attentional_posture"):
            p.validate()

    def test_confidence_out_of_range(self):
        p = PrimingCondition(
            page_activation_vector=[0.5] * 20,
            ad_mechanism="m",
            attentional_posture=0.0,
            attentional_posture_confidence=1.5,
        )
        with pytest.raises(ValueError, match="confidence"):
            p.validate()


# -----------------------------------------------------------------------------
# GoalFulfillmentOutcome
# -----------------------------------------------------------------------------

class TestGoalFulfillmentOutcome:
    def test_valid(self):
        _valid_outcome().validate()

    def test_metric_name_mismatch(self):
        o = GoalFulfillmentOutcome(
            outcome_metric="different_metric",
            projected_distribution=_valid_spies(),  # metric_name is durable_conversion_rate
            autopilot_route_fraction=0.5,
            attention_route_fraction=0.3,
        )
        with pytest.raises(ValueError, match="must match outcome_metric"):
            o.validate()

    def test_route_fractions_exceed_one(self):
        o = GoalFulfillmentOutcome(
            outcome_metric="durable_conversion_rate",
            projected_distribution=_valid_spies(),
            autopilot_route_fraction=0.6,
            attention_route_fraction=0.5,  # sum = 1.1
        )
        with pytest.raises(ValueError, match="> 1"):
            o.validate()


# -----------------------------------------------------------------------------
# CompetingActivations + AudienceSummary
# -----------------------------------------------------------------------------

class TestCompetingActivations:
    def test_valid(self):
        _valid_competing().validate()

    def test_baseline_rate_out_of_range(self):
        c = dataclasses.replace(_valid_competing(), baseline_rate=1.5)
        with pytest.raises(ValueError, match="baseline_rate"):
            c.validate()


class TestAudienceSummary:
    def test_valid(self):
        _valid_summary().validate()

    def test_negative_observation_count(self):
        s = dataclasses.replace(_valid_summary(), observation_count=-1)
        with pytest.raises(ValueError, match="non-negative"):
            s.validate()


# -----------------------------------------------------------------------------
# ProjectedImpact composition + hash
# -----------------------------------------------------------------------------

class TestProjectedImpact:
    def test_valid(self):
        _valid_projected_impact().validate()

    def test_invalid_sub_type_propagates(self):
        pi = dataclasses.replace(
            _valid_projected_impact(),
            audience_summary=dataclasses.replace(_valid_summary(), observation_count=-1),
        )
        with pytest.raises(ValueError, match="non-negative"):
            pi.validate()

    def test_missing_claim_id(self):
        pi = dataclasses.replace(_valid_projected_impact(), claim_id="")
        with pytest.raises(ValueError, match="claim_id"):
            pi.validate()

    def test_non_positive_horizon(self):
        pi = dataclasses.replace(_valid_projected_impact(), horizon_days=0)
        with pytest.raises(ValueError, match="horizon_days"):
            pi.validate()

    def test_frozen_dataclass_prevents_mutation(self):
        pi = _valid_projected_impact()
        with pytest.raises(dataclasses.FrozenInstanceError):
            pi.claim_id = "mutated"  # type: ignore[misc]


class TestContentHash:
    def test_deterministic(self):
        pi = _valid_projected_impact()
        h1 = pi.compute_content_hash()
        h2 = pi.compute_content_hash()
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex

    def test_metadata_changes_do_not_affect_hash(self):
        """created_at / content_hash are metadata — substantive_content()
        must exclude them so cosmetic changes don't perturb the receipt."""
        pi1 = _valid_projected_impact()
        pi2 = dataclasses.replace(
            pi1,
            created_at="2026-04-24T12:00:00Z",
            content_hash="manually_set",
        )
        assert pi1.compute_content_hash() == pi2.compute_content_hash()

    def test_substantive_change_changes_hash(self):
        pi = _valid_projected_impact()
        variations = [
            dataclasses.replace(pi, claim_id=pi.claim_id + "_v2"),
            dataclasses.replace(pi, horizon_days=30),
            dataclasses.replace(pi, recommendation_class_id="other"),
            dataclasses.replace(
                pi,
                audience_scope=dataclasses.replace(
                    pi.audience_scope, horizon_band="long"
                ),
            ),
        ]
        base_hash = pi.compute_content_hash()
        for variant in variations:
            assert variant.compute_content_hash() != base_hash

    def test_canonical_hash_standalone(self):
        """canonical_hash should produce stable hex over arbitrary payloads."""
        h1 = canonical_hash({"a": 1, "b": [2, 3]})
        h2 = canonical_hash({"b": [2, 3], "a": 1})  # different key order
        assert h1 == h2  # sort_keys=True normalizes order

        h3 = canonical_hash({"a": 1, "b": [2, 3, 4]})  # different content
        assert h1 != h3
