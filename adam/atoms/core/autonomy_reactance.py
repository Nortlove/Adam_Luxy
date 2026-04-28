# =============================================================================
# ADAM Autonomy Reactance Atom — Canonical Brehm Redo (B3-LUXY Phase 0)
# Location: adam/atoms/core/autonomy_reactance.py
# =============================================================================

"""
AUTONOMY REACTANCE ATOM (canonical, B3-LUXY Phase 0)
=====================================================

Computes per-decision reactance magnitude using the canonical Brehm
multiplicative formula (Brehm 1966; Brehm & Brehm 1981 §3) and per-
mechanism backfire probability via the Wicklund 1974 §6 boomerang
sigmoid. Emits a `ChainAttestation` with five inferential links, each
grounded in a paper:section citation and tagged with calibration status.

Discipline rule compliance (see `memory/feedback_atom_redo_discipline.md`):
- (a) Canonical formulas in code with `paper:section` citations: see
  `_compute_reactance_magnitude_brehm`, `_compute_backfire_probability`.
- (b) Regression tests pinning published anchors: see
  `tests/unit/test_autonomy_reactance_canonical.py`.
- (c) Calibration-pending flags on placeholder constants: see A14 flags
  in this module's docstring and inline at each PILOT_PENDING value.
- (d) The atom emits a typed `ChainAttestation`; this is the structural
  difference between this redo and the prior wrapper.

ACADEMIC FOUNDATION
-------------------
- Brehm (1966): A Theory of Psychological Reactance. Foundational; defines
  reactance as a motivational state directed toward restoration of a
  threatened or eliminated freedom.
- Brehm & Brehm (1981) §3: Psychological Reactance: A Theory of Freedom
  and Control. Multiplicative interaction R = f(I × M × P), where I =
  importance of the threatened freedom, M = magnitude of threat, P =
  implication for further freedoms.
- Wicklund (1974) §6: Freedom and Reactance. The boomerang effect — when
  reactance exceeds threshold, the persuasion response REVERSES, producing
  the opposite of the intended behavior.
- Hong & Page (1989); Hong (1992): Hong Psychological Reactance Scale
  (HPRS) — the canonical trait-reactance measurement instrument. Our
  proxy from NDF dimensions is PILOT_PENDING; HPRS itself is the locked
  reference.
- Friestad & Wright (1994): Persuasion Knowledge Model (PKM). Persuasion
  knowledge amplifies the cognitive component of reactance — users with
  high PK detect manipulation tactics more readily.
- Steindl, Jonas, Sittenthaler, Traut-Mattausch & Greenberg (2015) §3-4:
  meta-analytic confirmation of the intertwined model — reactance is
  jointly mediated by anger (affective) and negative cognitions
  (cognitive), correlated r ≈ 0.7.
- Miron & Brehm (2006): Reactance Theory — 40 Years Later. Repeat-
  exposure amplification: P factor in I × M × P > 1.0 when threats
  follow a pattern.
- Deci & Ryan (1985): Self-Determination Theory. Autonomy as a fundamental
  psychological need; provides the importance-of-freedom (I) anchoring.

ACTIVE A14 CALIBRATION-PENDING FLAGS
-------------------------------------
- A14: REACTANCE_THRESHOLD_COEFFICIENTS_PILOT_PENDING — HPRS proxy
  derivation from NDF dimensions; literature-midpoint coefficients.
  Retire when LUXY pilot accumulates ≥200 backfire events with
  reactance-threshold predictions.
- A14: MECHANISM_COERCIVENESS_LITERATURE_MIDPOINTS_PILOT_PENDING — the
  per-mechanism coerciveness magnitudes in `MECHANISM_COERCIVENESS`
  dict are literature midpoints. Retire when pilot accumulates ≥50
  conversions per mechanism with reactance-attenuated scoring.
- A14: BACKFIRE_SIGMOID_STEEPNESS_PILOT_PENDING — the sigmoid steepness
  k=5.0 in `_compute_backfire_probability` is a literature convention.
  Retire when pilot calibrates k against observed backfire-event
  distribution.
- A14: PROPAGATION_FACTOR_REPEAT_EXPOSURE_PILOT_PENDING — the P
  amplification factor for repeat exposures is a literature midpoint.
  Retire when pilot accumulates ≥100 multi-exposure decisions with
  measured backfire variance.

CHAIN SHAPE
-----------
This atom emits a 5-link chain (Phase 0 simplest shape). Other atoms
will reveal multi-step temporal (`persuasion_pharmacology`) and multi-
source convergence (`mimetic_desire_atom`) shapes; the schema will
refactor after atom 3.

  L1: (user_dispositional_signals) -[MODULATED_BY]-> (reactance_proneness)
      — HPRS proxy derivation; PILOT_PENDING.
  L2: (reactance_proneness)        -[MODULATED_BY]-> (effective_threshold)
      — proneness-to-threshold inversion; PINNED.
  L3: (mechanism_coerciveness)     -[THREATENS]->    (autonomy_freedom)
      — per-mechanism freedom-threat operationalization; PILOT_PENDING
      coerciveness magnitudes.
  L4: (freedom_threat × persuasion_knowledge) -[AMPLIFIES]-> (reactance_magnitude)
      — Brehm I × M × P × PKM amplification; PINNED structure.
  L5: (reactance_magnitude > threshold) -[PRODUCES]-> (backfire_probability)
      — Wicklund boomerang sigmoid; PILOT_PENDING steepness.
"""

