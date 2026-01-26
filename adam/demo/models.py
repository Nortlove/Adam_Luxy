# =============================================================================
# ADAM Demo - Data Models
# =============================================================================

"""
Data models for the ADAM demonstration platform.

PHILOSOPHICAL FOUNDATION:
- Demographics DON'T predict behavior
- STATE (momentary psychological state) + TRAITS (stable personality) DO
- We infer WHO someone is psychologically from:
  1. Content consumption (music genre, podcast type, show content)
  2. Time patterns (when they listen, duration)
  3. Implicit signals (nonconscious behavioral tendencies)
  4. Linguistic patterns (how they express themselves in reviews)

This demo showcases the "Unknown User → Known User" capability
WITHOUT requiring login/identity data.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict


# =============================================================================
# ENUMS
# =============================================================================

class DemoScenario(str, Enum):
    """Available demonstration scenarios."""
    IHEART_RADIO_AD = "iheart_radio_ad"
    PODCAST_SPONSORSHIP = "podcast_sponsorship"
    DIGITAL_DISPLAY_AD = "digital_display_ad"
    AUDIO_STREAMING_AD = "audio_streaming_ad"


class AgeRange(str, Enum):
    """Target age ranges."""
    AGE_18_24 = "18-24"
    AGE_25_34 = "25-34"
    AGE_35_44 = "35-44"
    AGE_45_54 = "45-54"
    AGE_55_64 = "55-64"
    AGE_65_PLUS = "65+"


class Gender(str, Enum):
    """Target gender."""
    ALL = "all"
    MALE = "male"
    FEMALE = "female"


class IncomeLevel(str, Enum):
    """Target income levels."""
    ALL = "all"
    LOW = "low"
    MIDDLE = "middle"
    UPPER_MIDDLE = "upper_middle"
    HIGH = "high"


class InferenceSource(str, Enum):
    """Sources of psychological inference."""
    STATION_FORMAT = "station_format"
    CONTENT_TYPE = "content_type"
    TIME_OF_DAY = "time_of_day"
    LISTENING_DURATION = "listening_duration"
    SKIP_BEHAVIOR = "skip_behavior"
    VOLUME_PATTERNS = "volume_patterns"
    DEVICE_TYPE = "device_type"
    LOCATION_CONTEXT = "location_context"
    LINGUISTIC_PATTERNS = "linguistic_patterns"
    PURCHASE_HISTORY = "purchase_history"
    REVIEW_SENTIMENT = "review_sentiment"
    AMAZON_PRIORS = "amazon_priors"


class ProcessingRoute(str, Enum):
    """Cognitive processing route."""
    CENTRAL = "central"      # Deep, analytical processing
    PERIPHERAL = "peripheral"  # Quick, heuristic processing
    MIXED = "mixed"          # Context-dependent


# =============================================================================
# INPUT MODELS
# =============================================================================

class BrandInfo(BaseModel):
    """Brand information input."""
    
    brand_name: str = Field(default="Your Brand", description="Name of the brand advertising")
    brand_description: Optional[str] = Field(None, description="Brief brand description")
    brand_values: List[str] = Field(default_factory=list, description="Core brand values")
    brand_tone: Optional[str] = Field(None, description="Brand voice/tone (e.g., professional, playful)")
    industry: Optional[str] = Field(None, description="Industry/category")


class ProductInfo(BaseModel):
    """Product information input."""
    
    product_name: str = Field(default="Your Product", description="Name of the product being advertised")
    product_description: Optional[str] = Field(None, description="Product description")
    product_url: Optional[str] = Field(None, description="Product URL if available")
    price_point: Optional[str] = Field(None, description="Price range or specific price")
    key_benefits: List[str] = Field(default_factory=list, description="Key product benefits")
    unique_selling_points: List[str] = Field(default_factory=list, description="What makes it unique")


class AdvertisementInfo(BaseModel):
    """Advertisement creative input."""
    
    ad_copy: Optional[str] = Field(None, description="Current advertisement copy")
    headline: Optional[str] = Field(None, description="Ad headline if separate")
    call_to_action: Optional[str] = Field(None, description="Desired CTA")
    creative_url: Optional[str] = Field(None, description="URL to creative asset")
    creative_type: Optional[str] = Field(None, description="Type: audio, image, video")
    duration_seconds: Optional[int] = Field(None, description="Ad duration for audio/video")


class CustomerTarget(BaseModel):
    """Customer targeting specifics."""
    
    # Demographics (optional, NOT primary)
    age_ranges: List[AgeRange] = Field(default_factory=list, description="Target age ranges")
    gender: Gender = Field(default=Gender.ALL, description="Target gender")
    income_levels: List[IncomeLevel] = Field(default_factory=list, description="Target income")
    locations: List[str] = Field(default_factory=list, description="Target locations/DMAs")
    
    # Psychographics (PRIMARY - what actually predicts behavior)
    interests: List[str] = Field(default_factory=list, description="Target interests")
    lifestyle: Optional[str] = Field(None, description="Target lifestyle description")
    values: List[str] = Field(default_factory=list, description="Target values")
    
    # Behavioral
    purchase_intent: Optional[str] = Field(None, description="Purchase intent signals")
    media_consumption: List[str] = Field(default_factory=list, description="Media habits")
    
    # Personality hints
    personality_description: Optional[str] = Field(None, description="Describe ideal customer personality")


class MediaPreferences(BaseModel):
    """Optional media channel and content preferences."""
    
    preferred_channels: List[str] = Field(default_factory=list, description="Preferred iHeart channels")
    preferred_shows: List[str] = Field(default_factory=list, description="Preferred shows")
    preferred_dayparts: List[str] = Field(default_factory=list, description="Morning, afternoon, evening, night")
    preferred_genres: List[str] = Field(default_factory=list, description="Music/content genres")
    excluded_content: List[str] = Field(default_factory=list, description="Content to avoid")


class RecommendationRequest(BaseModel):
    """Complete recommendation request."""
    
    request_id: str = Field(default_factory=lambda: f"req_{uuid4().hex[:12]}")
    
    # Required inputs
    brand: BrandInfo
    product: ProductInfo
    
    # Optional inputs
    advertisement: Optional[AdvertisementInfo] = None
    target: Optional[CustomerTarget] = None
    media_preferences: Optional[MediaPreferences] = None
    
    # Request metadata
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# PSYCHOLOGICAL STATE MODELS (THE CORE OF ADAM)
# =============================================================================

class MomentaryState(BaseModel):
    """
    STATE: The listener's psychological state RIGHT NOW.
    
    This changes moment-to-moment based on:
    - What content they're consuming
    - Time of day
    - Context (commuting, working, relaxing)
    - Nonconscious signals
    
    THIS IS WHAT PREDICTS RESPONSE TO ADS.
    """
    
    # Arousal-Valence (emotional state)
    arousal: float = Field(ge=0.0, le=1.0, description="Energy/activation level (0=calm, 1=excited)")
    valence: float = Field(ge=-1.0, le=1.0, description="Emotional tone (-1=negative, +1=positive)")
    
    # Cognitive availability
    cognitive_load: float = Field(ge=0.0, le=1.0, description="Mental bandwidth being used (0=available, 1=overloaded)")
    attention_available: float = Field(ge=0.0, le=1.0, description="Attention available for ads")
    
    # Motivational state
    approach_tendency: float = Field(ge=-1.0, le=1.0, description="Approach vs avoidance orientation")
    processing_fluency: float = Field(ge=0.0, le=1.0, description="Ease of processing new info")
    
    # Regulatory focus (momentary)
    promotion_activated: float = Field(ge=0.0, le=1.0, description="Achievement/aspiration focus")
    prevention_activated: float = Field(ge=0.0, le=1.0, description="Security/vigilance focus")
    
    # Construal level (momentary)
    construal_level: float = Field(ge=0.0, le=1.0, description="Abstract (1) vs concrete (0) thinking")
    
    # What's influencing this state
    state_drivers: List[str] = Field(default_factory=list)
    
    # Inference metadata
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    inference_sources: List[InferenceSource] = Field(default_factory=list)


class StableTraits(BaseModel):
    """
    TRAITS: Enduring psychological characteristics.
    
    These are relatively stable over time and predict:
    - What content resonates
    - Which persuasion mechanisms work
    - Communication style preferences
    
    Inferred from:
    - Music/podcast preferences over time
    - Language patterns (from reviews, if available)
    - Behavioral consistency
    """
    
    # Big Five Personality
    openness: float = Field(ge=0.0, le=1.0, description="Openness to experience")
    conscientiousness: float = Field(ge=0.0, le=1.0, description="Organization, dependability")
    extraversion: float = Field(ge=0.0, le=1.0, description="Sociability, energy")
    agreeableness: float = Field(ge=0.0, le=1.0, description="Cooperation, trust")
    neuroticism: float = Field(ge=0.0, le=1.0, description="Emotional reactivity")
    
    # Regulatory focus (dispositional)
    chronic_promotion: float = Field(ge=0.0, le=1.0, description="Habitual promotion focus")
    chronic_prevention: float = Field(ge=0.0, le=1.0, description="Habitual prevention focus")
    
    # Decision style
    need_for_cognition: float = Field(ge=0.0, le=1.0, description="Enjoys effortful thinking")
    impulsivity: float = Field(ge=0.0, le=1.0, description="Tendency to act quickly")
    
    # What's influencing this inference
    trait_drivers: List[str] = Field(default_factory=list)
    
    # Inference metadata
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    inference_sources: List[InferenceSource] = Field(default_factory=list)
    data_points_used: int = Field(ge=0, default=0)


class InferenceSourceDetail(BaseModel):
    """Detail about a single inference source."""
    
    source: InferenceSource
    signal_name: str
    signal_value: Any
    contribution_weight: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class ListenerInference(BaseModel):
    """
    THE CORE VALUE PROPOSITION: Unknown → Known
    
    This shows HOW we infer who the listener is
    WITHOUT knowing their identity.
    """
    
    # What we're inferring FROM
    listening_context: Dict[str, Any] = Field(default_factory=dict)
    
    # The inferred STATE (momentary)
    current_state: MomentaryState
    
    # The inferred TRAITS (stable)
    personality_traits: StableTraits
    
    # Detailed breakdown of inference sources
    inference_breakdown: List[InferenceSourceDetail] = Field(default_factory=list)
    
    # What mechanisms will work best
    mechanism_susceptibility: Dict[str, float] = Field(default_factory=dict)
    
    # Optimal messaging approach
    recommended_framing: str  # gain vs loss
    recommended_construal: str  # abstract vs concrete
    recommended_processing_route: ProcessingRoute
    
    # The transformation story
    unknown_signals: List[str] = Field(default_factory=list, description="What we observed")
    known_insights: List[str] = Field(default_factory=list, description="What we inferred")
    
    # Confidence and validation
    overall_confidence: float = Field(ge=0.0, le=1.0)
    validation_notes: List[str] = Field(default_factory=list)


# =============================================================================
# OUTPUT MODELS
# =============================================================================

class ChannelRecommendation(BaseModel):
    """Recommended iHeart channel."""
    
    channel_name: str
    channel_format: str
    match_score: float = Field(ge=0.0, le=1.0)
    audience_match: float = Field(ge=0.0, le=1.0)
    psychological_match: float = Field(ge=0.0, le=1.0)
    reasoning: str
    
    # State/trait alignment
    state_alignment: Dict[str, float] = Field(default_factory=dict)
    trait_alignment: Dict[str, float] = Field(default_factory=dict)


class ShowRecommendation(BaseModel):
    """Recommended show within a channel."""
    
    show_name: str
    channel: str
    daypart: str
    match_score: float = Field(ge=0.0, le=1.0)
    audience_demographics: Dict[str, Any] = Field(default_factory=dict)
    reasoning: str
    
    # Expected listener state during this show
    expected_listener_state: Optional[MomentaryState] = None


class StateMimicryAnalysis(BaseModel):
    """Analysis of how the ad mimics the listener's current STATE."""
    
    # What state we're mimicking
    target_arousal: float = Field(ge=0.0, le=1.0, description="Energy level to match")
    target_valence: float = Field(ge=-1.0, le=1.0, description="Emotional tone to match")
    target_cognitive_load: float = Field(ge=0.0, le=1.0, description="Complexity level to match")
    
    # How the ad mimics it
    ad_energy_level: str  # "high", "medium", "low"
    ad_emotional_tone: str  # "uplifting", "calm", "urgent", "neutral"
    ad_complexity: str  # "simple", "moderate", "detailed"
    
    # Flow preservation
    flow_disruption_risk: float = Field(ge=0.0, le=1.0, description="Risk of breaking listener flow")
    seamlessness_score: float = Field(ge=0.0, le=1.0, description="How well ad blends with content")
    
    # Explanation
    mimicry_strategy: str
    why_this_works: str


