"""
Task 18: Composite Alignment Weight Recalibration
====================================================

Runs the `RecalibrationPipeline` from `adam/retargeting/engines/recalibration.py`
against recent bilateral edges to detect and correct weight drift in the
composite_alignment computation.

Why this matters
----------------
The Session 34-2 diagnostic found that `composite_alignment` was *inverted*
(r = −0.29 with conversion) because 11 of 25 dimensions had wrong-sign weights.
The v6 fix applied one-time logistic regression to 1,492 LUXY Ride edges and
produced data-calibrated weights with r = +0.86. That fix is static and only
applies to the category mix it was calibrated on.

**Without periodic recalibration, composite_alignment will drift back toward
the inverted state** as new data accumulates from different categories or
outcome patterns. The drift is silent — it shows up in outcome data weeks
later, not in any alert. This task closes the loop by automatically
re-running logistic regression on the latest edge data and deploying new
weights when they improve AUC by more than the minimum threshold.

Integration caveat (known follow-up)
------------------------------------
As of Stage 1 of the audit-driven wiring work, `RecalibrationPipeline`
writes new weights to `data/calibration_history.json` and to its own
`self.current_weights`, but no other module in the codebase currently
imports or reads those weights. A grep for `CURRENT_V6_WEIGHTS` returns
only references inside `recalibration.py` itself. This means the
composite_alignment computation elsewhere in the codebase is reading
weights from some other source — and the recalibration pipeline's output
is observable (via the history file and this task's logs) but is not
yet consumed by live scoring.

This task's job is to get the pipeline *running* so we can detect drift
and have the corrected weights ready. Actually consuming those weights
in `composite_alignment` computation is a Stage 2 wiring item that
requires identifying where the live weights are read from and routing
them through `RecalibrationPipeline.get_weights()`.

Schedule
--------
- Runs weekly (every 168 hours)
- UTC hour 5 (5 AM) on Sundays — same-day run window as Tasks 5-8
- Frequency gate ensures it does not run more than once per week even
  if the scheduler checks more often

Consumption pathway
-------------------
- Writes `CalibrationResult` to `data/calibration_history.json`
- Logs deployed weights to stdout/structured logger
- (Future) writes to Redis for live consumption by composite_alignment code

Graceful degradation
--------------------
- If Neo4j is unavailable, returns success=True with items_processed=0
- If too few edges exist (<200), returns insufficient_data and skips
- Never raises; failures are recorded in `result.errors`
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


# Minimum edges required before recalibration attempts a run.
# Below this, the RecalibrationPipeline itself returns insufficient_data.
MIN_EDGES_FOR_CALIBRATION = 200

# Cap on edges pulled from Neo4j per run. Logistic regression on 10k+
# edges is fast, but we do not need more to get a stable calibration,
# and pulling more is wasteful.
MAX_EDGES_TO_FETCH = 10_000


class RecalibrationTask(DailyStrengtheningTask):
    """Weekly recalibration of composite_alignment weights."""

    @property
    def name(self) -> str:
        return "composite_alignment_recalibration"

    @property
    def schedule_hours(self) -> List[int]:
        # 5 AM UTC — same morning window as Tasks 5-8. The frequency_hours
        # gate below ensures it only runs once per week even though the
        # scheduler checks daily.
        return [5]

    @property
    def frequency_hours(self) -> int:
        # Weekly. Composite_alignment weights do not change fast enough
        # to justify more frequent runs, and logistic regression over
        # 10k+ edges has a real (if small) cost.
        return 24 * 7

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        # Lazy imports so the task file can be imported even when the
        # retargeting subsystem is partially unavailable during tests.
        try:
            from adam.retargeting.engines.recalibration import (
                RecalibrationPipeline,
            )
        except Exception as exc:
            logger.warning(
                "RecalibrationTask: could not import RecalibrationPipeline: %s", exc
            )
            result.errors += 1
            result.details["import_error"] = str(exc)
            return result

        # Fetch edges from Neo4j. Gracefully degrade when Neo4j is not
        # reachable — this task must not crash the scheduler on infra
        # outages.
        edges = await self._fetch_bilateral_edges()
        result.details["edges_fetched"] = len(edges)

        if len(edges) < MIN_EDGES_FOR_CALIBRATION:
            logger.info(
                "RecalibrationTask: skipping — %d edges is below the "
                "minimum of %d. (No drift risk yet; more data needed.)",
                len(edges), MIN_EDGES_FOR_CALIBRATION,
            )
            result.details["skipped"] = "insufficient_data"
            return result

        # Run the pipeline. It validates data sufficiency internally,
        # fits new weights via logistic regression, computes AUC, and
        # only deploys if the improvement exceeds the threshold.
        try:
            pipeline = RecalibrationPipeline()
            calibration_result = pipeline.recalibrate(
                edges=edges,
                category="all",  # Cross-category weights for the default run
            )
        except Exception as exc:
            logger.exception("RecalibrationTask: pipeline failed")
            result.errors += 1
            result.success = False
            result.details["pipeline_error"] = str(exc)
            return result

        # Record outcome
        result.items_processed = calibration_result.n_edges
        result.items_stored = 1 if calibration_result.deployed else 0
        result.details["category"] = calibration_result.category
        result.details["n_converted"] = calibration_result.n_converted
        result.details["current_auc"] = calibration_result.current_auc
        result.details["new_auc"] = calibration_result.new_auc
        result.details["auc_improvement"] = calibration_result.auc_improvement
        result.details["deployed"] = calibration_result.deployed
        result.details["reason"] = calibration_result.reason
        result.details["sign_flips"] = calibration_result.sign_flips

        if calibration_result.deployed:
            logger.info(
                "RecalibrationTask: new weights deployed. AUC %.4f → %.4f "
                "(Δ %+.4f), %d sign flips. Output in data/calibration_history.json.",
                calibration_result.current_auc,
                calibration_result.new_auc,
                calibration_result.auc_improvement,
                calibration_result.sign_flips,
            )
        else:
            logger.info(
                "RecalibrationTask: no deployment (%s). AUC %.4f → %.4f.",
                calibration_result.reason,
                calibration_result.current_auc,
                calibration_result.new_auc,
            )

        return result

    async def _fetch_bilateral_edges(self) -> List[Dict[str, Any]]:
        """Fetch recent bilateral edges from Neo4j for recalibration.

        Returns a list of dicts with alignment dimensions + outcome label.
        Returns an empty list on any failure — the caller treats that as
        insufficient data and skips the run.
        """
        try:
            from adam.core.dependencies import get_infrastructure
        except Exception as exc:
            logger.debug("RecalibrationTask: infrastructure import failed: %s", exc)
            return []

        try:
            infra = await get_infrastructure()
            driver = getattr(infra, "neo4j_driver", None) or getattr(infra, "neo4j", None)
            if driver is None:
                logger.debug("RecalibrationTask: no Neo4j driver in infrastructure")
                return []
        except Exception as exc:
            logger.debug(
                "RecalibrationTask: could not obtain Neo4j driver: %s", exc
            )
            return []

        # Cypher query: pull BRAND_CONVERTED edges with alignment
        # dimensions and an outcome label. The alignment dimensions are
        # stored as edge properties (matching COMPOSITE_DIMENSIONS in
        # recalibration.py). Outcome label comes from the edge's
        # `conversion_outcome` property or defaults to empty.
        query = (
            "MATCH (b:Buyer)-[e:BRAND_CONVERTED]->(p:Product) "
            "WHERE e.conversion_outcome IS NOT NULL "
            "RETURN properties(e) AS edge_props "
            "ORDER BY e.updated_at DESC "
            "LIMIT $limit"
        )

        try:
            async with driver.session() as session:
                cursor = await session.run(query, limit=MAX_EDGES_TO_FETCH)
                records = await cursor.data()
        except Exception as exc:
            logger.debug(
                "RecalibrationTask: Neo4j query failed: %s — skipping run.", exc
            )
            return []

        edges: List[Dict[str, Any]] = []
        for record in records:
            props = record.get("edge_props") or {}
            if not isinstance(props, dict):
                continue
            # Make sure the outcome label is accessible under the key
            # the pipeline expects.
            if "outcome" not in props and "conversion_outcome" in props:
                props["outcome"] = props["conversion_outcome"]
            edges.append(props)

        return edges
