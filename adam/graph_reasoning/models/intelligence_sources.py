# =============================================================================
# ADAM Intelligence Source Models
# Location: adam/graph_reasoning/models/intelligence_sources.py
# =============================================================================

"""
THE 10 INTELLIGENCE SOURCES

Each source represents a distinct form of knowledge in ADAM's cognitive ecology.
Sources write to the graph and are available to every reasoning process.

1. Claude Reasoning - Theory-driven psychological reasoning
2. Empirical Patterns - Correlation-first discoveries from data
3. Nonconscious Signals - Behavioral signatures revealing hidden states
4. Graph Emergence - Structural insights from graph traversals
5. Bandit Posteriors - Exploration-exploitation learned effectiveness
6. Meta-Learner Routing - Which paths work for which situations
7. Mechanism Trajectories - Causal attribution of mechanism effectiveness
8. Temporal Patterns - Time-based patterns and decay curves
9. Cross-Domain Transfer - Hidden constructs that transfer across domains
10. Cohort Organization - Emergent segments not anticipated a priori
"""

from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# ENUMS
# =============================================================================

class IntelligenceSourceType(str, Enum):
    """The 10 intelligence sources in ADAM's cognitive ecology."""
    
    CLAUDE_REASONING = "claude_reasoning"
    EMPIRICAL_PATTERNS = "empirical_patterns"
    NONCONSCIOUS_SIGNALS = "nonconscious_signals"
    GRAPH_EMERGENCE = "graph_emergence"
    BANDIT_POSTERIORS = "bandit_posteriors"
    META_LEARNER = "meta_learner"
    MECHANISM_TRAJECTORIES = "mechanism_trajectories"
    TEMPORAL_PATTERNS = "temporal_patterns"
    CROSS_DOMAIN_TRANSFER = "cross_domain_transfer"
    COHORT_ORGANIZATION = "cohort_organization"


class ConfidenceSemantics(str, Enum):
    """Different sources have different confidence semantics."""
    
    SELF_REPORTED = "self_reported"          # Claude's self-assessment
    STATISTICAL = "statistical"              # From sample size and variance
    SIGNAL_STRENGTH = "signal_strength"      # Behavioral measurement strength
    SUPPORT_COUNT = "support_count"          # Graph traversal support
    POSTERIOR_DISTRIBUTION = "posterior"     # Bayesian posterior
    EFFECT_SIZE = "effect_size"              # Causal attribution
    TEMPORAL_ADJUSTED = "temporal_adjusted"  # Time-decay adjusted
    TRANSFER_LIFT = "transfer_lift"          # Cross-domain testing
    CLUSTER_PURITY = "cluster_purity"        # Cohort analysis


class UpdateFrequency(str, Enum):
    """How often this source gets updated."""
    
    PER_REQUEST = "per_request"
    PER_OUTCOME = "per_outcome"
    REAL_TIME = "real_time"
    BATCH_DAILY = "batch_daily"
    BATCH_WEEKLY = "batch_weekly"


# =============================================================================
# BASE MODEL
# =============================================================================

class IntelligenceSourceBase(BaseModel):
    """
    Base class for all intelligence source evidence.
    
    Every piece of evidence in ADAM's cognitive ecology inherits from this,
    ensuring consistent provenance tracking and confidence semantics.
    """
    
    # Unique identifier
    evidence_id: str = Field(
        default_factory=lambda: f"evid_{uuid4().hex[:12]}"
    )
    
    # Source identification
    source_type: IntelligenceSourceType
    source_version: str = Field(default="1.0")
    
    # Provenance
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    # Confidence with semantics
    confidence: float = Field(..., ge=0.0, le=1.0)
    confidence_semantics: ConfidenceSemantics
    confidence_justification: str = Field(default="")
    
    # Update characteristics
    update_frequency: UpdateFrequency
    last_validated: Optional[datetime] = None
    validation_count: int = Field(default=0)
    
    # Decay tracking
    decay_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    valid_until: Optional[datetime] = None
    
    # Conflict tracking
    conflicts_with: List[str] = Field(default_factory=list)
    conflict_resolution_id: Optional[str] = None
    
    @field_validator("confidence")
    @classmethod
    def round_confidence(cls, v: float) -> float:
        return round(v, 4)
    
    def compute_current_confidence(self) -> float:
        """Compute time-decayed confidence."""
        if self.decay_rate == 0.0:
            return self.confidence
        
        age_hours = (
            datetime.now(timezone.utc) - self.created_at
        ).total_seconds() / 3600
        
        decay_factor = (1 - self.decay_rate) ** (age_hours / 24)
        return round(self.confidence * decay_factor, 4)
    
    def is_valid(self) -> bool:
        """Check if this evidence is still temporally valid."""
        if self.valid_until is None:
            return True
        return datetime.now(timezone.utc) < self.valid_until