import logging
import math
from typing import Dict, List, Optional, Tuple

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
# A14: MECHANISM_COERCIVENESS_LITERATURE_MIDPOINTS_PILOT_PENDING
# =============================================================================
# Per-mechanism coerciveness ∈ [0, 1] — degree to which each mechanism
# is perceived to threaten user autonomy. Higher = stronger M (magnitude
# of threat) in Brehm's I × M × P formulation.
#
# These values are literature midpoints synthesized from:
#   Brehm 1966 §1.2 (overt commands as maximal threat)
#   Cialdini 2001 (scarcity/urgency operationalizations)
#   Petty & Cacioppo 1986 (peripheral vs central route — peripheral
#     mechanisms perceived as less threatening when received passively)
#
# RETIRE: when LUXY pilot accumulates ≥50 conversions per mechanism with
# reactance-attenuated scoring; replace with empirically-derived
# distributions per (mechanism, archetype, page-context) cell.
# =============================================================================
MECHANISM_COERCIVENESS: Dict[str, float] = {
    # High-coerciveness mechanisms (>0.7) — direct freedom threats
    "scarcity":              0.85,  # "Only 2 left!" — Brehm 1966 §3 explicit limitation
    "urgency":               0.90,  # "Buy NOW!" — Brehm 1966 §3 maximal coercion
    "attention_dynamics":    0.60,  # Salience manipulation
    # Moderate-coerciveness mechanisms (0.3–0.7) — indirect freedom pressure
    "temporal_construal":    0.50,  # Time framing
    "anchoring":             0.40,  # Price anchoring
    "regulatory_focus":      0.45,  # Gain/loss framing (loss more coercive)
    "social_proof":          0.35,  # "Everyone does it" — mild coercion
    "authority":             0.50,  # "Experts say"
    "commitment":            0.45,  # Foot-in-door
    "mimetic_desire":        0.30,  # Model-based — low coercion
    # Low-coerciveness mechanisms (<0.3) — autonomy-preserving
    "identity_construction": 0.20,  # Self-concept reflection
    "reciprocity":           0.25,  # Gift-giving
    "unity":                 0.15,  # Shared identity / belonging
    "storytelling":          0.10,  # Narrative — almost zero
    "embodied_cognition":    0.10,  # Sensory experience
}


