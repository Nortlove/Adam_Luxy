# =============================================================================
# ADAM Spine #5 — Active-Inference Free-Energy Objective
# Location: adam/intelligence/spine/spine_5_free_energy.py
# =============================================================================

"""Active-inference free-energy objective — attention-inversion as math.

PER DIRECTIVE SECTION 2 (Spine #5) + SECTION 5.

The user's deepest commitment — attention-inversion, blend-into-context-
and-fulfill-primed-goal — is *literally* the predictive coding / active
inference principle applied to ad selection. The brain minimizes
precision-weighted prediction error; an ad that minimizes the user's
prediction error relative to their current context-induced model will
be processed implicitly (Bargh-style automatic processing) without
triggering reactance.

This is NOT metaphor. It is the same math.

WHY THIS IS SPINE — the deepest primitive

Per directive: "The platform's defining strategic claim — that it
serves by blending rather than grabbing — has lived in the architecture
as a soft preference and a vocabulary discipline. It needs to live as
a *decision-time scoring objective* with a closed-form interpretation.
Active inference provides exactly that. Without it, attention-inversion
is a marketing claim. With it, attention-inversion is the optimization
target."

THE MATH (per directive Section 2 Spine #5)

For each candidate creative-mechanism `a` given user state `s` and
page posture `c`:

    F(a | s, c) = D_KL(q(goal_state | a, s, c) || p(goal_state | s, c))
                  − π(c) · log p(observation = a | goal_state)

    First term — ambiguity / mismatch term:
        KL divergence between the user's goal-state distribution
        implied by serving `a` and the goal-state distribution primed
        by the page context. LOWER IS BETTER. The ad blends into and
        fulfills, rather than fights, the primed goal.

    Second term — pragmatic term:
        Log-probability that `a` is "expected" given the inferred
        goal state, weighted by precision π(c) (high precision =
        posture is highly diagnostic; low precision = posture is
        ambiguous, weight the prior less).

DECOMPOSITION FOR PARTNER-FACING "WHY"

The free-energy decomposition has a clean partner-facing
interpretation: "this creative is shown because (a) it aligns with
the goal the user is currently in (low KL) AND (b) it is a
recognizable instance of that goal completion (high expected log-
likelihood)." This is the literal narrative version of attention-
inversion. The Defensive Reasoning panel (Spine #13) renders this.

CONSTRAINED BY FLUENCY FLOOR (Spine #4)

Per directive Section 4.4 + Section 5: "The free-energy scorer can
NEVER override the Spine #4 fluency floor. Free-energy is a soft
objective; the floor is hard. Free-energy can only choose among
already-fluent candidates." Foundation §7 rule 11 protected
structurally.

DECISION-TIME CONSUMERS (Rule A check)

  - Orchestrator's recommendation policy: action selection is via
    top-two Thompson sampling over softmax(-F), where F is computed
    by this module
  - Spine #6 DecisionTrace records the F decomposition per candidate
  - Spine #13 Defensive Reasoning panel reads the decomposition for
    partner-facing render

Cognitive primitive at the serving path. NOT measurement.

THIS COMMIT SHIPS

    - GoalState enum (12-15 goal states per directive Section 2)
    - GoalDistribution Pydantic model (categorical distribution over
      goal states)
    - kl_divergence_categorical pure-Python KL between two GoalDistributions
    - compute_free_energy: F(a | s, c) computation per the formula
    - FreeEnergyDecomposition Pydantic model (KL + pragmatic +
      precision-weighted total) for DecisionTrace + partner render
    - score_with_free_energy: orchestrator-facing entry point that
      computes F per candidate, applies fluency floor, and emits
      decompositions

THIS COMMIT DOES NOT SHIP (follow-on commits)

    - Generative model that infers q(goal_state | a, s, c) and
      p(goal_state | s, c) from page-content embeddings + user-state
      embeddings — substrate signature is here; offline pipeline
      (Spine #12) trains the model
    - Per-mechanism expected-likelihood calibration — calibration-
      pending; pilot-derived

REFERENCES

    Friston (2010) The free-energy principle: a unified brain theory.
    Da Costa et al. (2020) Active inference on discrete state-spaces.
    Friston et al. (2017) Active Inference: A Process Theory.
    Bargh & Ferguson (2000) Beyond behaviorism: on the automaticity
        of higher mental processes (predictive-coding link).
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)


# =============================================================================
# Goal-state inventory (per directive Section 2 Spine #5: 12-15 states)
# =============================================================================


class GoalState(str, Enum):
    """Inventory of goal states a user can be in at decision time.

    Per directive: "Goal states are mechanism-adjacent but distinct;
    they capture *why* the user is on that page, not what mechanism
    would persuade them."

    Calibration-pending; offline pipeline (Spine #12) refines the
    inventory from observed page-content + user-state patterns.

    LUXY-flavored 13 goal states:
    """

    COMMUTE_READINESS = "commute_readiness"
    EXPENSE_MANAGEMENT = "expense_management"
    COMPARATIVE_RESEARCH = "comparative_research"
    SOCIAL_POSITIONING = "social_positioning"
    TIME_PRESSURE = "time_pressure"
    TRIP_PLANNING = "trip_planning"
    PROFESSIONAL_ENCOUNTER_PREP = "professional_encounter_prep"
    ANXIETY_REDUCTION = "anxiety_reduction"
    STATUS_DISPLAY = "status_display"
    LEISURE_CONSUMPTION = "leisure_consumption"
    INFORMATION_FORAGING = "information_foraging"
    DECISION_DEFERRAL = "decision_deferral"
    OBLIGATION_FULFILLMENT = "obligation_fulfillment"


GOAL_STATES_ORDERED: Tuple[GoalState, ...] = tuple(GoalState)


# =============================================================================
# GoalDistribution Pydantic model
# =============================================================================


class GoalDistribution(BaseModel):
    """Categorical distribution over goal states.

    Used for both:
        - p(goal_state | s, c): prior over goal states given user state
          + page context
        - q(goal_state | a, s, c): variational posterior over goal
          states given the candidate ad + user state + context

    `weights` is in the same order as GOAL_STATES_ORDERED.
    """

    model_config = ConfigDict(extra="forbid")

    weights: List[float]

    @field_validator("weights")
    @classmethod
    def _validate_distribution(cls, v: List[float]) -> List[float]:
        n = len(GOAL_STATES_ORDERED)
        if len(v) != n:
            raise ValueError(
                f"weights must have length {n} (one per GoalState); "
                f"got {len(v)}"
            )
        for w in v:
            if w < 0.0:
                raise ValueError(
                    f"weights must be non-negative; got {w}"
                )
        s = sum(v)
        if abs(s - 1.0) > 1e-3:
            raise ValueError(
                f"weights must sum to ~1.0 (tol 1e-3); got {s}"
            )
        return v

    def goal_to_weight(self) -> Dict[GoalState, float]:
        """Return the distribution as a {GoalState: weight} dict."""
        return {GOAL_STATES_ORDERED[i]: self.weights[i] for i in range(len(self.weights))}

    def argmax_goal(self) -> GoalState:
        """Return the goal state with the highest weight."""
        i = max(range(len(self.weights)), key=lambda j: self.weights[j])
        return GOAL_STATES_ORDERED[i]

    def entropy(self) -> float:
        """Shannon entropy of the distribution (in nats)."""
        h = 0.0
        for w in self.weights:
            if w > 0:
                h -= w * math.log(w)
        return h


def uniform_goal_distribution() -> GoalDistribution:
    """Uniform distribution over goal states (max-entropy prior)."""
    n = len(GOAL_STATES_ORDERED)
    return GoalDistribution(weights=[1.0 / n] * n)


def point_goal_distribution(goal: GoalState) -> GoalDistribution:
    """Point distribution on a single goal state (with epsilon mass on
    others to avoid log(0) in KL).

    Useful for tests and for the "I know exactly what goal you're in"
    case (rare).
    """
    n = len(GOAL_STATES_ORDERED)
    eps = 1e-6
    weights = [eps] * n
    target_idx = GOAL_STATES_ORDERED.index(goal)
    weights[target_idx] = 1.0 - eps * (n - 1)
    # Renormalize for floating-point safety.
    total = sum(weights)
    return GoalDistribution(weights=[w / total for w in weights])


# =============================================================================
# KL divergence between two categorical distributions
# =============================================================================


def kl_divergence_categorical(
    q: GoalDistribution,
    p: GoalDistribution,
    *,
    epsilon: float = 1e-12,
) -> float:
    """Compute KL(q || p) for two categorical distributions.

    KL(q || p) = Σ_i q_i · log(q_i / p_i)

    KL is non-symmetric and non-negative (zero iff q == p).

    For numerical safety, both distributions are clipped at epsilon
    before the log. Mass is renormalized after clipping.
    """
    if len(q.weights) != len(p.weights):
        raise ValueError(
            f"q and p must have same dimensionality; got {len(q.weights)} "
            f"vs {len(p.weights)}"
        )

    q_w = [max(w, epsilon) for w in q.weights]
    p_w = [max(w, epsilon) for w in p.weights]

    # Renormalize.
    q_total = sum(q_w)
    p_total = sum(p_w)
    q_w = [w / q_total for w in q_w]
    p_w = [w / p_total for w in p_w]

    kl = 0.0
    for q_i, p_i in zip(q_w, p_w):
        if q_i > 0:
            kl += q_i * math.log(q_i / p_i)
    return max(0.0, kl)


# =============================================================================
# Free-energy computation
# =============================================================================


@dataclass(frozen=True)
class FreeEnergyDecomposition:
    """Decomposition of F(a | s, c) for partner-facing render.

    Components:
        kl_term: D_KL(q(goal | a, s, c) || p(goal | s, c)) — ambiguity
            / mismatch. Lower is better (ad blends into the primed goal).
        pragmatic_term: π(c) · log p(observation = a | goal_state) —
            expected log-likelihood that a is recognized as a goal-
            completion instance, precision-weighted.
        free_energy: F = kl_term − pragmatic_term

    The Defensive Reasoning panel (Spine #13) reads this for the
    contribution-decomposition view. Per directive: "this creative is
    shown because (a) it aligns with the goal the user is currently
    in (low KL) AND (b) it is a recognizable instance of that goal
    completion (high expected log-likelihood)."
    """

    kl_term: float
    pragmatic_term: float
    free_energy: float
    posture_precision: float
    posterior_argmax_goal: GoalState
    prior_argmax_goal: GoalState


def compute_free_energy(
    *,
    posterior_q: GoalDistribution,
    prior_p: GoalDistribution,
    log_p_observation_given_goal: Dict[GoalState, float],
    posture_precision: float = 1.0,
) -> FreeEnergyDecomposition:
    """Compute F(a | s, c) per directive Spine #5 formula.

    Args:
        posterior_q: q(goal_state | a, s, c) — variational posterior
            over goal states given the candidate ad + user state +
            context
        prior_p: p(goal_state | s, c) — prior over goal states given
            user state + context (from offline-pipeline goal-state
            inference)
        log_p_observation_given_goal: log p(observation = a | goal)
            for each goal state — measures how recognizable the
            candidate IS as a goal-completion instance per goal state
        posture_precision: π(c) — high when posture is highly diagnostic;
            low (toward 0) when posture is ambiguous

    Returns FreeEnergyDecomposition. F = KL(q || p) - π · E_q[log p(obs|goal)]

    Lower F = candidate fits better with primed goal AND is recognizable
    as goal completion. The recommendation policy selects to MINIMIZE F
    (subject to the fluency floor — Spine #5 cannot override Spine #4).
    """
    if not 0.0 <= posture_precision <= 10.0:
        # Wide bounds; values >> 1 amplify the pragmatic term and
        # are valid in highly-diagnostic contexts.
        raise ValueError(
            f"posture_precision must be non-negative and reasonable; "
            f"got {posture_precision}"
        )

    # KL term
    kl = kl_divergence_categorical(posterior_q, prior_p)

    # Pragmatic term: π · E_q[log p(obs | goal)] = π · Σ q_i · log_p_i
    # We MAXIMIZE the pragmatic, hence subtract from F.
    expected_log_p = 0.0
    for i, goal in enumerate(GOAL_STATES_ORDERED):
        log_p = log_p_observation_given_goal.get(goal, math.log(1e-6))
        expected_log_p += posterior_q.weights[i] * log_p
    pragmatic = posture_precision * expected_log_p

    free_energy = kl - pragmatic

    return FreeEnergyDecomposition(
        kl_term=kl,
        pragmatic_term=pragmatic,
        free_energy=free_energy,
        posture_precision=posture_precision,
        posterior_argmax_goal=posterior_q.argmax_goal(),
        prior_argmax_goal=prior_p.argmax_goal(),
    )


# =============================================================================
# Action-selection helpers (softmax over -F, eligible-set-aware)
# =============================================================================


def softmax_over_negative_free_energy(
    candidate_free_energies: Dict[str, float],
    *,
    temperature: float = 1.0,
) -> Dict[str, float]:
    """Convert candidate free energies to a softmax distribution over
    the candidates.

    Per directive Section 2 Spine #5: "Action selection is performed
    via top-two Thompson sampling over softmax(-F) rather than raw
    posterior reward."

    Args:
        candidate_free_energies: dict of mechanism → F value
        temperature: softmax temperature; lower → sharper, higher →
            more exploration. Per directive: "tied to the per-user
            posterior precision: more uncertain users get higher
            temperature."

    Returns mechanism → probability dict (sums to 1).
    """
    if not candidate_free_energies:
        return {}
    if temperature <= 0.0:
        raise ValueError(f"temperature must be positive; got {temperature}")

    # Negate and divide by temperature.
    log_unnorm = {
        m: -f / temperature for m, f in candidate_free_energies.items()
    }
    # Numerical stability: subtract max.
    max_log = max(log_unnorm.values())
    exp_unnorm = {m: math.exp(v - max_log) for m, v in log_unnorm.items()}
    total = sum(exp_unnorm.values())
    return {m: v / total for m, v in exp_unnorm.items()}


__all__ = [
    "FreeEnergyDecomposition",
    "GoalDistribution",
    "GoalState",
    "GOAL_STATES_ORDERED",
    "compute_free_energy",
    "kl_divergence_categorical",
    "point_goal_distribution",
    "softmax_over_negative_free_energy",
    "uniform_goal_distribution",
]
