# =============================================================================
# ADAM v3: Mechanism Interaction Engine
# Location: src/v3/interactions/mechanism.py
# =============================================================================

"""
MECHANISM INTERACTION ENGINE

Models how psychological mechanisms interact and combine.

Key capabilities:
- Mechanism synergy detection
- Conflict identification
- Optimal combination selection
- Interaction effect estimation
- Context-dependent modulation
"""

from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
import logging
import uuid
import numpy as np
from collections import defaultdict

logger = logging.getLogger(__name__)


class InteractionType(str, Enum):
    """Types of mechanism interactions."""
    SYNERGY = "synergy"             # Mechanisms amplify each other
    CONFLICT = "conflict"           # Mechanisms interfere
    INDEPENDENT = "independent"     # No interaction
    SEQUENTIAL = "sequential"       # One enables the other
    CONDITIONAL = "conditional"     # Interaction depends on context


class MechanismCategory(str, Enum):
    """Categories of psychological mechanisms."""
    REGULATORY = "regulatory"       # Regulatory focus
    COGNITIVE = "cognitive"         # Cognitive load, need for cognition
    EMOTIONAL = "emotional"         # Emotional valence
    SOCIAL = "social"               # Social proof, belonging
    TEMPORAL = "temporal"           # Scarcity, urgency
    SELF = "self"                   # Self-efficacy, identity


class Mechanism(BaseModel):
    """A psychological mechanism."""
    
    mechanism_id: str
    name: str
    category: MechanismCategory
    
    # Base effectiveness
    base_effectiveness: float = Field(ge=0.0, le=1.0, default=0.5)
    
    # Usage statistics
    activations: int = 0
    successes: int = 0
    
    @property
    def success_rate(self) -> float:
        """Historical success rate."""
        if self.activations == 0:
            return 0.5
        return self.successes / self.activations


class MechanismInteraction(BaseModel):
    """An interaction between two mechanisms."""
    
    interaction_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    mechanism_a: str
    mechanism_b: str
    
    interaction_type: InteractionType = InteractionType.INDEPENDENT
    
    # Effect modifiers
    synergy_multiplier: float = Field(ge=0.0, le=3.0, default=1.0)
    conflict_penalty: float = Field(ge=0.0, le=1.0, default=0.0)
    
    # Confidence
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    observations: int = 0
    
    # Context conditions
    context_conditions: Dict[str, Any] = Field(default_factory=dict)


class MechanismCombination(BaseModel):
    """A combination of mechanisms for a decision."""
    
    combination_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    mechanisms: List[str] = Field(default_factory=list)
    
    # Predicted effectiveness
    individual_effects: Dict[str, float] = Field(default_factory=dict)
    interaction_effects: Dict[str, float] = Field(default_factory=dict)
    combined_effectiveness: float = 0.0
    
    # Warnings
    conflicts: List[str] = Field(default_factory=list)
    synergies: List[str] = Field(default_factory=list)
    
    # Context
    context_match_score: float = 1.0


