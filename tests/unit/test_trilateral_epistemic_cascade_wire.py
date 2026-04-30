"""Pin the trilateral_epistemic cascade wire.

Audit §6 follow-up. trilateral_epistemic_value() existed in
adam/intelligence/trilateral_epistemic.py but had NO caller. The new
``apply_trilateral_epistemic_bonus`` adapter applies it as a
bounded multiplicative bonus on cascade mechanism_scores, completing
the trilateral information-value picture (buyer × page-mechanism ×
buyer-page) that the cascade's existing single-source IV bidding
can't capture.

These tests pin the adapter's contract:
    * Empty inputs → no-op
    * Missing graph_cache or get_buyer_profile → no-op
    * Missing buyer profile → no-op
    * BONG posterior None → no-op
    * Page edge dimensions empty → no-op
    * Successful path: each mapped mechanism produces a bounded
      multiplicative bonus capped at the cap (default ±15%)
    * Output ∈ [0, 1] even for extreme inputs
    * Unmapped mechanisms pass through unchanged
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from adam.intelligence.trilateral_epistemic import (
    _TRILATERAL_BONUS_CAP,
    apply_trilateral_epistemic_bonus,
)


# -----------------------------------------------------------------------------
# helpers
# -----------------------------------------------------------------------------


class _FakeBongPosterior:
    pass


class _FakeProfile:
    def __init__(self, has_bong: bool = True):
        self.bong_posterior = _FakeBongPosterior() if has_bong else None


def _cache_with(profile: _FakeProfile | None) -> Any:
    cache = MagicMock()
    cache.get_buyer_profile = MagicMock(return_value=profile)
    return cache


def _baseline_scores() -> Dict[str, float]:
    return {"social_proof": 0.50, "authority": 0.50, "scarcity": 0.50}


def _baseline_page_dims() -> Dict[str, float]:
    return {
        "regulatory_fit": 0.5,
        "construal_fit": 0.5,
        "emotional_resonance": 0.5,
        "social_proof_sensitivity": 0.7,
        "loss_aversion_intensity": 0.6,
    }


def _patched_bong_updater(d: int = 20):
    """Build an updater double whose dimension_names match the canonical
    BONG DEFAULT_DIMENSIONS set, with a non-trivial covariance."""
    from adam.intelligence.bong import DEFAULT_DIMENSIONS

    updater = MagicMock()
    updater.prior_eta = np.zeros(d)  # initialized
    updater.dimension_names = list(DEFAULT_DIMENSIONS)[:d]
    # Diagonal covariance with moderate uncertainty on every dim
    cov = np.eye(d) * 0.05
    updater.get_covariance = MagicMock(return_value=cov)
    return updater


# -----------------------------------------------------------------------------
# soft-fail / no-op paths
# -----------------------------------------------------------------------------


def test_empty_scores_returns_unchanged():
    out = apply_trilateral_epistemic_bonus(
        mechanism_scores={}, buyer_id="u",
        page_edge_dimensions=_baseline_page_dims(),
        graph_cache=_cache_with(_FakeProfile()),
    )
    assert out == {}


def test_empty_buyer_id_returns_unchanged():
    scores = _baseline_scores()
    cache = _cache_with(_FakeProfile())
    out = apply_trilateral_epistemic_bonus(
        mechanism_scores=scores, buyer_id="",
        page_edge_dimensions=_baseline_page_dims(),
        graph_cache=cache,
    )
    assert out == scores
    cache.get_buyer_profile.assert_not_called()


def test_empty_page_dims_returns_unchanged():
    scores = _baseline_scores()
    out = apply_trilateral_epistemic_bonus(
        mechanism_scores=scores, buyer_id="u",
        page_edge_dimensions={},
        graph_cache=_cache_with(_FakeProfile()),
    )
    assert out == scores


def test_missing_graph_cache_returns_unchanged():
    scores = _baseline_scores()
    out = apply_trilateral_epistemic_bonus(
        mechanism_scores=scores, buyer_id="u",
        page_edge_dimensions=_baseline_page_dims(),
        graph_cache=None,
    )
    assert out == scores


def test_missing_get_buyer_profile_returns_unchanged():
    scores = _baseline_scores()
    cache = object()
    out = apply_trilateral_epistemic_bonus(
        mechanism_scores=scores, buyer_id="u",
        page_edge_dimensions=_baseline_page_dims(),
        graph_cache=cache,
    )
    assert out == scores


def test_missing_profile_returns_unchanged():
    scores = _baseline_scores()
    out = apply_trilateral_epistemic_bonus(
        mechanism_scores=scores, buyer_id="u",
        page_edge_dimensions=_baseline_page_dims(),
        graph_cache=_cache_with(None),
    )
    assert out == scores


def test_no_bong_posterior_returns_unchanged():
    scores = _baseline_scores()
    out = apply_trilateral_epistemic_bonus(
        mechanism_scores=scores, buyer_id="u",
        page_edge_dimensions=_baseline_page_dims(),
        graph_cache=_cache_with(_FakeProfile(has_bong=False)),
    )
    assert out == scores


def test_get_buyer_profile_raises_returns_unchanged():
    scores = _baseline_scores()
    cache = MagicMock()
    cache.get_buyer_profile = MagicMock(side_effect=RuntimeError("redis down"))
    out = apply_trilateral_epistemic_bonus(
        mechanism_scores=scores, buyer_id="u",
        page_edge_dimensions=_baseline_page_dims(),
        graph_cache=cache,
    )
    assert out == scores


def test_uninitialized_bong_returns_unchanged():
    """If the BONG updater has prior_eta=None it's not initialized — no-op."""
    scores = _baseline_scores()
    cache = _cache_with(_FakeProfile())

    fake_updater = MagicMock()
    fake_updater.prior_eta = None  # not initialized
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=fake_updater,
    ):
        out = apply_trilateral_epistemic_bonus(
            mechanism_scores=scores, buyer_id="u",
            page_edge_dimensions=_baseline_page_dims(),
            graph_cache=cache,
        )
    assert out == scores