class TraitAlignmentAnalysis(BaseModel):
    """Analysis of how the ad aligns with stable personality TRAITS."""
    
    # Dominant traits being targeted
    primary_trait: str
    primary_trait_value: float = Field(ge=0.0, le=1.0)
    secondary_trait: str
    secondary_trait_value: float = Field(ge=0.0, le=1.0)
    
    # How we're aligning
    alignment_approach: str
    resonance_points: List[str]
    
    # Explanation
    why_resonates: str


class StateTraitConflictResolution(BaseModel):
    """Analysis when STATE and TRAIT suggest different approaches."""
    
    has_conflict: bool = Field(default=False)
    
    # What's conflicting
    state_suggests: Optional[str] = None
    trait_suggests: Optional[str] = None
    
    # Resolution
    resolution_approach: str
    intensity_modifier: float = Field(ge=0.0, le=1.0, default=1.0, description="1.0 = full, 0.5 = softened")
    
    # Explanation
    resolution_reasoning: str


class AdCopyRecommendation(BaseModel):
    """Recommended advertisement copy with deep psychological justification."""
    
    headline: str
    body: str
    call_to_action: str
    
    # Variants
    promotion_variant: str
    prevention_variant: str
    
    # Framing
    framing_type: str  # gain, loss, neutral
    construal_level: str  # abstract, concrete
    
    # Mechanisms used
    mechanisms_applied: List[str]
    mechanism_justification: Dict[str, str]
    
    # THE KEY ANALYSES (Mimic STATE, Align to TRAIT)
    state_mimicry: Optional[StateMimicryAnalysis] = None
    trait_alignment: Optional[TraitAlignmentAnalysis] = None
    conflict_resolution: Optional[StateTraitConflictResolution] = None
    
    # Flow Preservation
    flow_preservation_score: float = Field(ge=0.0, le=1.0, default=0.8)
    will_feel_like_ad: bool = Field(default=False, description="True if listener will consciously notice it's an ad")
    
    # Deep insight summary
    psychological_strategy: str = Field(default="", description="Summary of psychological approach")


