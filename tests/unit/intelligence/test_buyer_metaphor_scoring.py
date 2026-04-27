"""Pin F1 — buyer-side primary metaphor scoring on 8 axes.

Discipline anchors:
    - Reuses PRIMARY_METAPHOR_AXIS_NAMES from claude_feature_scoring
      so buyer-side and page-side vectors live in the SAME 8-axis
      space. Pin this so a future refactor can't silently introduce
      a parallel axis vocabulary (which would break the bilateral
      edge metaphor dimension F3 will compute).
    - neutral() with confidence=0 is the honest output on every error
      path. Tests pin: empty input, Claude exception, parse failure,
      malformed response — all return neutral.
    - Aggregation excludes low-confidence bundles. A buyer who hasn't
      written enough scored reviews doesn't get a fabricated profile.
    - Buyer-side semantics (trait expression) differ from page-side
      (contextual priming). Same axes, different scoring question.
      The system prompt explicitly names this distinction.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from adam.intelligence.buyer_metaphor_scoring import (
    BuyerMetaphorBundle,
    aggregate_buyer_metaphor_axes,
    score_review_metaphors,
)
from adam.intelligence.pages.claude_feature_scoring import (
    PRIMARY_METAPHOR_AXIS_NAMES,
)


# -----------------------------------------------------------------------------
# Axis space — buyer-side and page-side share PRIMARY_METAPHOR_AXIS_NAMES
# -----------------------------------------------------------------------------


def test_buyer_bundle_uses_canonical_axis_count():
    """The bundle's axis vector must match the canonical 8 axes.
    A length mismatch would silently break dot-product comparisons
    when F3 ships."""
    bundle = BuyerMetaphorBundle.neutral()
    assert len(bundle.primary_metaphor_axes) == len(PRIMARY_METAPHOR_AXIS_NAMES)
    assert len(PRIMARY_METAPHOR_AXIS_NAMES) == 8


def test_canonical_axis_names_unchanged():
    """Pin the 8 canonical Lakoff-Johnson axes. A drift here would
    break the buyer×page metaphor dot-product F3 will compute."""
    assert set(PRIMARY_METAPHOR_AXIS_NAMES) == {
        "warmth", "distance", "vertical", "solidity",
        "containment", "force", "path", "closeness",
    }


# -----------------------------------------------------------------------------
# Bundle validation
# -----------------------------------------------------------------------------


def test_bundle_validate_passes_canonical_neutral():
    BuyerMetaphorBundle.neutral().validate()  # must not raise


def test_bundle_validate_rejects_wrong_axis_count():
    bundle = BuyerMetaphorBundle(primary_metaphor_axes=[0.5, 0.5])
    with pytest.raises(ValueError, match="primary_metaphor_axes length"):
        bundle.validate()


def test_bundle_validate_rejects_axis_out_of_range():
    bundle = BuyerMetaphorBundle(
        primary_metaphor_axes=[1.5] + [0.0] * 7,
    )
    with pytest.raises(ValueError, match="warmth"):
        bundle.validate()


def test_bundle_validate_rejects_density_out_of_range():
    bundle = BuyerMetaphorBundle(metaphor_density=1.5)
    with pytest.raises(ValueError, match="density"):
        bundle.validate()


def test_bundle_validate_rejects_confidence_out_of_range():
    bundle = BuyerMetaphorBundle(confidence=-0.1)
    with pytest.raises(ValueError, match="confidence"):
        bundle.validate()


# -----------------------------------------------------------------------------
# from_claude_response — both wrapped and flat shapes
# -----------------------------------------------------------------------------


def test_from_claude_response_parses_wrapped_shape():
    """The page-side schema wraps everything in a 'primary_metaphor'
    key; the buyer-side reuses that shape so Claude's structured
    output matches without prompt-side adjustment."""
    response = {
        "primary_metaphor": {
            "density": 0.6,
            "axes": {
                "warmth": 0.7, "distance": 0.3, "vertical": 0.5,
                "solidity": 0.6, "containment": 0.4, "force": 0.5,
                "path": 0.4, "closeness": 0.8,
            },
            "confidence": 0.8,
        }
    }
    bundle = BuyerMetaphorBundle.from_claude_response(
        response, review_id="r1", buyer_id="b1",
    )
    assert bundle.metaphor_density == 0.6
    assert bundle.confidence == 0.8
    assert bundle.primary_metaphor_axes[0] == 0.7  # warmth
    assert bundle.primary_metaphor_axes[7] == 0.8  # closeness
    assert bundle.review_id == "r1"
    assert bundle.buyer_id == "b1"


def test_from_claude_response_parses_flat_shape():
    """Tolerant of a flat shape too — Claude doesn't always wrap."""
    response = {
        "density": 0.4,
        "axes": {
            "warmth": 0.2, "distance": 0.0, "vertical": 0.0,
            "solidity": 0.0, "containment": 0.0, "force": 0.0,
            "path": 0.0, "closeness": 0.0,
        },
        "confidence": 0.5,
    }
    bundle = BuyerMetaphorBundle.from_claude_response(response)
    assert bundle.metaphor_density == 0.4
    assert bundle.primary_metaphor_axes[0] == 0.2


