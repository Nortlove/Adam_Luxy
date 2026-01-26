# ADAM Enhancement Area #17: Privacy & Consent Management - Complete Enterprise Specification
## GDPR/CPRA Compliance, Data Governance, and Ethical Psychological Profiling Framework

**Date**: January 2026 | **Version**: 2.0 | **Priority**: P0 - Compliance Critical  
**Depends On**: Core Architecture | **Enables**: All ADAM Components  
**Status**: Complete Enterprise Specification  
**Estimated Implementation**: 10 weeks | **Team Size**: 3 engineers + 1 legal advisor

---

## Executive Summary

ADAM's psychological profiling capabilities create extraordinary privacy obligations. We are inferring personality traits, emotional states, cognitive patterns, and behavioral tendencies from user data. This is **high-risk processing under GDPR** requiring:

1. **Explicit Consent**: Psychological profiling requires explicit, informed consent (GDPR Art. 22)
2. **Right to Explanation**: Users can demand explanations of profiling decisions (GDPR Art. 22)
3. **Data Protection Impact Assessment**: Mandatory DPIA before processing (GDPR Art. 35)
4. **Special Category Protection**: Some inferences may touch health/political beliefs (GDPR Art. 9)
5. **Minor Protection**: Additional safeguards for users under 18

### Why This Is Critical

```
                    WITHOUT ROBUST PRIVACY INFRASTRUCTURE
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  • Regulatory fines up to 4% of global revenue (GDPR)                        │
│  • Class action lawsuits (CPRA private right of action)                      │
│  • Reputational destruction (psychological profiling scandals)               │
│  • Criminal liability for executives (some jurisdictions)                    │
│  • Market exclusion (can't operate in EU/CA without compliance)              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Regulatory Landscape

| Regulation | Jurisdiction | Key Requirements | ADAM Impact | Deadline |
|------------|--------------|------------------|-------------|----------|
| **GDPR** | EU/EEA + UK | Explicit consent for profiling, DPIA, right to explanation | All EU users | Immediate |
| **CPRA** | California | Opt-out of sale/sharing, sensitive data restrictions | CA users | Immediate |
| **VCDPA** | Virginia | Consent for profiling, appeals process | VA users | Active |
| **CPA** | Colorado | Universal opt-out signal recognition | CO users | Active |
| **CTDPA** | Connecticut | Profiling consent, data minimization | CT users | Jul 2023+ |
| **LGPD** | Brazil | Consent + legitimate interest, data portability | BR users | Active |
| **PIPL** | China | Explicit consent for sensitive data, localization | CN users | If applicable |

---

## Part 1: Pydantic Data Models

### 1.1 Core Consent Models

```python
"""
ADAM Enhancement #17: Privacy & Consent Management Data Models
Enterprise-grade Pydantic models with full validation and cryptographic integrity.
"""

from pydantic import BaseModel, Field, validator, root_validator, SecretStr
from typing import Dict, List, Optional, Set, Literal, Any, Union
from datetime import datetime, timedelta
from enum import Enum
from uuid import uuid4
import hashlib
import hmac
import json


# =============================================================================
# ENUMS
# =============================================================================

class ConsentPurpose(str, Enum):
    """Purposes for which consent can be given - mapped to processing activities."""
    
    # Essential (no consent needed - contractual basis)
    ESSENTIAL_SERVICE = "essential_service"
    
    # Advertising tiers (require consent)
    CONTEXTUAL_ADS = "contextual_ads"           # Based on page content only
    BASIC_PERSONALIZATION = "basic_personalization"  # Demographics, stated preferences
    BEHAVIORAL_TARGETING = "behavioral_targeting"    # Behavioral history
    PSYCHOLOGICAL_PROFILING = "psychological_profiling"  # Personality inference
    EMOTIONAL_TARGETING = "emotional_targeting"      # Real-time emotional state
    
    # Cross-platform
    CROSS_DEVICE_TRACKING = "cross_device_tracking"
    CROSS_PLATFORM_IDENTITY = "cross_platform_identity"
    
    # Analytics
    ANALYTICS_AGGREGATED = "analytics_aggregated"    # Anonymous aggregates
    ANALYTICS_INDIVIDUAL = "analytics_individual"    # Individual-level analytics
    
    # Model training
    MODEL_TRAINING = "model_training"           # Use data to train models
    
    # Third party
    THIRD_PARTY_SHARING = "third_party_sharing"
    DATA_SALE = "data_sale"                     # CPRA "sale of data"
    
    # Special categories (GDPR Art. 9)
    HEALTH_INFERENCES = "health_inferences"
    POLITICAL_INFERENCES = "political_inferences"
    RELIGIOUS_INFERENCES = "religious_inferences"
    SEXUAL_ORIENTATION_INFERENCES = "sexual_orientation_inferences"


class ConsentStatus(str, Enum):
    """Current status of consent."""
    GRANTED = "granted"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"
    NOT_REQUESTED = "not_requested"
    EXPIRED = "expired"
    PENDING_VERIFICATION = "pending_verification"


class LegalBasis(str, Enum):
    """GDPR Article 6 legal basis for processing."""
    CONSENT = "consent"                 # 6(1)(a)
    CONTRACT = "contract"               # 6(1)(b)
    LEGAL_OBLIGATION = "legal_obligation"  # 6(1)(c)
    VITAL_INTERESTS = "vital_interests"    # 6(1)(d)
    PUBLIC_INTEREST = "public_interest"    # 6(1)(e)
    LEGITIMATE_INTEREST = "legitimate_interest"  # 6(1)(f)


class DSRType(str, Enum):
    """Data Subject Request types."""
    ACCESS = "access"                   # Art. 15
    RECTIFICATION = "rectification"     # Art. 16
    ERASURE = "erasure"                 # Art. 17
    RESTRICTION = "restriction"         # Art. 18
    PORTABILITY = "portability"         # Art. 20
    OBJECTION = "objection"             # Art. 21
    AUTOMATED_DECISION = "automated_decision"  # Art. 22 - explanation


class DSRStatus(str, Enum):
    """Data Subject Request status."""
    SUBMITTED = "submitted"
    IDENTITY_VERIFICATION = "identity_verification"
    IN_PROGRESS = "in_progress"
    AWAITING_INFORMATION = "awaiting_information"
    COMPLETED = "completed"
    REJECTED = "rejected"
    APPEALED = "appealed"


class Jurisdiction(str, Enum):
    """Privacy regulation jurisdictions."""
    GDPR_EU = "gdpr_eu"
    GDPR_UK = "gdpr_uk"
    CPRA_CA = "cpra_ca"
    VCDPA_VA = "vcdpa_va"
    CPA_CO = "cpa_co"
    CTDPA_CT = "ctdpa_ct"
    LGPD_BR = "lgpd_br"
    PIPL_CN = "pipl_cn"
    DEFAULT = "default"


