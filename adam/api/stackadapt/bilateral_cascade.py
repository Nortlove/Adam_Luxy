"""
Bilateral Cascade Engine — derives creative intelligence from BRAND_CONVERTED edges.

The prediction power comes from the edge, not the archetype label. The edge
dimensions ARE the creative intelligence. This module implements the 5-level
progressive depth cascade:

    Level 1: Archetype Prior         (< 2ms,  in-memory)
    Level 2: Category Posterior      (2-10ms, cached BayesianPrior)
    Level 3: Bilateral Edge Intel    (10-30ms, BRAND_CONVERTED aggregates)
    Level 4: Inferential Transfer    (30-100ms, theory graph traversal)
    Level 5: Full Atom Reasoning     (100-500ms, AoT DAG — future)

Each level returns a CreativeIntelligence result. Higher levels override
lower levels with stronger evidence.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from adam.constants import (
    AD_PERSUASION_PROPERTIES,
    EDGE_DIMENSIONS,
    MECHANISMS,
    resolve_archetype,
)
from adam.intelligence.gradient_fields import (
    GradientIntelligence,
    compute_optimization_priorities,
)
from adam.intelligence.information_value import (
    BuyerUncertaintyProfile,
    InformationValueResult,
    compute_information_value,
)
from adam.config.settings import get_settings

logger = logging.getLogger(__name__)

def _cascade_cfg():
    """Lazy accessor for cascade settings."""
    return get_settings().cascade


# ---------------------------------------------------------------------------
# Result dataclass — what the cascade produces at every level
# ---------------------------------------------------------------------------
@dataclass
class CreativeIntelligence:
    """Creative intelligence derived from the bilateral evidence cascade."""

    # Core creative parameters (derived from evidence, NOT looked up)
    primary_mechanism: str = "social_proof"
    secondary_mechanism: str = "authority"
    framing: str = "gain"               # gain | loss | mixed
    construal_level: str = "moderate"    # concrete | moderate | abstract
    social_proof_density: float = 0.5
    urgency_level: float = 0.3
    tone: str = "balanced"              # warm | balanced | authoritative | urgent
    emotional_intensity: float = 0.5
    copy_length: str = "medium"         # short | medium | long

    # Evidence metadata
    cascade_level: int = 1
    evidence_source: str = "archetype_prior"
    edge_count: int = 0
    confidence: float = 0.3
    sample_size: int = 0

    # Lift estimates (derived from edge composite_alignment)
    ctr_lift_pct: float = 15.0
    conversion_lift_pct: float = 20.0

    # Raw edge dimensions (when available from Level 3+)
    edge_dimensions: Dict[str, float] = field(default_factory=dict)

    # Ad-side profile (when available from Level 3+)
    ad_profile: Dict[str, float] = field(default_factory=dict)

    # Mechanism scores (all mechanisms ranked)
    mechanism_scores: Dict[str, float] = field(default_factory=dict)

    # Gradient intelligence (when gradient field available for this cell)
    gradient_intelligence: Optional[GradientIntelligence] = None

    # Information value bidding (when buyer uncertainty profile available)
    information_value: Optional[InformationValueResult] = None

    # Page context intelligence (when page_url available)
    context_intelligence: Optional[Dict[str, Any]] = None

    # Mechanism portfolio weights (from interaction learner)
    mechanism_portfolio: Optional[List[Dict[str, Any]]] = None

    # Decision probability result (from NDF congruence equation)
    decision_probability: Optional[Any] = None

    # Category deviation from universal (cross-category transfer)
    category_deviation: Optional[Dict[str, float]] = None

    # Reasoning trace
    reasoning: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Edge dimension → creative parameter derivation
# ---------------------------------------------------------------------------
def derive_framing_from_edges(reg_fit: float) -> str:
    """Regulatory fit score → framing direction.

    High regulatory_fit with promotion focus → gain framing.
    The reg_fit score encodes how well the ad's regulatory approach
    matched the buyer's regulatory orientation at time of purchase.
    Values > threshold indicate promotion-focused buyers converted more;
    values < threshold indicate prevention-focused buyers converted more.
    """
    cfg = _cascade_cfg()
    if reg_fit > cfg.framing_promotion_threshold:
        return "gain"
    elif reg_fit < cfg.framing_prevention_threshold:
        return "loss"
    return "mixed"


def derive_construal_from_edges(construal_fit: float) -> str:
    """Construal fit score → construal level recommendation.

    High construal_fit → abstract messaging worked for conversions.
    Low → concrete, feature-specific messaging drove purchases.
    """
    cfg = _cascade_cfg()
    if construal_fit > cfg.construal_abstract_threshold:
        return "abstract"
    elif construal_fit < cfg.construal_concrete_threshold:
        return "concrete"
    return "moderate"


def derive_tone_from_edges(
    emotional_resonance: float, personality_align: float,
) -> str:
    """Emotional resonance + personality alignment → tone.

    High emotional + high personality → warm (personal connection drove sale).
    High emotional + low personality → urgent (emotional pressure drove sale).
    Low emotional + high personality → authoritative (rational match drove sale).
    Low emotional + low personality → balanced (no strong signal).
    """
    cfg = _cascade_cfg()
    if emotional_resonance > cfg.tone_emotion_threshold and personality_align > cfg.tone_personality_threshold:
        return "warm"
    elif emotional_resonance > cfg.tone_emotion_threshold:
        return "urgent"
    elif personality_align > cfg.tone_personality_threshold:
        return "authoritative"
    return "balanced"


def derive_urgency_from_edges(
    emotional_resonance: float, construal_fit: float,
) -> float:
    """Urgency level from emotional intensity + construal concreteness.

    Concrete construal + high emotion → high urgency (0.7-0.9).
    Abstract construal + low emotion → low urgency (0.1-0.3).
    """
    cfg = _cascade_cfg()
    concreteness = 1.0 - construal_fit  # invert: low construal_fit = concrete
    return round(cfg.urgency_concreteness_weight * concreteness + cfg.urgency_emotional_weight * emotional_resonance * concreteness, 2)


def derive_social_proof_density(
    personality_align: float, value_align: float,
) -> float:
    """How much social proof to include.

    High personality alignment → buyer matches brand tribe → social proof resonates.
    High value alignment → rational match → less social proof needed.
    """
    cfg = _cascade_cfg()
    return round(cfg.social_proof_personality_weight * personality_align + cfg.social_proof_value_weight * (1.0 - value_align * cfg.social_proof_value_discount), 2)


def derive_emotional_intensity(
    emotional_resonance: float, evo_motive: float,
) -> float:
    """How emotionally intense the creative should be.

    emotional_resonance: how much emotion drove conversion.
    evolutionary_motive_match: how primal the purchase motivation was.
    """
    cfg = _cascade_cfg()
    return round(cfg.emotional_intensity_emotion_weight * emotional_resonance + cfg.emotional_intensity_evo_weight * evo_motive, 2)


def derive_mechanism_from_ad_profile(
    ad_profile: Dict[str, float],
) -> Tuple[str, str]:
    """Determine primary/secondary mechanism from the ad's own persuasion profile.

    The ProductDescription node stores what Cialdini techniques the product
    page actually uses (ad_persuasion_techniques_*). The dominant technique
    on the ad side is likely the strongest mechanism to activate — because
    the buyer already encountered it on the product page and converted.
    """
    if not ad_profile:
        return "social_proof", "authority"

    # Extract ad persuasion scores
    scores = {}
    for mech, prop_name in AD_PERSUASION_PROPERTIES.items():
        val = ad_profile.get(prop_name, 0.0)
        if val and isinstance(val, (int, float)):
            scores[mech] = float(val)

    if not scores:
        return "social_proof", "authority"

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    primary = ranked[0][0]
    secondary = ranked[1][0] if len(ranked) > 1 else "social_proof"
    return primary, secondary


def derive_lift_from_composite(
    composite: float, confidence: float, edge_count: int,
) -> Tuple[float, float]:
    """Compute CTR and conversion lift from composite alignment.

    Based on Matz et al. (2017): personality-matched advertising delivers
    40-54% conversion lift. We scale by composite alignment strength and
    discount by evidence count.

    Returns (ctr_lift_pct, conversion_lift_pct).
    """
    cfg = _cascade_cfg()
    # Base lift from alignment strength (0.0-1.0 → 0%-54%)
    base_conversion_lift = composite * cfg.matz_conversion_lift_pct
    base_ctr_lift = composite * cfg.matz_ctr_lift_pct

    # Discount for low evidence (full strength at N+ edges)
    evidence_factor = min(1.0, edge_count / cfg.lift_full_evidence_edges)

    # Confidence-weighted
    conf_factor = max(cfg.lift_min_confidence_factor, confidence)

    return (
        round(base_ctr_lift * evidence_factor * conf_factor, 1),
        round(base_conversion_lift * evidence_factor * conf_factor, 1),
    )


# ---------------------------------------------------------------------------
# Level 1: Archetype Prior — population-level, always available
# ---------------------------------------------------------------------------
# Pre-computed from corpus: which mechanisms work best per archetype globally.
# These are the posterior means from Thompson Sampling across all categories.
#
# At startup, load_graph_archetype_priors() replaces these with empirical
# values from RESPONDS_TO edges in Neo4j. The hardcoded values below serve
# as fallback when the graph is unavailable.
_ARCHETYPE_MECHANISM_PRIORS_FALLBACK: Dict[str, Dict[str, float]] = {
    "achiever": {
        "authority": 0.72, "social_proof": 0.68, "commitment": 0.61,
        "scarcity": 0.55, "cognitive_ease": 0.48, "curiosity": 0.45,
        "loss_aversion": 0.52, "liking": 0.40, "reciprocity": 0.38, "unity": 0.35,
    },
    "guardian": {
        "social_proof": 0.78, "commitment": 0.71, "authority": 0.65,
        "loss_aversion": 0.62, "cognitive_ease": 0.55, "reciprocity": 0.48,
        "scarcity": 0.42, "liking": 0.45, "unity": 0.40, "curiosity": 0.35,
    },
    "explorer": {
        "curiosity": 0.75, "cognitive_ease": 0.62, "social_proof": 0.55,
        "authority": 0.50, "liking": 0.52, "scarcity": 0.48,
        "unity": 0.45, "reciprocity": 0.40, "commitment": 0.35, "loss_aversion": 0.30,
    },
    "connector": {
        "liking": 0.76, "social_proof": 0.74, "unity": 0.68,
        "reciprocity": 0.62, "cognitive_ease": 0.55, "commitment": 0.48,
        "authority": 0.42, "curiosity": 0.45, "scarcity": 0.35, "loss_aversion": 0.30,
    },
    "analyst": {
        "cognitive_ease": 0.72, "authority": 0.70, "commitment": 0.62,
        "social_proof": 0.55, "loss_aversion": 0.50, "reciprocity": 0.48,
        "curiosity": 0.52, "scarcity": 0.45, "liking": 0.38, "unity": 0.32,
    },
    "creator": {
        "curiosity": 0.74, "unity": 0.68, "liking": 0.65,
        "cognitive_ease": 0.60, "social_proof": 0.52, "authority": 0.48,
        "reciprocity": 0.45, "scarcity": 0.40, "commitment": 0.35, "loss_aversion": 0.28,
    },
}

# Mutable reference — replaced by load_graph_archetype_priors() at startup
_ARCHETYPE_MECHANISM_PRIORS: Dict[str, Dict[str, float]] = dict(_ARCHETYPE_MECHANISM_PRIORS_FALLBACK)
_PRIORS_SOURCE: str = "hardcoded_fallback"


async def load_graph_archetype_priors(neo4j_driver=None) -> bool:
    """
    Replace hardcoded archetype mechanism priors with empirical values
    from RESPONDS_TO edges in Neo4j.

    Called once at server startup. Returns True if graph priors loaded.
    Falls back to hardcoded values silently if graph unavailable.

    Uses async Neo4j driver (AsyncDriver) since that's what the
    infrastructure provides.
    """
    global _ARCHETYPE_MECHANISM_PRIORS, _PRIORS_SOURCE

    driver = neo4j_driver
    if driver is None:
        try:
            from adam.infrastructure.neo4j.client import get_neo4j_client
            client = get_neo4j_client()
            if client.is_connected:
                driver = client.driver
        except Exception:
            pass

    if driver is None:
        logger.info("Graph unavailable — using hardcoded archetype mechanism priors")
        return False

    try:
        async with driver.session() as session:
            result = await session.run("""
                MATCH (a:CustomerArchetype)-[r:RESPONDS_TO]->(m:CognitiveMechanism)
                WHERE r.effectiveness IS NOT NULL AND r.sample_size > $min_samples
                RETURN a.name AS archetype, m.name AS mechanism,
                       r.effectiveness AS effectiveness,
                       r.sample_size AS sample_size
                ORDER BY a.name, r.effectiveness DESC
            """, min_samples=_cascade_cfg().graph_prior_min_sample_size)
            records = await result.data()

        if not records:
            logger.info("No RESPONDS_TO edges found — using hardcoded priors")
            return False

        graph_priors: Dict[str, Dict[str, float]] = {}
        for rec in records:
            arch = rec["archetype"]
            mech = rec["mechanism"]
            eff = rec["effectiveness"]
            if arch not in graph_priors:
                graph_priors[arch] = {}
            graph_priors[arch][mech] = float(eff)

        if graph_priors:
            # Merge: graph priors override, fallback fills gaps
            for arch, fallback_mechs in _ARCHETYPE_MECHANISM_PRIORS_FALLBACK.items():
                if arch not in graph_priors:
                    graph_priors[arch] = dict(fallback_mechs)
                else:
                    for mech, val in fallback_mechs.items():
                        if mech not in graph_priors[arch]:
                            graph_priors[arch][mech] = val

            _ARCHETYPE_MECHANISM_PRIORS = graph_priors
            _PRIORS_SOURCE = "neo4j_responds_to"
            logger.info(
                "Loaded graph-backed archetype priors: %d archetypes, %d total mechanism scores",
                len(graph_priors),
                sum(len(v) for v in graph_priors.values()),
            )
            return True

    except Exception as e:
        logger.warning("Failed to load graph archetype priors: %s", e)

    return False

# Default creative parameters per archetype (Level 1 baseline)
_ARCHETYPE_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "achiever":  {"framing": "gain",  "construal": "abstract", "tone": "authoritative", "urgency": 0.45},
    "guardian":  {"framing": "loss",  "construal": "concrete", "tone": "warm",          "urgency": 0.30},
    "explorer":  {"framing": "gain",  "construal": "abstract", "tone": "balanced",      "urgency": 0.55},
    "connector": {"framing": "gain",  "construal": "concrete", "tone": "warm",          "urgency": 0.25},
    "analyst":   {"framing": "mixed", "construal": "concrete", "tone": "authoritative", "urgency": 0.35},
    "creator":   {"framing": "gain",  "construal": "abstract", "tone": "balanced",      "urgency": 0.50},
}


def level1_archetype_prior(archetype: str) -> CreativeIntelligence:
    """Level 1: Population-level archetype prior. Always available, < 2ms."""
    archetype = resolve_archetype(archetype)
    priors = _ARCHETYPE_MECHANISM_PRIORS.get(archetype, _ARCHETYPE_MECHANISM_PRIORS["achiever"])
    defaults = _ARCHETYPE_DEFAULTS.get(archetype, _ARCHETYPE_DEFAULTS["achiever"])

    ranked = sorted(priors.items(), key=lambda x: x[1], reverse=True)
    primary = ranked[0][0]
    secondary = ranked[1][0]

    cfg = _cascade_cfg()
    return CreativeIntelligence(
        primary_mechanism=primary,
        secondary_mechanism=secondary,
        framing=defaults["framing"],
        construal_level=defaults["construal"],
        tone=defaults["tone"],
        urgency_level=defaults["urgency"],
        social_proof_density=cfg.l1_social_proof_density_primary if primary == "social_proof" else cfg.l1_social_proof_density_other,
        emotional_intensity=cfg.l1_emotional_intensity,
        cascade_level=1,
        evidence_source="archetype_prior",
        confidence=cfg.l1_confidence,
        mechanism_scores=dict(priors),
        ctr_lift_pct=cfg.l1_ctr_lift,
        conversion_lift_pct=cfg.l1_conversion_lift,
        reasoning=[f"Level 1: archetype={archetype}, primary={primary} (prior={ranked[0][1]:.2f})"],
    )


# ---------------------------------------------------------------------------
# Level 2: Category Posterior — category-specific BayesianPrior nodes
# ---------------------------------------------------------------------------
def level2_category_posterior(
    archetype: str,
    category: str,
    graph_cache: Any,
    base: CreativeIntelligence,
) -> CreativeIntelligence:
    """Level 2: Upgrade with category-specific BayesianPrior posteriors.

    Three-tier fallback:
    1. Category×archetype specific priors (strongest signal)
    2. Universal cross-category priors (psychological invariants)
    3. Stay at Level 1 (only if no BayesianPrior nodes exist at all)

    The cross-category transfer captures psychological invariants:
    "authority works well for achievers" is true across ALL categories.
    Category-specific deviations are layered on top.
    """
    if not graph_cache:
        return base

    # ── Tier 1: Category-specific priors ──
    mech_confidence = None
    evidence_source = "category_posterior"
    transfer_source = ""

    if hasattr(graph_cache, "get_all_mechanism_confidences"):
        mech_confidence = graph_cache.get_all_mechanism_confidences(
            category=category, archetype=archetype,
        )

    # ── Tier 2: Cross-category transfer ──
    # When category-specific priors are missing, fall back to universal
    # priors aggregated across ALL categories. This is dramatically better
    # than Level 1 (hardcoded archetype priors with no empirical signal)
    # because it reflects REAL outcome data pooled across categories.
    if not mech_confidence and hasattr(graph_cache, "get_universal_mechanism_priors"):
        mech_confidence = graph_cache.get_universal_mechanism_priors(
            archetype=archetype,
        )
        if mech_confidence:
            evidence_source = "cross_category_transfer"
            n_cats = next(
                (v.get("categories_pooled", 0) for v in mech_confidence.values()), 0
            )
            transfer_source = f" (universal prior from {n_cats} categories)"

    # ── Tier 3: Similar category transfer ──
    # When category-specific AND universal priors are both missing,
    # borrow from the most psychologically similar category.
    if not mech_confidence and hasattr(graph_cache, "get_similar_categories"):
        similar = graph_cache.get_similar_categories(category, archetype, top_n=1)
        if similar:
            mech_confidence = graph_cache.get_all_mechanism_confidences(
                category=similar[0], archetype=archetype,
            )
            if mech_confidence:
                evidence_source = "similar_category_transfer"
                transfer_source = f" (borrowed from similar category: {similar[0]})"

    if not mech_confidence:
        base.reasoning.append(
            f"Level 2: no BayesianPrior for {archetype}×{category} "
            f"and no universal priors available, staying at L1"
        )
        return base

    # ── Blend posteriors with Level 1 priors ──
    updated_scores = dict(base.mechanism_scores)
    total_obs = 0
    for mech, info in mech_confidence.items():
        posterior_mean = info.get("rate", info.get("posterior_mean", 0.5))
        n_obs = info.get("n_obs", info.get("observation_count", 0))
        total_obs += n_obs

        if mech in updated_scores:
            # Blend: weight by observation count relative to prior.
            # Cross-category transfer uses a lower max weight than
            # category-specific because the signal is less targeted.
            cfg = _cascade_cfg()
            if evidence_source == "category_posterior":
                max_weight = cfg.l2_category_max_blend
            elif evidence_source == "similar_category_transfer":
                max_weight = cfg.l2_similar_category_max_blend
            else:
                max_weight = cfg.l2_cross_category_max_blend
            obs_weight = min(max_weight, n_obs / cfg.l2_observation_divisor)
            updated_scores[mech] = (
                (1.0 - obs_weight) * updated_scores[mech]
                + obs_weight * posterior_mean
            )
        else:
            updated_scores[mech] = posterior_mean

    ranked = sorted(updated_scores.items(), key=lambda x: x[1], reverse=True)

    base.primary_mechanism = ranked[0][0]
    base.secondary_mechanism = ranked[1][0] if len(ranked) > 1 else base.secondary_mechanism
    base.mechanism_scores = dict(updated_scores)
    base.cascade_level = 2
    base.evidence_source = evidence_source
    base.confidence = min(cfg.l2_max_confidence, 0.3 + total_obs / 500.0)
    base.sample_size = total_obs

    # Compute category deviation if we have both category and universal data
    category_deviation = None
    if (
        evidence_source == "category_posterior"
        and hasattr(graph_cache, "get_category_deviation")
    ):
        category_deviation = graph_cache.get_category_deviation(
            category=category, archetype=archetype,
        )
        if category_deviation:
            # Store deviation on the result for response enrichment
            base.category_deviation = category_deviation

            # T1.1: APPLY category deviation to mechanism scores.
            # Previously computed and stored but never consumed.
            # delta > 0 means this mechanism is MORE effective in this category.
            cfg_dev = _cascade_cfg()
            deviations_applied = 0
            for mech, delta in category_deviation.items():
                if mech in base.mechanism_scores:
                    adjusted = base.mechanism_scores[mech] + delta * cfg_dev.category_deviation_weight
                    base.mechanism_scores[mech] = max(0.0, min(1.0, adjusted))
                    deviations_applied += 1
            if deviations_applied:
                # Re-rank after deviation adjustment
                ranked = sorted(base.mechanism_scores.items(), key=lambda x: x[1], reverse=True)
                base.primary_mechanism = ranked[0][0]
                base.secondary_mechanism = ranked[1][0] if len(ranked) > 1 else base.secondary_mechanism
                base.reasoning.append(
                    f"Category deviation applied: {deviations_applied} mechanisms adjusted "
                    f"(weight={cfg_dev.category_deviation_weight})"
                )

    base.reasoning.append(
        f"Level 2: category={category}, source={evidence_source}{transfer_source}, "
        f"{len(mech_confidence)} mechanisms, total_obs={total_obs}, "
        f"primary={ranked[0][0]} ({ranked[0][1]:.3f})"
        + (f", deviations={len(category_deviation)} dims" if category_deviation else "")
    )
    return base


# ---------------------------------------------------------------------------
# Level 3: Bilateral Edge Intelligence — the core innovation
# ---------------------------------------------------------------------------
def level3_bilateral_edges(
    asin: str,
    archetype: str,
    graph_cache: Any,
    base: CreativeIntelligence,
    buyer_id: Optional[str] = None,
) -> CreativeIntelligence:
    """Level 3: Derive creative parameters DIRECTLY from BRAND_CONVERTED edges.

    This is where the bilateral system activates. We query:
    1. The ad-side profile (ProductDescription, 65 properties)
    2. The edge aggregates (BRAND_CONVERTED alignment dimensions)

    Creative parameters come FROM the evidence, not a lookup table.
    """
    if not graph_cache:
        return base

    # Query bilateral evidence
    edge_agg = graph_cache.get_edge_aggregates(asin=asin, archetype=archetype)
    ad_profile = graph_cache.get_product_profile(asin=asin)

    cfg = _cascade_cfg()
    edge_count = edge_agg.get("edge_count", 0) if edge_agg else 0

    if edge_count < cfg.l3_min_edge_count:
        base.reasoning.append(
            f"Level 3: ASIN={asin}, edge_count={edge_count} (< {cfg.l3_min_edge_count} minimum), "
            f"insufficient bilateral evidence"
        )
        return base

    # --- Extract ALL edge dimensions (7 core + 13 extended) ---
    # The 13 extended dimensions map directly to psychological atoms.
    # Using them for mechanism scoring captures signal that the 7 core
    # dimensions alone cannot express.
    #
    # CORE (7): The original bilateral alignment dimensions
    reg_fit = edge_agg.get("avg_reg_fit", 0.5)
    construal_fit = edge_agg.get("avg_construal_fit", 0.5)
    personality_align = edge_agg.get("avg_personality_align", edge_agg.get("avg_personality", 0.5))
    emotional = edge_agg.get("avg_emotional", 0.5)
    value_align = edge_agg.get("avg_value", 0.5)
    evo_motive = edge_agg.get("avg_evo", 0.5)
    composite = edge_agg.get("avg_composite", 0.5)
    std_composite = edge_agg.get("std_composite", 0.15)
    persuasion_conf = edge_agg.get("avg_confidence", edge_agg.get("avg_persuasion_conf", 0.5))

    # EXTENDED (13): Psychological construct dimensions from bilateral annotation
    # Each one corresponds to an atom's primary construct.
    persuasion_susceptibility = edge_agg.get("avg_persuasion_susceptibility", 0.5)
    cognitive_load_tolerance = edge_agg.get("avg_cognitive_load_tolerance", 0.5)
    narrative_transport = edge_agg.get("avg_narrative_transport", 0.5)
    social_proof_sensitivity = edge_agg.get("avg_social_proof_sensitivity", 0.5)
    loss_aversion_intensity = edge_agg.get("avg_loss_aversion_intensity", 0.5)
    temporal_discounting = edge_agg.get("avg_temporal_discounting", 0.5)
    brand_relationship_depth = edge_agg.get("avg_brand_relationship_depth", 0.5)
    autonomy_reactance = edge_agg.get("avg_autonomy_reactance", 0.5)
    information_seeking = edge_agg.get("avg_information_seeking", 0.5)
    mimetic_desire = edge_agg.get("avg_mimetic_desire", 0.5)
    interoceptive_awareness = edge_agg.get("avg_interoceptive_awareness", 0.5)
    cooperative_framing_fit = edge_agg.get("avg_cooperative_framing_fit", 0.5)
    decision_entropy = edge_agg.get("avg_decision_entropy", 0.5)

    # --- Derive creative parameters from edge evidence ---
    # Categorical params (retained for backward compatibility with StackAdapt)
    base.framing = derive_framing_from_edges(reg_fit)
    base.construal_level = derive_construal_from_edges(construal_fit)
    base.tone = derive_tone_from_edges(emotional, personality_align)
    base.urgency_level = derive_urgency_from_edges(emotional, construal_fit)
    base.social_proof_density = derive_social_proof_density(personality_align, value_align)
    base.emotional_intensity = derive_emotional_intensity(emotional, evo_motive)

    # --- Update mechanism scores from FULL 20-dimension edge evidence ---
    # At Level 1-2, mechanism_scores reflect archetype/category priors.
    # At Level 3, we have actual bilateral edge evidence across 20 dimensions.
    # Each mechanism's score is derived from the dimensions that psychologically
    # drive it — not just the 7 core dims, but the 13 extended construct dims.
    #
    # This is the critical difference: we're not guessing which mechanism works
    # from 7 compressed floats. We're using the FULL psychological evidence:
    # - persuasion_susceptibility feeds ALL mechanisms
    # - social_proof_sensitivity directly feeds social_proof
    # - loss_aversion_intensity directly feeds loss_aversion
    # - narrative_transport feeds storytelling/identity_construction
    # - autonomy_reactance penalizes coercive mechanisms
    # - decision_entropy modulates scarcity/urgency
    # - mimetic_desire feeds social_proof/unity
    # - cognitive_load_tolerance gates complex mechanisms (authority, commitment)
    edge_mechanism_adjustments = {
        "authority": (
            0.30 * construal_fit              # deep processing → authority works
            + 0.20 * persuasion_conf           # high confidence → authority trusted
            + 0.15 * (1.0 - emotional)         # calm context → authority credible
            + 0.15 * cognitive_load_tolerance   # can handle complex arguments
            + 0.10 * information_seeking        # wants evidence → authority satisfies
            + 0.10 * (1.0 - autonomy_reactance) # low reactance → accepts authority
        ),
        "social_proof": (
            0.25 * social_proof_sensitivity     # direct construct signal
            + 0.20 * personality_align           # social orientation
            + 0.15 * mimetic_desire              # wants what others want
            + 0.15 * value_align                 # shared values → peer trust
            + 0.15 * emotional                   # emotional → social influence
            + 0.10 * (1.0 - autonomy_reactance)  # open to influence
        ),
        "scarcity": (
            0.25 * loss_aversion_intensity      # fear of missing out
            + 0.20 * emotional                   # high arousal → urgency receptive
            + 0.15 * (1.0 - construal_fit)       # concrete → immediate
            + 0.15 * decision_entropy            # high entropy → scarcity cuts through
            + 0.15 * evo_motive                  # primal competitive instinct
            + 0.10 * (1.0 - temporal_discounting) # present-focused
        ),
        "loss_aversion": (
            0.30 * loss_aversion_intensity      # direct construct signal
            + 0.25 * (1.0 - reg_fit)             # prevention-focused
            + 0.20 * emotional                   # emotional → loss feels worse
            + 0.15 * (1.0 - construal_fit)       # concrete → losses tangible
            + 0.10 * decision_entropy            # uncertain → risk-averse
        ),
        "commitment": (
            0.25 * value_align                  # shared values → commitment
            + 0.20 * brand_relationship_depth    # existing relationship
            + 0.20 * (1.0 - emotional)           # calm → deliberate commitment
            + 0.15 * construal_fit               # abstract → principle-based
            + 0.10 * cognitive_load_tolerance    # can process complex asks
            + 0.10 * cooperative_framing_fit     # fairness → reciprocal commitment
        ),
        "liking": (
            0.25 * personality_align            # personality match → liking
            + 0.20 * emotional                   # emotional → affective liking
            + 0.20 * brand_relationship_depth    # relationship → warmth
            + 0.15 * evo_motive                  # attractiveness/status
            + 0.10 * interoceptive_awareness     # body-felt positive response
            + 0.10 * cooperative_framing_fit     # perceived fairness
        ),
        "cognitive_ease": (
            0.30 * (1.0 - cognitive_load_tolerance) # low tolerance → needs simplicity
            + 0.25 * (1.0 - construal_fit)           # concrete → simple
            + 0.20 * (1.0 - information_seeking)     # doesn't want details
            + 0.15 * (1.0 - emotional)               # calm → effortless processing
            + 0.10 * value_align                     # familiar values → easy
        ),
        "curiosity": (
            0.25 * information_seeking           # direct construct signal
            + 0.20 * construal_fit                # abstract → exploration
            + 0.20 * narrative_transport          # story engagement → curious
            + 0.15 * evo_motive                   # novelty-seeking
            + 0.10 * (1.0 - personality_align)    # unfamiliar → intriguing
            + 0.10 * cognitive_load_tolerance     # can handle new info
        ),
        "reciprocity": (
            0.30 * cooperative_framing_fit       # direct construct signal
            + 0.25 * value_align                  # shared values → fair exchange
            + 0.20 * personality_align            # social → reciprocal norms
            + 0.15 * (1.0 - autonomy_reactance)  # accepts social obligations
            + 0.10 * brand_relationship_depth     # existing relationship → debt
        ),
        "unity": (
            0.25 * mimetic_desire                # in-group desire
            + 0.25 * personality_align            # social identity
            + 0.20 * value_align                  # shared values → belonging
            + 0.15 * emotional                    # emotional → identity resonance
            + 0.15 * cooperative_framing_fit      # community orientation
        ),
    }

    # ── T3.2: Cross-Dimensional Interaction Modeling ──
    # Psychology shows interaction effects: high social_calibration +
    # high status_sensitivity boosts identity_construction more than
    # either alone. Apply the 12 theory-driven interaction pairs from
    # gradient_fields.py as additional adjustment factors.
    interaction_adjustments: Dict[str, float] = {}
    try:
        # Pre-defined interaction pairs and their mechanism targets
        _INTERACTION_MECHANISM_MAP = {
            # (dim_a, dim_b) → (target_mechanism, direction)
            # direction > 0: interaction amplifies the mechanism
            # direction < 0: interaction suppresses the mechanism
            ("social_proof_sensitivity", "personality_align"): ("social_proof", 1.0),
            ("loss_aversion_intensity", "emotional"): ("loss_aversion", 1.0),
            ("autonomy_reactance", "persuasion_susceptibility"): ("authority", -1.0),
            ("narrative_transport", "construal_fit"): ("curiosity", 1.0),
            ("information_seeking", "cognitive_load_tolerance"): ("authority", 1.0),
            ("mimetic_desire", "value_align"): ("unity", 1.0),
            ("temporal_discounting", "emotional"): ("scarcity", 1.0),
            ("decision_entropy", "social_proof_sensitivity"): ("social_proof", 1.0),
            ("cooperative_framing_fit", "personality_align"): ("reciprocity", 1.0),
            ("brand_relationship_depth", "mimetic_desire"): ("commitment", 1.0),
            ("reg_fit", "emotional"): ("loss_aversion", 1.0),
            ("construal_fit", "cognitive_load_tolerance"): ("cognitive_ease", -1.0),
        }

        # Local namespace for dimension values
        dim_vals = {
            "reg_fit": reg_fit, "construal_fit": construal_fit,
            "personality_align": personality_align, "emotional": emotional,
            "value_align": value_align, "evo_motive": evo_motive,
            "persuasion_susceptibility": persuasion_susceptibility,
            "cognitive_load_tolerance": cognitive_load_tolerance,
            "narrative_transport": narrative_transport,
            "social_proof_sensitivity": social_proof_sensitivity,
            "loss_aversion_intensity": loss_aversion_intensity,
            "temporal_discounting": temporal_discounting,
            "brand_relationship_depth": brand_relationship_depth,
            "autonomy_reactance": autonomy_reactance,
            "information_seeking": information_seeking,
            "mimetic_desire": mimetic_desire,
            "interoceptive_awareness": interoceptive_awareness,
            "cooperative_framing_fit": cooperative_framing_fit,
            "decision_entropy": decision_entropy,
        }

        for (dim_a, dim_b), (target_mech, direction) in _INTERACTION_MECHANISM_MAP.items():
            val_a = dim_vals.get(dim_a, 0.5)
            val_b = dim_vals.get(dim_b, 0.5)
            # Interaction term: product of deviations from 0.5
            interaction = (val_a - 0.5) * (val_b - 0.5) * 4.0  # Scale to [-1, 1]
            # Apply as adjustment to target mechanism
            adj = interaction * direction * 0.08  # Conservative 8% max adjustment
            interaction_adjustments[target_mech] = (
                interaction_adjustments.get(target_mech, 0.0) + adj
            )
    except Exception as e:
        logger.debug("Cross-dimensional interaction modeling skipped: %s", e)

    # Blend edge-derived scores with prior scores at L3
    edge_w = cfg.l3_edge_prior_blend
    prior_w = 1.0 - edge_w
    for mech, edge_score in edge_mechanism_adjustments.items():
        prior_score = base.mechanism_scores.get(mech, 0.5)
        # Apply interaction adjustments on top of blended score
        interaction_adj = interaction_adjustments.get(mech, 0.0)
        blended = edge_w * edge_score + prior_w * prior_score + interaction_adj
        base.mechanism_scores[mech] = round(max(0.0, min(1.0, blended)), 4)

    # Re-rank mechanisms after edge evidence update
    ranked_after_edges = sorted(base.mechanism_scores.items(), key=lambda x: x[1], reverse=True)

    # Ad profile MODULATES the edge-ranked mechanisms, not overrides them.
    # If ad uses authority heavily AND edge evidence supports authority, double-confirm.
    # If ad uses authority but edges say liking works better, edges win (evidence > intent).
    if ad_profile:
        ad_primary, ad_secondary = derive_mechanism_from_ad_profile(ad_profile)
        base.ad_profile = ad_profile

        # Boost ad-endorsed mechanisms (the ad was designed this way for a reason)
        if ad_primary in base.mechanism_scores:
            base.mechanism_scores[ad_primary] = min(1.0, base.mechanism_scores[ad_primary] * cfg.l3_ad_primary_boost)
        if ad_secondary in base.mechanism_scores:
            base.mechanism_scores[ad_secondary] = min(1.0, base.mechanism_scores[ad_secondary] * cfg.l3_ad_secondary_boost)

        # Re-rank again after ad boost
        ranked_after_edges = sorted(base.mechanism_scores.items(), key=lambda x: x[1], reverse=True)

    base.primary_mechanism = ranked_after_edges[0][0]
    base.secondary_mechanism = ranked_after_edges[1][0] if len(ranked_after_edges) > 1 else base.secondary_mechanism

    # --- Decision Probability (the core equation) ---
    # Compute P(purchase) using the NDF congruence equation from
    # NONCONSCIOUS_DECISION_MODELS.md. This replaces the fixed Matz constants
    # with a proper congruence-based probability estimate.
    try:
        from adam.intelligence.decision_probability import (
            compute_decision_probability,
            extract_message_features,
        )

        # Pass ALL edge dimensions to decision probability — no NDF compression.
        # The 7-dim buyer_ndf was a bottleneck that discarded 13 extended dims.
        # The decision equation accepts any number of dimensions and weights them
        # by gradient magnitude when available.
        buyer_profile = dict(base.edge_dimensions) if hasattr(base, 'edge_dimensions') else {}
        if not buyer_profile:
            # Fallback: construct from core dims if edge_dimensions not populated
            buyer_profile = {
                "regulatory_fit": reg_fit,
                "construal_fit": construal_fit,
                "personality_alignment": personality_align,
                "emotional_resonance": emotional,
                "value_alignment": value_align,
                "evolutionary_motive": evo_motive,
            }

        # Also provide the legacy 7-dim NDF mapping for backward compatibility
        # with the existing match functions in decision_probability.py
        buyer_ndf = {
            "approach_avoidance": 2.0 * reg_fit - 1.0,
            "temporal_horizon": construal_fit,
            "social_calibration": personality_align,
            "uncertainty_tolerance": 1.0 - emotional * 0.5,
            "status_sensitivity": value_align,
            "cognitive_engagement": construal_fit,
            "arousal_seeking": emotional * 0.7 + evo_motive * 0.3,
        }

        message_features = extract_message_features(
            edge_dimensions=base.edge_dimensions if hasattr(base, 'edge_dimensions') else None,
            ad_profile=ad_profile,
            mechanism_scores=base.mechanism_scores,
        )

        category_for_dp = ad_profile.get("category", "") if ad_profile else ""
        dp_result = compute_decision_probability(
            buyer_ndf=buyer_ndf,
            message_features=message_features,
            category=category_for_dp,
            # Pass the full edge profile for extended matching
            buyer_edge_dimensions=buyer_profile,
        )

        # Use decision probability for lift estimation (replaces fixed Matz constants)
        base.ctr_lift_pct = round(dp_result.purchase_probability * 40.0, 1)
        base.conversion_lift_pct = round(dp_result.purchase_probability * 54.0, 1)

        # Store continuous creative weights (these supplement the categorical params)
        base.decision_probability = dp_result

    except Exception as e:
        logger.debug("Decision probability computation skipped: %s", e)
        # Fallback to Matz constants
        ctr_lift, conv_lift = derive_lift_from_composite(composite, persuasion_conf, edge_count)
        base.ctr_lift_pct = ctr_lift
        base.conversion_lift_pct = conv_lift

    # Store ALL 20 dimensions for downstream consumers (gradient fields, IV, copy gen)
    # Previously only stored 9 dimensions — losing 55% of the bilateral signal.
    base.edge_dimensions = {
        # 7 core alignment dimensions
        "regulatory_fit": reg_fit,
        "construal_fit": construal_fit,
        "personality_alignment": personality_align,
        "emotional_resonance": emotional,
        "value_alignment": value_align,
        "evolutionary_motive": evo_motive,
        "linguistic_style": edge_agg.get("avg_linguistic", 0.5),
        # Derived
        "composite_alignment": composite,
        "composite_std": std_composite,
        "persuasion_confidence": persuasion_conf,
        # 13 extended psychological construct dimensions
        "persuasion_susceptibility": persuasion_susceptibility,
        "cognitive_load_tolerance": cognitive_load_tolerance,
        "narrative_transport": narrative_transport,
        "social_proof_sensitivity": social_proof_sensitivity,
        "loss_aversion_intensity": loss_aversion_intensity,
        "temporal_discounting": temporal_discounting,
        "brand_relationship_depth": brand_relationship_depth,
        "autonomy_reactance": autonomy_reactance,
        "information_seeking": information_seeking,
        "mimetic_desire": mimetic_desire,
        "interoceptive_awareness": interoceptive_awareness,
        "cooperative_framing_fit": cooperative_framing_fit,
        "decision_entropy": decision_entropy,
    }

    # Update metadata
    base.cascade_level = 3
    base.evidence_source = "bilateral_edges"
    base.edge_count = edge_count
    base.confidence = min(0.9, persuasion_conf * min(1.0, edge_count / cfg.l3_confidence_edge_norm))
    base.sample_size = edge_count

    # Copy length from construal (abstract → longer narrative, concrete → short punchy)
    if base.construal_level == "abstract":
        base.copy_length = "long"
    elif base.construal_level == "concrete":
        base.copy_length = "short"

    # --- Gradient Field Intelligence ---
    # If we have a pre-computed gradient for this (archetype, category) cell,
    # compute optimization priorities: which dimensions to adjust for maximum lift.
    if hasattr(graph_cache, "get_gradient_field"):
        category_for_gradient = ""
        if ad_profile:
            category_for_gradient = ad_profile.get("category", "")
        gradient = graph_cache.get_gradient_field(archetype, category_for_gradient)
        if gradient and gradient.is_valid:
            base.gradient_intelligence = compute_optimization_priorities(
                gradient=gradient,
                current_alignment=base.edge_dimensions,
                top_n=3,
            )
            top_dim = base.gradient_intelligence.optimization_priorities[0] if base.gradient_intelligence.optimization_priorities else None
            base.reasoning.append(
                f"Gradient field: {gradient.n_edges} edges, R²={gradient.r_squared:.2f}, "
                f"top priority: {top_dim.dimension} (Δlift={top_dim.expected_lift_delta:+.1f}%)"
                if top_dim else "Gradient field: computed but no priorities"
            )

    # --- Information Value Bidding ---
    # If we have a buyer ID and can look up their uncertainty profile,
    # compute how much extra to bid for the learning value of this impression.
    if buyer_id and hasattr(graph_cache, "get_buyer_profile"):
        buyer_profile = graph_cache.get_buyer_profile(buyer_id=buyer_id)
        if buyer_profile:
            gradient_for_iv = None
            if base.gradient_intelligence and hasattr(graph_cache, "get_gradient_field"):
                category_for_iv = ad_profile.get("category", "") if ad_profile else ""
                gradient_for_iv = graph_cache.get_gradient_field(archetype, category_for_iv)

            iv_result = compute_information_value(
                buyer=buyer_profile,
                gradient_field=gradient_for_iv,
            )
            base.information_value = iv_result
            base.reasoning.append(
                f"Information value: exploration={iv_result.exploration_priority}, "
                f"bid_premium=${iv_result.recommended_bid_premium:.2f}/CPM, "
                f"buyer_confidence={iv_result.buyer_confidence:.2f}"
            )

    base.reasoning.append(
        f"Level 3 BILATERAL: ASIN={asin}, edges={edge_count}, "
        f"composite={composite:.3f}±{std_composite:.3f}, "
        f"reg_fit={reg_fit:.2f}→{base.framing}, "
        f"construal={construal_fit:.2f}→{base.construal_level}, "
        f"emotion={emotional:.2f}→tone={base.tone}, "
        f"primary={base.primary_mechanism}, "
        f"lift={base.conversion_lift_pct:.1f}%"
    )

    return base


# ---------------------------------------------------------------------------
# Level 4: Inferential Transfer — theory graph for low-evidence products
# ---------------------------------------------------------------------------
def level4_inferential_transfer(
    asin: str,
    archetype: str,
    graph_cache: Any,
    base: CreativeIntelligence,
) -> CreativeIntelligence:
    """Level 4: Use the ad-side profile + theory graph for zero-shot inference.

    When edge_count < 10 but we have the ProductDescription node, we can
    reason: the ad uses authority techniques → authority activates need for
    expertise validation → achievers respond to expertise → recommend authority.

    This is the inferential chain from the MechanismActivationAtom.
    """
    if not graph_cache:
        return base

    ad_profile = graph_cache.get_product_profile(asin=asin)
    if not ad_profile:
        base.reasoning.append(f"Level 4: no ProductDescription for ASIN={asin}")
        return base

    # Derive mechanism from ad's own persuasion profile
    ad_primary, ad_secondary = derive_mechanism_from_ad_profile(ad_profile)

    # Extract ad-side framing signals
    ad_framing = {}
    for key, val in ad_profile.items():
        if key.startswith("ad_frame_") or key.startswith("ad_construal_"):
            ad_framing[key] = val

    # Infer framing from ad-side constructs
    gain_signal = ad_framing.get("ad_frame_gain", 0.0) or 0.0
    loss_signal = ad_framing.get("ad_frame_loss", 0.0) or 0.0
    abstract_signal = ad_framing.get("ad_construal_abstract", 0.0) or 0.0
    concrete_signal = ad_framing.get("ad_construal_concrete", 0.0) or 0.0

    cfg = _cascade_cfg()
    if gain_signal > loss_signal + cfg.l4_signal_differentiation:
        base.framing = "gain"
    elif loss_signal > gain_signal + cfg.l4_signal_differentiation:
        base.framing = "loss"

    if abstract_signal > concrete_signal + cfg.l4_signal_differentiation:
        base.construal_level = "abstract"
    elif concrete_signal > abstract_signal + cfg.l4_signal_differentiation:
        base.construal_level = "concrete"

    base.primary_mechanism = ad_primary
    base.secondary_mechanism = ad_secondary
    base.ad_profile = ad_profile
    base.cascade_level = 4
    base.evidence_source = "inferential_transfer"
    base.confidence = min(0.5, base.confidence + cfg.l4_confidence_increment)

    base.reasoning.append(
        f"Level 4 INFERENTIAL: ASIN={asin}, ad uses {ad_primary} "
        f"(score={ad_profile.get(AD_PERSUASION_PROPERTIES.get(ad_primary, ''), 0):.2f}), "
        f"ad_framing={'gain' if gain_signal > loss_signal else 'loss'}, "
        f"inferred construal={'abstract' if abstract_signal > concrete_signal else 'concrete'}"
    )

    return base


# ---------------------------------------------------------------------------
# Context modulation — applied after cascade level determination
# ---------------------------------------------------------------------------
def apply_context_modulation(
    result: CreativeIntelligence,
    device_type: Optional[str] = None,
    time_of_day: Optional[int] = None,
    iab_category: Optional[str] = None,
    page_url: Optional[str] = None,
    # Additional bid request signals for impression state resolver
    page_title: str = "",
    referrer: str = "",
    keywords: Optional[List[str]] = None,
    iab_categories: Optional[List[str]] = None,
    # Segment ID for goal activation crossover scoring
    segment_id: str = "",
) -> CreativeIntelligence:
    """Apply contextual adjustments to the cascade result.

    Three signal sources:
    1. Device type (mobile → short copy)
    2. Time of day (commute → urgency, late night → reduced urgency)
    3. Page context intelligence (domain mindset → mechanism adjustments,
       tone, complexity). This is the trilateral resonance layer: the
       page creates a psychological field that modulates how the buyer
       interacts with the ad creative.
    """
    # --- Device modulation ---
    if device_type == "mobile":
        result.copy_length = "short"
        result.reasoning.append("Context: mobile → short copy")

    # --- Temporal modulation ---
    cfg = _cascade_cfg()
    if time_of_day is not None:
        if time_of_day >= cfg.late_night_start_hour or time_of_day <= cfg.late_night_end_hour:
            result.urgency_level *= cfg.late_night_urgency_multiplier
            result.reasoning.append(f"Context: late night (hour={time_of_day}) → urgency ×{cfg.late_night_urgency_multiplier}")
        elif 7 <= time_of_day <= 9:
            result.urgency_level = min(1.0, result.urgency_level * cfg.morning_urgency_multiplier)
            result.reasoning.append(f"Context: morning commute → urgency ×{cfg.morning_urgency_multiplier}")

    # --- Page context intelligence ---
    # Three-tier page profiling:
    # 1. Page-level (pre-crawled, Redis) — specific article/page psychology
    # 2. Domain-level (698K mappings) — "nytimes.com → informed mindset"
    # 3. Heuristic (keyword inference) — fallback for unknown domains
    #
    # The page where the ad appears primes the buyer's cognitive state.
    # A news article about inflation creates anxiety + prevention-focus.
    # A product comparison page creates analytical + high-engagement.
    # This is the difference between optimizing for WHO the buyer is
    # vs WHERE the buyer is RIGHT NOW.

    # ── NEW: Impression State Resolver (signal composition) ──
    # Runs ALONGSIDE the old page profile lookup. Both produce results.
    # The resolver composes ALL bid request signals (title, referrer,
    # keywords, IAB, domain, device, time) into a 20-dim position vector.
    # Results are stored for A/B comparison against the old system.
    reader_position = None
    try:
        from adam.intelligence.impression_state_resolver import resolve_reader_position
        reader_position = resolve_reader_position(
            page_url=page_url or "",
            page_title=page_title,
            referrer=referrer,
            keywords=keywords,
            iab_categories=iab_categories or ([iab_category] if iab_category else None),
            domain="",  # Auto-extracted from URL
            device_type=device_type or "",
            time_of_day=time_of_day if time_of_day is not None else -1,
        )
        if reader_position and reader_position.confidence > 0:
            # Store for comparison and potential use
            if not result.context_intelligence:
                result.context_intelligence = {}
            result.context_intelligence["reader_position"] = {
                "dimensions": reader_position.dimensions,
                "confidence": reader_position.confidence,
                "signals_used": reader_position.signals_used,
                "resolution_summary": reader_position.resolution_summary,
            }
            result.reasoning.append(
                f"ImpressionResolver: {reader_position.resolution_summary}"
            )
    except Exception as e:
        pass  # Resolver not available — old system continues

    # Tier 1: Check pre-indexed page intelligence cache (page-level)
    # Uses ALL 8 layers of the PagePsychologicalProfile to influence
    # mechanism selection, creative parameters, and persuasion framing.
    # NOTE: This is the OLD system. Runs alongside the new resolver.
    page_profile = None
    if page_url:
        try:
            from adam.intelligence.page_intelligence import get_page_intelligence_cache
            page_cache = get_page_intelligence_cache()
            page_profile = page_cache.lookup(page_url)
            if page_profile and page_profile.confidence > cfg.page_confidence_floor:
                pp = page_profile  # shorthand

                # ── EMPIRICAL: Page-conditioned graph query ──
                # Ask the graph: "among 47M bilateral edges, which conversions
                # happened when the buyer was in a state similar to what THIS
                # page creates?" The answer is empirical mechanism effectiveness.
                if pp.edge_dimensions and result.mechanism_scores:
                    try:
                        from adam.intelligence.page_conditioned_query import (
                            query_causal_effects,
                        )
                        import asyncio
                        # Check for discovered causal effects from the self-teaching loop
                        for mech in list(result.mechanism_scores.keys()):
                            try:
                                # Use thread-safe approach to avoid event loop conflicts
                                try:
                                    loop = asyncio.get_running_loop()
                                    # Already in async context — run in executor
                                    import concurrent.futures
                                    with concurrent.futures.ThreadPoolExecutor() as pool:
                                        causal_effects = pool.submit(
                                            asyncio.run, query_causal_effects(mech)
                                        ).result(timeout=2.0)
                                except RuntimeError:
                                    # No running loop — safe to use asyncio.run
                                    causal_effects = asyncio.run(
                                        query_causal_effects(mech)
                                    )
                            except RuntimeError:
                                causal_effects = {}

                            for dim, effect in causal_effects.items():
                                page_val = pp.edge_dimensions.get(dim, 0.5)
                                if effect["type"] == "amplifies" and page_val > 0.6:
                                    boost = 1.0 + effect["strength"] * 0.15
                                    result.mechanism_scores[mech] = min(1.0, result.mechanism_scores[mech] * boost)
                                    result.reasoning.append(
                                        f"Causal: {dim}={page_val:.2f} AMPLIFIES {mech} "
                                        f"(d={effect['strength']:.2f}, n={effect['n']})"
                                    )
                                elif effect["type"] == "suppresses" and page_val > 0.6:
                                    dampen = max(0.5, 1.0 - effect["strength"] * 0.15)
                                    result.mechanism_scores[mech] *= dampen
                                    result.reasoning.append(
                                        f"Causal: {dim}={page_val:.2f} SUPPRESSES {mech} "
                                        f"(d={effect['strength']:.2f}, n={effect['n']})"
                                    )
                    except Exception as e:
                        pass  # Causal effects not available yet — graceful degradation

                # ── LAYER 6: Persuasion channel gating ──
                # HARD gate: if a channel is CLOSED, reduce it significantly.
                # SOFT boost: if a channel is OPEN, amplify it.
                # This is the most critical layer: it determines which
                # mechanisms will RESONATE vs BACKFIRE on this specific page.
                if result.mechanism_scores:
                    for ch in pp.open_channels:
                        if ch in result.mechanism_scores:
                            result.mechanism_scores[ch] = min(1.0, result.mechanism_scores[ch] * cfg.page_open_channel_boost)
                    for ch in pp.closed_channels:
                        if ch in result.mechanism_scores:
                            result.mechanism_scores[ch] *= cfg.page_closed_channel_dampen

                    # Apply numeric mechanism adjustments (from NDF sigmoid)
                    for mech, multiplier in pp.mechanism_adjustments.items():
                        if mech in result.mechanism_scores:
                            result.mechanism_scores[mech] *= multiplier

                # ── LAYER 8: Decision-making style → creative parameters ──
                ds = pp.primed_decision_style
                if ds:
                    # ELM route → copy length and detail
                    elm = ds.get("elm_route", "mixed")
                    if elm == "central":
                        if result.copy_length == "short":
                            result.copy_length = "medium"
                        result.construal_level = "concrete"
                    elif elm == "peripheral":
                        if result.copy_length == "long":
                            result.copy_length = "short"

                    # Risk orientation → framing override
                    risk = ds.get("risk_orientation", "balanced")
                    if risk == "risk_averse" and result.framing == "gain":
                        # Page primed risk-aversion but cascade says gain framing
                        # Compromise: shift toward mixed (don't fully override evidence)
                        result.framing = "mixed"
                    elif risk == "risk_seeking" and result.framing == "loss":
                        result.framing = "mixed"

                    # Decision speed → urgency
                    speed = ds.get("decision_speed", "moderate")
                    if speed == "impulsive":
                        result.urgency_level = min(1.0, result.urgency_level * 1.3)
                    elif speed == "deliberative":
                        result.urgency_level *= 0.7

                # ── LAYER 1: Activated needs → mechanism alignment ──
                if pp.activated_needs and result.mechanism_scores:
                    # Boost mechanisms that align with the page's activated needs
                    _NEED_MECHANISM_MAP = {
                        "security": ["loss_aversion", "commitment", "authority"],
                        "belonging": ["social_proof", "unity", "liking"],
                        "competence": ["authority", "cognitive_ease", "commitment"],
                        "status": ["scarcity", "authority"],
                        "health_concern": ["authority", "commitment", "loss_aversion"],
                        "financial_security": ["authority", "commitment", "loss_aversion"],
                        "self_improvement": ["curiosity", "commitment", "cognitive_ease"],
                        "problem_solving": ["authority", "cognitive_ease", "curiosity"],
                    }
                    for need, strength in pp.activated_needs.items():
                        aligned_mechs = _NEED_MECHANISM_MAP.get(need, [])
                        for mech in aligned_mechs:
                            if mech in result.mechanism_scores:
                                boost = 1.0 + strength * cfg.need_mechanism_boost_max
                                result.mechanism_scores[mech] = min(1.0, result.mechanism_scores[mech] * boost)

                # ── LAYER 3: Cognitive state → bandwidth-aware messaging ──
                if pp.remaining_bandwidth < cfg.low_bandwidth_threshold:
                    result.copy_length = "short"
                    result.construal_level = "concrete"

                # ── LAYER 4: Credibility → authority mechanism boost ──
                if pp.publisher_authority > cfg.publisher_authority_threshold:
                    if "authority" in result.mechanism_scores:
                        result.mechanism_scores["authority"] = min(
                            1.0, result.mechanism_scores["authority"] * cfg.publisher_authority_boost
                        )

                # ── LAYER 2: Emotional field → tone ──
                if pp.dominant_emotions:
                    top_emotion = pp.dominant_emotions[0]
                    if top_emotion in ("anxiety", "fear") and result.tone == "balanced":
                        result.tone = "reassuring, protective"
                    elif top_emotion in ("excitement", "curiosity") and result.tone == "balanced":
                        result.tone = "energetic, compelling"
                    elif top_emotion == "trust" and result.tone == "balanced":
                        result.tone = "confident, trustworthy"
                elif pp.optimal_tone and result.tone == "balanced":
                    result.tone = pp.optimal_tone

                # ── TEMPORAL DRIFT: Adjust for mechanism effectiveness trends ──
                # Declining mechanisms get dampened; rising mechanisms get boosted.
                # This prevents the system from riding a declining mechanism
                # until it stops working — it proactively shifts.
                if result.mechanism_scores:
                    try:
                        from adam.intelligence.advanced_learning import get_mechanism_drift
                        for mech in list(result.mechanism_scores.keys()):
                            drift = get_mechanism_drift(mech)
                            if drift and drift["confidence"] > 0.3:
                                if drift["trend"] == "declining":
                                    # Dampen declining mechanisms (max 20% reduction)
                                    dampen = max(0.80, 1.0 + drift["slope"] * 10)
                                    result.mechanism_scores[mech] *= dampen
                                    result.reasoning.append(
                                        f"Drift: {mech} declining (slope={drift['slope']:.4f}) → ×{dampen:.2f}"
                                    )
                                elif drift["trend"] == "rising":
                                    # Boost rising mechanisms (max 15% boost)
                                    boost = min(1.15, 1.0 + drift["slope"] * 10)
                                    result.mechanism_scores[mech] *= boost
                                    result.reasoning.append(
                                        f"Drift: {mech} rising (slope={drift['slope']:.4f}) → ×{boost:.2f}"
                                    )
                    except Exception:
                        pass

                # ── Re-rank mechanisms after all page-context adjustments ──
                if result.mechanism_scores:
                    ranked = sorted(result.mechanism_scores.items(), key=lambda x: x[1], reverse=True)
                    if len(ranked) >= 1:
                        result.primary_mechanism = ranked[0][0]
                    if len(ranked) >= 2:
                        result.secondary_mechanism = ranked[1][0]

                # ── Build full context intelligence for response ──
                result.context_intelligence = {
                    "domain": pp.domain,
                    "mindset": pp.mindset,
                    "attention_level": "high" if pp.cognitive_load > 0.6 else ("low" if pp.cognitive_load < 0.3 else "medium"),
                    "purchase_intent": pp.funnel_stage_signal or (
                        "ready" if pp.purchase_intent_signal > 0.7
                        else "considering" if pp.purchase_intent_signal > 0.3
                        else "browsing"
                    ),
                    "mechanism_adjustments": pp.mechanism_adjustments,
                    "recommended_mechanisms": pp.open_channels,
                    "avoid_mechanisms": pp.closed_channels + pp.avoid_tactics,
                    "optimal_tone": pp.optimal_tone,
                    "recommended_complexity": pp.recommended_complexity,
                    "confidence": pp.confidence,
                    "emotional_valence": pp.emotional_valence,
                    "emotional_arousal": pp.emotional_arousal,
                    "cognitive_load": pp.cognitive_load,
                    "content_type": pp.content_type,
                    "primary_topic": pp.primary_topic,
                    "profile_source": pp.profile_source,
                    # New layers surfaced to StackAdapt
                    "activated_needs": pp.activated_needs,
                    "dominant_emotions": pp.dominant_emotions,
                    "emotional_trajectory": pp.emotional_trajectory,
                    "primed_decision_style": pp.primed_decision_style,
                    "open_channels": pp.open_channels,
                    "closed_channels": pp.closed_channels,
                    "channel_reasoning": pp.channel_reasoning,
                    "publisher_authority": pp.publisher_authority,
                    "remaining_bandwidth": pp.remaining_bandwidth,
                    "primed_categories": pp.primed_categories,
                    "recommended_ad_strategy": pp.recommended_ad_strategy,
                    # 20-dim page edge profile for causal learning
                    "page_edge_dimensions": pp.edge_dimensions,
                    "page_edge_scoring_tier": pp.edge_scoring_tier,
                    "page_confidence": pp.confidence,
                }

                # Reasoning
                n_open = len(pp.open_channels)
                n_closed = len(pp.closed_channels)
                top_need = list(pp.activated_needs.keys())[0] if pp.activated_needs else "none"
                ds_speed = ds.get("decision_speed", "unknown") if ds else "unknown"
                result.reasoning.append(
                    f"Context: 8-layer page profile for {pp.url_pattern} "
                    f"(mindset={pp.mindset}, decision_style={ds_speed}, "
                    f"top_need={top_need}, open={n_open} closed={n_closed} channels, "
                    f"authority={pp.publisher_authority:.1f}, conf={pp.confidence:.2f})"
                )
        except Exception as e:
            logger.debug("Page intelligence cache lookup skipped: %s", e)

    # Tier 2+3: Fall back to domain-level if no page profile found
    domain = _extract_domain(page_url) if page_url else None
    if domain and not page_profile:
        try:
            from adam.intelligence.context_intelligence import get_context_intelligence_service
            ctx_service = get_context_intelligence_service()
            ctx = ctx_service.get_context_recommendation(domain)

            if ctx and ctx.get("confidence", 0) > 0.2:
                mindset = ctx.get("mindset", "unknown")
                adjustments = ctx.get("mechanism_adjustments", {})

                # Apply mechanism adjustments to scores
                if result.mechanism_scores and adjustments:
                    for mech, multiplier in adjustments.items():
                        if mech in result.mechanism_scores:
                            old = result.mechanism_scores[mech]
                            result.mechanism_scores[mech] = old * multiplier

                    # Re-derive primary/secondary from adjusted scores
                    ranked = sorted(result.mechanism_scores.items(), key=lambda x: x[1], reverse=True)
                    if len(ranked) >= 1:
                        result.primary_mechanism = ranked[0][0]
                    if len(ranked) >= 2:
                        result.secondary_mechanism = ranked[1][0]

                # Apply tone from context (blend: 70% buyer, 30% context)
                ctx_tone = ctx.get("optimal_tone", "")
                if ctx_tone and result.tone == "balanced":
                    result.tone = ctx_tone
                    result.reasoning.append(f"Context: {mindset} mindset → tone={ctx_tone}")

                # Apply complexity recommendation
                complexity = ctx.get("recommended_complexity", "")
                if complexity == "simple" and result.copy_length == "long":
                    result.copy_length = "medium"
                    result.reasoning.append(f"Context: {mindset} mindset → simplified copy")
                elif complexity == "detailed" and result.copy_length == "short":
                    result.copy_length = "medium"
                    result.reasoning.append(f"Context: {mindset} mindset → enriched copy")

                # Store context intelligence on the result for response enrichment
                result.context_intelligence = {
                    "domain": domain,
                    "mindset": mindset,
                    "attention_level": ctx.get("attention_level", "medium"),
                    "purchase_intent": ctx.get("purchase_intent", "unknown"),
                    "mechanism_adjustments": adjustments,
                    "recommended_mechanisms": ctx.get("recommended_mechanisms", []),
                    "avoid_mechanisms": ctx.get("avoid_mechanisms", []),
                    "optimal_tone": ctx_tone,
                    "recommended_complexity": complexity,
                    "confidence": ctx.get("confidence", 0),
                }

                n_adjusted = sum(1 for v in adjustments.values() if v != 1.0)
                result.reasoning.append(
                    f"Context: domain={domain} mindset={mindset} "
                    f"confidence={ctx['confidence']:.2f} "
                    f"adjusted {n_adjusted} mechanisms"
                )
        except Exception as e:
            logger.debug("Context intelligence skipped: %s", e)

    # ── COMPARISON: Old vs New page intelligence systems ──
    # Both systems ran. Log comparison for evaluation.
    # The reader_position (new) ran first; page_profile (old) ran second.
    # Compare their outputs to evaluate which is more useful.
    if reader_position and reader_position.confidence > 0:
        comparison = {
            "new_system": {
                "signals_used": reader_position.signals_used,
                "confidence": reader_position.confidence,
                "dims_constrained": sum(
                    1 for v in reader_position.dimensions.values() if abs(v - 0.5) > 0.05
                ),
            },
            "old_system": {
                "source": page_profile.profile_source if page_profile else "none",
                "confidence": page_profile.confidence if page_profile else 0.0,
                "had_edge_dims": bool(page_profile.edge_dimensions) if page_profile else False,
            },
        }

        # Store comparison in context_intelligence for downstream analysis
        if result.context_intelligence is None:
            result.context_intelligence = {}
        result.context_intelligence["system_comparison"] = comparison

        # If old system returned nothing but new system has signal,
        # inject the reader position into the page edge dims
        if (not page_profile or page_profile.confidence < cfg.page_confidence_floor) \
           and reader_position.confidence > 0.15:
            # New system fills the gap — store its dims as edge_dimensions
            if not result.context_intelligence.get("page_edge_dimensions"):
                result.context_intelligence["page_edge_dimensions"] = reader_position.dimensions
                result.context_intelligence["page_confidence"] = reader_position.confidence
                result.context_intelligence["page_edge_scoring_tier"] = "impression_resolver"
                result.reasoning.append(
                    f"ImpressionResolver filled gap: old system had no profile, "
                    f"new system composed {len(reader_position.signals_used)} signals → "
                    f"conf={reader_position.confidence:.2f}"
                )

    # ── GOAL ACTIVATION: Nonconscious Goal Priming Layer ──
    # This is the crossover page intelligence layer. Grounded in Bargh's
    # auto-motive model: page content activates nonconscious goals, and
    # the ad serves as goal fulfillment. Goal-relevant ads are noticed
    # automatically through goal-directed selective attention.
    #
    # Unlike concept priming (which decays in seconds), goal priming
    # PERSISTS and INTENSIFIES when unfulfilled (Forster et al., 2007).
    # A mismatched ad faces ACTIVE SUPPRESSION from goal shielding (Shah, 2003).
    #
    # This layer:
    # 1. Scores the page for nonconscious goal activation
    # 2. Computes crossover score (goal activation × archetype fulfillment)
    # 3. Modulates mechanism scores based on goal alignment
    # 4. Stores goal activation data for downstream learning
    try:
        from adam.intelligence.goal_activation import (
            score_page_goal_activation,
            compute_crossover_score_learned,
            get_goal_learner,
            GOAL_TAXONOMY,
            ARCHETYPE_GOAL_FULFILLMENT,
        )

        # Build page text from available signals
        page_text_parts = []
        if page_title:
            page_text_parts.append(page_title)
        if keywords:
            page_text_parts.append(" ".join(keywords))
        if iab_categories:
            page_text_parts.append(" ".join(iab_categories))
        # Use domain name itself as weak signal
        if domain:
            page_text_parts.append(domain.replace(".", " ").replace("-", " "))

        # Estimate affect valence from existing context intelligence
        affect_valence = 0.5  # neutral default
        if result.context_intelligence:
            ev = result.context_intelligence.get("emotional_valence", 0.5)
            if isinstance(ev, (int, float)):
                affect_valence = ev

        page_text = " ".join(page_text_parts)
        if page_text.strip():
            # Parse archetype from segment_id for crossover computation
            archetype_for_crossover = ""
            if segment_id:
                archetype_for_crossover, _, _ = _parse_segment_id(segment_id)

            goal_result = score_page_goal_activation(page_text, affect_valence)

            if goal_result.dominant_strength > 0.1:
                # Apply goal-based mechanism modulation
                # If the dominant goal aligns with specific mechanisms,
                # boost those mechanisms and dampen misaligned ones
                _GOAL_MECHANISM_ALIGNMENT = {
                    "affiliation_safety": {"social_proof": 1.25, "authority": 1.15, "scarcity": 0.80},
                    "social_alignment": {"social_proof": 1.30, "unity": 1.20, "scarcity": 0.75},
                    "threat_reduction": {"loss_aversion": 1.25, "authority": 1.20, "commitment": 1.10, "curiosity": 0.75},
                    "novelty_exploration": {"curiosity": 1.30, "liking": 1.15, "scarcity": 1.10, "authority": 0.80},
                    "competence_verification": {"authority": 1.25, "cognitive_ease": 1.15, "scarcity": 0.85},
                    "planning_completion": {"commitment": 1.25, "cognitive_ease": 1.20, "loss_aversion": 1.10},
                    "indulgence_permission": {"liking": 1.25, "social_proof": 1.15, "scarcity": 1.10, "authority": 0.85},
                    "status_signaling": {"scarcity": 1.25, "authority": 1.20, "social_proof": 1.10, "reciprocity": 0.80},
                }

                dominant = goal_result.dominant_goal
                if dominant in _GOAL_MECHANISM_ALIGNMENT and result.mechanism_scores:
                    adjustments = _GOAL_MECHANISM_ALIGNMENT[dominant]
                    strength = goal_result.dominant_strength

                    for mech, multiplier in adjustments.items():
                        if mech in result.mechanism_scores:
                            # Scale adjustment by goal strength
                            scaled = 1.0 + (multiplier - 1.0) * strength
                            result.mechanism_scores[mech] *= scaled

                    # Goal shielding: dampen mechanisms aligned with SUPPRESSED goals
                    for shielded_goal in goal_result.goal_shielded:
                        if shielded_goal in _GOAL_MECHANISM_ALIGNMENT:
                            for mech, mult in _GOAL_MECHANISM_ALIGNMENT[shielded_goal].items():
                                if mult > 1.0 and mech in result.mechanism_scores:
                                    # This mechanism serves a suppressed goal — dampen
                                    result.mechanism_scores[mech] *= 0.85

                    # Re-rank after goal modulation
                    ranked = sorted(result.mechanism_scores.items(), key=lambda x: x[1], reverse=True)
                    if len(ranked) >= 1:
                        result.primary_mechanism = ranked[0][0]
                    if len(ranked) >= 2:
                        result.secondary_mechanism = ranked[1][0]

                # Compute crossover score if archetype known
                crossover_score = 0.0
                if archetype_for_crossover:
                    crossover_score = compute_crossover_score_learned(
                        goal_result, resolve_archetype(archetype_for_crossover)
                    )

                # Compute epistemic value for the hunt
                learner = get_goal_learner()
                page_category = ""
                if domain:
                    from adam.retargeting.engines.signal_collector import NonconsciousSignalCollector
                    page_category = NonconsciousSignalCollector._classify_domain_category(domain)

                epistemic = learner.compute_epistemic_value(
                    page_category or "general",
                    resolve_archetype(archetype_for_crossover) if archetype_for_crossover else "",
                    goal_result,
                ) if archetype_for_crossover else 0.0

                # Store goal activation in context_intelligence for:
                # 1. Response enrichment (API consumer sees goal data)
                # 2. Outcome handler learning (record_observation)
                # 3. Retargeting sequence (cumulative priming)
                if result.context_intelligence is None:
                    result.context_intelligence = {}
                result.context_intelligence["goal_activation"] = {
                    "goal_scores": goal_result.goal_scores,
                    "dominant_goal": goal_result.dominant_goal,
                    "dominant_strength": goal_result.dominant_strength,
                    "affect_valence": goal_result.affect_valence,
                    "goal_shielded": goal_result.goal_shielded,
                    "evidence": {g: markers[:3] for g, markers in goal_result.evidence.items() if markers},
                    "crossover_score": crossover_score,
                    "epistemic_value": epistemic,
                    "page_category": page_category,
                }

                result.reasoning.append(
                    f"GoalActivation: dominant={dominant} ({goal_result.dominant_strength:.2f}), "
                    f"crossover={crossover_score:.3f}, epistemic={epistemic:.3f}, "
                    f"shielded={goal_result.goal_shielded}"
                )
    except Exception as e:
        logger.debug("Goal activation layer skipped: %s", e)

    return result


def _extract_domain(url: str) -> Optional[str]:
    """Extract clean domain from URL."""
    if not url:
        return None
    url = url.lower().strip()
    # Remove protocol
    for prefix in ("https://", "http://", "//"):
        if url.startswith(prefix):
            url = url[len(prefix):]
    # Remove path
    url = url.split("/")[0]
    # Remove port
    url = url.split(":")[0]
    # Remove www
    if url.startswith("www."):
        url = url[4:]
    return url if url else None


# ---------------------------------------------------------------------------
# Synergy check — ensure mechanism combinations don't create reactance
# ---------------------------------------------------------------------------
# Complete antagonism table from research
MECHANISM_ANTAGONISMS: Dict[Tuple[str, str], List[str]] = {
    ("social_proof", "scarcity"): ["guardian", "analyst"],
    ("authority", "scarcity"): ["explorer", "creator"],
    ("reciprocity", "loss_aversion"): ["connector", "guardian"],
    ("scarcity", "commitment"): ["analyst"],
    ("liking", "authority"): ["analyst", "achiever"],
    ("curiosity", "commitment"): ["explorer"],
    ("unity", "scarcity"): ["connector"],
}

MECHANISM_SYNERGIES: Dict[str, Dict[str, str]] = {
    "authority":      {"achiever": "social_proof", "analyst": "cognitive_ease", "guardian": "commitment", "explorer": "curiosity", "connector": "liking", "creator": "curiosity"},
    "social_proof":   {"connector": "liking", "guardian": "commitment", "creator": "unity", "achiever": "authority", "analyst": "authority", "explorer": "curiosity"},
    "scarcity":       {"achiever": "loss_aversion", "explorer": "curiosity", "creator": "cognitive_ease", "guardian": "social_proof", "analyst": "authority", "connector": "social_proof"},
    "loss_aversion":  {"guardian": "social_proof", "analyst": "authority", "achiever": "commitment", "connector": "social_proof", "explorer": "curiosity", "creator": "cognitive_ease"},
    "cognitive_ease": {"analyst": "authority", "guardian": "social_proof", "connector": "liking", "achiever": "authority", "explorer": "curiosity", "creator": "unity"},
    "reciprocity":    {"connector": "liking", "guardian": "social_proof", "achiever": "commitment", "analyst": "cognitive_ease", "explorer": "curiosity", "creator": "unity"},
    "commitment":     {"achiever": "authority", "guardian": "social_proof", "analyst": "cognitive_ease", "connector": "reciprocity", "explorer": "curiosity", "creator": "unity"},
    "liking":         {"connector": "social_proof", "creator": "unity", "explorer": "curiosity", "achiever": "social_proof", "guardian": "social_proof", "analyst": "cognitive_ease"},
    "unity":          {"connector": "social_proof", "creator": "liking", "guardian": "commitment", "achiever": "social_proof", "analyst": "cognitive_ease", "explorer": "curiosity"},
    "curiosity":      {"explorer": "cognitive_ease", "creator": "unity", "analyst": "authority", "achiever": "authority", "connector": "liking", "guardian": "social_proof"},
}


def check_mechanism_synergy(
    result: CreativeIntelligence, archetype: str,
) -> CreativeIntelligence:
    """Ensure primary+secondary don't antagonize, and compute portfolio weights.

    Two-phase approach:
    1. If learned interactions have sufficient data (>20 observations),
       use the data-driven portfolio optimizer to select mechanism weights.
       This replaces the hardcoded lookup with empirical evidence.
    2. Fall back to the research-grounded antagonism table for safety.

    The portfolio is stored on the result for inclusion in the StackAdapt response.
    """
    archetype = resolve_archetype(archetype)

    # ── Phase 1: Data-driven portfolio optimization ──
    # When the interaction learner has enough observations, compute
    # portfolio weights that account for mechanism covariance.
    try:
        from adam.learning.mechanism_interactions import get_mechanism_interaction_learner
        learner = get_mechanism_interaction_learner()

        if (
            result.mechanism_scores
            and len(learner._observation_buffer) >= 20
        ):
            portfolio = learner.compute_portfolio_weights(
                base_effectiveness=result.mechanism_scores,
                max_mechanisms=4,
            )
            if portfolio:
                result.mechanism_portfolio = portfolio

                # Check if learned data suggests a different primary
                top = portfolio[0]
                if (
                    top["mechanism"] != result.primary_mechanism
                    and top["interaction_bonus"] > _cascade_cfg().learned_synergy_min_bonus
                ):
                    old_primary = result.primary_mechanism
                    result.primary_mechanism = top["mechanism"]
                    if len(portfolio) > 1:
                        result.secondary_mechanism = portfolio[1]["mechanism"]
                    result.reasoning.append(
                        f"Portfolio: learned synergy shifted primary "
                        f"{old_primary}→{top['mechanism']} "
                        f"(bonus={top['interaction_bonus']:.3f}, "
                        f"observations={len(learner._observation_buffer)})"
                    )
                else:
                    result.reasoning.append(
                        f"Portfolio: {len(portfolio)} mechanisms weighted "
                        f"({len(learner._observation_buffer)} observations)"
                    )

                # Also check for learned suppressions on current primary+secondary
                if learner.should_avoid_combination(
                    result.primary_mechanism, result.secondary_mechanism
                ):
                    # Use learned companion instead
                    companions = learner.recommend_companion_mechanisms(
                        primary_mechanism=result.primary_mechanism,
                        available_mechanisms=list(result.mechanism_scores.keys()),
                        num_recommendations=1,
                    )
                    if companions:
                        old = result.secondary_mechanism
                        result.secondary_mechanism = companions[0]
                        result.reasoning.append(
                            f"Portfolio: learned suppression ({result.primary_mechanism}, "
                            f"{old}) → swapped to {companions[0]}"
                        )
    except Exception as e:
        logger.debug("Learned portfolio optimization skipped: %s", e)

    # ── Phase 2: Research-grounded safety check (always runs) ──
    # Even with learned data, the hardcoded antagonism table catches
    # dangerous combinations that may not have enough observation data yet.
    pair = (result.primary_mechanism, result.secondary_mechanism)
    reverse_pair = (result.secondary_mechanism, result.primary_mechanism)

    for p in (pair, reverse_pair):
        if p in MECHANISM_ANTAGONISMS and archetype in MECHANISM_ANTAGONISMS[p]:
            synergy_map = MECHANISM_SYNERGIES.get(result.primary_mechanism, {})
            recommended = synergy_map.get(archetype, result.secondary_mechanism)
            old = result.secondary_mechanism
            result.secondary_mechanism = recommended
            result.reasoning.append(
                f"Synergy: ({result.primary_mechanism}, {old}) antagonistic "
                f"for {archetype} → swapped to {recommended}"
            )
            break

    return result


# ---------------------------------------------------------------------------
# Main cascade entry point
# ---------------------------------------------------------------------------
def run_bilateral_cascade(
    segment_id: str,
    graph_cache: Any = None,
    asin: Optional[str] = None,
    device_type: Optional[str] = None,
    time_of_day: Optional[int] = None,
    iab_category: Optional[str] = None,
    buyer_id: Optional[str] = None,
    page_url: Optional[str] = None,
    # Additional OpenRTB signals for impression state resolution
    page_title: str = "",
    referrer: str = "",
    keywords: Optional[List[str]] = None,
    iab_categories: Optional[List[str]] = None,
    # Latency budget (optional — if None, no timeout enforcement)
    latency_budget=None,
) -> CreativeIntelligence:
    """Run the full bilateral cascade and return creative intelligence.

    Progressive depth: goes as deep as data availability allows within
    the latency budget. If budget is provided and exhausted, returns
    the best result achieved so far (graceful degradation).
    """
    t0 = time.monotonic()

    # Parse segment
    archetype, mechanism_hint, category = _parse_segment_id(segment_id)
    archetype = resolve_archetype(archetype)

    # Level 1: Always available (< 2ms)
    result = level1_archetype_prior(archetype)

    # Level 2: If we have category (2-10ms)
    if category and graph_cache:
        result = level2_category_posterior(archetype, category, graph_cache, result)

    # Level 3 or 4: If we have ASIN (10-50ms)
    # Check budget AND circuit breaker before expensive graph queries
    budget_ok = latency_budget is None or latency_budget.has_budget
    neo4j_circuit_ok = True
    try:
        from adam.infrastructure.resilience.circuit_breaker import get_circuit_breaker
        neo4j_cb = get_circuit_breaker("neo4j")
        if neo4j_cb.is_open:
            neo4j_circuit_ok = False
            result.reasoning.append("L3/L4 skipped: Neo4j circuit breaker OPEN")
    except Exception:
        pass

    if asin and graph_cache and budget_ok and neo4j_circuit_ok:
        # Try Level 3 first (bilateral edges)
        pre_level = result.cascade_level
        result = level3_bilateral_edges(asin, archetype, graph_cache, result, buyer_id=buyer_id)

        budget_ok = latency_budget is None or latency_budget.has_budget
        if result.cascade_level == pre_level and budget_ok:
            # Level 3 didn't have enough edges; try Level 4 (inferential)
            result = level4_inferential_transfer(asin, archetype, graph_cache, result)
    elif asin and graph_cache and not budget_ok:
        result.reasoning.append(
            f"L3/L4 skipped: budget exhausted ({latency_budget.elapsed_ms:.0f}ms elapsed)"
        )

    # If segment_id specified a mechanism, use it as a strong hint
    if mechanism_hint and mechanism_hint in MECHANISMS:
        if result.cascade_level <= 2:
            # At low cascade levels, the segment hint IS the mechanism
            result.primary_mechanism = mechanism_hint
            result.reasoning.append(f"Segment hint: mechanism={mechanism_hint} applied (cascade ≤ L2)")

    # Context modulation (device, temporal, page context, AND goal activation)
    result = apply_context_modulation(
        result, device_type, time_of_day, iab_category, page_url,
        page_title=page_title, referrer=referrer,
        keywords=keywords, iab_categories=iab_categories,
        segment_id=segment_id,
    )

    # Synergy check
    result = check_mechanism_synergy(result, archetype)

    elapsed_ms = (time.monotonic() - t0) * 1000
    result.reasoning.append(f"Cascade complete: level={result.cascade_level}, elapsed={elapsed_ms:.1f}ms")

    # Record cascade observability metrics
    try:
        from adam.infrastructure.prometheus import get_metrics
        metrics = get_metrics()
        metrics.cascade_level_reached.labels(level=str(result.cascade_level)).inc()
        if result.edge_count is not None:
            metrics.cascade_edge_count.observe(result.edge_count)
    except Exception:
        pass

    return result


def _parse_segment_id(segment_id: str) -> Tuple[str, Optional[str], Optional[str]]:
    """Parse segment_id into (archetype, mechanism_hint, category).

    Supports both standard archetypes (achiever, guardian, etc.) and
    campaign-specific archetypes (corporate_executive, airport_anxiety, etc.)
    with optional category and mechanism components.

    Examples:
        informativ_achiever_t1 → ("achiever", None, None)
        informativ_corporate_executive_luxury_transportation_t1
            → ("corporate_executive", None, "luxury_transportation")
        informativ_airport_anxiety_loss_aversion_luxury_transportation_t2
            → ("airport_anxiety", "loss_aversion", "luxury_transportation")
        informativ_luxury_transportation_corporate_executive_t1
            → ("corporate_executive", None, "luxury_transportation")
    """
    body = segment_id.replace("informativ_", "")

    # Strip tier suffix
    tier = None
    for t in ("_t1", "_t2", "_t3"):
        if body.endswith(t):
            tier = t[1:]
            body = body[:-3]
            break

    # Known multi-word tokens (order matters — longest first)
    _KNOWN_ARCHETYPES = {
        "corporate_executive", "airport_anxiety", "special_occasion",
        "first_timer", "repeat_loyal",
        "status_seeker", "easy_decider", "careful_truster",
        "skeptical_analyst", "disillusioned",
        "achiever", "guardian", "explorer", "connector", "analyst", "creator",
    }
    _KNOWN_MECHANISMS = {
        "social_proof", "loss_aversion", "cognitive_ease",
        "authority", "scarcity", "reciprocity", "commitment",
        "liking", "unity", "curiosity",
    }
    _KNOWN_CATEGORIES = {
        "luxury_transportation": "luxury_transportation",
        "beauty": "Beauty",
        "personal_care": "Personal Care",
        "health": "Health",
        "electronics": "Electronics",
    }

    archetype = "achiever"
    mechanism_hint = None
    category = None

    # Greedy match: try to find known tokens in the body string
    remaining = body
    for token in sorted(_KNOWN_ARCHETYPES, key=len, reverse=True):
        if token in remaining:
            archetype = token
            remaining = remaining.replace(token, "", 1).strip("_")
            break

    for token in sorted(_KNOWN_MECHANISMS, key=len, reverse=True):
        if token in remaining:
            mechanism_hint = token
            remaining = remaining.replace(token, "", 1).strip("_")
            break

    for token in sorted(_KNOWN_CATEGORIES.keys(), key=len, reverse=True):
        if token in remaining:
            category = _KNOWN_CATEGORIES[token]
            remaining = remaining.replace(token, "", 1).strip("_")
            break

    return archetype, mechanism_hint, category
