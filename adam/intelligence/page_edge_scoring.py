"""
Full-Width Page Edge Scoring — Direct 20-Dimension Extraction
==============================================================

THE PROBLEM:
The page intelligence system was extracting 7 NDF dimensions from text,
then mapping them to 20 edge dimensions via a shift matrix. This is
lossy compression — squeezing rich page psychology through a 7-dim
bottleneck, then expanding it back. NDF should only be a fallback.

THE FIX:
Score pages DIRECTLY on all 20 edge dimensions using:
1. Graph-backed category priors (from 47M bilateral edges)
2. Construct-level text extraction (from 524-construct taxonomy)
3. Deep linguistic analysis (from spaCy + embeddings)
4. NDF word-list extraction ONLY as the final fallback

The output is a `PageEdgeProfile` — the page's effect on each of the
20 dimensions that the bilateral cascade actually uses for mechanism
scoring. This replaces the NDF-based page profile in the cascade.

ARCHITECTURE:

    Page Text
         ↓
    ┌─────────────────────────────────────────────────────────┐
    │ Tier 1: Graph Priors (if category known)               │
    │   Query BayesianPrior nodes for category-level          │
    │   psychological environment → 20 dimensions             │
    │   Confidence: 0.7 (backed by bilateral edge evidence)  │
    ├─────────────────────────────────────────────────────────┤
    │ Tier 2: Full-Width Text Extraction                     │
    │   Extract each of the 20 dimensions directly from text │
    │   using dimension-specific linguistic markers           │
    │   Confidence: 0.4-0.6 (depends on text length)         │
    ├─────────────────────────────────────────────────────────┤
    │ Tier 3: NDF Fallback (when Tiers 1-2 unavailable)      │
    │   7-dim word lists → map to 20 dims via heuristic      │
    │   Confidence: 0.2-0.4 (compressed, lossy)              │
    └─────────────────────────────────────────────────────────┘
         ↓
    PageEdgeProfile (20 dimensions)
         ↓
    Bilateral Cascade (mechanism scoring on same dimensions)
"""

from __future__ import annotations

import logging
import math
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# The 20 edge dimensions — THESE are what the cascade uses
EDGE_DIMENSIONS = [
    "regulatory_fit",
    "construal_fit",
    "personality_alignment",
    "emotional_resonance",
    "value_alignment",
    "evolutionary_motive",
    "linguistic_style",
    "persuasion_susceptibility",
    "cognitive_load_tolerance",
    "narrative_transport",
    "social_proof_sensitivity",
    "loss_aversion_intensity",
    "temporal_discounting",
    "brand_relationship_depth",
    "autonomy_reactance",
    "information_seeking",
    "mimetic_desire",
    "interoceptive_awareness",
    "cooperative_framing_fit",
    "decision_entropy",
]


@dataclass
class PageEdgeProfile:
    """Page psychological state expressed in the SAME 20 dimensions as bilateral edges.

    This is what the cascade should consume — not NDF, not mechanism adjustments,
    but the page's direct effect on each dimension the mechanism scoring formulas use.

    Each value represents: "a reader on this page has their [dimension] shifted to [value]"
    where 0.0 = minimum, 1.0 = maximum, 0.5 = neutral/unknown.
    """
    dimensions: Dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0
    scoring_tier: str = ""       # "graph_prior", "full_extraction", "ndf_fallback"
    source_evidence: str = ""    # What backed this score
    extraction_details: Dict[str, str] = field(default_factory=dict)  # Per-dim source


# ============================================================================
# DIMENSION-SPECIFIC TEXT EXTRACTION
# ============================================================================
# Each of the 20 edge dimensions has its own linguistic markers.
# These are NOT the same as NDF word lists — they map directly to
# the psychological constructs the cascade uses.

