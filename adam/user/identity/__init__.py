# =============================================================================
# ADAM Identity Resolution (#19)
# =============================================================================

"""
IDENTITY RESOLUTION

Cross-platform user identity linking and resolution.
"""

from adam.user.identity.service import IdentityResolutionService
from adam.user.identity.models import (
    PlatformIdentity,
    UnifiedIdentity,
    IdentityMatch,
)

__all__ = [
    "IdentityResolutionService",
    "PlatformIdentity",
    "UnifiedIdentity",
    "IdentityMatch",
]
