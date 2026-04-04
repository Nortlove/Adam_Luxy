# =============================================================================
# Therapeutic Retargeting Engine — Bayesian Mechanism Selection Engine
# Location: adam/retargeting/engines/mechanism_selector.py
# Spec: Enhancement #33, Section E.2
# =============================================================================

"""
Bayesian Mechanism Selection Engine

Uses Thompson Sampling via the HierarchicalPriorManager to select which
therapeutic mechanism to deploy for a given barrier x archetype x personality
profile.

Each (mechanism, barrier, archetype) triple has a Beta(alpha, beta) prior
at every level of the hierarchy. Selection samples from the EFFECTIVE
posterior (blended across levels) and applies modulation from:
- Big Five personality susceptibility
- Current reactance level
- PKM (Persuasion Knowledge Model) phase
- Recent failure history

This is a PLATFORM SERVICE — used by:
- Retargeting engine: per-touch mechanism selection
- Bilateral cascade: first-touch barrier-aware mechanism selection
- Copy generation: mechanism -> creative parameter mapping
"""

import logging
from typing import Dict, List, Optional, Tuple

from adam.constants import BARRIER_MECHANISM_CANDIDATES, THERAPEUTIC_TO_CIALDINI
from adam.retargeting.models.enums import (
    BarrierCategory,
    ConversionStage,
    TherapeuticMechanism,
)
from adam.retargeting.engines.prior_manager import HierarchicalPriorManager
import numpy as np

from adam.retargeting.personality_mechanism_matrix import (
    PERSONALITY_MECHANISM_SUSCEPTIBILITY,
)

logger = logging.getLogger(__name__)

# Mechanisms that are safe under high reactance (autonomy-preserving)
_AUTONOMY_SAFE_MECHANISMS = {
    TherapeuticMechanism.AUTONOMY_RESTORATION,
    TherapeuticMechanism.NARRATIVE_TRANSPORTATION,
    TherapeuticMechanism.SOCIAL_PROOF_MATCHED,
    TherapeuticMechanism.EVIDENCE_PROOF,
    TherapeuticMechanism.VIVID_SCENARIO,
}

# Mechanisms that feel "salesy" under PKM scrutiny (phase 2-3 penalty)
_PKM_PENALIZED_MECHANISMS = {
    TherapeuticMechanism.MICRO_COMMITMENT,
    TherapeuticMechanism.LOSS_FRAMING,
    TherapeuticMechanism.DISSONANCE_ACTIVATION,
    TherapeuticMechanism.PRICE_ANCHOR,
}

# Stage-appropriate mechanism mapping with calibrated boost magnitudes.
# From Krebs et al. (2010, k=88): stage-matched interventions produce
# calibrated_d=0.30 improvement. Converted to alpha multiplier via:
#   P(success) boost ≈ 0.06 (from Φ(0.30/√2) - 0.5)
#   Alpha multiplier = 1 + (0.06 * 4) / base_alpha ≈ 1.08 for weak prior
# We use 1.10 as the stage-MATCHED boost (conservative) and 0.90 for
# stage-MISMATCHED penalty (action-oriented on pre-contemplative = resistance).
_STAGE_MECHANISM_FIT = {
    ConversionStage.CURIOUS: {
        "matched": {
            TherapeuticMechanism.NARRATIVE_TRANSPORTATION,
            TherapeuticMechanism.VIVID_SCENARIO,
        },
        "mismatched": {
            TherapeuticMechanism.IMPLEMENTATION_INTENTION,  # Action on pre-contemplative
            TherapeuticMechanism.LOSS_FRAMING,
            TherapeuticMechanism.PRICE_ANCHOR,
        },
    },
    ConversionStage.EVALUATING: {
        "matched": {
            TherapeuticMechanism.EVIDENCE_PROOF,
            TherapeuticMechanism.SOCIAL_PROOF_MATCHED,
            TherapeuticMechanism.CLAUDE_ARGUMENT,
        },
        "mismatched": set(),
    },
    ConversionStage.INTENDING: {
        "matched": {
            TherapeuticMechanism.IMPLEMENTATION_INTENTION,
            TherapeuticMechanism.OWNERSHIP_REACTIVATION,
            TherapeuticMechanism.MICRO_COMMITMENT,
        },
        "mismatched": {
            TherapeuticMechanism.NARRATIVE_TRANSPORTATION,  # Too abstract for action stage
        },
    },
    ConversionStage.STALLED: {
        "matched": {
            TherapeuticMechanism.OWNERSHIP_REACTIVATION,
            TherapeuticMechanism.LOSS_FRAMING,
            TherapeuticMechanism.IMPLEMENTATION_INTENTION,
        },
        "mismatched": set(),
    },
}

