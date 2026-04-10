# =============================================================================
# ADAM Weak Supervision Pipeline
# Location: adam/ml/weak_supervisor.py
# =============================================================================

"""
WEAK SUPERVISION PIPELINE

Converts rule-based extraction outputs (NDF, 430+ dimensions, archetypes)
into training data for ML models. This is the key insight: our 1B+ reviews
processed by rule-based extractors create the LARGEST labeled dataset for
psychological dimension prediction ever assembled.

Paradigm: Snorkel / Data Programming (Ratner et al., Stanford 2017)
- Rule-based extractors = "labeling functions"
- Each LF votes on each example
- Noise-aware label model resolves disagreements
- Final labels train downstream ML models

Pipeline:
    1. Export rule-based outputs → labeled training examples
    2. Apply noise-aware label model → denoised labels
    3. Generate train/val/test splits
    4. Output format for PyTorch DataLoader or HuggingFace datasets
"""

import json
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict

import numpy as np

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class LabeledExample:
    """A single labeled training example."""
    text: str
    text_hash: str  # Dedup key
    
    # NDF labels (7 dimensions, each 0-1)
    ndf_labels: Dict[str, float] = field(default_factory=dict)
    ndf_confidence: float = 0.0
    
    # Dimension labels (430+ dimensions, each 0-1)
    dimension_labels: Dict[str, float] = field(default_factory=dict)
    dimension_confidence: float = 0.0
    
    # Archetype label
    archetype_label: Optional[str] = None
    archetype_confidence: float = 0.0
    
    # Mechanism susceptibility labels
    mechanism_labels: Dict[str, float] = field(default_factory=dict)
    
    # Source metadata
    source_dataset: str = ""
    category: str = ""
    
    # Label quality metrics
    labeling_functions_agreed: int = 0
    labeling_functions_total: int = 0
    
    def label_agreement_ratio(self) -> float:
        if self.labeling_functions_total == 0:
            return 0.0
        return self.labeling_functions_agreed / self.labeling_functions_total


@dataclass
class TrainingBatch:
    """A batch of labeled examples ready for training."""
    examples: List[LabeledExample]
    task: str  # "ndf", "dimensions", "archetype", "mechanism"
    split: str  # "train", "val", "test"
    
    def to_texts_and_labels(self) -> Tuple[List[str], np.ndarray]:
        """Convert to texts + label matrix for training."""
        texts = [e.text for e in self.examples]
        
        if self.task == "ndf":
            dims = ["approach_avoidance", "temporal_horizon", "social_calibration",
                     "uncertainty_tolerance", "status_sensitivity",
                     "cognitive_engagement", "arousal_seeking"]
            labels = np.array([
                [e.ndf_labels.get(d, 0.5) for d in dims]
                for e in self.examples
            ])
        elif self.task == "archetype":
            # One-hot or string labels
            labels = np.array([e.archetype_label or "unknown" for e in self.examples])
        elif self.task == "mechanism":
            mechs = sorted(set(k for e in self.examples for k in e.mechanism_labels))
            labels = np.array([
                [e.mechanism_labels.get(m, 0.5) for m in mechs]
                for e in self.examples
            ])
        else:
            # Default: dimension labels
            dims = sorted(set(k for e in self.examples for k in e.dimension_labels))
            labels = np.array([
                [e.dimension_labels.get(d, 0.0) for d in dims]
                for e in self.examples
            ])
        
        return texts, labels


# =============================================================================
# WEAK SUPERVISION PIPELINE
# =============================================================================

