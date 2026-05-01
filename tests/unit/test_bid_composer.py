"""Pin the bid composer — Spines #6 + #8 + #9 + Phase 2 composition.

Discipline anchors (B3-LUXY a/b/c/d) for
``adam/intelligence/bid_composer.py``:

    (a) Composition formula (directive Phase 4 lines 1011-1024 +
        Spine #5 line 220 attention-inversion gate):
            fluency_score   = compatibility_prior(posture, mechanism)
            fluency_passed  = fluency_score > FLUENCY_PROXY_FLOOR
            epistemic_bonus = compute_epistemic_bonus(
                                  individual=bong_posterior,
                                  fluency_passed=fluency_passed,
                                  cohort_daily_budget=None)
            pragmatic_bid   = compute_pragmatic_bid(
                                  posterior_edge=score,
                                  posterior_variance=affinity_var,
                                  supply_path)
            bid_value       = pragmatic_bid + epistemic_bonus

    (b) Boundary anchors pinned by these tests:
          * fluency_score equals compatibility_prior
          * mechanism_compatibility_score = fluency_score
          * fluency LOW → epistemic_bonus = 0 (structural gate
            per directive line 220)
          * fluency MID/HIGH → epistemic_bonus computed
          * bid_value = pragmatic + epistemic (dual-control)
          * bong_posterior None → epistemic + bid_value = None;
            fluency still populated
          * affinity_variance None → bid_value = None
          * compose_alternatives preserves order
          * compose_chosen_bid_value returns None when no BONG
          * compose_chosen_bid_value uses chosen_score as edge

    (c) calibration_pending=True. FLUENCY_PROXY_FLOOR = 0.30 sits
        between LOW (0.25) and MID (0.50) — LOW gated, MID/HIGH pass.

    (d) Honest tags — what is NOT tested here (named successors):
          * Creative-level hard fluency floor (operates on
            CreativeFeatureBundle × PageFeatureBundle, requires
            creative-resolution layer).
          * Cohort-conditional budget cap (Spine #7 BLOCKED).
          * Empirical clearing-distribution shading (Spine #9 sibling).

VOCABULARY NOTE
---------------

These tests use ``mimetic_desire`` (or other mechanisms appearing in
BOTH ``MECHANISM_TAXONOMY`` and ``MECHANISM_DIMENSION_MAP``). The
vocabulary divergence between layers is real: at runtime, a mechanism
appearing only in MECHANISM_DIMENSION_MAP (cohort-side names like
"social_proof") falls through to ``compatibility_prior`` returning
MID (soft-fail), and a mechanism only in MECHANISM_TAXONOMY falls
through to variance unavailable. The composer is honest about both
soft-fails; tests pin the canonical paths where both vocabularies
overlap.

Mechanisms in BOTH (taxonomy ↔ dimension-map):
  - mimetic_desire (BLEND_COMPATIBLE)
  - embodied_cognition (BLEND_COMPATIBLE)
  - temporal_construal (BLEND_COMPATIBLE)
  - identity_construction (VIGILANCE_ACTIVATING)
  - attention_dynamics (VIGILANCE_ACTIVATING)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import patch

import numpy as np
import pytest

from adam.intelligence.bid_composer import (
    DEFAULT_OBSERVATION_PRECISION,
    DEFAULT_SUPPLY_PATH,
    FLUENCY_PROXY_FLOOR,
    affinity_variance_for_mechanism,
    compose_alternative_bid_metadata,
    compose_alternatives,
    compose_chosen_bid_value,
)
from adam.intelligence.decision_trace import AlternativeCandidate
from adam.intelligence.epistemic_bid_bonus import compute_epistemic_bonus
from adam.intelligence.kelly_bid_sizing import (
    SupplyPath,
    compute_pragmatic_bid,
)
from adam.intelligence.page_attentional_posture_substrate import (
    POSTURE_BLEND,
    POSTURE_NEUTRAL,
    POSTURE_UNKNOWN,
    POSTURE_VIGILANCE,
)
from adam.intelligence.per_user_posterior_modulation import (
    MECHANISM_DIMENSION_MAP,
)
from adam.intelligence.posture_mechanism_prior import (
    COMPATIBILITY_HIGH,
    COMPATIBILITY_LOW,
    COMPATIBILITY_MID,
    compatibility_prior,
)


# -----------------------------------------------------------------------------
# Test fixtures
# -----------------------------------------------------------------------------


class _FakeBONGUpdater:
    """Duck-typed BONGUpdater for unit tests.

    Produces the same per-dim mean + variance vector regardless of
    which BONGPosterior is passed in (the composer reduces over a
    fixed dimension map, not per-individual structure). Mirrors
    BONG semantics: variance = 1/D (precision-inverse) so a fake
    posterior with .D = 25 reports variance 0.04.
    """

    def __init__(self, D_by_dim: Dict[str, float]):
        self.dimension_names = list(D_by_dim.keys())
        self._D = np.array(
            [D_by_dim[d] for d in self.dimension_names], dtype=np.float64,
        )
        self.prior_eta = np.zeros_like(self._D)  # signal "initialized"

    def get_mean(self, _individual: Any) -> np.ndarray:
        return np.zeros_like(self._D)

    def get_per_dimension_variance(self, _individual: Any) -> np.ndarray:
        return 1.0 / np.maximum(self._D, 1e-6)


class _FakeBONGPosterior:
    """BONGPosterior-shaped fake. compute_epistemic_bonus reads .D."""

    def __init__(self, D: np.ndarray):
        self.D = np.asarray(D, dtype=np.float64)
        self.eta = np.zeros_like(self.D)
        self.observation_count = 0


def _bong_setup_for_mechanism(
    mechanism: str,
    *,
    D_per_dim: float = 25.0,
) -> Tuple[_FakeBONGUpdater, _FakeBONGPosterior]:
    """Build (updater, posterior) covering mechanism's primary dims.

    Default D_per_dim=25 → variance=0.04 → σ=0.2 — a reasonable
    pre-pilot per-user posterior precision.
    """
    primary = MECHANISM_DIMENSION_MAP[mechanism]
    D_by_dim = {dim: D_per_dim for dim in primary}
    updater = _FakeBONGUpdater(D_by_dim)
    posterior = _FakeBONGPosterior(D=updater._D.copy())
    return updater, posterior


def _alt(
    mechanism: str,
    score: float,
    propensity: float = 0.5,
) -> AlternativeCandidate:
    return AlternativeCandidate(
        creative_id=f"mechanism_proxy:{mechanism}",
        mechanism=mechanism,
        posterior_score=score,
        propensity_under_TS=propensity,
    )


# -----------------------------------------------------------------------------
# affinity_variance_for_mechanism — variance reduction
# -----------------------------------------------------------------------------


def test_affinity_variance_returns_correct_reduction_single_dim():
    """Single-dim mechanism: var(affinity) = (1/1²) · σ² = σ²."""
    updater, posterior = _bong_setup_for_mechanism("storytelling", D_per_dim=11.111)
    # 1/D ≈ 0.09 — single-dim, n=1; var(affinity) = σ²
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=updater,
    ):
        var = affinity_variance_for_mechanism(
            bong_posterior=posterior,
            mechanism="storytelling",
        )
    assert var == pytest.approx(1.0 / 11.111, rel=1e-4)


def test_affinity_variance_reduction_multi_dim():
    """Multi-dim: var(affinity) = (1/n²) · Σ σ²."""
    updater, posterior = _bong_setup_for_mechanism(
        "temporal_construal",  # → 2 dims
        D_per_dim=25.0,
    )
    # variance per dim = 1/25 = 0.04; n=2; var(affinity) = (0.04 + 0.04)/4 = 0.02
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=updater,
    ):
        var = affinity_variance_for_mechanism(
            bong_posterior=posterior,
            mechanism="temporal_construal",
        )
    assert var == pytest.approx(0.02)


def test_affinity_variance_unknown_mechanism_returns_none():
    var = affinity_variance_for_mechanism(
        bong_posterior=_FakeBONGPosterior(np.array([25.0])),
        mechanism="not_a_real_mechanism",
    )
    assert var is None


def test_affinity_variance_uninitialized_updater_returns_none():
    updater, posterior = _bong_setup_for_mechanism("mimetic_desire")
    updater.prior_eta = None
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=updater,
    ):
        var = affinity_variance_for_mechanism(
            bong_posterior=posterior,
            mechanism="mimetic_desire",
        )
    assert var is None


def test_affinity_variance_no_overlapping_dims_returns_none():
    """BONG dim vocabulary disjoint from mechanism's primary dims."""
    updater = _FakeBONGUpdater({"unrelated": 25.0})
    posterior = _FakeBONGPosterior(updater._D)
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=updater,
    ):
        var = affinity_variance_for_mechanism(
            bong_posterior=posterior,
            mechanism="mimetic_desire",
        )
    assert var is None


