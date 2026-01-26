# =============================================================================
# ADAM Embedding Fine-Tuning Dataset
# Location: adam/embeddings/finetuning/dataset.py
# =============================================================================

"""
FINE-TUNING DATASET

Dataset creation for embedding model fine-tuning.

Supports:
- Contrastive pairs (similar/dissimilar)
- Triplets (anchor, positive, negative)
- Behavioral signals from ADAM interactions
- Psychological ground truth labels
"""

import asyncio
import hashlib
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# =============================================================================
# DATA MODELS
# =============================================================================

class SampleType(str, Enum):
    """Types of training samples."""
    
    CONTRASTIVE_PAIR = "contrastive_pair"
    TRIPLET = "triplet"
    CLASSIFICATION = "classification"
    REGRESSION = "regression"


class LabelSource(str, Enum):
    """Source of ground truth labels."""
    
    BEHAVIORAL = "behavioral"      # From user behavior
    EXPLICIT = "explicit"          # From explicit feedback
    INFERRED = "inferred"          # From inference chain
    SYNTHETIC = "synthetic"        # Synthetically generated
    EXPERT = "expert"              # Expert annotated


class ContrastivePair(BaseModel):
    """A contrastive pair for similarity learning."""
    
    pair_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    
    # Text inputs
    text_a: str
    text_b: str
    
    # Label: 1.0 = similar, 0.0 = dissimilar
    label: float = Field(ge=0.0, le=1.0)
    
    # Metadata
    source_a_id: Optional[str] = None
    source_b_id: Optional[str] = None
    label_source: LabelSource = LabelSource.BEHAVIORAL
    
    # Psychological context
    psychological_dimension: Optional[str] = None  # e.g., "openness"
    mechanism_id: Optional[str] = None
    
    # Quality
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)


class TripletSample(BaseModel):
    """A triplet sample for metric learning."""
    
    triplet_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    
    # Texts
    anchor: str
    positive: str  # Similar to anchor
    negative: str  # Dissimilar to anchor
    
    # Metadata
    anchor_id: Optional[str] = None
    positive_id: Optional[str] = None
    negative_id: Optional[str] = None
    label_source: LabelSource = LabelSource.BEHAVIORAL
    
    # Psychological context
    psychological_dimension: Optional[str] = None
    
    # Margin (distance between positive and negative)
    margin: float = Field(ge=0.0, default=0.2)
    
    # Quality
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)


class ClassificationSample(BaseModel):
    """A classification sample for supervised learning."""
    
    sample_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    
    text: str
    label: str  # Class label
    label_index: int  # Numeric label
    
    source_id: Optional[str] = None
    label_source: LabelSource = LabelSource.BEHAVIORAL
    
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)


# =============================================================================
# FINE-TUNING DATASET
# =============================================================================

