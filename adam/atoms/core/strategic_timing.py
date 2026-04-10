# =============================================================================
# ADAM Strategic Timing Atom
# Location: adam/atoms/core/strategic_timing.py
# =============================================================================

"""
STRATEGIC TIMING ATOM

Grounded in Option Value Theory (Dixit & Pindyck, 1994) and the theory
of Optimal Stopping (Ferguson, 2006). Models the decision to act NOW
vs wait, and determines when urgency is appropriate vs when patience
signals are more effective.

Key insight: Every purchase has an "option value of waiting" — the value
of keeping the decision open. When the cost of delay is low, urgency
mechanisms backfire because they signal the seller's desperation.
When the option value of waiting is genuinely low (limited stock, rising
prices, seasonal), urgency is authentic and effective.

Academic Foundation:
- Dixit & Pindyck (1994): Investment Under Uncertainty — real options theory
- Ferguson (2006): Optimal Stopping and Applications
- Ariely & Wertenbroch (2002): Procrastination, Deadlines, Performance
- Shu & Gneezy (2010): Procrastination of Enjoyable Experiences
"""

import logging
from datetime import datetime
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


# Option value drivers (higher = more reason to wait)
OPTION_VALUE_FACTORS = {
    "price_volatility": {
        "description": "Price likely to change?",
        "categories": {
            "Electronics": 0.7,   # Prices drop fast
            "Fashion": 0.6,      # Sales cycles
            "Travel": 0.8,       # Highly volatile
            "Subscription": 0.2, # Stable pricing
            "Food": 0.1,         # Low volatility
            "Automotive": 0.5,
            "Health": 0.3,
        },
    },
    "new_alternatives": {
        "description": "Better options likely to emerge?",
        "categories": {
            "Electronics": 0.8,  # Constant innovation
            "Software": 0.7,
            "Fashion": 0.5,
            "Food": 0.1,
            "Health": 0.3,
            "Automotive": 0.6,
        },
    },
    "decision_reversibility": {
        "description": "Can undo the decision?",
        "categories": {
            "Subscription": 0.9,  # Easy to cancel
            "Fashion": 0.7,      # Returns usually possible
            "Electronics": 0.6,
            "Travel": 0.2,       # Hard to undo
            "Automotive": 0.1,
            "Tattoo": 0.0,
        },
    },
}

# Timing strategy → mechanism mapping
TIMING_MECHANISMS = {
    "act_now": {
        "scarcity": 0.2,
        "temporal_construal": 0.15,
        "attention_dynamics": 0.1,
        "social_proof": 0.05,
        "commitment": -0.1,  # Don't emphasize long-term when pushing now
    },
    "build_conviction": {
        "commitment": 0.2,
        "authority": 0.15,
        "identity_construction": 0.1,
        "social_proof": 0.1,
        "scarcity": -0.15,  # Don't rush — builds resistance
    },
    "create_urgency": {
        "scarcity": 0.25,
        "regulatory_focus": 0.15,  # Loss framing
        "social_proof": 0.1,
        "temporal_construal": 0.1,
    },
}