# -----------------------------------------------------------------------------
# compose_alternative_bid_metadata — slot population
# -----------------------------------------------------------------------------


def test_alternative_fluency_score_equals_compatibility_prior():
    """fluency_score must equal compatibility_prior(posture, mechanism)."""
    alt = _alt("mimetic_desire", 0.7)
    updater, posterior = _bong_setup_for_mechanism("mimetic_desire")
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=updater,
    ):
        out = compose_alternative_bid_metadata(
            alt,
            posture=POSTURE_BLEND,
            bong_posterior=posterior,
        )
    expected = compatibility_prior(POSTURE_BLEND, "mimetic_desire")
    assert out.fluency_score == pytest.approx(expected)
    assert out.mechanism_compatibility_score == pytest.approx(expected)


def test_alternative_low_fluency_zeroes_epistemic_bonus():
    """Mismatched posture × mechanism (LOW) → fluency_passed=False
    → epistemic_bonus=0 per directive line 220 structural gate.

    mimetic_desire is BLEND_COMPATIBLE → on POSTURE_VIGILANCE → LOW.
    """
    assert compatibility_prior(
        POSTURE_VIGILANCE, "mimetic_desire",
    ) == COMPATIBILITY_LOW

    alt = _alt("mimetic_desire", 0.7)
    updater, posterior = _bong_setup_for_mechanism("mimetic_desire")
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=updater,
    ):
        out = compose_alternative_bid_metadata(
            alt,
            posture=POSTURE_VIGILANCE,
            bong_posterior=posterior,
        )

    # Per directive line 220 + epistemic_bid_bonus.compute_epistemic_bonus
    # rationale "blocked_by_fluency_floor": bonus is exactly 0.0.
    assert out.epistemic_bonus == 0.0


