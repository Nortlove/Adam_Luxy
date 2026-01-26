# =============================================================================
# ADAM Embedding Fine-Tuning Pipeline
# Location: adam/embeddings/finetuning/pipeline.py
# =============================================================================

"""
FINE-TUNING PIPELINE

End-to-end pipeline for embedding model fine-tuning.

Stages:
1. Data Collection - Gather behavioral data
2. Dataset Creation - Build training datasets
3. Model Training - Fine-tune embedding model
4. Evaluation - Assess model quality
5. Deployment - Export and version model
"""

import asyncio
import logging
import os
import shutil
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field
from prometheus_client import Counter, Gauge

from adam.embeddings.finetuning.dataset import (
    FineTuningDataset,
    DatasetBuilder,
    LabelSource,
)
from adam.embeddings.finetuning.trainer import (
    EmbeddingTrainer,
    TrainingConfig,
    TrainingMetrics,
)
from adam.infrastructure.redis import ADAMRedisCache

logger = logging.getLogger(__name__)


# =============================================================================
# PROMETHEUS METRICS
# =============================================================================

PIPELINE_RUNS = Counter(
    "adam_finetuning_pipeline_runs_total",
    "Fine-tuning pipeline runs",
    ["status"],
)

PIPELINE_STAGE = Gauge(
    "adam_finetuning_pipeline_stage",
    "Current pipeline stage",
    ["run_id"],
)


# =============================================================================
# MODELS
# =============================================================================

class PipelineStage(str, Enum):
    """Pipeline stages."""
    
    INITIALIZED = "initialized"
    DATA_COLLECTION = "data_collection"
    DATASET_CREATION = "dataset_creation"
    TRAINING = "training"
    EVALUATION = "evaluation"
    DEPLOYMENT = "deployment"
    COMPLETED = "completed"
    FAILED = "failed"


class PipelineStatus(BaseModel):
    """Status of a pipeline run."""
    
    run_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    
    # Progress
    stage: PipelineStage = PipelineStage.INITIALIZED
    progress_percent: float = 0.0
    
    # Timing
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: Optional[datetime] = None
    
    # Results
    dataset_stats: Dict[str, Any] = Field(default_factory=dict)
    training_metrics: Optional[TrainingMetrics] = None
    evaluation_results: Dict[str, Any] = Field(default_factory=dict)
    
    # Output
    model_path: Optional[str] = None
    model_version: Optional[str] = None
    
    # Errors
    error: Optional[str] = None


class PipelineConfig(BaseModel):
    """Configuration for fine-tuning pipeline."""
    
    # Identifiers
    name: str = "adam_psychological_embedding"
    version: str = "1.0.0"
    
    # Data collection
    min_samples: int = 1000
    include_synthetic: bool = True
    synthetic_samples: int = 2000
    
    # Dataset
    train_ratio: float = 0.8
    val_ratio: float = 0.1
    test_ratio: float = 0.1
    
    # Training
    training_config: TrainingConfig = Field(default_factory=TrainingConfig)
    
    # Evaluation
    min_similarity_correlation: float = 0.7  # Min correlation with ground truth
    max_eval_loss: float = 0.5
    
    # Output
    output_dir: str = "./models/embeddings"
    keep_checkpoints: bool = True


# =============================================================================
# DATA COLLECTORS
# =============================================================================

class DataCollector:
    """Collects data from ADAM systems for fine-tuning."""
    
    def __init__(
        self,
        cache: Optional[ADAMRedisCache] = None,
    ):
        self.cache = cache
    
    async def collect_conversion_outcomes(
        self,
        limit: int = 10000,
    ) -> List[Dict[str, Any]]:
        """Collect conversion outcome data."""
        # In production, this would query Neo4j/Redis
        # For now, return empty list (will use synthetic data)
        logger.info("Collecting conversion outcomes...")
        return []
    
    async def collect_mechanism_effectiveness(
        self,
        limit: int = 10000,
    ) -> List[Dict[str, Any]]:
        """Collect mechanism effectiveness data."""
        logger.info("Collecting mechanism effectiveness...")
        return []
    
    async def collect_psychological_profiles(
        self,
        limit: int = 10000,
    ) -> List[Dict[str, Any]]:
        """Collect psychological profile data."""
        logger.info("Collecting psychological profiles...")
        return []
    
    async def collect_ad_user_matches(
        self,
        limit: int = 10000,
    ) -> List[Dict[str, Any]]:
        """Collect ad-user match outcome data."""
        logger.info("Collecting ad-user matches...")
        return []


# =============================================================================
# EVALUATOR
# =============================================================================

