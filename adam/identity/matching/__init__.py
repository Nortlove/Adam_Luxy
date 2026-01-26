# =============================================================================
# ADAM Enhancement #19: Matching Package
# Location: adam/identity/matching/__init__.py
# =============================================================================

"""
Identity Matching Components

Deterministic Matching:
- 100% confidence exact matches
- Email, phone, login, platform IDs

Probabilistic Matching:
- ML-based feature scoring
- IP, fingerprint, behavioral signals
"""

from .deterministic import DeterministicMatcher
from .probabilistic import ProbabilisticMatcher, MatchFeatures

__all__ = [
    "DeterministicMatcher",
    "ProbabilisticMatcher",
    "MatchFeatures",
]
