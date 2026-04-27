"""Pin the M6 constitutional loop substrate.

Discipline anchors:
    - Interim heuristic scorers ARE NOT pretending to be G-Eval/FActScore.
      Their function names end with `_heuristic`; tests pin both
      directions (heuristic returns expected score on canonical inputs;
      function name signals 'interim' so swap to real DeepEval/factscore
      is unambiguous).
    - blend_dont_grab industry-default phrases ('compelling', 'break
      through', 'stand out', 'attention-grabbing', 'eye-catching') are
      detected by the archetype-fit scorer. The platform's deepest
      strategic commitment must be enforced even by the interim scorer.
    - Successful runs write to the B3 cache; failed runs (max_iter
      hit) do NOT. Caching a non-converged argument would defeat the
      entire constitutional check.
    - Thresholds 0.85 / 0.95 / max_iter=3 pinned; a future tune
      requires explicit code change visible in diff review.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adam.intelligence.argument_constitution import compose_constitution
from adam.intelligence.constitutional_loop import (
    ARCHETYPE_FIT_THRESHOLD,
    CAIResult,
    FACTSCORE_THRESHOLD,
    MAX_ITER,
    run_constitutional_loop,
    score_archetype_fit_heuristic,
    score_factual_grounding_heuristic,
)


# -----------------------------------------------------------------------------
# Canonical thresholds preserved from handoff §6.4
# -----------------------------------------------------------------------------


def test_thresholds_match_handoff_specification():
    """Handoff §6.4: archetype_fit ≥ 0.85, factscore ≥ 0.95, max_iter=3.
    Drift requires explicit edit visible in diff review."""
    assert ARCHETYPE_FIT_THRESHOLD == 0.85
    assert FACTSCORE_THRESHOLD == 0.95
    assert MAX_ITER == 3


# -----------------------------------------------------------------------------
# Heuristic archetype-fit scorer
# -----------------------------------------------------------------------------


def test_archetype_scorer_rewards_what_works_phrases():
    """Status seeker 'what_works' includes 'aspirational identity' —
    text containing it should score above baseline."""
    constitution = compose_constitution("status_seeker", "social_proof")
    text = (
        "Bespoke chauffeur service for those whose aspirational identity "
        "matches discreet exclusivity."
    )
    score = score_archetype_fit_heuristic(text, constitution)
    assert score > 0.7  # above baseline


def test_archetype_scorer_penalizes_what_fails_phrases():
    """Status seeker 'what_fails' includes 'self deprecation' — text
    containing forbidden phrasing should score below baseline."""
    constitution = compose_constitution("status_seeker", "social_proof")
    text = "We know we're a small player but with self deprecation we offer..."
    score = score_archetype_fit_heuristic(text, constitution)
    assert score < 0.7


def test_archetype_scorer_penalizes_blend_dont_grab_violations():
    """The platform's deepest strategic commitment: 'compelling',
    'break through', 'stand out', 'attention-grabbing' are forbidden.
    Even the interim heuristic scorer must enforce this."""
    constitution = compose_constitution("status_seeker", "social_proof")

    forbidden_examples = [
        "Our compelling headline grabs your attention.",
        "We break through the noise of competitors.",
        "Stand out from your peers with our service.",
        "An attention-grabbing experience awaits you.",
        "Eye-catching design meets premium service.",
    ]
    neutral_text = (
        "Bespoke chauffeur service used by professionals who value privacy."
    )
    neutral_score = score_archetype_fit_heuristic(neutral_text, constitution)

    for forbidden in forbidden_examples:
        forbidden_score = score_archetype_fit_heuristic(
            forbidden, constitution,
        )
        assert forbidden_score < neutral_score, (
            f"Forbidden phrase '{forbidden}' scored "
            f"{forbidden_score} >= neutral {neutral_score}"
        )


def test_archetype_scorer_clamped_to_unit_interval():
    constitution = compose_constitution("status_seeker", "social_proof")
    score = score_archetype_fit_heuristic("", constitution)
    assert 0.0 <= score <= 1.0


def test_archetype_scorer_handles_missing_constitution():
    score = score_archetype_fit_heuristic("any text", None)
    assert score == 0.0


# -----------------------------------------------------------------------------
# Heuristic factual-grounding scorer
# -----------------------------------------------------------------------------


def test_factscore_returns_threshold_on_empty_kb():
    """When brand_kb is empty, the cascade hasn't ingested KB data yet.
    Substrate path: pass at the threshold so the loop can still
    converge during pilot ramp-up before per-brand KB ingestion."""
    score = score_factual_grounding_heuristic(
        "Some text with claims.", brand_kb={},
    )
    assert score == FACTSCORE_THRESHOLD


def test_factscore_returns_one_on_text_with_no_factual_claims():
    """No factual claims → trivially passes (no hallucination risk)."""
    score = score_factual_grounding_heuristic(
        "  ",  # no factual content
        brand_kb={"name": "LUXY", "description": "transportation"},
    )
    assert score == 1.0


def test_factscore_grounded_text_passes():
    """Text whose factual claims overlap the KB scores high."""
    text = "LUXY operates in 5 markets with 200 chauffeurs."
    kb = {
        "name": "LUXY",
        "description": "Premium chauffeur service in 5 markets",
        "fleet": "200 trained chauffeurs and luxury vehicles",
    }
    score = score_factual_grounding_heuristic(text, kb)
    assert score >= 0.5


def test_factscore_handles_empty_text():
    score = score_factual_grounding_heuristic("", {"name": "LUXY"})
    assert score == 0.0


# -----------------------------------------------------------------------------
# Loop — convergence path
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_loop_converges_when_scorers_pass():
    """If both scorers return passing values immediately, the loop
    converges at iteration 0 (no critique/revise)."""
    engine = MagicMock()
    engine_result = MagicMock()
    engine_result.headline = "Quietly arrived"
    engine_result.body = "Discreet chauffeur service"
    engine_result.cta = "Open your private profile"
    engine.generate = AsyncMock(return_value=engine_result)

    with patch(
        "adam.intelligence.constitutional_loop.put_cached_argument",
    ) as mock_put:
        result = await run_constitutional_loop(
            brand_id="lux_luxy_ride",
            archetype="status_seeker",
            mechanism="social_proof",
            barrier="trust_deficit",
            brand_kb={"name": "LUXY"},
            engine=engine,
            archetype_fit_scorer=lambda text, c: 0.95,  # passes
            factscore_scorer=lambda text, kb: 0.99,      # passes
        )

    assert result.converged is True
    assert result.iterations == 0
    assert result.archetype_fit_score == 0.95
    assert result.factscore == 0.99
    mock_put.assert_called_once()


@pytest.mark.asyncio
async def test_loop_iterates_then_converges():
    """First pass fails archetype_fit; second pass passes. Loop
    converges at iteration 1 with critique log."""
    engine = MagicMock()
    engine_result = MagicMock()
    engine_result.headline = "h"
    engine_result.body = "b"
    engine_result.cta = "c"
    engine.generate = AsyncMock(return_value=engine_result)

    # Scorer returns failing on first call, passing on second
    call_count = {"n": 0}

    def archetype_scorer(text, constitution):
        call_count["n"] += 1
        return 0.95 if call_count["n"] >= 2 else 0.50

    with patch(
        "adam.intelligence.constitutional_loop.put_cached_argument",
    ):
        result = await run_constitutional_loop(
            brand_id="lux", archetype="status_seeker",
            mechanism="social_proof", barrier="trust_deficit",
            brand_kb={"name": "LUXY"},
            engine=engine,
            archetype_fit_scorer=archetype_scorer,
            factscore_scorer=lambda t, k: 0.99,
        )

    assert result.converged is True
    assert result.iterations == 1
    assert len(result.critique_log) == 1


# -----------------------------------------------------------------------------
# Loop — non-convergence path
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_loop_max_iter_publish_fails():
    """If the loop hits max_iter without converging, return
    converged=False with publish_failed_reason. Do NOT cache the
    non-converged argument."""
    engine = MagicMock()
    engine_result = MagicMock()
    engine_result.headline = "h"
    engine_result.body = "b"
    engine_result.cta = "c"
    engine.generate = AsyncMock(return_value=engine_result)

    with patch(
        "adam.intelligence.constitutional_loop.put_cached_argument",
    ) as mock_put:
        result = await run_constitutional_loop(
            brand_id="lux", archetype="status_seeker",
            mechanism="social_proof", barrier="trust_deficit",
            brand_kb={"name": "LUXY"},
            engine=engine,
            archetype_fit_scorer=lambda t, c: 0.50,  # always fails
            factscore_scorer=lambda t, k: 0.99,
        )

    assert result.converged is False
    assert result.iterations == MAX_ITER
    assert "max_iter" in result.publish_failed_reason
    # Non-converged arguments must NOT be cached
    mock_put.assert_not_called()


# -----------------------------------------------------------------------------
# Loop — early-exit paths
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_loop_unknown_archetype_returns_publish_fail():
    result = await run_constitutional_loop(
        brand_id="lux", archetype="totally_unknown",
        mechanism="social_proof", barrier="trust_deficit",
        brand_kb={"name": "LUXY"},
    )
    assert result.converged is False
    assert "unknown" in result.publish_failed_reason.lower()


@pytest.mark.asyncio
async def test_loop_unknown_mechanism_returns_publish_fail():
    result = await run_constitutional_loop(
        brand_id="lux", archetype="status_seeker",
        mechanism="totally_made_up", barrier="trust_deficit",
        brand_kb={"name": "LUXY"},
    )
    assert result.converged is False


@pytest.mark.asyncio
async def test_loop_no_engine_no_api_key_returns_publish_fail():
    """No engine + no API key → publish_fails cleanly. The cascade
    keeps using template fallback for this cell."""
    with patch(
        "adam.intelligence.argument_ranking._try_build_engine",
        return_value=None,
    ):
        result = await run_constitutional_loop(
            brand_id="lux", archetype="status_seeker",
            mechanism="social_proof", barrier="trust_deficit",
            brand_kb={"name": "LUXY"},
        )
    assert result.converged is False
    assert "claude" in result.publish_failed_reason.lower()


# -----------------------------------------------------------------------------
# Cache wire — successful loop writes the B3 cache
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_loop_caches_with_correct_cell_keys():
    """Successful run writes via put_cached_argument with the canonical
    (brand_id, archetype, mechanism, barrier) keys. The cascade reader
    uses the same keys."""
    engine = MagicMock()
    engine_result = MagicMock()
    engine_result.headline = "h"; engine_result.body = "b"; engine_result.cta = "c"
    engine.generate = AsyncMock(return_value=engine_result)

    with patch(
        "adam.intelligence.constitutional_loop.put_cached_argument",
    ) as mock_put:
        await run_constitutional_loop(
            brand_id="lux_luxy_ride",
            archetype="status_seeker",
            mechanism="social_proof",
            barrier="status_signaling_anxiety",
            brand_kb={"name": "LUXY"},
            engine=engine,
            archetype_fit_scorer=lambda t, c: 0.95,
            factscore_scorer=lambda t, k: 0.99,
        )

    call_kwargs = mock_put.call_args.kwargs
    assert call_kwargs["brand_id"] == "lux_luxy_ride"
    assert call_kwargs["archetype"] == "status_seeker"
    assert call_kwargs["mechanism"] == "social_proof"
    assert call_kwargs["barrier"] == "status_signaling_anxiety"


# -----------------------------------------------------------------------------
# Discipline: no-cache-on-failure
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_to_cache_false_skips_caching_even_on_success():
    """write_to_cache=False is for dry-run / testing. Even on
    convergence, no cache write."""
    engine = MagicMock()
    engine_result = MagicMock()
    engine_result.headline = "h"; engine_result.body = "b"; engine_result.cta = "c"
    engine.generate = AsyncMock(return_value=engine_result)

    with patch(
        "adam.intelligence.constitutional_loop.put_cached_argument",
    ) as mock_put:
        result = await run_constitutional_loop(
            brand_id="lux", archetype="status_seeker",
            mechanism="social_proof", barrier="trust_deficit",
            brand_kb={"name": "LUXY"},
            engine=engine,
            archetype_fit_scorer=lambda t, c: 0.95,
            factscore_scorer=lambda t, k: 0.99,
            write_to_cache=False,
        )

    assert result.converged is True
    mock_put.assert_not_called()