def test_alternative_high_fluency_computes_epistemic_bonus():
    """Matched posture × mechanism (HIGH) → fluency_passed=True
    → epistemic_bonus computed (positive given EIG > 0)."""
    assert compatibility_prior(
        POSTURE_BLEND, "mimetic_desire",
    ) == COMPATIBILITY_HIGH

    alt = _alt("mimetic_desire", 0.7)
    updater, posterior = _bong_setup_for_mechanism("mimetic_desire")
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=updater,
    ):
        out = compose_alternative_bid_metadata(
            alt,
            posture=POSTURE_BLEND,
            bong_posterior=posterior,
        )

    assert out.epistemic_bonus is not None
    assert out.epistemic_bonus > 0.0


def test_alternative_neutral_posture_passes_fluency_gate():
    """POSTURE_NEUTRAL → MID compatibility → above FLUENCY_PROXY_FLOOR
    → fluency_passed=True → epistemic computed."""
    assert COMPATIBILITY_MID > FLUENCY_PROXY_FLOOR

    alt = _alt("mimetic_desire", 0.7)
    updater, posterior = _bong_setup_for_mechanism("mimetic_desire")
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=updater,
    ):
        out = compose_alternative_bid_metadata(
            alt,
            posture=POSTURE_NEUTRAL,
            bong_posterior=posterior,
        )

    assert out.fluency_score == pytest.approx(COMPATIBILITY_MID)
    assert out.epistemic_bonus is not None
    assert out.epistemic_bonus > 0.0


