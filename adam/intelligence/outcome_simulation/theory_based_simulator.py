# =============================================================================
# Theory-Based Outcome Simulator
# Location: adam/intelligence/outcome_simulation/theory_based_simulator.py
# =============================================================================

"""
Theory-Based Outcome Simulation for Demo Mode Learning

This module simulates ad outcomes based on psychological research, enabling
the Thompson Sampling learning system to demonstrate improvement without
real ad serving data.

The simulation is grounded in:
1. Archetype → Mechanism effectiveness priors (Enhancement #13)
2. Construct → Mechanism influences (Enhancement #27)
3. Context moderators (time of day, message framing, etc.)
4. Realistic noise to reflect real-world variability

This is NOT random - outcomes are theory-driven predictions of what
WOULD happen based on 25 years of psychological research.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
import random
import math

logger = logging.getLogger(__name__)


# =============================================================================
# OUTCOME TYPES
# =============================================================================

class OutcomeType(str, Enum):
    """Types of ad outcomes to simulate."""
    IMPRESSION = "impression"          # Ad was shown
    ATTENTION = "attention"            # User paid attention
    ENGAGEMENT = "engagement"          # User engaged (clicked, listened)
    CONVERSION = "conversion"          # User took action (purchased, signed up)
    BRAND_LIFT = "brand_lift"          # Attitude/awareness improved
    RECALL = "recall"                  # Message was remembered


class OutcomeLevel(str, Enum):
    """Granularity of outcome simulation."""
    BINARY = "binary"                  # Success/failure
    CONTINUOUS = "continuous"          # 0.0 - 1.0 score
    MULTI_STAGE = "multi_stage"        # Funnel stages


@dataclass
class SimulatedOutcome:
    """Result of outcome simulation."""
    outcome_type: OutcomeType
    success: bool
    probability: float
    score: float  # 0.0 - 1.0
    
    # Decomposition of factors
    base_effectiveness: float
    archetype_fit: float
    mechanism_match: float
    construct_modulation: float
    context_modifier: float
    noise_factor: float
    
    # Explanation
    explanation: str
    key_factors: List[str]
    
    # Learning signal
    reward: float  # For Thompson Sampling update


@dataclass
class SimulationContext:
    """Context for outcome simulation."""
    # Target audience
    archetype_id: str
    
    # Selected strategy
    mechanism_id: str
    
    # Optional fields with defaults
    construct_profile: Dict[str, float] = field(default_factory=dict)
    secondary_mechanisms: List[str] = field(default_factory=list)
    
    # Message properties
    message_framing: str = "neutral"  # gain, loss, neutral
    emotional_tone: str = "positive"  # positive, negative, neutral
    abstraction_level: str = "concrete"  # concrete, abstract
    
    # Delivery context
    time_of_day: str = "afternoon"  # morning, afternoon, evening, night
    day_of_week: str = "weekday"  # weekday, weekend
    platform: str = "radio"  # radio, podcast, streaming
    
    # Product fit
    product_category: str = "general"
    product_involvement: str = "medium"  # low, medium, high


# =============================================================================
# ARCHETYPE-MECHANISM EFFECTIVENESS MATRIX
# =============================================================================

# Expected effectiveness (mean of Beta prior) for each archetype-mechanism pair
# These values come from Enhancement #13 - Cold Start Strategy

ARCHETYPE_MECHANISM_EFFECTIVENESS: Dict[str, Dict[str, float]] = {
    "achievement_driven": {
        "regulatory_focus": 0.75,        # Promotion focus aligns well
        "identity_construction": 0.67,   # Status signaling
        "temporal_construal": 0.64,      # Future achievement
        "evolutionary_motive": 0.57,     # Status motive
        "construal_level": 0.57,
        "automatic_evaluation": 0.54,
        "wanting_liking": 0.54,
        "attention_dynamics": 0.50,
        "mimetic_desire": 0.46,
    },
    "novelty_seeker": {
        "automatic_evaluation": 0.73,    # Fast positive to new
        "wanting_liking": 0.67,          # Anticipation
        "identity_construction": 0.67,   # Unique identity
        "attention_dynamics": 0.64,
        "regulatory_focus": 0.57,
        "construal_level": 0.54,
        "temporal_construal": 0.54,
        "mimetic_desire": 0.54,
        "evolutionary_motive": 0.54,
    },
    "social_connector": {
        "mimetic_desire": 0.81,          # Strong social modeling
        "identity_construction": 0.71,   # Social identity
        "automatic_evaluation": 0.64,
        "evolutionary_motive": 0.64,     # Affiliation
        "wanting_liking": 0.57,
        "attention_dynamics": 0.54,
        "regulatory_focus": 0.54,
        "construal_level": 0.46,
        "temporal_construal": 0.46,
    },
    "security_focused": {
        "regulatory_focus": 0.75,        # Prevention focus
        "temporal_construal": 0.73,      # Long-term
        "construal_level": 0.64,         # Detailed
        "evolutionary_motive": 0.64,     # Self-protection
        "automatic_evaluation": 0.57,
        "identity_construction": 0.54,
        "mimetic_desire": 0.46,
        "attention_dynamics": 0.50,
        "wanting_liking": 0.42,          # Less impulsive
    },
    "harmony_seeker": {
        "automatic_evaluation": 0.71,
        "mimetic_desire": 0.64,
        "wanting_liking": 0.64,
        "regulatory_focus": 0.57,
        "identity_construction": 0.54,
        "construal_level": 0.54,
        "temporal_construal": 0.54,
        "evolutionary_motive": 0.54,
        "attention_dynamics": 0.46,
    },
    "analytical_thinker": {
        "construal_level": 0.73,         # Detailed analysis
        "regulatory_focus": 0.67,
        "temporal_construal": 0.64,
        "attention_dynamics": 0.57,
        "identity_construction": 0.54,
        "automatic_evaluation": 0.46,    # Less automatic
        "wanting_liking": 0.46,
        "mimetic_desire": 0.42,          # Less social
        "evolutionary_motive": 0.50,
    },
    "spontaneous_experiencer": {
        "automatic_evaluation": 0.80,    # Fast, intuitive
        "wanting_liking": 0.73,          # Immediate pleasure
        "attention_dynamics": 0.67,
        "evolutionary_motive": 0.57,
        "identity_construction": 0.57,
        "mimetic_desire": 0.54,
        "regulatory_focus": 0.46,
        "construal_level": 0.42,
        "temporal_construal": 0.33,      # Present-focused
    },
    "traditionalist": {
        "regulatory_focus": 0.73,        # Prevention
        "mimetic_desire": 0.67,          # Follow tradition
        "identity_construction": 0.64,
        "temporal_construal": 0.57,
        "automatic_evaluation": 0.57,
        "evolutionary_motive": 0.57,
        "construal_level": 0.54,
        "wanting_liking": 0.46,
        "attention_dynamics": 0.46,
    },
}

# Default for unknown archetypes
DEFAULT_MECHANISM_EFFECTIVENESS = 0.50


# =============================================================================
# CONSTRUCT MODULATION EFFECTS
# =============================================================================

# How construct scores modulate mechanism effectiveness
# Format: {construct_id: {mechanism_id: modulation_coefficient}}
# Positive = amplifies effectiveness, Negative = dampens

CONSTRUCT_MECHANISM_MODULATION: Dict[str, Dict[str, float]] = {
    "cognitive_nfc": {
        "construal_level": 0.15,
        "automatic_evaluation": -0.10,
        "attention_dynamics": 0.12,
    },
    "selfreg_rf": {
        "regulatory_focus": 0.25,  # Direct mapping - promotion focus amplifies
        "temporal_construal": 0.10,
    },
    "temporal_ddr": {
        "temporal_construal": -0.20,  # High discounting = less future-oriented
        "wanting_liking": 0.15,
        "automatic_evaluation": 0.10,
    },
    "social_conformity": {
        "mimetic_desire": 0.20,
        "identity_construction": 0.08,
    },
    "social_nfu": {
        "identity_construction": 0.18,
        "mimetic_desire": -0.15,
    },
    "emotion_ai": {
        "automatic_evaluation": 0.15,
        "wanting_liking": 0.12,
        "attention_dynamics": 0.10,
    },
    "value_hub": {
        "wanting_liking": 0.15,
        "automatic_evaluation": 0.10,
        "identity_construction": 0.08,
    },
}


# =============================================================================
# CONTEXT MODIFIERS
# =============================================================================

TIME_OF_DAY_MODIFIERS: Dict[str, Dict[str, float]] = {
    "morning": {
        "attention_dynamics": 0.10,      # Higher morning attention
        "regulatory_focus": 0.05,        # Goal-oriented
        "automatic_evaluation": -0.05,   # Less impulsive
    },
    "afternoon": {
        # Neutral baseline
    },
    "evening": {
        "wanting_liking": 0.08,          # Relaxation/reward mode
        "mimetic_desire": 0.05,          # Social context
        "regulatory_focus": -0.05,
    },
    "night": {
        "automatic_evaluation": 0.10,    # Lower cognitive resources
        "attention_dynamics": -0.10,     # Tired
        "construal_level": -0.08,        # Less analytical
    },
}

MESSAGE_FRAMING_MODIFIERS: Dict[str, Dict[str, float]] = {
    "gain": {
        "regulatory_focus": 0.15,        # Promotion-framed
        "wanting_liking": 0.10,
    },
    "loss": {
        "regulatory_focus": 0.15,        # Prevention-framed (different but equally strong)
        "attention_dynamics": 0.08,      # Loss gets attention
    },
    "neutral": {
        # No modifier
    },
}

PLATFORM_MODIFIERS: Dict[str, Dict[str, float]] = {
    "radio": {
        "attention_dynamics": -0.05,     # Background medium
        "automatic_evaluation": 0.08,    # Passive processing
    },
    "podcast": {
        "attention_dynamics": 0.12,      # Active listening
        "identity_construction": 0.08,   # Host relationship
        "mimetic_desire": 0.10,          # Host influence
    },
    "streaming": {
        "automatic_evaluation": 0.05,
        "wanting_liking": 0.05,
    },
}


# =============================================================================
# OUTCOME SIMULATOR
# =============================================================================

class TheoryBasedOutcomeSimulator:
    """
    Simulates ad outcomes based on psychological research.
    
    This enables Thompson Sampling to learn in demo mode by providing
    theory-grounded outcome predictions instead of random noise.
    """
    
    def __init__(
        self,
        noise_level: float = 0.15,
        seed: Optional[int] = None,
    ):
        """
        Initialize the simulator.
        
        Args:
            noise_level: Standard deviation of outcome noise (0.0 - 0.5)
            seed: Random seed for reproducibility
        """
        self.noise_level = min(0.5, max(0.0, noise_level))
        self.rng = random.Random(seed)
        
        # Tracking
        self.total_simulations = 0
        self.outcome_history: List[SimulatedOutcome] = []
    
    def simulate_outcome(
        self,
        context: SimulationContext,
        outcome_type: OutcomeType = OutcomeType.ENGAGEMENT,
    ) -> SimulatedOutcome:
        """
        Simulate an ad outcome based on psychological theory.
        
        Args:
            context: Full context for simulation
            outcome_type: Type of outcome to simulate
            
        Returns:
            SimulatedOutcome with theory-grounded prediction
        """
        self.total_simulations += 1
        
        # Step 1: Base effectiveness from archetype-mechanism match
        base_effectiveness = self._get_base_effectiveness(
            context.archetype_id,
            context.mechanism_id
        )
        
        # Step 2: Archetype fit (how well we identified the archetype)
        archetype_fit = 0.85  # Assume reasonable archetype classification
        
        # Step 3: Mechanism match (primary mechanism effectiveness)
        mechanism_match = base_effectiveness
        
        # Step 4: Construct modulation
        construct_modulation = self._calculate_construct_modulation(
            context.construct_profile,
            context.mechanism_id
        )
        
        # Step 5: Context modifiers
        context_modifier = self._calculate_context_modifier(context)
        
        # Step 6: Combine factors
        raw_probability = (
            base_effectiveness * 0.40 +           # Base is primary
            mechanism_match * 0.25 +              # Mechanism match
            (0.5 + construct_modulation) * 0.20 + # Construct adjustment
            (0.5 + context_modifier) * 0.15       # Context adjustment
        )
        
        # Apply outcome type conversion funnel
        funnel_modifier = self._get_funnel_modifier(outcome_type)
        adjusted_probability = raw_probability * funnel_modifier
        
        # Step 7: Add realistic noise
        noise = self.rng.gauss(0, self.noise_level)
        noise_factor = noise
        
        final_probability = max(0.0, min(1.0, adjusted_probability + noise))
        
        # Step 8: Generate binary outcome
        success = self.rng.random() < final_probability
        
        # Step 9: Calculate reward for learning
        reward = self._calculate_reward(success, final_probability, outcome_type)
        
        # Step 10: Generate explanation
        explanation, key_factors = self._generate_explanation(
            context, base_effectiveness, construct_modulation, 
            context_modifier, final_probability, success
        )
        
        outcome = SimulatedOutcome(
            outcome_type=outcome_type,
            success=success,
            probability=final_probability,
            score=final_probability,
            base_effectiveness=base_effectiveness,
            archetype_fit=archetype_fit,
            mechanism_match=mechanism_match,
            construct_modulation=construct_modulation,
            context_modifier=context_modifier,
            noise_factor=noise_factor,
            explanation=explanation,
            key_factors=key_factors,
            reward=reward,
        )
        
        self.outcome_history.append(outcome)
        return outcome
    
    def simulate_batch(
        self,
        context: SimulationContext,
        n_simulations: int = 100,
        outcome_type: OutcomeType = OutcomeType.ENGAGEMENT,
    ) -> Dict[str, float]:
        """
        Simulate multiple outcomes for statistical analysis.
        
        Returns:
            Dictionary with success_rate, mean_probability, std, etc.
        """
        outcomes = []
        for _ in range(n_simulations):
            outcome = self.simulate_outcome(context, outcome_type)
            outcomes.append(outcome)
        
        successes = sum(1 for o in outcomes if o.success)
        probabilities = [o.probability for o in outcomes]
        
        return {
            "success_rate": successes / n_simulations,
            "mean_probability": sum(probabilities) / n_simulations,
            "std_probability": self._std(probabilities),
            "min_probability": min(probabilities),
            "max_probability": max(probabilities),
            "n_simulations": n_simulations,
        }
    
    def _get_base_effectiveness(
        self,
        archetype_id: str,
        mechanism_id: str,
    ) -> float:
        """Get base effectiveness from archetype-mechanism matrix."""
        archetype_lower = archetype_id.lower().replace("-", "_").replace(" ", "_")
        mechanism_lower = mechanism_id.lower().replace("-", "_").replace(" ", "_")
        
        if archetype_lower in ARCHETYPE_MECHANISM_EFFECTIVENESS:
            arch_effects = ARCHETYPE_MECHANISM_EFFECTIVENESS[archetype_lower]
            return arch_effects.get(mechanism_lower, DEFAULT_MECHANISM_EFFECTIVENESS)
        
        return DEFAULT_MECHANISM_EFFECTIVENESS
    
    def _calculate_construct_modulation(
        self,
        construct_profile: Dict[str, float],
        mechanism_id: str,
    ) -> float:
        """Calculate how construct profile modulates effectiveness."""
        total_modulation = 0.0
        mechanism_lower = mechanism_id.lower().replace("-", "_").replace(" ", "_")
        
        for construct_id, score in construct_profile.items():
            if construct_id in CONSTRUCT_MECHANISM_MODULATION:
                mech_effects = CONSTRUCT_MECHANISM_MODULATION[construct_id]
                if mechanism_lower in mech_effects:
                    # Score is 0-1, center at 0.5 and scale
                    centered_score = (score - 0.5) * 2  # -1 to 1
                    modulation = mech_effects[mechanism_lower] * centered_score
                    total_modulation += modulation
        
        # Cap modulation
        return max(-0.3, min(0.3, total_modulation))
    
    def _calculate_context_modifier(
        self,
        context: SimulationContext,
    ) -> float:
        """Calculate context-based effectiveness modifier."""
        total_modifier = 0.0
        mechanism_lower = context.mechanism_id.lower().replace("-", "_").replace(" ", "_")
        
        # Time of day
        if context.time_of_day in TIME_OF_DAY_MODIFIERS:
            mods = TIME_OF_DAY_MODIFIERS[context.time_of_day]
            total_modifier += mods.get(mechanism_lower, 0.0)
        
        # Message framing
        if context.message_framing in MESSAGE_FRAMING_MODIFIERS:
            mods = MESSAGE_FRAMING_MODIFIERS[context.message_framing]
            total_modifier += mods.get(mechanism_lower, 0.0)
        
        # Platform
        if context.platform in PLATFORM_MODIFIERS:
            mods = PLATFORM_MODIFIERS[context.platform]
            total_modifier += mods.get(mechanism_lower, 0.0)
        
        return max(-0.25, min(0.25, total_modifier))
    
    def _get_funnel_modifier(self, outcome_type: OutcomeType) -> float:
        """Get conversion funnel modifier for outcome type."""
        funnel_rates = {
            OutcomeType.IMPRESSION: 1.0,      # Always shown
            OutcomeType.ATTENTION: 0.70,      # 70% pay attention
            OutcomeType.ENGAGEMENT: 0.30,     # 30% engage
            OutcomeType.CONVERSION: 0.08,     # 8% convert
            OutcomeType.BRAND_LIFT: 0.40,     # 40% attitude shift
            OutcomeType.RECALL: 0.25,         # 25% recall
        }
        return funnel_rates.get(outcome_type, 0.30)
    
    def _calculate_reward(
        self,
        success: bool,
        probability: float,
        outcome_type: OutcomeType,
    ) -> float:
        """Calculate reward signal for Thompson Sampling."""
        # Base reward is binary success
        base_reward = 1.0 if success else 0.0
        
        # Weight by outcome importance
        importance_weights = {
            OutcomeType.IMPRESSION: 0.5,
            OutcomeType.ATTENTION: 0.7,
            OutcomeType.ENGAGEMENT: 1.0,
            OutcomeType.CONVERSION: 1.5,
            OutcomeType.BRAND_LIFT: 1.2,
            OutcomeType.RECALL: 0.9,
        }
        weight = importance_weights.get(outcome_type, 1.0)
        
        # Blend binary outcome with probability for smoother learning
        blended_reward = (base_reward * 0.7 + probability * 0.3) * weight
        
        return min(1.0, blended_reward)
    
    def _generate_explanation(
        self,
        context: SimulationContext,
        base_effectiveness: float,
        construct_modulation: float,
        context_modifier: float,
        final_probability: float,
        success: bool,
    ) -> Tuple[str, List[str]]:
        """Generate explanation of outcome factors."""
        key_factors = []
        
        # Base effectiveness
        if base_effectiveness > 0.65:
            key_factors.append(f"Strong {context.mechanism_id}-{context.archetype_id} fit ({base_effectiveness:.0%})")
        elif base_effectiveness < 0.45:
            key_factors.append(f"Weak {context.mechanism_id}-{context.archetype_id} fit ({base_effectiveness:.0%})")
        
        # Construct modulation
        if abs(construct_modulation) > 0.1:
            direction = "amplified" if construct_modulation > 0 else "dampened"
            key_factors.append(f"Construct profile {direction} effectiveness")
        
        # Context modifier
        if abs(context_modifier) > 0.08:
            direction = "favorable" if context_modifier > 0 else "unfavorable"
            key_factors.append(f"Context was {direction} ({context.time_of_day}, {context.platform})")
        
        # Result
        outcome_str = "succeeded" if success else "did not convert"
        explanation = (
            f"Simulated {context.mechanism_id} on {context.archetype_id} archetype: "
            f"{outcome_str} (p={final_probability:.1%}). "
            f"Base effectiveness {base_effectiveness:.0%}, "
            f"construct modulation {construct_modulation:+.0%}, "
            f"context effect {context_modifier:+.0%}."
        )
        
        return explanation, key_factors
    
    def _std(self, values: List[float]) -> float:
        """Calculate standard deviation."""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return math.sqrt(variance)
    
    def get_stats(self) -> Dict[str, float]:
        """Get simulator statistics."""
        if not self.outcome_history:
            return {"total_simulations": 0}
        
        successes = sum(1 for o in self.outcome_history if o.success)
        return {
            "total_simulations": self.total_simulations,
            "success_rate": successes / len(self.outcome_history),
            "avg_probability": sum(o.probability for o in self.outcome_history) / len(self.outcome_history),
            "avg_reward": sum(o.reward for o in self.outcome_history) / len(self.outcome_history),
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

# Singleton instance
_simulator: Optional[TheoryBasedOutcomeSimulator] = None


def get_outcome_simulator(seed: Optional[int] = None) -> TheoryBasedOutcomeSimulator:
    """Get singleton outcome simulator."""
    global _simulator
    if _simulator is None:
        _simulator = TheoryBasedOutcomeSimulator(seed=seed)
    return _simulator


def simulate_mechanism_outcome(
    archetype_id: str,
    mechanism_id: str,
    construct_profile: Optional[Dict[str, float]] = None,
    outcome_type: OutcomeType = OutcomeType.ENGAGEMENT,
) -> SimulatedOutcome:
    """
    Convenience function to simulate a single outcome.
    
    Args:
        archetype_id: Customer archetype (e.g., 'achievement_driven')
        mechanism_id: Cognitive mechanism (e.g., 'regulatory_focus')
        construct_profile: Optional construct scores
        outcome_type: Type of outcome to simulate
        
    Returns:
        SimulatedOutcome with theory-grounded prediction
    """
    simulator = get_outcome_simulator()
    context = SimulationContext(
        archetype_id=archetype_id,
        mechanism_id=mechanism_id,
        construct_profile=construct_profile or {},
    )
    return simulator.simulate_outcome(context, outcome_type)


def update_thompson_sampler_with_simulation(
    sampler,  # ThompsonSampler instance
    archetype_id: str,
    mechanism_id: str,
    construct_profile: Optional[Dict[str, float]] = None,
) -> Tuple[bool, float]:
    """
    Simulate an outcome and update Thompson Sampler.
    
    This is the key integration point for demo mode learning.
    
    Args:
        sampler: ThompsonSampler instance to update
        archetype_id: Customer archetype
        mechanism_id: Selected mechanism
        construct_profile: Optional construct scores
        
    Returns:
        Tuple of (success, reward)
    """
    outcome = simulate_mechanism_outcome(
        archetype_id=archetype_id,
        mechanism_id=mechanism_id,
        construct_profile=construct_profile,
    )
    
    # Update sampler (needs proper enum conversion)
    # The sampler expects CognitiveMechanism enum and ArchetypeID enum
    # For now, return the outcome for external handling
    return outcome.success, outcome.reward


# =============================================================================
# CLI TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("THEORY-BASED OUTCOME SIMULATOR TEST")
    print("=" * 60)
    
    simulator = TheoryBasedOutcomeSimulator(noise_level=0.15, seed=42)
    
    # Test different archetype-mechanism combinations
    test_cases = [
        ("achievement_driven", "regulatory_focus"),    # High fit
        ("achievement_driven", "mimetic_desire"),      # Low fit
        ("social_connector", "mimetic_desire"),        # High fit
        ("analytical_thinker", "automatic_evaluation"), # Low fit
        ("spontaneous_experiencer", "wanting_liking"), # High fit
    ]
    
    print("\nSingle Outcome Simulations:")
    print("-" * 60)
    
    for archetype, mechanism in test_cases:
        context = SimulationContext(
            archetype_id=archetype,
            mechanism_id=mechanism,
        )
        outcome = simulator.simulate_outcome(context)
        
        status = "✓" if outcome.success else "✗"
        print(f"{status} {archetype} + {mechanism}:")
        print(f"   Probability: {outcome.probability:.1%}")
        print(f"   Base effectiveness: {outcome.base_effectiveness:.1%}")
        print(f"   Reward: {outcome.reward:.2f}")
    
    print("\n" + "=" * 60)
    print("BATCH SIMULATION (100 trials each)")
    print("=" * 60)
    
    for archetype, mechanism in test_cases:
        context = SimulationContext(
            archetype_id=archetype,
            mechanism_id=mechanism,
        )
        stats = simulator.simulate_batch(context, n_simulations=100)
        
        print(f"\n{archetype} + {mechanism}:")
        print(f"   Success rate: {stats['success_rate']:.1%}")
        print(f"   Mean probability: {stats['mean_probability']:.1%}")
        print(f"   Std: {stats['std_probability']:.3f}")
    
    print("\n" + "=" * 60)
    print(f"Total simulations: {simulator.total_simulations}")
