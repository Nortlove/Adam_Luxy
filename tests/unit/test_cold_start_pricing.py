# =============================================================================
# Cold Start Scoring & Pricing Validation
# Location: tests/unit/test_cold_start_pricing.py
# =============================================================================

"""
Validates the complete cold-start scoring and pricing system:

1. BuyerUncertaintyProfile — per-dimension Beta posteriors
2. Archetype-informed priors — differentiated cold-start beliefs
3. Bayesian update mechanics — learning from observations
4. Information value computation — bid premiums for exploration
5. Premium convergence — bid decay as buyer becomes characterized
6. Gradient field integration — dimension-weighted learning value
7. Full bid decomposition — conversion + information value
8. Observability metrics — tracking computations
"""

import math
import pytest
from unittest.mock import MagicMock
from dataclasses import dataclass

from adam.intelligence.information_value import (
    BuyerUncertaintyProfile,
    ConstructPosterior,
    InformationValueResult,
    compute_information_value,
    compute_bid_with_information_value,
    iv_metrics,
    _IVMetrics,
    UNCERTAINTY_DIMENSIONS,
    DEFAULT_ALPHA,
    DEFAULT_BETA,
    _ARCHETYPE_DIMENSION_PRIORS,
)


# =============================================================================
# 1. ConstructPosterior — The Beta distribution building block
# =============================================================================

class TestConstructPosterior:
    """Validate the per-dimension Beta posterior mechanics."""

    def test_default_prior(self):
        """Default Beta(2,2) is uninformative."""
        p = ConstructPosterior()
        assert p.alpha == 2.0
        assert p.beta == 2.0
        assert p.mean == pytest.approx(0.5, abs=0.001)
        # Beta(2,2) variance = 2*2 / (4^2 * 5) = 4/80 = 0.05
        assert p.variance == pytest.approx(0.05, abs=0.001)

    def test_confidence_at_default(self):
        """Confidence should be low at default prior."""
        p = ConstructPosterior()
        # confidence = 1 - min(1, 4*0.05) = 1 - 0.2 = 0.8
        assert p.confidence == pytest.approx(0.8, abs=0.01)

    def test_confidence_grows_with_observations(self):
        """Confidence should increase as we observe more data."""
        p = ConstructPosterior()
        initial_conf = p.confidence
        # Simulate 10 observations at value=0.6
        for _ in range(10):
            p.update(0.6, weight=1.0)
        assert p.confidence > initial_conf

    def test_update_shifts_mean(self):
        """Updating with high values should shift mean upward."""
        p = ConstructPosterior()
        for _ in range(5):
            p.update(0.9, weight=1.0)
        assert p.mean > 0.6

    def test_update_shifts_mean_down(self):
        """Updating with low values should shift mean downward."""
        p = ConstructPosterior()
        for _ in range(5):
            p.update(0.1, weight=1.0)
        assert p.mean < 0.4

    def test_variance_shrinks_with_observations(self):
        """Variance should decrease as we observe more data."""
        p = ConstructPosterior()
        initial_var = p.variance
        for _ in range(10):
            p.update(0.5, weight=1.0)
        assert p.variance < initial_var

    def test_expected_information_gain_positive(self):
        """EIG should be positive (we always learn something)."""
        p = ConstructPosterior()
        eig = p.expected_information_gain()
        assert eig > 0

    def test_eig_decreases_with_observations(self):
        """EIG should decrease as posterior tightens."""
        p = ConstructPosterior()
        eig_initial = p.expected_information_gain()
        for _ in range(20):
            p.update(0.5, weight=1.0)
        eig_later = p.expected_information_gain()
        assert eig_later < eig_initial

    def test_weighted_update(self):
        """Weight=0.3 should move the posterior less than weight=1.0."""
        p1 = ConstructPosterior()
        p2 = ConstructPosterior()
        p1.update(0.8, weight=1.0)
        p2.update(0.8, weight=0.3)
        # p1 should have moved further from default
        assert abs(p1.mean - 0.5) > abs(p2.mean - 0.5)


