# =============================================================================
# ADAM Temporal Self Atom
# Location: adam/atoms/core/temporal_self.py
# =============================================================================

"""
TEMPORAL SELF ATOM

Grounded in the philosophy of personal identity over time (Parfit, 1984)
and Hershfield's Future Self-Continuity research (2011). Models how
connected or disconnected the user feels from their future self, and
how this affects present-moment decision-making.

Key insight: People who feel DISCONNECTED from their future self treat
their future self like a stranger — they discount future outcomes heavily
and respond to immediate gratification. People who feel CONNECTED to their
future self make decisions that serve long-term interests. This has
profound implications for which mechanisms work: urgency/scarcity for
disconnected; investment/identity framing for connected.

Academic Foundation:
- Parfit (1984): Reasons and Persons — personal identity over time
- Hershfield (2011): Future self-continuity and financial decisions
- Hershfield et al. (2011): Increasing saving behavior through age-progressed self
- Frederick, Loewenstein & O'Donoghue (2002): Time discounting review
- Bartels & Urminsky (2011): On intertemporal selfishness
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


# Future self-continuity → mechanism mapping
CONTINUITY_MECHANISMS = {
    "high_continuity": {
        # Sees future self as continuous with present → investment framing
        "identity_construction": 0.2,
        "temporal_construal": 0.15,
        "commitment": 0.15,
        "authority": 0.05,
        # Urgency less needed
        "scarcity": -0.1,
        "attention_dynamics": -0.05,
    },
    "low_continuity": {
        # Future self is a stranger → present-focused mechanisms
        "scarcity": 0.2,
        "attention_dynamics": 0.15,
        "embodied_cognition": 0.15,
        "mimetic_desire": 0.1,
        "social_proof": 0.1,
        # Investment framing won't work
        "temporal_construal": -0.15,
        "commitment": -0.1,
    },
    "moderate_continuity": {
        "social_proof": 0.1,
        "identity_construction": 0.1,
        "regulatory_focus": 0.1,
        "commitment": 0.05,
    },
}

# Category temporal profiles
CATEGORY_TEMPORAL = {
    "Health": {"future_relevance": 0.9, "continuity_boost": 0.1},
    "Financial": {"future_relevance": 0.95, "continuity_boost": 0.15},
    "Education": {"future_relevance": 0.85, "continuity_boost": 0.1},
    "Insurance": {"future_relevance": 0.9, "continuity_boost": 0.1},
    "Food": {"future_relevance": 0.2, "continuity_boost": -0.1},
    "Entertainment": {"future_relevance": 0.15, "continuity_boost": -0.15},
    "Fashion": {"future_relevance": 0.3, "continuity_boost": -0.05},
    "Electronics": {"future_relevance": 0.5, "continuity_boost": 0.0},
    "Subscription": {"future_relevance": 0.7, "continuity_boost": 0.05},
}


class TemporalSelfAtom(BaseAtom):
    """
    Models future self-continuity to optimize temporal framing.

    This atom:
    1. Estimates how connected the user feels to their future self
    2. Determines whether present-focused or future-focused framing
    3. Calibrates time discounting for mechanism selection
    4. Adjusts copy framing (immediate reward vs long-term investment)
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

    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        return None

    def _estimate_future_self_continuity(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        Estimate future self-continuity from NDF profile.

        NDF mapping:
        - temporal_horizon: PRIMARY indicator (long horizon → high continuity)
        - cognitive_engagement: HIGH → connected (thinks about consequences)
        - approach_avoidance: HIGH approach → present-focused (low continuity)
        - arousal_seeking: HIGH → present-focused (low continuity)
        """
        ad_context = atom_input.ad_context or {}
        # Use PsychologicalConstructResolver — prefers graph/expanded types over NDF
        psy = PsychologicalConstructResolver(atom_input)
        category = ad_context.get("category", "")

        continuity = 0.5
        if psy.has_any:
            th = psy.temporal_horizon
            ce = psy.cognitive_engagement
            aa = psy.approach_avoidance
            aas = psy.arousal_seeking

            continuity = (
                0.15 +
                th * 0.35 +          # Primary driver
                ce * 0.2 +           # Thoughtful → connected
                (1 - aas) * 0.15 +   # Low arousal seeking → future-oriented
                (1 - aa) * 0.1       # Cautious → future-oriented
            )

        # Category adjustment
        for cat_key, profile in CATEGORY_TEMPORAL.items():
            if cat_key.lower() in category.lower():
                continuity += profile["continuity_boost"]
                break

        continuity = max(0.05, min(0.95, continuity))

        # Discount rate: inverse of continuity
        # High continuity → low discount → patient
        discount_rate = 1.0 - continuity

        # Classify
        if continuity > 0.65:
            level = "high_continuity"
        elif continuity > 0.35:
            level = "moderate_continuity"
        else:
            level = "low_continuity"

        return {
            "continuity": continuity,
            "discount_rate": discount_rate,
            "level": level,
            "future_relevance": next(
                (p["future_relevance"] for k, p in CATEGORY_TEMPORAL.items()
                 if k.lower() in category.lower()),
                0.5
            ),
        }

    def _compute_mechanism_adjustments(
        self,
        temporal_profile: Dict[str, float],
    ) -> Dict[str, float]:
        """Convert temporal self analysis to mechanism adjustments."""
        level = temporal_profile["level"]
        continuity = temporal_profile["continuity"]

        base_map = CONTINUITY_MECHANISMS.get(level, CONTINUITY_MECHANISMS["moderate_continuity"])

        adjustments = {}
        intensity = 0.5 + abs(continuity - 0.5)
        for mech, adj in base_map.items():
            adjustments[mech] = adj * intensity

        # Special: if category has high future relevance but user has low continuity,
        # we need to BRIDGE the gap — make the future feel present
        if temporal_profile["future_relevance"] > 0.7 and continuity < 0.4:
            adjustments["embodied_cognition"] = adjustments.get("embodied_cognition", 0) + 0.15
            adjustments["identity_construction"] = adjustments.get("identity_construction", 0) + 0.1
            adjustments["social_proof"] = adjustments.get("social_proof", 0) + 0.1

        return adjustments

    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build temporal self output."""

        profile = self._estimate_future_self_continuity(atom_input)
        adjustments = self._compute_mechanism_adjustments(profile)

        # DSP category moderation: adjust mechanisms by product category effectiveness
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            adjustments = CategoryModerationHelper.apply(adjustments, dsp)

        primary = profile["level"]

        sorted_mechs = sorted(adjustments.items(), key=lambda x: x[1], reverse=True)
        recommended = [m for m, s in sorted_mechs[:3] if s > 0]

        confidence = min(0.85, 0.4 + abs(profile["continuity"] - 0.5) * 0.7)

        fusion_result.assessment = primary
        fusion_result.confidence = confidence

        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary,
            secondary_assessments={
                "temporal_profile": profile,
                "mechanism_adjustments": adjustments,
                "framing_guidance": {
                    "use_future_framing": profile["continuity"] > 0.6,
                    "use_present_framing": profile["continuity"] < 0.4,
                    "bridge_temporal_gap": profile["future_relevance"] > 0.7 and profile["continuity"] < 0.4,
                },
            },
            recommended_mechanisms=recommended,
            mechanism_weights={m: max(0.1, 0.5 + adjustments.get(m, 0))
                             for m in recommended} if recommended else {"social_proof": 0.5},
            inferred_states={
                "future_self_continuity": profile["continuity"],
                "discount_rate": profile["discount_rate"],
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
