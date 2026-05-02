# =============================================================================
# Phase 9 simulation — synthetic population
# Location: adam/intelligence/simulation/population.py
# =============================================================================
"""Generate a synthetic LUXY-plausible user population per a
SimulationConfig.

Each user has TRUE latent parameters that the SyntheticWorld uses to
produce impressions + outcomes. The architectures under test do NOT
see these — they only see (user_id, mechanism_sent, outcome) tuples.
The "lift" each architecture earns over the baseline is its
demonstrable value.

The population structure mirrors the directive's Spine #1 model:
each user has per-mechanism efficacy parameters that depend on cohort
membership + cohort separation regime + true interaction strength.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from adam.intelligence.simulation.config import (
    CohortSeparation,
    InteractionStrength,
    SimulationConfig,
)


@dataclass(frozen=True)
class SyntheticUser:
    """One synthetic user.

    ``user_id``: stable id (string) used by architectures.
    ``cohort_id``: which cohort this user belongs to.
    ``true_mechanism_efficacy``: per-mechanism TRUE conversion-given-
        click probability for THIS user. Architectures only learn this
        through observation; the baseline is config.user_base_ctr ×
        config.conversion_rate_given_click. The actual efficacy ranges
        around the baseline depending on the cohort separation +
        interaction strength.
    ``true_carryover_rho``: per-user AR(1) carryover coefficient. For
        Architecture A (no carryover model) this is invisible; for
        Architecture C+ this is what they're trying to estimate.
    """

    user_id: str
    cohort_id: int
    true_mechanism_efficacy: Dict[str, float]
    true_carryover_rho: float = 0.0


@dataclass(frozen=True)
class SyntheticPopulation:
    """A synthetic user population for one SimulationConfig cell."""

    users: List[SyntheticUser]
    mechanisms: List[str]
    n_cohorts: int
    config: SimulationConfig

    def by_cohort(self) -> Dict[int, List[SyntheticUser]]:
        out: Dict[int, List[SyntheticUser]] = {}
        for u in self.users:
            out.setdefault(u.cohort_id, []).append(u)
        return out


# =============================================================================
# Helpers
# =============================================================================


def _separation_signal_to_noise(separation: CohortSeparation) -> float:
    """Higher = cohorts produce more distinct mechanism-efficacy
    profiles. Used to scale the cohort-mean offset relative to within-
    cohort noise."""
    return {
        CohortSeparation.INDISTINGUISHABLE: 0.0,
        CohortSeparation.WEAKLY_SEPARABLE: 0.3,
        CohortSeparation.STRONGLY_SEPARABLE: 1.0,
    }[separation]


def _interaction_amplitude(strength: InteractionStrength) -> float:
    """Per-user × per-mechanism interaction component amplitude (added
    on top of cohort-level mean). Higher = the user's individual
    response varies more from the cohort baseline."""
    return {
        InteractionStrength.NONE: 0.0,
        InteractionStrength.WEAK: 0.05,
        InteractionStrength.MODERATE: 0.15,
        InteractionStrength.STRONG: 0.30,
    }[strength]


def _default_mechanisms(n: int) -> List[str]:
    """Canonical mechanism names used throughout the codebase. The
    simulation uses a subset of size ``n`` (= config.n_mechanisms)."""
    pool = (
        "social_proof", "scarcity", "authority", "reciprocity",
        "commitment", "liking", "unity", "reason_why",
    )
    return list(pool[:max(1, min(n, len(pool)))])


def generate_population(config: SimulationConfig) -> SyntheticPopulation:
    """Build a synthetic population for one cell.

    Determinism: seeded by ``config.seed`` so re-runs of the same cell
    produce identical populations (necessary for reproducible sweeps).

    Per-user TRUE efficacy:
        baseline = config.user_base_ctr × config.conversion_rate_given_click
        cohort_offset = sep_factor × cohort_specific_drift_per_mech
        user_interaction = interaction_amp × N(0, 1)
        true_efficacy[m] = clip(baseline × (1 + cohort_offset[m]
                                  + user_interaction), 0.0001, 0.5)

    The cohort_offset is drawn ONCE per cohort × mechanism cell so
    cohorts have stable mechanism-efficacy fingerprints (the thing
    Architecture B onward is supposed to discover).
    """
    rng = random.Random(int(config.seed))

    mechanisms = _default_mechanisms(config.n_mechanisms)
    sep_factor = _separation_signal_to_noise(config.cohort_separation)
    interaction_amp = _interaction_amplitude(config.interaction_strength)

    # Cohort-level mechanism offsets — one fingerprint per cohort.
    cohort_offsets: Dict[int, Dict[str, float]] = {}
    for c in range(config.n_cohorts):
        cohort_offsets[c] = {
            m: sep_factor * rng.gauss(0.0, 1.0) for m in mechanisms
        }

    baseline = (
        config.user_base_ctr * config.conversion_rate_given_click
    )

    users: List[SyntheticUser] = []
    user_ix = 0
    for c in range(config.n_cohorts):
        for _ in range(config.audience_size_per_cohort):
            efficacy: Dict[str, float] = {}
            for m in mechanisms:
                offset = cohort_offsets[c][m]
                interaction = (
                    interaction_amp * rng.gauss(0.0, 1.0)
                    if interaction_amp > 0.0 else 0.0
                )
                # Combine multiplicatively (1 + offset + interaction)
                # so values stay near the baseline order of magnitude.
                eff = baseline * (1.0 + offset + interaction)
                eff = max(1e-4, min(0.5, eff))
                efficacy[m] = eff

            # Per-user carryover rho — bounded, mean 0.
            rho = 0.5 * rng.gauss(0.0, 1.0)
            rho = max(-0.99, min(0.99, rho))

            users.append(SyntheticUser(
                user_id=f"sim-u-{user_ix:07d}",
                cohort_id=c,
                true_mechanism_efficacy=efficacy,
                true_carryover_rho=rho,
            ))
            user_ix += 1

    return SyntheticPopulation(
        users=users,
        mechanisms=mechanisms,
        n_cohorts=config.n_cohorts,
        config=config,
    )
