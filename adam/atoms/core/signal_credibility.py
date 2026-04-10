# =============================================================================
# ADAM Signal Credibility Atom
# Location: adam/atoms/core/signal_credibility.py
# =============================================================================

"""
SIGNAL CREDIBILITY ATOM

Grounded in Signaling Theory (Spence, 1973) and Costly Signaling Theory
(Zahavi, 1975). Evaluates the credibility of advertising signals by
analyzing whether they are costly (hard to fake), observable (verifiable),
and relevant (diagnostic of actual quality).

Key insight: Consumers subconsciously assess whether an ad's claims are
"cheap talk" or "costly signals." A money-back guarantee is costly (the
firm bears real risk); a vague "best in class" claim is cheap. This atom
determines which mechanisms to use based on whether the brand has credible
signals to leverage — and which signals the user is most attuned to.

Academic Foundation:
- Spence (1973): Job Market Signaling — costly actions reveal private info
- Zahavi (1975): Handicap Principle — reliable signals must be costly
- Connelly et al. (2011): Signaling Theory review — management applications
- Kirmani & Rao (2000): No Pain, No Gain — costly signal typology in ads
"""

import logging
import math
from typing import Dict, List, Optional

from adam.atoms.core.base import BaseAtom
from adam.atoms.models.evidence import (
    IntelligenceEvidence,
    MultiSourceEvidence,
    FusionResult,
    EvidenceStrength,
)
from adam.atoms.models.atom_io import AtomInput, AtomOutput
from adam.blackboard.models.zone2_reasoning import AtomType
from adam.graph_reasoning.models.intelligence_sources import (
    IntelligenceSourceType,
    ConfidenceSemantics,
)
from adam.atoms.core.dsp_integration import DSPDataAccessor, CategoryModerationHelper
from adam.atoms.core.construct_resolver import PsychologicalConstructResolver

logger = logging.getLogger(__name__)


# =============================================================================
# SIGNAL TAXONOMY (Kirmani & Rao, 2000 typology)
# =============================================================================

SIGNAL_TYPES = {
    "warranty": {
        "costliness": 0.9,   # High real cost if product fails
        "observability": 0.95,  # Easily verified
        "mechanisms": ["commitment", "authority", "social_proof"],
        "ndf_affinity": {"uncertainty_tolerance": -0.3, "approach_avoidance": 0.2},
        "description": "Money-back guarantees, extended warranties — real financial risk",
    },
    "price_premium": {
        "costliness": 0.85,
        "observability": 0.9,
        "mechanisms": ["anchoring", "identity_construction", "scarcity"],
        "ndf_affinity": {"status_sensitivity": 0.4, "cognitive_engagement": 0.2},
        "description": "Premium pricing as quality signal — Veblen goods effect",
    },
    "brand_investment": {
        "costliness": 0.8,
        "observability": 0.7,
        "mechanisms": ["authority", "identity_construction"],
        "ndf_affinity": {"temporal_horizon": 0.3, "social_calibration": 0.2},
        "description": "Heavy advertising spend, celebrity endorsements, sponsorships",
    },
    "transparency": {
        "costliness": 0.75,
        "observability": 0.85,
        "mechanisms": ["reciprocity", "commitment"],
        "ndf_affinity": {"cognitive_engagement": 0.3, "uncertainty_tolerance": 0.2},
        "description": "Open-book pricing, ingredient lists, process documentation",
    },
    "third_party_validation": {
        "costliness": 0.7,
        "observability": 0.95,
        "mechanisms": ["authority", "social_proof"],
        "ndf_affinity": {"uncertainty_tolerance": -0.2, "cognitive_engagement": 0.3},
        "description": "Certifications, awards, peer-reviewed claims, expert endorsements",
    },
    "social_proof_signals": {
        "costliness": 0.4,   # Lower cost — easy to aggregate
        "observability": 0.8,
        "mechanisms": ["social_proof", "mimetic_desire"],
        "ndf_affinity": {"social_calibration": 0.4, "uncertainty_tolerance": -0.2},
        "description": "User counts, review scores, 'bestseller' tags",
    },
    "cheap_talk": {
        "costliness": 0.1,   # Essentially free claims
        "observability": 0.2,
        "mechanisms": [],  # These should be AVOIDED
        "ndf_affinity": {"cognitive_engagement": 0.4},  # Only works on low-engagement
        "description": "Unverifiable claims: 'best quality', 'world class', 'premium'",
    },
}

