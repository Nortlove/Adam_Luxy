# =============================================================================
# ADAM Dialogue Ledger — Session-Start Mood Probe (Loop B v0.1)
# Location: adam/intelligence/dialogue_ledger/mood_probe.py
# =============================================================================

"""
SESSION-START MOOD PROBE — HMT §7.6 + §6 Principle 3

Two-alternative timed-choice on affective imagery at session start.
Indexes mood, which is then covariate-adjusted out of subsequent
elicitations within the session.

WHY THIS MATTERS

  - Schwarz & Clore (1983) — sunny-day vs. rainy-day study: life-
    satisfaction ratings tracked weather, but the effect disappeared
    when subjects were cued to attribute their mood to the weather.
    Implication: any subsequent elicited rating is contaminated by
    ambient mood unless we surface it.
  - HMT §7.6: mood and bias are first-class contaminants. The platform
    instruments them.

DESIGN

  - The probe is two render-ready imagery choices (e.g. "warm sunlit
    landscape" vs "cold overcast cityscape"). User picks the one that
    feels more like their current state.
  - The choice maps to a mood_index in [0, 1]: positive imagery picked
    → 1.0; negative imagery picked → 0.0. Real production wires would
    use validated affective stimuli (IAPS database or similar); v0.1
    uses simple labelled options.
  - mood_index is stored on the SessionMoodState object and picked up
    by elicitation generators via ElicitationContext.mood_index.

DISCIPLINE

  - The probe is BINARY forced-choice (HMT discipline rule 14 —
    binary over Likert).
  - The probe is TIMED (default 5s) — Type 1 elicitation, no
    deliberation.
  - The mood_index is a covariate, not a prediction. Subsequent
    elicitations carry the index for analytic adjustment, not as a
    weight on the user's substantive responses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import uuid4


# =============================================================================
# Affective option enum
# =============================================================================


class AffectivePolarity(str, Enum):
    """Which polarity an option represents.

    POSITIVE / NEGATIVE — the binary forced-choice axis.
    """

    POSITIVE = "positive"
    NEGATIVE = "negative"


# =============================================================================
# Mood probe payloads
# =============================================================================


def _new_probe_id() -> str:
    return f"mood:{uuid4().hex[:16]}"


@dataclass(frozen=True)
class MoodProbeOption:
    """One option in the binary forced-choice.

    `label` — render-ready text/image label.
    `polarity` — POSITIVE or NEGATIVE; determines which mood_index the
        choice maps to.
    """

    label: str
    polarity: AffectivePolarity


@dataclass(frozen=True)
class MoodProbeQuestion:
    """Render-ready session-start mood probe.

    Two options are presented; user picks the one that feels more like
    their current state. `countdown_seconds` drives the timed element
    (default 5s — HMT §6 Principle 2).
    """

    probe_id: str
    prompt: str
    option_a: MoodProbeOption
    option_b: MoodProbeOption
    countdown_seconds: float


@dataclass(frozen=True)
class MoodProbeResponse:
    """Captured response.

    `chosen` is "a" or "b" or None (when deadline_hit).
    `latency_ms` is response time.
    """

    probe_id: str
    chosen: Optional[str]
    latency_ms: int
    deadline_hit: bool = False


# =============================================================================
# Session mood state
# =============================================================================


@dataclass
class SessionMoodState:
    """Per-session mood index + provenance.

    `mood_index` ∈ [0, 1] where 0=negative polarity chosen, 1=positive.
    `confidence` reflects fast/clean response (high) vs deadline-hit /
    slow (low). Default 0.5 confidence on deadline-hit, 1.0 on a
    fast-and-clean choice within 30% of the countdown window.

    Subsequent elicitations within the session carry `mood_index` via
    ElicitationContext for covariate adjustment.
    """

    session_id: str
    user_id: str
    mood_index: float
    confidence: float
    set_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    probe_id: Optional[str] = None
    deadline_hit: bool = False


# =============================================================================
# Generator
# =============================================================================


# Default affective options. Production wires would load validated
# IAPS-style stimuli; v0.1 uses simple labelled placeholders.
_DEFAULT_POSITIVE_OPTIONS: List[MoodProbeOption] = [
    MoodProbeOption(
        label="warm, sunlit landscape with open sky",
        polarity=AffectivePolarity.POSITIVE,
    ),
    MoodProbeOption(
        label="bright morning, gentle breeze",
        polarity=AffectivePolarity.POSITIVE,
    ),
    MoodProbeOption(
        label="forest path lit by afternoon sun",
        polarity=AffectivePolarity.POSITIVE,
    ),
]

_DEFAULT_NEGATIVE_OPTIONS: List[MoodProbeOption] = [
    MoodProbeOption(
        label="cold, overcast cityscape after rain",
        polarity=AffectivePolarity.NEGATIVE,
    ),
    MoodProbeOption(
        label="empty waiting room, fluorescent lighting",
        polarity=AffectivePolarity.NEGATIVE,
    ),
    MoodProbeOption(
        label="industrial corridor at dusk",
        polarity=AffectivePolarity.NEGATIVE,
    ),
]


class MoodProbeGenerator:
    """Session-start affective two-alternative forced-choice generator.

    Uses internal randomness for option selection within polarity sets;
    accepts an optional `seed` for deterministic test runs.
    """

    DEFAULT_COUNTDOWN_SECONDS: float = 5.0
    DEADLINE_HIT_CONFIDENCE: float = 0.3
    FAST_RESPONSE_CONFIDENCE: float = 1.0
    SLOW_RESPONSE_CONFIDENCE: float = 0.5
    DEFAULT_PROMPT: str = (
        "Which of these feels more like your state right now?"
    )

    def __init__(
        self,
        positive_options: Optional[List[MoodProbeOption]] = None,
        negative_options: Optional[List[MoodProbeOption]] = None,
    ) -> None:
        # Only fall back to defaults when input is None — an empty list
        # is an explicit "I want zero options" signal that should fail.
        if positive_options is None:
            self._positive = list(_DEFAULT_POSITIVE_OPTIONS)
        else:
            self._positive = list(positive_options)
        if negative_options is None:
            self._negative = list(_DEFAULT_NEGATIVE_OPTIONS)
        else:
            self._negative = list(negative_options)
        if not self._positive or not self._negative:
            raise ValueError(
                "MoodProbeGenerator requires at least one positive AND "
                "one negative option"
            )

    def render(
        self,
        countdown_seconds: Optional[float] = None,
        prompt: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> MoodProbeQuestion:
        """Render a render-ready mood probe.

        `seed` allows deterministic option selection for test runs.
        """
        import random
        rng = random.Random(seed) if seed is not None else random

        positive_choice = rng.choice(self._positive)
        negative_choice = rng.choice(self._negative)

        # Randomize which side is option_a vs option_b so the user
        # doesn't develop a bias toward picking position A.
        if rng.random() < 0.5:
            option_a, option_b = positive_choice, negative_choice
        else:
            option_a, option_b = negative_choice, positive_choice

        return MoodProbeQuestion(
            probe_id=_new_probe_id(),
            prompt=prompt or self.DEFAULT_PROMPT,
            option_a=option_a,
            option_b=option_b,
            countdown_seconds=(
                countdown_seconds
                if countdown_seconds is not None
                else self.DEFAULT_COUNTDOWN_SECONDS
            ),
        )

    def capture(
        self,
        session_id: str,
        user_id: str,
        question: MoodProbeQuestion,
        response: MoodProbeResponse,
    ) -> SessionMoodState:
        """Capture the response and produce a SessionMoodState.

        Pure function — does NOT write to the dialogue ledger directly.
        Mood state is per-session ephemeral data; subsequent elicitations
        carry the mood_index via ElicitationContext, where the value
        lands on each Claim's `mood_index` field for permanent record.
        """
        if response.probe_id != question.probe_id:
            raise ValueError(
                "response.probe_id does not match question.probe_id"
            )
        if response.latency_ms < 0:
            raise ValueError("latency_ms must be non-negative")

        if response.deadline_hit:
            if response.chosen is not None:
                raise ValueError(
                    "chosen must be None when deadline_hit=True"
                )
            # On deadline-hit, default to neutral mood (0.5) with low
            # confidence — caller may decide to skip mood adjustment.
            return SessionMoodState(
                session_id=session_id,
                user_id=user_id,
                mood_index=0.5,
                confidence=self.DEADLINE_HIT_CONFIDENCE,
                probe_id=question.probe_id,
                deadline_hit=True,
            )

        if response.chosen not in ("a", "b"):
            raise ValueError(
                f"chosen must be 'a' or 'b'; got {response.chosen!r}"
            )

        chosen_option = (
            question.option_a if response.chosen == "a"
            else question.option_b
        )

        # Mood index from polarity
        mood_index = (
            1.0 if chosen_option.polarity == AffectivePolarity.POSITIVE
            else 0.0
        )

        # Confidence from latency: fast (within 30% of countdown) →
        # high confidence Type 1 response. Slow (>= 70% of countdown)
        # → lower confidence Type 2 deliberation.
        countdown_ms = question.countdown_seconds * 1000
        latency_fraction = response.latency_ms / countdown_ms
        if latency_fraction <= 0.3:
            confidence = self.FAST_RESPONSE_CONFIDENCE
        elif latency_fraction >= 0.7:
            confidence = self.SLOW_RESPONSE_CONFIDENCE
        else:
            # Linear interpolation
            confidence = (
                self.SLOW_RESPONSE_CONFIDENCE
                + (self.FAST_RESPONSE_CONFIDENCE - self.SLOW_RESPONSE_CONFIDENCE)
                * (0.7 - latency_fraction) / 0.4
            )

        return SessionMoodState(
            session_id=session_id,
            user_id=user_id,
            mood_index=mood_index,
            confidence=confidence,
            probe_id=question.probe_id,
            deadline_hit=False,
        )


__all__ = [
    "AffectivePolarity",
    "MoodProbeGenerator",
    "MoodProbeOption",
    "MoodProbeQuestion",
    "MoodProbeResponse",
    "SessionMoodState",
]
