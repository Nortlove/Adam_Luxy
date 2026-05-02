"""Pin Slice 18 — Section 6.5 reactance-risk pre-publication scorer.

Per directive Section 6.5 lines 811-820: every generated creative is
scored independently for reactance risk via three signals
(explicitness, pressure-language, control-override) and rejected
above a threshold before entering the live candidate pool.

Discipline anchors (B3-LUXY a/b/c/d):

    (a) Citations: directive Section 6.5 lines 811-820 + Section 6.4
        line 805 + creative_upload_pipeline.py:71-73 (named sibling).

    (b) Boundary anchors:
          - empty / whitespace text → score 0
          - explicitness markers ('only', 'must', 'act now') flagged
          - pressure markers ('hurry', 'last chance') flagged
          - control-override markers ('countdown', 'only 1 left')
            flagged
          - density-scaled — short copy floors at 10 tokens
          - total_score in [0, 1]
          - flagged_markers contains (token, category) tuples
          - ReactanceRiskResult is frozen
          - default threshold = 0.50
          - passes_reactance_check returns (bool, ReactanceRiskResult)
          - upload_creative rejects when score >= threshold
          - upload_creative skips check when copy_text=None
          - upload_creative bypasses check when
            enforce_reactance_check=False

    (c) calibration_pending=True (threshold + weights pre-pilot).

    (d) Honest tags — what is NOT tested here:
          - Visual / non-text reactance (sibling)
          - Per-archetype thresholds (sibling)
          - Reactance × posture interaction (sibling)
          - Multilingual (sibling)
          - Context-aware NLP (sibling)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from adam.intelligence.reactance_risk_scorer import (
    CONTROL_OVERRIDE_MARKERS,
    EXPLICITNESS_MARKERS,
    PRESSURE_MARKERS,
    REACTANCE_REJECT_THRESHOLD,
    ReactanceRiskResult,
    passes_reactance_check,
    score_reactance_risk,
)


# -----------------------------------------------------------------------------
# Default threshold + marker dictionary contracts
# -----------------------------------------------------------------------------


def test_default_threshold_is_50_percent():
    """The reject threshold defaults to 0.50 — calibration_pending."""
    assert REACTANCE_REJECT_THRESHOLD == 0.50


def test_marker_dicts_non_empty():
    """Each of the three categories has at least 5 markers."""
    assert len(EXPLICITNESS_MARKERS) >= 5
    assert len(PRESSURE_MARKERS) >= 5
    assert len(CONTROL_OVERRIDE_MARKERS) >= 5


def test_directive_specific_markers_present():
    """The directive's literal examples must appear in the marker
    lists — these are the canonical anchors."""
    assert "only" in EXPLICITNESS_MARKERS
    assert "must" in EXPLICITNESS_MARKERS
    assert "act now" in EXPLICITNESS_MARKERS
    assert "limited time" in EXPLICITNESS_MARKERS


# -----------------------------------------------------------------------------
# score_reactance_risk — empty / edge cases
# -----------------------------------------------------------------------------


def test_score_empty_string_returns_zero():
    out = score_reactance_risk("")
    assert out.total_score == 0.0
    assert out.flagged_markers == []
    assert out.n_tokens == 0


def test_score_whitespace_only_returns_zero():
    out = score_reactance_risk("   \n\t  ")
    assert out.total_score == 0.0
    assert out.n_tokens == 0


def test_score_clean_copy_returns_zero():
    """Reasonable copy without pressure markers → score 0."""
    text = (
        "Premium black-car service for daily commutes. "
        "Reliable arrival times, professional drivers."
    )
    out = score_reactance_risk(text)
    assert out.total_score == 0.0
    assert out.flagged_markers == []


# -----------------------------------------------------------------------------
# Per-category scoring
# -----------------------------------------------------------------------------


def test_score_explicitness_marker_flagged():
    """Single explicitness marker → contributes to explicitness."""
    out = score_reactance_risk("Act now to secure your reservation.")
    assert out.explicitness_score > 0.0
    assert ("act now", "explicitness") in out.flagged_markers


def test_score_pressure_marker_flagged():
    out = score_reactance_risk("Hurry — running out fast!")
    assert out.pressure_score > 0.0
    flagged_tokens = {t for t, _ in out.flagged_markers}
    assert "hurry" in flagged_tokens
    assert "running out" in flagged_tokens


def test_score_control_override_marker_flagged():
    out = score_reactance_risk(
        "Countdown timer: only 1 left in your size."
    )
    assert out.control_override_score > 0.0
    flagged_tokens = {t for t, _ in out.flagged_markers}
    assert "countdown" in flagged_tokens
    assert "1 left" in flagged_tokens or "only 1 left" in flagged_tokens


def test_score_high_pressure_copy_exceeds_threshold():
    """A worst-case ad copy should breach the default threshold."""
    text = (
        "Act now! Limited time! Hurry — only 1 left! "
        "Last chance — countdown ticking — don't miss out — "
        "must buy now, expires today!"
    )
    out = score_reactance_risk(text)
    assert out.total_score >= REACTANCE_REJECT_THRESHOLD


def test_score_total_bounded_in_unit_interval():
    """Even worst-case input → total_score <= 1.0."""
    text = " ".join(EXPLICITNESS_MARKERS) + " " + " ".join(PRESSURE_MARKERS)
    out = score_reactance_risk(text)
    assert 0.0 <= out.total_score <= 1.0


def test_score_pure_function_idempotent():
    """Same input → same result on repeat call."""
    text = "Act now! Limited time!"
    a = score_reactance_risk(text)
    b = score_reactance_risk(text)
    assert a.total_score == b.total_score
    assert a.flagged_markers == b.flagged_markers


def test_score_word_boundary_excludes_substring_match():
    """'must' should NOT match 'mustard' or similar substrings."""
    out_clean = score_reactance_risk(
        "Try our gourmet mustard with every order."
    )
    flagged_tokens = {t for t, _ in out_clean.flagged_markers}
    assert "must" not in flagged_tokens


def test_score_short_copy_false_positive_guard():
    """Ultra-short copy (n_tokens < 5) with one marker → subscore is
    halved (false-positive guard for headlines)."""
    out = score_reactance_risk("Act now!")  # 2 tokens, 1 marker
    # Saturation: 1 hit / 3 = 0.333; halved by short-copy guard = 0.167.
    assert out.explicitness_score < 0.5
    assert out.explicitness_score == pytest.approx(1.0 / 6.0, abs=0.01)


def test_score_n_tokens_populated():
    text = "Act now to secure your reservation."  # 6 tokens
    out = score_reactance_risk(text)
    assert out.n_tokens == 6


# -----------------------------------------------------------------------------
# passes_reactance_check
# -----------------------------------------------------------------------------


def test_passes_check_returns_tuple():
    out = passes_reactance_check("normal copy")
    assert isinstance(out, tuple) and len(out) == 2
    passes, result = out
    assert isinstance(passes, bool)
    assert isinstance(result, ReactanceRiskResult)


def test_passes_check_clean_text_passes():
    passes, _ = passes_reactance_check("Premium service.")
    assert passes is True


def test_passes_check_high_pressure_fails():
    passes, _ = passes_reactance_check(
        "Act now! Hurry! Last chance! Only 1 left! Countdown!",
    )
    assert passes is False


def test_passes_check_custom_threshold():
    """Lowering the threshold flips a marginal copy from pass to fail."""
    text = "Act now to subscribe."
    passes_default, result_default = passes_reactance_check(text)
    passes_strict, _ = passes_reactance_check(
        text, threshold=0.001,
    )
    # Default threshold (0.50) → passes; strict 0.001 → fails (any
    # non-zero score breaches).
    assert passes_default is True
    assert passes_strict is False


# -----------------------------------------------------------------------------
# Frozen dataclass
# -----------------------------------------------------------------------------


def test_result_frozen():
    out = score_reactance_risk("hello world")
    with pytest.raises((AttributeError, Exception)):
        out.total_score = 0.99  # type: ignore[misc]


# -----------------------------------------------------------------------------
# upload_creative integration — the gate
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_creative_rejects_high_pressure_copy():
    """upload_creative with high-pressure copy_text → returns None
    (rejected) and does NOT call create_creative_by_url."""
    from adam.intelligence.creative_upload_pipeline import upload_creative

    fake_client = MagicMock()
    fake_client.create_creative_by_url = AsyncMock(
        return_value={"creative": {"id": "should-not-reach"}, "errors": []}
    )

    result = await upload_creative(
        landing_page_url="https://x",
        name="bad",
        client=fake_client,
        copy_text=(
            "Act now! Limited time! Hurry — only 1 left! "
            "Last chance — countdown ticking — don't miss out — "
            "must buy now, expires today!"
        ),
    )
    assert result is None
    fake_client.create_creative_by_url.assert_not_called()


@pytest.mark.asyncio
async def test_upload_creative_passes_clean_copy_through_gate():
    """Clean copy_text → score below threshold → upload proceeds."""
    from adam.intelligence.creative_upload_pipeline import upload_creative

    fake_client = MagicMock()
    fake_client.create_creative_by_url = AsyncMock(
        return_value={"creative": {"id": "ok-id"}, "errors": []}
    )

    result = await upload_creative(
        landing_page_url="https://x",
        name="good",
        client=fake_client,
        copy_text="Premium service for daily commutes.",
    )
    assert result is not None
    assert result.stackadapt_creative_id == "ok-id"


@pytest.mark.asyncio
async def test_upload_creative_skips_gate_when_copy_text_none():
    """No copy_text → gate skipped (back-compat)."""
    from adam.intelligence.creative_upload_pipeline import upload_creative

    fake_client = MagicMock()
    fake_client.create_creative_by_url = AsyncMock(
        return_value={"creative": {"id": "ok"}, "errors": []}
    )
    result = await upload_creative(
        landing_page_url="https://x",
        name="no-copy",
        client=fake_client,
        # no copy_text
    )
    assert result is not None
    fake_client.create_creative_by_url.assert_called_once()


@pytest.mark.asyncio
async def test_upload_creative_bypasses_gate_when_disabled():
    """enforce_reactance_check=False → gate skipped even with bad copy."""
    from adam.intelligence.creative_upload_pipeline import upload_creative

    fake_client = MagicMock()
    fake_client.create_creative_by_url = AsyncMock(
        return_value={"creative": {"id": "ok"}, "errors": []}
    )
    result = await upload_creative(
        landing_page_url="https://x",
        name="bypassed",
        client=fake_client,
        copy_text="Act now! Hurry! Only 1 left!",  # would normally fail
        enforce_reactance_check=False,
    )
    assert result is not None
    fake_client.create_creative_by_url.assert_called_once()


def test_upload_pipeline_honest_tag_marked_shipped():
    """creative_upload_pipeline.py honest tag must reflect Slice 18
    shipped (so future agents don't re-implement)."""
    from pathlib import Path
    src = Path(
        "adam/intelligence/creative_upload_pipeline.py"
    ).read_text()
    assert "SHIPPED in Slice 18" in src, (
        "Honest tag for reactance scorer (line 71-73) still says "
        "v0.1 sibling — should reflect Slice 18 shipped."
    )
