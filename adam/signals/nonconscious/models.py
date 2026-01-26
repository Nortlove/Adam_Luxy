# =============================================================================
# ADAM Nonconscious Analytics - Models
# =============================================================================

"""
NONCONSCIOUS SIGNAL MODELS

Research-backed data models for implicit behavioral signals and psychological
inference from nonconscious processes.

Scientific Foundations:
- Mouse dynamics correlate with cognitive state (Hehman et al., 2015)
- Keystroke patterns reveal personality (Segalin et al., 2017)
- Response latency reflects attitude accessibility (Fazio, 1990)
- Scroll behavior indicates engagement depth (Huang & Mosier, 2012)
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================

class SignalSource(str, Enum):
    """Source of nonconscious signal capture."""
    MOUSE = "mouse"
    KEYBOARD = "keyboard"
    SCROLL = "scroll"
    TOUCH = "touch"
    TIMING = "timing"
    GAZE = "gaze"  # If eye tracking available
    AUDIO = "audio"  # Voice hesitation, pace


class ProcessingDepth(str, Enum):
    """Processing depth per Elaboration Likelihood Model."""
    PERIPHERAL = "peripheral"  # Low elaboration, heuristic
    CENTRAL = "central"  # High elaboration, systematic
    MIXED = "mixed"


class ValenceDirection(str, Enum):
    """Emotional valence direction."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    AMBIVALENT = "ambivalent"


# =============================================================================
# RAW SIGNAL MODELS
# =============================================================================

class NonconsciousSignal(BaseModel):
    """Base model for all nonconscious signals."""
    
    signal_id: str = Field(default_factory=lambda: f"nc_{uuid4().hex[:12]}")
    user_id: str
    session_id: str
    source: SignalSource
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Raw measurement
    raw_value: Dict[str, Any] = Field(default_factory=dict)
    
    # Capture quality
    capture_confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    
    # Context
    page_url: Optional[str] = None
    element_id: Optional[str] = None
    content_context: Optional[str] = None


class KinematicSignal(NonconsciousSignal):
    """
    Mouse/cursor movement signal.
    
    Research: Mouse tracking reveals decision processes in real-time
    (Freeman & Ambady, 2010; Spivey et al., 2005)
    """
    
    source: SignalSource = SignalSource.MOUSE
    
    # Movement vectors
    positions: List[Tuple[float, float, int]] = Field(
        default_factory=list,
        description="List of (x, y, timestamp_ms) tuples"
    )
    
    # Derived metrics
    total_distance: float = Field(ge=0.0, default=0.0)
    duration_ms: int = Field(ge=0, default=0)
    
    # Movement characteristics
    avg_velocity: float = Field(ge=0.0, default=0.0)
    max_velocity: float = Field(ge=0.0, default=0.0)
    velocity_variance: float = Field(ge=0.0, default=0.0)
    
    # Trajectory analysis
    directness_ratio: float = Field(
        ge=0.0, le=1.0, default=1.0,
        description="Straight line distance / actual path (1.0 = direct)"
    )
    x_flips: int = Field(ge=0, default=0, description="Horizontal direction changes")
    y_flips: int = Field(ge=0, default=0, description="Vertical direction changes")
    
    # Hovering
    hover_events: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of hover events with element, duration"
    )
    
    # Psychological indicators
    decisiveness_score: float = Field(
        ge=0.0, le=1.0, default=0.5,
        description="Higher = more decisive movement"
    )
    conflict_indicator: float = Field(
        ge=0.0, le=1.0, default=0.0,
        description="Higher = more trajectory conflict (x-flips)"
    )


