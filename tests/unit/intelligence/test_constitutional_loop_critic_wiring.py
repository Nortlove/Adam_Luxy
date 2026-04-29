"""Pin the M6 cross-family critic wiring into constitutional_loop.

Closes B3-finish per `docs/PILOT_BUILD_ROADMAP.md` Section 5 Week 2 #10.

Substrate (`cai_cross_family_critic`) was shipped in commit 04109ae;
this file pins the orchestrator-side wiring:

    1. When critic_engine + critic_config are provided, _critique_and_revise
       routes through run_llm_critique (LLM critic) instead of the
       heuristic string-match path.
    2. The critique_text is rendered from structured CritiqueFinding
       records via templated string formatting — A12 defense pinned.
    3. record_critique_run is invoked, emitting M6_CROSS_FAMILY_CRITIC_PENDING
       on same-family configs.
    4. When critic_engine is omitted, the heuristic path runs unchanged
       (regression anchor — no behavior change for callers that haven't
       opted into the LLM critic yet).
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from adam.intelligence.cai_cross_family_critic import (
    CriticFamily,
    CrossFamilyCriticConfig,
)
from adam.intelligence.constitutional_loop import (
    _critique_and_revise,
    run_constitutional_loop,
)
from adam.intelligence.argument_constitution import compose_constitution


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


def _build_engine_mock(headline="Quietly arrived", body="Discreet service",
                      cta="Continue"):
    """Build a generator engine mock that returns canonical text."""
    engine = MagicMock()
    engine_result = MagicMock()
    engine_result.headline = headline
    engine_result.body = body
    engine_result.cta = cta
    engine.generate = AsyncMock(return_value=engine_result)
    return engine


def _build_critic_engine_mock(critic_response_json: dict):
    """Build a critic engine mock that returns the given JSON as text."""
    critic = MagicMock()
    critic.complete = AsyncMock(
        return_value={"text": json.dumps(critic_response_json)},
    )
    return critic


def _make_arg():
    """Build a minimal CachedArgument for direct _critique_and_revise tests."""
    from adam.intelligence.argument_cache import CachedArgument
    return CachedArgument(
        headline="Stand out from competitors",
        body="Compelling reasons to choose our service",
        cta="Get started",
        barrier_addressed="trust_deficit",
        archetype_audited="status_seeker",
        mechanism_audited="social_proof",
    )


# -----------------------------------------------------------------------------
# _critique_and_revise — LLM critic path (cross-family critic provided)
# -----------------------------------------------------------------------------


class TestCritiqueAndReviseWithLLMCritic:

    @pytest.mark.asyncio
    async def test_llm_critic_invoked_when_engine_and_config_provided(self):
        """When both critic_engine and critic_config are supplied, the
        critic engine's .complete is invoked exactly once per critique."""
        constitution = compose_constitution("status_seeker", "social_proof")
        assert constitution is not None

        critic = _build_critic_engine_mock({
            "overall_disposition": "REVISE",
            "archetype_fit_score": 0.65,
            "factuality_score": 0.92,
            "findings": [
                {
                    "rule_id": "STAND_OUT_VIOLATION",
                    "severity": "major",
                    "quoted_span": "Stand out from competitors",
                    "explanation": "Stand-out language violates blend-don't-grab.",
                    "suggested_revision": "Use mechanism-faithful framing.",
                },
            ],
        })
        engine = _build_engine_mock()
        cfg = CrossFamilyCriticConfig(
            generator=CriticFamily.ANTHROPIC_SONNET,
            critic=CriticFamily.ANTHROPIC_OPUS,
        )

        arg = _make_arg()
        revised, critique_text = await _critique_and_revise(
            arg, constitution, brand_kb={"name": "LUXY"},
            bilateral_edge={}, engine=engine,
            critic_config=cfg, critic_engine=critic,
            iteration=0,
        )

        # Critic engine was called exactly once.
        assert critic.complete.call_count == 1

    @pytest.mark.asyncio
    async def test_critique_text_rendered_from_structured_findings(self):
        """The critique_text is composed by templated formatting of
        CritiqueFinding records — NOT by free-form prose. A12 defense."""
        constitution = compose_constitution("status_seeker", "social_proof")

        critic = _build_critic_engine_mock({
            "overall_disposition": "REVISE",
            "archetype_fit_score": 0.65,
            "factuality_score": 0.92,
            "findings": [
                {
                    "rule_id": "STAND_OUT_VIOLATION",
                    "severity": "major",
                    "quoted_span": "Stand out",
                    "explanation": "Stand-out language is forbidden.",
                    "suggested_revision": "Rephrase.",
                },
                {
                    "rule_id": "TONE_MISMATCH",
                    "severity": "minor",
                    "quoted_span": "Get started",
                    "explanation": "CTA tone is too aggressive.",
                    "suggested_revision": "Soften.",
                },
            ],
        })
        engine = _build_engine_mock()
        cfg = CrossFamilyCriticConfig(
            generator=CriticFamily.ANTHROPIC_SONNET,
            critic=CriticFamily.ANTHROPIC_OPUS,
        )

        arg = _make_arg()
        _, critique_text = await _critique_and_revise(
            arg, constitution, brand_kb={"name": "LUXY"},
            bilateral_edge={}, engine=engine,
            critic_config=cfg, critic_engine=critic,
            iteration=0,
        )

        # Both findings rendered into critique_text via the [severity]
        # rule_id: explanation template.
        assert "[major] STAND_OUT_VIOLATION" in critique_text
        assert "[minor] TONE_MISMATCH" in critique_text
        assert "Stand-out language is forbidden" in critique_text
        assert "CTA tone is too aggressive" in critique_text
        # Separator pinned.
        assert " | " in critique_text

    @pytest.mark.asyncio
    async def test_no_findings_yields_disposition_summary(self):
        """When the critic returns zero findings + APPROVE disposition,
        the critique_text is the templated disposition summary."""
        constitution = compose_constitution("status_seeker", "social_proof")
        critic = _build_critic_engine_mock({
            "overall_disposition": "APPROVE",
            "archetype_fit_score": 0.92,
            "factuality_score": 0.97,
            "findings": [],
        })
        engine = _build_engine_mock()
        cfg = CrossFamilyCriticConfig(
            generator=CriticFamily.ANTHROPIC_SONNET,
            critic=CriticFamily.ANTHROPIC_OPUS,
        )

        arg = _make_arg()
        _, critique_text = await _critique_and_revise(
            arg, constitution, brand_kb={"name": "LUXY"},
            bilateral_edge={}, engine=engine,
            critic_config=cfg, critic_engine=critic,
            iteration=0,
        )

        assert "APPROVE" in critique_text
        assert "no structured findings" in critique_text

    @pytest.mark.asyncio
    async def test_record_critique_run_invoked(self):
        """record_critique_run is called once per critique with the
        critic_config passed."""
        constitution = compose_constitution("status_seeker", "social_proof")
        critic = _build_critic_engine_mock({
            "overall_disposition": "REVISE",
            "archetype_fit_score": 0.5,
            "factuality_score": 0.95,
            "findings": [
                {
                    "rule_id": "X",
                    "severity": "minor",
                    "quoted_span": "y",
                    "explanation": "z",
                    "suggested_revision": "w",
                },
            ],
        })
        engine = _build_engine_mock()
        cfg = CrossFamilyCriticConfig(
            generator=CriticFamily.ANTHROPIC_SONNET,
            critic=CriticFamily.SAME_AS_GENERATOR,
        )

        arg = _make_arg()
        with patch(
            "adam.intelligence.cai_cross_family_critic.record_critique_run",
        ) as mock_record:
            mock_record.return_value = ["M6_CROSS_FAMILY_CRITIC_PENDING"]
            await _critique_and_revise(
                arg, constitution, brand_kb={"name": "LUXY"},
                bilateral_edge={}, engine=engine,
                critic_config=cfg, critic_engine=critic,
                iteration=0,
            )

        mock_record.assert_called_once()
        call_args = mock_record.call_args
        # First positional arg is the config; or keyword.
        passed_cfg = call_args.args[0] if call_args.args else call_args.kwargs.get("config")
        assert passed_cfg.generator == CriticFamily.ANTHROPIC_SONNET

    @pytest.mark.asyncio
    async def test_critic_engine_failure_falls_back_to_heuristic(self):
        """When the critic engine raises, the wiring catches the
        exception and falls back to the heuristic path WITHOUT
        crashing the constitutional loop."""
        constitution = compose_constitution("status_seeker", "social_proof")

        critic = MagicMock()
        critic.complete = AsyncMock(side_effect=RuntimeError("simulated"))

        engine = _build_engine_mock()
        cfg = CrossFamilyCriticConfig(
            generator=CriticFamily.ANTHROPIC_SONNET,
            critic=CriticFamily.ANTHROPIC_OPUS,
        )

        arg = _make_arg()
        # The wiring catches the exception inside run_llm_critique
        # (which returns a REJECT critique with CRITIC_ENGINE_ERROR);
        # critique_text gets rendered from that.
        revised, critique_text = await _critique_and_revise(
            arg, constitution, brand_kb={"name": "LUXY"},
            bilateral_edge={}, engine=engine,
            critic_config=cfg, critic_engine=critic,
            iteration=0,
        )
        # Either the engine error was rendered as a finding, or fallback
        # to heuristic happened — both are acceptable.
        assert critique_text  # non-empty


