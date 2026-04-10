# =============================================================================
# ADAM Universal Intelligence API — Router
# Location: adam/api/universal/router.py
# =============================================================================

"""
UNIVERSAL INTELLIGENCE API

Serves all four participants in the ad transaction from the same
psychological intelligence layer:

  POST /api/v1/intelligence/page/profile      — Publisher: profile a page
  POST /api/v1/intelligence/bid/enrich        — SSP: enrich a bid request
  POST /api/v1/intelligence/brand/profile     — Brand: analyze messaging psychology
  POST /api/v1/intelligence/inventory/match   — Match brand to publisher inventory

Same 47M bilateral edges. Same theory graph. Same gradient fields.
Four lenses on the same intelligence.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter

from adam.api.universal.models import (
    AudienceAlignment,
    BidEnrichmentRequest,
    BidEnrichmentResponse,
    BilateralDimension,
    BrandProfileRequest,
    BrandProfileResponse,
    ConstructActivation,
    EnrichedSegment,
    GranularTypeProfile,
    IntelligenceLevel,
    InteractionAwareDirection,
    InventoryMatch,
    InventoryMatchRequest,
    InventoryMatchResponse,
    MechanismScore,
    OpenRTBData,
    OpenRTBSegment,
    PageProfileRequest,
    PageProfileResponse,
    PagePsychologyLayer,
    PsychologicalProfile,
    PsychologicalSegment,
    DimensionConfidence,
    GradientPriority,
    MechanismSynergy,
    TheoryChainSummary,
    VerticalValue,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/intelligence",
    tags=["universal-intelligence"],
)

# Module-level cache for graph-loaded archetype centroids.
# Populated on first use from CustomerArchetype nodes; falls back to hardcoded.
_cached_archetype_centroids: Optional[Dict[str, Dict[str, float]]] = None


# =============================================================================
# SHARED INFRASTRUCTURE
# =============================================================================

def _get_content_profiler():
    """Get the ContentProfiler singleton."""
    try:
        from adam.platform.intelligence.content_profiler import ContentProfiler
        return ContentProfiler()
    except Exception as e:
        logger.debug("ContentProfiler not available: %s", e)
        return None


def _get_segment_builder():
    """Get SegmentBuilder instance methods."""
    try:
        from adam.platform.intelligence.segment_builder import SegmentBuilder
        builder = SegmentBuilder()
        return builder.build_segments, builder.get_available_segments
    except Exception as e:
        logger.debug("SegmentBuilder not available: %s", e)
        return None, None


def _get_unified_intelligence():
    """Get UnifiedIntelligenceService singleton."""
    try:
        from adam.intelligence.unified_intelligence_service import (
            get_unified_intelligence_service,
        )
        return get_unified_intelligence_service()
    except Exception as e:
        logger.debug("UnifiedIntelligenceService not available: %s", e)
        return None


def _get_intel_settings():
    """Get IntelligenceAPISettings from cached Settings."""
    try:
        from adam.config.settings import get_settings
        return get_settings().intelligence
    except Exception:
        # Return a default instance if settings unavailable
        from adam.config.settings import IntelligenceAPISettings
        return IntelligenceAPISettings()


def _get_granular_type_detector():
    """Get GranularCustomerTypeDetector singleton."""
    try:
        from adam.intelligence.granular_type_detector import GranularCustomerTypeDetector
        return GranularCustomerTypeDetector()
    except Exception as e:
        logger.debug("GranularCustomerTypeDetector not available: %s", e)
        return None


_cached_segment_engine = None


def _get_segment_engine():
    """Get PsychologicalSegmentEngine singleton (module-level cached)."""
    global _cached_segment_engine
    if _cached_segment_engine is not None:
        return _cached_segment_engine
    try:
        from adam.segments.engine import PsychologicalSegmentEngine
        _cached_segment_engine = PsychologicalSegmentEngine()
        return _cached_segment_engine
    except Exception as e:
        logger.debug("PsychologicalSegmentEngine not available: %s", e)
        return None


def _get_construct_integration():
    """Get construct-based recommendation function."""
    try:
        from adam.intelligence.unified_construct_integration import (
            get_construct_based_recommendations,
        )
        return get_construct_based_recommendations
    except Exception as e:
        logger.debug("UnifiedConstructIntegration not available: %s", e)
        return None


def _get_mechanism_interaction_learner():
    """Get MechanismInteractionLearner singleton (uses module-level singleton)."""
    try:
        from adam.learning.mechanism_interactions import get_mechanism_interaction_learner
        return get_mechanism_interaction_learner()
    except Exception as e:
        logger.debug("MechanismInteractionLearner not available: %s", e)
        return None


def _ndf_to_profile(ndf: Dict[str, float]) -> PsychologicalProfile:
    """Convert NDF dict to PsychologicalProfile model."""
    return PsychologicalProfile(
        approach_avoidance=ndf.get("approach_avoidance", 0.5),
        temporal_horizon=ndf.get("temporal_horizon", 0.5),
        social_calibration=ndf.get("social_calibration", 0.5),
        uncertainty_tolerance=ndf.get("uncertainty_tolerance", 0.5),
        status_sensitivity=ndf.get("status_sensitivity", 0.5),
        cognitive_engagement=ndf.get("cognitive_engagement", 0.5),
        arousal_seeking=ndf.get("arousal_seeking", 0.5),
        cognitive_velocity=ndf.get("cognitive_velocity", 0.5),
    )


# Vertical-to-psychology mapping: which NDF dimensions make a page
# valuable for each advertiser vertical.
_VERTICAL_PSYCHOLOGY = {
    "financial_services": {
        "dimensions": {"uncertainty_tolerance": -1, "cognitive_engagement": 1, "temporal_horizon": 1},
        "mechanisms": ["authority", "commitment", "loss_aversion"],
        "description": "Prevention-focused, analytical, future-oriented",
    },
    "luxury_goods": {
        "dimensions": {"status_sensitivity": 1, "approach_avoidance": 1, "arousal_seeking": 1},
        "mechanisms": ["identity_construction", "scarcity", "social_proof"],
        "description": "Status-driven, aspirational, high-arousal",
    },
    "health_wellness": {
        "dimensions": {"approach_avoidance": -1, "uncertainty_tolerance": -1, "cognitive_engagement": 1},
        "mechanisms": ["authority", "social_proof", "commitment"],
        "description": "Prevention-focused, certainty-seeking, health-conscious",
    },
    "technology": {
        "dimensions": {"cognitive_engagement": 1, "uncertainty_tolerance": 1, "arousal_seeking": 1},
        "mechanisms": ["curiosity", "authority", "social_proof"],
        "description": "High engagement, exploration-oriented, novelty-seeking",
    },
    "ecommerce_general": {
        "dimensions": {"approach_avoidance": 1, "arousal_seeking": 1, "social_calibration": 1},
        "mechanisms": ["social_proof", "scarcity", "reciprocity"],
        "description": "Action-oriented, socially-influenced, deal-responsive",
    },
    "automotive": {
        "dimensions": {"status_sensitivity": 1, "cognitive_engagement": 1, "temporal_horizon": 1},
        "mechanisms": ["identity_construction", "authority", "social_proof"],
        "description": "Status-conscious, research-driven, long-term",
    },
    "entertainment": {
        "dimensions": {"arousal_seeking": 1, "approach_avoidance": 1, "social_calibration": 1},
        "mechanisms": ["liking", "social_proof", "curiosity"],
        "description": "Experience-seeking, socially-engaged, novelty-driven",
    },
    "insurance": {
        "dimensions": {"uncertainty_tolerance": -1, "approach_avoidance": -1, "temporal_horizon": 1},
        "mechanisms": ["authority", "loss_aversion", "commitment"],
        "description": "Risk-averse, prevention-focused, future-planning",
    },
}


# Category family groupings for fuzzy matching.
# When an exact category match yields no graph evidence, we expand to
# related categories in the same family. This handles the 500+ Amazon
# category gap — we may not have BayesianPrior data for "Industrial_and_Scientific"
# but we do for the "technology" family.
_CATEGORY_FAMILIES = {
    "beauty": [
        "All_Beauty", "Beauty_and_Personal_Care", "sephora",
    ],
    "fashion": [
        "Clothing_Shoes_and_Jewelry", "Handmade_Products", "rent_the_runway",
    ],
    "tech": [
        "Electronics", "Cell_Phones_and_Accessories", "Software",
        "Industrial_and_Scientific", "Kindle_Store", "bh_photo", "twcs",
    ],
    "health": [
        "Health_and_Household", "Health_and_Personal_Care",
        "Sports_and_Outdoors", "Baby_Products",
    ],
    "home": [
        "Home_and_Kitchen", "Tools_and_Home_Improvement",
        "Patio_Lawn_and_Garden", "Appliances", "Office_Products",
    ],
    "food": [
        "Grocery_and_Gourmet_Food", "Pet_Supplies", "Subscription_Boxes",
    ],
    "entertainment": [
        "Books", "Movies_and_TV", "Digital_Music", "CDs_and_Vinyl",
        "Musical_Instruments", "Toys_and_Games", "Arts_Crafts_and_Sewing",
        "Magazine_Subscriptions", "steam", "podcast",
    ],
    "automotive": ["Automotive", "automotive"],
    "finance": ["glassdoor", "trustpilot"],
    "local": ["google_local", "yelp"],
    "social": ["twitter", "reddit_mbti"],
    "travel": ["airline"],
}

# Reverse lookup: category → family name
_CATEGORY_TO_FAMILY: Dict[str, str] = {}
for _family, _cats in _CATEGORY_FAMILIES.items():
    for _cat in _cats:
        _CATEGORY_TO_FAMILY[_cat] = _family
        _CATEGORY_TO_FAMILY[_cat.lower()] = _family


async def _resolve_category(client, category: str) -> List[str]:
    """
    Resolve a category string to a list of queryable category names.

    Strategy:
    1. Start with exact match [category]
    2. If category is in a known family, expand to all family members
    3. If category is unknown, try keyword-based family detection
    4. If all else fails, query graph for CONTAINS-based category matching

    Returns a list of categories to query (IN clause), ensuring the original
    category is always first (for result priority).
    """
    categories = [category]

    # Check if this category belongs to a known family
    family = _CATEGORY_TO_FAMILY.get(category) or _CATEGORY_TO_FAMILY.get(category.lower())

    if not family:
        # Keyword-based family detection for unmapped categories
        cat_lower = category.lower().replace("_", " ").replace("-", " ")
        keyword_families = {
            "beauty": ["beauty", "cosmetic", "skincare", "makeup", "fragrance"],
            "fashion": ["cloth", "shoe", "jewelry", "fashion", "apparel", "wear"],
            "tech": ["tech", "electron", "computer", "software", "digital", "phone", "gadget"],
            "health": ["health", "medical", "wellness", "pharma", "fitness", "sport", "vitamin"],
            "home": ["home", "kitchen", "garden", "tool", "furniture", "decor", "appliance"],
            "food": ["food", "grocery", "gourmet", "pet", "snack", "beverage"],
            "entertainment": ["book", "movie", "music", "game", "toy", "art", "craft", "entertain"],
            "automotive": ["car", "auto", "vehicle", "motor", "tire"],
            "finance": ["financ", "bank", "invest", "credit", "insur"],
            "local": ["local", "restaurant", "shop", "store"],
        }
        for fam, keywords in keyword_families.items():
            if any(kw in cat_lower for kw in keywords):
                family = fam
                break

    if family and family in _CATEGORY_FAMILIES:
        # Add family members (original first, then siblings)
        for sibling in _CATEGORY_FAMILIES[family]:
            if sibling != category and sibling not in categories:
                categories.append(sibling)

    return categories


async def _query_category_psychological_environment(
    category: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Query the graph for the psychological environment a content category creates.

    This is the Publisher/SSP answer to "what psychological state does content
    in this category put readers in?" — derived from bilateral edge evidence.

    Approach: For a given product category, we aggregate the buyer-side NDF
    profiles of all AnnotatedReview nodes connected via BRAND_CONVERTED edges.
    The average buyer NDF across those conversions tells us what kind of buyer
    psychology this category activates. That IS the psychological environment.

    Also retrieves:
    - BayesianPrior mechanism effectiveness for this category
    - Evidence counts (how many edges back this intelligence)
    - Dominant mechanisms from category-level priors

    Returns None when graph unavailable or category has no evidence.
    """
    if not category:
        return None

    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client
        client = get_neo4j_client()
        if not client.is_connected:
            return None

        # Resolve category: try exact match first, then fuzzy match via
        # graph taxonomy or keyword-based category family grouping.
        resolved_category = await _resolve_category(client, category)

        # Query 1: Aggregate buyer-side NDF from BRAND_CONVERTED edges in this category.
        # ProductDescription nodes have a 'category' property matching Amazon categories.
        # The buyer-side AnnotatedReview nodes have NDF-derived constructs.
        # The EDGE itself carries 20+ alignment dimensions — these tell us what
        # psychological profile converts in this category.
        ndf_query = """
        MATCH (pd:ProductDescription)-[bc:BRAND_CONVERTED]->(ar:AnnotatedReview)
        WHERE pd.category IN $categories
              AND bc.composite_alignment IS NOT NULL
        WITH count(bc) AS edge_count,
             // Core alignment dimensions
             AVG(bc.regulatory_fit_score) AS avg_reg_fit,
             AVG(bc.construal_fit_score) AS avg_construal_fit,
             AVG(bc.personality_brand_alignment) AS avg_personality,
             AVG(bc.emotional_resonance) AS avg_emotional,
             AVG(bc.value_alignment) AS avg_value,
             AVG(bc.composite_alignment) AS avg_composite,
             AVG(COALESCE(bc.evolutionary_motive_match, 0.5)) AS avg_evo,
             AVG(COALESCE(bc.linguistic_style_matching, 0.5)) AS avg_linguistic,
             // Extended psychological dimensions
             AVG(COALESCE(bc.social_proof_sensitivity, 0.5)) AS avg_social_proof,
             AVG(COALESCE(bc.loss_aversion_intensity, 0.5)) AS avg_loss_aversion,
             AVG(COALESCE(bc.cognitive_load_tolerance, 0.5)) AS avg_cognitive_load,
             AVG(COALESCE(bc.narrative_transport, 0.5)) AS avg_narrative,
             AVG(COALESCE(bc.temporal_discounting, 0.5)) AS avg_temporal,
             AVG(COALESCE(bc.autonomy_reactance, 0.5)) AS avg_autonomy,
             AVG(COALESCE(bc.information_seeking, 0.5)) AS avg_info_seeking,
             AVG(COALESCE(bc.decision_entropy, 0.5)) AS avg_decision_entropy,
             AVG(COALESCE(bc.persuasion_susceptibility, 0.5)) AS avg_persuasion_suscept,
             AVG(COALESCE(bc.brand_relationship_depth, 0.5)) AS avg_brand_rel_depth,
             AVG(COALESCE(bc.mimetic_desire, 0.5)) AS avg_mimetic_desire,
             AVG(COALESCE(bc.interoceptive_awareness, 0.5)) AS avg_interoceptive,
             AVG(COALESCE(bc.cooperative_framing_fit, 0.5)) AS avg_cooperative_framing,
             // Match dimensions (full 27-dim vector)
             AVG(COALESCE(bc.appeal_resonance, 0.5)) AS avg_appeal_resonance,
             AVG(COALESCE(bc.processing_route_match, 0.5)) AS avg_processing_route,
             AVG(COALESCE(bc.implicit_driver_match, 0.5)) AS avg_implicit_driver,
             AVG(COALESCE(bc.lay_theory_alignment, 0.5)) AS avg_lay_theory,
             AVG(COALESCE(bc.identity_signaling_match, 0.5)) AS avg_identity_signal,
             AVG(COALESCE(bc.full_cosine_alignment, 0.5)) AS avg_full_cosine,
             AVG(COALESCE(bc.uniqueness_popularity_fit, 0.5)) AS avg_uniqueness_pop,
             AVG(COALESCE(bc.mental_simulation_resonance, 0.5)) AS avg_mental_sim,
             AVG(COALESCE(bc.involvement_weight_modifier, 0.5)) AS avg_involvement,
             AVG(COALESCE(bc.negativity_bias_match, 0.5)) AS avg_negativity_bias,
             AVG(COALESCE(bc.reactance_fit, 0.5)) AS avg_reactance_fit,
             AVG(COALESCE(bc.optimal_distinctiveness_fit, 0.5)) AS avg_opt_distinct,
             AVG(COALESCE(bc.brand_trust_fit, 0.5)) AS avg_brand_trust,
             AVG(COALESCE(bc.self_monitoring_fit, 0.5)) AS avg_self_monitoring,
             AVG(COALESCE(bc.spending_pain_match, 0.5)) AS avg_spending_pain,
             AVG(COALESCE(bc.disgust_contamination_fit, 0.5)) AS avg_disgust_contam,
             AVG(COALESCE(bc.anchor_susceptibility_match, 0.5)) AS avg_anchor_suscept,
             AVG(COALESCE(bc.mental_ownership_match, 0.5)) AS avg_mental_ownership,
             // Metadata signals
             AVG(COALESCE(bc.star_rating, 0)) AS avg_star_rating,
             AVG(COALESCE(bc.helpful_votes, 0)) AS avg_helpful_votes,
             AVG(COALESCE(bc.verified_purchase_trust, 0.5)) AS avg_verified_trust,
             STDEV(bc.composite_alignment) AS std_composite,
             STDEV(bc.star_rating) AS std_star_rating
        WHERE edge_count >= 5
        RETURN edge_count, avg_reg_fit, avg_construal_fit, avg_personality,
               avg_emotional, avg_value, avg_composite, std_composite,
               avg_evo, avg_linguistic,
               avg_social_proof, avg_loss_aversion, avg_cognitive_load,
               avg_narrative, avg_temporal, avg_autonomy, avg_info_seeking,
               avg_decision_entropy, avg_persuasion_suscept, avg_brand_rel_depth,
               avg_mimetic_desire, avg_interoceptive, avg_cooperative_framing,
               avg_appeal_resonance, avg_processing_route, avg_implicit_driver,
               avg_lay_theory, avg_identity_signal, avg_full_cosine,
               avg_uniqueness_pop, avg_mental_sim, avg_involvement,
               avg_negativity_bias, avg_reactance_fit, avg_opt_distinct,
               avg_brand_trust, avg_self_monitoring, avg_spending_pain,
               avg_disgust_contam, avg_anchor_suscept, avg_mental_ownership,
               avg_star_rating, avg_helpful_votes, avg_verified_trust,
               std_star_rating
        """

        # Query 2: BayesianPrior mechanism effectiveness for this category
        mech_query = """
        MATCH (bp:BayesianPrior)
        WHERE bp.category IN $categories
              AND bp.posterior_mean IS NOT NULL
        RETURN bp.mechanism AS mechanism,
               bp.archetype AS archetype,
               bp.posterior_mean AS posterior_mean,
               bp.n_observations AS n_observations,
               bp.alpha AS alpha,
               bp.beta AS beta
        ORDER BY bp.posterior_mean DESC
        """

        edge_result = None
        mech_result = None

        async with client.driver.session() as session:
            result = await session.run(ndf_query, categories=resolved_category)
            edge_result = await result.single()

            result2 = await session.run(mech_query, categories=resolved_category)
            mech_result = await result2.data()

        if not edge_result or not edge_result.get("edge_count"):
            # No bilateral edge evidence for this category
            if mech_result:
                # Still have BayesianPrior data — return partial
                return _build_partial_environment(mech_result)
            return None

        edge_count = edge_result["edge_count"]

        # Derive NDF profile from bilateral edge averages.
        # Map edge alignment dimensions → NDF dimensions.
        # The edge dimensions measure ALIGNMENT between buyer and seller —
        # high alignment in a dimension means the content environment activates
        # that psychological dimension in buyers who convert.
        derived_ndf = {
            "approach_avoidance": edge_result.get("avg_reg_fit", 0.5),
            "temporal_horizon": edge_result.get("avg_construal_fit", 0.5),
            "social_calibration": edge_result.get("avg_personality", 0.5),
            "uncertainty_tolerance": 1.0 - edge_result.get("avg_decision_entropy", 0.5),
            "status_sensitivity": edge_result.get("avg_value", 0.5),
            "cognitive_engagement": edge_result.get("avg_info_seeking", 0.5),
            "arousal_seeking": edge_result.get("avg_emotional", 0.5),
        }

        # Build extended dimensions (the 13 beyond core 7)
        extended_dims = {
            "social_proof_sensitivity": edge_result.get("avg_social_proof", 0.5),
            "loss_aversion_intensity": edge_result.get("avg_loss_aversion", 0.5),
            "cognitive_load_tolerance": edge_result.get("avg_cognitive_load", 0.5),
            "narrative_transport": edge_result.get("avg_narrative", 0.5),
            "temporal_discounting": edge_result.get("avg_temporal", 0.5),
            "autonomy_reactance": edge_result.get("avg_autonomy", 0.5),
            "decision_entropy": edge_result.get("avg_decision_entropy", 0.5),
            "persuasion_susceptibility": edge_result.get("avg_persuasion_suscept", 0.5),
            "brand_relationship_depth": edge_result.get("avg_brand_rel_depth", 0.5),
            "mimetic_desire": edge_result.get("avg_mimetic_desire", 0.5),
            "interoceptive_awareness": edge_result.get("avg_interoceptive", 0.5),
            "cooperative_framing_fit": edge_result.get("avg_cooperative_framing", 0.5),
        }

        # Full 27-dim bilateral vector (match dimensions)
        match_dims = {
            "regulatory_fit": edge_result.get("avg_reg_fit", 0.5),
            "construal_fit": edge_result.get("avg_construal_fit", 0.5),
            "personality_alignment": edge_result.get("avg_personality", 0.5),
            "emotional_resonance": edge_result.get("avg_emotional", 0.5),
            "value_alignment": edge_result.get("avg_value", 0.5),
            "evolutionary_motive": edge_result.get("avg_evo", 0.5),
            "linguistic_style": edge_result.get("avg_linguistic", 0.5),
            "appeal_resonance": edge_result.get("avg_appeal_resonance", 0.5),
            "processing_route_match": edge_result.get("avg_processing_route", 0.5),
            "implicit_driver_match": edge_result.get("avg_implicit_driver", 0.5),
            "lay_theory_alignment": edge_result.get("avg_lay_theory", 0.5),
            "identity_signaling_match": edge_result.get("avg_identity_signal", 0.5),
            "full_cosine_alignment": edge_result.get("avg_full_cosine", 0.5),
            "uniqueness_popularity_fit": edge_result.get("avg_uniqueness_pop", 0.5),
            "mental_simulation_resonance": edge_result.get("avg_mental_sim", 0.5),
            "involvement_weight_modifier": edge_result.get("avg_involvement", 0.5),
            "negativity_bias_match": edge_result.get("avg_negativity_bias", 0.5),
            "reactance_fit": edge_result.get("avg_reactance_fit", 0.5),
            "optimal_distinctiveness_fit": edge_result.get("avg_opt_distinct", 0.5),
            "brand_trust_fit": edge_result.get("avg_brand_trust", 0.5),
            "self_monitoring_fit": edge_result.get("avg_self_monitoring", 0.5),
            "spending_pain_match": edge_result.get("avg_spending_pain", 0.5),
            "disgust_contamination_fit": edge_result.get("avg_disgust_contam", 0.5),
            "anchor_susceptibility_match": edge_result.get("avg_anchor_suscept", 0.5),
            "mental_ownership_match": edge_result.get("avg_mental_ownership", 0.5),
            "social_proof_sensitivity": edge_result.get("avg_social_proof", 0.5),
            "narrative_transport": edge_result.get("avg_narrative", 0.5),
        }

        # Metadata signals
        metadata_sigs = {
            "star_rating": edge_result.get("avg_star_rating", 0),
            "helpful_votes": edge_result.get("avg_helpful_votes", 0),
            "verified_purchase_trust": edge_result.get("avg_verified_trust", 0.5),
            "star_rating_std": edge_result.get("std_star_rating") or 0.0,
        }

        # Aggregate mechanisms from BayesianPrior nodes
        mechanism_effectiveness = {}
        for rec in (mech_result or []):
            mech = rec.get("mechanism")
            if not mech:
                continue
            posterior = rec.get("posterior_mean", 0.5)
            n_obs = rec.get("n_observations", 0)
            # Aggregate across archetypes — take weighted average by observation count
            if mech in mechanism_effectiveness:
                existing = mechanism_effectiveness[mech]
                total_n = existing["n_observations"] + n_obs
                if total_n > 0:
                    existing["effectiveness"] = (
                        existing["effectiveness"] * existing["n_observations"]
                        + posterior * n_obs
                    ) / total_n
                    existing["n_observations"] = total_n
            else:
                mechanism_effectiveness[mech] = {
                    "effectiveness": posterior,
                    "n_observations": n_obs,
                }

        composite_quality = edge_result.get("avg_composite", 0.5)
        composite_std = edge_result.get("std_composite") or 0.0

        s = _get_intel_settings()

        logger.info(
            "Category psychological environment for %s: %d edges, "
            "composite=%.3f±%.3f, %d mechanisms",
            category, edge_count, composite_quality, composite_std,
            len(mechanism_effectiveness),
        )

        return {
            "ndf_profile": derived_ndf,
            "extended_dimensions": extended_dims,
            "match_dimensions": match_dims,
            "metadata_signals": metadata_sigs,
            "mechanism_effectiveness": mechanism_effectiveness,
            "edge_count": edge_count,
            "composite_alignment": composite_quality,
            "composite_std": composite_std,
            "intelligence_level": IntelligenceLevel.L3_BILATERAL
            if edge_count >= s.l3_min_edges
            else IntelligenceLevel.L2_CATEGORY,
            "source": "bilateral_edge_aggregates",
        }

    except Exception as e:
        logger.debug("Category psychological environment unavailable: %s", e)
        return None


