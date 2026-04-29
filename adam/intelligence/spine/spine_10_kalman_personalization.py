# =============================================================================
# ADAM Spine #10 — Online Kalman State-Space Personalization
# Location: adam/intelligence/spine/spine_10_kalman_personalization.py
# =============================================================================

"""Online Kalman state-space personalization wrapping Spine #1.

PER DIRECTIVE SECTION 2 (Spine #10).

Each user's mechanism-effect parameters drift over time (mood, day-of-
week, life-event transitions). Model the per-user latent state as a
slow random walk with Kalman-filter updates per observation. The
forgetting coefficient is itself learned online (parameter-drift
transition density).

Runs *on top of* Spine #1's hierarchical Bayesian engine — the Kalman
layer is the non-stationary state-evolution model, while Spine #1
provides the within-time-slice posterior structure.

WHY THIS IS SPINE

Per directive: "Stationary priors are wrong in B2B-travel where intent
is event-driven. Without state-space drift modeling, the system locks
onto stale-grabby-creative that worked once and cannot transition to
the user's evolved state. Kalman is the right tool for linear-Gaussian
state-space (Titsias et al. style); for non-Gaussian, particle-filter
fallback. At 27-dimensional construct space, full-covariance Kalman
is trivially storable per user."

THE MATH

State-space model:
    State: θ_i,t is the per-user posterior mean at time t
    Transition: θ_i,t+1 = θ_i,t + ε_t, ε_t ~ N(0, Q_i)
    Observation: each impression's outcome conditions on θ_i,t

Q_i is the per-user process noise matrix (learned). Large Q_i =
high non-stationarity (state changes fast); small Q_i = stable.

Integration with Spine #1:
    Between observations: Kalman prediction step inflates the
        precision matrix by Q_i⁻¹ (relaxes the precision toward
        the prior — "we know less now than we did before because
        time has passed")
    On observation: Spine #1 BONG performs the natural-gradient
        update on the inflated prior

DECISION-TIME CONSUMERS (Rule A check)

  - Spine #1 wraps with Kalman: between-observation prediction step
    inflates precision before BONG update. The decision-time effective
    prior reads from the Kalman-inflated UserPosterior.
  - Spine #6 DecisionTrace records the Kalman-inflated posterior
    snapshot for partner audit
  - Spine #4 trilateral cascade reads the same Kalman-inflated
    posterior at decision time

Cognitive primitive at the serving path. NOT measurement.

THIS COMMIT SHIPS

    - kalman_predict_step: inflate precision by Q⁻¹ between observations
    - default_process_noise_matrix: identity-Q with configurable scale
      (calibration-pending; learned via empirical-Bayes per user)
    - learn_process_noise_from_residuals: empirical-Bayes Q estimate
    - integrate_with_bong_update: convenience function that does
      predict_step then BONG update (the canonical decision-time path)

THIS COMMIT DOES NOT SHIP (follow-on commits)

    - Particle-filter fallback for non-Gaussian state-space (rare)
    - Full hierarchical Q hyperprior reconciliation (offline pipeline
      Spine #12 task)

REFERENCES

    Kalman 1960 — A New Approach to Linear Filtering.
    Titsias et al. — variational state-space.
    Particle filters for non-Gaussian extensions (deferred).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import List, Optional

from adam.intelligence.spine.spine_1_n_of_1_engine import (
    USER_POSTERIOR_DIM,
    UserPosterior,
    bong_update_step,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration constants
# =============================================================================


# Default process noise scale. Per directive: "effective half-life ~14
# days for B2B intent." With observations at ~1/day cadence, a process-
# noise scale that gives ~14-day half-life on the precision: at scale
# σ_Q² = 1/14, the precision relaxes by exp(-Δt / 14) per day.
#
# In the natural-parameter inflation: Λ_predicted = (Λ_old⁻¹ + Q)⁻¹
#                                                ≈ Λ_old · (I − Q · Λ_old)
# For diagonal Q with scale q on the diagonal:
#   Λ_predicted_diag ≈ Λ_old_diag / (1 + q · Λ_old_diag)
#
# Interpretation: high precision diagonals decay faster (more "knowing
# less" over time), low precision diagonals decay slowly.
DEFAULT_PROCESS_NOISE_SCALE: float = 0.01


# Per directive: "effective half-life ~14 days for B2B intent."
DEFAULT_TARGET_HALF_LIFE_DAYS: float = 14.0


# Process-noise learning rate (empirical-Bayes update step).
DEFAULT_Q_LEARNING_RATE: float = 0.05


# =============================================================================
# Process-noise matrix
# =============================================================================


def default_process_noise_diagonal(
    dim: int = USER_POSTERIOR_DIM,
    scale: float = DEFAULT_PROCESS_NOISE_SCALE,
) -> List[float]:
    """Return a diagonal process-noise matrix Q as a flat diagonal vector.

    Default: identity scaled by `scale`. Per directive Section 3.2,
    full-covariance Kalman is trivially storable at d=27 — but the
    diagonal-Q approximation is sufficient for the substrate; full-
    covariance can be used in production if non-trivial cross-
    dimensional drift is observed.

    Returns a list of `dim` floats representing Q's diagonal.
    """
    if dim <= 0:
        raise ValueError(f"dim must be positive; got {dim}")
    if scale <= 0.0:
        raise ValueError(f"scale must be positive; got {scale}")
    return [scale] * dim


def half_life_to_process_noise_scale(
    target_half_life_days: float = DEFAULT_TARGET_HALF_LIFE_DAYS,
    observations_per_day: float = 1.0,
    typical_precision: float = 1.0,
) -> float:
    """Convert a desired effective half-life into a process-noise scale.

    Heuristic: at typical_precision λ and observation rate ω, the
    half-life of the precision under iterated Kalman prediction (no
    new observations) approximately satisfies:
        λ(t) ≈ λ_0 / (1 + q · λ_0 · t)
    Half-life: t_½ such that λ(t_½) = λ_0 / 2 →
        q ≈ 1 / (λ_0 · t_½)

    Returns a scale value suitable for default_process_noise_diagonal.
    """
    if target_half_life_days <= 0.0:
        raise ValueError(
            f"target_half_life_days must be positive; got {target_half_life_days}"
        )
    if observations_per_day <= 0.0:
        raise ValueError(
            f"observations_per_day must be positive; got {observations_per_day}"
        )
    if typical_precision <= 0.0:
        raise ValueError(
            f"typical_precision must be positive; got {typical_precision}"
        )
    # Convert half-life from days to "observation steps".
    half_life_steps = target_half_life_days * observations_per_day
    return 1.0 / (typical_precision * half_life_steps)


# =============================================================================
# Kalman prediction step (between-observation precision inflation)
# =============================================================================


def kalman_predict_step(
    posterior: UserPosterior,
    process_noise_diagonal: Optional[List[float]] = None,
    elapsed_steps: float = 1.0,
) -> UserPosterior:
    """Apply the Kalman prediction step to a UserPosterior.

    Between observations, the user's true state may have drifted; the
    posterior precision should DECREASE (we know less now). The
    natural-parameter form makes this explicit:

        Λ_predicted = (Λ_old⁻¹ + Q · elapsed_steps)⁻¹

    For diagonal Q with element q_i on dimension i:
        Λ_predicted_diag_i ≈ Λ_old_diag_i / (1 + q_i · Λ_old_diag_i · elapsed_steps)

    The off-diagonals of Λ are scaled by the same factor as the diagonal
    (approximation). This is the "shrink toward the prior" Kalman
    prediction in the natural-parameter representation.

    The precision-weighted mean η scales by the same factor:
        η_predicted = η_old · (Λ_predicted / Λ_old)

    This preserves μ = Λ⁻¹ η across the prediction step (drift in mean
    is captured by the increased uncertainty, not by shifting the mean).

    Args:
        posterior: the current UserPosterior (natural-parameter form)
        process_noise_diagonal: per-dimension Q diagonal; defaults to
            DEFAULT_PROCESS_NOISE_SCALE on every dim
        elapsed_steps: number of observation-steps since last update;
            defaults to 1.0 (one step)

    Returns a new UserPosterior with predicted (relaxed) precision +
    rescaled η.
    """
    d = posterior.dim
    if process_noise_diagonal is None:
        process_noise_diagonal = default_process_noise_diagonal(d)
    if len(process_noise_diagonal) != d:
        raise ValueError(
            f"process_noise_diagonal length must be dim = {d}; "
            f"got {len(process_noise_diagonal)}"
        )
    if elapsed_steps <= 0.0:
        return posterior  # No-op for non-positive elapsed time

    # Compute new diagonal scaling factor per dimension.
    new_precision = list(posterior.precision_matrix_flat)
    new_eta = list(posterior.precision_weighted_mean)

    # For each diagonal element: λ_new = λ_old / (1 + q·λ_old·elapsed)
    for i in range(d):
        diag_idx = i * d + i
        old_diag = posterior.precision_matrix_flat[diag_idx]
        if old_diag <= 0.0:
            continue
        q_i = process_noise_diagonal[i]
        denom = 1.0 + q_i * old_diag * elapsed_steps
        new_diag = old_diag / denom

        # Scale entire row + column by new_diag / old_diag (preserves
        # cross-dim correlations approximately).
        if old_diag > 0.0:
            scale = new_diag / old_diag
            for j in range(d):
                new_precision[i * d + j] *= scale
                if i != j:
                    new_precision[j * d + i] *= scale
            # Rescale η[i] correspondingly so μ = Λ⁻¹ η preserved.
            new_eta[i] *= scale

    return posterior.model_copy(update={
        "precision_matrix_flat": new_precision,
        "precision_weighted_mean": new_eta,
    })


# =============================================================================
# Composed predict-then-BONG step (canonical decision-time path)
# =============================================================================


def kalman_predict_then_bong_update(
    posterior: UserPosterior,
    feature_vector: List[float],
    outcome_value: float,
    outcome_class: str,
    *,
    process_noise_diagonal: Optional[List[float]] = None,
    elapsed_steps: float = 1.0,
) -> UserPosterior:
    """Predict-then-update: the canonical sequence per directive.

    Per Section 3.2 + Spine #10: "the Kalman layer wraps the BONG
    natural-gradient updates — between observations, the Kalman
    prediction step inflates the precision matrix by Q_i⁻¹; on
    observation, BONG performs the natural-gradient update on the
    inflated prior."

    Returns the updated UserPosterior after both steps.
    """
    predicted = kalman_predict_step(
        posterior=posterior,
        process_noise_diagonal=process_noise_diagonal,
        elapsed_steps=elapsed_steps,
    )
    return bong_update_step(
        posterior=predicted,
        feature_vector=feature_vector,
        outcome_value=outcome_value,
        outcome_class=outcome_class,
    )


# =============================================================================
# Process-noise empirical-Bayes update
# =============================================================================


def learn_process_noise_from_residual(
    current_q_diagonal: List[float],
    residual_per_dim: List[float],
    *,
    learning_rate: float = DEFAULT_Q_LEARNING_RATE,
) -> List[float]:
    """Online empirical-Bayes update of the process-noise diagonal.

    When an observation arrives, the residual between the predicted
    state and the observed outcome reveals how non-stationary the
    state is. Large residuals → increase Q (more drift expected);
    small residuals → decrease Q (state is stable).

    Update rule:
        q_new[i] = (1 - lr) · q_old[i] + lr · residual[i]²

    Args:
        current_q_diagonal: existing per-dim Q diagonal
        residual_per_dim: residual on each dim from the most recent
            observation (per-dim difference between predicted and
            observed feature contribution)
        learning_rate: empirical-Bayes step size (in [0, 1])

    Returns updated Q diagonal.
    """
    if len(current_q_diagonal) != len(residual_per_dim):
        raise ValueError(
            f"current_q_diagonal and residual_per_dim must have same "
            f"length; got {len(current_q_diagonal)} vs "
            f"{len(residual_per_dim)}"
        )
    if not 0.0 <= learning_rate <= 1.0:
        raise ValueError(f"learning_rate must be in [0, 1]; got {learning_rate}")

    return [
        max(1e-6, (1.0 - learning_rate) * q + learning_rate * (r * r))
        for q, r in zip(current_q_diagonal, residual_per_dim)
    ]


__all__ = [
    "DEFAULT_PROCESS_NOISE_SCALE",
    "DEFAULT_TARGET_HALF_LIFE_DAYS",
    "DEFAULT_Q_LEARNING_RATE",
    "default_process_noise_diagonal",
    "half_life_to_process_noise_scale",
    "kalman_predict_step",
    "kalman_predict_then_bong_update",
    "learn_process_noise_from_residual",
]
