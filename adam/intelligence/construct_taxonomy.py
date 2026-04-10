"""
ADAM Psychological Construct Taxonomy v2.0
==========================================
Edge-Level Bayesian Fusion Architecture — Complete Machine-Readable Specification

AUTHORITATIVE SOURCE: taxonomy/Construct_Taxonomy_v2_COMPLETE.md
                      taxonomy/ADAM_Corpus_Architecture_Addendum_Dual_Annotation.md

This module is the Python translation of the authoritative taxonomy documents.
No constructs may be added, removed, or modified here without first updating
the source markdown documents.

Total: 441 constructs across 35 domains
  - Customer-side (Domains 1-22): 247 constructs
  - Shared (Domains 23-28): 82 constructs
  - Ad/Brand-side (Domains 29-33): 80 constructs
  - Peer Persuasion (Domain 34): 18 constructs
  - Persuasion Ecosystem (Domain 35): 14 constructs

Architecture:
  - Edge tier (~178 constructs): 10ms latency, Neo4j + Redis
  - Reasoning tier (~263 constructs): 2000ms latency, Claude context
  - Three edge types: BRAND_CONVERTED, PEER_INFLUENCED, ECOSYSTEM_CONVERTED
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# =============================================================================
# ENUMS
# =============================================================================

class ScoringSwitch(str, Enum):
    """Which side of the edge a construct is scored on."""
    USER_SIDE = "user_side"
    AD_SIDE = "ad_side"
    BOTH = "both"
    ECOSYSTEM = "ecosystem"


class TemporalStability(str, Enum):
    """How stable a construct is over time — governs Bayesian prior strength."""
    TRAIT = "trait"              # Stable over years
    DISPOSITION = "disposition"  # Stable over months
    STATE = "state"              # Shifts minutes-hours
    MOMENTARY = "momentary"      # Shifts in seconds


class InferenceTier(str, Enum):
    """Whether construct is scored in real-time or by reasoning layer."""
    EDGE = "edge"                       # Real-time, <10ms
    REASONING_LAYER = "reasoning_layer"  # Claude atoms, <2000ms


class InferenceTractability(str, Enum):
    """How reliably ADAM can estimate this construct at the individual level."""
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


class EdgeType(str, Enum):
    """The three edge types from the dual-annotation paradigm."""
    BRAND_CONVERTED = "BRAND_CONVERTED"
    PEER_INFLUENCED = "PEER_INFLUENCED"
    ECOSYSTEM_CONVERTED = "ECOSYSTEM_CONVERTED"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class BayesianPrior:
    """Prior distribution parameters for a construct."""
    distribution: str = "beta"
    alpha: float = 5.0
    beta: float = 5.0


@dataclass
class Construct:
    """A single psychological construct — the atomic unit of ADAM's intelligence."""
    id: str
    name: str
    domain_id: str
    description: str = ""
    range_min: float = 0.0
    range_max: float = 1.0
    scoring_side: ScoringSwitch = ScoringSwitch.USER_SIDE
    temporal_stability: TemporalStability = TemporalStability.DISPOSITION
    inference_tractability: InferenceTractability = InferenceTractability.MODERATE
    tier: InferenceTier = InferenceTier.EDGE
    prior: BayesianPrior = field(default_factory=BayesianPrior)
    population_prior_only: bool = False
    inference_sources: list[str] = field(default_factory=list)
    mechanism_connections: list[str] = field(default_factory=list)
    ad_implications: str = ""
    research_effect_size: str = ""
    research_basis: str = ""
    ethical_note: str = ""
    cross_reference: str = ""
    derived_from: list[str] = field(default_factory=list)
    facets: dict[str, dict] = field(default_factory=dict)
    state_modulation: bool = False
    # For ecosystem constructs with sub-scores
    sub_scores: dict[str, dict] = field(default_factory=dict)


@dataclass
class Domain:
    """A domain grouping related constructs."""
    domain_id: str
    domain_name: str
    scoring_side: ScoringSwitch
    construct_count: int
    constructs: dict[str, Construct]
    purpose: str = ""
    primary_research: str = ""
    adam_relevance: str = ""
    applies_to: str = ""  # e.g. "reviews_as_ads_only", "product_level_aggregate"


# =============================================================================
# TEMPORAL STABILITY CONFIGURATION (from Part IV)
# =============================================================================

TEMPORAL_STABILITY_CONFIG = {
    TemporalStability.TRAIT: {
        "description": "Stable over years. Core personality and deep dispositions.",
        "prior_strength": "strong",
        "bayesian_alpha_base": 10.0,
        "update_learning_rate": 0.01,
        "min_observations_for_update": 20,
        "decay_rate": 0.0,
    },
    TemporalStability.DISPOSITION: {
        "description": "Stable over months. Habitual patterns and chronic orientations.",
        "prior_strength": "moderate",
        "bayesian_alpha_base": 5.0,
        "update_learning_rate": 0.05,
        "min_observations_for_update": 10,
        "decay_rate": 0.001,
    },
    TemporalStability.STATE: {
        "description": "Shifts over minutes to hours. Current psychological condition.",
        "prior_strength": "weak",
        "bayesian_alpha_base": 2.0,
        "update_learning_rate": 0.2,
        "min_observations_for_update": 3,
        "decay_rate": 0.1,
    },
    TemporalStability.MOMENTARY: {
        "description": "Shifts in seconds. Reactive and transient.",
        "prior_strength": "very_weak",
        "bayesian_alpha_base": 1.0,
        "update_learning_rate": 0.5,
        "min_observations_for_update": 1,
        "decay_rate": 0.5,
    },
}


# =============================================================================
# TIER ASSIGNMENT CONFIGURATION (from Part IV)
# =============================================================================

TIER_ASSIGNMENT_CONFIG = {
    InferenceTier.EDGE: {
        "description": "Scored in real-time, stored in Neo4j as edge properties.",
        "max_parameters": 150,
        "latency_budget_ms": 10,
        "storage": "Neo4j edge properties + Redis cache",
        "update_mechanism": "Bayesian online update via Gradient Bridge",
    },
    InferenceTier.REASONING_LAYER: {
        "description": "Scored by Claude Atom of Thought atoms during deeper reasoning.",
        "max_parameters": None,  # unlimited
        "latency_budget_ms": 2000,
        "storage": "Claude reasoning context, Neo4j for persistent insights",
        "update_mechanism": "Claude inference -> ReasoningInsight node -> batch consolidation",
    },
}


# =============================================================================
# CROSS-DOMAIN DEPENDENCY MAP (from Part IV)
# =============================================================================

CROSS_DOMAIN_DEPENDENCIES = {
    "evolutionary_modulates": {
        "evo_self_protection": ["bias_loss_aversion", "bias_status_quo", "ci_authority", "reg_prevention"],
        "evo_affiliation": ["ci_social_proof", "ci_unity", "soc_conformity", "soc_normative_influence"],
        "evo_status": ["ci_scarcity", "ci_authority", "evo_conspicuous", "dark_narcissism"],
        "evo_kin_care": ["pt_loss_aversion_coeff", "bias_zero_risk", "reg_prevention"],
        "evo_life_history": ["bias_hyperbolic_discount", "bias_present", "dm_impulse_cog", "tp_future"],
        "evo_threat_calibration": ["evo_self_protection", "evo_disease_avoidance", "evo_scarcity_psych"],
    },
    "nonconscious_modulates": {
        "nc_context_dependency": ["imp_affective_priming", "imp_semantic_priming", "bias_framing"],
        "nc_auto_eval": ["imp_perceptual_fluency", "bias_halo", "bias_mere_exposure"],
        "nc_emotional_contagion": ["emo_arousal", "emo_pleasure", "nt_emotional"],
        "nc_habit_resistance": ["bias_status_quo", "dm_loyalty_beh", "bias_default"],
    },
    "implicit_motivation_modulates": {
        "im_wanting": ["dm_impulse_cog", "dm_impulse_aff", "approach_motivation"],
        "im_reg_fit": ["reg_promotion", "reg_prevention"],
        "im_compensatory": ["mat_centrality", "evo_status"],
    },
    "state_modulates_trait_expression": {
        "emo_arousal": ["reg_prevention", "clt_temporal", "dm_system1", "ip_attention_span"],
        "cognitive_load": ["dm_nfc", "dm_system2", "elm_central", "ip_overload_threshold"],
    },
}


# =============================================================================
# HELPER: Build a Construct with defaults from the taxonomy
# =============================================================================

def _infer_tier(
    inference_tractability: InferenceTractability,
    population_prior_only: bool,
    explicit_tier: Optional[InferenceTier],
) -> InferenceTier:
    """Derive tier from tractability if not explicitly set.
    
    Rule from taxonomy: edge-level constructs are individually estimable
    with high or moderate tractability. Low tractability and population-prior-only
    go to reasoning layer. Explicit tier overrides.
    """
    if explicit_tier is not None:
        return explicit_tier
    if population_prior_only:
        return InferenceTier.REASONING_LAYER
    if inference_tractability == InferenceTractability.LOW:
        return InferenceTier.REASONING_LAYER
    return InferenceTier.EDGE


def _c(
    id: str,
    domain_id: str,
    name: str = "",
    description: str = "",
    range_min: float = 0.0,
    range_max: float = 1.0,
    scoring_side: ScoringSwitch = ScoringSwitch.USER_SIDE,
    temporal_stability: TemporalStability = TemporalStability.DISPOSITION,
    inference_tractability: InferenceTractability = InferenceTractability.MODERATE,
    tier: Optional[InferenceTier] = None,  # None = auto-infer from tractability
    prior: Optional[BayesianPrior] = None,
    population_prior_only: bool = False,
    inference_sources: Optional[list[str]] = None,
    mechanism_connections: Optional[list[str]] = None,
    ad_implications: str = "",
    research_effect_size: str = "",
    research_basis: str = "",
    ethical_note: str = "",
    cross_reference: str = "",
    derived_from: Optional[list[str]] = None,
    facets: Optional[dict] = None,
    state_modulation: bool = False,
    sub_scores: Optional[dict] = None,
) -> Construct:
    resolved_tier = _infer_tier(inference_tractability, population_prior_only, tier)
    return Construct(
        id=id,
        name=name or id,
        domain_id=domain_id,
        description=description,
        range_min=range_min,
        range_max=range_max,
        scoring_side=scoring_side,
        temporal_stability=temporal_stability,
        inference_tractability=inference_tractability,
        tier=resolved_tier,
        prior=prior or BayesianPrior(),
        population_prior_only=population_prior_only,
        inference_sources=inference_sources or [],
        mechanism_connections=mechanism_connections or [],
        ad_implications=ad_implications,
        research_effect_size=research_effect_size,
        research_basis=research_basis,
        ethical_note=ethical_note,
        cross_reference=cross_reference,
        derived_from=derived_from or [],
        facets=facets or {},
        state_modulation=state_modulation,
        sub_scores=sub_scores or {},
    )


# Shorthand aliases for readability
_US = ScoringSwitch.USER_SIDE
_AD = ScoringSwitch.AD_SIDE
_BO = ScoringSwitch.BOTH
_EC = ScoringSwitch.ECOSYSTEM
_TR = TemporalStability.TRAIT
_DI = TemporalStability.DISPOSITION
_ST = TemporalStability.STATE
_MO = TemporalStability.MOMENTARY
_HI = InferenceTractability.HIGH
_MD = InferenceTractability.MODERATE
_LO = InferenceTractability.LOW
_E = InferenceTier.EDGE
_R = InferenceTier.REASONING_LAYER


# =============================================================================
# DOMAIN 1: PERSONALITY & INDIVIDUAL DIFFERENCES (48 constructs)
# =============================================================================

_D1 = "personality"

