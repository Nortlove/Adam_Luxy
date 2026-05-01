"""Pin Task 39 — mSPRT campaign monitor scheduler hookup.

Tests pin:
  * Task name + schedule (7 AM UTC, daily)
  * Registration in scheduler registry
  * execute() pipeline: aggregate → step → log state
  * Skipped on no_driver
  * Skipped on no_observations (zero batch from aggregation)
  * Failed on aggregate exception
  * Failed on step exception
  * RED-criterion detection logged + surfaced in result.details
  * Result counters populated (items_processed, batch_*, decision)
  * Default campaign_id from env var fallback
  * Custom campaign_id via env override
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest

from adam.intelligence.daily.task_39_msprt_campaign_monitor import (
    DEFAULT_PILOT_CAMPAIGN_ID,
    WINDOW_SECONDS,
    MSPRTCampaignMonitorTask,
)
from adam.intelligence.msprt_campaign_monitor import (
    MSPRTCampaignState,
    ObservationBatch,
)
from adam.intelligence.spine.phase_9_pre_launch import MSPRTDecision


# -----------------------------------------------------------------------------
# Schedule + identity pinned
# -----------------------------------------------------------------------------


def test_task_name_pinned():
    task = MSPRTCampaignMonitorTask()
    assert task.name == "msprt_campaign_monitor"


def test_task_schedule_is_seven_am_utc_daily():
    task = MSPRTCampaignMonitorTask()
    assert task.schedule_hours == [7]
    assert task.frequency_hours == 24


def test_window_seconds_is_24_hours():
    """Window must match daily cadence."""
    assert WINDOW_SECONDS == 24 * 3600


def test_default_campaign_id_pinned():
    assert DEFAULT_PILOT_CAMPAIGN_ID == "luxy_pilot"


# -----------------------------------------------------------------------------
# Registration in scheduler
# -----------------------------------------------------------------------------


def test_task_39_registers_in_scheduler():
    """Task 39 MUST appear in the scheduler registry under
    'msprt_campaign_monitor'."""
    import adam.intelligence.daily.scheduler as scheduler_mod
    scheduler_mod._task_registry.clear()
    registry = scheduler_mod.get_task_registry()
    assert "msprt_campaign_monitor" in registry


# -----------------------------------------------------------------------------
# Fake infrastructure
# -----------------------------------------------------------------------------


class _FakeNeo4jDriver:
    """Minimal stand-in for the async Neo4j driver."""
    pass


class _FakeInfra:
    def __init__(self, neo4j_driver: Optional[Any] = None) -> None:
        self.neo4j = neo4j_driver


# -----------------------------------------------------------------------------
# execute() — happy path
# -----------------------------------------------------------------------------


async def test_execute_happy_path_calls_aggregate_and_step():
    driver = _FakeNeo4jDriver()
    infra = _FakeInfra(neo4j_driver=driver)

    aggregate_calls: List = []
    step_calls: List = []

    async def _fake_aggregate(driver, since_ts, until_ts):
        aggregate_calls.append((driver, since_ts, until_ts))
        return ObservationBatch(
            treatment_n=100, treatment_sum=10.0,
            control_n=100, control_sum=5.0,
        )

    async def _fake_step(config, batch, driver):
        step_calls.append((config, batch, driver))
        return MSPRTCampaignState(
            campaign_id=config.campaign_id,
            n_treatment=100, n_control=100,
            sum_treatment=10.0, sum_control=5.0,
            log_likelihood_ratio=2.0,
            decision=MSPRTDecision.CONTINUE.value,
            upper_boundary=2.77,
            lower_boundary=-1.56,
        )

    async def _fake_get_infra():
        return infra

    with patch(
        "adam.core.dependencies.get_infrastructure",
        side_effect=_fake_get_infra,
    ), patch(
        "adam.intelligence.msprt_outcome_aggregation.aggregate_outcomes_for_window",
        side_effect=_fake_aggregate,
    ), patch(
        "adam.intelligence.msprt_campaign_monitor.step_campaign_monitor",
        side_effect=_fake_step,
    ):
        task = MSPRTCampaignMonitorTask()
        result = await task.execute()

    assert result.success is True
    assert len(aggregate_calls) == 1
    assert len(step_calls) == 1
    # Aggregate received a 24h window
    _, since, until = aggregate_calls[0]
    assert (until - since) == pytest.approx(WINDOW_SECONDS, abs=1)
    # Step got the batch
    _, step_batch, _ = step_calls[0]
    assert step_batch.treatment_n == 100
    # Result counters populated
    assert result.items_processed == 200
    assert result.items_stored == 1
    assert result.details["decision"] == MSPRTDecision.CONTINUE.value
    assert result.details["log_likelihood_ratio"] == 2.0
    assert result.details["red_criterion_triggered"] is False


# -----------------------------------------------------------------------------
# Skip paths
# -----------------------------------------------------------------------------


async def test_execute_skipped_when_no_driver():
    """Driver unavailable → skipped with detail (not failed)."""
    infra = _FakeInfra(neo4j_driver=None)

    async def _fake_get_infra():
        return infra

    with patch(
        "adam.core.dependencies.get_infrastructure",
        side_effect=_fake_get_infra,
    ):
        task = MSPRTCampaignMonitorTask()
        result = await task.execute()

    assert result.success is True
    assert result.details["skipped"] == "no_driver"


async def test_execute_skipped_when_no_observations():
    """Aggregate returns zero batch → skipped, no mSPRT step taken
    (cumulative state unchanged, nothing to persist)."""
    driver = _FakeNeo4jDriver()
    infra = _FakeInfra(neo4j_driver=driver)

    async def _fake_aggregate(driver, since_ts, until_ts):
        return ObservationBatch(
            treatment_n=0, treatment_sum=0.0,
            control_n=0, control_sum=0.0,
        )

    async def _fake_get_infra():
        return infra

    step_called = []

    async def _fake_step(config, batch, driver):
        step_called.append(True)
        return MSPRTCampaignState(campaign_id=config.campaign_id)

    with patch(
        "adam.core.dependencies.get_infrastructure",
        side_effect=_fake_get_infra,
    ), patch(
        "adam.intelligence.msprt_outcome_aggregation.aggregate_outcomes_for_window",
        side_effect=_fake_aggregate,
    ), patch(
        "adam.intelligence.msprt_campaign_monitor.step_campaign_monitor",
        side_effect=_fake_step,
    ):
        task = MSPRTCampaignMonitorTask()
        result = await task.execute()

    assert result.success is True
    assert result.details["skipped"] == "no_observations"
    # mSPRT step NOT called when batch is empty
    assert step_called == []


# -----------------------------------------------------------------------------
# Failure paths
# -----------------------------------------------------------------------------


async def test_execute_fails_on_aggregate_exception():
    driver = _FakeNeo4jDriver()
    infra = _FakeInfra(neo4j_driver=driver)

    async def _raising_aggregate(driver, since_ts, until_ts):
        raise RuntimeError("simulated aggregation failure")

    async def _fake_get_infra():
        return infra

    with patch(
        "adam.core.dependencies.get_infrastructure",
        side_effect=_fake_get_infra,
    ), patch(
        "adam.intelligence.msprt_outcome_aggregation.aggregate_outcomes_for_window",
        side_effect=_raising_aggregate,
    ):
        task = MSPRTCampaignMonitorTask()
        result = await task.execute()

    assert result.success is False
    assert "aggregate_outcomes_for_window failed" in result.details["error"]


async def test_execute_fails_on_step_exception():
    driver = _FakeNeo4jDriver()
    infra = _FakeInfra(neo4j_driver=driver)

    async def _fake_aggregate(driver, since_ts, until_ts):
        return ObservationBatch(
            treatment_n=10, treatment_sum=1.0,
            control_n=10, control_sum=0.0,
        )

    async def _raising_step(config, batch, driver):
        raise RuntimeError("simulated step failure")

    async def _fake_get_infra():
        return infra

    with patch(
        "adam.core.dependencies.get_infrastructure",
        side_effect=_fake_get_infra,
    ), patch(
        "adam.intelligence.msprt_outcome_aggregation.aggregate_outcomes_for_window",
        side_effect=_fake_aggregate,
    ), patch(
        "adam.intelligence.msprt_campaign_monitor.step_campaign_monitor",
        side_effect=_raising_step,
    ):
        task = MSPRTCampaignMonitorTask()
        result = await task.execute()

    assert result.success is False
    assert "step_campaign_monitor failed" in result.details["error"]


# -----------------------------------------------------------------------------
# RED-criterion surfacing
# -----------------------------------------------------------------------------


async def test_execute_surfaces_red_criterion_in_details():
    """When ACCEPT_NULL → red_criterion_triggered=True in details."""
    driver = _FakeNeo4jDriver()
    infra = _FakeInfra(neo4j_driver=driver)

    async def _fake_aggregate(driver, since_ts, until_ts):
        return ObservationBatch(
            treatment_n=100, treatment_sum=5.0,  # Identical rates
            control_n=100, control_sum=5.0,
        )

    async def _fake_step(config, batch, driver):
        return MSPRTCampaignState(
            campaign_id=config.campaign_id,
            n_treatment=100, n_control=100,
            sum_treatment=5.0, sum_control=5.0,
            log_likelihood_ratio=-2.0,
            decision=MSPRTDecision.ACCEPT_NULL.value,
            upper_boundary=2.77,
            lower_boundary=-1.56,
        )

    async def _fake_get_infra():
        return infra

    with patch(
        "adam.core.dependencies.get_infrastructure",
        side_effect=_fake_get_infra,
    ), patch(
        "adam.intelligence.msprt_outcome_aggregation.aggregate_outcomes_for_window",
        side_effect=_fake_aggregate,
    ), patch(
        "adam.intelligence.msprt_campaign_monitor.step_campaign_monitor",
        side_effect=_fake_step,
    ):
        task = MSPRTCampaignMonitorTask()
        result = await task.execute()

    assert result.success is True
    assert result.details["red_criterion_triggered"] is True
    assert result.details["decision"] == MSPRTDecision.ACCEPT_NULL.value


# -----------------------------------------------------------------------------
# Campaign ID resolution
# -----------------------------------------------------------------------------


async def test_execute_default_campaign_id_when_env_unset(monkeypatch):
    """No env var → uses DEFAULT_PILOT_CAMPAIGN_ID."""
    monkeypatch.delenv("MSPRT_PILOT_CAMPAIGN_ID", raising=False)

    driver = _FakeNeo4jDriver()
    infra = _FakeInfra(neo4j_driver=driver)
    seen_campaign_ids: List[str] = []

    async def _fake_aggregate(driver, since_ts, until_ts):
        return ObservationBatch(
            treatment_n=10, treatment_sum=1.0,
            control_n=10, control_sum=0.0,
        )

    async def _fake_step(config, batch, driver):
        seen_campaign_ids.append(config.campaign_id)
        return MSPRTCampaignState(campaign_id=config.campaign_id)

    async def _fake_get_infra():
        return infra

    with patch(
        "adam.core.dependencies.get_infrastructure",
        side_effect=_fake_get_infra,
    ), patch(
        "adam.intelligence.msprt_outcome_aggregation.aggregate_outcomes_for_window",
        side_effect=_fake_aggregate,
    ), patch(
        "adam.intelligence.msprt_campaign_monitor.step_campaign_monitor",
        side_effect=_fake_step,
    ):
        task = MSPRTCampaignMonitorTask()
        await task.execute()

    assert seen_campaign_ids == [DEFAULT_PILOT_CAMPAIGN_ID]


async def test_execute_custom_campaign_id_via_env(monkeypatch):
    """MSPRT_PILOT_CAMPAIGN_ID env var overrides default."""
    monkeypatch.setenv("MSPRT_PILOT_CAMPAIGN_ID", "custom_campaign_xyz")

    driver = _FakeNeo4jDriver()
    infra = _FakeInfra(neo4j_driver=driver)
    seen_campaign_ids: List[str] = []

    async def _fake_aggregate(driver, since_ts, until_ts):
        return ObservationBatch(
            treatment_n=10, treatment_sum=1.0,
            control_n=10, control_sum=0.0,
        )

    async def _fake_step(config, batch, driver):
        seen_campaign_ids.append(config.campaign_id)
        return MSPRTCampaignState(campaign_id=config.campaign_id)

    async def _fake_get_infra():
        return infra

    with patch(
        "adam.core.dependencies.get_infrastructure",
        side_effect=_fake_get_infra,
    ), patch(
        "adam.intelligence.msprt_outcome_aggregation.aggregate_outcomes_for_window",
        side_effect=_fake_aggregate,
    ), patch(
        "adam.intelligence.msprt_campaign_monitor.step_campaign_monitor",
        side_effect=_fake_step,
    ):
        task = MSPRTCampaignMonitorTask()
        await task.execute()

    assert seen_campaign_ids == ["custom_campaign_xyz"]
