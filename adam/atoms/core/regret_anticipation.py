# =============================================================================
# ADAM Regret Anticipation Atom — Canonical Loomes & Sugden Redo (B3-LUXY Phase 2)
# Location: adam/atoms/core/regret_anticipation.py
# =============================================================================

"""
REGRET ANTICIPATION ATOM (canonical, B3-LUXY Phase 2 atom 7)
==============================================================

Implements Loomes & Sugden (1982) Regret Theory eq. 4: the modified
utility of choosing action `a` over foregone alternative `b` is

    M(a | b) = u(c_a) + R(u(c_a) − u(c_b))

where R is the regret/rejoice function with R(0) = 0, R(−z) = −R(z),
R monotone increasing. Bell (1982) adds reversibility moderation;
Gilovich & Medvec (1995) and Inman & Zeelenberg (2002) document the
empirical action-vs-inaction asymmetries that condition R's
operationalization for marketing decisions.

Discipline rule compliance (see `memory/feedback_atom_redo_discipline.md`):
- (a) Canonical formulas in code with `paper:section` citations: see
  `_regret_function` (Loomes & Sugden 1982 eq. 4),
  `_apply_reversibility_moderation` (Bell 1982 §3),
  `_classify_dominant_regret_type` (Inman & Zeelenberg 2002).
- (b) Regression tests pinning published anchors.
- (c) Calibration-pending flags on placeholder constants.
- (d) 5-link ChainAttestation with Loomes-Sugden-canonical chain shape.

ACADEMIC FOUNDATION
-------------------
- Loomes & Sugden (1982) eq. 4: *Regret Theory: An Alternative Theory
  of Rational Choice Under Uncertainty*. The canonical formula. R is
  the regret/rejoice function. Pins: R(0) = 0, R(−z) = −R(z),
  R monotone increasing.
- Loomes & Sugden (1982) §4: regret-averse R is convex on the loss
  side; the magnitude |R(−z)| > z (linear baseline) for regret-averse
  agents.
- Bell (1982) §3: *Regret in Decision Making Under Uncertainty*.
  Independent derivation of regret-utility framework; Bell's
  contribution is operationalizing reversibility — reversible
  decisions reduce anticipated action-regret because the agent
  knows they can undo.
- Gilovich & Medvec (1995): *The Experience of Regret*. Empirical
  asymmetry — short-term: action regret > inaction; long-term:
  inaction regret > action. This temporal-horizon moderation is
  load-bearing for advertising decisions (mostly short-term).
- Inman & Zeelenberg (2002): action vs inaction regret asymmetries
  in consumer decisions; per-category empirical priors.
- Zeelenberg (1999): *Anticipated Regret*. Regret about a decision
  precedes the decision and influences it; this is what makes regret
  load-bearing for ad copy framing (we manipulate anticipated regret).
- Connolly & Zeelenberg (2002): regret-mechanism mappings — how
  regret-aware framing maps to specific persuasion mechanisms.
- Simonson (1992): the *Compromise Effect* — middle options chosen to
  minimize anticipated regret of either extreme.

ACTIVE A14 CALIBRATION-PENDING FLAGS
-------------------------------------
- A14: LOOMES_SUGDEN_REVERSIBILITY_WEIGHTS_PILOT_PENDING — Bell 1982
  specifies that reversibility moderates anticipated action-regret;
  the moderation magnitude is a literature midpoint (currently 0.5).
  Retire when LUXY pilot accumulates ≥300 conversions with
  reversibility-stratified outcomes.
- A14: REGRET_AVERSION_BETA_PILOT_PENDING — the β exponent in
  R(z) = sign(z) × |z|^β is a literature midpoint (currently 1.2).
  Loomes & Sugden 1982 §4 specifies that β > 1 captures regret
  aversion. Retire when pilot data calibrates per-archetype β values.
- A14: CATEGORY_REGRET_PROFILES_PILOT_PENDING — per-category action /
  inaction / reversibility magnitudes synthesized from Inman &
  Zeelenberg 2002 + category-specific empirical observations. Retire
  when pilot accumulates ≥30 conversions per category with regret-type
  outcome attribution.
- A14: NDF_REGRET_WEIGHTS_PILOT_PENDING — per-NDF-dim weights that
  shift action/inaction regret balance. Direction is theoretically
  motivated; magnitudes are literature midpoints.
- A14: REGRET_MECHANISM_MAPPINGS_PILOT_PENDING — REGRET_MECHANISM_MAP
  magnitudes derive from Connolly & Zeelenberg 2002 typology;
  per-mechanism magnitudes are placeholders.

CHAIN SHAPE
-----------
Loomes-Sugden-canonical (5 links). L2 (R-function) and L3 (Bell
reversibility) are PINNED canonical structures.

  L1: (dispositional × category_regret_profile)
      -[MODULATED_BY]-> (action_inaction_regret_balance)
      — Inman & Zeelenberg 2002; Gilovich & Medvec 1995; PILOT_PENDING.
  L2: (regret_balance × outcome_uncertainty)
      -[PRODUCES]-> (regret_function_R_z)
      — Loomes & Sugden 1982 eq. 4; PINNED canonical R.
  L3: (regret_function_R_z × decision_reversibility)
      -[MODULATED_BY]-> (effective_anticipated_regret)
      — Bell 1982 §3; PINNED canonical reversibility moderation.
  L4: (effective_anticipated_regret)
      -[PRODUCES]-> (dominant_regret_type)
      — Inman & Zeelenberg 2002 classification; PILOT_PENDING thresholds.
  L5: (dominant_regret_type)
      -[PRODUCES]-> (mechanism_adjustments)
      — Connolly & Zeelenberg 2002 typology; PILOT_PENDING magnitudes.
"""