DOMAIN_1_PERSONALITY = Domain(
    domain_id=_D1,
    domain_name="Personality & Individual Differences",
    scoring_side=_US,
    construct_count=48,
    purpose="Stable trait-level individual differences that predict long-term patterns in ad response.",
    primary_research="Costa & McCrae (1992), Ashton & Lee (2004), Matz et al. (2017)",
    constructs={
        # Big Five (5 traits + 30 facets = 35)
        "big5_openness": _c("big5_openness", _D1, "Openness to Experience",
            temporal_stability=_TR, inference_tractability=_HI,
            prior=BayesianPrior(alpha=5.0, beta=5.0),
            research_effect_size="r = .41-.44 with music preferences (Rentfrow & Gosling, 2003)"),
        "big5_openness_fantasy": _c("big5_openness_fantasy", _D1, "Openness: Fantasy", temporal_stability=_TR, inference_tractability=_MD),
        "big5_openness_aesthetics": _c("big5_openness_aesthetics", _D1, "Openness: Aesthetics", temporal_stability=_TR, inference_tractability=_MD),
        "big5_openness_feelings": _c("big5_openness_feelings", _D1, "Openness: Feelings", temporal_stability=_TR, inference_tractability=_MD),
        "big5_openness_actions": _c("big5_openness_actions", _D1, "Openness: Actions", temporal_stability=_TR, inference_tractability=_MD),
        "big5_openness_ideas": _c("big5_openness_ideas", _D1, "Openness: Ideas", temporal_stability=_TR, inference_tractability=_MD),
        "big5_openness_values": _c("big5_openness_values", _D1, "Openness: Values", temporal_stability=_TR, inference_tractability=_MD),

        "big5_conscientiousness": _c("big5_conscientiousness", _D1, "Conscientiousness",
            temporal_stability=_TR, inference_tractability=_HI, prior=BayesianPrior(alpha=5.0, beta=5.0)),
        "big5_consc_competence": _c("big5_consc_competence", _D1, "Conscientiousness: Competence", temporal_stability=_TR, inference_tractability=_MD),
        "big5_consc_order": _c("big5_consc_order", _D1, "Conscientiousness: Order", temporal_stability=_TR, inference_tractability=_MD),
        "big5_consc_dutifulness": _c("big5_consc_dutifulness", _D1, "Conscientiousness: Dutifulness", temporal_stability=_TR, inference_tractability=_MD),
        "big5_consc_achievement": _c("big5_consc_achievement", _D1, "Conscientiousness: Achievement Striving", temporal_stability=_TR, inference_tractability=_MD),
        "big5_consc_self_discipline": _c("big5_consc_self_discipline", _D1, "Conscientiousness: Self-Discipline", temporal_stability=_TR, inference_tractability=_MD),
        "big5_consc_deliberation": _c("big5_consc_deliberation", _D1, "Conscientiousness: Deliberation", temporal_stability=_TR, inference_tractability=_MD),

        "big5_extraversion": _c("big5_extraversion", _D1, "Extraversion",
            temporal_stability=_TR, inference_tractability=_HI, prior=BayesianPrior(alpha=5.0, beta=5.0)),
        "big5_extra_warmth": _c("big5_extra_warmth", _D1, "Extraversion: Warmth", temporal_stability=_TR, inference_tractability=_MD),
        "big5_extra_gregariousness": _c("big5_extra_gregariousness", _D1, "Extraversion: Gregariousness", temporal_stability=_TR, inference_tractability=_MD),
        "big5_extra_assertiveness": _c("big5_extra_assertiveness", _D1, "Extraversion: Assertiveness", temporal_stability=_TR, inference_tractability=_MD),
        "big5_extra_activity": _c("big5_extra_activity", _D1, "Extraversion: Activity", temporal_stability=_TR, inference_tractability=_MD),
        "big5_extra_excitement": _c("big5_extra_excitement", _D1, "Extraversion: Excitement Seeking", temporal_stability=_TR, inference_tractability=_MD),
        "big5_extra_positive_emotions": _c("big5_extra_positive_emotions", _D1, "Extraversion: Positive Emotions", temporal_stability=_TR, inference_tractability=_MD),

        "big5_agreeableness": _c("big5_agreeableness", _D1, "Agreeableness",
            temporal_stability=_TR, inference_tractability=_HI, prior=BayesianPrior(alpha=5.0, beta=5.0)),
        "big5_agree_trust": _c("big5_agree_trust", _D1, "Agreeableness: Trust", temporal_stability=_TR, inference_tractability=_MD),
        "big5_agree_straightforward": _c("big5_agree_straightforward", _D1, "Agreeableness: Straightforwardness", temporal_stability=_TR, inference_tractability=_MD),
        "big5_agree_altruism": _c("big5_agree_altruism", _D1, "Agreeableness: Altruism", temporal_stability=_TR, inference_tractability=_MD),
        "big5_agree_compliance": _c("big5_agree_compliance", _D1, "Agreeableness: Compliance", temporal_stability=_TR, inference_tractability=_MD),
        "big5_agree_modesty": _c("big5_agree_modesty", _D1, "Agreeableness: Modesty", temporal_stability=_TR, inference_tractability=_MD),
        "big5_agree_tender_minded": _c("big5_agree_tender_minded", _D1, "Agreeableness: Tender-Mindedness", temporal_stability=_TR, inference_tractability=_MD),

        "big5_neuroticism": _c("big5_neuroticism", _D1, "Neuroticism",
            temporal_stability=_TR, inference_tractability=_MD, prior=BayesianPrior(alpha=5.0, beta=5.0),
            ethical_note="NEVER target vulnerability. Use for protective framing only."),
        "big5_neuro_anxiety": _c("big5_neuro_anxiety", _D1, "Neuroticism: Anxiety", temporal_stability=_TR, inference_tractability=_MD),
        "big5_neuro_hostility": _c("big5_neuro_hostility", _D1, "Neuroticism: Angry Hostility", temporal_stability=_TR, inference_tractability=_MD),
        "big5_neuro_depression": _c("big5_neuro_depression", _D1, "Neuroticism: Depression", temporal_stability=_TR, inference_tractability=_MD),
        "big5_neuro_self_conscious": _c("big5_neuro_self_conscious", _D1, "Neuroticism: Self-Consciousness", temporal_stability=_TR, inference_tractability=_MD),
        "big5_neuro_impulsiveness": _c("big5_neuro_impulsiveness", _D1, "Neuroticism: Impulsiveness", temporal_stability=_TR, inference_tractability=_MD),
        "big5_neuro_vulnerability": _c("big5_neuro_vulnerability", _D1, "Neuroticism: Vulnerability", temporal_stability=_TR, inference_tractability=_MD),

        # HEXACO Honesty-Humility (1 + 4 facets = 5)
        "hexaco_honesty_humility": _c("hexaco_honesty_humility", _D1, "Honesty-Humility",
            temporal_stability=_TR, inference_tractability=_MD, prior=BayesianPrior(alpha=5.0, beta=5.0)),
        "hexaco_hh_sincerity": _c("hexaco_hh_sincerity", _D1, "Honesty-Humility: Sincerity", temporal_stability=_TR, inference_tractability=_MD),
        "hexaco_hh_fairness": _c("hexaco_hh_fairness", _D1, "Honesty-Humility: Fairness", temporal_stability=_TR, inference_tractability=_MD),
        "hexaco_hh_greed_avoid": _c("hexaco_hh_greed_avoid", _D1, "Honesty-Humility: Greed Avoidance", temporal_stability=_TR, inference_tractability=_MD),
        "hexaco_hh_modesty": _c("hexaco_hh_modesty", _D1, "Honesty-Humility: Modesty", temporal_stability=_TR, inference_tractability=_MD),

        # Dark Triad (3)
        "dark_narcissism": _c("dark_narcissism", _D1, "Narcissism",
            temporal_stability=_TR, inference_tractability=_MD, prior=BayesianPrior(alpha=3.0, beta=7.0),
            ethical_note="Score for messaging optimization. Never exploit grandiosity vulnerabilities."),
        "dark_machiavellianism": _c("dark_machiavellianism", _D1, "Machiavellianism",
            temporal_stability=_TR, inference_tractability=_LO, prior=BayesianPrior(alpha=3.0, beta=7.0)),
        "dark_psychopathy": _c("dark_psychopathy", _D1, "Subclinical Psychopathy",
            temporal_stability=_TR, inference_tractability=_LO, prior=BayesianPrior(alpha=2.0, beta=8.0),
            ethical_note="Population-level prior heavily weighted. Individual estimation unreliable."),

        # Sensation Seeking (4)
        "ss_thrill_adventure": _c("ss_thrill_adventure", _D1, "Thrill & Adventure Seeking",
            temporal_stability=_TR, inference_tractability=_MD, prior=BayesianPrior(alpha=4.0, beta=6.0)),
        "ss_experience_seeking": _c("ss_experience_seeking", _D1, "Experience Seeking",
            temporal_stability=_TR, inference_tractability=_MD, prior=BayesianPrior(alpha=4.0, beta=6.0)),
        "ss_disinhibition": _c("ss_disinhibition", _D1, "Disinhibition",
            temporal_stability=_TR, inference_tractability=_LO, prior=BayesianPrior(alpha=3.0, beta=7.0)),
        "ss_boredom_susceptibility": _c("ss_boredom_susceptibility", _D1, "Boredom Susceptibility",
            temporal_stability=_TR, inference_tractability=_MD, prior=BayesianPrior(alpha=4.0, beta=6.0)),

        # Self-Monitoring (1)
        "self_monitoring": _c("self_monitoring", _D1, "Self-Monitoring",
            temporal_stability=_TR, inference_tractability=_MD, prior=BayesianPrior(alpha=5.0, beta=5.0)),

        # Locus of Control (2)
        "loc_internal": _c("loc_internal", _D1, "Internal Locus of Control",
            temporal_stability=_TR, inference_tractability=_MD, prior=BayesianPrior(alpha=5.5, beta=4.5)),
        "loc_external": _c("loc_external", _D1, "External Locus of Control",
            temporal_stability=_TR, inference_tractability=_MD, prior=BayesianPrior(alpha=4.5, beta=5.5)),
    },
)


# =============================================================================
# DOMAIN 2: MOTIVATION & SELF-DETERMINATION (16 constructs)
# =============================================================================

_D2 = "motivation"

DOMAIN_2_MOTIVATION = Domain(
    domain_id=_D2,
    domain_name="Motivation & Self-Determination",
    scoring_side=_US,
    construct_count=16,
    purpose="What drives behavior — intrinsic/extrinsic motivation, achievement needs, regulatory focus.",
    primary_research="Deci & Ryan (2000), McClelland (1961), Higgins (1997)",
    constructs={
        # SDT Basic Needs (3)
        "sdt_autonomy": _c("sdt_autonomy", _D2, "Autonomy Need Strength", temporal_stability=_DI, inference_tractability=_MD),
        "sdt_competence": _c("sdt_competence", _D2, "Competence Need Strength", temporal_stability=_DI, inference_tractability=_MD),
        "sdt_relatedness": _c("sdt_relatedness", _D2, "Relatedness Need Strength", temporal_stability=_DI, inference_tractability=_MD),
        # SDT Motivation Continuum (6)
        "sdt_intrinsic": _c("sdt_intrinsic", _D2, "Intrinsic Motivation", temporal_stability=_DI, inference_tractability=_MD),
        "sdt_integrated": _c("sdt_integrated", _D2, "Integrated Regulation", temporal_stability=_DI, inference_tractability=_LO),
        "sdt_identified": _c("sdt_identified", _D2, "Identified Regulation", temporal_stability=_DI, inference_tractability=_LO),
        "sdt_introjected": _c("sdt_introjected", _D2, "Introjected Regulation", temporal_stability=_DI, inference_tractability=_LO),
        "sdt_external": _c("sdt_external", _D2, "External Regulation", temporal_stability=_DI, inference_tractability=_MD),
        "sdt_amotivation": _c("sdt_amotivation", _D2, "Amotivation", temporal_stability=_ST, inference_tractability=_LO),
        # Achievement Motivation (3)
        "ach_achievement": _c("ach_achievement", _D2, "Need for Achievement", temporal_stability=_TR, inference_tractability=_MD),
        "ach_affiliation": _c("ach_affiliation", _D2, "Need for Affiliation", temporal_stability=_TR, inference_tractability=_MD),
        "ach_power": _c("ach_power", _D2, "Need for Power", temporal_stability=_TR, inference_tractability=_MD),
        # Goal Orientation (2)
        "goal_mastery": _c("goal_mastery", _D2, "Mastery Goal Orientation", temporal_stability=_DI, inference_tractability=_MD),
        "goal_performance": _c("goal_performance", _D2, "Performance Goal Orientation", temporal_stability=_DI, inference_tractability=_MD),
        # Regulatory Focus (2)
        "reg_promotion": _c("reg_promotion", _D2, "Promotion Focus",
            temporal_stability=_DI, inference_tractability=_HI,
            research_effect_size="Regulatory fit increases persuasion 20-40% (Cesario et al., 2004)"),
        "reg_prevention": _c("reg_prevention", _D2, "Prevention Focus", temporal_stability=_DI, inference_tractability=_HI),
    },
)


# =============================================================================
# DOMAIN 3: COGNITIVE BIASES & HEURISTICS (22 edge + 10 reasoning = 32)
# =============================================================================

_D3 = "cognitive_biases"

DOMAIN_3_BIASES = Domain(
    domain_id=_D3,
    domain_name="Cognitive Biases & Heuristics",
    scoring_side=_US,
    construct_count=32,
    purpose="Systematic deviations from rational decision-making that advertising can ethically leverage.",
    primary_research="Kahneman (2011), Thaler & Sunstein (2008), Ariely (2008)",
    constructs={
        # Edge-level (22)
        "bias_anchoring": _c("bias_anchoring", _D3, "Anchoring Susceptibility", temporal_stability=_DI, inference_tractability=_HI),
        "bias_availability": _c("bias_availability", _D3, "Availability Heuristic", temporal_stability=_DI, inference_tractability=_MD),
        "bias_loss_aversion": _c("bias_loss_aversion", _D3, "Loss Aversion", temporal_stability=_DI, inference_tractability=_HI),
        "bias_endowment": _c("bias_endowment", _D3, "Endowment Effect", temporal_stability=_DI, inference_tractability=_MD),
        "bias_status_quo": _c("bias_status_quo", _D3, "Status Quo Bias", temporal_stability=_DI, inference_tractability=_HI),
        "bias_sunk_cost": _c("bias_sunk_cost", _D3, "Sunk Cost Susceptibility", temporal_stability=_DI, inference_tractability=_MD),
        "bias_framing": _c("bias_framing", _D3, "Framing Effect Sensitivity", temporal_stability=_DI, inference_tractability=_HI),
        "bias_bandwagon": _c("bias_bandwagon", _D3, "Bandwagon Susceptibility", temporal_stability=_DI, inference_tractability=_HI),
        "bias_peak_end": _c("bias_peak_end", _D3, "Peak-End Sensitivity", temporal_stability=_DI, inference_tractability=_MD),
        "bias_hyperbolic_discount": _c("bias_hyperbolic_discount", _D3, "Hyperbolic Discounting", temporal_stability=_DI, inference_tractability=_HI),
        "bias_present": _c("bias_present", _D3, "Present Bias", temporal_stability=_DI, inference_tractability=_HI),
        "bias_decoy": _c("bias_decoy", _D3, "Decoy Effect Susceptibility", temporal_stability=_DI, inference_tractability=_MD),
        "bias_choice_overload": _c("bias_choice_overload", _D3, "Choice Overload Sensitivity", temporal_stability=_DI, inference_tractability=_MD),
        "bias_default": _c("bias_default", _D3, "Default Effect", temporal_stability=_DI, inference_tractability=_MD),
        "bias_mere_exposure": _c("bias_mere_exposure", _D3, "Mere Exposure Sensitivity", temporal_stability=_DI, inference_tractability=_HI),
        "bias_halo": _c("bias_halo", _D3, "Halo Effect Susceptibility", temporal_stability=_DI, inference_tractability=_MD),
        "bias_contrast": _c("bias_contrast", _D3, "Contrast Effect", temporal_stability=_DI, inference_tractability=_MD),
        "bias_authority": _c("bias_authority", _D3, "Authority Bias", temporal_stability=_DI, inference_tractability=_HI),
        "bias_zero_risk": _c("bias_zero_risk", _D3, "Zero Risk Bias", temporal_stability=_DI, inference_tractability=_MD),
        "bias_affect_heuristic": _c("bias_affect_heuristic", _D3, "Affect Heuristic", temporal_stability=_DI, inference_tractability=_MD),
        "bias_ikea": _c("bias_ikea", _D3, "IKEA Effect", temporal_stability=_DI, inference_tractability=_MD),
        "bias_optimism": _c("bias_optimism", _D3, "Optimism Bias", temporal_stability=_DI, inference_tractability=_MD),
        # Reasoning-layer only (10)
        "bias_representativeness": _c("bias_representativeness", _D3, "Representativeness Heuristic", tier=_R, population_prior_only=True),
        "bias_confirmation": _c("bias_confirmation", _D3, "Confirmation Bias", tier=_R, population_prior_only=True),
        "bias_recency": _c("bias_recency", _D3, "Recency Bias", tier=_R, population_prior_only=True),
        "bias_primacy": _c("bias_primacy", _D3, "Primacy Effect", tier=_R, population_prior_only=True),
        "bias_recognition": _c("bias_recognition", _D3, "Recognition Heuristic", tier=_R, population_prior_only=True),
        "bias_dunning_kruger": _c("bias_dunning_kruger", _D3, "Dunning-Kruger Effect", tier=_R, population_prior_only=True),
        "bias_hindsight": _c("bias_hindsight", _D3, "Hindsight Bias", tier=_R, population_prior_only=True),
        "bias_belief_perseverance": _c("bias_belief_perseverance", _D3, "Belief Perseverance", tier=_R, population_prior_only=True),
        "bias_planning_fallacy": _c("bias_planning_fallacy", _D3, "Planning Fallacy", tier=_R, population_prior_only=True),
        "bias_self_serving": _c("bias_self_serving", _D3, "Self-Serving Bias", tier=_R, population_prior_only=True),
    },
)


