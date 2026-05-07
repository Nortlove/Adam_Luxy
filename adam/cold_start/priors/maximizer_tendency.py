"""Maximizer tendency Beta prior derivation from archetype Big Five profiles.

Per A.2 slice (predecessor: A.2.0 audit memo at
docs/audits/COLD_START_ARCHETYPE_PROFILES_AUDIT.md). Converts archetype
Gaussian profiles into per-archetype Beta priors for the
maximizer_tendency PersonalityDimension via z-score normalization
against engine-empirical (mu, sigma) per Big Five trait, weighted by
Schwartz et al. 2002 trait correlates of maximization.

Z-score reference (mu, sigma) per trait is engine-empirical (computed
across the 8 archetype profiles in
adam/cold_start/archetypes/definitions.py), NOT literature-rescaled
Costa-McCrae norms. Per Q11.A=(beta) adjudication: differentiation we
care about is archetype-relative-to-engine, not archetype-relative-to-
general-population. The engine's internal convention shifts ~0.04-0.11
below literature norms; using literature norms would compress
differentiation. See docs/audits/COLD_START_ARCHETYPE_PROFILES_AUDIT.md
section 6 for full rationale.

Per Q11.B adjudication: Schwartz weights {O: +0.20, C: +0.40,
A: -0.20, N: +0.20}. E term dropped (negligible empirical weight per
literature). Sum of absolute values = 1.0 (clean normalization).

Per Q11.C adjudication: pseudo-count strength n=10 (informative but
updatable; ~10 prior observations equivalent, so 5-10 real bid
observations update the posterior meaningfully).

References:
    Schwartz, B., Ward, A., Monterosso, J., Lyubomirsky, S., White, K.,
        & Lehman, D. R. (2002). Maximizing versus satisficing:
        Happiness is a matter of choice. Journal of Personality and
        Social Psychology, 83(5), 1178-1197.
    Bruine de Bruin, W., Parker, A. M., & Fischhoff, B. (2007).
        Individual differences in adult decision-making competence.
        Journal of Personality and Social Psychology, 92(5), 938-956.
"""
import math
from typing import Dict

from adam.cold_start.archetypes.definitions import ARCHETYPE_DEFINITIONS
from adam.cold_start.models.archetypes import ArchetypeDefinition
from adam.cold_start.models.enums import ArchetypeID
from adam.cold_start.models.priors import BetaDistribution


# =============================================================================
# Constants — engine-empirical population reference per Q11.A=(beta)
# =============================================================================

# Engine-empirical per-trait (mean, std) computed across the 8 archetype
# profiles in adam/cold_start/archetypes/definitions.py. See audit memo
# section 6 for derivation. Each std is the SAMPLE STANDARD DEVIATION
# of the 8 archetype means per trait, NOT the within-archetype variance
# from GaussianDistribution.
ENGINE_EMPIRICAL_POPULATION: Dict[str, tuple] = {
    "openness":          (0.6250, 0.1604),
    "conscientiousness": (0.6313, 0.1607),
    "extraversion":      (0.5563, 0.1675),
    "agreeableness":     (0.6188, 0.1416),
    "neuroticism":       (0.4313, 0.1130),
}


# Schwartz et al. 2002 + Bruine de Bruin et al. 2007 trait correlates
# of maximization. Per Q11.B adjudication: E term dropped (empirical
# weight near zero); other weights normalized so sum-of-absolute-values
# equals 1.0.
SCHWARTZ_MAXIMIZER_WEIGHTS: Dict[str, float] = {
    "openness":          +0.20,
    "conscientiousness": +0.40,
    "agreeableness":     -0.20,
    "neuroticism":       +0.20,
}


# Sigmoid slope for converting raw weighted z-score sum to [0, 1] score.
# Slope of 0.7 means a one-SD-on-conscientiousness deviation
# (raw_z ≈ +0.40) maps to score ≈ 0.57 (mild maximizer tilt). A
# two-SD-on-conscientiousness deviation maps to score ≈ 0.69.
# Calibration choice informed by need to produce non-degenerate priors
# that differentiate archetypes substantively but don't collapse to
# extreme poles.
SIGMOID_SLOPE: float = 0.7


# Pseudo-count strength per Q11.C: n=10. Each archetype's prior is
# equivalent to ~10 prior observations — informative enough to
# differentiate, light enough that 5-10 real bid observations update
# the posterior meaningfully.
PRIOR_STRENGTH: float = 10.0


# Score clipping bounds prevent degenerate Beta priors near 0 or 1
# (which would make Bayesian updates pathological).
SCORE_CLIP_MIN: float = 0.05
SCORE_CLIP_MAX: float = 0.95


