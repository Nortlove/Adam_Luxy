# =============================================================================
# ADAM Construct-Chain Rendering Tests
# Location: tests/unit/test_chain_rendering.py
# =============================================================================

"""Tests for task #25 — Construct-chain rendering at partner interface.

Foundation §4.3 commits "every atom that emits a scalar must also emit
the chain of construct activations that produced it" — this rendering
layer is what materializes that chain for partner consumption.

Coverage:
  - Citation parsing across common formats
  - Chain step rendering (one ConstructLink → one ChainStepRendering)
  - Final assessment + adjustment rendering
  - Full attestation rendering — all fields populated
  - Multi-attestation aggregation (citations + A14 flags deduped)
  - Sentence + paragraph + partner-text formats
  - JSON-friendly serialization
  - Discipline anchor: every claim text traces back to structured input
"""

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
    ChainAttestationRendering,
    ChainStepRendering,
    Citation,
    FinalAssessmentRendering,
    MechanismAdjustmentRendering,
    RecommendationChainRendering,
    attestation_to_dict,
    recommendation_to_dict,
    render_chain_attestation,
    render_chain_step,
    render_final_assessment,
    render_mechanism_adjustment,
    render_recommendation,
)


# ============================================================================
# Citation parsing
# ============================================================================


class TestCitation:

    def test_parse_section_with_section_marker(self):
        c = Citation.parse("Cialdini 2007 §2.4")
        assert c.paper == "Cialdini 2007"
        assert c.section == "§2.4"

    def test_parse_section_with_sec_word(self):
        c = Citation.parse("Bargh 1990 sec 3")
        assert c.paper == "Bargh 1990"
        assert c.section == "sec 3"

    def test_parse_no_section(self):
        c = Citation.parse("no citation")
        assert c.paper == "no citation"
        assert c.section == ""

    def test_parse_preserves_raw(self):
        raw = "Wicklund 1974 §IV.2"
        c = Citation.parse(raw)
        assert c.raw == raw


# ============================================================================
# Chain step rendering
# ============================================================================


def _make_link(
    source: str = "src",
    relation: RelationType = RelationType.CREATES_NEED_FOR,
    target: str = "tgt",
    evidence: float = 0.6,
    confidence: float = 0.7,
    citation: str = "test 2024 §1.2",
    calibration: CalibrationStatus = CalibrationStatus.PINNED,
) -> ConstructLink:
    return ConstructLink(
        source_construct=source,
        relation_type=relation,
        target_construct=target,
        evidence_value=evidence,
        confidence=confidence,
        citation=citation,
        calibration_status=calibration,
    )


class TestChainStepRendering:

    def test_render_basic(self):
        link = _make_link(
            source="uncertainty_intolerance",
            relation=RelationType.CREATES_NEED_FOR,
            target="need_for_closure",
            evidence=0.8,
            confidence=0.7,
            citation="Bargh 1990 §3.2",
        )
        step = render_chain_step(link)
        assert step.source_construct == "uncertainty_intolerance"
        assert step.target_construct == "need_for_closure"
        assert step.relation_verb == "creates need for"
        assert step.evidence_value == 0.8
        assert step.confidence == 0.7
        assert step.citation.paper == "Bargh 1990"

    def test_relation_verbs_for_all_relation_types(self):
        """Every RelationType has a canonical verb mapping (no fallback
        to enum.value)."""
        for rel in RelationType:
            link = _make_link(relation=rel)
            step = render_chain_step(link)
            # The verb should be a human-readable phrase, not the
            # SCREAMING_SNAKE enum name
            assert " " in step.relation_verb or step.relation_verb.islower()
            # And NOT contain the underscore-laden enum form
            assert step.relation_verb != rel.value

    def test_as_sentence_includes_all_components(self):
        link = _make_link(
            source="uncertainty_intolerance",
            relation=RelationType.CREATES_NEED_FOR,
            target="need_for_closure",
            evidence=0.75,
            confidence=0.8,
            citation="Bargh 1990 §3.2",
        )
        step = render_chain_step(link)
        sentence = step.as_sentence()
        assert "uncertainty_intolerance" in sentence
        assert "creates need for" in sentence
        assert "need_for_closure" in sentence
        assert "Bargh 1990 §3.2" in sentence
        assert "0.75" in sentence
        assert "0.80" in sentence


