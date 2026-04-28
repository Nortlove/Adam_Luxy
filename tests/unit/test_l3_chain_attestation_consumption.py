# =============================================================================
# ADAM L3 Chain-Attestation Consumption Tests
# Location: tests/unit/test_l3_chain_attestation_consumption.py
# =============================================================================

"""
L3 CHAIN-ATTESTATION CONSUMPTION TESTS — B3-LUXY Phase 0 deliverable 4

Pins the interface contract between atom-emitted ChainAttestations and
the L3 bilateral cascade's mechanism scoring.

Anchors pinned:
- None / empty chain_attestations → L3 output unchanged (backward compat)
- Negative adjustment → mechanism score reduced
- Positive adjustment → mechanism score increased
- Adjustments aggregate across multiple attestations (sum)
- Chain modifier clamped to [_CHAIN_MODIFIER_MIN, _CHAIN_MODIFIER_MAX]
- Adjustments referencing unknown mechanisms are silently ignored
- Multiplicative fusion (not additive)

See docs/B3_LUXY_PHASE_PLAN.md §5 for the full contract.
"""

import pytest

from adam.api.stackadapt.bilateral_cascade import (
    _CHAIN_MODIFIER_MAX,
    _CHAIN_MODIFIER_MIN,
    _apply_chain_attestation_adjustments,
)
from adam.atoms.models.chain_attestation import (
    AdjustmentEvidence,
    CalibrationStatus,
    ChainAttestation,
    ChainProvenance,
    ConstructLink,
    RelationType,
    TypedEvidence,
)


def _make_attestation(
    *,
    atom_id: str = "atom_test",
    request_id: str = "req_test",
    target: str = "test_construct",
    adjustments: list[tuple[str, float]] = (),
) -> ChainAttestation:
    """Build a minimal ChainAttestation with the given mechanism adjustments."""
    chain = [
        ConstructLink(
            source_construct="src",
            relation_type=RelationType.MODULATED_BY,
            target_construct=target,
            evidence_value=0.5,
            confidence=0.7,
            citation="test_citation 1.0",
        )
    ]
    final = TypedEvidence(
        construct=target,
        value=0.5,
        confidence=0.7,
        citation="test_citation 1.0",
        calibration_status=CalibrationStatus.PINNED,
    )
    provenance = ChainProvenance(atom_id=atom_id)
    chain_link_ids = [chain[0].link_id]
    adj_evidence = [
        AdjustmentEvidence(
            mechanism_id=mech,
            adjustment_value=value,
            chain_links_responsible=chain_link_ids,
            confidence=0.7,
        )
        for mech, value in adjustments
    ]
    return ChainAttestation(
        atom_id=atom_id,
        request_id=request_id,
        target_construct=target,
        chain=chain,
        final_assessment=final,
        mechanism_adjustments=adj_evidence,
        provenance=provenance,
    )


# =============================================================================
# BACKWARD COMPATIBILITY (NO CHAIN ATTESTATIONS)
# =============================================================================


class TestBackwardCompatibility:
    """Pin: when no chain attestations are passed, L3 produces unchanged output."""

    def test_none_attestations_returns_input_unchanged(self):
        scores = {"authority": 0.7, "social_proof": 0.6, "scarcity": 0.4}
        result = _apply_chain_attestation_adjustments(scores, None)
        assert result == scores

    def test_empty_list_returns_input_unchanged(self):
        scores = {"authority": 0.7, "social_proof": 0.6, "scarcity": 0.4}
        result = _apply_chain_attestation_adjustments(scores, [])
        assert result == scores

    def test_attestations_with_no_mechanism_adjustments_returns_input_unchanged(self):
        scores = {"authority": 0.7, "social_proof": 0.6}
        attestation = _make_attestation(adjustments=[])  # empty adjustments
        result = _apply_chain_attestation_adjustments(scores, [attestation])
        assert result == scores


# =============================================================================
# DIRECTIONAL ADJUSTMENTS
# =============================================================================


