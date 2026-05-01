# =============================================================================
# Spine #5 — Offline B-vs-C evaluator (Slice 19)
# Location: adam/intelligence/dual_eval_evaluator.py
# =============================================================================
"""Empirical comparison of LogisticGoalStateModel (B) and
HierarchicalGoalStateModel (C) on held-out goal-state labels.

Closes the operational loop on Chris's call (2026-05-01): "We may
want B & C as options. In other words we may want both directions
and then with both we can consider which is producing the stronger
answers. Only then will we know."

Slice 17d wired both models in parallel — primary modulates
mechanism_scores, shadow logs predictions in DecisionTrace. Slice 18
ships labeled training data via Claude API. THIS slice scores both
models' predictions on the labeled set and identifies which is
winning per-goal-state and overall.

WHY THIS EXISTS — DECISION-TIME PATH

  Slice 18 → :GoalStateLabel nodes (ground truth)
      ↓
  load_labels_from_neo4j → held-out labeled set
      ↓
  THIS SLICE: evaluate_on_labels for each model
      ↓ Brier, log-loss, top-K accuracy + per-goal breakdown
  EvaluationReport with winning model + margin
      ↓ recommend_primary(report)
  Operational decision: which model goes in
  register_dual_eval_context(primary=winner, shadow=other)

WHEN TO RUN

After every label-generation cycle (Slice 18) AND every model retrain
(Slice 17b/c train()). Pilot data accumulates → comparison gets more
reliable → primary swaps to whichever wins on held-out.

METRICS

For multi-label labels with multinomial-shaped predictions (both B
and C output normalized distributions over the 14-goal inventory),
the canonical scoring metrics are:

  - Brier score: BS = (1/n) Σ_i Σ_g (p_g - y_g)²
    Lower is better. y_g is the ground-truth probability for goal g
    (we treat multi-label labels as uniform mass across active goals).
  - Log-loss / cross-entropy: -(1/n) Σ_i Σ_g y_g · log(p_g)
    Lower is better. Penalizes confident wrong predictions more
    than Brier.
  - Top-1 accuracy: fraction of labels where the model's argmax
    goal is in the active set.
  - Top-3 accuracy: fraction where any of the top-3 goals is in
    the active set.

Per-goal breakdown lets you see "C wins on commute_readiness but
B wins on comparative_research" — useful when one model captures
specific patterns better.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: standard ML scoring metrics — Brier 1950 (proper
    scoring rule); cross-entropy / log-loss canonical; top-K
    accuracy as exhibited in IR / classification eval.
    Multi-label-as-uniform-multinomial treatment is the apples-to-
    apples comparison method when both models output multinomials.

(b) Tests pin: Brier ≥ 0; Brier = 0 when predicted == truth;
    log-loss ≥ 0; log-loss → ∞ as predicted → 0 on a true positive;
    top-1 accuracy in [0, 1]; per-goal breakdown sums to total
    correctly; winning model identified when one strictly better;
    tie-handling when metrics within tolerance; empty labels →
    metrics not computable (returns None / zero).

(c) calibration_pending=False — metric formulas are canonical.
    The TIE_TOLERANCE default 0.01 is conservative; LUXY pilot
    data + ops review calibrate.

(d) Honest tags — what is NOT in this slice (named successors):

    * DecisionTrace-side comparison from production traffic. The
      gs_primary.* / gs_shadow.* keys logged in Slice 17d carry
      both models' posteriors per real decision; with ground-truth
      labels at production scale, you could score on real traffic
      rather than only on the held-out set. Requires page_url on
      the DecisionTrace (not currently a top-level field) — sibling
      slice.
    * Confidence-aware scoring. v0.1 weights every label equally;
      a sibling could weight by GoalStateLabel.confidence so
      Claude-uncertain labels contribute less.
    * Calibration plots / reliability diagrams. Useful for
      diagnosing systematic over/under-confidence; sibling
      visualization slice.
    * Per-archetype / per-cohort breakdown — sibling once cohort
      discovery (Spine #7) unblocks Loop B.
    * Active-learning scorer that flags labels where B and C
      disagree most strongly — feeds back into Slice 18 to
      preferentially label those page types. Sibling.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from adam.intelligence.free_energy import GoalStatePosterior
from adam.intelligence.goal_state_inventory import list_goal_states
from adam.intelligence.goal_state_label_generator import GoalStateLabel

logger = logging.getLogger(__name__)


# Numerical floor for log() — prevents log(0) on degenerate
# predictions. Matches the discipline elsewhere in free_energy.py.
_PROB_FLOOR: float = 1e-12

# A14 SPINE_5_EVAL_TIE_TOLERANCE_PILOT_PENDING
TIE_TOLERANCE: float = 0.01
"""Two metric values within this absolute tolerance count as a tie.
Conservative pre-pilot; pilot data + ops review calibrate."""


# =============================================================================
# Per-model metrics
# =============================================================================


class EvaluationMetrics(BaseModel):
    """Metrics for one model across the labeled evaluation set.

    All metrics are computed against the multi-label ground truth,
    with the truth treated as a multinomial (uniform mass across
    active goals). Lower Brier / log-loss = better. Higher accuracy
    = better.
    """

    model_config = ConfigDict(extra="forbid")

    model_name: str
    n_evaluated: int = Field(ge=0)
    brier_score: float = Field(ge=0.0)
    """Mean Brier score across labels. 0 = perfect; theoretical
    maximum is 2 for a misalign-everything multinomial."""
    log_loss: float = Field(ge=0.0)
    """Mean log-loss across labels. 0 = perfect; +∞ at degenerate
    confident-wrong predictions (numerically clamped)."""
    top_1_accuracy: float = Field(ge=0.0, le=1.0)
    """Fraction of labels where the model's argmax goal is in the
    active set."""
    top_3_accuracy: float = Field(ge=0.0, le=1.0)
    """Fraction of labels where any of the top-3 goals is in the
    active set."""
    per_goal_brier: Dict[str, float] = Field(default_factory=dict)
    """Per-goal mean Brier. Each entry is the per-goal contribution
    averaged across labels — sums (across goals) and the total
    Brier × n match within numerical tolerance."""
    per_goal_log_loss: Dict[str, float] = Field(default_factory=dict)


# =============================================================================
# Comparative report
# =============================================================================


class EvaluationReport(BaseModel):
    """Side-by-side comparison of primary vs shadow on the same
    labeled set."""

    model_config = ConfigDict(extra="forbid")

    primary_metrics: EvaluationMetrics
    shadow_metrics: Optional[EvaluationMetrics] = None
    n_labels: int = Field(ge=0)
    winning_model_name: Optional[str] = None
    """Name of the model with lower Brier (lower-is-better metric).
    None when shadow is None OR the two models tie within
    TIE_TOLERANCE."""
    winning_brier_margin: Optional[float] = None
    """primary.brier - shadow.brier (signed). Negative → primary
    won. None when shadow is None."""
    per_goal_winners: Dict[str, str] = Field(default_factory=dict)
    """Goal-state-id → winning model name. Per-goal, by Brier."""


# =============================================================================
# Math primitives
# =============================================================================


def _label_to_truth_distribution(label: GoalStateLabel) -> Dict[str, float]:
    """Convert multi-label active set to a multinomial truth.

    Uniform mass across active goals. Empty active set → uniform
    over all 14 goals (treated as "no signal in any direction").
    """
    all_ids = [g.id for g in list_goal_states()]
    n_goals = len(all_ids)

    if not label.active_goal_state_ids:
        # No active goals — uniform truth (no signal)
        return {gid: 1.0 / n_goals for gid in all_ids}

    active_set = set(label.active_goal_state_ids)
    n_active = len(active_set)
    return {
        gid: (1.0 / n_active if gid in active_set else 0.0)
        for gid in all_ids
    }


def compute_brier_score(
    predicted: GoalStatePosterior,
    truth: Dict[str, float],
) -> Tuple[float, Dict[str, float]]:
    """Per-label Brier score: Σ_g (p_g - y_g)².

    Returns (total_brier, per_goal_brier).
    """
    all_ids = [g.id for g in list_goal_states()]
    per_goal: Dict[str, float] = {}
    total = 0.0
    for gid in all_ids:
        p = float(predicted.probabilities.get(gid, 0.0))
        y = float(truth.get(gid, 0.0))
        sq_err = (p - y) ** 2
        per_goal[gid] = sq_err
        total += sq_err
    return total, per_goal


def compute_log_loss(
    predicted: GoalStatePosterior,
    truth: Dict[str, float],
    *,
    epsilon: float = _PROB_FLOOR,
) -> Tuple[float, Dict[str, float]]:
    """Per-label log-loss: -Σ_g y_g · log(p_g).

    epsilon floors p so log doesn't blow up on zero predictions.
    Goals with y_g = 0 contribute zero (no penalty).
    Returns (total_log_loss, per_goal_log_loss).
    """
    all_ids = [g.id for g in list_goal_states()]
    per_goal: Dict[str, float] = {}
    total = 0.0
    for gid in all_ids:
        p = float(predicted.probabilities.get(gid, 0.0))
        y = float(truth.get(gid, 0.0))
        if y <= 0.0:
            per_goal[gid] = 0.0
            continue
        p_safe = max(p, epsilon)
        contribution = -y * math.log(p_safe)
        per_goal[gid] = contribution
        total += contribution
    return total, per_goal


def compute_top_k_accuracy(
    predicted: GoalStatePosterior,
    truth_active_set: set,
    k: int,
) -> bool:
    """Did any of the top-K predicted goals appear in the truth's
    active set?

    Returns True iff at least one of the K highest-probability goals
    is in the active set. Empty active set → False (no goals to hit).
    """
    if not truth_active_set:
        return False
    top_k = sorted(
        predicted.probabilities.items(),
        key=lambda kv: kv[1], reverse=True,
    )[:k]
    return any(gid in truth_active_set for gid, _ in top_k)


# =============================================================================
# Per-model evaluation
# =============================================================================


def evaluate_on_labels(
    labels: List[GoalStateLabel],
    model: Any,
) -> Optional[EvaluationMetrics]:
    """Score a model on the labeled set.

    Args:
        labels: list of GoalStateLabel from Slice 18.
        model: implements GoalStatePriorModel protocol — predict_p(
            page_features, user_state) → GoalStatePosterior.

    Returns None when labels is empty. Otherwise returns
    EvaluationMetrics with Brier / log-loss / top-K accuracy +
    per-goal breakdown.

    Soft-fail per-label: if a single predict_p raises, that label
    is skipped (logged at WARNING) and the rest of the set is still
    scored. n_evaluated reflects successfully-scored count.
    """
    if not labels:
        return None

    n_total = 0
    sum_brier = 0.0
    sum_log_loss = 0.0
    n_top_1 = 0
    n_top_3 = 0
    sum_per_goal_brier: Dict[str, float] = {
        g.id: 0.0 for g in list_goal_states()
    }
    sum_per_goal_log_loss: Dict[str, float] = {
        g.id: 0.0 for g in list_goal_states()
    }

    for label in labels:
        try:
            predicted = model.predict_p(
                page_features=label.page_features,
            )
        except Exception as exc:
            logger.warning(
                "evaluate_on_labels: predict_p failed for label_id=%s: %s",
                label.label_id, exc,
            )
            continue

        truth = _label_to_truth_distribution(label)

        brier_total, brier_per_goal = compute_brier_score(predicted, truth)
        ll_total, ll_per_goal = compute_log_loss(predicted, truth)

        sum_brier += brier_total
        sum_log_loss += ll_total
        for gid, v in brier_per_goal.items():
            sum_per_goal_brier[gid] = sum_per_goal_brier.get(gid, 0.0) + v
        for gid, v in ll_per_goal.items():
            sum_per_goal_log_loss[gid] = sum_per_goal_log_loss.get(gid, 0.0) + v

        truth_active_set = set(label.active_goal_state_ids)
        if compute_top_k_accuracy(predicted, truth_active_set, k=1):
            n_top_1 += 1
        if compute_top_k_accuracy(predicted, truth_active_set, k=3):
            n_top_3 += 1

        n_total += 1

    if n_total == 0:
        # Every prediction failed — return None to signal "no eval"
        return None

    model_name = getattr(model, "model_name", "unknown")
    return EvaluationMetrics(
        model_name=str(model_name),
        n_evaluated=n_total,
        brier_score=sum_brier / n_total,
        log_loss=sum_log_loss / n_total,
        top_1_accuracy=n_top_1 / n_total,
        top_3_accuracy=n_top_3 / n_total,
        per_goal_brier={
            gid: sum_per_goal_brier[gid] / n_total
            for gid in sum_per_goal_brier
        },
        per_goal_log_loss={
            gid: sum_per_goal_log_loss[gid] / n_total
            for gid in sum_per_goal_log_loss
        },
    )


# =============================================================================
# Comparative evaluation — B vs C side-by-side
# =============================================================================


def compare_models_on_labels(
    labels: List[GoalStateLabel],
    primary: Any,
    shadow: Optional[Any] = None,
    *,
    tie_tolerance: float = TIE_TOLERANCE,
) -> Optional[EvaluationReport]:
    """Score primary and (optional) shadow on the same labels.

    The report includes:
      - per-model EvaluationMetrics
      - winning_model_name (None on tie within tolerance)
      - winning_brier_margin (signed: negative = primary won)
      - per_goal_winners dict

    Returns None when labels is empty. Returns a single-model
    report (shadow_metrics=None, no winner) when shadow is None.
    """
    if not labels:
        return None

    primary_metrics = evaluate_on_labels(labels, primary)
    if primary_metrics is None:
        return None

    if shadow is None:
        return EvaluationReport(
            primary_metrics=primary_metrics,
            shadow_metrics=None,
            n_labels=len(labels),
            winning_model_name=None,
            winning_brier_margin=None,
            per_goal_winners={},
        )

    shadow_metrics = evaluate_on_labels(labels, shadow)
    if shadow_metrics is None:
        return EvaluationReport(
            primary_metrics=primary_metrics,
            shadow_metrics=None,
            n_labels=len(labels),
        )

    # Determine winner (lower Brier is better)
    brier_margin = primary_metrics.brier_score - shadow_metrics.brier_score
    winning_model_name: Optional[str] = None
    if abs(brier_margin) <= tie_tolerance:
        winning_model_name = None  # tie
    elif brier_margin < 0:
        winning_model_name = primary_metrics.model_name
    else:
        winning_model_name = shadow_metrics.model_name

    # Per-goal winner — by per-goal Brier
    per_goal_winners: Dict[str, str] = {}
    for gid in list_goal_states():
        p_brier = primary_metrics.per_goal_brier.get(gid.id, 0.0)
        s_brier = shadow_metrics.per_goal_brier.get(gid.id, 0.0)
        diff = p_brier - s_brier
        if abs(diff) <= tie_tolerance:
            per_goal_winners[gid.id] = "tie"
        elif diff < 0:
            per_goal_winners[gid.id] = primary_metrics.model_name
        else:
            per_goal_winners[gid.id] = shadow_metrics.model_name

    return EvaluationReport(
        primary_metrics=primary_metrics,
        shadow_metrics=shadow_metrics,
        n_labels=len(labels),
        winning_model_name=winning_model_name,
        winning_brier_margin=brier_margin,
        per_goal_winners=per_goal_winners,
    )


def recommend_primary(report: EvaluationReport) -> Optional[str]:
    """Based on the comparison report, return the model name to set
    as primary in DualEvalContext, OR None if a tie / no shadow.

    Convenience for the operational handoff:

        labels = await load_labels_from_neo4j(driver)
        report = compare_models_on_labels(labels, b, c)
        winner = recommend_primary(report)
        if winner == b.model_name:
            register_dual_eval_context(primary_model=b, shadow_model=c)
        elif winner == c.model_name:
            register_dual_eval_context(primary_model=c, shadow_model=b)
        # else: tie or no shadow — keep current configuration
    """
    return report.winning_model_name
