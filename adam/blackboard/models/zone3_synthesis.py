# =============================================================================
# ADAM Blackboard Zone 3: Synthesis Workspace
# Location: adam/blackboard/models/zone3_synthesis.py
# =============================================================================

"""
ZONE 3: SYNTHESIS WORKSPACE

Aggregated reasoning from all atoms, conflict resolution, and recommendations.

Contents:
- Atom aggregation (combined outputs)
- Conflict resolution log
- Mechanism weights (final recommendations)
- Unified psychological assessment

Access: Write by synthesis, read by decision + learners.
TTL: Request duration + 1 hour (for attribution)
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# =============================================================================
# ATOM AGGREGATION
# =============================================================================

class AtomContribution(BaseModel):
    """Contribution from a single atom to synthesis."""
    
    atom_id: str
    atom_type: str
    
    # Core contribution
    primary_output: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Mechanism recommendations
    mechanism_scores: Dict[str, float] = Field(default_factory=dict)
    
    # Weight in synthesis
    synthesis_weight: float = Field(ge=0.0, le=1.0, default=1.0)
    weight_reason: str = ""
    
    # Conflict flags
    conflicts_with: List[str] = Field(default_factory=list)


class AtomAggregation(BaseModel):
    """Aggregated contributions from all atoms."""
    
    aggregation_id: str = Field(default_factory=lambda: f"agg_{uuid4().hex[:8]}")
    request_id: str
    
    # Contributions
    contributions: List[AtomContribution] = Field(default_factory=list)
    
    # Summary
    total_atoms: int = Field(default=0, ge=0)
    completed_atoms: int = Field(default=0, ge=0)
    errored_atoms: int = Field(default=0, ge=0)
    
    # Aggregated mechanism scores (weighted average)
    aggregated_mechanism_scores: Dict[str, float] = Field(default_factory=dict)
    
    # Aggregated confidence
    aggregated_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Token usage across all atoms
    total_tokens_in: int = Field(default=0, ge=0)
    total_tokens_out: int = Field(default=0, ge=0)


# =============================================================================
# CONFLICT RESOLUTION
# =============================================================================

class ConflictType(str, Enum):
    """Types of conflicts between atoms."""
    
    CONTRADICTORY_SIGNALS = "contradictory_signals"  # Atoms disagree on a value
    INCOMPATIBLE_MECHANISMS = "incompatible_mechanisms"  # Mechanisms that don't work together
    CONFIDENCE_DIVERGENCE = "confidence_divergence"  # Large confidence gaps
    STATE_INCONSISTENCY = "state_inconsistency"  # Inconsistent state inferences


class ConflictResolutionStrategy(str, Enum):
    """Strategies for resolving conflicts."""
    
    CONFIDENCE_WEIGHTED = "confidence_weighted"  # Weight by confidence
    RECENCY_WEIGHTED = "recency_weighted"  # Prefer more recent
    EVIDENCE_COUNT = "evidence_count"  # Prefer more evidence
    DOMAIN_EXPERTISE = "domain_expertise"  # Prefer domain expert atom
    ESCALATE_TO_CLAUDE = "escalate_to_claude"  # Use Claude to resolve
    CONSERVATIVE = "conservative"  # Take the safer option


class ConflictInstance(BaseModel):
    """A detected conflict between atoms."""
    
    conflict_id: str = Field(default_factory=lambda: f"conf_{uuid4().hex[:8]}")
    conflict_type: ConflictType
    
    # Parties
    atom_a: str
    atom_b: str
    
    # What's conflicting
    conflicting_field: str
    value_a: Any
    value_b: Any
    confidence_a: float = Field(ge=0.0, le=1.0)
    confidence_b: float = Field(ge=0.0, le=1.0)
    
    # Resolution
    resolved: bool = Field(default=False)
    resolution_strategy: Optional[ConflictResolutionStrategy] = None
    resolved_value: Optional[Any] = None
    resolution_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    resolution_reason: str = ""
    
    # Timing
    detected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    resolved_at: Optional[datetime] = None


class ConflictResolution(BaseModel):
    """Complete conflict resolution log."""
    
    request_id: str
    
    # Detected conflicts
    conflicts: List[ConflictInstance] = Field(default_factory=list)
    
    # Summary
    total_conflicts: int = Field(default=0, ge=0)
    resolved_conflicts: int = Field(default=0, ge=0)
    unresolved_conflicts: int = Field(default=0, ge=0)
    
    # Escalations
    escalated_to_claude: int = Field(default=0, ge=0)
    
    def add_conflict(
        self,
        conflict_type: ConflictType,
        atom_a: str,
        atom_b: str,
        field: str,
        value_a: Any,
        value_b: Any,
        confidence_a: float = 0.5,
        confidence_b: float = 0.5,
    ) -> ConflictInstance:
        """Add a detected conflict."""
        conflict = ConflictInstance(
            conflict_type=conflict_type,
            atom_a=atom_a,
            atom_b=atom_b,
            conflicting_field=field,
            value_a=value_a,
            value_b=value_b,
            confidence_a=confidence_a,
            confidence_b=confidence_b,
        )
        self.conflicts.append(conflict)
        self.total_conflicts += 1
        self.unresolved_conflicts += 1
        return conflict
    
    def resolve_conflict(
        self,
        conflict_id: str,
        strategy: ConflictResolutionStrategy,
        resolved_value: Any,
        confidence: float,
        reason: str,
    ) -> None:
        """Mark a conflict as resolved."""
        for conflict in self.conflicts:
            if conflict.conflict_id == conflict_id:
                conflict.resolved = True
                conflict.resolution_strategy = strategy
                conflict.resolved_value = resolved_value
                conflict.resolution_confidence = confidence
                conflict.resolution_reason = reason
                conflict.resolved_at = datetime.now(timezone.utc)
                
                self.resolved_conflicts += 1
                self.unresolved_conflicts -= 1
                
                if strategy == ConflictResolutionStrategy.ESCALATE_TO_CLAUDE:
                    self.escalated_to_claude += 1
                break


# =============================================================================
# PSYCHOLOGICAL ASSESSMENT
# =============================================================================

class PsychologicalAssessment(BaseModel):
    """Unified psychological assessment from synthesis."""
    
    # Regulatory constructs
    regulatory_focus: str = Field(default="balanced")  # "promotion", "prevention", "balanced"
    regulatory_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    construal_level: str = Field(default="moderate")  # "concrete", "moderate", "abstract"
    construal_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Current state
    arousal: float = Field(ge=0.0, le=1.0, default=0.5)
    valence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Dominant traits (if known)
    dominant_traits: Dict[str, float] = Field(default_factory=dict)
    
    # Psychological coherence
    coherence_score: float = Field(ge=0.0, le=1.0, default=0.5)
    coherence_issues: List[str] = Field(default_factory=list)


# =============================================================================
# MECHANISM RECOMMENDATION
# =============================================================================

class MechanismRecommendation(BaseModel):
    """Recommended mechanism with justification."""
    
    mechanism_id: str
    mechanism_name: str
    
    # Scores
    raw_score: float = Field(ge=0.0, le=1.0)
    weighted_score: float = Field(ge=0.0, le=1.0)
    
    # Ranking
    rank: int = Field(ge=1)
    is_primary: bool = Field(default=False)
    
    # Justification
    contributing_atoms: List[str] = Field(default_factory=list)
    justification: str = ""
    
    # Prior used
    prior_effectiveness: float = Field(ge=0.0, le=1.0, default=0.5)
    prior_source: str = Field(default="default")


# =============================================================================
# SYNTHESIS WORKSPACE (Zone 3)
# =============================================================================

class SynthesisWorkspace(BaseModel):
    """
    Zone 3: Complete synthesis workspace.
    
    Contains aggregated atom outputs, conflict resolution,
    and final recommendations.
    """
    
    # Identity
    workspace_id: str = Field(default_factory=lambda: f"z3_{uuid4().hex[:12]}")
    request_id: str
    
    # Lifecycle
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Status
    status: str = Field(default="pending")
    
    # Atom aggregation
    atom_aggregation: Optional[AtomAggregation] = None
    
    # Conflict resolution
    conflict_resolution: ConflictResolution = Field(
        default_factory=lambda: ConflictResolution(request_id="")
    )
    
    # Psychological assessment
    psychological_assessment: Optional[PsychologicalAssessment] = None
    
    # Mechanism recommendations
    mechanism_recommendations: List[MechanismRecommendation] = Field(
        default_factory=list
    )
    primary_mechanism: Optional[str] = None
    
    # Synthesis metadata
    synthesis_tokens_in: int = Field(default=0, ge=0)
    synthesis_tokens_out: int = Field(default=0, ge=0)
    synthesis_duration_ms: float = Field(ge=0.0, default=0.0)
    
    def start(self, request_id: str) -> None:
        """Start synthesis."""
        self.request_id = request_id
        self.conflict_resolution.request_id = request_id
        self.started_at = datetime.now(timezone.utc)
        self.status = "running"
    
    def complete(self) -> None:
        """Mark synthesis as complete."""
        self.completed_at = datetime.now(timezone.utc)
        self.status = "completed"
        
        if self.started_at:
            self.synthesis_duration_ms = (
                self.completed_at - self.started_at
            ).total_seconds() * 1000
    
    def get_top_mechanisms(self, n: int = 3) -> List[MechanismRecommendation]:
        """Get top N mechanism recommendations."""
        return sorted(
            self.mechanism_recommendations,
            key=lambda m: m.weighted_score,
            reverse=True
        )[:n]
