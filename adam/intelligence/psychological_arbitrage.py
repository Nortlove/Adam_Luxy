"""
Psychological Arbitrage Scoring
================================

Finds buyer×product×context combinations where ADAM's predicted conversion
probability diverges most from the market's implied probability.

In financial markets, arbitrage exists when the same asset has different
prices in different markets. In advertising, arbitrage exists when the
market prices an impression based on demographics/behavioral signals,
but the TRUE conversion probability (based on psychological alignment)
is much higher.

The market (other bidders) uses: demographics, browsing history, contextual
category, retargeting signals. These are behavioral CORRELATIONS.

ADAM uses: 27-dimensional bilateral edge alignment, mechanism effectiveness
posteriors, gradient field optimization, buyer uncertainty profiles. These
are psychological CAUSES.

The delta between correlation-based and causation-based predictions is
pure alpha. This module quantifies that delta and returns it to StackAdapt
as an actionable bid signal.

Every impression where arbitrage_score > 1.0 means: "ADAM predicts higher
conversion than the market does. Bid aggressively."
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ArbitrageResult:
    """Quantified psychological arbitrage opportunity."""

    # Core arbitrage signal
    arbitrage_score: float = 1.0
    """Ratio of ADAM's predicted effectiveness vs market baseline.
    >1.0 = ADAM sees more value than the market (bid aggressively).
    <1.0 = ADAM sees less value (bid conservatively).
    1.0 = no divergence."""

    adam_predicted_effectiveness: float = 0.5
    """ADAM's predicted conversion effectiveness based on bilateral edge
    alignment, mechanism selection, and buyer profile (0-1)."""

    market_baseline_effectiveness: float = 0.5
    """Estimated market-implied effectiveness based on segment type,
    category, and device — what a demographics-based system would predict."""

    # Bid guidance
    recommended_bid_multiplier: float = 1.0
    """Suggested multiplier on base CPM bid. Capped at 3.0x to avoid
    runaway bidding during cold-start."""

    alpha_value: float = 0.0
    """Dollar-denominated alpha: how much more value ADAM sees per
    impression vs the market, in CPM units."""

    # Evidence
    confidence: float = 0.0
    """Confidence in the arbitrage estimate (0-1). Based on cascade level,
    edge count, and buyer profile completeness."""

    arbitrage_drivers: List[str] = field(default_factory=list)
    """Which psychological dimensions drive the arbitrage opportunity."""

    reasoning: List[str] = field(default_factory=list)


# Market baseline CPM and conversion rates by segment type.
# These represent what a demographics-only system would expect.
# Source: StackAdapt CPM benchmarks by vertical (public data).
_MARKET_BASELINES = {
    "beauty": {"ctr": 0.08, "cvr": 0.025, "cpm": 4.50},
    "electronics": {"ctr": 0.06, "cvr": 0.018, "cpm": 5.20},
    "health": {"ctr": 0.07, "cvr": 0.022, "cpm": 4.80},
    "finance": {"ctr": 0.05, "cvr": 0.015, "cpm": 8.50},
    "automotive": {"ctr": 0.04, "cvr": 0.008, "cpm": 6.00},
    "food": {"ctr": 0.09, "cvr": 0.030, "cpm": 3.50},
    "fashion": {"ctr": 0.07, "cvr": 0.020, "cpm": 4.20},
    "travel": {"ctr": 0.06, "cvr": 0.012, "cpm": 5.80},
    "default": {"ctr": 0.06, "cvr": 0.018, "cpm": 4.00},
}


def compute_arbitrage(
    cascade_level: int,
    mechanism_scores: Dict[str, float],
    edge_dimensions: Optional[Dict[str, float]] = None,
    buyer_confidence: float = 0.0,
    category: str = "",
    context_mindset: str = "",
    gradient_priorities: Optional[List[Dict[str, Any]]] = None,
    base_cpm: float = 4.00,
) -> ArbitrageResult:
    """Compute psychological arbitrage score.

    Compares ADAM's prediction (from bilateral edges, mechanisms,
    buyer profile) against the market baseline (demographics only).

    Args:
        cascade_level: 1-5, higher = more evidence depth
        mechanism_scores: {mechanism: score} from cascade
        edge_dimensions: Bilateral edge alignment scores (Level 3+)
        buyer_confidence: How well-characterized this buyer is (0-1)
        category: Product category for market baseline lookup
        context_mindset: Page mindset (purchasing, informed, etc.)
        gradient_priorities: Top gradient optimization dimensions
        base_cpm: Base CPM for this segment

    Returns:
        ArbitrageResult with score, bid multiplier, and reasoning.
    """
    result = ArbitrageResult()

    # ── ADAM's predicted effectiveness ──
    # Based on cascade evidence depth. Higher cascade levels = more
    # precise prediction = more confident arbitrage.
    adam_effectiveness = 0.5  # neutral baseline
    drivers: List[str] = []

    # Mechanism quality: top mechanism score
    if mechanism_scores:
        top_mech_score = max(mechanism_scores.values())
        adam_effectiveness = top_mech_score

        # Mechanism diversity bonus: if top 3 mechanisms are all >0.6,
        # the portfolio is strong
        ranked = sorted(mechanism_scores.values(), reverse=True)
        if len(ranked) >= 3 and ranked[2] > 0.6:
            adam_effectiveness = min(1.0, adam_effectiveness * 1.1)
            drivers.append("strong_mechanism_portfolio")

    # Bilateral edge evidence (Level 3+): composite alignment
    if edge_dimensions:
        composite = edge_dimensions.get("composite_alignment", 0)
        if composite > 0.6:
            # Strong bilateral alignment = ADAM is highly confident
            adam_effectiveness = max(adam_effectiveness, composite)
            drivers.append(f"bilateral_alignment_{composite:.2f}")

    # Buyer confidence: well-known buyers have more precise predictions
    if buyer_confidence > 0.5:
        adam_effectiveness = min(1.0, adam_effectiveness * (1.0 + buyer_confidence * 0.1))
        drivers.append(f"buyer_known_{buyer_confidence:.2f}")

    # Context alignment: if page mindset matches the mechanism strategy
    if context_mindset == "purchasing":
        adam_effectiveness = min(1.0, adam_effectiveness * 1.15)
        drivers.append("purchasing_context_boost")
    elif context_mindset == "informed" and mechanism_scores.get("authority", 0) > 0.7:
        adam_effectiveness = min(1.0, adam_effectiveness * 1.10)
        drivers.append("authority_in_informed_context")

    # Gradient intelligence: high gradient magnitude = optimization
    # opportunity the market doesn't see
    if gradient_priorities:
        total_lift = sum(p.get("expected_lift_delta", 0) for p in gradient_priorities)
        if total_lift > 5.0:
            adam_effectiveness = min(1.0, adam_effectiveness * 1.05)
            drivers.append(f"gradient_lift_{total_lift:.1f}pct")

    # ── Market baseline effectiveness ──
    # What a demographics-only system would predict for this category.
    cat_key = category.lower().replace("_", "").replace(" ", "")
    for k in _MARKET_BASELINES:
        if k in cat_key or cat_key in k:
            cat_key = k
            break
    else:
        cat_key = "default"

    baseline = _MARKET_BASELINES[cat_key]
    market_effectiveness = baseline["cvr"] / 0.05  # Normalize to 0-1 scale
    market_effectiveness = min(1.0, max(0.1, market_effectiveness))

    # ── Arbitrage computation ──
    if market_effectiveness > 0:
        arbitrage_score = adam_effectiveness / market_effectiveness
    else:
        arbitrage_score = 1.0

    # ── Confidence ──
    # Higher cascade level + buyer confidence = more confident arbitrage
    level_confidence = {1: 0.2, 2: 0.35, 3: 0.6, 4: 0.5, 5: 0.7}
    confidence = level_confidence.get(cascade_level, 0.2)
    if buyer_confidence > 0:
        confidence = min(0.95, confidence + buyer_confidence * 0.2)

    # ── Bid multiplier ──
    # Proportional to arbitrage score but capped for safety
    if arbitrage_score > 1.0:
        # Scale: 1.0 → 1.0x, 2.0 → 2.0x, capped at 3.0x
        bid_multiplier = min(3.0, arbitrage_score)
    else:
        # ADAM sees less value than market: reduce bid
        bid_multiplier = max(0.3, arbitrage_score)

    # Dampen by confidence: low confidence → bid closer to 1.0x
    bid_multiplier = 1.0 + (bid_multiplier - 1.0) * confidence

    # Alpha value in CPM units
    alpha_value = (bid_multiplier - 1.0) * base_cpm

    # ── Populate result ──
    result.arbitrage_score = round(arbitrage_score, 3)
    result.adam_predicted_effectiveness = round(adam_effectiveness, 4)
    result.market_baseline_effectiveness = round(market_effectiveness, 4)
    result.recommended_bid_multiplier = round(bid_multiplier, 3)
    result.alpha_value = round(alpha_value, 4)
    result.confidence = round(confidence, 3)
    result.arbitrage_drivers = drivers

    if arbitrage_score > 1.2:
        result.reasoning.append(
            f"Arbitrage opportunity: ADAM predicts {adam_effectiveness:.2f} vs "
            f"market {market_effectiveness:.2f} ({arbitrage_score:.1f}x). "
            f"Bid {bid_multiplier:.2f}x base CPM."
        )
    elif arbitrage_score < 0.8:
        result.reasoning.append(
            f"Market overvalues: ADAM predicts {adam_effectiveness:.2f} vs "
            f"market {market_effectiveness:.2f}. Reduce bid to {bid_multiplier:.2f}x."
        )

    return result
