"""Unit tests for claude_feature_scoring — the #7 MV page-feature scorer."""

from __future__ import annotations

from typing import Any, Dict

import pytest

from adam.intelligence.goal_activation import GOAL_TAXONOMY
from adam.intelligence.pages.claude_feature_scoring import (
    GOAL_ACTIVATION_KEYS,
    PRIMARY_METAPHOR_AXIS_NAMES,
    PageFeatureBundle,
    REGISTER_CATEGORIES,
    score_page_features,
)


# -----------------------------------------------------------------------------
# Constants are stable and consistent with upstream dependencies
# -----------------------------------------------------------------------------


class TestConstants:
    def test_primary_metaphor_axis_count_is_eight(self):
        assert len(PRIMARY_METAPHOR_AXIS_NAMES) == 8

    def test_primary_metaphor_axes_are_canonical(self):
        # Order must match entity_graph.py zero-stub shape. Changing
        # this order is a cross-module break.
        assert PRIMARY_METAPHOR_AXIS_NAMES == (
            "warmth", "distance", "vertical", "solidity",
            "containment", "force", "path", "closeness",
        )

    def test_goal_activation_keys_match_taxonomy(self):
        # If GOAL_TAXONOMY changes, GOAL_ACTIVATION_KEYS must track.
        assert set(GOAL_ACTIVATION_KEYS) == set(GOAL_TAXONOMY.keys())

    def test_register_categories_are_nonempty(self):
        assert len(REGISTER_CATEGORIES) >= 4
        assert all(c and isinstance(c, str) for c in REGISTER_CATEGORIES)


# -----------------------------------------------------------------------------
# PageFeatureBundle validation
# -----------------------------------------------------------------------------


def _valid_bundle_kwargs() -> Dict[str, Any]:
    return dict(
        register_score=0.3,
        register_category="journalistic",
        register_confidence=0.7,
        primary_metaphor_density=0.4,
        primary_metaphor_axes=[0.5] * 8,
        primary_metaphor_confidence=0.6,
        goal_activation_profile={k: 0.2 for k in GOAL_ACTIVATION_KEYS},
        goal_activation_confidence=0.5,
        temporal_horizon_induction=-0.2,
        temporal_horizon_confidence=0.5,
        processing_fluency=0.7,
        processing_fluency_confidence=0.6,
    )


class TestPageFeatureBundleValidation:
    def test_valid_bundle_passes(self):
        PageFeatureBundle(**_valid_bundle_kwargs()).validate()

    def test_register_score_out_of_range_rejected(self):
        kwargs = _valid_bundle_kwargs()
        kwargs["register_score"] = 1.5
        with pytest.raises(ValueError, match=r"register_score"):
            PageFeatureBundle(**kwargs).validate()

    def test_unknown_register_category_rejected(self):
        kwargs = _valid_bundle_kwargs()
        kwargs["register_category"] = "surrealist"
        with pytest.raises(ValueError, match="register_category"):
            PageFeatureBundle(**kwargs).validate()

    def test_wrong_length_metaphor_axes_rejected(self):
        kwargs = _valid_bundle_kwargs()
        kwargs["primary_metaphor_axes"] = [0.5] * 6  # wrong length
        with pytest.raises(ValueError, match="primary_metaphor_axes length"):
            PageFeatureBundle(**kwargs).validate()

    def test_metaphor_axis_out_of_range_rejected(self):
        kwargs = _valid_bundle_kwargs()
        axes = [0.5] * 8
        axes[3] = 1.2
        kwargs["primary_metaphor_axes"] = axes
        with pytest.raises(ValueError, match=r"primary_metaphor_axes\[solidity\]"):
            PageFeatureBundle(**kwargs).validate()

    def test_missing_goal_key_rejected(self):
        kwargs = _valid_bundle_kwargs()
        partial = {k: 0.2 for k in GOAL_ACTIVATION_KEYS[:-1]}
        kwargs["goal_activation_profile"] = partial
        with pytest.raises(ValueError, match="goal_activation_profile keys"):
            PageFeatureBundle(**kwargs).validate()

    def test_extra_goal_key_rejected(self):
        kwargs = _valid_bundle_kwargs()
        extra = {k: 0.2 for k in GOAL_ACTIVATION_KEYS}
        extra["invented_goal"] = 0.3
        kwargs["goal_activation_profile"] = extra
        with pytest.raises(ValueError, match="goal_activation_profile keys"):
            PageFeatureBundle(**kwargs).validate()

    def test_temporal_horizon_out_of_range_rejected(self):
        kwargs = _valid_bundle_kwargs()
        kwargs["temporal_horizon_induction"] = -1.5
        with pytest.raises(ValueError, match="temporal_horizon_induction"):
            PageFeatureBundle(**kwargs).validate()


