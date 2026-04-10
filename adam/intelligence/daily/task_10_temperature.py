"""
Task 10: Category Conversion Temperature Index
================================================

Computes a "temperature" score per category indicating how hot or cold
the category is for conversions right now.

Combines internal outcome data with external signals (social sentiment,
calendar events, news cycle) to produce a single temperature indicator.

Produces:
- CategoryTemperature: z-score vs baseline, trend direction, driver
- CrossCategoryHeatMap: heating/cooling categories

Consumed at bid time:
- Hot categories get higher information value (more active buyers =
  more learning opportunities). Cold categories → more conservative.

Redis keys:
- informativ:temperature:{category} — temperature score (12h TTL)
- informativ:temperature:heatmap — cross-category view
"""

from __future__ import annotations

import json
import logging
import math
import time
from typing import Any, Dict, List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)

_ALL_CATEGORIES = [
    "beauty", "electronics", "health", "home", "fashion",
    "finance", "automotive", "travel", "food", "education",
    "gaming", "sports", "entertainment", "pets", "baby",
]


class TemperatureIndexTask(DailyStrengtheningTask):
    """Compute category conversion temperature index."""

    @property
    def name(self) -> str:
        return "temperature_index"

    @property
    def schedule_hours(self) -> List[int]:
        return [6, 14, 22]  # Every 8 hours

    @property
    def frequency_hours(self) -> int:
        return 8

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)
        r = self._get_redis()

        temperatures: Dict[str, Dict[str, Any]] = {}

        for category in _ALL_CATEGORIES:
            try:
                temp = await self._compute_temperature(category, r)
                temperatures[category] = temp
                result.items_processed += 1

                temp_key = f"informativ:temperature:{category}"
                if self._store_redis_hash(temp_key, temp, ttl=43200):
                    result.items_stored += 1
            except Exception as e:
                result.errors += 1
                logger.debug("Temperature failed for %s: %s", category, e)

        # Cross-category heatmap
        if temperatures:
            heating = [c for c, t in temperatures.items() if t.get("trend") == "heating"]
            cooling = [c for c, t in temperatures.items() if t.get("trend") == "cooling"]
            stable = [c for c, t in temperatures.items() if t.get("trend") == "stable"]

            heatmap = {
                "heating": heating,
                "cooling": cooling,
                "stable": stable,
                "hottest": max(temperatures.items(), key=lambda x: x[1].get("score", 0))[0] if temperatures else "",
                "coldest": min(temperatures.items(), key=lambda x: x[1].get("score", 0))[0] if temperatures else "",
                "computed_at": time.time(),
            }
            if self._store_redis_hash("informativ:temperature:heatmap", heatmap, ttl=43200):
                result.items_stored += 1

        result.details["heating"] = [c for c, t in temperatures.items() if t.get("trend") == "heating"]
        result.details["cooling"] = [c for c, t in temperatures.items() if t.get("trend") == "cooling"]
        return result

    async def _compute_temperature(
        self, category: str, r=None,
    ) -> Dict[str, Any]:
        """Compute temperature for a single category.

        Combines signals:
        - Social pulse activity (Task 7)
        - Calendar event relevance (Task 6)
        - Competitive ad density (Task 1)
        - Fatigue levels (Task 4)
        """
        score = 0.0
        drivers = []

        # Signal 1: Social pulse intensity
        if r:
            try:
                pulse_data = r.hgetall(f"informativ:social:{category}:pulse")
                if pulse_data:
                    posts = int(pulse_data.get("posts_analyzed", 0))
                    valence_raw = pulse_data.get("dominant_valence", "neutral")
                    if posts > 20:
                        score += 0.3  # Active discussion = heating
                        drivers.append("social_activity")
                    if valence_raw == "positive":
                        score += 0.15
            except Exception:
                pass

        # Signal 2: Calendar event activation
        if r:
            try:
                cal_data = r.hgetall("informativ:calendar:active")
                if cal_data:
                    affected = cal_data.get("affected_categories", "[]")
                    if isinstance(affected, str):
                        try:
                            affected = json.loads(affected)
                        except Exception:
                            affected = []
                    if category in affected or "all" in affected:
                        score += 0.4
                        drivers.append("calendar_event")
            except Exception:
                pass

        # Signal 3: Competitive density (more ads = hotter market)
        if r:
            try:
                cursor = 0
                comp_count = 0
                while True:
                    cursor, keys = r.scan(
                        cursor, match=f"informativ:competitive:{category}:*", count=50,
                    )
                    comp_count += len(keys)
                    if cursor == 0:
                        break
                if comp_count > 5:
                    score += 0.2
                    drivers.append("competitive_density")
            except Exception:
                pass

        # Signal 4: Fatigue check (high fatigue = cooling)
        if r:
            try:
                # Check if mechanisms are fatigued for domains in this category
                cursor = 0
                fatigue_sum = 0.0
                fatigue_count = 0
                while True:
                    cursor, keys = r.scan(
                        cursor, match="informativ:fatigue:index:*", count=50,
                    )
                    for key in keys:
                        data = r.hgetall(key)
                        if data:
                            f = float(data.get("overall_fatigue", 0))
                            fatigue_sum += f
                            fatigue_count += 1
                    if cursor == 0:
                        break
                if fatigue_count > 0:
                    avg_fatigue = fatigue_sum / fatigue_count
                    if avg_fatigue > 0.5:
                        score -= 0.2
                        drivers.append("high_fatigue")
            except Exception:
                pass

        # Classify
        if score > 0.5:
            trend = "heating"
        elif score < -0.1:
            trend = "cooling"
        else:
            trend = "stable"

        return {
            "category": category,
            "score": round(score, 3),
            "trend": trend,
            "drivers": drivers,
            "bid_adjustment": round(1.0 + score * 0.2, 3),  # ±20% adjustment
            "computed_at": time.time(),
        }
