# =============================================================================
# ADAM Information Asymmetry Atom
# Location: adam/atoms/core/information_asymmetry.py
# =============================================================================

"""
INFORMATION ASYMMETRY ATOM

Grounded in Information Economics (Akerlof, 1970; Stiglitz, 2000).
Models the information gap between the brand and the consumer and
determines how to strategically bridge (or leverage) that gap.

Key insight: Every purchase decision involves an information asymmetry —
the seller knows more about the product than the buyer. The consumer's
perception of this gap dramatically affects which persuasion mechanisms
work. Users who FEEL informationally disadvantaged respond to authority
and social proof (reducing uncertainty). Users who feel well-informed
respond to commitment and identity mechanisms.

Academic Foundation:
- Akerlof (1970): The Market for Lemons — asymmetric information
- Stiglitz (2000): The Contributions of Information Economics
- Nelson (1970): Information & Consumer Behavior — search vs experience goods
- Darby & Karni (1973): Credence goods — cannot evaluate even after purchase
"""

import logging
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
# GOOD TYPE CLASSIFICATION (Nelson 1970 / Darby & Karni 1973)
# =============================================================================

GOOD_TYPE_MAP = {
    # Search goods: quality determinable BEFORE purchase
    "Electronics": "search",
    "Clothing": "search",
    "Furniture": "search",
    "Books": "search",
    "Toys": "search",
    # Experience goods: quality determinable only AFTER purchase
    "Restaurant": "experience",
    "Software": "experience",
    "Subscription": "experience",
    "Travel": "experience",
    "Entertainment": "experience",
    "Food": "experience",
    "Beauty": "experience",
    # Credence goods: quality hard to determine even AFTER purchase
    "Health": "credence",
    "Medical": "credence",
    "Financial": "credence",
    "Insurance": "credence",
    "Legal": "credence",
    "Education": "credence",
    "Supplements": "credence",
    "Automotive": "credence",  # Complex technical qualities
}

# Good type → information asymmetry severity → mechanism effectiveness
GOOD_TYPE_MECHANISMS = {
    "search": {
        "asymmetry_level": 0.3,  # Low — can verify before buying
        "mechanism_boosts": {
            "anchoring": 0.15,        # Price comparison is key
            "social_proof": 0.05,     # Less needed
            "identity_construction": 0.1,
            "attention_dynamics": 0.1,
        },
        "mechanism_penalties": {
            "authority": -0.1,  # Don't need expert opinion
        },
    },
    "experience": {
        "asymmetry_level": 0.6,  # Moderate — must trust before buying
        "mechanism_boosts": {
            "social_proof": 0.2,       # Reviews are critical
            "reciprocity": 0.15,       # Free trials reduce risk
            "storytelling": 0.1,       # Others' experiences matter
            "mimetic_desire": 0.1,
        },
        "mechanism_penalties": {
            "anchoring": -0.05,
        },
    },
    "credence": {
        "asymmetry_level": 0.85,  # Very high — can never fully verify
        "mechanism_boosts": {
            "authority": 0.25,          # Expert endorsement critical
            "commitment": 0.15,         # Guarantees essential
            "social_proof": 0.1,        # Need validation
            "regulatory_focus": 0.1,    # Prevention framing
        },
        "mechanism_penalties": {
            "scarcity": -0.15,  # Pressure backfires when can't verify
            "attention_dynamics": -0.1,
        },
    },
}


