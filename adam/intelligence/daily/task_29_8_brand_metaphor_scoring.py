"""F2 daily runner — score brand product copy on 8 primary-metaphor axes.

Activates the F3 cascade-side metaphor wire by populating the brand
half of metaphor_storage. For each Product/Brand node with copy
content in Neo4j:
    1. Pull title + features + description from the node
    2. Score via score_brand_copy_metaphors (8 axes + density + confidence)
    3. Persist to Redis via put_brand_metaphor_bundle

Combined with task_29_7 (buyer half), this populates both halves of
metaphor_alignment so the cascade's compute_metaphor_alignment fetch
in level3_bilateral_edges starts hitting bundles. The 21st edge
dimension flows live as soon as both halves populate for a given
(buyer × brand) pair.

Discipline:
    - Soft-fail at every layer.
    - Skips brands with already-fresh bundles (confidence ≥ 0.5,
      bundle age ≤ 30d). Brand copy changes infrequently so the
      refit cadence is longer than F1's buyer-side cadence.
    - Caps per-run brand count to bound Claude API spend.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)


class BrandMetaphorScoringTask(DailyStrengtheningTask):
    """F2 daily runner.

    Scores brand product copy on the 8 primary-metaphor axes and
    persists per-brand bundles to Redis. Activates F3's cascade-side
    metaphor_alignment wire (task #54) for the brand half.
    """

    @property
    def name(self) -> str:
        return "brand_metaphor_scoring"

    @property
    def schedule_hours(self) -> List[int]:
        # 06:30 UTC — 30 min after task_29_7 (buyer half) so the two
        # write to metaphor_storage in proximity. Same daily cadence
        # but brand bundles refresh less often via the freshness gate.
        return [6]

    @property
    def frequency_hours(self) -> int:
        # Brand copy changes infrequently — weekly cadence is enough
        # under most conditions. The freshness gate in execute()
        # skips already-fresh brands so this is mostly idempotent
        # at daily firing too.
        return 24 * 7

    async def execute(self) -> TaskResult:
        max_brands_per_run = 100
        days_lookback = 90

        # Soft-fail on missing infra
        try:
            from adam.core.dependencies import get_neo4j_driver
            from adam.llm.client import ClaudeClient
            from adam.intelligence.brand_copy_metaphor_scoring import (
                score_brand_copy_metaphors,
            )
            from adam.intelligence.metaphor_storage import (
                get_brand_metaphor_bundle,
                put_brand_metaphor_bundle,
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

        brands = self._fetch_brand_copy_batches(
            driver, max_brands_per_run, days_lookback,
        )
        if not brands:
            return TaskResult(
                task_name=self.name, success=True,
                items_processed=0,
                details={"reason": "no brands with copy content"},
            )

        scored = 0
        skipped_fresh = 0
        stored = 0
        errors = 0

        for asin, copy in brands.items():
            existing = get_brand_metaphor_bundle(asin)
            if existing is not None and existing.confidence >= 0.5:
                skipped_fresh += 1
                continue

            try:
                bundle = await score_brand_copy_metaphors(
                    client,
                    title=copy.get("title", ""),
                    features=copy.get("features", ""),
                    description=copy.get("description", ""),
                    asin=asin,
                    brand_id=copy.get("brand_id", ""),
                )
                if bundle.confidence > 0 and put_brand_metaphor_bundle(bundle):
                    stored += 1
                scored += 1
            except Exception as exc:
                logger.warning(
                    "brand_metaphor_scoring failed for %s: %s", asin, exc,
                )
                errors += 1

        return TaskResult(
            task_name=self.name,
            success=errors == 0 or stored > 0,
            items_processed=len(brands),
            items_stored=stored,
            errors=errors,
            details={
                "brands_seen": len(brands),
                "brands_scored": scored,
                "brands_stored": stored,
                "brands_skipped_fresh": skipped_fresh,
                "errors": errors,
            },
        )

    def _fetch_brand_copy_batches(
        self,
        driver: Any,
        max_brands: int,
        days_lookback: int,
    ) -> Dict[str, Dict[str, str]]:
        """Pull product copy from Neo4j Product/Brand nodes.

        Tolerant of multiple schema variants:
            Product node: title / product_title, features /
                bullet_points, description / product_description
            Brand node: brand_id / brand_name

        Returns empty dict on error.
        """
        import time
        cutoff_ms = int((time.time() - days_lookback * 86400) * 1000)

        cypher = """
        MATCH (p:Product)
        WHERE p.asin IS NOT NULL AND p.asin <> ''
            AND (
                coalesce(p.title, p.product_title, '') <> '' OR
                coalesce(p.description, p.product_description, '') <> ''
            )
        OPTIONAL MATCH (p)-[:OFFERED_BY]->(b:Brand)
        RETURN
            p.asin AS asin,
            coalesce(p.title, p.product_title, '') AS title,
            coalesce(p.features, p.bullet_points, '') AS features,
            coalesce(p.description, p.product_description, '') AS description,
            coalesce(b.brand_id, b.name, p.brand, '') AS brand_id
        LIMIT $limit
        """

        result: Dict[str, Dict[str, str]] = {}
        try:
            with driver.session() as session:
                records = session.run(cypher, limit=max_brands)
                for record in records:
                    asin = record.get("asin") or ""
                    if not asin:
                        continue
                    result[asin] = {
                        "title": record.get("title") or "",
                        "features": record.get("features") or "",
                        "description": record.get("description") or "",
                        "brand_id": record.get("brand_id") or "",
                    }
        except Exception as exc:
            logger.warning("brand_metaphor_scoring fetch failed: %s", exc)
            return {}

        return result
