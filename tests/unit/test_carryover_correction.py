"""Pin Slice 12 — Step 10 carryover correction primitive.

Discipline anchors (B3-LUXY a/b/c/d):

    (a) Citations: directive Section 5.1 Step 10 (line 692) +
        Spine #2 carryover formula (lines 116-118 + 477) +
        within_subject_eligibility honest tag (d) lines 85-89
        (this slice composes on the Slice 3 touch-history primitive).

    (b) Boundary anchors:
          - candidate ≠ last_touched → penalty 0 (single-ρ approx)
          - ρ=0 → penalty 0 (no signal)
          - Δ=0 + τ>0 → penalty = ρ · effect (no decay)
          - Δ→∞ → penalty → 0 (decay exhausts)
          - τ ≤ 0 → no decay (penalty saturates)
          - negative ρ → negative penalty → score INCREASE
          - score floor preserved (no score < 0)
          - empty mechanism_scores → pass-through
          - pure formula round-trip
          - CarryoverCorrectionResult frozen

    (c) calibration_pending=True. v0.1 single per-user ρ;
        pair-indexed sibling will activate cross-mechanism.

    (d) Honest tags — what is NOT tested here:
          - Pair-indexed ρ_m1→m2 (sibling)
          - Time-conditional effect(m, t-Δ) (sibling)
          - τ pilot calibration (sibling)
          - Chosen-mechanism score-component decomposition (sibling)
"""

from __future__ import annotations

import math

import pytest

from adam.intelligence.carryover_correction import (
    CarryoverCorrectionResult,
    apply_carryover_correction,
    compute_carryover_penalty,
)


# ---------------------------------------------------------------------------
# compute_carryover_penalty — formula primitive
# ---------------------------------------------------------------------------


def test_penalty_zero_when_no_last_touched():
    """Cold buyer: no prior touch → penalty 0."""
    p = compute_carryover_penalty(
        candidate_mechanism="social_proof",
        last_touched_mechanism=None,
        hours_since_last_touch=0.0,
        rho=0.5,
        effect_prev=0.7,
        tau=24.0,
    )
    assert p == 0.0


def test_penalty_zero_when_no_candidate():
    p = compute_carryover_penalty(
        candidate_mechanism="",
        last_touched_mechanism="social_proof",
        hours_since_last_touch=2.0,
        rho=0.5,
        effect_prev=0.7,
        tau=24.0,
    )
    assert p == 0.0


def test_penalty_zero_for_cross_mechanism_v01_single_rho():
    """v0.1 single-ρ approximation: candidate ≠ last_touched → 0.
    Pair-indexed ρ_m1→m2 is honest-tag sibling."""
    p = compute_carryover_penalty(
        candidate_mechanism="scarcity",
        last_touched_mechanism="social_proof",
        hours_since_last_touch=2.0,
        rho=0.5,
        effect_prev=0.7,
        tau=24.0,
    )
    assert p == 0.0


def test_penalty_zero_when_rho_zero():
    """ρ=0 → no AR(1) signal → no correction."""
    p = compute_carryover_penalty(
        candidate_mechanism="social_proof",
        last_touched_mechanism="social_proof",
        hours_since_last_touch=2.0,
        rho=0.0,
        effect_prev=0.7,
        tau=24.0,
    )
    assert p == 0.0


def test_penalty_at_zero_delta_equals_rho_times_effect():
    """Δ=0 → exp(0)=1 → penalty = ρ · effect."""
    p = compute_carryover_penalty(
        candidate_mechanism="social_proof",
        last_touched_mechanism="social_proof",
        hours_since_last_touch=0.0,
        rho=0.5,
        effect_prev=0.7,
        tau=24.0,
    )
    assert p == pytest.approx(0.5 * 0.7, rel=1e-9)


def test_penalty_decays_to_zero_at_large_delta():
    """As Δ → ∞, penalty → 0."""
    p_short = compute_carryover_penalty(
        candidate_mechanism="social_proof",
        last_touched_mechanism="social_proof",
        hours_since_last_touch=1.0,
        rho=0.5,
        effect_prev=0.7,
        tau=24.0,
    )
    p_long = compute_carryover_penalty(
        candidate_mechanism="social_proof",
        last_touched_mechanism="social_proof",
        hours_since_last_touch=240.0,  # 10× tau
        rho=0.5,
        effect_prev=0.7,
        tau=24.0,
    )
    assert p_short > p_long
    assert p_long < 1e-3  # very small after 10× decay


