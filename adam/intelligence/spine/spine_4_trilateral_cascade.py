# =============================================================================
# ADAM Spine #4 — Trilateral L3 Cascade with Hard Fluency Floor
# Location: adam/intelligence/spine/spine_4_trilateral_cascade.py
# =============================================================================

"""Trilateral L3 cascade — User × Mechanism × Page-Conditioned Posture.

PER DIRECTIVE SECTION 4 (Spine #4 specification).

A scoring function f(user_state, page_attentional_posture,
mechanism_candidate) → score that operates on the bilateral edge from
Spine #3 with page-attentional-posture as a *first-class* third
dimension, NOT a post-hoc tag. Combined with the mechanism-interaction
tensor from Spine #1's δ_iac term, this produces the per-decision
score that drives action selection.

WHY THIS IS SPINE

Per the directive: "This is the operationalization of attention-
inversion at the recommendation policy. The page is not a topic tag
(IAB category); it is an attentional posture vector that conditions
which mechanism can blend rather than grab. Industry contextual
platforms target on page topic; very few model page-conditioned
attentional posture as a structured dimension; and *none* use it as
a third dimension of the cascade alongside user state and mechanism
candidate. This is the largest single contributor to 'we have
something nobody else has.'"

DECISION-TIME CONSUMERS (Rule A check)

The trilateral cascade IS the decision-time scoring function. Direct
serving-path consumer:
    - The orchestrator's recommendation policy reads this score for
      each candidate and runs top-two Thompson sampling on it
    - The fluency floor (a method on this module) FILTERS the eligible
      set — candidates below floor are removed regardless of any other
      score (architectural enforcement of attention-inversion)
    - Spine #5 (free-energy scorer) reads the trilateral score as part
      of the soft objective composition
    - Spine #6 (DecisionTrace) records the trilateral decomposition
      (per-component contribution) for partner-facing audit

This IS the cognitive primitive the platform's market differentiator
rests on. Foundation §7 rule 11 (fitness function IS the ethics) made
operational at the policy level.

THIS COMMIT SHIPS

    - 5 posture classes (PageAttentionalPosture enum) per directive §4.2
    - PagePostureScore Pydantic model (posture distribution + auxiliary
      regression heads: cognitive load, valence, arousal, info density,
      goal-pursuit clarity)
    - POSTURE_MECHANISM_COMPATIBILITY matrix — prior (posture, mechanism)
      compatibility scores in [-1, +1] from cognitive-psych literature
    - TrilateralScore Pydantic model — full structured decomposition
      that the DecisionTrace consumes
    - score_candidate — the trilateral scoring function
    - check_fluency_floor — HARD architectural constraint
    - filter_eligible_by_fluency_floor — eligibility filter

THIS COMMIT DOES NOT SHIP (follow-on commits)

    - Sentence-transformer integration (`all-mpnet-base-v2`) — wired
      when sentence-transformers is added to requirements.txt. The
      PagePostureScore shape is stable; the encoder produces it.
    - Posture-head fine-tuning on hand-labeled URLs — a training
      pipeline; the substrate is consumer-side
    - Free-energy modulation (Spine #5 — separate spine, separate commit)
    - Top-two Thompson sampling action selection (orchestrator-level
      composition; reads trilateral score as input)

PRINCIPLE 2 ENFORCEMENT — THE FLUENCY FLOOR

Per directive Section 4.4: "The fluency floor is a HARD architectural
constraint, NOT an optimization term." Below the calibrated threshold,
a candidate is REMOVED from the eligible set, regardless of any other
score. No epistemic bonus, no exploitation pressure, no override.

Foundation §7 rule 11 made operational. Soft objectives drift under
reward pressure. Floors don't.

REFERENCES

    Cognitive-psych literature on page-attentional-posture signatures:
    information-foraging theory (Pirolli), task vs leisure attentional
    modes, social-consumption fatigue dynamics. The 5-class posture
    taxonomy is grounded — each class has documented signature in the
    cog-psych canon.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


# =============================================================================
# Page attentional-posture taxonomy (per directive §4.2)
# =============================================================================


class PageAttentionalPosture(str, Enum):
    """Five posture classes per directive Section 4.2.

    Each class has a documented attentional signature in the cognitive
    psych canon, which becomes the partner-facing 'why' vocabulary.

    INFORMATION_FORAGING — research-mode, comparative-evaluation pages.
        Pirolli & Card information-foraging theory. User is in
        diet-and-information-patch mode; attentional resources allocated
        to scanning structured information.

    TASK_COMPLETION — booking flows, calendar/expense tooling, in-flow
        productivity. User has a clear goal and is task-oriented;
        attentional resources allocated to completion of the task.

    LEISURE_BROWSING — entertainment, lifestyle, low-stakes content.
        User in default-network mode; attentional resources diffuse;
        recall and reactance both lower.

    SOCIAL_CONSUMPTION — social media, news-as-feed, peer-driven content.
        User in identity-construction / social-comparison mode;
        attentional resources allocated to peer signals; reactance
        risk to attention-grabbing creative is HIGH (the user is
        already fatigued from feed-grabbing dynamics).

    TRANSACTIONAL_COMPARISON — purchase-research, head-to-head
        comparisons, review-heavy. User in evaluation mode with
        explicit cognitive load on options analysis; high-effort
        comparison processing already engaged.
    """

    INFORMATION_FORAGING = "information_foraging"
    TASK_COMPLETION = "task_completion"
    LEISURE_BROWSING = "leisure_browsing"
    SOCIAL_CONSUMPTION = "social_consumption"
    TRANSACTIONAL_COMPARISON = "transactional_comparison"


# Convenience: ordered tuple of all classes (for posture distribution
# vector ordering).
POSTURE_CLASSES_ORDERED: Tuple[PageAttentionalPosture, ...] = (
    PageAttentionalPosture.INFORMATION_FORAGING,
    PageAttentionalPosture.TASK_COMPLETION,
    PageAttentionalPosture.LEISURE_BROWSING,
    PageAttentionalPosture.SOCIAL_CONSUMPTION,
    PageAttentionalPosture.TRANSACTIONAL_COMPARISON,
)


# =============================================================================
# PagePostureScore — encoder output structure
# =============================================================================


class PagePostureScore(BaseModel):
    """Output of the page-attentional-posture encoder.

    Per directive Section 4.2: "Output: posture distribution (5-vector)
    + raw 768-dim embedding. Both flow into the cascade."

    Plus auxiliary regression heads: cognitive load, valence, arousal,
    info density, goal-pursuit clarity. Each in [0, 1] (valence in
    [-1, +1]).

    Posture confidence in [0, 1] is used to weight the posture's
    influence on the cascade. Low-confidence pages fall back to
    category-prior-only scoring with no posture conditioning (per
    directive §4.2 calibration).
    """

    model_config = ConfigDict(extra="forbid")

    page_url: str
    posture_distribution: List[float]   # 5-vector; sums to ~1
    posture_confidence: float           # in [0, 1]
    argmax_posture: PageAttentionalPosture

    # Auxiliary regression heads
    cognitive_load: float = 0.5         # in [0, 1]
    emotional_valence: float = 0.0      # in [-1, +1]
    arousal: float = 0.5                # in [0, 1]
    information_density: float = 0.5    # in [0, 1]
    goal_pursuit_clarity: float = 0.5   # in [0, 1]

    # Raw embedding (optional; may be omitted at decision time when
    # the cascade only needs the structured fields). 768-dim per
    # all-mpnet-base-v2; stored as float list for JSON compatibility.
    raw_embedding: Optional[List[float]] = None

    encoded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("posture_distribution")
    @classmethod
    def _validate_distribution(cls, v: List[float]) -> List[float]:
        if len(v) != len(POSTURE_CLASSES_ORDERED):
            raise ValueError(
                f"posture_distribution must have length "
                f"{len(POSTURE_CLASSES_ORDERED)}; got {len(v)}"
            )
        for w in v:
            if w < 0.0 or w > 1.0:
                raise ValueError(
                    f"posture_distribution entries must be in [0, 1]; got {w}"
                )
        s = sum(v)
        if abs(s - 1.0) > 1e-3:
            raise ValueError(
                f"posture_distribution must sum to ~1.0 (tol 1e-3); got {s}"
            )
        return v

    @field_validator("posture_confidence")
    @classmethod
    def _validate_confidence(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"posture_confidence must be in [0, 1]; got {v}")
        return v

    @field_validator("emotional_valence")
    @classmethod
    def _validate_valence(cls, v: float) -> float:
        if not -1.0 <= v <= 1.0:
            raise ValueError(f"emotional_valence must be in [-1, +1]; got {v}")
        return v


# =============================================================================
# Posture × Mechanism compatibility prior matrix (per directive §4.3)
# =============================================================================


# Compatibility scores in [-1, +1]:
#   +1: highly fluent (mechanism naturally fulfills the goal the
#       posture is in)
#    0: neutral (mechanism is neither aided nor hindered)
#   -1: incompatible (mechanism fights the posture)
#
# Per directive Section 4.3, illustrative initial values from cognitive-
# psych literature. The matrix is updated by online observations; the
# campaign-level posterior on compatibility(posture, mechanism) is part
# of the bilateral edge structure (Spine #3).
#
# Pilot-pending: these are designer-asserted; the offline pipeline
# (Spine #12) refines via observed outcomes.

POSTURE_MECHANISM_COMPATIBILITY: Dict[Tuple[PageAttentionalPosture, str], float] = {
    # ─ INFORMATION_FORAGING ─────────────────────────────────────────────
    (PageAttentionalPosture.INFORMATION_FORAGING, "loss_aversion"):    0.0,
    (PageAttentionalPosture.INFORMATION_FORAGING, "construal_concrete"): 0.7,
    (PageAttentionalPosture.INFORMATION_FORAGING, "construal_abstract"): -0.2,
    (PageAttentionalPosture.INFORMATION_FORAGING, "authority"):         0.5,
    (PageAttentionalPosture.INFORMATION_FORAGING, "social_proof"):      0.3,
    (PageAttentionalPosture.INFORMATION_FORAGING, "scarcity"):         -0.5,  # fights research mode
    (PageAttentionalPosture.INFORMATION_FORAGING, "urgency"):          -0.6,
    (PageAttentionalPosture.INFORMATION_FORAGING, "frame_gain"):        0.2,
    (PageAttentionalPosture.INFORMATION_FORAGING, "frame_loss"):        0.0,
    (PageAttentionalPosture.INFORMATION_FORAGING, "comparison_framing"): 0.6,
    (PageAttentionalPosture.INFORMATION_FORAGING, "reliability_metaphor"): 0.4,
    (PageAttentionalPosture.INFORMATION_FORAGING, "containment_metaphor"): 0.1,
    (PageAttentionalPosture.INFORMATION_FORAGING, "forward_motion_metaphor"): 0.0,
    (PageAttentionalPosture.INFORMATION_FORAGING, "status_verticality_metaphor"): -0.1,
    (PageAttentionalPosture.INFORMATION_FORAGING, "identity_construction"): -0.3,

    # ─ TASK_COMPLETION (productivity / booking flows) ────────────────────
    (PageAttentionalPosture.TASK_COMPLETION, "loss_aversion"):         -0.4,
    (PageAttentionalPosture.TASK_COMPLETION, "construal_concrete"):     0.6,
    (PageAttentionalPosture.TASK_COMPLETION, "construal_abstract"):    -0.4,
    (PageAttentionalPosture.TASK_COMPLETION, "authority"):              0.4,
    (PageAttentionalPosture.TASK_COMPLETION, "social_proof"):           0.0,
    (PageAttentionalPosture.TASK_COMPLETION, "scarcity"):              -0.7,  # fights goal completion
    (PageAttentionalPosture.TASK_COMPLETION, "urgency"):               -0.7,
    (PageAttentionalPosture.TASK_COMPLETION, "frame_gain"):             0.3,
    (PageAttentionalPosture.TASK_COMPLETION, "frame_loss"):            -0.2,
    (PageAttentionalPosture.TASK_COMPLETION, "comparison_framing"):     0.0,
    (PageAttentionalPosture.TASK_COMPLETION, "reliability_metaphor"):   0.7,  # very fluent
    (PageAttentionalPosture.TASK_COMPLETION, "containment_metaphor"):   0.5,
    (PageAttentionalPosture.TASK_COMPLETION, "forward_motion_metaphor"): 0.7,
    (PageAttentionalPosture.TASK_COMPLETION, "status_verticality_metaphor"): -0.1,
    (PageAttentionalPosture.TASK_COMPLETION, "identity_construction"): -0.4,

    # ─ LEISURE_BROWSING ──────────────────────────────────────────────────
    (PageAttentionalPosture.LEISURE_BROWSING, "loss_aversion"):        -0.3,
    (PageAttentionalPosture.LEISURE_BROWSING, "construal_concrete"):    0.0,
    (PageAttentionalPosture.LEISURE_BROWSING, "construal_abstract"):    0.5,
    (PageAttentionalPosture.LEISURE_BROWSING, "authority"):             0.0,
    (PageAttentionalPosture.LEISURE_BROWSING, "social_proof"):          0.3,
    (PageAttentionalPosture.LEISURE_BROWSING, "scarcity"):             -0.5,
    (PageAttentionalPosture.LEISURE_BROWSING, "urgency"):              -0.5,
    (PageAttentionalPosture.LEISURE_BROWSING, "frame_gain"):            0.4,
    (PageAttentionalPosture.LEISURE_BROWSING, "frame_loss"):           -0.3,
    (PageAttentionalPosture.LEISURE_BROWSING, "comparison_framing"):   -0.2,
    (PageAttentionalPosture.LEISURE_BROWSING, "reliability_metaphor"):  0.2,
    (PageAttentionalPosture.LEISURE_BROWSING, "containment_metaphor"):  0.4,
    (PageAttentionalPosture.LEISURE_BROWSING, "forward_motion_metaphor"): 0.3,
    (PageAttentionalPosture.LEISURE_BROWSING, "status_verticality_metaphor"): 0.4,
    (PageAttentionalPosture.LEISURE_BROWSING, "identity_construction"): 0.5,

    # ─ SOCIAL_CONSUMPTION (peer signals; reactance HIGH) ─────────────────
    (PageAttentionalPosture.SOCIAL_CONSUMPTION, "loss_aversion"):      -0.5,
    (PageAttentionalPosture.SOCIAL_CONSUMPTION, "construal_concrete"): -0.1,
    (PageAttentionalPosture.SOCIAL_CONSUMPTION, "construal_abstract"):  0.4,
    (PageAttentionalPosture.SOCIAL_CONSUMPTION, "authority"):          -0.2,
    (PageAttentionalPosture.SOCIAL_CONSUMPTION, "social_proof"):        0.5,  # natural fit
    (PageAttentionalPosture.SOCIAL_CONSUMPTION, "scarcity"):           -0.7,  # high reactance risk
    (PageAttentionalPosture.SOCIAL_CONSUMPTION, "urgency"):            -0.8,
    (PageAttentionalPosture.SOCIAL_CONSUMPTION, "frame_gain"):          0.3,
    (PageAttentionalPosture.SOCIAL_CONSUMPTION, "frame_loss"):         -0.2,
    (PageAttentionalPosture.SOCIAL_CONSUMPTION, "comparison_framing"): -0.3,
    (PageAttentionalPosture.SOCIAL_CONSUMPTION, "reliability_metaphor"): 0.0,
    (PageAttentionalPosture.SOCIAL_CONSUMPTION, "containment_metaphor"): 0.2,
    (PageAttentionalPosture.SOCIAL_CONSUMPTION, "forward_motion_metaphor"): 0.2,
    (PageAttentionalPosture.SOCIAL_CONSUMPTION, "status_verticality_metaphor"): 0.5,
    (PageAttentionalPosture.SOCIAL_CONSUMPTION, "identity_construction"): 0.5,

    # ─ TRANSACTIONAL_COMPARISON ──────────────────────────────────────────
    (PageAttentionalPosture.TRANSACTIONAL_COMPARISON, "loss_aversion"): 0.3,
    (PageAttentionalPosture.TRANSACTIONAL_COMPARISON, "construal_concrete"): 0.7,
    (PageAttentionalPosture.TRANSACTIONAL_COMPARISON, "construal_abstract"): -0.4,
    (PageAttentionalPosture.TRANSACTIONAL_COMPARISON, "authority"):     0.5,
    (PageAttentionalPosture.TRANSACTIONAL_COMPARISON, "social_proof"):  0.5,
    (PageAttentionalPosture.TRANSACTIONAL_COMPARISON, "scarcity"):      0.0,
    (PageAttentionalPosture.TRANSACTIONAL_COMPARISON, "urgency"):      -0.2,
    (PageAttentionalPosture.TRANSACTIONAL_COMPARISON, "frame_gain"):    0.3,
    (PageAttentionalPosture.TRANSACTIONAL_COMPARISON, "frame_loss"):    0.3,
    (PageAttentionalPosture.TRANSACTIONAL_COMPARISON, "comparison_framing"): 0.7,
    (PageAttentionalPosture.TRANSACTIONAL_COMPARISON, "reliability_metaphor"): 0.6,
    (PageAttentionalPosture.TRANSACTIONAL_COMPARISON, "containment_metaphor"): 0.2,
    (PageAttentionalPosture.TRANSACTIONAL_COMPARISON, "forward_motion_metaphor"): 0.2,
    (PageAttentionalPosture.TRANSACTIONAL_COMPARISON, "status_verticality_metaphor"): 0.0,
    (PageAttentionalPosture.TRANSACTIONAL_COMPARISON, "identity_construction"): -0.1,
}


def get_posture_mechanism_compatibility(
    posture: PageAttentionalPosture,
    mechanism: str,
) -> float:
    """Return the (posture, mechanism) compatibility score in [-1, +1].

    Returns 0.0 for unspecified pairs (neutral; doesn't penalize but
    doesn't help). The offline pipeline expands the matrix when new
    mechanisms are added.
    """
    return POSTURE_MECHANISM_COMPATIBILITY.get((posture, mechanism), 0.0)


# =============================================================================
# Fluency floor (HARD architectural constraint)
# =============================================================================


# Per directive Section 4.4: "Target violation rate: 0.5–2% of decisions.
# Below 0.1% means the floor is too lax; above 5% means too strict."
#
# The floor is calibrated against the held-out labeled "this is grabby /
# this is blendy" page-creative pair set. Pilot-pending value here;
# Phase 2 gate validates calibration.
DEFAULT_FLUENCY_FLOOR: float = -0.4


def compute_fluency_score(
    posture: PageAttentionalPosture,
    mechanism: str,
    posture_confidence: float = 1.0,
) -> float:
    """Compute the fluency-against-context score for a (posture, mechanism)
    candidate.

    Score = compatibility * confidence. Low-confidence postures
    attenuate compatibility magnitude (per directive §4.2: "Low-
    confidence pages fall back to category-prior-only scoring with no
    posture conditioning").

    Returns float in roughly [-1, +1].
    """
    if not 0.0 <= posture_confidence <= 1.0:
        raise ValueError(
            f"posture_confidence must be in [0, 1]; got {posture_confidence}"
        )
    compatibility = get_posture_mechanism_compatibility(posture, mechanism)
    return compatibility * posture_confidence


def check_fluency_floor(
    posture: PageAttentionalPosture,
    mechanism: str,
    posture_confidence: float = 1.0,
    *,
    floor: float = DEFAULT_FLUENCY_FLOOR,
) -> bool:
    """HARD architectural constraint check.

    Returns True iff (posture, mechanism, confidence) passes the
    fluency floor (i.e., is eligible to be served). Returns False
    iff it MUST be removed from the eligible set.

    Per directive Section 4.4: "Below the calibrated threshold, the
    candidate is *removed* from the eligible set. Period. No epistemic
    bonus, no exploitation pressure, no override."

    This is the architectural enforcement of attention-inversion.
    Foundation §7 rule 11 made operational.
    """
    score = compute_fluency_score(posture, mechanism, posture_confidence)
    return score >= floor


# =============================================================================
# Trilateral score
# =============================================================================


@dataclass(frozen=True)
class TrilateralScoreComponents:
    """Decomposition of the trilateral score for a candidate.

    Each component is structured for the DecisionTrace renderer
    (Spine #6) to surface as a contribution percentage in the
    Defensive Reasoning panel.
    """

    user_posterior_contribution: float   # from Spine #1's effective_mean
    bilateral_edge_contribution: float    # from Spine #3 (placeholder; wired Phase 5)
    posture_compatibility_contribution: float
    carryover_correction_contribution: float
    base_score: float


class TrilateralScore(BaseModel):
    """Full trilateral score for one candidate at decision time.

    Read by the orchestrator's recommendation policy (top-two Thompson
    sampling) and by Spine #5 free-energy and Spine #6 DecisionTrace.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: str
    mechanism: str
    posture: PageAttentionalPosture
    score: float
    fluency_score: float
    fluency_floor_passed: bool
    components: Dict[str, float] = Field(default_factory=dict)


def score_candidate(
    user_id: str,
    mechanism: str,
    posture: PageAttentionalPosture,
    posture_confidence: float = 1.0,
    user_posterior_mean_for_mechanism: float = 0.0,
    bilateral_edge_score: float = 0.0,
    carryover_correction: float = 0.0,
    *,
    floor: float = DEFAULT_FLUENCY_FLOOR,
) -> TrilateralScore:
    """Score a candidate (user, mechanism, posture) triple.

    The score is a precision-weighted combination of:
        1. Per-user posterior on mechanism efficacy (from Spine #1)
        2. Bilateral edge causal-effect estimate (from Spine #3;
           placeholder until Phase 5)
        3. Page-attentional-posture compatibility (this module)
        4. Carryover-corrected adjustment (from Spine #2)

    The fluency_floor check runs INSIDE this function so the policy
    layer just reads `fluency_floor_passed` and removes failing
    candidates from the eligible set.

    Free-energy modulation (Spine #5) and epistemic-value bonus
    (Spine #8) are added by the orchestrator AFTER this scoring;
    they are soft objectives composed atop the trilateral score.
    """
    fluency = compute_fluency_score(posture, mechanism, posture_confidence)
    floor_passed = fluency >= floor

    base = (
        user_posterior_mean_for_mechanism
        + bilateral_edge_score
        + fluency
        + carryover_correction
    )

    components = {
        "user_posterior": user_posterior_mean_for_mechanism,
        "bilateral_edge": bilateral_edge_score,
        "posture_compatibility": fluency,
        "carryover": carryover_correction,
    }

    return TrilateralScore(
        user_id=user_id,
        mechanism=mechanism,
        posture=posture,
        score=base,
        fluency_score=fluency,
        fluency_floor_passed=floor_passed,
        components=components,
    )


def filter_by_fluency_floor(
    scores: List[TrilateralScore],
    *,
    floor: float = DEFAULT_FLUENCY_FLOOR,
) -> Tuple[List[TrilateralScore], List[TrilateralScore]]:
    """Split a list of TrilateralScore into (eligible, filtered_out).

    The eligible list is what the orchestrator's recommendation policy
    samples from; the filtered_out list is recorded in the DecisionTrace
    for partner-facing audit (so the Defensive Reasoning panel can
    show "scarcity was removed by the fluency floor on this social-
    consumption page").

    Note: the score's fluency_floor_passed is set at scoring time;
    this function uses it (and the floor argument) to ensure consistency
    even if scores were produced with a different floor.
    """
    eligible: List[TrilateralScore] = []
    filtered: List[TrilateralScore] = []
    for s in scores:
        if s.fluency_score >= floor:
            eligible.append(s)
        else:
            filtered.append(s)
    return eligible, filtered


__all__ = [
    "DEFAULT_FLUENCY_FLOOR",
    "PageAttentionalPosture",
    "POSTURE_CLASSES_ORDERED",
    "POSTURE_MECHANISM_COMPATIBILITY",
    "PagePostureScore",
    "TrilateralScore",
    "TrilateralScoreComponents",
    "check_fluency_floor",
    "compute_fluency_score",
    "filter_by_fluency_floor",
    "get_posture_mechanism_compatibility",
    "score_candidate",
]
