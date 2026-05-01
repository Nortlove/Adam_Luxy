"""Pin mSPRT outcome aggregation cypher (directive Section 8.3 line 913).

Tests pin:
  * Soft-fail without driver → zero-batch
  * Empty / inverted window → zero-batch
  * Cypher exception → zero-batch (logged, never raised)
  * Bilateral arm + positive outcome → treatment_sum incremented
  * Control arm + positive outcome → control_sum incremented
  * Bilateral arm + zero outcome → treatment_n only (sum unchanged)
  * Bilateral arm + missing outcome (NULL from OPTIONAL MATCH) → zero
  * Arm resolution: dc.treatment_arm property preferred over metadata
  * Arm resolution: metadata_json fallback when property None
  * Arm resolution: bad metadata_json JSON → "bilateral" default
  * Arm resolution: missing both → "bilateral" default
  * Unknown arm value → counted as treatment by convention
  * Multiple rows aggregate correctly
  * Cypher schema parameter contract pinned
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from adam.intelligence.msprt_campaign_monitor import ObservationBatch
from adam.intelligence.msprt_outcome_aggregation import (
    _resolve_arm,
    aggregate_outcomes_for_window,
)


# -----------------------------------------------------------------------------
# Fake async Neo4j driver
# -----------------------------------------------------------------------------


class _FakeRecord:
    def __init__(self, data: Dict[str, Any]) -> None:
        self._data = data

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)


class _FakeAsyncResult:
    def __init__(self, rows: List[Dict[str, Any]]) -> None:
        self._rows = list(rows)

    def __aiter__(self):
        async def _gen():
            for r in self._rows:
                yield _FakeRecord(r)
        return _gen()


class _FakeAsyncSession:
    def __init__(self, driver: "FakeAsyncNeo4jDriver") -> None:
        self._driver = driver

    async def __aenter__(self) -> "_FakeAsyncSession":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def run(self, cypher: str, **params: Any) -> _FakeAsyncResult:
        self._driver.calls.append((cypher, dict(params)))
        if self._driver.fail_next_run:
            self._driver.fail_next_run = False
            raise RuntimeError("simulated cypher failure")
        return _FakeAsyncResult(self._driver.next_rows)


class FakeAsyncNeo4jDriver:
    def __init__(self) -> None:
        self.next_rows: List[Dict[str, Any]] = []
        self.calls: List = []
        self.fail_next_run: bool = False

    def session(self) -> _FakeAsyncSession:
        return _FakeAsyncSession(self)


# -----------------------------------------------------------------------------
# _resolve_arm — arm resolution priority
# -----------------------------------------------------------------------------


def test_resolve_arm_prefers_property_over_metadata():
    """When dc.treatment_arm property is set, ignore metadata_json."""
    arm = _resolve_arm(
        arm_property="control",
        metadata_json='{"treatment_arm": "bilateral"}',
    )
    assert arm == "control"


def test_resolve_arm_falls_back_to_metadata_when_property_none():
    arm = _resolve_arm(
        arm_property=None,
        metadata_json='{"treatment_arm": "control"}',
    )
    assert arm == "control"


def test_resolve_arm_falls_back_to_metadata_when_property_empty():
    arm = _resolve_arm(
        arm_property="",
        metadata_json='{"treatment_arm": "control"}',
    )
    assert arm == "control"


def test_resolve_arm_default_when_metadata_json_missing():
    assert _resolve_arm(arm_property=None, metadata_json=None) == "bilateral"


def test_resolve_arm_default_when_metadata_json_invalid():
    assert _resolve_arm(
        arm_property=None, metadata_json="not-valid-json",
    ) == "bilateral"


def test_resolve_arm_default_when_metadata_lacks_treatment_arm_key():
    assert _resolve_arm(
        arm_property=None, metadata_json='{"other_key": "value"}',
    ) == "bilateral"


def test_resolve_arm_metadata_treatment_arm_empty_string_uses_default():
    assert _resolve_arm(
        arm_property=None, metadata_json='{"treatment_arm": ""}',
    ) == "bilateral"


# -----------------------------------------------------------------------------
# Soft-fail paths
# -----------------------------------------------------------------------------


async def test_aggregate_no_driver_returns_zero():
    batch = await aggregate_outcomes_for_window(
        driver=None, since_ts=0.0, until_ts=100.0,
    )
    assert batch.treatment_n == 0
    assert batch.control_n == 0
    assert batch.treatment_sum == 0.0
    assert batch.control_sum == 0.0


async def test_aggregate_empty_window_returns_zero():
    """since_ts >= until_ts → empty window, no cypher call."""
    driver = FakeAsyncNeo4jDriver()
    batch = await aggregate_outcomes_for_window(
        driver=driver, since_ts=100.0, until_ts=100.0,
    )
    assert batch.treatment_n == 0
    assert batch.control_n == 0
    # No cypher call should have been issued
    assert len(driver.calls) == 0


async def test_aggregate_inverted_window_returns_zero():
    driver = FakeAsyncNeo4jDriver()
    batch = await aggregate_outcomes_for_window(
        driver=driver, since_ts=200.0, until_ts=100.0,
    )
    assert batch.treatment_n == 0
    assert len(driver.calls) == 0


async def test_aggregate_cypher_failure_returns_zero():
    driver = FakeAsyncNeo4jDriver()
    driver.fail_next_run = True
    batch = await aggregate_outcomes_for_window(
        driver=driver, since_ts=0.0, until_ts=100.0,
    )
    assert batch.treatment_n == 0
    assert batch.control_n == 0


# -----------------------------------------------------------------------------
# Aggregation correctness
# -----------------------------------------------------------------------------


async def test_aggregate_bilateral_arm_positive_outcome_increments_treatment():
    driver = FakeAsyncNeo4jDriver()
    driver.next_rows = [
        {
            "arm_property": "bilateral",
            "metadata_json": None,
            "outcome_value": 1.0,
        },
    ]
    batch = await aggregate_outcomes_for_window(driver, 0.0, 100.0)
    assert batch.treatment_n == 1
    assert batch.treatment_sum == 1.0
    assert batch.control_n == 0
    assert batch.control_sum == 0.0


async def test_aggregate_control_arm_positive_outcome_increments_control():
    driver = FakeAsyncNeo4jDriver()
    driver.next_rows = [
        {
            "arm_property": "control",
            "metadata_json": None,
            "outcome_value": 1.0,
        },
    ]
    batch = await aggregate_outcomes_for_window(driver, 0.0, 100.0)
    assert batch.treatment_n == 0
    assert batch.control_n == 1
    assert batch.control_sum == 1.0


async def test_aggregate_zero_outcome_counts_n_but_not_sum():
    """Bernoulli collapse: outcome_value=0 → counted in n, not in sum."""
    driver = FakeAsyncNeo4jDriver()
    driver.next_rows = [
        {
            "arm_property": "bilateral",
            "metadata_json": None,
            "outcome_value": 0.0,
        },
    ]
    batch = await aggregate_outcomes_for_window(driver, 0.0, 100.0)
    assert batch.treatment_n == 1
    assert batch.treatment_sum == 0.0


async def test_aggregate_missing_outcome_treated_as_zero():
    """OPTIONAL MATCH returns NULL outcome_value when no AdOutcome.
    coalesce in cypher → 0.0; aggregator counts as no conversion."""
    driver = FakeAsyncNeo4jDriver()
    driver.next_rows = [
        {
            "arm_property": "bilateral",
            "metadata_json": None,
            "outcome_value": None,  # NULL from OPTIONAL MATCH
        },
    ]
    batch = await aggregate_outcomes_for_window(driver, 0.0, 100.0)
    assert batch.treatment_n == 1
    assert batch.treatment_sum == 0.0


async def test_aggregate_bernoulli_collapses_value_above_zero():
    """outcome_value > 0 → 1 (Bernoulli). Specific value doesn't matter."""
    driver = FakeAsyncNeo4jDriver()
    driver.next_rows = [
        {
            "arm_property": "bilateral",
            "metadata_json": None,
            "outcome_value": 0.5,  # any positive
        },
        {
            "arm_property": "bilateral",
            "metadata_json": None,
            "outcome_value": 100.0,
        },
    ]
    batch = await aggregate_outcomes_for_window(driver, 0.0, 100.0)
    assert batch.treatment_n == 2
    assert batch.treatment_sum == 2.0  # both → 1


