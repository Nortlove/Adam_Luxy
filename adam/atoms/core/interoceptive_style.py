# =============================================================================
# ADAM Interoceptive Style Atom
# Location: adam/atoms/core/interoceptive_style.py
# =============================================================================

"""
INTEROCEPTIVE STYLE ATOM

Grounded in Interoception research (Craig, 2002; Garfinkel et al., 2015)
and Somatic Marker Hypothesis (Damasio, 1994). Models how much a person
uses bodily/gut feelings versus analytical reasoning in their decisions.

Key insight: Some people literally "feel" their decisions in their body —
gut feelings, physical discomfort with bad options, excitement for good
ones. These "interoceptive" decision-makers respond powerfully to
sensory, embodied language in ads ("feel the difference," "experience
luxury"). Others are primarily analytical — they want specs, comparisons,
and data. This atom determines the user's interoceptive style and adapts
mechanism selection accordingly.

Academic Foundation:
- Damasio (1994): Somatic Marker Hypothesis — body guides decisions
- Craig (2002): Interoception — the sense of the body's condition
- Garfinkel et al. (2015): What the Heart Forgets — interoceptive sensitivity
- Dunn et al. (2010): Listening to Your Heart — interoceptive accuracy
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


# Interoceptive style → mechanism effectiveness
INTEROCEPTIVE_MECHANISMS = {
    "high_interoceptive": {
        # Body-aware decision maker — use sensory/emotional mechanisms
        "embodied_cognition": 0.25,
        "mimetic_desire": 0.1,
        "identity_construction": 0.1,
        "attention_dynamics": 0.1,
        # Reduce analytical mechanisms
        "authority": -0.1,
        "anchoring": -0.1,
    },
    "low_interoceptive": {
        # Analytical decision maker — use data/logic mechanisms
        "authority": 0.2,
        "anchoring": 0.15,
        "commitment": 0.1,
        "social_proof": 0.1,
        # Reduce sensory mechanisms
        "embodied_cognition": -0.15,
        "attention_dynamics": -0.05,
    },
    "balanced_interoceptive": {
        "social_proof": 0.1,
        "identity_construction": 0.05,
        "authority": 0.05,
        "embodied_cognition": 0.05,
    },
}


class InteroceptiveStyleAtom(BaseAtom):
    """
    Determines user's interoceptive processing style for mechanism selection.

    This atom:
    1. Estimates interoceptive sensitivity from NDF (embodied language use)
    2. Classifies processing style (somatic vs analytical)
    3. Adjusts mechanism weights for sensory vs data-driven approach
    4. Provides copy guidance (sensory language vs specifications)
    """

    ATOM_TYPE = AtomType.INTEROCEPTIVE_STYLE
    ATOM_NAME = "interoceptive_style"
    TARGET_CONSTRUCT = "body_awareness_processing"

    REQUIRED_SOURCES = [
        IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
    ]

    OPTIONAL_SOURCES = [
        IntelligenceSourceType.EMPIRICAL_PATTERNS,
        IntelligenceSourceType.MECHANISM_TRAJECTORIES,
    ]

    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        return None

    def _estimate_interoceptive_style(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        Estimate interoceptive sensitivity from NDF dimensions.

        Mapping:
        - arousal_seeking: HIGH → high interoceptive (body-aware)
        - cognitive_engagement: HIGH → low interoceptive (analytical)
        - approach_avoidance: HIGH approach → moderate interoceptive (gut-driven action)
        - uncertainty_tolerance: LOW → low interoceptive (needs data, not feelings)
        """
        ad_context = atom_input.ad_context or {}
        # Use PsychologicalConstructResolver — prefers graph/expanded types over NDF
        psy = PsychologicalConstructResolver(atom_input)

        interoception = 0.5
        if psy.has_any:
            aas = psy.arousal_seeking
            ce = psy.cognitive_engagement
            aa = psy.approach_avoidance
            ut = psy.uncertainty_tolerance

            interoception = (
                0.2 +
                aas * 0.3 +          # Arousal-seeking → body-aware
                (1 - ce) * 0.25 +    # Low cognitive → relies on feelings
                aa * 0.1 +           # Approach → gut-driven
                ut * 0.1             # Tolerance → comfortable with ambiguity of feelings
            )

        interoception = max(0.05, min(0.95, interoception))

        # Category adjustment
        category = ad_context.get("category", "")
        sensory_categories = {"Food", "Beauty", "Fashion", "Travel", "Fragrance"}
        analytical_categories = {"Electronics", "Software", "Financial", "Insurance"}

        if any(c.lower() in category.lower() for c in sensory_categories):
            interoception = min(0.95, interoception + 0.1)
        elif any(c.lower() in category.lower() for c in analytical_categories):
            interoception = max(0.05, interoception - 0.1)

        if interoception > 0.6:
            level = "high_interoceptive"
        elif interoception < 0.4:
            level = "low_interoceptive"
        else:
            level = "balanced_interoceptive"

        return {
            "interoception": interoception,
            "level": level,
            "processing_mode": "somatic" if interoception > 0.6 else ("analytical" if interoception < 0.4 else "mixed"),
        }

    def _compute_mechanism_adjustments(
        self,
        interoceptive_profile: Dict[str, float],
    ) -> Dict[str, float]:
        """Convert interoceptive analysis to mechanism adjustments."""
        level = interoceptive_profile["level"]
        intensity = abs(interoceptive_profile["interoception"] - 0.5) + 0.5

        base_map = INTEROCEPTIVE_MECHANISMS.get(level, INTEROCEPTIVE_MECHANISMS["balanced_interoceptive"])

        adjustments = {}
        for mech, adj in base_map.items():
            adjustments[mech] = adj * intensity

        return adjustments

    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build interoceptive style output."""

        profile = self._estimate_interoceptive_style(atom_input)
        adjustments = self._compute_mechanism_adjustments(profile)

        # DSP category moderation: adjust mechanisms by product category effectiveness
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            adjustments = CategoryModerationHelper.apply(adjustments, dsp)

        primary = profile["level"]

        sorted_mechs = sorted(adjustments.items(), key=lambda x: x[1], reverse=True)
        recommended = [m for m, s in sorted_mechs[:3] if s > 0]

        confidence = min(0.85, 0.4 + abs(profile["interoception"] - 0.5) * 0.7)

        fusion_result.assessment = primary
        fusion_result.confidence = confidence

        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary,
            secondary_assessments={
                "interoceptive_profile": profile,
                "mechanism_adjustments": adjustments,
                "copy_guidance": {
                    "use_sensory_language": profile["interoception"] > 0.55,
                    "use_data_specs": profile["interoception"] < 0.45,
                    "processing_mode": profile["processing_mode"],
                },
            },
            recommended_mechanisms=recommended,
            mechanism_weights={m: max(0.1, 0.5 + adjustments.get(m, 0))
                             for m in recommended} if recommended else {"social_proof": 0.5},
            inferred_states={
                "interoception": profile["interoception"],
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
