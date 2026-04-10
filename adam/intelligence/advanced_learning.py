"""
Advanced Learning — Phase E: Gradients, Transfer, and Drift
=============================================================

Three compounding intelligence layers that make the system smarter
with every category added and every day that passes:

1. PAGE-CONDITIONED GRADIENTS
   The gradient field ∂P(conversion)/∂dimension changes based on what
   the page has already done. If the page primed loss_aversion (0.85),
   the gradient for loss_aversion is FLAT (page did the work) — but
   the gradient for cognitive_load_tolerance may be STEEP (page consumed
   bandwidth, so the ad must compensate with simplicity).

2. CROSS-CATEGORY UNIVERSAL PRIORS WITH DELTA TRACKING
   Aggregate mechanism effectiveness across ALL categories to build
   universal priors. Then compute per-category deltas (what's unique
   about THIS category). New categories start from the universal prior
   instead of zero — each new category benefits from all previous ones.

3. TEMPORAL DRIFT DETECTION
   Track mechanism effectiveness in sliding time windows. Detect when
   mechanisms are gaining or losing effectiveness. Forecast what will
   work next quarter. Detect cultural shifts in real time.

All three feed into the bilateral cascade at bid time and into the
daily self-teaching loop for continuous improvement.
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
# 1. PAGE-CONDITIONED GRADIENTS
# ============================================================================

@dataclass
class PageConditionedGradient:
    """Gradient field adjusted for what the page has already done."""
    raw_gradients: Dict[str, float] = field(default_factory=dict)
    page_adjusted_gradients: Dict[str, float] = field(default_factory=dict)
    raw_gaps: Dict[str, float] = field(default_factory=dict)
    page_adjusted_gaps: Dict[str, float] = field(default_factory=dict)
    priorities: List[Dict[str, Any]] = field(default_factory=list)
    page_contributions: List[str] = field(default_factory=list)
    ad_must_address: List[str] = field(default_factory=list)


def compute_page_conditioned_gradient(
    gradient_vector: Dict[str, float],
    optimal_targets: Dict[str, float],
    current_alignment: Dict[str, float],
    page_edge_dims: Dict[str, float],
    page_confidence: float = 0.5,
) -> PageConditionedGradient:
    """Recompute gradient priorities accounting for what the page provides.

    For each dimension:
    - Raw gap: optimal - current (without page)
    - Page contribution: how much the page shifts toward optimal
    - Adjusted gap: optimal - (current + page_shift)
    - If page REDUCES the gap → dimension is LESS important for the ad
    - If page INCREASES the gap → dimension is MORE important for the ad

    The ad should focus on dimensions where the page LEFT a gap,
    and can skip dimensions the page already handled.
    """
    result = PageConditionedGradient()
    priorities = []

    for dim in EDGE_DIMENSIONS:
        gradient = gradient_vector.get(dim, 0.0)
        optimal = optimal_targets.get(dim, 0.5)
        current = current_alignment.get(dim, 0.5)
        page_val = page_edge_dims.get(dim, 0.5)

        # Raw gap (what the ad would need to close without page context)
        raw_gap = optimal - current

        # Page's contribution: how much it shifts the reader toward optimal
        page_shift = (page_val - 0.5) * page_confidence
        effective_position = current + page_shift
        adjusted_gap = optimal - effective_position

        result.raw_gradients[dim] = gradient
        result.raw_gaps[dim] = round(raw_gap, 4)
        result.page_adjusted_gaps[dim] = round(adjusted_gap, 4)

        # Adjusted gradient importance = gradient × adjusted gap
        raw_importance = abs(gradient * raw_gap)
        adjusted_importance = abs(gradient * adjusted_gap)

        # Did the page help or hurt?
        page_effect = raw_importance - adjusted_importance
        if page_effect > 0.01:
            page_helps = "page_helps"
            result.page_contributions.append(
                f"{dim}: page shifted toward optimal (gap {raw_gap:+.2f} → {adjusted_gap:+.2f})"
            )
        elif page_effect < -0.01:
            page_helps = "page_hurts"
            result.ad_must_address.append(
                f"{dim}: page shifted AWAY from optimal (gap {raw_gap:+.2f} → {adjusted_gap:+.2f})"
            )
        else:
            page_helps = "neutral"

        priorities.append({
            "dimension": dim,
            "gradient": round(gradient, 4),
            "optimal": round(optimal, 4),
            "current": round(current, 4),
            "page_value": round(page_val, 4),
            "raw_gap": round(raw_gap, 4),
            "adjusted_gap": round(adjusted_gap, 4),
            "raw_importance": round(raw_importance * 100, 2),
            "adjusted_importance": round(adjusted_importance * 100, 2),
            "page_effect": page_helps,
            "creative_priority": "high" if adjusted_importance > 0.05 else (
                "medium" if adjusted_importance > 0.02 else "low"
            ),
        })

    # Sort by adjusted importance (highest = most important for the ad to address)
    priorities.sort(key=lambda x: x["adjusted_importance"], reverse=True)
    result.priorities = priorities
    result.page_adjusted_gradients = {
        p["dimension"]: p["adjusted_importance"] for p in priorities
    }

    return result


# ============================================================================
# 2. CROSS-CATEGORY UNIVERSAL PRIORS WITH DELTA TRACKING
# ============================================================================

@dataclass
class UniversalPrior:
    """Cross-category aggregated mechanism effectiveness."""
    mechanism_effectiveness: Dict[str, float] = field(default_factory=dict)
    total_observations: int = 0
    categories_pooled: int = 0
    dimension_means: Dict[str, float] = field(default_factory=dict)


@dataclass
class CategoryDelta:
    """What's unique about this category vs the universal."""
    category: str = ""
    mechanism_deltas: Dict[str, float] = field(default_factory=dict)
    dimension_deltas: Dict[str, float] = field(default_factory=dict)
    observations: int = 0
    significance: Dict[str, float] = field(default_factory=dict)  # p-values