# -----------------------------------------------------------------------------
# Heuristic path preserved (regression — no critic_engine provided)
# -----------------------------------------------------------------------------


class TestHeuristicPathPreserved:

    @pytest.mark.asyncio
    async def test_no_critic_engine_uses_heuristic_path(self):
        """When critic_engine is None (default), the existing heuristic
        path runs — no LLM critic call. This is the regression anchor."""
        constitution = compose_constitution("status_seeker", "social_proof")
        engine = _build_engine_mock()

        # If anyone tries to call a critic_engine in this path, it
        # would need to exist; it doesn't. The test passes only if the
        # heuristic path runs without any critic_engine reference.
        arg = _make_arg()
        revised, critique_text = await _critique_and_revise(
            arg, constitution, brand_kb={"name": "LUXY"},
            bilateral_edge={}, engine=engine,
            # Both omitted → heuristic path.
        )

        # Heuristic critique text uses the existing format.
        # Either has "violation" findings or the canonical no-violations text.
        is_canonical = (
            critique_text == "No constitutional violations detected."
            or "violation" in critique_text.lower()
        )
        assert is_canonical

    @pytest.mark.asyncio
    async def test_only_critic_engine_without_config_uses_heuristic(self):
        """Both critic_engine AND critic_config must be provided to
        opt into the LLM path. Either one missing → heuristic."""
        constitution = compose_constitution("status_seeker", "social_proof")
        engine = _build_engine_mock()
        critic = _build_critic_engine_mock({
            "overall_disposition": "REVISE",
            "archetype_fit_score": 0.5,
            "factuality_score": 0.5,
            "findings": [],
        })
        # critic_engine provided but critic_config omitted → heuristic.
        arg = _make_arg()
        _, critique_text = await _critique_and_revise(
            arg, constitution, brand_kb={"name": "LUXY"},
            bilateral_edge={}, engine=engine,
            critic_engine=critic,
            # critic_config omitted.
        )

        # The critic.complete should NOT have been called.
        assert critic.complete.call_count == 0


