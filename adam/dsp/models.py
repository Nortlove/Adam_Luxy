"""
DSP Enrichment Engine — Models & Data Structures
=================================================

All enums and dataclasses for the DSP enrichment pipeline, extended with
constructs from the full ADAM platform (atoms, intelligence modules, review
extractors, NDF dimensions, and 82 psychological frameworks).

Sections:
    1. Enumerations (reasoning, confidence, domains, mechanisms, signals, etc.)
    2. Core data structures (effect sizes, signals, temporal, creative)
    3. ImpressionContext — DSP input layer
    4. PsychologicalStateVector — inferred consumer state (50+ dimensions)
    5. PersuasionStrategy — complete output space
    6. InventoryEnrichmentScore — CPM premium justification
"""

from __future__ import annotations
import math
import time
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# SECTION 1: ENUMERATIONS
# =============================================================================

class ReasoningType(Enum):
    """Types of inferential reasoning encoded in graph edges."""
    CAUSAL = "causal"
    MEDIATIONAL = "mediational"
    MODERATIONAL = "moderational"
    THRESHOLD = "threshold"
    BIDIRECTIONAL = "bidirectional"
    TEMPORAL = "temporal"
    CONDITIONAL = "conditional"
    INHIBITORY = "inhibitory"
    COMPENSATORY = "compensatory"
    SYNERGISTIC = "synergistic"
    CONTEXTUAL_MODERATION = "contextual_moderation"
    TEMPORAL_INTERACTION = "temporal_interaction"
    SIGNAL_FUSION = "signal_fusion"
    PRECISION_WEIGHTED = "precision_weighted"
    ACTIVE_INFERENCE = "active_inference"
    CORRELATIONAL = "correlational"
    ETHICAL_BOUNDARY = "ethical_boundary"
    # --- ADAM extensions ---
    CREATES_NEED = "creates_need"
    SATISFIED_BY = "satisfied_by"
    ACTIVATES_ROUTE = "activates_route"
    REQUIRES_QUALITY = "requires_quality"
    MODERATES = "moderates"
    ANTAGONISTIC = "antagonistic"
    COOPERATIVE = "cooperative"


class ConfidenceLevel(Enum):
    """Evidence quality tiers with numeric weights for scoring."""
    META_ANALYTIC = "meta_analytic"
    REPLICATED = "replicated"
    HIGH = "high"
    MODERATE = "moderate"
    SINGLE_STUDY = "single_study"
    THEORETICAL = "theoretical"
    EXPERT_CONSENSUS = "expert_consensus"
    FIELD_VALIDATED = "field_validated"
    AB_CONFIRMED = "ab_confirmed"
    CROSS_VALIDATED = "cross_validated"
    # --- ADAM extensions ---
    INGESTION_DERIVED = "ingestion_derived"
    REVIEW_MINED = "review_mined"
    ATOM_INFERRED = "atom_inferred"

    @property
    def numeric_weight(self) -> float:
        weights = {
            "meta_analytic": 0.95, "replicated": 0.85, "high": 0.80,
            "field_validated": 0.82, "ab_confirmed": 0.80, "cross_validated": 0.78,
            "moderate": 0.65, "single_study": 0.60,
            "expert_consensus": 0.50, "theoretical": 0.35,
            "ingestion_derived": 0.70, "review_mined": 0.65,
            "atom_inferred": 0.55,
        }
        return weights.get(self.value, 0.5)


class PsychologicalDomain(Enum):
    """Expanded domain taxonomy — DSP engine 34 domains + ADAM extensions."""
    PERSONALITY = "personality"
    MOTIVATION = "motivation"
    EMOTION = "emotion"
    COGNITION = "cognition"
    SOCIAL = "social"
    DECISION_MAKING = "decision_making"
    PERSUASION = "persuasion"
    ATTITUDE = "attitude"
    MEMORY = "memory"
    ATTENTION = "attention"
    VALUES = "values"
    IDENTITY = "identity"
    SELF_REGULATION = "self_regulation"
    MORAL_PSYCHOLOGY = "moral_psychology"
    EVOLUTIONARY = "evolutionary"
    CULTURAL = "cultural"
    DEVELOPMENTAL = "developmental"
    NEUROSCIENCE = "neuroscience"
    BEHAVIORAL_ECONOMICS = "behavioral_economics"
    CONSUMER_BEHAVIOR = "consumer_behavior"
    COGNITIVE_LOAD = "cognitive_load"
    PREDICTIVE_PROCESSING = "predictive_processing"
    EMBODIED_COGNITION = "embodied_cognition"
    IMPLICIT_COGNITION = "implicit_cognition"
    AFFECT_REGULATION = "affect_regulation"
    INTEROCEPTION = "interoception"
    SOCIAL_IDENTITY = "social_identity"
    DECISION_ARCHITECTURE = "decision_architecture"
    ATTENTION_SCIENCE = "attention_science"
    CREATIVE_PSYCHOLOGY = "creative_psychology"
    CONTEXTUAL_PSYCHOLOGY = "contextual_psychology"
    TEMPORAL_PSYCHOLOGY = "temporal_psychology"
    COGNITIVE_PROCESSING = "cognitive_processing"
    EVOLUTIONARY_PSYCHOLOGY = "evolutionary_psychology"
    # --- ADAM platform extensions ---
    NONCONSCIOUS_DECISION = "nonconscious_decision"
    PSYCHOLINGUISTICS = "psycholinguistics"
    NARRATIVE_PSYCHOLOGY = "narrative_psychology"
    TRUST_CREDIBILITY = "trust_credibility"
    PRICE_VALUE_PSYCHOLOGY = "price_value_psychology"
    BRAND_PSYCHOLOGY = "brand_psychology"
    VULNERABILITY = "vulnerability"
    COOPERATIVE_FRAMING = "cooperative_framing"
    INFORMATION_ASYMMETRY = "information_asymmetry"
    REGRET_THEORY = "regret_theory"
    MOTIVATIONAL_CONFLICT = "motivational_conflict"
    MIMETIC_THEORY = "mimetic_theory"
    SIGNAL_THEORY = "signal_theory"
    ATTACHMENT_THEORY = "attachment_theory"
    CIRCADIAN_PSYCHOLOGY = "circadian_psychology"