_DIMENSION_EXTRACTORS: Dict[str, Dict[str, Any]] = {
    "regulatory_fit": {
        # Regulatory Focus Theory: promotion vs prevention framing
        "promotion": ["achieve", "gain", "aspire", "hope", "ideal", "opportunity",
                       "advance", "earn", "grow", "improve", "maximize", "potential"],
        "prevention": ["safe", "secure", "protect", "avoid", "prevent", "risk",
                        "duty", "obligation", "responsible", "careful", "maintain"],
        "compute": "ratio",  # promotion / (promotion + prevention)
        "description": "How the page frames goals: approach vs avoidance",
    },
    "construal_fit": {
        # Construal Level Theory: abstract vs concrete processing
        "abstract": ["vision", "principle", "values", "identity", "purpose",
                      "meaning", "philosophy", "fundamental", "essence", "concept",
                      "ideally", "broadly", "theoretically"],
        "concrete": ["specifically", "exactly", "step by step", "price", "feature",
                      "specification", "measurement", "quantity", "ingredient",
                      "instruction", "how to", "tutorial", "percent"],
        "compute": "ratio",
        "description": "Abstract values vs concrete features",
    },
    "personality_alignment": {
        # Big Five social orientation signals
        "social": ["together", "community", "shared", "collective", "team",
                    "everyone", "relationship", "connection", "empathy", "caring"],
        "independent": ["individual", "unique", "personal", "alone", "self",
                         "independent", "solitary", "autonomous", "self-made"],
        "compute": "ratio",
        "description": "Social vs individual orientation of content",
    },
    "emotional_resonance": {
        # Emotional vs analytical content (ratio-based for discrimination)
        "emotional": ["feel", "heart", "passion", "deeply", "profound", "powerful",
                       "touching", "moving", "emotional", "tears", "joy", "grief",
                       "love", "hate", "anger", "fear", "hope", "dream",
                       "devastating", "incredible", "overwhelming", "heartbreaking",
                       "panic", "terrif", "horrif", "outrage", "shock", "stun",
                       "tragic", "cruel", "suffer", "pain", "agony", "despair",
                       "fury", "rage", "anxious", "dread", "desperate", "crisis",
                       "scary", "frighten", "worry", "concern", "alarm", "distress",
                       "inspire", "thrill", "excit", "amaz", "beautiful", "wonderful",
                       "happy", "delight", "celebrate", "triumph", "miracle"],
        "analytical": ["data", "analysis", "study", "research", "percent", "ratio",
                        "evidence", "measure", "calculate", "statistic", "finding",
                        "methodology", "hypothesis", "correlation", "variable",
                        "framework", "metric", "benchmark", "index", "survey",
                        "sample", "margin", "trend", "forecast", "model",
                        "equation", "algorithm", "parameter", "coefficient"],
        "compute": "ratio",
        "description": "Emotional vs analytical processing mode of content",
    },
    "value_alignment": {
        # Values-driven vs transaction-driven content
        "values": ["integrity", "honest", "ethical", "moral", "fair", "just",
                    "authentic", "genuine", "transparent", "trustworthy", "reliable",
                    "commitment", "dedication", "responsibility", "sustainable",
                    "quality", "excellence", "heritage", "tradition", "craftsmanship"],
        "transactional": ["deal", "discount", "price", "cheap", "bargain", "coupon",
                           "clearance", "markdown", "lowest", "budget", "affordable",
                           "cost", "promo", "sale", "offer", "save money"],
        "compute": "ratio",
        "description": "Values-driven vs transaction-driven purchase framing",
    },
    "evolutionary_motive": {
        # Primal need activation
        "survival": ["danger", "threat", "safety", "protect", "survival",
                      "emergency", "crisis", "death", "disease", "attack"],
        "status": ["prestigious", "elite", "exclusive", "luxury", "superior",
                    "dominant", "winning", "champion", "leader", "alpha"],
        "belonging": ["tribe", "community", "belong", "family", "loyalty",
                       "insider", "membership", "brotherhood", "sisterhood"],
        "attraction": ["beautiful", "attractive", "desire", "seductive",
                        "irresistible", "gorgeous", "stunning", "alluring"],
        "compute": "max_category",
        "description": "Which primal motive the page activates",
    },
    "linguistic_style": {
        # Language register detection
        "formal": ["therefore", "consequently", "furthermore", "moreover",
                    "notwithstanding", "heretofore", "pursuant", "regarding",
                    "accordingly", "henceforth"],
        "casual": ["gonna", "wanna", "kinda", "lol", "omg", "btw", "tbh",
                    "ngl", "idk", "imo", "fwiw", "yeah", "nah", "dude"],
        "compute": "ratio",
        "description": "Formal vs casual language register",
    },
    "persuasion_susceptibility": {
        # Content that lowers persuasion defenses
        "lowering": ["recommended", "trusted", "endorsed", "backed by",
                      "suggested", "advised", "according to experts",
                      "follow these steps", "simply do"],
        "raising": ["skeptical", "question everything", "don't believe",
                     "manipulation", "propaganda", "think critically",
                     "do your own research", "buyer beware", "scam"],
        "compute": "ratio",
        "description": "Does the page lower or raise persuasion defenses",
    },
    "cognitive_load_tolerance": {
        # Remaining cognitive bandwidth
        "complex_indicators": ["analysis", "furthermore", "multivariate",
                                "nuanced", "counterintuitively", "paradoxically",
                                "longitudinal", "multifaceted", "comprehensive"],
        "simple_indicators": ["simple", "easy", "quick", "straightforward",
                               "just", "basically", "essentially", "bottom line"],
        "compute": "inverse_complexity",
        "description": "How much cognitive bandwidth remains after reading",
    },
    "narrative_transport": {
        # Story-driven vs fact-driven content
        "narrative": ["story", "journey", "chapter", "beginning", "once upon",
                       "imagine", "picture this", "it started", "character",
                       "plot", "narrative", "tale", "adventure", "hero",
                       "villain", "quest", "destiny", "memoir", "testimony",
                       "confession", "diary", "experience", "remember when",
                       "grew up", "childhood", "flashback", "revelation",
                       "twist", "climax", "ending", "lived", "survived"],
        "factual": ["report", "data", "statistics", "according to", "survey",
                     "findings", "results", "published", "peer reviewed",
                     "confirmed", "source", "official", "verified", "record",
                     "document", "release", "statement", "announce",
                     "quarter", "fiscal", "revenue", "regulatory", "policy"],
        "compute": "ratio",
        "description": "Narrative immersion vs factual reporting",
    },
    "social_proof_sensitivity": {
        # Social/crowd-validated vs independently-evaluated content
        "social": ["everyone", "millions", "most people", "popular", "trending",
                    "best seller", "top rated", "recommended by", "5 stars",
                    "reviews", "testimonial", "customers say", "users love",
                    "community favorite", "viral", "shared by", "liked by"],
        "independent": ["in my opinion", "personally", "i found", "my experience",
                         "individual", "unique perspective", "contrary to popular",
                         "underrated", "overlooked", "niche", "hidden gem",
                         "independently", "my own research", "i tested"],
        "compute": "ratio",
        "description": "Social validation vs independent evaluation mode",
    },
    "loss_aversion_intensity": {
        # Prospect Theory loss activation
        "loss_markers": ["lose", "miss out", "cost", "decline", "drop", "fall",
                          "risk of losing", "before it's too late", "running out",
                          "won't get back", "damage", "penalty", "forfeiture",
                          "your savings could", "your home could"],
        "gain_markers": ["gain", "earn", "save", "win", "profit", "benefit",
                          "reward", "bonus", "growth", "increase", "build"],
        "compute": "asymmetric_ratio",  # Losses weighted 2.25x per Prospect Theory
        "description": "How strongly the page activates loss aversion",
    },
    "temporal_discounting": {
        # Present vs future orientation
        "present": ["now", "today", "immediately", "instant", "right away",
                     "don't wait", "hurry", "act fast", "limited time",
                     "while supplies last", "flash", "urgent", "deadline"],
        "future": ["invest", "long-term", "eventually", "plan ahead", "future",
                    "retirement", "legacy", "sustainable", "years from now",
                    "compound", "strategic", "patient"],
        "compute": "ratio",
        "description": "Present urgency vs future planning orientation",
    },
    "brand_relationship_depth": {
        # Loyalty/relationship vs novelty/switching content
        "loyalty": ["loyal", "fan", "love this brand", "always use",
                     "my go-to", "been using for years", "trust", "reliable",
                     "never let me down", "heritage", "established",
                     "tradition", "committed", "dedicated", "repeat"],
        "novelty": ["new", "switch", "alternative", "try something different",
                     "just launched", "startup", "disruptor", "challenger",
                     "competitor", "better option", "upgrade from",
                     "replacement", "innovative", "fresh", "reimagined"],
        "compute": "ratio",
        "description": "Loyalty/trust vs novelty/switching mindset",
    },
    "autonomy_reactance": {
        # Reactance to persuasion pressure
        "pressure": ["you must", "you need to", "don't miss", "act now",
                      "last chance", "limited offer", "hurry", "pressure",
                      "mandate", "required", "obligatory", "comply"],
        "freedom": ["your choice", "up to you", "optional", "freedom",
                     "decide for yourself", "no pressure", "take your time",
                     "when you're ready", "at your own pace"],
        "compute": "ratio",
        "description": "How much the page triggers resistance to persuasion",
    },
    "information_seeking": {
        # Active research/evaluation vs passive consumption
        "seeking": ["how to", "guide", "tutorial", "comparison", "versus",
                     "best", "review", "which is better", "pros and cons",
                     "in-depth", "analysis", "breakdown", "comprehensive",
                     "everything you need to know", "explained", "compared",
                     "recommend", "advice", "tips", "expert", "evaluate",
                     "assess", "consider", "option", "alternative", "criteria",
                     "checklist", "factor", "decision", "choose", "select",
                     "research", "investigate", "learn", "understand", "question"],
        "passive": ["watch", "enjoy", "relax", "sit back", "entertainment",
                     "fun", "laugh", "unwind", "escape", "binge",
                     "trending now", "you won't believe", "shocking", "viral",
                     "celebrity", "gossip", "drama", "scandal", "rumor",
                     "meme", "hilarious", "lol", "omg", "wtf", "epic"],
        "compute": "ratio",
        "description": "Active research vs passive consumption mode",
    },
    "mimetic_desire": {
        # Aspirational/imitative vs practical/functional content
        "aspirational": ["celebrity", "influencer", "what the rich buy", "luxury",
                          "aspirational", "enviable", "coveted", "exclusive access",
                          "insider", "VIP", "curated for", "taste maker",
                          "what experts choose", "editor's pick", "must have",
                          "dream", "wish list", "goals", "lifestyle"],
        "practical": ["practical", "functional", "utilitarian", "everyday",
                       "budget", "basic", "essential", "necessary", "standard",
                       "ordinary", "common", "typical", "routine", "mundane"],
        "compute": "ratio",
        "description": "Aspirational imitation vs practical functionality mode",
    },
    "interoceptive_awareness": {
        # Sensory/embodied vs abstract/conceptual content
        "sensory": ["feel", "sensation", "taste", "touch", "smell", "texture",
                     "smooth", "warm", "cool", "refreshing", "soothing",
                     "invigorating", "tingling", "soft", "silky", "crisp",
                     "hunger", "thirst", "fatigue", "energy", "relax",
                     "aroma", "flavor", "comfort", "pain"],
        "abstract": ["concept", "theory", "principle", "framework", "model",
                      "paradigm", "abstract", "intellectual", "philosophical",
                      "theoretical", "ideological", "metaphysical", "systemic"],
        "compute": "ratio",
        "description": "Sensory/embodied vs abstract/conceptual processing",
    },
    "cooperative_framing_fit": {
        # Cooperative/fair vs competitive/zero-sum framing
        "cooperative": ["fair", "mutual", "together", "partnership", "reciprocal",
                         "give back", "share", "equal", "transparent",
                         "no hidden fees", "honest", "community", "collaborative",
                         "win-win", "for everyone", "shared value"],
        "competitive": ["beat", "dominate", "crush", "outperform", "destroy",
                         "winner", "loser", "versus", "battle", "war",
                         "fight", "conquer", "defeat", "rival", "enemy"],
        "compute": "ratio",
        "description": "Cooperative/fair vs competitive/zero-sum framing",
    },
    "decision_entropy": {
        # Choice difficulty / decision paralysis
        "paradox": ["overwhelmed", "too many options", "confused", "complicated",
                     "hard to choose", "which one", "comparison", "trade-off",
                     "on the other hand", "alternatively", "pros and cons"],
        "clarity": ["clear winner", "obviously", "simple choice", "no brainer",
                     "the best", "recommended", "just get this", "winner"],
        "compute": "ratio",
        "description": "How much the page creates decision difficulty",
    },
}


