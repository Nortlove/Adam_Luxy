"""
Task 44: Daily identity-stability collapse sweep — RED criterion #4 producer.

Closes the named sibling tag from
``task_42_launch_gate_runner.py:43-46``:

    "Identity-stability collapse counter producer wire. The
     snapshot's record_identity_collapse method exists; the
     user-posterior maintenance sweep that calls it is a sibling
     slice (named in red_criteria_snapshot (d))."

Per directive Section 9 Phase 10 line 1131-1138 RED criterion #4
("Per-user posterior pathologies — identity-stability weight collapse
for >30% of touches" → launch defers RED). The check function
``check_posterior_pathology`` in phase_10_launch_sequence already
consumes the producer counters
(``n_users_with_collapsed_identity_stability`` /
``n_users_active``); this task is the producer that finally
populates them.

Schedule: 04:00 UTC — same hour as Task 41 (OPE daily estimator).
Both produce nightly state that Task 42 (05:00 launch-gate runner)
consumes:

  * Task 40 03:00 — dual-eval re-warm
  * Task 41 04:00 — OPE daily estimator (writes :OPEDailyEstimate)
  * Task 44 04:00 — identity-stability sweep (increments
    snapshot.record_user_active + snapshot.record_identity_collapse)
  * Task 42 05:00 — launch-gate runner (reads + resets snapshot)

NOT IN SCOPE (named successors per identity_stability_sweep.py:d)

  * Persistent per-user :User.identity_stability scalar with
    learned-update-on-touch semantics. v0.1 decays from a default
    starting point (1.0) per active buyer based on
    days-since-last-touch in decision_cache.
  * Multi-pod sweep. The in-process decision_cache is per-process;
    multi-pod deploy needs the Redis-backed touch registry already
    named in within_subject_eligibility's honest tag (d).
  * Per-cohort attrition_per_day calibration.

DISCIPLINE (B3-LUXY a/b/c/d)
============================

(a) Citations: directive Section 9 Phase 10 lines 1131-1138 (RED
    criterion #4); task_42_launch_gate_runner.py:43-46 (named
    sibling tag); identity_stability_sweep.py (the primitive this
    task drives).

(b) Tests pin: name + schedule_hours + frequency_hours; execute()
    routes to sweep_active_buyers; no decision_cache → skipped;
    snapshot counters incremented; result.details surfaces
    n_active + n_collapsed + collapse_fraction; registered in
    scheduler.

(c) calibration_pending=True. 04:00 UTC slot conservative (BEFORE
    Task 42 05:00 reads the snapshot). A14 flag:
    SPINE_10_TASK_44_CADENCE_PILOT_PENDING.
"""

from __future__ import annotations

import logging
from typing import List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


class IdentityStabilitySweepTask(DailyStrengtheningTask):
    """Daily sweep over recently-active buyers — increments the
    launch-gate snapshot accumulator's identity-collapse counter
    so RED criterion #4 (``check_posterior_pathology``) can fire.
    """

    @property
    def name(self) -> str:
        return "identity_stability_sweep"

    @property
    def schedule_hours(self) -> List[int]:
        # 04:00 UTC slot — alongside Task 41 (OPE estimator); both
        # populate state Task 42 (05:00) reads. Order between Task 41
        # and Task 44 doesn't matter (different state surfaces).
        return [4]

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        # --- Lazy imports ---
        try:
            from adam.api.stackadapt.decision_cache import (
                get_decision_cache,
            )
            from adam.intelligence.identity_stability_sweep import (
                sweep_active_buyers,
            )
            from adam.intelligence.red_criteria_snapshot import (
                get_red_snapshot,
            )
        except Exception as exc:
            result.success = False
            result.details["error"] = f"import failed: {exc}"
            return result

        decision_cache = None
        try:
            decision_cache = get_decision_cache()
        except Exception as exc:
            result.details["skipped"] = f"no_decision_cache: {exc}"
            return result

        if decision_cache is None:
            result.details["skipped"] = "no_decision_cache"
            return result

        snapshot = None
        try:
            snapshot = get_red_snapshot()
        except Exception as exc:
            logger.debug(
                "Task 44 snapshot accumulator unavailable: %s", exc,
            )

        try:
            sweep_result = sweep_active_buyers(
                decision_cache=decision_cache,
                snapshot=snapshot,
            )
        except Exception as exc:
            result.success = False
            result.details["error"] = f"sweep failed: {exc}"
            return result

        result.details["n_active"] = sweep_result.n_active
        result.details["n_collapsed"] = sweep_result.n_collapsed
        result.details["collapse_fraction"] = sweep_result.collapse_fraction
        result.details["snapshot_incremented"] = (
            snapshot is not None and sweep_result.n_active > 0
        )

        logger.info(
            "Task 44 identity-stability sweep: n_active=%d n_collapsed=%d "
            "fraction=%.3f",
            sweep_result.n_active,
            sweep_result.n_collapsed,
            sweep_result.collapse_fraction,
        )
        return result
