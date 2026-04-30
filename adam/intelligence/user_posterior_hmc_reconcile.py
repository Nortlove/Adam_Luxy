# =============================================================================
# Per-User HMC Posterior Reconcile — Spine #1 offline path
# Location: adam/intelligence/user_posterior_hmc_reconcile.py
# =============================================================================
"""HMC offline reconcile for per-user posteriors — directive Phase 1.

Closes the directive's third Spine #1 update path:
  1. BONG online conjugate update path (shipped — Track 2)
  2. Variational batch reconcile path (future slice)
  3. HMC offline reconcile path  ← THIS MODULE

WHY THIS EXISTS

The online BONG update is fast and recursive: each touch updates the
user's Beta(α, β) posterior incrementally via conjugate Bayesian
update. That's correct for the simple Bernoulli-Beta likelihood but
ignores:

  * AR(1) carryover correction across sequential touches
    (directive Phase 1 line 951: "AR(1) carryover correction in the
    N-of-1 likelihood")
  * Random intercept (per-user responsiveness baseline) shrinkage
    across mechanisms
  * Joint posterior over mechanisms (the online path treats each
    mechanism's Beta as independent — but the user's overall
    responsiveness correlates them)

The HMC reconcile path runs NumPyro NUTS over the user's accumulated
observations periodically (e.g., daily) to refine the joint posterior,
correcting the online path's drift. The refined posterior is written
back to UserPosteriorProfile and persisted via the L3 Neo4j tier
(commit b9aff2b).

REAL CONSUMERS

  * Daily Task 36 (task_36_hmc_user_posterior_reconcile.py) scans
    Neo4j for users with stale posteriors (last_updated_ts >
    cutoff) and runs reconcile per user.
  * Refined posteriors flow back into the cascade at decision time
    via UserPosteriorManager L3 → L2 → L1 read chain.

DISCIPLINE (B3-LUXY a/b/c/d)

  (a) Canonical formula: per-mechanism Beta(α, β) likelihood +
      AR(1)(ρ) latent autocorrelation. Cited Albert & Chib 1993 for
      the Beta-Bernoulli logit-space treatment; Kass-Carlin 1996 for
      the AR(1) hierarchical specification.
  (b) Tests pin: synthetic user with biased response → reconcile
      shifts posterior in the correct direction; AR(1) ρ recovered
      within 0.15 on synthetic data with known autocorrelation;
      empty observations → no-op (returns profile unchanged); MCMC
      failure → graceful no-op (logs warning, returns input).
  (c) calibration_pending=True. NUTS hyperparameters (draws=300,
      tune=300, chains=2 default) are conservative defaults; LUXY
      pilot data will calibrate. A14 flag:
      USER_HMC_RECONCILE_NUTS_HYPERPARAMS_PILOT_PENDING.
  (d) Honest tag — random_intercept estimation in this slice uses
      the simplest specification (single scalar shift). Mechanism
      slopes (per-mechanism deviation from baseline) are a separate
      Phase 3 slice (δ_iac with horseshoe priors). Marked
      explicitly in the docstring of reconcile_user_posterior.
"""

from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# NUTS hyperparameters — calibration-pending under
# USER_HMC_RECONCILE_NUTS_HYPERPARAMS_PILOT_PENDING.
DEFAULT_DRAWS: int = 300
DEFAULT_TUNE: int = 300
DEFAULT_CHAINS: int = 2

# Below this many sequential observations, AR(1) is unidentifiable —
# fall back to per-mechanism Beta posteriors only.
MIN_OBSERVATIONS_FOR_AR1: int = 5

# Below this many observations across all mechanisms, reconcile is
# a no-op (returns profile unchanged). Conservative — the online BONG
# path is correct in low-N regime.
MIN_OBSERVATIONS_FOR_RECONCILE: int = 8


