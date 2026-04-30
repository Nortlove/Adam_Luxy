"""Pin the per-user N-of-1 posterior modulation primitive.

Discipline anchors (B3-LUXY a/b/c/d) for
``adam/intelligence/per_user_posterior_modulation.py``:

    (a) Empirical-Bayes shrinkage formula — score' = score + w·s·(affinity - score),
        where w = mixing_weight, s = stability ∈ [0,1], affinity = mean of
        user's posterior over the mechanism's primary dimensions.

    (b) Boundary anchors pinned by these tests:
          * cold-start buyer (< MIN_OBSERVATIONS_FOR_MODULATION)  → no shift
          * missing buyer profile / missing graph_cache method     → no shift
          * stability = 0 (no confidence)                          → no shift
          * stability = 1, biased posterior                        → bounded shift
          * mechanism without primary_dims                         → unchanged
          * shrunken scores stay in [0, 1]
          * direction of shift matches direction of (affinity - score)

    (c) calibration_pending — defaults assert the conservative-default
        behavior (mixing_weight=0.30). Pilot-derived recalibration is
        expected to land via mSPRT outcomes.

    (d) honest tag — the mechanism→dimension map is canonical
        (mechanism_activation.py:1585), not learned. These tests pin
        ONLY the modulation behavior; the map itself is substrate.
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from adam.intelligence.per_user_posterior_modulation import (
    MECHANISM_DIMENSION_MAP,
    MIN_OBSERVATIONS_FOR_MODULATION,
    apply_per_user_posterior_modulation,
)


# -----------------------------------------------------------------------------
# helpers
# -----------------------------------------------------------------------------


class _FakeConstructPosterior:
    def __init__(self, mean: float):
        self.mean = mean


class _FakeProfile:
    """Minimal stand-in for BuyerUncertaintyProfile used by graph_cache.

    Only the attributes the modulation primitive reads are populated.
    The legacy-constructs path is exercised when bong_posterior=None.
    """

    def __init__(
        self,
        constructs: Dict[str, float],
        total_interactions: int,
        aggregate_confidence: float,
        bong_posterior: Any = None,
    ):
        self.constructs = {
            dim: _FakeConstructPosterior(mean) for dim, mean in constructs.items()
        }
        self.total_interactions = total_interactions
        self.aggregate_confidence = aggregate_confidence
        self.bong_posterior = bong_posterior


def _cache_with(profile: _FakeProfile | None) -> Any:
    cache = MagicMock()
    cache.get_buyer_profile = MagicMock(return_value=profile)
    return cache


def _baseline_scores() -> Dict[str, float]:
    # Use mechanisms that ALL appear in MECHANISM_DIMENSION_MAP so the
    # tests aren't accidentally exercising the "unknown mechanism" branch.
    return {
        "social_proof": 0.50,
        "authority": 0.50,
        "scarcity": 0.50,
        "regulatory_focus": 0.50,
    }


# -----------------------------------------------------------------------------
# (b) cold-start / missing-data → identity
# -----------------------------------------------------------------------------


def test_cold_start_buyer_returns_unchanged():
    """Below MIN_OBSERVATIONS_FOR_MODULATION the cohort prior IS the answer."""
    profile = _FakeProfile(
        constructs={"social_proof_sensitivity": 0.95},
        total_interactions=MIN_OBSERVATIONS_FOR_MODULATION - 1,
        aggregate_confidence=0.5,
    )
    cache = _cache_with(profile)

    scores = _baseline_scores()
    out = apply_per_user_posterior_modulation(
        mechanism_scores=scores, buyer_id="u_cold", graph_cache=cache,
    )
    assert out == scores


def test_missing_profile_returns_unchanged():
    cache = _cache_with(None)
    scores = _baseline_scores()
    out = apply_per_user_posterior_modulation(
        mechanism_scores=scores, buyer_id="u_unknown", graph_cache=cache,
    )
    assert out == scores


def test_missing_get_buyer_profile_method_returns_unchanged():
    """A graph_cache without get_buyer_profile must not raise."""
    cache = object()  # no get_buyer_profile attribute
    scores = _baseline_scores()
    out = apply_per_user_posterior_modulation(
        mechanism_scores=scores, buyer_id="u_x", graph_cache=cache,
    )
    assert out == scores


def test_empty_buyer_id_returns_unchanged():
    profile = _FakeProfile(
        constructs={"social_proof_sensitivity": 0.95},
        total_interactions=10,
        aggregate_confidence=0.9,
    )
    cache = _cache_with(profile)
    scores = _baseline_scores()
    out = apply_per_user_posterior_modulation(
        mechanism_scores=scores, buyer_id="", graph_cache=cache,
    )
    assert out == scores
    cache.get_buyer_profile.assert_not_called()


def test_zero_stability_returns_unchanged():
    """aggregate_confidence=0 means no per-user evidence weight."""
    profile = _FakeProfile(
        constructs={"social_proof_sensitivity": 0.95, "mimetic_desire": 0.95},
        total_interactions=10,
        aggregate_confidence=0.0,
    )
    cache = _cache_with(profile)
    scores = _baseline_scores()
    out = apply_per_user_posterior_modulation(
        mechanism_scores=scores, buyer_id="u_no_conf", graph_cache=cache,
    )
    assert out == scores


# -----------------------------------------------------------------------------
# (b) high-stability + biased posterior → bounded, directional shift
# -----------------------------------------------------------------------------


def test_high_stability_biased_posterior_shifts_in_correct_direction():
    """User who consistently converts on social_proof dims should see
    social_proof score INCREASE; mechanisms whose primary dims aren't
    represented should be unchanged."""
    # User mean alignment is HIGH on social_proof's primary dims and LOW
    # on scarcity's primary dims.
    profile = _FakeProfile(
        constructs={
            "social_proof_sensitivity": 0.95,
            "mimetic_desire": 0.95,
            "loss_aversion_intensity": 0.10,
            "decision_entropy": 0.10,
        },
        total_interactions=20,
        aggregate_confidence=1.0,  # max stability
    )
    cache = _cache_with(profile)
    scores = {"social_proof": 0.50, "scarcity": 0.50}

    out = apply_per_user_posterior_modulation(
        mechanism_scores=scores, buyer_id="u_warm", graph_cache=cache,
    )

    # Direction: social_proof up (affinity > base), scarcity down.
    assert out["social_proof"] > scores["social_proof"]
    assert out["scarcity"] < scores["scarcity"]

    # Magnitude bounded by stability * mixing_weight = 1.0 * 0.30 = 0.30.
    # social_proof: 0.5 + 0.30·(0.95 - 0.5) = 0.635 (exact)
    assert out["social_proof"] == pytest.approx(0.635, abs=1e-6)
    # scarcity: 0.5 + 0.30·(0.10 - 0.5) = 0.380 (exact)
    assert out["scarcity"] == pytest.approx(0.380, abs=1e-6)


def test_modulated_scores_stay_in_unit_interval():
    """Even with extreme inputs the output must clamp to [0, 1]."""
    profile = _FakeProfile(
        constructs={
            "social_proof_sensitivity": 1.0,
            "mimetic_desire": 1.0,
            "loss_aversion_intensity": 0.0,
            "decision_entropy": 0.0,
        },
        total_interactions=100,
        aggregate_confidence=1.0,
    )
    cache = _cache_with(profile)
    # Push base scores to the edges to test clamping.
    scores = {"social_proof": 0.99, "scarcity": 0.01}

    out = apply_per_user_posterior_modulation(
        mechanism_scores=scores, buyer_id="u_extreme", graph_cache=cache,
        mixing_weight=1.0,  # turn shrinkage all the way up
    )

    for v in out.values():
        assert 0.0 <= v <= 1.0


def test_unknown_mechanism_passes_through():
    """A mechanism not in MECHANISM_DIMENSION_MAP is left unchanged."""
    profile = _FakeProfile(
        constructs={"social_proof_sensitivity": 0.95, "mimetic_desire": 0.95},
        total_interactions=10,
        aggregate_confidence=1.0,
    )
    cache = _cache_with(profile)

    fake_mech = "this_mechanism_is_not_in_the_map"
    assert fake_mech not in MECHANISM_DIMENSION_MAP

    scores = {"social_proof": 0.50, fake_mech: 0.50}
    out = apply_per_user_posterior_modulation(
        mechanism_scores=scores, buyer_id="u_warm", graph_cache=cache,
    )
    assert out[fake_mech] == 0.50  # untouched
    assert out["social_proof"] != 0.50  # touched (sanity)


def test_mechanism_with_no_observed_primary_dims_passes_through():
    """If user_alignment lacks ALL of a mechanism's primary dims,
    that mechanism's score is left untouched."""
    profile = _FakeProfile(
        # Only one totally-unrelated dim populated
        constructs={"unrelated_dim": 0.99},
        total_interactions=10,
        aggregate_confidence=1.0,
    )
    cache = _cache_with(profile)

    scores = {"social_proof": 0.50}
    out = apply_per_user_posterior_modulation(
        mechanism_scores=scores, buyer_id="u_x", graph_cache=cache,
    )
    assert out["social_proof"] == 0.50


