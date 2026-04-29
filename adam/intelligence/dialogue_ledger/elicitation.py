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
# kAFC — k-alternative forced-choice (v0.2)
# =============================================================================


@dataclass(frozen=True)
class KAFCQuestion:
    """Render-ready k-alternative forced-choice payload.

    Generalization of ForcedPair to k options (typically k=3..5). Used
    for psychophysical-style discrimination where binary choice is too
    coarse — e.g., "which of these four creative variants feels most
    aligned with your audience?"

    `options` is the ordered list of k options. `option_labels` is the
    parallel list of single-character labels ("a", "b", "c", ...) for
    response routing.
    """

    question_id: str
    prompt: str
    options: List[str]
    option_labels: List[str]

    def k(self) -> int:
        return len(self.options)


@dataclass(frozen=True)
class KAFCResponse:
    """Captured response to a KAFCQuestion."""

    question_id: str
    chosen_label: str  # one of question.option_labels
    latency_ms: int


class KAFCGenerator:
    """k-alternative forced-choice generator (HMT §8 v0.2 mode).

    Choose k=3 when binary is too coarse but the user is still expected
    to converge fast. k=5 introduces material processing-depth cost and
    is appropriate when System 2 deliberation is desired (per HMT
    §8.4: kAFC's coarse-vs-fine tradeoff).

    Validation:
        - k MUST be in [3, 5] (HMT §8.4 boundary)
        - All option strings non-empty + distinct
        - chosen_label MUST be one of the option_labels
    """

    mode = ElicitationMode.K_AFC

    _MIN_K = 3
    _MAX_K = 5

    def render(
        self,
        prompt: str,
        options: List[str],
    ) -> KAFCQuestion:
        if not prompt.strip():
            raise ValueError("prompt must be non-empty")
        if not (self._MIN_K <= len(options) <= self._MAX_K):
            raise ValueError(
                f"kAFC requires k in [{self._MIN_K}, {self._MAX_K}]; "
                f"got k={len(options)}"
            )
        cleaned = [o.strip() for o in options]
        if any(not o for o in cleaned):
            raise ValueError("every option must be non-empty")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("options must be distinct")
        labels = [chr(ord("a") + i) for i in range(len(cleaned))]
        return KAFCQuestion(
            question_id=_new_question_id(),
            prompt=prompt,
            options=cleaned,
            option_labels=labels,
        )

    async def capture(
        self,
        context: ElicitationContext,
        question: KAFCQuestion,
        response: KAFCResponse,
        ledger: DialogueLedgerService,
    ) -> Claim:
        if response.question_id != question.question_id:
            raise ValueError(
                f"response.question_id ({response.question_id}) does not "
                f"match question.question_id ({question.question_id})"
            )
        if response.chosen_label not in question.option_labels:
            raise ValueError(
                f"chosen_label must be one of {question.option_labels}; "
                f"got {response.chosen_label!r}"
            )
        if response.latency_ms < 0:
            raise ValueError(
                f"latency_ms must be non-negative; got {response.latency_ms}"
            )

        idx = question.option_labels.index(response.chosen_label)
        chosen_text = question.options[idx]
        claim_text = (
            f"selected '{chosen_text}' from {question.k()} alternatives "
            f"for: {question.prompt}"
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
            capture_reason=f"k_afc: {question.question_id}",
        )
        return claim


# =============================================================================
# RankOrder — full ordering of n items (v0.2)
# =============================================================================


@dataclass(frozen=True)
class RankOrderQuestion:
    """Render-ready rank-order question payload.

    User orders n items from most-preferred (rank 1) to least-preferred
    (rank n) along a stated psychological dimension.

    `dimension` is the named psychological dimension being ranked
    (e.g., "trustworthiness", "attention-grabbing-ness"). `items` is
    the ordered list to be reordered.
    """

    question_id: str
    prompt: str
    dimension: str
    items: List[str]

    def n(self) -> int:
        return len(self.items)


