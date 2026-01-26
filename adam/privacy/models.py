# =============================================================================
# ADAM Privacy Models
# Location: adam/privacy/models.py
# =============================================================================

"""
PRIVACY MODELS

Models for consent and privacy management.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field


class ConsentType(str, Enum):
    """Types of consent."""
    
    PSYCHOLOGICAL_PROFILING = "psychological_profiling"
    CROSS_PLATFORM_SHARING = "cross_platform_sharing"
    AD_PERSONALIZATION = "ad_personalization"
    DATA_RETENTION = "data_retention"
    ANALYTICS = "analytics"
    MARKETING = "marketing"


class ConsentStatus(str, Enum):
    """Status of consent."""
    
    GRANTED = "granted"
    DENIED = "denied"
    PENDING = "pending"
    WITHDRAWN = "withdrawn"


class UserConsent(BaseModel):
    """Consent record for a user."""
    
    consent_id: str
    user_id: str
    consent_type: ConsentType
    
    # Status
    status: ConsentStatus
    
    # Scope
    scope: Optional[str] = None  # Specific platforms/categories
    
    # Legal basis
    legal_basis: str = Field(default="consent")  # consent, legitimate_interest, etc.
    
    # Timing
    granted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None
    
    # Source
    consent_source: str = Field(default="direct")  # direct, sdk, import
    ip_address: Optional[str] = None
    
    # Version
    terms_version: str = Field(default="1.0")


class PrivacyPreference(BaseModel):
    """User privacy preferences."""
    
    user_id: str
    
    # Consents
    consents: Dict[str, UserConsent] = Field(default_factory=dict)
    
    # Preferences
    do_not_sell: bool = Field(default=False)
    do_not_track: bool = Field(default=False)
    limit_data_use: bool = Field(default=False)
    
    # Data retention
    preferred_retention_days: Optional[int] = None
    
    # Last updated
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class RequestType(str, Enum):
    """Types of data subject requests."""
    
    ACCESS = "access"           # Right to access
    ERASURE = "erasure"         # Right to erasure
    RECTIFICATION = "rectification"  # Right to correction
    PORTABILITY = "portability"  # Right to data portability
    RESTRICTION = "restriction"  # Right to restrict processing
    OBJECTION = "objection"      # Right to object


class RequestStatus(str, Enum):
    """Status of data subject request."""
    
    RECEIVED = "received"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


class DataSubjectRequest(BaseModel):
    """A data subject rights request."""
    
    request_id: str
    user_id: str
    request_type: RequestType
    
    # Status
    status: RequestStatus
    
    # Details
    description: Optional[str] = None
    affected_data: List[str] = Field(default_factory=list)
    
    # Timing
    submitted_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    deadline: datetime  # 30 days from submission
    completed_at: Optional[datetime] = None
    
    # Response
    response: Optional[str] = None
    data_export_url: Optional[str] = None  # For portability requests


class PrivacyAuditLog(BaseModel):
    """Audit log entry for privacy operations."""
    
    log_id: str
    
    # What
    action: str
    resource_type: str
    resource_id: str
    
    # Who
    user_id: Optional[str] = None
    operator_id: Optional[str] = None
    
    # Details
    details: Dict[str, Any] = Field(default_factory=dict)
    
    # Result
    success: bool
    error_message: Optional[str] = None
    
    # Timing
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
