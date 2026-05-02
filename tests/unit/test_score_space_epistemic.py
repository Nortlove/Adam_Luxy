"""Pin Slice 4 — score-space epistemic bonus modulation before TTTS.

Discipline anchors (B3-LUXY a/b/c/d) for
``adam/intelligence/score_space_epistemic.py``:

    (a) Per directive Section 5.1 Step 9 line 691:
            score → score + λ_E · epistemic
        conditioned on fluency-floor pass. Spine #8 closed-form EIG
        under BONG (lines 273-294). Slice 1's hard fluency floor
        already drops LOW posture × mechanism candidates from
        mechanism_scores, so every remaining candidate is
        fluency-passed by structural composition.

    (b) Boundary anchors pinned by these tests:
          - bonus added to score-space (modulated_score = score + λ_E·b)
          - mechanism without primary dims (unknown) → no bonus
          - empty mechanism_scores → pass-through
          - missing bong_posterior → pass-through
          - lambda_e == 0 → pass-through
          - high-precision user → low bonus (per directive line 285)
          - low-precision user → higher bonus
          - score floor / ceiling preserved [0, 1]
          - per_mechanism_bonus dict populated for diagnostics
          - total_bonus_mass tracks aggregate score shift
          - EpistemicScoreModResult is frozen
          - observation_precision_for_mechanism returns None for
            unknown mechanism, ndarray for known mechanism

    (c) calibration_pending=True. DEFAULT_LAMBDA_E=0.05 conservative
        pre-pilot. A14 flag.

    (d) Honest tags — what is NOT tested here:
          - Cohort-budget cap (Spine #7 BLOCKED on Loop B; cohort
            budget kept None at this layer).
          - Edge-derived per-dim observation precision (sibling slice).
          - Cross-dimension correlation in EIG (sibling slice).
"""

from __future__ import annotations

import numpy as np
import pytest

from adam.intelligence.bong import BONGPosterior, DEFAULT_DIMENSIONS
from adam.intelligence.score_space_epistemic import (
    DEFAULT_LAMBDA_E,
    EpistemicScoreModResult,
    apply_score_space_epistemic_bonus,
    observation_precision_for_mechanism,
)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------


def _fresh_bong_posterior() -> BONGPosterior:
    """Create a fresh (low-precision, cold-buyer) BONG posterior.

    BONGPosterior schema is (eta, D) — dimension_names live on the
    BONGUpdater singleton, which the score_space_epistemic primitive
    accepts as a separate argument (defaulting to DEFAULT_DIMENSIONS).
    """
    d = len(DEFAULT_DIMENSIONS)
    return BONGPosterior(
        eta=np.zeros(d),
        D=np.full(d, 0.5),  # low precision per dim → meaningful EIG
    )


def _high_precision_bong_posterior() -> BONGPosterior:
    """High-precision (well-characterized) BONG posterior."""
    d = len(DEFAULT_DIMENSIONS)
    return BONGPosterior(
        eta=np.zeros(d),
        D=np.full(d, 100.0),  # very high precision per dim
    )


# -----------------------------------------------------------------------------
# observation_precision_for_mechanism
# -----------------------------------------------------------------------------


def test_obs_precision_known_mechanism_returns_array():
    """Known mechanism → numpy array with primary dims set."""
    bong_dims = list(DEFAULT_DIMENSIONS)
    precision = observation_precision_for_mechanism("social_proof", bong_dims)
    assert precision is not None
    assert isinstance(precision, np.ndarray)
    assert precision.shape == (len(bong_dims),)
    assert (precision > 0).any()  # at least one primary dim


def test_obs_precision_unknown_mechanism_returns_none():
    """Unknown mechanism → None (no primary dims to claim EIG over)."""
    bong_dims = list(DEFAULT_DIMENSIONS)
    precision = observation_precision_for_mechanism(
        "xyz_unknown_mechanism", bong_dims,
    )
    assert precision is None


def test_obs_precision_unit_on_primary_zero_elsewhere():
    """Default primary precision = 1.0 on primary dims, 0.0 elsewhere."""
    bong_dims = list(DEFAULT_DIMENSIONS)
    precision = observation_precision_for_mechanism(
        "regulatory_focus", bong_dims,  # primary: regulatory_fit
    )
    assert precision is not None
    # Some dims should be 1.0; others 0.0
    assert (precision == 1.0).any()
    assert (precision == 0.0).any()


# -----------------------------------------------------------------------------
# apply_score_space_epistemic_bonus
# -----------------------------------------------------------------------------


def test_apply_empty_scores_pass_through():
    """No candidates → empty result, no modulation."""
    bong = _fresh_bong_posterior()
    result = apply_score_space_epistemic_bonus(
        mechanism_scores={},
        bong_posterior=bong,
    )
    assert isinstance(result, EpistemicScoreModResult)
    assert result.modulated_scores == {}
    assert result.n_modulated == 0