import logging
import math
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
# A14: REGRET_AVERSION_BETA_PILOT_PENDING
# =============================================================================
# β exponent in R(z) = sign(z) × |z|^β.
#   β = 1.0 → linear (no regret aversion)
#   β > 1.0 → regret aversion (Loomes & Sugden 1982 §4)
#   β < 1.0 → "rejoice-prefering" (gains loom larger; rare)
#
# 1.2 is a literature-midpoint default. Per-archetype β values are
# empirical and PILOT_PENDING.
# =============================================================================
_REGRET_AVERSION_BETA = 1.2


# =============================================================================
# A14: LOOMES_SUGDEN_REVERSIBILITY_WEIGHTS_PILOT_PENDING
# =============================================================================
# Bell 1982 §3: reversible decisions reduce anticipated ACTION-regret.
# Operationally:
#     action_regret_effective = action_regret × (1 − γ × reversibility)
#     inaction_regret unchanged (cannot un-NOT-buy by reversing)
# γ = 0.5 is a literature-midpoint moderation magnitude.
# =============================================================================
_REVERSIBILITY_MODERATION_GAMMA = 0.5


# =============================================================================
# A14: CATEGORY_REGRET_PROFILES_PILOT_PENDING
# =============================================================================
# Per-category (action_regret_baseline, inaction_regret_baseline,
# reversibility) profiles. Synthesized from Inman & Zeelenberg 2002
# typology + category-specific empirical observations.
#
# RETIRE: when pilot accumulates ≥30 conversions per category with
# regret-type outcome attribution.
# =============================================================================
CATEGORY_REGRET_PROFILES: Dict[str, Dict[str, float]] = {
    "Electronics":  {"action": 0.60, "inaction": 0.40, "reversibility": 0.50},
    "Fashion":      {"action": 0.30, "inaction": 0.70, "reversibility": 0.60},
    "Health":       {"action": 0.70, "inaction": 0.30, "reversibility": 0.20},
    "Food":         {"action": 0.20, "inaction": 0.80, "reversibility": 0.90},
    "Software":     {"action": 0.50, "inaction": 0.50, "reversibility": 0.70},
    "Automotive":   {"action": 0.80, "inaction": 0.20, "reversibility": 0.10},
    "Travel":       {"action": 0.25, "inaction": 0.75, "reversibility": 0.15},
    "Luxury":       {"action": 0.55, "inaction": 0.45, "reversibility": 0.30},
    "Home":         {"action": 0.55, "inaction": 0.45, "reversibility": 0.40},
    "Subscription": {"action": 0.35, "inaction": 0.65, "reversibility": 0.80},
}


