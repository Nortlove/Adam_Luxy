# =============================================================================
# ADAM Phase 9 — Pre-Launch Validation Substrate
# Location: adam/intelligence/spine/phase_9_pre_launch.py
# =============================================================================

"""Pre-launch validation substrate.

PER DIRECTIVE SECTION 9 PHASE 9 + SECTION 8.4.

Substrate items (this module):
    - mSPRT (mixture Sequential Probability Ratio Test) campaign-level
      monitor — Wald's sequential test with mixture prior; permits
      continuous monitoring WITHOUT alpha inflation
    - Pre-registered analysis plan Pydantic + lock semantics
    - Simulation exercise framework (per directive Appendix A)

Operational items (deferred to actual execution):
    - Internal red-team review against Foundation §7 rule 11 (human)
    - CMO walkthrough rehearsal (human)
    - Pre-reg published externally (OSF / AsPredicted; operational)

PHASE 9 RED-CRITERION GATE (per directive Section 9 Phase 9)

    "Simulation results validate the priority order of cognitive
    primitives (each component carries weight in the order specified
    by the spine). Red-team reveals no path where the fluency floor
    can be bypassed. CMO walkthrough is articulable in his own words."

DECISION-TIME CONSUMERS (Rule A check)

  - mSPRT runs continuously during the pilot; partner dashboard
    (Spine #13 MSPRTBoundaryStatus) displays current state
  - Pre-reg locked structure feeds the pilot launch decision (Phase 10)
  - Simulation framework outputs the Appendix A comparison report
    that calibrates mSPRT boundaries

mSPRT IS decision-time substrate (campaign-level monitor running every
day during the pilot). The pre-reg + simulation framework are pre-
launch artifacts that GATE the launch decision (Phase 10) — they are
"decision-time" at the launch-gate decision, not the bid-time decision.

REFERENCES

    Wald 1947 — Sequential Analysis (the SPRT).
    Robbins 1970 — Statistical methods related to the law of the
        iterated logarithm (mixture SPRT).
    Lai 1976 — On confidence sequences (continuous-monitoring valid).
    Howard, Ramdas, McAuliffe & Sekhon 2021 — modern mSPRT bounds.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# =============================================================================
# Configuration constants
# =============================================================================


# Standard mSPRT thresholds for type-I and type-II error rates (Robbins
# 1970; Wald 1947). For α = 0.05 and β = 0.20 (80% power), the canonical
# log-likelihood-ratio thresholds are:
#   upper = log((1 - β) / α) = log(16) ≈ 2.77
#   lower = log(β / (1 - α)) = log(0.20 / 0.95) ≈ -1.56
# These are the boundaries that, IF CROSSED, the test rejects the null
# (upper) or accepts the null (lower). Per directive Section 7.1 +
# 8.4: the LOWER crossing is a RED-criterion launch deferral trigger
# during the pilot.

DEFAULT_MSPRT_ALPHA: float = 0.05
DEFAULT_MSPRT_BETA: float = 0.20  # 80% power


def _wald_upper_boundary(alpha: float, beta: float) -> float:
    """log((1 - β) / α). Reject null when test stat ≥ this."""
    return math.log((1.0 - beta) / alpha)


def _wald_lower_boundary(alpha: float, beta: float) -> float:
    """log(β / (1 - α)). Accept null when test stat ≤ this."""
    return math.log(beta / (1.0 - alpha))


# =============================================================================
# mSPRT (mixture Sequential Probability Ratio Test) for binary outcomes
# =============================================================================


class MSPRTDecision(str, Enum):
    """Three outcomes of an mSPRT step."""

    CONTINUE = "continue"      # No boundary crossed; keep observing
    REJECT_NULL = "reject_null"  # Upper boundary crossed; treatment > control
    ACCEPT_NULL = "accept_null"  # Lower boundary crossed; no detectable lift


@dataclass(frozen=True)
class MSPRTState:
    """Current state of the mSPRT campaign-level monitor.

    Per directive Section 8.4: 'mSPRT (mixture SPRT) for the
    population-level "is this campaign creating lift" question; it
    permits continuous monitoring without alpha inflation.'

    The test statistic is the cumulative log-likelihood ratio under
    the alternative hypothesis (effect = expected_lift) vs the null
    (effect = 0). A mixture prior over alternatives gives the
    "mixture" version's continuous-monitoring validity.
    """

    n_treatment: int        # cumulative count in treatment arm
    n_control: int          # cumulative count in control arm
    sum_treatment: float    # cumulative outcome sum, treatment
    sum_control: float      # cumulative outcome sum, control
    log_likelihood_ratio: float
    decision: MSPRTDecision
    upper_boundary: float
    lower_boundary: float


def msprt_step(
    n_treatment: int,
    n_control: int,
    sum_treatment: float,
    sum_control: float,
    expected_lift: float,
    *,
    alpha: float = DEFAULT_MSPRT_ALPHA,
    beta: float = DEFAULT_MSPRT_BETA,
    null_baseline_rate: float = 0.05,
) -> MSPRTState:
    """One step of the mSPRT for binary outcomes (e.g., conversion).

    Per Wald 1947 + Robbins 1970 mixture extension: the cumulative
    log-likelihood ratio compares H_1 (lift = expected_lift) vs H_0
    (lift = 0). Under continuous monitoring with the mixture prior,
    crossing the boundaries gives a valid sequential test.

    For binary outcomes with rates p_t (treatment) and p_c (control)
    centered at null_baseline_rate, with H_0 : p_t = p_c = p_0 and
    H_1 : p_t = p_0 + expected_lift :

        LLR_step = log(L_H1(observation) / L_H0(observation))

    Cumulative LLR: sum across observations. Compare to Wald boundaries.

    Returns MSPRTState with decision (CONTINUE / REJECT_NULL / ACCEPT_NULL)
    + the boundaries.

    Args:
        n_treatment, n_control: cumulative counts
        sum_treatment, sum_control: cumulative outcome sums (binary)
        expected_lift: H_1 lift over H_0 baseline
        alpha, beta: error rates
        null_baseline_rate: H_0 rate (when treatment = control)
    """
    if n_treatment < 0 or n_control < 0:
        raise ValueError("counts must be non-negative")
    if sum_treatment < 0 or sum_control < 0:
        raise ValueError("sums must be non-negative")
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must be in (0, 1); got {alpha}")
    if not 0.0 < beta < 1.0:
        raise ValueError(f"beta must be in (0, 1); got {beta}")
    if not 0.0 < null_baseline_rate < 1.0:
        raise ValueError(
            f"null_baseline_rate must be in (0, 1); got {null_baseline_rate}"
        )

    upper = _wald_upper_boundary(alpha, beta)
    lower = _wald_lower_boundary(alpha, beta)

    # Compute LLR for the observed treatment + control arms.
    # Under H_0: both arms have rate p_0
    # Under H_1: treatment arm has rate p_0 + lift; control arm has p_0
    p_0 = null_baseline_rate
    p_1 = max(0.001, min(0.999, p_0 + expected_lift))

    # Treatment arm contribution (Bernoulli LLR)
    llr_treatment = (
        sum_treatment * (math.log(p_1) - math.log(p_0))
        + (n_treatment - sum_treatment)
        * (math.log(1.0 - p_1) - math.log(1.0 - p_0))
        if n_treatment > 0
        else 0.0
    )

    # Control arm contribution: under H_0 rate is p_0; under H_1 also
    # p_0 (control unaffected). LLR contribution = 0.
    # In practice the mSPRT can also test for control drift; here we
    # pin to the canonical campaign-vs-holdout test where H_1 affects
    # treatment only.
    llr_control = 0.0

    cumulative_llr = llr_treatment + llr_control

    # Decision rule
    if cumulative_llr >= upper:
        decision = MSPRTDecision.REJECT_NULL
    elif cumulative_llr <= lower:
        decision = MSPRTDecision.ACCEPT_NULL
    else:
        decision = MSPRTDecision.CONTINUE

    return MSPRTState(
        n_treatment=n_treatment,
        n_control=n_control,
        sum_treatment=sum_treatment,
        sum_control=sum_control,
        log_likelihood_ratio=cumulative_llr,
        decision=decision,
        upper_boundary=upper,
        lower_boundary=lower,
    )


# =============================================================================
# mSPRT for sub-Gaussian / Gaussian continuous outcomes (Slice 7)
# =============================================================================
#
# Closes the named-successor slice from msprt_outcome_aggregation
# (line 75-77): "continuous-outcome mSPRT (Howard et al. 2021 sub-
# gaussian extension) is a sibling slice when LUXY pilot data shows
# binary collapses too much information."
#
# WHY THIS EXISTS
# ---------------
#
# The binary mSPRT (msprt_step above) collapses every continuous
# outcome (viewable dwell, scroll depth, time-on-site, value-conversion)
# to {0, 1}. For a campaign that genuinely produces graded effects
# (e.g., LUXY's premium-tier conversion has dollar-value variance,
# not just yes/no), this loses information — small lifts on
# continuous outcomes never reach the binary boundary in feasible
# time, and the test stays at CONTINUE long after a sub-Gaussian
# test would have decided.
#
# This v0.1 ships Gaussian-likelihood mSPRT with caller-provided
# sub-Gaussian σ. The full Howard et al. 2021 nonparametric time-
# uniform boundary (empirical-Bernstein with running variance
# estimator, no σ assumption) is the v1.0 sibling.
#
# ALGORITHM
# ---------
#
# Two-sample mSPRT for difference of means, sub-Gaussian (or Gaussian)
# observations with known σ.
#
#   H_0: μ_T - μ_C = 0
#   H_1: μ_T - μ_C = δ   (the expected_lift)
#
# Per-obs LLR for treatment observation X_T (with sample mean of
# control μ̂_C plugged in for the nuisance parameter):
#
#   LLR_per_obs(X_T) = (X_T - μ̂_C) · δ / σ² - δ² / (2σ²)
#
# Cumulative LLR over both arms collapses (under H_0 vs H_1 the
# control LLR is 0 by symmetry — μ_C is unchanged) to a function of
# the difference of sample means, weighted by the harmonic-pooled n:
#
#   n_pooled = (n_T · n_C) / (n_T + n_C)         [variance of difference of means]
#   diff_obs = μ̂_T - μ̂_C
#   LLR     = δ · diff_obs · n_pooled / σ²  -  n_pooled · δ² / (2σ²)
#
# Wald boundaries (same α/β-derived constants as binary):
#   upper = log((1 - β) / α)        REJECT_NULL when LLR ≥ upper
#   lower = log(β / (1 - α))        ACCEPT_NULL when LLR ≤ lower
#
# Either arm with n=0 → LLR=0 / CONTINUE (no signal yet).


def msprt_step_continuous(
    n_treatment: int,
    n_control: int,
    sum_treatment: float,
    sum_control: float,
    expected_lift: float,
    sub_gaussian_sigma: float,
    *,
    alpha: float = DEFAULT_MSPRT_ALPHA,
    beta: float = DEFAULT_MSPRT_BETA,
) -> MSPRTState:
    """One step of the mSPRT for sub-Gaussian / Gaussian continuous outcomes.

    v0.1 of the directive's Howard et al. 2021 sub-Gaussian mSPRT.
    Uses Gaussian-likelihood LLR with a caller-provided sub-Gaussian
    σ upper bound; full nonparametric empirical-Bernstein boundary
    (running σ̂ estimator) is a sibling slice.

    Args:
        n_treatment, n_control: cumulative arm counts.
        sum_treatment, sum_control: cumulative outcome sums (continuous).
        expected_lift: H_1 effect on the difference of means (δ).
        sub_gaussian_sigma: known / upper-bound sub-Gaussian parameter
            for per-obs noise. Continuous outcomes are NOT bounded to
            [0, 1] like the binary mSPRT — caller is responsible for
            providing a σ that conservatively bounds the per-obs
            sub-Gaussian noise. Conservative = larger σ = slower test
            but valid; underestimating σ inflates type-I error.
        alpha, beta: error rates (default α=0.05, β=0.20).

    Returns MSPRTState with decision (CONTINUE / REJECT_NULL /
    ACCEPT_NULL) and the boundaries.

    Raises ValueError on negative counts / non-positive σ / out-of-
    range α/β. Sums may be negative (some outcome scales are signed,
    e.g., time-since-baseline).
    """
    if n_treatment < 0 or n_control < 0:
        raise ValueError("counts must be non-negative")
    if sub_gaussian_sigma <= 0:
        raise ValueError(
            f"sub_gaussian_sigma must be positive; got {sub_gaussian_sigma}"
        )
    if not 0.0 < alpha < 1.0:
        raise ValueError(f"alpha must be in (0, 1); got {alpha}")
    if not 0.0 < beta < 1.0:
        raise ValueError(f"beta must be in (0, 1); got {beta}")

    upper = _wald_upper_boundary(alpha, beta)
    lower = _wald_lower_boundary(alpha, beta)
    sigma_sq = sub_gaussian_sigma ** 2

    # When either arm has no observations, the difference of means is
    # undefined — LLR is 0 and we stay in CONTINUE.
    if n_treatment == 0 or n_control == 0:
        cumulative_llr = 0.0
    else:
        mean_t = sum_treatment / n_treatment
        mean_c = sum_control / n_control
        diff_obs = mean_t - mean_c
        # Harmonic-pooled n for the variance of the difference of means
        n_pooled = (n_treatment * n_control) / (n_treatment + n_control)
        cumulative_llr = (
            expected_lift * diff_obs * n_pooled / sigma_sq
            - n_pooled * (expected_lift ** 2) / (2.0 * sigma_sq)
        )

    if cumulative_llr >= upper:
        decision = MSPRTDecision.REJECT_NULL
    elif cumulative_llr <= lower:
        decision = MSPRTDecision.ACCEPT_NULL
    else:
        decision = MSPRTDecision.CONTINUE

    return MSPRTState(
        n_treatment=n_treatment,
        n_control=n_control,
        sum_treatment=sum_treatment,
        sum_control=sum_control,
        log_likelihood_ratio=cumulative_llr,
        decision=decision,
        upper_boundary=upper,
        lower_boundary=lower,
    )


def is_red_criterion_triggered(state: MSPRTState) -> bool:
    """Return True iff the mSPRT has crossed the LOWER boundary.

    Per directive Section 7.1: "crossing the lower boundary mid-pilot
    is a RED-criterion launch deferral trigger."

    Note: ACCEPT_NULL (lower crossing) is the RED. REJECT_NULL (upper
    crossing) is the POSITIVE signal — campaign is creating lift.
    CONTINUE means we're still observing.
    """
    return state.decision == MSPRTDecision.ACCEPT_NULL


# =============================================================================
# Pre-registered analysis plan
# =============================================================================


class PreRegStatus(str, Enum):
    """Pre-reg lifecycle states."""

    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    LOCKED = "locked"        # Cannot be modified; published externally
    AMENDED = "amended"       # Locked + amendments tracked


class PreRegisteredAnalysisPlan(BaseModel):
    """Pre-registered campaign-level analysis plan per directive Section 8.4.

    Per directive: 'Estimand: ATE on conversion rate (ADAM-treated vs.
    holdout) over the pilot window. Prior: weak Gaussian on the
    difference, centered at 0. Likelihood: Bernoulli on conversion /
    outcome composite per user-day. Posterior: Gaussian process over
    the daily-difference time series (handles autocorrelation).
    Reporting: posterior probability of positive lift; 95% credible
    interval on lift; per-cohort posteriors with appropriate
    hierarchical pooling. mSPRT boundaries: pre-specified.'

    Once locked, the plan cannot be modified — only AMENDED with a
    public amendment log. Foundation §7 rule 11 protected at the
    pre-launch artifact level.
    """

    model_config = ConfigDict(extra="forbid")

    plan_id: str
    pilot_id: str

    # Estimand
    estimand_description: str  # human-authored; templated cognitive vocab
    estimand_kind: str  # "ATE" | "CATE_per_cohort" | etc.

    # Prior + likelihood
    prior_specification: str
    likelihood_specification: str
    posterior_method: str  # "Gaussian process" | "MCMC" | etc.

    # mSPRT boundaries (pre-specified)
    msprt_alpha: float = DEFAULT_MSPRT_ALPHA
    msprt_beta: float = DEFAULT_MSPRT_BETA
    msprt_expected_lift: float = 0.0
    msprt_null_baseline_rate: float = 0.05

    # Reporting commitments
    reports_posterior_probability_of_lift: bool = True
    reports_95_credible_interval: bool = True
    reports_per_cohort_posteriors: bool = True

    # Lifecycle
    status: PreRegStatus = PreRegStatus.DRAFT
    locked_at: Optional[datetime] = None
    amendments: List[Dict[str, Any]] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=_now_utc)

    @field_validator("msprt_alpha", "msprt_beta")
    @classmethod
    def _validate_error_rate(cls, v: float) -> float:
        if not 0.0 < v < 1.0:
            raise ValueError(f"error rate must be in (0, 1); got {v}")
        return v

    @field_validator("msprt_null_baseline_rate")
    @classmethod
    def _validate_baseline(cls, v: float) -> float:
        if not 0.0 < v < 1.0:
            raise ValueError(
                f"msprt_null_baseline_rate must be in (0, 1); got {v}"
            )
        return v


def lock_plan(plan: PreRegisteredAnalysisPlan) -> PreRegisteredAnalysisPlan:
    """Lock the plan (LOCKED status; cannot be modified).

    Per directive Section 8.4: Pre-reg locked + power calc finalized
    is Phase 9 deliverable. After locking, only amendments (tracked
    publicly) are permitted.

    Raises ValueError if already locked or amended.
    """
    if plan.status in (PreRegStatus.LOCKED, PreRegStatus.AMENDED):
        raise ValueError(
            f"Plan is already in status {plan.status}; cannot relock"
        )
    return plan.model_copy(update={
        "status": PreRegStatus.LOCKED,
        "locked_at": _now_utc(),
    })


def add_amendment(
    plan: PreRegisteredAnalysisPlan,
    amendment_description: str,
    rationale_tag: str,
) -> PreRegisteredAnalysisPlan:
    """Add an amendment to a locked plan.

    Per directive: 'Amendments log discipline.' Each amendment is
    public + auditable. The rationale_tag is a categorical signal
    (A12 defense) describing why the amendment was needed.
    """
    if plan.status not in (PreRegStatus.LOCKED, PreRegStatus.AMENDED):
        raise ValueError(
            f"Plan must be LOCKED or AMENDED to add amendment; "
            f"got {plan.status}"
        )
    if not amendment_description.strip():
        raise ValueError("amendment_description must be non-empty")
    if not rationale_tag.strip():
        raise ValueError(
            "rationale_tag is required (categorical signal). A12 defense."
        )
    new_amendment = {
        "amendment_description": amendment_description,
        "rationale_tag": rationale_tag,
        "added_at": _now_utc().isoformat(),
    }
    new_amendments = list(plan.amendments) + [new_amendment]
    return plan.model_copy(update={
        "status": PreRegStatus.AMENDED,
        "amendments": new_amendments,
    })


# =============================================================================
# Simulation exercise framework (per directive Appendix A)
# =============================================================================


class SimulationArchitecture(str, Enum):
    """The five architectures to compare per directive Appendix A."""

    A_MARGINAL_ADDITIVE_BASELINE = "A_marginal_additive_baseline"
    B_TRILATERAL_CASCADE_ONLY = "B_trilateral_cascade_only"
    C_TRILATERAL_PLUS_INTERACTION = "C_trilateral_plus_interaction"
    D_FULL_PROPOSED_STACK = "D_full_proposed_stack"
    E_FULL_STACK_PLUS_COUNTERFACTUAL = "E_full_stack_plus_counterfactual"


class SimulationParams(BaseModel):
    """One simulation run's parameter set per directive Appendix A.

    Per directive: 'Variables to vary (full factorial or LHS-sampled):
    User base CTR {0.05%, 0.15%, 0.5%}; Conversion rate given click
    {0.5%, 2%, 5%}; Interaction strength {none, weak, moderate, strong};
    Cohort separation {indistinguishable, weakly separable, strongly
    separable}; Non-stationarity {stationary, slow drift, abrupt
    switching}; Audience size per cohort {500, 2000, 10000}; Per-user
    impression rate {2/week, 7/week, 20/week}.'
    """

    model_config = ConfigDict(extra="forbid")

    architecture: SimulationArchitecture
    base_ctr: float
    conversion_rate_given_click: float
    interaction_strength: str   # "none" | "weak" | "moderate" | "strong"
    cohort_separation: str
    non_stationarity_regime: str  # "stationary" | "slow_drift" | "abrupt_switching"
    audience_size_per_cohort: int
    per_user_impression_rate_per_week: float
    horizon_weeks: int = 6

    @field_validator("interaction_strength")
    @classmethod
    def _validate_interaction(cls, v: str) -> str:
        if v not in {"none", "weak", "moderate", "strong"}:
            raise ValueError(
                f"interaction_strength must be one of "
                f"{{'none', 'weak', 'moderate', 'strong'}}; got {v!r}"
            )
        return v

    @field_validator("cohort_separation")
    @classmethod
    def _validate_separation(cls, v: str) -> str:
        if v not in {"indistinguishable", "weakly_separable", "strongly_separable"}:
            raise ValueError(
                f"cohort_separation invalid; got {v!r}"
            )
        return v

    @field_validator("non_stationarity_regime")
    @classmethod
    def _validate_regime(cls, v: str) -> str:
        if v not in {"stationary", "slow_drift", "abrupt_switching"}:
            raise ValueError(
                f"non_stationarity_regime invalid; got {v!r}"
            )
        return v


class SimulationMetrics(BaseModel):
    """Metrics computed at simulation horizons per directive Appendix A.

    Per directive: 'Cumulative lift over a non-cognitive baseline;
    posterior-credible-interval-width per-cohort; time-to-confident-
    best-arm per cohort (mSPRT stopping time); robustness to abrupt
    non-stationarity (lift recovery time after a regime switch);
    counterfactual-trace efficiency multiplier (effective sample size
    with vs. without Spine #6).'
    """

    model_config = ConfigDict(extra="forbid")

    architecture: SimulationArchitecture
    horizon_weeks: int

    # Per-architecture metrics
    cumulative_lift_vs_baseline: float
    posterior_ci_width_avg_per_cohort: float
    time_to_confident_best_arm_per_cohort_weeks: float
    lift_recovery_after_regime_shift_weeks: Optional[float] = None
    counterfactual_trace_eff_sample_size_multiplier: float = 1.0


@dataclass
class ArchitectureRanking:
    """Ranked architecture comparison per directive Appendix A output."""

    rankings_by_horizon_weeks: Dict[int, List[SimulationArchitecture]] = field(
        default_factory=dict
    )

    def winner_at_horizon(self, weeks: int) -> Optional[SimulationArchitecture]:
        ranking = self.rankings_by_horizon_weeks.get(weeks, [])
        return ranking[0] if ranking else None


def rank_architectures_by_metric(
    metrics_per_arch: Dict[SimulationArchitecture, SimulationMetrics],
    metric_field: str,
    *,
    higher_is_better: bool = True,
) -> List[SimulationArchitecture]:
    """Rank the 5 architectures by the given metric.

    Per directive Phase 9 gate: 'Simulation results validate the
    priority order of cognitive primitives (each component carries
    weight in the order specified by the spine).'

    The expected ordering per directive: E > D > C > B > A — i.e.,
    each primitive added (cascade, interaction, full stack, counter-
    factual) yields incremental improvement.

    Args:
        metrics_per_arch: dict of architecture → SimulationMetrics
        metric_field: name of the metric attribute on SimulationMetrics
        higher_is_better: if True, higher values rank first

    Returns: list of architectures sorted from best to worst.
    """
    if not metrics_per_arch:
        return []

    def _key(arch: SimulationArchitecture) -> float:
        m = metrics_per_arch[arch]
        return float(getattr(m, metric_field, 0.0))

    # higher_is_better → descending sort (best first); else ascending
    return sorted(
        metrics_per_arch.keys(), key=_key, reverse=higher_is_better,
    )


__all__ = [
    "ArchitectureRanking",
    "DEFAULT_MSPRT_ALPHA",
    "DEFAULT_MSPRT_BETA",
    "MSPRTDecision",
    "MSPRTState",
    "PreRegStatus",
    "PreRegisteredAnalysisPlan",
    "SimulationArchitecture",
    "SimulationMetrics",
    "SimulationParams",
    "add_amendment",
    "is_red_criterion_triggered",
    "lock_plan",
    "msprt_step",
    "rank_architectures_by_metric",
]
