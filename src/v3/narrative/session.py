# =============================================================================
# ADAM v3: Narrative Session Engine
# Location: src/v3/narrative/session.py
# =============================================================================

"""
NARRATIVE SESSION ENGINE

Manages user journey narratives across sessions.

Key capabilities:
- Session continuity tracking
- Narrative arc modeling
- Story coherence maintenance
- Journey milestone detection
- Personalization memory
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel, Field
import logging
import uuid

logger = logging.getLogger(__name__)


class NarrativePhase(str, Enum):
    """Phases in the user narrative journey."""
    INTRODUCTION = "introduction"       # First encounters
    EXPLORATION = "exploration"         # Discovering preferences
    ENGAGEMENT = "engagement"           # Active interaction
    COMMITMENT = "commitment"           # Regular user
    ADVOCACY = "advocacy"               # Recommending to others
    DORMANT = "dormant"                 # Inactive period
    RETURN = "return"                   # Coming back after dormancy


class SessionEvent(BaseModel):
    """An event within a session."""
    
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    event_type: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Event details
    action: Optional[str] = None
    content_id: Optional[str] = None
    mechanism_triggered: Optional[str] = None
    
    # Outcome
    response: Optional[str] = None
    engagement_score: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Context
    context: Dict[str, Any] = Field(default_factory=dict)


class NarrativeArc(BaseModel):
    """A narrative arc representing a coherent story segment."""
    
    arc_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    user_id: str
    
    # Arc definition
    theme: str = ""
    start_date: datetime = Field(default_factory=datetime.utcnow)
    end_date: Optional[datetime] = None
    
    # Arc state
    current_phase: NarrativePhase = NarrativePhase.INTRODUCTION
    progress: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Key moments
    milestones: List[str] = Field(default_factory=list)
    turning_points: List[str] = Field(default_factory=list)
    
    # Personalization
    preferred_mechanisms: List[str] = Field(default_factory=list)
    avoided_mechanisms: List[str] = Field(default_factory=list)
    
    # Effectiveness
    engagement_trend: float = 0.0
    conversion_count: int = 0
    
    @property
    def is_active(self) -> bool:
        """Whether arc is still active."""
        return self.end_date is None


class UserSession(BaseModel):
    """A single user session."""
    
    session_id: str = Field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:12]}")
    user_id: str
    
    # Timing
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    
    # Events
    events: List[SessionEvent] = Field(default_factory=list)
    
    # Summary
    total_interactions: int = 0
    avg_engagement: float = 0.0
    mechanisms_activated: List[str] = Field(default_factory=list)
    
    # Narrative context
    active_arc_id: Optional[str] = None
    narrative_phase: NarrativePhase = NarrativePhase.EXPLORATION
    
    def add_event(self, event: SessionEvent) -> None:
        """Add an event to the session."""
        self.events.append(event)
        self.total_interactions += 1
        
        # Update average engagement
        total_engagement = sum(e.engagement_score for e in self.events)
        self.avg_engagement = total_engagement / len(self.events)
        
        # Track mechanisms
        if event.mechanism_triggered and event.mechanism_triggered not in self.mechanisms_activated:
            self.mechanisms_activated.append(event.mechanism_triggered)


class NarrativeSessionEngine:
    """
    Manages narrative continuity across user sessions.
    
    Tracks:
    - Individual sessions
    - Narrative arcs (multi-session journeys)
    - Story coherence
    - Milestone achievements
    """
    
    # Session timeout (30 minutes of inactivity)
    SESSION_TIMEOUT_MINUTES = 30
    
    # Phase thresholds
    EXPLORATION_THRESHOLD = 3   # sessions before exploration
    ENGAGEMENT_THRESHOLD = 10   # sessions before engagement
    COMMITMENT_THRESHOLD = 30   # sessions before commitment
    DORMANT_DAYS = 14           # days before dormant
    
    def __init__(self):
        # Active sessions by user
        self._active_sessions: Dict[str, UserSession] = {}
        
        # Session history by user
        self._session_history: Dict[str, List[UserSession]] = {}
        
        # Narrative arcs by user
        self._narrative_arcs: Dict[str, NarrativeArc] = {}
        
        # Statistics
        self._sessions_created = 0
        self._events_recorded = 0
    
    async def get_or_create_session(
        self,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> UserSession:
        """
        Get existing session or create new one.
        
        Args:
            user_id: User identifier
            context: Optional context for session
            
        Returns:
            Active user session
        """
        now = datetime.utcnow()
        
        # Check for existing active session
        if user_id in self._active_sessions:
            session = self._active_sessions[user_id]
            
            # Check if session timed out
            last_event_time = session.events[-1].timestamp if session.events else session.start_time
            if (now - last_event_time).total_seconds() / 60 > self.SESSION_TIMEOUT_MINUTES:
                # End old session, start new
                await self._end_session(session)
            else:
                return session
        
        # Create new session
        session = await self._create_session(user_id, context)
        return session
    
    async def _create_session(
        self,
        user_id: str,
        context: Optional[Dict[str, Any]] = None
    ) -> UserSession:
        """Create a new session."""
        # Get or create narrative arc
        arc = await self._get_or_create_arc(user_id)
        
        session = UserSession(
            user_id=user_id,
            active_arc_id=arc.arc_id,
            narrative_phase=arc.current_phase,
        )
        
        self._active_sessions[user_id] = session
        self._sessions_created += 1
        
        logger.debug(f"Created session {session.session_id} for user {user_id}")
        return session
    
    async def _end_session(self, session: UserSession) -> None:
        """End a session and archive it."""
        session.end_time = datetime.utcnow()
        
        # Archive to history
        if session.user_id not in self._session_history:
            self._session_history[session.user_id] = []
        self._session_history[session.user_id].append(session)
        
        # Update narrative arc
        await self._update_arc_from_session(session)
        
        # Remove from active
        if session.user_id in self._active_sessions:
            del self._active_sessions[session.user_id]
    
    async def _get_or_create_arc(self, user_id: str) -> NarrativeArc:
        """Get or create narrative arc for user."""
        if user_id in self._narrative_arcs:
            arc = self._narrative_arcs[user_id]
            if arc.is_active:
                return arc
        
        # Create new arc
        arc = NarrativeArc(
            user_id=user_id,
            theme="engagement_journey",
        )
        self._narrative_arcs[user_id] = arc
        return arc
    
    async def _update_arc_from_session(self, session: UserSession) -> None:
        """Update narrative arc based on completed session."""
        if session.active_arc_id not in self._narrative_arcs.values():
            return
        
        arc = self._narrative_arcs[session.user_id]
        
        # Count total sessions
        user_sessions = len(self._session_history.get(session.user_id, []))
        
        # Determine phase
        if user_sessions <= self.EXPLORATION_THRESHOLD:
            arc.current_phase = NarrativePhase.INTRODUCTION
        elif user_sessions <= self.ENGAGEMENT_THRESHOLD:
            arc.current_phase = NarrativePhase.EXPLORATION
        elif user_sessions <= self.COMMITMENT_THRESHOLD:
            arc.current_phase = NarrativePhase.ENGAGEMENT
        else:
            arc.current_phase = NarrativePhase.COMMITMENT
        
        # Update progress
        arc.progress = min(1.0, user_sessions / self.COMMITMENT_THRESHOLD)
        
        # Track preferred mechanisms
        for mech in session.mechanisms_activated:
            if mech not in arc.preferred_mechanisms:
                arc.preferred_mechanisms.append(mech)
        
        # Update engagement trend
        recent_sessions = self._session_history.get(session.user_id, [])[-5:]
        if recent_sessions:
            recent_engagement = [s.avg_engagement for s in recent_sessions]
            if len(recent_engagement) >= 2:
                arc.engagement_trend = recent_engagement[-1] - recent_engagement[0]
    
    async def record_event(
        self,
        user_id: str,
        event_type: str,
        action: Optional[str] = None,
        content_id: Optional[str] = None,
        mechanism_triggered: Optional[str] = None,
        engagement_score: float = 0.5,
        context: Optional[Dict[str, Any]] = None
    ) -> SessionEvent:
        """
        Record an event in the user's current session.
        
        Args:
            user_id: User identifier
            event_type: Type of event
            action: Action taken
            content_id: Content involved
            mechanism_triggered: Psychological mechanism
            engagement_score: Engagement level
            context: Additional context
            
        Returns:
            Recorded event
        """
        session = await self.get_or_create_session(user_id)
        
        event = SessionEvent(
            event_type=event_type,
            action=action,
            content_id=content_id,
            mechanism_triggered=mechanism_triggered,
            engagement_score=engagement_score,
            context=context or {},
        )
        
        session.add_event(event)
        self._events_recorded += 1
        
        return event
    
    async def get_narrative_context(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get full narrative context for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Narrative context for personalization
        """
        arc = self._narrative_arcs.get(user_id)
        session = self._active_sessions.get(user_id)
        history = self._session_history.get(user_id, [])
        
        return {
            "user_id": user_id,
            "narrative_phase": arc.current_phase.value if arc else "unknown",
            "journey_progress": arc.progress if arc else 0.0,
            "total_sessions": len(history),
            "preferred_mechanisms": arc.preferred_mechanisms[:5] if arc else [],
            "engagement_trend": arc.engagement_trend if arc else 0.0,
            "current_session": {
                "interactions": session.total_interactions if session else 0,
                "avg_engagement": session.avg_engagement if session else 0.0,
            } if session else None,
            "milestones": arc.milestones if arc else [],
        }
    
    async def check_for_milestone(
        self,
        user_id: str
    ) -> Optional[str]:
        """
        Check if user has achieved a milestone.
        
        Args:
            user_id: User identifier
            
        Returns:
            Milestone name if achieved, None otherwise
        """
        arc = self._narrative_arcs.get(user_id)
        if not arc:
            return None
        
        history = self._session_history.get(user_id, [])
        
        # Check milestones
        milestones_to_check = {
            "first_session": len(history) >= 1,
            "explorer": len(history) >= 5,
            "engaged_user": len(history) >= 15,
            "power_user": len(history) >= 50,
            "high_engagement": arc.engagement_trend > 0.2,
            "diverse_mechanisms": len(arc.preferred_mechanisms) >= 5,
        }
        
        for milestone, achieved in milestones_to_check.items():
            if achieved and milestone not in arc.milestones:
                arc.milestones.append(milestone)
                logger.info(f"User {user_id} achieved milestone: {milestone}")
                return milestone
        
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "sessions_created": self._sessions_created,
            "events_recorded": self._events_recorded,
            "active_sessions": len(self._active_sessions),
            "users_tracked": len(self._narrative_arcs),
        }


# Singleton instance
_engine: Optional[NarrativeSessionEngine] = None


def get_narrative_session_engine() -> NarrativeSessionEngine:
    """Get singleton Narrative Session Engine."""
    global _engine
    if _engine is None:
        _engine = NarrativeSessionEngine()
    return _engine
