# =============================================================================
# ADAM Enhancement #19: Privacy Package
# Location: adam/identity/privacy/__init__.py
# =============================================================================

"""
Privacy-Preserving Identity Operations

Bloom Filters:
- Secure matching in clean rooms
- No raw identifier exchange
- Probabilistic with tunable FPR

Differential Privacy:
- Privacy budget tracking (epsilon)
- Noise injection for aggregates
- Membership inference protection
"""

from .bloom_filter import (
    BloomFilterConfig,
    BloomFilter,
    BloomFilterMatcher,
)

from .differential_privacy import (
    PrivacyBudget,
    LaplaceMechanism,
    GaussianMechanism,
    DifferentialPrivacyEngine,
    get_differential_privacy_engine,
)

__all__ = [
    # Bloom Filters
    "BloomFilterConfig",
    "BloomFilter",
    "BloomFilterMatcher",
    
    # Differential Privacy
    "PrivacyBudget",
    "LaplaceMechanism",
    "GaussianMechanism",
    "DifferentialPrivacyEngine",
    "get_differential_privacy_engine",
]
