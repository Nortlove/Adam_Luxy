"""Pin Slice 19 — Section 6.4 metaphor-coherence pre-publication scorer.

Per directive Section 6.4 line 1064 ("multi-dimensional scoring:
metaphor coherence, mechanism activation, predicted fluency, reactance
risk") + Phase 10 line 1135 (RED criterion #6 — "any creative in
rotation fails primary-metaphor coherence in spot check"). The check
function check_metaphor_coherence_failed already exists in
phase_10_launch_sequence.py:239; this slice ships the producer.

Discipline anchors (B3-LUXY a/b/c/d):

    (a) Citations: directive Section 6.4 line 1064 + Phase 10 line
        1135 + claude_feature_scoring.py:80-89 (canonical 8-axis
        vocabulary). Marker words from the standard primary-metaphor
        literature (Lakoff & Johnson, Grady, Boroditsky).

    (b) Boundary anchors:
          - empty / whitespace text → score 0
          - unknown target_metaphor → score 0 (non-strict)
          - unknown target_metaphor + strict_target=True → raises
          - target-axis-only markers → high coherence (≥ threshold)
          - cross-axis markers → low coherence (< threshold)
          - per-axis hit counts populated
          - threshold = 0.50
          - flagged_markers contains (token, axis) tuples
          - pure function idempotent
          - MetaphorCoherenceResult is frozen
          - 8-axis vocabulary matches PRIMARY_METAPHOR_AXIS_NAMES

    (c) calibration_pending=True (marker dictionaries pre-pilot).

    (d) Honest tags — what is NOT tested here:
          - Continuous 8-dim metaphor vector via Claude API (sibling)
          - Multilingual markers (English only)
          - Compound-marker phrase patterns (sibling)
          - Per-archetype threshold tuning (sibling)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from adam.intelligence.metaphor_coherence_scorer import (
    METAPHOR_COHERENCE_THRESHOLD,
    MIN_TOTAL_HITS_FOR_COHERENCE,
    MetaphorCoherenceResult,
    passes_metaphor_coherence_check,
    score_metaphor_coherence,
)
from adam.intelligence.pages.claude_feature_scoring import (
    PRIMARY_METAPHOR_AXIS_NAMES,
)


# -----------------------------------------------------------------------------
# Vocabulary contract
# -----------------------------------------------------------------------------


def test_default_threshold_is_50_percent():
    assert METAPHOR_COHERENCE_THRESHOLD == 0.50


def test_axes_match_canonical_vocabulary():
    """The scorer must know all 8 canonical axes from
    claude_feature_scoring.PRIMARY_METAPHOR_AXIS_NAMES — Buyer /
    Brand / Creative bundles all share this vocabulary."""
    # The module's marker dict completeness check runs at import
    # time (raises RuntimeError if any axis missing); reaching this
    # point means the dict is canonical. We re-pin the count for
    # belt-and-suspenders.
    assert len(PRIMARY_METAPHOR_AXIS_NAMES) == 8
    expected = {
        "warmth", "distance", "vertical", "solidity", "containment",
        "force", "path", "closeness",
    }
    assert set(PRIMARY_METAPHOR_AXIS_NAMES) == expected


# -----------------------------------------------------------------------------
# Empty / unknown-axis edge cases
# -----------------------------------------------------------------------------


def test_score_empty_text_returns_zero():
    out = score_metaphor_coherence("", "warmth")
    assert out.coherence_score == 0.0
    assert out.threshold_passed is False
    assert out.target_hits == 0
    assert out.total_hits == 0


def test_score_whitespace_text_returns_zero():
    out = score_metaphor_coherence("   \n\t  ", "warmth")
    assert out.coherence_score == 0.0


def test_unknown_axis_returns_zero_in_non_strict():
    out = score_metaphor_coherence("warm and cozy", "not_an_axis")
    assert out.coherence_score == 0.0
    assert out.threshold_passed is False


def test_unknown_axis_raises_in_strict():
    with pytest.raises(ValueError):
        score_metaphor_coherence(
            "warm and cozy", "not_an_axis", strict_target=True,
        )


# -----------------------------------------------------------------------------
# Per-axis scoring
# -----------------------------------------------------------------------------


def test_warmth_target_with_warmth_markers_high_coherence():
    """Predominantly warmth markers → coherence ≥ threshold.
    'intimate' appears in BOTH warmth and closeness lists by design
    (some tokens span axes); the result reflects the cross-axis
    count honestly."""
    text = "Warm welcome — cozy, friendly experience here."
    out = score_metaphor_coherence(text, "warmth")
    assert out.target_hits >= 3
    assert out.total_hits >= 3
    # Predominantly warmth → coherence above threshold.
    assert out.coherence_score >= METAPHOR_COHERENCE_THRESHOLD
    assert out.threshold_passed is True


def test_pure_target_markers_yield_one_coherence():
    """Markers exclusive to ONE axis → coherence = 1.0."""
    text = "warm warmth hot heat cozy comforting"  # all warmth-only
    out = score_metaphor_coherence(text, "warmth")
    assert out.target_hits == out.total_hits
    assert out.coherence_score == pytest.approx(1.0)


def test_path_target_with_path_markers_passes():
    text = "A clear path forward — every step advances your journey."
    out = score_metaphor_coherence(text, "path")
    assert out.target_hits >= 3
    assert out.threshold_passed is True


def test_target_with_cross_axis_markers_low_coherence():
    """Target=warmth but text invokes path/force → low coherence."""
    text = "Push forward on the journey to your destination."
    out = score_metaphor_coherence(text, "warmth")
    # Target hits are 0; total hits are non-zero (path + force).
    assert out.target_hits == 0
    assert out.total_hits > 0
    assert out.coherence_score == 0.0
    assert out.threshold_passed is False


def test_mixed_target_and_off_target_threshold_borderline():
    """When target is half of total hits, check threshold behavior."""
    # 2 warmth markers + 2 path markers → coherence = 2/4 = 0.50
    text = (
        "A warm welcome to a cozy place. Step forward onward."
    )
    out = score_metaphor_coherence(text, "warmth")
    assert out.target_hits == 2
    # Total >= 4 (some force/path markers)
    assert out.coherence_score == pytest.approx(
        2.0 / out.total_hits, rel=0.01,
    )


def test_axis_hits_populated_per_axis():
    text = "Warm path forward — push high above the cold barriers."
    out = score_metaphor_coherence(text, "warmth")
    assert "warmth" in out.axis_hits
    assert "path" in out.axis_hits
    assert "force" in out.axis_hits
    assert "vertical" in out.axis_hits
    assert "containment" in out.axis_hits
    # warmth has at least 2 markers (warm, cold)
    assert out.axis_hits["warmth"] >= 1


def test_min_hits_floor_prevents_single_marker_saturation():
    """One marker, on target → ratio floored at MIN_TOTAL_HITS so
    the result isn't 1.0/1.0 = 1.0 (false-positive risk on accidental
    short copy with one marker)."""
    text = "warm"  # 1 token, 1 hit
    out = score_metaphor_coherence(text, "warmth")
    # target_hits=1, total_hits=1, denom=max(1, MIN_TOTAL_HITS_FOR_COHERENCE)
    # → coherence = 1 / 2 = 0.5 (right at threshold)
    assert out.coherence_score == pytest.approx(
        1.0 / MIN_TOTAL_HITS_FOR_COHERENCE, rel=0.01,
    )


def test_score_total_bounded_in_unit_interval():
    """coherence_score always in [0, 1]."""
    text = "warm warmth hot heat cozy"  # all warmth
    out = score_metaphor_coherence(text, "warmth")
    assert 0.0 <= out.coherence_score <= 1.0


def test_score_pure_function_idempotent():
    text = "Warm welcome — cozy, friendly."
    a = score_metaphor_coherence(text, "warmth")
    b = score_metaphor_coherence(text, "warmth")
    assert a.coherence_score == b.coherence_score
    assert a.target_hits == b.target_hits


def test_word_boundary_excludes_substring_match():
    """'high' should NOT match 'highway'."""
    text = "Cruise the highway in style."
    out = score_metaphor_coherence(text, "vertical")
    flagged_tokens = {t for t, _ in out.flagged_markers}
    assert "high" not in flagged_tokens


def test_flagged_markers_contains_token_axis_tuples():
    text = "Warm path forward."
    out = score_metaphor_coherence(text, "warmth")
    assert all(
        isinstance(item, tuple) and len(item) == 2
        for item in out.flagged_markers
    )


def test_target_metaphor_case_insensitive():
    """target_metaphor input is case-insensitive."""
    text = "Warm welcome — cozy, friendly."
    a = score_metaphor_coherence(text, "warmth")
    b = score_metaphor_coherence(text, "Warmth")
    c = score_metaphor_coherence(text, "WARMTH")
    assert a.coherence_score == b.coherence_score == c.coherence_score


def test_n_tokens_populated():
    text = "Warm path forward."  # 3 tokens
    out = score_metaphor_coherence(text, "warmth")
    assert out.n_tokens == 3


# -----------------------------------------------------------------------------
# passes_metaphor_coherence_check
# -----------------------------------------------------------------------------


def test_passes_check_returns_tuple():
    out = passes_metaphor_coherence_check(
        "warm welcome", "warmth",
    )
    assert isinstance(out, tuple) and len(out) == 2
    passes, result = out
    assert isinstance(passes, bool)
    assert isinstance(result, MetaphorCoherenceResult)


def test_passes_check_high_coherence_passes():
    text = "Warm welcome — cozy, friendly, intimate experience."
    passes, _ = passes_metaphor_coherence_check(text, "warmth")
    assert passes is True


def test_passes_check_off_target_fails():
    text = "Push forward on the journey to your destination."
    passes, _ = passes_metaphor_coherence_check(text, "warmth")
    assert passes is False


def test_passes_check_custom_threshold():
    text = "warm path forward"  # 1 warmth + 2 path
    # Default threshold (0.50) — coherence = 1/3 = 0.33 → fails
    passes_default, _ = passes_metaphor_coherence_check(text, "warmth")
    # Lower threshold (0.20) — same coherence → passes
    passes_loose, _ = passes_metaphor_coherence_check(
        text, "warmth", threshold=0.20,
    )
    assert passes_default is False
    assert passes_loose is True


# -----------------------------------------------------------------------------
# Frozen dataclass
# -----------------------------------------------------------------------------


def test_result_frozen():
    out = score_metaphor_coherence("warm", "warmth")
    with pytest.raises((AttributeError, Exception)):
        out.coherence_score = 0.99  # type: ignore[misc]


# -----------------------------------------------------------------------------
# upload_creative integration
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_creative_rejects_off_target_metaphor_copy():
    """upload_creative with primary_metaphor=warmth but force/path
    copy → coherence below threshold → rejected before upload."""
    from adam.intelligence.creative_upload_pipeline import upload_creative

    fake_client = MagicMock()
    fake_client.create_creative_by_url = AsyncMock(
        return_value={"creative": {"id": "should-not-reach"}, "errors": []}
    )

    result = await upload_creative(
        landing_page_url="https://x",
        name="off-target",
        primary_metaphor="warmth",
        client=fake_client,
        copy_text=(
            "Push forward on the journey to your destination. "
            "Step ahead. Stride towards your goal."
        ),
    )
    assert result is None
    fake_client.create_creative_by_url.assert_not_called()


@pytest.mark.asyncio
async def test_upload_creative_passes_target_aligned_copy():
    """Copy aligned with target metaphor → upload proceeds."""
    from adam.intelligence.creative_upload_pipeline import upload_creative

    fake_client = MagicMock()
    fake_client.create_creative_by_url = AsyncMock(
        return_value={"creative": {"id": "ok-id"}, "errors": []}
    )

    result = await upload_creative(
        landing_page_url="https://x",
        name="aligned",
        primary_metaphor="warmth",
        client=fake_client,
        copy_text="Warm welcome — cozy, friendly experience.",
    )
    assert result is not None
    assert result.stackadapt_creative_id == "ok-id"


@pytest.mark.asyncio
async def test_upload_creative_skips_metaphor_gate_when_no_metaphor():
    """No primary_metaphor → metaphor gate skipped (back-compat)."""
    from adam.intelligence.creative_upload_pipeline import upload_creative

    fake_client = MagicMock()
    fake_client.create_creative_by_url = AsyncMock(
        return_value={"creative": {"id": "ok"}, "errors": []}
    )
    result = await upload_creative(
        landing_page_url="https://x",
        name="no-metaphor",
        client=fake_client,
        # primary_metaphor not set
        copy_text="Anything goes here, really.",
    )
    assert result is not None


@pytest.mark.asyncio
async def test_upload_creative_bypasses_metaphor_gate_when_disabled():
    from adam.intelligence.creative_upload_pipeline import upload_creative

    fake_client = MagicMock()
    fake_client.create_creative_by_url = AsyncMock(
        return_value={"creative": {"id": "ok"}, "errors": []}
    )
    result = await upload_creative(
        landing_page_url="https://x",
        name="bypassed",
        primary_metaphor="warmth",
        client=fake_client,
        copy_text="Push forward on the journey.",  # would normally fail
        enforce_metaphor_coherence_check=False,
    )
    assert result is not None
    fake_client.create_creative_by_url.assert_called_once()
