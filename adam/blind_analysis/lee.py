"""Gross-Vitells look-elsewhere effect (LEE) trial-factor (directive §1.A.SI.2).

When the same test statistic is evaluated at many parameter points (the
"look-elsewhere" — many candidate creative × cell × cohort × posture
combinations), the local p-value at any single point understates the
chance of seeing an extreme value SOMEWHERE on the grid by chance. The
trial factor TF(z) corrects for this:

    TF(z) = p_global(z) / p_local(z)

The closed-form expression follows Gross & Vitells (2010,
*Eur. Phys. J. C* 70:525–530, "Trial factors for the look elsewhere
effect in high energy physics"). For a 1-d parameter scan with
chi-squared-distributed test statistic q = z², they derive

    p_global(z) ≈ p_local(z) + ⟨N(z_ref)⟩ * exp(-(z² - z_ref²) / 2)        (1)

where ⟨N(z_ref)⟩ is the expected number of upcrossings of the test
statistic across a low reference threshold u_ref = z_ref². Davies
(1987, *Biometrika* 74:33–43) supplies the asymptotic form for the
upcrossings expectation: for k = 1 (one-dimensional scan),

    ⟨N(c)⟩ ≈ ⟨N(c_ref)⟩ * exp(-(c - c_ref) / 2)                            (2)

so the trial factor is fully determined by a single empirically
calibrated parameter ⟨N(z_ref)⟩ (the upcrossings rate at the chosen
reference threshold).

ASYMPTOTIC LINEARITY (the directive's specific claim — `§1.A.SI.2`):
For large local-z, p_local(z) ≈ φ(z) / z = (1/√(2π)) * (1/z) *
exp(-z²/2), so

    TF(z) ≈ 1 + ⟨N(z_ref)⟩ * exp(z_ref²/2) * √(2π) * z                     (3)

i.e. the trial factor is asymptotically LINEAR in the fixed-mass
local significance z. Equation (3) is what
`gross_vitells_trial_factor` returns; the test-suite parametrization
verifies that (TF(z) − 1) / z converges to ⟨N(z_ref)⟩ * exp(z_ref²/2)
* √(2π) at large z.

Monte-Carlo cross-check (`monte_carlo_global_p_value`): generate
synthetic Gaussian random fields on a 1-d grid (squared-exponential
covariance with calibrated correlation length), compute the
maximum-z over the grid for each trial, and emit the empirical
distribution of maxima. The empirical p_global at threshold z* is
the fraction of trials whose max-z exceeds z*. This is the
non-asymptotic ground truth that the closed-form (1) must agree
with for large z.

`empirical_upcrossings_at_threshold` is the reciprocal calibration
helper — it counts upcrossings at a chosen reference z_ref in the
same MC ensemble, which then feeds the closed-form trial factor.

The pre-registration discipline of §1.A.SI.1 composes with §1.A.SI.2:
when the placeholder NULL data generator
(`placeholder_data_generator`) seeds many independent runs over the
sealed box's parameter grid, the empirical Type-I error rate at the
box's `decision_threshold` is exactly what equation (1) predicts.
The two slices together form the closed loop: pre-register a box
(SI.1) → predict false-discovery rate at its threshold via the
trial factor (SI.2) → apply to live signal claims after authorized
unblinding (SB.1, deferred until S5 closes per directive §1.A.SB.1).

References:
  * Gross & Vitells 2010, *Eur. Phys. J. C* 70:525–530.
  * Davies 1987, *Biometrika* 74:33–43.
  * Lyons 2008, *Annals of Applied Statistics* 2:887–915 (blind
    analysis as discipline against multiple-comparisons bias).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Sequence, Tuple

import numpy as np
from scipy.special import erfc


__all__ = [
    "MonteCarloLEEResult",
    "gross_vitells_global_p_value",
    "gross_vitells_trial_factor",
    "p_local_one_sided",
    "monte_carlo_global_p_value",
    "empirical_upcrossings_at_threshold",
]


# ----------------------------------------------------------------------------
# Closed-form (Gross-Vitells 2010 + Davies 1987)
# ----------------------------------------------------------------------------

def p_local_one_sided(local_z: float) -> float:
    """One-sided local p-value for a Gaussian test statistic.

    p_local(z) = P(Z > z) where Z ~ N(0, 1)
                = (1/2) * erfc(z / √2)

    No normalization for the look-elsewhere effect — this is the
    `p_local` factor in TF(z) = p_global(z) / p_local(z).
    """
    if not math.isfinite(local_z):
        raise ValueError(f"local_z must be finite, got {local_z!r}")
    return 0.5 * erfc(local_z / math.sqrt(2.0))


def gross_vitells_global_p_value(
    local_z: float,
    upcrossings_at_reference: float,
    *,
    reference_z: float = 0.0,
) -> float:
    """Closed-form global p-value with Gross-Vitells LEE correction.

    Implements equation (1) of the module docstring:

        p_global(z) = p_local(z) + ⟨N(z_ref)⟩ * exp(-(z² - z_ref²) / 2)

    Parameters
    ----------
    local_z
        Observed local significance in standard-normal sigma units
        (one-sided).
    upcrossings_at_reference
        Expected number of upcrossings of the test statistic across
        the reference threshold z_ref². Must be ≥ 0. Calibrated from
        Monte Carlo (`empirical_upcrossings_at_threshold`) or from
        the geometric properties of the search grid (Davies 1987).
    reference_z
        Reference threshold for the upcrossings calibration, in
        sigma units. Default 0 (count upcrossings of the random
        field across zero).

    Returns
    -------
    float in [0, 1]; saturates at 1.0 when the LEE correction would
    push the estimate past 1.

    Notes
    -----
    The closed form is asymptotic; for very small `local_z` (less
    than `reference_z`) the equation degrades. We saturate at 1.0
    to keep the return value a valid probability.
    """
    if upcrossings_at_reference < 0:
        raise ValueError(
            f"upcrossings_at_reference must be non-negative, "
            f"got {upcrossings_at_reference!r}"
        )
    if not math.isfinite(reference_z):
        raise ValueError(f"reference_z must be finite, got {reference_z!r}")

    p_local = p_local_one_sided(local_z)
    delta_chi_squared = local_z**2 - reference_z**2
    upcrossings_term = upcrossings_at_reference * math.exp(-delta_chi_squared / 2.0)
    return min(1.0, p_local + upcrossings_term)


def gross_vitells_trial_factor(
    local_z: float,
    upcrossings_at_reference: float,
    *,
    reference_z: float = 0.0,
) -> float:
    """Trial factor TF(z) = p_global(z) / p_local(z).

    Asymptotically TF(z) → ⟨N(z_ref)⟩ * exp(z_ref² / 2) * √(2π) * z
    + 1 for large local_z (equation (3) of the module docstring).
    The directive §1.A.SI.2 names this asymptotic linearity in
    fixed-mass significance as the test-suite parametrization
    target.
    """
    p_local = p_local_one_sided(local_z)
    if p_local <= 0.0:
        return float("inf")
    p_global = gross_vitells_global_p_value(
        local_z,
        upcrossings_at_reference,
        reference_z=reference_z,
    )
    return p_global / p_local


# ----------------------------------------------------------------------------
# Monte-Carlo cross-check
# ----------------------------------------------------------------------------

@dataclass(frozen=True)
class MonteCarloLEEResult:
    """Empirical look-elsewhere statistics from a synthetic Gaussian-process
    ensemble.

    `n_trials` random fields were generated on `n_grid_points` parameter
    locations under the null hypothesis. `max_z_per_trial[i]` is the
    maximum z-statistic observed in trial `i`; `upcrossings_at_zero` is
    the per-trial average number of upward zero-crossings (the
    empirical estimate of ⟨N(0)⟩).
    """
    n_trials: int
    n_grid_points: int
    correlation_length: float
    max_z_per_trial: Tuple[float, ...]
    upcrossings_at_zero: float

    def empirical_p_global(self, threshold_z: float) -> float:
        """Fraction of trials whose maximum-z exceeded `threshold_z`."""
        if self.n_trials == 0:
            return 0.0
        n_above = sum(1 for m in self.max_z_per_trial if m > threshold_z)
        return n_above / self.n_trials


def _squared_exponential_covariance(
    grid: np.ndarray, correlation_length: float,
) -> np.ndarray:
    """k(x_i, x_j) = exp(-(x_i - x_j)² / (2 * ℓ²))."""
    diffs = grid[:, None] - grid[None, :]
    return np.exp(-(diffs**2) / (2.0 * correlation_length**2))


def monte_carlo_global_p_value(
    *,
    n_trials: int,
    n_grid_points: int,
    correlation_length: float,
    seed: int = 0,
    grid_extent: float = 1.0,
) -> MonteCarloLEEResult:
    """Synthetic null-hypothesis Gaussian-process ensemble.

    For each of `n_trials`:
      1. Sample a centered Gaussian random field on `n_grid_points`
         equally spaced points in [0, grid_extent].
      2. Covariance is squared-exponential with the named
         `correlation_length`. Diagonal-jitter regularization keeps
         the Cholesky factor numerically well-defined for short
         correlation lengths.
      3. Record max-z over the grid (per-trial) and per-trial
         upcrossings of the field across zero.

    The result is consumed by tests as the non-asymptotic ground
    truth that `gross_vitells_global_p_value` must agree with.

    Notes
    -----
    The grid is normalized to [0, 1] by default; only the ratio of
    `correlation_length` to `grid_extent` matters for the upcrossings
    rate. A grid with O(grid_extent / correlation_length)
    independent regions has an upcrossings-at-zero rate that scales
    proportionally — verified by the test suite via parametrization
    over correlation lengths.
    """
    if n_trials <= 0:
        raise ValueError(f"n_trials must be positive, got {n_trials!r}")
    if n_grid_points <= 1:
        raise ValueError(f"n_grid_points must be > 1, got {n_grid_points!r}")
    if correlation_length <= 0:
        raise ValueError(
            f"correlation_length must be positive, got {correlation_length!r}"
        )

    rng = np.random.default_rng(seed)
    grid = np.linspace(0.0, grid_extent, n_grid_points)
    covariance = _squared_exponential_covariance(grid, correlation_length)
    # Jitter for numerical stability of the Cholesky factor.
    covariance = covariance + 1e-9 * np.eye(n_grid_points)
    cholesky = np.linalg.cholesky(covariance)

    max_z_per_trial: List[float] = []
    total_upcrossings = 0
    for _ in range(n_trials):
        white = rng.standard_normal(n_grid_points)
        field = cholesky @ white
        max_z_per_trial.append(float(np.max(field)))
        total_upcrossings += _count_upward_crossings(field, threshold=0.0)

    return MonteCarloLEEResult(
        n_trials=n_trials,
        n_grid_points=n_grid_points,
        correlation_length=correlation_length,
        max_z_per_trial=tuple(max_z_per_trial),
        upcrossings_at_zero=total_upcrossings / n_trials,
    )


def empirical_upcrossings_at_threshold(
    field: Sequence[float],
    threshold: float,
) -> int:
    """Count upward crossings: positions i where field[i] ≤ threshold and
    field[i+1] > threshold."""
    arr = np.asarray(field, dtype=float)
    if arr.ndim != 1:
        raise ValueError(f"field must be 1-d, got shape {arr.shape}")
    return _count_upward_crossings(arr, threshold)


def _count_upward_crossings(field: np.ndarray, threshold: float) -> int:
    below_or_equal = field[:-1] <= threshold
    above = field[1:] > threshold
    return int(np.sum(below_or_equal & above))