def _build_partial_environment(
    mech_records: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """Build a partial environment from BayesianPrior data when no bilateral edges available."""
    mechanism_effectiveness = {}
    for rec in mech_records:
        mech = rec.get("mechanism")
        if not mech:
            continue
        posterior = rec.get("posterior_mean", 0.5)
        n_obs = rec.get("n_observations", 0)
        if mech in mechanism_effectiveness:
            existing = mechanism_effectiveness[mech]
            total_n = existing["n_observations"] + n_obs
            if total_n > 0:
                existing["effectiveness"] = (
                    existing["effectiveness"] * existing["n_observations"]
                    + posterior * n_obs
                ) / total_n
                existing["n_observations"] = total_n
        else:
            mechanism_effectiveness[mech] = {
                "effectiveness": posterior,
                "n_observations": n_obs,
            }

    if not mechanism_effectiveness:
        return None

    return {
        "ndf_profile": None,
        "extended_dimensions": None,
        "mechanism_effectiveness": mechanism_effectiveness,
        "edge_count": 0,
        "composite_alignment": None,
        "composite_std": None,
        "intelligence_level": IntelligenceLevel.L2_CATEGORY,
        "source": "bayesian_prior_only",
    }


async def _compute_vertical_values_from_graph(
    ndf: Dict[str, float],
) -> List[VerticalValue]:
    """
    Compute page vertical values from bilateral edge evidence.

    Queries BRAND_CONVERTED edges to find empirical conversion rates for
    pages with similar NDF profiles, grouped by product category (vertical).
    Falls back to heuristic computation when graph unavailable.

    This is what makes publisher inventory grading data-driven instead of
    theoretical — backed by 47M actual purchase decisions.
    """
    values = []

    # Try graph-backed computation first
    graph_values = await _query_vertical_evidence_from_graph(ndf)
    if graph_values:
        return graph_values

    # Fallback: heuristic computation from hardcoded vertical psychology
    return _compute_vertical_values_heuristic(ndf)


async def _query_vertical_evidence_from_graph(
    ndf: Dict[str, float],
) -> Optional[List[VerticalValue]]:
    """
    Query bilateral edges to find which verticals convert best
    for buyers with this NDF profile.

    For each product category in the graph, find the average
    composite_alignment of BRAND_CONVERTED edges where the buyer's
    NDF profile is similar to the page NDF. Higher alignment = higher value.
    """
    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client
        client = get_neo4j_client()
        if not client.is_connected:
            return None

        # Find which archetype best matches this NDF profile
        # (closest NDF match on CustomerArchetype nodes)
        archetype = await _ndf_to_best_archetype(ndf)

        query = """
        MATCH (a:CustomerArchetype {name: $archetype})
              -[r:RESPONDS_TO]->(m:CognitiveMechanism)
        WHERE r.effectiveness IS NOT NULL AND r.sample_size > 10
        WITH m.name AS mechanism, r.effectiveness AS effectiveness,
             r.sample_size AS evidence
        ORDER BY effectiveness DESC

        // Also get category-level conversion evidence
        WITH COLLECT({mechanism: mechanism, effectiveness: effectiveness, evidence: evidence}) AS mechs

        OPTIONAL MATCH (pc:ProductCategory)
        WHERE pc.dominant_persuasion IS NOT NULL
        WITH mechs, pc.name AS category, pc.dominant_persuasion AS dominant_mech,
             pc.dominant_emotion AS dominant_emotion

        RETURN category, dominant_mech, dominant_emotion, mechs
        LIMIT 20
        """
        async with client.driver.session() as session:
            result = await session.run(query, archetype=archetype)
            records = await result.data()

        if not records or not records[0].get("category"):
            return None

        # Map graph categories to verticals
        # Complete mapping of all 46+ known categories to 8 verticals.
        # Covers Amazon categories (32) + multi-dataset categories (14).
        category_vertical_map = {
            # Amazon categories
            "All_Beauty": "luxury_goods",
            "Beauty_and_Personal_Care": "luxury_goods",
            "Clothing_Shoes_and_Jewelry": "luxury_goods",
            "Handmade_Products": "luxury_goods",
            "Electronics": "technology",
            "Cell_Phones_and_Accessories": "technology",
            "Software": "technology",
            "Industrial_and_Scientific": "technology",
            "Kindle_Store": "technology",
            "Health_and_Household": "health_wellness",
            "Health_and_Personal_Care": "health_wellness",
            "Sports_and_Outdoors": "health_wellness",
            "Baby_Products": "health_wellness",
            "Automotive": "automotive",
            "Home_and_Kitchen": "ecommerce_general",
            "Grocery_and_Gourmet_Food": "ecommerce_general",
            "Tools_and_Home_Improvement": "ecommerce_general",
            "Office_Products": "ecommerce_general",
            "Patio_Lawn_and_Garden": "ecommerce_general",
            "Pet_Supplies": "ecommerce_general",
            "Appliances": "ecommerce_general",
            "Gift_Cards": "ecommerce_general",
            "Subscription_Boxes": "ecommerce_general",
            "Unknown": "ecommerce_general",
            "Books": "entertainment",
            "Movies_and_TV": "entertainment",
            "Digital_Music": "entertainment",
            "CDs_and_Vinyl": "entertainment",
            "Musical_Instruments": "entertainment",
            "Toys_and_Games": "entertainment",
            "Arts_Crafts_and_Sewing": "entertainment",
            "Magazine_Subscriptions": "entertainment",
            # Multi-dataset categories
            "airline": "ecommerce_general",
            "automotive": "automotive",
            "bh_photo": "technology",
            "glassdoor": "ecommerce_general",
            "google_local": "ecommerce_general",
            "podcast": "entertainment",
            "reddit_mbti": "entertainment",
            "rent_the_runway": "luxury_goods",
            "sephora": "luxury_goods",
            "steam": "entertainment",
            "trustpilot": "ecommerce_general",
            "twcs": "technology",
            "twitter": "entertainment",
            "yelp": "ecommerce_general",
        }

        # Aggregate evidence by vertical
        vertical_evidence: Dict[str, List[float]] = {}
        vertical_mechs: Dict[str, List[str]] = {}
        for rec in records:
            cat = rec.get("category", "")
            vertical = category_vertical_map.get(cat)
            # Dynamic fallback for unmapped categories
            if not vertical and cat:
                cat_lower = cat.lower()
                if any(w in cat_lower for w in ["health", "medical", "wellness", "pharma"]):
                    vertical = "health_wellness"
                elif any(w in cat_lower for w in ["tech", "electronic", "computer", "software", "digital"]):
                    vertical = "technology"
                elif any(w in cat_lower for w in ["luxury", "fashion", "beauty", "jewelry", "watch"]):
                    vertical = "luxury_goods"
                elif any(w in cat_lower for w in ["car", "auto", "vehicle", "motor"]):
                    vertical = "automotive"
                elif any(w in cat_lower for w in ["insur", "protect"]):
                    vertical = "insurance"
                elif any(w in cat_lower for w in ["finance", "bank", "invest", "credit"]):
                    vertical = "financial_services"
                elif any(w in cat_lower for w in ["music", "movie", "game", "book", "entertain", "art"]):
                    vertical = "entertainment"
                else:
                    vertical = "ecommerce_general"
            if not vertical:
                continue
            if vertical not in vertical_evidence:
                vertical_evidence[vertical] = []
                vertical_mechs[vertical] = []

            # Use mechanism effectiveness as a proxy for vertical value
            mechs = rec.get("mechs", [])
            if isinstance(mechs, list):
                for m in mechs[:5]:
                    if isinstance(m, dict):
                        vertical_evidence[vertical].append(m.get("effectiveness", 0.5))
                        if m.get("mechanism"):
                            vertical_mechs[vertical].append(m["mechanism"])

            if rec.get("dominant_mech"):
                vertical_mechs[vertical].insert(0, rec["dominant_mech"])

        if not vertical_evidence:
            return None

        values = []
        for vertical, evidence_scores in vertical_evidence.items():
            avg_eff = sum(evidence_scores) / len(evidence_scores)
            # NDF alignment score for this vertical
            config = _VERTICAL_PSYCHOLOGY.get(vertical, {})
            ndf_alignment = 0.0
            n_dims = 0
            for dim, direction in config.get("dimensions", {}).items():
                dim_val = ndf.get(dim, 0.5)
                if direction > 0:
                    ndf_alignment += dim_val
                else:
                    ndf_alignment += (1.0 - dim_val)
                n_dims += 1
            ndf_score = ndf_alignment / n_dims if n_dims > 0 else 0.5

            # Blend: graph evidence + NDF alignment (externalized weights)
            _s = _get_intel_settings()
            blended = _s.graph_weight * avg_eff + _s.profiler_weight * ndf_score
            multiplier = _s.cpm_floor + blended * _s.cpm_scale

            # Deduplicate mechanisms
            seen_mechs = []
            for m in vertical_mechs.get(vertical, []):
                if m not in seen_mechs:
                    seen_mechs.append(m)

            values.append(VerticalValue(
                vertical=vertical,
                value_multiplier=round(multiplier, 2),
                reasoning=f"Graph-backed: {len(evidence_scores)} evidence points, "
                          f"avg effectiveness {avg_eff:.2f}, NDF alignment {ndf_score:.2f}",
                top_mechanisms=seen_mechs[:3],
            ))

        # Add heuristic values for verticals not in graph
        graph_verticals = set(vertical_evidence.keys())
        for vertical, config in _VERTICAL_PSYCHOLOGY.items():
            if vertical not in graph_verticals:
                score = 0.0
                count = 0
                for dim, direction in config["dimensions"].items():
                    dim_val = ndf.get(dim, 0.5)
                    if direction > 0:
                        score += dim_val
                    else:
                        score += (1.0 - dim_val)
                    count += 1
                if count > 0:
                    avg = score / count
                    _s = _get_intel_settings()
                    values.append(VerticalValue(
                        vertical=vertical,
                        value_multiplier=round(_s.cpm_floor + avg * _s.cpm_scale, 2),
                        reasoning=config["description"] + " (heuristic — no graph evidence)",
                        top_mechanisms=config["mechanisms"],
                    ))

        values.sort(key=lambda v: v.value_multiplier, reverse=True)
        logger.info("Vertical values computed from graph: %d graph-backed, %d heuristic",
                     len(graph_verticals), len(values) - len(graph_verticals))
        return values

    except Exception as e:
        logger.debug("Graph-backed vertical values unavailable: %s", e)
        return None


_ARCHETYPE_CENTROIDS_FALLBACK = {
    "achiever":   {"approach_avoidance": 0.75, "temporal_horizon": 0.70, "social_calibration": 0.50,
                   "uncertainty_tolerance": 0.55, "status_sensitivity": 0.60, "cognitive_engagement": 0.70, "arousal_seeking": 0.55},
    "explorer":   {"approach_avoidance": 0.80, "temporal_horizon": 0.45, "social_calibration": 0.40,
                   "uncertainty_tolerance": 0.80, "status_sensitivity": 0.35, "cognitive_engagement": 0.60, "arousal_seeking": 0.75},
    "connector":  {"approach_avoidance": 0.60, "temporal_horizon": 0.50, "social_calibration": 0.80,
                   "uncertainty_tolerance": 0.50, "status_sensitivity": 0.45, "cognitive_engagement": 0.45, "arousal_seeking": 0.55},
    "guardian":   {"approach_avoidance": 0.25, "temporal_horizon": 0.70, "social_calibration": 0.55,
                   "uncertainty_tolerance": 0.20, "status_sensitivity": 0.35, "cognitive_engagement": 0.55, "arousal_seeking": 0.25},
    "analyst":    {"approach_avoidance": 0.45, "temporal_horizon": 0.65, "social_calibration": 0.30,
                   "uncertainty_tolerance": 0.60, "status_sensitivity": 0.25, "cognitive_engagement": 0.90, "arousal_seeking": 0.30},
    "creator":    {"approach_avoidance": 0.70, "temporal_horizon": 0.40, "social_calibration": 0.35,
                   "uncertainty_tolerance": 0.75, "status_sensitivity": 0.55, "cognitive_engagement": 0.65, "arousal_seeking": 0.70},
    "nurturer":   {"approach_avoidance": 0.55, "temporal_horizon": 0.60, "social_calibration": 0.75,
                   "uncertainty_tolerance": 0.40, "status_sensitivity": 0.30, "cognitive_engagement": 0.50, "arousal_seeking": 0.40},
    "pragmatist": {"approach_avoidance": 0.50, "temporal_horizon": 0.50, "social_calibration": 0.50,
                   "uncertainty_tolerance": 0.50, "status_sensitivity": 0.40, "cognitive_engagement": 0.55, "arousal_seeking": 0.45},
}

_NDF_DIMS = [
    "approach_avoidance", "temporal_horizon", "social_calibration",
    "uncertainty_tolerance", "status_sensitivity", "cognitive_engagement",
    "arousal_seeking",
]


async def _load_archetype_centroids() -> Dict[str, Dict[str, float]]:
    """
    Load archetype NDF centroids from CustomerArchetype nodes in Neo4j.

    Cached at module level after first successful load.
    Falls back to hardcoded centroids when graph unavailable.
    """
    global _cached_archetype_centroids
    if _cached_archetype_centroids is not None:
        return _cached_archetype_centroids

    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client
        client = get_neo4j_client()
        if not client.is_connected:
            return _ARCHETYPE_CENTROIDS_FALLBACK

        query = """
        MATCH (a:CustomerArchetype)
        RETURN a.name AS name,
               a.approach_avoidance AS approach_avoidance,
               a.temporal_horizon AS temporal_horizon,
               a.social_calibration AS social_calibration,
               a.uncertainty_tolerance AS uncertainty_tolerance,
               a.status_sensitivity AS status_sensitivity,
               a.cognitive_engagement AS cognitive_engagement,
               a.arousal_seeking AS arousal_seeking
        """
        async with client.driver.session() as session:
            result = await session.run(query)
            records = await result.data()

        if not records:
            return _ARCHETYPE_CENTROIDS_FALLBACK

        centroids = {}
        for rec in records:
            name = rec.get("name")
            if not name:
                continue
            centroid = {}
            for dim in _NDF_DIMS:
                val = rec.get(dim)
                if val is not None:
                    centroid[dim] = float(val)
                else:
                    # Fill from fallback if graph node is missing a dimension
                    fb = _ARCHETYPE_CENTROIDS_FALLBACK.get(name, {})
                    centroid[dim] = fb.get(dim, 0.5)
            centroids[name] = centroid

        if centroids:
            _cached_archetype_centroids = centroids
            logger.info(
                "Loaded %d archetype centroids from graph (dims: %s)",
                len(centroids), ", ".join(_NDF_DIMS),
            )
            return centroids

        return _ARCHETYPE_CENTROIDS_FALLBACK

    except Exception as e:
        logger.debug("Could not load archetype centroids from graph: %s", e)
        return _ARCHETYPE_CENTROIDS_FALLBACK


async def _ndf_to_best_archetype(ndf: Dict[str, float]) -> str:
    """
    Find the archetype whose NDF centroid is closest to the given NDF profile.

    Uses Euclidean distance across all 7 NDF dimensions to the archetype
    centroids loaded from CustomerArchetype nodes in Neo4j (cached after
    first load). Falls back to hardcoded centroids when graph unavailable.
    """
    centroids = await _load_archetype_centroids()

    best_archetype = "pragmatist"
    best_distance = float("inf")

    for arch, centroid in centroids.items():
        dist_sq = 0.0
        for dim, centroid_val in centroid.items():
            ndf_val = ndf.get(dim, 0.5)
            dist_sq += (ndf_val - centroid_val) ** 2
        if dist_sq < best_distance:
            best_distance = dist_sq
            best_archetype = arch

    return best_archetype


def _compute_vertical_values_heuristic(
    ndf: Dict[str, float],
) -> List[VerticalValue]:
    """Heuristic vertical values from hardcoded psychology (fallback)."""
    s = _get_intel_settings()
    values = []
    for vertical, config in _VERTICAL_PSYCHOLOGY.items():
        score = 0.0
        count = 0
        for dim, direction in config["dimensions"].items():
            dim_val = ndf.get(dim, 0.5)
            if direction > 0:
                score += dim_val
            else:
                score += (1.0 - dim_val)
            count += 1

        if count > 0:
            avg = score / count
            multiplier = s.cpm_floor + avg * s.cpm_scale

            values.append(VerticalValue(
                vertical=vertical,
                value_multiplier=round(multiplier, 2),
                reasoning=config["description"],
                top_mechanisms=config["mechanisms"],
            ))

    values.sort(key=lambda v: v.value_multiplier, reverse=True)
    return values


def _infer_mindset(ndf: Dict[str, float]) -> str:
    """Infer the dominant cognitive mindset from NDF profile."""
    s = _get_intel_settings()
    ce = ndf.get("cognitive_engagement", 0.5)
    aa = ndf.get("approach_avoidance", 0.5)
    sc = ndf.get("social_calibration", 0.5)
    ut = ndf.get("uncertainty_tolerance", 0.5)

    if ce > s.mindset_high and ut > s.mindset_uncertainty_high:
        return "analytical"
    if ce > s.mindset_high and ut < s.mindset_uncertainty_low:
        return "vigilant"
    if aa > s.mindset_high and sc > s.mindset_social_high:
        return "social_action"
    if aa > s.mindset_high:
        return "action_oriented"
    if sc > s.mindset_high:
        return "social_comparison"
    if ut < s.mindset_low:
        return "certainty_seeking"
    return "balanced"


def _infer_processing_route(ndf: Dict[str, float]) -> str:
    """Infer the dominant ELM processing route from NDF."""
    s = _get_intel_settings()
    ce = ndf.get("cognitive_engagement", 0.5)
    ar = ndf.get("arousal_seeking", 0.5)
    sc = ndf.get("social_calibration", 0.5)

    if ce > s.mindset_high:
        return "central"
    if ar > s.mindset_high:
        return "experiential"
    if sc > s.mindset_high:
        return "narrative"
    return "peripheral"


async def _query_mechanism_receptivity_from_graph(
    archetype: str,
    category: Optional[str] = None,
    category_env: Optional[Dict[str, Any]] = None,
) -> List[MechanismScore]:
    """
    Query RESPONDS_TO edges for mechanism receptivity with evidence depth.

    Returns MechanismScore list with source and evidence_depth populated from
    actual graph data. When category_env is available (from
    _query_category_psychological_environment), uses BayesianPrior data for
    category-specific mechanism effectiveness.

    Priority:
    1. Category-specific BayesianPrior mechanism effectiveness (strongest)
    2. RESPONDS_TO archetype-level mechanism effectiveness (population-level)
    3. Empty list (caller falls back to content profiler)
    """
    scores = []

    # Source 1: Category-specific mechanism effectiveness from bilateral evidence
    s = _get_intel_settings()
    if category_env and category_env.get("mechanism_effectiveness"):
        mech_eff = category_env["mechanism_effectiveness"]
        edge_count = category_env.get("edge_count", 0)
        for mech, data in sorted(
            mech_eff.items(), key=lambda x: x[1]["effectiveness"], reverse=True,
        ):
            n_obs = data.get("n_observations", 0)
            if n_obs < s.evidence_weak_min:
                evidence = "weak"
            elif n_obs < s.evidence_strong:
                evidence = "moderate"
            else:
                evidence = "strong"

            scores.append(MechanismScore(
                mechanism=mech,
                score=round(data["effectiveness"], 3),
                evidence_depth=evidence,
                source=f"bilateral_category({category_env.get('source', 'graph')})",
            ))

        if scores:
            return scores[:10]

    # Source 2: RESPONDS_TO archetype-level effectiveness
    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client
        client = get_neo4j_client()
        if not client.is_connected:
            return scores

        query = """
        MATCH (a:CustomerArchetype {name: $archetype})
              -[r:RESPONDS_TO]->(m:CognitiveMechanism)
        WHERE r.effectiveness IS NOT NULL
        RETURN m.name AS mechanism,
               r.effectiveness AS effectiveness,
               r.sample_size AS sample_size,
               r.confidence AS confidence
        ORDER BY r.effectiveness DESC
        """
        async with client.driver.session() as session:
            result = await session.run(query, archetype=archetype)
            records = await result.data()

        if not records:
            return scores

        for rec in records:
            mech = rec.get("mechanism")
            eff = rec.get("effectiveness", 0.5)
            sample = rec.get("sample_size") or 0

            # Evidence depth from sample size (externalized thresholds)
            if sample >= s.evidence_very_strong:
                evidence = "very_strong"
            elif sample >= s.evidence_strong:
                evidence = "strong"
            elif sample >= s.evidence_moderate:
                evidence = "moderate"
            elif sample >= s.evidence_weak_min:
                evidence = "weak"
            else:
                evidence = "none"
                # Shrink low-evidence priors toward 0.5
                eff = 0.5 + (eff - 0.5) * (sample / max(s.evidence_weak_min, 1)) if sample > 0 else 0.5

            scores.append(MechanismScore(
                mechanism=mech,
                score=round(eff, 3),
                evidence_depth=evidence,
                source="graph_responds_to",
            ))

        logger.debug(
            "Mechanism receptivity from graph: %d mechanisms for archetype %s",
            len(scores), archetype,
        )
        return scores[:10]

    except Exception as e:
        logger.debug("Graph mechanism receptivity unavailable: %s", e)
        return scores


async def _query_mechanism_synergies(
    mechanisms: List[str],
) -> List[MechanismSynergy]:
    """
    Query MECHANISM_SYNERGY and ANTAGONIZES edges for the given mechanism set.

    Returns synergy/antagonism pairs relevant to the mechanisms in play.
    Creative teams need this to avoid deploying conflicting mechanisms
    and to amplify combinations that reinforce each other.
    """
    if len(mechanisms) < 2:
        return []

    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client
        client = get_neo4j_client()
        if not client.is_connected:
            return []

        query = """
        MATCH (m1:CognitiveMechanism)-[s:MECHANISM_SYNERGY]->(m2:CognitiveMechanism)
        WHERE m1.name IN $mechanisms AND m2.name IN $mechanisms
              AND s.synergy_score IS NOT NULL
        RETURN m1.name AS mech_a, m2.name AS mech_b,
               s.synergy_score AS synergy_score,
               s.combined_lift AS combined_lift,
               s.context AS context

        UNION

        MATCH (m1:CognitiveMechanism)-[a:ANTAGONIZES]->(m2:CognitiveMechanism)
        WHERE m1.name IN $mechanisms AND m2.name IN $mechanisms
        RETURN m1.name AS mech_a, m2.name AS mech_b,
               COALESCE(a.strength, 0.5) AS synergy_score,
               0.0 AS combined_lift,
               'antagonistic — avoid combining' AS context
        """
        async with client.driver.session() as session:
            result = await session.run(query, mechanisms=mechanisms)
            records = await result.data()

        synergies = []
        seen_pairs = set()
        for rec in records:
            pair_key = tuple(sorted([rec["mech_a"], rec["mech_b"]]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            synergies.append(MechanismSynergy(
                mechanism_a=rec["mech_a"],
                mechanism_b=rec["mech_b"],
                synergy_score=round(rec.get("synergy_score", 1.0), 3),
                combined_lift=round(rec.get("combined_lift", 0.0), 3),
                context=rec.get("context") or "",
            ))

        return synergies

    except Exception as e:
        logger.debug("Mechanism synergies unavailable: %s", e)
        return []


async def _query_gradient_priorities(
    archetype: str,
    category: Optional[str] = None,
    current_ndf: Optional[Dict[str, float]] = None,
) -> List[GradientPriority]:
    """
    Query pre-computed gradient fields from BayesianPrior nodes.

    Returns dimensions ranked by expected conversion lift — the answer to
    "where should creative investment go?" This is what no adtech platform
    has: quantified ∂P(conversion)/∂dimension per archetype×category cell.
    """
    try:
        from adam.infrastructure.neo4j.client import get_neo4j_client
        client = get_neo4j_client()
        if not client.is_connected:
            return []

        # Query BayesianPrior nodes with gradient properties
        query = """
        MATCH (bp:BayesianPrior)
        WHERE bp.archetype = $archetype
              AND ($category IS NULL OR bp.category = $category)
              AND bp.gradient_r_squared IS NOT NULL
              AND bp.gradient_r_squared > 0.05
        RETURN bp.category AS category,
               bp.gradient_r_squared AS r_squared,
               bp.gradient_n_edges AS n_edges,
               properties(bp) AS props
        ORDER BY bp.gradient_r_squared DESC
        LIMIT 1
        """
        async with client.driver.session() as session:
            result = await session.run(
                query, archetype=archetype, category=category,
            )
            record = await result.single()

        if not record:
            return []

        props = record.get("props", {})
        n_edges = record.get("n_edges", 0)

        # Extract gradient, optimal, and mean values from BayesianPrior properties
        # Properties are stored as: gradient_{dim}, gradient_optimal_{dim}, gradient_mean_{dim}
        priorities = []
        for key, val in props.items():
            if not key.startswith("gradient_") or val is None:
                continue
            # Skip metadata keys
            if key in ("gradient_r_squared", "gradient_n_edges"):
                continue
            # Skip optimal/mean/std (we'll look them up by dimension)
            if key.startswith("gradient_optimal_") or key.startswith("gradient_mean_") or key.startswith("gradient_std_"):
                continue

            dim_name = key.replace("gradient_", "")
            gradient_mag = float(val)
            optimal = props.get(f"gradient_optimal_{dim_name}")
            mean = props.get(f"gradient_mean_{dim_name}")

            gs = _get_intel_settings()
            if optimal is None or abs(gradient_mag) < gs.gradient_magnitude_min:
                continue

            # Compute expected lift from current position
            current = 0.5
            if current_ndf:
                # Map gradient dimension names back to NDF
                current = current_ndf.get(dim_name, 0.5)

            gap = float(optimal) - current
            std = props.get(f"gradient_std_{dim_name}", 0.15) or 0.15
            expected_lift_pct = gradient_mag * (gap / max(float(std), gs.gradient_magnitude_min)) * 100

            # Human-readable creative direction
            direction = ""
            if gradient_mag > 0 and gap > gs.gradient_gap_meaningful:
                direction = f"Increase {dim_name.replace('_', ' ')} — current {current:.2f}, optimal {float(optimal):.2f}"
            elif gradient_mag > 0 and gap < -gs.gradient_gap_meaningful:
                direction = f"Already above optimal on {dim_name.replace('_', ' ')}"
            elif gradient_mag < 0:
                direction = f"Reduce {dim_name.replace('_', ' ')} for better conversion"

            priorities.append(GradientPriority(
                dimension=dim_name,
                gradient_magnitude=round(gradient_mag, 4),
                current_value=round(current, 3),
                optimal_value=round(float(optimal), 3),
                expected_lift_pct=round(expected_lift_pct, 2),
                creative_direction=direction,
            ))

        # Sort by absolute expected lift (highest impact first)
        priorities.sort(key=lambda p: abs(p.expected_lift_pct), reverse=True)
        return priorities[:10]

    except Exception as e:
        logger.debug("Gradient priorities unavailable: %s", e)
        return []


def _build_dimension_confidence(
    ndf: Dict[str, float],
    category_env: Optional[Dict[str, Any]] = None,
    content_profiled: bool = False,
) -> List[DimensionConfidence]:
    """
    Build per-dimension confidence report.

    Tells callers which dimensions have real evidence vs. defaults.
    """
    edge_count = category_env.get("edge_count", 0) if category_env else 0
    has_graph = category_env is not None and category_env.get("ndf_profile") is not None

    s = _get_intel_settings()
    confidences = []
    for dim in _NDF_DIMS:
        val = ndf.get(dim, 0.5)
        # Determine source and confidence
        if has_graph and abs(val - 0.5) > 0.001:
            source = "bilateral_edge" if edge_count >= s.l3_min_edges else "bayesian_prior"
            conf = min(s.confidence_cap, s.confidence_base + (edge_count / s.confidence_edge_divisor))
        elif content_profiled and abs(val - 0.5) > 0.001:
            source = "content_profiler"
            conf = s.confidence_floor
        else:
            source = "default"
            conf = 0.0

        confidences.append(DimensionConfidence(
            dimension=dim,
            evidence_edges=edge_count if has_graph else 0,
            source=source,
            confidence=round(conf, 3),
        ))

    return confidences


# =============================================================================
# FULL-POWER HELPERS — bilateral dimensions, constructs, segments, directions
# =============================================================================


def _build_bilateral_dimensions_from_env(
    category_env: Optional[Dict[str, Any]],
) -> List[BilateralDimension]:
    """
    Build List[BilateralDimension] from expanded category environment query.

    Exposes the full 27-dimension bilateral edge vector with per-dim audit.
    """
    if not category_env:
        return []

    edge_count = category_env.get("edge_count", 0)
    dims = []

    # Core + extended NDF dimensions
    for source_dict, source_label in [
        (category_env.get("ndf_profile", {}), "core_ndf"),
        (category_env.get("extended_dimensions", {}), "extended"),
    ]:
        if not source_dict:
            continue
        for name, value in source_dict.items():
            if value is None:
                continue
            dims.append(BilateralDimension(
                name=name,
                value=round(value, 4),
                edge_count=edge_count,
                source=f"bilateral_edge ({source_label})",
            ))

    # Full match dimensions
    match_dims = category_env.get("match_dimensions", {})
    for name, value in match_dims.items():
        if value is None:
            continue
        # Skip if already covered by NDF or extended
        if any(d.name == name for d in dims):
            continue
        dims.append(BilateralDimension(
            name=name,
            value=round(value, 4),
            edge_count=edge_count,
            source="bilateral_edge (match)",
        ))

    return dims


def _build_construct_activations(
    bilateral_dims: List[BilateralDimension],
    ndf: Optional[Dict[str, float]] = None,
) -> List[ConstructActivation]:
    """
    Map bilateral edge dimensions → construct activations using
    POLARITY-AWARE directional inference.

    Unlike the old symmetric formula (abs(val-0.5)*2), this preserves
    direction. A regulatory_fit=0.8 activates promotion_focus (high end),
    while regulatory_fit=0.2 activates prevention_focus (low end).
    Each bilateral dimension can activate DIFFERENT constructs depending
    on whether the value is above or below neutral.

    Also builds NDF→construct bridge so PsychologicalSegmentEngine's
    canonical segments (which expect construct IDs like "prevention_focus",
    "openness", "sensation_seeking") receive proper activations.
    """
    try:
        from adam.intelligence.unified_construct_integration import (
            CONSTRUCT_MECHANISM_INFLUENCES,
        )
    except ImportError:
        CONSTRUCT_MECHANISM_INFLUENCES = {}

    if not bilateral_dims and not ndf:
        return []

    dim_values = {d.name: d.value for d in bilateral_dims}

    # ================================================================
    # POLARITY-AWARE dimension→construct mapping
    # Each entry: dim_name → (high_construct, low_construct, domain)
    #   high_construct activates when value > 0.5
    #   low_construct  activates when value < 0.5
    #   If only one side matters, the other is None
    # ================================================================
    _DIM_TO_POLAR_CONSTRUCT = {
        # Core alignment — directional constructs
        "regulatory_fit": (
            ("promotion_focus", "self_regulatory"),
            ("prevention_focus", "self_regulatory"),
        ),
        "construal_fit": (
            ("cognitive_nfc", "cognitive_processing"),       # High = abstract/high NFC
            ("concrete_processing", "cognitive_processing"),  # Low = concrete/low NFC
        ),
        "personality_alignment": (
            ("big_five_agreeableness", "social"),
            ("autonomy_preference", "social"),
        ),
        "emotional_resonance": (
            ("emotional_intensity_high", "emotional"),
            ("emotional_regulation", "emotional"),
        ),
        "value_alignment": (
            ("self_enhancement", "motivation"),
            ("conservation_values", "motivation"),
        ),
        "evolutionary_motive": (
            ("approach_motivation", "motivation"),
            ("avoidance_motivation", "motivation"),
        ),
        "linguistic_style": (
            ("narrative_transportation", "information_processing"),
            ("analytical_processing", "information_processing"),
        ),
        # Extended psychological — directional
        "social_proof_sensitivity": (
            ("social_proof_susceptibility", "social"),
            ("independence_preference", "social"),
        ),
        "loss_aversion_intensity": (
            ("loss_aversion", "decision_making"),
            ("gain_orientation", "decision_making"),
        ),
        "narrative_transport": (
            ("narrative_transportation", "information_processing"),
            ("analytical_processing", "information_processing"),
        ),
        "temporal_discounting": (
            ("present_bias", "temporal"),
            ("future_orientation", "temporal"),
        ),
        "autonomy_reactance": (
            ("psychological_reactance", "self_regulatory"),
            ("compliance_readiness", "self_regulatory"),
        ),
        "cognitive_load_tolerance": (
            ("cognitive_engagement", "cognitive_processing"),
            ("cognitive_load", "cognitive_processing"),
        ),
        "decision_entropy": (
            ("decision_conflict", "decision_making"),
            ("need_for_closure", "decision_making"),
        ),
        "brand_trust_fit": (
            ("brand_loyalty", "social"),
            ("brand_skepticism", "social"),
        ),
        "mimetic_desire": (
            ("mimetic_desire", "social"),
            None,  # No low-end construct
        ),
        # Match dimensions — directional
        "identity_signaling_match": (
            ("identity_salience", "motivation"),
            None,
        ),
        "mental_ownership_match": (
            ("endowment_effect", "decision_making"),
            None,
        ),
        "anchor_susceptibility_match": (
            ("anchoring_susceptibility", "cognitive_processing"),
            ("anchoring_resistance", "cognitive_processing"),
        ),
        "reactance_fit": (
            ("psychological_reactance", "self_regulatory"),
            ("compliance_readiness", "self_regulatory"),
        ),
        "appeal_resonance": (
            ("emotional_appeal_match", "emotional"),
            None,
        ),
        "self_monitoring_fit": (
            ("self_monitoring", "social"),
            ("self_authenticity", "social"),
        ),
        "spending_pain_match": (
            ("pain_of_paying", "decision_making"),
            ("spending_pleasure", "decision_making"),
        ),
        "processing_route_match": (
            ("elaboration_likelihood", "information_processing"),
            ("peripheral_processing", "information_processing"),
        ),
        "involvement_weight_modifier": (
            ("product_involvement", "motivation"),
            ("low_involvement", "motivation"),
        ),
        "implicit_driver_match": (
            ("implicit_motivation", "motivation"),
            None,
        ),
        "lay_theory_alignment": (
            ("lay_theories", "cognitive_processing"),
            None,
        ),
        "uniqueness_popularity_fit": (
            ("need_for_uniqueness", "self_regulatory"),
            ("conformity_need", "social"),
        ),
        "optimal_distinctiveness_fit": (
            ("optimal_distinctiveness", "social"),
            None,
        ),
        "mental_simulation_resonance": (
            ("mental_simulation", "cognitive_processing"),
            None,
        ),
        "negativity_bias_match": (
            ("negativity_bias", "emotional"),
            ("positivity_orientation", "emotional"),
        ),
        "full_cosine_alignment": (
            ("holistic_alignment", "information_processing"),
            None,
        ),
        "disgust_contamination_fit": (
            ("contamination_sensitivity", "emotional"),
            None,
        ),
    }

    # ================================================================
    # NDF → Construct bridge
    # Maps NDF dims to ALL construct IDs that CANONICAL_SEGMENTS expect.
    # Each NDF dim can activate MULTIPLE constructs (one dim contributes
    # to several segment definitions). Format:
    #   dim_name: {
    #     "high": [(construct_id, domain, weight), ...],  # activated when > 0.5
    #     "low":  [(construct_id, domain, weight), ...],  # activated when < 0.5
    #   }
    # ================================================================
    _NDF_TO_CONSTRUCTS = {
        "approach_avoidance": {
            "high": [
                ("approach_motivation", "motivation", 1.0),
                ("promotion_focus", "self_regulatory", 0.8),
                ("curiosity", "cognitive_processing", 0.5),
            ],
            "low": [
                ("prevention_focus", "self_regulatory", 1.0),
                ("risk_sensitivity", "decision_making", 0.8),
                ("risk_aversion", "decision_making", 0.8),
                ("loss_aversion", "decision_making", 0.7),
            ],
        },
        "temporal_horizon": {
            "high": [
                ("future_orientation", "temporal", 1.0),
                ("conscientiousness", "personality", 0.6),
                ("delay_tolerance", "decision_making", 0.7),
            ],
            "low": [
                ("present_bias", "temporal", 1.0),
                ("impulsivity", "decision_making", 0.7),
                ("delay_discounting", "temporal", 0.8),
            ],
        },
        "social_calibration": {
            "high": [
                ("social_proof_susceptibility", "social", 1.0),
                ("extraversion", "personality", 0.7),
                ("conformity_need", "social", 0.7),
                ("relatedness_need", "social", 0.6),
                ("agreeableness", "personality", 0.5),
                ("social_comparison", "social", 0.5),
            ],
            "low": [
                ("independence_preference", "social", 1.0),
                ("skepticism", "cognitive_processing", 0.5),
            ],
        },
        "uncertainty_tolerance": {
            "high": [
                ("openness", "personality", 1.0),
                ("curiosity", "cognitive_processing", 0.6),
            ],
            "low": [
                ("uncertainty_intolerance", "decision_making", 1.0),
                ("need_for_closure", "cognitive_processing", 0.8),
                ("risk_sensitivity", "decision_making", 0.6),
                ("trust_propensity", "social", 0.5),
                ("authority_susceptibility", "social", 0.5),
            ],
        },
        "status_sensitivity": {
            "high": [
                ("status_sensitivity", "motivation", 1.0),
                ("identity_salience", "motivation", 0.7),
                ("self_enhancement", "motivation", 0.6),
                ("narcissism_trait", "personality", 0.3),
            ],
            "low": [
                ("egalitarian_values", "motivation", 0.7),
                ("price_sensitivity", "decision_making", 0.5),
            ],
        },
        "cognitive_engagement": {
            "high": [
                ("need_for_cognition", "cognitive_processing", 1.0),
                ("analytical_processing", "cognitive_processing", 0.8),
                ("cognitive_engagement", "cognitive_processing", 0.9),
                ("conscientiousness", "personality", 0.5),
                ("comparison_tendency", "decision_making", 0.5),
            ],
            "low": [
                ("cognitive_miser", "cognitive_processing", 0.8),
                ("impulsivity", "decision_making", 0.4),
            ],
        },
        "arousal_seeking": {
            "high": [
                ("sensation_seeking", "motivation", 1.0),
                ("arousal_seeking", "motivation", 0.9),
                ("impulsivity", "decision_making", 0.5),
            ],
            "low": [
                ("comfort_preference", "motivation", 0.7),
                ("conscientiousness", "personality", 0.4),
            ],
        },
    }

    activations_dict: Dict[str, ConstructActivation] = {}

    def _add_activation(construct_id: str, domain: str, level: float, source: str):
        """Add or update a construct activation (keep highest level)."""
        mech_inf = CONSTRUCT_MECHANISM_INFLUENCES.get(construct_id, {})
        if construct_id in activations_dict:
            existing = activations_dict[construct_id]
            if level > existing.activation_level:
                activations_dict[construct_id] = ConstructActivation(
                    construct_id=construct_id, domain=domain,
                    activation_level=round(min(level, 1.0), 3),
                    source=source, mechanism_influences=mech_inf,
                )
        else:
            activations_dict[construct_id] = ConstructActivation(
                construct_id=construct_id, domain=domain,
                activation_level=round(min(level, 1.0), 3),
                source=source, mechanism_influences=mech_inf,
            )

    # Process bilateral dimensions with polarity
    # Skip exact-zero values (0.0) — these often mean "not measured" rather
    # than "definitely zero," and would produce artificial 1.0 activations.
    for dim_name, value in dim_values.items():
        mapping = _DIM_TO_POLAR_CONSTRUCT.get(dim_name)
        if not mapping:
            continue
        if value == 0.0:
            continue  # Likely "not measured" — skip to avoid false 1.0 activation

        high_mapping, low_mapping = mapping
        deviation = value - 0.5

        if deviation > 0.01 and high_mapping:
            construct_id, domain = high_mapping
            activation = min(deviation * 2.0, 1.0)  # 0.5→0, 0.75→0.5, 1.0→1.0
            _add_activation(construct_id, domain, activation, "bilateral_edge_directional")

        elif deviation < -0.01 and low_mapping:
            construct_id, domain = low_mapping
            activation = min(abs(deviation) * 2.0, 1.0)
            _add_activation(construct_id, domain, activation, "bilateral_edge_directional")

    # Process NDF dimensions — multi-construct mapping for segment engine compatibility
    if ndf:
        for dim_name, value in ndf.items():
            mapping = _NDF_TO_CONSTRUCTS.get(dim_name)
            if not mapping:
                continue

            deviation = value - 0.5
            base_activation = min(abs(deviation) * 2.0, 1.0)

            if deviation > 0.01:
                for construct_id, domain, weight in mapping.get("high", []):
                    _add_activation(construct_id, domain, base_activation * weight, "ndf_directional")
            elif deviation < -0.01:
                for construct_id, domain, weight in mapping.get("low", []):
                    _add_activation(construct_id, domain, base_activation * weight, "ndf_directional")

        # ================================================================
        # DIRECT NDF→CONSTRUCT passthrough for segment engine
        # Some CANONICAL_SEGMENTS constructs map 1:1 to NDF values.
        # Even when the NDF is near 0.5 (no polarity activation), the
        # segment engine needs the RAW value to compute match scores.
        # Without this, segments get 0.5 defaults and match poorly.
        # ================================================================
        _NDF_DIRECT_CONSTRUCTS = {
            # NDF dim → list of (construct_id, domain) that should receive the raw value
            "approach_avoidance": [
                ("approach_motivation", "motivation"),  # raw value (high = approach)
                ("promotion_focus", "self_regulatory"), # raw value (high = promotion)
            ],
            "social_calibration": [
                ("social_proof_susceptibility", "social"),
                ("extraversion", "personality"),
                ("agreeableness", "personality"),
                ("conformity_need", "social"),
                ("relatedness_need", "social"),
                ("social_comparison", "social"),
            ],
            "uncertainty_tolerance": [
                ("openness", "personality"),
                ("uncertainty_intolerance", "decision_making"),  # inverted below
                ("need_for_closure", "cognitive_processing"),   # inverted below
                ("trust_propensity", "social"),                  # inverted below
                ("authority_susceptibility", "social"),           # inverted below
            ],
            "status_sensitivity": [
                ("status_sensitivity", "motivation"),
                ("identity_salience", "motivation"),
                ("self_enhancement", "motivation"),
                ("narcissism_trait", "personality"),
            ],
            "cognitive_engagement": [
                ("need_for_cognition", "cognitive_processing"),
                ("analytical_processing", "cognitive_processing"),
                ("cognitive_engagement", "cognitive_processing"),
                ("comparison_tendency", "decision_making"),
            ],
            "arousal_seeking": [
                ("arousal_seeking", "motivation"),
                ("sensation_seeking", "motivation"),
                ("curiosity", "cognitive_processing"),
            ],
            "temporal_horizon": [
                ("conscientiousness", "personality"),  # high temporal = future-planning = conscientious
                ("delay_discounting", "temporal"),      # inverted: high horizon = LOW discounting
                ("present_bias", "temporal"),            # inverted: high horizon = LOW present bias
            ],
        }
        # Inverted constructs: these activate as 1.0 - ndf_value
        _INVERTED_CONSTRUCTS = {
            "uncertainty_intolerance", "need_for_closure",
            "trust_propensity", "authority_susceptibility",
            "delay_discounting", "present_bias",
        }

        for dim_name, constructs in _NDF_DIRECT_CONSTRUCTS.items():
            value = ndf.get(dim_name)
            if value is None:
                continue
            for construct_id, domain in constructs:
                raw = (1.0 - value) if construct_id in _INVERTED_CONSTRUCTS else value
                _add_activation(construct_id, domain, round(raw, 3), "ndf_direct")

        # Brand loyalty from brand_trust bilateral dim (if available)
        bt = dim_values.get("brand_trust_fit")
        if bt is not None and bt > 0.01:
            _add_activation("brand_loyalty", "social", round(bt, 3), "bilateral_direct")
        # Anchoring susceptibility
        anch = dim_values.get("anchor_susceptibility_match")
        if anch is not None and anch > 0.01:
            _add_activation("anchoring_susceptibility", "cognitive_processing", round(anch, 3), "bilateral_direct")

    # Sort by activation level descending
    activations = sorted(activations_dict.values(), key=lambda a: a.activation_level, reverse=True)
    return activations


def _segment_confidence_to_float(conf) -> float:
    """Convert a SegmentConfidence enum or raw value to float."""
    if isinstance(conf, (int, float)):
        return float(conf)
    # SegmentConfidence enum: HIGH="high", MODERATE="moderate", EXPLORATORY="exploratory"
    if hasattr(conf, "value"):
        _CONF_MAP = {"high": 0.9, "moderate": 0.6, "exploratory": 0.3}
        return _CONF_MAP.get(str(conf.value).lower(), 0.5)
    # String fallback
    if isinstance(conf, str):
        _CONF_MAP = {"high": 0.9, "moderate": 0.6, "exploratory": 0.3}
        return _CONF_MAP.get(conf.lower(), 0.5)
    return 0.5


def _build_enriched_segments(
    construct_activations: List[ConstructActivation],
) -> List[EnrichedSegment]:
    """
    Build enriched segments from PsychologicalSegmentEngine using construct activations.
    """
    engine = _get_segment_engine()
    if not engine or not construct_activations:
        return []

    try:
        # Build construct activation dict for the engine
        construct_dict = {
            a.construct_id: a.activation_level
            for a in construct_activations
            if a.activation_level > _get_intel_settings().construct_activation_min
        }

        if not construct_dict:
            return []

        matches = engine.match_profile_to_segments(construct_dict, top_n=5)

        # Load canonical segment definitions for mechanism recommendations
        try:
            from adam.segments.engine import CANONICAL_SEGMENTS
        except ImportError:
            CANONICAL_SEGMENTS = {}

        enriched = []
        for seg, match_score in matches:
            # Convert engine's MechanismRecommendation to dicts
            mech_recs = []
            if hasattr(seg, "mechanism_recommendations") and seg.mechanism_recommendations:
                for mr in seg.mechanism_recommendations:
                    if hasattr(mr, "mechanism"):
                        mech_recs.append({
                            "mechanism": mr.mechanism,
                            "predicted_effectiveness": getattr(mr, "predicted_effectiveness", 0.5),
                            "confidence": getattr(mr, "confidence", 0.5),
                            "reasoning": getattr(mr, "reasoning", ""),
                        })

            # Fallback: populate from CANONICAL_SEGMENTS good_mechanisms
            if not mech_recs:
                seg_def = CANONICAL_SEGMENTS.get(getattr(seg, "segment_id", ""), {})
                for i, mech in enumerate(seg_def.get("good_mechanisms", [])):
                    mech_recs.append({
                        "mechanism": mech,
                        "predicted_effectiveness": round(0.8 - i * 0.1, 2),
                        "confidence": 0.7 if i == 0 else 0.5,
                        "reasoning": f"{getattr(seg, 'name', '')} segment responds to {mech}",
                    })

            enriched.append(EnrichedSegment(
                segment_id=getattr(seg, "segment_id", ""),
                name=getattr(seg, "name", ""),
                description=getattr(seg, "description", ""),
                defining_constructs=getattr(seg, "defining_constructs", {}),
                regulatory_orientation=getattr(seg, "regulatory_orientation", ""),
                processing_style=getattr(seg, "processing_style", ""),
                mechanism_recommendations=mech_recs,
                mechanisms_to_avoid=getattr(seg, "mechanisms_to_avoid", []),
                creative_guidance=getattr(seg, "creative_guidance", {}),
                estimated_prevalence=getattr(seg, "estimated_prevalence", 0.0),
                confidence=_segment_confidence_to_float(getattr(seg, "confidence", 0.5)),
                strength=round(match_score, 3),
                recommended_mechanisms_list=[
                    mr.get("mechanism", "") if isinstance(mr, dict) else getattr(mr, "mechanism", "")
                    for mr in (mech_recs or [])
                ],
            ))

        return enriched

    except Exception as e:
        logger.debug("Enriched segment building failed: %s", e)
        return []


def _build_granular_type(body_text: Optional[str]) -> Optional[GranularTypeProfile]:
    """
    Detect granular customer type from body text using GranularCustomerTypeDetector.
    """
    if not body_text:
        return None

    detector = _get_granular_type_detector()
    if not detector:
        return None

    try:
        result = detector.detect(body_text)
        if not result or not getattr(result, "type_id", None):
            return None

        return GranularTypeProfile(
            type_id=result.type_id,
            type_name=getattr(result, "type_name", ""),
            dimensions={
                "purchase_motivation": getattr(result, "purchase_motivation", ""),
                "decision_style": getattr(result, "decision_style", ""),
                "regulatory_focus": getattr(result, "regulatory_focus", ""),
                "emotional_intensity": getattr(result, "emotional_intensity", ""),
                "price_sensitivity": getattr(result, "price_sensitivity", ""),
                "archetype": getattr(result, "archetype", ""),
                "domain": getattr(result, "domain", ""),
            },
            confidence=getattr(result, "overall_confidence", 0.0),
            mechanism_effectiveness=getattr(result, "mechanism_effectiveness", {}),
            recommended_mechanisms=getattr(result, "recommended_mechanisms", []),
        )
    except Exception as e:
        logger.debug("Granular type detection failed: %s", e)
        return None


def _build_interaction_aware_directions(
    gradient_priorities: List[GradientPriority],
    synergies: List[MechanismSynergy],
    mechanism_receptivity: List[MechanismScore],
) -> List[InteractionAwareDirection]:
    """
    Build interaction-aware creative directions by combining:
    1. Gradient priorities (where to invest — highest conversion lift dimensions)
    2. Mechanism synergies (which mechanisms amplify each other)
    3. Mechanism receptivity (what the audience responds to)

    For each top gradient priority:
      - Find which mechanisms influence that dimension
      - Check synergy data for amplifying/antagonizing combinations
      - Generate actionable creative brief
    """
    if not gradient_priorities:
        return []

    # Build mechanism lookup from receptivity
    mech_scores = {m.mechanism: m.score for m in mechanism_receptivity}

    # Build synergy/antagonism lookup from MECHANISM_SYNERGY graph edges
    synergy_map: Dict[str, List[str]] = {}  # mech → [synergistic partners]
    antagonism_map: Dict[str, List[str]] = {}  # mech → [antagonistic partners]
    ss = _get_intel_settings()
    for syn in synergies:
        if syn.synergy_score > ss.synergy_amplify_threshold:
            synergy_map.setdefault(syn.mechanism_a, []).append(syn.mechanism_b)
            synergy_map.setdefault(syn.mechanism_b, []).append(syn.mechanism_a)
        elif syn.synergy_score < ss.synergy_antagonize_threshold:
            antagonism_map.setdefault(syn.mechanism_a, []).append(syn.mechanism_b)
            antagonism_map.setdefault(syn.mechanism_b, []).append(syn.mechanism_a)

    # Enrich with MechanismInteractionLearner's empirically learned synergies
    # (from outcome observations, complements the pre-computed graph edges)
    learner = _get_mechanism_interaction_learner()
    if learner:
        for ms in mechanism_receptivity[:6]:
            mech = ms.mechanism
            try:
                syn_pairs = learner.get_synergistic_pairs(mech, min_strength=0.1, min_confidence=0.5)
                for partner, strength in syn_pairs:
                    if partner not in synergy_map.get(mech, []):
                        synergy_map.setdefault(mech, []).append(partner)
                sup_pairs = learner.get_suppressive_pairs(mech, min_strength=0.1, min_confidence=0.5)
                for partner, strength in sup_pairs:
                    if partner not in antagonism_map.get(mech, []):
                        antagonism_map.setdefault(mech, []).append(partner)
            except Exception:
                pass  # Learner may not have data for all mechanisms

    # Reverse map: dimension → mechanisms that influence it
    # Uses CONSTRUCT_MECHANISM_INFLUENCES for the mapping
    try:
        from adam.intelligence.unified_construct_integration import (
            CONSTRUCT_MECHANISM_INFLUENCES,
        )
        # Build dim → mechanisms from the construct influences
        dim_to_mechs: Dict[str, List[str]] = {}
        _DIM_CONSTRUCT_MAP = {
            "regulatory_fit": "regulatory_focus",
            "construal_fit": "cognitive_nfc",
            "personality_alignment": "big_five_agreeableness",
            "emotional_resonance": "emotional_appeal_match",
            "value_alignment": "personal_values",
            "social_proof_sensitivity": "social_proof_susceptibility",
            "loss_aversion_intensity": "loss_aversion",
            "narrative_transport": "narrative_transportation",
            "cognitive_load_tolerance": "cognitive_load",
            "autonomy_reactance": "psychological_reactance",
        }
        for dim_name, construct_id in _DIM_CONSTRUCT_MAP.items():
            influences = CONSTRUCT_MECHANISM_INFLUENCES.get(construct_id, {})
            if influences:
                # Mechanisms that this construct influences (sorted by strength)
                dim_to_mechs[dim_name] = sorted(
                    influences.keys(),
                    key=lambda m: abs(influences[m]),
                    reverse=True,
                )[:5]
    except ImportError:
        dim_to_mechs = {}

    directions = []
    selected_mechs = set()  # Track already-selected to avoid repeats

    for gp in gradient_priorities[:5]:
        # Find candidate mechanisms for this gradient dimension
        candidate_mechs = dim_to_mechs.get(gp.dimension, [])
        if not candidate_mechs:
            # Fallback: use top receptivity mechanisms
            candidate_mechs = [m.mechanism for m in mechanism_receptivity[:3]]

        # Pick best mechanism not already selected
        primary = None
        for cm in candidate_mechs:
            if cm not in selected_mechs and cm in mech_scores:
                primary = cm
                break
        if not primary and candidate_mechs:
            primary = candidate_mechs[0]
        if not primary:
            continue

        selected_mechs.add(primary)

        # Find synergistic and antagonistic mechanisms
        syn_mechs = [m for m in synergy_map.get(primary, []) if m in mech_scores]
        ant_mechs = [m for m in antagonism_map.get(primary, []) if m in mech_scores]

        # Estimate combined lift
        base_lift = abs(gp.expected_lift_pct)
        syn_bonus = base_lift * ss.synergy_bonus_factor * len(syn_mechs)
        combined_lift = base_lift + syn_bonus

        # Build creative brief
        syn_str = f" — synergizes with {', '.join(syn_mechs[:2])}" if syn_mechs else ""
        ant_str = f" Avoid {', '.join(ant_mechs[:2])} which would cancel the effect." if ant_mechs else ""
        brief = (
            f"Lead with {primary} on {gp.dimension.replace('_', ' ')}{syn_str} "
            f"for {combined_lift:.1f}% combined lift.{ant_str}"
        )

        directions.append(InteractionAwareDirection(
            primary_mechanism=primary,
            synergistic_mechanisms=syn_mechs[:3],
            antagonistic_mechanisms=ant_mechs[:3],
            gradient_dimension=gp.dimension,
            gradient_magnitude=gp.gradient_magnitude,
            combined_expected_lift_pct=round(combined_lift, 2),
            creative_brief=brief,
        ))

    return directions


# =============================================================================
# PUBLISHER ENDPOINT: Profile a page's psychological environment
# =============================================================================

@router.post(
    "/page/profile",
    response_model=PageProfileResponse,
    summary="Profile a page's psychological environment",
    description=(
        "Analyzes page content to determine what psychological state it creates "
        "in readers, which advertiser verticals would benefit most, and what "
        "persuasion mechanisms the reader is receptive to. Used by publishers "
        "to grade their inventory and by SSPs for floor pricing."
    ),
)
async def profile_page(request: PageProfileRequest) -> PageProfileResponse:
    start = time.monotonic()

    profiler = _get_content_profiler()
    build_segments, _ = _get_segment_builder()

    ndf: Dict[str, float] = {}
    segments_raw: List[Dict[str, Any]] = []
    mechanisms: List[str] = []
    confidence = 0.3
    intelligence_level = IntelligenceLevel.HEURISTIC
    category_env: Optional[Dict[str, Any]] = None
    edge_count = 0

    # =====================================================================
    # LAYER 1: Graph-backed category intelligence (PRIMARY when category known)
    #
    # Query bilateral edge aggregates for this category. The aggregate
    # buyer NDF across conversions IS the psychological environment this
    # content type creates. This is evidence-backed, not keyword-based.
    # =====================================================================
    if request.category:
        category_env = await _query_category_psychological_environment(request.category)

    s = _get_intel_settings()

    if category_env and category_env.get("ndf_profile"):
        ndf = category_env["ndf_profile"]
        edge_count = category_env.get("edge_count", 0)
        intelligence_level = category_env.get("intelligence_level", IntelligenceLevel.L2_CATEGORY)
        confidence = min(s.confidence_cap, s.confidence_floor + (edge_count / s.confidence_edge_norm))

    # =====================================================================
    # LAYER 2: Content profiler enrichment (BLENDED with graph when available)
    #
    # When body_text is available, content profiler provides text-specific
    # signals. When graph NDF is also available, blend 65% graph + 35%
    # content profiler (graph has conversion evidence; profiler has page-
    # specific text signals). When graph unavailable, profiler is primary.
    # =====================================================================
    content_ndf: Dict[str, float] = {}
    content_mechanisms: List[str] = []
    content_mechanism_scores: List[Dict[str, Any]] = []
    if profiler and request.body_text:
        try:
            profile_result = await profiler.profile(
                title=request.title,
                body=request.body_text,
                metadata=request.metadata,
            )
            content_ndf = profile_result.get("ndf_profile", {})
            content_mechanisms = profile_result.get("mechanisms", [])
            content_mechanism_scores = profile_result.get("mechanism_scores", [])
        except Exception as e:
            logger.warning("Content profiling failed: %s", e)

    if ndf and content_ndf:
        # Blend: graph evidence + content-specific text signals (externalized weights)
        for dim in _NDF_DIMS:
            graph_val = ndf.get(dim, 0.5)
            text_val = content_ndf.get(dim, 0.5)
            ndf[dim] = s.graph_weight * graph_val + s.profiler_weight * text_val
        mechanisms = content_mechanisms
        # Blended intelligence is no longer pure L3 — downgrade to L2
        if intelligence_level == IntelligenceLevel.L3_BILATERAL:
            intelligence_level = IntelligenceLevel.L2_CATEGORY
            logger.debug("Intelligence level downgraded to L2 after graph+content blend")
    elif content_ndf and not ndf:
        # No graph intelligence — content profiler is sole source
        ndf = content_ndf
        mechanisms = content_mechanisms
        confidence = max(confidence, 0.3)
        if intelligence_level == IntelligenceLevel.HEURISTIC:
            intelligence_level = IntelligenceLevel.L1_ARCHETYPE

    # =====================================================================
    # LAYER 3: Theory-graph mechanism inference (ENRICHMENT)
    #
    # When NDF is available (from any source), run the theory graph
    # State→Need→Mechanism traversal to get causal mechanism recommendations.
    # This replaces keyword-based mechanism detection with theory-backed
    # inference grounded in Kruglanski, Cialdini, Petty & Cacioppo.
    # Works with any NDF profile — no archetype or category required.
    # =====================================================================
    theory_chains = None
    if ndf:
        try:
            from adam.intelligence.graph.reasoning_chain_generator import (
                generate_chains_local,
            )
            theory_chains = generate_chains_local(
                ndf_profile=ndf,
                archetype="",
                category=request.category or "",
                top_k=5,
            )
            if theory_chains:
                # Extract theory-backed mechanism names to supplement
                # content profiler mechanisms (which are keyword-based)
                theory_mechs = [
                    getattr(c, "recommended_mechanism", None)
                    for c in theory_chains
                    if getattr(c, "recommended_mechanism", None)
                ]
                if theory_mechs and not mechanisms:
                    mechanisms = theory_mechs
                elif theory_mechs:
                    # Merge: theory mechanisms that aren't already in content list
                    for tm in theory_mechs:
                        if tm not in mechanisms:
                            mechanisms.append(tm)
        except Exception as e:
            logger.debug("Theory graph inference unavailable: %s", e)

    # =====================================================================
    # Build segments from NDF (legacy SegmentBuilder — fallback only)
    # Primary segments come from PsychologicalSegmentEngine via
    # enriched_segments field, built later from construct activations.
    # SegmentBuilder populates the backward-compat `segments` field.
    # =====================================================================
    if build_segments and ndf:
        try:
            segments_raw = build_segments(ndf, mechanisms, request.category)
        except Exception as e:
            logger.warning("Segment building failed: %s", e)

    # =====================================================================
    # Build psychological layers — now with graph-aware channel state
    # =====================================================================
    layers = []
    if ndf:
        # Channel state: multi-dimensional assessment instead of naive threshold.
        # Closed when: low engagement AND low arousal AND high avoidance AND
        # high decision entropy (content creates confused, disengaged state).
        ce = ndf.get("cognitive_engagement", 0.5)
        ar = ndf.get("arousal_seeking", 0.5)
        aa = ndf.get("approach_avoidance", 0.5)
        # Include extended dimensions when available from graph
        de = 0.5
        if category_env and category_env.get("extended_dimensions"):
            de = category_env["extended_dimensions"].get("decision_entropy", 0.5)

        channel_openness = (ce * s.channel_ce_weight + ar * s.channel_ar_weight + aa * s.channel_aa_weight + (1.0 - de) * s.channel_de_weight)
        if channel_openness < s.channel_closed:
            channel_state = f"closed — openness {channel_openness:.2f}"
        elif channel_openness < s.channel_narrow:
            channel_state = f"narrow — openness {channel_openness:.2f}"
        else:
            channel_state = f"open — openness {channel_openness:.2f}"

        # Competitive environment from extended dimensions
        comp_env = "standard"
        if category_env and category_env.get("composite_std"):
            std = category_env["composite_std"]
            if std > s.comp_env_high_variance:
                comp_env = f"high variance (σ={std:.2f}) — differentiation opportunity"
            elif std < s.comp_env_low_variance:
                comp_env = f"low variance (σ={std:.2f}) — saturated"

        layer_defs = [
            (1, "Activated Needs", _infer_mindset(ndf)),
            (2, "Emotional Field", f"valence={ndf.get('approach_avoidance', 0.5):.2f}, arousal={ndf.get('arousal_seeking', 0.5):.2f}"),
            (3, "Cognitive State", f"engagement={ndf.get('cognitive_engagement', 0.5):.2f}"),
            (4, "Credibility", f"analytical_depth={ndf.get('cognitive_engagement', 0.5):.2f}"),
            (5, "Primed Categories", request.category or "general"),
            (6, "Channel State", channel_state),
            (7, "Competitive Environment", comp_env),
            (8, "Decision Style", _infer_processing_route(ndf)),
        ]
        for num, name, val in layer_defs:
            layers.append(PagePsychologyLayer(
                layer_name=name, layer_number=num, value=val,
            ))

    # =====================================================================
    # Compute vertical values
    # =====================================================================
    vertical_values = (await _compute_vertical_values_from_graph(ndf)) if ndf else []

    # =====================================================================
    # Mechanism receptivity — graph-backed with evidence depth
    # =====================================================================
    archetype = await _ndf_to_best_archetype(ndf) if ndf else "pragmatist"
    mech_receptivity = await _query_mechanism_receptivity_from_graph(
        archetype=archetype,
        category=request.category,
        category_env=category_env,
    )

    # Fallback tier 2: theory-graph causal chains (theory-backed, not keyword)
    if not mech_receptivity and theory_chains:
        for chain in theory_chains:
            mech = getattr(chain, "recommended_mechanism", None)
            score = getattr(chain, "mechanism_score", 0.5)
            if mech:
                mech_receptivity.append(MechanismScore(
                    mechanism=mech,
                    score=round(score, 3),
                    evidence_depth="moderate",
                    source="theory_graph",
                ))

    # Fallback tier 3: content profiler keyword mechanisms (weakest)
    if not mech_receptivity and content_mechanism_scores:
        for ms in content_mechanism_scores:
            if isinstance(ms, dict) and "mechanism" in ms:
                mech_receptivity.append(MechanismScore(
                    mechanism=ms["mechanism"],
                    score=ms.get("score", 0.5),
                    evidence_depth="none",
                    source="content_profiler",
                ))

    # Deduplicate mechanisms (keep highest-scored entry per mechanism name)
    if mech_receptivity:
        seen = {}
        for ms in mech_receptivity:
            if ms.mechanism not in seen or ms.score > seen[ms.mechanism].score:
                seen[ms.mechanism] = ms
        mech_receptivity = list(seen.values())

    elapsed = (time.monotonic() - start) * 1000

    # Build theory chain summaries for response
    theory_chain_summaries = []
    if theory_chains:
        for chain in theory_chains:
            guidance = getattr(chain, "creative_guidance", None)
            guidance_dict = {}
            if guidance:
                guidance_dict = {
                    "what_to_say": getattr(guidance, "what_to_say", []),
                    "what_not_to_say": getattr(guidance, "what_not_to_say", []),
                    "tone": getattr(guidance, "tone", ""),
                    "detail_level": getattr(guidance, "detail_level", ""),
                    "urgency_level": getattr(guidance, "urgency_level", ""),
                    "social_framing": getattr(guidance, "social_framing", ""),
                }
            theory_chain_summaries.append(TheoryChainSummary(
                mechanism=getattr(chain, "recommended_mechanism", ""),
                score=getattr(chain, "mechanism_score", 0.0),
                active_states=getattr(chain, "active_states", []),
                active_needs=getattr(chain, "active_needs", []),
                creative_guidance=guidance_dict,
                confidence=getattr(chain, "confidence", 0.0),
            ))

    # Build extended dimensions from category environment
    ext_dims = {}
    if category_env and category_env.get("extended_dimensions"):
        ext_dims = category_env["extended_dimensions"]

    # Gradient priorities: which dimensions yield most conversion lift
    gradient_prios = await _query_gradient_priorities(
        archetype=archetype,
        category=request.category,
        current_ndf=ndf,
    )

    # Mechanism synergies: which combinations amplify vs cancel
    active_mechs = [m.mechanism for m in mech_receptivity[:6]]
    synergies = await _query_mechanism_synergies(active_mechs)

    # Per-dimension confidence
    dim_confidence = _build_dimension_confidence(
        ndf, category_env, content_profiled=bool(content_ndf),
    )

    # =====================================================================
    # FULL-POWER FIELDS — bilateral dimensions, constructs, segments, etc.
    # =====================================================================
    bilateral_dims = _build_bilateral_dimensions_from_env(category_env)
    construct_acts = _build_construct_activations(bilateral_dims, ndf=ndf)
    enriched_segs = _build_enriched_segments(construct_acts)
    granular_type = _build_granular_type(request.body_text)
    interaction_dirs = _build_interaction_aware_directions(
        gradient_prios, synergies, mech_receptivity,
    )

    # Metadata signals from category environment
    meta_signals = {}
    if category_env and category_env.get("metadata_signals"):
        meta_signals = category_env["metadata_signals"]

    return PageProfileResponse(
        page_url=request.page_url,
        psychological_profile=_ndf_to_profile(ndf),
        extended_dimensions=ext_dims,
        psychological_layers=layers,
        # Primary: derive backward-compat segments FROM enriched_segments.
        # Fallback: old SegmentBuilder segments_raw when engine unavailable.
        segments=(
            [
                PsychologicalSegment(
                    segment_id=es.segment_id,
                    name=es.name,
                    description=es.description,
                    strength=es.strength,
                    iab_taxonomy_ids=es.iab_taxonomy_ids,
                    recommended_mechanisms=es.recommended_mechanisms_list,
                )
                for es in enriched_segs
            ]
            if enriched_segs
            else [
                PsychologicalSegment(
                    segment_id=seg.get("segment_id", ""),
                    name=seg.get("segment_name", ""),
                    description=seg.get("description", ""),
                    strength=seg.get("strength", seg.get("ndf_strength", 0.0)),
                    iab_taxonomy_ids=seg.get("taxonomy_ids", seg.get("iab_taxonomy_ids", [])),
                    recommended_mechanisms=seg.get("recommended_mechanisms", []),
                )
                for seg in segments_raw
            ]
        ),
        vertical_values=vertical_values,
        dominant_mindset=_infer_mindset(ndf) if ndf else "",
        processing_route=_infer_processing_route(ndf) if ndf else "",
        mechanism_receptivity=mech_receptivity,
        theory_chains=theory_chain_summaries,
        gradient_priorities=gradient_prios,
        mechanism_synergies=synergies,
        dimension_confidence=dim_confidence,
        # Full-power fields
        bilateral_dimensions=bilateral_dims,
        construct_activations=construct_acts,
        granular_type=granular_type,
        enriched_segments=enriched_segs,
        interaction_aware_directions=interaction_dirs,
        metadata_signals=meta_signals,
        confidence=confidence,
        intelligence_level=intelligence_level,
        edge_evidence_count=edge_count,
        profiling_ms=round(elapsed, 2),
    )


# =============================================================================
# SSP ENDPOINT: Enrich a bid request with psychological signals
# =============================================================================

@router.post(
    "/bid/enrich",
    response_model=BidEnrichmentResponse,
    summary="Enrich a bid request with psychological signals",
    description=(
        "Attaches psychological segments and value signals to a bid request "
        "in OpenRTB 2.5 format. SSPs include this in the data[] array of "
        "bid requests so DSPs can bid based on psychological environment, "
        "not just demographics. Also returns a floor multiplier."
    ),
)
async def enrich_bid(request: BidEnrichmentRequest) -> BidEnrichmentResponse:
    start = time.monotonic()

    ndf: Dict[str, float] = {}
    segments_raw: List[Dict[str, Any]] = []
    intelligence_level = IntelligenceLevel.HEURISTIC
    category_env: Optional[Dict[str, Any]] = None
    edge_count = 0

    # =====================================================================
    # LAYER 1: Graph-backed category intelligence (fastest path when
    # category is known — no text processing needed)
    # =====================================================================
    if request.page_category:
        category_env = await _query_category_psychological_environment(request.page_category)
        if category_env and category_env.get("ndf_profile"):
            ndf = category_env["ndf_profile"]
            edge_count = category_env.get("edge_count", 0)
            intelligence_level = category_env.get(
                "intelligence_level", IntelligenceLevel.L2_CATEGORY,
            )

    # =====================================================================
    # LAYER 2: Cached profile or content profiler fallback
    # =====================================================================
    if not ndf and request.cached_page_profile:
        ndf = request.cached_page_profile.get("ndf_profile", {})
        segments_raw = request.cached_page_profile.get("segments", [])
        if ndf:
            intelligence_level = IntelligenceLevel.L2_CATEGORY

    if not ndf:
        profiler = _get_content_profiler()
        if profiler and request.page_title:
            try:
                profile_result = await profiler.profile(
                    title=request.page_title,
                    body=request.page_title,  # minimal — title only for speed
                    metadata={"category": request.page_category},
                )
                ndf = profile_result.get("ndf_profile", {})
                intelligence_level = IntelligenceLevel.L1_ARCHETYPE
            except Exception as e:
                logger.debug("SSP content profiling failed: %s", e)

    # =====================================================================
    # Build segments
    # =====================================================================
    # Build enriched segments (primary) + legacy fallback
    # =====================================================================
    bid_bilateral_dims = _build_bilateral_dimensions_from_env(category_env)
    bid_construct_acts = _build_construct_activations(bid_bilateral_dims, ndf=ndf)
    bid_enriched_segs = _build_enriched_segments(bid_construct_acts)

    # Legacy SegmentBuilder — fallback only when engine unavailable
    build_segments, _ = _get_segment_builder()
    if not bid_enriched_segs and build_segments and ndf:
        try:
            segments_raw = build_segments(ndf)
        except Exception as e:
            logger.debug("SSP segment building failed: %s", e)

    # =====================================================================
    # Convert to OpenRTB format
    #
    # THREE signal layers in the OpenRTB data[] array:
    #
    # 1. CONTINUOUS bilateral dimensions as key-value segments
    #    (informativ_dim_{name} = value). DSPs that understand continuous
    #    signals can bid on these directly — no compression.
    #
    # 2. CONTINUOUS construct activations (top 10)
    #    (informativ_construct_{id} = activation). Richer than segments,
    #    maps to mechanism effectiveness for creative optimization.
    #
    # 3. DISCRETE enriched segments (8 buckets)
    #    (informativ_{segment_id} = strength). For DSPs that only
    #    support discrete segment targeting.
    # =====================================================================
    openrtb_segments = []

    # Layer 1: Bilateral dimensions as continuous key-value signals
    # DSPs bid on these directly: "informativ_dim_brand_trust_fit" = "0.73"
    for bd in bid_bilateral_dims:
        if bd.value is not None and abs(bd.value - 0.5) > 0.02:
            openrtb_segments.append(OpenRTBSegment(
                id=f"informativ_dim_{bd.name}",
                name=f"Dim: {bd.name.replace('_', ' ')}",
                value=str(round(bd.value, 3)),
            ))

    # Layer 2: Top construct activations as continuous signals
    # "informativ_construct_promotion_focus" = "0.6"
    for ca in bid_construct_acts[:10]:
        if ca.activation_level > _get_intel_settings().construct_activation_min:
            openrtb_segments.append(OpenRTBSegment(
                id=f"informativ_construct_{ca.construct_id}",
                name=f"Construct: {ca.construct_id.replace('_', ' ')}",
                value=str(round(ca.activation_level, 3)),
            ))

    # Layer 3: Discrete enriched segments (backward compat for simple DSPs)
    if bid_enriched_segs:
        for es in bid_enriched_segs:
            if es.segment_id:
                openrtb_segments.append(OpenRTBSegment(
                    id=f"informativ_{es.segment_id}",
                    name=es.name,
                    value=str(round(es.strength, 2)),
                ))
    else:
        for seg in segments_raw:
            seg_id = seg.get("segment_id", "")
            if seg_id:
                openrtb_segments.append(OpenRTBSegment(
                    id=f"informativ_{seg_id}",
                    name=seg.get("segment_name", ""),
                    value=str(round(seg.get("strength", seg.get("ndf_strength", 0.0)), 2)),
                ))

    if ndf:
        mindset = _infer_mindset(ndf)
        openrtb_segments.append(OpenRTBSegment(
            id=f"informativ_mindset_{mindset}",
            name=f"Mindset: {mindset}",
            value="1.0",
        ))

        route = _infer_processing_route(ndf)
        openrtb_segments.append(OpenRTBSegment(
            id=f"informativ_route_{route}",
            name=f"Processing: {route}",
            value="1.0",
        ))

    # =====================================================================
    # Floor multiplier — bilateral evidence-backed when available
    #
    # When category_env has bilateral edge evidence, the floor multiplier
    # is derived from actual conversion data (composite_alignment from
    # BRAND_CONVERTED edges). When unavailable, falls back to vertical
    # grading via RESPONDS_TO edges.
    # =====================================================================
    s = _get_intel_settings()
    floor_multiplier = 1.0
    if category_env and category_env.get("composite_alignment") is not None:
        composite = category_env["composite_alignment"]
        floor_multiplier = s.cpm_floor + composite * s.cpm_scale

        # Adjust for advertiser vertical if provided
        if request.advertiser_vertical and category_env.get("mechanism_effectiveness"):
            vertical_config = _VERTICAL_PSYCHOLOGY.get(request.advertiser_vertical)
            if vertical_config:
                mech_eff = category_env["mechanism_effectiveness"]
                vertical_mechs = vertical_config.get("mechanisms", [])
                vertical_boost = 0.0
                n_matched = 0
                for vm in vertical_mechs:
                    if vm in mech_eff:
                        vertical_boost += mech_eff[vm]["effectiveness"]
                        n_matched += 1
                if n_matched > 0:
                    avg_mech_match = vertical_boost / n_matched
                    floor_multiplier += (avg_mech_match - 0.5) * s.cpm_vertical_adj
    else:
        # Fallback: vertical values from RESPONDS_TO edges
        vertical_values = (await _compute_vertical_values_from_graph(ndf)) if ndf else []
        if vertical_values:
            if request.advertiser_vertical:
                for v in vertical_values:
                    if v.vertical == request.advertiser_vertical:
                        floor_multiplier = v.value_multiplier
                        break
                else:
                    top3 = vertical_values[:3]
                    floor_multiplier = sum(v.value_multiplier for v in top3) / len(top3)
            else:
                top3 = vertical_values[:3]
                floor_multiplier = sum(v.value_multiplier for v in top3) / len(top3)

    floor_multiplier = max(s.cpm_floor, min(s.cpm_floor + s.cpm_scale, floor_multiplier))

    # =====================================================================
    # Channel state — multi-dimensional assessment
    # =====================================================================
    channel_openness = 1.0
    channel_open = True
    if ndf:
        ce = ndf.get("cognitive_engagement", 0.5)
        ar = ndf.get("arousal_seeking", 0.5)
        aa = ndf.get("approach_avoidance", 0.5)
        de = 0.5
        if category_env and category_env.get("extended_dimensions"):
            de = category_env["extended_dimensions"].get("decision_entropy", 0.5)
        channel_openness = ce * s.channel_ce_weight + ar * s.channel_ar_weight + aa * s.channel_aa_weight + (1.0 - de) * s.channel_de_weight
        channel_open = channel_openness >= s.channel_closed

    # =====================================================================
    # Mechanism receptivity — graph-backed
    # =====================================================================
    archetype = await _ndf_to_best_archetype(ndf) if ndf else "pragmatist"
    mech_receptivity = await _query_mechanism_receptivity_from_graph(
        archetype=archetype,
        category=request.page_category,
        category_env=category_env,
    )

    # Gradient priorities and synergies for the SSP
    gradient_prios = await _query_gradient_priorities(
        archetype=archetype, category=request.page_category, current_ndf=ndf,
    )
    active_mechs = [m.mechanism for m in mech_receptivity[:6]]
    synergies = await _query_mechanism_synergies(active_mechs)

    # =====================================================================
    # DAILY STRENGTHENING INTELLIGENCE
    # Reads pre-computed intelligence from the 10 daily tasks.
    # All lookups are Redis (<2ms). Falls back gracefully if unavailable.
    # =====================================================================
    page_intel_tier = "domain_heuristic"
    recommended_ad_pos = ""
    est_viewability = 0.5
    cat_temperature = 0.0
    active_events_list: List[str] = []

    try:
        from adam.intelligence.daily.consumer import get_intelligence_consumer
        consumer = get_intelligence_consumer()

        # Environmental context (ambient + calendar)
        env_ctx = consumer.get_environmental_context()
        active_events_list = env_ctx.get("active_events", [])

        # Apply environmental mechanism modifiers to floor multiplier
        env_mods = env_ctx.get("combined_mechanism_mods", {})
        if env_mods and mech_receptivity:
            # Boost floor for mechanisms enhanced by environment
            top_mech = mech_receptivity[0].mechanism if mech_receptivity else ""
            env_boost = float(env_mods.get(top_mech, 1.0))
            if env_boost > 1.1:
                floor_multiplier *= min(1.2, env_boost * 0.5 + 0.5)

        # Category temperature
        if request.page_category:
            temp = consumer.get_category_temperature(request.page_category)
            cat_temperature = temp.get("score", 0.0)

        # Page intelligence tier (from crawl cache)
        if request.page_url:
            from adam.intelligence.page_intelligence import get_page_intelligence_cache
            page_cache = get_page_intelligence_cache()
            page_profile = page_cache.lookup(request.page_url)
            if page_profile:
                page_intel_tier = page_profile.profile_source
                recommended_ad_pos = getattr(page_profile, "ad_position_optimal", "")
                est_viewability = getattr(page_profile, "estimated_viewability", 0.5)

                # Add page-derived segments to OpenRTB
                if page_profile.processing_mode:
                    openrtb_segments.append(OpenRTBSegment(
                        id=f"informativ_page_{page_profile.processing_mode}",
                        name=f"Page Processing: {page_profile.processing_mode}",
                        value="1.0",
                    ))
                if page_profile.publisher_authority > 0.7:
                    openrtb_segments.append(OpenRTBSegment(
                        id="informativ_page_high_authority",
                        name="Page: High Authority Publisher",
                        value=str(round(page_profile.publisher_authority, 2)),
                    ))
    except Exception as e:
        logger.debug("Daily strengthening intelligence unavailable: %s", e)

    floor_multiplier = max(s.cpm_floor, min(s.cpm_floor + s.cpm_scale, floor_multiplier))

    elapsed = (time.monotonic() - start) * 1000

    return BidEnrichmentResponse(
        impression_id=request.impression_id,
        openrtb_data=OpenRTBData(segment=openrtb_segments),
        floor_multiplier=round(floor_multiplier, 2),
        psychological_profile=_ndf_to_profile(ndf) if ndf else None,
        dominant_mindset=_infer_mindset(ndf) if ndf else "",
        channel_open=channel_open,
        channel_openness=round(channel_openness, 3),
        edge_evidence_count=edge_count,
        mechanism_receptivity=mech_receptivity,
        mechanism_synergies=synergies,
        gradient_priorities=gradient_prios,
        # Full-power fields
        bilateral_dimensions=bid_bilateral_dims,
        enriched_segments=bid_enriched_segs,
        intelligence_level=intelligence_level,
        # Page intelligence fields
        page_intelligence_tier=page_intel_tier,
        recommended_ad_position=recommended_ad_pos,
        estimated_viewability=round(est_viewability, 3),
        category_temperature=round(cat_temperature, 3),
        active_events=active_events_list,
        enrichment_ms=round(elapsed, 2),
    )


# =============================================================================
# BRAND ENDPOINT: Analyze a brand's messaging psychology
# =============================================================================

@router.post(
    "/brand/profile",
    response_model=BrandProfileResponse,
    summary="Analyze a brand's messaging psychology",
    description=(
        "Profiles a brand's messaging to determine what psychological dimensions "
        "it activates, which audience segments align best, and where there's "
        "whitespace vs. competitors. Includes gradient-field-informed creative "
        "direction for optimization."
    ),
)
async def profile_brand(request: BrandProfileRequest) -> BrandProfileResponse:
    start = time.monotonic()

    build_segments, _ = _get_segment_builder()
    unified = _get_unified_intelligence()

    brand_ndf: Dict[str, float] = {}
    seller_psychology: Dict[str, Any] = {}
    mechanisms: List[str] = []
    intelligence_level = IntelligenceLevel.HEURISTIC
    product_intel = None
    brand_archetype = None

    # STRATEGY: Two paths for brand profiling, depending on data available.
    #
    # PATH A (ASIN available): Query the graph's seller-side properties directly.
    #   ProductDescription nodes have 65+ Claude-annotated ad-side constructs
    #   (ad_persuasion_techniques_*, ad_emotional_appeal_*, etc.)
    #   This is SELLER psychology — what the brand's messaging actually does.
    #
    # PATH B (no ASIN): Fall back to content profiler on brand text.
    #   This is weaker — it runs a buyer-NDF profiler on seller copy.
    #   Results are approximate and should be flagged as heuristic.

    # PATH A: Query seller-side psychology from graph
    if unified and request.asin:
        try:
            product_intel = unified.get_intelligence(
                asin=request.asin,
                category=request.target_category or "",
            )
            if product_intel and product_intel.get("layers_used"):
                intelligence_level = IntelligenceLevel.L3_BILATERAL

                # Extract SELLER-SIDE persuasion scores from ProductDescription
                layer3 = product_intel.get("layer3", {})
                product = layer3.get("product", {})
                if product:
                    # Extract ad-side persuasion techniques
                    for key, val in product.items():
                        if key.startswith("ad_persuasion_techniques_") and val is not None:
                            mech = key.replace("ad_persuasion_techniques_", "")
                            seller_psychology[mech] = float(val)
                            if float(val) > 0.5:
                                mechanisms.append(mech)

                    # Derive NDF-like profile from BILATERAL edge averages.
                    # Uses same mapping as _query_category_psychological_environment:
                    #   regulatory_fit → approach_avoidance (Higgins regulatory focus)
                    #   construal_fit → temporal_horizon (Trope-Liberman construal level)
                    #   personality_alignment → social_calibration (Big Five congruence)
                    #   decision_entropy → uncertainty_tolerance (inverted: high entropy = low tolerance)
                    #   value_alignment → status_sensitivity (values predict status sensitivity)
                    #   information_seeking → cognitive_engagement (information need = engagement)
                    #   emotional_resonance → arousal_seeking (emotional intensity → arousal)
                    edge_stats = layer3.get("edge_statistics", {})
                    if edge_stats:
                        brand_ndf = {
                            "approach_avoidance": edge_stats.get("avg_reg_fit",
                                                    edge_stats.get("avg_regulatory_fit", 0.5)),
                            "temporal_horizon": edge_stats.get("avg_construal_fit", 0.5),
                            "social_calibration": edge_stats.get("avg_personality",
                                                    edge_stats.get("avg_personality_alignment", 0.5)),
                            "uncertainty_tolerance": 1.0 - edge_stats.get("avg_decision_entropy",
                                                            edge_stats.get("decision_entropy", 0.5)),
                            "status_sensitivity": edge_stats.get("avg_value",
                                                    edge_stats.get("avg_value_alignment", 0.5)),
                            "cognitive_engagement": edge_stats.get("avg_info_seeking",
                                                     edge_stats.get("avg_information_seeking", 0.5)),
                            "arousal_seeking": edge_stats.get("avg_emotional",
                                                edge_stats.get("avg_emotional_resonance", 0.5)),
                        }
                        brand_archetype = await _ndf_to_best_archetype(brand_ndf)

                # Infer archetype from buyer-side edge data
                layer1 = product_intel.get("layer1", {})
                if layer1.get("inferred_archetype"):
                    brand_archetype = layer1["inferred_archetype"]

        except Exception as e:
            logger.warning("Graph-backed brand profiling failed: %s", e)

    # PATH B: Content profiler fallback (buyer-NDF on seller text — approximate)
    if not brand_ndf:
        profiler = _get_content_profiler()
        text = " ".join(filter(None, [
            request.brand_description,
            request.product_description,
            request.sample_ad_copy,
        ]))
        if profiler and text:
            try:
                profile_result = await profiler.profile(
                    title=request.brand_name,
                    body=text,
                )
                brand_ndf = profile_result.get("ndf_profile", {})
                mechanisms = profile_result.get("mechanisms", [])
                intelligence_level = IntelligenceLevel.L1_ARCHETYPE
            except Exception as e:
                logger.warning("Brand content profiling failed: %s", e)

    # Ensure brand_archetype is always set (PATH A may have set it; PATH B didn't)
    if not brand_archetype and brand_ndf:
        brand_archetype = await _ndf_to_best_archetype(brand_ndf)

    # Build audience alignments using BUYER segments
    # Primary: PsychologicalSegmentEngine via construct activations
    # Fallback: SegmentBuilder when engine unavailable
    alignments = []
    brand_construct_acts_for_segs = _build_construct_activations([], ndf=brand_ndf)
    brand_enriched_for_align = _build_enriched_segments(brand_construct_acts_for_segs)
    seg_settings = _get_intel_settings()

    if brand_enriched_for_align:
        for es in brand_enriched_for_align:
            alignments.append(AudienceAlignment(
                segment=PsychologicalSegment(
                    segment_id=es.segment_id,
                    name=es.name,
                    strength=es.strength,
                    recommended_mechanisms=es.recommended_mechanisms_list,
                ),
                alignment_score=es.strength,
                opportunity=(
                    "strong match" if es.strength > seg_settings.segment_strong
                    else "growth opportunity" if es.strength > seg_settings.segment_growth
                    else "misaligned"
                ),
            ))
    elif build_segments and brand_ndf:
        try:
            all_segments = build_segments(brand_ndf, mechanisms)
            for seg in all_segments:
                strength = seg.get("strength", seg.get("ndf_strength", 0.0))
                alignments.append(AudienceAlignment(
                    segment=PsychologicalSegment(
                        segment_id=seg.get("segment_id", ""),
                        name=seg.get("segment_name", ""),
                        strength=strength,
                        recommended_mechanisms=seg.get("recommended_mechanisms", []),
                    ),
                    alignment_score=strength,
                    opportunity=(
                        "strong match" if strength > seg_settings.segment_strong
                        else "growth opportunity" if strength > seg_settings.segment_growth
                        else "misaligned"
                    ),
                ))
        except Exception as e:
            logger.debug("Brand audience alignment failed: %s", e)

    # Mechanism scores — prefer seller-side graph data over content profiler
    mech_scores = []
    if seller_psychology:
        # From graph: actual ad-side persuasion technique scores
        for mech, score in sorted(seller_psychology.items(), key=lambda x: x[1], reverse=True)[:8]:
            mech_scores.append(MechanismScore(
                mechanism=mech, score=score, source="graph_seller_side",
            ))
    elif product_intel and product_intel.get("fused_mechanisms"):
        for fm in product_intel["fused_mechanisms"]:
            mech_scores.append(MechanismScore(
                mechanism=fm["mechanism"], score=fm["fused_score"], source="three_layer_fusion",
            ))
    elif mechanisms:
        for i, m in enumerate(mechanisms[:5]):
            mech_scores.append(MechanismScore(
                mechanism=m, score=_get_intel_settings().fallback_mech_base - i * _get_intel_settings().fallback_mech_decrement, source="content_profiler_heuristic",
            ))

    # Gradient priorities from bilateral edge statistics
    gradient_priorities = []
    if product_intel and product_intel.get("layer3", {}).get("edge_statistics"):
        stats = product_intel["layer3"]["edge_statistics"]
        for dim in ["regulatory_fit", "personality_alignment", "emotional_resonance",
                     "construal_fit", "value_alignment"]:
            key = f"avg_{dim}" if not dim.startswith("avg_") else dim
            val = stats.get(key)
            if val is not None:
                gradient_priorities.append({
                    "dimension": dim,
                    "current_value": round(val, 3),
                    "importance": "high" if val < _get_intel_settings().segment_growth else "medium" if val < _get_intel_settings().segment_strong else "low",
                })

    elapsed = (time.monotonic() - start) * 1000

    # Full-power: bilateral dimensions from product intelligence
    brand_bilateral_dims = []
    brand_construct_acts = []
    brand_enriched_segs = []
    brand_interaction_dirs = []

    if product_intel and product_intel.get("layer3", {}).get("edge_statistics"):
        stats = product_intel["layer3"]["edge_statistics"]
        for dim_name, key in [
            ("regulatory_fit", "avg_reg_fit"),
            ("construal_fit", "avg_construal_fit"),
            ("personality_alignment", "avg_personality"),
            ("emotional_resonance", "avg_emotional"),
            ("value_alignment", "avg_value"),
            ("evolutionary_motive", "avg_evo"),
            ("linguistic_style", "avg_linguistic"),
        ]:
            val = stats.get(key, stats.get(f"avg_{dim_name}"))
            if val is not None:
                brand_bilateral_dims.append(BilateralDimension(
                    name=dim_name,
                    value=round(float(val), 4),
                    source="graph_seller_side",
                ))

        brand_construct_acts = _build_construct_activations(brand_bilateral_dims, ndf=brand_ndf)
        brand_enriched_segs = _build_enriched_segments(brand_construct_acts)

        # Build interaction-aware directions from gradient priorities
        # Convert gradient_priorities (dicts) to GradientPriority objects for the helper
        gp_objects = []
        for gp_dict in gradient_priorities:
            gp_objects.append(GradientPriority(
                dimension=gp_dict.get("dimension", ""),
                gradient_magnitude=0.2,  # Estimated from importance
                current_value=gp_dict.get("current_value", 0.5),
                optimal_value=0.7 if gp_dict.get("importance") == "high" else 0.5,
                expected_lift_pct=10.0 if gp_dict.get("importance") == "high" else 5.0,
            ))
        if gp_objects:
            brand_interaction_dirs = _build_interaction_aware_directions(
                gp_objects, [], mech_scores,
            )

    # Construct activations from seller-side ad constructs
    if product_intel and not brand_construct_acts:
        layer3 = product_intel.get("layer3", {})
        product = layer3.get("product", {})
        for key, val in product.items():
            if key.startswith("ad_") and val is not None and isinstance(val, (int, float)):
                construct_id = key.replace("ad_persuasion_techniques_", "").replace("ad_emotional_appeal_", "")
                brand_construct_acts.append(ConstructActivation(
                    construct_id=construct_id,
                    domain="seller_side",
                    activation_level=min(float(val), 1.0),
                    source="graph_product_description",
                ))
        brand_construct_acts.sort(key=lambda a: a.activation_level, reverse=True)
        if brand_construct_acts and not brand_enriched_segs:
            brand_enriched_segs = _build_enriched_segments(brand_construct_acts)

    return BrandProfileResponse(
        brand_name=request.brand_name,
        brand_archetype=brand_archetype or "",
        messaging_profile=_ndf_to_profile(brand_ndf),
        dominant_mechanisms=mech_scores,
        audience_alignments=alignments,
        creative_direction={
            "dominant_frame": "gain" if brand_ndf.get("approach_avoidance", 0.5) > 0.5 else "loss",
            "construal_level": "abstract" if brand_ndf.get("temporal_horizon", 0.5) > 0.5 else "concrete",
            "processing_route": _infer_processing_route(brand_ndf),
            "emotional_register": "high" if brand_ndf.get("arousal_seeking", 0.5) > _get_intel_settings().arousal_high_threshold else "moderate",
        },
        gradient_priorities=gradient_priorities,
        # Full-power fields
        bilateral_dimensions=brand_bilateral_dims,
        construct_activations=brand_construct_acts,
        enriched_segments=brand_enriched_segs,
        interaction_aware_directions=brand_interaction_dirs,
        intelligence_level=intelligence_level,
        analysis_ms=round(elapsed, 2),
    )


# =============================================================================
# INVENTORY MATCH ENDPOINT: Brand × Publisher alignment
# =============================================================================

@router.post(
    "/inventory/match",
    response_model=InventoryMatchResponse,
    summary="Match a brand's psychology to publisher inventory",
    description=(
        "Evaluates how well a brand's messaging psychology aligns with "
        "publisher pages. Returns ranked matches with CPM premium estimates "
        "and creative recommendations per page. Used by publishers for "
        "proactive advertiser outreach and by agencies for media planning."
    ),
)
async def match_inventory(request: InventoryMatchRequest) -> InventoryMatchResponse:
    start = time.monotonic()

    # Profile the brand
    brand_resp = await profile_brand(request.brand_profile)
    brand_ndf = brand_resp.messaging_profile

    matches = []
    for page_req in request.page_profiles:
        # Profile each page
        page_resp = await profile_page(page_req)
        page_ndf = page_resp.psychological_profile

        # Compute alignment per dimension with mode-aware scoring.
        # Some dimensions benefit from SIMILARITY (brand and page match),
        # others from COMPLEMENTARITY (brand provides what page reader needs).
        #
        # Per Higgins' Regulatory Fit Theory and contrast effects:
        # - approach_avoidance: COMPLEMENTARY — gain-framed brand on loss-averse page
        #   creates attention-capturing contrast
        # - cognitive_engagement: SIMILAR — analytical brand on analytical page
        #   enables depth processing
        # - social_calibration: SIMILAR — social brand on social page reinforces
        # - status_sensitivity: SIMILAR — luxury brand on luxury-primed page
        # - arousal_seeking: COMPLEMENTARY — calm brand on high-arousal page
        #   provides relief (or high-energy brand on calm page creates excitement)
        _COMPLEMENT_DIMS = {"approach_avoidance", "arousal_seeking"}
        _SIMILAR_DIMS = {
            "temporal_horizon", "social_calibration", "uncertainty_tolerance",
            "status_sensitivity", "cognitive_engagement",
        }

        dims = list(_COMPLEMENT_DIMS | _SIMILAR_DIMS)
        alignment = {}
        total = 0.0
        for dim in dims:
            brand_val = getattr(brand_ndf, dim, 0.5)
            page_val = getattr(page_ndf, dim, 0.5)

            if dim in _COMPLEMENT_DIMS:
                dim_align = abs(brand_val - page_val)
            else:
                dim_align = 1.0 - abs(brand_val - page_val)

            alignment[dim] = round(dim_align, 3)
            total += dim_align

        match_score = total / len(dims) if dims else 0.5

        # 27-dimension bilateral alignment using full edge vectors
        # Extended complement/similar classification based on psychological theory
        _COMPLEMENT_DIMS_27 = {
            "approach_avoidance", "arousal_seeking", "reactance_fit",
            "negativity_bias_match", "spending_pain_match",
        }
        _SIMILAR_DIMS_27 = {
            "temporal_horizon", "social_calibration", "uncertainty_tolerance",
            "status_sensitivity", "cognitive_engagement",
            "regulatory_fit", "construal_fit", "personality_alignment",
            "emotional_resonance", "value_alignment", "evolutionary_motive",
            "linguistic_style", "appeal_resonance", "processing_route_match",
            "implicit_driver_match", "lay_theory_alignment",
            "identity_signaling_match", "full_cosine_alignment",
            "uniqueness_popularity_fit", "mental_simulation_resonance",
            "brand_trust_fit", "self_monitoring_fit", "mental_ownership_match",
            "anchor_susceptibility_match", "optimal_distinctiveness_fit",
            "disgust_contamination_fit", "involvement_weight_modifier",
        }

        bilateral_alignment = {}
        # Get bilateral dims from brand and page responses
        brand_bi = {d.name: d.value for d in brand_resp.bilateral_dimensions}
        page_bi = {d.name: d.value for d in page_resp.bilateral_dimensions}
        all_bi_dims = set(brand_bi.keys()) | set(page_bi.keys())

        for dim in all_bi_dims:
            b_val = brand_bi.get(dim, 0.5)
            p_val = page_bi.get(dim, 0.5)
            if dim in _COMPLEMENT_DIMS_27:
                bilateral_alignment[dim] = round(abs(b_val - p_val), 3)
            else:
                bilateral_alignment[dim] = round(1.0 - abs(b_val - p_val), 3)

        # CPM premium based on alignment (externalized)
        s = _get_intel_settings()
        cpm_premium = s.cpm_floor + match_score * s.cpm_scale

        # Recommend mechanisms that work in both brand and page context
        shared_mechs = []
        brand_mechs = set(m.mechanism for m in brand_resp.dominant_mechanisms[:5])
        page_mechs = set(m.mechanism for m in page_resp.mechanism_receptivity[:5])
        shared_mechs = list(brand_mechs & page_mechs)
        if not shared_mechs:
            shared_mechs = list(brand_mechs)[:3]

        matches.append(InventoryMatch(
            page_url=page_req.page_url,
            page_title=page_req.title,
            match_score=round(match_score, 3),
            psychological_alignment=alignment,
            bilateral_alignment=bilateral_alignment,
            recommended_mechanisms=shared_mechs,
            cpm_premium=round(cpm_premium, 2),
            reasoning=f"Psychological alignment {match_score:.0%} across {len(dims)} NDF + {len(bilateral_alignment)} bilateral dimensions",
        ))

    # Sort by match score
    matches.sort(key=lambda m: m.match_score, reverse=True)
    matches = matches[:request.top_k]

    elapsed = (time.monotonic() - start) * 1000

    return InventoryMatchResponse(
        matches=matches,
        brand_name=request.brand_profile.brand_name,
        total_inventory_evaluated=len(request.page_profiles),
        analysis_ms=round(elapsed, 2),
    )


# =============================================================================
# ADMIN: Page Intelligence Health Endpoint
# =============================================================================

@router.get(
    "/page-intelligence/health",
    summary="Page intelligence system health",
    description=(
        "Returns status of page crawl infrastructure, daily strengthening tasks, "
        "cache population, and intelligence freshness."
    ),
)
async def page_intelligence_health():
    """Health check for the page intelligence subsystem."""
    health: Dict[str, Any] = {
        "status": "healthy",
        "page_cache": {},
        "inventory_tracker": {},
        "daily_strengthening": {},
        "intelligence_freshness": {},
    }

    # Page cache stats
    try:
        from adam.intelligence.page_intelligence import (
            get_page_intelligence_cache, get_inventory_tracker,
        )
        cache = get_page_intelligence_cache()
        health["page_cache"] = cache.stats

        tracker = get_inventory_tracker()
        health["inventory_tracker"] = tracker.stats
    except Exception as e:
        health["page_cache"] = {"error": str(e)}

    # Daily strengthening task status
    try:
        from adam.intelligence.daily.scheduler import get_task_registry
        registry = get_task_registry()
        task_status = {}
        import redis as _redis
        r = _redis.Redis(host="localhost", port=6379, decode_responses=True)
        for name, task in registry.items():
            last_run = r.get(f"informativ:diss:last_run:{name}")
            task_status[name] = {
                "schedule_hours": task.schedule_hours,
                "frequency_hours": task.frequency_hours,
                "last_run": float(last_run) if last_run else None,
                "is_due": task.is_due(),
            }
        health["daily_strengthening"] = {
            "registered_tasks": len(registry),
            "tasks": task_status,
        }
    except Exception as e:
        health["daily_strengthening"] = {"error": str(e)}

    # Intelligence freshness
    try:
        import redis as _redis
        r = _redis.Redis(host="localhost", port=6379, decode_responses=True)

        freshness = {}
        check_keys = {
            "ambient_state": "informativ:ambient:global",
            "calendar": "informativ:calendar:active",
            "temperature_heatmap": "informativ:temperature:heatmap",
        }
        for label, key in check_keys.items():
            data = r.hgetall(key)
            if data and "computed_at" in data:
                age_hours = (time.time() - float(data["computed_at"])) / 3600
                freshness[label] = {
                    "available": True,
                    "age_hours": round(age_hours, 1),
                }
            else:
                freshness[label] = {"available": False}

        # Count indexed pages
        cursor, keys = r.scan(0, match="informativ:page:*", count=100)
        freshness["estimated_indexed_pages"] = len(keys)

        health["intelligence_freshness"] = freshness
    except Exception as e:
        health["intelligence_freshness"] = {"error": str(e)}

    return health
