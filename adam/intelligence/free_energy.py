# =============================================================================
# Spine #5 — Active-Inference Free-Energy substrate
# Location: adam/intelligence/free_energy.py
# =============================================================================
"""Free-energy decomposition over the LUXY goal-state inventory.

Closes the keystone substrate of directive Spine #5 (lines 199-222):

    F(a | s, c) = D_KL(q(goal | a, s, c) || p(goal | s, c))
                  − π(c) · log p(observation = a | goal_state)

Where:
  - p(goal | s, c): prior over the 14 goal states given user state s
    and page context c (model-dependent; see GoalStatePriorModel).
  - q(goal | a, s, c): posterior shifted by candidate action a — the
    closed-form Bayesian update with the goal-conditional likelihood
    p(obs = a | goal).
  - D_KL: ambiguity / mismatch term; lower = candidate better aligns
    with primed goals.
  - π(c): page posture confidence; high = posture is highly diagnostic.
  - log p(obs = a | goal_state): pragmatic term; the goal's
    mechanism-prior on the candidate's mechanism is the closed-form
    likelihood (goal_state.mechanism_priors[mech]).

The decision-time consumer is the trilateral cascade's score
modulation per directive line 521:

    final_score(a) = posterior_score(a) − λ_F · F(a | s, c)
                   + λ_E · epistemic(a)

Action selection via top-two Thompson sampling on final_score.
The KL-and-pragmatic decomposition is also rendered in the
Defensive Reasoning surface (Spine #13 Layer 3 — Slice 17d wires).

WHY THIS EXISTS — DECISION-TIME CONSUMER

Per directive line 203: "without it, attention-inversion is a
marketing claim. With it, attention-inversion is the optimization
target."

Slice 8 (e48679a) shipped the SOFT trilateral promotion (posture ×
mechanism modulation in the cascade). Slice 17a ships the
attention-inversion math itself: the free-energy scorer that
penalizes goal-misaligned candidates BEFORE the bandit gets to
exploit them. Together with the HARD fluency floor (Slice 2's
structural epistemic-bonus gate), this is the three-layer
attention-inversion architecture:

    SOFT modulation: ±10% multiplicative on mechanism_scores (Slice 8)
    SOFT cost:       λ_F · F(a) subtracted from score (THIS SLICE)
    HARD gate:       LOW posture × mechanism → epistemic_bonus = 0
                     (Slice 2's structural defense)

ARCHITECTURE — POOLED WITH B AND C

The GoalStatePriorModel Protocol decouples the free-energy math
from the prior-model implementation:

    GoalStatePriorModel.predict_p(s, c) → GoalStatePosterior
    GoalStatePriorModel.predict_q(p, a) → GoalStatePosterior

  - LogisticGoalStateModel (Slice 17b, Option B)
  - HierarchicalGoalStateModel (Slice 17c, Option C)
  - PassthroughGoalStateModel (this slice, v0.1 fallback)

The passthrough model returns a posture-and-keyword heuristic prior;
it lets the substrate ship + the cascade integrate without depending
on Slice 17b/c training labels. Both Slice 17b and 17c plug in via
the same Protocol so the cascade-side wiring (Slice 17d) is
model-agnostic.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Spine #5 lines 199-222; Foundation §7
    rule 11 (fitness function IS ethics — soft cost composes with
    hard gate); active inference (Friston FEP; Da Costa et al. 2020).
    Closed-form Bayesian update under the goal-conditional
    likelihood: q(g | a) ∝ p(g) · L(a | g) is canonical.

(b) Tests pin: KL(q || p) ≥ 0; KL = 0 when q == p; closed-form
    posterior update q ∝ p · L; pragmatic = π · log E[L]
    (likelihood marginalized over prior); F() composes correctly;
    PassthroughGoalStateModel returns posterior-shaped uniform when
    no signal; numerical guards (epsilon floor on probabilities to
    prevent log(0)).

(c) calibration_pending=True. λ_F (free-energy weight) and
    epsilon_floor are conservative pre-pilot defaults. A14 flag:
    SPINE_5_FREE_ENERGY_WEIGHT_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * LogisticGoalStateModel (Slice 17b Option B).
    * HierarchicalGoalStateModel (Slice 17c Option C).
    * Cascade integration that calls compute_free_energy on every
      candidate and modulates mechanism_scores (Slice 17d).
    * DecisionTrace logging of both B + C posteriors for empirical
      comparison (Slice 17d).
    * Claude API label generator producing
      (page_features, active_goal_states) tuples for B and C
      training (Slice 18 / directive Section 6.2).
    * Offline B-vs-C evaluator on held-out labels (Slice 19).
    * Primary-metaphor decomposition in the F-rendering one-liner
      (carried from Spine #13 honest tag — Phase 6 line 1059).
    * Goal-state inference from page+user embeddings (the
      "generative model" of directive line 216) — the
      PassthroughGoalStateModel here is heuristic-Bayesian, not
      generative-from-embeddings; that's Slice 17b/c territory.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from adam.intelligence.goal_state_inventory import (
    GoalState,
    list_goal_states,
)

logger = logging.getLogger(__name__)


# =============================================================================
# A14 calibration-pending defaults
# =============================================================================

# A14 SPINE_5_FREE_ENERGY_WEIGHT_PILOT_PENDING
DEFAULT_FREE_ENERGY_WEIGHT: float = 0.10
"""λ_F — multiplicative weight on F(a) in the cascade's score
modulation per directive line 521. Conservative pre-pilot; LUXY
data + the offline goal-state inference will calibrate."""

# Numerical floor on probabilities — prevents log(0) and division-by-zero.
# Matches MIN_PRECISION discipline elsewhere in the platform.
_PROB_FLOOR: float = 1e-12


# =============================================================================
# GoalStatePosterior schema
# =============================================================================


class GoalStatePosterior(BaseModel):
    """Distribution over the LUXY goal-state inventory.

    The Pydantic shape every goal-state model produces. Both B
    (Slice 17b LogisticGoalStateModel) and C (Slice 17c
    HierarchicalGoalStateModel) emit this exact shape so the
    cascade-side consumer is invariant to model choice.

    ``probabilities`` maps each goal_state_id to its probability.
    Sums to 1.0 ± tolerance. A "multi-label" interpretation —
    where the same page can activate multiple goals — emits as
    a multinomial posterior here too: each probability is the
    marginal posterior probability of that goal being active.
    """

    model_config = ConfigDict(extra="forbid")

    probabilities: Dict[str, float]
    """Maps goal_state_id → probability in [0, 1]. Marginal under
    the posterior; sums to 1.0 ± tolerance for the standard
    multinomial interpretation."""

    model_name: str
    """Identifier of the model that produced this posterior. Used
    by the dual-eval wiring (Slice 17d) to track which model
    each posterior came from in the DecisionTrace."""

    @field_validator("probabilities")
    @classmethod
    def _probabilities_in_unit_range(
        cls, v: Dict[str, float],
    ) -> Dict[str, float]:
        for key, value in v.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(
                    f"probability for {key!r} must be in [0, 1]; got {value}"
                )
        return v


# =============================================================================
# GoalStatePriorModel Protocol
# =============================================================================


class GoalStatePriorModel(Protocol):
    """Common interface implemented by Options A, B, and C.

    The free-energy scorer + cascade integration consume this
    interface — they don't care whether the prior comes from the
    heuristic passthrough, sklearn logistic regression, or a
    NumPyro SVI hierarchical Bayesian fit.
    """

    @property
    def model_name(self) -> str:
        """Identifier — used to tag posteriors in DecisionTrace."""

    def predict_p(
        self,
        page_features: Dict[str, Any],
        user_state: Optional[Dict[str, float]] = None,
    ) -> GoalStatePosterior:
        """Produce p(goal | s, c) given page context + user state.

        page_features carries the page-side inputs (posture, edge
        dimensions, keywords / page_text). user_state is optional
        (multi-page priors that don't condition on user pass None).
        """

    def predict_q(
        self,
        p: GoalStatePosterior,
        candidate_mechanism: str,
    ) -> GoalStatePosterior:
        """Produce q(goal | a, s, c) — Bayesian update of p under
        the goal-conditional likelihood for candidate action a's
        mechanism. Closed-form: q(g) ∝ p(g) · L(a | g) where
        L(a | g) = goal_state(g).mechanism_priors[mech].
        """


# =============================================================================
# Pure-function math primitives
# =============================================================================


def compute_kl_divergence(
    q: GoalStatePosterior,
    p: GoalStatePosterior,
    *,
    epsilon: float = _PROB_FLOOR,
) -> float:
    """KL(q || p) — non-negative, zero iff q = p.

    Sums over the union of goal_state_ids. Missing keys in either
    distribution → that goal contributes zero (q[g] = 0 → 0 · log
    anything = 0; q[g] > 0, p[g] missing → uses epsilon floor).
    """
    keys = set(q.probabilities.keys()) | set(p.probabilities.keys())
    kl = 0.0
    for k in keys:
        q_prob = max(q.probabilities.get(k, 0.0), 0.0)
        p_prob = max(p.probabilities.get(k, 0.0), 0.0)
        if q_prob <= 0.0:
            continue  # 0 · log(...) = 0 by convention
        # Floor p to prevent log(0) when q[g] > 0 and p[g] = 0.
        p_eff = max(p_prob, epsilon)
        kl += q_prob * (math.log(q_prob) - math.log(p_eff))
    # Numerical floor — small negative values from float arithmetic.
    return max(0.0, kl)


def compute_pragmatic_term(
    p: GoalStatePosterior,
    candidate_mechanism: str,
    *,
    posture_confidence: float = 1.0,
    epsilon: float = _PROB_FLOOR,
) -> float:
    """π(c) · log p(observation = a | goal-state-distribution).

    The likelihood marginalizes the candidate's
    goal-conditional probability over the goal-state distribution:

        L(a | p) = Σ_g p(g) · goal_state(g).mechanism_priors[mech]

    Returns π(c) · log L(a | p). Higher = candidate is more
    "expected" given the inferred goals. Numerically floored to
    prevent log(0) on degenerate distributions.

    Args:
        p: prior or posterior over goal states.
        candidate_mechanism: mechanism name of candidate action.
        posture_confidence: π(c) in [0, 1]. Scales the term down
            when posture is ambiguous.
        epsilon: numerical floor on the marginalized likelihood.
    """
    if not 0.0 <= posture_confidence <= 1.0:
        raise ValueError(
            f"posture_confidence must be in [0, 1]; got {posture_confidence}"
        )

    # Marginalize the goal-conditional likelihood over p.
    likelihood = 0.0
    for g in list_goal_states():
        prob = p.probabilities.get(g.id, 0.0)
        if prob <= 0.0:
            continue
        l_g = g.mechanism_priors.get(candidate_mechanism, 0.0)
        likelihood += prob * l_g

    likelihood = max(likelihood, epsilon)
    return float(posture_confidence * math.log(likelihood))


def compute_free_energy(
    p: GoalStatePosterior,
    candidate_mechanism: str,
    prior_model: GoalStatePriorModel,
    *,
    posture_confidence: float = 1.0,
) -> float:
    """F(a | s, c) — the directive's free-energy expression.

        F = D_KL(q || p) − π(c) · log p(obs = a | goal_state)

    Lower F = candidate aligns better with primed goals AND is
    more recognizable as a goal-fulfilling instance. The cascade
    subtracts λ_F · F(a) from the score per directive line 521.
    """
    q = prior_model.predict_q(p, candidate_mechanism)
    kl = compute_kl_divergence(q, p)
    pragmatic = compute_pragmatic_term(
        p, candidate_mechanism, posture_confidence=posture_confidence,
    )
    return kl - pragmatic


def closed_form_q_from_p(
    p: GoalStatePosterior,
    candidate_mechanism: str,
    *,
    model_name: str = "closed_form_bayes",
    epsilon: float = _PROB_FLOOR,
) -> GoalStatePosterior:
    """Closed-form Bayesian update — q(g) ∝ p(g) · L(a | g).

    Helper that any GoalStatePriorModel implementation can call as
    its `predict_q` if the model uses the canonical Bayesian update.
    Both LogisticGoalStateModel and HierarchicalGoalStateModel use
    this for their q-prediction (the goal-conditional likelihood is
    the inventory's mechanism_priors regardless of the prior model).
    """
    unnormalized: Dict[str, float] = {}
    for g in list_goal_states():
        prob_g = p.probabilities.get(g.id, 0.0)
        if prob_g <= 0.0:
            continue
        l_g = g.mechanism_priors.get(candidate_mechanism, 0.0)
        unnormalized[g.id] = prob_g * l_g

    total = sum(unnormalized.values())
    if total <= epsilon:
        # Likelihood is zero across all goals — q can't be formed
        # from the canonical update. Fallback: return p unchanged.
        # Tagged honestly via the model_name.
        return GoalStatePosterior(
            probabilities=dict(p.probabilities),
            model_name=f"{model_name}:degenerate_fallback",
        )

    normalized = {k: v / total for k, v in unnormalized.items()}
    return GoalStatePosterior(
        probabilities=normalized,
        model_name=model_name,
    )


# =============================================================================
# PassthroughGoalStateModel — heuristic Bayesian v0.1
# =============================================================================


class PassthroughGoalStateModel:
    """Heuristic prior model — uses the inventory's posture +
    mechanism priors directly to compute p(goal | c). Used as the
    cascade-side default until LogisticGoalStateModel (Slice 17b)
    or HierarchicalGoalStateModel (Slice 17c) trains.

    This is Option A from the Spine #5 architecture analysis:
    closed-form, zero training data, ships immediately. Not as
    good as B/C once labels arrive, but lets the cascade
    integration (Slice 17d) ship today.
    """

    @property
    def model_name(self) -> str:
        return "passthrough_heuristic_v1"

    def predict_p(
        self,
        page_features: Dict[str, Any],
        user_state: Optional[Dict[str, float]] = None,
    ) -> GoalStatePosterior:
        """p(goal | c) ∝ goal.posture_compatibility[posture] ·
        keyword_overlap_score(page_text, goal.keywords).

        ``page_features`` keys consumed:
          - posture_class: str — POSTURE_BLEND / VIGILANCE / NEUTRAL
          - posture_confidence: float in [0, 1]
          - page_keywords: List[str] (optional) — extracted page
            keywords to score against goal.keywords

        When posture is unknown / page has no keywords, the prior
        falls back to uniform over the 14 goals.
        """
        posture_class = page_features.get("posture_class") or "neutral"
        page_keywords_raw = page_features.get("page_keywords", []) or []
        page_keywords = {str(k).lower() for k in page_keywords_raw}

        unnormalized: Dict[str, float] = {}
        for g in list_goal_states():
            posture_prior = g.posture_compatibility.get(posture_class, 0.5)
            # Keyword overlap: count of goal keywords matching page keywords.
            if page_keywords:
                goal_kw = {kw.lower() for kw in g.keywords}
                overlap = len(page_keywords & goal_kw)
                # Normalize: max attainable is goal.keywords count;
                # add 1 in numerator and denominator so 0-overlap
                # doesn't zero out the goal entirely.
                kw_score = (overlap + 1.0) / (max(len(goal_kw), 1) + 1.0)
            else:
                kw_score = 1.0  # no keyword signal — neutral
            unnormalized[g.id] = posture_prior * kw_score

        total = sum(unnormalized.values())
        if total <= _PROB_FLOOR:
            # Degenerate — fall back to uniform.
            n = len(unnormalized) or 1
            normalized = {k: 1.0 / n for k in unnormalized.keys()}
        else:
            normalized = {k: v / total for k, v in unnormalized.items()}

        return GoalStatePosterior(
            probabilities=normalized,
            model_name=self.model_name,
        )

    def predict_q(
        self,
        p: GoalStatePosterior,
        candidate_mechanism: str,
    ) -> GoalStatePosterior:
        """Closed-form Bayesian update — same as B and C use."""
        return closed_form_q_from_p(
            p, candidate_mechanism, model_name=self.model_name,
        )


# =============================================================================
# Free-energy result envelope (for cascade integration)
# =============================================================================


class FreeEnergyDecomposition(BaseModel):
    """Per-candidate free-energy result with KL/pragmatic split.

    The decomposition is rendered in the Defensive Reasoning Layer 3
    chain-of-reasoning bar chart (Spine #13 line 857). Both B and C
    posteriors get logged in DecisionTrace via Slice 17d so the
    offline evaluator (Slice 19) compares them on the same decisions.
    """

    model_config = ConfigDict(extra="forbid")

    candidate_mechanism: str
    free_energy: float
    kl_divergence: float
    pragmatic_term: float
    posture_confidence: float
    p_posterior_model_name: str
    """Which model produced p(goal | s, c) — passthrough_heuristic_v1
    / logistic_v1 / hierarchical_bayes_v1. Distinguishes which
    model's posterior the trace logged."""


def decompose_free_energy(
    p: GoalStatePosterior,
    candidate_mechanism: str,
    prior_model: GoalStatePriorModel,
    *,
    posture_confidence: float = 1.0,
) -> FreeEnergyDecomposition:
    """Compute F + the KL/pragmatic decomposition. Used by Slice
    17d's cascade wiring."""
    q = prior_model.predict_q(p, candidate_mechanism)
    kl = compute_kl_divergence(q, p)
    pragmatic = compute_pragmatic_term(
        p, candidate_mechanism, posture_confidence=posture_confidence,
    )
    return FreeEnergyDecomposition(
        candidate_mechanism=candidate_mechanism,
        free_energy=kl - pragmatic,
        kl_divergence=kl,
        pragmatic_term=pragmatic,
        posture_confidence=posture_confidence,
        p_posterior_model_name=p.model_name,
    )
