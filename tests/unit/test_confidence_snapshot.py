"""Pin the confidence-snapshot helper — DR Layer 4 producer.

Discipline anchors (B3-LUXY a/b/c/d) for
``adam/intelligence/confidence_snapshot.py``:

    (a) 90% CI = mean ± 1.6448536269514722 · σ where σ is the
        per-mechanism affinity sigma:
            point_estimate = (1/n) · Σ μ_i
            σ²             = (1/n²) · Σ σ_i²
        across the mechanism's primary cohort-side dimensions.

    (b) Boundary anchors pinned by these tests:
          * empty buyer_id / missing graph_cache → empty dict
          * profile.bong_posterior is None       → empty dict
          * mechanism not in MECHANISM_DIMENSION_MAP → empty dict
          * single-dim mechanism — point_estimate = μ; CI half-width = z·σ
          * multi-dim mechanism — point_estimate = mean of dim means;
            variance reduction (1/n²) Σ σ_i²
          * symmetric CI: ci_lower < point_estimate < ci_upper
          * monotonic: doubling per-dim σ doubles CI half-width
          * the helper is purely additive — empty snapshot leaves
            renderer at status="not_available"
          * ci_level=0.90 returns z_{0.95} = 1.6448536269514722 exactly

    (c) calibration_pending=False — closed-form Gaussian quantile;
        formula is canonical, not pilot-tuned.

    (d) Honest tag — cohort_pooled_estimate intentionally NOT in the
        snapshot (BLOCKED on Loop B / Spine #7). Tests verify the
        helper does NOT populate that key.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from adam.intelligence.confidence_snapshot import (
    Z_QUANTILE_95,
    _snapshot_from_bong,
    compute_confidence_snapshot,
)


# -----------------------------------------------------------------------------
# Test fixtures — fake BONG updater + fake buyer profile
# -----------------------------------------------------------------------------


class _FakeBONGUpdater:
    """Minimal duck-typed BONGUpdater for direct unit-test ergonomics.

    The cohort-side dimension map (per_user_posterior_modulation.
    BONG_TO_COHORT_DIM) translates BONG dim names — these fakes use
    the BONG names so the translation logic exercises in tests.
    """

    def __init__(
        self,
        means_by_bong_dim: Dict[str, float],
        variances_by_bong_dim: Dict[str, float],
    ):
        self.dimension_names = list(means_by_bong_dim.keys())
        self._means = np.array([
            means_by_bong_dim[d] for d in self.dimension_names
        ])
        self._vars = np.array([
            variances_by_bong_dim[d] for d in self.dimension_names
        ])
        self.prior_eta = np.zeros_like(self._means)  # signal "initialized"

    def get_mean(self, _individual: Any) -> np.ndarray:
        return self._means

    def get_per_dimension_variance(self, _individual: Any) -> np.ndarray:
        return self._vars


class _FakeProfile:
    def __init__(self, bong_posterior: Any = MagicMock()):
        self.bong_posterior = bong_posterior


def _cache_with(profile: Optional[_FakeProfile]) -> Any:
    cache = MagicMock()
    cache.get_buyer_profile = MagicMock(return_value=profile)
    return cache


# -----------------------------------------------------------------------------
# (b) Empty / missing input → empty snapshot
# -----------------------------------------------------------------------------


def test_empty_buyer_id_returns_empty():
    cache = _cache_with(_FakeProfile())
    snap = compute_confidence_snapshot(
        buyer_id="",
        graph_cache=cache,
        chosen_mechanism="social_proof",
    )
    assert snap == {}


def test_none_graph_cache_returns_empty():
    snap = compute_confidence_snapshot(
        buyer_id="user-1",
        graph_cache=None,
        chosen_mechanism="social_proof",
    )
    assert snap == {}


def test_empty_chosen_mechanism_returns_empty():
    cache = _cache_with(_FakeProfile())
    snap = compute_confidence_snapshot(
        buyer_id="user-1",
        graph_cache=cache,
        chosen_mechanism="",
    )
    assert snap == {}


def test_unknown_mechanism_returns_empty():
    """Mechanism outside MECHANISM_DIMENSION_MAP → empty dict.

    Renderer correctly falls back to status="not_available" — contract.
    """
    cache = _cache_with(_FakeProfile())
    snap = compute_confidence_snapshot(
        buyer_id="user-1",
        graph_cache=cache,
        chosen_mechanism="not_a_real_mechanism",
    )
    assert snap == {}


def test_cache_without_get_buyer_profile_returns_empty():
    cache = MagicMock(spec=[])  # spec=[] removes default auto-attrs
    snap = compute_confidence_snapshot(
        buyer_id="user-1",
        graph_cache=cache,
        chosen_mechanism="social_proof",
    )
    assert snap == {}


def test_get_buyer_profile_raises_returns_empty():
    cache = MagicMock()
    cache.get_buyer_profile.side_effect = RuntimeError("graph_cache offline")
    snap = compute_confidence_snapshot(
        buyer_id="user-1",
        graph_cache=cache,
        chosen_mechanism="social_proof",
    )
    assert snap == {}


def test_none_profile_returns_empty():
    cache = _cache_with(None)
    snap = compute_confidence_snapshot(
        buyer_id="user-1",
        graph_cache=cache,
        chosen_mechanism="social_proof",
    )
    assert snap == {}


def test_profile_without_bong_posterior_returns_empty():
    profile = _FakeProfile(bong_posterior=None)
    cache = _cache_with(profile)
    snap = compute_confidence_snapshot(
        buyer_id="user-1",
        graph_cache=cache,
        chosen_mechanism="social_proof",
    )
    assert snap == {}


# -----------------------------------------------------------------------------
# (a) Canonical CI formula — single-dimension mechanism
# -----------------------------------------------------------------------------


def test_single_dim_mechanism_point_estimate_equals_mean():
    """authority maps to ['persuasion_susceptibility', 'information_seeking'].

    Use a single-dim case for cleanest verification: the 'storytelling'
    mechanism maps to ['narrative_transport'] alone.
    """
    means = {"narrative_transport": 0.72}
    vars_ = {"narrative_transport": 0.04}  # σ = 0.2

    fake_updater = _FakeBONGUpdater(means, vars_)
    snap = _snapshot_from_bong(
        bong_posterior=MagicMock(),
        primary_dims=["narrative_transport"],
        ci_level=0.90,
    )

    # Patch the updater singleton inline:
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=fake_updater,
    ):
        snap = _snapshot_from_bong(
            bong_posterior=MagicMock(),
            primary_dims=["narrative_transport"],
            ci_level=0.90,
        )

    assert snap["point_estimate"] == pytest.approx(0.72)

    sigma = math.sqrt(0.04)
    expected_half = Z_QUANTILE_95 * sigma
    assert snap["ci_lower_90"] == pytest.approx(0.72 - expected_half)
    assert snap["ci_upper_90"] == pytest.approx(0.72 + expected_half)


def test_canonical_ci_half_width_matches_z095_times_sigma():
    """ci_upper - ci_lower = 2 · z_{0.95} · σ."""
    means = {"narrative_transport": 0.50}
    vars_ = {"narrative_transport": 0.09}  # σ = 0.3

    fake_updater = _FakeBONGUpdater(means, vars_)
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=fake_updater,
    ):
        snap = _snapshot_from_bong(
            bong_posterior=MagicMock(),
            primary_dims=["narrative_transport"],
            ci_level=0.90,
        )

    width = snap["ci_upper_90"] - snap["ci_lower_90"]
    assert width == pytest.approx(2 * Z_QUANTILE_95 * math.sqrt(0.09))


def test_z_quantile_95_constant_matches_scipy():
    """The pinned z-quantile equals scipy.stats.norm.ppf(0.95) when present."""
    try:
        from scipy.stats import norm  # type: ignore
    except Exception:
        pytest.skip("scipy not available — cannot verify constant.")
    assert Z_QUANTILE_95 == pytest.approx(float(norm.ppf(0.95)), rel=1e-9)


# -----------------------------------------------------------------------------
# (a) Multi-dimension mechanism — affinity-mean reduction
# -----------------------------------------------------------------------------


def test_multi_dim_mechanism_uses_affinity_mean():
    """temporal_construal maps to ['construal_fit', 'temporal_discounting'].

    point_estimate = (μ_1 + μ_2) / 2.
    """
    # BONG_TO_COHORT_DIM translates "construal_fit_score" → "construal_fit".
    means = {
        "construal_fit_score": 0.60,
        "temporal_discounting": 0.40,
        # plus an irrelevant dim that should be filtered out
        "regulatory_fit_score": 0.99,
    }
    vars_ = {
        "construal_fit_score": 0.04,
        "temporal_discounting": 0.04,
        "regulatory_fit_score": 0.01,
    }

    fake_updater = _FakeBONGUpdater(means, vars_)
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=fake_updater,
    ):
        snap = _snapshot_from_bong(
            bong_posterior=MagicMock(),
            primary_dims=["construal_fit", "temporal_discounting"],
            ci_level=0.90,
        )

    assert snap["point_estimate"] == pytest.approx((0.60 + 0.40) / 2)


def test_multi_dim_variance_reduction_under_independence():
    """σ² over n dims = (1/n²) · Σ σ_i² (variance of mean assumption)."""
    means = {"construal_fit_score": 0.50, "temporal_discounting": 0.50}
    vars_ = {"construal_fit_score": 0.04, "temporal_discounting": 0.04}

    fake_updater = _FakeBONGUpdater(means, vars_)
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=fake_updater,
    ):
        snap = _snapshot_from_bong(
            bong_posterior=MagicMock(),
            primary_dims=["construal_fit", "temporal_discounting"],
            ci_level=0.90,
        )

    expected_var = (0.04 + 0.04) / 4  # (1/n²) Σ σ_i²; n=2
    expected_half = Z_QUANTILE_95 * math.sqrt(expected_var)
    width = snap["ci_upper_90"] - snap["ci_lower_90"]
    assert width == pytest.approx(2 * expected_half)


def test_ci_strictly_brackets_point_estimate():
    means = {"narrative_transport": 0.30}
    vars_ = {"narrative_transport": 0.01}

    fake_updater = _FakeBONGUpdater(means, vars_)
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=fake_updater,
    ):
        snap = _snapshot_from_bong(
            bong_posterior=MagicMock(),
            primary_dims=["narrative_transport"],
            ci_level=0.90,
        )

    assert snap["ci_lower_90"] < snap["point_estimate"] < snap["ci_upper_90"]


def test_doubling_sigma_doubles_ci_half_width():
    """σ' = 2·σ ⇒ ci_half' = 2 · ci_half. Linearity of the formula."""
    fake_updater_a = _FakeBONGUpdater(
        {"narrative_transport": 0.50},
        {"narrative_transport": 0.04},  # σ = 0.2
    )
    fake_updater_b = _FakeBONGUpdater(
        {"narrative_transport": 0.50},
        {"narrative_transport": 0.16},  # σ = 0.4 (doubled)
    )

    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=fake_updater_a,
    ):
        snap_a = _snapshot_from_bong(
            bong_posterior=MagicMock(),
            primary_dims=["narrative_transport"],
            ci_level=0.90,
        )
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=fake_updater_b,
    ):
        snap_b = _snapshot_from_bong(
            bong_posterior=MagicMock(),
            primary_dims=["narrative_transport"],
            ci_level=0.90,
        )

    half_a = snap_a["ci_upper_90"] - snap_a["point_estimate"]
    half_b = snap_b["ci_upper_90"] - snap_b["point_estimate"]
    assert half_b == pytest.approx(2 * half_a)


# -----------------------------------------------------------------------------
# (b) Updater not initialized / no overlapping dims
# -----------------------------------------------------------------------------


def test_uninitialized_updater_returns_empty():
    """prior_eta is None until initialize_default / from_file runs."""
    fake_updater = _FakeBONGUpdater(
        {"narrative_transport": 0.5},
        {"narrative_transport": 0.04},
    )
    fake_updater.prior_eta = None

    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=fake_updater,
    ):
        snap = _snapshot_from_bong(
            bong_posterior=MagicMock(),
            primary_dims=["narrative_transport"],
            ci_level=0.90,
        )
    assert snap == {}


def test_no_overlapping_dims_returns_empty():
    """BONG dim vocabulary disjoint from mechanism's primary_dims."""
    fake_updater = _FakeBONGUpdater(
        {"some_unrelated_dim": 0.5},
        {"some_unrelated_dim": 0.04},
    )
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=fake_updater,
    ):
        snap = _snapshot_from_bong(
            bong_posterior=MagicMock(),
            primary_dims=["narrative_transport"],
            ci_level=0.90,
        )
    assert snap == {}


