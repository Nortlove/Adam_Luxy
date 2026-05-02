"""Pin Slice 17 — DML cross-fit reward model.

Closes the named sibling tag from ope.py:270-272 (production passes
the DML cross-fit q̂ here). The cross-fit pattern (K-fold + OOS
predictions) is the spine; the v0.1 underlying model is per-action
marginal mean (simplest honest scaffold).

Discipline anchors (B3-LUXY a/b/c/d):

    (a) Citations: ope.py:270-272 (named sibling) + Spine #6
        + Chernozhukov et al. 2018 (DML cross-fit pattern) +
        Dudík et al. 2011 (DR estimator).

    (b) Boundary anchors:
          - K=5 default; samples partitioned mod K
          - Per-fold prediction trained on the OTHER K-1 folds
          - OOS predictions stable per (decision_id) and
            (context, action) hash
          - Insufficient samples (n < K) → single-fold marginal mean
          - Empty samples → constant 0.5 baseline (matches
            Task 41 v0.1 fallback)
          - Unseen context → grand mean across folds
          - CrossFitRewardModel is callable (Dict, str) → float
          - Drops into estimate_dr without raising
          - Frozen dataclass (immutable)

    (c) calibration_pending=True (per-action marginal mean is v0.1).

    (d) Honest tags — what is NOT tested here:
          - Context-conditional underlying model swap (sibling)
          - Per-action sample-balanced fold split (sibling)
          - Cross-validated K selection (sibling)
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Any, Dict, List

import pytest

from adam.intelligence.ope_dml_reward_model import (
    DEFAULT_K_FOLDS,
    MIN_SAMPLES_PER_FOLD,
    CrossFitRewardModel,
    fit_cross_fit_reward_model,
)


# -----------------------------------------------------------------------------
# Fakes
# -----------------------------------------------------------------------------


@dataclass
class _Sample:
    """Duck-type matching OPESample for fit_cross_fit_reward_model."""
    decision_id: str
    context: Dict[str, float]
    action: str
    reward: float
    propensity: float = 0.5
    pscore_known: bool = True


def _mk_sample(i: int, action: str, reward: float) -> _Sample:
    return _Sample(
        decision_id=f"dec-{i:04d}",
        context={"feat": float(i % 7)},
        action=action,
        reward=reward,
    )


# -----------------------------------------------------------------------------
# Edge cases — empty / small samples
# -----------------------------------------------------------------------------


def test_fit_empty_samples_returns_constant_baseline():
    """No samples → CrossFitRewardModel with constant 0.5 grand mean
    (matches Task 41 v0.1 baseline)."""
    out = fit_cross_fit_reward_model(
        samples=[], action_space=["a", "b"],
    )
    assert out.k_folds == 1
    # Predictions everywhere are 0.5
    assert out({}, "a") == 0.5
    assert out({}, "b") == 0.5


def test_fit_below_k_folds_returns_single_fold():
    """When n < K, the fitter returns a single-fold marginal-mean
    model. Still better than constant 0.5 — uses the actual data."""
    samples = [
        _mk_sample(0, "a", 1.0),
        _mk_sample(1, "a", 1.0),
        _mk_sample(2, "b", 0.0),
    ]
    out = fit_cross_fit_reward_model(
        samples=samples, action_space=["a", "b"],
        k_folds=DEFAULT_K_FOLDS,
    )
    assert out.k_folds == 1
    # All training samples now use the same single fold;
    # action 'a' marginal mean = 1.0; action 'b' = 0.0.
    pred_a = out({"feat": 0.0}, "a")
    pred_b = out({"feat": 0.0}, "b")
    # Predictions for in-training contexts come from the single model.
    # Use a sample that's known to be in training.
    pred_ds_a = out({"decision_id": "dec-0000"}, "a")
    pred_ds_b = out({"decision_id": "dec-0002"}, "b")
    assert pred_ds_a == pytest.approx(1.0)
    assert pred_ds_b == pytest.approx(0.0)


# -----------------------------------------------------------------------------
# K-fold cross-fit — main path
# -----------------------------------------------------------------------------


def test_fit_default_k_folds_is_5():
    """The default k_folds is 5 per the DEFAULT_K_FOLDS constant."""
    assert DEFAULT_K_FOLDS == 5


def test_fit_returns_k_separate_fold_models():
    """With K=5 and n=25, the fit creates 5 sub-models."""
    samples = [
        _mk_sample(i, "a" if i % 2 == 0 else "b", float(i % 2))
        for i in range(25)
    ]
    out = fit_cross_fit_reward_model(
        samples=samples, action_space=["a", "b"], k_folds=5,
    )
    assert out.k_folds == 5
    assert len(out.fold_predictions) == 5


def test_fit_each_fold_trained_on_held_out_data():
    """Each fold's sub-model uses only OTHER folds' samples for
    training. Smoke-test by constructing a dataset where action 'a'
    has perfect reward 1.0 ONLY in fold 0; the model trained without
    fold 0 should predict close to 0 for action 'a' (since training
    folds 1..4 only have action 'a' with reward 0)."""
    samples: List[_Sample] = []
    # 5 folds × 5 samples = 25. Sample i goes to fold i % 5.
    for i in range(25):
        fold_id = i % 5
        if fold_id == 0:
            # Fold 0: action 'a' with reward 1.0
            samples.append(_mk_sample(i, "a", 1.0))
        else:
            # Other folds: action 'a' with reward 0.0
            samples.append(_mk_sample(i, "a", 0.0))

    out = fit_cross_fit_reward_model(
        samples=samples, action_space=["a"], k_folds=5,
    )
    # Fold 0's sub-model was trained on folds 1..4 only → all 0s.
    fold_0_model = out.fold_predictions[0]
    assert fold_0_model["a"] == pytest.approx(0.0)
    # Fold 1's sub-model was trained on folds 0,2,3,4 — has 5 ones
    # (from fold 0) + 15 zeros = 0.25 mean.
    fold_1_model = out.fold_predictions[1]
    assert fold_1_model["a"] == pytest.approx(0.25)


def test_fit_oos_lookup_via_decision_id():
    """A training sample's prediction is its fold's OOS prediction
    (model trained without its fold)."""
    samples = [
        _mk_sample(i, "a", 1.0 if i < 5 else 0.0)
        for i in range(25)
    ]
    out = fit_cross_fit_reward_model(
        samples=samples, action_space=["a"], k_folds=5,
    )
    # Sample 0 is in fold 0 (0%5==0). Fold 0's sub-model trained
    # on folds 1..4 (20 samples total). Of those, samples 1,2,3,4
    # have reward 1.0 (4 ones), and the rest reward 0.0 → mean 4/20
    # = 0.2.
    pred = out({"decision_id": "dec-0000"}, "a")
    assert pred == pytest.approx(4.0 / 20.0, rel=1e-9)


def test_fit_unseen_context_returns_grand_mean():
    """A context not present in training → grand mean over the K
    sub-models."""
    samples = [
        _mk_sample(i, "a", 0.5) for i in range(25)
    ]
    out = fit_cross_fit_reward_model(
        samples=samples, action_space=["a"], k_folds=5,
    )
    pred_unseen = out({"decision_id": "unseen-id"}, "a")
    # Each fold's model trained on 20 samples all reward=0.5 →
    # all 5 sub-models predict 0.5 → grand mean 0.5.
    assert pred_unseen == pytest.approx(0.5)


def test_fit_action_absent_in_fold_falls_back_to_grand():
    """If action absent in a training fold, prediction falls back
    to the grand mean across folds."""
    samples = [
        _mk_sample(i, "a" if i < 20 else "b", 0.5)
        for i in range(25)
    ]
    out = fit_cross_fit_reward_model(
        samples=samples, action_space=["a", "b", "c"], k_folds=5,
    )
    # Action 'c' never appears in training → falls back.
    # The _per_action_mean function returns the grand mean for
    # missing actions, so each fold's model has prediction[c] =
    # grand mean of training samples (= 0.5).
    pred_c = out({"decision_id": "dec-0000"}, "c")
    assert pred_c == pytest.approx(0.5)


def test_fit_callable_signature_for_dr_dropin():
    """CrossFitRewardModel must accept (context: Dict, action: str)
    and return float — the signature ope.estimate_dr expects."""
    samples = [_mk_sample(i, "a", 0.5) for i in range(25)]
    model = fit_cross_fit_reward_model(
        samples=samples, action_space=["a"], k_folds=5,
    )
    # callable
    assert callable(model)
    val = model({"any": "context"}, "a")
    assert isinstance(val, float)


def test_fit_drops_into_estimate_dr_without_raising():
    """Smoke test — fit then pass to estimate_dr."""
    from adam.intelligence.ope import estimate_dr

    samples = [
        _mk_sample(i, "a" if i % 2 == 0 else "b", float(i % 2))
        for i in range(20)
    ]
    model = fit_cross_fit_reward_model(
        samples=samples, action_space=["a", "b"], k_folds=5,
    )

    def _identity_policy(ctx, action):
        return 0.5  # arbitrary target policy

    # Should not raise.
    dr_result = estimate_dr(
        samples=samples,
        target_policy=_identity_policy,
        reward_model=model,
        action_space=["a", "b"],
    )
    assert dr_result.estimator == "DR"
    assert dr_result.n_samples > 0


def test_cross_fit_model_frozen():
    """The CrossFitRewardModel dataclass is frozen."""
    samples = [_mk_sample(0, "a", 0.5)]
    model = fit_cross_fit_reward_model(
        samples=samples, action_space=["a"],
    )
    with pytest.raises((AttributeError, Exception)):
        model.k_folds = 99  # type: ignore[misc]


def test_fit_deterministic_reproducible():
    """Same samples + same K → same fold assignment + predictions."""
    samples = [_mk_sample(i, "a", float(i)) for i in range(25)]
    a = fit_cross_fit_reward_model(
        samples=samples, action_space=["a"], k_folds=5,
    )
    b = fit_cross_fit_reward_model(
        samples=samples, action_space=["a"], k_folds=5,
    )
    assert a.fold_predictions == b.fold_predictions
    assert a.sample_to_fold == b.sample_to_fold


# -----------------------------------------------------------------------------
# Task 41 integration — wire pin
# -----------------------------------------------------------------------------


def test_task_41_imports_dml_cross_fit():
    """Source-text contract: Task 41 references the cross-fit
    primitive (no longer constant 0.5)."""
    from pathlib import Path
    src = Path(
        "adam/intelligence/daily/task_41_ope_daily_estimator.py"
    ).read_text()
    assert "fit_cross_fit_reward_model" in src, (
        "Task 41 lost its DML cross-fit fit. Falling back to "
        "constant 0.5 baseline silently."
    )


def test_task_41_surfaces_reward_model_label():
    """Task 41 details surface which reward model was used so
    operators can audit (constant_0.5_fallback vs cross_fit)."""
    from pathlib import Path
    src = Path(
        "adam/intelligence/daily/task_41_ope_daily_estimator.py"
    ).read_text()
    assert 'result.details["reward_model"]' in src
    assert "dml_cross_fit_per_action_mean" in src


def test_ope_module_honest_tag_marked_shipped():
    """ope.py:270-272 honest tag updated to mark Slice 17 shipped."""
    from pathlib import Path
    src = Path("adam/intelligence/ope.py").read_text()
    assert "Slice 17" in src
    assert "ope_dml_reward_model" in src
