"""Tests for Spine #10 — Online Kalman State-Space Personalization.

Pins per directive Section 2 (Spine #10):
    1. default_process_noise_diagonal: identity-Q with configurable scale
    2. half_life_to_process_noise_scale: 14-day → reasonable scale
    3. kalman_predict_step: precision DECREASES (state more uncertain
       after time passes); μ = Λ⁻¹η preserved
    4. Higher Q → faster precision decay
    5. More elapsed time → more precision decay
    6. kalman_predict_then_bong_update: composed predict-then-update;
       end posterior reflects both drift and observation
    7. learn_process_noise_from_residual: large residuals → larger Q;
       small residuals → smaller Q
"""

from __future__ import annotations

import math

import pytest

from adam.intelligence.spine.spine_1_n_of_1_engine import (
    USER_POSTERIOR_DIM,
    bong_update_step,
    init_user_posterior,
    natural_to_standard,
)
from adam.intelligence.spine.spine_10_kalman_personalization import (
    DEFAULT_PROCESS_NOISE_SCALE,
    DEFAULT_TARGET_HALF_LIFE_DAYS,
    default_process_noise_diagonal,
    half_life_to_process_noise_scale,
    kalman_predict_step,
    kalman_predict_then_bong_update,
    learn_process_noise_from_residual,
)


# -----------------------------------------------------------------------------
# Process-noise matrix helpers
# -----------------------------------------------------------------------------


class TestProcessNoiseHelpers:

    def test_default_diagonal_correct_length(self):
        q = default_process_noise_diagonal()
        assert len(q) == USER_POSTERIOR_DIM
        assert all(v == DEFAULT_PROCESS_NOISE_SCALE for v in q)

    def test_custom_dim_and_scale(self):
        q = default_process_noise_diagonal(dim=5, scale=0.5)
        assert q == [0.5, 0.5, 0.5, 0.5, 0.5]

    def test_invalid_dim_rejected(self):
        with pytest.raises(ValueError, match="dim"):
            default_process_noise_diagonal(dim=0)

    def test_invalid_scale_rejected(self):
        with pytest.raises(ValueError, match="scale"):
            default_process_noise_diagonal(scale=0.0)

    def test_half_life_conversion_returns_positive(self):
        scale = half_life_to_process_noise_scale(14.0)
        assert scale > 0
        # 1 / (1 · 14) = 0.0714...
        assert scale == pytest.approx(1.0 / 14.0)

    def test_shorter_half_life_larger_scale(self):
        s_short = half_life_to_process_noise_scale(7.0)
        s_long = half_life_to_process_noise_scale(28.0)
        # Shorter half-life → higher process noise (more drift expected)
        assert s_short > s_long

    def test_invalid_half_life_rejected(self):
        with pytest.raises(ValueError, match="target_half_life_days"):
            half_life_to_process_noise_scale(0.0)


# -----------------------------------------------------------------------------
# Kalman prediction step
# -----------------------------------------------------------------------------


class TestKalmanPredictStep:

    def test_precision_decreases_after_predict(self):
        """The predict step inflates uncertainty: precision diagonals
        decrease after an elapsed step (no new observation)."""
        # Start with a posterior that has been updated from population.
        p0 = init_user_posterior(user_id="u")
        # Add an observation to make the precision non-trivial.
        x = [0.0] * USER_POSTERIOR_DIM
        x[0] = 1.0
        p1 = bong_update_step(p0, x, outcome_value=1.0,
                              outcome_class="CONVERSION")
        # p1 has Λ[0,0] = 1.0 + 1·1·1 = 2.0
        assert p1.precision_matrix_flat[0] == pytest.approx(2.0)

        # Now apply the predict step.
        p2 = kalman_predict_step(p1)
        # After predict, Λ[0,0] should be LESS than 2.0 (precision dropped).
        assert p2.precision_matrix_flat[0] < p1.precision_matrix_flat[0]
        # And > 0.
        assert p2.precision_matrix_flat[0] > 0.0

    def test_predict_preserves_posterior_mean_approximately(self):
        """μ = Λ⁻¹ η. After predict step, both Λ and η scale by the
        same factor on each dim, so μ is preserved."""
        p0 = init_user_posterior(user_id="u")
        x = [0.0] * USER_POSTERIOR_DIM
        x[0] = 1.0
        p1 = bong_update_step(p0, x, outcome_value=1.0,
                              outcome_class="CONVERSION")
        mu_before, _ = natural_to_standard(p1)

        p2 = kalman_predict_step(p1)
        mu_after, _ = natural_to_standard(p2)

        # μ should be approximately preserved (drift in mean is captured
        # via uncertainty, not by shifting the mean).
        for i in range(USER_POSTERIOR_DIM):
            assert mu_before[i] == pytest.approx(mu_after[i], abs=1e-6)

    def test_higher_q_faster_decay(self):
        p0 = init_user_posterior(user_id="u")
        x = [0.0] * USER_POSTERIOR_DIM
        x[0] = 1.0
        p1 = bong_update_step(p0, x, outcome_value=1.0,
                              outcome_class="CONVERSION")

        # Low Q
        q_low = [0.01] * USER_POSTERIOR_DIM
        p_low = kalman_predict_step(p1, process_noise_diagonal=q_low)

        # High Q
        q_high = [0.5] * USER_POSTERIOR_DIM
        p_high = kalman_predict_step(p1, process_noise_diagonal=q_high)

        # High Q decays the precision more aggressively.
        assert p_high.precision_matrix_flat[0] < p_low.precision_matrix_flat[0]

    def test_more_elapsed_steps_more_decay(self):
        p0 = init_user_posterior(user_id="u")
        x = [0.0] * USER_POSTERIOR_DIM
        x[0] = 1.0
        p1 = bong_update_step(p0, x, outcome_value=1.0,
                              outcome_class="CONVERSION")

        p_one_step = kalman_predict_step(p1, elapsed_steps=1.0)
        p_ten_steps = kalman_predict_step(p1, elapsed_steps=10.0)

        # 10 steps of elapsed time → much more decay
        assert p_ten_steps.precision_matrix_flat[0] < p_one_step.precision_matrix_flat[0]

    def test_zero_elapsed_no_op(self):
        p1 = init_user_posterior(user_id="u")
        # Add observation
        x = [0.0] * USER_POSTERIOR_DIM
        x[0] = 1.0
        p1 = bong_update_step(p1, x, outcome_value=1.0,
                              outcome_class="CONVERSION")
        p2 = kalman_predict_step(p1, elapsed_steps=0.0)
        # No-op: posterior unchanged.
        assert p2.precision_matrix_flat == p1.precision_matrix_flat
        assert p2.precision_weighted_mean == p1.precision_weighted_mean

    def test_process_noise_dim_mismatch_raises(self):
        p1 = init_user_posterior(user_id="u")
        with pytest.raises(ValueError, match="process_noise_diagonal"):
            kalman_predict_step(
                p1, process_noise_diagonal=[0.1, 0.1],  # wrong length
            )


