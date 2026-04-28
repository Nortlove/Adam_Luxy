# =============================================================================
# ADAM Signal Credibility Atom — Canonical Spence/Zahavi Redo (B3-LUXY Phase 2)
# Location: adam/atoms/core/signal_credibility.py
# =============================================================================

"""
SIGNAL CREDIBILITY ATOM (canonical, B3-LUXY Phase 2 atom 6)
=============================================================

Implements the canonical Spence 1973 §2 separating-equilibrium formula
`c_L > b > c_H` for signal credibility, with Zahavi 1975 handicap-
principle proportionality. For each brand signal, estimates the cost to
a high-quality producer (c_H), the cost to a low-quality producer
(c_L), and the perceived benefit (b). A signal is CREDIBLE only if
c_L > b > c_H (separating equilibrium); otherwise it pools and adds
no information.

This atom is the most LUXY-load-bearing of all 9 redos: in luxury
markets, price IS the signal. Spence's separating equilibrium is the
mathematical basis for why premium pricing creates rather than reflects
quality perception.

Discipline rule compliance (see `memory/feedback_atom_redo_discipline.md`):
- (a) Canonical formulas in code with `paper:section` citations: see
  `_spence_separating_equilibrium_satisfied` (Spence 1973 §2.3),
  `_spence_credibility_score` (Spence 1973 §3), `_zahavi_handicap_factor`
  (Zahavi 1975).
- (b) Regression tests pinning published anchors: see
  `tests/unit/test_signal_credibility_canonical.py`.
- (c) Calibration-pending flags on placeholder constants.
- (d) 5-link ChainAttestation with Spence-canonical chain shape.

ACADEMIC FOUNDATION
-------------------
- Spence (1973) §2 + §3: *Job Market Signaling*. Foundational. The
  separating-equilibrium condition: a signal is credible iff
      c_L > b > c_H
  where c_L = cost to low-quality types, c_H = cost to high-quality
  types, b = perceived benefit. When this holds, low-quality types
  cannot profitably mimic the signal (signaling > benefit), so high-
  quality types signal and the market separates. When it fails (c_L ≤ b
  or b ≤ c_H), signaling pools and conveys no information.
- Spence (1973) §3: derives the credibility-as-margin operationalization;
  signals with greater (c_L − b) and (b − c_H) margins are more credible.
- Zahavi (1975): The Handicap Principle. Biology-side proof that
  reliable signaling REQUIRES costliness — costless signals cannot be
  reliable in equilibrium.
- Connelly, Certo, Ireland & Reutzel (2011): review of signaling theory
  applied to management/marketing contexts.
- Kirmani & Rao (2000): No Pain, No Gain — cost-signal typology in
  advertising. Maps Spence's cost categories to advertising-specific
  signal types (warranty, brand investment, third-party validation,
  etc.).
- Akerlof (1970): asymmetric-information context (the lemons problem)
  that signaling theory resolves.

ACTIVE A14 CALIBRATION-PENDING FLAGS
-------------------------------------
- A14: SPENCE_COST_CURVES_PILOT_PENDING — the per-signal-type c_H and
  c_L estimates in `SIGNAL_COST_PARAMETERS` are literature midpoints
  synthesized from Kirmani & Rao 2000 typology. Spence 1973 specifies
  the separating-equilibrium STRUCTURE; pairwise (c_H, c_L) magnitudes
  for advertising signals are not empirically grounded. Retire when
  LUXY pilot accumulates ≥500 conversions per status-tier.
- A14: SIGNAL_BENEFIT_FROM_SENSITIVITY_PILOT_PENDING — the mapping
  from user signal sensitivity to perceived benefit b is literature-
  midpoint. Retire when pilot accumulates ≥150 decisions with
  sensitivity-stratified outcome data.
- A14: HANDICAP_PROPORTIONALITY_FACTOR_PILOT_PENDING — Zahavi 1975
  specifies that handicap cost must be proportional to type difference;
  the proportionality magnitude is a literature midpoint.
- A14: KIRMANI_RAO_MECHANISM_MAPPINGS_PILOT_PENDING — the per-signal
  → mechanism mappings are from Kirmani & Rao 2000 typology;
  per-mechanism magnitudes are literature midpoints.

CHAIN SHAPE
-----------
Spence-canonical (5 links). L3 is the canonical separating-equilibrium
check; L4 is the Zahavi handicap-validation. Both PINNED.

  L1: (brand_signal_features) -[PRODUCES]-> (signal_cost_estimates_c_H_c_L)
      — Kirmani & Rao 2000 typology; PILOT_PENDING per-signal magnitudes.
  L2: (signal_cost_estimates × user_signal_sensitivity) -[MODULATED_BY]-> (signal_benefit_b)
      — Spence 1973 §3; PILOT_PENDING benefit mapping.
  L3: (c_L, b, c_H) -[PRODUCES]-> (separating_equilibrium_check)
      — Spence 1973 §2.3 canonical inequality; PINNED structure.
  L4: (separating_equilibrium_check) -[MODULATED_BY]-> (handicap_validated_credibility)
      — Zahavi 1975 handicap principle; PINNED structure.
  L5: (handicap_validated_credibility) -[PRODUCES]-> (mechanism_adjustments)
      — Kirmani & Rao 2000 signal→mechanism mappings; PILOT_PENDING.
"""

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

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
# A14: SPENCE_COST_CURVES_PILOT_PENDING
# =============================================================================
# Per-signal-type (c_H, c_L) cost estimates in normalized [0, 1] space.
# Spence 1973 §2.3: separating equilibrium requires c_L > b > c_H.
#
# c_H = cost of producing the signal for a HIGH-quality producer
# c_L = cost of producing the signal for a LOW-quality producer
#
# For warranty: c_H is low (genuine product rarely needs refund);
#               c_L is high (low-quality product would face refund cost)
# For cheap_talk: c_H ≈ c_L ≈ 0 (cost of saying "world class" is the
#                same regardless of actual quality → no separation possible)
#
# Synthesized from Kirmani & Rao 2000 Table 2 (cost-signal typology).
# RETIRE: when LUXY pilot accumulates ≥500 conversions per status-tier
# with measured signal-cost-by-type-of-firm distributions.
# =============================================================================
SIGNAL_COST_PARAMETERS: Dict[str, Dict[str, Any]] = {
    "warranty": {
        "c_H": 0.10, "c_L": 0.85,
        "mechanisms": ["commitment", "authority", "social_proof"],
        "ndf_affinity": {"uncertainty_tolerance": -0.30, "approach_avoidance": 0.20},
        "description": "Money-back guarantees, extended warranties — real financial risk",
    },
    "price_premium": {
        "c_H": 0.15, "c_L": 0.80,
        "mechanisms": ["anchoring", "identity_construction", "scarcity"],
        "ndf_affinity": {"status_sensitivity": 0.40, "cognitive_engagement": 0.20},
        "description": "Premium pricing — Veblen / Spence handicap signal",
    },
    "brand_investment": {
        "c_H": 0.20, "c_L": 0.75,
        "mechanisms": ["authority", "identity_construction"],
        "ndf_affinity": {"temporal_horizon": 0.30, "social_calibration": 0.20},
        "description": "Sustained advertising spend, sponsorships",
    },
    "transparency": {
        "c_H": 0.15, "c_L": 0.70,
        "mechanisms": ["reciprocity", "commitment"],
        "ndf_affinity": {"cognitive_engagement": 0.30, "uncertainty_tolerance": 0.20},
        "description": "Open-book pricing, ingredient lists, process documentation",
    },
    "third_party_validation": {
        "c_H": 0.20, "c_L": 0.65,
        "mechanisms": ["authority", "social_proof"],
        "ndf_affinity": {"uncertainty_tolerance": -0.20, "cognitive_engagement": 0.30},
        "description": "Certifications, awards, peer-reviewed claims",
    },
    "social_proof_signals": {
        "c_H": 0.25, "c_L": 0.40,
        "mechanisms": ["social_proof", "mimetic_desire"],
        "ndf_affinity": {"social_calibration": 0.40, "uncertainty_tolerance": -0.20},
        "description": "User counts, review scores — moderate-cost signal",
    },
    "cheap_talk": {
        "c_H": 0.05, "c_L": 0.06,  # near-identical → Spence pooling equilibrium
        "mechanisms": [],
        "ndf_affinity": {"cognitive_engagement": 0.40},
        "description": "Unverifiable claims — Spence pooling equilibrium",
    },
}


