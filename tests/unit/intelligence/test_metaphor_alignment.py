"""Pin F3 — bilateral metaphor alignment metric.

Discipline anchors:
    - The metric uses STANDARD math (cosine similarity + min-evidence
      gating). No invented weights. Tests pin the formula behavior so
      a future refactor can't silently rewrite the alignment semantics.
    - confidence=0 on either side returns neutral. We do NOT claim
      alignment we don't have evidence for.
    - metaphor_alignment is a BILATERAL interaction value
      (buyer × brand_copy cosine), NOT a buyer trait. Tests pin that
      it does NOT appear in UNCERTAINTY_DIMENSIONS (which is the
      buyer-side trait list). A future refactor that mistakenly adds
      it there would cause type confusion across multiple brand
      encounters.
    - density_agreement is exposed as a separate diagnostic, NOT
      pre-composed into metaphor_alignment. Composition would bake
      in a specific weighting; downstream consumers compose as they
      need.
"""

from __future__ import annotations

import math

import pytest

from adam.intelligence.brand_copy_metaphor_scoring import BrandCopyMetaphorBundle
from adam.intelligence.buyer_metaphor_scoring import BuyerMetaphorBundle
from adam.intelligence.metaphor_alignment import (
    MetaphorAlignmentResult,
    _cosine_similarity,
    compute_metaphor_alignment,
)
from adam.intelligence.pages.claude_feature_scoring import (
    PRIMARY_METAPHOR_AXIS_NAMES,
)


_NUM_AXES = len(PRIMARY_METAPHOR_AXIS_NAMES)


# -----------------------------------------------------------------------------
# Cosine similarity correctness
# -----------------------------------------------------------------------------


def test_cosine_identical_unit_vectors_is_one():
    v = [0.5] * _NUM_AXES
    assert _cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_orthogonal_axes_is_zero():
    """Two vectors with non-overlapping axes (one nonzero on warmth,
    one nonzero on path) have zero dot product → cosine 0."""
    a = [0.0] * _NUM_AXES
    b = [0.0] * _NUM_AXES
    a[0] = 1.0  # warmth only
    b[6] = 1.0  # path only
    assert _cosine_similarity(a, b) == pytest.approx(0.0)


def test_cosine_zero_vector_returns_zero():
    """When either norm is zero, return 0 (not NaN, not undefined)."""
    zero = [0.0] * _NUM_AXES
    nonzero = [0.5] * _NUM_AXES
    assert _cosine_similarity(zero, nonzero) == 0.0
    assert _cosine_similarity(nonzero, zero) == 0.0
    assert _cosine_similarity(zero, zero) == 0.0


def test_cosine_length_mismatch_returns_zero():
    """Different-length vectors are schema drift; return 0 rather
    than raise — caller already has bundle-validation guards
    upstream."""
    assert _cosine_similarity([0.5, 0.5], [0.5] * 8) == 0.0


def test_cosine_handles_known_pythagorean_case():
    """Concrete check: vectors [1,0] and [1,1] (in 2-axis space) have
    cosine = 1/sqrt(2) ≈ 0.7071. Replicate via 8-axis padding."""
    a = [1.0, 0.0] + [0.0] * 6
    b = [1.0, 1.0] + [0.0] * 6
    expected = 1.0 / math.sqrt(2.0)
    assert _cosine_similarity(a, b) == pytest.approx(expected)


def test_cosine_clamped_to_unit_interval():
    """Floating-point can push slightly past 1; clamp to [0, 1]."""
    a = [0.5] * _NUM_AXES
    b = [0.5] * _NUM_AXES
    assert _cosine_similarity(a, b) <= 1.0


# -----------------------------------------------------------------------------
# compute_metaphor_alignment — neutral on every error path
# -----------------------------------------------------------------------------


def _bundle_buyer(axes_warmth: float = 0.7, density: float = 0.5,
                  confidence: float = 0.8) -> BuyerMetaphorBundle:
    axes = [0.0] * _NUM_AXES
    axes[0] = axes_warmth
    return BuyerMetaphorBundle(
        primary_metaphor_axes=axes,
        metaphor_density=density,
        confidence=confidence,
        buyer_id="b1",
    )


