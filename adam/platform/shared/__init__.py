# =============================================================================
# ADAM Cross-Platform Shared Services
# =============================================================================

"""
CROSS-PLATFORM SHARED SERVICES

Unified services for cross-platform user intelligence.

This module ensures that:
- User profiles are consistent across iHeart and WPP
- Mechanism effectiveness is properly merged
- Journey states are synchronized
- Learning signals propagate bidirectionally

Key Principles:
1. Single source of truth for user psychological profiles
2. Platform-specific adaptations without data fragmentation
3. Conflict resolution when platforms disagree
4. Audit trail for all cross-platform operations
"""

from adam.platform.shared.models import (
    UnifiedUserProfile,
    PlatformContribution,
    ProfileMergeResult,
    MechanismMergeResult,
    JourneySyncResult,
)
from adam.platform.shared.profile_service import CrossPlatformProfileService
from adam.platform.shared.mechanism_merging import MechanismMergingService
from adam.platform.shared.journey_sync import JourneySyncService

__all__ = [
    # Models
    "UnifiedUserProfile",
    "PlatformContribution",
    "ProfileMergeResult",
    "MechanismMergeResult",
    "JourneySyncResult",
    # Services
    "CrossPlatformProfileService",
    "MechanismMergingService",
    "JourneySyncService",
]
