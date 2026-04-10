"""
Task 6: Cultural Calendar Psychological Priming
================================================

Maintains a rolling 14-day lookahead of cultural/seasonal events that
predictably shift psychological receptivity.

Each event has a pre-modeled NDF impact profile. Valentine's Day shifts
social_calibration upward, approach_avoidance toward approach, and opens
the mimetic_desire and unity channels.

Produces:
- ActiveEventState: currently active events with composite NDF impact
- UpcomingEventPriors: what's coming in the next 14 days

Consumed at bid time:
- Composited with ambient state (Task 3) to form environmental context.
  During Valentine's week: social_proof boosted 1.3x, scarcity 1.2x.

Redis keys:
- informativ:calendar:active — active event composite (6h TTL)
- informativ:calendar:upcoming:{date} — per-date priors
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)

# Cultural event calendar with NDF impact models
# Each event has: date_range (month, day_start, day_end), ramp_days (lead-up),
# ndf_impact, mechanism_mods, affected_categories
_CULTURAL_EVENTS = [
    {
        "name": "new_years_resolution",
        "month": 1, "day_start": 1, "day_end": 21,
        "ramp_days": 5,
        "ndf_impact": {
            "approach_avoidance": 0.3,
            "temporal_horizon": 0.3,
            "cognitive_engagement": 0.1,
        },
        "mechanism_mods": {
            "commitment": 1.4, "authority": 1.2, "social_proof": 1.2,
            "scarcity": 0.8,
        },
        "affected_categories": ["health_fitness", "education", "self_improvement",
                                 "finance", "productivity"],
    },
    {
        "name": "valentines_day",
        "month": 2, "day_start": 7, "day_end": 14,
        "ramp_days": 7,
        "ndf_impact": {
            "social_calibration": 0.3,
            "approach_avoidance": 0.2,
            "arousal_seeking": 0.2,
            "status_sensitivity": 0.15,
        },
        "mechanism_mods": {
            "social_proof": 1.3, "scarcity": 1.25, "liking": 1.3,
            "unity": 1.2,
        },
        "affected_categories": ["beauty", "fashion", "food_drink", "jewelry",
                                 "experiences", "travel"],
    },
    {
        "name": "tax_season",
        "month": 3, "day_start": 15, "day_end": 30,
        "ramp_days": 14,
        "ndf_impact": {
            "approach_avoidance": -0.2,
            "temporal_horizon": -0.2,
            "uncertainty_tolerance": 0.2,
            "cognitive_engagement": 0.2,
        },
        "mechanism_mods": {
            "authority": 1.4, "loss_aversion": 1.3, "commitment": 1.2,
            "curiosity": 0.8, "scarcity": 0.7,
        },
        "affected_categories": ["finance", "tax_services", "accounting",
                                 "software", "legal"],
    },
    {
        "name": "mothers_day",
        "month": 5, "day_start": 1, "day_end": 12,
        "ramp_days": 10,
        "ndf_impact": {
            "social_calibration": 0.25,
            "approach_avoidance": 0.15,
            "status_sensitivity": 0.1,
        },
        "mechanism_mods": {
            "reciprocity": 1.3, "social_proof": 1.2, "scarcity": 1.2,
            "liking": 1.25,
        },
        "affected_categories": ["beauty", "jewelry", "flowers", "home",
                                 "experiences", "food_drink"],
    },
    {
        "name": "memorial_day_sales",
        "month": 5, "day_start": 20, "day_end": 27,
        "ramp_days": 5,
        "ndf_impact": {
            "approach_avoidance": 0.2,
            "arousal_seeking": 0.15,
        },
        "mechanism_mods": {
            "scarcity": 1.35, "social_proof": 1.2, "reciprocity": 1.2,
        },
        "affected_categories": ["automotive", "home", "appliances", "furniture",
                                 "mattress", "fashion"],
    },
    {
        "name": "fathers_day",
        "month": 6, "day_start": 8, "day_end": 15,
        "ramp_days": 7,
        "ndf_impact": {
            "social_calibration": 0.2,
            "approach_avoidance": 0.1,
        },
        "mechanism_mods": {
            "reciprocity": 1.25, "authority": 1.15, "social_proof": 1.15,
        },
        "affected_categories": ["electronics", "tools", "automotive", "sports",
                                 "fashion", "food_drink"],
    },
    {
        "name": "independence_day",
        "month": 7, "day_start": 1, "day_end": 4,
        "ramp_days": 3,
        "ndf_impact": {
            "social_calibration": 0.3,
            "arousal_seeking": 0.25,
            "approach_avoidance": 0.2,
        },
        "mechanism_mods": {
            "unity": 1.4, "social_proof": 1.2, "liking": 1.2,
        },
        "affected_categories": ["food_drink", "outdoor", "travel", "automotive",
                                 "fashion"],
    },
    {
        "name": "back_to_school",
        "month": 8, "day_start": 1, "day_end": 31,
        "ramp_days": 14,
        "ndf_impact": {
            "temporal_horizon": 0.15,
            "cognitive_engagement": 0.1,
            "approach_avoidance": 0.1,
        },
        "mechanism_mods": {
            "social_proof": 1.3, "scarcity": 1.2, "authority": 1.15,
            "commitment": 1.15,
        },
        "affected_categories": ["electronics", "fashion", "education",
                                 "office_supplies", "dorm"],
    },
    {
        "name": "labor_day_sales",
        "month": 9, "day_start": 1, "day_end": 7,
        "ramp_days": 5,
        "ndf_impact": {
            "approach_avoidance": 0.15,
            "arousal_seeking": 0.1,
        },
        "mechanism_mods": {
            "scarcity": 1.3, "social_proof": 1.2, "reciprocity": 1.15,
        },
        "affected_categories": ["automotive", "home", "appliances", "fashion",
                                 "travel"],
    },
    {
        "name": "halloween",
        "month": 10, "day_start": 15, "day_end": 31,
        "ramp_days": 7,
        "ndf_impact": {
            "arousal_seeking": 0.25,
            "social_calibration": 0.15,
        },
        "mechanism_mods": {
            "social_proof": 1.2, "scarcity": 1.25, "curiosity": 1.2,
            "liking": 1.15,
        },
        "affected_categories": ["costumes", "candy", "decorations", "experiences",
                                 "entertainment"],
    },
    {
        "name": "black_friday_cyber_monday",
        "month": 11, "day_start": 20, "day_end": 30,
        "ramp_days": 10,
        "ndf_impact": {
            "approach_avoidance": 0.3,
            "arousal_seeking": 0.3,
            "temporal_horizon": -0.3,
            "uncertainty_tolerance": -0.2,
        },
        "mechanism_mods": {
            "scarcity": 1.5, "social_proof": 1.35, "loss_aversion": 1.3,
            "reciprocity": 1.2, "authority": 0.8,
        },
        "affected_categories": ["electronics", "fashion", "home", "beauty",
                                 "toys", "all"],
    },
    {
        "name": "holiday_gift_season",
        "month": 12, "day_start": 1, "day_end": 24,
        "ramp_days": 7,
        "ndf_impact": {
            "social_calibration": 0.3,
            "approach_avoidance": 0.2,
            "temporal_horizon": -0.2,
            "status_sensitivity": 0.2,
        },
        "mechanism_mods": {
            "reciprocity": 1.4, "social_proof": 1.3, "scarcity": 1.35,
            "unity": 1.3, "liking": 1.2,
        },
        "affected_categories": ["all"],
    },
    {
        "name": "new_years_eve",
        "month": 12, "day_start": 28, "day_end": 31,
        "ramp_days": 3,
        "ndf_impact": {
            "arousal_seeking": 0.3,
            "social_calibration": 0.25,
            "temporal_horizon": 0.2,
        },
        "mechanism_mods": {
            "unity": 1.3, "social_proof": 1.25, "scarcity": 1.2,
        },
        "affected_categories": ["experiences", "fashion", "food_drink", "travel"],
    },
]


class CulturalCalendarTask(DailyStrengtheningTask):
    """Compute active and upcoming cultural event modifiers."""

    @property
    def name(self) -> str:
        return "cultural_calendar"

    @property
    def schedule_hours(self) -> List[int]:
        return [6, 18]  # Twice daily

    @property
    def frequency_hours(self) -> int:
        return 12

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        now = datetime.now(timezone.utc)
        today = now.date()

        # Find active events
        active_events = []
        for event in _CULTURAL_EVENTS:
            if self._is_active(event, today):
                strength = self._compute_strength(event, today)
                active_events.append({
                    "name": event["name"],
                    "strength": strength,
                    "ndf_impact": event["ndf_impact"],
                    "mechanism_mods": event["mechanism_mods"],
                    "affected_categories": event["affected_categories"],
                })

        # Compute composite active state
        composite_ndf = {}
        composite_mech = {}

        for event in active_events:
            s = event["strength"]
            for dim, impact in event["ndf_impact"].items():
                composite_ndf[dim] = composite_ndf.get(dim, 0) + impact * s
            for mech, mod in event["mechanism_mods"].items():
                current = composite_mech.get(mech, 1.0)
                adjustment = 1.0 + (mod - 1.0) * s
                composite_mech[mech] = round(current * adjustment, 3)

        # Round NDF values
        composite_ndf = {k: round(v, 4) for k, v in composite_ndf.items()}

        # Collect affected categories
        all_categories = set()
        for event in active_events:
            all_categories.update(event["affected_categories"])

        # Store active composite
        active_data = {
            "active_events": [e["name"] for e in active_events],
            "event_count": len(active_events),
            "composite_ndf_impact": composite_ndf,
            "composite_mechanism_mods": composite_mech,
            "affected_categories": list(all_categories),
            "computed_at": time.time(),
            "date": str(today),
        }
        if self._store_redis_hash("informativ:calendar:active", active_data, ttl=21600):
            result.items_stored += 1

        result.items_processed = len(_CULTURAL_EVENTS)

        # Store upcoming events for next 14 days
        for day_offset in range(1, 15):
            future_date = today + timedelta(days=day_offset)
            upcoming = []
            for event in _CULTURAL_EVENTS:
                if self._is_active(event, future_date):
                    upcoming.append(event["name"])
            if upcoming:
                date_key = f"informativ:calendar:upcoming:{future_date}"
                self._store_redis_hash(date_key, {
                    "events": upcoming,
                    "date": str(future_date),
                }, ttl=86400 * 15)
                result.items_stored += 1

        result.details["active_events"] = [e["name"] for e in active_events]
        result.details["composite_mechanism_mods"] = composite_mech
        return result

    def _is_active(self, event: Dict[str, Any], check_date) -> bool:
        """Check if event is active on given date (including ramp-up)."""
        month = event["month"]
        day_start = event["day_start"]
        day_end = event["day_end"]
        ramp = event.get("ramp_days", 0)

        # Adjust start for ramp-up
        from datetime import date
        try:
            event_start = date(check_date.year, month, day_start) - timedelta(days=ramp)
            event_end = date(check_date.year, month, day_end)
            return event_start <= check_date <= event_end
        except ValueError:
            return False

    def _compute_strength(self, event: Dict[str, Any], check_date) -> float:
        """Compute event strength based on position in timeline.

        Ramp up during lead-in, peak at event dates, decay after.
        """
        from datetime import date
        try:
            month = event["month"]
            event_start = date(check_date.year, month, event["day_start"])
            event_end = date(check_date.year, month, event["day_end"])
            ramp = event.get("ramp_days", 0)
            ramp_start = event_start - timedelta(days=ramp)

            if check_date < ramp_start:
                return 0.0
            elif check_date < event_start:
                # Ramp up phase
                days_in = (check_date - ramp_start).days
                return min(1.0, days_in / max(1, ramp))
            elif check_date <= event_end:
                # Peak phase
                return 1.0
            else:
                return 0.0
        except ValueError:
            return 0.0
