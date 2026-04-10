"""
Causal Learning Engine — Every Impression Is A Micro-Experiment
=================================================================

This module treats every ad impression as a controlled experiment:
- Treatment: which mechanism was deployed, what creative parameters
- Context: the page's 20-dim edge profile at decision time
- Subject: the buyer's uncertainty profile
- Outcome: conversion, click, engagement, or nothing

With enough observations, the system asks causal questions:
- "Does page dimension X CAUSE mechanism Y to be more effective?"
- "Is the effect of mechanism Y MODERATED by page context Z?"
- "Does page state A → buyer state B → mechanism C (mediation)?"

Validated discoveries become graph edges:
    (:PageDimension)-[:AMPLIFIES {strength, p_value, n}]->(:CognitiveMechanism)

These edges are DISCOVERED from data, not programmed. The cascade
queries them at bid time, so its mechanism scoring evolves from
empirical evidence rather than hardcoded theory weights.

Storage:
    Redis: informativ:causal:observations — circular buffer of recent observations
    Redis: informativ:causal:tests — test results
    Redis: informativ:causal:discoveries — validated causal links
    Neo4j: (:PageDimension)-[:AMPLIFIES|:SUPPRESSES|:MODERATES]->(:CognitiveMechanism)
"""

from __future__ import annotations

import json
import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

EDGE_DIMENSIONS = [
    "regulatory_fit", "construal_fit", "personality_alignment",
    "emotional_resonance", "value_alignment", "evolutionary_motive",
    "linguistic_style", "persuasion_susceptibility", "cognitive_load_tolerance",
    "narrative_transport", "social_proof_sensitivity", "loss_aversion_intensity",
    "temporal_discounting", "brand_relationship_depth", "autonomy_reactance",
    "information_seeking", "mimetic_desire", "interoceptive_awareness",
    "cooperative_framing_fit", "decision_entropy",
]

MECHANISMS = [
    "authority", "social_proof", "scarcity", "loss_aversion",
    "commitment", "liking", "reciprocity", "curiosity",
    "cognitive_ease", "unity",
]


# ============================================================================
# CAUSAL OBSERVATION — one impression treated as a micro-experiment
# ============================================================================

@dataclass
class CausalObservation:
    """A single impression with all four sides of the equation."""

    # Identity
    decision_id: str = ""
    timestamp: float = 0.0

    # Treatment (what we chose)
    mechanism_sent: str = ""
    secondary_mechanism: str = ""
    framing: str = ""
    cascade_level: int = 0

    # Context (the page's 20-dim psychological state)
    page_edge_dimensions: Dict[str, float] = field(default_factory=dict)
    page_domain: str = ""
    page_category: str = ""
    page_scoring_tier: str = ""
    page_confidence: float = 0.0

    # Subject (what we know about the buyer)
    buyer_id: str = ""
    archetype: str = ""
    buyer_edge_dimensions: Dict[str, float] = field(default_factory=dict)
    buyer_confidence: float = 0.0

    # Product
    asin: str = ""
    product_category: str = ""

    # Evidence used
    mechanism_scores: Dict[str, float] = field(default_factory=dict)
    edge_count: int = 0

    # Outcome (the dependent variable)
    outcome_type: str = ""  # conversion, click, engagement, bounce, skip
    outcome_value: float = 0.0
    success: bool = False

    def to_compact_dict(self) -> Dict[str, Any]:
        """Compact serialization for Redis storage."""
        return {
            "did": self.decision_id,
            "ts": self.timestamp,
            "mech": self.mechanism_sent,
            "frm": self.framing,
            "cl": self.cascade_level,
            "p_dims": self.page_edge_dimensions,
            "p_dom": self.page_domain,
            "p_cat": self.page_category,
            "p_tier": self.page_scoring_tier,
            "p_conf": self.page_confidence,
            "buyer": self.buyer_id,
            "arch": self.archetype,
            "b_dims": self.buyer_edge_dimensions,
            "asin": self.asin,
            "p_category": self.product_category,
            "m_scores": self.mechanism_scores,
            "outcome": self.outcome_type,
            "o_val": self.outcome_value,
            "success": self.success,
        }

    @classmethod
    def from_compact_dict(cls, d: Dict[str, Any]) -> "CausalObservation":
        return cls(
            decision_id=d.get("did", ""),
            timestamp=d.get("ts", 0),
            mechanism_sent=d.get("mech", ""),
            framing=d.get("frm", ""),
            cascade_level=d.get("cl", 0),
            page_edge_dimensions=d.get("p_dims", {}),
            page_domain=d.get("p_dom", ""),
            page_category=d.get("p_cat", ""),
            page_scoring_tier=d.get("p_tier", ""),
            page_confidence=d.get("p_conf", 0),
            buyer_id=d.get("buyer", ""),
            archetype=d.get("arch", ""),
            buyer_edge_dimensions=d.get("b_dims", {}),
            asin=d.get("asin", ""),
            product_category=d.get("p_category", ""),
            mechanism_scores=d.get("m_scores", {}),
            outcome_type=d.get("outcome", ""),
            outcome_value=d.get("o_val", 0),
            success=d.get("success", False),
        )