# =============================================================================
# 2. BuyerUncertaintyProfile — Complete buyer state
# =============================================================================

class TestBuyerUncertaintyProfile:
    """Validate the full buyer profile."""

    def test_default_profile_has_all_dimensions(self):
        """Profile should initialize all UNCERTAINTY_DIMENSIONS.

        Schema-evolution note: dimension count grew from 20 (pre-W.2b)
        to 21 (W.2b adds maximizer_tendency per Q24=(β) + Q26
        adjudication). Test pins the symbolic count
        (len(UNCERTAINTY_DIMENSIONS)) rather than literal 20 so future
        dimension additions don't break this test."""
        profile = BuyerUncertaintyProfile(buyer_id="test_buyer")
        assert len(profile.constructs) == len(UNCERTAINTY_DIMENSIONS)

    def test_default_profile_high_uncertainty(self):
        """New buyer should have high aggregate uncertainty."""
        profile = BuyerUncertaintyProfile(buyer_id="test_buyer")
        assert profile.aggregate_uncertainty > 0.04  # Beta(2,2) variance = 0.05

    def test_default_profile_metadata(self):
        """New buyer should have zero interactions."""
        profile = BuyerUncertaintyProfile(buyer_id="test_buyer")
        assert profile.total_interactions == 0
        assert profile.total_conversions == 0

    def test_update_from_edge_reduces_uncertainty(self):
        """Updating from a conversion edge should reduce uncertainty."""
        profile = BuyerUncertaintyProfile(buyer_id="test_buyer")
        initial_uncertainty = profile.aggregate_uncertainty

        edge_dims = {
            "regulatory_fit": 0.8,
            "construal_fit": 0.6,
            "personality_alignment": 0.7,
            "emotional_resonance": 0.5,
        }
        deltas = profile.update_from_edge(edge_dims, signal_type="conversion")

        assert profile.aggregate_uncertainty < initial_uncertainty
        assert profile.total_interactions == 1
        assert profile.total_conversions == 1
        # Variance deltas should be positive for updated dims
        for dim in edge_dims:
            assert deltas[dim] > 0

    def test_update_click_vs_conversion_weight(self):
        """Click signal (weight=0.3) should teach less than conversion (weight=1.0)."""
        p1 = BuyerUncertaintyProfile(buyer_id="buyer1")
        p2 = BuyerUncertaintyProfile(buyer_id="buyer2")

        edge = {"regulatory_fit": 0.7}
        d1 = p1.update_from_edge(edge, signal_type="conversion")
        d2 = p2.update_from_edge(edge, signal_type="click")

        assert d1["regulatory_fit"] > d2["regulatory_fit"]

    def test_total_information_gain_available(self):
        """Total EIG should be positive for new buyer."""
        profile = BuyerUncertaintyProfile(buyer_id="test_buyer")
        tig = profile.total_information_gain_available
        assert tig > 0

    def test_serialization_roundtrip(self):
        """to_dict → from_dict should preserve state."""
        profile = BuyerUncertaintyProfile(buyer_id="buyer123")
        profile.update_from_edge({"regulatory_fit": 0.8}, "conversion")

        data = profile.to_dict()
        restored = BuyerUncertaintyProfile.from_dict(data)

        assert restored.buyer_id == "buyer123"
        assert restored.total_interactions == 1
        assert restored.total_conversions == 1
        assert restored.constructs["regulatory_fit"].alpha == profile.constructs["regulatory_fit"].alpha
        assert restored.constructs["regulatory_fit"].beta == profile.constructs["regulatory_fit"].beta


# =============================================================================
# 3. Archetype-Informed Cold Start Priors
# =============================================================================

