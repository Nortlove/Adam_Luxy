"""Pin RANKING-mode wiring — variant reorder via ClaudeArgumentEngine.

Discipline anchors:
    - We use ranked_indices for ordering ONLY. We do NOT invent new
      confidence scores from rank position. Variants keep their original
      confidence values; only their position in the list changes.
    - Soft-fail on every error. The variant generator must never break
      because the ranker's offline.
    - Permutation validation prevents a malformed engine response from
      silently truncating or duplicating the variant list.
"""

from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock

import pytest

from adam.intelligence.argument_ranking import rank_variants_via_claude


@dataclass
class _Variant:
    text: str
    confidence: float


def _engine_returning(indices):
    """Build a mock engine whose generate() returns the given indices."""
    engine = MagicMock()
    result = MagicMock()
    result.ranked_indices = indices
    engine.generate = AsyncMock(return_value=result)
    return engine


# -----------------------------------------------------------------------------
# Happy path — reorder by Claude's indices
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reorders_variants_by_claude_indices():
    variants = [
        _Variant("first", 0.5),
        _Variant("second", 0.6),
        _Variant("third", 0.7),
    ]
    # Claude says: 2 (third) is best, then 0 (first), then 1 (second)
    engine = _engine_returning([2, 0, 1])

    result = await rank_variants_via_claude(
        variants=variants,
        text_extractor=lambda v: v.text,
        barrier="trust_deficit",
        archetype_id="status_seeker",
        bilateral_edge={"regulatory_fit": 0.7},
        engine=engine,
    )

    assert [v.text for v in result] == ["third", "first", "second"]


@pytest.mark.asyncio
async def test_preserves_original_confidence_values():
    """The ranker reorders ONLY. Variants must keep their original
    confidence values — no fabrication from rank position."""
    variants = [
        _Variant("a", 0.5),
        _Variant("b", 0.6),
        _Variant("c", 0.7),
    ]
    engine = _engine_returning([2, 0, 1])

    result = await rank_variants_via_claude(
        variants=variants,
        text_extractor=lambda v: v.text,
        barrier="trust_deficit",
        archetype_id="status_seeker",
        bilateral_edge={},
        engine=engine,
    )

    # The variant at rank-1 still has its original 0.7 confidence,
    # not a manufactured "0.9 because it's first"
    assert result[0].confidence == 0.7  # was "c"
    assert result[1].confidence == 0.5  # was "a"
    assert result[2].confidence == 0.6  # was "b"


@pytest.mark.asyncio
async def test_returns_new_list_does_not_mutate_input():
    """Ranker returns a NEW list. Caller's input must not be mutated —
    a future caller that holds a reference to the unranked list would
    silently see it reordered."""
    variants = [_Variant("a", 0.5), _Variant("b", 0.6)]
    original = list(variants)
    engine = _engine_returning([1, 0])

    result = await rank_variants_via_claude(
        variants=variants, text_extractor=lambda v: v.text,
        barrier="x", archetype_id="status_seeker",
        bilateral_edge={}, engine=engine,
    )

    assert variants == original   # input unchanged
    assert result is not variants  # new list


# -----------------------------------------------------------------------------
# Soft-fail paths
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_variant_returns_unchanged():
    """A list of 1 needs no ranking; engine is never called."""
    variants = [_Variant("only", 0.5)]
    engine = MagicMock()
    engine.generate = AsyncMock(side_effect=AssertionError("must not be called"))

    result = await rank_variants_via_claude(
        variants=variants, text_extractor=lambda v: v.text,
        barrier="x", archetype_id="status_seeker",
        bilateral_edge={}, engine=engine,
    )

    assert result == variants


@pytest.mark.asyncio
async def test_empty_list_returns_unchanged():
    engine = MagicMock()
    engine.generate = AsyncMock(side_effect=AssertionError("must not be called"))
    result = await rank_variants_via_claude(
        variants=[], text_extractor=lambda v: v.text,
        barrier="x", archetype_id="status_seeker",
        bilateral_edge={}, engine=engine,
    )
    assert result == []


