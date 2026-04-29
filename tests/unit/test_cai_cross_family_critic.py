# =============================================================================
# ADAM B3 — Cross-Family Constitutional Critic Substrate Tests
# Location: tests/unit/test_cai_cross_family_critic.py
# =============================================================================

"""Tests for `adam.intelligence.cai_cross_family_critic`.

Pins the load-bearing structural claims:
    1. CriticFamily enumeration is stable
    2. is_cross_family + is_cross_vendor classification is correct
    3. CrossFamilyCriticConfig validates non-degenerate generator
    4. build_critic_prompt produces a JSON-only contract prompt
    5. parse_critic_response handles structured output AND falls back
       to REJECT on unparseable input (A12 defense)
    6. run_llm_critique with a mock engine produces a structured critique
    7. record_critique_run emits A14 flag on same-family configs
    8. A14 flag identifier + retirement trigger documented
"""

from __future__ import annotations

import json

import pytest

from adam.intelligence.cai_cross_family_critic import (
    CriticFamily,
    CrossFamilyCriticConfig,
    CritiqueFinding,
    LLMCritique,
    M6_CROSS_FAMILY_CRITIC_PENDING_FLAG,
    M6_CROSS_FAMILY_RETIREMENT_TRIGGER,
    build_critic_prompt,
    family_vendor,
    is_cross_family,
    is_cross_vendor,
    parse_critic_response,
    record_critique_run,
    run_llm_critique,
)


# -----------------------------------------------------------------------------
# Family classification
# -----------------------------------------------------------------------------


class TestCriticFamilyClassification:

    def test_family_vendor_anthropic(self):
        assert family_vendor(CriticFamily.ANTHROPIC_OPUS) == "anthropic"
        assert family_vendor(CriticFamily.ANTHROPIC_SONNET) == "anthropic"
        assert family_vendor(CriticFamily.ANTHROPIC_HAIKU) == "anthropic"

    def test_family_vendor_openai(self):
        assert family_vendor(CriticFamily.OPENAI_GPT4) == "openai"
        assert family_vendor(CriticFamily.OPENAI_GPT4O) == "openai"

    def test_family_vendor_same(self):
        assert family_vendor(CriticFamily.SAME_AS_GENERATOR) == "same"

    def test_is_cross_family_distinct_anthropic_models(self):
        # Opus critiquing Sonnet is M6 §6.5 minimum cross-family.
        assert is_cross_family(
            CriticFamily.ANTHROPIC_SONNET, CriticFamily.ANTHROPIC_OPUS,
        ) is True

    def test_is_cross_family_same_anthropic_model(self):
        assert is_cross_family(
            CriticFamily.ANTHROPIC_SONNET, CriticFamily.ANTHROPIC_SONNET,
        ) is False

    def test_is_cross_family_same_marker(self):
        assert is_cross_family(
            CriticFamily.ANTHROPIC_SONNET, CriticFamily.SAME_AS_GENERATOR,
        ) is False

    def test_is_cross_family_cross_vendor(self):
        assert is_cross_family(
            CriticFamily.ANTHROPIC_SONNET, CriticFamily.OPENAI_GPT4,
        ) is True

    def test_is_cross_vendor_intra_anthropic(self):
        # Opus vs Sonnet — cross-family but SAME vendor.
        assert is_cross_vendor(
            CriticFamily.ANTHROPIC_SONNET, CriticFamily.ANTHROPIC_OPUS,
        ) is False

    def test_is_cross_vendor_distinct_vendors(self):
        assert is_cross_vendor(
            CriticFamily.ANTHROPIC_SONNET, CriticFamily.OPENAI_GPT4,
        ) is True

    def test_is_cross_vendor_same_marker(self):
        assert is_cross_vendor(
            CriticFamily.ANTHROPIC_SONNET, CriticFamily.SAME_AS_GENERATOR,
        ) is False


# -----------------------------------------------------------------------------
# Config validation
# -----------------------------------------------------------------------------


