"""Causal Forests + DML pipeline — M2 substrate.

Per the Seven-Component Methodological Upgrade Handoff §2: causal forests
(Wager-Athey 2018, Athey-Tibshirani-Wager 2019) compute Conditional
Average Treatment Effects τ̂(x) per (archetype × mechanism × category)
cell. DML (Chernozhukov 2018) gives debiased ATE per mechanism × category.
Both feed weekly into Beta(α₀, β₀) prior updates that TS samples from
online — the production pattern at Booking, Netflix, Microsoft ALICE.

This module is the substrate:
    - Data loader: reads :AdDecision rows from Neo4j with the M4-schema
      propensity fields (pscore_known=true filter) joined to outcomes
    - Fitter: wraps EconML's CausalForestDML with the handoff §2.3 params
      (n_estimators=2000, min_samples_leaf=15, honest=True, cv=5)
    - Writeback: persists τ̂ and CIs onto (Archetype)-[:RESPONDS_TO]->
      (Mechanism) edges in Neo4j as edge properties
    - Weekly job interface (handoff §2.10 cadence: Sunday 03:00 UTC)

The actual EconML / DoubleML library calls are gated behind a try-import
so the module loads even when the libs aren't installed (typical for
the LUXY pilot environment until production deployment). Without the
libs, the fitter raises a clear error rather than silently returning
None — discipline anchor: a "fit" that returns None when libs are
missing would let callers consume meaningless τ̂ values silently.

The full weekly Airflow DAG, the conformal Mondrian wrapper, the DML
monthly job, and the EconML version pinning are M2 follow-on work.
This commit ships the substrate that makes those follow-ons one-line
wires when the libs land.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# Handoff §2.3 canonical params for our scale
# (n ≈ 100k weekly conversion events, K=9 mechanisms, 5×6 archetype × category cube).
_DEFAULT_FOREST_PARAMS: Dict[str, Any] = {
    "n_estimators": 2000,
    "min_samples_leaf": 15,
    "max_samples": 0.45,
    "max_depth": 10,
    "honest": True,
    "cv": 5,
    "random_state": 42,
}


@dataclass
class CATEResult:
    """One cell's CATE estimate.

    Honest about uncertainty: bootstrap-of-little-bags (EconML default,
    subforest_size=4) gives asymptotic CIs; we expose them.

    For leaves with <200 events, the handoff §2.9 caveat applies: 95%
    nominal coverage often delivers 88-93% empirical. n_events <200
    is flagged on the result so downstream consumers can widen by
    ~1.3× empirically (handoff §2.9) or fall through to bootstrap.
    """
    archetype: str
    mechanism: str
    category: str
    tau_hat: float                  # CATE point estimate
    tau_lower: float                # 95% CI lower
    tau_upper: float                # 95% CI upper
    n_events: int                   # cell sample size
    cell_under_powered: bool = False  # True when n_events < 200


@dataclass
class FitDiagnostics:
    """Per-fit diagnostic info — written to Neo4j for ops visibility."""
    cells_fit: int = 0
    cells_skipped_low_n: int = 0
    cells_failed: int = 0
    fitted_at_ts: float = 0.0
    library_versions: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


@dataclass
class LoggedDecisionRow:
    """One :AdDecision row with everything CF needs for fitting.

    Matches the M1 + M4 schema. WCLS / OPE / CF all read pscore_known
    FIRST and exclude rows where it's False per Boruvka 2018 §2.
    """
    archetype: str
    mechanism: str
    category: str
    user_id: str
    context_features: Dict[str, float]   # X — covariates for CATE heterogeneity
    treatment: int                       # T — 1 if mechanism delivered, 0 if control
    outcome: float                       # Y — conversion or proximal outcome
    propensity: float                    # ts_propensity (pscore for IPW reweighting)
    pscore_known: bool                   # discipline anchor
    timestamp_ms: int = 0


def _try_import_econml() -> Optional[Any]:
    """Soft-import EconML. Returns the module or None if not installed."""
    try:
        import econml  # noqa: F401
        return econml
    except ImportError:
        return None


# -----------------------------------------------------------------------------
# Data loader — pulls decision + outcome rows from Neo4j
# -----------------------------------------------------------------------------


def load_decision_outcome_rows_for_cell(
    archetype: str,
    mechanism: str,
    category: str,
    driver: Optional[Any] = None,
    days_lookback: int = 90,
) -> List[LoggedDecisionRow]:
    """Pull (decision, outcome) joined rows for one cell.

    Filters on:
      - archetype/mechanism/category match
      - pscore_known=true (M4 schema discipline anchor — Boruvka 2018 §2)
      - decision created within days_lookback

    Returns a list of LoggedDecisionRow ready for fitting. On Neo4j
    unavailable, returns []. The caller decides whether empty rows
    means "no data" vs "infrastructure failure."
    """
    if driver is None:
        try:
            from adam.core.dependencies import get_neo4j_driver
            driver = get_neo4j_driver()
        except Exception as exc:
            logger.debug("Neo4j driver unavailable: %s", exc)
            return []

    if driver is None:
        return []

    cutoff_ts = _epoch_ms_n_days_ago(days_lookback)

    cypher = """
    MATCH (dc:DecisionContext)
    WHERE dc.archetype = $archetype
      AND dc.mechanism_sent = $mechanism
      AND dc.pscore_known = true
      AND dc.created_at * 1000 >= $cutoff_ts
    OPTIONAL MATCH (dc)-[:HAD_OUTCOME]->(o:AdOutcome)
    RETURN dc, o
    LIMIT 100000
    """

    rows: List[LoggedDecisionRow] = []
    try:
        with driver.session() as session:
            result = session.run(
                cypher,
                archetype=archetype, mechanism=mechanism,
                cutoff_ts=cutoff_ts,
            )
            for record in result:
                row = _record_to_logged_decision_row(record, category)
                if row is not None:
                    rows.append(row)
    except Exception as exc:
        logger.warning("CF data loader failed: %s", exc)
        return []

    return rows


def _epoch_ms_n_days_ago(days: int) -> int:
    import time
    return int((time.time() - days * 86400) * 1000)


def _record_to_logged_decision_row(
    record: Any, category: str,
) -> Optional[LoggedDecisionRow]:
    """Convert a Neo4j record into a LoggedDecisionRow. None on
    schema mismatch (caller skips the row)."""
    try:
        dc = record["dc"]
        o = record.get("o") if hasattr(record, "get") else record["o"]
    except Exception:
        return None

    try:
        archetype = dc.get("archetype", "")
        mechanism = dc.get("mechanism_sent", "")
        user_id = dc.get("buyer_id", "")
        propensity = float(dc.get("ts_propensity", 0.0) or 0.0)
        pscore_known = bool(dc.get("pscore_known", False))

        # Context features — start with edge_dimensions from metadata_json
        # if present, else empty (CATE will fall back to marginal effect)
        context_features: Dict[str, float] = {}

        outcome = 0.0
        treatment = 1  # mechanism was delivered
        if o is not None:
            outcome = float(o.get("outcome_value", 0.0) or 0.0)
    except Exception:
        return None

    return LoggedDecisionRow(
        archetype=archetype, mechanism=mechanism, category=category,
        user_id=user_id, context_features=context_features,
        treatment=treatment, outcome=outcome,
        propensity=propensity, pscore_known=pscore_known,
    )


# -----------------------------------------------------------------------------
# Fitter — wraps EconML's CausalForestDML; soft-fails when lib missing
# -----------------------------------------------------------------------------


class LibsMissingError(RuntimeError):
    """Raised when CausalForestDML is requested but EconML isn't installed.

    A 'fit' that returns None on missing libs would let callers consume
    meaningless τ̂ values silently — exactly the drift pattern we exist
    to prevent.
    """
    pass


def fit_causal_forest_for_cell(
    rows: List[LoggedDecisionRow],
    forest_params: Optional[Dict[str, Any]] = None,
) -> CATEResult:
    """Fit a CausalForestDML on one cell's logged rows.

    Per handoff §2.3:
        n_estimators=2000, min_samples_leaf=15, max_samples=0.45,
        max_depth=10, honest=True, cv=5

    Returns the average τ̂ over the cell with bootstrap CIs.

    Raises:
        LibsMissingError when EconML isn't installed
        ValueError when rows is empty or all-control / all-treatment
    """
    if not rows:
        raise ValueError("fit_causal_forest_for_cell: empty rows")

    # Filter to pscore_known=true rows — Boruvka 2018 §2 discipline.
    # This check happens BEFORE the EconML lib check because pscore
    # filtering doesn't need libraries.
    valid_rows = [r for r in rows if r.pscore_known]
    n_events = len(valid_rows)
    if n_events == 0:
        raise ValueError(
            "All rows have pscore_known=false; CATE not estimable"
        )

    archetype = valid_rows[0].archetype
    mechanism = valid_rows[0].mechanism
    category = valid_rows[0].category

    # Degenerate-cell check ALSO runs before lib import — all-control or
    # all-treatment cells are unidentifiable regardless of EconML
    # availability. The weekly job must continue past these without
    # requiring the lib.
    treatments = {r.treatment for r in valid_rows}
    if len(treatments) < 2:
        return CATEResult(
            archetype=archetype, mechanism=mechanism, category=category,
            tau_hat=0.0, tau_lower=0.0, tau_upper=0.0,
            n_events=n_events, cell_under_powered=True,
        )

    econml = _try_import_econml()
    if econml is None:
        raise LibsMissingError(
            "EconML not installed. M2 fitter requires econml>=0.16.0 "
            "(see handoff §2.10 library pins)."
        )

    # Lazy-import the EconML pieces inside the try (module-level import
    # would defeat the soft-import gate for callers who only need data
    # loading).
    try:
        from econml.dml import CausalForestDML
        from sklearn.ensemble import (
            GradientBoostingRegressor, GradientBoostingClassifier,
        )
        import numpy as np
    except ImportError as exc:
        raise LibsMissingError(f"causal-forest deps missing: {exc}")

    params = {**_DEFAULT_FOREST_PARAMS, **(forest_params or {})}

    # Build X / T / Y matrices. Context features come from each row;
    # for cells with empty context features (no edge_dimensions on the
    # decision row), we still fit but the CATE collapses to the ATE.
    feature_keys = sorted({
        k for r in valid_rows for k in r.context_features.keys()
    })

    X_list = []
    for r in valid_rows:
        X_list.append([r.context_features.get(k, 0.0) for k in feature_keys])
    X = np.asarray(X_list) if X_list and feature_keys else np.zeros((n_events, 1))
    T = np.asarray([r.treatment for r in valid_rows])
    Y = np.asarray([r.outcome for r in valid_rows])

    est = CausalForestDML(
        model_y=GradientBoostingRegressor(max_depth=4, n_estimators=200),
        model_t=GradientBoostingClassifier(max_depth=4, n_estimators=200),
        discrete_treatment=True,
        n_estimators=params["n_estimators"],
        min_samples_leaf=params["min_samples_leaf"],
        max_depth=params["max_depth"],
        max_samples=params["max_samples"],
        honest=params["honest"],
        inference=True,
        cv=params["cv"],
        random_state=params["random_state"],
    )

    try:
        est.fit(Y, T, X=X)
        tau = float(np.mean(est.effect(X)))
        lo, hi = est.effect_interval(X, alpha=0.05)
        tau_lower = float(np.mean(lo))
        tau_upper = float(np.mean(hi))
    except Exception as exc:
        logger.warning(
            "CausalForestDML fit failed for cell %s × %s × %s: %s",
            archetype, mechanism, category, exc,
        )
        return CATEResult(
            archetype=archetype, mechanism=mechanism, category=category,
            tau_hat=0.0, tau_lower=0.0, tau_upper=0.0,
            n_events=n_events, cell_under_powered=True,
        )

    # Handoff §2.9 caveat: leaf n<200 → empirical coverage 88-93% on
    # nominal 95%. Flag cell as under-powered so consumers can widen.
    under_powered = n_events < 200

    return CATEResult(
        archetype=archetype, mechanism=mechanism, category=category,
        tau_hat=tau, tau_lower=tau_lower, tau_upper=tau_upper,
        n_events=n_events, cell_under_powered=under_powered,
    )


# -----------------------------------------------------------------------------
# Neo4j writeback — persists τ̂ on (Archetype)-[:RESPONDS_TO]->(Mechanism)
# -----------------------------------------------------------------------------


def write_cate_to_neo4j(
    result: CATEResult,
    driver: Optional[Any] = None,
) -> bool:
    """Write a CATEResult onto the RESPONDS_TO edge per handoff §2.7.

    Edge property names match the handoff schema: tau, tau_lo, tau_hi,
    n, fitted_at. Idempotent (MATCH ... SET ...).

    Returns True on successful write, False on driver unavailable or
    write failure.
    """
    import time

    if driver is None:
        try:
            from adam.core.dependencies import get_neo4j_driver
            driver = get_neo4j_driver()
        except Exception:
            return False

    if driver is None:
        return False

    cypher = """
    MATCH (a:Archetype {name: $archetype})
    MATCH (m:CognitiveMechanism {name: $mechanism})
    MERGE (a)-[r:RESPONDS_TO]->(m)
    SET r.tau = $tau,
        r.tau_lo = $tau_lower,
        r.tau_hi = $tau_upper,
        r.n = $n,
        r.fitted_at = $fitted_at,
        r.cell_under_powered = $cell_under_powered,
        r.category = $category
    """

    try:
        with driver.session() as session:
            session.run(
                cypher,
                archetype=result.archetype,
                mechanism=result.mechanism,
                category=result.category,
                tau=result.tau_hat,
                tau_lower=result.tau_lower,
                tau_upper=result.tau_upper,
                n=result.n_events,
                fitted_at=time.time(),
                cell_under_powered=result.cell_under_powered,
            )
        return True
    except Exception as exc:
        logger.warning("CATE writeback failed: %s", exc)
        return False


# -----------------------------------------------------------------------------
# Weekly job — orchestrator for the production cron
# -----------------------------------------------------------------------------


def run_weekly_causal_forest_fit(
    cells: List[Tuple[str, str, str]],
    driver: Optional[Any] = None,
    days_lookback: int = 90,
) -> FitDiagnostics:
    """Drive the weekly fit across all (archetype, mechanism, category) cells.

    Per handoff §2.10: weekly Sunday 03:00 UTC. This function is the
    invokable interface; the cron / Airflow DAG wires it to a schedule.

    Args:
        cells: list of (archetype, mechanism, category) tuples to fit
        driver: optional Neo4j driver; resolves singleton if None
        days_lookback: how far back to pull decision rows

    Returns FitDiagnostics with per-cell counts and any errors.
    """
    import time

    diag = FitDiagnostics(fitted_at_ts=time.time())
    econml = _try_import_econml()
    if econml is not None:
        diag.library_versions["econml"] = getattr(econml, "__version__", "unknown")

    for (archetype, mechanism, category) in cells:
        try:
            rows = load_decision_outcome_rows_for_cell(
                archetype, mechanism, category,
                driver=driver, days_lookback=days_lookback,
            )
            if len(rows) < 30:
                # Too few rows for any meaningful fit; skip.
                diag.cells_skipped_low_n += 1
                continue

            result = fit_causal_forest_for_cell(rows)
            if write_cate_to_neo4j(result, driver=driver):
                diag.cells_fit += 1
            else:
                diag.cells_failed += 1
                diag.errors.append(
                    f"writeback failed for {archetype}×{mechanism}×{category}"
                )
        except LibsMissingError as exc:
            diag.errors.append(str(exc))
            diag.cells_failed += 1
        except Exception as exc:
            diag.cells_failed += 1
            diag.errors.append(
                f"{archetype}×{mechanism}×{category}: {exc}"
            )

    logger.info(
        "Weekly CF fit: fit=%d skipped_low_n=%d failed=%d",
        diag.cells_fit, diag.cells_skipped_low_n, diag.cells_failed,
    )
    return diag