# ============================================================================
# OBSERVATION RECORDING — called from outcome_handler
# ============================================================================

_MAX_OBSERVATIONS = 50000  # Keep last 50K observations in Redis
_OBSERVATION_KEY = "informativ:causal:observations"


def record_causal_observation(
    decision_id: str,
    outcome_type: str,
    outcome_value: float,
    metadata: Dict[str, Any],
) -> Optional[CausalObservation]:
    """Record a causal observation from an outcome event.

    Called from OutcomeHandler.process_outcome() after metadata is unpacked.
    Returns the observation if recorded successfully.
    """
    success = outcome_type in ("conversion", "click", "engagement") and outcome_value > 0.5

    obs = CausalObservation(
        decision_id=decision_id,
        timestamp=time.time(),
        mechanism_sent=metadata.get("mechanism_sent", ""),
        secondary_mechanism=metadata.get("secondary_mechanism", ""),
        framing=metadata.get("framing", ""),
        cascade_level=metadata.get("cascade_level", 0),
        page_edge_dimensions=metadata.get("page_edge_dimensions", {}),
        page_domain=metadata.get("context_domain", ""),
        page_category=metadata.get("content_category", ""),
        page_scoring_tier=metadata.get("page_edge_scoring_tier", ""),
        page_confidence=metadata.get("page_confidence", 0.0),
        buyer_id=metadata.get("buyer_id", ""),
        archetype=metadata.get("archetype", ""),
        buyer_edge_dimensions=metadata.get("alignment_scores", {}),
        asin=metadata.get("asin", ""),
        product_category=metadata.get("product_category", ""),
        mechanism_scores=metadata.get("mechanism_scores", {}),
        outcome_type=outcome_type,
        outcome_value=outcome_value,
        success=success,
    )

    # Store in Redis circular buffer
    try:
        import redis
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        r.lpush(_OBSERVATION_KEY, json.dumps(obs.to_compact_dict()))
        r.ltrim(_OBSERVATION_KEY, 0, _MAX_OBSERVATIONS - 1)
    except Exception as e:
        logger.debug("Causal observation recording failed: %s", e)
        return None

    return obs


def get_observations(limit: int = 10000) -> List[CausalObservation]:
    """Retrieve recent causal observations from Redis."""
    try:
        import redis
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        raw = r.lrange(_OBSERVATION_KEY, 0, limit - 1)
        return [CausalObservation.from_compact_dict(json.loads(item)) for item in raw]
    except Exception:
        return []


# ============================================================================
# STATISTICAL TESTING ENGINE
# ============================================================================

@dataclass
class TestResult:
    """Result of a single causal hypothesis test."""
    hypothesis: str = ""
    test_type: str = ""  # "direct_effect", "interaction", "mediation"
    dimension: str = ""
    mechanism: str = ""
    effect_size: float = 0.0  # Cohen's d or odds ratio
    p_value: float = 1.0
    n_total: int = 0
    n_high: int = 0
    n_low: int = 0
    rate_high: float = 0.0
    rate_low: float = 0.0
    significant: bool = False
    direction: str = ""  # "amplifies" or "suppresses"
    confidence_interval: Tuple[float, float] = (0.0, 0.0)


