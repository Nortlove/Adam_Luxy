# =============================================================================
# ADAM Strategic Awareness Atom — Canonical PKM Redo (B3-LUXY Phase 1)
# Location: adam/atoms/core/strategic_awareness.py
# =============================================================================

"""
STRATEGIC AWARENESS ATOM (canonical, B3-LUXY Phase 1 atom 4)
=============================================================

Models the user's Persuasion Knowledge Model (Friestad & Wright 1994):
the user's mental model of how persuasion works, and how they cope with
detected persuasion attempts. The atom computes per-mechanism detection
probability and routes around defenses by recommending stealthy
mechanisms.

Distinctive feature (per the plan doc): chain shape includes a FEEDBACK
LOOP from prior exposures — repeated exposure to a given mechanism
amplifies PK for that mechanism (Friestad & Wright 1994 §3: PK is
experience-learned). This is structurally different from the linear
chain in atoms 1-3.

Discipline rule compliance (see `memory/feedback_atom_redo_discipline.md`):
- (a) Canonical formulas in code with `paper:section` citations: see
  `_compute_baseline_pk` (Friestad & Wright 1994 §2), `_apply_exposure_feedback`
  (§3), `_compute_detection_probability` (§4), `_compute_correction_effect`
  (Wegener et al. 2004 §2).
- (b) Regression tests pinning published anchors: see
  `tests/unit/test_strategic_awareness_canonical.py`.
- (c) Calibration-pending flags on placeholder constants.
- (d) 5-link ChainAttestation with feedback-loop shape.

ACADEMIC FOUNDATION
-------------------
- Friestad & Wright (1994): A Persuasion Knowledge Model of consumer
  responses to advertising. The canonical PKM source. §2 defines PK
  as one of three mental knowledge structures (PK, agent knowledge,
  topic knowledge); §3 establishes that PK is learned through experience
  (the feedback-loop basis); §4 establishes that PK detection is
  mechanism-selective (high PK for one tactic doesn't transfer).
- Wegener, Petty, Detweiler-Bedell & Jarvis (2001 / 2004 §2): Flexible
  Correction Model. When users detect persuasion, they correct for it
  rather than reverse it — and often overcorrect, producing effects
  opposite to the persuasion attempt's intended direction.
- Campbell & Kirmani (2000): Inference of ulterior motives. The
  diagnostic step in PKM activation: users compute a probability of
  hidden persuasion motive, and this triggers PKM coping responses.
- Isaac & Grayson (2017): Beyond skepticism — calibrated trust.
  Modern extension: PK doesn't always produce skepticism; sometimes it
  produces calibrated trust when source is genuine.

ACTIVE A14 CALIBRATION-PENDING FLAGS
-------------------------------------
- A14: NDF_TO_PKM_COEFFICIENTS_PILOT_PENDING — the per-NDF-dim weights
  in `NDF_TO_PKM` are theoretically motivated (high cognitive_engagement
  → ↑ PK; high uncertainty_tolerance → ↓ PK) but the magnitudes are
  literature midpoints. Retire when LUXY pilot accumulates ≥150
  decisions with PK-stratified outcome distributions.
- A14: PKM_DETECTABILITY_LITERATURE_MIDPOINTS_PILOT_PENDING — the
  per-mechanism detectability magnitudes in `MECHANISM_DETECTABILITY`
  are literature midpoints. Retire when pilot accumulates ≥50 detection
  events per mechanism.
- A14: PKM_EXPOSURE_FEEDBACK_RATE_PILOT_PENDING — the exposure-count
  amplification rate (κ_pk) for the feedback-loop link is a literature
  midpoint. Friestad & Wright 1994 §3 specifies the feedback dynamic
  but not a magnitude. Retire when pilot accumulates ≥100 multi-
  exposure decisions with per-exposure PK measurement.
- A14: WEGENER_OVERCORRECTION_PENALTY_PILOT_PENDING — Wegener et al.
  2004 specifies that high-PK detection produces correction, often
  overcorrection. The 15% global penalty for very-high-PK users is a
  literature-midpoint placeholder.

CHAIN SHAPE
-----------
Linear-with-feedback-loop (5 links). L2 is the novel element — a
feedback link where prior exposures amplify the user's PK level. The
schema's `ConstructLink.from_prior_only` flag and the chain ordering
suffice to encode this without schema modification.

  L1: (user_dispositional_signals) -[MODULATED_BY]-> (baseline_persuasion_knowledge)
      — Friestad & Wright 1994 §2; PILOT_PENDING NDF→PK weights.
  L2: (prior_exposure_history) -[AMPLIFIES]-> (effective_persuasion_knowledge)
      — Friestad & Wright 1994 §3 (PK is experience-learned). FEEDBACK LOOP.
        PILOT_PENDING amplification rate.
  L3: (effective_PK × mechanism_detectability) -[PRODUCES]-> (detection_probability)
      — Friestad & Wright 1994 §4 (mechanism-selective detection);
        PILOT_PENDING magnitudes.
  L4: (detection_probability) -[THREATENS]-> (mechanism_effectiveness)
      — Wegener et al. 2004 §2 (flexible correction; detection produces
        correction not reversal); PINNED structure.
  L5: (mechanism_effectiveness) -[MODULATED_BY]-> (mechanism_adjustments)
      — stealth-aware mechanism scoring; PILOT_PENDING magnitudes.
"""