class MechanismInteractionEngine:
    """
    Models interactions between psychological mechanisms.
    
    Learns:
    - Which mechanisms synergize
    - Which mechanisms conflict
    - Context-dependent interaction effects
    - Optimal combinations for goals
    """
    
    # Known mechanism definitions
    KNOWN_MECHANISMS = {
        "regulatory_focus_promotion": Mechanism(
            mechanism_id="regulatory_focus_promotion",
            name="Promotion Focus",
            category=MechanismCategory.REGULATORY,
            base_effectiveness=0.55,
        ),
        "regulatory_focus_prevention": Mechanism(
            mechanism_id="regulatory_focus_prevention",
            name="Prevention Focus",
            category=MechanismCategory.REGULATORY,
            base_effectiveness=0.52,
        ),
        "construal_high": Mechanism(
            mechanism_id="construal_high",
            name="High Construal (Abstract)",
            category=MechanismCategory.COGNITIVE,
            base_effectiveness=0.50,
        ),
        "construal_low": Mechanism(
            mechanism_id="construal_low",
            name="Low Construal (Concrete)",
            category=MechanismCategory.COGNITIVE,
            base_effectiveness=0.53,
        ),
        "social_proof": Mechanism(
            mechanism_id="social_proof",
            name="Social Proof",
            category=MechanismCategory.SOCIAL,
            base_effectiveness=0.58,
        ),
        "scarcity": Mechanism(
            mechanism_id="scarcity",
            name="Scarcity",
            category=MechanismCategory.TEMPORAL,
            base_effectiveness=0.56,
        ),
        "reciprocity": Mechanism(
            mechanism_id="reciprocity",
            name="Reciprocity",
            category=MechanismCategory.SOCIAL,
            base_effectiveness=0.54,
        ),
        "self_efficacy": Mechanism(
            mechanism_id="self_efficacy",
            name="Self-Efficacy",
            category=MechanismCategory.SELF,
            base_effectiveness=0.51,
        ),
        "loss_aversion": Mechanism(
            mechanism_id="loss_aversion",
            name="Loss Aversion",
            category=MechanismCategory.EMOTIONAL,
            base_effectiveness=0.60,
        ),
        "cognitive_ease": Mechanism(
            mechanism_id="cognitive_ease",
            name="Cognitive Ease",
            category=MechanismCategory.COGNITIVE,
            base_effectiveness=0.49,
        ),
    }
    
    # Known interactions (pre-defined based on research)
    KNOWN_INTERACTIONS = [
        # Synergies
        ("regulatory_focus_promotion", "construal_high", InteractionType.SYNERGY, 1.15),
        ("regulatory_focus_prevention", "construal_low", InteractionType.SYNERGY, 1.12),
        ("scarcity", "loss_aversion", InteractionType.SYNERGY, 1.20),
        ("social_proof", "cognitive_ease", InteractionType.SYNERGY, 1.10),
        
        # Conflicts
        ("regulatory_focus_promotion", "regulatory_focus_prevention", InteractionType.CONFLICT, 0.7),
        ("construal_high", "construal_low", InteractionType.CONFLICT, 0.6),
        ("scarcity", "cognitive_ease", InteractionType.CONFLICT, 0.85),
    ]
    
    def __init__(self):
        # Mechanism registry
        self._mechanisms = dict(self.KNOWN_MECHANISMS)
        
        # Interaction matrix
        self._interactions: Dict[Tuple[str, str], MechanismInteraction] = {}
        self._init_known_interactions()
        
        # Learned interactions
        self._learned_interactions: Dict[Tuple[str, str], List[float]] = defaultdict(list)
        
        # Statistics
        self._combinations_evaluated = 0
        self._outcomes_recorded = 0
    
    def _init_known_interactions(self) -> None:
        """Initialize known interactions."""
        for mech_a, mech_b, int_type, multiplier in self.KNOWN_INTERACTIONS:
            key = tuple(sorted([mech_a, mech_b]))
            
            interaction = MechanismInteraction(
                mechanism_a=mech_a,
                mechanism_b=mech_b,
                interaction_type=int_type,
                synergy_multiplier=multiplier if int_type == InteractionType.SYNERGY else 1.0,
                conflict_penalty=1.0 - multiplier if int_type == InteractionType.CONFLICT else 0.0,
                confidence=0.8,  # High confidence for research-backed interactions
                observations=100,  # Treat as if observed many times
            )
            self._interactions[key] = interaction
    
    async def evaluate_combination(
        self,
        mechanisms: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> MechanismCombination:
        """
        Evaluate a combination of mechanisms.
        
        Args:
            mechanisms: List of mechanism IDs
            context: Context for evaluation
            
        Returns:
            Evaluation result with predicted effectiveness
        """
        self._combinations_evaluated += 1
        
        combination = MechanismCombination(
            mechanisms=mechanisms,
        )
        
        # Calculate individual effects
        for mech_id in mechanisms:
            if mech_id in self._mechanisms:
                mech = self._mechanisms[mech_id]
                effectiveness = mech.base_effectiveness
                
                # Adjust for historical success
                if mech.activations >= 10:
                    effectiveness = 0.7 * effectiveness + 0.3 * mech.success_rate
                
                combination.individual_effects[mech_id] = effectiveness
        
        # Calculate interaction effects
        for i, mech_a in enumerate(mechanisms):
            for mech_b in mechanisms[i+1:]:
                key = tuple(sorted([mech_a, mech_b]))
                
                if key in self._interactions:
                    interaction = self._interactions[key]
                    
                    if interaction.interaction_type == InteractionType.SYNERGY:
                        effect_key = f"{mech_a}+{mech_b}"
                        combination.interaction_effects[effect_key] = interaction.synergy_multiplier - 1.0
                        combination.synergies.append(
                            f"{self._mechanisms[mech_a].name} + {self._mechanisms[mech_b].name}"
                        )
                    
                    elif interaction.interaction_type == InteractionType.CONFLICT:
                        effect_key = f"{mech_a}x{mech_b}"
                        combination.interaction_effects[effect_key] = -interaction.conflict_penalty
                        combination.conflicts.append(
                            f"{self._mechanisms[mech_a].name} conflicts with {self._mechanisms[mech_b].name}"
                        )
        
        # Calculate combined effectiveness
        base_effect = np.mean(list(combination.individual_effects.values())) if combination.individual_effects else 0.5
        interaction_modifier = sum(combination.interaction_effects.values())
        
        combination.combined_effectiveness = max(0.0, min(1.0, base_effect + interaction_modifier * 0.5))
        
        return combination
    
    async def find_optimal_combination(
        self,
        available_mechanisms: List[str],
        max_mechanisms: int = 3,
        context: Optional[Dict[str, Any]] = None
    ) -> MechanismCombination:
        """
        Find optimal mechanism combination.
        
        Args:
            available_mechanisms: Mechanisms to choose from
            max_mechanisms: Maximum number to combine
            context: Context for evaluation
            
        Returns:
            Optimal combination
        """
        from itertools import combinations
        
        best_combination = None
        best_effectiveness = 0.0
        
        # Try all combinations up to max size
        for size in range(1, min(max_mechanisms + 1, len(available_mechanisms) + 1)):
            for combo in combinations(available_mechanisms, size):
                result = await self.evaluate_combination(list(combo), context)
                
                # Prefer combinations without conflicts
                conflict_penalty = len(result.conflicts) * 0.1
                adjusted_effectiveness = result.combined_effectiveness - conflict_penalty
                
                if adjusted_effectiveness > best_effectiveness:
                    best_effectiveness = adjusted_effectiveness
                    best_combination = result
        
        return best_combination or MechanismCombination(mechanisms=[])
    
    async def record_outcome(
        self,
        mechanisms: List[str],
        success: bool,
        effect_size: float = 0.0,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record outcome for mechanism combination.
        
        Args:
            mechanisms: Mechanisms used
            success: Whether outcome was successful
            effect_size: Measured effect size
            context: Context of the outcome
        """
        self._outcomes_recorded += 1
        
        # Update individual mechanism stats
        for mech_id in mechanisms:
            if mech_id in self._mechanisms:
                mech = self._mechanisms[mech_id]
                mech.activations += 1
                if success:
                    mech.successes += 1
        
        # Update pairwise interactions
        for i, mech_a in enumerate(mechanisms):
            for mech_b in mechanisms[i+1:]:
                key = tuple(sorted([mech_a, mech_b]))
                
                # Record observed effect
                observed_effect = effect_size if success else -effect_size
                self._learned_interactions[key].append(observed_effect)
                
                # Update interaction model if enough observations
                if len(self._learned_interactions[key]) >= 20:
                    await self._update_interaction(key)
    
    async def _update_interaction(self, key: Tuple[str, str]) -> None:
        """Update interaction model based on observations."""
        observations = self._learned_interactions[key]
        
        mean_effect = np.mean(observations)
        
        if key in self._interactions:
            interaction = self._interactions[key]
            interaction.observations += len(observations)
            
            # Update multiplier based on observations
            if mean_effect > 0.05:
                interaction.interaction_type = InteractionType.SYNERGY
                interaction.synergy_multiplier = 1.0 + mean_effect
                interaction.conflict_penalty = 0.0
            elif mean_effect < -0.05:
                interaction.interaction_type = InteractionType.CONFLICT
                interaction.synergy_multiplier = 1.0
                interaction.conflict_penalty = -mean_effect
            else:
                interaction.interaction_type = InteractionType.INDEPENDENT
        else:
            # Create new interaction
            mech_a, mech_b = key
            int_type = InteractionType.INDEPENDENT
            
            if mean_effect > 0.05:
                int_type = InteractionType.SYNERGY
            elif mean_effect < -0.05:
                int_type = InteractionType.CONFLICT
            
            self._interactions[key] = MechanismInteraction(
                mechanism_a=mech_a,
                mechanism_b=mech_b,
                interaction_type=int_type,
                synergy_multiplier=1.0 + max(0, mean_effect),
                conflict_penalty=-min(0, mean_effect),
                confidence=min(0.9, 0.5 + len(observations) / 100),
                observations=len(observations),
            )
        
        # Clear observations
        self._learned_interactions[key] = []
    
    def get_interaction(
        self,
        mechanism_a: str,
        mechanism_b: str
    ) -> Optional[MechanismInteraction]:
        """Get interaction between two mechanisms."""
        key = tuple(sorted([mechanism_a, mechanism_b]))
        return self._interactions.get(key)
    
    def get_all_synergies(self) -> List[MechanismInteraction]:
        """Get all known synergistic interactions."""
        return [
            i for i in self._interactions.values()
            if i.interaction_type == InteractionType.SYNERGY
        ]
    
    def get_all_conflicts(self) -> List[MechanismInteraction]:
        """Get all known conflicting interactions."""
        return [
            i for i in self._interactions.values()
            if i.interaction_type == InteractionType.CONFLICT
        ]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "mechanisms_registered": len(self._mechanisms),
            "interactions_known": len(self._interactions),
            "synergies": sum(1 for i in self._interactions.values() if i.interaction_type == InteractionType.SYNERGY),
            "conflicts": sum(1 for i in self._interactions.values() if i.interaction_type == InteractionType.CONFLICT),
            "combinations_evaluated": self._combinations_evaluated,
            "outcomes_recorded": self._outcomes_recorded,
        }


# Singleton instance
_engine: Optional[MechanismInteractionEngine] = None


def get_mechanism_interaction_engine() -> MechanismInteractionEngine:
    """Get singleton Mechanism Interaction Engine."""
    global _engine
    if _engine is None:
        _engine = MechanismInteractionEngine()
    return _engine
