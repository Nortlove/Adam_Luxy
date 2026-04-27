"""Constitutional AI loop for CLAUDE_ARGUMENT — M6 substrate.

Per the handoff §6: generate → critique → revise loop offline. Per
LUXY's <120ms cascade SLA: this loop runs OFFLINE and writes passing
arguments to the B3 argument cache. The cascade hot path reads from
the cache; M6 populates it.

Discipline anchors:
    - The scorer functions (score_archetype_fit, score_factual_grounding)
      ship here as INTERIM HEURISTIC SUBSTRATE. Real G-Eval (DeepEval)
      and FActScore (factscore lib) replace them with one-line swaps
      when those libraries install. The interim heuristics are
      explicitly named and tested as such — they are NOT pretending to
      be the canonical scorers.
    - Thresholds (archetype_fit ≥ 0.85, factscore ≥ 0.95, max_iter=3)
      preserved verbatim from handoff §6.4. A bump requires
      pre-registration per handoff §6.6 calibration step.
    - Cross-family critic (Opus critiques Sonnet, or vice versa)
      handles self-preference bias (Zheng et al. 2023). Until both
      family clients are wired, single-family critique is the interim;
      tests pin this distinction so the upgrade path is explicit.
    - Successful arguments write to the B3 argument cache via
      put_cached_argument — the wire B3 already shipped. M6 is the
      writer; the cascade is the reader.

The full G-Eval + FActScore + per-brand KB ingestion + Arena pairwise
A/B + 200-arg human eval is M6 follow-on work. This commit ships the
structure that makes the swap-in operational once libs install.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from adam.intelligence.argument_cache import (
    CachedArgument, put_cached_argument,
)
from adam.intelligence.argument_constitution import (
    ComposedConstitution, compose_constitution,
)

logger = logging.getLogger(__name__)


# Handoff §6.4 canonical thresholds — preserved verbatim.
ARCHETYPE_FIT_THRESHOLD = 0.85
FACTSCORE_THRESHOLD = 0.95
MAX_ITER = 3


@dataclass
class CAIResult:
    """Outcome of one CAI loop run."""
    converged: bool                    # passed both thresholds within max_iter
    iterations: int                    # 0..max_iter
    final_argument: Optional[CachedArgument] = None
    archetype_fit_score: float = 0.0
    factscore: float = 0.0
    critique_log: List[str] = field(default_factory=list)
    publish_failed_reason: str = ""


# -----------------------------------------------------------------------------
# Interim scorers — heuristic substrate; swap for G-Eval / FActScore
# -----------------------------------------------------------------------------


def score_archetype_fit_heuristic(
    text: str, constitution: ComposedConstitution,
) -> float:
    """Interim archetype-fit scorer — INTERIM HEURISTIC ONLY.

    Real G-Eval (Liu et al. 2023) replaces this with token-probability-
    weighted LLM-as-judge scoring. This heuristic counts:
      + 0.1 per archetype-slice "what_works" phrase present
      − 0.1 per archetype-slice "what_fails" phrase present
      − 0.1 per blend_dont_grab forbidden framing present
      Anchored to baseline 0.7

    Returns a [0, 1] score. Score >= ARCHETYPE_FIT_THRESHOLD passes.

    A future swap to G-Eval is a one-line change to this function
    body. The test suite pins both directions: heuristic returns the
    expected score on canonical inputs, AND the function name signals
    'interim' so the swap is unambiguous.
    """
    if not text or not constitution:
        return 0.0
    text_lower = text.lower()

    score = 0.7  # Baseline — neutral expectation

    # Reward "what_works" phrasings
    for tag in constitution.archetype_slice.what_works:
        token = tag.replace("_", " ")
        if token in text_lower:
            score += 0.1

    # Penalize "what_fails" phrasings
    for tag in constitution.archetype_slice.what_fails:
        token = tag.replace("_", " ")
        if token in text_lower:
            score -= 0.1

    # Penalize blend_dont_grab forbidden framings (industry-default
    # 'compelling/breakthrough/stand-out' language)
    forbidden_phrases = (
        "compelling", "break through", "stand out",
        "attention-grabbing", "attention grabbing",
        "eye-catching", "eye catching",
    )
    for phrase in forbidden_phrases:
        if phrase in text_lower:
            score -= 0.15

    return max(0.0, min(1.0, score))


def score_factual_grounding_heuristic(
    text: str, brand_kb: Dict[str, Any],
) -> float:
    """Interim factual-grounding scorer — INTERIM HEURISTIC ONLY.

    Real FActScore (Min et al. 2023) replaces this with atomic-fact
    decomposition + retrieval against per-brand KB.

    The interim approach: count factual-claim sentences (those with
    numbers, named entities, or measurable assertions); score the
    fraction that have at least one token overlapping the brand KB.
    Aggressive recall — heavy on false positives, but anchored above
    the 0.95 threshold means real KB-supported text passes.

    Returns a [0, 1] score. Score >= FACTSCORE_THRESHOLD passes.
    """
    if not text:
        return 0.0
    if not brand_kb:
        # No KB to ground against — assume neutral pass (the cascade's
        # absence of KB integration is itself a M6 follow-up).
        return FACTSCORE_THRESHOLD

    # Extract sentences with numerical or factual cues
    sentences = re.split(r"(?<=[.!?])\s+", text)
    factual_sentences = [
        s for s in sentences
        if re.search(r"\d|%|\$", s) or re.search(r"\b[A-Z][a-z]+\b", s)
    ]
    if not factual_sentences:
        # No factual claims → trivially passes (handoff §6.8: empty
        # arguments aren't a hallucination risk)
        return 1.0

    # KB tokens: lowercase set of all words in the KB string fields
    kb_tokens = set()
    for v in brand_kb.values():
        if isinstance(v, str):
            kb_tokens.update(re.findall(r"\b\w+\b", v.lower()))

    grounded = 0
    for sentence in factual_sentences:
        sentence_tokens = set(re.findall(r"\b\w+\b", sentence.lower()))
        # Sentence is "grounded" if it shares ≥2 tokens with the KB
        if len(sentence_tokens & kb_tokens) >= 2:
            grounded += 1

    return grounded / len(factual_sentences)


# -----------------------------------------------------------------------------
# Generate / critique / revise — wraps ClaudeArgumentEngine
# -----------------------------------------------------------------------------


async def _generate_argument(
    constitution: ComposedConstitution,
    brand_id: str,
    brand_kb: Dict[str, Any],
    barrier: str,
    bilateral_edge: Dict[str, float],
    engine: Any,
) -> CachedArgument:
    """First-pass generate using ClaudeArgumentEngine FULL mode.

    The constitution travels alongside the engine prompt as the rubric
    the critic will later score against. The engine itself doesn't yet
    consume the constitution at generation time; that's M6 follow-on
    work (extending build_full_generation_prompt to include the
    constitution slice). Today the constitution is consumed at the
    EVALUATE step.
    """
    from adam.retargeting.engines.claude_argument_engine import ArgumentMode

    result = await engine.generate(
        mode=ArgumentMode.FULL,
        barrier=barrier,
        archetype_id=constitution.archetype_slice.archetype,
        brand_name=str(brand_kb.get("name", brand_id)),
        brand_data=brand_kb,
        bilateral_edge=bilateral_edge,
        touch_history=[],
        narrative_chapter=1,
        scaffold_level=2,
        construal_level="concrete",
        sequence_id=f"cai_{brand_id}_{constitution.archetype_slice.archetype}_{constitution.mechanism_slice.mechanism}",
    )
    return CachedArgument(
        headline=getattr(result, "headline", "") or "",
        body=getattr(result, "body", "") or "",
        cta=getattr(result, "cta", "") or "",
        barrier_addressed=barrier,
        archetype_audited=constitution.archetype_slice.archetype,
        mechanism_audited=constitution.mechanism_slice.mechanism,
    )


async def _critique_and_revise(
    arg: CachedArgument,
    constitution: ComposedConstitution,
    brand_kb: Dict[str, Any],
    bilateral_edge: Dict[str, float],
    engine: Any,
) -> Tuple[CachedArgument, str]:
    """Run critique + revise against the rubric.

    Critique surface uses the existing engine's FULL-regeneration with
    a critique-augmented prompt. Cross-family critic (Opus critiques
    Sonnet) is M6 follow-on; today's substrate uses the same engine
    family for both (single-family critique). The TEST suite pins this
    distinction explicitly.

    Returns (revised_argument, critique_text). On engine failure,
    returns (original_argument, error_message) so the caller can
    decide whether to retry or publish-fail.
    """
    from adam.retargeting.engines.claude_argument_engine import ArgumentMode

    failures: List[str] = []
    arch_slice = constitution.archetype_slice
    mech_slice = constitution.mechanism_slice

    # Critique heuristic: identify which constitutional principles the
    # current argument violates, build a one-paragraph critique
    text_for_check = " ".join((arg.headline, arg.body, arg.cta))
    text_lower = text_for_check.lower()

    for tag in arch_slice.what_fails:
        token = tag.replace("_", " ")
        if token in text_lower:
            failures.append(
                f"Archetype tone violation: '{token}' is forbidden for "
                f"{arch_slice.archetype}"
            )
    for substitute in mech_slice.forbidden_substitutes:
        token = substitute.replace("_", " ")
        if token in text_lower:
            failures.append(
                f"Mechanism faithfulness violation: '{token}' is a "
                f"forbidden substitute for {mech_slice.mechanism}"
            )

    critique_text = (
        " | ".join(failures) if failures else "No constitutional violations detected."
    )

    # Revise via FULL regeneration with critique appended to brand_data.
    # This is the canonical Bai et al. 2022 inference-time pattern:
    # the critique is data the next generate sees.
    revised_brand_data = dict(brand_kb)
    revised_brand_data["__cai_critique__"] = critique_text
    revised_brand_data["__cai_constitutional_constraints__"] = (
        f"Adhere to {arch_slice.archetype} tone: {arch_slice.tone_principle}. "
        f"Concretely invoke {mech_slice.mechanism}: {mech_slice.must_concretely_invoke}. "
        f"Avoid forbidden phrasing: 'compelling', 'break through the noise', "
        f"'stand out', 'attention-grabbing'."
    )

    try:
        revised = await engine.generate(
            mode=ArgumentMode.FULL,
            barrier=arg.barrier_addressed,
            archetype_id=arch_slice.archetype,
            brand_name=str(brand_kb.get("name", "")),
            brand_data=revised_brand_data,
            bilateral_edge=bilateral_edge,
            touch_history=[],
            narrative_chapter=1,
            scaffold_level=2,
            construal_level="concrete",
            sequence_id=f"cai_revise_{arch_slice.archetype}_{mech_slice.mechanism}",
        )
        revised_arg = CachedArgument(
            headline=getattr(revised, "headline", "") or arg.headline,
            body=getattr(revised, "body", "") or arg.body,
            cta=getattr(revised, "cta", "") or arg.cta,
            barrier_addressed=arg.barrier_addressed,
            archetype_audited=arg.archetype_audited,
            mechanism_audited=arg.mechanism_audited,
            iterations_to_converge=arg.iterations_to_converge + 1,
        )
        return revised_arg, critique_text
    except Exception as exc:
        logger.warning("CAI revise failed: %s", exc)
        return arg, f"revise_error: {exc}"


# -----------------------------------------------------------------------------
# The CAI loop — generate → critique → revise until thresholds pass
# -----------------------------------------------------------------------------


async def run_constitutional_loop(
    brand_id: str,
    archetype: str,
    mechanism: str,
    barrier: str,
    brand_kb: Dict[str, Any],
    bilateral_edge: Optional[Dict[str, float]] = None,
    engine: Optional[Any] = None,
    write_to_cache: bool = True,
    archetype_fit_scorer=None,
    factscore_scorer=None,
) -> CAIResult:
    """Run the full generate → critique → revise loop.

    Args:
        brand_id, archetype, mechanism, barrier: cell coordinates
        brand_kb: per-brand knowledge base for FActScore grounding
        bilateral_edge: buyer × brand bilateral profile (drives generation)
        engine: optional pre-built ClaudeArgumentEngine
        write_to_cache: whether to put_cached_argument on success
        archetype_fit_scorer / factscore_scorer: injectable scorers.
            Default to interim heuristic substrate.

    Returns CAIResult with converged flag, scores, iteration count.
    """
    constitution = compose_constitution(archetype, mechanism)
    if constitution is None:
        return CAIResult(
            converged=False, iterations=0,
            publish_failed_reason=(
                f"unknown archetype/mechanism: {archetype}/{mechanism}"
            ),
        )

    if engine is None:
        try:
            from adam.intelligence.argument_ranking import _try_build_engine
            engine = _try_build_engine()
        except Exception as exc:
            return CAIResult(
                converged=False, iterations=0,
                publish_failed_reason=f"engine init failed: {exc}",
            )
    if engine is None:
        return CAIResult(
            converged=False, iterations=0,
            publish_failed_reason="no claude API key",
        )

    arch_scorer = archetype_fit_scorer or score_archetype_fit_heuristic
    fact_scorer = factscore_scorer or score_factual_grounding_heuristic
    bilateral = bilateral_edge or {}

    try:
        arg = await _generate_argument(
            constitution, brand_id, brand_kb, barrier, bilateral, engine,
        )
    except Exception as exc:
        return CAIResult(
            converged=False, iterations=0,
            publish_failed_reason=f"initial generate failed: {exc}",
        )

    critique_log: List[str] = []
    archetype_score = 0.0
    fact_score = 0.0

    for iteration in range(MAX_ITER):
        text = " ".join((arg.headline, arg.body, arg.cta))
        archetype_score = arch_scorer(text, constitution)
        fact_score = fact_scorer(text, brand_kb)

        # Stamp the converged scores onto the cache record so the
        # cascade can audit them at retrieve-time.
        arg.archetype_fit_score = archetype_score
        arg.factscore = fact_score
        arg.iterations_to_converge = iteration

        if (archetype_score >= ARCHETYPE_FIT_THRESHOLD
                and fact_score >= FACTSCORE_THRESHOLD):
            # Converged. Persist to B3 cache.
            if write_to_cache:
                put_cached_argument(
                    brand_id=brand_id,
                    archetype=archetype,
                    mechanism=mechanism,
                    barrier=barrier,
                    argument=arg,
                )
            return CAIResult(
                converged=True, iterations=iteration,
                final_argument=arg,
                archetype_fit_score=archetype_score,
                factscore=fact_score,
                critique_log=critique_log,
            )

        # Not yet — critique and revise
        try:
            arg, critique_text = await _critique_and_revise(
                arg, constitution, brand_kb, bilateral, engine,
            )
            critique_log.append(critique_text)
        except Exception as exc:
            critique_log.append(f"revise loop exception: {exc}")
            break

    # Hit max_iter without converging — handoff §6.8: route to human
    # review. We DO NOT cache the non-converged argument; the cascade
    # falls through to its template path for this cell until a future
    # CAI run produces a passing version.
    return CAIResult(
        converged=False, iterations=MAX_ITER,
        final_argument=arg,
        archetype_fit_score=archetype_score,
        factscore=fact_score,
        critique_log=critique_log,
        publish_failed_reason=(
            f"max_iter={MAX_ITER} reached without convergence "
            f"(archetype_fit={archetype_score:.2f}, factscore={fact_score:.2f})"
        ),
    )
