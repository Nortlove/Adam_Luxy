# =============================================================================
# ADAM Mechanism Interaction Learning
# Location: adam/learning/mechanism_interactions.py
# =============================================================================

"""
MECHANISM INTERACTION LEARNING

Learns how cognitive mechanisms interact with each other.

Some mechanism pairs synergize (both high → better outcomes):
- Promotion Focus + High Construal → aspirational messaging
- Wanting + Mimetic Desire → social proof amplification

Some mechanism pairs suppress (one blocks the other):
- Prevention Focus + Risk messaging → fear paralysis
- High Cognitive Load + Complex messaging → abandonment

This implements the learning loop for mechanism interactions:
1. Track which mechanisms are co-activated
2. Measure outcome when both are high/low
3. Compute interaction strength (synergy/suppression)
4. Feed back to mechanism selection

Reference: Enhancement #03 Meta-Learning Orchestration
"""

import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Set
from collections import defaultdict
import math

from pydantic import BaseModel, Field

from adam.behavioral_analytics.models.mechanisms import CognitiveMechanism

logger = logging.getLogger(__name__)


# =============================================================================
# MODELS
# =============================================================================

class InteractionType(str, Enum):
    """Type of interaction between mechanisms."""
    
    SYNERGISTIC = "synergistic"  # Both high → amplified effect
    SUPPRESSIVE = "suppressive"  # Both high → reduced effect
    NEUTRAL = "neutral"  # No significant interaction
    CONDITIONAL = "conditional"  # Depends on context
    UNKNOWN = "unknown"  # Not enough data


class MechanismPair(BaseModel):
    """A pair of mechanisms for interaction tracking."""
    
    mechanism_a: str
    mechanism_b: str
    
    @property
    def pair_id(self) -> str:
        """Canonical ID for the pair (sorted for consistency)."""
        sorted_mechs = sorted([self.mechanism_a, self.mechanism_b])
        return f"{sorted_mechs[0]}::{sorted_mechs[1]}"
    
    def __hash__(self):
        return hash(self.pair_id)
    
    def __eq__(self, other):
        if isinstance(other, MechanismPair):
            return self.pair_id == other.pair_id
        return False


class InteractionObservation(BaseModel):
    """A single observation of mechanism interaction."""
    
    observation_id: str = Field(default_factory=lambda: f"obs_{datetime.now().timestamp()}")
    
    pair: MechanismPair
    
    # Activation levels (0-1)
    activation_a: float = Field(ge=0.0, le=1.0)
    activation_b: float = Field(ge=0.0, le=1.0)
    
    # Outcome
    outcome_value: float = Field(ge=0.0, le=1.0)
    
    # Context
    user_id: str
    decision_id: str
    category: Optional[str] = None
    
    # Timestamp
    observed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LearnedInteraction(BaseModel):
    """Learned interaction between two mechanisms."""
    
    pair: MechanismPair
    
    # Interaction classification
    interaction_type: InteractionType = InteractionType.UNKNOWN
    
    # Interaction strength (-1 to 1)
    # Positive = synergistic (both high → better)
    # Negative = suppressive (both high → worse)
    interaction_strength: float = Field(ge=-1.0, le=1.0, default=0.0)
    
    # Confidence in the interaction
    sample_size: int = Field(default=0, ge=0)
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Outcome statistics by quadrant
    # [both_high, a_high_b_low, a_low_b_high, both_low]
    quadrant_outcomes: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])
    quadrant_counts: List[int] = Field(default_factory=lambda: [0, 0, 0, 0])
    
    # Context-specific effects
    context_effects: Dict[str, float] = Field(default_factory=dict)
    
    # Timing
    first_observed: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    @property
    def both_high_rate(self) -> float:
        """Outcome rate when both mechanisms are high."""
        if self.quadrant_counts[0] == 0:
            return 0.0
        return self.quadrant_outcomes[0] / self.quadrant_counts[0]
    
    @property
    def expected_independent(self) -> float:
        """Expected outcome if mechanisms were independent."""
        # P(success | A high) * P(success | B high)
        a_high_rate = (
            self.quadrant_outcomes[0] + self.quadrant_outcomes[1]
        ) / (
            self.quadrant_counts[0] + self.quadrant_counts[1] + 1
        )
        b_high_rate = (
            self.quadrant_outcomes[0] + self.quadrant_outcomes[2]
        ) / (
            self.quadrant_counts[0] + self.quadrant_counts[2] + 1
        )
        return a_high_rate * b_high_rate
    
    def compute_interaction_strength(self) -> float:
        """Compute interaction strength from quadrant data."""
        if sum(self.quadrant_counts) < 10:
            return 0.0
        
        # Observed joint effect vs expected independent effect
        observed_joint = self.both_high_rate
        expected = self.expected_independent
        
        if expected == 0:
            return 0.0
        
        # Interaction strength = (observed - expected) / expected
        # Clamped to [-1, 1]
        strength = (observed_joint - expected) / max(expected, 0.01)
        return max(-1.0, min(1.0, strength))


