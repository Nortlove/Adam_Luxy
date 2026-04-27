"""Causal Discovery / SCM ensemble — M7 substrate.

Note: a different module at adam/intelligence/causal_discovery.py
contains a pre-existing PC-based relationship-discovery pipeline (with
its own CausalEdge / CausalDiscoveryEngine surfaces). This module is
DIFFERENT — the M7 ensemble layer per handoff §7: PC + FCI + GES +
DAGMA voting, DoWhy refutation, Neo4j (PsychDim)-[:CAUSES]->(PsychDim)
writeback. The two coexist; this is the canonical M7 surface.

Per the handoff §7: discover the causal DAG over the 31 identity-stable
+ 27 alignment + 9 mechanism dims via an ENSEMBLE of methods (PC, FCI,
GES, DAGMA), keeping edges that survive ≥2/4 methods. DoWhy refutes
high-vote edges via placebo + random-common-cause + unobserved-
confounder tests.

The discovered DAG informs:
    - Adjustment sets for M2 causal forests
    - Pre-treatment covariate identification for M1 MRT
    - Parents of conversion as covariates at M3 hierarchical level 4
    - Typed (PsychDim)-[:CAUSES]->(PsychDim) edges that regularize
      M5 GNN message passing

Discipline anchor — variance-ordering exploit defense:
    NOTEARS (Zheng et al. 2018) and DAGMA (Bello et al. 2022) exploit
    variance ordering in unstandardized data (Reisach-Seng-Schölkopf
    2021). This module ALWAYS standardizes inputs before running. A
    silent unstandardized fit is the publication-trap the test suite
    pins against.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class M7CausalEdge:
    """One directed edge in the M7-ensemble discovered DAG.

    Named M7CausalEdge to avoid collision with the existing
    causal_discovery.CausalEdge (different layer)."""
    source: str
    target: str
    method_votes: int
    methods: Tuple[str, ...] = ()


@dataclass
class DiscoveryDiagnostics:
    methods_run: List[str] = field(default_factory=list)
    methods_failed: List[str] = field(default_factory=list)
    edges_per_method: Dict[str, int] = field(default_factory=dict)
    robust_edge_count: int = 0
    fitted_at_ts: float = 0.0
    library_versions: Dict[str, str] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class CausalDiscoveryLibsMissingError(RuntimeError):
    """Raised when ALL discovery methods are unavailable."""
    pass


# -----------------------------------------------------------------------------
# Soft-import gates — partial install is supported
# -----------------------------------------------------------------------------


def _try_import_causal_learn() -> Optional[Any]:
    try:
        import causallearn  # noqa: F401
        return causallearn
    except ImportError:
        return None


def _try_import_dagma() -> Optional[Any]:
    try:
        import dagma  # noqa: F401
        return dagma
    except ImportError:
        return None


# -----------------------------------------------------------------------------
# Standardize — Reisach-Seng-Schölkopf 2021 defense
# -----------------------------------------------------------------------------


def standardize_columns(X: Any) -> Any:
    """Standardize columns to mean-0 var-1 BEFORE any DAG fit.

    NOTEARS / DAGMA exploit variance ordering — a silent unstandardized
    fit produces spurious edges (Reisach-Seng-Schölkopf 2021). All
    methods in this module receive standardized X.

    If numpy isn't installed, returns X unchanged (caller will fail
    downstream — explicit failure is better than silent unstandardized
    fit).
    """
    try:
        import numpy as np
    except ImportError:
        return X

    X = np.asarray(X)
    means = X.mean(axis=0)
    stds = X.std(axis=0)
    stds = np.where(stds < 1e-9, 1.0, stds)
    return (X - means) / stds


# -----------------------------------------------------------------------------
# Per-method discovery — each gates its own import
# -----------------------------------------------------------------------------


def discover_pc(X: Any, varnames: List[str], alpha: float = 0.01) -> Set[Tuple[str, str]]:
    """PC algorithm. Sound under faithfulness + causal sufficiency."""
    if _try_import_causal_learn() is None:
        return set()
    try:
        from causallearn.search.ConstraintBased.PC import pc
        from causallearn.utils.cit import fisherz
        cg = pc(X, alpha=alpha, indep_test=fisherz, stable=True, show_progress=False)
        return _adjacency_to_edge_set(cg.G.graph, varnames)
    except Exception as exc:
        logger.warning("PC discovery failed: %s", exc)
        return set()


def discover_fci(X: Any, varnames: List[str], alpha: float = 0.01) -> Set[Tuple[str, str]]:
    """FCI — handles latent confounders. PAG output."""
    if _try_import_causal_learn() is None:
        return set()
    try:
        from causallearn.search.ConstraintBased.FCI import fci
        from causallearn.utils.cit import fisherz
        g, _ = fci(X, indep_test_func=fisherz, alpha=alpha)
        return _adjacency_to_edge_set(g.graph, varnames)
    except Exception as exc:
        logger.warning("FCI discovery failed: %s", exc)
        return set()


def discover_ges(X: Any, varnames: List[str]) -> Set[Tuple[str, str]]:
    """GES — score-based BIC."""
    if _try_import_causal_learn() is None:
        return set()
    try:
        from causallearn.search.ScoreBased.GES import ges
        record = ges(X, score_func='local_score_BIC', maxP=None)
        return _adjacency_to_edge_set(record['G'].graph, varnames)
    except Exception as exc:
        logger.warning("GES discovery failed: %s", exc)
        return set()


def discover_dagma(X: Any, varnames: List[str]) -> Set[Tuple[str, str]]:
    """DAGMA — continuous optimization (Bello 2022). REQUIRES standardized X."""
    if _try_import_dagma() is None:
        return set()
    try:
        from dagma.linear import DagmaLinear
        W = DagmaLinear(loss_type='l2').fit(X, lambda1=0.02, w_threshold=0.3)
        return _adjacency_to_edge_set(W, varnames)
    except Exception as exc:
        logger.warning("DAGMA discovery failed: %s", exc)
        return set()


def _adjacency_to_edge_set(
    adj: Any, varnames: List[str],
) -> Set[Tuple[str, str]]:
    """Convert an adjacency matrix to a set of (source, target) edges."""
    edges: Set[Tuple[str, str]] = set()
    try:
        import numpy as np
        adj = np.asarray(adj)
        n = adj.shape[0]
        if n != len(varnames):
            return edges
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                if abs(float(adj[i, j])) > 1e-6:
                    edges.add((varnames[i], varnames[j]))
    except Exception:
        return edges
    return edges


# -----------------------------------------------------------------------------
# Ensemble voting
# -----------------------------------------------------------------------------


def ensemble_vote(
    edge_sets: Dict[str, Set[Tuple[str, str]]],
    min_votes: int = 2,
) -> List[M7CausalEdge]:
    """Aggregate per-method edge sets into a vote count per edge.

    Edges with ≥min_votes are 'robust' (handoff §7.3 default: ≥2/4
    methods). Returns sorted by vote count descending.
    """
    if not edge_sets:
        return []

    counts: Dict[Tuple[str, str], int] = {}
    methods_per_edge: Dict[Tuple[str, str], List[str]] = {}
    for method_name, edges in edge_sets.items():
        for edge in edges:
            counts[edge] = counts.get(edge, 0) + 1
            methods_per_edge.setdefault(edge, []).append(method_name)

    robust = [
        M7CausalEdge(
            source=src, target=tgt,
            method_votes=v,
            methods=tuple(sorted(methods_per_edge[(src, tgt)])),
        )
        for (src, tgt), v in counts.items()
        if v >= min_votes
    ]
    robust.sort(key=lambda e: e.method_votes, reverse=True)
    return robust


# -----------------------------------------------------------------------------
# Top-level driver
# -----------------------------------------------------------------------------


def run_causal_discovery(
    X: Any,
    varnames: List[str],
    alpha: float = 0.01,
    min_votes: int = 2,
) -> Tuple[List[M7CausalEdge], DiscoveryDiagnostics]:
    """Run the ensemble (PC + FCI + GES + DAGMA) on standardized X.

    Standardizes X first (Reisach-Seng-Schölkopf 2021).

    Raises CausalDiscoveryLibsMissingError if NO discovery method is
    available. Partial availability (e.g., causal-learn alone) is
    supported — missing methods are recorded as 'failed' in
    diagnostics.
    """
    import time

    diag = DiscoveryDiagnostics(fitted_at_ts=time.time())

    cl = _try_import_causal_learn()
    dagma = _try_import_dagma()

    if cl is None and dagma is None:
        raise CausalDiscoveryLibsMissingError(
            "Neither causal-learn nor dagma installed; cannot run "
            "discovery. Need at least one of: causal-learn>=0.1.4, "
            "dagma>=1.1 (handoff §7.6 library pins)."
        )

    if cl is not None:
        diag.library_versions["causal-learn"] = getattr(cl, "__version__", "unknown")
    if dagma is not None:
        diag.library_versions["dagma"] = getattr(dagma, "__version__", "unknown")

    X_std = standardize_columns(X)

    edge_sets: Dict[str, Set[Tuple[str, str]]] = {}
    method_runners = [
        ("pc", lambda: discover_pc(X_std, varnames, alpha=alpha)),
        ("fci", lambda: discover_fci(X_std, varnames, alpha=alpha)),
        ("ges", lambda: discover_ges(X_std, varnames)),
        ("dagma", lambda: discover_dagma(X_std, varnames)),
    ]
    for name, runner in method_runners:
        try:
            edges = runner()
            if edges:
                edge_sets[name] = edges
                diag.methods_run.append(name)
                diag.edges_per_method[name] = len(edges)
            else:
                diag.methods_failed.append(name)
        except Exception as exc:
            diag.methods_failed.append(name)
            diag.errors.append(f"{name}: {exc}")

    robust_edges = ensemble_vote(edge_sets, min_votes=min_votes)
    diag.robust_edge_count = len(robust_edges)

    return robust_edges, diag


# -----------------------------------------------------------------------------
# Neo4j writeback — (PsychDim)-[:CAUSES]->(PsychDim)
# -----------------------------------------------------------------------------


def write_causal_edge_to_neo4j(
    edge: M7CausalEdge,
    driver: Optional[Any] = None,
) -> bool:
    """Persist a robust causal edge as (:PsychDim)-[:CAUSES]->(:PsychDim).

    Per handoff §7.3: edge properties = votes, methods, discovered_at.
    Idempotent (MERGE).
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
    MERGE (s:PsychDim {name: $source})
    MERGE (t:PsychDim {name: $target})
    MERGE (s)-[r:CAUSES]->(t)
    SET r.votes = $votes,
        r.methods = $methods,
        r.discovered_at = $discovered_at
    """
    try:
        with driver.session() as session:
            session.run(
                cypher,
                source=edge.source, target=edge.target,
                votes=edge.method_votes,
                methods=list(edge.methods),
                discovered_at=time.time(),
            )
        return True
    except Exception as exc:
        logger.warning("Causal edge writeback failed: %s", exc)
        return False
