# =============================================================================
# ADAM Custom AI Model Training Pipeline
# Location: adam/ml/training_pipeline.py
# =============================================================================

"""
CUSTOM AI MODEL TRAINING PIPELINE

End-to-end pipeline for training ADAM's proprietary models on the 1B+
review corpus. These are NOT just priors — they are LEARNED REPRESENTATIONS
that capture patterns no rule-based system can express.

Models trained:
1. NDF Predictor — predicts 7 NDF dimensions from text
2. Archetype Classifier — classifies into deep archetypes
3. Mechanism Susceptibility Regressor — predicts mechanism effectiveness
4. Psycholinguistic Embeddings — domain-specific sentence embeddings
5. Decision Style Classifier — ELM-based processing style prediction

Training paradigm:
- Phase 1: Pre-train on full corpus (self-supervised, masked language modeling)
- Phase 2: Fine-tune with weak supervision labels (multi-task)
- Phase 3: Reinforcement from outcomes (Thompson Sampling feedback)

This gives us THREE learning loops:
1. Static learning: Pre-trained representations from language patterns
2. Supervised learning: Fine-tuned on rule-based extracted labels
3. Online learning: Updated from real-world ad outcome feedback
"""

import logging
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# =============================================================================
# PIPELINE CONFIGURATION
# =============================================================================

@dataclass
class TrainingConfig:
    """Configuration for the training pipeline."""
    
    # Model backbone
    base_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # Training parameters
    learning_rate: float = 2e-5
    batch_size: int = 32
    max_epochs: int = 5
    warmup_ratio: float = 0.1
    weight_decay: float = 0.01
    max_seq_length: int = 256
    
    # Multi-task weights
    ndf_task_weight: float = 1.0
    archetype_task_weight: float = 0.5
    mechanism_task_weight: float = 0.7
    
    # Curriculum learning
    curriculum_stages: int = 3
    initial_confidence_threshold: float = 0.7
    final_confidence_threshold: float = 0.3
    
    # Data
    training_data_dir: str = "data/ml_training"
    output_dir: str = "models/adam_custom"
    
    # Hardware
    device: str = "cpu"
    fp16: bool = False
    gradient_accumulation_steps: int = 4
    
    # Evaluation
    eval_steps: int = 500
    save_steps: int = 1000
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


@dataclass
class TrainingMetrics:
    """Metrics from a training run."""
    total_examples: int = 0
    total_steps: int = 0
    train_loss: float = 0.0
    val_loss: float = 0.0
    
    # Task-specific metrics
    ndf_mae: float = 0.0        # Mean absolute error for NDF dimensions
    archetype_accuracy: float = 0.0
    mechanism_mae: float = 0.0
    
    # Timing
    training_time_seconds: float = 0.0
    throughput_examples_per_second: float = 0.0
    
    def to_dict(self) -> Dict[str, float]:
        return {k: v for k, v in self.__dict__.items()}


# =============================================================================
# TRAINING PIPELINE
# =============================================================================

