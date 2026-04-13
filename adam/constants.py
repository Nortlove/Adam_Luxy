# adam/constants.py — CANONICAL SOURCE for all cross-module constants
# Every StackAdapt integration module imports from here. Never redeclare.

import re

# ---------------------------------------------------------------------------
# Phase 1 categories — only these have full BRAND_CONVERTED edge coverage
# ---------------------------------------------------------------------------
FULLY_EDGED_CATEGORIES = ["Beauty", "Personal Care", "Beauty & Personal Care"]

CATEGORY_PATH_FILTER = (
    "pd.category_path STARTS WITH 'Beauty' "
    "OR pd.category_path CONTAINS 'Personal Care'"
)

# ---------------------------------------------------------------------------
# Archetypes — 6 external (StackAdapt-facing), 8 internal (full system)
# ---------------------------------------------------------------------------
EXTERNAL_ARCHETYPES = [
    "achiever", "guardian", "explorer", "connector", "analyst", "creator",
]

INTERNAL_ARCHETYPES = EXTERNAL_ARCHETYPES + ["nurturer", "pragmatist"]

# Map internal archetypes that don't have StackAdapt segments to their
# closest external archetype (based on Big Five centroid distance)
ARCHETYPE_ALIASES = {
    "nurturer": "connector",
    "pragmatist": "analyst",
    # Legacy aliases from various subsystems
    "the_achiever": "achiever",
    "the_guardian": "guardian",
    "the_explorer": "explorer",
    "the_connector": "connector",
    "the_analyst": "analyst",
    "the_creator": "creator",
    "Achiever": "achiever",
    "Guardian": "guardian",
    "Explorer": "explorer",
    "Connector": "connector",
    "Analyst": "analyst",
    "Creator": "creator",
    # LUXY Ride campaign-specific personas → graph archetypes
    "corporate_executive": "careful_truster",
    "airport_anxiety": "careful_truster",
    "special_occasion": "status_seeker",
    "first_timer": "easy_decider",
    "repeat_loyal": "easy_decider",
    # Interaction-effect archetypes (validated: 11,805 polar + 3,586 moderate)
    "explorer": "explorer",
    "prevention_planner": "prevention_planner",
    "reliable_cooperator": "reliable_cooperator",
    "anxious_economist": "anxious_economist",
    "vocal_resistor": "vocal_resistor",
    "loyalist": "trusting_loyalist",
    "trusting_loyalist": "trusting_loyalist",
    "confident_promoter": "trusting_loyalist",  # brand_trust × promotion_focus (9.1x in moderate)
    # Subtle archetypes from moderate segment (rating 4-6, N=3,586)
    "dependable_loyalist": "dependable_loyalist",  # brand_trust × conscientiousness (6.6x in moderate)
    "consensus_seeker": "consensus_seeker",         # agreeableness × social_proof (3.3x in moderate)
    "defensive_skeptic": "defensive_skeptic",       # neuroticism × reactance (0.01x — HARDEST suppress)
    "careful_analyst": "prevention_planner",         # NFC × prevention (0.46x — maps to prevention_planner)
    "methodical_evaluator": "dependable_loyalist",   # alias
}

# Campaign ID prefix → archetype mapping
# Used by signal_collector, conversion endpoint, ops intelligence
CAMPAIGN_ARCHETYPE_MAP = {
    "CT": "careful_truster",
    "SS": "status_seeker",
    "ED": "easy_decider",
    "EX": "explorer",
    "PP": "prevention_planner",
    "RC": "reliable_cooperator",
    "TL": "trusting_loyalist",
    "DL": "dependable_loyalist",
    "CS": "consensus_seeker",
}

# All active archetypes for iteration (cross-category validated)
ALL_ARCHETYPES = [
    "careful_truster", "status_seeker", "easy_decider",
    "explorer", "prevention_planner", "reliable_cooperator",
    "trusting_loyalist", "dependable_loyalist", "consensus_seeker",
]

# Archetypes to auto-suppress (validated from moderate segment, N=3,586)
SUPPRESS_ARCHETYPES = [
    "anxious_economist",    # neuroticism × spending_pain, 0.23x lift
    "vocal_resistor",       # expressiveness × reactance, 0.36x lift
    "defensive_skeptic",    # neuroticism × reactance, 0.01x lift (worst)
]


def resolve_archetype(raw: str) -> str:
    """Resolve any archetype string to one of the 6 external archetypes."""
    lower = raw.lower().strip()
    return ARCHETYPE_ALIASES.get(lower, lower)


