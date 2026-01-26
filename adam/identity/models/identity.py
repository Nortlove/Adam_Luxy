# =============================================================================
# ADAM Enhancement #19: Unified Identity Models
# Location: adam/identity/models/identity.py
# =============================================================================

"""
Unified identity representing one real person across devices and platforms.

A UnifiedIdentity aggregates:
- Multiple identifiers (email, device, platform IDs)
- Links between identifiers
- Household membership
- Consent status
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, computed_field
import uuid

from .identifiers import Identifier, IdentityLink, IdentifierType


class UnifiedIdentity(BaseModel):
    """
    A unified identity representing one real person.
    
    Aggregates identifiers across:
    - Multiple devices (mobile, desktop, tablet)
    - Multiple platforms (iHeart, Spotify, Amazon)
    - Multiple channels (web, app, email)
    """
    
    identity_id: str = Field(
        default_factory=lambda: f"uid_{uuid.uuid4().hex[:16]}"
    )
    
    # Identifiers grouped by type
    identifiers: Dict[str, List[Identifier]] = Field(default_factory=dict)
    
    # Primary identifier (most reliable)
    primary_identifier_type: Optional[IdentifierType] = None
    primary_identifier_value: Optional[str] = None
    
    # Links between identifiers
    links: List[IdentityLink] = Field(default_factory=list)
    
    # Household
    household_id: Optional[str] = None
    household_role: Optional[str] = None  # primary, secondary, child
    
    # Metrics
    total_identifiers: int = Field(0, ge=0)
    deterministic_links: int = Field(0, ge=0)
    probabilistic_links: int = Field(0, ge=0)
    overall_confidence: float = Field(0.5, ge=0.0, le=1.0)
    known_devices: int = Field(0, ge=0)
    active_devices: int = Field(0, ge=0)
    
    # Consent
    linking_consent: bool = Field(True)
    cross_device_consent: bool = Field(True)
    profiling_consent: bool = Field(True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    
    # History
    merge_history: List[str] = Field(default_factory=list)
    
    # Industry IDs (cached for quick access)
    uid2_token: Optional[str] = None
    ramp_id: Optional[str] = None
    iheart_id: Optional[str] = None
    
    def get_identifier(
        self, 
        identifier_type: IdentifierType
    ) -> Optional[Identifier]:
        """Get best identifier of specified type."""
        type_key = identifier_type.value
        if type_key not in self.identifiers or not self.identifiers[type_key]:
            return None
        # Return highest confidence identifier
        return max(
            self.identifiers[type_key], 
            key=lambda x: x.effective_confidence
        )
    
    def get_all_identifier_values(
        self, 
        identifier_type: IdentifierType
    ) -> List[str]:
        """Get all identifier values of specified type."""
        type_key = identifier_type.value
        if type_key not in self.identifiers:
            return []
        return [id.identifier_value for id in self.identifiers[type_key]]
    
    def add_identifier(self, identifier: Identifier) -> None:
        """Add identifier to this identity."""
        type_key = identifier.identifier_type.value
        if type_key not in self.identifiers:
            self.identifiers[type_key] = []
        
        # Check if already exists
        existing = [
            i for i in self.identifiers[type_key]
            if i.identifier_value == identifier.identifier_value
        ]
        if not existing:
            self.identifiers[type_key].append(identifier)
            self.total_identifiers += 1
            
            # Update device count
            if identifier.identifier_type.is_device_level:
                self.known_devices += 1
                if not identifier.is_stale:
                    self.active_devices += 1
    
    @computed_field
    @property
    def is_high_quality(self) -> bool:
        """Whether this is a high-quality identity."""
        return (
            self.overall_confidence >= 0.75 and
            self.total_identifiers >= 2 and
            (self.deterministic_links >= 1 or self.overall_confidence >= 0.90)
        )
    
    @computed_field
    @property
    def profile_completeness(self) -> float:
        """Completeness score for the identity profile (0-1)."""
        has_email = IdentifierType.EMAIL_HASH.value in self.identifiers
        has_device = any(
            t.value in self.identifiers 
            for t in [IdentifierType.DEVICE_ID, IdentifierType.COOKIE_ID]
        )
        has_platform = any(
            t.value in self.identifiers 
            for t in [IdentifierType.IHEART_ID, IdentifierType.SPOTIFY_ID]
        )
        has_industry = any(
            t.value in self.identifiers 
            for t in [IdentifierType.UID2, IdentifierType.RAMP_ID]
        )
        
        score = 0.0
        if has_email: 
            score += 0.3
        if has_device: 
            score += 0.25
        if has_platform: 
            score += 0.25
        if has_industry: 
            score += 0.2
        
        return score
    
    @computed_field
    @property
    def is_cross_device(self) -> bool:
        """Whether identity spans multiple devices."""
        return self.known_devices > 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "identity_id": self.identity_id,
            "total_identifiers": self.total_identifiers,
            "known_devices": self.known_devices,
            "active_devices": self.active_devices,
            "overall_confidence": self.overall_confidence,
            "profile_completeness": self.profile_completeness,
            "household_id": self.household_id,
            "is_high_quality": self.is_high_quality,
            "is_cross_device": self.is_cross_device,
        }


class MatchResult(BaseModel):
    """Result of a match operation."""
    
    match_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query_identifiers: List[Identifier] = Field(default_factory=list)
    query_context: Dict[str, Any] = Field(default_factory=dict)
    
    matched_identity: Optional[UnifiedIdentity] = None
    match_confidence: str = "insufficient"  # MatchConfidence value
    match_score: float = Field(0.0, ge=0.0, le=1.0)
    
    new_identity_created: bool = Field(False)
    match_type: str = "anonymous"  # deterministic, probabilistic, new, anonymous
    
    match_signals: List[str] = Field(default_factory=list)
    match_algorithm: str = Field("unknown")
    
    runner_up_identities: List[tuple] = Field(default_factory=list)
    
    resolution_time_ms: float = Field(0.0)
    candidates_evaluated: int = Field(0)
    
    timestamp: datetime = Field(default_factory=datetime.utcnow)
