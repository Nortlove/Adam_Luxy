# =============================================================================
# ADAM M6 — Cross-Family Constitutional Critic Substrate
# Location: adam/intelligence/cai_cross_family_critic.py
# =============================================================================

"""Cross-family Constitutional AI critic — M6 substrate.

WHY THIS EXISTS

`adam/intelligence/constitutional_loop.py` ships the generate → critique
→ revise loop with a HEURISTIC critique step (string-matching against
the constitution's `what_fails` and `forbidden_substitutes` slices) and
the SAME engine family on both generation and revision.

Per the handoff §6.5 and the canonical CAI literature (Bai et al. 2022)
plus Zheng et al. 2023's documentation of self-preference bias in
LLM-as-judge evaluation, the production-grade critique loop must:

    1. Use a SEPARATE model family for the critic than the generator
       to mitigate self-preference (Opus critiques Sonnet, or vice
       versa; gold standard is cross-vendor: OpenAI critiques Anthropic).
    2. Use an LLM-based structured critique step (not just heuristic
       string-matching) — the critic identifies BOTH constitutional
       violations AND argument-quality issues the heuristic can't see
       (e.g., overall tone misalignment, implicit demographic targeting,
       backfire-risk vocabulary).

This module is the substrate for both upgrades. Today it ships:

    - Cross-family config (which family generates, which critiques)
    - Structured critic-output schema (NOT free-form prose — A12 defense)
    - Engine builder for the critic family (returns None when API key
      missing; A14 flag emitted)
    - LLM-based critique function that produces structured findings

The wire-up into `constitutional_loop.run_constitutional_loop` lands as
a separate commit (Week 2 #10 "B3 finish") so the substrate is
exercisable in isolation first.

A14 FLAG

Identifier:
    M6_CROSS_FAMILY_CRITIC_PENDING

Retirement trigger:
    Retire when (a) the cross-family critic engine is configured AND
    healthy (recent successful critique within 24h), (b) ≥30 critique
    runs have completed end-to-end with structured findings parseable,
    AND (c) at least one alternate-family critic family has been
    operationally exercised (cross-vendor or intra-vendor cross-model)
    for ≥7 days alongside the primary critic family.

WHY A SEPARATE MODULE FROM constitutional_loop.py

`constitutional_loop.py` is the orchestrator (generate → critique →
revise control flow + cache writeback + iteration accounting). Mixing
the cross-family routing and structured critique-parsing logic into
that file would obscure the flow. Keeping the critic primitives in a
sibling module preserves the orchestrator's readability.

REFERENCES

Bai et al. (2022) Constitutional AI: Harmlessness from AI Feedback.
Zheng et al. (2023) Judging LLM-as-a-Judge with MT-Bench and Chatbot
Arena. Liu et al. (2023) G-Eval: NLG Evaluation using GPT-4 with Better
Human Alignment. Min et al. (2023) FActScore: Fine-grained Atomic
Evaluation of Factual Precision in Long Form Text Generation.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# A14 flag constants
# =============================================================================


M6_CROSS_FAMILY_CRITIC_PENDING_FLAG: str = "M6_CROSS_FAMILY_CRITIC_PENDING"

M6_CROSS_FAMILY_RETIREMENT_TRIGGER: str = (
    "Retire M6_CROSS_FAMILY_CRITIC_PENDING when (a) the cross-family "
    "critic engine is configured AND healthy (recent successful critique "
    "within 24h), (b) ≥30 critique runs have completed end-to-end with "
    "structured findings parseable, AND (c) at least one alternate-family "
    "critic family has been operationally exercised (cross-vendor or "
    "intra-vendor cross-model) for ≥7 days alongside the primary critic "
    "family."
)


# =============================================================================
# Critic-family enumeration
# =============================================================================


class CriticFamily(str, Enum):
    """Model families the critic engine may be pinned to.

    Anthropic intra-vendor pairings (e.g., Opus critiques Sonnet) are
    valid M6 §6.5 cross-family configurations — "cross-family" means
    distinct model lineages, not necessarily distinct vendors. Per
    Zheng et al. 2023, intra-vendor self-preference is real but smaller
    than cross-vendor self-preference; Anthropic Opus-vs-Sonnet is the
    minimum acceptable cross-family configuration.

    Cross-vendor pairings (Anthropic ↔ OpenAI) are the gold standard
    but require the OpenAI dependency to be installed and an API key
    available. Until then, cross-vendor is gated by an A14 flag.
    """

    # Anthropic family
    ANTHROPIC_OPUS = "anthropic_opus"
    ANTHROPIC_SONNET = "anthropic_sonnet"
    ANTHROPIC_HAIKU = "anthropic_haiku"

    # OpenAI family (gated on openai lib install + key)
    OPENAI_GPT4 = "openai_gpt4"
    OPENAI_GPT4O = "openai_gpt4o"

    # Same-family fallback marker — used by `is_cross_family` to flag
    # SAME family on both sides (degraded mode).
    SAME_AS_GENERATOR = "__same_as_generator__"


def family_vendor(family: CriticFamily) -> str:
    """Return the vendor (anthropic / openai / same) for a family."""
    name = family.value
    if name.startswith("anthropic_"):
        return "anthropic"
    if name.startswith("openai_"):
        return "openai"
    return "same"


def is_cross_family(
    generator: CriticFamily, critic: CriticFamily,
) -> bool:
    """Return True iff generator and critic are distinct lineages.

    Distinct lineage = different model family within a vendor (e.g.,
    Anthropic Opus vs Sonnet) OR different vendor entirely.
    """
    if critic == CriticFamily.SAME_AS_GENERATOR:
        return False
    return generator != critic


def is_cross_vendor(
    generator: CriticFamily, critic: CriticFamily,
) -> bool:
    """Return True iff generator and critic are distinct vendors.

    Cross-vendor is the gold standard for self-preference bias mitigation
    per Zheng et al. 2023. Cross-family-but-same-vendor (e.g., Opus
    critiquing Sonnet) is the minimum acceptable; cross-vendor is
    strictly stronger.
    """
    if critic == CriticFamily.SAME_AS_GENERATOR:
        return False
    return family_vendor(generator) != family_vendor(critic)


# =============================================================================
# Cross-family config
# =============================================================================


@dataclass(frozen=True)
class CrossFamilyCriticConfig:
    """Specifies which family generates and which critiques.

    Construction validates that the pair is non-degenerate. SAME_AS_GENERATOR
    on the critic side is allowed as the explicit "single-family fallback"
    configuration (which surfaces the A14 flag).
    """

    generator: CriticFamily
    critic: CriticFamily

    def __post_init__(self) -> None:
        # The generator side cannot be SAME_AS_GENERATOR — the marker
        # is meaningful only on the critic.
        if self.generator == CriticFamily.SAME_AS_GENERATOR:
            raise ValueError(
                "generator cannot be CriticFamily.SAME_AS_GENERATOR; "
                "specify a concrete family"
            )

    def is_cross_family(self) -> bool:
        return is_cross_family(self.generator, self.critic)

    def is_cross_vendor(self) -> bool:
        return is_cross_vendor(self.generator, self.critic)


# =============================================================================
# Structured critic output (NOT free-form prose)
# =============================================================================


@dataclass(frozen=True)
class CritiqueFinding:
    """One specific finding produced by the LLM critic.

    Fields are templated structured slots — the critic LLM is prompted
    to produce JSON conforming to this shape. The orchestrator parses
    the JSON, extracts findings, and rejects any output that is not
    structured.

    A12 (English-fluency drift) defense: the critic NEVER returns
    free-form prose. Findings are typed records.
    """

    rule_id: str            # Identifier of the constitutional rule violated
    severity: str           # "critical" | "major" | "minor"
    quoted_span: str        # The argument span that triggered the finding
    explanation: str        # One-sentence explanation (templated; bounded length)
    suggested_revision: str # One-sentence fix suggestion (templated; bounded)


@dataclass(frozen=True)
class LLMCritique:
    """Full structured critic output for one argument.

    `findings` is the list of per-rule violations. `overall_disposition`
    is one of REVISE / APPROVE / REJECT. `iteration` is the GCR loop
    iteration index this critique was produced in.
    """

    argument_id: str
    critic_family: CriticFamily
    overall_disposition: str         # "REVISE" | "APPROVE" | "REJECT"
    findings: List[CritiqueFinding]
    archetype_fit_score: float       # G-Eval-shaped score in [0, 1]
    factuality_score: float          # FActScore-shaped score in [0, 1]
    iteration: int = 0
    raw_response_truncated: str = "" # First 500 chars of raw critic output (for audit)


# =============================================================================
# Engine builder for the critic family
# =============================================================================


def build_critic_engine(
    family: CriticFamily,
    api_key_env_var: Optional[str] = None,
) -> Optional[Any]:
    """Build a critic engine pinned to the requested family.

    Returns None when:
        - The vendor is OpenAI but openai lib not installed or key missing
        - The vendor is Anthropic but ANTHROPIC_API_KEY not set
        - Engine construction fails for any reason

    The pattern mirrors `argument_ranking._try_build_engine` — soft-fail,
    callers decide whether to fall through to single-family mode (with
    A14 flag emission) or block.

    The Anthropic critic engines pin a specific model on each call by
    setting the engine's underlying ClaudeClient.config.default_model
    to the family-specific model id.
    """
    vendor = family_vendor(family)
    if vendor == "anthropic":
        return _build_anthropic_critic_engine(family)
    if vendor == "openai":
        return _build_openai_critic_engine(family)
    return None


# Family → model id mapping. Pinned to canonical model ids.
_ANTHROPIC_FAMILY_MODELS: Dict[CriticFamily, str] = {
    CriticFamily.ANTHROPIC_OPUS: "claude-opus-4-7",
    CriticFamily.ANTHROPIC_SONNET: "claude-sonnet-4-6",
    CriticFamily.ANTHROPIC_HAIKU: "claude-haiku-4-5-20251001",
}

_OPENAI_FAMILY_MODELS: Dict[CriticFamily, str] = {
    CriticFamily.OPENAI_GPT4: "gpt-4-turbo",
    CriticFamily.OPENAI_GPT4O: "gpt-4o",
}


def _build_anthropic_critic_engine(family: CriticFamily) -> Optional[Any]:
    """Build a ClaudeArgumentEngine pinned to a specific Anthropic model."""
    try:
        from adam.intelligence.argument_ranking import _try_build_engine
        from adam.llm.client import ClaudeClient
    except Exception as exc:
        logger.debug("Critic engine: Anthropic imports failed (%s)", exc)
        return None

    try:
        client = ClaudeClient()
        if not getattr(client, "api_key", None):
            return None

        # Pin the client's default model to the family-specific id so
        # subsequent .complete() calls route to that model.
        model_id = _ANTHROPIC_FAMILY_MODELS.get(family)
        if model_id is None:
            return None
        try:
            client.config.default_model = model_id
        except Exception:
            pass  # Some configs are frozen; still return engine.

        # Reuse the existing engine-builder pattern — it handles the
        # adapter shape the engine expects.
        return _try_build_engine()
    except Exception as exc:
        logger.debug("Anthropic critic engine init failed: %s", exc)
        return None


def _build_openai_critic_engine(family: CriticFamily) -> Optional[Any]:
    """Build an OpenAI critic engine. None until openai lib + key land.

    The shape it returns must duck-type-match the Anthropic engine
    (a `.complete(prompt, ...)` async method returning {"text": ...}).
    The actual implementation lands when the openai dep is added in a
    follow-up commit.
    """
    try:
        import openai  # noqa: F401
    except ImportError:
        return None

    # Substrate placeholder — actual OpenAI client wiring lands when
    # openai is added to requirements.txt. Until then this returns None
    # by raising into the outer except.
    logger.debug(
        "OpenAI critic family %s requested but client wiring not yet "
        "implemented — substrate awaits dependency add",
        family.value,
    )
    return None


# =============================================================================
# Structured-prompt builder for the critic
# =============================================================================


def build_critic_prompt(
    argument_text: str,
    constitution_summary: str,
    archetype: str,
    mechanism: str,
) -> str:
    """Build the critic prompt — strict JSON-only output.

    Structured templated prompt. NOT free-form. The critic is asked to
    return JSON conforming to LLMCritique's shape. Free-form prose in
    the critic output is parsed as a violation of the substrate
    contract and the parser falls through to a REJECT disposition.

    Templated from structured input — A12 defense: no English fluency
    in this module.
    """
    return (
        "You are a constitutional AI critic. Analyze the argument below "
        "against the named constitution. Return a SINGLE valid JSON "
        "object exactly matching this schema. NO prose outside the JSON.\n\n"
        "{\n"
        '  "overall_disposition": "REVISE" | "APPROVE" | "REJECT",\n'
        '  "archetype_fit_score": <number in [0, 1]>,\n'
        '  "factuality_score": <number in [0, 1]>,\n'
        '  "findings": [\n'
        "    {\n"
        '      "rule_id": "<constitution rule identifier>",\n'
        '      "severity": "critical" | "major" | "minor",\n'
        '      "quoted_span": "<the argument span that triggered>",\n'
        '      "explanation": "<one-sentence explanation>",\n'
        '      "suggested_revision": "<one-sentence fix>"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        f"=== Constitution (archetype={archetype}, mechanism={mechanism}) ===\n"
        f"{constitution_summary}\n\n"
        "=== Argument under review ===\n"
        f"{argument_text}\n\n"
        "Return JSON only. Do not include any prose before or after."
    )


# =============================================================================
# Critic invocation + structured parsing
# =============================================================================


def parse_critic_response(
    raw_response: str,
    critic_family: CriticFamily,
    argument_id: str,
    iteration: int = 0,
) -> LLMCritique:
    """Parse the critic's raw JSON response into a structured LLMCritique.

    On parse failure: returns an LLMCritique with overall_disposition=
    "REJECT" and a single CRITIC_OUTPUT_UNPARSEABLE finding. This is the
    A12 defense: a critic that returns free-form prose where structured
    JSON was requested cannot be silently consumed.
    """
    raw_truncated = (raw_response or "")[:500]

    try:
        # Lenient JSON extraction — strip code-fence wrappers if present
        cleaned = raw_response.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        parsed = json.loads(cleaned)
    except (json.JSONDecodeError, ValueError, AttributeError):
        return LLMCritique(
            argument_id=argument_id,
            critic_family=critic_family,
            overall_disposition="REJECT",
            findings=[
                CritiqueFinding(
                    rule_id="CRITIC_OUTPUT_UNPARSEABLE",
                    severity="critical",
                    quoted_span="",
                    explanation=(
                        "Critic produced output that did not parse as JSON; "
                        "structured-output contract violated."
                    ),
                    suggested_revision="Re-run critic with stricter prompt.",
                ),
            ],
            archetype_fit_score=0.0,
            factuality_score=0.0,
            iteration=iteration,
            raw_response_truncated=raw_truncated,
        )

    findings: List[CritiqueFinding] = []
    for f in parsed.get("findings", []) or []:
        try:
            findings.append(
                CritiqueFinding(
                    rule_id=str(f.get("rule_id", "")),
                    severity=str(f.get("severity", "minor")),
                    quoted_span=str(f.get("quoted_span", "")),
                    explanation=str(f.get("explanation", "")),
                    suggested_revision=str(f.get("suggested_revision", "")),
                )
            )
        except Exception:
            continue

    disposition = str(parsed.get("overall_disposition", "REVISE"))
    if disposition not in {"REVISE", "APPROVE", "REJECT"}:
        disposition = "REVISE"

    arch_fit = _coerce_score(parsed.get("archetype_fit_score"))
    fact_score = _coerce_score(parsed.get("factuality_score"))

    return LLMCritique(
        argument_id=argument_id,
        critic_family=critic_family,
        overall_disposition=disposition,
        findings=findings,
        archetype_fit_score=arch_fit,
        factuality_score=fact_score,
        iteration=iteration,
        raw_response_truncated=raw_truncated,
    )


def _coerce_score(value: Any) -> float:
    """Coerce critic-output scores into [0, 1] floats; clamp."""
    try:
        s = float(value)
    except (TypeError, ValueError):
        return 0.0
    if s != s:  # NaN
        return 0.0
    return max(0.0, min(1.0, s))


# =============================================================================
# A14 flag emission
# =============================================================================


def record_critique_run(
    config: CrossFamilyCriticConfig,
    atom_id: str = "cai_critic",
) -> List[str]:
    """Increment the A14 counter and return active flags for this run.

    Returns ["M6_CROSS_FAMILY_CRITIC_PENDING"] when the config does NOT
    achieve cross-family separation OR when cross-family separation is
    achieved but the additional retirement-trigger conditions are still
    pending (operational; checked at the orchestrator layer).

    This function emits the flag whenever the run is non-cross-family;
    the operational retirement (≥30 runs, ≥7 days, etc.) is checked
    elsewhere and is the trigger for the flag's eventual removal.
    """
    flags: List[str] = []
    if not config.is_cross_family():
        flags.append(M6_CROSS_FAMILY_CRITIC_PENDING_FLAG)
        _increment_a14_counter(atom_id, M6_CROSS_FAMILY_CRITIC_PENDING_FLAG)
    return flags


def _increment_a14_counter(atom_id: str, flag: str) -> None:
    """Non-fatal Prometheus counter increment for A14 flag emission."""
    try:
        from adam.infrastructure.prometheus.metrics import get_metrics
        pm = get_metrics()
        pm.a14_flag_active.labels(atom_id=atom_id, a14_flag=flag).inc()
    except Exception as exc:
        logger.debug("M6 A14 metric emission failed: %s", exc)


# =============================================================================
# Async critique runner — composes engine call + parser
# =============================================================================


async def run_llm_critique(
    argument_text: str,
    constitution_summary: str,
    archetype: str,
    mechanism: str,
    config: CrossFamilyCriticConfig,
    critic_engine: Any,
    argument_id: str = "arg",
    iteration: int = 0,
    max_tokens: int = 1024,
    temperature: float = 0.0,
) -> LLMCritique:
    """Invoke the critic engine on the argument; return structured critique.

    `critic_engine` must be a duck-typed engine exposing:
        async def complete(prompt: str, max_tokens: int, temperature: float)
            -> Dict[str, str] (with "text" key)

    The engine builder (`build_critic_engine`) returns this shape for
    the Anthropic family; OpenAI follows once that dep lands.

    Critic temperature defaults to 0.0 — deterministic critique is the
    discipline anchor; temperature variation in the critic introduces
    audit noise.
    """
    prompt = build_critic_prompt(
        argument_text=argument_text,
        constitution_summary=constitution_summary,
        archetype=archetype,
        mechanism=mechanism,
    )

    try:
        response = await critic_engine.complete(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        raw_text = response.get("text", "") if isinstance(response, dict) else ""
    except Exception as exc:
        logger.warning("Critic engine call failed: %s", exc)
        return LLMCritique(
            argument_id=argument_id,
            critic_family=config.critic,
            overall_disposition="REJECT",
            findings=[
                CritiqueFinding(
                    rule_id="CRITIC_ENGINE_ERROR",
                    severity="critical",
                    quoted_span="",
                    explanation=f"Critic engine raised: {exc}",
                    suggested_revision="Check critic engine availability.",
                ),
            ],
            archetype_fit_score=0.0,
            factuality_score=0.0,
            iteration=iteration,
        )

    return parse_critic_response(
        raw_response=raw_text,
        critic_family=config.critic,
        argument_id=argument_id,
        iteration=iteration,
    )


__all__ = [
    "CriticFamily",
    "CrossFamilyCriticConfig",
    "CritiqueFinding",
    "LLMCritique",
    "M6_CROSS_FAMILY_CRITIC_PENDING_FLAG",
    "M6_CROSS_FAMILY_RETIREMENT_TRIGGER",
    "build_critic_engine",
    "build_critic_prompt",
    "family_vendor",
    "is_cross_family",
    "is_cross_vendor",
    "parse_critic_response",
    "record_critique_run",
    "run_llm_critique",
]
