"""W.2b — maximizer_tendency dimension wiring tests.

Pin: UNCERTAINTY_DIMENSIONS extension; A.2 archetype-conditional
priors injected at module load; apply_archetype_maximizer_prior
helper correctness; integration with W.2a archetype assignment;
zero-regression on existing 20 dimensions.
"""
import pytest

from adam.cold_start.models.enums import ArchetypeID
from adam.cold_start.priors.maximizer_tendency import (
    ARCHETYPE_MAXIMIZER_PRIORS,
)
from adam.intelligence.archetype_reassignment import (
    MAXIMIZER_TENDENCY_DIMENSION,
)
from adam.intelligence.information_value import (
    UNCERTAINTY_DIMENSIONS,
    _ARCHETYPE_DIMENSION_PRIORS,
    BuyerUncertaintyProfile,
    ConstructPosterior,
    apply_archetype_maximizer_prior,
)


# ---------------------------------------------------------------------------
# UNCERTAINTY_DIMENSIONS extension
# ---------------------------------------------------------------------------

class TestDimensionListExtension:

    def test_maximizer_tendency_in_dimensions_list(self):
        assert "maximizer_tendency" in UNCERTAINTY_DIMENSIONS

    def test_maximizer_tendency_matches_w2a_constant(self):
        """W.2a's MAXIMIZER_TENDENCY_DIMENSION constant points to
        the same dimension name W.2b adds — pin against drift."""
        assert MAXIMIZER_TENDENCY_DIMENSION == "maximizer_tendency"

    def test_dimension_count_grew_by_exactly_one(self):
        """Pre-W.2b had 20 dimensions; W.2b adds exactly 1."""
        assert len(UNCERTAINTY_DIMENSIONS) == 21


# ---------------------------------------------------------------------------
# A.2 priors injected at module load
# ---------------------------------------------------------------------------

class TestArchetypePriorsInjection:

    @pytest.mark.parametrize("archetype_key", [
        "achiever", "explorer", "connector", "guardian",
        "analyst", "creator", "nurturer", "pragmatist",
    ])
    def test_each_archetype_has_maximizer_tendency_prior(
        self, archetype_key,
    ):
        priors = _ARCHETYPE_DIMENSION_PRIORS[archetype_key]
        assert "maximizer_tendency" in priors, (
            f"archetype {archetype_key!r} missing maximizer_tendency"
        )
        alpha, beta = priors["maximizer_tendency"]
        assert alpha > 0 and beta > 0, (
            f"archetype {archetype_key} maximizer prior has "
            f"non-positive parameter: ({alpha}, {beta})"
        )

    def test_injected_priors_match_a2_derivation(self):
        """The injected priors must match A.2's
        derive_maximizer_beta_priors output exactly."""
        for archetype_id, beta_dist in ARCHETYPE_MAXIMIZER_PRIORS.items():
            arch_key = archetype_id.value.lower()
            injected = _ARCHETYPE_DIMENSION_PRIORS[arch_key]["maximizer_tendency"]
            assert injected[0] == pytest.approx(float(beta_dist.alpha))
            assert injected[1] == pytest.approx(float(beta_dist.beta))

    def test_all_8_archetypes_produce_different_priors(self):
        """Pin A.2's differentiation pattern: 8 archetypes → 8
        distinct (alpha, beta) tuples on maximizer_tendency."""
        unique = set()
        for archetype_key in [
            "achiever", "explorer", "connector", "guardian",
            "analyst", "creator", "nurturer", "pragmatist",
        ]:
            prior = _ARCHETYPE_DIMENSION_PRIORS[archetype_key].get(
                "maximizer_tendency",
            )
            unique.add(prior)
        assert len(unique) == 8, (
            f"only {len(unique)} distinct maximizer priors across 8 "
            f"archetypes — A.2 differentiation pattern broken"
        )


# ---------------------------------------------------------------------------
# apply_archetype_maximizer_prior helper
# ---------------------------------------------------------------------------

