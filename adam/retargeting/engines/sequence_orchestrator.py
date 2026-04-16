# =============================================================================
# Therapeutic Retargeting Engine — Sequence Orchestrator
# Location: adam/retargeting/engines/sequence_orchestrator.py
# Spec: Enhancement #33, Session 33-7
# =============================================================================

"""
Therapeutic Sequence Orchestrator — The Brain of the Retargeting System.

This is NOT a linear sequence engine. It is a DECISION TREE orchestrator.
After each touch outcome:
1. Observe outcome (engaged? stage advanced? converted? new barrier?)
2. Update barrier diagnosis
3. Check for ruptures
4. Check suppression rules
5. Select next mechanism via Thompson Sampling
6. Build next touch with appropriate scaffold level and construal shift
7. Manage narrative arc position
8. Handle cross-archetype reclassification signals
9. Update learning at all hierarchy levels

The orchestrator delegates to:
- ConversionBarrierDiagnosticEngine (diagnosis)
- BayesianMechanismSelector (mechanism selection)
- RuptureDetector (rupture assessment)
- SuppressionController (suppression rules)
- TouchBuilder (touch construction)
- NarrativeArcBuilder (narrative positioning)
- HierarchicalPriorManager (learning updates)
"""

import asyncio
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from uuid import uuid4

from adam.retargeting.models.enums import (
    BarrierCategory,
    ConversionStage,
    RuptureType,
    TherapeuticMechanism,
)
from adam.retargeting.models.diagnostics import (
    ConversionBarrierDiagnosis,
    BarrierResolutionOutcome,
)
from adam.retargeting.models.sequences import TherapeuticSequence, TherapeuticTouch
from adam.retargeting.models.learning import MechanismEffectivenessSignal
from adam.retargeting.engines.barrier_diagnostic import (
    ConversionBarrierDiagnosticEngine,
)
from adam.retargeting.engines.mechanism_selector import BayesianMechanismSelector
from adam.retargeting.engines.rupture_detector import RuptureDetector
from adam.retargeting.engines.suppression_controller import SuppressionController
from adam.retargeting.engines.touch_builder import TouchBuilder
from adam.retargeting.engines.narrative_arc import NarrativeArcBuilder
from adam.retargeting.engines.prior_manager import HierarchicalPriorManager
from adam.retargeting.engines.learning_loop import RetargetingLearningLoop
from adam.retargeting.engines.options_framework import OptionsController

logger = logging.getLogger(__name__)