class TestCrossFamilyCriticConfig:

    def test_valid_intra_anthropic_config(self):
        cfg = CrossFamilyCriticConfig(
            generator=CriticFamily.ANTHROPIC_SONNET,
            critic=CriticFamily.ANTHROPIC_OPUS,
        )
        assert cfg.is_cross_family() is True
        assert cfg.is_cross_vendor() is False

    def test_valid_cross_vendor_config(self):
        cfg = CrossFamilyCriticConfig(
            generator=CriticFamily.ANTHROPIC_SONNET,
            critic=CriticFamily.OPENAI_GPT4,
        )
        assert cfg.is_cross_family() is True
        assert cfg.is_cross_vendor() is True

    def test_same_family_config_is_cross_family_false(self):
        cfg = CrossFamilyCriticConfig(
            generator=CriticFamily.ANTHROPIC_SONNET,
            critic=CriticFamily.SAME_AS_GENERATOR,
        )
        assert cfg.is_cross_family() is False

    def test_generator_cannot_be_same_marker(self):
        with pytest.raises(ValueError):
            CrossFamilyCriticConfig(
                generator=CriticFamily.SAME_AS_GENERATOR,
                critic=CriticFamily.ANTHROPIC_OPUS,
            )


# -----------------------------------------------------------------------------
# Prompt builder — JSON-only contract
# -----------------------------------------------------------------------------


class TestBuildCriticPrompt:

    def test_prompt_demands_json_only(self):
        prompt = build_critic_prompt(
            argument_text="Book a black car.",
            constitution_summary="No demographic targeting.",
            archetype="careful_truster",
            mechanism="authority",
        )
        # Strict-output anchors that prevent prose drift.
        assert "JSON" in prompt
        assert "Return JSON only" in prompt
        assert "NO prose outside the JSON" in prompt or "Do not include" in prompt
        assert "overall_disposition" in prompt
        assert "findings" in prompt

    def test_prompt_includes_argument_and_constitution(self):
        prompt = build_critic_prompt(
            argument_text="My specific argument text",
            constitution_summary="My constitution summary",
            archetype="careful_truster",
            mechanism="authority",
        )
        assert "My specific argument text" in prompt
        assert "My constitution summary" in prompt
        assert "careful_truster" in prompt
        assert "authority" in prompt


# -----------------------------------------------------------------------------
# Response parser — structured + REJECT-on-unparseable
# -----------------------------------------------------------------------------


class TestParseCriticResponse:

    def test_parse_valid_json(self):
        raw = json.dumps({
            "overall_disposition": "REVISE",
            "archetype_fit_score": 0.72,
            "factuality_score": 0.91,
            "findings": [
                {
                    "rule_id": "ARCHETYPE_TONE_MISMATCH",
                    "severity": "major",
                    "quoted_span": "compelling offer",
                    "explanation": "Compelling violates blend-don't-grab.",
                    "suggested_revision": "Replace with mechanism-faithful framing.",
                },
            ],
        })
        critique = parse_critic_response(
            raw_response=raw,
            critic_family=CriticFamily.ANTHROPIC_OPUS,
            argument_id="arg_test",
            iteration=1,
        )
        assert critique.overall_disposition == "REVISE"
        assert critique.archetype_fit_score == 0.72
        assert critique.factuality_score == 0.91
        assert len(critique.findings) == 1
        assert critique.findings[0].rule_id == "ARCHETYPE_TONE_MISMATCH"
        assert critique.findings[0].severity == "major"
        assert critique.iteration == 1

    def test_parse_handles_code_fence_wrapping(self):
        raw = (
            "```json\n"
            + json.dumps({
                "overall_disposition": "APPROVE",
                "archetype_fit_score": 0.92,
                "factuality_score": 0.97,
                "findings": [],
            })
            + "\n```"
        )
        critique = parse_critic_response(
            raw_response=raw,
            critic_family=CriticFamily.ANTHROPIC_OPUS,
            argument_id="arg_test",
        )
        assert critique.overall_disposition == "APPROVE"
        assert len(critique.findings) == 0

    def test_unparseable_response_falls_back_to_reject(self):
        # Free-form prose where JSON was demanded → REJECT with
        # CRITIC_OUTPUT_UNPARSEABLE finding. A12 defense.
        critique = parse_critic_response(
            raw_response="This argument is fine, looks good!",
            critic_family=CriticFamily.ANTHROPIC_OPUS,
            argument_id="arg_test",
        )
        assert critique.overall_disposition == "REJECT"
        assert len(critique.findings) == 1
        assert critique.findings[0].rule_id == "CRITIC_OUTPUT_UNPARSEABLE"
        assert critique.findings[0].severity == "critical"

    def test_invalid_disposition_normalized_to_revise(self):
        raw = json.dumps({
            "overall_disposition": "DESTROY",
            "archetype_fit_score": 0.5,
            "factuality_score": 0.5,
            "findings": [],
        })
        critique = parse_critic_response(
            raw_response=raw,
            critic_family=CriticFamily.ANTHROPIC_OPUS,
            argument_id="arg_test",
        )
        assert critique.overall_disposition == "REVISE"

    def test_score_clamped_to_unit_interval(self):
        raw = json.dumps({
            "overall_disposition": "REVISE",
            "archetype_fit_score": 1.5,
            "factuality_score": -0.3,
            "findings": [],
        })
        critique = parse_critic_response(
            raw_response=raw,
            critic_family=CriticFamily.ANTHROPIC_OPUS,
            argument_id="arg_test",
        )
        assert critique.archetype_fit_score == 1.0
        assert critique.factuality_score == 0.0

    def test_raw_response_truncated_to_500_chars(self):
        raw = "x" * 1000
        critique = parse_critic_response(
            raw_response=raw,
            critic_family=CriticFamily.ANTHROPIC_OPUS,
            argument_id="arg_test",
        )
        assert len(critique.raw_response_truncated) == 500


