# =============================================================================
# ADAM Feature Store Models
# Location: adam/features/models.py
# =============================================================================

"""
FEATURE STORE MODELS

Models for feature definitions and values.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from pydantic import BaseModel, Field


class FeatureType(str, Enum):
    """Feature data types."""
    
    FLOAT = "float"
    INTEGER = "integer"
    STRING = "string"
    BOOLEAN = "boolean"
    VECTOR = "vector"
    TIMESTAMP = "timestamp"


class FeatureScope(str, Enum):
    """Feature scope."""
    
    USER = "user"
    ITEM = "item"
    CONTEXT = "context"
    INTERACTION = "interaction"


class AggregationType(str, Enum):
    """Aggregation types for derived features."""
    
    NONE = "none"
    SUM = "sum"
    MEAN = "mean"
    MAX = "max"
    MIN = "min"
    COUNT = "count"
    LAST = "last"


class FeatureDefinition(BaseModel):
    """Definition of a feature."""
    
    feature_id: str
    name: str
    description: Optional[str] = None
    
    # Type
    feature_type: FeatureType
    scope: FeatureScope
    
    # Schema
    dimensions: Optional[int] = None  # For vector types
    default_value: Optional[Any] = None
    
    # Aggregation
    aggregation: AggregationType = Field(default=AggregationType.NONE)
    time_window_seconds: Optional[int] = None
    
    # Versioning
    version: str = Field(default="1.0")
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    
    # Timing
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class FeatureValue(BaseModel):
    """A feature value for an entity."""
    
    feature_id: str
    entity_id: str  # User ID, Item ID, etc.
    
    # Value
    value: Any
    
    # Metadata
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    version: str = Field(default="1.0")
    
    # Quality
    freshness_seconds: Optional[float] = None
    confidence: Optional[float] = None


class FeatureSet(BaseModel):
    """Collection of features for a request."""
    
    entity_id: str
    
    # Features
    features: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    feature_ids: List[str] = Field(default_factory=list)
    
    # Quality
    freshness: Dict[str, float] = Field(
        default_factory=dict,
        description="feature_id -> seconds since update"
    )
    
    # Timing
    retrieved_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    retrieval_duration_ms: float = Field(default=0.0, ge=0.0)
