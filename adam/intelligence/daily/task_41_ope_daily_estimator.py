"""
Task 41: Daily OPE estimator — Spine #6 off-policy evaluator runner

Closes audit Tier 1 #5 (consumer side): ``adam/intelligence/ope.py``
ships full IPS/DR/SNIPS estimators + ``policy_gate`` + the loader
``load_ope_samples_from_neo4j``, with zero production callers. Slice
6's :AdOutcome writer (sibling of this task) populates the input
schema; this task is the consumer that actually computes the
estimates and persists daily snapshots so the directive's "every
served impression contributes to evaluating every arm" multiplier
(line 244) becomes operational, not aspirational.

Schedule: 04:00 UTC nightly. Sits AFTER Task 40 (03:00 dual-eval
re-warm) and AFTER Task 38's hourly trace drain has already pushed
the prior-day decisions into Neo4j. By 04:00 the prior 24h
(propensity, action, reward) rows are in the graph and stable.

Cadence rationale: OPE estimators are O(N) on samples; daily on
LUXY-scale (~30K decisions/week → ~5K samples/day) is microseconds
of compute. Sub-daily would not change the decision-time policy
(estimates inform CI/CD gates, not the live cascade).

OUTPUTS

  * Per-window IPS / SNIPS / DR estimates with normal-approx CIs
  * :OPEDailyEstimate Neo4j node — one per task run — for trending /
    dashboard surfaces. Idempotent on (date, lookback_days) key.
  * Surfaces estimates on result.details for log inspection.

NOT IN SCOPE (named successors)

  * Policy-gate firing on a CANDIDATE policy. ``policy_gate(candidate,
    current)`` requires a candidate DR estimate — we have one policy
    today (the cascade itself), so the gate awaits a CI/CD path
    that promotes a candidate (e.g., a configuration A/B with
    distinct ts_propensity logging). v0.1 task computes ONLY the
    current-policy estimate.
  * SwitchDR (``estimate_switch_dr``) — requires a switching policy
    distinct from the current. Sibling slice with the policy-gate
    wire.
  * Per-cohort / per-archetype estimates. Spine #7 cohort discovery
    BLOCKED on Loop B; v0.1 estimator runs on the full sample pool.
  * Prometheus gauges for the daily estimates. Sibling observability
    slice that surfaces the snapshot to /metrics.
  * Replay / backfill window beyond the loader's default 90 days.
    Operational sibling slice.

DISCIPLINE (B3-LUXY a/b/c/d)
============================

(a) Citations: directive Section 5.2 Step 9 line 710 (off-policy
    evaluator update); ope.py existing primitives (IPS/SNIPS/DR/
    policy_gate); audit 2026-05-01 Tier 1 #5.

(b) Tests pin: name + schedule_hours + frequency_hours; execute()
    routes to load_ope_samples_from_neo4j + estimate_dr +
    estimate_ips + estimate_snips; outcome propagates to details;
    no driver → skipped; no samples → succeeds with empty estimate
    detail (cold-start, not failure); snapshot Cypher idempotent
    on (date, lookback_days).

(c) calibration_pending=True. 04:00 UTC slot conservative (after
    Task 40 03:00). 90-day default lookback inherited from
    ``load_ope_samples_from_neo4j``. Pilot may calibrate. A14 flag:
    SPINE_6_TASK_41_CADENCE_PILOT_PENDING.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


_OPE_DAILY_ESTIMATE_NODE: str = "OPEDailyEstimate"
_OPE_DAILY_LOOKBACK_DAYS: int = 90


_SNAPSHOT_CYPHER: str = (
    f"MERGE (e:{_OPE_DAILY_ESTIMATE_NODE} "
    "{date: $date, lookback_days: $lookback_days}) "
    "SET e.n_samples = $n_samples, "
    "    e.n_known = $n_known, "
    "    e.ips_point = $ips_point, "
    "    e.ips_lower = $ips_lower, "
    "    e.ips_upper = $ips_upper, "
    "    e.snips_point = $snips_point, "
    "    e.snips_lower = $snips_lower, "
    "    e.snips_upper = $snips_upper, "
    "    e.dr_point = $dr_point, "
    "    e.dr_lower = $dr_lower, "
    "    e.dr_upper = $dr_upper, "
    "    e.computed_at_ts = $computed_at_ts "
    "RETURN e.date AS date"
)


class OPEDailyEstimatorTask(DailyStrengtheningTask):
    """Daily OPE estimator. Loads ``:DecisionContext-[:HAD_OUTCOME]->:
    AdOutcome`` rows, computes IPS / SNIPS / DR estimates with normal-
    approx CIs, persists a :OPEDailyEstimate snapshot for trending,
    and surfaces results on ``result.details``."""

    @property
    def name(self) -> str:
        return "ope_daily_estimator"

    @property
    def schedule_hours(self) -> List[int]:
        # 04:00 UTC nightly — after Task 40 (03:00) so dual-eval is
        # already re-warmed if labels arrived overnight.
        return [4]

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        # --- Lazy imports ---
        try:
            from adam.intelligence.ope import (
                estimate_dr,
                estimate_ips,
                estimate_snips,
                load_ope_samples_from_neo4j,
            )
        except Exception as exc:
            result.success = False
            result.details["error"] = f"ope import failed: {exc}"
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
            logger.debug("Task 41 infrastructure unavailable: %s", exc)

        if neo4j_driver is None:
            result.details["skipped"] = "no_neo4j_driver"
            return result

        # --- Load OPE samples ---
        try:
            samples = load_ope_samples_from_neo4j(
                driver=neo4j_driver,
                days_lookback=_OPE_DAILY_LOOKBACK_DAYS,
                pscore_known_only=True,  # production-grade only
            )
        except Exception as exc:
            result.success = False
            result.details["error"] = (
                f"load_ope_samples_from_neo4j failed: {exc}"
            )
            return result

        n_samples = len(samples)
        n_known = sum(1 for s in samples if getattr(s, "pscore_known", False))

        result.details["n_samples"] = n_samples
        result.details["n_known"] = n_known
        result.details["lookback_days"] = _OPE_DAILY_LOOKBACK_DAYS

        if n_samples == 0:
            # Cold-start / pre-pilot — no signal yet. Not a failure.
            result.details["outcome"] = "no_samples"
            logger.info(
                "Task 41 OPE estimator: no samples in last %d days "
                "(cold-start; succeeds without estimate)",
                _OPE_DAILY_LOOKBACK_DAYS,
            )
            return result

        # --- Compute estimates ---
        # v0.1 target policy: uniform identity (returns 1.0 for any
        # action). Yields IPS = avg(reward / propensity) — the
        # unbiased expected-reward estimate of the logging policy
        # itself. DR's reward_model uses a constant 0.5 baseline (the
        # uninformative prior). Honest tag (d): DML cross-fit reward
        # model from M2 is the production sibling per ope.py:272.
        # Action space derived from observed sample actions.
        def _identity_policy(context, action):  # type: ignore[no-untyped-def]
            return 1.0

        def _baseline_reward_model(context, action):  # type: ignore[no-untyped-def]
            return 0.5

        action_space = sorted({s.action for s in samples if s.action})

        try:
            ips_result = estimate_ips(samples, _identity_policy)
            snips_result = estimate_snips(samples, _identity_policy)
            dr_result = estimate_dr(
                samples,
                _identity_policy,
                _baseline_reward_model,
                action_space,
            )
        except Exception as exc:
            result.success = False
            result.details["error"] = f"estimator failed: {exc}"
            return result

        result.details.update({
            "outcome": "computed",
            "ips_point": ips_result.point_estimate,
            "ips_lower": ips_result.ci_lower,
            "ips_upper": ips_result.ci_upper,
            "snips_point": snips_result.point_estimate,
            "snips_lower": snips_result.ci_lower,
            "snips_upper": snips_result.ci_upper,
            "dr_point": dr_result.point_estimate,
            "dr_lower": dr_result.ci_lower,
            "dr_upper": dr_result.ci_upper,
        })
        result.items_processed = n_samples
        result.items_stored = 0  # set to 1 if snapshot writes succeed

        # --- Persist snapshot for trending ---
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            params = {
                "date": today,
                "lookback_days": _OPE_DAILY_LOOKBACK_DAYS,
                "n_samples": int(n_samples),
                "n_known": int(n_known),
                "ips_point": float(ips_result.point_estimate),
                "ips_lower": float(ips_result.ci_lower),
                "ips_upper": float(ips_result.ci_upper),
                "snips_point": float(snips_result.point_estimate),
                "snips_lower": float(snips_result.ci_lower),
                "snips_upper": float(snips_result.ci_upper),
                "dr_point": float(dr_result.point_estimate),
                "dr_lower": float(dr_result.ci_lower),
                "dr_upper": float(dr_result.ci_upper),
                "computed_at_ts": float(time.time()),
            }
            with neo4j_driver.session() as session:
                session.run(_SNAPSHOT_CYPHER, **params)
            result.items_stored = 1
        except Exception as exc:
            logger.warning(
                "Task 41 OPE estimator: snapshot write failed: %s", exc,
            )
            result.details["snapshot_write_error"] = str(exc)

        logger.info(
            "Task 41 OPE estimator: n=%d ips=%.4f snips=%.4f dr=%.4f",
            n_samples,
            ips_result.point_estimate,
            snips_result.point_estimate,
            dr_result.point_estimate,
        )

        return result