class MechanismType(Enum):
    """
    All psychological mechanisms — merged from:
    - DSP engine (108 mechanisms)
    - ADAM core 9 mechanisms
    - ADAM 82 frameworks
    - ADAM atom-specific mechanisms
    - Cialdini principles (18 sub-techniques)
    """
    # --- Cialdini Principles ---
    SOCIAL_PROOF = "social_proof"
    SCARCITY = "scarcity"
    RECIPROCITY = "reciprocity"
    COMMITMENT_CONSISTENCY = "commitment_consistency"
    AUTHORITY = "authority"
    LIKING = "liking"
    UNITY = "unity"

    # --- ADAM Core 9 ---
    TEMPORAL_CONSTRUAL = "temporal_construal"
    REGULATORY_FOCUS = "regulatory_focus"
    IDENTITY_CONSTRUCTION = "identity_construction"
    MIMETIC_DESIRE = "mimetic_desire"
    ATTENTION_DYNAMICS = "attention_dynamics"
    EMBODIED_COGNITION_MECHANISM = "embodied_cognition"
    ANCHORING = "anchoring"
    AUTOMATIC_EVALUATION = "automatic_evaluation"
    WANTING_LIKING = "wanting_liking"

    # --- Cognitive Persuasion ---
    PRIMING = "priming"
    FRAMING = "framing"
    ELABORATION = "elaboration"
    HEURISTIC_PROCESSING = "heuristic_processing"
    AFFECT_TRANSFER = "affect_transfer"
    COGNITIVE_DISSONANCE = "cognitive_dissonance"
    SELF_PERCEPTION = "self_perception"
    MERE_EXPOSURE = "mere_exposure"
    CLASSICAL_CONDITIONING = "classical_conditioning"
    OPERANT_CONDITIONING = "operant_conditioning"
    NARRATIVE_TRANSPORTATION = "narrative_transportation"
    REGULATORY_FIT = "regulatory_fit"
    CONSTRUAL_MATCHING = "construal_matching"
    PROCESSING_FLUENCY = "processing_fluency"

    # --- Behavioral Economics ---
    ENDOWMENT_EFFECT = "endowment_effect"
    LOSS_AVERSION = "loss_aversion"
    STATUS_QUO_BIAS = "status_quo_bias"
    DEFAULT_EFFECT = "default_effect"
    DECOY_EFFECT = "decoy_effect"
    MENTAL_ACCOUNTING = "mental_accounting"
    HYPERBOLIC_DISCOUNTING = "hyperbolic_discounting"
    PEAK_END_RULE = "peak_end_rule"
    SPACING_EFFECT = "spacing_effect"
    TESTING_EFFECT = "testing_effect"
    GENERATION_EFFECT = "generation_effect"
    SUNK_COST = "sunk_cost"

    # --- Motivational ---
    APPROACH_AVOIDANCE = "approach_avoidance"
    PSYCHOLOGICAL_OWNERSHIP = "psychological_ownership"
    CURIOSITY_GAP = "curiosity_gap"
    PREDICTION_ERROR = "prediction_error"
    DOPAMINERGIC_WANTING = "dopaminergic_wanting"

    # --- Moral / Identity ---
    MORAL_LICENSING = "moral_licensing"
    MORAL_CLEANSING = "moral_cleansing"
    COSTLY_SIGNALING = "costly_signaling"
    IDENTITY_ACTIVATION = "identity_activation"
    REACTANCE = "reactance"

    # --- Emotional ---
    FEAR_APPEAL = "fear_appeal"
    HUMOR_PROCESSING = "humor_processing"
    NOSTALGIA_ACTIVATION = "nostalgia_activation"
    GRATITUDE_RECIPROCITY = "gratitude_reciprocity"
    AWE_SMALL_SELF = "awe_small_self"
    ELEVATION_PROSOCIAL = "elevation_prosocial"
    EMOTIONAL_CONTAGION = "emotional_contagion"
    MOOD_CONGRUENCY = "mood_congruency"
    MOOD_REPAIR = "mood_repair"
    AFFECT_AS_INFORMATION = "affect_as_information"
    SOMATIC_MARKER = "somatic_marker"

    # --- Temporal / Circadian ---
    CIRCADIAN_MODULATION = "circadian_modulation"
    DECISION_FATIGUE = "decision_fatigue"
    VIGILANCE_DECREMENT = "vigilance_decrement"
    CHRONOTYPE_INTERACTION = "chronotype_interaction"
    SLEEP_DEPRIVATION = "sleep_deprivation"

    # --- Attention / Cognitive ---
    MIND_WANDERING = "mind_wandering"
    ATTENTION_CAPTURE = "attention_capture"
    INHIBITION_FAILURE = "inhibition_failure"
    COGNITIVE_DEPLETION = "cognitive_depletion"
    DUAL_PROCESS_SHIFT = "dual_process_shift"
    PERCEPTUAL_FLUENCY = "perceptual_fluency"
    CONCEPTUAL_FLUENCY = "conceptual_fluency"
    METACOGNITIVE_EXPERIENCE = "metacognitive_experience"
    COGNITIVE_ABSORPTION = "cognitive_absorption"
    FLOW_STATE = "flow_state"

    # --- Dual Process / Learning ---
    SYSTEM1_DOMINANCE = "system1_dominance"
    SYSTEM2_ENGAGEMENT = "system2_engagement"
    MODEL_FREE_HABIT = "model_free_habit"
    MODEL_BASED_PLANNING = "model_based_planning"
    PREDICTION_ERROR_LEARNING = "prediction_error_learning"
    BAYESIAN_UPDATING = "bayesian_updating"
    ACTIVE_INFERENCE_MECHANISM = "active_inference"

    # --- Information Processing ---
    INFORMATION_AVOIDANCE = "information_avoidance"
    CONFIRMATION_SEEKING = "confirmation_seeking"
    UNCERTAINTY_REDUCTION = "uncertainty_reduction"
    OPTIMAL_AROUSAL = "optimal_arousal"
    ILLUSORY_TRUTH = "illusory_truth"
    AVAILABILITY_HEURISTIC = "availability_heuristic"
    REPRESENTATIVENESS = "representativeness"
    RECOGNITION_HEURISTIC = "recognition_heuristic"

    # --- Decision Strategy ---
    CHOICE_OVERLOAD = "choice_overload"
    SATISFICING = "satisficing"
    MAXIMIZING = "maximizing"

    # --- Composite / Alias ---
    CONSTRUAL_FIT = "construal_fit"
    ELABORATION_LIKELIHOOD = "elaboration_likelihood"
    COGNITIVE_LOAD_DEPLETION = "cognitive_load_depletion"
    ATTENTION_COMPETITION = "attention_competition"
    AROUSAL_REGULATION = "arousal_regulation"
    COGNITIVE_BIAS_EXPLOITATION = "cognitive_bias_exploitation"
    TRAIT_MATCHING = "trait_matching"
    STATUS_SIGNALING = "status_signaling"
    DUAL_PROCESS = "dual_process"
    EGO_DEPLETION = "ego_depletion"
    HABIT_FORMATION = "habit_formation"
    IMPLICIT_LEARNING = "implicit_learning"
    MEMORY_ENCODING = "memory_encoding"
    DECISION_CONFLICT = "decision_conflict"
    TEMPORAL_DISCOUNTING = "temporal_discounting"
    INFORMATION_GAP = "information_gap"
    CONFIRMATION_BIAS = "confirmation_bias"
    PSYCHOLOGICAL_REACTANCE = "psychological_reactance"
    ETHICAL_OVERRIDE = "ethical_override"

    # --- ADAM Platform Atom-Specific ---
    STORYTELLING = "storytelling"
    EVOLUTIONARY_ADAPTATIONS = "evolutionary_adaptations"
    URGENCY = "urgency"
    FOMO = "fomo"
    NOVELTY = "novelty"
    INVESTMENT_FRAMING = "investment_framing"
    INSTANT_GRATIFICATION = "instant_gratification"
    BELONGING = "belonging"
    COMMUNITY = "community"
    EXCLUSIVITY = "exclusivity"
    RELATABILITY = "relatability"

    # --- ADAM Framework 41-82 Extensions ---
    STATE_TRAIT_INTERACTION = "state_trait_interaction"
    AROUSAL_MODULATION = "arousal_modulation"
    CIRCADIAN_PATTERNS = "circadian_patterns"
    JOURNEY_STAGE = "journey_stage"
    MICRO_TEMPORAL_PATTERNS = "micro_temporal_patterns"
    CROSS_CATEGORY_BEHAVIOR = "cross_category_behavior"
    CONTENT_CONSUMPTION_PATTERNS = "content_consumption_patterns"
    PHYSIOLOGICAL_PROXIES = "physiological_proxies"
    INTERACTION_SEQUENCING = "interaction_sequencing"
    BRAND_PERSONALITY_MATCHING = "brand_personality_matching"
    BRAND_SELF_CONGRUITY = "brand_self_congruity"
    MORAL_FOUNDATIONS_ACTIVATION = "moral_foundations_activation"
    SCHWARTZ_VALUES_ACTIVATION = "schwartz_values_activation"
    ELABORATIVE_ENCODING = "elaborative_encoding"
    MEANING_MAKING = "meaning_making"
    HEROS_JOURNEY = "heros_journey"
    SOURCE_CREDIBILITY = "source_credibility"
    EVIDENCE_ELABORATION = "evidence_elaboration"
    NEGATIVITY_BIAS = "negativity_bias"
    REFERENCE_PRICE = "reference_price"
    PAIN_OF_PAYING = "pain_of_paying"
    MECHANISM_SYNERGY = "mechanism_synergy"
    MECHANISM_INTERFERENCE = "mechanism_interference"
    MECHANISM_SEQUENCING = "mechanism_sequencing"
    RESOURCE_DEPLETION = "resource_depletion"
    CULTURAL_SELF_CONSTRUAL = "cultural_self_construal"
    POWER_DISTANCE = "power_distance"
    UNCERTAINTY_AVOIDANCE_CULTURAL = "uncertainty_avoidance_cultural"
    VULNERABILITY_DETECTION = "vulnerability_detection"
    MANIPULATION_BOUNDARY = "manipulation_boundary"
    IDENTITY_THREAT = "identity_threat"
    COUNTERFACTUAL_REASONING = "counterfactual_reasoning"
    TRANSFER_LEARNING_ARCHETYPES = "transfer_learning_archetypes"
    CONFIDENCE_CALIBRATION = "confidence_calibration"