@dataclass(frozen=True)
class RankOrderResponse:
    """Captured response to a RankOrderQuestion.

    `ranking` is a list of indices into question.items, in the user's
    order from most → least. Length must equal question.n().
    """

    question_id: str
    ranking: List[int]
    latency_ms: int


class RankOrderGenerator:
    """Full-ordering generator (HMT §8 v0.2 mode).

    Captures more information per response than ForcedPair (n choose 2
    pairwise inferences from one ranking) at the cost of higher
    cognitive load for the user. HMT §8.5: use for n ≤ 5; beyond that
    the response time and confabulation risk both spike.

    Validation:
        - n MUST be in [3, 5]
        - All items distinct
        - ranking MUST be a valid permutation of [0..n-1]
    """

    mode = ElicitationMode.RANK_ORDER

    _MIN_N = 3
    _MAX_N = 5

    def render(
        self,
        prompt: str,
        dimension: str,
        items: List[str],
    ) -> RankOrderQuestion:
        if not prompt.strip():
            raise ValueError("prompt must be non-empty")
        if not dimension.strip():
            raise ValueError("dimension must be non-empty")
        if not (self._MIN_N <= len(items) <= self._MAX_N):
            raise ValueError(
                f"RankOrder requires n in [{self._MIN_N}, {self._MAX_N}]; "
                f"got n={len(items)}"
            )
        cleaned = [i.strip() for i in items]
        if any(not i for i in cleaned):
            raise ValueError("every item must be non-empty")
        if len(set(cleaned)) != len(cleaned):
            raise ValueError("items must be distinct")
        return RankOrderQuestion(
            question_id=_new_question_id(),
            prompt=prompt,
            dimension=dimension,
            items=cleaned,
        )

    async def capture(
        self,
        context: ElicitationContext,
        question: RankOrderQuestion,
        response: RankOrderResponse,
        ledger: DialogueLedgerService,
    ) -> Claim:
        if response.question_id != question.question_id:
            raise ValueError(
                f"response.question_id ({response.question_id}) does not "
                f"match question.question_id ({question.question_id})"
            )
        n = question.n()
        if len(response.ranking) != n:
            raise ValueError(
                f"ranking length must equal n={n}; got {len(response.ranking)}"
            )
        if sorted(response.ranking) != list(range(n)):
            raise ValueError(
                f"ranking must be a permutation of [0..{n - 1}]; "
                f"got {response.ranking}"
            )
        if response.latency_ms < 0:
            raise ValueError(
                f"latency_ms must be non-negative; got {response.latency_ms}"
            )

        ordered = [question.items[i] for i in response.ranking]
        claim_text = (
            f"ranked items by '{question.dimension}' (most→least): "
            f"{' > '.join(ordered)} | prompt: {question.prompt}"
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
            capture_reason=f"rank_order: {question.question_id}",
        )
        return claim


# =============================================================================
# SPIES — Subjective Probability Interval Estimates (v0.2)
# =============================================================================


@dataclass(frozen=True)
class SPIESQuestion:
    """Render-ready SPIES question payload.

    Per directive Section 7.1: 'SPIES (Subjective Probability Interval
    Estimates) — partner provides an interval estimate for an effect;
    yields variance estimates needed for the precision-weighted active-
    inference layer.'

    Frontend renders prompt + dimension + response_unit; user provides
    [lower, upper] bound on the estimated quantity.
    """

    question_id: str
    prompt: str
    dimension: str        # what's being estimated (e.g., "lift_for_authority_in_status_seekers")
    response_unit: str    # "probability" | "rate" | "ratio"


@dataclass(frozen=True)
class SPIESResponse:
    """Captured response to a SPIESQuestion.

    `lower_bound` and `upper_bound` define the user's subjective
    interval. Validation ensures monotonicity and unit-interval bounds.
    """

    question_id: str
    lower_bound: float
    upper_bound: float
    latency_ms: int