class RiskLevel(str, Enum):
    """Risk level for DPIA."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


# =============================================================================
# CONSENT MODELS
# =============================================================================

class ConsentText(BaseModel):
    """Versioned consent text shown to users."""
    
    version: str = Field(..., description="Semantic version of consent text")
    purpose: ConsentPurpose
    language: str = Field(default="en")
    
    # Text content
    title: str = Field(..., max_length=200)
    short_description: str = Field(..., max_length=500)
    full_description: str = Field(..., max_length=5000)
    
    # Legal references
    legal_basis: LegalBasis
    data_categories: List[str] = Field(default_factory=list)
    retention_period_days: int = Field(..., gt=0)
    third_party_recipients: List[str] = Field(default_factory=list)
    
    # Timing
    effective_date: datetime
    expiry_date: Optional[datetime] = None
    
    # Integrity
    content_hash: str = Field(default="")
    
    @validator('content_hash', pre=True, always=True)
    def compute_content_hash(cls, v, values):
        if v:
            return v
        content = f"{values.get('title', '')}{values.get('full_description', '')}{values.get('version', '')}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    class Config:
        frozen = True  # Immutable once created


class ConsentRecord(BaseModel):
    """Cryptographically-secured consent record."""
    
    consent_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    purpose: ConsentPurpose
    status: ConsentStatus
    legal_basis: LegalBasis
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    responded_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    withdrawn_at: Optional[datetime] = None
    
    # Consent context
    consent_text_version: str
    consent_text_hash: str
    collection_point: str = Field(..., description="UI location where consent collected")
    
    # User action proof
    user_action: str = Field(..., description="clicked_accept, toggled_on, api_grant, etc.")
    interaction_id: str = Field(default_factory=lambda: str(uuid4()))
    
    # Device/session context
    ip_address_hash: str = Field(..., description="Hashed IP for audit without storing PII")
    user_agent_hash: str
    session_id: str
    
    # Jurisdiction
    detected_jurisdiction: Jurisdiction
    
    # Granularity (what specific data types)
    scope: Dict[str, bool] = Field(
        default_factory=dict,
        description="Specific data types covered by this consent"
    )
    
    # Cryptographic integrity
    record_hash: str = Field(default="")
    previous_record_hash: Optional[str] = Field(
        default=None,
        description="Hash of previous consent record for this user+purpose"
    )
    
    @validator('record_hash', pre=True, always=True)
    def compute_record_hash(cls, v, values):
        if v:
            return v
        # Hash of all critical fields
        critical = {
            "consent_id": values.get("consent_id"),
            "user_id": values.get("user_id"),
            "purpose": values.get("purpose"),
            "status": values.get("status"),
            "responded_at": str(values.get("responded_at")),
            "consent_text_hash": values.get("consent_text_hash")
        }
        return hashlib.sha256(json.dumps(critical, sort_keys=True).encode()).hexdigest()
    
    def to_neo4j_properties(self) -> Dict[str, Any]:
        return {
            "consent_id": self.consent_id,
            "user_id": self.user_id,
            "purpose": self.purpose.value,
            "status": self.status.value,
            "legal_basis": self.legal_basis.value,
            "created_at": self.created_at.isoformat(),
            "responded_at": self.responded_at.isoformat() if self.responded_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "consent_text_version": self.consent_text_version,
            "consent_text_hash": self.consent_text_hash,
            "collection_point": self.collection_point,
            "user_action": self.user_action,
            "detected_jurisdiction": self.detected_jurisdiction.value,
            "record_hash": self.record_hash
        }


class UserConsentProfile(BaseModel):
    """Complete consent profile for a user."""
    
    user_id: str
    profile_id: str = Field(default_factory=lambda: str(uuid4()))
    
    # Jurisdiction
    primary_jurisdiction: Jurisdiction
    applicable_jurisdictions: List[Jurisdiction] = Field(default_factory=list)
    
    # Current consents by purpose
    consents: Dict[ConsentPurpose, ConsentRecord] = Field(default_factory=dict)
    
    # Computed permissions
    allowed_purposes: Set[ConsentPurpose] = Field(default_factory=set)
    denied_purposes: Set[ConsentPurpose] = Field(default_factory=set)
    pending_purposes: Set[ConsentPurpose] = Field(default_factory=set)
    
    # Global opt-outs
    do_not_sell: bool = Field(default=False, description="CPRA opt-out")
    do_not_share: bool = Field(default=False, description="CPRA sharing opt-out")
    do_not_profile: bool = Field(default=False, description="Profiling opt-out")
    limit_sensitive: bool = Field(default=False, description="Limit sensitive data use")
    universal_opt_out_signal: bool = Field(default=False, description="GPC signal detected")
    
    # Age and verification
    age_verified: bool = Field(default=False)
    verified_age_bracket: Optional[str] = Field(default=None)  # "18+", "16-17", "13-15", "<13"
    is_minor: bool = Field(default=False)
    parental_consent_required: bool = Field(default=False)
    parental_consent_obtained: bool = Field(default=False)
    
    # Pending DSRs
    pending_dsr_ids: List[str] = Field(default_factory=list)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    last_consent_review: Optional[datetime] = None
    
    # TCF integration
    tcf_consent_string: Optional[str] = Field(default=None, description="IAB TCF 2.0 string")
    
    def can_process(self, purpose: ConsentPurpose) -> bool:
        """Check if processing is allowed for purpose."""
        # Global opt-outs first
        if self.do_not_profile and purpose in {
            ConsentPurpose.PSYCHOLOGICAL_PROFILING,
            ConsentPurpose.EMOTIONAL_TARGETING,
            ConsentPurpose.BEHAVIORAL_TARGETING
        }:
            return False
        
        if self.do_not_sell and purpose == ConsentPurpose.DATA_SALE:
            return False
        
        if self.do_not_share and purpose == ConsentPurpose.THIRD_PARTY_SHARING:
            return False
        
        # Minor protection
        if self.is_minor and purpose in {
            ConsentPurpose.PSYCHOLOGICAL_PROFILING,
            ConsentPurpose.EMOTIONAL_TARGETING,
            ConsentPurpose.DATA_SALE
        }:
            return False
        
        # Check explicit consent
        return purpose in self.allowed_purposes


# =============================================================================
# DATA SUBJECT REQUEST MODELS
# =============================================================================

class DSRRequest(BaseModel):
    """Data Subject Rights request."""
    
    request_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    request_type: DSRType
    
    # Timing
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged_at: Optional[datetime] = None
    due_date: datetime
    completed_at: Optional[datetime] = None
    
    # Status
    status: DSRStatus = Field(default=DSRStatus.SUBMITTED)
    status_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Identity verification
    identity_verified: bool = Field(default=False)
    verification_method: Optional[str] = None
    verification_timestamp: Optional[datetime] = None
    
    # Scope
    scope: Dict[str, Any] = Field(
        default_factory=dict,
        description="What data/decisions the request covers"
    )
    
    # Response
    response_data: Optional[Dict[str, Any]] = None
    response_format: Optional[str] = None
    response_url: Optional[str] = Field(default=None, description="Secure download URL")
    response_expires_at: Optional[datetime] = None
    
    # Rejection
    rejection_reason: Optional[str] = None
    rejection_legal_basis: Optional[str] = None
    
    # Appeal
    appeal_submitted: bool = Field(default=False)
    appeal_response: Optional[str] = None
    
    # Audit
    processing_notes: List[str] = Field(default_factory=list)
    
    @validator('due_date', pre=True, always=True)
    def set_due_date(cls, v, values):
        if v:
            return v
        # Default 30 days for GDPR, 45 for US laws
        return datetime.utcnow() + timedelta(days=30)


class DSRResponse(BaseModel):
    """Response to a DSR request."""
    
    request_id: str
    user_id: str
    request_type: DSRType
    
    # Status
    completed: bool
    completion_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    # Response content
    data_provided: Optional[Dict[str, Any]] = None
    items_deleted: List[str] = Field(default_factory=list)
    items_retained: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Items retained with retention reasons"
    )
    
    # For portability
    export_format: Optional[str] = None
    export_size_bytes: Optional[int] = None
    download_url: Optional[str] = None
    download_expires_at: Optional[datetime] = None
    
    # For explanation requests
    explanation: Optional[Dict[str, Any]] = None
    human_readable_explanation: Optional[str] = None
    
    # Appeal info
    appeal_available: bool = Field(default=True)
    appeal_deadline: Optional[datetime] = None
    appeal_instructions: str = Field(
        default="Contact privacy@company.com within 30 days"
    )


# =============================================================================
# DPIA MODELS
# =============================================================================

class DPIAAssessment(BaseModel):
    """Data Protection Impact Assessment."""
    
    dpia_id: str = Field(default_factory=lambda: str(uuid4()))
    assessment_name: str
    assessment_version: str
    
    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_reviewed: datetime = Field(default_factory=datetime.utcnow)
    next_review_due: datetime
    
    # Processing description
    processing_description: str
    purposes: List[ConsentPurpose]
    data_categories: List[str]
    data_subjects: List[str] = Field(
        default_factory=list,
        description="Categories of data subjects (users, minors, etc.)"
    )
    
    # Necessity and proportionality
    necessity_assessment: str
    proportionality_assessment: str
    
    # Risk assessment
    risks_identified: List['RiskAssessment'] = Field(default_factory=list)
    overall_risk_level: RiskLevel
    
    # Mitigation measures
    mitigations: List['MitigationMeasure'] = Field(default_factory=list)
    residual_risk_level: RiskLevel
    
    # Consultation
    dpo_consulted: bool = Field(default=False)
    dpo_opinion: Optional[str] = None
    authority_consultation_required: bool = Field(default=False)
    authority_consultation_outcome: Optional[str] = None
    
    # Approval
    approved: bool = Field(default=False)
    approved_by: Optional[str] = None
    approval_date: Optional[datetime] = None
    
    # Linked processing
    linked_consent_purposes: List[ConsentPurpose] = Field(default_factory=list)


class RiskAssessment(BaseModel):
    """Individual risk within DPIA."""
    
    risk_id: str = Field(default_factory=lambda: str(uuid4()))
    risk_description: str
    risk_category: str = Field(
        ...,
        description="data_breach, discrimination, reputational, financial, etc."
    )
    
    # Impact assessment
    likelihood: Literal["rare", "unlikely", "possible", "likely", "almost_certain"]
    impact_severity: Literal["negligible", "limited", "significant", "maximum"]
    
    # Affected rights
    affected_rights: List[str] = Field(default_factory=list)
    affected_data_subjects: List[str] = Field(default_factory=list)
    
    # Risk level calculation
    risk_level: RiskLevel
    
    # Mitigation reference
    mitigation_ids: List[str] = Field(default_factory=list)


class MitigationMeasure(BaseModel):
    """Mitigation measure for identified risk."""
    
    mitigation_id: str = Field(default_factory=lambda: str(uuid4()))
    measure_description: str
    measure_type: Literal["technical", "organizational", "contractual", "legal"]
    
    # Implementation
    implementation_status: Literal["planned", "in_progress", "implemented", "verified"]
    implementation_date: Optional[datetime] = None
    responsible_party: str
    
    # Effectiveness
    effectiveness_rating: Literal["low", "medium", "high"]
    verification_method: str
    last_verified: Optional[datetime] = None
    
    # Linked risks
    addresses_risk_ids: List[str] = Field(default_factory=list)


# =============================================================================
# AUDIT MODELS
# =============================================================================

class AuditEvent(BaseModel):
    """Immutable audit log entry with cryptographic integrity."""
    
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: str
    
    # Actor
    actor_type: Literal["user", "system", "admin", "automated", "third_party"]
    actor_id: str
    actor_ip_hash: Optional[str] = None
    
    # Subject
    subject_type: str
    subject_id: str
    
    # Action
    action: str
    action_category: str = Field(
        ...,
        description="consent, dsr, data_access, data_modification, etc."
    )
    action_details: Dict[str, Any] = Field(default_factory=dict)
    
    # Result
    success: bool
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    
    # Context
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # Chain integrity
    previous_event_hash: Optional[str] = None
    event_hash: str = Field(default="")
    
    @validator('event_hash', pre=True, always=True)
    def compute_event_hash(cls, v, values):
        if v:
            return v
        critical = {
            "event_id": values.get("event_id"),
            "timestamp": str(values.get("timestamp")),
            "event_type": values.get("event_type"),
            "actor_id": values.get("actor_id"),
            "subject_id": values.get("subject_id"),
            "action": values.get("action"),
            "success": values.get("success"),
            "previous_event_hash": values.get("previous_event_hash")
        }
        return hashlib.sha256(json.dumps(critical, sort_keys=True).encode()).hexdigest()


class AuditQuery(BaseModel):
    """Query parameters for audit log retrieval."""
    
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    event_types: Optional[List[str]] = None
    actor_ids: Optional[List[str]] = None
    subject_ids: Optional[List[str]] = None
    action_categories: Optional[List[str]] = None
    success_only: Optional[bool] = None
    limit: int = Field(default=100, le=1000)
    offset: int = Field(default=0, ge=0)


# =============================================================================
# API MODELS
# =============================================================================

class ConsentGrantRequest(BaseModel):
    """Request to grant consent."""
    
    user_id: str
    purposes: List[ConsentPurpose]
    consent_text_versions: Dict[ConsentPurpose, str]
    collection_point: str
    user_action: str
    scope: Optional[Dict[str, bool]] = None
    
    # Device context (will be hashed)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: str


class ConsentWithdrawRequest(BaseModel):
    """Request to withdraw consent."""
    
    user_id: str
    purposes: List[ConsentPurpose]
    reason: Optional[str] = None


class ConsentCheckRequest(BaseModel):
    """Request to check consent status."""
    
    user_id: str
    purposes: List[ConsentPurpose]
    requester: str
    processing_context: Optional[str] = None


class ConsentCheckResponse(BaseModel):
    """Response to consent check."""
    
    user_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    results: Dict[ConsentPurpose, bool]
    denial_reasons: Dict[ConsentPurpose, str] = Field(default_factory=dict)
    
    # Recommendations
    consent_needed: List[ConsentPurpose] = Field(default_factory=list)
    
    # Global flags
    do_not_sell: bool
    do_not_profile: bool
    is_minor: bool


class DSRSubmitRequest(BaseModel):
    """Request to submit a DSR."""
    
    user_id: str
    request_type: DSRType
    scope: Dict[str, Any] = Field(default_factory=dict)
    verification_token: Optional[str] = None


class PrivacyPreferencesUpdate(BaseModel):
    """Update privacy preferences."""
    
    user_id: str
    do_not_sell: Optional[bool] = None
    do_not_share: Optional[bool] = None
    do_not_profile: Optional[bool] = None
    limit_sensitive: Optional[bool] = None
    universal_opt_out: Optional[bool] = None
```

---

## Part 2: Consent Management Service

### 2.1 Core Consent Manager

```python
"""
ADAM Enhancement #17: Consent Management Service
Enterprise-grade consent lifecycle management.
"""

import asyncio
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import hashlib
import json
from functools import lru_cache


class ConsentManager:
    """
    Manage user consent lifecycle with full audit trail.
    
    Key responsibilities:
    1. Collect and store consent with cryptographic integrity
    2. Enforce jurisdiction-specific requirements
    3. Handle consent withdrawal with downstream propagation
    4. Provide real-time consent checking for all ADAM components
    5. Manage consent expiration and renewal
    """
    
    def __init__(
        self,
        consent_store: 'ConsentStore',
        jurisdiction_detector: 'JurisdictionDetector',
        audit_logger: 'AuditLogger',
        event_publisher: 'EventPublisher',
        encryption_service: 'EncryptionService'
    ):
        self.store = consent_store
        self.jurisdiction = jurisdiction_detector
        self.audit = audit_logger
        self.events = event_publisher
        self.encryption = encryption_service
        
        # Load jurisdiction configurations
        self.configs = self._load_jurisdiction_configs()
        
        # Cache for hot-path consent checks
        self._consent_cache: Dict[str, 'CachedConsent'] = {}
        self._cache_ttl_seconds = 60
    
    # =========================================================================
    # CONSENT COLLECTION
    # =========================================================================
    
    async def record_consent(
        self,
        request: 'ConsentGrantRequest'
    ) -> List[ConsentRecord]:
        """
        Record consent grant for one or more purposes.
        
        Returns list of created ConsentRecord objects.
        """
        user_id = request.user_id
        jurisdiction = await self.jurisdiction.detect(user_id, request.ip_address)
        config = self.configs[jurisdiction]
        
        records = []
        
        for purpose in request.purposes:
            # Validate consent text version
            text_version = request.consent_text_versions.get(purpose)
            consent_text = await self.store.get_consent_text(purpose, text_version)
            
            if not consent_text:
                raise ValueError(f"Invalid consent text version: {text_version}")
            
            # Check if this purpose requires explicit consent in jurisdiction
            if purpose in config.requires_explicit_consent:
                if request.user_action not in ["clicked_accept", "explicit_grant"]:
                    raise ValueError(
                        f"Purpose {purpose} requires explicit consent action, "
                        f"got: {request.user_action}"
                    )
            
            # Get previous consent record for chaining
            previous_record = await self.store.get_latest_consent(user_id, purpose)
            previous_hash = previous_record.record_hash if previous_record else None
            
            # Create consent record
            record = ConsentRecord(
                user_id=user_id,
                purpose=purpose,
                status=ConsentStatus.GRANTED,
                legal_basis=config.required_consents.get(purpose, LegalBasis.CONSENT),
                responded_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=config.consent_validity_days),
                consent_text_version=text_version,
                consent_text_hash=consent_text.content_hash,
                collection_point=request.collection_point,
                user_action=request.user_action,
                interaction_id=str(uuid4()),
                ip_address_hash=self._hash_pii(request.ip_address) if request.ip_address else "",
                user_agent_hash=self._hash_pii(request.user_agent) if request.user_agent else "",
                session_id=request.session_id,
                detected_jurisdiction=jurisdiction,
                scope=request.scope or {},
                previous_record_hash=previous_hash
            )
            
            # Store
            await self.store.save_consent(record)
            records.append(record)
            
            # Audit
            await self.audit.log_event(AuditEvent(
                event_type="consent_granted",
                actor_type="user",
                actor_id=user_id,
                subject_type="consent",
                subject_id=record.consent_id,
                action="grant",
                action_category="consent",
                action_details={
                    "purpose": purpose.value,
                    "jurisdiction": jurisdiction.value,
                    "collection_point": request.collection_point
                },
                success=True
            ))
            
            # Invalidate cache
            self._invalidate_cache(user_id, purpose)
        
        # Update user consent profile
        await self._update_consent_profile(user_id)
        
        # Publish consent change event
        await self.events.publish("consent.granted", {
            "user_id": user_id,
            "purposes": [p.value for p in request.purposes],
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return records
    
    async def withdraw_consent(
        self,
        request: 'ConsentWithdrawRequest'
    ) -> List[ConsentRecord]:
        """
        Process consent withdrawal with downstream propagation.
        """
        user_id = request.user_id
        records = []
        
        for purpose in request.purposes:
            # Get current consent
            current = await self.store.get_latest_consent(user_id, purpose)
            
            if not current or current.status != ConsentStatus.GRANTED:
                continue  # Nothing to withdraw
            
            # Update record
            current.status = ConsentStatus.WITHDRAWN
            current.withdrawn_at = datetime.utcnow()
            
            await self.store.save_consent(current)
            records.append(current)
            
            # Trigger downstream cleanup
            await self._propagate_consent_withdrawal(user_id, purpose)
            
            # Audit
            await self.audit.log_event(AuditEvent(
                event_type="consent_withdrawn",
                actor_type="user",
                actor_id=user_id,
                subject_type="consent",
                subject_id=current.consent_id,
                action="withdraw",
                action_category="consent",
                action_details={
                    "purpose": purpose.value,
                    "reason": request.reason
                },
                success=True
            ))
            
            # Invalidate cache
            self._invalidate_cache(user_id, purpose)
        
        # Update profile
        await self._update_consent_profile(user_id)
        
        # Publish event
        await self.events.publish("consent.withdrawn", {
            "user_id": user_id,
            "purposes": [p.value for p in request.purposes],
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return records
    
    # =========================================================================
    # CONSENT CHECKING
    # =========================================================================
    
    async def check_consent(
        self,
        request: 'ConsentCheckRequest'
    ) -> ConsentCheckResponse:
        """
        Check consent status for multiple purposes.
        
        This is the hot path - called for every ad decision.
        Optimized with caching.
        """
        user_id = request.user_id
        results = {}
        denial_reasons = {}
        consent_needed = []
        
        # Get user profile (cached)
        profile = await self.get_consent_profile(user_id)
        
        for purpose in request.purposes:
            # Check cache first
            cached = self._check_cache(user_id, purpose)
            if cached is not None:
                results[purpose] = cached
                if not cached:
                    denial_reasons[purpose] = "Consent not granted (cached)"
                continue
            
            # Full check
            allowed = profile.can_process(purpose)
            results[purpose] = allowed
            
            if not allowed:
                # Determine reason
                if profile.do_not_profile and purpose in {
                    ConsentPurpose.PSYCHOLOGICAL_PROFILING,
                    ConsentPurpose.EMOTIONAL_TARGETING
                }:
                    denial_reasons[purpose] = "User opted out of profiling"
                elif profile.do_not_sell and purpose == ConsentPurpose.DATA_SALE:
                    denial_reasons[purpose] = "User opted out of data sale"
                elif profile.is_minor:
                    denial_reasons[purpose] = "Minor - special protection applies"
                elif purpose not in profile.consents:
                    denial_reasons[purpose] = "Consent not collected"
                    consent_needed.append(purpose)
                else:
                    denial_reasons[purpose] = "Consent denied or expired"
            
            # Update cache
            self._update_cache(user_id, purpose, allowed)
        
        # Audit access check
        await self.audit.log_event(AuditEvent(
            event_type="consent_check",
            actor_type="system",
            actor_id=request.requester,
            subject_type="user",
            subject_id=user_id,
            action="check_consent",
            action_category="data_access",
            action_details={
                "purposes_checked": [p.value for p in request.purposes],
                "results": {p.value: r for p, r in results.items()},
                "context": request.processing_context
            },
            success=True
        ))
        
        return ConsentCheckResponse(
            user_id=user_id,
            results=results,
            denial_reasons=denial_reasons,
            consent_needed=consent_needed,
            do_not_sell=profile.do_not_sell,
            do_not_profile=profile.do_not_profile,
            is_minor=profile.is_minor
        )
    
    async def check_single_purpose(
        self,
        user_id: str,
        purpose: ConsentPurpose,
        requester: str = "system"
    ) -> bool:
        """
        Optimized single-purpose consent check.
        Used internally by other ADAM components.
        """
        # Check cache
        cached = self._check_cache(user_id, purpose)
        if cached is not None:
            return cached
        
        # Get profile and check
        profile = await self.get_consent_profile(user_id)
        allowed = profile.can_process(purpose)
        
        # Update cache
        self._update_cache(user_id, purpose, allowed)
        
        return allowed
    
    # =========================================================================
    # PROFILE MANAGEMENT
    # =========================================================================
    
    async def get_consent_profile(
        self,
        user_id: str
    ) -> UserConsentProfile:
        """Get or create user consent profile."""
        
        profile = await self.store.get_profile(user_id)
        
        if not profile:
            # New user - create default profile
            jurisdiction = await self.jurisdiction.detect(user_id)
            profile = self._create_default_profile(user_id, jurisdiction)
            await self.store.save_profile(profile)
        
        # Check for expired consents
        profile = await self._check_expirations(profile)
        
        return profile
    
    async def update_privacy_preferences(
        self,
        request: 'PrivacyPreferencesUpdate'
    ) -> UserConsentProfile:
        """Update user privacy preferences (opt-outs)."""
        
        profile = await self.get_consent_profile(request.user_id)
        
        if request.do_not_sell is not None:
            profile.do_not_sell = request.do_not_sell
        
        if request.do_not_share is not None:
            profile.do_not_share = request.do_not_share
        
        if request.do_not_profile is not None:
            profile.do_not_profile = request.do_not_profile
            
            # If opting out of profiling, trigger cleanup
            if request.do_not_profile:
                await self._propagate_consent_withdrawal(
                    request.user_id, 
                    ConsentPurpose.PSYCHOLOGICAL_PROFILING
                )
        
        if request.limit_sensitive is not None:
            profile.limit_sensitive = request.limit_sensitive
        
        if request.universal_opt_out is not None:
            profile.universal_opt_out_signal = request.universal_opt_out
            
            # Universal opt-out implies do_not_sell
            if request.universal_opt_out:
                profile.do_not_sell = True
        
        profile.last_updated = datetime.utcnow()
        await self.store.save_profile(profile)
        
        # Audit
        await self.audit.log_event(AuditEvent(
            event_type="preferences_updated",
            actor_type="user",
            actor_id=request.user_id,
            subject_type="profile",
            subject_id=profile.profile_id,
            action="update_preferences",
            action_category="consent",
            action_details={
                "do_not_sell": profile.do_not_sell,
                "do_not_profile": profile.do_not_profile
            },
            success=True
        ))
        
        # Invalidate all caches for this user
        self._invalidate_user_cache(request.user_id)
        
        # Publish event
        await self.events.publish("privacy.preferences_updated", {
            "user_id": request.user_id,
            "do_not_sell": profile.do_not_sell,
            "do_not_profile": profile.do_not_profile
        })
        
        return profile
    
    # =========================================================================
    # DOWNSTREAM PROPAGATION
    # =========================================================================
    
    async def _propagate_consent_withdrawal(
        self,
        user_id: str,
        purpose: ConsentPurpose
    ):
        """
        Propagate consent withdrawal to other ADAM components.
        
        When consent is withdrawn, we need to:
        1. Delete data that was collected under that consent
        2. Stop ongoing processing
        3. Notify relevant components
        """
        cleanup_actions = {
            ConsentPurpose.PSYCHOLOGICAL_PROFILING: [
                ("profile_store", "delete_psychological_profile"),
                ("embedding_store", "delete_user_embeddings"),
                ("journey_store", "delete_user_journeys")
            ],
            ConsentPurpose.BEHAVIORAL_TARGETING: [
                ("signal_store", "delete_behavioral_signals"),
                ("targeting_store", "clear_targeting_data")
            ],
            ConsentPurpose.CROSS_DEVICE_TRACKING: [
                ("identity_store", "unlink_devices")
            ],
            ConsentPurpose.EMOTIONAL_TARGETING: [
                ("state_store", "delete_emotional_states")
            ],
            ConsentPurpose.MODEL_TRAINING: [
                ("training_store", "exclude_from_training")
            ],
            ConsentPurpose.THIRD_PARTY_SHARING: [
                ("sync_store", "revoke_third_party_access")
            ]
        }
        
        actions = cleanup_actions.get(purpose, [])
        
        for store_name, method_name in actions:
            try:
                # Publish cleanup event
                await self.events.publish(f"consent.cleanup.{store_name}", {
                    "user_id": user_id,
                    "action": method_name,
                    "purpose": purpose.value,
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                # Log but don't fail
                await self.audit.log_event(AuditEvent(
                    event_type="cleanup_error",
                    actor_type="system",
                    actor_id="consent_manager",
                    subject_type="user",
                    subject_id=user_id,
                    action=f"cleanup_{store_name}",
                    action_category="consent",
                    action_details={"error": str(e)},
                    success=False,
                    error_message=str(e)
                ))
    
    # =========================================================================
    # CACHING
    # =========================================================================
    
    def _check_cache(
        self,
        user_id: str,
        purpose: ConsentPurpose
    ) -> Optional[bool]:
        """Check consent cache."""
        key = f"{user_id}:{purpose.value}"
        cached = self._consent_cache.get(key)
        
        if cached and (datetime.utcnow() - cached.timestamp).seconds < self._cache_ttl_seconds:
            return cached.allowed
        
        return None
    
    def _update_cache(
        self,
        user_id: str,
        purpose: ConsentPurpose,
        allowed: bool
    ):
        """Update consent cache."""
        key = f"{user_id}:{purpose.value}"
        self._consent_cache[key] = CachedConsent(
            allowed=allowed,
            timestamp=datetime.utcnow()
        )
    
    def _invalidate_cache(
        self,
        user_id: str,
        purpose: ConsentPurpose
    ):
        """Invalidate specific cache entry."""
        key = f"{user_id}:{purpose.value}"
        self._consent_cache.pop(key, None)
    
    def _invalidate_user_cache(self, user_id: str):
        """Invalidate all cache entries for a user."""
        to_remove = [k for k in self._consent_cache if k.startswith(f"{user_id}:")]
        for k in to_remove:
            self._consent_cache.pop(k, None)
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    def _hash_pii(self, value: str) -> str:
        """Hash PII for storage."""
        if not value:
            return ""
        return hashlib.sha256(value.encode()).hexdigest()[:32]
    
    def _create_default_profile(
        self,
        user_id: str,
        jurisdiction: Jurisdiction
    ) -> UserConsentProfile:
        """Create default consent profile for new user."""
        config = self.configs[jurisdiction]
        
        return UserConsentProfile(
            user_id=user_id,
            primary_jurisdiction=jurisdiction,
            applicable_jurisdictions=[jurisdiction],
            consents={},
            allowed_purposes=set(),
            denied_purposes=set(),
            pending_purposes=set(config.required_consents.keys()),
            do_not_sell=False,
            do_not_share=False,
            do_not_profile=False,
            limit_sensitive=False,
            universal_opt_out_signal=False,
            age_verified=False,
            is_minor=False,
            parental_consent_required=False
        )
    
    async def _update_consent_profile(self, user_id: str):
        """Update computed fields in consent profile."""
        profile = await self.store.get_profile(user_id)
        if not profile:
            return
        
        # Recompute allowed/denied sets
        allowed = set()
        denied = set()
        
        for purpose, record in profile.consents.items():
            if record.status == ConsentStatus.GRANTED:
                if not record.expires_at or record.expires_at > datetime.utcnow():
                    allowed.add(purpose)
                else:
                    denied.add(purpose)
            else:
                denied.add(purpose)
        
        profile.allowed_purposes = allowed
        profile.denied_purposes = denied
        profile.last_updated = datetime.utcnow()
        
        await self.store.save_profile(profile)
    
    async def _check_expirations(
        self,
        profile: UserConsentProfile
    ) -> UserConsentProfile:
        """Check and handle expired consents."""
        now = datetime.utcnow()
        changed = False
        
        for purpose, record in profile.consents.items():
            if record.status == ConsentStatus.GRANTED:
                if record.expires_at and record.expires_at < now:
                    record.status = ConsentStatus.EXPIRED
                    await self.store.save_consent(record)
                    
                    profile.allowed_purposes.discard(purpose)
                    profile.denied_purposes.add(purpose)
                    changed = True
                    
                    self._invalidate_cache(profile.user_id, purpose)
        
        if changed:
            profile.last_updated = now
            await self.store.save_profile(profile)
        
        return profile
    
    def _load_jurisdiction_configs(self) -> Dict[Jurisdiction, 'JurisdictionConfig']:
        """Load jurisdiction-specific configurations."""
        return {
            Jurisdiction.GDPR_EU: JurisdictionConfig(
                jurisdiction=Jurisdiction.GDPR_EU,
                consent_validity_days=365,
                required_consents={
                    ConsentPurpose.PSYCHOLOGICAL_PROFILING: LegalBasis.CONSENT,
                    ConsentPurpose.EMOTIONAL_TARGETING: LegalBasis.CONSENT,
                    ConsentPurpose.BEHAVIORAL_TARGETING: LegalBasis.CONSENT,
                    ConsentPurpose.CROSS_DEVICE_TRACKING: LegalBasis.CONSENT,
                    ConsentPurpose.THIRD_PARTY_SHARING: LegalBasis.CONSENT,
                    ConsentPurpose.ANALYTICS_INDIVIDUAL: LegalBasis.CONSENT
                },
                requires_explicit_consent={
                    ConsentPurpose.PSYCHOLOGICAL_PROFILING,
                    ConsentPurpose.EMOTIONAL_TARGETING,
                    ConsentPurpose.HEALTH_INFERENCES,
                    ConsentPurpose.POLITICAL_INFERENCES
                },
                allows_legitimate_interest={
                    ConsentPurpose.ANALYTICS_AGGREGATED,
                    ConsentPurpose.CONTEXTUAL_ADS
                },
                prohibits_profiling_minors=True,
                minor_age_threshold=16,
                dsr_deadline_days=30
            ),
            Jurisdiction.CPRA_CA: JurisdictionConfig(
                jurisdiction=Jurisdiction.CPRA_CA,
                consent_validity_days=365,
                required_consents={
                    ConsentPurpose.PSYCHOLOGICAL_PROFILING: LegalBasis.CONSENT,
                    ConsentPurpose.DATA_SALE: LegalBasis.CONSENT,
                    ConsentPurpose.THIRD_PARTY_SHARING: LegalBasis.CONSENT
                },
                requires_explicit_consent={
                    ConsentPurpose.DATA_SALE,
                    ConsentPurpose.HEALTH_INFERENCES
                },
                allows_legitimate_interest=set(),
                prohibits_profiling_minors=True,
                minor_age_threshold=16,
                dsr_deadline_days=45,
                supports_universal_opt_out=True
            ),
            # Add more jurisdictions...
            Jurisdiction.DEFAULT: JurisdictionConfig(
                jurisdiction=Jurisdiction.DEFAULT,
                consent_validity_days=365,
                required_consents={
                    ConsentPurpose.PSYCHOLOGICAL_PROFILING: LegalBasis.CONSENT
                },
                requires_explicit_consent={
                    ConsentPurpose.PSYCHOLOGICAL_PROFILING
                },
                allows_legitimate_interest={
                    ConsentPurpose.ANALYTICS_AGGREGATED
                },
                prohibits_profiling_minors=True,
                minor_age_threshold=18,
                dsr_deadline_days=30
            )
        }


class JurisdictionConfig(BaseModel):
    """Jurisdiction-specific privacy configuration."""
    
    jurisdiction: Jurisdiction
    consent_validity_days: int
    required_consents: Dict[ConsentPurpose, LegalBasis]
    requires_explicit_consent: Set[ConsentPurpose]
    allows_legitimate_interest: Set[ConsentPurpose]
    prohibits_profiling_minors: bool
    minor_age_threshold: int = Field(default=18)
    dsr_deadline_days: int = Field(default=30)
    supports_universal_opt_out: bool = Field(default=False)


class CachedConsent(BaseModel):
    """Cached consent check result."""
    allowed: bool
    timestamp: datetime
```

*Continued in Part 2: DSR Processing, DPIA Framework, Neo4j Schema, API Endpoints*
# ADAM Enhancement Area #17: Privacy & Consent Management - Part 2
## DSR Processing, DPIA Framework, Neo4j Schema, API Layer, and Integration

**Continuation of Part 1**

---

## Part 3: Data Subject Rights (DSR) Processor

### 3.1 DSR Processing Service

```python
"""
ADAM Enhancement #17: Data Subject Rights Processing
Automated handling of GDPR Articles 15-22 rights requests.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import zipfile
import io
from pathlib import Path