class SignalSource(Enum):
    """Where behavioral signals originate in the DSP bidstream."""
    MOUSE_CURSOR = "mouse_cursor"
    TOUCH_INTERACTION = "touch_interaction"
    SCROLL_BEHAVIOR = "scroll_behavior"
    TEMPORAL_PATTERN = "temporal_pattern"
    CONTENT_CONTEXT = "content_context"
    NAVIGATION_PATTERN = "navigation_pattern"
    DWELL_TIME = "dwell_time"
    DEVICE_SENSOR = "device_sensor"
    SOCIAL_REFERRAL = "social_referral"
    LINGUISTIC_SIGNAL = "linguistic_signal"
    NON_ACTION = "non_action"
    PUBLISHER_FIRST_PARTY = "publisher_first_party"
    AD_OPPORTUNITY = "ad_opportunity"
    ENVIRONMENTAL = "environmental"
    # --- ADAM extensions ---
    REVIEW_BEHAVIOR = "review_behavior"
    PURCHASE_HISTORY = "purchase_history"
    SEARCH_PATTERN = "search_pattern"
    SESSION_ANALYTICS = "session_analytics"


class SignalReliability(Enum):
    """Reliability tiers for behavioral signals with scoring weights."""
    TIER_1_VALIDATED = "tier_1_validated"
    TIER_2_REPLICATED = "tier_2_replicated"
    TIER_3_EMERGING = "tier_3_emerging"
    TIER_4_THEORETICAL = "tier_4_theoretical"
    TIER_5_EXPERIMENTAL = "tier_5_experimental"

    @property
    def weight(self) -> float:
        return {
            "tier_1_validated": 1.0, "tier_2_replicated": 0.8,
            "tier_3_emerging": 0.6, "tier_4_theoretical": 0.4,
            "tier_5_experimental": 0.2,
        }.get(self.value, 0.5)


