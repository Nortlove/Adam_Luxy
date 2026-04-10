# =============================================================================
# ADAM Cooperative Framing Atom
# Location: adam/atoms/core/cooperative_framing.py
# =============================================================================

"""
COOPERATIVE FRAMING ATOM

Grounded in Cooperative Game Theory (Shapley, 1953) and the theory of
Joint Value Creation. Models the purchase decision as a cooperative game
where brand and consumer create joint value — rather than a zero-sum
adversarial exchange.

Key insight: When consumers perceive the brand-consumer relationship as
cooperative ("we're solving your problem together"), persuasion resistance
drops dramatically. The Friestad & Wright (1994) persuasion knowledge
defenses are tuned for ADVERSARIAL persuasion. Cooperative framing
bypasses these defenses because the consumer doesn't activate skepticism
when they perceive genuine mutual benefit.

Academic Foundation:
- Shapley (1953): A Value for N-person Games
- Nash (1953): Two-Person Cooperative Games
- Prahalad & Ramaswamy (2004): Co-Creation of Value
- Vargo & Lusch (2004): Service-Dominant Logic — value co-creation
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


# Cooperative value dimensions (what the brand is offering beyond the product)
COOPERATIVE_DIMENSIONS = {
    "problem_solving": {
        "description": "Brand helps solve a genuine problem",
        "mechanism_boosts": {"reciprocity": 0.15, "commitment": 0.1, "unity": 0.1},
        "ndf_affinity": {"approach_avoidance": 0.2, "uncertainty_tolerance": -0.1},
    },
    "identity_enhancement": {
        "description": "Brand helps you become who you want to be",
        "mechanism_boosts": {"identity_construction": 0.2, "mimetic_desire": 0.1},
        "ndf_affinity": {"status_sensitivity": 0.3, "social_calibration": 0.1},
    },
    "community_belonging": {
        "description": "Brand connects you with like-minded people",
        "mechanism_boosts": {"unity": 0.2, "social_proof": 0.15},
        "ndf_affinity": {"social_calibration": 0.3, "approach_avoidance": 0.1},
    },
    "knowledge_sharing": {
        "description": "Brand educates and empowers",
        "mechanism_boosts": {"authority": 0.15, "reciprocity": 0.15},
        "ndf_affinity": {"cognitive_engagement": 0.3, "uncertainty_tolerance": 0.1},
    },
    "empathy_alignment": {
        "description": "Brand genuinely understands your situation",
        "mechanism_boosts": {"reciprocity": 0.2, "unity": 0.15, "embodied_cognition": 0.1},
        "ndf_affinity": {"social_calibration": 0.2, "approach_avoidance": -0.2},
    },
}


class CooperativeFramingAtom(BaseAtom):
    """
    Frames the brand-consumer interaction as cooperative value creation.

    This atom determines:
    1. Which cooperative dimension best fits the brand/user combination
    2. How to frame the ad as a cooperative invitation vs a sales pitch
    3. The "Shapley value" of the interaction — perceived joint surplus
    4. Mechanism adjustments that reinforce cooperative framing

    This is strategically important because cooperative framing BYPASSES
    persuasion knowledge defenses (see StrategicAwarenessAtom).
    """

    ATOM_TYPE = AtomType.COOPERATIVE_FRAMING
    ATOM_NAME = "cooperative_framing"
    TARGET_CONSTRUCT = "cooperative_value"

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

    def _compute_cooperative_fit(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, Dict]:
        """
        Score how well each cooperative dimension fits the user-brand pair.
        """
        ad_context = atom_input.ad_context or {}
        # Use PsychologicalConstructResolver — prefers graph/expanded types over NDF
        psy = PsychologicalConstructResolver(atom_input)
        psy_dict = psy.as_full_construct_dict()

        fits = {}
        for dim_id, dim_def in COOPERATIVE_DIMENSIONS.items():
            score = 0.3  # Base

            # Psychological construct alignment (graph/expanded type preferred over NDF)
            if psy.has_any:
                for psy_dim, weight in dim_def["ndf_affinity"].items():
                    val = psy_dict.get(psy_dim, 0.5)
                    score += (val - 0.5) * weight

            # Brand context alignment
            desc = (ad_context.get("brand_description", "") +
                    ad_context.get("product_description", "")).lower()

            # Simple keyword matching for cooperative signals
            coop_keywords = {
                "problem_solving": ["solution", "solve", "help", "fix", "improve"],
                "identity_enhancement": ["become", "aspire", "transform", "elevate", "style"],
                "community_belonging": ["community", "together", "join", "belong", "member"],
                "knowledge_sharing": ["learn", "guide", "education", "empower", "discover"],
                "empathy_alignment": ["understand", "care", "support", "we know", "been there"],
            }

            keywords = coop_keywords.get(dim_id, [])
            brand_match = sum(1 for k in keywords if k in desc) / max(1, len(keywords))
            score += brand_match * 0.3

            fits[dim_id] = {
                "score": max(0.05, min(0.95, score)),
                "mechanism_boosts": dim_def["mechanism_boosts"],
            }

        return fits

    def _compute_joint_surplus(
        self,
        cooperative_fits: Dict[str, Dict],
        atom_input: AtomInput,
    ) -> float:
        """
        Compute the perceived "joint surplus" — how much both sides benefit.

        Higher joint surplus → stronger cooperative framing → lower resistance.
        """
        if not cooperative_fits:
            return 0.3

        best_fit = max(cooperative_fits.values(), key=lambda x: x["score"])
        best_score = best_fit["score"]

        # Upstream persuasion knowledge (from strategic_awareness atom if available)
        pk_level = 0.5
        sa_output = atom_input.get_upstream("atom_strategic_awareness")
        if sa_output and sa_output.secondary_assessments:
            pk_level = sa_output.secondary_assessments.get("pk_level", 0.5)

        # Joint surplus is inversely related to PK when cooperative framing is strong
        # High cooperative fit + high PK = joint surplus bridges the resistance gap
        surplus = best_score * (0.5 + pk_level * 0.3)  # PK helps when coop is genuine
        return max(0.1, min(0.95, surplus))

    def _compute_mechanism_adjustments(
        self,
        cooperative_fits: Dict[str, Dict],
        joint_surplus: float,
    ) -> Dict[str, float]:
        """Convert cooperative framing to mechanism adjustments."""
        adjustments = {}

        # Aggregate mechanism boosts from top cooperative dimensions
        sorted_dims = sorted(
            cooperative_fits.items(), key=lambda x: x[1]["score"], reverse=True
        )

        for dim_id, dim_data in sorted_dims[:2]:  # Top 2 cooperative dimensions
            score = dim_data["score"]
            for mech, boost in dim_data["mechanism_boosts"].items():
                adj = boost * score * (0.5 + joint_surplus * 0.5)
                adjustments[mech] = adjustments.get(mech, 0) + adj

        # Cooperative framing globally reduces need for aggressive mechanisms
        if joint_surplus > 0.5:
            adjustments["scarcity"] = adjustments.get("scarcity", 0) - 0.1
            adjustments["attention_dynamics"] = adjustments.get("attention_dynamics", 0) - 0.05

        return adjustments

    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build cooperative framing output."""

        cooperative_fits = self._compute_cooperative_fit(atom_input)
        joint_surplus = self._compute_joint_surplus(cooperative_fits, atom_input)
        adjustments = self._compute_mechanism_adjustments(cooperative_fits, joint_surplus)

        # DSP category moderation: adjust mechanisms by product category effectiveness
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            adjustments = CategoryModerationHelper.apply(adjustments, dsp)

        # Best cooperative dimension
        best_dim = max(cooperative_fits.items(), key=lambda x: x[1]["score"])
        primary = best_dim[0]

        sorted_mechs = sorted(adjustments.items(), key=lambda x: x[1], reverse=True)
        recommended = [m for m, s in sorted_mechs[:3] if s > 0]

        confidence = min(0.85, 0.4 + joint_surplus * 0.4)

        fusion_result.assessment = primary
        fusion_result.confidence = confidence

        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary,
            secondary_assessments={
                "cooperative_fits": {k: v["score"] for k, v in cooperative_fits.items()},
                "joint_surplus": joint_surplus,
                "mechanism_adjustments": adjustments,
                "framing_guidance": {
                    "cooperative_dimension": primary,
                    "cooperative_language": True,
                    "avoid_adversarial": joint_surplus > 0.5,
                },
            },
            recommended_mechanisms=recommended,
            mechanism_weights={m: max(0.1, 0.5 + adjustments.get(m, 0))
                             for m in recommended} if recommended else {"reciprocity": 0.5},
            inferred_states={
                "joint_surplus": joint_surplus,
                **{f"coop_{k}": v["score"] for k, v in cooperative_fits.items()},
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