class ScrollBehaviorSignal(NonconsciousSignal):
    """
    Scroll behavior signal.
    
    Research: Scroll patterns indicate engagement and information processing
    (Arapakis et al., 2014; Kim et al., 2015)
    """
    
    source: SignalSource = SignalSource.SCROLL
    
    # Scroll metrics
    total_scroll_distance: int = Field(ge=0, default=0)
    max_depth_percent: float = Field(ge=0.0, le=100.0, default=0.0)
    scroll_events: int = Field(ge=0, default=0)
    
    # Velocity patterns
    avg_scroll_velocity: float = Field(ge=0.0, default=0.0)
    velocity_changes: int = Field(ge=0, default=0)
    
    # Pauses (indicating reading/processing)
    pause_count: int = Field(ge=0, default=0)
    total_pause_duration_ms: int = Field(ge=0, default=0)
    avg_pause_duration_ms: float = Field(ge=0.0, default=0.0)
    
    # Re-reading behavior
    reverse_scroll_count: int = Field(ge=0, default=0)
    revisit_sections: List[str] = Field(default_factory=list)
    
    # Engagement indicators
    engagement_score: float = Field(ge=0.0, le=1.0, default=0.5)
    depth_engagement: float = Field(ge=0.0, le=1.0, default=0.5)
    deliberation_score: float = Field(ge=0.0, le=1.0, default=0.5)


class KeystrokeSignal(NonconsciousSignal):
    """
    Keystroke dynamics signal.
    
    Research: Keystroke timing patterns correlate with personality traits
    (Banerjee & Woodard, 2012; Monaco et al., 2013)
    """
    
    source: SignalSource = SignalSource.KEYBOARD
    
    # Timing measurements (milliseconds)
    avg_dwell_time: float = Field(
        ge=0.0, default=0.0,
        description="Time key held down"
    )
    avg_flight_time: float = Field(
        ge=0.0, default=0.0,
        description="Time between key release and next press"
    )
    avg_interkey_latency: float = Field(
        ge=0.0, default=0.0,
        description="Time between consecutive key presses"
    )
    
    # Variance (indicates consistency)
    dwell_variance: float = Field(ge=0.0, default=0.0)
    flight_variance: float = Field(ge=0.0, default=0.0)
    
    # Speed
    typing_speed_cpm: float = Field(ge=0.0, default=0.0)
    words_per_minute: float = Field(ge=0.0, default=0.0)
    
    # Corrections (indicates uncertainty/carefulness)
    backspace_count: int = Field(ge=0, default=0)
    delete_count: int = Field(ge=0, default=0)
    correction_rate: float = Field(ge=0.0, default=0.0)
    
    # Pauses (indicates thinking)
    pause_count: int = Field(ge=0, default=0)
    avg_pause_duration_ms: float = Field(ge=0.0, default=0.0)
    
    # Psychological indicators
    deliberation_score: float = Field(ge=0.0, le=1.0, default=0.5)
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.5)
    emotional_arousal: float = Field(ge=0.0, le=1.0, default=0.5)


class TemporalSignal(NonconsciousSignal):
    """
    Response latency and timing signal.
    
    Research: Response times indicate attitude accessibility and
    automatic evaluations (Fazio, 1990; Greenwald et al., 1998)
    """
    
    source: SignalSource = SignalSource.TIMING
    
    # Primary latency
    response_latency_ms: int = Field(
        ge=0, default=0,
        description="Time from stimulus to response"
    )
    
    # Context
    stimulus_type: str = Field(default="", description="What triggered timing")
    response_type: str = Field(default="", description="What response occurred")
    
    # Normalized metrics
    latency_percentile: float = Field(
        ge=0.0, le=1.0, default=0.5,
        description="Percentile vs. user's baseline"
    )
    deviation_from_baseline: float = Field(
        default=0.0,
        description="Z-score from user's mean"
    )
    
    # Interpretation
    attitude_accessibility: float = Field(
        ge=0.0, le=1.0, default=0.5,
        description="Higher = more accessible attitude"
    )


class HesitationSignal(NonconsciousSignal):
    """
    Hesitation and uncertainty signal.
    
    Aggregated from multiple sources to detect decisional conflict.
    """
    
    # Sources contributing
    contributing_signals: List[str] = Field(default_factory=list)
    
    # Hesitation metrics
    hesitation_count: int = Field(ge=0, default=0)
    total_hesitation_duration_ms: int = Field(ge=0, default=0)
    
    # Pattern
    pre_decision_hesitation: bool = Field(default=False)
    mid_action_hesitation: bool = Field(default=False)
    post_action_hesitation: bool = Field(default=False)
    
    # Psychological indicators
    uncertainty_score: float = Field(ge=0.0, le=1.0, default=0.5)
    conflict_score: float = Field(ge=0.0, le=1.0, default=0.5)


