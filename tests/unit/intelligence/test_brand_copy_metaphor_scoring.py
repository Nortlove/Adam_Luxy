"""Pin F2 — brand-copy-side primary metaphor scoring on 8 axes.

Discipline anchors:
    - Reuses PRIMARY_METAPHOR_AXIS_NAMES (same as F1 + page-side) so
      buyer × brand_copy alignment in F3 is meaningful.
    - Soft-fail on every error path (empty, exception, malformed).
    - Brand-copy semantics: ATTEMPTED ACTIVATION (what the brand is
      reaching for), distinct from F1's TRAIT EXPRESSION and
      page-side's CONTEXTUAL PRIMING. The system prompt names this
      explicitly.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from adam.intelligence.brand_copy_metaphor_scoring import (
    BrandCopyMetaphorBundle,
    score_brand_copy_metaphors,
)
from adam.intelligence.pages.claude_feature_scoring import (
    PRIMARY_METAPHOR_AXIS_NAMES,
)


# -----------------------------------------------------------------------------
# Shared axis space — same canonical 8 axes as F1 / page-side
# -----------------------------------------------------------------------------


def test_brand_bundle_uses_canonical_axis_count():
    """Length must match the canonical 8 — F3's bilateral dot product
    requires both halves in the same axis space."""
    bundle = BrandCopyMetaphorBundle.neutral()
    assert len(bundle.primary_metaphor_axes) == len(PRIMARY_METAPHOR_AXIS_NAMES)


# -----------------------------------------------------------------------------
# Bundle validation
# -----------------------------------------------------------------------------


def test_bundle_validate_passes_neutral():
    BrandCopyMetaphorBundle.neutral().validate()


def test_bundle_validate_rejects_wrong_axis_count():
    bundle = BrandCopyMetaphorBundle(primary_metaphor_axes=[0.5, 0.5, 0.5])
    with pytest.raises(ValueError, match="primary_metaphor_axes length"):
        bundle.validate()


def test_bundle_validate_rejects_axis_out_of_range():
    bundle = BrandCopyMetaphorBundle(
        primary_metaphor_axes=[1.5] + [0.0] * 7,
    )
    with pytest.raises(ValueError, match="warmth"):
        bundle.validate()


def test_bundle_validate_rejects_density_out_of_range():
    bundle = BrandCopyMetaphorBundle(metaphor_density=-0.1)
    with pytest.raises(ValueError, match="density"):
        bundle.validate()


def test_bundle_validate_rejects_confidence_out_of_range():
    bundle = BrandCopyMetaphorBundle(confidence=1.5)
    with pytest.raises(ValueError, match="confidence"):
        bundle.validate()


def test_bundle_carries_asin_and_brand_id():
    """The bundle must carry both asin (Amazon-style) and brand_id
    (StackAdapt-style) so downstream consumers can route by either."""
    bundle = BrandCopyMetaphorBundle(asin="lux_luxy_ride", brand_id="luxy")
    assert bundle.asin == "lux_luxy_ride"
    assert bundle.brand_id == "luxy"


# -----------------------------------------------------------------------------
# from_claude_response — wrapped + flat shapes
# -----------------------------------------------------------------------------


def test_from_claude_response_parses_wrapped_shape():
    response = {
        "primary_metaphor": {
            "density": 0.7,
            "axes": {
                "warmth": 0.8, "distance": 0.2, "vertical": 0.6,
                "solidity": 0.5, "containment": 0.4, "force": 0.3,
                "path": 0.7, "closeness": 0.5,
            },
            "confidence": 0.85,
        }
    }
    bundle = BrandCopyMetaphorBundle.from_claude_response(
        response, asin="lux_luxy_ride", brand_id="luxy",
    )
    assert bundle.metaphor_density == 0.7
    assert bundle.confidence == 0.85
    assert bundle.primary_metaphor_axes[0] == 0.8  # warmth
    assert bundle.asin == "lux_luxy_ride"
    assert bundle.brand_id == "luxy"


def test_from_claude_response_parses_flat_shape():
    response = {
        "density": 0.3,
        "axes": {n: 0.0 for n in PRIMARY_METAPHOR_AXIS_NAMES},
        "confidence": 0.4,
    }
    bundle = BrandCopyMetaphorBundle.from_claude_response(response)
    assert bundle.metaphor_density == 0.3


def test_from_claude_response_clamps_out_of_range_axes():
    response = {
        "primary_metaphor": {
            "density": 1.5,  # over 1
            "axes": {
                "warmth": -0.5, "distance": 2.0, "vertical": 0.5,
                "solidity": 0.5, "containment": 0.5, "force": 0.5,
                "path": 0.5, "closeness": 0.5,
            },
            "confidence": 0.7,
        }
    }
    bundle = BrandCopyMetaphorBundle.from_claude_response(response)
    assert bundle.metaphor_density == 1.0
    assert bundle.primary_metaphor_axes[0] == 0.0  # warmth clamped
    assert bundle.primary_metaphor_axes[1] == 1.0  # distance clamped


def test_from_claude_response_raises_on_missing_axes():
    response = {"primary_metaphor": {"density": 0.5}}
    with pytest.raises(ValueError, match="axes"):
        BrandCopyMetaphorBundle.from_claude_response(response)


def test_from_claude_response_raises_on_non_dict():
    with pytest.raises(ValueError, match="not a dict"):
        BrandCopyMetaphorBundle.from_claude_response(["not", "a", "dict"])


def test_from_claude_response_zero_default_for_missing_axis():
    """Some axes might be omitted by Claude; default to 0.0 (no signal
    for that axis), matching F1 behavior."""
    response = {
        "primary_metaphor": {
            "density": 0.5,
            "axes": {"warmth": 0.7},  # only one axis
            "confidence": 0.4,
        }
    }
    bundle = BrandCopyMetaphorBundle.from_claude_response(response)
    assert bundle.primary_metaphor_axes[0] == 0.7  # warmth
    assert all(v == 0.0 for v in bundle.primary_metaphor_axes[1:])


# -----------------------------------------------------------------------------
# score_brand_copy_metaphors — soft-fail on every error path
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_score_all_empty_inputs_returns_neutral():
    """All three input fields empty → neutral. Claude not called."""
    client = MagicMock()
    client.complete_structured = AsyncMock()
    bundle = await score_brand_copy_metaphors(
        client, title="", features="", description="",
    )
    assert bundle.confidence == 0.0
    client.complete_structured.assert_not_called()


@pytest.mark.asyncio
async def test_score_only_title_present_calls_claude():
    """When at least one field has content, Claude IS called.
    Brand copy can be just a title; missing features/description
    shouldn't gate the call."""
    client = MagicMock()
    client.complete_structured = AsyncMock(return_value={
        "primary_metaphor": {
            "density": 0.0,
            "axes": {n: 0.0 for n in PRIMARY_METAPHOR_AXIS_NAMES},
            "confidence": 0.2,
        }
    })
    bundle = await score_brand_copy_metaphors(
        client, title="LUXY Ride", features="", description="",
    )
    client.complete_structured.assert_called_once()
    assert bundle is not None