class CausalTestEngine:
    """Runs statistical tests on accumulated causal observations."""

    def test_dimension_amplifies_mechanism(
        self,
        dimension: str,
        mechanism: str,
        observations: List[CausalObservation],
        split_point: float = 0.5,
    ) -> TestResult:
        """Does page dimension X amplify mechanism Y's effectiveness?

        Method: Split observations into high/low on dimension X
        (among those where mechanism Y was sent). Compare conversion rates.

        Statistical test: Two-proportion z-test + Cohen's h effect size.
        """
        # Filter to observations where this mechanism was sent
        mech_obs = [o for o in observations if o.mechanism_sent == mechanism]
        if len(mech_obs) < 20:
            return TestResult(
                hypothesis=f"{dimension} amplifies {mechanism}",
                test_type="direct_effect",
                dimension=dimension, mechanism=mechanism,
                n_total=len(mech_obs),
            )

        # Split by page dimension value
        high = [o for o in mech_obs if o.page_edge_dimensions.get(dimension, 0.5) > split_point]
        low = [o for o in mech_obs if o.page_edge_dimensions.get(dimension, 0.5) <= split_point]

        if len(high) < 10 or len(low) < 10:
            return TestResult(
                hypothesis=f"{dimension} amplifies {mechanism}",
                test_type="direct_effect",
                dimension=dimension, mechanism=mechanism,
                n_total=len(mech_obs), n_high=len(high), n_low=len(low),
            )

        # Compute conversion rates
        rate_high = sum(1 for o in high if o.success) / len(high)
        rate_low = sum(1 for o in low if o.success) / len(low)

        # Two-proportion z-test
        n1, n2 = len(high), len(low)
        p1, p2 = rate_high, rate_low
        p_pooled = (p1 * n1 + p2 * n2) / (n1 + n2)

        if p_pooled == 0 or p_pooled == 1:
            z = 0.0
        else:
            se = math.sqrt(p_pooled * (1 - p_pooled) * (1/n1 + 1/n2))
            z = (p1 - p2) / max(se, 1e-10)

        # Two-tailed p-value (approximation using normal CDF)
        p_value = 2 * (1 - _normal_cdf(abs(z)))

        # Cohen's h effect size
        h1 = 2 * math.asin(math.sqrt(max(0, min(1, p1))))
        h2 = 2 * math.asin(math.sqrt(max(0, min(1, p2))))
        cohens_h = abs(h1 - h2)

        significant = p_value < 0.05 and cohens_h > 0.2
        direction = "amplifies" if p1 > p2 else "suppresses"

        return TestResult(
            hypothesis=f"Page {dimension} {'amplifies' if p1 > p2 else 'suppresses'} {mechanism}",
            test_type="direct_effect",
            dimension=dimension,
            mechanism=mechanism,
            effect_size=round(cohens_h, 4),
            p_value=round(p_value, 6),
            n_total=len(mech_obs),
            n_high=n1,
            n_low=n2,
            rate_high=round(rate_high, 4),
            rate_low=round(rate_low, 4),
            significant=significant,
            direction=direction,
        )

    def test_all_direct_effects(
        self,
        observations: List[CausalObservation],
        min_observations: int = 30,
    ) -> List[TestResult]:
        """Test all (dimension, mechanism) pairs for direct effects.

        20 dimensions × 10 mechanisms = 200 tests.
        Applies Benjamini-Hochberg FDR correction for multiple comparisons.
        """
        results = []

        for dim in EDGE_DIMENSIONS:
            # Only test dims where we have page edge data
            has_data = sum(1 for o in observations
                          if dim in o.page_edge_dimensions
                          and o.page_edge_dimensions[dim] != 0.5)
            if has_data < min_observations:
                continue

            for mech in MECHANISMS:
                result = self.test_dimension_amplifies_mechanism(
                    dim, mech, observations,
                )
                if result.n_total >= min_observations:
                    results.append(result)

        # Benjamini-Hochberg FDR correction
        results = _apply_bh_correction(results)

        return results

    def test_cross_category_universality(
        self,
        dimension: str,
        mechanism: str,
        observations: List[CausalObservation],
    ) -> Dict[str, Any]:
        """Test if a dimension→mechanism effect holds across categories.

        A universal effect is one that works in 3+ categories.
        A category-specific effect only works in 1-2 categories.
        """
        # Group by product category
        by_category: Dict[str, List[CausalObservation]] = {}
        for obs in observations:
            cat = obs.product_category or "unknown"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(obs)

        category_results = {}
        categories_significant = 0

        for cat, cat_obs in by_category.items():
            if len(cat_obs) < 20:
                continue
            result = self.test_dimension_amplifies_mechanism(
                dimension, mechanism, cat_obs,
            )
            category_results[cat] = {
                "significant": result.significant,
                "effect_size": result.effect_size,
                "direction": result.direction,
                "n": result.n_total,
            }
            if result.significant:
                categories_significant += 1

        return {
            "dimension": dimension,
            "mechanism": mechanism,
            "categories_tested": len(category_results),
            "categories_significant": categories_significant,
            "is_universal": categories_significant >= 3,
            "is_category_specific": categories_significant == 1,
            "per_category": category_results,
        }


# ============================================================================
# GRAPH INTEGRATION — write validated discoveries to Neo4j
# ============================================================================

