# =============================================================================
# ADAM Embedding Fine-Tuning Trainer
# Location: adam/embeddings/finetuning/trainer.py
# =============================================================================

"""
EMBEDDING TRAINER

Training infrastructure for fine-tuning embedding models.

Supports:
- Contrastive learning (SimCLR, CoSENT)
- Triplet loss training
- Multi-task learning
- Gradient accumulation
- Mixed precision training
"""

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field
from prometheus_client import Counter, Gauge, Histogram

from adam.embeddings.finetuning.dataset import (
    FineTuningDataset,
    ContrastivePair,
    TripletSample,
)

logger = logging.getLogger(__name__)


# =============================================================================
# PROMETHEUS METRICS
# =============================================================================

TRAINING_LOSS = Gauge(
    "adam_embedding_training_loss",
    "Current training loss",
    ["model", "loss_type"],
)

TRAINING_STEP = Counter(
    "adam_embedding_training_steps_total",
    "Total training steps",
    ["model"],
)

TRAINING_EPOCH = Gauge(
    "adam_embedding_training_epoch",
    "Current training epoch",
    ["model"],
)


# =============================================================================
# CONFIGURATION
# =============================================================================

class LossType(str, Enum):
    """Loss function types."""
    
    CONTRASTIVE = "contrastive"
    TRIPLET = "triplet"
    COSENT = "cosent"  # Cosine sentence embedding
    MULTIPLE_NEGATIVES_RANKING = "mnr"


class TrainingConfig(BaseModel):
    """Configuration for embedding training."""
    
    # Model
    base_model: str = "all-MiniLM-L6-v2"
    output_dimensions: int = 384
    
    # Training
    batch_size: int = 32
    epochs: int = 10
    learning_rate: float = 2e-5
    warmup_ratio: float = 0.1
    weight_decay: float = 0.01
    
    # Loss
    loss_type: LossType = LossType.COSENT
    margin: float = 0.5  # For triplet loss
    temperature: float = 0.05  # For contrastive loss
    
    # Optimization
    gradient_accumulation_steps: int = 1
    max_grad_norm: float = 1.0
    fp16: bool = False
    
    # Checkpointing
    checkpoint_dir: str = "./checkpoints"
    checkpoint_every_steps: int = 1000
    save_total_limit: int = 3
    
    # Evaluation
    eval_steps: int = 500
    early_stopping_patience: int = 3
    early_stopping_threshold: float = 0.001
    
    # Logging
    log_steps: int = 100


class TrainingMetrics(BaseModel):
    """Metrics from training run."""
    
    run_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    
    # Training progress
    epoch: int = 0
    step: int = 0
    total_steps: int = 0
    
    # Losses
    train_loss: float = 0.0
    eval_loss: Optional[float] = None
    best_eval_loss: Optional[float] = None
    
    # Learning rate
    current_lr: float = 0.0
    
    # Timing
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    training_time_seconds: float = 0.0
    
    # Checkpoints
    checkpoints_saved: int = 0
    best_checkpoint_path: Optional[str] = None


# =============================================================================
# LOSS FUNCTIONS
# =============================================================================

class EmbeddingLoss:
    """Base class for embedding losses."""
    
    def __call__(
        self,
        embeddings: Any,
        labels: Any,
    ) -> Any:
        raise NotImplementedError


class ContrastiveLoss(EmbeddingLoss):
    """
    Contrastive loss for similarity learning.
    
    L = (1-y) * 0.5 * d^2 + y * 0.5 * max(0, margin-d)^2
    """
    
    def __init__(self, margin: float = 0.5, temperature: float = 0.05):
        self.margin = margin
        self.temperature = temperature
    
    def __call__(
        self,
        embeddings_a,  # Tensor
        embeddings_b,  # Tensor
        labels,  # Tensor (1 = similar, 0 = dissimilar)
    ):
        """Compute contrastive loss."""
        try:
            import torch
            import torch.nn.functional as F
            
            # Normalize embeddings
            embeddings_a = F.normalize(embeddings_a, p=2, dim=1)
            embeddings_b = F.normalize(embeddings_b, p=2, dim=1)
            
            # Compute cosine similarity
            similarity = torch.sum(embeddings_a * embeddings_b, dim=1)
            
            # Convert to distance
            distance = 1 - similarity
            
            # Contrastive loss
            loss = (
                labels * 0.5 * distance.pow(2) +
                (1 - labels) * 0.5 * F.relu(self.margin - distance).pow(2)
            )
            
            return loss.mean()
            
        except ImportError:
            raise RuntimeError("PyTorch required for training")