# ============================================================================
# Final assessment rendering
# ============================================================================


class TestFinalAssessmentRendering:

    def test_render_basic(self):
        final = TypedEvidence(
            construct="closure_satisfied_by_authority",
            value=0.65,
            confidence=0.78,
            citation="Cialdini 2007 §2.4",
            calibration_status=CalibrationStatus.PINNED,
        )
        rendering = render_final_assessment(final)
        assert rendering.construct == "closure_satisfied_by_authority"
        assert rendering.value == 0.65
        assert rendering.calibration_status == CalibrationStatus.PINNED
        assert rendering.citation.paper == "Cialdini 2007"

    def test_pilot_pending_status_preserved(self):
        final = TypedEvidence(
            construct="x",
            value=0.5,
            confidence=0.7,
            citation="ref",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        )
        rendering = render_final_assessment(final)
        assert rendering.calibration_status == CalibrationStatus.PILOT_PENDING

    def test_as_sentence_shows_calibration_status(self):
        final = TypedEvidence(
            construct="closure_satisfied",
            value=0.65,
            confidence=0.78,
            citation="Cialdini 2007 §2.4",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        )
        rendering = render_final_assessment(final)
        sentence = rendering.as_sentence()
        assert "PILOT_PENDING" in sentence or "pilot_pending" in sentence


# ============================================================================
# Mechanism adjustment rendering
# ============================================================================


class TestMechanismAdjustmentRendering:

    def test_positive_adjustment_direction_raise(self):
        adj = AdjustmentEvidence(
            mechanism_id="authority",
            adjustment_value=0.15,
            chain_links_responsible=["link:1"],
            confidence=0.7,
        )
        rendering = render_mechanism_adjustment(adj)
        assert rendering.direction == "raise"
        assert rendering.adjustment_value == 0.15

    def test_negative_adjustment_direction_lower(self):
        adj = AdjustmentEvidence(
            mechanism_id="scarcity",
            adjustment_value=-0.20,
            chain_links_responsible=["link:1", "link:2"],
            confidence=0.65,
        )
        rendering = render_mechanism_adjustment(adj)
        assert rendering.direction == "lower"

    def test_near_zero_adjustment_neutral(self):
        adj = AdjustmentEvidence(
            mechanism_id="social_proof",
            adjustment_value=1e-10,
            chain_links_responsible=["link:1"],
            confidence=0.5,
        )
        rendering = render_mechanism_adjustment(adj)
        assert rendering.direction == "neutral"

    def test_as_sentence_shows_magnitude_and_link_count(self):
        adj = AdjustmentEvidence(
            mechanism_id="authority",
            adjustment_value=0.15,
            chain_links_responsible=["link:1", "link:2"],
            confidence=0.7,
        )
        rendering = render_mechanism_adjustment(adj)
        sentence = rendering.as_sentence()
        assert "raise" in sentence
        assert "authority" in sentence
        assert "0.150" in sentence  # magnitude
        assert "2 link" in sentence  # link count


# ============================================================================
# Full attestation rendering
# ============================================================================


def _make_attestation(
    *,
    atom_id: str = "atom_test",
    a14_flags: list[str] | None = None,
    n_steps: int = 1,
    mechanism_adjustments: list[tuple[str, float]] | None = None,
) -> ChainAttestation:
    chain = []
    for i in range(n_steps):
        chain.append(_make_link(
            source=f"src_{i}",
            target=f"tgt_{i}",
            citation=f"test_paper §{i}.1",
        ))
    final = TypedEvidence(
        construct="final_construct",
        value=0.7,
        confidence=0.8,
        citation="final_paper §X",
        calibration_status=CalibrationStatus.PINNED,
    )
    chain_link_ids = [c.link_id for c in chain]
    adj_ev = [
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
        target_construct="target",
        chain=chain,
        final_assessment=final,
        mechanism_adjustments=adj_ev,
        provenance=ChainProvenance(
            atom_id=atom_id,
            a14_flags_active=list(a14_flags or []),
        ),
    )


