# =============================================================================
# ADAM Mimetic Desire Atom — Canonical Girardian Redo (B3-LUXY Phase 1)
# Location: adam/atoms/core/mimetic_desire_atom.py
# =============================================================================

"""
MIMETIC DESIRE ATOM (canonical, B3-LUXY Phase 1 atom 3)
=========================================================

Models imitative desire via the canonical Girardian framework: Subject
(S) wants Object (O) because Model (M) wants O — the triangular structure
of mediated desire (Girard 1961 §1). Distinguishes external mediation
(socially distant model, no rivalry) from internal mediation (socially
close model, rivalry possible per Girard 1972 §1). Computes per-decision
mimetic susceptibility, optimal model selection, mediation classification,
and rivalry risk → mechanism adjustments.

Discipline rule compliance (see `memory/feedback_atom_redo_discipline.md`):
- (a) Canonical formulas in code with `paper:section` citations: see
  `_classify_mediation_type` (Girard 1961 §2), `_compute_rivalry_probability`
  (Girard 1972 §1), formula citations on every chain link.
- (b) Regression tests pinning published anchors: see
  `tests/unit/test_mimetic_desire_canonical.py`.
- (c) Calibration-pending flags on placeholder constants: see A14 flags
  in this module's docstring and inline at each PILOT_PENDING value.
- (d) Multi-source convergence ChainAttestation emitted (5 links;
  different chain shape from atoms 1-2 — stress-tests the schema for
  the post-atom-3 lock review).

ACADEMIC FOUNDATION
-------------------
- Girard (1961) §1: *Deceit, Desire, and the Novel*. Foundational —
  desire is not intrinsic but mediated; the triangular S-M-O structure
  is the canonical model.
- Girard (1961) §2: distinguishes external mediation (model socially
  distant; pure imitation) from internal mediation (model socially
  close; rivalry possible).
- Girard (1972) §1: *Violence and the Sacred*. Internal mediation
  produces mimetic rivalry — when subject and model converge on the
  same object, they become obstacles to each other and the relationship
  escalates toward conflict.
- Oughourlian (2010): *The Genesis of Desire*. Clinical operationalization
  of Girardian theory; demonstrates mimetic desire's role in psychopathology.
- Gallese (2001): mirror neuron substrate for action understanding and
  imitation; the neurobiological basis of mimetic desire.
- Belk (1988): *Possessions and the Extended Self*. Objects acquire
  meaning through their owners; mimetic desire works via this — wanting
  object X to be like person Y who owns X.
- Tarde (1890); Bandura (1977): historical / cognitive precedents for
  imitation as a primary social-learning mechanism (cited but not
  load-bearing for this atom).

ACTIVE A14 CALIBRATION-PENDING FLAGS
-------------------------------------
- A14: MIMETIC_SUSCEPTIBILITY_COEFFICIENTS_PILOT_PENDING — the per-NDF-
  dim coefficients in `_compute_susceptibility` are theoretically
  motivated (high social_calibration → mimetic; high cognitive_engagement
  → less mimetic) but the magnitudes are literature midpoints. Retire
  when LUXY pilot accumulates ≥150 decisions with measured mimetic
  outcome distributions.
- A14: MODEL_TYPE_PARAMETERS_PILOT_PENDING — `MODEL_TYPES` per-model
  (effectiveness_base, ndf_fit, risk_of_rivalry) are literature midpoints
  synthesized from Girard 1961/1972 + clinical observations from
  Oughourlian 2010. Retire when pilot accumulates ≥100 decisions per
  model-type with measured conversion + rivalry-signal distributions.
- A14: MIMETIC_MECHANISM_ADJUSTMENT_MAGNITUDES_PILOT_PENDING — the
  `MIMETIC_MECHANISMS` per-level adjustment magnitudes are literature-
  midpoint estimates. Retire when pilot accumulates ≥200 decisions with
  per-mechanism mimetic-segmented outcomes.
- A14: RIVALRY_THRESHOLD_INTERNAL_MEDIATION_PILOT_PENDING — the
  `_INTERNAL_MEDIATION_THRESHOLD` (proximity above which rivalry risk
  fires) is a literature midpoint. Girard does not specify a numerical
  threshold; we use 0.4 (proximity scale) as the operational pin.
  Retire when pilot data calibrates the proximity-vs-rivalry-event
  relationship.

CHAIN SHAPE
-----------
Multi-source convergence (5 links; different from atom 2's temporal
shape and atom 1's linear-trait-to-state shape). Two convergence points
(L2: trait + context → model_selection; L4: mediation + susceptibility
→ rivalry_probability). This shape stress-tests the schema for the
post-atom-3 lock review.

  L1: (user_dispositional_signals) -[MODULATED_BY]-> (mimetic_susceptibility)
      — Girard 1961 §1 + dispositional NDF derivation; PILOT_PENDING.
  L2: (mimetic_susceptibility × candidate_models) -[MODULATED_BY]-> (selected_model)
      — Multi-source convergence: trait + Girardian model-type fit.
      Belk 1988 (possessions as identity); Gallese 2001 (imitation
      neural substrate); PILOT_PENDING magnitudes.
  L3: (selected_model) -[PRODUCES]-> (mediation_type)
      — Girard 1961 §2 (internal vs external mediation classification);
      PINNED structure, PILOT_PENDING threshold.
  L4: (mediation_type × susceptibility) -[THREATENS]-> (rivalry_probability)
      — Multi-source convergence: Girard 1972 §1 rivalry escalation;
      internal mediation + high susceptibility → rivalry; PINNED structure.
  L5: (rivalry_probability) -[MODULATED_BY]-> (mechanism_adjustments)
      — rivalry-aware suppression of competition-amplifying mechanisms;
      PILOT_PENDING magnitudes.
"""