@pytest.mark.asyncio
async def test_score_claude_exception_returns_neutral():
    client = MagicMock()
    client.complete_structured = AsyncMock(
        side_effect=ConnectionError("api down"),
    )
    bundle = await score_brand_copy_metaphors(
        client, title="title", description="real description",
    )
    assert bundle.confidence == 0.0


@pytest.mark.asyncio
async def test_score_empty_response_returns_neutral():
    client = MagicMock()
    client.complete_structured = AsyncMock(return_value=None)
    bundle = await score_brand_copy_metaphors(
        client, title="title", description="real description",
    )
    assert bundle.confidence == 0.0


@pytest.mark.asyncio
async def test_score_malformed_response_returns_neutral():
    client = MagicMock()
    client.complete_structured = AsyncMock(
        return_value={"unrelated_key": "garbage"}
    )
    bundle = await score_brand_copy_metaphors(
        client, title="title", description="description",
    )
    assert bundle.confidence == 0.0


@pytest.mark.asyncio
async def test_score_happy_path_returns_validated_bundle():
    client = MagicMock()
    client.complete_structured = AsyncMock(return_value={
        "primary_metaphor": {
            "density": 0.65,
            "axes": {
                "warmth": 0.6, "distance": 0.3, "vertical": 0.7,
                "solidity": 0.8, "containment": 0.5, "force": 0.4,
                "path": 0.7, "closeness": 0.3,
            },
            "confidence": 0.82,
        }
    })
    bundle = await score_brand_copy_metaphors(
        client,
        title="LUXY Ride: Bespoke chauffeur service",
        features="Premium fleet | Privacy-first | On-demand",
        description="Discreet, quietly arrived. The chauffeur for those who already know.",
        asin="lux_luxy_ride",
        brand_id="luxy",
    )
    assert bundle.confidence == 0.82
    assert bundle.metaphor_density == 0.65
    assert bundle.asin == "lux_luxy_ride"
    assert bundle.brand_id == "luxy"
    # Validate — must not raise
    bundle.validate()


@pytest.mark.asyncio
async def test_score_truncates_long_inputs():
    """Each field is independently truncated at max_chars."""
    client = MagicMock()
    client.complete_structured = AsyncMock(return_value={
        "primary_metaphor": {
            "density": 0.0,
            "axes": {n: 0.0 for n in PRIMARY_METAPHOR_AXIS_NAMES},
            "confidence": 0.0,
        }
    })
    huge = "X" * 100_000
    await score_brand_copy_metaphors(
        client,
        title=huge, features=huge, description=huge,
        max_chars=500,
    )
    sent_prompt = client.complete_structured.call_args.kwargs["prompt"]
    # The full huge string should never appear in the prompt
    assert huge not in sent_prompt
    # Each truncated field of 500 chars; total prompt body shouldn't
    # exceed roughly 3 × 500 + scaffold
    assert len(sent_prompt) < 5000