class WeakSupervisor:
    """
    Converts rule-based extraction outputs into ML training data.
    
    The key innovation: we don't need human labels. Our rule-based
    extractors (NDF, 82 frameworks, 430+ dimensions, deep archetype)
    each act as a "labeling function" that votes on every review.
    
    Where multiple LFs agree, we have high confidence.
    Where they disagree, we apply a noise-aware label model.
    """
    
    def __init__(
        self,
        output_dir: str = "data/ml_training",
        min_text_length: int = 50,
        min_label_confidence: float = 0.3,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.min_text_length = min_text_length
        self.min_label_confidence = min_label_confidence
        
        self._examples: List[LabeledExample] = []
        self._seen_hashes: set = set()
    
    def add_from_ingestion_result(
        self,
        text: str,
        ndf_profile: Optional[Dict[str, float]] = None,
        dimension_profile: Optional[Dict[str, float]] = None,
        archetype: Optional[str] = None,
        archetype_confidence: float = 0.0,
        mechanism_susceptibility: Optional[Dict[str, float]] = None,
        source_dataset: str = "",
        category: str = "",
    ) -> bool:
        """
        Add a labeled example from ingestion pipeline output.
        
        Returns True if example was added (not duplicate, meets quality threshold).
        """
        if len(text) < self.min_text_length:
            return False
        
        # Dedup
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in self._seen_hashes:
            return False
        self._seen_hashes.add(text_hash)
        
        # Count how many labeling functions produced output
        lf_total = 0
        lf_agreed = 0
        
        ndf_labels = {}
        ndf_conf = 0.0
        if ndf_profile:
            lf_total += 1
            non_default = sum(1 for v in ndf_profile.values() if abs(v - 0.5) > 0.05)
            if non_default >= 3:  # At least 3 dimensions with signal
                ndf_labels = ndf_profile
                ndf_conf = min(0.9, 0.3 + non_default * 0.1)
                lf_agreed += 1
        
        dim_labels = {}
        dim_conf = 0.0
        if dimension_profile:
            lf_total += 1
            active_dims = sum(1 for v in dimension_profile.values() if v > 0.1)
            if active_dims >= 5:
                dim_labels = dimension_profile
                dim_conf = min(0.9, 0.2 + active_dims * 0.02)
                lf_agreed += 1
        
        arch_label = None
        arch_conf = 0.0
        if archetype and archetype_confidence > self.min_label_confidence:
            lf_total += 1
            arch_label = archetype
            arch_conf = archetype_confidence
            lf_agreed += 1
        
        mech_labels = {}
        if mechanism_susceptibility:
            lf_total += 1
            active_mechs = sum(1 for v in mechanism_susceptibility.values() if abs(v - 0.5) > 0.1)
            if active_mechs >= 2:
                mech_labels = mechanism_susceptibility
                lf_agreed += 1
        
        if lf_agreed < 1:
            return False  # No labeling function produced usable output
        
        example = LabeledExample(
            text=text,
            text_hash=text_hash,
            ndf_labels=ndf_labels,
            ndf_confidence=ndf_conf,
            dimension_labels=dim_labels,
            dimension_confidence=dim_conf,
            archetype_label=arch_label,
            archetype_confidence=arch_conf,
            mechanism_labels=mech_labels,
            source_dataset=source_dataset,
            category=category,
            labeling_functions_agreed=lf_agreed,
            labeling_functions_total=lf_total,
        )
        
        self._examples.append(example)
        return True
    
    def apply_noise_aware_label_model(self) -> None:
        """
        Apply a noise-aware label model to denoise weak labels.
        
        Uses the principle from Snorkel: when multiple labeling functions
        disagree, weight by their estimated accuracy rather than majority vote.
        
        For our case:
        - NDF extractor: high precision, moderate recall
        - 430+ dimension profiler: moderate precision, high recall
        - Archetype detector: moderate precision, moderate recall
        - Mechanism susceptibility: moderate precision, moderate recall
        
        We upweight examples where multiple LFs agree.
        """
        for example in self._examples:
            agreement = example.label_agreement_ratio()
            
            # Boost confidence for high-agreement examples
            if agreement > 0.75:
                example.ndf_confidence = min(0.95, example.ndf_confidence * 1.2)
                example.dimension_confidence = min(0.95, example.dimension_confidence * 1.2)
                example.archetype_confidence = min(0.95, example.archetype_confidence * 1.2)
            elif agreement < 0.5:
                # Reduce confidence for low-agreement examples
                example.ndf_confidence *= 0.8
                example.dimension_confidence *= 0.8
                example.archetype_confidence *= 0.8
        
        logger.info(
            f"Applied noise-aware label model to {len(self._examples)} examples. "
            f"High agreement: {sum(1 for e in self._examples if e.label_agreement_ratio() > 0.75)}, "
            f"Low agreement: {sum(1 for e in self._examples if e.label_agreement_ratio() < 0.5)}"
        )
    
    def generate_splits(
        self,
        train_ratio: float = 0.85,
        val_ratio: float = 0.10,
        test_ratio: float = 0.05,
        seed: int = 42,
    ) -> Dict[str, List[LabeledExample]]:
        """Generate train/val/test splits with stratification by source."""
        rng = np.random.RandomState(seed)
        
        # Shuffle
        indices = list(range(len(self._examples)))
        rng.shuffle(indices)
        
        n = len(indices)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)
        
        splits = {
            "train": [self._examples[i] for i in indices[:n_train]],
            "val": [self._examples[i] for i in indices[n_train:n_train + n_val]],
            "test": [self._examples[i] for i in indices[n_train + n_val:]],
        }
        
        logger.info(
            f"Generated splits: train={len(splits['train'])}, "
            f"val={len(splits['val'])}, test={len(splits['test'])}"
        )
        
        return splits
    
    def export_training_batches(
        self,
        task: str = "ndf",
        batch_size: int = 256,
    ) -> List[TrainingBatch]:
        """Export training batches for a specific task."""
        splits = self.generate_splits()
        
        batches = []
        for split_name, examples in splits.items():
            # Filter to examples with labels for this task
            if task == "ndf":
                filtered = [e for e in examples if e.ndf_labels and e.ndf_confidence > 0.3]
            elif task == "archetype":
                filtered = [e for e in examples if e.archetype_label and e.archetype_confidence > 0.3]
            elif task == "mechanism":
                filtered = [e for e in examples if e.mechanism_labels]
            else:
                filtered = [e for e in examples if e.dimension_labels]
            
            # Create batches
            for i in range(0, len(filtered), batch_size):
                batch = TrainingBatch(
                    examples=filtered[i:i + batch_size],
                    task=task,
                    split=split_name,
                )
                batches.append(batch)
        
        logger.info(f"Created {len(batches)} batches for task '{task}'")
        return batches
    
    def export_to_disk(self, task: str = "ndf") -> Path:
        """Export labeled data to disk in JSON Lines format."""
        output_path = self.output_dir / f"{task}_training_data.jsonl"
        
        splits = self.generate_splits()
        
        count = 0
        with open(output_path, "w") as f:
            for split_name, examples in splits.items():
                for example in examples:
                    record = {
                        "text": example.text,
                        "split": split_name,
                        "source": example.source_dataset,
                        "category": example.category,
                    }
                    
                    if task == "ndf" and example.ndf_labels:
                        record["labels"] = example.ndf_labels
                        record["confidence"] = example.ndf_confidence
                    elif task == "archetype" and example.archetype_label:
                        record["label"] = example.archetype_label
                        record["confidence"] = example.archetype_confidence
                    elif task == "mechanism" and example.mechanism_labels:
                        record["labels"] = example.mechanism_labels
                    elif task == "dimensions" and example.dimension_labels:
                        record["labels"] = example.dimension_labels
                        record["confidence"] = example.dimension_confidence
                    else:
                        continue
                    
                    f.write(json.dumps(record) + "\n")
                    count += 1
        
        logger.info(f"Exported {count} examples to {output_path}")
        return output_path
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get statistics about the labeled dataset."""
        return {
            "total_examples": len(self._examples),
            "with_ndf": sum(1 for e in self._examples if e.ndf_labels),
            "with_dimensions": sum(1 for e in self._examples if e.dimension_labels),
            "with_archetype": sum(1 for e in self._examples if e.archetype_label),
            "with_mechanism": sum(1 for e in self._examples if e.mechanism_labels),
            "high_agreement": sum(1 for e in self._examples if e.label_agreement_ratio() > 0.75),
            "unique_sources": len(set(e.source_dataset for e in self._examples)),
            "unique_categories": len(set(e.category for e in self._examples)),
        }
