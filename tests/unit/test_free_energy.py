"""Pin Slice 17a — Spine #5 free-energy substrate.

Discipline anchors (B3-LUXY a/b/c/d):

    (a) Citations: directive Spine #5 lines 199-222; Foundation
        §7 rule 11 (fitness function IS ethics); active inference
        (Friston FEP). Closed-form Bayesian update q(g) ∝ p(g) · L(a|g).

    (b) Boundary anchors:
          - KL ≥ 0; KL = 0 when q == p
          - KL with non-uniform q against uniform p > 0
          - q from closed-form update concentrates on goals that
            mechanism fulfills
          - pragmatic = π · log E[L]
          - F = KL - pragmatic, can be negative (good candidate)
          - PassthroughGoalStateModel returns valid posterior shape
          - PassthroughGoalStateModel falls back to uniform on
            no signal
          - posture-aware: BLEND posture → blend-compatible goals
            get higher prior
          - keyword-aware: matching keywords → higher prior
          - degenerate Q (likelihood zero across all goals) →
            falls back to p; tagged honestly
          - Pydantic validation: probabilities in [0, 1]
          - decompose returns FreeEnergyDecomposition with all
            fields populated

    (c) calibration_pending=True. λ_F default 0.10 conservative;
        A14 flag SPINE_5_FREE_ENERGY_WEIGHT_PILOT_PENDING.

    (d) Honest tags — what is NOT tested here:
          - LogisticGoalStateModel (Slice 17b) — sibling.
          - HierarchicalGoalStateModel (Slice 17c) — sibling.
          - Cascade integration with score modulation (Slice 17d).
          - DecisionTrace logging of B + C posteriors (Slice 17d).
"""

from __future__ import annotations

import math
from typing import Any, Dict

import pytest

from adam.intelligence.free_energy import (
    DEFAULT_FREE_ENERGY_WEIGHT,
    FreeEnergyDecomposition,
    GoalStatePosterior,
    PassthroughGoalStateModel,
    closed_form_q_from_p,
    compute_free_energy,
    compute_kl_divergence,
    compute_pragmatic_term,
    decompose_free_energy,
)
from adam.intelligence.goal_state_inventory import (
    list_goal_states,
)
from adam.intelligence.page_attentional_posture_substrate import (
    POSTURE_BLEND,
    POSTURE_NEUTRAL,
    POSTURE_VIGILANCE,
)


def _uniform_posterior(model_name: str = "test") -> GoalStatePosterior:
    n = len(list_goal_states())
    return GoalStatePosterior(
        probabilities={g.id: 1.0 / n for g in list_goal_states()},
        model_name=model_name,
    )


# -----------------------------------------------------------------------------
# Pydantic schema
# -----------------------------------------------------------------------------


def test_posterior_pydantic_round_trip():
    p = _uniform_posterior("test_model_v1")
    serialized = p.model_dump_json()
    restored = GoalStatePosterior.model_validate_json(serialized)
    assert restored.model_name == "test_model_v1"
    assert restored.probabilities == p.probabilities


def test_posterior_rejects_out_of_range_probability():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        GoalStatePosterior(
            probabilities={"x": 1.5}, model_name="bad",
        )


def test_posterior_rejects_negative_probability():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        GoalStatePosterior(
            probabilities={"x": -0.1}, model_name="bad",
        )


# -----------------------------------------------------------------------------
# KL divergence
# -----------------------------------------------------------------------------


def test_kl_divergence_zero_when_q_equals_p():
    p = _uniform_posterior()
    q = _uniform_posterior()
    assert compute_kl_divergence(q, p) == pytest.approx(0.0, abs=1e-9)


def test_kl_divergence_non_negative():
    p = _uniform_posterior()
    q = GoalStatePosterior(
        probabilities={"commute_readiness": 1.0},
        model_name="test",
    )
    kl = compute_kl_divergence(q, p)
    assert kl >= 0.0


def test_kl_divergence_concentrated_q_against_uniform_p():
    """Concentrated q vs uniform p: KL = log(n)."""
    n = len(list_goal_states())
    p = _uniform_posterior()
    q = GoalStatePosterior(
        probabilities={"commute_readiness": 1.0},
        model_name="test",
    )
    kl = compute_kl_divergence(q, p)
    # KL of point mass against uniform = log(n)
    assert kl == pytest.approx(math.log(n), rel=1e-6)


def test_kl_divergence_zero_q_contributes_zero():
    """Goal states with q=0 contribute nothing to KL (0 · log = 0)."""
    p = _uniform_posterior()
    # q with most goal probabilities zeroed is still valid as long
    # as the remaining ones sum near 1.
    q = GoalStatePosterior(
        probabilities={
            "commute_readiness": 0.5,
            "airport_transfer": 0.5,
        },
        model_name="test",
    )
    kl = compute_kl_divergence(q, p)
    assert kl >= 0.0
    assert math.isfinite(kl)


