"""Pin F4 — creative-side primary metaphor scoring + creative×buyer alignment.

Discipline anchors:
    - Reuses canonical PRIMARY_METAPHOR_AXIS_NAMES (same 8 axes as
      F1, F2, page-side). F1/F2/F3/F4 all live in the same axis
      space — pin so a future refactor can't silently fragment.
    - Soft-fail on every error path (empty input, Claude exception,
      malformed response, parse failure). Same A14 discipline as F1/F2.
    - Identifier fields: creative_id + variant_id + brand_id +
      decision_id. The decision_id link makes the bundle joinable
      back to the cascade decision that produced it (so a future
      adjudicator can correlate creative-side metaphor delivery
      with the cascade's intended mechanism × archetype).
    - Creative × buyer alignment uses identical math to F3 (cosine
      gated by min-confidence). DIFFERENT bundle types, IDENTICAL
      axis space — pin both.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from adam.intelligence.buyer_metaphor_scoring import BuyerMetaphorBundle
from adam.intelligence.creative_metaphor_scoring import (
    CreativeBuyerAlignmentResult,
    CreativeMetaphorBundle,
    compute_creative_buyer_alignment,
    score_creative_metaphors,
    to_creative_feature_metaphor_fields,
)
from adam.intelligence.pages.claude_feature_scoring import (
    PRIMARY_METAPHOR_AXIS_NAMES,
)


_NUM_AXES = len(PRIMARY_METAPHOR_AXIS_NAMES)


# =============================================================================
# Bundle shape — same axis space as F1/F2
# =============================================================================


def test_creative_bundle_uses_canonical_axis_count():
    bundle = CreativeMetaphorBundle.neutral()
    assert len(bundle.primary_metaphor_axes) == _NUM_AXES


def test_bundle_carries_creative_specific_identifiers():
    """creative_id + variant_id + brand_id + decision_id — joinable
    back to the cascade decision that produced the creative."""
    bundle = CreativeMetaphorBundle(
        creative_id="cr_42", variant_id="v1",
        brand_id="luxy", decision_id="d_xyz",
    )
    assert bundle.creative_id == "cr_42"
    assert bundle.variant_id == "v1"
    assert bundle.brand_id == "luxy"
    assert bundle.decision_id == "d_xyz"


# =============================================================================
# Validation
# =============================================================================


def test_bundle_validate_passes_neutral():
    CreativeMetaphorBundle.neutral().validate()


def test_bundle_validate_rejects_wrong_axis_count():
    bundle = CreativeMetaphorBundle(primary_metaphor_axes=[0.5, 0.5])
    with pytest.raises(ValueError, match="primary_metaphor_axes length"):
        bundle.validate()


def test_bundle_validate_rejects_axis_out_of_range():
    bundle = CreativeMetaphorBundle(
        primary_metaphor_axes=[1.5] + [0.0] * 7,
    )
    with pytest.raises(ValueError, match="warmth"):
        bundle.validate()


def test_bundle_validate_rejects_density_out_of_range():
    bundle = CreativeMetaphorBundle(metaphor_density=-0.1)
    with pytest.raises(ValueError, match="density"):
        bundle.validate()


def test_bundle_validate_rejects_confidence_out_of_range():
    bundle = CreativeMetaphorBundle(confidence=1.1)
    with pytest.raises(ValueError, match="confidence"):
        bundle.validate()


# =============================================================================
# from_claude_response
# =============================================================================


def test_from_claude_response_parses_wrapped_shape():
    response = {
        "primary_metaphor": {
            "density": 0.6,
            "axes": {
                "warmth": 0.7, "distance": 0.3, "vertical": 0.5,
                "solidity": 0.6, "containment": 0.4, "force": 0.5,
                "path": 0.8, "closeness": 0.5,
            },
            "confidence": 0.75,
        }
    }
    bundle = CreativeMetaphorBundle.from_claude_response(
        response, creative_id="cr1", variant_id="v0",
    )
    assert bundle.metaphor_density == 0.6
    assert bundle.confidence == 0.75
    assert bundle.primary_metaphor_axes[6] == 0.8  # path
    assert bundle.creative_id == "cr1"


def test_from_claude_response_clamps_out_of_range_axes():
    response = {
        "primary_metaphor": {
            "density": 1.5,
            "axes": {
                "warmth": -0.5, "distance": 2.0, "vertical": 0.5,
                "solidity": 0.5, "containment": 0.5, "force": 0.5,
                "path": 0.5, "closeness": 0.5,
            },
            "confidence": 0.7,
        }
    }
    bundle = CreativeMetaphorBundle.from_claude_response(response)
    assert bundle.metaphor_density == 1.0
    assert bundle.primary_metaphor_axes[0] == 0.0
    assert bundle.primary_metaphor_axes[1] == 1.0


def test_from_claude_response_raises_on_missing_axes():
    with pytest.raises(ValueError, match="axes"):
        CreativeMetaphorBundle.from_claude_response(
            {"primary_metaphor": {"density": 0.5}}
        )


def test_from_claude_response_raises_on_non_dict():
    with pytest.raises(ValueError, match="not a dict"):
        CreativeMetaphorBundle.from_claude_response("not a dict")


# =============================================================================
# score_creative_metaphors — soft-fail on every error path
# =============================================================================


@pytest.mark.asyncio
async def test_score_all_empty_inputs_returns_neutral():
    client = MagicMock()
    client.complete_structured = AsyncMock()
    bundle = await score_creative_metaphors(
        client, headline="", body="", cta="",
    )
    assert bundle.confidence == 0.0
    client.complete_structured.assert_not_called()


@pytest.mark.asyncio
async def test_score_only_headline_calls_claude():
    """A creative can be just a headline — short copy is still copy.
    Don't gate the Claude call on having all three fields."""
    client = MagicMock()
    client.complete_structured = AsyncMock(return_value={
        "primary_metaphor": {
            "density": 0.0,
            "axes": {n: 0.0 for n in PRIMARY_METAPHOR_AXIS_NAMES},
            "confidence": 0.2,
        }
    })
    await score_creative_metaphors(
        client, headline="Quietly arrived", body="", cta="",
    )
    client.complete_structured.assert_called_once()


