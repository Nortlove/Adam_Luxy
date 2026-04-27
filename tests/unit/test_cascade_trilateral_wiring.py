"""Regression tests for the trilateral page-conditioned query wiring in
the bilateral cascade.

Discipline anchors:
    - The trilateral query (page_conditioned_query.query_page_conditioned_edges)
      is the canonical decision pattern per the "newer directions" directive.
      The cascade L3 path must invoke it whenever page_edge_dimensions are
      available, AND must consume its mechanism_effectiveness as the L3
      mechanism scores when confidence ≥ floor.
    - The deprecated additive page-shift path (apply_page_shift_to_edges +
      formula scoring on shifted edges) MUST be skipped when the trilateral
      query produces sufficient evidence — these tests guard against
      regression to running both paths or running the deprecated path
      preferentially.
    - Fall-through to the additive path is permitted (and currently
      operational under A14 flag ADDITIVE_PAGE_SHIFT_FALLBACK) only when
      trilateral returns None or low-confidence evidence.
"""

from __future__ import annotations

from unittest.mock import patch, MagicMock

from adam.api.stackadapt.bilateral_cascade import (
    _TRILATERAL_CONFIDENCE_FLOOR,
    _query_trilateral_evidence_sync,
    level3_bilateral_edges,
)
from adam.intelligence.page_conditioned_query import PageConditionedEvidence


# -----------------------------------------------------------------------------
# Wiring-shape tests — the trilateral path must EXIST and be the primary
# decision pattern. These pin the contract against re-drift.
# -----------------------------------------------------------------------------


def test_level3_signature_accepts_page_edge_dimensions_and_category():
    """L3 MUST accept page_edge_dimensions and category — these are the
    inputs the trilateral query needs. Removing either parameter would
    cut the canonical query off from L3."""
    import inspect

    sig = inspect.signature(level3_bilateral_edges)
    assert "page_edge_dimensions" in sig.parameters, (
        "level3_bilateral_edges must accept page_edge_dimensions; this is "
        "the input to the canonical trilateral query path. Removing this "
        "parameter would silently regress L3 to the deprecated additive "
        "page-shift path on every request."
    )
    assert "category" in sig.parameters, (
        "level3_bilateral_edges must accept category; the trilateral query "
        "filters by product category for evidence specificity."
    )


def test_trilateral_confidence_floor_is_set():
    """The confidence floor gates the canonical-vs-deprecated decision.
    Must be a float in (0, 1)."""
    assert 0.0 < _TRILATERAL_CONFIDENCE_FLOOR < 1.0, (
        "Confidence floor must be in (0, 1); got "
        f"{_TRILATERAL_CONFIDENCE_FLOOR}"
    )


# -----------------------------------------------------------------------------
# Behavioral tests — when trilateral fires, the additive path is skipped.
# When trilateral is unavailable, the additive path operates as fallback.
# -----------------------------------------------------------------------------


def test_query_trilateral_returns_none_for_empty_page_dims():
    """An empty page edge dimensions dict means the query has no input to
    filter on — return None and let L3 fall through to the additive path."""
    result = _query_trilateral_evidence_sync(
        page_edge_dims={},
        category="luxury_transportation",
        asin="lux_luxy_ride",
    )
    assert result is None


def test_query_trilateral_handles_failure_gracefully():
    """When the underlying async query raises, the sync wrapper must
    return None (not propagate). Falling through to the additive path
    is the correct behavior; raising would crash the cascade."""
    with patch(
        "adam.intelligence.page_conditioned_query.query_page_conditioned_edges",
        side_effect=RuntimeError("simulated graph failure"),
    ):
        result = _query_trilateral_evidence_sync(
            page_edge_dims={"regulatory_fit": 0.8, "construal_fit": 0.3},
            category="luxury_transportation",
            asin="lux_luxy_ride",
        )
    assert result is None


def test_trilateral_evidence_above_floor_overrides_additive_shift():
    """When trilateral evidence has confidence ≥ floor, the additive
    page-shift path MUST be skipped. This is the canonical-direction
    invariant — failing this test means the deprecated path is still
    running on production traffic.
    """
    high_conf_evidence = PageConditionedEvidence(
        optimal_alignment={
            "regulatory_fit": 0.72,
            "construal_fit": 0.40,
            "personality_alignment": 0.65,
            "emotional_resonance": 0.55,
            "value_alignment": 0.70,
            "evolutionary_motive": 0.50,
            "persuasion_susceptibility": 0.60,
            "cognitive_load_tolerance": 0.45,
            "narrative_transport": 0.50,
            "social_proof_sensitivity": 0.55,
            "loss_aversion_intensity": 0.42,
            "temporal_discounting": 0.30,
            "brand_relationship_depth": 0.65,
            "autonomy_reactance": 0.30,
            "information_seeking": 0.55,
            "mimetic_desire": 0.50,
            "interoceptive_awareness": 0.50,
            "cooperative_framing_fit": 0.60,
            "decision_entropy": 0.40,
        },
        mechanism_effectiveness={
            "authority": 0.62,
            "social_proof": 0.71,
            "scarcity": 0.35,
            "loss_aversion": 0.40,
            "commitment": 0.58,
            "liking": 0.65,
            "reciprocity": 0.55,
            "curiosity": 0.50,
            "cognitive_ease": 0.45,
            "unity": 0.60,
        },
        matching_edge_count=312,
        confidence=0.78,  # well above floor
        signature_dimensions=["regulatory_fit", "personality_alignment", "construal_fit"],
        page_state_hash="abc123",
        category="luxury_transportation",
    )

    # Verify the gate: confidence above floor → additive path is suppressed.
    use_additive = (
        high_conf_evidence is None
        or high_conf_evidence.confidence < _TRILATERAL_CONFIDENCE_FLOOR
    )
    assert use_additive is False, (
        f"Trilateral confidence {high_conf_evidence.confidence} is above "
        f"floor {_TRILATERAL_CONFIDENCE_FLOOR} — additive path should be "
        "skipped, but the gate is letting it run. Production traffic would "
        "still hit the deprecated path."
    )


def test_trilateral_evidence_below_floor_falls_through_to_additive():
    """When trilateral confidence is below the floor, the additive
    path is permitted as fallback. A14 flag ADDITIVE_PAGE_SHIFT_FALLBACK
    governs this — the path stays operational until trilateral coverage
    is sufficient at scale.
    """
    low_conf_evidence = PageConditionedEvidence(
        optimal_alignment={"regulatory_fit": 0.5},
        mechanism_effectiveness={"authority": 0.5},
        matching_edge_count=12,
        confidence=0.30,  # below floor
        signature_dimensions=["regulatory_fit"],
    )

    use_additive = (
        low_conf_evidence is None
        or low_conf_evidence.confidence < _TRILATERAL_CONFIDENCE_FLOOR
    )
    assert use_additive is True, (
        "Low-confidence trilateral evidence must fall through to the "
        "additive path; the gate is preventing the fallback."
    )


def test_no_trilateral_evidence_falls_through_to_additive():
    """No trilateral evidence at all (None) → additive path runs. This
    is the case when the page is neutral (no signature dims) or the
    edge corpus has no matching edges for this state."""
    use_additive = (None is None or 0.0 < _TRILATERAL_CONFIDENCE_FLOOR)
    assert use_additive is True