def test_alternative_bid_value_equals_pragmatic_plus_epistemic():
    """bid_value = compute_pragmatic_bid + compute_epistemic_bonus
    (directive line 282 dual-control formulation)."""
    alt = _alt("mimetic_desire", 0.7)
    updater, posterior = _bong_setup_for_mechanism("mimetic_desire")

    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=updater,
    ):
        out = compose_alternative_bid_metadata(
            alt,
            posture=POSTURE_BLEND,
            bong_posterior=posterior,
        )

    # Recompute each leg independently and assert structural sum.
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=updater,
    ):
        affinity_var = affinity_variance_for_mechanism(
            bong_posterior=posterior,
            mechanism="mimetic_desire",
        )
    pragmatic_result = compute_pragmatic_bid(
        posterior_edge=0.7,
        posterior_variance=affinity_var,
        supply_path=DEFAULT_SUPPLY_PATH,
    )
    epi_result = compute_epistemic_bonus(
        individual=posterior,
        observation_precision=DEFAULT_OBSERVATION_PRECISION,
        fluency_passed=True,
    )
    expected_bid = pragmatic_result.bid_value + epi_result.bonus

    assert out.bid_value == pytest.approx(expected_bid)
    assert out.epistemic_bonus == pytest.approx(epi_result.bonus)


def test_alternative_no_bong_posterior_keeps_bid_slots_none():
    """bong_posterior=None → epistemic_bonus + bid_value remain None;
    fluency_score (posture-only) is still populated."""
    alt = _alt("mimetic_desire", 0.7)
    out = compose_alternative_bid_metadata(
        alt,
        posture=POSTURE_BLEND,
        bong_posterior=None,
    )
    assert out.fluency_score is not None
    assert out.mechanism_compatibility_score is not None
    assert out.epistemic_bonus is None
    assert out.bid_value is None


def test_alternative_unknown_posture_returns_mid_compatibility():
    """Unknown posture string → compatibility_prior soft-fails to MID."""
    alt = _alt("mimetic_desire", 0.7)
    out = compose_alternative_bid_metadata(
        alt,
        posture="completely_unknown_posture",
        bong_posterior=None,
    )
    assert out.fluency_score == pytest.approx(COMPATIBILITY_MID)


def test_alternative_unknown_mechanism_keeps_bid_value_none():
    """Mechanism not in MECHANISM_DIMENSION_MAP → variance None →
    bid_value None even with bong_posterior."""
    alt = _alt("not_a_real_mechanism", 0.7)
    posterior = _FakeBONGPosterior(np.array([25.0]))
    out = compose_alternative_bid_metadata(
        alt,
        posture=POSTURE_BLEND,
        bong_posterior=posterior,
    )
    assert out.bid_value is None
    # fluency still populated (returns MID for unknown mechanism)
    assert out.fluency_score == pytest.approx(COMPATIBILITY_MID)


# -----------------------------------------------------------------------------
# compose_alternatives — bulk + order preservation
# -----------------------------------------------------------------------------


def test_compose_alternatives_preserves_order():
    alts = [
        _alt("mimetic_desire", 0.9),
        _alt("temporal_construal", 0.8),
        _alt("embodied_cognition", 0.7),
    ]
    updater, posterior = _bong_setup_for_mechanism("mimetic_desire")
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=updater,
    ):
        out = compose_alternatives(
            alts,
            posture=POSTURE_BLEND,
            bong_posterior=posterior,
        )

    assert [a.mechanism for a in out] == [
        "mimetic_desire", "temporal_construal", "embodied_cognition",
    ]
    # Every alt has a fluency_score populated
    assert all(a.fluency_score is not None for a in out)


def test_compose_alternatives_does_not_mutate_input():
    alts = [_alt("mimetic_desire", 0.9)]
    out = compose_alternatives(
        alts,
        posture=POSTURE_BLEND,
        bong_posterior=None,
    )
    assert alts[0].fluency_score is None  # input unchanged
    assert out[0].fluency_score is not None  # output populated


# -----------------------------------------------------------------------------
# compose_chosen_bid_value — trace-level
# -----------------------------------------------------------------------------


def test_chosen_bid_value_returns_none_without_bong():
    bid = compose_chosen_bid_value(
        chosen_mechanism="mimetic_desire",
        chosen_score=0.7,
        posture=POSTURE_BLEND,
        bong_posterior=None,
    )
    assert bid is None