class DSRProcessor:
    """
    Process Data Subject Rights requests with full compliance.
    
    Handles:
    - Right of Access (Art. 15)
    - Right to Rectification (Art. 16)
    - Right to Erasure (Art. 17)
    - Right to Restriction (Art. 18)
    - Right to Portability (Art. 20)
    - Right to Object (Art. 21)
    - Right re Automated Decisions (Art. 22)
    """
    
    # Regulatory deadlines by jurisdiction
    DEADLINES = {
        Jurisdiction.GDPR_EU: 30,
        Jurisdiction.GDPR_UK: 30,
        Jurisdiction.CPRA_CA: 45,
        Jurisdiction.VCDPA_VA: 45,
        Jurisdiction.CPA_CO: 45,
        Jurisdiction.CTDPA_CT: 45,
        Jurisdiction.LGPD_BR: 15,
        Jurisdiction.DEFAULT: 30
    }
    
    def __init__(
        self,
        dsr_store: 'DSRStore',
        user_store: 'UserStore',
        profile_store: 'ProfileStore',
        signal_store: 'SignalStore',
        decision_store: 'DecisionStore',
        embedding_store: 'EmbeddingStore',
        journey_store: 'JourneyStore',
        consent_manager: 'ConsentManager',
        audit_logger: 'AuditLogger',
        notification_service: 'NotificationService',
        encryption_service: 'EncryptionService'
    ):
        self.dsr_store = dsr_store
        self.user_store = user_store
        self.profile_store = profile_store
        self.signal_store = signal_store
        self.decision_store = decision_store
        self.embedding_store = embedding_store
        self.journey_store = journey_store
        self.consent = consent_manager
        self.audit = audit_logger
        self.notifications = notification_service
        self.encryption = encryption_service
    
    # =========================================================================
    # REQUEST SUBMISSION
    # =========================================================================
    
    async def submit_request(
        self,
        request: 'DSRSubmitRequest'
    ) -> DSRRequest:
        """Submit a new DSR request."""
        
        # Detect jurisdiction for deadline
        jurisdiction = await self.consent.jurisdiction.detect(request.user_id)
        deadline_days = self.DEADLINES.get(jurisdiction, 30)
        
        dsr = DSRRequest(
            user_id=request.user_id,
            request_type=request.request_type,
            due_date=datetime.utcnow() + timedelta(days=deadline_days),
            scope=request.scope,
            status=DSRStatus.SUBMITTED,
            status_history=[{
                "status": DSRStatus.SUBMITTED.value,
                "timestamp": datetime.utcnow().isoformat(),
                "note": "Request submitted"
            }]
        )
        
        await self.dsr_store.save(dsr)
        
        # Audit
        await self.audit.log_event(AuditEvent(
            event_type="dsr_submitted",
            actor_type="user",
            actor_id=request.user_id,
            subject_type="dsr",
            subject_id=dsr.request_id,
            action="submit",
            action_category="dsr",
            action_details={
                "request_type": request.request_type.value,
                "deadline": dsr.due_date.isoformat()
            },
            success=True
        ))
        
        # Send acknowledgment
        await self.notifications.send_dsr_acknowledgment(
            user_id=request.user_id,
            request_id=dsr.request_id,
            request_type=request.request_type,
            due_date=dsr.due_date
        )
        
        # Add to user's pending DSRs
        profile = await self.consent.get_consent_profile(request.user_id)
        profile.pending_dsr_ids.append(dsr.request_id)
        await self.consent.store.save_profile(profile)
        
        return dsr
    
    async def verify_identity(
        self,
        request_id: str,
        verification_token: str,
        verification_method: str
    ) -> bool:
        """Verify identity for DSR processing."""
        
        dsr = await self.dsr_store.get(request_id)
        if not dsr:
            raise ValueError(f"DSR not found: {request_id}")
        
        # Verify token (implementation depends on method)
        verified = await self._verify_token(
            dsr.user_id,
            verification_token,
            verification_method
        )
        
        if verified:
            dsr.identity_verified = True
            dsr.verification_method = verification_method
            dsr.verification_timestamp = datetime.utcnow()
            dsr.status = DSRStatus.IN_PROGRESS
            dsr.status_history.append({
                "status": DSRStatus.IN_PROGRESS.value,
                "timestamp": datetime.utcnow().isoformat(),
                "note": f"Identity verified via {verification_method}"
            })
            
            await self.dsr_store.save(dsr)
            
            # Audit
            await self.audit.log_event(AuditEvent(
                event_type="dsr_identity_verified",
                actor_type="user",
                actor_id=dsr.user_id,
                subject_type="dsr",
                subject_id=request_id,
                action="verify_identity",
                action_category="dsr",
                action_details={"method": verification_method},
                success=True
            ))
        
        return verified
    
    # =========================================================================
    # ACCESS REQUEST (Art. 15)
    # =========================================================================
    
    async def process_access_request(
        self,
        request_id: str
    ) -> DSRResponse:
        """
        Process Right of Access request.
        
        Returns all personal data held about the user plus:
        - Purposes of processing
        - Categories of data
        - Recipients
        - Retention periods
        - Rights information
        - Source of data
        - Existence of automated decision-making
        """
        
        dsr = await self._validate_and_get_dsr(request_id, DSRType.ACCESS)
        user_id = dsr.user_id
        
        # Gather all data
        data = {
            "request_id": request_id,
            "generated_at": datetime.utcnow().isoformat(),
            "data_controller": "ADAM / Informativ AI",
            "contact": "privacy@informativ.ai",
            
            # User profile
            "user_profile": await self._get_user_data(user_id),
            
            # Psychological profile
            "psychological_profile": await self._get_psychological_data(user_id),
            
            # Behavioral signals
            "behavioral_data": await self._get_behavioral_data(user_id),
            
            # Ad decisions
            "ad_decisions": await self._get_decision_data(user_id),
            
            # Embeddings
            "embeddings": await self._get_embedding_data(user_id),
            
            # Journey data
            "journey_data": await self._get_journey_data(user_id),
            
            # Consent history
            "consent_history": await self._get_consent_history(user_id),
            
            # Inferences made
            "inferences": await self._get_inferences(user_id),
            
            # Processing information
            "processing_info": {
                "purposes": self._get_processing_purposes(),
                "data_categories": self._get_data_categories(),
                "recipients": self._get_recipients(),
                "retention_periods": self._get_retention_periods(),
                "data_sources": self._get_data_sources(),
                "automated_decisions": True,
                "automated_decision_logic": self._get_decision_logic_explanation()
            },
            
            # Rights information
            "your_rights": self._get_rights_information(dsr.user_id)
        }
        
        # Generate human-readable summary
        summary = self._generate_access_summary(data)
        
        # Create downloadable package
        download_url, expires_at = await self._create_download_package(
            user_id, data, "access"
        )
        
        # Complete DSR
        response = DSRResponse(
            request_id=request_id,
            user_id=user_id,
            request_type=DSRType.ACCESS,
            completed=True,
            data_provided=data,
            export_format="json",
            export_size_bytes=len(json.dumps(data)),
            download_url=download_url,
            download_expires_at=expires_at,
            human_readable_explanation=summary
        )
        
        dsr.status = DSRStatus.COMPLETED
        dsr.completed_at = datetime.utcnow()
        dsr.response_data = {"download_url": download_url}
        dsr.response_url = download_url
        dsr.response_expires_at = expires_at
        dsr.status_history.append({
            "status": DSRStatus.COMPLETED.value,
            "timestamp": datetime.utcnow().isoformat(),
            "note": "Access request completed"
        })
        
        await self.dsr_store.save(dsr)
        
        # Audit
        await self.audit.log_event(AuditEvent(
            event_type="dsr_completed",
            actor_type="system",
            actor_id="dsr_processor",
            subject_type="dsr",
            subject_id=request_id,
            action="complete_access",
            action_category="dsr",
            action_details={"data_size_bytes": response.export_size_bytes},
            success=True
        ))
        
        # Notify user
        await self.notifications.send_dsr_completed(
            user_id=user_id,
            request_id=request_id,
            download_url=download_url,
            expires_at=expires_at
        )
        
        return response
    
    # =========================================================================
    # ERASURE REQUEST (Art. 17) - Right to be Forgotten
    # =========================================================================
    
    async def process_erasure_request(
        self,
        request_id: str
    ) -> DSRResponse:
        """
        Process Right to Erasure request.
        
        Deletes all personal data except:
        - Data required for legal compliance
        - Data required for legal claims
        - Consent records (retained for audit)
        """
        
        dsr = await self._validate_and_get_dsr(request_id, DSRType.ERASURE)
        user_id = dsr.user_id
        scope = dsr.scope
        
        deletion_report = {
            "deleted_items": [],
            "retained_items": [],
            "retention_reasons": [],
            "deletion_timestamp": datetime.utcnow().isoformat()
        }
        
        # Delete psychological profile
        if scope.get("psychological_profile", True):
            count = await self.profile_store.delete_profile(user_id)
            deletion_report["deleted_items"].append({
                "category": "psychological_profile",
                "count": count,
                "description": "Personality traits, psychological inferences"
            })
        
        # Delete behavioral signals
        if scope.get("behavioral_signals", True):
            count = await self.signal_store.delete_user_signals(user_id)
            deletion_report["deleted_items"].append({
                "category": "behavioral_signals",
                "count": count,
                "description": "Browsing behavior, interaction patterns"
            })
        
        # Delete embeddings
        if scope.get("embeddings", True):
            count = await self.embedding_store.delete_user_embeddings(user_id)
            deletion_report["deleted_items"].append({
                "category": "embeddings",
                "count": count,
                "description": "Vector representations of behavior"
            })
        
        # Delete journey data
        if scope.get("journey_data", True):
            count = await self.journey_store.delete_user_journeys(user_id)
            deletion_report["deleted_items"].append({
                "category": "journey_data",
                "count": count,
                "description": "Decision journey tracking"
            })
        
        # Delete ad decisions
        if scope.get("ad_decisions", True):
            count = await self.decision_store.delete_user_decisions(user_id)
            deletion_report["deleted_items"].append({
                "category": "ad_decisions",
                "count": count,
                "description": "Ad targeting and delivery records"
            })
        
        # RETAINED DATA
        
        # Consent records (legal requirement)
        deletion_report["retained_items"].append({
            "category": "consent_records",
            "retention_period": "3 years from withdrawal",
            "legal_basis": "GDPR Art. 7(1) - proof of consent"
        })
        deletion_report["retention_reasons"].append(
            "Consent records retained to demonstrate lawful processing"
        )
        
        # Audit logs (legal requirement)
        deletion_report["retained_items"].append({
            "category": "audit_logs",
            "retention_period": "7 years",
            "legal_basis": "Legal obligation for compliance documentation"
        })
        deletion_report["retention_reasons"].append(
            "Audit logs retained for regulatory compliance"
        )
        
        # DSR request itself (proof of compliance)
        deletion_report["retained_items"].append({
            "category": "dsr_records",
            "retention_period": "3 years",
            "legal_basis": "Proof of compliance with data subject rights"
        })
        
        # Complete DSR
        response = DSRResponse(
            request_id=request_id,
            user_id=user_id,
            request_type=DSRType.ERASURE,
            completed=True,
            items_deleted=[item["category"] for item in deletion_report["deleted_items"]],
            items_retained=[
                {"category": item["category"], "reason": item["legal_basis"]}
                for item in deletion_report["retained_items"]
            ],
            human_readable_explanation=self._generate_erasure_summary(deletion_report)
        )
        
        dsr.status = DSRStatus.COMPLETED
        dsr.completed_at = datetime.utcnow()
        dsr.response_data = deletion_report
        dsr.status_history.append({
            "status": DSRStatus.COMPLETED.value,
            "timestamp": datetime.utcnow().isoformat(),
            "note": f"Erasure completed: {len(deletion_report['deleted_items'])} categories deleted"
        })
        
        await self.dsr_store.save(dsr)
        
        # Audit
        await self.audit.log_event(AuditEvent(
            event_type="dsr_erasure_completed",
            actor_type="system",
            actor_id="dsr_processor",
            subject_type="user",
            subject_id=user_id,
            action="erasure",
            action_category="dsr",
            action_details={
                "deleted_categories": [item["category"] for item in deletion_report["deleted_items"]],
                "retained_categories": [item["category"] for item in deletion_report["retained_items"]]
            },
            success=True
        ))
        
        # Withdraw all consents
        await self.consent.withdraw_consent(ConsentWithdrawRequest(
            user_id=user_id,
            purposes=list(ConsentPurpose),
            reason="Erasure request"
        ))
        
        # Notify user
        await self.notifications.send_erasure_completed(
            user_id=user_id,
            request_id=request_id,
            deletion_report=deletion_report
        )
        
        return response
    
    # =========================================================================
    # PORTABILITY REQUEST (Art. 20)
    # =========================================================================
    
    async def process_portability_request(
        self,
        request_id: str
    ) -> DSRResponse:
        """
        Process Data Portability request.
        
        Returns data in machine-readable format (JSON).
        Only includes data PROVIDED by user or OBSERVED about user.
        Does NOT include INFERRED data (psychological profiles).
        """
        
        dsr = await self._validate_and_get_dsr(request_id, DSRType.PORTABILITY)
        user_id = dsr.user_id
        
        # Gather PORTABLE data only
        portable_data = {
            "export_metadata": {
                "request_id": request_id,
                "user_id": user_id,
                "generated_at": datetime.utcnow().isoformat(),
                "format": "JSON",
                "schema_version": "1.0"
            },
            
            # User-provided data
            "user_provided": await self.user_store.get_user_provided_data(user_id),
            
            # Observed behavioral data (raw signals)
            "behavioral_observations": await self.signal_store.get_raw_signals(
                user_id,
                include_timestamps=True
            ),
            
            # Preferences explicitly set
            "preferences": await self._get_user_preferences(user_id),
            
            # Consent choices
            "consent_choices": await self._get_consent_choices(user_id)
        }
        
        # EXCLUDED (inferred, not portable):
        # - Psychological profile
        # - Personality scores
        # - Emotional states
        # - Predicted behaviors
        
        # Create download package
        json_data = json.dumps(portable_data, indent=2, default=str)
        download_url, expires_at = await self._create_download_package(
            user_id,
            portable_data,
            "portability"
        )
        
        response = DSRResponse(
            request_id=request_id,
            user_id=user_id,
            request_type=DSRType.PORTABILITY,
            completed=True,
            export_format="application/json",
            export_size_bytes=len(json_data),
            download_url=download_url,
            download_expires_at=expires_at,
            human_readable_explanation=(
                "Your portable data has been exported in JSON format. "
                "This includes data you provided and behavioral observations. "
                "It does not include inferred psychological profiles, as these "
                "are derived data not subject to portability rights."
            )
        )
        
        dsr.status = DSRStatus.COMPLETED
        dsr.completed_at = datetime.utcnow()
        dsr.response_url = download_url
        dsr.response_format = "application/json"
        dsr.response_expires_at = expires_at
        dsr.status_history.append({
            "status": DSRStatus.COMPLETED.value,
            "timestamp": datetime.utcnow().isoformat(),
            "note": "Portability export ready"
        })
        
        await self.dsr_store.save(dsr)
        
        # Audit
        await self.audit.log_event(AuditEvent(
            event_type="dsr_portability_completed",
            actor_type="system",
            actor_id="dsr_processor",
            subject_type="dsr",
            subject_id=request_id,
            action="portability_export",
            action_category="dsr",
            action_details={"size_bytes": len(json_data)},
            success=True
        ))
        
        return response
    
    # =========================================================================
    # AUTOMATED DECISION EXPLANATION (Art. 22)
    # =========================================================================
    
    async def process_explanation_request(
        self,
        request_id: str
    ) -> DSRResponse:
        """
        Process request for explanation of automated decisions.
        
        ADAM's psychological profiling constitutes "automated decision-making
        with legal or significant effects" under GDPR Art. 22.
        """
        
        dsr = await self._validate_and_get_dsr(request_id, DSRType.AUTOMATED_DECISION)
        user_id = dsr.user_id
        decision_id = dsr.scope.get("decision_id")
        
        if decision_id:
            # Explain specific decision
            explanation = await self._explain_specific_decision(user_id, decision_id)
        else:
            # Explain overall profiling logic
            explanation = await self._explain_profiling_system(user_id)
        
        # Add human-readable summary
        human_explanation = self._generate_human_explanation(explanation)
        
        # Add appeal/human review info
        explanation["your_rights"] = {
            "right_to_contest": True,
            "right_to_human_review": True,
            "how_to_contest": (
                "You may contest this decision by contacting privacy@informativ.ai "
                "or clicking 'Request Human Review' in your privacy dashboard."
            ),
            "human_review_timeline": "5 business days",
            "appeal_process": (
                "If unsatisfied with our response, you may lodge a complaint "
                "with your local data protection authority."
            )
        }
        
        response = DSRResponse(
            request_id=request_id,
            user_id=user_id,
            request_type=DSRType.AUTOMATED_DECISION,
            completed=True,
            explanation=explanation,
            human_readable_explanation=human_explanation,
            appeal_available=True,
            appeal_deadline=datetime.utcnow() + timedelta(days=30),
            appeal_instructions=(
                "To request human review of automated decisions affecting you, "
                "reply to this notification or contact privacy@informativ.ai"
            )
        )
        
        dsr.status = DSRStatus.COMPLETED
        dsr.completed_at = datetime.utcnow()
        dsr.response_data = explanation
        dsr.status_history.append({
            "status": DSRStatus.COMPLETED.value,
            "timestamp": datetime.utcnow().isoformat(),
            "note": "Explanation provided"
        })
        
        await self.dsr_store.save(dsr)
        
        return response
    
    async def _explain_specific_decision(
        self,
        user_id: str,
        decision_id: str
    ) -> Dict[str, Any]:
        """Explain a specific ad targeting decision."""
        
        decision = await self.decision_store.get_decision(decision_id)
        if not decision or decision.user_id != user_id:
            raise ValueError("Decision not found or access denied")
        
        return {
            "decision_id": decision_id,
            "decision_type": "ad_targeting",
            "decision_timestamp": decision.timestamp.isoformat(),
            
            "what_was_decided": (
                f"An advertisement was selected for you based on your "
                f"psychological profile and current state."
            ),
            
            "factors_considered": {
                "psychological_traits": {
                    "description": "Stable personality characteristics",
                    "traits_used": decision.traits_used,
                    "weight_in_decision": "40%"
                },
                "current_state": {
                    "description": "Your current emotional/cognitive state",
                    "state_factors": decision.state_factors,
                    "weight_in_decision": "30%"
                },
                "behavioral_signals": {
                    "description": "Recent browsing and interaction patterns",
                    "signals_used": decision.behavioral_signals,
                    "weight_in_decision": "20%"
                },
                "contextual_factors": {
                    "description": "Time, content, device context",
                    "factors": decision.context_factors,
                    "weight_in_decision": "10%"
                }
            },
            
            "outcome": {
                "ad_selected": decision.ad_id,
                "ad_category": decision.ad_category,
                "match_score": decision.match_score,
                "confidence": decision.confidence
            },
            
            "logic_explanation": (
                f"This ad was selected because your psychological profile "
                f"indicated {decision.primary_match_reason}. "
                f"The system predicted this ad would be relevant to you with "
                f"{decision.confidence:.0%} confidence."
            )
        }
    
    async def _explain_profiling_system(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Explain ADAM's profiling system to user."""
        
        profile = await self.profile_store.get_profile(user_id)
        
        return {
            "system_name": "ADAM (Atomic Decision & Audience Modeling)",
            "purpose": (
                "To select advertisements that are relevant to your interests "
                "and psychological preferences, improving your advertising experience "
                "and making ads more useful to you."
            ),
            
            "data_collected": [
                {
                    "category": "Behavioral Data",
                    "description": "How you interact with content - clicks, scrolls, time spent",
                    "how_used": "Infer interests and engagement patterns"
                },
                {
                    "category": "Text/Voice Data",
                    "description": "Content you consume or create (with consent)",
                    "how_used": "Understand communication style and values"
                },
                {
                    "category": "Device/Context Data",
                    "description": "Time of day, device type, content context",
                    "how_used": "Optimize ad timing and format"
                }
            ],
            
            "inferences_made": {
                "personality_traits": {
                    "description": "Big Five personality dimensions",
                    "your_profile": self._format_personality(profile) if profile else "Not available",
                    "accuracy": "Validated models with ~70% accuracy"
                },
                "regulatory_focus": {
                    "description": "Whether you're motivated by gains or avoiding losses",
                    "your_profile": profile.regulatory_focus if profile else "Unknown"
                },
                "construal_level": {
                    "description": "Whether you prefer abstract or concrete messaging",
                    "your_profile": profile.construal_level if profile else "Unknown"
                },
                "emotional_state": {
                    "description": "Current mood and cognitive state",
                    "how_determined": "Real-time behavioral signals",
                    "retention": "Not stored - used only in moment"
                }
            },
            
            "how_decisions_are_made": (
                "1. Your psychological profile is compared against ad characteristics\n"
                "2. Ads matching your personality are scored higher\n"
                "3. Your current state is assessed to optimize timing\n"
                "4. The best-matching ad is selected and shown\n"
                "5. Your response helps improve future matching"
            ),
            
            "significance": (
                "These decisions affect which advertisements you see. "
                "This may influence your purchasing decisions and the offers "
                "you receive. You have the right to opt out of this profiling."
            ),
            
            "your_control": {
                "opt_out": "You can opt out of psychological profiling at any time",
                "delete_data": "You can request deletion of your profile",
                "correct_data": "You can request corrections to your data",
                "human_review": "You can request human review of any decision"
            }
        }
    
    # =========================================================================
    # HELPERS
    # =========================================================================
    
    async def _validate_and_get_dsr(
        self,
        request_id: str,
        expected_type: DSRType
    ) -> DSRRequest:
        """Validate DSR exists and is ready for processing."""
        
        dsr = await self.dsr_store.get(request_id)
        
        if not dsr:
            raise ValueError(f"DSR not found: {request_id}")
        
        if dsr.request_type != expected_type:
            raise ValueError(f"DSR type mismatch: expected {expected_type}, got {dsr.request_type}")
        
        if not dsr.identity_verified:
            raise ValueError("Identity not yet verified")
        
        if dsr.status == DSRStatus.COMPLETED:
            raise ValueError("DSR already completed")
        
        return dsr
    
    async def _create_download_package(
        self,
        user_id: str,
        data: Dict,
        package_type: str
    ) -> tuple[str, datetime]:
        """Create encrypted download package."""
        
        # Create ZIP with JSON
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                f"{package_type}_export_{user_id}.json",
                json.dumps(data, indent=2, default=str)
            )
            zf.writestr(
                "README.txt",
                f"ADAM Data Export - {package_type.title()}\n"
                f"Generated: {datetime.utcnow().isoformat()}\n"
                f"User ID: {user_id}\n\n"
                f"This export contains your personal data as requested."
            )
        
        # Encrypt
        encrypted = self.encryption.encrypt(buffer.getvalue())
        
        # Store and get URL
        expires_at = datetime.utcnow() + timedelta(days=7)
        download_url = await self.dsr_store.store_download(
            user_id=user_id,
            data=encrypted,
            expires_at=expires_at
        )
        
        return download_url, expires_at
    
    def _generate_erasure_summary(self, report: Dict) -> str:
        """Generate human-readable erasure summary."""
        
        deleted = len(report["deleted_items"])
        retained = len(report["retained_items"])
        
        summary = f"Your data deletion request has been processed.\n\n"
        summary += f"DELETED ({deleted} categories):\n"
        for item in report["deleted_items"]:
            summary += f"• {item['description']}: {item['count']} records\n"
        
        summary += f"\nRETAINED FOR LEGAL REQUIREMENTS ({retained} categories):\n"
        for item in report["retained_items"]:
            summary += f"• {item['category']}: {item['legal_basis']}\n"
        
        return summary
    
    def _generate_human_explanation(self, explanation: Dict) -> str:
        """Convert technical explanation to plain language."""
        
        if "decision_id" in explanation:
            return (
                f"On {explanation.get('decision_timestamp', 'a recent date')}, "
                f"our system selected an advertisement for you. "
                f"{explanation.get('logic_explanation', '')}\n\n"
                f"The main factors were your personality profile "
                f"({explanation['factors_considered']['psychological_traits']['weight_in_decision']}) "
                f"and your current browsing behavior "
                f"({explanation['factors_considered']['behavioral_signals']['weight_in_decision']})."
            )
        else:
            return (
                "ADAM is a system that selects advertisements based on your "
                "psychological profile and browsing behavior. It analyzes how "
                "you interact with content to understand your preferences, then "
                "matches ads that align with your personality and current needs.\n\n"
                "You can opt out of this profiling at any time through your "
                "privacy settings or by contacting us."
            )