class DeviceType(Enum):
    DESKTOP = "desktop"
    MOBILE = "mobile"
    TABLET = "tablet"
    SMART_TV = "smart_tv"
    WEARABLE = "wearable"
    CONNECTED_TV = "connected_tv"
    DIGITAL_OOH = "digital_ooh"


class ContentCategory(Enum):
    NEWS = "news"
    FINANCE = "finance"
    ENTERTAINMENT = "entertainment"
    SPORTS = "sports"
    HEALTH = "health"
    TECHNOLOGY = "technology"
    LIFESTYLE = "lifestyle"
    FOOD = "food"
    TRAVEL = "travel"
    EDUCATION = "education"
    SHOPPING = "shopping"
    AUTOMOTIVE = "automotive"
    REAL_ESTATE = "real_estate"
    GAMING = "gaming"
    PARENTING = "parenting"
    FASHION = "fashion"
    HOME_GARDEN = "home_garden"
    SCIENCE = "science"
    POLITICS = "politics"
    BUSINESS = "business"
    # --- ADAM extensions (iHeart content types) ---
    RADIO_TALK = "radio_talk"
    RADIO_MUSIC = "radio_music"
    PODCAST = "podcast"
    AUDIO_STREAMING = "audio_streaming"


class FunnelStage(Enum):
    UNAWARE = "unaware"
    AWARENESS = "awareness"
    CONSIDERATION = "consideration"
    EVALUATION = "evaluation"
    INTENT = "intent"
    PURCHASE = "purchase"
    POST_PURCHASE = "post_purchase"
    ADVOCACY = "advocacy"


class SessionPhase(Enum):
    EARLY = "early"
    MIDDLE = "middle"
    EXTENDED = "extended"
    DEEP = "deep"
    RETURNING = "returning"