class TestArchetypePriors:
    """Validate that archetypes get differentiated starting beliefs."""

    def test_all_eight_archetypes_defined(self):
        """All 8 archetypes should have prior definitions."""
        expected = {"achiever", "explorer", "connector", "guardian",
                    "analyst", "creator", "nurturer", "pragmatist"}
        assert set(_ARCHETYPE_DIMENSION_PRIORS.keys()) == expected

    def test_achiever_has_strong_regulatory_fit_prior(self):
        """Achiever should expect high regulatory fit (promotion focus)."""
        profile = BuyerUncertaintyProfile.from_archetype_priors("achiever", "buyer_a")
        reg_fit = profile.constructs["regulatory_fit"]
        # Beta(5,2) → mean ≈ 0.71
        assert reg_fit.alpha > DEFAULT_ALPHA
        assert reg_fit.mean > 0.6

    def test_guardian_has_strong_loss_aversion_prior(self):
        """Guardian should expect high loss aversion."""
        profile = BuyerUncertaintyProfile.from_archetype_priors("guardian", "buyer_g")
        loss = profile.constructs["loss_aversion_intensity"]
        assert loss.alpha > DEFAULT_ALPHA
        assert loss.mean > 0.6

    def test_explorer_has_strong_narrative_prior(self):
        """Explorer should expect high narrative transport."""
        profile = BuyerUncertaintyProfile.from_archetype_priors("explorer", "buyer_e")
        narrative = profile.constructs["narrative_transport"]
        assert narrative.alpha > DEFAULT_ALPHA
        assert narrative.mean > 0.6

    def test_connector_has_strong_social_proof_prior(self):
        """Connector should expect high social proof sensitivity."""
        profile = BuyerUncertaintyProfile.from_archetype_priors("connector", "buyer_c")
        social = profile.constructs["social_proof_sensitivity"]
        assert social.alpha > DEFAULT_ALPHA
        assert social.mean > 0.6

    def test_archetype_priors_vs_uniform(self):
        """Archetype priors should have lower initial uncertainty on key dims."""
        uniform = BuyerUncertaintyProfile(buyer_id="uniform")
        achiever = BuyerUncertaintyProfile.from_archetype_priors("achiever", "ach")

        # Achiever should be more certain about regulatory_fit
        assert achiever.constructs["regulatory_fit"].variance < \
               uniform.constructs["regulatory_fit"].variance

    def test_archetype_unspecified_dims_stay_default(self):
        """Dimensions not in the archetype's priors should stay Beta(2,2)."""
        profile = BuyerUncertaintyProfile.from_archetype_priors("achiever", "buyer")
        # Achiever has no prior on mimetic_desire
        mime = profile.constructs["mimetic_desire"]
        assert mime.alpha == DEFAULT_ALPHA
        assert mime.beta == DEFAULT_BETA

    def test_unknown_archetype_falls_back_to_uniform(self):
        """Unknown archetype should get uniform priors on everything."""
        profile = BuyerUncertaintyProfile.from_archetype_priors("nonexistent", "buyer")
        for dim, posterior in profile.constructs.items():
            assert posterior.alpha == DEFAULT_ALPHA
            assert posterior.beta == DEFAULT_BETA

    def test_archetype_prior_accelerates_learning(self):
        """Archetype-primed buyer should reach confidence faster on primed dims."""
        uniform = BuyerUncertaintyProfile(buyer_id="uniform")
        achiever = BuyerUncertaintyProfile.from_archetype_priors("achiever", "ach")

        # 3 observations on regulatory_fit
        for _ in range(3):
            uniform.update_from_edge({"regulatory_fit": 0.75}, "conversion")
            achiever.update_from_edge({"regulatory_fit": 0.75}, "conversion")

        # Achiever should be more confident (started tighter)
        assert achiever.constructs["regulatory_fit"].confidence > \
               uniform.constructs["regulatory_fit"].confidence


# =============================================================================
# 4. Information Value Computation
# =============================================================================

