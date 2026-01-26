# =============================================================================
# ADAM Meta-Learner Data Models
# Location: adam/meta_learner/models.py
# =============================================================================

"""
Type-safe data models for the Meta-Learning Orchestration system.

All models use Pydantic for validation and serialization,
ensuring type safety across the entire meta-learner pipeline.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

import numpy as np
from pydantic import BaseModel, Field


# =============================================================================
# ENUMS
# =============================================================================

class LearningModality(str, Enum):
    """
    All learning approaches ADAM can use.
    
    Each modality represents a different strategy for making
    ad decisions, with different data requirements and latencies.
    """
    # Supervised learning (requires historical labels)
    SUPERVISED_CONVERSION = "supervised_conversion"
    SUPERVISED_ENGAGEMENT = "supervised_engagement"
    
    # Reinforcement learning (exploration-exploitation)
    REINFORCEMENT_BANDIT = "bandit"
    REINFORCEMENT_CONTEXTUAL_BANDIT = "contextual_bandit"
    
    # Unsupervised learning (pattern discovery)
    UNSUPERVISED_CLUSTERING = "clustering"
    UNSUPERVISED_GRAPH_EMBEDDING = "graph_embedding"
    
    # Causal/contrastive learning (deep understanding)
    CAUSAL_INFERENCE = "causal"
    SELF_SUPERVISED_CONTRASTIVE = "contrastive"


class ExecutionPath(str, Enum):
    """
    Execution paths in LangGraph workflow.
    
    Each path has different latency characteristics and compute costs.
    """
    FAST_PATH = "fast"           # Cache, archetype, graph lookup (<50ms)
    REASONING_PATH = "reasoning"  # Full Claude + AoT (500ms-2s)
    EXPLORATION_PATH = "explore"  # Bandit exploration (<100ms)


# Mapping from modality to execution path
MODALITY_TO_PATH: Dict[LearningModality, ExecutionPath] = {
    # FAST_PATH: Exploit known patterns
    LearningModality.SUPERVISED_CONVERSION: ExecutionPath.FAST_PATH,
    LearningModality.SUPERVISED_ENGAGEMENT: ExecutionPath.FAST_PATH,
    LearningModality.UNSUPERVISED_CLUSTERING: ExecutionPath.FAST_PATH,
    LearningModality.UNSUPERVISED_GRAPH_EMBEDDING: ExecutionPath.FAST_PATH,
    
    # REASONING_PATH: Complex reasoning required
    LearningModality.CAUSAL_INFERENCE: ExecutionPath.REASONING_PATH,
    LearningModality.SELF_SUPERVISED_CONTRASTIVE: ExecutionPath.REASONING_PATH,
    
    # EXPLORATION_PATH: Explore-exploit tradeoff
    LearningModality.REINFORCEMENT_BANDIT: ExecutionPath.EXPLORATION_PATH,
    LearningModality.REINFORCEMENT_CONTEXTUAL_BANDIT: ExecutionPath.EXPLORATION_PATH,
}


# =============================================================================
# POSTERIOR DISTRIBUTION
# =============================================================================

class ModalityPosterior(BaseModel):
    """
    Beta posterior distribution for a modality's performance.
    
    Uses Beta(α, β) distribution for binary rewards (converted/not converted).
    Thompson Sampling samples from this posterior to balance exploration/exploitation.
    
    Properties:
    - mean = α / (α + β)
    - variance = αβ / ((α + β)² × (α + β + 1))
    - Higher α → more successes observed
    - Higher β → more failures observed
    """
    modality: LearningModality
    alpha: float = Field(default=1.0, ge=0.1, description="Success count + prior")
    beta: float = Field(default=1.0, ge=0.1, description="Failure count + prior")
    sample_count: int = Field(default=0, ge=0, description="Total observations")
    recent_rewards: List[float] = Field(default_factory=list, description="Last 100 rewards")
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    @property
    def mean(self) -> float:
        """Expected value of the posterior."""
        return self.alpha / (self.alpha + self.beta)
    
    @property
    def variance(self) -> float:
        """Variance of the posterior."""
        a, b = self.alpha, self.beta
        return (a * b) / ((a + b) ** 2 * (a + b + 1))
    
    @property
    def confidence(self) -> float:
        """Confidence in the estimate (inverse of variance, normalized)."""
        return 1.0 / (1.0 + self.variance * 100)
    
    def sample(self) -> float:
        """Sample from Beta posterior (Thompson Sampling)."""
        return float(np.random.beta(self.alpha, self.beta))
    
    def update(self, reward: float) -> None:
        """
        Update posterior with observed reward.
        
        Args:
            reward: Observed reward (0-1 for partial, 0/1 for binary)
        """
        # Update alpha/beta (reward interpreted as probability of success)
        self.alpha += reward
        self.beta += (1 - reward)
        self.sample_count += 1
        
        # Track recent rewards (sliding window)
        self.recent_rewards.append(reward)
        if len(self.recent_rewards) > 100:
            self.recent_rewards.pop(0)
        
        self.last_updated = datetime.now(timezone.utc)
    
    def decay(self, factor: float = 0.995) -> None:
        """
        Apply decay to allow adaptation to changing environments.
        
        Shrinks alpha and beta toward prior (1,1) to forget old data.
        """
        prior = 1.0
        self.alpha = prior + (self.alpha - prior) * factor
        self.beta = prior + (self.beta - prior) * factor


# =============================================================================
# CONTEXT FEATURES
# =============================================================================

class DataRichness(str, Enum):
    """User data richness levels."""
    COLD_START = "cold_start"      # No history
    SPARSE = "sparse"              # <10 interactions
    MODERATE = "moderate"          # 10-50 interactions
    RICH = "rich"                  # >50 interactions


class ContextNovelty(str, Enum):
    """How novel is the current context."""
    FAMILIAR = "familiar"          # Seen this context often
    SOMEWHAT_NOVEL = "somewhat_novel"  # Some new elements
    HIGHLY_NOVEL = "highly_novel"  # Very new context


class ContextFeatures(BaseModel):
    """
    Features extracted from the current context for routing decisions.
    
    These features determine which modalities are eligible and
    influence the Thompson sampling weights.
    """
    
    # User data richness
    user_id: str
    interaction_count: int = Field(default=0, ge=0)
    conversion_count: int = Field(default=0, ge=0)
    profile_completeness: float = Field(ge=0.0, le=1.0, default=0.0)
    data_richness: DataRichness = Field(default=DataRichness.COLD_START)
    
    # Context novelty
    content_type: str = Field(default="unknown")
    station_format: Optional[str] = None
    context_novelty: ContextNovelty = Field(default=ContextNovelty.FAMILIAR)
    ad_pool_size: int = Field(default=0, ge=0)
    
    # Time features
    time_of_day: int = Field(ge=0, le=23, default=12)
    day_of_week: int = Field(ge=0, le=6, default=0)
    session_depth: int = Field(default=0, ge=0)  # How many decisions in session
    
    # Constraints
    latency_budget_ms: int = Field(default=100, ge=0)
    exploration_allowed: bool = Field(default=True)
    
    # Campaign context
    campaign_mode: str = Field(default="standard")  # "standard", "launch", "test"
    
    @property
    def allows_fast_path(self) -> bool:
        """Check if fast path is viable."""
        return self.data_richness in [DataRichness.MODERATE, DataRichness.RICH]
    
    @property
    def requires_exploration(self) -> bool:
        """Check if exploration is needed."""
        return (
            self.data_richness == DataRichness.COLD_START or
            self.context_novelty == ContextNovelty.HIGHLY_NOVEL
        )
    
    @classmethod
    def from_user_profile(
        cls,
        user_id: str,
        interaction_count: int,
        conversion_count: int,
        profile_completeness: float,
        latency_budget_ms: int = 100,
    ) -> "ContextFeatures":
        """Create from user profile data."""
        # Determine data richness
        if interaction_count == 0:
            richness = DataRichness.COLD_START
        elif interaction_count < 10:
            richness = DataRichness.SPARSE
        elif interaction_count < 50:
            richness = DataRichness.MODERATE
        else:
            richness = DataRichness.RICH
        
        return cls(
            user_id=user_id,
            interaction_count=interaction_count,
            conversion_count=conversion_count,
            profile_completeness=profile_completeness,
            data_richness=richness,
            latency_budget_ms=latency_budget_ms,
        )


# =============================================================================
# MODALITY CONSTRAINTS
# =============================================================================

class ModalityConstraint(BaseModel):
    """
    Constraints that determine modality eligibility.
    
    Each modality has minimum requirements that must be met.
    """
    modality: LearningModality
    
    # Data requirements
    min_interactions: int = Field(default=0, ge=0)
    min_conversions: int = Field(default=0, ge=0)
    min_profile_completeness: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Context requirements
    allowed_data_richness: List[DataRichness] = Field(default_factory=list)
    
    # Latency requirements
    max_latency_ms: int = Field(default=100, ge=0)
    
    # Special flags
    requires_graph_connections: bool = Field(default=False)
    requires_cluster_assignment: bool = Field(default=False)
    requires_exploration_budget: bool = Field(default=False)
    
    def is_satisfied(self, features: ContextFeatures) -> bool:
        """Check if constraints are satisfied by the context."""
        # Check data requirements
        if features.interaction_count < self.min_interactions:
            return False
        if features.conversion_count < self.min_conversions:
            return False
        if features.profile_completeness < self.min_profile_completeness:
            return False
        
        # Check data richness
        if self.allowed_data_richness:
            if features.data_richness not in self.allowed_data_richness:
                return False
        
        # Check latency budget
        if features.latency_budget_ms < self.max_latency_ms:
            return False
        
        # Check exploration
        if self.requires_exploration_budget and not features.exploration_allowed:
            return False
        
        return True


# Default constraints for each modality
DEFAULT_MODALITY_CONSTRAINTS: Dict[LearningModality, ModalityConstraint] = {
    LearningModality.SUPERVISED_CONVERSION: ModalityConstraint(
        modality=LearningModality.SUPERVISED_CONVERSION,
        min_interactions=20,
        min_conversions=3,
        min_profile_completeness=0.5,
        allowed_data_richness=[DataRichness.MODERATE, DataRichness.RICH],
        max_latency_ms=50,
    ),
    LearningModality.SUPERVISED_ENGAGEMENT: ModalityConstraint(
        modality=LearningModality.SUPERVISED_ENGAGEMENT,
        min_interactions=15,
        min_conversions=0,
        min_profile_completeness=0.3,
        allowed_data_richness=[DataRichness.MODERATE, DataRichness.RICH],
        max_latency_ms=50,
    ),
    LearningModality.UNSUPERVISED_CLUSTERING: ModalityConstraint(
        modality=LearningModality.UNSUPERVISED_CLUSTERING,
        min_interactions=5,
        min_profile_completeness=0.2,
        allowed_data_richness=[DataRichness.SPARSE, DataRichness.MODERATE, DataRichness.RICH],
        max_latency_ms=50,
        requires_cluster_assignment=True,
    ),
    LearningModality.UNSUPERVISED_GRAPH_EMBEDDING: ModalityConstraint(
        modality=LearningModality.UNSUPERVISED_GRAPH_EMBEDDING,
        min_interactions=10,
        min_profile_completeness=0.3,
        allowed_data_richness=[DataRichness.MODERATE, DataRichness.RICH],
        max_latency_ms=50,
        requires_graph_connections=True,
    ),
    LearningModality.REINFORCEMENT_BANDIT: ModalityConstraint(
        modality=LearningModality.REINFORCEMENT_BANDIT,
        min_interactions=0,
        allowed_data_richness=[DataRichness.COLD_START, DataRichness.SPARSE],
        max_latency_ms=100,
        requires_exploration_budget=True,
    ),
    LearningModality.REINFORCEMENT_CONTEXTUAL_BANDIT: ModalityConstraint(
        modality=LearningModality.REINFORCEMENT_CONTEXTUAL_BANDIT,
        min_interactions=3,
        allowed_data_richness=[DataRichness.SPARSE, DataRichness.MODERATE],
        max_latency_ms=100,
        requires_exploration_budget=True,
    ),
    LearningModality.CAUSAL_INFERENCE: ModalityConstraint(
        modality=LearningModality.CAUSAL_INFERENCE,
        min_interactions=50,
        min_conversions=10,
        min_profile_completeness=0.7,
        allowed_data_richness=[DataRichness.RICH],
        max_latency_ms=2000,
    ),
    LearningModality.SELF_SUPERVISED_CONTRASTIVE: ModalityConstraint(
        modality=LearningModality.SELF_SUPERVISED_CONTRASTIVE,
        min_interactions=0,
        allowed_data_richness=[DataRichness.COLD_START, DataRichness.SPARSE],
        max_latency_ms=2000,
    ),
}


# =============================================================================
# ROUTING DECISION
# =============================================================================

class RoutingDecision(BaseModel):
    """
    The Meta-Learner's routing decision.
    
    Contains the selected modality, execution path, and
    supporting information for downstream components.
    """
    decision_id: str = Field(
        default_factory=lambda: f"route_{uuid4().hex[:12]}"
    )
    request_id: str
    user_id: str
    
    # Selected routing
    selected_modality: LearningModality
    execution_path: ExecutionPath
    
    # Thompson sampling details
    sampled_values: Dict[str, float] = Field(default_factory=dict)
    adjusted_values: Dict[str, float] = Field(default_factory=dict)
    eligible_modalities: List[LearningModality] = Field(default_factory=list)
    
    # Reasoning
    selection_reason: str = ""
    constraints_failed: Dict[str, List[str]] = Field(default_factory=dict)
    
    # Confidence
    selection_confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    exploration_probability: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Context snapshot
    context_features: Optional[ContextFeatures] = None
    
    # Timing
    decided_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    decision_latency_ms: float = Field(ge=0.0, default=0.0)
    
    def get_path_latency_budget(self) -> int:
        """Get latency budget based on execution path."""
        if self.execution_path == ExecutionPath.FAST_PATH:
            return 50
        elif self.execution_path == ExecutionPath.EXPLORATION_PATH:
            return 100
        else:  # REASONING_PATH
            return 2000


# =============================================================================
# POSTERIOR STATE
# =============================================================================

class PosteriorState(BaseModel):
    """
    Complete state of all modality posteriors.
    
    Persisted in Redis/Neo4j for continuity across requests.
    """
    state_id: str = Field(
        default_factory=lambda: f"post_{uuid4().hex[:12]}"
    )
    
    # All posteriors
    posteriors: Dict[LearningModality, ModalityPosterior] = Field(
        default_factory=dict
    )
    
    # Global stats
    total_decisions: int = Field(default=0, ge=0)
    total_rewards: float = Field(default=0.0, ge=0.0)
    
    # Timing
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    
    def initialize_posteriors(self) -> None:
        """Initialize posteriors for all modalities with uninformative priors."""
        for modality in LearningModality:
            if modality not in self.posteriors:
                self.posteriors[modality] = ModalityPosterior(
                    modality=modality,
                    alpha=1.0,
                    beta=1.0,
                )
    
    def get_posterior(self, modality: LearningModality) -> ModalityPosterior:
        """Get posterior for a modality, initializing if needed."""
        if modality not in self.posteriors:
            self.posteriors[modality] = ModalityPosterior(
                modality=modality,
                alpha=1.0,
                beta=1.0,
            )
        return self.posteriors[modality]
    
    def update_posterior(
        self,
        modality: LearningModality,
        reward: float,
    ) -> None:
        """Update a modality's posterior with observed reward."""
        posterior = self.get_posterior(modality)
        posterior.update(reward)
        self.total_decisions += 1
        self.total_rewards += reward
        self.last_updated = datetime.now(timezone.utc)
    
    def decay_all(self, factor: float = 0.995) -> None:
        """Apply decay to all posteriors."""
        for posterior in self.posteriors.values():
            posterior.decay(factor)
