# =============================================================================
# ADAM Gradient Bridge Feature Models
# Location: adam/gradient_bridge/models/features.py
# =============================================================================

"""
FEATURE EXTRACTION MODELS

Models for extracting psychological features from atoms
to create enriched feature vectors for the bandit.

The key insight: Atoms produce psychological assessments that become
40+ features for the contextual bandit, enabling 3x faster convergence.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# =============================================================================
# ATOM FEATURES
# =============================================================================

class AtomFeatures(BaseModel):
    """Features extracted from a single atom's output."""
    
    atom_id: str
    atom_type: str
    
    # Primary assessment
    primary_assessment: str
    primary_value: Optional[float] = None
    
    # Confidence
    confidence: float = Field(ge=0.0, le=1.0)
    
    # Extracted features (normalized 0-1)
    features: Dict[str, float] = Field(default_factory=dict)
    
    # Feature names for downstream use
    feature_names: List[str] = Field(default_factory=list)


# =============================================================================
# PSYCHOLOGICAL FEATURES
# =============================================================================

class PsychologicalFeatures(BaseModel):
    """
    Psychological feature set extracted from atoms.
    
    These are the core psychological dimensions ADAM reasons about.
    """
    
    # Regulatory Focus
    regulatory_promotion: float = Field(ge=0.0, le=1.0, default=0.5)
    regulatory_prevention: float = Field(ge=0.0, le=1.0, default=0.5)
    regulatory_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Construal Level
    construal_abstract: float = Field(ge=0.0, le=1.0, default=0.5)
    construal_concrete: float = Field(ge=0.0, le=1.0, default=0.5)
    construal_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Big Five (if known)
    openness: float = Field(ge=0.0, le=1.0, default=0.5)
    conscientiousness: float = Field(ge=0.0, le=1.0, default=0.5)
    extraversion: float = Field(ge=0.0, le=1.0, default=0.5)
    agreeableness: float = Field(ge=0.0, le=1.0, default=0.5)
    neuroticism: float = Field(ge=0.0, le=1.0, default=0.5)
    personality_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Current State
    arousal: float = Field(ge=0.0, le=1.0, default=0.5)
    valence: float = Field(ge=0.0, le=1.0, default=0.5)
    engagement: float = Field(ge=0.0, le=1.0, default=0.5)
    
    def to_vector(self) -> List[float]:
        """Convert to feature vector."""
        return [
            self.regulatory_promotion,
            self.regulatory_prevention,
            self.regulatory_confidence,
            self.construal_abstract,
            self.construal_concrete,
            self.construal_confidence,
            self.openness,
            self.conscientiousness,
            self.extraversion,
            self.agreeableness,
            self.neuroticism,
            self.personality_confidence,
            self.arousal,
            self.valence,
            self.engagement,
        ]
    
    @classmethod
    def feature_names(cls) -> List[str]:
        """Get feature names for the vector."""
        return [
            "regulatory_promotion",
            "regulatory_prevention",
            "regulatory_confidence",
            "construal_abstract",
            "construal_concrete",
            "construal_confidence",
            "openness",
            "conscientiousness",
            "extraversion",
            "agreeableness",
            "neuroticism",
            "personality_confidence",
            "arousal",
            "valence",
            "engagement",
        ]


# =============================================================================
# CONTEXT FEATURES
# =============================================================================

