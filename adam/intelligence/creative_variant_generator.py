# =============================================================================
# Section 6.4 — Creative variant generator (Claude API + 4-dimensional scoring)
# Location: adam/intelligence/creative_variant_generator.py
# =============================================================================
"""End-to-end creative variant generation per directive Section 6.4.

Per directive lines 798-808 (Section 6.4 — Primary-Metaphor-Driven
Creative Generation):

    "Claude API generates the variant under the constraint:
     'produce a variant that activates [primary metaphor] via
     [mechanism] for a user in [posture] pursuing [goal state].'
     Generated variants are scored against:
       — Primary-metaphor coherence with the target.
       — Mechanism-activation strength.
       — Predicted fluency against representative pages of the
         target posture.
       — Predicted reactance risk (independently scored — see below).
     Variants below thresholds are rejected; surviving variants
     enter the candidate pool. New variants are uploaded to
     StackAdapt via createCreativeByURL() with mechanism + metaphor
     + posture metadata."

Slice 21 closes the generation loop. The four scoring dimensions are
already shipped:
  - Slice 1: predicted fluency (posture × mechanism floor)
  - Slice 18: reactance risk
  - Slice 19: metaphor coherence
  - Slice 20: mechanism activation

This module composes them with Claude API generation under a
structured constraint prompt. Surviving variants (passing all four
gates) can be uploaded via the existing ``upload_creative`` from
Slice 13, which itself enforces the gates a second time as a defense.

WHAT THIS IS NOT

This is NOT a decision-time path. It runs OFFLINE — operator-triggered
or scheduled — to populate the candidate pool. Decision-time consumers
(cascade) read from the pool via Slice C lookup.

THE PRIMITIVE

  * ``CreativeVariantSpec`` — frozen dataclass: target_mechanism,
    primary_metaphor, posture_class, goal_state (optional), archetype
    (optional), brand_context (optional), max_words (optional).
  * ``GeneratedVariant`` — frozen dataclass: copy_text + per-dimension
    scores + passes_all_gates flag + rejection_reasons list.
  * ``generate_creative_variant(spec, claude_client, *, max_attempts)``
    — async; calls Claude with the directive's constraint prompt,
    parses the response, scores against all four dimensions; returns
    GeneratedVariant. Soft-fails on Claude error → returns variant
    with passes_all_gates=False + rejection_reasons populated.
  * ``CONSTRAINT_PROMPT_TEMPLATE`` — the directive's literal phrasing.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Section 6.4 lines 798-808 (constraint prompt
    + four scoring dimensions) + Slice 1 / 18 / 19 / 20 (the four
    scorers this slice composes). Prompt template uses the directive's
    EXACT wording from line 800 ("produce a variant that activates
    [primary metaphor] via [mechanism] for a user in [posture]
    pursuing [goal state]").

(b) Tests pin: prompt structure includes all four constraint slots;
    successful generation → variant with score dict; missing
    Claude client → returns failed variant + reason; Claude API
    raise → soft-fail to failed variant; empty Claude response →
    failed variant; passes_all_gates True iff every gate passes;
    rejection_reasons enumerates which gates failed; max_attempts
    retry on schema parse failure; GeneratedVariant frozen.

(c) calibration_pending=True. Prompt template + temperature (0.7
    for creative variation) + max_attempts (3) all pre-pilot.
    A14 flag: SECTION_6_4_GENERATOR_PILOT_PENDING. LUXY pilot via
    CMO walkthrough on generated-variant quality.

(d) Honest tags — what is NOT in this slice (named successors):

    * Multi-variant generation per cell (return N candidates, not 1).
      v0.1 returns ONE variant per call; multi-variant batching with
      diversity constraints is sibling.
    * Per-archetype prompt template tuning. v0.1 uses one prompt;
      archetype-conditioned templates are sibling.
    * Page-representative fluency scoring. v0.1 uses Slice 1's
      mechanism × posture floor as the predicted-fluency proxy;
      the directive's "representative pages of the target posture"
      requires page corpora + per-page fluency assessment. Sibling.
    * Iterative refinement (multi-turn). v0.1 single-turn; if a
      variant fails gates, the whole generation fails. Sibling slice
      runs refinement loops.
    * Cohort-level memoization (same (mechanism, metaphor, posture)
      cell, multiple brands → cache base prompt). Sibling.
    * Generated-creative diversity check (don't return clones of
      already-uploaded variants). Sibling.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# A14 SECTION_6_4_GENERATOR_PILOT_PENDING
DEFAULT_MAX_ATTEMPTS: int = 3
DEFAULT_GENERATION_TEMPERATURE: float = 0.7


# Directive Section 6.4 line 800 exact phrasing.
CONSTRAINT_PROMPT_TEMPLATE: str = (
    "Produce ONE ad copy variant that activates the primary metaphor "
    "[{primary_metaphor}] via the persuasion mechanism [{mechanism}] "
    "for a user in attentional posture [{posture_class}] "
    "pursuing the goal state [{goal_state}].\n\n"
    "Brand context: {brand_context}\n"
    "Archetype: {archetype}\n"
    "Maximum {max_words} words. The copy MUST:\n"
    "  - Predominantly invoke {primary_metaphor}-frame language "
    "(the dominant metaphor frame in the copy).\n"
    "  - Predominantly invoke {mechanism} mechanism vocabulary "
    "(the dominant persuasion lever in the copy).\n"
    "  - Be compatible with [{posture_class}] attentional posture "
    "(blend with the user's mode, do not grab against it).\n"
    "  - AVOID high-pressure markers ('act now', 'limited time', "
    "'hurry', countdown phrasing, scarcity-manipulation cues) — "
    "the system rejects creatives above a reactance-risk threshold.\n\n"
    "Return JSON: {{\"copy_text\": \"<the variant copy>\"}}.\n"
    "Output ONLY the JSON object, no surrounding prose."
)


@dataclass(frozen=True)
class CreativeVariantSpec:
    """Specification for one creative variant generation request.

    Maps directly to the directive's constraint-prompt slots
    (Section 6.4 line 800).
    """

    target_mechanism: str
    primary_metaphor: str
    posture_class: str
    goal_state: str = "general_consideration"
    archetype: str = "default"
    brand_context: str = ""
    max_words: int = 30


@dataclass(frozen=True)
class GeneratedVariant:
    """One generated + scored creative variant.

    ``copy_text``: the produced ad copy ("" when generation failed).
    ``passes_all_gates``: True iff all four gates passed AND the
        generation itself succeeded.
    ``coherence_score`` / ``mechanism_activation_score`` /
    ``reactance_score`` / ``fluency_eligible``: per-dimension
        outcomes. None when scoring couldn't run (e.g., generation
        empty).
    ``rejection_reasons``: list of strings naming gates that failed.
        Empty list when passes_all_gates=True. Non-empty even on
        partial success — operator-readable diagnostic.
    ``spec``: the spec that produced this variant (echoed for
        traceability).
    """

    copy_text: str
    passes_all_gates: bool
    coherence_score: Optional[float] = None
    mechanism_activation_score: Optional[float] = None
    reactance_score: Optional[float] = None
    fluency_eligible: Optional[bool] = None
    rejection_reasons: List[str] = field(default_factory=list)
    spec: Optional[CreativeVariantSpec] = None


def _build_constraint_prompt(spec: CreativeVariantSpec) -> str:
    """Format the directive's literal constraint phrasing."""
    return CONSTRAINT_PROMPT_TEMPLATE.format(
        primary_metaphor=spec.primary_metaphor,
        mechanism=spec.target_mechanism,
        posture_class=spec.posture_class,
        goal_state=spec.goal_state,
        archetype=spec.archetype,
        brand_context=spec.brand_context or "(no specific brand context)",
        max_words=spec.max_words,
    )


