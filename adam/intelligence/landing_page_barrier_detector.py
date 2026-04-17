"""
Landing Page Barrier Detector
================================

Analyzes visitor behavior on luxyride.com (via informativ.js telemetry)
to infer which psychological barrier is preventing conversion.

informativ.js captures:
- Section dwell time (which parts of the page they read)
- Page navigation (which pages they visit)
- Scroll depth and velocity
- Click/hover behavior on interactive elements
- Time on site before bounce

This module classifies the barrier from that behavioral fingerprint,
enabling therapeutic retargeting with the RIGHT mechanism for each
visitor — not generic retargeting with the same ad repeated.

Barrier types (from bilateral evidence):
- TRUST_DEFICIT: needs credibility, guarantees, social proof
- PRICE_FRICTION: needs value framing, cognitive ease, no-risk positioning
- QUALITY_UNCERTAINTY: needs visual proof, testimonials, fleet details
- COMPLEXITY_FRICTION: needs simplicity, one-click booking, ease
- LOW_MOTIVATION: needs curiosity activation, aspiration, novelty
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class BarrierClassification:
    """Result of barrier detection for one visitor."""
    visitor_id: str
    primary_barrier: str
    confidence: float = 0.0
    secondary_barrier: str = ""

    # Recommended retargeting
    recommended_mechanism: str = ""
    recommended_headline: str = ""
    recommended_cta: str = ""

    # Evidence
    signals_used: List[str] = field(default_factory=list)
    page_behavior: Dict[str, Any] = field(default_factory=dict)


# Page → barrier mapping for luxyride.com
# Based on: if a visitor dwells on a specific page/section,
# they're trying to resolve a specific concern
PAGE_BARRIER_MAP = {
    # Pricing-related pages
    "pricing": "PRICE_FRICTION",
    "rates": "PRICE_FRICTION",
    "cost": "PRICE_FRICTION",
    "packages": "PRICE_FRICTION",

    # Trust-related pages
    "about": "TRUST_DEFICIT",
    "about-us": "TRUST_DEFICIT",
    "company": "TRUST_DEFICIT",
    "safety": "TRUST_DEFICIT",
    "insurance": "TRUST_DEFICIT",

    # Quality-related pages
    "fleet": "QUALITY_UNCERTAINTY",
    "vehicles": "QUALITY_UNCERTAINTY",
    "luxury": "QUALITY_UNCERTAINTY",
    "experience": "QUALITY_UNCERTAINTY",

    # Booking friction
    "booking": "COMPLEXITY_FRICTION",
    "book": "COMPLEXITY_FRICTION",
    "reserve": "COMPLEXITY_FRICTION",
    "app": "COMPLEXITY_FRICTION",

    # General browsing (low motivation)
    "home": "LOW_MOTIVATION",
    "blog": "LOW_MOTIVATION",
}

# Barrier → therapeutic mechanism
BARRIER_RESOLUTION = {
    "TRUST_DEFICIT": {
        "mechanism": "authority",
        "headline": "Trusted by Fortune 500 travel managers",
        "body": "On-time guarantee. Professional chauffeurs. Flight tracking included.",
        "cta": "See why professionals choose LUXY",
        "metaphor_family": "warmth (reliable, genuine, trusted)",
    },
    "PRICE_FRICTION": {
        "mechanism": "cognitive_ease",
        "headline": "Premium transport. No surprises.",
        "body": "No surge pricing. No hidden fees. No tips required. Just transparent luxury.",
        "cta": "See our simple pricing",
        "metaphor_family": "flow (seamless, straightforward, clear)",
    },
    "QUALITY_UNCERTAINTY": {
        "mechanism": "social_proof",
        "headline": "4.9★ rated by 10,000+ travelers",
        "body": "See why executives, celebrities, and discerning travelers choose our fleet.",
        "cta": "Read reviews from travelers like you",
        "metaphor_family": "weight (substantial, impressive, significant)",
    },
    "COMPLEXITY_FRICTION": {
        "mechanism": "cognitive_ease",
        "headline": "Book in 30 seconds. Really.",
        "body": "No account required. No app download. Just enter your pickup and go.",
        "cta": "Book now — it takes 30 seconds",
        "metaphor_family": "flow (effortless, smooth, instant)",
    },
    "LOW_MOTIVATION": {
        "mechanism": "curiosity",
        "headline": "Curious what a private car service is actually like?",
        "body": "No stiffness. No pretension. Just a better ride than you're used to.",
        "cta": "See what you've been missing",
        "metaphor_family": "space (discover, explore, open)",
    },
}


def classify_barrier(
    visitor_data: Dict[str, Any],
) -> BarrierClassification:
    """Classify a visitor's conversion barrier from their site behavior.

    Args:
        visitor_data: Telemetry from informativ.js, containing:
            - visitor_id: unique identifier
            - pages_viewed: list of page paths
            - section_dwell: dict of section → dwell_seconds
            - total_time_on_site: seconds
            - scroll_depth: 0-1
            - bounce: bool
            - device: "mobile" | "desktop"
    """
    visitor_id = visitor_data.get("visitor_id", "unknown")
    pages = visitor_data.get("pages_viewed", [])
    section_dwell = visitor_data.get("section_dwell", {})
    total_time = visitor_data.get("total_time_on_site", 0)
    bounce = visitor_data.get("bounce", True)
    device = visitor_data.get("device", "desktop")

    signals = []
    barrier_scores: Dict[str, float] = {
        "TRUST_DEFICIT": 0.0,
        "PRICE_FRICTION": 0.0,
        "QUALITY_UNCERTAINTY": 0.0,
        "COMPLEXITY_FRICTION": 0.0,
        "LOW_MOTIVATION": 0.0,
    }

    # 1. Page path analysis
    for page in pages:
        page_lower = page.strip("/").lower().split("/")[-1]
        barrier = PAGE_BARRIER_MAP.get(page_lower)
        if barrier:
            barrier_scores[barrier] += 1.5
            signals.append(f"visited /{page_lower} → {barrier}")

    # 2. Section dwell analysis
    for section, dwell in section_dwell.items():
        section_lower = section.lower()
        if dwell > 5:
            if any(w in section_lower for w in ["price", "cost", "rate"]):
                barrier_scores["PRICE_FRICTION"] += dwell * 0.3
                signals.append(f"dwelled {dwell:.0f}s on pricing section")
            elif any(w in section_lower for w in ["about", "team", "trust", "safety"]):
                barrier_scores["TRUST_DEFICIT"] += dwell * 0.3
                signals.append(f"dwelled {dwell:.0f}s on trust section")
            elif any(w in section_lower for w in ["fleet", "vehicle", "car"]):
                barrier_scores["QUALITY_UNCERTAINTY"] += dwell * 0.3
                signals.append(f"dwelled {dwell:.0f}s on fleet section")
            elif any(w in section_lower for w in ["book", "reserve", "app"]):
                barrier_scores["COMPLEXITY_FRICTION"] += dwell * 0.3
                signals.append(f"dwelled {dwell:.0f}s on booking section")

    # 3. Bounce behavior
    if bounce and total_time < 10:
        barrier_scores["LOW_MOTIVATION"] += 3.0
        signals.append("quick bounce (<10s)")
    elif bounce and total_time > 30:
        barrier_scores["COMPLEXITY_FRICTION"] += 1.5
        signals.append("slow bounce (>30s, explored but left)")

    # 4. Mobile friction bonus
    if device == "mobile":
        barrier_scores["COMPLEXITY_FRICTION"] += 1.0
        signals.append("mobile device (higher friction)")

    # 5. Default if no signal
    if max(barrier_scores.values()) < 0.5:
        barrier_scores["TRUST_DEFICIT"] = 1.0
        signals.append("no strong signal, defaulting to trust_deficit")

    # Classify
    ranked = sorted(barrier_scores.items(), key=lambda x: x[1], reverse=True)
    primary = ranked[0][0]
    secondary = ranked[1][0] if len(ranked) > 1 else ""

    resolution = BARRIER_RESOLUTION.get(primary, BARRIER_RESOLUTION["TRUST_DEFICIT"])
    confidence = min(0.95, ranked[0][1] / max(sum(barrier_scores.values()), 1))

    return BarrierClassification(
        visitor_id=visitor_id,
        primary_barrier=primary,
        confidence=round(confidence, 3),
        secondary_barrier=secondary,
        recommended_mechanism=resolution["mechanism"],
        recommended_headline=resolution["headline"],
        recommended_cta=resolution["cta"],
        signals_used=signals,
        page_behavior={
            "pages_viewed": pages,
            "total_time": total_time,
            "bounce": bounce,
            "device": device,
        },
    )


def get_retargeting_creative(barrier: str) -> Dict[str, str]:
    """Get the retargeting creative spec for a given barrier type."""
    return BARRIER_RESOLUTION.get(barrier, BARRIER_RESOLUTION["TRUST_DEFICIT"])