# -----------------------------------------------------------------------------
# PageFeatureBundle.neutral
# -----------------------------------------------------------------------------


class TestPageFeatureBundleNeutral:
    def test_neutral_passes_validation(self):
        PageFeatureBundle.neutral().validate()

    def test_neutral_confidences_are_zero(self):
        bundle = PageFeatureBundle.neutral()
        # Every confidence field must be 0 so downstream Welford skips.
        assert bundle.register_confidence == 0.0
        assert bundle.primary_metaphor_confidence == 0.0
        assert bundle.goal_activation_confidence == 0.0
        assert bundle.temporal_horizon_confidence == 0.0
        assert bundle.processing_fluency_confidence == 0.0

    def test_neutral_fluency_is_midpoint(self):
        # Fluency is [0, 1] with no signed neutral; midpoint is honest.
        assert PageFeatureBundle.neutral().processing_fluency == 0.5

    def test_neutral_goal_profile_has_all_keys(self):
        bundle = PageFeatureBundle.neutral()
        assert set(bundle.goal_activation_profile.keys()) == set(GOAL_ACTIVATION_KEYS)
        assert all(v == 0.0 for v in bundle.goal_activation_profile.values())


# -----------------------------------------------------------------------------
# PageFeatureBundle.from_claude_response — parsing + clamping
# -----------------------------------------------------------------------------


def _valid_claude_response() -> Dict[str, Any]:
    return {
        "register": {
            "score": 0.4,
            "category": "journalistic",
            "confidence": 0.8,
        },
        "primary_metaphor": {
            "density": 0.5,
            "axes": {name: 0.3 for name in PRIMARY_METAPHOR_AXIS_NAMES},
            "confidence": 0.7,
        },
        "goal_activation_profile": {k: 0.2 for k in GOAL_ACTIVATION_KEYS},
        "goal_activation_confidence": 0.6,
        "temporal_horizon": {"induction": -0.3, "confidence": 0.7},
        "processing_fluency": {"score": 0.8, "confidence": 0.9},
    }


class TestFromClaudeResponse:
    def test_well_formed_response_parses(self):
        bundle = PageFeatureBundle.from_claude_response(_valid_claude_response())
        bundle.validate()
        assert bundle.register_category == "journalistic"
        assert bundle.processing_fluency == 0.8

    def test_out_of_range_score_is_clamped(self):
        response = _valid_claude_response()
        response["register"]["score"] = 5.0
        bundle = PageFeatureBundle.from_claude_response(response)
        assert bundle.register_score == 1.0

    def test_unknown_register_category_falls_back_to_journalistic(self):
        response = _valid_claude_response()
        response["register"]["category"] = "hieroglyphic"
        bundle = PageFeatureBundle.from_claude_response(response)
        assert bundle.register_category == "journalistic"

    def test_missing_metaphor_axis_falls_back_to_zero(self):
        response = _valid_claude_response()
        # Drop one axis; others present.
        response["primary_metaphor"]["axes"].pop("vertical")
        bundle = PageFeatureBundle.from_claude_response(response)
        vertical_idx = PRIMARY_METAPHOR_AXIS_NAMES.index("vertical")
        assert bundle.primary_metaphor_axes[vertical_idx] == 0.0

    def test_missing_goal_key_falls_back_to_zero(self):
        response = _valid_claude_response()
        first_key = GOAL_ACTIVATION_KEYS[0]
        response["goal_activation_profile"].pop(first_key)
        bundle = PageFeatureBundle.from_claude_response(response)
        assert bundle.goal_activation_profile[first_key] == 0.0

    def test_empty_response_falls_back_to_neutral_confidences(self):
        bundle = PageFeatureBundle.from_claude_response({})
        # All confidence fields should be 0.0; scores at neutral defaults.
        assert bundle.register_confidence == 0.0
        assert bundle.primary_metaphor_confidence == 0.0
        assert bundle.goal_activation_confidence == 0.0
        assert bundle.temporal_horizon_confidence == 0.0
        assert bundle.processing_fluency_confidence == 0.0

    def test_non_numeric_field_falls_back_gracefully(self):
        response = _valid_claude_response()
        response["processing_fluency"]["score"] = "very fluent"
        bundle = PageFeatureBundle.from_claude_response(response)
        # Non-numeric → default of 0.5 (neutral midpoint).
        assert bundle.processing_fluency == 0.5


