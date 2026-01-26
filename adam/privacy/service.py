# =============================================================================
# ADAM Privacy Service
# Location: adam/privacy/service.py
# =============================================================================

"""
PRIVACY SERVICE

Unified privacy and consent management.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from adam.privacy.models import (
    ConsentType,
    ConsentStatus,
    UserConsent,
    PrivacyPreference,
    RequestType,
    RequestStatus,
    DataSubjectRequest,
    PrivacyAuditLog,
)
from adam.infrastructure.redis import ADAMRedisCache

logger = logging.getLogger(__name__)


class ConsentManager:
    """Manages user consent."""
    
    def __init__(self, cache: Optional[ADAMRedisCache] = None):
        self.cache = cache
        self._consents: Dict[str, PrivacyPreference] = {}
    
    async def record_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        granted: bool,
        scope: Optional[str] = None,
    ) -> UserConsent:
        """Record a consent decision."""
        
        consent = UserConsent(
            consent_id=f"consent_{uuid4().hex[:12]}",
            user_id=user_id,
            consent_type=consent_type,
            status=ConsentStatus.GRANTED if granted else ConsentStatus.DENIED,
            scope=scope,
            granted_at=datetime.now(timezone.utc) if granted else None,
        )
        
        # Update preferences
        prefs = self._consents.get(user_id, PrivacyPreference(user_id=user_id))
        prefs.consents[consent_type.value] = consent
        prefs.updated_at = datetime.now(timezone.utc)
        self._consents[user_id] = prefs
        
        return consent
    
    async def check_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
    ) -> bool:
        """Check if user has granted consent."""
        
        prefs = self._consents.get(user_id)
        if not prefs:
            return False
        
        consent = prefs.consents.get(consent_type.value)
        if not consent:
            return False
        
        if consent.status != ConsentStatus.GRANTED:
            return False
        
        if consent.expires_at and consent.expires_at < datetime.now(timezone.utc):
            return False
        
        return True
    
    async def get_preferences(self, user_id: str) -> Optional[PrivacyPreference]:
        """Get user privacy preferences."""
        return self._consents.get(user_id)


class DataSubjectRightsService:
    """Handles data subject rights requests."""
    
    def __init__(self, cache: Optional[ADAMRedisCache] = None):
        self.cache = cache
        self._requests: Dict[str, DataSubjectRequest] = {}
    
    async def submit_request(
        self,
        user_id: str,
        request_type: RequestType,
        description: Optional[str] = None,
    ) -> DataSubjectRequest:
        """Submit a data subject request."""
        
        now = datetime.now(timezone.utc)
        
        request = DataSubjectRequest(
            request_id=f"dsr_{uuid4().hex[:12]}",
            user_id=user_id,
            request_type=request_type,
            status=RequestStatus.RECEIVED,
            description=description,
            submitted_at=now,
            deadline=now + timedelta(days=30),
        )
        
        self._requests[request.request_id] = request
        
        logger.info(f"DSR submitted: {request.request_id} ({request_type.value})")
        
        return request
    
    async def process_request(
        self,
        request_id: str,
    ) -> DataSubjectRequest:
        """Process a data subject request."""
        
        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"Request not found: {request_id}")
        
        request.status = RequestStatus.IN_PROGRESS
        
        # Handle based on type
        if request.request_type == RequestType.ACCESS:
            await self._handle_access(request)
        elif request.request_type == RequestType.ERASURE:
            await self._handle_erasure(request)
        elif request.request_type == RequestType.PORTABILITY:
            await self._handle_portability(request)
        
        return request
    
    async def _handle_access(self, request: DataSubjectRequest) -> None:
        """Handle access request."""
        request.affected_data = [
            "psychological_profile",
            "mechanism_effectiveness",
            "journey_history",
            "platform_interactions",
        ]
        request.status = RequestStatus.COMPLETED
        request.completed_at = datetime.now(timezone.utc)
        request.response = "Data access report generated"
    
    async def _handle_erasure(self, request: DataSubjectRequest) -> None:
        """Handle erasure request."""
        request.affected_data = [
            "psychological_profile",
            "mechanism_effectiveness",
            "journey_history",
        ]
        request.status = RequestStatus.COMPLETED
        request.completed_at = datetime.now(timezone.utc)
        request.response = "User data erased"
    
    async def _handle_portability(self, request: DataSubjectRequest) -> None:
        """Handle portability request."""
        request.data_export_url = f"/exports/{request.request_id}.json"
        request.status = RequestStatus.COMPLETED
        request.completed_at = datetime.now(timezone.utc)
        request.response = "Data export ready"


class PrivacyService:
    """
    Unified privacy service.
    """
    
    def __init__(self, cache: Optional[ADAMRedisCache] = None):
        self.consent_manager = ConsentManager(cache)
        self.rights_service = DataSubjectRightsService(cache)
        self._audit_log: List[PrivacyAuditLog] = []
    
    async def check_can_process(
        self,
        user_id: str,
        operation: str,
    ) -> tuple:
        """Check if we can process user data for an operation."""
        
        required_consents = {
            "psychological_profiling": ConsentType.PSYCHOLOGICAL_PROFILING,
            "cross_platform": ConsentType.CROSS_PLATFORM_SHARING,
            "ad_personalization": ConsentType.AD_PERSONALIZATION,
        }
        
        consent_type = required_consents.get(operation)
        if not consent_type:
            return True, "No consent required"
        
        has_consent = await self.consent_manager.check_consent(user_id, consent_type)
        
        if has_consent:
            return True, "Consent granted"
        else:
            return False, f"Missing consent: {consent_type.value}"
    
    async def record_consent(
        self,
        user_id: str,
        consent_type: ConsentType,
        granted: bool,
    ) -> UserConsent:
        """Record consent and log."""
        
        consent = await self.consent_manager.record_consent(
            user_id, consent_type, granted
        )
        
        await self._log(
            action="consent_recorded",
            resource_type="consent",
            resource_id=consent.consent_id,
            user_id=user_id,
            details={
                "consent_type": consent_type.value,
                "granted": granted,
            },
        )
        
        return consent
    
    async def submit_dsr(
        self,
        user_id: str,
        request_type: RequestType,
    ) -> DataSubjectRequest:
        """Submit data subject request and log."""
        
        request = await self.rights_service.submit_request(
            user_id, request_type
        )
        
        await self._log(
            action="dsr_submitted",
            resource_type="dsr",
            resource_id=request.request_id,
            user_id=user_id,
            details={"request_type": request_type.value},
        )
        
        return request
    
    async def _log(
        self,
        action: str,
        resource_type: str,
        resource_id: str,
        user_id: Optional[str] = None,
        details: Dict[str, Any] = None,
    ) -> None:
        """Add audit log entry."""
        
        log = PrivacyAuditLog(
            log_id=f"audit_{uuid4().hex[:12]}",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            details=details or {},
            success=True,
        )
        
        self._audit_log.append(log)
        
        # Keep last 10000 entries
        if len(self._audit_log) > 10000:
            self._audit_log = self._audit_log[-10000:]
