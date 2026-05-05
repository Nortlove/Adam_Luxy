"""Pharmacovigilance schema + disproportionality metrics.

Per directive §G.3 (pre-pilot deliverable). Schema is fixed pre-pilot;
data populates post-pilot as Stage C events flow through S5.

Disproportionality metrics implemented:
  - PRR (Proportional Reporting Ratio)
  - ROR (Reporting Odds Ratio)
  - IC + IC025 (Bayesian Confidence Propagation Neural Network style
    Information Component, Bate et al. 1998)
  - EBGM (Empirical Bayes Geometric Mean) with DuMouchel MGPS
    two-gamma-mixture-prior shrinkage (DuMouchel 1999, *Amer. Stat.*
    53:170-190; DuMouchel & Pregibon 2001 KDD '01)
    * Naive single-cell EBGM provided here (gamma-Poisson posterior
      mean of log(λ)); full MGPS empirical-Bayes prior fitting is an
      iterative EM over the entire signal table and lands in a later
      slice once data is populated.
  - Tree-based scan statistics (Kulldorff 2003) — schema only,
    computation lands when data is populated.

Signal localization grain: (creative_id × cohort_id × posture_class ×
cell_id). Operational signal threshold: EB05 > 2 per Almenoff/EFSPI
convention. IC025 > 0 (BCPNN convention) is a complementary signal.

References:
  DuMouchel W. (1999). "Bayesian Data Mining in Large Frequency
    Tables, with an Application to the FDA Spontaneous Reporting
    System." Amer. Stat. 53:170-190.
  Bate A. et al. (1998). "A Bayesian neural network method for
    adverse drug reaction signal generation." Eur. J. Clin.
    Pharmacol. 54:315-321.
  Kulldorff M. et al. (2003). "A tree-based scan statistic for
    database disease surveillance." Biometrics 59:323-331.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional, Tuple


PostureClass = Literal[
    "INFORMATION_FORAGING",
    "TASK_COMPLETION",
    "LEISURE_BROWSING",
    "SOCIAL_CONSUMPTION",
    "TRANSACTIONAL_COMPARISON",
]


# ----------------------------------------------------------------------------
# Schema
# ----------------------------------------------------------------------------

@dataclass(frozen=True)
class SignalThresholds:
    """Operational thresholds for signal declaration.

    EB05 > 2 per Almenoff/EFSPI convention is the primary signal.
    IC025 > 0 per BCPNN convention is a complementary signal (Bate
    et al. 1998). PRR > 2 with chi-squared > 4 is a legacy threshold
    (Evans-Waller-Davis 2001). ROR > 2 corresponds to ~PRR > 2 at
    moderate-to-large counts.

    A signal is declared if ANY threshold fires (`mode='any'`) or
    only if MULTIPLE thresholds fire (`mode='consensus'`); the schema
    supports both via the `is_signal()` helper below.
    """
    eb05_threshold: float = 2.0
    ic025_threshold: float = 0.0
    prr_threshold: float = 2.0
    prr_chi2_threshold: float = 4.0
    ror_threshold: float = 2.0


@dataclass(frozen=True)
class DisproportionalityMetrics:
    """Computed metrics for one (creative × cohort × posture × cell)
    cell. All metrics computed from the 2x2 table:

                    event       non-event
        target arm    a            b
        baseline      c            d

    Where 'event' is the negative-outcome event being surveilled
    (per directive Slice S5.4 within-subject negative-outcome
    adapter) and 'baseline' is the rest of the table excluding
    target arm.
    """
    a: int  # target arm, event
    b: int  # target arm, non-event
    c: int  # baseline, event
    d: int  # baseline, non-event

    # Computed
    prr: Optional[float] = None
    prr_chi2: Optional[float] = None
    ror: Optional[float] = None
    ic: Optional[float] = None
    ic025: Optional[float] = None
    ebgm: Optional[float] = None
    eb05: Optional[float] = None  # populated by full MGPS later

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DisproportionalityMetrics":
        return cls(**{k: d.get(k) for k in (
            "a", "b", "c", "d",
            "prr", "prr_chi2", "ror", "ic", "ic025", "ebgm", "eb05",
        ) if k in d})


@dataclass(frozen=True)
class PharmacovigilanceCell:
    """One row in the signal-table per directive §G.3 grain
    (creative × cohort × posture × cell).

    `metrics` is the computed-metric block; `last_updated` is the
    timestamp of the latest data refresh from Stage C events."""
    creative_id: str
    cohort_id: str
    posture: PostureClass
    cell_id: str
    metrics: DisproportionalityMetrics
    last_updated: Optional[str] = None  # ISO-8601 string; None pre-data
    signal: bool = False
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["metrics"] = self.metrics.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PharmacovigilanceCell":
        m = d.get("metrics") or {}
        return cls(
            creative_id=d["creative_id"],
            cohort_id=d["cohort_id"],
            posture=d["posture"],
            cell_id=d["cell_id"],
            metrics=DisproportionalityMetrics.from_dict(m),
            last_updated=d.get("last_updated"),
            signal=bool(d.get("signal", False)),
            notes=d.get("notes"),
        )


@dataclass(frozen=True)
class TreeScanResult:
    """Output of a Kulldorff tree-based scan over the
    (creative × cohort × posture × cell) hierarchy.

    `most_likely_cluster_path` is the dot-separated path through the
    hierarchy (e.g., 'creative_8847221.cohort_status_seeker.LEISURE_BROWSING.cell_42'
    or just a prefix for higher-level clusters). `pvalue` is from
    Monte Carlo permutation; `relative_risk` is the cluster's
    observed/expected ratio under the null."""
    most_likely_cluster_path: str
    log_likelihood_ratio: float
    relative_risk: float
    cluster_observed: float
    cluster_expected: float
    pvalue: float
    n_permutations: int


# ----------------------------------------------------------------------------
# Computations (closed-form + naive EBGM; full MGPS in later slice)
# ----------------------------------------------------------------------------

def compute_prr(a: int, b: int, c: int, d: int) -> Tuple[float, float]:
    """Proportional Reporting Ratio + chi-squared.

    PRR = (a/(a+b)) / (c/(c+d))
    chi-sq = sum_i (O_i - E_i)^2 / E_i over the 2x2 table

    Returns (PRR, chi2). Both NaN-safe: returns (0, 0) when target
    arm is empty or baseline event rate is 0.
    """
    if (a + b) == 0 or (c + d) == 0 or c == 0:
        return 0.0, 0.0
    p_target = a / (a + b)
    p_baseline = c / (c + d)
    if p_baseline == 0.0:
        return 0.0, 0.0
    prr = p_target / p_baseline

    # Chi-squared (Yates-uncorrected; Almenoff convention)
    n = a + b + c + d
    e_a = (a + b) * (a + c) / n
    e_b = (a + b) * (b + d) / n
    e_c = (c + d) * (a + c) / n
    e_d = (c + d) * (b + d) / n
    chi2 = sum(
        ((obs - exp) ** 2) / exp if exp > 0 else 0.0
        for obs, exp in zip([a, b, c, d], [e_a, e_b, e_c, e_d])
    )
    return prr, chi2


def compute_ror(a: int, b: int, c: int, d: int) -> float:
    """Reporting Odds Ratio = (a*d) / (b*c).

    Returns 0.0 if denominator is 0."""
    if b == 0 or c == 0:
        return 0.0
    return (a * d) / (b * c)


def compute_ic(a: int, b: int, c: int, d: int) -> float:
    """Information Component (BCPNN style; Bate et al. 1998
    simplified form).

    Uses the Norén et al. 2006 closed-form approximation:
        IC = log2((a + 0.5) * N / ((a + b + 0.5) * (a + c + 0.5)))

    where N = a + b + c + d. The 0.5 pseudo-count is the standard
    Bayesian shrinkage for low-count cells.

    Returns 0.0 when N=0.
    """
    n = a + b + c + d
    if n == 0:
        return 0.0
    numerator = (a + 0.5) * n
    denominator = (a + b + 0.5) * (a + c + 0.5)
    if denominator <= 0:
        return 0.0
    val = numerator / denominator
    if val <= 0:
        return 0.0
    return math.log2(val)


def compute_ic025(a: int, b: int, c: int, d: int) -> float:
    """Lower 2.5th percentile (one-tailed 5%) of the IC posterior
    via the Norén et al. 2006 approximation:
        IC025 ≈ IC - 3.3 * (a + 0.5)^(-1/2) - 2 * (a + 0.5)^(-3/2)

    The 3.3 and 2 coefficients come from a Wilson-style approximation
    to the IC posterior variance under low counts. IC025 > 0 is the
    BCPNN signal threshold.
    """
    if a < 0:
        return 0.0
    ic = compute_ic(a, b, c, d)
    a_plus = a + 0.5
    var_term = 3.3 * (a_plus ** -0.5) + 2.0 * (a_plus ** -1.5)
    return ic - var_term


def compute_ebgm_naive(
    a: int, b: int, c: int, d: int,
    alpha: float = 0.5, beta: float = 0.5,
) -> float:
    """Naive EBGM: posterior mean of log(λ) under a single
    Gamma(α, β) prior, conjugate-posterior closed form.

    For the gamma-Poisson model with prior λ ~ Gamma(α, β) and
    observed event count a with expected count E:
        posterior λ ~ Gamma(α + a, β + E)
        E[log λ] = ψ(α + a) - log(β + E)  (digamma identity)
        EBGM = exp(E[log λ])

    Where E (the expected count under independence) is:
        E = (a + b) * (a + c) / N  with N = a + b + c + d.

    This is the SINGLE-CELL EBGM. The full DuMouchel MGPS shrinkage
    fits a TWO-GAMMA-MIXTURE prior to the entire signal-table
    distribution via EM, which lands in a later slice when data
    populates. This naive version is the schema-correct placeholder
    that tests + the dashboard wiring can exercise.

    Returns 0.0 when N=0 or expected count is 0.
    """
    n = a + b + c + d
    if n == 0:
        return 0.0
    expected = (a + b) * (a + c) / n
    if expected <= 0:
        return 0.0
    # E[log(λ)] under Gamma(α + a, β + E) posterior.
    # Use lgamma-derivative via numerical digamma; avoid scipy dep.
    posterior_alpha = alpha + a
    posterior_beta = beta + expected
    # Approximate digamma(x) for x > 0: psi(x) ≈ log(x) - 1/(2x) - 1/(12x^2)
    # (reasonable for x > 1; series term cap)
    x = posterior_alpha
    if x < 1.0:
        # Recurrence: psi(x) = psi(x+1) - 1/x
        psi = _digamma_approx(x + 5) - sum(1.0 / (x + k) for k in range(5))
    else:
        psi = _digamma_approx(x)
    expected_log_lambda = psi - math.log(posterior_beta)
    return math.exp(expected_log_lambda)


def _digamma_approx(x: float) -> float:
    """Asymptotic series for digamma; accurate for x ≥ 1."""
    return (math.log(x) - 1.0 / (2 * x) - 1.0 / (12 * x * x)
            + 1.0 / (120 * x ** 4))


def is_signal(
    metrics: DisproportionalityMetrics,
    thresholds: SignalThresholds = SignalThresholds(),
    mode: Literal["any", "consensus"] = "any",
) -> bool:
    """Evaluate signal status from a metrics block + thresholds.

    'any' mode: signal if ANY of (EB05 > τ, IC025 > τ, [PRR > τ AND
        chi2 > τ_chi2], ROR > τ).
    'consensus' mode: signal only if AT LEAST 2 thresholds fire.
    """
    fired = []
    if metrics.eb05 is not None and metrics.eb05 > thresholds.eb05_threshold:
        fired.append("eb05")
    if metrics.ic025 is not None and metrics.ic025 > thresholds.ic025_threshold:
        fired.append("ic025")
    if (metrics.prr is not None and metrics.prr > thresholds.prr_threshold
            and metrics.prr_chi2 is not None
            and metrics.prr_chi2 > thresholds.prr_chi2_threshold):
        fired.append("prr")
    if metrics.ror is not None and metrics.ror > thresholds.ror_threshold:
        fired.append("ror")

    if mode == "any":
        return len(fired) >= 1
    return len(fired) >= 2
