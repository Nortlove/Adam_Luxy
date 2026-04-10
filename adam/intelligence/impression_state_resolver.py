"""
Impression State Resolver — Computing the Reader's Psychological Position
==========================================================================

THE FUNDAMENTAL REFRAME:

URL resolution is the WRONG abstraction. We're not resolving a URL to a
category. We're computing the reader's POSITION in the 20-dimensional
purchase-dance space at the moment they encounter the ad.

Every signal from the bid request narrows that position:
- The page title tells us the EMOTIONAL and COGNITIVE state
- The referrer tells us the INTENT (search → evaluating, social → browsing)
- The keywords tell us the TOPIC-ACTIVATED NEEDS
- The IAB category gives STRUCTURAL CONTEXT
- The domain gives PUBLISHER BASELINE
- Device + time give SITUATIONAL MODIFIERS

These signals are NOT alternatives (fallback tiers). They are ADDITIVE.
Each one constrains different dimensions. Together they compose a precise
20-dim position vector — even for a page we've never scored.

Then: that position vector conditions the graph query. The 47M bilateral
edges tell us: "when buyers were at THIS position in the dance, what
alignment + mechanism produced conversion?"

This is not categorization. This is psychological triangulation.

ARCHITECTURE:

    Bid Request
         ↓
    ┌─────────────────────────────────────────────┐
    │ Signal Extractors (parallel, ~5ms total)    │
    │                                             │
    │  Title → 20-dim extraction (highest power)  │
    │  Referrer → intent → dim modifiers          │
    │  Keywords → topic-need activation           │
    │  IAB cat → graph category prior             │
    │  Domain → taxonomy centroid                 │
    │  Device → bandwidth/patience modifiers      │
    │  Time → temporal modifiers                  │
    │  Pre-scored page → exact profile            │
    └──────────────────┬──────────────────────────┘
                       ↓
    ┌─────────────────────────────────────────────┐
    │ Signal Compositor                           │
    │ Weighted blend of all signals into one      │
    │ 20-dim position vector                      │
    │                                             │
    │ Weight = signal's discriminating power ×    │
    │          signal's availability confidence    │
    └──────────────────┬──────────────────────────┘
                       ↓
    reader_position: Dict[str, float]  # 20-dim vector
    position_confidence: float          # How precisely located
         ↓
    Page-conditioned graph query → empirical mechanism evidence
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs

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


@dataclass
class ReaderPosition:
    """The reader's computed position in 20-dim purchase-dance space."""
    dimensions: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    signals_used: List[str] = field(default_factory=list)
    signal_contributions: Dict[str, Dict[str, float]] = field(default_factory=dict)
    resolution_summary: str = ""


# ============================================================================
# SIGNAL EXTRACTORS — each produces a partial 20-dim vector + confidence
# ============================================================================

@dataclass
class SignalContribution:
    """One signal's contribution to the 20-dim position."""
    dimensions: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0      # How reliable this signal is (0-1)
    weight: float = 0.0          # How much discriminating power (0-1)
    source: str = ""


def _extract_from_title(title: str) -> SignalContribution:
    """Extract 20-dim position from page title.

    Titles are psychologically DENSE — 5-15 words that encode the
    core emotional and cognitive state the content creates.

    Weight: 0.35 (highest single signal)
    """
    if not title or len(title) < 5:
        return SignalContribution(source="title")

    from adam.intelligence.page_edge_scoring import extract_full_edge_dimensions
    dims = extract_full_edge_dimensions(title)

    # Title is short — only trust dimensions that scored non-neutral
    confident_dims = {d: v for d, v in dims.items() if abs(v - 0.5) > 0.05}
    confidence = min(0.7, len(confident_dims) / 10.0 + 0.2)

    return SignalContribution(
        dimensions=dims,
        confidence=confidence,
        weight=0.35,
        source="title",
    )