# =============================================================================
# A14: NDF_REGRET_WEIGHTS_PILOT_PENDING
# =============================================================================
# Per-NDF-dim weights that shift action/inaction regret balance.
# Direction (sign) is theoretically motivated:
#   approach_avoidance: high approach → inaction regret (FOMO; want things)
#   uncertainty_tolerance: low UT → action regret (fear of bad choice)
#   temporal_horizon: short → inaction regret; long → action regret
#   arousal_seeking: high → inaction regret (FOMO on novelty)
#   status_sensitivity: high → inaction regret (status-anxious)
#   cognitive_engagement: high → action regret (thinks before buying)
# Magnitudes are literature midpoints.
# =============================================================================
NDF_REGRET_WEIGHTS: Dict[str, Dict[str, float]] = {
    "approach_avoidance":    {"inaction": 0.30, "action": -0.30},
    "uncertainty_tolerance": {"inaction": -0.20, "action": 0.20},
    "temporal_horizon":      {"inaction": -0.20, "action": 0.20},
    "arousal_seeking":       {"inaction": 0.25, "action": -0.25},
    "status_sensitivity":    {"inaction": 0.15, "action": -0.05},
    "cognitive_engagement":  {"inaction": -0.10, "action": 0.15},
}


# =============================================================================
# A14: REGRET_MECHANISM_MAPPINGS_PILOT_PENDING
# =============================================================================
# Connolly & Zeelenberg 2002 typology — regret-aware framing maps to
# specific persuasion mechanisms:
#   inaction-dominant → urgency / scarcity / mimetic (counter the FOMO)
#   action-dominant   → commitment / authority / regulatory_focus
#                       (provide reassurance to counter buyer's remorse)
# Magnitudes are literature midpoints.
# =============================================================================
REGRET_MECHANISM_MAP: Dict[str, Dict[str, float]] = {
    "inaction_dominant": {
        "scarcity": 0.20,
        "social_proof": 0.15,
        "mimetic_desire": 0.15,
        "attention_dynamics": 0.10,
        "temporal_construal": 0.10,
        "commitment": -0.05,
        "authority": -0.05,
    },
    "action_dominant": {
        "commitment": 0.20,
        "authority": 0.15,
        "social_proof": 0.10,
        "regulatory_focus": 0.10,
        "scarcity": -0.15,
        "attention_dynamics": -0.05,
    },
    "balanced": {
        "social_proof": 0.10,
        "commitment": 0.05,
        "regulatory_focus": 0.05,
    },
}


# =============================================================================
# CANONICAL FORMULA HELPERS
# =============================================================================


def _regret_function(delta_utility: float, beta: float = _REGRET_AVERSION_BETA) -> float:
    """Loomes & Sugden 1982 eq. 4 regret/rejoice function R(z).

    # Loomes & Sugden 1982 eq. 4:
    #     R(0) = 0
    #     R(-z) = -R(z)               (antisymmetric)
    #     R'(z) > 0                   (monotone increasing)
    #     |R'(z)| > 1 for z > 0 → regret-averse (β > 1)
    #
    # Power-form operationalization:
    #     R(z) = sign(z) × |z|^β
    #
    # Pins (anchored in tests):
    #   R(0) = 0
    #   R(-z) = -R(z)
    #   R(z) increasing in z
    #   |R(z)| > |z| when β > 1 (regret aversion magnification)
    #
    # PINNED structure; β PILOT_PENDING.
    """
    if delta_utility == 0.0:
        return 0.0
    sign = 1.0 if delta_utility > 0.0 else -1.0
    return sign * (abs(delta_utility) ** beta)


