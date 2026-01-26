# =============================================================================
# ADAM Linguistic Signal Service
# Location: adam/signals/linguistic/__init__.py
# =============================================================================

"""
LINGUISTIC SIGNAL SERVICE

Analyzes text for psychological indicators using LIWC-style analysis
and modern NLP techniques.

Key Capabilities:
- Big Five personality inference from text
- Regulatory focus detection (promotion/prevention)
- Emotional valence and arousal extraction
- Cognitive complexity markers
- Temporal orientation signals
"""

from adam.signals.linguistic.models import (
    LinguisticSignal,
    LinguisticFeatures,
    TextPsychologyProfile,
    TemporalMarkers,
    EmotionalValence,
)
from adam.signals.linguistic.service import LinguisticSignalService

__all__ = [
    "LinguisticSignal",
    "LinguisticFeatures",
    "TextPsychologyProfile",
    "TemporalMarkers",
    "EmotionalValence",
    "LinguisticSignalService",
]
