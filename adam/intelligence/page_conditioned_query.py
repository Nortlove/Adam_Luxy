"""
Page-Conditioned Graph Query — The Trilateral Evidence Engine
==============================================================

THE CORE QUESTION:
"Among the 6.7M bilateral edges, which conversions happened when the
buyer was in a psychological state SIMILAR to what this page creates —
and what alignment dimensions predicted those conversions?"

HOW IT WORKS:
The page creates a psychological state expressed in 20 edge dimensions.
The BRAND_CONVERTED edges record the buyer's psychological state (from
their review) in the same 20 dimensions. We find edges where the buyer
dimensions MATCH the page dimensions — because those buyers were in the
same psychological state the current reader is in.

This is not a formula. This is empirical evidence filtered by
psychological relevance.

EFFICIENCY:
Running a full 20-dim similarity filter on 6.7M edges per request is
too expensive (~500ms). Instead:

1. IDENTIFY the page's "signature dimensions" — the 3-5 dimensions where
   the page deviates most from neutral (0.5). These are the dimensions
   where the page has strong psychological signal.

2. FILTER edges only on those signature dimensions. A page with high
   loss_aversion (0.82) and high information_seeking (0.90) filters on
   those two, not all 20.

3. CACHE results per (signature_hash, category) with 24h TTL. Similar
   page states reuse cached evidence.

4. PRE-COMPUTE during daily strengthening for common page state clusters.

RESULT:
PageConditionedEvidence — what mechanism works when the reader is in
THIS psychological state, backed by actual conversion data.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Minimum absolute deviation from 0.5 to count as a "signature dimension"
_SIGNATURE_THRESHOLD = 0.10

# Minimum edges to consider evidence reliable
_MIN_EVIDENCE_EDGES = 10

# How wide the filter window is around the page value (±tolerance)
_DIMENSION_TOLERANCE = 0.25

# Maximum dimensions to filter on (more = fewer matching edges)
_MAX_FILTER_DIMS = 3

# Dimensions ranked by discriminating power (from empirical variance analysis).
# High-variance dims actually DIFFERENTIATE page states.
# Low-variance dims score nearly the same on every page — they're noise.
# The page-conditioned query should ONLY filter on discriminating dims.
_DISCRIMINATING_DIMS = [
    "personality_alignment",    # var=0.037 — social/tribal vs individual
    "construal_fit",            # var=0.031 — abstract vs concrete
    "evolutionary_motive",      # var=0.030 — survival/status activation
    "temporal_discounting",     # var=0.030 — present urgency vs future
    "regulatory_fit",           # var=0.025 — approach vs prevention
    "loss_aversion_intensity",  # var=0.024 — loss aversion activation
    "persuasion_susceptibility",# var=0.021 — openness to persuasion
    "linguistic_style",         # var=0.021 — formal vs casual register
    "cognitive_load_tolerance", # var=0.021 — remaining bandwidth
    "decision_entropy",         # var=0.019 — choice difficulty
    "autonomy_reactance",       # var=0.016 — resistance to direction
]

# Non-discriminating dims — don't waste filter budget on these
_NON_DISCRIMINATING_DIMS = frozenset([
    "emotional_resonance",      # var=0.001 — too similar across pages
    "value_alignment",          # var=0.001
    "narrative_transport",      # var=0.003
    "social_proof_sensitivity", # var=0.002
    "brand_relationship_depth", # var=0.002
    "information_seeking",      # var=0.002
    "mimetic_desire",           # var=0.001
    "interoceptive_awareness",  # var=0.002
    "cooperative_framing_fit",  # var=0.005
])

# Cache TTL for page-conditioned results
_CACHE_TTL = 86400  # 24 hours

# Actual value ranges observed in Neo4j BRAND_CONVERTED edges.
# Page values (0-1) are mapped to these ranges before filtering.
_DIM_GRAPH_RANGES = {
    "regulatory_fit": (-0.7, 0.63),
    "construal_fit": (0.0, 1.0),
    "personality_alignment": (0.0, 1.0),
    "emotional_resonance": (0.04, 0.85),
    "value_alignment": (0.0, 1.0),
    "evolutionary_motive": (0.0, 1.0),
    "linguistic_style": (0.0, 1.0),
    "persuasion_susceptibility": (0.0, 1.0),
    "cognitive_load_tolerance": (0.0, 1.0),
    "narrative_transport": (0.0, 1.0),
    "social_proof_sensitivity": (0.0, 0.5),
    "loss_aversion_intensity": (0.32, 0.80),
    "temporal_discounting": (0.0, 1.0),
    "brand_relationship_depth": (0.0, 1.0),
    "autonomy_reactance": (0.0, 1.0),
    "information_seeking": (0.0, 1.0),
    "mimetic_desire": (0.0, 1.0),
    "interoceptive_awareness": (0.0, 1.0),
    "cooperative_framing_fit": (0.0, 1.0),
    "decision_entropy": (0.0, 1.0),
}

# Dimensions that are all zeros or null in current graph data.
# Skip these in WHERE clauses to avoid filtering out everything.
# NOTE: luxury_transportation edges (1,629) DO populate these.
# Only skip for categories that haven't been re-annotated.
_UNPOPULATED_DIMS: set = set()  # All dims now populated in annotated edges

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
class PageConditionedEvidence:
    """What the graph tells us about ads that work in this page state."""

    # What converted when the buyer was in this state
    optimal_alignment: Dict[str, float] = field(default_factory=dict)
    """The 20-dim alignment profile of successful conversions under
    this page state. This is what the ad needs to achieve."""

    # Which mechanisms worked
    mechanism_effectiveness: Dict[str, float] = field(default_factory=dict)
    """Per-mechanism conversion rate among matching edges."""

    # The evidence strength
    matching_edge_count: int = 0
    total_edge_count: int = 0
    confidence: float = 0.0

    # What we filtered on
    signature_dimensions: List[str] = field(default_factory=list)
    """The page dimensions that drove the filtering."""

    page_state_hash: str = ""
    """Hash of the page state for caching."""

    category: str = ""
    """Product category context (if filtered)."""

    # Creative direction derived from the evidence
    creative_direction: Dict[str, Any] = field(default_factory=dict)
    """What the successful ads in this state communicated."""

    # Gradient priorities conditioned on this page state
    conditioned_gradient: Dict[str, float] = field(default_factory=dict)
    """∂P(conversion)/∂dimension for edges matching this page state."""

    # Comparison to unconditioned baseline
    baseline_alignment: Dict[str, float] = field(default_factory=dict)
    """Unconditioned (all edges) alignment for comparison."""

    delta_from_baseline: Dict[str, float] = field(default_factory=dict)
    """How the page state shifts optimal alignment vs baseline."""


def compute_page_state_signature(
    page_edge_dims: Dict[str, float],
) -> Tuple[List[str], str]:
    """Identify the page's signature dimensions and compute a cache hash.

    Signature dimensions = dimensions where the page deviates most from
    neutral (0.5). These are where the page has strong psychological signal.

    Returns:
        (signature_dims, state_hash)
    """
    deviations = []
    for dim in _DISCRIMINATING_DIMS:  # Only consider dims that actually differentiate pages
        val = page_edge_dims.get(dim, 0.5)
        deviation = abs(val - 0.5)
        if deviation > _SIGNATURE_THRESHOLD:
            deviations.append((dim, deviation, val))

    # Sort by deviation magnitude (strongest signal first)
    deviations.sort(key=lambda x: x[1], reverse=True)

    # Take top N dimensions
    signature_dims = [d[0] for d in deviations[:_MAX_FILTER_DIMS]]

    # Compute hash for caching
    # Quantize values to 0.1 bins so similar page states share cache
    hash_parts = []
    for dim in sorted(signature_dims):
        val = page_edge_dims.get(dim, 0.5)
        quantized = round(val * 10) / 10  # Round to nearest 0.1
        hash_parts.append(f"{dim}:{quantized}")
    state_hash = hashlib.md5("|".join(hash_parts).encode()).hexdigest()[:12]

    return signature_dims, state_hash


def _build_page_conditioned_cypher(
    signature_dims: List[str],
    page_edge_dims: Dict[str, float],
    category: str = "",
    tolerance: float = _DIMENSION_TOLERANCE,
) -> Tuple[str, Dict[str, Any]]:
    """Build the Cypher query for page-conditioned edge retrieval.

    Filters BRAND_CONVERTED edges where the buyer-side dimensions
    are within ±tolerance of the page's values on signature dimensions.
    """
    # Map our 20 edge dimension names to ACTUAL Neo4j edge property names.
    # The graph uses different naming conventions (from the original annotation).
    # Properties confirmed present on 6.7M BRAND_CONVERTED edges:
    #   regulatory_fit_score, construal_fit_score, personality_brand_alignment,
    #   emotional_resonance, value_alignment, evolutionary_motive_match,
    #   linguistic_style_matching, composite_alignment, persuasion_confidence_multiplier,
    #   reactance_fit, self_monitoring_fit, processing_route_match,
    #   spending_pain_match, brand_trust_fit, identity_signaling_match,
    #   mental_simulation_resonance, anchor_susceptibility_match,
    #   mental_ownership_match, optimal_distinctiveness_fit, appeal_resonance,
    #   involvement_weight_modifier, lay_theory_alignment,
    #   negativity_bias_match, disgust_contamination_fit,
    #   uniqueness_popularity_fit, full_cosine_alignment
    _DIM_TO_PROPERTY = {
        "regulatory_fit": "bc.regulatory_fit_score",
        "construal_fit": "bc.construal_fit_score",
        "personality_alignment": "bc.personality_brand_alignment",
        "emotional_resonance": "bc.emotional_resonance",
        "value_alignment": "bc.value_alignment",
        "evolutionary_motive": "bc.evolutionary_motive_match",
        "linguistic_style": "bc.linguistic_style_matching",
        # Extended dims → mapped to closest actual edge properties
        "persuasion_susceptibility": "bc.persuasion_confidence_multiplier",
        "cognitive_load_tolerance": "bc.processing_route_match",
        "narrative_transport": "bc.mental_simulation_resonance",
        "social_proof_sensitivity": "bc.optimal_distinctiveness_fit",
        "loss_aversion_intensity": "bc.spending_pain_match",
        "temporal_discounting": "bc.involvement_weight_modifier",
        "brand_relationship_depth": "bc.brand_trust_fit",
        "autonomy_reactance": "bc.reactance_fit",
        "information_seeking": "bc.self_monitoring_fit",
        "mimetic_desire": "bc.identity_signaling_match",
        "interoceptive_awareness": "bc.anchor_susceptibility_match",
        "cooperative_framing_fit": "bc.lay_theory_alignment",
        "decision_entropy": "bc.negativity_bias_match",
    }

    # Build WHERE clauses for signature dimensions
    where_clauses = []
    params: Dict[str, Any] = {}

    if category:
        where_clauses.append("bc.product_category CONTAINS $category")
        params["category"] = category

    for dim in signature_dims:
        page_val = page_edge_dims.get(dim, 0.5)
        low = max(0.0, page_val - tolerance)
        high = min(1.0, page_val + tolerance)

        edge_prop = _DIM_TO_PROPERTY.get(dim)
        if not edge_prop:
            continue

        # Skip dimensions known to be unpopulated (all zeros) in the graph
        if dim in _UNPOPULATED_DIMS:
            continue

        # Use the page value directly — most edge properties are in 0-1 space.
        # For regulatory_fit (which ranges -0.7 to 0.63), map from 0-1 to that range.
        if dim == "regulatory_fit":
            mapped_val = -0.7 + page_val * 1.33  # Map [0,1] → [-0.7, 0.63]
        else:
            mapped_val = page_val

        param_low = f"p_{dim}_low"
        param_high = f"p_{dim}_high"
        params[param_low] = mapped_val - tolerance
        params[param_high] = mapped_val + tolerance

        where_clauses.append(
            f"{edge_prop} >= ${param_low} AND {edge_prop} <= ${param_high}"
        )

    where_str = " AND ".join(where_clauses) if where_clauses else "TRUE"

    # Build the full query using ACTUAL edge property names
    query = f"""
    MATCH (pd:ProductDescription)-[bc:BRAND_CONVERTED]->(ar:AnnotatedReview)
    WHERE {where_str}
    RETURN
        count(bc) AS edge_count,
        avg(bc.composite_alignment) AS avg_composite,
        avg(bc.regulatory_fit_score) AS avg_reg_fit,
        avg(bc.construal_fit_score) AS avg_construal_fit,
        avg(bc.personality_brand_alignment) AS avg_personality,
        avg(bc.emotional_resonance) AS avg_emotional,
        avg(bc.value_alignment) AS avg_value,
        avg(bc.evolutionary_motive_match) AS avg_evo,
        avg(bc.linguistic_style_matching) AS avg_linguistic,
        avg(bc.persuasion_confidence_multiplier) AS avg_confidence,
        avg(bc.spending_pain_match) AS avg_loss_aversion_intensity,
        avg(bc.reactance_fit) AS avg_autonomy_reactance,
        avg(bc.self_monitoring_fit) AS avg_information_seeking,
        avg(bc.processing_route_match) AS avg_cognitive_load_tolerance,
        avg(bc.mental_simulation_resonance) AS avg_narrative_transport,
        avg(bc.optimal_distinctiveness_fit) AS avg_social_proof_sensitivity,
        avg(bc.involvement_weight_modifier) AS avg_temporal_discounting,
        avg(bc.brand_trust_fit) AS avg_brand_relationship_depth,
        avg(bc.identity_signaling_match) AS avg_mimetic_desire,
        avg(bc.anchor_susceptibility_match) AS avg_interoceptive_awareness,
        avg(bc.lay_theory_alignment) AS avg_cooperative_framing_fit,
        avg(bc.negativity_bias_match) AS avg_decision_entropy
    """

    return query, params


def _extract_alignment_from_result(record: Any) -> Dict[str, float]:
    """Extract the 20-dim alignment vector from a Neo4j query result."""
    _RESULT_TO_DIM = {
        "avg_reg_fit": "regulatory_fit",
        "avg_construal_fit": "construal_fit",
        "avg_personality": "personality_alignment",
        "avg_emotional": "emotional_resonance",
        "avg_value": "value_alignment",
        "avg_evo": "evolutionary_motive",
        "avg_linguistic": "linguistic_style",
        "avg_confidence": "persuasion_susceptibility",  # Close enough proxy
        "avg_persuasion_susceptibility": "persuasion_susceptibility",
        "avg_cognitive_load_tolerance": "cognitive_load_tolerance",
        "avg_narrative_transport": "narrative_transport",
        "avg_social_proof_sensitivity": "social_proof_sensitivity",
        "avg_loss_aversion_intensity": "loss_aversion_intensity",
        "avg_temporal_discounting": "temporal_discounting",
        "avg_brand_relationship_depth": "brand_relationship_depth",
        "avg_autonomy_reactance": "autonomy_reactance",
        "avg_information_seeking": "information_seeking",
        "avg_mimetic_desire": "mimetic_desire",
        "avg_interoceptive_awareness": "interoceptive_awareness",
        "avg_cooperative_framing_fit": "cooperative_framing_fit",
        "avg_decision_entropy": "decision_entropy",
    }

    alignment = {}
    for result_key, dim_name in _RESULT_TO_DIM.items():
        val = record.get(result_key)
        if val is not None:
            alignment[dim_name] = round(float(val), 4)
        else:
            alignment[dim_name] = 0.5

    return alignment


def _derive_mechanism_from_alignment(
    alignment: Dict[str, float],
) -> Dict[str, float]:
    """Derive mechanism effectiveness from the alignment that converts
    in this page state.

    Uses the SAME formulas as the cascade (bilateral_cascade.py lines 661-738)
    but applied to the page-conditioned alignment instead of raw edges.
    """
    reg = alignment.get("regulatory_fit", 0.5)
    con = alignment.get("construal_fit", 0.5)
    pers = alignment.get("personality_alignment", 0.5)
    emo = alignment.get("emotional_resonance", 0.5)
    val = alignment.get("value_alignment", 0.5)
    evo = alignment.get("evolutionary_motive", 0.5)
    ps = alignment.get("persuasion_susceptibility", 0.5)
    clt = alignment.get("cognitive_load_tolerance", 0.5)
    nt = alignment.get("narrative_transport", 0.5)
    sps = alignment.get("social_proof_sensitivity", 0.5)
    lai = alignment.get("loss_aversion_intensity", 0.5)
    td = alignment.get("temporal_discounting", 0.5)
    brd = alignment.get("brand_relationship_depth", 0.5)
    ar = alignment.get("autonomy_reactance", 0.5)
    isk = alignment.get("information_seeking", 0.5)
    md = alignment.get("mimetic_desire", 0.5)
    ia = alignment.get("interoceptive_awareness", 0.5)
    cf = alignment.get("cooperative_framing_fit", 0.5)
    de = alignment.get("decision_entropy", 0.5)

    mechanisms = {
        "authority": (
            0.30 * con + 0.20 * ps + 0.15 * (1.0 - emo)
            + 0.15 * clt + 0.10 * isk + 0.10 * (1.0 - ar)
        ),
        "social_proof": (
            0.25 * sps + 0.20 * pers + 0.15 * md
            + 0.15 * val + 0.15 * emo + 0.10 * (1.0 - ar)
        ),
        "scarcity": (
            0.25 * td + 0.20 * emo + 0.15 * lai
            + 0.15 * (1.0 - clt) + 0.15 * md + 0.10 * ps
        ),
        "loss_aversion": (
            0.30 * lai + 0.20 * (1.0 - reg) + 0.15 * td
            + 0.15 * ps + 0.10 * evo + 0.10 * de
        ),
        "commitment": (
            0.25 * brd + 0.20 * val + 0.20 * (1.0 - td)
            + 0.15 * cf + 0.10 * (1.0 - de) + 0.10 * con
        ),
        "liking": (
            0.25 * pers + 0.20 * emo + 0.20 * nt
            + 0.15 * (1.0 - ar) + 0.10 * ia + 0.10 * md
        ),
        "reciprocity": (
            0.30 * cf + 0.20 * val + 0.15 * (1.0 - ar)
            + 0.15 * pers + 0.10 * brd + 0.10 * (1.0 - de)
        ),
        "curiosity": (
            0.25 * isk + 0.20 * nt + 0.20 * emo
            + 0.15 * (1.0 - de) + 0.10 * con + 0.10 * md
        ),
        "cognitive_ease": (
            0.30 * (1.0 - clt) + 0.20 * (1.0 - de)
            + 0.20 * (1.0 - ar) + 0.15 * nt + 0.15 * ia
        ),
        "unity": (
            0.30 * cf + 0.25 * sps + 0.20 * pers
            + 0.15 * md + 0.10 * (1.0 - ar)
        ),
    }

    return {k: round(v, 4) for k, v in mechanisms.items()}


def _derive_creative_direction(
    alignment: Dict[str, float],
    mechanisms: Dict[str, float],
    page_edge_dims: Dict[str, float],
) -> Dict[str, Any]:
    """Derive creative direction from page-conditioned evidence."""
    reg = alignment.get("regulatory_fit", 0.5)
    con = alignment.get("construal_fit", 0.5)
    emo = alignment.get("emotional_resonance", 0.5)
    td = alignment.get("temporal_discounting", 0.5)
    clt = alignment.get("cognitive_load_tolerance", 0.5)

    # Framing
    if reg > 0.6:
        framing = "gain"
    elif reg < 0.4:
        framing = "loss"
    else:
        framing = "mixed"

    # Construal
    if con > 0.6:
        construal = "abstract"
    elif con < 0.4:
        construal = "concrete"
    else:
        construal = "moderate"

    # Urgency
    urgency = round(td * 0.6 + emo * 0.4, 2)

    # Complexity
    if clt > 0.6:
        complexity = "detailed"
    elif clt < 0.4:
        complexity = "simple"
    else:
        complexity = "moderate"

    # Top mechanisms
    ranked = sorted(mechanisms.items(), key=lambda x: x[1], reverse=True)
    primary = ranked[0][0]
    secondary = ranked[1][0] if len(ranked) > 1 else ""

    # What the page already did vs what the ad needs to do
    page_contributions = []
    ad_needs = []
    for dim in ["loss_aversion_intensity", "information_seeking",
                "social_proof_sensitivity", "autonomy_reactance",
                "regulatory_fit", "cognitive_load_tolerance"]:
        page_val = page_edge_dims.get(dim, 0.5)
        optimal_val = alignment.get(dim, 0.5)
        gap = optimal_val - page_val
        if abs(gap) < 0.1:
            page_contributions.append(f"Page already aligned {dim}")
        elif gap > 0.1:
            ad_needs.append(f"Ad must increase {dim} (+{gap:.2f})")
        elif gap < -0.1:
            ad_needs.append(f"Ad must decrease {dim} ({gap:.2f})")

    return {
        "primary_mechanism": primary,
        "secondary_mechanism": secondary,
        "framing": framing,
        "construal_level": construal,
        "urgency_level": urgency,
        "complexity": complexity,
        "page_contributions": page_contributions[:3],
        "ad_needs": ad_needs[:5],
        "evidence_based": True,
    }


# ============================================================================
# MAIN QUERY FUNCTION
# ============================================================================

async def query_page_conditioned_edges(
    page_edge_dims: Dict[str, float],
    category: str = "",
    asin: str = "",
) -> Optional[PageConditionedEvidence]:
    """Query the graph for conversions matching this page's psychological state.

    This is THE core function. It asks: "When buyers were in a state
    similar to what this page creates, what alignment dimensions and
    mechanisms predicted conversion?"

    Args:
        page_edge_dims: 20-dim page edge profile
        category: product category to filter on (optional, improves precision)
        asin: specific product ASIN (optional, for product-specific evidence)

    Returns:
        PageConditionedEvidence with empirical mechanism recommendations,
        or None if insufficient evidence.
    """
    if not page_edge_dims:
        return None

    # Step 1: Identify signature dimensions
    signature_dims, state_hash = compute_page_state_signature(page_edge_dims)

    if not signature_dims:
        logger.debug("No signature dimensions — page is neutral on all dims")
        return None

    # Step 2: Check cache
    cache_key = f"informativ:page_conditioned:{state_hash}:{category or 'all'}"
    r = _get_redis()
    if r:
        try:
            cached = r.hgetall(cache_key)
            if cached and "matching_edge_count" in cached:
                return _deserialize_evidence(cached)
        except Exception:
            pass

    # Step 3: Query Neo4j
    evidence = await _execute_graph_query(
        page_edge_dims, signature_dims, state_hash, category, asin,
    )

    if evidence is None:
        # Try with relaxed tolerance
        evidence = await _execute_graph_query(
            page_edge_dims, signature_dims[:3], state_hash, category, asin,
            tolerance=_DIMENSION_TOLERANCE * 1.5,
        )

    if evidence is None:
        # Last resort: unconditioned query (all edges)
        evidence = await _execute_graph_query(
            page_edge_dims, [], state_hash, category, asin,
        )
        if evidence:
            evidence.confidence *= 0.5  # Lower confidence for unconditioned

    # Step 4: Cache result
    if evidence and r:
        try:
            r.hset(cache_key, mapping=_serialize_evidence(evidence))
            r.expire(cache_key, _CACHE_TTL)
        except Exception:
            pass

    return evidence


async def _execute_graph_query(
    page_edge_dims: Dict[str, float],
    signature_dims: List[str],
    state_hash: str,
    category: str,
    asin: str,
    tolerance: float = _DIMENSION_TOLERANCE,
) -> Optional[PageConditionedEvidence]:
    """Execute the page-conditioned Cypher query."""
    try:
        from adam.core.dependencies import Infrastructure
        infra = Infrastructure.get_instance()
        if not infra._neo4j_driver:
            # Try initializing if not yet done (script context)
            try:
                await infra.initialize()
            except Exception:
                pass
        if not infra._neo4j_driver:
            return None

        # Build query
        query, params = _build_page_conditioned_cypher(
            signature_dims, page_edge_dims, category, tolerance,
        )

        # Execute
        async with infra._neo4j_driver.session() as session:
            result = await session.run(query, params)
            record = await result.single()

            if not record:
                return None

            edge_count = record.get("edge_count", 0)
            if edge_count < _MIN_EVIDENCE_EDGES:
                return None

            # Extract alignment
            alignment = _extract_alignment_from_result(dict(record))

            # Derive mechanisms from alignment
            mechanisms = _derive_mechanism_from_alignment(alignment)

            # Derive creative direction
            creative = _derive_creative_direction(
                alignment, mechanisms, page_edge_dims,
            )

            # Compute confidence
            confidence = min(0.9,
                0.3 + 0.1 * min(1.0, edge_count / 100)
                + 0.1 * len(signature_dims) / _MAX_FILTER_DIMS
                + 0.2 * (1.0 if category else 0.0)
            )

            # Compute delta from what unconditioned would give
            # (this shows the VALUE of page conditioning)
            delta = {}
            for dim in EDGE_DIMENSIONS:
                page_val = page_edge_dims.get(dim, 0.5)
                optimal_val = alignment.get(dim, 0.5)
                delta[dim] = round(optimal_val - 0.5, 4)  # vs neutral baseline

            evidence = PageConditionedEvidence(
                optimal_alignment=alignment,
                mechanism_effectiveness=mechanisms,
                matching_edge_count=edge_count,
                confidence=confidence,
                signature_dimensions=signature_dims,
                page_state_hash=state_hash,
                category=category,
                creative_direction=creative,
                delta_from_baseline=delta,
            )

            return evidence

    except Exception as e:
        logger.debug("Page-conditioned graph query failed: %s", e)
        return None


# ============================================================================
# PRE-COMPUTATION (for daily strengthening)
# ============================================================================

async def precompute_common_page_states(
    page_states: List[Dict[str, float]],
    categories: List[str],
) -> int:
    """Pre-compute page-conditioned evidence for common page states.

    Called by the daily strengthening scheduler. Runs the expensive
    graph query for common page state signatures so bid-time lookups
    are cache hits.
    """
    computed = 0

    for page_state in page_states:
        for category in categories:
            try:
                evidence = await query_page_conditioned_edges(
                    page_edge_dims=page_state,
                    category=category,
                )
                if evidence:
                    computed += 1
            except Exception:
                pass

    logger.info("Pre-computed %d page-conditioned evidence entries", computed)
    return computed


# ============================================================================
# HELPERS
# ============================================================================

def _get_redis():
    try:
        import redis
        r = redis.Redis(host="localhost", port=6379, decode_responses=True)
        r.ping()
        return r
    except Exception:
        return None


def _serialize_evidence(e: PageConditionedEvidence) -> Dict[str, str]:
    return {
        "optimal_alignment": json.dumps(e.optimal_alignment),
        "mechanism_effectiveness": json.dumps(e.mechanism_effectiveness),
        "matching_edge_count": str(e.matching_edge_count),
        "confidence": str(e.confidence),
        "signature_dimensions": json.dumps(e.signature_dimensions),
        "page_state_hash": e.page_state_hash,
        "category": e.category,
        "creative_direction": json.dumps(e.creative_direction),
        "delta_from_baseline": json.dumps(e.delta_from_baseline),
        "cached_at": str(time.time()),
    }


def _deserialize_evidence(data: Dict[str, str]) -> PageConditionedEvidence:
    def _jl(val, default):
        if isinstance(val, str):
            try:
                return json.loads(val)
            except (json.JSONDecodeError, TypeError):
                return default
        return val if val is not None else default

    return PageConditionedEvidence(
        optimal_alignment=_jl(data.get("optimal_alignment"), {}),
        mechanism_effectiveness=_jl(data.get("mechanism_effectiveness"), {}),
        matching_edge_count=int(data.get("matching_edge_count", 0)),
        confidence=float(data.get("confidence", 0)),
        signature_dimensions=_jl(data.get("signature_dimensions"), []),
        page_state_hash=data.get("page_state_hash", ""),
        category=data.get("category", ""),
        creative_direction=_jl(data.get("creative_direction"), {}),
        delta_from_baseline=_jl(data.get("delta_from_baseline"), {}),
    )
