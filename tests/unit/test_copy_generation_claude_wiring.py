"""Regression tests for ClaudeArgumentEngine wiring in CopyGenerationService.

Discipline anchors:
    - The canonical copy-emission path is `ClaudeArgumentEngine.generate()`
      (Doc 3 §I.6 V0). The f-string template path is DEPRECATED — A14
      flag COPY_TEMPLATES_AS_FALLBACK. These tests pin the wiring so the
      canonical path runs whenever its inputs are available, and the
      template fallback runs only when they aren't.
    - When archetype + edge_dimensions + Claude API key are all present,
      ClaudeArgumentEngine MUST be invoked and its output MUST replace
      the template emission.
    - When any of those inputs is missing, the gate returns None and the
      template path runs — preserving graceful degradation while
      preventing the engine from being silently bypassed when it should
      fire.
"""

from __future__ import annotations

import os
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from adam.output.copy_generation.service import CopyGenerationService


@pytest.fixture
def service() -> CopyGenerationService:
    return CopyGenerationService(brand_service=None, cache=None)


def _request_with(
    archetype: str = "careful_truster",
    edge_dimensions: dict = None,
):
    """Build a minimal CopyRequest-like object with the gate inputs.

    We don't fully construct CopyRequest because its Pydantic schema is
    extensive; we use a SimpleNamespace that satisfies attribute access
    via getattr(...) — which is how _try_claude_argument reads inputs.
    """
    from types import SimpleNamespace

    return SimpleNamespace(
        target_archetype=archetype,
        edge_dimensions=edge_dimensions or {
            "regulatory_fit": 0.62,
            "construal_fit": 0.55,
            "personality_alignment": 0.48,
            "emotional_resonance": 0.60,
            "value_alignment": 0.65,
        },
        diagnosed_barrier=None,
        brand_id="luxy_ride",
        product_name="LUXY Ride",
        product_description="premium executive transportation",
        product_category="luxury_transportation",
        abstraction_level=0.5,
    )


# -----------------------------------------------------------------------------
# Gate tests — when inputs are missing the canonical path MUST return None
# (caller falls through to templates). Failing these means the engine is
# attempting to fire on insufficient context.
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gate_returns_none_when_archetype_missing(service):
    request = _request_with(archetype=None)
    result = await service._try_claude_argument(request, brand=None)
    assert result is None


@pytest.mark.asyncio
async def test_gate_returns_none_when_edge_dimensions_empty(service):
    request = _request_with(edge_dimensions={})
    result = await service._try_claude_argument(request, brand=None)
    assert result is None


# -----------------------------------------------------------------------------
# Engine-init test — engine without API key must NOT be used (would emit
# canned LUXY-only copy from the engine's fallback table, wrong for
# non-LUXY brands and silently misleading for LUXY itself). The gate
# should detect "engine has no real client" and return None.
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gate_returns_none_when_no_api_key(service, monkeypatch):
    """With ANTHROPIC_API_KEY unset, the engine has no real client.
    The wiring must return None and let templates run — NOT use the
    engine's canned-LUXY-copy fallback path."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # Force re-init now that env is clean
    service._claude_argument_engine = None
    service._claude_argument_engine_attempted = False

    request = _request_with()
    result = await service._try_claude_argument(request, brand=None)
    assert result is None


# -----------------------------------------------------------------------------
# Canonical-path tests — when inputs and API key are present, the engine
# IS invoked and its output replaces the template emission. Failing these
# means the canonical path is silently inactive.
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_engine_invoked_when_all_inputs_present(service, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-fake-key-for-gate")
    service._claude_argument_engine = None
    service._claude_argument_engine_attempted = False

    request = _request_with()

    fake_argument = MagicMock()
    fake_argument.headline = "Mercedes S-Class. Verified drivers."
    fake_argument.body = "4.8 stars across 3,247 rides. Cancel free up to 24h."
    fake_argument.cta = "See driver profiles."

    fake_engine = MagicMock()
    fake_engine._client = MagicMock()  # truthy; passes the gate
    fake_engine.generate = AsyncMock(return_value=fake_argument)

    with patch.object(
        service,
        "_get_or_init_claude_argument_engine",
        return_value=fake_engine,
    ):
        result = await service._try_claude_argument(request, brand=None)

    assert fake_engine.generate.called, (
        "Engine.generate must be called when all inputs are present"
    )

    # Output assembled from headline + body + cta (canonical path output)
    assert result is not None
    assert "Mercedes S-Class" in result
    assert "4.8 stars" in result
    assert "See driver profiles" in result


@pytest.mark.asyncio
async def test_engine_invoked_with_correct_archetype_and_edges(service, monkeypatch):
    """Pin that the engine receives THE archetype and edge_dimensions
    (not stubbed defaults). Regression against silent input mangling.
    """
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-fake-key-for-gate")
    service._claude_argument_engine = None
    service._claude_argument_engine_attempted = False

    request = _request_with(
        archetype="reliable_cooperator",
        edge_dimensions={
            "regulatory_fit": 0.71,
            "construal_fit": 0.42,
            "personality_alignment": 0.55,
        },
    )

    fake_argument = MagicMock()
    fake_argument.headline = "x"
    fake_argument.body = "y"
    fake_argument.cta = "z"

    fake_engine = MagicMock()
    fake_engine._client = MagicMock()
    fake_engine.generate = AsyncMock(return_value=fake_argument)

    with patch.object(
        service,
        "_get_or_init_claude_argument_engine",
        return_value=fake_engine,
    ):
        await service._try_claude_argument(request, brand=None)

    call_kwargs = fake_engine.generate.await_args.kwargs
    assert call_kwargs["archetype_id"] == "reliable_cooperator"
    assert call_kwargs["bilateral_edge"]["regulatory_fit"] == 0.71
    assert call_kwargs["barrier"] == "trust_deficit"  # default for first-touch


@pytest.mark.asyncio
async def test_empty_engine_output_falls_through(service, monkeypatch):
    """Engine returning empty headline AND empty body → gate returns
    None → caller falls back to templates. Engine MUST NOT emit
    only-cta or otherwise partial output."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-fake-key-for-gate")
    service._claude_argument_engine = None
    service._claude_argument_engine_attempted = False

    request = _request_with()

    fake_argument = MagicMock()
    fake_argument.headline = ""
    fake_argument.body = ""
    fake_argument.cta = "click here"

    fake_engine = MagicMock()
    fake_engine._client = MagicMock()
    fake_engine.generate = AsyncMock(return_value=fake_argument)

    with patch.object(
        service,
        "_get_or_init_claude_argument_engine",
        return_value=fake_engine,
    ):
        result = await service._try_claude_argument(request, brand=None)

    assert result is None


@pytest.mark.asyncio
async def test_engine_exception_falls_through(service, monkeypatch):
    """Exception in engine.generate → gate returns None (does not
    propagate). Failing this means a transient API issue would crash
    every copy generation request instead of degrading to templates."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-fake-key-for-gate")
    service._claude_argument_engine = None
    service._claude_argument_engine_attempted = False

    request = _request_with()

    fake_engine = MagicMock()
    fake_engine._client = MagicMock()
    fake_engine.generate = AsyncMock(side_effect=RuntimeError("simulated"))

    with patch.object(
        service,
        "_get_or_init_claude_argument_engine",
        return_value=fake_engine,
    ):
        result = await service._try_claude_argument(request, brand=None)

    assert result is None
