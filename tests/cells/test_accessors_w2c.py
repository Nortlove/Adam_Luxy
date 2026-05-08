"""W.2c — archetype + maximizer_prior accessor factory tests.

Pin: archetype_accessor coerces profile.archetype string back to
ArchetypeID enum; maximizer_prior_accessor reads
profile.constructs["maximizer_tendency"] and returns (mean, strength);
both accessors fail-soft to S6.2 neutral default at the wrapper seam.
"""
import random
import time
from unittest.mock import MagicMock

import pytest

from adam.cells.accessors import (
    make_archetype_accessor,
    make_maximizer_prior_accessor,
)
from adam.cold_start.models.enums import ArchetypeID
from adam.intelligence.information_value import (
    BuyerUncertaintyProfile,
    ConstructPosterior,
    apply_archetype_maximizer_prior,
)


def _profile_with_archetype(archetype_value: str = "analyst") -> BuyerUncertaintyProfile:
    p = BuyerUncertaintyProfile(buyer_id="u")
    p.archetype = archetype_value
    apply_archetype_maximizer_prior(p)
    return p


# ---------------------------------------------------------------------------
# archetype_accessor
# ---------------------------------------------------------------------------

class TestArchetypeAccessor:

    def test_returns_assigned_archetype(self):
        gc = MagicMock()
        profile = _profile_with_archetype("analyst")
        gc.get_buyer_profile.return_value = profile
        acc = make_archetype_accessor(gc)
        assert acc("u") == ArchetypeID.ANALYST

    def test_returns_pragmatist_when_profile_is_none(self):
        gc = MagicMock()
        gc.get_buyer_profile.return_value = None
        acc = make_archetype_accessor(gc)
        assert acc("u") == ArchetypeID.PRAGMATIST

    def test_returns_pragmatist_when_archetype_is_none(self):
        """Cold-start buyer who hasn't yet hit W.2a's cascade
        injection — profile exists but archetype field is None."""
        gc = MagicMock()
        profile = BuyerUncertaintyProfile(buyer_id="u")
        gc.get_buyer_profile.return_value = profile
        acc = make_archetype_accessor(gc)
        assert acc("u") == ArchetypeID.PRAGMATIST

    def test_fail_soft_on_graph_cache_exception(self):
        gc = MagicMock()
        gc.get_buyer_profile.side_effect = RuntimeError("Neo4j down")
        acc = make_archetype_accessor(gc)
        assert acc("u") == ArchetypeID.PRAGMATIST

    def test_empty_buyer_id_returns_pragmatist(self):
        gc = MagicMock()
        acc = make_archetype_accessor(gc)
        assert acc("") == ArchetypeID.PRAGMATIST
        gc.get_buyer_profile.assert_not_called()

    def test_unknown_archetype_value_falls_back_to_pragmatist(self):
        """Defensive: profile.archetype contains a value that
        doesn't coerce to ArchetypeID enum → PRAGMATIST default."""
        gc = MagicMock()
        profile = BuyerUncertaintyProfile(buyer_id="u")
        profile.archetype = "not_a_real_archetype"
        gc.get_buyer_profile.return_value = profile
        acc = make_archetype_accessor(gc)
        assert acc("u") == ArchetypeID.PRAGMATIST

    @pytest.mark.parametrize("arch", list(ArchetypeID))
    def test_all_8_archetypes_round_trip(self, arch):
        """Each of 8 ArchetypeID values stored as profile.archetype
        string round-trips through the accessor back to the same
        ArchetypeID enum."""
        gc = MagicMock()
        profile = BuyerUncertaintyProfile(buyer_id="u")
        profile.archetype = arch.value
        gc.get_buyer_profile.return_value = profile
        acc = make_archetype_accessor(gc)
        assert acc("u") == arch

    def test_uppercase_archetype_value_coerces(self):
        """Profile.archetype may be stored uppercase (e.g., from
        legacy code paths). Coerced via .lower() → matches enum."""
        gc = MagicMock()
        profile = BuyerUncertaintyProfile(buyer_id="u")
        profile.archetype = "EXPLORER"
        gc.get_buyer_profile.return_value = profile
        acc = make_archetype_accessor(gc)
        assert acc("u") == ArchetypeID.EXPLORER

    def test_determinism_same_buyer_id(self):
        gc = MagicMock()
        gc.get_buyer_profile.return_value = _profile_with_archetype(
            "connector",
        )
        acc = make_archetype_accessor(gc)
        for _ in range(50):
            assert acc("u_stable") == ArchetypeID.CONNECTOR