# =============================================================================
# SOURCE 1: CLAUDE REASONING
# =============================================================================

class ClaudeReasoningEvidence(IntelligenceSourceBase):
    """
    Evidence from Claude's explicit psychological reasoning.
    
    Theory-driven, explainable, grounded in academic psychology.
    """
    
    source_type: IntelligenceSourceType = IntelligenceSourceType.CLAUDE_REASONING
    confidence_semantics: ConfidenceSemantics = ConfidenceSemantics.SELF_REPORTED
    update_frequency: UpdateFrequency = UpdateFrequency.PER_REQUEST
    
    # Reasoning content
    reasoning_chain: List[str] = Field(default_factory=list)
    psychological_constructs: List[str] = Field(default_factory=list)
    research_citations: List[str] = Field(default_factory=list)
    
    # Mechanism recommendations
    recommended_mechanisms: List[str] = Field(default_factory=list)
    mechanism_justifications: Dict[str, str] = Field(default_factory=dict)
    
    # Inference outputs
    inferred_traits: Dict[str, float] = Field(default_factory=dict)
    inferred_states: Dict[str, float] = Field(default_factory=dict)
    
    # Context
    request_id: Optional[str] = None
    user_id: Optional[str] = None
    prompt_version: str = Field(default="1.0")


# =============================================================================
# SOURCE 2: EMPIRICAL PATTERNS
# =============================================================================

class EmpiricalPatternEvidence(IntelligenceSourceBase):
    """
    Evidence from empirically-discovered behavioral patterns.
    
    Emerges from outcome data analysis without LLM involvement.
    """
    
    source_type: IntelligenceSourceType = IntelligenceSourceType.EMPIRICAL_PATTERNS
    confidence_semantics: ConfidenceSemantics = ConfidenceSemantics.STATISTICAL
    update_frequency: UpdateFrequency = UpdateFrequency.BATCH_DAILY
    
    # Pattern definition
    pattern_id: str = Field(default_factory=lambda: f"pat_{uuid4().hex[:8]}")
    pattern_name: str
    pattern_description: str
    
    # Statistical properties
    sample_size: int = Field(ge=0)
    effect_size: float = Field(ge=0.0)
    p_value: Optional[float] = Field(None, ge=0.0, le=1.0)
    ci_lower: Optional[float] = None
    ci_upper: Optional[float] = None
    
    # Behavioral sequence
    behavioral_sequence: List[str] = Field(default_factory=list)
    
    # Outcome association
    outcome_type: str = "conversion"
    outcome_lift: float = Field(default=0.0)
    
    # Applicable context
    applicable_categories: List[str] = Field(default_factory=list)
    applicable_segments: List[str] = Field(default_factory=list)
    
    # Mining metadata
    mining_algorithm: str = Field(default="frequent_pattern")
    discovery_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# =============================================================================
# SOURCE 3: NONCONSCIOUS SIGNALS
# =============================================================================

