"""
Task 4: Ad Fatigue & Mechanism Wear Detection
=============================================

Analyzes ADAM's own outcome data to detect mechanism fatigue:
mechanisms that show declining effectiveness on specific domains.

Produces:
- MechanismFatigueCurve per (domain, mechanism)
- DomainAdFatigueIndex per domain
- Recommended substitute mechanisms

Consumed at bid time:
- Fatigued mechanisms get effectiveness multiplied by (1 - fatigue_score).
  Substitute mechanisms get corresponding boost.

Redis keys:
- informativ:fatigue:{domain}:{mechanism} -- fatigue + substitute (24h TTL)
- informativ:fatigue:index:{domain} -- overall domain fatigue
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Tuple

from adam.intelligence.daily.base import DailyStrengtheningTask, TaskResult

logger = logging.getLogger(__name__)

# Mechanism substitution graph: when A fatigues, try B
_MECHANISM_SUBSTITUTES = {
    "social_proof": ["authority", "commitment"],
    "authority": ["social_proof", "commitment"],
    "scarcity": ["curiosity", "loss_aversion"],
    "loss_aversion": ["authority", "commitment"],
    "reciprocity": ["liking", "commitment"],
    "commitment": ["reciprocity", "authority"],
    "liking": ["social_proof", "reciprocity"],
    "curiosity": ["scarcity", "social_proof"],
    "unity": ["social_proof", "liking"],
    "cognitive_ease": ["liking", "social_proof"],
}

_ALL_MECHANISMS = list(_MECHANISM_SUBSTITUTES.keys())


class FatigueDetectionTask(DailyStrengtheningTask):
    """Detect mechanism fatigue from outcome data."""

    @property
    def name(self) -> str:
        return "fatigue_detection"

    @property
    def schedule_hours(self) -> List[int]:
        return [4]  # 4 AM UTC

    async def execute(self) -> TaskResult:
        result = TaskResult(task_name=self.name, success=True)

        # Get outcome data from Redis mechanism Thompson Sampling keys
        domain_mechanism_outcomes = await self._gather_outcome_data()

        if not domain_mechanism_outcomes:
            result.details["note"] = "No outcome data available"
            return result

        for domain, mechanism_data in domain_mechanism_outcomes.items():
            result.items_processed += 1

            domain_fatigue_scores = {}

            for mechanism, daily_rates in mechanism_data.items():
                if len(daily_rates) < 3:
                    continue

                # Compute fatigue: declining effectiveness over time
                fatigue_score = self._compute_fatigue(daily_rates)

                # Find best substitute
                substitute = self._find_substitute(mechanism, mechanism_data)

                fatigue_key = f"informativ:fatigue:{domain}:{mechanism}"
                stored = self._store_redis_hash(fatigue_key, {
                    "domain": domain,
                    "mechanism": mechanism,
                    "fatigue_score": round(fatigue_score, 3),
                    "daily_rates": daily_rates,
                    "substitute_mechanism": substitute,
                    "effectiveness_multiplier": round(max(0.2, 1.0 - fatigue_score), 3),
                    "computed_at": time.time(),
                }, ttl=86400)
                if stored:
                    result.items_stored += 1

                domain_fatigue_scores[mechanism] = fatigue_score

                if fatigue_score > 0.5:
                    logger.info(
                        "FATIGUE: %s on %s (score=%.2f, substitute=%s)",
                        mechanism, domain, fatigue_score, substitute,
                    )

            # Store domain-level fatigue index
            if domain_fatigue_scores:
                avg_fatigue = sum(domain_fatigue_scores.values()) / len(domain_fatigue_scores)
                fresh_mechanisms = [m for m, f in domain_fatigue_scores.items() if f < 0.3]
                worn_mechanisms = [m for m, f in domain_fatigue_scores.items() if f > 0.5]

                index_key = f"informativ:fatigue:index:{domain}"
                self._store_redis_hash(index_key, {
                    "domain": domain,
                    "overall_fatigue": round(avg_fatigue, 3),
                    "fresh_mechanisms": fresh_mechanisms,
                    "worn_mechanisms": worn_mechanisms,
                    "mechanism_fatigue_scores": domain_fatigue_scores,
                    "computed_at": time.time(),
                }, ttl=86400)

        result.details["domains_analyzed"] = len(domain_mechanism_outcomes)
        return result

    def _compute_fatigue(self, daily_rates: List[float]) -> float:
        """Compute fatigue score from daily effectiveness rates.

        Fatigue = trend slope (negative = fatiguing).
        Normalized to 0-1 range.
        """
        n = len(daily_rates)
        if n < 2:
            return 0.0

        # Simple linear regression slope
        x_mean = (n - 1) / 2.0
        y_mean = sum(daily_rates) / n

        numerator = sum((i - x_mean) * (daily_rates[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        slope = numerator / denominator

        # Negative slope = declining = fatigue
        # Normalize: slope of -0.1/day -> fatigue 0.7
        fatigue = max(0.0, min(1.0, -slope * 7.0))
        return fatigue

    def _find_substitute(
        self, mechanism: str, mechanism_data: Dict[str, List[float]]
    ) -> str:
        """Find the least-fatigued substitute mechanism."""
        candidates = _MECHANISM_SUBSTITUTES.get(mechanism, _ALL_MECHANISMS[:3])

        best = candidates[0]
        best_fatigue = 1.0

        for candidate in candidates:
            if candidate in mechanism_data:
                fatigue = self._compute_fatigue(mechanism_data[candidate])
                if fatigue < best_fatigue:
                    best = candidate
                    best_fatigue = fatigue
            else:
                # Not used recently -> definitely not fatigued
                return candidate

        return best

    async def _gather_outcome_data(self) -> Dict[str, Dict[str, List[float]]]:
        """Gather mechanism effectiveness data per domain from Redis.

        Reads from informativ:page:mech_ts:{domain}:{mechanism} keys
        that contain Thompson Sampling alpha/beta posteriors.
        """
        r = self._get_redis()
        if not r:
            return {}

        results: Dict[str, Dict[str, List[float]]] = {}

        try:
            # Scan for mechanism Thompson keys
            cursor = 0
            keys = []
            while True:
                cursor, batch = r.scan(cursor, match="informativ:page:mech_ts:*", count=100)
                keys.extend(batch)
                if cursor == 0:
                    break

            for key in keys:
                parts = key.split(":")
                if len(parts) >= 5:
                    domain = parts[3]
                    mechanism = parts[4]

                    data = r.hgetall(key)
                    if data:
                        alpha = float(data.get("alpha", 1))
                        beta = float(data.get("beta", 1))
                        rate = alpha / max(1, alpha + beta)

                        if domain not in results:
                            results[domain] = {}
                        if mechanism not in results[domain]:
                            results[domain][mechanism] = []
                        results[domain][mechanism].append(rate)

        except Exception as e:
            logger.debug("Outcome data gather failed: %s", e)

        return results
