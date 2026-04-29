# =============================================================================
# ADAM Construct-Chain Rendering — Foundation §4.3 in code
# Location: adam/intelligence/chain_rendering.py
# =============================================================================

"""
CONSTRUCT-CHAIN RENDERING — partner-facing inferential-chain artifact

Foundation §4.3 names this "the single most important architectural
gap" because atoms compute the inferential chain that produces a
recommendation but never materialize it for downstream consumers.
This module materializes it.

WHY THIS IS THE DIFFERENTIATOR

Every correlational DSP shows scores: "authority: 0.82". The buyer
trusts the number or doesn't. There's no audit trail.

ADAM's chain rendering shows the COGNITION that produced the score:
"Careful Truster on this page activates need-for-closure
(uncertainty_intolerance → need_for_closure, Bargh 1990 §3.2) → which
authority satisfies (need_for_closure → satisfied_by → authority,
Cialdini 2007 §2.4) → must be substantive because cognitive engagement
is high (cognitive_engagement → requires → substantive_evidence) →
frame for long temporal horizon because construal level is abstract."

The reader can drill into each citation. Each link carries a
calibration_status (PINNED — canonical formula constant from cited
paper; PILOT_PENDING — placeholder awaiting pilot data). The renderer
makes the difference visible.

This is NOT LLM-generated text. The chain ConstructLinks already exist
in `ChainAttestation`; this module is a pure function from structured
ChainAttestations to partner-facing render structures.

CONTRACT (no LLM, no composed prose)

Every string in the output is templated from values directly readable
from the ChainAttestation. The verb between source and target is
mapped from `RelationType` enum values to short canonical phrases. No
generated reasoning. The reader should be able to drill from any
displayed line straight to the link_id and the citation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from adam.atoms.models.chain_attestation import (
    AdjustmentEvidence,
    CalibrationStatus,
    ChainAttestation,
    ConstructLink,
    RelationType,
    TypedEvidence,
)


# =============================================================================
# RELATION-TYPE → human-readable verb mapping
# =============================================================================


# Canonical phrasing per RelationType enum. Short, declarative, matches
# the construct-chain idiom in Foundation §4.3.
_RELATION_VERBS: Dict[RelationType, str] = {
    RelationType.CREATES_NEED_FOR: "creates need for",
    RelationType.SATISFIED_BY: "is satisfied by",
    RelationType.THREATENS: "threatens",
    RelationType.AMPLIFIES: "amplifies",
    RelationType.SUPPRESSES: "suppresses",
    RelationType.PRODUCES: "produces",
    RelationType.MODULATED_BY: "is modulated by",
}


def _relation_verb(rel: RelationType) -> str:
    """Map a RelationType to a short canonical phrase."""
    return _RELATION_VERBS.get(rel, rel.value.replace("_", " "))


# =============================================================================
# RENDER STRUCTURES
# =============================================================================


@dataclass(frozen=True)
class Citation:
    """A paper:section reference extracted from a chain link or assessment."""

    raw: str            # e.g., "Cialdini 2007 §2.4"
    paper: str          # e.g., "Cialdini 2007"
    section: str        # e.g., "§2.4"

    @classmethod
    def parse(cls, raw: str) -> "Citation":
        """Best-effort split on the section marker.

        Handles common patterns:
          "Cialdini 2007 §2.4" → ("Cialdini 2007", "§2.4")
          "Bargh 1990 sec 3"   → ("Bargh 1990", "sec 3")
          "no citation"        → ("no citation", "")
        """
        raw = raw.strip()
        for marker in ("§", " sec ", " section "):
            if marker in raw:
                idx = raw.index(marker)
                paper = raw[:idx].strip()
                section = raw[idx:].strip()
                return cls(raw=raw, paper=paper, section=section)
        return cls(raw=raw, paper=raw, section="")


@dataclass(frozen=True)
class ChainStepRendering:
    """One link in the rendered chain.

    `as_sentence` produces a single readable line — useful when the
    consumer wants flat text. The structured fields underneath let
    the dashboard build a visual node-edge view.
    """

    source_construct: str
    relation: RelationType
    relation_verb: str
    target_construct: str
    evidence_value: float
    confidence: float
    citation: Citation
    calibration_status: CalibrationStatus
    link_id: str

    def as_sentence(self) -> str:
        return (
            f"{self.source_construct} {self.relation_verb} "
            f"{self.target_construct} ({self.citation.raw}, "
            f"evidence={self.evidence_value:.2f}, "
            f"confidence={self.confidence:.2f})"
        )


@dataclass(frozen=True)
class FinalAssessmentRendering:
    """The atom's final TypedEvidence as a render structure."""

    construct: str
    value: float
    confidence: float
    citation: Citation
    calibration_status: CalibrationStatus

    def as_sentence(self) -> str:
        return (
            f"final assessment: {self.construct} = {self.value:.2f} "
            f"(confidence {self.confidence:.2f}, {self.citation.raw}, "
            f"{self.calibration_status.value})"
        )


