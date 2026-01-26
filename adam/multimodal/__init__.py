# =============================================================================
# ADAM Multimodal Fusion (#16)
# =============================================================================

"""
MULTIMODAL FUSION

Cross-modal signal integration for holistic user understanding.

Components:
- Audio signal processing
- Visual signal processing
- Text signal processing
- Cross-modal fusion
"""

from adam.multimodal.models import (
    Modality,
    ModalitySignal,
    ModalityWeight,
    FusedProfile,
)
from adam.multimodal.service import (
    CrossModalFusion,
    MultimodalService,
)

__all__ = [
    # Models
    "Modality",
    "ModalitySignal",
    "ModalityWeight",
    "FusedProfile",
    # Components
    "CrossModalFusion",
    "MultimodalService",
]
