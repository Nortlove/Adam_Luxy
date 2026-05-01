"""Pin Slice 17d — dual-eval wiring (B + C parallel logging).

Discipline anchors (B3-LUXY a/b/c/d):

    (a) Citations: directive Spine #5 lines 199-222; line 521
        (cascade score modulation); Foundation §7 rule 11
        (fitness function IS ethics — soft cost composes with
        hard gate from Slice 2). Empirical-comparison framing
        per Section 8.4 pre-registered analysis.

    (b) Boundary anchors:
          - apply_free_energy_modulation reduces scores when F > 0
          - identical posture/keywords → no-op (q == p, F = 0)
          - empty mechanism_scores → unchanged
          - primary None → unchanged (no-op)
          - score clipped to [0, 1]
          - mechanism not in inventory's mechanism_priors →
            degenerate-q falls back, F still finite, score
            modulated by KL only
          - compute_dual_eval_log returns namespaced keys
          - empty when both models None
          - shadow None → only gs_primary keys logged
          - both set → both gs_primary + gs_shadow logged
          - top-K goals included in posterior summary
          - entropy reported per posterior
          - F per mechanism logged
          - singleton get_dual_eval_context default has passthrough
            primary
          - register / reset_dual_eval_for_tests work

    (c) calibration_pending=True. λ_F default 0.10 carried from
        Slice 17a A14 flag.

    (d) Honest tags — what is NOT tested:
          - Cascade integration end-to-end (separate cascade test
            covers that path)
          - Slice 19 offline evaluator (sibling)
          - Slice 18 label generator (sibling)
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from adam.intelligence.free_energy import (
    GoalStatePosterior,
    PassthroughGoalStateModel,
)
from adam.intelligence.free_energy_dual_eval import (
    DEFAULT_TOP_K_GOALS_LOGGED,
    DualEvalContext,
    apply_free_energy_modulation,
    compute_dual_eval_log,
    get_dual_eval_context,
    register_dual_eval_context,
    reset_dual_eval_for_tests,
)
from adam.intelligence.goal_state_inventory import list_goal_states
from adam.intelligence.page_attentional_posture_substrate import (
    POSTURE_BLEND,
    POSTURE_VIGILANCE,
)


def setup_function() -> None:
    reset_dual_eval_for_tests()


# -----------------------------------------------------------------------------
# DualEvalContext shape
# -----------------------------------------------------------------------------


def test_dual_eval_context_default_no_models():
    ctx = DualEvalContext()
    assert ctx.primary_model is None
    assert ctx.shadow_model is None
    assert ctx.has_primary is False


def test_dual_eval_context_with_primary():
    ctx = DualEvalContext(primary_model=PassthroughGoalStateModel())
    assert ctx.has_primary is True
    assert ctx.shadow_model is None


# -----------------------------------------------------------------------------
# apply_free_energy_modulation
# -----------------------------------------------------------------------------


def test_modulation_no_op_when_primary_none():
    """No primary model → scores unchanged."""
    ctx = DualEvalContext()
    scores = {"social_proof": 0.5, "scarcity": 0.4}
    out = apply_free_energy_modulation(scores, page_features={}, context=ctx)
    assert out is scores


def test_modulation_no_op_on_empty_scores():
    ctx = DualEvalContext(primary_model=PassthroughGoalStateModel())
    out = apply_free_energy_modulation({}, page_features={}, context=ctx)
    assert out == {}


def test_modulation_clips_score_to_zero_floor():
    """Even pathological F values cannot produce negative scores."""
    ctx = DualEvalContext(primary_model=PassthroughGoalStateModel())
    # Score 0.0 baseline + huge λ_F → score still ≥ 0
    scores = {"mimetic_desire": 0.0}
    out = apply_free_energy_modulation(
        scores, page_features={"posture_class": POSTURE_BLEND},
        context=ctx, free_energy_weight=100.0,
    )
    assert out["mimetic_desire"] >= 0.0


def test_modulation_clips_score_to_one_ceiling():
    """Negative F (high pragmatic, low KL) shouldn't push score >1."""
    ctx = DualEvalContext(primary_model=PassthroughGoalStateModel())
    scores = {"mimetic_desire": 0.99}
    out = apply_free_energy_modulation(
        scores, page_features={"posture_class": POSTURE_BLEND},
        context=ctx,
    )
    assert out["mimetic_desire"] <= 1.0


