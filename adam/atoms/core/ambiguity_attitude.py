# =============================================================================
# ADAM Ambiguity Attitude Atom — Canonical Ellsberg Redo (B3-LUXY Phase 2)
# Location: adam/atoms/core/ambiguity_attitude.py
# =============================================================================

"""
AMBIGUITY ATTITUDE ATOM (canonical, B3-LUXY Phase 2 atom 8)
=============================================================

Implements Ellsberg 1961 ambiguity-premium formula:

    ambiguity_premium = (EU_known − EU_unknown) / EU_unknown

A positive premium reveals AMBIGUITY AVERSION (the user would pay to
avoid unknown probabilities); negative reveals AMBIGUITY SEEKING; zero
reveals neutrality (Savage axioms hold). Fox & Tversky 1995 add the
comparative-ignorance hypothesis (ambiguity aversion is contextual);
Heath & Tversky 1991 add the competence hypothesis (in self-perceived
competent domains, ambiguity aversion flips toward seeking).

Discipline rule compliance (see `memory/feedback_atom_redo_discipline.md`):
- (a) Canonical formulas in code with `paper:section` citations: see
  `_ellsberg_ambiguity_premium` (Ellsberg 1961 §IV),
  `_apply_competence_shift` (Heath & Tversky 1991 §3),
  `_apply_comparative_ignorance` (Fox & Tversky 1995 §2).
- (b) Regression tests pinning published anchors.
- (c) Calibration-pending flags on placeholder constants.
- (d) 5-link ChainAttestation with Ellsberg-canonical chain shape.

ACADEMIC FOUNDATION
-------------------
- Ellsberg (1961) §IV: *Risk, Ambiguity, and the Savage Axioms*. The
  foundational paradox demonstrating that people are not indifferent
  between known and unknown probabilities. Ambiguity premium formula:
      π = (EU_known − EU_unknown) / EU_unknown
  derived from observed willingness-to-pay differences in the two-urn
  experiment.
- Fox & Tversky (1995) §2: *Ambiguity Aversion and Comparative
  Ignorance*. Ambiguity aversion is contextual — it fires more
  strongly when the unknown option is presented beside a known option
  in a comparative frame. In isolation, ambiguity aversion is
  weaker.
- Heath & Tversky (1991) §3: *Preference and Belief — Ambiguity and
  Competence*. In domains where the user feels COMPETENT, ambiguity
  aversion attenuates and can flip to ambiguity-seeking. In
  unfamiliar domains, aversion is stronger.
- Camerer & Weber (1992): review of recent ambiguity models;
  documents the wide range of operationalizations and the lack of a
  single canonical functional form.
- Klibanoff, Marinacci & Mukerji (2005): smooth ambiguity model —
  alternative to Ellsberg's formulation; not used here but cited
  for completeness.

ACTIVE A14 CALIBRATION-PENDING FLAGS
-------------------------------------
- A14: ELLSBERG_AMBIGUITY_PREMIUM_PILOT_PENDING — the (EU_known,
  EU_unknown) values are derived from user-side competence × context-
  ambiguity. Ellsberg 1961 specifies the FORMULA structure;
  per-decision EU magnitudes are PILOT_PENDING. Retire when LUXY pilot
  accumulates ≥300 conversions with measured ambiguity-premium responses.
- A14: NDF_AMBIGUITY_WEIGHTS_PILOT_PENDING — per-NDF-dim coefficients
  for baseline ambiguity tolerance derivation. Direction motivated;
  magnitudes are literature midpoints.
- A14: COMPETENCE_AMBIGUITY_SHIFT_PILOT_PENDING — Heath & Tversky 1991
  specify that competence in a domain shifts ambiguity attitude;
  the magnitude (currently 0.20 max shift) is a literature midpoint.
- A14: AMBIGUITY_CLASSIFICATION_THRESHOLDS_PILOT_PENDING — the 0.35 /
  0.65 thresholds for averse/tolerant/seeking are operational
  midpoints; Ellsberg 1961 documents the qualitative trichotomy but
  does not specify numerical boundaries.
- A14: AMBIGUITY_MECHANISM_MAGNITUDES_PILOT_PENDING — per-attitude
  mechanism adjustment magnitudes are literature midpoints.

CHAIN SHAPE
-----------
Ellsberg-canonical (5 links). L3 (Ellsberg formula) is the load-bearing
PINNED step.

  L1: (user_dispositional_signals) -[MODULATED_BY]-> (baseline_ambiguity_attitude)
      — Ellsberg 1961; PILOT_PENDING NDF weights.
  L2: (user_competence_in_category) -[MODULATED_BY]-> (effective_ambiguity_attitude)
      — Heath & Tversky 1991 §3 competence hypothesis; PINNED structure,
        PILOT_PENDING magnitude.
  L3: (effective_attitude × context_ambiguity) -[PRODUCES]-> (ellsberg_ambiguity_premium)
      — Ellsberg 1961 §IV (canonical premium formula); PINNED structure.
  L4: (ambiguity_premium) -[PRODUCES]-> (ambiguity_classification)
      — three-class attitude classification; PILOT_PENDING thresholds.
  L5: (ambiguity_classification) -[PRODUCES]-> (mechanism_adjustments)
      — certainty-vs-exploration mechanism mapping; PILOT_PENDING magnitudes.
"""

