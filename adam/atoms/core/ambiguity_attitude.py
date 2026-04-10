# =============================================================================
# ADAM Ambiguity Attitude Atom
# Location: adam/atoms/core/ambiguity_attitude.py
# =============================================================================

"""
AMBIGUITY ATTITUDE ATOM

Grounded in Ambiguity Aversion (Ellsberg, 1961) and the distinction
between risk (known probabilities) and ambiguity (unknown probabilities).
Models how the user responds to unknown/uncertain product outcomes and
determines optimal framing strategy.

Key insight: Most consumer decisions involve ambiguity, not risk. The user
doesn't know the exact probability of satisfaction — they face UNKNOWN
unknowns. Ambiguity-averse users need mechanisms that convert ambiguity
to risk (testimonials, guarantees). Ambiguity-tolerant users can be
reached with novelty and exploration framing.

Academic Foundation:
- Ellsberg (1961): Risk, Ambiguity, and the Savage Axioms
- Fox & Tversky (1995): Ambiguity Aversion and Comparative Ignorance
- Heath & Tversky (1991): Preference and Belief — Ambiguity & Competence
- Camerer & Weber (1992): Recent Developments in Ambiguity Models
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


# NDF → Ambiguity attitude mapping
# uncertainty_tolerance is the PRIMARY driver
# cognitive_engagement and approach_avoidance are secondary
NDF_AMBIGUITY_MAP = {
    "uncertainty_tolerance": 0.50,   # Primary: directly maps
    "approach_avoidance": 0.15,      # Approach → ambiguity-tolerant
    "cognitive_engagement": 0.10,    # High CE → ambiguity-seeking (enjoys figuring out)
    "arousal_seeking": 0.15,         # High arousal → tolerant of unknown
    "temporal_horizon": 0.10,        # Long horizon → more tolerant of ambiguity
}

# Ambiguity attitude → mechanism adjustments
AMBIGUITY_MECHANISM_MAP = {
    "ambiguity_averse": {
        # Need certainty-providing mechanisms
        "social_proof": 0.2,        # "Others chose this" reduces ambiguity
        "authority": 0.2,           # Expert validation reduces ambiguity
        "commitment": 0.15,         # Guarantees convert ambiguity to known risk
        "regulatory_focus": 0.1,    # Prevention framing acknowledges concerns
        # Penalize uncertainty-inducing mechanisms
        "scarcity": -0.1,           # Pressure + ambiguity = anxiety
        "attention_dynamics": -0.1,
    },
    "ambiguity_tolerant": {
        # Can handle exploration framing
        "identity_construction": 0.15,  # "Be someone who tries new things"
        "mimetic_desire": 0.15,         # "Others are discovering this"
        "scarcity": 0.1,               # Urgency is acceptable
        "attention_dynamics": 0.1,      # Novelty framing works
        "embodied_cognition": 0.1,      # Sensory exploration
    },
    "ambiguity_seeking": {
        # Actively drawn to the unknown
        "attention_dynamics": 0.2,      # "Something new"
        "embodied_cognition": 0.15,     # "Experience something different"
        "identity_construction": 0.15,  # "Pioneer" identity
        "mimetic_desire": 0.1,
        # Penalize certainty mechanisms — they're boring to these users
        "commitment": -0.1,
        "authority": -0.05,
    },
}


class AmbiguityAttitudeAtom(BaseAtom):
    """
    Assesses user's ambiguity attitude and adapts persuasion accordingly.

    This atom determines:
    1. Ambiguity attitude (averse / tolerant / seeking) from NDF profile
    2. Category-level ambiguity (new product category = more ambiguous)
    3. Mechanism adjustments to match the user's comfort with the unknown
    4. Framing recommendations (certainty vs exploration)
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

    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        return None

    def _compute_ambiguity_attitude(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        Compute user's ambiguity attitude from psychological construct dimensions.
        Prefers graph/expanded type dimensions over NDF.
        """
        ad_context = atom_input.ad_context or {}
        # Use PsychologicalConstructResolver — prefers graph/expanded types over NDF
        psy = PsychologicalConstructResolver(atom_input)
        psy_dict = psy.as_full_construct_dict()

        # Compute ambiguity tolerance score (0 = very averse, 1 = seeking)
        tolerance = 0.5
        if psy.has_any:
            for dim, weight in NDF_AMBIGUITY_MAP.items():
                dim_val = psy_dict.get(dim, 0.5)
                tolerance += (dim_val - 0.5) * weight

        tolerance = max(0.05, min(0.95, tolerance))

        # Classify
        if tolerance < 0.35:
            attitude = "ambiguity_averse"
        elif tolerance > 0.65:
            attitude = "ambiguity_seeking"
        else:
            attitude = "ambiguity_tolerant"

        # Context ambiguity: new/unfamiliar categories are more ambiguous
        category = ad_context.get("category", "")
        is_novel = ad_context.get("is_new_category", False) or \
                   ad_context.get("first_purchase", False)

        context_ambiguity = 0.5
        if is_novel:
            context_ambiguity = 0.8  # New categories are highly ambiguous

        # Combined: user attitude × context
        # Averse user + high ambiguity = critical need for certainty
        ambiguity_gap = context_ambiguity * (1.0 - tolerance)

        return {
            "tolerance_score": tolerance,
            "attitude": attitude,
            "context_ambiguity": context_ambiguity,
            "ambiguity_gap": ambiguity_gap,  # How much the user needs certainty
            "needs_certainty": ambiguity_gap > 0.4,
        }

    def _compute_mechanism_adjustments(
        self,
        ambiguity_profile: Dict[str, float],
    ) -> Dict[str, float]:
        """Convert ambiguity attitude to mechanism adjustments."""
        attitude = ambiguity_profile["attitude"]
        gap = ambiguity_profile["ambiguity_gap"]

        base_map = AMBIGUITY_MECHANISM_MAP.get(attitude, AMBIGUITY_MECHANISM_MAP["ambiguity_tolerant"])

        adjustments = {}
        # Scale adjustments by ambiguity gap intensity
        intensity = 0.5 + gap  # 0.5 to 1.5 multiplier
        for mech, adj in base_map.items():
            adjustments[mech] = adj * intensity

        return adjustments

    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build ambiguity attitude output."""

        profile = self._compute_ambiguity_attitude(atom_input)
        adjustments = self._compute_mechanism_adjustments(profile)

        # DSP category moderation: adjust mechanisms by product category effectiveness
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            adjustments = CategoryModerationHelper.apply(adjustments, dsp)

        primary = profile["attitude"]

        sorted_mechs = sorted(adjustments.items(), key=lambda x: x[1], reverse=True)
        recommended = [m for m, s in sorted_mechs[:3] if s > 0]

        confidence = min(0.85, 0.4 + abs(profile["tolerance_score"] - 0.5) * 0.7)

        fusion_result.assessment = primary
        fusion_result.confidence = confidence

        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary,
            secondary_assessments={
                "ambiguity_profile": profile,
                "mechanism_adjustments": adjustments,
                "framing_guidance": {
                    "certainty_framing": profile["needs_certainty"],
                    "exploration_framing": profile["attitude"] == "ambiguity_seeking",
                    "recommended_language": "certain" if profile["needs_certainty"] else "discover",
                },
            },
            recommended_mechanisms=recommended,
            mechanism_weights={m: max(0.1, 0.5 + adjustments.get(m, 0))
                             for m in recommended} if recommended else {"social_proof": 0.5},
            inferred_states={
                "ambiguity_tolerance": profile["tolerance_score"],
                "ambiguity_gap": profile["ambiguity_gap"],
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
