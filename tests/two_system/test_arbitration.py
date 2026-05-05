"""Tests for the Daw two-system arbitration model (directive §1.G.SI.1)."""
from __future__ import annotations

import math

import pytest

from adam.two_system import (
    ArbitrationResult,
    QValueWithUncertainty,
    TwoSystemEstimate,
    arbitrate_with_processing_mode_prior,
    softmax_action_selection,
    uncertainty_weighted_arbitration,
)


# ----------------------------------------------------------------------------
# Frozen-dataclass invariants
# ----------------------------------------------------------------------------

class TestQValueWithUncertaintyInvariants:
    def test_basic_construction(self) -> None:
        q = QValueWithUncertainty(value=0.7, variance=0.04)
        assert q.value == 0.7
        assert q.variance == 0.04

    def test_rejects_zero_variance(self) -> None:
        with pytest.raises(ValueError):
            QValueWithUncertainty(value=0.5, variance=0.0)

    def test_rejects_negative_variance(self) -> None:
        with pytest.raises(ValueError):
            QValueWithUncertainty(value=0.5, variance=-0.1)

    def test_rejects_non_finite_value(self) -> None:
        with pytest.raises(ValueError):
            QValueWithUncertainty(value=float("nan"), variance=0.04)

    def test_rejects_non_finite_variance(self) -> None:
        with pytest.raises(ValueError):
            QValueWithUncertainty(value=0.5, variance=float("inf"))

    def test_frozen(self) -> None:
        q = QValueWithUncertainty(value=0.5, variance=0.04)
        with pytest.raises((AttributeError, Exception)):
            q.value = 0.9  # type: ignore[misc]


class TestArbitrationResultInvariants:
    def test_weights_must_sum_to_one(self) -> None:
        with pytest.raises(ValueError):
            ArbitrationResult(
                arbitrated_value=0.5,
                arbitrated_variance=0.02,
                weight_model_free=0.4,
                weight_model_based=0.4,  # 0.8 ≠ 1.0
            )

    def test_unit_sum_accepted(self) -> None:
        result = ArbitrationResult(
            arbitrated_value=0.5,
            arbitrated_variance=0.02,
            weight_model_free=0.3,
            weight_model_based=0.7,
        )
        assert result.weight_model_free == 0.3
        assert result.weight_model_based == 0.7


# ----------------------------------------------------------------------------
# Inverse-variance arbitration
# ----------------------------------------------------------------------------

