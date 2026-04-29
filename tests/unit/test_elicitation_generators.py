# =============================================================================
# ADAM Elicitation Generators Tests
# Location: tests/unit/test_elicitation_generators.py
# =============================================================================

"""Tests for the 4 v0.1 elicitation generators (Loop B v0.1 commit 2)."""

from __future__ import annotations

import pytest

from adam.intelligence.dialogue_ledger import (
    ClaimStatus,
    DialogueLedgerService,
    ElicitationMode,
)
from adam.intelligence.dialogue_ledger.elicitation import (
    ElicitationContext,
    ForcedPairGenerator,
    ForcedPairQuestion,
    ForcedPairResponse,
    RecallabilityProbeGenerator,
    RecallabilityProbeQuestion,
    RecallabilityProbeResponse,
    StoryPromptGenerator,
    StoryPromptQuestion,
    StoryPromptResponse,
    TimedPairGenerator,
    TimedPairQuestion,
    TimedPairResponse,
    all_v01_generators,
)
from adam.intelligence.dialogue_ledger.models import (
    FrameLabel,
    RecallabilityLabel,
)
from adam.intelligence.dialogue_ledger.service import (
    InMemoryDialogueLedgerBackend,
)


@pytest.fixture
def service() -> DialogueLedgerService:
    return DialogueLedgerService(InMemoryDialogueLedgerBackend())


@pytest.fixture
def context() -> ElicitationContext:
    return ElicitationContext(
        user_id="user:test",
        domain="mechanism_selection",
        session_id="session:abc",
        mood_index=0.5,
        frame=FrameLabel.NEUTRAL,
    )


# ============================================================================
# ForcedPair
# ============================================================================


class TestForcedPair:

    def test_render_produces_question_with_unique_id(self):
        gen = ForcedPairGenerator()
        q1 = gen.render("which mechanism?", "authority", "social_proof")
        q2 = gen.render("which mechanism?", "authority", "social_proof")
        assert q1.question_id != q2.question_id

    def test_render_rejects_empty_prompt(self):
        gen = ForcedPairGenerator()
        with pytest.raises(ValueError, match="prompt"):
            gen.render("", "a", "b")

    def test_render_rejects_empty_options(self):
        gen = ForcedPairGenerator()
        with pytest.raises(ValueError, match="options"):
            gen.render("p", "", "b")
        with pytest.raises(ValueError, match="options"):
            gen.render("p", "a", "")

    @pytest.mark.asyncio
    async def test_capture_writes_claim_with_chosen_text(self, service, context):
        gen = ForcedPairGenerator()
        q = gen.render(
            "which mechanism resonates more with careful_truster?",
            "authority",
            "social_proof",
        )
        r = ForcedPairResponse(question_id=q.question_id, chosen="a", latency_ms=2200)
        claim = await gen.capture(context, q, r, service)
        assert claim.elicitation_mode == ElicitationMode.FORCED_PAIR
        assert claim.status == ClaimStatus.HYPOTHESIS
        assert "authority" in claim.text  # chosen option
        assert claim.latency_ms == 2200

    @pytest.mark.asyncio
    async def test_capture_rejects_mismatched_question_id(self, service, context):
        gen = ForcedPairGenerator()
        q = gen.render("p", "a", "b")
        r = ForcedPairResponse(question_id="q:wrong", chosen="a", latency_ms=100)
        with pytest.raises(ValueError, match="question_id"):
            await gen.capture(context, q, r, service)

    @pytest.mark.asyncio
    async def test_capture_rejects_invalid_choice(self, service, context):
        gen = ForcedPairGenerator()
        q = gen.render("p", "a", "b")
        r = ForcedPairResponse(question_id=q.question_id, chosen="c", latency_ms=100)
        with pytest.raises(ValueError, match="'a' or 'b'"):
            await gen.capture(context, q, r, service)

    @pytest.mark.asyncio
    async def test_capture_rejects_negative_latency(self, service, context):
        gen = ForcedPairGenerator()
        q = gen.render("p", "a", "b")
        r = ForcedPairResponse(question_id=q.question_id, chosen="a", latency_ms=-1)
        with pytest.raises(ValueError, match="latency_ms"):
            await gen.capture(context, q, r, service)


# ============================================================================
# TimedPair
# ============================================================================


