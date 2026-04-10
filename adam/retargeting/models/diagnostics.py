# =============================================================================
# Therapeutic Retargeting Engine — Diagnostic Models
# Location: adam/retargeting/models/diagnostics.py
# Spec: Enhancement #33, Section C.2
# =============================================================================

"""
Conversion barrier diagnostic models.

The ConversionBarrierDiagnosis is the core analytical unit of the Therapeutic
Retargeting Engine. It answers: WHY did this specific person not convert,
given their specific psychological profile and the specific brand positioning
they encountered?
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field

from adam.retargeting.models.enums import (
    BarrierCategory,
    ConversionStage,
    RuptureType,
    ScaffoldLevel,
    TherapeuticMechanism,
)


class AlignmentGap(BaseModel):
    """A specific bilateral alignment dimension that fell below threshold."""

    dimension: str = Field(description="Name of the bilateral alignment dimension")
    actual_value: float = Field(description="Observed alignment score")
    threshold_value: float = Field(description="Minimum score for conversion")
    gap_magnitude: float = Field(description="threshold - actual (positive = deficit)")
    effect_size_d: float = Field(
        description="Cohen's d of gap relative to converters"
    )
    rank_in_archetype: int = Field(
        description="Rank of this gap's importance for this archetype"
    )


class ConversionBarrierDiagnosis(BaseModel):
    """Complete diagnostic output for a non-conversion event.

    This is the core analytical unit of the Therapeutic Retargeting Engine.
    It answers: WHY did this specific person not convert, given their
    specific psychological profile and the specific brand positioning
    they encountered?
    """

    diagnosis_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    brand_id: str
    archetype_id: str
    diagnosed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    # Current stage assessment
    conversion_stage: ConversionStage
    stage_confidence: float = Field(ge=0.0, le=1.0)
    stage_signals: Dict[str, float] = Field(
        default_factory=dict,
        description="Behavioral signals that determined stage classification",
    )

    # Rupture assessment
    rupture_type: RuptureType
    rupture_severity: float = Field(
        ge=0.0, le=1.0, description="0=no rupture, 1=complete disengagement"
    )

    # Primary barrier (the MOST important reason for non-conversion)
    primary_barrier: BarrierCategory
    primary_barrier_confidence: float = Field(ge=0.0, le=1.0)
    primary_alignment_gaps: List[AlignmentGap] = Field(
        description="Specific alignment dimensions contributing to primary barrier"
    )

    # Secondary barriers (may contribute but are not primary)
    secondary_barriers: List[Tuple[BarrierCategory, float]] = Field(
        default_factory=list,
        description="(barrier_category, confidence) pairs",
    )

    # Reactance state
    estimated_reactance_level: float = Field(
        ge=0.0,
        le=1.0,
        description="Current estimated reactance from prior retargeting touches",
    )
    reactance_budget_remaining: float = Field(
        ge=0.0,
        le=1.0,
        description="How much more retargeting pressure this user can tolerate",
    )

    # PKM state
    persuasion_knowledge_phase: int = Field(
        ge=1,
        le=3,
        description="1=peripheral, 2=PK activated, 3=full coping",
    )

    # Psychological ownership state
    ownership_level: float = Field(
        ge=0.0,
        le=1.0,
        description="Estimated psychological ownership from browsing behavior",
    )
    ownership_decay_rate: float = Field(
        description="Hours since peak ownership x decay coefficient"
    )

    # Touch history
    total_touches_received: int
    touches_since_last_engagement: int
    last_mechanism_deployed: Optional[TherapeuticMechanism] = None
    last_mechanism_outcome: Optional[str] = None  # engaged, ignored, bounced

    # Recommended intervention
    recommended_mechanism: TherapeuticMechanism
    recommended_scaffold_level: ScaffoldLevel
    mechanism_confidence: float = Field(ge=0.0, le=1.0)
    mechanism_rationale: str = Field(
        description="Human-readable explanation of why this mechanism was selected"
    )


class BarrierResolutionOutcome(BaseModel):
    """Outcome observation after a therapeutic touch is delivered."""

    outcome_id: str = Field(default_factory=lambda: str(uuid4()))
    diagnosis_id: str = Field(
        description="Links to the diagnosis this touch attempted to resolve"
    )
    touch_id: str
    user_id: str

    # What was deployed
    mechanism_deployed: TherapeuticMechanism
    scaffold_level: ScaffoldLevel
    creative_variant_id: str = ""

    # What happened
    impression_delivered: bool = True
    engagement_type: Optional[str] = None  # click, dwell>5s, site_visit, booking_start
    converted: bool = False

    # Barrier status after touch
    barrier_resolved: Optional[bool] = Field(
        default=None,
        description="Did the specific barrier targeted get resolved? None if unknown.",
    )
    new_barrier_emerged: Optional[BarrierCategory] = Field(
        default=None, description="If a new barrier surfaced, what is it?"
    )

    # Stage movement
    stage_before: ConversionStage
    stage_after: ConversionStage
    stage_advanced: bool = Field(
        description="Did the user move to a more advanced conversion stage?"
    )

    # Timing
    delivered_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    observed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    observation_window_hours: int = Field(
        default=48,
        description="How long after delivery we waited before observing outcome",
    )
