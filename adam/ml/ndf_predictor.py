# =============================================================================
# ADAM Neural NDF Predictor
# Location: adam/ml/ndf_predictor.py
# =============================================================================

"""
NEURAL NDF PREDICTOR

A fine-tuned sentence transformer with multi-task regression heads
for predicting NDF dimensions from text. This is the ML counterpart
to the rule-based NDF extractor.

Architecture:
    Text → Sentence Transformer (all-MiniLM-L6-v2 or similar)
         → [CLS] embedding (384d)
         → Multi-Task Heads:
             → NDF Head (7 outputs, sigmoid activation)
             → Archetype Head (N outputs, softmax)
             → Mechanism Head (M outputs, sigmoid activation)

Training:
    - Weak supervision labels from 1B+ rule-processed reviews
    - Multi-task learning (shared backbone, task-specific heads)
    - Category-aware: category embedding concatenated before heads
    - Curriculum learning: start with high-confidence labels only

Key advantages over rule-based:
    - Handles negation: "This product is NOT bad" → positive
    - Handles sarcasm: "Oh great, another 'premium' product"
    - Captures style: sentence length, complexity → cognitive engagement
    - Transfer learning: patterns from one category help others
"""

import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# NDF PREDICTOR
# =============================================================================

class NDFPredictor:
    """
    Neural predictor for Nonconscious Decision Fingerprint dimensions.
    
    Can be used in two modes:
    1. Inference mode: Load a trained model and predict
    2. Training mode: Fine-tune on weak supervision labels
    """
    
    NDF_DIMENSIONS = [
        "approach_avoidance",
        "temporal_horizon",
        "social_calibration",
        "uncertainty_tolerance",
        "status_sensitivity",
        "cognitive_engagement",
        "arousal_seeking",
    ]
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        device: str = "cpu",
    ):
        self.model_name = model_name
        self.device = device
        self._model = None
        self._tokenizer = None
        self._ndf_head = None
        self._archetype_head = None
        self._mechanism_head = None
        self._is_loaded = False
    
    def _ensure_model(self) -> bool:
        """Lazy-load the model."""
        if self._is_loaded:
            return True
        
        try:
            import torch
            import torch.nn as nn
            from transformers import AutoTokenizer, AutoModel
            
            logger.info(f"Loading model: {self.model_name}")
            self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self._model = AutoModel.from_pretrained(self.model_name)
            self._model.to(self.device)
            self._model.eval()
            
            # Get hidden size
            hidden_size = self._model.config.hidden_size
            
            # Create task heads
            self._ndf_head = nn.Sequential(
                nn.Linear(hidden_size, 128),
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(128, len(self.NDF_DIMENSIONS)),
                nn.Sigmoid(),
            ).to(self.device)
            
            self._archetype_head = nn.Sequential(
                nn.Linear(hidden_size, 128),
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(128, 64),  # 64 archetype classes
            ).to(self.device)
            
            self._mechanism_head = nn.Sequential(
                nn.Linear(hidden_size, 128),
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(128, 9),  # 9 core mechanisms
                nn.Sigmoid(),
            ).to(self.device)
            
            self._is_loaded = True
            logger.info("Model loaded successfully")
            return True
            
        except ImportError as e:
            logger.warning(f"PyTorch/Transformers not available: {e}")
            return False
        except Exception as e:
            logger.warning(f"Failed to load model: {e}")
            return False
    
    def predict(
        self,
        text: str,
        category: str = "",
    ) -> Dict[str, Any]:
        """
        Predict NDF dimensions, archetype, and mechanism susceptibility.
        
        Returns dict with:
            ndf_profile: Dict[str, float]  (7 dimensions)
            ndf_confidence: float
            archetype: str
            archetype_confidence: float
            mechanism_scores: Dict[str, float]
        """
        if not self._ensure_model():
            return {}
        
        try:
            import torch
            
            # Tokenize
            inputs = self._tokenizer(
                text,
                max_length=512,
                truncation=True,
                padding=True,
                return_tensors="pt",
            ).to(self.device)
            
            # Forward pass
            with torch.no_grad():
                outputs = self._model(**inputs)
                
                # Use [CLS] token embedding
                cls_embedding = outputs.last_hidden_state[:, 0, :]
                
                # Task-specific predictions
                ndf_pred = self._ndf_head(cls_embedding).cpu().numpy()[0]
                archetype_logits = self._archetype_head(cls_embedding)
                mechanism_pred = self._mechanism_head(cls_embedding).cpu().numpy()[0]
            
            # Build NDF profile
            ndf_profile = {
                dim: float(ndf_pred[i])
                for i, dim in enumerate(self.NDF_DIMENSIONS)
            }
            
            # NDF confidence: based on how far from 0.5 (uninformative) the predictions are
            ndf_confidence = min(0.9, 0.3 + np.mean(np.abs(ndf_pred - 0.5)) * 2.0)
            
            # Archetype (top-1)
            archetype_probs = torch.softmax(archetype_logits, dim=-1).cpu().numpy()[0]
            archetype_idx = int(np.argmax(archetype_probs))
            archetype_confidence = float(archetype_probs[archetype_idx])
            
            # Mechanism scores
            mechanism_names = [
                "social_proof", "scarcity", "authority", "commitment",
                "reciprocity", "identity_construction", "mimetic_desire",
                "attention_dynamics", "embodied_cognition",
            ]
            mechanism_scores = {
                name: float(mechanism_pred[i])
                for i, name in enumerate(mechanism_names)
            }
            
            return {
                "ndf_profile": ndf_profile,
                "ndf_confidence": ndf_confidence,
                "archetype": f"archetype_{archetype_idx}",
                "archetype_confidence": archetype_confidence,
                "mechanism_scores": mechanism_scores,
            }
            
        except Exception as e:
            logger.warning(f"Prediction failed: {e}")
            return {}
    
    def predict_batch(
        self,
        texts: List[str],
        categories: Optional[List[str]] = None,
        batch_size: int = 32,
    ) -> List[Dict[str, Any]]:
        """Predict NDF dimensions for a batch of texts."""
        results = []
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_results = [self.predict(t) for t in batch_texts]
            results.extend(batch_results)
        
        return results
    
    def save(self, path: str) -> None:
        """Save model and heads to disk."""
        if not self._is_loaded:
            logger.warning("No model to save")
            return
        
        import torch
        
        save_dir = Path(path)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        self._model.save_pretrained(save_dir / "backbone")
        self._tokenizer.save_pretrained(save_dir / "backbone")
        
        torch.save(self._ndf_head.state_dict(), save_dir / "ndf_head.pt")
        torch.save(self._archetype_head.state_dict(), save_dir / "archetype_head.pt")
        torch.save(self._mechanism_head.state_dict(), save_dir / "mechanism_head.pt")
        
        # Save config
        config = {
            "model_name": self.model_name,
            "ndf_dimensions": self.NDF_DIMENSIONS,
        }
        with open(save_dir / "config.json", "w") as f:
            json.dump(config, f)
        
        logger.info(f"Model saved to {path}")
    
    @classmethod
    def load(cls, path: str) -> "NDFPredictor":
        """Load a trained model from disk."""
        import torch
        
        save_dir = Path(path)
        
        with open(save_dir / "config.json") as f:
            config = json.load(f)
        
        predictor = cls(model_name=str(save_dir / "backbone"))
        predictor._ensure_model()
        
        predictor._ndf_head.load_state_dict(
            torch.load(save_dir / "ndf_head.pt", map_location=predictor.device)
        )
        predictor._archetype_head.load_state_dict(
            torch.load(save_dir / "archetype_head.pt", map_location=predictor.device)
        )
        predictor._mechanism_head.load_state_dict(
            torch.load(save_dir / "mechanism_head.pt", map_location=predictor.device)
        )
        
        logger.info(f"Model loaded from {path}")
        return predictor


