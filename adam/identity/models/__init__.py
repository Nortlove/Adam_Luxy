# =============================================================================
# ADAM Enhancement #19: Identity Models Package
# Location: adam/identity/models/__init__.py
# =============================================================================

"""
Cross-Platform Identity Resolution Models

Identifier Models:
- IdentifierType: 20+ identifier types with classification
- MatchConfidence: Confidence levels for matching
- IdentifierSource: Where identifiers come from
- Identifier: Single identifier with metadata
- IdentityLink: Link between identifiers

Identity Models:
- UnifiedIdentity: One real person across devices
- MatchResult: Result of identity resolution

Household Models:
- HouseholdSignals: Signals for household detection
- HouseholdMember: Member of a household
- Household: Household containing multiple identities
"""

from .identifiers import (
    IdentifierType,
    MatchConfidence,
    IdentifierSource,
    Identifier,
    IdentityLink,
)

from .identity import (
    UnifiedIdentity,
    MatchResult,
)

from .household import (
    HouseholdSignals,
    HouseholdMember,
    Household,
)

__all__ = [
    # Identifiers
    "IdentifierType",
    "MatchConfidence",
    "IdentifierSource",
    "Identifier",
    "IdentityLink",
    
    # Identity
    "UnifiedIdentity",
    "MatchResult",
    
    # Household
    "HouseholdSignals",
    "HouseholdMember",
    "Household",
]
