# =============================================================================
# ADAM WPP Brand Models
# Location: adam/platform/wpp/models/brand.py
# =============================================================================

"""
BRAND INTELLIGENCE MODELS

Models for brand-specific constraints, voice, and optimization.

WPP manages thousands of brands, each with:
- Voice guidelines
- Psychological positioning
- Mechanism constraints
- Performance targets
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class BrandTone(str, Enum):
    """Brand communication tone."""
    
    AUTHORITATIVE = "authoritative"
    FRIENDLY = "friendly"
    INSPIRATIONAL = "inspirational"
    PLAYFUL = "playful"
    SOPHISTICATED = "sophisticated"
    TRUSTWORTHY = "trustworthy"
    URGENT = "urgent"


class MechanismConstraint(str, Enum):
    """How a mechanism can be used with a brand."""
    
    REQUIRED = "required"     # Must use this mechanism
    PREFERRED = "preferred"   # Prefer this mechanism
    ALLOWED = "allowed"       # Can use if appropriate
    AVOID = "avoid"           # Avoid unless necessary
    FORBIDDEN = "forbidden"   # Never use


class BrandVoice(BaseModel):
    """
    Brand voice guidelines for messaging.
    """
    
    # Tone
    primary_tone: BrandTone = Field(default=BrandTone.FRIENDLY)
    secondary_tones: List[BrandTone] = Field(default_factory=list)
    
    # Language
    vocabulary_level: str = Field(default="conversational")  # "simple", "conversational", "sophisticated"
    sentence_length: str = Field(default="medium")  # "short", "medium", "long"
    
    # Personality alignment
    target_personality: Dict[str, float] = Field(default_factory=dict)
    # Example: {"openness": 0.7, "extraversion": 0.6}
    
    # Regulatory focus alignment
    regulatory_focus: str = Field(default="balanced")  # "promotion", "prevention", "balanced"
    
    # Construal preference
    construal_preference: str = Field(default="moderate")  # "abstract", "concrete", "moderate"


class BrandConstraints(BaseModel):
    """
    Mechanism and messaging constraints for a brand.
    """
    
    # Mechanism constraints
    mechanism_constraints: Dict[str, MechanismConstraint] = Field(
        default_factory=dict
    )
    # Example: {"scarcity": "avoid", "social_proof": "preferred"}
    
    # Forbidden words/phrases
    forbidden_words: List[str] = Field(default_factory=list)
    
    # Required disclosures
    required_disclosures: List[str] = Field(default_factory=list)
    
    # Maximum mechanism intensity
    max_mechanism_intensity: float = Field(ge=0.0, le=1.0, default=0.8)
    
    # Category restrictions
    excluded_categories: List[str] = Field(default_factory=list)
    
    # Competitor blocking
    blocked_competitors: List[str] = Field(default_factory=list)


class BrandProfile(BaseModel):
    """
    Complete brand profile for ADAM optimization.
    """
    
    brand_id: str = Field(default_factory=lambda: f"brand_{uuid4().hex[:8]}")
    
    # Identity
    name: str
    advertiser_id: str
    category: str
    
    # Voice
    voice: BrandVoice = Field(default_factory=BrandVoice)
    
    # Constraints
    constraints: BrandConstraints = Field(default_factory=BrandConstraints)
    
    # Historical performance
    historical_ctr: float = Field(ge=0.0, le=1.0, default=0.02)
    historical_conversion_rate: float = Field(ge=0.0, le=1.0, default=0.01)
    
    # Mechanism effectiveness for this brand
    mechanism_effectiveness: Dict[str, float] = Field(default_factory=dict)
    
    # Optimal personality segments
    high_performing_segments: List[str] = Field(default_factory=list)
    
    # Status
    is_active: bool = Field(default=True)
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class CampaignObjective(str, Enum):
    """Campaign objectives."""
    
    AWARENESS = "awareness"
    CONSIDERATION = "consideration"
    CONVERSION = "conversion"
    LOYALTY = "loyalty"
    REACTIVATION = "reactivation"


class WPPCampaign(BaseModel):
    """
    A WPP advertising campaign.
    """
    
    campaign_id: str = Field(default_factory=lambda: f"wpp_camp_{uuid4().hex[:8]}")
    
    # Brand
    brand_id: str
    advertiser_id: str
    
    # Campaign metadata
    name: str
    objective: CampaignObjective = Field(default=CampaignObjective.AWARENESS)
    
    # Targeting
    target_categories: List[str] = Field(default_factory=list)
    target_demographics: Dict[str, str] = Field(default_factory=dict)
    target_platforms: List[str] = Field(default_factory=list)  # "iheart", "web", "social"
    
    # Psychological targeting
    target_personality_profile: Optional[Dict[str, float]] = None
    preferred_mechanisms: List[str] = Field(default_factory=list)
    
    # Budget
    budget_total: float = Field(ge=0.0)
    budget_daily: float = Field(ge=0.0)
    spend_to_date: float = Field(default=0.0, ge=0.0)
    
    # Performance targets
    target_ctr: float = Field(ge=0.0, le=1.0, default=0.02)
    target_conversion_rate: float = Field(ge=0.0, le=1.0, default=0.01)
    target_roas: float = Field(ge=0.0, default=3.0)
    
    # Actual performance
    impressions: int = Field(default=0, ge=0)
    clicks: int = Field(default=0, ge=0)
    conversions: int = Field(default=0, ge=0)
    revenue: float = Field(default=0.0, ge=0.0)
    
    # Schedule
    start_date: datetime
    end_date: datetime
    is_active: bool = Field(default=True)
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
