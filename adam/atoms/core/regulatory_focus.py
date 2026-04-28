# =============================================================================
# ADAM Regulatory Focus Atom — Canonical Higgins Redo (B3-LUXY Phase 2)
# Location: adam/atoms/core/regulatory_focus.py
# =============================================================================

"""
REGULATORY FOCUS ATOM (canonical, B3-LUXY Phase 2 atom 9)
============================================================

Implements Higgins 1997 Regulatory Focus Theory with the canonical
ORTHOGONAL two-dimensional structure (promotion and prevention as
independent dimensions, not opposite ends of a single scale —
Higgins 1997 §4). Operationalizes the RFQ instrument (Higgins et al.
2001) for trait derivation from Big Five. Computes regulatory fit
(Higgins 2000) when ad framing context is available.

Discipline rule compliance (see `memory/feedback_atom_redo_discipline.md`):
- (a) Canonical formulas in code with `paper:section` citations: see
  `_compute_rfq_scores_orthogonal` (Higgins et al. 2001),
  `_classify_dominant_focus` (Higgins 1997 §4),
  `_compute_regulatory_fit` (Higgins 2000).
- (b) Regression tests pinning published anchors.
- (c) Calibration-pending flags on placeholder constants.
- (d) 5-link ChainAttestation with orthogonality preserved (L1+L2 are
  parallel-not-sequential).

ACADEMIC FOUNDATION
-------------------
- Higgins (1997) §4: *Beyond Pleasure and Pain*. Foundational paper.
  Two regulatory systems (promotion and prevention) operate
  independently. Promotion: motivated by ideal self-guides, presence
  vs absence of positives, eagerness strategies. Prevention: motivated
  by ought self-guides, presence vs absence of negatives, vigilance
  strategies. The two dimensions are ORTHOGONAL — a person can be high
  on both, low on both, or asymmetric.
- Higgins, Friedman, Harlow, Idson, Ayduk & Taylor (2001) §3-§4:
  *Regulatory Focus Questionnaire*. The 11-item RFQ with two scales
  (promotion: 6 items; prevention: 5 items) empirically supports the
  orthogonality (between-scale correlation r ≈ 0.0-0.2). This is the
  canonical measurement instrument — our Big Five proxy is PILOT_PENDING
  pending RFQ-instrument integration.
- Higgins (2000): *Making a Good Decision: Value from Fit*. Regulatory
  fit theory. When framing matches focus (gain framing × promotion;
  loss framing × prevention), persuasion is more effective. The match
  produces a "feeling-right" experience that amplifies evaluations.
- Avnet & Higgins (2006): regulatory-fit operationalization in
  marketing contexts.
- Crowe & Higgins (1997): empirical demonstration of the eagerness vs
  vigilance strategy distinction.
- Lockwood, Jordan & Kunda (2002): role of self-relevant exemplars in
  promotion vs prevention regulatory orientation.

ACTIVE A14 CALIBRATION-PENDING FLAGS
-------------------------------------
- A14: HIGGINS_RFQ_PILOT_PENDING — the Big Five → RFQ mapping is a
  literature-midpoint proxy. The canonical instrument (Higgins et al.
  2001) is direct measurement; our derivation from Big Five is a
  proxy. Retire when LUXY pilot accumulates ≥500 conversions per
  archetype with RFQ-derived framing.
- A14: AROUSAL_RFQ_SHIFT_PILOT_PENDING — Yerkes-Dodson high arousal
  shifts toward prevention; the magnitude is a literature midpoint.
- A14: HIGGINS_DOMINANCE_THRESHOLD_PILOT_PENDING — the magnitude
  difference required for dominance classification (promo vs prev) is
  a literature midpoint.
- A14: REGULATORY_FIT_AMPLIFIER_PILOT_PENDING — Higgins 2000 specifies
  fit amplifies persuasion; the amplification magnitude is a literature
  midpoint (currently 1.3x for matched, 0.8x for mismatched).
- A14: RFQ_MECHANISM_MAPPINGS_PILOT_PENDING — per-focus Cialdini
  mechanism adjustments are literature midpoints.

CHAIN SHAPE
-----------
Higgins-orthogonal (5 links). L1 and L2 are PARALLEL (both feed L3) —
this preserves the orthogonality of the promotion and prevention
dimensions in the chain itself, not just in the score.

  L1: (user_dispositional_signals × Big_Five) -[MODULATED_BY]-> (RFQ_promotion_score)
      — Higgins et al. 2001 promotion subscale; PILOT_PENDING coefficients.
  L2: (user_dispositional_signals × Big_Five) -[MODULATED_BY]-> (RFQ_prevention_score)
      — Higgins et al. 2001 prevention subscale; PILOT_PENDING coefficients.
  L3: (RFQ_promotion × RFQ_prevention) -[PRODUCES]-> (dominant_focus)
      — Higgins 1997 §4 orthogonality → dominance; PINNED structure,
        PILOT_PENDING threshold.
  L4: (dominant_focus × ad_framing) -[PRODUCES]-> (regulatory_fit)
      — Higgins 2000 regulatory fit; PINNED structure, PILOT_PENDING
        amplification.
  L5: (regulatory_fit × dominant_focus) -[PRODUCES]-> (mechanism_adjustments)
      — focus-specific Cialdini mechanism mapping; PILOT_PENDING magnitudes.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from adam.atoms.core.base import BaseAtom
from adam.atoms.core.construct_resolver import PsychologicalConstructResolver
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
# A14: HIGGINS_DOMINANCE_THRESHOLD_PILOT_PENDING
# =============================================================================
# Threshold by which one focus must exceed the other to be classified
# as dominant; below threshold → balanced. Literature midpoint.
# =============================================================================
_DOMINANCE_THRESHOLD = 0.15


# =============================================================================
# A14: REGULATORY_FIT_AMPLIFIER_PILOT_PENDING
# =============================================================================
# Higgins 2000: regulatory fit amplifies persuasion when focus matches
# framing. Multipliers for matched / mismatched / neutral framing.
# =============================================================================
_FIT_MATCH_AMPLIFIER = 1.30
_FIT_MISMATCH_AMPLIFIER = 0.80
_FIT_NEUTRAL_AMPLIFIER = 1.00


# =============================================================================
# A14: AROUSAL_RFQ_SHIFT_PILOT_PENDING
# =============================================================================
# Yerkes-Dodson: high arousal narrows attention → prevention orientation.
# Magnitude of arousal-driven RFQ shift is a literature midpoint.
# =============================================================================
_AROUSAL_TO_PREVENTION_SHIFT = 0.15


# =============================================================================
# A14: HIGGINS_RFQ_PILOT_PENDING (Big Five → RFQ proxy)
# =============================================================================
# Per-Big-Five-trait coefficients for proxy RFQ derivation. Direction
# (sign) is theoretically motivated:
#   PROMOTION:
#     extraversion → ↑ promotion (eagerness, sociability)
#     openness → ↑ promotion (exploration, growth)
#     conscientiousness → mild ↑ (achievement focus subset)
#   PREVENTION:
#     conscientiousness → ↑ prevention (vigilance, duty)
#     neuroticism → ↑ prevention (threat-sensitivity)
#     openness → mild ↓ (exploration favors promotion over vigilance)
# Magnitudes are literature midpoints.
# =============================================================================
BIG_FIVE_TO_PROMOTION: Dict[str, float] = {
    "extraversion": 0.40,
    "openness": 0.30,
    "conscientiousness": 0.10,
    "agreeableness": 0.10,
    "neuroticism": -0.20,
}

BIG_FIVE_TO_PREVENTION: Dict[str, float] = {
    "conscientiousness": 0.40,
    "neuroticism": 0.30,
    "agreeableness": 0.10,
    "openness": -0.10,
    "extraversion": -0.10,
}


# =============================================================================
# A14: RFQ_MECHANISM_MAPPINGS_PILOT_PENDING
# =============================================================================
# Per-focus mechanism adjustments. Theoretically motivated:
#   promotion-dominant → mechanisms that signal achievement, growth,
#                         self-expansion (authority for achievement
#                         signals; identity_construction; mimetic_desire)
#   prevention-dominant → mechanisms that signal safety, security,
#                          loss-prevention (commitment, social_proof,
#                          authority for assurance, regulatory_focus
#                          via loss framing)
#   balanced → mild boost to broadly-applicable mechanisms
# Magnitudes are literature midpoints.
# =============================================================================
RFQ_MECHANISM_MAP: Dict[str, Dict[str, float]] = {
    "promotion": {
        "authority": 0.10,
        "identity_construction": 0.20,
        "mimetic_desire": 0.15,
        "scarcity": 0.05,
        "regulatory_focus": 0.15,  # Recommends gain framing
        "commitment": -0.05,
    },
    "prevention": {
        "commitment": 0.20,
        "social_proof": 0.15,
        "authority": 0.15,
        "regulatory_focus": 0.20,  # Recommends loss framing
        "scarcity": -0.10,
        "attention_dynamics": -0.10,
    },
    "balanced": {
        "social_proof": 0.10,
        "regulatory_focus": 0.10,
        "identity_construction": 0.05,
    },
}


# =============================================================================
# CANONICAL FORMULA HELPERS
# =============================================================================


def _compute_rfq_scores_orthogonal(
    big_five: Dict[str, float],
    has_signal: bool,
) -> Tuple[float, float]:
    """Compute promotion and prevention RFQ scores ORTHOGONALLY.

    # Higgins 1997 §4 + Higgins et al. 2001 §3-§4:
    # Promotion and prevention are TWO DIMENSIONS, not endpoints of
    # one. The RFQ measures them independently. We approximate via
    # weighted combinations of Big Five traits, but the scores are
    # NOT constrained to sum to 1 — they vary independently.
    #
    # Pins (anchored in tests):
    #   no signal → both scores = 0.5 (neutral baseline)
    #   high extraversion + openness → high promotion (independent of prevention)
    #   high conscientiousness + neuroticism → high prevention (independent
    #     of promotion)
    #   user can have HIGH BOTH (chronic dual-focus) or LOW BOTH (chronic
    #     dis-engagement)
    #
    # PINNED orthogonal structure; per-trait coefficients PILOT_PENDING.
    """
    if not has_signal:
        return 0.5, 0.5

    promotion = 0.5
    for trait, weight in BIG_FIVE_TO_PROMOTION.items():
        trait_value = big_five.get(trait, 0.5)
        promotion += (trait_value - 0.5) * weight
    promotion = max(0.05, min(0.95, promotion))

    prevention = 0.5
    for trait, weight in BIG_FIVE_TO_PREVENTION.items():
        trait_value = big_five.get(trait, 0.5)
        prevention += (trait_value - 0.5) * weight
    prevention = max(0.05, min(0.95, prevention))

    return promotion, prevention


def _classify_dominant_focus(
    promotion: float,
    prevention: float,
    threshold: float = _DOMINANCE_THRESHOLD,
) -> str:
    """Higgins 1997 §4 dominance classification from orthogonal scores.

    # Higgins 1997 §4: dominant focus is the dimension whose RFQ score
    # exceeds the other by a substantive margin. When neither
    # dominates, the user has BALANCED focus (responds to either
    # framing roughly equally) — distinct from low-engagement
    # (low both) which is also balanced for the purposes of
    # framing decisions.
    #
    # Pins:
    #   promotion > prevention + threshold → "promotion"
    #   prevention > promotion + threshold → "prevention"
    #   else                               → "balanced"
    #
    # PINNED structure; threshold magnitude PILOT_PENDING.
    """
    if promotion > prevention + threshold:
        return "promotion"
    if prevention > promotion + threshold:
        return "prevention"
    return "balanced"


def _compute_regulatory_fit(
    dominant_focus: str,
    ad_framing: Optional[str],
) -> Tuple[str, float]:
    """Higgins 2000 regulatory fit: framing-focus match amplification.

    # Higgins 2000:
    # When framing matches focus (gain × promotion; loss × prevention),
    # persuasion produces a "feeling-right" experience that amplifies
    # evaluations.
    #
    # Returns (fit_status, amplifier):
    #   "matched"    → _FIT_MATCH_AMPLIFIER (>1.0; amplification)
    #   "mismatched" → _FIT_MISMATCH_AMPLIFIER (<1.0; attenuation)
    #   "neutral"    → _FIT_NEUTRAL_AMPLIFIER (1.0; no effect — when
    #                  framing is unknown or balanced)
    #
    # PINNED structure; magnitudes PILOT_PENDING.
    """
    if ad_framing not in {"gain", "loss"}:
        return "neutral", _FIT_NEUTRAL_AMPLIFIER

    if dominant_focus == "promotion" and ad_framing == "gain":
        return "matched", _FIT_MATCH_AMPLIFIER
    if dominant_focus == "prevention" and ad_framing == "loss":
        return "matched", _FIT_MATCH_AMPLIFIER
    if dominant_focus == "balanced":
        return "neutral", _FIT_NEUTRAL_AMPLIFIER

    # Cross-pair: promotion×loss or prevention×gain → mismatch
    return "mismatched", _FIT_MISMATCH_AMPLIFIER


def _apply_arousal_shift(
    promotion: float,
    prevention: float,
    arousal: Optional[float],
) -> Tuple[float, float]:
    """Yerkes-Dodson arousal-shifts-toward-prevention moderation.

    # Yerkes-Dodson: high arousal narrows attention → vigilance
    # strategies → prevention orientation. Operationally, arousal
    # above 0.7 shifts mass from promotion to prevention.
    #
    # Pin: arousal = None → no shift; high arousal → prevention boost.
    """
    if arousal is None:
        return promotion, prevention
    if arousal > 0.70:
        shift = (arousal - 0.70) * _AROUSAL_TO_PREVENTION_SHIFT * 3.0
        return (
            max(0.05, promotion - shift),
            min(0.95, prevention + shift),
        )
    return promotion, prevention


# =============================================================================
# REGULATORY FOCUS ATOM
# =============================================================================


class RegulatoryFocusAtom(BaseAtom):
    """Models user's regulatory focus via Higgins 1997 + RFQ + Higgins 2000.

    Computes:
    1. Orthogonal RFQ promotion + prevention scores from Big Five
       (Higgins et al. 2001 proxy)
    2. Arousal-shift moderation (Yerkes-Dodson)
    3. Dominant-focus classification (Higgins 1997 §4)
    4. Regulatory fit when ad framing is known (Higgins 2000)
    5. Mechanism adjustments matched to focus + fit
    """

    ATOM_TYPE = AtomType.REGULATORY_FOCUS
    ATOM_NAME = "regulatory_focus"
    TARGET_CONSTRUCT = "regulatory_focus"

    REQUIRED_SOURCES = [
        IntelligenceSourceType.MECHANISM_TRAJECTORIES,
    ]

    OPTIONAL_SOURCES = [
        IntelligenceSourceType.EMPIRICAL_PATTERNS,
        IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
        IntelligenceSourceType.GRAPH_EMERGENCE,
        IntelligenceSourceType.BANDIT_POSTERIORS,
    ]

    # B3-LUXY redo metadata
    ATOM_VERSION = "2.0"  # 2.0 = canonical Higgins/RFQ redo

    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        if source == IntelligenceSourceType.NONCONSCIOUS_SIGNALS:
            return await self._query_arousal_signals(atom_input)
        elif source == IntelligenceSourceType.EMPIRICAL_PATTERNS:
            return await self._query_focus_patterns(atom_input)
        elif source == IntelligenceSourceType.BANDIT_POSTERIORS:
            return await self._query_focus_bandits(atom_input)
        return None

    async def _query_arousal_signals(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query arousal signals — high arousal shifts toward prevention."""
        try:
            user_intel = atom_input.request_context.user_intelligence
            if user_intel.current_arousal is not None:
                arousal = user_intel.current_arousal
                if arousal > 0.7:
                    focus = "prevention"
                    reasoning = f"High arousal ({arousal:.2f}) → prevention (Yerkes-Dodson)"
                elif arousal < 0.4:
                    focus = "promotion"
                    reasoning = f"Low arousal ({arousal:.2f}) → promotion eligible"
                else:
                    focus = "balanced"
                    reasoning = f"Moderate arousal ({arousal:.2f}) → balanced"
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
                    construct=self.TARGET_CONSTRUCT,
                    assessment=focus,
                    assessment_value=arousal,
                    confidence=0.6,
                    confidence_semantics=ConfidenceSemantics.SIGNAL_STRENGTH,
                    strength=EvidenceStrength.MODERATE,
                    reasoning=reasoning,
                )
        except (AttributeError, Exception) as e:
            logger.debug(f"Arousal query failed: {e}")
        return None

    async def _query_focus_patterns(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query empirical patterns for regulatory focus from Big Five."""
        try:
            user_intel = atom_input.request_context.user_intelligence
            if user_intel.profile and user_intel.profile.big_five:
                bf = user_intel.profile.big_five
                big_five_dict = {
                    "extraversion": bf.extraversion,
                    "openness": bf.openness,
                    "conscientiousness": bf.conscientiousness,
                    "agreeableness": bf.agreeableness,
                    "neuroticism": bf.neuroticism,
                }
                promotion, prevention = _compute_rfq_scores_orthogonal(
                    big_five_dict, has_signal=True
                )
                focus = _classify_dominant_focus(promotion, prevention)
                confidence = min(
                    0.85, 0.5 + abs(promotion - prevention)
                )
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.EMPIRICAL_PATTERNS,
                    construct=self.TARGET_CONSTRUCT,
                    assessment=focus,
                    assessment_value=promotion - prevention,
                    confidence=confidence,
                    confidence_semantics=ConfidenceSemantics.STATISTICAL,
                    strength=EvidenceStrength.MODERATE,
                    reasoning=(
                        f"Big Five proxy → promo={promotion:.2f}, "
                        f"prev={prevention:.2f} → {focus}"
                    ),
                )
        except (AttributeError, Exception) as e:
            logger.debug(f"Focus pattern query failed: {e}")
        return None

    async def _query_focus_bandits(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query bandit posteriors for focus-aligned messaging history."""
        try:
            user_intel = atom_input.request_context.user_intelligence
            if not user_intel.mechanism_history:
                return None
            promo_mechs = ["gain_framing", "aspiration_activation", "achievement"]
            prev_mechs = ["loss_framing", "safety_activation", "responsibility"]
            promo_success = 0.5
            prev_success = 0.5
            promo_trials = 0
            prev_trials = 0
            for mech_id, mech in user_intel.mechanism_history.mechanisms.items():
                if any(pm in mech_id.lower() for pm in promo_mechs):
                    promo_success = max(promo_success, mech.success_rate)
                    promo_trials += mech.trial_count
                elif any(pm in mech_id.lower() for pm in prev_mechs):
                    prev_success = max(prev_success, mech.success_rate)
                    prev_trials += mech.trial_count
            total_trials = promo_trials + prev_trials
            if total_trials > 5:
                if promo_success > prev_success + 0.1:
                    focus = "promotion"
                elif prev_success > promo_success + 0.1:
                    focus = "prevention"
                else:
                    focus = "balanced"
                return IntelligenceEvidence(
                    source_type=IntelligenceSourceType.BANDIT_POSTERIORS,
                    construct=self.TARGET_CONSTRUCT,
                    assessment=focus,
                    confidence=0.7 if focus != "balanced" else 0.5,
                    confidence_semantics=ConfidenceSemantics.BAYESIAN_POSTERIOR,
                    strength=self._trial_count_to_strength(total_trials),
                    support_count=total_trials,
                    reasoning=(
                        f"Bandit: promo={promo_success:.2f}, "
                        f"prev={prev_success:.2f}"
                    ),
                )
        except (AttributeError, Exception) as e:
            logger.debug(f"Focus bandits query failed: {e}")
        return None

    # ------------------------------------------------------------------
    # CORE COMPUTATION
    # ------------------------------------------------------------------

    def _compute_rfq_state(self, atom_input: AtomInput) -> Dict[str, Any]:
        """Compute orthogonal RFQ scores + arousal shift + classification +
        regulatory fit."""
        # Resolve Big Five from request context
        big_five_dict: Dict[str, float] = {}
        has_big_five = False
        try:
            user_intel = atom_input.request_context.user_intelligence
            if user_intel.profile and user_intel.profile.big_five:
                bf = user_intel.profile.big_five
                big_five_dict = {
                    "extraversion": bf.extraversion,
                    "openness": bf.openness,
                    "conscientiousness": bf.conscientiousness,
                    "agreeableness": bf.agreeableness,
                    "neuroticism": bf.neuroticism,
                }
                has_big_five = True
        except (AttributeError, Exception):
            pass

        # Step 1: orthogonal RFQ scores (Higgins et al. 2001 proxy)
        promotion, prevention = _compute_rfq_scores_orthogonal(
            big_five_dict, has_signal=has_big_five
        )

        # Step 2: arousal shift (Yerkes-Dodson)
        arousal: Optional[float] = None
        try:
            arousal = atom_input.request_context.user_intelligence.current_arousal
        except (AttributeError, Exception):
            pass
        promotion_eff, prevention_eff = _apply_arousal_shift(
            promotion, prevention, arousal
        )

        # Step 3: dominant-focus classification
        dominant = _classify_dominant_focus(promotion_eff, prevention_eff)

        # Step 4: regulatory fit (Higgins 2000)
        ad_framing = None
        try:
            ad_context = atom_input.ad_context or {}
            ad_framing = ad_context.get("ad_framing")  # "gain" | "loss" | None
        except (AttributeError, Exception):
            pass
        fit_status, fit_amplifier = _compute_regulatory_fit(dominant, ad_framing)

        return {
            "promotion": promotion,
            "prevention": prevention,
            "promotion_effective": promotion_eff,
            "prevention_effective": prevention_eff,
            "arousal": arousal,
            "dominant_focus": dominant,
            "ad_framing": ad_framing,
            "fit_status": fit_status,
            "fit_amplifier": fit_amplifier,
            "has_big_five": has_big_five,
        }

    def _compute_mechanism_adjustments(
        self,
        rfq_state: Dict[str, Any],
    ) -> Dict[str, float]:
        dominant = rfq_state["dominant_focus"]
        fit_amplifier = rfq_state["fit_amplifier"]
        base_map = RFQ_MECHANISM_MAP.get(dominant, RFQ_MECHANISM_MAP["balanced"])

        adjustments: Dict[str, float] = {}
        for mech, base_adj in base_map.items():
            adj = base_adj * fit_amplifier
            adjustments[mech] = max(-0.30, min(0.30, adj))

        return adjustments

    # ------------------------------------------------------------------
    # CHAIN ATTESTATION CONSTRUCTION
    # ------------------------------------------------------------------

    def _build_chain_attestation(
        self,
        atom_input: AtomInput,
        rfq_state: Dict[str, Any],
        adjustments: Dict[str, float],
    ) -> ChainAttestation:
        from_prior_only = not rfq_state["has_big_five"]

        # L1: dispositional × Big_Five → RFQ_promotion (PARALLEL with L2)
        link1 = ConstructLink(
            source_construct="user_dispositional_signals_x_Big_Five",
            relation_type=RelationType.MODULATED_BY,
            target_construct="RFQ_promotion_score",
            evidence_value=rfq_state["promotion"],
            confidence=0.65 if rfq_state["has_big_five"] else 0.40,
            citation="Higgins et al. 2001 §3 (RFQ promotion subscale)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
            from_prior_only=from_prior_only,
        )

        # L2: dispositional × Big_Five → RFQ_prevention (PARALLEL with L1)
        link2 = ConstructLink(
            source_construct="user_dispositional_signals_x_Big_Five",
            relation_type=RelationType.MODULATED_BY,
            target_construct="RFQ_prevention_score",
            evidence_value=rfq_state["prevention"],
            confidence=0.65 if rfq_state["has_big_five"] else 0.40,
            citation="Higgins et al. 2001 §4 (RFQ prevention subscale, orthogonal)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
            from_prior_only=from_prior_only,
        )

        # L3: (RFQ_promo × RFQ_prev) → dominant_focus  [PINNED]
        link3 = ConstructLink(
            source_construct="RFQ_promotion_x_RFQ_prevention_orthogonal",
            relation_type=RelationType.PRODUCES,
            target_construct=f"dominant_focus_{rfq_state['dominant_focus']}",
            evidence_value=abs(
                rfq_state["promotion_effective"] - rfq_state["prevention_effective"]
            ),
            confidence=0.75,
            citation="Higgins 1997 §4 (orthogonal-dimensions classification)",
            calibration_status=CalibrationStatus.PINNED,
        )

        # L4: dominant_focus × ad_framing → regulatory_fit  [PINNED structure]
        link4 = ConstructLink(
            source_construct="dominant_focus_x_ad_framing",
            relation_type=RelationType.PRODUCES,
            target_construct=f"regulatory_fit_{rfq_state['fit_status']}",
            evidence_value=abs(rfq_state["fit_amplifier"] - 1.0),
            confidence=0.75 if rfq_state["fit_status"] != "neutral" else 0.50,
            citation="Higgins 2000 (regulatory fit); Avnet & Higgins 2006",
            calibration_status=CalibrationStatus.PINNED,
        )

        # L5: regulatory_fit × dominant_focus → mechanism_adjustments
        adj_magnitude = sum(abs(v) for v in adjustments.values()) / max(
            1, len(adjustments)
        )
        link5 = ConstructLink(
            source_construct="regulatory_fit_x_dominant_focus",
            relation_type=RelationType.PRODUCES,
            target_construct="mechanism_adjustments",
            evidence_value=min(1.0, adj_magnitude * 4.0),
            confidence=0.65,
            citation="Crowe & Higgins 1997 (eagerness vs vigilance strategies)",
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
                f"focus={rfq_state['dominant_focus']}, "
                f"promo={rfq_state['promotion']:.2f}, "
                f"prev={rfq_state['prevention']:.2f}, "
                f"fit={rfq_state['fit_status']}"
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

        # Final assessment — encode dominance margin (signed: + promotion, - prevention)
        margin = rfq_state["promotion_effective"] - rfq_state["prevention_effective"]
        final = TypedEvidence(
            construct=self.TARGET_CONSTRUCT,
            value=max(0.0, min(1.0, 0.5 + margin / 2.0)),  # encoded: 0=prev, 1=promo, 0.5=balanced
            confidence=link3.confidence,
            citation="Higgins 1997 §4 + Higgins 2000 (composite)",
            calibration_status=CalibrationStatus.PILOT_PENDING,
        )

        provenance = ChainProvenance(
            atom_id=self.config.atom_id,
            atom_version=self.ATOM_VERSION,
            formula_citations=[
                "Higgins 1997 §4",
                "Higgins et al. 2001 §3",
                "Higgins et al. 2001 §4",
                "Higgins 2000",
                "Avnet & Higgins 2006",
                "Crowe & Higgins 1997",
            ],
            a14_flags_active=[
                "HIGGINS_RFQ_PILOT_PENDING",
                "AROUSAL_RFQ_SHIFT_PILOT_PENDING",
                "HIGGINS_DOMINANCE_THRESHOLD_PILOT_PENDING",
                "REGULATORY_FIT_AMPLIFIER_PILOT_PENDING",
                "RFQ_MECHANISM_MAPPINGS_PILOT_PENDING",
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
        rfq_state = self._compute_rfq_state(atom_input)
        adjustments = self._compute_mechanism_adjustments(rfq_state)

        chain_attestation = self._build_chain_attestation(
            atom_input, rfq_state, adjustments
        )

        focus = rfq_state["dominant_focus"]

        # Legacy framing recommendations (preserved for downstream consumers)
        if focus == "promotion":
            legacy_recommended = ["gain_framing", "aspiration_activation", "growth_messaging"]
            legacy_weights = {"gain_framing": 0.8, "aspiration_activation": 0.6}
        elif focus == "prevention":
            legacy_recommended = ["loss_framing", "safety_activation", "security_messaging"]
            legacy_weights = {"loss_framing": 0.8, "safety_activation": 0.6}
        else:
            legacy_recommended = ["balanced_framing", "dual_focus"]
            legacy_weights = {"balanced_framing": 0.6}

        # Combine with Cialdini-mechanism adjustments (new Phase 2)
        sorted_cialdini = sorted(
            adjustments.items(), key=lambda kv: kv[1], reverse=True
        )
        cialdini_recommended = [m for m, s in sorted_cialdini[:3] if s > 0]

        # Confidence: scales with dominance margin
        margin = abs(rfq_state["promotion_effective"] - rfq_state["prevention_effective"])
        confidence = min(0.85, 0.4 + margin * 1.5)

        fusion_result.assessment = focus
        fusion_result.confidence = confidence

        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=focus,
            secondary_assessments={
                "promotion_tendency": rfq_state["promotion_effective"],
                "prevention_tendency": rfq_state["prevention_effective"],
                "promotion_baseline": rfq_state["promotion"],
                "prevention_baseline": rfq_state["prevention"],
                "regulatory_fit": rfq_state["fit_status"],
                "fit_amplifier": rfq_state["fit_amplifier"],
                "ad_framing": rfq_state["ad_framing"],
                "legacy_recommended_framings": legacy_recommended,
                "cialdini_mechanism_adjustments": adjustments,
                "atom_version": self.ATOM_VERSION,
            },
            recommended_mechanisms=legacy_recommended + cialdini_recommended,
            mechanism_weights={
                **legacy_weights,
                **{m: max(0.1, 0.5 + adjustments.get(m, 0.0)) for m in cialdini_recommended},
            },
            inferred_states={
                "regulatory_focus_promotion": rfq_state["promotion_effective"],
                "regulatory_focus_prevention": rfq_state["prevention_effective"],
                "regulatory_fit_amplifier": rfq_state["fit_amplifier"],
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
            chain_attestation=chain_attestation,
        )
