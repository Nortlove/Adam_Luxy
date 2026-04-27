"""Pin the M7 causal-discovery ensemble substrate.

Discipline anchors:
    - Standardization is MANDATORY before any DAG fit. NOTEARS / DAGMA
      exploit variance ordering; an unstandardized fit produces
      spurious edges (Reisach-Seng-Schölkopf 2021). Pin the
      standardize_columns behavior so a refactor can't bypass it.
    - Ensemble voting threshold = 2/4 methods (handoff §7.3 default).
      Edges with fewer votes are treated as candidates, not robust
      edges. Drift in this threshold silently changes which edges
      flow into M2 adjustment sets and M1 covariate identification.
    - LibsMissingError raised cleanly when ALL discovery libs missing.
      Partial install (e.g., causal-learn alone, no DAGMA) is
      supported — missing methods recorded as failed in diagnostics.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from adam.intelligence.causal_dag_ensemble import (
    CausalDiscoveryLibsMissingError,
    M7CausalEdge,
    ensemble_vote,
    run_causal_discovery,
    standardize_columns,
    write_causal_edge_to_neo4j,
)


# -----------------------------------------------------------------------------
# Standardization — Reisach-Seng-Schölkopf 2021 defense
# -----------------------------------------------------------------------------


def test_standardize_zero_mean_unit_variance():
    """After standardization, each column has mean 0 and var 1
    (within float tolerance)."""
    import numpy as np
    X = np.array([
        [1.0, 100.0],
        [2.0, 200.0],
        [3.0, 300.0],
        [4.0, 400.0],
    ])
    X_std = standardize_columns(X)
    assert abs(X_std.mean(axis=0)).max() < 1e-9
    assert abs(X_std.std(axis=0) - 1.0).max() < 1e-9


def test_standardize_handles_zero_variance_column():
    """Constant column has std=0 — division by zero would NaN. The
    safety guard sets std=1 so the column passes through unchanged
    (centered to 0)."""
    import numpy as np
    X = np.array([
        [1.0, 5.0],
        [2.0, 5.0],
        [3.0, 5.0],
    ])
    X_std = standardize_columns(X)
    # Constant column → all zeros after centering, no NaN
    assert not np.isnan(X_std).any()


# -----------------------------------------------------------------------------
# Ensemble voting
# -----------------------------------------------------------------------------


def test_vote_keeps_edges_meeting_min_votes():
    """Edge seen in 2 methods passes; edge in 1 method drops at
    min_votes=2."""
    edge_sets = {
        "pc": {("A", "B"), ("A", "C")},
        "ges": {("A", "B"), ("B", "C")},
    }
    robust = ensemble_vote(edge_sets, min_votes=2)
    edge_pairs = {(e.source, e.target) for e in robust}
    assert ("A", "B") in edge_pairs
    assert ("A", "C") not in edge_pairs   # only 1 vote
    assert ("B", "C") not in edge_pairs   # only 1 vote


def test_vote_counts_correctly():
    """Same edge from 3 methods should report method_votes=3 with
    all three method names."""
    edge_sets = {
        "pc": {("A", "B")},
        "fci": {("A", "B")},
        "ges": {("A", "B")},
    }
    robust = ensemble_vote(edge_sets, min_votes=1)
    assert len(robust) == 1
    assert robust[0].method_votes == 3
    assert set(robust[0].methods) == {"pc", "fci", "ges"}


def test_vote_sorts_by_votes_descending():
    edge_sets = {
        "pc": {("A", "B"), ("C", "D")},
        "fci": {("A", "B")},
        "ges": {("A", "B"), ("E", "F")},
    }
    robust = ensemble_vote(edge_sets, min_votes=1)
    # A→B has 3 votes, others have 1
    assert robust[0].source == "A" and robust[0].target == "B"
    assert robust[0].method_votes == 3


def test_vote_empty_input_returns_empty():
    assert ensemble_vote({}) == []


# -----------------------------------------------------------------------------
# Soft-import gate — partial install is supported
# -----------------------------------------------------------------------------


def test_run_raises_libs_missing_when_no_methods_available():
    """If both causal-learn and dagma are absent, NOTHING can vote.
    Raise rather than return empty — empty would be ambiguous between
    'real result is empty' and 'no methods ran'."""
    with patch(
        "adam.intelligence.causal_dag_ensemble._try_import_causal_learn",
        return_value=None,
    ), patch(
        "adam.intelligence.causal_dag_ensemble._try_import_dagma",
        return_value=None,
    ):
        with pytest.raises(CausalDiscoveryLibsMissingError):
            run_causal_discovery(X=[[1, 2]], varnames=["a", "b"])


def test_run_records_partial_availability():
    """When causal-learn IS installed but dagma isn't, the run still
    proceeds and records dagma as failed in diagnostics."""
    fake_cl = MagicMock()
    fake_cl.__version__ = "0.1.4"
    with patch(
        "adam.intelligence.causal_dag_ensemble._try_import_causal_learn",
        return_value=fake_cl,
    ), patch(
        "adam.intelligence.causal_dag_ensemble._try_import_dagma",
        return_value=None,
    ), patch(
        "adam.intelligence.causal_dag_ensemble.discover_pc",
        return_value=set(),  # no actual fit attempted
    ), patch(
        "adam.intelligence.causal_dag_ensemble.discover_fci",
        return_value=set(),
    ), patch(
        "adam.intelligence.causal_dag_ensemble.discover_ges",
        return_value=set(),
    ):
        # Don't patch discover_dagma — real one returns set() because
        # dagma isn't installed
        edges, diag = run_causal_discovery(
            X=[[1, 2], [3, 4]], varnames=["a", "b"],
        )

    # No edges (all methods returned empty set)
    assert edges == []
    # Library version recorded for causal-learn but not for dagma
    assert "causal-learn" in diag.library_versions
    assert "dagma" not in diag.library_versions
    # All four methods recorded as failed (returned empty)
    assert "dagma" in diag.methods_failed


# -----------------------------------------------------------------------------
# Neo4j writeback — schema fidelity
# -----------------------------------------------------------------------------


def test_writeback_uses_psychdim_causes_schema():
    """Edge target must be (PsychDim)-[:CAUSES]->(PsychDim) per handoff
    §7.3. Edge properties: votes, methods, discovered_at."""
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__ = MagicMock(return_value=session)
    driver.session.return_value.__exit__ = MagicMock(return_value=None)

    edge = M7CausalEdge(
        source="regulatory_fit", target="conversion",
        method_votes=3, methods=("pc", "fci", "ges"),
    )
    ok = write_causal_edge_to_neo4j(edge, driver=driver)
    assert ok is True

    cypher = session.run.call_args.args[0]
    assert "PsychDim" in cypher
    assert ":CAUSES" in cypher
    assert "r.votes = $votes" in cypher
    assert "r.methods = $methods" in cypher


def test_writeback_returns_false_when_driver_unavailable():
    edge = M7CausalEdge(source="x", target="y", method_votes=2)
    ok = write_causal_edge_to_neo4j(edge, driver=None)
    assert ok is False


def test_writeback_returns_false_on_session_exception():
    driver = MagicMock()
    driver.session.side_effect = ConnectionError("auth")
    edge = M7CausalEdge(source="x", target="y", method_votes=2)
    ok = write_causal_edge_to_neo4j(edge, driver=driver)
    assert ok is False