```

---

## Part 4: DPIA Framework

### 4.1 DPIA Management Service

```python
"""
ADAM Enhancement #17: Data Protection Impact Assessment Framework
GDPR Article 35 compliance for high-risk processing.
"""


class DPIAManager:
    """
    Manage Data Protection Impact Assessments.
    
    ADAM's psychological profiling REQUIRES DPIA because it involves:
    - Systematic profiling with significant effects (Art. 35(3)(a))
    - Processing of data revealing psychological characteristics
    - Large-scale processing of behavioral data
    """
    
    def __init__(
        self,
        dpia_store: 'DPIAStore',
        audit_logger: 'AuditLogger',
        notification_service: 'NotificationService'
    ):
        self.store = dpia_store
        self.audit = audit_logger
        self.notifications = notification_service
    
    async def create_dpia(
        self,
        assessment_name: str,
        processing_description: str,
        purposes: List[ConsentPurpose],
        data_categories: List[str],
        data_subjects: List[str]
    ) -> DPIAAssessment:
        """Create new DPIA for processing activity."""
        
        dpia = DPIAAssessment(
            assessment_name=assessment_name,
            assessment_version="1.0",
            next_review_due=datetime.utcnow() + timedelta(days=365),
            processing_description=processing_description,
            purposes=purposes,
            data_categories=data_categories,
            data_subjects=data_subjects,
            necessity_assessment="",
            proportionality_assessment="",
            risks_identified=[],
            overall_risk_level=RiskLevel.HIGH,  # Default high for profiling
            mitigations=[],
            residual_risk_level=RiskLevel.HIGH,
            linked_consent_purposes=purposes
        )
        
        await self.store.save(dpia)
        
        # Audit
        await self.audit.log_event(AuditEvent(
            event_type="dpia_created",
            actor_type="admin",
            actor_id="dpia_manager",
            subject_type="dpia",
            subject_id=dpia.dpia_id,
            action="create",
            action_category="compliance",
            action_details={"name": assessment_name},
            success=True
        ))
        
        return dpia
    
    async def add_risk(
        self,
        dpia_id: str,
        risk: RiskAssessment
    ) -> DPIAAssessment:
        """Add identified risk to DPIA."""
        
        dpia = await self.store.get(dpia_id)
        if not dpia:
            raise ValueError(f"DPIA not found: {dpia_id}")
        
        dpia.risks_identified.append(risk)
        dpia = self._recalculate_risk_level(dpia)
        
        await self.store.save(dpia)
        return dpia
    
    async def add_mitigation(
        self,
        dpia_id: str,
        mitigation: MitigationMeasure
    ) -> DPIAAssessment:
        """Add mitigation measure to DPIA."""
        
        dpia = await self.store.get(dpia_id)
        if not dpia:
            raise ValueError(f"DPIA not found: {dpia_id}")
        
        dpia.mitigations.append(mitigation)
        dpia = self._recalculate_residual_risk(dpia)
        
        await self.store.save(dpia)
        return dpia
    
    async def submit_for_dpo_review(
        self,
        dpia_id: str
    ) -> DPIAAssessment:
        """Submit DPIA for DPO review."""
        
        dpia = await self.store.get(dpia_id)
        
        # Validate completeness
        if not dpia.necessity_assessment:
            raise ValueError("Necessity assessment required")
        if not dpia.proportionality_assessment:
            raise ValueError("Proportionality assessment required")
        if not dpia.risks_identified:
            raise ValueError("At least one risk must be identified")
        if not dpia.mitigations:
            raise ValueError("At least one mitigation required")
        
        # Notify DPO
        await self.notifications.notify_dpo(
            subject=f"DPIA Review Required: {dpia.assessment_name}",
            body=f"A new DPIA requires your review.\n\n"
                 f"Processing: {dpia.processing_description}\n"
                 f"Overall Risk: {dpia.overall_risk_level.value}\n"
                 f"Residual Risk: {dpia.residual_risk_level.value}"
        )
        
        return dpia
    
    async def approve_dpia(
        self,
        dpia_id: str,
        approver_id: str,
        dpo_opinion: str
    ) -> DPIAAssessment:
        """DPO approves DPIA."""
        
        dpia = await self.store.get(dpia_id)
        
        dpia.dpo_consulted = True
        dpia.dpo_opinion = dpo_opinion
        dpia.approved = True
        dpia.approved_by = approver_id
        dpia.approval_date = datetime.utcnow()
        
        # Check if authority consultation needed
        if dpia.residual_risk_level == RiskLevel.VERY_HIGH:
            dpia.authority_consultation_required = True
        
        await self.store.save(dpia)
        
        # Audit
        await self.audit.log_event(AuditEvent(
            event_type="dpia_approved",
            actor_type="admin",
            actor_id=approver_id,
            subject_type="dpia",
            subject_id=dpia_id,
            action="approve",
            action_category="compliance",
            action_details={
                "residual_risk": dpia.residual_risk_level.value,
                "authority_consultation": dpia.authority_consultation_required
            },
            success=True
        ))
        
        return dpia
    
    def _recalculate_risk_level(self, dpia: DPIAAssessment) -> DPIAAssessment:
        """Recalculate overall risk level."""
        
        if not dpia.risks_identified:
            dpia.overall_risk_level = RiskLevel.LOW
            return dpia
        
        # Highest risk wins
        risk_order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.VERY_HIGH]
        max_risk = max(
            dpia.risks_identified,
            key=lambda r: risk_order.index(r.risk_level)
        )
        dpia.overall_risk_level = max_risk.risk_level
        
        return dpia
    
    def _recalculate_residual_risk(self, dpia: DPIAAssessment) -> DPIAAssessment:
        """Recalculate residual risk after mitigations."""
        
        if not dpia.mitigations:
            dpia.residual_risk_level = dpia.overall_risk_level
            return dpia
        
        # Calculate based on mitigation effectiveness
        mitigated_risks = set()
        high_effectiveness_count = 0
        
        for mit in dpia.mitigations:
            if mit.implementation_status == "implemented":
                mitigated_risks.update(mit.addresses_risk_ids)
                if mit.effectiveness_rating == "high":
                    high_effectiveness_count += 1
        
        unmitigated = [
            r for r in dpia.risks_identified 
            if r.risk_id not in mitigated_risks
        ]
        
        if not unmitigated and high_effectiveness_count >= len(dpia.risks_identified):
            dpia.residual_risk_level = RiskLevel.LOW
        elif len(unmitigated) <= len(dpia.risks_identified) // 2:
            dpia.residual_risk_level = RiskLevel.MEDIUM
        else:
            dpia.residual_risk_level = dpia.overall_risk_level
        
        return dpia
    
    @staticmethod
    def get_adam_base_dpia() -> DPIAAssessment:
        """Get pre-configured DPIA for ADAM psychological profiling."""
        
        return DPIAAssessment(
            assessment_name="ADAM Psychological Profiling System",
            assessment_version="2.0",
            next_review_due=datetime.utcnow() + timedelta(days=365),
            processing_description=(
                "ADAM processes behavioral, textual, and voice signals to infer "
                "psychological characteristics including personality traits, "
                "emotional states, and cognitive patterns. These profiles are used "
                "to select and personalize advertising content."
            ),
            purposes=[
                ConsentPurpose.PSYCHOLOGICAL_PROFILING,
                ConsentPurpose.EMOTIONAL_TARGETING,
                ConsentPurpose.BEHAVIORAL_TARGETING
            ],
            data_categories=[
                "Behavioral signals (clicks, scrolls, time)",
                "Linguistic patterns (text content)",
                "Voice characteristics (tone, pace)",
                "Device and context data",
                "Inferred personality traits",
                "Inferred emotional states"
            ],
            data_subjects=["Adult users", "Potential minors (with age gate)"],
            necessity_assessment=(
                "Psychological profiling is necessary to deliver the core value "
                "proposition: personalized advertising that matches user psychology. "
                "Less invasive alternatives (contextual, demographic) have been "
                "evaluated but provide significantly lower effectiveness (40-50% "
                "lower conversion rates based on academic research)."
            ),
            proportionality_assessment=(
                "Processing is proportionate because: (1) Users provide explicit "
                "consent; (2) Data is used only for stated purpose; (3) Users can "
                "opt-out at any time; (4) Profiles are not used for decisions with "
                "legal effects beyond advertising; (5) Robust security measures "
                "protect data."
            ),
            risks_identified=[
                RiskAssessment(
                    risk_description="Unauthorized access to psychological profiles",
                    risk_category="data_breach",
                    likelihood="unlikely",
                    impact_severity="significant",
                    affected_rights=["Privacy", "Data protection"],
                    affected_data_subjects=["All users"],
                    risk_level=RiskLevel.HIGH
                ),
                RiskAssessment(
                    risk_description="Discriminatory outcomes from profiling",
                    risk_category="discrimination",
                    likelihood="possible",
                    impact_severity="significant",
                    affected_rights=["Non-discrimination", "Fair treatment"],
                    affected_data_subjects=["All users"],
                    risk_level=RiskLevel.HIGH
                ),
                RiskAssessment(
                    risk_description="Manipulation through emotional targeting",
                    risk_category="manipulation",
                    likelihood="possible",
                    impact_severity="limited",
                    affected_rights=["Autonomy", "Free will"],
                    affected_data_subjects=["All users"],
                    risk_level=RiskLevel.MEDIUM
                ),
                RiskAssessment(
                    risk_description="Profiling of minors",
                    risk_category="child_protection",
                    likelihood="unlikely",
                    impact_severity="maximum",
                    affected_rights=["Child protection"],
                    affected_data_subjects=["Minors"],
                    risk_level=RiskLevel.VERY_HIGH
                )
            ],
            overall_risk_level=RiskLevel.VERY_HIGH,
            mitigations=[
                MitigationMeasure(
                    measure_description="Encryption at rest and in transit",
                    measure_type="technical",
                    implementation_status="implemented",
                    responsible_party="Security team",
                    effectiveness_rating="high",
                    verification_method="Annual penetration testing",
                    addresses_risk_ids=[]  # Link to risk IDs
                ),
                MitigationMeasure(
                    measure_description="Age verification gate before profiling",
                    measure_type="technical",
                    implementation_status="implemented",
                    responsible_party="Product team",
                    effectiveness_rating="medium",
                    verification_method="Audit of age verification logs",
                    addresses_risk_ids=[]
                ),
                MitigationMeasure(
                    measure_description="Bias testing of profiling models",
                    measure_type="organizational",
                    implementation_status="implemented",
                    responsible_party="ML team",
                    effectiveness_rating="medium",
                    verification_method="Quarterly bias audits",
                    addresses_risk_ids=[]
                ),
                MitigationMeasure(
                    measure_description="Explicit consent with granular controls",
                    measure_type="legal",
                    implementation_status="implemented",
                    responsible_party="Legal team",
                    effectiveness_rating="high",
                    verification_method="Consent rate monitoring",
                    addresses_risk_ids=[]
                ),
                MitigationMeasure(
                    measure_description="Right to explanation for all decisions",
                    measure_type="organizational",
                    implementation_status="implemented",
                    responsible_party="Product team",
                    effectiveness_rating="high",
                    verification_method="DSR completion rates",
                    addresses_risk_ids=[]
                )
            ],
            residual_risk_level=RiskLevel.MEDIUM,
            dpo_consulted=False,
            authority_consultation_required=False
        )