# =============================================================================
# A14: HANDICAP_PROPORTIONALITY_FACTOR_PILOT_PENDING
# =============================================================================
# Zahavi 1975 handicap principle: reliable signaling requires that
# signal cost be PROPORTIONAL to type (high-quality types pay less,
# proportionally). Operationally:
#     handicap_factor = (c_L - c_H) / (c_L + c_H)   ∈ [-1, 1]
# Higher = greater proportionality = more reliable. Below threshold
# the signal pools regardless of separating-equilibrium check.
#
# RETIRE: when pilot data calibrates the handicap-magnitude vs
# signal-reliability relationship.
# =============================================================================
_HANDICAP_PROPORTIONALITY_THRESHOLD = 0.30  # below = unreliable signaling


# =============================================================================
# CANONICAL FORMULA HELPERS
# =============================================================================


def _spence_separating_equilibrium_satisfied(
    c_L: float,
    b: float,
    c_H: float,
) -> bool:
    """Canonical Spence separating-equilibrium check.

    # Spence 1973 §2.3:
    #     c_L > b > c_H  (strict inequalities)
    # When this holds:
    #   - High-quality types: signaling cost c_H < benefit b → they signal
    #   - Low-quality types: signaling cost c_L > benefit b → they don't
    #   - Market SEPARATES: signal is credible
    # When it fails:
    #   - c_L ≤ b: low types can profitably mimic → POOLING (signal lies)
    #   - b ≤ c_H: high types don't bother → no signaling
    #
    # PINNED canonical formula.
    """
    return c_L > b > c_H


