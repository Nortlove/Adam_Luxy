"""Pin Slice 20 — Section 6.4 mechanism-activation scorer.

Per directive Section 6.4 line 1064 ("multi-dimensional scoring:
metaphor coherence, mechanism activation, predicted fluency, reactance
risk"). Slice 20 ships the third dimension; Slices 1, 18, 19 ship the
others. Together the four close the offline-pipeline scoring stack.

Discipline anchors (B3-LUXY a/b/c/d):

    (a) Citations: directive Section 6.4 line 1064 +
        embeddings/pipeline.py:603-620 (canonical mechanism-keyword
        set). Marker words from Cialdini 1984 + Petty & Cacioppo
        ELM literature.

    (b) Boundary anchors: empty / unknown axis edge cases; per-mechanism
        marker scoring; threshold = 0.50; saturation guard against
        single accidental marker; pure function; result frozen;
        canonical 8 mechanisms; upload integration with bypass kwargs.

    (c) calibration_pending=True (marker dictionaries pre-pilot).

    (d) Honest tags: continuous Claude-API mechanism-activation vector
        (sibling); multilingual; NLP context awareness; per-archetype
        thresholds; compound markers.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from adam.intelligence.mechanism_activation_scorer import (
    CANONICAL_MECHANISMS,
    MECHANISM_ACTIVATION_THRESHOLD,
    MIN_TOTAL_HITS_FOR_ACTIVATION,
    MechanismActivationResult,
    passes_mechanism_activation_check,
    score_mechanism_activation,
)


# -----------------------------------------------------------------------------
# Vocabulary contract
# -----------------------------------------------------------------------------


def test_default_threshold_is_50_percent():
    assert MECHANISM_ACTIVATION_THRESHOLD == 0.50


def test_canonical_mechanisms_present():
    """The canonical 8 mechanisms (Cialdini 6 + reason_why + unity)
    are all present in the marker dict."""
    expected = {
        "social_proof", "scarcity", "authority", "reciprocity",
        "commitment", "liking", "unity", "reason_why",
    }
    assert set(CANONICAL_MECHANISMS) == expected


# -----------------------------------------------------------------------------
# Edge cases
# -----------------------------------------------------------------------------


def test_score_empty_text_returns_zero():
    out = score_mechanism_activation("", "social_proof")
    assert out.activation_score == 0.0
    assert out.threshold_passed is False


def test_score_unknown_mechanism_returns_zero_non_strict():
    out = score_mechanism_activation(
        "everyone is loving it", "not_a_mechanism",
    )
    assert out.activation_score == 0.0


def test_score_unknown_mechanism_raises_strict():
    with pytest.raises(ValueError):
        score_mechanism_activation(
            "everyone is loving it", "not_a_mechanism",
            strict_target=True,
        )


# -----------------------------------------------------------------------------
# Per-mechanism scoring
# -----------------------------------------------------------------------------


def test_social_proof_target_with_social_proof_markers_passes():
    text = "Everyone is loving it — millions trust this bestselling brand."
    out = score_mechanism_activation(text, "social_proof")
    assert out.target_hits >= 3
    assert out.threshold_passed is True


def test_scarcity_target_with_scarcity_markers_passes():
    text = "Limited time only — exclusive offer running out fast."
    out = score_mechanism_activation(text, "scarcity")
    assert out.target_hits >= 3
    assert out.threshold_passed is True


def test_authority_target_with_authority_markers_passes():
    text = "Doctor-recommended, scientist-proven, study-backed expert formula."
    out = score_mechanism_activation(text, "authority")
    assert out.target_hits >= 3
    assert out.threshold_passed is True


def test_off_target_copy_fails():
    """Target=social_proof but copy uses authority language → fails."""
    # Use authority markers that don't overlap with social_proof.
    text = "Scientist-proven research-backed expert formula."
    out = score_mechanism_activation(text, "social_proof")
    assert out.target_hits == 0
    assert out.threshold_passed is False


def test_per_mechanism_hits_populated():
    text = "Everyone is loving it — limited time exclusive offer."
    out = score_mechanism_activation(text, "social_proof")
    assert out.per_mechanism_hits["social_proof"] >= 1
    assert out.per_mechanism_hits["scarcity"] >= 1


def test_min_hits_floor_prevents_single_marker_saturation():
    text = "everyone"  # 1 token, 1 hit
    out = score_mechanism_activation(text, "social_proof")
    # target=1, total=1, denom=max(1, MIN)=2 → score = 0.5
    assert out.activation_score == pytest.approx(
        1.0 / MIN_TOTAL_HITS_FOR_ACTIVATION, rel=0.01,
    )


def test_score_bounded_in_unit_interval():
    text = " ".join(["everyone"] * 50)  # 50 social_proof hits
    out = score_mechanism_activation(text, "social_proof")
    assert 0.0 <= out.activation_score <= 1.0


def test_score_pure_function_idempotent():
    text = "Everyone is loving it."
    a = score_mechanism_activation(text, "social_proof")
    b = score_mechanism_activation(text, "social_proof")
    assert a.activation_score == b.activation_score


def test_word_boundary_excludes_substring():
    """'us' should NOT match 'truss' or 'discuss'."""
    text = "Discuss the trustworthy truss design."
    out = score_mechanism_activation(text, "unity")
    flagged_tokens = {t for t, _ in out.flagged_markers}
    assert "us" not in flagged_tokens


def test_target_mechanism_case_insensitive():
    text = "Everyone is loving it."
    a = score_mechanism_activation(text, "social_proof")
    b = score_mechanism_activation(text, "Social_Proof")
    c = score_mechanism_activation(text, "SOCIAL_PROOF")
    assert a.activation_score == b.activation_score == c.activation_score


def test_n_tokens_populated():
    text = "Everyone is loving it."  # 4 tokens
    out = score_mechanism_activation(text, "social_proof")
    assert out.n_tokens == 4


# -----------------------------------------------------------------------------
# passes_mechanism_activation_check
# -----------------------------------------------------------------------------


def test_passes_check_returns_tuple():
    out = passes_mechanism_activation_check(
        "everyone is loving it — millions trust", "social_proof",
    )
    passes, result = out
    assert isinstance(passes, bool)
    assert isinstance(result, MechanismActivationResult)


def test_passes_check_high_activation_passes():
    text = "Everyone is loving it — millions trust this bestseller."
    passes, _ = passes_mechanism_activation_check(text, "social_proof")
    assert passes is True


def test_passes_check_off_target_fails():
    text = "Doctor-proven scientist-endorsed expert-certified."
    passes, _ = passes_mechanism_activation_check(text, "social_proof")
    assert passes is False


def test_passes_check_custom_threshold():
    """Custom threshold flips marginal copy. 'limited time' matches
    both 'limited' and 'limited time' markers (2 scarcity hits) +
    'everyone' (1 social_proof hit) → ratio 1/3 ≈ 0.33."""
    text = "Everyone is. Limited time."
    passes_default, _ = passes_mechanism_activation_check(
        text, "social_proof",
    )
    passes_loose, _ = passes_mechanism_activation_check(
        text, "social_proof", threshold=0.20,
    )
    # Default 0.50 → fails; loose 0.20 → passes
    assert passes_default is False
    assert passes_loose is True


# -----------------------------------------------------------------------------
# Frozen
# -----------------------------------------------------------------------------


def test_result_frozen():
    out = score_mechanism_activation("everyone", "social_proof")
    with pytest.raises((AttributeError, Exception)):
        out.activation_score = 0.99  # type: ignore[misc]


# -----------------------------------------------------------------------------
# upload_creative integration
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_creative_rejects_off_mechanism_copy():
    """Mechanism=social_proof but copy is authority-language → reject."""
    from adam.intelligence.creative_upload_pipeline import upload_creative

    fake_client = MagicMock()
    fake_client.create_creative_by_url = AsyncMock(
        return_value={"creative": {"id": "should-not-reach"}, "errors": []}
    )

    result = await upload_creative(
        landing_page_url="https://x",
        name="off-mech",
        mechanism="social_proof",
        client=fake_client,
        copy_text="Doctor-proven scientist-endorsed expert-certified formula.",
    )
    assert result is None
    fake_client.create_creative_by_url.assert_not_called()


@pytest.mark.asyncio
async def test_upload_creative_passes_mechanism_aligned_copy():
    from adam.intelligence.creative_upload_pipeline import upload_creative

    fake_client = MagicMock()
    fake_client.create_creative_by_url = AsyncMock(
        return_value={"creative": {"id": "ok"}, "errors": []}
    )
    result = await upload_creative(
        landing_page_url="https://x",
        name="aligned",
        mechanism="social_proof",
        client=fake_client,
        copy_text=(
            "Everyone is loving it — millions of customers trust this "
            "top-rated bestseller."
        ),
    )
    assert result is not None


@pytest.mark.asyncio
async def test_upload_creative_skips_mechanism_gate_when_no_mechanism():
    from adam.intelligence.creative_upload_pipeline import upload_creative

    fake_client = MagicMock()
    fake_client.create_creative_by_url = AsyncMock(
        return_value={"creative": {"id": "ok"}, "errors": []}
    )
    result = await upload_creative(
        landing_page_url="https://x",
        name="no-mech",
        client=fake_client,
        copy_text="Anything goes.",
        # no mechanism declared
    )
    assert result is not None


@pytest.mark.asyncio
async def test_upload_creative_bypasses_mechanism_gate_when_disabled():
    from adam.intelligence.creative_upload_pipeline import upload_creative

    fake_client = MagicMock()
    fake_client.create_creative_by_url = AsyncMock(
        return_value={"creative": {"id": "ok"}, "errors": []}
    )
    result = await upload_creative(
        landing_page_url="https://x",
        name="bypass",
        mechanism="social_proof",
        client=fake_client,
        copy_text="Doctor-proven expert-certified.",  # would normally fail
        enforce_mechanism_activation_check=False,
    )
    assert result is not None
