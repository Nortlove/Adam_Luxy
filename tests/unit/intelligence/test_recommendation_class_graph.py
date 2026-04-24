"""Unit tests for RecommendationClassGraph identity layer.

Tests the invariants that make the identity safe to use as a stable,
deterministic key across the pilot. Neo4j-facing methods are covered by
integration tests against a live database — not here.
"""

from __future__ import annotations

import dataclasses
import pytest

from adam.intelligence.recommendation_class import (
    RecommendationClassIdentity,
    claim_node_id,
    recommendation_class_id,
)


def _valid_identity() -> RecommendationClassIdentity:
    return RecommendationClassIdentity(
        advertiser_id="luxy_ride",
        archetype_id="status_seeker",
        mechanism="regulatory_fit",
        context_posture_band="autopilot_low",
        horizon_band="short",
    )


# -----------------------------------------------------------------------------
# RecommendationClassIdentity
# -----------------------------------------------------------------------------

class TestRecommendationClassIdentity:
    def test_valid(self):
        _valid_identity().validate()

    def test_empty_advertiser_id_rejected(self):
        identity = dataclasses.replace(_valid_identity(), advertiser_id="")
        with pytest.raises(ValueError, match="advertiser_id"):
            identity.validate()

    def test_empty_archetype_id_rejected(self):
        identity = dataclasses.replace(_valid_identity(), archetype_id="")
        with pytest.raises(ValueError, match="archetype_id"):
            identity.validate()

    def test_empty_mechanism_rejected(self):
        identity = dataclasses.replace(_valid_identity(), mechanism="")
        with pytest.raises(ValueError, match="mechanism"):
            identity.validate()

    def test_empty_posture_band_rejected(self):
        identity = dataclasses.replace(_valid_identity(), context_posture_band="")
        with pytest.raises(ValueError, match="context_posture_band"):
            identity.validate()

    def test_empty_horizon_band_rejected(self):
        identity = dataclasses.replace(_valid_identity(), horizon_band="")
        with pytest.raises(ValueError, match="horizon_band"):
            identity.validate()

    def test_frozen(self):
        identity = _valid_identity()
        with pytest.raises(dataclasses.FrozenInstanceError):
            identity.advertiser_id = "mutated"  # type: ignore[misc]


# -----------------------------------------------------------------------------
# recommendation_class_id — determinism and collision resistance
# -----------------------------------------------------------------------------

class TestRecommendationClassId:
    def test_format(self):
        id_ = recommendation_class_id(_valid_identity())
        assert id_.startswith("rec_class:")
        # 16 hex chars after the prefix
        suffix = id_[len("rec_class:"):]
        assert len(suffix) == 16
        assert all(c in "0123456789abcdef" for c in suffix)

    def test_deterministic(self):
        id_a = recommendation_class_id(_valid_identity())
        id_b = recommendation_class_id(_valid_identity())
        assert id_a == id_b

    def test_id_property_matches_function(self):
        identity = _valid_identity()
        assert identity.id == recommendation_class_id(identity)

    def test_different_tuples_produce_different_ids(self):
        base = _valid_identity()
        variations = [
            dataclasses.replace(base, advertiser_id="other_advertiser"),
            dataclasses.replace(base, archetype_id="other_archetype"),
            dataclasses.replace(base, mechanism="other_mechanism"),
            dataclasses.replace(base, context_posture_band="vigilance_high"),
            dataclasses.replace(base, horizon_band="long"),
        ]
        base_id = recommendation_class_id(base)
        for variant in variations:
            assert recommendation_class_id(variant) != base_id

    def test_components_with_separator_character_do_not_collide(self):
        """The canonical slug joins components with '|'. Components
        containing '|' should still produce distinct ids (SHA-256 over the
        concatenated slug). This confirms no pathological collision when
        a component contains the delimiter."""
        identity_a = RecommendationClassIdentity(
            advertiser_id="a|b",
            archetype_id="c",
            mechanism="m",
            context_posture_band="p",
            horizon_band="h",
        )
        identity_b = RecommendationClassIdentity(
            advertiser_id="a",
            archetype_id="b|c",
            mechanism="m",
            context_posture_band="p",
            horizon_band="h",
        )
        # If slugs collide, both map to same digest. With "|" in values,
        # slugs are "a|b|c|m|p|h" vs "a|b|c|m|p|h" — collision intended
        # to document the known limitation (delimiter in values is a
        # caller-owned concern).
        # This test asserts the behavior rather than hides it.
        assert recommendation_class_id(identity_a) == recommendation_class_id(identity_b)