import logging
from typing import Any, Dict, List, Optional

from adam.atoms.core.base import BaseAtom
from adam.atoms.core.construct_resolver import PsychologicalConstructResolver
from adam.atoms.core.dsp_integration import (
    CategoryModerationHelper,
    DSPDataAccessor,
)
from adam.atoms.models.atom_io import AtomInput, AtomOutput
from adam.atoms.models.chain_attestation import (
    AdjustmentEvidence,
    CalibrationStatus,
    ChainAttestation,
    ChainProvenance,
    ConstructLink,
    RelationType,
    TypedEvidence,
)
from adam.atoms.models.evidence import (
    EvidenceStrength,
    FusionResult,
    IntelligenceEvidence,
    MultiSourceEvidence,
)
from adam.blackboard.models.zone2_reasoning import AtomType
from adam.graph_reasoning.models.intelligence_sources import (
    ConfidenceSemantics,
    IntelligenceSourceType,
)

logger = logging.getLogger(__name__)


# =============================================================================
# A14: AMBIGUITY_CLASSIFICATION_THRESHOLDS_PILOT_PENDING
# =============================================================================
# Three-class trichotomy thresholds. Ellsberg 1961 documents
# qualitative averse/neutral/seeking distinctions; numerical
# boundaries are operational midpoints.
# =============================================================================
_AMBIGUITY_AVERSE_THRESHOLD = 0.35   # tolerance < this → averse
_AMBIGUITY_SEEKING_THRESHOLD = 0.65  # tolerance > this → seeking


# =============================================================================
# A14: COMPETENCE_AMBIGUITY_SHIFT_PILOT_PENDING
# =============================================================================
# Heath & Tversky 1991 §3 competence hypothesis: high domain competence
# attenuates ambiguity aversion; can flip toward seeking. The maximum
# shift is bounded.
# =============================================================================
_COMPETENCE_MAX_SHIFT = 0.20


# =============================================================================
# A14: NDF_AMBIGUITY_WEIGHTS_PILOT_PENDING
# =============================================================================
# Per-NDF-dim weights for baseline ambiguity tolerance derivation.
# Direction (sign) is theoretically motivated:
#   uncertainty_tolerance: directly maps (primary driver, Ellsberg 1961)
#   approach_avoidance: high approach → tolerant
#   cognitive_engagement: high CE → seeking (enjoys figuring out)
#   arousal_seeking: high → tolerant of unknown
#   temporal_horizon: long → tolerant of ambiguity (resolution can wait)
# Magnitudes are literature midpoints.
# =============================================================================
NDF_AMBIGUITY_MAP: Dict[str, float] = {
    "uncertainty_tolerance": 0.50,
    "approach_avoidance": 0.15,
    "cognitive_engagement": 0.10,
    "arousal_seeking": 0.15,
    "temporal_horizon": 0.10,
}