class TestUncertaintyWeightedArbitration:
    def test_equal_uncertainty_yields_equal_weights(self) -> None:
        estimate = TwoSystemEstimate(
            model_free=QValueWithUncertainty(0.4, 0.05),
            model_based=QValueWithUncertainty(0.6, 0.05),
        )
        result = uncertainty_weighted_arbitration(estimate)
        assert result.weight_model_free == pytest.approx(0.5, abs=1e-12)
        assert result.weight_model_based == pytest.approx(0.5, abs=1e-12)
        # The arbitrated mean is the simple average.
        assert result.arbitrated_value == pytest.approx(0.5, abs=1e-12)

    def test_lower_variance_system_gets_higher_weight(self) -> None:
        # MF much more confident (lower variance) than MB.
        estimate = TwoSystemEstimate(
            model_free=QValueWithUncertainty(0.2, 0.001),
            model_based=QValueWithUncertainty(0.9, 0.5),
        )
        result = uncertainty_weighted_arbitration(estimate)
        assert result.weight_model_free > result.weight_model_based
        # Arbitrated value much closer to the confident MF estimate.
        assert abs(result.arbitrated_value - 0.2) < abs(result.arbitrated_value - 0.9)

    def test_arbitrated_variance_is_harmonic_mean_of_variances(self) -> None:
        """σ²_arbitrated = (σ²_MF * σ²_MB) / (σ²_MF + σ²_MB)."""
        sigma_mf = 0.04
        sigma_mb = 0.09
        estimate = TwoSystemEstimate(
            model_free=QValueWithUncertainty(0.3, sigma_mf),
            model_based=QValueWithUncertainty(0.7, sigma_mb),
        )
        result = uncertainty_weighted_arbitration(estimate)
        expected = (sigma_mf * sigma_mb) / (sigma_mf + sigma_mb)
        assert result.arbitrated_variance == pytest.approx(expected, rel=1e-12)

    def test_arbitrated_variance_strictly_smaller_than_each_component(self) -> None:
        """Information-additive Bayesian update: combining two estimates
        yields strictly smaller variance than either alone."""
        estimate = TwoSystemEstimate(
            model_free=QValueWithUncertainty(0.3, 0.04),
            model_based=QValueWithUncertainty(0.7, 0.09),
        )
        result = uncertainty_weighted_arbitration(estimate)
        assert result.arbitrated_variance < 0.04
        assert result.arbitrated_variance < 0.09

    def test_weights_sum_to_one(self) -> None:
        estimate = TwoSystemEstimate(
            model_free=QValueWithUncertainty(0.1, 0.02),
            model_based=QValueWithUncertainty(0.9, 0.07),
        )
        result = uncertainty_weighted_arbitration(estimate)
        assert (result.weight_model_free + result.weight_model_based
                == pytest.approx(1.0, abs=1e-12))

    def test_symmetry_in_value(self) -> None:
        """Swapping (Q_MF, σ_MF) ↔ (Q_MB, σ_MB) yields the same
        arbitrated value (with weights swapped)."""
        a = QValueWithUncertainty(0.3, 0.05)
        b = QValueWithUncertainty(0.7, 0.10)
        result1 = uncertainty_weighted_arbitration(
            TwoSystemEstimate(model_free=a, model_based=b)
        )
        result2 = uncertainty_weighted_arbitration(
            TwoSystemEstimate(model_free=b, model_based=a)
        )
        assert result1.arbitrated_value == pytest.approx(
            result2.arbitrated_value, abs=1e-12
        )
        assert result1.weight_model_free == pytest.approx(
            result2.weight_model_based, abs=1e-12
        )

    def test_extreme_variance_ratio(self) -> None:
        """When MF variance is 1000x MB variance, the result is
        dominated by MB."""
        estimate = TwoSystemEstimate(
            model_free=QValueWithUncertainty(0.0, 1.0),
            model_based=QValueWithUncertainty(1.0, 0.001),
        )
        result = uncertainty_weighted_arbitration(estimate)
        assert result.weight_model_based > 0.99
        assert result.arbitrated_value == pytest.approx(1.0, abs=0.01)


# ----------------------------------------------------------------------------
# Processing-mode-prior arbitration
# ----------------------------------------------------------------------------

