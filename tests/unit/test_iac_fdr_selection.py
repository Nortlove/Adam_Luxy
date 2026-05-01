"""Pin Phase 3 BH-style FDR control on δ_iac (directive line 988 + 1055).

Tests pin:
  * Empty moments → empty selection (no exception)
  * fdr_target outside (0, 1] → empty selection (defensive)
  * Strong-signal triples (high |z|) selected
  * Weak-signal triples (low |z|) not selected
  * Pure-null moments produce few selections (FDR-controlled)
  * Selection deterministic + lexicographically sorted
  * BH threshold algorithm correctness on synthetic p-values
  * z_threshold reported correctly (minimum |z| of selected)
  * z_scores_by_triple diagnostic populated for ALL candidates
  * Convenience helper returns same triples as full selection
  * Default constants pinned at A14 anchor
"""

from __future__ import annotations

import math
from typing import List

import numpy as np
import pytest

from adam.intelligence.iac_fdr_selection import (
    DEFAULT_FDR_TARGET,
    IacFDRSelectionResult,
    _bh_threshold,
    select_iac_via_fdr,
    select_pre_specified_for_next_fit,
)
from adam.intelligence.iac_prior import IacPriorMoments


# -----------------------------------------------------------------------------
# Constants pinned (A14 — drift requires explicit calibration update)
# -----------------------------------------------------------------------------


def test_default_fdr_target_pinned():
    assert DEFAULT_FDR_TARGET == 0.10


# -----------------------------------------------------------------------------
# BH threshold algorithm correctness
# -----------------------------------------------------------------------------


def test_bh_threshold_empty():
    assert _bh_threshold([], q=0.10) == 0


def test_bh_threshold_no_rejections_when_all_pvals_high():
    """All p-values above the threshold → zero rejections."""
    pvals = [0.5, 0.6, 0.7, 0.8, 0.9]
    assert _bh_threshold(pvals, q=0.10) == 0


def test_bh_threshold_all_rejections_when_all_pvals_zero():
    """All p-values at zero → all rejected."""
    pvals = [0.0, 0.0, 0.0, 0.0, 0.0]
    assert _bh_threshold(pvals, q=0.10) == 5


def test_bh_threshold_canonical_example():
    """BH 1995 canonical small example.

    With m=5 and q=0.10: thresholds are 0.02, 0.04, 0.06, 0.08, 0.10.
    p-values [0.005, 0.03, 0.07, 0.20, 0.50]:
      i=1: 0.005 ≤ 0.02 ✓ → k=1
      i=2: 0.03  ≤ 0.04 ✓ → k=2
      i=3: 0.07  > 0.06 ✗
      i=4: 0.20  > 0.08 ✗
      i=5: 0.50  > 0.10 ✗
    LARGEST k satisfying = 2.
    """
    pvals = [0.005, 0.03, 0.07, 0.20, 0.50]
    assert _bh_threshold(pvals, q=0.10) == 2


def test_bh_threshold_picks_largest_k_when_inequality_re_satisfies():
    """BH picks the LARGEST k. Even if the inequality fails at some
    middle index then re-satisfies later, BH still uses the largest
    k-where-it-holds (not the first failure).

    With m=10 and q=0.10:
      thresholds = 0.01, 0.02, ..., 0.10
    p-values: [0.005, 0.005, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.09, 0.099]
      i=1: 0.005 ≤ 0.01 ✓
      i=2: 0.005 ≤ 0.02 ✓
      i=3: 0.05  > 0.03 ✗
      ...
      i=9: 0.09  > 0.09 ✗ (strict >)
      i=10: 0.099 ≤ 0.10 ✓ → k=10 (LARGEST satisfying)
    """
    pvals = [0.005, 0.005, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.09, 0.099]
    assert _bh_threshold(pvals, q=0.10) == 10


# -----------------------------------------------------------------------------
# Soft-fail
# -----------------------------------------------------------------------------


def test_select_empty_moments_returns_empty():
    moments = IacPriorMoments()
    result = select_iac_via_fdr(moments)
    assert isinstance(result, IacFDRSelectionResult)
    assert result.selected_triples == []
    assert result.n_selected == 0
    assert result.n_candidates == 0


def test_select_none_moments_returns_empty():
    result = select_iac_via_fdr(None)  # type: ignore[arg-type]
    assert result.selected_triples == []


def test_select_fdr_target_zero_returns_empty():
    moments = IacPriorMoments()
    moments.moments[("exec", "authority", "biz")] = (1.0, 0.01)
    result = select_iac_via_fdr(moments, fdr_target=0.0)
    assert result.selected_triples == []