def _extract_from_referrer(referrer: str) -> SignalContribution:
    """Extract psychological intent from referrer URL.

    The referrer reveals WHY the reader is on this page:
    - Search referrer → active research mode (high information_seeking)
    - Social referrer → peer-influenced (high social_proof_sensitivity)
    - Direct/bookmark → habitual (high brand_relationship_depth)
    - Email → prompted (high persuasion_susceptibility)

    Weight: 0.20 (second highest — reveals intent, not just state)
    """
    if not referrer:
        return SignalContribution(source="referrer")

    ref_lower = referrer.lower()
    dims: Dict[str, float] = {}

    # Search engine referrer → active research/evaluation mode
    is_search = any(s in ref_lower for s in [
        "google.com/search", "bing.com/search", "yahoo.com/search",
        "duckduckgo.com", "search.", "q=",
    ])

    if is_search:
        dims["information_seeking"] = 0.85
        dims["decision_entropy"] = 0.60
        dims["construal_fit"] = 0.30  # Concrete — searching for specific things
        dims["temporal_discounting"] = 0.55  # Moderate urgency

        # Extract search query for deeper intent
        try:
            parsed = urlparse(referrer)
            query_params = parse_qs(parsed.query)
            search_query = query_params.get("q", [""])[0].lower()

            if any(w in search_query for w in ["best", "top", "review", "compare", "vs"]):
                dims["social_proof_sensitivity"] = 0.75
                dims["decision_entropy"] = 0.70
            if any(w in search_query for w in ["buy", "price", "deal", "cheap", "discount"]):
                dims["temporal_discounting"] = 0.75
                dims["construal_fit"] = 0.15  # Very concrete
                dims["loss_aversion_intensity"] = 0.55
            if any(w in search_query for w in ["how to", "guide", "tutorial", "diy"]):
                dims["cognitive_load_tolerance"] = 0.70
                dims["autonomy_reactance"] = 0.30
        except Exception:
            pass

        return SignalContribution(
            dimensions=dims, confidence=0.6, weight=0.20, source="referrer_search",
        )

    # Social media referrer → socially influenced
    is_social = any(s in ref_lower for s in [
        "facebook.com", "twitter.com", "x.com", "instagram.com",
        "reddit.com", "tiktok.com", "linkedin.com", "pinterest.com",
    ])

    if is_social:
        dims["social_proof_sensitivity"] = 0.75
        dims["mimetic_desire"] = 0.60
        dims["personality_alignment"] = 0.65
        dims["narrative_transport"] = 0.55
        dims["autonomy_reactance"] = 0.35

        if "reddit.com" in ref_lower:
            dims["information_seeking"] = 0.70
            dims["autonomy_reactance"] = 0.55  # Reddit users are more skeptical

        return SignalContribution(
            dimensions=dims, confidence=0.5, weight=0.20, source="referrer_social",
        )

    # Email referrer → prompted action
    is_email = any(s in ref_lower for s in [
        "mail.", "email", "newsletter", "campaign", "utm_medium=email",
    ])

    if is_email:
        dims["persuasion_susceptibility"] = 0.65
        dims["brand_relationship_depth"] = 0.60
        dims["temporal_discounting"] = 0.60
        dims["autonomy_reactance"] = 0.30
        return SignalContribution(
            dimensions=dims, confidence=0.5, weight=0.20, source="referrer_email",
        )

    # Direct / unknown referrer → habitual/organic
    return SignalContribution(
        dimensions={"brand_relationship_depth": 0.55},
        confidence=0.2,
        weight=0.05,
        source="referrer_direct",
    )


def _extract_from_keywords(keywords: List[str]) -> SignalContribution:
    """Extract psychological activation from publisher-curated keywords.

    Weight: 0.15 (high signal — publishers tag what matters)
    """
    if not keywords:
        return SignalContribution(source="keywords")

    from adam.intelligence.url_intelligence import _KEYWORD_PSYCHOLOGICAL_MAP

    dims: Dict[str, float] = {}
    matched = 0

    for kw in keywords:
        kw_lower = kw.lower().strip()
        if kw_lower in _KEYWORD_PSYCHOLOGICAL_MAP:
            matched += 1
            for dim, val in _KEYWORD_PSYCHOLOGICAL_MAP[kw_lower].items():
                if dim not in dims or abs(val - 0.5) > abs(dims[dim] - 0.5):
                    dims[dim] = val

    if not dims:
        return SignalContribution(source="keywords")

    confidence = min(0.6, matched / max(len(keywords), 1) + 0.2)
    return SignalContribution(
        dimensions=dims,
        confidence=confidence,
        weight=0.15,
        source="keywords",
    )


def _extract_from_iab_category(iab_cats: List[str]) -> SignalContribution:
    """Extract psychological context from IAB content categories.

    IAB categories map to product categories in our graph, which have
    BayesianPrior nodes with mechanism effectiveness data.

    Weight: 0.10
    """
    if not iab_cats:
        return SignalContribution(source="iab_category")

    # IAB to psychological category mapping
    _IAB_TO_PSYCH = {
        "IAB1": "arts_entertainment", "IAB2": "automotive",
        "IAB3": "business", "IAB4": "careers",
        "IAB5": "education", "IAB6": "parenting",
        "IAB7": "health", "IAB8": "food",
        "IAB9": "hobbies", "IAB10": "real_estate",
        "IAB12": "politics", "IAB13": "finance",
        "IAB15": "science", "IAB17": "sports",
        "IAB18": "fashion", "IAB19": "technology",
        "IAB20": "travel", "IAB22": "shopping",
    }

    from adam.intelligence.url_intelligence import _CATEGORY_UNIVERSAL_PRIORS

    for iab_cat in iab_cats:
        # Strip sub-category (IAB12-2 → IAB12)
        base_cat = iab_cat.split("-")[0].upper()
        psych_cat = _IAB_TO_PSYCH.get(base_cat)

        if psych_cat and psych_cat in _CATEGORY_UNIVERSAL_PRIORS:
            dims = dict(_CATEGORY_UNIVERSAL_PRIORS[psych_cat])
            return SignalContribution(
                dimensions=dims,
                confidence=0.5,
                weight=0.10,
                source=f"iab_{psych_cat}",
            )

    return SignalContribution(source="iab_category")