@dataclass(frozen=True)
class MechanismAdjustmentRendering:
    """A mechanism adjustment + which links drove it."""

    mechanism_id: str
    adjustment_value: float
    direction: str  # "raise" / "lower" / "neutral"
    confidence: float
    chain_links_responsible: List[str]

    def as_sentence(self) -> str:
        magnitude = abs(self.adjustment_value)
        return (
            f"{self.direction} '{self.mechanism_id}' by {magnitude:.3f} "
            f"(confidence {self.confidence:.2f}; driven by "
            f"{len(self.chain_links_responsible)} link(s))"
        )


@dataclass(frozen=True)
class ChainAttestationRendering:
    """One atom's chain attestation rendered for partner-facing display.

    `summary_sentence` is a single-line summary suitable for the top
    of a dashboard card. `chain_steps`, `final_assessment`,
    `mechanism_adjustments`, `citations`, `a14_flags` are the
    structured drill-downs.
    """

    atom_id: str
    target_construct: str
    summary_sentence: str
    chain_steps: List[ChainStepRendering]
    final_assessment: FinalAssessmentRendering
    mechanism_adjustments: List[MechanismAdjustmentRendering]
    citations: List[Citation]
    a14_flags: List[str]
    request_id: str

    def as_paragraph(self) -> str:
        """Human-readable paragraph rendering of the full chain.

        Useful for the deck slide / case-study artifact. The dashboard
        renders the structured fields with drill-down UI; this is the
        flat-text alternative.
        """
        lines = [self.summary_sentence]
        for step in self.chain_steps:
            lines.append(f"  → {step.as_sentence()}")
        lines.append(f"  ⇒ {self.final_assessment.as_sentence()}")
        if self.mechanism_adjustments:
            lines.append("  Mechanism adjustments:")
            for adj in self.mechanism_adjustments:
                lines.append(f"    • {adj.as_sentence()}")
        if self.a14_flags:
            lines.append(
                f"  A14 calibration-pending: {', '.join(self.a14_flags)}"
            )
        return "\n".join(lines)


@dataclass(frozen=True)
class RecommendationChainRendering:
    """A full recommendation's chain rendering — multi-atom view.

    A single ADAM decision typically activates multiple atoms; this
    aggregates their attestations and provides a recommendation-level
    overview.
    """

    recommendation_summary: str
    attestations: List[ChainAttestationRendering]
    aggregate_a14_flags: List[str]
    aggregate_citations: List[Citation]

    @property
    def n_attestations(self) -> int:
        return len(self.attestations)

    def as_partner_text(self) -> str:
        """Full text rendering suitable for partner-facing reports."""
        lines = [
            self.recommendation_summary,
            "",
            f"Inferential chains supporting this recommendation "
            f"({self.n_attestations} atom{'s' if self.n_attestations != 1 else ''}):",
        ]
        for att in self.attestations:
            lines.append("")
            lines.append(att.as_paragraph())
        if self.aggregate_a14_flags:
            lines.append("")
            lines.append(
                f"Calibration-pending across this recommendation: "
                f"{', '.join(sorted(set(self.aggregate_a14_flags)))}"
            )
        return "\n".join(lines)


