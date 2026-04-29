# =============================================================================
# ADAM Dialogue Ledger — Uncertainty Panel renderer (Loop B v0.1)
# Location: adam/intelligence/dialogue_ledger/uncertainty_panel.py
# =============================================================================

"""
UNCERTAINTY PANEL — HMT §11.1 + §7.1

For every AI-generated recommendation, surface three structured
columns: Confident / Uncertain / Possibly Wrong, each populated from
existing computed values (atom confidences, evidence counts, bilateral
cascade outputs, chain attestations). Pure surfacing of the cognition
that's already happening — no new model work.

WHY THIS MATTERS

  - HMT §7.1: a confidence percentage is not adequate explanation.
    The required output is structured: confident sub-decisions vs
    uncertain sub-decisions vs possibly-wrong sub-decisions, with
    the EVIDENCE that drives each placement explicit.
  - HMT §11.1: this is the single highest-leverage Loop B v0.1
    deliverable because every recommendation rendered without an
    Uncertainty Panel is a recommendation that pretends to know
    more than it does. ADAM's differentiator over correlational
    DSPs is exactly this: the system explains its confidence
    structure, not just its output.

DISCIPLINE

  - The panel renders cognition, it does NOT compose it. Every
    item in the panel cites a source (atom_id, edge dimension,
    cascade level, attestation chain) — no hand-composed English
    that is not directly traceable to a computed value.
  - Vocabulary: "atom activation", "evidence counts", "edge
    dimensions" — NOT "AI says", "the model thinks", "we suggest."
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# =============================================================================
# ENUMS
# =============================================================================


class UncertaintyBucket(str, Enum):
    """Which column of the panel an item lands in."""

    CONFIDENT = "confident"
    UNCERTAIN = "uncertain"
    POSSIBLY_WRONG = "possibly_wrong"


# =============================================================================
# THRESHOLDS — A14 calibration-pending
# =============================================================================

# A14 UNCERTAINTY_PANEL_CONFIDENCE_THRESHOLDS_PILOT_PENDING
# These thresholds are HMT §7.1 priors. Recalibrated from pilot data
# once we observe how often each bucket's items reflect ground truth.
CONFIDENT_ATOM_CONFIDENCE_FLOOR: float = 0.70
UNCERTAIN_ATOM_CONFIDENCE_RANGE: tuple = (0.40, 0.70)
POSSIBLY_WRONG_ATOM_CONFIDENCE_CEILING: float = 0.40

# Cascade-level thresholds for confident vs uncertain edge evidence
CONFIDENT_MIN_CASCADE_LEVEL: int = 3   # L3+ has bilateral edge evidence
UNCERTAIN_MAX_CASCADE_LEVEL: int = 2   # L1/L2 only — priors only

# Edge-count threshold for confident bilateral evidence
CONFIDENT_MIN_EDGE_COUNT: int = 100


# =============================================================================
# PANEL ITEM TYPES
# =============================================================================


@dataclass(frozen=True)
class PanelItem:
    """One item in one column of the Uncertainty Panel.

    `claim` — the assertion the system is making (or failing to make).
    `bucket` — which column.
    `evidence_trace` — list of source identifiers (atom_id strings,
      edge-dimension names, cascade-level marker, chain link_ids) so
      consumers can drill into each item.
    `quantitative_basis` — small dict of numeric values (atom
      confidence, edge count, etc.) that drove the placement.
    """

    claim: str
    bucket: UncertaintyBucket
    evidence_trace: List[str] = field(default_factory=list)
    quantitative_basis: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class UncertaintyPanel:
    """The rendered three-column structure.

    Render-ready: the frontend iterates `confident`, `uncertain`,
    `possibly_wrong` and displays each item's claim + evidence trace.
    """

    confident: List[PanelItem]
    uncertain: List[PanelItem]
    possibly_wrong: List[PanelItem]
    panel_summary: Dict[str, int] = field(default_factory=dict)

    @property
    def total_items(self) -> int:
        return (
            len(self.confident)
            + len(self.uncertain)
            + len(self.possibly_wrong)
        )


# =============================================================================
# RENDERER — pure function from cognition outputs to panel
# =============================================================================


def render_uncertainty_panel(
    *,
    cascade_level: Optional[int] = None,
    cascade_edge_count: int = 0,
    cascade_primary_mechanism: Optional[str] = None,
    cascade_confidence: Optional[float] = None,
    atom_results: Optional[Dict[str, Dict[str, Any]]] = None,
    chain_attestations: Optional[List[Any]] = None,
    mechanism_scores: Optional[Dict[str, float]] = None,
    a14_flags_active: Optional[List[str]] = None,
) -> UncertaintyPanel:
    """Render the Uncertainty Panel from existing cognition outputs.

    Pure function — no side effects, no I/O, no LLM calls. Every panel
    item traces directly to one of the input structures.

    Args:
        cascade_level: bilateral-cascade depth reached (1-5).
        cascade_edge_count: number of bilateral edges informing L3.
        cascade_primary_mechanism: cascade's primary mechanism choice.
        cascade_confidence: cascade's overall confidence in the choice.
        atom_results: dict mapping atom_id → atom output dict
            (must have keys 'confidence', 'reasoning' optional).
        chain_attestations: list of ChainAttestation objects emitted
            by atoms — each carries provenance.a14_flags_active.
        mechanism_scores: cascade's per-mechanism score dict.
        a14_flags_active: extra A14 flags from elsewhere in the system
            (decision-level, beyond per-attestation flags).

    Returns:
        UncertaintyPanel with three buckets populated.
    """
    confident: List[PanelItem] = []
    uncertain: List[PanelItem] = []
    possibly_wrong: List[PanelItem] = []

    # ── Cascade-level evidence assessment ──
    if cascade_level is not None:
        cascade_item = _classify_cascade_evidence(
            cascade_level=cascade_level,
            cascade_edge_count=cascade_edge_count,
            cascade_primary_mechanism=cascade_primary_mechanism,
            cascade_confidence=cascade_confidence,
        )
        if cascade_item is not None:
            _route_to_bucket(cascade_item, confident, uncertain, possibly_wrong)

    # ── Per-atom confidence assessment ──
    if atom_results:
        for atom_id, atom_data in atom_results.items():
            if not isinstance(atom_data, dict):
                continue
            atom_item = _classify_atom_evidence(atom_id, atom_data)
            if atom_item is not None:
                _route_to_bucket(
                    atom_item, confident, uncertain, possibly_wrong,
                )

    # ── Chain-attestation A14 flags assessment ──
    # A14 flags name uncertainty explicitly: pilot-pending coefficients,
    # placeholder constants. Each active flag becomes an Uncertain item
    # so the user sees what is calibration-pending.
    flags_seen: Dict[str, List[str]] = {}  # flag → [atom_ids that emit it]
    if chain_attestations:
        for att in chain_attestations:
            atom_id = getattr(att, "atom_id", "unknown")
            provenance = getattr(att, "provenance", None)
            if provenance is None:
                continue
            for flag in getattr(provenance, "a14_flags_active", []):
                flags_seen.setdefault(flag, []).append(atom_id)

    # Decision-level A14 flags (passed as kwarg)
    if a14_flags_active:
        for flag in a14_flags_active:
            flags_seen.setdefault(flag, []).append("decision_level")

    for flag, atoms in flags_seen.items():
        uncertain.append(PanelItem(
            claim=(
                f"{flag} — calibration-pending; pilot data will replace "
                f"the placeholder coefficient(s)"
            ),
            bucket=UncertaintyBucket.UNCERTAIN,
            evidence_trace=atoms,
            quantitative_basis={"atom_count": float(len(atoms))},
        ))

    # ── Mechanism-score divergence assessment ──
    # When multiple mechanisms are tightly bunched (top-2 within 0.05),
    # the choice is uncertain — surface this so the user sees it.
    if mechanism_scores and len(mechanism_scores) >= 2:
        sorted_scores = sorted(
            mechanism_scores.items(), key=lambda kv: kv[1], reverse=True,
        )
        top_score = sorted_scores[0][1]
        runner_up_score = sorted_scores[1][1]
        gap = top_score - runner_up_score
        if gap < 0.05:
            uncertain.append(PanelItem(
                claim=(
                    f"Mechanism choice between '{sorted_scores[0][0]}' "
                    f"({top_score:.3f}) and '{sorted_scores[1][0]}' "
                    f"({runner_up_score:.3f}) — top-2 within 0.05; "
                    f"either is plausible per current evidence"
                ),
                bucket=UncertaintyBucket.UNCERTAIN,
                evidence_trace=["mechanism_scores"],
                quantitative_basis={
                    "top_score": top_score,
                    "runner_up_score": runner_up_score,
                    "gap": gap,
                },
            ))

    # ── Possibly-wrong: conflicting attestations ──
    # When chain attestations point in opposite directions on a single
    # mechanism (one positive adjustment, one negative), the resulting
    # score is suspect — surface that.
    if chain_attestations:
        conflicts = _detect_attestation_conflicts(chain_attestations)
        for mech, conflicting_atoms in conflicts.items():
            possibly_wrong.append(PanelItem(
                claim=(
                    f"Mechanism '{mech}' has conflicting chain attestations "
                    f"from atoms {sorted(set(conflicting_atoms))}; one says "
                    f"raise, another says lower"
                ),
                bucket=UncertaintyBucket.POSSIBLY_WRONG,
                evidence_trace=conflicting_atoms,
                quantitative_basis={
                    "conflicting_atom_count": float(len(set(conflicting_atoms))),
                },
            ))

    panel_summary = {
        "confident_count": len(confident),
        "uncertain_count": len(uncertain),
        "possibly_wrong_count": len(possibly_wrong),
    }

    return UncertaintyPanel(
        confident=confident,
        uncertain=uncertain,
        possibly_wrong=possibly_wrong,
        panel_summary=panel_summary,
    )


# =============================================================================
# Internal classification logic
# =============================================================================


def _classify_cascade_evidence(
    *,
    cascade_level: int,
    cascade_edge_count: int,
    cascade_primary_mechanism: Optional[str],
    cascade_confidence: Optional[float],
) -> Optional[PanelItem]:
    """Classify the cascade's evidence into a PanelItem."""
    primary = cascade_primary_mechanism or "<unknown>"
    quantitative_basis: Dict[str, float] = {
        "cascade_level": float(cascade_level),
        "edge_count": float(cascade_edge_count),
    }
    if cascade_confidence is not None:
        quantitative_basis["confidence"] = float(cascade_confidence)

    if (
        cascade_level >= CONFIDENT_MIN_CASCADE_LEVEL
        and cascade_edge_count >= CONFIDENT_MIN_EDGE_COUNT
    ):
        return PanelItem(
            claim=(
                f"Cascade reached L{cascade_level} with {cascade_edge_count} "
                f"bilateral edges; primary mechanism '{primary}' is supported "
                f"by direct edge evidence"
            ),
            bucket=UncertaintyBucket.CONFIDENT,
            evidence_trace=[f"cascade:L{cascade_level}", "BRAND_CONVERTED_edges"],
            quantitative_basis=quantitative_basis,
        )

    if cascade_level <= UNCERTAIN_MAX_CASCADE_LEVEL:
        return PanelItem(
            claim=(
                f"Cascade only reached L{cascade_level} — operating on "
                f"{'archetype priors' if cascade_level == 1 else 'category posteriors'} "
                f"alone, no direct bilateral edge evidence"
            ),
            bucket=UncertaintyBucket.UNCERTAIN,
            evidence_trace=[f"cascade:L{cascade_level}"],
            quantitative_basis=quantitative_basis,
        )

    # L3 reached but edge count below threshold
    if cascade_level == 3 and cascade_edge_count < CONFIDENT_MIN_EDGE_COUNT:
        return PanelItem(
            claim=(
                f"Cascade reached L3 but with only {cascade_edge_count} "
                f"bilateral edges (threshold: {CONFIDENT_MIN_EDGE_COUNT}); "
                f"edge evidence is sparse for this cell"
            ),
            bucket=UncertaintyBucket.UNCERTAIN,
            evidence_trace=[f"cascade:L{cascade_level}", "sparse_edges"],
            quantitative_basis=quantitative_basis,
        )

    # L4 (inferential transfer) — some signal but not direct edges
    if cascade_level == 4:
        return PanelItem(
            claim=(
                f"Cascade reached L4 (inferential transfer) — bilateral edges "
                f"unavailable for this cell; recommendation derived from "
                f"theoretical-link traversal"
            ),
            bucket=UncertaintyBucket.UNCERTAIN,
            evidence_trace=["cascade:L4", "inferential_transfer"],
            quantitative_basis=quantitative_basis,
        )

    return None


