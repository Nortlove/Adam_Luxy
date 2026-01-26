# =============================================================================
# ADAM iHeart Advertising Models
# Location: adam/platform/iheart/models/advertising.py
# =============================================================================

"""
ADVERTISING MODELS

Ad decisions, creatives, campaigns, and outcomes.

The ad decision is where ADAM's psychological intelligence
is applied. Each decision:
1. Selects mechanisms based on user profile
2. Chooses creative variant matched to personality
3. Tracks outcome for learning

Outcomes feed back to Gradient Bridge for continuous improvement.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# =============================================================================
# OUTCOME TYPES
# =============================================================================

class AdOutcomeType(str, Enum):
    """Types of ad outcomes for learning."""
    
    # Positive outcomes
    LISTEN_COMPLETE = "listen_complete"   # Listened to full ad
    CLICK = "click"                       # Clicked CTA
    CONVERSION = "conversion"             # Completed conversion action
    
    # Partial outcomes
    LISTEN_PARTIAL = "listen_partial"     # Listened to part
    
    # Negative outcomes
    SKIP = "skip"                         # Skipped ad
    MUTE = "mute"                         # Muted during ad
    TUNE_OUT = "tune_out"                 # Left station during ad


class CreativeType(str, Enum):
    """Types of audio ad creatives."""
    
    PREROLL = "preroll"
    MIDROLL = "midroll"
    POSTROLL = "postroll"
    SPONSOR = "sponsor"
    LIVE_READ = "live_read"
    DYNAMIC = "dynamic"


# =============================================================================
# CAMPAIGN MODEL
# =============================================================================

class Campaign(BaseModel):
    """
    An advertising campaign.
    
    Campaigns contain targeting criteria and creatives.
    ADAM optimizes within campaigns based on user profiles.
    """
    
    campaign_id: str = Field(default_factory=lambda: f"camp_{uuid4().hex[:12]}")
    
    # Advertiser
    brand_id: str
    brand_name: str
    advertiser_id: Optional[str] = None
    
    # Campaign metadata
    name: str
    description: Optional[str] = None
    
    # Targeting
    target_demographics: Dict[str, str] = Field(default_factory=dict)
    target_markets: List[str] = Field(default_factory=list)
    target_station_formats: List[str] = Field(default_factory=list)
    target_genres: List[str] = Field(default_factory=list)
    
    # Psychological targeting (ADAM-specific)
    target_personality_profile: Optional[Dict[str, float]] = None
    target_mechanisms: List[str] = Field(default_factory=list)
    
    # Budget and pacing
    budget_total: Optional[float] = Field(None, ge=0.0)
    budget_daily: Optional[float] = Field(None, ge=0.0)
    spend_to_date: float = Field(default=0.0, ge=0.0)
    
    # Schedule
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: bool = Field(default=True)
    
    # Performance
    impressions: int = Field(default=0, ge=0)
    clicks: int = Field(default=0, ge=0)
    conversions: int = Field(default=0, ge=0)
    ctr: float = Field(default=0.0, ge=0.0, le=1.0)
    conversion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# AD CREATIVE MODEL
# =============================================================================

class VoiceProfile(BaseModel):
    """Voice characteristics for audio creative."""
    
    voice_id: str
    name: str
    gender: str = "neutral"
    age_range: str = "adult"
    
    # Personality matching
    personality_type: str = "warm"  # "warm", "authoritative", "energetic", "calm"
    energy_level: float = Field(default=0.5, ge=0.0, le=1.0)
    warmth_level: float = Field(default=0.5, ge=0.0, le=1.0)


class AdCreative(BaseModel):
    """
    An audio ad creative with personality matching.
    
    Creatives are matched to user personality:
    - Voice selection based on user preferences
    - Copy variant based on regulatory focus
    - Music bed based on current mood
    """
    
    creative_id: str = Field(default_factory=lambda: f"crtv_{uuid4().hex[:12]}")
    campaign_id: str
    
    # Creative metadata
    name: str
    creative_type: CreativeType = Field(default=CreativeType.MIDROLL)
    duration_seconds: int = Field(ge=0)
    
    # Audio assets
    audio_url: Optional[str] = None
    ssml_template: Optional[str] = None  # For dynamic audio generation
    
    # Voice profile
    voice_profile: Optional[VoiceProfile] = None
    
    # Copy variants (for personality matching)
    copy_variants: Dict[str, str] = Field(default_factory=dict)
    # Example: {"promotion": "Get ahead with...", "prevention": "Don't miss out on..."}
    
    # Personality match profile
    target_personality: Optional[Dict[str, float]] = None
    target_mechanisms: List[str] = Field(default_factory=list)
    
    # Embedding for similarity matching
    creative_embedding: List[float] = Field(default_factory=list)
    
    # Performance by personality segment
    performance_by_segment: Dict[str, float] = Field(default_factory=dict)
    
    # Content characteristics
    energy_level: float = Field(default=0.5, ge=0.0, le=1.0)
    emotional_tone: str = Field(default="neutral")
    
    # Status
    is_active: bool = Field(default=True)
    impressions: int = Field(default=0, ge=0)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# AD DECISION MODEL
# =============================================================================

class AdDecision(BaseModel):
    """
    An ADAM ad decision.
    
    This is where psychological intelligence is applied.
    Each decision records:
    - What mechanisms were activated
    - What creative was selected
    - Why (user profile state)
    - Outcome (for learning)
    """
    
    decision_id: str = Field(default_factory=lambda: f"dec_{uuid4().hex[:16]}")
    
    # Context
    user_id: str
    session_id: str
    station_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Request context
    request_id: Optional[str] = None
    ad_slot_position: str = Field(default="midroll")  # "preroll", "midroll", "postroll"
    content_before_id: Optional[str] = None
    content_before_type: Optional[str] = None
    
    # Selection
    campaign_id: str
    creative_id: str
    
    # Psychological reasoning
    user_profile_snapshot: Dict[str, float] = Field(default_factory=dict)
    mechanisms_applied: List[str] = Field(default_factory=list)
    primary_mechanism: Optional[str] = None
    mechanism_activation_scores: Dict[str, float] = Field(default_factory=dict)
    
    # Copy/voice variant selected
    copy_variant: Optional[str] = None
    voice_variant: Optional[str] = None
    
    # Selection reasoning (for explainability)
    selection_reason: str = Field(default="default")
    selection_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Content context (for adjacency analysis)
    content_energy: Optional[float] = Field(None, ge=0.0, le=1.0)
    content_valence: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    # Outcome (filled after ad plays)
    outcome_type: Optional[AdOutcomeType] = None
    outcome_value: Optional[float] = None
    outcome_observed_at: Optional[datetime] = None
    
    # Attribution
    listen_percentage: Optional[float] = Field(None, ge=0.0, le=1.0)
    clicked: bool = Field(default=False)
    converted: bool = Field(default=False)
    
    # Learning signal emitted
    learning_signal_emitted: bool = Field(default=False)
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# =============================================================================
# AD OUTCOME MODEL
# =============================================================================

class AdOutcome(BaseModel):
    """
    Outcome of an ad decision for learning.
    
    This feeds into the Gradient Bridge to update:
    - Mechanism effectiveness for this user
    - Creative performance
    - Campaign optimization
    """
    
    outcome_id: str = Field(default_factory=lambda: f"out_{uuid4().hex[:12]}")
    decision_id: str
    
    # Outcome details
    outcome_type: AdOutcomeType
    outcome_value: float = Field(ge=0.0, le=1.0)
    
    # Behavioral details
    listen_duration_seconds: int = Field(default=0, ge=0)
    listen_percentage: float = Field(ge=0.0, le=1.0)
    clicked: bool = Field(default=False)
    click_delay_ms: Optional[int] = Field(None, ge=0)
    converted: bool = Field(default=False)
    conversion_delay_seconds: Optional[int] = Field(None, ge=0)
    conversion_value: Optional[float] = Field(None, ge=0.0)
    
    # Context at outcome
    user_state_at_outcome: Dict[str, float] = Field(default_factory=dict)
    
    # Attribution confidence
    attribution_confidence: float = Field(ge=0.0, le=1.0, default=0.8)
    
    # Mechanism effectiveness signal
    mechanism_effectiveness_signals: Dict[str, float] = Field(default_factory=dict)
    # Example: {"mimetic_desire": 0.8, "scarcity": 0.3}
    
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Learning status
    processed_by_gradient_bridge: bool = Field(default=False)
    processed_at: Optional[datetime] = None