class TestTimedPair:

    def test_render_includes_countdown(self):
        gen = TimedPairGenerator()
        q = gen.render("p", "a", "b", countdown_seconds=2.5)
        assert q.countdown_seconds == 2.5

    def test_render_default_countdown(self):
        gen = TimedPairGenerator()
        q = gen.render("p", "a", "b")
        assert q.countdown_seconds == 3.0

    def test_render_rejects_non_positive_countdown(self):
        gen = TimedPairGenerator()
        with pytest.raises(ValueError, match="countdown_seconds"):
            gen.render("p", "a", "b", countdown_seconds=0)

    @pytest.mark.asyncio
    async def test_capture_normal_choice(self, service, context):
        gen = TimedPairGenerator()
        q = gen.render("which feels right?", "warm", "authoritative")
        r = TimedPairResponse(
            question_id=q.question_id, chosen="b", latency_ms=1900,
        )
        claim = await gen.capture(context, q, r, service)
        assert claim.elicitation_mode == ElicitationMode.TIMED_PAIR
        assert "authoritative" in claim.text  # chosen
        assert claim.latency_ms == 1900

    @pytest.mark.asyncio
    async def test_capture_deadline_hit(self, service, context):
        gen = TimedPairGenerator()
        q = gen.render("which feels right?", "warm", "authoritative")
        r = TimedPairResponse(
            question_id=q.question_id, chosen=None,
            latency_ms=3000, deadline_hit=True,
        )
        claim = await gen.capture(context, q, r, service)
        assert "deadline-hit" in claim.text
        assert claim.latency_ms == 3000

    @pytest.mark.asyncio
    async def test_capture_rejects_inconsistent_deadline_hit(
        self, service, context,
    ):
        """deadline_hit=True with a non-None chosen is malformed."""
        gen = TimedPairGenerator()
        q = gen.render("p", "a", "b")
        r = TimedPairResponse(
            question_id=q.question_id, chosen="a",
            latency_ms=3000, deadline_hit=True,
        )
        with pytest.raises(ValueError, match="None when deadline_hit"):
            await gen.capture(context, q, r, service)


# ============================================================================
# StoryPrompt
# ============================================================================


class TestStoryPrompt:

    def test_render_basic(self):
        gen = StoryPromptGenerator()
        q = gen.render(
            "tell me about the best campaign you ever ran and exactly why it worked"
        )
        assert q.prompt.startswith("tell me")

    def test_render_rejects_empty(self):
        gen = StoryPromptGenerator()
        with pytest.raises(ValueError, match="prompt"):
            gen.render("")

    @pytest.mark.asyncio
    async def test_capture_writes_full_text_as_claim(self, service, context):
        gen = StoryPromptGenerator()
        q = gen.render("tell me about a great campaign")
        long_response = (
            "We ran a campaign for an airline in 2023 where careful_truster "
            "responded to brand_trust_evidence on prevention-focused pages "
            "the way bilateral predicts."
        )
        r = StoryPromptResponse(
            question_id=q.question_id,
            response_text=long_response,
            time_to_first_keystroke_ms=4500,
            total_time_ms=78000,
        )
        claim = await gen.capture(context, q, r, service)
        assert claim.elicitation_mode == ElicitationMode.STORY
        assert claim.text == long_response  # full text preserved
        assert claim.latency_ms == 78000  # total time

    @pytest.mark.asyncio
    async def test_capture_rejects_empty_response(self, service, context):
        gen = StoryPromptGenerator()
        q = gen.render("tell me about a campaign")
        r = StoryPromptResponse(
            question_id=q.question_id,
            response_text="   ",  # whitespace
            time_to_first_keystroke_ms=1000,
            total_time_ms=2000,
        )
        with pytest.raises(ValueError, match="response_text"):
            await gen.capture(context, q, r, service)


# ============================================================================
# RecallabilityProbe
# ============================================================================