def _classify_atom_evidence(
    atom_id: str, atom_data: Dict[str, Any],
) -> Optional[PanelItem]:
    """Classify one atom's confidence into a PanelItem."""
    confidence = atom_data.get("confidence")
    if confidence is None or not isinstance(confidence, (int, float)):
        return None
    confidence = float(confidence)

    if confidence >= CONFIDENT_ATOM_CONFIDENCE_FLOOR:
        return PanelItem(
            claim=f"Atom {atom_id} activated with confidence {confidence:.2f}",
            bucket=UncertaintyBucket.CONFIDENT,
            evidence_trace=[atom_id],
            quantitative_basis={"confidence": confidence},
        )

    if confidence < POSSIBLY_WRONG_ATOM_CONFIDENCE_CEILING:
        return PanelItem(
            claim=(
                f"Atom {atom_id} activation low (confidence {confidence:.2f}) "
                f"— recommendation may not be supported by this atom's "
                f"reasoning"
            ),
            bucket=UncertaintyBucket.POSSIBLY_WRONG,
            evidence_trace=[atom_id],
            quantitative_basis={"confidence": confidence},
        )

    # Middle range — uncertain
    lo, hi = UNCERTAIN_ATOM_CONFIDENCE_RANGE
    if lo <= confidence < hi:
        return PanelItem(
            claim=(
                f"Atom {atom_id} activation moderate (confidence "
                f"{confidence:.2f}) — neither strongly supports nor "
                f"refutes the recommendation"
            ),
            bucket=UncertaintyBucket.UNCERTAIN,
            evidence_trace=[atom_id],
            quantitative_basis={"confidence": confidence},
        )

    return None


