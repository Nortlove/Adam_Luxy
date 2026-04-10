# =============================================================================
# ADAM Universal Intelligence API — Models
# Location: adam/api/universal/models.py
# =============================================================================

"""
Models for the Universal Intelligence API.

This API serves all four participants in the ad transaction:
  - Publishers:  "What psychological environment does my content create?"
  - SSPs:        "What is this impression psychologically worth?"
  - DSPs:        Already served by /api/v1/stackadapt/ — this adds cross-DSP support
  - Brands:      "How does my messaging psychology match audiences?"

Same intelligence primitives, four lenses. All backed by 47M bilateral edges.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# SHARED MODELS (used across all client types)
# =============================================================================

class PsychologicalProfile(BaseModel):
    """8-dimension NDF psychological profile."""

    approach_avoidance: float = Field(0.5, ge=0.0, le=1.0)
    temporal_horizon: float = Field(0.5, ge=0.0, le=1.0)
    social_calibration: float = Field(0.5, ge=0.0, le=1.0)
    uncertainty_tolerance: float = Field(0.5, ge=0.0, le=1.0)
    status_sensitivity: float = Field(0.5, ge=0.0, le=1.0)
    cognitive_engagement: float = Field(0.5, ge=0.0, le=1.0)
    arousal_seeking: float = Field(0.5, ge=0.0, le=1.0)
    cognitive_velocity: float = Field(0.5, ge=0.0, le=1.0)


class PsychologicalSegment(BaseModel):
    """A psychological audience segment."""

    segment_id: str
    name: str
    description: str = ""
    strength: float = Field(0.0, ge=0.0, le=1.0)
    iab_taxonomy_ids: List[str] = Field(default_factory=list)
    recommended_mechanisms: List[str] = Field(default_factory=list)


class MechanismScore(BaseModel):
    """Effectiveness score for a persuasion mechanism."""

    mechanism: str
    score: float = Field(ge=0.0, le=1.0)
    evidence_depth: str = "unknown"  # strong, moderate, weak, none
    source: str = ""  # graph, theory, corpus, blended


class IntelligenceLevel(str, Enum):
    """Quality tier of intelligence in the response."""

    L3_BILATERAL = "L3_bilateral"
    L2_CATEGORY = "L2_category"
    L1_ARCHETYPE = "L1_archetype"
    HEURISTIC = "static_heuristic"


class GradientPriority(BaseModel):
    """
    Which psychological dimension yields the most conversion lift if optimized.

    Derived from ∂P(conversion)/∂alignment_dimension — the gradient field
    pre-computed from BRAND_CONVERTED edges via OLS regression. This tells
    creative teams WHERE to invest effort: a dimension with gradient=0.34
    moves conversion probability 3.4x more per unit change than one with 0.10.
    """

    dimension: str = Field(description="Psychological dimension name")
    gradient_magnitude: float = Field(
        description="∂P(conversion)/∂dimension — how much conversion moves per unit change",
    )
    current_value: float = Field(
        0.5,
        description="Current alignment on this dimension (from bilateral edges or NDF)",
    )
    optimal_value: float = Field(
        0.5,
        description="Optimal alignment (75th percentile of converters in this category)",
    )
    expected_lift_pct: float = Field(
        0.0,
        description="Expected conversion lift (%) if dimension moved from current to optimal",
    )
    creative_direction: str = Field(
        "",
        description="What this means for creative: 'increase narrative transport' → more story-driven copy",
    )


class MechanismSynergy(BaseModel):
    """
    Interaction between two persuasion mechanisms — amplifying or cancelling.

    From MECHANISM_SYNERGY edges in Neo4j and the mechanism interaction learner.
    Creative teams MUST know this: deploying authority + social_proof amplifies
    (1.3x combined lift), but scarcity + exclusivity antagonizes (0.6x).
    """

    mechanism_a: str
    mechanism_b: str
    synergy_score: float = Field(
        description="<1.0 = antagonism, 1.0 = independent, >1.0 = amplification",
    )
    combined_lift: float = Field(
        0.0,
        description="Empirical combined conversion lift when both active",
    )
    context: str = Field(
        "",
        description="When this synergy is strongest (e.g., 'high cognitive engagement')",
    )


class DimensionConfidence(BaseModel):
    """
    How much evidence backs each psychological dimension.

    Not all dimensions are equally known. Some have 500 bilateral edges
    of evidence; others are inferred from archetype priors with 0 direct
    evidence. Callers pricing at $50M/year need to know which signals to
    trust and which to hedge.
    """

    dimension: str
    evidence_edges: int = Field(0, description="Direct bilateral edge observations")
    source: str = Field(
        "default",
        description="Where this dimension came from: bilateral_edge, bayesian_prior, theory_graph, content_profiler, default",
    )
    confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="0=no evidence (defaulted to 0.5), 1=high-evidence bilateral aggregate",
    )


# =============================================================================
# FULL-POWER MODELS — expose the complete bilateral edge + construct layer
# =============================================================================

class BilateralDimension(BaseModel):
    """
    One dimension from the full 27-dimension bilateral edge vector.

    Each dimension has per-dim audit: how many edges contributed, what the
    standard deviation is, and where the value came from. This replaces the
    7-dim NDF compression with the full map.
    """

    name: str = Field(description="Dimension name (e.g., 'regulatory_fit_score')")
    value: float = Field(0.5, description="Mean value across bilateral edges")
    std_dev: Optional[float] = Field(None, description="Standard deviation across edges")
    edge_count: int = Field(0, description="Number of edges contributing to this dimension")
    source: str = Field("bilateral_edge", description="Data source: bilateral_edge, category_aggregate, default")
    temporal_stability: Optional[float] = Field(
        None, description="How stable this dimension is over time (0=volatile, 1=stable)",
    )
    inference_tractability: Optional[float] = Field(
        None, description="How confidently this can be inferred from available data (0-1)",
    )


class ConstructActivation(BaseModel):
    """
    A psychological construct activated by the bilateral edge evidence.

    Maps from bilateral edge dimensions to the 524-construct taxonomy.
    E.g., construal_fit_score=0.8 → cognitive_nfc activation proportionally.
    """

    construct_id: str = Field(description="Construct identifier from taxonomy")
    domain: str = Field("", description="Construct domain (e.g., 'cognitive_processing', 'self_regulatory')")
    activation_level: float = Field(0.0, ge=0.0, le=1.0, description="Activation strength")
    source: str = Field("", description="How this was inferred: bilateral_edge, theory_graph, construct_mapping")
    mechanism_influences: Dict[str, float] = Field(
        default_factory=dict,
        description="Which mechanisms this construct activates/suppresses",
    )


class GranularTypeProfile(BaseModel):
    """
    Profile from the GranularCustomerTypeDetector (3,750 types).

    Provides fine-grained customer typing with mechanism-specific recommendations
    rather than the 8 coarse archetypes.
    """

    type_id: str = Field(description="Granular type ID (e.g., 'QUALITY_SEEKING_SYSTEM2_PROMOTION_HIGH')")
    type_name: str = Field("", description="Human-readable type name")
    dimensions: Dict[str, str] = Field(
        default_factory=dict,
        description="Dimension values (motivation, decision_style, regulatory_focus, etc.)",
    )
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    mechanism_effectiveness: Dict[str, float] = Field(
        default_factory=dict,
        description="Per-mechanism effectiveness for this type (0-1)",
    )
    recommended_mechanisms: List[str] = Field(
        default_factory=list,
        description="Top mechanisms for this granular type",
    )


class EnrichedSegment(BaseModel):
    """
    Psychology-first segment from PsychologicalSegmentEngine (8 segments).

    Replaces the 14-rule SegmentBuilder with construct-defined segments that
    include creative guidance, mechanism recommendations, and mechanisms to avoid.
    """

    segment_id: str
    name: str
    description: str = ""
    defining_constructs: Dict[str, float] = Field(
        default_factory=dict,
        description="Constructs that define this segment (construct_id → activation level)",
    )
    regulatory_orientation: str = Field(
        "", description="promotion, prevention, or balanced",
    )
    processing_style: str = Field(
        "", description="systematic, heuristic, or moderate",
    )
    mechanism_recommendations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Ranked mechanism recommendations with reasoning",
    )
    mechanisms_to_avoid: List[str] = Field(
        default_factory=list,
        description="Mechanisms that backfire for this segment",
    )
    creative_guidance: Dict[str, Any] = Field(
        default_factory=dict,
        description="Frame, tone, CTA style, detail level for this segment",
    )
    estimated_prevalence: float = Field(
        0.0, ge=0.0, le=1.0, description="Fraction of population in this segment",
    )
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    strength: float = Field(0.0, ge=0.0, le=1.0, description="Match strength for this profile")
    # Backward-compat with PsychologicalSegment
    iab_taxonomy_ids: List[str] = Field(default_factory=list)
    recommended_mechanisms_list: List[str] = Field(
        default_factory=list,
        description="Flat mechanism list (backward-compat with PsychologicalSegment)",
    )


class InteractionAwareDirection(BaseModel):
    """
    Creative direction that accounts for mechanism interactions.

    Combines gradient priorities (where to invest) with synergy data
    (which mechanisms amplify each other) for joint recommendations.
    """

    primary_mechanism: str = Field(description="Lead mechanism for this direction")
    synergistic_mechanisms: List[str] = Field(
        default_factory=list,
        description="Mechanisms that amplify the primary",
    )
    antagonistic_mechanisms: List[str] = Field(
        default_factory=list,
        description="Mechanisms to avoid combining with primary",
    )
    gradient_dimension: str = Field(
        "", description="Which bilateral dimension this targets",
    )
    gradient_magnitude: float = Field(
        0.0, description="How much conversion moves per unit change on this dimension",
    )
    combined_expected_lift_pct: float = Field(
        0.0, description="Expected lift when primary + synergistic deployed together",
    )
    creative_brief: str = Field(
        "",
        description=(
            "Actionable brief: 'Lead with [mechanism] on [dimension] — "
            "synergizes with [mechanism_b] for [lift]% combined lift. "
            "Avoid [antagonistic] which would cancel the effect.'"
        ),
    )


# =============================================================================
# PUBLISHER MODELS
# =============================================================================

class PageProfileRequest(BaseModel):
    """Request to profile a page's psychological environment."""

    page_url: Optional[str] = None
    title: str = Field(description="Page title")
    body_text: str = Field(description="Page body text (first 5000 chars sufficient)")
    category: Optional[str] = Field(
        None, description="IAB category if known (e.g., 'IAB13' for personal finance)"
    )
    publisher_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PagePsychologyLayer(BaseModel):
    """One of the 8 psychological layers of a page."""

    layer_name: str
    layer_number: int
    value: Any
    description: str = ""