# ---------------------------------------------------------------------------
# Mechanisms — Cialdini-based external vocabulary with atom-layer mapping
# ---------------------------------------------------------------------------
# External: what StackAdapt segments and creative intelligence use
MECHANISMS = [
    "social_proof", "authority", "scarcity", "reciprocity", "commitment",
    "liking", "unity", "cognitive_ease", "curiosity", "loss_aversion",
]

# Mapping: external mechanism → atom DAG mechanism(s)
# The atom DAG uses psychological process names; the external API uses
# Cialdini influence principle names. This bridge lets the StackAdapt
# endpoint leverage the full atom reasoning when needed.
MECHANISM_TO_ATOM = {
    "social_proof":   "social_proof",
    "authority":      "identity_construction",   # authority appeals to identity/expertise
    "scarcity":       "scarcity",
    "reciprocity":    "regulatory_focus",         # reciprocity activates regulatory fit
    "commitment":     "regulatory_focus",         # commitment is prevention-focused
    "liking":         "mimetic_desire",           # liking drives mimetic wanting
    "unity":          "identity_construction",    # unity is identity-based belonging
    "cognitive_ease": "attention_dynamics",        # fluency manages attention
    "curiosity":      "attention_dynamics",        # curiosity drives attentional capture
    "loss_aversion":  "temporal_construal",        # loss framing ties to temporal urgency
}

# Reverse mapping: atom mechanism → best external Cialdini principle
ATOM_TO_MECHANISM = {
    "social_proof":         "social_proof",
    "identity_construction": "authority",
    "scarcity":             "scarcity",
    "regulatory_focus":     "reciprocity",
    "mimetic_desire":       "liking",
    "attention_dynamics":   "curiosity",
    "temporal_construal":   "loss_aversion",
    "anchoring":            "cognitive_ease",
    "embodied_cognition":   "social_proof",  # sensory experience → social validation
}

# ---------------------------------------------------------------------------
# ProductDescription ad-side persuasion technique property names
# These are the actual Neo4j property names on ProductDescription nodes
# that encode what Cialdini techniques the product page uses.
# ---------------------------------------------------------------------------
AD_PERSUASION_PROPERTIES = {
    "social_proof":  "ad_persuasion_techniques_social_proof",
    "scarcity":      "ad_persuasion_techniques_scarcity",
    "authority":     "ad_persuasion_techniques_authority",
    "reciprocity":   "ad_persuasion_techniques_reciprocity",
    "commitment":    "ad_persuasion_techniques_commitment",
    "liking":        "ad_persuasion_techniques_liking",
    "anchoring":     "ad_persuasion_techniques_anchoring",
    "storytelling":  "ad_persuasion_techniques_storytelling",
}

# ---------------------------------------------------------------------------
# BRAND_CONVERTED edge dimension names (actual Neo4j property names)
# These are the bilateral alignment dimensions on the conversion edge.
# ---------------------------------------------------------------------------
EDGE_DIMENSIONS = {
    "regulatory_fit":       "regulatory_fit_score",
    "construal_fit":        "construal_fit_score",
    "personality_alignment": "personality_brand_alignment",
    "emotional_resonance":  "emotional_resonance",
    "value_alignment":      "value_alignment",
    "evolutionary_motive":  "evolutionary_motive_match",
    "composite_alignment":  "composite_alignment",
    "persuasion_confidence": "persuasion_confidence_multiplier",
}

# ---------------------------------------------------------------------------
# Segment ID format
# ---------------------------------------------------------------------------
SEGMENT_ID_REGEX = re.compile(
    r"^informativ_"
    r"(achiever|guardian|explorer|connector|analyst|creator"
    r"|corporate_executive|airport_anxiety|special_occasion|first_timer|repeat_loyal"
    r"|status_seeker|easy_decider|careful_truster|skeptical_analyst|disillusioned"
    r"|trusting_loyalist|reliable_cooperator|prevention_planner"
    r"|dependable_loyalist|consensus_seeker"
    r"|luxury_transportation)"
    r"(_social_proof|_authority|_scarcity|_reciprocity|_commitment|_liking"
    r"|_unity|_cognitive_ease|_curiosity|_loss_aversion|_aspiration|_urgency)?"
    r"(_beauty|_personal_care|_luxury_transportation|_luxury"
    r"|_corporate_executive|_airport_anxiety|_special_occasion|_first_timer|_repeat_loyal"
    r"|_status_seeker|_easy_decider|_careful_truster|_skeptical_analyst|_disillusioned"
    r"|_trusting_loyalist|_reliable_cooperator|_prevention_planner"
    r"|_dependable_loyalist|_consensus_seeker)?"
    r"_(t1|t2|t3)$"
)