def test_from_claude_response_clamps_out_of_range_axes():
    """Claude occasionally returns slightly-out-of-range floats.
    Clamp rather than raise on individual axes; raise only on truly
    unparseable shapes."""
    response = {
        "primary_metaphor": {
            "density": 1.2,  # over 1
            "axes": {
                "warmth": -0.1, "distance": 1.5, "vertical": 0.5,
                "solidity": 0.5, "containment": 0.5, "force": 0.5,
                "path": 0.5, "closeness": 0.5,
            },
            "confidence": 0.7,
        }
    }
    bundle = BuyerMetaphorBundle.from_claude_response(response)
    assert bundle.metaphor_density == 1.0  # clamped
    assert bundle.primary_metaphor_axes[0] == 0.0  # warmth clamped from -0.1
    assert bundle.primary_metaphor_axes[1] == 1.0  # distance clamped from 1.5


def test_from_claude_response_raises_on_missing_axes():
    """Missing axes block is unparseable — caller catches and
    returns neutral."""
    response = {"primary_metaphor": {"density": 0.5}}
    with pytest.raises(ValueError, match="axes"):
        BuyerMetaphorBundle.from_claude_response(response)


def test_from_claude_response_raises_on_non_dict():
    with pytest.raises(ValueError, match="not a dict"):
        BuyerMetaphorBundle.from_claude_response("not a dict")


def test_from_claude_response_uses_zero_default_for_missing_axis():
    """Some axes might be omitted by Claude. Default to 0.0 — honest
    'no signal' for that axis."""
    response = {
        "primary_metaphor": {
            "density": 0.5,
            "axes": {"warmth": 0.7},  # only one axis
            "confidence": 0.4,
        }
    }
    bundle = BuyerMetaphorBundle.from_claude_response(response)
    assert bundle.primary_metaphor_axes[0] == 0.7  # warmth
    # All others default to 0.0
    assert all(v == 0.0 for v in bundle.primary_metaphor_axes[1:])


# -----------------------------------------------------------------------------
# score_review_metaphors — soft-fail on every error path
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_score_empty_text_returns_neutral():
    client = MagicMock()
    bundle = await score_review_metaphors(client, "")
    assert bundle.confidence == 0.0
    assert bundle.metaphor_density == 0.0
    # Client never called for empty input
    client.complete_structured.assert_not_called() if hasattr(
        client.complete_structured, "assert_not_called"
    ) else None


@pytest.mark.asyncio
async def test_score_whitespace_only_returns_neutral():
    client = MagicMock()
    bundle = await score_review_metaphors(client, "    \n  \t  ")
    assert bundle.confidence == 0.0


@pytest.mark.asyncio
async def test_score_claude_exception_returns_neutral():
    client = MagicMock()
    client.complete_structured = AsyncMock(side_effect=ConnectionError("api down"))
    bundle = await score_review_metaphors(
        client, "this is a real review with content",
    )
    assert bundle.confidence == 0.0
    # No exception propagates to caller


@pytest.mark.asyncio
async def test_score_empty_response_returns_neutral():
    client = MagicMock()
    client.complete_structured = AsyncMock(return_value=None)
    bundle = await score_review_metaphors(client, "review text here")
    assert bundle.confidence == 0.0


