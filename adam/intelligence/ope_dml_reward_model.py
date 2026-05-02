# =============================================================================
# DML cross-fit reward model — Spine #6 / OPE DR upgrade
# Location: adam/intelligence/ope_dml_reward_model.py
# =============================================================================
"""Doubly-Machine-Learning cross-fit reward model q̂(x, a) for OPE DR.

Closes the named sibling tag from
``adam/intelligence/ope.py:270-272``:

    "Unbiased if EITHER q̂(x, a) OR p_i is correct. The substrate
     accepts a reward_model callable for q̂; production passes the
     DML cross-fit q̂ from M2 here."

Per the Seven-Component Methodological Upgrade Handoff §4 + directive
Spine #6 (lines 226-244): the DR estimator's q̂ component MUST be
out-of-fold — using in-sample predictions for q̂ in the DR formula
introduces overfitting bias that contaminates the estimate. The
canonical fix is K-fold cross-fitting (Chernozhukov et al. 2018):

    1. Split samples into K folds.
    2. For each fold k:
       — Train a reward model on the OTHER K-1 folds.
       — Predict on fold k (these predictions are OOS).
    3. The DR estimator uses the OOS prediction for sample i, where
       i ∈ fold k, with the model trained without fold k.

WHY THIS EXISTS

Task 41's v0.1 used a constant q̂ ≡ 0.5 baseline as a placeholder.
That's the worst-case DR — DR collapses to IPS when q̂ is the
constant marginal mean (no variance reduction from the DM control
variate). The cross-fit upgrade gets us a real DR with the right
asymptotic guarantees for CI/CD policy gates.

THE PRIMITIVE

  * ``CrossFitRewardModel`` — frozen artifact. Stores per-fold
    trained sub-models + a mapping from sample → fold. Implements
    the standard ``reward_model(context, action) -> float`` callable
    interface so it can be passed to ``estimate_dr`` /
    ``estimate_switch_dr`` as a drop-in.
  * ``fit_cross_fit_reward_model(samples, *, k_folds, action_space)``
    — fits + returns CrossFitRewardModel.

v0.1 underlying model: per-action mean reward (marginal q̂(a) — no
context conditioning). This is the simplest model that ships the
CROSS-FIT pattern correctly. The cross-fit machinery is the spine;
the underlying model is replaceable. Per-action means already give
DR a non-trivial control variate (each action's mean) which yields
real variance reduction even on small samples.

DISCIPLINE (B3-LUXY a/b/c/d)
----------------------------

(a) Citations: directive Spine #6 lines 226-244 + ope.py:270-272
    (named sibling). DML cross-fit pattern from Chernozhukov et al.
    2018 ("Double/Debiased Machine Learning for Treatment and
    Structural Parameters") + Dudík et al. 2011 (DR estimator). The
    K-fold split discipline is the substrate; the underlying per-
    action-mean model is the v0.1 simplest-honest scaffold.

(b) Tests pin: K=5 default; per-fold training honors held-out;
    OOS predictions are stable per (sample_id, action); fold split
    deterministic given seed; predict for unseen context returns
    grand mean across folds; insufficient samples (n < k_folds)
    falls back to single-fold marginal mean; CrossFitRewardModel
    is the standard ``Callable[[Dict, str], float]``; passes
    estimate_dr without raising.

(c) calibration_pending=True. v0.1 underlying model is per-action
    marginal mean (no context conditioning). LUXY pilot will
    calibrate (i) k_folds (5 is conservative pre-pilot), (ii)
    underlying model swap to gradient-boosted regressor /
    causal forest. A14 flag: SPINE_6_DML_REWARD_MODEL_PILOT_PENDING.

(d) Honest tags — what is NOT in this slice (named successors):

    * Context-conditional underlying model. v0.1 ignores
      ``context`` — predictions are per-action grand means
      (marginal q̂(a)). Sibling slice swaps in (i) gradient-
      boosted regressor over context features, or (ii) causal
      forest from M2 (per directive's "DML cross-fit q̂ from M2"
      reference). The cross-fit machinery in this slice composes
      with any underlying regressor.
    * Per-action sample-balancing within folds. v0.1 splits
      samples uniformly; an imbalanced action distribution can
      leave a fold with zero samples for some action. The
      callable falls back to overall mean for missing-action
      predictions; the rigor sibling stratifies the fold split
      by action.
    * Cross-validated k_folds selection. v0.1 uses a fixed K=5.
      Per-pilot tuning is sibling.
    * Variance estimation that accounts for the model uncertainty
      itself (sandwich variance). v0.1 uses the standard DR
      variance formula assuming q̂ is exact at predicted values;
      the true sandwich form is sibling.
"""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# A14 SPINE_6_DML_REWARD_MODEL_PILOT_PENDING
DEFAULT_K_FOLDS: int = 5

