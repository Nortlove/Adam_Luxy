"""SequentialSchedule — O'Brien-Fleming alpha-spending for pre-specified
interim looks at plant-model projections.

Frame discipline: this ships O'Brien-Fleming as a MATH TOOL for pre-
specified interim decisions on cell track records, not as a clinical-
trial treatment-effect-significance substrate. The 2026-04-24 frame
correction rejected E-values / fragility index / GRADE labels as frame
drift; the alpha-spending framework survives because it's a scheduling
discipline (when-to-look + what-critical-value), not a significance-
testing verdict. The boundary crossing signals STRONG EVIDENCE for the
native adjudicator's partition decision (validated / failing / untested),
not a p-value-based reject/accept.

What the plant model uses this for:

- Before launch: fix the look schedule for each RecommendationClass
  track record. K looks at pre-specified information fractions
  (t_1, ..., t_K = 1.0). The schedule is part of the pre-registration
  and cannot be rewritten mid-flight without invalidating the pre-reg.
- At each look: compare the observed conversion count vs. the plant-
  model-implied rate. Boundary crossing → early partition decision.
- At horizon completion: the final look's boundary is the pre-specified
  adjudicator threshold.

A14 compromises:

- Pilot uses O'Brien-Fleming boundaries only (no Pocock alternative).
  OBF was chosen because it concentrates rejection mass at late looks,
  matching the discipline that early-look claims should clear a high
  bar — aligns with the "don't declare victory early" posture the
  pilot needs to defend against StackAdapt and to LUXY.
- Equal-spacing information fractions (t_k = k/K) are the default.
  Callers can pass custom information fractions for irregular schedules.
- Task_23–32 ownership coupling: this module ships STANDALONE math.
  The interim-look EXECUTION (pulling data daily, firing decisions
  into downstream systems) is DCIL work owned elsewhere. The wrapper
  design makes that integration a later straightforward binding.

Reference:
- O'Brien, P.C. & Fleming, T.R. (1979). A multiple testing procedure
  for clinical trials. Biometrics, 35(3), 549-556.
- Lan, K.K.G. & DeMets, D.L. (1983). Discrete sequential boundaries
  for clinical trials. Biometrika, 70(3), 659-663. (The alpha-spending
  extension that supports irregular information fractions.)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence


# =============================================================================
# Defaults
# =============================================================================

DEFAULT_ALPHA = 0.05  # Two-sided overall significance budget.
DEFAULT_N_LOOKS = 3   # K = 3 interim looks (t = 1/3, 2/3, 1.0) default.


# =============================================================================
# Normal CDF / inverse — pure Python (no scipy)
# =============================================================================


def _normal_cdf(z: float) -> float:
    """Standard normal CDF via erf."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _normal_ppf(p: float, tol: float = 1e-10, max_iter: int = 100) -> float:
    """Inverse standard normal CDF.

    Beasley-Springer-Moro rational approximation refined by Newton
    iteration. Matches scipy.stats.norm.ppf to ~12 digits on [0.001, 0.999].
    """
    if not (0.0 < p < 1.0):
        if p == 0.0:
            return -math.inf
        if p == 1.0:
            return math.inf
        raise ValueError(f"ppf argument must be in (0, 1); got {p}")

    # Rational approximation (Beasley-Springer-Moro style) for the initial
    # guess; refined by Newton iteration below.
    a = [
        -3.969683028665376e+01,  2.209460984245205e+02,
        -2.759285104469687e+02,  1.383577518672690e+02,
        -3.066479806614716e+01,  2.506628277459239e+00,
    ]
    b = [
        -5.447609879822406e+01,  1.615858368580409e+02,
        -1.556989798598866e+02,  6.680131188771972e+01,
        -1.328068155288572e+01,
    ]
    c = [
        -7.784894002430293e-03, -3.223964580411365e-01,
        -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00,  2.938163982698783e+00,
    ]
    d = [
         7.784695709041462e-03,  3.224671290700398e-01,
         2.445134137142996e+00,  3.754408661907416e+00,
    ]

    p_low, p_high = 0.02425, 1.0 - 0.02425
    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        x = (
            ((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]
        ) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    elif p <= p_high:
        q = p - 0.5
        r = q * q
        x = (
            (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
        ) / (
            ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0
        )
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        x = -(
            ((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]
        ) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )

    # Newton refinement (one or two iterations tightens to ~1e-12).
    for _ in range(max_iter):
        e = _normal_cdf(x) - p
        if abs(e) < tol:
            break
        # Derivative is normal PDF.
        pdf = math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)
        if pdf < 1e-30:
            break
        x -= e / pdf
    return x


# =============================================================================
# LookSchedule — pre-specified information fractions + OBF boundaries
# =============================================================================


@dataclass(frozen=True)
class LookSchedule:
    """Pre-specified interim-look schedule.

    `information_fractions` is a monotonically increasing sequence in
    (0, 1], ending at 1.0 (the horizon-complete look). The boundary
    critical z-values at each look are computed from the overall
    two-sided alpha under O'Brien-Fleming spacing.

    The schedule is immutable once constructed — the pre-registration
    commits to it, and changing look timing after observation breaks
    the alpha-spending guarantee.
    """

    information_fractions: tuple[float, ...]
    alpha: float = DEFAULT_ALPHA

    def __post_init__(self) -> None:
        if not self.information_fractions:
            raise ValueError("information_fractions must be non-empty")
        if not (0.0 < self.alpha < 1.0):
            raise ValueError(
                f"alpha must be in (0, 1); got {self.alpha}"
            )
        prev = 0.0
        for t in self.information_fractions:
            if not (0.0 < t <= 1.0):
                raise ValueError(
                    f"information_fractions must lie in (0, 1]; got {t}"
                )
            if t <= prev:
                raise ValueError(
                    f"information_fractions must be strictly increasing; "
                    f"saw {t} after {prev}"
                )
            prev = t
        if self.information_fractions[-1] != 1.0:
            raise ValueError(
                f"information_fractions must end at 1.0; "
                f"got {self.information_fractions[-1]}"
            )

    @classmethod
    def equal_spacing(
        cls, n_looks: int = DEFAULT_N_LOOKS, alpha: float = DEFAULT_ALPHA,
    ) -> "LookSchedule":
        """K equally-spaced looks ending at 1.0."""
        if n_looks < 1:
            raise ValueError(f"n_looks must be >= 1; got {n_looks}")
        fractions = tuple(
            (k + 1) / n_looks for k in range(n_looks)
        )
        return cls(information_fractions=fractions, alpha=alpha)

    def n_looks(self) -> int:
        return len(self.information_fractions)

    def obrien_fleming_boundaries(self) -> List[float]:
        """Two-sided O'Brien-Fleming critical z-values at each look.

        Canonical form (Pocock & White 1999 pedagogic summary):
            z_k = Z(1 - alpha/2) * sqrt(t_K / t_k)
        where t_k is the information fraction at look k. Returns the
        upper boundary; the lower boundary is the negation.
        """
        z_overall = _normal_ppf(1.0 - self.alpha / 2.0)
        t_final = self.information_fractions[-1]
        return [
            z_overall * math.sqrt(t_final / t) for t in self.information_fractions
        ]


# =============================================================================
# Interim-look decision
# =============================================================================


class InterimDecision(str, Enum):
    CONTINUE = "continue"
    STOP_FOR_EFFICACY = "stop_for_efficacy"  # observed rate > implied_rate
    STOP_FOR_FUTILITY = "stop_for_futility"  # observed rate < implied_rate


@dataclass(frozen=True)
class InterimLookResult:
    """Outcome of a single interim-look evaluation.

    Contains all the inputs to the decision so that re-running the
    adjudication later (audit / debug) uses only this record, not the
    live data source.
    """

    look_index: int
    information_fraction: float
    observed_count: int
    observed_sample_size: int
    observed_rate: float
    implied_rate: float
    z_statistic: float
    upper_boundary: float
    lower_boundary: float
    decision: InterimDecision

    def crossed_boundary(self) -> bool:
        return self.decision is not InterimDecision.CONTINUE


@dataclass(frozen=True)
class SequentialAdjudicator:
    """Evaluates interim looks against a pre-specified schedule and
    plant-model-implied conversion rate.

    The implied rate is the posterior mean of the plant-model Beta
    (from `PlantModel._posterior_parameters`) — not the raw industry
    prior. Using the posterior as the null hypothesis point operationalizes
    "realized outcomes should track the plant's projection if the cell
    is valid" and produces boundary-crossing signal only when the
    empirical rate meaningfully diverges.
    """

    schedule: LookSchedule
    implied_rate: float

    def __post_init__(self) -> None:
        if not (0.0 < self.implied_rate < 1.0):
            raise ValueError(
                f"implied_rate must be in (0, 1); got {self.implied_rate}"
            )

    def evaluate_look(
        self,
        look_index: int,
        observed_count: int,
        observed_sample_size: int,
    ) -> InterimLookResult:
        """Evaluate a single interim look.

        Raises ValueError for out-of-range look_index. Raises for
        nonsensical sample counts (negative, count > sample).
        """
        if not (0 <= look_index < self.schedule.n_looks()):
            raise ValueError(
                f"look_index {look_index} outside "
                f"[0, {self.schedule.n_looks() - 1}]"
            )
        if observed_sample_size <= 0:
            raise ValueError(
                f"observed_sample_size must be positive; "
                f"got {observed_sample_size}"
            )
        if observed_count < 0 or observed_count > observed_sample_size:
            raise ValueError(
                f"observed_count {observed_count} out of range "
                f"[0, {observed_sample_size}]"
            )

        t = self.schedule.information_fractions[look_index]
        observed_rate = observed_count / observed_sample_size
        boundaries = self.schedule.obrien_fleming_boundaries()
        upper = boundaries[look_index]
        lower = -upper

        # Standard-normal z-statistic on the conversion-rate point null.
        # Variance under the implied-rate null is p(1-p)/n.
        p0 = self.implied_rate
        var = p0 * (1.0 - p0) / observed_sample_size
        if var <= 0.0:
            z = 0.0
        else:
            z = (observed_rate - p0) / math.sqrt(var)

        if z >= upper:
            decision = InterimDecision.STOP_FOR_EFFICACY
        elif z <= lower:
            decision = InterimDecision.STOP_FOR_FUTILITY
        else:
            decision = InterimDecision.CONTINUE

        return InterimLookResult(
            look_index=look_index,
            information_fraction=t,
            observed_count=observed_count,
            observed_sample_size=observed_sample_size,
            observed_rate=observed_rate,
            implied_rate=p0,
            z_statistic=z,
            upper_boundary=upper,
            lower_boundary=lower,
            decision=decision,
        )


__all__ = [
    "DEFAULT_ALPHA",
    "DEFAULT_N_LOOKS",
    "InterimDecision",
    "InterimLookResult",
    "LookSchedule",
    "SequentialAdjudicator",
]