# =============================================================================
# DOMAIN 4: PROSPECT THEORY & BEHAVIORAL ECONOMICS (10 constructs)
# =============================================================================

_D4 = "prospect_theory"

DOMAIN_4_PROSPECT_THEORY = Domain(
    domain_id=_D4,
    domain_name="Prospect Theory & Behavioral Economics",
    scoring_side=_US,
    construct_count=10,
    purpose="Parameters of the value function and probability weighting.",
    primary_research="Kahneman & Tversky (1979), Thaler (1985, 1999)",
    constructs={
        "pt_loss_aversion_coeff": _c("pt_loss_aversion_coeff", _D4, "Loss Aversion Coefficient", range_min=1.0, range_max=4.0, temporal_stability=_TR, inference_tractability=_MD),
        "pt_risk_aversion_gains": _c("pt_risk_aversion_gains", _D4, "Risk Aversion in Gains", temporal_stability=_DI, inference_tractability=_MD),
        "pt_risk_seeking_losses": _c("pt_risk_seeking_losses", _D4, "Risk Seeking in Losses", temporal_stability=_DI, inference_tractability=_MD),
        "pt_prob_weight_small": _c("pt_prob_weight_small", _D4, "Probability Weighting (Small)", temporal_stability=_TR, inference_tractability=_LO),
        "pt_prob_weight_large": _c("pt_prob_weight_large", _D4, "Probability Weighting (Large)", temporal_stability=_TR, inference_tractability=_LO),
        "pt_reference_sensitivity": _c("pt_reference_sensitivity", _D4, "Reference Point Sensitivity", temporal_stability=_DI, inference_tractability=_MD),
        # Mental Accounting (4)
        "ma_segregation": _c("ma_segregation", _D4, "Gain Segregation Tendency", temporal_stability=_DI, inference_tractability=_MD),
        "ma_budget_rigidity": _c("ma_budget_rigidity", _D4, "Mental Budget Rigidity", temporal_stability=_DI, inference_tractability=_MD),
        "ma_transaction_utility": _c("ma_transaction_utility", _D4, "Transaction Utility Sensitivity", temporal_stability=_DI, inference_tractability=_HI),
        "ma_payment_coupling": _c("ma_payment_coupling", _D4, "Payment-Consumption Coupling", temporal_stability=_DI, inference_tractability=_MD),
    },
)


# =============================================================================
# DOMAIN 5: APPROACH/AVOIDANCE & NEUROPSYCHOLOGICAL (8 constructs)
# =============================================================================

_D5 = "approach_avoidance"

DOMAIN_5_APPROACH_AVOIDANCE = Domain(
    domain_id=_D5,
    domain_name="Approach/Avoidance & Neuropsychological",
    scoring_side=_US,
    construct_count=8,
    purpose="Fundamental motivational systems governing approach vs. avoidance.",
    primary_research="Carver & White (1994), Gray (1970)",
    constructs={
        "bis_inhibition": _c("bis_inhibition", _D5, "Behavioral Inhibition", temporal_stability=_TR, inference_tractability=_MD),
        "bas_drive": _c("bas_drive", _D5, "BAS Drive", temporal_stability=_TR, inference_tractability=_MD),
        "bas_fun_seeking": _c("bas_fun_seeking", _D5, "BAS Fun Seeking", temporal_stability=_TR, inference_tractability=_MD),
        "bas_reward_responsive": _c("bas_reward_responsive", _D5, "BAS Reward Responsiveness", temporal_stability=_TR, inference_tractability=_MD),
        "approach_motivation": _c("approach_motivation", _D5, "Approach Motivation", temporal_stability=_DI, inference_tractability=_HI, derived_from=["bas_drive", "bas_fun_seeking", "bas_reward_responsive"]),
        "avoidance_motivation": _c("avoidance_motivation", _D5, "Avoidance Motivation", temporal_stability=_DI, inference_tractability=_HI, derived_from=["bis_inhibition"]),
        "reward_sensitivity": _c("reward_sensitivity", _D5, "Reward Sensitivity", temporal_stability=_TR, inference_tractability=_MD),
        "threat_sensitivity": _c("threat_sensitivity", _D5, "Threat Sensitivity", temporal_stability=_TR, inference_tractability=_MD),
    },
)


# =============================================================================
# DOMAIN 6: SOCIAL INFLUENCE SUSCEPTIBILITY (22 constructs)
# =============================================================================

_D6 = "social_influence"

DOMAIN_6_SOCIAL_INFLUENCE = Domain(
    domain_id=_D6,
    domain_name="Social Influence Susceptibility",
    scoring_side=_US,
    construct_count=22,
    purpose="Individual differences in susceptibility to specific social influence tactics.",
    primary_research="Cialdini (2021), Kelman (1958)",
    constructs={
        "ci_reciprocity": _c("ci_reciprocity", _D6, "Reciprocity Susceptibility", temporal_stability=_DI, inference_tractability=_HI),
        "ci_commitment": _c("ci_commitment", _D6, "Commitment/Consistency Susceptibility", temporal_stability=_DI, inference_tractability=_HI),
        "ci_social_proof": _c("ci_social_proof", _D6, "Social Proof Susceptibility", temporal_stability=_DI, inference_tractability=_HI),
        "ci_authority": _c("ci_authority", _D6, "Authority Susceptibility", temporal_stability=_DI, inference_tractability=_HI),
        "ci_liking": _c("ci_liking", _D6, "Liking Susceptibility", temporal_stability=_DI, inference_tractability=_MD),
        "ci_scarcity": _c("ci_scarcity", _D6, "Scarcity Susceptibility", temporal_stability=_DI, inference_tractability=_HI),
        "ci_unity": _c("ci_unity", _D6, "Unity Susceptibility", temporal_stability=_DI, inference_tractability=_MD),
        "soc_conformity": _c("soc_conformity", _D6, "Conformity Tendency", temporal_stability=_DI, inference_tractability=_MD),
        "soc_normative_influence": _c("soc_normative_influence", _D6, "Normative Influence Susceptibility", temporal_stability=_DI, inference_tractability=_MD),
        "soc_informational_influence": _c("soc_informational_influence", _D6, "Informational Influence Susceptibility", temporal_stability=_DI, inference_tractability=_MD),
        "soc_opinion_leadership": _c("soc_opinion_leadership", _D6, "Opinion Leadership", temporal_stability=_DI, inference_tractability=_MD),
        "soc_compare_upward": _c("soc_compare_upward", _D6, "Upward Social Comparison", temporal_stability=_DI, inference_tractability=_MD),
        "soc_compare_downward": _c("soc_compare_downward", _D6, "Downward Social Comparison", temporal_stability=_DI, inference_tractability=_LO),
        "soc_parasocial": _c("soc_parasocial", _D6, "Parasocial Propensity", temporal_stability=_DI, inference_tractability=_MD),
        "soc_ref_aspirational": _c("soc_ref_aspirational", _D6, "Aspirational Reference Group Influence", temporal_stability=_DI, inference_tractability=_MD),
        "soc_ref_dissociative": _c("soc_ref_dissociative", _D6, "Dissociative Reference Group Influence", temporal_stability=_DI, inference_tractability=_LO),
        "ci_sp_quantity": _c("ci_sp_quantity", _D6, "Social Proof: Quantity Sensitivity", temporal_stability=_DI, inference_tractability=_HI),
        "ci_sp_similarity": _c("ci_sp_similarity", _D6, "Social Proof: Similarity Sensitivity", temporal_stability=_DI, inference_tractability=_MD),
        "ci_sp_expert": _c("ci_sp_expert", _D6, "Social Proof: Expert Sensitivity", temporal_stability=_DI, inference_tractability=_MD),
        "ci_sc_quantity": _c("ci_sc_quantity", _D6, "Scarcity: Limited Quantity Sensitivity", temporal_stability=_DI, inference_tractability=_HI),
        "ci_sc_time": _c("ci_sc_time", _D6, "Scarcity: Limited Time Sensitivity", temporal_stability=_DI, inference_tractability=_HI),
        "ci_sc_exclusivity": _c("ci_sc_exclusivity", _D6, "Scarcity: Exclusivity Sensitivity", temporal_stability=_DI, inference_tractability=_MD),
    },
)


# =============================================================================
# DOMAIN 7: PERSUASION PROCESSING (12 constructs)
# =============================================================================

_D7 = "persuasion_processing"

DOMAIN_7_PERSUASION = Domain(
    domain_id=_D7,
    domain_name="Persuasion Processing",
    scoring_side=_US,
    construct_count=12,
    purpose="How individuals process persuasive messages.",
    primary_research="Petty & Cacioppo (1986), Green & Brock (2000), Friestad & Wright (1994)",
    constructs={
        "elm_central": _c("elm_central", _D7, "Central Route Preference", temporal_stability=_DI, inference_tractability=_HI),
        "elm_peripheral": _c("elm_peripheral", _D7, "Peripheral Route Preference", temporal_stability=_DI, inference_tractability=_HI),
        "pk_agent": _c("pk_agent", _D7, "Agent Knowledge", temporal_stability=_DI, inference_tractability=_MD),
        "pk_awareness": _c("pk_awareness", _D7, "Attempt Awareness", temporal_stability=_DI, inference_tractability=_MD),
        "pk_coping": _c("pk_coping", _D7, "Coping Behavior", temporal_stability=_DI, inference_tractability=_MD),
        "nt_immersion": _c("nt_immersion", _D7, "Narrative Immersion", temporal_stability=_DI, inference_tractability=_MD),
        "nt_character_id": _c("nt_character_id", _D7, "Character Identification", temporal_stability=_DI, inference_tractability=_MD),
        "nt_imagery": _c("nt_imagery", _D7, "Mental Imagery Vividness", temporal_stability=_TR, inference_tractability=_LO),
        "nt_emotional": _c("nt_emotional", _D7, "Emotional Engagement", temporal_stability=_ST, inference_tractability=_MD),
        "pers_dissonance": _c("pers_dissonance", _D7, "Cognitive Dissonance Sensitivity", temporal_stability=_DI, inference_tractability=_MD),
        "pers_reactance": _c("pers_reactance", _D7, "Psychological Reactance", temporal_stability=_TR, inference_tractability=_HI),
        "pers_skepticism": _c("pers_skepticism", _D7, "Ad Skepticism", temporal_stability=_TR, inference_tractability=_HI),
    },
)


# =============================================================================
# DOMAIN 8: DECISION MAKING STYLE (17 constructs)
# =============================================================================

_D8 = "decision_making"

DOMAIN_8_DECISION_MAKING = Domain(
    domain_id=_D8,
    domain_name="Decision Making Style",
    scoring_side=_US,
    construct_count=17,
    purpose="How individuals approach decisions.",
    primary_research="Schwartz et al. (2002), Cacioppo & Petty (1982), Kruglanski (1994)",
    constructs={
        "dm_system1": _c("dm_system1", _D8, "System 1 Dominance", temporal_stability=_DI, inference_tractability=_HI),
        "dm_system2": _c("dm_system2", _D8, "System 2 Engagement", temporal_stability=_DI, inference_tractability=_HI),
        "dm_effort": _c("dm_effort", _D8, "Cognitive Effort Willingness", temporal_stability=_DI, inference_tractability=_HI),
        "dm_maximizer": _c("dm_maximizer", _D8, "Maximizer Tendency", temporal_stability=_TR, inference_tractability=_HI),
        "dm_satisficer": _c("dm_satisficer", _D8, "Satisficer Tendency", temporal_stability=_TR, inference_tractability=_HI),
        "dm_confidence": _c("dm_confidence", _D8, "Decision Confidence", temporal_stability=_ST, inference_tractability=_MD),
        "dm_regret": _c("dm_regret", _D8, "Regret Sensitivity", temporal_stability=_DI, inference_tractability=_MD),
        "dm_involve_cog": _c("dm_involve_cog", _D8, "Cognitive Involvement", temporal_stability=_ST, inference_tractability=_MD),
        "dm_involve_aff": _c("dm_involve_aff", _D8, "Affective Involvement", temporal_stability=_ST, inference_tractability=_MD),
        "dm_involve_personal": _c("dm_involve_personal", _D8, "Personal Relevance Involvement", temporal_stability=_ST, inference_tractability=_MD),
        "dm_impulse_cog": _c("dm_impulse_cog", _D8, "Impulse Buying (Cognitive)", temporal_stability=_DI, inference_tractability=_HI),
        "dm_impulse_aff": _c("dm_impulse_aff", _D8, "Impulse Buying (Affective)", temporal_stability=_DI, inference_tractability=_HI),
        "dm_variety": _c("dm_variety", _D8, "Variety Seeking", temporal_stability=_DI, inference_tractability=_HI),
        "dm_loyalty_beh": _c("dm_loyalty_beh", _D8, "Brand Loyalty (Behavioral)", temporal_stability=_DI, inference_tractability=_HI),
        "dm_loyalty_att": _c("dm_loyalty_att", _D8, "Brand Loyalty (Attitudinal)", temporal_stability=_DI, inference_tractability=_MD),
        "dm_info_search": _c("dm_info_search", _D8, "Information Search Intensity", temporal_stability=_DI, inference_tractability=_HI),
        "dm_nfc": _c("dm_nfc", _D8, "Need for Cognition", temporal_stability=_TR, inference_tractability=_HI),
    },
)


