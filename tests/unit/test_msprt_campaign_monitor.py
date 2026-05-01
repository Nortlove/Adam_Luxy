"""Pin mSPRT campaign-level monitor (directive Section 8.3 line 913 + 8.4).

Tests pin:
  * State round-trip via fake async Neo4j driver.
  * Cumulative LLR grows correctly across multiple steps.
  * step_campaign_monitor with no prior state initializes correctly.
  * step_campaign_monitor accumulates over prior state.
  * Strong-signal accumulation eventually crosses upper boundary
    (REJECT_NULL — ADAM lifts).
  * Null accumulation eventually crosses lower boundary (ACCEPT_NULL
    — RED-criterion launch deferral).
  * Soft-fail without driver (in-memory step works, no persistence).
  * load returns None on missing campaign_id.
  * Campaign isolation: two campaigns don't cross-contaminate.
  * MERGE upsert on repeat persist (no duplicates).
  * is_red_criterion_triggered returns True iff decision = ACCEPT_NULL.
  * Cypher schema parameter contract pinned.
  * Constants pinned at A14 defaults.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from adam.intelligence.msprt_campaign_monitor import (
    DEFAULT_EXPECTED_LIFT,
    DEFAULT_NULL_BASELINE_RATE,
    MSPRTCampaignConfig,
    MSPRTCampaignState,
    ObservationBatch,
    is_red_criterion_triggered,
    load_campaign_state,
    save_campaign_state,
    step_campaign_monitor,
)
from adam.intelligence.spine.phase_9_pre_launch import (
    DEFAULT_MSPRT_ALPHA,
    DEFAULT_MSPRT_BETA,
    MSPRTDecision,
)


# -----------------------------------------------------------------------------
# Fake async Neo4j (records cypher calls + holds in-memory state)
# -----------------------------------------------------------------------------


class _FakeRecord:
    def __init__(self, data: Dict[str, Any]) -> None:
        self._data = data

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)


class _FakeAsyncResult:
    def __init__(self, rows: List[Dict[str, Any]]) -> None:
        self._rows = list(rows)

    async def single(self) -> Optional[_FakeRecord]:
        if not self._rows:
            return None
        return _FakeRecord(self._rows[0])

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

        cypher_norm = cypher.strip()

        # Persist: MERGE → in-memory by campaign_id
        if cypher_norm.startswith("MERGE (s:MSPRTCampaignState"):
            cid = params["campaign_id"]
            self._driver.states[cid] = dict(params)
            return _FakeAsyncResult([])

        # Load: MATCH ... RETURN
        if cypher_norm.startswith("MATCH (s:MSPRTCampaignState"):
            cid = params["campaign_id"]
            state = self._driver.states.get(cid)
            if state is None:
                return _FakeAsyncResult([])
            return _FakeAsyncResult([state])

        return _FakeAsyncResult([])


class FakeAsyncNeo4jDriver:
    def __init__(self) -> None:
        self.states: Dict[str, Dict[str, Any]] = {}
        self.calls: List = []

    def session(self) -> _FakeAsyncSession:
        return _FakeAsyncSession(self)


# -----------------------------------------------------------------------------
# Constants pinned (A14 defaults)
# -----------------------------------------------------------------------------


def test_constants_pinned():
    """Drift requires explicit calibration update."""
    assert DEFAULT_EXPECTED_LIFT == 0.05
    assert DEFAULT_NULL_BASELINE_RATE == 0.05


# -----------------------------------------------------------------------------
# Persistence (save/load) — round-trip
# -----------------------------------------------------------------------------


async def test_save_no_driver_returns_false():
    state = MSPRTCampaignState(campaign_id="c1")
    assert (await save_campaign_state(state, driver=None)) is False


async def test_load_no_driver_returns_none():
    assert (await load_campaign_state("c1", driver=None)) is None


async def test_save_then_load_round_trip():
    driver = FakeAsyncNeo4jDriver()
    state = MSPRTCampaignState(
        campaign_id="luxy_pilot",
        n_treatment=100,
        n_control=200,
        sum_treatment=12.0,
        sum_control=10.0,
        expected_lift=0.05,
        alpha=0.05,
        beta=0.20,
        null_baseline_rate=0.05,
        log_likelihood_ratio=1.5,
        decision="continue",
        upper_boundary=2.77,
        lower_boundary=-1.56,
        last_updated_ts=1700000000.0,
    )

    ok = await save_campaign_state(state, driver)
    assert ok is True

    loaded = await load_campaign_state("luxy_pilot", driver)
    assert loaded is not None
    assert loaded.campaign_id == "luxy_pilot"
    assert loaded.n_treatment == 100
    assert loaded.sum_treatment == 12.0
    assert loaded.log_likelihood_ratio == 1.5
    assert loaded.decision == "continue"


async def test_load_missing_campaign_returns_none():
    driver = FakeAsyncNeo4jDriver()
    assert (await load_campaign_state("never-saved", driver)) is None


async def test_save_cypher_param_contract():
    """Persist cypher parameter contract — break this test on any
    schema drift to force an explicit migration plan."""
    driver = FakeAsyncNeo4jDriver()
    state = MSPRTCampaignState(campaign_id="c1")
    await save_campaign_state(state, driver)
    assert len(driver.calls) == 1
    cypher, params = driver.calls[0]
    expected_keys = {
        "campaign_id", "n_treatment", "n_control",
        "sum_treatment", "sum_control",
        "expected_lift", "alpha", "beta", "null_baseline_rate",
        "log_likelihood_ratio", "decision",
        "upper_boundary", "lower_boundary", "last_updated_ts",
    }
    assert expected_keys.issubset(params.keys()), (
        f"missing cypher params: {expected_keys - params.keys()}"
    )


async def test_repeat_save_does_not_duplicate():
    """MERGE — re-saving same campaign_id updates rather than
    duplicating."""
    driver = FakeAsyncNeo4jDriver()
    state = MSPRTCampaignState(campaign_id="c1", log_likelihood_ratio=1.0)
    await save_campaign_state(state, driver)
    state.log_likelihood_ratio = 2.0
    await save_campaign_state(
        MSPRTCampaignState(campaign_id="c1", log_likelihood_ratio=2.0),
        driver,
    )
    assert len(driver.states) == 1
    loaded = await load_campaign_state("c1", driver)
    assert loaded.log_likelihood_ratio == 2.0  # last writer wins


# -----------------------------------------------------------------------------
# step_campaign_monitor — accumulation + boundary detection
# -----------------------------------------------------------------------------


async def test_step_initial_run_no_prior_state():
    """First call: starts from zero state defined by config."""
    driver = FakeAsyncNeo4jDriver()
    config = MSPRTCampaignConfig(
        campaign_id="luxy_pilot",
        expected_lift=0.05,
    )
    batch = ObservationBatch(
        treatment_n=100,
        treatment_sum=10.0,
        control_n=100,
        control_sum=5.0,
    )

    new_state = await step_campaign_monitor(config, batch, driver)
    assert new_state.campaign_id == "luxy_pilot"
    assert new_state.n_treatment == 100
    assert new_state.n_control == 100
    assert new_state.sum_treatment == 10.0
    assert new_state.sum_control == 5.0
    assert new_state.last_updated_ts > 0.0


async def test_step_accumulates_over_prior_state():
    """Second call adds to the prior cumulative — that's the whole
    point of the persistent monitor."""
    driver = FakeAsyncNeo4jDriver()
    config = MSPRTCampaignConfig(campaign_id="c_acc")

    batch1 = ObservationBatch(
        treatment_n=50, treatment_sum=3.0, control_n=50, control_sum=2.0,
    )
    state1 = await step_campaign_monitor(config, batch1, driver)
    assert state1.n_treatment == 50
    assert state1.sum_treatment == 3.0

    batch2 = ObservationBatch(
        treatment_n=70, treatment_sum=5.0, control_n=80, control_sum=3.0,
    )
    state2 = await step_campaign_monitor(config, batch2, driver)
    # Cumulative
    assert state2.n_treatment == 50 + 70
    assert state2.n_control == 50 + 80
    assert state2.sum_treatment == 3.0 + 5.0
    assert state2.sum_control == 2.0 + 3.0


async def test_step_soft_fails_without_driver():
    """Without driver, step runs in-memory and returns result;
    persistence is best-effort and silently skipped."""
    config = MSPRTCampaignConfig(campaign_id="c_no_driver")
    batch = ObservationBatch(
        treatment_n=10, treatment_sum=1.0, control_n=10, control_sum=0.0,
    )
    state = await step_campaign_monitor(config, batch, driver=None)
    assert state is not None
    assert state.campaign_id == "c_no_driver"
    assert state.n_treatment == 10


async def test_step_strong_signal_accumulates_to_reject_null():
    """Persistent strong lift → eventually upper boundary crossed
    (REJECT_NULL — ADAM lifts)."""
    driver = FakeAsyncNeo4jDriver()
    config = MSPRTCampaignConfig(
        campaign_id="c_signal",
        expected_lift=0.05,
        null_baseline_rate=0.05,
    )

    # Treatment converts at ~10% (= null + 0.05); control at ~5%
    # In one batch (large N) the cumulative LLR should cross the
    # upper boundary.
    batch = ObservationBatch(
        treatment_n=2000, treatment_sum=200.0,  # 10% rate
        control_n=2000, control_sum=100.0,      # 5% rate
    )

    state = await step_campaign_monitor(config, batch, driver)
    assert state.decision == MSPRTDecision.REJECT_NULL.value
    assert state.log_likelihood_ratio >= state.upper_boundary


async def test_step_null_accumulates_to_accept_null():
    """Persistent null (treatment ≈ control) → lower boundary
    eventually crossed (ACCEPT_NULL — RED-criterion launch deferral
    per directive line 1134)."""
    driver = FakeAsyncNeo4jDriver()
    config = MSPRTCampaignConfig(
        campaign_id="c_null",
        expected_lift=0.05,
        null_baseline_rate=0.05,
    )

    # Both arms converting at ~5% (= null baseline). Under H_1 we
    # expected treatment at 10%; we observe 5%. Cumulative LLR
    # accrues evidence FOR null → eventually crosses lower boundary.
    batch = ObservationBatch(
        treatment_n=5000, treatment_sum=250.0,  # 5% rate (= null)
        control_n=5000, control_sum=250.0,      # 5% rate (= null)
    )

    state = await step_campaign_monitor(config, batch, driver)
    assert state.decision == MSPRTDecision.ACCEPT_NULL.value
    assert state.log_likelihood_ratio <= state.lower_boundary


async def test_step_continue_on_small_n():
    """Small batch with weak signal → still in CONTINUE region."""
    driver = FakeAsyncNeo4jDriver()
    config = MSPRTCampaignConfig(
        campaign_id="c_continue",
        expected_lift=0.05,
        null_baseline_rate=0.05,
    )
    batch = ObservationBatch(
        treatment_n=10, treatment_sum=1.0,
        control_n=10, control_sum=0.0,
    )
    state = await step_campaign_monitor(config, batch, driver)
    assert state.decision == MSPRTDecision.CONTINUE.value


# -----------------------------------------------------------------------------
# Campaign isolation
# -----------------------------------------------------------------------------


async def test_two_campaigns_do_not_cross_contaminate():
    """Each campaign_id has its own persistent state."""
    driver = FakeAsyncNeo4jDriver()
    config_a = MSPRTCampaignConfig(campaign_id="campaign_a")
    config_b = MSPRTCampaignConfig(campaign_id="campaign_b")

    batch_a = ObservationBatch(
        treatment_n=100, treatment_sum=10.0, control_n=100, control_sum=5.0,
    )
    batch_b = ObservationBatch(
        treatment_n=200, treatment_sum=20.0, control_n=200, control_sum=8.0,
    )

    state_a = await step_campaign_monitor(config_a, batch_a, driver)
    state_b = await step_campaign_monitor(config_b, batch_b, driver)

    # Each has its own cumulative
    assert state_a.n_treatment == 100
    assert state_b.n_treatment == 200

    # Reload → still distinct
    loaded_a = await load_campaign_state("campaign_a", driver)
    loaded_b = await load_campaign_state("campaign_b", driver)
    assert loaded_a.n_treatment == 100
    assert loaded_b.n_treatment == 200


# -----------------------------------------------------------------------------
# RED-criterion convenience
# -----------------------------------------------------------------------------


def test_is_red_criterion_triggered_true_on_accept_null():
    state = MSPRTCampaignState(
        campaign_id="c", decision=MSPRTDecision.ACCEPT_NULL.value,
    )
    assert is_red_criterion_triggered(state) is True


def test_is_red_criterion_triggered_false_on_continue():
    state = MSPRTCampaignState(
        campaign_id="c", decision=MSPRTDecision.CONTINUE.value,
    )
    assert is_red_criterion_triggered(state) is False


def test_is_red_criterion_triggered_false_on_reject_null():
    """REJECT_NULL is GREEN (positive signal), not RED."""
    state = MSPRTCampaignState(
        campaign_id="c", decision=MSPRTDecision.REJECT_NULL.value,
    )
    assert is_red_criterion_triggered(state) is False


# -----------------------------------------------------------------------------
# Schema validation
# -----------------------------------------------------------------------------


def test_observation_batch_rejects_negative_counts():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ObservationBatch(
            treatment_n=-1, treatment_sum=0.0,
            control_n=0, control_sum=0.0,
        )


def test_observation_batch_accepts_negative_sums_for_continuous_outcomes():
    """Slice 10: continuous-outcome support means sums CAN be negative
    (signed-scale outcomes such as time-since-baseline shifts).
    Counts still cannot be negative; sums are unconstrained."""
    batch = ObservationBatch(
        treatment_n=10, treatment_sum=-1.0,
        control_n=10, control_sum=0.0,
    )
    assert batch.treatment_sum == -1.0


def test_state_extra_fields_forbidden():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        MSPRTCampaignState(
            campaign_id="c", unknown_field=1,  # type: ignore[call-arg]
        )


def test_config_extra_fields_forbidden():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        MSPRTCampaignConfig(
            campaign_id="c", unknown_field=1,  # type: ignore[call-arg]
        )


# -----------------------------------------------------------------------------
# Slice 10 — outcome_mode dispatch (continuous mSPRT wire)
# -----------------------------------------------------------------------------


def test_default_outcome_mode_is_binary():
    """Backward-compatible default: existing callers see binary mode."""
    config = MSPRTCampaignConfig(campaign_id="c")
    assert config.outcome_mode == "binary"
    assert config.sub_gaussian_sigma is None


@pytest.mark.asyncio
async def test_step_continuous_mode_seeds_initial_state():
    """First step on a continuous-mode campaign carries outcome_mode +
    sigma into the persisted state."""
    driver = FakeAsyncNeo4jDriver()
    config = MSPRTCampaignConfig(
        campaign_id="cont-1",
        expected_lift=0.05,
        outcome_mode="continuous",
        sub_gaussian_sigma=0.10,
    )
    batch = ObservationBatch(
        treatment_n=10, treatment_sum=1.0,
        control_n=10, control_sum=0.5,
    )
    state = await step_campaign_monitor(config, batch, driver=driver)

    assert state.outcome_mode == "continuous"
    assert state.sub_gaussian_sigma == pytest.approx(0.10)
    # State was persisted with the new fields
    persisted = driver.states["cont-1"]
    assert persisted["outcome_mode"] == "continuous"
    assert persisted["sub_gaussian_sigma"] == pytest.approx(0.10)


@pytest.mark.asyncio
async def test_step_continuous_strong_lift_rejects_null():
    """Continuous outcome — strong lift accumulates to REJECT_NULL."""
    driver = FakeAsyncNeo4jDriver()
    config = MSPRTCampaignConfig(
        campaign_id="cont-strong",
        expected_lift=0.15,
        outcome_mode="continuous",
        sub_gaussian_sigma=0.10,
    )
    # Treatment mean 0.20; control mean 0.05; diff 0.15 = expected_lift.
    # n=200 each → big LLR.
    batch = ObservationBatch(
        treatment_n=200, treatment_sum=40.0,  # mean 0.20
        control_n=200, control_sum=10.0,      # mean 0.05
    )
    state = await step_campaign_monitor(config, batch, driver=driver)
    assert state.decision == "reject_null"


@pytest.mark.asyncio
async def test_step_continuous_no_lift_accepts_null():
    """Continuous outcome — zero diff with large n accumulates to
    ACCEPT_NULL (RED-criterion launch deferral)."""
    driver = FakeAsyncNeo4jDriver()
    config = MSPRTCampaignConfig(
        campaign_id="cont-null",
        expected_lift=0.05,
        outcome_mode="continuous",
        sub_gaussian_sigma=0.10,
    )
    batch = ObservationBatch(
        treatment_n=500, treatment_sum=25.0,  # mean 0.05
        control_n=500, control_sum=25.0,      # mean 0.05
    )
    state = await step_campaign_monitor(config, batch, driver=driver)
    assert state.decision == "accept_null"
    assert is_red_criterion_triggered(state) is True


@pytest.mark.asyncio
async def test_step_continuous_negative_outcomes_supported():
    """Signed-scale continuous outcomes (e.g., time-since-baseline)
    flow through without ObservationBatch validation errors."""
    driver = FakeAsyncNeo4jDriver()
    config = MSPRTCampaignConfig(
        campaign_id="cont-signed",
        expected_lift=0.08,
        outcome_mode="continuous",
        sub_gaussian_sigma=0.10,
    )
    batch = ObservationBatch(
        treatment_n=100, treatment_sum=-2.0,  # mean -0.02
        control_n=100, control_sum=-10.0,     # mean -0.10
    )
    # diff = +0.08 (matches expected_lift) → positive LLR
    state = await step_campaign_monitor(config, batch, driver=driver)
    assert state.log_likelihood_ratio > 0


@pytest.mark.asyncio
async def test_step_continuous_mode_persists_across_loads():
    """Reload after a continuous step preserves outcome_mode + sigma."""
    driver = FakeAsyncNeo4jDriver()
    config = MSPRTCampaignConfig(
        campaign_id="cont-persist",
        expected_lift=0.05,
        outcome_mode="continuous",
        sub_gaussian_sigma=0.12,
    )
    batch1 = ObservationBatch(
        treatment_n=50, treatment_sum=5.0,
        control_n=50, control_sum=4.0,
    )
    state1 = await step_campaign_monitor(config, batch1, driver=driver)

    # Second step — config is now redundant (loaded state takes over)
    batch2 = ObservationBatch(
        treatment_n=50, treatment_sum=5.0,
        control_n=50, control_sum=4.0,
    )
    state2 = await step_campaign_monitor(config, batch2, driver=driver)

    assert state2.outcome_mode == "continuous"
    assert state2.sub_gaussian_sigma == pytest.approx(0.12)
    # Cumulative grew
    assert state2.n_treatment == 100
    assert state2.n_control == 100


@pytest.mark.asyncio
async def test_step_continuous_missing_sigma_raises():
    """outcome_mode='continuous' with sub_gaussian_sigma=None raises
    when the dispatch reaches msprt_step_continuous."""
    driver = FakeAsyncNeo4jDriver()
    config = MSPRTCampaignConfig(
        campaign_id="cont-bad",
        outcome_mode="continuous",
        sub_gaussian_sigma=None,  # explicit
    )
    batch = ObservationBatch(
        treatment_n=10, treatment_sum=1.0,
        control_n=10, control_sum=0.5,
    )
    with pytest.raises(ValueError, match="sub_gaussian_sigma"):
        await step_campaign_monitor(config, batch, driver=driver)


@pytest.mark.asyncio
async def test_step_binary_default_path_unchanged():
    """The original binary-mode behavior is preserved for callers
    that don't set outcome_mode."""
    driver = FakeAsyncNeo4jDriver()
    config = MSPRTCampaignConfig(
        campaign_id="bin-default",
        expected_lift=0.10,
        null_baseline_rate=0.05,
    )
    batch = ObservationBatch(
        treatment_n=50, treatment_sum=10.0,  # 20% rate
        control_n=50, control_sum=2.5,
    )
    state = await step_campaign_monitor(config, batch, driver=driver)
    assert state.outcome_mode == "binary"
    assert state.sub_gaussian_sigma is None
    # binary REJECT_NULL on strong-signal accumulation
    assert state.decision == "reject_null"


@pytest.mark.asyncio
async def test_load_pre_slice_10_state_defaults_to_binary():
    """Reloading a state persisted before Slice 10 (no outcome_mode
    property in record) defaults to binary mode for backward compat."""
    driver = FakeAsyncNeo4jDriver()
    # Manually plant a state row that lacks outcome_mode / sub_gaussian_sigma
    driver.states["legacy"] = {
        "campaign_id": "legacy",
        "n_treatment": 10, "n_control": 10,
        "sum_treatment": 1.0, "sum_control": 0.5,
        "expected_lift": 0.05,
        "alpha": 0.05, "beta": 0.20,
        "null_baseline_rate": 0.05,
        "log_likelihood_ratio": 0.0,
        "decision": "continue",
        "upper_boundary": 2.77,
        "lower_boundary": -1.56,
        "last_updated_ts": 1.0,
        # no outcome_mode, no sub_gaussian_sigma
    }
    loaded = await load_campaign_state("legacy", driver=driver)
    assert loaded is not None
    assert loaded.outcome_mode == "binary"
    assert loaded.sub_gaussian_sigma is None
