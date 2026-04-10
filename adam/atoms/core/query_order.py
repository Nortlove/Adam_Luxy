# =============================================================================
# ADAM Query Order Atom
# Location: adam/atoms/core/query_order.py
# =============================================================================

"""
QUERY ORDER ATOM

Grounded in Query Theory (Johnson, Häubl & Keinan, 2007). Models how
the ORDER in which a person considers aspects of a decision determines
the decision outcome — and how to strategically control that order.

Key insight: When deciding whether to buy, consumers internally generate
"queries" (reasons for and against). The ORDER matters enormously —
reasons generated first get disproportionate weight due to output
interference (each retrieved reason makes subsequent retrieval harder,
similar to memory retrieval dynamics). By controlling which queries
the ad triggers FIRST, we can bias the entire evaluation.

Academic Foundation:
- Johnson, Häubl & Keinan (2007): Aspects of Endowment — Query Theory
- Weber et al. (2007): Asymmetric Discounting in Intertemporal Choice
- Hardisty & Weber (2009): Discounting Future Green (Query Theory + environment)
- Johnson & Goldstein (2003): Defaults — Query Theory in policy
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


# =============================================================================
# QUERY TYPES AND THEIR EFFECTS
# =============================================================================

# Pro-purchase queries: reasons TO buy
PRO_QUERIES = {
    "benefit": {
        "description": "What will I gain?",
        "triggering_mechanisms": ["regulatory_focus", "identity_construction"],
        "ndf_triggers": {"approach_avoidance": 0.3, "arousal_seeking": 0.2},
    },
    "social_validation": {
        "description": "Will others approve?",
        "triggering_mechanisms": ["social_proof", "mimetic_desire"],
        "ndf_triggers": {"social_calibration": 0.4, "status_sensitivity": 0.2},
    },
    "opportunity_cost": {
        "description": "What will I miss if I don't?",
        "triggering_mechanisms": ["scarcity", "temporal_construal"],
        "ndf_triggers": {"arousal_seeking": 0.3, "approach_avoidance": 0.2},
    },
    "identity_fit": {
        "description": "Does this match who I am/want to be?",
        "triggering_mechanisms": ["identity_construction", "embodied_cognition"],
        "ndf_triggers": {"status_sensitivity": 0.3, "social_calibration": 0.2},
    },
}

# Anti-purchase queries: reasons NOT to buy
ANTI_QUERIES = {
    "cost_concern": {
        "description": "Is it worth the money?",
        "countering_mechanisms": ["anchoring", "reciprocity"],
        "ndf_triggers": {"uncertainty_tolerance": -0.3, "cognitive_engagement": 0.2},
    },
    "risk_fear": {
        "description": "What if it doesn't work?",
        "countering_mechanisms": ["authority", "commitment", "social_proof"],
        "ndf_triggers": {"uncertainty_tolerance": -0.4, "approach_avoidance": -0.3},
    },
    "decision_delay": {
        "description": "Can I decide later?",
        "countering_mechanisms": ["scarcity", "temporal_construal"],
        "ndf_triggers": {"temporal_horizon": 0.3, "uncertainty_tolerance": 0.2},
    },
    "alternative_search": {
        "description": "Is there something better?",
        "countering_mechanisms": ["anchoring", "identity_construction"],
        "ndf_triggers": {"cognitive_engagement": 0.3, "uncertainty_tolerance": 0.2},
    },
}


class QueryOrderAtom(BaseAtom):
    """
    Controls the order of internal evaluation queries for maximum persuasion.

    This atom determines:
    1. Which queries the user is likely to generate first (from NDF profile)
    2. How to structure the ad to trigger pro-queries before anti-queries
    3. Which mechanisms pre-empt specific anti-queries
    4. Optimal copy structure for query order manipulation

    Output feeds into MessageFraming for copy structure optimization.
    """

    ATOM_TYPE = AtomType.QUERY_ORDER
    ATOM_NAME = "query_order"
    TARGET_CONSTRUCT = "evaluation_sequence"

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

    def _predict_query_order(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        Predict which queries the user will generate first.

        Uses psychological construct dimensions to estimate the probability
        that each query type will be generated early (getting more weight).
        Prefers graph/expanded type dimensions over NDF.
        """
        # Use PsychologicalConstructResolver — prefers graph/expanded types over NDF
        psy = PsychologicalConstructResolver(atom_input)
        psy_dict = psy.as_full_construct_dict()

        pro_scores = {}
        anti_scores = {}

        # Score pro-queries by psychological construct alignment
        for query_id, query_def in PRO_QUERIES.items():
            score = 0.3  # Base probability
            if psy.has_any:
                for dim, weight in query_def["ndf_triggers"].items():
                    dim_val = psy_dict.get(dim, 0.5)
                    score += (dim_val - 0.5) * weight
            pro_scores[query_id] = max(0.05, min(0.95, score))

        # Score anti-queries by psychological construct alignment
        for query_id, query_def in ANTI_QUERIES.items():
            score = 0.3  # Base probability
            if psy.has_any:
                for dim, weight in query_def["ndf_triggers"].items():
                    dim_val = psy_dict.get(dim, 0.5)
                    score += (dim_val - 0.5) * weight
            anti_scores[query_id] = max(0.05, min(0.95, score))

        # Compute aggregate tendency
        avg_pro = sum(pro_scores.values()) / max(1, len(pro_scores))
        avg_anti = sum(anti_scores.values()) / max(1, len(anti_scores))
        pro_first_probability = avg_pro / (avg_pro + avg_anti + 0.001)

        return {
            "pro_query_scores": pro_scores,
            "anti_query_scores": anti_scores,
            "pro_first_probability": pro_first_probability,
            "dominant_pro": max(pro_scores, key=pro_scores.get) if pro_scores else "benefit",
            "dominant_anti": max(anti_scores, key=anti_scores.get) if anti_scores else "cost_concern",
        }

    def _compute_strategy(
        self,
        query_profile: Dict,
    ) -> Dict[str, any]:
        """
        Compute the optimal query order strategy.

        Determines:
        1. What to lead with (trigger strongest pro-query first)
        2. What to pre-empt (counter strongest anti-query before it arises)
        3. Copy structure recommendations
        """
        pro_first = query_profile["pro_first_probability"]
        dominant_pro = query_profile["dominant_pro"]
        dominant_anti = query_profile["dominant_anti"]

        # Strategy depends on natural query order tendency
        if pro_first > 0.6:
            # User naturally thinks of benefits first
            strategy = "amplify_pro"
            approach = "Lead with strongest benefit, stack social proof, close with urgency"
        elif pro_first < 0.4:
            # User naturally thinks of risks first
            strategy = "preempt_anti"
            approach = "Pre-empt biggest concern upfront, then pivot to benefit"
        else:
            # Balanced evaluator
            strategy = "balanced_reframe"
            approach = "Reframe concerns as benefits, integrate social proof throughout"

        # Specific mechanisms for the dominant queries
        lead_mechanisms = PRO_QUERIES.get(dominant_pro, {}).get("triggering_mechanisms", [])
        counter_mechanisms = ANTI_QUERIES.get(dominant_anti, {}).get("countering_mechanisms", [])

        return {
            "strategy": strategy,
            "approach_description": approach,
            "lead_with": dominant_pro,
            "lead_mechanisms": lead_mechanisms,
            "preempt": dominant_anti,
            "preempt_mechanisms": counter_mechanisms,
            "copy_structure": self._get_copy_structure(strategy, dominant_pro, dominant_anti),
        }

    def _get_copy_structure(
        self,
        strategy: str,
        dominant_pro: str,
        dominant_anti: str,
    ) -> List[Dict[str, str]]:
        """Generate copy structure recommendation for MessageFraming."""
        if strategy == "amplify_pro":
            return [
                {"position": "headline", "query_type": dominant_pro, "purpose": "trigger_pro"},
                {"position": "body_1", "query_type": "social_validation", "purpose": "reinforce_pro"},
                {"position": "body_2", "query_type": dominant_anti, "purpose": "address_briefly"},
                {"position": "cta", "query_type": "opportunity_cost", "purpose": "close_with_urgency"},
            ]
        elif strategy == "preempt_anti":
            return [
                {"position": "headline", "query_type": dominant_anti, "purpose": "acknowledge_concern"},
                {"position": "body_1", "query_type": dominant_pro, "purpose": "pivot_to_benefit"},
                {"position": "body_2", "query_type": "social_validation", "purpose": "validate"},
                {"position": "cta", "query_type": "identity_fit", "purpose": "close_with_identity"},
            ]
        else:
            return [
                {"position": "headline", "query_type": dominant_pro, "purpose": "start_positive"},
                {"position": "body_1", "query_type": dominant_anti, "purpose": "reframe_as_benefit"},
                {"position": "body_2", "query_type": "social_validation", "purpose": "reinforce"},
                {"position": "cta", "query_type": "opportunity_cost", "purpose": "close"},
            ]

    def _compute_mechanism_adjustments(
        self,
        query_profile: Dict,
        strategy: Dict,
    ) -> Dict[str, float]:
        """Convert query order analysis to mechanism adjustments."""
        adjustments = {}

        # Boost lead mechanisms
        for mech in strategy.get("lead_mechanisms", []):
            adjustments[mech] = adjustments.get(mech, 0) + 0.15

        # Boost preempt mechanisms
        for mech in strategy.get("preempt_mechanisms", []):
            adjustments[mech] = adjustments.get(mech, 0) + 0.1

        # Pro-first users: boost desire mechanisms
        if query_profile["pro_first_probability"] > 0.6:
            for mech in ["identity_construction", "mimetic_desire", "scarcity"]:
                adjustments[mech] = adjustments.get(mech, 0) + 0.05

        # Anti-first users: boost reassurance mechanisms
        if query_profile["pro_first_probability"] < 0.4:
            for mech in ["authority", "commitment", "social_proof"]:
                adjustments[mech] = adjustments.get(mech, 0) + 0.05

        return adjustments

    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build query order output."""

        query_profile = self._predict_query_order(atom_input)
        strategy = self._compute_strategy(query_profile)
        mechanism_adjustments = self._compute_mechanism_adjustments(
            query_profile, strategy
        )

        # DSP susceptibility: adjust mechanisms by user decision-style susceptibility
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            mechanism_adjustments = SusceptibilityHelper.apply(mechanism_adjustments, dsp)

        primary = strategy["strategy"]

        all_mechs = list(set(
            strategy.get("lead_mechanisms", []) +
            strategy.get("preempt_mechanisms", [])
        ))
        recommended = all_mechs[:3] if all_mechs else ["social_proof"]

        confidence = min(0.8, 0.4 + abs(query_profile["pro_first_probability"] - 0.5) * 0.6)

        fusion_result.assessment = primary
        fusion_result.confidence = confidence

        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary,
            secondary_assessments={
                "query_profile": query_profile,
                "strategy": strategy,
                "mechanism_adjustments": mechanism_adjustments,
            },
            recommended_mechanisms=recommended,
            mechanism_weights={m: max(0.1, 0.5 + mechanism_adjustments.get(m, 0))
                             for m in recommended},
            inferred_states={
                "pro_first_prob": query_profile["pro_first_probability"],
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