class SPIESGenerator:
    """SPIES generator — interval estimates for variance elicitation.

    HMT §8 v0.2 mode. Used to elicit user UNCERTAINTY (interval width)
    on a target effect. The width feeds the precision-weighted active-
    inference layer (Spine #5) — narrow intervals = high precision;
    wide intervals = low precision.

    Validation:
        - response_unit in {"probability", "rate", "ratio"}
        - 0 ≤ lower_bound ≤ upper_bound ≤ 1 for probability/rate
        - lower_bound < upper_bound (zero-width intervals rejected)
    """

    mode = ElicitationMode.SPIES

    _ALLOWED_UNITS: tuple = ("probability", "rate", "ratio")

    def render(
        self,
        prompt: str,
        dimension: str,
        response_unit: str = "probability",
    ) -> SPIESQuestion:
        if not prompt.strip():
            raise ValueError("prompt must be non-empty")
        if not dimension.strip():
            raise ValueError("dimension must be non-empty")
        if response_unit not in self._ALLOWED_UNITS:
            raise ValueError(
                f"response_unit must be one of {self._ALLOWED_UNITS}; "
                f"got {response_unit!r}"
            )
        return SPIESQuestion(
            question_id=_new_question_id(),
            prompt=prompt,
            dimension=dimension,
            response_unit=response_unit,
        )

    async def capture(
        self,
        context: ElicitationContext,
        question: SPIESQuestion,
        response: SPIESResponse,
        ledger: DialogueLedgerService,
    ) -> Claim:
        if response.question_id != question.question_id:
            raise ValueError(
                f"response.question_id ({response.question_id}) does not "
                f"match question.question_id ({question.question_id})"
            )
        if response.latency_ms < 0:
            raise ValueError(
                f"latency_ms must be non-negative; got {response.latency_ms}"
            )
        # Probability / rate constrained to [0, 1]; ratio is unconstrained.
        if question.response_unit in ("probability", "rate"):
            if not 0.0 <= response.lower_bound <= 1.0:
                raise ValueError(
                    f"lower_bound must be in [0, 1] for "
                    f"{question.response_unit}; got {response.lower_bound}"
                )
            if not 0.0 <= response.upper_bound <= 1.0:
                raise ValueError(
                    f"upper_bound must be in [0, 1] for "
                    f"{question.response_unit}; got {response.upper_bound}"
                )
        if response.lower_bound > response.upper_bound:
            raise ValueError(
                f"lower_bound ({response.lower_bound}) must be ≤ "
                f"upper_bound ({response.upper_bound})"
            )
        if response.lower_bound == response.upper_bound:
            raise ValueError(
                "zero-width interval; SPIES requires a non-degenerate "
                "interval to elicit variance"
            )

        width = response.upper_bound - response.lower_bound
        midpoint = (response.upper_bound + response.lower_bound) / 2.0
        claim_text = (
            f"interval estimate on '{question.dimension}' "
            f"({question.response_unit}): [{response.lower_bound:.3f}, "
            f"{response.upper_bound:.3f}] (midpoint {midpoint:.3f}, "
            f"width {width:.3f}) | prompt: {question.prompt}"
        )

        # stated_confidence is bounded [0, 1] in the Claim model.
        # Probability/rate units → midpoint is a confidence; ratio
        # units → midpoint is not a confidence (can be > 1), so omit.
        stated_conf: Optional[float] = (
            midpoint if question.response_unit in ("probability", "rate")
            else None
        )

        claim = make_claim(
            user_id=context.user_id,
            text=claim_text,
            elicitation_mode=self.mode,
            domain=context.domain,
            stated_confidence=stated_conf,
            latency_ms=response.latency_ms,
            frame=context.frame,
            session_id=context.session_id,
            mood_index=context.mood_index,
        )
        await ledger.record_claim(
            claim,
            capture_reason=f"spies: {question.question_id}",
        )
        return claim


