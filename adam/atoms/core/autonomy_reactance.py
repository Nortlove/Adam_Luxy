# =============================================================================
# ADAM Autonomy Reactance Atom
# Location: adam/atoms/core/autonomy_reactance.py
# =============================================================================

"""
AUTONOMY REACTANCE ATOM

Grounded in Psychological Reactance Theory (Brehm, 1966; Brehm & Brehm,
1981) and Self-Determination Theory (Deci & Ryan, 1985). Models how
perceived threats to freedom of choice trigger motivational resistance,
and how to persuade WITHOUT triggering reactance.

Key insight: When people feel their freedom of choice is threatened, they
experience "reactance" — a motivational state that makes them WANT the
forbidden option more and RESIST the recommended option. High-pressure
sales tactics, explicit commands ("Buy now!"), and limited options all
trigger reactance. This atom detects the user's reactance threshold and
ensures persuasion mechanisms operate BELOW it.

This is critically important because it's the main reason WHY advertising
fails — the user detects the manipulation and reverses their decision.

Academic Foundation:
- Brehm (1966): A Theory of Psychological Reactance
- Brehm & Brehm (1981): Psychological Reactance — A Theory of Freedom
- Deci & Ryan (1985): Self-Determination Theory — autonomy need
- Wicklund (1974): Freedom and Reactance
- Miron & Brehm (2006): Reactance Theory — 40 Years Later
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


# Mechanism coerciveness: how much each mechanism threatens perceived freedom
# Higher = more likely to trigger reactance
MECHANISM_COERCIVENESS = {
    "scarcity": 0.85,            # "Only 2 left!" — very coercive
    "urgency": 0.9,              # "Buy NOW!" — extremely coercive
    "attention_dynamics": 0.6,    # Salience manipulation — moderately coercive
    "temporal_construal": 0.5,    # Time framing — moderate
    "anchoring": 0.4,            # Price anchoring — low-moderate
    "regulatory_focus": 0.45,     # Gain/loss — moderate (loss framing more coercive)
    "social_proof": 0.35,        # "Everyone does it" — mild coercion
    "authority": 0.5,            # "Experts say" — moderate
    "commitment": 0.45,          # Foot-in-door — moderate
    "mimetic_desire": 0.3,       # Model-based — low coercion
    "identity_construction": 0.2, # Self-concept — very low (feels like self-expression)
    "reciprocity": 0.25,         # Gift-giving — low (feels like generosity)
    "unity": 0.15,               # Shared identity — very low (feels like belonging)
    "storytelling": 0.1,         # Narrative — almost zero (feels like entertainment)
    "embodied_cognition": 0.1,   # Sensory — almost zero (feels like experience)
}


class AutonomyReactanceAtom(BaseAtom):
    """
    Detects reactance risk and constrains persuasion intensity.

    This atom acts as a SAFETY VALVE for the entire persuasion system:
    1. Estimates the user's reactance threshold (how sensitive to coercion)
    2. Scores each mechanism's coerciveness
    3. Computes a "reactance budget" — how much coercion is safe
    4. Constrains mechanism recommendations to stay under threshold

    CRITICAL: This atom's output should be treated as a HARD CONSTRAINT,
    not a soft recommendation. Exceeding the reactance threshold doesn't
    just reduce effectiveness — it REVERSES it.
    """

    ATOM_TYPE = AtomType.AUTONOMY_REACTANCE
    ATOM_NAME = "autonomy_reactance"
    TARGET_CONSTRUCT = "reactance_threshold"

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

    def _estimate_reactance_threshold(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """
        Estimate the user's psychological reactance threshold.

        NDF mapping:
        - cognitive_engagement: HIGH → lower threshold (detects manipulation)
        - approach_avoidance: LOW approach → lower threshold (cautious)
        - uncertainty_tolerance: HIGH → higher threshold (tolerant of pressure)
        - social_calibration: HIGH → variable (aware of social influence)
        - arousal_seeking: HIGH → higher threshold (thrill-seekers handle pressure)

        Returns threshold 0-1: higher = more tolerant of coercion
        """
        ad_context = atom_input.ad_context or {}
        # Use PsychologicalConstructResolver — prefers graph/expanded types over NDF
        psy = PsychologicalConstructResolver(atom_input)

        threshold = 0.5

        if psy.has_any:
            ce = psy.cognitive_engagement
            aa = psy.approach_avoidance
            ut = psy.uncertainty_tolerance
            aas = psy.arousal_seeking

            threshold = (
                0.2 +
                (1 - ce) * 0.25 +    # Low CE → higher threshold
                aa * 0.15 +           # Approach → tolerant of pressure
                ut * 0.2 +            # Uncertainty tolerant → tolerant of pressure
                aas * 0.15            # Arousal seeking → tolerant
            )

        threshold = max(0.1, min(0.9, threshold))

        # Upstream persuasion knowledge (from strategic_awareness atom)
        sa_output = atom_input.get_upstream("atom_strategic_awareness")
        if sa_output and sa_output.secondary_assessments:
            pk_level = sa_output.secondary_assessments.get("pk_level", 0.5)
            # High PK → lower reactance threshold
            threshold = max(0.1, threshold - pk_level * 0.15)

        # Context: repeated exposure lowers threshold
        exposure_count = ad_context.get("exposure_count", 1)
        if exposure_count > 3:
            threshold *= 0.85  # Repeated ads lower tolerance

        # Classify
        if threshold < 0.35:
            level = "high_reactance_risk"
        elif threshold > 0.65:
            level = "low_reactance_risk"
        else:
            level = "moderate_reactance_risk"

        return {
            "threshold": threshold,
            "level": level,
            "exposure_count": exposure_count,
        }

    def _compute_reactance_budget(
        self,
        threshold: float,
    ) -> float:
        """
        Compute the total "coerciveness budget" — the maximum total
        coerciveness that can be applied across all mechanisms.

        Below threshold: full budget available
        At threshold: budget = 0 (any coercion will backfire)
        """
        return max(0.0, threshold * 1.5)

    def _compute_mechanism_adjustments(
        self,
        reactance_profile: Dict[str, float],
    ) -> Dict[str, float]:
        """
        Compute mechanism adjustments based on reactance threshold.

        Mechanisms above the threshold get PENALIZED (they'll backfire).
        Mechanisms below the threshold are SAFE or BOOSTED.
        """
        threshold = reactance_profile["threshold"]
        budget = self._compute_reactance_budget(threshold)

        adjustments = {}

        for mechanism, coerciveness in MECHANISM_COERCIVENESS.items():
            if coerciveness > threshold:
                # This mechanism exceeds the threshold — PENALIZE
                excess = coerciveness - threshold
                penalty = -excess * 0.5  # Strong penalty for exceeding
                adjustments[mechanism] = max(-0.3, penalty)
            elif coerciveness < threshold * 0.5:
                # This mechanism is well below threshold — SAFE, slight boost
                adjustments[mechanism] = 0.05 + (threshold - coerciveness) * 0.1
            else:
                # Near threshold — small adjustment
                adjustments[mechanism] = 0.0

        # High reactance users → boost autonomy-preserving mechanisms
        if threshold < 0.4:
            adjustments["identity_construction"] = adjustments.get("identity_construction", 0) + 0.15
            adjustments["storytelling"] = adjustments.get("storytelling", 0) + 0.15
            adjustments["embodied_cognition"] = adjustments.get("embodied_cognition", 0) + 0.1
            adjustments["unity"] = adjustments.get("unity", 0) + 0.1
            adjustments["reciprocity"] = adjustments.get("reciprocity", 0) + 0.1

        return adjustments

    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build autonomy reactance output."""

        profile = self._estimate_reactance_threshold(atom_input)
        adjustments = self._compute_mechanism_adjustments(profile)

        # DSP susceptibility: adjust mechanisms by user decision-style susceptibility
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            adjustments = SusceptibilityHelper.apply(adjustments, dsp)

        budget = self._compute_reactance_budget(profile["threshold"])

        primary = profile["level"]

        sorted_mechs = sorted(adjustments.items(), key=lambda x: x[1], reverse=True)
        recommended = [m for m, s in sorted_mechs[:3] if s > 0]

        # Mechanisms to AVOID (hard constraints)
        avoid = [m for m, s in sorted(adjustments.items(), key=lambda x: x[1]) if s < -0.1]

        confidence = min(0.9, 0.5 + abs(profile["threshold"] - 0.5) * 0.6)

        fusion_result.assessment = primary
        fusion_result.confidence = confidence

        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary,
            secondary_assessments={
                "reactance_profile": profile,
                "mechanism_adjustments": adjustments,
                "reactance_budget": budget,
                "mechanisms_to_avoid": avoid,
                "hard_constraints": {
                    "max_coerciveness": profile["threshold"],
                    "avoid_mechanisms": avoid,
                    "prefer_autonomy_preserving": profile["threshold"] < 0.4,
                },
            },
            recommended_mechanisms=recommended,
            mechanism_weights={m: max(0.1, 0.5 + adjustments.get(m, 0))
                             for m in recommended} if recommended else {"identity_construction": 0.5},
            inferred_states={
                "reactance_threshold": profile["threshold"],
                "reactance_budget": budget,
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