# =============================================================================
# Pure derivation function
# =============================================================================

def derive_maximizer_beta_priors(
    archetype_definitions: Dict[ArchetypeID, ArchetypeDefinition],
) -> Dict[ArchetypeID, BetaDistribution]:
    """Derive per-archetype Beta priors for maximizer_tendency.

    Pure function — no I/O, no global state mutation. Deterministic
    given the input archetype_definitions.

    Args:
        archetype_definitions: dict mapping ArchetypeID to
            ArchetypeDefinition. Source: ARCHETYPE_DEFINITIONS in
            adam/cold_start/archetypes/definitions.py.

    Returns:
        dict mapping ArchetypeID to BetaDistribution(alpha, beta) for
        maximizer_tendency. Each Beta prior has alpha + beta == PRIOR_STRENGTH
        (= 10.0) by construction.

    Method:
        1. For each archetype, extract the 4 Big Five trait means
           (O, C, A, N) from its trait_profile.
        2. Z-score each trait against engine-empirical (mu, sigma).
        3. Compute weighted z-score sum using SCHWARTZ_MAXIMIZER_WEIGHTS.
        4. Sigmoid-transform the sum to a score in (0, 1).
        5. Clip score to [SCORE_CLIP_MIN, SCORE_CLIP_MAX] to avoid
           degenerate priors.
        6. Scale to (alpha, beta) using PRIOR_STRENGTH:
           alpha = score * n, beta = (1 - score) * n.

    Notes:
        - Big Five Extraversion (E) is not used (per Q11.B adjudication
          dropping E term; empirical correlation with maximization near
          zero in Schwartz literature).
        - sigma derived from variance via the .std computed_field on
          GaussianDistribution (which calls sqrt(variance)). The
          engine schema stores variance, not std (per audit section 2).
    """
    priors: Dict[ArchetypeID, BetaDistribution] = {}

    for archetype_id, archetype_def in archetype_definitions.items():
        profile = archetype_def.trait_profile

        trait_means = {
            "openness":          profile.openness.mean,
            "conscientiousness": profile.conscientiousness.mean,
            "agreeableness":     profile.agreeableness.mean,
            "neuroticism":       profile.neuroticism.mean,
        }

        # Weighted z-score sum.
        raw_z_sum = 0.0
        for trait_name, weight in SCHWARTZ_MAXIMIZER_WEIGHTS.items():
            pop_mu, pop_sigma = ENGINE_EMPIRICAL_POPULATION[trait_name]
            trait_z = (trait_means[trait_name] - pop_mu) / pop_sigma
            raw_z_sum += weight * trait_z

        # Sigmoid to [0, 1].
        score = 1.0 / (1.0 + math.exp(-SIGMOID_SLOPE * raw_z_sum))

        # Clip to avoid degenerate Beta priors.
        score_clipped = max(SCORE_CLIP_MIN, min(SCORE_CLIP_MAX, score))

        # Scale to (alpha, beta) with pseudo-count strength.
        alpha = score_clipped * PRIOR_STRENGTH
        beta = (1.0 - score_clipped) * PRIOR_STRENGTH

        priors[archetype_id] = BetaDistribution(alpha=alpha, beta=beta)

    return priors


# =============================================================================
# Module-level registry — populated at import time
# =============================================================================

# Per-archetype Beta priors for maximizer_tendency. Populated by
# calling derive_maximizer_beta_priors against ARCHETYPE_DEFINITIONS
# from adam/cold_start/archetypes/definitions.py at module load.
# Pattern parallels ARCHETYPE_MECHANISM_PRIORS in definitions.py
# (per-archetype Beta priors keyed by ArchetypeID, but for a single
# extended-construct dimension rather than the full mechanism set).
ARCHETYPE_MAXIMIZER_PRIORS: Dict[ArchetypeID, BetaDistribution] = (
    derive_maximizer_beta_priors(ARCHETYPE_DEFINITIONS)
)


def get_maximizer_tendency_prior(
    archetype_id: ArchetypeID,
) -> BetaDistribution:
    """Accessor for an archetype's maximizer_tendency Beta prior.

    Args:
        archetype_id: ArchetypeID enum value.

    Returns:
        BetaDistribution(alpha, beta) for that archetype's
        maximizer_tendency prior, with alpha + beta == PRIOR_STRENGTH.

    Raises:
        KeyError: if archetype_id is not in ARCHETYPE_MAXIMIZER_PRIORS.
    """
    return ARCHETYPE_MAXIMIZER_PRIORS[archetype_id]