# -----------------------------------------------------------------------------
# success paths
# -----------------------------------------------------------------------------


def test_success_path_applies_bonus_to_mapped_mechanisms():
    """A working BONG + non-empty page → bounded shift on mapped mechanisms."""
    scores = _baseline_scores()
    cache = _cache_with(_FakeProfile())
    fake_updater = _patched_bong_updater()

    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=fake_updater,
    ):
        out = apply_trilateral_epistemic_bonus(
            mechanism_scores=scores, buyer_id="u",
            page_edge_dimensions=_baseline_page_dims(),
            graph_cache=cache,
        )

    # Each mapped mechanism stays in [0, 1]
    for mech_id, base in scores.items():
        v = out[mech_id]
        assert 0.0 <= v <= 1.0
        # And shift is bounded by ±cap
        assert abs(v - base) <= base * _TRILATERAL_BONUS_CAP + 1e-6


def test_unmapped_mechanism_passes_through():
    """A mechanism not in MECHANISM_DIMENSION_MAP is left untouched."""
    fake_mech = "this_mechanism_is_not_in_the_map"
    scores = {"social_proof": 0.5, fake_mech: 0.5}
    cache = _cache_with(_FakeProfile())
    fake_updater = _patched_bong_updater()

    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=fake_updater,
    ):
        out = apply_trilateral_epistemic_bonus(
            mechanism_scores=scores, buyer_id="u",
            page_edge_dimensions=_baseline_page_dims(),
            graph_cache=cache,
        )
    assert out[fake_mech] == 0.5


def test_bonus_capped_at_plus_minus_15_percent():
    """Even with extreme inputs, the per-mech multiplicative bonus is
    capped at ±15% (default _TRILATERAL_BONUS_CAP)."""
    scores = {"social_proof": 0.99}
    cache = _cache_with(_FakeProfile())
    fake_updater = _patched_bong_updater()
    # Extreme covariance (saturates total_epistemic)
    fake_updater.get_covariance = MagicMock(return_value=np.eye(20) * 100.0)

    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=fake_updater,
    ):
        out = apply_trilateral_epistemic_bonus(
            mechanism_scores=scores, buyer_id="u",
            page_edge_dimensions=_baseline_page_dims(),
            graph_cache=cache,
        )
    sp = out["social_proof"]
    assert sp <= 0.99 * (1.0 + _TRILATERAL_BONUS_CAP) + 1e-6
    assert sp <= 1.0
    assert sp >= 0.99 * (1.0 - _TRILATERAL_BONUS_CAP) - 1e-6


def test_returns_new_dict_when_modulating():
    """Successful modulation must NOT mutate the caller's dict in place."""
    scores = _baseline_scores()
    snapshot = dict(scores)
    cache = _cache_with(_FakeProfile())
    fake_updater = _patched_bong_updater()

    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=fake_updater,
    ):
        out = apply_trilateral_epistemic_bonus(
            mechanism_scores=scores, buyer_id="u",
            page_edge_dimensions=_baseline_page_dims(),
            graph_cache=cache,
        )
    # Original dict is untouched
    assert scores == snapshot
    # Output is a different object
    assert out is not scores
