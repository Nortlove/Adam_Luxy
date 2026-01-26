# =============================================================================
# ADAM Behavioral Analytics: Advertising Psychology Models
# Location: adam/behavioral_analytics/models/advertising_psychology.py
# =============================================================================

"""
ADVERTISING PSYCHOLOGY MODELS

Comprehensive models for psychologically-informed ad targeting and recommendation,
synthesizing 200+ empirical findings across 22 scientific domains (1989-2025).

Key Research Domains:
1. Signal Collection (Linguistic, Desktop Implicit, Mobile Implicit)
2. Personality Inference (Big Five via LIWC, behavioral signals)
3. Regulatory Focus (Promotion/Prevention detection and matching)
4. Cognitive State (Load estimation, circadian patterns)
5. Approach-Avoidance (BIS/BAS orientation)
6. Evolutionary Psychology (Life history, costly signaling)
7. Memory Optimization (Spacing effect, peak-end rule)
8. Nonconscious Processing (Low attention, wanting-liking)
9. Moral Foundations (6 foundations targeting)
10. Psychophysics (JND, cross-modal, fluency)
11. Temporal Targeting (Construal level, circadian)
12. Social Effects (Contagion, identity)

Core Insight: Advertising effectiveness operates primarily through nonconscious
processing (70-95% of decisions), yet industry measures conscious metrics.

Reference: advertising_psychology_research_claude_code_instructions.md
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import uuid


# =============================================================================
# CONFIDENCE TIERS
# =============================================================================

class ConfidenceTier(int, Enum):
    """
    Evidence quality tiers based on replication and meta-analysis status.
    
    TIER_1: Meta-analyzed, k>10 studies, large N - USE AS PRIMARY SIGNALS
    TIER_2: Independently replicated 3+ studies - USE WITH MONITORING
    TIER_3: Large sample, strong methodology, awaiting replication - EXPLORATORY
    TIER_4: Failed or mixed replication - DO NOT RELY ON
    """
    TIER_1_META_ANALYZED = 1
    TIER_2_REPLICATED = 2
    TIER_3_SINGLE_STUDY = 3
    TIER_4_CONTESTED = 4


class SignalConfidence(str, Enum):
    """Confidence level for signal-to-construct mapping."""
    HIGH = "high"          # d > 0.5 or r > 0.3, replicated
    MODERATE = "moderate"  # d 0.2-0.5 or r 0.1-0.3, replicated
    LOW = "low"            # Small effect or single study
    CONTESTED = "contested"  # Failed replications


# =============================================================================
# LINGUISTIC FEATURES (LIWC-22 BASED)
# =============================================================================

class LinguisticFeatures(BaseModel):
    """
    LIWC-22 and custom text features for psychological inference.
    
    CRITICAL: Single reviews (~100-500 words) are insufficient for individual-level
    personality inference. Aggregate 10+ reviews (minimum 3000 words) for reliability.
    
    Expected accuracy ceiling: r = 0.20-0.40 for Big Five traits
    Reference: Koutsoumpis et al. (2022) meta-analysis (k=31, N=85,724)
    """
    
    # LIWC Summary Variables (1-99 scale)
    analytic: float = Field(default=50.0, ge=0.0, le=100.0, 
        description="Formal, logical thinking")
    clout: float = Field(default=50.0, ge=0.0, le=100.0,
        description="Speaking from confidence/leadership")
    authentic: float = Field(default=50.0, ge=0.0, le=100.0,
        description="Personal, honest disclosure")
    tone: float = Field(default=50.0, ge=0.0, le=100.0,
        description="Emotional positivity")
    
    # Pronoun Patterns (proportion of words)
    first_person_singular: float = Field(default=0.0, ge=0.0, le=1.0,
        description="I, me, my - correlates with Neuroticism (rho=0.10)")
    first_person_plural: float = Field(default=0.0, ge=0.0, le=1.0,
        description="We, us, our - correlates with Status, Extraversion")
    
    # Affect Categories
    positive_emotion: float = Field(default=0.0, ge=0.0, le=1.0,
        description="Correlates with Extraversion (rho=0.11-0.14)")
    negative_emotion: float = Field(default=0.0, ge=0.0, le=1.0,
        description="Correlates with Neuroticism (rho=0.08-0.14)")
    anxiety_words: float = Field(default=0.0, ge=0.0, le=1.0)
    anger_words: float = Field(default=0.0, ge=0.0, le=1.0)
    sadness_words: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Cognitive Process
    insight_words: float = Field(default=0.0, ge=0.0, le=1.0,
        description="Correlates with Openness")
    causation_words: float = Field(default=0.0, ge=0.0, le=1.0)
    certainty_words: float = Field(default=0.0, ge=0.0, le=1.0,
        description="Boosters vs hedges")
    tentative_words: float = Field(default=0.0, ge=0.0, le=1.0,
        description="Correlates with Openness (rho=0.08)")
    
    # Social
    social_words: float = Field(default=0.0, ge=0.0, le=1.0,
        description="Correlates with Extraversion (rho=0.10-0.14)")
    
    # Complexity Indicators
    word_count: int = Field(default=0, ge=0)
    words_per_sentence: float = Field(default=0.0, ge=0.0)
    six_letter_words: float = Field(default=0.0, ge=0.0, le=1.0,
        description="Correlates with Openness")
    
    # Custom Extractors
    exclamation_density: float = Field(default=0.0, ge=0.0, le=1.0,
        description="Correlates with Extraversion")
    question_density: float = Field(default=0.0, ge=0.0, le=1.0)
    capitalization_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    emoji_count: int = Field(default=0, ge=0)
    
    # Achievement and regulatory focus markers
    achievement_words: float = Field(default=0.0, ge=0.0, le=1.0)
    negations: float = Field(default=0.0, ge=0.0, le=1.0)
    articles: float = Field(default=0.0, ge=0.0, le=1.0)
    
    def is_sufficient_for_personality(self, min_words: int = 3000) -> bool:
        """Check if text volume is sufficient for reliable personality inference."""
        return self.word_count >= min_words


# =============================================================================
# DESKTOP BEHAVIORAL SIGNALS
# =============================================================================

class DesktopBehavioralSignals(BaseModel):
    """
    Cursor, keystroke, and scroll patterns for psychological inference.
    
    Research basis:
    - Cursor trajectory: d = 0.4-1.6 for decisional conflict (Freeman & Ambady)
    - Keystroke authentication: EER < 1% (CNN + gradient boosting)
    - Emotion from typing: AUC 0.73-0.94 with personalization
    """
    
    # Cursor Trajectory Metrics
    cursor_auc: float = Field(default=0.0, ge=0.0,
        description="Area under curve - deviation from ideal path")
    cursor_mad: float = Field(default=0.0, ge=0.0,
        description="Maximum absolute deviation")
    cursor_x_flips: int = Field(default=0, ge=0,
        description="Direction reversals indicate uncertainty")
    cursor_velocity_min: float = Field(default=0.0, ge=0.0,
        description="Hesitation points")
    cursor_initiation_time: float = Field(default=0.0, ge=0.0,
        description="Processing difficulty in ms")
    
    # Keystroke Dynamics
    inter_key_interval_mean: float = Field(default=0.0, ge=0.0,
        description="Mean digraph timing in ms")
    inter_key_interval_std: float = Field(default=0.0, ge=0.0)
    hold_time_mean: float = Field(default=0.0, ge=0.0,
        description="Mean key press duration in ms")
    hold_time_std: float = Field(default=0.0, ge=0.0)
    typing_speed_variance: float = Field(default=0.0, ge=0.0,
        description="Indicates emotional arousal")
    backspace_frequency: float = Field(default=0.0, ge=0.0, le=1.0,
        description="Indicates stress/cognitive load")
    
    # Scroll Behavior
    scroll_depth: float = Field(default=0.0, ge=0.0, le=1.0,
        description="Engagement threshold: 50%+")
    scroll_velocity_mean: float = Field(default=0.0, ge=0.0,
        description="Fast = scanning; slow = reading")
    scroll_reversals: int = Field(default=0, ge=0,
        description="Confusion or re-reading interest")
    
    # Click Patterns
    rage_clicks: int = Field(default=0, ge=0,
        description="3+ clicks, <500ms, <50px radius = Frustration")
    hesitation_before_click: float = Field(default=0.0, ge=0.0,
        description="Decision uncertainty in ms")
    
    # Session Context
    tab_switches: int = Field(default=0, ge=0,
        description="Distraction level indicator")
    session_duration: float = Field(default=0.0, ge=0.0,
        description="Session length in seconds")
    time_of_day: str = Field(default="12:00",
        description="For circadian matching HH:MM")


class DesktopSignalMapping(BaseModel):
    """Signal-to-construct mapping with effect sizes for desktop signals."""
    
    signal_name: str
    maps_to_construct: str
    effect_size: str  # e.g., "d = 0.4-1.6"
    confidence: SignalConfidence
    action: str  # Recommended action when signal detected


# =============================================================================
# MOBILE BEHAVIORAL SIGNALS
# =============================================================================

class MobileBehavioralSignals(BaseModel):
    """
    Touch, gesture, and sensor patterns for mobile psychological inference.
    
    Research basis:
    - Touch pressure: correlates with emotional arousal
    - Tap location relative to target: intention strength
    - Swipe velocity: decision confidence
    """
    
    # Touch Dynamics
    touch_pressure: float = Field(default=0.5, ge=0.0, le=1.0,
        description="Normalized pressure, correlates with emotional arousal")
    touch_duration: float = Field(default=0.0, ge=0.0,
        description="Engagement/hesitation in ms")
    touch_accuracy: float = Field(default=1.0, ge=0.0, le=1.0,
        description="Distance from target center, intent strength")
    
    # Gesture Patterns
    swipe_velocity: float = Field(default=0.0, ge=0.0,
        description="Fast = confident; slow = uncertain")
    swipe_direction: str = Field(default="neutral",
        description="toward_self = approach; away = avoidance")
    scroll_momentum: float = Field(default=0.0, ge=0.0)
    pinch_zoom_frequency: int = Field(default=0, ge=0,
        description="Detail seeking indicator")
    
    # Device Sensors
    device_orientation: str = Field(default="portrait",
        description="portrait vs landscape")
    accelerometer_variance: float = Field(default=0.0, ge=0.0,
        description="Movement patterns indicator")
    
    # Temporal Patterns
    response_latency: float = Field(default=0.0, ge=0.0,
        description="Decision confidence indicator in ms")
    dwell_time_on_element: float = Field(default=0.0, ge=0.0,
        description="Interest level in ms")
    session_time_of_day: str = Field(default="12:00")


class MobileEmbodiedMapping(BaseModel):
    """Embodied cognition transfer mappings for mobile signals."""
    
    gesture_pattern: str
    maps_to_construct: str
    confidence: SignalConfidence
    application: str


# =============================================================================
# REGULATORY FOCUS
# =============================================================================

class RegulatoryFocusProfile(BaseModel):
    """
    Regulatory Focus detection and matching profile.
    
    CRITICAL: This is one of the highest-impact targeting variables.
    Effect size: OR = 2-6x CTR when ad frame matches regulatory focus.
    Reference: Higgins (1997, 1998); Field experiment in search advertising
    """
    
    focus_type: str = Field(default="neutral",
        description="promotion, prevention, or neutral")
    focus_strength: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: SignalConfidence = Field(default=SignalConfidence.LOW)
    
    # Detection counts
    promotion_marker_count: int = Field(default=0, ge=0)
    prevention_marker_count: int = Field(default=0, ge=0)
    
    # Ad strategy recommendations
    recommended_frame: str = Field(default="neutral",
        description="gain, loss_avoidance, or neutral")
    recommended_language: List[str] = Field(default_factory=list)
    recommended_construal: str = Field(default="mixed",
        description="abstract or concrete")
    recommended_imagery: List[str] = Field(default_factory=list)


# Marker word lists for detection
PROMOTION_FOCUS_MARKERS = [
    'achieve', 'gain', 'advance', 'growth', 'dream', 'aspire',
    'ideal', 'hope', 'wish', 'accomplish', 'attain', 'earn',
    'opportunity', 'success', 'win', 'maximize', 'improve'
]

PREVENTION_FOCUS_MARKERS = [
    'avoid', 'prevent', 'protect', 'secure', 'safe', 'reliable',
    'stable', 'ought', 'should', 'duty', 'obligation', 'careful',
    'risk', 'loss', 'danger', 'mistake', 'careful', 'responsible'
]


# =============================================================================
# COGNITIVE STATE
# =============================================================================

class CognitiveStateProfile(BaseModel):
    """
    Real-time cognitive state for message complexity matching.
    
    Based on Cognitive Load Theory (Sweller) and circadian research.
    Effect sizes: d = 0.5-0.8 for load-reducing interventions.
    """
    
    cognitive_load: float = Field(default=0.5, ge=0.0, le=1.0,
        description="Current cognitive load level")
    
    # Component contributions
    circadian_load: float = Field(default=0.5, ge=0.0, le=1.0)
    fatigue_multiplier: float = Field(default=1.0, ge=1.0, le=1.5)
    behavioral_load: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Recommendations
    recommended_complexity: str = Field(default="moderate",
        description="high, moderate, or low")
    processing_route: str = Field(default="mixed",
        description="central or peripheral (ELM)")
    
    # Message guidelines
    copy_length: str = Field(default="medium")
    argument_style: str = Field(default="balanced")
    
    @property
    def should_use_peripheral_cues(self) -> bool:
        """Whether to use peripheral processing cues (social proof, etc.)."""
        return self.cognitive_load > 0.6


class ChronotypeProfile(BaseModel):
    """
    Chronotype for synchrony effect optimization.
    
    At peak times: MORE persuaded by strong arguments
    At off-peak times: MORE influenced by peripheral cues
    Reference: Yoon et al., 2007; Martin & Marrington, 2005
    """
    
    chronotype: str = Field(default="neutral",
        description="morning (25%), evening (25%), or neutral (50%)")
    
    # Peak performance windows
    peak_start_hour: int = Field(default=10, ge=0, le=23)
    peak_end_hour: int = Field(default=14, ge=0, le=23)
    
    def is_at_peak(self, current_hour: int) -> bool:
        """Check if user is at cognitive peak."""
        if self.chronotype == "morning":
            return 8 <= current_hour <= 11
        elif self.chronotype == "evening":
            return 18 <= current_hour <= 22
        else:
            return 10 <= current_hour <= 17


# =============================================================================
# APPROACH-AVOIDANCE (BIS/BAS)
# =============================================================================

class ApproachAvoidanceProfile(BaseModel):
    """
    BIS/BAS orientation for upstream motivational segmentation.
    
    More fundamental than regulatory focus - reflects biologically-based
    temperament rather than situational state.
    
    Reference: Gray's Reinforcement Sensitivity Theory
    BIS correlates with Neuroticism (r ≈ 0.4-0.6)
    BAS correlates with Extraversion (r ≈ 0.3-0.5)
    """
    
    bas_score: float = Field(default=0.5, ge=0.0, le=1.0,
        description="Behavioral Activation System (approach)")
    bis_score: float = Field(default=0.5, ge=0.0, le=1.0,
        description="Behavioral Inhibition System (avoidance)")
    
    @property
    def dominant_system(self) -> str:
        """Which system is dominant."""
        if self.bas_score > self.bis_score + 0.2:
            return "BAS"
        elif self.bis_score > self.bas_score + 0.2:
            return "BIS"
        else:
            return "balanced"
    
    @property
    def motivation_type(self) -> str:
        """Derived motivation type."""
        if self.dominant_system == "BAS":
            return "approach_dominant"
        elif self.dominant_system == "BIS":
            return "avoidance_dominant"
        else:
            return "balanced"
    
    def get_ad_strategy(self) -> Dict[str, Any]:
        """Get advertising strategy based on BIS/BAS orientation."""
        if self.dominant_system == "BAS":
            return {
                'motivation_type': 'approach_dominant',
                'appeals': ['excitement', 'achievement', 'gain', 'novelty'],
                'framing': 'positive outcomes, rewards, opportunities',
                'avoid': 'fear appeals, loss framing (will be ignored)',
                'imagery': 'action, success, winning'
            }
        elif self.dominant_system == "BIS":
            return {
                'motivation_type': 'avoidance_dominant',
                'appeals': ['security', 'protection', 'risk_reduction', 'safety'],
                'framing': 'threat reduction, loss prevention, security',
                'avoid': 'excitement appeals (will increase anxiety)',
                'imagery': 'calm, protection, stability'
            }
        else:
            return {
                'motivation_type': 'balanced',
                'appeals': ['mixed approach works'],
                'framing': 'can use either depending on product category'
            }


# =============================================================================
# EVOLUTIONARY PSYCHOLOGY
# =============================================================================

class LifeHistoryStrategy(str, Enum):
    """Life History Theory strategy types."""
    FAST = "fast"      # Present focus, impulsive, scarcity response
    SLOW = "slow"      # Future focus, deliberative, investment framing
    MIXED = "mixed"


class EvolutionaryMotiveProfile(BaseModel):
    """
    Evolutionary psychology framework for consumption as signaling.
    
    Geoffrey Miller's "Central Six" - consumers use products to signal
    fitness-relevant traits more than fulfilling functional needs.
    
    Reference: Miller (2009) Spent; Nelissen & Meijers (2011)
    """
    
    life_history_strategy: LifeHistoryStrategy = Field(default=LifeHistoryStrategy.MIXED)
    
    # Fast strategy indicators
    temporal_discounting: float = Field(default=0.5, ge=0.0, le=1.0,
        description="High = prefers immediate rewards")
    urgency_response: float = Field(default=0.5, ge=0.0, le=1.0)
    impulse_purchase_tendency: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Slow strategy indicators
    delayed_gratification: float = Field(default=0.5, ge=0.0, le=1.0)
    research_before_purchase: float = Field(default=0.5, ge=0.0, le=1.0)
    quality_focus: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Signaling analysis
    primary_signaling_traits: List[str] = Field(default_factory=list,
        description="What traits this user signals through consumption")
    
    def get_ad_approach(self) -> Dict[str, Any]:
        """Get advertising approach based on life history strategy."""
        if self.life_history_strategy == LifeHistoryStrategy.FAST:
            return {
                'strategy': 'fast',
                'framing': 'scarcity, urgency, immediate reward',
                'incentives': 'lottery, sweepstakes, instant win',
                'copy_style': "Now, today, limited time, don't miss out"
            }
        elif self.life_history_strategy == LifeHistoryStrategy.SLOW:
            return {
                'strategy': 'slow',
                'framing': 'investment, long-term value, quality',
                'incentives': 'loyalty programs, compound benefits',
                'copy_style': 'Built to last, wise investment, lasting value'
            }
        else:
            return {
                'strategy': 'mixed',
                'framing': 'balanced immediate and long-term benefits',
                'incentives': 'flexible options'
            }


# =============================================================================
# MEMORY OPTIMIZATION
# =============================================================================

class MemoryOptimizationProfile(BaseModel):
    """
    Memory is not permanent storage - optimal exposure timing matters.
    
    CRITICAL: Burst campaigns are SUBOPTIMAL for long-term memory.
    Spacing effect: Up to 150% improvement with distributed scheduling.
    Reference: Cepeda et al. (2008, 2009)
    """
    
    # Retention targets
    retention_interval_days: int = Field(default=7, ge=1)
    optimal_gap_days: float = Field(default=1.0, ge=0.1)
    exposure_count: int = Field(default=3, ge=1)
    
    # Ad fatigue thresholds by platform
    exposures_this_period: int = Field(default=0, ge=0)
    fatigue_threshold: int = Field(default=4, ge=1)
    
    @property
    def is_fatigued(self) -> bool:
        """Check if user is experiencing ad fatigue."""
        return self.exposures_this_period >= self.fatigue_threshold
    
    def calculate_optimal_gap(self) -> float:
        """
        Optimal gap = approximately 10-20% of retention interval.
        
        For 1-week retention: optimal gap ≈ 1 day
        For 1-month retention: optimal gap ≈ 3-4 days
        For 1-year retention: optimal gap ≈ 21-35 days
        """
        return self.retention_interval_days * 0.15


class PeakEndOptimization(BaseModel):
    """
    Peak-End Rule for experience design.
    
    Retrospective evaluations dominated by peak intensity and ending.
    Duration is essentially irrelevant (r = .03).
    Effect size: r = .70 correlation with global evaluation
    Reference: Kahneman's colonoscopy studies; meta-analytic confirmation
    """
    
    duration_seconds: int = Field(default=15, ge=1)
    peak_position_ratio: float = Field(default=0.67, ge=0.0, le=1.0,
        description="Peak should be ~2/3 through")
    
    # Investment allocation
    peak_investment_pct: int = Field(default=70, ge=0, le=100)
    ending_investment_pct: int = Field(default=20, ge=0, le=100)
    duration_investment_pct: int = Field(default=10, ge=0, le=100)
    
    def get_structure(self) -> Dict[str, str]:
        """Get recommended ad structure based on peak-end rule."""
        peak_pos = int(self.duration_seconds * self.peak_position_ratio)
        ending_start = self.duration_seconds - 3
        
        return {
            'build_phase': f'0-{peak_pos-2}s: Rising tension/interest',
            'peak_phase': f'{peak_pos-2}-{peak_pos+2}s: Maximum emotional impact',
            'resolution_phase': f'{peak_pos+2}-{ending_start}s: Process peak',
            'ending_phase': f'{ending_start}-{self.duration_seconds}s: Positive close + CTA',
            'key_insight': 'Shorter with strong peak/end beats longer mediocre'
        }


# =============================================================================
# NONCONSCIOUS PROCESSING
# =============================================================================

class NonConsciousProcessingProfile(BaseModel):
    """
    PARADIGM SHIFT: Low-attention processing can be MORE effective
    than high-attention for emotional content.
    
    Reference: Heath, Brandt & Nairn (2006)
    Finding:
    - High attention processors: 7.3% brand shift
    - Low attention processors: 2.7% brand shift
    
    Key insight: Less awareness of emotional elements = less opportunity
    to rationally evaluate and weaken
    """
    
    optimal_attention_level: str = Field(default="moderate",
        description="low, moderate, or high")
    processing_goal: str = Field(default="brand_maintenance",
        description="emotional_branding, rational_persuasion, brand_maintenance")
    
    # Mere exposure parameters
    mere_exposure_count: int = Field(default=0, ge=0)
    optimal_exposures: int = Field(default=15, ge=1,
        description="10-20 presentations optimal, then inverted-U decline")
    
    # Wanting vs Liking indicators
    wanting_score: float = Field(default=0.5, ge=0.0, le=1.0,
        description="Mesolimbic dopamine-mediated incentive salience")
    liking_score: float = Field(default=0.5, ge=0.0, le=1.0,
        description="Hedonic impact from consummation")
    
    @property
    def wanting_liking_gap(self) -> float:
        """Gap between wanting and liking - indicates brand loyalty potential."""
        return self.wanting_score - self.liking_score


class ImplicitAttitudeProfile(BaseModel):
    """
    Implicit attitudes predict spontaneous behavior;
    explicit attitudes predict deliberate behavior (double dissociation).
    
    Reference: Perugini (2005); Plessner et al. (2004)
    """
    
    # Context determines which dominates
    time_pressure: bool = Field(default=False,
        description="<5s response window = implicit dominates")
    cognitive_load: bool = Field(default=False,
        description="Depleted = implicit dominates")
    high_involvement: bool = Field(default=False,
        description="True = explicit dominates")
    
    # Implicit measurement signals
    response_latency_ms: float = Field(default=0.0, ge=0.0,
        description="300-1000ms valid response window")
    trajectory_conflict: float = Field(default=0.0, ge=0.0, le=1.0,
        description="AUC, Max Deviation from mouse tracking")
    
    @property
    def implicit_dominates(self) -> bool:
        """Whether implicit attitudes likely dominate current behavior."""
        return (self.time_pressure or self.cognitive_load) and not self.high_involvement


# =============================================================================
# MORAL FOUNDATIONS
# =============================================================================

class MoralFoundation(str, Enum):
    """Moral Foundations Theory (Haidt & Graham)."""
    CARE_HARM = "care_harm"
    FAIRNESS_CHEATING = "fairness_cheating"
    LOYALTY_BETRAYAL = "loyalty_betrayal"
    AUTHORITY_SUBVERSION = "authority_subversion"
    SANCTITY_DEGRADATION = "sanctity_degradation"
    LIBERTY_OPPRESSION = "liberty_oppression"


class MoralFoundationsProfile(BaseModel):
    """
    Values are UPSTREAM of preferences. Knowing moral foundations
    predicts response to brand positioning better than demographics.
    
    Effect sizes: d = 0.3-0.5 for consumer behavior predictions
    Reference: Haidt & Graham; Moral Foundations Theory
    """
    
    # Foundation scores (0-1)
    care_harm: float = Field(default=0.5, ge=0.0, le=1.0)
    fairness_cheating: float = Field(default=0.5, ge=0.0, le=1.0)
    loyalty_betrayal: float = Field(default=0.5, ge=0.0, le=1.0)
    authority_subversion: float = Field(default=0.5, ge=0.0, le=1.0)
    sanctity_degradation: float = Field(default=0.5, ge=0.0, le=1.0)
    liberty_oppression: float = Field(default=0.5, ge=0.0, le=1.0)
    
    def get_dominant_foundations(self, threshold: float = 0.6) -> List[MoralFoundation]:
        """Get foundations above threshold."""
        foundations = []
        if self.care_harm > threshold:
            foundations.append(MoralFoundation.CARE_HARM)
        if self.fairness_cheating > threshold:
            foundations.append(MoralFoundation.FAIRNESS_CHEATING)
        if self.loyalty_betrayal > threshold:
            foundations.append(MoralFoundation.LOYALTY_BETRAYAL)
        if self.authority_subversion > threshold:
            foundations.append(MoralFoundation.AUTHORITY_SUBVERSION)
        if self.sanctity_degradation > threshold:
            foundations.append(MoralFoundation.SANCTITY_DEGRADATION)
        if self.liberty_oppression > threshold:
            foundations.append(MoralFoundation.LIBERTY_OPPRESSION)
        return foundations
    
    def get_appeals_for_foundation(self, foundation: MoralFoundation) -> Dict[str, Any]:
        """Get ad appeals for a specific moral foundation."""
        appeals_map = {
            MoralFoundation.CARE_HARM: {
                'sensitivity': 'Protecting others from harm',
                'appeals': ['helping', 'nurturing', 'protection of vulnerable'],
                'imagery': ['children', 'animals', 'caring interactions'],
                'products': ['health', 'safety', 'charitable']
            },
            MoralFoundation.FAIRNESS_CHEATING: {
                'sensitivity': 'Justice, equality, reciprocity',
                'appeals': ['fair pricing', 'equal treatment', 'transparency'],
                'avoid': 'Dynamic pricing visibility (triggers outrage)',
                'products': ['ethical brands', 'fair trade']
            },
            MoralFoundation.LOYALTY_BETRAYAL: {
                'sensitivity': 'Group membership, patriotism',
                'appeals': ['heritage', 'tradition', 'brand community'],
                'imagery': ['flags', 'teams', 'families', 'generations'],
                'products': ['domestic brands', 'legacy brands']
            },
            MoralFoundation.AUTHORITY_SUBVERSION: {
                'sensitivity': 'Respect for hierarchy, tradition',
                'appeals': ['expertise', 'established brands', 'endorsements'],
                'imagery': ['professionals', 'institutions', 'certificates'],
                'products': ['premium brands', 'traditional categories']
            },
            MoralFoundation.SANCTITY_DEGRADATION: {
                'sensitivity': 'Purity, contamination avoidance',
                'appeals': ['natural', 'clean', 'pure', 'organic'],
                'avoid': 'Any contamination associations',
                'products': ['food', 'beauty', 'cleaning', 'health']
            },
            MoralFoundation.LIBERTY_OPPRESSION: {
                'sensitivity': 'Freedom from constraint',
                'appeals': ['choice', 'freedom', 'no obligations'],
                'avoid': 'Controlling language, forced bundling',
                'products': ['experiences', 'travel', 'customizable']
            }
        }
        return appeals_map.get(foundation, {})


class SchwartzValueQuadrant(str, Enum):
    """Schwartz Values circumplex quadrants."""
    SELF_TRANSCENDENCE = "self_transcendence"  # universalism, benevolence
    SELF_ENHANCEMENT = "self_enhancement"       # achievement, power
    OPENNESS_TO_CHANGE = "openness_to_change"  # self-direction, stimulation
    CONSERVATION = "conservation"               # tradition, conformity, security


class SchwartzValuesProfile(BaseModel):
    """Schwartz Values mapping for ad targeting."""
    
    dominant_quadrant: SchwartzValueQuadrant = Field(
        default=SchwartzValueQuadrant.CONSERVATION)
    
    # Quadrant scores
    self_transcendence: float = Field(default=0.5, ge=0.0, le=1.0)
    self_enhancement: float = Field(default=0.5, ge=0.0, le=1.0)
    openness_to_change: float = Field(default=0.5, ge=0.0, le=1.0)
    conservation: float = Field(default=0.5, ge=0.0, le=1.0)
    
    def get_ad_recommendations(self) -> Dict[str, Any]:
        """Get ad recommendations based on values."""
        recommendations = {
            SchwartzValueQuadrant.SELF_TRANSCENDENCE: {
                'values': ['universalism', 'benevolence'],
                'products': ['organic', 'sustainable', 'charitable'],
                'appeals': ['making a difference', 'helping others', 'planet']
            },
            SchwartzValueQuadrant.SELF_ENHANCEMENT: {
                'values': ['achievement', 'power'],
                'products': ['luxury', 'status', 'performance'],
                'appeals': ['success', 'winning', 'being the best']
            },
            SchwartzValueQuadrant.OPENNESS_TO_CHANGE: {
                'values': ['self-direction', 'stimulation'],
                'products': ['innovative', 'novel', 'experiential'],
                'appeals': ['new', 'different', 'exciting', 'freedom']
            },
            SchwartzValueQuadrant.CONSERVATION: {
                'values': ['tradition', 'conformity', 'security'],
                'products': ['established brands', 'reliable', 'familiar'],
                'appeals': ['trusted', 'proven', 'safe choice', 'heritage']
            }
        }
        return recommendations.get(self.dominant_quadrant, {})


# =============================================================================
# TEMPORAL TARGETING
# =============================================================================

class ConstrualLevelProfile(BaseModel):
    """
    Match message abstraction to psychological distance.
    
    Effect size: g = 0.475 (meta-analysis); d = 0.276 (pre-registered)
    Reference: Liberman & Trope, Construal Level Theory
    """
    
    funnel_stage: str = Field(default="consideration",
        description="awareness, consideration, decision, purchase")
    psychological_distance: str = Field(default="medium",
        description="far, medium, near, very_near")
    construal_level: str = Field(default="mixed",
        description="high (abstract) or low (concrete)")
    
    # Message recommendations
    message_focus: str = Field(default="",
        description="WHY (benefits) or HOW (features)")
    language_style: str = Field(default="balanced")
    imagery_type: str = Field(default="",
        description="wide_shots/aspirational or close_ups/details")
    
    def get_recommendations(self) -> Dict[str, Any]:
        """Get construal-matched recommendations for funnel stage."""
        stage_map = {
            'awareness': {
                'psychological_distance': 'FAR',
                'construal_level': 'HIGH (abstract)',
                'message_focus': 'WHY - benefits, values, desirability',
                'language': 'Transform, achieve, experience, lifestyle',
                'imagery': 'Wide shots, aspirational, future self'
            },
            'consideration': {
                'psychological_distance': 'MEDIUM',
                'construal_level': 'MIXED',
                'message_focus': 'WHY + HOW balance',
                'language': 'Benefits supported by features'
            },
            'decision': {
                'psychological_distance': 'NEAR',
                'construal_level': 'LOW (concrete)',
                'message_focus': 'HOW - features, specs, feasibility',
                'language': 'Specific, practical, actionable',
                'imagery': 'Close-ups, details, product in use'
            },
            'purchase': {
                'psychological_distance': 'VERY NEAR',
                'construal_level': 'VERY LOW',
                'message_focus': 'ACTION - checkout, delivery, guarantee',
                'language': 'Now, today, simple steps'
            }
        }
        return stage_map.get(self.funnel_stage, stage_map['consideration'])


class TemporalPattern(BaseModel):
    """Circadian and weekly patterns for timing optimization."""
    
    # Circadian
    current_hour: int = Field(default=12, ge=0, le=23)
    cognitive_peak_hours: List[int] = Field(default_factory=lambda: [10, 11, 12, 13, 16, 17, 18])
    cognitive_trough_hours: List[int] = Field(default_factory=lambda: [4, 5, 6, 14, 15])
    
    # Weekly
    day_of_week: int = Field(default=0, ge=0, le=6,
        description="0=Monday, 6=Sunday")
    
    @property
    def is_weekend(self) -> bool:
        return self.day_of_week >= 5
    
    @property
    def is_at_cognitive_peak(self) -> bool:
        return self.current_hour in self.cognitive_peak_hours
    
    def get_message_recommendation(self) -> Dict[str, Any]:
        """Get message type based on temporal context."""
        result = {
            'is_peak': self.is_at_cognitive_peak,
            'is_weekend': self.is_weekend,
        }
        
        if self.is_at_cognitive_peak:
            result['message_type'] = 'complex'
            result['appeals'] = 'rational, evidence-based'
        else:
            result['message_type'] = 'simple'
            result['appeals'] = 'emotional, peripheral cues'
        
        if self.is_weekend:
            result['shopping_mode'] = 'hedonic'
            result['spend_lift'] = '+20-25%'
        else:
            result['shopping_mode'] = 'utilitarian'
        
        return result


# =============================================================================
# SOCIAL EFFECTS
# =============================================================================

class SocialContagionProfile(BaseModel):
    """
    Mathematical models for how preferences spread through networks.
    
    Reference: Christakis & Fowler; Centola & Macy (2007)
    """
    
    # Network position
    network_centrality: float = Field(default=0.5, ge=0.0, le=1.0)
    cluster_density: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Contagion susceptibility
    susceptibility_score: float = Field(default=0.5, ge=0.0, le=1.0,
        description="Younger, unmarried, network-peripheral = higher")
    influential_friends_count: int = Field(default=0, ge=0)
    
    # Three degrees rule weights
    degree_1_weight: float = Field(default=1.0)
    degree_2_weight: float = Field(default=0.4)
    degree_3_weight: float = Field(default=0.15)
    
    @property
    def contagion_type(self) -> str:
        """Simple vs complex contagion type."""
        # Complex contagion requires multiple exposures from different sources
        if self.cluster_density > 0.6:
            return "complex"  # Dense clusters, behavior change, expensive purchases
        else:
            return "simple"   # Information, awareness, news


class SocialIdentityProfile(BaseModel):
    """
    Brand choice signals group membership.
    
    When brands become embedded in social identity,
    loyalty transcends product features.
    
    Reference: Tajfel, Social Identity Theory
    Effect size: d = 0.32 for ingroup favoritism (212-study meta)
    """
    
    ingroup_brands: List[str] = Field(default_factory=list)
    outgroup_brands: List[str] = Field(default_factory=list)
    identity_threat_sensitivity: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Optimal distinctiveness balance
    belonging_need: float = Field(default=0.5, ge=0.0, le=1.0)
    uniqueness_need: float = Field(default=0.5, ge=0.0, le=1.0)


# =============================================================================
# PSYCHOPHYSICS
# =============================================================================

class PsychophysicsProfile(BaseModel):
    """
    The science of how physical stimuli become psychological experience.
    
    Reference: Weber-Fechner Law, Stevens' Power Law
    """
    
    # Price JND (Just Noticeable Difference)
    price_jnd_threshold: float = Field(default=0.125,
        description="10-15% for most consumers")
    
    # Fluency preferences
    name_fluency_preference: float = Field(default=0.7, ge=0.0, le=1.0,
        description="Easy-to-pronounce names preferred")
    
    # Cross-modal correspondences
    prefers_high_pitch_associations: bool = Field(default=True,
        description="small, light, premium, angular, bright")
    
    def get_price_display_recommendation(self, original_price: float) -> Dict[str, str]:
        """Get price display recommendation based on JND."""
        discount_threshold = original_price * self.price_jnd_threshold
        
        if original_price > 100:
            return {
                'display_format': 'percentage',
                'reason': 'High price items: show percentage savings'
            }
        else:
            return {
                'display_format': 'absolute',
                'reason': 'Low price items: show dollar savings',
                'min_meaningful_discount': f"${discount_threshold:.2f}"
            }


# =============================================================================
# COMPREHENSIVE USER PSYCHOLOGY PROFILE
# =============================================================================

class UserAdvertisingPsychologyProfile(BaseModel):
    """
    Comprehensive psychological profile for advertising optimization.
    
    Integrates all research domains into a unified profile for
    ad selection, message framing, and timing optimization.
    """
    
    user_id: str
    profile_id: str = Field(default_factory=lambda: f"uapp_{uuid.uuid4().hex[:12]}")
    
    # Trait-based (stable)
    linguistic_features: Optional[LinguisticFeatures] = None
    approach_avoidance: Optional[ApproachAvoidanceProfile] = None
    evolutionary_motive: Optional[EvolutionaryMotiveProfile] = None
    moral_foundations: Optional[MoralFoundationsProfile] = None
    schwartz_values: Optional[SchwartzValuesProfile] = None
    
    # State-based (dynamic)
    regulatory_focus: Optional[RegulatoryFocusProfile] = None
    cognitive_state: Optional[CognitiveStateProfile] = None
    chronotype: Optional[ChronotypeProfile] = None
    construal_level: Optional[ConstrualLevelProfile] = None
    temporal_pattern: Optional[TemporalPattern] = None
    
    # Signal-based (real-time)
    desktop_signals: Optional[DesktopBehavioralSignals] = None
    mobile_signals: Optional[MobileBehavioralSignals] = None
    
    # Processing/Memory
    nonconscious_processing: Optional[NonConsciousProcessingProfile] = None
    memory_optimization: Optional[MemoryOptimizationProfile] = None
    implicit_attitude: Optional[ImplicitAttitudeProfile] = None
    
    # Social
    social_contagion: Optional[SocialContagionProfile] = None
    social_identity: Optional[SocialIdentityProfile] = None
    
    # Meta
    overall_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    domains_populated: List[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    def get_top_recommendations(self) -> Dict[str, Any]:
        """Get top-priority advertising recommendations from all domains."""
        recommendations = {
            'user_id': self.user_id,
            'confidence': self.overall_confidence,
            'domains_used': self.domains_populated,
        }
        
        # Regulatory focus (OR = 2-6x CTR)
        if self.regulatory_focus:
            recommendations['message_frame'] = self.regulatory_focus.recommended_frame
            recommendations['regulatory_focus'] = self.regulatory_focus.focus_type
        
        # Construal level (g = 0.475)
        if self.construal_level:
            recommendations['construal_recommendations'] = self.construal_level.get_recommendations()
        
        # Cognitive state (d = 0.5-0.8)
        if self.cognitive_state:
            recommendations['message_complexity'] = self.cognitive_state.recommended_complexity
            recommendations['processing_route'] = self.cognitive_state.processing_route
        
        # Moral foundations (d = 0.3-0.5)
        if self.moral_foundations:
            dominant = self.moral_foundations.get_dominant_foundations()
            if dominant:
                recommendations['moral_appeals'] = [
                    self.moral_foundations.get_appeals_for_foundation(f)
                    for f in dominant[:2]  # Top 2 foundations
                ]
        
        # Temporal optimization
        if self.temporal_pattern:
            recommendations['temporal'] = self.temporal_pattern.get_message_recommendation()
        
        # Memory optimization
        if self.memory_optimization:
            recommendations['is_fatigued'] = self.memory_optimization.is_fatigued
            recommendations['optimal_exposure_gap'] = self.memory_optimization.optimal_gap_days
        
        return recommendations


# =============================================================================
# ETHICAL CONSTRAINTS
# =============================================================================

class EthicalConstraints(BaseModel):
    """
    Ethical guardrails for psychological targeting.
    
    Vulnerability detection should enable ad SUPPRESSION, not targeting.
    """
    
    # DO NOT
    prohibited_uses: List[str] = Field(default_factory=lambda: [
        'Use mental health indicators for ad targeting',
        'Exploit off-peak vulnerability for manipulative ads',
        'Target depleted consumers with predatory products',
        'Make individual-level assessments for high-stakes decisions',
        'Use controlling language that triggers reactance',
        'Exploit moral licensing for harmful products'
    ])
    
    # DO
    permitted_uses: List[str] = Field(default_factory=lambda: [
        'Use signals for content personalization and relevance',
        'Aggregate to population segments rather than individuals',
        'Provide transparency about personalization',
        'Validate for demographic fairness before deployment',
        'Match message complexity to cognitive state for USER benefit',
        "Support users' actual goals through appropriate recommendations"
    ])
    
    # Vulnerability protection
    vulnerability_detected: bool = Field(default=False)
    vulnerability_type: Optional[str] = None
    
    @property
    def should_suppress_ads(self) -> bool:
        """Whether to suppress ads due to detected vulnerability."""
        return self.vulnerability_detected
