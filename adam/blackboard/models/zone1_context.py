# =============================================================================
# ADAM Blackboard Zone 1: Request Context
# Location: adam/blackboard/models/zone1_context.py
# =============================================================================

"""
ZONE 1: REQUEST CONTEXT

Immutable context set once at request ingestion.

Contents:
- User profile snapshot (from Graph via InteractionBridge)
- Content context (what's being shown)
- Ad candidates (available creatives)
- Graph-derived priors (mechanism effectiveness)
- Session context (journey state)

Access: Read-only for all components after initialization.
TTL: Request duration + 5 minutes
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from adam.graph_reasoning.models.graph_context import (
    UserProfileSnapshot,
    MechanismHistory,
    StateHistory,
    ArchetypeMatch,
    GraphContext,
)


# =============================================================================
# CONTENT CONTEXT
# =============================================================================

class ContentContext(BaseModel):
    """Context about the content being shown."""
    
    content_id: Optional[str] = None
    content_type: str = Field(default="unknown")  # "audio", "display", "video"
    
    # For iHeart
    station_id: Optional[str] = None
    station_format: Optional[str] = None
    track_id: Optional[str] = None
    podcast_id: Optional[str] = None
    
    # Content characteristics
    content_energy: float = Field(ge=0.0, le=1.0, default=0.5)
    content_valence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Category/genre
    category: Optional[str] = None
    genres: List[str] = Field(default_factory=list)


# =============================================================================
# AD CANDIDATES
# =============================================================================

class AdCandidate(BaseModel):
    """An ad candidate available for selection."""
    
    candidate_id: str
    campaign_id: str
    creative_id: str
    
    # Targeting match
    targeting_score: float = Field(ge=0.0, le=1.0)
    
    # Psychological alignment
    mechanism_alignment: Dict[str, float] = Field(default_factory=dict)
    personality_alignment: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Creative characteristics
    creative_energy: float = Field(ge=0.0, le=1.0, default=0.5)
    voice_type: Optional[str] = None
    
    # Variants
    copy_variants: List[str] = Field(default_factory=list)
    
    # Performance priors
    historical_ctr: float = Field(ge=0.0, le=1.0, default=0.01)
    historical_listen_through: float = Field(ge=0.0, le=1.0, default=0.7)


class AdCandidatePool(BaseModel):
    """Pool of ad candidates for this request."""
    
    candidates: List[AdCandidate] = Field(default_factory=list)
    total_count: int = Field(default=0, ge=0)
    
    # Filtering applied
    targeting_filters: List[str] = Field(default_factory=list)
    frequency_caps_applied: bool = Field(default=False)
    
    def get_candidate(self, candidate_id: str) -> Optional[AdCandidate]:
        """Get a specific candidate."""
        for c in self.candidates:
            if c.candidate_id == candidate_id:
                return c
        return None


# =============================================================================
# USER INTELLIGENCE PACKAGE
# =============================================================================

class UserIntelligencePackage(BaseModel):
    """
    Complete intelligence about the user for this request.
    
    Assembled from graph context + real-time signals.
    """
    
    user_id: str
    
    # From Graph (via InteractionBridge)
    profile: Optional[UserProfileSnapshot] = None
    mechanism_history: Optional[MechanismHistory] = None
    state_history: Optional[StateHistory] = None
    archetype_match: Optional[ArchetypeMatch] = None
    
    # Cold start handling
    is_cold_start: bool = Field(default=True)
    cold_start_tier: str = Field(default="full")  # "full", "partial", "warm"
    
    # Real-time signals (if available)
    current_arousal: Optional[float] = Field(None, ge=0.0, le=1.0)
    current_valence: Optional[float] = Field(None, ge=0.0, le=1.0)
    session_engagement: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    # Intelligence sources available
    sources_available: List[str] = Field(default_factory=list)
    
    @classmethod
    def from_graph_context(cls, context: GraphContext) -> "UserIntelligencePackage":
        """Create from a pulled graph context."""
        return cls(
            user_id=context.user_id,
            profile=context.user_profile,
            mechanism_history=context.mechanism_history,
            state_history=context.state_history,
            archetype_match=context.archetype_match,
            is_cold_start=context.is_cold_start,
            cold_start_tier="full" if context.is_cold_start else "warm",
            sources_available=["graph"],
        )


# =============================================================================
# SESSION CONTEXT
# =============================================================================

class SessionContext(BaseModel):
    """Context about the current session."""
    
    session_id: str
    
    # Timing
    session_start: datetime
    session_duration_seconds: int = Field(default=0, ge=0)
    
    # Activity
    decisions_in_session: int = Field(default=0, ge=0)
    ads_shown: int = Field(default=0, ge=0)
    ads_clicked: int = Field(default=0, ge=0)
    
    # Content consumption
    tracks_played: int = Field(default=0, ge=0)
    tracks_skipped: int = Field(default=0, ge=0)
    
    # Session-level signals
    skip_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    engagement_trend: str = Field(default="stable")


# =============================================================================
# REQUEST CONTEXT (Zone 1)
# =============================================================================

class RequestContext(BaseModel):
    """
    Zone 1: Complete request context.
    
    This is set once at request ingestion and is read-only thereafter.
    All components read from this to get grounded context.
    """
    
    # Identity
    context_id: str = Field(default_factory=lambda: f"ctx1_{uuid4().hex[:12]}")
    request_id: str
    
    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    # User intelligence
    user_intelligence: UserIntelligencePackage
    
    # Content context
    content_context: ContentContext = Field(default_factory=ContentContext)
    
    # Ad candidates
    ad_candidates: AdCandidatePool = Field(default_factory=AdCandidatePool)
    
    # Session context
    session_context: Optional[SessionContext] = None
    
    # Request parameters
    ad_slot_type: str = Field(default="midroll")  # "preroll", "midroll", "postroll"
    latency_budget_ms: int = Field(default=100, ge=0)
    
    # Platform
    platform: str = Field(default="iheart")
    device_type: Optional[str] = None
    
    # Feature flags
    feature_flags: Dict[str, bool] = Field(default_factory=dict)
    
    # Debug mode
    debug_mode: bool = Field(default=False)
    
    def get_mechanism_prior(self, mechanism_id: str) -> float:
        """Get the best prior for a mechanism."""
        if self.user_intelligence.mechanism_history:
            mech = self.user_intelligence.mechanism_history.get_mechanism(mechanism_id)
            if mech and mech.trial_count >= 5:
                return mech.success_rate
        
        if self.user_intelligence.archetype_match:
            priors = self.user_intelligence.archetype_match.mechanism_priors
            if mechanism_id in priors:
                return priors[mechanism_id]
        
        return 0.5