class TestApplyArchetypeMaximizerPrior:

    def test_no_archetype_is_noop(self):
        """When profile.archetype is None (cold-start before W.2a),
        helper is a no-op — leaves default Beta(2,2)."""
        p = BuyerUncertaintyProfile(buyer_id="u")
        assert p.archetype is None
        before = (
            p.constructs["maximizer_tendency"].alpha,
            p.constructs["maximizer_tendency"].beta,
        )
        apply_archetype_maximizer_prior(p)
        after = (
            p.constructs["maximizer_tendency"].alpha,
            p.constructs["maximizer_tendency"].beta,
        )
        assert before == after == (2.0, 2.0)

    @pytest.mark.parametrize("archetype_key", [
        "achiever", "explorer", "connector", "guardian",
        "analyst", "creator", "nurturer", "pragmatist",
    ])
    def test_archetype_assigned_overwrites_with_a2_prior(
        self, archetype_key,
    ):
        p = BuyerUncertaintyProfile(buyer_id="u")
        p.archetype = archetype_key
        apply_archetype_maximizer_prior(p)
        expected = _ARCHETYPE_DIMENSION_PRIORS[archetype_key]["maximizer_tendency"]
        assert p.constructs["maximizer_tendency"].alpha == expected[0]
        assert p.constructs["maximizer_tendency"].beta == expected[1]

    def test_idempotent(self):
        p = BuyerUncertaintyProfile(buyer_id="u")
        p.archetype = "explorer"
        apply_archetype_maximizer_prior(p)
        first = (
            p.constructs["maximizer_tendency"].alpha,
            p.constructs["maximizer_tendency"].beta,
        )
        apply_archetype_maximizer_prior(p)
        second = (
            p.constructs["maximizer_tendency"].alpha,
            p.constructs["maximizer_tendency"].beta,
        )
        assert first == second

    def test_case_insensitive_archetype_key(self):
        """archetype field can be uppercase (matches ArchetypeID.value
        case from .upper() in cell_id formatting); helper normalizes."""
        p = BuyerUncertaintyProfile(buyer_id="u")
        p.archetype = "ANALYST"
        apply_archetype_maximizer_prior(p)
        expected = _ARCHETYPE_DIMENSION_PRIORS["analyst"]["maximizer_tendency"]
        assert p.constructs["maximizer_tendency"].alpha == expected[0]

    def test_unknown_archetype_is_noop(self):
        """Defensive: archetype value not in
        _ARCHETYPE_DIMENSION_PRIORS → no-op (don't crash)."""
        p = BuyerUncertaintyProfile(buyer_id="u")
        p.archetype = "not_a_real_archetype"
        before = (
            p.constructs["maximizer_tendency"].alpha,
            p.constructs["maximizer_tendency"].beta,
        )
        apply_archetype_maximizer_prior(p)
        after = (
            p.constructs["maximizer_tendency"].alpha,
            p.constructs["maximizer_tendency"].beta,
        )
        assert before == after == (2.0, 2.0)

    def test_reassignment_replaces_accumulated_posterior(self):
        """On reassignment (archetype changes), the helper REPLACES
        the maximizer_tendency posterior with the new archetype's
        prior — discarding evidence accumulated under the old
        archetype. Acceptable per Q27=(ε) one-shot rarity."""
        p = BuyerUncertaintyProfile(buyer_id="u")
        p.archetype = "explorer"
        apply_archetype_maximizer_prior(p)
        # Simulate accumulated posterior:
        p.constructs["maximizer_tendency"] = ConstructPosterior(
            alpha=20.0, beta=10.0,
        )
        # Reassign:
        p.archetype = "analyst"
        apply_archetype_maximizer_prior(p)
        # The accumulated (20, 10) posterior is gone; new prior in
        # place.
        analyst_expected = _ARCHETYPE_DIMENSION_PRIORS["analyst"]["maximizer_tendency"]
        assert p.constructs["maximizer_tendency"].alpha == analyst_expected[0]
        assert p.constructs["maximizer_tendency"].beta == analyst_expected[1]


# ---------------------------------------------------------------------------
# Integration with W.2a archetype assignment
# ---------------------------------------------------------------------------

class TestIntegrationWithW2A:

    def test_cold_start_flow_then_apply_yields_archetype_specific_prior(self):
        """Simulate W.2a's cold-start path: profile created → mapper
        assigns archetype → helper applies maximizer prior. End
        state has the archetype-specific A.2 prior."""
        from adam.intelligence.cold_start_archetype_mapper import (
            map_cold_start_archetype,
        )
        p = BuyerUncertaintyProfile(buyer_id="u")
        # Cold-start: archetype is None, maximizer is Beta(2,2)
        assert p.archetype is None
        # Mapper assigns archetype
        new_archetype = map_cold_start_archetype(
            device="desktop", hour_of_day=14,
            iab_category="Business and Finance",
        )
        p.archetype = new_archetype.value  # ANALYST per voting
        # W.2b helper applies the archetype-conditional maximizer prior
        apply_archetype_maximizer_prior(p)
        # Maximizer now has the ANALYST-specific A.2-derived prior
        analyst_expected = _ARCHETYPE_DIMENSION_PRIORS[
            new_archetype.value
        ]["maximizer_tendency"]
        assert p.constructs["maximizer_tendency"].alpha == analyst_expected[0]
        assert p.constructs["maximizer_tendency"].beta == analyst_expected[1]

    def test_reassignment_path_refreshes_maximizer_prior(self):
        """Q27=(ε) reassignment switches archetype; W.2b helper is
        called again; maximizer prior switches to new archetype's
        A.2-derived prior."""
        p = BuyerUncertaintyProfile(buyer_id="u")
        p.archetype = "pragmatist"
        apply_archetype_maximizer_prior(p)
        prag_prior = _ARCHETYPE_DIMENSION_PRIORS["pragmatist"]["maximizer_tendency"]
        assert p.constructs["maximizer_tendency"].alpha == prag_prior[0]

        # Simulate reassignment:
        p.archetype = "analyst"
        p.archetype_reassigned = True
        apply_archetype_maximizer_prior(p)
        analyst_prior = _ARCHETYPE_DIMENSION_PRIORS["analyst"]["maximizer_tendency"]
        assert p.constructs["maximizer_tendency"].alpha == analyst_prior[0]