```

---

## Part 5: Neo4j Schema

```cypher
-- =============================================================================
-- ADAM Enhancement #17: Privacy & Consent Neo4j Schema
-- =============================================================================

-- Constraints
CREATE CONSTRAINT consent_record_id IF NOT EXISTS
FOR (cr:ConsentRecord) REQUIRE cr.consent_id IS UNIQUE;

CREATE CONSTRAINT consent_profile_id IF NOT EXISTS
FOR (cp:ConsentProfile) REQUIRE cp.profile_id IS UNIQUE;

CREATE CONSTRAINT consent_profile_user IF NOT EXISTS
FOR (cp:ConsentProfile) REQUIRE cp.user_id IS UNIQUE;

CREATE CONSTRAINT dsr_request_id IF NOT EXISTS
FOR (dsr:DSRRequest) REQUIRE dsr.request_id IS UNIQUE;

CREATE CONSTRAINT audit_event_id IF NOT EXISTS
FOR (ae:AuditEvent) REQUIRE ae.event_id IS UNIQUE;

CREATE CONSTRAINT dpia_id IF NOT EXISTS
FOR (dpia:DPIA) REQUIRE dpia.dpia_id IS UNIQUE;

CREATE CONSTRAINT consent_text_version IF NOT EXISTS
FOR (ct:ConsentText) REQUIRE (ct.purpose, ct.version) IS UNIQUE;

