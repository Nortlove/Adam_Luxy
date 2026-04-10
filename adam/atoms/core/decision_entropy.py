# =============================================================================
# ADAM Decision Entropy Atom
# Location: adam/atoms/core/decision_entropy.py
# =============================================================================

"""
DECISION ENTROPY ATOM

Grounded in Information Theory (Shannon, 1948) applied to decision-making.
Models the information-theoretic uncertainty in the user's decision state
and determines optimal information delivery to reduce entropy toward
the desired outcome.

Key insight: A decision with high entropy (many equally weighted options)
needs DIFFERENT mechanisms than one with low entropy (nearly decided).
High entropy → reduce choices (authority, social proof, anchoring).
Low entropy → reinforce the leading option (commitment, identity).
The optimal ad strategy depends entirely on WHERE the user is in their
decision entropy curve.

Academic Foundation:
- Shannon (1948): A Mathematical Theory of Communication
- Busemeyer & Townsend (1993): Decision Field Theory
- Roe, Busemeyer & Townsend (2001): Multialternative Decision Field Theory
- Tversky & Shafir (1992): Disjunction Effect — uncertainty causes inaction
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


# Decision stage → entropy level → mechanism effectiveness
ENTROPY_MECHANISM_MAP = {
    "high_entropy": {
        # Many options, hasn't narrowed — need to simplify
        "anchoring": 0.2,           # Set reference point
        "authority": 0.15,          # Expert narrows choices
        "social_proof": 0.15,       # Consensus simplifies
        "attention_dynamics": 0.1,  # Cut through noise
        # Avoid adding more complexity
        "identity_construction": -0.1,
        "embodied_cognition": -0.05,
    },
    "moderate_entropy": {
        # Considering a few options — need differentiation
        "identity_construction": 0.15,
        "social_proof": 0.1,
        "anchoring": 0.1,
        "temporal_construal": 0.1,
        "mimetic_desire": 0.1,
    },
    "low_entropy": {
        # Nearly decided — need confirmation and nudge
        "commitment": 0.2,
        "scarcity": 0.15,           # Now-or-never works here
        "reciprocity": 0.1,         # Tip the balance
        "regulatory_focus": 0.1,    # Loss of not acting
        # Don't introduce doubt
        "authority": -0.1,
        "anchoring": -0.1,
    },
    "decision_paralysis": {
        # Too many options, stuck — need to break the jam
        "social_proof": 0.2,        # "Most people choose..."
        "authority": 0.15,          # "Experts recommend..."
        "commitment": 0.1,          # Foot-in-door
        "scarcity": -0.15,          # Pressure makes paralysis worse
        "attention_dynamics": -0.1,
    },
}


class DecisionEntropyAtom(BaseAtom):
    """
    Models decision uncertainty using information theory to optimize
    information delivery and mechanism selection.

    This atom:
    1. Estimates current decision entropy (how uncertain the user is)
    2. Determines optimal entropy reduction strategy
    3. Selects mechanisms that move entropy toward decision
    4. Detects decision paralysis (too much information)
    """

    ATOM_TYPE = AtomType.DECISION_ENTROPY
    ATOM_NAME = "decision_entropy"
    TARGET_CONSTRUCT = "decision_uncertainty"

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
        return None

    def _estimate_decision_entropy(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        Estimate the user's current decision entropy.

        Uses NDF dimensions + context to estimate H(decision):
        - High uncertainty_tolerance + high cognitive_engagement → deliberating (moderate entropy)
        - Low uncertainty_tolerance → wants closure fast (works to reduce entropy)
        - High arousal + approach → ready to act (low entropy)
        - High cognitive_engagement + low approach → analyzing (high entropy, risk of paralysis)
        """
        ad_context = atom_input.ad_context or {}
        # Use PsychologicalConstructResolver — prefers graph/expanded types over NDF
        psy = PsychologicalConstructResolver(atom_input)

        # Base entropy from psychological constructs
        entropy = 0.5  # Moderate uncertainty
        paralysis_risk = 0.2

        if psy.has_any:
            ut = psy.uncertainty_tolerance
            ce = psy.cognitive_engagement
            aa = psy.approach_avoidance
            aas = psy.arousal_seeking

            # High CE + low approach = still deliberating → high entropy
            entropy += (ce - 0.5) * 0.3
            entropy -= (aa - 0.5) * 0.3
            entropy -= (aas - 0.5) * 0.15

            # Paralysis risk: high CE + low UT + low approach
            paralysis_risk = (
                0.1 + ce * 0.3 + (1 - ut) * 0.2 + (1 - aa) * 0.2
            )

        entropy = max(0.05, min(0.95, entropy))
        paralysis_risk = max(0.05, min(0.9, paralysis_risk))

        # Context modifiers
        num_alternatives = ad_context.get("num_alternatives", 3)
        if num_alternatives > 5:
            entropy = min(0.95, entropy * 1.2)
            paralysis_risk = min(0.9, paralysis_risk * 1.3)

        is_repeat_visit = ad_context.get("is_repeat_visit", False)
        if is_repeat_visit:
            entropy *= 0.8  # Already partially decided

        # Classify
        if paralysis_risk > 0.6:
            stage = "decision_paralysis"
        elif entropy > 0.65:
            stage = "high_entropy"
        elif entropy > 0.35:
            stage = "moderate_entropy"
        else:
            stage = "low_entropy"

        # Information value: how much value each bit of new info provides
        # High entropy → high info value; Low entropy → low info value
        info_value = entropy * (1.0 - paralysis_risk * 0.5)

        return {
            "entropy": entropy,
            "paralysis_risk": paralysis_risk,
            "stage": stage,
            "information_value": info_value,
            "needs_simplification": entropy > 0.6 or paralysis_risk > 0.5,
            "needs_nudge": entropy < 0.35,
        }

    def _compute_mechanism_adjustments(
        self,
        entropy_profile: Dict[str, float],
    ) -> Dict[str, float]:
        """Convert entropy analysis to mechanism adjustments."""
        stage = entropy_profile["stage"]
        entropy = entropy_profile["entropy"]

        base_map = ENTROPY_MECHANISM_MAP.get(stage, ENTROPY_MECHANISM_MAP["moderate_entropy"])

        adjustments = {}
        # Scale by entropy intensity
        intensity = 0.5 + abs(entropy - 0.5)
        for mech, adj in base_map.items():
            adjustments[mech] = adj * intensity

        return adjustments

    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build decision entropy output."""

        profile = self._estimate_decision_entropy(atom_input)
        adjustments = self._compute_mechanism_adjustments(profile)

        # DSP susceptibility: adjust mechanisms by user decision-style susceptibility
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            adjustments = SusceptibilityHelper.apply(adjustments, dsp)

        primary = profile["stage"]

        sorted_mechs = sorted(adjustments.items(), key=lambda x: x[1], reverse=True)
        recommended = [m for m, s in sorted_mechs[:3] if s > 0]

        confidence = min(0.85, 0.4 + abs(profile["entropy"] - 0.5) * 0.6)

        fusion_result.assessment = primary
        fusion_result.confidence = confidence

        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary,
            secondary_assessments={
                "entropy_profile": profile,
                "mechanism_adjustments": adjustments,
                "strategy_guidance": {
                    "simplify_choices": profile["needs_simplification"],
                    "push_for_action": profile["needs_nudge"],
                    "provide_info": profile["information_value"] > 0.5,
                },
            },
            recommended_mechanisms=recommended,
            mechanism_weights={m: max(0.1, 0.5 + adjustments.get(m, 0))
                             for m in recommended} if recommended else {"social_proof": 0.5},
            inferred_states={
                "decision_entropy": profile["entropy"],
                "paralysis_risk": profile["paralysis_risk"],
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
