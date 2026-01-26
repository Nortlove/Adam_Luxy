# =============================================================================
# ADAM Behavioral Analytics: Event Models
# Location: adam/behavioral_analytics/models/events.py
# =============================================================================

"""
BEHAVIORAL EVENT MODELS

Pydantic models for capturing both explicit (conscious) and implicit
(nonconscious) behavioral signals from user interactions.

Based on 20 years of peer-reviewed research establishing validated
mappings between observable behaviors and psychological constructs.
"""

from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import uuid


# =============================================================================
# ENUMS
# =============================================================================

class EventType(str, Enum):
    """Types of behavioral events across all domains (mobile, desktop, media)."""
    # Explicit (conscious)
    PAGE_VIEW = "page_view"
    CLICK = "click"
    SEARCH = "search"
    ADD_TO_CART = "add_to_cart"
    REMOVE_FROM_CART = "remove_from_cart"
    PURCHASE = "purchase"
    AD_VIEW = "ad_view"
    AD_CLICK = "ad_click"
    
    # Implicit - Mobile (nonconscious)
    TOUCH = "touch"
    SWIPE = "swipe"
    SCROLL = "scroll"
    ACCELEROMETER = "accelerometer"
    GYROSCOPE = "gyroscope"
    HESITATION = "hesitation"
    RAGE_CLICK = "rage_click"
    
    # Implicit - Desktop (nonconscious)
    CURSOR_MOVE = "cursor_move"
    CURSOR_TRAJECTORY = "cursor_trajectory"
    CURSOR_HOVER = "cursor_hover"
    KEYSTROKE = "keystroke"
    KEYSTROKE_SEQUENCE = "keystroke_sequence"
    DESKTOP_SCROLL = "desktop_scroll"
    
    # Media Preferences
    MEDIA_CONSUMPTION = "media_consumption"
    MUSIC_PREFERENCE = "music_preference"
    PODCAST_PREFERENCE = "podcast_preference"


class SignalDomain(str, Enum):
    """The domain/source of behavioral signals."""
    MOBILE = "mobile"
    DESKTOP = "desktop"
    MEDIA = "media"
    EXPLICIT = "explicit"


class CursorTrajectoryType(str, Enum):
    """Classification of cursor trajectory patterns."""
    DIRECT = "direct"  # Straight line, high confidence
    CURVED = "curved"  # Single curve, some uncertainty
    COMPLEX = "complex"  # Multiple direction changes, high conflict
    EXPLORATORY = "exploratory"  # Hovering, scanning pattern


class SwipeDirection(str, Enum):
    """Swipe direction enum."""
    LEFT = "left"
    RIGHT = "right"
    UP = "up"
    DOWN = "down"
    DIAGONAL = "diagonal"


class DeviceType(str, Enum):
    """Device type."""
    MOBILE = "mobile"
    TABLET = "tablet"
    DESKTOP = "desktop"


class SessionPhase(str, Enum):
    """Phase within a user session."""
    ARRIVAL = "arrival"
    BROWSING = "browsing"
    CONSIDERATION = "consideration"
    DECISION = "decision"
    POST_DECISION = "post_decision"


# =============================================================================
# EXPLICIT EVENT MODELS
# =============================================================================

class PageViewEvent(BaseModel):
    """Page view event with engagement metrics."""
    
    event_id: str = Field(default_factory=lambda: f"pv_{uuid.uuid4().hex[:12]}")
    event_type: EventType = EventType.PAGE_VIEW
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Page info
    url: str
    page_type: str  # "product", "category", "checkout", "cart", etc.
    
    # Engagement metrics
    dwell_time_ms: int = 0
    scroll_depth_percent: float = 0.0
    visible_time_ms: int = 0  # Time page was in foreground
    
    # Context
    referrer: Optional[str] = None
    position_in_session: int = 1