# -----------------------------------------------------------------------------
# A14 flag emission
# -----------------------------------------------------------------------------


class TestRecordCritiqueRun:

    def test_same_family_emits_a14_flag(self):
        cfg = CrossFamilyCriticConfig(
            generator=CriticFamily.ANTHROPIC_SONNET,
            critic=CriticFamily.SAME_AS_GENERATOR,
        )
        flags = record_critique_run(cfg, atom_id="test_atom")
        assert M6_CROSS_FAMILY_CRITIC_PENDING_FLAG in flags

    def test_intra_anthropic_cross_family_no_flag(self):
        cfg = CrossFamilyCriticConfig(
            generator=CriticFamily.ANTHROPIC_SONNET,
            critic=CriticFamily.ANTHROPIC_OPUS,
        )
        flags = record_critique_run(cfg, atom_id="test_atom")
        assert M6_CROSS_FAMILY_CRITIC_PENDING_FLAG not in flags

    def test_cross_vendor_no_flag(self):
        cfg = CrossFamilyCriticConfig(
            generator=CriticFamily.ANTHROPIC_SONNET,
            critic=CriticFamily.OPENAI_GPT4,
        )
        flags = record_critique_run(cfg, atom_id="test_atom")
        assert M6_CROSS_FAMILY_CRITIC_PENDING_FLAG not in flags


# -----------------------------------------------------------------------------
# A14 flag identifier + retirement trigger documented
# -----------------------------------------------------------------------------


class TestA14Flag:

    def test_flag_name_stable(self):
        assert M6_CROSS_FAMILY_CRITIC_PENDING_FLAG == "M6_CROSS_FAMILY_CRITIC_PENDING"

    def test_retirement_trigger_documented(self):
        # Three concrete pinned conditions surface in the trigger text.
        assert "≥30 critique runs" in M6_CROSS_FAMILY_RETIREMENT_TRIGGER
        assert "≥7 days" in M6_CROSS_FAMILY_RETIREMENT_TRIGGER
        assert "cross-vendor" in M6_CROSS_FAMILY_RETIREMENT_TRIGGER


# -----------------------------------------------------------------------------
# run_llm_critique with mocked engine
# -----------------------------------------------------------------------------


class _MockCriticEngine:
    """Mock engine that returns a fixed critic response for tests.

    Duck-types the .complete(prompt, max_tokens, temperature) -> {"text": ...}
    interface that the Anthropic engine adapter exposes.
    """

    def __init__(self, response_text: str):
        self.response_text = response_text
        self.calls: list = []

    async def complete(self, prompt: str, max_tokens: int, temperature: float):
        self.calls.append({
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
        })
        return {"text": self.response_text}


class _FailingCriticEngine:
    async def complete(self, prompt: str, max_tokens: int, temperature: float):
        raise RuntimeError("simulated network failure")