class TripletLoss(EmbeddingLoss):
    """
    Triplet loss for metric learning.
    
    L = max(0, d(a,p) - d(a,n) + margin)
    """
    
    def __init__(self, margin: float = 0.5):
        self.margin = margin
    
    def __call__(
        self,
        anchor,  # Tensor
        positive,  # Tensor
        negative,  # Tensor
    ):
        """Compute triplet loss."""
        try:
            import torch
            import torch.nn.functional as F
            
            # Normalize
            anchor = F.normalize(anchor, p=2, dim=1)
            positive = F.normalize(positive, p=2, dim=1)
            negative = F.normalize(negative, p=2, dim=1)
            
            # Distances
            pos_dist = 1 - torch.sum(anchor * positive, dim=1)
            neg_dist = 1 - torch.sum(anchor * negative, dim=1)
            
            # Triplet loss
            loss = F.relu(pos_dist - neg_dist + self.margin)
            
            return loss.mean()
            
        except ImportError:
            raise RuntimeError("PyTorch required for training")


class CoSENTLoss(EmbeddingLoss):
    """
    CoSENT (Cosine Sentence Embedding) loss.
    
    A ranking loss that uses cosine similarity directly.
    """
    
    def __init__(self, temperature: float = 0.05):
        self.temperature = temperature
    
    def __call__(
        self,
        embeddings_a,
        embeddings_b,
        labels,  # Similarity scores (0-1)
    ):
        """Compute CoSENT loss."""
        try:
            import torch
            import torch.nn.functional as F
            
            # Normalize
            embeddings_a = F.normalize(embeddings_a, p=2, dim=1)
            embeddings_b = F.normalize(embeddings_b, p=2, dim=1)
            
            # Cosine similarity
            similarities = torch.sum(embeddings_a * embeddings_b, dim=1)
            
            # Scale
            similarities = similarities / self.temperature
            labels = labels / self.temperature
            
            # Pairwise ranking loss
            batch_size = embeddings_a.size(0)
            loss = 0.0
            count = 0
            
            for i in range(batch_size):
                for j in range(i + 1, batch_size):
                    # If label[i] > label[j], similarity[i] should be > similarity[j]
                    if labels[i] > labels[j]:
                        loss += F.relu(similarities[j] - similarities[i] + 1)
                        count += 1
                    elif labels[j] > labels[i]:
                        loss += F.relu(similarities[i] - similarities[j] + 1)
                        count += 1
            
            return loss / max(count, 1)
            
        except ImportError:
            raise RuntimeError("PyTorch required for training")


# =============================================================================
# TRAINER
# =============================================================================