def test_select_fdr_target_above_one_returns_empty():
    moments = IacPriorMoments()
    moments.moments[("exec", "authority", "biz")] = (1.0, 0.01)
    result = select_iac_via_fdr(moments, fdr_target=1.5)
    assert result.selected_triples == []


# -----------------------------------------------------------------------------
# Selection correctness on signal + null
# -----------------------------------------------------------------------------


def test_select_strong_signal_is_selected():
    """A triple with mean=1.0, variance=0.01 → |z|=10 → tiny p →
    selected at any reasonable fdr_target."""
    moments = IacPriorMoments()
    moments.moments[("exec", "authority", "biz")] = (1.0, 0.01)
    moments.moments[("exec", "scarcity", "biz")] = (0.001, 1.0)  # near-null
    result = select_iac_via_fdr(moments, fdr_target=0.10)
    assert ("exec", "authority", "biz") in result.selected_triples


def test_select_weak_signal_not_selected():
    """A triple with mean=0.05, variance=1.0 → |z|=0.05 → p ≈ 1 →
    not selected."""
    moments = IacPriorMoments()
    moments.moments[("exec", "authority", "biz")] = (0.05, 1.0)
    moments.moments[("exec", "scarcity", "biz")] = (0.05, 1.0)
    result = select_iac_via_fdr(moments, fdr_target=0.10)
    assert result.selected_triples == []


def test_select_pure_null_few_false_discoveries():
    """100 triples drawn from null (mean ~ 0, variance = 1). At
    fdr_target=0.10 we expect ≤ 0.10 * (selected) false discoveries.
    Since all are nulls, selections ARE false discoveries — count
    should be small in expectation."""
    rng = np.random.default_rng(42)
    moments = IacPriorMoments()
    for i in range(100):
        # Standard-normal "posterior mean" sample with unit variance
        moments.moments[("a" + str(i), "m", "c")] = (
            float(rng.standard_normal()), 1.0,
        )
    result = select_iac_via_fdr(moments, fdr_target=0.10)
    # Under pure null at q=0.10, BH controls FDR — expected number of
    # rejections is small. Pin a generous bound: well under half.
    assert result.n_selected < 50, (
        f"BH FDR control failed on pure null: n_selected={result.n_selected}"
    )


def test_select_signal_dominates_over_null():
    """5 strong-signal triples + 50 null triples. The signals should
    all be selected at q=0.10."""
    rng = np.random.default_rng(7)
    moments = IacPriorMoments()
    # 5 strong signals: mean=1.0, variance=0.01 → |z|=10
    signal_keys = []
    for i in range(5):
        key = ("signal_" + str(i), "m", "c")
        moments.moments[key] = (1.0, 0.01)
        signal_keys.append(key)
    # 50 null triples
    for i in range(50):
        moments.moments[("null_" + str(i), "m", "c")] = (
            float(rng.standard_normal()) * 0.3, 1.0,
        )
    result = select_iac_via_fdr(moments, fdr_target=0.10)
    for key in signal_keys:
        assert key in result.selected_triples, (
            f"strong signal {key} not selected"
        )


# -----------------------------------------------------------------------------
# Determinism + ordering
# -----------------------------------------------------------------------------


def test_select_deterministic_on_repeated_call():
    """Same input → same output across calls (no random sampling)."""
    moments = IacPriorMoments()
    moments.moments[("exec", "authority", "biz")] = (1.0, 0.01)
    moments.moments[("exec", "scarcity", "biz")] = (0.8, 0.01)
    moments.moments[("pro", "authority", "biz")] = (0.7, 0.01)

    r1 = select_iac_via_fdr(moments, fdr_target=0.10)
    r2 = select_iac_via_fdr(moments, fdr_target=0.10)
    assert r1.selected_triples == r2.selected_triples
    assert r1.z_threshold == r2.z_threshold


def test_select_returns_lexicographically_sorted_triples():
    """selected_triples is sorted lexicographically — deterministic
    consumption by next horseshoe fit."""
    moments = IacPriorMoments()
    moments.moments[("z_arch", "z_mech", "z_cat")] = (1.0, 0.01)
    moments.moments[("a_arch", "a_mech", "a_cat")] = (1.0, 0.01)
    moments.moments[("m_arch", "m_mech", "m_cat")] = (1.0, 0.01)

    result = select_iac_via_fdr(moments, fdr_target=0.10)
    assert result.selected_triples == sorted(result.selected_triples)


# -----------------------------------------------------------------------------
# Result diagnostics
# -----------------------------------------------------------------------------


