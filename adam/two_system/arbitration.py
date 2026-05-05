"""Daw two-system arbitration (directive §1.G.SI.1).

Daw, Niv & Dayan (2005, *Nature Neuroscience* 8:1704–1711,
"Uncertainty-based competition between prefrontal and dorsolateral
striatal systems for behavioral control") propose that the brain
runs two reinforcement-learning systems in parallel:

  * **Model-free (MF).** Cached value estimates Q_MF(s, a) updated by
    temporal-difference learning. Fast, habit-like, low computational
    cost, but slow to update when contingencies change.
  * **Model-based (MB).** Forward simulation through a learned
    transition model T(s' | s, a) and reward function R(s, a) to
    compute Q_MB(s, a) on-the-fly. Slow, deliberative, high
    computational cost, but adapts immediately when contingencies
    change.

Both systems carry POSTERIOR UNCERTAINTY about their estimates.
Arbitration weights each system inversely to its uncertainty (i.e.,
Bayesian inverse-variance weighting):

    w_MF = σ²_MB / (σ²_MF + σ²_MB)
    w_MB = σ²_MF / (σ²_MF + σ²_MB)

The arbitrated estimate is the precision-weighted mean of the two:

    Q_arbitrated = w_MF * Q_MF + w_MB * Q_MB

with arbitrated posterior variance equal to the harmonic mean of
the component variances (the standard Gaussian-conjugate result):

    σ²_arbitrated = (σ²_MF * σ²_MB) / (σ²_MF + σ²_MB)
                  = 1 / (1/σ²_MF + 1/σ²_MB)

Action selection is Boltzmann (softmax) over the arbitrated value
estimates, parameterized by an inverse-temperature β:

    π(a | s) ∝ exp(β * Q_arbitrated(s, a))

ADAM application context (per directive §1.G mandate):
  * MF system ≈ bilateral cascade L1/L2/L3 cached-mechanism scores
    per archetype × cell × posture (already in production at
    `adam/api/stackadapt/bilateral_cascade.py`).
  * MB system ≈ forward simulation over the journey-state machine
    + per-archetype TherapeuticSequence (Surface 1 + Surface 2 of
    the §S2 retargeting audit).
  * Processing-mode prior (heuristic vs systematic) ≈ derived from
    cell classifier + journey-state metadata at the §1.G.SB.1
    substrate-blocked stage.

The SI stage (this slice) ships the abstract arbitration primitive
and the action-selection seam. The processing-mode prior enters via
`arbitrate_with_processing_mode_prior` — a thin wrapper that biases
the arbitration weights toward one system or the other based on a
[0, 1] prior weight (1.0 = full systematic / MB; 0.0 = full
heuristic / MF). The prior interpolates with the inverse-variance
arbitration: the SB stage can supply a context-derived prior weight
without dictating the arbitration math.

References:
  * Daw, Niv, Dayan 2005, *Nature Neuroscience* 8:1704–1711.
  * Lee, Shimojo, O'Doherty 2014, *Neuron* 81:687–699 (empirical
    validation of uncertainty-based arbitration in human fMRI).
  * Pinker 1999 *Words and Rules* — dual-mechanism theory composes
    with the same "two competing systems with dynamic arbitration"
    motif Chris's training surfaces; per CLAUDE.md user memory,
    Pinker's per-item automatization can override rules after
    enough reinforcement, exactly what the MF system models.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence, Tuple


__all__ = [
    "ArbitrationResult",
    "QValueWithUncertainty",
    "TwoSystemEstimate",
    "arbitrate_with_processing_mode_prior",
    "softmax_action_selection",
    "uncertainty_weighted_arbitration",
]


@dataclass(frozen=True)
class QValueWithUncertainty:
    """Posterior point estimate + variance for a single (state, action)
    Q-value.

    `value` is the mean; `variance` is the posterior variance (must
    be > 0; an estimate with zero variance is "infinitely confident,"
    which is degenerate for the Bayesian arbitration math)."""
    value: float
    variance: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.value):
            raise ValueError(f"value must be finite, got {self.value!r}")
        if not math.isfinite(self.variance):
            raise ValueError(f"variance must be finite, got {self.variance!r}")
        if self.variance <= 0:
            raise ValueError(
                f"variance must be strictly positive, got {self.variance!r}"
            )


@dataclass(frozen=True)
class TwoSystemEstimate:
    """A pair of (Q-value, variance) estimates from the model-free and
    model-based systems for the same (state, action)."""
    model_free: QValueWithUncertainty
    model_based: QValueWithUncertainty


@dataclass(frozen=True)
class ArbitrationResult:
    """Outcome of an arbitration step.

    `arbitrated_value` is the precision-weighted mean of the two
    component estimates; `arbitrated_variance` is the harmonic mean
    of the component variances (smaller than either component
    variance — the arbitration is strictly information-additive
    under the Gaussian-conjugate assumption).

    `weight_model_free` + `weight_model_based` always sum to 1.0;
    each weight is in [0, 1]."""
    arbitrated_value: float
    arbitrated_variance: float
    weight_model_free: float
    weight_model_based: float

    def __post_init__(self) -> None:
        sum_weights = self.weight_model_free + self.weight_model_based
        if not math.isclose(sum_weights, 1.0, abs_tol=1e-9):
            raise ValueError(
                f"weights must sum to 1.0, got "
                f"{self.weight_model_free!r} + {self.weight_model_based!r} = "
                f"{sum_weights!r}"
            )


def uncertainty_weighted_arbitration(
    estimate: TwoSystemEstimate,
) -> ArbitrationResult:
    """Bayesian inverse-variance arbitration of two Q-value estimates.

    Implements:
        precision_MF = 1 / σ²_MF;  precision_MB = 1 / σ²_MB
        Q_arbitrated = (precision_MF * Q_MF + precision_MB * Q_MB)
                       / (precision_MF + precision_MB)
        σ²_arbitrated = 1 / (precision_MF + precision_MB)
                      = (σ²_MF * σ²_MB) / (σ²_MF + σ²_MB)

    The weight on each system is its posterior precision share:
        w_MF = precision_MF / (precision_MF + precision_MB)
             = σ²_MB / (σ²_MF + σ²_MB)
        w_MB = 1 - w_MF
    """
    p_mf = 1.0 / estimate.model_free.variance
    p_mb = 1.0 / estimate.model_based.variance
    total_precision = p_mf + p_mb

    arbitrated_value = (
        p_mf * estimate.model_free.value
        + p_mb * estimate.model_based.value
    ) / total_precision
    arbitrated_variance = 1.0 / total_precision
    weight_mf = p_mf / total_precision
    weight_mb = p_mb / total_precision

    return ArbitrationResult(
        arbitrated_value=arbitrated_value,
        arbitrated_variance=arbitrated_variance,
        weight_model_free=weight_mf,
        weight_model_based=weight_mb,
    )


def arbitrate_with_processing_mode_prior(
    estimate: TwoSystemEstimate,
    *,
    systematic_prior: float,
) -> ArbitrationResult:
    """Arbitration biased by an exogenous processing-mode prior.

    The substrate-blocked §1.G.SB.1 stage supplies a context-derived
    prior weight (1.0 = systematic / MB-favored; 0.5 = neutral; 0.0
    = heuristic / MF-favored) inferred from the cell classifier +
    journey-state machine. The prior linearly interpolates with the
    inverse-variance arbitration weight:

        w_MB_combined = (1 - λ) * w_MB_inverse_variance + λ * systematic_prior
        w_MF_combined = 1 - w_MB_combined

    where λ controls the prior's relative influence; the closed-form
    here uses λ = 0.5 by convention (equal trust in inverse-variance
    arbitration and exogenous prior). The arbitrated value uses the
    combined weights; the arbitrated variance uses the unmodified
    inverse-variance result (the prior re-weights the mean estimate
    but does not re-weight precision).

    Implementation note: a fully-Bayesian alternative would treat
    `systematic_prior` as a Beta-prior on w_MB, but that requires
    committing to a specific prior strength which is exactly the
    knob §1.G.SB.1 will calibrate empirically. The linear-blend
    here is the discipline-conservative SI-stage choice — it
    exposes the seam without prescribing the calibration.
    """
    if not math.isfinite(systematic_prior):
        raise ValueError(
            f"systematic_prior must be finite, got {systematic_prior!r}"
        )
    if not 0.0 <= systematic_prior <= 1.0:
        raise ValueError(
            f"systematic_prior must be in [0, 1], got {systematic_prior!r}"
        )

    inverse_variance = uncertainty_weighted_arbitration(estimate)
    blend_lambda = 0.5
    weight_mb_combined = (
        (1.0 - blend_lambda) * inverse_variance.weight_model_based
        + blend_lambda * systematic_prior
    )
    weight_mf_combined = 1.0 - weight_mb_combined

    arbitrated_value = (
        weight_mf_combined * estimate.model_free.value
        + weight_mb_combined * estimate.model_based.value
    )
    return ArbitrationResult(
        arbitrated_value=arbitrated_value,
        arbitrated_variance=inverse_variance.arbitrated_variance,
        weight_model_free=weight_mf_combined,
        weight_model_based=weight_mb_combined,
    )


def softmax_action_selection(
    action_q_values: Sequence[float],
    *,
    inverse_temperature: float,
) -> Tuple[float, ...]:
    """Boltzmann (softmax) policy: π(a | s) ∝ exp(β * Q(s, a)).

    Numerically stable: subtracts max(Q) before exponentiation.
    Larger `inverse_temperature` (β) sharpens the policy toward the
    greedy action; β → 0 collapses to uniform; β → ∞ collapses to
    argmax (deterministic).

    Returns a tuple of probabilities summing to 1.0.
    """
    if not math.isfinite(inverse_temperature):
        raise ValueError(
            f"inverse_temperature must be finite, got {inverse_temperature!r}"
        )
    if inverse_temperature < 0:
        raise ValueError(
            f"inverse_temperature must be non-negative, got "
            f"{inverse_temperature!r}"
        )
    if not action_q_values:
        raise ValueError("action_q_values must be non-empty")
    for q in action_q_values:
        if not math.isfinite(q):
            raise ValueError(f"action_q_values must be finite, got {q!r}")

    if inverse_temperature == 0.0:
        n = len(action_q_values)
        return tuple(1.0 / n for _ in action_q_values)

    scaled = [inverse_temperature * q for q in action_q_values]
    max_scaled = max(scaled)
    exps = [math.exp(s - max_scaled) for s in scaled]
    total = sum(exps)
    return tuple(e / total for e in exps)
