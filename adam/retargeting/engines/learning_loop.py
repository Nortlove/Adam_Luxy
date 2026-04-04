# =============================================================================
# Therapeutic Retargeting Engine — Learning Loop
# Location: adam/retargeting/engines/learning_loop.py
# Spec: Enhancement #33, Session 33-8
# =============================================================================

"""
Learning Loop — Closes the feedback loop between outcomes and posteriors.

Two learning paths:
1. SYSTEM-LEVEL (cross-campaign): Every outcome updates corpus → category →
   brand posteriors. New campaigns cold-start from this accumulated wisdom.
2. CAMPAIGN-LEVEL (within-campaign): Each outcome updates campaign → sequence
   posteriors. The next touch in this sequence benefits immediately.

Integration with existing OutcomeHandler:
- Step 13 in outcome_handler.py calls HierarchicalPriorManager.update_all_levels()
- This module provides the retargeting-specific learning logic that wraps
  around the prior manager and generates learning signals for the Gradient Bridge.
"""

import logging
import math
from typing import Any, Dict, List, Optional

from adam.retargeting.models.enums import BarrierCategory, TherapeuticMechanism
from adam.retargeting.models.diagnostics import BarrierResolutionOutcome
from adam.retargeting.models.sequences import TherapeuticSequence, TherapeuticTouch
from adam.retargeting.models.learning import (
    MechanismEffectivenessSignal,
    SequenceLearningReport,
)
from adam.retargeting.engines.prior_manager import HierarchicalPriorManager

logger = logging.getLogger(__name__)


def _safe_log(p: float) -> float:
    """Safe log for likelihood computation. Clamps to avoid -inf."""
    return math.log(max(p, 1e-6))


