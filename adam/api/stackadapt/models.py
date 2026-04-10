"""
StackAdapt Creative Intelligence API — Request/Response Models
================================================================

Pydantic models for the <50ms creative intelligence endpoint.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

from adam.constants import SEGMENT_ID_REGEX


class CreativeIntelligenceRequest(BaseModel):
    """What StackAdapt (or an advertiser's DCO system) sends us."""

    segment_id: str = Field(
        ...,
        description="INFORMATIV segment ID (e.g. 'informativ_beauty_connector')",
    )

    @field_validator("segment_id")
    @classmethod
    def validate_segment_id(cls, v: str) -> str:
        if not SEGMENT_ID_REGEX.match(v):
            raise ValueError(
                f"Invalid segment_id '{v}'. Expected format: "
                "informativ_<archetype>[_<mechanism>][_<vertical>]_<tier> "
                "(e.g. 'informativ_connector_social_proof_beauty_t1')"
            )
        return v
    content_category: str = Field(
        default="",
        description="IAB or custom content category of the page",
    )
    device_type: str = Field(
        default="desktop",
        description="Device type: desktop, mobile, tablet, connected_tv, etc.",
    )
    page_url: str = Field(
        default="",
        description="URL of the page where the ad will appear",
    )
    time_of_day: int = Field(
        default=12,
        ge=0,
        le=23,
        description="Hour of day (0-23) in the user's local time",
    )
    day_of_week: str = Field(
        default="monday",
        description="Day of week (lowercase)",
    )
    product_category: str = Field(
        default="",
        description="Advertiser product category for cross-category transfer",
    )
    brand_name: str = Field(
        default="",
        description="Advertiser brand name for brand intelligence lookup",
    )
    asin: str = Field(
        default="",
        description="Amazon ASIN for Tier 2 product-specific graph intelligence",
    )
    buyer_id: str = Field(
        default="",
        description="Pseudonymous buyer identifier for information value bidding (hashed, no PII)",
    )

    # ── Additional OpenRTB signals for impression state resolution ──
    # These fields dramatically improve page intelligence when available.
    # The system works without them but produces more precise results with them.
    page_title: str = Field(
        default="",
        description="Content title from OpenRTB content.title (highest psychological signal)",
    )
    referrer: str = Field(
        default="",
        description="Referrer URL from site.ref (reveals reader intent: search vs social vs direct)",
    )
    page_keywords: Optional[List[str]] = Field(
        default=None,
        description="Publisher keywords from site.keywords (publisher-curated psychological signals)",
    )
    iab_categories: Optional[List[str]] = Field(
        default=None,
        description="IAB categories from site.cat (e.g., ['IAB12', 'IAB13'])",
    )

    # CTV content fields (from OpenRTB 2.6 content object)
    content_id: str = Field(default="", description="Content ID (TMDb, IMDB tconst)")
    content_title: str = Field(default="", description="Show/movie title")
    content_series: str = Field(default="", description="Series title (for episodes)")
    content_season: int = Field(default=0, description="Season number")
    content_episode: int = Field(default=0, description="Episode number")
    content_genre: Optional[List[str]] = Field(default=None, description="Genre list")
    content_rating: str = Field(default="", description="Content rating (TV-MA, PG-13)")
    content_duration: int = Field(default=0, description="Content duration in seconds")


class CreativeParameters(BaseModel):
    """Actionable creative parameters for DCO template selection."""

    primary_mechanism: str
    secondary_mechanism: str
    framing: str = Field(description="gain or loss")
    construal_level: str = Field(description="concrete or abstract")
    social_proof_density: str = Field(description="none, low, moderate, high")
    detail_level: str = Field(description="low, moderate, high")
    urgency: str = Field(description="none, low, moderate, high")
    tone: str
    headline_strategy: str
    cta_style: str
    persuasion_route: str
    emotional_vehicle: str
    copy_length: str = Field(description="short, medium, long")


class NDFProfile(BaseModel):
    """7+1 Nonconscious Decision Fingerprint dimensions."""

    approach_avoidance: float = Field(ge=-1.0, le=1.0)
    temporal_horizon: float = Field(ge=0.0, le=1.0)
    social_calibration: float = Field(ge=0.0, le=1.0)
    uncertainty_tolerance: float = Field(ge=0.0, le=1.0)
    status_sensitivity: float = Field(ge=0.0, le=1.0)
    cognitive_engagement: float = Field(ge=0.0, le=1.0)
    arousal_seeking: float = Field(ge=0.0, le=1.0)
    cognitive_velocity: float = Field(ge=0.0, le=1.0)


class CopyGuidance(BaseModel):
    """Natural-language creative guidance for copywriters / DCO engines."""

    headline_templates: List[str]
    value_propositions: List[str]
    cta_templates: List[str] = []
    avoid: List[str] = []


class ExpectedLift(BaseModel):
    """Performance lift estimates backed by empirical data."""

    ctr_lift_pct: float
    conversion_lift_pct: float
    confidence: str
    evidence_source: str = "937M_review_corpus"
    sample_size: int = 0


class MechanismGuidance(BaseModel):
    """Graph-derived mechanism synergy/antagonism guidance."""

    synergies: List[str] = []
    avoid_combinations: List[str] = []


class ProductIntelligence(BaseModel):
    """Tier 2 product-specific graph intelligence."""

    asin: str
    edge_count: int = 0
    alignment_dimensions: Optional[Dict[str, Any]] = None
    intelligence_tier: str = "tier2_live_graph"


class GradientOptimizationPriority(BaseModel):
    """A single dimension optimization recommendation from the gradient field."""

    dimension: str = Field(description="Alignment dimension name")
    current: float = Field(description="Current alignment value for this product")
    optimal: float = Field(description="Optimal value (top-quartile conversion mean)")
    gradient: float = Field(description="Partial derivative of conversion quality w.r.t. this dimension")
    gap: float = Field(description="optimal - current")
    expected_lift_delta: float = Field(description="Expected lift change (percentage points) from optimizing this dimension")
    creative_direction: str = Field(description="What to adjust in the creative, with specific guidance")


class GradientIntelligenceResponse(BaseModel):
    """Psychological gradient field intelligence.

    The gradient field tells you which alignment dimensions to optimize,
    in what direction, by how much, and what the expected lift would be.
    This is the Jacobian of the conversion function.
    """

    optimization_priorities: List[GradientOptimizationPriority] = []
    total_expected_lift_delta: float = Field(description="Sum of all optimization lift deltas")
    field_metadata: Dict[str, Any] = Field(default_factory=dict)


class InformationValueResponse(BaseModel):
    """Psychological Information Value Bidding intelligence.

    Every impression has two values:
    1. Conversion value = P(convert) × revenue
    2. Information value = P(signal) × Δ(model_accuracy) × PV(future_impressions)

    The information value tells the bid engine how much extra to bid for this
    impression because of what it will teach us about this buyer's psychology.
    """

    information_value: float = Field(description="Dollar value of learning from this impression")
    bid_modifier_pct: float = Field(description="Percentage to add to base bid")
    recommended_bid_premium: float = Field(description="Dollar amount to add to CPM")
    exploration_priority: str = Field(description="none | low | medium | high | critical")
    buyer_confidence: float = Field(description="How well-characterized this buyer is (0-1)")
    buyer_interactions: int = Field(description="Total prior interactions with this buyer")
    expected_info_gain: float = Field(description="Expected model accuracy improvement (bits)")
    top_learning_dimensions: Dict[str, float] = Field(
        default_factory=dict,
        description="Per-dimension learning value (highest = most valuable to learn about)",
    )
    reasoning: List[str] = Field(default_factory=list)


class ContextIntelligenceResponse(BaseModel):
    """Page-level psychological context intelligence.

    The page where the ad appears primes the buyer's cognitive state.
    This intelligence tells StackAdapt what mindset the buyer is in
    based on the content environment, and how mechanism effectiveness
    shifts as a result.
    """

    domain: str = Field(default="", description="Normalized domain of the placement page")
    mindset: str = Field(default="unknown", description="Detected psychological mindset: informed, purchasing, social, etc.")
    attention_level: str = Field(default="medium", description="Expected attention: high, medium, low")
    purchase_intent: str = Field(default="browsing", description="Buying readiness: none, browsing, considering, ready")
    mechanism_adjustments: Dict[str, float] = Field(
        default_factory=dict,
        description="Per-mechanism effectiveness multiplier (1.0=neutral, >1.0=boosted, <1.0=dampened)",
    )
    recommended_mechanisms: List[str] = Field(
        default_factory=list,
        description="Top mechanisms for this context (already reflected in creative_parameters)",
    )
    avoid_mechanisms: List[str] = Field(
        default_factory=list,
        description="Mechanisms that may backfire in this context",
    )
    optimal_tone: str = Field(default="", description="Recommended tone for this placement context")
    recommended_complexity: str = Field(default="", description="simple, moderate, or detailed")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Context detection confidence")


class MechanismScoreEntry(BaseModel):
    """A mechanism with its confidence score."""

    mechanism: str
    score: float = Field(ge=0.0, le=1.0, description="Confidence-weighted effectiveness score")


class MechanismPortfolioEntry(BaseModel):
    """A mechanism in the optimized portfolio with weight and synergy analysis."""

    mechanism: str = Field(description="Mechanism name")
    weight: float = Field(
        ge=0.0, le=1.0,
        description="Portfolio allocation weight (all weights sum to 1.0)",
    )
    base_score: float = Field(description="Base effectiveness before synergy adjustment")
    interaction_bonus: float = Field(
        description="Synergy bonus from learned mechanism interactions (positive=synergistic, negative=suppressive)",
    )
    portfolio_score: float = Field(description="Final score after synergy adjustment")


class MechanismPortfolioResponse(BaseModel):
    """Mechanism portfolio optimization result.

    Instead of picking a single mechanism, the system allocates weights
    across a portfolio that maximizes expected conversion while accounting
    for learned synergies and antagonisms between mechanisms.

    Analogous to Modern Portfolio Theory: mechanisms are "assets," the
    "return" is conversion probability, and the "covariance" comes from
    learned interaction patterns across millions of bilateral edges.
    """

    portfolio: List[MechanismPortfolioEntry] = Field(
        description="Mechanisms with optimal allocation weights",
    )
    observation_count: int = Field(
        default=0,
        description="Number of outcome observations backing the interaction matrix",
    )


class ArbitrageIntelligenceResponse(BaseModel):
    """Psychological arbitrage: where ADAM sees value the market doesn't.

    Every impression where arbitrage_score > 1.0 means ADAM predicts
    higher conversion than a demographics-based system would. The delta
    is pure alpha from psychological intelligence.
    """

    arbitrage_score: float = Field(
        description="ADAM predicted / market baseline. >1.0 = bid aggressively.",
    )
    adam_predicted_effectiveness: float = Field(
        description="ADAM's conversion prediction from bilateral evidence (0-1)",
    )
    market_baseline_effectiveness: float = Field(
        description="Market-implied conversion from demographics only (0-1)",
    )
    recommended_bid_multiplier: float = Field(
        description="Suggested multiplier on base CPM (0.3x to 3.0x)",
    )
    alpha_value: float = Field(
        description="Dollar-denominated alpha per impression (CPM units)",
    )
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in arbitrage estimate")
    arbitrage_drivers: List[str] = Field(
        default_factory=list,
        description="Which psychological dimensions drive the arbitrage opportunity",
    )
    reasoning: List[str] = Field(default_factory=list)


class SessionStateResponse(BaseModel):
    """Within-session psychological state estimation.

    The buyer's baseline profile tells us who they ARE. Session state
    tells us where they are RIGHT NOW based on their browsing behavior
    in this session. Creative should adapt to current state, not just
    baseline profile.
    """

    session_phase: str = Field(
        description="entry, exploration, evaluation, consideration, or decision",
    )
    observation_count: int = Field(description="Observations in this session")
    session_duration_seconds: float = Field(description="Session duration")
    ndf_adjustments: Dict[str, float] = Field(
        default_factory=dict,
        description="Additive deltas to apply on top of baseline NDF profile",
    )
    creative_adjustments: Dict[str, Any] = Field(
        default_factory=dict,
        description="Session-phase-specific creative parameter adjustments",
    )
    decision_readiness: float = Field(
        ge=0.0, le=1.0,
        description="How close the buyer is to a purchase decision (0=browsing, 1=ready)",
    )


class CounterfactualAlternative(BaseModel):
    """What would have happened with a different mechanism."""

    mechanism: str
    expected_effectiveness: float = Field(description="Predicted effectiveness if this mechanism were used (0-1)")
    delta_vs_chosen: float = Field(description="Difference from chosen mechanism (positive = better)")
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""


class CounterfactualAnalysisResponse(BaseModel):
    """Evidence-backed counterfactual analysis.

    Not simulation — real outcomes from psychologically similar buyers
    who received different mechanisms. Answers: 'If we had used mechanism Y
    instead of X, what would have happened?'
    """

    chosen_mechanism: str
    chosen_effectiveness: float
    alternatives: List[CounterfactualAlternative] = Field(
        description="Alternative mechanisms ranked by expected effectiveness",
    )
    chosen_is_optimal: bool = Field(
        description="Whether the chosen mechanism is the best option given evidence",
    )
    best_alternative: str = Field(
        default="",
        description="If chosen is not optimal, which mechanism would be better",
    )
    evidence_depth: str = Field(description="archetype_prior, category_posterior, bilateral_edges, etc.")
    reasoning: List[str] = Field(default_factory=list)


class EnrichedCopyGuidance(BaseModel):
    """Copy guidance enriched with gradient-driven optimization priorities.

    Unlike the base CopyGuidance (static templates), this provides
    continuous, evidence-weighted creative direction from the gradient field.
    """

    headline_templates: List[str] = []
    value_propositions: List[str] = []
    cta_templates: List[str] = []
    avoid: List[str] = []
    gradient_creative_directions: List[str] = Field(
        default_factory=list,
        description=(
            "Gradient-driven creative directions: which psychological dimensions "
            "to emphasize and by how much, ranked by expected lift."
        ),
    )
    mechanism_reasoning: List[str] = Field(
        default_factory=list,
        description="Why each mechanism was selected (psychological reasoning chain)",
    )


class CreativeIntelligenceResponse(BaseModel):
    """Full creative intelligence payload returned in <50ms."""

    decision_id: str = Field(
        default="",
        description=(
            "Unique decision identifier. Echo this back in conversion webhook "
            "event_args.decision_id so the learning loop can link outcomes to "
            "the exact decision that produced them."
        ),
    )
    creative_parameters: CreativeParameters
    ndf_profile: NDFProfile
    copy_guidance: CopyGuidance
    expected_lift: ExpectedLift
    mechanism_chain: List[str] = []
    mechanism_scores: Optional[Dict[str, float]] = Field(
        default=None,
        description=(
            "All mechanisms ranked by effectiveness with confidence scores. "
            "Unlike mechanism_chain (unscored list), this shows HOW confident "
            "each recommendation is."
        ),
    )
    reasoning_trace: List[str] = []
    segment_metadata: Dict[str, Any] = {}
    mechanism_guidance: Optional[MechanismGuidance] = None
    product_intelligence: Optional[ProductIntelligence] = None
    gradient_intelligence: Optional[GradientIntelligenceResponse] = Field(
        default=None,
        description="Psychological gradient field: which dimensions to optimize for maximum lift",
    )
    information_value: Optional[InformationValueResponse] = Field(
        default=None,
        description="Information value bidding: how much extra to bid for learning about this buyer",
    )
    context_intelligence: Optional[ContextIntelligenceResponse] = Field(
        default=None,
        description=(
            "Page-level psychological context: what mindset the placement page "
            "puts the buyer in, and how mechanism effectiveness shifts as a result."
        ),
    )
    mechanism_portfolio: Optional[MechanismPortfolioResponse] = Field(
        default=None,
        description=(
            "Mechanism portfolio optimization: instead of a single mechanism, "
            "allocates weights across a portfolio accounting for learned synergies. "
            "Available after sufficient outcome observations accumulate."
        ),
    )
    category_deviation: Optional[Dict[str, float]] = Field(
        default=None,
        description=(
            "How this category deviates from the universal psychological pattern. "
            "Positive = mechanism MORE effective here than average. "
            "Negative = LESS effective. The deviation IS the category-specific knowledge."
        ),
    )
    decision_probability: Optional[Dict[str, Any]] = Field(
        default=None,
        description=(
            "NDF congruence-based purchase probability. P = σ(Σ wᵢ · match(buyerᵢ, messageᵢ)). "
            "Includes per-dimension congruence analysis, backfire risk, and continuous "
            "creative weights that replace categorical bins."
        ),
    )
    counterfactual: Optional[CounterfactualAnalysisResponse] = Field(
        default=None,
        description=(
            "Evidence-backed counterfactual: what would happen with each "
            "alternative mechanism, based on real outcomes from similar buyers."
        ),
    )
    arbitrage: Optional[ArbitrageIntelligenceResponse] = Field(
        default=None,
        description=(
            "Psychological arbitrage: where ADAM sees conversion value that "
            "demographics-based systems miss. Score >1.0 = bid aggressively."
        ),
    )
    session_state: Optional[SessionStateResponse] = Field(
        default=None,
        description=(
            "Within-session psychological state: adapts creative to where "
            "the buyer IS RIGHT NOW, not just who they ARE."
        ),
    )
    timing_ms: float = Field(description="End-to-end latency in milliseconds")
    cascade_level: int = Field(default=1, description="Highest cascade level reached (1-5)")
    intelligence_level: str = Field(
        default="L1_archetype",
        description=(
            "Human-readable intelligence tier: L3_bilateral (real edge evidence), "
            "L2_category (category posterior), L1_archetype (cold-start prior), "
            "static_heuristic (no graph data). Consumers should check this to "
            "know whether the response is backed by empirical evidence or defaults."
        ),
    )
    evidence_source: str = Field(default="archetype_prior", description="Source of strongest evidence used")


class SegmentListItem(BaseModel):
    """Summary of an available INFORMATIV segment."""

    segment_id: str
    name: str
    archetype: str
    category: str = ""
    description: str = ""
    top_mechanisms: List[str] = []
    expected_ctr_lift_pct: float = 0.0


class SegmentListResponse(BaseModel):
    """All available INFORMATIV segments."""

    segments: List[SegmentListItem]
    total: int
    provider: str = "INFORMATIV"


class HealthResponse(BaseModel):
    """Health check for the creative intelligence service."""

    status: str
    registries_loaded: bool
    priors_loaded: bool
    graph_cache_available: bool = False
    segments_available: int
    avg_latency_ms: float
    version: str = "2.0.0"
    graph_cache: Optional[Dict[str, Any]] = None