class TestRunLLMCritique:

    @pytest.mark.asyncio
    async def test_critique_with_mock_engine_returns_structured_output(self):
        mock = _MockCriticEngine(
            response_text=json.dumps({
                "overall_disposition": "REVISE",
                "archetype_fit_score": 0.65,
                "factuality_score": 0.93,
                "findings": [
                    {
                        "rule_id": "TONE_MISMATCH",
                        "severity": "minor",
                        "quoted_span": "stand out from competitors",
                        "explanation": "Stand-out language is forbidden by blend principle.",
                        "suggested_revision": "Use mechanism-faithful framing.",
                    },
                ],
            }),
        )
        cfg = CrossFamilyCriticConfig(
            generator=CriticFamily.ANTHROPIC_SONNET,
            critic=CriticFamily.ANTHROPIC_OPUS,
        )
        critique = await run_llm_critique(
            argument_text="Stand out from competitors with our luxury car.",
            constitution_summary="Forbid stand-out language.",
            archetype="careful_truster",
            mechanism="authority",
            config=cfg,
            critic_engine=mock,
            argument_id="arg_xyz",
            iteration=2,
        )
        assert critique.overall_disposition == "REVISE"
        assert critique.archetype_fit_score == 0.65
        assert critique.iteration == 2
        assert critique.critic_family == CriticFamily.ANTHROPIC_OPUS
        assert len(critique.findings) == 1
        # The mock was actually called.
        assert len(mock.calls) == 1
        # Critic temperature defaults to 0 (audit discipline).
        assert mock.calls[0]["temperature"] == 0.0

    @pytest.mark.asyncio
    async def test_engine_failure_returns_reject_critique(self):
        cfg = CrossFamilyCriticConfig(
            generator=CriticFamily.ANTHROPIC_SONNET,
            critic=CriticFamily.ANTHROPIC_OPUS,
        )
        critique = await run_llm_critique(
            argument_text="Argument under review.",
            constitution_summary="Constitution.",
            archetype="careful_truster",
            mechanism="authority",
            config=cfg,
            critic_engine=_FailingCriticEngine(),
            argument_id="arg_fail",
        )
        assert critique.overall_disposition == "REJECT"
        assert any(
            f.rule_id == "CRITIC_ENGINE_ERROR"
            for f in critique.findings
        )

    @pytest.mark.asyncio
    async def test_unparseable_engine_response_returns_reject(self):
        mock = _MockCriticEngine(
            response_text="The argument is great. No issues found.",
        )
        cfg = CrossFamilyCriticConfig(
            generator=CriticFamily.ANTHROPIC_SONNET,
            critic=CriticFamily.ANTHROPIC_OPUS,
        )
        critique = await run_llm_critique(
            argument_text="Argument.",
            constitution_summary="Constitution.",
            archetype="careful_truster",
            mechanism="authority",
            config=cfg,
            critic_engine=mock,
            argument_id="arg_bad",
        )
        assert critique.overall_disposition == "REJECT"
        assert any(
            f.rule_id == "CRITIC_OUTPUT_UNPARSEABLE"
            for f in critique.findings
        )


# -----------------------------------------------------------------------------
# build_critic_engine — soft-fail behavior
# -----------------------------------------------------------------------------


class TestBuildCriticEngineSoftFail:
    """When API keys aren't set, the builder MUST return None — silent
    soft-fail is the existing pattern (mirrors argument_ranking._try_build_engine).

    The discipline is: callers receive None and decide whether to fall
    through to single-family mode WITH the A14 flag, or block. The
    builder doesn't make that policy decision; it surfaces availability.
    """

    def test_anthropic_critic_without_key_returns_none(self):
        # In dev environments without ANTHROPIC_API_KEY this returns None.
        # We don't assert None unconditionally because dev environments
        # may have the key set; we just assert the builder doesn't raise.
        from adam.intelligence.cai_cross_family_critic import (
            build_critic_engine,
        )
        result = build_critic_engine(CriticFamily.ANTHROPIC_OPUS)
        # Either None (no key) or an engine object — both are valid.
        assert result is None or hasattr(result, "generate") or callable(result)

    def test_openai_critic_without_lib_returns_none(self):
        # openai is not in requirements.txt yet; builder returns None.
        from adam.intelligence.cai_cross_family_critic import (
            build_critic_engine,
        )
        result = build_critic_engine(CriticFamily.OPENAI_GPT4)
        assert result is None
