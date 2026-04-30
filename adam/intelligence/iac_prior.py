# =============================================================================
# δ_iac Population → Per-User Informative Prior
# Location: adam/intelligence/iac_prior.py
# =============================================================================
"""Bridge: population-level δ_iac horseshoe posterior → per-user reconcile prior.

Closes the explicit follow-on slice named in
``adam/intelligence/user_posterior_hmc_reconcile.py`` line 113-114:

    "Mechanism slopes (per-mechanism deviation from baseline) — Phase 3
     δ_iac with horseshoe priors."

WHY THIS EXISTS
---------------

The Phase 3 horseshoe model (``hierarchical_bayes.build_hierarchical_model_with_interactions``,
shipped 4e02e5b) fits a population-level posterior over
``delta_iac[archetype, mechanism, category]`` interaction triples. The
posterior carries calibrated information about which (a, m, c) cells
deviate from the additive backbone and by how much.

Per-user reconcile (``user_posterior_hmc_reconcile.reconcile_user_posterior``)
currently uses an uninformative ``Beta(2, 2)`` prior on per-mechanism
conversion probability. The population horseshoe signal is sitting
unused at runtime — exactly the "hierarchy declared but not computed"
diagnosis (handoff §3.1) reappearing one level down.

This module is the plumbing that carries the population posterior down:

  1. Extract moments (mean, variance) of ``delta_iac`` per triple from
     a NumPyro/PyMC ``InferenceData`` once the population fit completes.
  2. Persist moments to Neo4j ``(:DeltaIacPosterior)`` nodes (small —
     a few KB per fit, even at 1000+ triples).
  3. Reload moments into an ``IacPriorMoments`` container at Task 36
     start.
  4. For each user U with archetype A, marginalize the moments to a
     per-mechanism prior ``Normal(mu_iac[m], sigma_iac[m])`` covering
     the (A, m, c) cells the user has touched. Mechanisms with no
     coverage in the population posterior fall back to ``Normal(0, 0.5)``
     (the same diffuse slack used by the existing model when this slice
     is bypassed).

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Canonical formula + citation — van de Schoot et al. 2014, "A Gentle
    Introduction to Bayesian Analysis: Applications to Developmental
    Research" §"Informative priors from prior data" — the canonical
    move of using population posterior moments as Normal informative
    priors on user-level parameters. Combined with the horseshoe substrate
    (Carvalho/Polson/Scott 2010, Piironen/Vehtari 2017) shipped in 4e02e5b.

(b) Tests pin: (i) regression — ``reconcile_user_posterior(profile)``
    matches current path bit-for-bit when ``iac_prior=None``; (ii)
    recovery — synthetic user with a planted (A, m, c) effect → reconcile
    with ``iac_prior`` recovers the effect direction more strongly than
    reconcile without; (iii) degenerate triples — mechanisms with no
    population coverage fall back to diffuse prior; (iv) loader — moment
    extraction from synthetic InferenceData round-trips through Neo4j
    writeback / reload.

(c) ``calibration_pending=True`` for the marginalization weighting (uniform
    over observed categories within an archetype × mechanism column;
    proper Bayesian marginalization weighted by posterior predictive
    over the user's category distribution is a future slice).
    A14 flag: ``USER_HMC_RECONCILE_IAC_PRIOR_PILOT_PENDING``.

(d) Honest tags — what is NOT in this slice (named successors):

    * Full posterior-predictive integration over user category
      distribution (this slice marginalizes uniformly across observed
      categories — fine when user touches are roughly category-balanced,
      conservative when not).
    * Per-mechanism × page_cluster slopes (the user side already has
      ``page_mechanism_posteriors`` keyed by ``mechanism:page_cluster``;
      lifting δ_iac into that finer grid is a separate slice).
    * Joint sampling from population posterior at user reconcile time
      (we collapse to moments — a Gaussian summary; uncertainty about
      the population posterior tail is silently flattened).

DECISION-TIME CONSUMER
----------------------

  * Task 36 nightly reconcile loads ``IacPriorMoments`` once at run start
    via ``load_iac_prior_from_neo4j`` and passes through to each per-user
    ``reconcile_user_posterior`` call.
  * Refined ``profile.mechanism_slopes`` (now non-zero when iac_prior
    available) flows through L3 Neo4j → next L1+L2 cold-start promotes
    informed slopes into cascade hot path.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Diffuse-prior fallback for mechanisms with no population coverage —
# matches the Normal(0, 0.5) slack the reconcile model uses on
# random_intercept and produces a sensible default for mechanism_slopes.
DEFAULT_FALLBACK_MEAN: float = 0.0
DEFAULT_FALLBACK_STD: float = 0.5


# Triple key alias — kept positional to match hierarchical_bayes
# observed_triples ordering convention.
TripleKey = Tuple[str, str, str]  # (archetype, mechanism, category)


@dataclass
class IacPriorMoments:
    """Population-level δ_iac posterior moments, indexed by triple.

    One ``IacPriorMoments`` is loaded per Task 36 run from the most-recent
    population horseshoe fit. It exposes per-user marginalization via
    ``per_mechanism_for_user``.

    Attributes:
        moments: ``{(archetype, mechanism, category): (mean, variance)}``
        fitted_at_ts: epoch seconds when the population fit produced
            these moments (for staleness diagnostics).
        n_triples: convenience cache of ``len(moments)``.
    """

    moments: Dict[TripleKey, Tuple[float, float]] = field(default_factory=dict)
    fitted_at_ts: float = 0.0

    @property
    def n_triples(self) -> int:
        return len(self.moments)

    def per_mechanism_for_user(
        self,
        archetype: str,
        mechanisms: Iterable[str],
    ) -> Dict[str, Tuple[float, float]]:
        """Marginalize population moments to per-mechanism (mean, std).

        For each requested mechanism ``m``, average ``delta_iac`` posterior
        moments across the categories ``c`` for which ``(archetype, m, c)``
        has population coverage. Mechanisms without coverage are omitted
        from the returned dict (caller falls back to diffuse default).

        Marginalization (calibration-pending):
            mean[m]  = mean over c of moments[(archetype, m, c)].mean
            var[m]   = mean over c of moments[(archetype, m, c)].variance
                       + variance over c of moments[(archetype, m, c)].mean
                       (between-category dispersion adds uncertainty —
                        var(E[X|c]) + E[Var(X|c)] decomposition).
            std[m]   = sqrt(var[m])
        """
        result: Dict[str, Tuple[float, float]] = {}
        for m in mechanisms:
            cell_means: List[float] = []
            cell_vars: List[float] = []
            for (a_key, m_key, _c_key), (mu, var) in self.moments.items():
                if a_key == archetype and m_key == m:
                    cell_means.append(mu)
                    cell_vars.append(var)
            if not cell_means:
                continue
            mean_of_means = sum(cell_means) / len(cell_means)
            mean_of_vars = sum(cell_vars) / len(cell_vars)
            if len(cell_means) > 1:
                between_var = sum(
                    (x - mean_of_means) ** 2 for x in cell_means
                ) / len(cell_means)
            else:
                between_var = 0.0
            total_var = mean_of_vars + between_var
            # Floor std to avoid pathologically tight priors when the
            # population posterior is deceptively concentrated on small N.
            total_std = max(0.05, total_var ** 0.5)
            result[m] = (mean_of_means, total_std)
        return result

    def is_empty(self) -> bool:
        return len(self.moments) == 0


# -----------------------------------------------------------------------------
# Extraction — InferenceData → IacPriorMoments
# -----------------------------------------------------------------------------


def extract_iac_prior_from_inferencedata(
    idata: Any,
    triples: List[TripleKey],
    fitted_at_ts: Optional[float] = None,
) -> IacPriorMoments:
    """Extract (mean, variance) moments of ``delta_iac`` per observed triple.

    Args:
        idata: a PyMC ``InferenceData`` produced by sampling the model
            from ``build_hierarchical_model_with_interactions``.
        triples: the ordered list of ``(archetype, mechanism, category)``
            triples returned by that model builder. Indexes into
            ``idata.posterior['delta_iac']``'s last axis.
        fitted_at_ts: optional override; defaults to ``time.time()``.

    Soft-fail discipline: missing ``delta_iac`` variable, mismatched
    triple count, or extraction failure → returns an empty
    ``IacPriorMoments`` and logs at WARNING. Empty moments degrade
    cleanly through ``per_mechanism_for_user`` — every mechanism
    falls back to diffuse default.
    """
    moments = IacPriorMoments(fitted_at_ts=fitted_at_ts or time.time())

    try:
        delta_post = idata.posterior["delta_iac"]
    except (KeyError, AttributeError) as exc:
        logger.warning(
            "iac_prior extraction skipped — delta_iac not in posterior: %s", exc,
        )
        return moments

    try:
        mean_arr = delta_post.mean(dim=("chain", "draw")).values  # (n_iac,)
        var_arr = delta_post.var(dim=("chain", "draw")).values
    except Exception as exc:
        logger.warning(
            "iac_prior extraction failed during mean/var aggregation: %s", exc,
        )
        return moments

    if len(mean_arr) != len(triples):
        logger.warning(
            "iac_prior extraction mismatch: posterior n_iac=%d, triples=%d",
            len(mean_arr), len(triples),
        )
        return moments

    for i, triple in enumerate(triples):
        try:
            mu = float(mean_arr[i])
            v = float(var_arr[i])
        except Exception:
            continue
        if not (mu == mu) or not (v == v):  # NaN guard
            continue
        if v < 0.0:
            continue
        moments.moments[triple] = (mu, v)

    return moments


# -----------------------------------------------------------------------------
# Neo4j writeback / reload
# -----------------------------------------------------------------------------


_DELTA_IAC_NODE_LABEL = "DeltaIacPosterior"


def write_iac_posterior_to_neo4j(
    moments: IacPriorMoments,
    driver: Optional[Any] = None,
) -> int:
    """Persist ``IacPriorMoments`` to Neo4j, one node per triple.

    Idempotent (MERGE on triple key, SET overwrites moments).
    Returns the number of triples successfully written. Soft-fails to
    0 on any infrastructure exception.

    Schema:
        (:DeltaIacPosterior {
            archetype: str, mechanism: str, category: str,
            posterior_mean: float, posterior_variance: float,
            fitted_at_ts: float, source: 'horseshoe_v1'
        })
    """
    if moments.is_empty():
        return 0

    if driver is None:
        try:
            from adam.core.dependencies import get_neo4j_driver
            driver = get_neo4j_driver()
        except Exception:
            return 0
    if driver is None:
        return 0

    cypher = (
        "MERGE (d:" + _DELTA_IAC_NODE_LABEL + " {"
        "archetype: $archetype, mechanism: $mechanism, category: $category"
        "}) "
        "SET d.posterior_mean = $posterior_mean, "
        "    d.posterior_variance = $posterior_variance, "
        "    d.fitted_at_ts = $fitted_at_ts, "
        "    d.source = 'horseshoe_v1'"
    )

    written = 0
    try:
        with driver.session() as session:
            for (archetype, mechanism, category), (mu, var) in moments.moments.items():
                try:
                    session.run(
                        cypher,
                        archetype=archetype,
                        mechanism=mechanism,
                        category=category,
                        posterior_mean=float(mu),
                        posterior_variance=float(var),
                        fitted_at_ts=float(moments.fitted_at_ts),
                    )
                    written += 1
                except Exception as exc:
                    logger.debug(
                        "iac_prior writeback failed for triple=%s: %s",
                        (archetype, mechanism, category), exc,
                    )
    except Exception as exc:
        logger.warning("iac_prior writeback session failed: %s", exc)
        return written

    logger.info(
        "iac_prior writeback complete: triples=%d fitted_at_ts=%.0f",
        written, moments.fitted_at_ts,
    )
    return written


def load_iac_prior_from_neo4j(
    driver: Optional[Any] = None,
    max_age_seconds: Optional[int] = None,
) -> IacPriorMoments:
    """Load the most-recent ``IacPriorMoments`` from Neo4j.

    Args:
        driver: optional Neo4j driver. Resolved from dependencies if None.
        max_age_seconds: when set, drop triples whose ``fitted_at_ts`` is
            older than ``time.time() - max_age_seconds``. None = no filter.

    Returns an empty ``IacPriorMoments`` (caller treats as no signal) if:
      - driver unavailable
      - query fails
      - no DeltaIacPosterior nodes exist
      - all nodes filtered out by max_age_seconds

    The empty case degrades cleanly: ``reconcile_user_posterior(profile,
    iac_prior=empty)`` matches ``iac_prior=None`` behavior because
    ``per_mechanism_for_user`` returns an empty dict.
    """
    if driver is None:
        try:
            from adam.core.dependencies import get_neo4j_driver
            driver = get_neo4j_driver()
        except Exception:
            return IacPriorMoments()
    if driver is None:
        return IacPriorMoments()

    cutoff_ts: Optional[float] = None
    if max_age_seconds is not None and max_age_seconds > 0:
        cutoff_ts = time.time() - float(max_age_seconds)

    cypher_with_cutoff = (
        "MATCH (d:" + _DELTA_IAC_NODE_LABEL + ") "
        "WHERE d.fitted_at_ts >= $cutoff "
        "RETURN d.archetype AS archetype, d.mechanism AS mechanism, "
        "       d.category AS category, "
        "       d.posterior_mean AS posterior_mean, "
        "       d.posterior_variance AS posterior_variance, "
        "       d.fitted_at_ts AS fitted_at_ts"
    )
    cypher_no_cutoff = (
        "MATCH (d:" + _DELTA_IAC_NODE_LABEL + ") "
        "RETURN d.archetype AS archetype, d.mechanism AS mechanism, "
        "       d.category AS category, "
        "       d.posterior_mean AS posterior_mean, "
        "       d.posterior_variance AS posterior_variance, "
        "       d.fitted_at_ts AS fitted_at_ts"
    )

    moments = IacPriorMoments()
    latest_fit_ts = 0.0
    try:
        with driver.session() as session:
            if cutoff_ts is not None:
                rec = session.run(cypher_with_cutoff, cutoff=cutoff_ts)
            else:
                rec = session.run(cypher_no_cutoff)
            for r in rec:
                archetype = r.get("archetype")
                mechanism = r.get("mechanism")
                category = r.get("category")
                mu = r.get("posterior_mean")
                var = r.get("posterior_variance")
                fit_ts = r.get("fitted_at_ts") or 0.0
                if not (archetype and mechanism and category):
                    continue
                if mu is None or var is None:
                    continue
                try:
                    mu_f = float(mu)
                    var_f = float(var)
                except (TypeError, ValueError):
                    continue
                if var_f < 0.0:
                    continue
                moments.moments[(archetype, mechanism, category)] = (mu_f, var_f)
                if fit_ts > latest_fit_ts:
                    latest_fit_ts = float(fit_ts)
    except Exception as exc:
        logger.warning("iac_prior load failed: %s", exc)
        return IacPriorMoments()

    moments.fitted_at_ts = latest_fit_ts
    if not moments.is_empty():
        logger.info(
            "iac_prior loaded: triples=%d latest_fit_ts=%.0f",
            moments.n_triples, latest_fit_ts,
        )
    return moments


# -----------------------------------------------------------------------------
# Per-user filter
# -----------------------------------------------------------------------------


def iac_prior_for_user(
    profile: Any,
    population_moments: Optional[IacPriorMoments],
) -> Dict[str, Tuple[float, float]]:
    """Return per-mechanism (mean, std) prior for the user's archetype.

    Returns an empty dict when population_moments is None or empty —
    caller (reconcile_user_posterior) treats empty as "fall back to
    diffuse Normal(0, 0.5) per mechanism" (current behavior).

    The returned dict only contains mechanisms covered in the population
    posterior for the user's archetype. Mechanisms missing from the
    return value implicitly mean "no informative population signal —
    use diffuse fallback at reconcile time."
    """
    if population_moments is None or population_moments.is_empty():
        return {}

    archetype = getattr(profile, "archetype_id", "") or ""
    if not archetype:
        return {}

    mechanisms = list(profile.mechanism_posteriors.keys())
    if not mechanisms:
        return {}

    return population_moments.per_mechanism_for_user(archetype, mechanisms)