# -----------------------------------------------------------------------------
# (b) graph_cache failure modes — soft-fail
# -----------------------------------------------------------------------------


def test_graph_cache_raises_returns_unchanged():
    """Any exception from graph_cache.get_buyer_profile must be swallowed."""
    cache = MagicMock()
    cache.get_buyer_profile = MagicMock(side_effect=RuntimeError("redis down"))

    scores = _baseline_scores()
    out = apply_per_user_posterior_modulation(
        mechanism_scores=scores, buyer_id="u_x", graph_cache=cache,
    )
    assert out == scores


def test_empty_mechanism_scores_returns_unchanged():
    profile = _FakeProfile(
        constructs={"social_proof_sensitivity": 0.95, "mimetic_desire": 0.95},
        total_interactions=10,
        aggregate_confidence=1.0,
    )
    cache = _cache_with(profile)
    out = apply_per_user_posterior_modulation(
        mechanism_scores={}, buyer_id="u_warm", graph_cache=cache,
    )
    assert out == {}


# -----------------------------------------------------------------------------
# (b) shrinkage scales with stability
# -----------------------------------------------------------------------------


def test_partial_stability_partial_shift():
    """At stability=0.5, shift should equal half of the full-stability shift."""
    full_profile = _FakeProfile(
        constructs={"social_proof_sensitivity": 0.95, "mimetic_desire": 0.95},
        total_interactions=10,
        aggregate_confidence=1.0,
    )
    half_profile = _FakeProfile(
        constructs={"social_proof_sensitivity": 0.95, "mimetic_desire": 0.95},
        total_interactions=10,
        aggregate_confidence=0.5,
    )

    full_out = apply_per_user_posterior_modulation(
        mechanism_scores={"social_proof": 0.50},
        buyer_id="u",
        graph_cache=_cache_with(full_profile),
    )
    half_out = apply_per_user_posterior_modulation(
        mechanism_scores={"social_proof": 0.50},
        buyer_id="u",
        graph_cache=_cache_with(half_profile),
    )

    full_delta = full_out["social_proof"] - 0.50
    half_delta = half_out["social_proof"] - 0.50

    # Half-stability delta is exactly half of full-stability delta.
    assert half_delta == pytest.approx(full_delta / 2.0, abs=1e-9)