class TestAttestationRendering:

    def test_render_basic(self):
        att = _make_attestation(
            atom_id="atom_authority",
            n_steps=2,
            mechanism_adjustments=[("authority", 0.15)],
            a14_flags=["FLAG_PILOT_PENDING"],
        )
        rendering = render_chain_attestation(att)
        assert rendering.atom_id == "atom_authority"
        assert len(rendering.chain_steps) == 2
        assert len(rendering.mechanism_adjustments) == 1
        assert rendering.a14_flags == ["FLAG_PILOT_PENDING"]

    def test_citations_deduped_across_chain_and_final(self):
        """A citation that appears in multiple links should appear once
        in the citations list."""
        c1 = _make_link(citation="shared_paper §1")
        c2 = _make_link(citation="shared_paper §1")  # duplicate raw
        c3 = _make_link(citation="other_paper §2")
        final = TypedEvidence(
            construct="x",
            value=0.5,
            confidence=0.7,
            citation="other_paper §2",  # also duplicate
            calibration_status=CalibrationStatus.PINNED,
        )
        att = ChainAttestation(
            atom_id="atom_test",
            request_id="req",
            target_construct="t",
            chain=[c1, c2, c3],
            final_assessment=final,
            mechanism_adjustments=[],
            provenance=ChainProvenance(atom_id="atom_test"),
        )
        rendering = render_chain_attestation(att)
        # Should have only 2 unique citation raws
        raws = {c.raw for c in rendering.citations}
        assert raws == {"shared_paper §1", "other_paper §2"}

    def test_summary_sentence_mentions_atom_and_link_count(self):
        att = _make_attestation(atom_id="atom_x", n_steps=3)
        rendering = render_chain_attestation(att)
        assert "atom_x" in rendering.summary_sentence
        assert "3 construct link" in rendering.summary_sentence

    def test_as_paragraph_includes_all_steps(self):
        att = _make_attestation(
            atom_id="atom_x",
            n_steps=2,
            mechanism_adjustments=[("authority", 0.1)],
            a14_flags=["FLAG_A_PILOT_PENDING"],
        )
        rendering = render_chain_attestation(att)
        paragraph = rendering.as_paragraph()
        assert "atom_x" in paragraph
        assert "→" in paragraph  # chain step indicator
        assert "⇒" in paragraph  # final assessment indicator
        assert "Mechanism adjustments" in paragraph
        assert "FLAG_A_PILOT_PENDING" in paragraph


# ============================================================================
# Recommendation-level (multi-attestation) rendering
# ============================================================================


class TestRecommendationRendering:

    def test_aggregates_citations_across_attestations(self):
        a1 = _make_attestation(atom_id="atom_a")
        a1.chain[0].citation = "paper_a §1"
        a1.final_assessment.citation = "paper_a §1"
        # Manually adjust to ensure only one unique citation
        a2 = _make_attestation(atom_id="atom_b")
        # paper_b in a2 (default fixtures use test_paper §0.1 which differs)

        rec = render_recommendation(
            [a1, a2],
            recommendation_summary="Recommend authority for careful_truster",
        )
        # At least 2 distinct citations appear (some from each)
        raws = {c.raw for c in rec.aggregate_citations}
        assert len(raws) >= 2

    def test_aggregates_a14_flags_deduped(self):
        a1 = _make_attestation(atom_id="atom_a", a14_flags=["FLAG_X", "FLAG_Y"])
        a2 = _make_attestation(atom_id="atom_b", a14_flags=["FLAG_Y", "FLAG_Z"])
        rec = render_recommendation(
            [a1, a2],
            recommendation_summary="Test recommendation",
        )
        # FLAG_Y appears once in aggregate
        assert sorted(rec.aggregate_a14_flags) == ["FLAG_X", "FLAG_Y", "FLAG_Z"]

    def test_n_attestations_correct(self):
        atts = [_make_attestation(atom_id=f"atom_{i}") for i in range(3)]
        rec = render_recommendation(atts, recommendation_summary="x")
        assert rec.n_attestations == 3

    def test_partner_text_includes_all_attestations(self):
        a1 = _make_attestation(atom_id="atom_aaa")
        a2 = _make_attestation(atom_id="atom_bbb")
        rec = render_recommendation(
            [a1, a2],
            recommendation_summary="Recommend authority for careful_truster",
        )
        text = rec.as_partner_text()
        assert "Recommend authority for careful_truster" in text
        assert "atom_aaa" in text
        assert "atom_bbb" in text
        assert "2 atoms" in text  # plural

    def test_partner_text_singular_attestation(self):
        a1 = _make_attestation(atom_id="atom_only")
        rec = render_recommendation([a1], recommendation_summary="x")
        text = rec.as_partner_text()
        assert "1 atom" in text and "atoms" not in text.split("1 atom")[1].split("\n")[0]

    def test_partner_text_includes_aggregate_a14_flags(self):
        a1 = _make_attestation(atom_id="atom_a", a14_flags=["FLAG_X"])
        rec = render_recommendation([a1], recommendation_summary="x")
        text = rec.as_partner_text()
        assert "Calibration-pending" in text
        assert "FLAG_X" in text