class PredictedOutcome(BaseModel):
    """Predicted performance metrics."""
    
    predicted_ctr: float = Field(ge=0.0, le=1.0)
    predicted_conversion: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Lift estimates
    baseline_ctr: float = Field(ge=0.0, le=1.0)
    psychological_lift: float
    
    # Breakdown
    ctr_by_mechanism: Dict[str, float] = Field(default_factory=dict)
    
    # Why we expect this
    prediction_drivers: List[str] = Field(default_factory=list)


class RegulatoryFocusAnalysis(BaseModel):
    """Regulatory focus analysis for target audience."""
    
    promotion_score: float = Field(ge=0.0, le=1.0)
    prevention_score: float = Field(ge=0.0, le=1.0)
    dominant_focus: str
    
    # Reasoning
    focus_drivers: List[str]
    messaging_implications: List[str]
    
    confidence: float = Field(ge=0.0, le=1.0)


class NonconsciousStateAnalysis(BaseModel):
    """Nonconscious state analysis for target + channel."""
    
    # State estimates
    cognitive_load_estimate: float = Field(ge=0.0, le=1.0)
    approach_tendency: float = Field(ge=-1.0, le=1.0)
    processing_fluency: float = Field(ge=0.0, le=1.0)
    engagement_potential: float = Field(ge=0.0, le=1.0)
    
    # Context factors
    context_factors: List[str]
    
    # Implications
    implications: List[str]


