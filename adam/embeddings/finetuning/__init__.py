# =============================================================================
# ADAM Embedding Fine-Tuning Pipeline
# =============================================================================

"""
EMBEDDING FINE-TUNING

Domain-specific fine-tuning for psychological embeddings.

Components:
- Dataset creation from ADAM behavioral data
- Contrastive learning for personality traits
- Triplet mining for mechanism effectiveness
- Model export and versioning
"""

from adam.embeddings.finetuning.dataset import (
    FineTuningDataset,
    ContrastivePair,
    TripletSample,
    DatasetBuilder,
)
from adam.embeddings.finetuning.trainer import (
    EmbeddingTrainer,
    TrainingConfig,
    TrainingMetrics,
)
from adam.embeddings.finetuning.pipeline import (
    FineTuningPipeline,
    PipelineConfig,
    PipelineStatus,
)

__all__ = [
    "FineTuningDataset",
    "ContrastivePair",
    "TripletSample",
    "DatasetBuilder",
    "EmbeddingTrainer",
    "TrainingConfig",
    "TrainingMetrics",
    "FineTuningPipeline",
    "PipelineConfig",
    "PipelineStatus",
]
