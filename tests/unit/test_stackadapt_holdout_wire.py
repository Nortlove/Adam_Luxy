"""Pin Slice 2 — holdout assignment wire in the StackAdapt service path.

Audit 2026-05-01 Tier 1 #2 found that
``adam.intelligence.spine.phase_8_stackadapt_integration.assign_holdout``
existed as a single tested function with zero non-test callers. The
5-10% deterministic-hash holdout (directive line 916) was not actually
shielding any production traffic. The Phase 8 RED gate (line 1105) and
the pre-registered campaign-level treatment-vs-control comparison
(line 919-928) both depend on this wire.

This test pins:
    * Import of assign_holdout in the service path
    * Holdout-assigned buyer returns is_holdout=True with no cascade
    * Treatment-assigned buyer falls through to the normal cascade path
    * Empty buyer_id bypasses holdout (anonymous users; honest tag (d))
    * Stratum counters present on the metrics surface
    * The holdout response shape carries decision_id + holdout_assignment
      block for audit + treatment-vs-control downstream consumers
    * Same buyer_id deterministic — repeated calls give same assignment
    * Honest contract: holdout response does NOT call _persist_decision
      (a holdout decision is not an ADAM decision; persisting would
      pollute the learning loop)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from adam.api.stackadapt.service import CreativeIntelligenceService


# -----------------------------------------------------------------------------
# Contract pins — wire is in place
# -----------------------------------------------------------------------------


def test_service_module_imports_assign_holdout():
    """Source-text pin: guards against silent removal of the wire."""
    from pathlib import Path

    src = Path("adam/api/stackadapt/service.py").read_text()
    assert "assign_holdout" in src, (
        "service.py no longer references assign_holdout. The Phase 8 "
        "holdout-discipline wire is missing — directive line 1103 + "
        "RED gate 1105 cannot be evaluated."
    )
    assert "is_holdout" in src, (
        "Holdout response flag missing from service.py. Downstream "
        "treatment-vs-control comparison cannot route."
    )


def test_metrics_surface_exposes_holdout_counter():
    """Stratum counter present on metrics surface."""
    from adam.infrastructure.prometheus import get_metrics

    metrics = get_metrics()
    assert hasattr(
        metrics, "stackadapt_holdout_assignments_total"
    ), (
        "Metrics surface missing stackadapt_holdout_assignments_total. "
        "Phase 8 RED gate input + audit visibility lost."
    )


# -----------------------------------------------------------------------------
# Behavioral pins — holdout-assigned buyer returns untouched response
# -----------------------------------------------------------------------------


def _service() -> CreativeIntelligenceService:
    """Bare service — no Neo4j / Redis init."""
    return CreativeIntelligenceService()


def test_holdout_assigned_returns_untouched_response():
    """When assign_holdout returns True, response is_holdout=True with
    no cascade run, no persuasion engine, no persist."""
    svc = _service()

    with patch(
        "adam.intelligence.spine.phase_8_stackadapt_integration."
        "assign_holdout",
        return_value=True,
    ), patch(
        "adam.api.stackadapt.service.run_bilateral_cascade",
    ) as mock_cascade, patch.object(
        svc, "_persist_decision",
    ) as mock_persist:
        result = svc.get_creative_intelligence(
            segment_id="achiever_high_intent",
            buyer_id="ramp_id_holdout_user_42",
            content_category="luxury_transportation",
        )

    # Cascade NOT called for holdout users
    mock_cascade.assert_not_called()
    # Holdout decision NOT persisted (would pollute learning loop)
    mock_persist.assert_not_called()

    assert result["is_holdout"] is True
    assert result["holdout_assignment"]["stratum"] == "holdout"
    assert "holdout_fraction" in result["holdout_assignment"]
    assert result["primary_mechanism"] is None
    assert "decision_id" in result
    assert "timing_ms" in result
    # Reasoning trace tags the holdout
    assert any(
        "HOLDOUT" in str(line) for line in result["reasoning_trace"]
    )


def test_treatment_assigned_falls_through_to_cascade():
    """When assign_holdout returns False, the normal cascade path runs."""
    svc = _service()

    # Build a minimal CreativeIntelligence the cascade would produce
    from adam.api.stackadapt.bilateral_cascade import CreativeIntelligence
    fake_ci = CreativeIntelligence(
        primary_mechanism="social_proof",
        secondary_mechanism="authority",
        framing="gain",
        cascade_level=2,
    )

    with patch(
        "adam.intelligence.spine.phase_8_stackadapt_integration."
        "assign_holdout",
        return_value=False,
    ), patch(
        "adam.api.stackadapt.service.run_bilateral_cascade",
        return_value=fake_ci,
    ) as mock_cascade, patch.object(
        svc, "_persist_decision",
    ):
        result = svc.get_creative_intelligence(
            segment_id="achiever_high_intent",
            buyer_id="ramp_id_treatment_user_99",
            content_category="luxury_transportation",
        )

    # Cascade WAS called for treatment users
    mock_cascade.assert_called_once()
    # No is_holdout flag on treatment response (the field stays absent
    # rather than False to avoid downstream consumers depending on it)
    assert not result.get("is_holdout", False)


def test_empty_buyer_id_bypasses_holdout_check():
    """Anonymous users (empty buyer_id) skip the holdout assignment.

    Honest tag: anonymous holdout-bucketing requires a fallback hash
    key (e.g. session_id) which is a sibling slice. Until then,
    anonymous traffic stays in treatment.
    """
    svc = _service()

    from adam.api.stackadapt.bilateral_cascade import CreativeIntelligence
    fake_ci = CreativeIntelligence(
        primary_mechanism="curiosity",
        cascade_level=1,
    )

    with patch(
        "adam.intelligence.spine.phase_8_stackadapt_integration."
        "assign_holdout",
    ) as mock_holdout, patch(
        "adam.api.stackadapt.service.run_bilateral_cascade",
        return_value=fake_ci,
    ), patch.object(
        svc, "_persist_decision",
    ):
        result = svc.get_creative_intelligence(
            segment_id="achiever_high_intent",
            buyer_id="",  # anonymous
            content_category="luxury_transportation",
        )

    # assign_holdout NOT called for anonymous users
    mock_holdout.assert_not_called()
    assert not result.get("is_holdout", False)


def test_holdout_response_carries_decision_id_for_traceability():
    """Decision_id is generated BEFORE the holdout check so even untouched
    requests get a traceable id. The mSPRT campaign monitor and
    treatment-vs-control comparison both need this for joining."""
    svc = _service()

    with patch(
        "adam.intelligence.spine.phase_8_stackadapt_integration."
        "assign_holdout",
        return_value=True,
    ), patch.object(
        svc, "_persist_decision",
    ):
        result = svc.get_creative_intelligence(
            segment_id="achiever_high_intent",
            buyer_id="ramp_id_holdout_with_id",
            content_category="luxury_transportation",
        )

    assert result["decision_id"]
    assert isinstance(result["decision_id"], str)
    assert len(result["decision_id"]) > 0


def test_holdout_response_includes_segment_metadata():
    """Holdout responses carry segment_metadata so the contract with
    downstream consumers is preserved."""
    svc = _service()

    with patch(
        "adam.intelligence.spine.phase_8_stackadapt_integration."
        "assign_holdout",
        return_value=True,
    ), patch.object(
        svc, "_persist_decision",
    ):
        result = svc.get_creative_intelligence(
            segment_id="achiever_high_intent",
            buyer_id="ramp_id_seg_test",
            content_category="luxury_transportation",
        )

    assert "segment_metadata" in result
    assert result["segment_metadata"]["segment_id"] == "achiever_high_intent"


# -----------------------------------------------------------------------------
# Underlying primitive — assign_holdout deterministic behavior preserved
# -----------------------------------------------------------------------------


def test_assign_holdout_deterministic_same_id_same_assignment():
    """Same buyer_id always assigns the same way (stable bucketing)."""
    from adam.intelligence.spine.phase_8_stackadapt_integration import (
        assign_holdout,
    )

    a = assign_holdout("stable_user_42")
    b = assign_holdout("stable_user_42")
    c = assign_holdout("stable_user_42")
    assert a == b == c


def test_assign_holdout_proportion_converges():
    """Aggregate holdout proportion converges to holdout_fraction."""
    from adam.intelligence.spine.phase_8_stackadapt_integration import (
        DEFAULT_HOLDOUT_FRACTION,
        estimate_holdout_proportion,
    )

    user_ids = [f"sim_user_{i}" for i in range(5000)]
    proportion = estimate_holdout_proportion(user_ids)
    # 5000 samples, target 10% — within ±2% absolute is the standard
    # binomial confidence band.
    assert abs(proportion - DEFAULT_HOLDOUT_FRACTION) < 0.02
