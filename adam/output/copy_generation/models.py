# =============================================================================
# ADAM Copy Generation Models
# Location: adam/output/copy_generation/models.py
# =============================================================================

"""
COPY GENERATION MODELS

Models for personality-matched copy generation.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field


class CopyType(str, Enum):
    """Types of copy."""
    
    HEADLINE = "headline"
    BODY = "body"
    CTA = "cta"
    TAGLINE = "tagline"
    AUDIO_SCRIPT = "audio_script"
    FULL_AD = "full_ad"


class CopyLength(str, Enum):
    """Copy length variants."""
    
    SHORT = "short"      # 5-10 words
    MEDIUM = "medium"    # 15-25 words
    LONG = "long"        # 30-50 words


class VoiceGender(str, Enum):
    """Voice gender for audio."""
    
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"


class CopyRequest(BaseModel):
    """Request for copy generation."""
    
    request_id: str = Field(default_factory=lambda: f"copy_{datetime.now().strftime('%Y%m%d%H%M%S')}")
    user_id: str = Field(default="anonymous")
    brand_id: str = Field(default="default")
    
    # What to generate
    copy_type: CopyType
    length: CopyLength = Field(default=CopyLength.MEDIUM)
    
    # Product/offer context
    product_name: Optional[str] = None
    product_description: Optional[str] = None
    offer: Optional[str] = None
    cta_action: Optional[str] = None  # "Buy now", "Learn more", etc.
    
    # Framing (from MessageFramingAtom)
    gain_emphasis: float = Field(ge=0.0, le=1.0, default=0.5)
    abstraction_level: float = Field(ge=0.0, le=1.0, default=0.5)
    emotional_appeal: float = Field(ge=0.0, le=1.0, default=0.5)
    urgency_level: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Tone
    tone: str = Field(default="neutral")
    
    # Mechanisms to activate
    mechanisms: List[str] = Field(default_factory=list)
    
    # Audio-specific
    include_audio: bool = Field(default=False)
    preferred_voice_gender: VoiceGender = Field(default=VoiceGender.NEUTRAL)
    target_duration_seconds: Optional[int] = None


class TextVariant(BaseModel):
    """A text variant."""
    
    variant_id: str
    text: str
    
    # Variant parameters
    framing: str = Field(default="neutral")  # gain, loss, neutral
    mechanism: Optional[str] = None
    
    # Quality
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class AudioCopy(BaseModel):
    """Audio copy with SSML."""
    
    audio_id: str
    
    # Text
    plain_text: str
    ssml: str
    
    # Voice selection
    voice_id: str
    voice_gender: VoiceGender
    
    # Timing
    estimated_duration_seconds: float = Field(ge=0.0)
    
    # Quality
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)


class GeneratedCopy(BaseModel):
    """Complete generated copy result."""
    
    request_id: str
    user_id: str
    brand_id: str
    
    # Generated text
    primary_text: str
    text_variants: List[TextVariant] = Field(default_factory=list)
    
    # Audio (if requested)
    audio: Optional[AudioCopy] = None
    
    # Metadata
    copy_type: CopyType
    length: CopyLength
    
    # Framing used
    framing_applied: Dict[str, Any] = Field(default_factory=dict)
    mechanisms_used: List[str] = Field(default_factory=list)
    
    # Quality
    overall_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Timing
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