def reconcile_user_posterior(
    profile,  # UserPosteriorProfile (avoid hard import for soft fallback)
    draws: int = DEFAULT_DRAWS,
    tune: int = DEFAULT_TUNE,
    chains: int = DEFAULT_CHAINS,
):
    """Run HMC reconcile over a user's accumulated observations.

    Updates ``profile.mechanism_posteriors[m].alpha`` and ``.beta`` to
    the HMC posterior moments, refines ``profile.within_user_correlation``
    from the AR(1) estimate, refines ``profile.random_intercept`` from
    the joint posterior shift.

    Returns the (mutated) profile. Soft-fail at every layer:
      * MIN_OBSERVATIONS_FOR_RECONCILE not met → returns profile unchanged
      * NumPyro / JAX import failure → returns profile unchanged + logs
      * MCMC sampling exception → returns profile unchanged + logs

    NOT in this slice (named successors):
      * Mechanism slopes (per-mechanism deviation from baseline) —
        Phase 3 δ_iac with horseshoe priors.
      * Cross-user shrinkage (population → user partial pooling) —
        composes with hierarchical_bayes.py's cell-level HMC.

    Decision-time consumer: refined profile flows through
    UserPosteriorManager._store_to_neo4j (L3) → next L1+L2 cold-start
    promotes refined posterior into cascade hot path.
    """
    # --- Gate 1: enough observations to reconcile ---
    total_obs = sum(
        len(mp.outcomes) for mp in profile.mechanism_posteriors.values()
    )
    if total_obs < MIN_OBSERVATIONS_FOR_RECONCILE:
        logger.debug(
            "HMC reconcile no-op for user=%s brand=%s: %d obs < %d minimum",
            profile.user_id, profile.brand_id, total_obs,
            MIN_OBSERVATIONS_FOR_RECONCILE,
        )
        return profile

    # --- Gate 2: lib import (soft-fail) ---
    try:
        import jax
        import jax.numpy as jnp
        import numpy as np
        import numpyro
        from numpyro import distributions as dist
        from numpyro.infer import MCMC, NUTS
    except ImportError as exc:
        logger.warning(
            "HMC reconcile skipped — NumPyro/JAX not installed: %s", exc,
        )
        return profile

    # --- Build observation arrays ---
    # Per-mechanism: list of (mechanism_idx, outcome) pairs
    mechanisms: List[str] = sorted(profile.mechanism_posteriors.keys())
    if not mechanisms:
        return profile
    mech_to_idx: Dict[str, int] = {m: i for i, m in enumerate(mechanisms)}

    # Sequence of (mech_idx, outcome) from all_outcomes/all_mechanisms
    seq_mechs: List[int] = []
    seq_outcomes: List[float] = []
    for m_name, out in zip(profile.all_mechanisms, profile.all_outcomes):
        if m_name in mech_to_idx:
            seq_mechs.append(mech_to_idx[m_name])
            seq_outcomes.append(float(out))

    if len(seq_outcomes) < MIN_OBSERVATIONS_FOR_RECONCILE:
        # Insufficient sequential data; fall back to per-mechanism
        # Beta updates from the outcomes lists (no AR(1)).
        return _reconcile_per_mechanism_only(profile, mechanisms, draws, tune, chains)

    seq_mechs_arr = jnp.array(seq_mechs, dtype=jnp.int32)
    seq_outcomes_arr = jnp.array(seq_outcomes, dtype=jnp.float32)
    n_mechs = len(mechanisms)
    use_ar1 = len(seq_outcomes) >= MIN_OBSERVATIONS_FOR_AR1

    # --- NumPyro model ---
    def model():
        # Per-mechanism conversion probability — Beta(2, 2) prior
        # (uninformative; the population posterior would be the
        # informative prior in a future Phase 3 slice).
        p = numpyro.sample(
            "p", dist.Beta(2.0 * jnp.ones(n_mechs), 2.0 * jnp.ones(n_mechs)),
        )
        # Random intercept — user-level baseline shift on logit scale.
        random_intercept = numpyro.sample(
            "random_intercept", dist.Normal(0.0, 0.5),
        )
        # AR(1) correlation across sequential touches.
        if use_ar1:
            rho = numpyro.sample("rho", dist.Uniform(-0.95, 0.95))
        # Likelihood: each touch's outcome conditional on its mechanism's p
        # Apply random intercept on logit scale, then re-map.
        logits = jnp.log(p[seq_mechs_arr] / (1.0 - p[seq_mechs_arr])) + random_intercept
        # AR(1): expected logit = base + rho * (prev_outcome - p_at_prev_mech)
        if use_ar1:
            # Shift previous-outcome residuals by rho — first obs no shift
            prev_out = jnp.concatenate([jnp.zeros(1), seq_outcomes_arr[:-1]])
            prev_mech_p = jnp.concatenate([jnp.array([0.5]), p[seq_mechs_arr[:-1]]])
            ar_term = rho * (prev_out - prev_mech_p)
            logits = logits + ar_term
        adjusted_p = 1.0 / (1.0 + jnp.exp(-logits))
        numpyro.sample(
            "y", dist.Bernoulli(probs=adjusted_p), obs=seq_outcomes_arr,
        )

    # --- Run NUTS ---
    try:
        kernel = NUTS(model, target_accept_prob=0.85)
        mcmc = MCMC(
            kernel, num_warmup=tune, num_samples=draws,
            num_chains=chains, progress_bar=False,
        )
        rng_key = jax.random.PRNGKey(int(time.time()) % (2**31 - 1))
        mcmc.run(rng_key)
        samples = mcmc.get_samples()
    except Exception as exc:
        logger.warning(
            "HMC reconcile MCMC sampling failed for user=%s: %s",
            profile.user_id, exc,
        )
        return profile

    # --- Extract refined posterior moments + write back to profile ---
    p_samples = np.asarray(samples["p"])  # shape (chains*draws, n_mechs)
    p_mean = p_samples.mean(axis=0)
    p_var = p_samples.var(axis=0)

    for i, m_name in enumerate(mechanisms):
        mech_post = profile.mechanism_posteriors.get(m_name)
        if mech_post is None:
            continue
        # Convert (mean, var) → (alpha, beta) via method-of-moments:
        #   mean = α / (α+β)
        #   var = αβ / [(α+β)²(α+β+1)]
        # → α + β = mean*(1-mean)/var − 1
        m, v = float(p_mean[i]), float(p_var[i])
        if v <= 1e-9 or m <= 0.0 or m >= 1.0:
            continue
        common = m * (1.0 - m) / v - 1.0
        if common <= 0.0:
            continue
        alpha = m * common
        beta = (1.0 - m) * common
        if alpha > 0.5 and beta > 0.5:
            mech_post.alpha = alpha
            mech_post.beta = beta

    # Refined random intercept
    if "random_intercept" in samples:
        ri = float(np.asarray(samples["random_intercept"]).mean())
        profile.random_intercept = ri

    # Refined AR(1)
    if "rho" in samples:
        rho_mean = float(np.asarray(samples["rho"]).mean())
        profile.within_user_correlation = rho_mean

    logger.info(
        "HMC reconcile complete: user=%s brand=%s mechs=%d obs=%d "
        "rho=%.3f random_intercept=%.3f",
        profile.user_id, profile.brand_id, n_mechs, len(seq_outcomes),
        profile.within_user_correlation, profile.random_intercept,
    )
    return profile