# =============================================================================
# A14: PROPAGATION_FACTOR_REPEAT_EXPOSURE_PILOT_PENDING
# =============================================================================
# The P factor in Brehm's I × M × P amplifies reactance when the threat
# pattern suggests further threats are coming. Operationally, repeat
# exposure to the same coercive mechanism signals a pattern.
# Miron & Brehm (2006) §4 documents this amplification but does not
# specify a magnitude. Below: literature-midpoint magnitudes.
#
# RETIRE: when pilot accumulates ≥100 multi-exposure decisions with
# measured backfire variance.
# =============================================================================
_P_BASELINE = 1.0  # No prior pattern — neutral
_P_REPEAT_AMPLIFIER_PER_EXPOSURE = 0.10  # Each additional exposure +10%
_P_MAX = 1.5  # Saturation


# =============================================================================
# A14: BACKFIRE_SIGMOID_STEEPNESS_PILOT_PENDING
# =============================================================================
# Wicklund (1974) §6 documents the boomerang effect (response reversal
# above threshold) but does not specify the transition steepness.
# k = 5.0 is a smooth-but-decisive sigmoid (P(R=threshold)=0.5,
# P(R=threshold+0.2)≈0.73, P(R=threshold+0.4)≈0.88).
#
# RETIRE: when pilot calibrates k against observed backfire-event
# distribution at varying reactance levels.
# =============================================================================
_BACKFIRE_SIGMOID_K = 5.0


# =============================================================================
# A14: REACTANCE_THRESHOLD_COEFFICIENTS_PILOT_PENDING
# =============================================================================
# HPRS (Hong & Page 1989) is the canonical trait-reactance instrument
# and is NOT measured here. The function below derives a proxy for
# user proneness to reactance from available NDF dimensions. The
# coefficient signs are theoretically motivated:
#   cognitive_engagement (CE) → high CE detects manipulation → ↑ proneness
#   approach_avoidance (AA)   → high AA tolerates pressure → ↓ proneness
#   uncertainty_tolerance (UT) → high UT tolerates pressure → ↓ proneness
#   arousal_seeking (AS)      → thrill-seekers handle pressure → ↓ proneness
# The MAGNITUDES are literature-midpoint estimates. The proxy is not
# HPRS; it is a placeholder pending HPRS-instrument integration or
# pilot-data calibration.
#
# RETIRE: when LUXY pilot accumulates ≥200 backfire events with
# reactance-threshold predictions, OR when HPRS-instrument data is
# integrated for a sample of users.
# =============================================================================


def _compute_reactance_proneness_proxy(
    cognitive_engagement: float,
    approach_avoidance: float,
    uncertainty_tolerance: float,
    arousal_seeking: float,
) -> float:
    """Derive a proxy for HPRS-style trait reactance proneness from NDF dims.

    Returns proneness ∈ [0.1, 0.9]: higher = more sensitive to coercion.
    Citation: Hong & Page 1989 (HPRS instrument); proxy derivation
    PILOT_PENDING.

    Structure: multiplicative around 0.5 baseline. Each NDF dim
    contributes a factor in [0.7, 1.3]; product clamped to [0.1, 0.9].
    The multiplicative structure (rather than the prior additive form)
    is theoretically motivated — Brehm's framework treats reactance
    components as interacting, not summing.
    """
    # Multiplicative factors, each centered on 1.0 (no effect at 0.5
    # input, ±0.3 range across [0,1] input range).
    f_ce = 0.7 + cognitive_engagement * 0.6  # high CE → ↑ proneness
    f_aa = 1.3 - approach_avoidance * 0.6     # high AA → ↓ proneness
    f_ut = 1.3 - uncertainty_tolerance * 0.6  # high UT → ↓ proneness
    f_as = 1.3 - arousal_seeking * 0.6        # high AS → ↓ proneness

    proneness = 0.5 * f_ce * f_aa * f_ut * f_as
    return max(0.1, min(0.9, proneness))