def _check_fluency_eligibility(
    mechanism: str, posture_class: str,
) -> bool:
    """Slice 1 substrate: posture × mechanism compatibility table.

    Inherits the existing fluency floor — if the (mechanism,
    posture_class) cell is LOW, the generated variant cannot pass
    the predicted-fluency check regardless of copy content. v0.1
    proxy for the directive's "representative pages of the target
    posture" full check.
    """
    try:
        from adam.intelligence.mechanism_fluency_floor import (
            MECHANISM_FLUENCY_FLOOR,
        )
        from adam.intelligence.posture_mechanism_prior import (
            compatibility_prior,
        )
        compat = compatibility_prior(
            mechanism=mechanism, posture=posture_class,
        )
        return float(compat) >= float(MECHANISM_FLUENCY_FLOOR)
    except Exception as exc:
        logger.debug(
            "fluency eligibility check failed (%s); fail-OPEN", exc,
        )
        return True  # fail-open — let downstream gates catch issues


def _parse_claude_json(content: str) -> Optional[str]:
    """Parse the Claude response as JSON; return copy_text when
    valid, None otherwise."""
    if not content:
        return None
    cleaned = content.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    try:
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(parsed, dict):
        return None
    copy_text = parsed.get("copy_text")
    if not isinstance(copy_text, str) or not copy_text.strip():
        return None
    return copy_text.strip()


