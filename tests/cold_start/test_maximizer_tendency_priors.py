"""A.2 — maximizer_tendency Beta prior derivation tests.

Per A.2 slice (predecessor: A.2.0 audit memo at
docs/audits/COLD_START_ARCHETYPE_PROFILES_AUDIT.md). Pin the
derivation function's correctness, the per-archetype Beta priors'
non-degeneracy and differentiation, the qualitative ordering pattern
predicted by Schwartz literature, the trait × state posterior-update
direction, and zero-regression on existing prior surfaces.
"""
from typing import Dict

import pytest

from adam.cold_start.archetypes.definitions import ARCHETYPE_DEFINITIONS
from adam.cold_start.models.enums import ArchetypeID
from adam.cold_start.models.priors import BetaDistribution
from adam.cold_start.priors.maximizer_tendency import (
    ARCHETYPE_MAXIMIZER_PRIORS,
    ENGINE_EMPIRICAL_POPULATION,
    PRIOR_STRENGTH,
    SCHWARTZ_MAXIMIZER_WEIGHTS,
    derive_maximizer_beta_priors,
    get_maximizer_tendency_prior,
)


# ---------------------------------------------------------------------------
# Test 1 — pure function existence and signature
# ---------------------------------------------------------------------------

def test_derive_function_exists_and_callable():
    """derive_maximizer_beta_priors is a callable that takes a dict
    of ArchetypeID → ArchetypeDefinition and returns a dict of
    ArchetypeID → BetaDistribution."""
    assert callable(derive_maximizer_beta_priors)
    result = derive_maximizer_beta_priors(ARCHETYPE_DEFINITIONS)
    assert isinstance(result, dict)
    for arch_id, prior in result.items():
        assert isinstance(arch_id, ArchetypeID)
        assert isinstance(prior, BetaDistribution)


# ---------------------------------------------------------------------------
# Test 2 — all 8 archetypes have a maximizer_tendency Beta prior
# ---------------------------------------------------------------------------

def test_all_eight_archetypes_have_priors():
    """Every ArchetypeID in {EXPLORER, ACHIEVER, CONNECTOR, GUARDIAN,
    ANALYST, CREATOR, NURTURER, PRAGMATIST} is a key in the derived
    priors."""
    result = derive_maximizer_beta_priors(ARCHETYPE_DEFINITIONS)
    assert len(result) == 8
    expected = {
        ArchetypeID.EXPLORER, ArchetypeID.ACHIEVER, ArchetypeID.CONNECTOR,
        ArchetypeID.GUARDIAN, ArchetypeID.ANALYST, ArchetypeID.CREATOR,
        ArchetypeID.NURTURER, ArchetypeID.PRAGMATIST,
    }
    assert set(result.keys()) == expected


# ---------------------------------------------------------------------------
# Test 3 — Beta priors are non-degenerate
# ---------------------------------------------------------------------------

def test_priors_non_degenerate():
    """For each archetype: 0.05 ≤ α/(α+β) ≤ 0.95. Degenerate priors
    (mean near 0 or 1) would make Bayesian updates pathological."""
    for arch_id, prior in ARCHETYPE_MAXIMIZER_PRIORS.items():
        mean = prior.alpha / (prior.alpha + prior.beta)
        assert 0.05 <= mean <= 0.95, (
            f"{arch_id.value} prior mean {mean:.4f} outside "
            f"[0.05, 0.95] non-degenerate band"
        )


# ---------------------------------------------------------------------------
# Test 4 — prior strength consistency (pseudo-count n=10)
# ---------------------------------------------------------------------------

def test_prior_strength_consistent():
    """For each archetype: α + β = PRIOR_STRENGTH (= 10.0) within
    1e-6 tolerance. Pseudo-count discipline per Q11.C."""
    for arch_id, prior in ARCHETYPE_MAXIMIZER_PRIORS.items():
        total = prior.alpha + prior.beta
        assert abs(total - PRIOR_STRENGTH) < 1e-6, (
            f"{arch_id.value} prior α+β={total:.6f} != "
            f"PRIOR_STRENGTH={PRIOR_STRENGTH}"
        )


# ---------------------------------------------------------------------------
# Test 5 — differentiation invariant (max - min ≥ 0.20)
# ---------------------------------------------------------------------------