@pytest.mark.asyncio
async def test_no_engine_returns_input_order():
    """When no engine is passed AND no real client can be built (no API
    key in test env), variants pass through in original order."""
    variants = [_Variant("a", 0.5), _Variant("b", 0.6)]

    # No engine, no API key → returns input order. The actual ClaudeClient
    # build will fail or return None inside _try_build_engine.
    result = await rank_variants_via_claude(
        variants=variants, text_extractor=lambda v: v.text,
        barrier="x", archetype_id="status_seeker",
        bilateral_edge={}, engine=None,
    )

    # Either the engine couldn't be built (no API key) → input order,
    # OR the build succeeded and engine.generate failed → input order.
    # Either way, soft-fall returns input order.
    assert [v.text for v in result] == ["a", "b"]


@pytest.mark.asyncio
async def test_engine_exception_returns_input_order():
    variants = [_Variant("a", 0.5), _Variant("b", 0.6)]
    engine = MagicMock()
    engine.generate = AsyncMock(side_effect=ConnectionError("API down"))

    result = await rank_variants_via_claude(
        variants=variants, text_extractor=lambda v: v.text,
        barrier="x", archetype_id="status_seeker",
        bilateral_edge={}, engine=engine,
    )
    assert [v.text for v in result] == ["a", "b"]


@pytest.mark.asyncio
async def test_text_extractor_exception_returns_input_order():
    variants = [_Variant("a", 0.5), _Variant("b", 0.6)]
    engine = _engine_returning([1, 0])

    def broken_extractor(v):
        raise ValueError("extractor blew up")

    result = await rank_variants_via_claude(
        variants=variants, text_extractor=broken_extractor,
        barrier="x", archetype_id="status_seeker",
        bilateral_edge={}, engine=engine,
    )
    assert [v.text for v in result] == ["a", "b"]


@pytest.mark.asyncio
async def test_empty_text_skips_ranking():
    """Ranker can't operate on empty-text variants — skip rather than
    pass garbage to the engine."""
    variants = [_Variant("", 0.5), _Variant("real", 0.6)]
    engine = MagicMock()
    engine.generate = AsyncMock(side_effect=AssertionError("must not be called"))

    result = await rank_variants_via_claude(
        variants=variants, text_extractor=lambda v: v.text,
        barrier="x", archetype_id="status_seeker",
        bilateral_edge={}, engine=engine,
    )
    assert [v.text for v in result] == ["", "real"]


# -----------------------------------------------------------------------------
# Permutation validation
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_permutation_too_short_returns_input_order():
    """Engine returns indices [1] for 2 variants — invalid. Fall through."""
    variants = [_Variant("a", 0.5), _Variant("b", 0.6)]
    engine = _engine_returning([1])

    result = await rank_variants_via_claude(
        variants=variants, text_extractor=lambda v: v.text,
        barrier="x", archetype_id="status_seeker",
        bilateral_edge={}, engine=engine,
    )
    assert [v.text for v in result] == ["a", "b"]


@pytest.mark.asyncio
async def test_invalid_permutation_with_duplicate_returns_input_order():
    """Engine returns [0, 0] — invalid permutation. Fall through rather
    than serve a result with one variant duplicated and one missing."""
    variants = [_Variant("a", 0.5), _Variant("b", 0.6)]
    engine = _engine_returning([0, 0])

    result = await rank_variants_via_claude(
        variants=variants, text_extractor=lambda v: v.text,
        barrier="x", archetype_id="status_seeker",
        bilateral_edge={}, engine=engine,
    )
    assert [v.text for v in result] == ["a", "b"]


@pytest.mark.asyncio
async def test_invalid_permutation_out_of_range_returns_input_order():
    """Engine returns [0, 5] — index 5 doesn't exist for 2 variants.
    Fall through."""
    variants = [_Variant("a", 0.5), _Variant("b", 0.6)]
    engine = _engine_returning([0, 5])

    result = await rank_variants_via_claude(
        variants=variants, text_extractor=lambda v: v.text,
        barrier="x", archetype_id="status_seeker",
        bilateral_edge={}, engine=engine,
    )
    assert [v.text for v in result] == ["a", "b"]


@pytest.mark.asyncio
async def test_engine_returns_no_indices_returns_input_order():
    """Engine result has empty/missing ranked_indices — fall through."""
    engine = MagicMock()
    result = MagicMock()
    result.ranked_indices = []
    engine.generate = AsyncMock(return_value=result)

    variants = [_Variant("a", 0.5), _Variant("b", 0.6)]
    out = await rank_variants_via_claude(
        variants=variants, text_extractor=lambda v: v.text,
        barrier="x", archetype_id="status_seeker",
        bilateral_edge={}, engine=engine,
    )
    assert [v.text for v in out] == ["a", "b"]
