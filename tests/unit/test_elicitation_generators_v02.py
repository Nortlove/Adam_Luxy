# =============================================================================
# ADAM Elicitation Generators v0.2 Tests — kAFC + RankOrder
# Location: tests/unit/test_elicitation_generators_v02.py
# =============================================================================

"""Tests for the v0.2 elicitation generators added on top of the
v0.1 four (Loop B v0.2 expansion).

Pins:
    1. kAFC: k in [3, 5] enforced; distinct non-empty options;
       chosen_label routed correctly; claim text includes count
    2. RankOrder: n in [3, 5] enforced; distinct items; ranking must
       be a valid permutation; claim text shows ordered chain
    3. Both generators thread through the DialogueLedgerService and
       the resulting Claims enter as HYPOTHESIS (HMT rule 12)
    4. all_v02_generators() returns both new generators
"""

from __future__ import annotations

import pytest

from adam.intelligence.dialogue_ledger import (
    ClaimStatus,
    DialogueLedgerService,
    ElicitationMode,
)
from adam.intelligence.dialogue_ledger.elicitation import (
    ElicitationContext,
    KAFCGenerator,
    KAFCQuestion,
    KAFCResponse,
    RankOrderGenerator,
    RankOrderQuestion,
    RankOrderResponse,
    all_v02_generators,
)
from adam.intelligence.dialogue_ledger.models import FrameLabel
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
# kAFC — k-alternative forced-choice
# ============================================================================


class TestKAFCRender:

    def test_render_with_three_options(self):
        gen = KAFCGenerator()
        q = gen.render(
            prompt="Which feels most aligned for this audience?",
            options=["authority", "social_proof", "scarcity"],
        )
        assert q.k() == 3
        assert q.option_labels == ["a", "b", "c"]
        assert q.options == ["authority", "social_proof", "scarcity"]

    def test_render_with_five_options(self):
        gen = KAFCGenerator()
        q = gen.render(
            prompt="p",
            options=["a1", "a2", "a3", "a4", "a5"],
        )
        assert q.k() == 5
        assert q.option_labels == ["a", "b", "c", "d", "e"]

    def test_render_rejects_k_below_three(self):
        gen = KAFCGenerator()
        with pytest.raises(ValueError, match="k in"):
            gen.render(prompt="p", options=["a", "b"])

    def test_render_rejects_k_above_five(self):
        gen = KAFCGenerator()
        with pytest.raises(ValueError, match="k in"):
            gen.render(prompt="p", options=["a", "b", "c", "d", "e", "f"])

    def test_render_rejects_empty_prompt(self):
        gen = KAFCGenerator()
        with pytest.raises(ValueError, match="prompt"):
            gen.render(prompt="", options=["a", "b", "c"])

    def test_render_rejects_empty_option(self):
        gen = KAFCGenerator()
        with pytest.raises(ValueError, match="non-empty"):
            gen.render(prompt="p", options=["a", "", "c"])

    def test_render_rejects_duplicate_options(self):
        gen = KAFCGenerator()
        with pytest.raises(ValueError, match="distinct"):
            gen.render(prompt="p", options=["a", "b", "a"])

    def test_render_strips_whitespace(self):
        gen = KAFCGenerator()
        q = gen.render(prompt="p", options=["  a  ", "b", "c"])
        assert q.options[0] == "a"


class TestKAFCCapture:

    @pytest.mark.asyncio
    async def test_capture_with_valid_response(self, service, context):
        gen = KAFCGenerator()
        q = gen.render(
            prompt="Which?",
            options=["authority", "social_proof", "scarcity"],
        )
        response = KAFCResponse(
            question_id=q.question_id,
            chosen_label="b",
            latency_ms=1500,
        )
        claim = await gen.capture(context, q, response, service)
        # Claim is HYPOTHESIS at construction (HMT rule 12).
        assert claim.status == ClaimStatus.HYPOTHESIS
        assert claim.elicitation_mode == ElicitationMode.K_AFC
        assert "social_proof" in claim.text
        assert "3 alternatives" in claim.text
        assert claim.latency_ms == 1500

    @pytest.mark.asyncio
    async def test_capture_rejects_mismatched_question_id(self, service, context):
        gen = KAFCGenerator()
        q = gen.render(prompt="p", options=["a", "b", "c"])
        with pytest.raises(ValueError, match="question_id"):
            await gen.capture(
                context, q,
                KAFCResponse(
                    question_id="wrong:id",
                    chosen_label="a",
                    latency_ms=100,
                ),
                service,
            )

    @pytest.mark.asyncio
    async def test_capture_rejects_invalid_label(self, service, context):
        gen = KAFCGenerator()
        q = gen.render(prompt="p", options=["a", "b", "c"])
        with pytest.raises(ValueError, match="chosen_label"):
            await gen.capture(
                context, q,
                KAFCResponse(
                    question_id=q.question_id,
                    chosen_label="x",  # not in [a, b, c]
                    latency_ms=100,
                ),
                service,
            )

    @pytest.mark.asyncio
    async def test_capture_rejects_negative_latency(self, service, context):
        gen = KAFCGenerator()
        q = gen.render(prompt="p", options=["a", "b", "c"])
        with pytest.raises(ValueError, match="latency_ms"):
            await gen.capture(
                context, q,
                KAFCResponse(
                    question_id=q.question_id,
                    chosen_label="a",
                    latency_ms=-1,
                ),
                service,
            )


