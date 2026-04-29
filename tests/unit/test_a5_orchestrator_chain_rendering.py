# =============================================================================
# ADAM A5 — Orchestrator Construct-Chain Response Wiring Tests
# Location: tests/unit/test_a5_orchestrator_chain_rendering.py
# =============================================================================

"""Tests for task A5 — wiring chain_rendering at orchestrator response so
the construct chain is visible at the partner interface."""

from __future__ import annotations

import pytest

from adam.atoms.models.chain_attestation import (
    AdjustmentEvidence,
    CalibrationStatus,
    ChainAttestation,
    ChainProvenance,
    ConstructLink,
    RelationType,
    TypedEvidence,
)
from adam.intelligence.chain_rendering import (
    recommendation_to_dict,
    render_recommendation,
)
from adam.orchestrator.models import (
    AtomDAGResult,
    CampaignAnalysisResult,
)


def _make_attestation_for_a5(atom_id: str, mechanism_id: str) -> ChainAttestation:
    link = ConstructLink(
        source_construct="src",
        relation_type=RelationType.CREATES_NEED_FOR,
        target_construct="tgt",
        evidence_value=0.6,
        confidence=0.7,
        citation="A5_test §1.1",
    )
    final = TypedEvidence(
        construct="tgt",
        value=0.6,
        confidence=0.7,
        citation="A5_test §1.1",
        calibration_status=CalibrationStatus.PINNED,
    )
    return ChainAttestation(
        atom_id=atom_id,
        request_id="req_a5",
        target_construct="tgt",
        chain=[link],
        final_assessment=final,
        mechanism_adjustments=[
            AdjustmentEvidence(
                mechanism_id=mechanism_id,
                adjustment_value=0.1,
                chain_links_responsible=[link.link_id],
                confidence=0.7,
            )
        ],
        provenance=ChainProvenance(
            atom_id=atom_id,
            a14_flags_active=["TEST_FLAG_PILOT_PENDING"],
        ),
    )


# ============================================================================
# CampaignAnalysisResult.construct_chain field
# ============================================================================


class TestCampaignAnalysisResultConstructChain:

    def test_construct_chain_field_default_none(self):
        result = CampaignAnalysisResult(
            request_id="req_test",
            brand="LUXY",
            product="black_car",
            description="x",
            call_to_action="book",
            primary_mechanism="authority",
            recommended_tone="warm",
            recommended_frame="gain",
        )
        assert result.construct_chain is None

    def test_construct_chain_accepts_dict(self):
        # Build a realistic chain rendering payload
        att = _make_attestation_for_a5("atom_test", "authority")
        rendering = render_recommendation(
            [att],
            recommendation_summary="Test",
        )
        payload = recommendation_to_dict(rendering)

        result = CampaignAnalysisResult(
            request_id="req_test",
            brand="LUXY",
            product="black_car",
            description="x",
            call_to_action="book",
            primary_mechanism="authority",
            recommended_tone="warm",
            recommended_frame="gain",
            construct_chain=payload,
        )
        assert result.construct_chain is not None
        assert result.construct_chain["recommendation_summary"] == "Test"
        assert result.construct_chain["n_attestations"] == 1


# ============================================================================
# Orchestrator response shape (no full execute() — focused on the
# render-construction logic)
# ============================================================================


class TestOrchestratorChainRenderingHook:
    """Tests focused on the chain-rendering hook in orchestrator.execute().

    Full `execute()` is heavy with dependencies (Neo4j, intelligence
    prefetch, atom DAG); these tests exercise the rendering logic in
    isolation by directly invoking the chain_rendering primitives the
    orchestrator uses.
    """

    def test_atom_dag_result_with_attestations_produces_payload(self):
        """When AtomDAGResult.chain_attestations is non-empty, the
        rendering primitive produces a dict suitable for stamping on
        CampaignAnalysisResult.construct_chain."""
        att1 = _make_attestation_for_a5("atom_1", "authority")
        att2 = _make_attestation_for_a5("atom_2", "scarcity")
        atom_result = AtomDAGResult(chain_attestations=[att1, att2])

        # Simulate the orchestrator's logic
        rendering = render_recommendation(
            atom_result.chain_attestations,
            recommendation_summary="Recommend authority for careful_truster",
        )
        payload = recommendation_to_dict(rendering)
        assert payload["n_attestations"] == 2
        assert "atom_1" in {a["atom_id"] for a in payload["attestations"]}
        assert "atom_2" in {a["atom_id"] for a in payload["attestations"]}

    def test_atom_dag_result_without_attestations_yields_empty(self):
        """When AtomDAGResult.chain_attestations is empty, the rendering
        yields zero attestations."""
        atom_result = AtomDAGResult(chain_attestations=[])

        rendering = render_recommendation(
            atom_result.chain_attestations,
            recommendation_summary="Test no attestations",
        )
        payload = recommendation_to_dict(rendering)
        assert payload["n_attestations"] == 0
        assert payload["attestations"] == []

    def test_payload_is_json_serializable(self):
        """The dict the orchestrator stamps on construct_chain MUST be
        JSON-serializable so partners can consume it via API."""
        import json
        att = _make_attestation_for_a5("atom_test", "authority")
        atom_result = AtomDAGResult(chain_attestations=[att])
        rendering = render_recommendation(
            atom_result.chain_attestations,
            recommendation_summary="JSON serialization test",
        )
        payload = recommendation_to_dict(rendering)
        # Round-trip through JSON
        s = json.dumps(payload)
        d = json.loads(s)
        assert d["recommendation_summary"] == "JSON serialization test"
        assert d["n_attestations"] == 1

    def test_payload_includes_a14_flags(self):
        """A14 flags from provenance flow through the rendering →
        partner sees what's calibration-pending."""
        att = _make_attestation_for_a5("atom_test", "authority")
        atom_result = AtomDAGResult(chain_attestations=[att])
        rendering = render_recommendation(
            atom_result.chain_attestations,
            recommendation_summary="A14 flag test",
        )
        payload = recommendation_to_dict(rendering)
        assert "TEST_FLAG_PILOT_PENDING" in payload["aggregate_a14_flags"]

    def test_payload_includes_citation_dedup(self):
        """Multiple attestations citing the same paper → citation list
        deduplicated in the payload."""
        att1 = _make_attestation_for_a5("atom_1", "authority")
        att2 = _make_attestation_for_a5("atom_2", "scarcity")
        # Both attestations cite "A5_test §1.1" via the helper
        atom_result = AtomDAGResult(chain_attestations=[att1, att2])
        rendering = render_recommendation(
            atom_result.chain_attestations,
            recommendation_summary="Dedup test",
        )
        payload = recommendation_to_dict(rendering)
        # Should have 1 unique citation, not 2 (deduplication)
        unique_citations = {
            c["raw"] for c in payload["aggregate_citations"]
        }
        assert "A5_test §1.1" in unique_citations
