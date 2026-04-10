# =============================================================================
# Therapeutic Retargeting Engine — Learning Signal Models
# Location: adam/retargeting/models/learning.py
# Spec: Enhancement #33, Section C.5
# =============================================================================

"""
Learning signal models for the Therapeutic Retargeting Engine.

Every therapeutic touch outcome generates a MechanismEffectivenessSignal
that updates the Bayesian posterior for mechanism effectiveness conditioned
on personality dimensions. SequenceLearningReport is generated when a
sequence completes, feeding back to the hierarchical prior system.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from adam.retargeting.models.enums import (
    BarrierCategory,
    ConversionStage,
    ScaffoldLevel,
    TherapeuticMechanism,
)


class MechanismEffectivenessSignal(BaseModel):
    """Learning signal sent to the Gradient Bridge (#06) after each touch outcome.

    This is how the system learns which mechanisms work for which
    psychological profiles. Each signal updates the Bayesian posterior
    for mechanism effectiveness conditioned on personality dimensions.
    """

    signal_id: str = Field(default_factory=lambda: str(uuid4()))
    sequence_id: str
    touch_id: str

    # Context
    archetype_id: str
    user_personality_vector: List[float] = Field(
        default_factory=list,
        description="65-dimensional buyer psychology vector",
    )
    barrier_category: BarrierCategory
    alignment_dimension_targeted: str

    # Intervention
    mechanism_deployed: TherapeuticMechanism
    scaffold_level: ScaffoldLevel
    construal_level: str = ""
    narrative_chapter: int = 0

    # Outcome
    engagement_occurred: bool = False
    stage_advanced: bool = False
    converted: bool = False
    barrier_resolved: Optional[bool] = None

    # Composite outcome score (for Thompson Sampling update)
    outcome_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Weighted composite: 0.1*engagement + 0.3*stage_advance + 0.6*conversion",
    )

    # Reactance observation
    reactance_indicator: float = Field(
        ge=-1.0,
        le=1.0,
        default=0.0,
        description="Negative = engagement increased, Positive = engagement decreased",
    )

    # Timestamp
    observed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class SequenceLearningReport(BaseModel):
    """Comprehensive learning report generated when a sequence completes.

    Fed back to the Bayesian prior hierarchy for cross-user,
    cross-archetype, and cross-brand learning.
    """

    sequence_id: str
    user_id: str
    brand_id: str
    archetype_id: str

    # Sequence outcome
    final_status: str  # "converted", "suppressed", "exhausted"
    total_touches: int
    total_days: int
    converted: bool

    # Per-touch mechanism effectiveness
    mechanism_outcomes: List[MechanismEffectivenessSignal] = Field(
        default_factory=list
    )

    # Barrier resolution chain
    barriers_diagnosed: List[BarrierCategory] = Field(default_factory=list)
    barriers_resolved: List[BarrierCategory] = Field(default_factory=list)
    barriers_unresolved: List[BarrierCategory] = Field(default_factory=list)

    # Stage progression
    stage_trajectory: List[ConversionStage] = Field(default_factory=list)

    # Reactance trajectory
    reactance_trajectory: List[float] = Field(default_factory=list)
    peak_reactance: float = 0.0

    # Cross-archetype signal
    reclassification_occurred: bool = False
    reclassified_to: Optional[str] = None

    # Key learnings (human-readable for dashboard)
    key_insight: str = Field(
        default="",
        description=(
            "E.g., 'Trust-deficit barriers for high-agreeableness users resolve "
            "2.3x faster with evidence_proof than with social_proof_matched'"
        ),
    )

    # Enhancement #36: Within-subject repeated measures analysis
    trajectory_analysis: Optional[Dict] = Field(
        default=None,
        description="TrajectoryAnalysis dict — longitudinal engagement trajectory",
    )
    within_user_mechanism_rankings: Dict[str, float] = Field(
        default_factory=dict,
        description="mechanism -> within-user posterior mean (personalized ranking)",
    )
    variance_components: Optional[Dict] = Field(
        default=None,
        description="VarianceComponents dict — between/within variance decomposition",
    )
    design_efficiency: float = Field(
        default=0.0,
        description="How well the sequence exploited within-subject power (0-1)",
    )

    # Timing
    completed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