# -----------------------------------------------------------------------------
# Composed predict-then-update
# -----------------------------------------------------------------------------


class TestKalmanPredictThenBong:

    def test_composed_step_executes_both(self):
        """The canonical decision-time path: predict (drift) then
        BONG update (observation). End posterior reflects both."""
        p0 = init_user_posterior(user_id="u")
        x = [0.0] * USER_POSTERIOR_DIM
        x[0] = 1.0

        # First observation establishes a posterior.
        p1 = bong_update_step(p0, x, outcome_value=1.0,
                              outcome_class="CONVERSION")
        # 7 days pass, then second observation.
        p2 = kalman_predict_then_bong_update(
            p1, x, outcome_value=1.0,
            outcome_class="CONVERSION",
            elapsed_steps=7.0,
        )
        # p2's precision should be > p1's precision (BONG updated)
        # but the precision INCREMENT from p1 → p2 is smaller than
        # if we had used a fresh BONG update without the predict step
        # (because the predict step decayed the precision first).
        p2_no_kalman = bong_update_step(
            p1, x, outcome_value=1.0, outcome_class="CONVERSION",
        )
        # p2_no_kalman precision[0,0] = 2.0 + 1.0 = 3.0
        # p2 precision[0,0] = (decayed_from_2.0) + 1.0 < 3.0
        assert p2.precision_matrix_flat[0] < p2_no_kalman.precision_matrix_flat[0]
        # observation count incremented in both.
        assert p2.total_observations == p1.total_observations + 1


# -----------------------------------------------------------------------------
# Empirical-Bayes process-noise update
# -----------------------------------------------------------------------------


class TestLearnProcessNoiseFromResidual:

    def test_large_residuals_increase_q(self):
        q_old = [0.1, 0.1, 0.1]
        residuals_large = [1.0, 1.0, 1.0]  # |residual| = 1
        q_new = learn_process_noise_from_residual(
            q_old, residuals_large, learning_rate=0.5,
        )
        # q_new = 0.5·0.1 + 0.5·1² = 0.55
        assert q_new[0] == pytest.approx(0.55)
        # All dims updated.
        for q in q_new:
            assert q > q_old[0]

    def test_small_residuals_pull_q_down(self):
        q_old = [1.0, 1.0, 1.0]
        residuals_small = [0.1, 0.1, 0.1]
        q_new = learn_process_noise_from_residual(
            q_old, residuals_small, learning_rate=0.5,
        )
        # q_new = 0.5·1.0 + 0.5·0.01 = 0.505
        assert q_new[0] == pytest.approx(0.505)
        # All dims updated downward.
        for q in q_new:
            assert q < q_old[0]

    def test_dimension_mismatch_raises(self):
        with pytest.raises(ValueError, match="same length"):
            learn_process_noise_from_residual([0.1, 0.1], [0.5])

    def test_invalid_learning_rate_rejected(self):
        with pytest.raises(ValueError, match="learning_rate"):
            learn_process_noise_from_residual([0.1], [0.5], learning_rate=1.5)

    def test_q_floored_above_zero(self):
        """Even with zero residuals, Q should never decay to zero."""
        q_old = [0.001, 0.001]
        residuals = [0.0, 0.0]
        q_new = learn_process_noise_from_residual(
            q_old, residuals, learning_rate=0.999,
        )
        # q_new = 0.001·0.001 + 0.999·0 ≈ near-zero, but floored
        assert all(q >= 1e-6 for q in q_new)