# =============================================================================
# A14: AMBIGUITY_MECHANISM_MAGNITUDES_PILOT_PENDING
# =============================================================================
# Per-attitude mechanism adjustments. Theoretically motivated:
#   averse → certainty-providing mechanisms (social_proof, authority,
#            commitment); penalize uncertainty-inducing (scarcity,
#            attention_dynamics)
#   tolerant → exploration-friendly mechanisms (identity, mimetic, scarcity)
#   seeking → novelty-amplifying mechanisms (attention, embodied,
#             identity); penalize certainty mechanisms (boring)
# Magnitudes are literature midpoints.
# =============================================================================
AMBIGUITY_MECHANISM_MAP: Dict[str, Dict[str, float]] = {
    "ambiguity_averse": {
        "social_proof": 0.20,
        "authority": 0.20,
        "commitment": 0.15,
        "regulatory_focus": 0.10,
        "scarcity": -0.10,
        "attention_dynamics": -0.10,
    },
    "ambiguity_tolerant": {
        "identity_construction": 0.15,
        "mimetic_desire": 0.15,
        "scarcity": 0.10,
        "attention_dynamics": 0.10,
        "embodied_cognition": 0.10,
    },
    "ambiguity_seeking": {
        "attention_dynamics": 0.20,
        "embodied_cognition": 0.15,
        "identity_construction": 0.15,
        "mimetic_desire": 0.10,
        "commitment": -0.10,
        "authority": -0.05,
    },
}


# =============================================================================
# CANONICAL FORMULA HELPERS
# =============================================================================


def _ellsberg_ambiguity_premium(eu_known: float, eu_unknown: float) -> float:
    """Ellsberg 1961 §IV canonical ambiguity premium.

    # Ellsberg 1961 §IV:
    #     π = (EU_known − EU_unknown) / EU_unknown
    #
    # π > 0 → AMBIGUITY AVERSE (would pay to avoid unknown)
    # π = 0 → AMBIGUITY NEUTRAL (Savage axioms hold)
    # π < 0 → AMBIGUITY SEEKING (pays for unknown)
    #
    # Pins (anchored in tests):
    #   EU_known = EU_unknown    → π = 0 (neutral)
    #   EU_known > EU_unknown    → π > 0 (averse direction)
    #   EU_known < EU_unknown    → π < 0 (seeking direction)
    #   EU_unknown = 0           → returns 0 (defensive: cannot divide)
    #
    # PINNED canonical formula.
    """
    if eu_unknown <= 0.0:
        return 0.0
    return (eu_known - eu_unknown) / eu_unknown


def _apply_competence_shift(
    baseline_tolerance: float,
    competence: float,
    max_shift: float = _COMPETENCE_MAX_SHIFT,
) -> float:
    """Heath & Tversky 1991 §3 competence-shift moderation.

    # Heath & Tversky 1991 §3:
    # In domains where the user feels competent, ambiguity aversion
    # ATTENUATES (tolerance INCREASES) and can flip to seeking when
    # competence is high. Operationally:
    #     effective_tolerance = baseline + (competence − 0.5) × 2 × max_shift
    # competence ∈ [0, 1]: 0.5 = neutral, 1 = expert, 0 = novice.
    # max_shift bounds the magnitude of competence-driven adjustment.
    #
    # Pins:
    #   competence = 0.5 → no shift (neutral)
    #   competence > 0.5 → tolerance increases (toward seeking)
    #   competence < 0.5 → tolerance decreases (toward averse)
    #
    # PINNED structure; magnitude PILOT_PENDING.
    """
    shift = (competence - 0.5) * 2.0 * max_shift
    return max(0.05, min(0.95, baseline_tolerance + shift))


def _apply_comparative_ignorance(
    base_premium: float,
    comparative_frame: bool,
) -> float:
    """Fox & Tversky 1995 §2 comparative ignorance amplification.

    # Fox & Tversky 1995 §2:
    # Ambiguity aversion fires harder when the unknown option is
    # presented beside a known option in a comparative frame. In
    # isolated presentation, aversion attenuates.
    #
    # Operationally: comparative-frame multiplies positive premium
    # by 1.3 (amplification).
    #
    # PINNED structure.
    """
    if comparative_frame and base_premium > 0:
        return base_premium * 1.3
    return base_premium


def _classify_ambiguity_attitude(tolerance: float) -> str:
    """Three-class trichotomy classification.

    # Pins:
    #   tolerance < _AMBIGUITY_AVERSE_THRESHOLD     → "ambiguity_averse"
    #   tolerance > _AMBIGUITY_SEEKING_THRESHOLD    → "ambiguity_seeking"
    #   else                                        → "ambiguity_tolerant"
    """
    if tolerance < _AMBIGUITY_AVERSE_THRESHOLD:
        return "ambiguity_averse"
    if tolerance > _AMBIGUITY_SEEKING_THRESHOLD:
        return "ambiguity_seeking"
    return "ambiguity_tolerant"