# -----------------------------------------------------------------------------
# (d) Honest tag — cohort_pooled_estimate intentionally absent
# -----------------------------------------------------------------------------


def test_snapshot_does_not_populate_cohort_pooled_estimate():
    """Spine #7 cohort discovery is BLOCKED on Loop B; no cohort key."""
    fake_updater = _FakeBONGUpdater(
        {"narrative_transport": 0.5},
        {"narrative_transport": 0.04},
    )
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=fake_updater,
    ):
        snap = _snapshot_from_bong(
            bong_posterior=MagicMock(),
            primary_dims=["narrative_transport"],
            ci_level=0.90,
        )

    assert "cohort_pooled_estimate" not in snap


def test_snapshot_keys_are_renderer_compatible():
    """Renderer (defensive_reasoning_renderer._render_confidence) reads
    'ci_lower_90' / 'ci_upper_90' / 'point_estimate' literal keys."""
    fake_updater = _FakeBONGUpdater(
        {"narrative_transport": 0.5},
        {"narrative_transport": 0.04},
    )
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=fake_updater,
    ):
        snap = _snapshot_from_bong(
            bong_posterior=MagicMock(),
            primary_dims=["narrative_transport"],
            ci_level=0.90,
        )
    assert set(snap.keys()) == {"point_estimate", "ci_lower_90", "ci_upper_90"}


