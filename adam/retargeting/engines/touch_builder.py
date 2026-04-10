# =============================================================================
# Therapeutic Retargeting Engine — Touch Builder
# Location: adam/retargeting/engines/touch_builder.py
# =============================================================================

"""
Touch Builder — Constructs TherapeuticTouch from diagnosis + narrative position.

Assembles all the pieces from the diagnostic loop into a concrete touch
specification that the creative generation system can execute.
"""

import logging
from typing import Dict, Optional

from adam.retargeting.models.enums import (
    BarrierCategory,
    ConversionStage,
    ScaffoldLevel,
    TherapeuticMechanism,
)
from adam.retargeting.models.diagnostics import ConversionBarrierDiagnosis
from adam.retargeting.models.sequences import TherapeuticTouch
from adam.retargeting.engines.narrative_arc import NarrativeArcBuilder, NarrativePosition

logger = logging.getLogger(__name__)


# Trigger type mapping from stage
_STAGE_TRIGGER_MAP = {
    ConversionStage.UNAWARE: "time_elapsed",
    ConversionStage.CURIOUS: "time_elapsed",
    ConversionStage.EVALUATING: "site_revisit",
    ConversionStage.INTENDING: "cart_abandon",
    ConversionStage.STALLED: "time_elapsed",
}

# Timing constraints by stage
_STAGE_TIMING = {
    ConversionStage.CURIOUS: {"min_hours": 48, "max_hours": 120},
    ConversionStage.EVALUATING: {"min_hours": 24, "max_hours": 72},
    ConversionStage.INTENDING: {"min_hours": 2, "max_hours": 48},
    ConversionStage.STALLED: {"min_hours": 24, "max_hours": 72},
}


PAGE_CLUSTERS = ["analytical", "emotional", "social", "transactional", "aspirational"]

# Minimum observations per mechanism:cluster before user preference overrides population
_MIN_OBS_TO_OVERRIDE = 2


