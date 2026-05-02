"""Pin Slice 1 — mechanism-granularity hard fluency floor.

Discipline anchors (B3-LUXY a/b/c/d) for
``adam/intelligence/mechanism_fluency_floor.py``:

    (a) Hard eligibility filter on posture × mechanism compatibility
        per directive line 974 ("Wire as eligibility filter, not as
        score modifier"). Threshold MECHANISM_FLUENCY_FLOOR = 0.30 sits
        between COMPATIBILITY_LOW (0.25) and COMPATIBILITY_MID (0.50)
        so LOW combinations are dropped while MID and HIGH pass.
        Matches bid_composer.FLUENCY_PROXY_FLOOR (0.30) so the soft
        gate (epistemic_bonus=0) and the hard gate (drop) fire on the
        same condition.

    (b) Boundary anchors pinned by these tests:
          - LOW posture × mechanism (e.g. POSTURE_BLEND × VIGILANCE)
            dropped from filtered_scores
          - MID posture (POSTURE_NEUTRAL / POSTURE_UNKNOWN) → all kept
          - HIGH diagonal kept
          - posture=None → pass-through (no signal)
          - empty mechanism_scores → pass-through
          - unknown mechanism → MID by soft-fail → kept
          - all-mechanisms-LOW → bypassed=True with input intact
            (Slice 3 will replace with refuse-all-bid)
          - n_dropped, n_eligible, dropped_mechanisms accounting
            consistent with the diff
          - threshold parameter respected
          - default threshold matches FLUENCY_PROXY_FLOOR for
            cross-module consistency

    (c) calibration_pending=True. Default threshold 0.30 calibration-
        pending under LUXY pilot via the matched_vs_mismatched_diagonals
        accumulator. A14 flag.

    (d) Honest tags — what is NOT tested here:
          - Creative-bundle-level fluency_floor (sibling Slice C —
            creative resolution). Composes ON TOP of this filter when
            it lands.
          - Hard refuse-all-bid semantic when all mechanisms LOW —
            sibling Slice 3 (within-subject scheduler + eligible-set
            construction per directive line 122).
          - Per-archetype × posture × mechanism prior tensor (sibling).
          - 5-class posture head (sibling).
"""

from __future__ import annotations

import logging

import pytest

from adam.intelligence.mechanism_fluency_floor import (
    MECHANISM_FLUENCY_FLOOR,
    MechanismFluencyResult,
    apply_mechanism_fluency_floor,
    passes_mechanism_fluency,
)
from adam.intelligence.page_attentional_posture_substrate import (
    POSTURE_BLEND,
    POSTURE_NEUTRAL,
    POSTURE_UNKNOWN,
    POSTURE_VIGILANCE,
)


# Mechanisms used here (per MECHANISM_TAXONOMY):
#   BLEND_COMPATIBLE: mimetic_desire, embodied_cognition, temporal_construal
#   VIGILANCE_ACTIVATING: identity_construction, attention_dynamics


# -----------------------------------------------------------------------------
# Threshold constant — cross-module consistency
# -----------------------------------------------------------------------------


def test_default_threshold_matches_bid_composer_proxy():
    """Hard floor and bid_composer's soft proxy fire on the same condition."""
    from adam.intelligence.bid_composer import FLUENCY_PROXY_FLOOR
    assert MECHANISM_FLUENCY_FLOOR == FLUENCY_PROXY_FLOOR


def test_threshold_sits_between_low_and_mid():
    """Default threshold drops LOW (0.25) but keeps MID (0.50) and HIGH (0.75)."""
    from adam.intelligence.posture_mechanism_prior import (
        COMPATIBILITY_HIGH,
        COMPATIBILITY_LOW,
        COMPATIBILITY_MID,
    )
    assert COMPATIBILITY_LOW < MECHANISM_FLUENCY_FLOOR < COMPATIBILITY_MID
    assert MECHANISM_FLUENCY_FLOOR < COMPATIBILITY_HIGH


# -----------------------------------------------------------------------------
# passes_mechanism_fluency — single-pair gate
# -----------------------------------------------------------------------------


def test_passes_high_diagonal():
    """POSTURE_BLEND × mimetic_desire (BLEND_COMPATIBLE) → HIGH → eligible."""
    assert passes_mechanism_fluency(POSTURE_BLEND, "mimetic_desire") is True


def test_passes_high_diagonal_vigilance():
    """POSTURE_VIGILANCE × identity_construction (VIGILANCE_ACTIVATING) → HIGH."""
    assert passes_mechanism_fluency(
        POSTURE_VIGILANCE, "identity_construction"
    ) is True


