# =============================================================================
# ADAM Audio Models
# Location: adam/audio/models.py
# =============================================================================

"""
AUDIO MODELS

Models for voice synthesis and audio processing.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field


class VoiceGender(str, Enum):
    """Voice gender options."""
    
    MALE = "male"
    FEMALE = "female"
    NEUTRAL = "neutral"


class VoiceStyle(str, Enum):
    """Voice delivery styles."""
    
    CONVERSATIONAL = "conversational"
    PROFESSIONAL = "professional"
    ENTHUSIASTIC = "enthusiastic"
    CALM = "calm"
    URGENT = "urgent"
    FRIENDLY = "friendly"


class AudioFormat(str, Enum):
    """Audio output formats."""
    
    MP3 = "mp3"
    WAV = "wav"
    OGG = "ogg"
    AAC = "aac"


class VoiceProfile(BaseModel):
    """Voice profile for synthesis."""
    
    profile_id: str
    name: str
    
    # Voice characteristics
    gender: VoiceGender
    style: VoiceStyle
    
    # Prosody defaults
    rate: float = Field(ge=0.5, le=2.0, default=1.0)
    pitch: float = Field(ge=-50.0, le=50.0, default=0.0)
    volume: float = Field(ge=0.0, le=1.0, default=0.8)
    
    # Provider
    provider: str = Field(default="default")
    voice_id: str = Field(default="en-US-Standard-A")
    
    # Psychological alignment
    big_five_alignment: Dict[str, float] = Field(default_factory=dict)


class SSMLDocument(BaseModel):
    """SSML document for speech synthesis."""
    
    ssml: str
    
    # Metadata
    duration_estimate_seconds: Optional[float] = None
    word_count: int = Field(default=0, ge=0)
    
    # Prosody applied
    voice_profile: Optional[str] = None
    
    # Timing
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class AudioVariant(BaseModel):
    """Generated audio variant."""
    
    variant_id: str
    
    # Content
    text: str
    ssml: str
    
    # Audio
    audio_url: Optional[str] = None
    audio_format: AudioFormat = Field(default=AudioFormat.MP3)
    duration_seconds: Optional[float] = None
    
    # Voice
    voice_profile: VoiceProfile
    
    # Psychological context
    target_personality: Dict[str, float] = Field(default_factory=dict)
    framing_applied: List[str] = Field(default_factory=list)
    
    # Timing
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ProsodyModulation(BaseModel):
    """Dynamic prosody modulation based on psychology."""
    
    # Rate adjustments
    rate_multiplier: float = Field(ge=0.5, le=2.0, default=1.0)
    
    # Pitch adjustments
    pitch_adjustment_hz: float = Field(ge=-50.0, le=50.0, default=0.0)
    
    # Emphasis
    emphasis_words: List[str] = Field(default_factory=list)
    
    # Pauses
    sentence_pause_ms: int = Field(ge=0, le=2000, default=500)
    
    # Reasoning
    based_on: Dict[str, Any] = Field(default_factory=dict)