def _compute_effective_threshold(proneness: float) -> float:
    """Map reactance proneness to the effective tolerance threshold.

    Brehm & Brehm 1981 §4 (trait-state relationship): high trait
    proneness → low situational threshold (small threats trigger
    reactance). Inverse relationship.

    Returns threshold ∈ [0.1, 0.9]: lower = less coercion tolerated
    before reactance fires.
    """
    # Direct inversion. PINNED structure (Brehm & Brehm 1981 §4).
    return 1.0 - proneness


def _compute_reactance_magnitude_brehm(
    importance: float,
    threat_magnitude: float,
    propagation: float = _P_BASELINE,
) -> float:
    """Canonical Brehm reactance magnitude.

    # Brehm 1966; Brehm & Brehm 1981 §3:
    # R = I × M × P
    # where I = importance of threatened freedom,
    #       M = magnitude of threat,
    #       P = implication for further freedoms (propagation).
    # Strong threats to unimportant freedoms → minimal reactance.
    # Weak threats to important freedoms → also minimal.
    # The interaction is what drives the response.

    Returns R ∈ [0, 1]. PINNED structure (canonical Brehm formulation).
    """
    return max(0.0, min(1.0, importance * threat_magnitude * propagation))


def _compute_backfire_probability(
    reactance_magnitude: float,
    effective_threshold: float,
    sigmoid_k: float = _BACKFIRE_SIGMOID_K,
) -> float:
    """Wicklund boomerang sigmoid: P(backfire | reactance, threshold).

    # Wicklund 1974 §6 (boomerang effect):
    # When reactance exceeds threshold, persuasion response REVERSES.
    # Structure is canonical; transition steepness is empirical and
    # PILOT_PENDING (A14: BACKFIRE_SIGMOID_STEEPNESS_PILOT_PENDING).

    Pins:
    - R << threshold → P ≈ 0
    - R = threshold  → P = 0.5
    - R >> threshold → P ≈ 1
    """
    delta = reactance_magnitude - effective_threshold
    return 1.0 / (1.0 + math.exp(-sigmoid_k * delta))


def _compute_propagation_factor(exposure_count: int) -> float:
    """The P factor in I × M × P, amplified by repeat exposure.

    # Brehm & Brehm 1981 §3 / Miron & Brehm 2006 §4:
    # Repeat exposure to the same coercive mechanism signals a pattern,
    # amplifying P (implication for further freedoms).
    # PINNED structure; magnitude is PILOT_PENDING (A14:
    # PROPAGATION_FACTOR_REPEAT_EXPOSURE_PILOT_PENDING).
    """
    if exposure_count <= 1:
        return _P_BASELINE
    extra = (exposure_count - 1) * _P_REPEAT_AMPLIFIER_PER_EXPOSURE
    return min(_P_MAX, _P_BASELINE + extra)


# =============================================================================
# AUTONOMY REACTANCE ATOM
# =============================================================================

# Default importance of autonomy in advertising context (Deci & Ryan 1985:
# autonomy is a fundamental psychological need, generally high-valued).
# PINNED for the default case; per-domain adjustments are TBD.
_AUTONOMY_IMPORTANCE_DEFAULT = 0.7


