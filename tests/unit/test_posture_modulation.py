"""Pin Slice 8 — posture × mechanism modulation of cascade scores.

Discipline anchors (B3-LUXY a/b/c/d) for
``adam/intelligence/posture_modulation.py``:

    (a) Multiplicative shrinkage formula:
            factor = 1.0 + POSTURE_WEIGHT · (compatibility - 0.5) · 2.0
            modulated_score = base_score · factor
        With POSTURE_WEIGHT=0.20:
            LOW (0.25) → factor 0.90  (mismatched diagonal)
            MID (0.50) → factor 1.00  (neutral / unknown)
            HIGH (0.75) → factor 1.10 (matched diagonal)

    (b) Boundary anchors pinned by these tests:
          - matched diagonal (POSTURE_BLEND × BLEND_COMPATIBLE) → up
          - mismatched diagonal (POSTURE_BLEND × VIGILANCE_ACTIVATING) → down
          - MID compatibility → unchanged
          - POSTURE_UNKNOWN → unchanged (early-out)
          - None posture → unchanged
          - empty mechanism_scores → unchanged
          - unknown mechanism in scores → MID by soft-fail (no shift)
          - score values clipped to [0, 1] after modulation
          - factor monotonic in compatibility

    (c) calibration_pending=True. POSTURE_WEIGHT=0.20 is conservative
        pre-pilot. A14 flag.

    (d) Honest tags — what is NOT tested here:
          - Per-archetype × posture × mechanism prior tensor (sibling)
          - Continuous-vector posture (5-class head) (sibling)
          - Posture-conditional bilateral edge query (sibling)
"""

from __future__ import annotations

import pytest

from adam.intelligence.page_attentional_posture_substrate import (
    POSTURE_BLEND,
    POSTURE_NEUTRAL,
    POSTURE_UNKNOWN,
    POSTURE_VIGILANCE,
)
from adam.intelligence.posture_modulation import (
    POSTURE_WEIGHT,
    apply_posture_modulation,
    posture_modulation_factor,
)
from adam.intelligence.posture_mechanism_prior import (
    COMPATIBILITY_HIGH,
    COMPATIBILITY_LOW,
    COMPATIBILITY_MID,
)


# Mechanisms in MECHANISM_TAXONOMY for clean diagonal tests:
#   BLEND_COMPATIBLE: mimetic_desire, embodied_cognition, temporal_construal
#   VIGILANCE_ACTIVATING: identity_construction, attention_dynamics


# -----------------------------------------------------------------------------
# posture_modulation_factor — formula correctness
# -----------------------------------------------------------------------------


def test_factor_matched_diagonal_high():
    """POSTURE_BLEND × mimetic_desire (BLEND_COMPATIBLE) → HIGH → factor 1.10."""
    factor = posture_modulation_factor(POSTURE_BLEND, "mimetic_desire")
    expected = 1.0 + POSTURE_WEIGHT * (COMPATIBILITY_HIGH - 0.5) * 2.0
    assert factor == pytest.approx(expected)
    assert factor == pytest.approx(1.10)


def test_factor_mismatched_diagonal_low():
    """POSTURE_BLEND × identity_construction (VIGILANCE_ACTIVATING) → LOW → 0.90."""
    factor = posture_modulation_factor(POSTURE_BLEND, "identity_construction")
    expected = 1.0 + POSTURE_WEIGHT * (COMPATIBILITY_LOW - 0.5) * 2.0
    assert factor == pytest.approx(expected)
    assert factor == pytest.approx(0.90)


def test_factor_neutral_posture_mid():
    """POSTURE_NEUTRAL × any → MID → factor 1.0."""
    factor = posture_modulation_factor(POSTURE_NEUTRAL, "mimetic_desire")
    assert factor == pytest.approx(1.0)


def test_factor_unknown_posture_mid():
    """POSTURE_UNKNOWN → soft-fail to MID → factor 1.0."""
    factor = posture_modulation_factor(POSTURE_UNKNOWN, "mimetic_desire")
    assert factor == pytest.approx(1.0)


def test_factor_unknown_mechanism_mid():
    """Mechanism not in taxonomy → MID by soft-fail → factor 1.0."""
    factor = posture_modulation_factor(POSTURE_BLEND, "not_a_real_mechanism")
    assert factor == pytest.approx(1.0)


def test_factor_monotonic_in_compatibility():
    """LOW < MID < HIGH compatibility → factors order accordingly."""
    f_low = posture_modulation_factor(POSTURE_BLEND, "identity_construction")
    f_mid = posture_modulation_factor(POSTURE_NEUTRAL, "mimetic_desire")
    f_high = posture_modulation_factor(POSTURE_BLEND, "mimetic_desire")
    assert f_low < f_mid < f_high