def test_differentiation_invariant():
    """Substantive differentiation: max(means) - min(means) ≥ 0.20.
    If all priors collapse to similar means, derivation is
    miscalibrated and archetype-specific priors lose their purpose."""
    means = [
        prior.alpha / (prior.alpha + prior.beta)
        for prior in ARCHETYPE_MAXIMIZER_PRIORS.values()
    ]
    diff = max(means) - min(means)
    assert diff >= 0.20, (
        f"Differentiation max-min = {diff:.4f} < 0.20 — priors "
        f"too similar across archetypes"
    )


# ---------------------------------------------------------------------------
# Test 6 — qualitative ordering sanity per audit §6.4
# ---------------------------------------------------------------------------

def _mean_of(arch_id: ArchetypeID) -> float:
    prior = ARCHETYPE_MAXIMIZER_PRIORS[arch_id]
    return prior.alpha / (prior.alpha + prior.beta)


class TestQualitativeOrderingSanity:
    """Per audit §6.4 illustrative pattern. Don't pin every pairwise
    ordering — qualitative direction only. Schwartz literature: high
    C + high N → maximizer; high A → satisficer."""

    def test_guardian_higher_than_connector(self):
        """GUARDIAN (high N + high C) > CONNECTOR (high A + high E,
        low C)."""
        assert _mean_of(ArchetypeID.GUARDIAN) > _mean_of(ArchetypeID.CONNECTOR)

    def test_analyst_higher_than_explorer(self):
        """ANALYST (high C, deliberate) > EXPLORER (lower C)."""
        assert _mean_of(ArchetypeID.ANALYST) > _mean_of(ArchetypeID.EXPLORER)

    def test_top_3_archetypes_in_expected_set(self):
        """Top 3 by maximizer prior mean should be within the audit's
        predicted set {GUARDIAN, ANALYST, ACHIEVER}, allowing 1 swap
        with {NURTURER, CREATOR}."""
        rankings = sorted(
            ARCHETYPE_MAXIMIZER_PRIORS.items(),
            key=lambda kv: -_mean_of(kv[0]),
        )
        top_3 = {arch_id for arch_id, _ in rankings[:3]}
        expected_core = {
            ArchetypeID.GUARDIAN, ArchetypeID.ANALYST, ArchetypeID.ACHIEVER,
        }
        allowed_swaps = {ArchetypeID.NURTURER, ArchetypeID.CREATOR}
        # All of top_3 must be in expected_core ∪ allowed_swaps,
        # and at least 2 of expected_core must appear in top_3.
        assert top_3.issubset(expected_core | allowed_swaps), (
            f"top_3={[a.value for a in top_3]} contains unexpected "
            f"archetype outside expected_core ∪ allowed_swaps"
        )
        assert len(top_3 & expected_core) >= 2, (
            f"top_3={[a.value for a in top_3]} contains fewer than "
            f"2 of expected_core={[a.value for a in expected_core]}"
        )


# ---------------------------------------------------------------------------
# Test 7 — z-score reference uses engine-empirical (per Q11.A=(β))
# ---------------------------------------------------------------------------

def test_engine_empirical_population_matches_audit_section_6():
    """Per Q11.A=(β) adjudication + audit §6.1 reference table."""
    expected = {
        "openness":          (0.6250, 0.1604),
        "conscientiousness": (0.6313, 0.1607),
        "extraversion":      (0.5563, 0.1675),
        "agreeableness":     (0.6188, 0.1416),
        "neuroticism":       (0.4313, 0.1130),
    }
    for trait, (exp_mu, exp_sigma) in expected.items():
        assert trait in ENGINE_EMPIRICAL_POPULATION, (
            f"missing trait {trait} in ENGINE_EMPIRICAL_POPULATION"
        )
        actual_mu, actual_sigma = ENGINE_EMPIRICAL_POPULATION[trait]
        assert abs(actual_mu - exp_mu) < 1e-9, (
            f"{trait} μ={actual_mu} != audit expected {exp_mu}"
        )
        assert abs(actual_sigma - exp_sigma) < 1e-9, (
            f"{trait} σ={actual_sigma} != audit expected {exp_sigma}"
        )


# ---------------------------------------------------------------------------
# Test 8 — Schwartz weights normalized (per Q11.B)
# ---------------------------------------------------------------------------

def test_schwartz_weights_sum_to_one_in_absolute_value():
    """Per Q11.B adjudication: |w_O| + |w_C| + |w_A| + |w_N| = 1.0."""
    total_abs = sum(abs(w) for w in SCHWARTZ_MAXIMIZER_WEIGHTS.values())
    assert abs(total_abs - 1.0) < 1e-9, (
        f"sum of |Schwartz weights| = {total_abs:.9f} != 1.0"
    )