# =============================================================================
# DOMAIN 9: STRATEGIC & FAIRNESS ORIENTATION (10 constructs)
# =============================================================================

_D9 = "strategic_fairness"

DOMAIN_9_STRATEGIC = Domain(
    domain_id=_D9,
    domain_name="Strategic & Fairness Orientation",
    scoring_side=_US,
    construct_count=10,
    purpose="Cooperative vs. competitive orientation, fairness sensitivity, trust propensity.",
    primary_research="Van Lange (1999), Fehr & Schmidt (1999), Spence (1973)",
    constructs={
        "svo_cooperative": _c("svo_cooperative", _D9, "Cooperative Orientation", temporal_stability=_TR, inference_tractability=_MD),
        "svo_competitive": _c("svo_competitive", _D9, "Competitive Orientation", temporal_stability=_TR, inference_tractability=_MD),
        "svo_individualistic": _c("svo_individualistic", _D9, "Individualistic Orientation", temporal_stability=_TR, inference_tractability=_MD),
        "svo_altruistic": _c("svo_altruistic", _D9, "Altruistic Orientation", temporal_stability=_TR, inference_tractability=_MD),
        "fair_inequity_aversion": _c("fair_inequity_aversion", _D9, "Inequity Aversion", temporal_stability=_TR, inference_tractability=_MD),
        "fair_procedural": _c("fair_procedural", _D9, "Procedural Fairness Sensitivity", temporal_stability=_DI, inference_tractability=_MD),
        "fair_distributive": _c("fair_distributive", _D9, "Distributive Fairness Sensitivity", temporal_stability=_DI, inference_tractability=_MD),
        "strat_trust": _c("strat_trust", _D9, "Trust Propensity", temporal_stability=_TR, inference_tractability=_HI),
        "strat_quality_signal": _c("strat_quality_signal", _D9, "Quality Signal Sensitivity", temporal_stability=_DI, inference_tractability=_HI),
        "strat_price_signal": _c("strat_price_signal", _D9, "Price Signal Sensitivity", temporal_stability=_DI, inference_tractability=_HI),
    },
)


# =============================================================================
# DOMAIN 10: CULTURAL DIMENSIONS (11 constructs)
# =============================================================================

_D10 = "cultural"

DOMAIN_10_CULTURAL = Domain(
    domain_id=_D10,
    domain_name="Cultural Dimensions",
    scoring_side=_US,
    construct_count=11,
    purpose="Cultural-level psychological orientation modulating all other constructs.",
    primary_research="Hofstede (2001), Markus & Kitayama (1991), Gelfand (2011)",
    constructs={
        "cult_power_distance": _c("cult_power_distance", _D10, "Power Distance", temporal_stability=_TR, inference_tractability=_MD),
        "cult_individualism": _c("cult_individualism", _D10, "Individualism-Collectivism", temporal_stability=_TR, inference_tractability=_MD),
        "cult_masculinity": _c("cult_masculinity", _D10, "Masculinity-Femininity", temporal_stability=_TR, inference_tractability=_LO),
        "cult_uncertainty_avoid": _c("cult_uncertainty_avoid", _D10, "Uncertainty Avoidance", temporal_stability=_TR, inference_tractability=_MD),
        "cult_long_term": _c("cult_long_term", _D10, "Long-Term Orientation", temporal_stability=_TR, inference_tractability=_MD),
        "cult_indulgence": _c("cult_indulgence", _D10, "Indulgence-Restraint", temporal_stability=_TR, inference_tractability=_MD),
        "cult_independent_self": _c("cult_independent_self", _D10, "Independent Self-Construal", temporal_stability=_TR, inference_tractability=_MD),
        "cult_interdependent_self": _c("cult_interdependent_self", _D10, "Interdependent Self-Construal", temporal_stability=_TR, inference_tractability=_MD),
        "cult_tightness": _c("cult_tightness", _D10, "Cultural Tightness", temporal_stability=_TR, inference_tractability=_LO),
        "cult_performance": _c("cult_performance", _D10, "Performance Orientation", temporal_stability=_TR, inference_tractability=_LO),
        "cult_humane": _c("cult_humane", _D10, "Humane Orientation", temporal_stability=_TR, inference_tractability=_LO),
    },
)


# =============================================================================
# DOMAIN 11: RISK & UNCERTAINTY (12 constructs)
# =============================================================================

_D11 = "risk_uncertainty"

DOMAIN_11_RISK = Domain(
    domain_id=_D11,
    domain_name="Risk & Uncertainty",
    scoring_side=_US,
    construct_count=12,
    purpose="Individual differences in risk perception, tolerance, and uncertainty response.",
    primary_research="Ellsberg (1961), Slovic (2000)",
    constructs={
        "risk_financial": _c("risk_financial", _D11, "Perceived Risk: Financial", temporal_stability=_ST, inference_tractability=_HI),
        "risk_performance": _c("risk_performance", _D11, "Perceived Risk: Performance", temporal_stability=_ST, inference_tractability=_MD),
        "risk_social": _c("risk_social", _D11, "Perceived Risk: Social", temporal_stability=_ST, inference_tractability=_MD),
        "risk_psychological": _c("risk_psychological", _D11, "Perceived Risk: Psychological", temporal_stability=_ST, inference_tractability=_LO),
        "risk_physical": _c("risk_physical", _D11, "Perceived Risk: Physical", temporal_stability=_ST, inference_tractability=_LO),
        "risk_time": _c("risk_time", _D11, "Perceived Risk: Time", temporal_stability=_ST, inference_tractability=_MD),
        "risk_ambiguity_aversion": _c("risk_ambiguity_aversion", _D11, "Ambiguity Aversion", temporal_stability=_TR, inference_tractability=_MD),
        "risk_uncertainty_tolerance": _c("risk_uncertainty_tolerance", _D11, "Uncertainty Tolerance", temporal_stability=_TR, inference_tractability=_MD),
        "risk_regret_aversion": _c("risk_regret_aversion", _D11, "Regret Aversion", temporal_stability=_DI, inference_tractability=_MD),
        "risk_anticipated_regret": _c("risk_anticipated_regret", _D11, "Anticipated Regret", temporal_stability=_ST, inference_tractability=_MD),
        "risk_tolerance": _c("risk_tolerance", _D11, "Risk Tolerance (General)", temporal_stability=_TR, inference_tractability=_HI),
        "risk_domain_specific": _c("risk_domain_specific", _D11, "Domain-Specific Risk Attitude", temporal_stability=_DI, inference_tractability=_MD),
    },
)


# =============================================================================
# DOMAIN 12: SELF & IDENTITY (12 constructs)
# =============================================================================

_D12 = "self_identity"

DOMAIN_12_SELF_IDENTITY = Domain(
    domain_id=_D12,
    domain_name="Self & Identity",
    scoring_side=_US,
    construct_count=12,
    purpose="Self-concept structures and identity dynamics.",
    primary_research="Higgins (1987), Bandura (1977), Markus & Nurius (1986)",
    constructs={
        "self_actual": _c("self_actual", _D12, "Actual Self", temporal_stability=_TR, inference_tractability=_MD),
        "self_ideal": _c("self_ideal", _D12, "Ideal Self", temporal_stability=_DI, inference_tractability=_MD),
        "self_ought": _c("self_ought", _D12, "Ought Self", temporal_stability=_DI, inference_tractability=_LO),
        "self_actual_ideal_gap": _c("self_actual_ideal_gap", _D12, "Actual-Ideal Gap", temporal_stability=_DI, inference_tractability=_MD),
        "self_actual_ought_gap": _c("self_actual_ought_gap", _D12, "Actual-Ought Gap", temporal_stability=_DI, inference_tractability=_LO),
        "self_efficacy": _c("self_efficacy", _D12, "Self-Efficacy", temporal_stability=_DI, inference_tractability=_MD),
        "self_esteem": _c("self_esteem", _D12, "Self-Esteem", temporal_stability=_DI, inference_tractability=_MD,
            ethical_note="NEVER target low self-esteem. Use for appropriate messaging tone only."),
        "self_identity_salience": _c("self_identity_salience", _D12, "Identity Salience", temporal_stability=_ST, inference_tractability=_MD),
        "self_hoped": _c("self_hoped", _D12, "Hoped-For Self", temporal_stability=_DI, inference_tractability=_MD),
        "self_feared": _c("self_feared", _D12, "Feared Self", temporal_stability=_DI, inference_tractability=_LO),
        "self_clarity": _c("self_clarity", _D12, "Self-Concept Clarity", temporal_stability=_DI, inference_tractability=_LO),
        "self_threat_sensitivity": _c("self_threat_sensitivity", _D12, "Identity Threat Sensitivity", temporal_stability=_DI, inference_tractability=_LO),
    },
)


# =============================================================================
# DOMAIN 13: INFORMATION PROCESSING STYLE (9 constructs)
# =============================================================================

_D13 = "information_processing"

DOMAIN_13_INFORMATION_PROCESSING = Domain(
    domain_id=_D13,
    domain_name="Information Processing Style",
    scoring_side=_US,
    construct_count=10,
    purpose="How information is encoded, processed, and retrieved.",
    primary_research="Cacioppo & Petty (1982), Kruglanski (1994)",
    constructs={
        "ip_need_closure": _c("ip_need_closure", _D13, "Need for Closure", temporal_stability=_TR, inference_tractability=_MD),
        "ip_cognitive_complexity": _c("ip_cognitive_complexity", _D13, "Cognitive Complexity", temporal_stability=_TR, inference_tractability=_MD),
        "ip_visual_pref": _c("ip_visual_pref", _D13, "Visual Processing Preference", temporal_stability=_TR, inference_tractability=_HI),
        "ip_verbal_pref": _c("ip_verbal_pref", _D13, "Verbal Processing Preference", temporal_stability=_TR, inference_tractability=_HI),
        "ip_holistic": _c("ip_holistic", _D13, "Holistic Thinking", temporal_stability=_TR, inference_tractability=_MD),
        "ip_analytic": _c("ip_analytic", _D13, "Analytic Thinking", temporal_stability=_TR, inference_tractability=_MD),
        "ip_field_independence": _c("ip_field_independence", _D13, "Field Independence", temporal_stability=_TR, inference_tractability=_LO),
        "ip_overload_threshold": _c("ip_overload_threshold", _D13, "Information Overload Threshold", temporal_stability=_DI, inference_tractability=_MD),
        "ip_attention_span": _c("ip_attention_span", _D13, "Attention Span", temporal_stability=_ST, inference_tractability=_HI),
        # Cognitive Load — referenced in cross-domain dependency map as state modulator
        "cognitive_load": _c("cognitive_load", _D13, "Current Cognitive Load", temporal_stability=_ST, inference_tractability=_HI),
    },
)


# =============================================================================
# DOMAIN 14: CONSUMER-SPECIFIC TRAITS (16 constructs)
# =============================================================================

_D14 = "consumer_traits"

DOMAIN_14_CONSUMER = Domain(
    domain_id=_D14,
    domain_name="Consumer-Specific Traits",
    scoring_side=_US,
    construct_count=16,
    purpose="Traits specific to consumer behavior and shopping psychology.",
    primary_research="Richins (1992), Tian et al. (2001)",
    constructs={
        "mat_centrality": _c("mat_centrality", _D14, "Materialism: Centrality", temporal_stability=_TR, inference_tractability=_HI),
        "mat_success": _c("mat_success", _D14, "Materialism: Success", temporal_stability=_TR, inference_tractability=_HI),
        "mat_happiness": _c("mat_happiness", _D14, "Materialism: Happiness", temporal_stability=_TR, inference_tractability=_MD),
        "nfu_creative": _c("nfu_creative", _D14, "Need for Uniqueness: Creative Choice", temporal_stability=_TR, inference_tractability=_HI),
        "nfu_unpopular": _c("nfu_unpopular", _D14, "Need for Uniqueness: Unpopular Choice", temporal_stability=_TR, inference_tractability=_MD),
        "nfu_avoid_similar": _c("nfu_avoid_similar", _D14, "Need for Uniqueness: Avoidance of Similarity", temporal_stability=_TR, inference_tractability=_HI),
        "con_brand": _c("con_brand", _D14, "Brand Consciousness", temporal_stability=_DI, inference_tractability=_HI),
        "con_price": _c("con_price", _D14, "Price Consciousness", temporal_stability=_DI, inference_tractability=_HI),
        "con_quality": _c("con_quality", _D14, "Quality Consciousness", temporal_stability=_DI, inference_tractability=_HI),
        "con_fashion": _c("con_fashion", _D14, "Fashion Consciousness", temporal_stability=_DI, inference_tractability=_MD),
        "con_compulsive": _c("con_compulsive", _D14, "Compulsive Buying", temporal_stability=_DI, inference_tractability=_HI,
            ethical_note="Score for detection/protection. NEVER exploit compulsive buying tendency."),
        "con_deal_prone": _c("con_deal_prone", _D14, "Deal Proneness", temporal_stability=_DI, inference_tractability=_HI),
        "con_coupon_prone": _c("con_coupon_prone", _D14, "Coupon Proneness", temporal_stability=_DI, inference_tractability=_HI),
        "con_hedonic": _c("con_hedonic", _D14, "Hedonic Shopping Motivation", temporal_stability=_DI, inference_tractability=_HI),
        "con_utilitarian": _c("con_utilitarian", _D14, "Utilitarian Shopping Motivation", temporal_stability=_DI, inference_tractability=_HI),
        "con_ethnocentrism": _c("con_ethnocentrism", _D14, "Consumer Ethnocentrism", temporal_stability=_TR, inference_tractability=_MD),
    },
)