class FineTuningDataset(BaseModel):
    """Complete dataset for embedding fine-tuning."""
    
    dataset_id: str = Field(default_factory=lambda: uuid4().hex[:12])
    name: str
    version: str = "1.0.0"
    
    # Samples
    contrastive_pairs: List[ContrastivePair] = Field(default_factory=list)
    triplets: List[TripletSample] = Field(default_factory=list)
    classification_samples: List[ClassificationSample] = Field(default_factory=list)
    
    # Metadata
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    description: str = ""
    
    # Statistics
    total_samples: int = 0
    psychological_dimensions: List[str] = Field(default_factory=list)
    mechanisms_covered: List[str] = Field(default_factory=list)
    
    # Quality metrics
    avg_confidence: float = 0.0
    label_sources: Dict[str, int] = Field(default_factory=dict)
    
    def add_contrastive_pair(self, pair: ContrastivePair) -> None:
        """Add a contrastive pair to the dataset."""
        self.contrastive_pairs.append(pair)
        self.total_samples += 1
        self._update_metadata(pair)
    
    def add_triplet(self, triplet: TripletSample) -> None:
        """Add a triplet to the dataset."""
        self.triplets.append(triplet)
        self.total_samples += 1
        self._update_metadata(triplet)
    
    def add_classification_sample(self, sample: ClassificationSample) -> None:
        """Add a classification sample to the dataset."""
        self.classification_samples.append(sample)
        self.total_samples += 1
    
    def _update_metadata(self, sample) -> None:
        """Update dataset metadata from sample."""
        if hasattr(sample, "psychological_dimension") and sample.psychological_dimension:
            if sample.psychological_dimension not in self.psychological_dimensions:
                self.psychological_dimensions.append(sample.psychological_dimension)
        
        if hasattr(sample, "mechanism_id") and sample.mechanism_id:
            if sample.mechanism_id not in self.mechanisms_covered:
                self.mechanisms_covered.append(sample.mechanism_id)
        
        # Update label source counts
        source = sample.label_source.value
        self.label_sources[source] = self.label_sources.get(source, 0) + 1
    
    def compute_statistics(self) -> Dict[str, Any]:
        """Compute dataset statistics."""
        confidences = []
        
        for pair in self.contrastive_pairs:
            confidences.append(pair.confidence)
        for triplet in self.triplets:
            confidences.append(triplet.confidence)
        for sample in self.classification_samples:
            confidences.append(sample.confidence)
        
        self.avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            "total_samples": self.total_samples,
            "contrastive_pairs": len(self.contrastive_pairs),
            "triplets": len(self.triplets),
            "classification_samples": len(self.classification_samples),
            "psychological_dimensions": self.psychological_dimensions,
            "mechanisms_covered": self.mechanisms_covered,
            "avg_confidence": self.avg_confidence,
            "label_sources": self.label_sources,
        }
    
    def split(
        self,
        train_ratio: float = 0.8,
        val_ratio: float = 0.1,
        test_ratio: float = 0.1,
        seed: int = 42,
    ) -> Tuple["FineTuningDataset", "FineTuningDataset", "FineTuningDataset"]:
        """Split dataset into train/val/test."""
        random.seed(seed)
        
        def split_list(items, ratios):
            n = len(items)
            items_shuffled = items.copy()
            random.shuffle(items_shuffled)
            
            train_end = int(n * ratios[0])
            val_end = int(n * (ratios[0] + ratios[1]))
            
            return (
                items_shuffled[:train_end],
                items_shuffled[train_end:val_end],
                items_shuffled[val_end:],
            )
        
        ratios = (train_ratio, val_ratio, test_ratio)
        
        train_pairs, val_pairs, test_pairs = split_list(self.contrastive_pairs, ratios)
        train_triplets, val_triplets, test_triplets = split_list(self.triplets, ratios)
        train_class, val_class, test_class = split_list(self.classification_samples, ratios)
        
        train = FineTuningDataset(
            name=f"{self.name}_train",
            contrastive_pairs=train_pairs,
            triplets=train_triplets,
            classification_samples=train_class,
        )
        
        val = FineTuningDataset(
            name=f"{self.name}_val",
            contrastive_pairs=val_pairs,
            triplets=val_triplets,
            classification_samples=val_class,
        )
        
        test = FineTuningDataset(
            name=f"{self.name}_test",
            contrastive_pairs=test_pairs,
            triplets=test_triplets,
            classification_samples=test_class,
        )
        
        train.compute_statistics()
        val.compute_statistics()
        test.compute_statistics()
        
        return train, val, test


# =============================================================================
# DATASET BUILDER
# =============================================================================