@pytest.mark.asyncio
async def test_score_malformed_response_returns_neutral():
    """Claude returns malformed JSON / wrong shape — parse fails →
    return neutral. No exception bubbles up."""
    client = MagicMock()
    client.complete_structured = AsyncMock(
        return_value={"unrelated": "garbage"}  # no axes block
    )
    bundle = await score_review_metaphors(client, "review text")
    assert bundle.confidence == 0.0


@pytest.mark.asyncio
async def test_score_happy_path_returns_validated_bundle():
    client = MagicMock()
    client.complete_structured = AsyncMock(return_value={
        "primary_metaphor": {
            "density": 0.55,
            "axes": {
                "warmth": 0.7, "distance": 0.2, "vertical": 0.4,
                "solidity": 0.5, "containment": 0.3, "force": 0.6,
                "path": 0.5, "closeness": 0.8,
            },
            "confidence": 0.78,
        }
    })
    bundle = await score_review_metaphors(
        client, "Warm welcoming staff, made me feel right at home",
        review_id="r42", buyer_id="b7",
    )
    assert bundle.confidence == 0.78
    assert bundle.metaphor_density == 0.55
    assert bundle.review_id == "r42"
    assert bundle.buyer_id == "b7"


@pytest.mark.asyncio
async def test_score_truncates_long_reviews():
    """Long reviews get truncated to max_chars to keep Claude latency
    bounded. Pin that the truncation actually happens."""
    client = MagicMock()
    client.complete_structured = AsyncMock(return_value={
        "primary_metaphor": {
            "density": 0.0,
            "axes": {n: 0.0 for n in PRIMARY_METAPHOR_AXIS_NAMES},
            "confidence": 0.0,
        }
    })
    long_review = "x" * 100_000
    await score_review_metaphors(client, long_review, max_chars=1000)

    sent_prompt = client.complete_structured.call_args.kwargs["prompt"]
    # The prompt body cannot contain more than ~1000 chars of review
    # (plus the prompt scaffold overhead); the full 100k long_review
    # should NOT appear
    assert long_review not in sent_prompt


# -----------------------------------------------------------------------------
# Aggregation — confidence-weighted, low-confidence bundles excluded
# -----------------------------------------------------------------------------


def _bundle(axes_warmth: float, confidence: float, buyer_id: str = "b1") -> BuyerMetaphorBundle:
    axes = [0.0] * 8
    axes[0] = axes_warmth  # warmth axis
    return BuyerMetaphorBundle(
        primary_metaphor_axes=axes,
        metaphor_density=0.5,
        confidence=confidence,
        buyer_id=buyer_id,
    )


def test_aggregate_returns_none_when_all_low_confidence():
    """A buyer with no confident reviews doesn't get a fabricated
    profile — return None so caller knows there's no signal yet."""
    bundles = [_bundle(0.5, 0.1), _bundle(0.5, 0.2)]
    result = aggregate_buyer_metaphor_axes(bundles, min_confidence=0.3)
    assert result is None


def test_aggregate_returns_none_when_empty():
    assert aggregate_buyer_metaphor_axes([]) is None


def test_aggregate_confidence_weights_correctly():
    """Bundle with conf 0.9 should dominate one with conf 0.5."""
    bundles = [
        _bundle(0.8, 0.9),  # high-confidence high-warmth
        _bundle(0.2, 0.5),  # lower-confidence low-warmth
    ]
    result = aggregate_buyer_metaphor_axes(bundles)
    assert result is not None
    # Aggregate warmth should lean toward 0.8 (the high-conf bundle)
    assert result.primary_metaphor_axes[0] > 0.5


def test_aggregate_excludes_below_min_confidence():
    """min_confidence=0.5 excludes bundles below it. The remaining
    confident bundle drives the aggregate alone."""
    bundles = [
        _bundle(0.9, 0.8),  # included
        _bundle(0.1, 0.2),  # excluded
    ]
    result = aggregate_buyer_metaphor_axes(bundles, min_confidence=0.5)
    assert result is not None
    # Aggregate warmth should be 0.9 (only the included bundle counts)
    assert result.primary_metaphor_axes[0] == pytest.approx(0.9)
