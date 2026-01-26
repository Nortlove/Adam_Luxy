# =============================================================================
# ADAM Enhancement #13: Decision Output Models
# Location: adam/cold_start/models/decisions.py
# =============================================================================

"""
Cold start decision output models.

These models capture the output of cold start strategy selection
and are used for downstream components and learning.
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, computed_field
import uuid

from .enums import (
    UserDataTier, ColdStartStrategy, ArchetypeID,
    CognitiveMechanism, PriorSource, PersonalityTrait
)
from .priors import PsychologicalPrior


class ColdStartDecision(BaseModel):
    """
    Output of cold start strategy selection.
    
    Contains the inferred psychological profile and recommendations
    for downstream components (Atom DAG, Copy Generation, etc.).
    """
    # Request identification
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    session_id: str
    
    # User classification
    data_tier: UserDataTier
    strategy_applied: ColdStartStrategy
    
    # Archetype assignment (if applicable)
    assigned_archetype: Optional[ArchetypeID] = None
    archetype_confidence: float = 0.0
    
    # Inferred psychological profile
    inferred_prior: PsychologicalPrior = Field(default_factory=PsychologicalPrior)
    
    # Profile quality metrics
    overall_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    trait_confidences: Dict[PersonalityTrait, float] = Field(default_factory=dict)
    mechanism_uncertainties: Dict[CognitiveMechanism, float] = Field(default_factory=dict)
    
    # Exploration recommendations
    exploration_rate: float = Field(ge=0.0, le=1.0, default=0.5)
    exploration_focus: Optional[CognitiveMechanism] = None
    next_best_action: str = "observe_interaction"
    
    # Prior sources used
    sources_used: List[PriorSource] = Field(default_factory=list)
    
    # Performance tracking
    latency_ms: float = 0.0
    cache_hit: bool = False
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @computed_field
    @property
    def is_cold(self) -> bool:
        """Whether this is a cold start (not full profile)."""
        return self.data_tier != UserDataTier.TIER_5_PROFILED_FULL
    
    @computed_field
    @property
    def most_uncertain_mechanism(self) -> Optional[CognitiveMechanism]:
        """Get mechanism with highest uncertainty."""
        if not self.mechanism_uncertainties:
            return None
        return max(
            self.mechanism_uncertainties.items(),
            key=lambda x: x[1]
        )[0]
    
    def to_atom_context(self) -> Dict[str, Any]:
        """
        Convert to context for Atom of Thought atoms.
        
        This is injected into atom prompts for prior-informed reasoning.
        """
        return {
            "data_tier": self.data_tier.value,
            "is_cold_start": self.is_cold,
            "assigned_archetype": (
                self.assigned_archetype.value if self.assigned_archetype else None
            ),
            "archetype_confidence": self.archetype_confidence,
            "overall_confidence": self.overall_confidence,
            "exploration_rate": self.exploration_rate,
            "trait_means": {
                trait.value: self.inferred_prior.get_trait_mean(trait)
                for trait in PersonalityTrait
            },
            "mechanism_effectiveness": {
                mech.value: self.inferred_prior.get_mechanism_effectiveness(mech)
                for mech in CognitiveMechanism
            },
            "most_uncertain_mechanism": (
                self.most_uncertain_mechanism.value 
                if self.most_uncertain_mechanism else None
            ),
            "sources_used": [s.value for s in self.sources_used]
        }


class TierTransitionEvent(BaseModel):
    """
    Event emitted when user transitions between data tiers.
    
    Consumed by Gradient Bridge for learning signal propagation.
    """
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    session_id: str
    
    # Transition details
    previous_tier: UserDataTier
    new_tier: UserDataTier
    
    # What triggered the transition
    trigger_interaction_count: int
    trigger_confidence: float
    
    # Profile state at transition
    profile_at_transition: Optional[PsychologicalPrior] = None
    
    # Timestamps
    transition_time: datetime = Field(default_factory=datetime.utcnow)
    time_in_previous_tier_hours: float = 0.0
    
    @computed_field
    @property
    def is_upgrade(self) -> bool:
        """Whether this is an upgrade (more data available)."""
        return self.new_tier.tier_number > self.previous_tier.tier_number


class ProfileVelocityMetrics(BaseModel):
    """Metrics for tracking profile development velocity."""
    user_id: str
    
    # Interaction metrics
    interactions_today: int = 0
    interactions_this_week: int = 0
    interactions_total: int = 0
    
    # Confidence progression
    confidence_when_first_seen: float = 0.0
    confidence_current: float = 0.0
    confidence_delta_per_day: float = 0.0
    
    # Information gain
    total_information_gain: float = 0.0
    information_gain_per_interaction: float = 0.0
    
    # Projections
    estimated_days_to_full_profile: Optional[int] = None
    estimated_tier_at_day_30: UserDataTier = UserDataTier.TIER_0_ANONYMOUS_NEW
    
    # Timestamps
    first_seen_at: datetime = Field(default_factory=datetime.utcnow)
    last_interaction_at: datetime = Field(default_factory=datetime.utcnow)
    metrics_updated_at: datetime = Field(default_factory=datetime.utcnow)


class ColdStartOutcome(BaseModel):
    """
    Outcome of a cold start decision for learning.
    
    Pairs decision with eventual outcome for prior updates.
    """
    decision_id: str
    user_id: Optional[str] = None
    session_id: str
    
    # Decision details
    tier_at_decision: UserDataTier
    strategy_used: ColdStartStrategy
    archetype_used: Optional[ArchetypeID] = None
    
    # Mechanisms activated
    mechanisms_activated: List[CognitiveMechanism] = Field(default_factory=list)
    
    # Outcome
    outcome_type: str  # "conversion", "click", "engagement", "skip"
    outcome_value: float = 0.0
    conversion_value: Optional[float] = None
    
    # Attribution
    attributed_to_cold_start: float = 0.0  # 0-1 attribution weight
    
    # Timing
    decision_timestamp: datetime
    outcome_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @computed_field
    @property
    def is_positive_outcome(self) -> bool:
        """Whether outcome was positive."""
        return self.outcome_value > 0.5
    
    @computed_field
    @property
    def latency_seconds(self) -> float:
        """Time between decision and outcome."""
        return (self.outcome_timestamp - self.decision_timestamp).total_seconds()
