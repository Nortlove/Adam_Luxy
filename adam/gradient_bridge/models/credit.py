# =============================================================================
# ADAM Gradient Bridge Credit Assignment Models
# Location: adam/gradient_bridge/models/credit.py
# =============================================================================

"""
CREDIT ASSIGNMENT MODELS

Models for multi-level attribution of outcomes to components.

Attribution Levels:
1. Atom Level - Which atoms contributed to success?
2. Mechanism Level - Which mechanisms were effective?
3. Component Level - Bandit, Graph, Meta-Learner contributions
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================

class ComponentType(str, Enum):
    """Components that can receive learning signals."""
    
    # Atoms
    ATOM_REGULATORY_FOCUS = "atom_regulatory_focus"
    ATOM_CONSTRUAL_LEVEL = "atom_construal_level"
    ATOM_PERSONALITY = "atom_personality"
    ATOM_MECHANISM = "atom_mechanism"
    ATOM_AD_SELECTION = "atom_ad_selection"
    
    # Core
    BANDIT = "bandit"
    GRAPH = "graph"
    META_LEARNER = "meta_learner"
    VERIFICATION = "verification"
    BLACKBOARD = "blackboard"


class OutcomeType(str, Enum):
    """Types of outcomes tracked."""
    
    CONVERSION = "conversion"
    CLICK = "click"
    LISTEN_COMPLETE = "listen_complete"
    LISTEN_PARTIAL = "listen_partial"
    SKIP = "skip"
    ENGAGEMENT = "engagement"


class AttributionMethod(str, Enum):
    """Methods for computing credit."""
    
    CONFIDENCE_WEIGHTED = "confidence_weighted"
    LLM_GUIDED = "llm_guided"
    COUNTERFACTUAL = "counterfactual"
    SHAPLEY = "shapley"
    ENSEMBLE = "ensemble"


# =============================================================================
# ATOM CREDIT
# =============================================================================

class AtomCredit(BaseModel):
    """Credit assigned to a single atom."""
    
    atom_id: str
    atom_type: str
    
    # Credit
    credit_score: float = Field(ge=0.0, le=1.0)
    credit_share: float = Field(ge=0.0, le=1.0)  # Fraction of total credit
    
    # How it was computed
    method: AttributionMethod = Field(default=AttributionMethod.CONFIDENCE_WEIGHTED)
    
    # Supporting data
    atom_confidence: float = Field(ge=0.0, le=1.0)
    atom_contribution: str = ""  # What the atom contributed
    
    # Counterfactual (if computed)
    counterfactual_outcome: Optional[float] = None
    marginal_contribution: Optional[float] = None
    
    # Mechanisms recommended by this atom
    mechanisms_recommended: List[str] = Field(default_factory=list)
    mechanism_weights: Dict[str, float] = Field(default_factory=dict)


# =============================================================================
# COMPONENT CREDIT
# =============================================================================

class ComponentCredit(BaseModel):
    """Credit assigned to a system component."""
    
    component_type: ComponentType
    component_id: str = ""
    
    # Credit
    credit_score: float = Field(ge=0.0, le=1.0)
    credit_share: float = Field(ge=0.0, le=1.0)
    
    # Breakdown
    sub_credits: Dict[str, float] = Field(default_factory=dict)
    
    # Update signal strength
    update_weight: float = Field(ge=0.0, le=1.0, default=1.0)


# =============================================================================
# OUTCOME ATTRIBUTION
# =============================================================================

class OutcomeAttribution(BaseModel):
    """
    Complete attribution of an outcome to all components.
    
    This is the output of the credit attribution engine.
    """
    
    attribution_id: str = Field(
        default_factory=lambda: f"attr_{uuid4().hex[:12]}"
    )
    
    # Outcome reference
    decision_id: str
    request_id: str
    user_id: str
    
    # Outcome details
    outcome_type: OutcomeType
    outcome_value: float = Field(ge=0.0, le=1.0)
    outcome_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    # Time between decision and outcome
    latency_seconds: int = Field(default=0, ge=0)
    
    # Attribution method used
    method: AttributionMethod = Field(default=AttributionMethod.ENSEMBLE)
    
    # Atom-level credit
    atom_credits: List[AtomCredit] = Field(default_factory=list)
    total_atom_credit: float = Field(ge=0.0, default=0.0)
    
    # Mechanism-level credit
    mechanism_credits: Dict[str, float] = Field(default_factory=dict)
    primary_mechanism: Optional[str] = None
    primary_mechanism_credit: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Construct-level credit (DSP constructs)
    construct_credits: Dict[str, float] = Field(default_factory=dict)  # {construct_id: credit}
    active_constructs: List[str] = Field(default_factory=list)  # Constructs active at decision time
    
    # Component-level credit
    component_credits: List[ComponentCredit] = Field(default_factory=list)
    
    # Confidence in attribution
    attribution_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Context for learning
    execution_path: str = ""  # "fast", "reasoning", "exploration"
    meta_learner_modality: str = ""
    
    # Timing
    computed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    computation_ms: float = Field(ge=0.0, default=0.0)
    
    def get_atom_credit(self, atom_id: str) -> Optional[AtomCredit]:
        """Get credit for a specific atom."""
        for ac in self.atom_credits:
            if ac.atom_id == atom_id:
                return ac
        return None
    
    def get_component_credit(self, component: ComponentType) -> Optional[ComponentCredit]:
        """Get credit for a component."""
        for cc in self.component_credits:
            if cc.component_type == component:
                return cc
        return None


# =============================================================================
# CREDIT ASSIGNMENT REQUEST
# =============================================================================

class CreditAssignmentRequest(BaseModel):
    """Request to compute credit attribution."""
    
    decision_id: str
    request_id: str
    user_id: str
    
    # Outcome
    outcome_type: OutcomeType
    outcome_value: float = Field(ge=0.0, le=1.0)
    
    # Context
    atom_outputs: Dict[str, Any] = Field(default_factory=dict)
    mechanism_used: Optional[str] = None
    mechanisms_considered: List[str] = Field(default_factory=list)
    
    # Decision context
    execution_path: str = ""
    meta_learner_modality: str = ""
    
    # Method preference
    preferred_method: Optional[AttributionMethod] = None


class CreditAssignment(BaseModel):
    """Alias for OutcomeAttribution for backwards compatibility."""
    
    attribution: OutcomeAttribution
    success: bool = Field(default=True)
    error_message: Optional[str] = None