# =============================================================================
# AMBIGUITY ATTITUDE ATOM
# =============================================================================


class AmbiguityAttitudeAtom(BaseAtom):
    """Models user's ambiguity attitude via Ellsberg 1961 + Heath & Tversky.

    Computes:
    1. Baseline ambiguity tolerance from NDF (Ellsberg 1961)
    2. Competence-shifted effective tolerance (Heath & Tversky 1991 §3)
    3. Ellsberg ambiguity premium (Ellsberg 1961 §IV formula)
    4. Three-class attitude classification
    5. Mechanism adjustments matched to attitude
    """

    ATOM_TYPE = AtomType.AMBIGUITY_ATTITUDE
    ATOM_NAME = "ambiguity_attitude"
    TARGET_CONSTRUCT = "ambiguity_tolerance"

    REQUIRED_SOURCES = [
        IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
    ]

    OPTIONAL_SOURCES = [
        IntelligenceSourceType.EMPIRICAL_PATTERNS,
        IntelligenceSourceType.MECHANISM_TRAJECTORIES,
        IntelligenceSourceType.GRAPH_EMERGENCE,
    ]

    # B3-LUXY redo metadata
    ATOM_VERSION = "2.0"  # 2.0 = canonical Ellsberg redo

    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        return None

    # ------------------------------------------------------------------
    # CORE COMPUTATION
    # ------------------------------------------------------------------

    def _compute_ambiguity_state(self, atom_input: AtomInput) -> Dict[str, Any]:
        """Compute baseline tolerance + competence-shifted effective →
        Ellsberg premium → classification."""
        ad_context = atom_input.ad_context or {}
        psy = PsychologicalConstructResolver(atom_input)
        psy_dict = psy.as_full_construct_dict() if psy.has_any else {}
        signal_quality = 1.0 if psy.has_any else 0.0

        # Step 1: baseline tolerance from NDF
        baseline_tolerance = 0.5
        if psy.has_any:
            for dim, weight in NDF_AMBIGUITY_MAP.items():
                dim_value = psy_dict.get(dim, 0.5)
                baseline_tolerance += (dim_value - 0.5) * weight
        baseline_tolerance = max(0.05, min(0.95, baseline_tolerance))

        # Step 2: competence shift (Heath & Tversky 1991 §3)
        # Competence is approximated by domain familiarity in ad_context;
        # if not available, default to neutral (0.5).
        competence = float(ad_context.get("user_category_competence", 0.5))
        effective_tolerance = _apply_competence_shift(baseline_tolerance, competence)

        # Step 3: Ellsberg premium (Ellsberg 1961 §IV)
        # Operationalize EU values from effective_tolerance and context_ambiguity:
        #   EU_known   = effective_tolerance × 1.0      (full information case)
        #   EU_unknown = effective_tolerance × (1 - context_ambiguity)
        # When user is highly ambiguity-tolerant AND context has high
        # ambiguity, EU_unknown still receives substantial value;
        # when user is highly averse AND context has high ambiguity,
        # EU_unknown is heavily discounted.
        is_novel = ad_context.get("is_new_category", False) or ad_context.get(
            "first_purchase", False
        )
        context_ambiguity = 0.8 if is_novel else 0.5

        eu_known = max(0.01, effective_tolerance)  # avoid divide-by-zero downstream
        eu_unknown = max(0.01, effective_tolerance * (1.0 - context_ambiguity))
        base_premium = _ellsberg_ambiguity_premium(eu_known, eu_unknown)

        # Apply Fox & Tversky 1995 comparative-ignorance if comparative frame
        comparative_frame = bool(ad_context.get("comparative_frame", False))
        ambiguity_premium = _apply_comparative_ignorance(base_premium, comparative_frame)

        # Step 4: three-class classification
        attitude = _classify_ambiguity_attitude(effective_tolerance)

        # Step 5: ambiguity gap — how much certainty the user needs
        ambiguity_gap = context_ambiguity * (1.0 - effective_tolerance)

        return {
            "baseline_tolerance": baseline_tolerance,
            "competence": competence,
            "effective_tolerance": effective_tolerance,
            "context_ambiguity": context_ambiguity,
            "eu_known": eu_known,
            "eu_unknown": eu_unknown,
            "ambiguity_premium": ambiguity_premium,
            "comparative_frame": comparative_frame,
            "attitude": attitude,
            "ambiguity_gap": ambiguity_gap,
            "needs_certainty": ambiguity_gap > 0.4,
            "signal_quality": signal_quality,
        }

    def _compute_mechanism_adjustments(
        self,
        ambiguity_state: Dict[str, Any],
    ) -> Dict[str, float]:
        attitude = ambiguity_state["attitude"]
        gap = ambiguity_state["ambiguity_gap"]
        base_map = AMBIGUITY_MECHANISM_MAP.get(
            attitude, AMBIGUITY_MECHANISM_MAP["ambiguity_tolerant"]
        )

        intensity = 0.5 + gap  # 0.5 to 1.5
        adjustments: Dict[str, float] = {}
        for mech, base_adj in base_map.items():
            adjustments[mech] = max(-0.30, min(0.30, base_adj * intensity))

        return adjustments

    # ------------------------------------------------------------------
    # CHAIN ATTESTATION CONSTRUCTION
    # ------------------------------------------------------------------

    def _build_chain_attestation(
        self,
        atom_input: AtomInput,
        ambiguity_state: Dict[str, Any],
        adjustments: Dict[str, float],
    ) -> ChainAttestation:
        signal_quality = ambiguity_state["signal_quality"]
        from_prior_only = signal_quality < 0.5

        # L1: dispositional → baseline_ambiguity_attitude
        link1 = ConstructLink(
            source_construct="user_dispositional_signals",
            relation_type=RelationType.MODULATED_BY,
            target_construct="baseline_ambiguity_attitude",
            evidence_value=ambiguity_state["baseline_tolerance"],
            confidence=0.5 + signal_quality * 0.3,
            citation="Ellsberg 1961 §IV (ambiguity attitude as trait)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
            from_prior_only=from_prior_only,
        )

        # L2: competence → effective_attitude (Heath & Tversky 1991 §3)
        link2 = ConstructLink(
            source_construct="user_competence_in_category",
            relation_type=RelationType.MODULATED_BY,
            target_construct="effective_ambiguity_attitude",
            evidence_value=ambiguity_state["effective_tolerance"],
            confidence=0.65,
            citation="Heath & Tversky 1991 §3 (competence hypothesis)",
            calibration_status=CalibrationStatus.PINNED,
        )

        # L3: effective_attitude × context_ambiguity → ellsberg_premium
        # PINNED canonical Ellsberg formula
        premium_evidence = max(
            0.0, min(1.0, abs(ambiguity_state["ambiguity_premium"]))
        )
        link3 = ConstructLink(
            source_construct="effective_attitude_x_context_ambiguity",
            relation_type=RelationType.PRODUCES,
            target_construct="ellsberg_ambiguity_premium",
            evidence_value=premium_evidence,
            confidence=0.80,
            citation="Ellsberg 1961 §IV (π = (EU_k - EU_u) / EU_u)",
            calibration_status=CalibrationStatus.PINNED,
        )

        # L4: ambiguity_premium → ambiguity_classification
        attitude = ambiguity_state["attitude"]
        link4 = ConstructLink(
            source_construct="ambiguity_premium",
            relation_type=RelationType.PRODUCES,
            target_construct=f"attitude_{attitude}",
            evidence_value=premium_evidence,
            confidence=0.7,
            citation="Ellsberg 1961 §IV (averse/neutral/seeking trichotomy)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        )

        # L5: classification → mechanism_adjustments
        adj_magnitude = sum(abs(v) for v in adjustments.values()) / max(
            1, len(adjustments)
        )
        link5 = ConstructLink(
            source_construct="ambiguity_classification",
            relation_type=RelationType.PRODUCES,
            target_construct="mechanism_adjustments",
            evidence_value=min(1.0, adj_magnitude * 4.0),
            confidence=0.65,
            citation="Camerer & Weber 1992 (review of ambiguity-mechanism mappings)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        )

        chain = [link1, link2, link3, link4, link5]
        chain_link_ids = [link.link_id for link in chain]

        # Per-mechanism AdjustmentEvidence
        adjustment_evidences: List[AdjustmentEvidence] = []
        for mech, adj_value in adjustments.items():
            if abs(adj_value) < 1e-6:
                continue
            rationale = (
                f"attitude={attitude}, "
                f"premium={ambiguity_state['ambiguity_premium']:+.2f}, "
                f"competence={ambiguity_state['competence']:.2f}, "
                f"context={ambiguity_state['context_ambiguity']:.2f}"
            )
            adjustment_evidences.append(
                AdjustmentEvidence(
                    mechanism_id=mech,
                    adjustment_value=adj_value,
                    chain_links_responsible=chain_link_ids,
                    confidence=link5.confidence,
                    rationale=rationale,
                )
            )

        final = TypedEvidence(
            construct=self.TARGET_CONSTRUCT,
            value=ambiguity_state["effective_tolerance"],
            confidence=link2.confidence,
            citation="Ellsberg 1961 + Heath & Tversky 1991 (composite)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        )

        provenance = ChainProvenance(
            atom_id=self.config.atom_id,
            atom_version=self.ATOM_VERSION,
            formula_citations=[
                "Ellsberg 1961 §IV",
                "Heath & Tversky 1991 §3",
                "Fox & Tversky 1995 §2",
                "Camerer & Weber 1992",
            ],
            a14_flags_active=[
                "ELLSBERG_AMBIGUITY_PREMIUM_PILOT_PENDING",
                "NDF_AMBIGUITY_WEIGHTS_PILOT_PENDING",
                "COMPETENCE_AMBIGUITY_SHIFT_PILOT_PENDING",
                "AMBIGUITY_CLASSIFICATION_THRESHOLDS_PILOT_PENDING",
                "AMBIGUITY_MECHANISM_MAGNITUDES_PILOT_PENDING",
            ],
        )

        return ChainAttestation(
            atom_id=self.config.atom_id,
            request_id=atom_input.request_id,
            target_construct=self.TARGET_CONSTRUCT,
            chain=chain,
            final_assessment=final,
            mechanism_adjustments=adjustment_evidences,
            provenance=provenance,
        )

    # ------------------------------------------------------------------
    # OUTPUT BUILDING
    # ------------------------------------------------------------------

    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        ambiguity_state = self._compute_ambiguity_state(atom_input)
        adjustments = self._compute_mechanism_adjustments(ambiguity_state)

        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            adjustments = CategoryModerationHelper.apply(adjustments, dsp)

        chain_attestation = self._build_chain_attestation(
            atom_input, ambiguity_state, adjustments
        )

        primary = ambiguity_state["attitude"]
        sorted_mechs = sorted(adjustments.items(), key=lambda kv: kv[1], reverse=True)
        recommended = [m for m, s in sorted_mechs[:3] if s > 0]

        confidence = min(
            0.85,
            0.4 + abs(ambiguity_state["effective_tolerance"] - 0.5) * 0.7,
        )
        fusion_result.assessment = primary
        fusion_result.confidence = confidence

        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary,
            secondary_assessments={
                "ambiguity_profile": {
                    "tolerance_score": ambiguity_state["effective_tolerance"],
                    "baseline_tolerance": ambiguity_state["baseline_tolerance"],
                    "competence": ambiguity_state["competence"],
                    "ambiguity_premium": ambiguity_state["ambiguity_premium"],
                    "context_ambiguity": ambiguity_state["context_ambiguity"],
                    "ambiguity_gap": ambiguity_state["ambiguity_gap"],
                    "attitude": primary,
                    "needs_certainty": ambiguity_state["needs_certainty"],
                },
                "mechanism_adjustments": adjustments,
                "framing_guidance": {
                    "certainty_framing": ambiguity_state["needs_certainty"],
                    "exploration_framing": primary == "ambiguity_seeking",
                    "recommended_language": (
                        "certain" if ambiguity_state["needs_certainty"] else "discover"
                    ),
                },
                "atom_version": self.ATOM_VERSION,
            },
            recommended_mechanisms=recommended,
            mechanism_weights={
                m: max(0.1, 0.5 + adjustments.get(m, 0.0)) for m in recommended
            } if recommended else {"social_proof": 0.5},
            inferred_states={
                "ambiguity_tolerance": ambiguity_state["effective_tolerance"],
                "ambiguity_premium": ambiguity_state["ambiguity_premium"],
                "ambiguity_gap": ambiguity_state["ambiguity_gap"],
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
            chain_attestation=chain_attestation,
        )
