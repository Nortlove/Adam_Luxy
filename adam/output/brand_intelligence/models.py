# =============================================================================
# ADAM Brand Intelligence Models
# Location: adam/output/brand_intelligence/models.py
# =============================================================================

"""
BRAND INTELLIGENCE MODELS

Models for brand psychological profiles and matching.

Based on Aaker's Brand Personality Framework:
- Sincerity (down-to-earth, honest, wholesome, cheerful)
- Excitement (daring, spirited, imaginative, up-to-date)
- Competence (reliable, intelligent, successful)
- Sophistication (upper-class, charming)
- Ruggedness (outdoorsy, tough)
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field


# =============================================================================
# BRAND PERSONALITY (AAKER)
# =============================================================================

class BrandPersonality(BaseModel):
    """Aaker's Brand Personality dimensions."""
    
    sincerity: float = Field(ge=0.0, le=1.0, default=0.5)
    excitement: float = Field(ge=0.0, le=1.0, default=0.5)
    competence: float = Field(ge=0.0, le=1.0, default=0.5)
    sophistication: float = Field(ge=0.0, le=1.0, default=0.5)
    ruggedness: float = Field(ge=0.0, le=1.0, default=0.5)
    
    def to_vector(self) -> List[float]:
        """Convert to vector for similarity computation."""
        return [
            self.sincerity,
            self.excitement,
            self.competence,
            self.sophistication,
            self.ruggedness,
        ]
    
    def get_dominant_traits(self, threshold: float = 0.6) -> List[str]:
        """Get dominant personality traits."""
        traits = []
        if self.sincerity >= threshold:
            traits.append("sincerity")
        if self.excitement >= threshold:
            traits.append("excitement")
        if self.competence >= threshold:
            traits.append("competence")
        if self.sophistication >= threshold:
            traits.append("sophistication")
        if self.ruggedness >= threshold:
            traits.append("ruggedness")
        return traits


class BrandVoice(BaseModel):
    """Brand voice characteristics."""
    
    tone: str = Field(default="neutral")  # friendly, professional, playful, etc.
    formality: float = Field(ge=0.0, le=1.0, default=0.5)  # 0=casual, 1=formal
    energy: float = Field(ge=0.0, le=1.0, default=0.5)     # 0=calm, 1=energetic
    humor: float = Field(ge=0.0, le=1.0, default=0.3)      # 0=serious, 1=humorous
    
    # Vocabulary
    preferred_words: List[str] = Field(default_factory=list)
    forbidden_words: List[str] = Field(default_factory=list)


class BrandProfile(BaseModel):
    """Complete brand profile."""
    
    brand_id: str
    brand_name: str
    
    # Personality
    personality: BrandPersonality
    
    # Voice
    voice: BrandVoice
    
    # Category
    primary_category: str
    secondary_categories: List[str] = Field(default_factory=list)
    
    # Target audience Big Five tendencies
    target_openness: float = Field(ge=0.0, le=1.0, default=0.5)
    target_conscientiousness: float = Field(ge=0.0, le=1.0, default=0.5)
    target_extraversion: float = Field(ge=0.0, le=1.0, default=0.5)
    target_agreeableness: float = Field(ge=0.0, le=1.0, default=0.5)
    target_neuroticism: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Mechanism preferences
    preferred_mechanisms: List[str] = Field(default_factory=list)
    forbidden_mechanisms: List[str] = Field(default_factory=list)
    
    # Constraints
    max_urgency: float = Field(ge=0.0, le=1.0, default=0.8)
    min_construal_level: float = Field(ge=0.0, le=1.0, default=0.2)
    
    # Metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class BrandUserMatch(BaseModel):
    """Match result between brand and user."""
    
    brand_id: str
    user_id: str
    
    # Match scores
    personality_match: float = Field(ge=0.0, le=1.0)
    voice_fit: float = Field(ge=0.0, le=1.0)
    mechanism_alignment: float = Field(ge=0.0, le=1.0)
    
    # Overall
    overall_match: float = Field(ge=0.0, le=1.0)
    match_confidence: float = Field(ge=0.0, le=1.0)
    
    # Recommendations
    recommended_mechanisms: List[str] = Field(default_factory=list)
    recommended_tone: str = Field(default="neutral")
    
    # Timing
    matched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
