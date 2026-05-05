"""Hill equation and Emax dose-response (directive §1.F.SI.1).

Hill (1910, *J. Physiol.* 40 Suppl., "The possible effects of the
aggregation of the molecules of haemoglobin on its dissociation
curves") originally described the cooperative oxygen binding of
haemoglobin with the now-canonical Emax sigmoid

    E(c) = E_0 + (E_max - E_0) * c^n / (EC_50^n + c^n)              (1)

Parameters:
  E_0     — baseline effect at zero concentration.
  E_max   — asymptotic (saturating) effect at infinite concentration.
  EC_50   — concentration at which E = (E_0 + E_max) / 2.
  n       — Hill coefficient. n=1 reduces to Michaelis-Menten;
            n > 1 yields a steeper sigmoid; n < 1 yields a shallower
            curve.

Two derived helpers:

    inhibition_factor(c, I_max, IC_50, n)
        = 1 - I_max * c^n / (IC_50^n + c^n)

The fractional reduction (in [1 - I_max, 1]) of a baseline rate when
the drug INHIBITS that rate. I_max ∈ [0, 1] is the maximum fractional
inhibition; I_max = 1 → complete suppression at saturating c.

    stimulation_factor(c, S_max, SC_50, n)
        = 1 + S_max * c^n / (SC_50^n + c^n)

The fractional amplification (in [1, 1 + S_max]) of a baseline rate
when the drug STIMULATES that rate. S_max ≥ 0 is the maximum
fractional increase.

These factors compose with the Dayneka-Garg-Jusko four basic
indirect-response models (`indirect_response.py`) — each model uses
either an inhibition or a stimulation factor on either the
production rate (k_in) or the elimination rate (k_out) of the
response variable R.

ADAM application context: c(t) is the modeled "concentration" of ad
exposure (e.g., from a one-compartment exponential-decay PK model
applied to discrete impressions). E(c) is the per-user instantaneous
response (e.g., conversion-rate inflation factor). The Hill
coefficient n captures cooperative ad-frequency effects beyond
single-impression dose-response.
"""
from __future__ import annotations

import math


__all__ = [
    "hill_response",
    "inhibition_factor",
    "stimulation_factor",
]


def hill_response(
    concentration: float,
    *,
    baseline_effect: float,
    max_effect: float,
    ec50: float,
    hill_coefficient: float,
) -> float:
    """Hill / Emax dose-response (eq. 1 of the module docstring).

    Parameters
    ----------
    concentration
        Drug concentration c ≥ 0.
    baseline_effect
        E_0 — effect at c = 0.
    max_effect
        E_max — asymptotic effect at c → ∞.
    ec50
        EC_50 > 0 — concentration at half-max effect.
    hill_coefficient
        n > 0 — slope; n=1 gives Michaelis-Menten kinetics.

    Returns
    -------
    E(c) per equation (1). Continuous in c on [0, ∞); equals
    `baseline_effect` at c=0; approaches `max_effect` as c→∞.
    """
    if concentration < 0:
        raise ValueError(
            f"concentration must be non-negative, got {concentration!r}"
        )
    if not math.isfinite(concentration):
        raise ValueError(
            f"concentration must be finite, got {concentration!r}"
        )
    if ec50 <= 0:
        raise ValueError(f"ec50 must be positive, got {ec50!r}")
    if hill_coefficient <= 0:
        raise ValueError(
            f"hill_coefficient must be positive, got {hill_coefficient!r}"
        )

    if concentration == 0.0:
        return baseline_effect
    fraction = concentration**hill_coefficient / (
        ec50**hill_coefficient + concentration**hill_coefficient
    )
    return baseline_effect + (max_effect - baseline_effect) * fraction


def inhibition_factor(
    concentration: float,
    *,
    max_inhibition: float,
    ic50: float,
    hill_coefficient: float = 1.0,
) -> float:
    """Hill-type inhibition factor on a baseline rate.

        factor(c) = 1 - I_max * c^n / (IC_50^n + c^n)

    Returns a value in [1 - I_max, 1]. At c=0 the factor is 1
    (no inhibition); as c → ∞ the factor approaches 1 - I_max.
    """
    if not 0.0 <= max_inhibition <= 1.0:
        raise ValueError(
            f"max_inhibition must be in [0, 1], got {max_inhibition!r}"
        )
    if ic50 <= 0:
        raise ValueError(f"ic50 must be positive, got {ic50!r}")
    if hill_coefficient <= 0:
        raise ValueError(
            f"hill_coefficient must be positive, got {hill_coefficient!r}"
        )
    if concentration < 0:
        raise ValueError(
            f"concentration must be non-negative, got {concentration!r}"
        )

    if concentration == 0.0:
        return 1.0
    fraction = concentration**hill_coefficient / (
        ic50**hill_coefficient + concentration**hill_coefficient
    )
    return 1.0 - max_inhibition * fraction


def stimulation_factor(
    concentration: float,
    *,
    max_stimulation: float,
    sc50: float,
    hill_coefficient: float = 1.0,
) -> float:
    """Hill-type stimulation factor on a baseline rate.

        factor(c) = 1 + S_max * c^n / (SC_50^n + c^n)

    Returns a value in [1, 1 + S_max]. At c=0 the factor is 1
    (no stimulation); as c → ∞ the factor approaches 1 + S_max.
    """
    if max_stimulation < 0:
        raise ValueError(
            f"max_stimulation must be non-negative, got {max_stimulation!r}"
        )
    if sc50 <= 0:
        raise ValueError(f"sc50 must be positive, got {sc50!r}")
    if hill_coefficient <= 0:
        raise ValueError(
            f"hill_coefficient must be positive, got {hill_coefficient!r}"
        )
    if concentration < 0:
        raise ValueError(
            f"concentration must be non-negative, got {concentration!r}"
        )

    if concentration == 0.0:
        return 1.0
    fraction = concentration**hill_coefficient / (
        sc50**hill_coefficient + concentration**hill_coefficient
    )
    return 1.0 + max_stimulation * fraction
