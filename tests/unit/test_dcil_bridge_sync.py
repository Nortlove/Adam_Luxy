"""Pin the refactored dcil_bridge sync + the daily task that invokes it.

Discipline anchors:
    - Each directive gets inserted under ITS OWN campaign_id (not under
      a single campaign_id passed as a parameter). The previous
      function signature was a bug — re-running per-campaign would have
      duplicated each directive once per campaign.
    - Idempotency: re-running the sync skips already-persisted
      directives via id-match on directive_id. Daily scheduler can
      re-fire safely.
    - FK gate: directives targeting a campaign_id absent from
      management.campaigns are skipped (not FK-violating mid-batch).
      Counts surfaced for log visibility.
"""

from __future__ import annotations

from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from adam.api.admin.services.dcil_bridge import sync_directives_to_postgres


def _validated_directive(
    directive_id: str,
    campaign_id: str,
    directive_type: str = "budget_reallocation",
    status: str = "approved",
):
    """A representative validated-directive dict shape (matches what
    task_29 _store_validated_directives writes)."""
    return {
        "directive_id": directive_id,
        "type": directive_type,
        "status": status,
        "campaign_id": campaign_id,
        "archetype": "careful_truster",
        "parameter": "daily_budget",
        "proposed_value": 600,
        "rationale": "High-retention archetype showing increased capacity for spend",
        "blocked_reason": None,
        "confidence": 0.78,
    }


# -----------------------------------------------------------------------------
# Per-directive campaign_id — pin the bug-fix
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_each_directive_inserted_under_its_own_campaign_id():
    """Bug-fix regression: prior version of sync_directives_to_postgres
    took a campaign_id parameter and inserted ALL directives under that
    one id. This test pins that each directive lands in
    dcil_directives with ITS OWN campaign_id from the directive blob."""
    payload = {
        "directives": [
            _validated_directive("dir_A", "campaign_X"),
            _validated_directive("dir_B", "campaign_Y"),
            _validated_directive("dir_C", "campaign_X"),
        ]
    }

    db = MagicMock()
    db.fetch_all = AsyncMock(return_value=[
        {"id": "campaign_X"}, {"id": "campaign_Y"},
    ])
    db.fetch_one = AsyncMock(return_value=None)  # No directives already exist
    db.execute = AsyncMock()

    with patch(
        "adam.api.admin.services.dcil_bridge.get_db", return_value=db,
    ), patch(
        "adam.api.admin.services.dcil_bridge._load_from_redis_or_memory",
        return_value=payload,
    ):
        counts = await sync_directives_to_postgres()

    # All three directives synced (each to their stated campaign_id)
    assert counts["synced"] == 3
    assert counts["skipped_existing"] == 0
    assert counts["skipped_no_campaign"] == 0

    # Verify each insert call carried the right (directive_id, campaign_id) pair
    insert_calls = db.execute.await_args_list
    assert len(insert_calls) == 3

    # The first two positional args after the SQL string are id + campaign_id
    pairs_inserted = {(call.args[1], call.args[2]) for call in insert_calls}
    assert ("dir_A", "campaign_X") in pairs_inserted
    assert ("dir_B", "campaign_Y") in pairs_inserted
    assert ("dir_C", "campaign_X") in pairs_inserted


# -----------------------------------------------------------------------------
# Idempotency — re-running the sync is a no-op on already-persisted directives
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_already_persisted_directives_are_skipped():
    """Sync must use directive_id from the blob (NOT a fresh uuid) so
    re-runs match the existing primary key and skip via id-lookup."""
    payload = {
        "directives": [
            _validated_directive("dir_existing", "campaign_X"),
            _validated_directive("dir_new", "campaign_X"),
        ]
    }

    db = MagicMock()
    db.fetch_all = AsyncMock(return_value=[{"id": "campaign_X"}])
    # First check: dir_existing exists (returns row); second: dir_new doesn't (returns None)
    db.fetch_one = AsyncMock(side_effect=[{"id": "dir_existing"}, None])
    db.execute = AsyncMock()

    with patch(
        "adam.api.admin.services.dcil_bridge.get_db", return_value=db,
    ), patch(
        "adam.api.admin.services.dcil_bridge._load_from_redis_or_memory",
        return_value=payload,
    ):
        counts = await sync_directives_to_postgres()

    assert counts["synced"] == 1
    assert counts["skipped_existing"] == 1
    # Only one INSERT (for dir_new); dir_existing skipped via id-match
    assert db.execute.await_count == 1
    assert db.execute.await_args.args[1] == "dir_new"


