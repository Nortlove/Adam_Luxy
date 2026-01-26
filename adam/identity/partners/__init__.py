# =============================================================================
# ADAM Enhancement #19: Partner Connectors Package
# Location: adam/identity/partners/__init__.py
# =============================================================================

"""
Partner Identity Connectors

Connectors for cross-platform identity resolution:
- UID2: Unified ID 2.0 (email/phone based)
- iHeart: iHeart platform integration
- RampID: LiveRamp identity resolution
"""

from .base import (
    PartnerConnector,
    PartnerConfig,
    PartnerSyncResult,
)

from .uid2 import (
    UID2Connector,
    UID2Config,
    get_uid2_connector,
)

from .iheart import (
    IHeartConnector,
    IHeartConfig,
    get_iheart_connector,
)

from .rampid import (
    RampIDConnector,
    RampIDConfig,
    get_rampid_connector,
)

__all__ = [
    # Base
    "PartnerConnector",
    "PartnerConfig",
    "PartnerSyncResult",
    
    # UID2
    "UID2Connector",
    "UID2Config",
    "get_uid2_connector",
    
    # iHeart
    "IHeartConnector",
    "IHeartConfig",
    "get_iheart_connector",
    
    # RampID
    "RampIDConnector",
    "RampIDConfig",
    "get_rampid_connector",
]
