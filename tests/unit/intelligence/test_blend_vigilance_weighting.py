"""Pin F5 — blend-vs-vigilance strategic weighting.

Discipline anchors:
    - Default weights are HAND-SET per the attention-inversion platform
      commitment, NOT empirical. Tests pin both directions: canonical
      values match the default, AND a future change can't relabel them
      as 'empirically tuned' without an explicit edit visible in diff
      review.
    - Weighting is BOUNDED: blend ∈ [1.0, 1.25], vigilance ∈ [0.75, 1.0].
      Outside these bounds, the dataclass raises — preventing a
      configuration drift from turning the soft preference into a hard
      override.
    - Reuses C2's _category_for_cialdini helper so taxonomy translation
      lives in one place. Tests confirm the integration.
    - Unmapped mechanisms (no taxonomy entry) pass through unchanged —
      same conservative discipline as the constitution and route gate.
"""

from __future__ import annotations

import pytest

from adam.intelligence.blend_vigilance_weighting import (
    BlendVigilanceWeights,
    apply_blend_vigilance_weighting,
    explain_blend_vigilance_classification,
)
from adam.intelligence.mechanism_taxonomy import MechanismRouteCategory
from adam.intelligence.processing_depth_router import _category_for_cialdini


# -----------------------------------------------------------------------------
# Default weights — hand-set per platform commitment, NOT empirical
# -----------------------------------------------------------------------------


def test_default_weights_match_canonical_strategic_preference():
    """Default ±5% — blend boost 1.05, vigilance dampen 0.95. These
    encode the attention-inversion platform commitment. A future
    refactor that changes them without explicit intent breaks the
    documented commitment."""
    w = BlendVigilanceWeights()
    assert w.blend_boost == 1.05
    assert w.vigilance_dampen == 0.95
    assert w.unmapped_passthrough == 1.0


def test_weights_reject_inverted_direction():
    """blend_boost < 1.0 would invert the preference (blend mechanisms
    dampened) — the opposite of the platform commitment. Reject."""
    with pytest.raises(ValueError):
        BlendVigilanceWeights(blend_boost=0.95)


def test_weights_reject_excess_blend_boost():
    """blend_boost > 1.25 turns the soft preference into a hard
    override. The taxonomy commitment is to weight, not gate."""
    with pytest.raises(ValueError):
        BlendVigilanceWeights(blend_boost=2.0)


def test_weights_reject_inverted_vigilance():
    """vigilance_dampen > 1.0 would BOOST vigilance mechanisms — the
    opposite of the platform commitment."""
    with pytest.raises(ValueError):
        BlendVigilanceWeights(vigilance_dampen=1.05)


def test_weights_reject_excess_vigilance_dampen():
    """vigilance_dampen < 0.75 collapses vigilance scores too aggressively;
    use C2 hard gate instead for that intent."""
    with pytest.raises(ValueError):
        BlendVigilanceWeights(vigilance_dampen=0.5)


# -----------------------------------------------------------------------------
# Application — boost blend, dampen vigilance, passthrough unmapped
# -----------------------------------------------------------------------------


def test_blend_compatible_mechanism_score_increases():
    """A mechanism whose taxonomy category is BLEND_COMPATIBLE should
    have its score multiplied by blend_boost (default 1.05).
    Uses 'liking' which maps to atom 'mimetic_desire' (BLEND_COMPATIBLE)."""
    cat = _category_for_cialdini("liking")
    assert cat == MechanismRouteCategory.BLEND_COMPATIBLE, (
        f"taxonomy regression: liking should be BLEND_COMPATIBLE, got {cat}"
    )

    scores = {"liking": 0.8}
    out = apply_blend_vigilance_weighting(scores)
    assert out["liking"] == pytest.approx(0.8 * 1.05)


def test_vigilance_activating_mechanism_score_decreases():
    """A vigilance-activating mechanism gets dampened by 0.95.
    Uses 'authority' which maps to atom 'identity_construction'
    (VIGILANCE_ACTIVATING)."""
    cat = _category_for_cialdini("authority")
    assert cat == MechanismRouteCategory.VIGILANCE_ACTIVATING, (
        f"taxonomy regression: authority should be VIGILANCE_ACTIVATING, got {cat}"
    )

    scores = {"authority": 0.8}
    out = apply_blend_vigilance_weighting(scores)
    assert out["authority"] == pytest.approx(0.8 * 0.95)


def test_unmapped_mechanism_passes_through_unchanged():
    """A name not in MECHANISM_TO_ATOM (or whose atom isn't in the
    taxonomy) is unmapped — pass through at 1.0 multiplier."""
    scores = {"totally_unmapped_mechanism": 0.7}
    out = apply_blend_vigilance_weighting(scores)
    assert out["totally_unmapped_mechanism"] == 0.7


