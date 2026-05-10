"""Q.B/Q.3 (Sketch C+) — tests for causal_learning MODERATES.

Pin: vocabulary coherence (Q.W + Q.X), moderation test logic, BH FDR
on grid, persist gating on box state, query → cascade application,
end-to-end discovery + cascade.
"""

import pytest

from adam.intelligence.causal_learning import (
    CANONICAL_CIALDINI_9,
    EDGE_DIMENSIONS,
    MECHANISMS,
    CausalObservation,
    CausalTestEngine,
    ModerationTestResult,
    apply_moderates_modulation,
    _apply_bh_correction_to_moderation,
)


# =============================================================================
# Q.W + Q.X — vocabulary coherence regression tests
# =============================================================================


def test_anchoring_present_in_mechanisms():
    """Q.W: anchoring must be present (canonical Cialdini-9)."""
    assert "anchoring" in MECHANISMS


def test_canonical_cialdini_9_size():
    """Q.W: canonical subset is exactly 9 mechanisms."""
    assert len(CANONICAL_CIALDINI_9) == 9


def test_canonical_cialdini_9_contains_anchoring():
    assert "anchoring" in CANONICAL_CIALDINI_9


def test_cognitive_ease_preserved_for_backward_compat():
    """Q.W: cognitive_ease stays in MECHANISMS (additive cleanup —
    blast radius across constants.py + main.py + demo data)."""
    assert "cognitive_ease" in MECHANISMS


def test_maximizer_tendency_in_edge_dimensions():
    """Q.X: maximizer_tendency added (W.2b dimension)."""
    assert "maximizer_tendency" in EDGE_DIMENSIONS


def test_edge_dimensions_count_includes_maximizer():
    """Q.X: 21 dims (20 original + maximizer_tendency)."""
    assert len(EDGE_DIMENSIONS) == 21


# =============================================================================
# ModerationTestResult dataclass
# =============================================================================


def test_moderation_test_result_effect_size_aliases_cohens_h():
    r = ModerationTestResult(cohens_h=0.42)
    assert r.effect_size == 0.42


def test_moderation_test_result_default_not_significant():
    r = ModerationTestResult()
    assert r.significant is False
    assert r.lift == 1.0


# =============================================================================
# test_archetype_moderates_dimension_amplifies_mechanism
# =============================================================================


def _obs(
    archetype: str,
    dim_value: float,
    success: bool,
    *,
    mechanism: str = "social_proof",
    decision_id: str = "d",
) -> CausalObservation:
    return CausalObservation(
        decision_id=decision_id,
        mechanism_sent=mechanism,
        page_edge_dimensions={"regulatory_fit": dim_value},
        archetype=archetype,
        success=success,
    )


def test_moderation_insufficient_data_returns_non_significant():
    engine = CausalTestEngine()
    obs = [_obs("achiever", 0.7, True)]  # only 1
    result = engine.test_archetype_moderates_dimension_amplifies_mechanism(
        "achiever", "regulatory_fit", "social_proof", obs,
    )
    assert result.significant is False
    assert result.n_archetype <= 20


def test_moderation_strong_amplification_in_archetype_yields_significant():
    """Synthetic case: 'achiever' has STRONG amplification by
    regulatory_fit; non-achievers have weak amplification."""
    engine = CausalTestEngine()
    obs = []
    # Achiever: high-dim wins 80% / low-dim wins 20% → 0.6 amplification
    for i in range(30):
        obs.append(_obs("achiever", 0.8, success=(i < 24), decision_id=f"a_h_{i}"))
    for i in range(30):
        obs.append(_obs("achiever", 0.2, success=(i < 6), decision_id=f"a_l_{i}"))
    # Non-achiever: high-dim wins 50% / low-dim wins 40% → 0.1 amplification
    for i in range(30):
        obs.append(_obs("explorer", 0.8, success=(i < 15), decision_id=f"e_h_{i}"))
    for i in range(30):
        obs.append(_obs("explorer", 0.2, success=(i < 12), decision_id=f"e_l_{i}"))
    result = engine.test_archetype_moderates_dimension_amplifies_mechanism(
        "achiever", "regulatory_fit", "social_proof", obs,
    )
    assert result.lift > 1.5  # achiever amplification much greater
    assert result.cohens_h > 0.2
    assert result.p_value < 0.05
    assert result.significant is True


def test_moderation_no_difference_yields_non_significant():
    engine = CausalTestEngine()
    obs = []
    for arch in ("achiever", "explorer"):
        for i in range(30):
            obs.append(_obs(arch, 0.8, success=(i < 15), decision_id=f"{arch}_h_{i}"))
            obs.append(_obs(arch, 0.2, success=(i < 12), decision_id=f"{arch}_l_{i}"))
    result = engine.test_archetype_moderates_dimension_amplifies_mechanism(
        "achiever", "regulatory_fit", "social_proof", obs,
    )
    # Both partitions have same amplification → lift ≈ 1.0; not significant
    assert result.significant is False


# =============================================================================
# BH-FDR correction on the moderation grid
# =============================================================================