# =============================================================================
# DOMAIN 15: IMPLICIT & NONCONSCIOUS PROCESSING (10 constructs)
# =============================================================================

_D15 = "implicit_processing"

DOMAIN_15_IMPLICIT = Domain(
    domain_id=_D15,
    domain_name="Implicit & Nonconscious Processing",
    scoring_side=_US,
    construct_count=10,
    purpose="Processing fluency, priming effects, somatic markers.",
    primary_research="Zajonc (1968), Damasio (1994), Winkielman et al. (2003)",
    constructs={
        "imp_perceptual_fluency": _c("imp_perceptual_fluency", _D15, "Perceptual Fluency Sensitivity", temporal_stability=_TR, inference_tractability=_MD),
        "imp_conceptual_fluency": _c("imp_conceptual_fluency", _D15, "Conceptual Fluency Sensitivity", temporal_stability=_TR, inference_tractability=_MD),
        "imp_mere_exposure": _c("imp_mere_exposure", _D15, "Mere Exposure Sensitivity", temporal_stability=_TR, inference_tractability=_HI),
        "imp_semantic_priming": _c("imp_semantic_priming", _D15, "Semantic Priming Susceptibility", temporal_stability=_DI, inference_tractability=_MD),
        "imp_affective_priming": _c("imp_affective_priming", _D15, "Affective Priming Susceptibility", temporal_stability=_DI, inference_tractability=_MD),
        "imp_somatic_marker": _c("imp_somatic_marker", _D15, "Somatic Marker Sensitivity", temporal_stability=_TR, inference_tractability=_MD),
        "imp_self_esteem": _c("imp_self_esteem", _D15, "Implicit Self-Esteem", temporal_stability=_TR, inference_tractability=_LO),
        "imp_brand_attitude": _c("imp_brand_attitude", _D15, "Implicit Brand Attitude", temporal_stability=_ST, inference_tractability=_MD),
        "imp_affect_info": _c("imp_affect_info", _D15, "Affect-as-Information Susceptibility", temporal_stability=_TR, inference_tractability=_MD),
        "imp_nostalgia": _c("imp_nostalgia", _D15, "Nostalgia Proneness", temporal_stability=_TR, inference_tractability=_MD),
    },
)


# =============================================================================
# DOMAIN 16: TEMPORAL PSYCHOLOGY (12 constructs)
# =============================================================================

_D16 = "temporal"

DOMAIN_16_TEMPORAL = Domain(
    domain_id=_D16,
    domain_name="Temporal Psychology",
    scoring_side=_US,
    construct_count=12,
    purpose="Time perspective, construal level, temporal decision parameters.",
    primary_research="Zimbardo & Boyd (1999), Trope & Liberman (2003)",
    constructs={
        "tp_past_neg": _c("tp_past_neg", _D16, "Past Negative Time Perspective", temporal_stability=_TR, inference_tractability=_MD),
        "tp_past_pos": _c("tp_past_pos", _D16, "Past Positive Time Perspective", temporal_stability=_TR, inference_tractability=_MD),
        "tp_present_hed": _c("tp_present_hed", _D16, "Present Hedonistic", temporal_stability=_TR, inference_tractability=_HI),
        "tp_present_fat": _c("tp_present_fat", _D16, "Present Fatalistic", temporal_stability=_TR, inference_tractability=_LO),
        "tp_future": _c("tp_future", _D16, "Future Time Perspective", temporal_stability=_TR, inference_tractability=_HI),
        "clt_temporal": _c("clt_temporal", _D16, "Construal: Temporal Distance", temporal_stability=_ST, inference_tractability=_HI),
        "clt_spatial": _c("clt_spatial", _D16, "Construal: Spatial Distance", temporal_stability=_ST, inference_tractability=_MD),
        "clt_social": _c("clt_social", _D16, "Construal: Social Distance", temporal_stability=_ST, inference_tractability=_MD),
        "clt_hypothetical": _c("clt_hypothetical", _D16, "Construal: Hypothetical Distance", temporal_stability=_ST, inference_tractability=_MD),
        "temp_discount_rate": _c("temp_discount_rate", _D16, "Discount Rate", temporal_stability=_DI, inference_tractability=_HI),
        "temp_future_perspective": _c("temp_future_perspective", _D16, "Future Time Perspective", temporal_stability=_DI, inference_tractability=_MD),
        "temp_consistency": _c("temp_consistency", _D16, "Intertemporal Consistency", temporal_stability=_DI, inference_tractability=_MD),
    },
)


# =============================================================================
# DOMAIN 17: ATTACHMENT & RELATIONSHIP STYLE (6 constructs)
# =============================================================================

_D17 = "attachment"

DOMAIN_17_ATTACHMENT = Domain(
    domain_id=_D17,
    domain_name="Attachment & Relationship Style",
    scoring_side=_US,
    construct_count=6,
    purpose="Trait-level attachment orientation determining brand relationship formation.",
    primary_research="Hazan & Shaver (1987), Thomson et al. (2005), Bowlby (1969)",
    constructs={
        "attach_anxiety": _c("attach_anxiety", _D17, "Attachment Anxiety", temporal_stability=_TR, inference_tractability=_MD),
        "attach_avoidance": _c("attach_avoidance", _D17, "Attachment Avoidance", temporal_stability=_TR, inference_tractability=_MD),
        "attach_security": _c("attach_security", _D17, "Attachment Security", temporal_stability=_TR, inference_tractability=_MD,
            derived_from=["attach_anxiety", "attach_avoidance"]),
        "attach_brand_separation": _c("attach_brand_separation", _D17, "Brand Separation Distress", temporal_stability=_DI, inference_tractability=_MD),
        "attach_brand_proximity": _c("attach_brand_proximity", _D17, "Brand Proximity Seeking", temporal_stability=_DI, inference_tractability=_MD),
        "attach_brand_haven": _c("attach_brand_haven", _D17, "Brand Safe Haven", temporal_stability=_DI, inference_tractability=_MD),
    },
)


# =============================================================================
# DOMAIN 18: REGULATORY MODE (2 constructs)
# =============================================================================

_D18 = "regulatory_mode"

DOMAIN_18_REGULATORY_MODE = Domain(
    domain_id=_D18,
    domain_name="Regulatory Mode",
    scoring_side=_US,
    construct_count=2,
    purpose="Locomotion vs. Assessment — distinct from Regulatory Focus.",
    primary_research="Kruglanski et al. (2000)",
    constructs={
        "rm_locomotion": _c("rm_locomotion", _D18, "Locomotion", temporal_stability=_TR, inference_tractability=_MD),
        "rm_assessment": _c("rm_assessment", _D18, "Assessment", temporal_stability=_TR, inference_tractability=_MD),
    },
)


# =============================================================================
# DOMAIN 19: EVOLUTIONARY CONSUMER PSYCHOLOGY (28 constructs) — NEW CRITICAL
# =============================================================================

_D19 = "evolutionary"

DOMAIN_19_EVOLUTIONARY = Domain(
    domain_id=_D19,
    domain_name="Evolutionary Consumer Psychology",
    scoring_side=_US,
    construct_count=28,
    purpose="Evolved psychological mechanisms shaping consumer behavior.",
    primary_research="Griskevicius & Kenrick (2013), Saad (2007, 2013), Kenrick et al. (2010)",
    adam_relevance="Captures WHY mechanisms work. Scarcity works because of evolved resource competition.",
    constructs={
        # Fundamental Motive Framework (7)
        "evo_self_protection": _c("evo_self_protection", _D19, "Self-Protection Motive Sensitivity", temporal_stability=_DI, inference_tractability=_MD, state_modulation=True, mechanism_connections=["loss_aversion", "status_quo_bias", "authority_bias"]),
        "evo_disease_avoidance": _c("evo_disease_avoidance", _D19, "Behavioral Immune System Sensitivity", temporal_stability=_DI, inference_tractability=_MD, state_modulation=True),
        "evo_affiliation": _c("evo_affiliation", _D19, "Affiliation Motive Sensitivity", temporal_stability=_DI, inference_tractability=_HI, state_modulation=True, mechanism_connections=["social_proof", "bandwagon", "unity"]),
        "evo_status": _c("evo_status", _D19, "Status/Prestige Motive Sensitivity", temporal_stability=_DI, inference_tractability=_HI, state_modulation=True, mechanism_connections=["scarcity", "authority"]),
        "evo_mate_acquisition": _c("evo_mate_acquisition", _D19, "Mate Acquisition Motive Sensitivity", temporal_stability=_DI, inference_tractability=_MD, state_modulation=True, ethical_note="Score for messaging optimization only. Never exploit mate-seeking anxiety."),
        "evo_mate_retention": _c("evo_mate_retention", _D19, "Mate Retention Motive Sensitivity", temporal_stability=_DI, inference_tractability=_MD, state_modulation=True),
        "evo_kin_care": _c("evo_kin_care", _D19, "Kin Care Motive Sensitivity", temporal_stability=_DI, inference_tractability=_HI, state_modulation=True, mechanism_connections=["loss_aversion", "zero_risk_bias"]),
        # Life History Strategy (1)
        "evo_life_history": _c("evo_life_history", _D19, "Life History Strategy Speed", temporal_stability=_TR, inference_tractability=_HI),
        # Costly Signaling (2)
        "evo_conspicuous": _c("evo_conspicuous", _D19, "Conspicuous Consumption Tendency", temporal_stability=_DI, inference_tractability=_HI),
        "evo_conspicuous_green": _c("evo_conspicuous_green", _D19, "Conspicuous Conservation", temporal_stability=_DI, inference_tractability=_MD),
        # Mismatch Sensitivity (2)
        "evo_food_scarcity": _c("evo_food_scarcity", _D19, "Food Scarcity Psychology Activation", temporal_stability=_DI, inference_tractability=_MD, state_modulation=True),
        "evo_coalitional": _c("evo_coalitional", _D19, "Coalitional Psychology Sensitivity", temporal_stability=_DI, inference_tractability=_HI, mechanism_connections=["unity", "social_proof"]),
        "evo_dominance_prestige": _c("evo_dominance_prestige", _D19, "Dominance vs. Prestige Orientation", temporal_stability=_TR, inference_tractability=_MD),
        # Reciprocal Altruism (2)
        "evo_reciprocal": _c("evo_reciprocal", _D19, "Reciprocal Altruism Sensitivity", temporal_stability=_TR, inference_tractability=_HI, mechanism_connections=["reciprocity"]),
        "evo_cheater_detection": _c("evo_cheater_detection", _D19, "Cheater Detection Sensitivity", temporal_stability=_TR, inference_tractability=_MD),
        # Evolved Aesthetics (2)
        "evo_savanna_pref": _c("evo_savanna_pref", _D19, "Savanna/Nature Aesthetic Preference", temporal_stability=_TR, inference_tractability=_MD),
        "evo_symmetry": _c("evo_symmetry", _D19, "Symmetry Preference Intensity", temporal_stability=_TR, inference_tractability=_LO, tier=_R),
        # Parental Investment (1)
        "evo_parental_invest": _c("evo_parental_invest", _D19, "Parental Investment Orientation", temporal_stability=_DI, inference_tractability=_HI, state_modulation=True),
        # Inclusive Fitness (1)
        "evo_kin_altruism": _c("evo_kin_altruism", _D19, "Kin Altruism Activation Level", temporal_stability=_ST, inference_tractability=_HI),
        # Loss Aversion as Evolved Endowment (1)
        "evo_possession_attach": _c("evo_possession_attach", _D19, "Possession Attachment Intensity", temporal_stability=_DI, inference_tractability=_MD, state_modulation=True, mechanism_connections=["endowment_effect", "loss_aversion"]),
        # Resource Allocation (1)
        "evo_scarcity_psych": _c("evo_scarcity_psych", _D19, "Subjective Resource Scarcity", temporal_stability=_ST, inference_tractability=_MD, mechanism_connections=["present_bias", "hyperbolic_discounting", "tunneling"]),
        # Territorial (1)
        "evo_territorial": _c("evo_territorial", _D19, "Territorial/Ownership Marking Tendency", temporal_stability=_DI, inference_tractability=_MD, mechanism_connections=["IKEA_effect", "endowment_effect"]),
        # Environmental Threat Calibration (1)
        "evo_threat_calibration": _c("evo_threat_calibration", _D19, "Environmental Threat Calibration Level", temporal_stability=_ST, inference_tractability=_HI),
    },
)


# =============================================================================
# DOMAIN 20: NONCONSCIOUS DECISION ARCHITECTURE (16 constructs) — NEW CRITICAL
# =============================================================================

_D20 = "nonconscious_architecture"

DOMAIN_20_NONCONSCIOUS = Domain(
    domain_id=_D20,
    domain_name="Nonconscious Decision Architecture",
    scoring_side=_US,
    construct_count=16,
    purpose="Structural architecture of nonconscious decision-making.",
    primary_research="Dijksterhuis (2004), Wilson & Schooler (1991), Bargh (2006)",
    adam_relevance="The 95% principle — architecture of nonconscious processing.",
    constructs={
        "nc_goal_susceptibility": _c("nc_goal_susceptibility", _D20, "Nonconscious Goal Activation Susceptibility", temporal_stability=_TR, inference_tractability=_MD),
        "nc_goal_shielding": _c("nc_goal_shielding", _D20, "Active Goal Shielding Strength", temporal_stability=_DI, inference_tractability=_MD),
        "nc_unconscious_thought": _c("nc_unconscious_thought", _D20, "Unconscious Thought Preference", temporal_stability=_TR, inference_tractability=_LO),
        "nc_auto_eval": _c("nc_auto_eval", _D20, "Automatic Evaluation Intensity", temporal_stability=_TR, inference_tractability=_MD),
        "nc_eval_correction": _c("nc_eval_correction", _D20, "Evaluation Correction Tendency", temporal_stability=_DI, inference_tractability=_MD),
        "nc_embodied": _c("nc_embodied", _D20, "Embodied Cognition Sensitivity", temporal_stability=_TR, inference_tractability=_LO),
        "nc_assoc_density": _c("nc_assoc_density", _D20, "Associative Network Density", temporal_stability=_TR, inference_tractability=_LO),
        "nc_context_dependency": _c("nc_context_dependency", _D20, "Context Dependency of Judgment", temporal_stability=_DI, inference_tractability=_HI),
        "nc_habit_speed": _c("nc_habit_speed", _D20, "Habit Formation Speed", temporal_stability=_TR, inference_tractability=_MD),
        "nc_habit_resistance": _c("nc_habit_resistance", _D20, "Habit Disruption Resistance", temporal_stability=_TR, inference_tractability=_HI),
        "nc_implicit_self_reg": _c("nc_implicit_self_reg", _D20, "Implicit Self-Regulation Strength", temporal_stability=_DI, inference_tractability=_MD),
        "nc_psych_ownership": _c("nc_psych_ownership", _D20, "Psychological Ownership Formation Speed", temporal_stability=_TR, inference_tractability=_MD, mechanism_connections=["IKEA_effect", "endowment_effect"]),
        "nc_fluency_truth": _c("nc_fluency_truth", _D20, "Fluency-Truth Conflation", temporal_stability=_TR, inference_tractability=_MD),
        "nc_mimicry": _c("nc_mimicry", _D20, "Behavioral Mimicry Susceptibility", temporal_stability=_TR, inference_tractability=_LO, mechanism_connections=["social_proof", "liking"]),
        "nc_emotional_contagion": _c("nc_emotional_contagion", _D20, "Emotional Contagion Susceptibility", temporal_stability=_TR, inference_tractability=_MD, cross_reference="Also in Domain 28 (ei_contagion)"),
        "nc_tunneling": _c("nc_tunneling", _D20, "Scarcity-Induced Tunneling", temporal_stability=_ST, inference_tractability=_MD),
    },
)


