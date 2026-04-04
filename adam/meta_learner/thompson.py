# =============================================================================
# ADAM Thompson Sampling Engine
# Location: adam/meta_learner/thompson.py
# =============================================================================

"""
THOMPSON SAMPLING ENGINE

Implements Thompson Sampling for modality selection.

Key features:
- Beta posterior distributions for each modality
- Context-aware constraint checking
- Exploration-exploitation balance
- Decay for non-stationary environments
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import numpy as np

from adam.meta_learner.models import (
    LearningModality,
    ExecutionPath,
    ModalityPosterior,
    ContextFeatures,
    ModalityConstraint,
    RoutingDecision,
    PosteriorState,
    DataRichness,
    MODALITY_TO_PATH,
    DEFAULT_MODALITY_CONSTRAINTS,
)

logger = logging.getLogger(__name__)


class ThompsonSamplingEngine:
    """
    Thompson Sampling engine for modality selection.
    
    Uses Beta posteriors to balance exploration and exploitation.
    Context features determine which modalities are eligible.
    """
    
    def __init__(
        self,
        posterior_state: Optional[PosteriorState] = None,
        constraints: Optional[Dict[LearningModality, ModalityConstraint]] = None,
        exploration_bonus: float = 0.1,
        decay_factor: float = 0.995,
    ):
        """
        Initialize the Thompson Sampling engine.
        
        Args:
            posterior_state: Existing posterior state, or None to initialize
            constraints: Custom constraints, or None for defaults
            exploration_bonus: Bonus for under-explored modalities
            decay_factor: Factor for posterior decay (adaptation)
        """
        self.posterior_state = posterior_state or PosteriorState()
        self.posterior_state.initialize_posteriors()
        
        self.constraints = constraints or DEFAULT_MODALITY_CONSTRAINTS
        self.exploration_bonus = exploration_bonus
        self.decay_factor = decay_factor
    
    def select_modality(
        self,
        request_id: str,
        user_id: str,
        context: ContextFeatures,
    ) -> RoutingDecision:
        """
        Select a modality using Thompson Sampling.
        
        Args:
            request_id: Unique request identifier
            user_id: User identifier
            context: Context features for constraint checking
        
        Returns:
            RoutingDecision with selected modality and path
        """
        start_time = datetime.now(timezone.utc)
        
        # Step 1: Determine eligible modalities
        eligible, constraints_failed = self._check_constraints(context)
        
        if not eligible:
            # No modalities eligible - fall back to bandit
            logger.warning(f"No modalities eligible for {user_id}, falling back to bandit")
            eligible = [LearningModality.REINFORCEMENT_BANDIT]
        
        # Step 2: Sample from posteriors
        sampled_values: Dict[str, float] = {}
        for modality in LearningModality:
            posterior = self.posterior_state.get_posterior(modality)
            sampled_values[modality.value] = posterior.sample()
        
        # Step 3: Apply adjustments for exploration (buyer-uncertainty-aware)
        # High buyer uncertainty → stronger exploration bonus → explore more
        # aggressively for cold buyers where information value is highest.
        buyer_uncertainty_multiplier = 1.0
        if context.buyer_uncertainty_level > 0.5:
            # Scale exploration bonus by buyer uncertainty (1x-3x)
            buyer_uncertainty_multiplier = 1.0 + 2.0 * (context.buyer_uncertainty_level - 0.5)
        elif context.buyer_interaction_count > 20:
            # Well-known buyers: reduce exploration to exploit
            buyer_uncertainty_multiplier = 0.5

        adjusted_values: Dict[str, float] = {}
        for modality in LearningModality:
            base_value = sampled_values[modality.value]

            # Apply exploration bonus for under-explored modalities
            posterior = self.posterior_state.get_posterior(modality)
            if posterior.sample_count < 20:
                exploration_factor = (
                    self.exploration_bonus
                    * (1 - posterior.sample_count / 20)
                    * buyer_uncertainty_multiplier
                )
            else:
                exploration_factor = 0.0

            # Zero out ineligible modalities
            if modality not in eligible:
                adjusted_values[modality.value] = 0.0
            else:
                adjusted_values[modality.value] = base_value + exploration_factor
        
        # Step 4: Select best eligible modality
        best_modality = max(
            eligible,
            key=lambda m: adjusted_values[m.value]
        )
        
        # Step 5: Determine execution path
        execution_path = MODALITY_TO_PATH[best_modality]
        
        # Step 6: Calculate selection confidence
        posterior = self.posterior_state.get_posterior(best_modality)
        selection_confidence = posterior.confidence
        
        # Calculate exploration probability
        exploration_prob = self._calculate_exploration_probability(
            best_modality, adjusted_values
        )
        
        # Build decision
        end_time = datetime.now(timezone.utc)
        latency_ms = (end_time - start_time).total_seconds() * 1000
        
        decision = RoutingDecision(
            request_id=request_id,
            user_id=user_id,
            selected_modality=best_modality,
            execution_path=execution_path,
            sampled_values=sampled_values,
            adjusted_values=adjusted_values,
            eligible_modalities=eligible,
            selection_reason=self._generate_selection_reason(
                best_modality, context, posterior
            ),
            constraints_failed={k.value: v for k, v in constraints_failed.items()},
            selection_confidence=selection_confidence,
            exploration_probability=exploration_prob,
            context_features=context,
            decision_latency_ms=latency_ms,
        )
        
        logger.debug(
            f"Selected modality {best_modality.value} for user {user_id}, "
            f"path={execution_path.value}, confidence={selection_confidence:.2f}"
        )
        
        return decision
    
    def update(
        self,
        modality: LearningModality,
        reward: float,
    ) -> None:
        """
        Update posterior with observed reward.
        
        Args:
            modality: The modality that was used
            reward: Observed reward (0-1)
        """
        self.posterior_state.update_posterior(modality, reward)
        logger.debug(
            f"Updated posterior for {modality.value}, reward={reward:.2f}, "
            f"new mean={self.posterior_state.get_posterior(modality).mean:.3f}"
        )
    
    def apply_decay(self) -> None:
        """Apply decay to all posteriors for non-stationary adaptation."""
        self.posterior_state.decay_all(self.decay_factor)
    
    def _check_constraints(
        self,
        context: ContextFeatures,
    ) -> Tuple[List[LearningModality], Dict[LearningModality, List[str]]]:
        """
        Check which modalities are eligible given the context.
        
        Returns:
            Tuple of (eligible modalities, constraints failed per modality)
        """
        eligible = []
        constraints_failed: Dict[LearningModality, List[str]] = {}
        
        has_rich_dsp = (
            context.dsp_graph_available and context.dsp_construct_count > 10
        )
        
        for modality, constraint in self.constraints.items():
            failed_reasons = []
            
            # Check graph connections (for graph-based modalities)
            if constraint.requires_graph_connections:
                if not context.dsp_graph_available or context.dsp_construct_count <= 10:
                    failed_reasons.append(
                        "requires graph connections (dsp_graph_available and dsp_construct_count > 10)"
                    )
            
            # Check data requirements
            if context.interaction_count < constraint.min_interactions:
                failed_reasons.append(
                    f"interactions {context.interaction_count} < {constraint.min_interactions}"
                )
            
            if context.conversion_count < constraint.min_conversions:
                failed_reasons.append(
                    f"conversions {context.conversion_count} < {constraint.min_conversions}"
                )
            
            if context.profile_completeness < constraint.min_profile_completeness:
                failed_reasons.append(
                    f"profile {context.profile_completeness:.1%} < {constraint.min_profile_completeness:.1%}"
                )
            
            # Check data richness (richer DSP relaxes by one level)
            if constraint.allowed_data_richness:
                effective_allowed = set(constraint.allowed_data_richness)
                if has_rich_dsp:
                    for r in list(effective_allowed):
                        if r == DataRichness.SPARSE:
                            effective_allowed.add(DataRichness.COLD_START)
                        elif r == DataRichness.MODERATE:
                            effective_allowed.add(DataRichness.SPARSE)
                        elif r == DataRichness.RICH:
                            effective_allowed.add(DataRichness.MODERATE)
                if context.data_richness not in effective_allowed:
                    failed_reasons.append(
                        f"richness {context.data_richness.value} not in allowed"
                    )
            
            # Check latency
            if context.latency_budget_ms < constraint.max_latency_ms:
                failed_reasons.append(
                    f"latency {context.latency_budget_ms}ms < required {constraint.max_latency_ms}ms"
                )
            
            # Check exploration
            if constraint.requires_exploration_budget and not context.exploration_allowed:
                failed_reasons.append("exploration not allowed")
            
            if failed_reasons:
                constraints_failed[modality] = failed_reasons
            else:
                eligible.append(modality)
        
        return eligible, constraints_failed
    
    def _calculate_exploration_probability(
        self,
        selected: LearningModality,
        adjusted_values: Dict[str, float],
    ) -> float:
        """
        Calculate the probability that this selection is exploratory.
        
        Higher when selected modality has lower sample count or
        when values are close.
        """
        posterior = self.posterior_state.get_posterior(selected)
        
        # Low sample count = high exploration
        sample_factor = max(0, 1 - posterior.sample_count / 50)
        
        # Close values = high exploration
        values = list(adjusted_values.values())
        if len(values) > 1:
            max_val = max(values)
            second_max = sorted(values)[-2] if len(values) > 1 else 0
            value_factor = 1 - abs(max_val - second_max) if max_val > 0 else 1.0
        else:
            value_factor = 0.0
        
        return min(1.0, (sample_factor + value_factor) / 2)
    
    def _generate_selection_reason(
        self,
        modality: LearningModality,
        context: ContextFeatures,
        posterior: ModalityPosterior,
    ) -> str:
        """Generate a human-readable selection reason."""
        reasons = []

        # Data richness explanation
        if context.data_richness == context.data_richness.COLD_START:
            reasons.append("cold-start user")
        elif context.data_richness == context.data_richness.RICH:
            reasons.append("rich historical data")

        # Buyer uncertainty explanation
        if context.buyer_uncertainty_level > 0.7:
            reasons.append(
                f"high buyer uncertainty ({context.buyer_uncertainty_level:.0%}), "
                f"boosted exploration for information value"
            )
        elif context.buyer_interaction_count > 20:
            reasons.append(
                f"well-characterized buyer ({context.buyer_interaction_count} interactions), "
                f"reduced exploration"
            )

        # Posterior performance
        if posterior.sample_count > 20:
            reasons.append(f"historical success rate {posterior.mean:.1%}")
        else:
            reasons.append(f"exploring (only {posterior.sample_count} observations)")

        # Path rationale
        path = MODALITY_TO_PATH[modality]
        if path == ExecutionPath.FAST_PATH:
            reasons.append("fast path for low latency")
        elif path == ExecutionPath.REASONING_PATH:
            reasons.append("reasoning path for complex analysis")
        else:
            reasons.append("exploration path for learning")

        return "; ".join(reasons)
    
    def get_posterior_summary(self) -> Dict[str, Dict[str, float]]:
        """Get summary of all posteriors for monitoring."""
        summary = {}
        for modality in LearningModality:
            posterior = self.posterior_state.get_posterior(modality)
            summary[modality.value] = {
                "mean": posterior.mean,
                "variance": posterior.variance,
                "confidence": posterior.confidence,
                "sample_count": posterior.sample_count,
                "alpha": posterior.alpha,
                "beta": posterior.beta,
            }
        return summary