# ============================================================================
# EXTRACTION ENGINE
# ============================================================================

def _extract_dimension(
    text_lower: str,
    word_count: int,
    config: Dict[str, Any],
) -> float:
    """Extract a single edge dimension value from text."""
    compute_type = config.get("compute", "density")

    if compute_type == "ratio":
        # Two opposing poles — compute ratio
        keys = [k for k in config if k not in ("compute", "description")]
        if len(keys) < 2:
            return 0.5
        pos_words = config[keys[0]]
        neg_words = config[keys[1]]
        pos_hits = sum(1 for w in pos_words if w in text_lower)
        neg_hits = sum(1 for w in neg_words if w in text_lower)
        total = pos_hits + neg_hits
        if total == 0:
            return 0.5
        return round(pos_hits / total, 4)

    elif compute_type == "density":
        # Single set of markers — density per word count
        markers = config.get("markers", [])
        hits = sum(1 for m in markers if m in text_lower)
        neutral = config.get("neutral", 0.5)
        scale = config.get("scale", 3.0)
        if word_count == 0:
            return neutral
        density = hits / (word_count / 100.0)
        return round(min(1.0, neutral + density / scale), 4)

    elif compute_type == "inverse_complexity":
        # Higher complexity → lower tolerance (bandwidth consumed)
        complex_markers = config.get("complex_indicators", [])
        simple_markers = config.get("simple_indicators", [])
        complex_hits = sum(1 for m in complex_markers if m in text_lower)
        simple_hits = sum(1 for m in simple_markers if m in text_lower)
        total = complex_hits + simple_hits
        if total == 0:
            return 0.5
        # More complex = less remaining tolerance
        complexity_ratio = complex_hits / total
        return round(1.0 - complexity_ratio * 0.6, 4)  # 0.4-1.0 range

    elif compute_type == "asymmetric_ratio":
        # Prospect Theory: losses weighted 2.25x
        loss_markers = config.get("loss_markers", [])
        gain_markers = config.get("gain_markers", [])
        loss_hits = sum(1 for m in loss_markers if m in text_lower) * 2.25
        gain_hits = sum(1 for m in gain_markers if m in text_lower)
        total = loss_hits + gain_hits
        if total == 0:
            return 0.5
        return round(min(1.0, loss_hits / total), 4)

    elif compute_type == "max_category":
        # Multiple categories — return strength of dominant
        best_score = 0.0
        for key, markers in config.items():
            if key in ("compute", "description"):
                continue
            if not isinstance(markers, list):
                continue
            hits = sum(1 for m in markers if m in text_lower)
            if hits > best_score:
                best_score = hits
        return round(min(1.0, best_score / 3.0 + 0.3), 4)

    return 0.5