class ClickEvent(BaseModel):
    """Click/tap event with position and context."""
    
    event_id: str = Field(default_factory=lambda: f"ck_{uuid.uuid4().hex[:12]}")
    event_type: EventType = EventType.CLICK
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Element info
    element_type: str  # "button", "link", "product", "image"
    element_id: Optional[str] = None
    element_text: Optional[str] = None
    
    # Position
    x: int
    y: int
    viewport_x: int = 0
    viewport_y: int = 0
    
    # Context
    page_url: str
    time_on_page_ms: int = 0


class CartEvent(BaseModel):
    """Cart add/remove event."""
    
    event_id: str = Field(default_factory=lambda: f"ct_{uuid.uuid4().hex[:12]}")
    event_type: EventType  # ADD_TO_CART or REMOVE_FROM_CART
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Product info
    product_id: str
    product_category: str
    product_price: float
    quantity: int = 1
    
    # Context
    source_page: str
    time_to_add_ms: int = 0  # Time from page view to add


class PurchaseEvent(BaseModel):
    """Purchase completion event."""
    
    event_id: str = Field(default_factory=lambda: f"pu_{uuid.uuid4().hex[:12]}")
    event_type: EventType = EventType.PURCHASE
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Order info
    order_id: str
    total_amount: float
    item_count: int
    product_ids: List[str] = Field(default_factory=list)
    categories: List[str] = Field(default_factory=list)
    
    # Journey metrics
    session_duration_ms: int = 0
    pages_viewed: int = 0
    cart_views_before_purchase: int = 0


class AdEvent(BaseModel):
    """Ad view or click event."""
    
    event_id: str = Field(default_factory=lambda: f"ad_{uuid.uuid4().hex[:12]}")
    event_type: EventType  # AD_VIEW or AD_CLICK
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Ad info
    ad_id: str
    creative_id: str
    campaign_id: str
    placement: str
    
    # Engagement
    view_duration_ms: int = 0
    viewability_percent: float = 0.0  # Percent of ad visible
    
    # Response (for clicks)
    response_time_ms: Optional[int] = None


# =============================================================================
# IMPLICIT EVENT MODELS
# =============================================================================

class TouchEvent(BaseModel):
    """
    Touch/tap event with pressure and timing.
    
    Research: Touch pressure correlates with emotional arousal (89% accuracy)
    """
    
    event_id: str = Field(default_factory=lambda: f"tc_{uuid.uuid4().hex[:12]}")
    event_type: EventType = EventType.TOUCH
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Position
    x: float
    y: float
    
    # Pressure (0-1 normalized)
    pressure: float = 0.5
    
    # Touch area
    radius_x: float = 10.0
    radius_y: float = 10.0
    
    # Timing
    duration_ms: int = 0
    time_since_last_touch_ms: Optional[int] = None
    
    # Context
    target_element: Optional[str] = None


class SwipeEvent(BaseModel):
    """
    Swipe gesture event.
    
    Research:
    - Swipe directness correlates with decision confidence (r=0.30)
    - Right swipe activates approach motivation (d=0.35)
    """
    
    event_id: str = Field(default_factory=lambda: f"sw_{uuid.uuid4().hex[:12]}")
    event_type: EventType = EventType.SWIPE
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Start/end positions
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    
    # Derived metrics
    direction: SwipeDirection
    
    # Path efficiency (1.0 = perfectly straight)
    directness: float = 1.0
    
    # Velocity
    velocity: float  # pixels/second
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    
    # Timing
    duration_ms: int
    
    # Path details
    path_length: float  # Total distance traveled
    direction_changes: int = 0  # Number of direction reversals


class ScrollEvent(BaseModel):
    """
    Scroll behavior event.
    
    Research: Scroll velocity and pauses indicate engagement depth.
    """
    
    event_id: str = Field(default_factory=lambda: f"sc_{uuid.uuid4().hex[:12]}")
    event_type: EventType = EventType.SCROLL
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Scroll position
    scroll_y: float
    scroll_x: float = 0.0
    scroll_depth_percent: float
    
    # Velocity
    velocity: float  # pixels/second
    
    # Pattern flags
    is_pause: bool = False  # Pause/fixation detected
    pause_duration_ms: int = 0
    is_reversal: bool = False  # Scrolled back up