def test_dropped_low_diagonal_blend_into_vigilance():
    """POSTURE_BLEND × identity_construction (VIGILANCE_ACTIVATING) → LOW."""
    assert passes_mechanism_fluency(
        POSTURE_BLEND, "identity_construction"
    ) is False


def test_dropped_low_diagonal_vigilance_into_blend():
    """POSTURE_VIGILANCE × mimetic_desire (BLEND_COMPATIBLE) → LOW."""
    assert passes_mechanism_fluency(
        POSTURE_VIGILANCE, "mimetic_desire"
    ) is False


def test_passes_neutral_posture_any_mechanism():
    """POSTURE_NEUTRAL × any → MID → eligible."""
    assert passes_mechanism_fluency(POSTURE_NEUTRAL, "mimetic_desire") is True
    assert passes_mechanism_fluency(
        POSTURE_NEUTRAL, "identity_construction"
    ) is True


def test_passes_unknown_posture_pass_through():
    """POSTURE_UNKNOWN → no-signal pass-through (eligible)."""
    assert passes_mechanism_fluency(
        POSTURE_UNKNOWN, "identity_construction"
    ) is True


def test_passes_none_posture_pass_through():
    """posture=None → no-signal pass-through (eligible)."""
    assert passes_mechanism_fluency(None, "identity_construction") is True


def test_passes_unknown_mechanism_soft_fail_mid():
    """Unknown mechanism name → MID by soft-fail → eligible."""
    assert passes_mechanism_fluency(POSTURE_BLEND, "xyz_nonexistent") is True


def test_threshold_parameter_respected():
    """Setting a high threshold makes everything fail."""
    assert passes_mechanism_fluency(
        POSTURE_BLEND, "mimetic_desire", threshold=0.99,
    ) is False


def test_threshold_zero_passes_everything():
    """threshold=0 makes even LOW combinations pass."""
    assert passes_mechanism_fluency(
        POSTURE_BLEND, "identity_construction", threshold=0.0,
    ) is True


# -----------------------------------------------------------------------------
# apply_mechanism_fluency_floor — bulk filter
# -----------------------------------------------------------------------------


def test_apply_drops_low_keeps_high():
    """Mixed LOW + HIGH input — LOW dropped, HIGH kept."""
    scores = {
        "mimetic_desire": 0.7,         # POSTURE_BLEND → HIGH → keep
        "identity_construction": 0.6,  # POSTURE_BLEND → LOW  → drop
        "embodied_cognition": 0.5,     # POSTURE_BLEND → HIGH → keep
    }
    result = apply_mechanism_fluency_floor(
        mechanism_scores=scores,
        posture=POSTURE_BLEND,
    )
    assert isinstance(result, MechanismFluencyResult)
    assert "identity_construction" not in result.filtered_scores
    assert result.filtered_scores["mimetic_desire"] == 0.7
    assert result.filtered_scores["embodied_cognition"] == 0.5
    assert result.n_dropped == 1
    assert result.n_eligible == 2
    assert result.dropped_mechanisms == ["identity_construction"]
    assert result.all_dropped is False
    assert result.bypassed is False


def test_apply_keeps_all_mid_posture():
    """POSTURE_NEUTRAL → all MID → all kept."""
    scores = {
        "mimetic_desire": 0.4,
        "identity_construction": 0.6,
    }
    result = apply_mechanism_fluency_floor(
        mechanism_scores=scores,
        posture=POSTURE_NEUTRAL,
    )
    assert result.filtered_scores == scores
    assert result.n_dropped == 0
    assert result.n_eligible == 2
    assert result.bypassed is False


def test_apply_unknown_posture_pass_through():
    """POSTURE_UNKNOWN → pass-through, no drops, not bypassed."""
    scores = {
        "mimetic_desire": 0.4,
        "identity_construction": 0.6,
    }
    result = apply_mechanism_fluency_floor(
        mechanism_scores=scores,
        posture=POSTURE_UNKNOWN,
    )
    assert result.filtered_scores is scores  # identity preserved
    assert result.n_dropped == 0
    assert result.bypassed is False
    assert result.all_dropped is False


def test_apply_none_posture_pass_through():
    """posture=None → pass-through (no signal)."""
    scores = {"mimetic_desire": 0.4, "identity_construction": 0.6}
    result = apply_mechanism_fluency_floor(
        mechanism_scores=scores,
        posture=None,
    )
    assert result.filtered_scores is scores
    assert result.n_dropped == 0
    assert result.bypassed is False