# -----------------------------------------------------------------------------
# Public function — full integration with cache + profile
# -----------------------------------------------------------------------------


def test_public_function_integrates_cache_to_snapshot():
    """End-to-end: graph_cache.get_buyer_profile → bong_posterior →
    snapshot keys."""
    profile = _FakeProfile(bong_posterior=MagicMock())
    cache = _cache_with(profile)

    fake_updater = _FakeBONGUpdater(
        {
            "regulatory_fit_score": 0.80,  # → cohort dim 'regulatory_fit'
            "narrative_transport": 0.99,   # not in regulatory_focus map
        },
        {
            "regulatory_fit_score": 0.04,
            "narrative_transport": 0.04,
        },
    )
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=fake_updater,
    ):
        snap = compute_confidence_snapshot(
            buyer_id="user-1",
            graph_cache=cache,
            chosen_mechanism="regulatory_focus",  # → ['regulatory_fit']
        )

    assert snap["point_estimate"] == pytest.approx(0.80)


def test_public_function_min_var_floor_prevents_zero_width():
    """Degenerate per-dim variance still produces a non-zero (tiny) CI
    rather than a degenerate zero-width interval."""
    fake_updater = _FakeBONGUpdater(
        {"narrative_transport": 0.5},
        {"narrative_transport": 0.0},  # variance underflow
    )
    with patch(
        "adam.intelligence.bong.get_bong_updater",
        return_value=fake_updater,
    ):
        snap = _snapshot_from_bong(
            bong_posterior=MagicMock(),
            primary_dims=["narrative_transport"],
            ci_level=0.90,
        )
    # ci width is tiny but strictly positive.
    width = snap["ci_upper_90"] - snap["ci_lower_90"]
    assert 0.0 < width < 1e-3