# Calibrated multipliers (from TTM d=0.30, lab-to-production factor 0.62)
_STAGE_MATCHED_MULTIPLIER = 1.10    # Small boost for stage-appropriate
_STAGE_MISMATCHED_MULTIPLIER = 0.85  # Penalty: generates resistance (TTM)


class BayesianMechanismSelector:
    """Selects the optimal therapeutic mechanism using Thompson Sampling.

    Priors are initialized from research effect sizes and inherited through
    the 5-level hierarchy (corpus -> category -> brand -> campaign -> sequence).

    Personality interaction weights modify the sampling:
    if a mechanism is +1 susceptible for the user's dominant trait,
    the effective alpha is multiplied by 1.3 (30% bonus).
    If -1 resistant, alpha is multiplied by 0.7 (30% penalty).
    """

    def __init__(
        self,
        prior_manager: Optional[HierarchicalPriorManager] = None,
        neural_linucb=None,
    ):
        self._prior_manager = prior_manager or HierarchicalPriorManager()
        # Neural-LinUCB: used when bilateral edge dims are available (L3+)
        # Lazy-initialized on first use if not provided
        self._neural_linucb = neural_linucb
        self._neural_linucb_initialized = neural_linucb is not None
        # Last mechanism selection probabilities (for counterfactual learning)
        self._last_mechanism_probabilities: Dict[str, float] = {}

    async def select(
        self,
        barrier: BarrierCategory,
        archetype_id: str,
        stage: ConversionStage = ConversionStage.EVALUATING,
        reactance_level: float = 0.0,
        pk_phase: int = 1,
        ownership_level: float = 0.0,
        touch_history: Optional[List[Dict]] = None,
        user_personality: Optional[Dict[str, float]] = None,
        context: Optional[Dict[str, str]] = None,
        bilateral_edge: Optional[Dict[str, float]] = None,
        user_profile=None,
        within_subject_design=None,
        touch_position: int = 0,
    ) -> Tuple[TherapeuticMechanism, float, str]:
        """Select mechanism via Thompson Sampling with personality modulation.

        Enhancement #36 (repeated measures): When user_profile is provided
        with 3+ observations, blends user-level posteriors with population
        posteriors for personalized mechanism selection. When within_subject_design
        indicates this is an exploration slot, delegates to
        WithinSubjectDesigner.select_exploration_mechanism() instead of pure
        Thompson Sampling — deliberately testing a new mechanism to build
        within-user evidence.

        When bilateral_edge is provided (L3+ of cascade), Neural-LinUCB
        adjusts the selection using 43-dimensional context that captures
        non-linear buyer×seller×alignment interactions. When not provided,
        falls back to pure Thompson Sampling.

        Args:
            barrier: The diagnosed primary barrier
            archetype_id: User's archetype
            stage: Current conversion stage
            reactance_level: 0-1 cumulative reactance
            pk_phase: 1-3 persuasion knowledge phase
            ownership_level: 0-1 psychological ownership
            touch_history: Previous touches and outcomes
            user_personality: Big Five scores {openness, conscientiousness, ...}
            context: Hierarchy context for prior lookup
            bilateral_edge: 43-dim bilateral edge for Neural-LinUCB (L3+ only)
            user_profile: Enhancement #36 — UserPosteriorProfile for within-subject posteriors
            within_subject_design: Enhancement #36 — WithinSubjectDesign for exploration/exploitation
            touch_position: Enhancement #36 — current touch position in sequence (1-indexed)

        Returns:
            (mechanism, confidence, rationale)
        """
        touch_history = touch_history or []

        # Get candidates for this barrier
        candidates_str = BARRIER_MECHANISM_CANDIDATES.get(barrier.value, [])
        if not candidates_str:
            return (
                TherapeuticMechanism.EVIDENCE_PROOF,
                0.3,
                f"No candidates for {barrier.value}; defaulting to evidence_proof",
            )

        candidates = [TherapeuticMechanism(c) for c in candidates_str]

        # Filter 1: Remove recently-failed mechanisms
        candidates = self._filter_recent_failures(candidates, touch_history)

        # Filter 2: Reactance constraints
        if reactance_level > 0.7:
            filtered = [m for m in candidates if m in _AUTONOMY_SAFE_MECHANISMS]
            if filtered:
                candidates = filtered

        # -----------------------------------------------------------
        # Enhancement #36: Within-subject exploration routing
        # -----------------------------------------------------------
        # If this is an exploration slot and design says explore,
        # delegate to WithinSubjectDesigner instead of Thompson Sampling.
        if (
            within_subject_design is not None
            and user_profile is not None
            and touch_position > 0
            and within_subject_design.is_exploration_slot(touch_position)
        ):
            from adam.retargeting.engines.repeated_measures import WithinSubjectDesigner
            designer = WithinSubjectDesigner(self._prior_manager)
            exploration_mech = designer.select_exploration_mechanism(
                user_profile=user_profile,
                barrier=barrier.value,
                archetype_id=archetype_id,
                context=context,
            )
            if exploration_mech:
                try:
                    mech = TherapeuticMechanism(exploration_mech)
                    rationale = (
                        f"Within-subject exploration slot (touch {touch_position}): "
                        f"testing {exploration_mech} to build within-user contrast. "
                        f"User has tried {user_profile.mechanisms_tried} mechanisms "
                        f"across {user_profile.total_touches_observed} touches."
                    )
                    return mech, 0.5, rationale
                except ValueError:
                    pass  # Invalid mechanism — fall through to Thompson

        # -----------------------------------------------------------
        # Get posteriors: blend user-level + population-level
        # -----------------------------------------------------------
        posteriors = self._prior_manager.get_all_posteriors_for_barrier(
            barrier.value, archetype_id, context
        )

        # Enhancement #36: When user has 3+ touches, blend in user-level posteriors
        # for tighter, personalized estimates.
        if (
            user_profile is not None
            and user_profile.total_touches_observed >= 3
        ):
            for mech_str, pop_posterior in posteriors.items():
                user_mech = user_profile.mechanism_posteriors.get(mech_str)
                if user_mech and user_mech.sample_count >= 1:
                    # Blend: user_weight increases with observations
                    user_weight = min(1.0, user_mech.sample_count / 3.0)
                    pop_posterior.alpha = (
                        user_weight * user_mech.alpha
                        + (1 - user_weight) * pop_posterior.alpha
                    )
                    pop_posterior.beta = (
                        user_weight * user_mech.beta
                        + (1 - user_weight) * pop_posterior.beta
                    )

        # ── Session 34-3: Neural-LinUCB as PRIMARY selector ──
        #
        # When bilateral context is available (>= 10 dims), Neural-LinUCB
        # is the first-choice selector. It uses the full 50-dim context
        # (alignment + mechanism scores + user longitudinal + nonconscious
        # signals) to learn mechanism-context interactions that Thompson
        # Sampling cannot represent (e.g., "evidence_proof fails when
        # processing_depth is low because the argument isn't evaluated").
        #
        # Thompson Sampling remains as:
        # 1. FALLBACK when bilateral context is sparse (< 10 dims)
        # 2. PRIOR for Neural-LinUCB cold start (UCB explores more)
        # 3. Source of mechanism_probabilities for counterfactual learning

        # Always run Thompson to get probabilities for counterfactual learning
        best_mechanism = None
        best_sample = -1.0
        samples: Dict[TherapeuticMechanism, float] = {}

        for mechanism in candidates:
            posterior = posteriors.get(mechanism.value)
            if posterior is None:
                sample = float(np.random.beta(2.0, 2.0))
            else:
                alpha = posterior.alpha
                beta = posterior.beta

                if user_personality:
                    alpha = self._apply_personality_modulation(
                        alpha, mechanism, user_personality
                    )

                if pk_phase >= 2 and mechanism in _PKM_PENALIZED_MECHANISMS:
                    alpha *= 0.7

                stage_fit = _STAGE_MECHANISM_FIT.get(stage, {})
                if mechanism in stage_fit.get("matched", set()):
                    alpha *= _STAGE_MATCHED_MULTIPLIER
                elif mechanism in stage_fit.get("mismatched", set()):
                    alpha *= _STAGE_MISMATCHED_MULTIPLIER

                if user_profile and abs(user_profile.random_intercept) > 0.01:
                    intercept_shift = user_profile.random_intercept * 0.5
                    alpha = max(0.1, alpha + intercept_shift)

                sample = float(np.random.beta(max(0.1, alpha), max(0.1, beta)))

            samples[mechanism] = sample
            if sample > best_sample:
                best_sample = sample
                best_mechanism = mechanism

        if best_mechanism is None:
            best_mechanism = TherapeuticMechanism.EVIDENCE_PROOF

        thompson_choice = best_mechanism

        # Neural-LinUCB: PRIMARY selector when bilateral context is available.
        # Uses 50-dim context to capture mechanism × context interactions.
        neural_rationale = ""
        if bilateral_edge and len(bilateral_edge) >= 10:
            try:
                linucb = self._get_neural_linucb()
                linucb_result = linucb.select(
                    bilateral_edge=bilateral_edge,
                    candidate_mechanisms=[m.value for m in candidates],
                )
                linucb_mech = TherapeuticMechanism(linucb_result.selected_mechanism)
                if linucb_mech in candidates:
                    best_mechanism = linucb_mech
                    if linucb_mech == thompson_choice:
                        neural_rationale = (
                            f" Neural-LinUCB+Thompson agree: {linucb_result.selected_mechanism} "
                            f"(UCB={linucb_result.ucb_score:.3f}, "
                            f"ctx={len(bilateral_edge)}d, "
                            f"latency={linucb_result.latency_ms:.1f}ms)."
                        )
                    else:
                        neural_rationale = (
                            f" Neural-LinUCB selected: {linucb_result.selected_mechanism} "
                            f"(UCB={linucb_result.ucb_score:.3f}, "
                            f"Thompson preferred: {thompson_choice.value}, "
                            f"ctx={len(bilateral_edge)}d, "
                            f"latency={linucb_result.latency_ms:.1f}ms)."
                        )
            except Exception as e:
                logger.debug("Neural-LinUCB failed, falling back to Thompson: %s", e)

        # Compute confidence from posterior mean (not sample)
        best_posterior = posteriors.get(best_mechanism.value)
        confidence = best_posterior.mean if best_posterior else 0.5

        # Compute mechanism selection probabilities from Thompson samples.
        # These approximate P(selected) if we reran the decision many times.
        # Needed for counterfactual learning (Unified Directive §2.2).
        mechanism_probabilities = {}
        if samples:
            sample_values = np.array([samples.get(m, 0.0) for m in candidates])
            if sample_values.max() > sample_values.min():
                # Softmax of Thompson samples
                exp_vals = np.exp(sample_values - sample_values.max())
                probs = exp_vals / exp_vals.sum()
                for i, m in enumerate(candidates):
                    mechanism_probabilities[m.value] = round(float(probs[i]), 4)
            else:
                # Uniform when all samples are identical
                for m in candidates:
                    mechanism_probabilities[m.value] = round(1.0 / len(candidates), 4)

        # Store probabilities on the instance for downstream access
        self._last_mechanism_probabilities = mechanism_probabilities

        # Generate rationale
        rationale = self._generate_rationale(
            best_mechanism, barrier, archetype_id, confidence,
            samples, reactance_level, pk_phase, stage,
        )
        rationale += neural_rationale

        return best_mechanism, round(confidence, 3), rationale

    def _get_neural_linucb(self):
        """Lazy-initialize Neural-LinUCB on first use."""
        if not self._neural_linucb_initialized:
            from adam.retargeting.engines.neural_linucb import NeuralLinUCBSelector
            self._neural_linucb = NeuralLinUCBSelector()
            self._neural_linucb_initialized = True
        return self._neural_linucb

    def update_neural_linucb(
        self,
        bilateral_edge: Dict[str, float],
        mechanism: str,
        reward: float,
    ) -> None:
        """Update Neural-LinUCB arm with observed outcome.

        Called from the learning loop after each retargeting touch outcome.
        """
        if self._neural_linucb_initialized and self._neural_linucb is not None:
            self._neural_linucb.update(bilateral_edge, mechanism, reward)

    def _filter_recent_failures(
        self,
        candidates: List[TherapeuticMechanism],
        touch_history: List[Dict],
    ) -> List[TherapeuticMechanism]:
        """Remove mechanisms that failed in the last 2 touches."""
        if not touch_history:
            return candidates

        recent_failures = {
            t.get("mechanism")
            for t in touch_history[-2:]
            if not t.get("engagement_occurred", False)
        }

        filtered = [m for m in candidates if m.value not in recent_failures]
        return filtered if filtered else candidates  # Never empty

    def _apply_personality_modulation(
        self,
        alpha: float,
        mechanism: TherapeuticMechanism,
        personality: Dict[str, float],
    ) -> float:
        """Modulate alpha based on Big Five x mechanism susceptibility.

        Uses CONTINUOUS modulation across the full 0-1 trait range,
        not binary thresholds. A trait at 0.7 produces stronger modulation
        than a trait at 0.55, which produces mild modulation.

        Modulation formula: alpha *= (1.0 + direction * intensity * 0.3)
        where intensity = |trait - 0.5| * 2 (0 at midpoint, 1 at extremes)
        """
        cialdini_key = THERAPEUTIC_TO_CIALDINI.get(mechanism.value)
        if not cialdini_key:
            return alpha

        modulated = alpha
        trait_map = {
            "openness": personality.get("openness", 0.5),
            "conscientiousness": personality.get("conscientiousness", 0.5),
            "extraversion": personality.get("extraversion", 0.5),
            "agreeableness": personality.get("agreeableness", 0.5),
            "neuroticism": personality.get("neuroticism", 0.5),
        }

        for trait_name, trait_value in trait_map.items():
            # Compute intensity: 0 at midpoint (0.5), 1 at extremes (0 or 1)
            intensity = abs(trait_value - 0.5) * 2.0

            # Only modulate if there's meaningful deviation from midpoint
            if intensity < 0.1:
                continue

            # Look up susceptibility for high or low end
            if trait_value >= 0.5:
                key = f"{trait_name}_high"
            else:
                key = f"{trait_name}_low"

            susceptibility = PERSONALITY_MECHANISM_SUSCEPTIBILITY.get(key, {})
            direction = susceptibility.get(cialdini_key, 0)

            if direction != 0:
                # Continuous modulation: stronger traits = stronger effect
                # At intensity=1.0 (extreme): alpha *= 1.3 or 0.7
                # At intensity=0.5 (moderate): alpha *= 1.15 or 0.85
                modulated *= (1.0 + direction * intensity * 0.3)

        return modulated

    def _generate_rationale(
        self,
        mechanism: TherapeuticMechanism,
        barrier: BarrierCategory,
        archetype_id: str,
        confidence: float,
        samples: Dict[TherapeuticMechanism, float],
        reactance_level: float,
        pk_phase: int,
        stage: ConversionStage,
    ) -> str:
        """Generate human-readable rationale for mechanism selection."""
        sorted_samples = sorted(
            samples.items(), key=lambda x: x[1], reverse=True
        )
        top3 = [(m.value, f"{s:.3f}") for m, s in sorted_samples[:3]]

        parts = [
            f"For {barrier.value} barrier in {archetype_id} "
            f"(stage={stage.value}): selected {mechanism.value} "
            f"(confidence={confidence:.2f}).",
            f"Thompson samples: {top3}.",
        ]

        if reactance_level > 0.5:
            parts.append(
                f"Reactance={reactance_level:.2f}: autonomy-safe filter applied."
            )
        if pk_phase >= 2:
            parts.append(f"PK phase {pk_phase}: salesy mechanisms penalized.")

        return " ".join(parts)