@pytest.mark.asyncio
async def test_score_claude_exception_returns_neutral():
    client = MagicMock()
    client.complete_structured = AsyncMock(
        side_effect=ConnectionError("api down"),
    )
    bundle = await score_creative_metaphors(
        client, headline="real headline", body="real body",
    )
    assert bundle.confidence == 0.0


@pytest.mark.asyncio
async def test_score_empty_response_returns_neutral():
    client = MagicMock()
    client.complete_structured = AsyncMock(return_value=None)
    bundle = await score_creative_metaphors(
        client, headline="real headline",
    )
    assert bundle.confidence == 0.0


@pytest.mark.asyncio
async def test_score_malformed_response_returns_neutral():
    client = MagicMock()
    client.complete_structured = AsyncMock(
        return_value={"unrelated_key": "garbage"},
    )
    bundle = await score_creative_metaphors(
        client, headline="real headline",
    )
    assert bundle.confidence == 0.0


@pytest.mark.asyncio
async def test_score_happy_path_validates():
    client = MagicMock()
    client.complete_structured = AsyncMock(return_value={
        "primary_metaphor": {
            "density": 0.7,
            "axes": {
                "warmth": 0.6, "distance": 0.2, "vertical": 0.5,
                "solidity": 0.4, "containment": 0.3, "force": 0.4,
                "path": 0.8, "closeness": 0.7,
            },
            "confidence": 0.85,
        }
    })
    bundle = await score_creative_metaphors(
        client,
        headline="Discover the road less traveled",
        body="Bespoke chauffeur service for those who choose the journey",
        cta="Begin your route",
        creative_id="cr_42", variant_id="v1",
        brand_id="luxy", decision_id="d_xyz",
    )
    bundle.validate()
    assert bundle.creative_id == "cr_42"
    assert bundle.confidence == 0.85
    assert bundle.primary_metaphor_axes[6] == 0.8  # path — high


