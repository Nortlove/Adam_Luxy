# =============================================================================
# ADAM Graph Context Models
# Location: adam/graph_reasoning/models/graph_context.py
# =============================================================================

"""
GRAPH CONTEXT MODELS

Models for context pulled from Neo4j to inform reasoning.

The Interaction Bridge pulls this context before reasoning and
uses it to hydrate the Atom of Thought DAG with learned priors.

Context Components:
- UserProfileSnapshot: Big Five, traits, preferences
- MechanismHistory: Past mechanism effectiveness for this user
- StateHistory: Recent psychological state trajectory
- ArchetypeMatch: Best-matching archetype with priors
- CategoryPriors: Category-level mechanism effectiveness
- GraphContext: Complete context package
"""

from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# =============================================================================
# USER PROFILE SNAPSHOT
# =============================================================================

class BigFiveProfile(BaseModel):
    """Big Five personality trait scores."""
    
    openness: float = Field(ge=0.0, le=1.0, default=0.5)
    conscientiousness: float = Field(ge=0.0, le=1.0, default=0.5)
    extraversion: float = Field(ge=0.0, le=1.0, default=0.5)
    agreeableness: float = Field(ge=0.0, le=1.0, default=0.5)
    neuroticism: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Confidence in each trait
    openness_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    conscientiousness_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    extraversion_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    agreeableness_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    neuroticism_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    def to_dict(self) -> Dict[str, float]:
        """Return trait scores as dict."""
        return {
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "extraversion": self.extraversion,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism,
        }


class RegulatoryFocus(BaseModel):
    """Regulatory focus (Higgins, 1997)."""
    
    promotion_focus: float = Field(ge=0.0, le=1.0, default=0.5)
    prevention_focus: float = Field(ge=0.0, le=1.0, default=0.5)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    @property
    def dominant_focus(self) -> str:
        """Return the dominant focus."""
        if self.promotion_focus > self.prevention_focus:
            return "promotion"
        elif self.prevention_focus > self.promotion_focus:
            return "prevention"
        else:
            return "balanced"


class ConstrualLevel(BaseModel):
    """Construal Level (Trope & Liberman, 2010)."""
    
    abstraction_level: float = Field(ge=0.0, le=1.0, default=0.5)
    # 0 = very concrete, 1 = very abstract
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    @property
    def level_label(self) -> str:
        """Return a descriptive label."""
        if self.abstraction_level < 0.33:
            return "concrete"
        elif self.abstraction_level > 0.67:
            return "abstract"
        else:
            return "moderate"


class UserProfileSnapshot(BaseModel):
    """
    Complete psychological profile snapshot for a user.
    
    This is pulled from Neo4j at the start of each reasoning cycle.
    """
    
    user_id: str
    snapshot_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    # Core personality
    big_five: BigFiveProfile = Field(default_factory=BigFiveProfile)
    
    # Regulatory constructs
    regulatory_focus: RegulatoryFocus = Field(default_factory=RegulatoryFocus)
    construal_level: ConstrualLevel = Field(default_factory=ConstrualLevel)
    
    # Extended traits (from Enhancement #27)
    extended_traits: Dict[str, float] = Field(default_factory=dict)
    extended_trait_confidence: Dict[str, float] = Field(default_factory=dict)
    
    # Demographic context
    age_range: Optional[str] = None
    gender: Optional[str] = None
    location_market: Optional[str] = None
    
    # Engagement history
    total_decisions: int = Field(default=0, ge=0)
    total_conversions: int = Field(default=0, ge=0)
    overall_conversion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Profile quality
    profile_completeness: float = Field(ge=0.0, le=1.0, default=0.1)
    is_cold_start: bool = Field(default=True)
    
    # Last update timestamps
    last_decision_at: Optional[datetime] = None
    last_conversion_at: Optional[datetime] = None
    profile_updated_at: Optional[datetime] = None


# =============================================================================
# MECHANISM HISTORY
# =============================================================================

class MechanismEffectiveness(BaseModel):
    """Effectiveness of a single mechanism for a user."""
    
    mechanism_id: str
    mechanism_name: str
    
    # Success metrics
    success_rate: float = Field(ge=0.0, le=1.0)
    effect_size: float = Field(ge=0.0)
    trial_count: int = Field(ge=0)
    
    # Confidence bounds
    confidence: float = Field(ge=0.0, le=1.0)
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    
    # Temporal
    last_applied_at: Optional[datetime] = None
    last_success_at: Optional[datetime] = None
    
    # Trend
    trend_direction: str = Field(default="stable")  # "increasing", "decreasing", "stable"
    recent_success_rate: Optional[float] = None


class MechanismHistory(BaseModel):
    """
    Complete mechanism effectiveness history for a user.
    
    Contains learned priors from the RESPONDS_TO relationships.
    """
    
    user_id: str
    snapshot_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    # Mechanism effectiveness
    mechanism_effectiveness: List[MechanismEffectiveness] = Field(default_factory=list)
    
    # Best mechanisms for this user
    top_mechanisms: List[str] = Field(default_factory=list)
    
    # Mechanisms to avoid
    underperforming_mechanisms: List[str] = Field(default_factory=list)
    
    # Total trials
    total_mechanism_trials: int = Field(default=0, ge=0)
    
    def get_mechanism(self, mechanism_id: str) -> Optional[MechanismEffectiveness]:
        """Get effectiveness for a specific mechanism."""
        for m in self.mechanism_effectiveness:
            if m.mechanism_id == mechanism_id:
                return m
        return None
    
    def get_ranked_mechanisms(self) -> List[MechanismEffectiveness]:
        """Return mechanisms ranked by success rate."""
        return sorted(
            self.mechanism_effectiveness,
            key=lambda m: m.success_rate,
            reverse=True
        )


