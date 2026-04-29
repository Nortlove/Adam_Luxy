# =============================================================================
# ADAM Elicitation v0.2 Full-Suite Tests — SPIES + FourPoint +
#    CounterExample + Scenario
# Location: tests/unit/test_elicitation_generators_v02_full.py
# =============================================================================

"""Tests for the 4 remaining v0.2 elicitation modes (closing the
6-mode set per directive Section 7.1).

kAFC + RankOrder shipped earlier in the session (commit 8e29ab4); this
file pins SPIES + FourPoint + CounterExample + Scenario.

Pins:
    1. SPIES: interval validation; lower ≤ upper; non-degenerate
       width; probability/rate clamped to [0, 1]; ratio unconstrained
    2. FourPoint: monotonic non-decreasing across p10/25/75/90;
       probability/rate range; median + IQR derived for the Claim
    3. CounterExample: target_cohort + target_mechanism + REQUIRED
       categorical breakdown_reason_tag (A12); annotation optional
    4. Scenario: scenario_kind_tag + expected_outcome_tag both
       REQUIRED categorical (A12); annotation optional
    5. all_v02_generators returns 6 modes (full set)
    6. Every Claim enters as HYPOTHESIS (HMT rule 12)
"""

from __future__ import annotations

import pytest

from adam.intelligence.dialogue_ledger import (
    ClaimStatus,
    DialogueLedgerService,
    ElicitationMode,
)
from adam.intelligence.dialogue_ledger.elicitation import (
    COUNTER_EXAMPLE_BREAKDOWN_TAGS,
    CounterExampleGenerator,
    CounterExampleQuestion,
    CounterExampleResponse,
    ElicitationContext,
    FourPointGenerator,
    FourPointQuestion,
    FourPointResponse,
    SCENARIO_KIND_TAGS,
    SCENARIO_OUTCOME_TAGS,
    SPIESGenerator,
    SPIESQuestion,
    SPIESResponse,
    ScenarioGenerator,
    ScenarioQuestion,
    ScenarioResponse,
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
# SPIES — Subjective Probability Interval Estimates
# ============================================================================


class TestSPIESRender:

    def test_render_default_unit_probability(self):
        gen = SPIESGenerator()
        q = gen.render(
            prompt="Estimate authority lift in status_seekers",
            dimension="authority_lift_status_seekers",
        )
        assert q.dimension == "authority_lift_status_seekers"
        assert q.response_unit == "probability"

    def test_render_with_custom_unit(self):
        gen = SPIESGenerator()
        q = gen.render(prompt="p", dimension="d", response_unit="rate")
        assert q.response_unit == "rate"

    def test_render_rejects_invalid_unit(self):
        gen = SPIESGenerator()
        with pytest.raises(ValueError, match="response_unit"):
            gen.render(prompt="p", dimension="d", response_unit="furlongs")

    def test_render_rejects_empty_prompt(self):
        gen = SPIESGenerator()
        with pytest.raises(ValueError, match="prompt"):
            gen.render(prompt="", dimension="d")

    def test_render_rejects_empty_dimension(self):
        gen = SPIESGenerator()
        with pytest.raises(ValueError, match="dimension"):
            gen.render(prompt="p", dimension="")


class TestSPIESCapture:

    @pytest.mark.asyncio
    async def test_capture_valid_interval(self, service, context):
        gen = SPIESGenerator()
        q = gen.render(prompt="p", dimension="d")
        r = SPIESResponse(
            question_id=q.question_id,
            lower_bound=0.05, upper_bound=0.15,
            latency_ms=2500,
        )
        claim = await gen.capture(context, q, r, service)
        assert claim.status == ClaimStatus.HYPOTHESIS
        assert claim.elicitation_mode == ElicitationMode.SPIES
        # Midpoint stamped as stated_confidence
        assert claim.stated_confidence == pytest.approx(0.10)
        # Width visible in claim text
        assert "width 0.100" in claim.text

    @pytest.mark.asyncio
    async def test_capture_rejects_zero_width(self, service, context):
        gen = SPIESGenerator()
        q = gen.render(prompt="p", dimension="d")
        r = SPIESResponse(
            question_id=q.question_id,
            lower_bound=0.5, upper_bound=0.5,  # zero width
            latency_ms=100,
        )
        with pytest.raises(ValueError, match="zero-width"):
            await gen.capture(context, q, r, service)

    @pytest.mark.asyncio
    async def test_capture_rejects_inverted_interval(self, service, context):
        gen = SPIESGenerator()
        q = gen.render(prompt="p", dimension="d")
        r = SPIESResponse(
            question_id=q.question_id,
            lower_bound=0.7, upper_bound=0.3,
            latency_ms=100,
        )
        with pytest.raises(ValueError, match="lower_bound"):
            await gen.capture(context, q, r, service)

    @pytest.mark.asyncio
    async def test_capture_probability_out_of_range(self, service, context):
        gen = SPIESGenerator()
        q = gen.render(prompt="p", dimension="d", response_unit="probability")
        r = SPIESResponse(
            question_id=q.question_id,
            lower_bound=-0.1, upper_bound=0.5,
            latency_ms=100,
        )
        with pytest.raises(ValueError, match="lower_bound"):
            await gen.capture(context, q, r, service)

    @pytest.mark.asyncio
    async def test_capture_ratio_unconstrained_above_one(self, service, context):
        """Ratio response_unit allows values above 1.0 (e.g., risk
        ratio of 1.5 = 50% increase)."""
        gen = SPIESGenerator()
        q = gen.render(prompt="p", dimension="d", response_unit="ratio")
        r = SPIESResponse(
            question_id=q.question_id,
            lower_bound=1.2, upper_bound=2.5,
            latency_ms=100,
        )
        claim = await gen.capture(context, q, r, service)
        assert claim is not None

    @pytest.mark.asyncio
    async def test_capture_rejects_question_id_mismatch(self, service, context):
        gen = SPIESGenerator()
        q = gen.render(prompt="p", dimension="d")
        r = SPIESResponse(
            question_id="wrong:id",
            lower_bound=0.1, upper_bound=0.2, latency_ms=100,
        )
        with pytest.raises(ValueError, match="question_id"):
            await gen.capture(context, q, r, service)


# ============================================================================
# FourPoint — 4-percentile distribution-shape elicitation
# ============================================================================


class TestFourPointRender:

    def test_render_default_probability(self):
        gen = FourPointGenerator()
        q = gen.render(prompt="p", dimension="d")
        assert q.response_unit == "probability"

    def test_render_rejects_empty_inputs(self):
        gen = FourPointGenerator()
        with pytest.raises(ValueError, match="prompt"):
            gen.render(prompt="", dimension="d")
        with pytest.raises(ValueError, match="dimension"):
            gen.render(prompt="p", dimension="")


class TestFourPointCapture:

    @pytest.mark.asyncio
    async def test_capture_valid_anchors(self, service, context):
        gen = FourPointGenerator()
        q = gen.render(prompt="p", dimension="d")
        r = FourPointResponse(
            question_id=q.question_id,
            p10=0.05, p25=0.10, p75=0.30, p90=0.50,
            latency_ms=4000,
        )
        claim = await gen.capture(context, q, r, service)
        assert claim.status == ClaimStatus.HYPOTHESIS
        assert claim.elicitation_mode == ElicitationMode.FOUR_POINT
        # Approx-median (p25 + p75)/2 = 0.20
        assert claim.stated_confidence == pytest.approx(0.20)
        # Claim text contains anchors
        assert "p10=0.050" in claim.text
        assert "p90=0.500" in claim.text
        assert "IQR 0.200" in claim.text

    @pytest.mark.asyncio
    async def test_capture_rejects_non_monotonic(self, service, context):
        gen = FourPointGenerator()
        q = gen.render(prompt="p", dimension="d")
        # p25 < p10 (inverted)
        r = FourPointResponse(
            question_id=q.question_id,
            p10=0.30, p25=0.10, p75=0.50, p90=0.70,
            latency_ms=100,
        )
        with pytest.raises(ValueError, match="monotonic"):
            await gen.capture(context, q, r, service)

    @pytest.mark.asyncio
    async def test_capture_rejects_p75_above_p90(self, service, context):
        gen = FourPointGenerator()
        q = gen.render(prompt="p", dimension="d")
        r = FourPointResponse(
            question_id=q.question_id,
            p10=0.05, p25=0.10, p75=0.80, p90=0.50,
            latency_ms=100,
        )
        with pytest.raises(ValueError, match="monotonic"):
            await gen.capture(context, q, r, service)

    @pytest.mark.asyncio
    async def test_capture_probability_out_of_range(self, service, context):
        gen = FourPointGenerator()
        q = gen.render(prompt="p", dimension="d", response_unit="probability")
        r = FourPointResponse(
            question_id=q.question_id,
            p10=0.05, p25=0.10, p75=0.30, p90=1.5,  # out of range
            latency_ms=100,
        )
        with pytest.raises(ValueError, match="p90"):
            await gen.capture(context, q, r, service)

    @pytest.mark.asyncio
    async def test_capture_negative_latency_rejected(self, service, context):
        gen = FourPointGenerator()
        q = gen.render(prompt="p", dimension="d")
        r = FourPointResponse(
            question_id=q.question_id,
            p10=0.1, p25=0.2, p75=0.3, p90=0.4,
            latency_ms=-1,
        )
        with pytest.raises(ValueError, match="latency_ms"):
            await gen.capture(context, q, r, service)


# ============================================================================
# CounterExample — heterogeneous-effect prior elicitation
# ============================================================================


class TestCounterExampleRender:

    def test_render_valid(self):
        gen = CounterExampleGenerator()
        q = gen.render(
            prompt="Identify a counter-example",
            target_belief="authority works for status_seekers",
        )
        assert q.target_belief == "authority works for status_seekers"

    def test_render_rejects_empty_prompt(self):
        gen = CounterExampleGenerator()
        with pytest.raises(ValueError, match="prompt"):
            gen.render(prompt="", target_belief="x")

    def test_render_rejects_empty_belief(self):
        gen = CounterExampleGenerator()
        with pytest.raises(ValueError, match="target_belief"):
            gen.render(prompt="p", target_belief="")


class TestCounterExampleCapture:

    @pytest.mark.asyncio
    async def test_capture_valid(self, service, context):
        gen = CounterExampleGenerator()
        q = gen.render(prompt="p", target_belief="authority works")
        r = CounterExampleResponse(
            question_id=q.question_id,
            target_cohort="status_seeker",
            target_mechanism="authority",
            breakdown_reason_tag="prior_observation_contradicts",
            annotation="Becca: saw it backfire on user X last quarter",
            latency_ms=3500,
        )
        claim = await gen.capture(context, q, r, service)
        assert claim.status == ClaimStatus.HYPOTHESIS
        assert claim.elicitation_mode == ElicitationMode.COUNTER_EXAMPLE
        # All structured slots in claim text
        assert "status_seeker" in claim.text
        assert "authority" in claim.text
        assert "prior_observation_contradicts" in claim.text
        # Annotation pass-through
        assert "Becca" in claim.text

    @pytest.mark.asyncio
    async def test_capture_without_annotation(self, service, context):
        gen = CounterExampleGenerator()
        q = gen.render(prompt="p", target_belief="b")
        r = CounterExampleResponse(
            question_id=q.question_id,
            target_cohort="status_seeker",
            target_mechanism="authority",
            breakdown_reason_tag="cohort_membership_uncertain",
            latency_ms=200,
        )
        claim = await gen.capture(context, q, r, service)
        # No annotation in claim text
        assert "annotation" not in claim.text

    @pytest.mark.asyncio
    async def test_capture_rejects_empty_breakdown_tag(self, service, context):
        gen = CounterExampleGenerator()
        q = gen.render(prompt="p", target_belief="b")
        r = CounterExampleResponse(
            question_id=q.question_id,
            target_cohort="x", target_mechanism="y",
            breakdown_reason_tag="",  # empty
            latency_ms=100,
        )
        with pytest.raises(ValueError, match="breakdown_reason_tag"):
            await gen.capture(context, q, r, service)

    @pytest.mark.asyncio
    async def test_capture_rejects_arbitrary_tag(self, service, context):
        gen = CounterExampleGenerator()
        q = gen.render(prompt="p", target_belief="b")
        r = CounterExampleResponse(
            question_id=q.question_id,
            target_cohort="x", target_mechanism="y",
            breakdown_reason_tag="arbitrary_invented_tag",
            latency_ms=100,
        )
        with pytest.raises(ValueError, match="not in COUNTER_EXAMPLE"):
            await gen.capture(context, q, r, service)

    @pytest.mark.asyncio
    async def test_capture_rejects_empty_cohort_or_mechanism(self, service, context):
        gen = CounterExampleGenerator()
        q = gen.render(prompt="p", target_belief="b")
        r1 = CounterExampleResponse(
            question_id=q.question_id,
            target_cohort="", target_mechanism="y",
            breakdown_reason_tag="cohort_membership_uncertain",
            latency_ms=100,
        )
        with pytest.raises(ValueError, match="target_cohort"):
            await gen.capture(context, q, r1, service)
        r2 = CounterExampleResponse(
            question_id=q.question_id,
            target_cohort="x", target_mechanism="",
            breakdown_reason_tag="cohort_membership_uncertain",
            latency_ms=100,
        )
        with pytest.raises(ValueError, match="target_mechanism"):
            await gen.capture(context, q, r2, service)

    def test_breakdown_tag_vocabulary(self):
        """Per directive A12 + Section 7.1: closed vocabulary for
        categorical reasons. The vocabulary covers the directive's
        named example ('here's a user who is in cohort X but...')."""
        for tag in (
            "cohort_membership_uncertain",
            "prior_observation_contradicts",
            "context_mismatch",
            "specific_user_history_argues_against",
        ):
            assert tag in COUNTER_EXAMPLE_BREAKDOWN_TAGS


# ============================================================================
# Scenario — conditional prior elicitation
# ============================================================================


class TestScenarioRender:

    def test_render_valid(self):
        gen = ScenarioGenerator()
        q = gen.render(
            prompt="Describe scenario",
            mechanism_under_consideration="authority",
        )
        assert q.mechanism_under_consideration == "authority"

    def test_render_rejects_empty(self):
        gen = ScenarioGenerator()
        with pytest.raises(ValueError, match="prompt"):
            gen.render(prompt="", mechanism_under_consideration="x")
        with pytest.raises(ValueError, match="mechanism_under_consideration"):
            gen.render(prompt="p", mechanism_under_consideration="")


class TestScenarioCapture:

    @pytest.mark.asyncio
    async def test_capture_valid(self, service, context):
        gen = ScenarioGenerator()
        q = gen.render(
            prompt="p", mechanism_under_consideration="authority",
        )
        r = ScenarioResponse(
            question_id=q.question_id,
            scenario_kind_tag="morning_commute_pressure",
            expected_outcome_tag="expected_higher_response",
            annotation="users in time-pressure are more receptive to authority",
            latency_ms=4000,
        )
        claim = await gen.capture(context, q, r, service)
        assert claim.status == ClaimStatus.HYPOTHESIS
        assert claim.elicitation_mode == ElicitationMode.SCENARIO
        assert "morning_commute_pressure" in claim.text
        assert "authority" in claim.text
        assert "expected_higher_response" in claim.text
        assert "users in time-pressure" in claim.text

    @pytest.mark.asyncio
    async def test_capture_rejects_invalid_scenario_kind(self, service, context):
        gen = ScenarioGenerator()
        q = gen.render(prompt="p", mechanism_under_consideration="x")
        r = ScenarioResponse(
            question_id=q.question_id,
            scenario_kind_tag="arbitrary_invented_scenario",
            expected_outcome_tag="expected_higher_response",
            latency_ms=100,
        )
        with pytest.raises(ValueError, match="not in SCENARIO_KIND_TAGS"):
            await gen.capture(context, q, r, service)

    @pytest.mark.asyncio
    async def test_capture_rejects_invalid_outcome_tag(self, service, context):
        gen = ScenarioGenerator()
        q = gen.render(prompt="p", mechanism_under_consideration="x")
        r = ScenarioResponse(
            question_id=q.question_id,
            scenario_kind_tag="morning_commute_pressure",
            expected_outcome_tag="arbitrary_outcome",
            latency_ms=100,
        )
        with pytest.raises(ValueError, match="not in SCENARIO_OUTCOME_TAGS"):
            await gen.capture(context, q, r, service)

    @pytest.mark.asyncio
    async def test_capture_rejects_empty_kind_tag(self, service, context):
        gen = ScenarioGenerator()
        q = gen.render(prompt="p", mechanism_under_consideration="x")
        r = ScenarioResponse(
            question_id=q.question_id,
            scenario_kind_tag="",
            expected_outcome_tag="expected_higher_response",
            latency_ms=100,
        )
        with pytest.raises(ValueError, match="scenario_kind_tag"):
            await gen.capture(context, q, r, service)

    @pytest.mark.asyncio
    async def test_capture_rejects_empty_outcome_tag(self, service, context):
        gen = ScenarioGenerator()
        q = gen.render(prompt="p", mechanism_under_consideration="x")
        r = ScenarioResponse(
            question_id=q.question_id,
            scenario_kind_tag="morning_commute_pressure",
            expected_outcome_tag="",
            latency_ms=100,
        )
        with pytest.raises(ValueError, match="expected_outcome_tag"):
            await gen.capture(context, q, r, service)

    def test_scenario_kind_vocabulary(self):
        """Closed vocabulary covers directive's example scenarios."""
        for tag in (
            "morning_commute_pressure",
            "leisure_evening_browse",
            "expense_quarter_close",
            "new_user_first_touch",
        ):
            assert tag in SCENARIO_KIND_TAGS

    def test_scenario_outcome_vocabulary(self):
        for tag in (
            "expected_higher_response",
            "expected_lower_response",
            "expected_indifferent",
            "expected_backfire_risk",
        ):
            assert tag in SCENARIO_OUTCOME_TAGS


# ============================================================================
# Registry — all 6 v0.2 modes
# ============================================================================


class TestAllV02GeneratorsFullSet:

    def test_returns_six_generators(self):
        gens = all_v02_generators()
        assert len(gens) == 6

    def test_includes_all_modes(self):
        gens = all_v02_generators()
        kinds = {type(g).__name__ for g in gens}
        assert kinds == {
            "KAFCGenerator", "RankOrderGenerator",
            "SPIESGenerator", "FourPointGenerator",
            "CounterExampleGenerator", "ScenarioGenerator",
        }

    def test_modes_match(self):
        gens = all_v02_generators()
        modes = {g.mode for g in gens}
        assert modes == {
            ElicitationMode.K_AFC,
            ElicitationMode.RANK_ORDER,
            ElicitationMode.SPIES,
            ElicitationMode.FOUR_POINT,
            ElicitationMode.COUNTER_EXAMPLE,
            ElicitationMode.SCENARIO,
        }
