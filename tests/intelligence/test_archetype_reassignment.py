"""W.2a — archetype_reassignment policy tests.

Pin: Q27=(ε) one-shot semantics; LLR threshold; numerical stability;
W.2b dependency (returns None when maximizer_tendency construct
absent); guard sequence per policy spec.
"""
import math

import pytest

from adam.cold_start.models.enums import ArchetypeID
from adam.cold_start.priors.maximizer_tendency import (
    ARCHETYPE_MAXIMIZER_PRIORS,
)
from adam.intelligence.archetype_reassignment import (
    MAXIMIZER_TENDENCY_DIMENSION,
    REASSIGNMENT_BID_THRESHOLD,
    REASSIGNMENT_LOG_LIKELIHOOD_RATIO_THRESHOLD,
    _beta_log_likelihood,
    evaluate_reassignment,
)
from adam.intelligence.information_value import (
    BuyerUncertaintyProfile,
    ConstructPosterior,
)


def _profile_with_maximizer(
    *,
    archetype: str = "pragmatist",
    bids_since: int = REASSIGNMENT_BID_THRESHOLD,
    reassigned: bool = False,
    user_alpha: float = 5.0,
    user_beta: float = 5.0,
):
    p = BuyerUncertaintyProfile(buyer_id="u")
    p.archetype = archetype
    p.archetype_assigned_at = "2026-05-08T00:00:00+00:00"
    p.archetype_reassigned = reassigned
    p.bids_since_archetype_assignment = bids_since
    p.constructs[MAXIMIZER_TENDENCY_DIMENSION] = ConstructPosterior(
        alpha=user_alpha, beta=user_beta,
    )
    return p


class TestGuardSequence:

    def test_returns_none_when_already_reassigned(self):
        p = _profile_with_maximizer(reassigned=True)
        assert evaluate_reassignment(p) is None

    def test_returns_none_when_archetype_is_none(self):
        p = BuyerUncertaintyProfile(buyer_id="u")
        # archetype is None by default
        assert evaluate_reassignment(p) is None

    def test_returns_none_when_bids_since_below_threshold(self):
        p = _profile_with_maximizer(
            bids_since=REASSIGNMENT_BID_THRESHOLD - 1,
        )
        assert evaluate_reassignment(p) is None

    def test_returns_none_when_bids_since_above_threshold(self):
        """Exactly at threshold (==), not >=. Per Q27=(ε) one-shot
        semantics: evaluator runs once at bid 20; later bids skip."""
        p = _profile_with_maximizer(
            bids_since=REASSIGNMENT_BID_THRESHOLD + 1,
        )
        assert evaluate_reassignment(p) is None

    def test_returns_none_when_maximizer_construct_absent(self):
        """W.2b dependency: maximizer_tendency dimension must exist
        on profile.constructs. Until W.2b ships, the construct is
        absent → reassignment policy dormant."""
        p = BuyerUncertaintyProfile(buyer_id="u")
        p.archetype = "pragmatist"
        p.bids_since_archetype_assignment = REASSIGNMENT_BID_THRESHOLD
        # Don't add MAXIMIZER_TENDENCY_DIMENSION
        if MAXIMIZER_TENDENCY_DIMENSION in p.constructs:
            del p.constructs[MAXIMIZER_TENDENCY_DIMENSION]
        assert evaluate_reassignment(p) is None


class TestReassignmentLogic:

    def test_reassigns_when_alternative_archetype_strongly_better(self):
        """Posterior with very high alpha (200) and low beta (10)
        signals strong maximizer tendency. ANALYST has highest alpha
        prior per A.2 derivation → should win."""
        p = _profile_with_maximizer(
            archetype="pragmatist",
            user_alpha=200.0, user_beta=10.0,
        )
        result = evaluate_reassignment(p)
        # Expect reassignment to a high-maximizer archetype
        # (typically ANALYST per A.2's z-score derivation).
        assert result is not None
        assert isinstance(result, ArchetypeID)
        assert result != ArchetypeID.PRAGMATIST

    def test_does_not_reassign_when_posterior_near_current_prior(self):
        """When the user's accumulated posterior is close to the
        current archetype's prior, no other archetype's prior fits
        substantially better → no reassignment."""
        prag_prior = ARCHETYPE_MAXIMIZER_PRIORS[ArchetypeID.PRAGMATIST]
        p = _profile_with_maximizer(
            archetype="pragmatist",
            user_alpha=prag_prior.alpha + 5.0,
            user_beta=prag_prior.beta + 5.0,
        )
        result = evaluate_reassignment(p)
        assert result is None

    def test_handles_unknown_archetype_value_gracefully(self):
        """Profile with an archetype value that doesn't coerce to
        ArchetypeID enum → return None (don't crash)."""
        p = _profile_with_maximizer(archetype="not_a_real_archetype")
        assert evaluate_reassignment(p) is None