class SensorSample(BaseModel):
    """
    Device sensor sample (accelerometer/gyroscope).
    
    Research: Accelerometer variance correlates with emotional arousal (87-89%)
    """
    
    sample_id: str = Field(default_factory=lambda: f"ss_{uuid.uuid4().hex[:12]}")
    sensor_type: EventType  # ACCELEROMETER or GYROSCOPE
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # 3-axis values
    x: float
    y: float
    z: float
    
    # Derived
    magnitude: float = 0.0  # sqrt(x² + y² + z²)
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.magnitude == 0.0:
            self.magnitude = (self.x**2 + self.y**2 + self.z**2) ** 0.5


class HesitationEvent(BaseModel):
    """
    Detected hesitation event.
    
    Research: Pre-CTA hesitation indicates decision uncertainty.
    """
    
    event_id: str = Field(default_factory=lambda: f"hs_{uuid.uuid4().hex[:12]}")
    event_type: EventType = EventType.HESITATION
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Context
    element_type: str  # "cta", "form", "product"
    element_id: Optional[str] = None
    
    # Hesitation metrics
    dwell_time_ms: int
    cursor_movements: int = 0
    false_starts: int = 0  # Moved toward then away
    
    # Threshold that triggered detection
    threshold_exceeded_by_ms: int = 0


class RageClickEvent(BaseModel):
    """
    Detected rage click event.
    
    Research: Strong correlation with user-reported frustration.
    """
    
    event_id: str = Field(default_factory=lambda: f"rc_{uuid.uuid4().hex[:12]}")
    event_type: EventType = EventType.RAGE_CLICK
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Pattern
    click_count: int
    area_radius: float  # Pixel radius of click cluster
    duration_ms: int  # Time span of clicks
    
    # Context
    target_element: Optional[str] = None
    page_url: str


# =============================================================================
# IMPLICIT EVENT MODELS - DESKTOP
# =============================================================================

class CursorMoveEvent(BaseModel):
    """
    Mouse cursor movement event.
    
    Research: Cursor position correlates with gaze (r=0.84) and 
    can reveal attention patterns without eye tracking.
    """
    
    event_id: str = Field(default_factory=lambda: f"cm_{uuid.uuid4().hex[:12]}")
    event_type: EventType = EventType.CURSOR_MOVE
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Position
    x: float
    y: float
    viewport_x: float = 0.0
    viewport_y: float = 0.0
    
    # Velocity (pixels/second)
    velocity: float = 0.0
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    
    # Acceleration (pixels/second²)
    acceleration: float = 0.0
    
    # Context
    element_under_cursor: Optional[str] = None
    page_url: Optional[str] = None
    
    # Timing
    time_since_last_move_ms: Optional[int] = None


