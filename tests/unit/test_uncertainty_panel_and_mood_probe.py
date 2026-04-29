# =============================================================================
# ADAM Uncertainty Panel + Mood Probe Tests
# Location: tests/unit/test_uncertainty_panel_and_mood_probe.py
# =============================================================================

"""Tests for Loop B v0.1 commit 3 — Uncertainty Panel rendering +
session-start mood probe."""

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
from adam.intelligence.dialogue_ledger.mood_probe import (
    AffectivePolarity,
    MoodProbeGenerator,
    MoodProbeOption,
    MoodProbeResponse,
)
from adam.intelligence.dialogue_ledger.uncertainty_panel import (
    CONFIDENT_MIN_CASCADE_LEVEL,
    CONFIDENT_MIN_EDGE_COUNT,
    UncertaintyBucket,
    render_uncertainty_panel,
)


def _make_attestation(
    atom_id: str,
    a14_flags: list[str] | None = None,
    mechanism_adjustments: list[tuple[str, float]] | None = None,
) -> ChainAttestation:
    chain = [
        ConstructLink(
            source_construct="src",
            relation_type=RelationType.MODULATED_BY,
            target_construct="tgt",
            evidence_value=0.5,
            confidence=0.7,
            citation="test 1.0",
        )
    ]
    final = TypedEvidence(
        construct="construct",
        value=0.5,
        confidence=0.7,
        citation="test 1.0",
        calibration_status=CalibrationStatus.PINNED,
    )
    chain_link_ids = [chain[0].link_id]
    adjustments = [
        AdjustmentEvidence(
            mechanism_id=mech,
            adjustment_value=val,
            chain_links_responsible=chain_link_ids,
            confidence=0.7,
        )
        for mech, val in (mechanism_adjustments or [])
    ]
    return ChainAttestation(
        atom_id=atom_id,
        request_id="req_test",
        target_construct="construct",
        chain=chain,
        final_assessment=final,
        mechanism_adjustments=adjustments,
        provenance=ChainProvenance(
            atom_id=atom_id,
            a14_flags_active=list(a14_flags or []),
        ),
    )


# ============================================================================
# Cascade-evidence classification
# ============================================================================


class TestCascadeEvidenceClassification:

    def test_l3_with_sufficient_edges_lands_in_confident(self):
        panel = render_uncertainty_panel(
            cascade_level=3,
            cascade_edge_count=CONFIDENT_MIN_EDGE_COUNT + 50,
            cascade_primary_mechanism="authority",
            cascade_confidence=0.8,
        )
        assert any(
            "L3" in item.claim and "supported by direct edge evidence" in item.claim
            for item in panel.confident
        )

    def test_l3_with_sparse_edges_lands_in_uncertain(self):
        panel = render_uncertainty_panel(
            cascade_level=3,
            cascade_edge_count=10,  # below threshold
        )
        assert any(
            "sparse" in item.claim.lower()
            for item in panel.uncertain
        )

    def test_l1_lands_in_uncertain(self):
        panel = render_uncertainty_panel(cascade_level=1, cascade_edge_count=0)
        assert any(
            "L1" in item.claim and "archetype priors" in item.claim
            for item in panel.uncertain
        )

    def test_l2_lands_in_uncertain(self):
        panel = render_uncertainty_panel(cascade_level=2, cascade_edge_count=0)
        assert any(
            "L2" in item.claim
            for item in panel.uncertain
        )

    def test_l4_lands_in_uncertain(self):
        panel = render_uncertainty_panel(
            cascade_level=4,
            cascade_edge_count=0,
        )
        assert any(
            "L4" in item.claim and "inferential transfer" in item.claim
            for item in panel.uncertain
        )

    def test_no_cascade_level_no_cascade_item(self):
        panel = render_uncertainty_panel(cascade_level=None)
        # No item mentioning cascade in any bucket
        all_items = panel.confident + panel.uncertain + panel.possibly_wrong
        assert not any("Cascade" in item.claim for item in all_items)


# ============================================================================
# Atom-evidence classification
# ============================================================================


