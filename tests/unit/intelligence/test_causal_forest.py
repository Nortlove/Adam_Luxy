"""Pin the M2 Causal Forests substrate.

Discipline anchors:
    - The fitter raises LibsMissingError when EconML isn't installed.
      Returning None on missing libs would let callers consume
      meaningless τ̂ values silently — exact drift pattern we exist to
      prevent.
    - pscore_known=False rows MUST be excluded before fitting. WCLS and
      OPE have the same discipline; CF inherits it.
    - All-control / all-treatment cells return CATEResult with
      cell_under_powered=True rather than raising — the writeback can
      audit this state without the weekly job crashing.
    - Neo4j writeback uses property names that match handoff §2.7
      verbatim (tau, tau_lo, tau_hi, n, fitted_at).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from adam.intelligence.causal_forest import (
    CATEResult,
    FitDiagnostics,
    LibsMissingError,
    LoggedDecisionRow,
    fit_causal_forest_for_cell,
    load_decision_outcome_rows_for_cell,
    run_weekly_causal_forest_fit,
    write_cate_to_neo4j,
)


def _make_row(treatment: int = 1, outcome: float = 1.0,
              propensity: float = 0.97, pscore_known: bool = True,
              context_features=None) -> LoggedDecisionRow:
    return LoggedDecisionRow(
        archetype="status_seeker",
        mechanism="social_proof",
        category="luxury_transportation",
        user_id="u1",
        context_features=context_features or {},
        treatment=treatment, outcome=outcome,
        propensity=propensity, pscore_known=pscore_known,
    )


# -----------------------------------------------------------------------------
# Soft-import gate — fitter raises clearly when libs missing
# -----------------------------------------------------------------------------


def test_fit_raises_libs_missing_error_when_econml_unavailable():
    """If EconML isn't installed, fit_causal_forest_for_cell must
    raise LibsMissingError, NOT return None or silently fail."""
    rows = [_make_row(treatment=1), _make_row(treatment=0)]
    with patch(
        "adam.intelligence.causal_forest._try_import_econml",
        return_value=None,
    ):
        with pytest.raises(LibsMissingError):
            fit_causal_forest_for_cell(rows)


def test_fit_raises_value_error_on_empty_rows():
    with pytest.raises(ValueError):
        fit_causal_forest_for_cell([])


# -----------------------------------------------------------------------------
# pscore_known discipline
# -----------------------------------------------------------------------------


def test_fit_filters_out_pscore_unknown_rows():
    """Rows with pscore_known=False must be excluded — Boruvka 2018 §2."""
    rows = [
        _make_row(treatment=1, outcome=1.0, pscore_known=False),
        _make_row(treatment=0, outcome=0.0, pscore_known=False),
    ]
    # All rows excluded → ValueError (CATE not estimable)
    with patch(
        "adam.intelligence.causal_forest._try_import_econml",
        return_value=MagicMock(),  # pretend EconML is present
    ):
        with pytest.raises(ValueError, match="pscore_known"):
            fit_causal_forest_for_cell(rows)


# -----------------------------------------------------------------------------
# Degenerate cells — all-control, all-treatment
# -----------------------------------------------------------------------------


def test_fit_all_treatment_returns_under_powered():
    """All-treatment cell can't estimate counterfactual outcome → flag
    as under-powered, return τ̂=0 rather than raise. The weekly job
    must continue past degenerate cells."""
    rows = [_make_row(treatment=1, outcome=1.0) for _ in range(50)]
    with patch(
        "adam.intelligence.causal_forest._try_import_econml",
        return_value=MagicMock(),
    ):
        result = fit_causal_forest_for_cell(rows)

    assert result.cell_under_powered is True
    assert result.tau_hat == 0.0
    assert result.archetype == "status_seeker"
    assert result.mechanism == "social_proof"


def test_fit_all_control_returns_under_powered():
    rows = [_make_row(treatment=0, outcome=0.0) for _ in range(50)]
    with patch(
        "adam.intelligence.causal_forest._try_import_econml",
        return_value=MagicMock(),
    ):
        result = fit_causal_forest_for_cell(rows)
    assert result.cell_under_powered is True


# -----------------------------------------------------------------------------
# Data loader — Neo4j unavailable returns []
# -----------------------------------------------------------------------------


def test_loader_returns_empty_when_driver_unavailable():
    rows = load_decision_outcome_rows_for_cell(
        "status_seeker", "social_proof", "luxury_transportation",
        driver=None,
    )
    assert rows == []


def test_loader_query_filters_pscore_known():
    """The Cypher query must filter on pscore_known=true. Pin so a
    refactor can't silently drop the filter."""
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__ = MagicMock(return_value=session)
    driver.session.return_value.__exit__ = MagicMock(return_value=None)
    session.run = MagicMock(return_value=[])

    load_decision_outcome_rows_for_cell(
        "status_seeker", "social_proof", "luxury_transportation",
        driver=driver,
    )

    # Inspect the Cypher actually sent
    call_args = session.run.call_args
    cypher = call_args.args[0]
    assert "pscore_known = true" in cypher