# ---------------------------------------------------------------------------
# Cascade integration block (W.2b extends W.2a's block)
# ---------------------------------------------------------------------------

class TestCascadeIntegration:
    """Pin that the cascade integration block calls
    apply_archetype_maximizer_prior after archetype assignment +
    after reassignment."""

    def _cascade_source(self):
        import inspect
        from adam.api.stackadapt import bilateral_cascade
        return inspect.getsource(bilateral_cascade)

    def test_helper_called_on_cold_start_assignment(self):
        src = self._cascade_source()
        assert "apply_archetype_maximizer_prior" in src

    def test_w2a_block_marker_still_present(self):
        src = self._cascade_source()
        assert (
            "W.2a — ARCHETYPE COLD-START + ONE-SHOT REASSIGNMENT POLICY"
            in src
        )

    def test_helper_called_after_archetype_value_set(self):
        """Pin ordering: W.2b helper call must come AFTER profile.
        archetype assignment so the helper sees the new archetype
        value."""
        src = self._cascade_source()
        # Find the cold-start block's archetype assignment
        idx_arch_set = src.index(
            "_profile.archetype = _new_archetype.value"
        )
        idx_helper = src.index(
            "apply_archetype_maximizer_prior",
            idx_arch_set,  # search starting from the assignment
        )
        assert idx_helper > idx_arch_set


# ---------------------------------------------------------------------------
# Zero-regression on existing dimensions
# ---------------------------------------------------------------------------

class TestZeroRegression:

    def test_pre_w2b_dimensions_still_present(self):
        """The 20 pre-W.2b dimensions must all still be in the list —
        W.2b only adds maximizer_tendency, doesn't remove anything."""
        pre_w2b_dims = {
            "regulatory_fit", "construal_fit", "personality_alignment",
            "emotional_resonance", "value_alignment",
            "evolutionary_motive", "linguistic_style",
            "persuasion_susceptibility", "cognitive_load_tolerance",
            "narrative_transport", "social_proof_sensitivity",
            "loss_aversion_intensity", "temporal_discounting",
            "brand_relationship_depth", "autonomy_reactance",
            "information_seeking", "mimetic_desire",
            "interoceptive_awareness", "cooperative_framing_fit",
            "decision_entropy",
        }
        for dim in pre_w2b_dims:
            assert dim in UNCERTAINTY_DIMENSIONS, (
                f"pre-W.2b dimension {dim!r} missing from list"
            )

    def test_existing_archetype_priors_unchanged(self):
        """W.2b only INJECTS maximizer_tendency entries into
        _ARCHETYPE_DIMENSION_PRIORS — it doesn't modify existing
        per-dimension priors. Pin one specific known value."""
        # Per the FALLBACK dict, achiever's regulatory_fit was (5, 2)
        achiever_priors = _ARCHETYPE_DIMENSION_PRIORS["achiever"]
        assert achiever_priors["regulatory_fit"] == (5, 2)

    def test_buyer_profile_post_init_creates_constructs_for_all_dims(self):
        """Constructs dict gets a default ConstructPosterior for
        every dimension, including the newly-added maximizer_tendency."""
        p = BuyerUncertaintyProfile(buyer_id="u")
        for dim in UNCERTAINTY_DIMENSIONS:
            assert dim in p.constructs
            assert isinstance(p.constructs[dim], ConstructPosterior)

    def test_from_archetype_priors_classmethod_handles_maximizer(self):
        """Pre-existing from_archetype_priors classmethod must work
        with the new maximizer_tendency dimension. For an archetype
        with maximizer entry in priors, the construct gets the
        archetype-specific prior, not the default."""
        p = BuyerUncertaintyProfile.from_archetype_priors(
            archetype="analyst", buyer_id="u",
        )
        analyst_expected = _ARCHETYPE_DIMENSION_PRIORS["analyst"]["maximizer_tendency"]
        assert p.constructs["maximizer_tendency"].alpha == analyst_expected[0]
        assert p.constructs["maximizer_tendency"].beta == analyst_expected[1]


# ---------------------------------------------------------------------------
# Latency
# ---------------------------------------------------------------------------

class TestLatency:

    def test_apply_archetype_maximizer_prior_p99_under_100us(self):
        """Helper is dict lookup + ConstructPosterior() construction;
        should be well under 100μs."""
        import time

        p = BuyerUncertaintyProfile(buyer_id="u")
        p.archetype = "analyst"

        latencies_us = []
        for _ in range(10000):
            t0 = time.perf_counter()
            apply_archetype_maximizer_prior(p)
            latencies_us.append((time.perf_counter() - t0) * 1_000_000)
        latencies_us.sort()
        p99 = latencies_us[int(len(latencies_us) * 0.99)]
        assert p99 < 100, (
            f"apply_archetype_maximizer_prior p99 {p99:.1f}μs exceeds "
            f"100μs target"
        )