class StrategicTimingAtom(BaseAtom):
    """
    Determines optimal timing strategy for persuasion.

    This atom answers: "Should we push for immediate action, or is the
    user better served (and more likely to convert) with a patient,
    conviction-building approach?"

    Uses option value analysis + NDF temporal dimensions.
    """

    ATOM_TYPE = AtomType.STRATEGIC_TIMING
    ATOM_NAME = "strategic_timing"
    TARGET_CONSTRUCT = "decision_timing"

    REQUIRED_SOURCES = [
        IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
        IntelligenceSourceType.EMPIRICAL_PATTERNS,
    ]

    OPTIONAL_SOURCES = [
        IntelligenceSourceType.TEMPORAL_PATTERNS,
        IntelligenceSourceType.MECHANISM_TRAJECTORIES,
    ]

    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        return None

    def _compute_option_value(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        Compute the option value of waiting.

        High option value = user should wait → urgency backfires
        Low option value = user should act → urgency is appropriate
        """
        ad_context = atom_input.ad_context or {}
        category = ad_context.get("category", "")

        # Category-level option value components
        factor_scores = {}
        for factor, data in OPTION_VALUE_FACTORS.items():
            score = 0.5
            for cat_key, cat_score in data["categories"].items():
                if cat_key.lower() in category.lower():
                    score = cat_score
                    break
            factor_scores[factor] = score

        # Aggregate option value
        option_value = sum(factor_scores.values()) / max(1, len(factor_scores))

        # Context modifiers
        has_promotion = ad_context.get("has_promotion", False)
        limited_stock = ad_context.get("limited_stock", False)
        seasonal = ad_context.get("seasonal", False)

        if has_promotion:
            option_value *= 0.6  # Promotion reduces option value of waiting
        if limited_stock:
            option_value *= 0.4  # Genuine scarcity
        if seasonal:
            option_value *= 0.7  # Seasonal relevance

        return {
            "option_value": max(0.05, min(0.95, option_value)),
            "factor_scores": factor_scores,
            "urgency_appropriate": option_value < 0.4,
            "patience_needed": option_value > 0.6,
        }

    def _compute_user_timing_preference(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """Compute user's inherent timing preference from NDF."""
        ad_context = atom_input.ad_context or {}
        # Use PsychologicalConstructResolver — prefers graph/expanded types over NDF
        psy = PsychologicalConstructResolver(atom_input)

        # temporal_horizon: high = patient, low = impulsive
        # arousal_seeking: high = wants stimulation now
        # approach_avoidance: high approach = acts fast
        # uncertainty_tolerance: low = decides fast to reduce uncertainty

        impulsivity = 0.5
        if psy.has_any:
            th = psy.temporal_horizon
            aas = psy.arousal_seeking
            aa = psy.approach_avoidance
            ut = psy.uncertainty_tolerance

            impulsivity = (
                (1.0 - th) * 0.3 +  # Short horizon → impulsive
                aas * 0.25 +          # High arousal seeking → impulsive
                aa * 0.25 +           # High approach → impulsive
                (1.0 - ut) * 0.2      # Low uncertainty tolerance → decides fast
            )

        impulsivity = max(0.05, min(0.95, impulsivity))

        return {
            "impulsivity": impulsivity,
            "prefers_immediate": impulsivity > 0.6,
            "prefers_deliberation": impulsivity < 0.4,
        }

    def _determine_timing_strategy(
        self,
        option_value: Dict,
        user_timing: Dict,
    ) -> str:
        """Determine the optimal timing strategy."""
        ov = option_value["option_value"]
        imp = user_timing["impulsivity"]

        if ov < 0.4 and imp > 0.5:
            return "act_now"  # Low OV + impulsive user → push now
        elif ov > 0.6:
            return "build_conviction"  # High OV → patience
        elif imp > 0.6:
            return "create_urgency"  # Impulsive user → urgency even if moderate OV
        else:
            return "build_conviction"  # Default to patience

    def _compute_mechanism_adjustments(
        self,
        strategy: str,
    ) -> Dict[str, float]:
        """Convert timing strategy to mechanism adjustments."""
        return TIMING_MECHANISMS.get(strategy, TIMING_MECHANISMS["build_conviction"])

    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build strategic timing output."""

        option_value = self._compute_option_value(atom_input)
        user_timing = self._compute_user_timing_preference(atom_input)
        strategy = self._determine_timing_strategy(option_value, user_timing)
        adjustments = self._compute_mechanism_adjustments(strategy)

        # DSP category moderation: adjust mechanisms by product category effectiveness
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            adjustments = CategoryModerationHelper.apply(adjustments, dsp)

        sorted_mechs = sorted(adjustments.items(), key=lambda x: x[1], reverse=True)
        recommended = [m for m, s in sorted_mechs[:3] if s > 0]

        confidence = min(0.8, 0.4 +
                        abs(option_value["option_value"] - 0.5) * 0.3 +
                        abs(user_timing["impulsivity"] - 0.5) * 0.3)

        fusion_result.assessment = strategy
        fusion_result.confidence = confidence

        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=strategy,
            secondary_assessments={
                "option_value_analysis": option_value,
                "user_timing_preference": user_timing,
                "mechanism_adjustments": adjustments,
            },
            recommended_mechanisms=recommended,
            mechanism_weights={m: max(0.1, 0.5 + adjustments.get(m, 0))
                             for m in recommended} if recommended else {"commitment": 0.5},
            inferred_states={
                "option_value": option_value["option_value"],
                "impulsivity": user_timing["impulsivity"],
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