class AutonomyReactanceAtom(BaseAtom):
    """Detects reactance risk and constrains persuasion intensity.

    Acts as a SAFETY VALVE for the persuasion system:
    1. Estimates user's reactance proneness (HPRS proxy)
    2. Computes per-mechanism reactance magnitude via canonical Brehm formula
    3. Maps reactance to backfire probability via Wicklund sigmoid
    4. Emits per-mechanism adjustments + a typed ChainAttestation

    Output should be treated as a HARD CONSTRAINT for high-coerciveness
    mechanisms — exceeding the reactance threshold doesn't just reduce
    effectiveness, it REVERSES it (Wicklund 1974 §6).
    """

    ATOM_TYPE = AtomType.AUTONOMY_REACTANCE
    ATOM_NAME = "autonomy_reactance"
    TARGET_CONSTRUCT = "reactance_threshold"

    REQUIRED_SOURCES = [
        IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
    ]

    OPTIONAL_SOURCES = [
        IntelligenceSourceType.EMPIRICAL_PATTERNS,
        IntelligenceSourceType.MECHANISM_TRAJECTORIES,
        IntelligenceSourceType.GRAPH_EMERGENCE,
    ]

    # B3-LUXY redo metadata — bump on canonical-formula or chain-shape change
    ATOM_VERSION = "2.0"  # 2.0 = canonical Brehm redo (was 1.0 additive proxy)

    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        return None

    # ------------------------------------------------------------------
    # CORE COMPUTATION
    # ------------------------------------------------------------------

    def _compute_user_reactance_state(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """Compute the user-side reactance state (proneness + threshold + PK).

        Returns dict with: proneness, threshold, persuasion_knowledge,
        exposure_count, signal_quality (0=default-only, 1=full signal).
        """
        ad_context = atom_input.ad_context or {}
        psy = PsychologicalConstructResolver(atom_input)

        signal_quality = 1.0 if psy.has_any else 0.0

        # NDF-derived reactance proneness proxy
        ce = psy.cognitive_engagement if psy.has_any else 0.5
        aa = psy.approach_avoidance if psy.has_any else 0.5
        ut = psy.uncertainty_tolerance if psy.has_any else 0.5
        aas = psy.arousal_seeking if psy.has_any else 0.5

        proneness = _compute_reactance_proneness_proxy(ce, aa, ut, aas)
        threshold = _compute_effective_threshold(proneness)

        # Persuasion Knowledge Model (Friestad & Wright 1994) modulation —
        # high PK amplifies cognitive component of reactance per Steindl
        # 2015 §3 (intertwined model: cognitive vigilance and detection).
        pk_level = 0.5  # baseline (no upstream signal)
        pk_from_upstream = False
        sa_output = atom_input.get_upstream("atom_strategic_awareness")
        if sa_output and sa_output.secondary_assessments:
            pk_value = sa_output.secondary_assessments.get("pk_level")
            if pk_value is not None:
                pk_level = float(pk_value)
                pk_from_upstream = True
                # High PK lowers effective threshold (vigilance increases
                # sensitivity). Bounded modulation per Friestad & Wright
                # 1994 finding that PK shifts but does not eliminate
                # persuasion susceptibility.
                threshold = max(0.1, threshold - pk_level * 0.15)

        exposure_count = int(ad_context.get("exposure_count", 1) or 1)

        return {
            "proneness": proneness,
            "threshold": threshold,
            "persuasion_knowledge": pk_level,
            "exposure_count": float(exposure_count),
            "signal_quality": signal_quality,
            "pk_from_upstream": 1.0 if pk_from_upstream else 0.0,
            "ndf_ce": ce,
            "ndf_aa": aa,
            "ndf_ut": ut,
            "ndf_aas": aas,
        }

    def _compute_per_mechanism_backfire(
        self,
        user_state: Dict[str, float],
    ) -> Dict[str, Dict[str, float]]:
        """Compute reactance magnitude + backfire probability per mechanism.

        Returns dict: mechanism_id → {reactance, backfire_prob, adjustment}.
        Uses canonical Brehm I × M × P then Wicklund sigmoid.
        """
        I = _AUTONOMY_IMPORTANCE_DEFAULT
        P = _compute_propagation_factor(int(user_state["exposure_count"]))
        threshold = user_state["threshold"]
        # PK amplifies M (the threat magnitude felt) — high-PK users
        # perceive coerciveness more sharply.
        pk_amplifier = 1.0 + 0.3 * user_state["persuasion_knowledge"]

        results: Dict[str, Dict[str, float]] = {}
        for mechanism, raw_coerciveness in MECHANISM_COERCIVENESS.items():
            M = min(1.0, raw_coerciveness * pk_amplifier)
            R = _compute_reactance_magnitude_brehm(I, M, P)
            p_backfire = _compute_backfire_probability(R, threshold)

            # Adjustment: negative when likely to backfire, positive
            # boost for autonomy-preserving alternatives when reactance
            # is elevated.
            #
            # ORDERING NOTE: the autonomy-preserving boost short-circuits
            # the backfire-penalty branches. Theoretically, mechanisms
            # below the perceived-threat floor (raw_coerciveness < 0.25
            # — storytelling, embodied_cognition, unity, identity_construction,
            # reciprocity) operate via Petty & Cacioppo 1986 peripheral
            # route or via Cialdini "unity" principle without engaging
            # the freedom-threat circuit at all. Their residual sigmoid
            # P(backfire) is a numerical artifact of the smooth transition,
            # not a genuine theoretical signal — those mechanisms should
            # be promoted for reactance-prone users, not penalized.
            if raw_coerciveness < 0.25 and user_state["proneness"] > 0.6:
                # Autonomy-preserving mechanism + high-proneness user → boost
                # (the autonomy-preserving alternative is especially helpful)
                adjustment = 0.10 + (user_state["proneness"] - 0.6) * 0.25
            elif p_backfire > 0.5:
                # Above threshold — heavy penalty (Wicklund response reversal)
                adjustment = -min(0.30, p_backfire * 0.4)
            elif p_backfire > 0.2:
                # Approaching threshold — moderate penalty
                adjustment = -min(0.15, (p_backfire - 0.2) * 0.5)
            else:
                adjustment = 0.0

            results[mechanism] = {
                "raw_coerciveness": raw_coerciveness,
                "amplified_coerciveness_M": M,
                "reactance_magnitude_R": R,
                "backfire_probability": p_backfire,
                "adjustment": adjustment,
            }

        return results

    # ------------------------------------------------------------------
    # CHAIN ATTESTATION CONSTRUCTION
    # ------------------------------------------------------------------

    def _build_chain_attestation(
        self,
        atom_input: AtomInput,
        user_state: Dict[str, float],
        per_mechanism: Dict[str, Dict[str, float]],
    ) -> ChainAttestation:
        """Construct the 5-link ChainAttestation for this decision.

        Chain shape (Phase 0 simplest case):
          L1: NDF dispositional signals → reactance_proneness
          L2: reactance_proneness → effective_threshold
          L3: mechanism_coerciveness → autonomy_freedom_threat
              (per-mechanism but represented at chain level via the
              average for chain-level theory updates; per-mechanism
              detail lives in mechanism_adjustments)
          L4: freedom_threat × persuasion_knowledge → reactance_magnitude
          L5: reactance_magnitude > threshold → backfire_probability
        """
        signal_quality = user_state["signal_quality"]
        from_prior_only = signal_quality < 0.5

        # L1: NDF dispositional signals → reactance_proneness
        # PILOT_PENDING — HPRS proxy derivation, not canonical HPRS.
        link1 = ConstructLink(
            source_construct="user_dispositional_signals",
            relation_type=RelationType.MODULATED_BY,
            target_construct="reactance_proneness",
            evidence_value=user_state["proneness"],
            confidence=0.5 + signal_quality * 0.3,
            citation="Hong & Page 1989 (HPRS instrument); Steindl et al. 2015 §3",
            calibration_status=CalibrationStatus.PILOT_PENDING,
            from_prior_only=from_prior_only,
        )

        # L2: reactance_proneness → effective_threshold
        # PINNED — direct inversion per Brehm & Brehm 1981 §4.
        link2 = ConstructLink(
            source_construct="reactance_proneness",
            relation_type=RelationType.MODULATED_BY,
            target_construct="effective_threshold",
            evidence_value=user_state["threshold"],
            confidence=0.7,
            citation="Brehm & Brehm 1981 §4 (trait-state relationship)",
            calibration_status=CalibrationStatus.PINNED,
        )

        # L3: mechanism_coerciveness → autonomy_freedom (chain-level summary)
        # Per-mechanism detail in AdjustmentEvidence below. PILOT_PENDING
        # because per-mechanism magnitudes are literature midpoints.
        avg_coerciveness = sum(
            d["raw_coerciveness"] for d in per_mechanism.values()
        ) / max(1, len(per_mechanism))
        link3 = ConstructLink(
            source_construct="mechanism_coerciveness",
            relation_type=RelationType.THREATENS,
            target_construct="autonomy_freedom",
            evidence_value=avg_coerciveness,
            confidence=0.6,
            citation="Brehm 1966 §1.2 (freedom-threat operationalization)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        )

        # L4: freedom_threat × persuasion_knowledge → reactance_magnitude
        # PINNED structure (Brehm I × M × P + PKM amplification);
        # the I, M, P magnitudes themselves are PILOT_PENDING but the
        # MULTIPLICATIVE COMBINATION RULE is canonical and pinned.
        avg_R = sum(
            d["reactance_magnitude_R"] for d in per_mechanism.values()
        ) / max(1, len(per_mechanism))
        link4 = ConstructLink(
            source_construct="freedom_threat_x_persuasion_knowledge",
            relation_type=RelationType.AMPLIFIES,
            target_construct="reactance_magnitude",
            evidence_value=avg_R,
            confidence=0.7,
            citation=(
                "Brehm & Brehm 1981 §3 (R = I × M × P); "
                "Friestad & Wright 1994 (PKM amplification)"
            ),
            calibration_status=CalibrationStatus.PINNED,
        )

        # L5: reactance_magnitude > threshold → backfire_probability
        # Sigmoid steepness PILOT_PENDING; canonical structure PINNED.
        avg_p_backfire = sum(
            d["backfire_probability"] for d in per_mechanism.values()
        ) / max(1, len(per_mechanism))
        link5 = ConstructLink(
            source_construct="reactance_magnitude_vs_threshold",
            relation_type=RelationType.PRODUCES,
            target_construct="backfire_probability",
            evidence_value=avg_p_backfire,
            confidence=0.65,
            citation="Wicklund 1974 §6 (boomerang); Steindl et al. 2015 §4 (intertwined model)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        )

        chain = [link1, link2, link3, link4, link5]

        # Per-mechanism AdjustmentEvidence — each adjustment records
        # the link_ids responsible so the learning loop can update the
        # right LinkPosteriors when the outcome arrives.
        chain_link_ids = [link.link_id for link in chain]
        adjustments: List[AdjustmentEvidence] = []
        for mechanism, data in per_mechanism.items():
            if abs(data["adjustment"]) < 1e-6:
                continue  # skip no-op adjustments
            rationale = (
                f"M={data['amplified_coerciveness_M']:.2f}, "
                f"R={data['reactance_magnitude_R']:.2f}, "
                f"P(backfire)={data['backfire_probability']:.2f}"
            )
            adjustments.append(
                AdjustmentEvidence(
                    mechanism_id=mechanism,
                    adjustment_value=data["adjustment"],
                    chain_links_responsible=chain_link_ids,
                    confidence=link5.confidence,
                    rationale=rationale,
                )
            )

        # Final assessment — the highest backfire probability is the
        # decision-relevant scalar (worst-case mechanism is the
        # constraint).
        max_backfire = max(
            (d["backfire_probability"] for d in per_mechanism.values()),
            default=0.0,
        )
        final = TypedEvidence(
            construct=self.TARGET_CONSTRUCT,
            value=max_backfire,
            confidence=link5.confidence,
            citation="Wicklund 1974 §6 + Brehm & Brehm 1981 §3",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        )

        provenance = ChainProvenance(
            atom_id=self.config.atom_id,
            atom_version=self.ATOM_VERSION,
            formula_citations=[
                "Brehm 1966",
                "Brehm & Brehm 1981 §3",
                "Wicklund 1974 §6",
                "Hong & Page 1989",
                "Friestad & Wright 1994",
                "Steindl et al. 2015",
                "Miron & Brehm 2006",
            ],
            a14_flags_active=[
                "REACTANCE_THRESHOLD_COEFFICIENTS_PILOT_PENDING",
                "MECHANISM_COERCIVENESS_LITERATURE_MIDPOINTS_PILOT_PENDING",
                "BACKFIRE_SIGMOID_STEEPNESS_PILOT_PENDING",
                "PROPAGATION_FACTOR_REPEAT_EXPOSURE_PILOT_PENDING",
            ],
        )

        return ChainAttestation(
            atom_id=self.config.atom_id,
            request_id=atom_input.request_id,
            target_construct=self.TARGET_CONSTRUCT,
            chain=chain,
            final_assessment=final,
            mechanism_adjustments=adjustments,
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
        """Build atom output: legacy AtomOutput contract + ChainAttestation."""

        user_state = self._compute_user_reactance_state(atom_input)
        per_mechanism = self._compute_per_mechanism_backfire(user_state)
        chain_attestation = self._build_chain_attestation(
            atom_input, user_state, per_mechanism
        )

        # ----- Legacy AtomOutput shape (preserved for existing consumers) -----
        adjustments_dict: Dict[str, float] = {
            m: d["adjustment"] for m, d in per_mechanism.items()
        }

        # DSP susceptibility post-multiplier (existing path preserved)
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            adjustments_dict = SusceptibilityHelper.apply(adjustments_dict, dsp)

        threshold = user_state["threshold"]
        budget = max(0.0, threshold * 1.5)  # legacy budget expression

        if threshold < 0.35:
            primary = "high_reactance_risk"
        elif threshold > 0.65:
            primary = "low_reactance_risk"
        else:
            primary = "moderate_reactance_risk"

        sorted_mechs = sorted(adjustments_dict.items(), key=lambda x: x[1], reverse=True)
        recommended = [m for m, s in sorted_mechs[:3] if s > 0]
        avoid = [m for m, s in sorted(adjustments_dict.items(), key=lambda x: x[1]) if s < -0.1]

        confidence = min(0.9, 0.5 + abs(threshold - 0.5) * 0.6)
        fusion_result.assessment = primary
        fusion_result.confidence = confidence

        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary,
            secondary_assessments={
                "reactance_profile": {
                    "threshold": threshold,
                    "proneness": user_state["proneness"],
                    "level": primary,
                    "exposure_count": int(user_state["exposure_count"]),
                    "persuasion_knowledge": user_state["persuasion_knowledge"],
                    "signal_quality": user_state["signal_quality"],
                },
                "mechanism_adjustments": adjustments_dict,
                "per_mechanism_detail": per_mechanism,
                "reactance_budget": budget,
                "mechanisms_to_avoid": avoid,
                "hard_constraints": {
                    "max_coerciveness": threshold,
                    "avoid_mechanisms": avoid,
                    "prefer_autonomy_preserving": user_state["proneness"] > 0.6,
                },
                "atom_version": self.ATOM_VERSION,
            },
            recommended_mechanisms=recommended,
            mechanism_weights={
                m: max(0.1, 0.5 + adjustments_dict.get(m, 0.0))
                for m in recommended
            } if recommended else {"identity_construction": 0.5},
            inferred_states={
                "reactance_threshold": threshold,
                "reactance_proneness": user_state["proneness"],
                "reactance_budget": budget,
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
            chain_attestation=chain_attestation,  # B3-LUXY Phase 0 typed evidence
        )
