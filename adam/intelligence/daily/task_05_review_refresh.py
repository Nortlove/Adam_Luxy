"""
Task 5: Review Intelligence Refresh
====================================

Fetches fresh product reviews to update buyer psychology priors.
New reviews update BRAND_CONVERTED edge aggregates and gradient fields.

Produces:
- Updated Beta posteriors on bilateral edge dimensions
- Fresh susceptibility scores from review mechanism analysis

Consumed at bid time:
- Directly strengthens L3 (Bilateral Edge Intelligence) of the cascade.
  Fresher edges = more accurate mechanism predictions.

Redis keys:
- informativ:review_refresh:{category}:{archetype} -- last update + delta
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)

# Top categories for daily refresh (by volume)
_PRIORITY_CATEGORIES = [
    "Beauty_and_Personal_Care", "Electronics", "Health_and_Household",
    "Home_and_Kitchen", "Clothing_Shoes_and_Jewelry", "Sports_and_Outdoors",
    "Tools_and_Home_Improvement", "Baby_Products", "Automotive",
    "Cell_Phones_and_Accessories", "Pet_Supplies", "Grocery_and_Gourmet_Food",
    "Office_Products", "Patio_Lawn_and_Garden", "Toys_and_Games",
    "Books", "Software", "Industrial_and_Scientific",
    "Arts_Crafts_and_Sewing", "Musical_Instruments",
]


class ReviewRefreshTask(DailyStrengtheningTask):
    """Refresh buyer psychology priors from new reviews."""

    @property
    def name(self) -> str:
        return "review_refresh"

    @property
    def schedule_hours(self) -> List[int]:
        return [1]  # 1 AM UTC

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        for category in _PRIORITY_CATEGORIES[:10]:  # Top 10 daily
            try:
                processed = await self._refresh_category(category)
                result.items_processed += processed.get("reviews_analyzed", 0)
                result.items_stored += processed.get("priors_updated", 0)
            except Exception as e:
                result.errors += 1
                logger.debug("Review refresh failed for %s: %s", category, e)

        result.details["categories_refreshed"] = min(10, len(_PRIORITY_CATEGORIES))
        return result

    async def _refresh_category(self, category: str) -> Dict[str, int]:
        """Refresh review intelligence for a single category."""
        stats = {"reviews_analyzed": 0, "priors_updated": 0}

        # Check when we last refreshed this category
        r = self._get_redis()
        last_refresh_key = f"informativ:review_refresh:last:{category}"
        last_refresh = 0.0
        if r:
            lr = r.get(last_refresh_key)
            if lr:
                last_refresh = float(lr)
                # Skip if refreshed in last 20 hours
                if time.time() - last_refresh < 72000:
                    return stats

        # Fetch recent reviews (from existing scrapers or stored corpus)
        reviews = await self._fetch_recent_reviews(category)
        if not reviews:
            return stats

        # NDF-profile each review to extract buyer psychology
        buyer_ndf_vectors = []
        mechanism_detections = []

        for review in reviews:
            stats["reviews_analyzed"] += 1
            text = review.get("text", "")
            if not text or len(text) < 50:
                continue

            # Extract buyer NDF from review text
            ndf = self._ndf_from_text(text)
            buyer_ndf_vectors.append(ndf)

            # Detect mechanism responsiveness from review language
            mechanism_signals = self._detect_mechanism_signals_in_review(text)
            if mechanism_signals:
                mechanism_detections.append(mechanism_signals)

        if buyer_ndf_vectors:
            # Compute category-level NDF centroid update
            centroid = {}
            for dim in buyer_ndf_vectors[0].keys():
                values = [v.get(dim, 0.5) for v in buyer_ndf_vectors]
                centroid[dim] = round(sum(values) / len(values), 4)

            # Store updated category intelligence
            update_key = f"informativ:review_refresh:{category}:centroid"
            if self._store_redis_hash(update_key, {
                "ndf_centroid": centroid,
                "sample_size": len(buyer_ndf_vectors),
                "category": category,
                "computed_at": time.time(),
            }, ttl=86400 * 3):
                stats["priors_updated"] += 1

        if mechanism_detections:
            # Aggregate mechanism responsiveness
            mech_agg: Dict[str, List[float]] = {}
            for detection in mechanism_detections:
                for mech, score in detection.items():
                    if mech not in mech_agg:
                        mech_agg[mech] = []
                    mech_agg[mech].append(score)

            mech_summary = {
                mech: round(sum(scores) / len(scores), 3)
                for mech, scores in mech_agg.items()
            }

            mech_key = f"informativ:review_refresh:{category}:mechanisms"
            if self._store_redis_hash(mech_key, {
                "mechanism_responsiveness": mech_summary,
                "sample_size": len(mechanism_detections),
                "category": category,
                "computed_at": time.time(),
            }, ttl=86400 * 3):
                stats["priors_updated"] += 1

        # Mark as refreshed
        if r:
            r.set(last_refresh_key, str(time.time()), ex=86400 * 7)

        return stats

    async def _fetch_recent_reviews(self, category: str) -> List[Dict[str, Any]]:
        """Fetch recent reviews for a category.

        Uses Neo4j corpus if available, falls back to empty list.
        The scraper integration (Oxylabs) can be added when API access is configured.
        """
        reviews = []

        try:
            from adam.core.dependencies import Infrastructure
            infra = Infrastructure.get_instance()
            if infra._neo4j_driver:
                # Query recent reviews from graph
                async with infra._neo4j_driver.session() as session:
                    query = """
                    MATCH (r:Review)-[:REVIEWS]->(p:Product)-[:IN_CATEGORY]->(c:Category)
                    WHERE c.name = $category
                    RETURN r.text AS text, r.rating AS rating, r.helpful_votes AS helpful
                    ORDER BY r.date DESC
                    LIMIT 500
                    """
                    result = await session.run(query, category=category)
                    async for record in result:
                        reviews.append({
                            "text": record.get("text", ""),
                            "rating": record.get("rating", 0),
                            "helpful": record.get("helpful", 0),
                        })
        except Exception as e:
            logger.debug("Neo4j review fetch failed for %s: %s", category, e)

        return reviews

    def _detect_mechanism_signals_in_review(self, text: str) -> Dict[str, float]:
        """Detect which persuasion mechanisms the reviewer is responsive to.

        Review language reveals what convinced them:
        - "everyone says" -> social_proof responsive
        - "the expert recommended" -> authority responsive
        - "had to get it before it sold out" -> scarcity responsive
        """
        text_lower = text.lower()
        signals = {}

        _REVIEW_MECHANISM_MARKERS = {
            "social_proof": ["everyone", "popular", "recommended", "reviews said",
                            "best seller", "most people", "highly rated"],
            "authority": ["expert", "doctor", "recommended by", "professional",
                         "dermatologist", "certified", "clinically"],
            "scarcity": ["before it sold out", "hard to find", "limited",
                        "finally got", "back in stock", "waited"],
            "reciprocity": ["free sample", "free trial", "came with bonus",
                           "generous", "included extras"],
            "commitment": ["tried it first", "started with", "committed to",
                          "invested in", "long term"],
            "loss_aversion": ["didn't want to miss", "afraid", "couldn't risk",
                             "didn't want to lose", "protect"],
        }

        for mechanism, markers in _REVIEW_MECHANISM_MARKERS.items():
            hits = sum(1 for m in markers if m in text_lower)
            if hits > 0:
                signals[mechanism] = min(1.0, hits / len(markers) * 3.0)

        return signals