def test_known_taxonomy_coverage_gap_flagged():
    """KNOWN GAP: 4 of ADAM's 10 Cialdini mechanisms are unmapped in
    MECHANISM_TAXONOMY (social_proof, scarcity, reciprocity, commitment).
    Their atom counterparts ('social_proof', 'scarcity', 'regulatory_focus')
    are NOT taxonomy entries.

    F5 correctly handles this by passing them through unchanged. This
    test pins the gap so:
      - A future taxonomy expansion (adding atoms for those names) is
        caught by this test failing — that's the SIGNAL to update F5
        consumers.
      - A drift that adds them under the wrong category is caught
        immediately.
    """
    expected_unmapped = {"social_proof", "scarcity", "reciprocity", "commitment"}
    for mech in expected_unmapped:
        cat = _category_for_cialdini(mech)
        assert cat is None, (
            f"taxonomy coverage CHANGED for {mech}: now {cat}. "
            f"Update F5 tests + downstream consumers."
        )


def test_apply_returns_new_dict_not_mutating_input():
    """apply_* must return a NEW dict so callers that hold a reference
    to the unweighted scores see the original."""
    scores = {"social_proof": 0.8, "scarcity": 0.6}
    original = dict(scores)
    out = apply_blend_vigilance_weighting(scores)
    assert scores == original  # input unchanged
    assert out is not scores  # new dict


def test_apply_clips_to_unit_interval():
    """Even with the maximum 1.25 boost, no score should exceed 1.0.
    Uses 'liking' (BLEND_COMPATIBLE) so the boost actually fires."""
    scores = {"liking": 0.95}
    weights = BlendVigilanceWeights(blend_boost=1.25)
    out = apply_blend_vigilance_weighting(scores, weights)
    # 0.95 * 1.25 = 1.1875 → clipped to 1.0
    assert out["liking"] == 1.0


def test_apply_empty_scores_returns_empty():
    assert apply_blend_vigilance_weighting({}) == {}


# -----------------------------------------------------------------------------
# Composition with C2 — F5 weights run before, C2 gates after
# -----------------------------------------------------------------------------


def test_f5_weighting_composes_with_c2_gate_passthrough():
    """The cascade applies F5 weighting then C2 gate. After F5, scores
    are nudged but all still > 0. C2's gate then zeros incompatibles
    based on predicted depth. Pin: F5 leaves all scores positive
    (it doesn't zero anything itself), so the gate is C2's job alone."""
    scores = {"social_proof": 0.8, "scarcity": 0.6, "authority": 0.5}
    out = apply_blend_vigilance_weighting(scores)
    for mech, score in out.items():
        assert score > 0, f"F5 should never zero scores; {mech}={score}"


def test_relative_ordering_preserved_within_category():
    """Among mechanisms in the same category, relative ordering must
    be preserved by F5. Two blend-compatible mechanisms with scores
    A > B before F5 still have A > B after."""
    # liking and loss_aversion both BLEND_COMPATIBLE per taxonomy
    scores = {"liking": 0.7, "loss_aversion": 0.5}
    out = apply_blend_vigilance_weighting(scores)
    assert out["liking"] > out["loss_aversion"]


# -----------------------------------------------------------------------------
# Diagnostic explainer
# -----------------------------------------------------------------------------


def test_explain_returns_label_per_mechanism():
    scores = {"social_proof": 0.5, "scarcity": 0.5, "made_up_name": 0.5}
    labels = explain_blend_vigilance_classification(scores)
    assert set(labels.keys()) == set(scores.keys())
    assert labels["made_up_name"] == "unmapped"
    # social_proof / scarcity get blend / vigilance per taxonomy
    assert labels["social_proof"] in ("blend", "vigilance", "unmapped")
    assert labels["scarcity"] in ("blend", "vigilance", "unmapped")


# -----------------------------------------------------------------------------
# Custom weights flow through correctly
# -----------------------------------------------------------------------------


def test_custom_weights_used_when_provided():
    """Caller can override the defaults; the override takes effect."""
    custom = BlendVigilanceWeights(blend_boost=1.10, vigilance_dampen=0.90)
    # liking → BLEND, authority → VIGILANCE per actual taxonomy
    scores = {"liking": 0.5, "authority": 0.5}

    out = apply_blend_vigilance_weighting(scores, custom)

    assert out["liking"] == pytest.approx(0.5 * 1.10)
    assert out["authority"] == pytest.approx(0.5 * 0.90)