# ---------------------------------------------------------------------------
# CPM configuration
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Conversion Barrier Categories (Enhancement #33 — Therapeutic Retargeting)
# Each maps to one or more bilateral alignment dimensions that fell below
# the conversion threshold for a specific archetype.
# ---------------------------------------------------------------------------
BARRIER_CATEGORIES = [
    "trust_deficit",            # brand_trust_fit below threshold
    "regulatory_mismatch",      # regulatory_fit_score below threshold
    "processing_overload",      # processing_route_match below threshold
    "emotional_disconnect",     # emotional_resonance below threshold
    "price_friction",           # anchor_susceptibility + spending_pain below threshold
    "motive_mismatch",          # evolutionary_motive_match below threshold
    "negativity_block",         # negativity_bias_match above threshold (inverted)
    "reactance_triggered",      # persuasion_reactance_match above threshold
    "identity_misalignment",    # personality_brand_alignment below threshold
    "intention_action_gap",     # all alignment adequate but no conversion
]

# Therapeutic Mechanisms — research-backed interventions for barrier resolution
# Each maps to one of the 16 research domains in Enhancement #33.
THERAPEUTIC_MECHANISMS = [
    "evidence_proof",              # Domain 3: Scaffolding
    "narrative_transportation",     # Domain 5: Green & Brock
    "social_proof_matched",         # Domain 12: Bandura modeling
    "autonomy_restoration",         # Domain 8: SDT
    "construal_shift",              # Domain 9: CLT
    "ownership_reactivation",       # Domain 10: Endowment
    "implementation_intention",     # Domain 14: Gollwitzer
    "micro_commitment",             # Domain 6: FITD
    "dissonance_activation",        # Domain 11: Festinger
    "loss_framing",                 # Domain 10: Loss aversion
    "anxiety_resolution",           # Domain 2: Rupture repair
    "frustration_control",          # Domain 3: Scaffolding
    "novelty_disruption",           # Domain 13: Dual process
    "vivid_scenario",               # Domain 5: Transportation
    "price_anchor",                 # Domain 9: CLT concrete
    "claude_argument",              # Domain 16: LLM factual argument generation
]

# Map bilateral alignment dimensions → barrier category
# Used by the barrier diagnostic engine to classify gaps.
DIMENSION_BARRIER_MAP = {
    "brand_trust_fit":             "trust_deficit",
    "regulatory_fit_score":        "regulatory_mismatch",
    "processing_route_match":      "processing_overload",
    "emotional_resonance":         "emotional_disconnect",
    "anchor_susceptibility_match": "price_friction",
    "spending_pain_match":         "price_friction",
    "evolutionary_motive_match":   "motive_mismatch",
    "negativity_bias_match":       "negativity_block",
    "persuasion_reactance_match":  "reactance_triggered",
    "personality_brand_alignment": "identity_misalignment",
    "optimal_distinctiveness_fit": "identity_misalignment",
    "composite_alignment":         "intention_action_gap",
}

# Which therapeutic mechanisms can address which barriers
# Ordered by expected effectiveness (first = highest priority).
BARRIER_MECHANISM_CANDIDATES = {
    "trust_deficit":         ["claude_argument", "evidence_proof", "social_proof_matched", "narrative_transportation"],
    "regulatory_mismatch":   ["claude_argument", "construal_shift", "narrative_transportation", "vivid_scenario"],
    "processing_overload":   ["frustration_control", "micro_commitment"],
    "emotional_disconnect":  ["claude_argument", "narrative_transportation", "vivid_scenario", "social_proof_matched"],
    "price_friction":        ["claude_argument", "price_anchor", "loss_framing", "ownership_reactivation"],
    "motive_mismatch":       ["claude_argument", "construal_shift", "vivid_scenario"],
    "negativity_block":      ["claude_argument", "anxiety_resolution", "social_proof_matched", "evidence_proof"],
    "reactance_triggered":   ["autonomy_restoration", "narrative_transportation"],
    "identity_misalignment": ["claude_argument", "narrative_transportation", "social_proof_matched"],
    "intention_action_gap":  ["implementation_intention", "ownership_reactivation", "loss_framing", "micro_commitment"],
}

# Map therapeutic mechanisms → closest Cialdini principle (for interop with
# existing MECHANISMS vocabulary used by StackAdapt and atom DAG).
THERAPEUTIC_TO_CIALDINI = {
    "evidence_proof":          "authority",
    "narrative_transportation": "liking",
    "social_proof_matched":    "social_proof",
    "autonomy_restoration":    "reciprocity",
    "construal_shift":         "cognitive_ease",
    "ownership_reactivation":  "commitment",
    "implementation_intention": "commitment",
    "micro_commitment":        "commitment",
    "dissonance_activation":   "commitment",
    "loss_framing":            "loss_aversion",
    "anxiety_resolution":      "authority",
    "frustration_control":     "cognitive_ease",
    "novelty_disruption":      "curiosity",
    "vivid_scenario":          "liking",
    "price_anchor":            "scarcity",
    "claude_argument":         "authority",
}

# ---------------------------------------------------------------------------
# CPM configuration
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Frustrated Dimension Pairs (Enhancement #34, Session 34-2 diagnostic)
# Computed from covariance analysis of 754 converted LUXY Ride bilateral edges.
# Negatively correlated among converters: satisfying one makes the other worse.
# Retargeting MUST address these SEQUENTIALLY, never simultaneously.
# ---------------------------------------------------------------------------
FRUSTRATED_DIMENSION_PAIRS = [
    # (dim_a, dim_b, correlation_among_converters)
    # Empirically derived from 754 converted LUXY Ride edges (Session 34-2).
    # All pairs with r < -0.3. Frustration score × conversion: r=-0.582.
    # Retargeting MUST address frustrated pairs SEQUENTIALLY, never simultaneously.
    #
    # anchor_susceptibility_match is the dominant frustrator — conflicts with
    # 9 other dimensions. Price anchoring competes with emotional/trust/value.
    ("mental_simulation_resonance", "anchor_susceptibility_match", -0.743),
    ("value_alignment", "anchor_susceptibility_match", -0.673),
    ("emotional_resonance", "anchor_susceptibility_match", -0.662),
    ("personality_brand_alignment", "anchor_susceptibility_match", -0.569),
    ("uniqueness_popularity_fit", "anchor_susceptibility_match", -0.555),
    ("anchor_susceptibility_match", "full_cosine_alignment", -0.473),
    ("anchor_susceptibility_match", "mental_ownership_match", -0.453),
    ("lay_theory_alignment", "anchor_susceptibility_match", -0.417),
    ("identity_signaling_match", "anchor_susceptibility_match", -0.416),
    ("self_monitoring_fit", "anchor_susceptibility_match", -0.362),
    ("construal_fit_score", "anchor_susceptibility_match", -0.320),
    ("linguistic_style_match", "anchor_susceptibility_match", -0.301),
    # reactance × trust: can't build trust and reduce reactance simultaneously
    ("reactance_fit", "brand_trust_fit", -0.496),
    ("negativity_bias_match", "brand_trust_fit", -0.426),
    ("emotional_resonance", "brand_trust_fit", -0.302),
    ("brand_trust_fit", "full_cosine_alignment", -0.457),
    # regulatory_fit conflicts with negativity/reactance/involvement
    ("regulatory_fit_score", "negativity_bias_match", -0.451),
    ("regulatory_fit_score", "reactance_fit", -0.444),
    ("regulatory_fit_score", "involvement_weight_modifier", -0.433),
    ("regulatory_fit_score", "composite_alignment", -0.388),
    ("regulatory_fit_score", "full_cosine_alignment", -0.363),
    ("regulatory_fit_score", "evolutionary_motive_match", -0.358),
    # value_alignment conflicts with processing/evolutionary/involvement/linguistic
    ("value_alignment", "evolutionary_motive_match", -0.489),
    ("value_alignment", "processing_route_match", -0.487),
    ("value_alignment", "involvement_weight_modifier", -0.423),
    ("value_alignment", "linguistic_style_matching", -0.391),
    # uniqueness × distinctiveness
    ("uniqueness_popularity_fit", "optimal_distinctiveness_fit", -0.413),
]

MAX_CPM_FLOOR = 8.00

CPM_FLOOR_TABLE = {
    "t1": {"base_cpm": 2.50, "confidence_multiplier": 1.0},
    "t2": {"base_cpm": 3.50, "confidence_multiplier": 1.2},
    "t3": {"base_cpm": 5.00, "confidence_multiplier": 1.5},
}


def calculate_cpm_floor(
    tier: str, lift_estimate: float, evidence_count: int,
) -> float:
    """CPM floor from evidence strength. Capped at MAX_CPM_FLOOR."""
    config = CPM_FLOOR_TABLE[tier]
    lift_premium = 1.0 + (lift_estimate / 2.0)
    evidence_discount = min(1.0, evidence_count / 100.0)
    raw = config["base_cpm"] * config["confidence_multiplier"] * lift_premium * evidence_discount
    return round(min(raw, MAX_CPM_FLOOR), 2)
