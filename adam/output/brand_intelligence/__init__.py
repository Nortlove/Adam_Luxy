# =============================================================================
# ADAM Brand Intelligence (#14)
# =============================================================================

"""
BRAND INTELLIGENCE

Brand psychological profiling and user-brand matching.
"""

from adam.output.brand_intelligence.models import (
    BrandPersonality,
    BrandProfile,
    BrandUserMatch,
)
from adam.output.brand_intelligence.service import BrandIntelligenceService

__all__ = [
    "BrandPersonality",
    "BrandProfile",
    "BrandUserMatch",
    "BrandIntelligenceService",
]