# -----------------------------------------------------------------------------
# Neo4j writeback — schema fidelity to handoff §2.7
# -----------------------------------------------------------------------------


def test_write_uses_handoff_property_names():
    """Property names tau, tau_lo, tau_hi, n, fitted_at must match
    handoff §2.7 verbatim. Drift here breaks any downstream consumer
    expecting the canonical schema."""
    driver = MagicMock()
    session = MagicMock()
    driver.session.return_value.__enter__ = MagicMock(return_value=session)
    driver.session.return_value.__exit__ = MagicMock(return_value=None)

    result = CATEResult(
        archetype="status_seeker", mechanism="social_proof",
        category="luxury_transportation",
        tau_hat=0.05, tau_lower=0.02, tau_upper=0.08, n_events=500,
    )

    ok = write_cate_to_neo4j(result, driver=driver)
    assert ok is True

    cypher = session.run.call_args.args[0]
    assert "r.tau = $tau" in cypher
    assert "r.tau_lo = $tau_lower" in cypher
    assert "r.tau_hi = $tau_upper" in cypher
    assert "r.n = $n" in cypher
    assert "r.fitted_at = $fitted_at" in cypher


def test_write_returns_false_when_driver_unavailable():
    """When driver=None and the auto-built sync driver also unavailable
    (no NEO4J env vars / unreachable Neo4j), write returns False."""
    result = CATEResult(
        archetype="x", mechanism="y", category="z",
        tau_hat=0.0, tau_lower=0.0, tau_upper=0.0, n_events=0,
    )
    with patch(
        "adam.core.dependencies.get_neo4j_driver",
        return_value=None,
    ):
        ok = write_cate_to_neo4j(result, driver=None)
    assert ok is False


def test_write_returns_false_when_session_raises():
    driver = MagicMock()
    driver.session.side_effect = ConnectionError("auth")
    result = CATEResult(
        archetype="x", mechanism="y", category="z",
        tau_hat=0.0, tau_lower=0.0, tau_upper=0.0, n_events=0,
    )
    ok = write_cate_to_neo4j(result, driver=driver)
    assert ok is False


# -----------------------------------------------------------------------------
# Weekly orchestrator
# -----------------------------------------------------------------------------


def test_weekly_skips_low_n_cells():
    """Cells with <30 rows are skipped — too few for meaningful fit."""
    cells = [("status_seeker", "social_proof", "luxury_transportation")]

    with patch(
        "adam.intelligence.causal_forest.load_decision_outcome_rows_for_cell",
        return_value=[_make_row() for _ in range(5)],  # only 5 rows
    ):
        diag = run_weekly_causal_forest_fit(cells, driver=MagicMock())

    assert diag.cells_skipped_low_n == 1
    assert diag.cells_fit == 0


def test_weekly_records_libs_missing_as_error():
    """When EconML isn't installed AND the cell has both treatments
    (so the degenerate-cell short-circuit doesn't fire), the weekly
    job continues and records the LibsMissingError per cell rather
    than crashing."""
    cells = [("status_seeker", "social_proof", "luxury_transportation")]
    # Mix treatments so we reach the lib-import branch (degenerate
    # short-circuit only fires on all-T or all-C cells)
    mixed_rows = (
        [_make_row(treatment=1, outcome=1.0) for _ in range(25)]
        + [_make_row(treatment=0, outcome=0.0) for _ in range(25)]
    )
    with patch(
        "adam.intelligence.causal_forest.load_decision_outcome_rows_for_cell",
        return_value=mixed_rows,
    ), patch(
        "adam.intelligence.causal_forest._try_import_econml",
        return_value=None,
    ):
        diag = run_weekly_causal_forest_fit(cells, driver=MagicMock())

    assert diag.cells_failed == 1
    assert any("EconML" in e or "econml" in e for e in diag.errors)


def test_weekly_succeeds_with_mocked_writeback():
    """End-to-end with a mocked fitter + mocked writeback. Confirms the
    weekly orchestration glue is sound even when libs aren't present."""
    cells = [("status_seeker", "social_proof", "luxury_transportation")]
    fake_result = CATEResult(
        archetype="status_seeker", mechanism="social_proof",
        category="luxury_transportation",
        tau_hat=0.05, tau_lower=0.02, tau_upper=0.08, n_events=500,
    )

    with patch(
        "adam.intelligence.causal_forest.load_decision_outcome_rows_for_cell",
        return_value=[_make_row() for _ in range(50)],
    ), patch(
        "adam.intelligence.causal_forest.fit_causal_forest_for_cell",
        return_value=fake_result,
    ), patch(
        "adam.intelligence.causal_forest.write_cate_to_neo4j",
        return_value=True,
    ):
        diag = run_weekly_causal_forest_fit(cells, driver=MagicMock())

    assert diag.cells_fit == 1
    assert diag.cells_failed == 0
    assert diag.errors == []
