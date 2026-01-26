# =============================================================================
# ADAM Copy Generation (#15)
# =============================================================================

"""
COPY GENERATION

Personality-matched copy generation for text and audio.
"""

from adam.output.copy_generation.models import (
    CopyRequest,
    GeneratedCopy,
    AudioCopy,
    TextVariant,
)
from adam.output.copy_generation.service import CopyGenerationService

__all__ = [
    "CopyRequest",
    "GeneratedCopy",
    "AudioCopy",
    "TextVariant",
    "CopyGenerationService",
]