# =============================================================================
# RENDERERS — pure functions, no I/O, no LLM
# =============================================================================


def render_chain_step(link: ConstructLink) -> ChainStepRendering:
    """Render a single ConstructLink."""
    return ChainStepRendering(
        source_construct=link.source_construct,
        relation=link.relation_type,
        relation_verb=_relation_verb(link.relation_type),
        target_construct=link.target_construct,
        evidence_value=float(link.evidence_value),
        confidence=float(link.confidence),
        citation=Citation.parse(link.citation),
        calibration_status=link.calibration_status,
        link_id=link.link_id,
    )


def render_final_assessment(
    final: TypedEvidence,
) -> FinalAssessmentRendering:
    return FinalAssessmentRendering(
        construct=final.construct,
        value=float(final.value),
        confidence=float(final.confidence),
        citation=Citation.parse(final.citation),
        calibration_status=final.calibration_status,
    )


def render_mechanism_adjustment(
    adj: AdjustmentEvidence,
) -> MechanismAdjustmentRendering:
    if adj.adjustment_value > 1e-9:
        direction = "raise"
    elif adj.adjustment_value < -1e-9:
        direction = "lower"
    else:
        direction = "neutral"
    return MechanismAdjustmentRendering(
        mechanism_id=adj.mechanism_id,
        adjustment_value=float(adj.adjustment_value),
        direction=direction,
        confidence=float(adj.confidence),
        chain_links_responsible=list(adj.chain_links_responsible),
    )


def render_chain_attestation(
    attestation: ChainAttestation,
) -> ChainAttestationRendering:
    """Render one atom's chain attestation as a partner-facing structure.

    Pure function. No LLM. No I/O.
    """
    chain_steps = [render_chain_step(link) for link in attestation.chain]
    final = render_final_assessment(attestation.final_assessment)
    adjustments = [
        render_mechanism_adjustment(adj)
        for adj in attestation.mechanism_adjustments
    ]

    citations: List[Citation] = []
    seen_raw: set = set()
    for step in chain_steps:
        if step.citation.raw not in seen_raw:
            citations.append(step.citation)
            seen_raw.add(step.citation.raw)
    if final.citation.raw not in seen_raw:
        citations.append(final.citation)
        seen_raw.add(final.citation.raw)

    summary_sentence = (
        f"Atom {attestation.atom_id}: assessing "
        f"{attestation.target_construct} via "
        f"{len(chain_steps)} construct link"
        f"{'s' if len(chain_steps) != 1 else ''}"
    )

    a14_flags = list(attestation.provenance.a14_flags_active)

    return ChainAttestationRendering(
        atom_id=attestation.atom_id,
        target_construct=attestation.target_construct,
        summary_sentence=summary_sentence,
        chain_steps=chain_steps,
        final_assessment=final,
        mechanism_adjustments=adjustments,
        citations=citations,
        a14_flags=a14_flags,
        request_id=attestation.request_id,
    )


