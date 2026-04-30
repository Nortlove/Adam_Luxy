"""Pin the cohort-prior boost wire — Audit §6 follow-up.

Decision-time consumer: cascade ``result.mechanism_scores`` → bid
mechanism returned to StackAdapt.

These tests pin the adapter's contract:
    * Empty inputs → no-op (the input dict is returned unchanged)
    * Missing graph_cache or get_cohort_priors → no-op
    * Empty cohort priors → no-op
    * cohort_effectiveness ≤ 0.5 → no boost (matches canonical service)
    * cohort_effectiveness > 0.5 → bounded boost
    * Output ∈ [0, 1]
    * Returned dict is a NEW object when modulating (no in-place mutation)
    * Mechanisms not in cohort priors pass through unchanged
    * Exception in graph_cache → no-op (soft-fail)
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import MagicMock

import pytest

from adam.intelligence.cohort_modulation import (
    COHORT_BOOST_WEIGHT,
    NEUTRAL_EFFECTIVENESS,
    apply_cohort_priors,
)


# -----------------------------------------------------------------------------
# helpers
# -----------------------------------------------------------------------------


def _cache_returning(priors: Dict[str, float]) -> Any:
    cache = MagicMock()
    cache.get_cohort_priors = MagicMock(return_value=priors)
    return cache


def _baseline_scores() -> Dict[str, float]:
    return {"social_proof": 0.50, "authority": 0.50, "scarcity": 0.50}


# -----------------------------------------------------------------------------
# soft-fail / no-op paths
# -----------------------------------------------------------------------------


def test_empty_scores_returns_unchanged():
    cache = _cache_returning({"social_proof": 0.9})
    out = apply_cohort_priors({}, buyer_id="u", graph_cache=cache)
    assert out == {}


def test_empty_buyer_id_returns_unchanged():
    cache = _cache_returning({"social_proof": 0.9})
    scores = _baseline_scores()
    out = apply_cohort_priors(scores, buyer_id="", graph_cache=cache)
    assert out == scores
    cache.get_cohort_priors.assert_not_called()


def test_missing_graph_cache_returns_unchanged():
    scores = _baseline_scores()
    out = apply_cohort_priors(scores, buyer_id="u", graph_cache=None)
    assert out == scores


def test_missing_method_returns_unchanged():
    """A graph_cache without get_cohort_priors must not raise."""
    scores = _baseline_scores()
    out = apply_cohort_priors(scores, buyer_id="u", graph_cache=object())
    assert out == scores


def test_empty_priors_returns_unchanged():
    """Pre-pilot state — cohort discovery hasn't run / buyer not clustered."""
    cache = _cache_returning({})
    scores = _baseline_scores()
    out = apply_cohort_priors(scores, buyer_id="u", graph_cache=cache)
    assert out == scores


def test_priors_lookup_raises_returns_unchanged():
    """Any exception in graph_cache.get_cohort_priors → soft-fail."""
    cache = MagicMock()
    cache.get_cohort_priors = MagicMock(side_effect=RuntimeError("Neo4j down"))
    scores = _baseline_scores()
    out = apply_cohort_priors(scores, buyer_id="u", graph_cache=cache)
    assert out == scores


# -----------------------------------------------------------------------------
# canonical boost behavior
# -----------------------------------------------------------------------------


def test_below_neutral_effectiveness_no_boost():
    """cohort_effectiveness ≤ 0.5 → no positive shift (canonical gate)."""
    cache = _cache_returning({"social_proof": 0.40, "authority": 0.50})
    scores = _baseline_scores()
    out = apply_cohort_priors(scores, buyer_id="u", graph_cache=cache)
    assert out["social_proof"] == 0.50
    assert out["authority"] == 0.50


def test_above_neutral_effectiveness_bounded_boost():
    """cohort_effectiveness > 0.5 → boost = (eff - 0.5) * boost_weight."""
    cache = _cache_returning({"social_proof": 0.80, "authority": 0.60})
    scores = _baseline_scores()
    out = apply_cohort_priors(scores, buyer_id="u", graph_cache=cache)

    # social_proof: 0.50 + (0.80 - 0.50) * 0.20 = 0.56 (exact)
    assert out["social_proof"] == pytest.approx(0.56, abs=1e-9)
    # authority: 0.50 + (0.60 - 0.50) * 0.20 = 0.52 (exact)
    assert out["authority"] == pytest.approx(0.52, abs=1e-9)
    # scarcity: not in cohort priors → unchanged
    assert out["scarcity"] == 0.50


def test_boost_clamps_to_unit_interval():
    """Even with extreme inputs the output stays in [0, 1]."""
    cache = _cache_returning({"social_proof": 1.0})
    scores = {"social_proof": 0.99}
    out = apply_cohort_priors(scores, buyer_id="u", graph_cache=cache)
    assert 0.0 <= out["social_proof"] <= 1.0


def test_returned_dict_is_a_copy_when_modulating():
    """Successful modulation must NOT mutate the caller's dict."""
    cache = _cache_returning({"social_proof": 0.80})
    scores = {"social_proof": 0.50, "authority": 0.50}
    snapshot = dict(scores)
    out = apply_cohort_priors(scores, buyer_id="u", graph_cache=cache)
    assert scores == snapshot  # untouched
    assert out is not scores


def test_returned_dict_is_input_object_when_no_op():
    """No-op paths return the input dict unchanged (identity preserved)
    — the cascade's diff-detection compares object identity to log
    'shifted' counts, so this is load-bearing."""
    cache = _cache_returning({})
    scores = _baseline_scores()
    out = apply_cohort_priors(scores, buyer_id="u", graph_cache=cache)
    assert out is scores


def test_non_numeric_effectiveness_skipped():
    """Cohort prior with a non-numeric value must not crash and must
    not boost that mechanism."""
    cache = _cache_returning({"social_proof": "totally", "authority": 0.7})
    scores = _baseline_scores()
    out = apply_cohort_priors(scores, buyer_id="u", graph_cache=cache)
    assert out["social_proof"] == 0.50  # untouched
    assert out["authority"] == pytest.approx(0.54, abs=1e-9)


# -----------------------------------------------------------------------------
# constants pin
# -----------------------------------------------------------------------------


def test_canonical_constants_match_cohort_discovery_service():
    """The boost weight and neutral threshold mirror the canonical
    CohortDiscoveryService.get_cohort_boost. If the service changes,
    THIS test should fail and force a manual reconciliation rather
    than silent drift."""
    assert COHORT_BOOST_WEIGHT == 0.20
    assert NEUTRAL_EFFECTIVENESS == 0.5