class NonconsciousSignalEvidence(IntelligenceSourceBase):
    """
    Evidence from behavioral signatures revealing hidden psychological states.
    
    This is ADAM's proprietary analytics layer - signals users aren't
    consciously aware they're exhibiting.
    """
    
    source_type: IntelligenceSourceType = IntelligenceSourceType.NONCONSCIOUS_SIGNALS
    confidence_semantics: ConfidenceSemantics = ConfidenceSemantics.SIGNAL_STRENGTH
    update_frequency: UpdateFrequency = UpdateFrequency.REAL_TIME
    
    # Signal identification
    signal_id: str = Field(default_factory=lambda: f"sig_{uuid4().hex[:8]}")
    signal_type: str  # e.g., "scroll_velocity", "mouse_hesitation"
    signal_name: str
    
    # Measurement
    raw_value: float
    normalized_value: float = Field(ge=0.0, le=1.0)
    measurement_window_seconds: float = Field(default=60.0)
    
    # Psychological mapping
    maps_to_construct: str  # e.g., "cognitive_load", "decision_conflict"
    mapping_confidence: float = Field(ge=0.0, le=1.0)
    mapping_research_basis: Optional[str] = None
    
    # User context
    user_id: str
    session_id: Optional[str] = None
    
    # Signal categories
    is_arousal_signal: bool = False
    is_attention_signal: bool = False
    is_conflict_signal: bool = False
    is_engagement_signal: bool = False


# =============================================================================
# SOURCE 4: GRAPH EMERGENCE
# =============================================================================

class GraphEmergenceEvidence(IntelligenceSourceBase):
    """
    Evidence from graph-structural patterns discovered through traversal.
    
    Neo4j isn't just storage—it's a reasoning substrate.
    """
    
    source_type: IntelligenceSourceType = IntelligenceSourceType.GRAPH_EMERGENCE
    confidence_semantics: ConfidenceSemantics = ConfidenceSemantics.SUPPORT_COUNT
    update_frequency: UpdateFrequency = UpdateFrequency.BATCH_DAILY
    
    # Pattern identification
    emergence_id: str = Field(default_factory=lambda: f"emrg_{uuid4().hex[:8]}")
    pattern_type: str  # e.g., "co-occurrence", "path_pattern"
    pattern_description: str
    
    # Cypher representation
    discovery_query: str
    node_types_involved: List[str] = Field(default_factory=list)
    relationship_types_involved: List[str] = Field(default_factory=list)
    
    # Support metrics
    support_count: int = Field(ge=0)
    total_population: int = Field(ge=1)
    support_ratio: float = Field(ge=0.0, le=1.0)
    
    # Inference
    inferred_relationship: str
    inference_strength: float = Field(ge=0.0, le=1.0)
    
    # Discovery metadata
    discovery_algorithm: str = Field(default="graph_mining")
    discovery_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# =============================================================================
# SOURCE 5: BANDIT POSTERIORS
# =============================================================================

class BanditPosteriorEvidence(IntelligenceSourceBase):
    """
    Evidence from Thompson Sampling bandit posteriors.
    
    After thousands of trials, bandits "know" what works for which contexts.
    """
    
    source_type: IntelligenceSourceType = IntelligenceSourceType.BANDIT_POSTERIORS
    confidence_semantics: ConfidenceSemantics = ConfidenceSemantics.POSTERIOR_DISTRIBUTION
    update_frequency: UpdateFrequency = UpdateFrequency.PER_OUTCOME
    
    # Bandit identification
    bandit_id: str
    arm_id: str
    arm_name: str
    
    # Posterior parameters (Beta distribution)
    alpha: float = Field(ge=0.0)
    beta: float = Field(ge=0.0)
    
    # Derived metrics
    posterior_mean: float = Field(ge=0.0, le=1.0)
    posterior_variance: float = Field(ge=0.0)
    
    # Trial history
    trial_count: int = Field(ge=0)
    success_count: int = Field(ge=0)
    
    # Context
    context_features: Dict[str, Any] = Field(default_factory=dict)
    
    # Comparison
    relative_rank: Optional[int] = None
    probability_best: float = Field(default=0.0, ge=0.0, le=1.0)


# =============================================================================
# SOURCE 6: META-LEARNER ROUTING
# =============================================================================