import logging
from typing import Any, Dict, List, Optional

from adam.atoms.core.base import BaseAtom
from adam.atoms.core.construct_resolver import PsychologicalConstructResolver
from adam.atoms.core.dsp_integration import (
    DSPDataAccessor,
    EmpiricalEffectivenessHelper,
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
# A14: MODEL_TYPE_PARAMETERS_PILOT_PENDING
# =============================================================================
# Per-model parameters (effectiveness_base, ndf_fit, risk_of_rivalry,
# proximity). Synthesized from:
#   Girard 1961 §2 (internal vs external mediation distinction)
#   Girard 1972 §1 (rivalry escalation in internal mediation)
#   Oughourlian 2010 (clinical observations)
#
# `proximity` ∈ [0, 1]: 0 = maximally distant (celebrity), 1 = maximally
# close (in-group peer). The Girardian internal/external boundary is at
# `_INTERNAL_MEDIATION_THRESHOLD`.
#
# RETIRE: when pilot accumulates ≥100 decisions per model-type with
# measured conversion + rivalry-signal distributions.
# =============================================================================
MODEL_TYPES: Dict[str, Dict[str, Any]] = {
    "aspirational_peer": {
        "description": "Someone slightly above you in the hierarchy you care about",
        "effectiveness_base": 0.80,
        "proximity": 0.65,  # Internal mediation territory
        "ndf_fit": {"status_sensitivity": 0.30, "social_calibration": 0.20},
        "risk_of_rivalry": 0.30,  # Girard 1972 §1: close enough to compete with
    },
    "distant_celebrity": {
        "description": "Famous person far above in social hierarchy",
        "effectiveness_base": 0.50,
        "proximity": 0.10,  # External mediation: too far for rivalry
        "ndf_fit": {"status_sensitivity": 0.40, "arousal_seeking": 0.10},
        "risk_of_rivalry": 0.05,
    },
    "expert_authority": {
        "description": "Domain expert whose judgment you trust",
        "effectiveness_base": 0.70,
        "proximity": 0.30,  # Boundary case — domain-defined external
        "ndf_fit": {"cognitive_engagement": 0.30, "uncertainty_tolerance": -0.20},
        "risk_of_rivalry": 0.10,
    },
    "in_group_member": {
        "description": "Someone in your social group or identity category",
        "effectiveness_base": 0.75,
        "proximity": 0.85,  # Maximum internal mediation (Girard 1972 §1)
        "ndf_fit": {"social_calibration": 0.40, "approach_avoidance": 0.10},
        "risk_of_rivalry": 0.40,  # Highest rivalry risk
    },
    "anonymous_mass": {
        "description": "Large number of unnamed others",
        "effectiveness_base": 0.40,
        "proximity": 0.20,  # External: no identifiable model to rival
        "ndf_fit": {"uncertainty_tolerance": -0.20, "social_calibration": 0.10},
        "risk_of_rivalry": 0.0,
    },
}


# =============================================================================
# A14: RIVALRY_THRESHOLD_INTERNAL_MEDIATION_PILOT_PENDING
# =============================================================================
# Proximity threshold above which Girard 1961 §2 internal-mediation
# applies and Girard 1972 §1 rivalry risk fires. Girard does not specify
# a numerical threshold; 0.4 is the operational pin synthesized from his
# distinction examples (peers and in-group → internal; celebrities and
# masses → external).
#
# RETIRE: when pilot data calibrates the proximity-vs-rivalry-event
# relationship at scale.
# =============================================================================
_INTERNAL_MEDIATION_THRESHOLD = 0.4


# =============================================================================
# A14: MIMETIC_MECHANISM_ADJUSTMENT_MAGNITUDES_PILOT_PENDING
# =============================================================================
# Per-level mechanism adjustments. The MECHANISMS targeted are
# theoretically motivated:
#   high_mimetic   → boost mimetic_desire, identity_construction (Belk 1988
#                    via possessions-as-extended-self)
#   moderate       → mild boosts to imitation-adjacent mechanisms
#   low            → boost mechanisms that don't depend on imitation
#                    (authority, commitment, anchoring); suppress mimetic
#
# Magnitudes are literature midpoints. Retire when pilot accumulates
# ≥200 decisions with per-mechanism mimetic-segmented outcomes.
# =============================================================================
MIMETIC_MECHANISMS: Dict[str, Dict[str, float]] = {
    "high_mimetic": {
        "mimetic_desire": 0.25,
        "identity_construction": 0.15,
        "social_proof": 0.10,
        "scarcity": 0.10,
    },
    "moderate_mimetic": {
        "social_proof": 0.15,
        "mimetic_desire": 0.10,
        "identity_construction": 0.10,
    },
    "low_mimetic": {
        "authority": 0.10,
        "commitment": 0.10,
        "anchoring": 0.05,
        "mimetic_desire": -0.10,
    },
}


# =============================================================================
# CANONICAL FORMULA HELPERS
# =============================================================================


def _classify_mediation_type(proximity: float) -> str:
    """Internal vs external mediation per Girard 1961 §2.

    # Girard 1961 §2:
    #   External mediation: model is socially distant (celebrity, character).
    #     The subject can imitate without becoming the model's rival because
    #     the gulf is unbridgeable. No rivalry.
    #   Internal mediation: model is socially close (peer, in-group). The
    #     gulf is bridgeable; the subject and model can compete for the
    #     same object → rivalry possible (Girard 1972 §1).
    #
    # Pin: proximity > _INTERNAL_MEDIATION_THRESHOLD → "internal"
    #      else                                       → "external"
    #
    # PINNED structure; threshold magnitude PILOT_PENDING.
    """
    if proximity > _INTERNAL_MEDIATION_THRESHOLD:
        return "internal"
    return "external"


def _compute_rivalry_probability(
    mediation_type: str,
    susceptibility: float,
    risk_of_rivalry_base: float,
) -> float:
    """Rivalry probability per Girard 1972 §1.

    # Girard 1972 §1:
    #   External mediation → rivalry ≈ 0 (the gulf prevents competition).
    #   Internal mediation → rivalry rises with both subject's
    #     mimetic susceptibility AND the model's rivalry-baseline
    #     (in-group members are highest; aspirational peers are second).
    #
    # Operational form (literature midpoint magnitudes):
    #   external:  P(rivalry) = 0.5 × risk_of_rivalry_base
    #              (small baseline only; no susceptibility amplification)
    #   internal:  P(rivalry) = risk_of_rivalry_base × (0.5 + susceptibility × 0.7)
    #
    # Pins (anchored in tests):
    #   external mediation always produces lower rivalry than internal
    #     for the same risk_of_rivalry_base and susceptibility.
    #   internal: monotonic in susceptibility for fixed risk_of_rivalry_base.
    #   bounded ∈ [0, 1].
    #
    # PINNED structure; multipliers PILOT_PENDING.
    """
    if mediation_type == "external":
        return max(0.0, min(1.0, 0.5 * risk_of_rivalry_base))
    # internal mediation
    return max(
        0.0,
        min(1.0, risk_of_rivalry_base * (0.5 + susceptibility * 0.7)),
    )


# =============================================================================
# MIMETIC DESIRE ATOM
# =============================================================================


class MimeticDesireAtom(BaseAtom):
    """Models imitative desire patterns via canonical Girardian theory.

    Computes:
    1. Mimetic susceptibility (NDF-derived; PILOT_PENDING)
    2. Optimal model type via Girardian S-M-O matching
    3. Mediation classification (Girard 1961 §2 internal vs external)
    4. Rivalry probability (Girard 1972 §1)
    5. Mechanism adjustments (rivalry-aware)

    Distinction from `social_proof` mechanism:
    - social_proof: "many people chose this" (quantity / consensus)
    - mimetic_desire: "THAT person chose this" (quality / model)
    """

    ATOM_TYPE = AtomType.MIMETIC_DESIRE
    ATOM_NAME = "mimetic_desire_assessment"
    TARGET_CONSTRUCT = "mimetic_susceptibility"

    REQUIRED_SOURCES = [
        IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
    ]

    OPTIONAL_SOURCES = [
        IntelligenceSourceType.EMPIRICAL_PATTERNS,
        IntelligenceSourceType.GRAPH_EMERGENCE,
        IntelligenceSourceType.MECHANISM_TRAJECTORIES,
    ]

    # B3-LUXY redo metadata
    ATOM_VERSION = "2.0"  # 2.0 = canonical Girardian redo with citations + chain emission

    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        return None

    # ------------------------------------------------------------------
    # CORE COMPUTATION
    # ------------------------------------------------------------------

    def _compute_susceptibility(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, Any]:
        """Compute mimetic susceptibility from dispositional NDF dimensions.

        # A14: MIMETIC_SUSCEPTIBILITY_COEFFICIENTS_PILOT_PENDING
        # Direction (sign) of each component is theoretically motivated:
        #   social_calibration  → mimetic    (Girard 1961: imitation is social)
        #   status_sensitivity  → mimetic    (Belk 1988: status drives wanting)
        #   cognitive_engagement→ less mimetic (deliberation defeats imitation)
        #   uncertainty_tolerance→less mimetic (independent thinkers resist)
        #   approach_avoidance  → mildly mimetic (engagement amplifies wanting)
        # Magnitudes are literature midpoints.
        """
        psy = PsychologicalConstructResolver(atom_input)
        signal_quality = 1.0 if psy.has_any else 0.0

        susceptibility = 0.5  # baseline (no signal)

        if psy.has_any:
            sc = psy.social_calibration
            ss = psy.status_sensitivity
            ce = psy.cognitive_engagement
            ut = psy.uncertainty_tolerance
            aa = psy.approach_avoidance

            # Additive deviation from 0.5 — literature midpoint magnitudes
            susceptibility = (
                0.25
                + sc * 0.25
                + ss * 0.20
                + (1.0 - ce) * 0.15
                + (1.0 - ut) * 0.10
                + aa * 0.05
            )

        susceptibility = max(0.05, min(0.95, susceptibility))

        if susceptibility > 0.65:
            level = "high_mimetic"
        elif susceptibility > 0.35:
            level = "moderate_mimetic"
        else:
            level = "low_mimetic"

        return {
            "susceptibility": susceptibility,
            "level": level,
            "signal_quality": signal_quality,
        }

    def _select_model(
        self,
        atom_input: AtomInput,
        susceptibility_profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Select optimal Girardian model (S-M-O triangle's M).

        # Girard 1961 §1: the model-object pair drives the subject's
        # desire. Choosing the right model is the first-order decision —
        # not the right object features.
        # Belk 1988: object's identity-conferring power flows from the
        # model who owns/endorses it.
        # Gallese 2001: mirror-neuron substrate makes model selection
        # neurally efficient — high social_calibration users compute
        # this faster, but all users compute it.
        """
        psy = PsychologicalConstructResolver(atom_input)
        psy_dict = psy.as_full_construct_dict() if psy.has_any else {}

        susceptibility = susceptibility_profile["susceptibility"]
        model_scores: Dict[str, float] = {}

        for model_id, model_def in MODEL_TYPES.items():
            score = model_def["effectiveness_base"]

            # Trait-fit: NDF dims align with model's effective triggers
            for dim, weight in model_def["ndf_fit"].items():
                val = psy_dict.get(dim, 0.5)
                score += (val - 0.5) * weight

            # Rivalry penalty for high-mimetic users + high-rivalry models
            # (Girard 1972 §1: internal mediation produces rivalry that
            # converts mimetic desire into resentment).
            if susceptibility > 0.6:
                score -= model_def["risk_of_rivalry"] * 0.20

            model_scores[model_id] = max(0.10, min(0.95, score))

        best_model_id = max(model_scores, key=model_scores.get)
        best_model_def = MODEL_TYPES[best_model_id]
        mediation_type = _classify_mediation_type(best_model_def["proximity"])
        rivalry_prob = _compute_rivalry_probability(
            mediation_type=mediation_type,
            susceptibility=susceptibility,
            risk_of_rivalry_base=best_model_def["risk_of_rivalry"],
        )

        return {
            "optimal_model": best_model_id,
            "model_scores": model_scores,
            "proximity": best_model_def["proximity"],
            "mediation_type": mediation_type,
            "rivalry_probability": rivalry_prob,
        }

    def _compute_mechanism_adjustments(
        self,
        susceptibility_profile: Dict[str, Any],
        model_selection: Dict[str, Any],
    ) -> Dict[str, float]:
        """Convert mimetic analysis to mechanism adjustments.

        # Rivalry-aware suppression (Girard 1972 §1):
        # When rivalry probability is high, mechanisms that AMPLIFY
        # competition (scarcity in particular) become counterproductive
        # — they convert the model→object aspiration into
        # subject→model rivalry. Boost unity instead, which channels
        # the imitation impulse toward shared identity rather than
        # competition.
        """
        level = susceptibility_profile["level"]
        adjustments: Dict[str, float] = dict(
            MIMETIC_MECHANISMS.get(level, MIMETIC_MECHANISMS["moderate_mimetic"])
        )

        model = model_selection["optimal_model"]
        if model == "expert_authority":
            adjustments["authority"] = adjustments.get("authority", 0.0) + 0.10
        elif model == "in_group_member":
            adjustments["unity"] = adjustments.get("unity", 0.0) + 0.15
        elif model == "aspirational_peer":
            adjustments["identity_construction"] = (
                adjustments.get("identity_construction", 0.0) + 0.10
            )

        # Rivalry mitigation (Girard 1972 §1)
        if model_selection["rivalry_probability"] > 0.30:
            adjustments["unity"] = adjustments.get("unity", 0.0) + 0.10
            adjustments["scarcity"] = adjustments.get("scarcity", 0.0) - 0.10

        return adjustments

    # ------------------------------------------------------------------
    # CHAIN ATTESTATION CONSTRUCTION
    # ------------------------------------------------------------------

    def _build_chain_attestation(
        self,
        atom_input: AtomInput,
        susceptibility_profile: Dict[str, Any],
        model_selection: Dict[str, Any],
        adjustments: Dict[str, float],
    ) -> ChainAttestation:
        """Construct the 5-link multi-source-convergence ChainAttestation.

        Convergence points:
        - L2: trait (susceptibility) + context (candidate models) → selected_model
        - L4: mediation_type + susceptibility → rivalry_probability
        """
        signal_quality = susceptibility_profile["signal_quality"]
        from_prior_only = signal_quality < 0.5
        susceptibility = susceptibility_profile["susceptibility"]

        # L1: dispositional signals → mimetic_susceptibility
        link1 = ConstructLink(
            source_construct="user_dispositional_signals",
            relation_type=RelationType.MODULATED_BY,
            target_construct="mimetic_susceptibility",
            evidence_value=susceptibility,
            confidence=0.5 + signal_quality * 0.3,
            citation="Girard 1961 §1 (triangular desire); Belk 1988 (extended self)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
            from_prior_only=from_prior_only,
        )

        # L2: susceptibility × candidate_models → selected_model
        # Multi-source convergence point #1: trait + Girardian model-fit
        best_score = max(model_selection["model_scores"].values())
        link2 = ConstructLink(
            source_construct="susceptibility_x_candidate_models",
            relation_type=RelationType.MODULATED_BY,
            target_construct="selected_model",
            evidence_value=best_score,
            confidence=0.65,
            citation="Girard 1961 §1; Gallese 2001 (mirror-neuron substrate)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        )

        # L3: selected_model → mediation_type
        # Girard 1961 §2 internal/external classification
        mediation_type = model_selection["mediation_type"]
        # Encode mediation type as evidence_value: external = 0.0, internal = 1.0
        mediation_value = 1.0 if mediation_type == "internal" else 0.0
        link3 = ConstructLink(
            source_construct="selected_model",
            relation_type=RelationType.PRODUCES,
            target_construct=f"mediation_type_{mediation_type}",
            evidence_value=mediation_value,
            confidence=0.75,
            citation="Girard 1961 §2 (internal vs external mediation)",
            calibration_status=CalibrationStatus.PINNED,
        )

        # L4: mediation_type × susceptibility → rivalry_probability
        # Multi-source convergence point #2: Girard 1972 §1
        link4 = ConstructLink(
            source_construct="mediation_type_x_susceptibility",
            relation_type=RelationType.THREATENS,
            target_construct="rivalry_probability",
            evidence_value=model_selection["rivalry_probability"],
            confidence=0.7,
            citation="Girard 1972 §1 (rivalry escalation in internal mediation)",
            calibration_status=CalibrationStatus.PINNED,
        )

        # L5: rivalry_probability → mechanism_adjustments
        # Net mechanism-adjustment magnitude as the chain-level signal
        adj_magnitude = sum(abs(v) for v in adjustments.values()) / max(
            1, len(adjustments)
        )
        link5 = ConstructLink(
            source_construct="rivalry_probability",
            relation_type=RelationType.MODULATED_BY,
            target_construct="mechanism_adjustments",
            evidence_value=min(1.0, adj_magnitude * 5.0),  # scale for [0,1]
            confidence=0.65,
            citation="Girard 1972 §1 (rivalry → mechanism suppression)",
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
                f"susceptibility={susceptibility:.2f}, "
                f"model={model_selection['optimal_model']}, "
                f"mediation={mediation_type}, "
                f"rivalry_p={model_selection['rivalry_probability']:.2f}"
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

        # Final assessment — susceptibility is the load-bearing scalar
        final = TypedEvidence(
            construct=self.TARGET_CONSTRUCT,
            value=susceptibility,
            confidence=link1.confidence,
            citation="Girard 1961 §1 + 1972 §1 (composite)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        )

        provenance = ChainProvenance(
            atom_id=self.config.atom_id,
            atom_version=self.ATOM_VERSION,
            formula_citations=[
                "Girard 1961 §1",
                "Girard 1961 §2",
                "Girard 1972 §1",
                "Belk 1988",
                "Gallese 2001",
                "Oughourlian 2010",
            ],
            a14_flags_active=[
                "MIMETIC_SUSCEPTIBILITY_COEFFICIENTS_PILOT_PENDING",
                "MODEL_TYPE_PARAMETERS_PILOT_PENDING",
                "MIMETIC_MECHANISM_ADJUSTMENT_MAGNITUDES_PILOT_PENDING",
                "RIVALRY_THRESHOLD_INTERNAL_MEDIATION_PILOT_PENDING",
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

        susceptibility_profile = self._compute_susceptibility(atom_input)
        model_selection = self._select_model(atom_input, susceptibility_profile)
        adjustments = self._compute_mechanism_adjustments(
            susceptibility_profile, model_selection
        )

        # DSP empirical effectiveness modulation (preserved)
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            adjustments = EmpiricalEffectivenessHelper.apply(adjustments, dsp)

        chain_attestation = self._build_chain_attestation(
            atom_input, susceptibility_profile, model_selection, adjustments
        )

        primary = susceptibility_profile["level"]
        sorted_mechs = sorted(adjustments.items(), key=lambda x: x[1], reverse=True)
        recommended = [m for m, s in sorted_mechs[:3] if s > 0]

        confidence = min(
            0.85, 0.4 + abs(susceptibility_profile["susceptibility"] - 0.5) * 0.7
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
                "mimetic_profile": {
                    "susceptibility": susceptibility_profile["susceptibility"],
                    "level": susceptibility_profile["level"],
                    "signal_quality": susceptibility_profile["signal_quality"],
                },
                "model_selection": model_selection,
                "mechanism_adjustments": adjustments,
                "atom_version": self.ATOM_VERSION,
            },
            recommended_mechanisms=recommended,
            mechanism_weights={
                m: max(0.1, 0.5 + adjustments.get(m, 0.0)) for m in recommended
            } if recommended else {"social_proof": 0.5},
            inferred_states={
                "mimetic_susceptibility": susceptibility_profile["susceptibility"],
                "rivalry_probability": model_selection["rivalry_probability"],
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
            chain_attestation=chain_attestation,
        )
