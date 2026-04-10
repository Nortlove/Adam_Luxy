"""
Intelligence Consumer — Bid-Time Consumption of Daily Strengthening Data
=========================================================================

At bid time (<50ms), reads pre-computed intelligence from Redis
and applies it to the decision pipeline. This module is the bridge
between the offline daily strengthening tasks and the real-time
bilateral cascade.

Usage:
    consumer = IntelligenceConsumer()

    # Get environmental context (ambient + calendar)
    env = consumer.get_environmental_context()

    # Get mechanism modifiers for a specific domain + category
    mods = consumer.get_mechanism_modifiers("nytimes.com", "finance")

    # Get brand complement recommendation
    complement = consumer.get_brand_complement("nike")

    # Get category temperature
    temp = consumer.get_category_temperature("beauty")
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class IntelligenceConsumer:
    """Reads daily strengthening intelligence at bid time.

    All reads are from Redis (<2ms). No computation at bid time.
    Falls back gracefully if any intelligence layer is unavailable.
    """

    def __init__(self):
        self._redis = None

    def _get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            import redis
            self._redis = redis.Redis(
                host="localhost", port=6379, decode_responses=True,
            )
            self._redis.ping()
            return self._redis
        except Exception:
            return None

    def _read_hash(self, key: str) -> Optional[Dict[str, str]]:
        r = self._get_redis()
        if not r:
            return None
        try:
            data = r.hgetall(key)
            return data if data else None
        except Exception:
            return None

    def _parse_json_field(self, data: Dict, field: str, default=None):
        """Safely parse a JSON-encoded field from Redis hash."""
        val = data.get(field)
        if val is None:
            return default
        if isinstance(val, str):
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return default
        return val

    # ─── Environmental Context ──────────────────────────────────────

    def get_environmental_context(self) -> Dict[str, Any]:
        """Get combined ambient + calendar context.

        Returns:
            {
                "ambient_ndf": {dim: value},
                "ambient_mechanism_mods": {mechanism: multiplier},
                "active_events": ["event_name", ...],
                "calendar_ndf_impact": {dim: value},
                "calendar_mechanism_mods": {mechanism: multiplier},
                "combined_mechanism_mods": {mechanism: multiplier},
            }
        """
        result = {
            "ambient_ndf": {},
            "ambient_mechanism_mods": {},
            "active_events": [],
            "calendar_ndf_impact": {},
            "calendar_mechanism_mods": {},
            "combined_mechanism_mods": {},
        }

        # Read ambient state (Task 3: News Cycle)
        ambient = self._read_hash("informativ:ambient:global")
        if ambient:
            result["ambient_ndf"] = self._parse_json_field(ambient, "ndf_vector", {})
            result["ambient_mechanism_mods"] = self._parse_json_field(
                ambient, "mechanism_modifiers", {},
            )
            result["active_events"] = self._parse_json_field(
                ambient, "active_events", [],
            )

        # Read calendar state (Task 6: Cultural Calendar)
        calendar = self._read_hash("informativ:calendar:active")
        if calendar:
            result["calendar_ndf_impact"] = self._parse_json_field(
                calendar, "composite_ndf_impact", {},
            )
            result["calendar_mechanism_mods"] = self._parse_json_field(
                calendar, "composite_mechanism_mods", {},
            )
            cal_events = self._parse_json_field(calendar, "active_events", [])
            result["active_events"].extend(cal_events)

        # Combine mechanism modifiers (multiplicative)
        combined = {}
        for source in [result["ambient_mechanism_mods"], result["calendar_mechanism_mods"]]:
            for mech, mod in source.items():
                mod_float = float(mod)
                combined[mech] = combined.get(mech, 1.0) * mod_float

        result["combined_mechanism_mods"] = {
            k: round(v, 3) for k, v in combined.items()
        }

        return result

    # ─── Mechanism Modifiers ────────────────────────────────────────

    def get_mechanism_modifiers(
        self, domain: str, category: str = "",
    ) -> Dict[str, float]:
        """Get composite mechanism modifiers for a domain + category.

        Combines:
        - Domain drift (Task 2)
        - Mechanism fatigue (Task 4)
        - Competitive saturation (Task 1)
        - Environmental context (Tasks 3 + 6)
        - Social sentiment (Task 7)

        Returns {mechanism: multiplier} where 1.0 = no change.
        """
        modifiers: Dict[str, float] = {}

        # 1. Environmental context
        env = self.get_environmental_context()
        for mech, mod in env["combined_mechanism_mods"].items():
            modifiers[mech] = modifiers.get(mech, 1.0) * float(mod)

        # 2. Fatigue (Task 4)
        r = self._get_redis()
        if r and domain:
            try:
                fatigue_index = r.hgetall(f"informativ:fatigue:index:{domain}")
                if fatigue_index:
                    fatigue_scores = self._parse_json_field(
                        fatigue_index, "mechanism_fatigue_scores", {},
                    )
                    for mech, fatigue in fatigue_scores.items():
                        fatigue_float = float(fatigue)
                        if fatigue_float > 0.3:
                            # Discount fatigued mechanisms
                            discount = max(0.3, 1.0 - fatigue_float)
                            modifiers[mech] = modifiers.get(mech, 1.0) * discount
            except Exception:
                pass

        # 3. Competitive saturation (Task 1)
        if r and category:
            try:
                for mech in ["social_proof", "authority", "scarcity", "reciprocity",
                             "commitment", "liking", "loss_aversion", "curiosity"]:
                    sat_data = r.hgetall(
                        f"informativ:competitive:{category}:{mech}"
                    )
                    if sat_data:
                        saturation = float(sat_data.get("saturation", 0))
                        if saturation > 0.5:
                            # Counter-cyclical: high saturation → discount
                            discount = max(0.6, 1.0 - (saturation - 0.5) * 0.6)
                            modifiers[mech] = modifiers.get(mech, 1.0) * discount
            except Exception:
                pass

        # 4. Social sentiment mechanism preferences (Task 7)
        if r and category:
            try:
                mech_data = r.hgetall(f"informativ:social:{category}:mechanisms")
                if mech_data:
                    prefs = self._parse_json_field(mech_data, "preferences", {})
                    for mech, strength in prefs.items():
                        strength_float = float(strength)
                        if strength_float > 0.3:
                            # Social proof that mechanism works → boost
                            boost = 1.0 + strength_float * 0.2
                            modifiers[mech] = modifiers.get(mech, 1.0) * boost
            except Exception:
                pass

        return {k: round(v, 3) for k, v in modifiers.items()}

    # ─── Brand Complement ───────────────────────────────────────────

    def get_brand_complement(self, brand_id: str) -> Dict[str, Any]:
        """Get brand mechanism complement recommendation (Task 9).

        Returns:
            {
                "recommended_complement": "social_proof",
                "avoid_mechanism": "authority",
                "complement_ranking": {...},
            }
        """
        data = self._read_hash(f"informativ:brand:{brand_id}:complement")
        if data:
            return {
                "recommended_complement": data.get("recommended_complement", ""),
                "avoid_mechanism": data.get("avoid_mechanism", ""),
                "complement_ranking": self._parse_json_field(
                    data, "complement_ranking", {},
                ),
            }
        return {}

    # ─── Category Temperature ───────────────────────────────────────

    def get_category_temperature(self, category: str) -> Dict[str, Any]:
        """Get category temperature (Task 10).

        Returns:
            {
                "score": 0.6,
                "trend": "heating",
                "bid_adjustment": 1.12,
                "drivers": ["social_activity", "calendar_event"],
            }
        """
        data = self._read_hash(f"informativ:temperature:{category}")
        if data:
            return {
                "score": float(data.get("score", 0)),
                "trend": data.get("trend", "stable"),
                "bid_adjustment": float(data.get("bid_adjustment", 1.0)),
                "drivers": self._parse_json_field(data, "drivers", []),
            }
        return {"score": 0.0, "trend": "stable", "bid_adjustment": 1.0, "drivers": []}

    # ─── Gradient Intelligence ──────────────────────────────────────

    def get_fresh_gradient(
        self, archetype: str = "", category: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Get freshly computed gradient field (Task 8).

        Returns gradient vector, optimal targets, and optimization priorities.
        """
        key = f"informativ:gradient:{archetype or 'universal'}:{category or 'universal'}"
        data = self._read_hash(key)
        if data:
            return {
                "gradient_vector": self._parse_json_field(data, "gradient_vector", {}),
                "optimal_targets": self._parse_json_field(data, "optimal_targets", {}),
                "optimization_priorities": self._parse_json_field(
                    data, "optimization_priorities", [],
                ),
                "sample_size": int(data.get("sample_size", 0)),
            }
        return None

    # ─── Full Intelligence Bundle ───────────────────────────────────

    def get_full_intelligence(
        self,
        domain: str = "",
        category: str = "",
        brand_id: str = "",
        archetype: str = "",
    ) -> Dict[str, Any]:
        """Get ALL available strengthening intelligence for a bid request.

        This is the primary entry point for the bilateral cascade.
        Returns everything the system knows from daily strengthening.
        """
        return {
            "environmental_context": self.get_environmental_context(),
            "mechanism_modifiers": self.get_mechanism_modifiers(domain, category),
            "brand_complement": self.get_brand_complement(brand_id) if brand_id else {},
            "category_temperature": self.get_category_temperature(category) if category else {},
            "gradient": self.get_fresh_gradient(archetype, category),
            "intelligence_source": "daily_strengthening",
            "retrieved_at": time.time(),
        }


# ── Singleton ──────────────────────────────────────────────────────────

_consumer: Optional[IntelligenceConsumer] = None


def get_intelligence_consumer() -> IntelligenceConsumer:
    """Get the singleton IntelligenceConsumer."""
    global _consumer
    if _consumer is None:
        _consumer = IntelligenceConsumer()
    return _consumer