# =============================================================================
# FourPoint — 4-percentile distribution-shape elicitation (v0.2)
# =============================================================================


@dataclass(frozen=True)
class FourPointQuestion:
    """Render-ready FourPoint question payload.

    Per directive Section 7.1: 'FourPoint — partner provides four
    anchor points for a probability distribution; yields full
    distribution shape for prior elicitation.'

    Standard percentile anchors: 10th, 25th, 75th, 90th. With 4 points
    a partner can express asymmetric / skewed distributions that
    SPIES (which only captures interval) cannot.
    """

    question_id: str
    prompt: str
    dimension: str
    response_unit: str  # "probability" | "rate" | "ratio"


@dataclass(frozen=True)
class FourPointResponse:
    """Captured response to a FourPointQuestion.

    Four percentile anchors at 10/25/75/90. Must be monotonic non-
    decreasing.
    """

    question_id: str
    p10: float
    p25: float
    p75: float
    p90: float
    latency_ms: int


class FourPointGenerator:
    """FourPoint generator — 4-percentile distribution-shape elicitation.

    HMT §8 v0.2 mode. Used to elicit FULL DISTRIBUTION SHAPE
    (asymmetry / skew) on a target effect. The shape feeds prior
    elicitation in Spine #1 (more informative than SPIES intervals).

    Validation:
        - response_unit in {"probability", "rate", "ratio"}
        - p10 ≤ p25 ≤ p75 ≤ p90 (monotonic non-decreasing)
        - For probability/rate: all four in [0, 1]
    """

    mode = ElicitationMode.FOUR_POINT

    _ALLOWED_UNITS: tuple = ("probability", "rate", "ratio")

    def render(
        self,
        prompt: str,
        dimension: str,
        response_unit: str = "probability",
    ) -> FourPointQuestion:
        if not prompt.strip():
            raise ValueError("prompt must be non-empty")
        if not dimension.strip():
            raise ValueError("dimension must be non-empty")
        if response_unit not in self._ALLOWED_UNITS:
            raise ValueError(
                f"response_unit must be one of {self._ALLOWED_UNITS}; "
                f"got {response_unit!r}"
            )
        return FourPointQuestion(
            question_id=_new_question_id(),
            prompt=prompt,
            dimension=dimension,
            response_unit=response_unit,
        )

    async def capture(
        self,
        context: ElicitationContext,
        question: FourPointQuestion,
        response: FourPointResponse,
        ledger: DialogueLedgerService,
    ) -> Claim:
        if response.question_id != question.question_id:
            raise ValueError(
                f"response.question_id ({response.question_id}) does not "
                f"match question.question_id ({question.question_id})"
            )
        if response.latency_ms < 0:
            raise ValueError(
                f"latency_ms must be non-negative; got {response.latency_ms}"
            )
        # Range checks for probability / rate
        anchors = (response.p10, response.p25, response.p75, response.p90)
        if question.response_unit in ("probability", "rate"):
            for label, val in zip(("p10", "p25", "p75", "p90"), anchors):
                if not 0.0 <= val <= 1.0:
                    raise ValueError(
                        f"{label} must be in [0, 1] for "
                        f"{question.response_unit}; got {val}"
                    )
        # Monotonicity (non-decreasing)
        if not (response.p10 <= response.p25 <= response.p75 <= response.p90):
            raise ValueError(
                f"anchors must be monotonic non-decreasing "
                f"(p10 ≤ p25 ≤ p75 ≤ p90); got "
                f"p10={response.p10}, p25={response.p25}, "
                f"p75={response.p75}, p90={response.p90}"
            )

        # Median approximated as average of p25 and p75
        median_approx = (response.p25 + response.p75) / 2.0
        # Inter-quartile-range proxy for spread
        iqr = response.p75 - response.p25

        claim_text = (
            f"distribution shape on '{question.dimension}' "
            f"({question.response_unit}): "
            f"p10={response.p10:.3f}, p25={response.p25:.3f}, "
            f"p75={response.p75:.3f}, p90={response.p90:.3f} "
            f"(approx-median {median_approx:.3f}, IQR {iqr:.3f}) | "
            f"prompt: {question.prompt}"
        )

        # stated_confidence bounded [0, 1] — only pass median_approx
        # when response_unit is bounded (probability / rate).
        stated_conf: Optional[float] = (
            median_approx if question.response_unit in ("probability", "rate")
            else None
        )

        claim = make_claim(
            user_id=context.user_id,
            text=claim_text,
            elicitation_mode=self.mode,
            domain=context.domain,
            stated_confidence=stated_conf,
            latency_ms=response.latency_ms,
            frame=context.frame,
            session_id=context.session_id,
            mood_index=context.mood_index,
        )
        await ledger.record_claim(
            claim,
            capture_reason=f"four_point: {question.question_id}",
        )
        return claim