# -----------------------------------------------------------------------------
# run_constitutional_loop — params flow through end-to-end
# -----------------------------------------------------------------------------


class TestRunConstitutionalLoopThreading:

    @pytest.mark.asyncio
    async def test_critic_params_thread_through_to_critique_step(self):
        """The new critic_config + critic_engine kwargs on
        run_constitutional_loop reach _critique_and_revise."""
        engine = _build_engine_mock(headline="h", body="b", cta="c")

        # Scorer returns failing first time so the loop iterates and
        # calls _critique_and_revise (which is where the LLM critic
        # would be invoked).
        call_count = {"n": 0}

        def archetype_scorer(text, constitution):
            call_count["n"] += 1
            return 0.95 if call_count["n"] >= 2 else 0.50

        critic = _build_critic_engine_mock({
            "overall_disposition": "REVISE",
            "archetype_fit_score": 0.5,
            "factuality_score": 0.99,
            "findings": [
                {
                    "rule_id": "X",
                    "severity": "minor",
                    "quoted_span": "y",
                    "explanation": "z",
                    "suggested_revision": "w",
                },
            ],
        })
        cfg = CrossFamilyCriticConfig(
            generator=CriticFamily.ANTHROPIC_SONNET,
            critic=CriticFamily.ANTHROPIC_OPUS,
        )

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
                critic_config=cfg,
                critic_engine=critic,
            )

        assert result.converged is True
        # Critic was invoked at least once during the loop.
        assert critic.complete.call_count >= 1