# -----------------------------------------------------------------------------
# FK gate — directive targeting unknown campaign skipped, not FK-violating
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_directive_targeting_unknown_campaign_skipped():
    """A directive whose campaign_id is absent from management.campaigns
    must be skipped (counted in skipped_no_campaign), not propagated
    into an INSERT that would violate the FK constraint."""
    payload = {
        "directives": [
            _validated_directive("dir_orphan", "campaign_unmirrored"),
            _validated_directive("dir_valid", "campaign_X"),
        ]
    }

    db = MagicMock()
    db.fetch_all = AsyncMock(return_value=[{"id": "campaign_X"}])  # campaign_unmirrored absent
    db.fetch_one = AsyncMock(return_value=None)
    db.execute = AsyncMock()

    with patch(
        "adam.api.admin.services.dcil_bridge.get_db", return_value=db,
    ), patch(
        "adam.api.admin.services.dcil_bridge._load_from_redis_or_memory",
        return_value=payload,
    ):
        counts = await sync_directives_to_postgres()

    assert counts["synced"] == 1
    assert counts["skipped_no_campaign"] == 1
    assert db.execute.await_count == 1
    assert db.execute.await_args.args[1] == "dir_valid"


# -----------------------------------------------------------------------------
# Empty-Redis case — no validated_directives → empty counts, no errors
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_redis_returns_zero_counts_no_errors():
    """No validated_directives blob in Redis → soft-fail with zero
    counts (not an exception)."""
    db = MagicMock()
    db.fetch_all = AsyncMock(return_value=[])
    db.fetch_one = AsyncMock()
    db.execute = AsyncMock()

    with patch(
        "adam.api.admin.services.dcil_bridge.get_db", return_value=db,
    ), patch(
        "adam.api.admin.services.dcil_bridge._load_from_redis_or_memory",
        return_value=None,
    ):
        counts = await sync_directives_to_postgres()

    assert counts == {
        "synced": 0,
        "skipped_existing": 0,
        "skipped_no_campaign": 0,
        "failed": 0,
    }
    db.execute.assert_not_called()


# -----------------------------------------------------------------------------
# Insert failure — counted in failed, doesn't propagate
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_insert_failure_counted_does_not_propagate():
    """A single insert failure (e.g., transient DB error) is counted in
    `failed`; sync continues with subsequent directives."""
    payload = {
        "directives": [
            _validated_directive("dir_fail", "campaign_X"),
            _validated_directive("dir_ok", "campaign_X"),
        ]
    }

    db = MagicMock()
    db.fetch_all = AsyncMock(return_value=[{"id": "campaign_X"}])
    db.fetch_one = AsyncMock(return_value=None)
    db.execute = AsyncMock(side_effect=[RuntimeError("simulated"), None])

    with patch(
        "adam.api.admin.services.dcil_bridge.get_db", return_value=db,
    ), patch(
        "adam.api.admin.services.dcil_bridge._load_from_redis_or_memory",
        return_value=payload,
    ):
        counts = await sync_directives_to_postgres()

    assert counts["synced"] == 1
    assert counts["failed"] == 1


# -----------------------------------------------------------------------------
# DCILBridgeSyncTask — daily-task wrapper
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dcil_bridge_sync_task_returns_counts_in_details():
    """The TaskResult `details` dict carries the bridge's counts so
    operators can see synced/skipped/failed counts in the daily log."""
    from adam.intelligence.daily.task_29_5_dcil_bridge_sync import DCILBridgeSyncTask

    fake_counts = {
        "synced": 3, "skipped_existing": 7, "skipped_no_campaign": 1, "failed": 0,
    }

    with patch(
        "adam.api.admin.services.dcil_bridge.sync_directives_to_postgres",
        new=AsyncMock(return_value=fake_counts),
    ):
        task = DCILBridgeSyncTask()
        result = await task.execute()

    assert result.success is True
    assert result.items_stored == 3
    assert result.items_processed == 11  # 3 + 7 + 1 + 0
    assert result.details == fake_counts


@pytest.mark.asyncio
async def test_dcil_bridge_sync_task_soft_fails_on_exception():
    """An exception inside sync_directives_to_postgres is caught, the
    TaskResult flags failure, and the daily pipeline continues."""
    from adam.intelligence.daily.task_29_5_dcil_bridge_sync import DCILBridgeSyncTask

    with patch(
        "adam.api.admin.services.dcil_bridge.sync_directives_to_postgres",
        new=AsyncMock(side_effect=RuntimeError("simulated")),
    ):
        task = DCILBridgeSyncTask()
        result = await task.execute()

    assert result.success is False
    assert result.errors == 1
    assert "simulated" in (result.details.get("error") or "")
