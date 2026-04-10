# =============================================================================
# ADAM Predictive Error Atom
# Location: adam/atoms/core/predictive_error.py
# =============================================================================

"""
PREDICTIVE ERROR ATOM

Grounded in Predictive Processing / Free Energy Principle (Friston, 2010)
and Prediction Error Theory of Attention (Rao & Ballard, 1999).

Key insight from neuroscience: The brain is a prediction machine. It
constantly generates predictions about what will happen next, and
ATTENTION is allocated to prediction errors — things that are surprising
or unexpected. An ad that is completely predictable is invisible. An ad
that is completely random is confusing. The optimal persuasion strategy
operates in the "Goldilocks zone" of prediction error — surprising enough
to capture attention, predictable enough to feel safe.

Academic Foundation:
- Friston (2010): The Free-Energy Principle — unified brain theory
- Clark (2013): Whatever Next? Predictive Brains, Situated Agents
- Rao & Ballard (1999): Predictive Coding in the Visual Cortex
- Berlyne (1960): Conflict, Arousal, and Curiosity — optimal stimulation
- Silvia (2005): Interest — what is it and what does it tell us?
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
from adam.atoms.core.dsp_integration import DSPDataAccessor, SusceptibilityHelper
from adam.atoms.core.construct_resolver import PsychologicalConstructResolver

logger = logging.getLogger(__name__)


# Optimal prediction error zones for different NDF profiles
# arousal_seeking determines the width and center of the optimal zone
PE_OPTIMAL_ZONES = {
    "low_arousal": {  # arousal_seeking < 0.35
        "optimal_center": 0.3,   # Prefer mild surprise
        "zone_width": 0.2,      # Narrow tolerance
        "mechanisms_at_optimal": ["social_proof", "commitment", "authority"],
    },
    "moderate_arousal": {  # 0.35-0.65
        "optimal_center": 0.5,
        "zone_width": 0.3,
        "mechanisms_at_optimal": ["identity_construction", "social_proof", "mimetic_desire"],
    },
    "high_arousal": {  # > 0.65
        "optimal_center": 0.7,   # Prefer strong surprise
        "zone_width": 0.35,     # Wider tolerance
        "mechanisms_at_optimal": ["scarcity", "attention_dynamics", "embodied_cognition"],
    },
}


class PredictiveErrorAtom(BaseAtom):
    """
    Optimizes the prediction error level in advertising for maximum attention.

    This atom determines:
    1. The user's "prediction model" — what they expect from this category
    2. The optimal level of surprise (prediction error)
    3. Which mechanisms create the right amount of prediction error
    4. How to make the ad surprising enough to capture attention but
       familiar enough to feel trustworthy

    This is a fundamentally different approach from traditional persuasion:
    instead of matching the user's psychology, we're calibrating the
    MISMATCH between expectation and reality for optimal engagement.
    """

    ATOM_TYPE = AtomType.PREDICTIVE_ERROR
    ATOM_NAME = "predictive_error"
    TARGET_CONSTRUCT = "prediction_error_optimization"

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

    def _estimate_user_prediction_model(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        Estimate what the user expects from ads in this category.

        Users form predictions based on:
        - Category norms (what ads in this category usually look like)
        - Personal experience (their history with the brand/category)
        - NDF dimensions (their inherent prediction precision)
        """
        ad_context = atom_input.ad_context or {}
        # Use PsychologicalConstructResolver — prefers graph/expanded types over NDF
        psy = PsychologicalConstructResolver(atom_input)

        # Prediction precision: how tight are the user's expectations?
        # High cognitive engagement → tight predictions (notices deviations)
        # High uncertainty tolerance → loose predictions (accepts variation)
        prediction_precision = 0.5
        if psy.has_any:
            ce = psy.cognitive_engagement
            ut = psy.uncertainty_tolerance
            prediction_precision = 0.3 + ce * 0.4 - (ut - 0.5) * 0.3

        prediction_precision = max(0.1, min(0.9, prediction_precision))

        # Optimal arousal level
        arousal_seeking = psy.arousal_seeking

        if arousal_seeking < 0.35:
            zone = PE_OPTIMAL_ZONES["low_arousal"]
        elif arousal_seeking > 0.65:
            zone = PE_OPTIMAL_ZONES["high_arousal"]
        else:
            zone = PE_OPTIMAL_ZONES["moderate_arousal"]

        return {
            "prediction_precision": prediction_precision,
            "arousal_seeking": arousal_seeking,
            "optimal_pe_center": zone["optimal_center"],
            "pe_zone_width": zone["zone_width"],
            "optimal_mechanisms": zone["mechanisms_at_optimal"],
        }

    def _compute_mechanism_pe_levels(self) -> Dict[str, float]:
        """
        Compute the inherent prediction error level of each mechanism.

        Some mechanisms are inherently surprising (scarcity creates urgency
        that interrupts normal processing), others are predictable
        (social proof confirms expectations).
        """
        return {
            "scarcity": 0.75,             # High PE — "only 3 left!" breaks expectations
            "attention_dynamics": 0.8,     # Very high PE — designed to interrupt
            "embodied_cognition": 0.7,     # High PE — sensory language is unexpected
            "mimetic_desire": 0.6,         # Moderate PE — social comparison
            "identity_construction": 0.55, # Moderate PE — aspirational framing
            "temporal_construal": 0.5,     # Moderate — time framing
            "regulatory_focus": 0.45,      # Moderate — gain/loss
            "anchoring": 0.4,             # Low-moderate — price comparison expected
            "social_proof": 0.3,          # Low PE — confirms expectations
            "commitment": 0.25,           # Low PE — guarantees are expected
            "authority": 0.2,             # Very low PE — expertise is expected
            "reciprocity": 0.35,          # Low-moderate — "free trial" somewhat unexpected
        }

    def _compute_pe_fit(
        self,
        user_model: Dict,
        mechanism_pe_levels: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Compute how well each mechanism's PE level fits the user's optimal zone.

        Uses a Gaussian fit: mechanisms closest to optimal PE center get boost,
        those outside the zone get penalty.
        """
        center = user_model["optimal_pe_center"]
        width = user_model["pe_zone_width"]

        adjustments = {}
        for mechanism, pe_level in mechanism_pe_levels.items():
            # Gaussian fit: distance from optimal center
            distance = abs(pe_level - center)

            if distance <= width / 2:
                # Within optimal zone — boost proportional to closeness
                fit = 1.0 - (distance / (width / 2)) * 0.5
                adjustments[mechanism] = fit * 0.2
            else:
                # Outside optimal zone — penalty proportional to distance
                excess = distance - width / 2
                adjustments[mechanism] = -excess * 0.3

        return adjustments

    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build predictive error output."""

        user_model = self._estimate_user_prediction_model(atom_input)
        mechanism_pe_levels = self._compute_mechanism_pe_levels()
        pe_fit = self._compute_pe_fit(user_model, mechanism_pe_levels)

        # DSP susceptibility: adjust mechanisms by user decision-style susceptibility
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            pe_fit = SusceptibilityHelper.apply(pe_fit, dsp)

        # Primary assessment based on optimal PE level
        optimal_pe = user_model["optimal_pe_center"]
        if optimal_pe > 0.6:
            primary = "high_prediction_error_optimal"
        elif optimal_pe < 0.4:
            primary = "low_prediction_error_optimal"
        else:
            primary = "moderate_prediction_error_optimal"

        recommended = user_model["optimal_mechanisms"][:3]

        confidence = min(0.8, 0.4 + user_model["prediction_precision"] * 0.3)

        fusion_result.assessment = primary
        fusion_result.confidence = confidence

        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary,
            secondary_assessments={
                "user_prediction_model": user_model,
                "mechanism_pe_levels": mechanism_pe_levels,
                "pe_fit_adjustments": pe_fit,
            },
            recommended_mechanisms=recommended,
            mechanism_weights={m: max(0.1, 0.5 + pe_fit.get(m, 0))
                             for m in recommended},
            inferred_states={
                "prediction_precision": user_model["prediction_precision"],
                "optimal_pe": optimal_pe,
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
