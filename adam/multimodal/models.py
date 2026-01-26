# =============================================================================
# ADAM Multimodal Models
# Location: adam/multimodal/models.py
# =============================================================================

"""
MULTIMODAL MODELS

Models for cross-modal signal fusion.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field


class Modality(str, Enum):
    """Signal modalities."""
    
    AUDIO = "audio"          # iHeart listening, voice
    VISUAL = "visual"        # Display ads, video
    TEXT = "text"            # Reviews, searches
    BEHAVIORAL = "behavioral"  # Clicks, purchases
    CONTEXTUAL = "contextual"  # Time, location, device


class SignalSource(str, Enum):
    """Source of modality signal."""
    
    IHEART_AUDIO = "iheart_audio"
    IHEART_PODCAST = "iheart_podcast"
    WPP_DISPLAY = "wpp_display"
    WPP_VIDEO = "wpp_video"
    AMAZON_REVIEW = "amazon_review"
    AMAZON_SEARCH = "amazon_search"
    AMAZON_PURCHASE = "amazon_purchase"


class ModalitySignal(BaseModel):
    """A signal from a specific modality."""
    
    signal_id: str
    modality: Modality
    source: SignalSource
    user_id: str
    
    # Signal content
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Extracted features
    features: Dict[str, float] = Field(default_factory=dict)
    
    # Quality
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Timing
    observed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ModalityWeight(BaseModel):
    """Weight for a modality in fusion."""
    
    modality: Modality
    
    # Base weight
    weight: float = Field(ge=0.0, le=1.0)
    
    # Reliability
    reliability: float = Field(ge=0.0, le=1.0, default=0.8)
    
    # Context adjustments
    context_adjustments: Dict[str, float] = Field(default_factory=dict)


class FusedProfile(BaseModel):
    """Profile from multimodal fusion."""
    
    user_id: str
    
    # Fused Big Five
    big_five: Dict[str, float] = Field(default_factory=dict)
    
    # Regulatory focus
    regulatory_focus: Dict[str, float] = Field(default_factory=dict)
    
    # Construal level
    construal_level: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Modality contributions
    modality_contributions: Dict[str, Dict[str, float]] = Field(
        default_factory=dict
    )
    
    # Conflicts detected
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Quality
    overall_confidence: float = Field(ge=0.0, le=1.0)
    modality_coverage: Dict[str, bool] = Field(default_factory=dict)
    
    # Timing
    fused_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