def test_z_threshold_is_minimum_z_of_selected():
    """z_threshold should equal the smallest |z| among selected
    triples (the boundary)."""
    moments = IacPriorMoments()
    moments.moments[("a", "m", "c")] = (1.0, 0.01)   # z=10
    moments.moments[("b", "m", "c")] = (2.0, 0.01)   # z=20
    moments.moments[("c", "m", "c")] = (3.0, 0.01)   # z=30
    result = select_iac_via_fdr(moments, fdr_target=0.10)
    # All three selected; threshold = z of weakest (a) = 10
    assert math.isclose(result.z_threshold, 10.0, rel_tol=1e-6)


def test_z_threshold_is_inf_when_no_selection():
    moments = IacPriorMoments()
    moments.moments[("a", "m", "c")] = (0.001, 1.0)
    moments.moments[("b", "m", "c")] = (0.001, 1.0)
    result = select_iac_via_fdr(moments)
    assert result.z_threshold == float("inf")
    assert result.selected_triples == []


def test_z_scores_diagnostic_covers_all_candidates():
    """z_scores_by_triple should contain ALL input triples (not just
    selected). This is the diagnostic surface for the dashboard."""
    moments = IacPriorMoments()
    moments.moments[("a", "m", "c")] = (1.0, 0.01)   # selected
    moments.moments[("b", "m", "c")] = (0.001, 1.0)  # not selected
    result = select_iac_via_fdr(moments, fdr_target=0.10)
    triples_in_z_diag = {t for (t, _) in result.z_scores_by_triple}
    assert triples_in_z_diag == set(moments.moments.keys())


def test_z_scores_diagnostic_lexicographically_sorted():
    """Diagnostic surface is sorted for stable display."""
    moments = IacPriorMoments()
    moments.moments[("z", "m", "c")] = (1.0, 0.01)
    moments.moments[("a", "m", "c")] = (1.0, 0.01)
    moments.moments[("m", "m", "c")] = (1.0, 0.01)
    result = select_iac_via_fdr(moments, fdr_target=0.10)
    triples = [t for (t, _) in result.z_scores_by_triple]
    assert triples == sorted(triples)


def test_n_candidates_matches_input_size():
    moments = IacPriorMoments()
    for i in range(7):
        moments.moments[("a" + str(i), "m", "c")] = (1.0, 0.01)
    result = select_iac_via_fdr(moments)
    assert result.n_candidates == 7


def test_n_selected_matches_selected_triples_length():
    moments = IacPriorMoments()
    moments.moments[("a", "m", "c")] = (1.0, 0.01)
    moments.moments[("b", "m", "c")] = (1.0, 0.01)
    result = select_iac_via_fdr(moments)
    assert result.n_selected == len(result.selected_triples)


def test_result_is_immutable():
    moments = IacPriorMoments()
    moments.moments[("a", "m", "c")] = (1.0, 0.01)
    result = select_iac_via_fdr(moments)
    with pytest.raises((AttributeError, Exception)):
        result.selected_triples = []  # type: ignore[misc]


# -----------------------------------------------------------------------------
# Convenience helper
# -----------------------------------------------------------------------------


def test_select_pre_specified_returns_same_triples_as_full_selection():
    moments = IacPriorMoments()
    moments.moments[("a", "m", "c")] = (1.0, 0.01)
    moments.moments[("b", "m", "c")] = (1.0, 0.01)
    moments.moments[("c", "m", "c")] = (0.001, 1.0)

    full = select_iac_via_fdr(moments, fdr_target=0.10)
    helper = select_pre_specified_for_next_fit(moments, fdr_target=0.10)
    assert helper == full.selected_triples


def test_select_pre_specified_empty_input_returns_empty_list():
    helper = select_pre_specified_for_next_fit(IacPriorMoments())
    assert helper == []


# -----------------------------------------------------------------------------
# Integration: compose with IacPriorMoments downstream consumer
# -----------------------------------------------------------------------------


def test_selected_triples_shape_matches_horseshoe_pre_specified_arg():
    """The selected_triples must be List[Tuple[str, str, str]] —
    exactly the shape build_hierarchical_model_with_interactions
    accepts as pre_specified_interactions."""
    moments = IacPriorMoments()
    moments.moments[("exec", "authority", "biz")] = (1.0, 0.01)
    result = select_iac_via_fdr(moments)
    for triple in result.selected_triples:
        assert isinstance(triple, tuple)
        assert len(triple) == 3
        assert all(isinstance(x, str) for x in triple)