# =============================================================================
# DOMAIN 21: IMPLICIT MOTIVATIONAL DRIVERS (14 constructs) — NEW CRITICAL
# =============================================================================

_D21 = "implicit_motivation"

DOMAIN_21_IMPLICIT_MOTIVATION = Domain(
    domain_id=_D21,
    domain_name="Implicit Motivational Drivers",
    scoring_side=_US,
    construct_count=14,
    purpose="Motivational layer below conscious awareness — what people actually want.",
    primary_research="McClelland et al. (1989), Schultheiss & Brunstein (2010), Berridge & Robinson (2016)",
    constructs={
        "im_power": _c("im_power", _D21, "Implicit Power Motive", temporal_stability=_TR, inference_tractability=_MD),
        "im_achievement": _c("im_achievement", _D21, "Implicit Achievement Motive", temporal_stability=_TR, inference_tractability=_MD),
        "im_affiliation": _c("im_affiliation", _D21, "Implicit Affiliation Motive", temporal_stability=_TR, inference_tractability=_MD),
        "im_wanting": _c("im_wanting", _D21, "Incentive Salience (Wanting)", temporal_stability=_ST, inference_tractability=_MD),
        "im_liking": _c("im_liking", _D21, "Hedonic Liking Intensity", temporal_stability=_ST, inference_tractability=_MD),
        "im_want_like_gap": _c("im_want_like_gap", _D21, "Wanting-Liking Dissociation", temporal_stability=_ST, inference_tractability=_MD,
            derived_from=["im_wanting", "im_liking"],
            ethical_note="Large gaps may indicate problematic consumption. Flag for ethical review."),
        "im_approach": _c("im_approach", _D21, "Implicit Approach Tendency", temporal_stability=_ST, inference_tractability=_HI),
        "im_avoidance": _c("im_avoidance", _D21, "Implicit Avoidance Tendency", temporal_stability=_ST, inference_tractability=_HI),
        "im_reg_fit": _c("im_reg_fit", _D21, "Regulatory Fit Sensitivity", temporal_stability=_DI, inference_tractability=_HI),
        "im_identity_motivation": _c("im_identity_motivation", _D21, "Identity-Based Motivation Strength", temporal_stability=_DI, inference_tractability=_MD, mechanism_connections=["social_proof", "unity"]),
        "im_self_enhance": _c("im_self_enhance", _D21, "Implicit Self-Enhancement Drive", temporal_stability=_DI, inference_tractability=_MD),
        "im_compensatory": _c("im_compensatory", _D21, "Compensatory Consumption Tendency", temporal_stability=_DI, inference_tractability=_MD,
            ethical_note="Score for pattern detection. Never deliberately trigger compensatory consumption."),
    },
)


# =============================================================================
# DOMAIN 22: LAY THEORIES & MINDSETS (8 constructs) — NEW
# =============================================================================

_D22 = "lay_theories"

DOMAIN_22_LAY_THEORIES = Domain(
    domain_id=_D22,
    domain_name="Lay Theories & Mindsets",
    scoring_side=_US,
    construct_count=8,
    purpose="Implicit theories about how the world works.",
    primary_research="Dweck (2006), Levy et al. (1998), Plaks et al. (2005)",
    constructs={
        "lt_entity": _c("lt_entity", _D22, "Entity Theory (Fixed Mindset)", temporal_stability=_TR, inference_tractability=_MD),
        "lt_incremental": _c("lt_incremental", _D22, "Incremental Theory (Growth Mindset)", temporal_stability=_TR, inference_tractability=_MD),
        "lt_price_quality": _c("lt_price_quality", _D22, "Price-Quality Lay Theory", temporal_stability=_DI, inference_tractability=_HI),
        "lt_scarcity_value": _c("lt_scarcity_value", _D22, "Scarcity-Value Lay Theory", temporal_stability=_DI, inference_tractability=_HI, mechanism_connections=["scarcity"]),
        "lt_effort_quality": _c("lt_effort_quality", _D22, "Effort-Quality Lay Theory", temporal_stability=_DI, inference_tractability=_MD),
        "lt_natural": _c("lt_natural", _D22, "Natural-is-Better Lay Theory", temporal_stability=_DI, inference_tractability=_HI),
        "lt_zero_sum": _c("lt_zero_sum", _D22, "Zero-Sum Belief", temporal_stability=_DI, inference_tractability=_MD),
        "lt_just_world": _c("lt_just_world", _D22, "Just World Belief", temporal_stability=_TR, inference_tractability=_MD),
    },
)


# =============================================================================
# PART II: SHARED CONSTRUCTS
# =============================================================================

# DOMAIN 23: EMOTION (19 constructs)
_D23 = "emotion"

DOMAIN_23_EMOTION = Domain(
    domain_id=_D23,
    domain_name="Emotion",
    scoring_side=_BO,
    construct_count=19,
    purpose="Emotional state (user) and emotional tone/appeal (ad/brand).",
    primary_research="Russell & Mehrabian (1977), Plutchik (1980)",
    constructs={
        # PAD Edge-level (3)
        "emo_pleasure": _c("emo_pleasure", _D23, "Pleasure", range_min=-1.0, range_max=1.0, scoring_side=_BO, temporal_stability=_MO, inference_tractability=_HI),
        "emo_arousal": _c("emo_arousal", _D23, "Arousal", scoring_side=_BO, temporal_stability=_MO, inference_tractability=_HI),
        "emo_dominance": _c("emo_dominance", _D23, "Dominance", scoring_side=_BO, temporal_stability=_MO, inference_tractability=_MD),
        # Plutchik Primary (8) — reasoning layer
        "emo_joy": _c("emo_joy", _D23, "Joy", scoring_side=_BO, temporal_stability=_MO, tier=_R),
        "emo_trust": _c("emo_trust", _D23, "Trust", scoring_side=_BO, temporal_stability=_ST, tier=_R),
        "emo_fear": _c("emo_fear", _D23, "Fear", scoring_side=_BO, temporal_stability=_MO, tier=_R),
        "emo_surprise": _c("emo_surprise", _D23, "Surprise", scoring_side=_BO, temporal_stability=_MO, tier=_R),
        "emo_sadness": _c("emo_sadness", _D23, "Sadness", scoring_side=_BO, temporal_stability=_ST, tier=_R),
        "emo_disgust": _c("emo_disgust", _D23, "Disgust", scoring_side=_BO, temporal_stability=_MO, tier=_R),
        "emo_anger": _c("emo_anger", _D23, "Anger", scoring_side=_BO, temporal_stability=_MO, tier=_R),
        "emo_anticipation": _c("emo_anticipation", _D23, "Anticipation", scoring_side=_BO, temporal_stability=_MO, tier=_R),
        # Plutchik Secondary (8) — reasoning layer
        "emo_love": _c("emo_love", _D23, "Love", scoring_side=_BO, tier=_R, derived_from=["emo_joy", "emo_trust"]),
        "emo_submission": _c("emo_submission", _D23, "Submission", scoring_side=_BO, tier=_R, derived_from=["emo_trust", "emo_fear"]),
        "emo_awe": _c("emo_awe", _D23, "Awe", scoring_side=_BO, tier=_R, derived_from=["emo_fear", "emo_surprise"]),
        "emo_disapproval": _c("emo_disapproval", _D23, "Disapproval", scoring_side=_BO, tier=_R, derived_from=["emo_surprise", "emo_sadness"]),
        "emo_remorse": _c("emo_remorse", _D23, "Remorse", scoring_side=_BO, tier=_R, derived_from=["emo_sadness", "emo_disgust"]),
        "emo_contempt": _c("emo_contempt", _D23, "Contempt", scoring_side=_BO, tier=_R, derived_from=["emo_disgust", "emo_anger"]),
        "emo_aggressiveness": _c("emo_aggressiveness", _D23, "Aggressiveness", scoring_side=_BO, tier=_R, derived_from=["emo_anger", "emo_anticipation"]),
        "emo_optimism": _c("emo_optimism", _D23, "Optimism", scoring_side=_BO, tier=_R, derived_from=["emo_anticipation", "emo_joy"]),
    },
)

# DOMAIN 24: MORAL FOUNDATIONS (6 constructs)
_D24 = "moral_foundations"

DOMAIN_24_MORAL = Domain(
    domain_id=_D24, domain_name="Moral Foundations", scoring_side=_BO, construct_count=6,
    primary_research="Haidt & Graham (2007)",
    constructs={
        "mf_care": _c("mf_care", _D24, "Care/Harm", scoring_side=_BO, temporal_stability=_TR, inference_tractability=_MD),
        "mf_fairness": _c("mf_fairness", _D24, "Fairness/Cheating", scoring_side=_BO, temporal_stability=_TR, inference_tractability=_MD),
        "mf_loyalty": _c("mf_loyalty", _D24, "Loyalty/Betrayal", scoring_side=_BO, temporal_stability=_TR, inference_tractability=_MD),
        "mf_authority": _c("mf_authority", _D24, "Authority/Subversion", scoring_side=_BO, temporal_stability=_TR, inference_tractability=_MD),
        "mf_sanctity": _c("mf_sanctity", _D24, "Sanctity/Degradation", scoring_side=_BO, temporal_stability=_TR, inference_tractability=_MD),
        "mf_liberty": _c("mf_liberty", _D24, "Liberty/Oppression", scoring_side=_BO, temporal_stability=_TR, inference_tractability=_MD),
    },
)

# DOMAIN 25: VALUES (19 constructs)
_D25 = "values"

DOMAIN_25_VALUES = Domain(
    domain_id=_D25, domain_name="Values (Schwartz Refined)", scoring_side=_BO, construct_count=19,
    primary_research="Schwartz et al. (2012)",
    constructs={
        "val_sd_thought": _c("val_sd_thought", _D25, "Self-Direction: Thought", scoring_side=_BO, temporal_stability=_TR),
        "val_sd_action": _c("val_sd_action", _D25, "Self-Direction: Action", scoring_side=_BO, temporal_stability=_TR),
        "val_stimulation": _c("val_stimulation", _D25, "Stimulation", scoring_side=_BO, temporal_stability=_TR),
        "val_hedonism": _c("val_hedonism", _D25, "Hedonism", scoring_side=_BO, temporal_stability=_TR),
        "val_achievement": _c("val_achievement", _D25, "Achievement", scoring_side=_BO, temporal_stability=_TR),
        "val_power_dom": _c("val_power_dom", _D25, "Power: Dominance", scoring_side=_BO, temporal_stability=_TR),
        "val_power_res": _c("val_power_res", _D25, "Power: Resources", scoring_side=_BO, temporal_stability=_TR),
        "val_face": _c("val_face", _D25, "Face", scoring_side=_BO, temporal_stability=_TR),
        "val_sec_personal": _c("val_sec_personal", _D25, "Security: Personal", scoring_side=_BO, temporal_stability=_TR),
        "val_sec_societal": _c("val_sec_societal", _D25, "Security: Societal", scoring_side=_BO, temporal_stability=_TR),
        "val_tradition": _c("val_tradition", _D25, "Tradition", scoring_side=_BO, temporal_stability=_TR),
        "val_conform_rules": _c("val_conform_rules", _D25, "Conformity: Rules", scoring_side=_BO, temporal_stability=_TR),
        "val_conform_interp": _c("val_conform_interp", _D25, "Conformity: Interpersonal", scoring_side=_BO, temporal_stability=_TR),
        "val_humility": _c("val_humility", _D25, "Humility", scoring_side=_BO, temporal_stability=_TR),
        "val_benev_care": _c("val_benev_care", _D25, "Benevolence: Caring", scoring_side=_BO, temporal_stability=_TR),
        "val_benev_depend": _c("val_benev_depend", _D25, "Benevolence: Dependability", scoring_side=_BO, temporal_stability=_TR),
        "val_univ_concern": _c("val_univ_concern", _D25, "Universalism: Concern", scoring_side=_BO, temporal_stability=_TR),
        "val_univ_nature": _c("val_univ_nature", _D25, "Universalism: Nature", scoring_side=_BO, temporal_stability=_TR),
        "val_univ_tolerance": _c("val_univ_tolerance", _D25, "Universalism: Tolerance", scoring_side=_BO, temporal_stability=_TR),
    },
)

# DOMAIN 26: TRUST & CREDIBILITY (8 constructs)
_D26 = "trust_credibility"