def test_penalty_canonical_formula_round_trip():
    """Direct formula: ρ · effect · exp(-Δ/τ)."""
    rho, effect, delta, tau = 0.4, 0.8, 6.0, 12.0
    p = compute_carryover_penalty(
        candidate_mechanism="social_proof",
        last_touched_mechanism="social_proof",
        hours_since_last_touch=delta,
        rho=rho,
        effect_prev=effect,
        tau=tau,
    )
    expected = rho * effect * math.exp(-delta / tau)
    assert p == pytest.approx(expected, rel=1e-9)


def test_penalty_negative_rho_yields_negative_penalty():
    """Negative ρ (interference) → negative penalty → score
    INCREASE (Step 10 subtracts a negative)."""
    p = compute_carryover_penalty(
        candidate_mechanism="social_proof",
        last_touched_mechanism="social_proof",
        hours_since_last_touch=1.0,
        rho=-0.3,
        effect_prev=0.7,
        tau=24.0,
    )
    assert p < 0.0


def test_penalty_negative_delta_treated_as_zero():
    """Defensive: negative Δ (clock skew) → 0 hours."""
    p = compute_carryover_penalty(
        candidate_mechanism="social_proof",
        last_touched_mechanism="social_proof",
        hours_since_last_touch=-5.0,
        rho=0.5,
        effect_prev=0.7,
        tau=24.0,
    )
    assert p == pytest.approx(0.5 * 0.7, rel=1e-9)


def test_penalty_none_delta_treated_as_zero():
    p = compute_carryover_penalty(
        candidate_mechanism="social_proof",
        last_touched_mechanism="social_proof",
        hours_since_last_touch=None,
        rho=0.5,
        effect_prev=0.7,
        tau=24.0,
    )
    assert p == pytest.approx(0.5 * 0.7, rel=1e-9)


def test_penalty_tau_zero_disables_decay():
    """τ ≤ 0 means no decay applied — penalty saturates."""
    p_zero_tau = compute_carryover_penalty(
        candidate_mechanism="social_proof",
        last_touched_mechanism="social_proof",
        hours_since_last_touch=100.0,
        rho=0.5,
        effect_prev=0.7,
        tau=0.0,
    )
    assert p_zero_tau == pytest.approx(0.5 * 0.7, rel=1e-9)


def test_penalty_tau_negative_disables_decay():
    p_neg_tau = compute_carryover_penalty(
        candidate_mechanism="social_proof",
        last_touched_mechanism="social_proof",
        hours_since_last_touch=100.0,
        rho=0.5,
        effect_prev=0.7,
        tau=-1.0,
    )
    assert p_neg_tau == pytest.approx(0.5 * 0.7, rel=1e-9)


# ---------------------------------------------------------------------------
# apply_carryover_correction — wire-point primitive
# ---------------------------------------------------------------------------


def test_apply_empty_scores_returns_empty():
    out = apply_carryover_correction(
        {},
        last_touched_mechanism="social_proof",
        hours_since_last_touch=1.0,
        rho=0.5,
        effect_prev_for_last_touched=0.7,
        tau=24.0,
    )
    assert out.modulated_scores == {}
    assert out.per_mechanism_penalty == {}
    assert out.n_corrected == 0


def test_apply_no_last_touched_pass_through():
    """Cold buyer / no prior touch → all scores unchanged."""
    scores = {"social_proof": 0.6, "scarcity": 0.4}
    out = apply_carryover_correction(
        scores,
        last_touched_mechanism=None,
        hours_since_last_touch=None,
        rho=0.5,
        effect_prev_for_last_touched=0.7,
        tau=24.0,
    )
    assert out.modulated_scores == scores
    # Honest signal: penalty dict shows 0 per mechanism (was attempted,
    # nothing claimed).
    assert all(v == 0.0 for v in out.per_mechanism_penalty.values())
    assert out.n_corrected == 0


def test_apply_rho_zero_pass_through():
    """ρ=0 → all scores unchanged."""
    scores = {"social_proof": 0.6, "scarcity": 0.4}
    out = apply_carryover_correction(
        scores,
        last_touched_mechanism="social_proof",
        hours_since_last_touch=1.0,
        rho=0.0,
        effect_prev_for_last_touched=0.7,
        tau=24.0,
    )
    assert out.modulated_scores == scores
    assert out.n_corrected == 0


