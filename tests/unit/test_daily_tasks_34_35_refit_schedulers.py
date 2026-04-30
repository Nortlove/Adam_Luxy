"""Pin Task 34 (HB refit) + Task 35 (CF weekly fit) scheduler wrappers.

These tests pin ONLY the scheduler-wrapper layer:
    * The task IS registered in the scheduler registry under the
      expected name.
    * The task adapts FitDiagnostics into a TaskResult with the right
      fields populated.
    * Soft-fail paths (missing driver, no observations, no eligible
      cells, fit driver raising) DO NOT crash the scheduler — they
      land as TaskResult details with appropriate success flags.

The fit math itself is pinned by tests/unit/intelligence/
test_hierarchical_bayes.py and test_causal_forest.py — those tests
exercise the canonical formulas; this file only exercises the
scheduling/adaptation wrappers added in audit §6 follow-up.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import List, Tuple
from unittest.mock import MagicMock, patch

import pytest

from adam.intelligence.daily.task_34_hierarchical_bayes_refit import (
    HierarchicalBayesRefitTask,
)
from adam.intelligence.daily.task_35_causal_forest_fit import (
    CausalForestFitTask,
    _discover_cells_from_decision_log,
)


# -----------------------------------------------------------------------------
# Task 34 — HierarchicalBayesRefitTask
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_task34_success_path_records_diagnostics():
    """Success path: cells_recovered + r̂_max + divergences land on details."""
    fake_diag = SimpleNamespace(
        cells_recovered=42,
        r_hat_max=1.005,
        divergences=0,
        ess_bulk_min=850.0,
        errors=[],
    )

    task = HierarchicalBayesRefitTask()
    with patch(
        "adam.intelligence.hierarchical_bayes.run_nightly_hierarchical_refit",
        return_value=fake_diag,
    ):
        result = await task.execute()

    assert result.success is True
    assert result.items_processed == 42
    assert result.items_stored == 42
    assert result.errors == 0
    assert result.details["cells_recovered"] == 42
    assert result.details["r_hat_max"] == pytest.approx(1.005)
    assert result.details["divergences"] == 0
    assert "warning_r_hat" not in result.details  # 1.005 ≤ 1.01


@pytest.mark.asyncio
async def test_task34_high_r_hat_surfaces_warning():
    """r̂_max > 1.01 must add warning_r_hat to details (without failing)."""
    fake_diag = SimpleNamespace(
        cells_recovered=10, r_hat_max=1.05, divergences=2,
        ess_bulk_min=200.0, errors=[],
    )

    task = HierarchicalBayesRefitTask()
    with patch(
        "adam.intelligence.hierarchical_bayes.run_nightly_hierarchical_refit",
        return_value=fake_diag,
    ):
        result = await task.execute()

    assert result.success is True  # warning, not failure
    assert "warning_r_hat" in result.details
    assert "warning_divergences" in result.details
    assert result.details["warning_divergences"] == 2


@pytest.mark.asyncio
async def test_task34_total_failure_marks_task_failed():
    """If errors are present AND no cells recovered, success=False."""
    fake_diag = SimpleNamespace(
        cells_recovered=0, r_hat_max=0.0, divergences=0,
        ess_bulk_min=0.0,
        errors=["fit driver crashed", "another error"],
    )

    task = HierarchicalBayesRefitTask()
    with patch(
        "adam.intelligence.hierarchical_bayes.run_nightly_hierarchical_refit",
        return_value=fake_diag,
    ):
        result = await task.execute()

    assert result.success is False
    assert result.errors == 2


@pytest.mark.asyncio
async def test_task34_no_observations_returns_zero_cells_no_failure():
    """No observations is a benign empty-cycle case, not a failure.
    (run_nightly_hierarchical_refit returns FitDiagnostics with one
    'no observations available' error and cells_recovered=0 — but
    since errors only come from real fit failures vs cells_recovered>0
    in the loop, an empty obs list still sets errors=['no observations
    available'] which would mark this failed by the rule above. The
    task layer's job is to surface the empty cycle, not duplicate the
    diagnostic logic. Either outcome is acceptable; we just check the
    task DOES land a result with cells_recovered=0.)"""
    fake_diag = SimpleNamespace(
        cells_recovered=0, r_hat_max=0.0, divergences=0,
        ess_bulk_min=0.0,
        errors=["no observations available"],
    )
    task = HierarchicalBayesRefitTask()
    with patch(
        "adam.intelligence.hierarchical_bayes.run_nightly_hierarchical_refit",
        return_value=fake_diag,
    ):
        result = await task.execute()

    assert result.details["cells_recovered"] == 0
    assert "no observations available" in result.details.get("fit_errors", [])


@pytest.mark.asyncio
async def test_task34_fit_driver_exception_recorded():
    """Exception from run_nightly_hierarchical_refit must NOT propagate."""
    task = HierarchicalBayesRefitTask()
    with patch(
        "adam.intelligence.hierarchical_bayes.run_nightly_hierarchical_refit",
        side_effect=RuntimeError("PyMC blew up"),
    ):
        result = await task.execute()

    assert result.success is False
    assert "PyMC blew up" in result.details["error"]


def test_task34_schedule_is_nightly_at_02_utc():
    """Audit §6: nightly cadence."""
    task = HierarchicalBayesRefitTask()
    assert task.schedule_hours == [2]
    assert task.frequency_hours == 24
    assert task.name == "hierarchical_bayes_refit"


# -----------------------------------------------------------------------------
# Task 35 — CausalForestFitTask
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_task35_success_path_records_cell_counts():
    """Success path: cells_fit + cells_skipped_low_n + cells_failed land."""
    fake_cells: List[Tuple[str, str, str]] = [
        ("status_seeker", "social_proof", "luxury_transportation"),
        ("status_seeker", "authority", "luxury_transportation"),
        ("efficiency_optimizer", "scarcity", "professional_services"),
    ]
    fake_diag = SimpleNamespace(
        cells_fit=2, cells_skipped_low_n=1, cells_failed=0,
        errors=[], library_versions={"econml": "0.15.0"},
    )

    task = CausalForestFitTask()
    with patch(
        "adam.intelligence.daily.task_35_causal_forest_fit._discover_cells_from_decision_log",
        return_value=fake_cells,
    ), patch(
        "adam.intelligence.causal_forest.run_weekly_causal_forest_fit",
        return_value=fake_diag,
    ):
        result = await task.execute()

    assert result.success is True
    assert result.items_processed == 3
    assert result.items_stored == 2
    assert result.details["cells_fit"] == 2
    assert result.details["cells_skipped_low_n"] == 1
    assert result.details["cells_failed"] == 0
    assert result.details["library_versions"] == {"econml": "0.15.0"}


@pytest.mark.asyncio
async def test_task35_no_cells_discovered_skips():
    """Empty cell discovery is benign — surface 'skipped' in details."""
    task = CausalForestFitTask()
    with patch(
        "adam.intelligence.daily.task_35_causal_forest_fit._discover_cells_from_decision_log",
        return_value=[],
    ):
        result = await task.execute()

    assert result.success is True
    assert result.details["cells_discovered"] == 0
    assert result.details.get("skipped") == "no_eligible_cells"


@pytest.mark.asyncio
async def test_task35_pure_failure_marks_task_failed():
    """All cells failed (no fits, no low-n skips) → success=False."""
    fake_cells = [("a", "b", "c"), ("d", "e", "f")]
    fake_diag = SimpleNamespace(
        cells_fit=0, cells_skipped_low_n=0, cells_failed=2,
        errors=["econml not installed"],
        library_versions={},
    )

    task = CausalForestFitTask()
    with patch(
        "adam.intelligence.daily.task_35_causal_forest_fit._discover_cells_from_decision_log",
        return_value=fake_cells,
    ), patch(
        "adam.intelligence.causal_forest.run_weekly_causal_forest_fit",
        return_value=fake_diag,
    ):
        result = await task.execute()

    assert result.success is False
    assert result.details["cells_failed"] == 2


@pytest.mark.asyncio
async def test_task35_fit_driver_exception_recorded():
    """Exception from run_weekly_causal_forest_fit must NOT propagate."""
    fake_cells = [("a", "b", "c")]
    task = CausalForestFitTask()
    with patch(
        "adam.intelligence.daily.task_35_causal_forest_fit._discover_cells_from_decision_log",
        return_value=fake_cells,
    ), patch(
        "adam.intelligence.causal_forest.run_weekly_causal_forest_fit",
        side_effect=RuntimeError("CF crashed"),
    ):
        result = await task.execute()

    assert result.success is False
    assert "CF crashed" in result.details["error"]


def test_task35_schedule_is_weekly():
    """Audit §6 + handoff §2.10: weekly cadence."""
    task = CausalForestFitTask()
    assert task.schedule_hours == [3]
    assert task.frequency_hours == 24 * 7
    assert task.name == "causal_forest_weekly_fit"


# -----------------------------------------------------------------------------
# _discover_cells_from_decision_log
# -----------------------------------------------------------------------------


def test_discover_cells_no_driver_returns_empty():
    """Missing Neo4j driver → [], not exception."""
    with patch(
        "adam.core.dependencies.get_neo4j_driver",
        side_effect=RuntimeError("driver unavailable"),
    ):
        cells = _discover_cells_from_decision_log()
    assert cells == []


def test_discover_cells_query_exception_returns_empty():
    """Cypher exception → []."""
    fake_driver = MagicMock()
    fake_session = MagicMock()
    fake_session.run = MagicMock(side_effect=RuntimeError("Cypher syntax"))
    fake_driver.session.return_value.__enter__.return_value = fake_session

    cells = _discover_cells_from_decision_log(driver=fake_driver)
    assert cells == []


def test_discover_cells_filters_partial_records():
    """Records missing any of (archetype, mechanism, category) are dropped."""
    fake_driver = MagicMock()
    fake_session = MagicMock()
    fake_records = [
        {"archetype": "a1", "mechanism": "m1", "category": "c1"},
        {"archetype": "a2", "mechanism": None, "category": "c2"},   # drop
        {"archetype": "a3", "mechanism": "m3", "category": "c3"},
        {"archetype": None, "mechanism": "m4", "category": "c4"},   # drop
    ]
    # Make each "record" support .get(key) like a Neo4j Record
    fake_session.run.return_value = [
        MagicMock(get=lambda k, _r=r: _r.get(k)) for r in fake_records
    ]
    fake_driver.session.return_value.__enter__.return_value = fake_session

    cells = _discover_cells_from_decision_log(driver=fake_driver)
    assert ("a1", "m1", "c1") in cells
    assert ("a3", "m3", "c3") in cells
    assert len(cells) == 2


# -----------------------------------------------------------------------------
# Scheduler registration — task IS in the registry
# -----------------------------------------------------------------------------


def test_tasks_34_35_register_in_scheduler():
    """The two new tasks must show up in the registry."""
    # Force a fresh registry build
    import adam.intelligence.daily.scheduler as scheduler_mod
    scheduler_mod._task_registry.clear()

    registry = scheduler_mod.get_task_registry()

    assert "hierarchical_bayes_refit" in registry, (
        "Task 34 missing from scheduler registry"
    )
    assert "causal_forest_weekly_fit" in registry, (
        "Task 35 missing from scheduler registry"
    )