class MetaLearnerEvidence(IntelligenceSourceBase):
    """
    Evidence about which execution paths work for which situations.
    
    The meta-learner learns about learning itself.
    """
    
    source_type: IntelligenceSourceType = IntelligenceSourceType.META_LEARNER
    confidence_semantics: ConfidenceSemantics = ConfidenceSemantics.EFFECT_SIZE
    update_frequency: UpdateFrequency = UpdateFrequency.PER_OUTCOME
    
    # Routing decision
    routing_id: str = Field(default_factory=lambda: f"route_{uuid4().hex[:8]}")
    source_path: str
    target_path: str
    
    # Context that triggered routing
    routing_context: Dict[str, Any] = Field(default_factory=dict)
    
    # Effectiveness
    path_success_rate: float = Field(ge=0.0, le=1.0)
    path_trial_count: int = Field(ge=0)
    
    # Recommendation
    recommended_path: str
    recommendation_strength: float = Field(ge=0.0, le=1.0)


# =============================================================================
# SOURCE 7: MECHANISM TRAJECTORIES
# =============================================================================

class MechanismTrajectoryEvidence(IntelligenceSourceBase):
    """
    Evidence from causal attribution of mechanism effectiveness.
    
    Tracks which of the 9 mechanisms actually drove conversion.
    """
    
    source_type: IntelligenceSourceType = IntelligenceSourceType.MECHANISM_TRAJECTORIES
    confidence_semantics: ConfidenceSemantics = ConfidenceSemantics.EFFECT_SIZE
    update_frequency: UpdateFrequency = UpdateFrequency.PER_OUTCOME
    
    # Mechanism
    mechanism_id: str
    mechanism_name: str
    
    # Context
    user_segment: Optional[str] = None
    product_category: Optional[str] = None
    
    # Effectiveness metrics
    success_rate: float = Field(ge=0.0, le=1.0)
    effect_size: float = Field(ge=0.0)
    trial_count: int = Field(ge=0)
    
    # Trajectory (how effectiveness changed over time)
    trajectory_points: List[Dict[str, Any]] = Field(default_factory=list)
    trend_direction: str = Field(default="stable")  # "increasing", "decreasing", "stable"
    trend_strength: float = Field(default=0.0, ge=0.0, le=1.0)


# =============================================================================
# SOURCE 8: TEMPORAL PATTERNS
# =============================================================================

class TemporalPatternEvidence(IntelligenceSourceBase):
    """
    Evidence from time-based patterns.
    
    When does what work? How do effects decay?
    """
    
    source_type: IntelligenceSourceType = IntelligenceSourceType.TEMPORAL_PATTERNS
    confidence_semantics: ConfidenceSemantics = ConfidenceSemantics.TEMPORAL_ADJUSTED
    update_frequency: UpdateFrequency = UpdateFrequency.BATCH_DAILY
    
    # Pattern identification
    temporal_pattern_id: str = Field(default_factory=lambda: f"temp_{uuid4().hex[:8]}")
    pattern_type: str  # "day_of_week", "time_of_day", "decay_curve", "seasonality"
    
    # Temporal specification
    time_granularity: str = Field(default="hour")  # "minute", "hour", "day", "week"
    time_windows: List[str] = Field(default_factory=list)
    
    # Effect by time
    effectiveness_by_window: Dict[str, float] = Field(default_factory=dict)
    peak_windows: List[str] = Field(default_factory=list)
    
    # Decay parameters (if decay pattern)
    decay_function: Optional[str] = None  # "exponential", "power_law"
    decay_rate: Optional[float] = None
    half_life_hours: Optional[float] = None


# =============================================================================
# SOURCE 9: CROSS-DOMAIN TRANSFER
# =============================================================================

class CrossDomainTransferEvidence(IntelligenceSourceBase):
    """
    Evidence from patterns that transfer across domains.
    
    Reveals hidden psychological constructs.
    """
    
    source_type: IntelligenceSourceType = IntelligenceSourceType.CROSS_DOMAIN_TRANSFER
    confidence_semantics: ConfidenceSemantics = ConfidenceSemantics.TRANSFER_LIFT
    update_frequency: UpdateFrequency = UpdateFrequency.BATCH_WEEKLY
    
    # Transfer identification
    transfer_id: str = Field(default_factory=lambda: f"xfer_{uuid4().hex[:8]}")
    
    # Domains
    source_domain: str
    target_domain: str
    
    # Pattern that transfers
    pattern_description: str
    underlying_construct: str  # The latent construct enabling transfer
    
    # Transfer metrics
    transfer_lift: float  # How much the pattern helps in target domain
    source_domain_effect: float
    target_domain_effect: float
    
    # Validation
    validated_in_domains: List[str] = Field(default_factory=list)


