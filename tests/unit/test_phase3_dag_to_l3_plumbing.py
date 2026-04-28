# =============================================================================
# ADAM Phase 3 deliverable 1 — DAG → L3 chain-attestation plumbing tests
# Location: tests/unit/test_phase3_dag_to_l3_plumbing.py
# =============================================================================

"""
DAG → L3 PLUMBING TESTS — B3-LUXY Phase 3 deliverable 1

Pins the helper that extracts ChainAttestations from a DAG's atom_outputs
and applies them to L3-derived mechanism_scores via multiplicative fusion.

This is the helper the orchestrator uses to bridge:
    cascade.mechanism_scores  +  dag.atom_outputs
    →  cascade.mechanism_scores modulated by chain-attestation feedback

When atoms emit no chain_attestations (the 21 unchanged wrappers), the
helper passes through unchanged — fully backward compatible.
"""

from unittest.mock import MagicMock

import pytest

from adam.api.stackadapt.bilateral_cascade import (
    apply_chain_attestations_to_mechanism_scores,
    extract_chain_attestations_from_atom_outputs,
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


def _make_attestation(atom_id: str, adjustments: list[tuple[str, float]]) -> ChainAttestation:
    """Build a minimal ChainAttestation for tests."""
    chain = [
        ConstructLink(
            source_construct="src",
            relation_type=RelationType.MODULATED_BY,
            target_construct=f"target_{atom_id}",
            evidence_value=0.5,
            confidence=0.7,
            citation="test_citation 1.0",
        )
    ]
    final = TypedEvidence(
        construct=f"construct_{atom_id}",
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
        request_id="req_test",
        target_construct=f"construct_{atom_id}",
        chain=chain,
        final_assessment=final,
        mechanism_adjustments=adj_evidence,
        provenance=provenance,
    )


def _make_atom_output(atom_id: str, attestation):
    """Build a mock AtomOutput-like object with the chain_attestation field."""
    output = MagicMock()
    output.chain_attestation = attestation
    output.atom_id = atom_id
    return output


# =============================================================================
# EXTRACTION HELPER
# =============================================================================


class TestExtractChainAttestations:
    """Pin the extraction-from-atom-outputs helper."""

    def test_none_atom_outputs_returns_empty_list(self):
        result = extract_chain_attestations_from_atom_outputs(None)
        assert result == []

    def test_empty_dict_returns_empty_list(self):
        result = extract_chain_attestations_from_atom_outputs({})
        assert result == []

    def test_atoms_without_chain_attestation_yield_empty(self):
        """The 21 unchanged wrappers emit no chain_attestation."""
        outputs = {
            "atom_wrapper_1": _make_atom_output("atom_wrapper_1", None),
            "atom_wrapper_2": _make_atom_output("atom_wrapper_2", None),
        }
        result = extract_chain_attestations_from_atom_outputs(outputs)
        assert result == []

    def test_extracts_single_attestation(self):
        att = _make_attestation("atom_autonomy_reactance", [("scarcity", -0.2)])
        outputs = {"atom_autonomy_reactance": _make_atom_output("atom_autonomy_reactance", att)}
        result = extract_chain_attestations_from_atom_outputs(outputs)
        assert len(result) == 1
        assert result[0].atom_id == "atom_autonomy_reactance"

    def test_extracts_multiple_attestations(self):
        att1 = _make_attestation("atom1", [("scarcity", -0.1)])
        att2 = _make_attestation("atom2", [("authority", 0.2)])
        outputs = {
            "atom1": _make_atom_output("atom1", att1),
            "atom2": _make_atom_output("atom2", att2),
        }
        result = extract_chain_attestations_from_atom_outputs(outputs)
        assert len(result) == 2

    def test_skips_none_outputs(self):
        """Defensive: handles None entries in the dict."""
        att = _make_attestation("atom1", [("scarcity", -0.1)])
        outputs = {
            "atom1": _make_atom_output("atom1", att),
            "atom_failed": None,
        }
        result = extract_chain_attestations_from_atom_outputs(outputs)
        assert len(result) == 1

    def test_mixed_redone_and_wrapper_atoms(self):
        """Realistic case: 9 redone atoms emit attestations, 21 wrappers don't."""
        # 3 redone, 5 wrappers
        outputs = {
            "atom_autonomy_reactance": _make_atom_output(
                "atom_autonomy_reactance",
                _make_attestation("atom_autonomy_reactance", [("scarcity", -0.2)]),
            ),
            "atom_persuasion_pharmacology": _make_atom_output(
                "atom_persuasion_pharmacology",
                _make_attestation("atom_persuasion_pharmacology", [("authority", 0.1)]),
            ),
            "atom_mimetic_desire": _make_atom_output(
                "atom_mimetic_desire",
                _make_attestation("atom_mimetic_desire", [("unity", 0.15)]),
            ),
            "atom_construal_level": _make_atom_output("atom_construal_level", None),
            "atom_message_framing": _make_atom_output("atom_message_framing", None),
            "atom_ad_selection": _make_atom_output("atom_ad_selection", None),
            "atom_channel_selection": _make_atom_output("atom_channel_selection", None),
            "atom_user_state": _make_atom_output("atom_user_state", None),
        }
        result = extract_chain_attestations_from_atom_outputs(outputs)
        assert len(result) == 3
        atom_ids = {att.atom_id for att in result}
        assert atom_ids == {
            "atom_autonomy_reactance",
            "atom_persuasion_pharmacology",
            "atom_mimetic_desire",
        }


# =============================================================================
# END-TO-END APPLICATION HELPER
# =============================================================================


class TestApplyChainAttestationsToMechanismScores:
    """Pin the orchestrator-facing end-to-end helper."""

    def test_empty_mechanism_scores_returns_empty(self):
        result = apply_chain_attestations_to_mechanism_scores({}, None)
        assert result == {}

    def test_no_atoms_returns_input_unchanged(self):
        scores = {"authority": 0.7, "scarcity": 0.5}
        result = apply_chain_attestations_to_mechanism_scores(scores, None)
        assert result == scores

    def test_empty_atoms_returns_input_unchanged(self):
        scores = {"authority": 0.7, "scarcity": 0.5}
        result = apply_chain_attestations_to_mechanism_scores(scores, {})
        assert result == scores

    def test_only_wrapper_atoms_returns_input_unchanged(self):
        """All atoms emit None chain_attestation → no modulation."""
        scores = {"authority": 0.7, "scarcity": 0.5}
        outputs = {
            "atom_wrapper_1": _make_atom_output("atom_wrapper_1", None),
            "atom_wrapper_2": _make_atom_output("atom_wrapper_2", None),
        }
        result = apply_chain_attestations_to_mechanism_scores(scores, outputs)
        assert result == scores

    def test_redone_atom_modulates_scores(self):
        """A single redone atom emitting a negative scarcity adjustment
        should reduce the scarcity score."""
        scores = {"scarcity": 0.8, "authority": 0.6}
        att = _make_attestation("atom_autonomy_reactance", [("scarcity", -0.3)])
        outputs = {"atom_autonomy_reactance": _make_atom_output("atom_autonomy_reactance", att)}
        result = apply_chain_attestations_to_mechanism_scores(scores, outputs)
        # 0.8 * (1.0 - 0.3) = 0.56
        assert result["scarcity"] == pytest.approx(0.56, abs=1e-3)
        # authority unchanged (no adjustment for it)
        assert result["authority"] == pytest.approx(0.6)

    def test_multiple_atoms_aggregate_adjustments(self):
        """Two atoms both adjusting scarcity → adjustments sum (per
        the multiplicative-fusion contract from Phase 0)."""
        scores = {"scarcity": 0.8}
        att1 = _make_attestation("atom1", [("scarcity", -0.1)])
        att2 = _make_attestation("atom2", [("scarcity", -0.1)])
        outputs = {
            "atom1": _make_atom_output("atom1", att1),
            "atom2": _make_atom_output("atom2", att2),
        }
        result = apply_chain_attestations_to_mechanism_scores(scores, outputs)
        # combined -0.2 → modifier 0.8 → 0.8 * 0.8 = 0.64
        assert result["scarcity"] == pytest.approx(0.64, abs=1e-3)

    def test_adjustment_clamped_at_chain_modifier_bounds(self):
        """Extreme adjustments clamped per CHAIN_MODIFIER_MIN/MAX
        (Phase 0 fusion-form A14 flag)."""
        scores = {"scarcity": 0.8}
        att = _make_attestation("atom1", [("scarcity", -2.0)])  # extreme
        outputs = {"atom1": _make_atom_output("atom1", att)}
        result = apply_chain_attestations_to_mechanism_scores(scores, outputs)
        # Clamped to MIN modifier 0.5 → 0.8 * 0.5 = 0.4
        assert result["scarcity"] == pytest.approx(0.4, abs=1e-3)

    def test_realistic_three_redone_atoms_modulate_three_mechanisms(self):
        """Realistic case: autonomy_reactance suppresses scarcity,
        signal_credibility boosts authority, mimetic_desire boosts unity."""
        scores = {
            "scarcity": 0.7,
            "authority": 0.5,
            "unity": 0.4,
            "social_proof": 0.6,  # not adjusted by any atom
        }
        att_reactance = _make_attestation(
            "atom_autonomy_reactance", [("scarcity", -0.2)]
        )
        att_signal = _make_attestation(
            "atom_signal_credibility", [("authority", 0.15)]
        )
        att_mimetic = _make_attestation(
            "atom_mimetic_desire", [("unity", 0.10)]
        )
        outputs = {
            "atom_autonomy_reactance": _make_atom_output(
                "atom_autonomy_reactance", att_reactance
            ),
            "atom_signal_credibility": _make_atom_output(
                "atom_signal_credibility", att_signal
            ),
            "atom_mimetic_desire": _make_atom_output(
                "atom_mimetic_desire", att_mimetic
            ),
        }
        result = apply_chain_attestations_to_mechanism_scores(scores, outputs)

        # scarcity: 0.7 × (1.0 - 0.2) = 0.56
        assert result["scarcity"] == pytest.approx(0.56, abs=1e-3)
        # authority: 0.5 × (1.0 + 0.15) = 0.575
        assert result["authority"] == pytest.approx(0.575, abs=1e-3)
        # unity: 0.4 × (1.0 + 0.10) = 0.44
        assert result["unity"] == pytest.approx(0.44, abs=1e-3)
        # social_proof: unchanged
        assert result["social_proof"] == pytest.approx(0.6)