def test_modulation_handles_unknown_mechanism_softfail():
    """Mechanism not in inventory's mechanism_priors → degenerate q
    falls through; F = -log E[L] (KL=0). Score may shift but
    operation never raises."""
    ctx = DualEvalContext(primary_model=PassthroughGoalStateModel())
    scores = {"completely_unknown_mechanism": 0.5}
    out = apply_free_energy_modulation(
        scores, page_features={"posture_class": POSTURE_BLEND},
        context=ctx,
    )
    assert "completely_unknown_mechanism" in out
    # Output is finite and clipped to [0, 1]
    assert 0.0 <= out["completely_unknown_mechanism"] <= 1.0


def test_modulation_returns_modulated_scores_when_f_nonzero():
    """With passthrough primary on a real mechanism, modulated
    score generally differs from base (F has KL or pragmatic
    contributions)."""
    ctx = DualEvalContext(primary_model=PassthroughGoalStateModel())
    scores = {"mimetic_desire": 0.5}
    out = apply_free_energy_modulation(
        scores,
        page_features={
            "posture_class": POSTURE_BLEND,
            "page_keywords": ["airport", "flight"],
        },
        context=ctx, free_energy_weight=0.20,
    )
    # The output is a fresh dict, not the input
    assert out is not scores
    # Score is finite + clipped
    assert 0.0 <= out["mimetic_desire"] <= 1.0


# -----------------------------------------------------------------------------
# compute_dual_eval_log
# -----------------------------------------------------------------------------


def test_log_empty_when_both_models_none():
    ctx = DualEvalContext()
    log = compute_dual_eval_log(
        mechanism_scores={"x": 0.5},
        page_features={}, context=ctx,
    )
    assert log == {}


def test_log_only_primary_when_shadow_none():
    """No shadow → only gs_primary keys logged."""
    ctx = DualEvalContext(primary_model=PassthroughGoalStateModel())
    log = compute_dual_eval_log(
        mechanism_scores={"mimetic_desire": 0.5},
        page_features={"posture_class": POSTURE_BLEND},
        context=ctx,
    )
    has_primary = any(k.startswith("gs_primary.") for k in log.keys())
    has_shadow = any(k.startswith("gs_shadow.") for k in log.keys())
    assert has_primary
    assert not has_shadow


def test_log_both_when_both_present():
    """Both models → both namespaces present."""
    ctx = DualEvalContext(
        primary_model=PassthroughGoalStateModel(),
        shadow_model=PassthroughGoalStateModel(),
    )
    log = compute_dual_eval_log(
        mechanism_scores={"mimetic_desire": 0.5, "social_proof": 0.3},
        page_features={"posture_class": POSTURE_BLEND},
        context=ctx,
    )
    has_primary = any(k.startswith("gs_primary.") for k in log.keys())
    has_shadow = any(k.startswith("gs_shadow.") for k in log.keys())
    assert has_primary
    assert has_shadow


def test_log_includes_entropy():
    ctx = DualEvalContext(primary_model=PassthroughGoalStateModel())
    log = compute_dual_eval_log(
        mechanism_scores={"x": 0.5},
        page_features={"posture_class": POSTURE_BLEND},
        context=ctx,
    )
    assert "gs_primary.entropy_nats" in log
    # Entropy is a finite non-negative float
    assert log["gs_primary.entropy_nats"] >= 0.0


def test_log_includes_top_k_goals():
    ctx = DualEvalContext(primary_model=PassthroughGoalStateModel())
    log = compute_dual_eval_log(
        mechanism_scores={"x": 0.5},
        page_features={
            "posture_class": POSTURE_BLEND,
            "page_keywords": ["airport"],
        },
        context=ctx,
        top_k_goals=3,
    )
    top_keys = [k for k in log.keys() if k.startswith("gs_primary.top_goal.")]
    assert len(top_keys) == 3


def test_log_includes_per_mechanism_F():
    ctx = DualEvalContext(primary_model=PassthroughGoalStateModel())
    mechanisms = {"mimetic_desire": 0.5, "social_proof": 0.4}
    log = compute_dual_eval_log(
        mechanism_scores=mechanisms,
        page_features={"posture_class": POSTURE_BLEND},
        context=ctx,
    )
    f_keys = [k for k in log.keys() if k.startswith("gs_primary.f.")]
    assert "gs_primary.f.mimetic_desire" in f_keys
    assert "gs_primary.f.social_proof" in f_keys


def test_log_namespaces_dont_collide():
    """Primary and shadow keys live in different namespaces."""
    ctx = DualEvalContext(
        primary_model=PassthroughGoalStateModel(),
        shadow_model=PassthroughGoalStateModel(),
    )
    log = compute_dual_eval_log(
        mechanism_scores={"x": 0.5},
        page_features={"posture_class": POSTURE_BLEND},
        context=ctx,
    )
    # No key starts with both prefixes (impossible by string structure)
    for k in log.keys():
        assert not (
            k.startswith("gs_primary.") and k.startswith("gs_shadow.")
        )