class TestDirectionalAdjustments:
    """Pin: negative adjustment reduces; positive adjustment increases."""

    def test_negative_adjustment_reduces_score(self):
        scores = {"scarcity": 0.8}
        attestation = _make_attestation(adjustments=[("scarcity", -0.3)])
        result = _apply_chain_attestation_adjustments(scores, [attestation])
        # 0.8 * (1.0 - 0.3) = 0.8 * 0.7 = 0.56
        assert result["scarcity"] == pytest.approx(0.56, abs=1e-3)
        assert result["scarcity"] < scores["scarcity"]

    def test_positive_adjustment_increases_score(self):
        scores = {"storytelling": 0.5}
        attestation = _make_attestation(adjustments=[("storytelling", 0.2)])
        result = _apply_chain_attestation_adjustments(scores, [attestation])
        # 0.5 * (1.0 + 0.2) = 0.5 * 1.2 = 0.60
        assert result["storytelling"] == pytest.approx(0.60, abs=1e-3)
        assert result["storytelling"] > scores["storytelling"]

    def test_zero_adjustment_leaves_score_unchanged(self):
        scores = {"authority": 0.7}
        attestation = _make_attestation(adjustments=[("authority", 0.0)])
        result = _apply_chain_attestation_adjustments(scores, [attestation])
        assert result["authority"] == pytest.approx(0.7, abs=1e-3)


# =============================================================================
# AGGREGATION ACROSS ATTESTATIONS
# =============================================================================


class TestAggregationAcrossAttestations:
    """Pin: when multiple attestations adjust the same mechanism, the
    adjustment_values sum (per the docstring contract)."""

    def test_two_attestations_same_mechanism_sum(self):
        scores = {"authority": 0.8}
        att1 = _make_attestation(atom_id="a1", adjustments=[("authority", -0.1)])
        att2 = _make_attestation(atom_id="a2", adjustments=[("authority", -0.1)])
        result = _apply_chain_attestation_adjustments(scores, [att1, att2])
        # Combined: -0.2 → modifier 0.8 → 0.8 * 0.8 = 0.64
        assert result["authority"] == pytest.approx(0.64, abs=1e-3)

    def test_attestations_with_opposite_adjustments_cancel(self):
        scores = {"social_proof": 0.6}
        att1 = _make_attestation(atom_id="a1", adjustments=[("social_proof", 0.2)])
        att2 = _make_attestation(atom_id="a2", adjustments=[("social_proof", -0.2)])
        result = _apply_chain_attestation_adjustments(scores, [att1, att2])
        # Combined: 0.0 → modifier 1.0 → unchanged
        assert result["social_proof"] == pytest.approx(0.6, abs=1e-3)


# =============================================================================
# CLAMP TO MODIFIER BOUNDS
# =============================================================================


class TestModifierBounds:
    """Pin: chain modifier is clamped to [_CHAIN_MODIFIER_MIN, _CHAIN_MODIFIER_MAX].

    A14: CHAIN_ATTESTATION_LUXY_FUSION_FORM_PILOT_PENDING — the bounds
    prevent any single chain attestation from dominating or zeroing the
    edge-derived score during pilot. Pilot data may justify wider bounds
    or a different fusion form."""

    def test_extreme_negative_adjustment_clamped_at_min(self):
        scores = {"scarcity": 0.8}
        # Sum of -2.0 should clamp to _CHAIN_MODIFIER_MIN = 0.5
        attestation = _make_attestation(adjustments=[("scarcity", -2.0)])
        result = _apply_chain_attestation_adjustments(scores, [attestation])
        # 0.8 * 0.5 = 0.4 (not 0.8 * (1.0 - 2.0) = -0.8 clamped to 0.0)
        assert result["scarcity"] == pytest.approx(0.4, abs=1e-3)

    def test_extreme_positive_adjustment_clamped_at_max(self):
        scores = {"storytelling": 0.5}
        # Sum of +2.0 should clamp to _CHAIN_MODIFIER_MAX = 1.5
        attestation = _make_attestation(adjustments=[("storytelling", 2.0)])
        result = _apply_chain_attestation_adjustments(scores, [attestation])
        # 0.5 * 1.5 = 0.75
        assert result["storytelling"] == pytest.approx(0.75, abs=1e-3)

    def test_modifier_bounds_constants_sane(self):
        """Sanity: MIN < 1.0 < MAX, both finite."""
        assert 0.0 < _CHAIN_MODIFIER_MIN < 1.0 < _CHAIN_MODIFIER_MAX < 10.0


# =============================================================================
# UNKNOWN MECHANISMS
# =============================================================================