# =============================================================================
# SOURCE 10: COHORT ORGANIZATION
# =============================================================================

class CohortOrganizationEvidence(IntelligenceSourceBase):
    """
    Evidence from emergent cohorts that self-organize.
    
    Segments no one anticipated that emerge from behavioral similarity.
    """
    
    source_type: IntelligenceSourceType = IntelligenceSourceType.COHORT_ORGANIZATION
    confidence_semantics: ConfidenceSemantics = ConfidenceSemantics.CLUSTER_PURITY
    update_frequency: UpdateFrequency = UpdateFrequency.BATCH_WEEKLY
    
    # Cohort identification
    cohort_id: str = Field(default_factory=lambda: f"coh_{uuid4().hex[:8]}")
    cohort_name: str
    cohort_description: str
    
    # Cluster metrics
    cluster_size: int = Field(ge=0)
    cluster_purity: float = Field(ge=0.0, le=1.0)
    silhouette_score: float = Field(ge=-1.0, le=1.0)
    
    # Defining characteristics
    defining_features: List[str] = Field(default_factory=list)
    centroid_traits: Dict[str, float] = Field(default_factory=dict)
    
    # Mechanism preferences
    preferred_mechanisms: List[str] = Field(default_factory=list)
    mechanism_effectiveness: Dict[str, float] = Field(default_factory=dict)
    
    # Member samples (for validation)
    sample_member_ids: List[str] = Field(default_factory=list)


# =============================================================================
# MULTI-SOURCE EVIDENCE PACKAGE
# =============================================================================

class MultiSourceEvidencePackage(BaseModel):
    """
    Aggregated evidence from all available sources for a decision.
    
    This is what gets passed to the Evidence Synthesis Engine.
    """
    
    package_id: str = Field(default_factory=lambda: f"pkg_{uuid4().hex[:12]}")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    # Request context
    request_id: str
    user_id: str
    
    # Evidence from each source (may be empty if source unavailable)
    claude_reasoning: Optional[ClaudeReasoningEvidence] = None
    empirical_patterns: List[EmpiricalPatternEvidence] = Field(default_factory=list)
    nonconscious_signals: List[NonconsciousSignalEvidence] = Field(default_factory=list)
    graph_emergence: List[GraphEmergenceEvidence] = Field(default_factory=list)
    bandit_posteriors: List[BanditPosteriorEvidence] = Field(default_factory=list)
    meta_learner: Optional[MetaLearnerEvidence] = None
    mechanism_trajectories: List[MechanismTrajectoryEvidence] = Field(default_factory=list)
    temporal_patterns: List[TemporalPatternEvidence] = Field(default_factory=list)
    cross_domain_transfer: List[CrossDomainTransferEvidence] = Field(default_factory=list)
    cohort_organization: Optional[CohortOrganizationEvidence] = None
    
    # Synthesis metadata
    sources_available: List[IntelligenceSourceType] = Field(default_factory=list)
    sources_unavailable: List[IntelligenceSourceType] = Field(default_factory=list)
    total_evidence_count: int = Field(default=0)
    
    def count_evidence(self) -> int:
        """Count total pieces of evidence."""
        count = 0
        if self.claude_reasoning:
            count += 1
        count += len(self.empirical_patterns)
        count += len(self.nonconscious_signals)
        count += len(self.graph_emergence)
        count += len(self.bandit_posteriors)
        if self.meta_learner:
            count += 1
        count += len(self.mechanism_trajectories)
        count += len(self.temporal_patterns)
        count += len(self.cross_domain_transfer)
        if self.cohort_organization:
            count += 1
        self.total_evidence_count = count
        return count