class TouchBuilder:
    """Constructs a TherapeuticTouch from all diagnostic components.

    Combines:
    - Barrier diagnosis (what to target)
    - Mechanism selection (how to target)
    - Page mindstate prescription (where to target)
    - Narrative position (story context)
    - Stage-appropriate trigger and timing
    - Reactance-aware autonomy language
    """

    def __init__(
        self,
        narrative_builder: Optional[NarrativeArcBuilder] = None,
        placement_optimizer=None,
    ):
        self._narrative = narrative_builder or NarrativeArcBuilder()
        self._placement = placement_optimizer

    def build(
        self,
        sequence_id: str,
        position: int,
        diagnosis: ConversionBarrierDiagnosis,
        max_touches: int = 7,
        arc_reset: bool = False,
        brand_name: str = "",
        user_profile=None,
        context: Optional[Dict] = None,
    ) -> TherapeuticTouch:
        """Build a complete TherapeuticTouch specification.

        Args:
            sequence_id: The owning sequence
            position: 1-indexed position in the sequence
            diagnosis: The barrier diagnosis driving this touch
            max_touches: Total sequence length (for narrative pacing)
            arc_reset: True if narrative should restart (after rupture repair)
            brand_name: For creative context
            user_profile: UserPosteriorProfile for per-user page cluster selection
            context: Dict with optional page_switch_signal from prior outcome
        """
        context = context or {}
        # Get narrative position
        narrative_pos = self._narrative.get_narrative_position(
            touch_position=position,
            archetype_id=diagnosis.archetype_id,
            stage=diagnosis.conversion_stage,
            max_touches=max_touches,
            arc_reset=arc_reset,
        )

        # Build creative context
        creative_strategy = self._narrative.build_creative_context(
            position=narrative_pos,
            barrier=diagnosis.primary_barrier,
            mechanism=diagnosis.recommended_mechanism,
            brand_name=brand_name,
        )

        # Add diagnosis context to creative strategy
        creative_strategy["archetype_id"] = diagnosis.archetype_id
        creative_strategy["reactance_level"] = diagnosis.estimated_reactance_level
        creative_strategy["pk_phase"] = diagnosis.persuasion_knowledge_phase
        creative_strategy["ownership_level"] = diagnosis.ownership_level
        creative_strategy["scaffold_level"] = diagnosis.recommended_scaffold_level.value

        # Determine trigger
        trigger_type = _STAGE_TRIGGER_MAP.get(
            diagnosis.conversion_stage, "time_elapsed"
        )

        # Determine timing
        timing = _STAGE_TIMING.get(
            diagnosis.conversion_stage,
            {"min_hours": 24, "max_hours": 72},
        )

        # Target dimension: the first alignment gap if available
        target_dim = ""
        if diagnosis.primary_alignment_gaps:
            target_dim = diagnosis.primary_alignment_gaps[0].dimension

        # Autonomy language: always on, but especially if reactance > 0.3
        use_autonomy = True
        show_opt_out = diagnosis.estimated_reactance_level > 0.3

        # Compute page placement prescription
        target_page_cluster = ""
        target_page_mindstate = None
        placement_bid_strategy = {}

        if self._placement is not None:
            mechanism_str = diagnosis.recommended_mechanism.value
            barrier_str = diagnosis.primary_barrier.value
            archetype_str = diagnosis.archetype_id

            # Population-level ideal page mindstate for this mechanism
            ideal = self._placement.compute_ideal_mindstate(
                mechanism=mechanism_str,
                barrier=barrier_str,
                archetype=archetype_str,
            )
            target_page_cluster = self._placement._classify_page_cluster(ideal)
            target_page_mindstate = ideal.edge_dimensions

            # Per-user override: if user has page_mechanism_posteriors with
            # enough data, use their empirically-best cluster for this mechanism
            if user_profile is not None:
                user_cluster = self._select_user_preferred_cluster(
                    user_profile, mechanism_str, target_page_cluster, context,
                )
                if user_cluster:
                    target_page_cluster = user_cluster

            # Add to creative strategy so downstream systems know the page target
            creative_strategy["target_page_cluster"] = target_page_cluster

        return TherapeuticTouch(
            sequence_id=sequence_id,
            position_in_sequence=position,
            diagnosis_id=diagnosis.diagnosis_id,
            target_barrier=diagnosis.primary_barrier,
            target_alignment_dimension=target_dim,
            mechanism=diagnosis.recommended_mechanism,
            scaffold_level=diagnosis.recommended_scaffold_level,
            construal_level=narrative_pos.construal_level,
            processing_route=narrative_pos.processing_route,
            narrative_chapter=narrative_pos.chapter,
            narrative_function=narrative_pos.function,
            creative_strategy=creative_strategy,
            testimonial_model_type=narrative_pos.testimonial_type,
            min_hours_after_previous=timing["min_hours"],
            max_hours_after_previous=timing["max_hours"],
            trigger_type=trigger_type,
            trigger_conditions={
                "stage": diagnosis.conversion_stage.value,
                "barrier": diagnosis.primary_barrier.value,
            },
            expected_stage_movement=self._expected_stage(diagnosis.conversion_stage),
            expected_engagement_probability=min(
                0.8, diagnosis.mechanism_confidence * 0.8
            ),
            target_page_cluster=target_page_cluster,
            target_page_mindstate=target_page_mindstate,
            placement_bid_strategy=placement_bid_strategy,
            autonomy_language=use_autonomy,
            opt_out_visible=show_opt_out,
        )

    def _select_user_preferred_cluster(
        self,
        profile,
        mechanism: str,
        population_default: str,
        context: Dict,
    ) -> str:
        """Select the page cluster that works best for THIS user with THIS mechanism.

        Priority:
        1. If page_switch_signal == "switch_cluster": exclude the failed cluster,
           pick next-best from user data or fall back to population
        2. If user has 2+ observations for mechanism:cluster, pick highest posterior mean
        3. Fall back to population-level ideal (cold start)

        Returns cluster name or empty string to use population default.
        """
        page_switch = context.get("page_switch_signal", "")
        failed_cluster = context.get("failed_page_cluster", "")

        # Get user's page_mechanism_posteriors for this mechanism
        posteriors = {}
        if hasattr(profile, 'page_mechanism_posteriors'):
            for cluster in PAGE_CLUSTERS:
                key = f"{mechanism}:{cluster}"
                p = profile.page_mechanism_posteriors.get(key)
                if p and p.sample_count >= _MIN_OBS_TO_OVERRIDE:
                    posteriors[cluster] = p.alpha / (p.alpha + p.beta)

        if not posteriors:
            return ""  # Cold start — use population default

        # If switching: exclude the failed cluster
        if page_switch == "switch_cluster" and failed_cluster:
            posteriors.pop(failed_cluster, None)

        if not posteriors:
            return ""

        # Pick cluster with highest posterior mean
        best_cluster = max(posteriors, key=posteriors.get)
        return best_cluster

    def _expected_stage(self, current: ConversionStage) -> Optional[ConversionStage]:
        """What stage do we expect the user to move to?"""
        progression = {
            ConversionStage.UNAWARE: ConversionStage.CURIOUS,
            ConversionStage.CURIOUS: ConversionStage.EVALUATING,
            ConversionStage.EVALUATING: ConversionStage.INTENDING,
            ConversionStage.INTENDING: ConversionStage.CONVERTED,
            ConversionStage.STALLED: ConversionStage.INTENDING,
        }
        return progression.get(current)
