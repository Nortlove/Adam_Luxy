# =============================================================================
# ADAM Identity Models
# Location: adam/user/identity/models.py
# =============================================================================

"""
IDENTITY MODELS

Models for cross-platform identity resolution.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field


class IdentityType(str, Enum):
    """Types of identity."""
    
    FIRST_PARTY = "first_party"      # Platform's own ID
    UID2 = "uid2"                    # UID 2.0
    RAMP_ID = "ramp_id"              # LiveRamp RampID
    IHEART = "iheart"                # iHeart user ID
    WPP = "wpp"                      # WPP ID
    EMAIL_HASH = "email_hash"        # Hashed email
    DEVICE = "device"                # Device ID
    ADAM = "adam"                    # ADAM canonical ID


class MatchMethod(str, Enum):
    """Methods used for identity matching."""
    
    DETERMINISTIC = "deterministic"  # Exact match
    PROBABILISTIC = "probabilistic"  # Statistical match
    GRAPH_BASED = "graph_based"      # Graph traversal
    FIRST_PARTY = "first_party"      # Platform provided


class PlatformIdentity(BaseModel):
    """Identity from a specific platform."""
    
    platform: str
    identity_type: IdentityType
    identity_value: str
    
    # Metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_seen_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    # Quality
    confidence: float = Field(ge=0.0, le=1.0, default=0.9)
    is_verified: bool = Field(default=False)


class IdentityMatch(BaseModel):
    """A match between identities."""
    
    match_id: str
    
    source_identity: PlatformIdentity
    target_identity: PlatformIdentity
    
    # Match quality
    match_method: MatchMethod
    match_confidence: float = Field(ge=0.0, le=1.0)
    
    # Evidence
    matching_signals: List[str] = Field(default_factory=list)
    
    # Timing
    matched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class UnifiedIdentity(BaseModel):
    """Unified identity across platforms."""
    
    adam_id: str  # Canonical ADAM ID
    
    # Platform identities
    platform_ids: Dict[str, PlatformIdentity] = Field(default_factory=dict)
    
    # Match history
    matches: List[IdentityMatch] = Field(default_factory=list)
    
    # Profile link
    has_profile: bool = Field(default=False)
    profile_confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    def get_identity(
        self,
        platform: str,
    ) -> Optional[PlatformIdentity]:
        """Get identity for a specific platform."""
        return self.platform_ids.get(platform)
    
    def add_identity(
        self,
        identity: PlatformIdentity,
    ) -> None:
        """Add a platform identity."""
        self.platform_ids[identity.platform] = identity
        self.updated_at = datetime.now(timezone.utc)