class RhythmicSignal(NonconsciousSignal):
    """
    Session rhythm and engagement cadence signal.
    
    Captures temporal patterns across a session.
    """
    
    # Session metrics
    session_duration_ms: int = Field(ge=0, default=0)
    active_duration_ms: int = Field(ge=0, default=0)
    
    # Engagement rhythm
    engagement_bursts: int = Field(ge=0, default=0)
    avg_burst_duration_ms: float = Field(ge=0.0, default=0.0)
    inter_burst_interval_ms: float = Field(ge=0.0, default=0.0)
    
    # Attention patterns
    attention_spans: List[int] = Field(
        default_factory=list,
        description="Durations of focused attention periods"
    )
    avg_attention_span_ms: float = Field(ge=0.0, default=0.0)
    
    # Flow indicators
    flow_score: float = Field(ge=0.0, le=1.0, default=0.5)
    sustained_engagement: bool = Field(default=False)


# =============================================================================
# AGGREGATED PSYCHOLOGICAL CONSTRUCTS
# =============================================================================

class ApproachAvoidanceTendency(BaseModel):
    """
    Approach-Avoidance motivation indicator.
    
    Research: Fundamental motivational system influencing behavior
    (Elliot & Thrash, 2002; Carver & White, 1994)
    """
    
    user_id: str
    session_id: str
    
    # Core scores
    approach_strength: float = Field(
        ge=0.0, le=1.0, default=0.5,
        description="Strength of approach motivation"
    )
    avoidance_strength: float = Field(
        ge=0.0, le=1.0, default=0.5,
        description="Strength of avoidance motivation"
    )
    
    # Net tendency
    net_tendency: float = Field(
        ge=-1.0, le=1.0, default=0.0,
        description="Approach (+) vs Avoidance (-)"
    )
    
    # Evidence
    approach_signals: List[str] = Field(default_factory=list)
    avoidance_signals: List[str] = Field(default_factory=list)
    
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CognitiveLoadIndicator(BaseModel):
    """
    Cognitive load estimation.
    
    Research: Cognitive load affects decision quality and susceptibility
    (Sweller, 1988; Baumeister et al., 1998)
    """
    
    user_id: str
    session_id: str
    
    # Load levels
    intrinsic_load: float = Field(
        ge=0.0, le=1.0, default=0.5,
        description="Load from task complexity"
    )
    extraneous_load: float = Field(
        ge=0.0, le=1.0, default=0.5,
        description="Load from poor design"
    )
    germane_load: float = Field(
        ge=0.0, le=1.0, default=0.5,
        description="Load for learning"
    )
    
    # Total
    total_load: float = Field(ge=0.0, le=1.0, default=0.5)
    capacity_remaining: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Indicators
    is_overloaded: bool = Field(default=False)
    processing_depth: ProcessingDepth = Field(default=ProcessingDepth.MIXED)
    
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class EmotionalValenceProxy(BaseModel):
    """
    Emotional valence estimated from behavioral signals.
    
    Research: Somatic marker hypothesis - emotions guide decision-making
    (Damasio, 1994; Bechara et al., 1997)
    """
    
    user_id: str
    session_id: str
    
    # Valence
    valence: float = Field(
        ge=-1.0, le=1.0, default=0.0,
        description="Negative (-1) to Positive (+1)"
    )
    valence_direction: ValenceDirection = Field(default=ValenceDirection.NEUTRAL)
    
    # Arousal
    arousal: float = Field(
        ge=0.0, le=1.0, default=0.5,
        description="Low (0) to High (1) arousal"
    )
    
    # Dominance
    dominance: float = Field(
        ge=0.0, le=1.0, default=0.5,
        description="Feeling of control"
    )
    
    # Contributing signals
    velocity_contribution: float = Field(default=0.0)
    rhythm_contribution: float = Field(default=0.0)
    correction_contribution: float = Field(default=0.0)
    
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class ProcessingFluencyScore(BaseModel):
    """
    Processing fluency indicator.
    
    Research: Processing fluency affects preferences and trust
    (Reber et al., 1998; Alter & Oppenheimer, 2009)
    """
    
    user_id: str
    session_id: str
    
    # Fluency components
    perceptual_fluency: float = Field(
        ge=0.0, le=1.0, default=0.5,
        description="Ease of perceptual processing"
    )
    conceptual_fluency: float = Field(
        ge=0.0, le=1.0, default=0.5,
        description="Ease of meaning extraction"
    )
    
    # Combined
    overall_fluency: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Implications
    likely_preference_boost: float = Field(
        ge=-0.5, le=0.5, default=0.0,
        description="Expected preference impact"
    )
    likely_trust_boost: float = Field(
        ge=-0.5, le=0.5, default=0.0,
        description="Expected trust impact"
    )
    
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class EngagementIntensity(BaseModel):
    """
    Engagement intensity profile.
    
    Multi-dimensional engagement measurement.
    """
    
    user_id: str
    session_id: str
    
    # Engagement dimensions
    behavioral_engagement: float = Field(ge=0.0, le=1.0, default=0.5)
    cognitive_engagement: float = Field(ge=0.0, le=1.0, default=0.5)
    emotional_engagement: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Combined
    overall_engagement: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Trajectory
    engagement_trend: str = Field(
        default="stable",
        description="increasing, decreasing, stable, volatile"
    )
    
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


