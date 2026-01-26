# =============================================================================
# ADAM Explanation Models (#18)
# Location: adam/explanation/models.py
# =============================================================================

"""
EXPLANATION DATA MODELS

Pydantic models for decision explanations and transparency.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ExplanationAudience(str, Enum):
    """Target audience for explanation."""
    USER = "user"
    ADVERTISER = "advertiser"
    DATA_SCIENTIST = "data_scientist"
    ENGINEER = "engineer"
    REGULATOR = "regulator"


class ExplanationDetail(str, Enum):
    """Level of detail in explanation."""
    SUMMARY = "summary"
    STANDARD = "standard"
    DETAILED = "detailed"
    DEBUG = "debug"


class MechanismExplanation(BaseModel):
    """Explanation of mechanism selection."""
    
    mechanism: str
    score: float
    human_description: str
    rationale: str
    
    # Scientific backing
    research_reference: Optional[str] = None
    effectiveness_history: Optional[float] = None


class ProfileContribution(BaseModel):
    """How profile contributed to decision."""
    
    trait: str
    value: float
    contribution_weight: float
    influence_description: str


class DecisionTrace(BaseModel):
    """Full trace of decision logic."""
    
    trace_id: str = Field(default_factory=lambda: f"trace_{uuid4().hex[:12]}")
    decision_id: str
    
    # Steps
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Timing
    total_latency_ms: float
    per_step_latency: Dict[str, float] = Field(default_factory=dict)
    
    # Data sources used
    data_sources: List[str] = Field(default_factory=list)
    
    # Confidence breakdown
    confidence_factors: Dict[str, float] = Field(default_factory=dict)


class Explanation(BaseModel):
    """Complete explanation of a decision."""
    
    explanation_id: str = Field(default_factory=lambda: f"expl_{uuid4().hex[:12]}")
    decision_id: str
    user_id: Optional[str] = None
    
    # Target
    audience: ExplanationAudience = ExplanationAudience.ADVERTISER
    detail_level: ExplanationDetail = ExplanationDetail.STANDARD
    
    # Content
    summary: str
    reasoning: str
    
    # Mechanism explanations
    mechanisms: List[MechanismExplanation] = Field(default_factory=list)
    
    # Profile contributions
    profile_contributions: List[ProfileContribution] = Field(default_factory=list)
    
    # Full trace (if detailed)
    trace: Optional[DecisionTrace] = None
    
    # Metadata
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    generation_time_ms: Optional[float] = None


class ComplianceReport(BaseModel):
    """GDPR/CCPA compliance report."""
    
    report_id: str = Field(default_factory=lambda: f"comp_{uuid4().hex[:12]}")
    user_id: str
    
    # Data usage
    data_categories_used: List[str] = Field(default_factory=list)
    processing_purposes: List[str] = Field(default_factory=list)
    
    # Consent
    consent_basis: str = "legitimate_interest"
    consent_timestamp: Optional[datetime] = None
    
    # Decisions made
    decision_count: int = 0
    decisions_explained: int = 0
    
    # Generated
    report_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