class TestUnknownMechanisms:
    """Pin: adjustments referencing mechanisms not in the score dict are
    silently ignored — the chain-attestation primitive may name
    mechanisms that don't apply to a given decision context."""

    def test_unknown_mechanism_ignored(self):
        scores = {"authority": 0.7}
        attestation = _make_attestation(
            adjustments=[("unknown_mechanism", -0.5)]
        )
        result = _apply_chain_attestation_adjustments(scores, [attestation])
        assert result == scores

    def test_partial_known_mechanisms_partial_applied(self):
        scores = {"authority": 0.7, "social_proof": 0.6}
        attestation = _make_attestation(
            adjustments=[
                ("authority", -0.2),
                ("nonexistent_mechanism", 0.5),
            ],
        )
        result = _apply_chain_attestation_adjustments(scores, [attestation])
        # authority: 0.7 * 0.8 = 0.56
        assert result["authority"] == pytest.approx(0.56, abs=1e-3)
        # social_proof unchanged
        assert result["social_proof"] == pytest.approx(0.6, abs=1e-3)
        # nonexistent_mechanism not introduced
        assert "nonexistent_mechanism" not in result


# =============================================================================
# FUSION FORM — MULTIPLICATIVE NOT ADDITIVE
# =============================================================================


class TestMultiplicativeFusion:
    """Pin: fusion is multiplicative (chain modifier × edge score), NOT
    additive (chain adjustment + edge score). Multiplicative respects
    chain-dependent attenuation (foundation §4.3) and avoids the
    additive smearing that would break per-link credit attribution."""

    def test_high_edge_score_high_chain_boost_amplified(self):
        """Multiplicative: 0.8 × 1.3 = 1.04 → clamped to 1.0; not 0.8 + 0.3 = 1.1."""
        scores_high = {"authority": 0.8}
        attestation = _make_attestation(adjustments=[("authority", 0.3)])
        result_high = _apply_chain_attestation_adjustments(scores_high, [attestation])
        # 0.8 * 1.3 = 1.04 → clamped to 1.0
        assert result_high["authority"] == pytest.approx(1.0, abs=1e-3)

    def test_low_edge_score_high_chain_boost_attenuated(self):
        """Multiplicative: 0.2 × 1.3 = 0.26; the chain boost is
        attenuated by the weak edge signal — additive would have
        produced 0.5, but the edge says this mechanism doesn't fit."""
        scores_low = {"authority": 0.2}
        attestation = _make_attestation(adjustments=[("authority", 0.3)])
        result_low = _apply_chain_attestation_adjustments(scores_low, [attestation])
        # 0.2 * 1.3 = 0.26
        assert result_low["authority"] == pytest.approx(0.26, abs=1e-3)
        # Crucially: not 0.2 + 0.3 = 0.5 (additive would have produced this)
        assert result_low["authority"] < 0.4

    def test_low_edge_score_negative_chain_attenuated_in_absolute_terms(self):
        """Multiplicative: 0.3 × 0.7 = 0.21 (loss of 0.09); additive
        would have given 0.0 (loss of 0.3). The chain's "this is bad"
        signal is appropriately attenuated when the edge already says
        the mechanism is weak."""
        scores = {"scarcity": 0.3}
        attestation = _make_attestation(adjustments=[("scarcity", -0.3)])
        result = _apply_chain_attestation_adjustments(scores, [attestation])
        assert result["scarcity"] == pytest.approx(0.21, abs=1e-3)


# =============================================================================
# OUTPUT RANGE
# =============================================================================


class TestOutputRange:
    """Pin: output scores remain ∈ [0.0, 1.0]."""

    def test_score_clamped_to_unit_interval_when_modifier_pushes_above_1(self):
        scores = {"unity": 0.95}
        attestation = _make_attestation(adjustments=[("unity", 0.5)])
        result = _apply_chain_attestation_adjustments(scores, [attestation])
        assert 0.0 <= result["unity"] <= 1.0

    def test_score_clamped_to_unit_interval_when_modifier_pushes_below_0(self):
        scores = {"scarcity": 0.05}
        attestation = _make_attestation(adjustments=[("scarcity", -2.0)])
        result = _apply_chain_attestation_adjustments(scores, [attestation])
        assert 0.0 <= result["scarcity"] <= 1.0