class PersonalityAnalysis(BaseModel):
    """Big Five personality analysis for target audience."""
    
    # Inferred Big Five
    openness: float = Field(ge=0.0, le=1.0)
    conscientiousness: float = Field(ge=0.0, le=1.0)
    extraversion: float = Field(ge=0.0, le=1.0)
    agreeableness: float = Field(ge=0.0, le=1.0)
    neuroticism: float = Field(ge=0.0, le=1.0)
    
    # Trait implications
    trait_implications: Dict[str, str]
    
    # Channel-based modulation
    channel_modulation: str
    
    confidence: float = Field(ge=0.0, le=1.0)


class ReasoningTrace(BaseModel):
    """Complete reasoning and validation trace."""
    
    steps: List[str]
    atoms_executed: List[str]
    evidence_sources: List[str]
    conflicts_detected: List[str]
    resolution_method: str


class RecommendationResponse(BaseModel):
    """Complete recommendation response."""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    request_id: str
    response_id: str = Field(default_factory=lambda: f"resp_{uuid4().hex[:12]}")
    
    # THE KEY OUTPUT: Listener Inference
    listener_inference: Optional[ListenerInference] = None
    
    # Channel & Show Recommendations
    recommended_channels: List[ChannelRecommendation]
    recommended_shows: List[ShowRecommendation]
    
    # Ad Copy
    ad_copy_recommendation: AdCopyRecommendation
    
    # Predicted Outcomes
    predicted_outcome: PredictedOutcome
    
    # Model Justification
    regulatory_focus: RegulatoryFocusAnalysis
    nonconscious_state: NonconsciousStateAnalysis
    personality_analysis: PersonalityAnalysis
    reasoning_trace: ReasoningTrace
    
    # Metadata
    processing_time_ms: int = Field(ge=0)
    model_version: str = Field(default="ADAM v1.0")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # PLATFORM STATUS (Real vs Simulated components)
    platform_status: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Status of platform component usage (real vs simulated)"
    )
    using_real_platform: bool = Field(
        default=False,
        description="Whether any real platform components were used"
    )
    real_components_used: List[str] = Field(
        default_factory=list,
        description="List of real platform components that were used"
    )


