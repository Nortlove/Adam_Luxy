"""Pin the regret-weighted rank wire — Audit Item 11 (bounded piece).

Decision-time consumer: cascade ``result.mechanism_scores`` after
this call feeds the M1 ε-floor sampler → bid mechanism returned to
StackAdapt.

These tests pin:
    * Empty inputs → no-op (identity preserved)
    * Penalty-weight ≤ 0 → no-op
    * Cialdini name with NO atom translation → passthrough
    * Cialdini name → atom NOT in MECHANISM_TAXONOMY → passthrough
    * Known-regret mechanism → penalized (graded by prior)
    * Output ∈ [0, 1]
    * Returned dict is a NEW object when modulating; input dict is
      returned (identity) on pure no-op
    * High-regret atom (attention_dynamics, prior=0.70) gets larger
      penalty than low-regret atom (embodied_cognition, prior=0.15)
    * Default penalty weight produces bounded penalties (max ~14%)
"""

from __future__ import annotations

from typing import Dict

import pytest

from adam.intelligence.regret_weighted_ranking import (
    REGRET_PENALTY_WEIGHT_DEFAULT,
    apply_regret_weighted_ranking,
)


# -----------------------------------------------------------------------------
# helpers
# -----------------------------------------------------------------------------


def _baseline_scores() -> Dict[str, float]:
    # Mix of mechanisms whose atom-translations cover the full prior range.
    return {
        "social_proof": 0.50,        # → social_proof atom (NOT in taxonomy → passthrough)
        "scarcity": 0.50,             # → scarcity atom (NOT in taxonomy → passthrough)
        "loss_aversion": 0.50,        # → temporal_construal (BLEND, prior=0.20)
        "authority": 0.50,            # → identity_construction (VIGILANCE, prior=0.50)
        "curiosity": 0.50,            # → attention_dynamics (VIGILANCE, prior=0.70)
        "liking": 0.50,               # → mimetic_desire (BLEND, prior=0.20)
        "cognitive_ease": 0.50,       # → attention_dynamics (VIGILANCE, prior=0.70)
    }


# -----------------------------------------------------------------------------
# soft-fail / no-op paths
# -----------------------------------------------------------------------------


def test_empty_scores_returns_unchanged():
    out = apply_regret_weighted_ranking({})
    assert out == {}


def test_zero_penalty_weight_returns_unchanged():
    scores = _baseline_scores()
    out = apply_regret_weighted_ranking(scores, penalty_weight=0.0)
    assert out is scores  # identity preserved


def test_negative_penalty_weight_returns_unchanged():
    scores = _baseline_scores()
    out = apply_regret_weighted_ranking(scores, penalty_weight=-0.5)
    assert out is scores


def test_unknown_cialdini_name_passes_through():
    """Cialdini name not in MECHANISM_TO_ATOM is left unchanged."""
    fake_mech = "this_mech_is_not_in_the_translation_map"
    scores = {fake_mech: 0.50}
    out = apply_regret_weighted_ranking(scores)
    assert out is scores  # full no-op
    assert out[fake_mech] == 0.50


def test_atom_not_in_taxonomy_passes_through():
    """social_proof and scarcity translate to atoms NOT in taxonomy
    — they pass through unchanged."""
    scores = {"social_proof": 0.5, "scarcity": 0.5}
    out = apply_regret_weighted_ranking(scores)
    # Both atoms are not in MECHANISM_TAXONOMY → no shift on either
    assert out["social_proof"] == 0.5
    assert out["scarcity"] == 0.5


# -----------------------------------------------------------------------------
# canonical penalty behavior
# -----------------------------------------------------------------------------


def test_high_regret_mechanism_penalized_more_than_low_regret():
    """attention_dynamics (prior=0.70) takes larger discount than
    mimetic_desire (prior=0.20)."""
    scores = {"curiosity": 0.50, "liking": 0.50}
    # curiosity → attention_dynamics, prior=0.70
    # liking → mimetic_desire, prior=0.20
    out = apply_regret_weighted_ranking(scores)
    curiosity_penalty = 0.50 - out["curiosity"]
    liking_penalty = 0.50 - out["liking"]
    assert curiosity_penalty > liking_penalty


def test_default_weight_max_penalty_is_bounded():
    """Highest regret prior is 0.70 (attention_dynamics). At default
    weight 0.20, max discount = 0.70 * 0.20 = 14%. A 0.50 score gets
    at most 0.50 * 0.14 = 0.07 absolute penalty."""
    scores = {"curiosity": 0.50}
    out = apply_regret_weighted_ranking(scores)
    penalty = 0.50 - out["curiosity"]
    expected_max = 0.50 * 0.70 * REGRET_PENALTY_WEIGHT_DEFAULT
    assert penalty == pytest.approx(expected_max, abs=1e-9)
    # Sanity: < 14% absolute on a 0.5 score
    assert penalty < 0.08


def test_score_clamps_to_unit_interval():
    """Even with high penalty weight + extreme score the output stays in [0, 1]."""
    scores = {"curiosity": 0.99}  # attention_dynamics, prior=0.70
    out = apply_regret_weighted_ranking(scores, penalty_weight=2.0)  # discount = 1.40
    # discount capped at 1.0 → score * 0 = 0; clamp keeps it ≥ 0
    assert 0.0 <= out["curiosity"] <= 1.0


def test_returned_dict_is_a_copy_when_modulating():
    """Successful modulation must NOT mutate the caller's dict."""
    scores = {"curiosity": 0.50}
    snapshot = dict(scores)
    out = apply_regret_weighted_ranking(scores)
    assert scores == snapshot  # untouched
    assert out is not scores  # new dict


def test_returned_dict_is_input_object_when_no_op():
    """No-op paths return the input dict (identity preserved) — load-bearing
    for the cascade's diff-detection that logs 'shifted' counts."""
    scores = {"social_proof": 0.5, "scarcity": 0.5}  # neither in taxonomy
    out = apply_regret_weighted_ranking(scores)
    assert out is scores


# -----------------------------------------------------------------------------
# canonical anchor — taxonomy values
# -----------------------------------------------------------------------------


def test_canonical_default_weight():
    """The default penalty weight is the documented value. If this
    test fails, mechanism_taxonomy.regret_correlation_prior values
    or REGRET_PENALTY_WEIGHT_DEFAULT changed — reconcile manually."""
    assert REGRET_PENALTY_WEIGHT_DEFAULT == 0.20