class CreativeFormat(Enum):
    DISPLAY_BANNER = "display_banner"
    NATIVE_IN_FEED = "native_in_feed"
    VIDEO_PRE_ROLL = "video_pre_roll"
    VIDEO_MID_ROLL = "video_mid_roll"
    VIDEO_OUT_STREAM = "video_out_stream"
    RICH_MEDIA = "rich_media"
    INTERSTITIAL = "interstitial"
    AUDIO_PRE_ROLL = "audio_pre_roll"
    AUDIO_MID_ROLL = "audio_mid_roll"
    REWARDED_VIDEO = "rewarded_video"
    CONNECTED_TV = "connected_tv"
    DIGITAL_OOH = "digital_ooh"
    INTERACTIVE = "interactive"
    SHOPPABLE = "shoppable"
    DISPLAY_STANDARD = "display_standard"
    NATIVE = "native"
    VIDEO = "video"
    SOCIAL_PROOF_OVERLAY = "social_proof_overlay"


class PersuasionRoute(Enum):
    CENTRAL = "central"
    PERIPHERAL = "peripheral"
    EMOTIONAL = "emotional"
    SOCIAL = "social"
    NARRATIVE = "narrative"
    EXPERIENTIAL = "experiential"
    MIXED = "mixed"
    INFORMATIONAL = "informational"
    AUTOMATIC = "automatic"


class EmotionalVehicle(Enum):
    HUMOR = "humor"
    FEAR = "fear"
    NOSTALGIA = "nostalgia"
    AWE = "awe"
    GRATITUDE = "gratitude"
    PRIDE = "pride"
    EXCITEMENT = "excitement"
    WARMTH = "warmth"
    CURIOSITY = "curiosity"
    SURPRISE = "surprise"
    HOPE = "hope"
    EMPATHY = "empathy"
    ELEVATION = "elevation"
    ANTICIPATION = "anticipation"
    RELIEF = "relief"
    NEUTRAL = "neutral"
    ASPIRATION = "aspiration"
    BELONGING = "belonging"
    TRUST = "trust"


class VulnerabilityType(Enum):
    """Types of consumer vulnerability requiring ethical protection."""
    COGNITIVE_DEPLETION = "cognitive_depletion"
    EMOTIONAL_DISTRESS = "emotional_distress"
    FINANCIAL_STRESS = "financial_stress"
    HEALTH_ANXIETY = "health_anxiety"
    LONELINESS = "loneliness"
    SLEEP_DEPRIVATION = "sleep_deprivation"
    DECISION_FATIGUE = "decision_fatigue"
    GRIEF = "grief"
    ADDICTION_SUSCEPTIBILITY = "addiction_susceptibility"
    MINOR_DETECTED = "minor_detected"


# =============================================================================
# SECTION 2: CORE DATA STRUCTURES
# =============================================================================

@dataclass
class EffectSize:
    """Enhanced effect size with heterogeneity and replication metadata."""
    metric: str  # "cohens_d", "r", "odds_ratio", "eta_squared", "g", "beta", "auc"
    value: float
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    n: Optional[int] = None
    k: Optional[int] = None
    p_value: Optional[float] = None
    heterogeneity_i2: Optional[float] = None
    context: str = ""

    @property
    def magnitude_label(self) -> str:
        abs_v = abs(self.value)
        if self.metric in ("cohens_d", "g"):
            if abs_v < 0.2: return "negligible"
            if abs_v < 0.5: return "small"
            if abs_v < 0.8: return "medium"
            return "large"
        elif self.metric == "r":
            if abs_v < 0.1: return "negligible"
            if abs_v < 0.3: return "small"
            if abs_v < 0.5: return "medium"
            return "large"
        elif self.metric == "odds_ratio":
            if abs_v < 1.5: return "small"
            if abs_v < 3.0: return "medium"
            return "large"
        return "unclassified"


@dataclass
class BehavioralSignal:
    """Maps an observable behavioral signal to psychological constructs."""
    signal_id: str
    name: str
    source: SignalSource
    reliability: SignalReliability
    psychological_construct_ids: List[str]
    extraction_method: str
    effect_sizes: List[EffectSize] = field(default_factory=list)
    device_specific: Optional[DeviceType] = None
    latency_budget_ms: int = 50
    validated_accuracy: Optional[float] = None
    min_observations: int = 1
    description: str = ""
    citations: List[str] = field(default_factory=list)


@dataclass
class TemporalModulation:
    """How time-of-day, chronotype, and session phase modulate an edge."""
    circadian_peak_hours: List[int] = field(default_factory=list)
    circadian_trough_hours: List[int] = field(default_factory=list)
    chronotype_interaction: str = ""
    session_phase_modulation: Dict[str, float] = field(default_factory=dict)
    day_of_week_effect: str = ""
    seasonal_modulation: str = ""


@dataclass
class CreativeImplication:
    """Translates a psychological state into creative execution recommendation."""
    recommended_formats: List[CreativeFormat] = field(default_factory=list)
    persuasion_route: PersuasionRoute = PersuasionRoute.MIXED
    emotional_vehicle: EmotionalVehicle = EmotionalVehicle.NEUTRAL
    copy_characteristics: Dict[str, Any] = field(default_factory=dict)
    visual_characteristics: Dict[str, Any] = field(default_factory=dict)
    avoid_elements: List[str] = field(default_factory=list)
    rationale: str = ""


