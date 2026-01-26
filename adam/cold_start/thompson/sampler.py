# =============================================================================
# ADAM Enhancement #13: Thompson Sampling for Cold Start
# Location: adam/cold_start/thompson/sampler.py
# =============================================================================

"""
Thompson Sampling for mechanism selection in cold start.

Uses Beta posteriors to balance exploration/exploitation:
- Sample θ ~ Beta(α, β) for each mechanism
- Select mechanism with highest sample
- Update posterior with outcome
- Includes exploration bonus for high-uncertainty arms
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging
import numpy as np

from adam.cold_start.models.enums import CognitiveMechanism, ArchetypeID
from adam.cold_start.models.priors import BetaDistribution, MechanismPrior

logger = logging.getLogger(__name__)


class ThompsonSampler:
    """
    Thompson Sampling for mechanism selection.
    
    Maintains Beta posteriors for each (user_context, mechanism) pair.
    Supports:
    - Per-archetype mechanism priors
    - Exploration bonus for uncertain mechanisms
    - Outcome-based posterior updates
    """
    
    def __init__(
        self,
        exploration_bonus: float = 0.1,
        min_samples_for_exploitation: int = 10,
        decay_factor: float = 0.95,
    ):
        self.exploration_bonus = exploration_bonus
        self.min_samples = min_samples_for_exploitation
        self.decay_factor = decay_factor
        
        # Posteriors by archetype and mechanism
        self.posteriors: Dict[ArchetypeID, Dict[CognitiveMechanism, BetaDistribution]] = {}
        
        # Population-level posteriors (fallback)
        self.population_posteriors: Dict[CognitiveMechanism, BetaDistribution] = {
            mech: BetaDistribution(alpha=2.0, beta=2.0)
            for mech in CognitiveMechanism
        }
        
        # Tracking
        self.total_samples = 0
        self.total_updates = 0
    
    def initialize_from_priors(
        self,
        archetype: ArchetypeID,
        mechanism_priors: Dict[CognitiveMechanism, BetaDistribution]
    ) -> None:
        """Initialize posteriors from archetype priors."""
        self.posteriors[archetype] = {}
        for mech, prior in mechanism_priors.items():
            self.posteriors[archetype][mech] = BetaDistribution(
                alpha=prior.alpha,
                beta=prior.beta
            )
    
    def sample_mechanism(
        self,
        archetype: Optional[ArchetypeID] = None,
        available_mechanisms: Optional[List[CognitiveMechanism]] = None,
        force_exploration: bool = False,
    ) -> Tuple[CognitiveMechanism, float, str]:
        """
        Sample best mechanism using Thompson Sampling.
        
        Args:
            archetype: User's archetype (if known)
            available_mechanisms: Restrict to these mechanisms
            force_exploration: If True, sample from most uncertain
            
        Returns:
            (selected_mechanism, sample_value, selection_reason)
        """
        self.total_samples += 1
        
        # Get relevant posteriors
        if archetype and archetype in self.posteriors:
            posteriors = self.posteriors[archetype]
        else:
            posteriors = self.population_posteriors
        
        # Filter to available mechanisms
        if available_mechanisms:
            posteriors = {
                m: p for m, p in posteriors.items()
                if m in available_mechanisms
            }
        
        if not posteriors:
            posteriors = self.population_posteriors
        
        # Force exploration: select most uncertain
        if force_exploration:
            most_uncertain = max(
                posteriors.items(),
                key=lambda x: x[1].uncertainty
            )
            return (
                most_uncertain[0],
                most_uncertain[1].sample(),
                "forced_exploration"
            )
        
        # Thompson Sampling: sample from each posterior
        samples: Dict[CognitiveMechanism, float] = {}
        for mech, posterior in posteriors.items():
            sample = posterior.sample()
            
            # Add exploration bonus for uncertain mechanisms
            if posterior.samples < self.min_samples:
                sample += self.exploration_bonus * posterior.uncertainty
            
            samples[mech] = sample
        
        # Select highest sample
        best_mech = max(samples, key=samples.get)
        best_sample = samples[best_mech]
        
        # Determine reason
        posterior = posteriors[best_mech]
        if posterior.samples < self.min_samples:
            reason = "exploration"
        elif best_sample > posterior.mean + 0.1:
            reason = "lucky_sample"
        else:
            reason = "exploitation"
        
        return best_mech, best_sample, reason
    
    def sample_top_k(
        self,
        k: int = 3,
        archetype: Optional[ArchetypeID] = None,
        available_mechanisms: Optional[List[CognitiveMechanism]] = None,
    ) -> List[Tuple[CognitiveMechanism, float]]:
        """
        Sample top K mechanisms.
        
        Useful for multi-mechanism strategies.
        """
        # Get relevant posteriors
        if archetype and archetype in self.posteriors:
            posteriors = self.posteriors[archetype]
        else:
            posteriors = self.population_posteriors
        
        if available_mechanisms:
            posteriors = {
                m: p for m, p in posteriors.items()
                if m in available_mechanisms
            }
        
        # Sample all
        samples = []
        for mech, posterior in posteriors.items():
            sample = posterior.sample()
            if posterior.samples < self.min_samples:
                sample += self.exploration_bonus * posterior.uncertainty
            samples.append((mech, sample))
        
        # Sort and return top K
        samples.sort(key=lambda x: x[1], reverse=True)
        return samples[:k]
    
    def update_posterior(
        self,
        mechanism: CognitiveMechanism,
        success: bool,
        archetype: Optional[ArchetypeID] = None,
    ) -> BetaDistribution:
        """
        Update posterior with outcome.
        
        Args:
            mechanism: Mechanism that was used
            success: Whether outcome was positive
            archetype: User's archetype
            
        Returns:
            Updated posterior
        """
        self.total_updates += 1
        
        # Update archetype-specific posterior
        if archetype:
            if archetype not in self.posteriors:
                self.posteriors[archetype] = {}
            
            if mechanism not in self.posteriors[archetype]:
                # Initialize from population
                pop = self.population_posteriors.get(
                    mechanism, 
                    BetaDistribution(alpha=1.0, beta=1.0)
                )
                self.posteriors[archetype][mechanism] = BetaDistribution(
                    alpha=pop.alpha,
                    beta=pop.beta
                )
            
            self.posteriors[archetype][mechanism] = \
                self.posteriors[archetype][mechanism].update(success)
            
            return self.posteriors[archetype][mechanism]
        
        # Update population posterior
        if mechanism not in self.population_posteriors:
            self.population_posteriors[mechanism] = BetaDistribution(
                alpha=1.0, beta=1.0
            )
        
        self.population_posteriors[mechanism] = \
            self.population_posteriors[mechanism].update(success)
        
        return self.population_posteriors[mechanism]
    
    def get_posterior(
        self,
        mechanism: CognitiveMechanism,
        archetype: Optional[ArchetypeID] = None,
    ) -> BetaDistribution:
        """Get posterior for a mechanism."""
        if archetype and archetype in self.posteriors:
            if mechanism in self.posteriors[archetype]:
                return self.posteriors[archetype][mechanism]
        
        return self.population_posteriors.get(
            mechanism,
            BetaDistribution(alpha=1.0, beta=1.0)
        )
    
    def get_expected_effectiveness(
        self,
        mechanism: CognitiveMechanism,
        archetype: Optional[ArchetypeID] = None,
    ) -> float:
        """Get expected effectiveness (mean of posterior)."""
        posterior = self.get_posterior(mechanism, archetype)
        return posterior.mean
    
    def get_mechanism_ranking(
        self,
        archetype: Optional[ArchetypeID] = None,
    ) -> List[Tuple[CognitiveMechanism, float, float]]:
        """
        Get mechanism ranking by expected effectiveness.
        
        Returns:
            List of (mechanism, mean, uncertainty) tuples
        """
        if archetype and archetype in self.posteriors:
            posteriors = self.posteriors[archetype]
        else:
            posteriors = self.population_posteriors
        
        ranking = [
            (mech, post.mean, post.uncertainty)
            for mech, post in posteriors.items()
        ]
        ranking.sort(key=lambda x: x[1], reverse=True)
        return ranking
    
    def apply_decay(self) -> None:
        """Apply decay to all posteriors (for temporal adaptation)."""
        for archetype in self.posteriors:
            for mech in self.posteriors[archetype]:
                post = self.posteriors[archetype][mech]
                self.posteriors[archetype][mech] = BetaDistribution(
                    alpha=max(1.0, post.alpha * self.decay_factor),
                    beta=max(1.0, post.beta * self.decay_factor)
                )
        
        for mech in self.population_posteriors:
            post = self.population_posteriors[mech]
            self.population_posteriors[mech] = BetaDistribution(
                alpha=max(1.0, post.alpha * self.decay_factor),
                beta=max(1.0, post.beta * self.decay_factor)
            )


# Singleton instance
_sampler: Optional[ThompsonSampler] = None


def get_thompson_sampler() -> ThompsonSampler:
    """Get singleton Thompson Sampler."""
    global _sampler
    if _sampler is None:
        _sampler = ThompsonSampler()
    return _sampler