def test_factor_band_within_posture_weight():
    """factor in [1 − w, 1 + w] for any input."""
    for posture in (POSTURE_BLEND, POSTURE_VIGILANCE, POSTURE_NEUTRAL,
                    POSTURE_UNKNOWN):
        for mech in ("mimetic_desire", "identity_construction",
                     "attention_dynamics", "temporal_construal"):
            f = posture_modulation_factor(posture, mech)
            assert 1.0 - POSTURE_WEIGHT - 1e-9 <= f <= 1.0 + POSTURE_WEIGHT + 1e-9


# -----------------------------------------------------------------------------
# apply_posture_modulation — bulk wrapper
# -----------------------------------------------------------------------------


def test_apply_matched_diagonal_increases_score():
    scores = {"mimetic_desire": 0.50, "identity_construction": 0.50}
    out = apply_posture_modulation(scores, posture=POSTURE_BLEND)
    assert out["mimetic_desire"] > 0.50      # matched, up
    assert out["identity_construction"] < 0.50  # mismatched, down


def test_apply_mismatched_diagonal_decreases_score():
    scores = {"mimetic_desire": 0.50, "identity_construction": 0.50}
    out = apply_posture_modulation(scores, posture=POSTURE_VIGILANCE)
    assert out["mimetic_desire"] < 0.50      # mismatched, down
    assert out["identity_construction"] > 0.50  # matched, up


def test_apply_neutral_posture_no_change():
    """POSTURE_NEUTRAL → MID compatibility → factor 1.0 → no shift."""
    scores = {"mimetic_desire": 0.50, "identity_construction": 0.50}
    out = apply_posture_modulation(scores, posture=POSTURE_NEUTRAL)
    assert out["mimetic_desire"] == pytest.approx(0.50)
    assert out["identity_construction"] == pytest.approx(0.50)


def test_apply_unknown_posture_short_circuits():
    """POSTURE_UNKNOWN → return input unchanged (identity)."""
    scores = {"mimetic_desire": 0.50}
    out = apply_posture_modulation(scores, posture=POSTURE_UNKNOWN)
    assert out is scores  # identity — no allocation


def test_apply_none_posture_short_circuits():
    """posture=None → return input unchanged (identity)."""
    scores = {"mimetic_desire": 0.50}
    out = apply_posture_modulation(scores, posture=None)
    assert out is scores


def test_apply_empty_scores_returns_empty():
    out = apply_posture_modulation({}, posture=POSTURE_BLEND)
    assert out == {}


def test_apply_unknown_mechanism_unchanged():
    """Mechanism outside MECHANISM_TAXONOMY → factor 1.0 → unchanged."""
    scores = {"not_a_real_mechanism": 0.42}
    out = apply_posture_modulation(scores, posture=POSTURE_BLEND)
    assert out["not_a_real_mechanism"] == pytest.approx(0.42)


def test_apply_clips_to_score_range():
    """Modulated scores stay in [0, 1] even if base × factor would exceed."""
    # base=0.95, factor=1.10 → would be 1.045 → clipped to 1.0
    scores = {"mimetic_desire": 0.95}
    out = apply_posture_modulation(scores, posture=POSTURE_BLEND)
    assert out["mimetic_desire"] <= 1.0

    # base=0.05, factor=0.90 (POSTURE_VIGILANCE × mimetic) → 0.045
    scores2 = {"mimetic_desire": 0.05}
    out2 = apply_posture_modulation(scores2, posture=POSTURE_VIGILANCE)
    assert out2["mimetic_desire"] >= 0.0


def test_apply_preserves_score_count():
    """Modulation doesn't add or drop mechanisms."""
    scores = {
        "mimetic_desire": 0.5,
        "identity_construction": 0.5,
        "attention_dynamics": 0.5,
    }
    out = apply_posture_modulation(scores, posture=POSTURE_BLEND)
    assert set(out.keys()) == set(scores.keys())


def test_apply_factor_exact_band():
    """At base=0.50, modulated score equals 0.50 × factor exactly."""
    scores = {"mimetic_desire": 0.50}
    out = apply_posture_modulation(scores, posture=POSTURE_BLEND)
    expected = 0.50 * (1.0 + POSTURE_WEIGHT * (COMPATIBILITY_HIGH - 0.5) * 2.0)
    assert out["mimetic_desire"] == pytest.approx(expected)
    assert out["mimetic_desire"] == pytest.approx(0.55)