class CursorTrajectoryEvent(BaseModel):
    """
    Complete cursor trajectory between two decision points.
    
    Research:
    - Area Under Curve (AUC) correlates with decisional conflict (d=0.4-1.6)
    - Maximum Absolute Deviation (MAD) indicates attraction to non-chosen option
    - x-flips reveal conflict during decision process
    - Initiation time indicates automatic vs deliberative processing
    
    Based on mouse-tracking paradigm (Freeman & Ambady, 2010; Spivey et al., 2005)
    """
    
    event_id: str = Field(default_factory=lambda: f"ct_{uuid.uuid4().hex[:12]}")
    event_type: EventType = EventType.CURSOR_TRAJECTORY
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Start/end positions
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    
    # Core trajectory metrics
    area_under_curve: float = 0.0  # AUC: deviation from ideal straight line
    maximum_absolute_deviation: float = 0.0  # MAD: max perpendicular deviation
    
    # Direction change metrics
    x_flips: int = 0  # Number of times trajectory reversed x-direction
    y_flips: int = 0  # Number of times trajectory reversed y-direction
    
    # Velocity metrics
    velocity_minima: int = 0  # Points where velocity reached local minimum
    average_velocity: float = 0.0
    peak_velocity: float = 0.0
    velocity_at_decision: float = 0.0  # Velocity at moment of click
    
    # Timing
    initiation_time_ms: int = 0  # Time from stimulus to movement start
    movement_time_ms: int = 0  # Total movement duration
    
    @property
    def total_time_ms(self) -> int:
        """Total time: initiation + movement."""
        return self.initiation_time_ms + self.movement_time_ms
    
    # Trajectory classification
    trajectory_type: CursorTrajectoryType = CursorTrajectoryType.DIRECT
    
    # Raw trajectory points (sampled, not every point)
    trajectory_points: List[Tuple[float, float, int]] = Field(default_factory=list)
    # List of (x, y, timestamp_offset_ms)
    
    # Context
    start_element: Optional[str] = None
    end_element: Optional[str] = None
    target_options: List[str] = Field(default_factory=list)  # What options were available
    chosen_option: Optional[str] = None
    
    @property
    def conflict_score(self) -> float:
        """
        Composite conflict score from trajectory metrics.
        
        Higher values indicate greater decisional conflict.
        Normalized to 0-1 scale.
        """
        # Weight factors based on research effect sizes
        auc_contribution = min(1.0, self.area_under_curve / 0.5) * 0.35
        mad_contribution = min(1.0, self.maximum_absolute_deviation / 0.3) * 0.25
        xflip_contribution = min(1.0, self.x_flips / 4) * 0.25
        initiation_contribution = min(1.0, self.initiation_time_ms / 800) * 0.15
        
        return auc_contribution + mad_contribution + xflip_contribution + initiation_contribution
    
    @property
    def is_conflicted(self) -> bool:
        """Whether trajectory indicates significant conflict (d > 0.4)."""
        return self.conflict_score > 0.35


class CursorHoverEvent(BaseModel):
    """
    Cursor hover/dwell event over an element.
    
    Research: Hover duration correlates with attention and interest.
    Pausing over elements reveals information seeking behavior.
    """
    
    event_id: str = Field(default_factory=lambda: f"ch_{uuid.uuid4().hex[:12]}")
    event_type: EventType = EventType.CURSOR_HOVER
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Position
    x: float
    y: float
    
    # Element hovered
    element_id: Optional[str] = None
    element_type: Optional[str] = None  # "button", "product", "link", "image"
    element_text: Optional[str] = None
    
    # Hover metrics
    hover_duration_ms: int
    micro_movements: int = 0  # Small movements while hovering
    
    # Context
    page_url: Optional[str] = None
    position_in_sequence: int = 1  # Which hover in session


class KeystrokeEvent(BaseModel):
    """
    Individual keystroke event.
    
    Research:
    - Hold time (key down to key up) reveals typing rhythm
    - Flight time (key up to next key down) reveals fluency
    - Combined patterns enable user authentication (EER < 1%)
    - Typing speed changes correlate with emotional arousal
    """
    
    event_id: str = Field(default_factory=lambda: f"ks_{uuid.uuid4().hex[:12]}")
    event_type: EventType = EventType.KEYSTROKE
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Key info (anonymized - no actual key value for privacy)
    key_category: str  # "letter", "number", "punctuation", "space", "special", "backspace"
    is_modifier: bool = False
    
    # Timing (in milliseconds)
    hold_time_ms: int  # Duration key was held
    flight_time_ms: Optional[int] = None  # Time since last key up
    
    # Pressure (if available)
    pressure: Optional[float] = None
    
    # Error detection
    is_error_correction: bool = False  # Was this a backspace/delete
    
    # Context
    input_field_type: Optional[str] = None  # "search", "form", "text", "password"