import logging
from typing import Any, Dict, List, Optional

from adam.atoms.core.base import BaseAtom
from adam.atoms.core.construct_resolver import PsychologicalConstructResolver
from adam.atoms.core.dsp_integration import DSPDataAccessor, SusceptibilityHelper
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
# A14: PKM_DETECTABILITY_LITERATURE_MIDPOINTS_PILOT_PENDING
# =============================================================================
# Per-mechanism inherent detectability ∈ [0, 1] — how easily a typical
# user with average PK recognizes the mechanism as a persuasion tactic.
# Synthesized from Friestad & Wright 1994 §4 examples + Cialdini 2001
# operationalizations.
#
# RETIRE: when pilot accumulates ≥50 detection events per mechanism
# (e.g., implicit detection signals: dwell-time anomalies, avoidance
# patterns, explicit feedback).
# =============================================================================
MECHANISM_DETECTABILITY: Dict[str, float] = {
    "scarcity": 0.85,         # "Only 3 left!" — overt
    "social_proof": 0.70,     # "Millions trust us" — recognized as tactic
    "urgency": 0.90,          # "Act now!" — most overt
    "reciprocity": 0.40,      # genuine-gift framing harder to detect
    "commitment": 0.50,       # foot-in-door less detectable
    "authority": 0.65,        # expert endorsements moderately detectable
    "liking": 0.30,           # rapport-building hard to detect
    "unity": 0.25,            # shared identity is subtle
    "storytelling": 0.20,     # narrative transport bypasses defenses
    "anchoring": 0.55,        # price anchoring moderately detectable
    "identity_construction": 0.35,  # subtle
    "mimetic_desire": 0.30,   # imitation operates non-consciously
    "embodied_cognition": 0.15,     # sensory language is deeply subtle
    "temporal_construal": 0.40,     # time framing partial
    "regulatory_focus": 0.45,       # gain/loss framing partial
    "attention_dynamics": 0.50,     # salience manipulation moderate
}


# =============================================================================
# A14: NDF_TO_PKM_COEFFICIENTS_PILOT_PENDING
# =============================================================================
# Per-NDF-dim coefficients for baseline PK derivation. Direction (sign)
# is theoretically motivated:
#   cognitive_engagement → ↑ PK (critical thinkers detect more)
#   social_calibration   → ↑ PK (social attunement detects social tactics)
#   uncertainty_tolerance→ ↓ PK (tolerance of uncertainty → less scrutiny)
#   approach_avoidance   → ↓ PK (cautious users have higher defenses;
#                          higher-approach users have lower defenses)
#   status_sensitivity   → ↑ PK (attuned to status manipulation)
# Magnitudes are literature midpoints.
# =============================================================================
NDF_TO_PKM: Dict[str, float] = {
    "cognitive_engagement": 0.35,
    "social_calibration": 0.20,
    "uncertainty_tolerance": -0.15,
    "approach_avoidance": -0.10,
    "status_sensitivity": 0.05,
}


# =============================================================================
# A14: PKM_EXPOSURE_FEEDBACK_RATE_PILOT_PENDING
# =============================================================================
# Friestad & Wright 1994 §3: PK is learned through experience. The more
# a user has been exposed to a tactic, the better they detect it.
# Operationally:
#     pk_amplifier(n) = 1.0 + κ_pk × log(1 + n - 1)
# where n = exposure_count. Logarithmic growth (Stewart & Badiani 1993
# review of cumulative-exposure operationalization).
#
# κ_pk = 0.10 produces these amplifiers:
#   n=1: 1.00, n=2: 1.07, n=5: 1.16, n=10: 1.23, n=20: 1.30
# Bounded above at PKM_MAX_AMPLIFIER to prevent unbounded growth.
#
# RETIRE: when pilot accumulates ≥100 multi-exposure decisions with
# per-exposure PK measurement.
# =============================================================================
_PKM_EXPOSURE_RATE = 0.10
_PKM_MAX_AMPLIFIER = 1.5  # cap on cumulative-exposure PK growth