def _bundle_brand(axes_warmth: float = 0.7, density: float = 0.5,
                  confidence: float = 0.8) -> BrandCopyMetaphorBundle:
    axes = [0.0] * _NUM_AXES
    axes[0] = axes_warmth
    return BrandCopyMetaphorBundle(
        primary_metaphor_axes=axes,
        metaphor_density=density,
        confidence=confidence,
        asin="lux_luxy_ride",
        brand_id="luxy",
    )


def test_alignment_neutral_when_buyer_missing():
    result = compute_metaphor_alignment(None, _bundle_brand())
    assert result.metaphor_alignment == 0.0
    assert result.confidence == 0.0


def test_alignment_neutral_when_brand_missing():
    result = compute_metaphor_alignment(_bundle_buyer(), None)
    assert result.metaphor_alignment == 0.0


def test_alignment_neutral_when_buyer_zero_confidence():
    """Per discipline: don't claim alignment without evidence on
    BOTH sides."""
    buyer = _bundle_buyer(confidence=0.0)
    result = compute_metaphor_alignment(buyer, _bundle_brand())
    assert result.metaphor_alignment == 0.0
    assert result.buyer_id == "b1"


def test_alignment_neutral_when_brand_zero_confidence():
    brand = _bundle_brand(confidence=0.0)
    result = compute_metaphor_alignment(_bundle_buyer(), brand)
    assert result.metaphor_alignment == 0.0
    assert result.asin == "lux_luxy_ride"


# -----------------------------------------------------------------------------
# Confidence-floor gating
# -----------------------------------------------------------------------------


def test_alignment_gated_by_min_confidence():
    """If buyer confidence is 0.5 and brand confidence is 0.9, the
    alignment is gated by 0.5 — the WEAKER side. Not max, not mean,
    not product. min() is the standard min-evidence composition."""
    buyer = _bundle_buyer(axes_warmth=0.8, confidence=0.5)
    brand = _bundle_brand(axes_warmth=0.8, confidence=0.9)
    result = compute_metaphor_alignment(buyer, brand)
    # cosine of identical [0.8, 0,...,0] vectors = 1.0
    # alignment = 1.0 * min(0.5, 0.9) = 0.5
    assert result.cosine_similarity == pytest.approx(1.0)
    assert result.confidence == 0.5
    assert result.metaphor_alignment == pytest.approx(0.5)


# -----------------------------------------------------------------------------
# Cosine semantics — directional alignment
# -----------------------------------------------------------------------------


def test_alignment_high_when_axes_match():
    """Same axis vectors → cosine 1 → alignment = confidence_floor."""
    buyer = _bundle_buyer(axes_warmth=0.7, confidence=0.8)
    brand = _bundle_brand(axes_warmth=0.7, confidence=0.8)
    result = compute_metaphor_alignment(buyer, brand)
    assert result.cosine_similarity == pytest.approx(1.0)
    assert result.metaphor_alignment == pytest.approx(0.8)


def test_alignment_zero_when_axes_orthogonal():
    """Buyer reaches for warmth, brand reaches for path → 0 dot product."""
    buyer_axes = [0.0] * _NUM_AXES
    buyer_axes[0] = 0.8  # warmth
    brand_axes = [0.0] * _NUM_AXES
    brand_axes[6] = 0.8  # path
    buyer = BuyerMetaphorBundle(
        primary_metaphor_axes=buyer_axes,
        metaphor_density=0.5, confidence=0.8,
    )
    brand = BrandCopyMetaphorBundle(
        primary_metaphor_axes=brand_axes,
        metaphor_density=0.5, confidence=0.8,
    )
    result = compute_metaphor_alignment(buyer, brand)
    assert result.cosine_similarity == pytest.approx(0.0)
    assert result.metaphor_alignment == pytest.approx(0.0)


# -----------------------------------------------------------------------------
# Density agreement — separate diagnostic, NOT pre-composed
# -----------------------------------------------------------------------------


def test_density_agreement_one_when_densities_match():
    buyer = _bundle_buyer(density=0.6)
    brand = _bundle_brand(density=0.6)
    result = compute_metaphor_alignment(buyer, brand)
    assert result.density_agreement == pytest.approx(1.0)


def test_density_agreement_decreases_with_mismatch():
    buyer = _bundle_buyer(density=0.2)
    brand = _bundle_brand(density=0.8)
    result = compute_metaphor_alignment(buyer, brand)
    assert result.density_agreement == pytest.approx(1.0 - 0.6)