class KeystrokeSequence(BaseModel):
    """
    Sequence of keystrokes for pattern analysis.
    
    Research:
    - Digraph patterns (two-key combinations) are highly distinctive
    - Typing rhythm is stable within individuals, variable across
    - Can detect emotional states from typing pattern changes
    - Authentication systems achieve EER < 1%
    """
    
    event_id: str = Field(default_factory=lambda: f"sq_{uuid.uuid4().hex[:12]}")
    event_type: EventType = EventType.KEYSTROKE_SEQUENCE
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Sequence metadata
    sequence_length: int
    input_type: str  # "search", "form_field", "text_area"
    
    # Aggregate timing statistics
    hold_time_mean_ms: float
    hold_time_std_ms: float
    flight_time_mean_ms: float
    flight_time_std_ms: float
    
    # Derived metrics
    typing_speed_cpm: float  # Characters per minute
    pause_count: int = 0  # Number of pauses > 500ms
    burst_count: int = 0  # Rapid typing bursts
    
    # Error metrics
    error_count: int = 0  # Backspace/delete presses
    error_rate: float = 0.0  # Errors / total keystrokes
    
    # Digraph patterns (anonymized)
    # Dict of digraph_type -> timing (e.g., "letter_letter": {"mean": 120, "std": 30})
    digraph_patterns: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    
    # Rhythm metrics
    rhythm_regularity: float = 0.0  # 0 = irregular, 1 = metronomic
    speed_variance: float = 0.0  # Variance in typing speed over sequence
    
    # Individual keystrokes (if detailed analysis needed)
    keystrokes: List[KeystrokeEvent] = Field(default_factory=list)
    
    @property
    def cognitive_load_indicator(self) -> float:
        """
        Estimate cognitive load from typing patterns.
        
        High load indicated by:
        - Increased hold times
        - More pauses
        - Higher error rate
        - Lower rhythm regularity
        """
        pause_factor = min(1.0, self.pause_count / 5) * 0.3
        error_factor = min(1.0, self.error_rate * 5) * 0.3
        rhythm_factor = (1 - self.rhythm_regularity) * 0.2
        hold_factor = min(1.0, self.hold_time_mean_ms / 200) * 0.2
        
        return pause_factor + error_factor + rhythm_factor + hold_factor
    
    @property
    def emotional_arousal_indicator(self) -> float:
        """
        Estimate emotional arousal from typing patterns.
        
        High arousal indicated by:
        - Faster typing
        - More variable timing
        - Burst patterns
        """
        speed_factor = min(1.0, self.typing_speed_cpm / 400) * 0.4
        variance_factor = min(1.0, self.speed_variance / 50) * 0.3
        burst_factor = min(1.0, self.burst_count / 5) * 0.3
        
        return speed_factor + variance_factor + burst_factor


class DesktopScrollEvent(BaseModel):
    """
    Desktop scroll event (mouse wheel or trackpad).
    
    Extends base ScrollEvent with desktop-specific metrics.
    
    Research: Desktop scroll patterns differ from mobile due to
    precision scrolling capability and different interaction context.
    """
    
    event_id: str = Field(default_factory=lambda: f"ds_{uuid.uuid4().hex[:12]}")
    event_type: EventType = EventType.DESKTOP_SCROLL
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Scroll position
    scroll_y: float
    scroll_x: float = 0.0
    scroll_depth_percent: float
    
    # Velocity
    velocity: float  # pixels/second
    
    # Desktop-specific: scroll type
    scroll_type: str = "wheel"  # "wheel", "trackpad", "scrollbar", "keyboard"
    
    # Wheel-specific metrics
    delta_y: float = 0.0  # Raw wheel delta
    delta_x: float = 0.0
    delta_mode: int = 0  # 0=pixels, 1=lines, 2=pages
    
    # Pattern flags
    is_pause: bool = False
    pause_duration_ms: int = 0
    is_reversal: bool = False
    
    # Smoothness (trackpad vs discrete wheel)
    is_smooth: bool = False  # True for trackpad, false for notched wheel
    acceleration_applied: bool = False


