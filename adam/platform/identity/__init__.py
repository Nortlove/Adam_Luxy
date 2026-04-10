"""
ADAM Identity Resolution

Pluggable identity resolution modules that map anonymous/pseudonymous
signals to consistent user profiles. ADAM's key advantage: the system
works WITHOUT identity via contextual + psychological inference.

Modules:
  - ContextualResolver: No ID needed — content psychology + NDF = targeting
  - FirstPartyResolver: Publisher first-party IDs
  - UID2Resolver: Unified ID 2.0 / EUID
  - HouseholdResolver: IP-based household inference
"""

from adam.platform.identity.resolver import (
    BaseIdentityResolver,
    IdentityResolution,
    ContextualResolver,
    FirstPartyResolver,
    UID2Resolver,
    HouseholdResolver,
    resolve_identity,
)

__all__ = [
    "BaseIdentityResolver",
    "IdentityResolution",
    "ContextualResolver",
    "FirstPartyResolver",
    "UID2Resolver",
    "HouseholdResolver",
    "resolve_identity",
]
