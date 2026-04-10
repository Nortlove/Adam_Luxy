# =============================================================================
# ADAM Strategic Awareness Atom
# Location: adam/atoms/core/strategic_awareness.py
# =============================================================================

"""
STRATEGIC AWARENESS ATOM

Grounded in the Persuasion Knowledge Model (Friestad & Wright, 1994).
Assesses how aware the user is that they are being persuaded, and adapts
the persuasion strategy accordingly.

Key insight: When consumers activate their "persuasion knowledge" — their
mental model of how persuasion works — they become resistant to obvious
tactics. But this resistance is selective: people who are highly aware of
social proof tactics may still be fully susceptible to authority or
narrative-based mechanisms. This atom detects the user's persuasion
sophistication and routes around their defenses.

Academic Foundation:
- Friestad & Wright (1994): Persuasion Knowledge Model
- Campbell & Kirmani (2000): Inference of ulterior motives
- Wegener et al. (2004): Flexible correction in persuasion
- Isaac & Grayson (2017): Beyond skepticism — calibrated trust
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
# PERSUASION KNOWLEDGE PROFILES
# =============================================================================

# Mechanism detectability: how easy it is for a consumer to recognize
# each mechanism as a persuasion attempt. Higher = more detectable.
MECHANISM_DETECTABILITY = {
    "scarcity": 0.85,        # "Only 3 left!" is very obvious
    "social_proof": 0.7,     # "Millions trust us" recognized as tactic
    "urgency": 0.9,          # "Act now!" is extremely obvious
    "reciprocity": 0.4,      # Harder to detect (feels like genuine gift)
    "commitment": 0.5,       # Foot-in-door less detectable
    "authority": 0.65,       # Expert endorsements somewhat detectable
    "liking": 0.3,           # Rapport-building hard to detect
    "unity": 0.25,           # Shared identity is very subtle
    "storytelling": 0.2,     # Narrative transport bypasses defenses
    "anchoring": 0.55,       # Price anchoring moderately detectable
    "identity_construction": 0.35,  # Self-concept alignment is subtle
    "mimetic_desire": 0.3,   # Wanting what others want — hard to spot
    "embodied_cognition": 0.15,  # Sensory language very subtle
    "temporal_construal": 0.4,   # Time framing moderately detectable
    "regulatory_focus": 0.45,    # Gain/loss framing partially detectable
    "attention_dynamics": 0.5,   # Salience manipulation moderate
}

# NDF-to-persuasion-knowledge mapping
# High cognitive_engagement → more likely to detect persuasion
# High social_calibration → more attuned to social manipulation
# Low uncertainty_tolerance → less likely to accept without scrutiny
NDF_TO_PKM = {
    "cognitive_engagement": 0.35,    # Critical thinkers detect more
    "social_calibration": 0.20,      # Socially attuned detect social tactics
    "uncertainty_tolerance": -0.15,  # Intolerant of uncertainty → more skeptical
    "approach_avoidance": -0.10,     # Cautious → more defensive
    "status_sensitivity": 0.05,      # Status-sensitive → detect status plays
}


class StrategicAwarenessAtom(BaseAtom):
    """
    Assesses user's persuasion knowledge and adapts strategy accordingly.

    This atom determines:
    1. Overall persuasion sophistication (how aware they are of being persuaded)
    2. Which specific mechanisms they're likely to detect/resist
    3. Which mechanisms bypass their persuasion knowledge
    4. Optimal "stealth" strategy — persuasion that doesn't trigger defenses

    The output provides mechanism-level detectability penalties that
    MechanismActivation uses to avoid triggering persuasion resistance.
    """

    ATOM_TYPE = AtomType.STRATEGIC_AWARENESS
    ATOM_NAME = "strategic_awareness"
    TARGET_CONSTRUCT = "persuasion_knowledge"

    REQUIRED_SOURCES = [
        IntelligenceSourceType.NONCONSCIOUS_SIGNALS,
        IntelligenceSourceType.EMPIRICAL_PATTERNS,
    ]

    OPTIONAL_SOURCES = [
        IntelligenceSourceType.MECHANISM_TRAJECTORIES,
        IntelligenceSourceType.GRAPH_EMERGENCE,
    ]

    async def _query_construct_specific(
        self,
        source: IntelligenceSourceType,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query sources for persuasion knowledge assessment."""
        if source == IntelligenceSourceType.EMPIRICAL_PATTERNS:
            return await self._query_resistance_patterns(atom_input)
        return None

    async def _query_resistance_patterns(
        self,
        atom_input: AtomInput,
    ) -> Optional[IntelligenceEvidence]:
        """Query historical resistance patterns for this user/cohort."""
        try:
            # Check mechanism history for mechanisms that failed
            mech_output = atom_input.get_upstream("atom_mechanism_activation")
            if mech_output and mech_output.secondary_assessments:
                mechanism_scores = mech_output.secondary_assessments.get("mechanism_scores", {})
                if mechanism_scores:
                    return IntelligenceEvidence(
                        source_type=IntelligenceSourceType.EMPIRICAL_PATTERNS,
                        construct=self.TARGET_CONSTRUCT,
                        assessment="mechanism_history_available",
                        assessment_value=0.6,
                        confidence=0.5,
                        confidence_semantics=ConfidenceSemantics.DOMAIN_CALIBRATED,
                        strength=EvidenceStrength.MODERATE,
                        reasoning="Historical mechanism data available for resistance estimation",
                    )
        except Exception as e:
            logger.debug(f"Resistance pattern query failed: {e}")
        return None

    def _estimate_persuasion_knowledge(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        Estimate the user's persuasion knowledge level.

        Uses NDF dimensions to estimate how sophisticated the user is
        about persuasion tactics. Returns a score 0-1 for each mechanism.
        """
        ad_context = atom_input.ad_context or {}
        # Use PsychologicalConstructResolver — prefers graph/expanded types over NDF
        psy = PsychologicalConstructResolver(atom_input)
        psy_dict = psy.as_full_construct_dict()

        # Base persuasion knowledge from psychological constructs
        base_pk = 0.5  # Default moderate
        if psy.has_any:
            for dim, weight in NDF_TO_PKM.items():
                dim_value = psy_dict.get(dim, 0.5)
                base_pk += (dim_value - 0.5) * weight

        base_pk = max(0.1, min(0.95, base_pk))

        # Per-mechanism detection probability
        detection_probs = {}
        for mechanism, base_detect in MECHANISM_DETECTABILITY.items():
            # User's detection = mechanism's inherent detectability × user's PK
            # High PK users detect even subtle mechanisms
            # Low PK users miss even obvious ones
            prob = base_detect * (0.3 + base_pk * 0.7)
            detection_probs[mechanism] = max(0.05, min(0.95, prob))

        return {
            "overall_pk_level": base_pk,
            "detection_probabilities": detection_probs,
        }

    def _compute_stealth_scores(
        self,
        pk_profile: Dict,
    ) -> Dict[str, float]:
        """
        Compute "stealth scores" — how well each mechanism avoids detection.

        Stealth = 1 - detection_probability.
        High stealth mechanisms can be used even with high-PK users.
        """
        detection_probs = pk_profile.get("detection_probabilities", {})
        overall_pk = pk_profile.get("overall_pk_level", 0.5)

        stealth_scores = {}
        for mechanism, detect_prob in detection_probs.items():
            stealth = 1.0 - detect_prob

            # If user is very high PK, even "stealthy" mechanisms get a penalty
            if overall_pk > 0.75:
                stealth *= 0.85  # 15% penalty across the board

            stealth_scores[mechanism] = max(0.05, stealth)

        return stealth_scores

    def _compute_mechanism_adjustments(
        self,
        stealth_scores: Dict[str, float],
        pk_level: float,
    ) -> Dict[str, float]:
        """
        Convert stealth scores to mechanism weight adjustments.

        For high-PK users: penalize detectable mechanisms, boost stealthy ones
        For low-PK users: minimal adjustment (all mechanisms work)
        """
        adjustments = {}

        # Adjustment magnitude scales with PK level
        # At PK=0.5, adjustments are minimal (±5%)
        # At PK=0.9, adjustments are significant (±25%)
        magnitude = max(0, (pk_level - 0.4)) * 0.5

        for mechanism, stealth in stealth_scores.items():
            # Stealth > 0.5 → positive adjustment (mechanism is safe)
            # Stealth < 0.5 → negative adjustment (mechanism will be detected)
            adjustment = (stealth - 0.5) * magnitude
            adjustments[mechanism] = max(-0.25, min(0.25, adjustment))

        return adjustments

    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build strategic awareness output."""

        # Estimate persuasion knowledge
        pk_profile = self._estimate_persuasion_knowledge(atom_input)
        pk_level = pk_profile["overall_pk_level"]

        # Compute stealth scores
        stealth_scores = self._compute_stealth_scores(pk_profile)

        # Compute mechanism adjustments
        mechanism_adjustments = self._compute_mechanism_adjustments(
            stealth_scores, pk_level
        )

        # DSP susceptibility: adjust mechanisms by user decision-style susceptibility
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            mechanism_adjustments = SusceptibilityHelper.apply(mechanism_adjustments, dsp)

        # Primary assessment
        if pk_level > 0.7:
            primary = "high_persuasion_knowledge"
        elif pk_level > 0.45:
            primary = "moderate_persuasion_knowledge"
        else:
            primary = "low_persuasion_knowledge"

        # Recommend stealthiest mechanisms
        sorted_stealth = sorted(stealth_scores.items(), key=lambda x: x[1], reverse=True)
        recommended = [m for m, s in sorted_stealth[:3]]

        confidence = min(0.85, 0.5 + abs(pk_level - 0.5) * 0.6)

        fusion_result.assessment = primary
        fusion_result.confidence = confidence

        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary,
            secondary_assessments={
                "pk_level": pk_level,
                "detection_probabilities": pk_profile["detection_probabilities"],
                "stealth_scores": stealth_scores,
                "mechanism_adjustments": mechanism_adjustments,
                "recommended_approach": "subtle_mechanisms" if pk_level > 0.6 else "standard",
            },
            recommended_mechanisms=recommended,
            mechanism_weights={m: stealth_scores[m] for m in recommended},
            inferred_states={
                "persuasion_knowledge": pk_level,
                **{f"stealth_{k}": v for k, v in list(stealth_scores.items())[:5]},
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