class TestProcessingModePriorArbitration:
    def test_neutral_prior_blends_with_inverse_variance(self) -> None:
        """systematic_prior=0.5 with equal-variance estimates yields
        the same result as plain inverse-variance arbitration (because
        the inverse-variance weights are also 0.5/0.5)."""
        estimate = TwoSystemEstimate(
            model_free=QValueWithUncertainty(0.3, 0.05),
            model_based=QValueWithUncertainty(0.7, 0.05),
        )
        plain = uncertainty_weighted_arbitration(estimate)
        prior = arbitrate_with_processing_mode_prior(
            estimate, systematic_prior=0.5
        )
        assert plain.arbitrated_value == pytest.approx(
            prior.arbitrated_value, abs=1e-12
        )

    def test_full_systematic_prior_pulls_toward_model_based(self) -> None:
        """systematic_prior=1.0 maximally biases toward MB; with the
        0.5 blend the resulting MB weight is (0.5 * w_iv_MB + 0.5 * 1.0)
        — strictly greater than the plain inverse-variance weight when
        plain weight < 1.0."""
        estimate = TwoSystemEstimate(
            model_free=QValueWithUncertainty(0.0, 0.05),
            model_based=QValueWithUncertainty(1.0, 0.05),
        )
        plain = uncertainty_weighted_arbitration(estimate)
        prior = arbitrate_with_processing_mode_prior(
            estimate, systematic_prior=1.0,
        )
        assert prior.weight_model_based > plain.weight_model_based
        assert prior.arbitrated_value > plain.arbitrated_value

    def test_full_heuristic_prior_pulls_toward_model_free(self) -> None:
        estimate = TwoSystemEstimate(
            model_free=QValueWithUncertainty(0.0, 0.05),
            model_based=QValueWithUncertainty(1.0, 0.05),
        )
        plain = uncertainty_weighted_arbitration(estimate)
        prior = arbitrate_with_processing_mode_prior(
            estimate, systematic_prior=0.0,
        )
        assert prior.weight_model_free > plain.weight_model_free
        assert prior.arbitrated_value < plain.arbitrated_value

    def test_prior_preserves_arbitrated_variance(self) -> None:
        """The processing-mode prior is a re-weighting of the mean
        estimate only; the arbitrated variance reflects only the
        Bayesian inverse-variance combination."""
        estimate = TwoSystemEstimate(
            model_free=QValueWithUncertainty(0.0, 0.04),
            model_based=QValueWithUncertainty(1.0, 0.09),
        )
        plain = uncertainty_weighted_arbitration(estimate)
        for sp in [0.0, 0.25, 0.5, 0.75, 1.0]:
            prior = arbitrate_with_processing_mode_prior(
                estimate, systematic_prior=sp,
            )
            assert prior.arbitrated_variance == pytest.approx(
                plain.arbitrated_variance, rel=1e-12
            )

    def test_rejects_prior_outside_unit_interval(self) -> None:
        estimate = TwoSystemEstimate(
            model_free=QValueWithUncertainty(0.0, 0.04),
            model_based=QValueWithUncertainty(1.0, 0.09),
        )
        with pytest.raises(ValueError):
            arbitrate_with_processing_mode_prior(estimate, systematic_prior=-0.1)
        with pytest.raises(ValueError):
            arbitrate_with_processing_mode_prior(estimate, systematic_prior=1.1)
        with pytest.raises(ValueError):
            arbitrate_with_processing_mode_prior(
                estimate, systematic_prior=float("nan"),
            )


# ----------------------------------------------------------------------------
# Softmax action selection
# ----------------------------------------------------------------------------

class TestSoftmaxActionSelection:
    def test_uniform_when_equal_q(self) -> None:
        probs = softmax_action_selection([0.5, 0.5, 0.5], inverse_temperature=1.0)
        for p in probs:
            assert p == pytest.approx(1.0 / 3.0, abs=1e-12)

    def test_zero_temperature_yields_uniform(self) -> None:
        """β=0 collapses softmax to uniform regardless of Q-values."""
        probs = softmax_action_selection(
            [0.1, 0.5, 0.9], inverse_temperature=0.0,
        )
        for p in probs:
            assert p == pytest.approx(1.0 / 3.0, abs=1e-12)

    def test_high_temperature_concentrates_on_argmax(self) -> None:
        """β=20 should make the highest-Q action have ~all the
        probability mass."""
        probs = softmax_action_selection(
            [0.1, 0.5, 0.9], inverse_temperature=20.0,
        )
        assert probs.index(max(probs)) == 2  # 0.9 is the argmax
        assert max(probs) > 0.99

    def test_probabilities_sum_to_one(self) -> None:
        probs = softmax_action_selection(
            [0.1, 0.4, -0.2, 0.7, 0.0], inverse_temperature=2.5,
        )
        assert sum(probs) == pytest.approx(1.0, abs=1e-12)

    def test_numerically_stable_for_large_q(self) -> None:
        """Large Q-values × β must not overflow the exp."""
        probs = softmax_action_selection(
            [100.0, 200.0, 300.0], inverse_temperature=10.0,
        )
        assert sum(probs) == pytest.approx(1.0, abs=1e-12)
        # 300 * 10 dominates: argmax mass ≈ 1.
        assert probs[2] > 0.999

    def test_rejects_empty_actions(self) -> None:
        with pytest.raises(ValueError):
            softmax_action_selection([], inverse_temperature=1.0)

    def test_rejects_negative_temperature(self) -> None:
        with pytest.raises(ValueError):
            softmax_action_selection([0.5], inverse_temperature=-1.0)

    def test_rejects_non_finite_temperature(self) -> None:
        with pytest.raises(ValueError):
            softmax_action_selection([0.5], inverse_temperature=float("inf"))

    def test_rejects_non_finite_q(self) -> None:
        with pytest.raises(ValueError):
            softmax_action_selection(
                [0.5, float("nan")], inverse_temperature=1.0,
            )