async def test_aggregate_unknown_arm_counted_as_treatment():
    """An unrecognized arm value (not 'control') → treatment by
    convention (default bilateral pool)."""
    driver = FakeAsyncNeo4jDriver()
    driver.next_rows = [
        {
            "arm_property": "weird_arm_value",
            "metadata_json": None,
            "outcome_value": 1.0,
        },
    ]
    batch = await aggregate_outcomes_for_window(driver, 0.0, 100.0)
    assert batch.treatment_n == 1
    assert batch.control_n == 0


async def test_aggregate_metadata_json_fallback():
    """When dc.treatment_arm property is None, fallback to metadata_json."""
    driver = FakeAsyncNeo4jDriver()
    driver.next_rows = [
        {
            "arm_property": None,
            "metadata_json": '{"treatment_arm": "control"}',
            "outcome_value": 1.0,
        },
    ]
    batch = await aggregate_outcomes_for_window(driver, 0.0, 100.0)
    assert batch.control_n == 1
    assert batch.treatment_n == 0


async def test_aggregate_mixed_arms_partition_correctly():
    driver = FakeAsyncNeo4jDriver()
    driver.next_rows = [
        # 3 bilateral, 1 conversion
        {"arm_property": "bilateral", "metadata_json": None, "outcome_value": 1.0},
        {"arm_property": "bilateral", "metadata_json": None, "outcome_value": 0.0},
        {"arm_property": "bilateral", "metadata_json": None, "outcome_value": 0.0},
        # 2 control, 0 conversions
        {"arm_property": "control", "metadata_json": None, "outcome_value": 0.0},
        {"arm_property": "control", "metadata_json": None, "outcome_value": 0.0},
    ]
    batch = await aggregate_outcomes_for_window(driver, 0.0, 100.0)
    assert batch.treatment_n == 3
    assert batch.treatment_sum == 1.0
    assert batch.control_n == 2
    assert batch.control_sum == 0.0


async def test_aggregate_returns_observation_batch_type():
    """Output is exactly the type step_campaign_monitor expects."""
    driver = FakeAsyncNeo4jDriver()
    driver.next_rows = []
    batch = await aggregate_outcomes_for_window(driver, 0.0, 100.0)
    assert isinstance(batch, ObservationBatch)


# -----------------------------------------------------------------------------
# Cypher contract
# -----------------------------------------------------------------------------


async def test_aggregate_cypher_param_contract():
    """Cypher receives since_ts + until_ts as floats. Schema drift
    breaks this test loudly."""
    driver = FakeAsyncNeo4jDriver()
    driver.next_rows = []
    await aggregate_outcomes_for_window(
        driver, since_ts=1700000000.0, until_ts=1700086400.0,
    )
    assert len(driver.calls) == 1
    cypher, params = driver.calls[0]
    assert "since_ts" in params
    assert "until_ts" in params
    assert isinstance(params["since_ts"], float)
    assert isinstance(params["until_ts"], float)
    # Schema discipline: cypher mentions DecisionContext + AdOutcome
    assert "DecisionContext" in cypher
    assert "AdOutcome" in cypher
    assert "HAD_OUTCOME" in cypher