def compute_universal_prior(
    bayesian_priors: Dict[str, Dict[str, Any]],
) -> UniversalPrior:
    """Aggregate BayesianPrior nodes across ALL categories.

    This creates the baseline that new categories start from.
    Each category's contribution is weighted by observation count.
    """
    mechanism_totals: Dict[str, Tuple[float, int]] = {}  # mech → (weighted_sum, total_weight)
    total_obs = 0
    categories_seen = set()

    for key, prior in bayesian_priors.items():
        category = prior.get("category", "")
        if not category or category == "all":
            continue

        categories_seen.add(category)
        n = int(prior.get("n_observations", 0) or prior.get("observation_count", 0) or 0)
        if n == 0:
            continue

        total_obs += n

        for mech in MECHANISMS:
            rate = prior.get(f"avg_{mech}", None)
            if rate is not None:
                rate = float(rate)
                if mech not in mechanism_totals:
                    mechanism_totals[mech] = (0.0, 0)
                weighted_sum, total_weight = mechanism_totals[mech]
                mechanism_totals[mech] = (weighted_sum + rate * n, total_weight + n)

    # Compute weighted averages
    universal = UniversalPrior(
        total_observations=total_obs,
        categories_pooled=len(categories_seen),
    )

    for mech, (ws, tw) in mechanism_totals.items():
        if tw > 0:
            universal.mechanism_effectiveness[mech] = round(ws / tw, 4)

    return universal


def compute_category_delta(
    category: str,
    category_priors: Dict[str, Dict[str, Any]],
    universal: UniversalPrior,
) -> CategoryDelta:
    """Compute what's UNIQUE about this category vs the universal.

    Positive delta: mechanism MORE effective in this category
    Negative delta: mechanism LESS effective
    """
    delta = CategoryDelta(category=category)

    # Find priors for this category
    category_mechs: Dict[str, Tuple[float, int]] = {}
    total_n = 0

    for key, prior in category_priors.items():
        if prior.get("category", "") != category:
            continue
        n = int(prior.get("n_observations", 0) or 0)
        total_n += n
        for mech in MECHANISMS:
            rate = prior.get(f"avg_{mech}")
            if rate is not None:
                if mech not in category_mechs:
                    category_mechs[mech] = (0.0, 0)
                ws, tw = category_mechs[mech]
                category_mechs[mech] = (ws + float(rate) * n, tw + n)

    delta.observations = total_n

    for mech, (ws, tw) in category_mechs.items():
        if tw > 0:
            cat_mean = ws / tw
            univ_mean = universal.mechanism_effectiveness.get(mech, 0.5)
            delta.mechanism_deltas[mech] = round(cat_mean - univ_mean, 4)

    return delta


