# =============================================================================
# ADAM Cross-Platform Models
# Location: adam/platform/shared/models.py
# =============================================================================

"""
CROSS-PLATFORM MODELS

Unified models for cross-platform user intelligence.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field


class Platform(str, Enum):
    """Supported platforms."""
    
    IHEART = "iheart"
    WPP = "wpp"
    AMAZON = "amazon"  # For cold-start priors
    ADAM = "adam"      # Internal ADAM-generated


class DataQuality(str, Enum):
    """Quality tiers for platform data."""
    
    VERIFIED = "verified"      # Survey-validated
    OBSERVED = "observed"      # From actual behavior
    INFERRED = "inferred"      # ML inference
    PRIOR = "prior"            # Population prior


class ConflictResolution(str, Enum):
    """How conflicts were resolved."""
    
    RECENCY = "recency"        # Most recent wins
    CONFIDENCE = "confidence"  # Highest confidence wins
    WEIGHTED = "weighted"      # Weighted average
    BEHAVIORAL = "behavioral"  # Behavioral evidence wins
    MANUAL = "manual"          # Human override


# =============================================================================
# BIG FIVE PROFILE
# =============================================================================

class PlatformBigFive(BaseModel):
    """Big Five from a single platform."""
    
    platform: Platform
    
    openness: float = Field(ge=0.0, le=1.0)
    conscientiousness: float = Field(ge=0.0, le=1.0)
    extraversion: float = Field(ge=0.0, le=1.0)
    agreeableness: float = Field(ge=0.0, le=1.0)
    neuroticism: float = Field(ge=0.0, le=1.0)
    
    # Quality metrics
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    quality: DataQuality = Field(default=DataQuality.INFERRED)
    observation_count: int = Field(default=0, ge=0)
    
    # Timing
    first_observed: Optional[datetime] = None
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class UnifiedBigFive(BaseModel):
    """Unified Big Five across platforms."""
    
    openness: float = Field(ge=0.0, le=1.0)
    conscientiousness: float = Field(ge=0.0, le=1.0)
    extraversion: float = Field(ge=0.0, le=1.0)
    agreeableness: float = Field(ge=0.0, le=1.0)
    neuroticism: float = Field(ge=0.0, le=1.0)
    
    # Overall confidence
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Which platforms contributed
    contributing_platforms: List[Platform] = Field(default_factory=list)
    
    # How conflicts were resolved
    resolution_method: ConflictResolution = Field(
        default=ConflictResolution.WEIGHTED
    )


# =============================================================================
# MECHANISM EFFECTIVENESS
# =============================================================================

class PlatformMechanismEffectiveness(BaseModel):
    """Mechanism effectiveness from a single platform."""
    
    platform: Platform
    mechanism_id: str
    
    # Beta distribution parameters
    alpha: float = Field(default=1.0, ge=0.0)
    beta: float = Field(default=1.0, ge=0.0)
    
    # Derived
    @property
    def success_rate(self) -> float:
        return self.alpha / (self.alpha + self.beta)
    
    @property
    def observation_count(self) -> int:
        return int(self.alpha + self.beta - 2)  # Subtract priors
    
    # Context modulations
    context_modulations: Dict[str, float] = Field(default_factory=dict)
    
    # Timing
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class UnifiedMechanismEffectiveness(BaseModel):
    """Unified mechanism effectiveness across platforms."""
    
    mechanism_id: str
    
    # Merged Beta parameters
    alpha: float = Field(default=1.0, ge=0.0)
    beta: float = Field(default=1.0, ge=0.0)
    
    @property
    def success_rate(self) -> float:
        return self.alpha / (self.alpha + self.beta)
    
    # Platform contributions
    platform_contributions: Dict[str, float] = Field(default_factory=dict)
    
    # Merged context modulations
    context_modulations: Dict[str, float] = Field(default_factory=dict)


# =============================================================================
# PLATFORM CONTRIBUTION
# =============================================================================

class PlatformContribution(BaseModel):
    """Contribution from a platform to unified profile."""
    
    platform: Platform
    
    # What this platform provides
    big_five: Optional[PlatformBigFive] = None
    mechanisms: Dict[str, PlatformMechanismEffectiveness] = Field(
        default_factory=dict
    )
    
    # Quality
    overall_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    data_quality: DataQuality = Field(default=DataQuality.INFERRED)
    
    # Stats
    total_observations: int = Field(default=0, ge=0)
    
    # Timing
    first_seen: Optional[datetime] = None
    last_active: Optional[datetime] = None


# =============================================================================
# UNIFIED USER PROFILE
# =============================================================================

class UnifiedUserProfile(BaseModel):
    """Unified user profile across all platforms."""
    
    adam_id: str  # Canonical ADAM identifier
    
    # Platform identities
    platform_ids: Dict[str, str] = Field(
        default_factory=dict,
        description="platform -> platform_user_id"
    )
    
    # Unified psychological profile
    big_five: UnifiedBigFive
    
    # Unified mechanism effectiveness
    mechanisms: Dict[str, UnifiedMechanismEffectiveness] = Field(
        default_factory=dict
    )
    
    # Regulatory focus (unified)
    promotion_tendency: float = Field(ge=0.0, le=1.0, default=0.5)
    prevention_tendency: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Construal level (unified)
    construal_level: float = Field(
        ge=0.0, le=1.0, default=0.5,
        description="0=concrete, 1=abstract"
    )
    
    # Platform contributions
    contributions: Dict[str, PlatformContribution] = Field(
        default_factory=dict
    )
    
    # Profile quality
    overall_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    total_observations: int = Field(default=0, ge=0)
    
    # Conflicts
    active_conflicts: List[str] = Field(default_factory=list)
    
    # Timing
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    def get_platform_id(self, platform: Platform) -> Optional[str]:
        """Get user ID for a specific platform."""
        return self.platform_ids.get(platform.value)


# =============================================================================
# MERGE RESULTS
# =============================================================================

class ProfileMergeResult(BaseModel):
    """Result of merging platform profiles."""
    
    adam_id: str
    
    # The unified profile
    unified_profile: UnifiedUserProfile
    
    # Merge details
    platforms_merged: List[Platform]
    conflicts_detected: int = Field(default=0, ge=0)
    conflicts_resolved: int = Field(default=0, ge=0)
    
    # Conflict details
    conflict_details: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Quality
    merge_confidence: float = Field(ge=0.0, le=1.0)
    
    # Timing
    merged_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class MechanismMergeResult(BaseModel):
    """Result of merging mechanism effectiveness."""
    
    mechanism_id: str
    
    # Merged effectiveness
    unified: UnifiedMechanismEffectiveness
    
    # Platform inputs
    platform_inputs: Dict[str, PlatformMechanismEffectiveness] = Field(
        default_factory=dict
    )
    
    # Merge method
    merge_method: str = Field(default="beta_combination")
    
    # Quality
    merge_confidence: float = Field(ge=0.0, le=1.0)


class JourneySyncResult(BaseModel):
    """Result of syncing journey state across platforms."""
    
    adam_id: str
    category: str
    
    # Synced state
    unified_stage: str
    unified_urgency: str
    
    # Platform states before sync
    platform_states: Dict[str, str] = Field(default_factory=dict)
    
    # Sync details
    sync_method: str = Field(default="most_advanced")
    conflict_detected: bool = Field(default=False)
    
    # Timing
    synced_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
