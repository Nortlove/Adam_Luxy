# =============================================================================
# ADAM Dialogue Ledger — Elicitation Generators (Loop B v0.1)
# Location: adam/intelligence/dialogue_ledger/elicitation.py
# =============================================================================

"""
ELICITATION GENERATORS — v0.1 (4 of 10 HMT §8 modes)

Each generator produces a render-ready question payload + captures
the response into a Claim written through the DialogueLedgerService.

v0.1 ships these four because together they cover ~80% of the data we
need for the LUXY pilot's Loop B (HMT §12 v0.1 starting rig):

  - ForcedPair (forced-choice, leisurely) — Bradley-Terry preference
    elicitation with low contamination risk
  - TimedPair (forced-choice, speeded) — Type 1 elicitation with
    countdown for tacit knowledge
  - StoryPrompt (episodic recall) — high-bandwidth anchored to a
    specific instance, less vulnerable to confabulation
  - RecallabilityProbe (tacit-vs-guess discrimination) — follow-up
    to a confident assertion that distinguishes tacit knowledge
    (fluent specific recall) from confident guess (abstract restatement)

The remaining 6 modes (kAFC, RankOrder, CounterExample, Scenario, SPIES,
FourPoint) are valid `ElicitationMode` enum values but do not have
generators in v0.1 — added in subsequent commits as the pilot demands.

DESIGN

Each generator has two methods:
  - `render(...)` — produces a render-ready payload object that the
    UI displays. Pure function, no side effects.
  - `capture(...)` — takes the user's response, builds the Claim,
    writes through the ledger service, returns the persisted Claim.

This separation lets the UI render questions without touching the
ledger, and the ledger receives writes only when the user has actually
responded.

DISCIPLINE — every Claim built here enters with status=HYPOTHESIS
(enforced by the Claim model + service). The capture method returns
the Claim object so callers can chain a RecallabilityProbe to a
confident-claim id, or render a Why-Library defensive reasoning panel
on top.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
from uuid import uuid4

from adam.intelligence.dialogue_ledger.models import (
    Claim,
    ElicitationMode,
    FrameLabel,
    RecallabilityLabel,
    make_claim,
)
from adam.intelligence.dialogue_ledger.service import DialogueLedgerService


# =============================================================================
# Common types
# =============================================================================


@dataclass(frozen=True)
class ElicitationContext:
    """Context for an elicitation event.

    Carries session-level data (user, domain, mood) so generators don't
    need to take many positional arguments.
    """

    user_id: str
    domain: str
    session_id: Optional[str] = None
    mood_index: Optional[float] = None
    frame: FrameLabel = FrameLabel.NEUTRAL


def _new_question_id() -> str:
    return f"q:{uuid4().hex[:16]}"


# =============================================================================
# ForcedPair — binary forced-choice, leisurely
# =============================================================================


@dataclass(frozen=True)
class ForcedPairQuestion:
    """Render-ready binary forced-choice payload.

    Frontend displays `prompt`, `option_a`, `option_b`; user picks one.
    `question_id` correlates the response back to this rendering.
    """

    question_id: str
    prompt: str
    option_a: str
    option_b: str


@dataclass(frozen=True)
class ForcedPairResponse:
    """Captured user response to a ForcedPairQuestion.

    `chosen` is "a" or "b" (string, not boolean — keeps the UI
    serialization explicit). `latency_ms` is the response time;
    fast responses indicate Type 1 / tacit, slow indicate Type 2 /
    deliberate.
    """

    question_id: str
    chosen: str  # "a" or "b"
    latency_ms: int


class ForcedPairGenerator:
    """Bradley-Terry preference-elicitation generator with leisurely pace.

    Use when contamination risk is moderate — the user CAN deliberate;
    System 2 reflection is acceptable. For tacit-knowledge elicitation
    where deliberation invites confabulation, use TimedPairGenerator.
    """

    mode = ElicitationMode.FORCED_PAIR

    def render(
        self,
        prompt: str,
        option_a: str,
        option_b: str,
    ) -> ForcedPairQuestion:
        if not prompt.strip():
            raise ValueError("prompt must be non-empty")
        if not option_a.strip() or not option_b.strip():
            raise ValueError("both options must be non-empty")
        return ForcedPairQuestion(
            question_id=_new_question_id(),
            prompt=prompt,
            option_a=option_a,
            option_b=option_b,
        )

    async def capture(
        self,
        context: ElicitationContext,
        question: ForcedPairQuestion,
        response: ForcedPairResponse,
        ledger: DialogueLedgerService,
    ) -> Claim:
        if response.question_id != question.question_id:
            raise ValueError(
                f"response.question_id ({response.question_id}) does not "
                f"match question.question_id ({question.question_id})"
            )
        if response.chosen not in ("a", "b"):
            raise ValueError(
                f"chosen must be 'a' or 'b'; got {response.chosen!r}"
            )
        if response.latency_ms < 0:
            raise ValueError(
                f"latency_ms must be non-negative; got {response.latency_ms}"
            )

        chosen_text = (
            question.option_a if response.chosen == "a" else question.option_b
        )

        claim_text = f"prefers '{chosen_text}' over alternative for: {question.prompt}"

        claim = make_claim(
            user_id=context.user_id,
            text=claim_text,
            elicitation_mode=self.mode,
            domain=context.domain,
            latency_ms=response.latency_ms,
            frame=context.frame,
            session_id=context.session_id,
            mood_index=context.mood_index,
        )
        await ledger.record_claim(
            claim,
            capture_reason=f"forced_pair: {question.question_id}",
        )
        return claim


# =============================================================================
# TimedPair — binary forced-choice with countdown (Type 1 elicitation)
# =============================================================================


@dataclass(frozen=True)
class TimedPairQuestion:
    """Render-ready timed binary forced-choice payload.

    Same as ForcedPairQuestion but with a `countdown_seconds` field
    the UI uses to drive a visible countdown timer. Default 3 seconds
    per HMT §8.2 (forces Type 1 response).
    """

    question_id: str
    prompt: str
    option_a: str
    option_b: str
    countdown_seconds: float


@dataclass(frozen=True)
class TimedPairResponse:
    """Captured response to a TimedPairQuestion. `deadline_hit=True`
    when the user did NOT respond within the countdown."""

    question_id: str
    chosen: Optional[str]  # "a" or "b" — None when deadline_hit
    latency_ms: int
    deadline_hit: bool = False


class TimedPairGenerator:
    """Forced-choice generator with visible countdown forcing Type 1
    response.

    Use when System 2 deliberation would invite confabulation — tacit
    preferences, implicit attitudes, intuitive judgments. The countdown
    is part of the elicitation, not a UI nicety.
    """

    mode = ElicitationMode.TIMED_PAIR

    def render(
        self,
        prompt: str,
        option_a: str,
        option_b: str,
        countdown_seconds: float = 3.0,
    ) -> TimedPairQuestion:
        if not prompt.strip():
            raise ValueError("prompt must be non-empty")
        if not option_a.strip() or not option_b.strip():
            raise ValueError("both options must be non-empty")
        if countdown_seconds <= 0:
            raise ValueError(
                f"countdown_seconds must be positive; got {countdown_seconds}"
            )
        return TimedPairQuestion(
            question_id=_new_question_id(),
            prompt=prompt,
            option_a=option_a,
            option_b=option_b,
            countdown_seconds=countdown_seconds,
        )

    async def capture(
        self,
        context: ElicitationContext,
        question: TimedPairQuestion,
        response: TimedPairResponse,
        ledger: DialogueLedgerService,
    ) -> Claim:
        if response.question_id != question.question_id:
            raise ValueError(
                "response.question_id does not match question.question_id"
            )
        if response.deadline_hit:
            if response.chosen is not None:
                raise ValueError(
                    "response.chosen must be None when deadline_hit=True"
                )
            claim_text = (
                f"deadline-hit (no choice within "
                f"{question.countdown_seconds:.1f}s) for: {question.prompt}"
            )
        else:
            if response.chosen not in ("a", "b"):
                raise ValueError(
                    f"chosen must be 'a' or 'b' when deadline NOT hit; "
                    f"got {response.chosen!r}"
                )
            chosen_text = (
                question.option_a if response.chosen == "a"
                else question.option_b
            )
            claim_text = (
                f"timed-prefers '{chosen_text}' for: {question.prompt}"
            )

        if response.latency_ms < 0:
            raise ValueError(
                f"latency_ms must be non-negative; got {response.latency_ms}"
            )

        claim = make_claim(
            user_id=context.user_id,
            text=claim_text,
            elicitation_mode=self.mode,
            domain=context.domain,
            latency_ms=response.latency_ms,
            frame=context.frame,
            session_id=context.session_id,
            mood_index=context.mood_index,
        )
        await ledger.record_claim(
            claim,
            capture_reason=(
                f"timed_pair: {question.question_id} "
                f"(deadline_hit={response.deadline_hit})"
            ),
        )
        return claim


# =============================================================================
# StoryPrompt — episodic recall, free-text
# =============================================================================


@dataclass(frozen=True)
class StoryPromptQuestion:
    """Render-ready episodic-recall prompt.

    Frontend displays `prompt`; user types a free-text response. The
    prompt should ANCHOR on a specific instance (HMT §8.5) — e.g.
    "tell me about the best campaign you ever ran and exactly why it
    worked" — to surface episodic detail rather than abstract
    generalization.
    """

    question_id: str
    prompt: str


@dataclass(frozen=True)
class StoryPromptResponse:
    """Captured free-text response.

    `time_to_first_keystroke_ms` indicates retrieval speed (proxy for
    fluent recall vs hesitation). `total_time_ms` is the full session
    on this prompt. The text body is the structured assertion.
    """

    question_id: str
    response_text: str
    time_to_first_keystroke_ms: int
    total_time_ms: int


class StoryPromptGenerator:
    """Episodic-recall elicitation generator.

    HMT §8.5: episodic memory is richer and less vulnerable to post-hoc
    theorizing than semantic recall. Anchor prompts on specific
    instances. The free-text response is logged raw to the ledger;
    structural parsing (LLM-extracted constructs, emotional tone, etc.)
    is a downstream concern handled by analytics, not the ledger.
    """

    mode = ElicitationMode.STORY

    def render(self, prompt: str) -> StoryPromptQuestion:
        if not prompt.strip():
            raise ValueError("prompt must be non-empty")
        return StoryPromptQuestion(
            question_id=_new_question_id(),
            prompt=prompt,
        )

    async def capture(
        self,
        context: ElicitationContext,
        question: StoryPromptQuestion,
        response: StoryPromptResponse,
        ledger: DialogueLedgerService,
    ) -> Claim:
        if response.question_id != question.question_id:
            raise ValueError(
                "response.question_id does not match question.question_id"
            )
        if not response.response_text.strip():
            raise ValueError("response_text must be non-empty")
        if response.time_to_first_keystroke_ms < 0:
            raise ValueError("time_to_first_keystroke_ms must be non-negative")
        if response.total_time_ms < 0:
            raise ValueError("total_time_ms must be non-negative")

        # Latency for Claim is total time on this prompt — that's what
        # the analytics loop should weight.
        claim = make_claim(
            user_id=context.user_id,
            text=response.response_text,
            elicitation_mode=self.mode,
            domain=context.domain,
            latency_ms=response.total_time_ms,
            frame=context.frame,
            session_id=context.session_id,
            mood_index=context.mood_index,
        )
        await ledger.record_claim(
            claim,
            capture_reason=(
                f"story_prompt: {question.question_id} "
                f"(time_to_first_keystroke={response.time_to_first_keystroke_ms}ms)"
            ),
        )
        return claim


# =============================================================================
# RecallabilityProbe — tacit-vs-guess discrimination
# =============================================================================


@dataclass(frozen=True)
class RecallabilityProbeQuestion:
    """Render-ready follow-up to a confident assertion.

    Frontend displays the original confident claim's text + a follow-up:
    "Can you think of a specific instance where you saw this happen?"
    User responds with an instance description (or indicates absence).

    `parent_claim_id` correlates this probe to the confident claim it
    is testing. The probe's response updates the parent claim's
    `recallability` field via the service.
    """

    question_id: str
    parent_claim_id: str
    parent_claim_text: str
    follow_up_prompt: str = (
        "Can you think of a specific instance where this was true?"
    )


@dataclass(frozen=True)
class RecallabilityProbeResponse:
    """Captured recallability response.

    `instance_text` is the user's instance description (empty when
    absent=True). `time_to_first_keystroke_ms` is the retrieval-speed
    signal — fast → fluent, slow → hesitant. `absent=True` means the
    user explicitly indicated they cannot recall a specific instance.
    """

    question_id: str
    instance_text: str
    time_to_first_keystroke_ms: int
    absent: bool = False


class RecallabilityProbeGenerator:
    """Tacit-vs-confabulation discrimination probe.

    HMT §7.4 + §8.7: a confident assertion the user CAN recall a
    specific instance for is weighted as tacit knowledge; one they
    cannot is weighted as confident guess (logged but flagged).

    `time_to_first_keystroke_ms` thresholds:
      < 5000ms  → FLUENT
      >= 5000ms but instance_text non-empty → HESITANT
      absent=True → ABSENT
    """

    mode = ElicitationMode.RECALLABILITY

    # HMT §8.7 fluency threshold — tunable as we accumulate per-user data
    FLUENT_THRESHOLD_MS: int = 5000

    def render(
        self,
        parent_claim_id: str,
        parent_claim_text: str,
        follow_up_prompt: Optional[str] = None,
    ) -> RecallabilityProbeQuestion:
        if not parent_claim_id:
            raise ValueError("parent_claim_id must be non-empty")
        if not parent_claim_text.strip():
            raise ValueError("parent_claim_text must be non-empty")
        return RecallabilityProbeQuestion(
            question_id=_new_question_id(),
            parent_claim_id=parent_claim_id,
            parent_claim_text=parent_claim_text,
            follow_up_prompt=(
                follow_up_prompt
                or "Can you think of a specific instance where this was true?"
            ),
        )

    def classify(
        self, response: RecallabilityProbeResponse,
    ) -> RecallabilityLabel:
        """Classify the response into a RecallabilityLabel."""
        if response.absent:
            return RecallabilityLabel.ABSENT
        if not response.instance_text.strip():
            return RecallabilityLabel.ABSENT
        if response.time_to_first_keystroke_ms < self.FLUENT_THRESHOLD_MS:
            return RecallabilityLabel.FLUENT
        return RecallabilityLabel.HESITANT

    async def capture(
        self,
        context: ElicitationContext,
        question: RecallabilityProbeQuestion,
        response: RecallabilityProbeResponse,
        ledger: DialogueLedgerService,
    ) -> Claim:
        if response.question_id != question.question_id:
            raise ValueError(
                "response.question_id does not match question.question_id"
            )
        if response.time_to_first_keystroke_ms < 0:
            raise ValueError(
                "time_to_first_keystroke_ms must be non-negative"
            )

        label = self.classify(response)
        instance_text = (
            response.instance_text.strip()
            if not response.absent else ""
        )

        claim_text = (
            f"recallability={label.value} for parent claim "
            f"{question.parent_claim_id}: {instance_text}"
            if instance_text else
            f"recallability={label.value} for parent claim "
            f"{question.parent_claim_id}: <no instance recalled>"
        )

        # The probe's Claim records the recallability assessment.
        claim = make_claim(
            user_id=context.user_id,
            text=claim_text,
            elicitation_mode=self.mode,
            domain=context.domain,
            latency_ms=response.time_to_first_keystroke_ms,
            frame=context.frame,
            session_id=context.session_id,
            mood_index=context.mood_index,
        )
        # Override the recallability field on the new Claim — it's the
        # whole point of the probe.
        claim.recallability = label

        await ledger.record_claim(
            claim,
            capture_reason=(
                f"recallability_probe: {question.question_id} "
                f"(parent={question.parent_claim_id}, label={label.value})"
            ),
        )
        return claim


# =============================================================================
# Convenience: get all v0.1 generators
# =============================================================================


def all_v01_generators() -> List[object]:
    """Return one instance of each v0.1 generator. Useful for
    introspection (e.g., "what modes does v0.1 support?")."""
    return [
        ForcedPairGenerator(),
        TimedPairGenerator(),
        StoryPromptGenerator(),
        RecallabilityProbeGenerator(),
    ]


__all__ = [
    "ElicitationContext",
    "ForcedPairGenerator",
    "ForcedPairQuestion",
    "ForcedPairResponse",
    "RecallabilityProbeGenerator",
    "RecallabilityProbeQuestion",
    "RecallabilityProbeResponse",
    "StoryPromptGenerator",
    "StoryPromptQuestion",
    "StoryPromptResponse",
    "TimedPairGenerator",
    "TimedPairQuestion",
    "TimedPairResponse",
    "all_v01_generators",
]