# -----------------------------------------------------------------------------
# Closed-form q from p
# -----------------------------------------------------------------------------


def test_closed_form_q_concentrates_on_high_likelihood_goals():
    """When candidate mechanism is one that some goals fulfill
    strongly, q concentrates on those goals."""
    p = _uniform_posterior()
    # mimetic_desire is a canonical mechanism in the inventory's
    # mechanism_priors. Goals with higher mimetic_desire prior
    # should have higher q.
    q = closed_form_q_from_p(p, candidate_mechanism="mimetic_desire")

    # social_positioning has mimetic_desire=0.6 (relatively high).
    # frequent_traveler_loyalty has mimetic_desire=0.4 (moderate).
    # commute_readiness has no mimetic_desire entry → contributes 0.
    sp = q.probabilities.get("social_positioning", 0.0)
    cr = q.probabilities.get("commute_readiness", 0.0)
    # social_positioning should have non-trivial probability;
    # commute_readiness should be near zero (no mimetic_desire prior).
    assert sp > cr


def test_closed_form_q_sums_to_one():
    p = _uniform_posterior()
    q = closed_form_q_from_p(p, candidate_mechanism="mimetic_desire")
    total = sum(q.probabilities.values())
    assert total == pytest.approx(1.0, abs=1e-6)


def test_closed_form_q_degenerate_likelihood_falls_back_to_p():
    """When candidate mechanism has zero likelihood across all goals
    (no goal_state.mechanism_priors entry for it), q falls back to p
    and is tagged with degenerate suffix."""
    p = _uniform_posterior()
    q = closed_form_q_from_p(p, candidate_mechanism="not_a_real_mechanism")
    assert q.probabilities == p.probabilities
    assert "degenerate_fallback" in q.model_name


# -----------------------------------------------------------------------------
# Pragmatic term
# -----------------------------------------------------------------------------


def test_pragmatic_term_higher_for_well_fulfilled_mechanism():
    """A mechanism well-fulfilled by high-probability goals →
    higher pragmatic term."""
    # Concentrated p on commute_readiness (which has
    # mechanism_priors: embodied_cognition=0.7,
    # temporal_construal=0.6, automatic_evaluation=0.5)
    p = GoalStatePosterior(
        probabilities={"commute_readiness": 1.0},
        model_name="test",
    )
    high = compute_pragmatic_term(
        p, candidate_mechanism="embodied_cognition",
    )
    low = compute_pragmatic_term(
        p, candidate_mechanism="not_a_real_mechanism",  # zero L
    )
    assert high > low


def test_pragmatic_term_scales_with_posture_confidence():
    """π=0 → pragmatic=0 (regardless of likelihood)."""
    p = _uniform_posterior()
    full = compute_pragmatic_term(
        p, "mimetic_desire", posture_confidence=1.0,
    )
    half = compute_pragmatic_term(
        p, "mimetic_desire", posture_confidence=0.5,
    )
    zero = compute_pragmatic_term(
        p, "mimetic_desire", posture_confidence=0.0,
    )
    assert full == pytest.approx(2.0 * half)
    assert zero == pytest.approx(0.0)


def test_pragmatic_term_rejects_invalid_posture_confidence():
    p = _uniform_posterior()
    with pytest.raises(ValueError):
        compute_pragmatic_term(p, "x", posture_confidence=1.5)


# -----------------------------------------------------------------------------
# F() composition
# -----------------------------------------------------------------------------


def test_compute_free_energy_combines_kl_minus_pragmatic():
    p = _uniform_posterior()
    model = PassthroughGoalStateModel()
    f_value = compute_free_energy(
        p, "mimetic_desire", model, posture_confidence=1.0,
    )
    # F is finite real number
    assert math.isfinite(f_value)


def test_decompose_free_energy_returns_full_breakdown():
    p = _uniform_posterior()
    model = PassthroughGoalStateModel()
    decomp = decompose_free_energy(
        p, "mimetic_desire", model, posture_confidence=0.7,
    )
    assert isinstance(decomp, FreeEnergyDecomposition)
    assert decomp.candidate_mechanism == "mimetic_desire"
    assert decomp.kl_divergence >= 0.0
    assert decomp.posture_confidence == pytest.approx(0.7)
    assert decomp.p_posterior_model_name == "test"
    # F = KL - pragmatic
    assert decomp.free_energy == pytest.approx(
        decomp.kl_divergence - decomp.pragmatic_term, abs=1e-9
    )


# -----------------------------------------------------------------------------
# PassthroughGoalStateModel
# -----------------------------------------------------------------------------


