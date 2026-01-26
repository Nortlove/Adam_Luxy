# =============================================================================
# ADAM Blackboard Zone 2: Atom Reasoning Spaces
# Location: adam/blackboard/models/zone2_reasoning.py
# =============================================================================

"""
ZONE 2: ATOM REASONING SPACES

Each atom writes to its own namespace within Zone 2.
Other atoms can read to coordinate reasoning.

Contents:
- Preliminary signals (early discoveries)
- Confidence evolution (how certainty changed)
- Reasoning traces (step-by-step reasoning)
- Final outputs (atom conclusions)

Access: Write by owning atom, read by synthesis + other atoms.
TTL: Request duration + 30 minutes (for learning)
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# =============================================================================
# ATOM IDENTIFICATION
# =============================================================================

class AtomType(str, Enum):
    """Types of reasoning atoms."""
    
    # Core psychological atoms
    USER_STATE = "user_state"
    REGULATORY_FOCUS = "regulatory_focus"
    CONSTRUAL_LEVEL = "construal_level"
    PERSONALITY_EXPRESSION = "personality_expression"
    AROUSAL_DETECTION = "arousal_detection"
    
    # Mechanism atoms
    MECHANISM_SELECTION = "mechanism_selection"
    MECHANISM_ACTIVATION = "mechanism_activation"
    
    # Framing atoms
    MESSAGE_FRAMING = "message_framing"
    
    # Decision atoms
    AD_SELECTION = "ad_selection"
    COPY_GENERATION = "copy_generation"
    
    # Channel intelligence
    CHANNEL_SELECTION = "channel_selection"
    
    # Verification
    VERIFICATION = "verification"
    
    # Custom
    CUSTOM = "custom"


# =============================================================================
# PRELIMINARY SIGNALS
# =============================================================================

class SignalUrgency(str, Enum):
    """Urgency of a preliminary signal."""
    
    LOW = "low"           # Informational
    MEDIUM = "medium"     # Should influence other atoms
    HIGH = "high"         # Must be considered
    CRITICAL = "critical" # Blocks conflicting reasoning


class PreliminarySignal(BaseModel):
    """
    A preliminary discovery shared before atom completion.
    
    This enables real-time coordination between atoms.
    Example: Arousal detection shares high-arousal signal so
    Construal Level can adjust to concrete messaging.
    """
    
    signal_id: str = Field(default_factory=lambda: f"sig_{uuid4().hex[:8]}")
    
    # Source
    source_atom: AtomType
    source_atom_instance: str = ""
    
    # Signal content
    signal_type: str  # e.g., "arousal_detection", "conflict_detected"
    signal_value: Any
    
    # Metadata
    confidence: float = Field(ge=0.0, le=1.0)
    urgency: SignalUrgency = Field(default=SignalUrgency.MEDIUM)
    
    # Evidence
    evidence: List[str] = Field(default_factory=list)
    
    # Targeting (which atoms should read this)
    target_atoms: List[AtomType] = Field(default_factory=list)  # Empty = all
    
    # Timestamp
    emitted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# =============================================================================
# CONFIDENCE EVOLUTION
# =============================================================================

class ConfidencePoint(BaseModel):
    """A point in the confidence evolution."""
    
    step: int
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ConfidenceEvolution(BaseModel):
    """
    How confidence changed during atom reasoning.
    
    Used by synthesis to understand certainty trajectory.
    Atoms that quickly converge to high confidence are weighted more.
    """
    
    atom_id: str
    initial_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    final_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Evolution trace
    evolution_points: List[ConfidencePoint] = Field(default_factory=list)
    
    # Summary
    confidence_delta: float = Field(default=0.0)
    volatility: float = Field(ge=0.0, default=0.0)  # How much it fluctuated
    convergence_step: Optional[int] = None  # When it stabilized
    
    def add_point(self, confidence: float, reason: str) -> None:
        """Add a confidence point."""
        point = ConfidencePoint(
            step=len(self.evolution_points),
            confidence=confidence,
            reason=reason,
        )
        self.evolution_points.append(point)
        self.final_confidence = confidence
        self.confidence_delta = self.final_confidence - self.initial_confidence


# =============================================================================
# REASONING TRACE
# =============================================================================

class ReasoningStepType(str, Enum):
    """Types of reasoning steps."""
    
    CONTEXT_ANALYSIS = "context_analysis"
    EVIDENCE_EVALUATION = "evidence_evaluation"
    HYPOTHESIS_GENERATION = "hypothesis_generation"
    HYPOTHESIS_TESTING = "hypothesis_testing"
    CONFLICT_RESOLUTION = "conflict_resolution"
    CONCLUSION = "conclusion"


class AtomReasoningStep(BaseModel):
    """A single step in atom reasoning."""
    
    step_number: int
    step_type: ReasoningStepType
    description: str
    
    # Inputs/outputs
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    
    # Claude usage (if applicable)
    used_claude: bool = Field(default=False)
    claude_tokens_in: int = Field(default=0, ge=0)
    claude_tokens_out: int = Field(default=0, ge=0)
    
    # Timing
    duration_ms: float = Field(ge=0.0, default=0.0)


class AtomReasoningTrace(BaseModel):
    """Complete reasoning trace for an atom."""
    
    atom_id: str
    atom_type: AtomType
    
    steps: List[AtomReasoningStep] = Field(default_factory=list)
    total_steps: int = Field(default=0, ge=0)
    
    # Token usage
    total_claude_tokens_in: int = Field(default=0, ge=0)
    total_claude_tokens_out: int = Field(default=0, ge=0)
    
    # Timing
    total_duration_ms: float = Field(ge=0.0, default=0.0)


# =============================================================================
# ATOM OUTPUT
# =============================================================================

class AtomOutput(BaseModel):
    """Final output from an atom."""
    
    output_id: str = Field(default_factory=lambda: f"out_{uuid4().hex[:8]}")
    atom_id: str
    atom_type: AtomType
    
    # Primary output
    primary_result: Dict[str, Any] = Field(default_factory=dict)
    
    # Confidence
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_justification: str = ""
    
    # Mechanism recommendations (if applicable)
    recommended_mechanisms: List[str] = Field(default_factory=list)
    mechanism_scores: Dict[str, float] = Field(default_factory=dict)
    
    # State inferences (if applicable)
    inferred_states: Dict[str, float] = Field(default_factory=dict)
    
    # Warnings/notes
    warnings: List[str] = Field(default_factory=list)
    
    # Timing
    completed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# =============================================================================
# ATOM REASONING SPACE (Zone 2)
# =============================================================================

class AtomReasoningSpace(BaseModel):
    """
    Zone 2: Complete reasoning space for an atom.
    
    Each atom has its own namespace in Zone 2.
    """
    
    # Identity
    space_id: str = Field(default_factory=lambda: f"z2_{uuid4().hex[:12]}")
    request_id: str
    atom_id: str
    atom_type: AtomType
    
    # Lifecycle
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # State
    status: str = Field(default="pending")  # "pending", "running", "completed", "error"
    
    # Preliminary signals (shared early)
    preliminary_signals: List[PreliminarySignal] = Field(default_factory=list)
    
    # Signals consumed from other atoms
    consumed_signals: List[str] = Field(default_factory=list)  # Signal IDs
    
    # Confidence evolution
    confidence_evolution: Optional[ConfidenceEvolution] = None
    
    # Reasoning trace
    reasoning_trace: Optional[AtomReasoningTrace] = None
    
    # Final output
    output: Optional[AtomOutput] = None
    
    # Error (if any)
    error_message: Optional[str] = None
    
    def start(self) -> None:
        """Mark the atom as started."""
        self.started_at = datetime.now(timezone.utc)
        self.status = "running"
        self.confidence_evolution = ConfidenceEvolution(atom_id=self.atom_id)
        self.reasoning_trace = AtomReasoningTrace(
            atom_id=self.atom_id,
            atom_type=self.atom_type,
        )
    
    def emit_signal(
        self,
        signal_type: str,
        signal_value: Any,
        confidence: float,
        urgency: SignalUrgency = SignalUrgency.MEDIUM,
        evidence: Optional[List[str]] = None,
        target_atoms: Optional[List[AtomType]] = None,
    ) -> PreliminarySignal:
        """Emit a preliminary signal for other atoms."""
        signal = PreliminarySignal(
            source_atom=self.atom_type,
            source_atom_instance=self.atom_id,
            signal_type=signal_type,
            signal_value=signal_value,
            confidence=confidence,
            urgency=urgency,
            evidence=evidence or [],
            target_atoms=target_atoms or [],
        )
        self.preliminary_signals.append(signal)
        return signal
    
    def complete(self, output: AtomOutput) -> None:
        """Mark the atom as complete with output."""
        self.completed_at = datetime.now(timezone.utc)
        self.status = "completed"
        self.output = output
    
    def fail(self, error: str) -> None:
        """Mark the atom as failed."""
        self.completed_at = datetime.now(timezone.utc)
        self.status = "error"
        self.error_message = error


# =============================================================================
# ZONE 2 AGGREGATE
# =============================================================================

class Zone2Aggregate(BaseModel):
    """Aggregate view of all atom reasoning spaces."""
    
    request_id: str
    
    # All atom spaces
    atom_spaces: Dict[str, AtomReasoningSpace] = Field(default_factory=dict)
    
    # Status summary
    atoms_pending: List[str] = Field(default_factory=list)
    atoms_running: List[str] = Field(default_factory=list)
    atoms_completed: List[str] = Field(default_factory=list)
    atoms_errored: List[str] = Field(default_factory=list)
    
    # All preliminary signals (for coordination)
    all_signals: List[PreliminarySignal] = Field(default_factory=list)
    
    def get_signals_for_atom(self, atom_type: AtomType) -> List[PreliminarySignal]:
        """Get signals relevant to a specific atom type."""
        relevant = []
        for signal in self.all_signals:
            # Empty target = broadcast to all
            if not signal.target_atoms or atom_type in signal.target_atoms:
                relevant.append(signal)
        return relevant
    
    def update_from_space(self, space: AtomReasoningSpace) -> None:
        """Update aggregate from an atom space."""
        self.atom_spaces[space.atom_id] = space
        
        # Update status lists
        atom_id = space.atom_id
        for lst in [self.atoms_pending, self.atoms_running, 
                    self.atoms_completed, self.atoms_errored]:
            if atom_id in lst:
                lst.remove(atom_id)
        
        if space.status == "pending":
            self.atoms_pending.append(atom_id)
        elif space.status == "running":
            self.atoms_running.append(atom_id)
        elif space.status == "completed":
            self.atoms_completed.append(atom_id)
        elif space.status == "error":
            self.atoms_errored.append(atom_id)
        
        # Aggregate signals
        for signal in space.preliminary_signals:
            if signal.signal_id not in [s.signal_id for s in self.all_signals]:
                self.all_signals.append(signal)