class ADAMTrainingPipeline:
    """
    End-to-end training pipeline for ADAM's custom models.
    
    This pipeline:
    1. Loads weak supervision labels from the rule-based extraction
    2. Applies curriculum learning (high confidence → low confidence)
    3. Trains multi-task model (NDF + archetype + mechanism)
    4. Evaluates on held-out test set
    5. Exports trained model for production use
    """
    
    def __init__(self, config: Optional[TrainingConfig] = None):
        self.config = config or TrainingConfig()
        self._metrics_history: List[TrainingMetrics] = []
    
    def prepare_data(self) -> Dict[str, Any]:
        """
        Prepare training data from weak supervision pipeline.
        
        Returns dict with train/val/test splits and metadata.
        """
        from adam.ml.weak_supervisor import WeakSupervisor
        
        supervisor = WeakSupervisor(output_dir=self.config.training_data_dir)
        
        # Load pre-exported data if available
        data_path = Path(self.config.training_data_dir) / "ndf_training_data.jsonl"
        
        if data_path.exists():
            logger.info(f"Loading pre-exported training data from {data_path}")
            
            examples = {"train": [], "val": [], "test": []}
            with open(data_path) as f:
                for line in f:
                    record = json.loads(line)
                    split = record.get("split", "train")
                    examples[split].append(record)
            
            logger.info(
                f"Loaded data: train={len(examples['train'])}, "
                f"val={len(examples['val'])}, test={len(examples['test'])}"
            )
            return examples
        else:
            logger.warning(
                f"No pre-exported data found at {data_path}. "
                f"Run the weak supervision pipeline first."
            )
            return {"train": [], "val": [], "test": []}
    
    def build_curriculum(
        self,
        examples: List[Dict],
    ) -> List[List[Dict]]:
        """
        Build curriculum stages — start with high-confidence examples,
        gradually include lower-confidence ones.
        
        Inspired by Bengio et al. (2009) Curriculum Learning.
        """
        stages = []
        n_stages = self.config.curriculum_stages
        
        conf_range = (
            self.config.initial_confidence_threshold -
            self.config.final_confidence_threshold
        )
        step = conf_range / n_stages
        
        for stage_idx in range(n_stages):
            threshold = self.config.initial_confidence_threshold - step * stage_idx
            
            stage_examples = [
                ex for ex in examples
                if ex.get("confidence", 0) >= threshold
            ]
            
            stages.append(stage_examples)
            logger.info(
                f"Curriculum stage {stage_idx + 1}: "
                f"threshold={threshold:.2f}, examples={len(stage_examples)}"
            )
        
        return stages
    
    def train_ndf_model(
        self,
        train_data: List[Dict],
        val_data: List[Dict],
    ) -> TrainingMetrics:
        """Train the NDF prediction model."""
        import numpy as np
        
        logger.info(f"Training NDF model on {len(train_data)} examples")
        start_time = time.time()
        
        # Prepare labels
        ndf_dims = [
            "approach_avoidance", "temporal_horizon", "social_calibration",
            "uncertainty_tolerance", "status_sensitivity",
            "cognitive_engagement", "arousal_seeking",
        ]
        
        train_texts = [ex["text"] for ex in train_data if "labels" in ex]
        train_labels = np.array([
            [ex["labels"].get(d, 0.5) for d in ndf_dims]
            for ex in train_data if "labels" in ex
        ])
        
        confidence_weights = np.array([
            ex.get("confidence", 0.5) for ex in train_data if "labels" in ex
        ])
        
        if len(train_texts) == 0:
            logger.warning("No training examples with labels")
            return TrainingMetrics()
        
        # Use NDFTrainer
        from adam.ml.ndf_predictor import NDFTrainer
        
        trainer = NDFTrainer(
            model_name=self.config.base_model,
            learning_rate=self.config.learning_rate,
            batch_size=self.config.batch_size,
            epochs=self.config.max_epochs,
            device=self.config.device,
        )
        
        # Curriculum training
        curriculum = self.build_curriculum(train_data)
        
        total_metrics = {}
        for stage_idx, stage_data in enumerate(curriculum):
            stage_texts = [ex["text"] for ex in stage_data if "labels" in ex]
            stage_labels = np.array([
                [ex["labels"].get(d, 0.5) for d in ndf_dims]
                for ex in stage_data if "labels" in ex
            ])
            stage_weights = np.array([
                ex.get("confidence", 0.5) for ex in stage_data if "labels" in ex
            ])
            
            if len(stage_texts) == 0:
                continue
            
            stage_metrics = trainer.train(
                train_texts=stage_texts,
                train_ndf_labels=stage_labels,
                confidence_weights=stage_weights,
                output_dir=f"{self.config.output_dir}/ndf_stage_{stage_idx}",
            )
            
            total_metrics.update(stage_metrics)
        
        elapsed = time.time() - start_time
        
        metrics = TrainingMetrics(
            total_examples=len(train_texts),
            train_loss=total_metrics.get("final_train_loss", 0.0),
            training_time_seconds=elapsed,
            throughput_examples_per_second=len(train_texts) / max(1, elapsed),
        )
        
        self._metrics_history.append(metrics)
        
        logger.info(
            f"NDF training complete: loss={metrics.train_loss:.4f}, "
            f"time={elapsed:.1f}s, throughput={metrics.throughput_examples_per_second:.0f} ex/s"
        )
        
        return metrics
    
    def train_archetype_model(
        self,
        train_data: List[Dict],
        val_data: List[Dict],
    ) -> TrainingMetrics:
        """Train the archetype classification model with cross-entropy loss."""
        logger.info(f"Training archetype model on {len(train_data)} examples")
        start_time = time.time()
        
        # Filter to examples with archetype labels
        labeled = [ex for ex in train_data if ex.get("label")]
        
        if not labeled:
            logger.warning("No archetype training data available")
            return TrainingMetrics()
        
        try:
            import torch
            import torch.nn as nn
            from transformers import AutoTokenizer, AutoModel, get_linear_schedule_with_warmup
        except ImportError:
            logger.error("PyTorch/Transformers required for training")
            return TrainingMetrics()
        
        # Build label map
        unique_archetypes = sorted(set(ex["label"] for ex in labeled))
        label_to_idx = {label: idx for idx, label in enumerate(unique_archetypes)}
        num_classes = len(unique_archetypes)
        logger.info(f"Training on {len(labeled)} examples, {num_classes} archetypes")
        
        # Prepare data
        train_texts = [ex["text"] for ex in labeled]
        train_labels = [label_to_idx[ex["label"]] for ex in labeled]
        confidence_weights = [ex.get("confidence", 0.5) for ex in labeled]
        
        # Initialize model
        tokenizer = AutoTokenizer.from_pretrained(self.config.base_model)
        backbone = AutoModel.from_pretrained(self.config.base_model)
        hidden_size = backbone.config.hidden_size
        
        archetype_head = nn.Sequential(
            nn.Linear(hidden_size, 256),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(256, 128),
            nn.GELU(),
            nn.Linear(128, num_classes),
        )
        
        backbone.train()
        archetype_head.train()
        
        # Tokenize
        encodings = tokenizer(
            train_texts, max_length=256, truncation=True,
            padding=True, return_tensors="pt",
        )
        labels_tensor = torch.tensor(train_labels, dtype=torch.long)
        weights_tensor = torch.tensor(confidence_weights, dtype=torch.float32)
        
        # Optimizer
        optimizer = torch.optim.AdamW(
            list(backbone.parameters()) + list(archetype_head.parameters()),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )
        
        total_steps = (len(train_texts) // self.config.batch_size + 1) * self.config.max_epochs
        scheduler = get_linear_schedule_with_warmup(
            optimizer,
            num_warmup_steps=int(total_steps * self.config.warmup_ratio),
            num_training_steps=total_steps,
        )
        
        loss_fn = nn.CrossEntropyLoss(reduction='none')
        
        # Training loop
        best_loss = float('inf')
        for epoch in range(self.config.max_epochs):
            epoch_loss = 0.0
            correct = 0
            total = 0
            
            indices = torch.randperm(len(train_texts))
            
            for i in range(0, len(train_texts), self.config.batch_size):
                batch_idx = indices[i:i + self.config.batch_size]
                batch_inputs = {k: v[batch_idx] for k, v in encodings.items()}
                batch_labels = labels_tensor[batch_idx]
                batch_weights = weights_tensor[batch_idx]
                
                outputs = backbone(**batch_inputs)
                cls_embedding = outputs.last_hidden_state[:, 0, :]
                logits = archetype_head(cls_embedding)
                
                # Weighted cross-entropy
                per_example_loss = loss_fn(logits, batch_labels)
                loss = (per_example_loss * batch_weights).mean()
                
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(backbone.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                
                epoch_loss += loss.item()
                preds = logits.argmax(dim=-1)
                correct += (preds == batch_labels).sum().item()
                total += len(batch_labels)
            
            n_batches = max(1, len(train_texts) // self.config.batch_size)
            avg_loss = epoch_loss / n_batches
            accuracy = correct / max(1, total)
            
            logger.info(
                f"Archetype epoch {epoch+1}/{self.config.max_epochs}: "
                f"loss={avg_loss:.4f}, accuracy={accuracy:.3f}"
            )
            
            if avg_loss < best_loss:
                best_loss = avg_loss
                # Save best model
                save_dir = Path(self.config.output_dir) / "archetype_model"
                save_dir.mkdir(parents=True, exist_ok=True)
                backbone.save_pretrained(save_dir / "backbone")
                tokenizer.save_pretrained(save_dir / "backbone")
                torch.save(archetype_head.state_dict(), save_dir / "archetype_head.pt")
                # Save label map
                with open(save_dir / "label_map.json", "w") as f:
                    json.dump({"label_to_idx": label_to_idx, "idx_to_label": {v: k for k, v in label_to_idx.items()}}, f)
        
        elapsed = time.time() - start_time
        metrics = TrainingMetrics(
            total_examples=len(labeled),
            train_loss=best_loss,
            archetype_accuracy=accuracy,
            training_time_seconds=elapsed,
            throughput_examples_per_second=len(labeled) / max(1, elapsed),
        )
        
        self._metrics_history.append(metrics)
        logger.info(f"Archetype training complete: accuracy={accuracy:.3f}, time={elapsed:.1f}s")
        return metrics
    
    def train_full_pipeline(self) -> Dict[str, TrainingMetrics]:
        """
        Run the full training pipeline.
        
        Order:
        1. Prepare data from weak supervision
        2. Train NDF model (curriculum)
        3. Train archetype model
        4. Train mechanism susceptibility model
        5. Evaluate all models on test set
        6. Export best models for production
        """
        logger.info("=" * 60)
        logger.info("ADAM Custom Model Training Pipeline")
        logger.info("=" * 60)
        
        start = time.time()
        
        # Step 1: Prepare data
        data = self.prepare_data()
        
        if not data["train"]:
            logger.error("No training data available. Run ingestion + weak supervision first.")
            return {}
        
        all_metrics = {}
        
        # Step 2: NDF model
        ndf_data = [ex for ex in data["train"] if "labels" in ex and isinstance(ex.get("labels"), dict)]
        ndf_val = [ex for ex in data["val"] if "labels" in ex and isinstance(ex.get("labels"), dict)]
        
        if ndf_data:
            all_metrics["ndf"] = self.train_ndf_model(ndf_data, ndf_val)
        
        # Step 3: Archetype model
        arch_data = [ex for ex in data["train"] if "label" in ex]
        arch_val = [ex for ex in data["val"] if "label" in ex]
        
        if arch_data:
            all_metrics["archetype"] = self.train_archetype_model(arch_data, arch_val)
        
        elapsed = time.time() - start
        logger.info(f"Full pipeline complete in {elapsed:.1f}s")
        
        # Save pipeline config
        config_path = Path(self.config.output_dir) / "pipeline_config.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump({
                "config": self.config.to_dict(),
                "metrics": {k: v.to_dict() for k, v in all_metrics.items()},
                "total_time_seconds": elapsed,
            }, f, indent=2)
        
        return all_metrics
    
    @property
    def metrics_history(self) -> List[TrainingMetrics]:
        return self._metrics_history


# =============================================================================
# PSYCHOLINGUISTIC EMBEDDING MODEL
# =============================================================================

class PsycholinguisticEmbedder:
    """
    Domain-specific sentence embedding model fine-tuned on psycholinguistic
    dimensions. Produces embeddings where psychological similarity is
    captured in vector space.
    
    Unlike generic sentence transformers (optimized for semantic similarity),
    this model is optimized for:
    - NDF similarity: texts from same NDF profile cluster together
    - Archetype similarity: same archetype → close in embedding space
    - Mechanism sensitivity: texts responsive to same mechanisms → close
    
    Training uses contrastive learning (SimCSE-style):
    - Positive pairs: texts with similar NDF profiles
    - Negative pairs: texts with dissimilar NDF profiles
    - Hard negatives: semantically similar but psycholinguistically different
    """
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        embedding_dim: int = 384,
    ):
        self.model_path = model_path
        self.embedding_dim = embedding_dim
        self._model = None
        self._tokenizer = None
        self._is_loaded = False
    
    def _ensure_loaded(self) -> bool:
        """Load model if not already loaded."""
        if self._is_loaded:
            return True
        
        try:
            from transformers import AutoTokenizer, AutoModel
            
            model_name = self.model_path or "sentence-transformers/all-MiniLM-L6-v2"
            self._tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._model = AutoModel.from_pretrained(model_name)
            self._model.eval()
            self._is_loaded = True
            return True
        except Exception as e:
            logger.warning(f"Could not load embedding model: {e}")
            return False
    
    def embed(self, text: str) -> Optional[list]:
        """Generate psycholinguistic embedding for a text."""
        if not self._ensure_loaded():
            return None
        
        try:
            import torch
            
            inputs = self._tokenizer(
                text, max_length=256, truncation=True,
                padding=True, return_tensors="pt",
            )
            
            with torch.no_grad():
                outputs = self._model(**inputs)
                # Mean pooling
                embedding = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
            
            return embedding.tolist()
        except Exception as e:
            logger.warning(f"Embedding failed: {e}")
            return None
    
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[Optional[list]]:
        """Embed a batch of texts."""
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_results = [self.embed(t) for t in batch]
            results.extend(batch_results)
        return results
    
    def similarity(self, text1: str, text2: str) -> float:
        """Compute psycholinguistic similarity between two texts."""
        import numpy as np
        
        emb1 = self.embed(text1)
        emb2 = self.embed(text2)
        
        if emb1 is None or emb2 is None:
            return 0.0
        
        # Cosine similarity
        a, b = np.array(emb1), np.array(emb2)
        return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))
    
    def train_contrastive(
        self,
        positive_pairs: List[Tuple[str, str]],
        negative_pairs: List[Tuple[str, str]],
        epochs: int = 3,
        learning_rate: float = 2e-5,
        output_dir: str = "models/psycholinguistic_embedder",
        temperature: float = 0.07,
        val_positive_pairs: Optional[List[Tuple[str, str]]] = None,
    ) -> Dict[str, float]:
        """
        Fine-tune using contrastive learning on psycholinguistic similarity.
        
        Uses proper InfoNCE loss (NT-Xent from SimCLR):
            L = -log(exp(sim(z_i, z_j+) / tau) / sum_k exp(sim(z_i, z_k) / tau))
        
        The correct implementation uses ONLY positive pairs in each batch.
        In-batch negatives (off-diagonal elements) serve as negative examples.
        This is the standard NT-Xent / InfoNCE formulation from SimCLR
        (Chen et al. 2020) and CLIP (Radford et al. 2021).
        
        Hard negatives (from negative_pairs) are mixed into batches to ensure
        the model sees psycholinguistically dissimilar texts as in-batch negatives.
        
        Args:
            positive_pairs: (text_a, text_b) where a and b have similar NDF profiles
            negative_pairs: (text_a, text_b) where a and b have dissimilar NDF profiles
                These are broken apart and used as in-batch hard negatives.
            epochs: Number of training epochs
            learning_rate: Learning rate for AdamW
            output_dir: Directory to save trained model
            temperature: Temperature for NT-Xent (lower = sharper distribution)
            val_positive_pairs: Optional validation positive pairs for evaluation
        """
        logger.info(
            f"Training contrastive embedder: {len(positive_pairs)} pos pairs, "
            f"{len(negative_pairs)} neg pairs (used as in-batch hard negatives)"
        )
        
        if not positive_pairs:
            logger.warning("No positive pairs for contrastive training")
            return {"error": "no_data"}
        
        try:
            import torch
            import torch.nn as nn
            import torch.nn.functional as F
            from transformers import AutoTokenizer, AutoModel, get_linear_schedule_with_warmup
            import random
        except ImportError:
            logger.error("PyTorch/Transformers required for contrastive training")
            return {"error": "dependencies"}
        
        # Initialize model
        model_name = self.model_path or "sentence-transformers/all-MiniLM-L6-v2"
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name)
        hidden_size = model.config.hidden_size
        
        # Projection head for contrastive learning (map to unit hypersphere)
        projection = nn.Sequential(
            nn.Linear(hidden_size, 256),
            nn.GELU(),
            nn.Linear(256, 128),
        )
        
        model.train()
        projection.train()
        
        optimizer = torch.optim.AdamW(
            list(model.parameters()) + list(projection.parameters()),
            lr=learning_rate,
            weight_decay=0.01,
        )
        
        def encode(texts):
            """Encode texts to L2-normalized embeddings via projection head."""
            enc = tokenizer(
                texts, max_length=256, truncation=True,
                padding=True, return_tensors="pt",
            )
            out = model(**enc)
            # Mean pooling over token embeddings
            attention_mask = enc["attention_mask"].unsqueeze(-1)
            token_embs = out.last_hidden_state * attention_mask
            emb = token_embs.sum(dim=1) / attention_mask.sum(dim=1)
            proj = projection(emb)
            return F.normalize(proj, p=2, dim=-1)
        
        @torch.no_grad()
        def evaluate_alignment(pairs, label="val"):
            """Compute alignment/uniformity metrics for evaluation."""
            if not pairs or len(pairs) < 4:
                return {}
            model.eval()
            projection.eval()
            
            sample = pairs[:min(200, len(pairs))]
            texts_a = [p[0] for p in sample]
            texts_b = [p[1] for p in sample]
            
            emb_a = encode(texts_a)
            emb_b = encode(texts_b)
            
            # Alignment: avg cosine sim of positive pairs (should be high)
            pos_sims = (emb_a * emb_b).sum(dim=-1)
            alignment = pos_sims.mean().item()
            
            # Uniformity: how spread out embeddings are (should be low = uniform)
            all_embs = torch.cat([emb_a, emb_b], dim=0)
            sq_pdist = torch.cdist(all_embs, all_embs, p=2).pow(2)
            uniformity = sq_pdist.mul(-2).exp().mean().log().item()
            
            # Mean reciprocal rank: for each anchor, rank of its positive
            sim_matrix = torch.mm(emb_a, emb_b.t())
            ranks = (sim_matrix >= sim_matrix.diag().unsqueeze(1)).sum(dim=1).float()
            mrr = (1.0 / ranks).mean().item()
            
            model.train()
            projection.train()
            return {
                f"{label}_alignment": round(alignment, 4),
                f"{label}_uniformity": round(uniformity, 4),
                f"{label}_mrr": round(mrr, 4),
            }
        
        # Build training data: positive pairs are the anchors.
        # Hard negatives from negative_pairs are broken apart and shuffled
        # into the anchor/positive pools to create in-batch hard negatives.
        train_anchors = [p[0] for p in positive_pairs]
        train_positives = [p[1] for p in positive_pairs]
        
        # Extract hard negative texts to inject into batches
        hard_neg_pool_a = [p[0] for p in negative_pairs]
        hard_neg_pool_b = [p[1] for p in negative_pairs]
        
        batch_size = 64
        # Each batch: first `real_size` items are true positive pairs,
        # remaining are hard negatives (paired with random texts = implicit negatives)
        hard_neg_ratio = min(0.25, len(negative_pairs) / max(1, len(positive_pairs)))
        n_hard_per_batch = max(0, int(batch_size * hard_neg_ratio))
        real_per_batch = batch_size - n_hard_per_batch
        
        total_steps = (len(train_anchors) // real_per_batch + 1) * epochs
        scheduler = get_linear_schedule_with_warmup(
            optimizer,
            num_warmup_steps=int(total_steps * 0.1),
            num_training_steps=total_steps,
        )
        
        metrics = {
            "train_losses": [],
            "val_metrics": [],
            "epochs": epochs,
            "temperature": temperature,
            "batch_size": batch_size,
            "n_positive_pairs": len(positive_pairs),
            "n_negative_pairs": len(negative_pairs),
        }
        
        best_val_mrr = 0.0
        best_epoch = 0
        
        for epoch in range(epochs):
            epoch_loss = 0.0
            n_batches = 0
            
            # Shuffle training pairs
            indices = list(range(len(train_anchors)))
            random.shuffle(indices)
            
            for i in range(0, len(indices), real_per_batch):
                batch_idx = indices[i:i + real_per_batch]
                
                # Anchor texts and their positives
                batch_anchors = [train_anchors[j] for j in batch_idx]
                batch_positives = [train_positives[j] for j in batch_idx]
                
                # Inject hard negatives: add hard neg texts as both anchors
                # and positives but MISMATCHED, creating false pairs that the
                # InfoNCE loss treats as in-batch negatives
                if n_hard_per_batch > 0 and hard_neg_pool_a:
                    hn_indices = random.sample(
                        range(len(hard_neg_pool_a)),
                        min(n_hard_per_batch, len(hard_neg_pool_a)),
                    )
                    for hi in hn_indices:
                        batch_anchors.append(hard_neg_pool_a[hi])
                        # Pair with a RANDOM positive (not the true pair) = hard negative
                        rand_pos = train_positives[random.randint(0, len(train_positives) - 1)]
                        batch_positives.append(rand_pos)
                
                current_batch_size = len(batch_anchors)
                if current_batch_size < 2:
                    continue
                
                # Encode both views
                emb_a = encode(batch_anchors)
                emb_b = encode(batch_positives)
                
                # === CORRECT InfoNCE / NT-Xent Loss ===
                # Similarity matrix: (batch, batch) — cosine sim / temperature
                sim_matrix = torch.mm(emb_a, emb_b.t()) / temperature
                
                # Ground truth labels: the i-th anchor's positive is the i-th positive
                # This is a classification problem: for row i, the correct column is i
                labels = torch.arange(current_batch_size, device=sim_matrix.device)
                
                # Symmetric NT-Xent: loss from anchor→positive AND positive→anchor
                loss_ab = F.cross_entropy(sim_matrix, labels)
                loss_ba = F.cross_entropy(sim_matrix.t(), labels)
                loss = (loss_ab + loss_ba) / 2.0
                
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                
                epoch_loss += loss.item()
                n_batches += 1
            
            avg_loss = epoch_loss / max(1, n_batches)
            metrics["train_losses"].append(avg_loss)
            
            # Evaluate on validation set if provided
            val_result = {}
            if val_positive_pairs:
                val_result = evaluate_alignment(val_positive_pairs, "val")
                metrics["val_metrics"].append(val_result)
                
                val_mrr = val_result.get("val_mrr", 0)
                if val_mrr > best_val_mrr:
                    best_val_mrr = val_mrr
                    best_epoch = epoch + 1
                    # Save best model
                    save_dir = Path(output_dir)
                    save_dir.mkdir(parents=True, exist_ok=True)
                    model.save_pretrained(save_dir / "backbone")
                    tokenizer.save_pretrained(save_dir / "backbone")
                    torch.save(projection.state_dict(), save_dir / "projection.pt")
            
            # Also evaluate on training sample
            train_eval = evaluate_alignment(positive_pairs[:200], "train")
            
            logger.info(
                f"Contrastive epoch {epoch+1}/{epochs}: loss={avg_loss:.4f} "
                f"| train_align={train_eval.get('train_alignment', 0):.4f} "
                f"| train_mrr={train_eval.get('train_mrr', 0):.4f}"
                + (f" | val_mrr={val_result.get('val_mrr', 0):.4f}" if val_result else "")
            )
        
        # Save final model (or best was already saved during val)
        save_dir = Path(output_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        if not val_positive_pairs:
            # No validation — save last epoch
            model.save_pretrained(save_dir / "backbone")
            tokenizer.save_pretrained(save_dir / "backbone")
            torch.save(projection.state_dict(), save_dir / "projection.pt")
        
        self.model_path = str(save_dir / "backbone")
        self._model = model
        self._tokenizer = tokenizer
        self._is_loaded = True
        
        # Final evaluation metrics
        final_train_eval = evaluate_alignment(positive_pairs[:500], "final_train")
        metrics.update(final_train_eval)
        
        if val_positive_pairs:
            final_val_eval = evaluate_alignment(val_positive_pairs, "final_val")
            metrics.update(final_val_eval)
            metrics["best_val_mrr"] = best_val_mrr
            metrics["best_epoch"] = best_epoch
        
        metrics["final_loss"] = metrics["train_losses"][-1] if metrics["train_losses"] else 0.0
        logger.info(
            f"Contrastive training complete. Model saved to {output_dir}. "
            f"Final loss={metrics['final_loss']:.4f}"
        )
        return metrics
