# =============================================================================
# ADAM Enhancement #19: Identifier Models
# Location: adam/identity/models/identifiers.py
# =============================================================================

"""
Identifier types and classification for cross-platform identity resolution.

Supports:
- Deterministic identifiers (100% confidence)
- Device-level identifiers (high confidence)
- Industry standard IDs (UID2, RampID)
- Probabilistic matching signals
"""

from __future__ import annotations
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Literal
from pydantic import BaseModel, Field, computed_field
import uuid


class IdentifierType(str, Enum):
    """
    Types of identifiers with confidence classification.
    
    Deterministic identifiers provide 100% match confidence.
    Device identifiers provide high confidence with proper handling.
    Probabilistic identifiers require ML matching.
    """
    
    # Deterministic (100% confidence when matched)
    EMAIL_HASH = "email_hash"
    PHONE_HASH = "phone_hash"
    LOGIN_ID = "login_id"
    CUSTOMER_ID = "customer_id"
    CRM_ID = "crm_id"
    
    # Device-based (high confidence with proper handling)
    DEVICE_ID = "device_id"           # Mobile IDFA/GAID
    COOKIE_ID = "cookie_id"           # Browser cookie
    FINGERPRINT = "fingerprint"       # Device fingerprint hash
    IP_HASH = "ip_hash"               # Hashed IP address
    
    # Platform-specific (deterministic within platform)
    IHEART_ID = "iheart_id"
    SPOTIFY_ID = "spotify_id"
    AMAZON_ID = "amazon_id"
    
    # Industry standard (cross-platform)
    UID2 = "uid2"                     # Unified ID 2.0
    RAMP_ID = "ramp_id"               # LiveRamp RampID
    ID5 = "id5"                       # ID5 identifier
    
    # Household-level
    HOUSEHOLD_ID = "household_id"
    POSTAL_HASH = "postal_hash"       # Hashed postal code
    
    # Transient (session-level only)
    SESSION_ID = "session_id"
    REQUEST_ID = "request_id"
    
    @property
    def is_deterministic(self) -> bool:
        """Whether this identifier type provides deterministic matches."""
        return self in {
            IdentifierType.EMAIL_HASH,
            IdentifierType.PHONE_HASH,
            IdentifierType.LOGIN_ID,
            IdentifierType.CUSTOMER_ID,
            IdentifierType.CRM_ID,
            IdentifierType.IHEART_ID,
            IdentifierType.SPOTIFY_ID,
            IdentifierType.AMAZON_ID,
        }
    
    @property
    def is_device_level(self) -> bool:
        """Whether this identifier is device-specific."""
        return self in {
            IdentifierType.DEVICE_ID,
            IdentifierType.COOKIE_ID,
            IdentifierType.FINGERPRINT,
        }
    
    @property
    def is_industry_standard(self) -> bool:
        """Whether this is an industry-standard cross-platform ID."""
        return self in {
            IdentifierType.UID2,
            IdentifierType.RAMP_ID,
            IdentifierType.ID5,
        }
    
    @property
    def persistence_days(self) -> int:
        """Expected persistence of this identifier type in days."""
        persistence_map = {
            IdentifierType.EMAIL_HASH: 3650,      # ~10 years
            IdentifierType.PHONE_HASH: 1825,      # ~5 years
            IdentifierType.LOGIN_ID: 3650,        # ~10 years
            IdentifierType.CUSTOMER_ID: 3650,     # ~10 years
            IdentifierType.DEVICE_ID: 365,        # ~1 year (reset on OS update)
            IdentifierType.COOKIE_ID: 30,         # ~1 month (ITP, browser limits)
            IdentifierType.FINGERPRINT: 90,       # ~3 months (browser changes)
            IdentifierType.IP_HASH: 7,            # ~1 week (dynamic IPs)
            IdentifierType.UID2: 365,             # ~1 year (refresh cycle)
            IdentifierType.RAMP_ID: 365,          # ~1 year
            IdentifierType.HOUSEHOLD_ID: 1095,    # ~3 years
            IdentifierType.SESSION_ID: 0,         # Session only
        }
        return persistence_map.get(self, 30)