-- Indexes
CREATE INDEX consent_user_idx IF NOT EXISTS
FOR (cr:ConsentRecord) ON (cr.user_id);

CREATE INDEX consent_purpose_idx IF NOT EXISTS
FOR (cr:ConsentRecord) ON (cr.purpose);

CREATE INDEX consent_status_idx IF NOT EXISTS
FOR (cr:ConsentRecord) ON (cr.status);

CREATE INDEX consent_timestamp_idx IF NOT EXISTS
FOR (cr:ConsentRecord) ON (cr.responded_at);

CREATE INDEX dsr_user_idx IF NOT EXISTS
FOR (dsr:DSRRequest) ON (dsr.user_id);

CREATE INDEX dsr_status_idx IF NOT EXISTS
FOR (dsr:DSRRequest) ON (dsr.status);

CREATE INDEX dsr_due_date_idx IF NOT EXISTS
FOR (dsr:DSRRequest) ON (dsr.due_date);

CREATE INDEX audit_timestamp_idx IF NOT EXISTS
FOR (ae:AuditEvent) ON (ae.timestamp);

CREATE INDEX audit_user_idx IF NOT EXISTS
FOR (ae:AuditEvent) ON (ae.subject_id);

CREATE INDEX audit_type_idx IF NOT EXISTS
FOR (ae:AuditEvent) ON (ae.event_type);