class TherapeuticSequenceOrchestrator:
    """Manages the complete lifecycle of therapeutic retargeting sequences.

    Responsibilities:
    - Create new sequences for non-converting users
    - Generate the next touch based on updated diagnosis
    - Process outcomes and update all learning systems
    - Manage sequence state transitions
    - Enforce suppression rules
    - Handle cross-archetype reclassification
    """

    # TTL for sequence storage (7 days — covers max sequence duration + attribution window)
    SEQUENCE_TTL_SECONDS = 7 * 24 * 3600
    # Max sequences to keep in L1 memory cache
    MAX_L1_SEQUENCES = 10_000

    def __init__(
        self,
        prior_manager: Optional[HierarchicalPriorManager] = None,
        neo4j_driver=None,
        redis_client=None,
        user_posterior_manager=None,
        event_bus=None,
    ):
        self._prior_manager = prior_manager or HierarchicalPriorManager()
        self._mechanism_selector = BayesianMechanismSelector(self._prior_manager)
        self._diagnostic_engine = ConversionBarrierDiagnosticEngine(
            mechanism_selector=self._mechanism_selector,
        )
        self._rupture_detector = RuptureDetector()
        self._suppression = SuppressionController()
        self._narrative = NarrativeArcBuilder()
        self._event_bus = event_bus

        # Enhancement #33 learning loop wrapper — wraps prior_manager with
        # MechanismEffectivenessSignal generation, event publishing, and
        # archetype reclassification detection. Previously orphaned and
        # bypassed; now invoked from process_outcome_and_get_next.
        # We pass user_posterior_manager=None because THIS orchestrator
        # owns the per-user update (it needs the UserProfile result for
        # page-cluster switch signaling). The design_effect_weight is
        # passed into process_touch_outcome as an override instead.
        self._learning_loop = RetargetingLearningLoop(
            prior_manager=self._prior_manager,
            event_bus=event_bus,
            user_posterior_manager=None,
        )

        # Placement optimizer for page mindstate prescription
        try:
            from adam.retargeting.resonance.placement_optimizer import get_placement_optimizer
            self._placement_optimizer = get_placement_optimizer()
        except Exception:
            self._placement_optimizer = None

        self._touch_builder = TouchBuilder(
            placement_optimizer=self._placement_optimizer,
        )
        self._options = OptionsController()
        self._driver = neo4j_driver
        self._redis = redis_client

        # Enhancement #36: Within-subject repeated measures
        self._user_posterior_manager = user_posterior_manager
        self._within_subject_designer = None
        if user_posterior_manager is not None:
            from adam.retargeting.engines.repeated_measures import WithinSubjectDesigner
            self._within_subject_designer = WithinSubjectDesigner(self._prior_manager)

        # L1 in-memory cache (fast path) + L2 Redis (durable, survives restart)
        self._sequences: Dict[str, TherapeuticSequence] = {}
        # Per-sequence async locks to prevent interleaved process_outcome_and_get_next
        # calls on the same sequence across await points
        self._seq_locks: Dict[str, asyncio.Lock] = {}
        # Protects _sequences dict mutations (insert/evict) and _seq_locks creation
        self._storage_lock = threading.Lock()

    async def create_sequence(
        self,
        user_id: str,
        brand_id: str,
        archetype_id: str,
        bilateral_edge: Dict[str, float],
        behavioral_signals: Optional[Dict[str, float]] = None,
        context: Optional[Dict[str, str]] = None,
        brand_name: str = "",
        max_touches: int = 7,
    ) -> Tuple[TherapeuticSequence, TherapeuticTouch]:
        """Create a new therapeutic sequence and generate the first touch.

        This is the entry point when a non-conversion is detected.

        Args:
            user_id: The non-converting user
            brand_id: Brand they didn't convert for
            archetype_id: Their classified archetype
            bilateral_edge: 27-dim alignment vector
            behavioral_signals: Current behavioral state
            context: Hierarchy context (category, campaign_id)
            brand_name: For creative generation
            max_touches: Max touches for this sequence

        Returns:
            (sequence, first_touch)
        """
        context = context or {}

        # Determine arc type from archetype
        arc_type = self._narrative.get_arc_type(archetype_id)

        # Create sequence
        sequence = TherapeuticSequence(
            user_id=user_id,
            brand_id=brand_id,
            archetype_id=archetype_id,
            max_touches=max_touches,
            narrative_arc_type=arc_type,
        )

        # Enhancement #36: Create within-subject experimental design
        if self._within_subject_designer and self._user_posterior_manager:
            user_profile = self._user_posterior_manager.get_user_profile(
                user_id=user_id,
                brand_id=brand_id,
                archetype_id=archetype_id,
                context=context,
            )
            ws_design = self._within_subject_designer.design_sequence(
                user_id=user_id,
                sequence_id=sequence.sequence_id,
                archetype_id=archetype_id,
                barrier="",  # Will be set after diagnosis
                max_touches=max_touches,
                user_profile=user_profile,
                context=context,
            )
            sequence.within_subject_design = ws_design.model_dump()

        # Store with sequence_id in context for prior lookups
        ctx_with_seq = {**context, "sequence_id": sequence.sequence_id}

        # Run initial diagnosis
        diagnosis = await self._diagnostic_engine.diagnose(
            user_id=user_id,
            brand_id=brand_id,
            archetype_id=archetype_id,
            bilateral_edge=bilateral_edge,
            behavioral_signals=behavioral_signals,
            touch_history=[],
            context=ctx_with_seq,
        )

        sequence.current_diagnosis_id = diagnosis.diagnosis_id

        # Options Framework: filter mechanism by stage policy
        diagnosis = self._apply_options_filter(diagnosis)

        # Frustration check: warn if targeting conflicting dimensions
        self._check_frustration(diagnosis, sequence)

        # Build first touch (with placement prescription from population priors)
        # First touch uses population-level ideal page cluster (cold start for user)
        first_user_profile = None
        if self._user_posterior_manager:
            first_user_profile = self._user_posterior_manager.get_user_profile(
                user_id, brand_id, archetype_id,
            )
        first_touch = self._touch_builder.build(
            sequence_id=sequence.sequence_id,
            position=1,
            diagnosis=diagnosis,
            max_touches=max_touches,
            brand_name=brand_name,
            user_profile=first_user_profile,
        )

        sequence.touches_delivered.append(first_touch)
        sequence.delivered_count += 1
        sequence.narrative_arc_position = first_touch.narrative_chapter

        # Store sequence (L1 memory + L2 Redis)
        self._persist_sequence(sequence)

        logger.info(
            "Created sequence %s for user=%s brand=%s arch=%s barrier=%s mech=%s",
            sequence.sequence_id[:12],
            user_id,
            brand_id,
            archetype_id,
            diagnosis.primary_barrier.value,
            diagnosis.recommended_mechanism.value,
        )

        return sequence, first_touch

    async def process_outcome_and_get_next(
        self,
        sequence_id: str,
        outcome: BarrierResolutionOutcome,
        bilateral_edge: Dict[str, float],
        behavioral_signals: Optional[Dict[str, float]] = None,
        context: Optional[Dict[str, str]] = None,
        brand_name: str = "",
    ) -> Tuple[Optional[TherapeuticTouch], TherapeuticSequence, str]:
        """Process an outcome and generate the next touch (or stop).

        This is the core adaptive loop. Each call:
        1. Records the outcome
        2. Updates learning at all hierarchy levels
        3. Re-diagnoses the barrier
        4. Checks rupture + suppression
        5. Generates next touch (or terminates)

        Args:
            sequence_id: Active sequence
            outcome: What happened after the last touch
            bilateral_edge: Updated alignment vector (may have changed)
            behavioral_signals: Updated behavioral state
            context: Hierarchy context
            brand_name: For creative generation

        Returns:
            (next_touch_or_None, updated_sequence, status_message)
        """
        context = context or {}
        sequence = self._sequences.get(sequence_id)
        if sequence is None:
            return None, TherapeuticSequence(
                user_id="", brand_id="", archetype_id=""
            ), "Sequence not found"

        # Acquire per-sequence lock to prevent interleaved outcome processing.
        # Without this, two concurrent outcomes for the same sequence can
        # interleave across await points (e.g., diagnose), corrupting
        # mechanism_effectiveness_log, touch ordering, and reactance state.
        seq_lock = self._get_seq_lock(sequence_id)
        async with seq_lock:
            ctx_with_seq = {**context, "sequence_id": sequence_id}

            # --- 1. Record outcome ---
            self._record_outcome(sequence, outcome)

            # Enhancement #36: Record per-touch stage and reactance for trajectory analysis
            if outcome.stage_after:
                sequence.per_touch_stage.append(
                    outcome.stage_after.value if hasattr(outcome.stage_after, "value") else str(outcome.stage_after)
                )
            sequence.per_touch_reactance.append(sequence.cumulative_reactance)

            # --- 2. Update learning at all hierarchy levels ---
            reward = self._compute_reward(outcome)
            last_touch = sequence.touches_delivered[-1] if sequence.touches_delivered else None

            # Enhancement #36: Update user posteriors first to get design-effect weight
            design_effect_weight = None
            user_profile = None
            page_switch_signal = ""
            if last_touch and self._user_posterior_manager:
                # Pass page_cluster from the resolved touch for user×page learning
                resolved_page_cluster = getattr(last_touch, 'target_page_cluster', '')

                user_profile = self._user_posterior_manager.update_user_posterior(
                    user_id=sequence.user_id,
                    brand_id=sequence.brand_id,
                    mechanism=last_touch.mechanism.value,
                    barrier=last_touch.target_barrier.value,
                    archetype_id=sequence.archetype_id,
                    reward=reward,
                    touch_position=last_touch.position_in_sequence,
                    context=ctx_with_seq,
                    page_cluster=resolved_page_cluster,
                )
                design_effect_weight = user_profile.design_effect_weight

                # Compute page mindstate switch signal:
                # - Conversion: find more pages like this mindstate
                # - Click/engagement: keep this mindstate, it's working
                # - No engagement: try a different page mindstate next
                if outcome.converted:
                    page_switch_signal = "expand_same"
                elif outcome.engagement_type:
                    page_switch_signal = "continue_same"
                elif resolved_page_cluster:
                    page_switch_signal = "switch_cluster"

            if last_touch:
                # Route through the Enhancement #33 learning_loop wrapper.
                # This is structurally the same as calling
                # prior_manager.update_all_levels() directly (which is
                # what the code used to do here), but the wrapper also:
                # (1) generates a MechanismEffectivenessSignal for the
                #     Gradient Bridge
                # (2) publishes a retargeting.outcome.observed event if an
                #     event bus is configured
                # (3) runs the archetype reclassification check
                #
                # The user_posterior update happened earlier in this
                # method (lines above) because the orchestrator needs the
                # UserProfile result for page-cluster switch signaling,
                # so we pass design_effect_weight as an override and the
                # learning_loop skips its internal per-user update.
                loop_results = await self._learning_loop.process_touch_outcome(
                    sequence=sequence,
                    touch=last_touch,
                    outcome=outcome,
                    context={**ctx_with_seq, "user_id": sequence.user_id},
                    design_effect_weight_override=design_effect_weight,
                )
                # B1 Stage 2: TherapeuticSequence now has first-class
                # fields for the learning signal produced by the wrapper
                # (last_mechanism_effectiveness_signal + capped history).
                # Stash the signal so downstream telemetry, Gradient
                # Bridge consumers, and pilot retrospection can read it
                # without subscribing to the event bus.
                learning_signal = (
                    loop_results.get("learning_signal") if loop_results else None
                )
                if learning_signal is not None:
                    sequence.last_mechanism_effectiveness_signal = learning_signal
                    sequence.mechanism_effectiveness_signals.append(learning_signal)
                    # Cap history at 32 — bounded to keep serialized sequence
                    # state small; 32 > max_touches (default 7) gives comfortable
                    # headroom for reclassified sequences that exceed the cap.
                    if len(sequence.mechanism_effectiveness_signals) > 32:
                        sequence.mechanism_effectiveness_signals = (
                            sequence.mechanism_effectiveness_signals[-32:]
                        )

            # --- 3. Check conversion ---
            if outcome.converted:
                sequence.status = "converted"
                sequence.completed_at = datetime.now(timezone.utc)
                logger.info("Sequence %s CONVERTED", sequence_id[:12])
                return None, sequence, "Converted! Sequence complete."

            # --- 4. Build touch history for re-diagnosis ---
            touch_history = self._build_touch_history(sequence)

            # --- 5. Rupture detection ---
            rupture = self._rupture_detector.assess(
                touch_history,
                behavioral_signals,
                sequence.archetype_id,
            )

            # --- 6. Update reactance (Wicklund's hydraulic model) ---
            # Key: threats that arrive before prior reactance dissipates
            # compound MULTIPLICATIVELY, not additively.
            if last_touch:
                # First: apply decay from time since last touch
                if outcome.observation_window_hours > 0:
                    days = outcome.observation_window_hours / 24.0
                    decay_factor = max(0.0, 1.0 - 0.15 * days)
                    sequence.cumulative_reactance *= decay_factor

                # Then: apply new reactance from this touch
                base_reactance = 0.1
                if not outcome.engagement_type:
                    base_reactance = 0.15  # Ignored touches generate more reactance

                # Wicklund multiplicative compounding: if existing reactance > 0.2,
                # new threat amplifies instead of adding
                if sequence.cumulative_reactance > 0.2:
                    # Multiplicative: R_new = R_old * (1 + threat_magnitude)
                    sequence.cumulative_reactance = min(
                        1.0,
                        sequence.cumulative_reactance * (1.0 + base_reactance * 3.0),
                    )
                else:
                    # Below threshold: additive (normal)
                    sequence.cumulative_reactance = min(
                        1.0,
                        sequence.cumulative_reactance + base_reactance,
                    )

            # --- 7. Suppression check ---
            suppression = self._suppression.check(
                sequence=sequence,
                current_reactance=sequence.cumulative_reactance,
                rupture_assessment=rupture,
                current_stage=outcome.stage_after,
            )

            if suppression.should_suppress:
                sequence.status = suppression.new_status
                sequence.completed_at = datetime.now(timezone.utc)
                logger.info(
                    "Sequence %s SUPPRESSED: %s",
                    sequence_id[:12], suppression.reason,
                )
                return None, sequence, suppression.reason

            if suppression.should_pause:
                sequence.status = "paused"
                logger.info(
                    "Sequence %s PAUSED %dh: %s",
                    sequence_id[:12], suppression.pause_hours, suppression.reason,
                )
                return None, sequence, suppression.reason

            # --- 8. Re-diagnose barrier ---
            # Enhancement #36: Pass user profile and within-subject design
            # to mechanism selector (through diagnostic engine) so it can:
            # - Blend user-level posteriors with population posteriors
            # - Route exploration slots to information-maximizing mechanisms
            # - Add user random intercept to Thompson Sampling
            next_position = len(sequence.touches_delivered) + 1
            ws_design = None
            if sequence.within_subject_design:
                from adam.retargeting.models.within_subject import WithinSubjectDesign
                ws_design = (
                    sequence.within_subject_design
                    if isinstance(sequence.within_subject_design, WithinSubjectDesign)
                    else WithinSubjectDesign(**sequence.within_subject_design)
                )

            diagnosis = await self._diagnostic_engine.diagnose(
                user_id=sequence.user_id,
                brand_id=sequence.brand_id,
                archetype_id=sequence.archetype_id,
                bilateral_edge=bilateral_edge,
                behavioral_signals=behavioral_signals,
                touch_history=touch_history,
                context=ctx_with_seq,
                user_profile=user_profile,
                within_subject_design=ws_design,
                touch_position=next_position,
            )

            sequence.current_diagnosis_id = diagnosis.diagnosis_id

            # Options Framework: filter mechanism by stage policy
            diagnosis = self._apply_options_filter(diagnosis)

            # Frustration check: avoid conflicting dimensions with previous touch
            self._check_frustration(diagnosis, sequence)

            # --- 9. Determine if arc should reset ---
            arc_reset = (
                rupture.rupture_type != RuptureType.NONE
                and rupture.severity > 0.5
            )

            # --- 10. Build next touch (with placement prescription) ---
            touch_context = {
                "page_switch_signal": page_switch_signal,
                "failed_page_cluster": (
                    getattr(last_touch, 'target_page_cluster', '')
                    if page_switch_signal == "switch_cluster" else ""
                ),
            }

            next_touch = self._touch_builder.build(
                sequence_id=sequence_id,
                position=next_position,
                diagnosis=diagnosis,
                max_touches=sequence.max_touches,
                arc_reset=arc_reset,
                brand_name=brand_name,
                user_profile=user_profile,
                context=touch_context,
            )

            sequence.touches_delivered.append(next_touch)
            sequence.delivered_count += 1
            sequence.narrative_arc_position = next_touch.narrative_chapter

            page_target = (
                f", page={next_touch.target_page_cluster}"
                if next_touch.target_page_cluster else ""
            )
            status_msg = (
                f"Touch {next_position}: {diagnosis.primary_barrier.value} → "
                f"{diagnosis.recommended_mechanism.value} "
                f"(stage={diagnosis.conversion_stage.value}, "
                f"reactance={sequence.cumulative_reactance:.2f}"
                f"{page_target})"
            )

            logger.info("Sequence %s touch %d: %s", sequence_id[:12], next_position, status_msg)

        return next_touch, sequence, status_msg

    def _get_seq_lock(self, sequence_id: str) -> asyncio.Lock:
        """Get or create an asyncio.Lock for a specific sequence.

        Thread-safe: uses _storage_lock to protect _seq_locks dict creation.
        """
        lock = self._seq_locks.get(sequence_id)
        if lock is None:
            with self._storage_lock:
                # Double-check after acquiring lock
                lock = self._seq_locks.get(sequence_id)
                if lock is None:
                    lock = asyncio.Lock()
                    self._seq_locks[sequence_id] = lock
        return lock

    def get_sequence(self, sequence_id: str) -> Optional[TherapeuticSequence]:
        """Retrieve a sequence by ID. Checks L1 memory, then L2 Redis."""
        # L1: in-memory
        seq = self._sequences.get(sequence_id)
        if seq is not None:
            return seq

        # L2: Redis (if available)
        if self._redis is not None:
            try:
                import json
                key = f"adam:retargeting:sequence:{sequence_id}"
                data = self._redis.get(key)
                if data:
                    seq = TherapeuticSequence.model_validate_json(data)
                    # Promote to L1
                    self._sequences[sequence_id] = seq
                    return seq
            except Exception as e:
                logger.debug("Redis sequence lookup failed: %s", e)

        return None

    def _persist_sequence(self, sequence: TherapeuticSequence) -> None:
        """Persist sequence to L1 memory + L2 Redis.

        Thread-safe: uses _storage_lock to protect dict insert + eviction
        so concurrent create_sequence calls don't evict each other's entries.
        """
        with self._storage_lock:
            # L1: memory (with eviction)
            self._sequences[sequence.sequence_id] = sequence
            if len(self._sequences) > self.MAX_L1_SEQUENCES:
                # Evict oldest (first inserted)
                oldest_key = next(iter(self._sequences))
                del self._sequences[oldest_key]
                # Clean up the corresponding sequence lock
                self._seq_locks.pop(oldest_key, None)

        # L2: Redis (if available) — outside lock since Redis is I/O
        if self._redis is not None:
            try:
                key = f"adam:retargeting:sequence:{sequence.sequence_id}"
                self._redis.setex(
                    key,
                    self.SEQUENCE_TTL_SECONDS,
                    sequence.model_dump_json(),
                )
            except Exception as e:
                logger.debug("Redis sequence persist failed: %s", e)

    # --- Internal helpers ---

    def _apply_options_filter(
        self,
        diagnosis: ConversionBarrierDiagnosis,
    ) -> ConversionBarrierDiagnosis:
        """Filter mechanism recommendation through Options Framework.

        The Options Framework defines which mechanisms are allowed/excluded
        per conversion stage. E.g., UNAWARE stage excludes action-oriented
        mechanisms like implementation_intention.
        """
        option = self._options.get_active_option(diagnosis.conversion_stage)
        allowed = self._options.get_allowed_mechanisms(option, diagnosis.primary_barrier)

        if allowed and diagnosis.recommended_mechanism not in allowed:
            # Override with the first allowed mechanism
            old_mech = diagnosis.recommended_mechanism
            diagnosis.recommended_mechanism = allowed[0]
            diagnosis.mechanism_rationale += (
                f" Options filter: {old_mech.value} excluded for "
                f"stage={diagnosis.conversion_stage.value}, "
                f"replaced with {allowed[0].value}."
            )
        return diagnosis

    def _check_frustration(
        self,
        diagnosis: ConversionBarrierDiagnosis,
        sequence: TherapeuticSequence,
    ) -> None:
        """Check if the recommended mechanism targets a dimension that
        conflicts with the previous touch's target dimension.

        If frustration is detected, log a warning. Future enhancement:
        swap to a non-conflicting mechanism.
        """
        if not sequence.touches_delivered or not diagnosis.primary_alignment_gaps:
            return

        last_touch = sequence.touches_delivered[-1]
        last_dim = last_touch.target_alignment_dimension
        current_dim = diagnosis.primary_alignment_gaps[0].dimension if diagnosis.primary_alignment_gaps else ""

        if not last_dim or not current_dim:
            return

        from adam.retargeting.engines.barrier_diagnostic import ConversionBarrierDiagnosticEngine
        conflicts = ConversionBarrierDiagnosticEngine.get_frustrated_conflicts(last_dim)

        for conflicting_dim, r in conflicts:
            if conflicting_dim == current_dim:
                logger.warning(
                    "FRUSTRATION: Touch %d targets %s which conflicts with "
                    "previous touch's %s (r=%.3f). Consider sequencing differently.",
                    len(sequence.touches_delivered) + 1, current_dim, last_dim, r,
                )

    def _record_outcome(
        self,
        sequence: TherapeuticSequence,
        outcome: BarrierResolutionOutcome,
    ) -> None:
        """Record an outcome in the sequence's effectiveness log."""
        mech = outcome.mechanism_deployed.value
        if mech not in sequence.mechanism_effectiveness_log:
            sequence.mechanism_effectiveness_log[mech] = []

        score = self._compute_reward(outcome)
        sequence.mechanism_effectiveness_log[mech].append(score)

        # Track engagement for CTR suppression
        if outcome.engagement_type:
            sequence.engaged_count += 1

        # Also store by touch_id for reliable out-of-order lookup
        if not hasattr(sequence, "_touch_outcomes"):
            sequence._touch_outcomes = {}  # type: ignore[attr-defined]
        sequence._touch_outcomes[outcome.touch_id] = score  # type: ignore[attr-defined]

    def _compute_reward(self, outcome: BarrierResolutionOutcome) -> float:
        """Compute composite reward for Thompson Sampling update.

        Weighted: 0.1 * engagement + 0.3 * stage_advance + 0.6 * conversion
        """
        reward = 0.0
        if outcome.engagement_type:
            reward += 0.1
        if outcome.stage_advanced:
            reward += 0.3
        if outcome.converted:
            reward += 0.6
        return min(1.0, reward)

    def _build_touch_history(
        self, sequence: TherapeuticSequence
    ) -> List[Dict]:
        """Convert sequence touches to the dict format used by engines.

        Uses touch_id-keyed outcome lookup (not position index) to handle
        out-of-order outcome arrival correctly.
        """
        history = []
        # Build a touch_id → outcome score map from the per-touch outcomes
        # stored in _touch_outcomes (populated by _record_outcome)
        touch_outcomes = getattr(sequence, "_touch_outcomes", {})

        for i, touch in enumerate(sequence.touches_delivered):
            # Lookup by touch_id (reliable) or fall back to position estimate
            outcome_score = touch_outcomes.get(touch.touch_id, None)
            if outcome_score is None:
                # Fallback: check mechanism log by counting position
                mech = touch.mechanism.value
                mech_outcomes = sequence.mechanism_effectiveness_log.get(mech, [])
                # Count how many of THIS mechanism's touches came before this one
                prior_same_mech = sum(
                    1 for t in sequence.touches_delivered[:i]
                    if t.mechanism.value == mech
                )
                if prior_same_mech < len(mech_outcomes):
                    outcome_score = mech_outcomes[prior_same_mech]

            engaged = outcome_score is not None and outcome_score > 0.05

            entry = {
                "mechanism": touch.mechanism.value,
                "engagement_occurred": engaged,
                "hours_since_previous": touch.min_hours_after_previous if i > 0 else 0,
                "hours_since_delivery": 24.0 * (len(sequence.touches_delivered) - i),
                "delivered_at": (
                    sequence.started_at.timestamp() + i * 86400
                    if sequence.started_at else 0
                ),
                "outcome": "engaged" if engaged else "ignored",
                "touch_id": touch.touch_id,
            }
            history.append(entry)

        return history

    def generate_learning_signal(
        self,
        sequence: TherapeuticSequence,
        touch: TherapeuticTouch,
        outcome: BarrierResolutionOutcome,
    ) -> MechanismEffectivenessSignal:
        """Generate a learning signal for the Gradient Bridge.

        This signal feeds the cross-campaign learning loop — every
        outcome teaches the ENTIRE system, not just this sequence.
        """
        return MechanismEffectivenessSignal(
            sequence_id=sequence.sequence_id,
            touch_id=touch.touch_id,
            archetype_id=sequence.archetype_id,
            barrier_category=touch.target_barrier,
            alignment_dimension_targeted=touch.target_alignment_dimension,
            mechanism_deployed=touch.mechanism,
            scaffold_level=touch.scaffold_level,
            construal_level=touch.construal_level,
            narrative_chapter=touch.narrative_chapter,
            engagement_occurred=outcome.engagement_type is not None,
            stage_advanced=outcome.stage_advanced,
            converted=outcome.converted,
            barrier_resolved=outcome.barrier_resolved,
            outcome_score=self._compute_reward(outcome),
            reactance_indicator=(
                -0.1 if outcome.engagement_type else 0.1
            ),
        )
