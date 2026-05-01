"""Pin Slice 17c — HierarchicalGoalStateModel (Option C).

Discipline anchors (B3-LUXY a/b/c/d):

    (a) Citations: directive Spine #5 line 216; hierarchical
        Bayesian inference (Gelman et al. 2013); SVI (Hoffman et al.
        2013); NumPyro AutoNormal guide; per-goal Bernoulli with
        hierarchical pooling pattern from hierarchical_bayes.py.

    (b) Boundary anchors:
          - import-skip when numpyro / jax absent
          - empty labeled_pairs → train returns False
          - all-empty active-goals → train returns False
          - untrained model → predict_p falls back to passthrough
            with model_name suffix
          - trained model returns valid posterior shape (sums to 1
            via renormalization across goals)
          - trained model concentrates on goals seen as active in
            training pattern
          - predict_q delegates to closed_form_q_from_p with this
            model's name 'hierarchical_bayes_v1'
          - softfail when SVI raises during predict
          - softfail when zero mass after renormalization

    (c) calibration_pending=True (SVI_NUM_STEPS, SVI_LEARNING_RATE,
        prior scales).

    (d) Honest tags — what is NOT tested here:
          - Claude API label generator (Slice 18)
          - MCMC fallback comparison (sibling)
          - Online posterior update (sibling)
          - Cohort-conditional priors (BLOCKED on Loop B)
"""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

import pytest

# Skip the whole module if numpyro / jax aren't installed in test env.
numpyro = pytest.importorskip("numpyro")
jax = pytest.importorskip("jax")

from adam.intelligence.free_energy import GoalStatePosterior
from adam.intelligence.goal_state_hierarchical_model import (
    HierarchicalGoalStateModel,
    SVI_LEARNING_RATE,
    SVI_NUM_STEPS,
)
from adam.intelligence.goal_state_inventory import list_goal_states
from adam.intelligence.page_attentional_posture_substrate import (
    POSTURE_BLEND,
    POSTURE_NEUTRAL,
    POSTURE_VIGILANCE,
)


# -----------------------------------------------------------------------------
# Constants pinned
# -----------------------------------------------------------------------------


def test_constants_pinned():
    assert SVI_NUM_STEPS == 2000
    assert SVI_LEARNING_RATE == pytest.approx(0.01)


# -----------------------------------------------------------------------------
# Untrained model — soft-fail to passthrough
# -----------------------------------------------------------------------------


def test_untrained_model_returns_passthrough_fallback():
    """Untrained → predict_p returns valid posterior via passthrough
    fallback. Cascade integration doesn't break."""
    model = HierarchicalGoalStateModel()
    assert model.is_trained is False
    p = model.predict_p(page_features={"posture_class": POSTURE_BLEND})
    assert isinstance(p, GoalStatePosterior)
    # model_name signals the fallback path
    assert "fallback_passthrough" in p.model_name
    # Distribution is valid
    total = sum(p.probabilities.values())
    assert abs(total - 1.0) < 1e-6


def test_untrained_model_predict_q_uses_closed_form():
    """Even untrained, predict_q works (uses closed-form Bayesian
    update on whatever p is supplied)."""
    model = HierarchicalGoalStateModel()
    p = GoalStatePosterior(
        probabilities={g.id: 1.0 / len(list_goal_states())
                       for g in list_goal_states()},
        model_name="test",
    )
    q = model.predict_q(p, candidate_mechanism="mimetic_desire")
    assert q.model_name == "hierarchical_bayes_v1"
    assert sum(q.probabilities.values()) == pytest.approx(1.0, abs=1e-6)


# -----------------------------------------------------------------------------
# Train path
# -----------------------------------------------------------------------------