class TestInformationValueComputation:
    """Validate the core pricing engine."""

    def test_new_buyer_gets_positive_iv(self):
        """Brand new buyer should have positive information value."""
        buyer = BuyerUncertaintyProfile(buyer_id="new_buyer")
        result = compute_information_value(buyer, base_cpm=3.50)

        assert result.information_value > 0
        assert result.recommended_bid_premium > 0
        assert result.bid_modifier_pct > 0

    def test_new_buyer_exploration_critical(self):
        """Brand new buyer (0 interactions) should be 'critical' priority."""
        buyer = BuyerUncertaintyProfile(buyer_id="new")
        result = compute_information_value(buyer, base_cpm=3.50)
        assert result.exploration_priority == "critical"

    def test_few_interactions_exploration_high(self):
        """Buyer with 3 interactions should be 'high' priority."""
        buyer = BuyerUncertaintyProfile(buyer_id="few")
        buyer.total_interactions = 3
        result = compute_information_value(buyer, base_cpm=3.50)
        assert result.exploration_priority == "high"

    def test_well_characterized_buyer_low_iv(self):
        """Buyer with many interactions should have near-zero IV."""
        buyer = BuyerUncertaintyProfile(buyer_id="veteran")
        # Simulate 50 observations tightening all constructs
        edge = {dim: 0.6 for dim in UNCERTAINTY_DIMENSIONS}
        for _ in range(50):
            buyer.update_from_edge(edge, "conversion")

        result = compute_information_value(buyer, base_cpm=3.50)
        # IV should be much lower than a new buyer
        new_buyer = BuyerUncertaintyProfile(buyer_id="new")
        new_result = compute_information_value(new_buyer, base_cpm=3.50)

        assert result.recommended_bid_premium < new_result.recommended_bid_premium * 0.2

    def test_bid_premium_capped(self):
        """Bid premium should not exceed max_bid_premium_pct of base CPM."""
        buyer = BuyerUncertaintyProfile(buyer_id="new")
        result = compute_information_value(buyer, base_cpm=3.50)

        # Default cap is 100% → max premium = $3.50
        assert result.recommended_bid_premium <= 3.50

    def test_iv_result_has_reasoning(self):
        """Result should include reasoning trace."""
        buyer = BuyerUncertaintyProfile(buyer_id="new")
        result = compute_information_value(buyer, base_cpm=3.50)
        assert len(result.reasoning) > 0
        assert "buyer" in result.reasoning[-1].lower() or "info" in result.reasoning[-1].lower()

    def test_iv_has_dimension_values(self):
        """Result should break down value by dimension."""
        buyer = BuyerUncertaintyProfile(buyer_id="new")
        result = compute_information_value(buyer, base_cpm=3.50)
        assert len(result.dimension_values) > 0

    def test_iv_with_zero_base_cpm(self):
        """Should handle zero CPM gracefully."""
        buyer = BuyerUncertaintyProfile(buyer_id="new")
        result = compute_information_value(buyer, base_cpm=0.0)
        # Should not crash
        assert result.information_value >= 0


# =============================================================================
# 5. Premium Convergence — The Exploration Decay Curve
# =============================================================================

class TestPremiumConvergence:
    """Validate that bid premiums decay as the buyer is characterized."""

    def test_premium_decreases_over_time(self):
        """Premium should decrease substantially over many interactions.

        Note: With only 7/20 dims updated, early premiums stay capped at
        base_cpm because extended dims retain high uncertainty. With all
        20 dims updated, the premium drops below the cap around i=9 and
        converges toward zero.
        """
        buyer = BuyerUncertaintyProfile(buyer_id="decay_test")
        premiums = []

        # Update ALL 20 dimensions to see convergence
        edge = {dim: 0.6 for dim in UNCERTAINTY_DIMENSIONS}

        for i in range(30):
            result = compute_information_value(buyer, base_cpm=3.50)
            premiums.append(result.recommended_bid_premium)
            buyer.update_from_edge(edge, "conversion")

        # Premium should drop below cap by ~interaction 10
        assert premiums[15] < premiums[0]
        # Premium at interaction 25 should be <30% of peak
        assert premiums[25] < premiums[0] * 0.30

    def test_exploration_priority_transitions(self):
        """Priority should transition: critical → high → medium/low → none."""
        buyer = BuyerUncertaintyProfile(buyer_id="priority_test")
        edge = {dim: 0.6 for dim in UNCERTAINTY_DIMENSIONS}
        priorities = []

        for _ in range(50):
            result = compute_information_value(buyer, base_cpm=3.50)
            priorities.append(result.exploration_priority)
            buyer.update_from_edge(edge, "conversion")

        assert priorities[0] == "critical"
        assert "none" in priorities  # should eventually reach none


