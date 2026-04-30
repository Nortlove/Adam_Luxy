"""Pin the creative-side feature scorer — Phase E Item 3a.

Tests the parser/factory contract — neutral fallback, claude-response
round-trip, clamp behavior. The scorer's actual Claude calls are
exercised by integration tests with mocked client; this file pins
the deterministic parts.

Discipline (B3-LUXY a/b/c/d):
  (a) Schema mirrors PageFeatureBundle's; pairs documented in the
      module docstring.
  (b) These tests pin: neutral on empty input; clamp out-of-range;
      missing fields fall back to confidence=0; round-trip from
      Claude response.
  (c) calibration_pending=True on the prompt itself (LUXY pilot will
      validate against blend-fit outcomes).
  (d) Honest tag — attentional_posture is creative-side
      self-assessment by Claude; pilot data may reveal it diverges
      from reader-observed posture.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from adam.intelligence.creative_feature_scoring import (
    bundle_from_claude_response,
    neutral_creative_bundle,
    score_creative_features,
)
from adam.intelligence.pages.claude_feature_scoring import (
    GOAL_ACTIVATION_KEYS,
    PRIMARY_METAPHOR_AXIS_NAMES,
)


# -----------------------------------------------------------------------------
# Neutral bundle — Claude-unavailable fallback
# -----------------------------------------------------------------------------


def test_neutral_bundle_has_zero_confidences():
    """Every confidence field MUST be 0.0 so downstream blend_fit's
    confidence-weighted alignment skips the observation."""
    b = neutral_creative_bundle()
    assert b.register_confidence == 0.0
    assert b.primary_metaphor_confidence == 0.0
    assert b.goal_fulfillment_confidence == 0.0
    assert b.temporal_horizon_confidence == 0.0
    assert b.processing_fluency_confidence == 0.0
    assert b.attentional_posture_confidence == 0.0


def test_neutral_bundle_validates():
    """Neutral bundle must pass its own validate() — defensive against
    schema drift between the bundle and the neutral factory."""
    b = neutral_creative_bundle()
    b.validate()  # raises on invalid


def test_neutral_bundle_has_canonical_axis_dimensionality():
    b = neutral_creative_bundle()
    assert len(b.primary_metaphor_axes) == len(PRIMARY_METAPHOR_AXIS_NAMES)
    assert set(b.goal_fulfillment_profile.keys()) == set(GOAL_ACTIVATION_KEYS)


# -----------------------------------------------------------------------------
# Claude-response parser
# -----------------------------------------------------------------------------


def _full_response() -> dict:
    """A complete, in-bounds Claude response for round-trip testing."""
    return {
        "register": {"score": -0.3, "category": "conversational", "confidence": 0.85},
        "primary_metaphor": {
            "density": 0.6,
            "axes": {
                "warmth": 0.7, "distance": 0.2, "vertical": 0.4,
                "solidity": 0.5, "containment": 0.3, "force": 0.6,
                "path": 0.4, "closeness": 0.5,
            },
            "confidence": 0.8,
        },
        "goal_fulfillment_profile": {k: 0.5 for k in GOAL_ACTIVATION_KEYS},
        "goal_fulfillment_confidence": 0.7,
        "temporal_horizon": {"induction": -0.4, "confidence": 0.65},
        "processing_fluency": {"score": 0.85, "confidence": 0.9},
        "attentional_posture": {"score": -0.6, "confidence": 0.75},
    }


def test_parser_round_trips_full_response():
    response = _full_response()
    b = bundle_from_claude_response(response)
    assert b.register_score == pytest.approx(-0.3)
    assert b.register_category == "conversational"
    assert b.register_confidence == pytest.approx(0.85)
    assert b.primary_metaphor_density == pytest.approx(0.6)
    assert b.primary_metaphor_axes[0] == pytest.approx(0.7)  # warmth
    assert b.goal_fulfillment_confidence == pytest.approx(0.7)
    assert b.temporal_horizon_induction == pytest.approx(-0.4)
    assert b.processing_fluency == pytest.approx(0.85)
    assert b.attentional_posture == pytest.approx(-0.6)
    assert b.attentional_posture_confidence == pytest.approx(0.75)


def test_parser_clamps_out_of_range_values():
    response = {
        "register": {"score": -2.5, "category": "conversational", "confidence": 1.5},
        "primary_metaphor": {
            "density": 99.0,
            "axes": {name: -10.0 for name in PRIMARY_METAPHOR_AXIS_NAMES},
            "confidence": -0.5,
        },
        "goal_fulfillment_profile": {k: 5.0 for k in GOAL_ACTIVATION_KEYS},
        "goal_fulfillment_confidence": 99.0,
        "temporal_horizon": {"induction": 99.0, "confidence": 99.0},
        "processing_fluency": {"score": -3.0, "confidence": 99.0},
        "attentional_posture": {"score": 99.0, "confidence": -1.0},
    }
    b = bundle_from_claude_response(response)
    # All values must clamp into bounds
    assert -1.0 <= b.register_score <= 1.0
    assert 0.0 <= b.register_confidence <= 1.0
    assert 0.0 <= b.primary_metaphor_density <= 1.0
    for v in b.primary_metaphor_axes:
        assert 0.0 <= v <= 1.0
    assert 0.0 <= b.primary_metaphor_confidence <= 1.0
    for v in b.goal_fulfillment_profile.values():
        assert 0.0 <= v <= 1.0
    assert 0.0 <= b.goal_fulfillment_confidence <= 1.0
    assert -1.0 <= b.temporal_horizon_induction <= 1.0
    assert 0.0 <= b.processing_fluency <= 1.0
    assert -1.0 <= b.attentional_posture <= 1.0


def test_parser_unknown_register_category_falls_back():
    response = _full_response()
    response["register"]["category"] = "totally_made_up_category"
    b = bundle_from_claude_response(response)
    # Falls back to "journalistic"
    assert b.register_category == "journalistic"


def test_parser_missing_fields_use_zero_confidence():
    """Missing top-level fields should produce zero-confidence defaults
    so blend_fit downstream skips them."""
    response = {
        # only register provided; everything else missing
        "register": {"score": 0.0, "category": "conversational", "confidence": 0.5},
    }
    b = bundle_from_claude_response(response)
    assert b.register_confidence == pytest.approx(0.5)
    # Missing → confidences are 0.0 (skip in blend_fit)
    assert b.primary_metaphor_confidence == 0.0
    assert b.goal_fulfillment_confidence == 0.0
    assert b.temporal_horizon_confidence == 0.0
    assert b.processing_fluency_confidence == 0.0
    assert b.attentional_posture_confidence == 0.0


# -----------------------------------------------------------------------------
# score_creative_features end-to-end (mocked Claude)
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_score_creative_returns_neutral_on_empty_headline():
    """No headline → neutral bundle (Claude not called)."""
    fake = MagicMock()
    fake.complete_structured = AsyncMock(return_value=_full_response())
    b = await score_creative_features(claude_client=fake, headline="")
    assert b.register_confidence == 0.0  # neutral
    fake.complete_structured.assert_not_called()


@pytest.mark.asyncio
async def test_score_creative_calls_claude_with_headline():
    fake = MagicMock()
    fake.complete_structured = AsyncMock(return_value=_full_response())
    b = await score_creative_features(
        claude_client=fake,
        headline="Trusted by professionals",
        body="Used by executives.",
        cta="See the lineup",
        brand="LUXY",
    )
    fake.complete_structured.assert_awaited_once()
    # Bundle reflects the mocked response (round-trip)
    assert b.register_category == "conversational"
    assert b.register_confidence == pytest.approx(0.85)


@pytest.mark.asyncio
async def test_score_creative_neutral_on_claude_exception():
    """Any Claude API error must produce a neutral bundle, not raise."""
    fake = MagicMock()
    fake.complete_structured = AsyncMock(
        side_effect=RuntimeError("Claude API down"),
    )
    b = await score_creative_features(
        claude_client=fake, headline="Try our service",
    )
    assert b.register_confidence == 0.0  # neutral fallback


@pytest.mark.asyncio
async def test_score_creative_neutral_on_empty_response():
    fake = MagicMock()
    fake.complete_structured = AsyncMock(return_value=None)
    b = await score_creative_features(
        claude_client=fake, headline="Try our service",
    )
    assert b.register_confidence == 0.0


@pytest.mark.asyncio
async def test_score_creative_neutral_on_malformed_response():
    """Response that fails parser validation → neutral fallback, not raise."""
    fake = MagicMock()
    fake.complete_structured = AsyncMock(
        return_value={"register": "not a dict"},  # malformed
    )
    b = await score_creative_features(
        claude_client=fake, headline="Try our service",
    )
    assert b.register_confidence == 0.0


# -----------------------------------------------------------------------------
# blend_fit integration — the canonical decision-time consumer
# -----------------------------------------------------------------------------


def test_neutral_creative_bundle_yields_neutral_blend_fit():
    """compute_blend_fit on neutral creative + any page → 0.5 neutral
    (no information). Pins the integration contract."""
    from adam.intelligence.blend_fit import compute_blend_fit
    from adam.intelligence.pages.claude_feature_scoring import PageFeatureBundle

    creative = neutral_creative_bundle()
    page = PageFeatureBundle.neutral()
    score, decomp = compute_blend_fit(creative, page)
    # Both sides are zero-confidence → neutral 0.5 fallback
    assert score == pytest.approx(0.5)