def test_apply_no_posterior_pass_through():
    """No BONG posterior → input unchanged."""
    scores = {"social_proof": 0.7}
    result = apply_score_space_epistemic_bonus(
        mechanism_scores=scores,
        bong_posterior=None,
    )
    assert result.modulated_scores is scores
    assert result.n_modulated == 0


def test_apply_lambda_zero_pass_through():
    """lambda_e=0 → no modulation (explicitly disabled)."""
    bong = _fresh_bong_posterior()
    scores = {"social_proof": 0.7}
    result = apply_score_space_epistemic_bonus(
        mechanism_scores=scores,
        bong_posterior=bong,
        lambda_e=0.0,
    )
    assert result.modulated_scores is scores
    assert result.n_modulated == 0


def test_apply_low_precision_buyer_high_bonus():
    """Cold buyer (low precision) → meaningful bonus added to scores."""
    bong = _fresh_bong_posterior()
    scores = {
        "social_proof": 0.5,
        "scarcity": 0.5,
    }
    result = apply_score_space_epistemic_bonus(
        mechanism_scores=scores,
        bong_posterior=bong,
    )
    # At least one mechanism shifted (both have primary dims)
    assert result.n_modulated >= 1
    assert result.total_bonus_mass > 0.0
    # Per-mechanism bonus tracked
    assert "social_proof" in result.per_mechanism_bonus
    # Modulated score >= base (bonus is non-negative for non-degenerate
    # info gain)
    assert result.modulated_scores["social_proof"] >= 0.5


def test_apply_high_precision_buyer_low_bonus():
    """Well-characterized user → smaller bonus per directive line 285."""
    low_bong = _fresh_bong_posterior()
    high_bong = _high_precision_bong_posterior()
    scores = {"social_proof": 0.5}

    low_result = apply_score_space_epistemic_bonus(
        mechanism_scores=scores,
        bong_posterior=low_bong,
    )
    high_result = apply_score_space_epistemic_bonus(
        mechanism_scores=scores,
        bong_posterior=high_bong,
    )

    # High precision yields smaller per-mechanism bonus
    assert (
        high_result.per_mechanism_bonus.get("social_proof", 0.0)
        < low_result.per_mechanism_bonus.get("social_proof", 0.0)
    )


def test_apply_unknown_mechanism_no_bonus():
    """Unknown mechanism → score unchanged (no primary dims to claim)."""
    bong = _fresh_bong_posterior()
    scores = {"xyz_unknown": 0.6, "social_proof": 0.5}
    result = apply_score_space_epistemic_bonus(
        mechanism_scores=scores,
        bong_posterior=bong,
    )
    # xyz_unknown should not be in per_mechanism_bonus (None precision)
    assert "xyz_unknown" not in result.per_mechanism_bonus
    # And its modulated score equals input (no shift)
    assert result.modulated_scores["xyz_unknown"] == 0.6
    # social_proof should have shifted
    assert "social_proof" in result.per_mechanism_bonus


def test_apply_score_ceiling_preserved():
    """Scores at 1.0 cannot exceed 1.0 after bonus."""
    bong = _fresh_bong_posterior()
    scores = {"social_proof": 1.0}
    result = apply_score_space_epistemic_bonus(
        mechanism_scores=scores,
        bong_posterior=bong,
        lambda_e=10.0,  # large lambda — would push above ceiling
    )
    assert result.modulated_scores["social_proof"] <= 1.0


def test_apply_score_floor_preserved():
    """Scores cannot go below 0.0 (bonus is non-negative anyway, but
    defensive: lambda_e is signed in principle)."""
    bong = _fresh_bong_posterior()
    scores = {"social_proof": 0.0}
    result = apply_score_space_epistemic_bonus(
        mechanism_scores=scores,
        bong_posterior=bong,
    )
    assert result.modulated_scores["social_proof"] >= 0.0


def test_apply_returns_frozen_dataclass():
    """EpistemicScoreModResult is frozen — caller cannot mutate."""
    bong = _fresh_bong_posterior()
    result = apply_score_space_epistemic_bonus(
        mechanism_scores={"social_proof": 0.5},
        bong_posterior=bong,
    )
    with pytest.raises(Exception):  # FrozenInstanceError
        result.n_modulated = 99  # type: ignore[misc]


def test_apply_per_mechanism_bonus_populated():
    """Diagnostic dict per-mechanism populated for known mechanisms."""
    bong = _fresh_bong_posterior()
    scores = {
        "social_proof": 0.5,
        "scarcity": 0.5,
        "loss_aversion": 0.5,
    }
    result = apply_score_space_epistemic_bonus(
        mechanism_scores=scores,
        bong_posterior=bong,
    )
    assert "social_proof" in result.per_mechanism_bonus
    assert "scarcity" in result.per_mechanism_bonus
    assert "loss_aversion" in result.per_mechanism_bonus


def test_apply_default_lambda_value():
    """Default lambda_e equals DEFAULT_LAMBDA_E (calibration-pending)."""
    assert DEFAULT_LAMBDA_E == 0.05