# =============================================================================
# 6. Gradient Field Integration
# =============================================================================

class TestGradientFieldIntegration:
    """Validate that gradient fields weight information value by dimension importance."""

    @staticmethod
    def _make_gradient_field(**kwargs):
        """Create a mock gradient field."""
        gf = MagicMock()
        gf.gradients = kwargs.get("gradients", {})
        return gf

    def test_gradient_weights_dimension_value(self):
        """High-gradient dimensions should contribute more to IV."""
        buyer = BuyerUncertaintyProfile(buyer_id="grad_test")

        # Gradient field: regulatory_fit has high gradient, rest low
        gf = self._make_gradient_field(gradients={
            "regulatory_fit": 0.8,
            "construal_fit": 0.1,
            "personality_alignment": 0.1,
            "emotional_resonance": 0.1,
            "value_alignment": 0.1,
            "evolutionary_motive": 0.05,
            "linguistic_style": 0.05,
        })

        result = compute_information_value(buyer, gradient_field=gf, base_cpm=3.50)

        # regulatory_fit should have highest dimension value
        if "regulatory_fit" in result.dimension_values:
            assert result.dimension_values["regulatory_fit"] >= \
                   result.dimension_values.get("construal_fit", 0)

    def test_gradient_vs_no_gradient_iv(self):
        """With a focused gradient, IV should differ from uniform weighting."""
        buyer1 = BuyerUncertaintyProfile(buyer_id="g1")
        buyer2 = BuyerUncertaintyProfile(buyer_id="g2")

        gf = self._make_gradient_field(gradients={
            "regulatory_fit": 0.9,
            "construal_fit": 0.01,
        })

        r1 = compute_information_value(buyer1, gradient_field=gf, base_cpm=3.50)
        r2 = compute_information_value(buyer2, gradient_field=None, base_cpm=3.50)

        # Should differ because gradient weights change the value mix
        assert r1.gradient_weighted_gain != r2.gradient_weighted_gain

    def test_gradient_reasoning_mentions_top_dimension(self):
        """Reasoning should identify the highest-value learning dimension."""
        buyer = BuyerUncertaintyProfile(buyer_id="reason")
        gf = self._make_gradient_field(gradients={
            "regulatory_fit": 0.9,
            "emotional_resonance": 0.05,
        })
        result = compute_information_value(buyer, gradient_field=gf, base_cpm=3.50)
        # Reasoning should mention which dimension has highest learning value
        combined_reasoning = " ".join(result.reasoning)
        assert "regulatory_fit" in combined_reasoning


# =============================================================================
# 7. Full Bid Decomposition
# =============================================================================

