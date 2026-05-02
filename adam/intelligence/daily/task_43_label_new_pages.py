"""
Task 43: Daily Claude API label generation for new DecisionTrace pages

Original-Slice-B: Task 40 docstring (lines 62-67) explicitly named
this as the missing sibling — Task 40 nightly RETRAINS dual-eval
B/C models on accumulated :GoalStateLabel nodes; this task
GENERATES the labels for newly-seen page_urls so the retraining
loop can compound from production traffic, not just manual labels.

Closes the autonomous label-accumulation loop:

    Day N — production cascade emits DecisionTraces with page_url
        ↓ Slice 5 archive_trace_to_neo4j writes :DecisionTrace nodes
    Day N 02:30 UTC — Task 43 fires (THIS TASK)
        ↓ scan distinct page_urls from recent traces
        ↓ exclude already-labeled URLs
        ↓ generate_labels_bulk via Claude API
        ↓ persist :GoalStateLabel nodes
    Day N 03:00 UTC — Task 40 fires
        ↓ warm_dual_eval_from_neo4j retrains on the larger labeled set

Schedule rationale: 02:30 UTC sits BEFORE Task 40 (03:00) so new
labels are persisted before retraining. Sits AFTER Task 38 hourly
trace drain (last drain ~24:50 prior day, well before 02:30) so
the Neo4j archive has the most recent traces visible to the scan.

WHY THIS EXISTS

Without this task, the directive's "Claude as the slow brain"
(Section 6 line 730) loop only fires on manually-uploaded labels
or on whatever external pipeline an operator runs. Production
traffic accumulates traces but no labels — the dual-eval cascade
stays at its bootstrap label count forever. This task is the
autonomous compound-from-production-data wire.

NOT IN SCOPE (named successors)

  * Per-domain rate-limiting on the Claude API. The generator's
    rate_limit_delay_seconds parameter handles this; v0.1 uses
    a small 0.1s default for LUXY's expected scale (~50 new pages/
    day). Sibling slice if rate climbs.
  * Re-labeling stale labels (e.g., when the LUXY goal-state
    inventory expands). For v0.1 we treat existing labels as
    immutable — sibling slice (label refresh task) when goal-
    state inventory changes warrant it.
  * Smart batching by domain / category for prompt-cache locality.
    v0.1 processes pages individually; the prompt cache TTL on the
    system block (1h) is more than enough at LUXY's volume.

DISCIPLINE (B3-LUXY a/b/c/d)
============================

(a) Citations: directive Section 6.2 (Claude API as offline slow
    brain — daily cadence specified there); Slice 18
    GoalStateLabelGenerator (e3a25f7); Original-Slice-A (page_url
    on DecisionTrace); Task 40 docstring lines 62-67 (named-
    successor reference).

(b) Tests pin: name + schedule_hours + frequency_hours; execute()
    routes to scan → generate → persist; no driver → skipped;
    no new pages → succeeds with outcome=no_new_pages (cold-start);
    pages found → labels persisted; existing labels skipped on the
    scan (no double-labeling); registered in scheduler.

(c) calibration_pending=True. 02:30 UTC slot conservative (after
    Task 36 02:00 hierarchical refit, before Task 40 03:00 dual-
    eval re-warm). Lookback default 7 days inherited from sensible
    cron-discipline default. A14 flag:
    SPINE_5_TASK_43_CADENCE_PILOT_PENDING.
"""

from __future__ import annotations

import logging
from typing import List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


# Lookback window for new-page scan. 7 days is generous — most
# DecisionTraces are TTL-archived to Neo4j within hours, and the
# label-generation cost is small per URL. Sibling slice can tune.
_LABEL_SCAN_LOOKBACK_DAYS: int = 7

# Cap to avoid runaway cost on a backlog. At LUXY's expected ~50 new
# pages/day this never bites; protects against e.g. a misconfigured
# trace emitter producing thousands of synthetic page_urls.
_MAX_PAGES_PER_RUN: int = 500

# Inter-request delay to be friendly to the Claude API. SDK auto-
# retries 429s with backoff; this just reduces retry cost on tight
# rate-limit tiers.
_RATE_LIMIT_DELAY_SECONDS: float = 0.1


