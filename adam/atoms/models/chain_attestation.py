# =============================================================================
# ADAM Chain-Attestation Typed Evidence Models
# Location: adam/atoms/models/chain_attestation.py
# =============================================================================

"""
CHAIN-ATTESTATION TYPED EVIDENCE

Materializes the foundation §4.3 commitment: every atom that emits a scalar
must also emit the chain of construct activations that produced it, tagged
with the literature grounding each link, consumed downstream as chain — not
scalar.

This module is the Phase 0 emergent primitive for B3-LUXY. It is designed
from `autonomy_reactance` as the simplest chain shape (single-source threat
→ threshold modulation → mechanism penalty) and will be refactored as
atoms 2–3 (`persuasion_pharmacology`, `mimetic_desire_atom`) reveal
multi-step temporal and multi-source convergence shapes. After atom 3 the
schema locks; remaining 6 atoms slot in.

INTEGRATION CONTRACT
--------------------
The `ChainAttestation.theoretical_link_keys` property and `.to_chain_data()`
method are the contract surface for `adam.core.learning.theory_learner`:

  TheoryLearner.process_chain_outcome(
      chain_data={
          "chain_id": <str>,
          "theoretical_link_keys": [<link_key>, ...],
          "recommended_mechanism": <str>,
      },
      decision_id=<str>,
      success=<bool>,
      outcome_value=<float>,
  )

Link key format (matching TheoryLearner LinkPosterior keys):
  "{relation_type}:{source_construct}:{target_construct}"

L3 CONSUMPTION
--------------
L3 (`adam/api/stackadapt/bilateral_cascade.py:961` `level3_bilateral_edges`)
consumes chain-attestations as additional alignment dimensions alongside
the existing 21 bilateral edge dims. Chain-derived mechanism contributions
combine multiplicatively with edge-derived contributions (A14-flagged
fusion form, pilot-pending). See `docs/B3_LUXY_PHASE_PLAN.md` §5.

DISCIPLINE RULE
---------------
This schema is the load-bearing primitive that lets atoms be honest about
the difference between (a) a theoretically-grounded inferential step backed
by a paper:section citation and pinned by regression tests, and (b) a
placeholder coefficient awaiting pilot calibration. The `calibration_status`
and `citation` fields on every link are not optional metadata — they are
the structural defense against shipping theory-in-docstring drift dressed
as a typed primitive. See `memory/feedback_atom_redo_discipline.md`.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


# =============================================================================
# CALIBRATION STATUS
# =============================================================================

class CalibrationStatus(str, Enum):
    """Whether a constant in the formula is locked or pilot-pending.

    PINNED — value is the canonical literature formula constant. Cited
    paper:section is the authoritative source. Not subject to pilot
    recalibration unless the citation is replaced.

    PILOT_PENDING — value is a placeholder (literature midpoint, expert
    estimate, or theory-derived prior). Will be recalibrated from LUXY
    pilot data once accumulation crosses the retirement trigger named
    in the corresponding A14 flag. Documented as such, not silent.

    Per discipline rule (c): every placeholder must carry an A14 flag
    naming its retirement trigger. PILOT_PENDING without an active A14
    is dishonest and fails review.
    """

    PINNED = "pinned"
    PILOT_PENDING = "pilot_pending"


# =============================================================================
# RELATION TYPES
# =============================================================================

class RelationType(str, Enum):
    """Theoretical link types between psychological constructs.

    Intentionally small initial set — extend as additional atoms reveal
    additional canonical relation types. The set will be reviewed and
    finalized after Phase 1 atom 3 (`mimetic_desire_atom`) reveals
    whether multi-source convergence requires new relation types.

    Naming convention: VERBPHRASE in SCREAMING_SNAKE_CASE; matches the
    TheoryLearner LinkPosterior key format
    `"{relation}:{source}:{target}"`.
    """

    CREATES_NEED_FOR = "CREATES_NEED_FOR"
    """A psychological state creates a need that must be satisfied.
    Example: uncertainty_intolerance → need_for_closure."""

    SATISFIED_BY = "SATISFIED_BY"
    """A need is satisfied by a specific mechanism or stimulus.
    Example: need_for_closure → authority_signal."""

    THREATENS = "THREATENS"
    """A mechanism or context threatens a freedom or value.
    Example: coercive_mechanism → autonomy_freedom (Brehm 1966)."""

    AMPLIFIES = "AMPLIFIES"
    """A trait or state amplifies the magnitude of a response.
    Example: persuasion_knowledge → reactance_response (Friestad & Wright 1994)."""

    SUPPRESSES = "SUPPRESSES"
    """A trait or state suppresses the magnitude of a response.
    Example: autonomy_preserving_frame → reactance_response."""

    PRODUCES = "PRODUCES"
    """A psychological state produces a behavioral outcome.
    Example: reactance_response → mechanism_backfire (Wicklund 1974)."""

    MODULATED_BY = "MODULATED_BY"
    """An effect is moderated by a trait, state, or contextual factor.
    Example: reactance_baseline → trait_HPRS (Hong & Page 1989)."""


# =============================================================================
# CONSTRUCT LINK — A SINGLE THEORETICAL STEP
# =============================================================================

class ConstructLink(BaseModel):
    """A single theoretical link in an inferential chain.

    Encodes one inferential step: source_construct {relation_type} target_construct.
    Each link is grounded in a paper:section citation, carries its own
    evidence value and confidence, and declares its calibration status
    (pinned vs. pilot-pending).

    The `link_key` property is the integration contract surface for
    `TheoryLearner.LinkPosterior` — see module docstring.
    """

    link_id: str = Field(
        default_factory=lambda: f"lnk_{uuid4().hex[:12]}"
    )

    # The inferential step
    source_construct: str = Field(
        ...,
        description="The construct providing the input to this step (e.g., 'high_persuasion_knowledge')",
    )
    relation_type: RelationType
    target_construct: str = Field(
        ...,
        description="The construct produced by this step (e.g., 'lowered_reactance_threshold')",
    )

    # Evidence for this specific user/decision
    evidence_value: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "How strongly this link fired for this user/decision (0-1). "
            "1.0 = canonical case, 0.0 = link did not fire. Distinct from "
            "the link's posterior strength (which lives in TheoryLearner)."
        ),
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Epistemic uncertainty in evidence_value for this decision",
    )

    # Provenance
    citation: str = Field(
        ...,
        description=(
            "paper:section grounding this link. E.g. 'Brehm 1966 §3.1', "
            "'Friestad & Wright 1994 p.4', 'Steindl et al. 2015 fig.2'. "
            "Required field — links without canonical citations should "
            "not exist in chain attestations."
        ),
    )
    calibration_status: CalibrationStatus = CalibrationStatus.PINNED

    # When user/decision evidence was insufficient and the link was
    # instantiated from cohort priors only — flag so downstream consumers
    # can weight accordingly. False by default; set True only when the
    # atom resorted to prior-derived instantiation.
    from_prior_only: bool = Field(default=False)

    @property
    def link_key(self) -> str:
        """The TheoryLearner.LinkPosterior key for this link.

        Format: "{relation_type}:{source_construct}:{target_construct}"
        Matches the existing LinkPosterior key convention so outcomes
        update the same posterior whether emitted via this primitive
        or via legacy chain code.
        """
        return f"{self.relation_type.value}:{self.source_construct}:{self.target_construct}"

    def describe(self) -> str:
        """Human-readable single-link description."""
        prior_marker = " (prior-only)" if self.from_prior_only else ""
        return (
            f"{self.source_construct} -[{self.relation_type.value}]-> "
            f"{self.target_construct}"
            f" [ev={self.evidence_value:.2f}, conf={self.confidence:.2f}, "
            f"{self.calibration_status.value}, {self.citation}]{prior_marker}"
        )


# =============================================================================
# TYPED EVIDENCE — A SCALAR WITH PROVENANCE
# =============================================================================

class TypedEvidence(BaseModel):
    """A scalar assessment value with explicit provenance.

    Distinct from `IntelligenceEvidence` in `evidence.py` — that model is
    per-source (which of the 10 intelligence sources contributed). This
    model is per-construct-emission with explicit calibration status and
    formula citation, designed to flow through the chain-attestation
    primitive into L3 consumption and learning-loop updates.
    """

    construct: str = Field(..., description="The construct this evidence assesses")
    value: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    citation: str = Field(
        ...,
        description="paper:section grounding the formula that produced this value",
    )
    calibration_status: CalibrationStatus = CalibrationStatus.PINNED


# =============================================================================
# ADJUSTMENT EVIDENCE — A MECHANISM ADJUSTMENT WITH CHAIN PROVENANCE
# =============================================================================

class AdjustmentEvidence(BaseModel):
    """A mechanism adjustment derived from specific chain links.

    The `chain_links_responsible` field is the load-bearing detail: it
    records WHICH chain links drove this adjustment, so when the
    mechanism's outcome arrives the learning loop can update those
    specific LinkPosteriors (theory-revision update, foundation §4.4)
    rather than smearing the outcome credit across the whole chain.
    """

    mechanism_id: str = Field(
        ...,
        description="The mechanism being adjusted (e.g., 'scarcity', 'authority')",
    )
    adjustment_value: float = Field(
        ...,
        description=(
            "Adjustment applied to the mechanism's score. Negative = penalty "
            "(suppress mechanism), positive = boost (amplify mechanism). "
            "No fixed range — interpretation is mechanism-scoring-pipeline-specific."
        ),
    )
    chain_links_responsible: List[str] = Field(
        default_factory=list,
        description=(
            "The link_id values from the parent chain that drove this "
            "adjustment. Used by OutcomeHandler to update the specific "
            "LinkPosteriors when the mechanism's outcome arrives."
        ),
    )
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    rationale: str = Field(
        default="",
        description="Brief plain-language rationale (for debugging/dashboards)",
    )


# =============================================================================
# CHAIN PROVENANCE — ATOM IDENTITY + FORMULA HASHES
# =============================================================================

class ChainProvenance(BaseModel):
    """Identity and formula provenance for an atom's chain-attestation output.

    Tracks the atom version that produced the chain (so chains produced
    before/after a redo can be distinguished in the learning loop) and
    the active A14 flags (so pilot-pending placeholders are visible to
    downstream measurement frameworks).
    """

    atom_id: str
    atom_version: str = Field(
        default="1.0",
        description="Bump on canonical-formula or chain-shape changes; not on bug fixes",
    )
    formula_citations: List[str] = Field(
        default_factory=list,
        description="All paper:section references the atom used for this decision",
    )
    a14_flags_active: List[str] = Field(
        default_factory=list,
        description=(
            "Active A14 calibration-pending flags (e.g., "
            "'REACTANCE_THRESHOLD_COEFFICIENTS_PILOT_PENDING'). Surfaces "
            "to per-atom contribution measurement so pilot-pending vs. "
            "pinned scores can be analyzed separately."
        ),
    )
    produced_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


# =============================================================================
# CHAIN ATTESTATION — THE TOP-LEVEL OBJECT
# =============================================================================

class ChainAttestation(BaseModel):
    """An atom's typed-evidence chain-attestation output.

    Foundation §4.3 commitment materialized: every atom that emits a
    scalar must also emit the chain of construct activations that
    produced the scalar, tagged with the literature grounding each link,
    consumed downstream as chain — not scalar.

    Emitted alongside (not replacing) the existing `AtomOutput`. Atoms
    that have not been redone against the discipline rule emit no
    chain-attestation; the absence is the signal that the atom remains
    a wrapper.

    Consumed by:
    - L3 bilateral cascade (`level3_bilateral_edges` at
      `bilateral_cascade.py:961`) — chain-derived mechanism contributions
      combine multiplicatively with bilateral-edge contributions.
    - OutcomeHandler — per-link feedback routes to
      `TheoryLearner.process_chain_outcome` via `to_chain_data()`.
    - Per-atom contribution measurement framework (Phase 3 deliverable).
    """

    attestation_id: str = Field(
        default_factory=lambda: f"att_{uuid4().hex[:12]}"
    )
    atom_id: str
    request_id: str
    target_construct: str = Field(
        ...,
        description="The atom's primary construct (e.g., 'reactance_threshold')",
    )

    # The reasoning chain — ordered links from input observation to
    # final assessment. Empty list signals "atom ran but had no chain
    # evidence to attest" (e.g., total prefetch failure).
    chain: List[ConstructLink] = Field(default_factory=list)

    # The final scalar assessment with provenance. The chain produces
    # this value; downstream consumers can use either the scalar (legacy
    # path) or the full chain (new path).
    final_assessment: TypedEvidence

    # Mechanism adjustments derived from the chain. Each adjustment
    # records the link_ids from the chain that drove it.
    mechanism_adjustments: List[AdjustmentEvidence] = Field(default_factory=list)

    # Atom version, formula citations, A14 flags
    provenance: ChainProvenance

    # ------------------------------------------------------------------
    # INTEGRATION CONTRACT — TheoryLearner
    # ------------------------------------------------------------------

    @property
    def theoretical_link_keys(self) -> List[str]:
        """LinkPosterior keys for every link in the chain.

        Used by `TheoryLearner.process_chain_outcome(chain_data=...)`.
        Order matches `chain` order; duplicates preserved (a chain may
        legitimately fire the same link twice in different positions).
        """
        return [link.link_key for link in self.chain]

    def to_chain_data(self, recommended_mechanism: str = "") -> Dict[str, Any]:
        """Convert to the dict shape `TheoryLearner.process_chain_outcome` expects.

        Args:
            recommended_mechanism: The mechanism this chain ultimately
                supported (or suppressed). Optional; passed through to
                the chain pattern stats for aggregate analysis.

        Returns:
            dict with keys: chain_id, theoretical_link_keys, recommended_mechanism.
        """
        return {
            "chain_id": self.attestation_id,
            "theoretical_link_keys": self.theoretical_link_keys,
            "recommended_mechanism": recommended_mechanism,
        }

    # ------------------------------------------------------------------
    # DEBUGGING / DASHBOARDS
    # ------------------------------------------------------------------

    def chain_summary(self) -> str:
        """Human-readable chain summary for logging and dashboards.

        Example:
            "high_persuasion_knowledge -[AMPLIFIES]-> reactance_response
            -[PRODUCES]-> mechanism_backfire"
        """
        if not self.chain:
            return f"{self.target_construct}: empty chain"
        parts: List[str] = [self.chain[0].source_construct]
        for link in self.chain:
            parts.append(f"-[{link.relation_type.value}]->")
            parts.append(link.target_construct)
        return " ".join(parts)

    def has_pilot_pending_links(self) -> bool:
        """True if any link in the chain has calibration_status PILOT_PENDING.

        Used by per-atom contribution measurement to segment scores by
        pinned-only vs. mixed-calibration chains during pilot.
        """
        return any(
            link.calibration_status == CalibrationStatus.PILOT_PENDING
            for link in self.chain
        )