def _detect_attestation_conflicts(
    chain_attestations: List[Any],
) -> Dict[str, List[str]]:
    """Find mechanisms where one attestation says raise (positive
    adjustment_value) and another says lower (negative). Returns
    a dict mapping mechanism_id → list of conflicting atom_ids."""
    # mech → list of (atom_id, signed_adjustment) tuples
    by_mech: Dict[str, List[tuple]] = {}
    for att in chain_attestations:
        atom_id = getattr(att, "atom_id", "unknown")
        adjustments = getattr(att, "mechanism_adjustments", [])
        for adj in adjustments:
            mech_id = getattr(adj, "mechanism_id", None)
            adj_value = getattr(adj, "adjustment_value", 0.0)
            if mech_id is None:
                continue
            by_mech.setdefault(mech_id, []).append((atom_id, adj_value))

    conflicts: Dict[str, List[str]] = {}
    for mech, entries in by_mech.items():
        if len(entries) < 2:
            continue
        signs = {1 if v > 0 else -1 if v < 0 else 0 for _, v in entries}
        # Conflict iff both +1 and -1 are present
        if 1 in signs and -1 in signs:
            conflicts[mech] = [aid for aid, _ in entries]

    return conflicts


def _route_to_bucket(
    item: PanelItem,
    confident: List[PanelItem],
    uncertain: List[PanelItem],
    possibly_wrong: List[PanelItem],
) -> None:
    if item.bucket == UncertaintyBucket.CONFIDENT:
        confident.append(item)
    elif item.bucket == UncertaintyBucket.UNCERTAIN:
        uncertain.append(item)
    elif item.bucket == UncertaintyBucket.POSSIBLY_WRONG:
        possibly_wrong.append(item)


__all__ = [
    "CONFIDENT_ATOM_CONFIDENCE_FLOOR",
    "CONFIDENT_MIN_CASCADE_LEVEL",
    "CONFIDENT_MIN_EDGE_COUNT",
    "POSSIBLY_WRONG_ATOM_CONFIDENCE_CEILING",
    "UNCERTAIN_ATOM_CONFIDENCE_RANGE",
    "UNCERTAIN_MAX_CASCADE_LEVEL",
    "PanelItem",
    "UncertaintyBucket",
    "UncertaintyPanel",
    "render_uncertainty_panel",
]
