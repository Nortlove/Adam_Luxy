# =============================================================================
# ADAM Privacy & Consent Framework (#17)
# =============================================================================

"""
PRIVACY & CONSENT FRAMEWORK

GDPR-compliant privacy and consent management.

Components:
- Consent management
- Data subject rights (access, erasure, portability)
- Privacy-preserving operations
- Audit logging
"""

from adam.privacy.models import (
    ConsentType,
    ConsentStatus,
    UserConsent,
    PrivacyPreference,
    DataSubjectRequest,
    PrivacyAuditLog,
)
from adam.privacy.service import (
    ConsentManager,
    DataSubjectRightsService,
    PrivacyService,
)

__all__ = [
    # Models
    "ConsentType",
    "ConsentStatus",
    "UserConsent",
    "PrivacyPreference",
    "DataSubjectRequest",
    "PrivacyAuditLog",
    # Services
    "ConsentManager",
    "DataSubjectRightsService",
    "PrivacyService",
]