class VerticalValue(BaseModel):
    """How valuable this page's psychology is for a specific advertiser vertical."""

    vertical: str
    value_multiplier: float = Field(
        1.0,
        description="CPM multiplier relative to average (1.0 = average, 1.5 = 50% premium)",
    )
    reasoning: str = ""
    top_mechanisms: List[str] = Field(default_factory=list)


class TheoryChainSummary(BaseModel):
    """Summary of a theory-backed causal reasoning chain."""

    mechanism: str = Field(description="Recommended mechanism (e.g., 'authority')")
    score: float = Field(0.0, ge=0.0, le=1.0)
    active_states: List[str] = Field(
        default_factory=list,
        description="Psychological states activated by this NDF profile",
    )
    active_needs: List[str] = Field(
        default_factory=list,
        description="Psychological needs inferred from active states",
    )
    creative_guidance: Dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Theory-backed creative direction: what_to_say, what_not_to_say, "
            "tone, detail_level, urgency_level, social_framing"
        ),
    )
    confidence: float = Field(0.0, ge=0.0, le=1.0)


class PageProfileResponse(BaseModel):
    """Complete psychological profile of a page."""

    page_url: Optional[str] = None
    psychological_profile: PsychologicalProfile
    extended_dimensions: Dict[str, float] = Field(
        default_factory=dict,
        description=(
            "Extended psychological dimensions beyond core 7 NDF: "
            "social_proof_sensitivity, loss_aversion_intensity, cognitive_load_tolerance, "
            "narrative_transport, temporal_discounting, autonomy_reactance, decision_entropy"
        ),
    )
    psychological_layers: List[PagePsychologyLayer] = Field(default_factory=list)
    segments: List[PsychologicalSegment] = Field(default_factory=list)
    vertical_values: List[VerticalValue] = Field(default_factory=list)
    dominant_mindset: str = ""
    processing_route: str = ""  # central, peripheral, experiential, narrative
    mechanism_receptivity: List[MechanismScore] = Field(default_factory=list)
    theory_chains: List[TheoryChainSummary] = Field(
        default_factory=list,
        description=(
            "Theory-backed causal reasoning chains: State → Need → Mechanism. "
            "Includes creative guidance and the 'why' behind each mechanism recommendation."
        ),
    )
    gradient_priorities: List[GradientPriority] = Field(
        default_factory=list,
        description=(
            "Ranked by expected conversion lift: which psychological dimensions "
            "matter most for advertisers on this page. Derived from ∂P(conversion)/∂dim."
        ),
    )
    mechanism_synergies: List[MechanismSynergy] = Field(
        default_factory=list,
        description=(
            "Mechanism interaction pairs: which combinations amplify vs. cancel. "
            "Creative teams must deploy synergistic pairs, not antagonistic ones."
        ),
    )
    dimension_confidence: List[DimensionConfidence] = Field(
        default_factory=list,
        description="Per-dimension evidence depth — which signals to trust vs. hedge.",
    )
    # --- Full-power fields (Phase C upgrade) ---
    bilateral_dimensions: List[BilateralDimension] = Field(
        default_factory=list,
        description="Full 27-dim bilateral edge vector with per-dim audit",
    )
    construct_activations: List[ConstructActivation] = Field(
        default_factory=list,
        description="Active constructs from 524-construct taxonomy",
    )
    granular_type: Optional[GranularTypeProfile] = Field(
        None, description="Fine-grained customer type from GranularCustomerTypeDetector",
    )
    enriched_segments: List[EnrichedSegment] = Field(
        default_factory=list,
        description="Psychology-first segments from PsychologicalSegmentEngine",
    )
    interaction_aware_directions: List[InteractionAwareDirection] = Field(
        default_factory=list,
        description="Joint gradient+synergy creative directions",
    )
    metadata_signals: Dict[str, float] = Field(
        default_factory=dict,
        description="Verified purchase trust, recency, star rating polarization",
    )
    confidence: float = Field(0.0, ge=0.0, le=1.0)
    intelligence_level: IntelligenceLevel = IntelligenceLevel.HEURISTIC
    edge_evidence_count: int = Field(
        0, description="Bilateral conversion edges backing this profile",
    )
    profiling_ms: float = 0.0