async def persist_causal_discovery(
    result: TestResult,
) -> bool:
    """Write a validated causal discovery to Neo4j.

    Creates or updates edges:
    (:PageDimension)-[:AMPLIFIES|:SUPPRESSES]->(:CognitiveMechanism)
    """
    if not result.significant:
        return False

    try:
        from adam.core.dependencies import Infrastructure
        infra = Infrastructure.get_instance()
        if not infra._neo4j_driver:
            try:
                await infra.initialize()
            except Exception:
                pass
        if not infra._neo4j_driver:
            return False

        rel_type = "AMPLIFIES" if result.direction == "amplifies" else "SUPPRESSES"

        async with infra._neo4j_driver.session() as session:
            await session.run(f"""
                MERGE (pd:PageDimension {{name: $dimension}})
                MERGE (m:CognitiveMechanism {{name: $mechanism}})
                MERGE (pd)-[r:{rel_type}]->(m)
                SET r.effect_size = $effect_size,
                    r.p_value = $p_value,
                    r.n_observations = $n,
                    r.rate_high = $rate_high,
                    r.rate_low = $rate_low,
                    r.test_type = $test_type,
                    r.discovered_at = datetime(),
                    r.last_validated = datetime()
            """, {
                "dimension": result.dimension,
                "mechanism": result.mechanism,
                "effect_size": result.effect_size,
                "p_value": result.p_value,
                "n": result.n_total,
                "rate_high": result.rate_high,
                "rate_low": result.rate_low,
                "test_type": result.test_type,
            })
            return True

    except Exception as e:
        logger.debug("Causal discovery persistence failed: %s", e)
        return False


async def query_causal_effects(
    mechanism: str,
) -> Dict[str, Dict[str, Any]]:
    """Query discovered causal effects for a mechanism from Neo4j.

    Returns {dimension: {direction, strength, p_value, n}} for all
    dimensions that causally influence this mechanism's effectiveness.

    Called by the cascade at bid time to adjust mechanism scores
    based on empirical evidence rather than hardcoded weights.
    """
    effects: Dict[str, Dict[str, Any]] = {}

    try:
        from adam.core.dependencies import Infrastructure
        infra = Infrastructure.get_instance()
        if not infra._neo4j_driver:
            return effects

        async with infra._neo4j_driver.session() as session:
            # Query both AMPLIFIES and SUPPRESSES
            result = await session.run("""
                MATCH (pd:PageDimension)-[r:AMPLIFIES|SUPPRESSES]->(m:CognitiveMechanism {name: $mechanism})
                RETURN pd.name AS dimension,
                       type(r) AS effect_type,
                       r.effect_size AS effect_size,
                       r.p_value AS p_value,
                       r.n_observations AS n,
                       r.rate_high AS rate_high,
                       r.rate_low AS rate_low
            """, {"mechanism": mechanism})

            async for record in result:
                dim = record.get("dimension", "")
                if dim:
                    effects[dim] = {
                        "type": record.get("effect_type", "").lower(),
                        "strength": float(record.get("effect_size", 0)),
                        "p_value": float(record.get("p_value", 1)),
                        "n": int(record.get("n", 0)),
                        "rate_high": float(record.get("rate_high", 0)),
                        "rate_low": float(record.get("rate_low", 0)),
                    }

    except Exception as e:
        logger.debug("Causal effect query failed: %s", e)

    return effects


# ============================================================================
# HELPERS
# ============================================================================

def _normal_cdf(x: float) -> float:
    """Approximate standard normal CDF using Abramowitz & Stegun."""
    if x < 0:
        return 1.0 - _normal_cdf(-x)
    t = 1.0 / (1.0 + 0.2316419 * x)
    d = 0.3989422804014327  # 1/sqrt(2*pi)
    p = d * math.exp(-x * x / 2.0) * t * (
        0.319381530 + t * (-0.356563782 + t * (
            1.781477937 + t * (-1.821255978 + t * 1.330274429)
        ))
    )
    return 1.0 - p


def _apply_bh_correction(
    results: List[TestResult],
    alpha: float = 0.05,
) -> List[TestResult]:
    """Benjamini-Hochberg FDR correction for multiple comparisons.

    Re-evaluates significance after correcting for testing 200+ hypotheses.
    """
    if not results:
        return results

    # Sort by p-value
    indexed = [(i, r) for i, r in enumerate(results)]
    indexed.sort(key=lambda x: x[1].p_value)

    m = len(indexed)
    for rank, (orig_idx, result) in enumerate(indexed, 1):
        # BH threshold: (rank / m) * alpha
        threshold = (rank / m) * alpha
        result.significant = result.p_value <= threshold and result.effect_size > 0.2

    return results
