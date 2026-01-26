# =============================================================================
# ADAM Enhancement #13: User Data Models
# Location: adam/cold_start/models/user.py
# =============================================================================

"""
User data models for Cold Start classification and profiling.

These models capture:
- What data we have about a user (inventory)
- Interaction statistics (behavioral density)
- Complete user data profile (tier classification)
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field, computed_field
import uuid

from .enums import UserDataTier, ArchetypeID


class UserDataInventory(BaseModel):
    """
    Inventory of available data for a user.
    
    Determines which cold start strategies are applicable.
    Used to classify users into data tiers.
    """
    # Identity
    has_user_id: bool = False
    has_device_id: bool = False
    has_session_id: bool = True  # Always have session
    
    # Demographics
    has_age: bool = False
    has_gender: bool = False
    has_location: bool = False
    has_language: bool = False
    has_income_bracket: bool = False
    has_education_level: bool = False
    
    # Behavioral
    has_behavioral_history: bool = False
    has_purchase_history: bool = False
    has_content_preferences: bool = False
    
    # Profile
    has_psychological_profile: bool = False
    has_archetype_assignment: bool = False
    has_mechanism_priors: bool = False
    
    @computed_field
    @property
    def demographic_completeness(self) -> float:
        """Fraction of demographic fields available (0-1)."""
        fields = [
            self.has_age, self.has_gender, self.has_location,
            self.has_language, self.has_income_bracket, self.has_education_level
        ]
        return sum(fields) / len(fields)
    
    @computed_field
    @property
    def total_data_richness(self) -> float:
        """Overall data richness score (0-1)."""
        weights = {
            "identity": 0.1,
            "demographics": 0.2,
            "behavioral": 0.3,
            "profile": 0.4
        }
        
        identity_score = (self.has_user_id * 0.7 + self.has_device_id * 0.3)
        behavioral_score = (
            self.has_behavioral_history * 0.4 +
            self.has_purchase_history * 0.4 +
            self.has_content_preferences * 0.2
        )
        profile_score = (
            self.has_psychological_profile * 0.5 +
            self.has_archetype_assignment * 0.3 +
            self.has_mechanism_priors * 0.2
        )
        
        return (
            weights["identity"] * identity_score +
            weights["demographics"] * self.demographic_completeness +
            weights["behavioral"] * behavioral_score +
            weights["profile"] * profile_score
        )


class UserInteractionStats(BaseModel):
    """Quantified interaction statistics for a user."""
    
    total_interactions: int = 0
    ad_impressions: int = 0
    ad_clicks: int = 0
    ad_conversions: int = 0
    
    content_views: int = 0
    content_engagements: int = 0
    
    days_since_first_seen: int = 0
    days_since_last_interaction: int = 0
    
    unique_content_types: int = 0
    unique_ad_categories: int = 0
    
    @computed_field
    @property
    def click_through_rate(self) -> float:
        """Overall CTR."""
        if self.ad_impressions == 0:
            return 0.0
        return self.ad_clicks / self.ad_impressions
    
    @computed_field
    @property
    def conversion_rate(self) -> float:
        """Overall conversion rate (conversions / clicks)."""
        if self.ad_clicks == 0:
            return 0.0
        return self.ad_conversions / self.ad_clicks
    
    @computed_field
    @property
    def interaction_velocity(self) -> float:
        """Interactions per day."""
        if self.days_since_first_seen == 0:
            return float(self.total_interactions)
        return self.total_interactions / self.days_since_first_seen


class UserDataProfile(BaseModel):
    """
    Complete data profile for a user.
    
    Used to classify into data tier and select cold start strategy.
    """
    # Identifiers
    user_id: Optional[str] = None
    device_id: Optional[str] = None
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    
    # Data inventory
    inventory: UserDataInventory = Field(default_factory=UserDataInventory)
    
    # Interaction statistics
    stats: UserInteractionStats = Field(default_factory=UserInteractionStats)
    
    # Demographics (if available)
    age_bracket: Optional[str] = None
    gender: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    language: Optional[str] = None
    income_bracket: Optional[str] = None
    education_level: Optional[str] = None
    
    # Current context
    current_content_type: Optional[str] = None
    current_content_id: Optional[str] = None
    current_device_type: Optional[str] = None
    current_hour_of_day: Optional[int] = None
    current_day_of_week: Optional[int] = None
    referral_source: Optional[str] = None
    
    # Profile status
    assigned_archetype: Optional[ArchetypeID] = None
    archetype_confidence: float = 0.0
    profile_confidence: float = 0.0
    
    # Timestamps
    first_seen_at: Optional[datetime] = None
    last_interaction_at: Optional[datetime] = None
    profile_updated_at: Optional[datetime] = None
    
    @computed_field
    @property
    def data_tier(self) -> UserDataTier:
        """Classify user into data tier based on available data."""
        # Full profile available
        if (self.inventory.has_psychological_profile and 
            self.profile_confidence >= 0.7):
            return UserDataTier.TIER_5_PROFILED_FULL
        
        # Moderate behavioral history
        if (self.inventory.has_user_id and 
            self.stats.total_interactions >= 20):
            return UserDataTier.TIER_4_REGISTERED_MODERATE
        
        # Sparse behavioral history
        if (self.inventory.has_user_id and 
            self.stats.total_interactions >= 5):
            return UserDataTier.TIER_3_REGISTERED_SPARSE
        
        # Demographics only
        if (self.inventory.has_user_id and 
            self.inventory.demographic_completeness > 0.3):
            return UserDataTier.TIER_2_REGISTERED_MINIMAL
        
        # Session behavior available
        if self.stats.total_interactions > 0:
            return UserDataTier.TIER_1_ANONYMOUS_SESSION
        
        # Completely new
        return UserDataTier.TIER_0_ANONYMOUS_NEW


class UserTierClassifier(BaseModel):
    """
    Classifier for determining user data tier.
    
    Uses configurable thresholds for tier boundaries.
    Can be optimized based on outcome data.
    """
    
    # Tier thresholds
    sparse_interaction_threshold: int = 5
    moderate_interaction_threshold: int = 20
    full_profile_interaction_threshold: int = 50
    full_profile_confidence_threshold: float = 0.7
    demographic_completeness_threshold: float = 0.3
    
    def classify(self, profile: UserDataProfile) -> UserDataTier:
        """
        Classify user into appropriate data tier.
        
        Args:
            profile: User's data profile
            
        Returns:
            Appropriate UserDataTier
        """
        # Check for full profile first
        if (profile.inventory.has_psychological_profile and
            profile.profile_confidence >= self.full_profile_confidence_threshold):
            return UserDataTier.TIER_5_PROFILED_FULL
        
        # Not registered
        if not profile.inventory.has_user_id:
            if profile.stats.total_interactions > 0:
                return UserDataTier.TIER_1_ANONYMOUS_SESSION
            return UserDataTier.TIER_0_ANONYMOUS_NEW
        
        # Registered with varying data richness
        interactions = profile.stats.total_interactions
        
        if interactions >= self.moderate_interaction_threshold:
            return UserDataTier.TIER_4_REGISTERED_MODERATE
        
        if interactions >= self.sparse_interaction_threshold:
            return UserDataTier.TIER_3_REGISTERED_SPARSE
        
        if profile.inventory.demographic_completeness >= self.demographic_completeness_threshold:
            return UserDataTier.TIER_2_REGISTERED_MINIMAL
        
        # Registered but minimal data
        return UserDataTier.TIER_2_REGISTERED_MINIMAL