# =============================================================================
# DASHBOARD STATE
# =============================================================================

class DashboardState(BaseModel):
    """Current state of the demo dashboard."""
    
    # Current request (if any)
    current_request: Optional[RecommendationRequest] = None
    
    # Current recommendation (if any)
    current_recommendation: Optional[RecommendationResponse] = None
    
    # History
    request_history: List[RecommendationRequest] = Field(default_factory=list)
    recommendation_history: List[RecommendationResponse] = Field(default_factory=list)
    
    # Stats
    total_recommendations: int = Field(ge=0, default=0)
    avg_processing_time_ms: float = Field(ge=0.0, default=0.0)


# =============================================================================
# iHEART CHANNEL DATA
# =============================================================================

class iHeartChannel(BaseModel):
    """iHeart channel with psychological profile."""
    
    name: str
    format: str
    description: str
    
    # Audience demographics (for context, not primary)
    primary_age: str
    gender_skew: str
    income_profile: str
    
    # PSYCHOLOGICAL PROFILES (the real value)
    # What listening to this channel DOES to your state
    state_induction: Dict[str, float] = Field(default_factory=dict)
    # What traits people who prefer this channel have
    trait_profile: Dict[str, float] = Field(default_factory=dict)
    # Legacy name for compatibility
    big_five_profile: Dict[str, float] = Field(default_factory=dict)
    regulatory_focus: Dict[str, float] = Field(default_factory=dict)
    
    # Programming
    sample_shows: List[str]
    peak_dayparts: List[str]