# ---------------------------------------------------------------------------
# maximizer_prior_accessor
# ---------------------------------------------------------------------------

class TestMaximizerPriorAccessor:

    def test_returns_mean_strength_from_populated_construct(self):
        """Profile with archetype-conditional maximizer prior (via
        W.2b apply_archetype_maximizer_prior) returns the expected
        (mean, strength) tuple."""
        from adam.intelligence.information_value import (
            _ARCHETYPE_DIMENSION_PRIORS,
        )
        gc = MagicMock()
        profile = _profile_with_archetype("analyst")
        gc.get_buyer_profile.return_value = profile
        acc = make_maximizer_prior_accessor(gc)
        mean, strength = acc("u", ArchetypeID.ANALYST)
        # ANALYST A.2 prior: alpha=6.08, beta=3.92 → mean=0.608, strength=10.0
        analyst_alpha, analyst_beta = _ARCHETYPE_DIMENSION_PRIORS[
            "analyst"
        ]["maximizer_tendency"]
        expected_mean = analyst_alpha / (analyst_alpha + analyst_beta)
        expected_strength = analyst_alpha + analyst_beta
        assert mean == pytest.approx(expected_mean)
        assert strength == pytest.approx(expected_strength)

    def test_returns_default_when_profile_is_none(self):
        gc = MagicMock()
        gc.get_buyer_profile.return_value = None
        acc = make_maximizer_prior_accessor(gc)
        assert acc("u", ArchetypeID.PRAGMATIST) == (0.5, 10.0)

    def test_returns_default_when_construct_absent(self):
        """Profile exists but constructs dict doesn't have
        maximizer_tendency entry (legacy data)."""
        gc = MagicMock()
        profile = BuyerUncertaintyProfile(buyer_id="u")
        # Remove the maximizer_tendency construct populated by __post_init__
        if "maximizer_tendency" in profile.constructs:
            del profile.constructs["maximizer_tendency"]
        gc.get_buyer_profile.return_value = profile
        acc = make_maximizer_prior_accessor(gc)
        assert acc("u", ArchetypeID.PRAGMATIST) == (0.5, 10.0)

    def test_returns_default_when_alpha_plus_beta_invalid(self):
        """Defensive: invalid Beta with α + β <= 0 returns default."""
        gc = MagicMock()
        profile = BuyerUncertaintyProfile(buyer_id="u")
        profile.constructs["maximizer_tendency"] = ConstructPosterior(
            alpha=0.0, beta=0.0,
        )
        gc.get_buyer_profile.return_value = profile
        acc = make_maximizer_prior_accessor(gc)
        assert acc("u", ArchetypeID.PRAGMATIST) == (0.5, 10.0)

    def test_fail_soft_on_graph_cache_exception(self):
        gc = MagicMock()
        gc.get_buyer_profile.side_effect = RuntimeError("Neo4j down")
        acc = make_maximizer_prior_accessor(gc)
        assert acc("u", ArchetypeID.PRAGMATIST) == (0.5, 10.0)

    def test_empty_buyer_id_returns_default(self):
        gc = MagicMock()
        acc = make_maximizer_prior_accessor(gc)
        assert acc("", ArchetypeID.PRAGMATIST) == (0.5, 10.0)
        gc.get_buyer_profile.assert_not_called()

    def test_mean_computation_alpha_beta_combo(self):
        """Profile with α=6, β=4 → mean=0.6, strength=10."""
        gc = MagicMock()
        profile = BuyerUncertaintyProfile(buyer_id="u")
        profile.constructs["maximizer_tendency"] = ConstructPosterior(
            alpha=6.0, beta=4.0,
        )
        gc.get_buyer_profile.return_value = profile
        acc = make_maximizer_prior_accessor(gc)
        mean, strength = acc("u", ArchetypeID.PRAGMATIST)
        assert mean == pytest.approx(0.6)
        assert strength == pytest.approx(10.0)

    def test_strength_grows_with_bid_evidence(self):
        """Profile that has accumulated bid evidence: α=10, β=10
        → strength=20 (vs cold-start strength=10)."""
        gc = MagicMock()
        profile = BuyerUncertaintyProfile(buyer_id="u")
        profile.constructs["maximizer_tendency"] = ConstructPosterior(
            alpha=10.0, beta=10.0,
        )
        gc.get_buyer_profile.return_value = profile
        acc = make_maximizer_prior_accessor(gc)
        mean, strength = acc("u", ArchetypeID.PRAGMATIST)
        assert mean == pytest.approx(0.5)
        assert strength == pytest.approx(20.0)

    @pytest.mark.parametrize("arch_key", [
        "achiever", "explorer", "connector", "guardian",
        "analyst", "creator", "nurturer", "pragmatist",
    ])
    def test_all_8_archetypes_a2_priors_round_trip(self, arch_key):
        """For each of 8 archetypes, the apply_archetype_maximizer_prior-
        populated construct returns the A.2-derived (mean, strength)."""
        from adam.intelligence.information_value import (
            _ARCHETYPE_DIMENSION_PRIORS,
        )
        gc = MagicMock()
        profile = _profile_with_archetype(arch_key)
        gc.get_buyer_profile.return_value = profile
        acc = make_maximizer_prior_accessor(gc)
        mean, strength = acc("u", ArchetypeID(arch_key))
        alpha, beta = _ARCHETYPE_DIMENSION_PRIORS[arch_key]["maximizer_tendency"]
        expected_mean = alpha / (alpha + beta)
        expected_strength = alpha + beta
        assert mean == pytest.approx(expected_mean)
        assert strength == pytest.approx(expected_strength)