# ----------------------------------------------------------------------------
# Integration: arbitration → action selection
# ----------------------------------------------------------------------------

class TestEndToEndComposition:
    def test_arbitrated_q_values_drive_action_selection(self) -> None:
        """Compose arbitration with softmax: two actions a1, a2 with
        per-system (Q, σ²) estimates. Arbitrate per-action; feed
        arbitrated values to softmax."""
        estimates = [
            # Action a1: MF says 0.2 (variance 0.05); MB says 0.6 (variance 0.05).
            TwoSystemEstimate(
                model_free=QValueWithUncertainty(0.2, 0.05),
                model_based=QValueWithUncertainty(0.6, 0.05),
            ),
            # Action a2: MF says 0.7 (variance 0.05); MB says 0.5 (variance 0.05).
            TwoSystemEstimate(
                model_free=QValueWithUncertainty(0.7, 0.05),
                model_based=QValueWithUncertainty(0.5, 0.05),
            ),
        ]
        arbitrated = [uncertainty_weighted_arbitration(e) for e in estimates]
        q_values = [a.arbitrated_value for a in arbitrated]
        # Action 1 arbitrated: 0.4; Action 2 arbitrated: 0.6.
        assert q_values[0] == pytest.approx(0.4, abs=1e-12)
        assert q_values[1] == pytest.approx(0.6, abs=1e-12)
        probs = softmax_action_selection(q_values, inverse_temperature=10.0)
        # Action 2 should be preferred (higher arbitrated Q).
        assert probs[1] > probs[0]
        assert probs[1] > 0.85

    def test_systematic_prior_can_flip_action_preference(self) -> None:
        """When MB values differ from MF values, a strong systematic
        prior can flip which action softmax prefers."""
        # MF prefers action 0 (Q_MF: 0.9 vs 0.1).
        # MB prefers action 1 (Q_MB: 0.1 vs 0.9).
        # With equal variance + neutral arbitration, q values average to 0.5
        # each → softmax is uniform over both actions.
        # With systematic_prior=1.0 (full MB), MB's preference dominates.
        estimates = [
            TwoSystemEstimate(
                model_free=QValueWithUncertainty(0.9, 0.05),
                model_based=QValueWithUncertainty(0.1, 0.05),
            ),
            TwoSystemEstimate(
                model_free=QValueWithUncertainty(0.1, 0.05),
                model_based=QValueWithUncertainty(0.9, 0.05),
            ),
        ]
        habitual = [
            arbitrate_with_processing_mode_prior(e, systematic_prior=0.0)
            for e in estimates
        ]
        deliberate = [
            arbitrate_with_processing_mode_prior(e, systematic_prior=1.0)
            for e in estimates
        ]
        habitual_q = [a.arbitrated_value for a in habitual]
        deliberate_q = [a.arbitrated_value for a in deliberate]
        # In habitual mode (prior=0), MF preference dominates → action 0
        # has higher arbitrated Q.
        assert habitual_q[0] > habitual_q[1]
        # In deliberate mode (prior=1), MB preference dominates → action 1
        # has higher arbitrated Q.
        assert deliberate_q[1] > deliberate_q[0]
        # Softmax responds correspondingly.
        habitual_probs = softmax_action_selection(
            habitual_q, inverse_temperature=10.0,
        )
        deliberate_probs = softmax_action_selection(
            deliberate_q, inverse_temperature=10.0,
        )
        assert habitual_probs[0] > habitual_probs[1]
        assert deliberate_probs[1] > deliberate_probs[0]
