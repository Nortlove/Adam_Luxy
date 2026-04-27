"""Variant ranking via ClaudeArgumentEngine RANKING mode.

This is the B4 production gate — wires the RANKING operating mode of the
ClaudeArgumentEngine onto the variant-generation path. Variant generators
(CopyGenerationService._generate_variants and parallels) emit 3-4
candidates with statically-assigned confidence scores. RANKING re-orders
them against the buyer's bilateral edge profile in ~100ms (vs FULL's
~500ms — the engine docstring at adam/retargeting/engines/
claude_argument_engine.py:21).

Discipline:
    The RANKING engine returns ranked_indices — a permutation of the input
    list. We use this for ORDERING only. We do NOT fabricate new confidence
    scores from rank position; that would be the same drift pattern as the
    previously-caught corrected_d × 50.0 fudge factor. Original confidence
    values stay attached to their variants; the ordering changes.

    Honest framing: ranking tells us relative order, not absolute scores.
    Treating rank-1 as "0.9 confidence" is invention. Treating rank-1 as
    "the variant Claude picked first given THIS bilateral edge" is the
    truth.

Soft-fail by design:
    Missing engine, missing API key, malformed engine response, exception
    in the call — all return the input list unchanged. Variant generation
    must never break because the ranker's offline.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence, TypeVar

logger = logging.getLogger(__name__)


T = TypeVar("T")


async def rank_variants_via_claude(
    variants: Sequence[T],
    text_extractor,
    barrier: str,
    archetype_id: str,
    bilateral_edge: Dict[str, float],
    engine: Optional[Any] = None,
) -> List[T]:
    """Rank a list of variants by predicted effectiveness for this buyer.

    Args:
        variants: any sequence of variant-shaped objects
        text_extractor: callable taking one variant → its display text string
        barrier: diagnosed psychological barrier (e.g. "trust_deficit")
        archetype_id: resolved archetype name
        bilateral_edge: buyer's edge dimensions (the ranker's grounding)
        engine: optional pre-built ClaudeArgumentEngine; if None, attempts
                to build one with a real ClaudeClient. None on no-API-key.

    Returns:
        A NEW list with the same items in the order Claude ranked them.
        On any failure path, returns list(variants) — the input order.

    Never raises. Soft-fails on every error.
    """
    if not variants or len(variants) < 2:
        # Nothing to rank — single variant is its own ranking.
        return list(variants)

    try:
        texts = [text_extractor(v) for v in variants]
    except Exception as exc:
        logger.debug("Variant ranking: text extraction failed (%s)", exc)
        return list(variants)

    # Filter out empty/None texts — ranker can't operate on them.
    if any(not t for t in texts):
        logger.debug("Variant ranking: at least one variant has empty text; skipping")
        return list(variants)

    # Build engine if one wasn't passed in.
    eng = engine
    if eng is None:
        eng = _try_build_engine()
    if eng is None:
        return list(variants)

    try:
        from adam.retargeting.engines.claude_argument_engine import (
            ArgumentMode,
        )
        result = await eng.generate(
            mode=ArgumentMode.RANKING,
            barrier=barrier,
            archetype_id=archetype_id,
            bilateral_edge=bilateral_edge,
            arguments_to_rank=list(texts),
        )
    except Exception as exc:
        logger.debug("Variant ranking: engine.generate failed (%s)", exc)
        return list(variants)

    indices = list(getattr(result, "ranked_indices", None) or [])
    # Validate the permutation. RANKING mode is supposed to return a
    # permutation of [0..n-1]; if it returned junk, fall through.
    if not _is_valid_permutation(indices, len(variants)):
        logger.debug(
            "Variant ranking: indices %s are not a valid permutation of %d",
            indices, len(variants),
        )
        return list(variants)

    return [variants[i] for i in indices]


def _is_valid_permutation(indices: Sequence[int], n: int) -> bool:
    if len(indices) != n:
        return False
    return sorted(indices) == list(range(n))


def _try_build_engine() -> Optional[Any]:
    """Build a ClaudeArgumentEngine wired to a real ClaudeClient.

    Returns None when ANTHROPIC_API_KEY isn't set, when the engine module
    isn't importable, or when client construction fails. Mirrors the
    soft-fail pattern in copy_generation/service.py:_get_or_init_claude_argument_engine.
    """
    try:
        from adam.retargeting.engines.claude_argument_engine import (
            ClaudeArgumentEngine,
        )
        from adam.llm.client import ClaudeClient
    except Exception as exc:
        logger.debug("Variant ranking: engine imports failed (%s)", exc)
        return None

    try:
        client = ClaudeClient()
        if not getattr(client, "api_key", None):
            return None

        # Same adapter shape used in CopyGenerationService — the engine's
        # ._client expects .complete(prompt, max_tokens, temperature) →
        # dict with "text" key. ClaudeClient returns ClaudeResponse with
        # .content; wrap.
        class _CompleteAdapter:
            def __init__(self, claude_client):
                self._claude_client = claude_client

            async def complete(
                self, prompt: str,
                max_tokens: int = 500, temperature: float = 0.7,
            ) -> Dict[str, str]:
                response = await self._claude_client.complete(
                    prompt=prompt, max_tokens=max_tokens, temperature=temperature,
                )
                text = (
                    response.content if hasattr(response, "content") else str(response)
                )
                return {"text": text}

        return ClaudeArgumentEngine(claude_client=_CompleteAdapter(client))
    except Exception as exc:
        logger.debug("Variant ranking: engine init failed (%s)", exc)
        return None
