# =============================================================================
# mSPRT Outcome Aggregation — daily cypher for campaign monitor
# Location: adam/intelligence/msprt_outcome_aggregation.py
# =============================================================================
"""Daily outcome aggregation for the mSPRT campaign monitor.

Reads :DecisionContext + :AdOutcome rows in a time window, partitions
by treatment_arm ("bilateral" vs "control"), and returns an
``ObservationBatch`` consumable by ``step_campaign_monitor`` (shipped
f4a9093).

Closes the named-successor slice from f4a9093's honest tags:

    "Daily aggregation cypher that reads :DecisionContext +
     :AdOutcome nodes for the prior day, partitions by
     ``treatment_arm`` ("bilateral" vs "control"), and produces an
     ObservationBatch."

WHY THIS EXISTS
---------------

The mSPRT campaign monitor (f4a9093) is the persistent state +
boundary-detection wrapper. It needs an observation batch on each
step. This module is the producer that reads from the live
:AdOutcome stream + :DecisionContext rows and aggregates per
treatment arm.

The directive's deterministic-hash holdout (Section 8.3 line 916)
puts ~5-10% of impressions into "control" without ADAM treatment,
the rest into "bilateral" treatment. The mSPRT compares the two
arms' conversion rates over the pilot window.

ARCHITECTURE
------------

  bid-time decision
        ↓ writes :DecisionContext with treatment_arm + metadata_json
  outcome event
        ↓ writes :AdOutcome via OutcomeHandler, links via :HAD_OUTCOME
  Daily Task 39 (sibling slice)
        ↓ aggregate_outcomes_for_window(driver, since_ts, until_ts)
  ObservationBatch (this module's output)
        ↓
  step_campaign_monitor(config, batch, driver)  [f4a9093]
        ↓
  MSPRTCampaignState (persisted)

TREATMENT ARM RESOLUTION
------------------------

The treatment_arm is sourced from :DecisionContext following the
existing OutcomeHandler convention (adam/core/learning/outcome_handler
.py:560-589):

  1. dc.treatment_arm property (preferred — fast cypher access)
  2. metadata_json["treatment_arm"] (fallback — JSON-parsed Python-side)
  3. Default "bilateral" when both missing

Two arm values are recognized:
  - "control" → counted toward control_n / control_sum
  - anything else (including "bilateral") → treatment_n / treatment_sum

This matches the ``MultiHorizonAdjudication.treatment_arm`` field at
adam/intelligence/multi_horizon_adjudication.py:103 ("bilateral" |
"control" — drives diagonal analysis).

OUTCOME BINARIZATION
--------------------

For mSPRT (Bernoulli outcomes), AdOutcome.outcome_value > 0 → 1 else 0.
The campaign-level question per directive Section 8.4 is conversion
rate (binary), not value. Multi-value outcomes are summarized by
"any positive outcome" → 1 for the mSPRT.

Honest tag: continuous-outcome mSPRT (Howard et al. 2021 sub-
gaussian extension) is a sibling slice when LUXY pilot data shows
binary collapses too much information.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Section 8.3 line 913 (mSPRT replacement);
    directive line 916 (deterministic-hash holdout); existing
    OutcomeHandler treatment_arm convention.

(b) Tests pin: aggregation correctly partitions arms; missing
    outcomes counted as zero (Bernoulli); arm resolution prefers
    property over metadata_json; metadata_json fallback works;
    unknown arm → treatment by convention; soft-fail without driver
    returns zero-batch; window bounds respected.

(c) calibration_pending=False — this is declarative cypher logic;
    no pilot-tunable constants here.

(d) Honest tags — what is NOT in this slice (named successors):

    * Continuous-outcome mSPRT (sub-gaussian Howard et al. 2021).
      Binary collapse may lose information for value-conversion
      analysis; sibling slice when pilot data shows it matters.
    * Per-cohort aggregation. Cohorts (Spine #7) are BLOCKED on
      Loop B; this slice produces campaign-level totals only.
    * Decision-arm metadata index migration (CREATE INDEX ON
      :DecisionContext(treatment_arm)). Operational, not code;
      should run before this writer hits scale.
    * Observation deduplication. The cypher query is bounded by
      [since_ts, until_ts) — daily callers must pass non-
      overlapping windows. Deduplication via decision_id is a
      sibling slice if observed late-arriving events cause
      double-count.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from adam.intelligence.msprt_campaign_monitor import ObservationBatch

logger = logging.getLogger(__name__)


# =============================================================================
# Cypher (kept module-level so tests pin the schema)
# =============================================================================


_AGGREGATION_CYPHER: str = (
    "MATCH (dc:DecisionContext) "
    "WHERE dc.created_at >= $since_ts AND dc.created_at < $until_ts "
    "OPTIONAL MATCH (dc)-[:HAD_OUTCOME]->(o:AdOutcome) "
    "RETURN dc.treatment_arm AS arm_property, "
    "       dc.metadata_json AS metadata_json, "
    "       coalesce(o.outcome_value, 0.0) AS outcome_value"
)

# Recognized treatment arm values (matches outcome_handler convention)
_CONTROL_ARM: str = "control"
_DEFAULT_ARM: str = "bilateral"


# =============================================================================
# Arm resolution
# =============================================================================


def _resolve_arm(
    arm_property: Optional[str],
    metadata_json: Optional[str],
) -> str:
    """Return the treatment_arm for one DecisionContext row.

    Preference order:
      1. dc.treatment_arm property (fast cypher access)
      2. metadata_json["treatment_arm"] (JSON-parsed Python-side)
      3. Default "bilateral"
    """
    if arm_property:
        return str(arm_property)

    if not metadata_json:
        return _DEFAULT_ARM

    try:
        meta = json.loads(metadata_json)
    except Exception:
        return _DEFAULT_ARM

    arm = meta.get("treatment_arm")
    if not arm:
        return _DEFAULT_ARM
    return str(arm)


# =============================================================================
# Aggregation
# =============================================================================


async def aggregate_outcomes_for_window(
    driver: Optional[Any],
    since_ts: float,
    until_ts: float,
) -> ObservationBatch:
    """Aggregate :DecisionContext outcomes in [since_ts, until_ts).

    Reads every DecisionContext in the window, joins to AdOutcome
    via :HAD_OUTCOME, partitions by treatment_arm, returns the
    Bernoulli-collapsed counts ready for step_campaign_monitor.

    Args:
        driver: async Neo4j driver. None → returns zero-batch.
        since_ts: window start (epoch seconds, inclusive).
        until_ts: window end (epoch seconds, exclusive).

    Soft-fail: any cypher / driver exception → returns zero-batch
    with a warning log. The caller (Task 39) will see "no observations
    this window" and take no mSPRT step.
    """
    zero_batch = ObservationBatch(
        treatment_n=0, treatment_sum=0.0,
        control_n=0, control_sum=0.0,
    )

    if driver is None:
        logger.debug(
            "aggregate_outcomes_for_window: no driver (soft-fail)"
        )
        return zero_batch

    if since_ts >= until_ts:
        logger.debug(
            "aggregate_outcomes_for_window: empty window since=%s until=%s",
            since_ts, until_ts,
        )
        return zero_batch

    treatment_n = 0
    treatment_sum = 0.0
    control_n = 0
    control_sum = 0.0

    try:
        async with driver.session() as session:
            result = await session.run(
                _AGGREGATION_CYPHER,
                since_ts=float(since_ts),
                until_ts=float(until_ts),
            )
            async for r in result:
                arm = _resolve_arm(
                    r.get("arm_property"),
                    r.get("metadata_json"),
                )

                # Bernoulli collapse: any positive outcome → 1
                outcome_v = r.get("outcome_value")
                try:
                    outcome_v = float(outcome_v) if outcome_v is not None else 0.0
                except (TypeError, ValueError):
                    outcome_v = 0.0
                outcome_binary = 1.0 if outcome_v > 0.0 else 0.0

                if arm == _CONTROL_ARM:
                    control_n += 1
                    control_sum += outcome_binary
                else:
                    treatment_n += 1
                    treatment_sum += outcome_binary
    except Exception as exc:
        logger.warning(
            "aggregate_outcomes_for_window cypher failed: %s", exc,
        )
        return zero_batch

    return ObservationBatch(
        treatment_n=treatment_n,
        treatment_sum=treatment_sum,
        control_n=control_n,
        control_sum=control_sum,
    )