DOMAIN_26_TRUST = Domain(
    domain_id=_D26, domain_name="Trust & Credibility", scoring_side=_BO, construct_count=8,
    constructs={
        "tr_cognitive": _c("tr_cognitive", _D26, "Cognitive Trust", scoring_side=_BO, temporal_stability=_DI),
        "tr_affective": _c("tr_affective", _D26, "Affective Trust", scoring_side=_BO, temporal_stability=_DI),
        "tr_institutional": _c("tr_institutional", _D26, "Institutional Trust", scoring_side=_BO, temporal_stability=_DI),
        "tr_swift": _c("tr_swift", _D26, "Swift Trust", scoring_side=_BO, temporal_stability=_ST),
        "tr_expertise": _c("tr_expertise", _D26, "Perceived Expertise", scoring_side=_BO, temporal_stability=_ST),
        "tr_trustworthiness": _c("tr_trustworthiness", _D26, "Perceived Trustworthiness", scoring_side=_BO, temporal_stability=_ST),
        "tr_attractiveness": _c("tr_attractiveness", _D26, "Perceived Attractiveness", scoring_side=_BO, temporal_stability=_ST),
        "tr_privacy_concern": _c("tr_privacy_concern", _D26, "Privacy Concern", scoring_side=_BO, temporal_stability=_DI),
    },
)

# DOMAIN 27: BRAND RELATIONSHIP (20 constructs)
_D27 = "brand_relationship"

DOMAIN_27_BRAND_RELATIONSHIP = Domain(
    domain_id=_D27, domain_name="Brand Relationship", scoring_side=_BO, construct_count=20,
    primary_research="Fournier (1998), Batra et al. (2012), Park et al. (2010)",
    constructs={
        "br_love": _c("br_love", _D27, "Love/Passion", scoring_side=_BO, temporal_stability=_DI),
        "br_self_connect": _c("br_self_connect", _D27, "Self-Connection", scoring_side=_BO, temporal_stability=_DI),
        "br_interdependence": _c("br_interdependence", _D27, "Interdependence", scoring_side=_BO, temporal_stability=_DI),
        "br_commitment": _c("br_commitment", _D27, "Commitment", scoring_side=_BO, temporal_stability=_DI),
        "br_intimacy": _c("br_intimacy", _D27, "Intimacy", scoring_side=_BO, temporal_stability=_DI),
        "br_partner_quality": _c("br_partner_quality", _D27, "Partner Quality", scoring_side=_BO, temporal_stability=_DI),
        "br_passion": _c("br_passion", _D27, "Brand Passion", scoring_side=_BO, temporal_stability=_DI),
        "br_self_integration": _c("br_self_integration", _D27, "Brand-Self Integration", scoring_side=_BO, temporal_stability=_DI),
        "br_positive_emo": _c("br_positive_emo", _D27, "Brand Positive Emotion", scoring_side=_BO, temporal_stability=_ST),
        "br_attach_connect": _c("br_attach_connect", _D27, "Brand-Self Connection", scoring_side=_BO, temporal_stability=_DI),
        "br_attach_prominence": _c("br_attach_prominence", _D27, "Brand Prominence", scoring_side=_BO, temporal_stability=_ST),
        "br_engage_cog": _c("br_engage_cog", _D27, "Engagement: Cognitive", scoring_side=_BO, temporal_stability=_ST),
        "br_engage_emo": _c("br_engage_emo", _D27, "Engagement: Emotional", scoring_side=_BO, temporal_stability=_ST),
        "br_engage_beh": _c("br_engage_beh", _D27, "Engagement: Behavioral", scoring_side=_BO, temporal_stability=_ST),
        "br_identification": _c("br_identification", _D27, "Customer-Brand Identification", scoring_side=_BO, temporal_stability=_DI),
        "br_cocreation": _c("br_cocreation", _D27, "Co-Creation Propensity", scoring_side=_BO, temporal_stability=_DI),
        "br_advocacy": _c("br_advocacy", _D27, "Advocacy Propensity", scoring_side=_BO, temporal_stability=_DI),
        "br_wom": _c("br_wom", _D27, "Word-of-Mouth Propensity", scoring_side=_BO, temporal_stability=_DI),
        "br_switching_cost": _c("br_switching_cost", _D27, "Switching Cost Perception", scoring_side=_BO, temporal_stability=_ST),
        "br_investment": _c("br_investment", _D27, "Relationship Investment", scoring_side=_BO, temporal_stability=_DI),
    },
)

# DOMAIN 28: EMOTIONAL INTELLIGENCE & REGULATION (10 constructs)
_D28 = "emotional_intelligence"

DOMAIN_28_EI = Domain(
    domain_id=_D28, domain_name="Emotional Intelligence & Regulation", scoring_side=_BO, construct_count=10,
    primary_research="Salovey & Mayer (1990)",
    constructs={
        "ei_perception": _c("ei_perception", _D28, "Emotion Perception", scoring_side=_BO, temporal_stability=_TR),
        "ei_facilitation": _c("ei_facilitation", _D28, "Emotion Facilitation", scoring_side=_BO, temporal_stability=_TR),
        "ei_understanding": _c("ei_understanding", _D28, "Emotion Understanding", scoring_side=_BO, temporal_stability=_TR),
        "ei_management": _c("ei_management", _D28, "Emotion Management", scoring_side=_BO, temporal_stability=_TR),
        "er_reappraisal": _c("er_reappraisal", _D28, "Cognitive Reappraisal", scoring_side=_BO, temporal_stability=_DI),
        "er_suppression": _c("er_suppression", _D28, "Suppression", scoring_side=_BO, temporal_stability=_DI),
        "er_distraction": _c("er_distraction", _D28, "Distraction", scoring_side=_BO, temporal_stability=_DI),
        "er_rumination": _c("er_rumination", _D28, "Rumination", scoring_side=_BO, temporal_stability=_DI),
        "er_acceptance": _c("er_acceptance", _D28, "Acceptance", scoring_side=_BO, temporal_stability=_DI),
        "ei_contagion": _c("ei_contagion", _D28, "Emotional Contagion Susceptibility", scoring_side=_BO, temporal_stability=_TR,
            cross_reference="Also in Domain 20 (nc_emotional_contagion)"),
    },
)


# =============================================================================
# PART III: AD/BRAND-SIDE CONSTRUCTS
# =============================================================================

# DOMAIN 29: ADVERTISING STYLE & EXECUTION (25 constructs)
_D29 = "ad_style"

DOMAIN_29_AD_STYLE = Domain(
    domain_id=_D29, domain_name="Advertising Style & Execution", scoring_side=_AD, construct_count=25,
    constructs={
        "ad_frame_gain": _c("ad_frame_gain", _D29, "Gain Framing", scoring_side=_AD),
        "ad_frame_loss": _c("ad_frame_loss", _D29, "Loss Framing", scoring_side=_AD),
        "ad_frame_hedonic": _c("ad_frame_hedonic", _D29, "Hedonic Framing", scoring_side=_AD),
        "ad_frame_utilitarian": _c("ad_frame_utilitarian", _D29, "Utilitarian Framing", scoring_side=_AD),
        "ad_appeal_rational": _c("ad_appeal_rational", _D29, "Rational Appeal", scoring_side=_AD),
        "ad_appeal_emotional": _c("ad_appeal_emotional", _D29, "Emotional Appeal", scoring_side=_AD),
        "ad_appeal_fear": _c("ad_appeal_fear", _D29, "Fear Appeal", scoring_side=_AD),
        "ad_appeal_humor": _c("ad_appeal_humor", _D29, "Humor Appeal", scoring_side=_AD),
        "ad_appeal_sex": _c("ad_appeal_sex", _D29, "Sex Appeal", scoring_side=_AD),
        "ad_appeal_comparative": _c("ad_appeal_comparative", _D29, "Comparative Appeal", scoring_side=_AD),
        "ad_appeal_metaphor": _c("ad_appeal_metaphor", _D29, "Metaphor Appeal", scoring_side=_AD),
        "ad_appeal_narrative": _c("ad_appeal_narrative", _D29, "Narrative Appeal", scoring_side=_AD),
        "ad_proc_central": _c("ad_proc_central", _D29, "Central Processing Target", scoring_side=_AD),
        "ad_proc_peripheral": _c("ad_proc_peripheral", _D29, "Peripheral Processing Target", scoring_side=_AD),
        "ad_construal_abstract": _c("ad_construal_abstract", _D29, "Abstract Construal Target", scoring_side=_AD),
        "ad_construal_concrete": _c("ad_construal_concrete", _D29, "Concrete Construal Target", scoring_side=_AD),
        "ad_complexity": _c("ad_complexity", _D29, "Ad Complexity", scoring_side=_AD),
        "ad_info_density": _c("ad_info_density", _D29, "Information Density", scoring_side=_AD),
        "ad_emo_intensity": _c("ad_emo_intensity", _D29, "Emotional Intensity", scoring_side=_AD),
        "ad_cta_strength": _c("ad_cta_strength", _D29, "CTA Strength", scoring_side=_AD),
        "ad_visual_dom": _c("ad_visual_dom", _D29, "Visual Dominance", scoring_side=_AD),
        "ad_text_dom": _c("ad_text_dom", _D29, "Text Dominance", scoring_side=_AD),
        "ad_repetition": _c("ad_repetition", _D29, "Repetition Strategy", scoring_side=_AD),
        "ad_novelty": _c("ad_novelty", _D29, "Novelty Level", scoring_side=_AD),
        "ad_personalization": _c("ad_personalization", _D29, "Personalization Level", scoring_side=_AD),
    },
)

# DOMAIN 30: PERSUASION TECHNIQUES (28 constructs)
_D30 = "persuasion_techniques"

DOMAIN_30_PERSUASION_TECHNIQUES = Domain(
    domain_id=_D30, domain_name="Persuasion Techniques", scoring_side=_AD, construct_count=28,
    constructs={
        "pt_social_proof": _c("pt_social_proof", _D30, "Social Proof Technique", scoring_side=_AD),
        "pt_scarcity": _c("pt_scarcity", _D30, "Scarcity Technique", scoring_side=_AD),
        "pt_authority": _c("pt_authority", _D30, "Authority Technique", scoring_side=_AD),
        "pt_reciprocity": _c("pt_reciprocity", _D30, "Reciprocity Technique", scoring_side=_AD),
        "pt_commitment": _c("pt_commitment", _D30, "Commitment Technique", scoring_side=_AD),
        "pt_liking": _c("pt_liking", _D30, "Liking Technique", scoring_side=_AD),
        "pt_unity": _c("pt_unity", _D30, "Unity Technique", scoring_side=_AD),
        "pt_anchoring": _c("pt_anchoring", _D30, "Anchoring Technique", scoring_side=_AD),
        "pt_framing": _c("pt_framing", _D30, "Framing Technique", scoring_side=_AD),
        "pt_contrast": _c("pt_contrast", _D30, "Contrast Technique", scoring_side=_AD),
        "pt_storytelling": _c("pt_storytelling", _D30, "Storytelling Technique", scoring_side=_AD),
        "pt_fear_appeal": _c("pt_fear_appeal", _D30, "Fear Appeal Technique", scoring_side=_AD),
        "pt_humor": _c("pt_humor", _D30, "Humor Technique", scoring_side=_AD),
        "pt_aspirational": _c("pt_aspirational", _D30, "Aspirational Technique", scoring_side=_AD),
        "pt_nostalgia": _c("pt_nostalgia", _D30, "Nostalgia Technique", scoring_side=_AD),
        "pt_curiosity_gap": _c("pt_curiosity_gap", _D30, "Curiosity Gap Technique", scoring_side=_AD),
        "pt_loss_aversion": _c("pt_loss_aversion", _D30, "Loss Aversion Technique", scoring_side=_AD),
        "pt_endowment": _c("pt_endowment", _D30, "Endowment Technique", scoring_side=_AD),
        "pt_default": _c("pt_default", _D30, "Default Technique", scoring_side=_AD),
        "pt_decoy": _c("pt_decoy", _D30, "Decoy Technique", scoring_side=_AD),
        "pt_mere_exposure": _c("pt_mere_exposure", _D30, "Mere Exposure Technique", scoring_side=_AD),
        "pt_fluency": _c("pt_fluency", _D30, "Cognitive Fluency Technique", scoring_side=_AD),
        "pt_self_ref": _c("pt_self_ref", _D30, "Self-Referencing Technique", scoring_side=_AD),
        "pt_temporal_reframe": _c("pt_temporal_reframe", _D30, "Temporal Reframing Technique", scoring_side=_AD),
        "pt_social_identity": _c("pt_social_identity", _D30, "Social Identity Technique", scoring_side=_AD),
        "pt_transformation": _c("pt_transformation", _D30, "Transformation Technique", scoring_side=_AD),
        "pt_reg_fit": _c("pt_reg_fit", _D30, "Regulatory Fit Technique", scoring_side=_AD),
        "pt_goal_priming": _c("pt_goal_priming", _D30, "Goal Priming Technique", scoring_side=_AD),
    },
)

# DOMAIN 31: VALUE PROPOSITIONS (13 constructs)
_D31 = "value_propositions"

DOMAIN_31_VALUE_PROPS = Domain(
    domain_id=_D31, domain_name="Value Propositions", scoring_side=_AD, construct_count=13,
    constructs={
        "vp_performance": _c("vp_performance", _D31, "Performance Superiority", scoring_side=_AD),
        "vp_convenience": _c("vp_convenience", _D31, "Convenience/Ease", scoring_side=_AD),
        "vp_reliability": _c("vp_reliability", _D31, "Reliability/Durability", scoring_side=_AD),
        "vp_cost": _c("vp_cost", _D31, "Cost Efficiency", scoring_side=_AD),
        "vp_pleasure": _c("vp_pleasure", _D31, "Pleasure/Enjoyment", scoring_side=_AD),
        "vp_peace": _c("vp_peace", _D31, "Peace of Mind", scoring_side=_AD),
        "vp_self_express": _c("vp_self_express", _D31, "Self-Expression", scoring_side=_AD),
        "vp_transformation": _c("vp_transformation", _D31, "Transformation", scoring_side=_AD),
        "vp_status": _c("vp_status", _D31, "Status/Prestige", scoring_side=_AD),
        "vp_belonging": _c("vp_belonging", _D31, "Belonging/Connection", scoring_side=_AD),
        "vp_social_resp": _c("vp_social_resp", _D31, "Social Responsibility", scoring_side=_AD),
        "vp_novelty": _c("vp_novelty", _D31, "Novelty/Innovation", scoring_side=_AD),
        "vp_knowledge": _c("vp_knowledge", _D31, "Knowledge/Expertise", scoring_side=_AD),
    },
)