def test_bh_correction_demotes_borderline_p_values():
    """High p-value results should be demoted to non-significant
    after BH correction even if the per-test p-value < 0.05.

    With 3 tests at [0.001, 0.04, 0.06] and alpha=0.05:
      rank 1: threshold = 1/3 * 0.05 ≈ 0.0167; 0.001 ≤ 0.0167 → sig
      rank 2: threshold = 2/3 * 0.05 ≈ 0.0333; 0.04  > 0.0333 → not sig
      rank 3: threshold = 3/3 * 0.05 = 0.05;   0.06  > 0.05    → not sig
    """
    results = [
        ModerationTestResult(p_value=0.001, cohens_h=0.5, lift=2.0),
        ModerationTestResult(p_value=0.04, cohens_h=0.3, lift=1.5),
        ModerationTestResult(p_value=0.06, cohens_h=0.3, lift=1.3),
    ]
    _apply_bh_correction_to_moderation(results, alpha=0.05)
    # Strongest result should remain significant
    assert results[0].significant is True
    # Borderline results should be demoted (BH gates them out)
    assert results[1].significant is False
    assert results[2].significant is False


def test_bh_correction_empty_returns_empty():
    out = _apply_bh_correction_to_moderation([], alpha=0.05)
    assert out == []


def test_bh_correction_lift_threshold_gate():
    """Even with p < threshold, lift <= 1.1 should not be significant."""
    results = [
        ModerationTestResult(p_value=0.001, cohens_h=0.5, lift=1.05),  # too small
    ]
    _apply_bh_correction_to_moderation(results, alpha=0.05)
    assert results[0].significant is False


# =============================================================================
# apply_moderates_modulation — cascade modulator
# =============================================================================


def test_apply_moderates_modulation_no_op_when_empty():
    scores = {"social_proof": 0.5, "authority": 0.6}
    out, log = apply_moderates_modulation(scores, {}, {})
    assert out == scores
    assert log == []


def test_apply_moderates_modulation_amplifies_when_page_dim_high():
    scores = {"social_proof": 0.5}
    moderates_map = {
        ("regulatory_fit", "social_proof"): {"lift": 1.5},
    }
    page_dims = {"regulatory_fit": 0.8}  # > 0.6 threshold
    out, log = apply_moderates_modulation(scores, moderates_map, page_dims)
    assert out["social_proof"] == pytest.approx(0.5 * 1.5)
    assert len(log) == 1
    assert "MODERATES" in log[0]


def test_apply_moderates_modulation_no_op_when_page_dim_low():
    scores = {"social_proof": 0.5}
    moderates_map = {
        ("regulatory_fit", "social_proof"): {"lift": 1.5},
    }
    page_dims = {"regulatory_fit": 0.4}  # below 0.6 threshold
    out, log = apply_moderates_modulation(scores, moderates_map, page_dims)
    assert out["social_proof"] == 0.5
    assert log == []


def test_apply_moderates_modulation_bounded_lift_upper():
    """Lift > 2.0 should clip to 2.0 (bounded multiplier)."""
    scores = {"social_proof": 0.4}
    moderates_map = {
        ("regulatory_fit", "social_proof"): {"lift": 5.0},  # would 5x without bound
    }
    page_dims = {"regulatory_fit": 0.9}
    out, _ = apply_moderates_modulation(scores, moderates_map, page_dims)
    # 0.4 * 2.0 = 0.8 (bounded), clamped to [0, 1]
    assert out["social_proof"] == pytest.approx(0.8)


def test_apply_moderates_modulation_bounded_lift_lower():
    """Lift < 0.5 should clip to 0.5 (prevent zeroing-out)."""
    scores = {"social_proof": 0.6}
    moderates_map = {
        ("regulatory_fit", "social_proof"): {"lift": 0.1},  # would near-zero without bound
    }
    page_dims = {"regulatory_fit": 0.9}
    out, _ = apply_moderates_modulation(scores, moderates_map, page_dims)
    # 0.6 * 0.5 = 0.3 (bounded)
    assert out["social_proof"] == pytest.approx(0.3)


def test_apply_moderates_modulation_clamps_to_unit_interval():
    """Output mechanism scores stay in [0, 1] regardless of input."""
    scores = {"social_proof": 0.9}
    moderates_map = {
        ("regulatory_fit", "social_proof"): {"lift": 2.0},
    }
    page_dims = {"regulatory_fit": 0.9}
    out, _ = apply_moderates_modulation(scores, moderates_map, page_dims)
    assert out["social_proof"] <= 1.0
    assert out["social_proof"] >= 0.0


def test_apply_moderates_modulation_skips_unknown_mechanism():
    """If mechanism not in scores dict, modulation entry skipped."""
    scores = {"social_proof": 0.5}
    moderates_map = {
        ("regulatory_fit", "anchoring"): {"lift": 1.5},  # anchoring not in scores
    }
    page_dims = {"regulatory_fit": 0.9}
    out, log = apply_moderates_modulation(scores, moderates_map, page_dims)
    assert out == scores
    assert log == []


def test_apply_moderates_modulation_multiple_entries():
    scores = {"social_proof": 0.5, "authority": 0.4}
    moderates_map = {
        ("regulatory_fit", "social_proof"): {"lift": 1.4},
        ("construal_fit", "authority"): {"lift": 1.3},
    }
    page_dims = {"regulatory_fit": 0.8, "construal_fit": 0.7}
    out, log = apply_moderates_modulation(scores, moderates_map, page_dims)
    assert out["social_proof"] == pytest.approx(0.5 * 1.4)
    assert out["authority"] == pytest.approx(0.4 * 1.3)
    assert len(log) == 2