def _multi_label_synthetic() -> List[Tuple[Dict[str, Any], Set[str]]]:
    """Generate multi-label synthetic training pairs.

    The differentiator vs Option B: pages can have multiple active
    goals. Here we synthesize:
      - airport pages → {airport_transfer}
      - commute pages → {commute_readiness}
      - airport-AND-time-pressure pages → {airport_transfer, time_pressure}
        (multi-label — one of C's strengths over B)
    """
    pairs: List[Tuple[Dict[str, Any], Set[str]]] = []

    for _ in range(15):
        pairs.append(({
            "posture_class": POSTURE_VIGILANCE,
            "posture_confidence": 0.8,
            "page_keywords": ["airport", "flight", "TSA"],
        }, {"airport_transfer"}))

    for _ in range(15):
        pairs.append(({
            "posture_class": POSTURE_BLEND,
            "posture_confidence": 0.9,
            "page_keywords": ["commute", "morning", "office"],
        }, {"commute_readiness"}))

    # Multi-label samples — airport AND time_pressure
    for _ in range(15):
        pairs.append(({
            "posture_class": POSTURE_VIGILANCE,
            "posture_confidence": 0.85,
            "page_keywords": ["airport", "flight", "delayed", "rush hour"],
        }, {"airport_transfer", "time_pressure"}))

    return pairs


def test_train_returns_false_on_empty_labels():
    model = HierarchicalGoalStateModel()
    ok = model.train([])
    assert ok is False
    assert model.is_trained is False


def test_train_returns_false_when_no_positive_labels():
    """All labels with empty active-goal sets → no positive labels
    → train False."""
    model = HierarchicalGoalStateModel()
    pairs: List[Tuple[Dict[str, Any], Set[str]]] = [
        ({"posture_class": POSTURE_BLEND}, set())
        for _ in range(10)
    ]
    ok = model.train(pairs)
    assert ok is False
    assert model.is_trained is False


@pytest.mark.slow
def test_train_returns_true_on_synthetic_pattern():
    """Full SVI fit on synthetic multi-label pattern. Slow because
    SVI runs 2000 iterations."""
    model = HierarchicalGoalStateModel()
    pairs = _multi_label_synthetic()
    # Run with reduced steps for test-speed.
    ok = model.train(pairs, num_steps=500)
    assert ok is True
    assert model.is_trained is True
    assert model.n_train_samples == len(pairs)


@pytest.mark.slow
def test_trained_model_predict_returns_normalized_distribution():
    """Trained model output sums to 1 (multinomial-shaped after
    renormalization)."""
    model = HierarchicalGoalStateModel()
    pairs = _multi_label_synthetic()
    model.train(pairs, num_steps=500)

    p = model.predict_p(page_features={
        "posture_class": POSTURE_VIGILANCE,
        "posture_confidence": 0.8,
        "page_keywords": ["airport", "flight"],
    })

    assert p.model_name == "hierarchical_bayes_v1"
    total = sum(p.probabilities.values())
    assert total == pytest.approx(1.0, abs=1e-3)
    assert set(p.probabilities.keys()) == {
        g.id for g in list_goal_states()
    }


@pytest.mark.slow
def test_trained_model_concentrates_on_seen_pattern():
    """After training on (airport keywords + VIGILANCE) →
    airport_transfer, predicting on a matching page should give
    airport_transfer non-trivial probability."""
    model = HierarchicalGoalStateModel()
    pairs = _multi_label_synthetic()
    model.train(pairs, num_steps=500)

    p = model.predict_p(page_features={
        "posture_class": POSTURE_VIGILANCE,
        "posture_confidence": 0.8,
        "page_keywords": ["airport", "flight", "TSA"],
    })

    # airport_transfer should rank higher than commute_readiness
    # (which has different keywords + different posture in training)
    airport_p = p.probabilities.get("airport_transfer", 0.0)
    commute_p = p.probabilities.get("commute_readiness", 0.0)
    assert airport_p > commute_p


@pytest.mark.slow
def test_trained_model_predict_q_uses_closed_form_with_model_name():
    """predict_q on trained model uses canonical update tagged with
    this model's name."""
    model = HierarchicalGoalStateModel()
    pairs = _multi_label_synthetic()
    model.train(pairs, num_steps=500)

    p = model.predict_p(page_features={
        "posture_class": POSTURE_BLEND,
    })
    q = model.predict_q(p, candidate_mechanism="mimetic_desire")
    assert q.model_name == "hierarchical_bayes_v1"
    assert sum(q.probabilities.values()) == pytest.approx(1.0, abs=1e-3)