@pytest.mark.asyncio
async def test_score_truncates_long_inputs_per_field():
    client = MagicMock()
    client.complete_structured = AsyncMock(return_value={
        "primary_metaphor": {
            "density": 0.0,
            "axes": {n: 0.0 for n in PRIMARY_METAPHOR_AXIS_NAMES},
            "confidence": 0.0,
        }
    })
    huge = "X" * 100_000
    await score_creative_metaphors(
        client, headline=huge, body=huge, cta=huge,
        max_chars_per_field=200,
    )
    sent_prompt = client.complete_structured.call_args.kwargs["prompt"]
    assert huge not in sent_prompt
    # 3 fields × 200 chars + scaffold overhead — bounded
    assert len(sent_prompt) < 3000


# =============================================================================
# Creative × buyer alignment — same axis space, same math as F3
# =============================================================================


def _creative(axes_path: float = 0.7, density: float = 0.5,
              confidence: float = 0.8) -> CreativeMetaphorBundle:
    axes = [0.0] * _NUM_AXES
    axes[6] = axes_path  # path axis
    return CreativeMetaphorBundle(
        primary_metaphor_axes=axes,
        metaphor_density=density,
        confidence=confidence,
        creative_id="cr1", variant_id="v0",
        brand_id="luxy",
    )


def _buyer(axes_path: float = 0.7, density: float = 0.5,
           confidence: float = 0.8) -> BuyerMetaphorBundle:
    axes = [0.0] * _NUM_AXES
    axes[6] = axes_path
    return BuyerMetaphorBundle(
        primary_metaphor_axes=axes,
        metaphor_density=density,
        confidence=confidence,
        buyer_id="b1",
    )


def test_alignment_neutral_when_creative_missing():
    result = compute_creative_buyer_alignment(None, _buyer())
    assert result.metaphor_alignment == 0.0


def test_alignment_neutral_when_buyer_missing():
    result = compute_creative_buyer_alignment(_creative(), None)
    assert result.metaphor_alignment == 0.0


def test_alignment_neutral_when_either_zero_confidence():
    """Don't claim alignment without evidence on BOTH sides."""
    creative = _creative(confidence=0.0)
    result = compute_creative_buyer_alignment(creative, _buyer())
    assert result.metaphor_alignment == 0.0
    assert result.creative_id == "cr1"

    buyer_zero = _buyer(confidence=0.0)
    result2 = compute_creative_buyer_alignment(_creative(), buyer_zero)
    assert result2.metaphor_alignment == 0.0


def test_alignment_high_when_axes_match():
    """Same path-heavy axis vectors → cosine 1 → alignment = min(conf)."""
    result = compute_creative_buyer_alignment(_creative(), _buyer())
    assert result.cosine_similarity == pytest.approx(1.0)
    assert result.metaphor_alignment == pytest.approx(0.8)


def test_alignment_zero_when_axes_orthogonal():
    """Creative reaches for path; buyer expresses warmth — orthogonal."""
    creative = _creative(axes_path=0.8)
    buyer_axes = [0.0] * _NUM_AXES
    buyer_axes[0] = 0.8  # warmth
    buyer = BuyerMetaphorBundle(
        primary_metaphor_axes=buyer_axes,
        metaphor_density=0.5, confidence=0.8,
        buyer_id="b1",
    )
    result = compute_creative_buyer_alignment(creative, buyer)
    assert result.cosine_similarity == pytest.approx(0.0)
    assert result.metaphor_alignment == pytest.approx(0.0)