# ---------------------------------------------------------------------------
# Latency
# ---------------------------------------------------------------------------

class TestLatency:

    def test_archetype_accessor_p99_under_1ms(self):
        gc = MagicMock()
        profile = _profile_with_archetype("analyst")
        gc.get_buyer_profile.return_value = profile
        acc = make_archetype_accessor(gc)

        latencies_us = []
        for _ in range(10000):
            t0 = time.perf_counter()
            acc("u")
            latencies_us.append((time.perf_counter() - t0) * 1_000_000)
        latencies_us.sort()
        p99 = latencies_us[int(len(latencies_us) * 0.99)]
        assert p99 < 1000, (
            f"archetype_accessor p99 {p99:.1f}μs exceeds 1ms target"
        )

    def test_maximizer_prior_accessor_p99_under_1ms(self):
        gc = MagicMock()
        profile = _profile_with_archetype("analyst")
        gc.get_buyer_profile.return_value = profile
        acc = make_maximizer_prior_accessor(gc)

        latencies_us = []
        for _ in range(10000):
            t0 = time.perf_counter()
            acc("u", ArchetypeID.ANALYST)
            latencies_us.append((time.perf_counter() - t0) * 1_000_000)
        latencies_us.sort()
        p99 = latencies_us[int(len(latencies_us) * 0.99)]
        assert p99 < 1000, (
            f"maximizer_prior_accessor p99 {p99:.1f}μs exceeds 1ms target"
        )