# =============================================================================
# SSP MODELS
# =============================================================================

class BidEnrichmentRequest(BaseModel):
    """Request to enrich a bid request with psychological signals."""

    impression_id: str
    page_url: Optional[str] = None
    page_title: Optional[str] = None
    page_category: Optional[str] = None
    device_type: Optional[str] = None
    time_of_day: Optional[int] = None
    advertiser_vertical: Optional[str] = Field(
        None,
        description=(
            "Advertiser's vertical (e.g., 'financial_services', 'luxury_goods'). "
            "When provided, floor_multiplier is computed specifically for this "
            "vertical instead of averaging top 3."
        ),
    )
    # Pre-computed page profile (if cached)
    cached_page_profile: Optional[Dict[str, Any]] = None


class OpenRTBSegment(BaseModel):
    """Psychological segment in OpenRTB 2.5 format."""

    id: str = Field(description="Segment ID (e.g., 'informativ_promotion_seeker')")
    name: str = ""
    value: str = Field("", description="Segment strength as string (e.g., '0.82')")


class OpenRTBData(BaseModel):
    """OpenRTB 2.5 data object with INFORMATIV psychological segments."""

    id: str = "informativ"
    name: str = "INFORMATIV Psychological Intelligence"
    segment: List[OpenRTBSegment] = Field(default_factory=list)