# =============================================================================
# A14: WEGENER_OVERCORRECTION_PENALTY_PILOT_PENDING
# =============================================================================
# Wegener et al. 2004 §2 Flexible Correction Model: high-PK users who
# DETECT persuasion correct for it, often overcorrecting. Operationally,
# very-high-PK users (PK > 0.75) get a 15% additional penalty across all
# mechanisms — even ostensibly stealthy ones — because their global
# detection-vigilance overcorrects on average.
#
# RETIRE: when pilot calibrates the overcorrection magnitude across
# mechanisms with measured detection events.
# =============================================================================
_WEGENER_HIGH_PK_THRESHOLD = 0.75
_WEGENER_OVERCORRECTION_PENALTY = 0.85  # 15% reduction


# =============================================================================
# CANONICAL FORMULA HELPERS
# =============================================================================


def _compute_baseline_pk(
    psy_dict: Dict[str, float],
    has_signal: bool,
) -> float:
    """Baseline persuasion knowledge from dispositional NDF dimensions.

    # Friestad & Wright 1994 §2: PK is one of three knowledge structures
    # users build from experience and disposition. Disposition (cognitive
    # style, social attunement) gives a baseline that experience modifies.
    # PINNED: additive-deviation structure.
    # PILOT_PENDING: per-dim magnitudes (NDF_TO_PKM).
    """
    base_pk = 0.5  # baseline (no signal)
    if not has_signal:
        return base_pk
    for dim, weight in NDF_TO_PKM.items():
        dim_value = psy_dict.get(dim, 0.5)
        base_pk += (dim_value - 0.5) * weight
    return max(0.10, min(0.95, base_pk))


def _apply_exposure_feedback(baseline_pk: float, exposure_count: int) -> float:
    """Feedback-loop amplification of PK by prior exposures.

    # Friestad & Wright 1994 §3: PK is experience-learned. Repeat
    # exposure to a tactic teaches the user to recognize it; PK
    # amplifies logarithmically.
    # Stewart & Badiani 1993 reviews logarithmic operationalizations
    # of cumulative-exposure effects.
    #
    # Pins:
    #   pk(n=1) = baseline (no amplification on first exposure)
    #   pk(n>1) > baseline (monotonic increase)
    #   pk(n→∞) → bounded (never exceeds 0.95 or PKM_MAX_AMPLIFIER × baseline)
    """
    import math
    if exposure_count <= 1:
        return baseline_pk
    amplifier = 1.0 + _PKM_EXPOSURE_RATE * math.log(exposure_count)
    amplifier = min(_PKM_MAX_AMPLIFIER, amplifier)
    return min(0.95, baseline_pk * amplifier)


def _compute_detection_probability(
    pk_level: float,
    mechanism_detectability: float,
) -> float:
    """Per-mechanism detection probability.

    # Friestad & Wright 1994 §4: detection is mechanism-selective.
    # High PK in one area doesn't mean uniform detection.
    # Operationally:
    #     P(detect | mechanism) = mechanism_detectability × (0.3 + pk × 0.7)
    # The (0.3 + pk × 0.7) term ensures even low-PK users have non-zero
    # detection of overt mechanisms (Friestad & Wright 1994 §4: salience
    # of cue affects detection independent of PK).
    #
    # Pins:
    #   P(detect | low-PK, high-detectability) > 0 (overt cues detected)
    #   P(detect | high-PK, low-detectability) > P(low-PK, low-detectability)
    #   bounded ∈ [0.05, 0.95]
    """
    prob = mechanism_detectability * (0.3 + pk_level * 0.7)
    return max(0.05, min(0.95, prob))


