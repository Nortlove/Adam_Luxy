"""
Task 38: DecisionTrace daily drain — Spine #6 storage operationalization

Closes the operational loop on Spine #6 (directive line 248).
The cascade emits ``DecisionTrace`` records into an in-memory log
synchronously (cascade producer wiring, ab10f26). Without a scheduled
drain consumer, those traces accumulate in memory and are lost on
process restart — exactly the substrate-without-consumer antipattern
Appendix E rule A flags.

This task is the consumer. It runs hourly, draining the in-memory log
into the Spine #6 storage tiers:

    in-memory log (decision_trace_emitter.InMemoryDecisionTraceLog)
            ↓ Task 38 drain (this module)
    Redis hot cache (decision_trace_store.store_trace)
    + Neo4j long-term (decision_trace_neo4j.archive_trace_to_neo4j)
            ↓
    Defensive Reasoning surface (Spine #13, sibling slice) reads
    from Redis (hot path) or Neo4j (beyond TTL window)

Schedule: hourly (every UTC hour). The scheduler loop polls every 5
minutes, so the actual cadence floor is 5min; the hourly is_due()
check ensures we drain at most once per hour aligned to the hour
boundary.

Cadence rationale: at 10,000 in-memory log capacity, hourly drain
covers up to ~2.78 traces/sec. Beyond that decision rate, the
producer's deque starts evicting oldest traces (the eviction counter
is logged at WARNING). Calibration-pending: pilot data will inform
whether sub-hourly cadence (via long-running async drain worker —
sibling slice) is needed.

Soft-fail discipline:
  * Infrastructure unavailable → skipped with detail
  * Drain function exception → result.success=False with error detail
  * Per-trace storage failures inside drain are counted but don't
    abort the batch (handled by drain_to_storage itself)

Discipline (B3-LUXY a/b/c/d)
============================

(a) Citation: directive Spine #6 line 248 (Redis hot + Neo4j archival).
    Operationalization pattern follows existing Daily Strengthening
    Tasks (Task 34/35/36 hierarchy refit / causal forest / HMC
    reconcile) — same base class, same scheduler registration.

(b) Tests pin: name + schedule_hours + frequency_hours; execute()
    drains pending traces successfully into mocked storage; soft-fail
    on missing infra; drain exception → failed result; registration
    in scheduler.

(c) calibration_pending=True. Hourly cadence + 10k in-memory
    capacity bound the system to ~10k traces/hour without eviction.
    LUXY pilot decision rate will calibrate. A14 flag:
    SPINE_6_DRAIN_TASK_CADENCE_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):
    * Sub-hourly cadence via long-running async drain worker.
      The Daily Strengthening Tasks scheduler is hour-granularity.
      For higher decision rates, a dedicated drain worker (looping
      every N seconds) replaces the hourly task. Sibling slice if
      pilot calibration shows hourly is too slow.
    * Per-trace replay-after-failure logic. Currently traces that
      fail to store are dropped from the in-memory log (drain pops
      before write). A retry-with-backoff queue is its own slice if
      pilot data shows storage flakiness.
    * Cross-region replication / cold-storage migration of Neo4j
      archived traces — operational, out of scope.
"""

from __future__ import annotations

import logging
from typing import List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


# A14 SPINE_6_DRAIN_TASK_CADENCE_PILOT_PENDING
DRAIN_BATCH_MAX_ITEMS: int = 10_000
"""Per-call cap on traces drained. At hourly cadence with 10k
in-memory log capacity, this fully drains a saturated log per call.
LUXY pilot will calibrate against actual decision rate."""


class DecisionTraceDrainTask(DailyStrengtheningTask):
    """Hourly drain of in-memory DecisionTrace log to Redis + Neo4j."""

    @property
    def name(self) -> str:
        return "decision_trace_drain"

    @property
    def schedule_hours(self) -> List[int]:
        # Every hour (UTC). The scheduler loop checks every 5 minutes;
        # is_due() additionally enforces frequency_hours.
        return list(range(24))

    @property
    def frequency_hours(self) -> int:
        return 1

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        # --- Resolve drain function (lazy import) ---
        try:
            from adam.intelligence.decision_trace_emitter import (
                drain_to_storage,
                get_log,
            )
        except Exception as exc:
            result.success = False
            result.details["error"] = f"drain_to_storage import failed: {exc}"
            return result

        # --- Resolve infrastructure (soft-fail per layer) ---
        redis_client = None
        neo4j_driver = None
        try:
            from adam.core.dependencies import get_infrastructure
            infra = await get_infrastructure()
            try:
                redis_client = infra.redis
            except Exception as exc:
                logger.debug(
                    "Task 38 redis client unavailable: %s", exc,
                )
            try:
                neo4j_driver = infra.neo4j
            except Exception as exc:
                logger.debug(
                    "Task 38 neo4j driver unavailable: %s", exc,
                )
        except Exception as exc:
            logger.debug("Task 38 infrastructure unavailable: %s", exc)

        if redis_client is None and neo4j_driver is None:
            # Nothing to write to. Don't drain — the in-memory log
            # would lose traces with no destination. Better to leave
            # them queued for a future drain when infra recovers.
            result.details["skipped"] = "no_storage_clients"
            result.details["log_size_at_skip"] = len(get_log())
            return result

        # --- Drain ---
        log_size_before = len(get_log())
        try:
            drained, n_redis, n_neo4j = await drain_to_storage(
                redis_client=redis_client,
                neo4j_driver=neo4j_driver,
                max_items=DRAIN_BATCH_MAX_ITEMS,
            )
        except Exception as exc:
            result.success = False
            result.details["error"] = f"drain_to_storage failed: {exc}"
            return result

        result.items_processed = drained
        result.items_stored = max(n_redis, n_neo4j)  # at least one tier wrote
        result.details.update({
            "log_size_before": log_size_before,
            "log_size_after": len(get_log()),
            "drained": drained,
            "redis_writes_ok": n_redis,
            "neo4j_writes_ok": n_neo4j,
            "redis_available": redis_client is not None,
            "neo4j_available": neo4j_driver is not None,
        })

        # If drained > 0 and BOTH tiers had clients but BOTH failed
        # to write any → mark unsuccessful. Partial-write success
        # (one tier wrote, the other failed all) is acceptable per
        # drain_to_storage's per-trace soft-fail discipline.
        if drained > 0 and redis_client is not None and neo4j_driver is not None:
            if n_redis == 0 and n_neo4j == 0:
                result.success = False
                result.details["error"] = (
                    "drained traces but both storage tiers wrote zero"
                )

        return result
