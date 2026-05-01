"""
Task 39: mSPRT campaign-level monitor — daily scheduler hookup

Closes the operational scheduler-hookup half of the mSPRT chain
(directive line 31 + Section 8.3 line 913 + line 1125):

    line 1125: "Soft launch: 10% of campaign budget against holdout;
                daily monitoring of fluency-floor violation rate,
                decision-trace emission rate, posterior update health,
                mSPRT campaign-level boundary status."

The Task 39 daily flow:

  1. Resolve the active pilot campaign_id (env var
     MSPRT_PILOT_CAMPAIGN_ID, default "luxy_pilot")
  2. Compute the prior-24h outcome window
  3. aggregate_outcomes_for_window from :DecisionContext + :AdOutcome
  4. step_campaign_monitor(config, batch, driver) → updated state
  5. Log + report state for the partner dashboard

Per directive line 31: "mSPRT runs continuously during the pilot."
Without this scheduler hookup, the campaign monitor (f4a9093) +
aggregation function (sibling) exist but never run on real data.

Soft-fail discipline:
  * Infra unavailable → skipped with detail
  * Aggregation exception → returns zero-batch, no mSPRT step taken
  * Step exception → result.success=False, error logged

Directive citations:
  - line 31: mSPRT continuous monitoring
  - Section 8.3 line 913: replaces sample-size adequacy tracker
  - line 927: pre-specified boundaries; lower-cross = RED-criterion
  - line 1125: daily monitoring during soft launch
  - line 1134: lower-boundary cross is launch-deferral trigger
"""

from __future__ import annotations

import logging
import os
import time
from typing import List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


# A14 MSPRT_PILOT_CAMPAIGN_ID_PILOT_PENDING
DEFAULT_PILOT_CAMPAIGN_ID: str = "luxy_pilot"
"""Default campaign_id for the LUXY pilot. Production callers set
MSPRT_PILOT_CAMPAIGN_ID env var to override. A registry of multiple
active campaigns is a sibling slice when the pilot expands beyond
the single campaign."""

# Window: prior 24h
WINDOW_SECONDS: int = 24 * 3600


class MSPRTCampaignMonitorTask(DailyStrengtheningTask):
    """Daily mSPRT campaign-level boundary check."""

    @property
    def name(self) -> str:
        return "msprt_campaign_monitor"

    @property
    def schedule_hours(self) -> List[int]:
        # 7 AM UTC — after main daily ingest + Task 38 drain finishes
        return [7]

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        # --- Resolve dependencies ---
        try:
            from adam.intelligence.msprt_campaign_monitor import (
                MSPRTCampaignConfig,
                is_red_criterion_triggered,
                step_campaign_monitor,
            )
            from adam.intelligence.msprt_outcome_aggregation import (
                aggregate_outcomes_for_window,
            )
        except Exception as exc:
            result.success = False
            result.details["error"] = f"import failed: {exc}"
            return result

        # --- Resolve infrastructure ---
        try:
            from adam.core.dependencies import get_infrastructure
            infra = await get_infrastructure()
            driver = getattr(infra, "neo4j", None)
        except Exception as exc:
            logger.debug("Task 39 infrastructure unavailable: %s", exc)
            driver = None

        if driver is None:
            result.details["skipped"] = "no_driver"
            return result

        # --- Resolve campaign config ---
        campaign_id = os.environ.get(
            "MSPRT_PILOT_CAMPAIGN_ID", DEFAULT_PILOT_CAMPAIGN_ID,
        )
        config = MSPRTCampaignConfig(campaign_id=campaign_id)

        # --- Compute window ---
        until_ts = time.time()
        since_ts = until_ts - WINDOW_SECONDS

        # --- Aggregate outcomes ---
        try:
            batch = await aggregate_outcomes_for_window(
                driver=driver,
                since_ts=since_ts,
                until_ts=until_ts,
            )
        except Exception as exc:
            result.success = False
            result.details["error"] = (
                f"aggregate_outcomes_for_window failed: {exc}"
            )
            return result

        result.details["window_since_ts"] = since_ts
        result.details["window_until_ts"] = until_ts
        result.details["batch_treatment_n"] = batch.treatment_n
        result.details["batch_treatment_sum"] = batch.treatment_sum
        result.details["batch_control_n"] = batch.control_n
        result.details["batch_control_sum"] = batch.control_sum

        if batch.treatment_n == 0 and batch.control_n == 0:
            # No observations this window — skip mSPRT step (cumulative
            # state would be unchanged; persisting that is wasteful).
            result.details["skipped"] = "no_observations"
            return result

        # --- Step campaign monitor ---
        try:
            new_state = await step_campaign_monitor(
                config=config, batch=batch, driver=driver,
            )
        except Exception as exc:
            result.success = False
            result.details["error"] = (
                f"step_campaign_monitor failed: {exc}"
            )
            return result

        result.items_processed = batch.treatment_n + batch.control_n
        result.items_stored = 1  # one MSPRTCampaignState row updated
        result.details.update({
            "campaign_id": campaign_id,
            "decision": new_state.decision,
            "log_likelihood_ratio": new_state.log_likelihood_ratio,
            "upper_boundary": new_state.upper_boundary,
            "lower_boundary": new_state.lower_boundary,
            "n_treatment_cumulative": new_state.n_treatment,
            "n_control_cumulative": new_state.n_control,
            "red_criterion_triggered": is_red_criterion_triggered(new_state),
        })

        # Surface RED-criterion at WARNING level so ops sees it
        if is_red_criterion_triggered(new_state):
            logger.warning(
                "mSPRT RED-criterion triggered for campaign_id=%s: "
                "ACCEPT_NULL crossed (LLR=%.3f, lower=%.3f). "
                "Per directive line 1134, this is a launch-deferral "
                "trigger.",
                campaign_id,
                new_state.log_likelihood_ratio,
                new_state.lower_boundary,
            )

        return result