def test_schwartz_weights_e_term_dropped():
    """Per Q11.B: E term dropped (negligible empirical weight per
    Schwartz literature)."""
    assert "extraversion" not in SCHWARTZ_MAXIMIZER_WEIGHTS


def test_schwartz_weights_signs_match_literature():
    """Schwartz et al. 2002: maximizers correlate +O, +C, -A, +N
    (more open, more deliberate, less agreeable, more anxious)."""
    assert SCHWARTZ_MAXIMIZER_WEIGHTS["openness"] > 0
    assert SCHWARTZ_MAXIMIZER_WEIGHTS["conscientiousness"] > 0
    assert SCHWARTZ_MAXIMIZER_WEIGHTS["agreeableness"] < 0
    assert SCHWARTZ_MAXIMIZER_WEIGHTS["neuroticism"] > 0


# ---------------------------------------------------------------------------
# Test 9 — posterior update direction (trait × state interaction
#          demonstration)
# ---------------------------------------------------------------------------

def test_posterior_update_direction_trait_x_state():
    """Initialize maximizer_tendency Beta posteriors for ANALYST and
    PRAGMATIST. Apply 5 synthetic 'high-comparison-shopping' Bayesian
    updates (each increments α by 1.0). Verify both posteriors move
    upward; PRAGMATIST's upward movement is LARGER in absolute terms
    because PRAGMATIST starts further from where evidence points,
    and the prior pulls less hard once posterior strength grows.

    This pins the multiplicative trait × state architecture: state
    evidence reshapes the trait posterior in a direction-aware way.
    """
    analyst_prior = ARCHETYPE_MAXIMIZER_PRIORS[ArchetypeID.ANALYST]
    pragmatist_prior = ARCHETYPE_MAXIMIZER_PRIORS[ArchetypeID.PRAGMATIST]

    analyst_initial_mean = (
        analyst_prior.alpha / (analyst_prior.alpha + analyst_prior.beta)
    )
    pragmatist_initial_mean = (
        pragmatist_prior.alpha
        / (pragmatist_prior.alpha + pragmatist_prior.beta)
    )

    # Apply 5 'high-comparison-shopping' updates (each = success = True
    # increments α by 1.0 via BetaDistribution.update).
    analyst_posterior = analyst_prior
    pragmatist_posterior = pragmatist_prior
    for _ in range(5):
        analyst_posterior = analyst_posterior.update(success=True)
        pragmatist_posterior = pragmatist_posterior.update(success=True)

    analyst_posterior_mean = (
        analyst_posterior.alpha
        / (analyst_posterior.alpha + analyst_posterior.beta)
    )
    pragmatist_posterior_mean = (
        pragmatist_posterior.alpha
        / (pragmatist_posterior.alpha + pragmatist_posterior.beta)
    )

    # Both posteriors move upward (evidence reinforces).
    assert analyst_posterior_mean > analyst_initial_mean, (
        f"ANALYST posterior {analyst_posterior_mean:.4f} did not "
        f"move upward from prior {analyst_initial_mean:.4f}"
    )
    assert pragmatist_posterior_mean > pragmatist_initial_mean, (
        f"PRAGMATIST posterior {pragmatist_posterior_mean:.4f} did "
        f"not move upward from prior {pragmatist_initial_mean:.4f}"
    )

    # PRAGMATIST's upward movement is larger in absolute terms —
    # PRAGMATIST starts lower (prior mean ≈ 0.48) and 5 successes
    # have larger marginal effect than for ANALYST (prior mean
    # ≈ 0.61, closer to where evidence points).
    analyst_delta = analyst_posterior_mean - analyst_initial_mean
    pragmatist_delta = pragmatist_posterior_mean - pragmatist_initial_mean
    assert pragmatist_delta > analyst_delta, (
        f"PRAGMATIST Δ={pragmatist_delta:.4f} should exceed ANALYST "
        f"Δ={analyst_delta:.4f} (lower-prior posterior absorbs more "
        f"evidence shift per identical observation count)"
    )


# ---------------------------------------------------------------------------
# Test 10 — zero-regression invariant (existing priors untouched)
# ---------------------------------------------------------------------------

