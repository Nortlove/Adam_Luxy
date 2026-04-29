# =============================================================================
# ADAM Agency Dashboard Aggregator Tests
# Location: tests/unit/test_agency_dashboard.py
# =============================================================================

"""Tests for task #33 — agency-facing dashboard aggregator."""

from __future__ import annotations

import json

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
from adam.intelligence.agency_dashboard import (
    attention_inversion_test_result,
    build_agency_dashboard_payload,
)
from adam.intelligence.chain_rendering import render_recommendation
from adam.intelligence.dialogue_ledger.mood_probe import (
    AffectivePolarity,
    MoodProbeGenerator,
    MoodProbeResponse,
)
from adam.intelligence.dialogue_ledger.uncertainty_panel import (
    render_uncertainty_panel,
)
from adam.intelligence.mechanism_rotation import (
    CellEvidence,
    RotationRegistry,
    TriggerCondition,
    register_rotation,
)
from adam.intelligence.mechanism_taxonomy import MechanismRouteCategory
from adam.intelligence.mechanism_taxonomy_runtime import (
    TaxonomyConditionalAccumulator,
    tag_decision,
)
from adam.intelligence.page_attentional_posture_substrate import (
    PageAttentionalPostureAccumulator,
    PageObservation,
)


def _make_chain_attestation() -> ChainAttestation:
    link = ConstructLink(
        source_construct="src",
        relation_type=RelationType.CREATES_NEED_FOR,
        target_construct="tgt",
        evidence_value=0.6,
        confidence=0.8,
        citation="test §1.1",
    )
    final = TypedEvidence(
        construct="x", value=0.6, confidence=0.7,
        citation="test §1.1", calibration_status=CalibrationStatus.PINNED,
    )
    return ChainAttestation(
        atom_id="atom_test",
        request_id="req_test",
        target_construct="tgt",
        chain=[link],
        final_assessment=final,
        mechanism_adjustments=[
            AdjustmentEvidence(
                mechanism_id="authority",
                adjustment_value=0.1,
                chain_links_responsible=[link.link_id],
                confidence=0.8,
            )
        ],
        provenance=ChainProvenance(
            atom_id="atom_test",
            a14_flags_active=["TEST_FLAG_PILOT_PENDING"],
        ),
    )


# ============================================================================
# Minimum payload — decision_summary only
# ============================================================================


class TestMinimumPayload:

    def test_decision_summary_required(self):
        with pytest.raises(ValueError, match="decision_summary"):
            build_agency_dashboard_payload(decision_summary={})

    def test_minimum_payload(self):
        payload = build_agency_dashboard_payload(
            decision_summary={
                "request_id": "req_001",
                "primary_mechanism": "authority",
                "archetype": "careful_truster",
            },
        )
        assert "generated_at" in payload
        assert payload["decision_summary"]["primary_mechanism"] == "authority"
        # Optional sections absent
        assert "uncertainty_panel" not in payload
        assert "construct_chain" not in payload

    def test_payload_json_serializable(self):
        payload = build_agency_dashboard_payload(
            decision_summary={"request_id": "x"},
        )
        # Round-trip through JSON
        s = json.dumps(payload)
        d = json.loads(s)
        assert d["decision_summary"]["request_id"] == "x"


# ============================================================================
# Uncertainty panel section
# ============================================================================


class TestUncertaintyPanelSection:

    def test_panel_serialized_into_payload(self):
        panel = render_uncertainty_panel(
            cascade_level=3,
            cascade_edge_count=200,
            cascade_primary_mechanism="authority",
            atom_results={"atom_x": {"confidence": 0.85}},
        )
        payload = build_agency_dashboard_payload(
            decision_summary={"request_id": "x"},
            uncertainty_panel=panel,
        )
        assert "uncertainty_panel" in payload
        assert "confident" in payload["uncertainty_panel"]
        assert "uncertain" in payload["uncertainty_panel"]
        assert "possibly_wrong" in payload["uncertainty_panel"]
        assert "summary" in payload["uncertainty_panel"]

    def test_panel_section_is_json_serializable(self):
        panel = render_uncertainty_panel(cascade_level=1)
        payload = build_agency_dashboard_payload(
            decision_summary={"request_id": "x"},
            uncertainty_panel=panel,
        )
        # Round-trip
        json.dumps(payload)


# ============================================================================
# Chain rendering section
# ============================================================================


class TestChainRenderingSection:

    def test_chain_rendering_serialized(self):
        att = _make_chain_attestation()
        rendering = render_recommendation(
            [att], recommendation_summary="Test recommendation",
        )
        payload = build_agency_dashboard_payload(
            decision_summary={"request_id": "x"},
            chain_rendering=rendering,
        )
        assert "construct_chain" in payload
        assert payload["construct_chain"]["recommendation_summary"] == "Test recommendation"
        assert payload["construct_chain"]["n_attestations"] == 1
        # Round-trip
        json.dumps(payload)