class InformationAsymmetryAtom(BaseAtom):
    """
    Models information gaps to optimize persuasion strategy.

    This atom determines:
    1. Good type (search/experience/credence)
    2. User's perceived information gap (from NDF + context)
    3. Optimal mechanisms for bridging the gap
    4. Whether to reduce asymmetry (inform) or leverage it (create urgency)
    """

    ATOM_TYPE = AtomType.INFORMATION_ASYMMETRY
    ATOM_NAME = "information_asymmetry"
    TARGET_CONSTRUCT = "information_gap"

    REQUIRED_SOURCES = [
        IntelligenceSourceType.EMPIRICAL_PATTERNS,
        IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
    ]

    OPTIONAL_SOURCES = [
        IntelligenceSourceType.GRAPH_EMERGENCE,
        IntelligenceSourceType.MECHANISM_TRAJECTORIES,
    ]

    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        if source == IntelligenceSourceType.EMPIRICAL_PATTERNS:
            return await self._query_category_asymmetry(atom_input)
        return None

    async def _query_category_asymmetry(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Classify the good type and return asymmetry level."""
        try:
            ad_context = atom_input.ad_context or {}
            category = ad_context.get("category", "")

            good_type = "experience"  # default
            for cat_key, gtype in GOOD_TYPE_MAP.items():
                if cat_key.lower() in category.lower():
                    good_type = gtype
                    break

            profile = GOOD_TYPE_MECHANISMS[good_type]
            return IntelligenceEvidence(
                source_type=IntelligenceSourceType.EMPIRICAL_PATTERNS,
                construct=self.TARGET_CONSTRUCT,
                assessment=f"{good_type}_good",
                assessment_value=profile["asymmetry_level"],
                confidence=0.7,
                confidence_semantics=ConfidenceSemantics.DOMAIN_CALIBRATED,
                strength=EvidenceStrength.STRONG,
                reasoning=f"Category '{category}' classified as {good_type} good",
            )
        except Exception as e:
            logger.debug(f"Category asymmetry query failed: {e}")
        return None

    def _classify_good_type(self, category: str) -> str:
        """Classify category into search/experience/credence."""
        for cat_key, gtype in GOOD_TYPE_MAP.items():
            if cat_key.lower() in category.lower():
                return gtype
        return "experience"

    def _compute_perceived_gap(
        self,
        atom_input: AtomInput,
        good_type: str,
    ) -> Dict[str, float]:
        """
        Compute user's PERCEIVED information gap.

        Objective asymmetry (good type) × subjective perception (NDF).
        """
        ad_context = atom_input.ad_context or {}
        # Use PsychologicalConstructResolver — prefers graph/expanded types over NDF
        psy = PsychologicalConstructResolver(atom_input)

        base_asymmetry = GOOD_TYPE_MECHANISMS[good_type]["asymmetry_level"]

        # Psychological construct adjustments to perceived gap
        perceived = base_asymmetry
        if psy.has_any:
            # High uncertainty tolerance → smaller perceived gap
            ut = psy.uncertainty_tolerance
            perceived -= (ut - 0.5) * 0.3

            # High cognitive engagement → wants to close the gap
            ce = psy.cognitive_engagement
            gap_closing_drive = ce * 0.3

            # Low approach → more cautious about gap
            aa = psy.approach_avoidance
            perceived += (0.5 - aa) * 0.2

        perceived = max(0.1, min(0.95, perceived))

        # Information-seeking drive: how motivated to close the gap
        info_drive = 0.5
        if psy.has_any:
            info_drive = 0.3 + psy.cognitive_engagement * 0.4 + \
                         (0.5 - psy.uncertainty_tolerance) * 0.2
            info_drive = max(0.1, min(0.95, info_drive))

        return {
            "objective_asymmetry": base_asymmetry,
            "perceived_gap": perceived,
            "information_seeking_drive": info_drive,
            "good_type": good_type,
            "strategy": "reduce_gap" if perceived > 0.6 else "leverage_gap",
        }

    def _compute_mechanism_adjustments(
        self,
        gap_profile: Dict[str, float],
    ) -> Dict[str, float]:
        """Convert information gap analysis to mechanism adjustments."""
        good_type = gap_profile["good_type"]
        perceived = gap_profile["perceived_gap"]
        strategy = gap_profile["strategy"]

        type_profile = GOOD_TYPE_MECHANISMS[good_type]
        adjustments = {}

        # Apply good-type mechanism boosts/penalties
        for mech, adj in type_profile.get("mechanism_boosts", {}).items():
            adjustments[mech] = adj * (0.5 + perceived)

        for mech, adj in type_profile.get("mechanism_penalties", {}).items():
            adjustments[mech] = adj * (0.5 + perceived)

        # Strategy-specific adjustments
        if strategy == "reduce_gap":
            # User needs information → boost info-providing mechanisms
            adjustments["authority"] = adjustments.get("authority", 0) + 0.1
            adjustments["social_proof"] = adjustments.get("social_proof", 0) + 0.1
            adjustments["commitment"] = adjustments.get("commitment", 0) + 0.05
        else:
            # User is comfortable → can use desire-based mechanisms
            adjustments["scarcity"] = adjustments.get("scarcity", 0) + 0.1
            adjustments["mimetic_desire"] = adjustments.get("mimetic_desire", 0) + 0.1
            adjustments["identity_construction"] = adjustments.get("identity_construction", 0) + 0.1

        return adjustments

    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build information asymmetry output."""
        ad_context = atom_input.ad_context or {}
        category = ad_context.get("category", "")

        good_type = self._classify_good_type(category)
        gap_profile = self._compute_perceived_gap(atom_input, good_type)
        mechanism_adjustments = self._compute_mechanism_adjustments(gap_profile)

        # DSP category moderation: adjust mechanisms by product category effectiveness
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            mechanism_adjustments = CategoryModerationHelper.apply(mechanism_adjustments, dsp)

        primary = f"{good_type}_good_{gap_profile['strategy']}"

        sorted_mechs = sorted(mechanism_adjustments.items(), key=lambda x: x[1], reverse=True)
        recommended = [m for m, s in sorted_mechs[:3] if s > 0]

        confidence = 0.6 + abs(gap_profile["perceived_gap"] - 0.5) * 0.4

        fusion_result.assessment = primary
        fusion_result.confidence = confidence

        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary,
            secondary_assessments={
                "information_gap_profile": gap_profile,
                "mechanism_adjustments": mechanism_adjustments,
            },
            recommended_mechanisms=recommended,
            mechanism_weights={m: max(0.1, 0.5 + mechanism_adjustments.get(m, 0))
                             for m in recommended} if recommended else {"authority": 0.5},
            inferred_states={
                "perceived_gap": gap_profile["perceived_gap"],
                "info_drive": gap_profile["information_seeking_drive"],
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