class InteractionMatrix(BaseModel):
    """Complete matrix of mechanism interactions."""
    
    interactions: Dict[str, LearnedInteraction] = Field(default_factory=dict)
    
    # Global statistics
    total_observations: int = 0
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Best synergies found
    top_synergies: List[str] = Field(default_factory=list)  # pair_ids
    
    # Worst suppressions found
    top_suppressions: List[str] = Field(default_factory=list)  # pair_ids


# =============================================================================
# MECHANISM INTERACTION LEARNER
# =============================================================================

class MechanismInteractionLearner:
    """
    Learns mechanism interactions from outcome data.
    
    This tracks:
    1. Which mechanisms are co-activated
    2. Outcomes when both are high/low
    3. Interaction strength (synergy vs suppression)
    
    The learned interactions inform:
    1. Mechanism selection (avoid suppressions)
    2. Message optimization (leverage synergies)
    3. Meta-learner routing
    """
    
    def __init__(
        self,
        activation_threshold: float = 0.6,
        min_samples_for_confidence: int = 20,
    ):
        self.activation_threshold = activation_threshold
        self.min_samples = min_samples_for_confidence
        
        # Learned interactions
        self._interactions: Dict[str, LearnedInteraction] = {}
        
        # Observation buffer
        self._observation_buffer: List[InteractionObservation] = []
        
        # Known mechanism list
        self._all_mechanisms = [m.value for m in CognitiveMechanism]
        
        # Initialize all pairs
        self._initialize_pairs()
    
    def _initialize_pairs(self) -> None:
        """Initialize all mechanism pairs."""
        for i, mech_a in enumerate(self._all_mechanisms):
            for mech_b in self._all_mechanisms[i+1:]:
                pair = MechanismPair(mechanism_a=mech_a, mechanism_b=mech_b)
                self._interactions[pair.pair_id] = LearnedInteraction(pair=pair)
    
    def record_observation(
        self,
        mechanism_activations: Dict[str, float],
        outcome_value: float,
        user_id: str,
        decision_id: str,
        category: Optional[str] = None,
    ) -> List[str]:
        """
        Record mechanism co-activation and outcome.
        
        Args:
            mechanism_activations: Dict of mechanism -> activation level
            outcome_value: Outcome (0-1)
            user_id: User ID
            decision_id: Decision ID
            category: Optional category context
        
        Returns:
            List of pair IDs that were updated
        """
        updated_pairs = []
        
        # Get active mechanisms
        mechanisms = list(mechanism_activations.keys())
        
        # Update all pairs
        for i, mech_a in enumerate(mechanisms):
            for mech_b in mechanisms[i+1:]:
                pair = MechanismPair(mechanism_a=mech_a, mechanism_b=mech_b)
                
                act_a = mechanism_activations[mech_a]
                act_b = mechanism_activations[mech_b]
                
                # Record observation
                obs = InteractionObservation(
                    pair=pair,
                    activation_a=act_a,
                    activation_b=act_b,
                    outcome_value=outcome_value,
                    user_id=user_id,
                    decision_id=decision_id,
                    category=category,
                )
                self._observation_buffer.append(obs)
                
                # Update learned interaction
                interaction = self._interactions.get(pair.pair_id)
                if interaction:
                    self._update_interaction(interaction, obs)
                    updated_pairs.append(pair.pair_id)
        
        return updated_pairs
    
    def _update_interaction(
        self,
        interaction: LearnedInteraction,
        obs: InteractionObservation,
    ) -> None:
        """Update a learned interaction with new observation."""
        
        # Determine quadrant
        a_high = obs.activation_a >= self.activation_threshold
        b_high = obs.activation_b >= self.activation_threshold
        
        if a_high and b_high:
            quadrant = 0
        elif a_high and not b_high:
            quadrant = 1
        elif not a_high and b_high:
            quadrant = 2
        else:
            quadrant = 3
        
        # Update quadrant statistics
        interaction.quadrant_counts[quadrant] += 1
        interaction.quadrant_outcomes[quadrant] += obs.outcome_value
        
        # Update sample size
        interaction.sample_size = sum(interaction.quadrant_counts)
        
        # Recompute interaction strength
        interaction.interaction_strength = interaction.compute_interaction_strength()
        
        # Classify interaction type
        if interaction.sample_size >= self.min_samples:
            strength = interaction.interaction_strength
            if strength > 0.15:
                interaction.interaction_type = InteractionType.SYNERGISTIC
            elif strength < -0.15:
                interaction.interaction_type = InteractionType.SUPPRESSIVE
            else:
                interaction.interaction_type = InteractionType.NEUTRAL
            
            # Compute confidence
            interaction.confidence = min(0.95, 0.3 + interaction.sample_size / 100)
        
        # Update context effects
        if obs.category:
            if obs.category not in interaction.context_effects:
                interaction.context_effects[obs.category] = 0.0
            # Exponential moving average
            current = interaction.context_effects[obs.category]
            interaction.context_effects[obs.category] = (
                current * 0.9 + (obs.outcome_value - 0.5) * 0.1
            )
        
        interaction.last_updated = datetime.now(timezone.utc)
    
    def get_interaction(
        self,
        mechanism_a: str,
        mechanism_b: str,
    ) -> Optional[LearnedInteraction]:
        """Get the learned interaction between two mechanisms."""
        pair = MechanismPair(mechanism_a=mechanism_a, mechanism_b=mechanism_b)
        return self._interactions.get(pair.pair_id)
    
    def get_synergistic_pairs(
        self,
        mechanism: str,
        min_strength: float = 0.1,
        min_confidence: float = 0.5,
    ) -> List[Tuple[str, float]]:
        """
        Get mechanisms that synergize with the given mechanism.
        
        Returns:
            List of (mechanism_id, interaction_strength) tuples
        """
        synergies = []
        
        for pair_id, interaction in self._interactions.items():
            if interaction.interaction_type != InteractionType.SYNERGISTIC:
                continue
            
            if interaction.confidence < min_confidence:
                continue
            
            if interaction.interaction_strength < min_strength:
                continue
            
            # Check if this pair includes the target mechanism
            if mechanism == interaction.pair.mechanism_a:
                synergies.append((
                    interaction.pair.mechanism_b,
                    interaction.interaction_strength,
                ))
            elif mechanism == interaction.pair.mechanism_b:
                synergies.append((
                    interaction.pair.mechanism_a,
                    interaction.interaction_strength,
                ))
        
        # Sort by strength
        synergies.sort(key=lambda x: x[1], reverse=True)
        return synergies
    
    def get_suppressive_pairs(
        self,
        mechanism: str,
        min_strength: float = 0.1,
        min_confidence: float = 0.5,
    ) -> List[Tuple[str, float]]:
        """
        Get mechanisms that suppress the given mechanism.
        
        Returns:
            List of (mechanism_id, suppression_strength) tuples
        """
        suppressions = []
        
        for pair_id, interaction in self._interactions.items():
            if interaction.interaction_type != InteractionType.SUPPRESSIVE:
                continue
            
            if interaction.confidence < min_confidence:
                continue
            
            if interaction.interaction_strength > -min_strength:
                continue
            
            # Check if this pair includes the target mechanism
            if mechanism == interaction.pair.mechanism_a:
                suppressions.append((
                    interaction.pair.mechanism_b,
                    abs(interaction.interaction_strength),
                ))
            elif mechanism == interaction.pair.mechanism_b:
                suppressions.append((
                    interaction.pair.mechanism_a,
                    abs(interaction.interaction_strength),
                ))
        
        # Sort by strength
        suppressions.sort(key=lambda x: x[1], reverse=True)
        return suppressions
    
    def get_interaction_matrix(self) -> InteractionMatrix:
        """Get the complete interaction matrix."""
        
        # Find top synergies
        synergies = [
            (pair_id, inter.interaction_strength)
            for pair_id, inter in self._interactions.items()
            if inter.interaction_type == InteractionType.SYNERGISTIC
            and inter.confidence >= 0.5
        ]
        synergies.sort(key=lambda x: x[1], reverse=True)
        top_synergies = [x[0] for x in synergies[:5]]
        
        # Find top suppressions
        suppressions = [
            (pair_id, inter.interaction_strength)
            for pair_id, inter in self._interactions.items()
            if inter.interaction_type == InteractionType.SUPPRESSIVE
            and inter.confidence >= 0.5
        ]
        suppressions.sort(key=lambda x: x[1])
        top_suppressions = [x[0] for x in suppressions[:5]]
        
        return InteractionMatrix(
            interactions=self._interactions,
            total_observations=len(self._observation_buffer),
            top_synergies=top_synergies,
            top_suppressions=top_suppressions,
        )
    
    def should_avoid_combination(
        self,
        mechanism_a: str,
        mechanism_b: str,
        threshold: float = -0.2,
    ) -> bool:
        """Check if a mechanism combination should be avoided."""
        interaction = self.get_interaction(mechanism_a, mechanism_b)
        if not interaction:
            return False
        
        return (
            interaction.interaction_type == InteractionType.SUPPRESSIVE and
            interaction.interaction_strength < threshold and
            interaction.confidence >= 0.5
        )
    
    def recommend_companion_mechanisms(
        self,
        primary_mechanism: str,
        available_mechanisms: List[str],
        num_recommendations: int = 2,
    ) -> List[str]:
        """
        Recommend companion mechanisms that synergize with the primary.
        
        Args:
            primary_mechanism: The primary mechanism being used
            available_mechanisms: Mechanisms available for selection
            num_recommendations: Number of companions to recommend
        
        Returns:
            List of recommended companion mechanism IDs
        """
        synergies = self.get_synergistic_pairs(primary_mechanism)
        
        # Filter to available mechanisms
        recommendations = []
        for mech, strength in synergies:
            if mech in available_mechanisms:
                recommendations.append(mech)
                if len(recommendations) >= num_recommendations:
                    break
        
        return recommendations
    
    def get_combined_effectiveness_estimate(
        self,
        mechanisms: List[str],
        base_effectiveness: Dict[str, float],
    ) -> float:
        """
        Estimate combined effectiveness considering interactions.
        
        Args:
            mechanisms: List of mechanisms being combined
            base_effectiveness: Individual effectiveness of each mechanism
        
        Returns:
            Estimated combined effectiveness (0-1)
        """
        if len(mechanisms) == 0:
            return 0.0
        
        if len(mechanisms) == 1:
            return base_effectiveness.get(mechanisms[0], 0.5)
        
        # Start with average individual effectiveness
        avg_eff = sum(
            base_effectiveness.get(m, 0.5) for m in mechanisms
        ) / len(mechanisms)
        
        # Apply interaction effects
        total_interaction = 0.0
        interaction_count = 0
        
        for i, mech_a in enumerate(mechanisms):
            for mech_b in mechanisms[i+1:]:
                interaction = self.get_interaction(mech_a, mech_b)
                if interaction and interaction.confidence >= 0.5:
                    total_interaction += interaction.interaction_strength
                    interaction_count += 1
        
        # Adjust effectiveness based on interactions
        if interaction_count > 0:
            avg_interaction = total_interaction / interaction_count
            adjusted_eff = avg_eff * (1 + avg_interaction * 0.3)
        else:
            adjusted_eff = avg_eff
        
        return max(0.0, min(1.0, adjusted_eff))