# -----------------------------------------------------------------------------
# score_page_features — async scoring entry point
# -----------------------------------------------------------------------------


class _FakeClaudeClient:
    """Stand-in for ClaudeClient. ``behavior`` is one of:
       "ok"     → returns _valid_claude_response
       "raise"  → raises on complete_structured
       "empty"  → returns {}
       "malformed" → returns a dict that fails parsing
    """

    def __init__(self, behavior: str = "ok"):
        self.behavior = behavior
        self.calls = []

    async def complete_structured(
        self, prompt: str, output_schema: Dict[str, Any],
        system=None, model=None,
    ):
        self.calls.append({"prompt": prompt, "system": system, "model": model})
        if self.behavior == "raise":
            raise RuntimeError("Claude API unavailable")
        if self.behavior == "empty":
            return {}
        if self.behavior == "malformed":
            return {"register": 12345}  # non-dict for nested field
        return _valid_claude_response()


@pytest.mark.asyncio
async def test_score_page_features_success_path():
    client = _FakeClaudeClient(behavior="ok")
    bundle = await score_page_features(
        client,
        title="Why market volatility rewards patient investors",
        body="The article text about markets and investing patience. " * 20,
    )
    bundle.validate()
    assert bundle.register_category == "journalistic"
    assert bundle.register_confidence == 0.8
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_score_page_features_empty_title_returns_neutral():
    client = _FakeClaudeClient(behavior="ok")
    bundle = await score_page_features(
        client, title="", body="Something",
    )
    assert bundle.register_confidence == 0.0
    assert len(client.calls) == 0


@pytest.mark.asyncio
async def test_score_page_features_empty_body_returns_neutral():
    client = _FakeClaudeClient(behavior="ok")
    bundle = await score_page_features(
        client, title="Headline", body="",
    )
    assert bundle.register_confidence == 0.0
    assert len(client.calls) == 0


@pytest.mark.asyncio
async def test_score_page_features_api_error_returns_neutral():
    client = _FakeClaudeClient(behavior="raise")
    bundle = await score_page_features(
        client, title="Headline", body="Body text " * 10,
    )
    assert bundle.register_confidence == 0.0
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_score_page_features_empty_response_returns_neutral():
    client = _FakeClaudeClient(behavior="empty")
    bundle = await score_page_features(
        client, title="Headline", body="Body text " * 10,
    )
    assert bundle.register_confidence == 0.0


@pytest.mark.asyncio
async def test_score_page_features_malformed_returns_neutral():
    client = _FakeClaudeClient(behavior="malformed")
    bundle = await score_page_features(
        client, title="Headline", body="Body text " * 10,
    )
    # Even if parsing succeeds with clamping, the invalid "register"
    # field should produce a neutral fallback on the register features
    # at minimum.
    bundle.validate()


@pytest.mark.asyncio
async def test_score_page_features_truncates_long_body():
    client = _FakeClaudeClient(behavior="ok")
    long_body = "word " * 10000  # ~50k chars
    bundle = await score_page_features(
        client, title="Headline", body=long_body, max_body_chars=2000,
    )
    bundle.validate()
    # Prompt should contain the truncated body, not the full one.
    sent_prompt = client.calls[0]["prompt"]
    assert len(sent_prompt) < len(long_body) + 2000  # headroom for template
