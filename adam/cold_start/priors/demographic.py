# =============================================================================
# ADAM Enhancement #13: Demographic Priors
# Location: adam/cold_start/priors/demographic.py
# =============================================================================

"""
Demographic-conditioned priors.

These priors adjust population baselines based on demographic factors
like age, gender, location, education, and income.

Based on:
- Costa & McCrae lifespan development research
- Schmitt et al. cross-cultural personality research
"""

from __future__ import annotations
from typing import Dict, Optional, Tuple
import numpy as np

from adam.cold_start.models.enums import (
    PersonalityTrait, CognitiveMechanism, PriorSource
)
from adam.cold_start.models.priors import (
    BetaDistribution, GaussianDistribution, TraitPrior, MechanismPrior,
    PsychologicalPrior
)
from .population import PopulationPriorEngine, get_population_prior_engine


# =============================================================================
# DEMOGRAPHIC ADJUSTMENT TABLES
# =============================================================================

# Age-based trait adjustments (deviations from population mean)
# Source: Costa & McCrae lifespan development research
AGE_TRAIT_ADJUSTMENTS: Dict[str, Dict[PersonalityTrait, float]] = {
    "18-24": {
        PersonalityTrait.OPENNESS: +0.08,
        PersonalityTrait.CONSCIENTIOUSNESS: -0.06,
        PersonalityTrait.EXTRAVERSION: +0.04,
        PersonalityTrait.AGREEABLENESS: -0.04,
        PersonalityTrait.NEUROTICISM: +0.06,
    },
    "25-34": {
        PersonalityTrait.OPENNESS: +0.04,
        PersonalityTrait.CONSCIENTIOUSNESS: +0.02,
        PersonalityTrait.EXTRAVERSION: +0.02,
        PersonalityTrait.AGREEABLENESS: +0.00,
        PersonalityTrait.NEUROTICISM: +0.02,
    },
    "35-44": {
        PersonalityTrait.OPENNESS: +0.00,
        PersonalityTrait.CONSCIENTIOUSNESS: +0.04,
        PersonalityTrait.EXTRAVERSION: -0.02,
        PersonalityTrait.AGREEABLENESS: +0.02,
        PersonalityTrait.NEUROTICISM: -0.02,
    },
    "45-54": {
        PersonalityTrait.OPENNESS: -0.02,
        PersonalityTrait.CONSCIENTIOUSNESS: +0.04,
        PersonalityTrait.EXTRAVERSION: -0.04,
        PersonalityTrait.AGREEABLENESS: +0.04,
        PersonalityTrait.NEUROTICISM: -0.04,
    },
    "55-64": {
        PersonalityTrait.OPENNESS: -0.04,
        PersonalityTrait.CONSCIENTIOUSNESS: +0.02,
        PersonalityTrait.EXTRAVERSION: -0.06,
        PersonalityTrait.AGREEABLENESS: +0.06,
        PersonalityTrait.NEUROTICISM: -0.06,
    },
    "65+": {
        PersonalityTrait.OPENNESS: -0.06,
        PersonalityTrait.CONSCIENTIOUSNESS: +0.00,
        PersonalityTrait.EXTRAVERSION: -0.08,
        PersonalityTrait.AGREEABLENESS: +0.08,
        PersonalityTrait.NEUROTICISM: -0.08,
    },
}

# Gender-based trait adjustments
# Source: Schmitt et al. cross-cultural personality research
GENDER_TRAIT_ADJUSTMENTS: Dict[str, Dict[PersonalityTrait, float]] = {
    "male": {
        PersonalityTrait.OPENNESS: +0.02,
        PersonalityTrait.CONSCIENTIOUSNESS: -0.02,
        PersonalityTrait.EXTRAVERSION: +0.00,
        PersonalityTrait.AGREEABLENESS: -0.06,
        PersonalityTrait.NEUROTICISM: -0.06,
    },
    "female": {
        PersonalityTrait.OPENNESS: -0.02,
        PersonalityTrait.CONSCIENTIOUSNESS: +0.02,
        PersonalityTrait.EXTRAVERSION: +0.00,
        PersonalityTrait.AGREEABLENESS: +0.06,
        PersonalityTrait.NEUROTICISM: +0.06,
    },
}

# Age-based mechanism effectiveness adjustments
# (alpha_mult, beta_mult) - multipliers for base prior
AGE_MECHANISM_ADJUSTMENTS: Dict[str, Dict[CognitiveMechanism, Tuple[float, float]]] = {
    "18-24": {
        CognitiveMechanism.MIMETIC_DESIRE: (1.3, 0.8),  # Social proof stronger
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (1.2, 0.9),
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (0.8, 1.2),  # Future focus weaker
    },
    "25-34": {
        CognitiveMechanism.REGULATORY_FOCUS: (1.2, 0.9),
        CognitiveMechanism.IDENTITY_CONSTRUCTION: (1.2, 0.9),
    },
    "35-44": {
        CognitiveMechanism.REGULATORY_FOCUS: (1.3, 0.8),  # Peak career focus
        CognitiveMechanism.AUTOMATIC_EVALUATION: (1.1, 0.9),
    },
    "45-54": {
        CognitiveMechanism.WANTING_LIKING: (1.2, 0.9),
        CognitiveMechanism.EVOLUTIONARY_MOTIVE: (0.9, 1.1),
    },
    "55-64": {
        CognitiveMechanism.TEMPORAL_CONSTRUAL: (1.2, 0.9),  # Future planning
        CognitiveMechanism.MIMETIC_DESIRE: (0.8, 1.2),  # Less social influence
    },
    "65+": {
        CognitiveMechanism.AUTOMATIC_EVALUATION: (1.2, 0.9),  # Rely on gut
        CognitiveMechanism.ATTENTION_DYNAMICS: (0.9, 1.1),  # Selective attention
    },
}


