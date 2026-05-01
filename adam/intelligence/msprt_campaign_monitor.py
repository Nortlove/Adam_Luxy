# =============================================================================
# mSPRT Campaign-Level Monitor — directive Section 8.3 line 913
# Location: adam/intelligence/msprt_campaign_monitor.py
# =============================================================================
"""Stateful campaign-level mSPRT monitor with Neo4j persistence.

Closes the named-replacement deliverable from directive Section 8.3
line 913:

    "mSPRT campaign-level monitor replaces sample-size adequacy
     tracker for the campaign-level question."

Plus directive lines 31, 420, 837, 874, 927, 1087, 1114, 1125 — the
mSPRT board is the partner-facing campaign-level boundary status
that the LUXY CMO inspects + the RED-criterion launch-deferral
trigger that gates Phase 10 launch (line 1134).

WHY THIS EXISTS
---------------

The mSPRT step primitive (``adam/intelligence/spine/phase_9_pre_launch
.msprt_step``) is stateless — it takes cumulative counts/sums and
returns the boundary status at that point. To run mSPRT continuously
across the pilot lifecycle, the cumulative counts MUST persist across
calls. Without persistence:

  * Each call recomputes from zero — the mixture-SPRT property
    (continuous monitoring without alpha inflation) is broken because
    each call is effectively a fresh test
  * The dashboard cannot show "current state of the test" — it would
    only show "today's slice"
  * The RED-criterion lower-boundary cross would never trigger because
    the LLR never accumulates

This module is the persistence + accumulation wrapper. It loads prior
state from Neo4j, adds the new observation batch, calls ``msprt_step``
on the cumulative totals, persists the new state, and returns the
boundary status.

DECISION-TIME CONSUMER
----------------------

  * The partner dashboard (Spine #13 component 3 — sibling slice)
    reads the latest persisted state and renders the boundary status:
      - CONTINUE     → "still observing"
      - REJECT_NULL  → "ADAM significantly outperforms holdout" ✓
      - ACCEPT_NULL  → "no detectable lift" — RED-criterion triggers
                       launch-deferral per directive line 1134
  * The Daily drain task (sibling slice — analogous to Task 38)
    runs ``step_campaign_monitor`` once per day after outcome ingest,
    feeding the prior day's (treatment, control) aggregates into the
    cumulative state.

ARCHITECTURE
------------

  Outcome event stream (StackAdapt webhook → :AdOutcome nodes)
        ↓ (sibling slice — daily aggregation cypher)
  ObservationBatch(treatment_n, treatment_sum, control_n, control_sum)
        ↓
  step_campaign_monitor(config, batch, driver)        ← THIS MODULE
        ↓ load_campaign_state → add batch → msprt_step → save
  MSPRTCampaignState (persisted, Pydantic-typed)
        ↓ async load by campaign_id (sibling)
  Partner dashboard (Spine #13 component 3 — sibling slice)

NEO4J SCHEMA
------------

    (:MSPRTCampaignState {
        campaign_id*,         (UNIQUE, MERGE key)
        n_treatment,
        n_control,
        sum_treatment,
        sum_control,
        expected_lift,
        alpha,
        beta,
        null_baseline_rate,
        log_likelihood_ratio,
        decision,             ('continue' | 'reject_null' | 'accept_null')
        upper_boundary,
        lower_boundary,
        last_updated_ts,
    })

Idempotent: ``MERGE`` on campaign_id; ``SET`` overwrites scalar fields.
Re-running step_campaign_monitor with the same observation batch is
NOT idempotent (the cumulative counts grow each call) — the daily-task
caller is expected to deduplicate observations upstream.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Section 8.3 line 913, lines 31, 420, 837,
    874, 927, 1087, 1114, 1125, 1134. The mSPRT step primitive
    citations (Wald 1947, Robbins 1970, Howard et al. 2021) flow
    through to this module via the underlying ``msprt_step``.

(b) Tests pin: state round-trip via fake Neo4j driver; cumulative
    LLR grows correctly across multiple steps; upper-boundary cross
    detected on strong-signal accumulation; lower-boundary cross
    detected on null accumulation; soft-fail without driver
    (in-memory step still works, no persistence); load returns None
    on missing campaign_id; campaign_id isolation (two campaigns
    don't cross-contaminate); MERGE upsert on repeat persist.

(c) calibration_pending=True. The default ``expected_lift`` (5%) is
    the directive's exploratory anchor; LUXY pilot data informed by
    Phase 5 cross-category transfer will calibrate. A14 flag:
    MSPRT_CAMPAIGN_EXPECTED_LIFT_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Daily aggregation cypher that reads :DecisionContext +
      :AdOutcome nodes for the prior day, partitions by
      ``treatment_arm`` ("bilateral" vs "control"), and produces an
      ObservationBatch. Sibling slice — composes naturally with
      this monitor.
    * Daily Task 39 (mSPRT campaign monitor scheduler) — the
      operational scheduler-hookup that calls
      ``step_campaign_monitor`` daily. Sibling slice; pattern matches
      Task 38 from this session.
    * Partner-dashboard endpoint that reads MSPRTCampaignState and
      renders the boundary status. Front-end / API slice when the
      dashboard work lands (per future enterprise plan additions).
    * RED-criterion automated alert (slack / email when
      ACCEPT_NULL crosses). Operational alerting, sibling slice.
    * Cohort-level mSPRT (per-cohort boundary tracking). Cohorts
      (Spine #7) are BLOCKED on Loop B; this slice ships the
      campaign-level monitor first per the directive's named primary.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from adam.intelligence.spine.phase_9_pre_launch import (
    DEFAULT_MSPRT_ALPHA,
    DEFAULT_MSPRT_BETA,
    MSPRTDecision,
    MSPRTState,
    msprt_step,
    msprt_step_continuous,
)


# =============================================================================
# Outcome modes
# =============================================================================

OUTCOME_MODE_BINARY: str = "binary"
"""Default outcome mode — Bernoulli on conversion. Calls ``msprt_step``
with ``null_baseline_rate``."""

OUTCOME_MODE_CONTINUOUS: str = "continuous"
"""Sub-Gaussian / Gaussian-likelihood outcome mode. Calls
``msprt_step_continuous`` with ``sub_gaussian_sigma``. Use when the
outcome is graded (viewable dwell, scroll depth, time-on-site, value-
conversion) rather than binary conversion."""

_RECOGNIZED_OUTCOME_MODES = frozenset({
    OUTCOME_MODE_BINARY,
    OUTCOME_MODE_CONTINUOUS,
})

logger = logging.getLogger(__name__)


# A14 MSPRT_CAMPAIGN_EXPECTED_LIFT_PILOT_PENDING
DEFAULT_EXPECTED_LIFT: float = 0.05
"""Default expected lift under H_1. 5% is the directive's exploratory
anchor for B2B-travel; LUXY pilot data + Phase 5 cross-category
transfer will calibrate."""

DEFAULT_NULL_BASELINE_RATE: float = 0.05
"""Default null hypothesis baseline conversion rate. Mid-range for
B2B-travel programmatic; recalibrated when initial outcome data
arrives."""


# =============================================================================
# Schema
# =============================================================================


class MSPRTCampaignConfig(BaseModel):
    """Per-campaign mSPRT configuration.

    Carried alongside cumulative state so changes to expected_lift
    or alpha/beta require an explicit campaign reset (re-creating
    the persistent state with new config).
    """

    model_config = ConfigDict(extra="forbid")

    campaign_id: str
    expected_lift: float = DEFAULT_EXPECTED_LIFT
    alpha: float = DEFAULT_MSPRT_ALPHA
    beta: float = DEFAULT_MSPRT_BETA
    null_baseline_rate: float = DEFAULT_NULL_BASELINE_RATE

    # Slice 10 — outcome-mode dispatch. "binary" preserves the
    # original Bernoulli path (msprt_step); "continuous" routes to
    # msprt_step_continuous (Howard et al. 2021 v0.1) and requires
    # a non-None sub_gaussian_sigma. Default "binary" is backward-
    # compatible.
    outcome_mode: str = OUTCOME_MODE_BINARY
    sub_gaussian_sigma: Optional[float] = None


class ObservationBatch(BaseModel):
    """Observations to add to the cumulative state in one step.

    For binary outcomes: sum = success count, n = total. For continuous
    outcomes (Slice 10 / Howard et al. 2021): sum = cumulative outcome
    sum, n = observation count; sums may be negative on signed-scale
    outcomes (e.g., time-since-baseline shifts). The aggregator
    (sibling slice) produces these from the prior day's
    :DecisionContext + :AdOutcome rows partitioned by ``treatment_arm``.
    """

    model_config = ConfigDict(extra="forbid")

    treatment_n: int = Field(ge=0)
    treatment_sum: float = 0.0
    control_n: int = Field(ge=0)
    control_sum: float = 0.0


class MSPRTCampaignState(BaseModel):
    """Persisted campaign-level mSPRT state.

    Combines the underlying ``MSPRTState`` boundary fields with
    campaign identity + config so the dashboard can render directly
    from a single load.
    """

    model_config = ConfigDict(extra="forbid")

    campaign_id: str
    n_treatment: int = Field(ge=0, default=0)
    # n_control / sum_control are non-negative for binary outcomes;
    # continuous outcomes can be negative (signed-scale outcomes such
    # as time-since-baseline shifts). Drop the ge constraint on sum_*
    # to support continuous mode; n_* counts stay non-negative.
    n_control: int = Field(ge=0, default=0)
    sum_treatment: float = 0.0
    sum_control: float = 0.0
    expected_lift: float = DEFAULT_EXPECTED_LIFT
    alpha: float = DEFAULT_MSPRT_ALPHA
    beta: float = DEFAULT_MSPRT_BETA
    null_baseline_rate: float = DEFAULT_NULL_BASELINE_RATE
    log_likelihood_ratio: float = 0.0
    decision: str = MSPRTDecision.CONTINUE.value
    upper_boundary: float = 0.0
    lower_boundary: float = 0.0
    last_updated_ts: float = 0.0

    # Slice 10 — outcome-mode persistence. Required so reload
    # preserves the dispatch decision across step calls.
    outcome_mode: str = OUTCOME_MODE_BINARY
    sub_gaussian_sigma: Optional[float] = None


# =============================================================================
# Neo4j cypher (kept module-level so tests pin schema)
# =============================================================================


_PERSIST_CYPHER: str = (
    "MERGE (s:MSPRTCampaignState {campaign_id: $campaign_id}) "
    "SET s.n_treatment = $n_treatment, "
    "    s.n_control = $n_control, "
    "    s.sum_treatment = $sum_treatment, "
    "    s.sum_control = $sum_control, "
    "    s.expected_lift = $expected_lift, "
    "    s.alpha = $alpha, "
    "    s.beta = $beta, "
    "    s.null_baseline_rate = $null_baseline_rate, "
    "    s.log_likelihood_ratio = $log_likelihood_ratio, "
    "    s.decision = $decision, "
    "    s.upper_boundary = $upper_boundary, "
    "    s.lower_boundary = $lower_boundary, "
    "    s.last_updated_ts = $last_updated_ts, "
    "    s.outcome_mode = $outcome_mode, "
    "    s.sub_gaussian_sigma = $sub_gaussian_sigma"
)

_LOAD_CYPHER: str = (
    "MATCH (s:MSPRTCampaignState {campaign_id: $campaign_id}) "
    "RETURN s.n_treatment AS n_treatment, "
    "       s.n_control AS n_control, "
    "       s.sum_treatment AS sum_treatment, "
    "       s.sum_control AS sum_control, "
    "       s.expected_lift AS expected_lift, "
    "       s.alpha AS alpha, "
    "       s.beta AS beta, "
    "       s.null_baseline_rate AS null_baseline_rate, "
    "       s.log_likelihood_ratio AS log_likelihood_ratio, "
    "       s.decision AS decision, "
    "       s.upper_boundary AS upper_boundary, "
    "       s.lower_boundary AS lower_boundary, "
    "       s.last_updated_ts AS last_updated_ts, "
    "       s.outcome_mode AS outcome_mode, "
    "       s.sub_gaussian_sigma AS sub_gaussian_sigma "
    "LIMIT 1"
)


# =============================================================================
# Persistence
# =============================================================================


async def save_campaign_state(
    state: MSPRTCampaignState,
    driver: Optional[Any],
) -> bool:
    """Persist state to Neo4j. Idempotent (MERGE).

    Returns True on success, False on soft-fail (no driver, cypher
    exception). The caller treats False as "state stayed in memory
    for this call but was not persisted" — the next step will
    overwrite or load the prior persisted version, never raises.
    """
    if driver is None:
        logger.debug(
            "save_campaign_state: no driver (soft-fail to False)"
        )
        return False

    try:
        async with driver.session() as session:
            await session.run(
                _PERSIST_CYPHER,
                campaign_id=state.campaign_id,
                n_treatment=int(state.n_treatment),
                n_control=int(state.n_control),
                sum_treatment=float(state.sum_treatment),
                sum_control=float(state.sum_control),
                expected_lift=float(state.expected_lift),
                alpha=float(state.alpha),
                beta=float(state.beta),
                null_baseline_rate=float(state.null_baseline_rate),
                log_likelihood_ratio=float(state.log_likelihood_ratio),
                decision=str(state.decision),
                upper_boundary=float(state.upper_boundary),
                lower_boundary=float(state.lower_boundary),
                last_updated_ts=float(state.last_updated_ts),
                outcome_mode=str(state.outcome_mode),
                sub_gaussian_sigma=(
                    float(state.sub_gaussian_sigma)
                    if state.sub_gaussian_sigma is not None
                    else None
                ),
            )
    except Exception as exc:
        logger.warning(
            "save_campaign_state cypher failed for campaign_id=%s: %s",
            state.campaign_id, exc,
        )
        return False

    return True


async def load_campaign_state(
    campaign_id: str,
    driver: Optional[Any],
) -> Optional[MSPRTCampaignState]:
    """Fetch persisted state by campaign_id. Returns None if missing
    or driver unavailable. Never raises."""
    if driver is None:
        return None

    try:
        async with driver.session() as session:
            result = await session.run(
                _LOAD_CYPHER, campaign_id=campaign_id,
            )
            record = await result.single()
    except Exception as exc:
        logger.warning(
            "load_campaign_state cypher failed for campaign_id=%s: %s",
            campaign_id, exc,
        )
        return None

    if record is None:
        return None

    try:
        # Slice 10: outcome_mode / sub_gaussian_sigma are optional on
        # the loaded record so pre-Slice-10 persisted states (no
        # outcome_mode property) reload as binary mode by default.
        sigma_raw = record.get("sub_gaussian_sigma")
        return MSPRTCampaignState(
            campaign_id=campaign_id,
            n_treatment=int(record.get("n_treatment") or 0),
            n_control=int(record.get("n_control") or 0),
            sum_treatment=float(record.get("sum_treatment") or 0.0),
            sum_control=float(record.get("sum_control") or 0.0),
            expected_lift=float(
                record.get("expected_lift") or DEFAULT_EXPECTED_LIFT
            ),
            alpha=float(record.get("alpha") or DEFAULT_MSPRT_ALPHA),
            beta=float(record.get("beta") or DEFAULT_MSPRT_BETA),
            null_baseline_rate=float(
                record.get("null_baseline_rate")
                or DEFAULT_NULL_BASELINE_RATE
            ),
            log_likelihood_ratio=float(
                record.get("log_likelihood_ratio") or 0.0
            ),
            decision=str(record.get("decision") or MSPRTDecision.CONTINUE.value),
            upper_boundary=float(record.get("upper_boundary") or 0.0),
            lower_boundary=float(record.get("lower_boundary") or 0.0),
            last_updated_ts=float(record.get("last_updated_ts") or 0.0),
            outcome_mode=str(
                record.get("outcome_mode") or OUTCOME_MODE_BINARY
            ),
            sub_gaussian_sigma=(
                float(sigma_raw) if sigma_raw is not None else None
            ),
        )
    except Exception as exc:
        logger.warning(
            "load_campaign_state parse failed for campaign_id=%s: %s",
            campaign_id, exc,
        )
        return None


# =============================================================================
# Step
# =============================================================================


def _state_to_msprt_step_args(state: MSPRTCampaignState) -> dict:
    """Project persisted state into the kwargs msprt_step expects."""
    return {
        "n_treatment": state.n_treatment,
        "n_control": state.n_control,
        "sum_treatment": state.sum_treatment,
        "sum_control": state.sum_control,
        "expected_lift": state.expected_lift,
        "alpha": state.alpha,
        "beta": state.beta,
        "null_baseline_rate": state.null_baseline_rate,
    }


def _initial_state(config: MSPRTCampaignConfig) -> MSPRTCampaignState:
    """Build the starting state for a brand-new campaign."""
    return MSPRTCampaignState(
        campaign_id=config.campaign_id,
        expected_lift=config.expected_lift,
        alpha=config.alpha,
        beta=config.beta,
        null_baseline_rate=config.null_baseline_rate,
        outcome_mode=config.outcome_mode,
        sub_gaussian_sigma=config.sub_gaussian_sigma,
    )


async def step_campaign_monitor(
    config: MSPRTCampaignConfig,
    batch: ObservationBatch,
    driver: Optional[Any] = None,
) -> MSPRTCampaignState:
    """Add the observation batch to the cumulative state and re-test.

    Pipeline:
      1. load_campaign_state(config.campaign_id, driver)
         → Optional[prior_state]
      2. If None: start from _initial_state(config)
      3. Add batch counts/sums to cumulative
      4. Call msprt_step on cumulative totals
      5. Build new MSPRTCampaignState
      6. save_campaign_state (best-effort; failure logged but doesn't
         abort)
      7. Return the new state

    Soft-fail discipline: when driver is None, step still runs in
    memory and returns the result — caller may use the in-memory
    state for one-shot CLI / test invocations. Persistence is
    best-effort.

    Note on idempotency: re-running with the same batch will
    DOUBLE-COUNT — the cumulative grows. The daily-task caller is
    expected to deduplicate observations upstream (e.g., bound the
    aggregation cypher to the prior day's window).
    """
    prior = await load_campaign_state(config.campaign_id, driver)
    if prior is None:
        prior = _initial_state(config)

    # Accumulate
    new_n_treatment = prior.n_treatment + batch.treatment_n
    new_n_control = prior.n_control + batch.control_n
    new_sum_treatment = prior.sum_treatment + batch.treatment_sum
    new_sum_control = prior.sum_control + batch.control_sum

    # Slice 10 — dispatch by outcome_mode. The persisted state's
    # outcome_mode (loaded above OR seeded by _initial_state) is the
    # source of truth across step calls; once a campaign is configured
    # for continuous outcomes, every subsequent step routes through
    # msprt_step_continuous.
    if prior.outcome_mode == OUTCOME_MODE_CONTINUOUS:
        if prior.sub_gaussian_sigma is None:
            raise ValueError(
                f"campaign {config.campaign_id} configured "
                f"outcome_mode='continuous' but sub_gaussian_sigma is None"
            )
        msprt_state: MSPRTState = msprt_step_continuous(
            n_treatment=new_n_treatment,
            n_control=new_n_control,
            sum_treatment=new_sum_treatment,
            sum_control=new_sum_control,
            expected_lift=prior.expected_lift,
            sub_gaussian_sigma=prior.sub_gaussian_sigma,
            alpha=prior.alpha,
            beta=prior.beta,
        )
    else:
        msprt_state = msprt_step(
            n_treatment=new_n_treatment,
            n_control=new_n_control,
            sum_treatment=new_sum_treatment,
            sum_control=new_sum_control,
            expected_lift=prior.expected_lift,
            alpha=prior.alpha,
            beta=prior.beta,
            null_baseline_rate=prior.null_baseline_rate,
        )

    new_state = MSPRTCampaignState(
        campaign_id=config.campaign_id,
        n_treatment=msprt_state.n_treatment,
        n_control=msprt_state.n_control,
        sum_treatment=msprt_state.sum_treatment,
        sum_control=msprt_state.sum_control,
        expected_lift=prior.expected_lift,
        alpha=prior.alpha,
        beta=prior.beta,
        null_baseline_rate=prior.null_baseline_rate,
        log_likelihood_ratio=msprt_state.log_likelihood_ratio,
        decision=msprt_state.decision.value,
        upper_boundary=msprt_state.upper_boundary,
        lower_boundary=msprt_state.lower_boundary,
        last_updated_ts=time.time(),
        outcome_mode=prior.outcome_mode,
        sub_gaussian_sigma=prior.sub_gaussian_sigma,
    )

    # Best-effort persist
    await save_campaign_state(new_state, driver)

    return new_state


# =============================================================================
# Convenience: red-criterion check
# =============================================================================


def is_red_criterion_triggered(state: MSPRTCampaignState) -> bool:
    """Return True iff the campaign monitor has crossed the LOWER
    boundary (mSPRT ACCEPT_NULL).

    Per directive line 1134: "mSPRT lower-boundary cross during
    soft launch" is one of the four RED-criterion triggers for
    pilot deferral. Wraps the same logic as
    ``phase_9_pre_launch.is_red_criterion_triggered`` but on the
    persisted-state shape.
    """
    return state.decision == MSPRTDecision.ACCEPT_NULL.value
