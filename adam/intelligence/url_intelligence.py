"""
URL Intelligence — Maximum Signal From Every URL
==================================================

When StackAdapt sends a bid request with a page_url, we need to return
psychological intelligence EVEN IF we've never scored that exact page.

The system uses a 7-tier resolution strategy, from most precise to
most general. At least one tier will ALWAYS produce a result:

    Tier 1: Exact URL match (pre-scored page in Redis)          → conf 0.8+
    Tier 2: Domain + Category taxonomy centroid                  → conf 0.5-0.7
    Tier 3: Domain + Category + Author (if detectable from URL)  → conf 0.6-0.75
    Tier 4: Domain-level centroid (any domain we've indexed)     → conf 0.3-0.5
    Tier 5: Category cross-domain universal (e.g., "politics")   → conf 0.3-0.5
    Tier 6: Content-type prior (review, recipe, listing, etc.)   → conf 0.2-0.4
    Tier 7: URL keyword → topic → psychological prior            → conf 0.15-0.3

Every tier extracts signals from the URL structure itself:
- Domain → publisher identity, authority level
- First path segment → category (politics, sports, business...)
- Path patterns → content type (review, recipe, listing, guide)
- Slug keywords → topic (tariff, quarterback, toddler, investing)

The system NEVER returns nothing. Even a completely unknown URL like
momtastic.com/parenting/advice/toddler-sleep-tips gets:
- Category: "parenting" (from URL path)
- Content type: "advice/guide" (from path)
- Keywords: ["toddler", "sleep", "tips"] (from slug)
- Psychological prior: parenting content activates security needs,
  prevention focus, information-seeking mode
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# URL PARSING
# ============================================================================

def parse_url_signals(url: str) -> Dict[str, Any]:
    """Extract all available signals from a URL without fetching it.

    Returns category, subcategory, content_type, keywords, domain info.
    """
    if not url:
        return {}

    # Clean URL
    clean = url.lower().strip()
    for prefix in ("https://", "http://", "//"):
        if clean.startswith(prefix):
            clean = clean[len(prefix):]
    if clean.startswith("www."):
        clean = clean[4:]

    # Split domain and path
    parts = clean.split("/", 1)
    domain = parts[0].split(":")[0]
    path = parts[1] if len(parts) > 1 else ""
    path = path.split("?")[0].split("#")[0]  # Remove query/fragment

    # Parse path segments (skip dates and IDs)
    path_parts = [p for p in path.rstrip("/").split("/") if p]
    content_parts = [p for p in path_parts
                     if not re.match(r"^\d{1,4}$", p)  # Skip dates
                     and p not in ("index.html", "index.htm", "_", "id")]

    signals = {
        "domain": domain,
        "path_parts": content_parts,
        "category": "",
        "subcategory": "",
        "content_type": "",
        "keywords": [],
        "publisher_tier": _classify_publisher_tier(domain),
    }

    # Category: first meaningful path segment
    if content_parts:
        signals["category"] = _normalize_category(content_parts[0])

    # Subcategory: second segment (if not a slug)
    if len(content_parts) >= 2:
        seg = content_parts[1]
        if len(seg) < 25 and "-" not in seg:
            signals["subcategory"] = _normalize_category(seg)

    # Content type detection from URL patterns
    signals["content_type"] = _detect_content_type(url, content_parts)

    # Keywords from slug (last long hyphenated segment)
    slug_parts = [p for p in content_parts if len(p) > 10 and "-" in p]
    if slug_parts:
        slug = slug_parts[-1]
        keywords = [w for w in slug.replace("_", "-").split("-")
                    if len(w) > 3 and not re.match(r"^\d+$", w)]
        signals["keywords"] = keywords[:10]

    return signals


def _normalize_category(raw: str) -> str:
    """Normalize a URL path segment to a category name."""
    cat = raw.lower().strip()
    cat = re.sub(r"[^a-z0-9_-]", "", cat)
    cat = cat.replace("-", "_")

    # Map common URL category names to standard names
    _CAT_MAP = {
        "biz": "business", "tech": "technology", "sci": "science",
        "ent": "entertainment", "showbiz": "entertainment",
        "money": "finance", "investing": "finance",
        "life": "lifestyle", "living": "lifestyle",
        "auto": "automotive", "cars": "automotive",
        "food": "food", "recipes": "food", "cooking": "food",
        "wellness": "health", "fitness": "health",
        "realestate": "real_estate", "homes": "real_estate",
        "homedetails": "real_estate",
        "nfl": "sports", "nba": "sports", "mlb": "sports",
        "ncaa": "sports", "soccer": "sports", "football": "sports",
        "opinion": "opinion", "editorial": "opinion",
        "review": "reviews", "reviews": "reviews",
    }
    return _CAT_MAP.get(cat, cat)


def _detect_content_type(url: str, content_parts: List[str]) -> str:
    """Detect content type from URL patterns."""
    url_lower = url.lower()

    if "/recipe" in url_lower:
        return "recipe"
    if "/review" in url_lower:
        return "review"
    if "/how-to" in url_lower or "/guide" in url_lower or "/tutorial" in url_lower:
        return "guide"
    if "/video/" in url_lower or "/watch/" in url_lower:
        return "video"
    if "/gallery/" in url_lower or "/photos/" in url_lower or "/slideshow/" in url_lower:
        return "gallery"
    if "/opinion" in url_lower or "/editorial" in url_lower or "/column" in url_lower:
        return "opinion"
    if "/homedetails/" in url_lower or "/listing/" in url_lower or "/property/" in url_lower:
        return "listing"
    if "/product/" in url_lower or "/dp/" in url_lower or "/buy/" in url_lower:
        return "product_page"
    if "/story/" in url_lower or "/article/" in url_lower:
        return "article"
    if "/live/" in url_lower or "/live-" in url_lower:
        return "live"

    return "article"  # Default


def _classify_publisher_tier(domain: str) -> str:
    """Classify publisher into authority tiers."""
    _TIER_1 = {"nytimes.com", "washingtonpost.com", "wsj.com", "reuters.com",
               "bbc.com", "apnews.com", "bloomberg.com", "economist.com",
               "nature.com", "science.org"}
    _TIER_2 = {"cnn.com", "foxnews.com", "nbcnews.com", "cnbc.com", "forbes.com",
               "techcrunch.com", "wired.com", "espn.com", "healthline.com",
               "webmd.com", "investopedia.com", "theverge.com"}
    _TIER_3 = {"buzzfeed.com", "huffpost.com", "medium.com", "reddit.com",
               "quora.com", "substack.com"}

    if domain in _TIER_1:
        return "tier_1_premium"
    elif domain in _TIER_2:
        return "tier_2_major"
    elif domain in _TIER_3:
        return "tier_3_ugc"
    return "tier_4_unknown"


# ============================================================================
# CONTENT TYPE → PSYCHOLOGICAL PRIOR
# ============================================================================

# When we know the content type but nothing else, these priors provide
# the baseline psychological state. A review puts the reader in a
# fundamentally different state than a recipe or a live sports event.

_CONTENT_TYPE_EDGE_PRIORS = {
    "article": {
        "regulatory_fit": 0.50, "construal_fit": 0.50,
        "personality_alignment": 0.50, "emotional_resonance": 0.50,
        "cognitive_load_tolerance": 0.60, "information_seeking": 0.60,
        "temporal_discounting": 0.40, "decision_entropy": 0.40,
    },
    "review": {
        "regulatory_fit": 0.55, "construal_fit": 0.30,  # Concrete
        "information_seeking": 0.85, "social_proof_sensitivity": 0.75,
        "cognitive_load_tolerance": 0.70, "decision_entropy": 0.60,
        "persuasion_susceptibility": 0.65, "autonomy_reactance": 0.35,
    },
    "recipe": {
        "regulatory_fit": 0.65, "construal_fit": 0.20,  # Very concrete
        "emotional_resonance": 0.55, "interoceptive_awareness": 0.80,
        "cooperative_framing_fit": 0.65, "information_seeking": 0.60,
        "temporal_discounting": 0.30, "autonomy_reactance": 0.25,
    },
    "guide": {
        "information_seeking": 0.90, "cognitive_load_tolerance": 0.70,
        "construal_fit": 0.25,  # Concrete steps
        "persuasion_susceptibility": 0.60, "autonomy_reactance": 0.30,
        "decision_entropy": 0.50, "narrative_transport": 0.25,
    },
    "opinion": {
        "emotional_resonance": 0.70, "personality_alignment": 0.65,
        "autonomy_reactance": 0.55, "social_proof_sensitivity": 0.55,
        "cognitive_load_tolerance": 0.55, "construal_fit": 0.60,
    },
    "listing": {
        "construal_fit": 0.15,  # Maximally concrete (price, specs)
        "information_seeking": 0.80, "decision_entropy": 0.70,
        "temporal_discounting": 0.60, "loss_aversion_intensity": 0.55,
        "persuasion_susceptibility": 0.55,
    },
    "product_page": {
        "construal_fit": 0.20, "information_seeking": 0.75,
        "social_proof_sensitivity": 0.80, "decision_entropy": 0.65,
        "temporal_discounting": 0.55, "loss_aversion_intensity": 0.50,
        "persuasion_susceptibility": 0.60,
    },
    "video": {
        "narrative_transport": 0.75, "emotional_resonance": 0.65,
        "cognitive_load_tolerance": 0.35, "autonomy_reactance": 0.30,
        "interoceptive_awareness": 0.55,
    },
    "gallery": {
        "interoceptive_awareness": 0.70, "emotional_resonance": 0.55,
        "cognitive_load_tolerance": 0.80, "narrative_transport": 0.30,
        "information_seeking": 0.25,
    },
    "live": {
        "temporal_discounting": 0.90, "emotional_resonance": 0.75,
        "social_proof_sensitivity": 0.80, "personality_alignment": 0.75,
        "cognitive_load_tolerance": 0.40, "autonomy_reactance": 0.20,
    },
}


# ============================================================================
# CATEGORY → PSYCHOLOGICAL PRIOR (Cross-Domain Universals)
# ============================================================================

# From our self-teaching discoveries: these patterns hold across 3+ domains
_CATEGORY_UNIVERSAL_PRIORS = {
    "politics": {
        "emotional_resonance": 0.65, "personality_alignment": 0.60,
        "autonomy_reactance": 0.55, "social_proof_sensitivity": 0.55,
        "temporal_discounting": 0.55, "decision_entropy": 0.45,
        "cognitive_load_tolerance": 0.60,
    },
    "sports": {
        "personality_alignment": 0.84, "temporal_discounting": 0.85,
        "emotional_resonance": 0.60, "social_proof_sensitivity": 0.60,
        "cooperative_framing_fit": 0.60, "decision_entropy": 0.31,
        "cognitive_load_tolerance": 0.75, "evolutionary_motive": 0.70,
    },
    "business": {
        "information_seeking": 0.70, "cognitive_load_tolerance": 0.65,
        "temporal_discounting": 0.35, "construal_fit": 0.55,
        "loss_aversion_intensity": 0.55, "decision_entropy": 0.50,
    },
    "health": {
        "loss_aversion_intensity": 0.60, "information_seeking": 0.70,
        "regulatory_fit": 0.35, "autonomy_reactance": 0.35,
        "persuasion_susceptibility": 0.60, "cognitive_load_tolerance": 0.55,
    },
    "technology": {
        "information_seeking": 0.75, "cognitive_load_tolerance": 0.70,
        "construal_fit": 0.40, "social_proof_sensitivity": 0.55,
        "mimetic_desire": 0.50, "temporal_discounting": 0.40,
    },
    "entertainment": {
        "emotional_resonance": 0.70, "narrative_transport": 0.65,
        "personality_alignment": 0.60, "mimetic_desire": 0.55,
        "cognitive_load_tolerance": 0.75, "autonomy_reactance": 0.30,
    },
    "finance": {
        "loss_aversion_intensity": 0.70, "information_seeking": 0.75,
        "temporal_discounting": 0.30, "cognitive_load_tolerance": 0.60,
        "regulatory_fit": 0.30, "autonomy_reactance": 0.40,
        "decision_entropy": 0.55, "persuasion_susceptibility": 0.55,
    },
    "travel": {
        "regulatory_fit": 0.65, "emotional_resonance": 0.55,
        "construal_fit": 0.55, "mimetic_desire": 0.55,
        "interoceptive_awareness": 0.55, "temporal_discounting": 0.45,
    },
    "food": {
        "interoceptive_awareness": 0.75, "cooperative_framing_fit": 0.60,
        "emotional_resonance": 0.50, "social_proof_sensitivity": 0.55,
        "construal_fit": 0.25, "information_seeking": 0.55,
    },
    "parenting": {
        "loss_aversion_intensity": 0.65, "regulatory_fit": 0.30,
        "information_seeking": 0.75, "autonomy_reactance": 0.30,
        "emotional_resonance": 0.60, "persuasion_susceptibility": 0.60,
        "cooperative_framing_fit": 0.60, "evolutionary_motive": 0.65,
    },
    "real_estate": {
        "loss_aversion_intensity": 0.70, "decision_entropy": 0.75,
        "information_seeking": 0.80, "temporal_discounting": 0.30,
        "construal_fit": 0.20, "cognitive_load_tolerance": 0.55,
        "persuasion_susceptibility": 0.50, "evolutionary_motive": 0.60,
    },
    "automotive": {
        "information_seeking": 0.75, "construal_fit": 0.30,
        "social_proof_sensitivity": 0.60, "decision_entropy": 0.65,
        "evolutionary_motive": 0.55, "temporal_discounting": 0.35,
    },
    "science": {
        "cognitive_load_tolerance": 0.55, "information_seeking": 0.70,
        "construal_fit": 0.60, "autonomy_reactance": 0.45,
        "narrative_transport": 0.45, "emotional_resonance": 0.35,
    },
    "opinion": {
        "emotional_resonance": 0.70, "autonomy_reactance": 0.60,
        "personality_alignment": 0.65, "social_proof_sensitivity": 0.50,
    },
    "lifestyle": {
        "mimetic_desire": 0.60, "emotional_resonance": 0.55,
        "social_proof_sensitivity": 0.60, "interoceptive_awareness": 0.55,
        "regulatory_fit": 0.60, "brand_relationship_depth": 0.50,
    },
    "reviews": {
        "information_seeking": 0.85, "social_proof_sensitivity": 0.75,
        "construal_fit": 0.25, "decision_entropy": 0.60,
        "cognitive_load_tolerance": 0.70, "persuasion_susceptibility": 0.60,
    },
}


# ============================================================================
# KEYWORD → TOPIC → PSYCHOLOGICAL PRIOR
# ============================================================================

# When all we have are slug keywords, map them to psychological states
_KEYWORD_PSYCHOLOGICAL_MAP = {
    # Financial anxiety keywords
    "recession": {"loss_aversion_intensity": 0.80, "regulatory_fit": 0.25, "temporal_discounting": 0.70},
    "inflation": {"loss_aversion_intensity": 0.75, "regulatory_fit": 0.25, "persuasion_susceptibility": 0.65},
    "crash": {"loss_aversion_intensity": 0.85, "emotional_resonance": 0.80, "temporal_discounting": 0.80},
    "layoff": {"loss_aversion_intensity": 0.80, "evolutionary_motive": 0.70, "regulatory_fit": 0.20},
    "debt": {"loss_aversion_intensity": 0.70, "regulatory_fit": 0.25, "decision_entropy": 0.60},
    "tariff": {"loss_aversion_intensity": 0.55, "cognitive_load_tolerance": 0.55, "temporal_discounting": 0.50},

    # Health keywords
    "cancer": {"loss_aversion_intensity": 0.85, "evolutionary_motive": 0.80, "regulatory_fit": 0.15},
    "treatment": {"information_seeking": 0.85, "regulatory_fit": 0.30, "persuasion_susceptibility": 0.60},
    "symptoms": {"information_seeking": 0.80, "loss_aversion_intensity": 0.60, "autonomy_reactance": 0.30},
    "diet": {"information_seeking": 0.70, "interoceptive_awareness": 0.70, "social_proof_sensitivity": 0.55},

    # Purchase/commerce keywords
    "best": {"information_seeking": 0.80, "social_proof_sensitivity": 0.70, "decision_entropy": 0.55},
    "review": {"information_seeking": 0.85, "social_proof_sensitivity": 0.75, "construal_fit": 0.25},
    "cheap": {"loss_aversion_intensity": 0.55, "construal_fit": 0.20, "temporal_discounting": 0.60},
    "luxury": {"mimetic_desire": 0.75, "evolutionary_motive": 0.60, "brand_relationship_depth": 0.55},

    # Parenting keywords
    "toddler": {"evolutionary_motive": 0.70, "regulatory_fit": 0.25, "information_seeking": 0.70},
    "baby": {"evolutionary_motive": 0.75, "regulatory_fit": 0.20, "loss_aversion_intensity": 0.60},
    "school": {"temporal_discounting": 0.35, "information_seeking": 0.65, "decision_entropy": 0.55},

    # Sports keywords
    "quarterback": {"personality_alignment": 0.80, "temporal_discounting": 0.85, "emotional_resonance": 0.60},
    "championship": {"emotional_resonance": 0.75, "personality_alignment": 0.80, "temporal_discounting": 0.90},
    "draft": {"temporal_discounting": 0.70, "decision_entropy": 0.65, "mimetic_desire": 0.55},

    # Tech keywords
    "iphone": {"mimetic_desire": 0.70, "social_proof_sensitivity": 0.65, "construal_fit": 0.25},
    "software": {"information_seeking": 0.70, "cognitive_load_tolerance": 0.60, "construal_fit": 0.30},
    "hack": {"loss_aversion_intensity": 0.60, "regulatory_fit": 0.25, "temporal_discounting": 0.70},
}


# ============================================================================
# MAIN RESOLUTION FUNCTION
# ============================================================================

def resolve_url_intelligence(
    url: str,
    page_cache=None,
) -> Dict[str, Any]:
    """Resolve maximum psychological intelligence from a URL.

    7-tier fallback ensures we ALWAYS return something useful.

    Returns:
        {
            "edge_dimensions": Dict[str, float],  # 20-dim profile
            "confidence": float,                    # 0.0-1.0
            "resolution_tier": str,                 # which tier matched
            "resolution_detail": str,               # human-readable
            "url_signals": Dict,                    # parsed URL signals
        }
    """
    signals = parse_url_signals(url)
    domain = signals.get("domain", "")
    category = signals.get("category", "")
    content_type = signals.get("content_type", "article")
    keywords = signals.get("keywords", [])

    # ── Tier 1: Exact URL match (pre-scored) ──
    if page_cache is None:
        from adam.intelligence.page_intelligence import get_page_intelligence_cache
        page_cache = get_page_intelligence_cache()

    profile = page_cache.lookup(url)
    if profile and profile.edge_dimensions:
        return {
            "edge_dimensions": profile.edge_dimensions,
            "confidence": profile.confidence,
            "resolution_tier": "tier_1_exact",
            "resolution_detail": f"Pre-scored page profile ({profile.profile_source})",
            "url_signals": signals,
        }

    # ── Tier 2: Domain + Category taxonomy centroid ──
    if domain and category:
        try:
            from adam.intelligence.domain_taxonomy import get_domain_taxonomy
            taxonomy = get_domain_taxonomy(domain)
            inferred = taxonomy.infer_psychology(url=url, category=category)
            if inferred and inferred.get("observations", 0) >= 3:
                return {
                    "edge_dimensions": inferred.get("edge_dimensions", {}),
                    "confidence": inferred.get("confidence", 0.4),
                    "resolution_tier": f"tier_2_taxonomy_{inferred.get('inference_level', 'category')}",
                    "resolution_detail": f"{domain}/{category} centroid ({inferred.get('observations', 0)} obs)",
                    "url_signals": signals,
                }
        except Exception:
            pass

    # ── Tier 3: Domain-level centroid ──
    if domain:
        try:
            from adam.intelligence.domain_taxonomy import get_domain_taxonomy
            taxonomy = get_domain_taxonomy(domain)
            inferred = taxonomy.infer_psychology(url=url)
            if inferred and inferred.get("observations", 0) >= 3:
                return {
                    "edge_dimensions": inferred.get("edge_dimensions", {}),
                    "confidence": inferred.get("confidence", 0.3),
                    "resolution_tier": "tier_3_domain",
                    "resolution_detail": f"{domain} domain centroid ({inferred.get('observations', 0)} obs)",
                    "url_signals": signals,
                }
        except Exception:
            pass

    # ── Tier 4: Cross-domain category universal ──
    if category and category in _CATEGORY_UNIVERSAL_PRIORS:
        prior = dict(_CATEGORY_UNIVERSAL_PRIORS[category])
        # Fill missing dims with 0.5
        from adam.intelligence.page_edge_scoring import EDGE_DIMENSIONS
        for dim in EDGE_DIMENSIONS:
            if dim not in prior:
                prior[dim] = 0.5
        return {
            "edge_dimensions": prior,
            "confidence": 0.35,
            "resolution_tier": "tier_4_category_universal",
            "resolution_detail": f"Cross-domain '{category}' psychological prior",
            "url_signals": signals,
        }

    # ── Tier 5: Content type prior ──
    if content_type and content_type in _CONTENT_TYPE_EDGE_PRIORS:
        prior = dict(_CONTENT_TYPE_EDGE_PRIORS[content_type])
        from adam.intelligence.page_edge_scoring import EDGE_DIMENSIONS
        for dim in EDGE_DIMENSIONS:
            if dim not in prior:
                prior[dim] = 0.5
        return {
            "edge_dimensions": prior,
            "confidence": 0.25,
            "resolution_tier": "tier_5_content_type",
            "resolution_detail": f"Content type '{content_type}' psychological prior",
            "url_signals": signals,
        }

    # ── Tier 6: Keyword-based psychological prior ──
    if keywords:
        keyword_dims: Dict[str, float] = {}
        matched_keywords = []
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in _KEYWORD_PSYCHOLOGICAL_MAP:
                matched_keywords.append(kw_lower)
                for dim, val in _KEYWORD_PSYCHOLOGICAL_MAP[kw_lower].items():
                    # Take strongest signal per dimension
                    if dim not in keyword_dims or abs(val - 0.5) > abs(keyword_dims[dim] - 0.5):
                        keyword_dims[dim] = val

        if keyword_dims:
            from adam.intelligence.page_edge_scoring import EDGE_DIMENSIONS
            for dim in EDGE_DIMENSIONS:
                if dim not in keyword_dims:
                    keyword_dims[dim] = 0.5
            return {
                "edge_dimensions": keyword_dims,
                "confidence": 0.20,
                "resolution_tier": "tier_6_keywords",
                "resolution_detail": f"Keywords {matched_keywords} → psychological prior",
                "url_signals": signals,
            }

    # ── Tier 7: Publisher tier + generic article ──
    # Even with NOTHING else, we know something about publisher authority
    publisher_tier = signals.get("publisher_tier", "tier_4_unknown")
    generic = dict(_CONTENT_TYPE_EDGE_PRIORS.get("article", {}))
    from adam.intelligence.page_edge_scoring import EDGE_DIMENSIONS
    for dim in EDGE_DIMENSIONS:
        if dim not in generic:
            generic[dim] = 0.5

    # Adjust based on publisher tier
    if publisher_tier == "tier_1_premium":
        generic["persuasion_susceptibility"] = 0.55
        generic["autonomy_reactance"] = 0.40
        generic["cognitive_load_tolerance"] = 0.60
    elif publisher_tier == "tier_3_ugc":
        generic["social_proof_sensitivity"] = 0.60
        generic["autonomy_reactance"] = 0.55

    return {
        "edge_dimensions": generic,
        "confidence": 0.15,
        "resolution_tier": "tier_7_generic",
        "resolution_detail": f"Generic article prior ({publisher_tier})",
        "url_signals": signals,
    }