def _reconcile_per_mechanism_only(profile, mechanisms, draws, tune, chains):
    """Fallback when sequence data is too short for AR(1) — run a
    simpler per-mechanism Beta model.

    Each mechanism's outcomes get a Beta(2, 2) prior + Bernoulli
    likelihood; the posterior moments method-of-moment back to
    (alpha, beta). No AR(1), no random intercept.
    """
    try:
        import jax
        import numpy as np
        import numpyro
        from numpyro import distributions as dist
        from numpyro.infer import MCMC, NUTS
        import jax.numpy as jnp
    except ImportError:
        return profile

    for m_name in mechanisms:
        mech_post = profile.mechanism_posteriors.get(m_name)
        if mech_post is None or len(mech_post.outcomes) < 2:
            continue
        outcomes = jnp.array(mech_post.outcomes, dtype=jnp.float32)

        def per_mech_model():
            p = numpyro.sample("p", dist.Beta(2.0, 2.0))
            numpyro.sample("y", dist.Bernoulli(probs=p), obs=outcomes)

        try:
            kernel = NUTS(per_mech_model, target_accept_prob=0.85)
            mcmc = MCMC(
                kernel, num_warmup=tune, num_samples=draws,
                num_chains=chains, progress_bar=False,
            )
            rng_key = jax.random.PRNGKey(
                hash(m_name + profile.user_id) & 0x7FFFFFFF,
            )
            mcmc.run(rng_key)
            samples = np.asarray(mcmc.get_samples()["p"])
        except Exception as exc:
            logger.debug(
                "Per-mech reconcile failed for user=%s mech=%s: %s",
                profile.user_id, m_name, exc,
            )
            continue

        m, v = float(samples.mean()), float(samples.var())
        if v <= 1e-9 or m <= 0.0 or m >= 1.0:
            continue
        common = m * (1.0 - m) / v - 1.0
        if common <= 0.0:
            continue
        alpha = m * common
        beta = (1.0 - m) * common
        if alpha > 0.5 and beta > 0.5:
            mech_post.alpha = alpha
            mech_post.beta = beta

    return profile