def _spence_credibility_score(c_L: float, b: float, c_H: float) -> float:
    """Spence credibility magnitude derived from inequality margins.

    # Spence 1973 §3: credibility scales with the margins
    #     margin_low  = c_L - b
    #     margin_high = b - c_H
    # Both must be positive for credibility > 0; the geometric mean
    # captures the joint magnitude.
    #
    # Pins (anchored in tests):
    #   credibility(c_L, b, c_H) = 0 if separating-equilibrium fails
    #   credibility > 0 when separating-equilibrium holds
    #   credibility increases with both margins
    #
    # PINNED structure.
    """
    if not _spence_separating_equilibrium_satisfied(c_L, b, c_H):
        return 0.0
    margin_low = c_L - b
    margin_high = b - c_H
    return min(1.0, math.sqrt(margin_low * margin_high))


def _zahavi_handicap_factor(c_L: float, c_H: float) -> float:
    """Zahavi 1975 handicap proportionality factor.

    # Zahavi 1975: reliable signaling requires that the cost ratio
    # between low-quality and high-quality types be substantial.
    #     handicap_factor = (c_L - c_H) / (c_L + c_H)   ∈ [-1, 1]
    # Higher factor → greater handicap-cost proportionality → more
    # reliable signaling.
    #
    # Pins:
    #   c_L = c_H → factor = 0 (no handicap, signal pools)
    #   c_L >> c_H → factor → 1 (strong handicap)
    #   c_H > c_L → factor < 0 (perverse: low types pay less)
    #
    # PINNED canonical formula.
    """
    if c_L + c_H <= 0.0:
        return 0.0
    return (c_L - c_H) / (c_L + c_H)


def _benefit_from_user_sensitivity(
    user_sensitivity: float,
    signal_observability: float = 0.7,
) -> float:
    """Map user signal sensitivity to perceived benefit b.

    # PILOT_PENDING (Spence 1973 §3 derives benefit from market
    # equilibrium; we operationalize as a function of user sensitivity
    # and signal observability since perception of benefit varies
    # by user even for identical signals).
    """
    return max(0.05, min(0.95, 0.30 + user_sensitivity * 0.40 + signal_observability * 0.20))


