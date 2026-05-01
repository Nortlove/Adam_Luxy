"""Pin Task 40 — Spine #5 dual_eval_context nightly re-warm.

Discipline anchors (B3-LUXY a/b/c/d):

    (a) Citations: directive Section 6.2 (offline daily cadence);
        Section 9 Phase 4 deliverable; Slice 20
        (warm_dual_eval_from_neo4j composer).

    (b) Boundary anchors:
          - name "dual_eval_rewarm"
          - schedule_hours [3] (03:00 UTC)
          - frequency_hours 24
          - no driver → skipped on result.details
          - successful warm → outcome propagates to result.details
          - cold_start → success=True (not a failure)
          - exception → success=False with error detail
          - registered in scheduler

    (c) calibration_pending=True. 03:00 UTC slot conservative.

    (d) Honest tags — what is NOT tested:
          - Real Claude API label generation (sibling task).
          - Sub-daily cadence variants (sibling).
          - Per-cohort dual-eval contexts (BLOCKED on Loop B).
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adam.intelligence.daily.task_40_dual_eval_rewarm import (
    DualEvalRewarmTask,
)


# -----------------------------------------------------------------------------
# Schedule + identity
# -----------------------------------------------------------------------------


def test_task_name_canonical():
    assert DualEvalRewarmTask().name == "dual_eval_rewarm"


def test_task_schedule_hours_03_utc():
    """03:00 UTC nightly — after Task 34 hierarchical refit (02:00)."""
    assert DualEvalRewarmTask().schedule_hours == [3]


def test_task_frequency_24h():
    assert DualEvalRewarmTask().frequency_hours == 24


# -----------------------------------------------------------------------------
# execute() routing
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_no_driver_returns_skipped():
    """When neo4j driver is unavailable, task succeeds but logs skipped."""
    fake_infra = MagicMock()
    fake_infra.neo4j_driver = None
    fake_infra.neo4j = None

    async def _fake_get_infra():
        return fake_infra

    with patch(
        "adam.core.dependencies.get_infrastructure",
        side_effect=_fake_get_infra,
    ):
        task = DualEvalRewarmTask()
        result = await task.execute()

    assert result.success is True
    assert result.details.get("skipped") == "no_neo4j_driver"


@pytest.mark.asyncio
async def test_execute_routes_to_warm_composer():
    """Successful warm propagates outcome to result.details."""
    fake_infra = MagicMock()
    fake_infra.neo4j_driver = MagicMock()  # truthy

    async def _fake_get_infra():
        return fake_infra

    fake_warm_status = {
        "outcome": "registered",
        "n_labels": 50,
        "trained_models": ["logistic_v1", "hierarchical_bayes_v1"],
        "winner": "logistic_v1",
        "reason": "",
    }

    async def _fake_warm(driver):
        return fake_warm_status

    with patch(
        "adam.core.dependencies.get_infrastructure",
        side_effect=_fake_get_infra,
    ), patch(
        "adam.intelligence.free_energy_dual_eval.warm_dual_eval_from_neo4j",
        side_effect=_fake_warm,
    ):
        task = DualEvalRewarmTask()
        result = await task.execute()

    assert result.success is True
    assert result.details["outcome"] == "registered"
    assert result.details["n_labels"] == 50
    assert result.details["winner"] == "logistic_v1"
    assert result.details["trained_models"] == [
        "logistic_v1", "hierarchical_bayes_v1",
    ]
    assert result.items_processed == 50
    assert result.items_stored == 1


@pytest.mark.asyncio
async def test_execute_cold_start_does_not_fail():
    """Cold start (no labels) is not a task failure — passthrough
    primary keeps the cascade running."""
    fake_infra = MagicMock()
    fake_infra.neo4j_driver = MagicMock()

    async def _fake_get_infra():
        return fake_infra

    async def _fake_warm(driver):
        return {
            "outcome": "cold_start",
            "n_labels": 5,
            "trained_models": [],
            "winner": None,
            "reason": "only 5 labels (< 20 required); keeping passthrough",
        }

    with patch(
        "adam.core.dependencies.get_infrastructure",
        side_effect=_fake_get_infra,
    ), patch(
        "adam.intelligence.free_energy_dual_eval.warm_dual_eval_from_neo4j",
        side_effect=_fake_warm,
    ):
        task = DualEvalRewarmTask()
        result = await task.execute()

    assert result.success is True  # cold start is OK
    assert result.details["outcome"] == "cold_start"
    assert result.items_stored == 0  # no model registered


@pytest.mark.asyncio
async def test_execute_warm_exception_marks_failed():
    """If warm_dual_eval_from_neo4j raises (unexpected), task fails
    with error detail."""
    fake_infra = MagicMock()
    fake_infra.neo4j_driver = MagicMock()

    async def _fake_get_infra():
        return fake_infra

    async def _fake_warm_raises(driver):
        raise RuntimeError("unexpected")

    with patch(
        "adam.core.dependencies.get_infrastructure",
        side_effect=_fake_get_infra,
    ), patch(
        "adam.intelligence.free_energy_dual_eval.warm_dual_eval_from_neo4j",
        side_effect=_fake_warm_raises,
    ):
        task = DualEvalRewarmTask()
        result = await task.execute()

    assert result.success is False
    assert "warm_dual_eval_from_neo4j failed" in result.details["error"]


@pytest.mark.asyncio
async def test_execute_skipped_outcome_logs_warning_but_succeeds():
    """warm returns 'skipped' (load_labels failed mid-chain) — task
    still succeeds (the cascade has its previous primary)."""
    fake_infra = MagicMock()
    fake_infra.neo4j_driver = MagicMock()

    async def _fake_get_infra():
        return fake_infra

    async def _fake_warm(driver):
        return {
            "outcome": "skipped",
            "n_labels": 0,
            "trained_models": [],
            "winner": None,
            "reason": "load_labels_failed: connection refused",
        }

    with patch(
        "adam.core.dependencies.get_infrastructure",
        side_effect=_fake_get_infra,
    ), patch(
        "adam.intelligence.free_energy_dual_eval.warm_dual_eval_from_neo4j",
        side_effect=_fake_warm,
    ):
        task = DualEvalRewarmTask()
        result = await task.execute()

    assert result.success is True  # not a hard failure
    assert result.details["outcome"] == "skipped"
    assert "connection refused" in result.details["warm_reason"]


# -----------------------------------------------------------------------------
# Scheduler registration
# -----------------------------------------------------------------------------


def test_task_40_registered_in_scheduler():
    """Verify Task 40 is registered in the scheduler's task registry."""
    from adam.intelligence.daily.scheduler import (
        _register_all_tasks,
        _task_registry,
    )
    # Reset and re-register to ensure idempotency
    _task_registry.clear()
    _register_all_tasks()
    assert "dual_eval_rewarm" in _task_registry
    task = _task_registry["dual_eval_rewarm"]
    assert isinstance(task, DualEvalRewarmTask)