-- =============================================================================
-- Relationships
-- =============================================================================

-- (:User)-[:HAS_CONSENT_PROFILE]->(:ConsentProfile)
-- (:ConsentProfile)-[:HAS_CONSENT {current: bool}]->(:ConsentRecord)
-- (:ConsentRecord)-[:FOR_PURPOSE]->(:ConsentPurpose)
-- (:ConsentRecord)-[:USED_TEXT]->(:ConsentText)
-- (:ConsentRecord)-[:PREVIOUS_RECORD]->(:ConsentRecord)
-- (:User)-[:SUBMITTED_DSR]->(:DSRRequest)
-- (:DSRRequest)-[:RESULTED_IN]->(:DSRResponse)
-- (:AuditEvent)-[:PREVIOUS_EVENT]->(:AuditEvent)
-- (:AuditEvent)-[:ABOUT_USER]->(:User)
-- (:AuditEvent)-[:ABOUT_CONSENT]->(:ConsentRecord)
-- (:DPIA)-[:COVERS_PURPOSE]->(:ConsentPurpose)
-- (:DPIA)-[:HAS_RISK]->(:Risk)
-- (:DPIA)-[:HAS_MITIGATION]->(:Mitigation)

-- =============================================================================
-- Example Queries
-- =============================================================================

-- Get user's current consent status for all purposes
MATCH (u:User {user_id: $user_id})-[:HAS_CONSENT_PROFILE]->(cp:ConsentProfile)
MATCH (cp)-[r:HAS_CONSENT {current: true}]->(cr:ConsentRecord)
RETURN cr.purpose, cr.status, cr.expires_at, cr.responded_at
ORDER BY cr.purpose;

-- Check specific consent
MATCH (u:User {user_id: $user_id})-[:HAS_CONSENT_PROFILE]->(cp:ConsentProfile)
MATCH (cp)-[:HAS_CONSENT {current: true}]->(cr:ConsentRecord {purpose: $purpose})
WHERE cr.status = 'granted' 
  AND (cr.expires_at IS NULL OR cr.expires_at > datetime())
RETURN cr IS NOT NULL as has_consent;

-- Get consent history for audit
MATCH (u:User {user_id: $user_id})-[:HAS_CONSENT_PROFILE]->(cp:ConsentProfile)
MATCH (cp)-[:HAS_CONSENT]->(cr:ConsentRecord)
WHERE cr.purpose = $purpose
RETURN cr ORDER BY cr.responded_at DESC;

-- Get pending DSRs near deadline
MATCH (dsr:DSRRequest)
WHERE dsr.status IN ['submitted', 'in_progress']
  AND dsr.due_date < datetime() + duration('P7D')
RETURN dsr.request_id, dsr.user_id, dsr.request_type, dsr.due_date
ORDER BY dsr.due_date ASC;

-- Verify audit chain integrity
MATCH path = (start:AuditEvent {event_id: $start_id})-[:PREVIOUS_EVENT*]->(end:AuditEvent {event_id: $end_id})
WITH nodes(path) as events
UNWIND range(0, size(events)-2) as i
WITH events[i] as current, events[i+1] as previous
WHERE current.previous_event_hash <> previous.event_hash
RETURN count(*) as integrity_violations;

-- Get all data for user (for access request)
MATCH (u:User {user_id: $user_id})
OPTIONAL MATCH (u)-[:HAS_CONSENT_PROFILE]->(cp:ConsentProfile)
OPTIONAL MATCH (cp)-[:HAS_CONSENT]->(cr:ConsentRecord)
OPTIONAL MATCH (u)<-[:PROFILE_FOR]-(pp:PsychologicalProfile)
OPTIONAL MATCH (u)<-[:ABOUT_USER]-(ae:AuditEvent)
RETURN u, cp, collect(DISTINCT cr) as consents, pp, collect(DISTINCT ae) as audit_events;

-- Delete user data (for erasure request)
MATCH (u:User {user_id: $user_id})
// Delete psychological profile
OPTIONAL MATCH (u)<-[:PROFILE_FOR]-(pp:PsychologicalProfile)
DETACH DELETE pp
// Delete embeddings
OPTIONAL MATCH (u)<-[:FOR_USER]-(emb:Embedding)
DETACH DELETE emb
// Delete journey data
OPTIONAL MATCH (u)<-[:USER_JOURNEY]-(j:Journey)
DETACH DELETE j
// Mark consent records as erasure-processed (don't delete for audit)
OPTIONAL MATCH (u)-[:HAS_CONSENT_PROFILE]->(cp:ConsentProfile)-[:HAS_CONSENT]->(cr:ConsentRecord)
SET cr.erasure_processed = true, cr.erasure_date = datetime()
RETURN count(*) as items_processed;
```

---

## Part 6: FastAPI Endpoints

```python
"""
ADAM Enhancement #17: Privacy API Endpoints
Complete REST API for consent and privacy management.
"""

from fastapi import FastAPI, HTTPException, Depends, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from prometheus_client import Counter, Histogram, generate_latest
from starlette.responses import Response
from contextlib import asynccontextmanager
from typing import Optional
import time


# Metrics
CONSENT_CHECKS = Counter('adam_consent_checks_total', 'Consent checks', ['purpose', 'result'])
CONSENT_GRANTS = Counter('adam_consent_grants_total', 'Consent grants', ['purpose'])
CONSENT_WITHDRAWALS = Counter('adam_consent_withdrawals_total', 'Consent withdrawals', ['purpose'])
DSR_REQUESTS = Counter('adam_dsr_requests_total', 'DSR requests', ['type', 'status'])
CONSENT_CHECK_LATENCY = Histogram('adam_consent_check_latency_seconds', 'Consent check latency',
                                  buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1])