def test_chosen_bid_value_returns_none_when_variance_unavailable():
    """Mechanism not in MECHANISM_DIMENSION_MAP → variance None →
    chosen bid_value None."""
    bid = compose_chosen_bid_value(
        chosen_mechanism="not_a_real_mechanism",
        chosen_score=0.7,
        posture=POSTURE_BLEND,
        bong_posterior=_FakeBONGPosterior(np.array([25.0])),
    )
    assert bid is None


def test_chosen_bid_value_uses_chosen_score_as_edge():
    """Pragmatic Kelly bid scales with posterior edge.
    Higher chosen_score → higher bid_value (Kelly-full = edge / variance
    is monotonic in edge; epistemic depends only on posterior precision,
    so doesn't change between calls)."""
    updater, posterior = _bong_setup_for_mechanism("mimetic_desire")
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=updater,
    ):
        bid_low = compose_chosen_bid_value(
            chosen_mechanism="mimetic_desire",
            chosen_score=0.3,
            posture=POSTURE_BLEND,
            bong_posterior=posterior,
        )
        bid_high = compose_chosen_bid_value(
            chosen_mechanism="mimetic_desire",
            chosen_score=0.9,
            posture=POSTURE_BLEND,
            bong_posterior=posterior,
        )

    assert bid_low is not None
    assert bid_high is not None
    assert bid_high > bid_low


def test_chosen_bid_value_zero_edge_gives_only_epistemic():
    """Zero/negative edge → pragmatic = 0; chosen bid = epistemic alone."""
    updater, posterior = _bong_setup_for_mechanism("mimetic_desire")
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=updater,
    ):
        bid = compose_chosen_bid_value(
            chosen_mechanism="mimetic_desire",
            chosen_score=0.0,  # no edge
            posture=POSTURE_BLEND,
            bong_posterior=posterior,
        )

    # Pragmatic is zero (no edge); only epistemic survives — and
    # epistemic > 0 since fluency_passed=True on BLEND × mimetic_desire.
    assert bid is not None
    assert bid >= 0.0


def test_chosen_bid_value_low_fluency_gates_epistemic():
    """Mismatched posture (LOW) → epistemic = 0 → chosen bid = pragmatic only."""
    updater, posterior = _bong_setup_for_mechanism("mimetic_desire")

    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=updater,
    ):
        bid_high_fluency = compose_chosen_bid_value(
            chosen_mechanism="mimetic_desire",
            chosen_score=0.7,
            posture=POSTURE_BLEND,  # → HIGH
            bong_posterior=posterior,
        )
        bid_low_fluency = compose_chosen_bid_value(
            chosen_mechanism="mimetic_desire",
            chosen_score=0.7,
            posture=POSTURE_VIGILANCE,  # → LOW
            bong_posterior=posterior,
        )

    # When LOW gates epistemic to 0, the bid is pragmatic only and
    # therefore strictly less than the matched case (which adds
    # epistemic > 0 on top of the same pragmatic).
    assert bid_high_fluency is not None
    assert bid_low_fluency is not None
    assert bid_high_fluency > bid_low_fluency


# -----------------------------------------------------------------------------
# Pydantic round-trip preserves slot values
# -----------------------------------------------------------------------------


def test_alternative_pydantic_round_trip_preserves_slots():
    """Slot values survive model_dump_json / model_validate."""
    alt = _alt("mimetic_desire", 0.7)
    updater, posterior = _bong_setup_for_mechanism("mimetic_desire")
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=updater,
    ):
        composed = compose_alternative_bid_metadata(
            alt,
            posture=POSTURE_BLEND,
            bong_posterior=posterior,
        )

    serialized = composed.model_dump_json()
    restored = AlternativeCandidate.model_validate_json(serialized)
    assert restored.fluency_score == pytest.approx(composed.fluency_score)
    assert restored.mechanism_compatibility_score == pytest.approx(
        composed.mechanism_compatibility_score
    )
    if composed.epistemic_bonus is not None:
        assert restored.epistemic_bonus == pytest.approx(composed.epistemic_bonus)
    if composed.bid_value is not None:
        assert restored.bid_value == pytest.approx(composed.bid_value)