class TestRecallabilityProbe:

    def test_render_requires_parent_claim(self):
        gen = RecallabilityProbeGenerator()
        with pytest.raises(ValueError, match="parent_claim_id"):
            gen.render("", "parent text")
        with pytest.raises(ValueError, match="parent_claim_text"):
            gen.render("claim:abc", "")

    def test_render_uses_default_followup(self):
        gen = RecallabilityProbeGenerator()
        q = gen.render("claim:abc", "I think X works")
        assert "specific instance" in q.follow_up_prompt

    def test_classify_fluent(self):
        gen = RecallabilityProbeGenerator()
        r = RecallabilityProbeResponse(
            question_id="q:test",
            instance_text="In Q3 2023 LUXY ran X for careful_truster on...",
            time_to_first_keystroke_ms=2000,  # < 5000 threshold
        )
        assert gen.classify(r) == RecallabilityLabel.FLUENT

    def test_classify_hesitant(self):
        gen = RecallabilityProbeGenerator()
        r = RecallabilityProbeResponse(
            question_id="q:test",
            instance_text="something like that... maybe",
            time_to_first_keystroke_ms=12000,  # > 5000 threshold
        )
        assert gen.classify(r) == RecallabilityLabel.HESITANT

    def test_classify_absent_via_flag(self):
        gen = RecallabilityProbeGenerator()
        r = RecallabilityProbeResponse(
            question_id="q:test",
            instance_text="",
            time_to_first_keystroke_ms=1000,
            absent=True,
        )
        assert gen.classify(r) == RecallabilityLabel.ABSENT

    def test_classify_absent_via_empty_text(self):
        gen = RecallabilityProbeGenerator()
        r = RecallabilityProbeResponse(
            question_id="q:test",
            instance_text="   ",  # whitespace only
            time_to_first_keystroke_ms=1000,
            absent=False,
        )
        assert gen.classify(r) == RecallabilityLabel.ABSENT

    @pytest.mark.asyncio
    async def test_capture_fluent(self, service, context):
        gen = RecallabilityProbeGenerator()
        q = gen.render(
            "claim:parent_001",
            "Status Seekers respond best to aspirational_self",
        )
        r = RecallabilityProbeResponse(
            question_id=q.question_id,
            instance_text="In May 2023 LUXY ran ...",
            time_to_first_keystroke_ms=2000,
        )
        claim = await gen.capture(context, q, r, service)
        assert claim.elicitation_mode == ElicitationMode.RECALLABILITY
        assert claim.recallability == RecallabilityLabel.FLUENT
        assert "fluent" in claim.text

    @pytest.mark.asyncio
    async def test_capture_absent(self, service, context):
        gen = RecallabilityProbeGenerator()
        q = gen.render(
            "claim:parent_002",
            "Easy Decider always converts on social_proof",
        )
        r = RecallabilityProbeResponse(
            question_id=q.question_id,
            instance_text="",
            time_to_first_keystroke_ms=1000,
            absent=True,
        )
        claim = await gen.capture(context, q, r, service)
        assert claim.recallability == RecallabilityLabel.ABSENT
        assert "<no instance recalled>" in claim.text


# ============================================================================
# all_v01_generators introspection
# ============================================================================


class TestAllV01Generators:

    def test_returns_four_distinct_modes(self):
        gens = all_v01_generators()
        assert len(gens) == 4
        modes = {g.mode for g in gens}
        assert modes == {
            ElicitationMode.FORCED_PAIR,
            ElicitationMode.TIMED_PAIR,
            ElicitationMode.STORY,
            ElicitationMode.RECALLABILITY,
        }


# ============================================================================
# Discipline anchor — every generator writes Claims as HYPOTHESIS
# ============================================================================


class TestEveryGeneratorRespectsHypothesisRule:
    """HMT discipline rule 12: every Claim a generator writes must be
    HYPOTHESIS at write time. Re-tested per generator to catch any
    accidental status mutation in capture()."""

    @pytest.mark.asyncio
    async def test_forced_pair_writes_hypothesis(self, service, context):
        gen = ForcedPairGenerator()
        q = gen.render("p", "a", "b")
        r = ForcedPairResponse(question_id=q.question_id, chosen="a", latency_ms=100)
        claim = await gen.capture(context, q, r, service)
        assert claim.status == ClaimStatus.HYPOTHESIS

    @pytest.mark.asyncio
    async def test_timed_pair_writes_hypothesis(self, service, context):
        gen = TimedPairGenerator()
        q = gen.render("p", "a", "b")
        r = TimedPairResponse(question_id=q.question_id, chosen="a", latency_ms=100)
        claim = await gen.capture(context, q, r, service)
        assert claim.status == ClaimStatus.HYPOTHESIS

    @pytest.mark.asyncio
    async def test_story_prompt_writes_hypothesis(self, service, context):
        gen = StoryPromptGenerator()
        q = gen.render("tell me about a campaign")
        r = StoryPromptResponse(
            question_id=q.question_id,
            response_text="some text",
            time_to_first_keystroke_ms=1000,
            total_time_ms=10000,
        )
        claim = await gen.capture(context, q, r, service)
        assert claim.status == ClaimStatus.HYPOTHESIS

    @pytest.mark.asyncio
    async def test_recallability_writes_hypothesis(self, service, context):
        gen = RecallabilityProbeGenerator()
        q = gen.render("claim:p", "parent text")
        r = RecallabilityProbeResponse(
            question_id=q.question_id,
            instance_text="example",
            time_to_first_keystroke_ms=1000,
        )
        claim = await gen.capture(context, q, r, service)
        assert claim.status == ClaimStatus.HYPOTHESIS
