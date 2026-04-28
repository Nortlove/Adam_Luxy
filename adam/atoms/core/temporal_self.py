# =============================================================================
# ADAM Temporal Self Atom — Canonical Continuity Redo (B3-LUXY Phase 1)
# Location: adam/atoms/core/temporal_self.py
# =============================================================================

"""
TEMPORAL SELF ATOM (canonical, B3-LUXY Phase 1 atom 5)
=========================================================

Models how connected or disconnected the user feels from their future
self via Parfit's gradient personal identity (1984 §3) and Hershfield's
Future Self-Continuity (2011). Maps continuity to a hyperbolic
intertemporal discount rate (Laibson 1997; Frederick, Loewenstein &
O'Donoghue 2002) and to a discrete mechanism-preference REGIME
(present-focused vs future-focused vs blended).

Distinctive feature (per the plan doc): chain shape includes a discrete
REGIME-SWITCH transition. The continuity scalar maps to one of three
regime classifications, and the regime — not the continuity scalar —
selects mechanism preferences. This produces the discrete state-
transition behavior that distinguishes this atom from atoms 1-4 (which
are all linear-in-trait).

Discipline rule compliance (see `memory/feedback_atom_redo_discipline.md`):
- (a) Canonical formulas in code with `paper:section` citations: see
  `_compute_continuity` (Hershfield 2011 FSCS), `_classify_regime`
  (Parfit 1984 §3 identity-of-degree), `_compute_hyperbolic_discount`
  (Laibson 1997 §2), `_apply_bridging_adjustment` (Hershfield et al. 2011).
- (b) Regression tests pinning published anchors.
- (c) Calibration-pending flags on placeholder constants.
- (d) 5-link ChainAttestation with regime-switch shape.

ACADEMIC FOUNDATION
-------------------
- Parfit (1984) §3: *Reasons and Persons*. Personal identity is a
  matter of degree, not all-or-nothing. The further the future self is
  in psychological connectedness, the more "stranger-like" it becomes.
  This is the canonical structural argument for the gradient continuity
  scalar AND for the regime-switch boundaries (Parfit explicitly
  argues that personal-identity questions reduce to questions about
  degree of continuity).
- Hershfield (2011): Future self-continuity. The Future Self-Continuity
  Scale (FSCS) operationalizes Parfit's gradient as a measurable
  scalar. High FSCS → future self feels SAME person → save, invest,
  plan. Low FSCS → future self feels STRANGER → discount future,
  prioritize present.
- Hershfield, Goldstein, Sharpe, Fox, Yeykelis, Carstensen & Bailenson
  (2011): age-progressed avatars increased savings rates. Mechanism:
  increase felt continuity → decrease intertemporal discount rate.
  This is the canonical "bridging intervention" — mechanisms that
  artificially boost continuity for low-continuity users in
  high-future-relevance categories.
- Frederick, Loewenstein & O'Donoghue (2002): review of intertemporal
  choice. The hyperbolic discount form k(t) = 1/(1 + k×t) (Mazur 1987;
  Laibson 1997) is the canonical empirical operationalization;
  exponential discounting (the rational-choice prior) systematically
  fails to predict observed time-preference reversals.
- Laibson (1997) §2: hyperbolic / quasi-hyperbolic discounting formal
  treatment.
- Bartels & Urminsky (2011): empirical demonstration that FSCS predicts
  intertemporal preferences after controlling for trait impulsivity.

ACTIVE A14 CALIBRATION-PENDING FLAGS
-------------------------------------
- A14: TEMPORAL_SELF_NDF_COEFFICIENTS_PILOT_PENDING — the per-NDF-dim
  coefficients in `_compute_continuity` are theoretically motivated
  (high temporal_horizon → ↑ continuity; high arousal_seeking → ↓
  continuity) but the magnitudes are literature midpoints, not FSCS-
  validated weights. Retire when LUXY pilot accumulates ≥150 decisions
  with FSCS-style continuity ratings.
- A14: CATEGORY_TEMPORAL_PROFILES_PILOT_PENDING — per-category
  future_relevance and continuity_boost values are literature midpoints.
  Retire when pilot accumulates ≥30 conversions per category-temporal
  cell.
- A14: CONTINUITY_REGIME_THRESHOLDS_PILOT_PENDING — Parfit 1984 §3
  argues for gradient identity but does not specify discrete thresholds;
  the 0.65 high/0.35 low boundaries are literature-midpoint
  operationalizations of the regime-switch concept. Retire when pilot
  shows the empirical regime-switch points.
- A14: HYPERBOLIC_DISCOUNT_FORM_PILOT_PENDING — the linear inversion
  k = 1 - continuity is a simple operationalization. Mazur 1987 / Laibson
  1997 specify k(t) = 1/(1+kt) but the per-user k itself comes from
  observation. Pilot may indicate quasi-hyperbolic (β-δ) form better
  predicts LUXY decision behavior.
- A14: CONTINUITY_MECHANISM_ADJUSTMENT_MAGNITUDES_PILOT_PENDING — the
  per-regime mechanism adjustments in CONTINUITY_MECHANISMS are
  literature midpoints. Retire when pilot accumulates ≥50 conversions
  per (regime, mechanism) cell.

CHAIN SHAPE
-----------
Regime-switch (5 links). L2 is the discrete classification — a
state-transition link. L3 (hyperbolic discount) and L4 (regime-keyed
preferences) are downstream of L2's discrete output. L5 applies the
Hershfield-style bridging adjustment for low-continuity users in
high-future-relevance categories.

  L1: (dispositional_signals × category_temporal_profile)
      -[MODULATED_BY]-> (continuity_estimate)
      — Hershfield 2011 (FSCS gradient); PILOT_PENDING coefficients.
  L2: (continuity_estimate) -[PRODUCES]-> (regime_classification)
      — Parfit 1984 §3 (gradient → discrete identity questions);
        PINNED structure, PILOT_PENDING thresholds.
  L3: (continuity_estimate) -[PRODUCES]-> (hyperbolic_discount_rate)
      — Frederick, Loewenstein & O'Donoghue 2002; Laibson 1997 §2;
        PINNED hyperbolic form; PILOT_PENDING per-user calibration.
  L4: (regime_classification × discount_rate) -[MODULATED_BY]-> (mechanism_preference_regime)
      — Bartels & Urminsky 2011 (regime predicts intertemporal choice);
        PILOT_PENDING magnitudes.
  L5: (mechanism_preference_regime × category_future_relevance)
      -[PRODUCES]-> (mechanism_adjustments)
      — Hershfield et al. 2011 (bridging interventions for low-
        continuity users in high-future-relevance categories);
        PILOT_PENDING magnitudes.
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
# A14: CONTINUITY_REGIME_THRESHOLDS_PILOT_PENDING
# =============================================================================
# Parfit 1984 §3 argues for gradient identity but does not specify
# discrete thresholds. The 0.65/0.35 boundaries are literature-midpoint
# operationalizations of the high/moderate/low regime distinctions
# Hershfield et al. 2011 use to segment FSCS scores.
#
# RETIRE: when pilot data shows the empirical regime-switch points
# at which mechanism-preference patterns transition.
# =============================================================================
_HIGH_CONTINUITY_THRESHOLD = 0.65
_LOW_CONTINUITY_THRESHOLD = 0.35


# =============================================================================
# A14: TEMPORAL_SELF_NDF_COEFFICIENTS_PILOT_PENDING
# =============================================================================
# Per-NDF-dim coefficients for continuity derivation. Direction (sign)
# is theoretically motivated:
#   temporal_horizon  → ↑ continuity (long horizon ↔ continuous future-self)
#   cognitive_engagement → ↑ continuity (deliberation → considers future)
#   arousal_seeking   → ↓ continuity (thrill-seeking → present-focused)
#   approach_avoidance→ ↓ continuity (high approach → present-focused;
#                                     cautious users plan further)
# Magnitudes are literature midpoints from FSCS validation studies.
# =============================================================================
_NDF_TO_CONTINUITY: Dict[str, float] = {
    "temporal_horizon": 0.35,       # Primary driver
    "cognitive_engagement": 0.20,
    "arousal_seeking": -0.15,        # negative weight applied as (1 - val)
    "approach_avoidance": -0.10,     # negative weight applied as (1 - val)
}


# =============================================================================
# A14: CATEGORY_TEMPORAL_PROFILES_PILOT_PENDING
# =============================================================================
# Per-category future_relevance ∈ [0, 1] and continuity_boost ∈ [-1, 1].
# Future-relevant categories (Health, Financial, Education, Insurance)
# benefit from high-continuity framing. Hedonic/immediate categories
# (Food, Entertainment, Fashion) favor low-continuity framing.
#
# RETIRE: when pilot accumulates ≥30 conversions per category-temporal
# cell with measured framing-condition outcomes.
# =============================================================================
CATEGORY_TEMPORAL: Dict[str, Dict[str, float]] = {
    "Health":        {"future_relevance": 0.90, "continuity_boost": 0.10},
    "Financial":     {"future_relevance": 0.95, "continuity_boost": 0.15},
    "Education":     {"future_relevance": 0.85, "continuity_boost": 0.10},
    "Insurance":     {"future_relevance": 0.90, "continuity_boost": 0.10},
    "Food":          {"future_relevance": 0.20, "continuity_boost": -0.10},
    "Entertainment": {"future_relevance": 0.15, "continuity_boost": -0.15},
    "Fashion":       {"future_relevance": 0.30, "continuity_boost": -0.05},
    "Electronics":   {"future_relevance": 0.50, "continuity_boost": 0.0},
    "Subscription":  {"future_relevance": 0.70, "continuity_boost": 0.05},
}


# =============================================================================
# A14: CONTINUITY_MECHANISM_ADJUSTMENT_MAGNITUDES_PILOT_PENDING
# =============================================================================
# Per-regime mechanism adjustments. Theoretically motivated by Parfit's
# gradient personal identity:
#   high_continuity  → invest, plan, identity-build (Hershfield 2011
#                     observed savings response to continuity-boosting
#                     interventions)
#   low_continuity   → present-focused, immediate-reward (high
#                     hyperbolic discount → scarcity, attention pop,
#                     embodied gratification)
#   moderate         → blended
# Magnitudes are literature midpoints.
# =============================================================================
CONTINUITY_MECHANISMS: Dict[str, Dict[str, float]] = {
    "high_continuity": {
        "identity_construction": 0.20,
        "temporal_construal": 0.15,
        "commitment": 0.15,
        "authority": 0.05,
        "scarcity": -0.10,
        "attention_dynamics": -0.05,
    },
    "low_continuity": {
        "scarcity": 0.20,
        "attention_dynamics": 0.15,
        "embodied_cognition": 0.15,
        "mimetic_desire": 0.10,
        "social_proof": 0.10,
        "temporal_construal": -0.15,
        "commitment": -0.10,
    },
    "moderate_continuity": {
        "social_proof": 0.10,
        "identity_construction": 0.10,
        "regulatory_focus": 0.10,
        "commitment": 0.05,
    },
}


# =============================================================================
# CANONICAL FORMULA HELPERS
# =============================================================================


def _compute_continuity(
    psy_dict: Dict[str, float],
    has_signal: bool,
    category_boost: float,
) -> float:
    """Compute continuity scalar from dispositional NDF + category boost.

    # Hershfield 2011: FSCS measures perceived continuity between
    # present and future self. Disposition (temporal_horizon, cognitive
    # style) gives a baseline; category context (Hershfield et al. 2011)
    # modulates it.
    # PILOT_PENDING coefficient magnitudes.
    """
    if not has_signal:
        return max(0.05, min(0.95, 0.5 + category_boost))

    th = psy_dict.get("temporal_horizon", 0.5)
    ce = psy_dict.get("cognitive_engagement", 0.5)
    aas = psy_dict.get("arousal_seeking", 0.5)
    aa = psy_dict.get("approach_avoidance", 0.5)

    continuity = (
        0.15
        + th * _NDF_TO_CONTINUITY["temporal_horizon"]
        + ce * _NDF_TO_CONTINUITY["cognitive_engagement"]
        + (1.0 - aas) * abs(_NDF_TO_CONTINUITY["arousal_seeking"])
        + (1.0 - aa) * abs(_NDF_TO_CONTINUITY["approach_avoidance"])
    )
    continuity += category_boost
    return max(0.05, min(0.95, continuity))


def _classify_regime(continuity: float) -> str:
    """Classify continuity into Parfit-style discrete regime.

    # Parfit 1984 §3: personal identity is a matter of degree, but
    # decisions about how to TREAT the future self bifurcate into
    # discrete regimes around critical thresholds. The continuity
    # scalar is gradient; the consumption / framing response is
    # regime-switched.
    #
    # Pins:
    #   continuity > _HIGH_CONTINUITY_THRESHOLD  → "high_continuity"
    #   continuity < _LOW_CONTINUITY_THRESHOLD   → "low_continuity"
    #   else                                     → "moderate_continuity"
    #
    # PINNED structure; threshold magnitudes PILOT_PENDING.
    """
    if continuity > _HIGH_CONTINUITY_THRESHOLD:
        return "high_continuity"
    if continuity < _LOW_CONTINUITY_THRESHOLD:
        return "low_continuity"
    return "moderate_continuity"


def _compute_hyperbolic_discount(continuity: float) -> float:
    """Hyperbolic intertemporal discount rate from continuity.

    # Frederick, Loewenstein & O'Donoghue 2002; Laibson 1997 §2:
    # Mazur 1987 hyperbolic form is k(t) = 1 / (1 + k × t) where k
    # is the per-user discount rate. The k parameter ITSELF (rate of
    # discounting) is what continuity determines:
    #     k = 1 - continuity
    # so high-continuity users have k → 0 (patient), low-continuity
    # users have k → 1 (impatient).
    # PINNED structure (k as inverse of continuity); PILOT_PENDING the
    # per-user calibration.
    """
    return max(0.0, min(1.0, 1.0 - continuity))


def _resolve_category_temporal(category: str) -> Dict[str, float]:
    """Look up category temporal profile (future_relevance, continuity_boost)."""
    if not category:
        return {"future_relevance": 0.5, "continuity_boost": 0.0}
    cat_lower = category.lower()
    for cat_key, profile in CATEGORY_TEMPORAL.items():
        if cat_key.lower() in cat_lower:
            return dict(profile)
    return {"future_relevance": 0.5, "continuity_boost": 0.0}


# =============================================================================
# TEMPORAL SELF ATOM
# =============================================================================


class TemporalSelfAtom(BaseAtom):
    """Models future self-continuity to optimize temporal framing.

    Computes:
    1. Continuity scalar from NDF + category context (Hershfield 2011)
    2. Discrete regime classification (Parfit 1984 §3 — REGIME SWITCH)
    3. Hyperbolic intertemporal discount rate (Laibson 1997)
    4. Regime-keyed mechanism preferences (Bartels & Urminsky 2011)
    5. Bridging adjustments for low-continuity users in high-future-
       relevance categories (Hershfield et al. 2011)
    """

    ATOM_TYPE = AtomType.TEMPORAL_SELF
    ATOM_NAME = "temporal_self"
    TARGET_CONSTRUCT = "future_self_continuity"

    REQUIRED_SOURCES = [
        IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
    ]

    OPTIONAL_SOURCES = [
        IntelligenceSourceType.EMPIRICAL_PATTERNS,
        IntelligenceSourceType.TEMPORAL_PATTERNS,
        IntelligenceSourceType.MECHANISM_TRAJECTORIES,
    ]

    # B3-LUXY redo metadata
    ATOM_VERSION = "2.0"  # 2.0 = canonical Parfit/Hershfield redo with regime-switch chain

    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        return None

    # ------------------------------------------------------------------
    # CORE COMPUTATION
    # ------------------------------------------------------------------

    def _compute_temporal_state(self, atom_input: AtomInput) -> Dict[str, Any]:
        """Compute continuity, regime, discount, and category profile."""
        ad_context = atom_input.ad_context or {}
        category = ad_context.get("category", "")
        psy = PsychologicalConstructResolver(atom_input)
        psy_dict = psy.as_full_construct_dict() if psy.has_any else {}
        signal_quality = 1.0 if psy.has_any else 0.0

        cat_profile = _resolve_category_temporal(category)
        continuity = _compute_continuity(
            psy_dict, has_signal=psy.has_any, category_boost=cat_profile["continuity_boost"]
        )
        regime = _classify_regime(continuity)
        discount_rate = _compute_hyperbolic_discount(continuity)

        return {
            "continuity": continuity,
            "regime": regime,
            "discount_rate": discount_rate,
            "category_future_relevance": cat_profile["future_relevance"],
            "category_continuity_boost": cat_profile["continuity_boost"],
            "signal_quality": signal_quality,
        }

    def _compute_mechanism_adjustments(
        self,
        temporal_state: Dict[str, Any],
    ) -> Dict[str, float]:
        """Convert regime + discount + category to mechanism adjustments.

        Regime-keyed base adjustments + Hershfield bridging for
        low-continuity users in high-future-relevance categories.
        """
        regime = temporal_state["regime"]
        continuity = temporal_state["continuity"]
        future_relevance = temporal_state["category_future_relevance"]

        base_map = CONTINUITY_MECHANISMS.get(
            regime, CONTINUITY_MECHANISMS["moderate_continuity"]
        )

        # Intensity scales with how far the user is from the regime midpoint
        intensity = 0.5 + abs(continuity - 0.5)

        adjustments: Dict[str, float] = {}
        for mech, adj in base_map.items():
            adjustments[mech] = adj * intensity

        # Hershfield et al. 2011 bridging intervention:
        # When category is high-future-relevance but user has low
        # continuity, the gap MUST be bridged (otherwise future-framing
        # falls flat) — boost mechanisms that operate ON CONTINUITY ITSELF
        # (embodied_cognition for present-future neural continuity;
        # identity_construction for self-extension; social_proof for
        # peer-future-self mirroring).
        if future_relevance > 0.7 and continuity < 0.4:
            adjustments["embodied_cognition"] = (
                adjustments.get("embodied_cognition", 0.0) + 0.15
            )
            adjustments["identity_construction"] = (
                adjustments.get("identity_construction", 0.0) + 0.10
            )
            adjustments["social_proof"] = (
                adjustments.get("social_proof", 0.0) + 0.10
            )

        return adjustments

    # ------------------------------------------------------------------
    # CHAIN ATTESTATION CONSTRUCTION
    # ------------------------------------------------------------------

    def _build_chain_attestation(
        self,
        atom_input: AtomInput,
        temporal_state: Dict[str, Any],
        adjustments: Dict[str, float],
    ) -> ChainAttestation:
        """Construct the 5-link regime-switch ChainAttestation.

        L2 is the discrete regime-classification link. L4 is regime-keyed.
        L5 includes Hershfield bridging when applicable.
        """
        signal_quality = temporal_state["signal_quality"]
        from_prior_only = signal_quality < 0.5
        continuity = temporal_state["continuity"]
        regime = temporal_state["regime"]

        # L1: dispositional × category → continuity_estimate
        link1 = ConstructLink(
            source_construct="dispositional_signals_x_category_temporal_profile",
            relation_type=RelationType.MODULATED_BY,
            target_construct="continuity_estimate",
            evidence_value=continuity,
            confidence=0.5 + signal_quality * 0.3,
            citation="Hershfield 2011 (FSCS); Parfit 1984 §3 (gradient identity)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
            from_prior_only=from_prior_only,
        )

        # L2: continuity → regime_classification (REGIME SWITCH)
        # The evidence_value here is regime-encoded: low=0.0, moderate=0.5, high=1.0
        regime_value = (
            1.0 if regime == "high_continuity"
            else 0.5 if regime == "moderate_continuity"
            else 0.0
        )
        link2 = ConstructLink(
            source_construct="continuity_estimate",
            relation_type=RelationType.PRODUCES,
            target_construct=f"regime_{regime}",
            evidence_value=regime_value,
            confidence=0.75,
            citation="Parfit 1984 §3 (gradient → discrete identity questions)",
            calibration_status=CalibrationStatus.PINNED,
        )

        # L3: continuity → hyperbolic_discount_rate
        link3 = ConstructLink(
            source_construct="continuity_estimate",
            relation_type=RelationType.PRODUCES,
            target_construct="hyperbolic_discount_rate",
            evidence_value=temporal_state["discount_rate"],
            confidence=0.7,
            citation=(
                "Frederick, Loewenstein & O'Donoghue 2002; "
                "Laibson 1997 §2 (hyperbolic discounting)"
            ),
            calibration_status=CalibrationStatus.PINNED,
        )

        # L4: regime × discount → mechanism_preference_regime
        link4 = ConstructLink(
            source_construct="regime_classification_x_discount_rate",
            relation_type=RelationType.MODULATED_BY,
            target_construct="mechanism_preference_regime",
            evidence_value=regime_value,
            confidence=0.7,
            citation="Bartels & Urminsky 2011 (FSCS predicts intertemporal choice)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        )

        # L5: regime × category_future_relevance → mechanism_adjustments
        # (with Hershfield bridging when applicable)
        bridging_active = (
            temporal_state["category_future_relevance"] > 0.7 and continuity < 0.4
        )
        adj_magnitude = sum(abs(v) for v in adjustments.values()) / max(
            1, len(adjustments)
        )
        link5 = ConstructLink(
            source_construct="regime_x_category_future_relevance",
            relation_type=RelationType.PRODUCES,
            target_construct=(
                "bridging_mechanism_adjustments"
                if bridging_active
                else "mechanism_adjustments"
            ),
            evidence_value=min(1.0, adj_magnitude * 5.0),
            confidence=0.75 if bridging_active else 0.65,
            citation=(
                "Hershfield et al. 2011 (bridging interventions for "
                "low-continuity users in high-future-relevance categories)"
            ),
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
                f"continuity={continuity:.2f}, regime={regime}, "
                f"discount={temporal_state['discount_rate']:.2f}, "
                f"future_relevance={temporal_state['category_future_relevance']:.2f}"
                + (", bridging_active" if bridging_active else "")
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

        # Final assessment — continuity is the load-bearing scalar
        final = TypedEvidence(
            construct=self.TARGET_CONSTRUCT,
            value=continuity,
            confidence=link1.confidence,
            citation="Parfit 1984 §3 + Hershfield 2011 (composite)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        )

        provenance = ChainProvenance(
            atom_id=self.config.atom_id,
            atom_version=self.ATOM_VERSION,
            formula_citations=[
                "Parfit 1984 §3",
                "Hershfield 2011",
                "Hershfield et al. 2011",
                "Frederick, Loewenstein & O'Donoghue 2002",
                "Laibson 1997 §2",
                "Bartels & Urminsky 2011",
                "Mazur 1987",
            ],
            a14_flags_active=[
                "TEMPORAL_SELF_NDF_COEFFICIENTS_PILOT_PENDING",
                "CATEGORY_TEMPORAL_PROFILES_PILOT_PENDING",
                "CONTINUITY_REGIME_THRESHOLDS_PILOT_PENDING",
                "HYPERBOLIC_DISCOUNT_FORM_PILOT_PENDING",
                "CONTINUITY_MECHANISM_ADJUSTMENT_MAGNITUDES_PILOT_PENDING",
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

        temporal_state = self._compute_temporal_state(atom_input)
        adjustments = self._compute_mechanism_adjustments(temporal_state)

        # DSP category moderation (preserved)
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            adjustments = CategoryModerationHelper.apply(adjustments, dsp)

        chain_attestation = self._build_chain_attestation(
            atom_input, temporal_state, adjustments
        )

        primary = temporal_state["regime"]
        sorted_mechs = sorted(adjustments.items(), key=lambda x: x[1], reverse=True)
        recommended = [m for m, s in sorted_mechs[:3] if s > 0]

        confidence = min(
            0.85, 0.4 + abs(temporal_state["continuity"] - 0.5) * 0.7
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
                "temporal_profile": {
                    "continuity": temporal_state["continuity"],
                    "regime": temporal_state["regime"],
                    "discount_rate": temporal_state["discount_rate"],
                    "future_relevance": temporal_state["category_future_relevance"],
                    "level": temporal_state["regime"],  # legacy alias
                },
                "mechanism_adjustments": adjustments,
                "framing_guidance": {
                    "use_future_framing": temporal_state["regime"] == "high_continuity",
                    "use_present_framing": temporal_state["regime"] == "low_continuity",
                    "bridge_temporal_gap": (
                        temporal_state["category_future_relevance"] > 0.7
                        and temporal_state["continuity"] < 0.4
                    ),
                },
                "atom_version": self.ATOM_VERSION,
            },
            recommended_mechanisms=recommended,
            mechanism_weights={
                m: max(0.1, 0.5 + adjustments.get(m, 0.0)) for m in recommended
            } if recommended else {"social_proof": 0.5},
            inferred_states={
                "future_self_continuity": temporal_state["continuity"],
                "discount_rate": temporal_state["discount_rate"],
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
            chain_attestation=chain_attestation,
        )