# ============================================================================
# Rotation events section
# ============================================================================


class TestRotationEventsSection:

    def test_empty_registry_yields_empty_events(self):
        registry = RotationRegistry()
        payload = build_agency_dashboard_payload(
            decision_summary={"request_id": "x"},
            rotation_registry=registry,
        )
        assert payload["rotation_events"] == []
        assert payload["rotation_events_count"] == 0

    def test_triggered_event_serialized(self):
        registry = RotationRegistry()
        c = register_rotation(
            archetype="careful_truster",
            from_mechanism="authority",
            to_mechanism="brand_trust_evidence",
            rationale="test rotation",
            trigger_condition=TriggerCondition.EDGE_COUNT_THRESHOLD,
            trigger_threshold=50.0,
            evaluation_window_days=14,
            registered_by="test",
        )
        registry.register(c)

        from_ev = CellEvidence(
            archetype="careful_truster", page_context=None,
            mechanism="authority", edge_count=80,
            cate_estimate=0.10,
        )
        to_ev = CellEvidence(
            archetype="careful_truster", page_context=None,
            mechanism="brand_trust_evidence", edge_count=70,
            cate_estimate=0.18,
        )
        registry.update_status_from_evidence(c.rotation_id, from_ev, to_ev)

        payload = build_agency_dashboard_payload(
            decision_summary={"request_id": "x"},
            rotation_registry=registry,
        )
        events = payload["rotation_events"]
        assert len(events) == 1
        assert events[0]["from_mechanism"] == "authority"
        assert events[0]["to_mechanism"] == "brand_trust_evidence"
        assert events[0]["from_cate_estimate"] == 0.10
        assert events[0]["to_cate_estimate"] == 0.18


# ============================================================================
# Attention-inversion diagonals section
# ============================================================================


class TestDiagonalsSection:

    def test_diagonals_serialized(self):
        acc = TaxonomyConditionalAccumulator()
        # Add some matched + mismatched data
        blend_tag = tag_decision("automatic_evaluation")
        vig_tag = tag_decision("attention_dynamics")
        for _ in range(60):
            acc.record_outcome(blend_tag, "blend_compatible",
                               converted=True, backfired=False)
            acc.record_outcome(vig_tag, "blend_compatible",
                               converted=False, backfired=False)

        payload = build_agency_dashboard_payload(
            decision_summary={"request_id": "x"},
            taxonomy_accumulator=acc,
        )
        diag = payload["attention_inversion_diagonals"]
        assert len(diag["matched"]) >= 1
        assert len(diag["mismatched"]) >= 1
        assert "matched_aggregate_conversion_rate" in diag
        assert "mismatched_aggregate_conversion_rate" in diag


# ============================================================================
# Page posture section
# ============================================================================


class TestPagePostureSection:

    def test_page_posture_summary_counts(self):
        acc = PageAttentionalPostureAccumulator()
        acc.record(PageObservation(
            page_url="x", posture_float=-0.5, posture_confidence=0.8,
            author_id="author:1", publication_id="pub:1",
        ))
        acc.record(PageObservation(
            page_url="y", posture_float=0.5, posture_confidence=0.8,
            author_id="author:2", section_id="section:1",
        ))
        payload = build_agency_dashboard_payload(
            decision_summary={"request_id": "x"},
            page_posture_accumulator=acc,
        )
        pp = payload["page_posture"]
        assert pp["author_predictions_count"] == 2
        assert pp["publication_predictions_count"] == 1
        assert pp["section_predictions_count"] == 1


# ============================================================================
# Session mood
# ============================================================================


class TestSessionMoodSection:

    def test_mood_serialized(self):
        gen = MoodProbeGenerator()
        q = gen.render(seed=42)
        positive_idx = "a" if q.option_a.polarity == AffectivePolarity.POSITIVE else "b"
        r = MoodProbeResponse(
            probe_id=q.probe_id, chosen=positive_idx, latency_ms=1500,
        )
        state = gen.capture(
            session_id="s", user_id="u", question=q, response=r,
        )

        payload = build_agency_dashboard_payload(
            decision_summary={"request_id": "x"},
            session_mood=state,
        )
        assert payload["session_mood"]["mood_index"] == 1.0

    def test_no_mood_section_when_state_none(self):
        payload = build_agency_dashboard_payload(
            decision_summary={"request_id": "x"},
            session_mood=None,
        )
        assert "session_mood" not in payload


# ============================================================================
# A14 flags
# ============================================================================


class TestA14FlagsSection:

    def test_flags_included_when_present(self):
        payload = build_agency_dashboard_payload(
            decision_summary={"request_id": "x"},
            a14_flags_active=["FLAG_X_PILOT_PENDING"],
        )
        assert payload["a14_flags_active"] == ["FLAG_X_PILOT_PENDING"]

    def test_no_flags_section_when_empty(self):
        payload = build_agency_dashboard_payload(
            decision_summary={"request_id": "x"},
            a14_flags_active=[],
        )
        assert "a14_flags_active" not in payload


