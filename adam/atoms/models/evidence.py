# =============================================================================
# ADAM Intelligence Evidence Models
# Location: adam/atoms/models/evidence.py
# =============================================================================

"""
INTELLIGENCE EVIDENCE MODELS

Models for representing evidence from the 10 intelligence sources
and fusing them into coherent assessments.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from adam.graph_reasoning.models.intelligence_sources import (
    IntelligenceSourceType,
    ConfidenceSemantics,
)


# =============================================================================
# EVIDENCE FROM A SINGLE SOURCE
# =============================================================================

class EvidenceStrength(str, Enum):
    """Strength of evidence from a source."""
    
    NONE = "none"           # Source has no relevant evidence
    WEAK = "weak"           # Low confidence or low support
    MODERATE = "moderate"   # Medium confidence/support
    STRONG = "strong"       # High confidence/support
    VERY_STRONG = "very_strong"  # Very high, statistically validated


class IntelligenceEvidence(BaseModel):
    """
    Evidence from a single intelligence source.
    
    Each source provides evidence with different semantics:
    - Claude: Self-reported confidence from reasoning
    - Empirical: Statistical significance and effect size
    - Bandit: Posterior distribution parameters
    - etc.
    """
    
    model_config = {"populate_by_name": True}
    
    evidence_id: str = Field(
        default_factory=lambda: f"evi_{uuid4().hex[:12]}"
    )
    
    # Source identification
    source_type: IntelligenceSourceType
    source_id: str = ""  # Specific source instance
    
    # Evidence content
    psychological_construct: str = Field(
        ..., alias="construct",
        description="What psychological construct this evidences"
    )
    assessment: str  # The assessment value (e.g., "promotion", "high", "0.73")
    assessment_value: Optional[float] = None  # Numeric value if applicable
    
    # Confidence (meaning depends on source)
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    confidence_semantics: ConfidenceSemantics = ConfidenceSemantics.SELF_REPORTED
    
    # Evidence strength
    strength: EvidenceStrength = Field(default=EvidenceStrength.MODERATE)
    
    # Support metrics (source-specific)
    support_count: Optional[int] = None  # Sample size, observation count
    effect_size: Optional[float] = None  # Cohen's d, lift, etc.
    p_value: Optional[float] = None  # Statistical significance
    
    # Reasoning/justification
    reasoning: str = ""
    evidence_items: List[str] = Field(default_factory=list)
    
    # Freshness
    observed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    staleness_hours: float = Field(default=0.0, ge=0.0)
    
    @property
    def is_fresh(self) -> bool:
        """Check if evidence is fresh (< 24 hours)."""
        return self.staleness_hours < 24.0
    
    @property
    def weighted_confidence(self) -> float:
        """Confidence weighted by strength and freshness."""
        strength_weights = {
            EvidenceStrength.NONE: 0.0,
            EvidenceStrength.WEAK: 0.5,
            EvidenceStrength.MODERATE: 0.75,
            EvidenceStrength.STRONG: 0.9,
            EvidenceStrength.VERY_STRONG: 1.0,
        }
        strength_factor = strength_weights.get(self.strength, 0.5)
        freshness_factor = max(0.5, 1.0 - (self.staleness_hours / 168.0))  # Decay over week
        return self.confidence * strength_factor * freshness_factor


# =============================================================================
# MULTI-SOURCE EVIDENCE
# =============================================================================

class MultiSourceEvidence(BaseModel):
    """
    Evidence aggregated from multiple intelligence sources.
    
    This is the input to the fusion process.
    """
    
    model_config = {"populate_by_name": True}
    
    package_id: str = Field(
        default_factory=lambda: f"mse_{uuid4().hex[:12]}"
    )
    
    # Target construct
    psychological_construct: str = Field(
        ..., alias="construct",
        description="e.g., 'regulatory_focus', 'construal_level'"
    )
    
    # Evidence from each source
    evidence: Dict[IntelligenceSourceType, IntelligenceEvidence] = Field(
        default_factory=dict
    )
    
    # Summary
    sources_queried: List[IntelligenceSourceType] = Field(default_factory=list)
    sources_with_evidence: List[IntelligenceSourceType] = Field(default_factory=list)
    sources_without_evidence: List[IntelligenceSourceType] = Field(default_factory=list)
    
    # Timing
    query_latency_ms: float = Field(default=0.0, ge=0.0)
    
    def add_evidence(self, evidence: IntelligenceEvidence) -> None:
        """Add evidence from a source."""
        self.evidence[evidence.source_type] = evidence
        if evidence.source_type not in self.sources_with_evidence:
            self.sources_with_evidence.append(evidence.source_type)
    
    def get_evidence(self, source: IntelligenceSourceType) -> Optional[IntelligenceEvidence]:
        """Get evidence from a specific source."""
        return self.evidence.get(source)
    
    @property
    def total_sources(self) -> int:
        """Number of sources with evidence."""
        return len(self.sources_with_evidence)
    
    @property
    def average_confidence(self) -> float:
        """Average confidence across sources."""
        if not self.evidence:
            return 0.5
        confidences = [e.confidence for e in self.evidence.values()]
        return sum(confidences) / len(confidences)
    
    @property
    def max_confidence(self) -> float:
        """Maximum confidence across sources."""
        if not self.evidence:
            return 0.5
        return max(e.confidence for e in self.evidence.values())


# =============================================================================
# EVIDENCE CONFLICT
# =============================================================================

class ConflictSeverity(str, Enum):
    """Severity of conflict between sources."""
    
    NONE = "none"           # Sources agree
    MINOR = "minor"         # Small disagreement, low confidence
    MODERATE = "moderate"   # Notable disagreement
    MAJOR = "major"         # Strong disagreement, needs resolution
    CRITICAL = "critical"   # Fundamental contradiction


class EvidenceConflict(BaseModel):
    """
    A detected conflict between intelligence sources.
    
    Conflicts are learning opportunities - they indicate either:
    - Different sources see different aspects of reality
    - Theory and empirical data diverge
    - Stale information needs updating
    """
    
    model_config = {"populate_by_name": True}
    
    conflict_id: str = Field(
        default_factory=lambda: f"con_{uuid4().hex[:12]}"
    )
    
    # Conflicting sources
    source_a: IntelligenceSourceType
    source_b: IntelligenceSourceType
    
    # What's conflicting
    psychological_construct: str = Field(..., alias="construct")
    assessment_a: str
    assessment_b: str
    confidence_a: float = Field(ge=0.0, le=1.0)
    confidence_b: float = Field(ge=0.0, le=1.0)
    
    # Conflict analysis
    severity: ConflictSeverity = Field(default=ConflictSeverity.MODERATE)
    conflict_type: str = ""  # "theory_vs_data", "stale_data", "different_signals"
    
    # Resolution
    resolved: bool = Field(default=False)
    resolution: Optional[str] = None
    resolution_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    resolution_explanation: str = ""
    
    @property
    def is_theory_vs_data(self) -> bool:
        """Check if this is a theory vs empirical data conflict."""
        theory_sources = {IntelligenceSourceType.CLAUDE_REASONING}
        data_sources = {
            IntelligenceSourceType.EMPIRICAL_PATTERNS,
            IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
            IntelligenceSourceType.BANDIT_POSTERIORS,
        }
        return (
            (self.source_a in theory_sources and self.source_b in data_sources) or
            (self.source_b in theory_sources and self.source_a in data_sources)
        )


# =============================================================================
# FUSION RESULT
# =============================================================================

class FusionResult(BaseModel):
    """
    Result of fusing evidence from multiple sources.
    
    Contains the synthesized assessment and the reasoning behind it.
    """
    
    model_config = {"populate_by_name": True}
    
    result_id: str = Field(
        default_factory=lambda: f"fus_{uuid4().hex[:12]}"
    )
    
    # Target construct
    psychological_construct: str = Field(..., alias="construct")
    
    # Fused assessment
    assessment: str  # e.g., "promotion", "concrete", "0.73"
    assessment_value: Optional[float] = None
    
    # Confidence (calibrated across source types)
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_interval: tuple = Field(default=(0.0, 1.0))
    
    # Source contribution
    sources_used: List[IntelligenceSourceType] = Field(default_factory=list)
    source_weights: Dict[str, float] = Field(default_factory=dict)
    primary_source: Optional[IntelligenceSourceType] = None
    
    # Conflicts detected and resolved
    conflicts_detected: List[EvidenceConflict] = Field(default_factory=list)
    conflicts_resolved: int = Field(default=0, ge=0)
    conflicts_unresolved: int = Field(default=0, ge=0)
    
    # Claude's synthesis (if used)
    claude_used: bool = Field(default=False)
    claude_synthesis: str = ""
    claude_tokens_in: int = Field(default=0, ge=0)
    claude_tokens_out: int = Field(default=0, ge=0)
    
    # Learning signals generated
    learning_signals: List[str] = Field(default_factory=list)
    
    # Timing
    fusion_latency_ms: float = Field(default=0.0, ge=0.0)
    
    @property
    def agreement_level(self) -> float:
        """How much sources agreed (1.0 = full agreement)."""
        if not self.conflicts_detected:
            return 1.0
        total = len(self.conflicts_detected)
        resolved = self.conflicts_resolved
        return resolved / total if total > 0 else 1.0