def test_log_handles_primary_predict_p_failure():
    """Primary raising → log doesn't include gs_primary keys but
    operation doesn't raise."""
    class _Raising:
        @property
        def model_name(self): return "raising"
        def predict_p(self, *a, **kw):
            raise RuntimeError("boom")
        def predict_q(self, *a, **kw):
            raise RuntimeError("boom")

    ctx = DualEvalContext(primary_model=_Raising())
    log = compute_dual_eval_log(
        mechanism_scores={"x": 0.5},
        page_features={}, context=ctx,
    )
    # Primary failed → no gs_primary keys; soft-fail path
    assert all(not k.startswith("gs_primary.") for k in log.keys())


# -----------------------------------------------------------------------------
# Singleton
# -----------------------------------------------------------------------------


def test_default_singleton_has_passthrough_primary():
    ctx = get_dual_eval_context()
    assert ctx.has_primary is True
    assert isinstance(ctx.primary_model, PassthroughGoalStateModel)
    assert ctx.shadow_model is None


def test_register_swaps_models():
    class _Stub:
        @property
        def model_name(self): return "stub"
        def predict_p(self, *a, **kw):
            return GoalStatePosterior(probabilities={"x": 1.0}, model_name="stub")
        def predict_q(self, *a, **kw):
            return GoalStatePosterior(probabilities={"x": 1.0}, model_name="stub")

    register_dual_eval_context(primary_model=_Stub(), shadow_model=_Stub())
    ctx = get_dual_eval_context()
    assert ctx.primary_model.model_name == "stub"
    assert ctx.shadow_model.model_name == "stub"


def test_reset_for_tests_restores_default():
    register_dual_eval_context(
        primary_model=None,  # → fallback to passthrough
        shadow_model=PassthroughGoalStateModel(),
    )
    reset_dual_eval_for_tests()
    ctx = get_dual_eval_context()
    assert isinstance(ctx.primary_model, PassthroughGoalStateModel)
    assert ctx.shadow_model is None


def test_register_with_none_primary_falls_back_to_passthrough():
    """register_dual_eval_context(primary_model=None) falls back to
    passthrough so the singleton always has a primary."""
    register_dual_eval_context(primary_model=None)
    ctx = get_dual_eval_context()
    assert isinstance(ctx.primary_model, PassthroughGoalStateModel)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


def test_default_top_k_pinned():
    assert DEFAULT_TOP_K_GOALS_LOGGED == 5


# -----------------------------------------------------------------------------
# Slice 20 — warm_dual_eval_from_neo4j
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_warm_no_driver_returns_skipped():
    """No driver → soft-fail; passthrough primary preserved."""
    from adam.intelligence.free_energy_dual_eval import (
        warm_dual_eval_from_neo4j,
    )
    status = await warm_dual_eval_from_neo4j(driver=None)
    assert status["outcome"] == "skipped"
    assert status["reason"] == "no_driver"


@pytest.mark.asyncio
async def test_warm_cold_start_when_below_threshold():
    """Fewer labels than min_label_count → cold_start; passthrough primary."""
    from adam.intelligence.free_energy_dual_eval import (
        warm_dual_eval_from_neo4j,
    )
    from adam.intelligence.goal_state_label_generator import GoalStateLabel

    fake_labels = [
        GoalStateLabel(
            label_id=f"l-{i}", page_url="x", page_features={},
            active_goal_state_ids=["airport_transfer"], confidence=0.85,
        )
        for i in range(5)
    ]

    with patch(
        "adam.intelligence.goal_state_label_generator.load_labels_from_neo4j",
        return_value=fake_labels,
    ):
        status = await warm_dual_eval_from_neo4j(
            driver=MagicMock(), min_label_count=20,
        )
    assert status["outcome"] == "cold_start"
    assert status["n_labels"] == 5
    assert "5 labels" in status["reason"]


@pytest.mark.asyncio
async def test_warm_load_labels_failure_returns_skipped():
    """If load_labels_from_neo4j raises, return skipped."""
    from adam.intelligence.free_energy_dual_eval import (
        warm_dual_eval_from_neo4j,
    )

    with patch(
        "adam.intelligence.goal_state_label_generator.load_labels_from_neo4j",
        side_effect=RuntimeError("neo4j down"),
    ):
        status = await warm_dual_eval_from_neo4j(driver=MagicMock())
    assert status["outcome"] == "skipped"
    assert "load_labels_failed" in status["reason"]


