# =============================================================================
# ADAM API: Desktop Behavioral Signal Collection
# Location: adam/api/behavioral/desktop_router.py
# =============================================================================

"""
DESKTOP BEHAVIORAL SIGNAL COLLECTION API

FastAPI router for collecting desktop implicit behavioral signals.

Endpoints:
- POST /cursor/trajectory - Record cursor trajectory between decision points
- POST /cursor/moves - Record cursor movements (batched)
- POST /cursor/hover - Record cursor hover events
- POST /keystroke/sequence - Record keystroke sequence
- POST /scroll - Record desktop scroll events
- POST /session/start - Start a desktop behavioral session
- POST /session/end - End a desktop behavioral session

All endpoints are designed for high-frequency, low-latency signal collection
from the JavaScript SDK.
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
import logging
import uuid

from adam.behavioral_analytics.models.events import (
    BehavioralSession,
    CursorMoveEvent,
    CursorTrajectoryEvent,
    CursorHoverEvent,
    KeystrokeEvent,
    KeystrokeSequence,
    DesktopScrollEvent,
    CursorTrajectoryType,
    DeviceType,
    SignalDomain,
)
from adam.behavioral_analytics.engine import get_behavioral_analytics_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/behavioral/desktop", tags=["behavioral", "desktop"])


# =============================================================================
# REQUEST MODELS
# =============================================================================

class CursorMoveRequest(BaseModel):
    """Batched cursor move events."""
    session_id: str
    moves: List[Dict[str, Any]]  # [{x, y, velocity, timestamp}, ...]
    

class CursorTrajectoryRequest(BaseModel):
    """Cursor trajectory between two decision points."""
    session_id: str
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    
    # Trajectory metrics
    area_under_curve: float = Field(ge=0.0)
    maximum_absolute_deviation: float = Field(ge=0.0)
    x_flips: int = Field(ge=0, default=0)
    y_flips: int = Field(ge=0, default=0)
    
    # Timing
    initiation_time_ms: int = Field(ge=0, default=0)
    movement_time_ms: int = Field(ge=0, default=0)
    
    # Context
    start_element: Optional[str] = None
    end_element: Optional[str] = None
    target_options: List[str] = Field(default_factory=list)
    chosen_option: Optional[str] = None
    
    # Raw trajectory points (sampled)
    trajectory_points: List[Tuple[float, float, int]] = Field(default_factory=list)


class CursorHoverRequest(BaseModel):
    """Cursor hover event."""
    session_id: str
    x: float
    y: float
    element_id: Optional[str] = None
    element_type: Optional[str] = None
    element_text: Optional[str] = None
    hover_duration_ms: int = Field(ge=0)
    micro_movements: int = Field(ge=0, default=0)


class KeystrokeSequenceRequest(BaseModel):
    """Keystroke sequence data."""
    session_id: str
    sequence_length: int
    input_type: str = "text"  # search, form_field, text_area
    
    # Aggregate timing
    hold_time_mean_ms: float
    hold_time_std_ms: float
    flight_time_mean_ms: float
    flight_time_std_ms: float
    
    # Derived metrics
    typing_speed_cpm: float
    pause_count: int = 0
    burst_count: int = 0
    error_count: int = 0
    error_rate: float = 0.0
    
    # Digraph patterns (anonymized)
    digraph_patterns: Dict[str, Dict[str, float]] = Field(default_factory=dict)


class DesktopScrollRequest(BaseModel):
    """Desktop scroll event."""
    session_id: str
    scroll_y: float
    scroll_x: float = 0.0
    scroll_depth_percent: float
    velocity: float
    scroll_type: str = "wheel"  # wheel, trackpad, scrollbar
    is_reversal: bool = False
    is_smooth: bool = False


class SessionStartRequest(BaseModel):
    """Start a desktop behavioral session."""
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    page_url: Optional[str] = None
    viewport_width: int = 0
    viewport_height: int = 0
    device_info: Optional[Dict[str, Any]] = None


class SessionEndRequest(BaseModel):
    """End a desktop behavioral session."""
    session_id: str
    outcome_type: Optional[str] = None
    outcome_value: Optional[float] = None


# =============================================================================
# SESSION MANAGEMENT
# =============================================================================

# In-memory session cache (production would use Redis)
_active_sessions: Dict[str, BehavioralSession] = {}


def get_or_create_session(session_id: str) -> BehavioralSession:
    """Get or create a behavioral session."""
    if session_id not in _active_sessions:
        _active_sessions[session_id] = BehavioralSession(
            session_id=session_id,
            device_type=DeviceType.DESKTOP,
            platform="desktop_web",
        )
        _active_sessions[session_id].signal_domains.append(SignalDomain.DESKTOP)
    return _active_sessions[session_id]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/session/start")
async def start_session(request: SessionStartRequest) -> Dict[str, Any]:
    """
    Start a new desktop behavioral tracking session.
    
    Returns session_id to use for subsequent events.
    """
    session_id = request.session_id or f"ds_{uuid.uuid4().hex[:16]}"
    
    session = BehavioralSession(
        session_id=session_id,
        user_id=request.user_id,
        device_type=DeviceType.DESKTOP,
        platform="desktop_web",
    )
    session.signal_domains.append(SignalDomain.DESKTOP)
    
    _active_sessions[session_id] = session
    
    logger.info(f"Started desktop session: {session_id}")
    
    return {
        "session_id": session_id,
        "started_at": datetime.utcnow().isoformat(),
        "status": "active",
    }


@router.post("/session/end")
async def end_session(
    request: SessionEndRequest,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """
    End a desktop behavioral session.
    
    Triggers async processing of collected signals.
    """
    session_id = request.session_id
    
    if session_id not in _active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = _active_sessions[session_id]
    
    # Record outcome if provided
    if request.outcome_type:
        session.outcome_type = request.outcome_type
        session.outcome_value = request.outcome_value
    
    # Queue async processing
    background_tasks.add_task(process_session_async, session)
    
    # Remove from active sessions
    del _active_sessions[session_id]
    
    logger.info(
        f"Ended desktop session: {session_id}, "
        f"events={session.total_events}"
    )
    
    return {
        "session_id": session_id,
        "ended_at": datetime.utcnow().isoformat(),
        "total_events": session.total_events,
        "status": "processing",
    }


@router.post("/cursor/trajectory")
async def record_cursor_trajectory(
    request: CursorTrajectoryRequest,
) -> Dict[str, Any]:
    """
    Record a cursor trajectory between decision points.
    
    This is the highest-value desktop signal for detecting
    decisional conflict (research effect size d=0.4-1.6).
    """
    session = get_or_create_session(request.session_id)
    
    # Determine trajectory type
    if request.area_under_curve > 0.3:
        trajectory_type = CursorTrajectoryType.COMPLEX
    elif request.area_under_curve > 0.1:
        trajectory_type = CursorTrajectoryType.CURVED
    else:
        trajectory_type = CursorTrajectoryType.DIRECT
    
    event = CursorTrajectoryEvent(
        start_x=request.start_x,
        start_y=request.start_y,
        end_x=request.end_x,
        end_y=request.end_y,
        area_under_curve=request.area_under_curve,
        maximum_absolute_deviation=request.maximum_absolute_deviation,
        x_flips=request.x_flips,
        y_flips=request.y_flips,
        initiation_time_ms=request.initiation_time_ms,
        movement_time_ms=request.movement_time_ms,
        total_time_ms=request.initiation_time_ms + request.movement_time_ms,
        trajectory_type=trajectory_type,
        trajectory_points=request.trajectory_points,
        start_element=request.start_element,
        end_element=request.end_element,
        target_options=request.target_options,
        chosen_option=request.chosen_option,
    )
    
    session.cursor_trajectories.append(event)
    
    return {
        "event_id": event.event_id,
        "conflict_score": event.conflict_score,
        "is_conflicted": event.is_conflicted,
        "trajectory_type": trajectory_type.value,
    }


@router.post("/cursor/moves")
async def record_cursor_moves(request: CursorMoveRequest) -> Dict[str, Any]:
    """
    Record batched cursor move events.
    
    For efficiency, moves are sent in batches from the SDK.
    """
    session = get_or_create_session(request.session_id)
    
    events_created = 0
    for move_data in request.moves:
        event = CursorMoveEvent(
            x=move_data.get("x", 0),
            y=move_data.get("y", 0),
            velocity=move_data.get("velocity", 0),
            velocity_x=move_data.get("velocity_x", 0),
            velocity_y=move_data.get("velocity_y", 0),
            acceleration=move_data.get("acceleration", 0),
            element_under_cursor=move_data.get("element"),
        )
        session.cursor_moves.append(event)
        events_created += 1
    
    return {
        "session_id": request.session_id,
        "events_recorded": events_created,
    }


@router.post("/cursor/hover")
async def record_cursor_hover(request: CursorHoverRequest) -> Dict[str, Any]:
    """
    Record cursor hover/dwell event.
    
    Hover duration correlates with attention and interest.
    """
    session = get_or_create_session(request.session_id)
    
    event = CursorHoverEvent(
        x=request.x,
        y=request.y,
        element_id=request.element_id,
        element_type=request.element_type,
        element_text=request.element_text,
        hover_duration_ms=request.hover_duration_ms,
        micro_movements=request.micro_movements,
    )
    
    session.cursor_hovers.append(event)
    
    return {
        "event_id": event.event_id,
        "recorded": True,
    }


@router.post("/keystroke/sequence")
async def record_keystroke_sequence(
    request: KeystrokeSequenceRequest,
) -> Dict[str, Any]:
    """
    Record keystroke sequence data.
    
    Keystroke dynamics can indicate:
    - Cognitive load (from pauses, errors)
    - Emotional arousal (from speed variance)
    - User identity (for authentication)
    """
    session = get_or_create_session(request.session_id)
    
    sequence = KeystrokeSequence(
        sequence_length=request.sequence_length,
        input_type=request.input_type,
        hold_time_mean_ms=request.hold_time_mean_ms,
        hold_time_std_ms=request.hold_time_std_ms,
        flight_time_mean_ms=request.flight_time_mean_ms,
        flight_time_std_ms=request.flight_time_std_ms,
        typing_speed_cpm=request.typing_speed_cpm,
        pause_count=request.pause_count,
        burst_count=request.burst_count,
        error_count=request.error_count,
        error_rate=request.error_rate,
        digraph_patterns=request.digraph_patterns,
    )
    
    session.keystroke_sequences.append(sequence)
    
    return {
        "event_id": sequence.event_id,
        "cognitive_load_indicator": sequence.cognitive_load_indicator,
        "emotional_arousal_indicator": sequence.emotional_arousal_indicator,
    }


@router.post("/scroll")
async def record_desktop_scroll(request: DesktopScrollRequest) -> Dict[str, Any]:
    """
    Record desktop scroll event.
    
    Desktop scrolling with precise control differs from mobile
    and provides different behavioral signals.
    """
    session = get_or_create_session(request.session_id)
    
    event = DesktopScrollEvent(
        scroll_y=request.scroll_y,
        scroll_x=request.scroll_x,
        scroll_depth_percent=request.scroll_depth_percent,
        velocity=request.velocity,
        scroll_type=request.scroll_type,
        is_reversal=request.is_reversal,
        is_smooth=request.is_smooth,
    )
    
    session.desktop_scrolls.append(event)
    
    return {
        "event_id": event.event_id,
        "recorded": True,
    }


@router.get("/session/{session_id}/stats")
async def get_session_stats(session_id: str) -> Dict[str, Any]:
    """Get current stats for an active session."""
    if session_id not in _active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = _active_sessions[session_id]
    
    return {
        "session_id": session_id,
        "total_events": session.total_events,
        "cursor_trajectories": len(session.cursor_trajectories),
        "cursor_moves": len(session.cursor_moves),
        "cursor_hovers": len(session.cursor_hovers),
        "keystroke_sequences": len(session.keystroke_sequences),
        "desktop_scrolls": len(session.desktop_scrolls),
        "has_desktop_signals": session.has_desktop_signals,
        "conflict_indicators": len(session.conflict_indicators),
    }


# =============================================================================
# BACKGROUND PROCESSING
# =============================================================================

async def process_session_async(session: BehavioralSession) -> None:
    """Process session in background."""
    try:
        engine = get_behavioral_analytics_engine()
        result = await engine.process_session(session, include_hypothesis_testing=True)
        
        logger.info(
            f"Async processing completed for session {session.session_id}: "
            f"{result.get('feature_count', 0)} features extracted"
        )
    except Exception as e:
        logger.error(f"Failed to process session {session.session_id}: {e}")
