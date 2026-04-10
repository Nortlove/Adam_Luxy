"""
Task 3: News Cycle Psychological State Detector
================================================

Monitors the current news cycle to compute an ambient psychological
state that all readers carry as they browse any page today.

A day dominated by financial crisis headlines creates elevated
uncertainty_tolerance activation and shifts approach_avoidance toward
avoidance across the entire web, not just news sites.

Produces:
- AmbientPsychologicalState: global NDF vector for today's mood
- PsychologicalEventFlags: high-impact event detection

Consumed at bid time:
- Baseline modifier applied to ALL decisions. On high-anxiety days,
  cold-start buyers get wider uncertainty intervals, increasing
  exploration bonus.

Redis keys:
- informativ:ambient:global -- global ambient state (12h TTL)
- informativ:ambient:events -- active event flags
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)

# Event detection patterns and their NDF impacts
_EVENT_SIGNATURES = {
    "market_crash": {
        "patterns": ["market crash", "stock plunge", "recession", "economic downturn",
                      "market sell-off", "bear market", "financial crisis"],
        "ndf_impact": {
            "approach_avoidance": -0.3,
            "uncertainty_tolerance": 0.3,
            "temporal_horizon": -0.2,
        },
        "mechanism_mods": {
            "authority": 1.3, "loss_aversion": 1.4,
            "scarcity": 0.7, "curiosity": 0.8,
        },
    },
    "election_tension": {
        "patterns": ["election results", "contested election", "political crisis",
                      "impeachment", "political divide"],
        "ndf_impact": {
            "social_calibration": 0.3,
            "uncertainty_tolerance": 0.2,
            "arousal_seeking": 0.2,
        },
        "mechanism_mods": {
            "unity": 1.3, "social_proof": 1.2,
            "authority": 0.8,
        },
    },
    "pandemic_fear": {
        "patterns": ["pandemic", "outbreak", "quarantine", "lockdown",
                      "new variant", "public health emergency"],
        "ndf_impact": {
            "approach_avoidance": -0.4,
            "social_calibration": -0.2,
            "uncertainty_tolerance": 0.4,
        },
        "mechanism_mods": {
            "authority": 1.5, "social_proof": 1.3,
            "scarcity": 1.4, "loss_aversion": 1.3,
        },
    },
    "national_celebration": {
        "patterns": ["independence day", "national holiday", "celebration",
                      "parade", "fireworks", "championship victory"],
        "ndf_impact": {
            "approach_avoidance": 0.3,
            "social_calibration": 0.3,
            "arousal_seeking": 0.3,
        },
        "mechanism_mods": {
            "unity": 1.4, "liking": 1.3,
            "social_proof": 1.2, "loss_aversion": 0.7,
        },
    },
    "major_tragedy": {
        "patterns": ["mass shooting", "natural disaster", "devastating",
                      "casualties", "emergency declared", "death toll"],
        "ndf_impact": {
            "approach_avoidance": -0.5,
            "arousal_seeking": 0.3,
            "social_calibration": 0.2,
        },
        "mechanism_mods": {
            "unity": 1.4, "authority": 1.2,
            "scarcity": 0.5, "liking": 0.7, "curiosity": 0.6,
        },
    },
}

# News sources to monitor
_NEWS_SOURCES = [
    "https://news.google.com/rss",
    "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
    "https://feeds.bbci.co.uk/news/rss.xml",
    "https://feeds.reuters.com/reuters/topNews",
    "https://rss.cnn.com/rss/edition.rss",
]


class NewsCycleTask(DailyStrengtheningTask):
    """Detect ambient psychological state from news cycle."""

    @property
    def name(self) -> str:
        return "news_cycle"

    @property
    def schedule_hours(self) -> List[int]:
        return [0, 4, 8, 12, 16, 20]  # Every 4 hours

    @property
    def frequency_hours(self) -> int:
        return 4

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        # Fetch headlines from multiple sources
        headlines = await self._fetch_headlines()
        result.items_processed = len(headlines)

        if not headlines:
            result.details["note"] = "No headlines fetched"
            return result

        # Combine all headlines into a single text for NDF analysis
        combined_text = " ".join(headlines)
        ambient_ndf = self._ndf_from_text(combined_text)

        # Detect active events
        text_lower = combined_text.lower()
        active_events = {}
        for event_name, event_config in _EVENT_SIGNATURES.items():
            hits = sum(1 for p in event_config["patterns"] if p in text_lower)
            if hits >= 2:  # Need 2+ pattern matches for confidence
                active_events[event_name] = {
                    "confidence": min(1.0, hits / len(event_config["patterns"]) * 2),
                    "ndf_impact": event_config["ndf_impact"],
                    "mechanism_mods": event_config["mechanism_mods"],
                    "pattern_hits": hits,
                }

        # Compute composite ambient state (base NDF + event impacts)
        composite_ndf = dict(ambient_ndf)
        composite_mechanism_mods = {}

        for event_name, event_data in active_events.items():
            confidence = event_data["confidence"]
            for dim, impact in event_data["ndf_impact"].items():
                if dim in composite_ndf:
                    composite_ndf[dim] = round(
                        composite_ndf[dim] + impact * confidence, 4
                    )
            for mech, mod in event_data["mechanism_mods"].items():
                # Blend: weighted by confidence, multiplicative across events
                current = composite_mechanism_mods.get(mech, 1.0)
                adjustment = 1.0 + (mod - 1.0) * confidence
                composite_mechanism_mods[mech] = round(current * adjustment, 3)

        # Store global ambient state
        ambient_data = {
            "ndf_vector": composite_ndf,
            "mechanism_modifiers": composite_mechanism_mods,
            "active_events": list(active_events.keys()),
            "event_details": active_events,
            "headline_count": len(headlines),
            "dominant_valence": "positive" if ambient_ndf.get("approach_avoidance", 0) > 0.1 else (
                "negative" if ambient_ndf.get("approach_avoidance", 0) < -0.1 else "neutral"
            ),
            "computed_at": time.time(),
        }

        if self._store_redis_hash("informativ:ambient:global", ambient_data, ttl=43200):
            result.items_stored += 1

        # Store event flags separately for fast lookup
        if active_events:
            if self._store_redis_hash("informativ:ambient:events", {
                "events": list(active_events.keys()),
                "event_count": len(active_events),
                "computed_at": time.time(),
            }, ttl=43200):
                result.items_stored += 1

            for event_name in active_events:
                logger.info("EVENT DETECTED: %s (confidence=%.2f)",
                            event_name, active_events[event_name]["confidence"])

        result.details["active_events"] = list(active_events.keys())
        result.details["ambient_valence"] = ambient_data["dominant_valence"]
        return result

    async def _fetch_headlines(self) -> List[str]:
        """Fetch headlines from RSS feeds."""
        headlines = []
        try:
            import httpx
        except ImportError:
            return headlines

        async with httpx.AsyncClient(timeout=10) as client:
            for feed_url in _NEWS_SOURCES:
                try:
                    resp = await client.get(feed_url, headers={
                        "User-Agent": "Mozilla/5.0 (compatible; ADAM/1.0)"
                    })
                    if resp.status_code == 200:
                        # Parse RSS/XML for titles
                        import re
                        titles = re.findall(r"<title[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", resp.text)
                        for title in titles:
                            title = title.strip()
                            if len(title) > 10 and title not in ("RSS", "Top Stories", "Home", "BBC News"):
                                headlines.append(title)
                except Exception as e:
                    logger.debug("RSS fetch failed for %s: %s", feed_url, e)

        return headlines[:200]  # Cap at 200 headlines
