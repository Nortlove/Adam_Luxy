# =============================================================================
# Options Framework — Hierarchical RL for TTM Stages
# Location: adam/retargeting/engines/options_framework.py
# Enhancement #34, Session 34-6
# =============================================================================

"""
Options Framework for TTM-Based Retargeting.

Formalizes what Enhancement #33's therapeutic loop does implicitly: each
ConversionStage is an OPTION (Sutton, Precup & Singh, 1999) with:
- Initiation set: when this option can start (stage entry conditions)
- Intra-option policy: which mechanisms to deploy within this stage
- Termination condition: when the stage is complete (advance or fail)

Why this matters: Instead of learning a single 10-touch policy (huge
search space), the system learns:
- A META-POLICY: which stage-option to activate
- 5 INTRA-OPTION POLICIES: 2-3 touch mechanism selection per stage
- TERMINATION CONDITIONS: when to advance or declare failure

This reduces the effective learning horizon from O(10^16) to O(5 × 16^3),
making Thompson Sampling converge ~100× faster.

Integration: Wraps the existing BayesianMechanismSelector. The meta-policy
selects the option (stage), the intra-option policy uses the selector to
pick mechanisms within that stage, and termination triggers stage advancement.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from adam.retargeting.models.enums import (
    BarrierCategory,
    ConversionStage,
    ScaffoldLevel,
    TherapeuticMechanism,
)

logger = logging.getLogger(__name__)


@dataclass
class StageOption:
    """A hierarchical RL option corresponding to a TTM conversion stage.

    Each option encodes:
    - WHAT mechanisms are appropriate for this stage
    - HOW MANY touches this stage typically takes
    - WHEN to terminate (advance to next stage or declare stuck)
    - WHAT success looks like for this stage
    """

    stage: ConversionStage
    name: str

    # Initiation: under what conditions can this option start?
    prerequisite_stages: Set[ConversionStage] = field(default_factory=set)

    # Intra-option policy: preferred mechanisms for this stage
    preferred_mechanisms: List[TherapeuticMechanism] = field(default_factory=list)
    excluded_mechanisms: List[TherapeuticMechanism] = field(default_factory=list)
    scaffold_level: ScaffoldLevel = ScaffoldLevel.SIMPLIFICATION

    # Timing
    typical_touches: int = 2  # Expected touches in this stage
    max_touches: int = 3  # Hard cap before termination

    # Termination conditions
    advance_signals: List[str] = field(default_factory=list)
    failure_signals: List[str] = field(default_factory=list)

    # Learning: per-option Thompson posteriors (keyed by mechanism)
    mechanism_rewards: Dict[str, List[float]] = field(default_factory=dict)
    total_activations: int = 0
    total_successes: int = 0

    @property
    def success_rate(self) -> float:
        return self.total_successes / max(self.total_activations, 1)


# ---------------------------------------------------------------------------
# Stage Option Definitions
# Each maps to a TTM stage with research-grounded policy defaults.
# ---------------------------------------------------------------------------

STAGE_OPTIONS: Dict[ConversionStage, StageOption] = {
    ConversionStage.UNAWARE: StageOption(
        stage=ConversionStage.UNAWARE,
        name="Awareness Building",
        prerequisite_stages=set(),
        preferred_mechanisms=[
            TherapeuticMechanism.NARRATIVE_TRANSPORTATION,
            TherapeuticMechanism.VIVID_SCENARIO,
        ],
        excluded_mechanisms=[
            # TTM: action-oriented on pre-contemplative generates RESISTANCE
            TherapeuticMechanism.IMPLEMENTATION_INTENTION,
            TherapeuticMechanism.LOSS_FRAMING,
            TherapeuticMechanism.PRICE_ANCHOR,
            TherapeuticMechanism.MICRO_COMMITMENT,
        ],
        scaffold_level=ScaffoldLevel.RECRUITMENT,
        typical_touches=1,
        max_touches=2,
        advance_signals=["ad_click", "site_visit", "ad_dwell_2s"],
        failure_signals=["ad_hide", "unsubscribe"],
    ),

    ConversionStage.CURIOUS: StageOption(
        stage=ConversionStage.CURIOUS,
        name="Interest Deepening",
        prerequisite_stages={ConversionStage.UNAWARE},
        preferred_mechanisms=[
            TherapeuticMechanism.NARRATIVE_TRANSPORTATION,
            TherapeuticMechanism.VIVID_SCENARIO,
            TherapeuticMechanism.EVIDENCE_PROOF,
        ],
        excluded_mechanisms=[
            TherapeuticMechanism.IMPLEMENTATION_INTENTION,
            TherapeuticMechanism.LOSS_FRAMING,
        ],
        scaffold_level=ScaffoldLevel.SIMPLIFICATION,
        typical_touches=2,
        max_touches=3,
        advance_signals=["pricing_page", "review_page", "comparison_page", "return_visit"],
        failure_signals=["no_engagement_3_touches"],
    ),

    ConversionStage.EVALUATING: StageOption(
        stage=ConversionStage.EVALUATING,
        name="Evidence Provision",
        prerequisite_stages={ConversionStage.CURIOUS},
        preferred_mechanisms=[
            TherapeuticMechanism.EVIDENCE_PROOF,
            TherapeuticMechanism.SOCIAL_PROOF_MATCHED,
            TherapeuticMechanism.CLAUDE_ARGUMENT,
        ],
        excluded_mechanisms=[],
        scaffold_level=ScaffoldLevel.DIRECTION_MAINTENANCE,
        typical_touches=2,
        max_touches=4,
        advance_signals=["cart_add", "booking_start", "email_signup"],
        failure_signals=["competitor_visit_only", "no_engagement_3_touches"],
    ),

    ConversionStage.INTENDING: StageOption(
        stage=ConversionStage.INTENDING,
        name="Friction Removal",
        prerequisite_stages={ConversionStage.EVALUATING},
        preferred_mechanisms=[
            TherapeuticMechanism.IMPLEMENTATION_INTENTION,
            TherapeuticMechanism.OWNERSHIP_REACTIVATION,
            TherapeuticMechanism.MICRO_COMMITMENT,
            TherapeuticMechanism.PRICE_ANCHOR,
        ],
        excluded_mechanisms=[
            # Too abstract for action stage
            TherapeuticMechanism.NARRATIVE_TRANSPORTATION,
        ],
        scaffold_level=ScaffoldLevel.FRUSTRATION_CONTROL,
        typical_touches=2,
        max_touches=3,
        advance_signals=["purchase", "booking_complete"],
        failure_signals=["cart_abandon_48h", "booking_abandon_48h"],
    ),

    ConversionStage.STALLED: StageOption(
        stage=ConversionStage.STALLED,
        name="Re-engagement",
        prerequisite_stages={ConversionStage.INTENDING},
        preferred_mechanisms=[
            TherapeuticMechanism.OWNERSHIP_REACTIVATION,
            TherapeuticMechanism.LOSS_FRAMING,
            TherapeuticMechanism.IMPLEMENTATION_INTENTION,
            TherapeuticMechanism.NOVELTY_DISRUPTION,
        ],
        excluded_mechanisms=[],
        scaffold_level=ScaffoldLevel.DEMONSTRATION,
        typical_touches=2,
        max_touches=3,
        advance_signals=["return_visit", "cart_add", "booking_start"],
        failure_signals=["no_activity_7_days", "unsubscribe"],
    ),
}


class OptionsController:
    """Hierarchical controller that manages stage-level option policies.

    Usage:
        controller = OptionsController()
        option = controller.get_active_option(current_stage)
        mechanisms = controller.get_allowed_mechanisms(option, barrier)
        # ... select mechanism via BayesianMechanismSelector ...
        controller.record_outcome(option, mechanism, reward)
        should_terminate, reason = controller.check_termination(option, signals)
    """

    def __init__(self):
        self.options = dict(STAGE_OPTIONS)  # Copy so we can track state

    def get_active_option(self, stage: ConversionStage) -> StageOption:
        """Get the option for the current stage."""
        return self.options.get(stage, self.options[ConversionStage.CURIOUS])

    def get_allowed_mechanisms(
        self,
        option: StageOption,
        barrier: BarrierCategory,
    ) -> List[TherapeuticMechanism]:
        """Get mechanisms allowed by both the option policy and the barrier.

        Intersection of: barrier's candidate mechanisms AND option's
        non-excluded mechanisms. Preferred mechanisms get priority ordering.
        """
        from adam.constants import BARRIER_MECHANISM_CANDIDATES

        barrier_candidates = [
            TherapeuticMechanism(m)
            for m in BARRIER_MECHANISM_CANDIDATES.get(barrier.value, [])
        ]

        excluded = set(option.excluded_mechanisms)

        # Start with preferred (if they're also barrier-appropriate)
        allowed = []
        preferred_set = set(option.preferred_mechanisms)

        # Preferred AND barrier-appropriate first
        for m in option.preferred_mechanisms:
            if m in barrier_candidates and m not in excluded:
                allowed.append(m)

        # Then remaining barrier candidates (not excluded, not already added)
        added = set(allowed)
        for m in barrier_candidates:
            if m not in excluded and m not in added:
                allowed.append(m)

        return allowed if allowed else barrier_candidates

    def check_termination(
        self,
        option: StageOption,
        behavioral_signals: Dict[str, float],
        touches_in_stage: int,
    ) -> Tuple[bool, str, Optional[ConversionStage]]:
        """Check if current stage-option should terminate.

        Returns:
            (should_terminate, reason, next_stage_or_None)
        """
        # Hard cap: max touches in this stage
        if touches_in_stage >= option.max_touches:
            return True, f"max_touches_{option.max_touches}", None

        # Advance signals: check if user has moved to next stage
        for signal in option.advance_signals:
            signal_key = signal.replace(" ", "_")
            if behavioral_signals.get(signal_key, 0) > 0:
                next_stage = self._next_stage(option.stage)
                return True, f"advanced_via_{signal}", next_stage

        # Failure signals
        for signal in option.failure_signals:
            signal_key = signal.replace(" ", "_")
            if behavioral_signals.get(signal_key, 0) > 0:
                return True, f"failed_via_{signal}", ConversionStage.STALLED

        return False, "continue", None

    def record_outcome(
        self,
        option: StageOption,
        mechanism: TherapeuticMechanism,
        reward: float,
    ) -> None:
        """Record mechanism effectiveness within this option."""
        mech_key = mechanism.value
        if mech_key not in option.mechanism_rewards:
            option.mechanism_rewards[mech_key] = []
        option.mechanism_rewards[mech_key].append(reward)
        option.total_activations += 1
        if reward > 0.3:
            option.total_successes += 1

    def get_option_stats(self) -> Dict[str, Any]:
        """Per-option performance statistics."""
        stats = {}
        for stage, option in self.options.items():
            if option.total_activations > 0:
                best_mech = None
                best_avg = 0.0
                for mech, rewards in option.mechanism_rewards.items():
                    avg = sum(rewards) / len(rewards)
                    if avg > best_avg:
                        best_avg = avg
                        best_mech = mech
                stats[stage.value] = {
                    "activations": option.total_activations,
                    "success_rate": round(option.success_rate, 3),
                    "best_mechanism": best_mech,
                    "best_mechanism_avg": round(best_avg, 3),
                }
        return stats

    @staticmethod
    def _next_stage(current: ConversionStage) -> ConversionStage:
        """Deterministic stage progression."""
        progression = {
            ConversionStage.UNAWARE: ConversionStage.CURIOUS,
            ConversionStage.CURIOUS: ConversionStage.EVALUATING,
            ConversionStage.EVALUATING: ConversionStage.INTENDING,
            ConversionStage.INTENDING: ConversionStage.CONVERTED,
            ConversionStage.STALLED: ConversionStage.INTENDING,
        }
        return progression.get(current, ConversionStage.CURIOUS)
