# =============================================================================
# Therapeutic Retargeting Engine — Sequence Models
# Location: adam/retargeting/models/sequences.py
# Spec: Enhancement #33, Section C.3
# =============================================================================

"""
Therapeutic touch and sequence models.

A TherapeuticSequence is NOT a linear sequence. It is a DECISION TREE where
each subsequent touch is selected based on the outcome of the previous
touch and the updated barrier diagnosis.
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


class TherapeuticTouch(BaseModel):
    """A single retargeting touch — the atomic unit of the therapeutic sequence.

    Unlike standard retargeting where each touch is an independent ad impression,
    a therapeutic touch is a DIAGNOSTIC INTERVENTION: it has a specific hypothesis
    about what barrier to resolve, a specific mechanism chosen to resolve it,
    and a specific outcome it expects to observe.
    """

    touch_id: str = Field(default_factory=lambda: str(uuid4()))
    sequence_id: str
    position_in_sequence: int

    # Diagnostic context
    diagnosis_id: str = Field(
        description="The barrier diagnosis this touch responds to"
    )
    target_barrier: BarrierCategory
    target_alignment_dimension: str = Field(
        description="The specific bilateral alignment dimension being addressed"
    )

    # Intervention selection
    mechanism: TherapeuticMechanism
    scaffold_level: ScaffoldLevel
    construal_level: str = Field(description="'abstract' or 'concrete'")
    processing_route: str = Field(description="'central' or 'peripheral'")

    # Narrative arc position
    narrative_chapter: int = Field(
        ge=1, le=5, description="Position in the 5-chapter narrative arc"
    )
    narrative_function: str = Field(
        description="E.g., 'introduce_character', 'present_conflict', 'show_resolution'"
    )

    # Creative specification
    creative_strategy: Dict = Field(
        default_factory=dict,
        description="Complete creative spec for personality-matched copy generation",
    )
    testimonial_model_type: Optional[str] = Field(
        default=None,
        description="'coping' or 'mastery' per Bandura/Braaksma matching rules",
    )

    # Delivery constraints
    min_hours_after_previous: int = Field(
        default=24,
        description="Minimum hours after previous touch (reactance management)",
    )
    max_hours_after_previous: int = Field(
        default=72,
        description="Maximum hours before ownership decay makes touch less effective",
    )

    # Trigger conditions
    trigger_type: str = Field(
        description="'time_elapsed', 'site_revisit', 'cart_abandon', 'competitor_visit'"
    )
    trigger_conditions: Dict = Field(
        default_factory=dict,
        description="Specific conditions that must be met to fire this touch",
    )

    # Expected outcome
    expected_stage_movement: Optional[ConversionStage] = None
    expected_engagement_probability: float = Field(ge=0.0, le=1.0, default=0.5)

    # Page context targeting (placement prescription)
    # The touch specifies WHERE to show it, not just WHAT. Page mindstate
    # is part of the therapeutic intervention — evidence_proof on an analytical
    # page is a fundamentally different intervention than evidence_proof on
    # an emotional page.
    target_page_cluster: str = Field(
        default="",
        description=(
            "Target page psychological cluster: analytical, emotional, social, "
            "transactional, aspirational. Empty = no preference (population default)."
        ),
    )
    target_page_mindstate: Optional[Dict[str, float]] = Field(
        default=None,
        description="32-dim ideal PageMindstateVector for bid computation",
    )
    placement_bid_strategy: Dict[str, float] = Field(
        default_factory=dict,
        description=(
            "Pre-computed bid multipliers: domain_or_cluster -> multiplier. "
            "Used by StackAdapt translator for per-touch placement optimization."
        ),
    )

    # Autonomy preservation
    autonomy_language: bool = Field(
        default=True,
        description="Use autonomy-supporting language ('consider', 'perhaps')",
    )
    opt_out_visible: bool = Field(
        default=True,
        description="Show easy opt-out to reduce reactance",
    )


class TherapeuticSequence(BaseModel):
    """A complete retargeting sequence for one user x one brand x one archetype.

    The sequence is NOT pre-planned linearly. It is a DECISION TREE where
    each subsequent touch is selected based on the outcome of the previous
    touch and the updated barrier diagnosis.
    """

    sequence_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    brand_id: str
    archetype_id: str

    # Configuration
    max_touches: int = Field(
        default=7,
        description="Maximum touches before suppression (inverted-U research)",
    )
    max_duration_days: int = Field(
        default=21, description="Maximum calendar days for sequence"
    )

    # Current state
    touches_delivered: List[TherapeuticTouch] = Field(default_factory=list)
    current_diagnosis_id: Optional[str] = None

    # Reactance management (Wicklund hydraulic model)
    cumulative_reactance: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Accumulated reactance. Wicklund hydraulic model.",
    )
    reactance_decay_rate: float = Field(
        default=0.15, description="Reactance decay per 24h of no-contact"
    )

    # Sequence status
    status: str = Field(
        default="active",
        description="'active', 'paused', 'suppressed', 'converted', 'exhausted'",
    )

    # Suppression rules
    suppress_if_ctr_below: float = Field(
        default=0.0003,
        description="If CTR drops below 0.03% at any point, pause 72h",
    )
    suppress_after_max_touches: bool = Field(default=True)
    suppression_duration_days: int = Field(
        default=14,
        description="Days of suppression before re-engagement attempt",
    )

    # Narrative arc tracking
    narrative_arc_position: int = Field(
        default=0, description="Current position in the 5-chapter narrative arc"
    )
    narrative_arc_type: str = Field(
        default="resolution",
        description="'resolution', 'discovery', 'transformation' — archetype-matched",
    )

    # Engagement tracking (for CTR suppression — updated as outcomes arrive)
    delivered_count: int = Field(
        default=0,
        description="Total touches delivered (incremented at delivery, not outcome)",
    )
    engaged_count: int = Field(
        default=0,
        description="Total touches that produced engagement (incremented at outcome)",
    )

    # Learning outputs
    mechanism_effectiveness_log: Dict[str, List[float]] = Field(
        default_factory=dict,
        description="mechanism_name -> [outcome_scores] for Bayesian updating",
    )

    # Cross-archetype reclassification
    reclassification_signals: List[Dict] = Field(default_factory=list)
    reclassified: bool = Field(default=False)
    original_archetype_id: Optional[str] = None

    # Enhancement #36: Within-subject repeated measures
    within_subject_design: Optional[Dict] = Field(
        default=None,
        description="WithinSubjectDesign dict — experimental design for this sequence",
    )
    per_touch_stage: List[str] = Field(
        default_factory=list,
        description="ConversionStage at each touch (for trajectory analysis)",
    )
    per_touch_reactance: List[float] = Field(
        default_factory=list,
        description="Cumulative reactance at each touch (for trajectory analysis)",
    )

    # Timing
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: Optional[datetime] = None


class SequenceDecisionNode(BaseModel):
    """A decision point in the therapeutic sequence tree.

    After each touch outcome, the system evaluates which branch to take.
    This is NOT a linear sequence — it's a decision tree.
    """

    node_id: str = Field(default_factory=lambda: str(uuid4()))
    after_touch_position: int

    # Evaluation criteria -> next mechanism
    if_barrier_resolved: Optional[TherapeuticMechanism] = Field(
        default=None,
        description="Next mechanism if the target barrier was resolved",
    )
    if_barrier_persists: Optional[TherapeuticMechanism] = Field(
        default=None,
        description="Next mechanism if the target barrier was NOT resolved",
    )
    if_new_barrier_emerged: Optional[TherapeuticMechanism] = Field(
        default=None,
        description="Next mechanism if a NEW barrier surfaced",
    )
    if_rupture_detected: Optional[str] = Field(
        default="pause_72h",
        description="Action if engagement rupture detected",
    )
    if_reactance_exceeded: str = Field(
        default="suppress",
        description="Action if cumulative reactance exceeds budget",
    )
    if_stage_advanced: Optional[TherapeuticMechanism] = Field(
        default=None,
        description="Next mechanism if user advanced to next stage",
    )
