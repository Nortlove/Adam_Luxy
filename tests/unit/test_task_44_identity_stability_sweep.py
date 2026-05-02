"""Pin Task 44 — daily identity-stability sweep runner.

Schedule + execution contract pin for the Slice 16 sibling that
closes RED criterion #4 producer.
"""

from __future__ import annotations

import time
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from adam.intelligence.daily.task_44_identity_stability_sweep import (
    IdentityStabilitySweepTask,
)


# -----------------------------------------------------------------------------
# Schedule contract
# -----------------------------------------------------------------------------


def test_task_44_name():
    task = IdentityStabilitySweepTask()
    assert task.name == "identity_stability_sweep"


def test_task_44_schedule_hours_before_task_42():
    """04:00 UTC slot — must be BEFORE Task 42's 05:00 so the
    snapshot accumulator is populated when Task 42 reads + resets."""
    task = IdentityStabilitySweepTask()
    assert task.schedule_hours == [4]


def test_task_44_frequency_24h():
    task = IdentityStabilitySweepTask()
    assert task.frequency_hours == 24


# -----------------------------------------------------------------------------
# Scheduler registration
# -----------------------------------------------------------------------------


def test_task_44_registered_in_scheduler():
    """Source-text contract pin: scheduler imports + registers Task 44."""
    from pathlib import Path
    src = Path("adam/intelligence/daily/scheduler.py").read_text()
    assert "task_44_identity_stability_sweep" in src, (
        "Task 44 import missing from scheduler. RED criterion #4 "
        "producer will never run."
    )
    assert "IdentityStabilitySweepTask" in src


# -----------------------------------------------------------------------------
# execute() routing
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_no_decision_cache_skips():
    """When get_decision_cache raises → task succeeds with skipped reason."""
    task = IdentityStabilitySweepTask()
    with patch(
        "adam.api.stackadapt.decision_cache.get_decision_cache",
        side_effect=RuntimeError("boom"),
    ):
        result = await task.execute()
    assert result.success is True  # skipped is not failure
    assert "skipped" in result.details


@pytest.mark.asyncio
async def test_execute_runs_sweep_and_surfaces_counts():
    """When decision_cache is available, execute() runs sweep and
    surfaces n_active / n_collapsed / collapse_fraction in details."""
    task = IdentityStabilitySweepTask()

    class _FakeCtx:
        def __init__(self, bid, ts):
            self.buyer_id = bid
            self.created_at = ts

    now = time.time()
    fake_cache = MagicMock()
    fake_cache._store = {
        "d1": _FakeCtx("buyer-1", now),
        "d2": _FakeCtx("buyer-old", now - 200 * 86400.0),
    }

    fake_snapshot = MagicMock()

    with patch(
        "adam.api.stackadapt.decision_cache.get_decision_cache",
        return_value=fake_cache,
    ), patch(
        "adam.intelligence.red_criteria_snapshot.get_red_snapshot",
        return_value=fake_snapshot,
    ):
        result = await task.execute()

    assert result.success is True
    assert "n_active" in result.details
    assert "n_collapsed" in result.details
    assert "collapse_fraction" in result.details
    # buyer-1 fresh, buyer-old's Δ=200d is past default 30d lookback
    # → only buyer-1 counted active.
    assert result.details["n_active"] == 1
    assert result.details["n_collapsed"] == 0


@pytest.mark.asyncio
async def test_execute_increments_snapshot_when_active_buyers_present():
    """Snapshot accumulator counters incremented when n_active > 0."""
    task = IdentityStabilitySweepTask()

    class _FakeCtx:
        def __init__(self, bid, ts):
            self.buyer_id = bid
            self.created_at = ts

    now = time.time()
    fake_cache = MagicMock()
    fake_cache._store = {"d1": _FakeCtx("buyer-1", now)}

    fake_snapshot = MagicMock()

    with patch(
        "adam.api.stackadapt.decision_cache.get_decision_cache",
        return_value=fake_cache,
    ), patch(
        "adam.intelligence.red_criteria_snapshot.get_red_snapshot",
        return_value=fake_snapshot,
    ):
        await task.execute()

    fake_snapshot.record_user_active.assert_called_once_with(1)
    # No collapsed buyers in this scenario.
    fake_snapshot.record_identity_collapse.assert_not_called()


@pytest.mark.asyncio
async def test_execute_handles_sweep_exception_gracefully():
    """If sweep_active_buyers raises, task surfaces failure but
    does not propagate (task framework expects task.execute to
    return a TaskResult, not raise)."""
    task = IdentityStabilitySweepTask()

    fake_cache = MagicMock()
    fake_cache._store = {}

    with patch(
        "adam.api.stackadapt.decision_cache.get_decision_cache",
        return_value=fake_cache,
    ), patch(
        "adam.intelligence.identity_stability_sweep.sweep_active_buyers",
        side_effect=RuntimeError("sweep boom"),
    ):
        result = await task.execute()

    assert result.success is False
    assert "error" in result.details


# -----------------------------------------------------------------------------
# task_42 honest tag updated
# -----------------------------------------------------------------------------


def test_task_42_honest_tag_marks_producer_shipped():
    """Task 42's named-sibling tag for RED criterion #4 must be
    updated to reflect Slice 16 / Task 44 shipped (so future agents
    don't re-implement)."""
    from pathlib import Path
    src = Path(
        "adam/intelligence/daily/task_42_launch_gate_runner.py"
    ).read_text()
    # Line break in docstring → check the marker pieces separately.
    assert "SHIPPED" in src and "Slice 16" in src, (
        "Task 42 honest tag (line 43-46) still says producer is "
        "sibling — should reflect Slice 16 shipped."
    )