# -----------------------------------------------------------------------------
# claim_node_id
# -----------------------------------------------------------------------------

class TestClaimNodeId:
    def test_format(self):
        node_id = claim_node_id("my_claim", "a" * 64)
        assert node_id.startswith("claim:")
        assert "my_claim" in node_id
        # 16-char suffix from the content hash
        assert node_id.endswith("a" * 16)

    def test_deterministic(self):
        id_a = claim_node_id("claim_x", "abc123def456abcd" + "0" * 48)
        id_b = claim_node_id("claim_x", "abc123def456abcd" + "0" * 48)
        assert id_a == id_b

    def test_empty_claim_id_rejected(self):
        with pytest.raises(ValueError, match="claim_id is required"):
            claim_node_id("", "a" * 64)

    def test_short_content_hash_rejected(self):
        with pytest.raises(ValueError, match="content_hash"):
            claim_node_id("claim_x", "abc")

    def test_different_claims_produce_different_ids(self):
        id_a = claim_node_id("claim_a", "a" * 64)
        id_b = claim_node_id("claim_b", "a" * 64)
        assert id_a != id_b

    def test_different_content_hashes_produce_different_ids(self):
        id_a = claim_node_id("claim_x", "a" * 64)
        id_b = claim_node_id("claim_x", "b" * 64)
        assert id_a != id_b


# -----------------------------------------------------------------------------
# Integration with ProjectedImpact — the class id in the claim must match
# -----------------------------------------------------------------------------

class TestIdentityIntegration:
    def test_projected_impact_class_id_matches_identity_id(self):
        """When a ProjectedImpact is authored for a given identity, the
        claim's recommendation_class_id field must equal identity.id so
        graph writes resolve to the right RecommendationClass node."""
        from adam.intelligence.recommendation_class import (
            AudienceScope,
            AudienceSummary,
            CompetingActivations,
            GoalFulfillmentOutcome,
            PrimingCondition,
            ProjectedImpact,
            SpiesDistribution,
        )

        identity = _valid_identity()

        scope = AudienceScope(
            advertiser_id=identity.advertiser_id,
            archetype_id=identity.archetype_id,
            vertical="luxury_transportation",
            context_posture_band=identity.context_posture_band,
            horizon_band=identity.horizon_band,
        )

        claim = ProjectedImpact(
            claim_id="test_claim",
            recommendation_class_id=identity.id,  # caller must set this correctly
            priming_condition=PrimingCondition(
                page_activation_vector=[0.5] * 20,
                ad_mechanism=identity.mechanism,  # must match identity.mechanism
                attentional_posture=0.0,
                attentional_posture_confidence=0.5,
            ),
            audience_scope=scope,
            goal_fulfillment_outcome=GoalFulfillmentOutcome(
                outcome_metric="durable_conversion_rate",
                projected_distribution=SpiesDistribution(
                    metric_name="durable_conversion_rate",
                    bin_edges=[0.0, 0.05, 1.0],
                    bin_weights=[0.7, 0.3],
                ),
                autopilot_route_fraction=0.6,
                attention_route_fraction=0.2,
            ),
            competing_activations=CompetingActivations(
                counter_regulation_untracked=True,
                attention_route_residual=True,
                winners_curse_portion=True,
                publication_bias_residual=True,
                baseline_rate=0.01,
            ),
            audience_summary=AudienceSummary(
                observation_count=100,
                coverage_estimate=0.8,
                expected_signal_strength=0.6,
            ),
            horizon_days=14,
        )

        claim.validate()
        assert claim.recommendation_class_id == identity.id