class BidEnrichmentResponse(BaseModel):
    """Psychological enrichment for a bid request."""

    impression_id: str
    openrtb_data: OpenRTBData
    floor_multiplier: float = Field(
        1.0,
        description="Recommended CPM floor multiplier based on psychological value",
    )
    psychological_profile: Optional[PsychologicalProfile] = None
    dominant_mindset: str = ""
    channel_open: bool = Field(
        True, description="False if page psychology suggests ad fatigue or hostility"
    )
    channel_openness: float = Field(
        1.0,
        ge=0.0,
        le=1.0,
        description=(
            "Continuous channel openness score (0=closed, 1=fully open). "
            "Multi-dimensional: cognitive engagement, arousal, approach, entropy."
        ),
    )
    edge_evidence_count: int = Field(
        0,
        description=(
            "Number of bilateral conversion edges backing this enrichment. "
            "Higher = more confident floor pricing. 0 = heuristic only."
        ),
    )
    mechanism_receptivity: List[MechanismScore] = Field(
        default_factory=list,
        description="Top mechanisms for this psychological environment with evidence depth",
    )
    mechanism_synergies: List[MechanismSynergy] = Field(
        default_factory=list,
        description="Which mechanism combinations amplify vs cancel for this impression",
    )
    gradient_priorities: List[GradientPriority] = Field(
        default_factory=list,
        description="Ranked dimensions by conversion lift potential for this impression context",
    )
    # --- Full-power fields (Phase C upgrade) ---
    bilateral_dimensions: List[BilateralDimension] = Field(
        default_factory=list,
        description="Bilateral edge dimensions (lightweight, from category aggregate)",
    )
    enriched_segments: List[EnrichedSegment] = Field(
        default_factory=list,
        description="Psychology-first segments from cached SegmentEngine",
    )
    intelligence_level: IntelligenceLevel = IntelligenceLevel.HEURISTIC
    page_intelligence_tier: str = Field(
        "domain_heuristic",
        description=(
            "Page intelligence tier: 'crawled_deep' (LLM-analyzed), "
            "'crawled_fast' (NLP+DOM), 'domain_heuristic' (domain-level only)"
        ),
    )
    recommended_ad_position: str = Field(
        "",
        description=(
            "Optimal ad position based on narrative arc analysis: "
            "early, mid, late, post_climax"
        ),
    )
    estimated_viewability: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Estimated ad viewability based on DOM analysis",
    )
    category_temperature: float = Field(
        0.0,
        description=(
            "Category conversion temperature (-2 to +2 std devs from baseline). "
            "Positive = heating market, negative = cooling."
        ),
    )
    active_events: List[str] = Field(
        default_factory=list,
        description="Active cultural/news events affecting this impression context",
    )
    enrichment_ms: float = 0.0


