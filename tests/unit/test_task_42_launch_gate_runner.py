"""Pin Task 42 — daily launch-gate runner (consumer side of Slice 8).

The task snapshots producer counters (red_criteria_snapshot), pulls
sapid round-trip rate from the monitor singleton, runs
``run_launch_gate_evaluation``, and persists a :LaunchGateResult
node for trending. This test pins:

    * Task name + schedule (05:00 UTC daily)
    * Cold-start (zero bids in window) succeeds with skipped checks
    * When data exists, gate runs and triggered_criteria surface
    * Snapshot Cypher idempotent on (date, schedule_hour)
    * Task registered in the scheduler
    * Cascade source-text wire pins for the producer increments
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adam.intelligence.daily.task_42_launch_gate_runner import (
    LaunchGateRunnerTask,
)


# -----------------------------------------------------------------------------
# Schedule contract + registration
# -----------------------------------------------------------------------------


def test_task_name():
    task = LaunchGateRunnerTask()
    assert task.name == "launch_gate_runner"


def test_schedule_05_utc_daily():
    """05:00 UTC — after Task 41 (04:00) + Task 40 (03:00)."""
    task = LaunchGateRunnerTask()
    assert task.schedule_hours == [5]
    assert task.frequency_hours == 24


def test_task_registered_in_scheduler():
    from adam.intelligence.daily.scheduler import (
        _register_all_tasks,
        get_task_registry,
    )
    _register_all_tasks()
    registry = get_task_registry()
    assert "launch_gate_runner" in registry


# -----------------------------------------------------------------------------
# Cold-start path — zero bids in window
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cold_start_succeeds_with_skipped_checks():
    """Zero bids → runner skips most checks (no data); task succeeds.

    Resets BOTH the snapshot accumulator (Slice 8 producer) AND the
    sapid round-trip monitor singleton (Phase 8 producer) so this
    test runs cleanly in any ordering. Cross-test singleton state
    pollution from sapid-test ordering would otherwise trigger the
    sapid criterion in cold-start.
    """
    from adam.intelligence.red_criteria_snapshot import reset_for_tests
    from adam.intelligence.spine.phase_8_stackadapt_integration import (
        reset_default_monitor,
    )
    reset_for_tests()
    reset_default_monitor()

    task = LaunchGateRunnerTask()

    with patch(
        "adam.core.dependencies.get_infrastructure",
        new=AsyncMock(return_value=MagicMock(neo4j_driver=None, neo4j=None)),
    ):
        result = await task.execute()

    assert result.success is True
    # No data → gate runs but appends 0 checks
    assert result.details.get("any_triggered") is False
    assert result.details.get("n_checks_evaluated", -1) >= 0


# -----------------------------------------------------------------------------
# Happy path — data flows through
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_happy_path_data_flows_through_runner():
    """Snapshot has bids + violations → runner computes + surfaces."""
    from adam.intelligence.red_criteria_snapshot import (
        get_red_snapshot,
        reset_for_tests,
    )
    reset_for_tests()
    snap = get_red_snapshot()
    # Simulate a healthy day: 1000 bids, 990 traces (99%), 10 violations
    for _ in range(1000):
        snap.record_bid()
    for _ in range(990):
        snap.record_trace_emission()
    snap.record_floor_violation(10)
    snap.record_latency_ms(50.0)

    task = LaunchGateRunnerTask()

    with patch(
        "adam.core.dependencies.get_infrastructure",
        new=AsyncMock(return_value=MagicMock(neo4j_driver=None, neo4j=None)),
    ):
        result = await task.execute()

    assert result.success is True
    snap_out = result.details["snapshot"]
    assert snap_out["n_bids"] == 1000
    assert snap_out["n_traces_emitted"] == 990
    assert snap_out["n_floor_violations"] == 10
    # Gate evaluated multiple checks
    assert result.details["n_checks_evaluated"] >= 2
    # 1% violation rate < 5% threshold + 99% emission rate ≥ 99% →
    # neither fluency nor emission criteria trigger
    assert "fluency_floor_violation" not in result.details["triggered_criteria"]


@pytest.mark.asyncio
async def test_high_violation_rate_triggers_gate():
    """Violation rate > 5% → criterion triggers."""
    from adam.intelligence.red_criteria_snapshot import (
        get_red_snapshot,
        reset_for_tests,
    )
    reset_for_tests()
    snap = get_red_snapshot()
    # 100 bids, 20 violations (20% rate, well above 5% threshold)
    for _ in range(100):
        snap.record_bid()
    snap.record_floor_violation(20)

    task = LaunchGateRunnerTask()

    with patch(
        "adam.core.dependencies.get_infrastructure",
        new=AsyncMock(return_value=MagicMock(neo4j_driver=None, neo4j=None)),
    ):
        result = await task.execute()

    assert result.success is True
    assert result.details["any_triggered"] is True
    # The triggered_criteria string includes "fluency" — exact format
    # is REDCriterion enum's __str__
    triggered = result.details["triggered_criteria"]
    assert any("fluency" in c.lower() for c in triggered)


# -----------------------------------------------------------------------------
# Snapshot Cypher
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_snapshot_cypher_uses_idempotent_merge():
    """Snapshot Cypher MERGEs on (date, schedule_hour)."""
    from adam.intelligence.red_criteria_snapshot import (
        get_red_snapshot,
        reset_for_tests,
    )
    reset_for_tests()
    snap = get_red_snapshot()
    snap.record_bid()
    snap.record_trace_emission()

    captured_queries = []

    def _capture_run(query, **kwargs):
        captured_queries.append(query)
        return MagicMock()

    fake_session = MagicMock()
    fake_session.run = _capture_run
    fake_session_cm = MagicMock()
    fake_session_cm.__enter__ = MagicMock(return_value=fake_session)
    fake_session_cm.__exit__ = MagicMock(return_value=None)
    fake_driver = MagicMock()
    fake_driver.session = MagicMock(return_value=fake_session_cm)

    fake_infra = MagicMock(neo4j_driver=fake_driver, neo4j=fake_driver)

    task = LaunchGateRunnerTask()
    with patch(
        "adam.core.dependencies.get_infrastructure",
        new=AsyncMock(return_value=fake_infra),
    ):
        result = await task.execute()

    assert result.success is True
    assert result.items_stored == 1
    assert len(captured_queries) == 1
    q = captured_queries[0]
    assert "MERGE" in q
    assert "LaunchGateResult" in q
    assert "date" in q
    assert "schedule_hour" in q


# -----------------------------------------------------------------------------
# Cascade source-text wire pins
# -----------------------------------------------------------------------------


def test_cascade_records_bid_at_entry():
    """Cascade source must call record_bid() at entry."""
    from pathlib import Path

    src = Path("adam/api/stackadapt/bilateral_cascade.py").read_text()
    assert "record_bid()" in src, (
        "Cascade no longer calls record_bid at entry — n_bids "
        "denominator for emission rate / floor violation rate lost."
    )


def test_cascade_records_trace_emission():
    """Cascade source must call record_trace_emission after emit."""
    from pathlib import Path

    src = Path("adam/api/stackadapt/bilateral_cascade.py").read_text()
    assert "record_trace_emission()" in src


def test_cascade_records_latency_ms():
    """Cascade source must call record_latency_ms after elapsed_ms."""
    from pathlib import Path

    src = Path("adam/api/stackadapt/bilateral_cascade.py").read_text()
    assert "record_latency_ms(elapsed_ms)" in src


def test_cascade_records_floor_violation_count():
    """Cascade fluency-floor block must call record_floor_violation
    when n_dropped > 0 (Slice 1 + Slice 8 composition)."""
    from pathlib import Path

    src = Path("adam/api/stackadapt/bilateral_cascade.py").read_text()
    assert "record_floor_violation(" in src