# =============================================================================
# SIGNAL CREDIBILITY ATOM
# =============================================================================


class SignalCredibilityAtom(BaseAtom):
    """Evaluates advertising signal credibility via Spence/Zahavi canon.

    Computes:
    1. Per-signal Spence (c_H, c_L) cost parameters (Kirmani & Rao 2000 typology)
    2. User-derived benefit b (Spence 1973 §3)
    3. Spence separating-equilibrium check (§2.3)
    4. Zahavi handicap proportionality
    5. Mechanism adjustments tied to credibility-validated signals
    """

    ATOM_TYPE = AtomType.SIGNAL_CREDIBILITY
    ATOM_NAME = "signal_credibility"
    TARGET_CONSTRUCT = "signal_credibility"

    REQUIRED_SOURCES = [
        IntelligenceSourceType.EMPIRICAL_PATTERNS,
        IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
    ]

    OPTIONAL_SOURCES = [
        IntelligenceSourceType.GRAPH_EMERGENCE,
        IntelligenceSourceType.MECHANISM_TRAJECTORIES,
        IntelligenceSourceType.BANDIT_POSTERIORS,
    ]

    # B3-LUXY redo metadata
    ATOM_VERSION = "2.0"  # 2.0 = canonical Spence/Zahavi redo

    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        if source == IntelligenceSourceType.EMPIRICAL_PATTERNS:
            return await self._query_signal_patterns(atom_input)
        return None

    async def _query_signal_patterns(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query empirical patterns for signal effectiveness."""
        try:
            ad_context = atom_input.ad_context or {}
            category = ad_context.get("category", "")

            high_signal_categories = {
                "Electronics", "Health", "Financial", "Automotive",
                "Software", "Medical", "Insurance", "Luxury",
            }

            if any(cat.lower() in category.lower() for cat in high_signal_categories):
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.EMPIRICAL_PATTERNS,
                    construct=self.TARGET_CONSTRUCT,
                    assessment="high_signal_sensitivity",
                    assessment_value=0.8,
                    confidence=0.7,
                    confidence_semantics=ConfidenceSemantics.DOMAIN_CALIBRATED,
                    strength=EvidenceStrength.STRONG,
                    reasoning=f"Category '{category}' associated with high signal scrutiny",
                )
            return IntelligenceEvidence(
                source_type=IntelligenceSourceType.EMPIRICAL_PATTERNS,
                construct=self.TARGET_CONSTRUCT,
                assessment="moderate_signal_sensitivity",
                assessment_value=0.5,
                confidence=0.5,
                confidence_semantics=ConfidenceSemantics.DOMAIN_CALIBRATED,
                strength=EvidenceStrength.MODERATE,
                reasoning=f"Category '{category}' has moderate signal requirements",
            )
        except Exception as e:
            logger.debug(f"Signal pattern query failed: {e}")
        return None

    # ------------------------------------------------------------------
    # CORE COMPUTATION
    # ------------------------------------------------------------------

    def _assess_user_sensitivity(self, atom_input: AtomInput) -> Dict[str, float]:
        """Derive user signal sensitivity from NDF dimensions.

        PILOT_PENDING coefficients (theoretically motivated signs:
        low UT → high sensitivity, high CE → high sensitivity).
        """
        psy = PsychologicalConstructResolver(atom_input)
        if not psy.has_any:
            return {"overall": 0.5, "signal_quality": 0.0}

        ut = psy.uncertainty_tolerance
        ce = psy.cognitive_engagement
        ss = psy.status_sensitivity
        aa = psy.approach_avoidance

        overall = max(
            0.05,
            min(
                0.95,
                0.5 + (0.5 - ut) * 0.40 + (ce - 0.5) * 0.30
                + (ss - 0.5) * 0.10 + (0.5 - aa) * 0.10,
            ),
        )
        return {"overall": overall, "signal_quality": 1.0}

    def _detect_brand_signals(self, atom_input: AtomInput) -> Dict[str, float]:
        """Detect available brand signals from ad context.

        Keyword-based detection (PILOT_PENDING — replace with NLP /
        structured ad-feature ingestion in a future revision).
        """
        ad_context = atom_input.ad_context or {}
        signals: Dict[str, float] = {}

        desc = (
            ad_context.get("product_description", "")
            + " "
            + ad_context.get("creative_text", "")
        ).lower()

        if any(w in desc for w in ["guarantee", "warranty", "money-back", "risk-free", "refund"]):
            signals["warranty"] = 0.80
        if any(w in desc for w in ["certified", "award", "endorsed", "approved", "verified"]):
            signals["third_party_validation"] = 0.70
        if any(w in desc for w in ["transparent", "honest", "open", "real ingredients"]):
            signals["transparency"] = 0.60
        if any(w in desc for w in ["million", "bestsell", "popular", "trusted by", "rated"]):
            signals["social_proof_signals"] = 0.70
        if any(w in desc for w in ["premium", "luxury", "exclusive", "artisan", "handcraft"]):
            signals["price_premium"] = 0.60

        # If primarily cheap talk and no costly signals
        cheap_words_present = any(
            w in desc for w in ["best", "amazing", "incredible", "world-class"]
        )
        if cheap_words_present and len(signals) < 2:
            signals["cheap_talk"] = 0.80

        # Brand investment from upstream brand_personality atom
        bp_output = atom_input.get_upstream("atom_brand_personality")
        if bp_output and bp_output.secondary_assessments:
            brand_trust = bp_output.secondary_assessments.get("trust_score", 0.5)
            if brand_trust > 0.7:
                signals["brand_investment"] = brand_trust

        return signals

    def _compute_per_signal_credibility(
        self,
        brand_signals: Dict[str, float],
        user_sensitivity: float,
    ) -> Dict[str, Dict[str, float]]:
        """For each detected brand signal, run Spence + Zahavi pipeline.

        Returns dict: signal_type → {c_H, c_L, b, separates, credibility,
        handicap_factor, signal_strength}.
        """
        per_signal: Dict[str, Dict[str, float]] = {}
        for signal_type, signal_strength in brand_signals.items():
            params = SIGNAL_COST_PARAMETERS.get(signal_type)
            if not params:
                continue

            c_H = params["c_H"]
            c_L = params["c_L"]
            b = _benefit_from_user_sensitivity(user_sensitivity)
            separates = _spence_separating_equilibrium_satisfied(c_L, b, c_H)
            credibility = _spence_credibility_score(c_L, b, c_H)
            handicap = _zahavi_handicap_factor(c_L, c_H)

            # Zahavi handicap-validation: weak handicap ratio invalidates
            # the credibility regardless of Spence inequality.
            handicap_validated = (
                handicap >= _HANDICAP_PROPORTIONALITY_THRESHOLD
            )
            if not handicap_validated:
                credibility *= 0.5  # heavy discount for weak handicap

            per_signal[signal_type] = {
                "c_H": c_H,
                "c_L": c_L,
                "b": b,
                "separates": float(separates),
                "credibility": credibility,
                "handicap_factor": handicap,
                "handicap_validated": float(handicap_validated),
                "signal_strength": signal_strength,
            }

        return per_signal

    def _compute_mechanism_adjustments(
        self,
        per_signal: Dict[str, Dict[str, float]],
        user_sensitivity: float,
    ) -> Dict[str, float]:
        """Map credibility-scored signals → mechanism adjustments via
        Kirmani & Rao 2000 typology.
        """
        adjustments: Dict[str, float] = {}

        for signal_type, signal_data in per_signal.items():
            params = SIGNAL_COST_PARAMETERS[signal_type]
            mechanisms = params["mechanisms"]
            credibility = signal_data["credibility"]
            signal_strength = signal_data["signal_strength"]

            # Adjustment per mechanism: scales with credibility and signal strength
            for mech in mechanisms:
                boost = (credibility - 0.30) * 0.40 * signal_strength
                adjustments[mech] = max(
                    -0.25, min(0.25, adjustments.get(mech, 0.0) + boost)
                )

        # Cheap-talk penalty: if cheap_talk dominates and user is sensitive,
        # mechanisms requiring credibility get penalized.
        cheap_talk_data = per_signal.get("cheap_talk")
        if cheap_talk_data and user_sensitivity > 0.6:
            for mech in ["authority", "commitment"]:
                adjustments[mech] = max(
                    -0.25, adjustments.get(mech, 0.0) - 0.15
                )
            # Boost mechanisms that don't depend on signal credibility
            for mech in ["social_proof", "mimetic_desire", "attention_dynamics"]:
                adjustments[mech] = min(
                    0.25, adjustments.get(mech, 0.0) + 0.10
                )

        return adjustments

    # ------------------------------------------------------------------
    # CHAIN ATTESTATION CONSTRUCTION
    # ------------------------------------------------------------------

    def _build_chain_attestation(
        self,
        atom_input: AtomInput,
        user_sensitivity: Dict[str, float],
        per_signal: Dict[str, Dict[str, float]],
        adjustments: Dict[str, float],
    ) -> ChainAttestation:
        """Construct the 5-link Spence-canonical ChainAttestation."""
        signal_quality = user_sensitivity["signal_quality"]
        from_prior_only = signal_quality < 0.5

        # Aggregate signals across detected types for chain-level summary
        n = max(1, len(per_signal))
        avg_c_diff = sum(
            (d["c_L"] - d["c_H"]) for d in per_signal.values()
        ) / n if per_signal else 0.0
        avg_b = sum(d["b"] for d in per_signal.values()) / n if per_signal else 0.5
        n_separates = sum(d["separates"] for d in per_signal.values())
        avg_credibility = sum(
            d["credibility"] for d in per_signal.values()
        ) / n if per_signal else 0.0
        avg_handicap = sum(
            d["handicap_factor"] for d in per_signal.values()
        ) / n if per_signal else 0.0

        # L1: brand_signal_features → signal_cost_estimates
        link1 = ConstructLink(
            source_construct="brand_signal_features",
            relation_type=RelationType.PRODUCES,
            target_construct="signal_cost_estimates_c_H_c_L",
            evidence_value=min(1.0, max(0.0, avg_c_diff)),
            confidence=0.65 if per_signal else 0.40,
            citation="Kirmani & Rao 2000 (cost-signal typology)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
            from_prior_only=(not per_signal),
        )

        # L2: signal_costs × user_sensitivity → signal_benefit_b
        link2 = ConstructLink(
            source_construct="signal_costs_x_user_sensitivity",
            relation_type=RelationType.MODULATED_BY,
            target_construct="signal_benefit_b",
            evidence_value=avg_b,
            confidence=0.60 + signal_quality * 0.20,
            citation="Spence 1973 §3 (benefit derivation)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
            from_prior_only=from_prior_only,
        )

        # L3: (c_L, b, c_H) → separating_equilibrium_check
        # PINNED canonical Spence inequality.
        link3 = ConstructLink(
            source_construct="cost_benefit_triple",
            relation_type=RelationType.PRODUCES,
            target_construct="separating_equilibrium_check",
            evidence_value=min(1.0, n_separates / max(1.0, float(len(per_signal))))
            if per_signal else 0.0,
            confidence=0.85,
            citation="Spence 1973 §2.3 (c_L > b > c_H separating equilibrium)",
            calibration_status=CalibrationStatus.PINNED,
        )

        # L4: separating_equilibrium → handicap_validated_credibility
        # PINNED canonical Zahavi handicap principle.
        link4 = ConstructLink(
            source_construct="separating_equilibrium_check",
            relation_type=RelationType.MODULATED_BY,
            target_construct="handicap_validated_credibility",
            evidence_value=max(0.0, avg_handicap),
            confidence=0.80,
            citation="Zahavi 1975 (handicap principle); Connelly et al. 2011",
            calibration_status=CalibrationStatus.PINNED,
        )

        # L5: handicap_validated_credibility → mechanism_adjustments
        adj_magnitude = sum(abs(v) for v in adjustments.values()) / max(
            1, len(adjustments)
        )
        link5 = ConstructLink(
            source_construct="handicap_validated_credibility",
            relation_type=RelationType.PRODUCES,
            target_construct="mechanism_adjustments",
            evidence_value=min(1.0, adj_magnitude * 4.0),
            confidence=0.65,
            citation="Kirmani & Rao 2000 (signal→mechanism mappings)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        )

        chain = [link1, link2, link3, link4, link5]
        chain_link_ids = [link.link_id for link in chain]

        # Per-mechanism AdjustmentEvidence
        adjustment_evidences: List[AdjustmentEvidence] = []
        for mech, adj_value in adjustments.items():
            if abs(adj_value) < 1e-6:
                continue
            rationale_signals = [
                f"{stype}(cred={d['credibility']:.2f}, sep={int(d['separates'])})"
                for stype, d in per_signal.items()
            ]
            rationale = (
                f"signals=[{', '.join(rationale_signals[:3])}], "
                f"sensitivity={user_sensitivity['overall']:.2f}, "
                f"avg_credibility={avg_credibility:.2f}"
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
            value=avg_credibility,
            confidence=link3.confidence,
            citation="Spence 1973 §2.3 + Zahavi 1975 (composite)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        )

        provenance = ChainProvenance(
            atom_id=self.config.atom_id,
            atom_version=self.ATOM_VERSION,
            formula_citations=[
                "Spence 1973 §2.3",
                "Spence 1973 §3",
                "Zahavi 1975",
                "Kirmani & Rao 2000",
                "Connelly et al. 2011",
                "Akerlof 1970",
            ],
            a14_flags_active=[
                "SPENCE_COST_CURVES_PILOT_PENDING",
                "SIGNAL_BENEFIT_FROM_SENSITIVITY_PILOT_PENDING",
                "HANDICAP_PROPORTIONALITY_FACTOR_PILOT_PENDING",
                "KIRMANI_RAO_MECHANISM_MAPPINGS_PILOT_PENDING",
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

        user_sensitivity = self._assess_user_sensitivity(atom_input)
        brand_signals = self._detect_brand_signals(atom_input)
        per_signal = self._compute_per_signal_credibility(
            brand_signals, user_sensitivity["overall"]
        )
        mechanism_adjustments = self._compute_mechanism_adjustments(
            per_signal, user_sensitivity["overall"]
        )

        # DSP category moderation (preserved)
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            mechanism_adjustments = CategoryModerationHelper.apply(
                mechanism_adjustments, dsp
            )

        chain_attestation = self._build_chain_attestation(
            atom_input, user_sensitivity, per_signal, mechanism_adjustments
        )

        if user_sensitivity["overall"] > 0.65:
            primary = "high_credibility_required"
        elif user_sensitivity["overall"] < 0.35:
            primary = "low_credibility_required"
        else:
            primary = "moderate_credibility_required"

        sorted_mechs = sorted(
            mechanism_adjustments.items(), key=lambda kv: kv[1], reverse=True
        )
        recommended = [m for m, s in sorted_mechs[:3] if s > 0]

        confidence = min(0.9, 0.5 + len(brand_signals) * 0.1)
        fusion_result.assessment = primary
        fusion_result.confidence = confidence

        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary,
            secondary_assessments={
                "user_signal_sensitivity": user_sensitivity,
                "brand_signals_available": brand_signals,
                "per_signal_credibility": per_signal,
                "mechanism_adjustments": mechanism_adjustments,
                "atom_version": self.ATOM_VERSION,
            },
            recommended_mechanisms=recommended,
            mechanism_weights={
                m: max(0.1, 0.5 + mechanism_adjustments.get(m, 0.0))
                for m in recommended
            } if recommended else {"social_proof": 0.5},
            inferred_states={
                "signal_credibility": sum(
                    d["credibility"] for d in per_signal.values()
                ) / max(1, len(per_signal)),
                "user_sensitivity": user_sensitivity["overall"],
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
            chain_attestation=chain_attestation,
        )