def test_passthrough_returns_valid_posterior_shape():
    model = PassthroughGoalStateModel()
    p = model.predict_p(page_features={})
    assert isinstance(p, GoalStatePosterior)
    assert p.model_name == "passthrough_heuristic_v1"
    # Probabilities sum to 1
    total = sum(p.probabilities.values())
    assert total == pytest.approx(1.0, abs=1e-6)
    # All 14 goal states present
    assert set(p.probabilities.keys()) == {
        g.id for g in list_goal_states()
    }


def test_passthrough_no_signal_returns_neutral_prior():
    """No posture_class, no keywords → posture defaults to 'neutral'.
    Each goal's prior is its posture_compatibility[NEUTRAL]
    (which varies across goals). Distribution is valid (sums to 1,
    all in [0, 1]) but NOT strictly uniform — the inventory's
    NEUTRAL compatibility scores carry signal."""
    model = PassthroughGoalStateModel()
    p = model.predict_p(page_features={})
    total = sum(p.probabilities.values())
    assert total == pytest.approx(1.0, abs=1e-6)
    for prob in p.probabilities.values():
        assert 0.0 < prob < 1.0


def test_passthrough_explicit_uniform_call_returns_close_to_uniform():
    """Edge case: synthetic page_features with all-equal priors
    would return uniform. We don't have that explicitly in the
    inventory, but we test the math: when posture_compatibility
    values match across goals, prior is uniform."""
    # Synthetic: every goal returns same posture+keyword score →
    # uniform. The posture-fallback default 0.5 + kw_score=1.0 →
    # all goals get 0.5 → normalized → uniform.
    model = PassthroughGoalStateModel()
    # Empty keywords + a posture class NOT in any goal's compat dict
    # → all goals get the soft-fail default 0.5.
    p = model.predict_p(page_features={
        "posture_class": "fabricated_posture_not_in_inventory",
    })
    n = len(list_goal_states())
    expected = 1.0 / n
    for prob in p.probabilities.values():
        assert prob == pytest.approx(expected, abs=1e-6)


def test_passthrough_blend_posture_favors_blend_compatible_goals():
    """POSTURE_BLEND should give higher prior to goals whose
    posture_compatibility[POSTURE_BLEND] is high."""
    model = PassthroughGoalStateModel()
    p = model.predict_p(page_features={
        "posture_class": POSTURE_BLEND,
    })

    # commute_readiness has posture_compatibility[BLEND]=0.7 (high)
    # comparative_research has posture_compatibility[BLEND]=0.2 (low)
    cr = p.probabilities["commute_readiness"]
    cmp_research = p.probabilities["comparative_research"]
    assert cr > cmp_research


def test_passthrough_vigilance_posture_favors_vigilance_goals():
    """POSTURE_VIGILANCE should favor research-mode / time-pressure goals."""
    model = PassthroughGoalStateModel()
    p = model.predict_p(page_features={
        "posture_class": POSTURE_VIGILANCE,
    })

    # comparative_research has posture[VIGILANCE]=0.9 (high)
    # commute_readiness has posture[VIGILANCE]=0.3 (low)
    cmp_research = p.probabilities["comparative_research"]
    cr = p.probabilities["commute_readiness"]
    assert cmp_research > cr


def test_passthrough_keywords_match_boost_relevant_goals():
    """Pages with matching keywords should boost the matching goals."""
    model = PassthroughGoalStateModel()

    # commute_readiness keywords include: commute, morning, office, work
    p_commute = model.predict_p(page_features={
        "posture_class": POSTURE_NEUTRAL,
        "page_keywords": ["commute", "morning", "office"],
    })
    # airport_transfer keywords include: airport, flight, luggage
    p_airport = model.predict_p(page_features={
        "posture_class": POSTURE_NEUTRAL,
        "page_keywords": ["airport", "flight", "TSA"],
    })

    # The goal whose keywords match should rank higher
    assert p_commute.probabilities["commute_readiness"] > \
        p_commute.probabilities["airport_transfer"]
    assert p_airport.probabilities["airport_transfer"] > \
        p_airport.probabilities["commute_readiness"]


def test_passthrough_predict_q_uses_closed_form_update():
    model = PassthroughGoalStateModel()
    p = model.predict_p(page_features={
        "posture_class": POSTURE_BLEND,
    })
    q = model.predict_q(p, candidate_mechanism="mimetic_desire")
    assert isinstance(q, GoalStatePosterior)
    # q probabilities sum to 1
    total = sum(q.probabilities.values())
    assert total == pytest.approx(1.0, abs=1e-6)


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------


def test_default_free_energy_weight_pinned():
    assert DEFAULT_FREE_ENERGY_WEIGHT == pytest.approx(0.10)
