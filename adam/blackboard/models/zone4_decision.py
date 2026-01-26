# =============================================================================
# ADAM Blackboard Zone 4: Decision State
# Location: adam/blackboard/models/zone4_decision.py
# =============================================================================

"""
ZONE 4: DECISION STATE

Final decision state including selected ad, mechanisms, and serving details.

Contents:
- Decision candidates (scored)
- Final selection
- Serving details
- Latency budget tracking
- Fallback tier used

Access: Write by decision, read by all.
TTL: Session duration + 24 hours (for outcome attribution)
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# =============================================================================
# DECISION TIER
# =============================================================================

class DecisionTier(str, Enum):
    """Decision tier based on latency/quality tradeoff."""
    
    FULL_REASONING = "full_reasoning"     # Full atom DAG
    FAST_PATH = "fast_path"               # Cached priors, no Claude
    EMERGENCY = "emergency"               # Pure rules, no learning
    FALLBACK = "fallback"                 # Default selection


# =============================================================================
# DECISION CANDIDATE
# =============================================================================

class DecisionCandidate(BaseModel):
    """A scored candidate for the final decision."""
    
    candidate_id: str
    campaign_id: str
    creative_id: str
    
    # Scores
    mechanism_alignment_score: float = Field(ge=0.0, le=1.0)
    personality_alignment_score: float = Field(ge=0.0, le=1.0)
    context_alignment_score: float = Field(ge=0.0, le=1.0)
    
    # Combined score
    total_score: float = Field(ge=0.0, le=1.0)
    
    # Ranking
    rank: int = Field(ge=1)
    
    # Mechanism application
    mechanisms_to_apply: List[str] = Field(default_factory=list)
    primary_mechanism: Optional[str] = None
    
    # Copy variant selection
    selected_copy_variant: Optional[str] = None
    copy_variant_reason: str = ""
    
    # Confidence
    selection_confidence: float = Field(ge=0.0, le=1.0, default=0.5)


# =============================================================================
# SERVING DETAILS
# =============================================================================

class ServingDetails(BaseModel):
    """Details about how the decision is served."""
    
    # Timing
    decision_latency_ms: float = Field(ge=0.0)
    total_latency_ms: float = Field(ge=0.0)
    latency_budget_ms: int = Field(ge=0)
    latency_budget_used_pct: float = Field(ge=0.0, le=100.0)
    
    # Tier
    decision_tier: DecisionTier
    tier_reason: str = ""
    
    # Cache usage
    profile_cache_hit: bool = Field(default=False)
    mechanism_cache_hit: bool = Field(default=False)
    
    # Components used
    atoms_executed: List[str] = Field(default_factory=list)
    atoms_skipped: List[str] = Field(default_factory=list)
    
    # Token usage
    total_claude_tokens: int = Field(default=0, ge=0)
    
    # Fallback details
    used_fallback: bool = Field(default=False)
    fallback_reason: Optional[str] = None


# =============================================================================
# DECISION STATE (Zone 4)
# =============================================================================

class DecisionState(BaseModel):
    """
    Zone 4: Complete decision state.
    
    Contains the final decision with all supporting information.
    """
    
    # Identity
    decision_id: str = Field(default_factory=lambda: f"dec_{uuid4().hex[:12]}")
    request_id: str
    user_id: str
    session_id: Optional[str] = None
    
    # Lifecycle
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    decided_at: Optional[datetime] = None
    
    # Status
    status: str = Field(default="pending")  # "pending", "decided", "served", "error"
    
    # Candidates
    candidates: List[DecisionCandidate] = Field(default_factory=list)
    candidate_count: int = Field(default=0, ge=0)
    
    # Final selection
    selected_candidate: Optional[DecisionCandidate] = None
    selected_campaign_id: Optional[str] = None
    selected_creative_id: Optional[str] = None
    
    # Mechanism application
    applied_mechanisms: List[str] = Field(default_factory=list)
    primary_mechanism: Optional[str] = None
    mechanism_intensities: Dict[str, float] = Field(default_factory=dict)
    
    # Copy selection
    selected_copy_variant: Optional[str] = None
    
    # Psychological context used
    user_regulatory_focus: Optional[str] = None
    user_construal_level: Optional[str] = None
    user_arousal: Optional[float] = None
    
    # Serving details
    serving_details: Optional[ServingDetails] = None
    
    # Confidence
    overall_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Explainability
    decision_reasoning: str = ""
    key_factors: List[str] = Field(default_factory=list)
    
    # Error (if any)
    error_message: Optional[str] = None
    
    def score_candidates(self, candidates: List[DecisionCandidate]) -> None:
        """Add and rank candidates."""
        self.candidates = sorted(
            candidates,
            key=lambda c: c.total_score,
            reverse=True
        )
        
        # Update ranks
        for i, c in enumerate(self.candidates):
            c.rank = i + 1
        
        self.candidate_count = len(self.candidates)
    
    def select(self, candidate: DecisionCandidate) -> None:
        """Select the winning candidate."""
        self.selected_candidate = candidate
        self.selected_campaign_id = candidate.campaign_id
        self.selected_creative_id = candidate.creative_id
        self.applied_mechanisms = candidate.mechanisms_to_apply
        self.primary_mechanism = candidate.primary_mechanism
        self.selected_copy_variant = candidate.selected_copy_variant
        self.overall_confidence = candidate.selection_confidence
        
        self.status = "decided"
        self.decided_at = datetime.now(timezone.utc)
    
    def mark_served(self, serving_details: ServingDetails) -> None:
        """Mark the decision as served."""
        self.serving_details = serving_details
        self.status = "served"
    
    def fail(self, error: str) -> None:
        """Mark the decision as failed."""
        self.status = "error"
        self.error_message = error
        self.decided_at = datetime.now(timezone.utc)