def _extract_from_domain_taxonomy(
    domain: str, url_category: str = "",
) -> SignalContribution:
    """Extract position from domain taxonomy centroid.

    Weight: 0.10 (low — broad baseline)
    """
    if not domain:
        return SignalContribution(source="domain")

    try:
        from adam.intelligence.domain_taxonomy import get_domain_taxonomy
        taxonomy = get_domain_taxonomy(domain)
        inferred = taxonomy.infer_psychology(
            url=f"https://{domain}/{url_category}" if url_category else f"https://{domain}/",
            category=url_category,
        )
        if inferred and inferred.get("observations", 0) >= 3:
            return SignalContribution(
                dimensions=inferred.get("edge_dimensions", {}),
                confidence=inferred.get("confidence", 0.3),
                weight=0.10,
                source=f"taxonomy_{inferred.get('inference_level', 'domain')}",
            )
    except Exception:
        pass

    return SignalContribution(source="domain")


def _extract_from_prescored(page_url: str) -> SignalContribution:
    """Check for pre-scored page profile (highest precision when available).

    Weight: 0.50 (dominant when available — this is ground truth)
    """
    if not page_url:
        return SignalContribution(source="prescored")

    try:
        from adam.intelligence.page_intelligence import get_page_intelligence_cache
        cache = get_page_intelligence_cache()
        # Use low-level Redis lookup to avoid recursion into url_intelligence
        from adam.intelligence.page_intelligence import _url_to_pattern, _REDIS_PREFIX
        pattern = _url_to_pattern(page_url)

        r = cache._get_redis()
        if r:
            from adam.intelligence.page_intelligence import PagePsychologicalProfile
            # Try exact URL pattern
            data = r.hgetall(f"{_REDIS_PREFIX}{pattern}")
            if data:
                profile = PagePsychologicalProfile.from_redis_dict(data)
                if profile.edge_dimensions:
                    return SignalContribution(
                        dimensions=profile.edge_dimensions,
                        confidence=profile.confidence,
                        weight=0.50,
                        source=f"prescored_{profile.profile_source}",
                    )
    except Exception:
        pass

    return SignalContribution(source="prescored")


def _extract_from_device_time(
    device_type: str = "", time_of_day: int = -1,
) -> SignalContribution:
    """Situational modifiers from device and time.

    Weight: 0.05 (lowest — modifiers, not primary signals)
    """
    dims: Dict[str, float] = {}

    if device_type == "mobile":
        dims["cognitive_load_tolerance"] = 0.35
        dims["temporal_discounting"] = 0.65
        dims["construal_fit"] = 0.30

    elif device_type == "connected_tv" or device_type == "ctv":
        dims["narrative_transport"] = 0.75
        dims["cognitive_load_tolerance"] = 0.30
        dims["autonomy_reactance"] = 0.25
        dims["emotional_resonance"] = 0.65

    if 0 <= time_of_day <= 23:
        if 22 <= time_of_day or time_of_day <= 5:  # Late night
            dims["cognitive_load_tolerance"] = dims.get("cognitive_load_tolerance", 0.5) * 0.8
            dims["emotional_resonance"] = dims.get("emotional_resonance", 0.5) * 1.2
            dims["autonomy_reactance"] = dims.get("autonomy_reactance", 0.5) * 0.8
        elif 7 <= time_of_day <= 9:  # Morning commute
            dims["temporal_discounting"] = dims.get("temporal_discounting", 0.5) * 1.3
            dims["information_seeking"] = dims.get("information_seeking", 0.5) * 1.1

    if not dims:
        return SignalContribution(source="device_time")

    return SignalContribution(
        dimensions={k: round(min(1.0, max(0.0, v)), 3) for k, v in dims.items()},
        confidence=0.3,
        weight=0.05,
        source="device_time",
    )


# ============================================================================
# SIGNAL COMPOSITOR — Weighted blend into single 20-dim position
# ============================================================================

