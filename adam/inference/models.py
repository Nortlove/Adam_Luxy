# =============================================================================
# ADAM Inference Engine Models (#09)
# Location: adam/inference/models.py
# =============================================================================

"""
INFERENCE ENGINE PYDANTIC MODELS

Enterprise-grade data models for the latency-optimized inference engine.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class InferenceTier(str, Enum):
    """Processing tiers with degradation path."""
    TIER_1_FULL = "tier_1_full"              # Full psychological reasoning (50-100ms)
    TIER_2_ARCHETYPE = "tier_2_archetype"    # Archetype-based selection (20-40ms)
    TIER_3_CACHED = "tier_3_cached"          # Mechanism-cached decision (5-15ms)
    TIER_4_COLD_START = "tier_4_cold_start"  # Cold start priors (2-5ms)
    TIER_5_DEFAULT = "tier_5_default"        # Global defaults (<1ms)


class MechanismType(str, Enum):
    """ADAM's 9 cognitive mechanisms."""
    CONSTRUAL_LEVEL = "construal_level"
    REGULATORY_FOCUS = "regulatory_focus"
    AUTOMATIC_EVALUATION = "automatic_evaluation"
    WANTING_LIKING = "wanting_liking"
    MIMETIC_DESIRE = "mimetic_desire"
    ATTENTION_DYNAMICS = "attention_dynamics"
    TEMPORAL_CONSTRUAL = "temporal_construal"
    IDENTITY_CONSTRUCTION = "identity_construction"
    EVOLUTIONARY_ADAPTATIONS = "evolutionary_adaptations"


class InferenceRequest(BaseModel):
    """Request for psychological inference."""
    
    request_id: str = Field(default_factory=lambda: f"inf_{uuid4().hex[:12]}")
    user_id: str
    session_id: Optional[str] = None
    
    # Context
    platform: str = "iheart"  # iheart, wpp
    content_id: Optional[str] = None
    content_type: Optional[str] = None
    
    # Constraints
    max_latency_ms: int = 100
    required_confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    
    # Features (if pre-fetched)
    pre_fetched_profile: Optional[Dict[str, Any]] = None
    pre_fetched_state: Optional[Dict[str, Any]] = None
    
    # Request metadata
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MechanismSelection(BaseModel):
    """Selected mechanism with confidence."""
    
    mechanism: MechanismType
    score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: Optional[str] = None


class DecisionContext(BaseModel):
    """Context for the inference decision."""
    
    # User state
    archetype: Optional[str] = None
    regulatory_focus: Optional[str] = None
    arousal_level: Optional[float] = None
    cognitive_load: Optional[float] = None
    
    # Journey state
    journey_stage: Optional[str] = None
    session_depth: int = 0
    
    # Content context
    content_category: Optional[str] = None
    priming_effect: Optional[Dict[str, float]] = None


class InferenceResult(BaseModel):
    """Result of inference processing."""
    
    tier_used: InferenceTier
    mechanisms: List[MechanismSelection]
    context: DecisionContext
    confidence: float = Field(ge=0.0, le=1.0)
    latency_ms: float
    
    # Attribution
    cache_hit: bool = False
    profile_available: bool = True


class InferenceResponse(BaseModel):
    """Full inference response."""
    
    request_id: str
    user_id: str
    
    # Decision
    result: InferenceResult
    
    # Recommendations
    recommended_creative_type: Optional[str] = None
    recommended_framing: Optional[str] = None  # gain, loss, balanced
    recommended_construal: Optional[str] = None  # abstract, concrete
    
    # Metadata
    processing_time_ms: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Learning
    attribution_id: str = Field(default_factory=lambda: f"attr_{uuid4().hex[:12]}")


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery
