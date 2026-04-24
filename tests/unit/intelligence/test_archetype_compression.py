"""Unit tests for the archetype compression primitive.

Covers the invariants that make the compressor safe to use as a
deterministic, reproducible substrate: fit determinism, refit stability,
posterior shape, MAP/posterior agreement, DP-prior component pruning,
input-validation refusals, state-gating of predict before fit.

Integration with the curated archetype catalog is not tested here — the
compressor is a standalone primitive. Bridge behavior lands with a later
slice and gets its own integration tests.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from adam.intelligence.recommendation_class import (
    ArchetypeCompressionResult,
    ArchetypeCompressor,
    DEFAULT_SEED,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


def _three_cluster_data(n_per_cluster: int = 30, d: int = 6, seed: int = 0) -> np.ndarray:
    """Generate a small, well-separated 3-cluster dataset in d dimensions.

    Components are at +3, 0, -3 along the first feature; other features are
    small noise. Well-separated so the fit is unambiguous across seeds.
    """
    rng = np.random.default_rng(seed)
    offsets = np.array([+3.0, 0.0, -3.0])
    parts = []
    for mu in offsets:
        block = rng.normal(loc=0.0, scale=0.35, size=(n_per_cluster, d))
        block[:, 0] += mu
        parts.append(block)
    return np.vstack(parts)


def _low_rank_data(n: int = 40, d: int = 5) -> np.ndarray:
    """Data with real rank 2 — DP prior should prune toward ~2 components."""
    rng = np.random.default_rng(7)
    latent = rng.normal(size=(n, 2))
    loadings = rng.normal(size=(2, d))
    return latent @ loadings + 0.05 * rng.normal(size=(n, d))


# -----------------------------------------------------------------------------
# Construction validation
# -----------------------------------------------------------------------------


class TestConstruction:
    def test_defaults_accepted(self):
        compressor = ArchetypeCompressor()
        assert compressor.seed == DEFAULT_SEED
        assert compressor.max_components >= 2
        assert compressor.last_result is None

    def test_max_components_below_two_rejected(self):
        with pytest.raises(ValueError, match="max_components"):
            ArchetypeCompressor(max_components=1)

    def test_min_observations_below_two_rejected(self):
        with pytest.raises(ValueError, match="min_observations"):
            ArchetypeCompressor(min_observations=1)

    def test_nonpositive_dirichlet_rejected(self):
        with pytest.raises(ValueError, match="dirichlet_concentration"):
            ArchetypeCompressor(dirichlet_concentration=0.0)
        with pytest.raises(ValueError, match="dirichlet_concentration"):
            ArchetypeCompressor(dirichlet_concentration=-0.1)

    def test_effective_weight_threshold_out_of_range_rejected(self):
        with pytest.raises(ValueError, match="effective_weight_threshold"):
            ArchetypeCompressor(effective_weight_threshold=0.0)
        with pytest.raises(ValueError, match="effective_weight_threshold"):
            ArchetypeCompressor(effective_weight_threshold=1.0)
        with pytest.raises(ValueError, match="effective_weight_threshold"):
            ArchetypeCompressor(effective_weight_threshold=-0.1)

    def test_unknown_covariance_type_rejected(self):
        with pytest.raises(ValueError, match="covariance_type"):
            ArchetypeCompressor(covariance_type="not_a_real_type")

    def test_each_valid_covariance_type_accepted(self):
        for ct in ("spherical", "diag", "tied", "full"):
            ArchetypeCompressor(covariance_type=ct)


# -----------------------------------------------------------------------------
# Fit / result shape
# -----------------------------------------------------------------------------


class TestFitShape:
    def test_fit_returns_frozen_result(self):
        compressor = ArchetypeCompressor()
        result = compressor.fit(_three_cluster_data())
        assert isinstance(result, ArchetypeCompressionResult)
        with pytest.raises(Exception):
            result.component_assignments = []  # type: ignore[misc]

    def test_result_shape_is_self_consistent(self):
        compressor = ArchetypeCompressor()
        X = _three_cluster_data()
        result = compressor.fit(X)
        n, d = X.shape
        assert result.n_observations == n
        assert result.n_features == d
        assert len(result.component_assignments) == n
        assert len(result.component_posteriors) == n
        n_components = len(result.component_weights)
        assert len(result.component_means) == n_components
        for row in result.component_posteriors:
            assert len(row) == n_components

    def test_posteriors_sum_to_one_per_row(self):
        compressor = ArchetypeCompressor()
        result = compressor.fit(_three_cluster_data())
        for row in result.component_posteriors:
            assert math.isclose(sum(row), 1.0, abs_tol=1e-6)

    def test_posteriors_nonnegative(self):
        compressor = ArchetypeCompressor()
        result = compressor.fit(_three_cluster_data())
        for row in result.component_posteriors:
            assert all(v >= 0.0 for v in row)

    def test_assignment_agrees_with_posterior_argmax(self):
        compressor = ArchetypeCompressor()
        result = compressor.fit(_three_cluster_data())
        for i, row in enumerate(result.component_posteriors):
            argmax = max(range(len(row)), key=lambda k: row[k])
            assert result.component_assignments[i] == argmax

    def test_weights_sum_to_one(self):
        compressor = ArchetypeCompressor()
        result = compressor.fit(_three_cluster_data())
        assert math.isclose(sum(result.component_weights), 1.0, abs_tol=1e-6)

    def test_converged_flag_present(self):
        compressor = ArchetypeCompressor()
        result = compressor.fit(_three_cluster_data())
        assert isinstance(result.converged, bool)


# -----------------------------------------------------------------------------
# Determinism
# -----------------------------------------------------------------------------


class TestDeterminism:
    def test_same_data_same_seed_same_fit_hash(self):
        X = _three_cluster_data()
        a = ArchetypeCompressor(seed=12345).fit(X)
        b = ArchetypeCompressor(seed=12345).fit(X)
        assert a.fit_hash == b.fit_hash

    def test_same_data_same_seed_same_assignments(self):
        X = _three_cluster_data()
        a = ArchetypeCompressor(seed=12345).fit(X)
        b = ArchetypeCompressor(seed=12345).fit(X)
        assert a.component_assignments == b.component_assignments

    def test_different_seed_may_differ(self):
        """Different seeds *may* produce different fit hashes. The test
        passes if at least one of several seed pairs differs, which is
        overwhelmingly likely for non-trivial data.
        """
        X = _three_cluster_data()
        base = ArchetypeCompressor(seed=1).fit(X).fit_hash
        any_diff = False
        for s in (2, 3, 4, 5):
            other = ArchetypeCompressor(seed=s).fit(X).fit_hash
            if other != base:
                any_diff = True
                break
        assert any_diff, "expected at least one different-seed fit to differ"

    def test_predict_after_fit_matches_fit_assignments(self):
        X = _three_cluster_data()
        compressor = ArchetypeCompressor()
        result = compressor.fit(X)
        predicted = compressor.predict(X)
        assert predicted == result.component_assignments


# -----------------------------------------------------------------------------
# DP prior auto-pruning
# -----------------------------------------------------------------------------


class TestDPPriorPruning:
    def test_three_well_separated_clusters_use_three_effective_components(self):
        compressor = ArchetypeCompressor(max_components=12, seed=42)
        result = compressor.fit(_three_cluster_data(n_per_cluster=40))
        assert result.effective_components <= 5, (
            f"DP prior should prune toward ~3 for 3-cluster data; "
            f"got {result.effective_components}"
        )
        assert result.effective_components >= 2, (
            f"DP prior dropped too many components; got {result.effective_components}"
        )

    def test_low_rank_data_uses_few_effective_components(self):
        compressor = ArchetypeCompressor(max_components=12, seed=42)
        result = compressor.fit(_low_rank_data())
        assert result.effective_components <= 8


# -----------------------------------------------------------------------------
# Well-separated clusters produce sensible groupings
# -----------------------------------------------------------------------------


class TestClusterRecovery:
    def test_three_clusters_produce_at_least_two_distinct_assignments(self):
        """The compressor must put well-separated clusters into different
        components. Exact component indices are not portable across seeds,
        so we check that at least two distinct assignments appear.
        """
        compressor = ArchetypeCompressor(max_components=12)
        X = _three_cluster_data(n_per_cluster=40)
        result = compressor.fit(X)
        distinct = set(result.component_assignments)
        assert len(distinct) >= 2

    def test_same_cluster_points_group_together_majority(self):
        """Points in the same generated cluster should share their MAP
        component the majority of the time. Tolerant threshold so the
        test doesn't flake on variational-fit boundary points.
        """
        n_per = 40
        X = _three_cluster_data(n_per_cluster=n_per)
        compressor = ArchetypeCompressor(max_components=12)
        result = compressor.fit(X)
        for cluster_idx in range(3):
            start = cluster_idx * n_per
            end = start + n_per
            slice_assignments = result.component_assignments[start:end]
            mode = max(set(slice_assignments), key=slice_assignments.count)
            majority = slice_assignments.count(mode) / n_per
            assert majority >= 0.7, (
                f"cluster {cluster_idx} majority only {majority:.2f}; "
                f"expected >= 0.7"
            )


# -----------------------------------------------------------------------------
# fit_hash behavior
# -----------------------------------------------------------------------------


class TestFitHash:
    def test_fit_hash_is_hex_sha256(self):
        compressor = ArchetypeCompressor()
        result = compressor.fit(_three_cluster_data())
        h = result.fit_hash
        assert len(h) == 64
        int(h, 16)  # raises if not hex

    def test_fit_hash_changes_when_data_changes(self):
        X1 = _three_cluster_data(seed=1)
        X2 = _three_cluster_data(seed=2)
        h1 = ArchetypeCompressor().fit(X1).fit_hash
        h2 = ArchetypeCompressor().fit(X2).fit_hash
        assert h1 != h2


# -----------------------------------------------------------------------------
# Input validation
# -----------------------------------------------------------------------------


class TestInputValidation:
    def test_below_min_observations_rejected(self):
        compressor = ArchetypeCompressor(min_observations=8)
        X = np.random.default_rng(0).normal(size=(5, 3))
        with pytest.raises(ValueError, match="min_observations"):
            compressor.fit(X)

    def test_zero_variance_column_rejected(self):
        compressor = ArchetypeCompressor(min_observations=4)
        X = np.random.default_rng(0).normal(size=(20, 4))
        X[:, 2] = 1.0
        with pytest.raises(ValueError, match="zero-variance"):
            compressor.fit(X)

    def test_non_2d_input_rejected(self):
        compressor = ArchetypeCompressor()
        with pytest.raises(ValueError, match="2-D"):
            compressor.fit(np.ones(10))
        with pytest.raises(ValueError, match="2-D"):
            compressor.fit(np.ones((3, 4, 5)))

    def test_non_finite_values_rejected(self):
        compressor = ArchetypeCompressor(min_observations=4)
        X = np.random.default_rng(0).normal(size=(20, 4))
        X[3, 2] = np.nan
        with pytest.raises(ValueError, match="non-finite"):
            compressor.fit(X)

        X2 = np.random.default_rng(0).normal(size=(20, 4))
        X2[5, 1] = np.inf
        with pytest.raises(ValueError, match="non-finite"):
            compressor.fit(X2)


# -----------------------------------------------------------------------------
# Predict state-gating
# -----------------------------------------------------------------------------


class TestPredictStateGating:
    def test_predict_before_fit_raises(self):
        compressor = ArchetypeCompressor()
        with pytest.raises(RuntimeError, match="fit"):
            compressor.predict(_three_cluster_data())

    def test_predict_proba_before_fit_raises(self):
        compressor = ArchetypeCompressor()
        with pytest.raises(RuntimeError, match="fit"):
            compressor.predict_proba(_three_cluster_data())

    def test_predict_on_new_data_returns_valid_assignments(self):
        compressor = ArchetypeCompressor(max_components=12)
        compressor.fit(_three_cluster_data(seed=1))
        X_new = _three_cluster_data(seed=2)
        predictions = compressor.predict(X_new)
        assert len(predictions) == X_new.shape[0]
        assert all(isinstance(v, int) for v in predictions)

    def test_predict_proba_on_new_data_returns_valid_posteriors(self):
        compressor = ArchetypeCompressor(max_components=12)
        fit_result = compressor.fit(_three_cluster_data(seed=1))
        n_components = len(fit_result.component_weights)
        X_new = _three_cluster_data(seed=2)
        posteriors = compressor.predict_proba(X_new)
        assert len(posteriors) == X_new.shape[0]
        for row in posteriors:
            assert len(row) == n_components
            assert math.isclose(sum(row), 1.0, abs_tol=1e-6)
            assert all(v >= 0.0 for v in row)


# -----------------------------------------------------------------------------
# last_result getter
# -----------------------------------------------------------------------------


class TestLastResult:
    def test_last_result_none_before_fit(self):
        assert ArchetypeCompressor().last_result is None

    def test_last_result_set_after_fit(self):
        compressor = ArchetypeCompressor()
        result = compressor.fit(_three_cluster_data())
        assert compressor.last_result is result

    def test_last_result_updated_on_refit(self):
        compressor = ArchetypeCompressor()
        r1 = compressor.fit(_three_cluster_data(seed=1))
        r2 = compressor.fit(_three_cluster_data(seed=2))
        assert compressor.last_result is r2
        assert r1 is not r2