class MatchConfidence(str, Enum):
    """Confidence levels for identity matches."""
    DETERMINISTIC = "deterministic"   # 100% certain (same email, login event)
    VERY_HIGH = "very_high"           # >98% confident (multiple strong signals)
    HIGH = "high"                     # 95-98% confident (2+ correlated signals)
    MEDIUM = "medium"                 # 80-95% confident (single strong signal)
    LOW = "low"                       # 60-80% confident (behavioral pattern)
    SPECULATIVE = "speculative"       # 50-60% confident (weak signals)
    INSUFFICIENT = "insufficient"     # <50% confident (do not use)
    
    @property
    def usable_for_targeting(self) -> bool:
        """Whether this confidence level is sufficient for ad targeting."""
        return self in {
            MatchConfidence.DETERMINISTIC,
            MatchConfidence.VERY_HIGH,
            MatchConfidence.HIGH,
            MatchConfidence.MEDIUM,
        }
    
    @property
    def numeric_threshold(self) -> float:
        """Minimum numeric score for this confidence level."""
        thresholds = {
            MatchConfidence.DETERMINISTIC: 1.0,
            MatchConfidence.VERY_HIGH: 0.98,
            MatchConfidence.HIGH: 0.95,
            MatchConfidence.MEDIUM: 0.80,
            MatchConfidence.LOW: 0.60,
            MatchConfidence.SPECULATIVE: 0.50,
            MatchConfidence.INSUFFICIENT: 0.0,
        }
        return thresholds[self]
    
    @classmethod
    def from_score(cls, score: float) -> 'MatchConfidence':
        """Convert numeric score to confidence level."""
        if score >= 1.0:
            return cls.DETERMINISTIC
        elif score >= 0.98:
            return cls.VERY_HIGH
        elif score >= 0.95:
            return cls.HIGH
        elif score >= 0.80:
            return cls.MEDIUM
        elif score >= 0.60:
            return cls.LOW
        elif score >= 0.50:
            return cls.SPECULATIVE
        else:
            return cls.INSUFFICIENT


class IdentifierSource(str, Enum):
    """Source of identifier observation."""
    LOGIN_EVENT = "login_event"
    REGISTRATION = "registration"
    PURCHASE = "purchase"
    PARTNER_SYNC = "partner_sync"
    SDK_COLLECTION = "sdk_collection"
    PIXEL_FIRE = "pixel_fire"
    API_CALL = "api_call"
    CLEAN_ROOM = "clean_room"
    INFERENCE = "inference"


class Identifier(BaseModel):
    """A single identifier for a user."""
    
    class Config:
        frozen = True
    
    identifier_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    identifier_type: IdentifierType
    identifier_value: str = Field(..., min_length=1, max_length=512)
    source: IdentifierSource
    source_system: str
    source_timestamp: datetime = Field(default_factory=datetime.utcnow)
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    observation_count: int = Field(1, ge=1)
    confidence: float = Field(1.0, ge=0.0, le=1.0)
    verified: bool = Field(False)
    consent_for_linking: bool = Field(True)
    
    @computed_field
    @property
    def age_days(self) -> float:
        """Days since first seen."""
        return (datetime.utcnow() - self.first_seen).total_seconds() / 86400
    
    @computed_field
    @property
    def recency_days(self) -> float:
        """Days since last seen."""
        return (datetime.utcnow() - self.last_seen).total_seconds() / 86400
    
    @computed_field
    @property
    def is_stale(self) -> bool:
        """Whether identifier has exceeded its expected persistence."""
        max_age = self.identifier_type.persistence_days
        return self.recency_days > max_age
    
    @computed_field
    @property
    def effective_confidence(self) -> float:
        """Confidence adjusted for recency and verification."""
        base = self.confidence
        
        # Apply recency decay
        if self.recency_days > 0:
            max_days = self.identifier_type.persistence_days
            decay_factor = max(0.5, 1.0 - (self.recency_days / (max_days * 2)))
            base *= decay_factor
        
        # Boost for verification
        if self.verified:
            base = min(1.0, base * 1.1)
        
        return base


class IdentityLink(BaseModel):
    """A link between two identifiers indicating same person."""
    
    link_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_identifier_id: str
    target_identifier_id: str
    source_type: IdentifierType
    target_type: IdentifierType
    match_type: Literal["deterministic", "probabilistic"]
    confidence: MatchConfidence
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    match_signals: List[str] = Field(default_factory=list)
    match_features: Dict[str, float] = Field(default_factory=dict)
    match_algorithm: str = Field("unknown")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_validated: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(True)
    
    @property
    def is_deterministic(self) -> bool:
        """Whether this is a deterministic link."""
        return self.match_type == "deterministic"
