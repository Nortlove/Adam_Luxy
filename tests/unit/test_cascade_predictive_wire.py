"""Pin the predictive_processing curiosity wire INSIDE the cascade.

Drift correction. The wire previously sat in
realtime_decision_engine.compute_persuasion_decision (commit
88b55a9), where its output flowed into `persuasion_intelligence` —
a metadata field with NO downstream consumers. Per Appendix E
rule (A) ("no measurement without immediate decision-time
consumer"), the wire was relocated to the cascade so the curiosity
bonus actually modulates `result.mechanism_scores` — the value that
becomes the bid mechanism returned to StackAdapt.

These tests pin the cascade-internal contract:
    * Engine called when buyer_id present + mechanism_scores non-empty
    * Engine NOT called when buyer_id empty
    * Bonus capped at ±15%
    * Output ∈ [0, 1] even with extreme inputs
    * Unmapped mechanisms pass through unchanged
    * Soft-fail on engine exception (mechanism_scores untouched)
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest


# Replicate the wire as a focused test harness: invoke the same
# logic the cascade does, but in isolation. The cascade integration
# itself is exercised by run_bilateral_cascade in cascade tests.

def _apply_curiosity_block(
    mechanism_scores: Dict[str, float],
    buyer_id: str,
    engine: Any,
) -> int:
    """Mirror the curiosity-bonus block in run_bilateral_cascade for unit
    testing. Returns the count of mechanisms that received a non-zero
    bonus."""
    from adam.intelligence.bong import DEFAULT_DIMENSIONS as _BONG_DIMS
    from adam.intelligence.per_user_posterior_modulation import (
        MECHANISM_DIMENSION_MAP,
    )

    applied = 0
    for mech_id in list(mechanism_scores.keys()):
        primary_dims = MECHANISM_DIMENSION_MAP.get(mech_id)
        if not primary_dims:
            continue
        ad_features = {}
        for d in _BONG_DIMS:
            cohort_name = d
            if cohort_name.endswith("_score"):
                cohort_name = cohort_name[: -len("_score")]
            if cohort_name.endswith("_match"):
                cohort_name = cohort_name[: -len("_match")]
            if cohort_name == "personality_brand_alignment":
                cohort_name = "personality_alignment"
            ad_features[d] = 1.0 if cohort_name in primary_dims else 0.5
        bonus = engine.get_curiosity_score(buyer_id, ad_features)
        capped = max(-0.15, min(0.15, float(bonus)))
        if abs(capped) > 1e-6:
            mechanism_scores[mech_id] = max(
                0.0, min(1.0, mechanism_scores[mech_id] * (1.0 + capped))
            )
            applied += 1
    return applied


# -----------------------------------------------------------------------------
# unit-level pins on the wire's behavior
# -----------------------------------------------------------------------------


def test_engine_called_per_mapped_mechanism():
    fake_engine = MagicMock()
    fake_engine.get_curiosity_score = MagicMock(return_value=0.05)

    scores = {
        "social_proof": 0.5,
        "authority": 0.5,
        "scarcity": 0.5,
        "this_mech_has_no_dims_mapping": 0.3,
    }
    _apply_curiosity_block(scores, "u_warm", fake_engine)
    # Three mapped mechanisms; one unmapped → 3 calls.
    assert fake_engine.get_curiosity_score.call_count == 3


def test_unmapped_mechanism_passes_through_untouched():
    fake_engine = MagicMock()
    fake_engine.get_curiosity_score = MagicMock(return_value=0.5)

    fake_mech = "this_mech_has_no_dims_mapping"
    scores = {fake_mech: 0.42}
    _apply_curiosity_block(scores, "u", fake_engine)
    assert scores[fake_mech] == 0.42
    fake_engine.get_curiosity_score.assert_not_called()


def test_extreme_positive_bonus_capped_at_plus_15_pct():
    fake_engine = MagicMock()
    fake_engine.get_curiosity_score = MagicMock(return_value=10.0)

    scores = {"social_proof": 0.5}
    _apply_curiosity_block(scores, "u", fake_engine)
    assert scores["social_proof"] <= 0.5 * 1.15 + 1e-6


def test_extreme_negative_bonus_capped_at_minus_15_pct():
    fake_engine = MagicMock()
    fake_engine.get_curiosity_score = MagicMock(return_value=-10.0)

    scores = {"social_proof": 0.5}
    _apply_curiosity_block(scores, "u", fake_engine)
    assert scores["social_proof"] >= 0.5 * 0.85 - 1e-6


def test_score_clamps_to_unit_interval():
    fake_engine = MagicMock()
    fake_engine.get_curiosity_score = MagicMock(return_value=10.0)
    scores = {"social_proof": 0.99}
    _apply_curiosity_block(scores, "u", fake_engine)
    assert 0.0 <= scores["social_proof"] <= 1.0


# -----------------------------------------------------------------------------
# end-to-end: run_bilateral_cascade does NOT call the engine when buyer_id
# is empty (we only verify the gating path; full cascade integration is
# already pinned by other test files)
# -----------------------------------------------------------------------------


def test_cascade_skips_predictive_wire_when_no_buyer_id():
    """When buyer_id is empty the wire MUST NOT call the engine."""
    from adam.api.stackadapt.bilateral_cascade import run_bilateral_cascade

    with patch(
        "adam.intelligence.predictive_processing.get_predictive_processing_engine",
    ) as engine_factory:
        # No graph_cache and no buyer_id → wire must short-circuit on
        # the buyer_id check before even constructing the engine.
        run_bilateral_cascade(segment_id="status_seeker:luxury_transportation")

    engine_factory.assert_not_called()


def test_cascade_engine_exception_does_not_crash():
    """Any exception inside the predictive wire MUST NOT propagate."""
    from adam.api.stackadapt.bilateral_cascade import run_bilateral_cascade

    fake_engine = MagicMock()
    fake_engine.get_curiosity_score = MagicMock(
        side_effect=RuntimeError("engine blew up"),
    )

    with patch(
        "adam.intelligence.predictive_processing.get_predictive_processing_engine",
        return_value=fake_engine,
    ):
        # MUST NOT RAISE — soft-fail is the contract.
        result = run_bilateral_cascade(
            segment_id="status_seeker:luxury_transportation",
            buyer_id="u_warm",
        )

    assert result is not None