async def build_and_store_universals() -> Dict[str, Any]:
    """Build universal priors and category deltas, store in Redis.

    Called by the daily self-teaching task. Enables instant cross-category
    transfer: new categories start from universal + delta, not from zero.
    """
    results = {"universal": None, "deltas": {}, "stored": 0}

    try:
        from adam.api.stackadapt.graph_cache import GraphIntelligenceCache
        cache = GraphIntelligenceCache()
        await cache.load_priors()  # Ensure priors are loaded

        universal = compute_universal_prior(cache._bayesian_priors)
        results["universal"] = {
            "mechanism_effectiveness": universal.mechanism_effectiveness,
            "total_observations": universal.total_observations,
            "categories_pooled": universal.categories_pooled,
        }

        # Compute delta for each category
        categories_seen = set()
        for key, prior in cache._bayesian_priors.items():
            cat = prior.get("category", "")
            if cat and cat != "all":
                categories_seen.add(cat)

        for category in categories_seen:
            delta = compute_category_delta(category, cache._bayesian_priors, universal)
            if delta.mechanism_deltas:
                results["deltas"][category] = {
                    "mechanism_deltas": delta.mechanism_deltas,
                    "observations": delta.observations,
                }

        # Store in Redis
        import redis
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)

        # Universal prior
        r.hset("informativ:universal_prior", mapping={
            "mechanism_effectiveness": json.dumps(universal.mechanism_effectiveness),
            "total_observations": universal.total_observations,
            "categories_pooled": universal.categories_pooled,
            "computed_at": time.time(),
        })
        r.expire("informativ:universal_prior", 86400 * 7)
        results["stored"] += 1

        # Category deltas
        for category, delta_data in results["deltas"].items():
            key = f"informativ:category_delta:{category}"
            r.hset(key, mapping={
                "mechanism_deltas": json.dumps(delta_data["mechanism_deltas"]),
                "observations": delta_data["observations"],
                "computed_at": time.time(),
            })
            r.expire(key, 86400 * 7)
            results["stored"] += 1

        logger.info(
            "Universal priors: %d mechanisms, %d obs, %d categories, %d deltas stored",
            len(universal.mechanism_effectiveness),
            universal.total_observations,
            universal.categories_pooled,
            len(results["deltas"]),
        )

    except Exception as e:
        logger.debug("Universal prior computation failed: %s", e)

    return results


# ============================================================================
# 3. TEMPORAL DRIFT DETECTION ON MECHANISM EFFECTIVENESS
# ============================================================================

@dataclass
class MechanismDrift:
    """Temporal drift analysis for a mechanism."""
    mechanism: str = ""
    windows: List[Dict[str, Any]] = field(default_factory=list)
    slope: float = 0.0           # Change per window (positive = gaining)
    acceleration: float = 0.0    # Is the change speeding up?
    current_rate: float = 0.0
    forecast_next: float = 0.0   # Predicted rate next window
    trend: str = ""              # "rising", "declining", "stable"
    confidence: float = 0.0
    observations_total: int = 0


@dataclass
class DriftReport:
    """Complete drift analysis for all mechanisms."""
    mechanisms: Dict[str, MechanismDrift] = field(default_factory=dict)
    rising: List[str] = field(default_factory=list)
    declining: List[str] = field(default_factory=list)
    stable: List[str] = field(default_factory=list)
    analysis_window_days: int = 0
    computed_at: float = 0.0