def render_recommendation(
    chain_attestations: List[ChainAttestation],
    *,
    recommendation_summary: str,
) -> RecommendationChainRendering:
    """Render multiple atom attestations as a single recommendation view.

    Args:
        chain_attestations: list of ChainAttestations from the atoms
            that contributed to this recommendation.
        recommendation_summary: caller-supplied one-line summary of
            the recommendation. Caller knows the recommendation
            context (archetype, mechanism chosen, etc.); this module
            does not.
    """
    rendered = [render_chain_attestation(a) for a in chain_attestations]

    # Aggregate A14 flags across attestations (deduped, preserved order)
    seen_flags: set = set()
    aggregate_flags: List[str] = []
    for r in rendered:
        for flag in r.a14_flags:
            if flag not in seen_flags:
                aggregate_flags.append(flag)
                seen_flags.add(flag)

    # Aggregate citations across attestations (deduped by raw text)
    seen_cit_raw: set = set()
    aggregate_citations: List[Citation] = []
    for r in rendered:
        for c in r.citations:
            if c.raw not in seen_cit_raw:
                aggregate_citations.append(c)
                seen_cit_raw.add(c.raw)

    return RecommendationChainRendering(
        recommendation_summary=recommendation_summary,
        attestations=rendered,
        aggregate_a14_flags=aggregate_flags,
        aggregate_citations=aggregate_citations,
    )


# =============================================================================
# JSON-friendly serialization
# =============================================================================


def attestation_to_dict(
    rendering: ChainAttestationRendering,
) -> Dict[str, Any]:
    """Convert a ChainAttestationRendering to a plain dict.

    Used by API responses + dashboard payloads. JSON-safe values only
    (enums → their .value, no datetime, no Pydantic model leakage).
    """
    return {
        "atom_id": rendering.atom_id,
        "target_construct": rendering.target_construct,
        "request_id": rendering.request_id,
        "summary_sentence": rendering.summary_sentence,
        "chain_steps": [
            {
                "source_construct": s.source_construct,
                "relation": s.relation.value,
                "relation_verb": s.relation_verb,
                "target_construct": s.target_construct,
                "evidence_value": s.evidence_value,
                "confidence": s.confidence,
                "citation": {
                    "raw": s.citation.raw,
                    "paper": s.citation.paper,
                    "section": s.citation.section,
                },
                "calibration_status": s.calibration_status.value,
                "link_id": s.link_id,
            }
            for s in rendering.chain_steps
        ],
        "final_assessment": {
            "construct": rendering.final_assessment.construct,
            "value": rendering.final_assessment.value,
            "confidence": rendering.final_assessment.confidence,
            "citation": {
                "raw": rendering.final_assessment.citation.raw,
                "paper": rendering.final_assessment.citation.paper,
                "section": rendering.final_assessment.citation.section,
            },
            "calibration_status": rendering.final_assessment.calibration_status.value,
        },
        "mechanism_adjustments": [
            {
                "mechanism_id": a.mechanism_id,
                "adjustment_value": a.adjustment_value,
                "direction": a.direction,
                "confidence": a.confidence,
                "chain_links_responsible": a.chain_links_responsible,
            }
            for a in rendering.mechanism_adjustments
        ],
        "citations": [
            {"raw": c.raw, "paper": c.paper, "section": c.section}
            for c in rendering.citations
        ],
        "a14_flags": rendering.a14_flags,
    }


def recommendation_to_dict(
    rendering: RecommendationChainRendering,
) -> Dict[str, Any]:
    return {
        "recommendation_summary": rendering.recommendation_summary,
        "n_attestations": rendering.n_attestations,
        "attestations": [
            attestation_to_dict(a) for a in rendering.attestations
        ],
        "aggregate_a14_flags": rendering.aggregate_a14_flags,
        "aggregate_citations": [
            {"raw": c.raw, "paper": c.paper, "section": c.section}
            for c in rendering.aggregate_citations
        ],
    }


__all__ = [
    "ChainAttestationRendering",
    "ChainStepRendering",
    "Citation",
    "FinalAssessmentRendering",
    "MechanismAdjustmentRendering",
    "RecommendationChainRendering",
    "attestation_to_dict",
    "recommendation_to_dict",
    "render_chain_attestation",
    "render_chain_step",
    "render_final_assessment",
    "render_mechanism_adjustment",
    "render_recommendation",
]