# ============================================================================
# attention_inversion_test_result helper
# ============================================================================


class TestAttentionInversionTestResult:

    def test_insufficient_data_note(self):
        acc = TaxonomyConditionalAccumulator()
        result = attention_inversion_test_result(acc)
        assert result["supports_foundation_prediction"] is False
        assert "Insufficient data" in result["interpretive_note"]
        assert result["n_matched"] == 0
        assert result["n_mismatched"] == 0

    def test_supports_prediction_when_matched_higher(self):
        acc = TaxonomyConditionalAccumulator()
        blend_tag = tag_decision("automatic_evaluation")
        vig_tag = tag_decision("attention_dynamics")
        # Matched cells: high conversion (35/50 = 70%)
        for i in range(50):
            acc.record_outcome(
                blend_tag, "blend_compatible",
                converted=(i < 35), backfired=False,
            )
            acc.record_outcome(
                vig_tag, "vigilance_activating",
                converted=(i < 30), backfired=False,
            )
        # Mismatched cells: lower conversion (20/50 = 40%)
        for i in range(50):
            acc.record_outcome(
                blend_tag, "vigilance_activating",
                converted=(i < 20), backfired=False,
            )
            acc.record_outcome(
                vig_tag, "blend_compatible",
                converted=(i < 15), backfired=False,
            )

        result = attention_inversion_test_result(acc)
        assert result["supports_foundation_prediction"] is True
        assert result["matched_conversion_rate"] > result["mismatched_conversion_rate"]
        assert "supported" in result["interpretive_note"]

    def test_does_not_support_when_mismatched_higher(self):
        acc = TaxonomyConditionalAccumulator()
        blend_tag = tag_decision("automatic_evaluation")
        vig_tag = tag_decision("attention_dynamics")
        # Reversed: matched LOSES, mismatched WINS
        for i in range(50):
            acc.record_outcome(
                blend_tag, "blend_compatible",
                converted=(i < 10), backfired=False,
            )
            acc.record_outcome(
                vig_tag, "vigilance_activating",
                converted=(i < 10), backfired=False,
            )
        for i in range(50):
            acc.record_outcome(
                blend_tag, "vigilance_activating",
                converted=(i < 35), backfired=False,
            )
            acc.record_outcome(
                vig_tag, "blend_compatible",
                converted=(i < 30), backfired=False,
            )

        result = attention_inversion_test_result(acc)
        assert result["supports_foundation_prediction"] is False
        assert result["matched_conversion_rate"] < result["mismatched_conversion_rate"]
        assert "NOT supported" in result["interpretive_note"]


# ============================================================================
# Full integration — all sections in one payload
# ============================================================================


class TestFullPayload:

    def test_full_payload_round_trips_through_json(self):
        # Build all sections
        panel = render_uncertainty_panel(cascade_level=3, cascade_edge_count=200)
        att = _make_chain_attestation()
        rendering = render_recommendation(
            [att], recommendation_summary="Test full payload",
        )
        registry = RotationRegistry()
        acc = TaxonomyConditionalAccumulator()
        page_acc = PageAttentionalPostureAccumulator()

        gen = MoodProbeGenerator()
        q = gen.render(seed=42)
        positive_idx = "a" if q.option_a.polarity == AffectivePolarity.POSITIVE else "b"
        mood_state = gen.capture(
            session_id="s", user_id="u",
            question=q,
            response=MoodProbeResponse(
                probe_id=q.probe_id, chosen=positive_idx, latency_ms=1500,
            ),
        )

        payload = build_agency_dashboard_payload(
            decision_summary={
                "request_id": "req_001",
                "primary_mechanism": "authority",
                "archetype": "careful_truster",
                "cascade_level": 3,
            },
            uncertainty_panel=panel,
            chain_rendering=rendering,
            rotation_registry=registry,
            taxonomy_accumulator=acc,
            page_posture_accumulator=page_acc,
            session_mood=mood_state,
            a14_flags_active=["FLAG_X_PILOT_PENDING"],
        )

        # Round-trip through JSON
        s = json.dumps(payload)
        d = json.loads(s)
        assert d["decision_summary"]["primary_mechanism"] == "authority"
        assert d["uncertainty_panel"] is not None
        assert d["construct_chain"]["recommendation_summary"] == "Test full payload"
        assert d["rotation_events"] == []
        assert d["attention_inversion_diagonals"] is not None
        assert d["page_posture"] is not None
        assert d["session_mood"]["mood_index"] == 1.0
        assert d["a14_flags_active"] == ["FLAG_X_PILOT_PENDING"]
