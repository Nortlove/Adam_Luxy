"""Pin Task 34 — Nightly hierarchical Bayes refit + knockoff-FDR wiring.

Discipline anchors (B3-LUXY a/b/c/d) for
``adam/intelligence/daily/task_34_hierarchical_bayes_refit.py``:

    (a) Citation: directive line 988 ("Knockoff-filter FDR control on
        which interactions are non-zero") + Phase 6 line 1055
        ("Knockoff-filter FDR control wired"). Composes
        ``iac_prior.load_iac_prior_from_neo4j`` →
        ``iac_fdr_selection.select_pre_specified_for_next_fit`` →
        ``hierarchical_bayes.run_nightly_hierarchical_refit
        (pre_specified_interactions=...)``.

    (b) Boundary anchors pinned by these tests:
          * Name + schedule + frequency invariants.
          * Empty IacPriorMoments (first run / no prior horseshoe
            fit) → refit called with pre_specified_interactions=None
            (original behavior preserved).
          * Non-empty moments → refit called with FDR-selected
            triples; counts surfaced on result.details.
          * FDR-load failure → soft-fail; refit still runs without
            pre_specified; warning recorded.
          * Refit failure → result.success=False with error detail.
          * Successful refit → details carry r_hat_max + cells_recovered
            + divergences + ess_bulk_min + fit_errors.
          * r̂ > 1.01 → diagnostic warning surfaced (not failure).
          * Total fit failure (errors + zero cells) → success=False.

    (c) calibration_pending=False on cadence; calibration_pending=True
        on FDR target via iac_fdr_selection.DEFAULT_FDR_TARGET (A14).

    (d) Honest tags — what is NOT tested here:
          * NUTS sampler convergence — pinned upstream in
            tests/unit/test_hierarchical_bayes_horseshoe.py.
          * BH algorithm correctness — pinned upstream in
            tests/unit/test_iac_fdr_selection.py.
          * Neo4j write/load mechanics for IacPriorMoments — pinned
            upstream in test_iac_prior_*.
          * Full end-to-end with PyMC sampling — these tests stub
            the refit + FDR primitives to keep the suite fast.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch

import pytest

from adam.intelligence.daily.task_34_hierarchical_bayes_refit import (
    HierarchicalBayesRefitTask,
)


# -----------------------------------------------------------------------------
# Fakes — minimal IacPriorMoments + FitDiagnostics duck types
# -----------------------------------------------------------------------------


@dataclass
class _FakeMoments:
    """Stand-in for IacPriorMoments — only the attributes the task reads."""

    moments: Dict[Tuple[str, str, str], Tuple[float, float]] = field(
        default_factory=dict,
    )

    @property
    def n_triples(self) -> int:
        return len(self.moments)

    def is_empty(self) -> bool:
        return len(self.moments) == 0


@dataclass
class _FakeDiag:
    """Stand-in for FitDiagnostics — duck-typed."""

    cells_recovered: int = 0
    r_hat_max: float = 1.0
    divergences: int = 0
    ess_bulk_min: float = 500.0
    errors: List[str] = field(default_factory=list)


# -----------------------------------------------------------------------------
# Schedule + identity invariants
# -----------------------------------------------------------------------------


def test_task_name_is_canonical():
    task = HierarchicalBayesRefitTask()
    assert task.name == "hierarchical_bayes_refit"


def test_task_schedule_hours_at_02_utc():
    """Per the docstring: 02:00 UTC nightly, between data-pull tasks
    (00:00–04:00) and gradient-recompute (05:00)."""
    task = HierarchicalBayesRefitTask()
    assert task.schedule_hours == [2]


def test_task_frequency_24h():
    task = HierarchicalBayesRefitTask()
    assert task.frequency_hours == 24


# -----------------------------------------------------------------------------
# FDR-wiring contract — empty moments → no pre_specified
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_iac_prior_moments_passes_pre_specified_none():
    """First run / no prior horseshoe fit → empty IacPriorMoments →
    refit called with pre_specified_interactions=None."""
    captured: Dict[str, Any] = {}

    def _fake_refit(*, days_lookback, pre_specified_interactions):
        captured["pre_specified_interactions"] = pre_specified_interactions
        captured["days_lookback"] = days_lookback
        return _FakeDiag(cells_recovered=12)

    with patch(
        "adam.intelligence.hierarchical_bayes.run_nightly_hierarchical_refit",
        side_effect=_fake_refit,
    ), patch(
        "adam.intelligence.iac_prior.load_iac_prior_from_neo4j",
        return_value=_FakeMoments(moments={}),
    ):
        task = HierarchicalBayesRefitTask()
        result = await task.execute()

    assert result.success is True
    assert captured["pre_specified_interactions"] is None
    assert captured["days_lookback"] == 90
    assert result.details["fdr_n_candidates"] == 0
    assert result.details["fdr_n_selected"] == 0


@pytest.mark.asyncio
async def test_non_empty_moments_runs_fdr_and_passes_selection():
    """Non-empty moments → FDR selection → refit called with the list."""
    captured: Dict[str, Any] = {}

    fake_moments = _FakeMoments(moments={
        ("achiever", "social_proof", "luxury"): (0.6, 0.04),
        ("achiever", "scarcity", "luxury"): (0.05, 0.04),  # weak
        ("guardian", "authority", "finance"): (0.8, 0.04),
    })

    def _fake_select(moments, fdr_target=0.10):
        # Emulate FDR by returning only the strong-signal triples
        return [
            t for t, (mu, var) in moments.moments.items()
            if abs(mu) / max(var ** 0.5, 1e-6) > 2.0
        ]

    def _fake_refit(*, days_lookback, pre_specified_interactions):
        captured["pre_specified_interactions"] = pre_specified_interactions
        return _FakeDiag(cells_recovered=15)

    with patch(
        "adam.intelligence.hierarchical_bayes.run_nightly_hierarchical_refit",
        side_effect=_fake_refit,
    ), patch(
        "adam.intelligence.iac_prior.load_iac_prior_from_neo4j",
        return_value=fake_moments,
    ), patch(
        "adam.intelligence.iac_fdr_selection.select_pre_specified_for_next_fit",
        side_effect=_fake_select,
    ):
        task = HierarchicalBayesRefitTask()
        result = await task.execute()

    assert result.success is True
    selected = captured["pre_specified_interactions"]
    assert selected is not None
    assert isinstance(selected, list)
    # Both strong-signal triples should pass the synthetic threshold.
    assert ("achiever", "social_proof", "luxury") in selected
    assert ("guardian", "authority", "finance") in selected
    # Weak triple should NOT.
    assert ("achiever", "scarcity", "luxury") not in selected

    assert result.details["fdr_n_candidates"] == 3
    assert result.details["fdr_n_selected"] == len(selected)


@pytest.mark.asyncio
async def test_fdr_load_failure_falls_through_to_no_fdr():
    """load_iac_prior_from_neo4j raising → soft-fail; refit still runs
    with pre_specified=None; warning surfaced on result.details."""
    captured: Dict[str, Any] = {}

    def _fake_refit(*, days_lookback, pre_specified_interactions):
        captured["pre_specified_interactions"] = pre_specified_interactions
        return _FakeDiag(cells_recovered=10)

    with patch(
        "adam.intelligence.hierarchical_bayes.run_nightly_hierarchical_refit",
        side_effect=_fake_refit,
    ), patch(
        "adam.intelligence.iac_prior.load_iac_prior_from_neo4j",
        side_effect=RuntimeError("neo4j down"),
    ):
        task = HierarchicalBayesRefitTask()
        result = await task.execute()

    # Refit STILL runs — the FDR chain is purely additive.
    assert result.success is True
    assert captured["pre_specified_interactions"] is None
    assert "fdr_load_warning" in result.details
    assert "neo4j down" in result.details["fdr_load_warning"]


@pytest.mark.asyncio
async def test_fdr_selection_failure_falls_through_to_no_fdr():
    """select_pre_specified_for_next_fit raising → soft-fail."""
    captured: Dict[str, Any] = {}

    def _fake_refit(*, days_lookback, pre_specified_interactions):
        captured["pre_specified_interactions"] = pre_specified_interactions
        return _FakeDiag(cells_recovered=8)

    fake_moments = _FakeMoments(moments={
        ("a", "m", "c"): (0.5, 0.04),
    })

    with patch(
        "adam.intelligence.hierarchical_bayes.run_nightly_hierarchical_refit",
        side_effect=_fake_refit,
    ), patch(
        "adam.intelligence.iac_prior.load_iac_prior_from_neo4j",
        return_value=fake_moments,
    ), patch(
        "adam.intelligence.iac_fdr_selection.select_pre_specified_for_next_fit",
        side_effect=RuntimeError("FDR math failed"),
    ):
        task = HierarchicalBayesRefitTask()
        result = await task.execute()

    assert result.success is True
    assert captured["pre_specified_interactions"] is None
    assert "fdr_load_warning" in result.details


# -----------------------------------------------------------------------------
# Refit success / failure paths (FDR-orthogonal)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_successful_refit_records_diagnostics():
    """Successful refit → details carry r_hat_max + cells_recovered + ..."""
    diag = _FakeDiag(
        cells_recovered=20,
        r_hat_max=1.005,
        divergences=0,
        ess_bulk_min=850.0,
        errors=[],
    )

    with patch(
        "adam.intelligence.hierarchical_bayes.run_nightly_hierarchical_refit",
        return_value=diag,
    ), patch(
        "adam.intelligence.iac_prior.load_iac_prior_from_neo4j",
        return_value=_FakeMoments(moments={}),
    ):
        task = HierarchicalBayesRefitTask()
        result = await task.execute()

    assert result.success is True
    assert result.items_processed == 20
    assert result.items_stored == 20
    assert result.details["cells_recovered"] == 20
    assert result.details["r_hat_max"] == pytest.approx(1.005)
    assert result.details["divergences"] == 0
    assert result.details["ess_bulk_min"] == pytest.approx(850.0)
    assert result.details["fit_errors"] == []


@pytest.mark.asyncio
async def test_refit_raising_marks_task_failed():
    """run_nightly_hierarchical_refit raising → result.success=False
    + error detail; FDR pre-load already on details."""
    with patch(
        "adam.intelligence.hierarchical_bayes.run_nightly_hierarchical_refit",
        side_effect=RuntimeError("PyMC sampler crashed"),
    ), patch(
        "adam.intelligence.iac_prior.load_iac_prior_from_neo4j",
        return_value=_FakeMoments(moments={}),
    ):
        task = HierarchicalBayesRefitTask()
        result = await task.execute()

    assert result.success is False
    assert "refit failed" in result.details["error"]
    assert "PyMC sampler crashed" in result.details["error"]


@pytest.mark.asyncio
async def test_high_r_hat_surfaces_warning_not_failure():
    """r_hat_max > 1.01 → diagnostic flag, not task failure."""
    diag = _FakeDiag(
        cells_recovered=20,
        r_hat_max=1.05,  # above threshold
        divergences=0,
        ess_bulk_min=400.0,
    )

    with patch(
        "adam.intelligence.hierarchical_bayes.run_nightly_hierarchical_refit",
        return_value=diag,
    ), patch(
        "adam.intelligence.iac_prior.load_iac_prior_from_neo4j",
        return_value=_FakeMoments(moments={}),
    ):
        task = HierarchicalBayesRefitTask()
        result = await task.execute()

    assert result.success is True  # warning, not failure
    assert "warning_r_hat" in result.details


@pytest.mark.asyncio
async def test_divergences_surface_warning():
    diag = _FakeDiag(
        cells_recovered=15,
        r_hat_max=1.0,
        divergences=7,
    )

    with patch(
        "adam.intelligence.hierarchical_bayes.run_nightly_hierarchical_refit",
        return_value=diag,
    ), patch(
        "adam.intelligence.iac_prior.load_iac_prior_from_neo4j",
        return_value=_FakeMoments(moments={}),
    ):
        task = HierarchicalBayesRefitTask()
        result = await task.execute()

    assert result.success is True
    assert result.details["warning_divergences"] == 7


@pytest.mark.asyncio
async def test_total_fit_failure_marks_task_failed():
    """errors present AND cells_recovered=0 → catastrophic; success=False."""
    diag = _FakeDiag(
        cells_recovered=0,
        errors=["NUTS sampler failed", "convergence error"],
    )

    with patch(
        "adam.intelligence.hierarchical_bayes.run_nightly_hierarchical_refit",
        return_value=diag,
    ), patch(
        "adam.intelligence.iac_prior.load_iac_prior_from_neo4j",
        return_value=_FakeMoments(moments={}),
    ):
        task = HierarchicalBayesRefitTask()
        result = await task.execute()

    assert result.success is False
    assert result.errors == 2
    assert "NUTS sampler failed" in result.details["fit_errors"]


# -----------------------------------------------------------------------------
# fdr_n_candidates / fdr_n_selected preserved alongside fit details
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fdr_counts_preserved_across_details_merge():
    """The result.details['fdr_n_*'] keys must survive the post-refit
    update() that adds fit-diagnostic keys."""
    fake_moments = _FakeMoments(moments={
        ("a", "m", "c"): (0.5, 0.04),
        ("b", "n", "d"): (0.0, 0.04),
    })
    selected = [("a", "m", "c")]

    def _fake_refit(*, days_lookback, pre_specified_interactions):
        return _FakeDiag(cells_recovered=5)

    with patch(
        "adam.intelligence.hierarchical_bayes.run_nightly_hierarchical_refit",
        side_effect=_fake_refit,
    ), patch(
        "adam.intelligence.iac_prior.load_iac_prior_from_neo4j",
        return_value=fake_moments,
    ), patch(
        "adam.intelligence.iac_fdr_selection.select_pre_specified_for_next_fit",
        return_value=selected,
    ):
        task = HierarchicalBayesRefitTask()
        result = await task.execute()

    # Both FDR keys AND fit-diagnostic keys present.
    assert result.details["fdr_n_candidates"] == 2
    assert result.details["fdr_n_selected"] == 1
    assert result.details["cells_recovered"] == 5
    assert "r_hat_max" in result.details