async def _call_claude_for_variant(
    claude_client: Any,
    prompt: str,
    *,
    temperature: float = DEFAULT_GENERATION_TEMPERATURE,
) -> Optional[str]:
    """Single Claude call. Returns parsed copy_text or None."""
    try:
        response = await claude_client.complete(
            prompt=prompt,
            temperature=temperature,
        )
    except Exception as exc:
        logger.warning(
            "creative_variant_generator: Claude call raised: %s", exc,
        )
        return None

    content = getattr(response, "content", "") if response else ""
    return _parse_claude_json(content)


def _score_variant(
    copy_text: str, spec: CreativeVariantSpec,
) -> Tuple[float, float, float, bool, List[str]]:
    """Run the four gates against a generated variant.

    Returns (coherence, activation, reactance, fluency_ok,
    rejection_reasons).
    """
    from adam.intelligence.mechanism_activation_scorer import (
        passes_mechanism_activation_check,
    )
    from adam.intelligence.metaphor_coherence_scorer import (
        passes_metaphor_coherence_check,
    )
    from adam.intelligence.reactance_risk_scorer import (
        passes_reactance_check,
    )

    reasons: List[str] = []

    # Slice 19 — metaphor coherence
    coh_passes, coh_result = passes_metaphor_coherence_check(
        copy_text, spec.primary_metaphor,
    )
    if not coh_passes:
        reasons.append(
            f"metaphor_coherence_below_threshold "
            f"(score={coh_result.coherence_score:.3f})"
        )

    # Slice 20 — mechanism activation
    mech_passes, mech_result = passes_mechanism_activation_check(
        copy_text, spec.target_mechanism,
    )
    if not mech_passes:
        reasons.append(
            f"mechanism_activation_below_threshold "
            f"(score={mech_result.activation_score:.3f})"
        )

    # Slice 18 — reactance risk (REJECT if score >= threshold;
    # passes_reactance_check returns True when below).
    react_passes, react_result = passes_reactance_check(copy_text)
    if not react_passes:
        reasons.append(
            f"reactance_above_threshold "
            f"(score={react_result.total_score:.3f})"
        )

    # Slice 1 — predicted fluency proxy (mechanism × posture floor).
    fluency_ok = _check_fluency_eligibility(
        spec.target_mechanism, spec.posture_class,
    )
    if not fluency_ok:
        reasons.append("fluency_floor_low_posture_mechanism_cell")

    return (
        coh_result.coherence_score,
        mech_result.activation_score,
        react_result.total_score,
        fluency_ok,
        reasons,
    )


async def generate_creative_variant(
    spec: CreativeVariantSpec,
    claude_client: Optional[Any],
    *,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    temperature: float = DEFAULT_GENERATION_TEMPERATURE,
) -> GeneratedVariant:
    """Generate + score one creative variant per spec.

    Args:
        spec: the (mechanism, metaphor, posture, goal_state, archetype)
            cell to generate for.
        claude_client: a ClaudeClient instance (or duck-type with
            ``async complete(prompt, temperature) -> response``).
            None → returns failed variant.
        max_attempts: retry on JSON parse failures (Claude
            occasionally wraps with extra prose).
        temperature: generation temperature. Default 0.7.

    Returns:
        ``GeneratedVariant``. ``passes_all_gates=True`` iff every
        gate passed and generation succeeded.

    Soft-fail discipline: any error → returns a GeneratedVariant
    with copy_text="" + passes_all_gates=False + rejection_reasons
    naming the failure. Never raises into the caller.
    """
    if claude_client is None:
        return GeneratedVariant(
            copy_text="",
            passes_all_gates=False,
            rejection_reasons=["no_claude_client"],
            spec=spec,
        )

    prompt = _build_constraint_prompt(spec)

    copy_text: Optional[str] = None
    for attempt in range(max(1, max_attempts)):
        copy_text = await _call_claude_for_variant(
            claude_client, prompt, temperature=temperature,
        )
        if copy_text:
            break

    if not copy_text:
        return GeneratedVariant(
            copy_text="",
            passes_all_gates=False,
            rejection_reasons=[
                f"claude_generation_failed_after_{max_attempts}_attempts"
            ],
            spec=spec,
        )

    coh, mech_act, react, fluency_ok, reasons = _score_variant(
        copy_text, spec,
    )
    passes = len(reasons) == 0

    return GeneratedVariant(
        copy_text=copy_text,
        passes_all_gates=passes,
        coherence_score=coh,
        mechanism_activation_score=mech_act,
        reactance_score=react,
        fluency_eligible=fluency_ok,
        rejection_reasons=reasons,
        spec=spec,
    )