class TestAtomEvidenceClassification:

    def test_high_confidence_atom_in_confident(self):
        panel = render_uncertainty_panel(
            atom_results={
                "atom_authority": {"confidence": 0.85, "reasoning": "x"},
            },
        )
        assert any(
            "atom_authority" in item.claim
            for item in panel.confident
        )

    def test_low_confidence_atom_in_possibly_wrong(self):
        panel = render_uncertainty_panel(
            atom_results={
                "atom_weak": {"confidence": 0.30},
            },
        )
        assert any(
            "atom_weak" in item.claim
            for item in panel.possibly_wrong
        )

    def test_mid_confidence_atom_in_uncertain(self):
        panel = render_uncertainty_panel(
            atom_results={
                "atom_mid": {"confidence": 0.55},
            },
        )
        assert any(
            "atom_mid" in item.claim
            for item in panel.uncertain
        )

    def test_atom_without_confidence_skipped(self):
        panel = render_uncertainty_panel(
            atom_results={
                "atom_no_conf": {"reasoning": "x"},  # missing confidence
            },
        )
        all_items = panel.confident + panel.uncertain + panel.possibly_wrong
        assert not any("atom_no_conf" in item.claim for item in all_items)


# ============================================================================
# A14 flag surfacing
# ============================================================================


class TestA14FlagSurfacing:

    def test_attestation_a14_flag_lands_in_uncertain(self):
        att = _make_attestation(
            atom_id="atom_test",
            a14_flags=["TEST_FLAG_PILOT_PENDING"],
        )
        panel = render_uncertainty_panel(chain_attestations=[att])
        assert any(
            "TEST_FLAG_PILOT_PENDING" in item.claim
            for item in panel.uncertain
        )

    def test_decision_level_a14_flag_lands_in_uncertain(self):
        panel = render_uncertainty_panel(
            a14_flags_active=["DECISION_LEVEL_FLAG_PILOT_PENDING"],
        )
        assert any(
            "DECISION_LEVEL_FLAG_PILOT_PENDING" in item.claim
            for item in panel.uncertain
        )

    def test_multiple_atoms_emit_same_flag_dedupes(self):
        """Two atoms emitting the same flag → one Uncertain item with
        both atom IDs in evidence_trace."""
        att1 = _make_attestation("atom_a", a14_flags=["SHARED_FLAG"])
        att2 = _make_attestation("atom_b", a14_flags=["SHARED_FLAG"])
        panel = render_uncertainty_panel(chain_attestations=[att1, att2])
        flag_items = [
            item for item in panel.uncertain
            if "SHARED_FLAG" in item.claim
        ]
        assert len(flag_items) == 1
        assert "atom_a" in flag_items[0].evidence_trace
        assert "atom_b" in flag_items[0].evidence_trace


# ============================================================================
# Mechanism-score divergence
# ============================================================================


class TestMechanismScoreDivergence:

    def test_close_top_two_lands_in_uncertain(self):
        panel = render_uncertainty_panel(
            mechanism_scores={
                "authority": 0.62,
                "scarcity": 0.61,
                "social_proof": 0.30,
            },
        )
        assert any(
            "Mechanism choice between" in item.claim
            for item in panel.uncertain
        )

    def test_decisive_winner_no_uncertainty_item(self):
        panel = render_uncertainty_panel(
            mechanism_scores={
                "authority": 0.85,
                "scarcity": 0.30,
            },
        )
        assert not any(
            "Mechanism choice between" in item.claim
            for item in panel.uncertain + panel.confident + panel.possibly_wrong
        )


# ============================================================================
# Conflict detection
# ============================================================================


class TestAttestationConflicts:

    def test_conflicting_signs_land_in_possibly_wrong(self):
        att_pos = _make_attestation(
            "atom_raise",
            mechanism_adjustments=[("authority", 0.2)],
        )
        att_neg = _make_attestation(
            "atom_lower",
            mechanism_adjustments=[("authority", -0.15)],
        )
        panel = render_uncertainty_panel(
            chain_attestations=[att_pos, att_neg],
        )
        assert any(
            "conflicting" in item.claim.lower()
            and "authority" in item.claim
            for item in panel.possibly_wrong
        )

    def test_consistent_signs_no_conflict_item(self):
        att1 = _make_attestation(
            "atom_a",
            mechanism_adjustments=[("authority", 0.2)],
        )
        att2 = _make_attestation(
            "atom_b",
            mechanism_adjustments=[("authority", 0.1)],
        )
        panel = render_uncertainty_panel(
            chain_attestations=[att1, att2],
        )
        assert not any(
            "conflicting" in item.claim.lower()
            for item in panel.possibly_wrong
        )


# ============================================================================
# Empty / null inputs
# ============================================================================


class TestEmptyInputs:

    def test_empty_inputs_yield_empty_panel(self):
        panel = render_uncertainty_panel()
        assert panel.total_items == 0
        assert panel.confident == []
        assert panel.uncertain == []
        assert panel.possibly_wrong == []

    def test_panel_summary_correct(self):
        panel = render_uncertainty_panel(
            cascade_level=1,
            atom_results={"atom_high": {"confidence": 0.9}},
        )
        assert panel.panel_summary["confident_count"] == 1  # atom_high
        assert panel.panel_summary["uncertain_count"] == 1  # cascade L1