class RetargetingLearningLoop:
    """Orchestrates learning from retargeting outcomes.

    Responsibilities:
    1. Process touch outcomes → update hierarchical posteriors
    2. Generate MechanismEffectivenessSignal for Gradient Bridge
    3. Generate SequenceLearningReport when sequence completes
    4. Track mechanism interaction effects (which pairs work together)
    5. Detect archetype reclassification signals
    """

    def __init__(
        self,
        prior_manager: Optional[HierarchicalPriorManager] = None,
        event_bus=None,
        user_posterior_manager=None,
    ):
        self._prior_manager = prior_manager or HierarchicalPriorManager()
        self._event_bus = event_bus
        # Enhancement #36: within-subject repeated measures
        self._user_posterior_manager = user_posterior_manager

    async def process_touch_outcome(
        self,
        sequence: TherapeuticSequence,
        touch: TherapeuticTouch,
        outcome: BarrierResolutionOutcome,
        context: Optional[Dict[str, str]] = None,
        processing_depth_weight: float = 1.0,
    ) -> Dict[str, Any]:
        """Process a single touch outcome through the full learning pipeline.

        This is the main entry point called by the sequence orchestrator
        after observing an outcome.

        Args:
            processing_depth_weight: Enhancement #34 processing depth weight
                (0.05-1.0). Scales all posterior updates so unprocessed
                impressions produce minimal learning signal.

        Returns:
            Dict with learning results: levels_updated, signals_generated, etc.
        """
        context = context or {}
        ctx_with_seq = {
            **context,
            "sequence_id": sequence.sequence_id,
            "user_id": sequence.user_id,
        }
        results: Dict[str, Any] = {}

        # 1. Compute composite reward
        reward = self._compute_reward(outcome)

        # 2. Enhancement #36: Update per-user posteriors (within-subject)
        # This must happen BEFORE population update so we can get the
        # design-effect weight for population-level discounting.
        design_effect_weight = None
        if self._user_posterior_manager is not None:
            user_profile = self._user_posterior_manager.update_user_posterior(
                user_id=sequence.user_id,
                brand_id=sequence.brand_id,
                mechanism=touch.mechanism.value,
                barrier=touch.target_barrier.value,
                archetype_id=sequence.archetype_id,
                reward=reward,
                touch_position=touch.position_in_sequence,
                context=ctx_with_seq,
            )
            design_effect_weight = user_profile.design_effect_weight
            results["user_profile_updated"] = True
            results["user_touches_observed"] = user_profile.total_touches_observed
            results["user_mechanisms_tried"] = user_profile.mechanisms_tried
            results["design_effect_weight"] = design_effect_weight

        # 3. Update hierarchical posteriors (ALL 6 levels, with design-effect discount)
        # Enhancement #34: processing_depth_weight scales the base weight so
        # unprocessed impressions (w=0.05) barely shift posteriors at any level.
        levels = self._prior_manager.update_all_levels(
            mechanism=touch.mechanism.value,
            barrier=touch.target_barrier.value,
            archetype=sequence.archetype_id,
            reward=reward,
            context=ctx_with_seq,
            weight=processing_depth_weight,
            design_effect_weight=design_effect_weight,
        )
        results["levels_updated"] = levels

        # 3b. Update Neural-LinUCB arms (Session 34-3)
        # Neural-LinUCB needs the bilateral edge context + mechanism + reward
        # to update its per-arm ridge regression parameters.
        if context and context.get("bilateral_edge"):
            try:
                from adam.retargeting.engines.mechanism_selector import (
                    BayesianMechanismSelector,
                )
                from adam.core.dependencies import Infrastructure, LearningComponents
                infra = Infrastructure.get_instance()
                components = LearningComponents.get_instance(infra)
                if hasattr(components, '_barrier_diagnostic_engine'):
                    diag_engine = components.barrier_diagnostic_engine
                    if diag_engine and hasattr(diag_engine, '_mechanism_selector'):
                        diag_engine._mechanism_selector.update_neural_linucb(
                            bilateral_edge=context["bilateral_edge"],
                            mechanism=touch.mechanism.value,
                            reward=reward * processing_depth_weight,
                        )
                        results["neural_linucb_updated"] = True
            except Exception as e:
                logger.debug("Neural-LinUCB arm update skipped: %s", e)

        # 3. Generate learning signal for Gradient Bridge
        signal = MechanismEffectivenessSignal(
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
            outcome_score=reward,
            reactance_indicator=-0.1 if outcome.engagement_type else 0.1,
        )
        results["learning_signal"] = signal

        # 4. Publish event (if event bus available)
        if self._event_bus:
            try:
                await self._event_bus.publish(
                    "retargeting.outcome.observed",
                    {
                        "sequence_id": sequence.sequence_id,
                        "touch_id": touch.touch_id,
                        "mechanism": touch.mechanism.value,
                        "barrier": touch.target_barrier.value,
                        "archetype": sequence.archetype_id,
                        "reward": reward,
                        "converted": outcome.converted,
                    },
                )
                results["event_published"] = True
            except Exception as e:
                logger.debug("Event publish failed: %s", e)
                results["event_published"] = False

        # 5. Check for archetype reclassification signals
        reclass = self._check_reclassification(sequence, outcome)
        if reclass:
            results["reclassification_signal"] = reclass

        return results

    async def generate_sequence_report(
        self,
        sequence: TherapeuticSequence,
    ) -> SequenceLearningReport:
        """Generate comprehensive learning report when sequence completes.

        Fed back to the Bayesian prior hierarchy for cross-user,
        cross-archetype, and cross-brand learning.
        """
        # Collect all barriers diagnosed and resolved
        barriers_diagnosed = []
        barriers_resolved = []
        barriers_unresolved = []

        # Build mechanism outcome signals
        mechanism_outcomes: List[MechanismEffectivenessSignal] = []

        for touch in sequence.touches_delivered:
            if touch.target_barrier not in barriers_diagnosed:
                barriers_diagnosed.append(touch.target_barrier)

            # Check if this barrier's mechanism had success
            mech_log = sequence.mechanism_effectiveness_log.get(
                touch.mechanism.value, []
            )
            if mech_log and max(mech_log) > 0.3:
                if touch.target_barrier not in barriers_resolved:
                    barriers_resolved.append(touch.target_barrier)

        barriers_unresolved = [
            b for b in barriers_diagnosed if b not in barriers_resolved
        ]

        # Stage trajectory
        stage_trajectory = []
        # We don't have per-touch stage records in the current model,
        # but we can infer from touch positions and the sequence status
        if sequence.status == "converted":
            from adam.retargeting.models.enums import ConversionStage
            stage_trajectory = [
                ConversionStage.EVALUATING,
                ConversionStage.INTENDING,
                ConversionStage.CONVERTED,
            ]

        # Compute total days
        total_days = 0
        if sequence.started_at and sequence.completed_at:
            delta = sequence.completed_at - sequence.started_at
            total_days = max(1, delta.days)

        # Key insight
        insight = self._generate_insight(sequence, barriers_resolved)

        return SequenceLearningReport(
            sequence_id=sequence.sequence_id,
            user_id=sequence.user_id,
            brand_id=sequence.brand_id,
            archetype_id=sequence.archetype_id,
            final_status=sequence.status,
            total_touches=len(sequence.touches_delivered),
            total_days=total_days,
            converted=sequence.status == "converted",
            mechanism_outcomes=mechanism_outcomes,
            barriers_diagnosed=barriers_diagnosed,
            barriers_resolved=barriers_resolved,
            barriers_unresolved=barriers_unresolved,
            stage_trajectory=stage_trajectory,
            reactance_trajectory=[],  # Would need per-touch tracking
            peak_reactance=sequence.cumulative_reactance,
            reclassification_occurred=sequence.reclassified,
            reclassified_to=sequence.original_archetype_id,
            key_insight=insight,
        )

    def _compute_reward(self, outcome: BarrierResolutionOutcome) -> float:
        """Compute composite reward: 0.1*engagement + 0.3*stage + 0.6*conversion."""
        reward = 0.0
        if outcome.engagement_type:
            reward += 0.1
        if outcome.stage_advanced:
            reward += 0.3
        if outcome.converted:
            reward += 0.6
        return min(1.0, reward)

    # Archetype → mechanism affinity profiles (which mechanisms each archetype
    # responds to). Derived from bilateral edge analysis + personality research.
    # Used for Bayesian reclassification: P(archetype|mechanism_effectiveness).
    _ARCHETYPE_MECHANISM_AFFINITY: Dict[str, Dict[str, float]] = {
        "careful_truster": {
            "evidence_proof": 0.8, "social_proof_matched": 0.7, "anxiety_resolution": 0.6,
            "narrative_transportation": 0.4, "construal_shift": 0.3,
        },
        "status_seeker": {
            "construal_shift": 0.7, "narrative_transportation": 0.7, "vivid_scenario": 0.6,
            "evidence_proof": 0.3, "social_proof_matched": 0.4,
        },
        "easy_decider": {
            "frustration_control": 0.8, "micro_commitment": 0.7, "price_anchor": 0.6,
            "implementation_intention": 0.5, "evidence_proof": 0.3,
        },
        "achiever": {
            "evidence_proof": 0.6, "construal_shift": 0.5, "claude_argument": 0.7,
            "social_proof_matched": 0.5, "implementation_intention": 0.6,
        },
        "guardian": {
            "evidence_proof": 0.7, "anxiety_resolution": 0.8, "social_proof_matched": 0.6,
            "loss_framing": 0.5, "narrative_transportation": 0.3,
        },
        "explorer": {
            "narrative_transportation": 0.8, "vivid_scenario": 0.7, "novelty_disruption": 0.7,
            "construal_shift": 0.5, "evidence_proof": 0.3,
        },
        "connector": {
            "social_proof_matched": 0.8, "narrative_transportation": 0.7, "vivid_scenario": 0.6,
            "evidence_proof": 0.4, "autonomy_restoration": 0.5,
        },
        "analyst": {
            "evidence_proof": 0.9, "claude_argument": 0.8, "construal_shift": 0.5,
            "social_proof_matched": 0.3, "narrative_transportation": 0.2,
        },
    }

    def _check_reclassification(
        self,
        sequence: TherapeuticSequence,
        outcome: BarrierResolutionOutcome,
    ) -> Optional[Dict[str, Any]]:
        """Detect if behavioral evidence suggests archetype reclassification.

        Uses Bayesian approach: compute P(archetype|observed mechanism outcomes)
        for ALL archetypes and flag if a different archetype has higher
        posterior probability than the current classification.

        Requires at least 3 mechanism outcomes to have meaningful signal.
        """
        log = sequence.mechanism_effectiveness_log
        if not log or sum(len(v) for v in log.values()) < 3:
            return None

        # Compute log-likelihood for each archetype given observed outcomes
        current_archetype = sequence.archetype_id
        best_archetype = current_archetype
        best_score = float("-inf")
        scores: Dict[str, float] = {}

        for archetype, affinities in self._ARCHETYPE_MECHANISM_AFFINITY.items():
            score = 0.0
            for mech, outcomes in log.items():
                affinity = affinities.get(mech, 0.3)  # Default low affinity
                for outcome_val in outcomes:
                    if outcome_val > 0.05:
                        # Success: P(success|archetype) = affinity
                        score += _safe_log(affinity)
                    else:
                        # Failure: P(failure|archetype) = 1 - affinity
                        score += _safe_log(1.0 - affinity)

            scores[archetype] = score
            if score > best_score:
                best_score = score
                best_archetype = archetype

        # Only flag if a DIFFERENT archetype has meaningfully higher score
        current_score = scores.get(current_archetype, float("-inf"))
        if (
            best_archetype != current_archetype
            and best_score - current_score > 1.0  # Log-likelihood ratio > e^1 ≈ 2.7x
        ):
            return {
                "signal": "reclassification_candidate",
                "current_archetype": current_archetype,
                "current_score": round(current_score, 3),
                "suggested_archetype": best_archetype,
                "suggested_score": round(best_score, 3),
                "likelihood_ratio": round(best_score - current_score, 3),
                "all_scores": {k: round(v, 3) for k, v in scores.items()},
            }

        return None

    def _generate_insight(
        self,
        sequence: TherapeuticSequence,
        barriers_resolved: List[BarrierCategory],
    ) -> str:
        """Generate human-readable key insight for the sequence."""
        if sequence.status == "converted":
            mechs_used = list(sequence.mechanism_effectiveness_log.keys())
            return (
                f"Converted {sequence.archetype_id} in {len(sequence.touches_delivered)} "
                f"touches using {', '.join(mechs_used)}. "
                f"Barriers resolved: {[b.value for b in barriers_resolved]}."
            )
        elif sequence.status == "suppressed":
            return (
                f"Suppressed after {len(sequence.touches_delivered)} touches. "
                f"Reactance={sequence.cumulative_reactance:.2f}."
            )
        else:
            return (
                f"Sequence ended ({sequence.status}) after "
                f"{len(sequence.touches_delivered)} touches."
            )