# ============================================================================
# RankOrder — full ordering
# ============================================================================


class TestRankOrderRender:

    def test_render_with_three_items(self):
        gen = RankOrderGenerator()
        q = gen.render(
            prompt="Order these by trustworthiness",
            dimension="trustworthiness",
            items=["authority", "social_proof", "scarcity"],
        )
        assert q.n() == 3
        assert q.dimension == "trustworthiness"
        assert q.items == ["authority", "social_proof", "scarcity"]

    def test_render_with_five_items(self):
        gen = RankOrderGenerator()
        q = gen.render(
            prompt="p",
            dimension="d",
            items=["a", "b", "c", "d", "e"],
        )
        assert q.n() == 5

    def test_render_rejects_n_below_three(self):
        gen = RankOrderGenerator()
        with pytest.raises(ValueError, match="n in"):
            gen.render(prompt="p", dimension="d", items=["a", "b"])

    def test_render_rejects_n_above_five(self):
        gen = RankOrderGenerator()
        with pytest.raises(ValueError, match="n in"):
            gen.render(
                prompt="p", dimension="d",
                items=["a", "b", "c", "d", "e", "f"],
            )

    def test_render_rejects_empty_prompt(self):
        gen = RankOrderGenerator()
        with pytest.raises(ValueError, match="prompt"):
            gen.render(prompt="", dimension="d", items=["a", "b", "c"])

    def test_render_rejects_empty_dimension(self):
        gen = RankOrderGenerator()
        with pytest.raises(ValueError, match="dimension"):
            gen.render(prompt="p", dimension="", items=["a", "b", "c"])

    def test_render_rejects_duplicate_items(self):
        gen = RankOrderGenerator()
        with pytest.raises(ValueError, match="distinct"):
            gen.render(prompt="p", dimension="d", items=["a", "b", "a"])


class TestRankOrderCapture:

    @pytest.mark.asyncio
    async def test_capture_with_valid_permutation(self, service, context):
        gen = RankOrderGenerator()
        q = gen.render(
            prompt="Order by trustworthiness",
            dimension="trustworthiness",
            items=["authority", "social_proof", "scarcity"],
        )
        # User picks: authority > scarcity > social_proof
        response = RankOrderResponse(
            question_id=q.question_id,
            ranking=[0, 2, 1],
            latency_ms=4000,
        )
        claim = await gen.capture(context, q, response, service)
        assert claim.status == ClaimStatus.HYPOTHESIS
        assert claim.elicitation_mode == ElicitationMode.RANK_ORDER
        # Claim text shows the ordered chain.
        assert "authority > scarcity > social_proof" in claim.text
        assert "trustworthiness" in claim.text

    @pytest.mark.asyncio
    async def test_capture_rejects_wrong_length(self, service, context):
        gen = RankOrderGenerator()
        q = gen.render(prompt="p", dimension="d", items=["a", "b", "c"])
        with pytest.raises(ValueError, match="length"):
            await gen.capture(
                context, q,
                RankOrderResponse(
                    question_id=q.question_id,
                    ranking=[0, 1],  # only 2 elements
                    latency_ms=100,
                ),
                service,
            )

    @pytest.mark.asyncio
    async def test_capture_rejects_invalid_permutation(self, service, context):
        gen = RankOrderGenerator()
        q = gen.render(prompt="p", dimension="d", items=["a", "b", "c"])
        with pytest.raises(ValueError, match="permutation"):
            await gen.capture(
                context, q,
                RankOrderResponse(
                    question_id=q.question_id,
                    ranking=[0, 0, 1],  # not a permutation (duplicate 0)
                    latency_ms=100,
                ),
                service,
            )

    @pytest.mark.asyncio
    async def test_capture_rejects_out_of_range_index(self, service, context):
        gen = RankOrderGenerator()
        q = gen.render(prompt="p", dimension="d", items=["a", "b", "c"])
        with pytest.raises(ValueError, match="permutation"):
            await gen.capture(
                context, q,
                RankOrderResponse(
                    question_id=q.question_id,
                    ranking=[0, 1, 5],  # 5 out of range
                    latency_ms=100,
                ),
                service,
            )

    @pytest.mark.asyncio
    async def test_capture_rejects_mismatched_question_id(self, service, context):
        gen = RankOrderGenerator()
        q = gen.render(prompt="p", dimension="d", items=["a", "b", "c"])
        with pytest.raises(ValueError, match="question_id"):
            await gen.capture(
                context, q,
                RankOrderResponse(
                    question_id="wrong:id",
                    ranking=[0, 1, 2],
                    latency_ms=100,
                ),
                service,
            )


# ============================================================================
# all_v02_generators — registry
# ============================================================================


class TestAllV02Generators:

    def test_returns_both_new_generators(self):
        gens = all_v02_generators()
        kinds = {type(g).__name__ for g in gens}
        assert "KAFCGenerator" in kinds
        assert "RankOrderGenerator" in kinds

    def test_modes_match(self):
        gens = all_v02_generators()
        modes = {g.mode for g in gens}
        assert ElicitationMode.K_AFC in modes
        assert ElicitationMode.RANK_ORDER in modes
