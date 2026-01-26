# =============================================================================
# ADAM Output Systems Package
# =============================================================================

"""
OUTPUT SYSTEMS

Components for content generation and brand matching.

Modules:
- brand_intelligence: Brand-user psychological matching
- copy_generation: Personality-matched copy generation
"""

from adam.output.brand_intelligence import BrandIntelligenceService, BrandProfile
from adam.output.copy_generation import CopyGenerationService, GeneratedCopy

__all__ = [
    "BrandIntelligenceService",
    "BrandProfile",
    "CopyGenerationService",
    "GeneratedCopy",
]
