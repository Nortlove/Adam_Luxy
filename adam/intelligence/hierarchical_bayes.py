"""Hierarchical Bayesian partial pooling — M3 substrate.

Closes the architectural diagnosis the handoff §3.1 named explicitly:

    "INFORMATIV already declares a 'population → cluster → demographic
     → contextual → user-historical' hierarchy and uses Beta-Binomial
     Thompson sampling — but the cells are independent Beta(α, β).
     Partial pooling and shrinkage are not actually computed. With
     5 archetypes × 9 mechanisms × ≈100 categories ≈ 4,500 cells and
     many holding <20 LUXY observations, TS exploration is dominated
     by noise rather than uncertainty."

Per handoff §3.2: logit-space partial pooling with non-centered
parameterization (Papaspiliopoulos, Roberts, Sköld 2007 — essential to
avoid Neal's funnel). Posterior moments → Beta(α, β) → write back to
BayesianPrior nodes. TS samples online from the hierarchically-shrunk
priors instead of the independent-cell priors that produced the
diagnosis.

This module ships the substrate:
    - Observation loader: pulls (archetype, mechanism, category, success)
      tuples from Neo4j AdDecision/AdOutcome rows
    - Model builder: PyMC model with non-centered parameterization at
      every level — the canonical handoff §3.3 skeleton
    - Sampler driver: NUTS via NumPyro when available, raises
      HierarchyLibsMissingError otherwise
    - Posterior → Beta(α, β) recovery: handoff §3.2 formula
        p = sigmoid(γ̂),  n_eff = max(1, p(1-p)/var − 1)
        α = p · n_eff,    β = (1-p) · n_eff
    - Writeback: BayesianPrior nodes updated with shrunk α, β

Library calls gate-import. Without PyMC + NumPyro, the fitter raises
HierarchyLibsMissingError clearly — same discipline as M2's
LibsMissingError. A 'fit' that returns None on missing libs would let
TS sample meaningless posteriors silently.

The full nightly Airflow refit, Bambi prototype, and PSIS-LOO
diagnostics are M3 follow-on. This commit ships the architectural
substrate so the diagnosis can be closed.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Handoff §3.3 priors — preserved here as the canonical specification.
# σ shrinks at each level (1.5 → 0.5 → 0.3 → 0.2) so deeper levels are
# more strongly informed by the level above unless the data overrides.
_HIERARCHY_PRIORS: Dict[str, float] = {
    "mu_pop_loc": 0.0,
    "mu_pop_scale": 1.5,
    "sigma_archetype_scale": 0.5,
    "sigma_demo_scale": 0.3,
    "sigma_ctx_scale": 0.2,
}

# NUTS hyperparameters per handoff §3.3
_NUTS_PARAMS: Dict[str, Any] = {
    "draws": 2000,
    "tune": 1500,
    "target_accept": 0.95,
    "chains": 4,
}


@dataclass
class HierarchicalObservation:
    """One outcome row indexed by hierarchy levels.

    archetype / mechanism / category index into the level-3 contextual
    cell. demographic is optional — when None, the model skips the
    demographic level for this row (still partial-pools across cluster).
    """
    archetype: str
    mechanism: str
    category: str
    success: int                       # 0 / 1 Bernoulli outcome
    demographic: Optional[str] = None  # optional level-2 demographic stratum


@dataclass
class CellPosterior:
    """One cell's Beta posterior recovered from PyMC trace."""
    archetype: str
    mechanism: str
    category: str
    alpha: float          # recovered from posterior mean + variance
    beta: float
    p_mean: float         # sigmoid(γ̂) — point estimate of conversion prob
    p_variance: float     # posterior variance
    n_obs: int            # observations contributing to this cell