class ModelEvaluator:
    """Evaluates fine-tuned embedding models."""
    
    def __init__(self, model_path: str):
        self.model_path = model_path
        self._model = None
    
    def _load_model(self):
        """Load the model for evaluation."""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_path)
    
    def evaluate_similarity_correlation(
        self,
        test_pairs: List[Dict[str, Any]],
    ) -> float:
        """
        Evaluate correlation between model similarity and ground truth.
        
        Returns Spearman correlation coefficient.
        """
        import numpy as np
        
        self._load_model()
        
        if not test_pairs:
            return 0.0
        
        predicted_similarities = []
        ground_truth = []
        
        for pair in test_pairs:
            emb_a = self._model.encode(pair["text_a"])
            emb_b = self._model.encode(pair["text_b"])
            
            # Cosine similarity
            similarity = np.dot(emb_a, emb_b) / (
                np.linalg.norm(emb_a) * np.linalg.norm(emb_b)
            )
            
            predicted_similarities.append(similarity)
            ground_truth.append(pair["label"])
        
        # Spearman correlation
        from scipy.stats import spearmanr
        correlation, _ = spearmanr(predicted_similarities, ground_truth)
        
        return correlation if not np.isnan(correlation) else 0.0
    
    def evaluate_triplet_accuracy(
        self,
        test_triplets: List[Dict[str, Any]],
    ) -> float:
        """
        Evaluate triplet accuracy (anchor closer to positive than negative).
        """
        import numpy as np
        
        self._load_model()
        
        if not test_triplets:
            return 0.0
        
        correct = 0
        total = 0
        
        for triplet in test_triplets:
            anchor = self._model.encode(triplet["anchor"])
            positive = self._model.encode(triplet["positive"])
            negative = self._model.encode(triplet["negative"])
            
            # Distances (lower = more similar for cosine)
            pos_sim = np.dot(anchor, positive) / (
                np.linalg.norm(anchor) * np.linalg.norm(positive)
            )
            neg_sim = np.dot(anchor, negative) / (
                np.linalg.norm(anchor) * np.linalg.norm(negative)
            )
            
            if pos_sim > neg_sim:
                correct += 1
            total += 1
        
        return correct / total if total > 0 else 0.0
    
    def evaluate_psychological_clustering(
        self,
        profiles: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        """
        Evaluate clustering of psychological profiles.
        
        Measures:
        - Within-trait similarity (same high/low should cluster)
        - Between-trait separation (different levels should separate)
        """
        import numpy as np
        
        self._load_model()
        
        if not profiles:
            return {}
        
        results = {}
        
        for trait in ["openness", "conscientiousness", "extraversion",
                      "agreeableness", "neuroticism"]:
            high_profiles = [
                p for p in profiles
                if p.get("big_five", {}).get(trait, 0.5) > 0.7
            ]
            low_profiles = [
                p for p in profiles
                if p.get("big_five", {}).get(trait, 0.5) < 0.3
            ]
            
            if len(high_profiles) < 2 or len(low_profiles) < 2:
                continue
            
            # Embed profiles
            high_embeddings = [
                self._model.encode(self._profile_to_text(p))
                for p in high_profiles[:10]
            ]
            low_embeddings = [
                self._model.encode(self._profile_to_text(p))
                for p in low_profiles[:10]
            ]
            
            # Within-group similarity
            within_high = self._avg_pairwise_similarity(high_embeddings)
            within_low = self._avg_pairwise_similarity(low_embeddings)
            
            # Between-group similarity
            between = self._avg_cross_similarity(high_embeddings, low_embeddings)
            
            # Separation ratio (higher is better)
            avg_within = (within_high + within_low) / 2
            separation = avg_within / (between + 0.001)
            
            results[trait] = {
                "within_high": within_high,
                "within_low": within_low,
                "between": between,
                "separation_ratio": separation,
            }
        
        return results
    
    def _avg_pairwise_similarity(self, embeddings: List) -> float:
        """Compute average pairwise similarity."""
        import numpy as np
        
        if len(embeddings) < 2:
            return 0.0
        
        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = np.dot(embeddings[i], embeddings[j]) / (
                    np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j])
                )
                similarities.append(sim)
        
        return np.mean(similarities) if similarities else 0.0
    
    def _avg_cross_similarity(self, group_a: List, group_b: List) -> float:
        """Compute average cross-group similarity."""
        import numpy as np
        
        similarities = []
        for a in group_a:
            for b in group_b:
                sim = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
                similarities.append(sim)
        
        return np.mean(similarities) if similarities else 0.0
    
    def _profile_to_text(self, profile: Dict[str, Any]) -> str:
        """Convert profile to text for embedding."""
        parts = []
        big_five = profile.get("big_five", {})
        for trait, value in big_five.items():
            if value > 0.7:
                parts.append(f"high {trait}")
            elif value < 0.3:
                parts.append(f"low {trait}")
        return f"User with {', '.join(parts)}" if parts else "User profile"


