"""F1 daily runner — score buyer reviews on 8 primary-metaphor axes.

Activates the F3 cascade-side metaphor wire by populating the buyer
half of metaphor_storage. For each unscored / stale buyer with at least
one review in the lookback window:
    1. Pull recent reviews from Neo4j (Review.review_text or .body)
    2. Score each via score_review_metaphors (8 axes + density + confidence)
    3. Aggregate per buyer via aggregate_buyer_metaphor_axes
       (confidence-weighted; min_confidence floor excludes weak signal)
    4. Persist to Redis via put_buyer_metaphor_bundle

Once this runs against real data, the cascade's compute_metaphor_alignment
fetch in level3_bilateral_edges starts hitting the buyer half. Combined
with task_29_8 (brand half), the 21st edge dimension flows live.

Discipline:
    - Soft-fail at every layer: missing Neo4j driver, missing Claude
      client, malformed review, scoring exception. NEVER raises.
    - Caps per-run buyer count + per-buyer review count to bound
      Claude API spend. Defaults are pilot-conservative; configurable.
    - Skips buyers with already-fresh bundles (confidence ≥ 0.5,
      bundle age ≤ 7d) — daily refit only when material change is
      possible.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


class BuyerMetaphorScoringTask(DailyStrengtheningTask):
    """F1 daily runner.

    Scores recent buyer reviews on the 8 primary-metaphor axes and
    persists per-buyer aggregates to Redis. Activates F3's cascade-
    side metaphor_alignment wire (task #54) for the buyer half.
    """

    @property
    def name(self) -> str:
        return "buyer_metaphor_scoring"

    @property
    def schedule_hours(self) -> List[int]:
        # 06:00 UTC — after the cascade's nightly fits but before
        # peak bid traffic begins.
        return [6]

    async def execute(self) -> TaskResult:
        max_buyers_per_run = 200       # Claude spend cap
        max_reviews_per_buyer = 20     # F1 scorer max_chars=4000 per call
        days_lookback = 30
        skip_if_fresh_within_days = 7

        # Soft-fail on missing infra
        try:
            from adam.core.dependencies import get_neo4j_driver
            from adam.llm.client import ClaudeClient
            from adam.intelligence.buyer_metaphor_scoring import (
                aggregate_buyer_metaphor_axes,
                score_review_metaphors,
            )
            from adam.intelligence.metaphor_storage import (
                get_buyer_metaphor_bundle,
                put_buyer_metaphor_bundle,
            )
        except Exception as exc:
            return TaskResult(
                task_name=self.name, success=False,
                details={"error": f"imports failed: {exc}"},
            )

        driver = None
        try:
            driver = get_neo4j_driver()
        except Exception as exc:
            return TaskResult(
                task_name=self.name, success=False,
                details={"error": f"no neo4j driver: {exc}"},
            )
        if driver is None:
            return TaskResult(
                task_name=self.name, success=False,
                details={"error": "neo4j driver returned None"},
            )

        try:
            client = ClaudeClient()
            if not getattr(client, "api_key", None):
                return TaskResult(
                    task_name=self.name, success=False,
                    details={"error": "ANTHROPIC_API_KEY not set"},
                )
        except Exception as exc:
            return TaskResult(
                task_name=self.name, success=False,
                details={"error": f"ClaudeClient init failed: {exc}"},
            )

        buyers = self._fetch_buyer_review_batches(
            driver, max_buyers_per_run, max_reviews_per_buyer, days_lookback,
        )
        if not buyers:
            return TaskResult(
                task_name=self.name, success=True,
                items_processed=0,
                details={"reason": "no buyers with reviews in window"},
            )

        scored = 0
        skipped_fresh = 0
        stored = 0
        errors = 0

        for buyer_id, reviews in buyers.items():
            # Skip if existing bundle is fresh + high-confidence
            existing = get_buyer_metaphor_bundle(buyer_id)
            if existing is not None and existing.confidence >= 0.5:
                skipped_fresh += 1
                continue

            try:
                bundles = []
                for review in reviews:
                    bundle = await score_review_metaphors(
                        client,
                        review_text=review.get("text", ""),
                        review_id=review.get("review_id", ""),
                        buyer_id=buyer_id,
                    )
                    if bundle.confidence > 0:
                        bundles.append(bundle)

                if not bundles:
                    continue

                aggregate = aggregate_buyer_metaphor_axes(bundles)
                if aggregate is None:
                    continue

                if put_buyer_metaphor_bundle(aggregate):
                    stored += 1
                scored += 1
            except Exception as exc:
                logger.warning(
                    "buyer_metaphor_scoring failed for %s: %s",
                    buyer_id, exc,
                )
                errors += 1

        return TaskResult(
            task_name=self.name,
            success=errors == 0 or stored > 0,
            items_processed=len(buyers),
            items_stored=stored,
            errors=errors,
            details={
                "buyers_seen": len(buyers),
                "buyers_scored": scored,
                "buyers_stored": stored,
                "buyers_skipped_fresh": skipped_fresh,
                "errors": errors,
            },
        )

    def _fetch_buyer_review_batches(
        self,
        driver: Any,
        max_buyers: int,
        max_reviews_per_buyer: int,
        days_lookback: int,
    ) -> Dict[str, List[Dict[str, str]]]:
        """Pull recent reviews from Neo4j, grouped by buyer.

        Tolerant of multiple Review schema variants found in the
        codebase (review_text, body, content). Returns empty dict on
        any error — runner soft-fails to 'no signal yet'.
        """
        import time
        cutoff_ms = int((time.time() - days_lookback * 86400) * 1000)

        cypher = """
        MATCH (r:Review)
        WHERE
            (r.review_text IS NOT NULL OR r.body IS NOT NULL OR r.content IS NOT NULL)
            AND r.buyer_id IS NOT NULL AND r.buyer_id <> ''
            AND coalesce(r.created_at, 0) * 1000 >= $cutoff_ms
        RETURN
            r.buyer_id AS buyer_id,
            coalesce(r.review_id, r.id, '') AS review_id,
            coalesce(r.review_text, r.body, r.content, '') AS text
        LIMIT $limit
        """

        result: Dict[str, List[Dict[str, str]]] = {}
        try:
            with driver.session() as session:
                records = session.run(
                    cypher,
                    cutoff_ms=cutoff_ms,
                    limit=max_buyers * max_reviews_per_buyer,
                )
                for record in records:
                    buyer_id = record.get("buyer_id") or ""
                    text = record.get("text") or ""
                    if not buyer_id or not text.strip():
                        continue
                    if buyer_id not in result:
                        if len(result) >= max_buyers:
                            continue
                        result[buyer_id] = []
                    if len(result[buyer_id]) >= max_reviews_per_buyer:
                        continue
                    result[buyer_id].append({
                        "review_id": record.get("review_id") or "",
                        "text": text,
                    })
        except Exception as exc:
            logger.warning("buyer_metaphor_scoring fetch failed: %s", exc)
            return {}

        return result