# Below this many samples, cross-fit collapses (K-fold needs ≥K
# samples). The fitter falls back to a single global per-action mean.
MIN_SAMPLES_PER_FOLD: int = 5


# Sample id is hashed by (decision_id when present) or by tuple of
# context items + action — anything that uniquely identifies the
# logged row. Cross-fit is always ON THE SAMPLES, so identity must
# be stable across the (split → train → predict) sequence.
def _sample_identity(sample: Any) -> Tuple:
    """Stable identity for a logged sample. Prefers ``decision_id``
    when present; falls back to (sorted context items, action)."""
    decision_id = getattr(sample, "decision_id", None)
    if decision_id is not None:
        return ("did", str(decision_id))
    ctx = getattr(sample, "context", {}) or {}
    if isinstance(ctx, dict):
        ctx_key = tuple(sorted(ctx.items()))
    else:
        ctx_key = (str(ctx),)
    action = getattr(sample, "action", "")
    return ("ctx_action", ctx_key, str(action))


def _per_action_mean(
    samples: List[Any], action_space: List[str],
) -> Dict[str, float]:
    """Per-action marginal mean reward. Empty action → grand mean
    fallback. Returns {action: predicted_reward}."""
    by_action: Dict[str, List[float]] = {a: [] for a in action_space}
    all_rewards: List[float] = []
    for s in samples:
        r = float(getattr(s, "reward", 0.0))
        a = str(getattr(s, "action", ""))
        all_rewards.append(r)
        if a in by_action:
            by_action[a].append(r)
    grand = (
        statistics.fmean(all_rewards) if all_rewards else 0.5
    )
    out: Dict[str, float] = {}
    for a in action_space:
        if by_action[a]:
            out[a] = statistics.fmean(by_action[a])
        else:
            out[a] = grand
    return out


@dataclass(frozen=True)
class CrossFitRewardModel:
    """Cross-fit reward model q̂(x, a) for OPE DR.

    Stores per-fold trained sub-models (each a Dict[action, mean])
    + the sample-to-fold mapping. The callable interface looks up
    each sample's fold and returns the OOS prediction (the prediction
    from the sub-model trained on the OTHER K-1 folds).

    For unseen contexts (production / counterfactual evaluation
    where the sample is not in training), the callable returns the
    grand mean across all K sub-models.
    """

    fold_predictions: List[Dict[str, float]]  # K sub-models
    sample_to_fold: Dict[Tuple, int]
    action_space: List[str]
    k_folds: int

    @property
    def grand_predictions(self) -> Dict[str, float]:
        """Grand-mean predictions across all K sub-models. Used for
        unseen contexts (counterfactual or production)."""
        if not self.fold_predictions:
            return {a: 0.5 for a in self.action_space}
        out: Dict[str, float] = {}
        for a in self.action_space:
            vals = [m.get(a, 0.5) for m in self.fold_predictions]
            out[a] = statistics.fmean(vals)
        return out

    def __call__(self, context: Any, action: str) -> float:
        """Drop-in callable for ope.estimate_dr's reward_model arg.

        Looks up the OOS prediction by context+action when the
        context matches a training sample; otherwise returns the
        grand mean (treated as "unseen context fallback").
        """
        # Try to match by (decision_id) first if context has one
        # (production callers often pass ``OPESample.context`` which
        # may include decision_id as a feature).
        decision_id = None
        if isinstance(context, dict):
            decision_id = context.get("decision_id")
        if decision_id is not None:
            key = ("did", str(decision_id))
            fold = self.sample_to_fold.get(key)
            if fold is not None:
                return float(
                    self.fold_predictions[fold].get(
                        str(action),
                        self.grand_predictions.get(str(action), 0.5),
                    )
                )

        # Fall back to (context, action) hash
        if isinstance(context, dict):
            ctx_key = tuple(sorted(context.items()))
        else:
            ctx_key = (str(context),)
        key = ("ctx_action", ctx_key, str(action))
        fold = self.sample_to_fold.get(key)
        if fold is not None:
            return float(
                self.fold_predictions[fold].get(
                    str(action),
                    self.grand_predictions.get(str(action), 0.5),
                )
            )

        # Unseen context — grand mean across folds.
        return float(self.grand_predictions.get(str(action), 0.5))