class TestZeroRegression:
    """A.2 must not modify any pre-existing prior surface. The slice
    is purely additive — derives + registers maximizer_tendency Beta
    priors per archetype, nothing else."""

    def test_archetype_trait_profiles_unchanged(self):
        """ARCHETYPE_TRAIT_PROFILES (the input to A.2's derivation)
        must be untouched by A.2. Spot-check 3 archetype-trait
        means against audit-recorded values."""
        from adam.cold_start.archetypes.definitions import (
            ARCHETYPE_TRAIT_PROFILES,
        )
        # Audit §3 Pass 2 spot-checks
        assert (
            ARCHETYPE_TRAIT_PROFILES[ArchetypeID.ANALYST]
            .conscientiousness.mean == 0.80
        )
        assert (
            ARCHETYPE_TRAIT_PROFILES[ArchetypeID.NURTURER]
            .agreeableness.mean == 0.90
        )
        assert (
            ARCHETYPE_TRAIT_PROFILES[ArchetypeID.GUARDIAN]
            .neuroticism.mean == 0.65
        )

    def test_population_trait_priors_unchanged(self):
        """POPULATION_TRAIT_PRIORS in adam/cold_start/priors/population.py
        must be untouched. These are the Big Five population-level
        priors that A.2 does NOT use as z-score reference (per
        Q11.A=(β) chose engine-empirical instead). A.2 must not
        modify them as a side effect."""
        from adam.cold_start.models.enums import PersonalityTrait
        from adam.cold_start.priors.population import (
            POPULATION_TRAIT_PRIORS,
        )
        # Spot-check the 5 Big Five population priors.
        for trait in (
            PersonalityTrait.OPENNESS,
            PersonalityTrait.CONSCIENTIOUSNESS,
            PersonalityTrait.EXTRAVERSION,
            PersonalityTrait.AGREEABLENESS,
            PersonalityTrait.NEUROTICISM,
        ):
            assert trait in POPULATION_TRAIT_PRIORS
            prior = POPULATION_TRAIT_PRIORS[trait]
            assert 0.0 <= prior.mean <= 1.0
            assert prior.variance > 0

    def test_archetype_mechanism_priors_unchanged(self):
        """ARCHETYPE_MECHANISM_PRIORS (the per-archetype-per-mechanism
        Beta prior registry — the precedent A.2's pattern parallels)
        must be untouched."""
        from adam.cold_start.archetypes.definitions import (
            ARCHETYPE_MECHANISM_PRIORS,
        )
        from adam.cold_start.models.enums import CognitiveMechanism
        # All 8 archetypes still present.
        assert len(ARCHETYPE_MECHANISM_PRIORS) == 8
        # Each archetype still has all 9 mechanism priors.
        for arch_id, mech_priors in ARCHETYPE_MECHANISM_PRIORS.items():
            assert len(mech_priors) == 9
            for mech, (alpha, beta) in mech_priors.items():
                assert isinstance(mech, CognitiveMechanism)
                assert alpha > 0 and beta > 0


# ---------------------------------------------------------------------------
# Bonus — accessor function works
# ---------------------------------------------------------------------------

def test_get_maximizer_tendency_prior_accessor():
    """get_maximizer_tendency_prior(arch_id) returns the same prior
    as direct dict access."""
    for arch_id in ArchetypeID:
        # Skip enum members that aren't archetype IDs (the enum may
        # have other members we're not deriving for; the dict will
        # raise KeyError for those).
        if arch_id not in ARCHETYPE_MAXIMIZER_PRIORS:
            continue
        accessor_result = get_maximizer_tendency_prior(arch_id)
        dict_result = ARCHETYPE_MAXIMIZER_PRIORS[arch_id]
        assert accessor_result is dict_result, (
            f"accessor for {arch_id.value} returned different object "
            f"than dict access"
        )


# ---------------------------------------------------------------------------
# Bonus — pure function determinism
# ---------------------------------------------------------------------------

def test_derivation_is_deterministic():
    """Calling derive_maximizer_beta_priors twice with the same input
    yields identical results (no random seed, no I/O)."""
    result_a = derive_maximizer_beta_priors(ARCHETYPE_DEFINITIONS)
    result_b = derive_maximizer_beta_priors(ARCHETYPE_DEFINITIONS)
    assert set(result_a.keys()) == set(result_b.keys())
    for arch_id in result_a:
        assert result_a[arch_id].alpha == result_b[arch_id].alpha
        assert result_a[arch_id].beta == result_b[arch_id].beta