def _apply_reversibility_moderation(
    action_regret: float,
    reversibility: float,
    gamma: float = _REVERSIBILITY_MODERATION_GAMMA,
) -> float:
    """Bell 1982 §3: reversibility moderates action-regret.

    # Bell 1982 §3:
    #     action_regret_effective = action_regret × (1 − γ × reversibility)
    #
    # Pins:
    #   reversibility=0 → no moderation (full action regret retained)
    #   reversibility=1 → maximum moderation (action regret reduced by γ)
    #   inaction regret IS NOT moderated by reversibility (Bell 1982: you
    #     cannot reverse a non-decision)
    #
    # PINNED structure; γ PILOT_PENDING.
    """
    return max(0.0, action_regret * (1.0 - gamma * reversibility))


def _classify_dominant_regret_type(
    action_regret: float,
    inaction_regret: float,
    threshold: float = 0.05,
) -> str:
    """Inman & Zeelenberg 2002 dominant-regret-type classification.

    # Pins:
    #   inaction > action + threshold → "inaction"
    #   action > inaction + threshold → "action"
    #   else                          → "balanced"
    #
    # PINNED structure; threshold magnitude PILOT_PENDING.
    """
    delta = inaction_regret - action_regret
    if delta > threshold:
        return "inaction"
    if delta < -threshold:
        return "action"
    return "balanced"


def _resolve_category_regret_profile(category: str) -> Optional[Dict[str, float]]:
    """Look up category regret profile; None if no match (defensive)."""
    if not category:
        return None
    cat_lower = category.lower()
    for cat_key, profile in CATEGORY_REGRET_PROFILES.items():
        if cat_key.lower() in cat_lower:
            return dict(profile)
    return None


# =============================================================================
# REGRET ANTICIPATION ATOM
# =============================================================================


