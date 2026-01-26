# =============================================================================
# ADAM Enhancement #13: Population Priors
# Location: adam/cold_start/priors/population.py
# =============================================================================

"""
Population-level priors derived from Amazon corpus and research literature.

These are the most general priors, used when no other information is available.
They form the base layer in the hierarchical prior system.
"""

from __future__ import annotations
from typing import Dict, Optional
from pydantic import BaseModel
import numpy as np

from adam.cold_start.models.enums import (
    PersonalityTrait, CognitiveMechanism, PriorSource
)
from adam.cold_start.models.priors import (
    BetaDistribution, GaussianDistribution, TraitPrior, MechanismPrior,
    PsychologicalPrior
)


class PopulationPriorConfig(BaseModel):
    """Configuration for population prior computation."""
    
    # Source weights
    amazon_corpus_weight: float = 0.6
    research_literature_weight: float = 0.3
    category_norms_weight: float = 0.1
    
    # Default uncertainty
    default_trait_variance: float = 0.04  # Moderately uncertain
    default_mechanism_pseudocounts: float = 5.0  # Weak prior


# =============================================================================
# POPULATION TRAIT PRIORS
# =============================================================================

# Research-based Big Five population means and variances
# Source: Costa & McCrae meta-analyses, Amazon corpus validation
POPULATION_TRAIT_PRIORS: Dict[PersonalityTrait, GaussianDistribution] = {
    PersonalityTrait.OPENNESS: GaussianDistribution(
        mean=0.55,  # Slightly above neutral (Amazon skews creative)
        variance=0.04
    ),
    PersonalityTrait.CONSCIENTIOUSNESS: GaussianDistribution(
        mean=0.52,
        variance=0.04
    ),
    PersonalityTrait.EXTRAVERSION: GaussianDistribution(
        mean=0.48,  # Slightly below (reviewers skew introverted)
        variance=0.05
    ),
    PersonalityTrait.AGREEABLENESS: GaussianDistribution(
        mean=0.56,  # Reviewers tend agreeable
        variance=0.04
    ),
    PersonalityTrait.NEUROTICISM: GaussianDistribution(
        mean=0.45,  # Below neutral
        variance=0.05
    ),
}


# =============================================================================
# POPULATION MECHANISM PRIORS
# =============================================================================

# Base rates for mechanism effectiveness from research + Amazon validation
# Alpha/Beta tuned to reflect population-level conversion rates
POPULATION_MECHANISM_PRIORS: Dict[CognitiveMechanism, BetaDistribution] = {
    CognitiveMechanism.CONSTRUAL_LEVEL: BetaDistribution(
        alpha=2.5, beta=2.5  # Neutral - varies widely by context
    ),
    CognitiveMechanism.REGULATORY_FOCUS: BetaDistribution(
        alpha=3.0, beta=2.0  # Generally effective
    ),
    CognitiveMechanism.AUTOMATIC_EVALUATION: BetaDistribution(
        alpha=3.5, beta=1.5  # Strong - emotional appeals work
    ),
    CognitiveMechanism.WANTING_LIKING: BetaDistribution(
        alpha=3.0, beta=2.0  # Effective for hedonic products
    ),
    CognitiveMechanism.MIMETIC_DESIRE: BetaDistribution(
        alpha=3.5, beta=2.0  # Social proof is powerful
    ),
    CognitiveMechanism.ATTENTION_DYNAMICS: BetaDistribution(
        alpha=2.5, beta=2.5  # Neutral - context dependent
    ),
    CognitiveMechanism.TEMPORAL_CONSTRUAL: BetaDistribution(
        alpha=2.0, beta=3.0  # Slightly weak - future discounting
    ),
    CognitiveMechanism.IDENTITY_CONSTRUCTION: BetaDistribution(
        alpha=3.0, beta=2.0  # Effective for lifestyle products
    ),
    CognitiveMechanism.EVOLUTIONARY_MOTIVE: BetaDistribution(
        alpha=2.5, beta=2.5  # Neutral - product dependent
    ),
}


class PopulationPriorEngine:
    """
    Engine for computing population-level priors.
    
    These are used as the base layer in the hierarchical prior system.
    """
    
    def __init__(self, config: Optional[PopulationPriorConfig] = None):
        self.config = config or PopulationPriorConfig()
        
        # Cache the population prior
        self._cached_prior: Optional[PsychologicalPrior] = None
    
    def get_population_prior(self) -> PsychologicalPrior:
        """
        Get the global population prior.
        
        Returns cached version if available.
        """
        if self._cached_prior is not None:
            return self._cached_prior
        
        # Build trait priors
        trait_priors = {}
        for trait, dist in POPULATION_TRAIT_PRIORS.items():
            trait_priors[trait] = TraitPrior(
                trait=trait,
                distribution=dist,
                source=PriorSource.POPULATION,
                confidence=1.0 - dist.variance * 10  # Lower variance = higher confidence
            )
        
        # Build mechanism priors
        mechanism_priors = {}
        for mech, dist in POPULATION_MECHANISM_PRIORS.items():
            mechanism_priors[mech] = MechanismPrior(
                mechanism=mech,
                distribution=dist,
                source=PriorSource.POPULATION
            )
        
        self._cached_prior = PsychologicalPrior(
            trait_priors=trait_priors,
            mechanism_priors=mechanism_priors,
            primary_source=PriorSource.POPULATION,
            sources_used=[PriorSource.POPULATION],
            overall_confidence=0.2  # Population is low confidence
        )
        
        return self._cached_prior
    
    def get_trait_prior(self, trait: PersonalityTrait) -> GaussianDistribution:
        """Get population prior for specific trait."""
        return POPULATION_TRAIT_PRIORS.get(
            trait,
            GaussianDistribution(mean=0.5, variance=0.0625)  # Uninformative
        )
    
    def get_mechanism_prior(self, mechanism: CognitiveMechanism) -> BetaDistribution:
        """Get population prior for specific mechanism."""
        return POPULATION_MECHANISM_PRIORS.get(
            mechanism,
            BetaDistribution(alpha=1.0, beta=1.0)  # Uninformative
        )
    
    def update_from_corpus(
        self,
        trait_means: Dict[PersonalityTrait, float],
        trait_variances: Dict[PersonalityTrait, float],
        mechanism_rates: Dict[CognitiveMechanism, float],
        mechanism_counts: Dict[CognitiveMechanism, int]
    ) -> None:
        """
        Update population priors from corpus analysis.
        
        Called during batch recomputation.
        """
        # Update trait priors
        for trait, mean in trait_means.items():
            variance = trait_variances.get(trait, 0.04)
            POPULATION_TRAIT_PRIORS[trait] = GaussianDistribution(
                mean=float(np.clip(mean, 0.0, 1.0)),
                variance=variance
            )
        
        # Update mechanism priors
        for mech, rate in mechanism_rates.items():
            count = mechanism_counts.get(mech, 10)
            # Convert rate to Beta parameters
            alpha = rate * count
            beta = (1 - rate) * count
            POPULATION_MECHANISM_PRIORS[mech] = BetaDistribution(
                alpha=max(1.0, alpha),
                beta=max(1.0, beta)
            )
        
        # Invalidate cache
        self._cached_prior = None
    
    def invalidate_cache(self) -> None:
        """Invalidate cached population prior."""
        self._cached_prior = None


# Singleton instance
_engine: Optional[PopulationPriorEngine] = None


def get_population_prior_engine() -> PopulationPriorEngine:
    """Get singleton population prior engine."""
    global _engine
    if _engine is None:
        _engine = PopulationPriorEngine()
    return _engine
