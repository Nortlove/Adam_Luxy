# =============================================================================
# ADAM Enhancement #19: Household Package
# Location: adam/identity/household/__init__.py
# =============================================================================

"""
Household Resolution

Detects and links identities belonging to the same household using:
- Shared IP addresses
- Same postal/address hash
- WiFi SSID signals
- Activity pattern overlap
"""

from .resolver import (
    HouseholdResolver,
    get_household_resolver,
)

__all__ = [
    "HouseholdResolver",
    "get_household_resolver",
]