# =============================================================================
# SECTION 3: IMPRESSION CONTEXT — THE DSP INPUT LAYER
# =============================================================================

@dataclass
class ImpressionContext:
    """
    Everything the DSP observes at bid time. This is the INPUT to the
    psychological inference engine — raw behavioral and contextual signals
    that get transformed into a PsychologicalStateVector.
    """
    # --- Temporal ---
    timestamp: float = 0.0
    day_of_week: int = 0
    local_hour: int = 12

    # --- Device ---
    device_type: DeviceType = DeviceType.DESKTOP
    screen_width: int = 1920
    screen_height: int = 1080
    dark_mode: bool = False
    connection_speed_mbps: float = 50.0

    # --- Content Context ---
    page_url: str = ""
    content_category: ContentCategory = ContentCategory.NEWS
    content_sentiment: float = 0.0
    content_arousal: float = 0.5
    content_complexity: float = 0.5
    content_keywords: List[str] = field(default_factory=list)
    ad_density: float = 0.3

    # --- Current Session Behavioral ---
    session_duration_seconds: int = 0
    pages_viewed: int = 1
    scroll_depth: float = 0.0
    scroll_velocity: float = 0.0
    time_on_page_seconds: float = 0.0
    mouse_velocity: float = 0.0
    mouse_max_deviation: float = 0.0
    click_precision: float = 1.0
    backspace_frequency: float = 0.0
    touch_pressure: float = 0.5

    # --- Navigation ---
    referrer_type: str = "direct"
    search_query: str = ""
    navigation_directness: float = 0.5
    category_changes: int = 0
    comparison_behavior: float = 0.0

    # --- Publisher First-Party ---
    publisher_segment: str = ""
    subscriber_status: bool = False
    visit_frequency: float = 0.0
    content_preferences: List[str] = field(default_factory=list)

    # --- Ad Opportunity ---
    available_formats: List[CreativeFormat] = field(default_factory=list)
    viewability_prediction: float = 0.7
    above_fold: bool = True

    # --- ADAM Extensions ---
    product_category: str = ""
    brand_name: str = ""
    price_point: Optional[float] = None
    involvement_level: str = "medium"  # low, medium, high
    prior_ndf_profile: Optional[Dict[str, float]] = None
    archetype_hint: str = ""

    # === DERIVED PROPERTIES ===

    @property
    def session_phase(self) -> str:
        if self.session_duration_seconds < 30:
            return "early"
        elif self.session_duration_seconds < 180:
            return "middle"
        elif self.session_duration_seconds < 600:
            return "extended"
        else:
            return "deep"

    @property
    def estimated_cognitive_load(self) -> float:
        """Estimate cognitive load from multiple signals."""
        load = 0.3
        load += min(0.3, self.content_complexity * 0.4)
        load += min(0.2, self.ad_density * 0.3)
        if self.session_duration_seconds > 600:
            load += 0.1
        if self.pages_viewed > 10:
            load += 0.1
        return max(0.0, min(1.0, load))

    @property
    def estimated_processing_mode(self) -> str:
        """System 1 vs System 2 estimate."""
        if self.scroll_velocity > 500 and self.time_on_page_seconds < 10:
            return "system1_dominant"
        elif self.time_on_page_seconds > 60 and self.scroll_velocity < 200:
            return "system2_dominant"
        elif self.comparison_behavior > 0.5:
            return "system2_dominant"
        return "mixed"

    @property
    def estimated_chronotype_state(self) -> str:
        """Estimate chronotype-aligned state from hour."""
        if 6 <= self.local_hour <= 9:
            return "morning_peak_rising"
        elif 9 <= self.local_hour <= 12:
            return "morning_peak_sustained"
        elif 12 <= self.local_hour <= 14:
            return "post_lunch_dip"
        elif 14 <= self.local_hour <= 17:
            return "afternoon_peak_sustained"
        elif 17 <= self.local_hour <= 21:
            return "evening_declining"
        else:
            return "night_depleted"


# =============================================================================
# SECTION 4: PSYCHOLOGICAL STATE VECTOR — THE INFERRED CONSUMER STATE
# =============================================================================

