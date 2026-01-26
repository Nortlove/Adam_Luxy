# =============================================================================
# ADAM Voice/Audio Module (#07)
# =============================================================================

"""
VOICE/AUDIO MODULE

Audio processing for iHeart and voice interactions.

Components:
- SSML generation
- Voice synthesis
- Audio format optimization
- Prosody control
"""

from adam.audio.models import (
    VoiceProfile,
    AudioFormat,
    SSMLDocument,
    AudioVariant,
)
from adam.audio.ssml import SSMLGenerator
from adam.audio.synthesis import VoiceSynthesizer
from adam.audio.service import AudioService

__all__ = [
    # Models
    "VoiceProfile",
    "AudioFormat",
    "SSMLDocument",
    "AudioVariant",
    # Components
    "SSMLGenerator",
    "VoiceSynthesizer",
    "AudioService",
]