# =============================================================================
# BRAND MODELS
# =============================================================================

class BrandProfileRequest(BaseModel):
    """Request to analyze a brand's messaging psychology."""

    brand_name: str
    brand_description: str = ""
    product_description: str = ""
    sample_ad_copy: Optional[str] = None
    target_category: Optional[str] = None
    asin: Optional[str] = None


class AudienceAlignment(BaseModel):
    """How well a brand's psychology aligns with an audience segment."""

    segment: PsychologicalSegment
    alignment_score: float = Field(ge=0.0, le=1.0)
    alignment_dimensions: Dict[str, float] = Field(default_factory=dict)
    opportunity: str = ""  # "strong match", "growth opportunity", "misaligned"


class BrandProfileResponse(BaseModel):
    """Complete psychological profile of a brand's messaging."""

    brand_name: str
    brand_archetype: str = Field(
        "",
        description="Closest buyer archetype this brand's messaging activates",
    )
    messaging_profile: PsychologicalProfile
    dominant_mechanisms: List[MechanismScore] = Field(default_factory=list)
    audience_alignments: List[AudienceAlignment] = Field(default_factory=list)
    creative_direction: Dict[str, Any] = Field(default_factory=dict)
    competitive_whitespace: List[str] = Field(default_factory=list)
    gradient_priorities: List[Dict[str, Any]] = Field(default_factory=list)
    # --- Full-power fields (Phase C upgrade) ---
    bilateral_dimensions: List[BilateralDimension] = Field(
        default_factory=list,
        description="Full bilateral edge dimensions for seller-side psychology",
    )
    construct_activations: List[ConstructActivation] = Field(
        default_factory=list,
        description="Active constructs from seller-side annotations",
    )
    enriched_segments: List[EnrichedSegment] = Field(
        default_factory=list,
        description="Audience segments from PsychologicalSegmentEngine",
    )
    interaction_aware_directions: List[InteractionAwareDirection] = Field(
        default_factory=list,
        description="Joint gradient+synergy creative directions",
    )
    intelligence_level: IntelligenceLevel = IntelligenceLevel.HEURISTIC
    analysis_ms: float = 0.0


# =============================================================================
# INVENTORY MATCHING MODELS (Publisher × Brand)
# =============================================================================

class InventoryMatchRequest(BaseModel):
    """Request to match a brand's psychology to publisher inventory."""

    brand_profile: BrandProfileRequest
    page_profiles: List[PageProfileRequest] = Field(
        default_factory=list,
        description="Pages to evaluate (or empty to match against cached inventory)",
    )
    top_k: int = Field(10, ge=1, le=100)


class InventoryMatch(BaseModel):
    """A match between a brand and a page."""

    page_url: Optional[str] = None
    page_title: str = ""
    match_score: float = Field(ge=0.0, le=1.0)
    psychological_alignment: Dict[str, float] = Field(default_factory=dict)
    bilateral_alignment: Dict[str, float] = Field(
        default_factory=dict,
        description="All 27 bilateral dimensions alignment (replaces 7-dim psychological_alignment)",
    )
    recommended_mechanisms: List[str] = Field(default_factory=list)
    cpm_premium: float = 1.0
    reasoning: str = ""


class InventoryMatchResponse(BaseModel):
    """Ranked matches between a brand and publisher inventory."""

    matches: List[InventoryMatch] = Field(default_factory=list)
    brand_name: str = ""
    total_inventory_evaluated: int = 0
    analysis_ms: float = 0.0