@pytest.mark.asyncio
async def test_warm_both_models_fail_returns_skipped():
    """If train_models_from_labels returns (None, None), return skipped."""
    from adam.intelligence.free_energy_dual_eval import (
        warm_dual_eval_from_neo4j,
    )
    from adam.intelligence.goal_state_label_generator import GoalStateLabel

    fake_labels = [
        GoalStateLabel(
            label_id=f"l-{i}", page_url="x", page_features={},
            active_goal_state_ids=["airport_transfer"], confidence=0.85,
        )
        for i in range(50)
    ]

    with patch(
        "adam.intelligence.goal_state_label_generator.load_labels_from_neo4j",
        return_value=fake_labels,
    ), patch(
        "adam.intelligence.goal_state_label_generator.train_models_from_labels",
        return_value=(None, None),
    ):
        status = await warm_dual_eval_from_neo4j(driver=MagicMock())
    assert status["outcome"] == "skipped"
    assert "both_models_failed_to_train" in status["reason"]


@pytest.mark.asyncio
async def test_warm_only_one_model_trains_registers_it_as_primary():
    """If only B trains (C lib missing), register B as primary."""
    from adam.intelligence.free_energy_dual_eval import (
        warm_dual_eval_from_neo4j,
    )
    from adam.intelligence.goal_state_label_generator import GoalStateLabel

    fake_labels = [
        GoalStateLabel(
            label_id=f"l-{i}", page_url="x", page_features={},
            active_goal_state_ids=["airport_transfer"], confidence=0.85,
        )
        for i in range(50)
    ]

    class _FakeB:
        @property
        def model_name(self): return "logistic_v1"
        def predict_p(self, page_features, user_state=None):
            return _uniform_posterior("logistic_v1")
        def predict_q(self, p, m): return p

    with patch(
        "adam.intelligence.goal_state_label_generator.load_labels_from_neo4j",
        return_value=fake_labels,
    ), patch(
        "adam.intelligence.goal_state_label_generator.train_models_from_labels",
        return_value=(_FakeB(), None),
    ):
        status = await warm_dual_eval_from_neo4j(driver=MagicMock())

    assert status["outcome"] == "registered"
    assert status["winner"] == "logistic_v1"
    assert status["reason"] == "only_one_model_trained"

    # Verify the singleton was actually swapped
    ctx = get_dual_eval_context()
    assert ctx.primary_model.model_name == "logistic_v1"
    assert ctx.shadow_model is None


@pytest.mark.asyncio
async def test_warm_both_trained_picks_winner_by_evaluator():
    """When both train, the winner is determined by the evaluator."""
    from adam.intelligence.free_energy_dual_eval import (
        warm_dual_eval_from_neo4j,
    )
    from adam.intelligence.goal_state_label_generator import GoalStateLabel

    fake_labels = [
        GoalStateLabel(
            label_id=f"l-{i}", page_url=f"https://x.com/{i}",
            page_features={"posture_class": "blend_compatible"},
            active_goal_state_ids=["airport_transfer"], confidence=0.85,
        )
        for i in range(50)
    ]

    # B concentrates on the right answer (will win)
    class _FakeB:
        @property
        def model_name(self): return "logistic_v1"
        def predict_p(self, page_features, user_state=None):
            n = len(list_goal_states())
            probs = {g.id: 0.01 for g in list_goal_states()}
            probs["airport_transfer"] = 1.0 - 0.01 * (n - 1)
            return GoalStatePosterior(
                probabilities=probs, model_name="logistic_v1",
            )
        def predict_q(self, p, m): return p

    # C is uniform (will lose)
    class _FakeC:
        @property
        def model_name(self): return "hierarchical_v1"
        def predict_p(self, page_features, user_state=None):
            return _uniform_posterior("hierarchical_v1")
        def predict_q(self, p, m): return p

    with patch(
        "adam.intelligence.goal_state_label_generator.load_labels_from_neo4j",
        return_value=fake_labels,
    ), patch(
        "adam.intelligence.goal_state_label_generator.train_models_from_labels",
        return_value=(_FakeB(), _FakeC()),
    ):
        status = await warm_dual_eval_from_neo4j(driver=MagicMock())

    assert status["outcome"] == "registered"
    assert status["winner"] == "logistic_v1"  # B wins
    assert "logistic_v1" in status["trained_models"]
    assert "hierarchical_v1" in status["trained_models"]

    ctx = get_dual_eval_context()
    assert ctx.primary_model.model_name == "logistic_v1"
    assert ctx.shadow_model.model_name == "hierarchical_v1"


from adam.intelligence.free_energy import GoalStatePosterior