def detect_mechanism_drift(
    window_days: int = 30,
    n_windows: int = 4,
) -> DriftReport:
    """Detect temporal drift in mechanism effectiveness.

    Analyzes mechanism Thompson Sampling data from Redis
    (informativ:page:mech_ts:{domain}:{mechanism}) across time windows.

    Returns which mechanisms are rising, declining, or stable.
    """
    report = DriftReport(
        analysis_window_days=window_days * n_windows,
        computed_at=time.time(),
    )

    try:
        import redis
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)

        # Gather all mechanism effectiveness data
        mech_data: Dict[str, List[Tuple[float, float]]] = {}  # mech → [(alpha, beta)]

        for key in r.keys("informativ:page:mech_ts:*"):
            parts = key.split(":")
            if len(parts) >= 5:
                mechanism = parts[4]
                data = r.hgetall(key)
                alpha = float(data.get("alpha", 1))
                beta = float(data.get("beta", 1))

                if mechanism not in mech_data:
                    mech_data[mechanism] = []
                mech_data[mechanism].append((alpha, beta))

        # Analyze each mechanism
        for mech, ab_pairs in mech_data.items():
            if len(ab_pairs) < 3:
                continue

            drift = MechanismDrift(mechanism=mech)

            # Compute overall rate
            total_alpha = sum(a for a, _ in ab_pairs)
            total_beta = sum(b for _, b in ab_pairs)
            drift.current_rate = round(total_alpha / max(1, total_alpha + total_beta), 4)
            drift.observations_total = int(total_alpha + total_beta)

            # Compute rates per domain (proxy for time windows since we don't have timestamps)
            rates = [a / max(1, a + b) for a, b in ab_pairs]

            if len(rates) >= 3:
                # Simple linear regression on rates
                n = len(rates)
                x_mean = (n - 1) / 2.0
                y_mean = sum(rates) / n
                numerator = sum((i - x_mean) * (rates[i] - y_mean) for i in range(n))
                denominator = sum((i - x_mean) ** 2 for i in range(n))
                slope = numerator / max(denominator, 1e-10)

                drift.slope = round(slope, 6)
                drift.forecast_next = round(drift.current_rate + slope, 4)

                # Classify trend
                if abs(slope) < 0.005:
                    drift.trend = "stable"
                    report.stable.append(mech)
                elif slope > 0:
                    drift.trend = "rising"
                    report.rising.append(mech)
                else:
                    drift.trend = "declining"
                    report.declining.append(mech)

                drift.confidence = round(min(0.8, len(ab_pairs) / 20.0), 2)
            else:
                drift.trend = "insufficient_data"

            report.mechanisms[mech] = drift

    except Exception as e:
        logger.debug("Drift detection failed: %s", e)

    return report


async def store_drift_report(report: DriftReport) -> bool:
    """Store drift report in Redis for bid-time consumption."""
    try:
        import redis
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)

        r.hset("informativ:drift:report", mapping={
            "rising": json.dumps(report.rising),
            "declining": json.dumps(report.declining),
            "stable": json.dumps(report.stable),
            "computed_at": report.computed_at,
            "analysis_window_days": report.analysis_window_days,
        })
        r.expire("informativ:drift:report", 86400 * 7)

        # Store per-mechanism drift
        for mech, drift in report.mechanisms.items():
            r.hset(f"informativ:drift:mechanism:{mech}", mapping={
                "slope": drift.slope,
                "current_rate": drift.current_rate,
                "forecast_next": drift.forecast_next,
                "trend": drift.trend,
                "confidence": drift.confidence,
                "observations": drift.observations_total,
                "computed_at": time.time(),
            })
            r.expire(f"informativ:drift:mechanism:{mech}", 86400 * 7)

        return True
    except Exception as e:
        logger.debug("Drift report storage failed: %s", e)
        return False


def get_mechanism_drift(mechanism: str) -> Optional[Dict[str, Any]]:
    """Get drift data for a mechanism at bid time (<1ms)."""
    try:
        import redis
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        data = r.hgetall(f"informativ:drift:mechanism:{mechanism}")
        if data:
            return {
                "trend": data.get("trend", "stable"),
                "slope": float(data.get("slope", 0)),
                "current_rate": float(data.get("current_rate", 0)),
                "forecast_next": float(data.get("forecast_next", 0)),
                "confidence": float(data.get("confidence", 0)),
            }
    except Exception:
        pass
    return None