# =============================================================================
# INFERENCE RESULTS
# =============================================================================

class ImplicitPreference(BaseModel):
    """
    Implicit preference inferred from nonconscious signals.
    
    Research: Implicit attitudes predict spontaneous behavior
    (Greenwald & Banaji, 1995; Fazio & Olson, 2003)
    """
    
    user_id: str
    target_id: str  # What the preference is for
    target_type: str  # brand, product, category, mechanism
    
    # Preference
    preference_strength: float = Field(
        ge=-1.0, le=1.0, default=0.0,
        description="Strong negative (-1) to strong positive (+1)"
    )
    preference_accessibility: float = Field(
        ge=0.0, le=1.0, default=0.5,
        description="How quickly/automatically this preference activates"
    )
    
    # Explicit comparison
    explicit_alignment: Optional[float] = Field(
        None,
        description="Correlation with explicit preference if known"
    )
    
    # Evidence
    evidence_signals: List[str] = Field(default_factory=list)
    evidence_count: int = Field(ge=0, default=0)
    
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    inferred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class AutomaticEvaluation(BaseModel):
    """
    Automatic evaluation of a stimulus.
    
    Research: Automatic evaluations occur within milliseconds
    (Bargh et al., 1996; Murphy & Zajonc, 1993)
    """
    
    user_id: str
    stimulus_id: str
    stimulus_type: str
    
    # Evaluation
    valence: float = Field(
        ge=-1.0, le=1.0, default=0.0,
        description="Automatic good/bad evaluation"
    )
    latency_ms: int = Field(ge=0, default=0)
    
    # Characteristics
    is_automatic: bool = Field(default=True)
    is_strong: bool = Field(default=False)
    
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NonconsciousProfile(BaseModel):
    """
    Complete nonconscious profile for a user session.
    
    Aggregates all nonconscious indicators into actionable intelligence.
    """
    
    user_id: str
    session_id: str
    
    # Core constructs
    approach_avoidance: ApproachAvoidanceTendency
    cognitive_load: CognitiveLoadIndicator
    emotional_valence: EmotionalValenceProxy
    processing_fluency: ProcessingFluencyScore
    engagement: EngagementIntensity
    
    # Implicit preferences
    implicit_preferences: List[ImplicitPreference] = Field(default_factory=list)
    
    # Automatic evaluations
    automatic_evaluations: List[AutomaticEvaluation] = Field(default_factory=list)
    
    # Raw signals used
    signals_processed: int = Field(ge=0, default=0)
    signal_types: List[str] = Field(default_factory=list)
    
    # Recommendations for persuasion
    recommended_processing_route: ProcessingDepth = Field(
        default=ProcessingDepth.MIXED
    )
    recommended_mechanisms: List[str] = Field(default_factory=list)
    mechanism_confidence: Dict[str, float] = Field(default_factory=dict)
    
    # Quality
    overall_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    profile_completeness: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valid_until: Optional[datetime] = None