@dataclass
class PsychologicalStateVector:
    """
    50+ dimensional psychological state inferred from behavioral signals at
    impression time. Every dimension is 0-1 (unless noted) with confidence.

    This bridges the DSP engine and ADAM's NDF system — the to_ndf_profile()
    method maps these 50+ dimensions to ADAM's 7+1 NDF dimensions.
    """
    # --- Regulatory & Motivational ---
    promotion_focus: float = 0.5
    promotion_focus_confidence: float = 0.3
    prevention_focus: float = 0.5
    prevention_focus_confidence: float = 0.3
    approach_motivation_bas: float = 0.5
    avoidance_motivation_bis: float = 0.5
    autonomy_need: float = 0.5
    competence_need: float = 0.5
    relatedness_need: float = 0.5

    # --- Cognitive ---
    cognitive_load: float = 0.5
    cognitive_load_confidence: float = 0.3
    processing_mode: float = 0.5  # 0=System1, 1=System2
    attention_level: float = 0.5
    vigilance_remaining: float = 0.7
    mind_wandering_probability: float = 0.3
    processing_fluency: float = 0.5

    # --- Emotional ---
    valence: float = 0.0  # -1 to 1
    arousal: float = 0.5  # 0 to 1
    dominant_emotion: str = "neutral"
    emotional_stability: float = 0.5
    mood_source_identified: bool = False

    # --- Personality (Big Five) ---
    openness: float = 0.5
    conscientiousness: float = 0.5
    extraversion: float = 0.5
    agreeableness: float = 0.5
    neuroticism: float = 0.5
    personality_confidence: float = 0.2

    # --- Values & Moral Foundations ---
    care_harm: float = 0.5
    fairness_cheating: float = 0.5
    loyalty_betrayal: float = 0.5
    authority_subversion: float = 0.5
    sanctity_degradation: float = 0.5
    liberty_oppression: float = 0.5

    # --- Construal Level ---
    construal_level: float = 0.5  # 0=concrete/how, 1=abstract/why
    psychological_distance: float = 0.5
    temporal_distance: float = 0.5

    # --- Decision State ---
    funnel_stage: FunnelStage = FunnelStage.AWARENESS
    decision_confidence: float = 0.5
    information_saturation: float = 0.0
    comparison_intensity: float = 0.0
    choice_overload_risk: float = 0.0
    purchase_urgency: float = 0.0

    # --- Social & Identity ---
    social_proof_susceptibility: float = 0.5
    identity_salience: float = 0.3
    ingroup_activation: float = 0.3
    status_motivation: float = 0.3

    # --- Temporal & Circadian ---
    chronotype_state: str = "afternoon_peak_sustained"
    circadian_cognitive_capacity: float = 0.7
    sleep_deprivation_probability: float = 0.1
    decision_fatigue_level: float = 0.2

    # --- Habit & Learning ---
    brand_habit_strength: float = 0.0
    model_free_dominance: float = 0.5
    wanting_without_liking: float = 0.0
    mere_exposure_saturation: float = 0.0

    # --- Vulnerability Protection ---
    vulnerability_flags: List[VulnerabilityType] = field(default_factory=list)
    vulnerability_severity: float = 0.0
    protection_mode: bool = False

    # === DERIVED METHODS ===

    def get_dominant_motivational_frame(self) -> str:
        if self.promotion_focus > self.prevention_focus + 0.15:
            return "promotion"
        elif self.prevention_focus > self.promotion_focus + 0.15:
            return "prevention"
        return "balanced"

    def get_optimal_processing_route(self) -> str:
        """Determine which persuasion route will be most effective."""
        if self.processing_mode > 0.7 and self.cognitive_load < 0.5:
            return "central"
        if self.arousal > 0.7 or self.valence < -0.3:
            return "emotional"
        if self.social_proof_susceptibility > 0.6 and self.ingroup_activation > 0.4:
            return "social"
        if self.mind_wandering_probability > 0.5 or self.processing_mode < 0.3:
            return "narrative"
        if self.cognitive_load > 0.7:
            return "peripheral"
        return "mixed"

    def get_moral_foundation_profile(self) -> Dict[str, float]:
        return {
            "care_harm": self.care_harm,
            "fairness_cheating": self.fairness_cheating,
            "loyalty_betrayal": self.loyalty_betrayal,
            "authority_subversion": self.authority_subversion,
            "sanctity_degradation": self.sanctity_degradation,
            "liberty_oppression": self.liberty_oppression,
        }

    def get_binding_vs_individualizing(self) -> Tuple[float, float]:
        """Binding (loyalty+authority+sanctity) vs Individualizing (care+fairness+liberty)."""
        binding = (self.loyalty_betrayal + self.authority_subversion + self.sanctity_degradation) / 3
        individualizing = (self.care_harm + self.fairness_cheating + self.liberty_oppression) / 3
        return (binding, individualizing)

    def to_ndf_profile(self) -> Dict[str, float]:
        """Map 50+ dimensional state vector to ADAM's 7+1 NDF dimensions."""
        return {
            "approach_avoidance": max(-1.0, min(1.0,
                (self.promotion_focus - self.prevention_focus) * 2)),
            "temporal_horizon": self.construal_level,
            "social_calibration": self.social_proof_susceptibility,
            "uncertainty_tolerance": max(0.0, min(1.0,
                1.0 - (self.choice_overload_risk * 0.5 + (1.0 - self.decision_confidence) * 0.5))),
            "status_sensitivity": self.status_motivation,
            "cognitive_engagement": self.processing_mode,
            "arousal_seeking": self.arousal,
            "cognitive_velocity": max(0.0, min(1.0,
                self.processing_fluency * 0.6 + self.attention_level * 0.4)),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for API responses."""
        result = {}
        for f in self.__dataclass_fields__:
            val = getattr(self, f)
            if isinstance(val, Enum):
                result[f] = val.value
            elif isinstance(val, list):
                result[f] = [v.value if isinstance(v, Enum) else v for v in val]
            else:
                result[f] = val
        return result


# =============================================================================
# SECTION 5: PERSUASION STRATEGY — THE COMPLETE OUTPUT SPACE
# =============================================================================

@dataclass
class PersuasionStrategy:
    """
    What the DSP recommends to the advertiser based on inferred psychological
    state. This is the ACTIONABLE OUTPUT — translating psychology into creative.
    """
    # --- Message Strategy ---
    message_frame: str = "gain"
    argument_strength: str = "strong"
    construal_match: str = "abstract_why"
    regulatory_fit: str = "promotion_gain"
    self_reference_level: str = "moderate"

    # --- Creative Execution ---
    persuasion_route: PersuasionRoute = PersuasionRoute.MIXED
    emotional_vehicle: EmotionalVehicle = EmotionalVehicle.NEUTRAL
    recommended_formats: List[CreativeFormat] = field(default_factory=list)
    copy_length: str = "medium"
    visual_style: str = "clean"
    white_space_level: str = "moderate"
    color_temperature: str = "neutral"
    model_type: str = "aspirational"
    eye_gaze: str = "direct"
    logo_size: str = "moderate"

    # --- Social Proof ---
    social_proof_type: str = "none"
    social_proof_strength: float = 0.0
    scarcity_messaging: str = "none"
    authority_signal: str = "none"

    # --- Temporal Optimization ---
    optimal_exposure_duration_ms: int = 5000
    frequency_cap_recommendation: int = 3
    spacing_recommendation_hours: float = 24.0
    sequence_position: str = "any"

    # --- Context Optimization ---
    content_affinity: float = 0.5
    mood_congruency_strategy: str = "congruent"
    clutter_tolerance: float = 0.5

    # --- Counter-indications ---
    avoid_elements: List[str] = field(default_factory=list)
    vulnerability_protections: List[str] = field(default_factory=list)

    # --- Mechanism Chain ---
    primary_mechanism: MechanismType = MechanismType.ELABORATION
    mechanism_chain: List[str] = field(default_factory=list)
    expected_effect_size: float = 0.3
    confidence: float = 0.5
    reasoning_trace: List[str] = field(default_factory=list)

    # --- ADAM Extensions ---
    inferential_chains: List[Dict[str, Any]] = field(default_factory=list)
    atom_recommended_mechanisms: List[str] = field(default_factory=list)
    ndf_profile_used: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for API responses."""
        return {
            "message_frame": self.message_frame,
            "argument_strength": self.argument_strength,
            "construal_match": self.construal_match,
            "regulatory_fit": self.regulatory_fit,
            "persuasion_route": self.persuasion_route.value if isinstance(self.persuasion_route, Enum) else self.persuasion_route,
            "emotional_vehicle": self.emotional_vehicle.value if isinstance(self.emotional_vehicle, Enum) else self.emotional_vehicle,
            "recommended_formats": [f.value if isinstance(f, Enum) else f for f in self.recommended_formats],
            "copy_length": self.copy_length,
            "visual_style": self.visual_style,
            "social_proof_type": self.social_proof_type,
            "social_proof_strength": self.social_proof_strength,
            "primary_mechanism": self.primary_mechanism.value if isinstance(self.primary_mechanism, Enum) else self.primary_mechanism,
            "mechanism_chain": self.mechanism_chain,
            "confidence": self.confidence,
            "reasoning_trace": self.reasoning_trace,
            "inferential_chains": self.inferential_chains,
            "avoid_elements": self.avoid_elements,
            "vulnerability_protections": self.vulnerability_protections,
        }


# =============================================================================
# SECTION 6: INVENTORY ENRICHMENT SCORE — CPM PREMIUM JUSTIFICATION
# =============================================================================

@dataclass
class InventoryEnrichmentScore:
    """
    Translates psychological optimization into CPM multiplier.
    Standard inventory → enriched inventory: 1.0x to 5.0x premium.
    """
    base_cpm: float = 2.50
    enrichment_multiplier: float = 1.0

    # Scoring dimensions (each 0-1)
    psychological_match_score: float = 0.0
    persuasion_optimization_score: float = 0.0
    temporal_alignment_score: float = 0.0
    creative_fit_score: float = 0.0
    attention_probability: float = 0.5
    vulnerability_clean: float = 1.0

    # Attached outputs
    recommended_strategy: Optional[PersuasionStrategy] = None
    reasoning_trace: List[str] = field(default_factory=list)

    # ADAM extensions
    inferential_chain_count: int = 0
    atom_confidence: float = 0.0
    theory_graph_depth: int = 0

    @property
    def enriched_cpm(self) -> float:
        return self.base_cpm * self.enrichment_multiplier

    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_cpm": self.base_cpm,
            "enrichment_multiplier": round(self.enrichment_multiplier, 3),
            "enriched_cpm": round(self.enriched_cpm, 2),
            "dimensions": {
                "psychological_match": round(self.psychological_match_score, 3),
                "persuasion_optimization": round(self.persuasion_optimization_score, 3),
                "temporal_alignment": round(self.temporal_alignment_score, 3),
                "creative_fit": round(self.creative_fit_score, 3),
                "attention_probability": round(self.attention_probability, 3),
                "vulnerability_clean": round(self.vulnerability_clean, 3),
            },
            "adam_enrichment": {
                "inferential_chain_count": self.inferential_chain_count,
                "atom_confidence": round(self.atom_confidence, 3),
                "theory_graph_depth": self.theory_graph_depth,
            },
            "reasoning_trace": self.reasoning_trace,
        }