class DatasetBuilder:
    """
    Builder for creating fine-tuning datasets from ADAM data.
    
    Supports:
    - Behavioral signals from user interactions
    - Conversion outcomes for mechanism effectiveness
    - Psychological profile similarity
    - Ad-user matching outcomes
    """
    
    def __init__(
        self,
        dataset_name: str,
        min_confidence: float = 0.6,
    ):
        self.dataset_name = dataset_name
        self.min_confidence = min_confidence
        self.dataset = FineTuningDataset(name=dataset_name)
        
        # Big Five trait keywords for text analysis
        self._big_five_keywords = {
            "openness": {
                "high": ["creative", "curious", "imaginative", "artistic", "innovative"],
                "low": ["conventional", "practical", "traditional", "routine"],
            },
            "conscientiousness": {
                "high": ["organized", "disciplined", "reliable", "careful", "thorough"],
                "low": ["spontaneous", "flexible", "casual", "relaxed"],
            },
            "extraversion": {
                "high": ["outgoing", "energetic", "social", "talkative", "assertive"],
                "low": ["quiet", "reserved", "introspective", "solitary"],
            },
            "agreeableness": {
                "high": ["kind", "cooperative", "trusting", "helpful", "compassionate"],
                "low": ["competitive", "skeptical", "challenging", "direct"],
            },
            "neuroticism": {
                "high": ["anxious", "worried", "sensitive", "nervous", "emotional"],
                "low": ["calm", "stable", "relaxed", "resilient", "confident"],
            },
        }
        
        # Regulatory focus keywords
        self._regulatory_keywords = {
            "promotion": ["achieve", "gain", "aspire", "opportunity", "success", "grow"],
            "prevention": ["safe", "secure", "protect", "avoid", "careful", "responsible"],
        }
    
    def add_from_conversion_outcomes(
        self,
        outcomes: List[Dict[str, Any]],
    ) -> int:
        """
        Add samples from conversion outcome data.
        
        Creates triplets where:
        - Anchor: User who converted
        - Positive: Similar user who also converted
        - Negative: User who didn't convert
        """
        added = 0
        
        # Group by conversion status
        converted = [o for o in outcomes if o.get("converted", False)]
        not_converted = [o for o in outcomes if not o.get("converted", False)]
        
        if len(converted) < 2 or len(not_converted) < 1:
            logger.warning("Insufficient data for conversion triplets")
            return 0
        
        for i, anchor in enumerate(converted[:-1]):
            positive = converted[i + 1]
            negative = random.choice(not_converted)
            
            anchor_text = self._outcome_to_text(anchor)
            positive_text = self._outcome_to_text(positive)
            negative_text = self._outcome_to_text(negative)
            
            triplet = TripletSample(
                anchor=anchor_text,
                positive=positive_text,
                negative=negative_text,
                anchor_id=anchor.get("user_id"),
                positive_id=positive.get("user_id"),
                negative_id=negative.get("user_id"),
                label_source=LabelSource.BEHAVIORAL,
                mechanism_id=anchor.get("mechanism_id"),
                confidence=0.85,
            )
            
            self.dataset.add_triplet(triplet)
            added += 1
        
        return added
    
    def add_from_mechanism_effectiveness(
        self,
        effectiveness_data: List[Dict[str, Any]],
    ) -> int:
        """
        Add samples from mechanism effectiveness data.
        
        Creates contrastive pairs based on mechanism success.
        """
        added = 0
        
        for data in effectiveness_data:
            user_id = data.get("user_id")
            mechanism_id = data.get("mechanism_id")
            success_rate = data.get("success_rate", 0.5)
            trial_count = data.get("trial_count", 0)
            
            if trial_count < 5:
                continue  # Skip low-confidence data
            
            user_text = self._user_mechanism_to_text(data)
            mechanism_text = self._mechanism_to_text(mechanism_id, success_rate)
            
            # High success = similar, low success = dissimilar
            label = success_rate
            
            pair = ContrastivePair(
                text_a=user_text,
                text_b=mechanism_text,
                label=label,
                source_a_id=user_id,
                source_b_id=mechanism_id,
                label_source=LabelSource.BEHAVIORAL,
                mechanism_id=mechanism_id,
                confidence=min(0.95, 0.5 + trial_count / 100),
            )
            
            self.dataset.add_contrastive_pair(pair)
            added += 1
        
        return added
    
    def add_from_psychological_profiles(
        self,
        profiles: List[Dict[str, Any]],
    ) -> int:
        """
        Add samples from psychological profile similarity.
        
        Creates contrastive pairs based on Big Five trait similarity.
        """
        added = 0
        
        for trait in ["openness", "conscientiousness", "extraversion", 
                      "agreeableness", "neuroticism"]:
            # Find high-trait and low-trait users
            high_trait = [
                p for p in profiles
                if p.get("big_five", {}).get(trait, 0.5) > 0.7
            ]
            low_trait = [
                p for p in profiles
                if p.get("big_five", {}).get(trait, 0.5) < 0.3
            ]
            
            # Create pairs within same trait level (similar)
            for i in range(0, len(high_trait) - 1, 2):
                pair = ContrastivePair(
                    text_a=self._profile_to_text(high_trait[i]),
                    text_b=self._profile_to_text(high_trait[i + 1]),
                    label=0.9,  # Similar
                    source_a_id=high_trait[i].get("user_id"),
                    source_b_id=high_trait[i + 1].get("user_id"),
                    label_source=LabelSource.INFERRED,
                    psychological_dimension=trait,
                    confidence=0.8,
                )
                self.dataset.add_contrastive_pair(pair)
                added += 1
            
            # Create pairs across trait levels (dissimilar)
            for high, low in zip(high_trait[:len(low_trait)], low_trait):
                pair = ContrastivePair(
                    text_a=self._profile_to_text(high),
                    text_b=self._profile_to_text(low),
                    label=0.1,  # Dissimilar
                    source_a_id=high.get("user_id"),
                    source_b_id=low.get("user_id"),
                    label_source=LabelSource.INFERRED,
                    psychological_dimension=trait,
                    confidence=0.8,
                )
                self.dataset.add_contrastive_pair(pair)
                added += 1
        
        return added
    
    def add_from_ad_user_matches(
        self,
        matches: List[Dict[str, Any]],
    ) -> int:
        """
        Add samples from ad-user match outcomes.
        
        Creates triplets based on engagement/conversion.
        """
        added = 0
        
        # Group by user
        user_matches = {}
        for match in matches:
            user_id = match.get("user_id")
            if user_id not in user_matches:
                user_matches[user_id] = {"engaged": [], "not_engaged": []}
            
            if match.get("engaged", False):
                user_matches[user_id]["engaged"].append(match)
            else:
                user_matches[user_id]["not_engaged"].append(match)
        
        for user_id, data in user_matches.items():
            if len(data["engaged"]) < 1 or len(data["not_engaged"]) < 1:
                continue
            
            for engaged in data["engaged"]:
                not_engaged = random.choice(data["not_engaged"])
                
                anchor_text = self._user_to_text({"user_id": user_id})
                positive_text = self._ad_to_text(engaged)
                negative_text = self._ad_to_text(not_engaged)
                
                triplet = TripletSample(
                    anchor=anchor_text,
                    positive=positive_text,
                    negative=negative_text,
                    anchor_id=user_id,
                    positive_id=engaged.get("ad_id"),
                    negative_id=not_engaged.get("ad_id"),
                    label_source=LabelSource.BEHAVIORAL,
                    mechanism_id=engaged.get("mechanism_id"),
                    confidence=0.8,
                )
                
                self.dataset.add_triplet(triplet)
                added += 1
        
        return added
    
    def add_synthetic_personality_pairs(
        self,
        count: int = 1000,
    ) -> int:
        """
        Generate synthetic contrastive pairs for personality traits.
        
        Uses keyword templates to create training data.
        """
        added = 0
        
        for trait, keywords in self._big_five_keywords.items():
            for _ in range(count // 5):  # Distribute across traits
                # Generate high-trait text
                high_keywords = random.sample(keywords["high"], min(3, len(keywords["high"])))
                high_text = f"User who is {', '.join(high_keywords)}"
                
                # Generate low-trait text
                low_keywords = random.sample(keywords["low"], min(3, len(keywords["low"])))
                low_text = f"User who is {', '.join(low_keywords)}"
                
                # Similar pair (both high)
                if random.random() > 0.5:
                    high_text_2 = f"Person described as {', '.join(random.sample(keywords['high'], min(2, len(keywords['high']))))} "
                    pair = ContrastivePair(
                        text_a=high_text,
                        text_b=high_text_2,
                        label=0.85,
                        label_source=LabelSource.SYNTHETIC,
                        psychological_dimension=trait,
                        confidence=0.7,
                    )
                else:
                    # Dissimilar pair (high vs low)
                    pair = ContrastivePair(
                        text_a=high_text,
                        text_b=low_text,
                        label=0.15,
                        label_source=LabelSource.SYNTHETIC,
                        psychological_dimension=trait,
                        confidence=0.7,
                    )
                
                self.dataset.add_contrastive_pair(pair)
                added += 1
        
        return added
    
    def add_synthetic_regulatory_focus_pairs(
        self,
        count: int = 500,
    ) -> int:
        """Generate synthetic pairs for regulatory focus."""
        added = 0
        
        for _ in range(count):
            promo_keywords = random.sample(
                self._regulatory_keywords["promotion"], 
                min(3, len(self._regulatory_keywords["promotion"]))
            )
            prev_keywords = random.sample(
                self._regulatory_keywords["prevention"],
                min(3, len(self._regulatory_keywords["prevention"]))
            )
            
            promo_text = f"Motivated by {', '.join(promo_keywords)}"
            prev_text = f"Focused on {', '.join(prev_keywords)}"
            
            # Cross-focus pairs are dissimilar
            pair = ContrastivePair(
                text_a=promo_text,
                text_b=prev_text,
                label=0.2,  # Different focus = dissimilar
                label_source=LabelSource.SYNTHETIC,
                psychological_dimension="regulatory_focus",
                confidence=0.7,
            )
            
            self.dataset.add_contrastive_pair(pair)
            added += 1
        
        return added
    
    def build(self) -> FineTuningDataset:
        """Build and return the dataset."""
        self.dataset.compute_statistics()
        return self.dataset
    
    # =========================================================================
    # TEXT CONVERSION HELPERS
    # =========================================================================
    
    def _outcome_to_text(self, outcome: Dict[str, Any]) -> str:
        """Convert outcome data to text."""
        parts = []
        
        if "user_id" in outcome:
            parts.append(f"User {outcome['user_id']}")
        if "mechanism_id" in outcome:
            parts.append(f"responded to {outcome['mechanism_id']}")
        if "category" in outcome:
            parts.append(f"in {outcome['category']}")
        if outcome.get("converted"):
            parts.append("and converted")
        
        return " ".join(parts) if parts else "User interaction"
    
    def _user_mechanism_to_text(self, data: Dict[str, Any]) -> str:
        """Convert user-mechanism data to text."""
        mechanism = data.get("mechanism_id", "unknown")
        success = data.get("success_rate", 0.5)
        
        if success > 0.7:
            return f"User highly responsive to {mechanism} persuasion"
        elif success > 0.4:
            return f"User moderately responsive to {mechanism}"
        else:
            return f"User resistant to {mechanism} persuasion"
    
    def _mechanism_to_text(self, mechanism_id: str, success_rate: float) -> str:
        """Convert mechanism to text description."""
        descriptions = {
            "social_proof": "Evidence that others trust and use the product",
            "scarcity": "Limited availability and urgency messaging",
            "authority": "Expert endorsements and credentials",
            "reciprocity": "Free value and gifts before asking",
            "commitment": "Small initial commitments leading to larger ones",
            "liking": "Personal connection and relatability",
        }
        
        base = descriptions.get(mechanism_id, mechanism_id)
        if success_rate > 0.7:
            return f"{base} - highly effective"
        elif success_rate > 0.4:
            return f"{base} - moderately effective"
        else:
            return f"{base} - limited effectiveness"
    
    def _profile_to_text(self, profile: Dict[str, Any]) -> str:
        """Convert psychological profile to text."""
        parts = []
        
        big_five = profile.get("big_five", {})
        for trait, value in big_five.items():
            if value > 0.7:
                parts.append(f"high {trait}")
            elif value < 0.3:
                parts.append(f"low {trait}")
        
        reg_focus = profile.get("regulatory_focus", {})
        if reg_focus.get("promotion", 0.5) > reg_focus.get("prevention", 0.5):
            parts.append("promotion-focused")
        else:
            parts.append("prevention-focused")
        
        return f"User with {', '.join(parts)}" if parts else "User profile"
    
    def _user_to_text(self, user: Dict[str, Any]) -> str:
        """Convert user data to text."""
        return f"User {user.get('user_id', 'unknown')}"
    
    def _ad_to_text(self, ad: Dict[str, Any]) -> str:
        """Convert ad data to text."""
        parts = []
        
        if "headline" in ad:
            parts.append(ad["headline"])
        if "copy" in ad:
            parts.append(ad["copy"][:100])
        if "mechanism_id" in ad:
            parts.append(f"using {ad['mechanism_id']}")
        
        return " ".join(parts) if parts else "Ad creative"