def fit_cross_fit_reward_model(
    samples: List[Any],
    *,
    action_space: List[str],
    k_folds: int = DEFAULT_K_FOLDS,
) -> CrossFitRewardModel:
    """Fit K-fold cross-fit per-action mean reward model.

    Args:
        samples: list of OPE sample objects with ``.context``,
            ``.action``, ``.reward`` attributes (anything matching
            ``OPESample`` shape works — duck-typed).
        action_space: full action space; predictions returned for
            every action even if absent from training fold.
        k_folds: K-fold split count. Default 5. When fewer than
            K samples are available, falls back to a single-fold
            global model (marginal-mean baseline; honest signal
            in the result).

    Returns:
        ``CrossFitRewardModel`` — passes as drop-in for the
        ``reward_model`` arg of ``estimate_dr`` / ``estimate_switch_dr``.

    Behavior:
      * n_samples == 0 → returns a model with one fold of grand
        means at 0.5 each (matches the constant-baseline behavior
        Task 41 v0.1 used).
      * n_samples < k_folds → reduces to single-fold marginal mean
        (preserves the callable interface; the DR caller still gets
        a reward_model, just without OOS rigor).
      * n_samples >= k_folds → standard K-fold cross-fit.

    Determinism: fold assignment uses sample index modulo K (no
    randomization). This makes fits reproducible across reruns;
    the ordering-sensitivity is a known limitation that pilot-stage
    can shore up via stratified or randomized splits.
    """
    n = len(samples)
    if n == 0:
        # Return constant-baseline shape — mirrors Task 41 v0.1.
        return CrossFitRewardModel(
            fold_predictions=[{a: 0.5 for a in action_space}],
            sample_to_fold={},
            action_space=list(action_space),
            k_folds=1,
        )

    if n < k_folds:
        # Single-fold marginal mean; preserves callable contract.
        means = _per_action_mean(samples, action_space)
        sample_to_fold = {
            _sample_identity(s): 0 for s in samples
        }
        return CrossFitRewardModel(
            fold_predictions=[means],
            sample_to_fold=sample_to_fold,
            action_space=list(action_space),
            k_folds=1,
        )

    # K-fold split — sample index modulo K (deterministic).
    folds: List[List[Any]] = [[] for _ in range(k_folds)]
    for i, s in enumerate(samples):
        folds[i % k_folds].append(s)

    fold_predictions: List[Dict[str, float]] = []
    sample_to_fold: Dict[Tuple, int] = {}

    for k in range(k_folds):
        # Train on K-1 folds (everything NOT in fold k)
        train: List[Any] = []
        for j in range(k_folds):
            if j != k:
                train.extend(folds[j])
        means_k = _per_action_mean(train, action_space)
        fold_predictions.append(means_k)

        # Mark this fold's samples for OOS lookup against this model
        for s in folds[k]:
            sample_to_fold[_sample_identity(s)] = k

    return CrossFitRewardModel(
        fold_predictions=fold_predictions,
        sample_to_fold=sample_to_fold,
        action_space=list(action_space),
        k_folds=k_folds,
    )
