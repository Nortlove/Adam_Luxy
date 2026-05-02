"""Pin Task 41 — daily OPE estimator (consumer side of Slice 6).

The task runs IPS / SNIPS / DR estimators on
:DecisionContext-[:HAD_OUTCOME]->:AdOutcome rows and persists daily
:OPEDailyEstimate snapshots. This test pins:

    * Task name + schedule (04:00 UTC daily)
    * No-driver path returns skipped (not failure)
    * No-samples path returns success with outcome="no_samples"
      (cold-start, not failure)
    * Estimates surface on result.details when samples exist
    * Snapshot Cypher idempotent on (date, lookback_days)
    * Task registered in the scheduler

Honest tag: policy_gate firing on a CANDIDATE policy is sibling
slice (requires CI/CD path that promotes a candidate distinct from
the cascade); v0.1 task computes ONLY the current-policy estimate.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adam.intelligence.daily.task_41_ope_daily_estimator import (
    OPEDailyEstimatorTask,
)


# -----------------------------------------------------------------------------
# Schedule contract
# -----------------------------------------------------------------------------


def test_task_name():
    task = OPEDailyEstimatorTask()
    assert task.name == "ope_daily_estimator"


def test_schedule_04_utc_daily():
    """04:00 UTC — after Task 40 (03:00) so dual-eval re-warm is fresh."""
    task = OPEDailyEstimatorTask()
    assert task.schedule_hours == [4]
    assert task.frequency_hours == 24


def test_task_registered_in_scheduler():
    """Task 41 must be in the scheduler's registered set."""
    from adam.intelligence.daily.scheduler import (
        _register_all_tasks,
        get_task_registry,
    )
    _register_all_tasks()
    registry = get_task_registry()
    assert "ope_daily_estimator" in registry


# -----------------------------------------------------------------------------
# Soft-fail paths
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_driver_skipped():
    """No driver → result.success=True with details["skipped"]=no_neo4j_driver."""
    task = OPEDailyEstimatorTask()
    with patch(
        "adam.core.dependencies.get_infrastructure",
        new=AsyncMock(return_value=MagicMock(neo4j_driver=None, neo4j=None)),
    ):
        result = await task.execute()
    assert result.success is True
    assert result.details.get("skipped") == "no_neo4j_driver"


@pytest.mark.asyncio
async def test_no_samples_succeeds_with_cold_start_outcome():
    """Empty sample list → success with outcome=no_samples (not failure)."""
    task = OPEDailyEstimatorTask()
    fake_driver = MagicMock()

    fake_infra = MagicMock(neo4j_driver=fake_driver, neo4j=fake_driver)

    with patch(
        "adam.core.dependencies.get_infrastructure",
        new=AsyncMock(return_value=fake_infra),
    ), patch(
        "adam.intelligence.ope.load_ope_samples_from_neo4j",
        return_value=[],
    ):
        result = await task.execute()

    assert result.success is True
    assert result.details.get("outcome") == "no_samples"
    assert result.details.get("n_samples") == 0


# -----------------------------------------------------------------------------
# Happy path — estimates computed and surfaced
# -----------------------------------------------------------------------------


def _make_sample(action="social_proof", reward=1.0, propensity=0.5):
    from adam.intelligence.ope import OPESample
    return OPESample(
        context={"archetype": "achiever"},
        action=action,
        reward=reward,
        propensity=propensity,
        pscore_known=True,
        decision_id=f"dec_{action}_{reward}",
    )


@pytest.mark.asyncio
async def test_estimates_computed_and_surfaced():
    """When samples exist, IPS/SNIPS/DR are computed and surfaced."""
    task = OPEDailyEstimatorTask()
    fake_driver = MagicMock()

    # Mock session for snapshot write
    fake_session = MagicMock()
    fake_session.run = MagicMock()
    fake_session_cm = MagicMock()
    fake_session_cm.__enter__ = MagicMock(return_value=fake_session)
    fake_session_cm.__exit__ = MagicMock(return_value=None)
    fake_driver.session = MagicMock(return_value=fake_session_cm)

    samples = [
        _make_sample("social_proof", 1.0, 0.5),
        _make_sample("scarcity", 0.0, 0.5),
        _make_sample("social_proof", 1.0, 0.5),
    ]

    fake_infra = MagicMock(neo4j_driver=fake_driver, neo4j=fake_driver)

    with patch(
        "adam.core.dependencies.get_infrastructure",
        new=AsyncMock(return_value=fake_infra),
    ), patch(
        "adam.intelligence.ope.load_ope_samples_from_neo4j",
        return_value=samples,
    ):
        result = await task.execute()

    assert result.success is True
    assert result.details.get("outcome") == "computed"
    assert result.details.get("n_samples") == 3
    assert "ips_point" in result.details
    assert "snips_point" in result.details
    assert "dr_point" in result.details


@pytest.mark.asyncio
async def test_snapshot_cypher_uses_idempotent_merge():
    """Snapshot Cypher must MERGE on (date, lookback_days) for idempotency."""
    task = OPEDailyEstimatorTask()
    fake_driver = MagicMock()

    captured_queries = []

    def _capture_run(query, **kwargs):
        captured_queries.append(query)
        return MagicMock()

    fake_session = MagicMock()
    fake_session.run = _capture_run
    fake_session_cm = MagicMock()
    fake_session_cm.__enter__ = MagicMock(return_value=fake_session)
    fake_session_cm.__exit__ = MagicMock(return_value=None)
    fake_driver.session = MagicMock(return_value=fake_session_cm)

    samples = [_make_sample()]

    fake_infra = MagicMock(neo4j_driver=fake_driver, neo4j=fake_driver)

    with patch(
        "adam.core.dependencies.get_infrastructure",
        new=AsyncMock(return_value=fake_infra),
    ), patch(
        "adam.intelligence.ope.load_ope_samples_from_neo4j",
        return_value=samples,
    ):
        await task.execute()

    assert len(captured_queries) == 1
    q = captured_queries[0]
    assert "MERGE" in q
    assert "OPEDailyEstimate" in q
    assert "date" in q
    assert "lookback_days" in q


# -----------------------------------------------------------------------------
# Outcome handler wire pin
# -----------------------------------------------------------------------------


def test_outcome_handler_imports_ad_outcome_writer():
    """OutcomeHandler must reference write_ad_outcome (Slice 6 producer wire)."""
    from pathlib import Path

    src = Path("adam/core/learning/outcome_handler.py").read_text()
    assert (
        "from adam.intelligence.ad_outcome_persist import"
        in src
    ), (
        "OutcomeHandler lost its import of write_ad_outcome. "
        "Slice 6 producer wire is broken — :AdOutcome rows will not "
        "be written; OPE daily estimator will see no data."
    )
    assert "write_ad_outcome" in src
