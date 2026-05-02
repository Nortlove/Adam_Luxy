"""
Task 42: Daily launch-gate runner — Slice 8 closure consumer

Closes audit Tier 1 #10 (consumer side): all 8 RED-criteria check
functions + ``run_launch_gate_evaluation`` aggregator exist with
skip-when-no-data discipline; only the sapid round-trip counter was
incrementing in production. Slice 8's snapshot accumulator
(adam/intelligence/red_criteria_snapshot.py) is the producer side
this task consumes.

Per directive Section 9 Phase 10 lines 1130-1138: ANY ONE of the 8
RED criteria triggers a launch deferral. The daily task constructs
LaunchGateInputs from the snapshot accumulator + the Sapid Round
Trip Monitor singleton, calls the runner, and persists a
:LaunchGateResult node for trending + dashboard surfaces.

Schedule: 05:00 UTC nightly. Sits AFTER Task 41 (04:00 OPE
estimator) and AFTER Task 40 (03:00 dual-eval re-warm) so the
day's posterior + estimate machinery is settled.

Snapshot atomicity: ``snapshot_and_reset()`` is atomic — the next
24h cycle starts cleanly. CMO disposition + metaphor coherence
inputs stay None per skip-when-no-data discipline (operational/
external signals; honest tag in red_criteria_snapshot (d)).

OUTPUTS

  * Per-criterion CriterionCheck list (which fired, which didn't)
  * Aggregate LaunchGateResult.any_triggered (the launch-deferral
    decision)
  * :LaunchGateResult Neo4j node — one per task run — for trending.
    Idempotent on (date, schedule_hours).
  * Surfaces summary on result.details.

NOT IN SCOPE (named successors)

  * cmo_review_disposition input. CMO review form is operational
    UI work (Phase 7 partner surface); until that lands, this
    criterion is skip-when-no-data.
  * n_creatives_failed_spot_check input. Offline-pipeline metaphor
    coherence scorer is Section 6 (Spine #12) work; not in cascade
    today. Skip-when-no-data until that scorer runs and aggregates.
  * Identity-stability collapse counter producer wire. The
    snapshot's record_identity_collapse method exists; the
    user-posterior maintenance sweep that calls it is a sibling
    slice (named in red_criteria_snapshot (d)).
  * Phase advance/defer automation (auto-pause, auto-rollback).
    Today the task surfaces the verdict; the human decides. CI/CD
    auto-pause is sibling slice on Phase 7 partner-surface work.

DISCIPLINE (B3-LUXY a/b/c/d)
============================

(a) Citations: directive Section 9 Phase 10 lines 1130-1138 (8 RED
    criteria); Section 9 Phase 10 line 1128 ("Continuous monitoring
    — the spine's own observability"); audit 2026-05-01 Tier 1 #10.

(b) Tests pin: name + schedule_hours + frequency_hours; execute()
    routes to snapshot_and_reset → run_launch_gate_evaluation;
    sapid round-trip rate pulled from monitor singleton when not
    in snapshot; cold-start (zero bids in window) yields runner
    with skipped checks; LaunchGateResult persisted; result.details
    surfaces any_triggered + triggered_criteria; registered in
    scheduler.

(c) calibration_pending=True. 05:00 UTC slot conservative (after
    Task 41 04:00). A14 flag: SPINE_10_TASK_42_CADENCE_PILOT_PENDING.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


_LAUNCH_GATE_NODE: str = "LaunchGateResult"


_SNAPSHOT_CYPHER: str = (
    f"MERGE (g:{_LAUNCH_GATE_NODE} "
    "{date: $date, schedule_hour: $schedule_hour}) "
    "SET g.any_triggered = $any_triggered, "
    "    g.triggered_criteria = $triggered_criteria, "
    "    g.n_checks_evaluated = $n_checks_evaluated, "
    "    g.n_bids = $n_bids, "
    "    g.n_traces_emitted = $n_traces_emitted, "
    "    g.n_floor_violations = $n_floor_violations, "
    "    g.p99_latency_ms = $p99_latency_ms, "
    "    g.sapid_round_trip_rate = $sapid_round_trip_rate, "
    "    g.window_seconds = $window_seconds, "
    "    g.computed_at_ts = $computed_at_ts "
    "RETURN g.date AS date"
)


class LaunchGateRunnerTask(DailyStrengtheningTask):
    """Daily launch-gate runner. Snapshots producer counters, calls
    ``run_launch_gate_evaluation``, persists :LaunchGateResult, and
    surfaces the verdict on ``result.details``."""

    @property
    def name(self) -> str:
        return "launch_gate_runner"

    @property
    def schedule_hours(self) -> List[int]:
        # 05:00 UTC nightly — after Task 41 (04:00) and Task 40 (03:00).
        return [5]

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        # --- Lazy imports ---
        try:
            from adam.intelligence.red_criteria_snapshot import (
                get_red_snapshot,
            )
            from adam.intelligence.spine.phase_10_launch_sequence import (
                LaunchGateInputs,
                run_launch_gate_evaluation,
            )
        except Exception as exc:
            result.success = False
            result.details["error"] = (
                f"launch_gate import failed: {exc}"
            )
            return result

        # --- Snapshot the producer counters atomically ---
        snapshot = get_red_snapshot().snapshot_and_reset()
        n_bids = int(snapshot.get("n_bids", 0))
        n_traces_emitted = int(snapshot.get("n_traces_emitted", 0))
        n_floor_violations = int(snapshot.get("n_floor_violations", 0))
        n_users_active = int(snapshot.get("n_users_active", 0))
        n_users_collapsed = int(
            snapshot.get("n_users_with_collapsed_identity_stability", 0)
        )
        p99_latency_ms = snapshot.get("p99_latency_ms")
        window_seconds = float(snapshot.get("window_seconds", 0.0))

        result.details["window_seconds"] = window_seconds
        result.details["snapshot"] = {
            "n_bids": n_bids,
            "n_traces_emitted": n_traces_emitted,
            "n_floor_violations": n_floor_violations,
            "n_users_active": n_users_active,
            "n_users_with_collapsed_identity_stability": n_users_collapsed,
            "p99_latency_ms": p99_latency_ms,
        }

        # --- Sapid round-trip rate from the monitor singleton ---
        sapid_rate = None
        try:
            from adam.intelligence.spine.phase_8_stackadapt_integration import (
                get_default_monitor,
            )
            mon = get_default_monitor()
            if mon.n_sapids_resolved + mon.n_sapids_unresolved > 0:
                sapid_rate = mon.round_trip_rate()
        except Exception as exc:
            logger.debug("Sapid monitor read failed: %s", exc)

        # --- Compose LaunchGateInputs (skip-when-no-data discipline) ---
        # Only forward (n_bids, n_floor_violations) when n_bids > 0
        # — otherwise the rate calc divides by zero. Same logic for
        # trace emission. The skip-when-no-data semantic is what the
        # runner itself uses for the categorical inputs (CMO + metaphor)
        # which we leave at None per honest tag (d).
        inputs_kwargs = {}
        if n_bids > 0:
            inputs_kwargs["n_decisions"] = n_bids
            inputs_kwargs["n_floor_violations"] = n_floor_violations
            inputs_kwargs["n_bids"] = n_bids
            inputs_kwargs["n_traces_emitted"] = n_traces_emitted
        if n_users_active > 0:
            inputs_kwargs["n_users_active"] = n_users_active
            inputs_kwargs["n_users_with_collapsed_identity_stability"] = (
                n_users_collapsed
            )
        if p99_latency_ms is not None:
            inputs_kwargs["p99_latency_ms"] = float(p99_latency_ms)
        if sapid_rate is not None:
            inputs_kwargs["sapid_round_trip_rate"] = float(sapid_rate)

        inputs = LaunchGateInputs(**inputs_kwargs)

        # --- Run the gate ---
        try:
            gate_result = run_launch_gate_evaluation(inputs)
        except Exception as exc:
            result.success = False
            result.details["error"] = (
                f"run_launch_gate_evaluation failed: {exc}"
            )
            return result

        triggered_criteria = [
            str(c) for c in gate_result.triggered_criteria
        ]
        n_checks = len(gate_result.checks)
        result.details.update({
            "any_triggered": bool(gate_result.any_triggered),
            "triggered_criteria": triggered_criteria,
            "n_checks_evaluated": n_checks,
        })
        result.items_processed = n_bids
        result.items_stored = 0  # set to 1 if snapshot writes succeed

        # --- Resolve infrastructure for snapshot persist ---
        neo4j_driver = None
        try:
            from adam.core.dependencies import get_infrastructure
            infra = await get_infrastructure()
            neo4j_driver = getattr(infra, "neo4j_driver", None) or getattr(
                infra, "neo4j", None,
            )
        except Exception as exc:
            logger.debug("Task 42 infrastructure unavailable: %s", exc)

        if neo4j_driver is not None:
            try:
                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                params = {
                    "date": today,
                    "schedule_hour": 5,
                    "any_triggered": bool(gate_result.any_triggered),
                    "triggered_criteria": triggered_criteria,
                    "n_checks_evaluated": int(n_checks),
                    "n_bids": int(n_bids),
                    "n_traces_emitted": int(n_traces_emitted),
                    "n_floor_violations": int(n_floor_violations),
                    "p99_latency_ms": (
                        float(p99_latency_ms)
                        if p99_latency_ms is not None else 0.0
                    ),
                    "sapid_round_trip_rate": (
                        float(sapid_rate) if sapid_rate is not None else 0.0
                    ),
                    "window_seconds": window_seconds,
                    "computed_at_ts": float(time.time()),
                }
                with neo4j_driver.session() as session:
                    session.run(_SNAPSHOT_CYPHER, **params)
                result.items_stored = 1
            except Exception as exc:
                logger.warning(
                    "Task 42 launch-gate runner: snapshot write failed: %s",
                    exc,
                )
                result.details["snapshot_write_error"] = str(exc)
        else:
            result.details["snapshot_write_skipped"] = "no_neo4j_driver"

        if gate_result.any_triggered:
            logger.warning(
                "Task 42 launch-gate runner: %d/%d criteria triggered: %s",
                len(triggered_criteria),
                n_checks,
                triggered_criteria,
            )
        else:
            logger.info(
                "Task 42 launch-gate runner: PASS (%d checks evaluated, "
                "0 triggered)",
                n_checks,
            )

        return result