class ContextFeatures(BaseModel):
    """Features from the request context."""
    
    # Session
    session_depth: int = Field(default=0, ge=0)
    session_duration_minutes: int = Field(default=0, ge=0)
    
    # Temporal
    hour_of_day: int = Field(ge=0, le=23, default=12)
    day_of_week: int = Field(ge=0, le=6, default=0)
    is_weekend: bool = Field(default=False)
    
    # Platform
    device_type: str = Field(default="unknown")
    platform: str = Field(default="unknown")
    
    # Content
    content_type: str = Field(default="unknown")
    station_format: str = Field(default="unknown")
    
    # User segment
    cold_start: bool = Field(default=False)
    data_richness: str = Field(default="unknown")
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to feature dict with numeric encoding."""
        features = {
            "session_depth": min(1.0, self.session_depth / 10),
            "session_duration": min(1.0, self.session_duration_minutes / 60),
            "hour_sin": self._hour_sin(),
            "hour_cos": self._hour_cos(),
            "is_weekend": 1.0 if self.is_weekend else 0.0,
            "is_cold_start": 1.0 if self.cold_start else 0.0,
        }
        return features
    
    def _hour_sin(self) -> float:
        """Cyclical encoding of hour."""
        import math
        return math.sin(2 * math.pi * self.hour_of_day / 24)
    
    def _hour_cos(self) -> float:
        """Cyclical encoding of hour."""
        import math
        return math.cos(2 * math.pi * self.hour_of_day / 24)


# =============================================================================
# MECHANISM FEATURES
# =============================================================================

class MechanismFeatures(BaseModel):
    """Features related to mechanism selection."""
    
    # Selected mechanism
    primary_mechanism: str = ""
    mechanism_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Mechanism affinity scores
    mechanism_scores: Dict[str, float] = Field(default_factory=dict)
    
    # Historical effectiveness (from graph)
    historical_effectiveness: Dict[str, float] = Field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to feature dict."""
        features = {
            "mechanism_confidence": self.mechanism_confidence,
        }
        
        # Add per-mechanism features
        for mech, score in self.mechanism_scores.items():
            features[f"mech_score_{mech}"] = score
        
        for mech, eff in self.historical_effectiveness.items():
            features[f"mech_hist_{mech}"] = eff
        
        return features


# =============================================================================
# ENRICHED FEATURE VECTOR
# =============================================================================

class EnrichedFeatureVector(BaseModel):
    """
    Complete enriched feature vector for the contextual bandit.
    
    Combines psychological, context, and mechanism features
    into a single vector with 40+ dimensions.
    """
    
    vector_id: str = Field(
        default_factory=lambda: f"vec_{uuid4().hex[:12]}"
    )
    
    # Source identifiers
    request_id: str
    user_id: str
    decision_id: Optional[str] = None
    
    # Component features
    psychological: PsychologicalFeatures = Field(
        default_factory=PsychologicalFeatures
    )
    context: ContextFeatures = Field(default_factory=ContextFeatures)
    mechanism: MechanismFeatures = Field(default_factory=MechanismFeatures)
    
    # Per-atom features
    atom_features: Dict[str, AtomFeatures] = Field(default_factory=dict)
    
    # Full feature dict (all features merged)
    features: Dict[str, float] = Field(default_factory=dict)
    
    # Feature names
    feature_names: List[str] = Field(default_factory=list)
    
    # Metadata
    total_features: int = Field(default=0, ge=0)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    def build_features(self) -> None:
        """Build the complete feature dict from components."""
        self.features = {}
        
        # Add psychological features
        for name, value in zip(
            PsychologicalFeatures.feature_names(),
            self.psychological.to_vector(),
        ):
            self.features[f"psych_{name}"] = value
        
        # Add context features
        for name, value in self.context.to_dict().items():
            self.features[f"ctx_{name}"] = value
        
        # Add mechanism features
        for name, value in self.mechanism.to_dict().items():
            self.features[f"mech_{name}"] = value
        
        # Add atom-specific features
        for atom_id, atom_feat in self.atom_features.items():
            for name, value in atom_feat.features.items():
                self.features[f"atom_{atom_id}_{name}"] = value
        
        self.feature_names = list(self.features.keys())
        self.total_features = len(self.features)
    
    def to_vector(self) -> List[float]:
        """Convert to ordered feature vector."""
        if not self.feature_names:
            self.build_features()
        return [self.features.get(n, 0.0) for n in self.feature_names]