def test_apply_empty_input_pass_through():
    """Empty scores → empty result, no drops."""
    result = apply_mechanism_fluency_floor(
        mechanism_scores={},
        posture=POSTURE_BLEND,
    )
    assert result.filtered_scores == {}
    assert result.n_dropped == 0
    assert result.n_eligible == 0
    assert result.bypassed is False
    assert result.all_dropped is False


def test_apply_all_low_bypassed_and_flagged(caplog):
    """All-mechanisms-LOW → bypassed=True, all_dropped=True, input intact."""
    scores = {
        "identity_construction": 0.6,  # POSTURE_BLEND → LOW
        "attention_dynamics": 0.5,     # POSTURE_BLEND → LOW
    }
    with caplog.at_level(logging.WARNING):
        result = apply_mechanism_fluency_floor(
            mechanism_scores=scores,
            posture=POSTURE_BLEND,
        )
    assert result.filtered_scores is scores  # input preserved on bypass
    assert result.all_dropped is True
    assert result.bypassed is True
    assert result.n_dropped == 2
    assert result.n_eligible == 2  # full input still eligible (bypassed)
    assert "all" in caplog.text.lower()
    assert "below floor" in caplog.text.lower()


def test_apply_unknown_mechanism_soft_fail_kept():
    """Unknown mechanism → MID by soft-fail → kept."""
    scores = {
        "xyz_nonexistent": 0.5,      # unknown → MID → keep
        "identity_construction": 0.6,  # POSTURE_BLEND → LOW → drop
    }
    result = apply_mechanism_fluency_floor(
        mechanism_scores=scores,
        posture=POSTURE_BLEND,
    )
    assert "xyz_nonexistent" in result.filtered_scores
    assert "identity_construction" not in result.filtered_scores
    assert result.n_dropped == 1


def test_apply_threshold_override():
    """Override threshold to 0.99 → all dropped → bypassed (since all-drop)."""
    scores = {"mimetic_desire": 0.7, "embodied_cognition": 0.5}
    result = apply_mechanism_fluency_floor(
        mechanism_scores=scores,
        posture=POSTURE_BLEND,
        threshold=0.99,
    )
    # Both would drop; bypassed semantic kicks in on all-drop
    assert result.all_dropped is True
    assert result.bypassed is True
    assert result.filtered_scores is scores


def test_apply_threshold_zero_keeps_everything():
    """Override threshold to 0 → nothing dropped."""
    scores = {
        "identity_construction": 0.6,
        "mimetic_desire": 0.7,
    }
    result = apply_mechanism_fluency_floor(
        mechanism_scores=scores,
        posture=POSTURE_BLEND,
        threshold=0.0,
    )
    assert result.filtered_scores == scores
    assert result.n_dropped == 0
    assert result.n_eligible == 2


def test_apply_dropped_mechanisms_order_preserved():
    """dropped_mechanisms list preserves input dict order."""
    scores = {
        "mimetic_desire": 0.7,            # keep
        "attention_dynamics": 0.5,        # drop (1st LOW)
        "embodied_cognition": 0.4,        # keep
        "identity_construction": 0.3,     # drop (2nd LOW)
    }
    result = apply_mechanism_fluency_floor(
        mechanism_scores=scores,
        posture=POSTURE_BLEND,
    )
    assert result.dropped_mechanisms == [
        "attention_dynamics",
        "identity_construction",
    ]


def test_apply_accounting_consistent():
    """n_dropped + n_eligible == input size on the non-bypass path."""
    scores = {
        "mimetic_desire": 0.7,          # keep
        "identity_construction": 0.5,   # drop
        "attention_dynamics": 0.4,      # drop
        "embodied_cognition": 0.6,      # keep
    }
    result = apply_mechanism_fluency_floor(
        mechanism_scores=scores,
        posture=POSTURE_BLEND,
    )
    assert result.bypassed is False
    assert result.n_dropped + result.n_eligible == len(scores)
    assert len(result.filtered_scores) == result.n_eligible


def test_apply_returns_frozen_dataclass():
    """MechanismFluencyResult is frozen — caller cannot mutate result fields."""
    scores = {"mimetic_desire": 0.5}
    result = apply_mechanism_fluency_floor(
        mechanism_scores=scores,
        posture=POSTURE_BLEND,
    )
    with pytest.raises(Exception):  # FrozenInstanceError
        result.n_dropped = 99  # type: ignore[misc]