# ============================================================================
# Mood probe — generator + capture
# ============================================================================


class TestMoodProbe:

    def test_render_produces_two_options_with_one_polarity_each(self):
        gen = MoodProbeGenerator()
        q = gen.render(seed=42)
        polarities = {q.option_a.polarity, q.option_b.polarity}
        assert polarities == {
            AffectivePolarity.POSITIVE,
            AffectivePolarity.NEGATIVE,
        }

    def test_render_default_countdown(self):
        gen = MoodProbeGenerator()
        q = gen.render(seed=42)
        assert q.countdown_seconds == gen.DEFAULT_COUNTDOWN_SECONDS

    def test_render_seed_produces_deterministic_output(self):
        gen = MoodProbeGenerator()
        q1 = gen.render(seed=42)
        q2 = gen.render(seed=42)
        # Same seed → same option labels (positions may swap but content
        # should be deterministic given seeded Random)
        assert {q1.option_a.label, q1.option_b.label} == {
            q2.option_a.label, q2.option_b.label,
        }

    def test_capture_positive_choice_yields_high_mood_index(self):
        gen = MoodProbeGenerator()
        q = gen.render(seed=42)
        # Identify which option is positive
        positive_idx = "a" if q.option_a.polarity == AffectivePolarity.POSITIVE else "b"
        r = MoodProbeResponse(
            probe_id=q.probe_id,
            chosen=positive_idx,
            latency_ms=1500,  # fast
        )
        state = gen.capture(
            session_id="s:test", user_id="u:test", question=q, response=r,
        )
        assert state.mood_index == 1.0
        assert state.confidence == gen.FAST_RESPONSE_CONFIDENCE

    def test_capture_negative_choice_yields_low_mood_index(self):
        gen = MoodProbeGenerator()
        q = gen.render(seed=42)
        negative_idx = "a" if q.option_a.polarity == AffectivePolarity.NEGATIVE else "b"
        r = MoodProbeResponse(
            probe_id=q.probe_id,
            chosen=negative_idx,
            latency_ms=1500,
        )
        state = gen.capture(
            session_id="s:test", user_id="u:test", question=q, response=r,
        )
        assert state.mood_index == 0.0

    def test_capture_deadline_hit_yields_neutral_low_confidence(self):
        gen = MoodProbeGenerator()
        q = gen.render(seed=42)
        r = MoodProbeResponse(
            probe_id=q.probe_id,
            chosen=None,
            latency_ms=5000,
            deadline_hit=True,
        )
        state = gen.capture(
            session_id="s:test", user_id="u:test", question=q, response=r,
        )
        assert state.mood_index == 0.5
        assert state.confidence == gen.DEADLINE_HIT_CONFIDENCE
        assert state.deadline_hit

    def test_capture_slow_response_lower_confidence(self):
        gen = MoodProbeGenerator()
        q = gen.render(seed=42)
        positive_idx = "a" if q.option_a.polarity == AffectivePolarity.POSITIVE else "b"
        # Latency at 80% of countdown → slow response
        slow_latency = int(q.countdown_seconds * 1000 * 0.8)
        r = MoodProbeResponse(
            probe_id=q.probe_id,
            chosen=positive_idx,
            latency_ms=slow_latency,
        )
        state = gen.capture(
            session_id="s:test", user_id="u:test", question=q, response=r,
        )
        assert state.confidence == gen.SLOW_RESPONSE_CONFIDENCE

    def test_capture_rejects_mismatched_probe_id(self):
        gen = MoodProbeGenerator()
        q = gen.render(seed=42)
        r = MoodProbeResponse(probe_id="mood:wrong", chosen="a", latency_ms=100)
        with pytest.raises(ValueError, match="probe_id"):
            gen.capture(
                session_id="s", user_id="u", question=q, response=r,
            )

    def test_capture_rejects_chosen_with_deadline_hit(self):
        gen = MoodProbeGenerator()
        q = gen.render(seed=42)
        r = MoodProbeResponse(
            probe_id=q.probe_id, chosen="a",
            latency_ms=5000, deadline_hit=True,
        )
        with pytest.raises(ValueError, match="None when deadline_hit"):
            gen.capture(
                session_id="s", user_id="u", question=q, response=r,
            )

    def test_constructor_requires_at_least_one_option_per_polarity(self):
        with pytest.raises(ValueError, match="positive AND"):
            MoodProbeGenerator(positive_options=[])