def _compute_correction_effect(
    detection_prob: float,
    pk_level: float,
) -> float:
    """Wegener et al. 2004 flexible correction → mechanism-effectiveness multiplier.

    # Wegener et al. 2004 §2 Flexible Correction Model:
    # When users detect persuasion, they correct for it rather than
    # reverse the response. Correction magnitude scales with
    # (a) detection probability and (b) PK level (high-PK users
    # apply stronger corrections, often overcorrecting).
    # Operationally:
    #     effectiveness_mult = 1.0 - detection_prob × (0.3 + pk × 0.4)
    # PINNED structure (canonical FCM); PILOT_PENDING magnitudes.
    #
    # Pins:
    #   effectiveness_mult ∈ (0, 1]
    #   detection_prob = 0 → effectiveness_mult = 1.0 (no correction)
    #   detection_prob = 1, pk = 1 → effectiveness_mult = 0.3 (max correction)
    """
    correction = detection_prob * (0.3 + pk_level * 0.4)
    return max(0.05, 1.0 - correction)


# =============================================================================
# STRATEGIC AWARENESS ATOM
# =============================================================================


class StrategicAwarenessAtom(BaseAtom):
    """Models the user's Persuasion Knowledge and adapts mechanism selection.

    Computes:
    1. Baseline PK from dispositional NDF (Friestad & Wright 1994 §2)
    2. Effective PK after experience feedback (§3) — FEEDBACK LOOP
    3. Per-mechanism detection probability (§4)
    4. Wegener flexible-correction effectiveness multipliers
    5. Stealth-aware mechanism adjustments

    Output: per-mechanism detection probability + effective stealth scores.
    Downstream MechanismActivation uses these to avoid PKM-triggering
    mechanisms when PK is high.
    """

    ATOM_TYPE = AtomType.STRATEGIC_AWARENESS
    ATOM_NAME = "strategic_awareness"
    TARGET_CONSTRUCT = "persuasion_knowledge"

    REQUIRED_SOURCES = [
        IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
        IntelligenceSourceType.EMPIRICAL_PATTERNS,
    ]

    OPTIONAL_SOURCES = [
        IntelligenceSourceType.MECHANISM_TRAJECTORIES,
        IntelligenceSourceType.GRAPH_EMERGENCE,
    ]

    # B3-LUXY redo metadata
    ATOM_VERSION = "2.0"  # 2.0 = canonical PKM redo with feedback-loop chain

    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        if source == IntelligenceSourceType.EMPIRICAL_PATTERNS:
            return await self._query_resistance_patterns(atom_input)
        return None

    async def _query_resistance_patterns(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query historical resistance patterns for this user/cohort."""
        try:
            mech_output = atom_input.get_upstream("atom_mechanism_activation")
            if mech_output and mech_output.secondary_assessments:
                mechanism_scores = mech_output.secondary_assessments.get(
                    "mechanism_scores", {}
                )
                if mechanism_scores:
                    return IntelligenceEvidence(
                        source_type=IntelligenceSourceType.EMPIRICAL_PATTERNS,
                        construct=self.TARGET_CONSTRUCT,
                        assessment="mechanism_history_available",
                        assessment_value=0.6,
                        confidence=0.5,
                        confidence_semantics=ConfidenceSemantics.DOMAIN_CALIBRATED,
                        strength=EvidenceStrength.MODERATE,
                        reasoning="Historical mechanism data available for resistance estimation",
                    )
        except Exception as e:
            logger.debug(f"Resistance pattern query failed: {e}")
        return None

    # ------------------------------------------------------------------
    # CORE COMPUTATION
    # ------------------------------------------------------------------

    def _compute_pk_state(self, atom_input: AtomInput) -> Dict[str, Any]:
        """Compute baseline + feedback-amplified PK + per-mechanism stealth."""
        ad_context = atom_input.ad_context or {}
        psy = PsychologicalConstructResolver(atom_input)
        psy_dict = psy.as_full_construct_dict() if psy.has_any else {}
        signal_quality = 1.0 if psy.has_any else 0.0

        baseline_pk = _compute_baseline_pk(psy_dict, has_signal=psy.has_any)
        exposure_count = int(ad_context.get("exposure_count", 1) or 1)
        effective_pk = _apply_exposure_feedback(baseline_pk, exposure_count)

        # Per-mechanism detection + correction
        per_mechanism: Dict[str, Dict[str, float]] = {}
        for mechanism, detectability in MECHANISM_DETECTABILITY.items():
            det_prob = _compute_detection_probability(effective_pk, detectability)
            effectiveness_mult = _compute_correction_effect(det_prob, effective_pk)
            stealth = 1.0 - det_prob

            # Wegener overcorrection: very-high-PK users apply global penalty
            if effective_pk > _WEGENER_HIGH_PK_THRESHOLD:
                effectiveness_mult *= _WEGENER_OVERCORRECTION_PENALTY
                stealth *= _WEGENER_OVERCORRECTION_PENALTY

            per_mechanism[mechanism] = {
                "detectability": detectability,
                "detection_probability": det_prob,
                "effectiveness_multiplier": effectiveness_mult,
                "stealth_score": max(0.05, stealth),
            }

        return {
            "baseline_pk": baseline_pk,
            "effective_pk": effective_pk,
            "exposure_count": exposure_count,
            "per_mechanism": per_mechanism,
            "signal_quality": signal_quality,
        }

    def _compute_mechanism_adjustments(
        self,
        pk_state: Dict[str, Any],
    ) -> Dict[str, float]:
        """Convert stealth scores to mechanism weight adjustments.

        Adjustment magnitude scales with PK level — at low PK, all
        mechanisms work fine and adjustments are small. At high PK,
        stealth-vs-detected divergence matters strongly.
        """
        effective_pk = pk_state["effective_pk"]
        per_mechanism = pk_state["per_mechanism"]

        # Magnitude grows with PK above 0.4 baseline
        magnitude = max(0.0, (effective_pk - 0.4)) * 0.5

        adjustments: Dict[str, float] = {}
        for mechanism, m_data in per_mechanism.items():
            stealth = m_data["stealth_score"]
            # Stealth > 0.5 → positive adjustment (mechanism is safe)
            # Stealth < 0.5 → negative adjustment (mechanism will be detected)
            adj = (stealth - 0.5) * magnitude
            adjustments[mechanism] = max(-0.25, min(0.25, adj))

        return adjustments

    # ------------------------------------------------------------------
    # CHAIN ATTESTATION CONSTRUCTION
    # ------------------------------------------------------------------

    def _build_chain_attestation(
        self,
        atom_input: AtomInput,
        pk_state: Dict[str, Any],
        adjustments: Dict[str, float],
    ) -> ChainAttestation:
        """Construct the 5-link feedback-loop ChainAttestation.

        L2 is the novel feedback link — prior exposure history amplifies PK.
        """
        signal_quality = pk_state["signal_quality"]
        from_prior_only = signal_quality < 0.5

        # L1: dispositional signals → baseline_pk
        link1 = ConstructLink(
            source_construct="user_dispositional_signals",
            relation_type=RelationType.MODULATED_BY,
            target_construct="baseline_persuasion_knowledge",
            evidence_value=pk_state["baseline_pk"],
            confidence=0.5 + signal_quality * 0.3,
            citation="Friestad & Wright 1994 §2 (PK as knowledge structure)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
            from_prior_only=from_prior_only,
        )

        # L2: prior_exposure_history → effective_pk (FEEDBACK LOOP)
        link2 = ConstructLink(
            source_construct="prior_exposure_history",
            relation_type=RelationType.AMPLIFIES,
            target_construct="effective_persuasion_knowledge",
            evidence_value=pk_state["effective_pk"],
            confidence=0.65 if pk_state["exposure_count"] > 1 else 0.50,
            citation="Friestad & Wright 1994 §3 (PK is experience-learned)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
            from_prior_only=(pk_state["exposure_count"] <= 1),
        )

        # L3: PK × mechanism_detectability → detection_probability
        avg_detection = sum(
            d["detection_probability"] for d in pk_state["per_mechanism"].values()
        ) / max(1, len(pk_state["per_mechanism"]))
        link3 = ConstructLink(
            source_construct="effective_PK_x_mechanism_detectability",
            relation_type=RelationType.PRODUCES,
            target_construct="detection_probability",
            evidence_value=avg_detection,
            confidence=0.7,
            citation="Friestad & Wright 1994 §4 (mechanism-selective detection)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        )

        # L4: detection_probability → mechanism_effectiveness (Wegener)
        avg_effectiveness = sum(
            d["effectiveness_multiplier"] for d in pk_state["per_mechanism"].values()
        ) / max(1, len(pk_state["per_mechanism"]))
        link4 = ConstructLink(
            source_construct="detection_probability",
            relation_type=RelationType.THREATENS,
            target_construct="mechanism_effectiveness",
            evidence_value=1.0 - avg_effectiveness,  # threat magnitude
            confidence=0.7,
            citation="Wegener et al. 2004 §2 (Flexible Correction Model)",
            calibration_status=CalibrationStatus.PINNED,
        )

        # L5: mechanism_effectiveness → mechanism_adjustments
        adj_magnitude = sum(abs(v) for v in adjustments.values()) / max(
            1, len(adjustments)
        )
        link5 = ConstructLink(
            source_construct="mechanism_effectiveness",
            relation_type=RelationType.MODULATED_BY,
            target_construct="mechanism_adjustments",
            evidence_value=min(1.0, adj_magnitude * 4.0),
            confidence=0.65,
            citation="Friestad & Wright 1994 §5 (coping responses); Wegener et al. 2004",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        )

        chain = [link1, link2, link3, link4, link5]
        chain_link_ids = [link.link_id for link in chain]

        # Per-mechanism AdjustmentEvidence
        adjustment_evidences: List[AdjustmentEvidence] = []
        for mech, adj_value in adjustments.items():
            if abs(adj_value) < 1e-6:
                continue
            m_data = pk_state["per_mechanism"][mech]
            rationale = (
                f"detect_p={m_data['detection_probability']:.2f}, "
                f"stealth={m_data['stealth_score']:.2f}, "
                f"effective_pk={pk_state['effective_pk']:.2f}, "
                f"exposure={pk_state['exposure_count']}"
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

        # Final assessment — effective PK level is the decision-relevant scalar
        final = TypedEvidence(
            construct=self.TARGET_CONSTRUCT,
            value=pk_state["effective_pk"],
            confidence=link2.confidence,
            citation="Friestad & Wright 1994 §2-§5 + Wegener et al. 2004",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        )

        provenance = ChainProvenance(
            atom_id=self.config.atom_id,
            atom_version=self.ATOM_VERSION,
            formula_citations=[
                "Friestad & Wright 1994 §2",
                "Friestad & Wright 1994 §3",
                "Friestad & Wright 1994 §4",
                "Friestad & Wright 1994 §5",
                "Wegener et al. 2004 §2",
                "Campbell & Kirmani 2000",
            ],
            a14_flags_active=[
                "NDF_TO_PKM_COEFFICIENTS_PILOT_PENDING",
                "PKM_DETECTABILITY_LITERATURE_MIDPOINTS_PILOT_PENDING",
                "PKM_EXPOSURE_FEEDBACK_RATE_PILOT_PENDING",
                "WEGENER_OVERCORRECTION_PENALTY_PILOT_PENDING",
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
        """Build atom output: legacy AtomOutput + ChainAttestation."""

        pk_state = self._compute_pk_state(atom_input)
        mechanism_adjustments = self._compute_mechanism_adjustments(pk_state)

        # DSP susceptibility post-multiplier (preserved)
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            mechanism_adjustments = SusceptibilityHelper.apply(
                mechanism_adjustments, dsp
            )

        chain_attestation = self._build_chain_attestation(
            atom_input, pk_state, mechanism_adjustments
        )

        effective_pk = pk_state["effective_pk"]
        if effective_pk > 0.7:
            primary = "high_persuasion_knowledge"
        elif effective_pk > 0.45:
            primary = "moderate_persuasion_knowledge"
        else:
            primary = "low_persuasion_knowledge"

        # Recommend stealthiest mechanisms
        sorted_stealth = sorted(
            pk_state["per_mechanism"].items(),
            key=lambda kv: kv[1]["stealth_score"],
            reverse=True,
        )
        recommended = [m for m, _ in sorted_stealth[:3]]

        confidence = min(0.85, 0.5 + abs(effective_pk - 0.5) * 0.6)
        fusion_result.assessment = primary
        fusion_result.confidence = confidence

        # Legacy stealth_scores dict for backward compat with existing consumers
        legacy_stealth = {
            m: d["stealth_score"] for m, d in pk_state["per_mechanism"].items()
        }
        legacy_detection = {
            m: d["detection_probability"]
            for m, d in pk_state["per_mechanism"].items()
        }

        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary,
            secondary_assessments={
                "pk_level": effective_pk,
                "baseline_pk": pk_state["baseline_pk"],
                "exposure_count": pk_state["exposure_count"],
                "detection_probabilities": legacy_detection,
                "stealth_scores": legacy_stealth,
                "mechanism_adjustments": mechanism_adjustments,
                "recommended_approach": (
                    "subtle_mechanisms" if effective_pk > 0.6 else "standard"
                ),
                "atom_version": self.ATOM_VERSION,
            },
            recommended_mechanisms=recommended,
            mechanism_weights={m: legacy_stealth[m] for m in recommended},
            inferred_states={
                "persuasion_knowledge": effective_pk,
                **{f"stealth_{k}": v for k, v in list(legacy_stealth.items())[:5]},
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
            chain_attestation=chain_attestation,
        )
