# =============================================================================
# ADAM Blackboard Core Models
# Location: adam/blackboard/models/core.py
# =============================================================================

"""
BLACKBOARD CORE MODELS

Foundation models for the shared state blackboard architecture.
"""

from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================

class BlackboardZone(str, Enum):
    """The 6 logical zones of the blackboard."""
    
    ZONE_1_CONTEXT = "zone1_context"       # Request context
    ZONE_2_REASONING = "zone2_reasoning"   # Atom reasoning spaces
    ZONE_3_SYNTHESIS = "zone3_synthesis"   # Synthesis workspace
    ZONE_4_DECISION = "zone4_decision"     # Decision state
    ZONE_5_LEARNING = "zone5_learning"     # Learning signals
    ZONE_6_REVIEW_INTELLIGENCE = "zone6_review_intelligence"  # Customer intelligence from reviews


class ZoneAccessMode(str, Enum):
    """Access modes for zone operations."""
    
    READ = "read"
    WRITE = "write"
    READ_WRITE = "read_write"
    NONE = "none"


class ComponentRole(str, Enum):
    """Roles that can access the blackboard."""
    
    REQUEST_HANDLER = "request_handler"
    ATOM = "atom"
    SYNTHESIS = "synthesis"
    DECISION = "decision"
    META_LEARNER = "meta_learner"
    GRADIENT_BRIDGE = "gradient_bridge"


# =============================================================================
# ZONE ACCESS CONTROL
# =============================================================================

# Zone access matrix
ZONE_ACCESS_MATRIX: Dict[BlackboardZone, Dict[ComponentRole, ZoneAccessMode]] = {
    BlackboardZone.ZONE_1_CONTEXT: {
        ComponentRole.REQUEST_HANDLER: ZoneAccessMode.WRITE,
        ComponentRole.ATOM: ZoneAccessMode.READ,
        ComponentRole.SYNTHESIS: ZoneAccessMode.READ,
        ComponentRole.DECISION: ZoneAccessMode.READ,
        ComponentRole.META_LEARNER: ZoneAccessMode.READ,
        ComponentRole.GRADIENT_BRIDGE: ZoneAccessMode.READ,
    },
    BlackboardZone.ZONE_2_REASONING: {
        ComponentRole.REQUEST_HANDLER: ZoneAccessMode.NONE,
        ComponentRole.ATOM: ZoneAccessMode.READ_WRITE,  # Own namespace only
        ComponentRole.SYNTHESIS: ZoneAccessMode.READ,
        ComponentRole.DECISION: ZoneAccessMode.NONE,
        ComponentRole.META_LEARNER: ZoneAccessMode.READ,
        ComponentRole.GRADIENT_BRIDGE: ZoneAccessMode.READ,
    },
    BlackboardZone.ZONE_3_SYNTHESIS: {
        ComponentRole.REQUEST_HANDLER: ZoneAccessMode.NONE,
        ComponentRole.ATOM: ZoneAccessMode.NONE,
        ComponentRole.SYNTHESIS: ZoneAccessMode.READ_WRITE,
        ComponentRole.DECISION: ZoneAccessMode.READ,
        ComponentRole.META_LEARNER: ZoneAccessMode.READ,
        ComponentRole.GRADIENT_BRIDGE: ZoneAccessMode.READ,
    },
    BlackboardZone.ZONE_4_DECISION: {
        ComponentRole.REQUEST_HANDLER: ZoneAccessMode.NONE,
        ComponentRole.ATOM: ZoneAccessMode.NONE,
        ComponentRole.SYNTHESIS: ZoneAccessMode.NONE,
        ComponentRole.DECISION: ZoneAccessMode.READ_WRITE,
        ComponentRole.META_LEARNER: ZoneAccessMode.READ,
        ComponentRole.GRADIENT_BRIDGE: ZoneAccessMode.READ,
    },
    BlackboardZone.ZONE_5_LEARNING: {
        ComponentRole.REQUEST_HANDLER: ZoneAccessMode.WRITE,
        ComponentRole.ATOM: ZoneAccessMode.WRITE,
        ComponentRole.SYNTHESIS: ZoneAccessMode.WRITE,
        ComponentRole.DECISION: ZoneAccessMode.WRITE,
        ComponentRole.META_LEARNER: ZoneAccessMode.READ_WRITE,
        ComponentRole.GRADIENT_BRIDGE: ZoneAccessMode.READ_WRITE,
    },
    # Zone 6: Review Intelligence - Customer insights from product reviews
    # Readable by atoms (for evidence), synthesis, decision, and learning components
    # Writable by request handler (to populate) and review intelligence atom
    BlackboardZone.ZONE_6_REVIEW_INTELLIGENCE: {
        ComponentRole.REQUEST_HANDLER: ZoneAccessMode.WRITE,
        ComponentRole.ATOM: ZoneAccessMode.READ_WRITE,  # ReviewIntelligenceAtom writes
        ComponentRole.SYNTHESIS: ZoneAccessMode.READ,
        ComponentRole.DECISION: ZoneAccessMode.READ,
        ComponentRole.META_LEARNER: ZoneAccessMode.READ,
        ComponentRole.GRADIENT_BRIDGE: ZoneAccessMode.READ,
    },
}

