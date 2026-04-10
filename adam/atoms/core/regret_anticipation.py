# =============================================================================
# ADAM Regret Anticipation Atom
# Location: adam/atoms/core/regret_anticipation.py
# =============================================================================

"""
REGRET ANTICIPATION ATOM

Grounded in Regret Theory (Loomes & Sugden, 1982) and Anticipated Regret
(Zeelenberg, 1999). Models how anticipated regret of action vs inaction
influences purchase decisions and determines optimal framing.

Key insight: People don't just evaluate outcomes — they anticipate HOW THEY
WILL FEEL about their decision. Anticipated regret of inaction ("I'll kick
myself if I don't buy this") is psychologically different from anticipated
regret of action ("What if I waste my money?"). The ratio between these
two determines whether urgency/scarcity or reassurance/guarantee mechanisms
will be more effective.

Academic Foundation:
- Loomes & Sugden (1982): Regret Theory — formal alternative to expected utility
- Bell (1982): Regret in Decision Making Under Uncertainty
- Zeelenberg (1999): Anticipated Regret & behavioral intentions
- Connolly & Zeelenberg (2002): Regret in Decision Making
- Simonson (1992): Compromise Effect — regret avoidance in choice sets
- Inman & Zeelenberg (2002): Regret of action vs inaction asymmetries
"""

import logging
import math
from typing import Dict, List, Optional, Tuple

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
# REGRET PARAMETERS
# =============================================================================

# Category-level regret asymmetry profiles
# action_regret_weight: how much regret of buying dominates
# inaction_regret_weight: how much regret of NOT buying dominates
CATEGORY_REGRET_PROFILES = {
    "Electronics": {"action": 0.6, "inaction": 0.4, "reversibility": 0.5},
    "Fashion": {"action": 0.3, "inaction": 0.7, "reversibility": 0.6},
    "Health": {"action": 0.7, "inaction": 0.3, "reversibility": 0.2},
    "Food": {"action": 0.2, "inaction": 0.8, "reversibility": 0.9},
    "Software": {"action": 0.5, "inaction": 0.5, "reversibility": 0.7},
    "Automotive": {"action": 0.8, "inaction": 0.2, "reversibility": 0.1},
    "Travel": {"action": 0.25, "inaction": 0.75, "reversibility": 0.15},
    "Luxury": {"action": 0.55, "inaction": 0.45, "reversibility": 0.3},
    "Home": {"action": 0.55, "inaction": 0.45, "reversibility": 0.4},
    "Subscription": {"action": 0.35, "inaction": 0.65, "reversibility": 0.8},
}

# NDF dimension → regret type mapping
# approach_avoidance: High approach → inaction regret dominates (they want things)
# uncertainty_tolerance: Low UT → action regret dominates (fear of bad choice)
# temporal_horizon: Short horizon → inaction regret (FOMO); Long → action regret (buyer's remorse)
# status_sensitivity: High → inaction regret for aspirational; action regret for wasteful
NDF_REGRET_WEIGHTS = {
    "approach_avoidance": {"inaction": 0.3, "action": -0.3},
    "uncertainty_tolerance": {"inaction": -0.2, "action": 0.2},
    "temporal_horizon": {"inaction": -0.2, "action": 0.2},
    "arousal_seeking": {"inaction": 0.25, "action": -0.25},
    "status_sensitivity": {"inaction": 0.15, "action": -0.05},
    "cognitive_engagement": {"inaction": -0.1, "action": 0.15},
}

# Regret type → mechanism effectiveness mapping
# Inaction regret → urgency mechanisms work well
# Action regret → reassurance mechanisms work well
REGRET_MECHANISM_MAP = {
    "inaction_dominant": {
        "scarcity": 0.2,
        "social_proof": 0.15,
        "mimetic_desire": 0.15,
        "attention_dynamics": 0.1,
        "temporal_construal": 0.1,
        # These should be reduced
        "commitment": -0.05,
        "authority": -0.05,
    },
    "action_dominant": {
        "commitment": 0.2,
        "authority": 0.15,
        "social_proof": 0.1,
        "regulatory_focus": 0.1,  # Prevention framing
        # These should be reduced
        "scarcity": -0.15,
        "attention_dynamics": -0.05,
    },
    "balanced": {
        "social_proof": 0.1,
        "commitment": 0.05,
        "regulatory_focus": 0.05,
    },
}