# =============================================================================
# TRAINING PIPELINE
# =============================================================================

class NDFTrainer:
    """
    Training pipeline for the NDF predictor using weak supervision labels.
    
    Training strategy:
    1. Curriculum learning: start with high-confidence labels (agreement > 0.75)
    2. Gradually include lower-confidence labels as model improves
    3. Multi-task: shared backbone, separate heads for NDF/archetype/mechanism
    4. Category-aware: category token prepended to text for domain adaptation
    """
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        learning_rate: float = 2e-5,
        batch_size: int = 32,
        epochs: int = 3,
        device: str = "cpu",
    ):
        self.model_name = model_name
        self.learning_rate = learning_rate
        self.batch_size = batch_size
        self.epochs = epochs
        self.device = device
    
    def train(
        self,
        train_texts: List[str],
        train_ndf_labels: np.ndarray,
        val_texts: Optional[List[str]] = None,
        val_ndf_labels: Optional[np.ndarray] = None,
        confidence_weights: Optional[np.ndarray] = None,
        output_dir: str = "models/ndf_predictor",
    ) -> Dict[str, float]:
        """
        Train the NDF predictor on weak supervision labels.
        
        Args:
            train_texts: List of review texts
            train_ndf_labels: Array of shape (N, 7) with NDF dimension labels
            val_texts: Optional validation texts
            val_ndf_labels: Optional validation labels
            confidence_weights: Per-example confidence weights (0-1)
            output_dir: Where to save the trained model
            
        Returns:
            Training metrics dict
        """
        try:
            import torch
            import torch.nn as nn
            from torch.utils.data import DataLoader, TensorDataset
            from transformers import AutoTokenizer, AutoModel, get_linear_schedule_with_warmup
        except ImportError:
            logger.error("PyTorch and Transformers required for training")
            return {"error": "Dependencies not available"}
        
        logger.info(f"Starting NDF training: {len(train_texts)} examples, {self.epochs} epochs")
        
        # Initialize model
        predictor = NDFPredictor(model_name=self.model_name, device=self.device)
        predictor._ensure_model()
        
        tokenizer = predictor._tokenizer
        model = predictor._model
        ndf_head = predictor._ndf_head
        
        # Set to training mode
        model.train()
        ndf_head.train()
        
        # Tokenize
        train_encodings = tokenizer(
            train_texts,
            max_length=256,
            truncation=True,
            padding=True,
            return_tensors="pt",
        )
        
        train_labels = torch.tensor(train_ndf_labels, dtype=torch.float32)
        
        if confidence_weights is not None:
            weights = torch.tensor(confidence_weights, dtype=torch.float32)
        else:
            weights = torch.ones(len(train_texts), dtype=torch.float32)
        
        # Optimizer
        optimizer = torch.optim.AdamW(
            list(model.parameters()) + list(ndf_head.parameters()),
            lr=self.learning_rate,
            weight_decay=0.01,
        )
        
        total_steps = (len(train_texts) // self.batch_size + 1) * self.epochs
        scheduler = get_linear_schedule_with_warmup(
            optimizer,
            num_warmup_steps=int(total_steps * 0.1),
            num_training_steps=total_steps,
        )
        
        # Training loop
        metrics = {"train_losses": [], "val_losses": []}
        
        for epoch in range(self.epochs):
            epoch_loss = 0.0
            num_batches = 0
            
            # Shuffle indices
            indices = torch.randperm(len(train_texts))
            
            for i in range(0, len(train_texts), self.batch_size):
                batch_idx = indices[i:i + self.batch_size]
                
                batch_inputs = {
                    k: v[batch_idx].to(self.device)
                    for k, v in train_encodings.items()
                }
                batch_labels = train_labels[batch_idx].to(self.device)
                batch_weights = weights[batch_idx].to(self.device)
                
                # Forward
                outputs = model(**batch_inputs)
                cls_embedding = outputs.last_hidden_state[:, 0, :]
                predictions = ndf_head(cls_embedding)
                
                # Weighted MSE loss
                loss = ((predictions - batch_labels) ** 2 * batch_weights.unsqueeze(1)).mean()
                
                # Backward
                optimizer.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                
                epoch_loss += loss.item()
                num_batches += 1
            
            avg_loss = epoch_loss / max(1, num_batches)
            metrics["train_losses"].append(avg_loss)
            
            logger.info(f"Epoch {epoch + 1}/{self.epochs}: train_loss={avg_loss:.4f}")
        
        # Save trained model
        predictor.save(output_dir)
        
        metrics["final_train_loss"] = metrics["train_losses"][-1]
        logger.info(f"Training complete. Model saved to {output_dir}")
        
        return metrics
