# =============================================================================
# ADAM Enhancement #13: Priors Package
# Location: adam/cold_start/priors/__init__.py
# =============================================================================

"""
Hierarchical Prior System for Cold Start

Provides priors at multiple levels of specificity:
1. Population - Global from Amazon corpus (least specific)
2. Demographic - Age/gender/location adjusted
3. Contextual - Content/time/device adjusted
4. Archetype - Matched archetype priors
5. User Historical - User's own history (most specific)

More specific priors receive higher weight when available.
"""

from .population import (
    PopulationPriorConfig,
    PopulationPriorEngine,
    get_population_prior_engine,
    POPULATION_TRAIT_PRIORS,
    POPULATION_MECHANISM_PRIORS,
)

from .demographic import (
    DemographicPriorEngine,
    get_demographic_prior_engine,
    AGE_TRAIT_ADJUSTMENTS,
    GENDER_TRAIT_ADJUSTMENTS,
    AGE_MECHANISM_ADJUSTMENTS,
)

from .maximizer_tendency import (
    ARCHETYPE_MAXIMIZER_PRIORS,
    ENGINE_EMPIRICAL_POPULATION,
    PRIOR_STRENGTH,
    SCHWARTZ_MAXIMIZER_WEIGHTS,
    SCORE_CLIP_MAX,
    SCORE_CLIP_MIN,
    SIGMOID_SLOPE,
    derive_maximizer_beta_priors,
    get_maximizer_tendency_prior,
)

__all__ = [
    # Population
    "PopulationPriorConfig",
    "PopulationPriorEngine",
    "get_population_prior_engine",
    "POPULATION_TRAIT_PRIORS",
    "POPULATION_MECHANISM_PRIORS",

    # Demographic
    "DemographicPriorEngine",
    "get_demographic_prior_engine",
    "AGE_TRAIT_ADJUSTMENTS",
    "GENDER_TRAIT_ADJUSTMENTS",
    "AGE_MECHANISM_ADJUSTMENTS",

    # Maximizer tendency (A.2 — extended-construct Beta priors)
    "ARCHETYPE_MAXIMIZER_PRIORS",
    "ENGINE_EMPIRICAL_POPULATION",
    "PRIOR_STRENGTH",
    "SCHWARTZ_MAXIMIZER_WEIGHTS",
    "SCORE_CLIP_MAX",
    "SCORE_CLIP_MIN",
    "SIGMOID_SLOPE",
    "derive_maximizer_beta_priors",
    "get_maximizer_tendency_prior",
]
