# =============================================================================
# Spine #5 — Dual-eval wiring (B + C parallel)
# Location: adam/intelligence/free_energy_dual_eval.py
# =============================================================================
"""Cascade integration for the free-energy scorer with B+C dual-eval.

Slice 17d — wires the Slice 17a/b/c substrate into the cascade's
score-modulation chain and logs BOTH primary (used for scoring) and
shadow (logged for offline comparison) posteriors in DecisionTrace.

WHY BOTH MODELS

Per Chris's call (2026-05-01): "We may want B & C as options. In other
words we may want both directions and then with both we can consider
which is producing the stronger answers. Only then will we know."

This module operationalizes the empirical comparison. At decision
time:

  1. Both models compute p(goal | s, c) on the same page features.
  2. Both models compute F(a) per candidate mechanism.
  3. PRIMARY model's F(a) modulates mechanism_scores per directive
     line 521: score → score - λ_F · F(a).
  4. SHADOW model's posterior + F values are logged in DecisionTrace
     (via user_posterior_snapshot namespaced keys) so the offline
     B-vs-C evaluator (Slice 19) compares them on the same decisions.

When only one model is trained, dual-eval degrades cleanly: shadow
disabled, primary modulates as normal. When neither is trained, both
fall back to PassthroughGoalStateModel (closed-form heuristic) which
still produces valid F values.

DECISION-TIME PATH

  page_features (cascade-built) + cascade.mechanism_scores
      ↓
  DualEvalContext.apply_free_energy_modulation(scores, page_features)
      ↓ score → score - λ_F · F_primary(a)
  modulated mechanism_scores (cascade picks chosen)
      ↓
  DualEvalContext.compute_log_for_trace(...)
      ↓ namespaced posterior + F summaries
  DecisionTrace.user_posterior_snapshot merge

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Spine #5 lines 199-222 (free-energy
    objective); line 521 (cascade score modulation); Foundation §7
    rule 11 (fitness function IS ethics — soft cost composes with
    hard gate from Slice 2). Empirical-comparison framing matches
    the Section 8.4 pre-registered analysis pattern (compare two
    architectures on the same data; let the data decide).

(b) Tests pin: apply_free_energy_modulation reduces scores by the
    right amount; mechanism not in primary's L → no modulation
    (degenerate-q falls through to no-op); both primary and shadow
    posteriors flow into the dual_eval_log; namespaced keys don't
    collide; soft-fail when both models untrained → passthrough
    behavior; soft-fail when shadow None → primary-only logging.

(c) calibration_pending=True. λ_F (free_energy_weight) = 0.10
    conservative pre-pilot (A14 SPINE_5_FREE_ENERGY_WEIGHT_PILOT_PENDING
    from Slice 17a). Comparison metric (Brier vs log-loss vs KL)
    is selected in Slice 19 evaluator.

(d) Honest tags — what is NOT in this slice (named successors):

    * Slice 18 — Claude API label generator that produces the
      training data both models need to be more than passthrough.
    * Slice 19 — offline B-vs-C evaluator on held-out labels.
      This slice's dual_eval_log feeds it; the actual scoring
      (Brier, log-loss, KL) is separate.
    * Cascade-side feature extraction. The bilateral_cascade.py
      wire-up reads page_intelligence's PagePsychologicalProfile
      → page_features dict; the FORMAT of page_features is
      documented but the wire is its own commit.
    * Per-archetype goal-state priors. v0.1 features are page-only;
      adding user_state conditioning is sibling.
    * Cohort-conditional dual-eval (per-cohort which model wins).
      Spine #7 BLOCKED on Loop B; sibling.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

from adam.intelligence.free_energy import (
    DEFAULT_FREE_ENERGY_WEIGHT,
    FreeEnergyDecomposition,
    GoalStatePosterior,
    GoalStatePriorModel,
    PassthroughGoalStateModel,
    decompose_free_energy,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

# Number of top goals from each posterior to log (full 14-goal
# distribution would explode the user_posterior_snapshot field;
# top-K is enough for offline comparison + Defensive Reasoning Layer 4).
DEFAULT_TOP_K_GOALS_LOGGED: int = 5


# =============================================================================
# DualEvalContext — primary + optional shadow
# =============================================================================


class DualEvalContext:
    """Holds the primary and optional shadow GoalStatePriorModel.

    Primary modulates mechanism_scores at decision time. Shadow's
    posteriors + F values are logged in DecisionTrace for offline
    B-vs-C comparison. Either or both can be None — degrades cleanly:

      - both None    → no-op (returns scores unchanged)
      - primary set, shadow None  → primary modulates; no shadow log
      - primary None, shadow set  → no modulation; shadow logged
        (still valuable for offline analysis)
      - both set     → primary modulates AND both logged
    """

    def __init__(
        self,
        *,
        primary_model: Optional[GoalStatePriorModel] = None,
        shadow_model: Optional[GoalStatePriorModel] = None,
    ) -> None:
        self.primary_model = primary_model
        self.shadow_model = shadow_model

    @property
    def has_primary(self) -> bool:
        return self.primary_model is not None


def _compute_posterior_summary(
    posterior: GoalStatePosterior,
    *,
    namespace: str,
    top_k: int = DEFAULT_TOP_K_GOALS_LOGGED,
) -> Dict[str, float]:
    """Reduce a GoalStatePosterior to a small set of namespaced
    summary stats for trace logging.

    Returns a dict with keys:
      {namespace}.entropy_nats: posterior entropy
      {namespace}.top_goal.{goal_id}: probability for top-K goals

    Numerical: zero-probability goals contribute zero to entropy
    (0 · log 0 = 0 by convention).
    """
    out: Dict[str, float] = {}

    # Entropy
    entropy = 0.0
    for prob in posterior.probabilities.values():
        if prob > 0.0:
            entropy -= prob * math.log(prob)
    out[f"{namespace}.entropy_nats"] = entropy

    # Top-K probabilities
    sorted_goals = sorted(
        posterior.probabilities.items(),
        key=lambda kv: kv[1], reverse=True,
    )[:top_k]
    for goal_id, prob in sorted_goals:
        out[f"{namespace}.top_goal.{goal_id}"] = float(prob)

    return out


def apply_free_energy_modulation(
    mechanism_scores: Dict[str, float],
    page_features: Dict[str, Any],
    context: DualEvalContext,
    *,
    posture_confidence: float = 1.0,
    free_energy_weight: float = DEFAULT_FREE_ENERGY_WEIGHT,
    user_state: Optional[Dict[str, float]] = None,
) -> Dict[str, float]:
    """Modulate mechanism_scores by F(a) per directive line 521.

    For each mechanism in scores:
        F(mech) = decompose_free_energy(p_primary, mech, primary_model, π)
        modulated[mech] = score - λ_F · F(mech)
        clip to [0, 1]

    Lower F = candidate aligns better with primed goals → smaller
    subtraction → less score reduction. Higher F = candidate fights
    the primed goals → larger subtraction → score reduced.

    Soft-fail discipline:
      - context.primary_model None → returns scores unchanged
      - empty mechanism_scores → returns scores unchanged
      - any per-candidate exception → that mechanism stays at base
    """
    if not mechanism_scores or context.primary_model is None:
        return mechanism_scores

    try:
        p_primary = context.primary_model.predict_p(
            page_features, user_state,
        )
    except Exception as exc:
        logger.debug(
            "apply_free_energy_modulation: primary predict_p failed: %s",
            exc,
        )
        return mechanism_scores

    modulated: Dict[str, float] = {}
    for mech, base in mechanism_scores.items():
        try:
            base_f = float(base)
        except (TypeError, ValueError):
            modulated[mech] = base
            continue

        try:
            decomp = decompose_free_energy(
                p_primary, mech, context.primary_model,
                posture_confidence=posture_confidence,
            )
            f_value = decomp.free_energy
        except Exception as exc:
            logger.debug(
                "apply_free_energy_modulation: F() failed for %s: %s",
                mech, exc,
            )
            modulated[mech] = base_f
            continue

        new_score = base_f - free_energy_weight * f_value
        if new_score < 0.0:
            new_score = 0.0
        elif new_score > 1.0:
            new_score = 1.0
        modulated[mech] = new_score

    return modulated


def compute_dual_eval_log(
    mechanism_scores: Dict[str, float],
    page_features: Dict[str, Any],
    context: DualEvalContext,
    *,
    posture_confidence: float = 1.0,
    user_state: Optional[Dict[str, float]] = None,
    top_k_goals: int = DEFAULT_TOP_K_GOALS_LOGGED,
) -> Dict[str, float]:
    """Build the dual_eval_log dict for DecisionTrace merging.

    Returns namespaced keys:
        gs_primary.entropy_nats
        gs_primary.top_goal.{goal_id}
        gs_primary.f.{mech}
        gs_shadow.entropy_nats              (if shadow present)
        gs_shadow.top_goal.{goal_id}        (if shadow present)
        gs_shadow.f.{mech}                  (if shadow present)

    Empty dict when both models None / on any soft-fail path. The
    caller merges the result into DecisionTrace.user_posterior_snapshot.

    Slice 19's offline evaluator reads these keys across many
    DecisionTraces to compute Brier / log-loss / KL between
    primary and shadow predictions.
    """
    out: Dict[str, float] = {}

    if context.primary_model is not None:
        try:
            p = context.primary_model.predict_p(page_features, user_state)
            out.update(_compute_posterior_summary(
                p, namespace="gs_primary", top_k=top_k_goals,
            ))
            for mech in mechanism_scores.keys():
                try:
                    decomp = decompose_free_energy(
                        p, mech, context.primary_model,
                        posture_confidence=posture_confidence,
                    )
                    out[f"gs_primary.f.{mech}"] = float(decomp.free_energy)
                except Exception:
                    continue
        except Exception as exc:
            logger.debug(
                "compute_dual_eval_log: primary failed: %s", exc,
            )

    if context.shadow_model is not None:
        try:
            p_shadow = context.shadow_model.predict_p(
                page_features, user_state,
            )
            out.update(_compute_posterior_summary(
                p_shadow, namespace="gs_shadow", top_k=top_k_goals,
            ))
            for mech in mechanism_scores.keys():
                try:
                    decomp = decompose_free_energy(
                        p_shadow, mech, context.shadow_model,
                        posture_confidence=posture_confidence,
                    )
                    out[f"gs_shadow.f.{mech}"] = float(decomp.free_energy)
                except Exception:
                    continue
        except Exception as exc:
            logger.debug(
                "compute_dual_eval_log: shadow failed: %s", exc,
            )

    return out


# =============================================================================
# Module singleton — registered by application startup or tests
# =============================================================================


_default_context: DualEvalContext = DualEvalContext(
    primary_model=PassthroughGoalStateModel(),
    shadow_model=None,
)


def get_dual_eval_context() -> DualEvalContext:
    """Return the process-wide DualEvalContext singleton.

    Default: passthrough as primary, no shadow. Application startup
    registers trained B + C models via ``register_dual_eval_context``;
    tests can swap in synthetic models.
    """
    return _default_context


def register_dual_eval_context(
    *,
    primary_model: Optional[GoalStatePriorModel] = None,
    shadow_model: Optional[GoalStatePriorModel] = None,
) -> None:
    """Replace the singleton's models. None falls back to passthrough
    on the primary side.
    """
    global _default_context
    _default_context = DualEvalContext(
        primary_model=primary_model or PassthroughGoalStateModel(),
        shadow_model=shadow_model,
    )


def reset_dual_eval_for_tests() -> None:
    """Reset to default (passthrough primary, no shadow)."""
    global _default_context
    _default_context = DualEvalContext(
        primary_model=PassthroughGoalStateModel(),
        shadow_model=None,
    )


# =============================================================================
# Slice 20 — startup wire (load labels → train B+C → register winner)
# =============================================================================


async def warm_dual_eval_from_neo4j(
    driver: Optional[Any],
    *,
    min_label_count: int = 20,
) -> Dict[str, Any]:
    """Application-startup composer.

    Composes:
        load_labels_from_neo4j(driver)
            ↓
        train_models_from_labels(labels)  → (B, C)
            ↓
        compare_models_on_labels(labels, primary, shadow)
            ↓
        recommend_primary(report)  → winner_name
            ↓
        register_dual_eval_context(primary=winner, shadow=other)

    Returns a status dict for the startup log:
        {
            "outcome": "registered" | "cold_start" | "skipped",
            "n_labels": int,
            "trained_models": list of names,
            "winner": str | None,
            "reason": str (when skipped/cold_start),
        }

    Soft-fail discipline: ANY exception in the chain returns
    outcome="skipped" with reason. The default DualEvalContext
    singleton (passthrough primary, no shadow) stays in place.
    Production cascade still emits valid F() values via passthrough
    fallback while operators investigate.

    Cold start: when fewer than ``min_label_count`` labels exist,
    skip training. Default 20 — both LogisticRegression and
    NumPyro SVI need a minimum sample for the fit to be meaningful.

    Idempotent: calling repeatedly re-runs the chain; the singleton
    is replaced on each call. Designed for FastAPI startup but also
    safe to call from a Daily Task that retrains nightly.
    """
    status: Dict[str, Any] = {
        "outcome": "skipped",
        "n_labels": 0,
        "trained_models": [],
        "winner": None,
        "reason": "",
    }

    if driver is None:
        status["reason"] = "no_driver"
        return status

    try:
        from adam.intelligence.goal_state_label_generator import (
            load_labels_from_neo4j,
            train_models_from_labels,
        )
        labels = await load_labels_from_neo4j(driver)
    except Exception as exc:
        status["reason"] = f"load_labels_failed: {exc}"
        return status

    status["n_labels"] = len(labels)

    if len(labels) < min_label_count:
        status["outcome"] = "cold_start"
        status["reason"] = (
            f"only {len(labels)} labels (< {min_label_count} required); "
            f"keeping passthrough primary"
        )
        return status

    try:
        b_model, c_model = train_models_from_labels(labels)
    except Exception as exc:
        status["reason"] = f"train_failed: {exc}"
        return status

    if b_model is None and c_model is None:
        status["reason"] = "both_models_failed_to_train"
        return status

    if b_model is not None:
        status["trained_models"].append(b_model.model_name)
    if c_model is not None:
        status["trained_models"].append(c_model.model_name)

    # If only one model trained, register it as primary directly.
    if b_model is None or c_model is None:
        primary = b_model if b_model is not None else c_model
        register_dual_eval_context(primary_model=primary, shadow_model=None)
        status["outcome"] = "registered"
        status["winner"] = primary.model_name
        status["reason"] = "only_one_model_trained"
        return status

    # Both trained — score them and pick the winner.
    try:
        from adam.intelligence.dual_eval_evaluator import (
            compare_models_on_labels,
            recommend_primary,
        )
        report = compare_models_on_labels(labels, b_model, c_model)
    except Exception as exc:
        # Evaluator failed — register B as primary by default
        register_dual_eval_context(
            primary_model=b_model, shadow_model=c_model,
        )
        status["outcome"] = "registered"
        status["winner"] = b_model.model_name
        status["reason"] = f"evaluator_failed_b_default: {exc}"
        return status

    if report is None:
        register_dual_eval_context(
            primary_model=b_model, shadow_model=c_model,
        )
        status["outcome"] = "registered"
        status["winner"] = b_model.model_name
        status["reason"] = "evaluator_returned_none_b_default"
        return status

    winner_name = recommend_primary(report)

    if winner_name == c_model.model_name:
        register_dual_eval_context(
            primary_model=c_model, shadow_model=b_model,
        )
        status["winner"] = c_model.model_name
    else:
        # Default to B as primary on ties / unknown winner — the Logistic
        # model is the simpler / more interpretable / faster of the two.
        register_dual_eval_context(
            primary_model=b_model, shadow_model=c_model,
        )
        status["winner"] = b_model.model_name

    status["outcome"] = "registered"
    return status