# DOMAIN 32: BRAND PERSONALITY (7 constructs)
_D32 = "brand_personality"

DOMAIN_32_BRAND_PERSONALITY = Domain(
    domain_id=_D32, domain_name="Brand Personality", scoring_side=_AD, construct_count=7,
    primary_research="Aaker (1997)",
    constructs={
        "bp_sincerity": _c("bp_sincerity", _D32, "Brand Sincerity", scoring_side=_AD),
        "bp_excitement": _c("bp_excitement", _D32, "Brand Excitement", scoring_side=_AD),
        "bp_competence": _c("bp_competence", _D32, "Brand Competence", scoring_side=_AD),
        "bp_sophistication": _c("bp_sophistication", _D32, "Brand Sophistication", scoring_side=_AD),
        "bp_ruggedness": _c("bp_ruggedness", _D32, "Brand Ruggedness", scoring_side=_AD),
        "bp_authenticity": _c("bp_authenticity", _D32, "Brand Authenticity", scoring_side=_AD),
        "bp_warmth": _c("bp_warmth", _D32, "Brand Warmth", scoring_side=_AD),
    },
)

# DOMAIN 33: LINGUISTIC STYLE (7 + 4 meta = 11 constructs)
_D33 = "linguistic_style"

DOMAIN_33_LINGUISTIC = Domain(
    domain_id=_D33, domain_name="Linguistic Style", scoring_side=_AD, construct_count=11,
    constructs={
        "ls_conversational": _c("ls_conversational", _D33, "Conversational Style", scoring_side=_AD),
        "ls_professional": _c("ls_professional", _D33, "Professional Style", scoring_side=_AD),
        "ls_technical": _c("ls_technical", _D33, "Technical Style", scoring_side=_AD),
        "ls_emotional": _c("ls_emotional", _D33, "Emotional Style", scoring_side=_AD),
        "ls_urgent": _c("ls_urgent", _D33, "Urgent Style", scoring_side=_AD),
        "ls_storytelling": _c("ls_storytelling", _D33, "Storytelling Style", scoring_side=_AD),
        "ls_minimalist": _c("ls_minimalist", _D33, "Minimalist Style", scoring_side=_AD),
        "ls_formality": _c("ls_formality", _D33, "Formality Level", scoring_side=_AD),
        "ls_complexity": _c("ls_complexity", _D33, "Complexity Level", scoring_side=_AD),
        "ls_emo_tone": _c("ls_emo_tone", _D33, "Emotional Tone", range_min=-1.0, range_max=1.0, scoring_side=_AD),
        "ls_directness": _c("ls_directness", _D33, "Directness", scoring_side=_AD),
    },
)


# =============================================================================
# DOMAIN 34: PEER PERSUASION CONSTRUCTS (18 constructs) — FROM ADDENDUM
# =============================================================================

_D34 = "peer_persuasion"

DOMAIN_34_PEER_PERSUASION = Domain(
    domain_id=_D34,
    domain_name="Peer Persuasion Constructs",
    scoring_side=_AD,
    construct_count=18,
    applies_to="reviews_as_ads_only",
    purpose="Review-as-advertisement persuasion — different pathways than brand content.",
    constructs={
        "peer_authenticity": _c("peer_authenticity", _D34, "Perceived Testimonial Authenticity", scoring_side=_AD),
        "peer_vulnerability": _c("peer_vulnerability", _D34, "Relatable Vulnerability", scoring_side=_AD),
        "peer_outcome_specificity": _c("peer_outcome_specificity", _D34, "Outcome Specificity", scoring_side=_AD),
        "peer_outcome_timeline": _c("peer_outcome_timeline", _D34, "Outcome Timeline Credibility", scoring_side=_AD),
        "peer_before_after": _c("peer_before_after", _D34, "Before/After Narrative Strength", scoring_side=_AD),
        "peer_risk_financial": _c("peer_risk_financial", _D34, "Financial Risk Resolution", scoring_side=_AD),
        "peer_risk_performance": _c("peer_risk_performance", _D34, "Performance Risk Resolution", scoring_side=_AD),
        "peer_risk_social": _c("peer_risk_social", _D34, "Social Risk Resolution", scoring_side=_AD),
        "peer_risk_durability": _c("peer_risk_durability", _D34, "Durability Risk Resolution", scoring_side=_AD),
        "peer_use_case": _c("peer_use_case", _D34, "Use Case Specificity & Matching", scoring_side=_AD),
        "peer_sp_amplification": _c("peer_sp_amplification", _D34, "Social Proof Amplification", scoring_side=_AD),
        "peer_objection_preempt": _c("peer_objection_preempt", _D34, "Objection Preemption", scoring_side=_AD),
        "peer_expertise": _c("peer_expertise", _D34, "Domain Expertise Signals", scoring_side=_AD),
        "peer_comparative": _c("peer_comparative", _D34, "Comparative Assessment Depth", scoring_side=_AD),
        "peer_emo_contagion": _c("peer_emo_contagion", _D34, "Emotional Contagion Potency", scoring_side=_AD),
        "peer_narrative_arc": _c("peer_narrative_arc", _D34, "Narrative Arc Completeness", scoring_side=_AD),
        "peer_resolved_anxiety": _c("peer_resolved_anxiety", _D34, "Resolved Anxiety Narrative", scoring_side=_AD),
        "peer_recommendation": _c("peer_recommendation", _D34, "Implicit/Explicit Recommendation Strength", scoring_side=_AD),
    },
)


# =============================================================================
# DOMAIN 35: PERSUASION ECOSYSTEM CONSTRUCTS (14 constructs) — FROM ADDENDUM
# =============================================================================

_D35 = "persuasion_ecosystem"

DOMAIN_35_ECOSYSTEM = Domain(
    domain_id=_D35,
    domain_name="Persuasion Ecosystem Constructs",
    scoring_side=_EC,
    construct_count=14,
    applies_to="product_level_aggregate",
    purpose="Emergent properties of the composite persuasion field per product.",
    constructs={
        "eco_frame_coherence": _c("eco_frame_coherence", _D35, "Psychological Frame Coherence", scoring_side=_EC),
        "eco_claim_validation": _c("eco_claim_validation", _D35, "Claim-Review Validation Ratio", scoring_side=_EC),
        "eco_frame_extension": _c("eco_frame_extension", _D35, "Frame Extension Score", scoring_side=_EC),
        "eco_risk_coverage": _c("eco_risk_coverage", _D35, "Perceived Risk Coverage Completeness", scoring_side=_EC,
            sub_scores={
                "financial_covered": {"range": [0.0, 1.0]}, "performance_covered": {"range": [0.0, 1.0]},
                "social_covered": {"range": [0.0, 1.0]}, "psychological_covered": {"range": [0.0, 1.0]},
                "physical_covered": {"range": [0.0, 1.0]}, "time_covered": {"range": [0.0, 1.0]},
            }),
        "eco_objection_coverage": _c("eco_objection_coverage", _D35, "Common Objection Coverage", scoring_side=_EC),
        "eco_sp_density": _c("eco_sp_density", _D35, "Social Proof Density", scoring_side=_EC),
        "eco_sp_diversity": _c("eco_sp_diversity", _D35, "Social Proof Psychological Diversity", scoring_side=_EC),
        "eco_authority_layers": _c("eco_authority_layers", _D35, "Authority Source Layering", scoring_side=_EC),
        "eco_evo_coverage": _c("eco_evo_coverage", _D35, "Evolutionary Motive Activation Coverage", scoring_side=_EC,
            sub_scores={
                "self_protection_activated": {"range": [0.0, 1.0]}, "affiliation_activated": {"range": [0.0, 1.0]},
                "status_activated": {"range": [0.0, 1.0]}, "mate_acquisition_activated": {"range": [0.0, 1.0]},
                "kin_care_activated": {"range": [0.0, 1.0]}, "disease_avoidance_activated": {"range": [0.0, 1.0]},
            }),
        "eco_cialdini_coverage": _c("eco_cialdini_coverage", _D35, "Influence Principle Coverage", scoring_side=_EC,
            sub_scores={
                "reciprocity_present": {"range": [0.0, 1.0]}, "commitment_present": {"range": [0.0, 1.0]},
                "social_proof_present": {"range": [0.0, 1.0]}, "authority_present": {"range": [0.0, 1.0]},
                "liking_present": {"range": [0.0, 1.0]}, "scarcity_present": {"range": [0.0, 1.0]},
                "unity_present": {"range": [0.0, 1.0]},
            }),
        "eco_persuasion_gaps": _c("eco_persuasion_gaps", _D35, "Persuasion Gap Analysis", scoring_side=_EC),
        "eco_temporal_arc": _c("eco_temporal_arc", _D35, "Temporal Persuasion Arc Quality", scoring_side=_EC),
        "eco_negative_resolution": _c("eco_negative_resolution", _D35, "Negative Review Resolution Quality", scoring_side=_EC),
    },
)


# =============================================================================
# MASTER REGISTRY: All 35 domains in one dict
# =============================================================================

ALL_DOMAINS: dict[str, Domain] = {
    "personality": DOMAIN_1_PERSONALITY,
    "motivation": DOMAIN_2_MOTIVATION,
    "cognitive_biases": DOMAIN_3_BIASES,
    "prospect_theory": DOMAIN_4_PROSPECT_THEORY,
    "approach_avoidance": DOMAIN_5_APPROACH_AVOIDANCE,
    "social_influence": DOMAIN_6_SOCIAL_INFLUENCE,
    "persuasion_processing": DOMAIN_7_PERSUASION,
    "decision_making": DOMAIN_8_DECISION_MAKING,
    "strategic_fairness": DOMAIN_9_STRATEGIC,
    "cultural": DOMAIN_10_CULTURAL,
    "risk_uncertainty": DOMAIN_11_RISK,
    "self_identity": DOMAIN_12_SELF_IDENTITY,
    "information_processing": DOMAIN_13_INFORMATION_PROCESSING,
    "consumer_traits": DOMAIN_14_CONSUMER,
    "implicit_processing": DOMAIN_15_IMPLICIT,
    "temporal": DOMAIN_16_TEMPORAL,
    "attachment": DOMAIN_17_ATTACHMENT,
    "regulatory_mode": DOMAIN_18_REGULATORY_MODE,
    "evolutionary": DOMAIN_19_EVOLUTIONARY,
    "nonconscious_architecture": DOMAIN_20_NONCONSCIOUS,
    "implicit_motivation": DOMAIN_21_IMPLICIT_MOTIVATION,
    "lay_theories": DOMAIN_22_LAY_THEORIES,
    "emotion": DOMAIN_23_EMOTION,
    "moral_foundations": DOMAIN_24_MORAL,
    "values": DOMAIN_25_VALUES,
    "trust_credibility": DOMAIN_26_TRUST,
    "brand_relationship": DOMAIN_27_BRAND_RELATIONSHIP,
    "emotional_intelligence": DOMAIN_28_EI,
    "ad_style": DOMAIN_29_AD_STYLE,
    "persuasion_techniques": DOMAIN_30_PERSUASION_TECHNIQUES,
    "value_propositions": DOMAIN_31_VALUE_PROPS,
    "brand_personality": DOMAIN_32_BRAND_PERSONALITY,
    "linguistic_style": DOMAIN_33_LINGUISTIC,
    "peer_persuasion": DOMAIN_34_PEER_PERSUASION,
    "persuasion_ecosystem": DOMAIN_35_ECOSYSTEM,
}


# =============================================================================
# CONVENIENCE ACCESSORS
# =============================================================================

def get_all_constructs() -> dict[str, Construct]:
    """Return a flat dict of construct_id -> Construct across all domains."""
    all_constructs: dict[str, Construct] = {}
    for domain in ALL_DOMAINS.values():
        all_constructs.update(domain.constructs)
    return all_constructs


def get_edge_constructs() -> dict[str, Construct]:
    """Return only constructs in the edge tier (real-time, <10ms)."""
    return {cid: c for cid, c in get_all_constructs().items() if c.tier == InferenceTier.EDGE}


def get_reasoning_constructs() -> dict[str, Construct]:
    """Return only constructs in the reasoning tier (Claude atoms, <2000ms)."""
    return {cid: c for cid, c in get_all_constructs().items() if c.tier == InferenceTier.REASONING_LAYER}


def get_constructs_by_side(side: ScoringSwitch) -> dict[str, Construct]:
    """Return constructs scored on a specific side."""
    return {cid: c for cid, c in get_all_constructs().items() if c.scoring_side == side}


def get_constructs_by_stability(stability: TemporalStability) -> dict[str, Construct]:
    """Return constructs of a specific temporal stability tier."""
    return {cid: c for cid, c in get_all_constructs().items() if c.temporal_stability == stability}


def get_constructs_with_ethical_notes() -> dict[str, Construct]:
    """Return all constructs that have ethical usage constraints."""
    return {cid: c for cid, c in get_all_constructs().items() if c.ethical_note}


def validate_construct_id_uniqueness() -> list[str]:
    """Validate that all construct IDs are unique across all domains. Returns duplicate IDs."""
    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for domain in ALL_DOMAINS.values():
        for cid in domain.constructs:
            if cid in seen:
                duplicates.append(f"{cid} (in {seen[cid]} and {domain.domain_id})")
            else:
                seen[cid] = domain.domain_id
    return duplicates


def get_taxonomy_summary() -> dict:
    """Return summary statistics matching the taxonomy document."""
    all_c = get_all_constructs()
    return {
        "total_domains": len(ALL_DOMAINS),
        "total_constructs": len(all_c),
        "customer_side": len(get_constructs_by_side(ScoringSwitch.USER_SIDE)),
        "shared": len(get_constructs_by_side(ScoringSwitch.BOTH)),
        "ad_side": len(get_constructs_by_side(ScoringSwitch.AD_SIDE)),
        "ecosystem": len(get_constructs_by_side(ScoringSwitch.ECOSYSTEM)),
        "edge_tier": len(get_edge_constructs()),
        "reasoning_tier": len(get_reasoning_constructs()),
        "by_stability": {
            s.value: len(get_constructs_by_stability(s))
            for s in TemporalStability
        },
        "with_ethical_notes": len(get_constructs_with_ethical_notes()),
        "duplicates": validate_construct_id_uniqueness(),
    }