class TestDeterminism:

    def test_same_profile_state_returns_same_result(self):
        p1 = _profile_with_maximizer(
            user_alpha=200.0, user_beta=10.0,
        )
        p2 = _profile_with_maximizer(
            user_alpha=200.0, user_beta=10.0,
        )
        assert evaluate_reassignment(p1) == evaluate_reassignment(p2)


class TestBetaLogLikelihood:

    def test_returns_finite_for_reasonable_priors(self):
        result = _beta_log_likelihood(
            observed_alpha=10.0, observed_beta=10.0,
            prior_alpha=2.0, prior_beta=2.0,
        )
        assert math.isfinite(result)

    def test_handles_extreme_alpha_values(self):
        """Numerical stability — lgamma must not overflow."""
        result = _beta_log_likelihood(
            observed_alpha=1000.0, observed_beta=10.0,
            prior_alpha=2.0, prior_beta=2.0,
        )
        assert math.isfinite(result)

    def test_returns_higher_for_better_fit(self):
        """The log-likelihood ranking should match intuition: a
        prior whose mode matches the observed posterior fits
        better than one that doesn't."""
        observed_alpha, observed_beta = 50.0, 5.0  # high alpha
        # Prior matched to high-alpha observation
        ll_match = _beta_log_likelihood(
            observed_alpha, observed_beta,
            prior_alpha=8.0, prior_beta=2.0,  # also high-alpha leaning
        )
        # Prior mismatched (low-alpha leaning)
        ll_mismatch = _beta_log_likelihood(
            observed_alpha, observed_beta,
            prior_alpha=2.0, prior_beta=8.0,  # low-alpha leaning
        )
        assert ll_match > ll_mismatch


class TestThresholdConstants:

    def test_thresholds_match_spec(self):
        assert REASSIGNMENT_BID_THRESHOLD == 20
        assert REASSIGNMENT_LOG_LIKELIHOOD_RATIO_THRESHOLD == 3.0


class TestArchetypeCoverage:

    def test_extreme_posteriors_reach_distinct_archetypes(self):
        """Pin that high-alpha and low-alpha extreme posteriors
        produce DIFFERENT reassignment targets. Reaching ALL 8
        archetypes from synthetic posteriors isn't structurally
        achievable because A.2's archetype priors cluster around
        similar (α, β) regions — but the ranking direction must
        be sensible: extreme-maximizer posteriors land on
        most-maximizer-tilted archetypes; extreme-satisficer
        posteriors land on most-satisficer-tilted archetypes.
        """
        # Extreme-maximizer posterior (very high α relative to β):
        p_maxim = _profile_with_maximizer(
            archetype="pragmatist",  # away from maximizer
            user_alpha=300.0, user_beta=10.0,
        )
        result_maxim = evaluate_reassignment(p_maxim)
        assert result_maxim is not None
        # Should reassign to a maximizer-tilted archetype (the
        # archetype with the HIGHEST α/(α+β) ratio in the priors).
        priors = ARCHETYPE_MAXIMIZER_PRIORS
        max_archetype = max(
            priors,
            key=lambda a: priors[a].alpha / (priors[a].alpha + priors[a].beta),
        )
        # Allow either the top maximizer or any nearby high-α archetype
        max_ratio = priors[result_maxim].alpha / (
            priors[result_maxim].alpha + priors[result_maxim].beta
        )
        max_top_ratio = priors[max_archetype].alpha / (
            priors[max_archetype].alpha + priors[max_archetype].beta
        )
        assert max_ratio >= 0.55, (
            f"extreme-maximizer posterior reassigned to {result_maxim.value} "
            f"with α/(α+β)={max_ratio:.2f}; expected ratio ≥ 0.55"
        )

        # Extreme-satisficer posterior (very low α relative to β):
        p_satis = _profile_with_maximizer(
            archetype="analyst",  # away from satisficer
            user_alpha=10.0, user_beta=300.0,
        )
        result_satis = evaluate_reassignment(p_satis)
        assert result_satis is not None
        # The two extreme posteriors should land on DIFFERENT archetypes
        # (otherwise the policy structurally collapses to a single
        # target — that would be the bug we're guarding against).
        assert result_satis != result_maxim, (
            f"both extreme posteriors reassigned to "
            f"{result_satis.value}; policy is collapsing"
        )