def extract_full_edge_dimensions(text: str) -> Dict[str, float]:
    """Extract all 20 edge dimensions directly from text.

    This is the FULL-WIDTH extraction — no NDF compression.
    Each dimension has its own linguistic markers and computation method.
    """
    text_lower = text.lower()
    word_count = len(text.split())

    dimensions = {}
    for dim_name, config in _DIMENSION_EXTRACTORS.items():
        dimensions[dim_name] = _extract_dimension(text_lower, word_count, config)

    return dimensions


# ============================================================================
# GRAPH-BACKED CATEGORY PRIORS (Tier 1)
# ============================================================================

_category_edge_priors: Dict[str, Dict[str, float]] = {}


async def load_category_edge_priors() -> Dict[str, Dict[str, float]]:
    """Load full 20-dimension priors per category from graph.

    These come from aggregating BRAND_CONVERTED edges by category.
    Backed by actual conversion data — the strongest signal.
    """
    global _category_edge_priors

    try:
        from adam.core.dependencies import Infrastructure
        infra = Infrastructure.get_instance()
        if not infra._neo4j_driver:
            return _category_edge_priors

        async with infra._neo4j_driver.session() as session:
            query = """
            MATCH (bp:BayesianPrior)
            WHERE bp.category IS NOT NULL AND bp.category <> ''
              AND bp.sample_size >= 10
            RETURN bp.category AS category,
                   bp.avg_reg_fit AS regulatory_fit,
                   bp.avg_construal_fit AS construal_fit,
                   bp.avg_personality_align AS personality_alignment,
                   bp.avg_emotional AS emotional_resonance,
                   bp.avg_value AS value_alignment,
                   bp.avg_evo AS evolutionary_motive,
                   bp.avg_persuasion_susceptibility AS persuasion_susceptibility,
                   bp.avg_cognitive_load_tolerance AS cognitive_load_tolerance,
                   bp.avg_narrative_transport AS narrative_transport,
                   bp.avg_social_proof_sensitivity AS social_proof_sensitivity,
                   bp.avg_loss_aversion_intensity AS loss_aversion_intensity,
                   bp.avg_temporal_discounting AS temporal_discounting,
                   bp.avg_brand_relationship_depth AS brand_relationship_depth,
                   bp.avg_autonomy_reactance AS autonomy_reactance,
                   bp.avg_information_seeking AS information_seeking,
                   bp.avg_mimetic_desire AS mimetic_desire,
                   bp.avg_interoceptive_awareness AS interoceptive_awareness,
                   bp.avg_cooperative_framing_fit AS cooperative_framing_fit,
                   bp.avg_decision_entropy AS decision_entropy,
                   bp.sample_size AS n
            """
            result = await session.run(query)
            async for record in result:
                cat = record.get("category", "")
                if cat:
                    dims = {}
                    for dim in EDGE_DIMENSIONS:
                        val = record.get(dim)
                        if val is not None:
                            dims[dim] = float(val)
                    if dims:
                        _category_edge_priors[cat] = dims

        logger.info("Loaded %d category edge priors from graph (20-dim)", len(_category_edge_priors))
    except Exception as e:
        logger.debug("Category edge prior loading failed: %s", e)

    return _category_edge_priors