# Cypher: distinct page_urls in recent DecisionTraces that have NO
# :GoalStateLabel for that URL. Original-Slice-A persisted page_url
# as a first-class scalar property on :DecisionTrace, so the scan
# does not need to parse payload_json.
_SCAN_NEW_PAGES_CYPHER: str = (
    "MATCH (d:DecisionTrace) "
    "WHERE d.timestamp >= $cutoff_ts "
    "  AND d.page_url IS NOT NULL "
    "  AND d.page_url <> '' "
    "  AND NOT EXISTS { "
    "    MATCH (l:GoalStateLabel) WHERE l.page_url = d.page_url "
    "  } "
    "RETURN DISTINCT d.page_url AS page_url "
    "LIMIT $limit"
)


class LabelNewPagesTask(DailyStrengtheningTask):
    """Daily Claude-API label-generation pass over new DecisionTrace
    page_urls. Persists :GoalStateLabel nodes that Task 40 retraining
    consumes."""

    @property
    def name(self) -> str:
        return "label_new_pages"

    @property
    def schedule_hours(self) -> List[int]:
        # 02:30 UTC slot — before Task 40 (03:00) re-warm so the
        # retrain sees today's new labels. The base scheduler runs
        # tasks at the START of the configured hour, so 02 is the
        # closest viable slot before 03 — sub-hour scheduling is
        # sibling slice (would need scheduler enhancement).
        return [2]

    @property
    def frequency_hours(self) -> int:
        return 24

    async def execute(self) -> TaskResult:
        import time as _time

        result = TaskResult(task_name=self.name, success=True)

        # --- Lazy imports ---
        try:
            from adam.intelligence.goal_state_label_generator import (
                GoalStateLabelGenerator,
                persist_label_to_neo4j,
            )
        except Exception as exc:
            result.success = False
            result.details["error"] = (
                f"label generator import failed: {exc}"
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
            logger.debug("Task 43 infrastructure unavailable: %s", exc)

        if neo4j_driver is None:
            result.details["skipped"] = "no_neo4j_driver"
            return result

        # --- Scan for new pages ---
        cutoff_ts = _time.time() - _LABEL_SCAN_LOOKBACK_DAYS * 86400.0
        new_page_urls: List[str] = []
        try:
            async with neo4j_driver.session() as session:
                rows = await session.run(
                    _SCAN_NEW_PAGES_CYPHER,
                    cutoff_ts=float(cutoff_ts),
                    limit=int(_MAX_PAGES_PER_RUN),
                )
                async for record in rows:
                    url = record.get("page_url")
                    if url:
                        new_page_urls.append(str(url))
        except Exception as exc:
            result.success = False
            result.details["error"] = (
                f"new-page scan failed: {exc}"
            )
            return result

        result.details["lookback_days"] = _LABEL_SCAN_LOOKBACK_DAYS
        result.details["n_new_pages"] = len(new_page_urls)

        if not new_page_urls:
            result.details["outcome"] = "no_new_pages"
            logger.info(
                "Task 43 label-new-pages: no new pages in last %d days "
                "(autonomous-label-loop quiescent)",
                _LABEL_SCAN_LOOKBACK_DAYS,
            )
            return result

        # --- Generate labels via Claude API ---
        generator = GoalStateLabelGenerator()
        if not generator.is_configured():
            # No API key — graceful skip rather than fail.
            result.details["outcome"] = "skipped_unconfigured"
            result.details["skipped"] = "anthropic_api_key_missing"
            logger.info(
                "Task 43 label-new-pages: %d new pages waiting but "
                "ANTHROPIC_API_KEY unset — skipped",
                len(new_page_urls),
            )
            return result

        pages = [{"page_url": url} for url in new_page_urls]
        try:
            labels = generator.generate_labels_bulk(
                pages,
                rate_limit_delay_seconds=_RATE_LIMIT_DELAY_SECONDS,
            )
        except Exception as exc:
            result.success = False
            result.details["error"] = (
                f"generate_labels_bulk failed: {exc}"
            )
            return result

        result.details["n_labels_generated"] = len(labels)
        result.items_processed = len(new_page_urls)

        # --- Persist labels ---
        n_persisted = 0
        for label in labels:
            try:
                ok = await persist_label_to_neo4j(label, neo4j_driver)
                if ok:
                    n_persisted += 1
            except Exception as exc:
                logger.warning(
                    "Task 43: persist_label_to_neo4j failed for "
                    "page_url=%s: %s", label.page_url, exc,
                )

        result.items_stored = n_persisted
        result.details["n_labels_persisted"] = n_persisted
        result.details["outcome"] = (
            "persisted" if n_persisted > 0 else "no_labels_persisted"
        )

        logger.info(
            "Task 43 label-new-pages: %d new pages → %d labels "
            "generated → %d persisted",
            len(new_page_urls), len(labels), n_persisted,
        )

        return result