# =============================================================================
# CounterExample — heterogeneous-effect prior elicitation (v0.2)
# =============================================================================


# Per directive Section 7.1: "CounterExample — partner provides
# counterexample cases ('here's a user who is in cohort X but I think
# mechanism Y won't work for them'); yields heterogeneous-effect
# priors."
#
# Closed vocabulary of breakdown reason tags — A12 defense.
COUNTER_EXAMPLE_BREAKDOWN_TAGS: frozenset = frozenset({
    "cohort_membership_uncertain",     # partner thinks user is borderline cohort
    "prior_observation_contradicts",   # past result with this user/cohort
    "context_mismatch",                # mechanism doesn't fit context the partner has seen
    "mechanism_fatigue_observed",      # repeated exposure has degraded
    "specific_user_history_argues_against",  # partner has direct knowledge
    "category_atypical_response",      # category-specific anomaly
})


@dataclass(frozen=True)
class CounterExampleQuestion:
    """Render-ready CounterExample question payload."""

    question_id: str
    prompt: str
    target_belief: str  # e.g., "authority works for status_seekers in luxury_transit"


@dataclass(frozen=True)
class CounterExampleResponse:
    """Captured response to a CounterExampleQuestion.

    Structured slots:
        target_cohort: cohort the partner is naming as the counter-example
        target_mechanism: mechanism the partner thinks won't work
        breakdown_reason_tag: REQUIRED categorical reason from
            COUNTER_EXAMPLE_BREAKDOWN_TAGS
        annotation: optional free-text human-authored context
    """

    question_id: str
    target_cohort: str
    target_mechanism: str
    breakdown_reason_tag: str
    annotation: Optional[str] = None
    latency_ms: int = 0