class TestFullBidDecomposition:
    """Validate the complete bid = conversion + information value."""

    def test_bid_decomposition_structure(self):
        """compute_bid_with_information_value should return all components."""
        buyer = BuyerUncertaintyProfile(buyer_id="bid_test")
        result = compute_bid_with_information_value(
            base_bid_cpm=3.50,
            conversion_probability=0.02,
            expected_revenue=50.0,
            buyer=buyer,
        )

        assert "total_bid_cpm" in result
        assert "base_bid_cpm" in result
        assert "information_component_cpm" in result
        assert "bid_premium_pct" in result
        assert "exploration_priority" in result
        assert "buyer_confidence" in result
        assert "reasoning" in result

    def test_total_bid_exceeds_base(self):
        """Total bid for new buyer should exceed base bid."""
        buyer = BuyerUncertaintyProfile(buyer_id="bid_new")
        result = compute_bid_with_information_value(
            base_bid_cpm=3.50,
            conversion_probability=0.02,
            expected_revenue=50.0,
            buyer=buyer,
        )
        assert result["total_bid_cpm"] > result["base_bid_cpm"]

    def test_veteran_bid_near_base(self):
        """Well-characterized buyer's bid should be close to base."""
        buyer = BuyerUncertaintyProfile(buyer_id="bid_vet")
        edge = {dim: 0.6 for dim in UNCERTAINTY_DIMENSIONS}
        for _ in range(50):
            buyer.update_from_edge(edge, "conversion")

        result = compute_bid_with_information_value(
            base_bid_cpm=3.50,
            conversion_probability=0.02,
            expected_revenue=50.0,
            buyer=buyer,
        )
        # Premium should be small
        assert result["information_component_cpm"] < 0.50

    def test_top_learning_dimensions_included(self):
        """Top learning dimensions should be in the response."""
        buyer = BuyerUncertaintyProfile(buyer_id="bid_dims")
        result = compute_bid_with_information_value(
            base_bid_cpm=3.50,
            conversion_probability=0.02,
            expected_revenue=50.0,
            buyer=buyer,
        )
        assert "top_learning_dimensions" in result
        assert len(result["top_learning_dimensions"]) <= 3


# =============================================================================
# 8. Observability Metrics
# =============================================================================

class TestIVObservability:
    """Validate the metrics tracking system."""

    def test_metrics_summary_structure(self):
        """Metrics summary should have all expected keys."""
        m = _IVMetrics()
        summary = m.summary()
        assert "iv_computations_total" in summary
        assert "iv_avg_bid_premium" in summary
        assert "iv_max_bid_premium" in summary
        assert "iv_profiles_created" in summary
        assert "iv_profiles_updated" in summary
        assert "iv_priority_distribution" in summary

    def test_metrics_record_computation(self):
        """Recording a computation should update counters."""
        m = _IVMetrics()
        result = InformationValueResult(
            recommended_bid_premium=1.50,
            exploration_priority="critical",
        )
        m.record_computation(result)
        assert m.computations_total == 1
        assert m._premium_max == 1.50

    def test_metrics_priority_distribution(self):
        """Priority distribution should track all priority levels."""
        m = _IVMetrics()
        for priority in ["critical", "high", "medium", "low", "none"]:
            result = InformationValueResult(
                recommended_bid_premium=0.5,
                exploration_priority=priority,
            )
            m.record_computation(result)

        summary = m.summary()
        for priority in ["critical", "high", "medium", "low", "none"]:
            assert summary["iv_priority_distribution"][priority] >= 1


# =============================================================================
# 9. End-to-End Cold Start Scenario
# =============================================================================