# Zone TTL configurations (in seconds)
ZONE_TTLS: Dict[BlackboardZone, int] = {
    BlackboardZone.ZONE_1_CONTEXT: 300,      # Request + 5 minutes
    BlackboardZone.ZONE_2_REASONING: 1800,   # Request + 30 minutes
    BlackboardZone.ZONE_3_SYNTHESIS: 3600,   # Request + 1 hour
    BlackboardZone.ZONE_4_DECISION: 86400,   # Session + 24 hours
    BlackboardZone.ZONE_5_LEARNING: 259200,  # 72 hours
    BlackboardZone.ZONE_6_REVIEW_INTELLIGENCE: 604800,  # 7 days (reviews are semi-static)
}


def check_access(
    zone: BlackboardZone,
    role: ComponentRole,
    mode: ZoneAccessMode,
) -> bool:
    """Check if a role has the required access to a zone."""
    allowed = ZONE_ACCESS_MATRIX.get(zone, {}).get(role, ZoneAccessMode.NONE)
    
    if allowed == ZoneAccessMode.READ_WRITE:
        return True
    if allowed == mode:
        return True
    return False


# =============================================================================
# BLACKBOARD STATE
# =============================================================================

class ZoneMetadata(BaseModel):
    """Metadata for a blackboard zone."""
    
    zone: BlackboardZone
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    update_count: int = Field(default=0, ge=0)
    size_bytes: int = Field(default=0, ge=0)
    ttl_seconds: int = Field(default=300, ge=0)
    expires_at: Optional[datetime] = None
    
    def touch(self) -> None:
        """Update the last_updated timestamp."""
        self.last_updated_at = datetime.now(timezone.utc)
        self.update_count += 1


class BlackboardState(BaseModel):
    """
    Complete blackboard state for a request.
    
    This is the root object that contains all 5 zones.
    Typically stored in Redis with the request_id as key.
    """
    
    # Identity
    blackboard_id: str = Field(
        default_factory=lambda: f"bb_{uuid4().hex[:16]}"
    )
    request_id: str
    user_id: str
    session_id: Optional[str] = None
    
    # Lifecycle
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: Optional[datetime] = None
    
    # Zone metadata
    zone_metadata: Dict[BlackboardZone, ZoneMetadata] = Field(
        default_factory=dict
    )
    
    # Zone data (references to actual zone objects)
    # In Redis, these are stored as separate keys
    zone_keys: Dict[BlackboardZone, str] = Field(default_factory=dict)
    
    # Processing state
    current_phase: str = Field(default="initialization")
    atoms_completed: List[str] = Field(default_factory=list)
    atoms_in_progress: List[str] = Field(default_factory=list)
    
    # Error tracking
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    has_errors: bool = Field(default=False)
    
    def initialize_zones(self) -> None:
        """Initialize metadata for all zones."""
        for zone in BlackboardZone:
            self.zone_metadata[zone] = ZoneMetadata(
                zone=zone,
                ttl_seconds=ZONE_TTLS[zone],
                expires_at=datetime.now(timezone.utc) + timedelta(seconds=ZONE_TTLS[zone]),
            )
            self.zone_keys[zone] = f"adam:blackboard:{self.request_id}:{zone.value}"
    
    def mark_atom_started(self, atom_id: str) -> None:
        """Mark an atom as started."""
        if atom_id not in self.atoms_in_progress:
            self.atoms_in_progress.append(atom_id)
    
    def mark_atom_completed(self, atom_id: str) -> None:
        """Mark an atom as completed."""
        if atom_id in self.atoms_in_progress:
            self.atoms_in_progress.remove(atom_id)
        if atom_id not in self.atoms_completed:
            self.atoms_completed.append(atom_id)
    
    def record_error(self, component: str, error: str) -> None:
        """Record an error."""
        self.errors.append({
            "component": component,
            "error": error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self.has_errors = True
    
    def complete(self) -> None:
        """Mark the blackboard as complete."""
        self.completed_at = datetime.now(timezone.utc)
        self.current_phase = "completed"
    
    @property
    def status(self) -> str:
        """Get blackboard status based on current phase."""
        if self.completed_at is not None:
            return "completed"
        if self.has_errors:
            return "error"
        if self.current_phase == "initialization":
            return "active"
        return "active"


# =============================================================================
# BLACKBOARD EVENT
# =============================================================================

class BlackboardEventType(str, Enum):
    """Types of blackboard events."""
    
    # Lifecycle
    BLACKBOARD_CREATED = "blackboard_created"
    BLACKBOARD_COMPLETED = "blackboard_completed"
    
    # Zone updates
    ZONE_UPDATED = "zone_updated"
    
    # Atom events
    ATOM_STARTED = "atom_started"
    ATOM_COMPLETED = "atom_completed"
    ATOM_ERROR = "atom_error"
    
    # Coordination
    PRELIMINARY_SIGNAL = "preliminary_signal"
    COORDINATION_REQUEST = "coordination_request"
    
    # Synthesis
    SYNTHESIS_STARTED = "synthesis_started"
    SYNTHESIS_COMPLETED = "synthesis_completed"
    
    # Decision
    DECISION_MADE = "decision_made"
    
    # Learning
    LEARNING_SIGNAL_EMITTED = "learning_signal_emitted"


class BlackboardEvent(BaseModel):
    """Event emitted when blackboard state changes."""
    
    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex[:12]}")
    event_type: BlackboardEventType
    
    # Context
    request_id: str
    blackboard_id: str
    
    # Source
    source_component: str
    source_zone: Optional[BlackboardZone] = None
    
    # Payload
    payload: Dict[str, Any] = Field(default_factory=dict)
    
    # Timestamp
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