def test_alignment_gated_by_min_confidence():
    """Pin: alignment = cosine × min(creative_conf, buyer_conf).
    Same min-evidence rule as F3."""
    creative = _creative(confidence=0.5)
    buyer = _buyer(confidence=0.9)
    result = compute_creative_buyer_alignment(creative, buyer)
    assert result.cosine_similarity == pytest.approx(1.0)
    assert result.confidence == 0.5
    assert result.metaphor_alignment == pytest.approx(0.5)


def test_alignment_density_NOT_baked_into_scalar():
    """Same discipline as F3: density agreement is a separate
    diagnostic, NOT pre-composed into the alignment scalar."""
    creative = _creative(density=0.2)
    buyer = _buyer(density=0.8)
    result = compute_creative_buyer_alignment(creative, buyer)
    # cosine = 1.0, confidence_floor = 0.8, density_agreement = 0.4
    # alignment = cosine × confidence_floor = 0.8 (NOT × density)
    assert result.metaphor_alignment == pytest.approx(0.8)
    assert result.density_agreement == pytest.approx(0.4)


def test_alignment_per_axis_closeness_in_canonical_order():
    creative_axes = [0.0] * _NUM_AXES
    creative_axes[6] = 0.7
    buyer_axes = [0.0] * _NUM_AXES
    buyer_axes[6] = 0.5
    creative = CreativeMetaphorBundle(
        primary_metaphor_axes=creative_axes,
        metaphor_density=0.5, confidence=0.8,
    )
    buyer = BuyerMetaphorBundle(
        primary_metaphor_axes=buyer_axes,
        metaphor_density=0.5, confidence=0.8,
    )
    result = compute_creative_buyer_alignment(creative, buyer)
    # path: 1 - |0.7 - 0.5| = 0.8 (position 6)
    assert result.per_axis_closeness[6] == pytest.approx(0.8)
    # All others match (both 0)
    for i in range(_NUM_AXES):
        if i != 6:
            assert result.per_axis_closeness[i] == pytest.approx(1.0)


def test_alignment_neutral_on_axis_count_mismatch():
    bad_creative = CreativeMetaphorBundle(
        primary_metaphor_axes=[0.5, 0.5],
        metaphor_density=0.5, confidence=0.8,
    )
    result = compute_creative_buyer_alignment(bad_creative, _buyer())
    assert result.metaphor_alignment == 0.0


# =============================================================================
# blend_fit adapter
# =============================================================================


def test_to_creative_feature_metaphor_fields_returns_canonical_keys():
    """The adapter produces the metaphor portion of CreativeFeatureBundle's
    field set (defined in adam/intelligence/blend_fit.py)."""
    bundle = CreativeMetaphorBundle(
        primary_metaphor_axes=[0.5] * _NUM_AXES,
        metaphor_density=0.6,
        confidence=0.7,
    )
    fields = to_creative_feature_metaphor_fields(bundle)
    assert set(fields.keys()) == {
        "primary_metaphor_density",
        "primary_metaphor_axes",
        "primary_metaphor_confidence",
    }
    assert fields["primary_metaphor_density"] == 0.6
    assert fields["primary_metaphor_confidence"] == 0.7
    assert len(fields["primary_metaphor_axes"]) == _NUM_AXES


def test_to_creative_feature_field_keys_match_blend_fit():
    """Pin: the field keys match blend_fit.CreativeFeatureBundle's
    metaphor fields. A drift in either side breaks the splice."""
    from adam.intelligence.blend_fit import CreativeFeatureBundle

    expected_keys = {"primary_metaphor_density", "primary_metaphor_axes",
                     "primary_metaphor_confidence"}
    bundle_fields = set(CreativeFeatureBundle.__dataclass_fields__.keys())
    # All our adapter keys must exist on CreativeFeatureBundle
    for key in expected_keys:
        assert key in bundle_fields, (
            f"blend_fit.CreativeFeatureBundle no longer has {key} — "
            f"F4 adapter splice broken"
        )