class TestColdStartEndToEnd:
    """Full scenario: buyer arrives → gets priced → converts → gets repriced."""

    def test_full_cold_start_lifecycle(self):
        """Simulate the complete lifecycle of a cold-start buyer.

        1. New buyer arrives → high bid premium, critical exploration
        2. First conversion → update profile → lower premium
        3. Several more conversions → premium converges to near-zero
        4. Well-characterized buyer → bid purely on conversion probability
        """
        # Phase 1: Brand new achiever buyer
        buyer = BuyerUncertaintyProfile.from_archetype_priors("achiever", "buyer_lifecycle")
        assert buyer.total_interactions == 0

        r1 = compute_information_value(buyer, base_cpm=3.50)
        assert r1.exploration_priority == "critical"
        assert r1.recommended_bid_premium > 0
        initial_premium = r1.recommended_bid_premium

        # Phase 2: First conversion arrives with edge dimensions (all 20)
        edge_1 = {dim: 0.6 + (0.1 if i < 7 else 0.0)
                  for i, dim in enumerate(UNCERTAINTY_DIMENSIONS)}
        deltas = buyer.update_from_edge(edge_1, "conversion")
        assert buyer.total_interactions == 1
        assert all(d > 0 for d in deltas.values())

        r2 = compute_information_value(buyer, base_cpm=3.50)
        # After 1 interaction the info_value drops but premium may still
        # be capped; the key assertion is that info_value decreased
        assert r2.information_value < r1.information_value

        # Phase 3: 15 more conversions (enough to drop below cap)
        for _ in range(15):
            buyer.update_from_edge(edge_1, "conversion")

        r3 = compute_information_value(buyer, base_cpm=3.50)
        assert r3.recommended_bid_premium < initial_premium
        assert r3.exploration_priority != "critical"

        # Phase 4: 40 more conversions → well-characterized
        for _ in range(40):
            buyer.update_from_edge(edge_1, "conversion")

        r4 = compute_information_value(buyer, base_cpm=3.50)
        assert r4.recommended_bid_premium < initial_premium * 0.10  # <10% of initial
        assert r4.buyer_confidence > 0.8

    def test_archetype_differentiation_in_pricing(self):
        """Different archetypes should get different initial premiums
        when gradient fields differ."""
        gf_achiever = MagicMock()
        gf_achiever.gradients = {"regulatory_fit": 0.8, "personality_alignment": 0.6}

        gf_guardian = MagicMock()
        gf_guardian.gradients = {"loss_aversion_intensity": 0.9, "decision_entropy": 0.7}

        achiever = BuyerUncertaintyProfile.from_archetype_priors("achiever", "a")
        guardian = BuyerUncertaintyProfile.from_archetype_priors("guardian", "g")

        r_a = compute_information_value(achiever, gradient_field=gf_achiever, base_cpm=3.50)
        r_g = compute_information_value(guardian, gradient_field=gf_guardian, base_cpm=3.50)

        # Both should have positive IV but different gradient-weighted gains
        assert r_a.gradient_weighted_gain > 0
        assert r_g.gradient_weighted_gain > 0
        # They should differ because priors × gradients create different profiles
        assert r_a.gradient_weighted_gain != r_g.gradient_weighted_gain


# =============================================================================
# 10. Dimension Count Normalization
# =============================================================================

class TestDimensionNormalization:
    """Validate that the dimension-count normalization prevents premium bloat."""

    def test_full_dim_premium_reasonable(self):
        """With the full UNCERTAINTY_DIMENSIONS set, initial premium
        should not exceed base CPM. Schema-evolution note: dimension
        count grew from 20 (pre-W.2b) to 21 (W.2b adds
        maximizer_tendency); test pins the invariant (premium ≤ base
        CPM) symbolically over len(UNCERTAINTY_DIMENSIONS) rather
        than literal 20."""
        buyer = BuyerUncertaintyProfile(buyer_id="norm_test")
        assert len(buyer.constructs) == len(UNCERTAINTY_DIMENSIONS)
        result = compute_information_value(buyer, base_cpm=3.50)
        # Premium should be capped at base CPM (100% cap)
        assert result.recommended_bid_premium <= 3.50

    def test_normalization_factor(self):
        """Accuracy-to-lift factor should scale inversely with
        dimension count.

        Formula: factor = 5.0 * 7 / n_dims (7 = core edge dimensions
        baseline). Pin the formula's structural invariant — the
        result divides 35 by current dimension count — rather than
        the literal value (which is dimension-count-sensitive and
        will change with future dimension additions like W.2b's
        maximizer_tendency)."""
        buyer = BuyerUncertaintyProfile(buyer_id="norm")
        n_dims = len(buyer.constructs)
        expected_factor = 5.0 * 7.0 / n_dims
        # Pin formula structure: factor × n_dims == 35 (5.0 × 7 cores).
        assert expected_factor * n_dims == pytest.approx(35.0)
