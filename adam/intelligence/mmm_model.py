"""E3b — Bayesian Marketing Mix Model substrate.

Closes the channel-ROI piece of E3. Three components:

    1. Adstock transform (Broadbent 1979, refined Hanssens-Parsons-
       Schultz 2001): geometric decay of ad effect over time.
           x_adstocked[t] = x[t] + λ · x_adstocked[t-1]
       λ ∈ [0, 1] is the carryover rate. Deterministic; no lib needed.

    2. Hill saturation (Jin-Wang-Sun-Chan-Koehler 2017, applied in
       Google's MMM tutorial): saturation curve with shape k and
       half-saturation θ.
           f(x) = x^k / (x^k + θ^k)
       Deterministic; no lib needed.

    3. Bayesian regression (PyMC, when installed): joint prior on
       per-channel (λ, k, θ) plus channel coefficients β; output is
       per-channel ROI with posterior uncertainty.

Substrate this commit ships:
    - Adstock + Hill transforms (deterministic, fully tested)
    - PyMC fit signature (raises MMMLibsMissingError when absent)
    - Per-channel ROI extraction shape

Discipline: same as M2/M3 substrate. The deterministic transforms ARE
shipped + tested. The Bayesian fit is gate-imported. No invented
hyperparameters; defaults follow the canonical Google-MMM example.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Deterministic transforms — adstock + Hill saturation
# =============================================================================


def adstock_geometric(
    impressions: List[float],
    carryover_rate: float,
) -> List[float]:
    """Geometric adstock: x_adstocked[t] = x[t] + λ · x_adstocked[t-1].

    Args:
        impressions: per-period impression / spend series
        carryover_rate: λ ∈ [0, 1]. 0 → no memory; 1 → infinite memory.

    Returns the adstocked series, same length as input.

    Canonical from Broadbent 1979 + Hanssens-Parsons-Schultz 2001
    'Market Response Models' Ch. 10. The geometric form is the
    standard MMM choice; alternative forms (Weibull adstock) are
    follow-on.
    """
    if not impressions:
        return []
    if not (0.0 <= carryover_rate <= 1.0):
        raise ValueError(
            f"carryover_rate {carryover_rate} outside [0, 1]"
        )

    adstocked: List[float] = [float(impressions[0])]
    for x in impressions[1:]:
        adstocked.append(float(x) + carryover_rate * adstocked[-1])
    return adstocked


def hill_saturation(
    x: float,
    half_saturation: float,
    slope: float,
) -> float:
    """Hill saturation: f(x) = x^k / (x^k + θ^k).

    Args:
        x: input value (post-adstock impression / spend)
        half_saturation: θ — the input level at which f(x) = 0.5
        slope: k — controls the shape (>1 = sigmoidal, =1 = Michaelis-
               Menten, <1 = concave)

    Returns f(x) ∈ [0, 1] for x >= 0 and θ > 0.

    Per Jin-Wang-Sun-Chan-Koehler 2017 'Bayesian Methods for Media
    Mix Modeling with Carryover and Shape Effects', the canonical
    saturation form for Bayesian MMM. f(0) = 0; f(θ) = 0.5; f(x) → 1
    as x → ∞.
    """
    if x < 0:
        # Saturation is for non-negative inputs (impressions/spend
        # can't be negative). Surface as 0.
        return 0.0
    if half_saturation <= 0 or slope <= 0:
        raise ValueError(
            f"half_saturation={half_saturation} and slope={slope} must be positive"
        )
    if x == 0:
        return 0.0
    x_pow = x ** slope
    theta_pow = half_saturation ** slope
    return x_pow / (x_pow + theta_pow)


def adstock_then_hill(
    impressions: List[float],
    carryover_rate: float,
    half_saturation: float,
    slope: float,
) -> List[float]:
    """Composed transform: adstock(geometric) → Hill saturation.

    The canonical MMM pipeline applies adstock FIRST (capture
    carryover) then saturation (capture diminishing returns). Order
    matters: applying saturation first would compress the input range
    BEFORE the carryover sums, producing a different curve.
    """
    adstocked = adstock_geometric(impressions, carryover_rate)
    return [hill_saturation(x, half_saturation, slope) for x in adstocked]


# =============================================================================
# Channel ROI extraction shape
# =============================================================================


@dataclass
class ChannelEffect:
    """Per-channel posterior summary."""
    channel_id: str
    coefficient_mean: float
    coefficient_lower: float        # 95% CI lower
    coefficient_upper: float
    carryover_rate_mean: float
    half_saturation_mean: float
    slope_mean: float
    contribution_share: float = 0.0  # fraction of total predicted outcome
    incremental_roi: float = 0.0     # contribution / spend


@dataclass
class MMMFitResult:
    """Full MMM fit summary."""
    channel_effects: Dict[str, ChannelEffect]
    intercept_mean: float
    r_squared: float
    n_observations: int
    library_versions: Dict[str, str] = field(default_factory=dict)
    diagnostics: List[str] = field(default_factory=list)


@dataclass
class MMMFitDiagnostics:
    """Per-fit ops diagnostics."""
    n_channels: int = 0
    n_observations: int = 0
    divergences: int = 0
    r_hat_max: float = 0.0
    fitted_at_ts: float = 0.0
    library_versions: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class MMMLibsMissingError(RuntimeError):
    """Raised when MMM Bayesian fit is requested but PyMC isn't installed.

    Returning None would let callers consume meaningless ROI silently.
    """
    pass


# -----------------------------------------------------------------------------
# Soft-import gate
# -----------------------------------------------------------------------------


def _try_import_pymc() -> Optional[Any]:
    try:
        import pymc  # noqa: F401
        return pymc
    except ImportError:
        return None


# -----------------------------------------------------------------------------
# Bayesian fit (PyMC) — substrate; full implementation when libs deploy
# -----------------------------------------------------------------------------


def fit_mmm(
    channel_data: Dict[str, List[float]],
    outcome: List[float],
    draws: int = 2000,
    tune: int = 1500,
    target_accept: float = 0.95,
) -> MMMFitResult:
    """Fit a Bayesian MMM with adstock + Hill saturation per channel.

    Args:
        channel_data: {channel_id: [per-period spend/impressions]}
        outcome: [per-period conversions or revenue]
        draws / tune / target_accept: PyMC NUTS hyperparameters

    Model structure (per Jin-Wang-Sun-Chan-Koehler 2017):
        For each channel c:
            λ_c ~ Beta(2, 2)            # carryover rate
            θ_c ~ HalfNormal(σ_θ)        # half-saturation
            k_c ~ HalfNormal(2)          # slope
            β_c ~ HalfNormal(σ_β)        # coefficient (positive)
            x'_c[t] = hill(adstock(x_c[t], λ_c), θ_c, k_c)

        intercept ~ Normal(0, σ_α)
        sigma ~ HalfNormal(σ_y)
        y[t] ~ Normal(intercept + Σ_c β_c · x'_c[t], sigma)

    Raises:
        MMMLibsMissingError when PyMC isn't available
        ValueError when input shapes don't align
    """
    if not channel_data:
        raise ValueError("fit_mmm: empty channel_data")
    if not outcome:
        raise ValueError("fit_mmm: empty outcome")

    # Validate shapes
    n_obs = len(outcome)
    for channel_id, series in channel_data.items():
        if len(series) != n_obs:
            raise ValueError(
                f"channel {channel_id!r} has {len(series)} obs but "
                f"outcome has {n_obs}"
            )

    pymc = _try_import_pymc()
    if pymc is None:
        raise MMMLibsMissingError(
            "PyMC not installed. Bayesian MMM requires pymc>=5.16. "
            "Install with `pip install pymc>=5.16 numpyro>=0.16`."
        )

    # Full PyMC build is M3-style follow-on (the model spec is
    # specified above; the actual PyMC graph construction uses the
    # same NCP pattern as M3's hierarchical model). This commit ships
    # the substrate signature + soft-import gate; the model graph
    # build runs when PyMC actually deploys.
    raise NotImplementedError(
        "fit_mmm: full PyMC build is E3 follow-on. Substrate signature "
        "shipped; the deterministic adstock + Hill transforms are "
        "fully implemented and tested. The Bayesian fit lands when "
        "PyMC is deployed (same gate as M3 hierarchical_bayes)."
    )


# -----------------------------------------------------------------------------
# Channel-level diagnostic from observed data (no fit required)
# -----------------------------------------------------------------------------


def channel_response_curve(
    spend_levels: List[float],
    carryover_rate: float = 0.5,
    half_saturation: float = 1000.0,
    slope: float = 1.5,
) -> List[Tuple[float, float]]:
    """Compute the response curve for a single channel under given
    transform parameters.

    Useful for visualizing what the adstock + Hill curve LOOKS LIKE
    under specific (λ, θ, k) without fitting. Pre-pilot when no fit
    data exists yet, this generates the canonical 'spend → response'
    curve for visualization in dashboards / investor decks.

    Returns [(spend, response), ...] — pairs the user can plot.

    The carryover_rate / half_saturation / slope defaults are
    illustrative midpoints, NOT empirical. They should be REPLACED
    with fitted values once fit_mmm runs.
    """
    return [
        (
            spend,
            hill_saturation(
                # No adstock here — single-period response curve
                spend, half_saturation, slope,
            ),
        )
        for spend in spend_levels
    ]