# =============================================================================
# SESSION MODEL
# =============================================================================

class BehavioralSession(BaseModel):
    """
    A complete behavioral session aggregating all events across all domains.
    
    This is the UNIFIED session model that contains mobile, desktop, and
    media preference signals. All signal types flow through the same 
    processing pipeline and contribute to psychological inferences.
    
    Contains both raw events and computed features for analysis.
    """
    
    session_id: str = Field(default_factory=lambda: f"bs_{uuid.uuid4().hex[:12]}")
    user_id: Optional[str] = None  # None for anonymous
    device_id: str
    
    # Session timing
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration_ms: int = 0
    
    # Device context
    device_type: DeviceType = DeviceType.MOBILE
    platform: str = "unknown"  # "ios", "android", "web", "desktop_web"
    
    # Session phase
    current_phase: SessionPhase = SessionPhase.ARRIVAL
    
    # Signal domain tracking
    signal_domains: List[SignalDomain] = Field(default_factory=list)
    
    # ==========================================================================
    # EXPLICIT EVENTS (conscious actions)
    # ==========================================================================
    page_views: List[PageViewEvent] = Field(default_factory=list)
    clicks: List[ClickEvent] = Field(default_factory=list)
    cart_events: List[CartEvent] = Field(default_factory=list)
    purchases: List[PurchaseEvent] = Field(default_factory=list)
    ad_events: List[AdEvent] = Field(default_factory=list)
    
    # ==========================================================================
    # IMPLICIT EVENTS - MOBILE (nonconscious touch/gesture signals)
    # ==========================================================================
    touches: List[TouchEvent] = Field(default_factory=list)
    swipes: List[SwipeEvent] = Field(default_factory=list)
    scrolls: List[ScrollEvent] = Field(default_factory=list)
    sensor_samples: List[SensorSample] = Field(default_factory=list)
    hesitations: List[HesitationEvent] = Field(default_factory=list)
    rage_clicks: List[RageClickEvent] = Field(default_factory=list)
    
    # ==========================================================================
    # IMPLICIT EVENTS - DESKTOP (nonconscious cursor/keyboard signals)
    # ==========================================================================
    cursor_moves: List[CursorMoveEvent] = Field(default_factory=list)
    cursor_trajectories: List[CursorTrajectoryEvent] = Field(default_factory=list)
    cursor_hovers: List[CursorHoverEvent] = Field(default_factory=list)
    keystrokes: List[KeystrokeEvent] = Field(default_factory=list)
    keystroke_sequences: List[KeystrokeSequence] = Field(default_factory=list)
    desktop_scrolls: List[DesktopScrollEvent] = Field(default_factory=list)
    
    # ==========================================================================
    # COMPUTED FEATURES (populated by feature extractors)
    # ==========================================================================
    features: Dict[str, float] = Field(default_factory=dict)
    
    # Domain-specific feature groups (for debugging/analysis)
    mobile_features: Dict[str, float] = Field(default_factory=dict)
    desktop_features: Dict[str, float] = Field(default_factory=dict)
    
    # ==========================================================================
    # OUTCOME TRACKING
    # ==========================================================================
    outcome_type: Optional[str] = None
    outcome_value: Optional[float] = None
    outcome_recorded_at: Optional[datetime] = None
    
    @property
    def total_events(self) -> int:
        """Total number of events in session across all domains."""
        return (
            # Explicit
            len(self.page_views) +
            len(self.clicks) +
            len(self.cart_events) +
            len(self.purchases) +
            len(self.ad_events) +
            # Mobile implicit
            len(self.touches) +
            len(self.swipes) +
            len(self.scrolls) +
            len(self.sensor_samples) +
            len(self.hesitations) +
            len(self.rage_clicks) +
            # Desktop implicit
            len(self.cursor_moves) +
            len(self.cursor_trajectories) +
            len(self.cursor_hovers) +
            len(self.keystrokes) +
            len(self.keystroke_sequences) +
            len(self.desktop_scrolls)
        )
    
    @property
    def is_known_user(self) -> bool:
        """Whether this is a known (logged in) user."""
        return self.user_id is not None
    
    @property
    def has_implicit_signals(self) -> bool:
        """Whether session has any implicit behavioral signals."""
        return self.has_mobile_signals or self.has_desktop_signals
    
    @property
    def has_mobile_signals(self) -> bool:
        """Whether session has mobile implicit signals."""
        return (
            len(self.touches) > 0 or
            len(self.swipes) > 0 or
            len(self.scrolls) > 0 or
            len(self.sensor_samples) > 0
        )
    
    @property
    def has_desktop_signals(self) -> bool:
        """Whether session has desktop implicit signals."""
        return (
            len(self.cursor_moves) > 0 or
            len(self.cursor_trajectories) > 0 or
            len(self.cursor_hovers) > 0 or
            len(self.keystrokes) > 0 or
            len(self.keystroke_sequences) > 0 or
            len(self.desktop_scrolls) > 0
        )
    
    @property
    def primary_signal_domain(self) -> SignalDomain:
        """Determine the primary signal domain for this session."""
        if self.has_mobile_signals and not self.has_desktop_signals:
            return SignalDomain.MOBILE
        elif self.has_desktop_signals and not self.has_mobile_signals:
            return SignalDomain.DESKTOP
        elif self.has_mobile_signals and self.has_desktop_signals:
            # Hybrid session - use device type as tiebreaker
            return SignalDomain.MOBILE if self.device_type == DeviceType.MOBILE else SignalDomain.DESKTOP
        else:
            return SignalDomain.EXPLICIT
    
    @property
    def conflict_indicators(self) -> List[Dict[str, Any]]:
        """Get all decisional conflict indicators from the session."""
        conflicts = []
        
        # Desktop: cursor trajectories with conflict
        for trajectory in self.cursor_trajectories:
            if trajectory.is_conflicted:
                conflicts.append({
                    "source": "cursor_trajectory",
                    "event_id": trajectory.event_id,
                    "conflict_score": trajectory.conflict_score,
                    "auc": trajectory.area_under_curve,
                    "mad": trajectory.maximum_absolute_deviation,
                    "x_flips": trajectory.x_flips,
                    "target_options": trajectory.target_options,
                })
        
        # Mobile: hesitations
        for hesitation in self.hesitations:
            if hesitation.element_type == "cta":
                conflicts.append({
                    "source": "pre_cta_hesitation",
                    "event_id": hesitation.event_id,
                    "dwell_time_ms": hesitation.dwell_time_ms,
                    "false_starts": hesitation.false_starts,
                })
        
        return conflicts


# =============================================================================
# OUTCOME MODELS
# =============================================================================

class OutcomeType(str, Enum):
    """Types of outcomes to track."""
    CONVERSION = "conversion"
    AD_CLICK = "ad_click"
    AD_ENGAGEMENT = "ad_engagement"
    ABANDONMENT = "abandonment"
    BOUNCE = "bounce"
    RETURN_VISIT = "return_visit"


class BehavioralOutcome(BaseModel):
    """
    An outcome event for learning.
    
    Links behavioral signals to observed outcomes for
    hypothesis testing and knowledge validation.
    """
    
    outcome_id: str = Field(default_factory=lambda: f"bo_{uuid.uuid4().hex[:12]}")
    session_id: str
    user_id: Optional[str] = None
    decision_id: Optional[str] = None
    
    # Outcome
    outcome_type: OutcomeType
    outcome_value: float  # 1.0 for binary, amount for continuous
    outcome_label: str  # Human readable
    
    # Attribution window
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    attribution_window_hours: int = 24
    
    # Context at outcome
    context: Dict[str, Any] = Field(default_factory=dict)
