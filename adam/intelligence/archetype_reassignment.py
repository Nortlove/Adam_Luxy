"""One-shot archetype reassignment policy per Q27=(ε).

Q27=(ε) policy: cold-start archetype is provisional. After N=20
bids of accumulated evidence, evaluate the per-user
maximizer_tendency Beta posterior against each of 8 archetype
priors. If a different archetype's prior fits the accumulated
posterior substantially better (log-likelihood ratio > 3 vs
assigned), reassign to that archetype. After this single
evaluation, the archetype is locked for pilot regardless of
outcome (`archetype_reassigned = True` flag set). Post-pilot
graduation to continuous Bayesian reassignment via S5.5 nightly
retrain.

W.2a ships the policy LOGIC. The policy DEPENDS on
maximizer_tendency Beta posterior being available on the buyer
profile — that's W.2b's wiring (extends UNCERTAINTY_DIMENSIONS).
Until W.2b lands, evaluate_reassignment returns None
(maximizer_tendency posterior absent). This is intentional
gradual activation: W.2a ships the framework + integration site
+ Beta LLR computation; W.2b activates the policy by populating
the construct W.2a reads from.

Bid-time latency budget: <2ms when policy fires (rare — once per
buyer at bid 20). Zero cost when policy doesn't apply (early
return on guard checks).
"""
from math import lgamma
from typing import Any, Dict, Optional

from adam.cold_start.models.enums import ArchetypeID


REASSIGNMENT_BID_THRESHOLD: int = 20
"""Q27=(ε) N=20 bids before reassignment opportunity fires."""

REASSIGNMENT_LOG_LIKELIHOOD_RATIO_THRESHOLD: float = 3.0
"""Log-likelihood ratio threshold (alternative archetype vs
current assigned) for reassignment to fire. Higher = more
conservative; reassignment only when strong evidence."""

MAXIMIZER_TENDENCY_DIMENSION: str = "maximizer_tendency"
"""Construct dimension W.2b will add to UNCERTAINTY_DIMENSIONS.
W.2a's reassignment evaluator reads from this dimension's Beta
posterior. Until W.2b lands, this construct doesn't exist on
profiles → evaluate_reassignment returns None."""


def evaluate_reassignment(profile: Any) -> Optional[ArchetypeID]:
    """Evaluate one-shot archetype reassignment per Q27=(ε).

    Args:
        profile: BuyerUncertaintyProfile with archetype field +
            reassignment-policy metadata + (W.2b dependency)
            maximizer_tendency in profile.constructs dict.

    Returns:
        New ArchetypeID if reassignment fires, None otherwise.
        Caller is responsible for applying the reassignment to
        the profile (updating archetype field, setting
        archetype_reassigned = True).

    Reassignment fires only when:
        1. profile.archetype_reassigned is False
        2. profile.archetype is not None (already assigned)
        3. profile.bids_since_archetype_assignment ==
           REASSIGNMENT_BID_THRESHOLD (exactly; not >=)
        4. profile.constructs[MAXIMIZER_TENDENCY_DIMENSION] is
           present (W.2b dependency)
        5. The maximizer_tendency posterior on profile fits a
           different archetype's prior with log-likelihood
           ratio > REASSIGNMENT_LOG_LIKELIHOOD_RATIO_THRESHOLD
    """
    if getattr(profile, "archetype_reassigned", False):
        return None
    current_archetype_value = getattr(profile, "archetype", None)
    if current_archetype_value is None:
        return None
    if (
        getattr(profile, "bids_since_archetype_assignment", 0)
        != REASSIGNMENT_BID_THRESHOLD
    ):
        return None

    # W.2b dependency: maximizer_tendency Beta posterior on profile.
    constructs = getattr(profile, "constructs", {})
    maximizer = constructs.get(MAXIMIZER_TENDENCY_DIMENSION)
    if maximizer is None:
        # W.2b hasn't shipped; reassignment policy dormant. Set the
        # one-shot guard anyway so the policy doesn't keep checking
        # forever — but caller is responsible for guard-flag write
        # via the cascade integration.
        return None

    user_alpha = getattr(maximizer, "alpha", None)
    user_beta = getattr(maximizer, "beta", None)
    if user_alpha is None or user_beta is None:
        return None

    # Coerce string archetype back to enum for comparison.
    try:
        current_archetype = ArchetypeID(current_archetype_value)
    except ValueError:
        return None

    # Compute log-likelihood under each archetype's maximizer prior.
    archetype_priors = _archetype_maximizer_priors()

    log_likelihoods: Dict[ArchetypeID, float] = {}
    for archetype_id, (prior_alpha, prior_beta) in archetype_priors.items():
        log_likelihoods[archetype_id] = _beta_log_likelihood(
            float(user_alpha), float(user_beta),
            prior_alpha, prior_beta,
        )

    if current_archetype not in log_likelihoods:
        return None

    current_ll = log_likelihoods[current_archetype]
    other_archetypes = [
        a for a in log_likelihoods if a != current_archetype
    ]
    if not other_archetypes:
        return None
    best_other = max(other_archetypes, key=lambda a: log_likelihoods[a])
    log_likelihood_ratio = log_likelihoods[best_other] - current_ll

    if log_likelihood_ratio > REASSIGNMENT_LOG_LIKELIHOOD_RATIO_THRESHOLD:
        return best_other
    return None


def _archetype_maximizer_priors() -> Dict[ArchetypeID, tuple]:
    """Return archetype → (alpha, beta) prior parameters by reading
    A.2's per-archetype maximizer Beta priors.

    Wraps adam.cold_start.priors.maximizer_tendency.ARCHETYPE_-
    MAXIMIZER_PRIORS so the LLR computation has a clean
    (alpha, beta) tuple shape.
    """
    from adam.cold_start.priors.maximizer_tendency import (
        ARCHETYPE_MAXIMIZER_PRIORS,
    )
    result: Dict[ArchetypeID, tuple] = {}
    for archetype_id, beta_dist in ARCHETYPE_MAXIMIZER_PRIORS.items():
        result[archetype_id] = (
            float(beta_dist.alpha),
            float(beta_dist.beta),
        )
    return result


def _beta_log_likelihood(
    observed_alpha: float, observed_beta: float,
    prior_alpha: float, prior_beta: float,
) -> float:
    """Log of the marginal likelihood of an observed Beta posterior
    Beta(α_obs, β_obs) under a prior Beta(α0, β0).

    Uses the Beta-Binomial conjugate identity:
        log p(data | prior) = log B(α_obs + α0, β_obs + β0)
                            - log B(α0, β0)
    where B is the Beta function and log B = lgamma(α) + lgamma(β)
    - lgamma(α + β). Numerically stable via lgamma.
    """
    return (
        lgamma(observed_alpha + prior_alpha)
        + lgamma(observed_beta + prior_beta)
        - lgamma(observed_alpha + observed_beta + prior_alpha + prior_beta)
        + lgamma(prior_alpha + prior_beta)
        - lgamma(prior_alpha)
        - lgamma(prior_beta)
    )
