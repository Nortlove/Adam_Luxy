# =============================================================================
# ADAM Mimetic Desire Atom
# Location: adam/atoms/core/mimetic_desire_atom.py
# =============================================================================

"""
MIMETIC DESIRE ATOM

Grounded in René Girard's Mimetic Theory (1961) and modern extensions.
Models how desire is not intrinsic but IMITATED — we want things because
other people (specifically, people we identify with or aspire to be)
want them. This is fundamentally different from social proof (which is
about consensus) — mimetic desire is about MODEL-BASED wanting.

Key insight: Social proof says "many people chose this." Mimetic desire
says "THAT PERSON chose this, and I want to be like that person." The
model (the person being imitated) is everything. A tech influencer's
choice matters more to tech enthusiasts than 10,000 anonymous reviews.
This atom identifies the right MODEL and the right mechanism for
triggering mimetic desire without activating rivalry/resentment.

Academic Foundation:
- Girard (1961): Deceit, Desire, and the Novel — mimetic theory
- Girard (1972): Violence and the Sacred — mimetic rivalry
- Oughourlian (2010): The Genesis of Desire — clinical mimetic theory
- Gallese (2001): Mirror Neurons — neural basis for imitation
- Belk (1988): Possessions and the Extended Self — objects as identity
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
from adam.atoms.core.dsp_integration import DSPDataAccessor, EmpiricalEffectivenessHelper
from adam.atoms.core.construct_resolver import PsychologicalConstructResolver

logger = logging.getLogger(__name__)


# Model types and their effectiveness drivers
# A "model" in Girardian terms is the person being imitated
MODEL_TYPES = {
    "aspirational_peer": {
        "description": "Someone slightly above you in the hierarchy you care about",
        "effectiveness_base": 0.8,
        "ndf_fit": {"status_sensitivity": 0.3, "social_calibration": 0.2},
        "risk_of_rivalry": 0.3,  # Can trigger resentment if too close in status
    },
    "distant_celebrity": {
        "description": "Famous person far above in social hierarchy",
        "effectiveness_base": 0.5,
        "ndf_fit": {"status_sensitivity": 0.4, "arousal_seeking": 0.1},
        "risk_of_rivalry": 0.05,  # Too distant for rivalry
    },
    "expert_authority": {
        "description": "Domain expert whose judgment you trust",
        "effectiveness_base": 0.7,
        "ndf_fit": {"cognitive_engagement": 0.3, "uncertainty_tolerance": -0.2},
        "risk_of_rivalry": 0.1,
    },
    "in_group_member": {
        "description": "Someone in your social group or identity category",
        "effectiveness_base": 0.75,
        "ndf_fit": {"social_calibration": 0.4, "approach_avoidance": 0.1},
        "risk_of_rivalry": 0.4,  # Highest rivalry risk (Girardian "internal mediation")
    },
    "anonymous_mass": {
        "description": "Large number of unnamed others",
        "effectiveness_base": 0.4,
        "ndf_fit": {"uncertainty_tolerance": -0.2, "social_calibration": 0.1},
        "risk_of_rivalry": 0.0,
    },
}

# Mimetic desire intensity → mechanism mapping
MIMETIC_MECHANISMS = {
    "high_mimetic": {
        "mimetic_desire": 0.25,
        "identity_construction": 0.15,
        "social_proof": 0.1,
        "scarcity": 0.1,  # "They're buying it" + limited = powerful
    },
    "moderate_mimetic": {
        "social_proof": 0.15,
        "mimetic_desire": 0.1,
        "identity_construction": 0.1,
    },
    "low_mimetic": {
        "authority": 0.1,
        "commitment": 0.1,
        "anchoring": 0.05,
        "mimetic_desire": -0.1,  # Don't trigger imitation for independent thinkers
    },
}


class MimeticDesireAtom(BaseAtom):
    """
    Models imitative desire patterns for persuasion optimization.

    This atom determines:
    1. User's mimetic susceptibility (how driven by imitation)
    2. Optimal model type (who should be shown as choosing this product)
    3. Rivalry risk (can trigger resentment if handled wrong)
    4. Mechanism adjustments for mimetic desire activation

    CRITICAL DISTINCTION from social proof:
    - Social proof = "many people chose this" (quantity)
    - Mimetic desire = "THAT person chose this" (quality of model)
    """

    ATOM_TYPE = AtomType.MIMETIC_DESIRE
    ATOM_NAME = "mimetic_desire_assessment"
    TARGET_CONSTRUCT = "mimetic_susceptibility"

    REQUIRED_SOURCES = [
        IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
    ]

    OPTIONAL_SOURCES = [
        IntelligenceSourceType.EMPIRICAL_PATTERNS,
        IntelligenceSourceType.GRAPH_EMERGENCE,
        IntelligenceSourceType.MECHANISM_TRAJECTORIES,
    ]

    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        return None

    def _compute_mimetic_susceptibility(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        Compute user's susceptibility to mimetic desire.

        High social_calibration + high status_sensitivity = high mimetic
        High cognitive_engagement + high uncertainty_tolerance = low mimetic
        """
        # Use PsychologicalConstructResolver — prefers graph/expanded types over NDF
        psy = PsychologicalConstructResolver(atom_input)

        susceptibility = 0.5
        if psy.has_any:
            sc = psy.social_calibration
            ss = psy.status_sensitivity
            ce = psy.cognitive_engagement
            ut = psy.uncertainty_tolerance
            aa = psy.approach_avoidance

            susceptibility = (
                0.25 +
                sc * 0.25 +         # Social awareness → mimetic
                ss * 0.2 +          # Status drive → mimetic
                (1 - ce) * 0.15 +   # Low critical thinking → mimetic
                (1 - ut) * 0.1 +    # Need for closure → mimetic
                aa * 0.05           # Approach → desire
            )

        susceptibility = max(0.05, min(0.95, susceptibility))

        # Classify
        if susceptibility > 0.65:
            level = "high_mimetic"
        elif susceptibility > 0.35:
            level = "moderate_mimetic"
        else:
            level = "low_mimetic"

        return {
            "susceptibility": susceptibility,
            "level": level,
        }

    def _select_optimal_model(
        self,
        atom_input: AtomInput,
        mimetic_profile: Dict,
    ) -> Dict[str, any]:
        """
        Select the optimal model type for mimetic desire activation.
        """
        # Use PsychologicalConstructResolver — prefers graph/expanded types over NDF
        psy = PsychologicalConstructResolver(atom_input)
        psy_dict = psy.as_full_construct_dict()

        model_scores = {}
        for model_id, model_def in MODEL_TYPES.items():
            score = model_def["effectiveness_base"]

            # Psychological construct fit (graph/expanded type preferred over NDF)
            if psy.has_any:
                for dim, weight in model_def["ndf_fit"].items():
                    val = psy_dict.get(dim, 0.5)
                    score += (val - 0.5) * weight

            # Rivalry risk penalty
            if mimetic_profile["susceptibility"] > 0.6:
                # High mimetic users are more prone to rivalry
                score -= model_def["risk_of_rivalry"] * 0.2

            model_scores[model_id] = max(0.1, min(0.95, score))

        best_model = max(model_scores, key=model_scores.get)

        return {
            "optimal_model": best_model,
            "model_scores": model_scores,
            "rivalry_risk": MODEL_TYPES[best_model]["risk_of_rivalry"],
        }

    def _compute_mechanism_adjustments(
        self,
        mimetic_profile: Dict,
        model_selection: Dict,
    ) -> Dict[str, float]:
        """Convert mimetic analysis to mechanism adjustments."""
        level = mimetic_profile["level"]
        adjustments = dict(MIMETIC_MECHANISMS.get(level, MIMETIC_MECHANISMS["moderate_mimetic"]))

        # Model-specific adjustments
        model = model_selection["optimal_model"]
        if model == "expert_authority":
            adjustments["authority"] = adjustments.get("authority", 0) + 0.1
        elif model == "in_group_member":
            adjustments["unity"] = adjustments.get("unity", 0) + 0.15
        elif model == "aspirational_peer":
            adjustments["identity_construction"] = adjustments.get("identity_construction", 0) + 0.1

        # Rivalry mitigation: if rivalry risk is high, boost unity to counter
        if model_selection["rivalry_risk"] > 0.3:
            adjustments["unity"] = adjustments.get("unity", 0) + 0.1
            adjustments["scarcity"] = adjustments.get("scarcity", 0) - 0.1  # Don't amplify competition

        return adjustments

    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build mimetic desire output."""

        mimetic_profile = self._compute_mimetic_susceptibility(atom_input)
        model_selection = self._select_optimal_model(atom_input, mimetic_profile)
        adjustments = self._compute_mechanism_adjustments(mimetic_profile, model_selection)

        # DSP empirical effectiveness: adjust mechanisms by review-corpus success data
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            adjustments = EmpiricalEffectivenessHelper.apply(adjustments, dsp)

        primary = mimetic_profile["level"]

        sorted_mechs = sorted(adjustments.items(), key=lambda x: x[1], reverse=True)
        recommended = [m for m, s in sorted_mechs[:3] if s > 0]

        confidence = min(0.85, 0.4 + abs(mimetic_profile["susceptibility"] - 0.5) * 0.7)

        fusion_result.assessment = primary
        fusion_result.confidence = confidence

        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary,
            secondary_assessments={
                "mimetic_profile": mimetic_profile,
                "model_selection": model_selection,
                "mechanism_adjustments": adjustments,
            },
            recommended_mechanisms=recommended,
            mechanism_weights={m: max(0.1, 0.5 + adjustments.get(m, 0))
                             for m in recommended} if recommended else {"social_proof": 0.5},
            inferred_states={
                "mimetic_susceptibility": mimetic_profile["susceptibility"],
                "rivalry_risk": model_selection["rivalry_risk"],
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
