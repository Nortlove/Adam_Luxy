# =============================================================================
# ADAM Narrative Identity Atom
# Location: adam/atoms/core/narrative_identity.py
# =============================================================================

"""
NARRATIVE IDENTITY ATOM

Grounded in Narrative Psychology (McAdams, 1993, 2001) and Narrative
Transportation Theory (Green & Brock, 2000). Models how people construct
their life story and how purchase decisions serve as "chapters" in that
narrative. When an ad connects to a person's ongoing life narrative,
persuasion resistance collapses because the purchase feels like self-
expression rather than influence.

Key insight: People don't just buy products — they buy PLOT DEVICES for
their life story. A fitness watch isn't a gadget; it's a chapter marker
in "my transformation story." Understanding which narrative themes
resonate (redemption, growth, belonging, adventure, mastery) determines
which framing and mechanisms create genuine narrative transport.

Academic Foundation:
- McAdams (1993): The Stories We Live By — narrative identity theory
- McAdams (2001): The Psychology of Life Stories — redemptive self
- Green & Brock (2000): Narrative Transportation Theory
- Escalas (2004): Narrative Processing & Persuasion
- Adaval & Wyer (1998): The Role of Narratives in Consumer Judgment
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
from adam.atoms.core.dsp_integration import DSPDataAccessor
from adam.atoms.core.construct_resolver import PsychologicalConstructResolver

logger = logging.getLogger(__name__)


# =============================================================================
# NARRATIVE THEMES (McAdams, 2001 life story model)
# =============================================================================

NARRATIVE_THEMES = {
    "redemption": {
        "description": "Overcoming adversity — bad becomes good",
        "ndf_affinity": {
            "approach_avoidance": 0.3,
            "temporal_horizon": 0.2,
            "uncertainty_tolerance": 0.1,
        },
        "mechanism_boosts": {
            "identity_construction": 0.2,
            "commitment": 0.15,
            "storytelling": 0.2,
            "social_proof": 0.1,
        },
        "ad_framing": "transformation_story",
        "example": "From struggling to thriving — your next chapter starts here",
    },
    "contamination": {
        "description": "Good situation threatened — must protect",
        "ndf_affinity": {
            "approach_avoidance": -0.3,
            "uncertainty_tolerance": -0.2,
            "arousal_seeking": -0.1,
        },
        "mechanism_boosts": {
            "regulatory_focus": 0.2,
            "commitment": 0.15,
            "authority": 0.15,
            "scarcity": 0.1,
        },
        "ad_framing": "protection_story",
        "example": "Don't let [threat] undermine what you've built",
    },
    "growth": {
        "description": "Continuous improvement — becoming better",
        "ndf_affinity": {
            "approach_avoidance": 0.2,
            "cognitive_engagement": 0.2,
            "temporal_horizon": 0.3,
        },
        "mechanism_boosts": {
            "identity_construction": 0.2,
            "authority": 0.1,
            "temporal_construal": 0.15,
        },
        "ad_framing": "progress_story",
        "example": "The next step in your journey",
    },
    "belonging": {
        "description": "Finding your tribe — connection and community",
        "ndf_affinity": {
            "social_calibration": 0.4,
            "approach_avoidance": 0.1,
            "status_sensitivity": -0.1,
        },
        "mechanism_boosts": {
            "unity": 0.25,
            "social_proof": 0.15,
            "mimetic_desire": 0.1,
            "reciprocity": 0.1,
        },
        "ad_framing": "community_story",
        "example": "Join thousands who already...",
    },
    "mastery": {
        "description": "Achieving expertise — competence and skill",
        "ndf_affinity": {
            "cognitive_engagement": 0.3,
            "status_sensitivity": 0.2,
            "arousal_seeking": -0.1,
        },
        "mechanism_boosts": {
            "authority": 0.2,
            "identity_construction": 0.15,
            "commitment": 0.1,
        },
        "ad_framing": "expertise_story",
        "example": "The tool that serious [professionals] rely on",
    },
    "adventure": {
        "description": "Exploration and novelty — expanding horizons",
        "ndf_affinity": {
            "arousal_seeking": 0.3,
            "uncertainty_tolerance": 0.2,
            "approach_avoidance": 0.2,
        },
        "mechanism_boosts": {
            "attention_dynamics": 0.2,
            "embodied_cognition": 0.15,
            "scarcity": 0.1,
            "mimetic_desire": 0.1,
        },
        "ad_framing": "exploration_story",
        "example": "Discover something extraordinary",
    },
    "status": {
        "description": "Rising in social hierarchy — achievement and recognition",
        "ndf_affinity": {
            "status_sensitivity": 0.4,
            "social_calibration": 0.2,
            "approach_avoidance": 0.1,
        },
        "mechanism_boosts": {
            "identity_construction": 0.2,
            "mimetic_desire": 0.15,
            "scarcity": 0.15,
            "anchoring": 0.1,
        },
        "ad_framing": "elevation_story",
        "example": "For those who demand the best",
    },
}


class NarrativeIdentityAtom(BaseAtom):
    """
    Identifies the user's dominant life narrative theme and matches
    the ad framing to serve as a chapter in that narrative.

    This atom:
    1. Identifies the dominant narrative theme from NDF profile
    2. Assesses narrative transportability (how story-receptive the user is)
    3. Recommends mechanisms that reinforce the narrative
    4. Provides copy framing guidance for narrative-matched messaging
    """

    ATOM_TYPE = AtomType.NARRATIVE_IDENTITY
    ATOM_NAME = "narrative_identity"
    TARGET_CONSTRUCT = "life_narrative"

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

    def _identify_narrative_theme(
        self,
        atom_input: AtomInput,
    ) -> Dict[str, float]:
        """Score each narrative theme by psychological construct affinity."""
        # Use PsychologicalConstructResolver — prefers graph/expanded types over NDF
        psy = PsychologicalConstructResolver(atom_input)
        psy_dict = psy.as_full_construct_dict()

        theme_scores = {}
        for theme_id, theme_def in NARRATIVE_THEMES.items():
            score = 0.3
            if psy.has_any:
                for dim, weight in theme_def["ndf_affinity"].items():
                    val = psy_dict.get(dim, 0.5)
                    score += (val - 0.5) * weight
            theme_scores[theme_id] = max(0.05, min(0.95, score))

        return theme_scores

    def _assess_transportability(
        self,
        atom_input: AtomInput,
    ) -> float:
        """
        Assess how susceptible the user is to narrative transportation.

        High arousal_seeking + moderate cognitive_engagement = high transport
        Very high cognitive_engagement = lower transport (too analytical)
        """
        # Use PsychologicalConstructResolver — prefers graph/expanded types over NDF
        psy = PsychologicalConstructResolver(atom_input)

        if not psy.has_any:
            return 0.5

        aas = psy.arousal_seeking
        ce = psy.cognitive_engagement
        sc = psy.social_calibration

        # Narrative transport: emotional engagement + social awareness
        # but penalized by extreme analytical processing
        transport = 0.3 + aas * 0.25 + sc * 0.2
        if ce > 0.7:
            transport -= (ce - 0.7) * 0.3  # Too analytical to be transported

        return max(0.1, min(0.95, transport))

    def _compute_mechanism_adjustments(
        self,
        theme_scores: Dict[str, float],
        transportability: float,
    ) -> Dict[str, float]:
        """Convert narrative analysis to mechanism adjustments."""
        adjustments = {}

        # Weight by top 2 themes
        sorted_themes = sorted(theme_scores.items(), key=lambda x: x[1], reverse=True)

        for theme_id, score in sorted_themes[:2]:
            theme_def = NARRATIVE_THEMES[theme_id]
            for mech, boost in theme_def["mechanism_boosts"].items():
                adj = boost * score * (0.5 + transportability * 0.5)
                adjustments[mech] = adjustments.get(mech, 0) + adj

        # Storytelling universal boost if transportable
        if transportability > 0.5:
            adjustments["storytelling"] = adjustments.get("storytelling", 0) + transportability * 0.15

        return adjustments

    async def _build_output(
        self,
        atom_input: AtomInput,
        evidence: MultiSourceEvidence,
        fusion_result: FusionResult,
    ) -> AtomOutput:
        """Build narrative identity output."""

        theme_scores = self._identify_narrative_theme(atom_input)
        transportability = self._assess_transportability(atom_input)
        adjustments = self._compute_mechanism_adjustments(theme_scores, transportability)

        # DSP construct integration: enhance narrative adjustments with
        # empirical effectiveness and category moderation for theme-specific mechanisms
        dsp = DSPDataAccessor(atom_input)
        if dsp.has_dsp:
            # Empirical effectiveness: boost mechanisms that work for detected themes
            empirical = dsp.get_all_empirical()
            for mech in list(adjustments.keys()):
                emp = empirical.get(mech)
                if emp:
                    success = emp.get("success_rate", 0.5)
                    samples = emp.get("sample_size", 0)
                    confidence = min(1.0, math.log1p(samples) / 10.0) if samples > 0 else 0.1
                    adjustments[mech] += 0.15 * (success - 0.5) * confidence

            # Category moderation: adjust by product category
            cat_mod = dsp.get_all_category_moderation()
            for mech in list(adjustments.keys()):
                delta = cat_mod.get(mech)
                if delta is not None:
                    adjustments[mech] += 0.10 * delta

        best_theme = max(theme_scores, key=theme_scores.get)
        primary = best_theme

        sorted_mechs = sorted(adjustments.items(), key=lambda x: x[1], reverse=True)
        recommended = [m for m, s in sorted_mechs[:3] if s > 0]

        confidence = min(0.85, 0.4 + theme_scores[best_theme] * 0.3 + transportability * 0.2)

        fusion_result.assessment = primary
        fusion_result.confidence = confidence

        return AtomOutput(
            atom_id=self.config.atom_id,
            atom_type=self.ATOM_TYPE,
            request_id=atom_input.request_id,
            fusion_result=fusion_result,
            primary_assessment=primary,
            secondary_assessments={
                "theme_scores": theme_scores,
                "transportability": transportability,
                "mechanism_adjustments": adjustments,
                "framing_guidance": {
                    "narrative_theme": best_theme,
                    "ad_framing": NARRATIVE_THEMES[best_theme]["ad_framing"],
                    "example_copy": NARRATIVE_THEMES[best_theme]["example"],
                    "use_narrative_structure": transportability > 0.5,
                },
            },
            recommended_mechanisms=recommended,
            mechanism_weights={m: max(0.1, 0.5 + adjustments.get(m, 0))
                             for m in recommended} if recommended else {"identity_construction": 0.5},
            inferred_states={
                "dominant_narrative": theme_scores.get(best_theme, 0.5),
                "transportability": transportability,
            },
            overall_confidence=confidence,
            evidence_package=evidence,
            sources_queried=len(evidence.sources_queried),
            claude_used=fusion_result.claude_used,
        )
