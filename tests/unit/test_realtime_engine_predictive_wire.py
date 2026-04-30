"""Pin the predictive-processing wire into compute_persuasion_decision.

Audit §6 follow-up: the predictive_processing engine was registered
in adam/core/container.py but no caller in realtime_decision_engine
consumed its curiosity score. This file pins:

    * The engine IS called when buyer_id is set
    * The engine is NOT called when buyer_id is empty
    * Bonuses are bounded to ±15%
    * An exception in the engine MUST NOT propagate
    * Mechanisms without primary dims in MECHANISM_DIMENSION_MAP are
      left untouched (no spurious bonus applied)

The engine's own behavior (belief-state tracking, prediction errors,
dimension precisions) is pinned by tests for predictive_processing
itself; this file pins ONLY the realtime-engine adaptation.
"""

from __future__ import annotations

from typing import Dict
from unittest.mock import MagicMock, patch

import pytest


# Tests that don't need a real Redis / impression resolver — exercise
# only the wire by patching every other dependency the function pulls.


def _patched_compute_persuasion_decision_calls_engine(buyer_id: str) -> MagicMock:
    """Run compute_persuasion_decision with everything stubbed except the
    predictive-processing engine call. Returns the engine mock so the
    caller can assert call counts."""
    from adam.intelligence import realtime_decision_engine as rde

    # Mock every external dependency
    fake_engine = MagicMock()
    fake_engine.get_curiosity_score = MagicMock(return_value=0.05)

    fake_redis_client = MagicMock()
    # Empty trend / drift hashes — Step 2b loop runs with no effect.
    fake_redis_client.hgetall = MagicMock(return_value={})

    with patch.object(
        rde, "_score_mechanisms_from_position",
        return_value={
            "social_proof": 0.7,
            "authority": 0.5,
            "scarcity": 0.4,
            "this_mech_has_no_dims_mapping": 0.3,  # unmapped → no bonus
        },
    ), patch(
        "redis.Redis", return_value=fake_redis_client,
    ), patch(
        "adam.intelligence.impression_state_resolver.resolve_reader_position",
        side_effect=Exception("skip resolver"),
    ), patch(
        "adam.intelligence.page_intelligence.get_page_intelligence_cache",
        side_effect=Exception("skip page cache"),
    ), patch(
        "adam.intelligence.daily.consumer.get_intelligence_consumer",
        side_effect=Exception("skip consumer"),
    ), patch(
        "adam.intelligence.predictive_processing.get_predictive_processing_engine",
        return_value=fake_engine,
    ):
        rde.compute_persuasion_decision(buyer_id=buyer_id)

    return fake_engine


def test_curiosity_engine_called_when_buyer_id_present():
    """A non-empty buyer_id must trigger the engine for each mapped mechanism."""
    fake_engine = _patched_compute_persuasion_decision_calls_engine(
        buyer_id="u_warm",
    )
    # Three of the four scored mechanisms (social_proof, authority, scarcity)
    # have entries in MECHANISM_DIMENSION_MAP. The fourth ("this_mech_has_no_
    # dims_mapping") should be skipped.
    assert fake_engine.get_curiosity_score.call_count == 3


def test_curiosity_engine_not_called_when_buyer_id_empty():
    """Anonymous bid (no buyer_id) → engine never invoked."""
    fake_engine = _patched_compute_persuasion_decision_calls_engine(
        buyer_id="",
    )
    fake_engine.get_curiosity_score.assert_not_called()


def test_curiosity_engine_exception_does_not_propagate():
    """An exception in the engine wire must be soft-failed."""
    from adam.intelligence import realtime_decision_engine as rde

    fake_engine = MagicMock()
    fake_engine.get_curiosity_score = MagicMock(
        side_effect=RuntimeError("engine blew up"),
    )

    fake_redis_client = MagicMock()
    fake_redis_client.hgetall = MagicMock(return_value={})

    with patch.object(
        rde, "_score_mechanisms_from_position",
        return_value={"social_proof": 0.7},
    ), patch(
        "redis.Redis", return_value=fake_redis_client,
    ), patch(
        "adam.intelligence.impression_state_resolver.resolve_reader_position",
        side_effect=Exception("skip"),
    ), patch(
        "adam.intelligence.page_intelligence.get_page_intelligence_cache",
        side_effect=Exception("skip"),
    ), patch(
        "adam.intelligence.daily.consumer.get_intelligence_consumer",
        side_effect=Exception("skip"),
    ), patch(
        "adam.intelligence.predictive_processing.get_predictive_processing_engine",
        return_value=fake_engine,
    ):
        # MUST NOT RAISE
        decision = rde.compute_persuasion_decision(buyer_id="u")

    assert decision.primary_mechanism == "social_proof"


def test_curiosity_bonus_capped_at_plus_minus_15_percent():
    """Even an extreme curiosity score must not push beyond ±15%."""
    from adam.intelligence import realtime_decision_engine as rde

    fake_engine = MagicMock()
    # Try a wildly large positive score
    fake_engine.get_curiosity_score = MagicMock(return_value=10.0)

    fake_redis_client = MagicMock()
    fake_redis_client.hgetall = MagicMock(return_value={})

    base_score = 0.5
    with patch.object(
        rde, "_score_mechanisms_from_position",
        return_value={"social_proof": base_score},
    ), patch(
        "redis.Redis", return_value=fake_redis_client,
    ), patch(
        "adam.intelligence.impression_state_resolver.resolve_reader_position",
        side_effect=Exception("skip"),
    ), patch(
        "adam.intelligence.page_intelligence.get_page_intelligence_cache",
        side_effect=Exception("skip"),
    ), patch(
        "adam.intelligence.daily.consumer.get_intelligence_consumer",
        side_effect=Exception("skip"),
    ), patch(
        "adam.intelligence.predictive_processing.get_predictive_processing_engine",
        return_value=fake_engine,
    ):
        decision = rde.compute_persuasion_decision(buyer_id="u_warm")

    # Multiplicative bonus capped at +15% → social_proof ≤ 0.5 * 1.15 = 0.575.
    sp_score = decision.mechanism_scores.get("social_proof", 0)
    assert sp_score <= base_score * 1.15 + 1e-6


def test_curiosity_bonus_extreme_negative_capped_at_minus_15_percent():
    """Even a wildly negative engine score must not push below -15%."""
    from adam.intelligence import realtime_decision_engine as rde

    fake_engine = MagicMock()
    fake_engine.get_curiosity_score = MagicMock(return_value=-10.0)

    fake_redis_client = MagicMock()
    fake_redis_client.hgetall = MagicMock(return_value={})

    base_score = 0.5
    with patch.object(
        rde, "_score_mechanisms_from_position",
        return_value={"social_proof": base_score},
    ), patch(
        "redis.Redis", return_value=fake_redis_client,
    ), patch(
        "adam.intelligence.impression_state_resolver.resolve_reader_position",
        side_effect=Exception("skip"),
    ), patch(
        "adam.intelligence.page_intelligence.get_page_intelligence_cache",
        side_effect=Exception("skip"),
    ), patch(
        "adam.intelligence.daily.consumer.get_intelligence_consumer",
        side_effect=Exception("skip"),
    ), patch(
        "adam.intelligence.predictive_processing.get_predictive_processing_engine",
        return_value=fake_engine,
    ):
        decision = rde.compute_persuasion_decision(buyer_id="u_cold")

    sp_score = decision.mechanism_scores.get("social_proof", 0)
    assert sp_score >= base_score * 0.85 - 1e-6