class CounterExampleGenerator:
    """CounterExample generator — heterogeneous-effect prior elicitation.

    HMT §8 v0.2 mode. Per directive: yields heterogeneous-effect priors
    (the partner's counter-example argues for a moderator on the
    treatment effect).

    Validation:
        - target_cohort + target_mechanism non-empty
        - breakdown_reason_tag REQUIRED + must be in vocabulary
          (A12 defense — categorical signal for analytics loop)
        - annotation optional, human-authored only
    """

    mode = ElicitationMode.COUNTER_EXAMPLE

    def render(
        self,
        prompt: str,
        target_belief: str,
    ) -> CounterExampleQuestion:
        if not prompt.strip():
            raise ValueError("prompt must be non-empty")
        if not target_belief.strip():
            raise ValueError("target_belief must be non-empty")
        return CounterExampleQuestion(
            question_id=_new_question_id(),
            prompt=prompt,
            target_belief=target_belief,
        )

    async def capture(
        self,
        context: ElicitationContext,
        question: CounterExampleQuestion,
        response: CounterExampleResponse,
        ledger: DialogueLedgerService,
    ) -> Claim:
        if response.question_id != question.question_id:
            raise ValueError(
                f"response.question_id ({response.question_id}) does not "
                f"match question.question_id ({question.question_id})"
            )
        if response.latency_ms < 0:
            raise ValueError(
                f"latency_ms must be non-negative; got {response.latency_ms}"
            )
        if not response.target_cohort.strip():
            raise ValueError("target_cohort must be non-empty")
        if not response.target_mechanism.strip():
            raise ValueError("target_mechanism must be non-empty")
        # breakdown_reason_tag REQUIRED + categorical (A12 defense)
        tag = (response.breakdown_reason_tag or "").strip()
        if not tag:
            raise ValueError(
                "breakdown_reason_tag is required (categorical signal). "
                "Free-form annotation alone is insufficient — A12 defense."
            )
        if tag not in COUNTER_EXAMPLE_BREAKDOWN_TAGS:
            raise ValueError(
                f"breakdown_reason_tag '{tag}' not in "
                f"COUNTER_EXAMPLE_BREAKDOWN_TAGS. To add a tag, edit the "
                f"constant; arbitrary tags rejected."
            )

        ann_part = (
            f" | annotation: {response.annotation}"
            if response.annotation else ""
        )
        claim_text = (
            f"counter-example to '{question.target_belief}': "
            f"cohort='{response.target_cohort}', "
            f"mechanism='{response.target_mechanism}', "
            f"reason='{tag}'{ann_part} | prompt: {question.prompt}"
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
            capture_reason=f"counter_example: {question.question_id}",
        )
        return claim


# =============================================================================
# Scenario — conditional prior elicitation (v0.2)
# =============================================================================


# Per directive Section 7.1: "Scenario — partner provides scenario
# descriptions; yields conditional priors ('in this situation, we'd
# expect this outcome')."
#
# Closed vocabularies — A12 defense.
SCENARIO_KIND_TAGS: frozenset = frozenset({
    "morning_commute_pressure",
    "leisure_evening_browse",
    "expense_quarter_close",
    "conference_season_intent",
    "new_user_first_touch",
    "repeat_user_steady_state",
    "post_negative_outcome_re_engage",
    "high_pressure_decision_window",
    "researching_alternatives",
    "weekend_personal_use",
})


SCENARIO_OUTCOME_TAGS: frozenset = frozenset({
    "expected_higher_response",
    "expected_lower_response",
    "expected_indifferent",
    "expected_backfire_risk",
    "expected_delayed_response",
})


@dataclass(frozen=True)
class ScenarioQuestion:
    """Render-ready Scenario question payload."""

    question_id: str
    prompt: str
    mechanism_under_consideration: str  # the mechanism the partner is reasoning about


@dataclass(frozen=True)
class ScenarioResponse:
    """Captured response to a ScenarioQuestion.

    Structured slots:
        scenario_kind_tag: REQUIRED categorical from SCENARIO_KIND_TAGS
        expected_outcome_tag: REQUIRED categorical from
            SCENARIO_OUTCOME_TAGS
        annotation: optional free-text context
    """

    question_id: str
    scenario_kind_tag: str
    expected_outcome_tag: str
    annotation: Optional[str] = None
    latency_ms: int = 0


