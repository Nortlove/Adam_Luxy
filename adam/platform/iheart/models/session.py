# =============================================================================
# ADAM iHeart Session Models
# Location: adam/platform/iheart/models/session.py
# =============================================================================

"""
SESSION MODELS

Listening sessions capture user behavior over time.
Sessions are the primary unit for behavioral signal extraction.

Key signals:
- Skip behavior → impatience, neuroticism
- Session duration → engagement level
- Station switching → variety seeking (openness)
- Completion rates → attention, interest
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# =============================================================================
# EVENT TYPES
# =============================================================================

class ListeningEventType(str, Enum):
    """Types of listening events for signal extraction."""
    
    # Session lifecycle
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    SESSION_PAUSE = "session_pause"
    SESSION_RESUME = "session_resume"
    
    # Content consumption
    TRACK_START = "track_start"
    TRACK_COMPLETE = "track_complete"
    TRACK_SKIP = "track_skip"
    
    PODCAST_START = "podcast_start"
    PODCAST_COMPLETE = "podcast_complete"
    PODCAST_SKIP = "podcast_skip"
    PODCAST_SEEK = "podcast_seek"
    
    # Station behavior
    STATION_TUNE_IN = "station_tune_in"
    STATION_TUNE_OUT = "station_tune_out"
    STATION_SWITCH = "station_switch"
    
    # Ad events
    AD_START = "ad_start"
    AD_COMPLETE = "ad_complete"
    AD_SKIP = "ad_skip"
    AD_CLICK = "ad_click"
    
    # Engagement signals
    VOLUME_CHANGE = "volume_change"
    MUTE = "mute"
    UNMUTE = "unmute"
    FOREGROUND = "foreground"
    BACKGROUND = "background"


class DeviceType(str, Enum):
    """Device types for context."""
    
    MOBILE_IOS = "mobile_ios"
    MOBILE_ANDROID = "mobile_android"
    WEB = "web"
    DESKTOP = "desktop"
    SMART_SPEAKER = "smart_speaker"
    CONNECTED_CAR = "connected_car"
    SMART_TV = "smart_tv"
    WEARABLE = "wearable"


# =============================================================================
# LISTENING EVENT MODEL
# =============================================================================

class ListeningEvent(BaseModel):
    """
    A granular listening event within a session.
    
    Events are the atomic behavioral signals that feed
    into psychological profile enrichment.
    """
    
    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex[:16]}")
    session_id: str
    user_id: str
    
    # Event type
    event_type: ListeningEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Content context
    content_id: Optional[str] = None
    content_type: Optional[str] = None  # "track", "podcast", "ad"
    station_id: Optional[str] = None
    
    # Event-specific data
    position_ms: Optional[int] = Field(None, ge=0)  # Position in content
    duration_ms: Optional[int] = Field(None, ge=0)  # Duration of event/content
    completion_percentage: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    # Skip-specific
    consecutive_skips: int = Field(default=0, ge=0)
    session_skip_count: int = Field(default=0, ge=0)
    
    # Audio context (from content)
    content_energy: Optional[float] = Field(None, ge=0.0, le=1.0)
    content_valence: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    # Ad-specific
    ad_decision_id: Optional[str] = None
    creative_id: Optional[str] = None
    campaign_id: Optional[str] = None
    clicked: bool = Field(default=False)
    
    # Psychological signal extraction
    signal_type: Optional[str] = None
    signal_value: Optional[float] = None
    signal_confidence: float = Field(default=0.8, ge=0.0, le=1.0)


# =============================================================================
# LISTENING SESSION MODEL
# =============================================================================

class ListeningSession(BaseModel):
    """
    A user listening session.
    
    Sessions aggregate events and provide session-level
    behavioral patterns for psychological inference.
    
    Key metrics:
    - Duration → engagement level
    - Skip rate → impatience/neuroticism
    - Genre variety → openness
    - Station loyalty → conscientiousness
    """
    
    session_id: str = Field(default_factory=lambda: f"sess_{uuid4().hex[:16]}")
    user_id: str
    
    # Session timing
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None
    duration_seconds: int = Field(default=0, ge=0)
    
    # Platform context
    platform: str = Field(default="iheart")
    device_type: DeviceType = Field(default=DeviceType.MOBILE_IOS)
    app_version: Optional[str] = None
    
    # Location context (for market matching)
    dma_code: Optional[str] = None
    timezone: Optional[str] = None
    
    # Primary listening context
    primary_station_id: Optional[str] = None
    primary_station_format: Optional[str] = None
    
    # Session-level aggregates
    tracks_played: int = Field(default=0, ge=0)
    tracks_skipped: int = Field(default=0, ge=0)
    tracks_completed: int = Field(default=0, ge=0)
    
    podcasts_started: int = Field(default=0, ge=0)
    podcasts_completed: int = Field(default=0, ge=0)
    
    ads_served: int = Field(default=0, ge=0)
    ads_completed: int = Field(default=0, ge=0)
    ads_skipped: int = Field(default=0, ge=0)
    ads_clicked: int = Field(default=0, ge=0)
    
    # Station behavior
    stations_visited: List[str] = Field(default_factory=list)
    station_switches: int = Field(default=0, ge=0)
    
    # Computed metrics
    skip_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    ad_listen_through_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Audio content exposure
    avg_content_energy: float = Field(default=0.5, ge=0.0, le=1.0)
    avg_content_valence: float = Field(default=0.5, ge=0.0, le=1.0)
    genres_consumed: List[str] = Field(default_factory=list)
    
    # Psychological signals extracted
    inferred_arousal: Optional[float] = Field(None, ge=0.0, le=1.0)
    inferred_mood: Optional[float] = Field(None, ge=0.0, le=1.0)
    inferred_engagement: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    # Events (for detailed analysis)
    event_count: int = Field(default=0, ge=0)
    events: List[ListeningEvent] = Field(default_factory=list)
    
    def compute_metrics(self) -> None:
        """Compute session-level metrics from events."""
        total_tracks = self.tracks_skipped + self.tracks_completed
        if total_tracks > 0:
            self.skip_rate = self.tracks_skipped / total_tracks
        
        total_ads = self.ads_served
        if total_ads > 0:
            self.ad_listen_through_rate = self.ads_completed / total_ads
        
        if self.ended_at and self.started_at:
            self.duration_seconds = int((self.ended_at - self.started_at).total_seconds())


# =============================================================================
# SESSION SUMMARY FOR LEARNING
# =============================================================================

class SessionPsychologicalSummary(BaseModel):
    """
    Psychological signals extracted from a session.
    
    This is what gets sent to the Gradient Bridge for
    profile enrichment.
    """
    
    session_id: str
    user_id: str
    
    # Behavioral signals
    skip_rate: float = Field(ge=0.0, le=1.0)
    engagement_duration_minutes: float = Field(ge=0.0)
    variety_seeking_score: float = Field(ge=0.0, le=1.0)  # From station switches
    
    # Inferred psychological states
    arousal_level: float = Field(ge=0.0, le=1.0)
    valence_level: float = Field(ge=0.0, le=1.0)
    
    # Big Five signal updates
    openness_signal: float = Field(default=0.0, ge=-1.0, le=1.0)
    conscientiousness_signal: float = Field(default=0.0, ge=-1.0, le=1.0)
    extraversion_signal: float = Field(default=0.0, ge=-1.0, le=1.0)
    agreeableness_signal: float = Field(default=0.0, ge=-1.0, le=1.0)
    neuroticism_signal: float = Field(default=0.0, ge=-1.0, le=1.0)
    
    # Regulatory focus signals
    promotion_focus_signal: float = Field(default=0.0, ge=-1.0, le=1.0)
    prevention_focus_signal: float = Field(default=0.0, ge=-1.0, le=1.0)
    
    # Content preferences (for future targeting)
    genre_preferences: Dict[str, float] = Field(default_factory=dict)
    station_format_preferences: Dict[str, float] = Field(default_factory=dict)
    
    # Confidence in signals
    signal_confidence: float = Field(ge=0.0, le=1.0)
    
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