def test_density_agreement_NOT_baked_into_metaphor_alignment():
    """Pin: alignment scalar = cosine × confidence_floor, NOT
    cosine × confidence × density_agreement. Pre-composing density
    would bake in a specific weighting; consumers compose as needed."""
    buyer = _bundle_buyer(axes_warmth=0.7, density=0.2, confidence=0.8)
    brand = _bundle_brand(axes_warmth=0.7, density=0.8, confidence=0.8)
    result = compute_metaphor_alignment(buyer, brand)
    # cosine = 1.0, confidence_floor = 0.8, density_agreement = 0.4
    # If density were baked in: alignment ≈ 1.0 * 0.8 * 0.4 = 0.32
    # Without (correct): alignment = 1.0 * 0.8 = 0.8
    assert result.metaphor_alignment == pytest.approx(0.8)
    # density_agreement still exposed as diagnostic
    assert result.density_agreement == pytest.approx(0.4)


# -----------------------------------------------------------------------------
# Per-axis closeness diagnostic
# -----------------------------------------------------------------------------


def test_per_axis_closeness_in_canonical_order():
    """Per-axis closeness vector follows PRIMARY_METAPHOR_AXIS_NAMES
    order. Position [0] = warmth closeness, position [7] = closeness
    closeness, etc."""
    buyer = _bundle_buyer(axes_warmth=0.7)  # warmth=0.7, others=0
    brand = _bundle_brand(axes_warmth=0.5)  # warmth=0.5, others=0
    result = compute_metaphor_alignment(buyer, brand)
    # warmth: 1 - |0.7 - 0.5| = 0.8
    assert result.per_axis_closeness[0] == pytest.approx(0.8)
    # All other axes match (both 0) → closeness 1.0
    for i in range(1, _NUM_AXES):
        assert result.per_axis_closeness[i] == pytest.approx(1.0)


def test_per_axis_closeness_length_matches_axes():
    result = compute_metaphor_alignment(_bundle_buyer(), _bundle_brand())
    assert len(result.per_axis_closeness) == _NUM_AXES


# -----------------------------------------------------------------------------
# to_edge_dimensions — produces partial dict for cascade merge
# -----------------------------------------------------------------------------


def test_to_edge_dimensions_returns_metaphor_alignment_key():
    """The result renders into a dict consumable by the cascade's
    edge_dimensions merge. Pin the canonical key name so downstream
    consumers have a stable contract."""
    result = compute_metaphor_alignment(_bundle_buyer(), _bundle_brand())
    edge_dims = result.to_edge_dimensions()
    assert "metaphor_alignment" in edge_dims
    assert isinstance(edge_dims["metaphor_alignment"], float)


# -----------------------------------------------------------------------------
# Discipline anchor: metaphor_alignment is NOT in UNCERTAINTY_DIMENSIONS
# -----------------------------------------------------------------------------


def test_metaphor_alignment_NOT_in_buyer_uncertainty_dimensions():
    """metaphor_alignment is a BILATERAL interaction value (buyer ×
    brand_copy), NOT a buyer trait. Adding it to
    UNCERTAINTY_DIMENSIONS would cause type confusion: a buyer's
    posterior on this 'dim' would conflate alignment scores from
    multiple brand encounters. Pin the omission so a well-meaning
    refactor can't silently break the type semantics."""
    from adam.intelligence.information_value import UNCERTAINTY_DIMENSIONS
    assert "metaphor_alignment" not in UNCERTAINTY_DIMENSIONS


# -----------------------------------------------------------------------------
# Schema drift — wrong axis count returns neutral
# -----------------------------------------------------------------------------


def test_alignment_neutral_on_axis_count_mismatch():
    """If a bundle somehow has the wrong axis count, return neutral
    rather than raise. Bundle validation upstream catches most cases;
    this is the belt-and-suspenders for cascade-side calls."""
    bad_buyer = BuyerMetaphorBundle(
        primary_metaphor_axes=[0.5, 0.5],  # only 2 axes
        metaphor_density=0.5, confidence=0.8,
    )
    result = compute_metaphor_alignment(bad_buyer, _bundle_brand())
    assert result.metaphor_alignment == 0.0