# =============================================================================
# FINE-TUNING PIPELINE
# =============================================================================

class FineTuningPipeline:
    """
    End-to-end pipeline for embedding model fine-tuning.
    
    Usage:
        pipeline = FineTuningPipeline(config)
        status = await pipeline.run()
        print(f"Model saved to: {status.model_path}")
    """
    
    def __init__(
        self,
        config: PipelineConfig,
        cache: Optional[ADAMRedisCache] = None,
    ):
        self.config = config
        self.cache = cache
        self.status = PipelineStatus()
        
        self.collector = DataCollector(cache)
        self.dataset_builder = None
        self.trainer = None
        self.evaluator = None
    
    async def run(
        self,
        progress_callback: Optional[Callable] = None,
    ) -> PipelineStatus:
        """
        Run the complete fine-tuning pipeline.
        
        Args:
            progress_callback: Called with status updates
            
        Returns:
            Final pipeline status
        """
        logger.info(f"Starting fine-tuning pipeline: {self.config.name}")
        
        try:
            # Stage 1: Data Collection
            await self._run_data_collection(progress_callback)
            
            # Stage 2: Dataset Creation
            await self._run_dataset_creation(progress_callback)
            
            # Stage 3: Training
            await self._run_training(progress_callback)
            
            # Stage 4: Evaluation
            await self._run_evaluation(progress_callback)
            
            # Stage 5: Deployment
            await self._run_deployment(progress_callback)
            
            # Complete
            self.status.stage = PipelineStage.COMPLETED
            self.status.completed_at = datetime.now(timezone.utc)
            self.status.progress_percent = 100.0
            
            PIPELINE_RUNS.labels(status="success").inc()
            logger.info(f"Pipeline completed successfully: {self.status.model_path}")
            
        except Exception as e:
            self.status.stage = PipelineStage.FAILED
            self.status.error = str(e)
            PIPELINE_RUNS.labels(status="failed").inc()
            logger.error(f"Pipeline failed: {e}")
            raise
        
        return self.status
    
    async def _run_data_collection(
        self,
        callback: Optional[Callable],
    ) -> None:
        """Run data collection stage."""
        self.status.stage = PipelineStage.DATA_COLLECTION
        self.status.progress_percent = 10.0
        PIPELINE_STAGE.labels(run_id=self.status.run_id).set(1)
        
        logger.info("Stage 1: Data Collection")
        
        # Collect data
        self._conversion_outcomes = await self.collector.collect_conversion_outcomes()
        self._mechanism_effectiveness = await self.collector.collect_mechanism_effectiveness()
        self._psychological_profiles = await self.collector.collect_psychological_profiles()
        self._ad_user_matches = await self.collector.collect_ad_user_matches()
        
        if callback:
            callback(self.status)
    
    async def _run_dataset_creation(
        self,
        callback: Optional[Callable],
    ) -> None:
        """Run dataset creation stage."""
        self.status.stage = PipelineStage.DATASET_CREATION
        self.status.progress_percent = 25.0
        PIPELINE_STAGE.labels(run_id=self.status.run_id).set(2)
        
        logger.info("Stage 2: Dataset Creation")
        
        # Initialize builder
        self.dataset_builder = DatasetBuilder(
            dataset_name=self.config.name,
            min_confidence=0.6,
        )
        
        # Add real data
        added = 0
        added += self.dataset_builder.add_from_conversion_outcomes(
            self._conversion_outcomes
        )
        added += self.dataset_builder.add_from_mechanism_effectiveness(
            self._mechanism_effectiveness
        )
        added += self.dataset_builder.add_from_psychological_profiles(
            self._psychological_profiles
        )
        added += self.dataset_builder.add_from_ad_user_matches(
            self._ad_user_matches
        )
        
        logger.info(f"Added {added} samples from real data")
        
        # Add synthetic data if enabled
        if self.config.include_synthetic:
            synth_count = self.config.synthetic_samples
            added += self.dataset_builder.add_synthetic_personality_pairs(
                count=int(synth_count * 0.7)
            )
            added += self.dataset_builder.add_synthetic_regulatory_focus_pairs(
                count=int(synth_count * 0.3)
            )
            logger.info(f"Added {synth_count} synthetic samples")
        
        # Build dataset
        self._dataset = self.dataset_builder.build()
        
        # Split
        self._train_dataset, self._val_dataset, self._test_dataset = (
            self._dataset.split(
                train_ratio=self.config.train_ratio,
                val_ratio=self.config.val_ratio,
                test_ratio=self.config.test_ratio,
            )
        )
        
        self.status.dataset_stats = self._dataset.compute_statistics()
        
        logger.info(f"Dataset created: {self._dataset.total_samples} total samples")
        
        if callback:
            callback(self.status)
    
    async def _run_training(
        self,
        callback: Optional[Callable],
    ) -> None:
        """Run training stage."""
        self.status.stage = PipelineStage.TRAINING
        self.status.progress_percent = 40.0
        PIPELINE_STAGE.labels(run_id=self.status.run_id).set(3)
        
        logger.info("Stage 3: Training")
        
        # Initialize trainer
        self.trainer = EmbeddingTrainer(
            config=self.config.training_config,
            model_name=self.config.name,
        )
        
        # Train
        def training_callback(metrics):
            self.status.progress_percent = 40.0 + (
                min(metrics.step / max(metrics.total_steps, 1), 1.0) * 30.0
            )
            if callback:
                callback(self.status)
        
        metrics = self.trainer.train(
            train_dataset=self._train_dataset,
            val_dataset=self._val_dataset,
            callback=training_callback,
        )
        
        self.status.training_metrics = metrics
        
        logger.info(f"Training completed: loss={metrics.train_loss:.4f}")
        
        if callback:
            callback(self.status)
    
    async def _run_evaluation(
        self,
        callback: Optional[Callable],
    ) -> None:
        """Run evaluation stage."""
        self.status.stage = PipelineStage.EVALUATION
        self.status.progress_percent = 75.0
        PIPELINE_STAGE.labels(run_id=self.status.run_id).set(4)
        
        logger.info("Stage 4: Evaluation")
        
        # Get model path
        model_path = self.status.training_metrics.best_checkpoint_path
        if not model_path:
            model_path = os.path.join(
                self.config.training_config.checkpoint_dir,
                f"{self.config.name}_final",
            )
        
        # Initialize evaluator
        self.evaluator = ModelEvaluator(model_path)
        
        # Evaluate on test set
        test_pairs = [
            {"text_a": p.text_a, "text_b": p.text_b, "label": p.label}
            for p in self._test_dataset.contrastive_pairs
        ]
        
        test_triplets = [
            {"anchor": t.anchor, "positive": t.positive, "negative": t.negative}
            for t in self._test_dataset.triplets
        ]
        
        similarity_correlation = self.evaluator.evaluate_similarity_correlation(
            test_pairs
        )
        triplet_accuracy = self.evaluator.evaluate_triplet_accuracy(test_triplets)
        
        self.status.evaluation_results = {
            "similarity_correlation": similarity_correlation,
            "triplet_accuracy": triplet_accuracy,
            "test_samples": len(test_pairs) + len(test_triplets),
        }
        
        logger.info(
            f"Evaluation: correlation={similarity_correlation:.4f}, "
            f"triplet_acc={triplet_accuracy:.4f}"
        )
        
        # Check quality thresholds
        if similarity_correlation < self.config.min_similarity_correlation:
            logger.warning(
                f"Model below quality threshold: "
                f"{similarity_correlation:.4f} < {self.config.min_similarity_correlation}"
            )
        
        if callback:
            callback(self.status)
    
    async def _run_deployment(
        self,
        callback: Optional[Callable],
    ) -> None:
        """Run deployment stage."""
        self.status.stage = PipelineStage.DEPLOYMENT
        self.status.progress_percent = 90.0
        PIPELINE_STAGE.labels(run_id=self.status.run_id).set(5)
        
        logger.info("Stage 5: Deployment")
        
        # Create output directory
        output_dir = Path(self.config.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate version
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        version = f"{self.config.version}_{timestamp}"
        
        # Final model path
        model_path = output_dir / f"{self.config.name}_{version}"
        
        # Copy best checkpoint to final location
        best_checkpoint = self.status.training_metrics.best_checkpoint_path
        if best_checkpoint and Path(best_checkpoint).exists():
            shutil.copytree(best_checkpoint, model_path)
        else:
            # Use final checkpoint
            final_path = Path(self.config.training_config.checkpoint_dir) / (
                f"{self.config.name}_final"
            )
            if final_path.exists():
                shutil.copytree(final_path, model_path)
        
        # Save metadata
        metadata = {
            "name": self.config.name,
            "version": version,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "training_metrics": self.status.training_metrics.model_dump() if self.status.training_metrics else {},
            "evaluation_results": self.status.evaluation_results,
            "dataset_stats": self.status.dataset_stats,
            "config": self.config.model_dump(),
        }
        
        import json
        metadata_path = model_path / "adam_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)
        
        self.status.model_path = str(model_path)
        self.status.model_version = version
        
        # Cleanup checkpoints if not keeping
        if not self.config.keep_checkpoints:
            checkpoint_dir = Path(self.config.training_config.checkpoint_dir)
            if checkpoint_dir.exists():
                shutil.rmtree(checkpoint_dir)
        
        logger.info(f"Model deployed: {model_path}")
        
        if callback:
            callback(self.status)