class RegretAnticipationAtom(BaseAtom):
    """
    Models anticipated regret to optimize persuasion framing.

    This atom determines whether the user is more likely to:
    - Regret ACTING (buyer's remorse) → use reassurance mechanisms
    - Regret NOT ACTING (FOMO) → use urgency/scarcity mechanisms

    The balance between these two drives the entire persuasion strategy.
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
        """Query category-level regret patterns."""
        try:
            ad_context = atom_input.ad_context or {}
            category = ad_context.get("category", "")

            for cat_key, profile in CATEGORY_REGRET_PROFILES.items():
                if cat_key.lower() in category.lower():
                    dominant = "inaction" if profile["inaction"] > profile["action"] else "action"
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

    def _compute_regret_balance(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        Compute the action vs inaction regret balance.

        Uses NDF profile + category priors + upstream state.

        Returns:
            Dict with regret scores and balance metrics
        """
        ad_context = atom_input.ad_context or {}
        # Use PsychologicalConstructResolver — prefers graph/expanded types over NDF
        psy = PsychologicalConstructResolver(atom_input)
        psy_dict = psy.as_full_construct_dict()
        category = ad_context.get("category", "")

        # Start with category prior
        cat_profile = None
        for cat_key, profile in CATEGORY_REGRET_PROFILES.items():
            if cat_key.lower() in category.lower():
                cat_profile = profile
                break

        action_regret = cat_profile["action"] if cat_profile else 0.5
        inaction_regret = cat_profile["inaction"] if cat_profile else 0.5
        reversibility = cat_profile["reversibility"] if cat_profile else 0.5

        # Adjust by psychological construct dimensions (graph/expanded type preferred over NDF)
        if psy.has_any:
            for dim, weights in NDF_REGRET_WEIGHTS.items():
                dim_value = psy_dict.get(dim, 0.5)
                deviation = dim_value - 0.5
                action_regret += deviation * weights.get("action", 0)
                inaction_regret += deviation * weights.get("inaction", 0)

        # Normalize to probabilities
        total = action_regret + inaction_regret
        if total > 0:
            action_regret /= total
            inaction_regret /= total
        else:
            action_regret = 0.5
            inaction_regret = 0.5

        # Upstream arousal influences regret intensity
        us_output = atom_input.get_upstream("atom_user_state")
        regret_intensity = 0.5
        if us_output and us_output.inferred_states:
            arousal = us_output.inferred_states.get("arousal", 0.5)
            regret_intensity = 0.3 + arousal * 0.5

        # Compute regret balance
        balance = inaction_regret - action_regret  # Positive = inaction dominant

        return {
            "action_regret": action_regret,
            "inaction_regret": inaction_regret,
            "regret_balance": balance,
            "regret_intensity": regret_intensity,
            "decision_reversibility": reversibility,
            "dominant_type": "inaction" if balance > 0.05 else ("action" if balance < -0.05 else "balanced"),
        }

    def _compute_mechanism_adjustments(
        self,
        regret_profile: Dict[str, float],
    ) -> Dict[str, float]:
        """Convert regret profile to mechanism weight adjustments."""
        dominant = regret_profile["dominant_type"]
        intensity = regret_profile["regret_intensity"]
        balance = abs(regret_profile["regret_balance"])

        base_map = REGRET_MECHANISM_MAP.get(
            f"{dominant}_dominant" if dominant != "balanced" else "balanced",
            REGRET_MECHANISM_MAP["balanced"]
        )

        adjustments = {}
        for mechanism, base_adj in base_map.items():
            # Scale adjustment by intensity and balance clarity
            adj = base_adj * intensity * (0.5 + balance)
            adjustments[mechanism] = max(-0.3, min(0.3, adj))

        # Reversibility modulates everything:
        # High reversibility → action regret is lower (can undo)
        reversibility = regret_profile["decision_reversibility"]
        if reversibility > 0.6 and dominant == "action":
            # Reduce action-regret-driven adjustments
            for mech in adjustments:
                adjustments[mech] *= (1.0 - reversibility * 0.5)

        return adjustments

    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build regret anticipation output."""

        regret_profile = self._compute_regret_balance(atom_input)
        mechanism_adjustments = self._compute_mechanism_adjustments(regret_profile)

        # DSP category moderation: adjust mechanisms by product category effectiveness
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            mechanism_adjustments = CategoryModerationHelper.apply(mechanism_adjustments, dsp)

        dominant = regret_profile["dominant_type"]
        primary = f"{dominant}_regret_dominant"

        sorted_mechs = sorted(mechanism_adjustments.items(), key=lambda x: x[1], reverse=True)
        recommended = [m for m, s in sorted_mechs[:3] if s > 0]

        confidence = min(0.85, 0.4 + regret_profile["regret_intensity"] * 0.3 +
                        abs(regret_profile["regret_balance"]) * 0.3)

        fusion_result.assessment = primary
        fusion_result.confidence = confidence

        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary,
            secondary_assessments={
                "regret_profile": regret_profile,
                "mechanism_adjustments": mechanism_adjustments,
                "framing_guidance": {
                    "use_loss_framing": dominant == "inaction",
                    "use_reassurance": dominant == "action",
                    "urgency_appropriate": dominant == "inaction" and regret_profile["regret_intensity"] > 0.5,
                    "guarantee_needed": dominant == "action" and regret_profile["action_regret"] > 0.6,
                },
            },
            recommended_mechanisms=recommended,
            mechanism_weights={m: max(0.1, 0.5 + mechanism_adjustments.get(m, 0))
                             for m in recommended} if recommended else {"social_proof": 0.5},
            inferred_states={
                "action_regret": regret_profile["action_regret"],
                "inaction_regret": regret_profile["inaction_regret"],
                "regret_intensity": regret_profile["regret_intensity"],
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