# =============================================================================
# STATE HISTORY
# =============================================================================

class TemporalUserState(BaseModel):
    """A point-in-time psychological state."""
    
    state_id: str = Field(default_factory=lambda: f"state_{uuid4().hex[:8]}")
    user_id: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    # Arousal-valence space
    arousal: float = Field(ge=0.0, le=1.0, default=0.5)
    valence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Regulatory state (may differ from trait)
    current_regulatory_focus: str = Field(default="balanced")
    current_construal_level: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Context
    session_id: Optional[str] = None
    trigger_event: Optional[str] = None
    
    # Momentum
    arousal_momentum: float = Field(default=0.0, ge=-1.0, le=1.0)
    valence_momentum: float = Field(default=0.0, ge=-1.0, le=1.0)


class StateHistory(BaseModel):
    """
    Recent psychological state trajectory for a user.
    
    Used to infer momentum and predict next state.
    """
    
    user_id: str
    snapshot_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    # Recent states (most recent first)
    recent_states: List[TemporalUserState] = Field(default_factory=list)
    
    # Current inferred state
    current_state: Optional[TemporalUserState] = None
    
    # Aggregate trajectory
    avg_arousal: float = Field(ge=0.0, le=1.0, default=0.5)
    avg_valence: float = Field(ge=0.0, le=1.0, default=0.5)
    arousal_trend: str = Field(default="stable")
    valence_trend: str = Field(default="stable")
    
    # Session context
    current_session_id: Optional[str] = None
    session_duration_seconds: int = Field(default=0, ge=0)


# =============================================================================
# ARCHETYPE MATCH
# =============================================================================

class ArchetypeMatch(BaseModel):
    """
    Best-matching archetype for a user.
    
    Archetypes provide mechanism effectiveness priors for cold-start.
    """
    
    archetype_id: str
    archetype_name: str
    
    # Match quality
    match_confidence: float = Field(ge=0.0, le=1.0)
    distance_to_centroid: float = Field(ge=0.0)
    
    # Archetype characteristics
    archetype_big_five: BigFiveProfile = Field(default_factory=BigFiveProfile)
    
    # Mechanism priors from archetype
    mechanism_priors: Dict[str, float] = Field(default_factory=dict)
    
    # Applicable categories
    primary_categories: List[str] = Field(default_factory=list)


# =============================================================================
# CATEGORY PRIORS
# =============================================================================

class CategoryMechanismPrior(BaseModel):
    """Mechanism effectiveness prior for a category."""
    
    category_id: str
    category_name: str
    mechanism_id: str
    mechanism_name: str
    
    # Prior effectiveness
    prior_mean: float = Field(ge=0.0, le=1.0)
    prior_variance: float = Field(ge=0.0)
    sample_size: int = Field(ge=0)
    
    # Confidence
    prior_confidence: float = Field(ge=0.0, le=1.0)


class CategoryPriors(BaseModel):
    """
    Category-level mechanism effectiveness priors.
    
    Used to inform decisions when user-specific data is sparse.
    """
    
    category_id: str
    category_name: str
    
    # Mechanism priors
    mechanism_priors: List[CategoryMechanismPrior] = Field(default_factory=list)
    
    # Best mechanisms for this category
    top_mechanisms: List[str] = Field(default_factory=list)
    
    # Category characteristics
    typical_big_five: Optional[BigFiveProfile] = None


# =============================================================================
# COMPLETE GRAPH CONTEXT
# =============================================================================

class GraphContext(BaseModel):
    """
    Complete graph context pulled for a reasoning cycle.
    
    This is the PULL side of the Interaction Bridge.
    Contains everything needed to hydrate the reasoning process.
    """
    
    context_id: str = Field(default_factory=lambda: f"ctx_{uuid4().hex[:12]}")
    request_id: str
    user_id: str
    pulled_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    # Core context components
    user_profile: UserProfileSnapshot
    mechanism_history: MechanismHistory
    state_history: StateHistory
    
    # Archetype for cold-start
    archetype_match: Optional[ArchetypeMatch] = None
    
    # Category context (if applicable)
    category_priors: Optional[CategoryPriors] = None
    
    # Query metadata
    query_latency_ms: float = Field(default=0.0, ge=0.0)
    cache_hit: bool = Field(default=False)
    
    # Context completeness
    is_cold_start: bool = Field(default=True)
    data_freshness_hours: float = Field(default=0.0, ge=0.0)
    
    def get_mechanism_prior(self, mechanism_id: str) -> float:
        """
        Get the best prior for a mechanism.
        
        Priority:
        1. User-specific effectiveness
        2. Archetype prior
        3. Category prior
        4. Default (0.5)
        """
        # User-specific
        user_mech = self.mechanism_history.get_mechanism(mechanism_id)
        if user_mech and user_mech.trial_count >= 5:
            return user_mech.success_rate
        
        # Archetype
        if self.archetype_match and mechanism_id in self.archetype_match.mechanism_priors:
            return self.archetype_match.mechanism_priors[mechanism_id]
        
        # Category
        if self.category_priors:
            for mp in self.category_priors.mechanism_priors:
                if mp.mechanism_id == mechanism_id:
                    return mp.prior_mean
        
        # Default
        return 0.5