# Pre-defined iHeart channels with PSYCHOLOGICAL profiles
IHEART_CHANNELS = [
    iHeartChannel(
        name="Z100 (WHTZ)",
        format="CHR (Contemporary Hit Radio)",
        description="Top 40 hits targeting young, trend-conscious listeners",
        primary_age="18-34",
        gender_skew="Female 55%",
        income_profile="Middle to Upper-Middle",
        # STATE INDUCTION: What this music does to listeners
        state_induction={
            "arousal": 0.75,           # High energy music
            "valence": 0.70,           # Positive mood
            "approach_tendency": 0.65,  # Approach-oriented
            "processing_fluency": 0.70, # Familiar, easy to process
            "promotion_activated": 0.75, # Achievement, aspiration
            "cognitive_load": 0.35,     # Low cognitive demand
        },
        # TRAIT PROFILE: Who chooses this station
        trait_profile={
            "openness": 0.65,
            "conscientiousness": 0.45,
            "extraversion": 0.75,
            "agreeableness": 0.60,
            "neuroticism": 0.50,
            "need_for_cognition": 0.40,
            "impulsivity": 0.60,
        },
        big_five_profile={
            "openness": 0.65,
            "conscientiousness": 0.45,
            "extraversion": 0.75,
            "agreeableness": 0.60,
            "neuroticism": 0.50
        },
        regulatory_focus={"promotion": 0.75, "prevention": 0.35},
        sample_shows=["Elvis Duran Morning Show", "On Air with Ryan Seacrest"],
        peak_dayparts=["Morning Drive", "Afternoon Drive"]
    ),
    iHeartChannel(
        name="LITE FM (WLTW)",
        format="Hot AC (Adult Contemporary)",
        description="Soft hits for working professionals",
        primary_age="25-54",
        gender_skew="Female 60%",
        income_profile="Upper-Middle",
        state_induction={
            "arousal": 0.45,
            "valence": 0.60,
            "approach_tendency": 0.40,
            "processing_fluency": 0.80,
            "promotion_activated": 0.50,
            "cognitive_load": 0.25,
        },
        trait_profile={
            "openness": 0.55,
            "conscientiousness": 0.65,
            "extraversion": 0.50,
            "agreeableness": 0.70,
            "neuroticism": 0.45,
            "need_for_cognition": 0.55,
            "impulsivity": 0.35,
        },
        big_five_profile={
            "openness": 0.55,
            "conscientiousness": 0.65,
            "extraversion": 0.50,
            "agreeableness": 0.70,
            "neuroticism": 0.45
        },
        regulatory_focus={"promotion": 0.55, "prevention": 0.55},
        sample_shows=["Valentine in the Morning", "Delilah After Dark"],
        peak_dayparts=["Morning Drive", "Evening"]
    ),
    iHeartChannel(
        name="WKTU",
        format="Rhythmic CHR / Dance",
        description="Dance, EDM, and rhythmic hits for party-oriented listeners",
        primary_age="18-34",
        gender_skew="Balanced",
        income_profile="Middle",
        state_induction={
            "arousal": 0.85,
            "valence": 0.75,
            "approach_tendency": 0.80,
            "processing_fluency": 0.65,
            "promotion_activated": 0.85,
            "cognitive_load": 0.30,
        },
        trait_profile={
            "openness": 0.75,
            "conscientiousness": 0.40,
            "extraversion": 0.85,
            "agreeableness": 0.55,
            "neuroticism": 0.45,
            "need_for_cognition": 0.35,
            "impulsivity": 0.70,
        },
        big_five_profile={
            "openness": 0.75,
            "conscientiousness": 0.40,
            "extraversion": 0.85,
            "agreeableness": 0.55,
            "neuroticism": 0.45
        },
        regulatory_focus={"promotion": 0.80, "prevention": 0.25},
        sample_shows=["KTU Dance Party", "Club KTU"],
        peak_dayparts=["Evening", "Night"]
    ),
    iHeartChannel(
        name="WINS (1010 WINS)",
        format="News / Talk",
        description="24-hour news for informed, busy professionals",
        primary_age="35-64",
        gender_skew="Male 55%",
        income_profile="Upper-Middle to High",
        state_induction={
            "arousal": 0.55,
            "valence": 0.35,           # News often negative
            "approach_tendency": 0.30,
            "processing_fluency": 0.50,
            "promotion_activated": 0.35,
            "cognitive_load": 0.70,    # News requires processing
        },
        trait_profile={
            "openness": 0.60,
            "conscientiousness": 0.80,
            "extraversion": 0.45,
            "agreeableness": 0.50,
            "neuroticism": 0.55,
            "need_for_cognition": 0.80,
            "impulsivity": 0.25,
        },
        big_five_profile={
            "openness": 0.60,
            "conscientiousness": 0.80,
            "extraversion": 0.45,
            "agreeableness": 0.50,
            "neuroticism": 0.55
        },
        regulatory_focus={"promotion": 0.40, "prevention": 0.70},
        sample_shows=["News on the Hour", "Business Updates"],
        peak_dayparts=["Morning Drive", "Afternoon Drive"]
    ),
    iHeartChannel(
        name="Q104.3",
        format="Classic Rock",
        description="Classic rock for nostalgic, established adults",
        primary_age="35-54",
        gender_skew="Male 60%",
        income_profile="Middle to Upper-Middle",
        state_induction={
            "arousal": 0.60,
            "valence": 0.55,
            "approach_tendency": 0.45,
            "processing_fluency": 0.85,  # Highly familiar music
            "promotion_activated": 0.45,
            "cognitive_load": 0.20,
        },
        trait_profile={
            "openness": 0.55,
            "conscientiousness": 0.55,
            "extraversion": 0.55,
            "agreeableness": 0.50,
            "neuroticism": 0.45,
            "need_for_cognition": 0.50,
            "impulsivity": 0.40,
        },
        big_five_profile={
            "openness": 0.55,
            "conscientiousness": 0.55,
            "extraversion": 0.55,
            "agreeableness": 0.50,
            "neuroticism": 0.45
        },
        regulatory_focus={"promotion": 0.50, "prevention": 0.55},
        sample_shows=["Jim Kerr Rock & Roll Morning Show", "Coop After Dark"],
        peak_dayparts=["Morning Drive", "Evening"]
    ),
    iHeartChannel(
        name="Power 105.1",
        format="Urban / Hip-Hop",
        description="Hip-hop and R&B for urban, trend-setting listeners",
        primary_age="18-44",
        gender_skew="Male 52%",
        income_profile="Middle",
        state_induction={
            "arousal": 0.75,
            "valence": 0.65,
            "approach_tendency": 0.70,
            "processing_fluency": 0.60,
            "promotion_activated": 0.75,
            "cognitive_load": 0.35,
        },
        trait_profile={
            "openness": 0.70,
            "conscientiousness": 0.45,
            "extraversion": 0.75,
            "agreeableness": 0.50,
            "neuroticism": 0.50,
            "need_for_cognition": 0.45,
            "impulsivity": 0.55,
        },
        big_five_profile={
            "openness": 0.70,
            "conscientiousness": 0.45,
            "extraversion": 0.75,
            "agreeableness": 0.50,
            "neuroticism": 0.50
        },
        regulatory_focus={"promotion": 0.70, "prevention": 0.35},
        sample_shows=["The Breakfast Club", "DJ Envy's Party"],
        peak_dayparts=["Morning Drive", "Evening"]
    ),
    iHeartChannel(
        name="WFAN",
        format="Sports",
        description="24-hour sports talk for passionate fans",
        primary_age="25-54",
        gender_skew="Male 75%",
        income_profile="Middle to Upper-Middle",
        state_induction={
            "arousal": 0.70,
            "valence": 0.50,  # Highly variable based on team performance
            "approach_tendency": 0.55,
            "processing_fluency": 0.55,
            "promotion_activated": 0.60,
            "cognitive_load": 0.55,
        },
        trait_profile={
            "openness": 0.50,
            "conscientiousness": 0.60,
            "extraversion": 0.65,
            "agreeableness": 0.45,
            "neuroticism": 0.55,
            "need_for_cognition": 0.55,
            "impulsivity": 0.50,
        },
        big_five_profile={
            "openness": 0.50,
            "conscientiousness": 0.60,
            "extraversion": 0.65,
            "agreeableness": 0.45,
            "neuroticism": 0.55
        },
        regulatory_focus={"promotion": 0.55, "prevention": 0.50},
        sample_shows=["Boomer & Gio", "Carton & Roberts"],
        peak_dayparts=["Morning Drive", "Afternoon Drive", "Game Time"]
    ),
    iHeartChannel(
        name="Country 94.7",
        format="Country",
        description="Country music for tradition-oriented listeners",
        primary_age="25-54",
        gender_skew="Female 55%",
        income_profile="Middle",
        state_induction={
            "arousal": 0.50,
            "valence": 0.60,
            "approach_tendency": 0.45,
            "processing_fluency": 0.80,
            "promotion_activated": 0.40,
            "cognitive_load": 0.25,
        },
        trait_profile={
            "openness": 0.45,
            "conscientiousness": 0.65,
            "extraversion": 0.55,
            "agreeableness": 0.70,
            "neuroticism": 0.45,
            "need_for_cognition": 0.45,
            "impulsivity": 0.35,
        },
        big_five_profile={
            "openness": 0.45,
            "conscientiousness": 0.65,
            "extraversion": 0.55,
            "agreeableness": 0.70,
            "neuroticism": 0.45
        },
        regulatory_focus={"promotion": 0.45, "prevention": 0.60},
        sample_shows=["Nash Nights Live", "Country Countdown"],
        peak_dayparts=["Morning Drive", "Evening"]
    ),
]
