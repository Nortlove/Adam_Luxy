# =============================================================================
# ADAM Motivational Conflict Atom
# Location: adam/atoms/core/motivational_conflict.py
# =============================================================================

"""
MOTIVATIONAL CONFLICT ATOM

Grounded in Lewin's Force Field Theory (1935) and Miller's Conflict
Theory (1944). Models the approach-avoidance dynamics in purchase
decisions where the user simultaneously wants the product (approach
gradient) and fears the consequences (avoidance gradient).

Key insight: Most purchase decisions involve APPROACH-AVOIDANCE CONFLICT
— wanting the product but fearing the cost, the commitment, or the
possibility of a bad outcome. The approach and avoidance gradients
have different mathematical properties: avoidance is steeper near the
decision point. This means that as the user gets closer to buying,
avoidance INCREASES faster than approach. The optimal strategy depends
on which gradient is currently dominant.

Academic Foundation:
- Lewin (1935): A Dynamic Theory of Personality — force fields
- Miller (1944): Experimental Studies of Conflict — gradient theory
- Hovland & Sears (1938): Approach-avoidance conflict patterns
- Cacioppo & Berntson (1994): Evaluative Space Model — bivalent motivation
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
from adam.atoms.core.dsp_integration import DSPDataAccessor, SusceptibilityHelper
from adam.atoms.core.construct_resolver import PsychologicalConstructResolver

logger = logging.getLogger(__name__)


# Conflict types and resolution strategies
CONFLICT_STRATEGIES = {
    "approach_dominant": {
        "description": "User wants it more than fears it — nudge to close",
        "mechanism_boosts": {
            "scarcity": 0.15,
            "commitment": 0.15,
            "temporal_construal": 0.1,
            "social_proof": 0.05,
        },
        "mechanism_penalties": {
            "authority": -0.05,  # Don't slow them down
        },
    },
    "avoidance_dominant": {
        "description": "Fears outweigh desire — reduce fears first",
        "mechanism_boosts": {
            "commitment": 0.2,       # Guarantees reduce avoidance
            "authority": 0.15,       # Expert validation
            "social_proof": 0.15,    # Others survived buying this
            "reciprocity": 0.1,      # Free trial = zero risk
        },
        "mechanism_penalties": {
            "scarcity": -0.2,        # Pressure amplifies avoidance
            "attention_dynamics": -0.1,
        },
    },
    "balanced_conflict": {
        "description": "Equal approach-avoidance — tip the balance",
        "mechanism_boosts": {
            "identity_construction": 0.15,  # Self-concept tips balance
            "social_proof": 0.1,
            "mimetic_desire": 0.1,
            "regulatory_focus": 0.1,
        },
        "mechanism_penalties": {},
    },
    "double_approach": {
        "description": "Choosing between two desired options",
        "mechanism_boosts": {
            "anchoring": 0.2,          # Differentiate options
            "identity_construction": 0.15,  # Which fits who you are?
            "authority": 0.1,
        },
        "mechanism_penalties": {
            "scarcity": -0.1,
        },
    },
    "double_avoidance": {
        "description": "Forced choice between two unwanted options",
        "mechanism_boosts": {
            "regulatory_focus": 0.2,   # Prevention → choose lesser evil
            "commitment": 0.15,
            "authority": 0.15,
        },
        "mechanism_penalties": {
            "identity_construction": -0.1,  # Don't frame as aspirational
        },
    },
}


class MotivationalConflictAtom(BaseAtom):
    """
    Models approach-avoidance dynamics to resolve purchase conflict.

    This atom:
    1. Estimates approach gradient (how much user wants the product)
    2. Estimates avoidance gradient (how much user fears the consequences)
    3. Classifies conflict type (approach-dominant, avoidance-dominant, etc.)
    4. Determines resolution strategy and mechanism adjustments
    5. Accounts for gradient steepness near decision point (Miller, 1944)
    """

    ATOM_TYPE = AtomType.MOTIVATIONAL_CONFLICT
    ATOM_NAME = "motivational_conflict"
    TARGET_CONSTRUCT = "approach_avoidance_conflict"

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

    def _compute_conflict_gradients(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        Compute approach and avoidance gradients.

        Approach gradient = desire for the product
        Avoidance gradient = fear of consequences

        From NDF:
        - approach_avoidance: directly maps
        - arousal_seeking: high → stronger approach
        - uncertainty_tolerance: low → stronger avoidance
        - status_sensitivity: high → approach for status goods
        - cognitive_engagement: high → analytical avoidance
        """
        ad_context = atom_input.ad_context or {}
        # Use PsychologicalConstructResolver — prefers graph/expanded types over NDF
        psy = PsychologicalConstructResolver(atom_input)

        approach = 0.5
        avoidance = 0.5

        if psy.has_any:
            aa = psy.approach_avoidance
            aas = psy.arousal_seeking
            ut = psy.uncertainty_tolerance
            ss = psy.status_sensitivity
            ce = psy.cognitive_engagement

            approach = 0.2 + aa * 0.3 + aas * 0.2 + ss * 0.15 + (1 - ce) * 0.1
            avoidance = 0.2 + (1 - aa) * 0.2 + (1 - ut) * 0.3 + ce * 0.15 + (1 - aas) * 0.1

        approach = max(0.1, min(0.95, approach))
        avoidance = max(0.1, min(0.95, avoidance))

        # Distance to decision (from upstream or context)
        # Closer to decision → avoidance steepens (Miller, 1944)
        distance = ad_context.get("decision_distance", 0.5)  # 0 = at decision point
        avoidance_steepening = max(0, (1.0 - distance) * 0.2)
        avoidance = min(0.95, avoidance + avoidance_steepening)

        # Conflict intensity
        conflict_intensity = 1.0 - abs(approach - avoidance)

        # Classify
        diff = approach - avoidance
        if diff > 0.15:
            conflict_type = "approach_dominant"
        elif diff < -0.15:
            conflict_type = "avoidance_dominant"
        elif approach > 0.6 and avoidance > 0.6:
            conflict_type = "balanced_conflict"
        elif approach < 0.4 and avoidance < 0.4:
            conflict_type = "double_approach"  # Neither strong approach nor avoidance
        else:
            conflict_type = "balanced_conflict"

        return {
            "approach_gradient": approach,
            "avoidance_gradient": avoidance,
            "conflict_type": conflict_type,
            "conflict_intensity": conflict_intensity,
            "decision_distance": distance,
            "avoidance_steepening": avoidance_steepening,
            "resolution_difficulty": conflict_intensity * (1.0 - distance),
        }

    def _compute_mechanism_adjustments(
        self,
        conflict_profile: Dict[str, float],
    ) -> Dict[str, float]:
        """Convert conflict analysis to mechanism adjustments."""
        conflict_type = conflict_profile["conflict_type"]
        intensity = conflict_profile["conflict_intensity"]

        strategy = CONFLICT_STRATEGIES.get(conflict_type, CONFLICT_STRATEGIES["balanced_conflict"])

        adjustments = {}
        # Scale by conflict intensity
        for mech, adj in strategy["mechanism_boosts"].items():
            adjustments[mech] = adj * (0.5 + intensity * 0.5)

        for mech, adj in strategy["mechanism_penalties"].items():
            adjustments[mech] = adj * (0.5 + intensity * 0.5)

        return adjustments

    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build motivational conflict output."""

        profile = self._compute_conflict_gradients(atom_input)
        adjustments = self._compute_mechanism_adjustments(profile)

        # DSP susceptibility: adjust mechanisms by user decision-style susceptibility
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            adjustments = SusceptibilityHelper.apply(adjustments, dsp)

        primary = profile["conflict_type"]

        sorted_mechs = sorted(adjustments.items(), key=lambda x: x[1], reverse=True)
        recommended = [m for m, s in sorted_mechs[:3] if s > 0]

        confidence = min(0.85, 0.4 + profile["conflict_intensity"] * 0.3 +
                        abs(profile["approach_gradient"] - profile["avoidance_gradient"]) * 0.2)

        fusion_result.assessment = primary
        fusion_result.confidence = confidence

        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary,
            secondary_assessments={
                "conflict_profile": profile,
                "mechanism_adjustments": adjustments,
                "resolution_guidance": {
                    "reduce_avoidance_first": profile["conflict_type"] == "avoidance_dominant",
                    "nudge_to_close": profile["conflict_type"] == "approach_dominant",
                    "use_guarantee": profile["avoidance_gradient"] > 0.6,
                    "use_urgency": profile["approach_gradient"] > 0.6 and profile["avoidance_gradient"] < 0.4,
                },
            },
            recommended_mechanisms=recommended,
            mechanism_weights={m: max(0.1, 0.5 + adjustments.get(m, 0))
                             for m in recommended} if recommended else {"commitment": 0.5},
            inferred_states={
                "approach": profile["approach_gradient"],
                "avoidance": profile["avoidance_gradient"],
                "conflict_intensity": profile["conflict_intensity"],
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
