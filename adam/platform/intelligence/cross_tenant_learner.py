"""
Cross-Tenant Learning Aggregator

Aggregates anonymized learning signals across tenants to improve the
shared intelligence graph. Privacy-safe: no tenant-specific data crosses
boundaries, only aggregate statistical patterns.

This is the flywheel effect: every tenant's outcomes improve
the intelligence for ALL tenants.

Signals aggregated:
  - Mechanism effectiveness by category/archetype
  - NDF profile → outcome correlations
  - Segment performance benchmarks
  - Creative strategy effectiveness
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AggregateSignal:
    """Accumulated learning signal across multiple tenants."""

    __slots__ = ("count", "sum_value", "sum_sq", "min_val", "max_val", "last_updated")

    def __init__(self):
        self.count: int = 0
        self.sum_value: float = 0.0
        self.sum_sq: float = 0.0
        self.min_val: float = float("inf")
        self.max_val: float = float("-inf")
        self.last_updated: Optional[datetime] = None

    def add(self, value: float) -> None:
        self.count += 1
        self.sum_value += value
        self.sum_sq += value * value
        self.min_val = min(self.min_val, value)
        self.max_val = max(self.max_val, value)
        self.last_updated = datetime.now(timezone.utc)

    @property
    def mean(self) -> float:
        return self.sum_value / self.count if self.count > 0 else 0.0

    @property
    def variance(self) -> float:
        if self.count < 2:
            return 0.0
        return (self.sum_sq / self.count) - (self.mean ** 2)

    @property
    def std(self) -> float:
        return self.variance ** 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "count": self.count,
            "mean": round(self.mean, 4),
            "std": round(self.std, 4),
            "min": round(self.min_val, 4) if self.min_val != float("inf") else None,
            "max": round(self.max_val, 4) if self.max_val != float("-inf") else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }


class CrossTenantLearner:
    """
    Aggregates anonymized outcome signals across tenants.

    All aggregation is done at the statistical level — no individual
    tenant data, user data, or content data is stored. Only aggregate
    patterns (mechanism effectiveness, segment performance, etc.).
    """

    def __init__(self, learning_hub=None, neo4j_driver=None):
        self._learning_hub = learning_hub
        self._neo4j = neo4j_driver

        self._mechanism_effectiveness: Dict[str, AggregateSignal] = defaultdict(AggregateSignal)
        self._mechanism_by_category: Dict[Tuple[str, str], AggregateSignal] = defaultdict(AggregateSignal)
        self._mechanism_by_archetype: Dict[Tuple[str, str], AggregateSignal] = defaultdict(AggregateSignal)
        self._segment_performance: Dict[str, AggregateSignal] = defaultdict(AggregateSignal)
        self._ndf_outcome_correlation: Dict[str, AggregateSignal] = defaultdict(AggregateSignal)
        self._blueprint_performance: Dict[str, AggregateSignal] = defaultdict(AggregateSignal)

        self._total_outcomes: int = 0
        self._promotion_window_start: Optional[datetime] = None

    async def ingest_outcome(
        self,
        outcome_type: str,
        outcome_value: float,
        mechanisms: Optional[List[str]] = None,
        archetype: Optional[str] = None,
        category: Optional[str] = None,
        segments: Optional[List[str]] = None,
        ndf_profile: Optional[Dict[str, float]] = None,
        blueprint_type: Optional[str] = None,
    ) -> None:
        """
        Ingest an anonymized outcome signal into aggregate statistics.
        Called by OutcomeBridge after processing tenant-specific outcomes.
        """
        self._total_outcomes += 1

        if mechanisms:
            for m in mechanisms:
                self._mechanism_effectiveness[m].add(outcome_value)
                if category:
                    self._mechanism_by_category[(m, category)].add(outcome_value)
                if archetype:
                    self._mechanism_by_archetype[(m, archetype)].add(outcome_value)

        if segments:
            for s in segments:
                self._segment_performance[s].add(outcome_value)

        if ndf_profile and outcome_value > 0:
            for dim, val in ndf_profile.items():
                self._ndf_outcome_correlation[dim].add(val)

        if blueprint_type:
            self._blueprint_performance[blueprint_type].add(outcome_value)

    def get_mechanism_prior(self, mechanism: str) -> Dict[str, Any]:
        """Get cross-tenant aggregate prior for a mechanism."""
        sig = self._mechanism_effectiveness.get(mechanism)
        if not sig or sig.count < 5:
            return {"mechanism": mechanism, "prior": None, "insufficient_data": True}
        return {"mechanism": mechanism, "prior": sig.to_dict()}

    def get_mechanism_priors_for_category(self, category: str) -> Dict[str, Dict]:
        """Get mechanism priors filtered by category."""
        result = {}
        for (m, cat), sig in self._mechanism_by_category.items():
            if cat == category and sig.count >= 3:
                result[m] = sig.to_dict()
        return result

    def get_mechanism_priors_for_archetype(self, archetype: str) -> Dict[str, Dict]:
        """Get mechanism priors filtered by archetype."""
        result = {}
        for (m, arch), sig in self._mechanism_by_archetype.items():
            if arch == archetype and sig.count >= 3:
                result[m] = sig.to_dict()
        return result

    def get_segment_benchmarks(self) -> Dict[str, Dict]:
        """Get performance benchmarks for all segments."""
        return {
            seg: sig.to_dict()
            for seg, sig in self._segment_performance.items()
            if sig.count >= 5
        }

    def get_blueprint_benchmarks(self) -> Dict[str, Dict]:
        """Get performance by blueprint type."""
        return {
            bp: sig.to_dict()
            for bp, sig in self._blueprint_performance.items()
            if sig.count >= 3
        }

    async def promote_to_graph(self, min_observations: int = 50) -> int:
        """
        Promote strong aggregate patterns into the Neo4j graph
        as cross-tenant priors. These feed back into the
        cold start and Bayesian fusion systems.
        """
        if not self._neo4j:
            return 0

        promoted = 0
        async with self._neo4j.session() as session:
            for mechanism, sig in self._mechanism_effectiveness.items():
                if sig.count < min_observations:
                    continue

                await session.run(
                    """
                    MERGE (cp:CrossTenantPrior {mechanism: $mechanism})
                    SET cp.mean_effectiveness = $mean,
                        cp.std_effectiveness = $std,
                        cp.observation_count = $count,
                        cp.updated_at = datetime()
                    """,
                    mechanism=mechanism,
                    mean=sig.mean,
                    std=sig.std,
                    count=sig.count,
                )
                promoted += 1

        logger.info("Promoted %d cross-tenant priors to graph", promoted)
        return promoted

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_outcomes_ingested": self._total_outcomes,
            "mechanisms_tracked": len(self._mechanism_effectiveness),
            "category_pairs_tracked": len(self._mechanism_by_category),
            "archetype_pairs_tracked": len(self._mechanism_by_archetype),
            "segments_tracked": len(self._segment_performance),
            "blueprints_tracked": len(self._blueprint_performance),
            "top_mechanisms": {
                m: round(s.mean, 4)
                for m, s in sorted(
                    self._mechanism_effectiveness.items(),
                    key=lambda x: x[1].mean,
                    reverse=True,
                )[:5]
                if s.count >= 5
            },
        }


_cross_tenant_learner: Optional[CrossTenantLearner] = None


def get_cross_tenant_learner(
    learning_hub=None, neo4j_driver=None
) -> CrossTenantLearner:
    global _cross_tenant_learner
    if _cross_tenant_learner is None:
        _cross_tenant_learner = CrossTenantLearner(
            learning_hub=learning_hub,
            neo4j_driver=neo4j_driver,
        )
    return _cross_tenant_learner