def compose_reader_position(
    signals: List[SignalContribution],
) -> ReaderPosition:
    """Compose multiple signal contributions into a single 20-dim position.

    Each signal contributes to each dimension weighted by:
    - signal.weight: how much discriminating power this signal type has
    - signal.confidence: how confident we are in THIS signal's extraction
    - dimension deviation: how far from neutral (stronger signals get more weight)

    Dimensions where we have no signal remain at 0.5 (neutral/unknown).
    """
    result = ReaderPosition()
    signals_used = []
    signal_details = {}

    # Collect all contributions per dimension
    dim_contributions: Dict[str, List[Tuple[float, float]]] = {}  # dim → [(value, weight)]

    for signal in signals:
        if not signal.dimensions or signal.confidence < 0.1:
            continue

        effective_weight = signal.weight * signal.confidence
        if effective_weight < 0.01:
            continue

        signals_used.append(signal.source)
        signal_details[signal.source] = {
            "weight": signal.weight,
            "confidence": signal.confidence,
            "effective_weight": round(effective_weight, 3),
            "dims_contributed": len(signal.dimensions),
        }

        for dim, val in signal.dimensions.items():
            if dim not in EDGE_DIMENSIONS:
                continue
            if dim not in dim_contributions:
                dim_contributions[dim] = []
            dim_contributions[dim].append((val, effective_weight))

    # Blend each dimension using weighted average
    final_dims: Dict[str, float] = {}
    for dim in EDGE_DIMENSIONS:
        if dim in dim_contributions:
            contributions = dim_contributions[dim]
            total_weight = sum(w for _, w in contributions)
            if total_weight > 0:
                weighted_sum = sum(v * w for v, w in contributions)
                final_dims[dim] = round(weighted_sum / total_weight, 4)
            else:
                final_dims[dim] = 0.5
        else:
            final_dims[dim] = 0.5  # No signal on this dimension

    # Overall confidence: based on how many signals contributed
    # and how much of the 20-dim space is constrained
    constrained_dims = sum(1 for v in final_dims.values() if abs(v - 0.5) > 0.05)
    total_effective_weight = sum(
        s.weight * s.confidence for s in signals if s.dimensions and s.confidence >= 0.1
    )
    result.confidence = round(min(0.9,
        0.1 + total_effective_weight * 0.5 + constrained_dims / 20.0 * 0.3
    ), 3)

    result.dimensions = final_dims
    result.signals_used = signals_used
    result.signal_contributions = signal_details

    # Summary
    n_signals = len(signals_used)
    result.resolution_summary = (
        f"{n_signals} signals → {constrained_dims}/20 dims constrained, "
        f"conf={result.confidence:.2f}"
    )

    return result


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def resolve_reader_position(
    page_url: str = "",
    page_title: str = "",
    referrer: str = "",
    keywords: Optional[List[str]] = None,
    iab_categories: Optional[List[str]] = None,
    domain: str = "",
    device_type: str = "",
    time_of_day: int = -1,
) -> ReaderPosition:
    """Compute the reader's position in 20-dim purchase-dance space.

    Composes ALL available bid request signals into a single position
    vector. Each signal is extracted independently and blended weighted
    by discriminating power × extraction confidence.

    This ALWAYS returns a position — even with just a URL and nothing else.
    More signals = more precise position = better graph query results.

    Args:
        page_url: Full page URL from bid request (site.page)
        page_title: Content title if available (content.title)
        referrer: Referrer URL (site.ref)
        keywords: Publisher keywords (site.keywords)
        iab_categories: IAB categories (site.cat)
        domain: Publisher domain (site.domain) — extracted from URL if not provided
        device_type: Device type (desktop, mobile, connected_tv)
        time_of_day: Hour 0-23

    Returns:
        ReaderPosition with 20-dim vector, confidence, and signal audit trail
    """
    if not domain and page_url:
        from adam.intelligence.page_intelligence import _extract_domain
        domain = _extract_domain(page_url) or ""

    # Extract URL category from path
    url_category = ""
    if page_url:
        from adam.intelligence.url_intelligence import parse_url_signals
        url_signals = parse_url_signals(page_url)
        url_category = url_signals.get("category", "")
        # Use URL-derived keywords if no explicit keywords
        if not keywords and url_signals.get("keywords"):
            keywords = url_signals["keywords"]

    # Extract all signals in parallel (conceptually — all are fast)
    signals = [
        _extract_from_prescored(page_url),
        _extract_from_title(page_title),
        _extract_from_referrer(referrer),
        _extract_from_keywords(keywords or []),
        _extract_from_iab_category(iab_categories or []),
        _extract_from_domain_taxonomy(domain, url_category),
        _extract_from_device_time(device_type, time_of_day),
    ]

    # If no title was provided but we have a URL, try to extract
    # title-like content from the URL slug
    if not page_title and page_url and url_category:
        slug_signals = parse_url_signals(page_url)
        slug_kw = slug_signals.get("keywords", [])
        if slug_kw:
            slug_text = " ".join(slug_kw)
            signals.append(_extract_from_title(slug_text))

    # Compose into single position
    position = compose_reader_position(signals)

    return position