class EmbeddingTrainer:
    """
    Trainer for embedding model fine-tuning.
    
    Usage:
        trainer = EmbeddingTrainer(config)
        trainer.train(train_dataset, val_dataset)
        trainer.save("path/to/model")
    """
    
    def __init__(
        self,
        config: TrainingConfig,
        model_name: Optional[str] = None,
    ):
        self.config = config
        self.model_name = model_name or config.base_model
        self.metrics = TrainingMetrics()
        
        self._model = None
        self._optimizer = None
        self._scheduler = None
        self._loss_fn = None
        self._device = "cpu"
    
    def _initialize_model(self) -> None:
        """Initialize the model and training components."""
        try:
            import torch
            from sentence_transformers import SentenceTransformer
            
            # Detect device
            self._device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device: {self._device}")
            
            # Load base model
            self._model = SentenceTransformer(self.config.base_model)
            self._model.to(self._device)
            
            # Initialize loss function
            if self.config.loss_type == LossType.CONTRASTIVE:
                self._loss_fn = ContrastiveLoss(
                    margin=self.config.margin,
                    temperature=self.config.temperature,
                )
            elif self.config.loss_type == LossType.TRIPLET:
                self._loss_fn = TripletLoss(margin=self.config.margin)
            elif self.config.loss_type == LossType.COSENT:
                self._loss_fn = CoSENTLoss(temperature=self.config.temperature)
            else:
                self._loss_fn = CoSENTLoss()
            
            # Initialize optimizer
            self._optimizer = torch.optim.AdamW(
                self._model.parameters(),
                lr=self.config.learning_rate,
                weight_decay=self.config.weight_decay,
            )
            
            logger.info(f"Model initialized: {self.config.base_model}")
            
        except ImportError:
            raise RuntimeError(
                "Training requires sentence-transformers and torch. "
                "Run: pip install sentence-transformers torch"
            )
    
    def train(
        self,
        train_dataset: FineTuningDataset,
        val_dataset: Optional[FineTuningDataset] = None,
        callback: Optional[Callable] = None,
    ) -> TrainingMetrics:
        """
        Train the embedding model.
        
        Args:
            train_dataset: Training dataset
            val_dataset: Validation dataset (optional)
            callback: Callback function called after each step
            
        Returns:
            Training metrics
        """
        import torch
        
        self._initialize_model()
        
        # Create data loaders
        train_pairs = self._prepare_contrastive_data(train_dataset.contrastive_pairs)
        train_triplets = self._prepare_triplet_data(train_dataset.triplets)
        
        # Calculate total steps
        samples_per_epoch = len(train_pairs) + len(train_triplets)
        steps_per_epoch = samples_per_epoch // self.config.batch_size
        self.metrics.total_steps = steps_per_epoch * self.config.epochs
        
        # Initialize scheduler
        warmup_steps = int(self.metrics.total_steps * self.config.warmup_ratio)
        self._scheduler = torch.optim.lr_scheduler.LinearLR(
            self._optimizer,
            start_factor=0.1,
            total_iters=warmup_steps,
        )
        
        logger.info(f"Starting training: {self.config.epochs} epochs, "
                   f"{self.metrics.total_steps} total steps")
        
        # Training loop
        best_loss = float("inf")
        patience_counter = 0
        
        for epoch in range(self.config.epochs):
            self.metrics.epoch = epoch + 1
            TRAINING_EPOCH.labels(model=self.model_name).set(epoch + 1)
            
            # Train epoch
            epoch_loss = self._train_epoch(train_pairs, train_triplets, callback)
            self.metrics.train_loss = epoch_loss
            TRAINING_LOSS.labels(
                model=self.model_name, loss_type="train"
            ).set(epoch_loss)
            
            logger.info(f"Epoch {epoch + 1}/{self.config.epochs}, "
                       f"Loss: {epoch_loss:.4f}")
            
            # Evaluate
            if val_dataset:
                val_pairs = self._prepare_contrastive_data(val_dataset.contrastive_pairs)
                eval_loss = self._evaluate(val_pairs)
                self.metrics.eval_loss = eval_loss
                TRAINING_LOSS.labels(
                    model=self.model_name, loss_type="eval"
                ).set(eval_loss)
                
                logger.info(f"Validation loss: {eval_loss:.4f}")
                
                # Early stopping check
                if eval_loss < best_loss - self.config.early_stopping_threshold:
                    best_loss = eval_loss
                    self.metrics.best_eval_loss = best_loss
                    patience_counter = 0
                    
                    # Save best checkpoint
                    checkpoint_path = self._save_checkpoint("best")
                    self.metrics.best_checkpoint_path = checkpoint_path
                else:
                    patience_counter += 1
                    if patience_counter >= self.config.early_stopping_patience:
                        logger.info(f"Early stopping at epoch {epoch + 1}")
                        break
            
            # Regular checkpoint
            if (epoch + 1) % 5 == 0:
                self._save_checkpoint(f"epoch_{epoch + 1}")
        
        # Final save
        self._save_checkpoint("final")
        
        self.metrics.training_time_seconds = (
            datetime.now(timezone.utc) - self.metrics.started_at
        ).total_seconds()
        self.metrics.last_updated = datetime.now(timezone.utc)
        
        return self.metrics
    
    def _train_epoch(
        self,
        pairs: List[Tuple],
        triplets: List[Tuple],
        callback: Optional[Callable],
    ) -> float:
        """Train for one epoch."""
        import torch
        import random
        
        self._model.train()
        total_loss = 0.0
        num_batches = 0
        
        # Shuffle data
        random.shuffle(pairs)
        random.shuffle(triplets)
        
        # Train on contrastive pairs
        for i in range(0, len(pairs), self.config.batch_size):
            batch = pairs[i:i + self.config.batch_size]
            
            texts_a = [p[0] for p in batch]
            texts_b = [p[1] for p in batch]
            labels = torch.tensor([p[2] for p in batch], dtype=torch.float32)
            labels = labels.to(self._device)
            
            # Encode
            embeddings_a = self._model.encode(
                texts_a, convert_to_tensor=True, show_progress_bar=False
            )
            embeddings_b = self._model.encode(
                texts_b, convert_to_tensor=True, show_progress_bar=False
            )
            
            # Compute loss
            if self.config.loss_type == LossType.TRIPLET:
                continue  # Skip, handle separately
            else:
                loss = self._loss_fn(embeddings_a, embeddings_b, labels)
            
            # Backward
            loss.backward()
            
            if (num_batches + 1) % self.config.gradient_accumulation_steps == 0:
                torch.nn.utils.clip_grad_norm_(
                    self._model.parameters(),
                    self.config.max_grad_norm,
                )
                self._optimizer.step()
                self._scheduler.step()
                self._optimizer.zero_grad()
            
            total_loss += loss.item()
            num_batches += 1
            self.metrics.step += 1
            TRAINING_STEP.labels(model=self.model_name).inc()
            
            if callback:
                callback(self.metrics)
        
        # Train on triplets
        for i in range(0, len(triplets), self.config.batch_size):
            batch = triplets[i:i + self.config.batch_size]
            
            anchors = [t[0] for t in batch]
            positives = [t[1] for t in batch]
            negatives = [t[2] for t in batch]
            
            anchor_emb = self._model.encode(
                anchors, convert_to_tensor=True, show_progress_bar=False
            )
            positive_emb = self._model.encode(
                positives, convert_to_tensor=True, show_progress_bar=False
            )
            negative_emb = self._model.encode(
                negatives, convert_to_tensor=True, show_progress_bar=False
            )
            
            loss = TripletLoss(self.config.margin)(
                anchor_emb, positive_emb, negative_emb
            )
            
            loss.backward()
            
            if (num_batches + 1) % self.config.gradient_accumulation_steps == 0:
                torch.nn.utils.clip_grad_norm_(
                    self._model.parameters(),
                    self.config.max_grad_norm,
                )
                self._optimizer.step()
                self._scheduler.step()
                self._optimizer.zero_grad()
            
            total_loss += loss.item()
            num_batches += 1
            self.metrics.step += 1
        
        return total_loss / max(num_batches, 1)
    
    def _evaluate(self, pairs: List[Tuple]) -> float:
        """Evaluate on validation set."""
        import torch
        
        self._model.eval()
        total_loss = 0.0
        num_batches = 0
        
        with torch.no_grad():
            for i in range(0, len(pairs), self.config.batch_size):
                batch = pairs[i:i + self.config.batch_size]
                
                texts_a = [p[0] for p in batch]
                texts_b = [p[1] for p in batch]
                labels = torch.tensor([p[2] for p in batch], dtype=torch.float32)
                labels = labels.to(self._device)
                
                embeddings_a = self._model.encode(
                    texts_a, convert_to_tensor=True, show_progress_bar=False
                )
                embeddings_b = self._model.encode(
                    texts_b, convert_to_tensor=True, show_progress_bar=False
                )
                
                loss = self._loss_fn(embeddings_a, embeddings_b, labels)
                total_loss += loss.item()
                num_batches += 1
        
        return total_loss / max(num_batches, 1)
    
    def _prepare_contrastive_data(
        self,
        pairs: List[ContrastivePair],
    ) -> List[Tuple[str, str, float]]:
        """Prepare contrastive pairs for training."""
        return [(p.text_a, p.text_b, p.label) for p in pairs]
    
    def _prepare_triplet_data(
        self,
        triplets: List[TripletSample],
    ) -> List[Tuple[str, str, str]]:
        """Prepare triplets for training."""
        return [(t.anchor, t.positive, t.negative) for t in triplets]
    
    def _save_checkpoint(self, name: str) -> str:
        """Save a checkpoint."""
        checkpoint_dir = Path(self.config.checkpoint_dir)
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        path = checkpoint_dir / f"{self.model_name}_{name}"
        self._model.save(str(path))
        
        self.metrics.checkpoints_saved += 1
        logger.info(f"Saved checkpoint: {path}")
        
        return str(path)
    
    def save(self, path: str) -> None:
        """Save the trained model."""
        if self._model:
            self._model.save(path)
            logger.info(f"Model saved to {path}")
    
    def load(self, path: str) -> None:
        """Load a trained model."""
        from sentence_transformers import SentenceTransformer
        
        self._model = SentenceTransformer(path)
        logger.info(f"Model loaded from {path}")