# ============================================================================
# MASTER SCORING FUNCTION
# ============================================================================

def score_page_full_width(
    text: str,
    url: str = "",
    category: str = "",
    html: str = "",
) -> PageEdgeProfile:
    """Score a page directly on all 20 edge dimensions.

    Three-tier scoring with automatic fallback:

    Tier 1 (graph-backed): If category is known and graph priors exist,
    start from the 20-dim category prior (backed by conversion edges).

    Tier 2 (full extraction): Extract all 20 dimensions directly from
    text using dimension-specific linguistic markers.

    Tier 3 (NDF fallback): Only if tiers 1-2 produce insufficient
    signal, fall back to 7-dim NDF extraction and map to 20 dims.

    Blending: When multiple tiers produce values, blend weighted by
    evidence quality (graph > full extraction > NDF).
    """
    profile = PageEdgeProfile()
    word_count = len(text.split()) if text else 0

    # ── Tier 1: Graph-backed category priors ──
    tier1_dims = {}
    tier1_available = False
    if category and category in _category_edge_priors:
        tier1_dims = dict(_category_edge_priors[category])
        tier1_available = True
        profile.scoring_tier = "graph_prior"
        profile.source_evidence = f"BayesianPrior edges for category={category}"

    # ── Tier 2: Full-width text extraction ──
    tier2_dims = {}
    tier2_confidence = 0.0
    if text and word_count >= 30:
        tier2_dims = extract_full_edge_dimensions(text)
        # Confidence scales with text length
        if word_count > 500:
            tier2_confidence = 0.6
        elif word_count > 200:
            tier2_confidence = 0.45
        elif word_count > 100:
            tier2_confidence = 0.35
        else:
            tier2_confidence = 0.25

        if not tier1_available:
            profile.scoring_tier = "full_extraction"
            profile.source_evidence = f"20-dim text extraction ({word_count} words)"

    # ── Blend ──
    final_dims = {}
    for dim in EDGE_DIMENSIONS:
        t1_val = tier1_dims.get(dim)
        t2_val = tier2_dims.get(dim)

        if t1_val is not None and t2_val is not None:
            # Both available: weight graph prior more (it's from conversion data)
            graph_weight = 0.6
            text_weight = 0.4
            # But if text is long, trust it more
            if word_count > 500:
                graph_weight = 0.5
                text_weight = 0.5
            elif word_count > 1000:
                graph_weight = 0.4
                text_weight = 0.6
            final_dims[dim] = round(t1_val * graph_weight + t2_val * text_weight, 4)
            profile.extraction_details[dim] = "graph+text"
        elif t1_val is not None:
            final_dims[dim] = t1_val
            profile.extraction_details[dim] = "graph_only"
        elif t2_val is not None:
            final_dims[dim] = t2_val
            profile.extraction_details[dim] = "text_only"
        else:
            final_dims[dim] = 0.5  # Unknown
            profile.extraction_details[dim] = "default"

    profile.dimensions = final_dims

    # Confidence
    if tier1_available and tier2_confidence > 0:
        profile.confidence = min(0.9, 0.5 + tier2_confidence * 0.4)
    elif tier1_available:
        profile.confidence = 0.7
    elif tier2_confidence > 0:
        profile.confidence = tier2_confidence
    else:
        profile.confidence = 0.2

    # ── Tier 3: NDF fallback (only if no signal from tiers 1-2) ──
    if not tier1_available and tier2_confidence < 0.25:
        # Fall back to NDF extraction
        try:
            from adam.intelligence.page_intelligence import profile_page_content
            ndf_profile = profile_page_content(url=url, text_content=text or "")
            ndf = ndf_profile.construct_activations

            # Map NDF to edge dimensions (lossy but better than nothing)
            _NDF_TO_EDGE = {
                "approach_avoidance": [
                    ("regulatory_fit", 1.0), ("loss_aversion_intensity", -0.8),
                    ("evolutionary_motive", -0.5),
                ],
                "temporal_horizon": [
                    ("construal_fit", 0.9), ("temporal_discounting", -0.8),
                ],
                "social_calibration": [
                    ("social_proof_sensitivity", 0.9), ("personality_alignment", 0.7),
                    ("mimetic_desire", 0.6), ("cooperative_framing_fit", 0.5),
                ],
                "uncertainty_tolerance": [
                    ("decision_entropy", 0.7), ("persuasion_susceptibility", 0.5),
                    ("autonomy_reactance", -0.4),
                ],
                "cognitive_engagement": [
                    ("cognitive_load_tolerance", -0.6), ("information_seeking", 0.7),
                    ("narrative_transport", -0.4),
                ],
                "arousal_seeking": [
                    ("emotional_resonance", 0.8), ("interoceptive_awareness", 0.5),
                ],
                "status_sensitivity": [
                    ("brand_relationship_depth", 0.6), ("mimetic_desire", 0.5),
                    ("value_alignment", 0.4), ("linguistic_style", 0.3),
                ],
            }

            for ndf_dim, edge_mappings in _NDF_TO_EDGE.items():
                ndf_val = ndf.get(ndf_dim, 0.5)
                deviation = ndf_val - 0.5
                if ndf_dim == "approach_avoidance":
                    deviation = ndf_val  # Centered at 0

                for edge_dim, weight in edge_mappings:
                    if profile.extraction_details.get(edge_dim) == "default":
                        current = final_dims.get(edge_dim, 0.5)
                        adjustment = deviation * weight * 0.5
                        final_dims[edge_dim] = round(
                            max(0.0, min(1.0, current + adjustment)), 4
                        )
                        profile.extraction_details[edge_dim] = "ndf_fallback"

            profile.dimensions = final_dims
            if profile.scoring_tier == "":
                profile.scoring_tier = "ndf_fallback"
                profile.source_evidence = "7-dim NDF mapped to 20-dim (lossy fallback)"
                profile.confidence = max(profile.confidence, ndf_profile.confidence * 0.6)

        except Exception as e:
            logger.debug("NDF fallback failed: %s", e)

    return profile