class RegretAnticipationAtom(BaseAtom):
    """Models anticipated regret via Loomes & Sugden 1982 + Bell 1982.

    Computes:
    1. Action vs inaction regret balance (NDF + category prior)
    2. R-function applied (Loomes & Sugden 1982 eq. 4)
    3. Reversibility moderation (Bell 1982 §3)
    4. Dominant-regret-type classification (Inman & Zeelenberg 2002)
    5. Mechanism adjustments (Connolly & Zeelenberg 2002 typology)
    """

    ATOM_TYPE = AtomType.REGRET_ANTICIPATION
    ATOM_NAME = "regret_anticipation"
    TARGET_CONSTRUCT = "anticipated_regret"

    REQUIRED_SOURCES = [
        IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
        IntelligenceSourceType.EMPIRICAL_PATTERNS,
    ]

    OPTIONAL_SOURCES = [
        IntelligenceSourceType.MECHANISM_TRAJECTORIES,
        IntelligenceSourceType.GRAPH_EMERGENCE,
        IntelligenceSourceType.BANDIT_POSTERIORS,
    ]

    # B3-LUXY redo metadata
    ATOM_VERSION = "2.0"  # 2.0 = canonical Loomes & Sugden redo

    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        if source == IntelligenceSourceType.EMPIRICAL_PATTERNS:
            return await self._query_regret_patterns(atom_input)
        return None

    async def _query_regret_patterns(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        try:
            ad_context = atom_input.ad_context or {}
            category = ad_context.get("category", "")
            profile = _resolve_category_regret_profile(category)
            if profile:
                dominant = (
                    "inaction" if profile["inaction"] > profile["action"] else "action"
                )
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.EMPIRICAL_PATTERNS,
                    construct=self.TARGET_CONSTRUCT,
                    assessment=f"{dominant}_regret_dominant",
                    assessment_value=max(profile["action"], profile["inaction"]),
                    confidence=0.6,
                    confidence_semantics=ConfidenceSemantics.DOMAIN_CALIBRATED,
                    strength=EvidenceStrength.MODERATE,
                    reasoning=f"Category '{category}' has {dominant} regret dominance",
                )
        except Exception as e:
            logger.debug(f"Regret pattern query failed: {e}")
        return None

    # ------------------------------------------------------------------
    # CORE COMPUTATION
    # ------------------------------------------------------------------

    def _compute_regret_state(self, atom_input: AtomInput) -> Dict[str, Any]:
        """Compute action vs inaction regret balance + R-function +
        reversibility-moderated effective regret + dominant type."""
        ad_context = atom_input.ad_context or {}
        category = ad_context.get("category", "")
        psy = PsychologicalConstructResolver(atom_input)
        psy_dict = psy.as_full_construct_dict() if psy.has_any else {}
        signal_quality = 1.0 if psy.has_any else 0.0

        # Step 1: category prior + NDF adjustments
        cat_profile = _resolve_category_regret_profile(category) or {
            "action": 0.5, "inaction": 0.5, "reversibility": 0.5
        }
        action_regret_raw = cat_profile["action"]
        inaction_regret_raw = cat_profile["inaction"]
        reversibility = cat_profile["reversibility"]

        if psy.has_any:
            for dim, weights in NDF_REGRET_WEIGHTS.items():
                dim_value = psy_dict.get(dim, 0.5)
                deviation = dim_value - 0.5
                action_regret_raw += deviation * weights.get("action", 0.0)
                inaction_regret_raw += deviation * weights.get("inaction", 0.0)

        # Normalize raw regrets to [0,1] (preserve relative balance)
        total = action_regret_raw + inaction_regret_raw
        if total > 0:
            action_regret_normalized = max(
                0.0, min(1.0, action_regret_raw / total)
            )
            inaction_regret_normalized = max(
                0.0, min(1.0, inaction_regret_raw / total)
            )
        else:
            action_regret_normalized = 0.5
            inaction_regret_normalized = 0.5

        # Step 2: apply Loomes & Sugden R-function to the regret magnitudes
        # R(action_regret) and R(inaction_regret) are the canonical regret
        # contributions to modified utility.
        r_action = abs(_regret_function(action_regret_normalized))
        r_inaction = abs(_regret_function(inaction_regret_normalized))

        # Step 3: Bell 1982 reversibility moderation (action only)
        r_action_effective = _apply_reversibility_moderation(r_action, reversibility)
        r_inaction_effective = r_inaction  # not moderated by reversibility

        # Step 4: dominant type classification
        dominant = _classify_dominant_regret_type(
            r_action_effective, r_inaction_effective
        )

        # Upstream arousal influences regret intensity (Zeelenberg 1999)
        regret_intensity = 0.5
        us_output = atom_input.get_upstream("atom_user_state")
        if us_output and us_output.inferred_states:
            arousal = us_output.inferred_states.get("arousal", 0.5)
            regret_intensity = 0.3 + arousal * 0.5

        balance = r_inaction_effective - r_action_effective

        return {
            "action_regret_raw": action_regret_normalized,
            "inaction_regret_raw": inaction_regret_normalized,
            "r_action": r_action,
            "r_inaction": r_inaction,
            "r_action_effective": r_action_effective,
            "r_inaction_effective": r_inaction_effective,
            "decision_reversibility": reversibility,
            "regret_intensity": regret_intensity,
            "regret_balance": balance,
            "dominant_type": dominant,
            "signal_quality": signal_quality,
        }

    def _compute_mechanism_adjustments(
        self,
        regret_state: Dict[str, Any],
    ) -> Dict[str, float]:
        dominant = regret_state["dominant_type"]
        intensity = regret_state["regret_intensity"]
        balance_magnitude = abs(regret_state["regret_balance"])

        key = (
            f"{dominant}_dominant" if dominant != "balanced" else "balanced"
        )
        base_map = REGRET_MECHANISM_MAP.get(key, REGRET_MECHANISM_MAP["balanced"])

        adjustments: Dict[str, float] = {}
        for mechanism, base_adj in base_map.items():
            adj = base_adj * intensity * (0.5 + balance_magnitude)
            adjustments[mechanism] = max(-0.30, min(0.30, adj))

        # Reversibility further moderates action-regret-driven adjustments
        reversibility = regret_state["decision_reversibility"]
        if reversibility > 0.6 and dominant == "action":
            for mech in adjustments:
                adjustments[mech] *= (1.0 - reversibility * 0.5)

        return adjustments

    # ------------------------------------------------------------------
    # CHAIN ATTESTATION CONSTRUCTION
    # ------------------------------------------------------------------

    def _build_chain_attestation(
        self,
        atom_input: AtomInput,
        regret_state: Dict[str, Any],
        adjustments: Dict[str, float],
    ) -> ChainAttestation:
        signal_quality = regret_state["signal_quality"]
        from_prior_only = signal_quality < 0.5

        # L1: dispositional × category → action_inaction_regret_balance
        balance_evidence = abs(
            regret_state["inaction_regret_raw"] - regret_state["action_regret_raw"]
        )
        link1 = ConstructLink(
            source_construct="dispositional_signals_x_category_regret_profile",
            relation_type=RelationType.MODULATED_BY,
            target_construct="action_inaction_regret_balance",
            evidence_value=balance_evidence,
            confidence=0.5 + signal_quality * 0.3,
            citation="Inman & Zeelenberg 2002; Gilovich & Medvec 1995",
            calibration_status=CalibrationStatus.PILOT_PENDING,
            from_prior_only=from_prior_only,
        )

        # L2: regret_balance × outcome_uncertainty → R-function
        # PINNED Loomes & Sugden 1982 eq. 4
        r_magnitude = max(regret_state["r_action"], regret_state["r_inaction"])
        link2 = ConstructLink(
            source_construct="regret_balance_x_outcome_uncertainty",
            relation_type=RelationType.PRODUCES,
            target_construct="regret_function_R_z",
            evidence_value=min(1.0, r_magnitude),
            confidence=0.80,
            citation="Loomes & Sugden 1982 eq. 4 (R(z) = sign(z) × |z|^β)",
            calibration_status=CalibrationStatus.PINNED,
        )

        # L3: R-function × reversibility → effective_anticipated_regret
        # PINNED Bell 1982 §3
        link3 = ConstructLink(
            source_construct="regret_function_x_reversibility",
            relation_type=RelationType.MODULATED_BY,
            target_construct="effective_anticipated_regret",
            evidence_value=max(
                regret_state["r_action_effective"],
                regret_state["r_inaction_effective"],
            ),
            confidence=0.75,
            citation="Bell 1982 §3 (reversibility moderates action-regret)",
            calibration_status=CalibrationStatus.PINNED,
        )

        # L4: effective regret → dominant_regret_type
        link4 = ConstructLink(
            source_construct="effective_anticipated_regret",
            relation_type=RelationType.PRODUCES,
            target_construct=f"dominant_regret_type_{regret_state['dominant_type']}",
            evidence_value=abs(regret_state["regret_balance"]),
            confidence=0.7,
            citation="Inman & Zeelenberg 2002 (action vs inaction asymmetry)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        )

        # L5: dominant_regret_type → mechanism_adjustments
        adj_magnitude = sum(abs(v) for v in adjustments.values()) / max(
            1, len(adjustments)
        )
        link5 = ConstructLink(
            source_construct="dominant_regret_type",
            relation_type=RelationType.PRODUCES,
            target_construct="mechanism_adjustments",
            evidence_value=min(1.0, adj_magnitude * 4.0),
            confidence=0.65,
            citation="Connolly & Zeelenberg 2002 (regret-mechanism mappings)",
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
                f"dominant={regret_state['dominant_type']}, "
                f"action_R={regret_state['r_action']:.2f}, "
                f"inaction_R={regret_state['r_inaction']:.2f}, "
                f"reversibility={regret_state['decision_reversibility']:.2f}"
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
            value=max(regret_state["r_action_effective"], regret_state["r_inaction_effective"]),
            confidence=link2.confidence,
            citation="Loomes & Sugden 1982 + Bell 1982 (composite)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        )

        provenance = ChainProvenance(
            atom_id=self.config.atom_id,
            atom_version=self.ATOM_VERSION,
            formula_citations=[
                "Loomes & Sugden 1982 eq. 4",
                "Loomes & Sugden 1982 §4 (regret aversion)",
                "Bell 1982 §3 (reversibility)",
                "Inman & Zeelenberg 2002",
                "Gilovich & Medvec 1995",
                "Zeelenberg 1999",
                "Connolly & Zeelenberg 2002",
            ],
            a14_flags_active=[
                "REGRET_AVERSION_BETA_PILOT_PENDING",
                "LOOMES_SUGDEN_REVERSIBILITY_WEIGHTS_PILOT_PENDING",
                "CATEGORY_REGRET_PROFILES_PILOT_PENDING",
                "NDF_REGRET_WEIGHTS_PILOT_PENDING",
                "REGRET_MECHANISM_MAPPINGS_PILOT_PENDING",
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
        regret_state = self._compute_regret_state(atom_input)
        adjustments = self._compute_mechanism_adjustments(regret_state)

        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            adjustments = CategoryModerationHelper.apply(adjustments, dsp)

        chain_attestation = self._build_chain_attestation(
            atom_input, regret_state, adjustments
        )

        dominant = regret_state["dominant_type"]
        primary = f"{dominant}_regret_dominant"

        sorted_mechs = sorted(adjustments.items(), key=lambda kv: kv[1], reverse=True)
        recommended = [m for m, s in sorted_mechs[:3] if s > 0]

        confidence = min(
            0.85,
            0.4
            + regret_state["regret_intensity"] * 0.3
            + abs(regret_state["regret_balance"]) * 0.3,
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
                "regret_profile": {
                    "action_regret": regret_state["action_regret_raw"],
                    "inaction_regret": regret_state["inaction_regret_raw"],
                    "r_action": regret_state["r_action"],
                    "r_inaction": regret_state["r_inaction"],
                    "r_action_effective": regret_state["r_action_effective"],
                    "r_inaction_effective": regret_state["r_inaction_effective"],
                    "regret_balance": regret_state["regret_balance"],
                    "regret_intensity": regret_state["regret_intensity"],
                    "decision_reversibility": regret_state["decision_reversibility"],
                    "dominant_type": dominant,
                },
                "mechanism_adjustments": adjustments,
                "framing_guidance": {
                    "use_loss_framing": dominant == "inaction",
                    "use_reassurance": dominant == "action",
                    "urgency_appropriate": (
                        dominant == "inaction" and regret_state["regret_intensity"] > 0.5
                    ),
                    "guarantee_needed": (
                        dominant == "action" and regret_state["r_action_effective"] > 0.6
                    ),
                },
                "atom_version": self.ATOM_VERSION,
            },
            recommended_mechanisms=recommended,
            mechanism_weights={
                m: max(0.1, 0.5 + adjustments.get(m, 0.0)) for m in recommended
            } if recommended else {"social_proof": 0.5},
            inferred_states={
                "action_regret": regret_state["action_regret_raw"],
                "inaction_regret": regret_state["inaction_regret_raw"],
                "regret_intensity": regret_state["regret_intensity"],
                "r_action_effective": regret_state["r_action_effective"],
                "r_inaction_effective": regret_state["r_inaction_effective"],
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
            chain_attestation=chain_attestation,
        )
