"""Pin the horizon adjudicator daily task that closes Loop γ auto-path.

Discipline anchors:
    - The auto path of causal_adjudicator.adjudicate_ready_deviations
      was previously exposed only via the dashboard's operator-triggered
      route. Without a daily scheduler call site, the auto-adjudication
      NEVER fired — operators who don't open the dashboard left
      horizon-expired Deviations forever pending. These tests pin the
      auto path's daily firing.
    - Per-user iteration: the underlying function takes user_id; the
      task enumerates users-with-pending-deviations and calls per-user.
    - Soft-fail: per-user failures are counted but don't propagate;
      one bad user's adjudication doesn't block the rest of the batch.
"""

from __future__ import annotations

from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from adam.intelligence.daily.task_29_6_horizon_adjudicator import (
    HorizonAdjudicatorTask,
)


def _adjudication_batch(adjudicated_count=0, too_early=0, no_data=0, already_done=0):
    """Stub a causal_adjudicator AdjudicationBatch return."""
    batch = MagicMock()
    batch.adjudicated = [MagicMock() for _ in range(adjudicated_count)]
    batch.skipped_too_early = too_early
    batch.skipped_no_data = no_data
    batch.skipped_already_done = already_done
    return batch


# -----------------------------------------------------------------------------
# Empty case — no users with pending deviations → success, zero counts
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_pending_users_succeeds_with_zero_counts():
    with patch(
        "adam.intelligence.daily.task_29_6_horizon_adjudicator._users_with_pending_deviations",
        new=AsyncMock(return_value=[]),
    ):
        task = HorizonAdjudicatorTask()
        result = await task.execute()

    assert result.success is True
    assert result.items_processed == 0
    assert result.items_stored == 0
    assert result.details["users_total"] == 0
    assert result.details["adjudicated"] == 0


# -----------------------------------------------------------------------------
# Multi-user iteration — counts aggregate across users
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_aggregates_counts_across_users():
    """When N users have pending deviations, each gets their own
    adjudicate_ready_deviations call; counts aggregate."""
    fake_batches = [
        _adjudication_batch(adjudicated_count=2, too_early=1),
        _adjudication_batch(adjudicated_count=0, no_data=3),
        _adjudication_batch(adjudicated_count=1, already_done=2),
    ]

    with patch(
        "adam.intelligence.daily.task_29_6_horizon_adjudicator._users_with_pending_deviations",
        new=AsyncMock(return_value=["user_A", "user_B", "user_C"]),
    ), patch(
        "adam.intelligence.causal_adjudicator.adjudicate_ready_deviations",
        new=AsyncMock(side_effect=fake_batches),
    ):
        task = HorizonAdjudicatorTask()
        result = await task.execute()

    assert result.success is True
    assert result.items_processed == 3  # 3 users
    assert result.items_stored == 3      # 2 + 0 + 1 adjudicated
    assert result.details["users_processed"] == 3
    assert result.details["users_failed"] == 0
    assert result.details["adjudicated"] == 3
    assert result.details["skipped_too_early"] == 1
    assert result.details["skipped_no_data"] == 3
    assert result.details["skipped_already_done"] == 2


# -----------------------------------------------------------------------------
# Per-user soft-fail — one bad user doesn't block the rest
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_per_user_failure_does_not_block_batch():
    """If adjudicate_ready_deviations raises for one user, the task
    counts the failure and continues with the remaining users."""
    fake_responses = [
        _adjudication_batch(adjudicated_count=1),
        RuntimeError("simulated user-level failure"),
        _adjudication_batch(adjudicated_count=2),
    ]

    with patch(
        "adam.intelligence.daily.task_29_6_horizon_adjudicator._users_with_pending_deviations",
        new=AsyncMock(return_value=["user_A", "user_B", "user_C"]),
    ), patch(
        "adam.intelligence.causal_adjudicator.adjudicate_ready_deviations",
        new=AsyncMock(side_effect=fake_responses),
    ):
        task = HorizonAdjudicatorTask()
        result = await task.execute()

    # Task surfaces partial failure but did process 2/3 users
    assert result.success is False  # users_failed > 0 → success=False
    assert result.errors == 1
    assert result.details["users_processed"] == 2
    assert result.details["users_failed"] == 1
    assert result.details["adjudicated"] == 3  # 1 + 2 from successful users


# -----------------------------------------------------------------------------
# Soft-fail on user-enumeration failure — doesn't propagate
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_enumeration_failure_returns_failure_taskresult():
    """When the Neo4j query for users-with-pending-deviations fails,
    the task returns success=False with error details, not raising."""
    with patch(
        "adam.intelligence.daily.task_29_6_horizon_adjudicator._users_with_pending_deviations",
        new=AsyncMock(side_effect=RuntimeError("simulated neo4j failure")),
    ):
        task = HorizonAdjudicatorTask()
        result = await task.execute()

    assert result.success is False
    assert result.errors == 1
    assert "neo4j failure" in result.details.get("error", "").lower() or \
           "user enumeration" in result.details.get("error", "").lower()