class ScenarioGenerator:
    """Scenario generator — conditional prior elicitation.

    HMT §8 v0.2 mode. Per directive: yields conditional priors. The
    partner names a scenario class + the outcome they'd expect; the
    resulting Claim conditions a prior on (scenario_kind, mechanism)
    pair.

    Validation:
        - mechanism_under_consideration non-empty
        - scenario_kind_tag REQUIRED + in vocabulary
        - expected_outcome_tag REQUIRED + in vocabulary
        - annotation optional, human-authored only
    """

    mode = ElicitationMode.SCENARIO

    def render(
        self,
        prompt: str,
        mechanism_under_consideration: str,
    ) -> ScenarioQuestion:
        if not prompt.strip():
            raise ValueError("prompt must be non-empty")
        if not mechanism_under_consideration.strip():
            raise ValueError("mechanism_under_consideration must be non-empty")
        return ScenarioQuestion(
            question_id=_new_question_id(),
            prompt=prompt,
            mechanism_under_consideration=mechanism_under_consideration,
        )

    async def capture(
        self,
        context: ElicitationContext,
        question: ScenarioQuestion,
        response: ScenarioResponse,
        ledger: DialogueLedgerService,
    ) -> Claim:
        if response.question_id != question.question_id:
            raise ValueError(
                f"response.question_id ({response.question_id}) does not "
                f"match question.question_id ({question.question_id})"
            )
        if response.latency_ms < 0:
            raise ValueError(
                f"latency_ms must be non-negative; got {response.latency_ms}"
            )
        kind = (response.scenario_kind_tag or "").strip()
        if not kind:
            raise ValueError(
                "scenario_kind_tag is required (categorical signal). "
                "A12 defense."
            )
        if kind not in SCENARIO_KIND_TAGS:
            raise ValueError(
                f"scenario_kind_tag '{kind}' not in SCENARIO_KIND_TAGS. "
                f"To add a tag, edit the constant; arbitrary tags rejected."
            )
        outcome = (response.expected_outcome_tag or "").strip()
        if not outcome:
            raise ValueError(
                "expected_outcome_tag is required (categorical signal). "
                "A12 defense."
            )
        if outcome not in SCENARIO_OUTCOME_TAGS:
            raise ValueError(
                f"expected_outcome_tag '{outcome}' not in "
                f"SCENARIO_OUTCOME_TAGS. To add a tag, edit the constant."
            )

        ann_part = (
            f" | annotation: {response.annotation}"
            if response.annotation else ""
        )
        claim_text = (
            f"scenario '{kind}' for mechanism "
            f"'{question.mechanism_under_consideration}': "
            f"outcome='{outcome}'{ann_part} | prompt: {question.prompt}"
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
            capture_reason=f"scenario: {question.question_id}",
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


def all_v02_generators() -> List[object]:
    """Return one instance of each v0.2 generator added beyond v0.1.

    Full v0.2 suite per directive Section 7.1: kAFC + RankOrder + SPIES
    + FourPoint + CounterExample + Scenario.
    """
    return [
        KAFCGenerator(),
        RankOrderGenerator(),
        SPIESGenerator(),
        FourPointGenerator(),
        CounterExampleGenerator(),
        ScenarioGenerator(),
    ]


__all__ = [
    "COUNTER_EXAMPLE_BREAKDOWN_TAGS",
    "CounterExampleGenerator",
    "CounterExampleQuestion",
    "CounterExampleResponse",
    "ElicitationContext",
    "ForcedPairGenerator",
    "ForcedPairQuestion",
    "ForcedPairResponse",
    "FourPointGenerator",
    "FourPointQuestion",
    "FourPointResponse",
    "KAFCGenerator",
    "KAFCQuestion",
    "KAFCResponse",
    "RankOrderGenerator",
    "RankOrderQuestion",
    "RankOrderResponse",
    "RecallabilityProbeGenerator",
    "RecallabilityProbeQuestion",
    "RecallabilityProbeResponse",
    "SCENARIO_KIND_TAGS",
    "SCENARIO_OUTCOME_TAGS",
    "SPIESGenerator",
    "SPIESQuestion",
    "SPIESResponse",
    "ScenarioGenerator",
    "ScenarioQuestion",
    "ScenarioResponse",
    "StoryPromptGenerator",
    "StoryPromptQuestion",
    "StoryPromptResponse",
    "TimedPairGenerator",
    "TimedPairQuestion",
    "TimedPairResponse",
    "all_v01_generators",
    "all_v02_generators",
]