# How uncertainty tolerance affects signal credibility requirements
# Low UT users NEED costly signals; high UT users accept cheaper ones
UNCERTAINTY_SIGNAL_THRESHOLDS = {
    "very_low": 0.8,    # Needs highly costly signals
    "low": 0.65,
    "moderate": 0.5,
    "high": 0.35,
    "very_high": 0.2,   # Accepts cheap talk more readily
}


class SignalCredibilityAtom(BaseAtom):
    """
    Evaluates advertising signal credibility to determine persuasion strategy.

    This atom answers: "Given what we know about this user's psychological
    profile and the brand's available signals, which persuasion mechanisms
    should we deploy that will be perceived as CREDIBLE rather than manipulative?"

    The atom reads upstream assessments and NDF profiles to determine:
    1. User's signal sensitivity (how much they discount cheap signals)
    2. Available signal types from brand context
    3. Mechanism recommendations aligned with credible signaling

    Output feeds into MechanismActivation for mechanism scoring.
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

    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query construct-specific sources for signal credibility."""
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

            # Categories where costly signals matter MORE
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
            else:
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

    def _assess_user_signal_sensitivity(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        Determine how sensitive this user is to signal credibility.

        Maps NDF dimensions to signal sensitivity:
        - Low uncertainty_tolerance → HIGH signal sensitivity (needs proof)
        - High cognitive_engagement → HIGH signal sensitivity (analyzes claims)
        - High status_sensitivity → SELECTIVE signal sensitivity (status signals)
        - Low approach_avoidance → HIGH signal sensitivity (cautious)
        """
        # Use PsychologicalConstructResolver — prefers graph/expanded types over NDF
        psy = PsychologicalConstructResolver(atom_input)

        # Default moderate sensitivity
        sensitivity = {
            "overall": 0.5,
            "warranty_need": 0.5,
            "authority_need": 0.5,
            "social_proof_need": 0.5,
            "transparency_need": 0.5,
            "cheap_talk_discount": 0.5,  # How much they discount cheap signals
        }

        if not psy.has_any:
            return sensitivity

        ut = psy.uncertainty_tolerance
        ce = psy.cognitive_engagement
        ss = psy.status_sensitivity
        aa = psy.approach_avoidance
        sc = psy.social_calibration

        # Overall signal sensitivity
        # Low uncertainty tolerance + high cognitive engagement = very signal-sensitive
        sensitivity["overall"] = 0.5 + (0.5 - ut) * 0.4 + (ce - 0.5) * 0.3

        # Specific signal needs
        sensitivity["warranty_need"] = max(0, min(1, 0.5 + (0.5 - ut) * 0.6))
        sensitivity["authority_need"] = max(0, min(1, 0.5 + ce * 0.3 + (0.5 - ut) * 0.2))
        sensitivity["social_proof_need"] = max(0, min(1, 0.3 + sc * 0.5 + (0.5 - ut) * 0.2))
        sensitivity["transparency_need"] = max(0, min(1, 0.3 + ce * 0.5 + (0.5 - aa) * 0.2))

        # Cheap talk discount: how much the user discounts unverifiable claims
        # High CE + low UT = heavy discount on cheap talk
        sensitivity["cheap_talk_discount"] = max(0, min(1,
            0.3 + ce * 0.3 + (0.5 - ut) * 0.3 + (0.5 - aa) * 0.1
        ))

        return sensitivity

    def _assess_brand_signals(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        Assess what signals the brand/product has available.

        Reads from ad context and upstream brand personality atom.
        """
        ad_context = atom_input.ad_context or {}
        signals = {}

        # Check for warranty/guarantee
        desc = (ad_context.get("product_description", "") +
                ad_context.get("creative_text", "")).lower()

        warranty_words = ["guarantee", "warranty", "money-back", "risk-free", "refund"]
        if any(w in desc for w in warranty_words):
            signals["warranty"] = 0.8

        # Check for third-party validation
        validation_words = ["certified", "award", "endorsed", "approved", "tested", "verified"]
        if any(w in desc for w in validation_words):
            signals["third_party_validation"] = 0.7

        # Check for transparency signals
        transparency_words = ["transparent", "honest", "open", "real ingredients", "no hidden"]
        if any(w in desc for w in transparency_words):
            signals["transparency"] = 0.6

        # Check for social proof signals
        social_words = ["million", "bestsell", "popular", "trusted by", "rated", "reviews"]
        if any(w in desc for w in social_words):
            signals["social_proof_signals"] = 0.7

        # Check for price premium signals
        premium_words = ["premium", "luxury", "exclusive", "artisan", "handcraft"]
        if any(w in desc for w in premium_words):
            signals["price_premium"] = 0.6

        # Check for cheap talk
        cheap_words = ["best", "amazing", "incredible", "world-class", "unbeatable"]
        if any(w in desc for w in cheap_words) and len(signals) < 2:
            signals["cheap_talk"] = 0.8  # Mostly cheap talk

        # Brand personality upstream
        bp_output = atom_input.get_upstream("atom_brand_personality")
        if bp_output and bp_output.secondary_assessments:
            brand_trust = bp_output.secondary_assessments.get("trust_score", 0.5)
            if brand_trust > 0.7:
                signals["brand_investment"] = brand_trust

        return signals

    def _compute_credibility_scores(
        self,
        user_sensitivity: Dict[str, float],
        brand_signals: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Compute mechanism credibility scores by matching user signal needs
        to available brand signals.

        Returns mechanism adjustments (-0.3 to +0.3) to apply to base scores.
        """
        mechanism_adjustments: Dict[str, float] = {}

        overall_sensitivity = user_sensitivity["overall"]
        cheap_discount = user_sensitivity["cheap_talk_discount"]

        for signal_type, signal_strength in brand_signals.items():
            signal_def = SIGNAL_TYPES.get(signal_type)
            if not signal_def:
                continue

            costliness = signal_def["costliness"]
            aligned_mechanisms = signal_def["mechanisms"]

            # Credibility score: how credible this signal is for this user
            # High costliness + low user sensitivity = high credibility
            # Low costliness + high user sensitivity = low credibility
            if costliness > 0.5:
                # Costly signal: always helpful, MORE helpful for sensitive users
                credibility = costliness * (0.5 + overall_sensitivity * 0.5)
            else:
                # Cheap signal: penalized proportional to user sensitivity
                credibility = costliness * (1.0 - cheap_discount * 0.6)

            # Boost aligned mechanisms
            for mechanism in aligned_mechanisms:
                mech_key = mechanism.lower().replace(" ", "_")
                boost = (credibility - 0.5) * 0.3 * signal_strength
                mechanism_adjustments[mech_key] = (
                    mechanism_adjustments.get(mech_key, 0.0) + boost
                )

        # If brand has mostly cheap talk and user is signal-sensitive,
        # penalize mechanisms that require credibility
        if brand_signals.get("cheap_talk", 0) > 0.5 and overall_sensitivity > 0.6:
            for mech in ["authority", "commitment"]:
                mechanism_adjustments[mech] = (
                    mechanism_adjustments.get(mech, 0.0) - 0.15
                )
            # But boost mechanisms that don't need credibility
            for mech in ["social_proof", "mimetic_desire", "attention_dynamics"]:
                mechanism_adjustments[mech] = (
                    mechanism_adjustments.get(mech, 0.0) + 0.1
                )

        return mechanism_adjustments

    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build signal credibility output."""

        # Assess user sensitivity
        user_sensitivity = self._assess_user_signal_sensitivity(atom_input)

        # Assess brand signals
        brand_signals = self._assess_brand_signals(atom_input)

        # Compute credibility-adjusted mechanism scores
        mechanism_adjustments = self._compute_credibility_scores(
            user_sensitivity, brand_signals
        )

        # DSP category moderation: adjust mechanisms by product category effectiveness
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            mechanism_adjustments = CategoryModerationHelper.apply(mechanism_adjustments, dsp)

        # Determine primary assessment
        if user_sensitivity["overall"] > 0.65:
            primary = "high_credibility_required"
        elif user_sensitivity["overall"] < 0.35:
            primary = "low_credibility_required"
        else:
            primary = "moderate_credibility_required"

        # Top recommended mechanisms (those with positive adjustments)
        sorted_mechs = sorted(
            mechanism_adjustments.items(), key=lambda x: x[1], reverse=True
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
                "mechanism_adjustments": mechanism_adjustments,
                "signal_credibility_gap": max(0, user_sensitivity["overall"] - sum(
                    SIGNAL_TYPES.get(s, {}).get("costliness", 0) * v
                    for s, v in brand_signals.items()
                ) / max(1, len(brand_signals))),
            },
            recommended_mechanisms=recommended,
            mechanism_weights={m: max(0.1, 0.5 + mechanism_adjustments.get(m, 0))
                             for m in recommended} if recommended else {"social_proof": 0.5},
            inferred_states={
                f"sensitivity_{k}": v for k, v in user_sensitivity.items()
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