class DemographicPriorEngine:
    """
    Engine for computing demographic-conditioned priors.
    
    Adjusts population priors based on demographic factors.
    """
    
    def __init__(
        self,
        population_engine: Optional[PopulationPriorEngine] = None
    ):
        self.population_engine = population_engine or get_population_prior_engine()
    
    def get_demographic_prior(
        self,
        age_bracket: Optional[str] = None,
        gender: Optional[str] = None,
        country: Optional[str] = None,
        income_bracket: Optional[str] = None,
        education_level: Optional[str] = None
    ) -> PsychologicalPrior:
        """
        Get demographic-adjusted prior.
        
        Starts from population prior and applies demographic adjustments.
        """
        base_prior = self.population_engine.get_population_prior()
        
        # Collect adjustments
        trait_adjustments: Dict[PersonalityTrait, float] = {
            t: 0.0 for t in PersonalityTrait
        }
        mechanism_adjustments: Dict[CognitiveMechanism, Tuple[float, float]] = {}
        
        # Apply age adjustments
        if age_bracket and age_bracket in AGE_TRAIT_ADJUSTMENTS:
            for trait, adj in AGE_TRAIT_ADJUSTMENTS[age_bracket].items():
                trait_adjustments[trait] += adj
            
            if age_bracket in AGE_MECHANISM_ADJUSTMENTS:
                for mech, mult in AGE_MECHANISM_ADJUSTMENTS[age_bracket].items():
                    mechanism_adjustments[mech] = mult
        
        # Apply gender adjustments
        if gender and gender.lower() in GENDER_TRAIT_ADJUSTMENTS:
            for trait, adj in GENDER_TRAIT_ADJUSTMENTS[gender.lower()].items():
                trait_adjustments[trait] += adj
        
        # Build adjusted priors
        adjusted_trait_priors = {}
        for trait in PersonalityTrait:
            if trait in base_prior.trait_priors:
                base_dist = base_prior.trait_priors[trait].distribution
            else:
                base_dist = GaussianDistribution(mean=0.5, variance=0.04)
            
            adj = trait_adjustments[trait]
            
            adjusted_trait_priors[trait] = TraitPrior(
                trait=trait,
                distribution=GaussianDistribution(
                    mean=float(np.clip(base_dist.mean + adj, 0.0, 1.0)),
                    variance=base_dist.variance * 0.9  # Slightly more confident
                ),
                source=PriorSource.DEMOGRAPHIC,
                confidence=min(1.0, base_prior.trait_priors.get(
                    trait, 
                    TraitPrior(trait=trait, distribution=base_dist, source=PriorSource.POPULATION)
                ).confidence * 1.1)
            )
        
        adjusted_mech_priors = {}
        for mech in CognitiveMechanism:
            if mech in base_prior.mechanism_priors:
                base_dist = base_prior.mechanism_priors[mech].distribution
            else:
                base_dist = BetaDistribution(alpha=2.0, beta=2.0)
            
            if mech in mechanism_adjustments:
                alpha_mult, beta_mult = mechanism_adjustments[mech]
                adjusted_mech_priors[mech] = MechanismPrior(
                    mechanism=mech,
                    distribution=BetaDistribution(
                        alpha=base_dist.alpha * alpha_mult,
                        beta=base_dist.beta * beta_mult
                    ),
                    source=PriorSource.DEMOGRAPHIC
                )
            else:
                adjusted_mech_priors[mech] = MechanismPrior(
                    mechanism=mech,
                    distribution=base_dist,
                    source=PriorSource.DEMOGRAPHIC
                )
        
        # Calculate confidence based on how much demographic info we have
        demo_completeness = sum([
            1 if age_bracket else 0,
            1 if gender else 0,
            1 if country else 0,
            1 if income_bracket else 0,
            1 if education_level else 0
        ]) / 5.0
        
        return PsychologicalPrior(
            trait_priors=adjusted_trait_priors,
            mechanism_priors=adjusted_mech_priors,
            primary_source=PriorSource.DEMOGRAPHIC,
            sources_used=[PriorSource.POPULATION, PriorSource.DEMOGRAPHIC],
            overall_confidence=0.25 + demo_completeness * 0.15
        )


# Singleton instance
_engine: Optional[DemographicPriorEngine] = None


def get_demographic_prior_engine() -> DemographicPriorEngine:
    """Get singleton demographic prior engine."""
    global _engine
    if _engine is None:
        _engine = DemographicPriorEngine()
    return _engine
