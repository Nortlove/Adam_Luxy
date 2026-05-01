"""
Task 40: Nightly dual_eval_context re-warm — Spine #5 operational closure

Re-runs ``warm_dual_eval_from_neo4j`` nightly. As new
``:GoalStateLabel`` nodes accumulate (via Slice 18's Claude API
labeler — manually triggered OR via a separate offline pipeline),
this task ensures the production cascade's primary model swaps
to whichever of B / C wins on the latest labeled set.

Without this scheduled, the Slice 20 startup wire only runs at
process boot — adding labels mid-run wouldn't propagate to the
cascade until the next deploy.

Schedule: 03:00 UTC nightly. Sits after Task 34 hierarchical
refit (02:00) so the day's posteriors update first, and after
Task 39 mSPRT monitor (07:00 — runs earlier in the queue).

Cadence rationale: model retraining is offline + idempotent. Daily
is sufficient to catch new labels without wasting compute when
labels haven't changed. Sub-daily cadence is sibling slice if
labels arrive at high enough rate to warrant it.

Soft-fail discipline:
  * Infrastructure unavailable → skipped with detail
  * warm_dual_eval_from_neo4j returns "skipped" → propagate to
    result.details; task succeeds (the cascade still has its
    previous primary)
  * warm_dual_eval_from_neo4j raises → result.success=False with
    error detail

DECISION-TIME PATH

  Day N — labels accumulate via Slice 18 (manual or external pipeline)
      ↓ persist_label_to_neo4j → :GoalStateLabel nodes
  Day N+1 03:00 UTC — Task 40 fires
      ↓ warm_dual_eval_from_neo4j(driver)
  Both models retrain on accumulated labels
      ↓ Slice 19 evaluator picks winner
  register_dual_eval_context(primary=winner, shadow=other)
      ↓
  Day N+1 cascade decisions use the updated primary

DISCIPLINE (B3-LUXY a/b/c/d)
============================

(a) Citation: directive Section 6.2 (Claude API as offline slow brain
    — daily cadence specified there); Section 9 Phase 4 deliverable
    (decision-time intelligence layer operational); Slice 20
    (warm_dual_eval_from_neo4j composer).

(b) Tests pin: name + schedule_hours + frequency_hours; execute()
    routes to warm_dual_eval_from_neo4j; outcome propagates to
    details; no driver → skipped; raise → failed result; registration
    in scheduler (sibling slice when added).

(c) calibration_pending=True. 03:00 UTC slot conservative (after
    Task 34 hierarchical refit at 02:00). LUXY pilot may reveal
    a different optimal slot. A14 flag:
    SPINE_5_TASK_40_CADENCE_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Task that runs Claude API label generation on new pages
      from production DecisionTraces. v0.1 assumes labels arrive
      via manual / external offline pipeline; an integrated
      labeler-task would call generate_labels_bulk against pages
      seen in production traces. Sibling slice.
    * Sub-daily cadence (re-warm every N hours). Daily is the
      conservative pre-pilot default; pilot data + label-arrival
      rate calibrate.
    * Per-archetype / per-cohort dual-eval contexts. Spine #7
      BLOCKED on Loop B.
    * Prometheus metrics on warm outcomes (gauges per
      registered/cold_start/skipped). Sibling observability slice.
    * Slack / email alert when winner switches between models.
      Operational sibling.
"""

from __future__ import annotations

import logging
from typing import List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


class DualEvalRewarmTask(DailyStrengtheningTask):
    """Nightly re-warm of the DualEvalContext singleton from accumulated
    :GoalStateLabel nodes. Routes to ``warm_dual_eval_from_neo4j`` and
    surfaces the outcome on ``result.details``."""

    @property
    def name(self) -> str:
        return "dual_eval_rewarm"

    @property
    def schedule_hours(self) -> List[int]:
        # 03:00 UTC nightly. After Task 34 hierarchical refit (02:00).
        return [3]

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        # --- Resolve composer (lazy import) ---
        try:
            from adam.intelligence.free_energy_dual_eval import (
                warm_dual_eval_from_neo4j,
            )
        except Exception as exc:
            result.success = False
            result.details["error"] = (
                f"warm_dual_eval_from_neo4j import failed: {exc}"
            )
            return result

        # --- Resolve infrastructure ---
        neo4j_driver = None
        try:
            from adam.core.dependencies import get_infrastructure
            infra = await get_infrastructure()
            neo4j_driver = getattr(infra, "neo4j_driver", None) or getattr(
                infra, "neo4j", None,
            )
        except Exception as exc:
            logger.debug("Task 40 infrastructure unavailable: %s", exc)

        if neo4j_driver is None:
            result.details["skipped"] = "no_neo4j_driver"
            return result

        # --- Re-warm ---
        try:
            warm_status = await warm_dual_eval_from_neo4j(neo4j_driver)
        except Exception as exc:
            result.success = False
            result.details["error"] = (
                f"warm_dual_eval_from_neo4j failed: {exc}"
            )
            return result

        # Surface outcome on result.details
        result.details.update({
            "outcome": warm_status.get("outcome", ""),
            "n_labels": warm_status.get("n_labels", 0),
            "trained_models": warm_status.get("trained_models", []),
            "winner": warm_status.get("winner", ""),
            "warm_reason": warm_status.get("reason", ""),
        })
        result.items_processed = warm_status.get("n_labels", 0)
        result.items_stored = (
            1 if warm_status.get("outcome") == "registered" else 0
        )

        # Cold start is NOT a failure — production cascade still runs
        # passthrough as primary, which is the v0.1 baseline.
        if warm_status.get("outcome") == "skipped":
            # Skipped means infrastructure / load failure mid-chain.
            # Surface as a non-failure but flag it.
            logger.warning(
                "Task 40 dual_eval re-warm skipped: %s",
                warm_status.get("reason"),
            )

        return result