def test_apply_only_same_mechanism_corrected():
    """v0.1: only candidate == last_touched gets a non-zero penalty."""
    scores = {"social_proof": 0.6, "scarcity": 0.4, "authority": 0.5}
    out = apply_carryover_correction(
        scores,
        last_touched_mechanism="social_proof",
        hours_since_last_touch=0.0,  # full effect
        rho=0.5,
        effect_prev_for_last_touched=0.7,
        tau=24.0,
    )
    expected_penalty = 0.5 * 0.7  # 0.35
    assert out.per_mechanism_penalty["social_proof"] == pytest.approx(
        expected_penalty,
    )
    assert out.per_mechanism_penalty["scarcity"] == 0.0
    assert out.per_mechanism_penalty["authority"] == 0.0
    # social_proof score reduced; others unchanged.
    assert out.modulated_scores["social_proof"] == pytest.approx(
        0.6 - expected_penalty,
    )
    assert out.modulated_scores["scarcity"] == 0.4
    assert out.modulated_scores["authority"] == 0.5
    assert out.n_corrected == 1


def test_apply_score_floor_preserves_zero():
    """Penalty exceeding score is floored at 0 (no negative scores)."""
    scores = {"social_proof": 0.05}  # tiny score
    out = apply_carryover_correction(
        scores,
        last_touched_mechanism="social_proof",
        hours_since_last_touch=0.0,
        rho=1.0,
        effect_prev_for_last_touched=0.9,  # penalty 0.9 >> 0.05
        tau=24.0,
    )
    assert out.modulated_scores["social_proof"] == 0.0


def test_apply_negative_rho_increases_score():
    """Negative ρ → negative penalty → score INCREASE
    (interference flip)."""
    scores = {"social_proof": 0.5}
    out = apply_carryover_correction(
        scores,
        last_touched_mechanism="social_proof",
        hours_since_last_touch=0.0,
        rho=-0.3,
        effect_prev_for_last_touched=0.6,
        tau=24.0,
    )
    expected_penalty = -0.3 * 0.6  # -0.18
    assert out.per_mechanism_penalty["social_proof"] == pytest.approx(
        expected_penalty,
    )
    # score = 0.5 - (-0.18) = 0.68
    assert out.modulated_scores["social_proof"] == pytest.approx(
        0.5 - expected_penalty,
    )
    assert out.n_corrected == 1


def test_apply_large_delta_decays_correction_to_negligible():
    """At Δ >> τ, score barely changes."""
    scores = {"social_proof": 0.5}
    out = apply_carryover_correction(
        scores,
        last_touched_mechanism="social_proof",
        hours_since_last_touch=240.0,  # 10× tau
        rho=0.5,
        effect_prev_for_last_touched=0.7,
        tau=24.0,
    )
    # Tiny penalty → score nearly unchanged
    assert out.modulated_scores["social_proof"] == pytest.approx(0.5, abs=1e-3)
    # n_corrected may be 0 if shift < 1e-9 tolerance — that's fine
    # (the test pins behavior, not whether it triggers the counter).


def test_apply_carryover_result_frozen():
    """CarryoverCorrectionResult is frozen — guard against mutation."""
    out = apply_carryover_correction(
        {"social_proof": 0.5},
        last_touched_mechanism="social_proof",
        hours_since_last_touch=0.0,
        rho=0.5,
        effect_prev_for_last_touched=0.7,
        tau=24.0,
    )
    with pytest.raises((AttributeError, Exception)):  # FrozenInstanceError
        out.n_corrected = 99  # type: ignore[misc]


def test_apply_rho_echoed_in_result():
    """The ρ value used is echoed back for diagnostic surfaces."""
    out = apply_carryover_correction(
        {"social_proof": 0.5},
        last_touched_mechanism="social_proof",
        hours_since_last_touch=1.0,
        rho=0.42,
        effect_prev_for_last_touched=0.7,
        tau=24.0,
    )
    assert out.rho == pytest.approx(0.42)


def test_apply_invalid_score_value_preserved():
    """Non-numeric score values pass through (defensive). Penalty is 0."""
    scores = {"social_proof": "not-a-number", "scarcity": 0.4}  # type: ignore
    out = apply_carryover_correction(
        scores,  # type: ignore
        last_touched_mechanism="social_proof",
        hours_since_last_touch=0.0,
        rho=0.5,
        effect_prev_for_last_touched=0.7,
        tau=24.0,
    )
    # Invalid score preserved; penalty=0 for that mechanism
    assert out.modulated_scores["social_proof"] == "not-a-number"
    assert out.per_mechanism_penalty["social_proof"] == 0.0
    # Valid one still works (and it's not the last_touched, so no penalty)
    assert out.modulated_scores["scarcity"] == 0.4