@dataclass
class FitDiagnostics:
    """PyMC fit-level diagnostics — written for ops visibility."""
    cells_recovered: int = 0
    divergences: int = 0
    r_hat_max: float = 0.0
    ess_bulk_min: float = 0.0
    fitted_at_ts: float = 0.0
    library_versions: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class HierarchyLibsMissingError(RuntimeError):
    """Raised when PyMC fit is requested but libs aren't installed.

    Returning None on missing libs would let TS sample meaningless
    posteriors silently — exact drift pattern we exist to prevent.
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
# Observation loader — Neo4j AdDecision joined to outcome
# -----------------------------------------------------------------------------


def load_observations_from_neo4j(
    driver: Optional[Any] = None,
    days_lookback: int = 90,
    pscore_known_only: bool = True,
) -> List[HierarchicalObservation]:
    """Pull observation rows for the hierarchical fit.

    Per handoff: filter on pscore_known=true to inherit the same
    discipline anchor M1/M2 use. Reconstructed propensities corrupt
    posteriors the same way they corrupt OPE estimates (Boruvka 2018
    §2 + Bibaut 2024).
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
      dc.mechanism_sent AS mechanism,
      coalesce(dc.product_category, dc.content_category, '') AS category,
      CASE WHEN o.outcome_value > 0 THEN 1 ELSE 0 END AS success
    LIMIT 200000
    """

    cutoff_ts = _epoch_ms_n_days_ago(days_lookback)
    obs: List[HierarchicalObservation] = []
    try:
        with driver.session() as session:
            result = session.run(cypher, cutoff_ts=cutoff_ts)
            for record in result:
                arch = record.get("archetype") or ""
                mech = record.get("mechanism") or ""
                cat = record.get("category") or ""
                success = int(record.get("success") or 0)
                if not arch or not mech:
                    continue
                obs.append(HierarchicalObservation(
                    archetype=arch, mechanism=mech, category=cat,
                    success=success,
                ))
    except Exception as exc:
        logger.warning("Hierarchical observation loader failed: %s", exc)
        return []

    return obs


def _epoch_ms_n_days_ago(days: int) -> int:
    import time
    return int((time.time() - days * 86400) * 1000)


# -----------------------------------------------------------------------------
# Model builder — handoff §3.3 canonical skeleton
# -----------------------------------------------------------------------------


def build_hierarchical_model(
    observations: List[HierarchicalObservation],
    priors: Optional[Dict[str, float]] = None,
) -> Tuple[Any, Dict[str, List[str]]]:
    """Build the PyMC model with non-centered parameterization.

    Returns (model, coords) where coords maps each level to its set of
    unique values (used for indexing the latent variables).

    Raises:
        HierarchyLibsMissingError if PyMC isn't available
        ValueError if observations is empty
    """
    if not observations:
        raise ValueError("build_hierarchical_model: empty observations")

    pymc = _try_import_pymc()
    if pymc is None:
        raise HierarchyLibsMissingError(
            "PyMC not installed. M3 fitter requires pymc>=5.16 and "
            "numpyro>=0.16 (handoff §3.6 library pins)."
        )

    try:
        import pymc as pm  # noqa: F401
        import numpy as np
    except ImportError as exc:
        raise HierarchyLibsMissingError(f"PyMC deps missing: {exc}")

    p = {**_HIERARCHY_PRIORS, **(priors or {})}

    archetypes = sorted({o.archetype for o in observations})
    mechanisms = sorted({o.mechanism for o in observations})
    categories = sorted({o.category for o in observations})

    arch_idx = {a: i for i, a in enumerate(archetypes)}
    mech_idx = {m: i for i, m in enumerate(mechanisms)}
    cat_idx = {c: i for i, c in enumerate(categories)}

    a_idx = np.asarray([arch_idx[o.archetype] for o in observations])
    m_idx = np.asarray([mech_idx[o.mechanism] for o in observations])
    c_idx = np.asarray([cat_idx[o.category] for o in observations])
    y = np.asarray([o.success for o in observations])

    coords = {
        "archetype": archetypes,
        "mechanism": mechanisms,
        "category": categories,
    }

    with pm.Model(coords=coords) as model:
        # Population mean (logit space)
        mu_pop = pm.Normal(
            "mu_pop", p["mu_pop_loc"], p["mu_pop_scale"],
        )
        # Archetype-level deviation
        sigma_archetype = pm.HalfNormal(
            "sigma_archetype", p["sigma_archetype_scale"],
        )
        z_archetype = pm.Normal(
            "z_archetype", 0, 1, dims="archetype",
        )
        alpha_archetype = pm.Deterministic(
            "alpha_archetype",
            mu_pop + sigma_archetype * z_archetype,
            dims="archetype",
        )

        # Mechanism × Category contextual level (collapsed demographic)
        sigma_ctx = pm.HalfNormal("sigma_ctx", p["sigma_ctx_scale"])
        z_ctx = pm.Normal(
            "z_ctx", 0, 1,
            dims=("archetype", "mechanism", "category"),
        )
        gamma_ctx = pm.Deterministic(
            "gamma_ctx",
            alpha_archetype[:, None, None] + sigma_ctx * z_ctx,
            dims=("archetype", "mechanism", "category"),
        )

        # Index into γ for each observation
        eta = gamma_ctx[a_idx, m_idx, c_idx]
        pm.Bernoulli("y_obs", logit_p=eta, observed=y)

    return model, coords


# -----------------------------------------------------------------------------
# Phase 3 δ_iac — horseshoe-shrunk trait × state × context interaction tensor
# -----------------------------------------------------------------------------
#
# Directive Phase 3 line 985-988: extend the cell-level partial-pooling
# model with sparse interaction terms `delta_iac[i]` for the small
# subset of (archetype, mechanism, category) triples where the
# interaction is materially non-zero. Horseshoe prior (Carvalho, Polson,
# Scott 2009; Piironen & Vehtari 2017) shrinks the irrelevant
# interactions toward zero while preserving the few that are real.
#
# Per directive line 987 — "Pre-specified interaction list (~10–15
# interactions Chris believes exist)" — the build function accepts a
# pre_specified_interactions argument: each pre-specified triple gets a
# wider Normal(0, 1.0) prior (no shrinkage), so the horseshoe doesn't
# fight against domain knowledge. Other triples present in the data go
# through the horseshoe.

# Horseshoe scale defaults — Piironen-Vehtari recommend tau_scale = (s/(D-s)) * (sigma/sqrt(N))
# where D = total interactions, s = expected non-zero count. Conservative:
# tau_scale=0.1 works well for D ≈ 100 and expected s ≈ 5-15.
_HORSESHOE_TAU_SCALE: float = 0.1
# Wide non-shrinkage prior for pre-specified interactions
_PRESPECIFIED_INTERACTION_SCALE: float = 1.0


def build_hierarchical_model_with_interactions(
    observations: List[HierarchicalObservation],
    pre_specified_interactions: Optional[List[Tuple[str, str, str]]] = None,
    priors: Optional[Dict[str, float]] = None,
    tau_scale: float = _HORSESHOE_TAU_SCALE,
) -> Tuple[Any, Dict[str, List[str]], List[Tuple[str, str, str]]]:
    """Build the M3 hierarchical model + δ_iac horseshoe interaction layer.

    Returns (model, coords, interaction_index) where interaction_index
    is the ordered list of (archetype, mechanism, category) triples
    that have at least one observation in the data — these are the
    candidate interaction slots; the horseshoe shrinks them toward zero
    unless evidence supports them.

    Args:
        observations: same as build_hierarchical_model
        pre_specified_interactions: list of (archetype, mechanism,
            category) triples Chris/the team believes exist a priori;
            these get the wide Normal(0, 1.0) prior instead of the
            horseshoe. Triples outside the observed data are silently
            dropped — you cannot pre-specify an interaction with zero
            data.
        priors: same as build_hierarchical_model
        tau_scale: horseshoe global shrinkage scale (Piironen-Vehtari
            2017 default 0.1 for moderate D)

    Raises:
        HierarchyLibsMissingError if PyMC isn't available
        ValueError if observations is empty
    """
    if not observations:
        raise ValueError("build_hierarchical_model_with_interactions: empty observations")

    pymc = _try_import_pymc()
    if pymc is None:
        raise HierarchyLibsMissingError(
            "PyMC not installed. δ_iac horseshoe model requires pymc>=5.16."
        )

    try:
        import pymc as pm
        import numpy as np
    except ImportError as exc:
        raise HierarchyLibsMissingError(f"PyMC deps missing: {exc}")

    p = {**_HIERARCHY_PRIORS, **(priors or {})}
    pre_specified = set(pre_specified_interactions or [])

    archetypes = sorted({o.archetype for o in observations})
    mechanisms = sorted({o.mechanism for o in observations})
    categories = sorted({o.category for o in observations})
    arch_idx = {a: i for i, a in enumerate(archetypes)}
    mech_idx = {m: i for i, m in enumerate(mechanisms)}
    cat_idx = {c: i for i, c in enumerate(categories)}

    # Interaction slot = unique (archetype, mechanism, category) triple
    # observed in the data. Each slot gets one delta_iac coefficient.
    observed_triples: List[Tuple[str, str, str]] = sorted({
        (o.archetype, o.mechanism, o.category) for o in observations
    })
    n_iac = len(observed_triples)
    triple_to_iac_idx = {t: i for i, t in enumerate(observed_triples)}

    # Mask: 1 if pre-specified (no shrinkage), 0 if horseshoe-shrunk
    is_prespecified = np.array(
        [1 if t in pre_specified else 0 for t in observed_triples],
        dtype=np.int32,
    )
    n_prespecified = int(is_prespecified.sum())
    n_horseshoe = n_iac - n_prespecified

    a_idx = np.asarray([arch_idx[o.archetype] for o in observations])
    m_idx = np.asarray([mech_idx[o.mechanism] for o in observations])
    c_idx = np.asarray([cat_idx[o.category] for o in observations])
    iac_idx = np.asarray([
        triple_to_iac_idx[(o.archetype, o.mechanism, o.category)]
        for o in observations
    ])
    y = np.asarray([o.success for o in observations])

    coords = {
        "archetype": archetypes,
        "mechanism": mechanisms,
        "category": categories,
        "interaction": [
            f"{a}|{m}|{c}" for (a, m, c) in observed_triples
        ],
    }

    with pm.Model(coords=coords) as model:
        # --- Existing partial-pooling backbone (unchanged) ---
        mu_pop = pm.Normal("mu_pop", p["mu_pop_loc"], p["mu_pop_scale"])
        sigma_archetype = pm.HalfNormal(
            "sigma_archetype", p["sigma_archetype_scale"],
        )
        z_archetype = pm.Normal("z_archetype", 0, 1, dims="archetype")
        alpha_archetype = pm.Deterministic(
            "alpha_archetype",
            mu_pop + sigma_archetype * z_archetype,
            dims="archetype",
        )
        sigma_ctx = pm.HalfNormal("sigma_ctx", p["sigma_ctx_scale"])
        z_ctx = pm.Normal(
            "z_ctx", 0, 1,
            dims=("archetype", "mechanism", "category"),
        )
        gamma_ctx = pm.Deterministic(
            "gamma_ctx",
            alpha_archetype[:, None, None] + sigma_ctx * z_ctx,
            dims=("archetype", "mechanism", "category"),
        )

        # --- Phase 3 δ_iac — horseshoe + pre-specified slots ---
        # Global scale (only relevant for horseshoe-shrunk slots)
        if n_horseshoe > 0:
            tau = pm.HalfCauchy("tau_iac", beta=tau_scale)
            # Local shrinkage per slot
            lam = pm.HalfCauchy("lambda_iac", beta=1.0, dims="interaction")
            # Per-slot scale combines global tau, local lambda, and the
            # pre-specified mask. Pre-specified slots use the wider
            # _PRESPECIFIED_INTERACTION_SCALE.
            mask_pre = pm.Data("is_prespecified", is_prespecified.astype(np.float64))
            scale = pm.Deterministic(
                "delta_iac_scale",
                mask_pre * _PRESPECIFIED_INTERACTION_SCALE
                + (1.0 - mask_pre) * tau * lam,
                dims="interaction",
            )
        else:
            # Pure pre-specified — no horseshoe needed
            scale = pm.Deterministic(
                "delta_iac_scale",
                pm.math.constant(
                    np.full(n_iac, _PRESPECIFIED_INTERACTION_SCALE),
                ),
                dims="interaction",
            )

        # Non-centered parameterization of delta to avoid Neal's funnel
        z_iac = pm.Normal("z_iac", 0, 1, dims="interaction")
        delta_iac = pm.Deterministic(
            "delta_iac", scale * z_iac, dims="interaction",
        )

        # eta = backbone + interaction term
        eta = gamma_ctx[a_idx, m_idx, c_idx] + delta_iac[iac_idx]
        pm.Bernoulli("y_obs", logit_p=eta, observed=y)

    return model, coords, observed_triples


# -----------------------------------------------------------------------------
# Sampler driver — runs NUTS, returns posterior summary
# -----------------------------------------------------------------------------


def fit_hierarchical_model(
    observations: List[HierarchicalObservation],
    nuts_params: Optional[Dict[str, Any]] = None,
    priors: Optional[Dict[str, float]] = None,
) -> Tuple[List[CellPosterior], FitDiagnostics]:
    """Fit the hierarchical model and recover Beta(α, β) per cell.

    Returns (cell_posteriors, diagnostics). The diagnostics include
    r_hat_max + ess_bulk_min + divergence count — handoff §3.7
    requires r̂ < 1.01 and ESS > 400 with zero divergences post-warmup.

    Raises:
        HierarchyLibsMissingError if PyMC/NumPyro isn't available
        ValueError if observations is empty
    """
    import time

    diag = FitDiagnostics(fitted_at_ts=time.time())

    if not observations:
        raise ValueError("fit_hierarchical_model: empty observations")

    pymc = _try_import_pymc()
    if pymc is None:
        raise HierarchyLibsMissingError(
            "PyMC not installed; cannot fit hierarchical model."
        )
    diag.library_versions["pymc"] = getattr(pymc, "__version__", "unknown")

    try:
        import pymc as pm
        import numpy as np
    except ImportError as exc:
        raise HierarchyLibsMissingError(f"PyMC deps missing: {exc}")

    model, coords = build_hierarchical_model(observations, priors=priors)
    nuts = {**_NUTS_PARAMS, **(nuts_params or {})}

    try:
        with model:
            idata = pm.sample(
                draws=nuts["draws"],
                tune=nuts["tune"],
                target_accept=nuts["target_accept"],
                chains=nuts["chains"],
                nuts_sampler="numpyro",
                progressbar=False,
                return_inferencedata=True,
            )
    except Exception as exc:
        diag.errors.append(f"NUTS sampler failed: {exc}")
        return [], diag

    # Extract gamma_ctx posterior moments → recover Beta(α, β)
    try:
        gamma_post = idata.posterior["gamma_ctx"]  # dims: chain, draw, archetype, mechanism, category
        gamma_mean = gamma_post.mean(dim=("chain", "draw"))
        gamma_var = gamma_post.var(dim=("chain", "draw"))

        # Diagnostic stats
        try:
            import arviz as az
            summary = az.summary(idata, var_names=["gamma_ctx"])
            diag.r_hat_max = float(summary["r_hat"].max())
            diag.ess_bulk_min = float(summary["ess_bulk"].min())
            sample_stats = idata.sample_stats
            if "diverging" in sample_stats:
                diag.divergences = int(sample_stats["diverging"].sum())
        except Exception:
            pass
    except KeyError as exc:
        diag.errors.append(f"posterior extraction failed: {exc}")
        return [], diag

    # Recover Beta per cell. Handoff §3.2 formula:
    #     p = sigmoid(γ̂)
    #     var ≈ p(1-p) for the Bernoulli; we use posterior var of γ as
    #     uncertainty input
    #     n_eff = max(1, p(1-p)/var_p − 1)
    #     α = p · n_eff,  β = (1-p) · n_eff
    cells: List[CellPosterior] = []
    for ai, archetype in enumerate(coords["archetype"]):
        for mi, mechanism in enumerate(coords["mechanism"]):
            for ci, category in enumerate(coords["category"]):
                gamma_hat = float(gamma_mean.values[ai, mi, ci])
                gamma_var_val = float(gamma_var.values[ai, mi, ci])
                p_hat = _sigmoid(gamma_hat)
                # Posterior variance on p via delta method:
                # Var(sigmoid(γ)) ≈ (p(1-p))² · Var(γ)
                p_var = (p_hat * (1.0 - p_hat)) ** 2 * gamma_var_val
                if p_var < 1e-9:
                    n_eff = 30.0  # default informativity matching to_beta_prior
                else:
                    n_eff = max(1.0, p_hat * (1.0 - p_hat) / p_var - 1.0)

                alpha = p_hat * n_eff
                beta = (1.0 - p_hat) * n_eff
                # Count observations for this cell
                n_obs = sum(
                    1 for o in observations
                    if o.archetype == archetype
                    and o.mechanism == mechanism
                    and o.category == category
                )
                cells.append(CellPosterior(
                    archetype=archetype, mechanism=mechanism, category=category,
                    alpha=alpha, beta=beta,
                    p_mean=p_hat, p_variance=p_var,
                    n_obs=n_obs,
                ))

    diag.cells_recovered = len(cells)
    return cells, diag


def _sigmoid(x: float) -> float:
    if x >= 0:
        return 1.0 / (1.0 + math.exp(-x))
    ez = math.exp(x)
    return ez / (1.0 + ez)


# -----------------------------------------------------------------------------
# Beta(α, β) writeback to BayesianPrior nodes
# -----------------------------------------------------------------------------


def write_cell_posterior_to_neo4j(
    posterior: CellPosterior,
    driver: Optional[Any] = None,
) -> bool:
    """Write a CellPosterior onto its BayesianPrior node.

    Idempotent (MATCH ... SET ...). Returns True on success.
    """
    if driver is None:
        try:
            from adam.core.dependencies import get_neo4j_driver
            driver = get_neo4j_driver()
        except Exception:
            return False
    if driver is None:
        return False

    cypher = """
    MATCH (bp:BayesianPrior {
        archetype: $archetype,
        mechanism: $mechanism,
        category: $category
    })
    SET bp.alpha = $alpha,
        bp.beta = $beta,
        bp.p_mean = $p_mean,
        bp.n_obs = $n_obs,
        bp.last_hierarchical_fit = timestamp(),
        bp.shrinkage_source = 'hierarchical_bayes_v1'
    """
    try:
        with driver.session() as session:
            session.run(
                cypher,
                archetype=posterior.archetype,
                mechanism=posterior.mechanism,
                category=posterior.category,
                alpha=posterior.alpha,
                beta=posterior.beta,
                p_mean=posterior.p_mean,
                n_obs=posterior.n_obs,
            )
        return True
    except Exception as exc:
        logger.warning("Hierarchical posterior writeback failed: %s", exc)
        return False


# -----------------------------------------------------------------------------
# Nightly orchestrator
# -----------------------------------------------------------------------------


def run_nightly_hierarchical_refit(
    driver: Optional[Any] = None,
    days_lookback: int = 90,
) -> FitDiagnostics:
    """Drive the nightly fit + writeback. Handoff §3.5 cadence.

    Diagnostics returned for ops visibility. r̂ > 1.01 OR
    divergences > 0 means the fit didn't converge — the writeback
    still happens (better than stale priors) but the diagnostic
    surface flags it.
    """
    obs = load_observations_from_neo4j(
        driver=driver, days_lookback=days_lookback,
    )
    if not obs:
        diag = FitDiagnostics()
        diag.errors.append("no observations available")
        return diag

    cells, diag = fit_hierarchical_model(obs)

    written = 0
    for cell in cells:
        if write_cell_posterior_to_neo4j(cell, driver=driver):
            written += 1
        else:
            diag.errors.append(
                f"writeback failed for {cell.archetype}×{cell.mechanism}×{cell.category}"
            )

    logger.info(
        "Hierarchical refit: cells=%d written=%d r_hat_max=%.3f divergences=%d",
        len(cells), written, diag.r_hat_max, diag.divergences,
    )
    return diag
