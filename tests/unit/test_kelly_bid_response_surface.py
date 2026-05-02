"""Pin Slice 7 — Kelly-shaded bid_value reaches StackAdapt response.

Audit Tier 1 #6: bid_composer.compose_chosen_bid_value computed the
Kelly bid_value (Spine #9 fractional Kelly + winner's-curse shading +
Spine #8 epistemic addend) and populated DecisionTrace.bid_value, but
``run_bilateral_cascade`` returned a CreativeIntelligence with NO
bid_value field — the math ran and was logged, but spend was not
actually shaped.

This test pins:
    * CreativeIntelligence dataclass exposes bid_value: Optional[float]
    * The cascade source mirrors trace.bid_value onto result.bid_value
      after the trace build (source-text contract)
    * The StackAdapt service response includes recommended_bid_value
    * Default (no posterior / no posture) → bid_value None →
      response carries None (not zero, not absent) so downstream
      callers can distinguish "no recommendation" from "bid 0"
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


# -----------------------------------------------------------------------------
# Dataclass field contract
# -----------------------------------------------------------------------------


def test_creative_intelligence_carries_bid_value_field():
    """CreativeIntelligence dataclass must expose bid_value: Optional[float]."""
    from adam.api.stackadapt.bilateral_cascade import CreativeIntelligence

    ci = CreativeIntelligence()
    assert hasattr(ci, "bid_value")
    # Default is None — distinguishes "not yet computed" from "zero bid"
    assert ci.bid_value is None


def test_creative_intelligence_bid_value_assignable():
    """bid_value is a writable Optional[float]."""
    from adam.api.stackadapt.bilateral_cascade import CreativeIntelligence

    ci = CreativeIntelligence()
    ci.bid_value = 1.234
    assert ci.bid_value == 1.234

    ci.bid_value = None
    assert ci.bid_value is None


# -----------------------------------------------------------------------------
# Cascade wire — source-text contract
# -----------------------------------------------------------------------------


def test_cascade_mirrors_trace_bid_value_onto_result():
    """Cascade source must mirror _trace.bid_value onto result.bid_value
    after the trace is built — otherwise bid_composer's math runs
    but spend is not shaped.
    """
    src = Path("adam/api/stackadapt/bilateral_cascade.py").read_text()
    assert "result.bid_value = float(_trace.bid_value)" in src, (
        "Cascade no longer mirrors trace.bid_value onto result.bid_value. "
        "Slice 7 (Kelly bid → response) is broken — DecisionTrace gets "
        "the value but the StackAdapt response will not."
    )


# -----------------------------------------------------------------------------
# Service response shape
# -----------------------------------------------------------------------------


def test_service_response_includes_recommended_bid_value():
    """_format_response must surface ci.bid_value as recommended_bid_value."""
    from adam.api.stackadapt.bilateral_cascade import CreativeIntelligence
    from adam.api.stackadapt.service import CreativeIntelligenceService

    svc = CreativeIntelligenceService()
    ci = CreativeIntelligence(
        primary_mechanism="social_proof",
        bid_value=2.45,
    )
    response = svc._format_response(
        ci=ci,
        copy_guidance={},
        dsp_info=None,
        elapsed_ms=10.0,
        segment_id="achiever_high_intent",
        decision_id="dec_xyz",
    )
    assert "recommended_bid_value" in response
    assert response["recommended_bid_value"] == 2.45


def test_service_response_recommended_bid_none_when_no_posterior():
    """Cold-start buyer (bid_value=None) → response carries None."""
    from adam.api.stackadapt.bilateral_cascade import CreativeIntelligence
    from adam.api.stackadapt.service import CreativeIntelligenceService

    svc = CreativeIntelligenceService()
    ci = CreativeIntelligence(
        primary_mechanism="social_proof",
        bid_value=None,
    )
    response = svc._format_response(
        ci=ci,
        copy_guidance={},
        dsp_info=None,
        elapsed_ms=10.0,
    )
    assert "recommended_bid_value" in response
    assert response["recommended_bid_value"] is None


def test_service_response_carries_holdout_no_bid_value():
    """Holdout users (Slice 2 wire) get no bid_value; response uses
    the early-return shape from Slice 2 (no recommended_bid_value field)."""
    from adam.api.stackadapt.service import CreativeIntelligenceService

    svc = CreativeIntelligenceService()

    with patch(
        "adam.intelligence.spine.phase_8_stackadapt_integration."
        "assign_holdout",
        return_value=True,
    ), patch.object(
        svc, "_persist_decision",
    ):
        result = svc.get_creative_intelligence(
            segment_id="achiever_high_intent",
            buyer_id="ramp_id_holdout_42",
            content_category="luxury_transportation",
        )

    # Holdout response shape from Slice 2 — no recommended_bid_value
    # field (confirms the two slices' response shapes don't collide
    # in unintended ways)
    assert result["is_holdout"] is True
    assert "recommended_bid_value" not in result


def test_service_treatment_response_includes_recommended_bid_value():
    """Treatment users get the full _format_response shape including
    recommended_bid_value (mirroring whatever the cascade computed)."""
    from adam.api.stackadapt.bilateral_cascade import CreativeIntelligence
    from adam.api.stackadapt.service import CreativeIntelligenceService

    svc = CreativeIntelligenceService()
    fake_ci = CreativeIntelligence(
        primary_mechanism="social_proof",
        cascade_level=2,
        bid_value=1.789,
    )

    with patch(
        "adam.intelligence.spine.phase_8_stackadapt_integration."
        "assign_holdout",
        return_value=False,
    ), patch(
        "adam.api.stackadapt.service.run_bilateral_cascade",
        return_value=fake_ci,
    ), patch.object(
        svc, "_persist_decision",
    ):
        result = svc.get_creative_intelligence(
            segment_id="achiever_high_intent",
            buyer_id="ramp_id_treatment_99",
            content_category="luxury_transportation",
        )

    assert result.get("recommended_bid_value") == 1.789
    assert not result.get("is_holdout", False)
