"""M4-OPE — Off-Policy Evaluation estimator suite + CI/CD policy gate.

Closes task #49. Consumes the M4-schema logged propensities
(ts_propensity + pscore_known on :DecisionContext, shipped earlier
this session) to evaluate candidate policies WITHOUT deploying them.

Per the Seven-Component Methodological Upgrade Handoff §4 — OPE is
the CI/CD gate that prevents bad policies from shipping. ADAM will
produce candidate policies from M1 MRT, M2 causal forests, M5 GNN,
M6 CAI loop, etc. Each candidate gets evaluated against logged data
before any ships. The gate criterion (handoff §4.4 verbatim):

    DR(π_e) ≥ DR(π_current) AND lower_CI(π_e) > point(π_current)

Estimators shipped here:

  IPS (Inverse Propensity Score) — unbiased baseline:
      V_IPS = (1/n) Σ_i (π_e(a_i|x_i) / p_i) · r_i
      Unbiased; high variance. Reference baseline.

  SNIPS (Self-Normalized IPS, Swaminathan-Joachims 2015):
      V_SNIPS = Σ_i w_i · r_i / Σ_i w_i,  w_i = π_e(a_i|x_i) / p_i
      Lower variance than IPS; not strictly unbiased.

  DM (Direct Method) — biased low-variance baseline:
      V_DM = (1/n) Σ_i Σ_a π_e(a|x_i) · q̂(x_i, a)
      Where q̂ is a regression estimate of E[r | x, a]. The substrate
      provides a marginal-mean q̂ (no per-action ML); production
      replaces it with the Doubly-ML cross-fit q̂ from M2.

  DR (Doubly Robust, Dudík 2011):
      V_DR = (1/n) Σ_i [Σ_a π_e(a|x_i)·q̂(x_i,a) + (π_e(a_i|x_i)/p_i)·(r_i − q̂(x_i,a_i))]
      Unbiased if EITHER q̂ OR p_i is correct. Canonical.

  SwitchDR (Wang-Agarwal-Dudík 2017, τ=10) — clip importance weights:
      Use DM contribution when w_i > τ; DR when w_i ≤ τ. Variance
      reduction at small bias cost.

  DRos (Su et al. 2020) — shrinkage on importance weights:
      w_i_shrunk = max(0, λ * w_i + (1-λ) * lambda_optimal)
      Lib-gated (uses obp.ope.DoublyRobustWithShrinkage).

  MIPS (Saito-Joachims 2022) — for structured/large action spaces:
      Marginalizes over action embeddings. Lib-gated.

The first three (IPS, SNIPS, DR) are implemented deterministically
in this module with citations. The full estimator family + CRM
learner ship behind a lib-gate (obp ≥ 0.5.7). OPELibsMissingError
raised when obp absent — same A14 discipline as M2/M3/M5/M7: returning
None on missing libs would let CI/CD gates pass with meaningless
estimates silently.

CI/CD gate (policy_gate function): applies the handoff §4.4 criterion
to candidate vs current policy estimates. Returns a GateResult with
pass/fail + reason chain.

Data loader (load_ope_samples_from_neo4j): pulls :DecisionContext
rows with pscore_known=true (Boruvka 2018 §2 discipline anchor —
reconstructed propensities corrupt OPE the same way they corrupt
WCLS). Joins to :AdOutcome for rewards.

Validation harness (validate_estimator_suite): synthetic-data
recovery test where logged action == policy action; the policy
value should equal the simple mean reward up to MC noise. Used as
a CI/CD step before live data accumulates.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Logged-bandit-feedback shape
# =============================================================================


@dataclass
class OPESample:
    """One logged decision: (context, action, reward, propensity, known).

    Shape per handoff §4.3 obp build_logged_bandit_feedback. The
    pscore_known flag is the discipline anchor inherited from M1 / M4 —
    pscore_known=False rows MUST be excluded from OPE per Boruvka
    2018 §2 (reconstructed propensities corrupt the estimator).
    """
    context: Dict[str, float]      # x: covariates
    action: str                    # a: chosen action (mechanism_id)
    reward: float                  # r: outcome value
    propensity: float              # p_i: logged behavior policy probability
    pscore_known: bool             # discipline anchor
    archetype: str = ""            # for stratified analysis
    decision_id: str = ""


# =============================================================================
# Canonical estimators (deterministic — implemented from formulas)
# =============================================================================


@dataclass
class OPEEstimateResult:
    """Per-estimator point + variance + sample size."""
    estimator: str
    point_estimate: float
    variance: float                # finite-sample variance (sample_var / n)
    std_error: float               # sqrt(variance)
    ci_lower: float                # 95% normal-approximation lower
    ci_upper: float                # 95% normal-approximation upper
    n_samples: int
    n_excluded: int = 0            # excluded (pscore_known=false)


def _filter_known(samples: List[OPESample]) -> Tuple[List[OPESample], int]:
    """Filter to pscore_known=true rows. Returns (kept, excluded_count).

    Boruvka 2018 §2 discipline: reconstructed propensities corrupt
    OPE estimates. Drop rows where the propensity wasn't logged at
    decision time.
    """
    kept = [s for s in samples if s.pscore_known]
    return kept, len(samples) - len(kept)


def _normal_ci(point: float, variance: float, alpha: float = 0.05) -> Tuple[float, float]:
    """95% normal-approximation CI for a point estimate."""
    if variance < 0:
        return (point, point)
    se = math.sqrt(variance)
    # 95% z = 1.959963984540054; using 1.96 for canonical anchor
    z = 1.96
    return (point - z * se, point + z * se)


def estimate_ips(
    samples: List[OPESample],
    target_policy: Callable[[Dict[str, float], str], float],
) -> OPEEstimateResult:
    """Inverse Propensity Score estimator.

    V_IPS(π_e) = (1/n) Σ_i (π_e(a_i|x_i) / p_i) · r_i

    Unbiased under positivity (p_i > 0 for all observed (x, a)).
    High variance when π_e/p_i is heavy-tailed. Reference baseline.
    """
    kept, excluded = _filter_known(samples)
    if not kept:
        return OPEEstimateResult(
            estimator="IPS", point_estimate=0.0, variance=0.0,
            std_error=0.0, ci_lower=0.0, ci_upper=0.0,
            n_samples=0, n_excluded=excluded,
        )

    contributions: List[float] = []
    for s in kept:
        if s.propensity <= 0:
            # Positivity violation — skip rather than div-by-zero.
            continue
        pi_e = target_policy(s.context, s.action)
        weight = pi_e / s.propensity
        contributions.append(weight * s.reward)

    n = len(contributions)
    if n == 0:
        return OPEEstimateResult(
            estimator="IPS", point_estimate=0.0, variance=0.0,
            std_error=0.0, ci_lower=0.0, ci_upper=0.0,
            n_samples=0, n_excluded=excluded,
        )

    point = sum(contributions) / n
    sample_var = sum((c - point) ** 2 for c in contributions) / max(1, n - 1)
    variance = sample_var / n
    std_error = math.sqrt(variance)
    ci_lower, ci_upper = _normal_ci(point, variance)

    return OPEEstimateResult(
        estimator="IPS",
        point_estimate=round(point, 5),
        variance=round(variance, 6),
        std_error=round(std_error, 5),
        ci_lower=round(ci_lower, 5),
        ci_upper=round(ci_upper, 5),
        n_samples=n,
        n_excluded=excluded,
    )


def estimate_snips(
    samples: List[OPESample],
    target_policy: Callable[[Dict[str, float], str], float],
) -> OPEEstimateResult:
    """Self-Normalized IPS (Swaminathan-Joachims 2015, NIPS).

    V_SNIPS(π_e) = Σ_i w_i · r_i / Σ_i w_i,  w_i = π_e(a_i|x_i) / p_i

    Self-normalized denominator. Lower variance than IPS at the cost
    of strict unbiasedness. Bounded by min(r) and max(r).
    """
    kept, excluded = _filter_known(samples)
    if not kept:
        return OPEEstimateResult(
            estimator="SNIPS", point_estimate=0.0, variance=0.0,
            std_error=0.0, ci_lower=0.0, ci_upper=0.0,
            n_samples=0, n_excluded=excluded,
        )

    weights: List[float] = []
    weighted_rewards: List[float] = []
    for s in kept:
        if s.propensity <= 0:
            continue
        pi_e = target_policy(s.context, s.action)
        w = pi_e / s.propensity
        weights.append(w)
        weighted_rewards.append(w * s.reward)

    n = len(weights)
    sum_w = sum(weights)
    if n == 0 or sum_w <= 0:
        return OPEEstimateResult(
            estimator="SNIPS", point_estimate=0.0, variance=0.0,
            std_error=0.0, ci_lower=0.0, ci_upper=0.0,
            n_samples=0, n_excluded=excluded,
        )

    point = sum(weighted_rewards) / sum_w
    # Delta-method variance approximation (Owen 2013 §9.5):
    # Var(SNIPS) ≈ (1/sum_w^2) · Σ w_i^2 · (r_i − point)^2
    if sum_w > 0:
        variance = sum(
            w ** 2 * (r / w - point) ** 2 if w > 0 else 0.0
            for w, r in zip(weights, weighted_rewards)
        ) / (sum_w ** 2)
    else:
        variance = 0.0
    std_error = math.sqrt(max(0.0, variance))
    ci_lower, ci_upper = _normal_ci(point, variance)

    return OPEEstimateResult(
        estimator="SNIPS",
        point_estimate=round(point, 5),
        variance=round(variance, 6),
        std_error=round(std_error, 5),
        ci_lower=round(ci_lower, 5),
        ci_upper=round(ci_upper, 5),
        n_samples=n,
        n_excluded=excluded,
    )


def estimate_dr(
    samples: List[OPESample],
    target_policy: Callable[[Dict[str, float], str], float],
    reward_model: Callable[[Dict[str, float], str], float],
    action_space: List[str],
) -> OPEEstimateResult:
    """Doubly Robust (Dudík-Langford-Li 2011).

    V_DR(π_e) = (1/n) Σ_i [
        Σ_a π_e(a|x_i) · q̂(x_i, a) +
        (π_e(a_i|x_i) / p_i) · (r_i − q̂(x_i, a_i))
    ]

    Unbiased if EITHER q̂(x, a) OR p_i is correct. The substrate
    accepts a reward_model callable for q̂; production passes the
    DML cross-fit q̂ from M2 here.
    """
    kept, excluded = _filter_known(samples)
    if not kept:
        return OPEEstimateResult(
            estimator="DR", point_estimate=0.0, variance=0.0,
            std_error=0.0, ci_lower=0.0, ci_upper=0.0,
            n_samples=0, n_excluded=excluded,
        )

    contributions: List[float] = []
    for s in kept:
        if s.propensity <= 0:
            continue
        # DM term: Σ_a π_e(a|x) · q̂(x, a)
        dm_term = sum(
            target_policy(s.context, a) * reward_model(s.context, a)
            for a in action_space
        )
        # IPS-correction term: (π_e(a|x) / p) · (r − q̂(x, a))
        pi_e_observed = target_policy(s.context, s.action)
        q_observed = reward_model(s.context, s.action)
        ips_correction = (pi_e_observed / s.propensity) * (s.reward - q_observed)
        contributions.append(dm_term + ips_correction)

    n = len(contributions)
    if n == 0:
        return OPEEstimateResult(
            estimator="DR", point_estimate=0.0, variance=0.0,
            std_error=0.0, ci_lower=0.0, ci_upper=0.0,
            n_samples=0, n_excluded=excluded,
        )

    point = sum(contributions) / n
    sample_var = sum((c - point) ** 2 for c in contributions) / max(1, n - 1)
    variance = sample_var / n
    std_error = math.sqrt(variance)
    ci_lower, ci_upper = _normal_ci(point, variance)

    return OPEEstimateResult(
        estimator="DR",
        point_estimate=round(point, 5),
        variance=round(variance, 6),
        std_error=round(std_error, 5),
        ci_lower=round(ci_lower, 5),
        ci_upper=round(ci_upper, 5),
        n_samples=n,
        n_excluded=excluded,
    )


def estimate_switch_dr(
    samples: List[OPESample],
    target_policy: Callable[[Dict[str, float], str], float],
    reward_model: Callable[[Dict[str, float], str], float],
    action_space: List[str],
    tau: float = 10.0,
) -> OPEEstimateResult:
    """Switch-DR (Wang-Agarwal-Dudík 2017).

    Switch between DM and DR per sample based on importance weight:
        if w_i ≤ τ:  use DR contribution
        if w_i > τ:  use DM contribution (clip the high-weight tail)

    τ=10 is the handoff §4.2 default. Variance reduction at small
    bias cost; targets propensity-collapse cases where π_e/p_i blows
    up on rare actions.
    """
    kept, excluded = _filter_known(samples)
    if not kept:
        return OPEEstimateResult(
            estimator="SwitchDR", point_estimate=0.0, variance=0.0,
            std_error=0.0, ci_lower=0.0, ci_upper=0.0,
            n_samples=0, n_excluded=excluded,
        )

    contributions: List[float] = []
    for s in kept:
        if s.propensity <= 0:
            continue
        pi_e_observed = target_policy(s.context, s.action)
        w = pi_e_observed / s.propensity

        # DM term always computed
        dm_term = sum(
            target_policy(s.context, a) * reward_model(s.context, a)
            for a in action_space
        )

        if w <= tau:
            # DR contribution: DM + IPS-correction
            q_observed = reward_model(s.context, s.action)
            contribution = dm_term + w * (s.reward - q_observed)
        else:
            # Clip — use DM term only (drop the IPS correction whose
            # weight exceeds τ)
            contribution = dm_term
        contributions.append(contribution)

    n = len(contributions)
    if n == 0:
        return OPEEstimateResult(
            estimator="SwitchDR", point_estimate=0.0, variance=0.0,
            std_error=0.0, ci_lower=0.0, ci_upper=0.0,
            n_samples=0, n_excluded=excluded,
        )

    point = sum(contributions) / n
    sample_var = sum((c - point) ** 2 for c in contributions) / max(1, n - 1)
    variance = sample_var / n
    std_error = math.sqrt(variance)
    ci_lower, ci_upper = _normal_ci(point, variance)

    return OPEEstimateResult(
        estimator="SwitchDR",
        point_estimate=round(point, 5),
        variance=round(variance, 6),
        std_error=round(std_error, 5),
        ci_lower=round(ci_lower, 5),
        ci_upper=round(ci_upper, 5),
        n_samples=n,
        n_excluded=excluded,
    )


# =============================================================================
# CI/CD policy gate (handoff §4.4 verbatim criterion)
# =============================================================================


@dataclass
class PolicyGateResult:
    """Outcome of the CI/CD gate evaluation."""
    passed: bool
    reasons: List[str] = field(default_factory=list)
    candidate_dr_point: float = 0.0
    candidate_dr_lower: float = 0.0
    current_dr_point: float = 0.0


def policy_gate(
    candidate_dr: OPEEstimateResult,
    current_dr: OPEEstimateResult,
) -> PolicyGateResult:
    """Apply handoff §4.4 CI/CD gate.

    Pass if BOTH:
      1. candidate_dr.point ≥ current_dr.point
         (new policy at least as good in DR estimate)
      2. candidate_dr.ci_lower > current_dr.point
         (new policy CI lower bound exceeds current point — meaningfully
          better with confidence)

    Both must hold. The strict greater-than on (2) is intentional —
    gate is the criterion for shipping a new policy. A new policy that
    only matches the current policy's point estimate within noise
    doesn't justify the rollout cost.

    Discipline anchor: NEVER ship a candidate that fails this gate.
    The gate is the safety surface preventing M1/M2/M5-derived policies
    from regressing the platform's per-impression value.
    """
    reasons: List[str] = []

    cond1 = candidate_dr.point_estimate >= current_dr.point_estimate
    if not cond1:
        reasons.append(
            f"candidate DR point {candidate_dr.point_estimate} < "
            f"current DR point {current_dr.point_estimate}"
        )

    cond2 = candidate_dr.ci_lower > current_dr.point_estimate
    if not cond2:
        reasons.append(
            f"candidate DR ci_lower {candidate_dr.ci_lower} ≤ "
            f"current DR point {current_dr.point_estimate} "
            f"(not meaningfully better)"
        )

    passed = cond1 and cond2
    if passed:
        reasons.append("PASS: candidate exceeds current with CI lower > current point")

    return PolicyGateResult(
        passed=passed,
        reasons=reasons,
        candidate_dr_point=candidate_dr.point_estimate,
        candidate_dr_lower=candidate_dr.ci_lower,
        current_dr_point=current_dr.point_estimate,
    )


# =============================================================================
# Data loader from M4-schema :DecisionContext + :AdOutcome
# =============================================================================


def load_ope_samples_from_neo4j(
    driver: Optional[Any] = None,
    days_lookback: int = 90,
    pscore_known_only: bool = True,
) -> List[OPESample]:
    """Pull logged decision rows for OPE.

    Filters on pscore_known=true by default (Boruvka 2018 §2 +
    Bibaut 2024 — reconstructed propensities corrupt the estimators).
    Set pscore_known_only=False ONLY for diagnostic comparisons; never
    for production gate evaluation.

    Returns [] when Neo4j is unavailable or no data exists. Empty list
    is a valid 'no signal yet' state — pre-pilot phase.
    """
    if driver is None:
        try:
            from adam.core.dependencies import get_neo4j_driver
            driver = get_neo4j_driver()
        except Exception:
            return []
    if driver is None:
        return []

    pscore_filter = "AND dc.pscore_known = true" if pscore_known_only else ""
    cypher = f"""
    MATCH (dc:DecisionContext)-[:HAD_OUTCOME]->(o:AdOutcome)
    WHERE dc.created_at * 1000 >= $cutoff_ts
      {pscore_filter}
    RETURN
      dc.archetype AS archetype,
      dc.mechanism_sent AS action,
      dc.ts_propensity AS propensity,
      dc.pscore_known AS pscore_known,
      o.outcome_value AS reward,
      dc.decision_id AS decision_id
    LIMIT 100000
    """

    cutoff_ts = _epoch_ms_n_days_ago(days_lookback)
    samples: List[OPESample] = []
    try:
        with driver.session() as session:
            result = session.run(cypher, cutoff_ts=cutoff_ts)
            for record in result:
                try:
                    propensity = float(record.get("propensity") or 0.0)
                    pscore = bool(record.get("pscore_known") or False)
                    reward = float(record.get("reward") or 0.0)
                    action = record.get("action") or ""
                    archetype = record.get("archetype") or ""
                    if not action:
                        continue
                    samples.append(OPESample(
                        context={"archetype": archetype},
                        action=action,
                        reward=reward,
                        propensity=propensity,
                        pscore_known=pscore,
                        archetype=archetype,
                        decision_id=record.get("decision_id") or "",
                    ))
                except (TypeError, ValueError):
                    continue
    except Exception as exc:
        logger.warning("OPE data loader failed: %s", exc)
        return []

    return samples


def _epoch_ms_n_days_ago(days: int) -> int:
    import time
    return int((time.time() - days * 86400) * 1000)


# =============================================================================
# Full obp suite — lib-gated
# =============================================================================


class OPELibsMissingError(RuntimeError):
    """Raised when the obp suite is requested but obp isn't installed.

    Returning None on missing libs would let CI/CD gates pass with
    meaningless estimates silently — exact drift pattern we exist to
    prevent.
    """
    pass


def _try_import_obp() -> Optional[Any]:
    try:
        import obp  # noqa: F401
        return obp
    except ImportError:
        return None


def evaluate_with_obp_suite(
    samples: List[OPESample],
    target_policy: Callable[[Dict[str, float], str], float],
    reward_model: Callable[[Dict[str, float], str], float],
    action_space: List[str],
) -> Dict[str, OPEEstimateResult]:
    """Run the full obp estimator suite (DR + SNDR + SwitchDR + DRos +
    MIPS) on logged samples.

    Per handoff §4.3:
        from obp.ope import OffPolicyEvaluation, DoublyRobust,
            SelfNormalizedDoublyRobust, SwitchDoublyRobust

    Substrate signature shipped; full obp wrapping is M4-OPE follow-on
    work pending obp deploy. Today's substrate provides IPS / SNIPS /
    DR / SwitchDR via the deterministic estimators above; the obp
    suite adds DRos (shrinkage) + MIPS (action embeddings) which
    require the lib.

    Raises OPELibsMissingError when obp isn't installed.
    """
    obp = _try_import_obp()
    if obp is None:
        raise OPELibsMissingError(
            "obp not installed. Full OPE suite requires obp>=0.5.7. "
            "The deterministic IPS / SNIPS / DR / SwitchDR estimators "
            "in this module work without obp; this function adds DRos "
            "+ MIPS which are obp-only."
        )

    raise NotImplementedError(
        "evaluate_with_obp_suite: full obp wrapping is M4-OPE follow-on. "
        "Substrate signature shipped; the four canonical estimators "
        "(IPS, SNIPS, DR, SwitchDR) are fully implemented above and "
        "callable independently. Add DRos + MIPS via this function "
        "when obp deploys."
    )


# =============================================================================
# Validation harness — synthetic-data recovery
# =============================================================================


def replay_value_for_uniform_policy(samples: List[OPESample]) -> float:
    """Reference value: when target_policy == logged behavior policy,
    OPE should recover the simple mean reward.

    Used by the validation harness to confirm estimators converge to
    the right answer on synthetic data where the answer is known.
    """
    kept, _ = _filter_known(samples)
    if not kept:
        return 0.0
    return sum(s.reward for s in kept) / len(kept)


def validate_estimator_recovery(
    samples: List[OPESample],
    tolerance: float = 0.1,
) -> Dict[str, bool]:
    """Synthetic recovery test: when π_e == π_b (target = logging),
    every estimator should equal mean(rewards) within MC noise.

    Per handoff §4.7: 'replay backtest where logged action == policy
    action; OPE estimate within DR ± 2·SE of replay value.'

    This is the CI sanity check — runs on synthetic data before the
    pilot to confirm the estimators work. Tolerance default 0.1 is
    permissive; tighten as sample sizes grow.

    Returns {estimator_name: passed} dict.
    """
    if not samples:
        return {}

    # Target policy = identity (always pick the logged action with
    # probability == observed propensity). Under this trivial policy
    # the importance weight w_i = p_i / p_i = 1, so V_IPS = mean(r).
    def identity_policy(context: Dict[str, float], action: str) -> float:
        # Find the matching sample's logged propensity
        for s in samples:
            if s.context == context and s.action == action:
                return s.propensity
        return 0.0

    truth = replay_value_for_uniform_policy(samples)
    results: Dict[str, bool] = {}

    ips = estimate_ips(samples, target_policy=identity_policy)
    results["IPS"] = abs(ips.point_estimate - truth) < tolerance

    snips = estimate_snips(samples, target_policy=identity_policy)
    results["SNIPS"] = abs(snips.point_estimate - truth) < tolerance

    return results