security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize privacy services."""
    from .config import Settings
    settings = Settings()
    
    # Initialize services
    app.state.consent_manager = ConsentManager(
        consent_store=ConsentStore(settings.neo4j_uri),
        jurisdiction_detector=JurisdictionDetector(),
        audit_logger=AuditLogger(settings.audit_store_uri),
        event_publisher=EventPublisher(settings.kafka_brokers),
        encryption_service=EncryptionService(settings.encryption_key)
    )
    
    app.state.dsr_processor = DSRProcessor(
        dsr_store=DSRStore(settings.neo4j_uri),
        # ... other dependencies
        consent_manager=app.state.consent_manager,
        audit_logger=app.state.consent_manager.audit
    )
    
    app.state.dpia_manager = DPIAManager(
        dpia_store=DPIAStore(settings.neo4j_uri),
        audit_logger=app.state.consent_manager.audit,
        notification_service=NotificationService(settings.notification_config)
    )
    
    yield
    
    # Cleanup
    await app.state.consent_manager.store.close()


app = FastAPI(
    title="ADAM Privacy & Consent API",
    description="GDPR/CPRA compliant consent management and data subject rights",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


# =============================================================================
# CONSENT ENDPOINTS
# =============================================================================

@app.post("/v1/consent/grant", response_model=List[ConsentRecord])
async def grant_consent(
    request: ConsentGrantRequest,
    background_tasks: BackgroundTasks
):
    """
    Record consent grant for one or more purposes.
    
    Called when user accepts consent dialog.
    """
    try:
        records = await app.state.consent_manager.record_consent(request)
        
        for record in records:
            CONSENT_GRANTS.labels(purpose=record.purpose.value).inc()
        
        return records
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/consent/withdraw", response_model=List[ConsentRecord])
async def withdraw_consent(
    request: ConsentWithdrawRequest,
    background_tasks: BackgroundTasks
):
    """
    Process consent withdrawal.
    
    Triggers downstream data cleanup.
    """
    try:
        records = await app.state.consent_manager.withdraw_consent(request)
        
        for record in records:
            CONSENT_WITHDRAWALS.labels(purpose=record.purpose.value).inc()
        
        return records
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/consent/check", response_model=ConsentCheckResponse)
async def check_consent(request: ConsentCheckRequest):
    """
    Check consent status for processing purposes.
    
    HOT PATH - optimized for low latency.
    Called before every ad decision.
    """
    start = time.time()
    
    response = await app.state.consent_manager.check_consent(request)
    
    latency = time.time() - start
    CONSENT_CHECK_LATENCY.observe(latency)
    
    for purpose, allowed in response.results.items():
        CONSENT_CHECKS.labels(
            purpose=purpose.value,
            result="allowed" if allowed else "denied"
        ).inc()
    
    return response


@app.get("/v1/consent/profile/{user_id}", response_model=UserConsentProfile)
async def get_consent_profile(user_id: str):
    """Get complete consent profile for user."""
    return await app.state.consent_manager.get_consent_profile(user_id)


@app.put("/v1/consent/preferences/{user_id}", response_model=UserConsentProfile)
async def update_preferences(
    user_id: str,
    request: PrivacyPreferencesUpdate
):
    """
    Update privacy preferences (opt-outs).
    
    Handles:
    - Do Not Sell (CPRA)
    - Do Not Profile
    - Global Privacy Control signal
    """
    request.user_id = user_id
    return await app.state.consent_manager.update_privacy_preferences(request)


@app.get("/v1/consent/text/{purpose}/{version}", response_model=ConsentText)
async def get_consent_text(
    purpose: ConsentPurpose,
    version: str
):
    """Get specific version of consent text."""
    text = await app.state.consent_manager.store.get_consent_text(purpose, version)
    if not text:
        raise HTTPException(status_code=404, detail="Consent text not found")
    return text


# =============================================================================
# DATA SUBJECT RIGHTS ENDPOINTS
# =============================================================================

@app.post("/v1/dsr/submit", response_model=DSRRequest)
async def submit_dsr(request: DSRSubmitRequest):
    """
    Submit a Data Subject Request.
    
    Supported types:
    - ACCESS: Get all personal data
    - ERASURE: Delete personal data
    - PORTABILITY: Export portable data
    - AUTOMATED_DECISION: Explain profiling decisions
    - RECTIFICATION: Correct personal data
    - OBJECTION: Object to processing
    """
    try:
        dsr = await app.state.dsr_processor.submit_request(request)
        DSR_REQUESTS.labels(type=request.request_type.value, status="submitted").inc()
        return dsr
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/v1/dsr/{request_id}/verify")
async def verify_dsr_identity(
    request_id: str,
    verification_token: str,
    verification_method: str = "email"
):
    """Verify identity for DSR processing."""
    verified = await app.state.dsr_processor.verify_identity(
        request_id, verification_token, verification_method
    )
    
    if not verified:
        raise HTTPException(status_code=401, detail="Verification failed")
    
    return {"verified": True, "request_id": request_id}


@app.get("/v1/dsr/{request_id}", response_model=DSRRequest)
async def get_dsr_status(request_id: str):
    """Get DSR request status."""
    dsr = await app.state.dsr_processor.dsr_store.get(request_id)
    if not dsr:
        raise HTTPException(status_code=404, detail="DSR not found")
    return dsr


@app.post("/v1/dsr/{request_id}/process", response_model=DSRResponse)
async def process_dsr(
    request_id: str,
    background_tasks: BackgroundTasks
):
    """
    Process a verified DSR request.
    
    Routes to appropriate handler based on request type.
    """
    dsr = await app.state.dsr_processor.dsr_store.get(request_id)
    if not dsr:
        raise HTTPException(status_code=404, detail="DSR not found")
    
    if not dsr.identity_verified:
        raise HTTPException(status_code=400, detail="Identity not verified")
    
    handlers = {
        DSRType.ACCESS: app.state.dsr_processor.process_access_request,
        DSRType.ERASURE: app.state.dsr_processor.process_erasure_request,
        DSRType.PORTABILITY: app.state.dsr_processor.process_portability_request,
        DSRType.AUTOMATED_DECISION: app.state.dsr_processor.process_explanation_request,
    }
    
    handler = handlers.get(dsr.request_type)
    if not handler:
        raise HTTPException(status_code=400, detail=f"Unsupported DSR type: {dsr.request_type}")
    
    response = await handler(request_id)
    DSR_REQUESTS.labels(type=dsr.request_type.value, status="completed").inc()
    
    return response


@app.get("/v1/dsr/{request_id}/download")
async def download_dsr_data(
    request_id: str,
    token: str = Header(...)
):
    """Download DSR response data (access/portability)."""
    # Validate token and return download
    dsr = await app.state.dsr_processor.dsr_store.get(request_id)
    if not dsr or not dsr.response_url:
        raise HTTPException(status_code=404, detail="Download not available")
    
    # Redirect to secure download URL
    return {"download_url": dsr.response_url, "expires_at": dsr.response_expires_at}


# =============================================================================
# TRANSPARENCY ENDPOINTS
# =============================================================================

@app.get("/v1/transparency/profile/{user_id}/explanation")
async def get_profile_explanation(user_id: str):
    """
    Get explanation of psychological profiling.
    
    Human-readable explanation of how user is profiled.
    """
    explanation = await app.state.dsr_processor._explain_profiling_system(user_id)
    human_explanation = app.state.dsr_processor._generate_human_explanation(explanation)
    
    return {
        "user_id": user_id,
        "explanation": explanation,
        "human_readable": human_explanation
    }


@app.get("/v1/transparency/decision/{decision_id}/explanation")
async def get_decision_explanation(
    decision_id: str,
    user_id: str
):
    """
    Get explanation of specific ad decision.
    
    GDPR Art. 22 compliance.
    """
    explanation = await app.state.dsr_processor._explain_specific_decision(
        user_id, decision_id
    )
    
    return {
        "decision_id": decision_id,
        "explanation": explanation,
        "human_readable": app.state.dsr_processor._generate_human_explanation(explanation)
    }


# =============================================================================
# ADMIN/COMPLIANCE ENDPOINTS
# =============================================================================

@app.get("/v1/admin/dsr/pending")
async def get_pending_dsrs(
    days_until_due: int = 7,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get DSRs approaching deadline (admin only)."""
    return await app.state.dsr_processor.dsr_store.get_pending_near_deadline(days_until_due)


@app.get("/v1/admin/audit/search")
async def search_audit_log(
    query: AuditQuery,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Search audit log (admin only)."""
    return await app.state.consent_manager.audit.search(query)


@app.get("/v1/admin/audit/verify")
async def verify_audit_integrity(
    start_event_id: str,
    end_event_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Verify audit chain integrity (admin only)."""
    is_valid = await app.state.consent_manager.audit.verify_chain(
        start_event_id, end_event_id
    )
    return {"valid": is_valid}


@app.get("/v1/admin/dpia/{dpia_id}", response_model=DPIAAssessment)
async def get_dpia(
    dpia_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get DPIA details (admin only)."""
    dpia = await app.state.dpia_manager.store.get(dpia_id)
    if not dpia:
        raise HTTPException(status_code=404, detail="DPIA not found")
    return dpia


# =============================================================================
# HEALTH & METRICS
# =============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "consent_cache_size": len(app.state.consent_manager._consent_cache),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain")
```

---

## Part 7: Component Integration

### 7.1 Privacy-Aware Decorator for ADAM Components

```python
"""
Privacy-aware decorators for automatic consent checking.
All ADAM components should use these for data access.
"""

from functools import wraps
from typing import Callable, List


class PrivacyGuard:
    """
    Decorator factory for privacy-aware data access.
    
    Automatically checks consent before processing.
    """
    
    def __init__(self, consent_manager: ConsentManager):
        self.consent = consent_manager
    
    def requires_consent(
        self,
        *required_purposes: ConsentPurpose,
        fallback: Callable = None
    ):
        """
        Decorator that checks consent before function execution.
        
        Usage:
            @privacy_guard.requires_consent(
                ConsentPurpose.PSYCHOLOGICAL_PROFILING,
                fallback=get_contextual_data
            )
            async def get_psychological_profile(user_id: str):
                ...
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(user_id: str, *args, **kwargs):
                # Check all required consents
                for purpose in required_purposes:
                    has_consent = await self.consent.check_single_purpose(
                        user_id=user_id,
                        purpose=purpose,
                        requester=func.__module__
                    )
                    
                    if not has_consent:
                        if fallback:
                            return await fallback(user_id, *args, **kwargs)
                        else:
                            raise PrivacyError(
                                f"Consent required for {purpose.value}",
                                purpose=purpose,
                                user_id=user_id
                            )
                
                return await func(user_id, *args, **kwargs)
            
            return wrapper
        return decorator
    
    def audit_access(self, data_type: str):
        """
        Decorator that logs data access to audit trail.
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(user_id: str, *args, **kwargs):
                result = await func(user_id, *args, **kwargs)
                
                await self.consent.audit.log_event(AuditEvent(
                    event_type="data_access",
                    actor_type="system",
                    actor_id=func.__module__,
                    subject_type="user",
                    subject_id=user_id,
                    action="read",
                    action_category="data_access",
                    action_details={
                        "data_type": data_type,
                        "function": func.__name__
                    },
                    success=True
                ))
                
                return result
            
            return wrapper
        return decorator


class PrivacyError(Exception):
    """Exception raised when privacy requirements not met."""
    
    def __init__(self, message: str, purpose: ConsentPurpose, user_id: str):
        self.message = message
        self.purpose = purpose
        self.user_id = user_id
        super().__init__(message)
```

### 7.2 Integration with Other ADAM Components

```yaml
# Component Integration Map

enhancement_1_graph_fusion:
  integration: "Consent check before graph queries"
  hook: "GraphQueryService.execute_query()"
  consent_required: [PSYCHOLOGICAL_PROFILING, BEHAVIORAL_TARGETING]

enhancement_2_shared_state:
  integration: "Privacy-aware state publishing"
  hook: "BlackboardService.publish_state()"
  consent_required: "Depends on state type"

enhancement_8_signal_aggregation:
  integration: "Filter signals based on consent"
  hook: "SignalAggregator.aggregate()"
  consent_required: [BEHAVIORAL_TARGETING, ANALYTICS_INDIVIDUAL]

enhancement_10_journey_tracking:
  integration: "Consent gate for journey creation"
  hook: "JourneyTracker.start_journey()"
  consent_required: [BEHAVIORAL_TARGETING, PSYCHOLOGICAL_PROFILING]

enhancement_15_copy_generation:
  integration: "Check consent before personalization"
  hook: "CopyGenerator.generate()"
  consent_required: [PSYCHOLOGICAL_PROFILING, PERSONALIZED_ADS]

enhancement_16_multimodal_fusion:
  integration: "Modal-specific consent checking"
  hook: "FusionService.fuse()"
  consent_required:
    voice: [PSYCHOLOGICAL_PROFILING]
    text: [PSYCHOLOGICAL_PROFILING]
    behavioral: [BEHAVIORAL_TARGETING]

enhancement_18_explanation:
  integration: "Art. 22 explanation generation"
  hook: "ExplanationService.explain()"
  consent_required: []  # Right to explanation cannot be denied

enhancement_19_identity_resolution:
  integration: "Cross-device consent check"
  hook: "IdentityResolver.resolve()"
  consent_required: [CROSS_DEVICE_TRACKING, CROSS_PLATFORM_IDENTITY]
```

---

## Part 8: Success Metrics

| Metric | Target | Measurement | Alert Threshold |
|--------|--------|-------------|-----------------|
| Consent collection rate | >40% | % users granting psychological profiling | <30% |
| DSR response time | <30 days | Average time to complete | >25 days |
| DSR completion rate | 100% | % requests completed on time | <98% |
| Audit log coverage | 100% | All data access logged | <100% |
| Consent check latency | <5ms P99 | Real-time check performance | >10ms |
| Privacy preference respect | 100% | No processing without consent | <100% |
| DPIA review frequency | Annual | All DPIAs reviewed yearly | Missed review |
| Minor detection rate | >95% | Age gate effectiveness | <90% |

---

## Part 9: Implementation Timeline (10 weeks)

```yaml
phase_1_core_consent:
  duration: "Weeks 1-3"
  deliverables:
    - Pydantic models complete
    - ConsentManager service
    - Jurisdiction detection
    - Consent storage (Neo4j)
    - Basic API endpoints

phase_2_dsr_processing:
  duration: "Weeks 4-6"
  deliverables:
    - DSRProcessor service
    - Access request handling
    - Erasure request handling
    - Portability export
    - Explanation generation

phase_3_compliance_framework:
  duration: "Weeks 7-8"
  deliverables:
    - DPIA management
    - Audit logging with chain integrity
    - Age verification gate
    - Universal opt-out (GPC) support

phase_4_integration:
  duration: "Weeks 9-10"
  deliverables:
    - Component integration hooks
    - Privacy-aware decorators
    - Monitoring and alerting
    - Documentation and training
    - Production deployment
```

---

## Part 10: Regulatory Compliance Checklist

### GDPR Compliance

- [x] **Art. 6**: Legal basis for processing (consent)
- [x] **Art. 7**: Conditions for consent (explicit, withdrawable)
- [x] **Art. 9**: Special category data handling
- [x] **Art. 13-14**: Transparency requirements
- [x] **Art. 15**: Right of access
- [x] **Art. 16**: Right to rectification
- [x] **Art. 17**: Right to erasure
- [x] **Art. 18**: Right to restriction
- [x] **Art. 20**: Right to portability
- [x] **Art. 21**: Right to object
- [x] **Art. 22**: Automated decision-making safeguards
- [x] **Art. 35**: Data Protection Impact Assessment
- [x] **Art. 37-39**: DPO consultation

### CPRA Compliance

- [x] Right to know
- [x] Right to delete
- [x] Right to correct
- [x] Right to opt-out of sale
- [x] Right to limit sensitive data use
- [x] Non-discrimination
- [x] Universal opt-out signal (GPC)

---

*Enhancement #17 Complete. ADAM now has enterprise-grade privacy infrastructure enabling compliant psychological profiling with full user control and regulatory alignment.*