# ============================================================================
# JSON serialization
# ============================================================================


class TestJSONSerialization:

    def test_attestation_to_dict_is_json_serializable(self):
        import json
        att = _make_attestation(
            atom_id="atom_x",
            n_steps=2,
            mechanism_adjustments=[("authority", 0.1)],
            a14_flags=["FLAG_PILOT_PENDING"],
        )
        rendering = render_chain_attestation(att)
        d = attestation_to_dict(rendering)
        # Round-trip through JSON to confirm no non-serializable values
        s = json.dumps(d)
        d2 = json.loads(s)
        assert d2["atom_id"] == "atom_x"
        assert len(d2["chain_steps"]) == 2
        assert d2["a14_flags"] == ["FLAG_PILOT_PENDING"]

    def test_recommendation_to_dict_round_trips(self):
        import json
        a1 = _make_attestation(atom_id="atom_a")
        a2 = _make_attestation(atom_id="atom_b", a14_flags=["F1"])
        rec = render_recommendation(
            [a1, a2], recommendation_summary="test rec",
        )
        d = recommendation_to_dict(rec)
        s = json.dumps(d)
        d2 = json.loads(s)
        assert d2["recommendation_summary"] == "test rec"
        assert d2["n_attestations"] == 2
        assert d2["aggregate_a14_flags"] == ["F1"]

    def test_relation_serialized_as_string(self):
        att = _make_attestation(n_steps=1)
        rendering = render_chain_attestation(att)
        d = attestation_to_dict(rendering)
        # relation field should be the string value, not the enum object
        assert isinstance(d["chain_steps"][0]["relation"], str)


# ============================================================================
# Discipline anchor — no LLM-generated text, every claim traces to input
# ============================================================================


class TestNoLLMComposedText:
    """Foundation §4.3 + Antipattern A4: every rendered string must be
    traceable to a structured input value. Verified by smoke-checking
    that the rendering doesn't add narrative beyond templated facts."""

    def test_summary_sentence_only_uses_atom_id_and_link_count(self):
        att = _make_attestation(atom_id="atom_test_xyz", n_steps=2)
        rendering = render_chain_attestation(att)
        # The summary should mention the atom_id and link count and
        # nothing else (no "We think...", "AI suggests...", etc.)
        summary = rendering.summary_sentence.lower()
        forbidden_phrases = [
            "ai", "think", "suggest", "believe", "feel",
            "we ", "the model",
        ]
        for phrase in forbidden_phrases:
            assert phrase not in summary, (
                f"Summary contains drift phrase {phrase!r}: {summary}"
            )

    def test_all_strings_in_chain_steps_traceable(self):
        att = _make_attestation(n_steps=1)
        rendering = render_chain_attestation(att)
        step = rendering.chain_steps[0]
        # source/target constructs come from the link
        assert step.source_construct == att.chain[0].source_construct
        assert step.target_construct == att.chain[0].target_construct
        # citation comes from the link
        assert step.citation.raw == att.chain[0].citation
        # link_id preserved
        assert step.link_id == att.chain[0].link_id
